# CLAUDE.md

## Commands

The project is managed exclusively with `uv` (Python 3.13, pinned in `.python-version`):

```bash
uv sync                 # install dependencies from uv.lock into .venv
uv run src/main.py      # run the entry point
uv add <pkg>            # add a dependency (updates pyproject.toml and uv.lock)
uv add --dev <pkg>      # add a dev-only dependency (e.g. pytest, ruff)
```

The app needs a NATS server. Settings come from environment variables:

```bash
docker compose up -d                                    # local NATS server (docker compose down to stop)
NATS_URL=nats://localhost:4222                          # default
DATABASE_URL=sqlite+aiosqlite:///./prompt_vault.db      # default
LOG_LEVEL=INFO                                          # default
HANDLER_TIMEOUT_SECONDS=5                               # default, per message
```

With NATS and the app running, `./smoke_test.sh` exercises every subject through the NATS CLI
(it creates prompts named `smoke-<id>`; `NATS_URL` points it at another server).

`src/main.py` is the composition root and `src/` is on `sys.path` when it runs. To run
anything else from the repo root, use `PYTHONPATH=src uv run python ...`.

## Project structure

- It's a hexagonal architecture

```text
src/
  app/ # Application layer (use cases)
  domain/ # Pure Core (DTOs, models, entities, NO INFRA)
  adapter/ # Library Connectors, External Clients and Port Implementations (messaging/, persistence/)
  port/ # Interfaces for inbound and outbound communication
  infra/ # DB settings, message broker...
  main.py # App initialization / Instantiations
```

## Tech stack

- Database: SQLAlchemy (async) + aiosqlite to persist prompt versions
- Messaging: NATS (nats-py) to receive prompt payloads
- Logging: structlog for structured log output
- CLI/Output: rich for terminal formatting

## Code style

### Design patterns

- Strategy Pattern, implemented with Factories and Decorators

### Naming conventions

- snake_case for functions, variables, folders and files

## Boundaries

- Never commit files containing PII
- Never commit files containing secrets
- Never delete failing unit tests

## Messaging contract

Subjects, payloads, events and configuration are listed in [`README.md`](README.md).

Replies are `{"ok": true, "correlation_id", "data"}` or `{"ok": false, "correlation_id", "error": {"code", "message"}, "subject"}`.
`data` mirrors the API response DTOs (see `adapter/messaging/serializers.py`; the API's `models/response_models.py` is the reference):

- `prompt.create`, `prompt.version.activate`, `prompt.delete`, `prompt.restore` -> `PromptResponse` (`content` only on create)
- `prompt.version.create`, `prompt.content.update` -> `PromptVersionResponse`
- `prompt.get` -> `PromptDetailResponse`
- `prompt.versions.list` -> array of `PromptVersionResponse`; `prompt.list.active` / `prompt.list.deleted` -> array of `PromptResponse`
- `prompt.versions.compare` -> `VersionDiffResponse` (a MODIFIED diff entry becomes a `removed` line plus an `added` line)

Error codes: `invalid_payload`, `not_found`, `version_not_found`, `invalid_version_comparison`, `prompt_deleted`, `prompt_not_deleted`, `invalid_prompt`, `domain_error` (other rules), `timeout`, `internal_error`. Use cases return the aggregate; only the adapter builds JSON.
