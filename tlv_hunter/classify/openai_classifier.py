"""`classify(RawPost) -> Listing` through the OpenAI Responses API (`PHASE_2.md` 2.4).

One call per `classify`: the cap is checked before it, every billed response is recorded on the
meter, and the answer is completed in code. Nothing is stored here.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from tlv_hunter.classify.base import ClassificationError
from tlv_hunter.classify.complete import AnswerError, Completed, Provenance, complete
from tlv_hunter.classify.cost import CallRecord, CostMeter, Usage, worst_case
from tlv_hunter.classify.instructions import (
    PROMPT_FINGERPRINT,
    PROMPT_VERSION,
    Prompt,
    build_prompt,
)
from tlv_hunter.classify.transport import ModelTransport, TransportError
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.listing_extraction import ListingExtraction
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.parsing.datetimes import require_utc


class OpenAIClassifier:
    def __init__(
        self,
        transport: ModelTransport,
        meter: CostMeter,
        *,
        clock: Callable[[], datetime],
        prompt: Prompt | None = None,
    ) -> None:
        self._prompt = build_prompt() if prompt is None else prompt
        if self._prompt.fingerprint() != PROMPT_FINGERPRINT:
            raise ValueError(
                "the prompt changed without a new PROMPT_VERSION: update PROMPT_VERSION and "
                "PROMPT_FINGERPRINT in classify/instructions.py (DECISIONS.md #179)"
            )
        self._transport = transport
        self._meter = meter
        self._clock = clock

    def request(self, post: RawPost) -> dict[str, Any]:
        """The instructions end at the cache breakpoint; the post follows, verbatim and alone
        (invariant 8, DECISIONS.md #147, #150, #157)."""
        prompt = self._prompt
        return {
            "model": prompt.model,
            "input": [
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt.instructions,
                            "prompt_cache_breakpoint": {"mode": "explicit"},
                        }
                    ],
                },
                {"role": "user", "content": [{"type": "input_text", "text": post.text}]},
            ],
            "text": {"format": prompt.text_format},
            "store": False,
            "reasoning": {"effort": prompt.reasoning_effort},
            "temperature": prompt.temperature,
            "max_output_tokens": prompt.max_output_tokens,
            "prompt_cache_options": {"mode": "explicit"},
        }

    def classify(self, post: RawPost) -> Listing:
        return self.classify_completed(post).listing

    def classify_completed(self, post: RawPost) -> Completed:
        """`classify`, with the names dropped by DECISIONS.md #162 and #180 beside the Listing."""
        request = self.request(post)
        self._meter.check(worst_case(request))
        started = require_utc(self._clock())
        try:
            response = self._transport.send(request)
        except TransportError as error:
            raise ClassificationError(
                error.kind, _transport_detail(error), retry_after=error.retry_after
            ) from error
        received = require_utc(self._clock())
        record = _Recorder(self._meter, post.listing_id, response, received - started)
        try:
            text = _answer_text(response)
            extraction = ListingExtraction.model_validate_json(text)
            provenance = Provenance(
                model_name=self._prompt.model,
                prompt_version=PROMPT_VERSION,
                classified_at=received,
            )
            completed = complete(extraction, post, provenance)
        except ClassificationError as error:
            record.done(error.kind)
            raise
        except ValidationError as error:
            record.done("invalid")
            raise ClassificationError("invalid", describe_validation(error)) from error
        except AnswerError as error:
            record.done("invalid")
            raise ClassificationError("invalid", str(error)) from error
        record.done("ok", completed)
        return completed


class _Recorder:
    """Records one billed response on the meter, once, whatever its outcome."""

    def __init__(self, meter: CostMeter, listing_id: str, response: dict[str, Any], elapsed):
        self._meter = meter
        self._listing_id = listing_id
        self._response = response
        self._seconds = elapsed.total_seconds()

    def done(self, outcome: str, completed: Completed | None = None) -> None:
        usage = Usage.from_response(self._response)
        self._meter.record(
            CallRecord(
                listing_id=self._listing_id,
                status=self._response.get("status"),
                outcome=outcome,
                usage=usage,
                cost=usage.cost(),
                reported_model=self._response.get("model"),
                seconds=self._seconds,
                dropped_streets=() if completed is None else completed.dropped_streets,
                dropped_area_names=() if completed is None else completed.dropped_area_names,
                dropped_other_city=None if completed is None else completed.dropped_other_city,
            )
        )


def _answer_text(response: dict[str, Any]) -> str:
    """The answer's JSON text. Checked in order: incomplete, refusal, any other status."""
    status = response.get("status")
    if status == "incomplete":
        reason = (response.get("incomplete_details") or {}).get("reason")
        raise ClassificationError("incomplete", str(reason or ""))
    contents = [
        content
        for item in response.get("output") or []
        if item.get("type") == "message"
        for content in item.get("content") or []
    ]
    if any(content.get("type") == "refusal" for content in contents):
        # The refusal's text is not kept: it may quote the post.
        raise ClassificationError("refusal", "")
    if status != "completed":
        raise ClassificationError("invalid", f"status {status}")
    text = "".join(
        content.get("text") or "" for content in contents if content.get("type") == "output_text"
    )
    if not text:
        raise ClassificationError("invalid", "no output text")
    return text


def _transport_detail(error: TransportError) -> str:
    return " ".join(str(part) for part in (error.status, error.code) if part is not None)


def describe_validation(error: ValidationError) -> str:
    """Field paths and error types only: pydantic's message carries the input values."""
    return "; ".join(
        f"{'.'.join(str(part) for part in entry['loc']) or '<model>'}: {entry['type']}"
        for entry in error.errors(include_input=False, include_url=False)
    )
