import asyncio
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infra.logging import get_logger
from port import PromptRepository

from .prompt_repository import SqlAlchemyPromptRepository

log = get_logger(__name__)


class SqlAlchemyUnitOfWork:
    """Transaction boundary. Leaving the block without `commit()` rolls back.

    The shared `write_lock` is held for the whole block, so read-modify-write cycles never
    interleave inside this process (otherwise two commands on the same prompt could lose
    an update). SQLite allows a single writer anyway.
    """

    prompts: PromptRepository

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], write_lock: asyncio.Lock
    ) -> None:
        self._session_factory = session_factory
        self._write_lock = write_lock
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> Self:
        await self._write_lock.acquire()
        try:
            self._session = self._session_factory()
            self.prompts = SqlAlchemyPromptRepository(self._session)
            self._committed = False
        except BaseException:
            self._write_lock.release()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self._require_session()
        try:
            if not self._committed:
                await session.rollback()
                log.info("transaction_rolled_back", failed=exc_type is not None)
        finally:
            await session.close()
            self._session = None
            self._write_lock.release()

    async def commit(self) -> None:
        await self._require_session().commit()
        self._committed = True
        log.info("transaction_committed")

    async def rollback(self) -> None:
        await self._require_session().rollback()
        log.info("transaction_rolled_back", failed=False)

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork used outside of 'async with'")
        return self._session
