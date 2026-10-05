"""The model's response (`SCHEMA.md`, `ListingExtraction`; DECISIONS.md #137, #151, #167).

Not stored: code turns it into a `Listing` (`classify/complete.py`). Its JSON schema is derived from
this model at runtime (#22) and sent in strict mode, so every field is required.
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from tlv_hunter.contracts.listing import Marked


class EntryDateParts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    immediate: bool
    day: int | None
    month: int | None
    year: int | None

    @model_validator(mode="after")
    def _parts(self) -> Self:
        if self.immediate:
            if (self.day, self.month, self.year) != (None, None, None):
                raise ValueError("an immediate entry has no day, month or year")
            return self
        if self.day is None or self.month is None:
            raise ValueError("day and month are required when the entry is not immediate")
        if not 1 <= self.day <= 31:
            raise ValueError("day is 1-31")
        if not 1 <= self.month <= 12:
            raise ValueError("month is 1-12")
        return self


class PhoneNamePair(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    phone: str
    name: str


class ListingExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    post_nature: Literal["rental_offer", "sublet_offer", "seeking", "for_sale", "not_listing"]
    apartment_kind: Marked[Literal["room", "whole_apartment"]]
    price: Marked[list[int]]
    entry_date_written: str | None
    entry_date_parts: Marked[EntryDateParts]
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
    phone_name_pairs: list[PhoneNamePair]
