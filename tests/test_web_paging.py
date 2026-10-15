"""A, the list in pages (#376–#378), and D, the grouping in the background (#379, #380):
`PHASE_3.md` 3.7 (l), "Plan for A", "Plan for D". Temporary stores only; the socket guard stays
on (`tests/test_web.py`'s loopback pair, on Windows only)."""

import dataclasses
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import overwrite_lifecycle
from tests.test_gate_d import add, make_member
from tests.test_web import NOW, bar
from tests.test_web import _event_loop_self_pipe as _event_loop_self_pipe  # noqa: F401
from tests.test_web_accounts import ORIGIN, sign_in, write
from tests.test_web_writes import HASHER, TiedStore, client_of
from tlv_hunter.dedup.stage_b import derive_cards
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.web.app import create_app, site_over
from tlv_hunter.web.filters import FIRST_CARDS, MOST_BY_ID
from tlv_hunter.web.grouping import Grouping, NotReady

EXTRA = 60  # with the store's own, more cards than one page


class ManyStore(TiedStore):
    """`TiedStore` (a two-post card, other single cards, hidden posts) and 60 more single cards."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        for n in range(EXTRA):
            add(self.repository, make_member(100 + n, price=[3000 + 10 * n], rooms=2.0, areas=[52]))


@pytest.fixture
def store(tmp_path: Path) -> ManyStore:
    return ManyStore(tmp_path / "store")


@pytest.fixture
def site(store: ManyStore):
    return site_over(store.db, store.root, clock=lambda: NOW, hasher=HASHER)


@pytest.fixture
def guest(site) -> TestClient:
    return client_of(site)


@pytest.fixture
def ron(site) -> TestClient:
    client = client_of(site)
    assert sign_in(client).status_code == 200
    return client


def whole(client: TestClient, **body) -> dict:
    return client.post("/api/cards", json={**bar(), **body}).json()


# --- A: the first cards with the whole order (#376) ---


def test_the_first_answer_has_the_count_the_whole_order_and_the_first_48_cards(
    guest: TestClient,
) -> None:
    answer = whole(guest)
    assert answer["count"] == len(answer["order"]) > FIRST_CARDS
    assert len(answer["cards"]) == FIRST_CARDS
    assert [card["id"] for card in answer["cards"]] == answer["order"][:FIRST_CARDS]
    assert len(set(answer["order"])) == len(answer["order"])
    assert guest.get("/api/cards").json()["order"] == answer["order"]  # a new guest's list too


def test_the_order_is_the_one_the_whole_list_had(guest: TestClient) -> None:
    """`first` changes how many cards come whole, never the order."""
    everything = whole(guest, first=MOST_BY_ID)
    assert len(everything["cards"]) == everything["count"] <= MOST_BY_ID
    assert [card["id"] for card in everything["cards"]] == whole(guest)["order"]


def test_first_zero_is_the_count_alone(guest: TestClient) -> None:
    """The preferences page's live count (#378)."""
    answer = whole(guest, first=0)
    assert answer["count"] == whole(guest)["count"]
    assert answer["order"] == [] and answer["cards"] == []


@pytest.mark.parametrize("first", [-1, MOST_BY_ID + 1, "48", 1.5])
def test_a_first_out_of_bounds_is_422(guest: TestClient, first) -> None:
    assert guest.post("/api/cards", json={**bar(), "first": first}).status_code == 422


def test_a_later_page_is_the_same_cards_as_the_whole_list(guest: TestClient) -> None:
    everything = whole(guest, first=MOST_BY_ID)
    by_id = {card["id"]: card for card in everything["cards"]}
    rest = whole(guest)["order"][FIRST_CARDS:]
    answer = guest.post("/api/cards/by-id", json={"bar": bar(), "ids": rest}).json()
    assert answer["gone"] == []
    assert [card["id"] for card in answer["cards"]] == rest  # in the order asked
    assert answer["cards"] == [by_id[i] for i in rest]  # the glow, the tier, the colours alike


def test_a_later_page_reads_the_same_bar(guest: TestClient) -> None:
    """A bar that hides a card: by id it is `gone`, as it would not be listed."""
    three_or_more = {"min": 3.0, "max": None, "level": "critical"}
    narrow = bar(room__rooms=three_or_more, whole_apartment__rooms=three_or_more)
    listed = guest.post("/api/cards", json={**narrow, "first": MOST_BY_ID}).json()["order"]
    every = whole(guest)["order"]
    hidden = [i for i in every if i not in listed][:3]
    assert listed and len(hidden) == 3
    answer = guest.post("/api/cards/by-id", json={"bar": narrow, "ids": listed + hidden}).json()
    assert [card["id"] for card in answer["cards"]] == listed
    assert answer["gone"] == hidden


def test_any_post_of_a_card_finds_it_once(guest: TestClient, store: ManyStore) -> None:
    ids = [store.tied, store.duplicate, store.active, "f" * 64]
    answer = guest.post("/api/cards/by-id", json={"bar": bar(), "ids": ids}).json()
    assert len(answer["cards"]) == 1
    assert {store.active, store.tied, store.duplicate} <= set(answer["cards"][0]["post_ids"])
    assert answer["gone"] == ["f" * 64]


@pytest.mark.parametrize(
    "body",
    [
        {"bar": bar(), "ids": []},
        {"bar": bar(), "ids": ["a" * 64] * (MOST_BY_ID + 1)},
        {"bar": bar(), "ids": ["a" * 64], "first": 5},
        {"ids": ["a" * 64]},
    ],
)
def test_an_invalid_page_request_is_422(guest: TestClient, body: dict) -> None:
    assert guest.post("/api/cards/by-id", json=body).status_code == 422


def test_a_users_later_page_carries_viewed_a_guests_does_not(
    guest: TestClient, ron: TestClient
) -> None:
    rest = whole(ron)["order"][FIRST_CARDS:]
    assert write(ron, "POST", f"/api/viewed/{rest[0]}").status_code == 200
    mine = ron.post("/api/cards/by-id", json={"bar": bar(), "ids": rest[:2]}).json()["cards"]
    assert [card["viewed"] for card in mine] == [True, False]
    theirs = guest.post("/api/cards/by-id", json={"bar": bar(), "ids": rest[:2]}).json()["cards"]
    assert all("viewed" not in card for card in theirs)


def test_a_flagged_card_is_gone_by_id(ron: TestClient, store: ManyStore) -> None:
    assert write(ron, "POST", f"/api/flag/{store.active}").status_code == 200
    answer = ron.post("/api/cards/by-id", json={"bar": bar(), "ids": [store.active]}).json()
    assert answer == {"generation": answer["generation"], "cards": [], "gone": [store.active]}


# --- D: the grouping in the background (#379, #380) ---


class Gate:
    """`derive_cards`, held while the gate is shut: a recompute as long as a test wants."""

    def __init__(self) -> None:
        self.open = threading.Event()
        self.open.set()
        self.calls = 0

    def __call__(self, inputs):
        self.calls += 1
        assert self.open.wait(10), "the gate was never opened"
        return derive_cards(inputs)


def settle(grouping: Grouping) -> None:
    assert grouping.wait(10), "the background recompute never ended"


@pytest.fixture
def gate() -> Gate:
    return Gate()


@pytest.fixture
def background(site, store: ManyStore, gate: Gate):
    grouping = Grouping(
        SqliteRepository(store.db, read_only=True),
        site.userdata.find_corrections,
        store.root,
        derive=gate,
        background=True,
    )
    return dataclasses.replace(site, grouping=grouping)


def test_before_the_first_grouping_every_answer_is_loading(background, gate: Gate) -> None:
    gate.open.clear()
    client = TestClient(create_app(background), base_url=ORIGIN)
    for path in ("/api/cards", f"/api/posts/{'a' * 64}", f"/api/photos/{'a' * 64}/a1.jpg"):
        response = client.get(path)
        assert response.status_code == 503, path
        assert response.json() == {"refusal": "loading"}
        assert response.headers["retry-after"] == "2"
    assert background.grouping.computing
    gate.open.set()
    settle(background.grouping)
    assert gate.calls == 1  # one recompute, started by the first request, however many asked
    assert client.get("/api/cards").status_code == 200


def test_start_begins_the_first_grouping_before_any_request(background, gate: Gate) -> None:
    background.grouping.start()
    settle(background.grouping)
    assert gate.calls == 1
    held = background.grouping.current()
    assert held.group_ms is None and held.snapshot.cards


def test_a_request_during_a_recompute_is_answered_at_once_from_the_old_snapshot(
    background, store: ManyStore, gate: Gate
) -> None:
    grouping = background.grouping
    grouping.start()
    settle(grouping)
    old = grouping.current().snapshot
    gate.open.clear()
    stored = store.repository.get_lifecycle(store.other)
    overwrite_lifecycle(store.repository, stored.model_copy(update={"state": "archived"}))
    for _ in range(5):
        assert grouping.current().snapshot is old  # not waiting: the gate is shut
    assert grouping.computing
    gate.open.set()
    settle(grouping)
    assert gate.calls == 2  # the first grouping, then one recompute for the five requests
    new = grouping.current().snapshot
    assert new.generation > old.generation and store.other not in new.card_of


def test_a_users_own_flag_leaves_every_answer_at_once(
    background, store: ManyStore, gate: Gate
) -> None:
    """The overlay (#379): the recompute is held shut, yet the card is gone everywhere."""
    background.grouping.start()
    settle(background.grouping)
    ron = TestClient(create_app(background), base_url=ORIGIN)
    assert sign_in(ron).status_code == 200
    before = ron.post("/api/cards", json={**bar(), "first": MOST_BY_ID}).json()
    assert store.active in before["order"]
    gate.open.clear()
    assert write(ron, "POST", f"/api/flag/{store.active}").json()["flagged"] == 2
    after = ron.post("/api/cards", json={**bar(), "first": MOST_BY_ID}).json()
    assert store.active not in after["order"] and after["count"] == before["count"] - 1
    assert all(store.active not in card["post_ids"] for card in after["cards"])
    assert ron.get(f"/api/posts/{store.tied}").status_code == 404  # the card's other member
    assert ron.get(f"/api/photos/{store.active}/a1.jpg").status_code == 404
    assert write(ron, "POST", f"/api/flag/{store.active}").json() == {"refusal": "gone"}
    gone = ron.post("/api/cards/by-id", json={"bar": bar(), "ids": [store.active]}).json()
    assert gone["gone"] == [store.active]
    assert background.grouping.computing  # all of it before the recompute ended
    gate.open.set()
    settle(background.grouping)
    assert background.grouping._removed == {}  # dropped once the new snapshot is held
    final = ron.post("/api/cards", json={**bar(), "first": MOST_BY_ID}).json()
    assert final["order"] == after["order"]


def test_a_report_that_removes_leaves_at_once(background, store: ManyStore, gate: Gate) -> None:
    background.grouping.start()
    settle(background.grouping)
    ron = TestClient(create_app(background), base_url=ORIGIN)
    assert sign_in(ron).status_code == 200
    gate.open.clear()
    answer = write(ron, "POST", f"/api/report/{store.other}", {"fields": ["price"]})
    assert answer.json() == {"removed": True}
    order = ron.post("/api/cards", json={**bar(), "first": MOST_BY_ID}).json()["order"]
    assert store.other not in order
    gate.open.set()
    settle(background.grouping)


def test_the_foreground_mode_still_computes_on_the_request(site) -> None:
    """The tests' default, and the behaviour before D: the request computes and says so."""
    held = site.grouping.current()
    assert held.group_ms is not None
    assert site.grouping.current().group_ms is None


def test_not_ready_only_in_the_background(background, gate: Gate) -> None:
    gate.open.clear()
    with pytest.raises(NotReady):
        background.grouping.current()
    gate.open.set()
    settle(background.grouping)
