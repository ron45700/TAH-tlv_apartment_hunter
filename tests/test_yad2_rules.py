"""Phase 6, build step 2 (`PHASE_6.md`; DECISIONS.md #495, #500, #502, #503, #508–#510, #512,
#517, #518): Yad2's rules around the model, on made-up pages (no fixture). The pre-model rules,
dedup A and the Gate D key kept apart from Facebook, the form merged into the model's answer with
`field_sources`, the request's labelled block, and the media of #512."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from tests.conftest import make_listing, overwrite_lifecycle, post_with_text
from tests.test_openai_classifier import FakeTransport, classifier
from tests.test_raw_post import _valid
from tlv_hunter.classify.complete import Completed, Provenance, complete
from tlv_hunter.contracts.listing import SOURCED_FIELDS
from tlv_hunter.contracts.listing_extraction import ListingExtraction
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.dedup.stage_a import dedup_a
from tlv_hunter.dedup.stage_b import KeyPost, pair_rules
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.postmodel.seen import seen_listing
from tlv_hunter.premodel.rejects import initial_lifecycle, pre_model_reason, recheck
from tlv_hunter.store.base import Repository
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.yad2 import mapping

FETCHED_AT = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
PROVENANCE = Provenance("gpt-6-luna", "7", FETCHED_AT)
DESCRIPTION = "דירת 3 חדרים משופצת, קרובה לים. כניסה מיידית."
STREET, NUMBER, AREA = "רחוב לדוגמה", 7, "שכונה לדוגמה"
PHOTOS = ["https://img.yad2.co.il/Pic/1/a.jpeg", "https://img.yad2.co.il/Pic/1/b.jpeg"]


def page(token: str = "ab1cd2ef", **changes: Any) -> dict[str, Any]:
    """A made-up listing page's `data`; every value invented."""
    d: dict[str, Any] = {
        "token": token,
        "adType": "private",
        "price": 6500,
        "furnitureInfo": "ספה ומיטה",
        "additionalDetails": {
            "property": {"id": 1, "text": "דירה"},
            "roomsCount": 3,
            "squareMeter": 70,
        },
        "inProperty": {"includeBalcony": True},
        "address": {
            "city": {"text": "תל אביב יפו"},
            "neighborhood": {"text": AREA},
            "street": {"text": STREET},
            "house": {"number": NUMBER, "floor": 2},
        },
        "metaData": {"description": DESCRIPTION, "images": PHOTOS},
        "customer": {"id": 1, "name": "שם"},
        "dates": {"updatedAt": "2026-10-24T14:30:00"},
    }
    return {**d, **changes}


def yad2_post(**changes: Any) -> RawPost:
    return annotate(mapping.to_raw_post(page(**changes), FETCHED_AT))


def with_kind(kind_id: int) -> RawPost:
    d = page()
    d["additionalDetails"] = {**d["additionalDetails"], "property": {"id": kind_id, "text": "x"}}
    return annotate(mapping.to_raw_post(d, FETCHED_AT))


def bare_page() -> dict[str, Any]:
    """No description and nothing for the block (#518)."""
    d = page(metaData={}, furnitureInfo=None, inProperty={})
    d["additionalDetails"] = {"property": {"id": 1}}
    d["address"] = {"city": {"text": "תל אביב יפו"}, "house": {}}
    return d


def facebook_post(post_id: str, text: str) -> RawPost:
    base = RawPost(**_valid(source_post_id=post_id, listing_id=compute_listing_id(post_id)))
    return post_with_text(base, text).with_changes(is_canonical=None)


# --- media (#512) ---


def test_photos_and_the_video_keep_their_own_url_and_point_at_the_listing() -> None:
    video = "https://videos.yad2.co.il/v/1.mp4"
    d = page()
    d["metaData"] = {**d["metaData"], "video": video}
    post = mapping.to_raw_post(d, FETCHED_AT)
    assert [(m.type, m.uri, m.media_id) for m in post.media] == [
        ("Photo", PHOTOS[0], PHOTOS[0]),
        ("Photo", PHOTOS[1], PHOTOS[1]),
        ("Video", video, video),
    ]
    assert {m.page_url for m in post.media} == {post.permalink}
    assert mapping.to_raw_post(page(metaData={"description": "x"}), FETCHED_AT).media == []


# --- the pre-model rules (Gate E's Yad2 rules) ---


def test_a_yad2_listing_with_no_photo_is_not_rejected() -> None:
    """#510."""
    post = yad2_post(metaData={"description": DESCRIPTION})
    assert post.media == [] and pre_model_reason(post) is None


def test_a_yad2_listing_with_no_description_goes_to_the_model_with_its_block() -> None:
    """#509: not `no_text` while the block has a line."""
    post = yad2_post(metaData={"images": []})
    assert post.no_text is True and pre_model_reason(post) is None
    assert initial_lifecycle(post).state == "pending"


def test_a_yad2_listing_with_nothing_for_the_model_is_no_text() -> None:
    """#518: no description and no line for the block."""
    post = annotate(mapping.to_raw_post(bare_page(), FETCHED_AT))
    assert mapping.model_block(post.raw) is None
    assert pre_model_reason(post) == "no_text"


@pytest.mark.parametrize("kind_id", [30, 45, 31, 25, 32, 55, 33, 44, 61, 50])
def test_a_kind_mapped_to_not_listing_is_rejected_before_the_model(kind_id: int) -> None:
    """#502 point 11."""
    record = initial_lifecycle(with_kind(kind_id))
    assert (record.state, record.rejection_reason) == ("rejected", "not_listing")


@pytest.mark.parametrize("kind_id", [1, 4, 11, 43, 41, 999])
def test_other_kinds_go_to_the_model(kind_id: int) -> None:
    assert pre_model_reason(with_kind(kind_id)) is None


def test_facebook_s_pre_model_rules_are_unchanged() -> None:
    assert pre_model_reason(facebook_post("1", "דירה להשכרה")) == "no_images"
    empty = annotate(RawPost(**_valid(text="", text_source="none")))
    assert pre_model_reason(empty) == "no_text"


def test_only_a_kind_s_not_listing_is_re_checked() -> None:
    """A model's `not_listing` is a verdict: never re-checked back to pending, for either source."""
    parking = with_kind(30)
    kind_record = initial_lifecycle(parking)
    assert recheck(kind_record, parking) == kind_record
    for post in (yad2_post(), facebook_post("2", "חניה להשכרה")):
        verdict = initial_lifecycle(post).model_copy(
            update={"state": "rejected", "rejection_reason": "not_listing"}
        )
        assert recheck(verdict, post) == verdict


# --- dedup A (#500, #508) ---


def _dedup(repository: Repository, batch: list[RawPost]) -> dict[str, tuple[bool, str | None]]:
    result = dedup_a(batch, repository)
    for post in result.posts:
        repository.upsert(post)
    for record in result.lifecycles:
        overwrite_lifecycle(repository, record)
    return {post.listing_id: (post.is_canonical, post.duplicate_of) for post in result.posts}


def test_dedup_a_never_joins_facebook_and_yad2(make_repository) -> None:
    repository = make_repository()
    stored = facebook_post("3", DESCRIPTION)
    _dedup(repository, [stored])
    yad2 = yad2_post()
    assert yad2.text_hash == repository.get(stored.listing_id).text_hash
    assert _dedup(repository, [yad2]) == {yad2.listing_id: (True, None)}


def test_two_private_yad2_listings_with_one_text_are_duplicates(make_repository) -> None:
    repository = make_repository()
    first = yad2_post(token="aaaa1111")
    second = yad2_post(token="bbbb2222", dates={"updatedAt": "2026-10-24T15:00:00"})
    _dedup(repository, [first])
    assert _dedup(repository, [second]) == {second.listing_id: (False, first.listing_id)}


def test_an_agency_listing_is_never_deduplicated_either_way(make_repository) -> None:
    """#508: not as a new post, and not as the stored match of a new one."""
    repository = make_repository()
    _dedup(repository, [yad2_post(token="aaaa1111", adType="commercial")])
    second_agency = yad2_post(token="bbbb2222", adType="commercial")
    private = yad2_post(token="cccc3333")
    assert _dedup(repository, [second_agency, private]) == {
        second_agency.listing_id: (True, None),
        private.listing_id: (True, None),
    }


# --- the Gate D key (#500) ---


def _key_post(post: RawPost) -> KeyPost:
    record = initial_lifecycle(post).model_copy(update={"state": "active"})
    return KeyPost(post, record, seen_listing(make_listing(post.listing_id), []), frozenset({"p"}))


def test_the_key_never_ties_facebook_and_yad2() -> None:
    """A shared phone and a shared photo tie two posts of one source, never across sources."""
    phone = ["0541234567"]
    fb_one = facebook_post("4", "דירה א").with_changes(is_canonical=True, phones=phone)
    fb_two = facebook_post("5", "דירה ב").with_changes(is_canonical=True, phones=phone)
    yad2 = yad2_post().with_changes(is_canonical=True, phones=phone)
    assert pair_rules(_key_post(fb_one), _key_post(fb_two), frozenset())
    assert pair_rules(_key_post(fb_one), _key_post(yad2), frozenset()) == ()


# --- the form merged into the model's answer (#495, #502, #517) ---


def answer(**changes: Any) -> dict[str, Any]:
    """A model answer with nothing written, as the schema shapes it."""
    listing = make_listing("a" * 64).model_dump(mode="json")
    code_filled = ("schema_version", "listing_id", "model_name", "prompt_version", "classified_at")
    for name in (*code_filled, "price_source", "entry_date", "phone_names", "field_sources"):
        del listing[name]
    listing.update(entry_date_parts={"state": "not_written", "value": None}, phone_name_pairs=[])
    return {**listing, **changes}


def _complete(post: RawPost, **changes: Any) -> Completed:
    return complete(ListingExtraction.model_validate(answer(**changes)), post, PROVENANCE)


def written(value: Any) -> dict[str, Any]:
    return {"state": "written", "value": value}


def test_the_form_wins_and_every_field_has_its_source() -> None:
    listing = _complete(
        yad2_post(adType="commercial"),
        price=written([5000]),
        rooms=written(4.0),
        broker=written(False),
        balcony=written(False),
        gender="women_only",
        areas=[12],
    ).listing
    assert listing.price.value == [6500] and listing.price_source == "native"
    assert listing.rooms.value == 3.0 and listing.broker.value is True
    assert listing.balcony.value is True
    assert (listing.gender, listing.areas) == ("women_only", [12])
    assert set(listing.field_sources) == SOURCED_FIELDS
    from_form = {name for name, source in listing.field_sources.items() if source == "form"}
    assert from_form == {
        "price",
        "rooms",
        "size_sqm",
        "floor",
        "broker",
        "balcony",
        "streets",
        "stated_area_names",
    }


def test_the_form_s_kind_wins_over_the_model() -> None:
    """#502 point 25: a sublet kind is a sublet, a housing unit a whole apartment."""
    sublet = _complete(with_kind(43), post_nature="rental_offer").listing
    assert sublet.post_nature == "sublet_offer" and sublet.field_sources["post_nature"] == "form"
    unit = _complete(with_kind(11), apartment_kind=written("room")).listing
    assert unit.apartment_kind.value == "whole_apartment"


def test_the_form_s_names_lead_and_the_model_s_follow() -> None:
    """#502 point 8, #517: the form's street and neighbourhood first, exempt from #162; a model
    name equal to the form's is merged, not dropped; the model's own names are held to #162."""
    done = _complete(
        yad2_post(),
        streets=[f"{STREET} {NUMBER}", "רחוב אחר"],
        stated_area_names=[AREA, "צפון"],
    )
    assert done.listing.streets == [f"{STREET} {NUMBER}"]
    assert done.listing.stated_area_names == [AREA]
    assert (done.dropped_streets, done.dropped_area_names) == (("רחוב אחר",), ("צפון",))
    sources = done.listing.field_sources
    assert sources["streets"] == sources["stated_area_names"] == "form"


def test_a_model_name_in_the_description_follows_the_form_s() -> None:
    text = f"{DESCRIPTION} ליד רחוב הים."
    done = _complete(yad2_post(metaData={"description": text}), streets=["רחוב הים"])
    assert done.listing.streets == [f"{STREET} {NUMBER}", "רחוב הים"]


def test_with_no_description_the_model_s_names_are_dropped_and_the_form_s_kept() -> None:
    done = _complete(yad2_post(metaData={"images": []}), streets=[STREET])
    assert done.listing.streets == [f"{STREET} {NUMBER}"]
    assert done.dropped_streets == (STREET,)


def test_a_facebook_listing_has_no_sources_and_is_as_before() -> None:
    post = facebook_post("6", "דירה ברחוב הירקון 5, 6000 ש״ח").with_changes(is_canonical=True)
    listing = _complete(post, price=written([6000]), streets=["הירקון 5"]).listing
    assert listing.field_sources == {}
    assert (listing.price.value, listing.price_source, listing.streets) == (
        [6000],
        "text",
        ["הירקון 5"],
    )


# --- the request (#498, #503, #509, #519) ---


def _user(post: RawPost) -> list[dict[str, Any]]:
    request = classifier(FakeTransport()).request(post)
    (user,) = [item for item in request["input"] if item["role"] == "user"]
    return user["content"]


def test_a_yad2_request_sends_the_text_then_the_block() -> None:
    post = yad2_post()
    assert _user(post) == [
        {"type": "input_text", "text": post.text},
        {"type": "input_text", "text": mapping.model_block(post.raw)},
    ]
    assert DESCRIPTION not in mapping.model_block(post.raw)


def test_with_no_description_the_block_alone_is_sent() -> None:
    parts = _user(yad2_post(metaData={"images": []}))
    assert len(parts) == 1 and parts[0]["text"].startswith("[Yad2 listing form")


def test_nothing_to_send_is_refused() -> None:
    post = annotate(mapping.to_raw_post(bare_page(), FETCHED_AT))
    with pytest.raises(ValueError, match="nothing to send"):
        _user(post)


def test_a_facebook_request_is_unchanged() -> None:
    post = facebook_post("7", "דירה להשכרה")
    assert _user(post) == [{"type": "input_text", "text": "דירה להשכרה"}]
    request = classifier(FakeTransport()).request(post)
    assert json.dumps(request, ensure_ascii=False).count("Yad2 listing form") == 1  # instructions


def test_the_block_is_never_normalized() -> None:
    """Invariant 8: the form's values go as Yad2 gives them, final letters and slashes kept."""
    post = yad2_post(furnitureInfo="ספה/מיטה, ארון")
    assert _user(post)[1]["text"].endswith("\nfurniture: ספה/מיטה, ארון")
