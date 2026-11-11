import json

import pytest
from nats.errors import Error as NATSError
from nats.errors import NoRespondersError
from nats.errors import TimeoutError as NATSTimeoutError

from messaging.nats_publisher import NATSPublisher
from tests.conftest import PID, reply
from utils.exceptions import (
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


def err(code: str, message: str = "") -> dict:
    return {"ok": False, "error": {"code": code, "message": message}}


# ---- publish

async def test_publish_sends_subject_and_json_bytes(nc):
    await NATSPublisher(nc).publish("prompt.create", {"name": "olá"})
    nc.publish.assert_awaited_once()
    subject, data = nc.publish.await_args.args
    assert subject == "prompt.create"
    assert isinstance(data, bytes)
    assert json.loads(data) == {"name": "olá"}
    assert "olá".encode() in data  # no \u escapes


@pytest.mark.parametrize("failure", [NATSError(), OSError("down")])
async def test_publish_failure_becomes_app_exception(nc, failure):
    nc.publish.side_effect = failure
    with pytest.raises(NATSPublishException) as info:
        await NATSPublisher(nc).publish("s", {})
    assert info.value.http_status == 503


# ---- request: success and transport failures

async def test_request_returns_only_data_of_the_wrapper(nc):
    envelope = {"ok": True, "correlation_id": "c", "data": {"id": PID, "name": "n"}}
    nc.request.return_value = reply(envelope)
    result = await NATSPublisher(nc).request("prompt.get", {"prompt_id": PID}, timeout=1.5)
    assert result == {"id": PID, "name": "n"}
    assert nc.request.await_args.kwargs["timeout"] == 1.5
    assert json.loads(nc.request.await_args.args[1]) == {"prompt_id": PID}


@pytest.mark.parametrize("failure", [NATSTimeoutError(), TimeoutError()])
async def test_request_timeout(nc, failure):
    nc.request.side_effect = failure
    with pytest.raises(CoreTimeoutException):
        await NATSPublisher(nc).request("s", {})


async def test_request_no_responders(nc):
    nc.request.side_effect = NoRespondersError()
    with pytest.raises(CoreUnavailableException):
        await NATSPublisher(nc).request("s", {})


async def test_request_other_nats_error(nc):
    nc.request.side_effect = OSError("down")
    with pytest.raises(NATSPublishException):
        await NATSPublisher(nc).request("s", {})


async def test_request_returns_list_data_as_is(nc):
    nc.request.return_value = reply({"ok": True, "data": [{"id": 1}, {"id": 2}]})
    assert await NATSPublisher(nc).request("s", {}) == [{"id": 1}, {"id": 2}]


async def test_request_without_data_returns_none(nc):
    nc.request.return_value = reply({"ok": True})
    assert await NATSPublisher(nc).request("s", {}) is None


@pytest.mark.parametrize("envelope", [{"data": {}}, {"ok": "maybe", "data": {}}])
async def test_request_invalid_envelope(nc, envelope):
    nc.request.return_value = reply(envelope)
    with pytest.raises(CoreResponseException):
        await NATSPublisher(nc).request("s", {})


@pytest.mark.parametrize("raw", [b"not json", b"[1, 2]"])
async def test_request_invalid_reply(nc, raw):
    msg = reply({})
    msg.data = raw
    nc.request.return_value = msg
    with pytest.raises(CoreResponseException):
        await NATSPublisher(nc).request("s", {})


# ---- request: core errors

async def test_not_found_carries_prompt_id(nc):
    nc.request.return_value = reply(err("not_found"))
    with pytest.raises(PromptNotFoundException) as info:
        await NATSPublisher(nc).request("prompt.get", {"prompt_id": PID})
    assert PID in info.value.message
    assert info.value.http_status == 404


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Version 9 does not exist in this prompt", VersionNotFoundException),
        ("Cannot compare version 2 with itself", InvalidVersionComparisonException),
        ("Cannot restore a prompt that is not deleted", PromptNotDeletedException),
        ("Cannot activate a deleted prompt; restore it first", PromptAlreadyDeletedException),
        ("something new", DomainRuleException),
    ],
)
async def test_domain_error_mapping(nc, message, expected):
    nc.request.return_value = reply(err("domain_error", message))
    with pytest.raises(expected) as info:
        await NATSPublisher(nc).request("s", {})
    assert info.value.details == {"reason": message}


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("invalid_payload", InvalidRequestException),
        ("timeout", CoreTimeoutException),
        ("internal_error", CoreResponseException),
        ("whatever", CoreResponseException),
    ],
)
async def test_other_core_error_codes(nc, code, expected):
    nc.request.return_value = reply(err(code, "msg"))
    with pytest.raises(expected):
        await NATSPublisher(nc).request("s", {})


async def test_malformed_error_envelope_is_handled(nc):
    nc.request.return_value = reply({"ok": False, "error": "oops"})
    with pytest.raises(CoreResponseException):
        await NATSPublisher(nc).request("s", {})
