import copy
from datetime import datetime
from typing import Any

from tlv_hunter.contracts.raw_post import RAW_POST_SCHEMA_VERSION, Media, RawPost
from tlv_hunter.parsing.datetimes import parse_rfc2822_utc
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.parsing.prices import UNPARSED_PRICE, parse_native_price
from tlv_hunter.textnorm.blank import is_blank

SOURCE = "thedoor"


class UnverifiedSharedPostError(NotImplementedError):
    """The sharedPost content shape is unverified; refuse the post rather than guess at it."""


def to_raw_post(item: dict[str, Any], fetched_at: datetime) -> RawPost:
    text = item["text"]
    if item["post_type"] == "shared" or (is_blank(text) and item["sharedPost"] is not None):
        raise UnverifiedSharedPostError(
            f"post {item['post_id']}: shared-post content shape is not verified yet"
        )

    sale_post = item["sale_post"]
    if sale_post is None:
        price_raw = title = location = None
        price = UNPARSED_PRICE
    else:
        price_raw = sale_post["price"]
        price = parse_native_price(price_raw)
        title = sale_post["title"]
        location = sale_post["location"]

    user = item["user"]
    return RawPost(
        schema_version=RAW_POST_SCHEMA_VERSION,
        source=SOURCE,
        source_post_id=item["post_id"],
        listing_id=compute_listing_id(item["post_id"]),
        group_id=item["group_id"],
        group_title=None,
        permalink=item["post_url"],
        posted_at=parse_rfc2822_utc(item["creation_time"]),
        fetched_at=fetched_at,
        raw=copy.deepcopy(item),
        text=text,
        text_source="none" if is_blank(text) else "text",
        post_type=item["post_type"],
        media=[_to_media(entry) for entry in item["media"]],
        native_price=price.amount,
        native_price_raw=price_raw,
        native_currency=price.currency,
        native_title=title,
        native_location=location,
        author_name=user["name"],
        author_id_raw=user["id"],
        author_profile_url=user["profileUrl"],
        top_comment=copy.deepcopy(item["topComment"]),
        reactions_count=item["reactions_count"],
        comments_count=item["comments_count"],
        shares_count=item["shares_count"],
    )


def _to_media(entry: dict[str, Any]) -> Media:
    return Media(
        type=entry["type"],
        uri=entry["uri"],
        # Video items omit width/height entirely; Photo items carry both.
        width=entry.get("width"),
        height=entry.get("height"),
        media_id=entry["id"],
        page_url=entry["url"],
    )
