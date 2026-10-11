"""Gate C: the one-time key the admin issues (SCHEMA.md, Gate C; DECISIONS.md #47, #243, #266)."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id, require_sha256_hex
from tlv_hunter.parsing.datetimes import require_utc

SIGNUP_KEY_SCHEMA_VERSION = 1


class SignupKey(BaseModel):
    """A key holds only the hash of the key itself, which is shown once (#266). Never deleted; no
    expiry (#243)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    key_id: str
    key_hash: str
    label: str
    created_at: datetime
    used_by: str | None
    used_at: datetime | None
    cancelled_at: datetime | None

    @field_validator("key_id", "used_by")
    @classmethod
    def _opaque(cls, value: str | None) -> str | None:
        return require_opaque_id(value)

    @field_validator("key_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        return require_sha256_hex(value)

    @field_validator("created_at", "used_at", "cancelled_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != SIGNUP_KEY_SCHEMA_VERSION:
            raise ValueError(f"unknown SignupKey schema_version {self.schema_version!r}")
        if not self.label.strip():
            raise ValueError("a key has a label (#243)")
        if (self.used_by is None) != (self.used_at is None):
            raise ValueError("used_by and used_at are set together or both None")
        if self.cancelled_at is not None and self.used_by is not None:
            raise ValueError("only an unused key can be cancelled (#243)")
        return self

    @property
    def usable(self) -> bool:
        return self.used_by is None and self.cancelled_at is None
