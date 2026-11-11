from typing import Protocol

from .models import DiffEntry


class DiffStrategy(Protocol):
    """Extension point: any algorithm (line, word, semantic...) that compares two texts."""

    name: str

    def diff(self, old: str, new: str) -> tuple[DiffEntry, ...]: ...
