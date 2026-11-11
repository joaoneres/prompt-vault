from types import TracebackType
from typing import Protocol, Self

from .prompt_repository import PromptRepository


class UnitOfWork(Protocol):
    """Transactional boundary. Leaving the block without `commit()` must roll back."""

    prompts: PromptRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
