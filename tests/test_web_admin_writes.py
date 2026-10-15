"""The admin's post writes, build steps 4 and 5 (`PHASE_3.md` 3.8 (e), (i); DECISIONS.md #389–#406):
test groups 5 (retry), 6 (restore, every case of #251, #281–#283, the flag action, the unfinished
restore), 7 (leave out, then restore later), 8 (remove from the list), 9 (corrections) and 11 (the
invariants) for the writes. Every write is checked against the post's `version` (#391) and written
by compare and set (#260).

Temporary stores only (`tests/test_web_admin.py`'s `AdminStore`); hashes with `profiles.CHEAPEST`.
"""

import dataclasses
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AnotherWriterFirst, overwrite_lifecycle
from tests.test_userdata_store import ADMIN_ID
from tests.test_web import (
    NOW,
    _event_loop_self_pipe,  # noqa: F401  (#344: the same one exception)
    bar,
)
from tests.test_web_accounts import FRIEND_PASSWORD, HASHER, ORIGIN, Clock, sign_in, write
from tests.test_web_admin import (
    AdminStore,
    a_report,
    client_of,
    flag,
    friend,
    posts,
    table_rows,
)
from tlv_hunter.web.app import create_app, site_over


@pytest.fixture
def store(tmp_path: Path) -> AdminStore:
    return AdminStore(tmp_path / "store")


@pytest.fixture
def site(store: AdminStore):
    return site_over(store.db, store.root, clock=Clock(), hasher=HASHER)


@pytest.fixture
def ron(site) -> TestClient:
    client = client_of(site)
    assert sign_in(client).status_code == 200
    return client


# --- helpers ---


def detail(client: TestClient, listing_id: str) -> dict:
    answer = client.get(f"/api/admin/posts/{listing_id}")
    assert answer.status_code == 200, answer.text
    return answer.json()


def version(client: TestClient, listing_id: str) -> str:
    return detail(client, listing_id)["version"]


def report(store: AdminStore, listing_id: str, fields: list[str], n: int = 1):
    """An open report as the site writes it: the report, then the post's record (#279, #280)."""
    made = store.userdata.add_report(a_report(listing_id, fields, n=n))
    flag(store, listing_id, reason="misclassified")
    return made


def restore(client: TestClient, *items: tuple[str, str]):
    body = {"posts": [{"listing_id": i, "version": v} for i, v in items]}
    return write(client, "POST", "/api/admin/restore", body)


def correct(client: TestClient, listing_id: str, field: str, value: Any, report_id: str):
    body = {
        "listing_id": listing_id,
        "field": field,
        "corrected_value": value,
        "report_id": report_id,
        "version": version(client, listing_id),
    }
    return write(client, "POST", "/api/admin/corrections", body)


def post_write(client: TestClient, path: str, listing_id: str, seen: str | None = None):
    seen = version(client, listing_id) if seen is None else seen
    return write(client, "POST", path.format(id=listing_id), {"version": seen})


def lifecycle(store: AdminStore, listing_id: str):
    return store.repository.get_lifecycle(listing_id)


# --- 5. retry ---


def test_retry_sets_the_failures_back_and_keeps_the_error(ron: TestClient, store: AdminStore):
    stored = lifecycle(store, store.pending)
    failing = {"classification_failures": 3, "last_classification_error": "timeout"}
    overwrite_lifecycle(store.repository, stored.model_copy(update=failing))
    answer = post_write(ron, "/api/admin/retry/{id}", store.pending)
    assert answer.status_code == 200
    assert answer.json()["lifecycle"]["failures"] == 0
    after = lifecycle(store, store.pending)
    assert (after.classification_failures, after.last_classification_error) == (0, "timeout")
    again = post_write(ron, "/api/admin/retry/{id}", store.pending, answer.json()["version"])
    assert (again.status_code, again.json()) == (409, {"refusal": "not_retryable"})


def test_a_stale_version_writes_nothing(ron: TestClient, store: AdminStore) -> None:
    stored = lifecycle(store, store.pending)
    overwrite_lifecycle(store.repository, stored.model_copy(update={"classification_failures": 1}))
    seen = version(ron, store.pending)
    store.userdata.add_report(a_report(store.pending, ["price"]))  # a write after the page read
    before = store.db.read_bytes()
    answer = post_write(ron, "/api/admin/retry/{id}", store.pending, seen)
    assert (answer.status_code, answer.json()) == (409, {"refusal": "changed"})
    assert store.db.read_bytes() == before


# --- 6. restore (#251, #281–#283) ---


def test_a_flag_action_restores_both_posts_to_active(ron: TestClient, store: AdminStore) -> None:
    flag(store, store.active)
    flag(store, store.other)
    rows = posts(ron, "flags").json()["rows"]
    answer = restore(ron, *[(r["id"], r["version"]) for r in rows])
    outcomes = {r["listing_id"]: (r["outcome"], r["state"]) for r in answer.json()["results"]}
    assert outcomes == {store.active: ("restored", "active"), store.other: ("restored", "active")}
    for listing_id in (store.active, store.other):
        record = lifecycle(store, listing_id)
        assert (record.flagged_by, record.flagged_at, record.flag_note) == (None, None, None)
    listed = {card["id"] for card in ron.get("/api/cards").json()["cards"]}
    assert {store.active, store.other} <= listed


def test_a_flag_action_with_one_post_changed_is_partial(ron: TestClient, store: AdminStore):
    flag(store, store.active)
    flag(store, store.other)
    rows = posts(ron, "flags").json()["rows"]
    stored = lifecycle(store, store.other)
    overwrite_lifecycle(store.repository, stored.model_copy(update={"flag_note": "another"}))
    results = restore(ron, *[(r["id"], r["version"]) for r in rows]).json()["results"]
    assert {r["listing_id"]: r["outcome"] for r in results} == {
        store.active: "restored",
        store.other: "changed",
    }
    assert lifecycle(store, store.other).rejection_reason == "flagged"


def test_a_reported_post_restores_by_its_corrected_nature(ron: TestClient, store: AdminStore):
    made = report(store, store.active, ["post_nature"])
    assert correct(ron, store.active, "post_nature", "for_sale", made.report_id).status_code == 200
    seen = detail(ron, store.active)
    assert seen["restore_preview"]["reason"] == "for_sale"  # #406
    results = restore(ron, (store.active, seen["version"])).json()["results"]
    assert results[0]["outcome"] == "restored"
    record = lifecycle(store, store.active)
    assert (record.state, record.rejection_reason) == ("rejected", "for_sale")  # #281
    assert record.flagged_by is None
    (stored,) = store.userdata.find_reports(listing_id=store.active)
    assert (stored.status, stored.resolved_by, stored.resolved_at) == ("restored", ADMIN_ID, NOW)


def test_an_other_city_post_restores_to_other_city(ron: TestClient, store: AdminStore) -> None:
    report(store, store.ramat_gan, ["other_city"])
    restore(ron, (store.ramat_gan, version(ron, store.ramat_gan)))
    record = lifecycle(store, store.ramat_gan)
    assert (record.state, record.rejection_reason) == ("rejected", "other_city")  # #214


def test_an_archived_post_stays_archived_its_reason_re_derived(ron: TestClient, store: AdminStore):
    stored = lifecycle(store, store.archived)
    flagged = {"rejection_reason": "flagged", "flagged_by": ADMIN_ID, "flagged_at": NOW}
    overwrite_lifecycle(store.repository, stored.model_copy(update=flagged))
    assert detail(ron, store.archived)["restore_preview"]["state"] == "archived"
    restore(ron, (store.archived, version(ron, store.archived)))
    record = lifecycle(store, store.archived)
    assert (record.state, record.rejection_reason, record.flagged_by) == ("archived", None, None)


def test_a_post_with_nothing_to_restore_is_refused(ron: TestClient, store: AdminStore) -> None:
    results = restore(ron, (store.rejected, version(ron, store.rejected))).json()["results"]
    assert results == [{"listing_id": store.rejected, "outcome": "not_restorable", "state": None}]


def test_an_unfinished_restore_is_marked_and_finished_by_running_it_again(
    ron: TestClient, store: AdminStore, site
) -> None:
    report(store, store.active, ["price"])
    seen = version(ron, store.active)
    shaky_site = dataclasses.replace(site, posts=AnotherWriterFirst(site.posts))
    shaky = TestClient(create_app(shaky_site), base_url=ORIGIN, cookies=ron.cookies)
    results = restore(shaky, (store.active, seen)).json()["results"]
    assert results[0]["outcome"] == "changed"  # the reports first (#392), then the record failed
    unfinished = detail(ron, store.active)
    assert unfinished["marks"] == ["restore_unfinished"]
    assert [r["status"] for r in unfinished["reports"]] == ["restored"]
    finished = restore(ron, (store.active, unfinished["version"])).json()["results"]
    assert finished == [{"listing_id": store.active, "outcome": "restored", "state": "active"}]
    assert detail(ron, store.active)["marks"] == []


# --- 7. leave out, then restore later (#286) ---


def test_leave_out_keeps_the_post_rejected_and_a_restore_later_brings_it_back(
    ron: TestClient, store: AdminStore
) -> None:
    report(store, store.active, ["rooms"])
    left = post_write(ron, "/api/admin/leave-out/{id}", store.active)
    assert left.status_code == 200
    assert [r["status"] for r in left.json()["reports"]] == ["left_out"]
    record = lifecycle(store, store.active)
    assert (record.state, record.rejection_reason) == ("rejected", "misclassified")  # kept (#255)
    again = post_write(ron, "/api/admin/leave-out/{id}", store.active, left.json()["version"])
    assert (again.status_code, again.json()) == (409, {"refusal": "no_open_report"})
    restore(ron, (store.active, left.json()["version"]))
    assert lifecycle(store, store.active).state == "active"
    (stored,) = store.userdata.find_reports(listing_id=store.active)
    assert stored.status == "restored"


# --- 8. remove the post from the list (3.4 point 3, #402) ---


def test_a_report_whose_post_stayed_is_applied_with_the_first_reporter(
    ron: TestClient, store: AdminStore, site
) -> None:
    friend(store)
    dana = store.userdata.find_user_by_username("dana")
    first = a_report(store.active, ["price"], n=1).model_copy(update={"reported_by": dana.user_id})
    store.userdata.add_report(first)
    later = a_report(store.active, ["rooms"], n=2).model_copy(
        update={"reported_at": NOW.replace(hour=10)}
    )
    store.userdata.add_report(later)
    assert detail(ron, store.active)["marks"] == ["not_removed"]
    answer = post_write(ron, "/api/admin/apply-reports/{id}", store.active)
    assert answer.status_code == 200 and answer.json()["marks"] == []
    record = lifecycle(store, store.active)
    assert (record.state, record.rejection_reason) == ("rejected", "misclassified")
    assert (record.flagged_by, record.flagged_at) == (dana.user_id, NOW)  # the earliest (#280)
    guest = client_of(site)
    assert store.active not in {c["id"] for c in guest.get("/api/cards").json()["cards"]}
    path = "/api/admin/apply-reports/{id}"
    refused = post_write(ron, path, store.active, answer.json()["version"])
    assert (refused.status_code, refused.json()) == (409, {"refusal": "not_applicable"})


# --- 9. corrections (#256, #284, #395, #404, #405) ---

VALUES = [
    ("post_nature", "sublet_offer"),
    ("apartment_kind", {"state": "written", "value": "room"}),
    ("price", {"state": "written", "value": [4500, 4800]}),
    ("price", {"state": "not_written", "value": None}),
    ("entry_date", {"state": "written", "value": "2026-11-01"}),
    ("entry_date", {"state": "written", "value": "immediate"}),
    ("rooms", {"state": "written", "value": 3.5}),
    ("floor", {"state": "written", "value": -1}),
    ("building_floors", {"state": "unclear", "value": None}),
    ("size_sqm", {"state": "written", "value": 72.0}),
    ("room_size_sqm", {"state": "not_written", "value": None}),
    ("broker", {"state": "written", "value": False}),
    ("balcony", {"state": "written", "value": True}),
    ("parking", {"state": "not_written", "value": None}),
    ("elevator", {"state": "written", "value": True}),
    ("air_conditioning", {"state": "written", "value": True}),
    ("furnished", {"state": "written", "value": "partial"}),
    ("arnona", {"state": "written", "value": 450}),
    ("house_committee", {"state": "written", "value": "included"}),
    ("gender", "women_only"),
    ("areas", [30, 31]),
    ("streets", ["דיזנגוף"]),
    ("other_city", "חולון"),
    ("phone_names", [{"phone": "0541234567", "name": "דנה"}]),
]


@pytest.mark.parametrize(("field", "value"), VALUES)
def test_every_field_can_be_corrected_by_its_gate_b_type(
    ron: TestClient, store: AdminStore, field: str, value: Any
) -> None:
    made = report(store, store.active, [field])
    answer = correct(ron, store.active, field, value, made.report_id)
    assert answer.status_code == 200, answer.text
    (row,) = [f for f in answer.json()["fields"] if f["field"] == field]
    assert row["corrected"] is True and row["seen"] == value
    (stored,) = store.userdata.find_corrections(listing_id=store.active)
    listing = store.repository.get_listing(store.active)
    assert stored.model_value == getattr(listing, field)  # the model's value kept beside (#256)
    assert stored.report_id == made.report_id and stored.corrected_by == ADMIN_ID


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rooms", {"state": "written", "value": None}),
        ("rooms", {"state": "written", "value": 3.3}),
        ("areas", [99]),
        ("price", {"state": "written", "value": []}),
        ("gender", "men_only"),
    ],
)
def test_a_value_that_breaks_gate_b_is_422_and_nothing_is_written(
    ron: TestClient, store: AdminStore, field: str, value: Any
) -> None:
    made = report(store, store.active, [field])
    before = store.db.read_bytes()
    answer = correct(ron, store.active, field, value, made.report_id)
    assert answer.status_code == 422 and answer.json()["refusal"] == "invalid_value"
    assert store.db.read_bytes() == before


def test_a_correction_needs_a_report_of_the_post(ron: TestClient, store: AdminStore) -> None:
    answer = correct(ron, store.active, "rooms", {"state": "written", "value": 2.0}, "f" * 32)
    assert (answer.status_code, answer.json()) == (409, {"refusal": "no_report"})


def test_a_second_correction_replaces_the_first_and_a_removal_keeps_the_record(
    ron: TestClient, store: AdminStore
) -> None:
    made = report(store, store.active, ["rooms"])
    correct(ron, store.active, "rooms", {"state": "written", "value": 2.0}, made.report_id)
    correct(ron, store.active, "rooms", {"state": "written", "value": 2.5}, made.report_id)
    every = store.userdata.find_corrections(listing_id=store.active, in_force=False)
    pairs = sorted((c.corrected_value.value, c.in_force) for c in every)
    assert pairs == [(2.0, False), (2.5, True)]  # the old removed, the new in force (#404)
    (in_force,) = [c for c in every if c.in_force]
    path = f"/api/admin/corrections/{in_force.correction_id}/remove"
    removed = write(ron, "POST", path, {"version": version(ron, store.active)})
    assert removed.status_code == 200
    assert len(store.userdata.find_corrections(listing_id=store.active, in_force=False)) == 2
    assert store.userdata.find_corrections(listing_id=store.active) == []
    record = lifecycle(store, store.active)
    assert record.rejection_reason == "misclassified"  # not re-derived (#394)
    again = write(ron, "POST", path, {"version": removed.json()["version"]})
    assert (again.status_code, again.json()) == (409, {"refusal": "not_in_force"})


def test_a_correction_reaches_the_users_cards(ron: TestClient, store: AdminStore, site) -> None:
    friend(store)
    dana = store.userdata.find_user_by_username("dana")
    made = a_report(store.active, ["rooms"]).model_copy(update={"reported_by": dana.user_id})
    store.userdata.add_report(made)  # a report whose post stayed on the list
    correct(ron, store.active, "rooms", {"state": "written", "value": 4.5}, made.report_id)
    cards = client_of(site).post("/api/cards", json=bar()).json()["cards"]
    (card,) = [c for c in cards if c["id"] == store.active]
    assert card["rooms"] == {"state": "written", "value": 4.5}
    assert "rooms" in card["evaluation"]["corrected"]


# --- 11. the invariants, over every write ---


def test_no_admin_write_touches_a_raw_post_or_a_listing(ron: TestClient, store: AdminStore):
    before = {table: table_rows(store, table) for table in ("raw_posts", "listings")}
    made = report(store, store.active, ["rooms"])
    correct(ron, store.active, "rooms", {"state": "written", "value": 2.0}, made.report_id)
    post_write(ron, "/api/admin/leave-out/{id}", store.active)
    restore(ron, (store.active, version(ron, store.active)))
    flag(store, store.other)
    restore(ron, (store.other, version(ron, store.other)))
    assert lifecycle(store, store.other).state == "active"
    assert {table: table_rows(store, table) for table in ("raw_posts", "listings")} == before


WRITES = [
    ("/api/admin/retry/{id}", {"version": "v"}),
    ("/api/admin/restore", {"posts": [{"listing_id": "{id}", "version": "v"}]}),
    ("/api/admin/leave-out/{id}", {"version": "v"}),
    ("/api/admin/apply-reports/{id}", {"version": "v"}),
    (
        "/api/admin/corrections",
        {
            "listing_id": "{id}",
            "field": "rooms",
            "corrected_value": None,
            "report_id": "r",
            "version": "v",
        },
    ),
    ("/api/admin/corrections/{id}/remove", {"version": "v"}),
]


@pytest.mark.parametrize(("path", "body"), WRITES)
def test_every_post_write_is_the_admins_only(site, store: AdminStore, path: str, body: dict):
    friend(store)
    dana = client_of(site)
    assert sign_in(dana, "dana", FRIEND_PASSWORD).status_code == 200
    before = store.db.read_bytes()
    filled = path.format(id=store.active)
    assert write(client_of(site), "POST", filled, body).status_code == 401
    assert write(dana, "POST", filled, body).status_code == 403
    assert store.db.read_bytes() == before
