"""Gate C: a post a user has viewed (SCHEMA.md, Gate C; DECISIONS.md #62, #253, #276).

Per user, never on the post (invariant 12). Key: (`user_id`, `listing_id`).
"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id
from tlv_hunter.parsing.datetimes import require_utc

VIEWED_POST_SCHEMA_VERSION = 1


class ViewedPost(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    user_id: str
    listing_id: str
    viewed_at: datetime

    @field_validator("user_id")
    @classmethod
    def _opaque(cls, value: str) -> str:
        require_opaque_id(value)
        return value

    @field_validator("viewed_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _check_version(self) -> Self:
        if self.schema_version != VIEWED_POST_SCHEMA_VERSION:
            raise ValueError(f"unknown ViewedPost schema_version {self.schema_version!r}")
        return self
