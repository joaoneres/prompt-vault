from typing import Any

from messaging.nats_publisher import NATSPublisher
from models.prompt_models import (
    ActivateVersionRequest,
    AddVersionRequest,
    CompareVersionsRequest,
    CreatePromptRequest,
    PromptIdRequest,
    UpdateContentRequest,
)

# Commands
PROMPT_CREATE = "prompt.create"
PROMPT_VERSION_CREATE = "prompt.version.create"
PROMPT_CONTENT_UPDATE = "prompt.content.update"
PROMPT_VERSION_ACTIVATE = "prompt.version.activate"
PROMPT_DELETE = "prompt.delete"
PROMPT_RESTORE = "prompt.restore"

# Queries
PROMPT_GET = "prompt.get"
PROMPT_VERSIONS_LIST = "prompt.versions.list"
PROMPT_LIST_ACTIVE = "prompt.list.active"
PROMPT_LIST_DELETED = "prompt.list.deleted"
PROMPT_VERSIONS_COMPARE = "prompt.versions.compare"


class PromptService:
    """Use cases: build the payload, pick the subject, hand it to the publisher."""

    def __init__(self, publisher: NATSPublisher) -> None:
        self.publisher = publisher

    # ---- commands

    async def create_prompt(self, req: CreatePromptRequest) -> Any:
        return await self.publisher.request(
            PROMPT_CREATE, {"name": req.name, "content": req.content}
        )

    async def add_version(self, req: AddVersionRequest) -> Any:
        return await self.publisher.request(
            PROMPT_VERSION_CREATE,
            {"prompt_id": str(req.prompt_id), "content": req.content},
        )

    async def update_content(self, req: UpdateContentRequest) -> Any:
        return await self.publisher.request(
            PROMPT_CONTENT_UPDATE,
            {"prompt_id": str(req.prompt_id), "content": req.content},
        )

    async def activate_version(self, req: ActivateVersionRequest) -> Any:
        return await self.publisher.request(
            PROMPT_VERSION_ACTIVATE,
            {"prompt_id": str(req.prompt_id), "version_number": req.version_number},
        )

    async def soft_delete_prompt(self, req: PromptIdRequest) -> Any:
        return await self.publisher.request(PROMPT_DELETE, {"prompt_id": str(req.prompt_id)})

    async def recover_prompt(self, req: PromptIdRequest) -> Any:
        return await self.publisher.request(PROMPT_RESTORE, {"prompt_id": str(req.prompt_id)})

    # ---- queries

    async def get_prompt_by_id(self, req: PromptIdRequest) -> Any:
        return await self.publisher.request(PROMPT_GET, {"prompt_id": str(req.prompt_id)})

    async def list_versions(self, req: PromptIdRequest) -> Any:
        return await self.publisher.request(
            PROMPT_VERSIONS_LIST, {"prompt_id": str(req.prompt_id)}
        )

    async def list_active_prompts(self) -> Any:
        return await self.publisher.request(PROMPT_LIST_ACTIVE, {})

    async def list_deleted_prompts(self) -> Any:
        return await self.publisher.request(PROMPT_LIST_DELETED, {})

    async def compare_versions(self, req: CompareVersionsRequest) -> Any:
        return await self.publisher.request(
            PROMPT_VERSIONS_COMPARE,
            {
                "prompt_id": str(req.prompt_id),
                "from_version": req.from_version,
                "to_version": req.to_version,
            },
        )
