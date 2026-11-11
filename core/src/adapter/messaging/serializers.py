"""Domain objects -> the JSON contract served in `data` (mirrors the API response DTOs)."""

from typing import Any

from domain import ChangeType, Prompt, PromptVersion, VersionDiff


def prompt_response(prompt: Prompt, *, content: str | None = None) -> dict[str, Any]:
    """PromptResponse. `content` is only sent by create_prompt."""
    active = prompt.active_version
    data: dict[str, Any] = {
        "id": str(prompt.id),
        "name": prompt.name,
        "status": prompt.status.value,
        "active_version_id": str(active.id) if active else None,
        "created_at": prompt.created_at.isoformat(),
        "updated_at": prompt.updated_at.isoformat(),
    }
    if content is not None:
        data["content"] = content
    return data


def version_response(prompt: Prompt, version: PromptVersion) -> dict[str, Any]:
    """PromptVersionResponse."""
    return {
        "id": str(version.id),
        "prompt_id": str(prompt.id),
        "version_number": version.number,
        "content": version.content,
        "created_at": version.created_at.isoformat(),
        "is_active": prompt.is_version_active(version.number),
    }


def versions_response(prompt: Prompt) -> list[dict[str, Any]]:
    return [version_response(prompt, version) for version in prompt.versions]


def prompt_detail_response(prompt: Prompt) -> dict[str, Any]:
    """PromptDetailResponse."""
    return {**prompt_response(prompt), "versions": versions_response(prompt)}


def diff_response(prompt: Prompt, diff: VersionDiff) -> dict[str, Any]:
    """VersionDiffResponse. A MODIFIED entry becomes a removed line plus an added line."""
    lines: list[dict[str, Any]] = []
    for entry in diff.entries:
        match entry.change_type:
            case ChangeType.UNCHANGED:
                lines.append(_line("unchanged", entry.new_text, entry.old_line, entry.new_line))
            case ChangeType.ADDED:
                lines.append(_line("added", entry.new_text, None, entry.new_line))
            case ChangeType.REMOVED:
                lines.append(_line("removed", entry.old_text, entry.old_line, None))
            case ChangeType.MODIFIED:
                lines.append(_line("removed", entry.old_text, entry.old_line, None))
                lines.append(_line("added", entry.new_text, None, entry.new_line))
    return {
        "prompt_id": str(diff.prompt_id),
        "version_id_before": str(prompt.get_version(diff.from_version).id),
        "version_id_after": str(prompt.get_version(diff.to_version).id),
        "version_number_before": diff.from_version,
        "version_number_after": diff.to_version,
        "lines": lines,
        "has_changes": diff.has_changes,
    }


def _line(kind: str, content: str | None, before: int | None, after: int | None) -> dict[str, Any]:
    return {
        "kind": kind,
        "content": content or "",
        "line_number_before": before,
        "line_number_after": after,
    }
