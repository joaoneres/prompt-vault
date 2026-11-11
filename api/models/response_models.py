"""Response contract of the Core, used for the generic wrapper and the OpenAPI docs.

The gateway only transports `data`; these models describe it, they do not reshape it.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ApiWrapper[T](BaseModel):
    """Envelope every Core reply comes in. Use ApiWrapper[PromptResponse], ApiWrapper[list[...]] etc."""

    ok: bool
    data: T | None = None


class PromptResponse(BaseModel):
    id: UUID
    name: str
    status: str
    active_version_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    content: str | None = None  # only returned by create_prompt


class PromptVersionResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    version_number: int
    content: str
    created_at: datetime
    is_active: bool


class PromptDetailResponse(BaseModel):
    id: UUID
    name: str
    status: str
    active_version_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    versions: list[PromptVersionResponse]


class DiffLineResponse(BaseModel):
    kind: str
    content: str
    line_number_before: int | None = None
    line_number_after: int | None = None


class VersionDiffResponse(BaseModel):
    prompt_id: UUID
    version_id_before: UUID
    version_id_after: UUID
    version_number_before: int
    version_number_after: int
    lines: list[DiffLineResponse]
    has_changes: bool


