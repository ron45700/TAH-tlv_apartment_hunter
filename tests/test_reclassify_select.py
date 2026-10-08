"""Reclassify, the plain part (`PHASE_2.md` 2.9; DECISIONS.md #144, #217): the selection, the
narrowing by `--allow` and `--limit`, the per-field diff, the lifecycle record written with a new
`Listing`, and the proposal record. No model, no network; both stores."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from tests.conftest import make_listing
from tests.test_classification_run import lifecycle
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.reclassify import (
    Candidate,
    Dropped,
    NewSide,
    OldSide,
    Proposal,
    changed_fields,
    narrow,
    reclassified_lifecycle,
    select,
    status_text,
)
from tlv_hunter.store.base import Repository

CURRENT = ("3", 1, "gpt-6-luna")
WRITTEN_PRICE = {"state": "written", "value": [4500]}


def store(repository: Repository, post: RawPost, **record: Any) -> RawPost:
    canonical = post.with_changes(is_canonical=True, duplicate_of=None)
    repository.upsert_with_lifecycle(canonical, lifecycle(canonical, **record))
    return canonical


def listing_for(post: RawPost, **changes: Any) -> Listing:
    return make_listing(post.listing_id, **{"prompt_version": "3", **changes})


@pytest.fixture
def shapes(make_repository: Callable[[], Repository], posts: list[RawPost]):
    """One post of every shape the selection has to tell apart."""
    repository = make_repository()
    named: dict[str, RawPost] = {}

    def add(name: str, post: RawPost, **record: Any) -> None:
        named[name] = store(repository, post, **record)

    p = iter(posts)
    add("old_version", next(p), state="active")
    add("old_version_rejected", next(p), state="rejected", rejection_reason="seeking")
    add("old_schema", next(p), state="active")
    add("old_model", next(p), state="rejected", rejection_reason="other_city")
    add("current", next(p), state="active")
    add("pending", next(p), state="pending")
    add("archived", next(p), state="archived")
    add("premodel", next(p), state="rejected", rejection_reason="no_images")
    add(
        "flagged",
        next(p),
        state="rejected",
        rejection_reason="flagged",
        flagged_by="u1",
        flagged_at=datetime(2026, 10, 7, tzinfo=UTC),
    )
    add(
        "flagged_active",
        next(p),
        state="active",
        flagged_by="u1",
        flagged_at=datetime(2026, 10, 7, tzinfo=UTC),
    )
    listings = {
        "old_version": listing_for(named["old_version"], prompt_version="2"),
        "old_version_rejected": listing_for(
            named["old_version_rejected"], prompt_version="2", post_nature="seeking"
        ),
        "old_schema": listing_for(named["old_schema"], schema_version=2),
        "old_model": listing_for(named["old_model"], model_name="gpt-other", other_city="חולון"),
        "current": listing_for(named["current"]),
        "archived": listing_for(named["archived"], prompt_version="2"),
        "flagged": listing_for(named["flagged"], prompt_version="2"),
        "flagged_active": listing_for(named["flagged_active"], prompt_version="2"),
    }
    for name, listing in listings.items():
        record = repository.get_lifecycle(named[name].listing_id)
        repository.save_classification(listing, record)
    duplicate = next(p).with_changes(is_canonical=False, duplicate_of=named["current"].listing_id)
    repository.upsert_with_lifecycle(duplicate, lifecycle(duplicate))
    named["duplicate"] = duplicate
    return repository, named


def ids(candidates, named: dict[str, RawPost]) -> set[str]:
    by_id = {post.listing_id: name for name, post in named.items()}
    return {by_id[c.listing_id] for c in candidates}


# --- the selection ---


def test_each_of_the_three_attributes_selects_and_the_rest_is_left_out(shapes) -> None:
    repository, named = shapes
    plan = select(repository, CURRENT)
    assert ids(plan.selected, named) == {
        "old_version",
        "old_version_rejected",
        "old_schema",
        "old_model",
        "flagged",
        "flagged_active",
    }
    assert plan.current == CURRENT
    assert [c.listing_id for c in plan.selected] == sorted(c.listing_id for c in plan.selected)
    assert plan.stored == {
        ("2", 1, "gpt-6-luna"): 5,
        ("3", 2, "gpt-6-luna"): 1,
        ("3", 1, "gpt-other"): 1,
        ("3", 1, "gpt-6-luna"): 1,
    }
    assert plan.left_out == {
        "current": 1,
        "not selectable (archived)": 1,
        "no Listing (pending)": 2,  # the pending post and the duplicate
        "no Listing (rejected: no_images)": 1,
    }


def test_the_flag_and_the_status_are_read_from_the_record(shapes) -> None:
    repository, named = shapes
    by_name = {
        name: c
        for c in select(repository, CURRENT).selected
        for name, post in named.items()
        if post.listing_id == c.listing_id
    }
    assert by_name["old_version"] == Candidate(
        named["old_version"].listing_id, ("2", 1, "gpt-6-luna"), ("active", None), False
    )
    assert by_name["old_version_rejected"].status == ("rejected", "seeking")
    assert by_name["flagged"].flagged and by_name["flagged"].status == ("rejected", "flagged")
    assert by_name["flagged_active"].flagged and by_name["flagged_active"].status == (
        "active",
        None,
    )


def test_when_every_listing_is_current_nothing_is_selected(shapes) -> None:
    """The shape of the real store on 2026-10-08: every Listing current."""
    repository, named = shapes
    assert select(repository, CURRENT).selected
    for post in named.values():
        listing = repository.get_listing(post.listing_id)
        if listing is not None:
            repository.save_classification(
                listing.model_copy(
                    update={"prompt_version": "3", "schema_version": 1, "model_name": "gpt-6-luna"}
                ),
                repository.get_lifecycle(post.listing_id),
            )
    plan = select(repository, CURRENT)
    assert plan.selected == () and plan.stored == {CURRENT: 8}


def test_select_writes_nothing(shapes) -> None:
    repository, named = shapes
    before = {p.listing_id: repository.get_lifecycle(p.listing_id) for p in named.values()}
    select(repository, CURRENT)
    assert before == {p.listing_id: repository.get_lifecycle(p.listing_id) for p in named.values()}


# --- --allow and --limit ---


def test_allow_keeps_the_prefixes_and_limit_the_first_n(shapes) -> None:
    repository, named = shapes
    selected = select(repository, CURRENT).selected
    first, second = selected[0], selected[1]
    only = narrow(selected, allow=[second.listing_id[:8]])
    assert only == (second,)
    assert narrow(selected, limit=2) == (first, second)
    assert narrow(selected, allow=[first.listing_id[:12], second.listing_id[:12]], limit=1) == (
        first,
    )
    assert narrow(selected) == selected


def test_allow_refuses_a_short_prefix_and_one_that_matches_nothing(shapes) -> None:
    repository, _ = shapes
    selected = select(repository, CURRENT).selected
    with pytest.raises(ValueError, match="at least 8 characters"):
        narrow(selected, allow=[selected[0].listing_id[:7]])
    with pytest.raises(ValueError, match="no selected post starts with it"):
        narrow(selected, allow=["ffffffffffff"])


# --- the diff ---


def test_changed_fields_detects_each_field_and_ignores_the_provenance() -> None:
    old = make_listing("a" * 64)
    assert changed_fields(old, old) == []
    new = make_listing(
        "a" * 64,
        prompt_version="4",
        model_name="other",
        schema_version=2,
        classified_at=datetime(2026, 11, 1, tzinfo=UTC),
        price=WRITTEN_PRICE,
        price_source="text",
        areas=[30, 31],
        streets=["הירקון"],
        gender="women_only",
    )
    assert set(changed_fields(old, new)) == {"price", "gender", "streets", "areas"}


def test_a_price_source_change_alone_changes_the_price() -> None:
    old = make_listing("a" * 64, price=WRITTEN_PRICE, price_source="text")
    new = make_listing("a" * 64, price=WRITTEN_PRICE, price_source="native")
    assert changed_fields(old, new) == ["price"]


# --- the lifecycle record ---


def test_an_unflagged_record_changes_only_the_state_and_the_reason(shapes) -> None:
    repository, named = shapes
    post = named["old_version"]
    record = repository.get_lifecycle(post.listing_id)
    new = listing_for(post, post_nature="seeking")
    written = reclassified_lifecycle(record, new, post)
    assert (written.state, written.rejection_reason) == ("rejected", "seeking")
    assert written.model_copy(update={"state": "active", "rejection_reason": None}) == record


@pytest.mark.parametrize(
    ("name", "nature", "expected"),
    [
        ("old_version", "rental_offer", ("active", None)),
        ("old_version", "for_sale", ("rejected", "for_sale")),
        ("old_version_rejected", "sublet_offer", ("active", None)),
        ("old_version_rejected", "not_listing", ("rejected", "not_listing")),
        ("old_model", "rental_offer", ("rejected", "other_city")),
    ],
)
def test_the_state_follows_the_new_answer(shapes, name: str, nature: str, expected) -> None:
    repository, named = shapes
    post = named[name]
    record = repository.get_lifecycle(post.listing_id)
    other_city = repository.get_listing(post.listing_id).other_city
    new = listing_for(post, post_nature=nature, other_city=other_city)
    written = reclassified_lifecycle(record, new, post)
    assert (written.state, written.rejection_reason) == expected


@pytest.mark.parametrize("name", ["flagged", "flagged_active"])
def test_a_flagged_record_is_returned_as_it_is(shapes, name: str) -> None:
    repository, named = shapes
    post = named[name]
    record = repository.get_lifecycle(post.listing_id)
    new = listing_for(post, post_nature="seeking")
    assert reclassified_lifecycle(record, new, post) == record


def test_a_record_that_is_not_active_or_rejected_is_refused(shapes) -> None:
    repository, named = shapes
    for name in ("pending", "archived"):
        post = named[name]
        with pytest.raises(ValueError, match="only an active or rejected record"):
            reclassified_lifecycle(
                repository.get_lifecycle(post.listing_id), listing_for(post), post
            )


def test_a_pre_model_reject_and_a_mismatched_post_are_refused(shapes) -> None:
    repository, named = shapes
    post = named["premodel"]
    with pytest.raises(ValueError, match="not a model-classified record"):
        reclassified_lifecycle(repository.get_lifecycle(post.listing_id), listing_for(post), post)
    other = named["old_version"]
    with pytest.raises(ValueError, match="different posts"):
        reclassified_lifecycle(
            repository.get_lifecycle(named["flagged"].listing_id),
            listing_for(other),
            named["flagged"],
        )


def test_the_native_city_still_decides_first(shapes) -> None:
    repository, named = shapes
    post = named["old_version"].with_changes(native_location="רמת גן, תל אביב")
    record = repository.get_lifecycle(post.listing_id)
    written = reclassified_lifecycle(record, listing_for(post, post_nature="seeking"), post)
    assert (written.state, written.rejection_reason) == ("rejected", "other_city")


# --- the proposal record ---


def proposal(post_id: str = "a" * 64, **changes: Any) -> Proposal:
    old = make_listing(post_id, prompt_version="2")
    new = make_listing(post_id, prompt_version="3", post_nature="seeking")
    fields: dict[str, Any] = {
        "listing_id": post_id,
        "text_sha256": "f" * 64,
        "old": OldSide(listing=old, state="active", rejection_reason=None, flagged=False),
        "new": NewSide(listing=new, state="rejected", rejection_reason="seeking"),
        "error": None,
        "attempts": 1,
        "fields_changed": ["post_nature"],
        "dropped": Dropped(streets=[], area_names=[], other_city=None),
        "cost": 0.0002,
        "reviewed": False,
        "corrected_fields": [],
    }
    return Proposal(**{**fields, **changes})


def test_a_proposal_round_trips_through_a_json_line() -> None:
    original = proposal()
    again = Proposal.model_validate_json(original.model_dump_json())
    assert again == original
    assert again.status_changed and again.old_status == ("active", None)
    assert status_text(again.new_status) == "rejected: seeking"
    assert status_text(None) == "-"


def test_a_proposal_has_a_new_listing_or_an_error_and_never_both_or_neither() -> None:
    with pytest.raises(ValidationError, match="exactly one of new and error"):
        proposal(error="timeout")
    with pytest.raises(ValidationError, match="exactly one of new and error"):
        proposal(new=None)
    failed = proposal(new=None, error="timeout", fields_changed=[])
    assert not failed.status_changed and failed.new_status is None


def test_a_proposal_whose_listings_belong_to_another_post_is_refused() -> None:
    with pytest.raises(ValidationError, match="another post"):
        proposal(listing_id="b" * 64)
