import json
from datetime import datetime
from enum import Enum
from uuid import UUID

import pytest

from utils.exceptions import CoreResponseException
from utils.json_utils import decode_json_object, encode_json


class Color(Enum):
    RED = "red"


def test_encode_returns_bytes():
    assert isinstance(encode_json({"a": 1}), bytes)


def test_encode_special_types():
    uid = UUID("11111111-1111-1111-1111-111111111111")
    data = json.loads(encode_json({"id": uid, "at": datetime(2026, 1, 2, 3, 4), "c": Color.RED}))
    assert data == {"id": str(uid), "at": "2026-01-02T03:04:00", "c": "red"}


def test_encode_keeps_accents():
    assert "ação".encode() in encode_json({"t": "ação"})


def test_encode_rejects_unknown_types():
    with pytest.raises(TypeError):
        encode_json({"x": object()})


def test_decode_object():
    assert decode_json_object(b'{"ok": true}') == {"ok": True}


@pytest.mark.parametrize("raw", [b"nope", b"\xff\xfe", b"[1]", b"3", b""])
def test_decode_invalid_raises_core_response_exception(raw):
    with pytest.raises(CoreResponseException):
        decode_json_object(raw)
