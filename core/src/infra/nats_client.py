import nats
from nats.aio.client import Client

from .logging import get_logger
from .settings import Settings

log = get_logger(__name__)


class NatsClient:
    """Owns the NATS connection and its lifecycle logging."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._nc: Client | None = None

    @property
    def nc(self) -> Client:
        if self._nc is None:
            raise RuntimeError("NatsClient is not connected")
        return self._nc

    async def connect(self) -> None:
        async def error_cb(exc: Exception) -> None:
            log.error("nats_error", error=repr(exc))

        async def disconnected_cb() -> None:
            log.warning("nats_disconnected")

        async def reconnected_cb() -> None:
            connected_url = self.nc.connected_url
            log.info("nats_reconnected", url=connected_url.netloc if connected_url else None)

        async def closed_cb() -> None:
            log.info("nats_closed")

        self._nc = await nats.connect(
            self._settings.nats_url,
            name="prompt-vault",
            max_reconnect_attempts=-1,
            error_cb=error_cb,
            disconnected_cb=disconnected_cb,
            reconnected_cb=reconnected_cb,
            closed_cb=closed_cb,
        )
        log.info("nats_connected", url=self._settings.nats_url)

    async def close(self) -> None:
        if self._nc is not None and not self._nc.is_closed:
            await self._nc.drain()
