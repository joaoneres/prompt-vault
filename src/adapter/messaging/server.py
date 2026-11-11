import asyncio
from collections.abc import Sequence
from typing import Any

from nats.aio.msg import Msg
from nats.aio.subscription import Subscription

from infra.logging import get_logger
from infra.nats_client import NatsClient

from . import subjects
from .codec import (
    CORRELATION_HEADER,
    decode_payload,
    error_envelope,
    ok_envelope,
    resolve_correlation_id,
)
from .correlation import correlation_scope
from .errors import InvalidPayloadError, to_error
from .handlers import Route, RouteKind

log = get_logger(__name__)


class MessagingAdapter:
    """Subscribes each route's subject, runs its handler and answers. No business logic."""

    def __init__(
        self, nats_client: NatsClient, routes: Sequence[Route], timeout_seconds: float
    ) -> None:
        self._nats_client = nats_client
        self._routes = routes
        self._timeout = timeout_seconds
        self._subscriptions: list[Subscription] = []

    async def start(self) -> None:
        for route in self._routes:
            subscription = await self._nats_client.nc.subscribe(
                route.subject, cb=self._callback_for(route)
            )
            self._subscriptions.append(subscription)
            log.info("subscribed", subject=route.subject, kind=route.kind.value)

    async def stop(self) -> None:
        for subscription in self._subscriptions:
            await subscription.unsubscribe()
        self._subscriptions.clear()
        log.info("unsubscribed")

    def _callback_for(self, route: Route):
        async def callback(msg: Msg) -> None:
            await self._dispatch(route, msg)

        return callback

    async def _dispatch(self, route: Route, msg: Msg) -> None:
        payload: dict[str, Any] = {}
        decode_error: InvalidPayloadError | None = None
        try:
            payload = decode_payload(msg.data)
        except InvalidPayloadError as exc:
            decode_error = exc

        correlation_id = resolve_correlation_id(msg.headers, payload)
        with correlation_scope(correlation_id):
            log.info(
                "event_received",
                subject=msg.subject,
                kind=route.kind.value,
                size=len(msg.data),
                has_reply=bool(msg.reply),
            )
            if route.kind is RouteKind.QUERY and not msg.reply:
                log.warning("query_ignored_without_reply", subject=msg.subject)
                return

            ok, envelope = await self._execute(route, payload, decode_error, correlation_id)
            await self._send(route, msg, ok, envelope, correlation_id)

    async def _execute(
        self,
        route: Route,
        payload: dict[str, Any],
        decode_error: InvalidPayloadError | None,
        correlation_id: str,
    ) -> tuple[bool, bytes]:
        try:
            if decode_error is not None:
                raise decode_error
            log.info("use_case_started", use_case=route.use_case)
            data = await asyncio.wait_for(route.handler(payload), timeout=self._timeout)
            log.info("use_case_completed", use_case=route.use_case)
            return True, ok_envelope(correlation_id, data)
        except Exception as exc:
            code, message, unexpected = to_error(exc)
            if unexpected:
                log.exception("use_case_failed", use_case=route.use_case, error_code=code)
            else:
                log.warning("use_case_rejected", use_case=route.use_case, error_code=code, error=message)
            return False, error_envelope(correlation_id, code, message, subject=route.subject)

    async def _send(
        self, route: Route, msg: Msg, ok: bool, envelope: bytes, correlation_id: str
    ) -> None:
        headers = {CORRELATION_HEADER: correlation_id}
        nc = self._nats_client.nc
        try:
            if msg.reply:
                await nc.publish(msg.reply, envelope, headers=headers)
                log.info("reply_sent", ok=ok, reply=msg.reply)
            elif not ok:
                # Fire-and-forget command that failed: nobody is waiting, so publish the error.
                await nc.publish(subjects.ERRORS, envelope, headers=headers)
                log.info("error_published", subject=subjects.ERRORS, source=route.subject)
        except Exception:
            log.exception("response_failed", subject=route.subject)
