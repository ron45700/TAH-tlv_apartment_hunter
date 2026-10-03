from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from tlv_hunter.parsing.datetimes import require_utc

GROUP_WATERMARK_SCHEMA_VERSION = 1


class GroupWatermark(BaseModel):
    """Gate E per-group watermark record. When it advances is task 1.13, not this record."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    group_id: str
    watermark: datetime | None
    last_success_at: datetime | None
    consecutive_failures: int

    @field_validator("watermark", "last_success_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)
