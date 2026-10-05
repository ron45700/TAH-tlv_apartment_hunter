"""The SDK's errors mapped to the transport's kinds, through `httpx2.MockTransport` (no socket).

401 and 400 use the bodies the spike captured (read in place); the 429, 5xx and timeout shapes come
from the documentation (`ASSUMPTIONS.md` O13, DECISIONS.md #181).
"""

from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from tests.conftest import load_openai_spike
from tlv_hunter.classify.transport import OpenAITransport, TransportError

REQUEST = {"model": "gpt-6-luna", "input": "x", "store": False, "max_output_tokens": 16}


def transport(handler: Callable[[httpx2.Request], httpx2.Response]) -> OpenAITransport:
    client = httpx2.Client(transport=httpx2.MockTransport(handler))
    return OpenAITransport("sk-test-not-a-key", http_client=client)


def answering(status: int, body: Any, headers: dict[str, str] | None = None):
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json=body, headers=headers or {})

    return handler


def error_body(code: str | None, kind: str = "requests") -> dict[str, Any]:
    return {"error": {"message": "...", "type": kind, "param": None, "code": code}}


def failure(handler) -> TransportError:
    with pytest.raises(TransportError) as caught:
        transport(handler).send(REQUEST)
    return caught.value


def test_a_completed_response_comes_back_as_a_dict() -> None:
    body = load_openai_spike("none_t0_p1_01")["response"]
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json=body)

    response = transport(handler).send(REQUEST)
    assert (response["status"], response["model"]) == ("completed", "gpt-6-luna")
    assert response["usage"] == body["usage"]
    assert len(sent) == 1 and sent[0].url.path.endswith("/responses")


def test_the_sdk_does_not_retry() -> None:
    """The job retries, so that each attempt passes the cap (DECISIONS.md #182)."""
    calls: list[int] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(1)
        return httpx2.Response(503, json=error_body("server_is_overloaded"))

    failure(handler)
    assert len(calls) == 1


def test_a_wrong_key_is_auth() -> None:
    body = load_openai_spike("probe_wrong_key")["error"]["body"]
    error = failure(answering(401, body))
    assert (error.kind, error.status, error.code) == ("auth", 401, "invalid_api_key")


def test_a_refused_schema_is_bad_request() -> None:
    body = load_openai_spike("probe_schema")["error"]["body"]
    error = failure(answering(400, body))
    assert (error.kind, error.code) == ("bad_request", "invalid_json_schema")


@pytest.mark.parametrize(
    ("status", "code", "kind"),
    [
        (429, "project_spend_limit_exceeded", "spend_limit"),
        (429, "organization_spend_limit_exceeded", "spend_limit"),
        (429, "credit_balance_exhausted", "quota"),
        (429, "organization_usage_limit_exceeded", "quota"),
        (429, "insufficient_quota", "quota"),
        (429, "slow_down", "rate_limit"),
        (429, None, "rate_limit"),
        (500, None, "server"),
        (503, "server_is_overloaded", "server"),
        (403, None, "auth"),
        (404, "model_not_found", "not_found"),
        (422, None, "bad_request"),
    ],
)
def test_status_errors(status: int, code: str | None, kind: str) -> None:
    error = failure(answering(status, error_body(code)))
    assert (error.kind, error.status) == (kind, status)


@pytest.mark.parametrize(("header", "seconds"), [("7", 7.0), ("1.5", 1.5), ("soon", None)])
def test_a_rate_limit_carries_retry_after_in_seconds(header: str, seconds: float | None) -> None:
    error = failure(answering(429, error_body("slow_down"), {"retry-after": header}))
    assert error.retry_after == seconds


def test_a_timeout_and_a_network_error() -> None:
    def timing_out(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=request)

    def refusing(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    assert failure(timing_out).kind == "timeout"
    assert failure(refusing).kind == "network"


def test_the_key_appears_in_no_error() -> None:
    error = failure(answering(401, error_body("invalid_api_key")))
    assert "sk-test-not-a-key" not in str(error)
