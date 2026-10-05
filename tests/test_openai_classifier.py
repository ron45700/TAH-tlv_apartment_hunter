"""The classifier through a fake transport (`PHASE_2.md` 2.4). The spike's raw responses are read
in place; they predate DECISIONS.md #167 and carry no `areas`, so `areas: []` is added to each
answer in memory. The refusal is built from the documented shape: none was observed (#181)."""

import copy
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from tests.conftest import (
    load_openai_spike,
    load_openai_spike_posts,
    post_with_text,
    spike_answer,
)
from tlv_hunter.classify.base import ClassificationError, Classifier
from tlv_hunter.classify.cost import CapReached, CostMeter, Usage
from tlv_hunter.classify.instructions import PROMPT_VERSION, build_prompt
from tlv_hunter.classify.openai_classifier import OpenAIClassifier
from tlv_hunter.classify.transport import TransportError
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.raw_post import RawPost

START = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


class FakeTransport:
    """Hands back the queued responses, or raises the queued errors, in order."""

    def __init__(self, *results: dict[str, Any] | Exception) -> None:
        self.results = list(results)
        self.requests: list[dict[str, Any]] = []

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(copy.deepcopy(request))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)


def ticking_clock(step: float = 3.0) -> Callable[[], datetime]:
    now = [START]

    def clock() -> datetime:
        now[0] += timedelta(seconds=step)
        return now[0]

    return clock


def with_answer(response: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    """The response with its message's text replaced."""
    response = copy.deepcopy(response)
    (message,) = [item for item in response["output"] if item["type"] == "message"]
    message["content"][0]["text"] = json.dumps(answer, ensure_ascii=False)
    return response


def spike_response(name: str = "none_t0_p1_01", **answer_changes: Any) -> dict[str, Any]:
    response = load_openai_spike(name)["response"]
    return with_answer(response, {**spike_answer(name), "areas": [], **answer_changes})


def spike_post(posts: list[RawPost], index: int) -> RawPost:
    """Spike post `index` (0-based) as a pending canonical, from the stored text read in place."""
    item = load_openai_spike_posts()[index]
    posted_at = (
        datetime.fromisoformat(item["posted_at"]) if item["posted_at"] else posts[0].posted_at
    )
    return post_with_text(
        posts[0], item["text"], native_price=item["native_price"], posted_at=posted_at
    )


def classifier(transport: FakeTransport, meter: CostMeter | None = None) -> OpenAIClassifier:
    return OpenAIClassifier(transport, meter or CostMeter(cap=1.0), clock=ticking_clock())


def test_it_satisfies_the_classifier_protocol() -> None:
    assert isinstance(classifier(FakeTransport()), Classifier)


def test_a_changed_prompt_is_refused_until_the_version_is_updated() -> None:
    changed = build_prompt()
    changed = type(changed)(**{**changed.__dict__, "instructions": changed.instructions + "x"})
    with pytest.raises(ValueError, match="PROMPT_VERSION"):
        OpenAIClassifier(FakeTransport(), CostMeter(cap=1.0), clock=ticking_clock(), prompt=changed)


# --- The request (`PHASE_2.md` 2.4, step 2) ---


def test_the_request_is_exactly_the_approved_one(posts: list[RawPost]) -> None:
    transport = FakeTransport(spike_response())
    post = spike_post(posts, 0)
    classifier(transport).classify(post)
    prompt = build_prompt()
    assert transport.requests == [
        {
            "model": "gpt-6-luna",
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
            "reasoning": {"effort": "none"},
            "temperature": 0,
            "max_output_tokens": 2000,
            "prompt_cache_options": {"mode": "explicit"},
        }
    ]


def test_the_post_is_sent_verbatim_and_alone(posts: list[RawPost]) -> None:
    """Invariant 8: the original text, never normalized; nothing else in the user message."""
    text = '  דירה ב"פלורנטין"  🙂\r\n 054-1234567 מִי'
    transport = FakeTransport(spike_response())
    classifier(transport).classify(post_with_text(posts[0], text))
    user = transport.requests[0]["input"][1]
    assert user == {"role": "user", "content": [{"type": "input_text", "text": text}]}


# --- A completed answer ---


def test_the_spike_answers_complete_into_listings(posts: list[RawPost]) -> None:
    """The 20 answers of `none_t0` pass 1, each with its own post, read in place."""
    meter = CostMeter(cap=1.0)
    for index in range(20):
        name = f"none_t0_p1_{index + 1:02d}"
        listing = classifier(FakeTransport(spike_response(name)), meter).classify(
            spike_post(posts, index)
        )
        assert isinstance(listing, Listing)
        assert listing.prompt_version == PROMPT_VERSION
        assert listing.model_name == "gpt-6-luna"
    assert len(meter.calls) == 20
    assert {call.reported_model for call in meter.calls} == {"gpt-6-luna"}
    assert {call.outcome for call in meter.calls} == {"ok"}


def test_the_call_is_recorded_with_its_usage_cost_and_reported_model(
    posts: list[RawPost],
) -> None:
    """The first spike call wrote the 2,514-token prefix: 2,779 input, 244 output."""
    meter = CostMeter(cap=1.0)
    response = spike_response()
    response["model"] = "gpt-6-luna-2026-11-01"
    completed = classifier(FakeTransport(response), meter).classify_completed(spike_post(posts, 0))
    (call,) = meter.calls
    assert call.usage == Usage.from_response(response)
    assert call.cost == pytest.approx(call.usage.cost())
    assert call.reported_model == "gpt-6-luna-2026-11-01"
    assert call.seconds == 3.0
    assert completed.listing.classified_at == START + timedelta(seconds=6)
    assert meter.spent == call.cost


def test_usage_cost_counts_cache_writes_inside_input_tokens() -> None:
    usage = Usage(
        input_tokens=2779,
        cached_tokens=0,
        cache_write_tokens=2514,
        output_tokens=244,
        reasoning_tokens=0,
    )
    assert usage.cost() == pytest.approx((265 * 0.10 + 2514 * 0.125 + 244 * 0.50) / 1e6)


def test_dropped_names_are_recorded_on_the_call(posts: list[RawPost]) -> None:
    meter = CostMeter(cap=1.0)
    response = spike_response(
        streets=["רחוב שאינו בטקסט"], stated_area_names=[], other_city="עיר שאינה בטקסט"
    )
    completed = classifier(FakeTransport(response), meter).classify_completed(spike_post(posts, 0))
    assert completed.listing.other_city is None
    (call,) = meter.calls
    assert call.dropped_streets == ("רחוב שאינו בטקסט",)
    assert call.dropped_other_city == "עיר שאינה בטקסט"


# --- The failure kinds ---


def refusal_response() -> dict[str, Any]:
    """RESEARCH.md §15, ASSUMPTIONS.md O13: a refusal content item instead of the JSON."""
    response = load_openai_spike("none_t0_p1_01")["response"]
    response = copy.deepcopy(response)
    (message,) = [item for item in response["output"] if item["type"] == "message"]
    message["content"] = [{"type": "refusal", "refusal": "I can't help with that. 054-1234567"}]
    return response


def attempt(posts: list[RawPost], result: Any, meter: CostMeter | None = None):
    meter = meter or CostMeter(cap=1.0)
    with pytest.raises(ClassificationError) as caught:
        classifier(FakeTransport(result), meter).classify(spike_post(posts, 0))
    return caught.value, meter


def test_a_refusal_is_billed_and_its_text_is_not_kept(posts: list[RawPost]) -> None:
    error, meter = attempt(posts, refusal_response())
    assert (error.kind, str(error)) == ("refusal", "refusal")
    assert [call.outcome for call in meter.calls] == ["refusal"]


def test_an_incomplete_answer_is_billed(posts: list[RawPost]) -> None:
    """The spike's probe, read in place: max_output_tokens 16, cut JSON."""
    error, meter = attempt(posts, load_openai_spike("probe_incomplete")["response"])
    assert (error.kind, error.detail) == ("incomplete", "max_output_tokens")
    assert meter.calls[0].usage.output_tokens == 16


def test_an_answer_failing_the_schema_is_invalid_and_names_no_value(
    posts: list[RawPost],
) -> None:
    error, meter = attempt(posts, spike_response(price={"state": "written", "value": "5500"}))
    assert error.kind == "invalid"
    assert "price" in error.detail and "5500" not in error.detail
    assert [call.outcome for call in meter.calls] == ["invalid"]


def test_an_answer_without_areas_is_invalid(posts: list[RawPost]) -> None:
    """A spike answer as it is: written before #167, so it has no `areas`."""
    response = load_openai_spike("none_t0_p1_01")["response"]
    error, _ = attempt(posts, response)
    assert (error.kind, error.detail) == ("invalid", "areas: missing")


def test_an_area_outside_1_to_71_is_invalid(posts: list[RawPost]) -> None:
    error, meter = attempt(posts, spike_response(areas=[72]))
    assert error.kind == "invalid"
    assert len(meter.calls) == 1


def test_a_response_with_another_status_is_invalid(posts: list[RawPost]) -> None:
    response = spike_response()
    response["status"] = "failed"
    error, _ = attempt(posts, response)
    assert (error.kind, error.detail) == ("invalid", "status failed")


@pytest.mark.parametrize(
    ("raised", "kind"),
    [
        (TransportError("network"), "network"),
        (TransportError("timeout"), "timeout"),
        (TransportError("rate_limit", status=429, retry_after=7.0), "rate_limit"),
        (TransportError("server", status=503, code="server_is_overloaded"), "server"),
        (
            TransportError("spend_limit", status=429, code="project_spend_limit_exceeded"),
            "spend_limit",
        ),
        (TransportError("auth", status=401, code="invalid_api_key"), "auth"),
    ],
)
def test_a_transport_error_is_not_billed(
    posts: list[RawPost], raised: TransportError, kind: str
) -> None:
    error, meter = attempt(posts, raised)
    assert error.kind == kind
    assert error.retry_after == raised.retry_after
    assert meter.calls == []


def test_the_cap_stops_before_the_send(posts: list[RawPost]) -> None:
    transport = FakeTransport(spike_response())
    with pytest.raises(CapReached):
        classifier(transport, CostMeter(cap=0.001)).classify(spike_post(posts, 0))
    assert transport.requests == []
