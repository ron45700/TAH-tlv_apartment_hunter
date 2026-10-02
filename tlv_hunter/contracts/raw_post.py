from datetime import datetime, timedelta
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.textnorm.blank import is_blank

RAW_POST_SCHEMA_VERSION = 1


class Media(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    type: str
    uri: str
    width: int | None
    height: int | None
    media_id: str
    page_url: str


class RawPost(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    source: Literal["thedoor", "memo23"]
    source_post_id: str
    listing_id: str
    group_id: str
    group_title: str | None
    permalink: str
    posted_at: datetime
    fetched_at: datetime
    raw: dict[str, Any]

    text: str
    text_source: Literal["text", "shared_post", "none"]
    post_type: str

    media: list[Media]

    native_price: int | None
    native_price_raw: str | None
    native_currency: str | None
    native_title: str | None
    native_location: str | None

    author_name: str | None
    author_id_raw: str | None
    author_profile_url: str | None

    top_comment: dict[str, Any] | None
    reactions_count: int | None
    comments_count: int | None
    shares_count: int | None

    text_hash: str | None = None
    phones: list[str] | None = None
    no_text: bool | None = None
    is_canonical: bool | None = None
    duplicate_of: str | None = None

    @field_validator("posted_at", "fetched_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("must be a tz-aware UTC datetime")
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.listing_id != compute_listing_id(self.source_post_id):
            raise ValueError("listing_id does not match source_post_id")
        blank = is_blank(self.text)
        if self.text_source == "text" and blank:
            raise ValueError("text_source is 'text' but text is blank")
        if self.text_source == "none" and not blank:
            raise ValueError("text_source is 'none' but text is not blank")
        if self.no_text is None:
            if self.text_hash is not None or self.phones is not None:
                raise ValueError("text_hash and phones must be None until textnorm has run")
        else:
            if self.no_text != blank:
                raise ValueError("no_text disagrees with the text")
            if self.no_text and self.text_hash is not None:
                raise ValueError("text_hash must be None when no_text is True")
            if not self.no_text and self.text_hash is None:
                raise ValueError("text_hash is required when no_text is False")
        return self

    def with_changes(self, **changes: Any) -> Self:
        return type(self)(**{**dict(self), **changes})
