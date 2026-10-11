"""Gate C: the admin's hand correction of one field of one post (SCHEMA.md, Gate C; DECISIONS.md
#173, #255, #256, #284, #288).

`model_value` and `corrected_value` hold the field's Gate B type. That type is read from
`Listing`'s own field definition, so Gate B's types are written in one place only (#284). The
`Listing` itself is never edited. Never deleted (#255).
"""

import json
from datetime import datetime
from functools import cache
from typing import Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    TypeAdapter,
    ValidationInfo,
    field_validator,
    model_validator,
)

from tlv_hunter.contracts.classification_report import ReportableField
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.user import require_opaque_id
from tlv_hunter.parsing.datetimes import require_utc

FIELD_CORRECTION_SCHEMA_VERSION = 1


@cache
def listing_field_type(field: str) -> TypeAdapter[Any]:
    """The Gate B type of a `Listing` field."""
    return TypeAdapter(Listing.model_fields[field].annotation)


def _typed(field: str, value: Any) -> Any:
    adapter = listing_field_type(field)
    try:
        text = json.dumps(value)
    except TypeError:
        return adapter.validate_python(value)  # already typed: a model, a date
    return adapter.validate_json(text)  # as read from a stored document


class FieldCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    correction_id: str
    listing_id: str
    field: ReportableField
    model_value: Any
    corrected_value: Any
    corrected_by: str
    corrected_at: datetime
    report_id: str | None
    removed_by: str | None
    removed_at: datetime | None

    @field_validator("model_value", "corrected_value")
    @classmethod
    def _of_the_field_type(cls, value: Any, info: ValidationInfo) -> Any:
        field = info.data.get("field")
        if field is None:
            raise ValueError("the field is not a reportable field")
        return _typed(field, value)

    @field_validator("correction_id", "corrected_by", "report_id", "removed_by")
    @classmethod
    def _opaque(cls, value: str | None) -> str | None:
        return require_opaque_id(value)

    @field_validator("corrected_at", "removed_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != FIELD_CORRECTION_SCHEMA_VERSION:
            raise ValueError(f"unknown FieldCorrection schema_version {self.schema_version!r}")
        if (self.removed_by is None) != (self.removed_at is None):
            raise ValueError("removed_by and removed_at are set together or both None")
        return self

    @property
    def in_force(self) -> bool:
        return self.removed_at is None
