from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class DiffEntry:
    """One position in a diff. Line numbers are 1-based; a missing side is None.

    ADDED has only the new side, REMOVED only the old side, MODIFIED and
    UNCHANGED have both.
    """

    change_type: ChangeType
    old_line: int | None = None
    new_line: int | None = None
    old_text: str | None = None
    new_text: str | None = None


@dataclass(frozen=True, slots=True)
class VersionDiff:
    """Technology-neutral result of comparing two versions of a prompt.

    `entries` follow the order of the text, so the position of each change is kept.
    """

    prompt_id: UUID
    from_version: int
    to_version: int
    algorithm: str
    entries: tuple[DiffEntry, ...]

    def _count(self, change_type: ChangeType) -> int:
        return sum(1 for entry in self.entries if entry.change_type is change_type)

    @property
    def added_count(self) -> int:
        return self._count(ChangeType.ADDED)

    @property
    def removed_count(self) -> int:
        return self._count(ChangeType.REMOVED)

    @property
    def modified_count(self) -> int:
        return self._count(ChangeType.MODIFIED)

    @property
    def has_changes(self) -> bool:
        return any(entry.change_type is not ChangeType.UNCHANGED for entry in self.entries)
