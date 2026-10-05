"""The classification job's loop (`PHASE_2.md` 2.5; DECISIONS.md #139, #152, #163, #182), on both
stores, with a scripted classifier and an injected sleep."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from tests.test_classify_complete import PROVENANCE, extraction
from tlv_hunter.classification_run import ClassifyRunResult, classify_pending
from tlv_hunter.classify.base import ClassificationError
from tlv_hunter.classify.complete import Completed, complete
from tlv_hunter.classify.cost import CallRecord, CapReached, CostMeter, Usage
from tlv_hunter.contracts.post_lifecycle import POST_LIFECYCLE_SCHEMA_VERSION, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.store.base import Repository

MakeRepository = Callable[[], Repository]
USAGE = Usage(
    input_tokens=2779,
    cached_tokens=2514,
    cache_write_tokens=0,
    output_tokens=270,
    reasoning_tokens=0,
)


def lifecycle(post: RawPost, **changes: Any) -> PostLifecycle:
    fields = {
        "schema_version": POST_LIFECYCLE_SCHEMA_VERSION,
        "listing_id": post.listing_id,
        "state": "pending",
        "rejection_reason": None,
        "flagged_by": None,
        "flagged_at": None,
        "flag_note": None,
        "last_published_at": post.posted_at,
        "images": [],
        "classification_failures": 0,
        "last_classification_error": None,
    }
    return PostLifecycle(**{**fields, **changes})


def store_pending(repository: Repository, posts: list[RawPost]) -> list[RawPost]:
    stored = []
    for post in posts:
        canonical = post.with_changes(is_canonical=True, duplicate_of=None)
        repository.upsert_with_lifecycle(canonical, lifecycle(canonical))
        stored.append(canonical)
    return sorted(stored, key=lambda post: post.listing_id)


class ScriptedClassifier:
    """Per listing_id, a list of results: a nature to answer with, or an exception to raise. A
    post with no script answers "rental_offer". Every answer is recorded on the meter, as billed."""

    def __init__(self, meter: CostMeter, script: dict[str, list[Any]] | None = None) -> None:
        self.meter = meter
        self.script = script or {}
        self.calls: list[str] = []
        self.during_call: Callable[[RawPost], None] | None = None

    def classify_completed(self, post: RawPost) -> Completed:
        self.calls.append(post.listing_id)
        if self.during_call is not None:
            self.during_call(post)
        results = self.script.get(post.listing_id, [])
        result = results.pop(0) if results else "rental_offer"
        if isinstance(result, Exception):
            if isinstance(result, ClassificationError) and result.kind in ("invalid", "refusal"):
                self._record(post, result.kind)
            raise result
        completed = complete(extraction(post_nature=result), post, PROVENANCE)
        self._record(post, "ok")
        return completed

    def _record(self, post: RawPost, outcome: str) -> None:
        self.meter.record(
            CallRecord(
                post.listing_id, "completed", outcome, USAGE, USAGE.cost(), "gpt-6-luna", 3.0
            )
        )


class Sleeps(list):
    def __call__(self, seconds: float) -> None:
        self.append(seconds)


def run(
    repository: Repository, classifier: ScriptedClassifier, **kwargs: Any
) -> tuple[ClassifyRunResult, Sleeps]:
    sleeps = Sleeps()
    result = classify_pending(
        repository=repository,
        classifier=classifier,
        meter=classifier.meter,
        sleep=sleeps,
        **kwargs,
    )
    return result, sleeps


@pytest.fixture
def setup(make_repository: MakeRepository, posts: list[RawPost]):
    repository = make_repository()
    stored = store_pending(repository, posts[:4])
    return repository, stored, ScriptedClassifier(CostMeter(cap=1.0))


def test_pending_canonicals_become_listings_with_their_states(setup) -> None:
    repository, stored, classifier = setup
    natures = ["rental_offer", "sublet_offer", "seeking", "for_sale"]
    for post, nature in zip(stored, natures, strict=True):
        classifier.script[post.listing_id] = [nature]
    result, _ = run(repository, classifier)

    assert classifier.calls == [post.listing_id for post in stored]  # listing_id order
    states = [
        (
            repository.get_lifecycle(p.listing_id).state,
            repository.get_lifecycle(p.listing_id).rejection_reason,
        )
        for p in stored
    ]
    assert states == [
        ("active", None),
        ("active", None),
        ("rejected", "seeking"),
        ("rejected", "for_sale"),
    ]
    assert all(repository.get_listing(p.listing_id) is not None for p in stored)
    assert [o.outcome for o in result.outcomes] == [
        "active",
        "active",
        "rejected: seeking",
        "rejected: for_sale",
    ]
    assert result.stopped is None and result.found == 4
    assert repository.find_pending_canonicals() == []


def test_only_pending_canonicals_are_classified(make_repository: MakeRepository, posts) -> None:
    repository = make_repository()
    pending, active, archived, rejected = store_pending(repository, posts[:4])
    repository.save_lifecycle(lifecycle(active, state="active"))
    repository.save_lifecycle(lifecycle(archived, state="archived"))
    repository.save_lifecycle(lifecycle(rejected, state="rejected", rejection_reason="no_images"))
    duplicate = posts[4].with_changes(is_canonical=False, duplicate_of=pending.listing_id)
    repository.upsert_with_lifecycle(duplicate, lifecycle(duplicate))

    classifier = ScriptedClassifier(CostMeter(cap=1.0))
    run(repository, classifier)
    assert classifier.calls == [pending.listing_id]
    for post in (active, archived, rejected, duplicate):
        assert repository.get_listing(post.listing_id) is None


def test_the_stored_posts_are_byte_identical_after_a_run(
    make_repository: MakeRepository, posts
) -> None:
    """Invariant 14 (DECISIONS.md #163), over a run that mixes successes and failures."""
    repository = make_repository()
    stored = store_pending(repository, posts)
    before = {post.listing_id: post.model_dump_json() for post in make_repository().query()}
    classifier = ScriptedClassifier(CostMeter(cap=1.0))
    classifier.script[stored[0].listing_id] = [ClassificationError("refusal", "")]
    classifier.script[stored[1].listing_id] = [ClassificationError("timeout", "")] * 3
    classifier.script[stored[2].listing_id] = ["not_listing"]
    run(repository, classifier)
    after = {post.listing_id: post.model_dump_json() for post in make_repository().query()}
    assert after == before


# --- Failed runs (#139, #152) ---


def test_a_failed_run_counts_one_and_records_the_reason(setup) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    classifier.script[post.listing_id] = [
        ClassificationError("invalid", "price.value: int_type")
    ] * 2
    result, _ = run(repository, classifier)
    record = repository.get_lifecycle(post.listing_id)
    assert (record.state, record.classification_failures) == ("pending", 1)
    assert record.last_classification_error == "invalid: price.value: int_type"
    assert result.outcomes[0].outcome == "failed: invalid"
    assert repository.get_listing(post.listing_id) is None


def test_three_failed_runs_and_the_post_is_skipped(setup) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    for _ in range(3):
        classifier.script[post.listing_id] = [ClassificationError("refusal", "")]
        run(repository, classifier)
    assert repository.get_lifecycle(post.listing_id).classification_failures == 3

    classifier.calls.clear()
    result, _ = run(repository, classifier)
    assert post.listing_id not in classifier.calls
    assert result.skipped == (post.listing_id,)
    assert repository.get_lifecycle(post.listing_id).state == "pending"


def test_a_later_success_leaves_the_failure_fields(setup) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    classifier.script[post.listing_id] = [ClassificationError("refusal", "")]
    run(repository, classifier)
    run(repository, classifier)  # no script left: answers rental_offer
    record = repository.get_lifecycle(post.listing_id)
    assert (record.state, record.classification_failures) == ("active", 1)
    assert record.last_classification_error == "refusal"


# --- Attempts per kind (#182) ---


@pytest.mark.parametrize("kind", ["network", "timeout", "rate_limit", "server"])
def test_a_transient_failure_gets_three_attempts_with_waits(setup, kind: str) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    classifier.script[post.listing_id] = [ClassificationError(kind, "")] * 3
    result, sleeps = run(repository, classifier, limit=1)
    assert classifier.calls == [post.listing_id] * 3
    assert sleeps == [2.0, 10.0]
    assert result.outcomes[0].attempts == 3
    assert repository.get_lifecycle(post.listing_id).classification_failures == 1


def test_a_transient_failure_then_success(setup) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    classifier.script[post.listing_id] = [ClassificationError("network", ""), "rental_offer"]
    result, sleeps = run(repository, classifier, limit=1)
    assert sleeps == [2.0]
    assert result.outcomes[0].outcome == "active"
    assert repository.get_lifecycle(post.listing_id).classification_failures == 0


def test_retry_after_is_honoured_when_longer(setup) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    classifier.script[post.listing_id] = [
        ClassificationError("rate_limit", "", retry_after=7.0)
    ] * 3
    _, sleeps = run(repository, classifier, limit=1)
    assert sleeps == [7.0, 10.0]


def test_a_retry_after_above_60_seconds_ends_the_attempts(setup) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    classifier.script[post.listing_id] = [ClassificationError("rate_limit", "", retry_after=120.0)]
    result, sleeps = run(repository, classifier, limit=1)
    assert (sleeps, result.outcomes[0].attempts) == ([], 1)
    assert result.outcomes[0].outcome == "failed: rate_limit"


@pytest.mark.parametrize(("kind", "attempts"), [("invalid", 2), ("incomplete", 2), ("refusal", 1)])
def test_an_answer_failure_is_retried_without_a_wait(setup, kind: str, attempts: int) -> None:
    repository, stored, classifier = setup
    post = stored[0]
    classifier.script[post.listing_id] = [ClassificationError(kind, "")] * attempts
    result, sleeps = run(repository, classifier, limit=1)
    assert (len(classifier.calls), sleeps) == (attempts, [])
    assert result.outcomes[0].outcome == f"failed: {kind}"


# --- Stops (#182) ---


def test_the_cap_stops_the_job_and_the_post_is_not_counted(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[1].listing_id] = [CapReached(0.99, 0.003, 1.0)]
    result, _ = run(repository, classifier)
    assert result.stopped is not None and result.stopped.startswith("cap")
    assert [o.listing_id for o in result.outcomes] == [stored[0].listing_id]
    assert repository.get_lifecycle(stored[0].listing_id).state == "active"
    record = repository.get_lifecycle(stored[1].listing_id)
    assert (record.state, record.classification_failures) == ("pending", 0)
    assert stored[2].listing_id not in classifier.calls


@pytest.mark.parametrize("kind", ["spend_limit", "quota", "auth", "bad_request", "not_found"])
def test_a_stop_kind_stops_the_job_and_the_post_is_not_counted(setup, kind: str) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = [ClassificationError(kind, "429")]
    result, _ = run(repository, classifier)
    assert result.stopped == f"{kind}: 429"
    assert classifier.calls == [stored[0].listing_id]
    record = repository.get_lifecycle(stored[0].listing_id)
    assert (record.classification_failures, record.last_classification_error) == (0, None)


def test_a_store_error_propagates(setup) -> None:
    repository, stored, classifier = setup

    class Failing:
        def __getattr__(self, name: str) -> Any:
            return getattr(repository, name)

        def save_classification(self, listing, lifecycle) -> None:
            raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        run(Failing(), classifier)


# --- The record read again before the write (#182) ---


def test_an_answer_for_a_post_no_longer_pending_is_discarded(setup) -> None:
    repository, stored, classifier = setup
    post = stored[0]

    def flag(during: RawPost) -> None:
        if during.listing_id == post.listing_id:
            repository.save_lifecycle(
                lifecycle(
                    post,
                    state="rejected",
                    rejection_reason="flagged",
                    flagged_by="ron",
                    flagged_at=datetime(2026, 10, 5, tzinfo=UTC),
                )
            )

    classifier.during_call = flag
    result, _ = run(repository, classifier, limit=1)
    assert result.outcomes[0].outcome == "discarded"
    assert repository.get_listing(post.listing_id) is None
    assert repository.get_lifecycle(post.listing_id).rejection_reason == "flagged"


# --- Limit and the written callback ---


def test_limit_counts_after_the_skipped_posts(setup) -> None:
    repository, stored, classifier = setup
    repository.save_lifecycle(lifecycle(stored[0], classification_failures=3))
    result, _ = run(repository, classifier, limit=2)
    assert classifier.calls == [stored[1].listing_id, stored[2].listing_id]
    assert result.skipped == (stored[0].listing_id,)


def test_on_written_receives_each_stored_result(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[1].listing_id] = [ClassificationError("refusal", "")]
    written: list[Completed] = []
    run(repository, classifier, on_written=written.append)
    assert [c.listing.listing_id for c in written] == [
        stored[0].listing_id,
        stored[2].listing_id,
        stored[3].listing_id,
    ]


def test_the_outcomes_carry_their_calls(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = [ClassificationError("invalid", ""), "rental_offer"]
    result, _ = run(repository, classifier, limit=1)
    assert [call.outcome for call in result.outcomes[0].calls] == ["invalid", "ok"]
    assert result.spent == pytest.approx(2 * USAGE.cost())
