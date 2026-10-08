"""Reclassify (`PHASE_2.md` 2.9; DECISIONS.md #144, #217–#222): which stored `Listing`s are not the
current ones, what a new answer changes, and the record of one proposed replacement. Plain functions
over the Repository: nothing here calls the model or writes anything.

A post is selected when it has a `Listing`, its state is `active` or `rejected` by the model (or it
is flagged), and the `Listing`'s (`prompt_version`, `schema_version`, `model_name`) differs from the
current triple. The pre-model rejects, archived and pending posts are never selected.
"""

from collections import Counter
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.rederive import MODEL_REASONS, rederived_lifecycle
from tlv_hunter.store.base import Repository

RECLASSIFY_DIRECTORY = "reclassify"
"""Under `store_root`: one folder per `reclassify --run` (#219)."""
PROPOSALS_FILE = "proposals.jsonl"
SUMMARY_FILE = "summary.json"
REPORT_FILE = "diff.html"
ALLOW_UNCHANGED_FILE = "allow_unchanged.txt"
ALLOW_STATE_CHANGES_FILE = "allow_state_changes.txt"
MIN_PREFIX = 8

Triple = tuple[str, int, str]
"""A `Listing`'s (prompt_version, schema_version, model_name)."""
Status = tuple[str, str | None]
"""A post's (state, rejection_reason)."""

# What always differs between two classifications of one post, and `price_source`, which follows the
# price: neither is a field that "changed".
_NOT_COMPARED = frozenset(
    {
        "schema_version",
        "listing_id",
        "model_name",
        "prompt_version",
        "classified_at",
        "price_source",
    }
)
COMPARED_FIELDS = tuple(name for name in Listing.model_fields if name not in _NOT_COMPARED)


def triple_of(listing: Listing) -> Triple:
    return (listing.prompt_version, listing.schema_version, listing.model_name)


@dataclass(frozen=True)
class Candidate:
    listing_id: str
    triple: Triple
    status: Status
    flagged: bool


@dataclass(frozen=True)
class ReclassifyPlan:
    current: Triple
    stored: dict[Triple, int]
    """Every stored `Listing`, counted by its triple."""
    selected: tuple[Candidate, ...]
    left_out: dict[str, int]
    """The other posts, by the reason they are not selected."""


def select(repository: Repository, current: Triple) -> ReclassifyPlan:
    stored: Counter[Triple] = Counter()
    left_out: Counter[str] = Counter()
    selected: list[Candidate] = []
    for post in repository.query():
        record = repository.get_lifecycle(post.listing_id)
        listing = repository.get_listing(post.listing_id)
        if listing is None:
            left_out[f"no Listing ({'no record' if record is None else _label(record)})"] += 1
            continue
        triple = triple_of(listing)
        stored[triple] += 1
        if record is None or not _selectable(record):
            left_out[f"not selectable ({'no record' if record is None else _label(record)})"] += 1
        elif triple == current:
            left_out["current"] += 1
        else:
            selected.append(
                Candidate(
                    post.listing_id,
                    triple,
                    (record.state, record.rejection_reason),
                    record.flagged_by is not None,
                )
            )
    return ReclassifyPlan(
        current,
        dict(stored),
        tuple(sorted(selected, key=lambda c: c.listing_id)),
        dict(left_out),
    )


def narrow(
    candidates: Sequence[Candidate], *, limit: int | None = None, allow: Collection[str] = ()
) -> tuple[Candidate, ...]:
    """`--allow` keeps the candidates whose id starts with one of the prefixes (a prefix that
    matches none is refused, #217), then `--limit` keeps the first N by `listing_id`."""
    chosen = tuple(candidates)
    if allow:
        for prefix in allow:
            if len(prefix) < MIN_PREFIX:
                raise ValueError(f"an --allow prefix needs at least {MIN_PREFIX} characters")
            if not any(c.listing_id.startswith(prefix) for c in chosen):
                raise ValueError(f"--allow {prefix}: no selected post starts with it")
        chosen = tuple(c for c in chosen if any(c.listing_id.startswith(p) for p in allow))
    return chosen if limit is None else chosen[:limit]


def _selectable(record: PostLifecycle) -> bool:
    if record.state not in ("active", "rejected"):
        return False
    return record.flagged_by is not None or record.rejection_reason in MODEL_REASONS


def _label(record: PostLifecycle) -> str:
    return (
        record.state
        if record.rejection_reason is None
        else (f"{record.state}: {record.rejection_reason}")
    )


def reclassified_lifecycle(
    existing: PostLifecycle, listing: Listing, post: RawPost
) -> PostLifecycle:
    """The record written with the new `Listing`. A flagged post keeps its flag and its state, so
    its record is returned as it is (#144, #217); any other model-classified record changes only
    `state` and `rejection_reason`, from the new answer (`rederived_lifecycle`)."""
    if existing.state not in ("active", "rejected"):
        raise ValueError(
            f"only an active or rejected record is reclassified, not {existing.state!r}"
        )
    if existing.flagged_by is not None:
        if existing.listing_id != listing.listing_id or post.listing_id != listing.listing_id:
            raise ValueError("the record, the post and the Listing belong to different posts")
        return existing
    return rederived_lifecycle(existing, listing, post)


def changed_fields(old: Listing, new: Listing) -> list[str]:
    """The `Listing` fields whose value differs, provenance left out. `price` also compares its
    source."""
    changed = []
    for name in COMPARED_FIELDS:
        before, after = getattr(old, name), getattr(new, name)
        if name == "price":
            before, after = (before, old.price_source), (after, new.price_source)
        if before != after:
            changed.append(name)
    return changed


# --- the record of one proposed replacement: one line of `proposals.jsonl` (#219) ---


class OldSide(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    listing: Listing
    state: Literal["active", "rejected"]
    rejection_reason: str | None
    flagged: bool


class NewSide(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    listing: Listing
    state: Literal["active", "rejected"]
    rejection_reason: str | None
    """What the lifecycle record will say after the apply (a flagged post's is its old one)."""


class Dropped(BaseModel):
    """The names #162 and #180 dropped from the new answer, for the dropped-names file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    streets: list[str]
    area_names: list[str]
    other_city: str | None


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    listing_id: str
    text_sha256: str
    """The text the model received; the apply refuses a post whose text is another one."""
    old: OldSide
    new: NewSide | None
    error: str | None
    """The short reason the post failed; `new` is None then."""
    attempts: int
    fields_changed: list[str]
    dropped: Dropped
    cost: float
    reviewed: bool
    """`corrections.json` holds a reviewed correction for this post (#222)."""
    corrected_fields: list[str]

    @model_validator(mode="after")
    def _new_or_error(self) -> Self:
        if (self.new is None) == (self.error is None):
            raise ValueError("exactly one of new and error is set")
        if self.new is not None and self.new.listing.listing_id != self.listing_id:
            raise ValueError("the new Listing belongs to another post")
        if self.old.listing.listing_id != self.listing_id:
            raise ValueError("the old Listing belongs to another post")
        return self

    @property
    def old_status(self) -> Status:
        return (self.old.state, self.old.rejection_reason)

    @property
    def new_status(self) -> Status | None:
        return None if self.new is None else (self.new.state, self.new.rejection_reason)

    @property
    def status_changed(self) -> bool:
        return self.new is not None and self.old_status != self.new_status


def status_text(status: Status | None) -> str:
    if status is None:
        return "-"
    return status[0] if status[1] is None else f"{status[0]}: {status[1]}"
