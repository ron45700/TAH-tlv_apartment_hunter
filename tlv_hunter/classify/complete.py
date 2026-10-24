"""The model's answer completed into a `Listing` (`PHASE_2.md` 2.4, step 3). Pure: no call, no
storage. The rules: DECISIONS.md #95, #105, #114, #115, #162 (for streets as amended by #486), #167,
#178, #179, #180.

A Yad2 listing (#495, #502, #517): Yad2's form wins wherever it gives a value (`yad2.mapping.
form_fields`); the form's street and neighbourhood lead `streets` and `stated_area_names`, exempt
from #162, the model's own names from the description after them (a model name equal to the form's
is merged, not counted as dropped); `field_sources` names the source of every field.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from tlv_hunter.contracts.listing import (
    AREA_NUMBERS,
    LISTING_SCHEMA_VERSION,
    SOURCED_FIELDS,
    Listing,
    Marked,
    PhoneName,
)
from tlv_hunter.contracts.listing_extraction import EntryDateParts, ListingExtraction, PhoneNamePair
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.parsing.datetimes import nearest_occurrence
from tlv_hunter.parsing.ids import YAD2_SOURCE
from tlv_hunter.parsing.prices import native_price_fallback
from tlv_hunter.textnorm.phones import canonical_phone
from tlv_hunter.yad2.mapping import form_fields

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
    form = form_fields(post.raw) if post.source == YAD2_SOURCE else {}
    form_streets = form.get("streets", [])
    form_area_names = form.get("stated_area_names", [])
    price, price_source = price_with_fallback(extraction.price, post.native_price)
    streets, dropped_streets = _streets_in_text(
        [name for name in extraction.streets if name.strip() not in form_streets], post.text
    )
    area_names, dropped_area_names = _in_text(
        [name for name in extraction.stated_area_names if name.strip() not in form_area_names],
        post.text,
    )
    other_city, dropped_other_city = _other_city(extraction.other_city, post.text)
    values: dict[str, Any] = {
        **{field: getattr(extraction, field) for field in _COPIED},
        "price": price,
        "price_source": price_source,
        "entry_date": entry_date_from_parts(extraction.entry_date_parts, post.posted_at.date()),
        "streets": streets,
        "stated_area_names": area_names,
        "areas": sorted(set(extraction.areas)),
        "other_city": other_city,
        "phone_names": _phone_names(extraction.phone_name_pairs, post.phones),
    }
    field_sources: dict[str, str] = {}
    if post.source == YAD2_SOURCE:
        values.update(form)
        values["streets"] = [*form_streets, *(name for name in streets if name not in form_streets)]
        values["stated_area_names"] = [
            *form_area_names,
            *(name for name in area_names if name not in form_area_names),
        ]
        field_sources = {name: "form" if name in form else "model" for name in SOURCED_FIELDS}
    listing = Listing(
        schema_version=LISTING_SCHEMA_VERSION,
        listing_id=post.listing_id,
        model_name=provenance.model_name,
        prompt_version=provenance.prompt_version,
        classified_at=provenance.classified_at,
        **values,
        field_sources=field_sources,
    )
    return Completed(
        listing=listing,
        dropped_streets=tuple(dropped_streets),
        dropped_area_names=tuple(dropped_area_names),
        dropped_other_city=dropped_other_city,
    )


def price_with_fallback(
    price: _Price, native_price: int | None
) -> tuple[_Price, Literal["text", "native"] | None]:
    """The text wins; an unclear text price stays unclear; native only when the text has none.
    Also applied to Ron's labels by the regression runner, which labels the text only (#187)."""
    if price.state != "not_written":
        return price, "text"
    native = native_price_fallback(native_price)
    if native is None:
        return price, None
    return _Price(state="written", value=[native]), "native"


def entry_date_from_parts(parts: Marked[EntryDateParts], published: date) -> _EntryDate:
    """The comparable entry date (#96, #115, #178, #179). Also applied to Ron's labels by the
    regression runner, which labels the parts (#187)."""
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


# A house number at a street's end (version 6, #484): digits, then at most one Hebrew letter
# ("12א").
_HOUSE_NUMBER = re.compile(r"(?P<name>.*\S)\s+(?P<number>\d+)[א-ת]?")


def _streets_in_text(streets: list[str], text: str) -> tuple[list[str], list[str]]:
    """#162 for streets, as amended by #486. A street that occurs in the text exactly is kept. One
    that ends in a house number is kept whole when its name occurs in the text exactly and the
    number occurs in it as a number, anywhere ("בן יהודה, מספר 83" keeps "בן יהודה 83");
    its name alone when the number does not. A street whose name the text does not contain is
    dropped and returned."""
    kept: list[str] = []
    dropped: list[str] = []
    for street in streets:
        stripped = street.strip()
        if not stripped:
            continue
        if stripped in text:
            kept.append(stripped)
            continue
        numbered = _HOUSE_NUMBER.fullmatch(stripped)
        if numbered is None or numbered["name"] not in text:
            dropped.append(stripped)
        elif re.search(rf"(?<!\d){numbered['number']}(?!\d)", text):
            kept.append(stripped)
        else:
            kept.append(numbered["name"])
    return kept, dropped


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
