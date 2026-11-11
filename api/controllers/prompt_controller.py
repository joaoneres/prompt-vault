from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from models.prompt_models import (
    ActivateVersionBody,
    ActivateVersionRequest,
    AddVersionBody,
    AddVersionRequest,
    CompareVersionsBody,
    CompareVersionsRequest,
    CreatePromptRequest,
    PromptIdRequest,
    UpdateContentBody,
    UpdateContentRequest,
)
from models.response_models import (
    PromptDetailResponse,
    PromptResponse,
    PromptVersionResponse,
    VersionDiffResponse,
)
from services.prompt_service import PromptService

router = APIRouter(prefix="/prompts", tags=["Prompts"])


def ok(model: Any) -> dict[str, Any]:
    """Documents the 200 body in Swagger without validating or reshaping it.

    The gateway returns the Core's `data` as is, so this is not a response_model.
    """
    return {"model": model}


def get_prompt_service(request: Request) -> PromptService:
    return request.app.state.prompt_service


Service = Depends(get_prompt_service)


@router.post("", responses={200: ok(PromptResponse)})
async def create_prompt(
    req: CreatePromptRequest, service: PromptService = Service
) -> Any:
    return await service.create_prompt(req)


# Fixed paths must be declared before "/{prompt_id}".
@router.get("/active", responses={200: ok(list[PromptResponse])})
async def list_active_prompts(service: PromptService = Service) -> Any:
    return await service.list_active_prompts()


@router.get("/deleted", responses={200: ok(list[PromptResponse])})
async def list_deleted_prompts(service: PromptService = Service) -> Any:
    return await service.list_deleted_prompts()


@router.get("/{prompt_id}", responses={200: ok(PromptDetailResponse)})
async def get_prompt_by_id(prompt_id: UUID, service: PromptService = Service) -> Any:
    return await service.get_prompt_by_id(PromptIdRequest(prompt_id=prompt_id))


@router.delete("/{prompt_id}", responses={200: ok(PromptResponse)})
async def soft_delete_prompt(prompt_id: UUID, service: PromptService = Service) -> Any:
    return await service.soft_delete_prompt(PromptIdRequest(prompt_id=prompt_id))


@router.post("/{prompt_id}/versions", responses={200: ok(PromptVersionResponse)})
async def add_version(
    prompt_id: UUID, body: AddVersionBody, service: PromptService = Service
) -> Any:
    return await service.add_version(AddVersionRequest(prompt_id=prompt_id, content=body.content))


@router.get("/{prompt_id}/versions", responses={200: ok(list[PromptVersionResponse])})
async def list_versions(prompt_id: UUID, service: PromptService = Service) -> Any:
    return await service.list_versions(PromptIdRequest(prompt_id=prompt_id))


@router.put("/{prompt_id}/content", responses={200: ok(PromptVersionResponse)})
async def update_content(
    prompt_id: UUID, body: UpdateContentBody, service: PromptService = Service
) -> Any:
    return await service.update_content(
        UpdateContentRequest(prompt_id=prompt_id, content=body.content)
    )


@router.post("/{prompt_id}/activate", responses={200: ok(PromptResponse)})
async def activate_version(
    prompt_id: UUID, body: ActivateVersionBody, service: PromptService = Service
) -> Any:
    return await service.activate_version(
        ActivateVersionRequest(prompt_id=prompt_id, version_number=body.version_number)
    )


@router.post("/{prompt_id}/compare", responses={200: ok(VersionDiffResponse)})
async def compare_versions(
    prompt_id: UUID, body: CompareVersionsBody, service: PromptService = Service
) -> Any:
    return await service.compare_versions(
        CompareVersionsRequest(
            prompt_id=prompt_id, from_version=body.from_version, to_version=body.to_version
        )
    )


@router.post("/{prompt_id}/recover", responses={200: ok(PromptResponse)})
async def recover_prompt(prompt_id: UUID, service: PromptService = Service) -> Any:
    return await service.recover_prompt(PromptIdRequest(prompt_id=prompt_id))
