::: chapter 0 "Before you begin" "Who this guide is for and how to study with it"

Welcome to the class. This guide is written for someone who has never programmed in Python (or has done it very little) and wants to understand, for real, the **Prompt Vault** project: what every piece does, why it sits where it sits, and how the pieces talk to each other. Instead of explaining technologies in the abstract, we use the project itself as a laboratory. Every code listing you will see was copied straight from the real files by the build script of this guide, and every result of an execution was obtained by running the system.

The project has grown since the first edition of this guide. It used to be a single Python service that listened to messages. It is now **three projects that work together**:

| Project | What it is | Language and main tools |
|---|---|---|
| `core/` | The business: prompts, versions, states, diff. It has no HTTP; it listens to NATS messages and stores data in SQLite. | Python 3.13, hexagonal architecture, NATS, SQLAlchemy |
| `api/` | An HTTP gateway. It validates requests, forwards each one to the core as a NATS message and turns the answer (or the error) into HTTP. | Python, FastAPI, Pydantic |
| `front/` | A browser dashboard to list, create, edit, compare, browse and recover prompts. | React, TypeScript, Vite, Tailwind CSS, Axios |

## 0.1 How to study with this guide

1. **Read in order.** Every chapter opens with a guiding question and closes with a summary. Chapters 2 to 8 also contain a *checkpoint*: three questions to fix the ideas (the answers are in Appendix D).
2. **Open the files.** When the text cites a file, open it in your editor next to the guide. Seeing the real code fixes far more than reading about it.
3. **Run the commands of Chapter 11.** Sending a message and watching the system answer turns a concept into an experience.
4. **Do not try to memorize.** The goal is to know where to look and why each thing exists.
5. **Break things on purpose.** Change a rule, run a smoke test and see which check fails. Tests exist to be read as documentation of the behavior.

## 0.2 Reading map

| Chapter | The question it answers |
|---|---|
| 1 · The problem and the solution | What is the system for, and how does anyone talk to it? |
| 2 · Essential Python | Which parts of the language do I need to read this code? |
| 3 · Hexagonal architecture | Why is the core split into five folders, and who may talk to whom? |
| 4 · Domain | Where do the business rules live, and how do they protect themselves? |
| 5 · Ports and Application | How does a request become a use case without depending on technology? |
| 6 · Adapters and Infra | How does the core connect to NATS, SQLite and the terminal? |
| 7 · The HTTP API | How do HTTP requests reach the core, and how do errors come back? |
| 8 · The front end | How does the browser application turn all of this into screens? |
| 9 · A request end to end | What happens, step by step, when someone clicks "Save" in the browser? |
| 10 · Verifying that it works | How do we know it really works? |
| 11 · Hands-on | How do I run, explore and extend the project myself? |

## 0.3 The colored boxes

::: concept
An idea or term that is new, explained slowly.
:::

::: analogy
A comparison with everyday life to anchor the idea.
:::

::: project
Where that idea appears, concretely, in the Prompt Vault code.
:::

::: warning
A common trap or an honest limitation of the project.
:::

::: lesson
Something that went wrong during development and what we learned from it.
:::

::: checkpoint
Three questions at the end of a chapter. The answers are in Appendix D.
:::
