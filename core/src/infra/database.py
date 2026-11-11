from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by the ORM models that live in the adapters."""


def create_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(database_url)

    if engine.url.get_backend_name() == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _configure_sqlite(dbapi_connection, _record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # readers don't block the writer
            cursor.execute("PRAGMA synchronous=NORMAL")  # safe with WAL, much faster
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")  # wait for locks instead of failing
            cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create the tables. The ORM models must be imported before calling this."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
