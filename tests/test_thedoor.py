import copy
from collections import Counter

import pytest

from tests.conftest import FETCHED_AT
from tlv_hunter.parsing.datetimes import parse_rfc2822_utc
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.providers.thedoor import UnverifiedSharedPostError, to_raw_post
from tlv_hunter.textnorm.annotate import annotate

NATIVE_FIELDS = (
    "native_price",
    "native_price_raw",
    "native_currency",
    "native_title",
    "native_location",
)
DERIVED_FIELDS = ("text_hash", "phones", "no_text", "is_canonical", "duplicate_of")


@pytest.fixture
def mapped(thedoor_items):
    return [(item, to_raw_post(item, FETCHED_AT)) for item in thedoor_items]


def test_all_20_map_and_raw_is_kept_whole(mapped) -> None:
    assert len(mapped) == 20
    for item, post in mapped:
        assert post.raw == item


def test_raw_is_a_copy_not_a_reference(thedoor_items) -> None:
    item = thedoor_items[0]
    post = to_raw_post(item, FETCHED_AT)
    item["text"] = "mutated after mapping"
    item["media"].clear()
    assert post.raw["text"] != "mutated after mapping"
    assert post.raw["media"]


def test_identity_and_provenance_fields(mapped) -> None:
    for item, post in mapped:
        assert post.schema_version == 1
        assert post.source == "thedoor"
        assert post.source_post_id == item["post_id"]
        assert post.listing_id == compute_listing_id(item["post_id"])
        assert post.group_id == item["group_id"]
        assert post.group_title is None
        assert post.permalink == item["post_url"]
        assert post.posted_at == parse_rfc2822_utc(item["creation_time"])
        assert post.fetched_at == FETCHED_AT


def test_content_fields(mapped) -> None:
    for item, post in mapped:
        assert post.text == item["text"]
        assert post.text_source == "text"
        assert post.post_type == item["post_type"]
    assert Counter(post.post_type for _, post in mapped) == {"regular": 12, "sale_post": 8}


def test_sale_post_native_fields(mapped) -> None:
    by_id = {post.source_post_id: post for _, post in mapped}
    room_only = by_id["2178444986052358"]
    assert room_only.native_price == 3560
    assert room_only.native_price_raw == "₪3,560"
    assert room_only.native_currency == "ILS"
    assert room_only.native_title == "1 bed · 2 bath · Room Only"
    assert room_only.native_location == "תל אביב - יפו, תל אביב"
    assert chr(0x200E) in by_id["2178554076041449"].native_title
    sale_posts = [post for _, post in mapped if post.post_type == "sale_post"]
    assert len(sale_posts) == 8
    assert all(
        post.native_price is not None and post.native_currency == "ILS" for post in sale_posts
    )


def test_regular_posts_have_no_native_fields(mapped) -> None:
    regular = [post for _, post in mapped if post.post_type == "regular"]
    assert len(regular) == 12
    for post in regular:
        assert all(getattr(post, name) is None for name in NATIVE_FIELDS)


def test_media(mapped) -> None:
    assert sum(len(post.media) for _, post in mapped) == 82
    for item, post in mapped:
        assert len(post.media) == len(item["media"])
        for entry, media in zip(item["media"], post.media, strict=True):
            assert (media.type, media.uri) == (entry["type"], entry["uri"])
            assert (media.width, media.height) == (entry.get("width"), entry.get("height"))
            assert media.media_id == entry["id"]
            assert media.page_url == entry["url"]
    raw_videos = [m for item, _ in mapped for m in item["media"] if m["type"] == "Video"]
    assert len(raw_videos) == 2
    assert all("width" not in m and "height" not in m for m in raw_videos)
    videos = [m for _, post in mapped for m in post.media if m.type == "Video"]
    assert len(videos) == 2
    assert all(m.width is None and m.height is None for m in videos)
    empty = {post.source_post_id for _, post in mapped if not post.media}
    assert empty == {"2177677192795804", "2177460729484117"}


def test_author_fields(mapped) -> None:
    for item, post in mapped:
        assert post.author_name == item["user"]["name"]
        assert post.author_id_raw == item["user"]["id"]
        assert post.author_profile_url == item["user"]["profileUrl"]
    by_id = {post.source_post_id: post for _, post in mapped}
    assert by_id["2178092279420962"].author_id_raw == "558703982"


def test_opportunistic_fields(mapped) -> None:
    with_comment = [(item, post) for item, post in mapped if post.top_comment is not None]
    assert len(with_comment) == 3
    assert all(post.top_comment == item["topComment"] for item, post in with_comment)
    for item, post in mapped:
        assert post.reactions_count == item["reactions_count"]
        assert post.comments_count == item["comments_count"]
        assert post.shares_count == item["shares_count"]


def test_derived_fields_are_not_computed_by_the_provider(mapped) -> None:
    for _, post in mapped:
        assert all(getattr(post, name) is None for name in DERIVED_FIELDS)


def test_shared_post_type_raises(thedoor_items) -> None:
    item = copy.deepcopy(thedoor_items[0])
    item["post_type"] = "shared"
    with pytest.raises(UnverifiedSharedPostError):
        to_raw_post(item, FETCHED_AT)


def test_empty_text_with_shared_post_payload_raises(thedoor_items) -> None:
    item = copy.deepcopy(thedoor_items[0])
    item["text"] = ""
    item["sharedPost"] = {"anything": "unverified"}
    with pytest.raises(UnverifiedSharedPostError):
        to_raw_post(item, FETCHED_AT)


def test_blank_text_without_shared_post_is_stored_as_no_text(thedoor_items) -> None:
    item = copy.deepcopy(thedoor_items[0])
    item["text"] = "   \n"
    post = annotate(to_raw_post(item, FETCHED_AT))
    assert post.text == "   \n"
    assert post.text_source == "none"
    assert post.no_text is True
    assert post.text_hash is None
    assert post.phones == []
