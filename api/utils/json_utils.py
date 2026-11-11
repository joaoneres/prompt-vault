import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from utils.exceptions import CoreResponseException


def _default(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def encode_json(data: Any) -> bytes:
    return json.dumps(data, default=_default, ensure_ascii=False).encode()


def decode_json_object(raw: bytes) -> dict[str, Any]:
    """Decode a reply from the core; anything but a JSON object is a bad response."""
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoreResponseException("response is not JSON") from exc
    if not isinstance(data, dict):
        raise CoreResponseException("response is not a JSON object")
    return data
