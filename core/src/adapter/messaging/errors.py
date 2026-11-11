from app import PromptNotFoundError
from domain import (
    DomainError,
    InvalidPromptError,
    InvalidVersionComparisonError,
    PromptDeletedError,
    PromptNotDeletedError,
    VersionNotFoundError,
)


class InvalidPayloadError(Exception):
    """The message is malformed (not JSON, missing or badly typed field)."""


def to_error(exc: BaseException) -> tuple[str, str, bool]:
    """Map an exception to (code, client-safe message, is_unexpected)."""
    if isinstance(exc, InvalidPayloadError):
        return "invalid_payload", str(exc), False
    if isinstance(exc, PromptNotFoundError):
        return "not_found", str(exc), False
    if isinstance(exc, DomainError):
        return _domain_code(exc), str(exc), False
    if isinstance(exc, TimeoutError):
        return "timeout", "The operation timed out", True
    return "internal_error", "Internal error", True  # details stay in the logs


_DOMAIN_CODES: tuple[tuple[type[DomainError], str], ...] = (
    (VersionNotFoundError, "version_not_found"),
    (InvalidVersionComparisonError, "invalid_version_comparison"),
    (PromptDeletedError, "prompt_deleted"),
    (PromptNotDeletedError, "prompt_not_deleted"),
    (InvalidPromptError, "invalid_prompt"),
)


def _domain_code(exc: DomainError) -> str:
    """One code per business rule; anything else keeps the generic `domain_error`."""
    for error_type, code in _DOMAIN_CODES:
        if isinstance(exc, error_type):
            return code
    return "domain_error"
