::: chapter D "Answers to the checkpoints" "The questions of each chapter, answered"

| Ch. | Question | Answer |
|---|---|---|
| 2 | What is `uv.lock` for? | It records the exact versions of everything installed, to reproduce the same environment on any machine. `uv` generates it; editing by hand risks breaking that guarantee. |
| 2 | What is `int \| None`? | A value that can be an integer or nothing (`None`). In `active_version_number`, `None` means "no active version". |
| 2 | What if there is an error before `commit()` in an `async with uow`? | On leaving the block, `__aexit__` does a rollback: nothing done in the transaction stays stored. |
| 3 | Why does `domain` not import `sqlalchemy`? | To stay independent from technology: it can be tested without a database, and the rules survive a change of technology. |
| 3 | What to change to swap SQLite for PostgreSQL? | `adapter/persistence` and the configuration in `infra/database.py` (URL and driver). `domain`, `app` and `port` stay intact. |
| 3 | Port versus adapter? | A port is the contract (a Protocol); an adapter is a concrete implementation of that contract, tied to a technology. |
| 4 | Why is `PromptVersion` frozen? | Because history is immutable: a version, once created, never changes. Switching the active version only moves the pointer. |
| 4 | What does `restore()` do on an active prompt? | It raises `PromptNotDeletedError`: only what is deleted can be restored. |
| 4 | A word-by-word diff? | A new class with `name` and `diff(old, new)` (a `DiffStrategy`), handed to the use case in `main.py`. |
| 5 | Command versus query? | A command changes the state (uses a transaction and publishes events); a query only reads (no transaction, publishes nothing). |
| 5 | Why publish after the commit? | Not to announce to the world something that, because of a failure while saving, did not happen. |
| 5 | Why does the use case receive the `uow` in the constructor? | Dependency injection: the use case does not know how the transaction is made, which allows swapping it (even for a fake, in tests). |
| 6 | What is the correlation id for? | To trace a message from beginning to end: it shows up in the reply, in the events and in every log line. |
| 6 | Why a new instance of each use case per message? | Each one carries its Unit of Work and its database session, which cannot be shared by simultaneous messages. |
| 6 | What does WAL improve? | Reading and writing coexist: readers are not blocked while someone writes. |
| 7 | Why does `NATSPublisher.request` return only `data`? | The gateway transports and does not reshape. The envelope (`ok`, `correlation_id`) is protocol; the controller's job is to return the content. |
| 7 | Why do controllers have no `try / except`? | Error handling is central: handlers registered on the app turn every exception into the same JSON format, so no route can forget or differ. |
| 7 | What can make the api answer 503 or 504 with no bug in the code? | The core is stopped (no responders, 503), publishing to NATS fails (503) or the core is slower than the three-second timeout (504). |
| 8 | Why call `/api/...` and not `localhost:8000` directly? | The api has no CORS, so the browser would block the cross-origin call. The Vite proxy makes the front end and the api look like one origin. |
| 8 | What does the stale response guard solve? | Two requests in flight where the older answers last: without the guard the screen would show a diff that does not match the selected versions. |
| 8 | Why does the front end not compute the diff? | The algorithm is a business rule and lives in the core. Computing it again would duplicate logic and risk two different answers. |
| 10 | What does the global smoke test prove that the others cannot? | That the pieces agree with each other: the HTTP bodies match the api's models and the core's `data`, and both sides see the same state. |
| 10 | Why one error code per rule? | Between systems a code is a stable contract; matching English prose breaks silently when someone rewords a message. |
| 10 | Why may api unit tests mock NATS, and what do they not prove? | Mocks isolate the api's own logic and make the tests fast and deterministic. They do not prove that the real core answers as the mock does; that is what the smoke tests are for. |
