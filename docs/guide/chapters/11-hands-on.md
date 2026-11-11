::: chapter 11 "Hands-on" "Run, explore and extend the project on your own"

::: question
How do I use the system myself, and how do I extend it without breaking the architecture?
:::

## 11.1 Bringing up the environment

You need Docker, `uv`, Python 3.13 and Node.js 22. Use one terminal per service:

```bash title="Terminal"
# 1) the NATS server (needs Docker)
cd core && docker compose up -d

# 2) the core (another terminal)
cd core && uv sync && uv run src/main.py

# 3) the api (another terminal)
cd api && uv sync && uv run uvicorn main:app --reload

# 4) the front end (another terminal)
cd front && npm install && npm run dev
```

Open `http://localhost:5173` for the application, and `http://localhost:8000/docs` for the api's Swagger page. Then run the full verification:

```bash title="Terminal"
./smoke_test.sh          # the global smoke test, from the repository root
```

## 11.2 Recipes

Replace `<ID>` with the `id` returned when you create a prompt. Open a second terminal running `nats sub 'prompt.events.>'` to see the events arriving while you work.

```bash title="Straight to the core, with the NATS CLI"
# create a prompt
nats request prompt.create '{"name":"greeting","content":"Hello\nworld"}' --raw
# new version (not active) and content change (creates and activates)
nats request prompt.version.create '{"prompt_id":"<ID>","content":"Hi\nworld"}' --raw
nats request prompt.content.update '{"prompt_id":"<ID>","content":"Hey\nworld\nend"}' --raw
# read, compare and go back
nats request prompt.get '{"prompt_id":"<ID>"}' --raw
nats request prompt.versions.compare '{"prompt_id":"<ID>","from_version":1,"to_version":3}' --raw
nats request prompt.version.activate '{"prompt_id":"<ID>","version_number":1}' --raw
# delete (soft), list and recover
nats request prompt.delete '{"prompt_id":"<ID>"}' --raw
nats request prompt.list.deleted '{}' --raw
nats request prompt.restore '{"prompt_id":"<ID>"}' --raw
# a command without a reply, with its own tracking code
nats pub prompt.delete '{"prompt_id":"<ID>"}' -H "X-Correlation-Id:my-trace"
```

```bash title="The same operations over HTTP, with curl"
curl -s -X POST localhost:8000/prompts -H 'Content-Type: application/json' \
     -d '{"name":"greeting","content":"Hello\nworld"}'
curl -s localhost:8000/prompts/<ID>
curl -s -X POST localhost:8000/prompts/<ID>/compare -H 'Content-Type: application/json' \
     -d '{"from_version":1,"to_version":2}'
curl -s -X DELETE localhost:8000/prompts/<ID>
curl -s localhost:8000/prompts/deleted
```

## 11.3 Exercises

| # | Exercise | Hint |
|---|---|---|
| 1 | **Watch the events.** With `nats sub 'prompt.events.>'` open, create a prompt and change its content, first with the NATS CLI and then in the browser. Which events appear, in which order? | Look for the `X-Correlation-Id` header in the output. |
| 2 | **Read a diff.** Create a version 2 with one changed line, one removed and one added, then compare. Classify every entry. | Note how a "modified" line appears as removed + added in the contract. |
| 3 | **Cause every kind of error.** Invalid JSON, an unknown UUID, restoring an active prompt. What `code` comes back from the core, and what HTTP status from the api? | Compare Chapter 6 (codes) with Chapter 7 (statuses). |
| 4 | **Follow a correlation id.** Send a request with `-H "X-Correlation-Id:my-trace"` and find that code in the core's output. | `grep` or your terminal's search. |
| 5 | **Stop the core.** With the front end open, stop the core and click around. What does the user see, and why? | `503 CORE_UNAVAILABLE`, in a toast. Then start the core: does the page recover without a reload? |
| 6 | **Challenge (domain).** Write a `DiffStrategy` that compares word by word. | Create a class in `src/domain/diff/` with `name` and `diff`, and swap the strategy in `main.py`. Which files did not need to change? |
| 7 | **Challenge (new feature).** "Rename prompt". Plan, layer by layer and project by project, what would change. | See the plan below, and count how many layers are touched. |

::: project Exercise 7: the map of the change
1. **domain:** a `Prompt.rename(name)` method (validates a non-blank name, updates the date) and a `PromptRenamed` event.
2. **port:** nothing changes; saving a modified prompt is the usual `save`.
3. **app:** `RenamePromptUseCase` and `RenamePromptCommand`, in the same mold as `DeletePromptUseCase`; it returns the prompt.
4. **adapter/messaging:** the subject `prompt.rename`, a handler and a `Route` in `build_routes`; the event gets its name in `_EVENT_NAMES`.
5. **adapter/persistence:** nothing changes; the mapper already copies the `name` field (`apply_state`).
6. **api:** a request DTO, a `PromptService.rename_prompt` method, a route (`PATCH /prompts/{id}`) and its tests.
7. **front:** a service function and an input in the details modal. Regenerate the types with `npm run gen:api`, and the compiler shows every place that must be updated.
8. **smoke tests:** new checks for the subject, the route and the event.

Notice: the database and the ports stay untouched. It is the architecture showing its value: the change touches only where it makes sense.
:::

## 11.4 Natural next steps

| Improvement | Why |
|---|---|
| Queue group in the subscriptions | Allow several instances of the core without executing each command twice. |
| Outbox pattern | Write the event in the same transaction as the data, so an event published after the commit can never be lost. |
| A read port (`PromptReader`) | Separate reading from writing in the ports and remove the read repository's concession. |
| Unit tests for the core | Turn the verification scripts into a permanent `pytest` suite that runs on every change. |
| Front-end tests | Add component tests and turn the browser scripts into a permanent suite. |
| Pagination, and the active version inside the list | Avoid returning every prompt at once, and spare the front end its request per card. |
| CORS in the api | Allow a production build of the front end served from another address. |
| AsyncAPI documentation | Formally describe subjects and payloads, so other teams can integrate. |
