from datetime import UTC, datetime
from uuid import UUID, uuid4

from ..diff import DiffStrategy, VersionDiff
from ..events import (
    DomainEvent,
    PromptCreated,
    PromptDeactivated,
    PromptDeleted,
    PromptReactivated,
    PromptRestored,
    PromptVersionActivated,
    PromptVersionAdded,
)
from ..exceptions import (
    InvalidPromptError,
    InvalidStateTransitionError,
    InvalidVersionComparisonError,
    PromptDeletedError,
    PromptNotDeletedError,
    VersionNotFoundError,
)
from ..status import PromptStatus
from .prompt_version import PromptVersion


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Prompt:
    """Aggregate root: owns the version history and the lifecycle state.

    All changes go through its methods, which enforce the invariants and record
    domain events (see `pull_events`) for a future event-driven architecture.
    """

    def __init__(
        self,
        *,
        id: UUID,
        name: str,
        status: PromptStatus,
        versions: list[PromptVersion],
        active_version_number: int | None,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
        status_before_deletion: PromptStatus | None = None,
    ) -> None:
        """Low-level constructor. Prefer `create` (new) or `rehydrate` (stored)."""
        if not name.strip():
            raise InvalidPromptError("Prompt name cannot be blank")
        if not versions:
            raise InvalidPromptError("A prompt must have at least one version")
        if [v.number for v in versions] != list(range(1, len(versions) + 1)):
            raise InvalidPromptError("Version numbers must be sequential, starting at 1")
        if active_version_number is not None and not 1 <= active_version_number <= len(versions):
            raise InvalidPromptError("Active version does not exist in this prompt")
        if (status is PromptStatus.DELETED) != (deleted_at is not None):
            raise InvalidPromptError("deleted_at must be set if, and only if, the prompt is deleted")

        self._id = id
        self._name = name.strip()
        self._status = status
        self._versions = list(versions)
        self._active_version_number = active_version_number
        self._created_at = created_at
        self._updated_at = updated_at
        self._deleted_at = deleted_at
        self._status_before_deletion = status_before_deletion
        self._events: list[DomainEvent] = []

    # ------------------------------------------------------------------ factories

    @classmethod
    def create(cls, name: str, content: str) -> "Prompt":
        """Create a new active prompt whose first version is already active."""
        now = _utcnow()
        prompt_id = uuid4()
        prompt = cls(
            id=prompt_id,
            name=name,
            status=PromptStatus.ACTIVE,
            versions=[PromptVersion(number=1, content=content, created_at=now)],
            active_version_number=1,
            created_at=now,
            updated_at=now,
        )
        prompt._record(PromptCreated(prompt_id=prompt_id, occurred_at=now, name=prompt.name))
        return prompt

    @classmethod
    def rehydrate(
        cls,
        *,
        id: UUID,
        name: str,
        status: PromptStatus,
        versions: list[PromptVersion],
        active_version_number: int | None,
        created_at: datetime,
        updated_at: datetime,
        deleted_at: datetime | None = None,
        status_before_deletion: PromptStatus | None = None,
    ) -> "Prompt":
        """Rebuild a prompt from stored state. Validates invariants, emits no events."""
        return cls(
            id=id,
            name=name,
            status=status,
            versions=versions,
            active_version_number=active_version_number,
            created_at=created_at,
            updated_at=updated_at,
            deleted_at=deleted_at,
            status_before_deletion=status_before_deletion,
        )

    # ------------------------------------------------------------------ read model

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> PromptStatus:
        return self._status

    @property
    def versions(self) -> tuple[PromptVersion, ...]:
        return tuple(self._versions)

    @property
    def latest_version(self) -> PromptVersion:
        return self._versions[-1]

    @property
    def active_version(self) -> PromptVersion | None:
        if self._active_version_number is None:
            return None
        return self._versions[self._active_version_number - 1]

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def deleted_at(self) -> datetime | None:
        return self._deleted_at

    @property
    def status_before_deletion(self) -> PromptStatus | None:
        return self._status_before_deletion

    @property
    def is_active(self) -> bool:
        return self._status is PromptStatus.ACTIVE

    @property
    def is_deleted(self) -> bool:
        return self._status is PromptStatus.DELETED

    @property
    def is_in_use(self) -> bool:
        """True when the prompt is active and has a version selected to be served."""
        return self.is_active and self._active_version_number is not None

    def get_version(self, number: int) -> PromptVersion:
        if not 1 <= number <= len(self._versions):
            raise VersionNotFoundError(number)
        return self._versions[number - 1]

    def is_version_active(self, number: int) -> bool:
        return number == self._active_version_number

    def diff(self, from_number: int, to_number: int, strategy: DiffStrategy) -> VersionDiff:
        """Compare two distinct existing versions. Read-only: no state change, no events."""
        if from_number == to_number:
            raise InvalidVersionComparisonError(from_number)
        old = self.get_version(from_number)
        new = self.get_version(to_number)
        return VersionDiff(
            prompt_id=self._id,
            from_version=from_number,
            to_version=to_number,
            algorithm=strategy.name,
            entries=strategy.diff(old.content, new.content),
        )

    # ------------------------------------------------------------------ versioning

    def add_version(self, content: str, *, activate: bool = False) -> PromptVersion:
        """Append a new version. It becomes the active one only if `activate` is set."""
        self._ensure_not_deleted("add a version to")
        now = _utcnow()
        version = PromptVersion(number=len(self._versions) + 1, content=content, created_at=now)
        self._versions.append(version)
        self._touch(now)
        self._record(
            PromptVersionAdded(prompt_id=self._id, occurred_at=now, version_number=version.number)
        )
        if activate:
            self.activate_version(version.number)
        return version

    def activate_version(self, number: int) -> None:
        """Make `number` the version in use. No-op if it already is."""
        self._ensure_not_deleted("activate a version of")
        self.get_version(number)
        if self.is_version_active(number):
            return
        now = _utcnow()
        previous = self._active_version_number
        self._active_version_number = number
        self._touch(now)
        self._record(
            PromptVersionActivated(
                prompt_id=self._id,
                occurred_at=now,
                version_number=number,
                previous_version_number=previous,
            )
        )

    # ------------------------------------------------------------------ lifecycle

    def deactivate(self) -> None:
        self._ensure_not_deleted("deactivate")
        now = self._transition_to(PromptStatus.INACTIVE)
        self._record(PromptDeactivated(prompt_id=self._id, occurred_at=now))

    def reactivate(self) -> None:
        self._ensure_not_deleted("reactivate")
        now = self._transition_to(PromptStatus.ACTIVE)
        self._record(PromptReactivated(prompt_id=self._id, occurred_at=now))

    def delete(self) -> None:
        """Soft delete: all versions are kept and the prompt can be restored."""
        previous = self._status
        now = self._transition_to(PromptStatus.DELETED)
        self._status_before_deletion = previous
        self._deleted_at = now
        self._record(PromptDeleted(prompt_id=self._id, occurred_at=now, previous_status=previous))

    def restore(self) -> None:
        """Undo a soft delete, going back to the status the prompt had before it."""
        if not self.is_deleted:
            raise PromptNotDeletedError()
        target = self._status_before_deletion or PromptStatus.INACTIVE
        now = self._transition_to(target)
        self._status_before_deletion = None
        self._deleted_at = None
        self._record(PromptRestored(prompt_id=self._id, occurred_at=now, restored_status=target))

    # ------------------------------------------------------------------ events

    def pull_events(self) -> list[DomainEvent]:
        """Return and clear the events recorded since the last pull."""
        events, self._events = self._events, []
        return events

    # ------------------------------------------------------------------ internals

    def _transition_to(self, target: PromptStatus) -> datetime:
        if not self._status.can_transition_to(target):
            raise InvalidStateTransitionError(self._status, target)
        now = _utcnow()
        self._status = target
        self._touch(now)
        return now

    def _ensure_not_deleted(self, action: str) -> None:
        if self.is_deleted:
            raise PromptDeletedError(action)

    def _touch(self, now: datetime) -> None:
        self._updated_at = now

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def __repr__(self) -> str:
        return (
            f"Prompt(id={self._id}, name={self._name!r}, status={self._status.value}, "
            f"versions={len(self._versions)}, active_version={self._active_version_number})"
        )
