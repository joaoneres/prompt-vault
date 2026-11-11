from typing import Any

from domain import Prompt, PromptVersion, VersionDiff


def version_to_dict(version: PromptVersion, *, is_active: bool | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(version.id),
        "number": version.number,
        "content": version.content,
        "created_at": version.created_at.isoformat(),
    }
    if is_active is not None:  # only known when the whole prompt is at hand
        data["is_active"] = is_active
    return data


def prompt_summary_to_dict(prompt: Prompt) -> dict[str, Any]:
    active = prompt.active_version
    return {
        "id": str(prompt.id),
        "name": prompt.name,
        "status": prompt.status.value,
        "active_version_number": active.number if active else None,
        "versions_count": len(prompt.versions),
        "is_in_use": prompt.is_in_use,
        "created_at": prompt.created_at.isoformat(),
        "updated_at": prompt.updated_at.isoformat(),
        "deleted_at": prompt.deleted_at.isoformat() if prompt.deleted_at else None,
    }


def versions_to_list(prompt: Prompt) -> list[dict[str, Any]]:
    return [
        version_to_dict(version, is_active=prompt.is_version_active(version.number))
        for version in prompt.versions
    ]


def prompt_to_dict(prompt: Prompt) -> dict[str, Any]:
    return {**prompt_summary_to_dict(prompt), "versions": versions_to_list(prompt)}


def diff_to_dict(diff: VersionDiff) -> dict[str, Any]:
    return {
        "prompt_id": str(diff.prompt_id),
        "from_version": diff.from_version,
        "to_version": diff.to_version,
        "algorithm": diff.algorithm,
        "has_changes": diff.has_changes,
        "added": diff.added_count,
        "removed": diff.removed_count,
        "modified": diff.modified_count,
        "entries": [
            {
                "change_type": entry.change_type.value,
                "old_line": entry.old_line,
                "new_line": entry.new_line,
                "old_text": entry.old_text,
                "new_text": entry.new_text,
            }
            for entry in diff.entries
        ],
    }
