::: chapter 10 "Verifying that it works" "Tests from top to bottom, and the lessons they gave"

::: question
How do we know that all of this really works, and does not merely look like it works?
:::

## 10.1 Verify in layers

Every stage of the project was verified at the level where it made sense. The deeper the layer, the faster and more isolated the test; the further out, the closer to reality:

| Level | What was tested | With what |
|---|---|---|
| Domain | Creation, versions, activation, life cycle, soft delete, events, rehydration, diff. | Pure Python, nothing external. |
| Application | The 11 use cases, including "nothing is saved nor published when the domain refuses". | Fake repository and publisher. |
| Persistence | Round trips to SQLite, time zones, rollback, 25 simultaneous commands, WAL mode, data after a restart. | Real SQLite in a temporary file. |
| The api | The publisher, the 11 service methods, the routes, the exceptions and handlers: 117 unit tests. | `pytest` with NATS and the service mocked. Nothing touches the network. |
| Core, end to end | Every subject, events, errors, timeout, clean shutdown. | Real NATS (Docker) and the real app. |
| Core smoke test | 54 checks through the "front door", using only the NATS CLI. | `core/smoke_test.sh` |
| Api smoke test | 48 checks over HTTP, with real NATS and a real core. | `api/smoke_test.sh` |
| Global smoke test | 62 checks that the three pieces agree (see 10.3). | `smoke_test.sh` at the root |
| Front end | Types checked by the compiler; every screen exercised in a real browser against the real api. | `npm run build`, plus browser scripts |

## 10.2 The smoke test

A **smoke test** comes from electronics: you turn the device on and see whether smoke comes out. In software, it is a quick check that the essentials work. The scripts are plain shell: they use only the NATS CLI or `curl`, exactly like a real user, send messages and compare the replies. Two small pieces hold the script up:

```bash title="core/smoke_test.sh · send a request and compare results"
req() {
  local subject=$1 payload=$2 cid=${3:-}
  local args=(request "$subject" "$payload" --timeout "$TIMEOUT" --raw)
  [[ -n "$cid" ]] && args+=(-H "X-Correlation-Id:$cid")
  RESP="$(nats "${args[@]}" 2>/dev/null)" || RESP="<no response within $TIMEOUT>"
}

expect_eq() { # <description> <expected> <actual>
  if [[ "$3" == "$2" ]]; then pass "$1"; else fail "$1" "expected: $2 | actual: $3"; fi
}
```

## 10.3 The global smoke test: do the three pieces agree?

The smoke test of each project checks that project against its own expectations. That is not enough: both sides could pass while disagreeing with each other. The global script (`smoke_test.sh` at the repository root) is built to catch exactly that:

1. It checks that NATS, the core and the api all answer, and tells you what to start if one does not.
2. It walks through every operation **over HTTP** and validates each JSON body against the api's own Pydantic models (`PromptResponse`, `PromptVersionResponse`, `PromptDetailResponse`, `VersionDiffResponse`, lists of them). If the core ever produced a field with a different name or type, this fails.
3. For each query, it asks the same thing **directly on NATS** and requires the HTTP body to be *identical* to the core's `data`. That proves the gateway only transports.
4. A prompt created over HTTP must be visible on NATS, and one created on NATS must be visible over HTTP.
5. Creating, changing, deleting and restoring over HTTP must publish the matching domain events (`prompt.events.created`, `version_added`, ...).
6. The core's errors must reach HTTP with the right status and code (404, 409, 422).

Result of the last run: **62 of 62** checks, 0 failures. The core's own smoke test passes 54 of 54, and the api's 48 of 48.

::: project Contract tests, discovered by accident
The idea of validating real bodies against the api's models was not in the plan. It came from a finding: the first time the api documented its DTOs, the core still answered in an older shape, and nothing failed. Documentation and reality had silently drifted. The global smoke test is the guard against that drift.
:::

## 10.4 Other verifications

- **Concurrency:** 40 simultaneous commands on the same prompt generated versions 2 to 41, with no loss and no duplicate.
- **Persistence and life cycle:** data survived a restart (the file in WAL mode) and `SIGTERM` stopped the app cleanly.
- **Timeout:** with the limit forced to 0.0001 s, the client received `timeout` and the log showed the formatted traceback.
- **Isolation:** no mention of infrastructure, adapters or libraries in `domain/`, `app/` and `port/`; `pyright` with 0 errors.
- **The browser:** compare, timeline, trash, activation and deletion were exercised with a real Chromium against the real api: success paths, simulated 500 and 409 errors, loading states, dark theme and a 375-pixel-wide screen.

## 10.5 Lessons from the way

| What went wrong | What we learned |
|---|---|
| SQLAlchemy 2.1 asked for `greenlet` when used asynchronously. | Read the error message to the end: it said the extra to install (`sqlalchemy[asyncio]`). |
| The traceback came out as a raw dictionary in the log. | Two good libraries can conflict at the junction; test the error path, not only the happy one. |
| The smoke test failed intermittently with `not_found`. | Two instances of the app were on the same NATS and both answered (each with its own database). Without a queue group, every subscriber receives everything. |
| `restore` worked on a prompt that was not deleted. | The end-to-end test found a business-rule hole that reading the code did not show. |
| The api guessed the type of a core error by reading its English message. | Between systems, exchange *codes*, not prose. The core now sends one code per rule. |
| The api documented its DTOs but the core answered in another shape. | Documentation drifts silently. Add a test that compares the two (the global smoke test). |
| `openapi-typescript` crashed with the newest TypeScript. | A tool that uses a compiler's internal API is tied to its major version; pin it. (The project uses TypeScript 5.) |
| The split diff overlapped long lines. | `table-layout: fixed` plus no-wrap text overflows its cell. Give the table a minimum width and let the wrapper scroll. |
| Browser tests failed although the page was right. | Tests have bugs too: wait for what only the final content has, and match text exactly. |

::: warning Scaling to several instances
Today, two instances of the core on the same NATS execute every command twice. To scale horizontally, the subscriptions need a *queue group* (NATS then delivers each message to only one member), and the shared database would need concurrency control beyond the local lock. It is a natural next step, not done yet.
:::

::: checkpoint
1. What does the global smoke test prove that each project's own smoke test cannot?
2. Why is it better for the core to send one error code per rule than a single generic one?
3. Why are the api unit tests allowed to mock NATS, and what do they *not* prove?
:::

::: summary
- Each layer was tested at the right level; the api has 117 unit tests with NATS mocked.
- Three smoke tests exist: core (54), api (48) and global (62). The global one checks that the pieces agree.
- The best lessons came from tests that failed; they are worth thanking.
:::
