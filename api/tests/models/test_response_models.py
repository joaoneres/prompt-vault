import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from models.response_models import (
    ApiWrapper,
    PromptDetailResponse,
    PromptResponse,
    PromptVersionResponse,
    VersionDiffResponse,
)

ID = "11111111-1111-1111-1111-111111111111"
NOW = "2026-01-02T03:04:05"
PROMPT = {"id": ID, "name": "n", "status": "active", "active_version_id": ID,
          "created_at": NOW, "updated_at": NOW}
VERSION = {"id": ID, "prompt_id": ID, "version_number": 1, "content": "c",
           "created_at": NOW, "is_active": True}


def test_wrapper_is_generic_over_the_data_type():
    wrapped = ApiWrapper[PromptResponse].model_validate({"ok": True, "data": PROMPT})
    assert isinstance(wrapped.data, PromptResponse)
    assert wrapped.data.id == UUID(ID)


def test_wrapper_with_list_data():
    wrapped = ApiWrapper[list[PromptVersionResponse]].model_validate(
        {"ok": True, "data": [VERSION, VERSION]}
    )
    assert len(wrapped.data) == 2


def test_wrapper_requires_ok():
    with pytest.raises(ValidationError):
        ApiWrapper[PromptResponse].model_validate({"data": PROMPT})


def test_prompt_response_content_is_optional_and_field_names_are_kept():
    prompt = PromptResponse.model_validate(PROMPT)
    assert prompt.content is None
    assert set(json.loads(prompt.model_dump_json())) >= {
        "id", "name", "status", "active_version_id", "created_at", "updated_at"
    }


def test_detail_has_versions():
    detail = PromptDetailResponse.model_validate({**{k: PROMPT[k] for k in PROMPT}, "versions": [VERSION]})
    assert detail.versions[0].version_number == 1


def test_version_diff():
    diff = VersionDiffResponse.model_validate({
        "prompt_id": ID, "version_id_before": ID, "version_id_after": ID,
        "version_number_before": 1, "version_number_after": 2, "has_changes": True,
        "lines": [{"kind": "added", "content": "x", "line_number_before": None, "line_number_after": 1}],
    })
    assert diff.lines[0].line_number_before is None
