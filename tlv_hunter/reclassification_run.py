"""The two loops of task 2.9 (`PHASE_2.md` 2.9; DECISIONS.md #217–#222). Wiring, like
`classification_run.py`, whose attempts table it reuses.

`propose` is stage 1: for each selected post, ask the model again and keep the answer as a proposal.
It reads the store and **writes nothing to it**. `apply_proposals` is stage 2: it replaces the
`Listing`s of the proposals it is given, each in one transaction, and never writes a `RawPost`
(invariant 14).
"""

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from tlv_hunter.classification_run import RunStop, attempt_post, tokens_by_kind
from tlv_hunter.classify.base import ClassificationError
from tlv_hunter.classify.cost import CostMeter
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.labeling.regression_set import text_sha256
from tlv_hunter.postmodel.reclassify import (
    Candidate,
    Dropped,
    NewSide,
    OldSide,
    Proposal,
    changed_fields,
    reclassified_lifecycle,
    status_text,
)
from tlv_hunter.store.base import Repository

logger = logging.getLogger(__name__)

ERROR_TEXT_LIMIT = 200


@dataclass(frozen=True)
class ProposeResult:
    proposals: tuple[Proposal, ...]
    not_attempted: tuple[str, ...]
    """The selected posts the run stopped before."""
    stopped: str | None
    spent: float


def propose(
    *,
    repository: Repository,
    classifier,
    meter: CostMeter,
    sleep: Callable[[float], None],
    candidates: Sequence[Candidate],
    corrections: Mapping[str, tuple[str, ...]],
    on_proposal: Callable[[Proposal], None],
) -> ProposeResult:
    """`classifier` has `classify_completed(post)`. `corrections` maps the posts with a reviewed
    correction on file to the fields Ron corrected. A failed post gets a proposal with an error and
    no new `Listing`; nothing about it reaches the store, so `classification_failures` and
    `last_classification_error` stay as they are (#152, #221)."""
    proposals: list[Proposal] = []
    stopped: str | None = None
    attempted = 0
    for candidate in candidates:
        post = repository.get(candidate.listing_id)
        record = repository.get_lifecycle(candidate.listing_id)
        old = repository.get_listing(candidate.listing_id)
        if post is None or record is None or old is None:
            raise RuntimeError(f"{candidate.listing_id}: post, record or Listing vanished")
        first_call = len(meter.calls)
        try:
            result, attempts = attempt_post(post, classifier, sleep)
        except RunStop as stop:
            stopped = stop.reason
            logger.warning("reclassify stopped before %s: %s", candidate.listing_id, stop.reason)
            break
        attempted += 1
        calls = meter.calls[first_call:]
        old_side = OldSide(
            listing=old,
            state=record.state,  # type: ignore[arg-type]  # selected: active or rejected
            rejection_reason=record.rejection_reason,
            flagged=record.flagged_by is not None,
        )
        reviewed = candidate.listing_id in corrections
        common = {
            "listing_id": candidate.listing_id,
            "text_sha256": text_sha256(post.text),
            "old": old_side,
            "attempts": attempts,
            "cost": sum(call.cost for call in calls),
            "reviewed": reviewed,
            "corrected_fields": list(corrections.get(candidate.listing_id, ())),
        }
        if isinstance(result, ClassificationError):
            proposal = Proposal(
                **common,
                new=None,
                error=str(result)[:ERROR_TEXT_LIMIT],
                fields_changed=[],
                dropped=Dropped(streets=[], area_names=[], other_city=None),
            )
        else:
            written = reclassified_lifecycle(record, result.listing, post)
            proposal = Proposal(
                **common,
                new=NewSide(
                    listing=result.listing,
                    state=written.state,  # type: ignore[arg-type]
                    rejection_reason=written.rejection_reason,
                ),
                error=None,
                fields_changed=changed_fields(old, result.listing),
                dropped=Dropped(
                    streets=list(result.dropped_streets),
                    area_names=list(result.dropped_area_names),
                    other_city=result.dropped_other_city,
                ),
            )
        on_proposal(proposal)
        proposals.append(proposal)
        _log_proposal(proposal, calls)
    not_attempted = tuple(c.listing_id for c in candidates[attempted:])
    logger.info(
        "reclassify done: %d attempted, %d proposed, %d failed, %d not attempted, %d state "
        "changes, %d calls, tokens %s, $%.6f of $%.2f, stopped %s",
        len(proposals),
        sum(p.new is not None for p in proposals),
        sum(p.new is None for p in proposals),
        len(not_attempted),
        sum(p.status_changed for p in proposals),
        len(meter.calls),
        tokens_by_kind(meter.calls),
        meter.spent,
        meter.cap,
        stopped or "no",
    )
    return ProposeResult(tuple(proposals), not_attempted, stopped, meter.spent)


def _log_proposal(proposal: Proposal, calls) -> None:
    """No post text, name, phone or key: identifiers, statuses, counts and field names only."""
    logger.info(
        "post %s: %s, %s -> %s, %d fields changed (%s), %d attempts, %d calls, tokens %s, $%.6f, "
        "reported model %s",
        proposal.listing_id,
        "proposed" if proposal.new is not None else f"failed: {proposal.error}",
        status_text(proposal.old_status),
        status_text(proposal.new_status),
        len(proposal.fields_changed),
        ",".join(proposal.fields_changed) or "-",
        proposal.attempts,
        len(calls),
        tokens_by_kind(calls),
        proposal.cost,
        ",".join(sorted({str(call.reported_model) for call in calls})) or "-",
    )


# --- stage 2 ---

ApplyResult = Literal["written", "already applied", "not written"]


@dataclass(frozen=True)
class ApplyOutcome:
    listing_id: str
    result: ApplyResult
    reason: str | None = None
    """Why a post was not written."""
    old_status: tuple[str, str | None] | None = None
    new_status: tuple[str, str | None] | None = None


def apply_proposals(
    *,
    repository: Repository,
    proposals: Sequence[Proposal],
    on_written: Callable[[Proposal], None] | None = None,
) -> list[ApplyOutcome]:
    """Replace the `Listing` of each proposal, in `listing_id` order. Each post is read again right
    before its write; a post that is no longer what the run saw is not written and is returned with
    its reason (#220). A proposal already in the store is "already applied": a second apply is a
    no-op. `save_classification` writes the `Listing` and the record in one transaction and never a
    `RawPost`."""
    outcomes = []
    for proposal in sorted(proposals, key=lambda p: p.listing_id):
        outcomes.append(_apply_one(repository, proposal, on_written))
    return outcomes


def _apply_one(
    repository: Repository, proposal: Proposal, on_written: Callable[[Proposal], None] | None
) -> ApplyOutcome:
    listing_id = proposal.listing_id
    if proposal.new is None:
        return ApplyOutcome(listing_id, "not written", "the run has no new Listing for it")
    post = repository.get(listing_id)
    record = repository.get_lifecycle(listing_id)
    stored = repository.get_listing(listing_id)
    if post is None or record is None or stored is None:
        return ApplyOutcome(
            listing_id, "not written", "the post, its record or its Listing is gone"
        )
    if stored == proposal.new.listing:
        return ApplyOutcome(listing_id, "already applied")
    reason = _changed_since(proposal, post, record, stored)
    if reason is not None:
        return ApplyOutcome(listing_id, "not written", reason)
    lifecycle = reclassified_lifecycle(record, proposal.new.listing, post)
    repository.save_classification(proposal.new.listing, lifecycle)
    if on_written is not None:
        on_written(proposal)
    return ApplyOutcome(
        listing_id,
        "written",
        old_status=(record.state, record.rejection_reason),
        new_status=(lifecycle.state, lifecycle.rejection_reason),
    )


def _changed_since(proposal: Proposal, post: RawPost, record, stored) -> str | None:
    if text_sha256(post.text) != proposal.text_sha256:
        return "the text changed since the run"
    if stored != proposal.old.listing:
        return "the Listing changed since the run"
    if (record.state, record.rejection_reason, record.flagged_by is not None) != (
        proposal.old.state,
        proposal.old.rejection_reason,
        proposal.old.flagged,
    ):
        return "the record changed since the run"
    return None
