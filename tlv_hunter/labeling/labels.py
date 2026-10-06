"""`labels.json`, the labelling page's export (`PHASE_2.md` 2.6; DECISIONS.md #142, #143, #171,
#177, #183): Ron's blind labels of the deciding fields, per `listing_id`.

Ron moves the file into `data/labeling/` and the code reads it only from there. The field names are
`SCHEMA.md`'s; the entry date is labelled as `entry_date_parts` (`ListingExtraction`), since a
label holds the year only when the post writes it. A field Ron has not labelled yet is `null`.
`other_city` is always labelled: empty means Tel Aviv-Yafo. Streets and area names are not labelled
(#177). A plain module: it reads, and writes nothing.
"""

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.listing import AREA_NUMBERS, Marked
from tlv_hunter.contracts.listing_extraction import EntryDateParts
from tlv_hunter.labeling.regression_set import text_sha256
from tlv_hunter.parsing.datetimes import require_utc

LABELS_FILE = "labels.json"
LABELS_FORMAT_VERSION = 1


class PostLabel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text_sha256: str
    post_nature: (
        Literal["rental_offer", "sublet_offer", "seeking", "for_sale", "not_listing"] | None
    )
    apartment_kind: Marked[Literal["room", "whole_apartment"]] | None
    price: Marked[list[int]] | None
    gender: Literal["no_restriction", "women_preferred", "women_only"] | None
    entry_date_parts: Marked[EntryDateParts] | None
    areas: list[int] | None
    other_city: str | None
    ambiguous: bool
    note: str

    @field_validator("areas")
    @classmethod
    def _areas(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        if any(number not in AREA_NUMBERS for number in value):
            raise ValueError("areas are municipal numbers 1-71")
        if value != sorted(set(value)):
            raise ValueError("areas are sorted with no repeats")
        return value

    @field_validator("other_city")
    @classmethod
    def _other_city(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("other_city is null for Tel Aviv-Yafo, never blank")
        return value

    @model_validator(mode="after")
    def _price(self) -> Self:
        amounts = None if self.price is None else self.price.value
        if amounts is not None and (not amounts or any(amount <= 0 for amount in amounts)):
            raise ValueError("a written price holds at least one amount, each above 0")
        return self

    @property
    def is_complete(self) -> bool:
        """Every deciding field labelled, or the post marked ambiguous (not counted, #142)."""
        if self.ambiguous:
            return True
        return None not in (
            self.post_nature,
            self.apartment_kind,
            self.price,
            self.gender,
            self.entry_date_parts,
            self.areas,
        )


class LabelFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1]
    exported_at: datetime
    labels: dict[str, PostLabel]

    @field_validator("exported_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    def incomplete(self) -> list[str]:
        return sorted(
            listing_id for listing_id, label in self.labels.items() if not label.is_complete
        )

    def stale(self, texts: Mapping[str, str]) -> list[str]:
        """The labelled posts whose text, by `listing_id`, is unknown or not the text labelled."""
        return sorted(
            listing_id
            for listing_id, label in self.labels.items()
            if listing_id not in texts or text_sha256(texts[listing_id]) != label.text_sha256
        )


def read_labels(path: Path) -> LabelFile:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"{path}: no labels. Export them from label_posts.html and move the file here"
        )
    return LabelFile.model_validate_json(path.read_text(encoding="utf-8"))
