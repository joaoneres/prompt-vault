from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .status import PromptStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Immutable fact about something that happened to a prompt."""

    prompt_id: UUID
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptCreated(DomainEvent):
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptVersionAdded(DomainEvent):
    version_number: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptVersionActivated(DomainEvent):
    version_number: int
    previous_version_number: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptDeactivated(DomainEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptReactivated(DomainEvent):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptDeleted(DomainEvent):
    previous_status: PromptStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class PromptRestored(DomainEvent):
    restored_status: PromptStatus
