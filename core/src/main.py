"""Composition root: the only place that knows every layer and wires them together."""

import asyncio
import signal

from adapter.messaging import MessagingAdapter, NatsEventPublisher, UseCaseFactories, build_routes
from adapter.persistence import SessionPerCallPromptRepository, SqlAlchemyUnitOfWork
from app.commands import (
    ActivateVersionUseCase,
    CreatePromptUseCase,
    CreateVersionUseCase,
    DeletePromptUseCase,
    RestorePromptUseCase,
    UpdateContentUseCase,
)
from app.queries import (
    CompareVersionsUseCase,
    GetPromptUseCase,
    ListActivePromptsUseCase,
    ListDeletedPromptsUseCase,
    ListVersionsUseCase,
)
from domain import LineDiffStrategy
from infra.database import create_engine, create_session_factory, init_db
from infra.logging import configure_logging, get_logger
from infra.nats_client import NatsClient
from infra.settings import Settings


async def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    log = get_logger("main")

    engine = create_engine(settings.database_url)
    await init_db(engine)
    session_factory = create_session_factory(engine)

    nats_client = NatsClient(settings)
    try:
        await nats_client.connect()
    except Exception:
        log.exception("nats_connection_failed", url=settings.nats_url)
        await engine.dispose()
        raise SystemExit(1)

    publisher = NatsEventPublisher(nats_client)
    write_lock = asyncio.Lock()
    reader = SessionPerCallPromptRepository(session_factory)
    diff_strategy = LineDiffStrategy()

    def uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, write_lock)

    factories = UseCaseFactories(
        create_prompt=lambda: CreatePromptUseCase(uow(), publisher),
        create_version=lambda: CreateVersionUseCase(uow(), publisher),
        update_content=lambda: UpdateContentUseCase(uow(), publisher),
        activate_version=lambda: ActivateVersionUseCase(uow(), publisher),
        delete_prompt=lambda: DeletePromptUseCase(uow(), publisher),
        restore_prompt=lambda: RestorePromptUseCase(uow(), publisher),
        get_prompt=lambda: GetPromptUseCase(reader),
        list_versions=lambda: ListVersionsUseCase(reader),
        list_active_prompts=lambda: ListActivePromptsUseCase(reader),
        list_deleted_prompts=lambda: ListDeletedPromptsUseCase(reader),
        compare_versions=lambda: CompareVersionsUseCase(reader, diff_strategy),
    )
    adapter = MessagingAdapter(
        nats_client, build_routes(factories), settings.handler_timeout_seconds
    )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await adapter.start()
    log.info("prompt_vault_started", nats_url=settings.nats_url, database=settings.database_url)
    try:
        await stop.wait()
    finally:
        log.info("prompt_vault_stopping")
        await adapter.stop()
        await nats_client.close()
        await engine.dispose()
        log.info("prompt_vault_stopped")


if __name__ == "__main__":
    asyncio.run(main())
