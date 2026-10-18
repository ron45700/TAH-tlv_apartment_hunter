"""Gate F: the one-time code that links a Telegram chat to a user (SCHEMA.md, Gate F; DECISIONS.md
#453; `PHASE_4.md` point 5 A).

The site shows the code once, in a deep link (`https://t.me/<bot>?start=<code>`); the store keeps
only its SHA-256, as for keys and sessions (`accounts/tokens.py`). Single use, valid for 15 minutes
from `created_at`. Keyed by `code_hash`.
"""

from datetime import datetime, timedelta
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id, require_sha256_hex
from tlv_hunter.parsing.datetimes import require_utc

TELEGRAM_LINK_CODE_SCHEMA_VERSION = 1
LINK_CODE_LIFETIME = timedelta(minutes=15)


class TelegramLinkCode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    code_hash: str
    user_id: str
    created_at: datetime
    used_at: datetime | None

    @field_validator("code_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        return require_sha256_hex(value)

    @field_validator("user_id")
    @classmethod
    def _opaque(cls, value: str) -> str:
        require_opaque_id(value)
        return value

    @field_validator("created_at", "used_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != TELEGRAM_LINK_CODE_SCHEMA_VERSION:
            raise ValueError(f"unknown TelegramLinkCode schema_version {self.schema_version!r}")
        if self.used_at is not None and self.used_at < self.created_at:
            raise ValueError("a code is used after it was created")
        return self

    def usable(self, now: datetime) -> bool:
        """Unused and less than 15 minutes old."""
        return self.used_at is None and now < self.created_at + LINK_CODE_LIFETIME
