"""The writes a user makes on a card (`PHASE_3.md` 3.7 (i), (l) group 7, build step 6): viewed and
not viewed, the "lied" flag on every member (#300) by compare and set (#260) with a partial answer
on a conflict (#330 point 21), the report on the shown post only (#254, #278–#280), a stale page's
409, a guest's 401, and invariants 12 and 14 after every write.

Temporary stores only (`tests/test_web.py`'s `Store`, plus a second post tied to its first by the
Gate D key, so one card holds two members); every hash is made with `profiles.CHEAPEST`.
"""

import dataclasses
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AnotherWriterFirst, overwrite_lifecycle
from tests.test_gate_d import add, make_member
from tests.test_userdata_store import ADMIN_ID
from tests.test_web import (
    NOW,
    Store,
    _event_loop_self_pipe,  # noqa: F401  (#344: the same one exception)
    bar,
)
from tests.test_web_accounts import ADMIN_PASSWORD, HASHER, ORIGIN, Clock, sign_in, write
from tlv_hunter.accounts import actions
from tlv_hunter.contracts.classification_report import NOTE_LIMIT
from tlv_hunter.web.app import create_app, site_over
from tlv_hunter.web.writes import flag_card

POST_TABLES = ("raw_posts", "listings")


class TiedStore(Store):
    """`Store`, plus `tied`: a second post the Gate D key ties to `active` (the same phone, price,
    rooms and area; another text), so their card has two members."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        tied = make_member(7, price=[5000], rooms=3.0, areas=[30], phone="054-123-4567")
        add(self.repository, tied)
        self.tied = tied.listing_id
        actions.reset_admin_password(self.userdata, ADMIN_PASSWORD, NOW, hasher=HASHER)


@pytest.fixture
def store(tmp_path: Path) -> TiedStore:
    return TiedStore(tmp_path / "store")


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def site(store: TiedStore, clock: Clock):
    return site_over(store.db, store.root, clock=clock, hasher=HASHER)


def client_of(site) -> TestClient:
    return TestClient(create_app(site), base_url=ORIGIN)


@pytest.fixture
def guest(site) -> TestClient:
    return client_of(site)


@pytest.fixture
def ron(site) -> TestClient:
    client = client_of(site)
    assert sign_in(client).status_code == 200
    return client


def with_posts(site, posts, ron: TestClient) -> TestClient:
    """Ron's session on the same site, its post writes going through `posts`."""
    app = create_app(dataclasses.replace(site, posts=posts))
    return TestClient(app, base_url=ORIGIN, cookies=ron.cookies)


def the_two_post_card(client: TestClient, store: TiedStore) -> dict:
    cards = client.post("/api/cards", json=bar()).json()["cards"]
    (card,) = [card for card in cards if store.active in card["post_ids"]]
    assert {store.active, store.tied, store.duplicate} == set(card["post_ids"])
    return card


def card_members(store: TiedStore, card: dict) -> tuple[str, str]:
    """The card's two members in `canonical_ids`' order: `posted_at` (equal here), `listing_id`."""
    first, second = sorted((store.active, store.tied))
    assert card["id"] == first
    return first, second


def rows(store: TiedStore, table: str) -> list[tuple]:
    with closing(sqlite3.connect(store.db)) as conn:
        return conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()  # noqa: S608


def lifecycle_docs(store: TiedStore) -> dict[str, str]:
    return dict(rows(store, "post_lifecycle"))


def viewed_at(store: TiedStore, listing_id: str) -> datetime:
    with closing(sqlite3.connect(store.db)) as conn:
        (value,) = conn.execute(
            "SELECT json_extract(doc, '$.viewed_at') FROM viewed_posts WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
    return datetime.fromisoformat(value)


# --- a guest ---

CARD_WRITES = [
    ("POST", "/api/viewed/{id}", {}),
    ("DELETE", "/api/viewed/{id}", {}),
    ("POST", "/api/hidden/{id}", {}),
    ("DELETE", "/api/hidden/{id}", {}),
    ("POST", "/api/flag/{id}", {}),
    ("POST", "/api/report/{id}", {"fields": ["price"]}),
]


@pytest.mark.parametrize(("method", "path", "body"), CARD_WRITES)
def test_a_guest_gets_401_on_every_card_write_and_nothing_is_written(
    guest: TestClient, store: TiedStore, method: str, path: str, body: dict
) -> None:
    guest.get("/api/cards")
    before = store.db.read_bytes()
    response = write(guest, method, path.format(id=store.active), body)
    assert response.status_code == 401
    assert store.db.read_bytes() == before


def test_a_guests_cards_carry_no_viewed_field_and_a_users_do(
    guest: TestClient, ron: TestClient
) -> None:
    assert all("viewed" not in card for card in guest.get("/api/cards").json()["cards"])
    assert all(card["viewed"] is False for card in ron.get("/api/cards").json()["cards"])


# --- viewed and not viewed (#62, #253, #276) ---


def test_opening_marks_the_shown_post_and_keeps_the_first_time(
    ron: TestClient, store: TiedStore, clock: Clock
) -> None:
    card = the_two_post_card(ron, store)
    _, second = card_members(store, card)
    # opened through a member that is not the shown post: the mark is the shown post's (#276)
    assert write(ron, "POST", f"/api/viewed/{second}").json() == {"viewed": True}
    assert store.userdata.viewed_listing_ids(ADMIN_ID) == {card["id"]}
    clock.now = NOW + timedelta(hours=2)
    write(ron, "POST", f"/api/viewed/{card['id']}")
    assert viewed_at(store, card["id"]) == NOW


def test_a_viewed_card_is_marked_and_listed_after_the_unviewed(
    ron: TestClient, store: TiedStore
) -> None:
    before = ron.get("/api/cards").json()["cards"]
    assert len(before) == 2
    first = before[0]["id"]
    write(ron, "POST", f"/api/viewed/{first}")
    cards = ron.get("/api/cards").json()["cards"]
    assert [c["id"] for c in cards] == [before[1]["id"], first]  # the first goes last (#62)
    assert (cards[0]["viewed"], cards[1]["viewed"]) == (False, True)


def test_not_viewed_removes_the_marks_on_every_post_of_the_card(
    ron: TestClient, store: TiedStore
) -> None:
    the_two_post_card(ron, store)
    for listing_id in (store.active, store.tied, store.duplicate):  # a mark on any post (#253)
        store.userdata.mark_viewed(ADMIN_ID, listing_id, NOW)
    store.userdata.mark_viewed(ADMIN_ID, store.other, NOW)  # another card: kept
    assert write(ron, "DELETE", f"/api/viewed/{store.duplicate}").json() == {"viewed": False}
    assert store.userdata.viewed_listing_ids(ADMIN_ID) == {store.other}


# --- hiding (#464–#466, #468; PHASE_4.md appendix A, points 8–15) ---

TEMPORARY = {**bar(), "include_sublets": True}  # not the saved preferences; shows the same cards


def hidden_at(store: TiedStore, listing_id: str) -> datetime:
    with closing(sqlite3.connect(store.db)) as conn:
        (value,) = conn.execute(
            "SELECT json_extract(doc, '$.hidden_at') FROM hidden_posts WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
    return datetime.fromisoformat(value)


def test_hide_marks_the_shown_post_and_keeps_the_first_time(
    ron: TestClient, store: TiedStore, clock: Clock
) -> None:
    card = the_two_post_card(ron, store)
    _, second = card_members(store, card)
    assert write(ron, "POST", f"/api/hidden/{second}").json() == {"hidden": True}
    assert store.userdata.hidden_listing_ids(ADMIN_ID) == {card["id"]}
    clock.now = NOW + timedelta(hours=2)
    write(ron, "POST", f"/api/hidden/{card['id']}")
    assert hidden_at(store, card["id"]) == NOW
    assert store.userdata.viewed_listing_ids(ADMIN_ID) == set()  # hiding is not viewing


def test_on_the_saved_preferences_a_hidden_card_leaves_the_list_and_the_count(
    ron: TestClient, store: TiedStore
) -> None:
    before = ron.post("/api/cards", json=bar()).json()
    assert (before["count"], before["hiding"], before["hidden_count"]) == (2, True, 0)
    card = the_two_post_card(ron, store)
    write(ron, "POST", f"/api/hidden/{card['id']}")
    after = ron.post("/api/cards", json=bar()).json()
    assert (after["count"], after["hiding"], after["hidden_count"]) == (1, True, 1)
    assert card["id"] not in after["order"] and all(not c["hidden"] for c in after["cards"])


def test_shown_hidden_cards_keep_their_place_with_the_switch_or_a_temporary_filter(
    ron: TestClient, store: TiedStore
) -> None:
    order = ron.post("/api/cards", json=bar()).json()["order"]
    card = the_two_post_card(ron, store)
    write(ron, "POST", f"/api/hidden/{card['id']}")
    switched = ron.post("/api/cards", json={**bar(), "show_hidden": True}).json()
    assert switched["order"] == order and switched["count"] == 2  # point 14: its own place
    assert switched["hiding"] and switched["hidden_count"] == 1
    assert {c["id"]: c["hidden"] for c in switched["cards"]}[card["id"]] is True
    temporary = ron.post("/api/cards", json=TEMPORARY).json()
    assert (temporary["count"], temporary["hiding"], temporary["hidden_count"]) == (2, False, 1)
    assert temporary["order"] == order  # #465: a temporary filter shows everything


def test_a_mark_on_any_post_of_a_grouped_card_hides_it(ron: TestClient, store: TiedStore) -> None:
    """Point 11: as viewed (#253), so a later publication grouped into the card keeps it hidden."""
    card = the_two_post_card(ron, store)
    _, second = card_members(store, card)
    store.userdata.hide(ADMIN_ID, second, NOW)  # the mark on the member that is not shown
    listed = ron.post("/api/cards", json=bar()).json()
    assert card["id"] not in listed["order"] and listed["hidden_count"] == 1


def test_unhide_removes_the_marks_on_every_post_of_the_card(
    ron: TestClient, store: TiedStore
) -> None:
    the_two_post_card(ron, store)
    for listing_id in (store.active, store.tied, store.duplicate):
        store.userdata.hide(ADMIN_ID, listing_id, NOW)
    store.userdata.hide(ADMIN_ID, store.other, NOW)  # another card: kept
    assert write(ron, "DELETE", f"/api/hidden/{store.duplicate}").json() == {"hidden": False}
    assert store.userdata.hidden_listing_ids(ADMIN_ID) == {store.other}


def test_a_later_page_leaves_a_card_hidden_meanwhile_only_on_the_saved_preferences(
    ron: TestClient, store: TiedStore
) -> None:
    card = the_two_post_card(ron, store)
    write(ron, "POST", f"/api/hidden/{card['id']}")
    asked = {"bar": bar(), "ids": [card["id"]]}
    assert ron.post("/api/cards/by-id", json=asked).json()["gone"] == [card["id"]]
    shown = ron.post("/api/cards/by-id", json={**asked, "show_hidden": True}).json()
    assert shown["gone"] == [] and shown["cards"][0]["hidden"] is True
    temporary = ron.post("/api/cards/by-id", json={"bar": TEMPORARY, "ids": [card["id"]]}).json()
    assert temporary["gone"] == [] and temporary["cards"][0]["hidden"] is True


def test_a_guest_has_no_hiding(guest: TestClient, store: TiedStore) -> None:
    store.userdata.hide(ADMIN_ID, store.active, NOW)  # the admin's mark hides nothing for a guest
    listed = guest.post("/api/cards", json=bar()).json()
    assert "hiding" not in listed and "hidden_count" not in listed and listed["count"] == 2
    assert all("hidden" not in card for card in listed["cards"])


# --- the "lied" flag on every member (#300) ---


class Recording:
    """The site's writable Repository, recording each lifecycle write and what it expected."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.calls: list[tuple[str, object]] = []

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    def save_lifecycle(self, record, *, expected):
        self.calls.append((record.listing_id, expected))
        return self._inner.save_lifecycle(record, expected=expected)


def test_a_flag_on_a_two_post_card_writes_both_with_expected(
    ron: TestClient, site, store: TiedStore
) -> None:
    card = the_two_post_card(ron, store)
    first, second = card_members(store, card)
    recording = Recording(site.posts)
    client = with_posts(site, recording, ron)
    read = {i: store.repository.get_lifecycle(i) for i in (first, second)}
    response = write(client, "POST", f"/api/flag/{card['id']}", {"note": "the photos are fake"})
    assert response.json() == {"flagged": 2, "of": 2, "remaining": []}
    assert recording.calls == [(first, read[first]), (second, read[second])]
    for listing_id in (first, second):
        stored = store.repository.get_lifecycle(listing_id)
        assert (stored.state, stored.rejection_reason) == ("rejected", "flagged")
        assert (stored.flagged_by, stored.flagged_at) == (ADMIN_ID, NOW)
        assert stored.flag_note == "the photos are fake"
    assert store.repository.get_lifecycle(store.duplicate).state == "pending"  # not a member
    listed = {c["id"] for c in client.post("/api/cards", json=bar()).json()["cards"]}
    assert not listed & {first, second}  # the counter moved: the card left the list


def test_a_flag_that_meets_another_writer_once_reads_again_and_writes(
    ron: TestClient, site, store: TiedStore
) -> None:
    card = the_two_post_card(ron, store)
    client = with_posts(site, AnotherWriterFirst(site.posts, times=1), ron)
    assert write(client, "POST", f"/api/flag/{card['id']}").json()["flagged"] == 2


def test_a_conflict_on_one_member_gives_the_partial_answer_and_a_retry_finishes(
    ron: TestClient, site, store: TiedStore
) -> None:
    card = the_two_post_card(ron, store)
    first, second = card_members(store, card)
    # another writer changes the first member before each of its two attempts
    client = with_posts(site, AnotherWriterFirst(site.posts, times=2), ron)
    answer = write(client, "POST", f"/api/flag/{card['id']}").json()
    assert answer == {"flagged": 1, "of": 2, "remaining": [first]}
    assert store.repository.get_lifecycle(first).state == "active"
    assert store.repository.get_lifecycle(second).rejection_reason == "flagged"
    retry = write(ron, "POST", f"/api/flag/{answer['remaining'][0]}").json()
    assert retry == {"flagged": 1, "of": 1, "remaining": []}
    assert store.repository.get_lifecycle(first).rejection_reason == "flagged"


def test_a_member_no_longer_active_is_skipped(site, store: TiedStore) -> None:
    (card,) = [c for c in site.grouping.current().snapshot.cards if store.active in c.post_ids]
    first, second = card.canonical_ids
    stored = store.repository.get_lifecycle(second)
    overwrite_lifecycle(
        store.repository,
        stored.model_copy(update={"state": "rejected", "rejection_reason": "other_city"}),
    )
    result = flag_card(site.posts, card, ADMIN_ID, NOW, None)
    assert (result.written, result.not_written) == ((first,), (second,))
    assert store.repository.get_lifecycle(second).rejection_reason == "other_city"


# --- the report on the shown post only (#254, #278–#280, #300) ---


def test_a_report_writes_the_shown_post_only(ron: TestClient, store: TiedStore) -> None:
    card = the_two_post_card(ron, store)
    first, second = card_members(store, card)
    body = {"fields": ["price", "rooms"], "note": "המחיר הוא לחדר"}
    response = write(ron, "POST", f"/api/report/{second}", body)  # through the other member
    assert response.json() == {"removed": True}
    (report,) = store.userdata.find_reports()
    assert (report.listing_id, report.reported_by, report.status) == (first, ADMIN_ID, "open")
    assert (report.fields, report.note) == (["price", "rooms"], body["note"])
    assert report.reported_at == NOW
    shown = store.repository.get_lifecycle(first)
    assert (shown.state, shown.rejection_reason, shown.flagged_by, shown.flagged_at) == (
        "rejected",
        "misclassified",
        ADMIN_ID,
        NOW,
    )
    assert store.repository.get_lifecycle(second).state == "active"


def test_a_report_whose_lifecycle_write_fails_stays_and_a_second_is_refused(
    ron: TestClient, site, store: TiedStore
) -> None:
    card = the_two_post_card(ron, store)
    client = with_posts(site, AnotherWriterFirst(site.posts, times=2), ron)
    answer = write(client, "POST", f"/api/report/{card['id']}", {"fields": ["areas"]})
    assert answer.json() == {"removed": False}  # the report stays; the admin will handle it
    assert len(store.userdata.find_reports(card["id"], "open")) == 1
    assert store.repository.get_lifecycle(card["id"]).state == "active"
    again = write(ron, "POST", f"/api/report/{card['id']}", {"fields": ["price"]})
    assert (again.status_code, again.json()) == (409, {"refusal": "already_reported"})
    assert len(store.userdata.find_reports()) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"fields": []},
        {"fields": ["price", "price"]},
        {"fields": ["colour"]},
        {"fields": ["price"], "note": "x" * (NOTE_LIMIT + 1)},
        {"fields": "price"},
        {"fields": ["price"], "extra": 1},
    ],
)
def test_an_invalid_report_is_422_and_writes_nothing(
    ron: TestClient, store: TiedStore, body: dict
) -> None:
    card = the_two_post_card(ron, store)
    before = lifecycle_docs(store)
    assert write(ron, "POST", f"/api/report/{card['id']}", body).status_code == 422
    assert store.userdata.find_reports() == [] and lifecycle_docs(store) == before


def test_a_note_of_exactly_the_limit_is_accepted(ron: TestClient, store: TiedStore) -> None:
    card = the_two_post_card(ron, store)
    body = {"fields": ["price"], "note": "א" * NOTE_LIMIT}
    assert write(ron, "POST", f"/api/report/{card['id']}", body).status_code == 200


# --- a stale page (3.7 (i)) ---


@pytest.mark.parametrize(("method", "path", "body"), CARD_WRITES)
def test_a_write_on_a_post_no_longer_in_a_current_card_is_409_gone(
    ron: TestClient, store: TiedStore, method: str, path: str, body: dict
) -> None:
    for listing_id in (store.rejected, store.pending, store.archived, "nobody"):
        response = write(ron, method, path.format(id=listing_id), body)
        assert (response.status_code, response.json()) == (409, {"refusal": "gone"})


def test_a_flagged_card_is_gone_for_the_next_write(ron: TestClient, store: TiedStore) -> None:
    card = the_two_post_card(ron, store)
    write(ron, "POST", f"/api/flag/{card['id']}")
    for method, path, body in CARD_WRITES:
        assert write(ron, method, path.format(id=card["id"]), body).status_code == 409


# --- invariants 14 and 12 after every write ---


def test_no_rawpost_or_listing_changes_and_nothing_per_user_reaches_the_post_tables(
    ron: TestClient, store: TiedStore
) -> None:
    card = the_two_post_card(ron, store)
    first, second = card_members(store, card)
    posts_before = {table: rows(store, table) for table in POST_TABLES}
    lifecycles_before = lifecycle_docs(store)

    write(ron, "POST", f"/api/viewed/{first}")
    write(ron, "DELETE", f"/api/viewed/{first}")
    write(ron, "POST", f"/api/hidden/{first}")
    write(ron, "DELETE", f"/api/hidden/{first}")
    assert lifecycle_docs(store) == lifecycles_before  # viewed and hidden: user data only (#62)
    write(ron, "POST", f"/api/report/{store.other}", {"fields": ["rooms"], "note": "x"})
    write(ron, "POST", f"/api/flag/{first}")

    for table in POST_TABLES:  # invariant 14: byte-identical
        assert rows(store, table) == posts_before[table]
    after = lifecycle_docs(store)
    changed = {i for i in after if after[i] != lifecycles_before[i]}
    assert changed == {first, second, store.other}
    for listing_id in changed:  # invariant 12: the user only in Gate E's `flagged_by`
        assert store.repository.get_lifecycle(listing_id).flagged_by == ADMIN_ID
        assert after[listing_id].count(ADMIN_ID) == 1
    for table in POST_TABLES:
        assert all(ADMIN_ID not in str(row) for row in rows(store, table))
