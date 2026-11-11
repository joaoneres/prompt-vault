# Project Guidelines

## Build and Test

This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management and running code.

```bash
# Install dependencies
uv sync

# Run the application
uv run uvicorn main:app --reload

# Add a dependency
uv add <package>

# Unit tests (no network)
uv run pytest

# Smoke test (needs NATS, the core and this API running)
./smoke_test.sh
```


## Architecture

This project is a FastAPI HTTP gateway for the Prompt Vault core. It talks to the core over [NATS](https://nats.io/) request/reply and returns the `data` of the core's `ApiWrapper` envelope as the HTTP body (always 200 on success). The entry point is [`main.py`](main.py). The core (business rules and persistence) lives in [`../core`](../core).

## Project Structure

In this project we use an MVC folder structure:

```
├── main.py              # Application entry point
├── controllers/             # FastAPI routers for different API endpoints
├── services/                # Use cases: one NATS message per use case (no business rules; those live in the core)
├── messaging/               # NATSPublisher: the only module that imports nats-py
├── models/                  # Request DTOs, response DTOs and ApiWrapper[T]
├── utils/                   # Exceptions, error handlers, json helpers, logging
├── tests/                   # Unit tests (pytest, NATS mocked)
```

## Code Style

- Python >= 3.13.7; use modern type hints (e.g., `list[str]` not `List[str]`)
- Follow FastAPI conventions: define routes with `APIRouter`, use Pydantic models for request/response bodies
- Use `async def` for all route handlers and NATS message handlers
- Keep [`main.py`](main.py) as the application entry point: app creation, NATS lifespan and handler registration only

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `NATS_URL` | `nats://localhost:4222` | NATS server (the app fails at startup if it is unreachable) |
| `LOG_LEVEL` | `INFO` | logging level |

## Stack

| Layer       | Technology          |
|-------------|---------------------|
| Web framework | FastAPI            |
| Messaging   | NATS (`nats-py`)    |
| Runtime     | Python 3.13+        |
| Package mgr | uv                  |

## Project Conventions

- `pyproject.toml` is the single source of truth for dependencies and metadata—do not use `requirements.txt`
- Core error codes become `BaseAppException` subclasses in `messaging/nats_publisher.py` (`_core_error`); a dedicated code per business rule means the API never has to read the core's message text, which is only a fallback for the generic `domain_error`
- NATS subjects follow the core's naming (`prompt.create`, `prompt.versions.list`, ...); they live in `services/prompt_service.py`
- Errors are always `BaseAppException` subclasses (`utils/exceptions.py`), rendered by the handlers in `utils/error_handlers.py`; controllers never catch exceptions
- The gateway does not reshape the core's `data`; `models/response_models.py` only documents it in Swagger. The repo-root `smoke_test.sh` validates the real responses against those models
