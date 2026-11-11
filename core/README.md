# Prompt Vault: core

Domain and use cases of Prompt Vault: create prompts, version them, activate any version, compare
versions and soft delete/recover. It has no HTTP: it listens on [NATS](https://nats.io/) subjects and
persists in SQLite. The HTTP side is the [`api/`](../api) gateway.

Architecture and conventions are in [`CLAUDE.md`](CLAUDE.md) (hexagonal: `domain`, `app`, `port`, `adapter`, `infra`).

## Run

Needs Docker (for NATS), `uv` and Python 3.13.

```bash
docker compose up -d        # NATS on :4222 (monitoring on :8222)
uv sync
uv run src/main.py
```

| Variable | Default | Purpose |
|---|---|---|
| `NATS_URL` | `nats://localhost:4222` | NATS server |
| `DATABASE_URL` | `sqlite+aiosqlite:///./prompt_vault.db` | SQLite file (created on first run) |
| `LOG_LEVEL` | `INFO` | structlog level |
| `HANDLER_TIMEOUT_SECONDS` | `5` | Time limit per message |

## Subjects

Commands reply only when the sender provides a reply subject (request/reply). Without one they run
fire-and-forget and failures are published on `prompt.errors`. Queries need a reply subject.

| Subject | Kind | Payload | `data` in the reply |
|---|---|---|---|
| `prompt.create` | command | `name`, `content` | `PromptResponse` (with `content`) |
| `prompt.version.create` | command | `prompt_id`, `content`, optional `activate` | `PromptVersionResponse` |
| `prompt.content.update` | command | `prompt_id`, `content` (creates and activates a version) | `PromptVersionResponse` |
| `prompt.version.activate` | command | `prompt_id`, `version_number` | `PromptResponse` |
| `prompt.delete` | command | `prompt_id` | `PromptResponse` |
| `prompt.restore` | command | `prompt_id` | `PromptResponse` |
| `prompt.get` | query | `prompt_id` | `PromptDetailResponse` |
| `prompt.versions.list` | query | `prompt_id` | `PromptVersionResponse[]` |
| `prompt.list.active` | query | `{}` | `PromptResponse[]` |
| `prompt.list.deleted` | query | `{}` | `PromptResponse[]` |
| `prompt.versions.compare` | query | `prompt_id`, `from_version`, `to_version` | `VersionDiffResponse` |

Reply envelope: `{"ok": true, "correlation_id", "data"}` or
`{"ok": false, "correlation_id", "error": {"code", "message"}, "subject"}`.
Send the `X-Correlation-Id` header (or a `correlation_id` field) to trace a request; it is echoed in the
reply, in logs and in the events.

Error codes: `invalid_payload`, `not_found`, `version_not_found`, `invalid_version_comparison`,
`prompt_deleted`, `prompt_not_deleted`, `invalid_prompt`, `domain_error` (other rules), `timeout`,
`internal_error`. The response shapes are defined by the API's `models/response_models.py`.

## Events

After each committed change the core publishes domain events on `prompt.events.<name>`:
`created`, `version_added`, `version_activated`, `deactivated`, `reactivated`, `deleted`, `restored`.
Listen to all of them with `nats sub 'prompt.events.>'`.

## Test

```bash
./smoke_test.sh     # needs NATS, the NATS CLI and the core running; creates prompts named smoke-<id>
```

The core has no unit tests yet. The root [`smoke_test.sh`](../smoke_test.sh) checks it together with the API.
