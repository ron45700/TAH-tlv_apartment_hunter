"""Gate C: a signed-in browser (SCHEMA.md, Gate C; DECISIONS.md #263, #288 R3, R5–R7, R9)."""

from datetime import datetime, timedelta
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id, require_sha256_hex
from tlv_hunter.parsing.datetimes import require_utc

SESSION_SCHEMA_VERSION = 1
# 30 days from sign-in, not extended by use (#263, R5).
SESSION_LIFETIME = timedelta(days=30)


class Session(BaseModel):
    """Keyed by the hash of the session token; the token itself is only in the user's cookie."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    token_hash: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ended_at: datetime | None

    @field_validator("token_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        return require_sha256_hex(value)

    @field_validator("user_id")
    @classmethod
    def _opaque(cls, value: str) -> str:
        require_opaque_id(value)
        return value

    @field_validator("created_at", "expires_at", "ended_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != SESSION_SCHEMA_VERSION:
            raise ValueError(f"unknown Session schema_version {self.schema_version!r}")
        if self.expires_at != self.created_at + SESSION_LIFETIME:
            raise ValueError("a session expires 30 days after it was created (#263)")
        return self
