from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.commands import (
    ActivateVersionCommand,
    ActivateVersionUseCase,
    CreatePromptCommand,
    CreatePromptUseCase,
    CreateVersionCommand,
    CreateVersionUseCase,
    DeletePromptCommand,
    DeletePromptUseCase,
    RestorePromptCommand,
    RestorePromptUseCase,
    UpdateContentCommand,
    UpdateContentUseCase,
)
from app.queries import (
    CompareVersionsQuery,
    CompareVersionsUseCase,
    GetPromptQuery,
    GetPromptUseCase,
    ListActivePromptsUseCase,
    ListDeletedPromptsUseCase,
    ListVersionsQuery,
    ListVersionsUseCase,
)

from . import subjects
from .codec import optional_bool, require_int, require_str, require_uuid
from .serializers import diff_to_dict, prompt_summary_to_dict, prompt_to_dict, version_to_dict

Handler = Callable[[dict[str, Any]], Awaitable[Any]]


class RouteKind(StrEnum):
    COMMAND = "command"
    QUERY = "query"


@dataclass(frozen=True, slots=True)
class Route:
    subject: str
    kind: RouteKind
    use_case: str
    handler: Handler


@dataclass(frozen=True, slots=True)
class UseCaseFactories:
    """One factory per use case: each message gets a fresh instance (and its own session)."""

    create_prompt: Callable[[], CreatePromptUseCase]
    create_version: Callable[[], CreateVersionUseCase]
    update_content: Callable[[], UpdateContentUseCase]
    activate_version: Callable[[], ActivateVersionUseCase]
    delete_prompt: Callable[[], DeletePromptUseCase]
    restore_prompt: Callable[[], RestorePromptUseCase]
    get_prompt: Callable[[], GetPromptUseCase]
    list_versions: Callable[[], ListVersionsUseCase]
    list_active_prompts: Callable[[], ListActivePromptsUseCase]
    list_deleted_prompts: Callable[[], ListDeletedPromptsUseCase]
    compare_versions: Callable[[], CompareVersionsUseCase]


def build_routes(factories: UseCaseFactories) -> list[Route]:
    """Translate payloads into use case inputs and results into plain data. No business rules."""

    async def create_prompt(p: dict[str, Any]) -> Any:
        command = CreatePromptCommand(name=require_str(p, "name"), content=require_str(p, "content"))
        return {"prompt_id": str(await factories.create_prompt().execute(command))}

    async def create_version(p: dict[str, Any]) -> Any:
        command = CreateVersionCommand(
            prompt_id=require_uuid(p, "prompt_id"),
            content=require_str(p, "content"),
            activate=optional_bool(p, "activate"),
        )
        return {"version_number": await factories.create_version().execute(command)}

    async def update_content(p: dict[str, Any]) -> Any:
        command = UpdateContentCommand(
            prompt_id=require_uuid(p, "prompt_id"), content=require_str(p, "content")
        )
        return {"version_number": await factories.update_content().execute(command)}

    async def activate_version(p: dict[str, Any]) -> Any:
        command = ActivateVersionCommand(
            prompt_id=require_uuid(p, "prompt_id"), version_number=require_int(p, "version_number")
        )
        await factories.activate_version().execute(command)

    async def delete_prompt(p: dict[str, Any]) -> Any:
        await factories.delete_prompt().execute(DeletePromptCommand(require_uuid(p, "prompt_id")))

    async def restore_prompt(p: dict[str, Any]) -> Any:
        await factories.restore_prompt().execute(RestorePromptCommand(require_uuid(p, "prompt_id")))

    async def get_prompt(p: dict[str, Any]) -> Any:
        prompt = await factories.get_prompt().execute(GetPromptQuery(require_uuid(p, "prompt_id")))
        return prompt_to_dict(prompt)

    async def list_versions(p: dict[str, Any]) -> Any:
        prompt_id = require_uuid(p, "prompt_id")
        versions = await factories.list_versions().execute(ListVersionsQuery(prompt_id))
        return {
            "prompt_id": str(prompt_id),
            "versions": [version_to_dict(version) for version in versions],
        }

    async def list_active(_: dict[str, Any]) -> Any:
        prompts = await factories.list_active_prompts().execute()
        return {"prompts": [prompt_summary_to_dict(prompt) for prompt in prompts]}

    async def list_deleted(_: dict[str, Any]) -> Any:
        prompts = await factories.list_deleted_prompts().execute()
        return {"prompts": [prompt_summary_to_dict(prompt) for prompt in prompts]}

    async def compare_versions(p: dict[str, Any]) -> Any:
        query = CompareVersionsQuery(
            prompt_id=require_uuid(p, "prompt_id"),
            from_version=require_int(p, "from_version"),
            to_version=require_int(p, "to_version"),
        )
        return diff_to_dict(await factories.compare_versions().execute(query))

    command, query = RouteKind.COMMAND, RouteKind.QUERY
    return [
        Route(subjects.PROMPT_CREATE, command, "CreatePrompt", create_prompt),
        Route(subjects.PROMPT_VERSION_CREATE, command, "CreateVersion", create_version),
        Route(subjects.PROMPT_CONTENT_UPDATE, command, "UpdateContent", update_content),
        Route(subjects.PROMPT_VERSION_ACTIVATE, command, "ActivateVersion", activate_version),
        Route(subjects.PROMPT_DELETE, command, "DeletePrompt", delete_prompt),
        Route(subjects.PROMPT_RESTORE, command, "RestorePrompt", restore_prompt),
        Route(subjects.PROMPT_GET, query, "GetPrompt", get_prompt),
        Route(subjects.PROMPT_VERSIONS_LIST, query, "ListVersions", list_versions),
        Route(subjects.PROMPT_LIST_ACTIVE, query, "ListActivePrompts", list_active),
        Route(subjects.PROMPT_LIST_DELETED, query, "ListDeletedPrompts", list_deleted),
        Route(subjects.PROMPT_VERSIONS_COMPARE, query, "CompareVersions", compare_versions),
    ]
