"""Whether a post alerts one user (`BASELINE.md` §9; DECISIONS.md #52, #360; `PHASE_4.md` 4.5).

Pure, like `evaluate`: from the post as users see it and its `Evaluation`, nothing written, no
model called (invariant 12). Rules 2 and 3 of §9 are the evaluation's (`shown`: the option of its
kind, the sublet switch, no critical condition failed); rule 1's "not rejected" holds for every card
(active posts only); rule 1's "new" (not a repost, not a post the Gate D key ties to an earlier one,
first stored after linking) is the alert pass's (`telegram/alerts.py`), since it needs the card and
the user's records. Preferences never block an alert; a critical category not written is named in
it (`missing_critical`).
"""

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Literal

from tlv_hunter.contracts.profile import Profile
from tlv_hunter.policy.base import CATEGORIES, Evaluation
from tlv_hunter.policy.colours import level_of, option_of
from tlv_hunter.postmodel.seen import SeenListing

NoAlert = Literal["not_shown", "kind_unclear", "no_price", "no_location"]

# Point 12 B of `PHASE_5.md` (DECISIONS.md #473, replacing #443): after a pause collection is never
# capped, and a post published longer ago than this before the alert pass never alerts.
PUBLISHED_WINDOW = timedelta(hours=24)


def published_too_long_ago(posted_at: datetime, now: datetime) -> bool:
    """The card's shown post (its earliest publication) is older than `PUBLISHED_WINDOW` at the
    alert pass: no alert, however recently it was collected or classified (no burst after a
    pause). The post is stored and on the site as always."""
    return posted_at < now - PUBLISHED_WINDOW


def no_alert_reason(seen: SeenListing, evaluation: Evaluation) -> NoAlert | None:
    """`None` when the post alerts; else why not. §9: shown by an enabled option (2, 3); its kind
    written (#360); an explicit price (4); its location understood (5): at least one area, and,
    when the user chose areas, one of them (the evaluation's critical area); no area at all, a
    street the model could not place included, never alerts (§7)."""
    listing = seen.listing
    if listing.listing_id != evaluation.listing_id:
        raise ValueError(f"evaluation {evaluation.listing_id} is not of {listing.listing_id}")
    if not evaluation.shown:
        return "not_shown"
    if evaluation.kind_marked:
        return "kind_unclear"
    if listing.price.state != "written":
        return "no_price"
    if not listing.areas:
        return "no_location"
    return None


def set_categories(profile: Profile, evaluation: Evaluation) -> Mapping[str, str]:
    """The categories the user set in the option that admits the post, each with its level
    ("critical" / "preference"), in `CATEGORIES` order: the alert's lines (#363)."""
    option = option_of(profile, evaluation)
    if option is None:
        return {}
    levels = {name: level_of(option, name) for name in CATEGORIES}
    return {name: level for name, level in levels.items() if level is not None}


def missing_critical(profile: Profile, evaluation: Evaluation) -> tuple[str, ...]:
    """The critical categories the post does not state: the alert's "⚠️ חסר" line (§9)."""
    return tuple(
        name
        for name, level in set_categories(profile, evaluation).items()
        if level == "critical" and evaluation.fields.get(name) == "not_written"
    )
