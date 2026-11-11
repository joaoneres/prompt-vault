::: chapter 1 "The problem and the solution" "Why Prompt Vault exists and how the three projects talk to each other"

::: question
Why does this system exist, and how does a person use it, if the business core has no screen and no web address?
:::

## 1.1 Prompts, and why version them

A **prompt** is the instruction text we send to a language model (an LLM, such as Claude): "summarize the text below in three bullet points, in a formal tone". Changing a single word can change the answer a lot. Anyone who works with LLMs ends up with dozens of prompts that evolve week after week, and uncomfortable questions appear: which version worked yesterday? who changed what? can I go back?

::: analogy The document history
Think of the version history of a Google Doc, or the commits of Git. Nobody erases the past: you only add new chapters and choose which one is "in force". Prompt Vault does exactly that, specialized in prompts.
:::

## 1.2 What the system does

| Capability | NATS subject | HTTP route (api) | Behavior |
|---|---|---|---|
| Create a prompt | `prompt.create` | `POST /prompts` | Born active, with version 1 already active. |
| Add a version | `prompt.version.create` | `POST /prompts/{id}/versions` | Appends a version; it is activated only if you ask (`activate`). |
| Change the content | `prompt.content.update` | `PUT /prompts/{id}/content` | Never edits: creates a new version and activates it. |
| Activate a version | `prompt.version.activate` | `POST /prompts/{id}/activate` | Chooses which version is "in force", including an old one (rollback). |
| Delete (soft delete) | `prompt.delete` | `DELETE /prompts/{id}` | Hides the prompt but keeps everything. It can be recovered. |
| Recover | `prompt.restore` | `POST /prompts/{id}/recover` | Returns to the state the prompt had before being deleted. |
| Read | `prompt.get`, `prompt.versions.list`, `prompt.list.active`, `prompt.list.deleted` | `GET /prompts/{id}`, `/versions`, `/active`, `/deleted` | Questions that only read, never change anything. |
| Compare versions | `prompt.versions.compare` | `POST /prompts/{id}/compare` | Shows lines added, removed and unchanged between two versions (a diff). |

::: concept The rules of the game
- Every change of content creates a new version. Nothing is overwritten.
- Only one version is active per prompt, at any moment.
- History is never lost. Deleting is "soft": the prompt disappears from the active lists but stays stored.
- These rules live in the heart of the system (the `domain` layer), not scattered around the code.
:::

## 1.3 Three projects, one conversation

Look at the table of the previous section: every capability has **two doors**. The core listens to NATS subjects, and the api offers the same operations as HTTP routes. That is the central design decision of the whole system: the business core knows nothing about HTTP, browsers or web pages.

@figure system "The whole system: the browser talks HTTP to the api; the api talks NATS to the core; the core talks SQL to a file."

How do you read this figure? From left to right, a request crosses three borders. The **front** (running in a browser) sends HTTP/JSON to the **api**. The api does not hold any business rule: it turns the HTTP request into a **NATS message** and waits for the answer. The **core** receives the message, runs the use case, stores the result in **SQLite** and answers. Anything else that speaks NATS (the `nats` command-line tool, or a future service) can use the core directly, without going through the api.

::: analogy The radio dispatch center
Imagine a taxi radio dispatch center. You do not call a specific driver: you speak on a channel ("channel 7, I need a car") and whoever serves that channel answers. NATS is the center, the *subjects* are the channels, and the core is the crew that serves the channels `prompt.*`. The api is a receptionist: customers arrive at the counter (HTTP), and the receptionist talks to the radio on their behalf.
:::

Here is a real conversation, made with the NATS CLI (a command-line tool to talk to NATS):

```bash title="Terminal · real output of the system"
$ nats request prompt.create '{"name":"cli","content":"hello"}' --raw
{"ok": true, "correlation_id": "25e14cde-cb7d-4f31-9fe5-29f8cce8cb65",
 "data": {"id": "f11c267d-...", "name": "cli", "status": "active",
          "active_version_id": "c763a3ff-...", "content": "hello", ...}}
```

The answer is a JSON **envelope**: `ok` says whether it worked, `correlation_id` is a tracking label (we will meet it in Chapter 6) and `data` carries the result, here the created prompt. The api uses exactly the same envelope, then returns only the `data` part to the browser.

## 1.4 The map of the project

The project was built in phases. First the core, from the inside out (domain, then ports and application, the diff between versions and, finally, the adapters and infrastructure that connect everything to the real world). Then the HTTP api on top of it, and finally the browser front end. The repository looks like this:

```text title="Repository layout"
prompt-vault/
├── README.md, smoke_test.sh       overview · global smoke test
├── docs/                          this guide and the interactive map
├── core/
│   ├── docker-compose.yml         local NATS server
│   ├── smoke_test.sh              smoke test through the NATS CLI
│   └── src/
│       ├── main.py                composition root: wires everything   (90 lines)
│       ├── domain/                pure business rules                  (605)
│       ├── port/                  contracts (Protocols)                 (57)
│       ├── app/                   use cases                            (316)
│       ├── adapter/
│       │    ├── persistence/      SQLAlchemy + SQLite                  (288)
│       │    └── messaging/        NATS                                 (589)
│       └── infra/                 technology configuration             (150)
├── api/
│   ├── main.py                    FastAPI app, NATS lifespan            (32)
│   ├── controllers/               the HTTP router                      (115)
│   ├── services/                  PromptService                         (90)
│   ├── messaging/                 NATSPublisher                        (108)
│   ├── models/                    DTOs and the response wrapper        (118)
│   ├── utils/                     exceptions, handlers, helpers        (195)
│   └── tests/                     117 unit tests                       (695)
└── front/
    ├── openapi.json               snapshot of the api contract
    └── src/                       React app, about 1,900 lines of TypeScript
```

## 1.5 The technologies, in a table

| Technology | Version | What it is for here |
|---|---|---|
| Python | 3.13 | The language of the core and the api. |
| uv | 0.13 | Creates the environment, installs dependencies and runs programs. |
| NATS + nats-py | server 2.x · lib 2.16.0 | The message bus: the "front door" of the core. |
| SQLite | built into Python | The database: a single file. |
| SQLAlchemy + aiosqlite | 2.1.8 · 0.22.1 | Translates Python objects into table rows, asynchronously. |
| structlog and rich | 26.1.0 · 15.0.0 | Structured logs, and readable colored terminal output. |
| FastAPI, Pydantic, uvicorn | 0.162 · 2.14 · 0.54 | The HTTP gateway: routes, validation and the server. |
| pytest + pytest-asyncio | 9.2 · 1.4 | The api unit tests. |
| React, Vite, TypeScript | 19.3 · 8.3 · 5.9 | The browser application and its tooling. |
| Tailwind CSS, Axios | 4.3 · 1.21 | Styling and HTTP calls from the browser. |
| Docker Compose | n/a | Starts the NATS server with a single command. |

::: summary
- Prompt Vault versions prompts: every change is a new version; one of them is active; nothing is lost.
- The business core has no screen and no HTTP: it talks through messages on a bus (NATS).
- The api is a thin translator between HTTP and NATS; the front end is a browser client of the api.
- The core has five areas (domain, port, app, adapter, infra). The next step is to understand why, after a little Python.
:::
