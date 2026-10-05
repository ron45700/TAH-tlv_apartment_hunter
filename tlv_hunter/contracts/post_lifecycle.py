import json
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.parsing.datetimes import require_utc

POST_LIFECYCLE_SCHEMA_VERSION = 2
_ADDED_IN_VERSION_2 = {"classification_failures": 0, "last_classification_error": None}


class PostImage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    listing_id: str
    media_id: str
    local_path: str | None
    error: str | None

    @model_validator(mode="after")
    def _exactly_one_outcome(self) -> Self:
        if (self.local_path is None) == (self.error is None):
            raise ValueError("exactly one of local_path and error must be set")
        return self


class PostLifecycle(BaseModel):
    """Gate E post lifecycle record: one per post, keyed by listing_id, separate from RawPost."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    listing_id: str
    state: Literal["pending", "active", "rejected", "archived"]
    rejection_reason: (
        Literal[
            "no_text",
            "no_images",
            "other_city",
            "seeking",
            "for_sale",
            "not_listing",
            "flagged",
        ]
        | None
    )
    flagged_by: str | None
    flagged_at: datetime | None
    flag_note: str | None
    last_published_at: datetime
    images: list[PostImage]
    classification_failures: int
    last_classification_error: str | None

    @classmethod
    def from_stored_json(cls, doc: str) -> "PostLifecycle":
        """Read a stored document. A version-1 one reads as version 2 with 0 and None
        (DECISIONS.md #152); it is written back as version 2 the next time it is saved, and
        nothing is rewritten in bulk. Both stores read lifecycle records only through here."""
        data = json.loads(doc)
        if isinstance(data, dict) and data.get("schema_version") == 1:
            if _ADDED_IN_VERSION_2.keys() & data.keys():
                raise ValueError("a version-1 record cannot carry version-2 fields")
            data = {**data, **_ADDED_IN_VERSION_2, "schema_version": POST_LIFECYCLE_SCHEMA_VERSION}
            doc = json.dumps(data)
        return cls.model_validate_json(doc)

    @field_validator("flagged_at", "last_published_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.state in ("pending", "active") and self.rejection_reason is not None:
            raise ValueError(f"rejection_reason must be None when state is {self.state!r}")
        if self.state == "rejected" and self.rejection_reason is None:
            raise ValueError("rejection_reason is required when state is 'rejected'")
        if (self.flagged_by is None) != (self.flagged_at is None):
            raise ValueError("flagged_by and flagged_at are set together or both None")
        if self.rejection_reason == "flagged" and self.flagged_by is None:
            raise ValueError("rejection_reason 'flagged' requires flagged_by and flagged_at")
        if self.schema_version != POST_LIFECYCLE_SCHEMA_VERSION:
            raise ValueError(f"unknown PostLifecycle schema_version {self.schema_version!r}")
        if self.classification_failures < 0:
            raise ValueError("classification_failures cannot be negative")
        return self
