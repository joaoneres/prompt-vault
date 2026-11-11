from app import PromptNotFoundError
from domain import DomainError


class InvalidPayloadError(Exception):
    """The message is malformed (not JSON, missing or badly typed field)."""


def to_error(exc: BaseException) -> tuple[str, str, bool]:
    """Map an exception to (code, client-safe message, is_unexpected)."""
    if isinstance(exc, InvalidPayloadError):
        return "invalid_payload", str(exc), False
    if isinstance(exc, PromptNotFoundError):
        return "not_found", str(exc), False
    if isinstance(exc, DomainError):
        return "domain_error", str(exc), False
    if isinstance(exc, TimeoutError):
        return "timeout", "The operation timed out", True
    return "internal_error", "Internal error", True  # details stay in the logs
