from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from domain import Prompt, PromptStatus
from infra.logging import get_logger

from .mapper import apply_state, to_domain, to_new_row, version_to_row
from .models import PromptModel

log = get_logger(__name__)


class SqlAlchemyPromptRepository:
    """PromptRepository bound to one session (and therefore to one unit of work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, prompt_id: UUID) -> Prompt | None:
        row = await self._fetch_row(str(prompt_id))
        return to_domain(row) if row else None

    async def save(self, prompt: Prompt) -> None:
        row = await self._fetch_row(str(prompt.id))
        if row is None:
            self._session.add(to_new_row(prompt))
        else:
            apply_state(row, prompt)
            stored_numbers = {version.number for version in row.versions}
            # History is append-only: only versions that are not stored yet are inserted.
            for version in prompt.versions:
                if version.number not in stored_numbers:
                    row.versions.append(version_to_row(prompt.id, version))
        await self._session.flush()
        log.info("prompt_saved", prompt_id=str(prompt.id), versions=len(prompt.versions))

    async def list_active(self) -> Sequence[Prompt]:
        return await self._list_by_status(PromptStatus.ACTIVE)

    async def list_deleted(self) -> Sequence[Prompt]:
        return await self._list_by_status(PromptStatus.DELETED)

    async def _fetch_row(self, prompt_id: str) -> PromptModel | None:
        statement = (
            select(PromptModel)
            .where(PromptModel.id == prompt_id)
            .options(selectinload(PromptModel.versions))
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def _list_by_status(self, status: PromptStatus) -> list[Prompt]:
        statement = (
            select(PromptModel)
            .where(PromptModel.status == status.value)
            .options(selectinload(PromptModel.versions))
            .order_by(PromptModel.created_at, PromptModel.id)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return [to_domain(row) for row in rows]


class SessionPerCallPromptRepository:
    """Read-side repository: every call opens (and closes) its own short session.

    Used by the query use cases, which don't need a transaction. Writes must go through
    SqlAlchemyUnitOfWork, so `save` is deliberately not supported here.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, prompt_id: UUID) -> Prompt | None:
        async with self._session_factory() as session:
            return await SqlAlchemyPromptRepository(session).get(prompt_id)

    async def save(self, prompt: Prompt) -> None:
        raise NotImplementedError("Read-only repository: save through SqlAlchemyUnitOfWork")

    async def list_active(self) -> Sequence[Prompt]:
        async with self._session_factory() as session:
            return await SqlAlchemyPromptRepository(session).list_active()

    async def list_deleted(self) -> Sequence[Prompt]:
        async with self._session_factory() as session:
            return await SqlAlchemyPromptRepository(session).list_deleted()
