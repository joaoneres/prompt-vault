import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import nats
from fastapi import FastAPI

from controllers.prompt_controller import router as prompt_router
from messaging.nats_publisher import NATSPublisher
from services.prompt_service import PromptService
from utils.error_handlers import register_exception_handlers
from utils.logger import setup_logging

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    nc = await nats.connect(NATS_URL)
    app.state.prompt_service = PromptService(NATSPublisher(nc))
    try:
        yield
    finally:
        await nc.drain()


app = FastAPI(title="Prompt Vault API", lifespan=lifespan)
app.include_router(prompt_router)

register_exception_handlers(app)
