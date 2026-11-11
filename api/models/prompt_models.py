from uuid import UUID

from pydantic import BaseModel


class CreatePromptRequest(BaseModel):
    name: str
    content: str


class PromptIdRequest(BaseModel):
    """Input for use cases that only need the prompt id."""

    prompt_id: UUID


class AddVersionRequest(BaseModel):
    prompt_id: UUID
    content: str


class UpdateContentRequest(BaseModel):
    prompt_id: UUID
    content: str


class ActivateVersionRequest(BaseModel):
    prompt_id: UUID
    version_number: int


class CompareVersionsRequest(BaseModel):
    prompt_id: UUID
    from_version: int
    to_version: int


# Body-only DTOs for HTTP: the prompt id comes from the path.
class AddVersionBody(BaseModel):
    content: str


class UpdateContentBody(BaseModel):
    content: str


class ActivateVersionBody(BaseModel):
    version_number: int


class CompareVersionsBody(BaseModel):
    from_version: int
    to_version: int
