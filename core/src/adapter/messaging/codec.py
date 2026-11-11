import json
import uuid
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from .errors import InvalidPayloadError

CORRELATION_HEADER = "X-Correlation-Id"


def _json_default(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def encode(data: Any) -> bytes:
    return json.dumps(data, default=_json_default, ensure_ascii=False).encode()


def decode_payload(data: bytes) -> dict[str, Any]:
    if not data:
        return {}
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidPayloadError("Payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidPayloadError("Payload must be a JSON object")
    return payload


def require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise InvalidPayloadError(f"Field '{key}' is required and must be a string")
    return value


def require_uuid(payload: Mapping[str, Any], key: str) -> UUID:
    value = require_str(payload, key)
    try:
        return UUID(value)
    except ValueError as exc:
        raise InvalidPayloadError(f"Field '{key}' must be a valid UUID") from exc


def require_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidPayloadError(f"Field '{key}' is required and must be an integer")
    return value


def optional_bool(payload: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise InvalidPayloadError(f"Field '{key}' must be a boolean")
    return value


def resolve_correlation_id(headers: Mapping[str, str] | None, payload: Mapping[str, Any]) -> str:
    """Header first, then the payload field, otherwise a fresh id."""
    from_header = (headers or {}).get(CORRELATION_HEADER)
    from_payload = payload.get("correlation_id")
    if from_header:
        return from_header
    if isinstance(from_payload, str) and from_payload:
        return from_payload
    return str(uuid.uuid4())


def ok_envelope(correlation_id: str, data: Any = None) -> bytes:
    return encode({"ok": True, "correlation_id": correlation_id, "data": data})


def error_envelope(
    correlation_id: str, code: str, message: str, *, subject: str | None = None
) -> bytes:
    envelope: dict[str, Any] = {
        "ok": False,
        "correlation_id": correlation_id,
        "error": {"code": code, "message": message},
    }
    if subject is not None:
        envelope["subject"] = subject
    return encode(envelope)
