"""The two loops of reclassify (`PHASE_2.md` 2.9; DECISIONS.md #144, #217-#222), on both
stores, with a scripted classifier: `propose` (stage 1, which writes nothing to the store)
and `apply_proposals` (stage 2, which replaces the Listings and never a RawPost)."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from tests.conftest import make_listing
from tests.test_classification_run import (
    USAGE,
    ScriptedClassifier,
    Sleeps,
    lifecycle,
    store_pending,
)
from tlv_hunter.classify.base import ClassificationError
from tlv_hunter.classify.complete import Completed
from tlv_hunter.classify.cost import CapReached, CostMeter
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.reclassify import Proposal, select
from tlv_hunter.reclassification_run import apply_proposals, propose
from tlv_hunter.store.base import Repository

CURRENT = ("3", 1, "gpt-6-luna")
MakeRepository = Callable[[], Repository]


def old_store(repository: Repository, posts: list[RawPost], count: int = 4, **record: Any):
    """`count` canonicals classified at prompt version 2: all selected against version 3."""
    stored = store_pending(repository, posts[:count])
    for post in stored:
        repository.save_classification(
            make_listing(post.listing_id, prompt_version="2"),
            lifecycle(post, state="active", **record),
        )
    return stored


def snapshot(repository: Repository) -> dict[str, Any]:
    """Everything the store holds about every post, to compare before and after."""
    return {
        post.listing_id: (
            post.model_dump_json(),
            repository.get_lifecycle(post.listing_id),
            repository.get_listing(post.listing_id),
        )
        for post in repository.query()
    }


def raw_documents(repository: Repository) -> dict[str, str]:
    return {post.listing_id: post.model_dump_json() for post in repository.query()}


def run_propose(
    repository: Repository,
    classifier: Any,
    *,
    corrections: dict[str, tuple[str, ...]] | None = None,
    candidates=None,
    on_proposal=None,
):
    sleeps = Sleeps()
    chosen = select(repository, CURRENT).selected if candidates is None else candidates
    proposals: list[Proposal] = []
    result = propose(
        repository=repository,
        classifier=classifier,
        meter=classifier.meter,
        sleep=sleeps,
        candidates=chosen,
        corrections=corrections or {},
        on_proposal=on_proposal or proposals.append,
    )
    return result, sleeps


@pytest.fixture
def setup(make_repository: MakeRepository, posts: list[RawPost]):
    repository = make_repository()
    stored = old_store(repository, posts)
    return repository, stored, ScriptedClassifier(CostMeter(cap=1.0))


# --- stage 1 ---


def test_each_post_becomes_a_proposal_and_the_store_is_untouched(setup) -> None:
    repository, stored, classifier = setup
    before = snapshot(repository)
    result, _ = run_propose(repository, classifier)

    assert [p.listing_id for p in result.proposals] == [p.listing_id for p in stored]
    assert classifier.calls == [p.listing_id for p in stored]
    for proposal in result.proposals:
        assert proposal.new is not None and proposal.error is None
        assert proposal.old.listing.prompt_version == "2"
        assert proposal.new.listing.prompt_version == "1"  # the scripted classifier's provenance
        assert proposal.text_sha256
        assert proposal.cost == pytest.approx(USAGE.cost())
        assert (proposal.attempts, proposal.reviewed, proposal.corrected_fields) == (1, False, [])
    assert snapshot(repository) == before  # nothing written: not a Listing, not a record
    assert result.stopped is None and result.not_attempted == ()


def test_the_proposal_records_the_status_the_new_answer_would_give(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = ["seeking"]
    classifier.script[stored[1].listing_id] = ["sublet_offer"]
    result, _ = run_propose(repository, classifier)
    first, second = result.proposals[0], result.proposals[1]
    assert first.old_status == ("active", None) and first.new_status == ("rejected", "seeking")
    assert first.status_changed and "post_nature" in first.fields_changed
    assert second.new_status == ("active", None) and not second.status_changed
    assert second.fields_changed == ["post_nature"]


def test_a_flagged_post_proposes_its_old_status(
    make_repository: MakeRepository, posts: list[RawPost]
) -> None:
    repository = make_repository()
    flag = {"flagged_by": "u1", "flagged_at": datetime(2026, 10, 7, tzinfo=UTC)}
    (post,) = old_store(repository, posts, count=1, **flag)
    classifier = ScriptedClassifier(CostMeter(cap=1.0), {post.listing_id: ["seeking"]})
    result, _ = run_propose(repository, classifier)
    (proposal,) = result.proposals
    assert proposal.old.flagged and proposal.new_status == ("active", None)
    assert not proposal.status_changed  # the flag keeps the state (#144)


def test_a_failed_post_leaves_the_old_listing_and_the_failure_fields(setup) -> None:
    """DECISIONS.md #221, #152: not counted, recorded nowhere in the store."""
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = [
        ClassificationError("refusal", ""),
    ]
    classifier.script[stored[1].listing_id] = [
        ClassificationError("invalid", "x"),
        ClassificationError("invalid", "x"),
    ]
    before = snapshot(repository)
    result, _ = run_propose(repository, classifier)
    refused, invalid = result.proposals[0], result.proposals[1]
    assert refused.new is None and refused.error.startswith("refusal")
    assert invalid.new is None and invalid.attempts == 2
    assert refused.fields_changed == [] and refused.new_status is None
    assert snapshot(repository) == before
    record = repository.get_lifecycle(stored[0].listing_id)
    assert (record.classification_failures, record.last_classification_error) == (0, None)
    assert [p.new is None for p in result.proposals] == [True, True, False, False]


def test_the_cap_stops_before_the_post_and_it_is_not_attempted(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[1].listing_id] = [CapReached(0.0, 0.0037, 0.001)]
    result, _ = run_propose(repository, classifier)
    assert [p.listing_id for p in result.proposals] == [stored[0].listing_id]
    assert result.not_attempted == tuple(p.listing_id for p in stored[1:])
    assert result.stopped is not None and "cap" in result.stopped


@pytest.mark.parametrize("kind", ["quota", "auth", "spend_limit", "bad_request", "not_found"])
def test_a_failure_every_post_would_share_stops_the_run(setup, kind: str) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = [ClassificationError(kind, "")]
    result, _ = run_propose(repository, classifier)
    assert result.proposals == () and len(result.not_attempted) == 4
    assert result.stopped is not None


def test_a_transient_failure_is_retried_with_the_shared_attempts_table(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = [ClassificationError("timeout", ""), "rental_offer"]
    result, sleeps = run_propose(repository, classifier)
    assert result.proposals[0].new is not None and result.proposals[0].attempts == 2
    assert list(sleeps) == [2.0]


def test_a_proposal_is_handed_over_before_the_next_post_is_asked_about(setup) -> None:
    repository, stored, classifier = setup
    events: list[str] = []
    classifier.during_call = lambda post: events.append(f"call {post.listing_id[:6]}")
    run_propose(
        repository, classifier, on_proposal=lambda p: events.append(f"line {p.listing_id[:6]}")
    )
    expected = []
    for post in stored:
        expected += [f"call {post.listing_id[:6]}", f"line {post.listing_id[:6]}"]
    assert events == expected


def test_a_correction_on_file_marks_the_proposal(setup) -> None:
    repository, stored, classifier = setup
    corrections = {stored[0].listing_id: ("price", "rooms"), stored[2].listing_id: ()}
    result, _ = run_propose(repository, classifier, corrections=corrections)
    marks = [(p.reviewed, p.corrected_fields) for p in result.proposals]
    assert marks == [(True, ["price", "rooms"]), (False, []), (True, []), (False, [])]


def test_the_names_dropped_from_the_new_answer_are_kept(setup) -> None:
    repository, stored, classifier = setup

    class Dropping:
        meter = classifier.meter

        def classify_completed(self, post: RawPost) -> Completed:
            completed = classifier.classify_completed(post)
            return Completed(
                completed.listing,
                dropped_streets=("רחוב",),
                dropped_area_names=("שכונה",),
                dropped_other_city="חולון",
            )

    result, _ = run_propose(
        repository, Dropping(), candidates=select(repository, CURRENT).selected[:1]
    )
    dropped = result.proposals[0].dropped
    assert (dropped.streets, dropped.area_names, dropped.other_city) == (
        ["רחוב"],
        ["שכונה"],
        "חולון",
    )


def test_a_vanished_post_fails_the_run(setup) -> None:
    repository, stored, classifier = setup
    candidates = select(repository, CURRENT).selected
    ghost = candidates[0].__class__("f" * 64, candidates[0].triple, ("active", None), False)
    with pytest.raises(RuntimeError, match="vanished"):
        run_propose(repository, classifier, candidates=(ghost,))


# --- stage 2 ---


def proposals_for(repository: Repository, classifier: ScriptedClassifier) -> list[Proposal]:
    return list(run_propose(repository, classifier)[0].proposals)


def test_apply_replaces_only_the_named_listings_and_no_raw_post(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = ["seeking"]
    proposals = proposals_for(repository, classifier)
    before = snapshot(repository)
    raw_before = raw_documents(repository)

    named = [p for p in proposals if p.listing_id in (stored[0].listing_id, stored[2].listing_id)]
    written: list[str] = []
    outcomes = apply_proposals(
        repository=repository, proposals=named, on_written=lambda p: written.append(p.listing_id)
    )

    assert {o.listing_id: o.result for o in outcomes} == {
        stored[0].listing_id: "written",
        stored[2].listing_id: "written",
    }
    assert written == [o.listing_id for o in outcomes]
    assert raw_documents(repository) == raw_before  # invariant 14: no RawPost was written
    by_id = {p.listing_id: p for p in proposals}
    for post in stored:
        listing = repository.get_listing(post.listing_id)
        record = repository.get_lifecycle(post.listing_id)
        if post.listing_id in (stored[0].listing_id, stored[2].listing_id):
            assert listing == by_id[post.listing_id].new.listing
        else:
            assert listing == before[post.listing_id][2]
            assert record == before[post.listing_id][1]
    seeking = repository.get_lifecycle(stored[0].listing_id)
    assert (seeking.state, seeking.rejection_reason) == ("rejected", "seeking")
    kept = repository.get_lifecycle(stored[2].listing_id)
    assert kept == before[stored[2].listing_id][1]  # status unchanged: the record is as it was


def test_only_the_state_and_the_reason_of_a_record_change(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = ["for_sale"]
    proposals = proposals_for(repository, classifier)
    was = repository.get_lifecycle(stored[0].listing_id)
    apply_proposals(repository=repository, proposals=proposals[:1])
    now = repository.get_lifecycle(stored[0].listing_id)
    assert (now.state, now.rejection_reason) == ("rejected", "for_sale")
    assert now.model_copy(update={"state": "active", "rejection_reason": None}) == was


def test_a_flagged_record_is_written_back_as_it_was(
    make_repository: MakeRepository, posts: list[RawPost]
) -> None:
    repository = make_repository()
    flag = {
        "flagged_by": "u1",
        "flagged_at": datetime(2026, 10, 7, tzinfo=UTC),
        "state": "rejected",
        "rejection_reason": "flagged",
    }
    stored = store_pending(repository, posts[:1])
    (post,) = stored
    repository.save_classification(
        make_listing(post.listing_id, prompt_version="2"), lifecycle(post, **flag)
    )
    was = repository.get_lifecycle(post.listing_id)
    classifier = ScriptedClassifier(CostMeter(cap=1.0), {post.listing_id: ["seeking"]})
    proposals = proposals_for(repository, classifier)
    (outcome,) = apply_proposals(repository=repository, proposals=proposals)
    assert outcome.result == "written"
    assert repository.get_lifecycle(post.listing_id) == was  # flag, state and reason kept
    assert repository.get_listing(post.listing_id) == proposals[0].new.listing  # Listing replaced


def test_a_second_apply_is_a_no_op(setup) -> None:
    repository, stored, classifier = setup
    proposals = proposals_for(repository, classifier)
    apply_proposals(repository=repository, proposals=proposals)
    after_first = snapshot(repository)
    again: list[str] = []
    outcomes = apply_proposals(
        repository=repository, proposals=proposals, on_written=lambda p: again.append(p.listing_id)
    )
    assert {o.result for o in outcomes} == {"already applied"} and again == []
    assert snapshot(repository) == after_first


def test_a_post_whose_text_changed_since_the_run_is_not_written(setup) -> None:
    repository, stored, classifier = setup
    proposals = proposals_for(repository, classifier)
    edited = repository.get(stored[0].listing_id).with_changes(text="טקסט אחר לגמרי")
    repository.upsert(edited)
    outcomes = {
        o.listing_id: o for o in apply_proposals(repository=repository, proposals=proposals)
    }
    assert outcomes[stored[0].listing_id].result == "not written"
    assert "text changed" in outcomes[stored[0].listing_id].reason
    assert repository.get_listing(stored[0].listing_id).prompt_version == "2"
    assert repository.get_listing(stored[1].listing_id).prompt_version == "1"  # the others went on


def test_a_listing_or_a_record_that_changed_since_the_run_is_not_written(setup) -> None:
    repository, stored, classifier = setup
    proposals = proposals_for(repository, classifier)
    other = make_listing(stored[0].listing_id, prompt_version="2", gender="women_only")
    repository.save_classification(other, repository.get_lifecycle(stored[0].listing_id))
    record = repository.get_lifecycle(stored[1].listing_id)
    repository.save_lifecycle(
        record.model_copy(update={"state": "rejected", "rejection_reason": "seeking"})
    )
    repository.save_lifecycle(
        repository.get_lifecycle(stored[2].listing_id).model_copy(update={"state": "archived"})
    )
    outcomes = {
        o.listing_id: o for o in apply_proposals(repository=repository, proposals=proposals)
    }
    assert "Listing changed" in outcomes[stored[0].listing_id].reason
    assert "record changed" in outcomes[stored[1].listing_id].reason
    assert "record changed" in outcomes[stored[2].listing_id].reason
    assert outcomes[stored[3].listing_id].result == "written"
    assert repository.get_listing(stored[0].listing_id) == other


def test_a_failed_proposal_has_nothing_to_apply(setup) -> None:
    repository, stored, classifier = setup
    classifier.script[stored[0].listing_id] = [ClassificationError("refusal", "")]
    proposals = proposals_for(repository, classifier)
    outcomes = {
        o.listing_id: o for o in apply_proposals(repository=repository, proposals=proposals)
    }
    assert outcomes[stored[0].listing_id].result == "not written"
    assert repository.get_listing(stored[0].listing_id).prompt_version == "2"


def test_a_post_that_is_gone_is_reported_not_raised(setup) -> None:
    repository, stored, classifier = setup
    proposals = proposals_for(repository, classifier)
    ghost = Proposal.model_construct(**{**dict(proposals[0]), "listing_id": "e" * 64})
    (outcome,) = apply_proposals(repository=repository, proposals=[ghost])
    assert outcome.result == "not written" and "gone" in outcome.reason
