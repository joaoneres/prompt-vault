from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import structlog

_current: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _current.get()


@contextmanager
def correlation_scope(correlation_id: str) -> Iterator[None]:
    """Make the id available to the publisher and to every log line inside the block."""
    token = _current.set(correlation_id)
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    try:
        yield
    finally:
        structlog.contextvars.unbind_contextvars("correlation_id")
        _current.reset(token)
