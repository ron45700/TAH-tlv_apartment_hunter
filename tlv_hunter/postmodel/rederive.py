"""Re-deriving the stored rejections with the native-location rule (DECISIONS.md #214). Plain
functions over the Repository: `plan_rederivation` reads and writes nothing; the command
(`jobs/rederive_rejections.py`) writes. No model call: a post's rejection is a pure function of its
stored `RawPost` and `Listing`, and the `Listing` is never edited.

Only a post that the model classified is considered: state `active`, or `rejected` for a reason the
model's answer gives (`other_city`, `seeking`, `for_sale`, `not_listing`). The pre-model rejects,
`flagged`, archived and pending posts are left alone.
"""

from collections import Counter
from dataclasses import dataclass

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.rejects import model_reason, native_locality
from tlv_hunter.store.base import Repository

MODEL_REASONS = (None, "other_city", "seeking", "for_sale", "not_listing")

Status = tuple[str, str | None]
"""A post's (state, rejection_reason)."""


@dataclass(frozen=True)
class Change:
    listing_id: str
    old: Status
    new: Status
    locality: str | None
    """The native locality, shown with the change: a city name, never post text."""


@dataclass(frozen=True)
class Plan:
    considered: int
    native_present: int
    """Of the considered posts, those whose location field has a usable locality (#214)."""
    changes: tuple[Change, ...]
    before: dict[Status, int]
    after: dict[Status, int]


def rederived_lifecycle(existing: PostLifecycle, listing: Listing, post: RawPost) -> PostLifecycle:
    """The record with the rule applied: only `state` and `rejection_reason` can change."""
    if existing.listing_id != listing.listing_id or post.listing_id != listing.listing_id:
        raise ValueError("the record, the post and the Listing belong to different posts")
    if (
        existing.state not in ("active", "rejected")
        or existing.rejection_reason not in MODEL_REASONS
    ):
        raise ValueError(
            f"not a model-classified record: {existing.state}, {existing.rejection_reason}"
        )
    reason = model_reason(post, listing)
    return PostLifecycle(
        **{
            **dict(existing),
            "state": "active" if reason is None else "rejected",
            "rejection_reason": reason,
        }
    )


def plan_rederivation(repository: Repository) -> Plan:
    changes: list[Change] = []
    before: Counter[Status] = Counter()
    after: Counter[Status] = Counter()
    considered = native_present = 0
    for post in repository.query():
        record = repository.get_lifecycle(post.listing_id)
        if record is None or record.state not in ("active", "rejected"):
            continue
        if record.rejection_reason not in MODEL_REASONS:
            continue
        listing = repository.get_listing(post.listing_id)
        if listing is None:
            continue
        considered += 1
        locality = native_locality(post.native_location)
        native_present += locality is not None
        old: Status = (record.state, record.rejection_reason)
        new_record = rederived_lifecycle(record, listing, post)
        new: Status = (new_record.state, new_record.rejection_reason)
        before[old] += 1
        after[new] += 1
        if new != old:
            changes.append(Change(post.listing_id, old, new, locality))
    return Plan(
        considered,
        native_present,
        tuple(sorted(changes, key=lambda c: c.listing_id)),
        dict(before),
        dict(after),
    )
