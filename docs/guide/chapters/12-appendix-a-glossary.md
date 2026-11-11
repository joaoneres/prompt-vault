::: chapter A "Glossary" "The terms of this guide in plain language"

| Term | Meaning |
|---|---|
| Adapter | A piece that translates between the core and a concrete technology (NATS, SQLite). |
| Aggregate | A group of objects treated as a unit, with a root that protects the rules (Prompt + versions). |
| Asynchronous | Not standing still while waiting: while one task waits, another moves on (`async/await`). |
| Axios | The HTTP client library used by the front end. |
| Broker | The central server that receives and distributes messages (the NATS server). |
| Command | A use case that changes the state of the system. |
| Component (React) | A function that returns a piece of screen. |
| Composition root | The single place that creates and connects all the pieces (`main.py`). |
| Context manager | The `with` structure that guarantees something is opened and closed correctly. |
| Controller | In the api, the function bound to an HTTP route. It stays one line long. |
| CORS | The browser rule that decides whether a page may call an API at another address. |
| Correlation id | A tracking label that accompanies a message in replies, events and logs. |
| Dataclass | A class whose constructor and comparisons are generated automatically. |
| Dependency injection | Handing an object the pieces it needs, instead of letting it create them. |
| Diff | A comparison showing what changed between two texts. |
| Domain event | An immutable fact in the past that happened in the domain ("version activated"). |
| Duck typing | "If it walks and quacks like a duck...": the shape of the object counts, not its inheritance. |
| DTO | A plain object that only carries data across a boundary. |
| Envelope | The standard reply format: `ok`, `correlation_id` and `data` or `error`. |
| Gateway | A thin entry point in front of a backend; here, the api. |
| Hexagonal | An architecture of "ports and adapters" that isolates the core from the technology. |
| Invariant | A statement that can never be false ("versions numbered with no gaps"). |
| Lifespan | Code that runs when a FastAPI app starts and stops. |
| LLM | A large language model; it receives prompts and generates text. |
| Mapper | Code that translates between the domain model and the table model. |
| NATS | A messaging system based on subjects, with publish/subscribe and request/reply. |
| OpenAPI | A machine-readable description of an HTTP API; the source of Swagger and of the front end's types. |
| ORM | Maps database tables to classes of the language (SQLAlchemy). |
| Outbox | A pattern that records events together with the data so they are never lost. |
| Port | A contract (Protocol) that the core demands from the outside world. |
| Prompt | An instruction text sent to a language model. |
| Protocol | A description of the methods a class must have, without inheritance. |
| Proxy (Vite) | A development server feature that forwards `/api` calls to the real API. |
| Pydantic | A library that validates data against type annotations. |
| Query | A use case that only reads. |
| React | A library for building user interfaces from components. |
| Request / reply | A conversation in which the asker waits for the answer. |
| Rollback | Undoing everything a transaction did; also, activating an old version. |
| Soft delete | Deleting by "hiding": the data stays stored and is recoverable. |
| SPA | Single-page application: one page that redraws itself and talks to an API. |
| State (React) | Data a component remembers between draws. |
| Strategy | A pattern to swap an algorithm without touching whoever uses it. |
| Subject | The "topic" (channel) where NATS messages are published. |
| Timeout | The maximum waiting time before giving up. |
| Toast | A small temporary notification on the screen. |
| Transaction | A set of operations that is "all or nothing". |
| Type hint | An annotation of the expected type of a value (`str \| None`). |
| Unit of Work | An object that manages a transaction and confirms or undoes everything. |
| uv | A tool that creates the Python environment and installs dependencies. |
| Vite | The development server and bundler of the front end. |
| WAL | The SQLite mode in which reading and writing coexist, via a "scratch page" of writes. |
