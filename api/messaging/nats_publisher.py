from typing import Any

from pydantic import ValidationError
from nats.aio.client import Client as NATSClient
from nats.errors import Error as NATSError
from nats.errors import NoRespondersError
from nats.errors import TimeoutError as NATSTimeoutError

from utils.exceptions import (
    BaseAppException,
    CoreResponseException,
    CoreTimeoutException,
    CoreUnavailableException,
    DomainRuleException,
    InvalidRequestException,
    InvalidVersionComparisonException,
    NATSPublishException,
    PromptAlreadyDeletedException,
    PromptNotDeletedException,
    PromptNotFoundException,
    VersionNotFoundException,
)
from models.response_models import ApiWrapper
from utils.json_utils import decode_json_object, encode_json


def _domain_error(message: str) -> BaseAppException:
    """Fallback for the generic core code "domain_error": match the message text.

    The core sends one code per business rule (see _core_error), so this only covers
    rules it has no dedicated code for. Unrecognised ones become DomainRuleException.
    """
    details = {"reason": message}
    if message.startswith("Version ") and "does not exist" in message:
        return VersionNotFoundException(details)
    if "Cannot compare version" in message:
        return InvalidVersionComparisonException(details)
    if "not deleted" in message:
        return PromptNotDeletedException(details)
    if "deleted prompt" in message:
        return PromptAlreadyDeletedException(details)
    return DomainRuleException(details)


def _core_error(code: str, message: str, payload: dict[str, Any]) -> BaseAppException:
    match code:
        case "not_found":
            return PromptNotFoundException(payload.get("prompt_id"))
        case "invalid_payload":
            return InvalidRequestException({"reason": message})
        case "version_not_found":
            return VersionNotFoundException({"reason": message})
        case "invalid_version_comparison":
            return InvalidVersionComparisonException({"reason": message})
        case "prompt_deleted":
            return PromptAlreadyDeletedException({"reason": message})
        case "prompt_not_deleted":
            return PromptNotDeletedException({"reason": message})
        case "invalid_prompt":
            return DomainRuleException({"reason": message})
        case "domain_error":
            return _domain_error(message)
        case "timeout":
            return CoreTimeoutException()
        case _:
            return CoreResponseException(f"internal core error ({code})")


class NATSPublisher:
    """The only place in the API that talks to NATS. Raises only BaseAppException."""

    def __init__(self, nc: NATSClient) -> None:
        self.nc = nc

    async def publish(self, subject: str, payload: dict[str, Any]) -> None:
        """Fire-and-forget."""
        try:
            await self.nc.publish(subject, encode_json(payload))
        except (NATSError, OSError, TypeError, ValueError) as exc:
            raise NATSPublishException(str(exc)) from exc

    async def request(
        self, subject: str, payload: dict[str, Any], timeout: float = 3.0
    ) -> Any:
        """Request/reply. Returns the `data` of the Core's wrapper or raises a BaseAppException."""
        try:
            msg = await self.nc.request(subject, encode_json(payload), timeout=timeout)
        except (NATSTimeoutError, TimeoutError) as exc:
            raise CoreTimeoutException() from exc
        except NoRespondersError as exc:
            raise CoreUnavailableException() from exc
        except (NATSError, OSError, TypeError, ValueError) as exc:
            raise NATSPublishException(str(exc)) from exc

        envelope = decode_json_object(msg.data)
        try:
            wrapper = ApiWrapper[Any].model_validate(envelope)
        except ValidationError as exc:
            raise CoreResponseException("invalid envelope") from exc
        if not wrapper.ok:
            error = envelope.get("error")
            error = error if isinstance(error, dict) else {}
            raise _core_error(
                str(error.get("code", "internal_error")),
                str(error.get("message", "")),
                payload,
            )
        return wrapper.data
