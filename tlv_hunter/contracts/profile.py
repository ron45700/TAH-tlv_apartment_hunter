"""Gate C: a user's profile, its two search options and its one sublet switch (SCHEMA.md, Gate C;
DECISIONS.md #245–#247, #268–#272, #288, #317).

The evaluation of a post against a profile is `policy/`'s (task 3.6); this module holds the
record and its rules only.
"""

import json
from datetime import date, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id
from tlv_hunter.parsing.datetimes import require_utc

PROFILE_SCHEMA_VERSION = 2
AREA_NUMBERS = range(1, 72)  # ms_shchuna 1–71 (#81, #83)
LOWEST_FLOOR = -1  # a basement (#118, #271)

CriterionLevel = Literal["preference", "critical"]


class RangeCriterion[T](BaseModel):
    """A range with at least one end; `level` is how it counts (`BASELINE.md` §8)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    min: T | None
    max: T | None
    level: CriterionLevel

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        if self.min is None and self.max is None:
            raise ValueError("a range has at least one end")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not exceed max")
        return self


class DateRangeCriterion(BaseModel):
    """The entry-date range, both ends optional but not both absent (#270)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    earliest: date | None
    latest: date | None
    level: CriterionLevel

    @model_validator(mode="after")
    def _check_range(self) -> Self:
        if self.earliest is None and self.latest is None:
            raise ValueError("a date range has at least one end")
        if self.earliest is not None and self.latest is not None and self.earliest > self.latest:
            raise ValueError("earliest must not be after latest")
        return self


class SearchOption(BaseModel):
    """One of the two searches, with its own full set of values (#245)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    enabled: bool
    areas: list[int]
    price_min: int | None
    price_max: int | None
    hide_women_only: bool
    rooms: RangeCriterion[float] | None
    floor: RangeCriterion[int] | None
    size_sqm: RangeCriterion[float] | None
    broker: CriterionLevel | None
    parking: CriterionLevel | None
    balcony: CriterionLevel | None
    entry_date: DateRangeCriterion | None

    @field_validator("areas")
    @classmethod
    def _areas(cls, value: list[int]) -> list[int]:
        if any(number not in AREA_NUMBERS for number in value):
            raise ValueError("areas are municipal numbers 1–71")
        if value != sorted(set(value)):
            raise ValueError("areas are sorted, with no repeats")
        return value

    @field_validator("rooms")
    @classmethod
    def _half_rooms(cls, value: RangeCriterion[float] | None) -> RangeCriterion[float] | None:
        if value is not None:
            for end in (value.min, value.max):
                if end is not None and (end * 2) != int(end * 2):
                    raise ValueError("rooms are whole or half numbers (#271)")
        return value

    @field_validator("floor")
    @classmethod
    def _floor(cls, value: RangeCriterion[int] | None) -> RangeCriterion[int] | None:
        if value is not None:
            for end in (value.min, value.max):
                if end is not None and end < LOWEST_FLOOR:
                    raise ValueError("the lowest floor is -1, a basement (#271)")
        return value

    @model_validator(mode="after")
    def _check_prices(self) -> Self:
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("price_min must not exceed price_max")
        return self


class Profile(BaseModel):
    """One per user (#245); keyed by `user_id`."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    user_id: str
    room: SearchOption
    whole_apartment: SearchOption
    include_sublets: bool
    """One switch for the profile (#317): a sublet shows only through an enabled option of its
    kind, and only when this is on."""
    updated_at: datetime

    @classmethod
    def from_stored_json(cls, doc: str) -> "Profile":
        """Read a stored profile. A version-1 one reads as version 2 (#317): its two per-option
        `include_sublets` become the profile's one switch, on when either was on. Read-time only,
        as `PostLifecycle.from_stored_json` does: it is written as version 2 the next time it is
        saved, and nothing is rewritten in bulk. `UserDataStore` reads profiles only through here;
        plain `model_validate_json` converts nothing."""
        data = json.loads(doc)
        if isinstance(data, dict) and data.get("schema_version") == 1:
            doc = json.dumps(_version_1_as_2(data))
        return cls.model_validate_json(doc)

    @field_validator("user_id")
    @classmethod
    def _opaque(cls, value: str) -> str:
        require_opaque_id(value)
        return value

    @field_validator("updated_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != PROFILE_SCHEMA_VERSION:
            raise ValueError(f"unknown Profile schema_version {self.schema_version!r}")
        if self.room.size_sqm is not None:
            raise ValueError("the room search has no sqm filter (#247)")
        return self


def _version_1_as_2(data: dict[str, Any]) -> dict[str, Any]:
    if "include_sublets" in data:
        raise ValueError("a version-1 profile has no profile-level include_sublets")
    converted = {**data, "schema_version": PROFILE_SCHEMA_VERSION}
    switched = False
    for name in ("room", "whole_apartment"):
        option = data.get(name)
        if isinstance(option, dict) and "include_sublets" in option:
            option = dict(option)
            if option.pop("include_sublets") is True:
                switched = True
            converted[name] = option
    converted["include_sublets"] = switched
    return converted


def new_profile(user_id: str, now: datetime) -> Profile:
    """A new user's profile (#268): both options on, nothing set, sublets off (#317), "women only"
    hidden."""
    option = SearchOption(
        enabled=True,
        areas=[],
        price_min=None,
        price_max=None,
        hide_women_only=True,
        rooms=None,
        floor=None,
        size_sqm=None,
        broker=None,
        parking=None,
        balcony=None,
        entry_date=None,
    )
    return Profile(
        schema_version=PROFILE_SCHEMA_VERSION,
        user_id=user_id,
        room=option,
        whole_apartment=option,
        include_sublets=False,
        updated_at=now,
    )
