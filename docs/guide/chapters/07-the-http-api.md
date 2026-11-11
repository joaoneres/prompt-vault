::: chapter 7 "The HTTP API" "How a web request reaches the core, and how errors find their way back"

::: question
If the core only understands NATS messages, how does a browser, which only speaks HTTP, use it?
:::

The `api/` project is a **gateway**: a thin entry point that hides a backend. It has no business rules. Its whole job is to (1) accept an HTTP request, (2) check that its shape is valid, (3) send one NATS message to the core, and (4) turn the reply, or the failure, into an HTTP response. It has about 660 lines of application code and 695 lines of tests.

::: analogy The receptionist
In a clinic, the receptionist does not treat patients. They greet you, check that your form is filled in correctly, pass it to the doctor's room and bring the answer back. If the doctor is busy or absent, the receptionist explains it politely instead of letting you wander into the corridor. That is the api: it knows the *format* of every conversation but none of the medicine.
:::

## 7.1 The layers of the api

The api uses the familiar MVC-style folders, but notice that each folder has a very small job:

@figure api_layers "The layers of the api. Only messaging/ imports nats-py; controllers never catch errors."

| Folder | Job | Example |
|---|---|---|
| `controllers/` | Declares the HTTP routes and turns the request into a DTO. No logic. | `update_content(prompt_id, body, service)` |
| `services/` | One method per use case: builds the payload and picks the NATS subject. | `PromptService.update_content` |
| `messaging/` | The *only* code that talks to NATS. Sends the request, unwraps the reply, raises errors. | `NATSPublisher.request` |
| `models/` | DTOs (Pydantic) for requests, and the models that *document* the replies. | `CreatePromptRequest`, `ApiWrapper[T]` |
| `utils/` | Exceptions, the error handlers, JSON helpers and logging. | `BaseAppException` |
| `tests/` | 117 unit tests with NATS mocked. | `test_nats_publisher.py` |

The entry point wires it together. Read `main.py` slowly; it is the whole application:

@code api/main.py:1-32 "api/main.py"

Three ideas appear here. **The lifespan** is code that runs when the server starts (connect to NATS, build the service) and when it stops (`drain()`: finish what is in flight, then close). **`app.state`** is a small shelf where the app keeps shared objects. **`register_exception_handlers`** installs the central error handling of section 7.5.

## 7.2 FastAPI in five minutes

FastAPI is a web framework. You declare a route with a decorator, and the function's parameters tell it what the request must contain:

@code api/controllers/prompt_controller.py:80-89 "api/controllers/prompt_controller.py · a route"

- `@router.put("/{prompt_id}/content")` binds the HTTP method and path.
- `prompt_id: UUID` is read from the path **and validated**: an id that is not a UUID is rejected with `422` before the function even runs.
- `body: UpdateContentBody` is a Pydantic model: FastAPI reads the JSON body and checks it against the model.
- `service: PromptService = Service` is **dependency injection**: FastAPI calls `get_prompt_service` and hands the result in. In the tests we replace that provider with a mock, without touching the route.
- The function body is one line: call the service. Nothing else.

::: concept Pydantic models are DTOs
A **DTO** (data transfer object) is a plain object that only carries data across a boundary. Pydantic turns a class with type annotations into a validator: `CreatePromptRequest(name: str, content: str)` refuses a body without `content`. That validation is the *shape* check. Whether the name is blank is a *business* rule, so it stays in the core.
:::

## 7.3 The service builds the message

@code api/services/prompt_service.py:29-60 "api/services/prompt_service.py"

Each method does the same three things: build a payload (with ids turned into strings so they are valid JSON), choose the subject, and ask the publisher. The subject names are the very same ones the core listens to; the api and the core agree on them as a contract. Before this phase the commands used a fire-and-forget publish. They now use *request and reply*, because a browser needs an answer (the id of the created prompt, the new version number) and needs to hear about errors.

## 7.4 The publisher: the only door to NATS

@code api/messaging/nats_publisher.py:69-108 "api/messaging/nats_publisher.py"

Read `request` as a story:

1. **Send** the request and wait up to `timeout` seconds. If NATS is slow, the api raises `CoreTimeoutException`. If nobody is subscribed to that subject (the core is down), NATS answers "no responders" and the api raises `CoreUnavailableException`.
2. **Decode** the reply bytes as JSON. Garbage becomes `CoreResponseException`.
3. **Validate the envelope** with `ApiWrapper[Any]` (below). A reply without `ok` is a protocol violation.
4. **If `ok` is false**, turn the core's error code into an exception of the api.
5. **Otherwise return only `data`**. The controller returns it as the HTTP body, untouched.

That last point is a design principle worth stating: **the gateway transports, it does not reshape**. It never rebuilds a prompt, never renames fields, never "fixes" dates. The core produces the JSON contract; the api forwards it. This keeps domain logic from being duplicated in two places.

@code api/models/response_models.py:13-17 "api/models/response_models.py · the generic wrapper"

`ApiWrapper[T]` is a **generic** model: `T` is a placeholder for "whatever the data is". `ApiWrapper[PromptResponse]` wraps a prompt, `ApiWrapper[list[PromptVersionResponse]]` wraps a list. The same class describes every reply of the core. (The other models in that file, such as `PromptResponse` and `VersionDiffResponse`, document the shape of `data`. FastAPI shows them in Swagger. They do not validate the actual response, because the gateway does not reshape it; the global smoke test of Chapter 10 checks that the core really produces them.)

## 7.5 Errors: one base class, one central place

Every error the api raises on purpose is a subclass of one base class:

@code api/utils/exceptions.py:4-27 "api/utils/exceptions.py"

An exception carries four things: a human `message`, a stable `error_code`, the `http_status` to answer with, and optional `details`. There is one subclass per situation:

| HTTP | Error codes (all subclasses of `BaseAppException`) |
|---|---|
| 404 | `PROMPT_NOT_FOUND`, `VERSION_NOT_FOUND` |
| 409 | `PROMPT_ALREADY_DELETED`, `PROMPT_NOT_DELETED`, `DOMAIN_RULE_VIOLATION` |
| 422 | `INVALID_REQUEST` (bad body, bad UUID, or bad payload at the core), `INVALID_VERSION_COMPARISON` |
| 502 | `CORE_RESPONSE_ERROR` (the core answered nonsense) |
| 503 | `NATS_PUBLISH_FAILED`, `CORE_UNAVAILABLE` |
| 504 | `CORE_TIMEOUT` |
| 500 | `INTERNAL_SERVER_ERROR` (anything unforeseen) |

The mapping from a *core error code* to one of these exceptions lives in one function, `_core_error`, using a `match` statement (Python's pattern matching):

@code api/messaging/nats_publisher.py:45-66 "api/messaging/nats_publisher.py · from core code to exception"

And a single place turns every exception into the JSON the client sees:

@code api/utils/error_handlers.py:11-40 "api/utils/error_handlers.py"

@figure errors "The path of an error, from the core's reply to a message on the screen."

::: project Controllers do not catch exceptions
Look back at the route in section 7.2: there is no `try`. When something goes wrong deep inside, the exception simply travels upward until FastAPI hands it to the registered handler. That is intentional. Error handling is a *cross-cutting concern*, and putting it in one place guarantees every route answers errors in the same format: `{"error": {"code", "message", "details"}}`. A stack trace is **never** sent to the client; the generic handler logs it and answers with a harmless "Internal server error".
:::

::: warning Language of the messages
The `message` field of the api errors (and the texts of the front end) are written in Portuguese, because they are what the end user reads. Everything else, from code and comments to the error *codes* themselves, is in English. A client should rely on the `code`, never on the message, which is meant for people.
:::

## 7.6 The contract: Swagger and OpenAPI

FastAPI generates an **OpenAPI** document from the routes and models: a machine-readable description of every endpoint, request body and response. The interactive page at `/docs` (Swagger UI) is drawn from it. The front end keeps a snapshot of that document and generates its TypeScript types from it (Chapter 8), so a change in the api contract becomes a compile error in the front end instead of a surprise in production.

## 7.7 Testing the api without a network

The api has 117 unit tests, grouped by layer: `models`, `messaging`, `services`, `controllers` and `utils`. They never open a network connection:

| Layer | What the tests replace | What they check |
|---|---|---|
| `NATSPublisher` | The NATS client, with an `AsyncMock` | Subject and JSON bytes sent; every failure becomes the right exception; every core error code maps to the right exception. |
| `PromptService` | The publisher, with a mock | Each of the 11 methods sends exactly one message, with the exact subject and payload. |
| Controllers | `PromptService`, via FastAPI's dependency override | Each route returns 200 with the service's data; bad input returns the standard 422; service errors become the standard JSON. |
| `utils` | Nothing: they are pure | Exceptions carry the right code and status; handlers never leak internals. |

::: checkpoint
1. Why does `NATSPublisher.request` return only `wrapper.data` instead of the whole reply?
2. Why do the controllers have no `try / except`?
3. Which three things can make the api answer `503` or `504` without any bug in the code?
:::

::: summary
- The api is a gateway: it validates shape, sends one NATS request per use case and returns the core's `data` untouched.
- Only `messaging/` talks to NATS; controllers stay one line long.
- Errors are subclasses of `BaseAppException`, created from the core's error codes, and rendered by central handlers into one JSON format.
- FastAPI publishes the contract as OpenAPI; the front end builds its types from it.
- Everything is unit-tested with NATS mocked.
:::
