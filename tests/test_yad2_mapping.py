"""Yad2's mapping (`PHASE_6.md` §6.2, §6.3, §6.3.1; DECISIONS.md #492–#501): a saved listing page's
`data` to a `RawPost` and to the form's part of a `Listing`, on the spikes' pages read in place from
`data/raw/` (gitignored). No value of a page is written here: every expectation is read from the
page's own `data` at the path the plan names, so no real name, street or token enters git."""

import copy
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import REPO_ROOT, make_listing
from tlv_hunter.contracts.listing import SOURCED_FIELDS, Listing
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.yad2 import mapping
from tlv_hunter.yad2.kinds import KINDS, PROPERTIES
from tlv_hunter.yad2.pages import listing_data, query_data

pytestmark = pytest.mark.raw_fixtures

RAW = REPO_ROOT / "data" / "raw"
# The pages and when each was fetched (the spikes' manifest, UTC). The phone responses are never
# fixtures (#494; deleted from the spike's folder, point 21).
PRIVATE = {
    1: ("yad2_listing_private_1_2026-10-24.html", datetime(2026, 10, 24, 11, 37, 54, tzinfo=UTC)),
    2: ("yad2_listing_private_2_2026-10-24.html", datetime(2026, 10, 24, 11, 38, 15, tzinfo=UTC)),
    3: ("yad2_listing_private_3_2026-10-24.html", datetime(2026, 10, 24, 11, 38, 45, tzinfo=UTC)),
}
# Spike 1's agency page: a listing outside Tel Aviv-Yafo, read for the agency's fields only.
AGENCY = ("yad2_listing_agency_1_2026-10-22.html", datetime(2026, 10, 22, 13, 48, 56, tzinfo=UTC))
LIST_PAGE = "yad2_list_page1_2026-10-24.html"
# Spike §S2.4: each private listing's `updatedAt` was this many minutes before its fetch.
MINUTES_BEFORE_FETCH = {1: 7, 2: 37, 3: 58}


def _page(name: str) -> str:
    path = RAW / name
    if not path.is_file():
        pytest.fail(f"fixture missing: {path}. data/ is gitignored; tests fail, never skip.")
    return path.read_text(encoding="utf-8")


def _data(name: str) -> dict[str, Any]:
    return listing_data(_page(name))


def _all() -> list[tuple[dict[str, Any], datetime]]:
    return [(_data(name), at) for name, at in [*PRIVATE.values(), AGENCY]]


def test_each_page_holds_one_listing_with_a_token() -> None:
    for d, _ in _all():
        assert len(d["token"]) == 8 and d["token"].isalnum() and d["token"].islower()


def test_the_raw_post_table_field_by_field() -> None:
    """§6.2, every row."""
    for d, fetched_at in _all():
        post = mapping.to_raw_post(d, fetched_at)
        token = d["token"]
        assert post.schema_version == 1
        assert post.source == "yad2"
        assert post.source_post_id == token
        assert post.listing_id == hashlib.sha256(f"yad2:{token}".encode()).hexdigest()
        assert post.group_id == "yad2-tel-aviv"
        assert post.group_title == "יד2 · תל אביב-יפו"
        assert post.permalink == f"https://www.yad2.co.il/realestate/item/tel-aviv-area/{token}"
        assert post.fetched_at == fetched_at
        assert post.text == d["metaData"]["description"]
        assert post.text_source == "text"
        assert post.post_type == "yad2_listing"
        assert post.native_price == d["price"] and post.native_price_raw == str(d["price"])
        assert post.native_currency == "ILS"
        assert post.native_title is None
        assert post.native_location == d["address"]["city"]["text"]
        assert post.author_name == d["customer"]["name"]
        assert post.author_id_raw == str(d["customer"]["id"])
        assert post.author_profile_url is None
        assert post.top_comment is None
        assert (post.reactions_count, post.comments_count, post.shares_count) == (None,) * 3
        assert (post.text_hash, post.phones, post.no_text) == (None, None, None)
        assert (post.is_canonical, post.duplicate_of) == (None, None)


def test_a_tel_aviv_listing_s_city_is_the_one_the_city_rule_reads() -> None:
    """#214 rules the city from `native_location`: a Tel Aviv-Yafo listing is never other_city."""
    for name, fetched_at in PRIVATE.values():
        assert mapping.to_raw_post(_data(name), fetched_at).native_location == "תל אביב יפו"


def test_each_photo_is_a_media_item_keyed_by_its_url() -> None:
    """#512: a photo's `media_id` is its own URL, `page_url` the listing's permalink; Yad2 gives no
    width or height. The pages saved hold no video."""
    for d, fetched_at in _all():
        post = mapping.to_raw_post(d, fetched_at)
        urls = d["metaData"]["images"]
        assert urls and all(url.startswith("https://img.yad2.co.il/") for url in urls)
        assert [item.uri for item in post.media] == urls == mapping.photo_urls(d)
        for item in post.media:
            assert (item.type, item.media_id, item.page_url) == ("Photo", item.uri, post.permalink)
            assert (item.width, item.height) == (None, None)
        assert len({item.media_id for item in post.media}) == len(urls)
        assert "video" not in d["metaData"]


def test_the_block_reads_the_form_s_values_verbatim() -> None:
    """#498, #503: the kind, the neighbourhood, the street with its number, roommates when Yad2
    says so, the furniture text; never the description."""
    for d, _ in _all():
        block = mapping.model_block(d)
        assert block is not None
        lines = block.split("\n")
        assert lines[0] == "[Yad2 listing form — not the poster's text]"
        assert f"property kind: {d['additionalDetails']['property']['text']}" in lines
        assert f"neighbourhood: {d['address']['neighborhood']['text']}" in lines
        assert any(line.startswith(f"street: {d['address']['street']['text']}") for line in lines)
        roommates = bool(d["inProperty"].get("isForPartners"))
        assert ("suitable for roommates: yes" in lines) == roommates
        if "furnitureInfo" in d:  # verbatim, its own line breaks included
            assert block.endswith(f"\nfurniture: {d['furnitureInfo']}")
        assert d["metaData"]["description"] not in block


def test_raw_is_the_page_data_whole_and_a_copy() -> None:
    """Invariant 4, #494."""
    for d, fetched_at in _all():
        before = copy.deepcopy(d)
        post = mapping.to_raw_post(d, fetched_at)
        assert post.raw == d == before
        assert json.dumps(post.raw, sort_keys=True) == json.dumps(before, sort_keys=True)
        post.raw["token"] = "changed"
        assert d["token"] == before["token"]


def test_posted_at_is_updated_at_from_israel_time_to_utc() -> None:
    """#492, invariant 9: summer time on 2026-10-24 (UTC+3); minutes before the fetch as the spike
    measured them; `rebouncedAt` is not used."""
    for number, (name, fetched_at) in PRIVATE.items():
        d = _data(name)
        post = mapping.to_raw_post(d, fetched_at)
        naive = datetime.fromisoformat(d["dates"]["updatedAt"])
        assert post.posted_at == (naive - timedelta(hours=3)).replace(tzinfo=UTC)
        before = (fetched_at - post.posted_at) / timedelta(minutes=1)
        assert round(before) == MINUTES_BEFORE_FETCH[number]
        rebounced = {**d, "dates": {**d["dates"], "updatedAt": d["dates"]["rebouncedAt"]}}
        assert post.posted_at != mapping.to_raw_post(rebounced, fetched_at).posted_at


def test_the_description_is_the_text_verbatim_and_hashes_as_today() -> None:
    """Invariants 8, 14: the stored text is the description unchanged; textnorm runs as for a
    Facebook post."""
    for d, fetched_at in _all():
        post = annotate(mapping.to_raw_post(d, fetched_at))
        assert post.text == d["metaData"]["description"]
        assert post.no_text is False and post.text_hash is not None


def _expected_form(d: dict[str, Any]) -> dict[str, Any]:
    """§6.3's table, read at each path the table names, with the page's own values."""

    def w(value: Any) -> dict[str, Any]:
        return {"state": "written", "value": value}

    extra, flags = d["additionalDetails"], d["inProperty"]
    house = d["address"]["house"]
    street = d["address"]["street"]["text"]
    form: dict[str, Any] = {
        "price": w([d["price"]]),
        "price_source": "native",
        "rooms": w(float(extra["roomsCount"])),
        "floor": w(house["floor"]),
        "size_sqm": w(float(extra["squareMeter"])),
        "broker": w(d["adType"] == "commercial"),
        "streets": [f"{street} {house['number']}" if "number" in house else street],
        "stated_area_names": [d["address"]["neighborhood"]["text"]],
    }
    if flags.get("isImmediateEntrance"):
        form["entry_date"] = w("immediate")
    elif "entranceDate" in extra:
        form["entry_date"] = w(date.fromisoformat(extra["entranceDate"][:10]))
    if "buildingTopFloor" in extra:
        form["building_floors"] = w(extra["buildingTopFloor"])
    for field, count, flag in (
        ("balcony", "balconiesCount", "includeBalcony"),
        ("parking", "parkingSpacesCount", "includeParking"),
    ):
        if extra.get(count, 0) > 0 or flags.get(flag) is True:
            form[field] = w(True)
        elif flags.get(flag) is False:
            form[field] = w(False)
    for field, flag in (
        ("elevator", "includeElevator"),
        ("air_conditioning", "includeAirconditioner"),
    ):
        if flag in flags:
            form[field] = w(flags[flag])
    if flags.get("includeFurniture") is False:
        form["furnished"] = w("no")
    for field, key in (("arnona", "propertyTax"), ("house_committee", "houseCommittee")):
        if d.get(key, 0) > 0:
            form[field] = w(d[key])
    return form


def test_the_form_part_on_every_page() -> None:
    kinds = []
    for d, _ in _all():
        expected = _expected_form(d)
        kind = d["additionalDetails"]["property"]["id"]
        kinds.append(kind)
        if kind == 11:  # "יחידת דיור": a whole apartment (#501)
            expected["apartment_kind"] = {"state": "written", "value": "whole_apartment"}
        else:
            assert kind == 1  # "דירה": the model decides the kind
        assert mapping.form_fields(d) == expected
    assert 11 in kinds and 1 in kinds


def test_the_pages_cover_the_table_s_cases() -> None:
    """The fixtures hold the cases the table distinguishes, so the test above is not vacuous."""
    pages = {number: _data(name) for number, (name, _) in PRIVATE.items()}
    forms = {number: mapping.form_fields(d) for number, d in pages.items()}
    agency_data = _data(AGENCY[0])
    agency = mapping.form_fields(agency_data)
    assert forms[1]["entry_date"]["value"] != "immediate"
    assert forms[2]["entry_date"] == {"state": "written", "value": "immediate"}
    assert "elevator" in forms[2] and "elevator" not in forms[1]
    assert "air_conditioning" in forms[1] and "air_conditioning" not in forms[2]
    assert "furnished" not in forms[1]  # `includeFurniture` true: the model chooses (point 7)
    assert "house_committee" not in forms[3] and "arnona" not in forms[3]
    assert forms[1]["broker"]["value"] is False and agency["broker"]["value"] is True
    assert "number" not in agency_data["address"]["house"]
    assert agency["streets"] == [agency_data["address"]["street"]["text"]]
    assert pages[1]["inProperty"]["includeSecurityRoom"] is False  # kept in raw only


def test_the_form_part_with_model_values_is_a_valid_listing_with_its_sources() -> None:
    """The form's values have `Listing`'s own types; the rest from the model, every source
    recorded (#495)."""
    for d, fetched_at in _all():
        post = mapping.to_raw_post(d, fetched_at)
        form = mapping.form_fields(d)
        base = make_listing(post.listing_id).model_dump()
        sources = {name: "form" if name in form else "model" for name in SOURCED_FIELDS}
        listing = Listing.model_validate({**base, **form, "field_sources": sources}, strict=False)
        assert listing.field_sources["price"] == "form"
        assert listing.field_sources["gender"] == "model"
        assert Listing.from_stored_json(listing.model_dump_json()) == listing


def test_the_22_kinds_are_yad2_s_own_search_options() -> None:
    """§6.3.1 against the rent search's `base-search-options` on the saved list page."""
    options = query_data(_page(LIST_PAGE), "base-search-options")
    groups = {group["id"]: group["title"].strip() for group in options["propertyGroup"]}
    yad2 = {int(o["id"]): (o["title"], groups[o["propertyGroupId"]]) for o in options["property"]}
    ours = {kind_id: (kind.title, kind.group) for kind_id, kind in KINDS.items()}
    assert len(yad2) == 22
    assert yad2 == ours
    assert groups["5"] == PROPERTIES


def test_the_search_s_floor_starts_at_minus_one() -> None:
    """Point 6: a basement is -1, as Gate B's `floor` (#98, #118)."""
    options = query_data(_page(LIST_PAGE), "base-search-options")
    assert options["floor"]["from"] == -1


def test_the_yad2_package_never_asks_for_a_phone() -> None:
    """#497: no request to Yad2's phone response or its reveal counter, anywhere in the package."""
    package = Path(mapping.__file__).parent
    for path in package.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "realestate-item/customer" not in source, path
        assert "phone-displayed" not in source, path
