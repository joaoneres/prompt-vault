::: chapter 5 "Ports and Application" "Contracts and use cases: how a request becomes an action without depending on technology"

::: question
How does the core execute an action ("create a version") without knowing where the data lives or through which door the request arrived?
:::

## 5.1 Ports: what the core demands from the world

The `port/` folder is tiny (57 lines) and very important. It contains three contracts, all written as Protocols. Each one expresses a need: "I need to store and find prompts", "I need to tell the world about events", "I need a transaction".

| Port | The need | Methods |
|---|---|---|
| `PromptRepository` | Store and retrieve prompts as if they were a collection | `get`, `save`, `list_active`, `list_deleted` |
| `EventPublisher` | Tell the world about the domain events | `publish(events)` |
| `UnitOfWork` | Group operations into an "all or nothing" transaction | `prompts`, `commit`, `rollback`, `async with` |

@code core/src/port/event_publisher.py:1-8 "core/src/port/event_publisher.py"

@code core/src/port/unit_of_work.py:8-23 "core/src/port/unit_of_work.py"

::: concept Minimal contracts
A port only has what the use cases really need. There is no `delete(id)` in the repository because deleting is a rule of the domain (`prompt.delete()`), followed by a save. The repository decides nothing: it only stores and fetches.
:::

## 5.2 Unit of Work: the "all or nothing" transaction

::: analogy The bank transfer
Transferring 100 from account A to account B is two operations: debit A and credit B. If the power goes out between the two, the money would vanish. A *transaction* guarantees that either both happen or neither does. The Unit of Work is the object that opens this "protected box" and confirms (`commit`) or undoes (`rollback`) everything.
:::

In the project: once you enter `async with uow:`, whatever is saved only counts if it reaches `commit()`. If an exception happens before it, leaving the block triggers the rollback and nothing stays stored.

## 5.3 Use cases: the orchestra

A **use case** is an action the system offers, from the point of view of whoever uses it: "create a prompt", "activate a version". The `app/` layer has 316 lines and contains exactly eleven use cases, split into two classic groups:

- **Commands (write):** change the state. They use the Unit of Work and publish events.
- **Queries (read):** only consult. They open no transaction and publish nothing.

| Use case | Kind | Orchestrates | Returns |
|---|---|---|---|
| `CreatePrompt` | command | `Prompt.create` | the `Prompt` |
| `CreateVersion` | command | `prompt.add_version(activate=...)` | the `Prompt` and the new `PromptVersion` |
| `UpdateContent` | command | `prompt.add_version(activate=True)` | the `Prompt` and the new `PromptVersion` |
| `ActivateVersion` | command | `prompt.activate_version(n)` | the `Prompt` |
| `DeletePrompt` | command | `prompt.delete()` | the `Prompt` |
| `RestorePrompt` | command | `prompt.restore()` | the `Prompt` |
| `GetPrompt` | query | repository `get` | the `Prompt` |
| `ListVersions` | query | `prompt.versions` | the `Prompt` (the adapter lists its versions) |
| `ListActivePrompts` | query | `list_active` | a list of prompts |
| `ListDeletedPrompts` | query | `list_deleted` | a list of prompts |
| `CompareVersions` | query | `prompt.diff(a, b, strategy)` | the `Prompt` and the `VersionDiff` |

::: project Use cases return the aggregate
In the first edition of this guide, `CreatePrompt` returned only an id and `ActivateVersion` returned nothing. Today every use case returns the **aggregate** (or the aggregate plus the object it created), and the adapter decides how to present it. Why? Because *presentation is not a business concern*. Returning the `Prompt` lets the adapter build the exact JSON the api and the front end need (ids, dates, which version is active) without the use case knowing anything about JSON.
:::

## 5.4 Anatomy of a use case

@code core/src/app/commands/create_version.py:17-30 "core/src/app/commands/create_version.py"

1. The constructor receives the Unit of Work and the publisher. The use case creates nothing: it only uses what was handed to it.
2. `async with self._uow` opens the transaction.
3. `require_prompt` loads the prompt (or raises `PromptNotFoundError`).
4. `prompt.add_version(...)`: the business rule is called in the domain. The use case decides nothing.
5. `save` + `commit`: persists and confirms.
6. Only after the commit are the events published and the result returned.

::: warning Why publish after the commit?
If we published before, an error while saving would leave the world knowing about something that did not happen. The cost: if publishing fails *after* the commit, the data is already saved but the event is lost. A mature solution for that is the *outbox* pattern (recording the event in the same transaction), not implemented here and recorded as a next step.
:::

## 5.5 Dependency injection and the power of the "fake"

Since the use case receives its dependencies (instead of creating them), we can hand it any object that fulfils the contract, including a fake made only for testing. That is how every use case was verified without a database and without NATS. This was the fake repository used in the tests:

```python title="Fake repository (verification script, outside the project)"
class FakeRepo:
    def __init__(self): self.store = {}
    async def get(self, i): return self.store.get(i)
    async def save(self, p): self.store[p.id] = p; log.append("save")
    async def list_active(self): return [p for p in self.store.values() if p.status is PromptStatus.ACTIVE]
    async def list_deleted(self): return [p for p in self.store.values() if p.is_deleted]
```

Six lines were enough to test the whole application. That is the prize of the architecture: the logic can be exercised in isolation. (The api uses the same trick: its tests replace the NATS publisher with a mock, as you will see in Chapter 10.)

::: project Application errors
The domain does not know how to "fetch" prompts, it only receives them. That is why whoever raises `PromptNotFoundError` ("this id does not exist") is the `app` layer, in `require_prompt`. Business-rule errors (`DomainError` and children) cross the application untouched; the messaging adapter converts them into error codes.
:::

::: checkpoint
1. What is the difference between a command and a query?
2. Why are events only published after the commit?
3. Why does the use case receive the `uow` in the constructor instead of creating it?
:::

::: summary
- Ports are three minimal contracts: repository, event publisher and unit of work.
- Use cases only coordinate: load, call the domain, save and publish. They return the aggregate.
- Commands write (with a transaction and events); queries only read.
- Dependency injection makes it possible to test with fake objects.
:::
