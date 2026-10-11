"""The `policy/` seam's contract (`CLAUDE.md`; DECISIONS.md #295): `evaluate(seen, profile, now) ->
Evaluation`, a classified post as one user sees it, against that user's profile. Pure: it reads
records, writes nothing, calls no model (`BASELINE.md` §2 principle 6; invariant 12). An
`Evaluation` is never stored and never written on a post.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from tlv_hunter.contracts.profile import Profile
from tlv_hunter.postmodel.seen import SeenListing

OptionName = Literal["room", "whole_apartment"]
Tier = Literal["preferences_met", "critical_met", "unknown"]
"""`BASELINE.md` §8: every preference met; the critical conditions met but not every preference
(an unknown preference counts as not met, #298); an unknown critical category, or no written price
whatever the profile holds (#302): the bottom."""
FieldState = Literal["match", "mismatch", "not_written", "unclear", "not_applied"]

TIER_RANK: Mapping[Tier, int] = {"preferences_met": 0, "critical_met": 1, "unknown": 2}

# The profile's categories, the keys of `Evaluation.fields`.
CATEGORIES = (
    "areas",
    "price",
    "women_only",
    "rooms",
    "floor",
    "size_sqm",
    "broker",
    "parking",
    "balcony",
    "entry_date",
)


@dataclass(frozen=True)
class Evaluation:
    """What one user's profile makes of one post: never stored (invariant 12)."""

    listing_id: str
    shown: bool
    option: OptionName | None
    """The search option that admits the post; `None` when it is not shown."""
    kind_marked: bool
    """The post's kind is unclear or not written: shown at the bottom, its kind marked (#273)."""
    tier: Tier | None
    """`None` when not shown."""
    fields: Mapping[str, FieldState]
    """One state per category of `CATEGORIES`, for the option that admits the post; empty when it
    is not shown."""
    missing_important: frozenset[str]
    """`price` and `entry_date` when not written (`BASELINE.md` §6)."""
    area_orange: bool
    """Two or more areas, not all in the option's selection (#250, #275)."""
    women_only_icon: bool
    """A "women only" post shown because the option does not hide it: the red icon (§8)."""
    corrected: frozenset[str]
    """The fields corrected by hand (#256)."""


Policy = Callable[[SeenListing, Profile, datetime], Evaluation]
"""The seam's shape; `policy.evaluate.evaluate` is the implementation."""
