"""The model's answer completed into a `Listing` (`PHASE_2.md` 2.4, step 3). Pure: no call, no
storage. The rules: DECISIONS.md #95, #105, #114, #115, #162, #167, #178, #179, #180.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from tlv_hunter.contracts.listing import (
    AREA_NUMBERS,
    LISTING_SCHEMA_VERSION,
    Listing,
    Marked,
    PhoneName,
)
from tlv_hunter.contracts.listing_extraction import EntryDateParts, ListingExtraction, PhoneNamePair
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.parsing.datetimes import nearest_occurrence
from tlv_hunter.parsing.prices import native_price_fallback
from tlv_hunter.textnorm.phones import canonical_phone

# The fields with the same name and type in the answer and in `Listing` (#137).
_COPIED = (
    "post_nature",
    "apartment_kind",
    "entry_date_written",
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
    "gender",
)


_EntryDate = Marked[Literal["immediate"] | date]
_Price = Marked[list[int]]


class AnswerError(ValueError):
    """The answer passed the schema but breaks a rule code checks (an area outside 1-71)."""


@dataclass(frozen=True)
class Provenance:
    model_name: str
    prompt_version: str
    classified_at: datetime


@dataclass(frozen=True)
class Completed:
    listing: Listing
    dropped_streets: tuple[str, ...]
    dropped_area_names: tuple[str, ...]
    dropped_other_city: str | None
    """Names the model returned that the post's text does not contain (#162, #180)."""


def complete(extraction: ListingExtraction, post: RawPost, provenance: Provenance) -> Completed:
    if post.phones is None:
        raise ValueError("phones is None: textnorm must run before classification")
    if any(number not in AREA_NUMBERS for number in extraction.areas):
        raise AnswerError("areas are municipal numbers 1-71")
    price, price_source = _price(extraction, post)
    streets, dropped_streets = _in_text(extraction.streets, post.text)
    area_names, dropped_area_names = _in_text(extraction.stated_area_names, post.text)
    other_city, dropped_other_city = _other_city(extraction.other_city, post.text)
    listing = Listing(
        schema_version=LISTING_SCHEMA_VERSION,
        listing_id=post.listing_id,
        model_name=provenance.model_name,
        prompt_version=provenance.prompt_version,
        classified_at=provenance.classified_at,
        **{field: getattr(extraction, field) for field in _COPIED},
        price=price,
        price_source=price_source,
        entry_date=_entry_date(extraction.entry_date_parts, post.posted_at.date()),
        streets=streets,
        stated_area_names=area_names,
        areas=sorted(set(extraction.areas)),
        other_city=other_city,
        phone_names=_phone_names(extraction.phone_name_pairs, post.phones),
    )
    return Completed(
        listing=listing,
        dropped_streets=tuple(dropped_streets),
        dropped_area_names=tuple(dropped_area_names),
        dropped_other_city=dropped_other_city,
    )


def _price(extraction: ListingExtraction, post: RawPost) -> tuple[_Price, str | None]:
    """The text wins; an unclear text price stays unclear; native only when the text has none."""
    if extraction.price.state != "not_written":
        return extraction.price, "text"
    native = native_price_fallback(post.native_price)
    if native is None:
        return extraction.price, None
    return _Price(state="written", value=[native]), "native"


def _entry_date(parts: Marked[EntryDateParts], published: date) -> _EntryDate:
    if parts.state != "written" or parts.value is None:
        return _EntryDate(state=parts.state, value=None)
    value = parts.value
    if value.immediate:
        return _EntryDate(state="written", value="immediate")
    assert value.day is not None and value.month is not None  # EntryDateParts requires both
    if value.year is None:
        found = nearest_occurrence(value.day, value.month, published)
    else:
        # A two-digit year is 20YY (#178): the instructions say so, and code holds to it too.
        year = value.year + 2000 if 0 <= value.year < 100 else value.year
        try:
            found = date(year, value.month, value.day)
        except ValueError:
            found = None
    if found is None:
        # An impossible date (31.11, 29.2 of a written non-leap year) is unclear (#179).
        return _EntryDate(state="unclear", value=None)
    return _EntryDate(state="written", value=found)


def _in_text(names: list[str], text: str) -> tuple[list[str], list[str]]:
    """Kept: a name that, stripped of surrounding whitespace, occurs in the text exactly. No
    normalization (invariant 8): a name in a different case is dropped (#162, #179)."""
    kept: list[str] = []
    dropped: list[str] = []
    for name in names:
        stripped = name.strip()
        if not stripped:
            continue
        (kept if stripped in text else dropped).append(stripped)
    return kept, dropped


def _other_city(city: str | None, text: str) -> tuple[str | None, str | None]:
    """A blank city reads as None (#179); a city not in the text is dropped and counted (#180)."""
    if city is None or not city.strip():
        return None, None
    stripped = city.strip()
    if stripped in text:
        return stripped, None
    return None, stripped


def _phone_names(pairs: list[PhoneNamePair], phones: list[str]) -> list[PhoneName]:
    """Kept when the number equals one already extracted (#105); a repeat once, a blank name
    dropped (#179)."""
    kept: list[PhoneName] = []
    for pair in pairs:
        if not pair.name.strip():
            continue
        phone = canonical_phone(pair.phone)
        if phone not in phones:
            continue
        candidate = PhoneName(phone=phone, name=pair.name)
        if candidate not in kept:
            kept.append(candidate)
    return kept
