::: chapter B "File map" "Where everything is, and which layer it belongs to"

## B.1 core/

| File | Layer | Responsibility |
|---|---|---|
| `src/domain/entities/prompt.py` | domain | `Prompt`: the root aggregate, with every rule and event. |
| `src/domain/entities/prompt_version.py` | domain | `PromptVersion`: an immutable snapshot of the content. |
| `src/domain/status.py` | domain | `PromptStatus` and the table of permitted transitions. |
| `src/domain/events.py` | domain | The seven domain events. |
| `src/domain/exceptions.py` | domain | Business errors (`DomainError` and children). |
| `src/domain/diff/models.py` | domain | `ChangeType`, `DiffEntry` and `VersionDiff`. |
| `src/domain/diff/strategy.py`, `line_diff.py` | domain | `DiffStrategy` (contract) and `LineDiffStrategy` (line by line, with `difflib`). |
| `src/port/*.py` | port | The three contracts: `PromptRepository`, `EventPublisher`, `UnitOfWork`. |
| `src/app/commands/*.py` | app | Six write use cases; each returns the aggregate. |
| `src/app/queries/*.py` | app | Five read use cases (including `CompareVersions`). |
| `src/app/exceptions.py`, `_helpers.py` | app | `PromptNotFoundError` and `require_prompt`. |
| `src/adapter/persistence/models.py` | adapter | ORM tables and the UTC date type. |
| `src/adapter/persistence/mapper.py` | adapter | Domain to tables translation, both ways. |
| `src/adapter/persistence/prompt_repository.py` | adapter | The SQLAlchemy repository (write and read). |
| `src/adapter/persistence/unit_of_work.py` | adapter | The concrete transaction, with the write key. |
| `src/adapter/messaging/subjects.py` | adapter | The subject names. |
| `src/adapter/messaging/codec.py` | adapter | JSON to objects, field validation and envelopes. |
| `src/adapter/messaging/handlers.py` | adapter | Translation from subject to use case. |
| `src/adapter/messaging/serializers.py` | adapter | Domain objects to the JSON contract (`PromptResponse` and friends). |
| `src/adapter/messaging/server.py` | adapter | Subscriptions, timeout, replies and logs. |
| `src/adapter/messaging/event_publisher.py` | adapter | Publishes the domain events on NATS. |
| `src/adapter/messaging/correlation.py` | adapter | The correlation id per asynchronous task. |
| `src/adapter/messaging/errors.py` | adapter | Exception to error code. |
| `src/infra/settings.py`, `database.py`, `nats_client.py`, `logging.py` | infra | Environment configuration, SQLite engine, NATS connection, structlog + rich. |
| `src/main.py`, `docker-compose.yml`, `smoke_test.sh`, `pyproject.toml`, `uv.lock` | n/a | Composition root · local NATS · smoke test · dependencies. |

## B.2 api/

| File | Responsibility |
|---|---|
| `main.py` | The FastAPI app, the NATS lifespan and the handler registration. |
| `controllers/prompt_controller.py` | The `/prompts` router: eleven one-line routes. |
| `services/prompt_service.py` | One method per use case: payload + subject + publisher. |
| `messaging/nats_publisher.py` | The only code that imports `nats-py`; maps core error codes to exceptions. |
| `models/prompt_models.py` | The request DTOs and the body-only DTOs. |
| `models/response_models.py` | `ApiWrapper[T]` and the response DTOs used for the documentation. |
| `utils/exceptions.py` | `BaseAppException` and its subclasses. |
| `utils/error_handlers.py` | The central handlers, and their registration. |
| `utils/json_utils.py`, `logger.py` | JSON encode/decode helpers and logging setup. |
| `tests/` | 117 unit tests, organized by layer. |
| `smoke_test.sh` | 48 checks over HTTP. |

## B.3 front/

| File | Responsibility |
|---|---|
| `src/main.tsx`, `App.tsx` | Startup, the state of the list, the hash router, the navigation bar and the toasts. |
| `src/api/client.ts` | The shared Axios instance and the error interceptor. |
| `src/api/prompts.ts` | One function per api endpoint. |
| `src/api/schema.d.ts` | Types generated from `openapi.json` (never edited by hand). |
| `src/types.ts` | Short aliases for the generated types. |
| `src/components/PromptList.tsx`, `PromptCard.tsx` | The searchable list and its cards. |
| `src/components/CreatePromptModal.tsx`, `PromptDetailModal.tsx` | Creation, and details with copy, edit and delete. |
| `src/components/ComparePage.tsx`, `VersionSelector.tsx`, `DiffViewer.tsx` | Version comparison. |
| `src/components/TimelinePage.tsx`, `VersionTimeline.tsx` | The version history and its quick actions. |
| `src/components/TrashPage.tsx`, `ConfirmModal.tsx`, `Modal.tsx` | The trash, and the dialogs. |
| `src/components/Toaster.tsx`, `ThemeToggle.tsx`, `GeometricBackground.tsx`, `FloatingAddButton.tsx` | Notifications, theme, decoration and the "+" button. |
| `vite.config.ts`, `openapi.json`, `.env.example` | Dev server and proxy · the api contract snapshot · configuration. |

## B.4 repository root

| File | Responsibility |
|---|---|
| `smoke_test.sh` | The global smoke test: HTTP, NATS, core, contract and cross-checks. |
| `docs/` | This guide (`prompt-vault-study-guide.pdf`), the interactive map (`prompt-vault-map.html`) and the guide's source (`docs/guide/`). |
