from uuid import UUID

from domain import Prompt, PromptStatus, PromptVersion

from .models import PromptModel, PromptVersionModel


def to_domain(row: PromptModel) -> Prompt:
    versions = [
        PromptVersion(
            id=UUID(version.id),
            number=version.number,
            content=version.content,
            created_at=version.created_at,
        )
        for version in row.versions
    ]
    status_before_deletion = row.status_before_deletion
    return Prompt.rehydrate(
        id=UUID(row.id),
        name=row.name,
        status=PromptStatus(row.status),
        versions=versions,
        active_version_number=row.active_version_number,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        status_before_deletion=(
            PromptStatus(status_before_deletion) if status_before_deletion else None
        ),
    )


def version_to_row(prompt_id: UUID, version: PromptVersion) -> PromptVersionModel:
    return PromptVersionModel(
        id=str(version.id),
        prompt_id=str(prompt_id),
        number=version.number,
        content=version.content,
        created_at=version.created_at,
    )


def to_new_row(prompt: Prompt) -> PromptModel:
    row = PromptModel(id=str(prompt.id), created_at=prompt.created_at)
    apply_state(row, prompt)
    row.versions = [version_to_row(prompt.id, version) for version in prompt.versions]
    return row


def apply_state(row: PromptModel, prompt: Prompt) -> None:
    """Copy the mutable state of the aggregate into its row (versions are handled apart)."""
    active = prompt.active_version
    before_deletion = prompt.status_before_deletion
    row.name = prompt.name
    row.status = prompt.status.value
    row.active_version_number = active.number if active else None
    row.status_before_deletion = before_deletion.value if before_deletion else None
    row.updated_at = prompt.updated_at
    row.deleted_at = prompt.deleted_at
