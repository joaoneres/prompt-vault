from unittest.mock import AsyncMock

import pytest

from messaging.nats_publisher import NATSPublisher
from models.prompt_models import (
    ActivateVersionRequest,
    AddVersionRequest,
    CompareVersionsRequest,
    CreatePromptRequest,
    PromptIdRequest,
    UpdateContentRequest,
)
from services.prompt_service import PromptService

PID = "11111111-1111-1111-1111-111111111111"
ID_ONLY = PromptIdRequest(prompt_id=PID)

CASES = [
    ("create_prompt", (CreatePromptRequest(name="n", content="c"),),
     "prompt.create", {"name": "n", "content": "c"}),
    ("add_version", (AddVersionRequest(prompt_id=PID, content="c"),),
     "prompt.version.create", {"prompt_id": PID, "content": "c"}),
    ("update_content", (UpdateContentRequest(prompt_id=PID, content="c"),),
     "prompt.content.update", {"prompt_id": PID, "content": "c"}),
    ("activate_version", (ActivateVersionRequest(prompt_id=PID, version_number=2),),
     "prompt.version.activate", {"prompt_id": PID, "version_number": 2}),
    ("soft_delete_prompt", (ID_ONLY,), "prompt.delete", {"prompt_id": PID}),
    ("recover_prompt", (ID_ONLY,), "prompt.restore", {"prompt_id": PID}),
    ("get_prompt_by_id", (ID_ONLY,), "prompt.get", {"prompt_id": PID}),
    ("list_versions", (ID_ONLY,), "prompt.versions.list", {"prompt_id": PID}),
    ("list_active_prompts", (), "prompt.list.active", {}),
    ("list_deleted_prompts", (), "prompt.list.deleted", {}),
    ("compare_versions",
     (CompareVersionsRequest(prompt_id=PID, from_version=1, to_version=3),),
     "prompt.versions.compare", {"prompt_id": PID, "from_version": 1, "to_version": 3}),
]


@pytest.fixture
def publisher() -> AsyncMock:
    mock = AsyncMock(spec=NATSPublisher)
    mock.request.return_value = {"x": 1}
    return mock


@pytest.mark.parametrize(("method", "args", "subject", "payload"), CASES)
async def test_use_case_sends_exactly_one_correct_message(publisher, method, args, subject, payload):
    result = await getattr(PromptService(publisher), method)(*args)

    publisher.request.assert_awaited_once_with(subject, payload)
    publisher.publish.assert_not_awaited()
    assert result == {"x": 1}


@pytest.mark.parametrize(("method", "args", "subject", "payload"), CASES)
async def test_payload_is_json_ready(publisher, method, args, subject, payload):
    """UUIDs must be sent as str, never as UUID objects."""
    await getattr(PromptService(publisher), method)(*args)
    sent = publisher.request.await_args.args[1]
    assert all(not hasattr(v, "hex") for v in sent.values())


async def test_service_propagates_publisher_errors(publisher):
    publisher.request.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        await PromptService(publisher).list_active_prompts()
