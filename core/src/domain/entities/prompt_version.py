from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from ..exceptions import InvalidPromptError


@dataclass(frozen=True, slots=True)
class PromptVersion:
    """Immutable snapshot of a prompt's content.

    Versions are never edited or removed; a change in content is a new version.
    Which version is in use is decided by the owning Prompt, not by the version.
    """

    number: int
    content: str
    created_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.number < 1:
            raise InvalidPromptError("Version number must be >= 1")
        if not self.content.strip():
            raise InvalidPromptError("Version content cannot be blank")
