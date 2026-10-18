"""Gate C: a user's account (SCHEMA.md, Gate C; DECISIONS.md #242, #244, #262–#265, #288), with
Gate F's two Telegram fields (SCHEMA.md, Gate F; DECISIONS.md #453, version 2).

Also the two id forms every Gate C record checks: the opaque ids (32 hex characters, #262, #288)
and the SHA-256 hashes of keys and session tokens (64 hex characters).
"""

import json
import re
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.parsing.datetimes import require_utc

USER_SCHEMA_VERSION = 2
# Version 2 adds the link to Telegram (Gate F, #453), both None on a version-1 record.
_ADDED_IN_VERSION_2 = {"telegram_chat_id": None, "telegram_linked_at": None}
OPAQUE_ID = re.compile(r"[0-9a-f]{32}")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
# Latin letters, digits, "_", "." and "-" only, 3 to 32 characters (#262).
USERNAME = re.compile(r"[A-Za-z0-9_.-]{3,32}")


def require_opaque_id(value: str | None) -> str | None:
    if value is not None and not OPAQUE_ID.fullmatch(value):
        raise ValueError("must be an opaque id: 32 lower-case hex characters")
    return value


def require_sha256_hex(value: str) -> str:
    if not SHA256_HEX.fullmatch(value):
        raise ValueError("must be a SHA-256 hash: 64 lower-case hex characters")
    return value


class User(BaseModel):
    """One account. Never deleted, only disabled (#265)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    user_id: str
    username: str
    password_hash: str
    is_admin: bool
    created_at: datetime
    signup_key_id: str | None
    must_change_password: bool
    password_changed_at: datetime
    disabled_at: datetime | None
    failed_sign_ins: int
    last_failed_sign_in_at: datetime | None
    telegram_chat_id: int | None
    """The linked Telegram chat (Gate F, #453): one chat per user and one user per chat."""
    telegram_linked_at: datetime | None
    """When it was linked: alerts come only for posts first stored after it (#452, point 10)."""

    @classmethod
    def from_stored_json(cls, doc: str) -> "User":
        """Read a stored user. A version-1 one reads as version 2 with no link (#453). Read-time
        only, as `Profile.from_stored_json` does: it is written as version 2 the next time it is
        saved, and nothing is rewritten in bulk. `UserDataStore` reads users only through here."""
        data = json.loads(doc)
        if isinstance(data, dict) and data.get("schema_version") == 1:
            if _ADDED_IN_VERSION_2.keys() & data.keys():
                raise ValueError("a version-1 user cannot carry version-2 fields")
            doc = json.dumps({**data, **_ADDED_IN_VERSION_2, "schema_version": USER_SCHEMA_VERSION})
        return cls.model_validate_json(doc)

    @field_validator("user_id", "signup_key_id")
    @classmethod
    def _opaque(cls, value: str | None) -> str | None:
        return require_opaque_id(value)

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        if not USERNAME.fullmatch(value):
            raise ValueError("a username is 3 to 32 Latin letters, digits, '_', '.' or '-'")
        return value

    @field_validator(
        "created_at",
        "password_changed_at",
        "disabled_at",
        "last_failed_sign_in_at",
        "telegram_linked_at",
    )
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != USER_SCHEMA_VERSION:
            raise ValueError(f"unknown User schema_version {self.schema_version!r}")
        if not self.password_hash:
            raise ValueError("password_hash is required")
        if (self.signup_key_id is None) != self.is_admin:
            raise ValueError("signup_key_id is None exactly for the admin (#244)")
        if self.is_admin and self.disabled_at is not None:
            raise ValueError("the admin cannot be disabled (R8)")
        if self.failed_sign_ins < 0:
            raise ValueError("failed_sign_ins cannot be negative")
        if (self.failed_sign_ins == 0) != (self.last_failed_sign_in_at is None):
            raise ValueError("last_failed_sign_in_at is None exactly when failed_sign_ins is 0")
        if (self.telegram_chat_id is None) != (self.telegram_linked_at is None):
            raise ValueError("telegram_chat_id and telegram_linked_at are set together, or neither")
        return self

    @property
    def username_key(self) -> str:
        """The username as compared: case-insensitively (#262)."""
        return self.username.lower()
