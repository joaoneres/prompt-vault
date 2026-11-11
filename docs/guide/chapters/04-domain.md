::: chapter 4 "Domain: the heart" "Where the business rules live, and how they protect themselves"

::: question
Where do the rules of the system live, and what stops someone from breaking them?
:::

The folder `core/src/domain/` has 605 lines and a rare property: nothing in it knows that a database, a network or a terminal exists. It is pure Python. That makes it easy to test and to understand; it is where the business "lives".

## 4.1 Rich modeling, not anemic

An **anemic model** is made only of data; the rules are scattered among whoever uses it. A **rich model** does the opposite: the object itself knows how to protect itself. Compare:

```python title="Illustration of the difference (not the full code)"
prompt.status = "deleted"          # anemic: anyone changes it, whenever they want, checking nothing
prompt.delete()                    # rich: the Prompt validates the transition, stores the time, records the event
```

All of Prompt Vault's domain follows the second approach: to change something, you *ask the object*, and it decides.

## 4.2 The aggregate: Prompt and its versions

In the jargon of Domain-Driven Design, an **aggregate** is a set of objects treated as a unit, with a *root* that is the only entry point. Here the root is `Prompt`: versions are only born by its hands. That is why the numbering of versions (1, 2, 3...) is never wrong: nobody else can create them.

| Method of Prompt | What it does | Event recorded |
|---|---|---|
| `Prompt.create(name, content)` | Creates an active prompt, with version 1 active. | `PromptCreated` |
| `add_version(content, activate=False)` | Appends the next version; activates it only if asked. | `PromptVersionAdded` (+ `PromptVersionActivated`) |
| `activate_version(n)` | Starts serving version `n`. If it already is the active one, does nothing. | `PromptVersionActivated` |
| `deactivate()` / `reactivate()` | Switches the prompt off / on. | `PromptDeactivated` / `PromptReactivated` |
| `delete()` / `restore()` | Soft delete and recovery. | `PromptDeleted` / `PromptRestored` |
| `diff(a, b, strategy)` | Compares two versions. Only reads. | none |
| `Prompt.rehydrate(...)` | Rebuilds a prompt coming from storage, validating the rules. | none |

@code core/src/domain/entities/prompt.py:201-213 "core/src/domain/entities/prompt.py · add_version"

Look at the order: (1) refuse if the prompt is deleted; (2) create the version (which validates the content by itself); (3) store it; (4) update the date; (5) record the event; (6) only then activate, if requested. None of these decisions leaked out of the domain.

## 4.3 Immutable versions and the active-version pointer

There are two separate ideas, and mixing them up is the most common beginner's mistake: the **versions** (content, immutable) and the **pointer** that says which of them is "in force". Changing the active version only moves the pointer; nobody rewrites the past.

@figure pointer "Versions never change; only the 'active' pointer moves. Going back (rollback) is just pointing to an old version."

## 4.4 The life cycle: a state machine

A prompt is always in exactly one of three states, `ACTIVE`, `INACTIVE` or `DELETED`, and can only move from one to another along permitted paths. We call this a **state machine**. It is written explicitly, in a transition table anyone can read:

@figure states "The states and the permitted transitions. Only restore() leaves DELETED, and it returns to the state the prompt had before being deleted."

@code core/src/domain/status.py:1-20 "core/src/domain/status.py"

Deleting is *soft*: no row is destroyed. The prompt stores `deleted_at` and the state it was in before. When restored, it goes back exactly there:

@code core/src/domain/entities/prompt.py:246-262 "core/src/domain/entities/prompt.py · delete and restore"

## 4.5 Invariants: what is always true

An **invariant** is a statement that can never be false. The domain guarantees all of these; whoever tries to violate them receives a specific exception:

| Invariant | Where it is guaranteed | Error |
|---|---|---|
| Name and content cannot be blank | `Prompt.__init__` and `PromptVersion.__post_init__` | `InvalidPromptError` |
| Versions numbered 1, 2, 3... with no gaps | `add_version` and `Prompt.__init__` | `InvalidPromptError` |
| The active version must exist | `activate_version` (via `get_version`) | `VersionNotFoundError` |
| A deleted prompt receives and activates no versions | `_ensure_not_deleted` | `PromptDeletedError` |
| Only what is deleted can be restored | `restore` | `PromptNotDeletedError` |
| Only permitted state transitions exist | `PromptStatus.can_transition_to` | `InvalidStateTransitionError` |
| `deleted_at` is filled if and only if the state is DELETED | `Prompt.__init__` | `InvalidPromptError` |
| Comparing requires two distinct, existing versions | `Prompt.diff` | `InvalidVersionComparisonError` |

These exceptions matter beyond the core. In Chapter 6 you will see the messaging adapter give each of them a *code* in the reply (`version_not_found`, `prompt_not_deleted`, ...), and in Chapter 7 the api turn each code into an HTTP status.

## 4.6 Domain events: facts that happened

When something relevant happens, the aggregate records an **event**: a fact, in the past, immutable ("version 3 was activated"). Important: the domain only *records*; whoever decides what to do with the events (publish them on NATS, for example) is an outer layer, through the `pull_events()` method, which returns the list and empties it.

@code core/src/domain/events.py:1-19 "core/src/domain/events.py"

There are seven events: `PromptCreated`, `PromptVersionAdded`, `PromptVersionActivated`, `PromptDeactivated`, `PromptReactivated`, `PromptDeleted`, `PromptRestored`. They leave the system ready for an event-driven architecture: other services can react to changes without Prompt Vault knowing they exist.

## 4.7 The diff and the Strategy pattern

Comparing two versions is a business rule, so it lives in the domain. The result is a neutral object (no HTML, no colors, no screen), made of `DiffEntry` items (each line, with the kind of change: `ADDED`, `REMOVED`, `MODIFIED` or `UNCHANGED`). Whoever presents it decides how to show it. (The api and the front end, later, show it as lines of a split view.)

The comparison *algorithm*, however, is swappable. `Prompt.diff` receives a strategy: any object with a `name` and a `diff(old, new)` method (a Protocol, remember?):

@code core/src/domain/entities/prompt.py:185-198 "core/src/domain/entities/prompt.py · diff"

The default strategy, `LineDiffStrategy`, compares line by line using the `difflib` module of the Python standard library. Its core is this loop, which translates the *operations* of `difflib` into entries of our model:

@code core/src/domain/diff/line_diff.py:16-39 "core/src/domain/diff/line_diff.py · the main loop"

A real example, executed on the system. Version 1: `line1 / line2 / line3 / line4`. Version 2: `line1 / line2 changed / line4 / line5`. The diff returned was:

| Kind | Old line | New line | Old text | New text |
|---|---|---|---|---|
| unchanged | 1 | 1 | line1 | line1 |
| modified | 2 | 2 | line2 | line2 changed |
| removed | 3 | none | line3 | none |
| unchanged | 4 | 3 | line4 | line4 |
| added | none | 4 | none | line5 |

::: project Extending without breaking anything
To create a "word by word" comparison, you only write a new class with `name` and `diff`, and hand it to the use case in `main.py`. The domain, the `CompareVersions` use case and the messaging adapter stay exactly as they are. That is the gain of the Strategy pattern.
:::

## 4.8 A lesson the tests taught

::: lesson The bug the smoke test found
In the first version of the domain, `restore()` worked even on prompts that were not deleted, and, since there was no stored previous state, it silently deactivated the prompt. Worse: `deactivate()` and `reactivate()` accepted deleted prompts, leaving a contradictory state (deleted but "active") that the domain itself refuses when loading, so the prompt would be saved and then become impossible to read.

The end-to-end test expected an error when restoring a non-deleted prompt and did not get one. The fix was three short guards (the `PromptNotDeletedError` and the `_ensure_not_deleted` you saw above). Moral: rules belong to the domain, and testing the system for real finds holes that reading the code does not show.
:::

::: checkpoint
1. Why is `PromptVersion` `frozen` (immutable)?
2. What happens if we call `restore()` on an active prompt?
3. What would you implement to compare two versions word by word?
:::

::: summary
- The `domain` is pure Python: rules, states, events and the diff, with no technology.
- `Prompt` is the root of the aggregate; `PromptVersion` is immutable; only the active-version pointer moves.
- The life cycle is an explicit state machine; deleting is soft and reversible.
- Invariants are protected by specific exceptions; events record facts that happened.
- The diff uses the Strategy pattern: the algorithm is swappable without touching anything else.
:::
