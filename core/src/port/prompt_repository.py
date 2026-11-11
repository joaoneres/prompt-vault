from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from domain import Prompt


class PromptRepository(Protocol):
    async def get(self, prompt_id: UUID) -> Prompt | None: ...

    async def save(self, prompt: Prompt) -> None:
        """Insert or update the whole aggregate, including all its versions."""
        ...

    async def list_active(self) -> Sequence[Prompt]:
        """Prompts whose status is ACTIVE."""
        ...

    async def list_deleted(self) -> Sequence[Prompt]:
        """Prompts whose status is DELETED (soft-deleted)."""
        ...
