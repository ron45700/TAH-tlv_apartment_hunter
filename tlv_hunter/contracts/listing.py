from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.textnorm.phones import canonical_phone

LISTING_SCHEMA_VERSION = 1
AREA_NUMBERS = range(1, 72)


class Marked[T](BaseModel):
    """Gate B's state structure (DECISIONS.md #91, #109): a value only when written."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    state: Literal["written", "not_written", "unclear"]
    value: T | None

    @model_validator(mode="after")
    def _value_only_when_written(self) -> Self:
        if (self.state == "written") != (self.value is not None):
            raise ValueError("value is set exactly when state is 'written'")
        return self


class PhoneName(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    phone: str
    name: str

    @field_validator("phone")
    @classmethod
    def _stored_phone_format(cls, value: str) -> str:
        if value != canonical_phone(value):
            raise ValueError("phone must be in the stored format (canonical_phone)")
        return value


class Listing(BaseModel):
    """Gate B: one classification record per post, keyed by listing_id, separate from RawPost."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    listing_id: str
    model_name: str
    prompt_version: str
    classified_at: datetime
    post_nature: Literal["rental_offer", "sublet_offer", "seeking", "for_sale", "not_listing"]
    apartment_kind: Marked[Literal["room", "whole_apartment"]]
    price: Marked[list[int]]
    price_source: Literal["text", "native"] | None
    entry_date_written: str | None
    entry_date: Marked[Literal["immediate"] | date]
    rooms: Marked[float]
    floor: Marked[int]
    building_floors: Marked[int]
    size_sqm: Marked[float]
    room_size_sqm: Marked[float]
    broker: Marked[bool]
    balcony: Marked[bool]
    parking: Marked[bool]
    elevator: Marked[bool]
    air_conditioning: Marked[bool]
    furnished: Marked[Literal["yes", "partial", "no"]]
    arnona: Marked[int | Literal["included"]]
    house_committee: Marked[int | Literal["included"]]
    gender: Literal["no_restriction", "women_preferred", "women_only"]
    streets: list[str]
    stated_area_names: list[str]
    areas: list[int]
    other_city: str | None
    phone_names: list[PhoneName]

    @field_validator("classified_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @field_validator("areas")
    @classmethod
    def _areas(cls, value: list[int]) -> list[int]:
        if any(number not in AREA_NUMBERS for number in value):
            raise ValueError("areas are municipal numbers 1-71")
        if value != sorted(set(value)):
            raise ValueError("areas are sorted with no repeats")
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if (self.price_source is None) != (self.price.state == "not_written"):
            raise ValueError("price_source is None exactly when price is not written")
        if self.price.value is not None:
            if not self.price.value:
                raise ValueError("a written price holds at least one amount")
            if any(amount <= 0 for amount in self.price.value):
                raise ValueError("prices are greater than 0")
        rooms = self.rooms.value
        if rooms is not None and (rooms <= 0 or (rooms * 2) != int(rooms * 2)):
            raise ValueError("rooms is a positive multiple of 0.5")
        return self
