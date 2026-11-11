import logging

import structlog
from rich.logging import RichHandler


def configure_logging(level: str = "INFO") -> None:
    """Structured logging: structlog -> stdlib logging -> rich (terminal)."""
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]
    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(
                colors=False, exception_formatter=structlog.dev.rich_traceback
            ),
        ],
    )
    # RichHandler prints time and level; the renderer adds event + context and, through
    # structlog's own rich_traceback formatter, the exception. rich_tracebacks must stay off:
    # RichHandler would bypass the structlog formatter and print the raw event dict instead.
    handler = RichHandler(rich_tracebacks=False, show_path=False, markup=False)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
