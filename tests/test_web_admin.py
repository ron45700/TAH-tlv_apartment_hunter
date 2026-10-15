"""The admin's pages, build steps 1 and 3 (`PHASE_3.md` 3.8 (i), (j); DECISIONS.md #389–#406):
test groups 1 (access), 2 (the lists), 3 (the city), 4 (the photos), the detail, the reports and the
corrections as read, 10 (keys and users) and 11 (the invariants), and the two derived marks.

Temporary stores only (`tests/test_web.py`'s `Store`: two active posts, one each rejected, pending,
archived, and a dedup A duplicate); every hash is made with `profiles.CHEAPEST`.
"""

import dataclasses
import logging
import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_correction, overwrite_lifecycle
from tests.test_gate_d import T0, add, make_member
from tests.test_userdata_store import ADMIN_ID
from tests.test_web import (
    NOW,
    PHOTO_BYTES,
    Store,
    _event_loop_self_pipe,  # noqa: F401  (#344: the same one exception)
)
from tests.test_web_accounts import (
    ADMIN_PASSWORD,
    FRIEND_PASSWORD,
    HASHER,
    ORIGIN,
    Clock,
    issue_key,
    sign_in,
    write,
)
from tlv_hunter.accounts import actions
from tlv_hunter.contracts.classification_report import (
    CLASSIFICATION_REPORT_SCHEMA_VERSION,
    ClassificationReport,
)
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.dedup.stage_b import PhotoHashes, load_key_posts
from tlv_hunter.postmodel.rejects import classified_lifecycle, report_marks
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.web.app import create_app, site_over

POST_TABLES = ("raw_posts", "listings", "post_lifecycle")
TEMPORARY = "temporary-pass-1"


class AdminStore(Store):
    """`Store`, plus a second rejected post (`for_sale`, a day newer) and an other-city post decided
    by Facebook's location field; the admin's password is real."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        newer = T0 + timedelta(days=1)
        for_sale = make_member(8, price=[4000], areas=[52], nature="for_sale", at=newer)
        add(self.repository, for_sale)
        self.for_sale = for_sale.listing_id
        self.ramat_gan = add_other_city(self, 9, native="רמת גן, מחוז תל אביב", model_city=None)
        actions.reset_admin_password(self.userdata, ADMIN_PASSWORD, NOW, hasher=HASHER)


def add_other_city(store: Store, n: int, *, native: str | None, model_city: str | None) -> str:
    member = make_member(n, price=[5000], areas=[30])
    post = member.post.with_changes(native_location=native)
    listing = member.listing.model_copy(update={"other_city": model_city})
    lifecycle = classified_lifecycle(initial_lifecycle(post), listing, post)
    assert lifecycle.rejection_reason == "other_city"
    changed = dataclasses.replace(member, post=post, listing=listing, lifecycle=lifecycle)
    add(store.repository, changed)
    return post.listing_id


@pytest.fixture
def store(tmp_path: Path) -> AdminStore:
    return AdminStore(tmp_path / "store")


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def site(store: AdminStore, clock: Clock):
    return site_over(store.db, store.root, clock=clock, hasher=HASHER)


def client_of(site) -> TestClient:
    return TestClient(create_app(site), base_url=ORIGIN)


@pytest.fixture
def ron(site) -> TestClient:
    client = client_of(site)
    assert sign_in(client).status_code == 200
    return client


def friend(store: Store, username: str = "dana") -> None:
    key = issue_key(store)
    actions.sign_up(store.userdata, key, username, FRIEND_PASSWORD, NOW, hasher=HASHER)


@pytest.fixture
def dana(site, store: AdminStore) -> TestClient:
    friend(store)
    client = client_of(site)
    assert sign_in(client, "dana", FRIEND_PASSWORD).status_code == 200
    return client


def posts(client: TestClient, name: str, **body: Any):
    return write(client, "POST", "/api/admin/posts", {"list": name, **body})


def row_ids(response) -> list[str]:
    return [row["id"] for row in response.json()["rows"]]


def table_rows(store: Store, table: str) -> list[tuple]:
    with closing(sqlite3.connect(store.db)) as conn:
        return conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()  # noqa: S608


def a_report(listing_id: str, fields: list[str], *, status: str = "open", n: int = 1):
    resolved = status != "open"
    return ClassificationReport(
        schema_version=CLASSIFICATION_REPORT_SCHEMA_VERSION,
        report_id=f"{n:032x}",
        listing_id=listing_id,
        reported_by=ADMIN_ID,
        reported_at=NOW,
        fields=fields,
        note="the price is per room",
        status=status,
        resolved_by=ADMIN_ID if resolved else None,
        resolved_at=NOW if resolved else None,
    )


def flag(store: Store, listing_id: str, *, reason: str = "flagged") -> None:
    stored = store.repository.get_lifecycle(listing_id)
    overwrite_lifecycle(
        store.repository,
        stored.model_copy(
            update={
                "state": "rejected",
                "rejection_reason": reason,
                "flagged_by": ADMIN_ID,
                "flagged_at": NOW,
                "flag_note": "fake" if reason == "flagged" else None,
            }
        ),
    )


# --- 1. access ---

READS = [
    ("GET", "/api/admin/summary", None),
    ("POST", "/api/admin/posts", {"list": "rejected"}),
    ("POST", "/api/admin/posts/by-id", {"list": "rejected", "ids": ["x"]}),
    ("GET", "/api/admin/posts/{rejected}", None),
    ("GET", "/api/admin/photos/{rejected}/a1.jpg", None),
    ("GET", "/api/admin/reports", None),
    ("GET", "/api/admin/corrections", None),
    ("GET", "/api/admin/keys", None),
    ("GET", "/api/admin/users", None),
]
WRITES = [
    ("POST", "/api/admin/keys", {"label": "for noa"}),
    ("POST", "/api/admin/keys/{key}/cancel", {}),
    ("POST", "/api/admin/users/dana/password", {"temporary_password": TEMPORARY}),
    ("POST", "/api/admin/users/dana/disable", {}),
    ("POST", "/api/admin/users/dana/enable", {}),
]


def call(client: TestClient, method: str, path: str, body: Any, store: AdminStore, key: str = "k"):
    path = path.format(rejected=store.rejected, key=key)
    return client.get(path) if method == "GET" else write(client, method, path, body)


@pytest.mark.parametrize(("method", "path", "body"), READS + WRITES)
def test_a_guest_gets_401_and_a_user_403_on_every_admin_route(
    site, store: AdminStore, dana: TestClient, method: str, path: str, body: Any
) -> None:
    before = store.db.read_bytes()
    assert call(client_of(site), method, path, body, store).status_code == 401
    assert call(dana, method, path, body, store).status_code == 403
    assert store.db.read_bytes() == before


@pytest.mark.parametrize(("method", "path", "body"), READS)
def test_the_admin_reads_every_route_and_not_while_a_password_change_is_due(
    ron: TestClient, store: AdminStore, method: str, path: str, body: Any
) -> None:
    assert call(ron, method, path, body, store).status_code == 200
    admin = store.userdata.get_user(ADMIN_ID)
    due = admin.model_copy(update={"must_change_password": True})
    store.userdata.save_user(due, expected=admin)
    assert call(ron, method, path, body, store).status_code == 403


def test_a_write_without_json_is_415_and_from_another_site_403(ron: TestClient) -> None:
    no_json = ron.post("/api/admin/keys", content="label=x", headers={"origin": ORIGIN})
    assert no_json.status_code == 415
    foreign = write(ron, "POST", "/api/admin/keys", {"label": "x"}, origin="https://evil.example")
    assert foreign.status_code == 403
    assert ron.get("/api/admin/keys").json() == {"keys": []}


# --- 2. the lists ---


def test_each_list_holds_its_canonicals_and_nothing_else(
    ron: TestClient, store: AdminStore
) -> None:
    rejected = posts(ron, "rejected")
    assert set(row_ids(rejected)) == {store.rejected, store.for_sale, store.ramat_gan}
    assert rejected.json()["reasons"] == {"seeking": 1, "for_sale": 1, "other_city": 1}
    assert row_ids(posts(ron, "pending")) == [store.pending]  # the duplicate is not a row (#75 B)
    assert row_ids(posts(ron, "archive")) == [store.archived]
    assert row_ids(posts(ron, "flags")) == []
    every = {i for name in ("rejected", "pending", "archive") for i in row_ids(posts(ron, name))}
    assert not every & {store.active, store.other, store.duplicate}


def test_the_reason_filter_and_the_order_newest_first(ron: TestClient, store: AdminStore) -> None:
    assert row_ids(posts(ron, "rejected", reason="seeking")) == [store.rejected]
    assert posts(ron, "rejected", reason="no_text").json()["count"] == 0
    assert posts(ron, "rejected").json()["order"][0] == store.for_sale  # a day newer (#403)


def test_paging_gives_the_whole_list_and_gone_for_an_id_not_in_it(
    ron: TestClient, store: AdminStore
) -> None:
    whole = posts(ron, "rejected").json()
    first = posts(ron, "rejected", first=1).json()
    assert first["order"] == whole["order"] and len(first["rows"]) == 1
    ids = [*first["order"][1:], store.active]
    rest = write(ron, "POST", "/api/admin/posts/by-id", {"list": "rejected", "ids": ids}).json()
    assert rest["rows"] == whole["rows"][1:]
    assert rest["gone"] == [store.active]
    assert posts(ron, "rejected", first=0).json() == {**whole, "order": [], "rows": []}
    assert posts(ron, "rejected", first=97).status_code == 422
    assert posts(ron, "accepted").status_code == 422


def test_a_row_carries_the_post_and_its_reason_in_words(ron: TestClient, store: AdminStore) -> None:
    (row,) = [r for r in posts(ron, "rejected").json()["rows"] if r["id"] == store.rejected]
    assert row["reason_words"] == "מחפשים דירה" and row["state"] == "rejected"
    assert row["photo"] == f"/api/admin/photos/{store.rejected}/a1.jpg"
    assert row["listing"]["post_nature"] == "seeking" and row["publications"] == 1
    (pending,) = posts(ron, "pending").json()["rows"]
    assert pending["listing"] is None and pending["failures"] == 0


def test_the_flags_list_groups_one_action_and_the_summary_counts_it(
    ron: TestClient, store: AdminStore
) -> None:
    flag(store, store.active)
    flag(store, store.other)
    flags = posts(ron, "flags").json()
    assert {r["id"] for r in flags["rows"]} == {store.active, store.other}
    assert {r["flag"]["by"] for r in flags["rows"]} == {"ron"}  # a username, never a user_id
    summary = ron.get("/api/admin/summary").json()
    assert (summary["flag_actions"], summary["flagged_posts"]) == (1, 2)
    assert (summary["rejected"], summary["pending"], summary["archive"]) == (5, 1, 1)


def test_others_are_read_in_the_same_pass_as_the_members(store: AdminStore) -> None:
    calls = []

    class Counting:
        def __getattr__(self, name: str) -> Any:
            if name == "query":
                calls.append(name)
            return getattr(store.repository, name)

    inputs = load_key_posts(Counting(), [], store.root, PhotoHashes())
    assert calls == ["query"]
    others = {o.listing_id for o in inputs.others}
    expected = {store.rejected, store.pending, store.archived, store.for_sale, store.ramat_gan}
    assert others == expected
    assert {m.listing_id for m in inputs.members} == {store.active, store.other}


def test_before_the_first_grouping_the_lists_answer_loading(store: AdminStore, clock) -> None:
    site = site_over(store.db, store.root, clock=clock, hasher=HASHER, background=True)
    client = client_of(site)
    assert sign_in(client).status_code == 200
    try:
        answer = posts(client, "rejected")
        assert answer.status_code == 503 and answer.json() == {"refusal": "loading"}
        assert client.get("/api/admin/users").status_code == 200  # no grouping needed
    finally:
        assert site.grouping.wait(30)


# --- 3. the city (#214, #296) ---


def test_the_city_by_the_location_field_by_the_model_and_by_a_correction(
    ron: TestClient, store: AdminStore
) -> None:
    holon = add_other_city(store, 10, native=None, model_city="חולון")
    corrected = add_other_city(store, 11, native=None, model_city="חולון")
    listing = store.repository.get_listing(corrected)
    store.userdata.add_correction(make_correction(listing, "other_city", "בת ים"))
    rows = posts(ron, "rejected", reason="other_city").json()["rows"]
    assert {r["id"]: r["city"] for r in rows} == {
        store.ramat_gan: "רמת גן",
        holon: "חולון",
        corrected: "בת ים",
    }
    detail = ron.get(f"/api/admin/posts/{corrected}").json()
    assert detail["city"] == {"name": "בת ים", "source": "correction"}
    ramat_gan = ron.get(f"/api/admin/posts/{store.ramat_gan}").json()
    assert ramat_gan["city"] == {"name": "רמת גן", "source": "native_location"}


# --- 4. the photos ---


def test_a_rejected_posts_photo_is_the_admins_only(
    ron: TestClient, dana: TestClient, store: AdminStore, site
) -> None:
    path = f"/api/admin/photos/{store.rejected}/a1.jpg"
    assert ron.get(path).content == PHOTO_BYTES
    assert dana.get(path).status_code == 403
    assert client_of(site).get(path).status_code == 401
    assert client_of(site).get(f"/api/photos/{store.rejected}/a1.jpg").status_code == 404
    for wrong in ("b2.jpg", "..%2F..%2Ftlv_hunter.sqlite3", "a1.jpg%00"):
        assert ron.get(f"/api/admin/photos/{store.rejected}/{wrong}").status_code == 404
    assert ron.get(f"/api/admin/photos/{store.active}/a1.jpg").status_code == 200
    assert ron.get(f"/api/admin/photos/{store.other}/a1.jpg").status_code == 404  # none stored


# --- the detail, read fresh ---


def test_the_detail_holds_the_record_the_fields_and_the_publications(
    ron: TestClient, store: AdminStore
) -> None:
    detail = ron.get(f"/api/admin/posts/{store.rejected}").json()
    assert detail["lifecycle"]["reason"] == "seeking" and detail["restore_preview"] is None
    assert len(detail["fields"]) == 22 and detail["fields"][0]["field"] == "post_nature"
    assert detail["fields"][0]["model"] == detail["fields"][0]["seen"] == "seeking"
    assert detail["classified"]["prompt_version"]
    active = ron.get(f"/api/admin/posts/{store.active}").json()
    published = sorted(p["id"] for p in active["publications"])
    assert published == sorted([store.active, store.duplicate])
    pending = ron.get(f"/api/admin/posts/{store.pending}").json()
    assert pending["fields"] == [] and pending["listing"] is None
    assert ron.get("/api/admin/posts/" + "f" * 64).status_code == 404


def test_the_detail_shows_what_a_restore_would_leave_and_reads_fresh(
    ron: TestClient, store: AdminStore
) -> None:
    ron.get("/api/admin/summary")  # the grouping held before the flag: the detail reads the store
    flag(store, store.active)
    detail = ron.get(f"/api/admin/posts/{store.active}").json()
    assert detail["lifecycle"]["flag"] == {"by": "ron", "at": NOW.isoformat(), "note": "fake"}
    assert detail["restore_preview"]["state"] == "active"  # #251, #406
    listing = store.repository.get_listing(store.active)
    store.userdata.add_correction(make_correction(listing, "post_nature", "for_sale"))
    corrected = ron.get(f"/api/admin/posts/{store.active}").json()
    assert corrected["restore_preview"] == {
        "state": "rejected",
        "state_words": "נדחתה",
        "reason": "for_sale",
        "reason_words": "למכירה",
    }
    (row,) = [f for f in corrected["fields"] if f["field"] == "post_nature"]
    assert (row["model"], row["seen"], row["corrected"]) == ("rental_offer", "for_sale", True)


# --- reports and corrections, as read ---


def test_reports_are_grouped_by_field_with_a_post_under_each(
    ron: TestClient, store: AdminStore
) -> None:
    store.userdata.add_report(a_report(store.other, ["price", "rooms"]))
    answer = ron.get("/api/admin/reports").json()
    assert (answer["count"], answer["posts"]) == (1, 1)
    assert [g["field"] for g in answer["groups"]] == ["price", "rooms"]
    entry = answer["groups"][0]["posts"][0]
    assert entry["listing_id"] == store.other and entry["post"]["id"] == store.other
    assert entry["reports"][0]["reporter"] == "ron"
    assert [f["label"] for f in entry["reports"][0]["fields"]] == ["מחיר", "מספר חדרים"]
    assert entry["marks"] == ["not_removed"]  # the post is still on the list (3.4 point 3)
    assert ron.get("/api/admin/reports?status=left_out").json()["groups"] == []
    assert ron.get("/api/admin/reports?status=closed").status_code == 422


def test_an_unfinished_restore_is_marked(ron: TestClient, store: AdminStore) -> None:
    flag(store, store.other, reason="misclassified")
    opened = store.userdata.add_report(a_report(store.other, ["price"]))
    restored = a_report(store.other, ["price"], status="restored")
    store.userdata.save_report(restored, expected=opened)
    restored = ron.get("/api/admin/reports?status=restored").json()
    assert restored["groups"][0]["posts"][0]["marks"] == ["restore_unfinished"]
    assert ron.get("/api/admin/summary").json()["restore_unfinished"] == 1


def test_corrections_in_force_and_removed(ron: TestClient, store: AdminStore) -> None:
    listing = store.repository.get_listing(store.active)
    rooms = {"state": "written", "value": 4.0}
    store.userdata.add_correction(make_correction(listing, "rooms", rooms))
    in_force = store.userdata.add_correction(make_correction(listing, "price", listing.price, n=2))
    removed = make_correction(listing, "price", listing.price, removed=True, n=2)
    store.userdata.save_correction(removed, expected=in_force)
    in_force = ron.get("/api/admin/corrections").json()["corrections"]
    assert [(c["field"], c["corrected_value"]["value"]) for c in in_force] == [("rooms", 4.0)]
    assert in_force[0]["corrected_by"] == "ron" and in_force[0]["post"]["id"] == store.active
    removed = ron.get("/api/admin/corrections?in_force=false").json()["corrections"]
    assert [c["field"] for c in removed] == ["price"] and removed[0]["removed_by"] == "ron"


# --- the two marks (pure) ---


def test_report_marks() -> None:
    record = PostLifecycle.model_validate(
        {
            "schema_version": 3,
            "listing_id": "p",
            "state": "active",
            "rejection_reason": None,
            "flagged_by": None,
            "flagged_at": None,
            "flag_note": None,
            "last_published_at": NOW,
            "images": [],
            "classification_failures": 0,
            "last_classification_error": None,
        }
    )
    reported = record.model_copy(
        update={
            "state": "rejected",
            "rejection_reason": "misclassified",
            "flagged_by": ADMIN_ID,
            "flagged_at": NOW,
        }
    )
    open_ = a_report("p", ["price"])
    restored = a_report("p", ["price"], status="restored", n=2)
    left_out = a_report("p", ["price"], status="left_out", n=3)
    assert report_marks(record, [open_]) == {"not_removed"}
    assert report_marks(reported, [open_]) == frozenset()
    assert report_marks(reported, [restored]) == {"restore_unfinished"}
    assert report_marks(reported, [restored, left_out]) == frozenset()
    assert report_marks(record, [a_report("q", ["price"])]) == frozenset()  # another post's


# --- 10. keys and users ---


def test_a_key_is_shown_once_and_signs_a_friend_up(ron: TestClient, site) -> None:
    issued = write(ron, "POST", "/api/admin/keys", {"label": "  for noa  "})
    assert issued.status_code == 200 and issued.headers["cache-control"] == "no-store"
    body = issued.json()
    key = body.pop("key")
    assert body["label"] == "for noa" and body["state"] == "usable"
    listed = ron.get("/api/admin/keys")
    assert key not in listed.text and "key_hash" not in listed.text
    assert "key" not in listed.json()["keys"][0]
    sign_up = {"key": key, "username": "noa", "password": "pw-noa-12"}
    assert write(client_of(site), "POST", "/api/sign-up", sign_up).status_code == 200
    (used,) = ron.get("/api/admin/keys").json()["keys"]
    assert (used["state"], used["used_by"]) == ("used", "noa")
    users = ron.get("/api/admin/users").json()["users"]
    assert [(u["username"], u["key_label"]) for u in users] == [("ron", None), ("noa", "for noa")]


def test_a_key_needs_a_label_and_a_cancelled_key_is_refused_at_sign_up(
    ron: TestClient, site
) -> None:
    empty = write(ron, "POST", "/api/admin/keys", {"label": "   "})
    assert (empty.status_code, empty.json()) == (422, {"refusal": "label_empty"})
    issued = write(ron, "POST", "/api/admin/keys", {"label": "for noa"}).json()
    cancelled = write(ron, "POST", f"/api/admin/keys/{issued['key_id']}/cancel")
    assert cancelled.json()["state"] == "cancelled"
    again = write(ron, "POST", f"/api/admin/keys/{issued['key_id']}/cancel")
    assert again.json()["cancelled_at"] == cancelled.json()["cancelled_at"]  # stays (#266)
    sign_up = {"key": issued["key"], "username": "noa", "password": "pw-noa-12"}
    assert write(client_of(site), "POST", "/api/sign-up", sign_up).status_code == 403
    assert write(ron, "POST", "/api/admin/keys/unknown/cancel").status_code == 404


def test_a_used_key_cannot_be_cancelled(ron: TestClient, store: AdminStore) -> None:
    friend(store)
    (used,) = ron.get("/api/admin/keys").json()["keys"]
    refused = write(ron, "POST", f"/api/admin/keys/{used['key_id']}/cancel")
    assert (refused.status_code, refused.json()) == (409, {"refusal": "key_used"})


def test_a_reset_ends_the_sessions_and_asks_a_new_password(
    ron: TestClient, dana: TestClient, site
) -> None:
    path = "/api/admin/users/{}/password"
    short = write(ron, "POST", path.format("dana"), {"temporary_password": "short"})
    assert (short.status_code, short.json()) == (422, {"refusal": "password_too_short"})
    reset = write(ron, "POST", path.format("dana"), {"temporary_password": TEMPORARY})
    assert reset.status_code == 200 and reset.json()["must_change_password"] is True
    assert dana.get("/api/profile").status_code == 401  # every session ended (#263)
    again = client_of(site)
    assert sign_in(again, "dana", TEMPORARY).json()["user"]["must_change_password"] is True
    assert again.get("/api/profile").status_code == 403  # only the change (Gate C)
    own = write(ron, "POST", path.format("ron"), {"temporary_password": TEMPORARY})
    assert (own.status_code, own.json()) == (403, {"refusal": "admin_row"})
    nobody = write(ron, "POST", path.format("nobody"), {"temporary_password": TEMPORARY})
    assert nobody.status_code == 404


def test_disable_ends_the_sessions_enable_lets_the_user_back(
    ron: TestClient, dana: TestClient, site
) -> None:
    disabled = write(ron, "POST", "/api/admin/users/dana/disable")
    assert disabled.status_code == 200 and disabled.json()["disabled_at"] == NOW.isoformat()
    assert dana.get("/api/profile").status_code == 401
    assert sign_in(client_of(site), "dana", FRIEND_PASSWORD).json() == {"refusal": "disabled"}
    enabled = write(ron, "POST", "/api/admin/users/dana/enable")
    assert enabled.json()["disabled_at"] is None
    assert sign_in(client_of(site), "dana", FRIEND_PASSWORD).status_code == 200
    admin = write(ron, "POST", "/api/admin/users/ron/disable")
    assert (admin.status_code, admin.json()) == (403, {"refusal": "admin_cannot_be_disabled"})
    assert write(ron, "POST", "/api/admin/users/nobody/disable").status_code == 404


# --- 11. the invariants ---


def test_no_admin_route_writes_a_post_and_no_secret_leaves(
    ron: TestClient, store: AdminStore, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    friend(store)
    before = {table: table_rows(store, table) for table in POST_TABLES}
    texts = [call(ron, method, path, body, store).text for method, path, body in READS]
    issued = write(ron, "POST", "/api/admin/keys", {"label": "for noa"}).json()
    for method, path, body in WRITES[1:]:
        texts.append(call(ron, method, path, body, store, key=issued["key_id"]).text)
    assert {table: table_rows(store, table) for table in POST_TABLES} == before  # 14, 12
    for secret in (issued["key"], TEMPORARY, ADMIN_PASSWORD, FRIEND_PASSWORD, "$argon2"):
        assert all(secret not in text for text in texts), secret
        assert secret not in caplog.text, secret
    joined = "".join(texts)
    assert ADMIN_ID not in joined and "user_id" not in joined and "password_hash" not in joined
