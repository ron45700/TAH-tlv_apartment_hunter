"""The filter bar's JSON to a transient `Profile` (`PHASE_3.md` 3.7 (e); DECISIONS.md #314, #315,
#317, #335).

The bar holds the shape of a profile: the two search options and the one sublet switch. Each list
request sends it; it is validated by `Profile`'s own rules (the same models the store reads, so a
date is ISO text, `YYYY-MM-DD`) and **never stored**: nothing here or in the site calls
`save_profile` for it. A guest's profile carries a fixed placeholder `user_id`.

The preferences page sends the same shape (`PUT /api/profile`, build step 5): `owned_profile` makes
it the user's own `Profile`, which only that endpoint saves (#335).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from tlv_hunter.contracts.profile import (
    PROFILE_SCHEMA_VERSION,
    Profile,
    SearchOption,
    new_profile,
)

GUEST_USER_ID = "0" * 32


class Bar(BaseModel):
    """What the bar holds: a profile's values without its owner or its time."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    room: SearchOption
    whole_apartment: SearchOption
    include_sublets: bool


FIRST_CARDS = 48
"""The cards of a list's first answer (#376): whole rows at 2, 3, 4 and 6 columns."""
MOST_BY_ID = 96
"""The most cards one request carries, the first answer's or a later page's (#376)."""


class CardsRequest(Bar):
    """`POST /api/cards`: the bar, and how many cards come whole with the order (#376); 0 asks
    the count alone (#378). `show_hidden`: the bar's "הצגת מוסתרים" (#465), never saved."""

    first: int = Field(default=FIRST_CARDS, ge=0, le=MOST_BY_ID)
    show_hidden: bool = False


class ByIdRequest(BaseModel):
    """`POST /api/cards/by-id`: the next cards of a load, by id, against the same bar (#376)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    bar: Bar
    ids: list[str] = Field(min_length=1, max_length=MOST_BY_ID)
    show_hidden: bool = False


def transient_profile(body: bytes, now: datetime) -> Profile:
    """The bar's JSON as a `Profile` for `policy.evaluate`. Raises `ValueError` (pydantic's
    `ValidationError` included) on a bar that breaks a rule: an unknown field, `min` above `max`, a
    sqm range in the room option."""
    return owned_profile(body, GUEST_USER_ID, now)


def cards_request(body: bytes, now: datetime) -> tuple[Profile, int, bool]:
    """A list request: the transient profile, `first` and `show_hidden`; the same refusals as the
    bar."""
    request = CardsRequest.model_validate_json(body)
    return _profile(request, GUEST_USER_ID, now), request.first, request.show_hidden


def by_id_request(body: bytes, now: datetime) -> tuple[Profile, list[str], bool]:
    """A later page's request: the transient profile, the ids asked and `show_hidden`."""
    request = ByIdRequest.model_validate_json(body)
    return _profile(request.bar, GUEST_USER_ID, now), request.ids, request.show_hidden


def same_values(bar: Profile, saved: Profile) -> bool:
    """Whether the bar holds the saved preferences, value by value (the page's "changed", 3.7 (e)):
    where hiding applies (#465; appendix A point 10, decided here, by the server)."""
    return bar_json(bar) == bar_json(saved)


def owned_profile(body: bytes, user_id: str, now: datetime) -> Profile:
    """The same JSON as the user's own profile, for `PUT /api/profile`; the same refusals."""
    return _profile(Bar.model_validate_json(body), user_id, now)


def _profile(bar: Bar, user_id: str, now: datetime) -> Profile:
    return Profile(
        schema_version=PROFILE_SCHEMA_VERSION,
        user_id=user_id,
        room=bar.room,
        whole_apartment=bar.whole_apartment,
        include_sublets=bar.include_sublets,
        updated_at=now,
    )


def bar_json(profile: Profile) -> dict:
    """A profile's values in the bar's shape, as the page reads and sends them."""
    return profile.model_dump(mode="json", include={"room", "whole_apartment", "include_sublets"})


def empty_bar(now: datetime) -> Profile:
    """A guest's bar as it starts (#315): a new profile's values (#268)."""
    return new_profile(GUEST_USER_ID, now)
