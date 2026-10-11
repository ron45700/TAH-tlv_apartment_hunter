"""Gate C: a user's "wrong classification" report (SCHEMA.md, Gate C; DECISIONS.md #173, #254,
#255, #277, #278, #286, #288).

Never deleted, also after its post is (#255).
"""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id
from tlv_hunter.parsing.datetimes import require_utc

CLASSIFICATION_REPORT_SCHEMA_VERSION = 1
NOTE_LIMIT = 500  # characters (#277)

# The card's fields by their Gate B names (#277); also the fields an admin can correct (#284).
ReportableField = Literal[
    "post_nature",
    "apartment_kind",
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
    "gender",
    "areas",
    "streets",
    "other_city",
    "phone_names",
]


class ClassificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    report_id: str
    listing_id: str
    reported_by: str
    reported_at: datetime
    fields: list[ReportableField]
    note: str | None
    status: Literal["open", "restored", "left_out"]
    resolved_by: str | None
    resolved_at: datetime | None

    @field_validator("report_id", "reported_by", "resolved_by")
    @classmethod
    def _opaque(cls, value: str | None) -> str | None:
        return require_opaque_id(value)

    @field_validator("reported_at", "resolved_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != CLASSIFICATION_REPORT_SCHEMA_VERSION:
            raise ValueError(f"unknown ClassificationReport schema_version {self.schema_version!r}")
        if not self.fields or len(set(self.fields)) != len(self.fields):
            raise ValueError("a report names one or more fields, with no repeats (#254)")
        if self.note is not None and len(self.note) > NOTE_LIMIT:
            raise ValueError(f"the note is at most {NOTE_LIMIT} characters (#277)")
        if (self.resolved_by is None) != (self.resolved_at is None):
            raise ValueError("resolved_by and resolved_at are set together or both None")
        if (self.status == "open") != (self.resolved_by is None):
            raise ValueError("resolved_by and resolved_at are set exactly when status is not open")
        return self
