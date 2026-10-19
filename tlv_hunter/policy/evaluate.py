"""The evaluation of a post against one user's profile (`PHASE_3.md` 3.6 (d), (f); `BASELINE.md`
§7, §8; SCHEMA.md, Gate C; DECISIONS.md #245–#247, #250, #269–#275, #288 R2, #295, #298, #299, #302,
#317, #320).

Pure: it reads the post as users see it (`SeenListing`) and the profile, writes nothing and calls
no model (`BASELINE.md` §2 principle 6; invariant 12).

Each category of an option comes out met, failed, or unknown (the post's value not written or
unclear). A failed critical category hides the post; an unknown critical one sends it to the bottom;
an unknown preference counts as not met (#298). Parking not written is unknown, as stored (#299). A
post with no written price is always at the bottom, whatever the profile holds (#302). An orange
location caps the tier at the middle (#320): two or more areas not all chosen, or no area while the
post gives a street or an area name; a post with no location at all is not capped.
"""

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from tlv_hunter.contracts.listing import Listing, Marked
from tlv_hunter.contracts.profile import (
    CriterionLevel,
    DateRangeCriterion,
    Profile,
    RangeCriterion,
    SearchOption,
)
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.policy.base import (
    CATEGORIES,
    TIER_RANK,
    Evaluation,
    FieldState,
    OptionName,
    Tier,
)
from tlv_hunter.postmodel.seen import SeenListing

Outcome = Literal["met", "failed", "unknown"]
OFFERS = ("rental_offer", "sublet_offer")  # the natures of an active post (Gate E's reasons)
# The fixed wanted values (#269).
WANTED = {"broker": False, "parking": True, "balcony": True}
OPTION_ORDER: tuple[OptionName, ...] = ("room", "whole_apartment")
# The quick chip "מיידי": entry no later than this many calendar months from today (#458).
IMMEDIATE_MONTHS = 3


@dataclass(frozen=True)
class _Category:
    level: CriterionLevel
    outcome: Outcome
    state: FieldState


@dataclass(frozen=True)
class _OptionResult:
    name: OptionName
    shown: bool
    tier: Tier | None
    fields: dict[str, FieldState]
    area_orange: bool
    women_only_icon: bool


def evaluate(seen: SeenListing, profile: Profile, now: datetime) -> Evaluation:
    """The post evaluated by the option its kind names, or by every enabled option when its kind
    is unclear or not written (#273); a sublet only when the profile's one `include_sublets` is on,
    through those same options (#246, #274, #317). "immediate" compares as the UTC calendar date of
    `now` (R2)."""
    today = require_utc(now).date()
    listing = seen.listing
    kind = listing.apartment_kind
    kind_marked = kind.state != "written"
    names: tuple[OptionName, ...] = OPTION_ORDER if kind.value is None else (kind.value,)
    results = []
    sublet_hidden = listing.post_nature == "sublet_offer" and not profile.include_sublets
    if listing.post_nature in OFFERS and not sublet_hidden:
        for name in names:
            option: SearchOption = getattr(profile, name)
            if not option.enabled:
                continue
            result = _evaluate_option(listing, option, name, today)
            if result.shown:
                results.append(result)
    missing = frozenset(
        name for name in ("price", "entry_date") if getattr(listing, name).state == "not_written"
    )
    if not results:
        return Evaluation(
            listing_id=listing.listing_id,
            shown=False,
            option=None,
            kind_marked=kind_marked,
            tier=None,
            fields={},
            missing_important=missing,
            area_orange=False,
            women_only_icon=False,
            corrected=frozenset(seen.corrected),
        )
    # Both options admit a post of unclear kind: the better tier's, the room option's on a tie
    # (#295, point 11).
    best = min(results, key=lambda r: (TIER_RANK[r.tier or "unknown"], OPTION_ORDER.index(r.name)))
    return Evaluation(
        listing_id=listing.listing_id,
        shown=True,
        option=best.name,
        kind_marked=kind_marked,
        tier="unknown" if kind_marked else best.tier,
        fields=best.fields,
        missing_important=missing,
        area_orange=best.area_orange,
        women_only_icon=best.women_only_icon,
        corrected=frozenset(seen.corrected),
    )


def _evaluate_option(
    listing: Listing, option: SearchOption, name: OptionName, today: date
) -> _OptionResult:
    size = option.size_sqm if name == "whole_apartment" else None  # no sqm in a room search (#247)
    categories: dict[str, _Category | None] = {
        "areas": _areas(listing, option),
        "price": _price(listing, option),
        "women_only": _women_only(listing, option),
        "rooms": _range(listing.rooms, option.rooms),
        "floor": _range(listing.floor, option.floor),
        "size_sqm": _range(listing.size_sqm, size),
        "broker": _fixed(listing.broker, option.broker, WANTED["broker"]),
        "parking": _fixed(listing.parking, option.parking, WANTED["parking"]),
        "balcony": _fixed(listing.balcony, option.balcony, WANTED["balcony"]),
        "entry_date": _entry_date(listing, option.entry_date, today),
    }
    fields: dict[str, FieldState] = {}
    for category in CATEGORIES:
        found = categories[category]
        fields[category] = "not_applied" if found is None else found.state
    if categories["areas"] is None and not listing.areas:
        fields["areas"] = _no_area_state(listing)  # the colour still says unclear or not written
    applied = [found for found in categories.values() if found is not None]
    critical = [found for found in applied if found.level == "critical"]
    preference = [found for found in applied if found.level == "preference"]
    area_orange = len(listing.areas) >= 2 and not set(listing.areas) <= set(option.areas)
    women_only_icon = listing.gender == "women_only" and not option.hide_women_only
    if any(found.outcome == "failed" for found in critical):
        return _OptionResult(name, False, None, fields, area_orange, women_only_icon)
    # A post with no written price is always at the bottom, also with no price range set (#302).
    if listing.price.state == "not_written" or any(
        found.outcome == "unknown" for found in critical
    ):
        tier: Tier = "unknown"
    elif all(found.outcome == "met" for found in preference) and not (
        area_orange or fields["areas"] == "unclear"
    ):
        tier = "preferences_met"
    else:
        tier = "critical_met"  # a preference not met, or an orange location (#320)
    return _OptionResult(name, True, tier, fields, area_orange, women_only_icon)


def _state(outcome: Outcome, marked_state: str) -> FieldState:
    if outcome == "met":
        return "match"
    if outcome == "failed":
        return "mismatch"
    return "unclear" if marked_state == "unclear" else "not_written"


def _no_area_state(listing: Listing) -> FieldState:
    """No area: unclear when the post gave a street or an area name, else not written (#110)."""
    return "unclear" if listing.streets or listing.stated_area_names else "not_written"


def _areas(listing: Listing, option: SearchOption) -> _Category | None:
    """Critical, fixed (#51); a post matches when any of its areas is chosen (#110)."""
    if not option.areas:
        return None
    if not listing.areas:
        return _Category("critical", "unknown", _no_area_state(listing))
    met = bool(set(listing.areas) & set(option.areas))
    return _Category("critical", "met" if met else "failed", "match" if met else "mismatch")


def _price(listing: Listing, option: SearchOption) -> _Category | None:
    """Critical, fixed; the lowest amount is compared (#95)."""
    if option.price_min is None and option.price_max is None:
        return None
    if listing.price.value is None:
        return _Category("critical", "unknown", _state("unknown", listing.price.state))
    outcome = _within(min(listing.price.value), option.price_min, option.price_max)
    return _Category("critical", outcome, _state(outcome, "written"))


def _women_only(listing: Listing, option: SearchOption) -> _Category | None:
    """Critical by default; with the switch off the post is shown with a red icon (§8)."""
    if not option.hide_women_only:
        return None
    outcome: Outcome = "failed" if listing.gender == "women_only" else "met"
    return _Category("critical", outcome, _state(outcome, "written"))


def _range[T: (int, float)](
    marked: Marked[T], criterion: RangeCriterion[T] | None
) -> _Category | None:
    if criterion is None:
        return None
    if marked.value is None:
        return _Category(criterion.level, "unknown", _state("unknown", marked.state))
    outcome = _within(marked.value, criterion.min, criterion.max)
    return _Category(criterion.level, outcome, _state(outcome, "written"))


def _fixed(marked: Marked[bool], level: CriterionLevel | None, wanted: bool) -> _Category | None:
    """Broker, parking, balcony: a fixed wanted value (#269). Not written is unknown (#299)."""
    if level is None:
        return None
    if marked.value is None:
        return _Category(level, "unknown", _state("unknown", marked.state))
    outcome: Outcome = "met" if marked.value == wanted else "failed"
    return _Category(level, outcome, _state(outcome, "written"))


def _entry_date(
    listing: Listing, criterion: DateRangeCriterion | None, today: date
) -> _Category | None:
    """ "immediate" compares as `today`, the UTC date of the evaluation (#270, R2). The chip's
    marker (#458) is the range with no lower bound up to `today` plus `IMMEDIATE_MONTHS` calendar
    months, re-computed at each evaluation, so a past date in a post is met."""
    if criterion is None:
        return None
    value = listing.entry_date.value
    if value is None:
        return _Category(criterion.level, "unknown", _state("unknown", listing.entry_date.state))
    when = today if value == "immediate" else value
    if criterion.immediate:
        outcome = _within(when, None, months_on(today, IMMEDIATE_MONTHS))
    else:
        outcome = _within(when, criterion.earliest, criterion.latest)
    return _Category(criterion.level, outcome, _state(outcome, "written"))


def months_on(day: date, months: int) -> date:
    """`months` calendar months after `day`: the same day of the month, or the month's last day
    when it has fewer (30.11 + 3 → 28.2)."""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _within[V: (int, float, date)](value: V, low: V | None, high: V | None) -> Outcome:
    """Inclusive at both ends; an end that is not set does not bound."""
    if low is not None and value < low:
        return "failed"
    if high is not None and value > high:
        return "failed"
    return "met"
