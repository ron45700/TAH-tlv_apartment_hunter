"""Phase 6, build step 1 (`PHASE_6.md` §6.2, §6.3, §6.7; DECISIONS.md #492–#501 and round 43's):
the contracts for Yad2 with no fixture. `RawPost`'s third source and Yad2's `listing_id`; Gate B's
`field_sources` and `Listing` version 2; Gate G's `RunRecord.source` and `ScheduleSettings`' Yad2
rhythm, each version 2 with stored version-1 rows read with defaults; Yad2's dates in the one
datetime module; the 22 kinds' decided rows; the form's edge cases on made-up pages."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tests.conftest import make_listing
from tests.test_gate_g import run_record, settings
from tests.test_raw_post import _valid
from tlv_hunter.contracts.listing import (
    LISTING_SCHEMA_VERSION,
    PROVENANCE_FIELDS,
    SOURCED_FIELDS,
    Listing,
)
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.contracts.run_record import RUN_RECORD_SCHEMA_VERSION, RunRecord
from tlv_hunter.contracts.schedule_settings import (
    SCHEDULE_SETTINGS_SCHEMA_VERSION,
    ScheduleSettings,
)
from tlv_hunter.parsing.datetimes import parse_israel_local_utc, parse_local_date
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.yad2 import mapping
from tlv_hunter.yad2.kinds import KINDS, kind_ruling
from tlv_hunter.yad2.pages import PageShapeError, listing_data

FETCHED_AT = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
TOKEN = "ab1cd2ef"
YAD2_RHYTHM = ("yad2_interval_minutes", "yad2_hours_from", "yad2_hours_until")


# --- dates (invariant 9; #492) ---


@pytest.mark.parametrize(
    ("local", "utc"),
    [
        ("2026-10-24T14:30:00", datetime(2026, 10, 24, 11, 30, tzinfo=UTC)),  # summer, +3
        ("2026-12-01T12:00:00", datetime(2026, 12, 1, 10, 0, tzinfo=UTC)),  # winter, +2
        ("2026-10-25T00:30:00", datetime(2026, 10, 24, 21, 30, tzinfo=UTC)),  # before the change
        ("2026-10-25T01:30:00", datetime(2026, 10, 24, 22, 30, tzinfo=UTC)),  # repeated: earlier
        ("2026-10-25T02:30:00", datetime(2026, 10, 25, 0, 30, tzinfo=UTC)),  # after the change
        ("2027-03-26T03:30:00", datetime(2027, 3, 26, 0, 30, tzinfo=UTC)),  # after spring's gap
        ("2026-10-24T14:30:00.123", datetime(2026, 10, 24, 11, 30, 0, 123000, tzinfo=UTC)),
    ],
)
def test_israel_local_time_to_utc_across_the_clock_changes(local: str, utc: datetime) -> None:
    converted = parse_israel_local_utc(local)
    assert converted == utc
    assert converted.utcoffset() == timedelta(0)


@pytest.mark.parametrize("value", ["2026-10-24T14:30:00+03:00", "2026-10-24T11:30:00Z"])
def test_a_yad2_date_with_a_zone_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="no zone"):
        parse_israel_local_utc(value)


def test_an_entrance_date_is_its_calendar_date() -> None:
    assert parse_local_date("2026-11-01T00:00:00") == date(2026, 11, 1)
    for bad in ("2026-11-01T09:00:00", "2026-11-01T00:00:00+02:00"):
        with pytest.raises(ValueError):
            parse_local_date(bad)


def test_the_one_utc_check_is_unchanged() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(posted_at=datetime(2026, 10, 24, 14, 30)))
    with pytest.raises(ValidationError):
        israel = timezone(timedelta(hours=3))
        RawPost(**_valid(posted_at=datetime(2026, 10, 24, 14, 30, tzinfo=israel)))


# --- RawPost and listing_id (#496) ---


def test_yad2_s_listing_id_and_facebook_s_unchanged() -> None:
    yad2 = hashlib.sha256(f"yad2:{TOKEN}".encode()).hexdigest()
    assert compute_listing_id(TOKEN, source="yad2") == yad2
    facebook = hashlib.sha256(b"123").hexdigest()
    assert compute_listing_id("123") == facebook
    for source in ("thedoor", "memo23"):
        assert compute_listing_id("123", source=source) == facebook


def test_raw_post_takes_the_yad2_source_with_its_listing_id() -> None:
    yad2 = _valid(
        source="yad2", source_post_id=TOKEN, listing_id=compute_listing_id(TOKEN, source="yad2")
    )
    assert RawPost(**yad2).source == "yad2"
    with pytest.raises(ValidationError, match="listing_id"):
        RawPost(**{**yad2, "listing_id": compute_listing_id(TOKEN)})
    with pytest.raises(ValidationError):
        RawPost(**_valid(source="yad3"))


def _page(**changes: Any) -> dict[str, Any]:
    """A made-up listing page's `data`: the keys the mapping reads; every value invented."""
    d: dict[str, Any] = {
        "token": TOKEN,
        "adType": "private",
        "price": 6500,
        "additionalDetails": {"property": {"id": 1}, "roomsCount": 3, "squareMeter": 70},
        "inProperty": {},
        "address": {
            "city": {"text": "תל אביב יפו"},
            "neighborhood": {"text": "שכונה לדוגמה"},
            "street": {"text": "רחוב לדוגמה"},
            "house": {"number": 7, "floor": 2},
        },
        "metaData": {"description": "דירה לדוגמה", "images": []},
        "customer": {"id": 1, "name": "שם"},
        "dates": {"updatedAt": "2026-10-24T14:30:00", "rebouncedAt": "2026-10-24T17:30:00"},
    }
    return {**d, **changes}


def _with_details(**details: Any) -> dict[str, Any]:
    page = _page()
    page["additionalDetails"] = {**page["additionalDetails"], **details}
    return page


def test_a_listing_with_no_description_has_no_text() -> None:
    """Point 23 is the pre-model rule's (a later step): the `RawPost` is as Gate A says."""
    for meta in ({"images": []}, {"description": "", "images": []}, {"description": "  "}):
        post = mapping.to_raw_post(_page(metaData=meta), FETCHED_AT)
        assert post.text_source == "none"
        annotated = annotate(post)
        assert annotated.no_text is True and annotated.text_hash is None


def test_a_price_of_zero_is_no_price_and_a_high_one_is_kept() -> None:
    """#501."""
    zero = mapping.to_raw_post(_page(price=0), FETCHED_AT)
    assert (zero.native_price, zero.native_price_raw, zero.native_currency) == (None, None, None)
    assert "price" not in mapping.form_fields(_page(price=0))
    high = mapping.to_raw_post(_page(price=25000), FETCHED_AT)
    assert (high.native_price, high.native_currency) == (25000, "ILS")
    assert mapping.form_fields(_page(price=25000))["price"]["value"] == [25000]


def test_posted_at_is_updated_at_never_rebounced_at() -> None:
    post = mapping.to_raw_post(_page(), FETCHED_AT)
    assert post.posted_at == datetime(2026, 10, 24, 11, 30, tzinfo=UTC)


def test_the_page_s_data_is_found_by_the_item_query() -> None:
    def html(queries: list[Any]) -> str:
        state = {"props": {"pageProps": {"dehydratedState": {"queries": queries}}}}
        script = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(state)}</script>'
        return f"<html><body>{script}</body></html>"

    item = {"queryKey": ["item", TOKEN], "state": {"data": {"token": TOKEN}}}
    other = {"queryKey": ["feature-flag"], "state": {"data": {}}}
    assert listing_data(html([other, item])) == {"token": TOKEN}
    for queries in ([other], [item, item]):
        with pytest.raises(PageShapeError):
            listing_data(html(queries))
    with pytest.raises(PageShapeError):
        listing_data("<html><title>Radware Bot Manager Captcha</title></html>")


# --- the form's part (§6.3) ---


def test_the_form_s_broker_and_flags() -> None:
    assert mapping.form_fields(_page())["broker"]["value"] is False
    assert mapping.form_fields(_page(adType="commercial"))["broker"]["value"] is True
    assert "broker" not in mapping.form_fields(_page(adType="unknown"))
    absent = mapping.form_fields(_page())
    for field in ("balcony", "parking", "elevator", "air_conditioning", "furnished"):
        assert field not in absent
    no = {"includeBalcony": False, "includeElevator": False, "includeFurniture": False}
    flags = mapping.form_fields(_page(inProperty=no))
    assert flags["balcony"]["value"] is False and flags["elevator"]["value"] is False
    assert flags["furnished"]["value"] == "no"
    furnished = mapping.form_fields(_page(inProperty={"includeFurniture": True}))
    assert "furnished" not in furnished  # point 7: the model chooses
    assert mapping.form_fields(_with_details(parkingSpacesCount=1))["parking"]["value"] is True
    assert "parking" not in mapping.form_fields(_with_details(parkingSpacesCount=0))


def test_the_form_s_numbers() -> None:
    assert mapping.form_fields(_with_details(roomsCount=2.5))["rooms"]["value"] == 2.5
    assert "rooms" not in mapping.form_fields(_with_details(roomsCount=2.3))
    for floor in (0, -1, 4):
        page = _page()
        page["address"] = {**page["address"], "house": {"floor": floor}}
        form = mapping.form_fields(page)
        assert form["floor"]["value"] == floor
        assert form["streets"] == ["רחוב לדוגמה"]  # no house number
    assert "arnona" not in mapping.form_fields(_page(propertyTax=0))
    taxes = mapping.form_fields(_page(propertyTax=400, houseCommittee=150))
    assert (taxes["arnona"]["value"], taxes["house_committee"]["value"]) == (400, 150)


def test_the_form_s_entry_date() -> None:
    later = _with_details(entranceDate="2026-12-01T00:00:00")
    assert mapping.form_fields(later)["entry_date"]["value"] == date(2026, 12, 1)
    later["inProperty"] = {"isImmediateEntrance": True}
    form = mapping.form_fields(later)
    assert form["entry_date"]["value"] == "immediate"
    assert "entry_date_written" not in form  # never "as written" (#96)
    assert "entry_date" not in mapping.form_fields(_page())


def test_the_form_never_fills_what_the_model_decides() -> None:
    """#495: `gender`, `areas`, `other_city`, `phone_names`, `room_size_sqm` and the written entry
    date are the model's, whatever the kind."""
    model_only = (
        "gender",
        "areas",
        "other_city",
        "phone_names",
        "room_size_sqm",
        "entry_date_written",
    )
    for kind_id in KINDS:
        form = mapping.form_fields(_with_details(property={"id": kind_id}))
        assert not set(model_only) & set(form)
        assert set(form) <= SOURCED_FIELDS | {"price_source"}


# --- the 22 kinds (§6.3.1) ---


def test_the_decided_kinds() -> None:
    """#501's rows, and point 10's as proposed."""
    assert len(KINDS) == 22
    for kind_id in (30, 45, 31, 25, 32, 55, 33, 44, 61, 50):
        assert KINDS[kind_id].post_nature == "not_listing"
        assert KINDS[kind_id].rejected_before_model
    assert KINDS[43].post_nature == "sublet_offer" and KINDS[43].apartment_kind is None
    assert KINDS[11].apartment_kind == "whole_apartment" and KINDS[11].post_nature is None
    assert KINDS[4].apartment_kind == "whole_apartment"
    for kind_id in (1, 3, 6, 7, 51, 49, 5, 39, 41):
        assert (KINDS[kind_id].post_nature, KINDS[kind_id].apartment_kind) == (None, None)
    rejected = {kind_id for kind_id, kind in KINDS.items() if kind.rejected_before_model}
    assert rejected == {31, 25, 32, 55, 30, 45, 33, 44, 61, 50}


def test_an_unknown_kind_leaves_both_to_the_model() -> None:
    for kind_id in (None, 999):
        kind = kind_ruling(kind_id)
        assert (kind.post_nature, kind.apartment_kind) == (None, None)
        assert not kind.rejected_before_model
    form = mapping.form_fields(_with_details(property={"id": 999}))
    assert "post_nature" not in form and "apartment_kind" not in form


def test_a_kind_s_values_reach_the_form() -> None:
    for kind_id, field, value in (
        (30, "post_nature", "not_listing"),
        (43, "post_nature", "sublet_offer"),
        (11, "apartment_kind", {"state": "written", "value": "whole_apartment"}),
    ):
        assert mapping.form_fields(_with_details(property={"id": kind_id}))[field] == value


# --- Listing version 2 (#495, point 5) ---


def test_listing_is_version_2_and_a_facebook_listing_has_no_sources() -> None:
    assert LISTING_SCHEMA_VERSION == 2
    listing = make_listing("a" * 64)
    assert listing.schema_version == 2 and listing.field_sources == {}
    assert "field_sources" in PROVENANCE_FIELDS
    assert SOURCED_FIELDS == frozenset(Listing.model_fields) - PROVENANCE_FIELDS
    some = {"post_nature", "price", "entry_date", "gender", "areas", "phone_names"}
    assert some <= SOURCED_FIELDS


def test_field_sources_names_every_field_or_none() -> None:
    every = dict.fromkeys(SOURCED_FIELDS, "model")
    assert make_listing("a" * 64, field_sources=every).field_sources == every
    for bad in (
        dict(list(every.items())[:-1]),
        {**every, "listing_id": "form"},
    ):
        with pytest.raises(ValidationError, match="field_sources"):
            make_listing("a" * 64, field_sources=bad)
    with pytest.raises(ValidationError):
        make_listing("a" * 64, field_sources={**every, "price": "native"})


def test_a_stored_version_1_listing_reads_as_version_2() -> None:
    stored = json.loads(make_listing("a" * 64).model_dump_json())
    del stored["field_sources"]
    stored["schema_version"] = 1
    listing = Listing.from_stored_json(json.dumps(stored))
    assert (listing.schema_version, listing.field_sources) == (2, {})
    assert listing == make_listing("a" * 64)
    stored["field_sources"] = {}
    assert Listing.from_stored_json(json.dumps(stored)) == listing
    stored["field_sources"] = {"price": "form"}
    with pytest.raises(ValueError, match="version-1"):
        Listing.from_stored_json(json.dumps(stored))


# --- Gate G version 2 (point 19) ---


def test_run_record_is_version_2_with_its_source() -> None:
    assert RUN_RECORD_SCHEMA_VERSION == 2
    assert run_record().source == "facebook"
    no_apify = {"apify_run_id": None, "charged_events": None}
    assert run_record(source="yad2", window_since=None, **no_apify).source == "yad2"
    for apify in ({"apify_run_id": "AbCdEf"}, {"charged_events": {"x": 1}}):
        with pytest.raises(ValidationError, match="Yad2 run"):
            run_record(source="yad2", **{**no_apify, **apify})
    with pytest.raises(ValidationError):
        run_record(source="memo23")


def test_a_stored_version_1_run_reads_as_a_facebook_run() -> None:
    stored = json.loads(run_record().model_dump_json())
    del stored["source"]
    stored["schema_version"] = 1
    assert RunRecord.from_stored_json(json.dumps(stored)) == run_record()
    stored["source"] = "facebook"
    with pytest.raises(ValueError, match="version-1"):
        RunRecord.from_stored_json(json.dumps(stored))


def test_schedule_settings_is_version_2_with_yad2_s_rhythm() -> None:
    assert SCHEDULE_SETTINGS_SCHEMA_VERSION == 2
    assert tuple(getattr(settings(), name) for name in YAD2_RHYTHM) == (None, None, None)
    rhythm = dict(zip(YAD2_RHYTHM, (60, "07:00", "23:00"), strict=True))
    assert settings(**rhythm).yad2_interval_minutes == 60
    for bad in (
        {**rhythm, "yad2_hours_until": None},
        {"yad2_interval_minutes": 60},
        {**rhythm, "yad2_interval_minutes": 4},
        {**rhythm, "yad2_interval_minutes": 24 * 60 + 1},
        {**rhythm, "yad2_hours_from": "23:00", "yad2_hours_until": "07:00"},
        {**rhythm, "yad2_hours_until": "07:00"},
        {**rhythm, "yad2_hours_from": "7:00"},
    ):
        with pytest.raises(ValidationError):
            settings(**bad)


def test_a_stored_version_1_schedule_reads_with_no_yad2_rhythm() -> None:
    stored = json.loads(settings().model_dump_json())
    for name in YAD2_RHYTHM:
        del stored[name]
    stored["schema_version"] = 1
    assert ScheduleSettings.from_stored_json(json.dumps(stored)) == settings()
    stored["yad2_interval_minutes"] = None
    with pytest.raises(ValueError, match="version-1"):
        ScheduleSettings.from_stored_json(json.dumps(stored))


def _store_version_1_rows(path: Path) -> None:
    run = json.loads(run_record().model_dump_json())
    del run["source"]
    schedule = json.loads(settings().model_dump_json())
    for name in YAD2_RHYTHM:
        del schedule[name]
    run["schema_version"] = schedule["schema_version"] = 1
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute(
            "INSERT INTO run_records (run_id, doc) VALUES (?, ?)", (run["run_id"], json.dumps(run))
        )
        conn.execute(
            "INSERT INTO schedule_settings (id, doc) VALUES ('schedule', ?)",
            (json.dumps(schedule),),
        )


def test_the_run_store_reads_and_writes_over_stored_version_1_rows(tmp_path: Path) -> None:
    """Read-time only: a version-1 row reads as version 2, compare and set holds against it, and
    the next save writes version 2."""
    path = tmp_path / "store.sqlite"
    store = SqliteRunStore(path)
    _store_version_1_rows(path)
    run = store.get_run(run_record().run_id)
    assert run == run_record() and store.recent_runs() == [run]
    settled = run.model_copy(update={"cost_usd": 0.01, "cost_settled_at": FETCHED_AT})
    store.save_run(RunRecord.model_validate(settled.model_dump()), expected=run)
    schedule = store.get_settings()
    assert schedule == settings()
    store.save_settings(settings(interval_minutes=45), expected=schedule)
    assert store.set_last_digest(FETCHED_AT)
    with closing(sqlite3.connect(path)) as conn:
        runs = [json.loads(doc) for (doc,) in conn.execute("SELECT doc FROM run_records")]
        rows = [json.loads(doc) for (doc,) in conn.execute("SELECT doc FROM schedule_settings")]
    assert [(doc["schema_version"], doc["source"]) for doc in runs] == [(2, "facebook")]
    assert [(doc["schema_version"], doc["yad2_interval_minutes"]) for doc in rows] == [(2, None)]
