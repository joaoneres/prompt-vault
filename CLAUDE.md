# CLAUDE.md

## Commands

The project is managed exclusively with `uv` (Python 3.13, pinned in `.python-version`):

```bash
uv sync                 # install dependencies from uv.lock into .venv
uv run src/main.py      # run the entry point
uv add <pkg>            # add a dependency (updates pyproject.toml and uv.lock)
uv add --dev <pkg>      # add a dev-only dependency (e.g. pytest, ruff)
```

## Project structure

- It's a hexagonal architecture

```text
src/
  app/ # Application layer (use cases)
  domain/ # Pure Core (DTOs, models, entities, NO INFRA)
  adapters/ # Library Connectors, External Clients and Port Implementations
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

```python
# Good snippet
```
```python
# Bad snippet
```

### Design patterns

- Strategy Pattern, implemented with Factories and Decorators

### Naming conventions

- snake_case for functions, variables, folders and files

## Boundaries

- Never commit files containing PII
- Never commit files containing secrets
- Never modify the /config layer
- Never delete failing unit tests