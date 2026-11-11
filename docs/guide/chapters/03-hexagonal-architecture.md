::: chapter 3 "Hexagonal architecture" "Why the core has five folders and who may talk to whom"

::: question
Why is the core not "a bunch of files together", and which rule keeps the order?
:::

## 3.1 The idea: protect the rules from the technology

**Hexagonal architecture** (also called *Ports and Adapters*, proposed by Alistair Cockburn) is born from an observation: technologies change, business rules last. Today we use NATS and SQLite; tomorrow it could be HTTP and PostgreSQL. If the rules ("only one active version", "deleting is soft") are mixed with the database code, every change of technology becomes a dangerous surgery.

::: analogy The wall socket and the travel adapter
Your laptop (the rules) does not know whether the energy comes from a hydroelectric plant or from a generator. It only knows the shape of the plug (the *port*). In every country you use a different adapter, and the laptop stays untouched. In software: the core defines the ports; the adapters plug the technologies in.
:::

@figure rings "The layers as rings: the core (domain) in the center, the external world at the edge. Everything that comes in or goes out crosses the rings."

Notice the whole system we saw in Chapter 1 sits at the border of this figure. The api, the `nats` CLI and the front end are all "NATS clients" in the left box; the SQLite file is the box on the right. The core never imports any of them.

## 3.2 The five blocks

An analogy helps to fix the role of each folder. Think of a restaurant:

| Folder | Role | In the restaurant | Example in the project |
|---|---|---|---|
| `domain/` | The business rules, in pure Python | The recipes and the kitchen hygiene rules | `Prompt`, `PromptStatus`, `VersionDiff` |
| `app/` | Use cases: coordinates the flow | The chef who coordinates the preparation of each order | `CreateVersionUseCase` |
| `port/` | Contracts the core demands from the world | The order form and the supplier contract | `PromptRepository`, `UnitOfWork` |
| `adapter/` | Translates and connects technologies | The waiter (translates the customer) and the delivery person (supplier) | `SqlAlchemyPromptRepository`, `MessagingAdapter` |
| `infra/` | Only configures the technologies | The equipment: stove, fridge, phone | `create_engine`, `NatsClient` |

There is a sixth character, outside the layer folders: `main.py`, the **composition root**. It is the only place that knows everyone and "connects the wires": it creates the adapters, hands them to the use cases and starts the service (Chapter 6).

## 3.3 The Dependency Rule

The whole discipline of the architecture fits in one sentence: **dependencies always point inward**. The adapters know the application and the domain; the application knows the domain and the ports; the domain knows nobody. "Knowing", here, literally means `import`.

@figure deps "The dependency rule. The arrows show who imports whom. Notice: no arrow starts in domain/."

::: project This rule is verified, not just wished for
During development, we ran a search for any mention of `sqlalchemy`, `nats`, `structlog`, `rich`, `adapter`, `infra` and even `logging` inside `domain/`, `app/` and `port/`. The result was always "no occurrences". And the type checker (`pyright`) finished with 0 errors. The core really does not know that NATS or SQLite exist.
:::

## 3.4 Why it is worth it (and what it costs)

| Benefit | How it appeared in this project |
|---|---|
| Test without technology | The whole domain and every use case were tested with a fake in-memory repository: no database, no NATS. |
| Swap parts | Replacing SQLite with PostgreSQL would touch only `adapter/persistence` and the `infra/` configuration. |
| Evolve | Exposing the system over HTTP became a *new project* (`api/`) beside the messaging adapter, and the rules did not change. |
| Understand | Given a file, you know which layer it belongs to, and therefore what it may (and may not) do. |

::: warning The cost
More folders and more "ceremony". For a 100-line script this would be overkill. Here it pays off because of the didactic nature of the project and because it was designed to grow: architecture is always a conscious trade.
:::

## 3.5 The patterns you will find

Architectures usually come with *design patterns*: named solutions for recurring problems. These are the ones in Prompt Vault:

| Pattern | In one sentence | Where |
|---|---|---|
| Aggregate (DDD) | A group of objects treated as a unit, with a "root" that protects the rules. | `Prompt` (root) + `PromptVersion` |
| Repository | Hides the storage behind a "collection" interface. | `PromptRepository` |
| Unit of Work | Groups several operations into an "all or nothing" transaction. | `UnitOfWork` |
| Strategy | Swaps one algorithm for another without touching who uses it. | `DiffStrategy` / `LineDiffStrategy` |
| Factory | A function that manufactures ready-to-use objects. | use case factories in `main.py` |
| Dependency Injection | Whoever uses a piece receives it ready, instead of creating it. | constructors of the use cases |
| Command / Query | Separate what changes from what only reads. | `app/commands` and `app/queries` |
| Domain Events | Record "facts that happened" for anyone who wants to react. | `events.py` and `pull_events()` |
| Gateway / Facade | A thin entry point that hides a complex backend. | the `api/` project |
| DTO | A plain object that only carries data across a boundary. | `models/` in the api, `types.ts` in the front |

::: checkpoint
1. Why can `domain` not import `sqlalchemy`?
2. Which layer(s) would you change to swap SQLite for PostgreSQL?
3. What is the difference between a port and an adapter?
:::

::: summary
- Hexagonal architecture separates rules (durable) from technology (replaceable).
- Five blocks: domain, app, port, adapter, infra, plus the `main.py` that wires them.
- Golden rule: dependencies point inward; the domain knows nobody.
- Port = contract (Protocol). Adapter = concrete implementation of that contract.
:::
