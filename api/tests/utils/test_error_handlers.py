import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from utils.error_handlers import register_exception_handlers
from utils.exceptions import BaseAppException, PromptNotFoundException


class Body(BaseModel):
    n: int


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-error")
    async def app_error():
        raise BaseAppException("Falhou", "CUSTOM", 418, {"k": "v"})

    @app.get("/not-found")
    async def not_found():
        raise PromptNotFoundException("42")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internals")

    @app.post("/validate")
    async def validate(body: Body):
        return body

    return TestClient(app, raise_server_exceptions=False)


def test_app_exception_response(client):
    response = client.get("/app-error")
    assert response.status_code == 418
    assert response.json() == {"error": {"code": "CUSTOM", "message": "Falhou", "details": {"k": "v"}}}


def test_specific_exception_response(client):
    response = client.get("/not-found")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROMPT_NOT_FOUND"
    assert response.json()["error"]["details"] == {}


def test_validation_error_response(client):
    response = client.post("/validate", json={"n": "abc"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert error["details"]["fields"][0]["campo"] == "body.n"


def test_unhandled_exception_is_generic_and_logged(client, caplog):
    with caplog.at_level(logging.ERROR):
        response = client.get("/boom")
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Erro interno do servidor",
            "details": {},
        }
    }
    assert "secret" not in response.text
    assert "Traceback" not in response.text
    assert any(r.exc_info for r in caplog.records)  # traceback stays in the logs
