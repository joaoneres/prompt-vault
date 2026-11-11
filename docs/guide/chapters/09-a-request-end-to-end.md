::: chapter 9 "A request end to end" "What happens, step by step, when someone clicks Save in the browser"

::: question
When I click a button, through which pieces does the request pass, and in what order?
:::

Now that you know every part, let us stitch everything together following one single action: the user edits a prompt in the browser and clicks **Save and activate**. Along the way we will cross three projects, three borders (HTTP, NATS, SQL) and every layer of the core.

## 9.1 The core's half of the story

First the inside view, the part executed by the core. A client (here the api, but it could be the `nats` CLI) sends a message to `prompt.content.update`:

```bash title="The request, as the NATS CLI would send it"
nats request prompt.content.update \
  '{"prompt_id": "<ID>", "content": "Hey\nworld\nend"}' \
  -H "X-Correlation-Id:my-trace"
```

@figure seq_core "The path of the message inside the core. Dashed lines are returns or publications; the numbers match the arrows."

| # | What happens | Arrows | Who | Layer |
|---|---|---|---|---|
| 1 | The message arrives at the subject. The adapter decodes the JSON, finds the correlation id (from the header) and records it in every log. | 1 | `MessagingAdapter` | adapter |
| 2 | The handler validates only the format (UUID and text), builds the `UpdateContentCommand` and asks the factory for a new use case. | 2 | `handlers.py` | adapter |
| 3 | The use case opens the transaction (`async with uow`): the Unit of Work takes the write key and opens a session. | 3 | `UpdateContentUseCase` | app |
| 4 | The repository does the `SELECT` of the prompt and its versions; the mapper rebuilds the aggregate with `rehydrate`. | 4, 5 | `SqlAlchemyPromptRepository` | adapter |
| 5 | The use case calls `prompt.add_version(content, activate=True)`. The business rule runs here: it validates, numbers, activates and records two events. | 6 | `Prompt` | domain |
| 6 | The repository writes (`INSERT` of the new version, `UPDATE` of the prompt) and the Unit of Work commits. The key is released. | 7, 8 | `SqlAlchemyUnitOfWork` | adapter |
| 7 | Already outside the transaction, the use case hands the events (`pull_events()`) to the publisher, which sends them to NATS with the correlation id. | 9, 10 | `NatsEventPublisher` | adapter |
| 8 | The use case returns the prompt and the new version. The handler serializes them into the `PromptVersionResponse` shape, wraps it in the `ok` envelope and publishes it on the client's reply address. | 11, 12 | `MessagingAdapter` | adapter |

## 9.2 The whole journey, from the browser

Now widen the camera. The same operation, started from the screen:

@figure seq_e2e "The complete journey of one click, from the browser to SQLite and back."

1. **The click.** In `PromptDetailModal`, `save(true)` calls `updateContent(id, draft)`, and Axios sends `PUT /api/prompts/{id}/content` with the body `{"content": ...}`.
2. **The proxy.** In development the Vite server forwards it to `http://localhost:8000/prompts/{id}/content`.
3. **The controller.** FastAPI validates the path (a UUID) and the body (a Pydantic model), and calls `service.update_content(...)`.
4. **The service and publisher.** `PromptService` builds `{"prompt_id": "...", "content": "..."}`, picks the subject `prompt.content.update` and `NATSPublisher.request` sends it, waiting at most three seconds.
5. **The core.** Everything in section 9.1 happens: use case, domain, SQLite, events, reply envelope.
6. **The reply.** NATS brings the envelope back. The publisher validates it, sees `ok: true` and returns only `data`. The controller returns that as the HTTP body, status 200.
7. **The screen.** The front end receives the new version, asks `reloadOne` to refresh that prompt (another `GET`, a full round trip through all the layers), closes the modal and shows the green toast "New version vN saved and activated".

## 9.3 What each observer sees

| Who | What they see |
|---|---|
| The browser user | The modal closes, the card shows the new version badge and the new preview, and a toast confirms it. |
| The api logs | One request line, no error. |
| A subscriber of `prompt.events.>` | Two events, `version_added` and `version_activated`, both with the header `X-Correlation-Id`. |
| The database | A new row in `prompt_versions` and the `active_version_number` updated in `prompts`. Older versions stay intact. |
| The core logs | `event_received`, `use_case_started`, `prompt_saved`, `transaction_committed`, `event_published`, `use_case_completed`, `reply_sent`, all with the same `correlation_id`. |

## 9.4 When something goes wrong

The same journey fails in different places, and every failure has a predictable ending:

| What fails | Where it is noticed | What the user ends up seeing |
|---|---|---|
| The id in the URL is not a UUID | FastAPI, before any NATS message | `422 INVALID_REQUEST`, a toast with the message. The core never hears about it. |
| The core is not running | NATS: nobody subscribed to the subject | `503 CORE_UNAVAILABLE`. |
| The core is too slow | The api's three-second timeout | `504 CORE_TIMEOUT`. |
| The prompt is in the trash | The domain refuses (`PromptDeletedError`); the core replies `prompt_deleted` | `409 PROMPT_ALREADY_DELETED`; the screen keeps working. |
| The prompt does not exist | The use case (`PromptNotFoundError`); the core replies `not_found` | `404 PROMPT_NOT_FOUND`. |
| Something nobody planned | The central handler of either side | `500 INTERNAL_SERVER_ERROR`, with the details only in the logs. |

::: summary
- A click crosses: component, service layer, HTTP, controller, service, publisher, NATS, messaging adapter, use case, domain, repository, SQLite, and the same path back.
- The correlation id follows the message through the core, from the reply to the events and logs.
- The lesson of architecture: NATS appears only in the messaging adapter and the api publisher; SQL only in the persistence adapter. The business rule (step 5 of 9.1) touches no technology. That is having the business at the center and the technology at the edges.
- Every kind of failure ends as the same standard JSON error, shown as a toast.
:::
