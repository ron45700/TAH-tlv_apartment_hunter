"""The card's colours: each field's colour, the glow and the tier's reasons (`PHASE_3.md` 3.7 (d);
`BASELINE.md` §6, §8; DECISIONS.md #308, #309, #320–#323, #326, #330 points 4–6, 8, 18).

Pure, like `evaluate`: it reads the post as users see it, an `Evaluation` and the profile the
evaluation used, writes nothing and calls no model. Computed on the server, so the page holds no
rule (#330 point 18). Nothing here is stored or written on a post (invariant 12).

A field's colour, by (d)'s table:
- a profile category, from its `FieldState`: `"match"` green, `"mismatch"` red, `"not_written"`
  grey, `"unclear"` orange;
- `"not_applied"`, and every field that is not a category, from the post's own value: a known
  positive green (broker `False`; balcony, parking, elevator, air conditioning `True`), a known
  negative plain, not written grey, unclear orange, any other written value plain;
- the area: orange when the location is orange (`area_orange`, or no area while the post gives a
  street or an area name), grey with no location, green on `"match"`, else plain;
- price and entry date not written: `"missing"`, the important-missing badge, never grey.
"""

from collections.abc import Mapping
from typing import Literal

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.profile import Profile, SearchOption
from tlv_hunter.policy.base import CATEGORIES, Evaluation
from tlv_hunter.policy.evaluate import WANTED

Colour = Literal["green", "red", "grey", "orange", "plain", "missing"]
Glow = Literal["green", "orange", "red"]

# The known positive value of each yes-or-no field (#309): the profile's fixed wanted values
# (#269, one implementation) and the two the card alone uses.
POSITIVE: Mapping[str, bool] = {**WANTED, "elevator": True, "air_conditioning": True}
IMPORTANT = ("price", "entry_date")
# Every field the card colours, besides the area.
COLOURED = (
    "price",
    "entry_date",
    "rooms",
    "floor",
    "building_floors",
    "size_sqm",
    "room_size_sqm",
    "broker",
    "balcony",
    "parking",
    "elevator",
    "air_conditioning",
    "furnished",
    "arnona",
    "house_committee",
)
# The categories whose level the user chooses: only these can hold a preference (§8).
LEVELLED = ("rooms", "floor", "size_sqm", "broker", "parking", "balcony", "entry_date")
_FROM_STATE: Mapping[str, Colour] = {
    "match": "green",
    "mismatch": "red",
    "not_written": "grey",
    "unclear": "orange",
}
_TIER_GLOW: Mapping[str, Glow] = {
    "preferences_met": "green",
    "critical_met": "orange",
    "unknown": "red",
}


def field_colours(listing: Listing, evaluation: Evaluation | None) -> Mapping[str, Colour]:
    """Every coloured field and `"areas"`. With no evaluation (a post the list does not hold), each
    field takes its colour from the post's own value."""
    fields = evaluation.fields if evaluation is not None and evaluation.shown else {}
    colours: dict[str, Colour] = {}
    for name in COLOURED:
        marked = getattr(listing, name)
        if name in IMPORTANT and marked.state == "not_written":
            colours[name] = "missing"
            continue
        state = fields.get(name, "not_applied")
        colours[name] = _FROM_STATE[state] if state != "not_applied" else _own(name, listing)
    colours["areas"] = _area(listing, evaluation, fields.get("areas", "not_applied"))
    return colours


def option_of(profile: Profile, evaluation: Evaluation) -> SearchOption | None:
    return getattr(profile, evaluation.option) if evaluation.option is not None else None


def holds_a_preference(option: SearchOption) -> bool:
    """Any category at the level "preference" (#322). Areas, price and "women only" are critical
    by their nature."""
    return any(level_of(option, name) == "preference" for name in LEVELLED)


def glow(evaluation: Evaluation, profile: Profile) -> Glow | None:
    """The tier's colour (#308); no green while the admitting option holds no preference (#322).
    `None` for a post that is not shown."""
    option = option_of(profile, evaluation)
    if not evaluation.shown or evaluation.tier is None or option is None:
        return None
    if evaluation.tier == "preferences_met" and not holds_a_preference(option):
        return None
    return _TIER_GLOW[evaluation.tier]


def tier_reasons(listing: Listing, evaluation: Evaluation, profile: Profile) -> tuple[str, ...]:
    """Why a card is not in the first tier, for the "i" and the opened post (#323, #332 point 29).
    The bottom: the kind unclear (`"kind"`), no written price (#302), and every critical category
    not written or unclear. The middle: every preference not met or not known (#298), and an
    orange location (`"location"`, #320). The first tier, or a post not shown: none."""
    option = option_of(profile, evaluation)
    if not evaluation.shown or option is None or evaluation.tier == "preferences_met":
        return ()
    fields = evaluation.fields
    if evaluation.tier == "unknown":
        reasons = ["kind"] if evaluation.kind_marked else []
        if listing.price.state == "not_written":
            reasons.append("price")
        for name in CATEGORIES:
            unknown = fields.get(name) in ("not_written", "unclear")
            if unknown and level_of(option, name) == "critical" and name not in reasons:
                reasons.append(name)
        return tuple(reasons)
    reasons = [
        name
        for name in CATEGORIES
        if level_of(option, name) == "preference" and fields.get(name) != "match"
    ]
    if evaluation.area_orange or fields.get("areas") == "unclear":
        reasons.append("location")
    return tuple(reasons)


def _own(name: str, listing: Listing) -> Colour:
    marked = getattr(listing, name)
    if marked.state == "not_written":
        return "grey"
    if marked.state == "unclear":
        return "orange"
    if name in POSITIVE:
        return "green" if marked.value == POSITIVE[name] else "plain"
    return "plain"


def _area(listing: Listing, evaluation: Evaluation | None, state: str) -> Colour:
    if evaluation is not None and evaluation.area_orange:
        return "orange"
    if not listing.areas:
        return "orange" if listing.streets or listing.stated_area_names else "grey"
    return "green" if state == "match" else "plain"


def level_of(option: SearchOption, name: str) -> str | None:
    """The level of a category in the option; `None` when it holds no value. Areas and price are
    critical when set; "women only" is critical while it hides (§8)."""
    if name == "areas":
        return "critical" if option.areas else None
    if name == "price":
        return "critical" if option.price_min is not None or option.price_max is not None else None
    if name == "women_only":
        return "critical" if option.hide_women_only else None
    value = getattr(option, name)
    if value is None:
        return None
    return value if isinstance(value, str) else value.level
