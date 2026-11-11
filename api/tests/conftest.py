import json
from unittest.mock import AsyncMock, MagicMock

import pytest

PID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def prompt_id() -> str:
    return PID


@pytest.fixture
def nc() -> MagicMock:
    """Fake NATS client: no network."""
    client = MagicMock()
    client.publish = AsyncMock()
    client.request = AsyncMock()
    return client


def reply(data: dict) -> MagicMock:
    msg = MagicMock()
    msg.data = json.dumps(data).encode()
    return msg
