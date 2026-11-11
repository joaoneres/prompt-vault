# Prompt Vault

Versioned prompt management, in three projects: a React front, an HTTP API and a core that the API reaches over [NATS](https://nats.io/):

```text
front (React) → api (FastAPI) ──NATS request/reply──▶ core (hexagonal, SQLite)
```

| Folder | Role | Docs |
|---|---|---|
| [`core/`](core) | Domain and use cases (create, version, activate, compare, soft delete). Listens on NATS subjects and persists in SQLite. | [`core/README.md`](core/README.md) |
| [`front/`](front) | Dashboard to list, search, create, edit, delete/recover, compare and browse the version history of prompts, activating any version (React + Vite + TypeScript + Tailwind + Axios). Talks only to the API. | [`front/README.md`](front/README.md) |
| [`api/`](api) | HTTP gateway. Validates input, sends one NATS message per use case and returns the Core's `data` as is. | [`api/CLAUDE.md`](api/CLAUDE.md) |

## Quick start

Requirements: Docker, `uv`, Python 3.13 and Node.js 22 (see [Environment setup](#environment-setup)).

```bash
# 1. NATS
cd core && docker compose up -d

# 2. Core (terminal 1)
cd core && uv sync && uv run src/main.py

# 3. API (terminal 2)
cd api && uv sync && uv run uvicorn main:app --reload

# 4. Front (terminal 3)
cd front && npm install && npm run dev
```

Front: http://localhost:5173 (Vite forwards `/api` to the API on port 8000, which has no CORS).

Swagger UI: http://localhost:8000/docs · ReDoc: http://localhost:8000/redoc

The API fails at startup if NATS is down. Without the Core running, calls return `503 CORE_UNAVAILABLE` or `504 CORE_TIMEOUT`.

| Variable | Used by | Default |
|---|---|---|
| `NATS_URL` | core, api | `nats://localhost:4222` |
| `DATABASE_URL` | core | `sqlite+aiosqlite:///./prompt_vault.db` |
| `LOG_LEVEL` | core, api | `INFO` |
| `HANDLER_TIMEOUT_SECONDS` | core | `5` |

## API

Every success returns **HTTP 200** with the Core's `data` as the body (an object, or an array for listings). Swagger documents the DTOs (`PromptResponse`, `PromptVersionResponse`, `PromptDetailResponse`, `VersionDiffResponse`); the API does not reshape the response, and the global smoke test checks the core really produces them.

| Method | Route | Use case | NATS subject |
|---|---|---|---|
| POST | `/prompts` | create prompt | `prompt.create` |
| GET | `/prompts/active` | list active prompts | `prompt.list.active` |
| GET | `/prompts/deleted` | list deleted prompts | `prompt.list.deleted` |
| GET | `/prompts/{prompt_id}` | get prompt with versions | `prompt.get` |
| DELETE | `/prompts/{prompt_id}` | soft delete | `prompt.delete` |
| POST | `/prompts/{prompt_id}/recover` | recover | `prompt.restore` |
| POST | `/prompts/{prompt_id}/versions` | add version | `prompt.version.create` |
| GET | `/prompts/{prompt_id}/versions` | list versions | `prompt.versions.list` |
| PUT | `/prompts/{prompt_id}/content` | update content | `prompt.content.update` |
| POST | `/prompts/{prompt_id}/activate` | activate version | `prompt.version.activate` |
| POST | `/prompts/{prompt_id}/compare` | compare two versions | `prompt.versions.compare` |

### Errors

Always JSON, never a stack trace (it stays in the logs):

```json
{ "error": { "code": "PROMPT_NOT_FOUND", "message": "Prompt 123 não encontrado", "details": {} } }
```

| HTTP | Codes |
|---|---|
| 404 | `PROMPT_NOT_FOUND`, `VERSION_NOT_FOUND` |
| 409 | `PROMPT_ALREADY_DELETED`, `PROMPT_NOT_DELETED`, `DOMAIN_RULE_VIOLATION` |
| 422 | `INVALID_REQUEST` (invalid body, UUID or core payload), `INVALID_VERSION_COMPARISON` |
| 502 | `CORE_RESPONSE_ERROR` |
| 503 | `NATS_PUBLISH_FAILED`, `CORE_UNAVAILABLE` |
| 504 | `CORE_TIMEOUT` |
| 500 | `INTERNAL_SERVER_ERROR` |

## API layout

```text
api/
  main.py          # app, NATS lifespan, handler registration
  controllers/     # FastAPI router, no business logic
  services/        # PromptService: one NATS message per use case
  messaging/       # NATSPublisher, the only module that imports nats-py
  models/          # request DTOs, response DTOs and ApiWrapper[T]
  utils/           # exceptions, error handlers, json helpers, logging
  tests/
```

## Tests

```bash
cd api  && uv run pytest        # unit tests, NATS mocked, no network
cd core && ./smoke_test.sh      # core only, via NATS CLI (needs NATS and the core)
cd api  && ./smoke_test.sh      # api only, via curl (needs NATS, core and api)
./smoke_test.sh                 # global: HTTP -> api -> NATS -> core, contract and cross-checks
```

The global smoke test uses the API's virtualenv, so run `cd api && uv sync` first.

The front has no automated tests yet: `cd front && npm run build` type-checks and builds it.

The global smoke test (needs NATS, core and api running) checks that every HTTP body is valid against the API DTOs and equal to the `data` returned by the core for the same query, that both sides see the same state, that domain events are published, and that core errors reach HTTP with the right status and code.

## Environment setup

Everything on Ubuntu: Cursor, Docker Engine, uv, Python 3.13, NATS CLI 0.3.1, and Node.js 22.

### Cursor

```bash
curl -fsSL https://downloads.cursor.com/keys/anysphere.asc | gpg --dearmor | sudo tee /etc/apt/keyrings/cursor.gpg > /dev/null
echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/cursor.gpg] https://downloads.cursor.com/aptrepo stable main" | sudo tee /etc/apt/sources.list.d/cursor.list > /dev/null
sudo apt update
sudo apt install cursor
```

### Docker Engine

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
docker run hello-world
docker --version
docker compose version
```

### uv and Python 3.13

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
uv python install 3.13
uv run --python 3.13 python --version
```

### NATS CLI 0.3.1

```bash
sudo apt install -y unzip
mkdir -p ~/.local/bin
tmp=$(mktemp -d)
curl -fsSL -o "$tmp/nats.zip" https://github.com/nats-io/natscli/releases/download/v0.3.1/nats-0.3.1-linux-amd64.zip
unzip -o "$tmp/nats.zip" -d "$tmp"
install -m 0755 "$tmp/nats-0.3.1-linux-amd64/nats" ~/.local/bin/nats
rm -rf "$tmp"
source ~/.bashrc
nats --version
```

### Node.js 22

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
source ~/.bashrc
nvm install 22
node --version
npm --version
```

### Checklist

```bash
uv --version
uv run --python 3.13 python --version
nats --version
node --version
npm --version
docker --version
docker compose version
docker run hello-world
```
