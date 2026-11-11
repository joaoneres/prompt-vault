import inspect

import pytest

from utils import exceptions
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


def test_base_exception_stores_fields():
    exc = BaseAppException("msg", "CODE", 418, {"a": 1})
    assert (exc.message, exc.error_code, exc.http_status, exc.details) == ("msg", "CODE", 418, {"a": 1})
    assert str(exc) == "msg"


def test_base_exception_defaults():
    exc = BaseAppException("msg", "CODE")
    assert exc.http_status == 400
    assert exc.details == {}


def test_details_are_not_shared_between_instances():
    a, b = BaseAppException("m", "C"), BaseAppException("m", "C")
    a.details["x"] = 1
    assert b.details == {}


def test_every_exception_in_module_inherits_from_base():
    classes = [
        c for _, c in inspect.getmembers(exceptions, inspect.isclass)
        if issubclass(c, Exception) and c.__module__ == exceptions.__name__
    ]
    assert len(classes) > 1
    assert all(issubclass(c, BaseAppException) for c in classes)


@pytest.mark.parametrize(
    ("exc", "code", "status"),
    [
        (PromptNotFoundException("abc"), "PROMPT_NOT_FOUND", 404),
        (VersionNotFoundException(), "VERSION_NOT_FOUND", 404),
        (PromptAlreadyDeletedException(), "PROMPT_ALREADY_DELETED", 409),
        (PromptNotDeletedException(), "PROMPT_NOT_DELETED", 409),
        (InvalidVersionComparisonException(), "INVALID_VERSION_COMPARISON", 422),
        (DomainRuleException(), "DOMAIN_RULE_VIOLATION", 409),
        (InvalidRequestException(), "INVALID_REQUEST", 422),
        (NATSPublishException("x"), "NATS_PUBLISH_FAILED", 503),
        (CoreTimeoutException(), "CORE_TIMEOUT", 504),
        (CoreUnavailableException(), "CORE_UNAVAILABLE", 503),
        (CoreResponseException(), "CORE_RESPONSE_ERROR", 502),
    ],
)
def test_code_and_status(exc, code, status):
    assert exc.error_code == code
    assert exc.http_status == status
    assert exc.message


def test_prompt_not_found_message_includes_id():
    assert "abc" in PromptNotFoundException("abc").message
    assert PromptNotFoundException().message == "Prompt não encontrado"


def test_reason_goes_to_details():
    assert NATSPublishException("down").details == {"reason": "down"}
    assert NATSPublishException().details == {}
