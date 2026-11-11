from uuid import UUID

import pytest
from pydantic import ValidationError

from models.prompt_models import (
    ActivateVersionRequest,
    AddVersionRequest,
    CompareVersionsRequest,
    CreatePromptRequest,
    PromptIdRequest,
)

PID = "11111111-1111-1111-1111-111111111111"


def test_prompt_id_is_parsed_as_uuid():
    assert PromptIdRequest(prompt_id=PID).prompt_id == UUID(PID)


def test_invalid_uuid_is_rejected():
    with pytest.raises(ValidationError):
        PromptIdRequest(prompt_id="abc")


def test_missing_field_is_rejected():
    with pytest.raises(ValidationError):
        CreatePromptRequest(name="x")


def test_add_version_requires_content():
    with pytest.raises(ValidationError):
        AddVersionRequest(prompt_id=PID)


def test_activate_version_requires_integer():
    with pytest.raises(ValidationError):
        ActivateVersionRequest(prompt_id=PID, version_number="abc")


def test_compare_versions_fields():
    req = CompareVersionsRequest(prompt_id=PID, from_version=1, to_version=3)
    assert (req.from_version, req.to_version) == (1, 3)
