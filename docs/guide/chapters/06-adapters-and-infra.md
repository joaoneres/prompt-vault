::: chapter 6 "Adapters and Infra" "How the core connects to NATS, SQLite and the terminal"

::: question
How can a core that "knows no technology at all" store data and receive messages?
:::

Here come the 1,027 lines that connect the core to the real world: 877 in the adapters and 150 in the infra. One golden rule applies to them: **no business rule**. Adapters only translate and connect; the infra only configures.

## 6.1 Infra: configuring the technologies

The `infra/` folder has four files, each configuring one technology. It imports nothing from the project: it is just tooling.

| File | Responsibility |
|---|---|
| `settings.py` | Reads the configuration from environment variables, with default values. |
| `database.py` | Creates the SQLite engine, applies the concurrency settings and creates the tables. |
| `nats_client.py` | Opens and closes the connection to NATS and logs the connection events. |
| `logging.py` | Configures structlog and rich, once, in a single place. |

| Environment variable | Default | What it is for |
|---|---|---|
| `NATS_URL` | `nats://localhost:4222` | Address of the NATS server. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./prompt_vault.db` | Where the database is (a single file). |
| `LOG_LEVEL` | `INFO` | How much detail appears in the logs. |
| `HANDLER_TIMEOUT_SECONDS` | `5` | Maximum time to process one message. |

## 6.2 Persistence: SQLAlchemy and SQLite

### SQLite and the WAL mode

SQLite is a database that fits in one file: there is no server to install. For concurrent use, we adjust a few options every time a connection is opened:

@code core/src/infra/database.py:13-22 "core/src/infra/database.py"

::: analogy The notebook with a scratch page (WAL)
In the ordinary mode, when someone writes in the "notebook", nobody can read it. In the WAL mode (*write-ahead log*), new notes go first to a scratch page beside it; readers keep reading the notebook while the writer takes notes. Later, the scratch page is merged. Result: reading and writing coexist. The other settings: `foreign_keys=ON` makes the database demand that the relations between tables are valid, and `busy_timeout` tells it to wait a little for a lock instead of failing immediately.
:::

### The ORM: tables as classes

An **ORM** (Object-Relational Mapper) such as SQLAlchemy lets you describe a table as a Python class. These classes are *not* the domain's: they are the relational model, and they never leave the adapter.

@code core/src/adapter/persistence/models.py:27-45 "core/src/adapter/persistence/models.py"

@figure er "The two tables. A prompt has many versions; the UNIQUE constraint prevents two equal numbers in the same prompt."

### Domain is not a table: the mapper

Why two models? Because they serve different owners. The domain changes for business reasons; the tables, for storage reasons. The **mapper** does the translation in both directions. When reading, it rebuilds the aggregate with `Prompt.rehydrate`, which revalidates the rules and emits no events (reconstituting is not a new fact):

@code core/src/adapter/persistence/mapper.py:8-33 "core/src/adapter/persistence/mapper.py"

When writing, the repository respects the nature of history: it only appends versions.

@code core/src/adapter/persistence/prompt_repository.py:27-40 "core/src/adapter/persistence/prompt_repository.py"

::: project A time zone detail
SQLite does not store time zones: it would hand back "loose" dates. A custom type, `UTCDateTime`, stores everything in UTC and returns time-zone-aware dates. A test confirmed it: the dates come back from the database identical to what the domain created.
:::

### The concrete Unit of Work and the write key

@code core/src/adapter/persistence/unit_of_work.py:33-60 "core/src/adapter/persistence/unit_of_work.py"

::: analogy Two people, one spreadsheet
If two people open the same spreadsheet, each changes a cell and saves, whoever saves last wipes out the other's change: the so-called *lost update*. The `asyncio.Lock` in `__aenter__` is the "single key to the room": while a write transaction is open, the others wait in line. We tested it with 40 simultaneous commands on the same prompt: the versions came out numbered 2 to 41, with no loss and no duplicate.
:::

::: warning An honest concession
Queries do not need a transaction, so they use a repository that opens a short session on every call (`SessionPerCallPromptRepository`). Since the port requires `save`, it exists but raises `NotImplementedError`. The "clean" solution would be a read-only port (`PromptReader`), touching `port/` and the queries. It was left as a future improvement.
:::

## 6.3 Messaging: the NATS adapter

NATS is a messaging system: a central server (the *broker*) where clients publish messages on **subjects** and others subscribe to those subjects. Names use dots to form hierarchies (`prompt.events.created`) and the wildcard `>` means "everything below" (`prompt.events.>` catches all the events). There are three usage patterns, all present here:

@figure nats "The three conversation patterns in Prompt Vault."

### The subjects of the system

| Kind | Subjects | Mode |
|---|---|---|
| Commands | `prompt.create`, `prompt.version.create`, `prompt.content.update`, `prompt.version.activate`, `prompt.delete`, `prompt.restore` | Asynchronous. They reply if the sender provides a reply address. |
| Queries | `prompt.get`, `prompt.versions.list`, `prompt.list.active`, `prompt.list.deleted`, `prompt.versions.compare` | Request and reply. Without a reply address, they are ignored. |
| Events (outbound) | `prompt.events.created`, `...version_added`, `...version_activated`, `...deleted`, `...restored`, `...deactivated`, `...reactivated` | Publish and subscribe. |
| Errors (outbound) | `prompt.errors` | Errors of commands that had nobody to reply to. |

### The correlation id: the tracking code

::: analogy The postal tracking code
With a tracking code, you follow the parcel through every stage. The correlation id does the same with a message: it enters through the `X-Correlation-Id` header (or the system creates one) and accompanies the reply, the published events and every log line. Later, you only search for that code to rebuild the whole story.
:::

@code core/src/adapter/messaging/correlation.py:15-23 "core/src/adapter/messaging/correlation.py"

It uses a `ContextVar`: a variable whose value is "private" to each asynchronous task. That way, simultaneous messages do not mix up their ids.

### The adapter only translates

See the "handler" of a command. It validates the format (is it a UUID? is it text?), builds the command and calls the use case. Then it asks a *serializer* to turn the result into the JSON the outside world expects. No business rule:

@code core/src/adapter/messaging/handlers.py:82-89 "core/src/adapter/messaging/handlers.py · create_version"

@code core/src/adapter/messaging/serializers.py:8-22 "core/src/adapter/messaging/serializers.py · the shape of a prompt"

The serializers are the *contract* of the core with the outside world. Their output matches the DTOs documented by the api (`PromptResponse`, `PromptVersionResponse`, `PromptDetailResponse`, `VersionDiffResponse`), which is why the api can forward the `data` untouched and the front end can trust it. A "modified" line of the domain diff, for instance, becomes two lines in the contract: a `removed` and an `added`, like a unified diff.

### Successes, failures and delays

The heart of the adapter decides what to do with successes, failures and slowness. Read carefully the `asyncio.wait_for` (the timeout) and the separation between "expected" errors (a warning) and "unexpected" ones (an exception, with traceback):

@code core/src/adapter/messaging/server.py:81-101 "core/src/adapter/messaging/server.py"

### The envelope and the error codes

Every reply is an envelope `{ok, correlation_id, data | error}`. A real error, produced by forcing a timeout:

```json title="Real error reply"
{"ok": false, "correlation_id": "ae85212c-327d-4d49-a689-64493a259c1f",
 "error": {"code": "timeout", "message": "The operation timed out"}, "subject": "prompt.list.active"}
```

@code core/src/adapter/messaging/errors.py:16-43 "core/src/adapter/messaging/errors.py"

| Code | When it happens | Example |
|---|---|---|
| `invalid_payload` | Malformed message: invalid JSON, missing or wrongly typed field, malformed UUID. | `{not json` |
| `not_found` | The requested prompt does not exist. | a random UUID |
| `version_not_found` | The version number does not exist in that prompt. | activating version 99 |
| `invalid_version_comparison` | Comparing a version with itself. | `from_version == to_version` |
| `prompt_deleted` | The operation is not allowed on a deleted prompt. | activating a version of a deleted prompt |
| `prompt_not_deleted` | Restoring a prompt that is not deleted. | `restore` on an active prompt |
| `invalid_prompt` | Invalid data for a prompt or version. | a blank name |
| `domain_error` | Any other business rule. | the generic fallback |
| `timeout` | Processing exceeded the limit. | a slow handler |
| `internal_error` | Unexpected error. Details only in the log, never in the reply. | an unforeseen failure |

::: lesson One code per rule
In the first edition every business rule became the same `domain_error`, so a client had to read the English message to know what happened. When the api was built, that turned out to be fragile: the api guessed the exception by matching text, and a reworded message would silently degrade the answer. The core now sends **one code per rule**, and the api maps codes, not words (the text match survives only as a fallback for `domain_error`). Moral: an interface between two systems should be a contract of codes, never of prose.
:::

### Publishing the events

@code core/src/adapter/messaging/event_publisher.py:45-56 "core/src/adapter/messaging/event_publisher.py"

Notice the `try / except`: if publishing fails, the error is logged but not propagated. The reason: the data was already saved; telling the client that the command failed would make it try again and duplicate the effect.

## 6.4 Structured logging: structlog + rich

A traditional log is a loose sentence: "user 42 deleted the prompt". To find something you have to guess the text. A **structured log** separates the event from its fields (`event=use_case_started use_case=DeletePrompt correlation_id=fail-1`), and each field becomes searchable. `structlog` produces that; `rich` takes care of the presentation in the terminal. The `correlation_id` is added automatically to every line, thanks to the `ContextVar` we saw.

This is the real trace of a command that failed (deleting a non-existent prompt, with no reply address), condensed to fit the page:

```text title="Real log (condensed)"
INFO       event_received            subject=prompt.delete kind=command has_reply=False correlation_id=fail-1
INFO       use_case_started          use_case=DeletePrompt                       correlation_id=fail-1
INFO       transaction_rolled_back   failed=True                                 correlation_id=fail-1
WARNING    use_case_rejected         use_case=DeletePrompt error_code=not_found correlation_id=fail-1
INFO       error_published           subject=prompt.errors source=prompt.delete correlation_id=fail-1
```

Read from top to bottom: the message arrived, the use case started, the transaction was undone (nothing stored), the error was classified as `not_found` and published on `prompt.errors`, all with the same `correlation_id`. The domain does not import the logger: logs live only in the adapters.

::: lesson When rich gets in the way
While testing the timeout, the error line came out as a raw dictionary instead of the normal format. The cause: the `RichHandler`, with tracebacks on, ignores structlog's formatter when there is an exception. The fix was to turn that option off and let structlog itself format the traceback (also with rich). Moral: integrating two good libraries requires testing the junction, including the error path.
:::

## 6.5 main.py: the composition root

All of this is loose pieces until someone wires them. That someone is `main.py`, the composition root: the only file that knows all the layers.

| # | Step | Why |
|---|---|---|
| 1 | Configure logging and read the settings | First of all, to record whatever comes next. |
| 2 | Create the SQLite engine and the tables | The database must exist before the first message. |
| 3 | Connect to NATS | If it fails, the program logs the error and exits. |
| 4 | Create the publisher, the write lock and the read repository | Pieces shared by all messages. |
| 5 | Build the use case factories | One new instance per message (see below). |
| 6 | Start the `MessagingAdapter` (subscribe to the subjects) | From here on the service answers. |
| 7 | Wait for SIGINT/SIGTERM and shut down cleanly | Cancel subscriptions, drain NATS, close the database. |

@code core/src/main.py:52-70 "core/src/main.py · the factories"

::: concept Why "one instance per message"?
Every write use case carries its Unit of Work, and therefore its database session. A session cannot be shared by simultaneous messages. That is why the `lambda` (an anonymous function) manufactures a new use case, with its own session, for each message received.
:::

::: checkpoint
1. What is the correlation id for?
2. Why does the app create a new instance of each use case for each message?
3. What does the SQLite WAL mode improve?
:::

::: summary
- `infra` only configures; adapters only translate and connect: no business rule.
- Persistence: a relational model separate from the domain, with a mapper; history only grows; a lock prevents lost updates.
- Messaging: subjects for commands and queries, a standard envelope, one error code per rule, a timeout and a correlation id.
- Serializers shape the replies into the contract the api and the front end rely on.
- Structured logs with structlog + rich; the correlation id stitches everything together.
- `main.py` wires the pieces: it is the only one that knows all the layers.
:::
