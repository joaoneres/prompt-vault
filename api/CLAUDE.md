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
```


## Architecture

This project is a FastAPI-based HTTP API service that communicates asynchronously via [NATS](https://nats.io/) messaging. The entry point is [`main.py`](../main.py). The project is in early scaffolding stage—features are built around FastAPI routers and NATS pub/sub patterns.

## Project Structure

In this project we use an MVC folder structure:

```
├── main.py              # Application entry point
├── controllers/             # FastAPI routers for different API endpoints
├── services/                # Business logic
├── messaging/               # NATS message handlers
├── models/                  # Pydantic models for request/response bodies
├── utils/                   # Utility functions and helpers
```

## Code Style

- Python >= 3.13.7; use modern type hints (e.g., `list[str]` not `List[str]`)
- Follow FastAPI conventions: define routes with `APIRouter`, use Pydantic models for request/response bodies
- Use `async def` for all route handlers and NATS message handlers
- Keep [`main.py`](../main.py) as the application entry point; extract routers and handlers into dedicated modules as the project grows

## Stack

| Layer       | Technology          |
|-------------|---------------------|
| Web framework | FastAPI            |
| Messaging   | NATS (`nats-py`)    |
| Runtime     | Python 3.13+        |
| Package mgr | uv                  |

## Project Conventions

- `pyproject.toml` is the single source of truth for dependencies and metadata—do not use `requirements.txt`
- NATS subjects should follow a `verb.noun` or `service.action` naming convention (e.g., `prompt.verify`)