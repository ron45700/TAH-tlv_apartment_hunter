"""The one place that talks to the model provider. `send(request) -> response` as a plain dict.

The failure shapes the spike never saw (a 429, a 5xx, a timeout) are mapped from the documentation
and from `openai` 3.24.0's exception classes (`ASSUMPTIONS.md` O13, DECISIONS.md #181).
"""

from typing import Any, Protocol

import httpx2
import openai

from tlv_hunter.classify.base import ErrorKind

TIMEOUT_SECONDS = 60.0  # DECISIONS.md #179

_SPEND_LIMIT_CODES = {"project_spend_limit_exceeded", "organization_spend_limit_exceeded"}
# The error-codes guide lists `credit_balance_exhausted`; `insufficient_quota` is the older name.
_QUOTA_CODES = {
    "credit_balance_exhausted",
    "organization_usage_limit_exceeded",
    "insufficient_quota",
}


class TransportError(Exception):
    def __init__(
        self,
        kind: ErrorKind,
        *,
        status: int | None = None,
        code: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(" ".join(str(part) for part in (kind, status, code) if part is not None))
        self.kind = kind
        self.status = status
        self.code = code
        self.retry_after = retry_after


class ModelTransport(Protocol):
    def send(self, request: dict[str, Any]) -> dict[str, Any]: ...


class OpenAITransport:
    """The key is held by the SDK client only, never logged. The SDK's own retries are off: the
    job retries, so that every attempt passes the cap check (DECISIONS.md #182)."""

    def __init__(self, api_key: str, *, http_client: httpx2.Client | None = None) -> None:
        self._client = openai.OpenAI(
            api_key=api_key, timeout=TIMEOUT_SECONDS, max_retries=0, http_client=http_client
        )

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.responses.create(**request)
        except openai.APITimeoutError as error:
            raise TransportError("timeout") from error
        except openai.APIConnectionError as error:
            raise TransportError("network") from error
        except openai.APIStatusError as error:
            raise _status_error(error) from error
        return response.model_dump(mode="json")


def _status_error(error: openai.APIStatusError) -> TransportError:
    status = error.status_code
    code = error.code
    if status == 429:
        if code in _SPEND_LIMIT_CODES:
            return TransportError("spend_limit", status=status, code=code)
        if code in _QUOTA_CODES:
            return TransportError("quota", status=status, code=code)
        return TransportError(
            "rate_limit",
            status=status,
            code=code,
            retry_after=_retry_after(error.response.headers.get("retry-after")),
        )
    if status >= 500:
        return TransportError("server", status=status, code=code)
    if status in (401, 403):
        return TransportError("auth", status=status, code=code)
    if status == 404:
        return TransportError("not_found", status=status, code=code)
    return TransportError("bad_request", status=status, code=code)


def _retry_after(value: str | None) -> float | None:
    """Seconds, as the rate-limits guide documents it; another form is ignored."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
