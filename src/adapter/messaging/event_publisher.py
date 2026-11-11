import dataclasses
from collections.abc import Sequence
from typing import Any

from domain import (
    DomainEvent,
    PromptCreated,
    PromptDeactivated,
    PromptDeleted,
    PromptReactivated,
    PromptRestored,
    PromptVersionActivated,
    PromptVersionAdded,
)
from infra.logging import get_logger
from infra.nats_client import NatsClient

from . import subjects
from .codec import CORRELATION_HEADER, encode
from .correlation import get_correlation_id

log = get_logger(__name__)

_EVENT_NAMES: dict[type[DomainEvent], str] = {
    PromptCreated: "created",
    PromptVersionAdded: "version_added",
    PromptVersionActivated: "version_activated",
    PromptDeactivated: "deactivated",
    PromptReactivated: "reactivated",
    PromptDeleted: "deleted",
    PromptRestored: "restored",
}


class NatsEventPublisher:
    """EventPublisher port: publishes domain events on `prompt.events.<name>`.

    It runs after the transaction has been committed, so a failure here is logged but not
    raised: the state is already saved and the caller must not be told the command failed.
    """

    def __init__(self, nats_client: NatsClient) -> None:
        self._nats_client = nats_client

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        correlation_id = get_correlation_id()
        headers = {CORRELATION_HEADER: correlation_id} if correlation_id else None
        for event in events:
            name = _EVENT_NAMES.get(type(event), type(event).__name__.lower())
            subject = f"{subjects.EVENTS_PREFIX}.{name}"
            body: dict[str, Any] = {"event": name, **dataclasses.asdict(event)}
            try:
                await self._nats_client.nc.publish(subject, encode(body), headers=headers)
                log.info("event_published", subject=subject, prompt_id=str(event.prompt_id))
            except Exception:
                log.exception("event_publish_failed", subject=subject)
