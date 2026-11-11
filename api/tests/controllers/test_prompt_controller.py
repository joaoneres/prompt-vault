from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from controllers.prompt_controller import get_prompt_service, router
from services.prompt_service import PromptService
from utils.error_handlers import register_exception_handlers
from utils.exceptions import PromptNotFoundException

PID = "11111111-1111-1111-1111-111111111111"
RESULT = {"id": PID, "name": "n"}


@pytest.fixture
def service() -> AsyncMock:
    mock = AsyncMock(spec=PromptService)
    for name in dir(PromptService):
        if not name.startswith("_"):
            getattr(mock, name).return_value = RESULT
    return mock


@pytest.fixture
def client(service) -> TestClient:
    app = FastAPI()  # no lifespan: nothing connects to NATS
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_prompt_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


# method, url, json body, expected status (always 200 on success), service method, number of positional args
ROUTES = [
    ("POST", "/prompts", {"name": "n", "content": "c"}, 200, "create_prompt", 1),
    ("POST", f"/prompts/{PID}/versions", {"content": "c"}, 200, "add_version", 1),
    ("PUT", f"/prompts/{PID}/content", {"content": "c"}, 200, "update_content", 1),
    ("POST", f"/prompts/{PID}/activate", {"version_number": 2}, 200, "activate_version", 1),
    ("GET", "/prompts/active", None, 200, "list_active_prompts", 0),
    ("GET", "/prompts/deleted", None, 200, "list_deleted_prompts", 0),
    ("GET", f"/prompts/{PID}", None, 200, "get_prompt_by_id", 1),
    ("GET", f"/prompts/{PID}/versions", None, 200, "list_versions", 1),
    ("POST", f"/prompts/{PID}/compare", {"from_version": 1, "to_version": 2}, 200,
     "compare_versions", 1),
    ("DELETE", f"/prompts/{PID}", None, 200, "soft_delete_prompt", 1),
    ("POST", f"/prompts/{PID}/recover", None, 200, "recover_prompt", 1),
]


@pytest.mark.parametrize(("verb", "url", "body", "status", "method", "nargs"), ROUTES)
def test_endpoint_calls_service_and_returns_its_result(
    client, service, verb, url, body, status, method, nargs
):
    response = client.request(verb, url, json=body)

    assert response.status_code == status
    assert response.json() == RESULT
    getattr(service, method).assert_awaited_once()
    assert len(getattr(service, method).await_args.args) == nargs
    for other in dir(PromptService):
        if not other.startswith("_") and other != method:
            getattr(service, other).assert_not_awaited()


def test_dto_built_from_path_and_body(client, service):
    client.post(f"/prompts/{PID}/versions", json={"content": "hello"})
    dto = service.add_version.await_args.args[0]
    assert str(dto.prompt_id) == PID
    assert dto.content == "hello"


def test_compare_dto(client, service):
    client.post(f"/prompts/{PID}/compare", json={"from_version": 1, "to_version": 3})
    dto = service.compare_versions.await_args.args[0]
    assert (dto.from_version, dto.to_version) == (1, 3)


def test_fixed_paths_are_not_captured_by_prompt_id(client, service):
    assert client.get("/prompts/active").status_code == 200
    assert client.get("/prompts/deleted").status_code == 200
    service.get_prompt_by_id.assert_not_awaited()


def test_invalid_uuid_returns_standard_422(client, service):
    response = client.get("/prompts/not-a-uuid")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert error["details"]["fields"]
    service.get_prompt_by_id.assert_not_awaited()


def test_invalid_body_returns_422(client, service):
    response = client.post("/prompts", json={"name": "only-name"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    service.create_prompt.assert_not_awaited()


def test_app_exception_from_service_becomes_http_error(client, service):
    service.get_prompt_by_id.side_effect = PromptNotFoundException(PID)
    response = client.get(f"/prompts/{PID}")
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "PROMPT_NOT_FOUND",
            "message": f"Prompt {PID} não encontrado",
            "details": {},
        }
    }


def test_unexpected_error_is_hidden(client, service):
    service.get_prompt_by_id.side_effect = RuntimeError("secret internals")
    response = client.get(f"/prompts/{PID}")
    assert response.status_code == 500
    assert "secret" not in response.text


def test_list_endpoints_return_json_arrays(client, service):
    service.list_active_prompts.return_value = [{"id": "1"}, {"id": "2"}]
    response = client.get("/prompts/active")
    assert response.status_code == 200
    assert response.json() == [{"id": "1"}, {"id": "2"}]


def test_response_body_is_passed_through_untouched(client, service):
    data = {"id": PID, "unknown_field": [1, 2], "created_at": "2026-01-02T03:04:05"}
    service.get_prompt_by_id.return_value = data
    assert client.get(f"/prompts/{PID}").json() == data


def test_openapi_documents_response_models(client):
    paths = client.app.openapi()["paths"]
    ref = paths["/prompts"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert ref["$ref"].endswith("PromptResponse")
    assert "201" not in paths["/prompts"]["post"]["responses"]
