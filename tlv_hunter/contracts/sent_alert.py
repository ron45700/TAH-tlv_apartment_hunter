"""Gate F: an alert sent to a user (SCHEMA.md, Gate F; DECISIONS.md #453; `PHASE_4.md` point 4 A).

One per user and post: "nothing alerted twice" means "no record yet". Per user, never on the post
(invariant 12). Key: (`user_id`, `listing_id`); the post is the card's shown post. Deleted with its
post (as `ViewedPost`, #62), by Phase 5's retention job.
"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id
from tlv_hunter.parsing.datetimes import require_utc

SENT_ALERT_SCHEMA_VERSION = 1


class SentAlert(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    user_id: str
    listing_id: str
    sent_at: datetime

    @field_validator("user_id")
    @classmethod
    def _opaque(cls, value: str) -> str:
        require_opaque_id(value)
        return value

    @field_validator("sent_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _check_version(self) -> Self:
        if self.schema_version != SENT_ALERT_SCHEMA_VERSION:
            raise ValueError(f"unknown SentAlert schema_version {self.schema_version!r}")
        return self
