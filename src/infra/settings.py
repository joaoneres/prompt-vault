import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    nats_url: str = "nats://localhost:4222"
    database_url: str = "sqlite+aiosqlite:///./prompt_vault.db"
    log_level: str = "INFO"
    handler_timeout_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            nats_url=os.environ.get("NATS_URL", defaults.nats_url),
            database_url=os.environ.get("DATABASE_URL", defaults.database_url),
            log_level=os.environ.get("LOG_LEVEL", defaults.log_level),
            handler_timeout_seconds=float(
                os.environ.get("HANDLER_TIMEOUT_SECONDS", defaults.handler_timeout_seconds)
            ),
        )
