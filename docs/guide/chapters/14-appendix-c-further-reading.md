::: chapter C "Going further" "Reading and documentation to continue where this guide stopped"

## C.1 Books and articles

| Work | Why read it |
|---|---|
| Hexagonal Architecture, Alistair Cockburn (article, 2005) | The origin of the idea of ports and adapters, by the author. |
| Domain-Driven Design, Eric Evans (2003) | The source of aggregates, entities, events and the "rich model". |
| Architecture Patterns with Python, Harry Percival and Bob Gregory (2020) | Repository, Unit of Work, events and messaging, all in Python. Very close to this project. |
| Patterns of Enterprise Application Architecture, Martin Fowler (2002) | The classic description of Repository and Unit of Work. |
| Designing Data-Intensive Applications, Martin Kleppmann (2017) | Messaging, consistency and why exactly-once delivery is hard. |
| Thinking in React (react.dev) | How to break a screen into components and where state should live. |

## C.2 Official documentation

| Technology | Where to look |
|---|---|
| Python (asyncio, dataclasses, typing) | docs.python.org |
| uv | docs.astral.sh/uv |
| NATS | docs.nats.io |
| SQLAlchemy 2.x (ORM and asyncio) | docs.sqlalchemy.org |
| FastAPI and Pydantic | fastapi.tiangolo.com · docs.pydantic.dev |
| pytest | docs.pytest.org |
| structlog and rich | structlog.org · rich.readthedocs.io |
| React and TypeScript | react.dev · typescriptlang.org |
| Vite and Tailwind CSS | vite.dev · tailwindcss.com |
| OpenAPI | spec.openapis.org |

::: concept How to study from here
Pick a folder (start with `domain/`), read the files from top to bottom, and for each function ask: "who calls it? what does it protect?" Then change something small, run a smoke test and see what happens. Code is learned by reading, running and breaking things on purpose.
:::
