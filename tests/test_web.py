"""The site's read-only API for a guest (`PHASE_3.md` 3.7 (l), build step 2): test groups 2 (the
guest parts), 3 (nothing but the current cards reaches a guest), 4 (the photo route), 5 (the
grouping held in memory), 6 (the bar, never saved), 8 (the headers, the telemetry), and `serve`'s
copy. Temporary stores only; `TestClient` calls the app in process, and the socket guard stays on.

One narrow exception, on Windows only: `TestClient` runs the app in an asyncio event loop, and on
Windows (Python 3.12 has no native `socket.socketpair` there) the loop builds its self-pipe with
the pure-Python fallback, which connects a socket to its own 127.0.0.1 listener. `_loopback_pair`
below makes that pair without the guarded `connect`; every other `connect`, `create_connection`
and `getaddrinfo` still raises (`test_the_test_client_is_httpx2_and_connects_nowhere`)."""

import hashlib
import importlib.util
import io
import json
import socket
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    SQLITE_FILENAME,
    NetworkBlockedError,
    make_correction,
    overwrite_lifecycle,
)
from tests.test_gate_d import add, add_pending, make_member, make_post
from tests.test_userdata_store import ADMIN_ID, admin
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.post_lifecycle import PostImage
from tlv_hunter.contracts.profile import RangeCriterion, new_profile
from tlv_hunter.jobs import serve
from tlv_hunter.jobs.common import CONFIG_ROOT
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.app import CONTENT_SECURITY_POLICY, create_app, site_over
from tlv_hunter.web.routes import router

NOW = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)
# Read when this module is imported, before the suite's guard replaces it for each test.
_REAL_CONNECT = socket.socket.connect


def _loopback_pair(
    family: int = socket.AF_INET, type: int = socket.SOCK_STREAM, proto: int = 0
) -> tuple[socket.socket, socket.socket]:
    """`socket.socketpair` as Python's own Windows fallback makes it: a listener on 127.0.0.1 and
    one socket connected to it, by this process, to itself. Nothing else is connected."""
    with socket.socket(family, type, proto) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.socket(family, type, proto)
        _REAL_CONNECT(client, listener.getsockname())
        server, _ = listener.accept()
    return server, client


@pytest.fixture(autouse=True)
def _event_loop_self_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    if sys.platform == "win32":
        monkeypatch.setattr(socket, "socketpair", _loopback_pair)


PHOTO_BYTES = b"\xff\xd8\xff\xe0 a jpeg's first bytes"


class Store:
    """A temporary store: two active posts (one with a photo), and one each rejected, pending,
    archived, and a dedup A duplicate of the first; the three hidden ones have photos on disk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.db = root / SQLITE_FILENAME
        root.mkdir(parents=True)
        repository = SqliteRepository(self.db)
        self.userdata = SqliteUserDataStore(self.db)
        self.userdata.create_admin(admin(), new_profile(ADMIN_ID, NOW))
        active = make_member(1, price=[5000], rooms=3.0, areas=[30])
        other = make_member(2, price=[7000], rooms=2.0, areas=[52])
        rejected = make_member(3, price=[5000], areas=[30], nature="seeking")
        archived = make_member(5, price=[6000], areas=[30])
        for member in (active, other, rejected, archived):
            add(repository, member)
        pending = make_post(4, "flat pending words")
        add_pending(repository, pending)
        duplicate = make_post(6, "flat duplicate words", canonical=False).with_changes(
            duplicate_of=active.listing_id
        )
        add_pending(repository, duplicate)
        self.active, self.other = active.listing_id, other.listing_id
        self.rejected, self.pending = rejected.listing_id, pending.listing_id
        self.archived, self.duplicate = archived.listing_id, duplicate.listing_id
        for listing_id in (self.active, self.rejected, self.pending, self.archived):
            self._photo(repository, listing_id)
        stored = repository.get_lifecycle(self.archived)
        overwrite_lifecycle(repository, stored.model_copy(update={"state": "archived"}))
        self.repository = repository

    def _photo(self, repository: SqliteRepository, listing_id: str) -> None:
        local_path = f"images/{listing_id}/a1.jpg"
        (self.root / local_path).parent.mkdir(parents=True)
        (self.root / local_path).write_bytes(PHOTO_BYTES)
        stored = repository.get_lifecycle(listing_id)
        image = PostImage(listing_id=listing_id, media_id="m1", local_path=local_path, error=None)
        overwrite_lifecycle(repository, stored.model_copy(update={"images": [image]}))


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "store")


@pytest.fixture
def site(store: Store):
    return site_over(store.db, store.root, clock=lambda: NOW)


@pytest.fixture
def client(site) -> TestClient:
    return TestClient(create_app(site))


def bar(**changes: Any) -> dict:
    data = new_profile(ADMIN_ID, NOW).model_dump(mode="json")
    body = {key: data[key] for key in ("room", "whole_apartment", "include_sublets")}
    for path, value in changes.items():
        option, field = path.split("__")
        body[option][field] = value
    return body


def card_ids(response) -> set[str]:
    return {card["id"] for card in response.json()["cards"]}


# --- the client: httpx2, in process ---


def test_the_test_client_is_httpx2_and_connects_nowhere(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Starlette 1.7.0's `TestClient` imports `httpx2` (plain `httpx` only as a deprecated
    fallback), and its transport calls the app in process: no socket connects anywhere."""
    import starlette.testclient as starlette_testclient

    assert starlette_testclient.httpx.__name__ == "httpx2"
    attempts: list[Any] = []

    def record(self: socket.socket, *args: Any, **kwargs: Any) -> None:
        attempts.append(args)
        raise OSError("tests must not connect")

    monkeypatch.setattr(socket.socket, "connect", record)
    monkeypatch.setattr(socket.socket, "connect_ex", record)
    assert client.get("/api/reference").status_code == 200
    assert client.post("/api/cards", json=bar()).status_code == 200
    assert attempts == []
    with pytest.raises(NetworkBlockedError):  # the guard is still on for anything else
        socket.create_connection(("127.0.0.1", 80))


# --- 2. guests ---


def test_a_guest_reads_the_reference(client: TestClient) -> None:
    body = client.get("/api/reference").json()
    assert [area["number"] for area in body["areas"]] == list(range(1, 72))
    assert sorted(n for group in body["area_groups"] for n in group["areas"]) == list(range(1, 72))
    assert body["area_groups"][-1]["collapsed"] is True
    assert "price" in body["reportable_fields"] and len(body["reportable_fields"]) == 22


def test_a_guest_lists_opens_and_sees_photos(client: TestClient, store: Store) -> None:
    listed = client.get("/api/cards")
    assert listed.status_code == 200
    cards = listed.json()["cards"]
    assert {card["id"] for card in cards} == {store.active, store.other}
    assert all("viewed" not in card for card in cards)  # a guest has no viewed marks
    first = next(card for card in cards if card["id"] == store.active)
    assert first["photos"] == [f"/api/photos/{store.active}/a1.jpg"]
    assert first["price"] == {"state": "written", "value": [5000]}
    opened = client.get(f"/api/posts/{store.active}").json()
    assert opened["text"] and opened["publications"][0]["id"] == store.active
    photo = client.get(first["photos"][0])
    assert photo.status_code == 200 and photo.content == PHOTO_BYTES


def test_a_posted_empty_bar_gives_the_same_list_as_a_new_guest(client: TestClient) -> None:
    assert card_ids(client.post("/api/cards", json=bar())) == card_ids(client.get("/api/cards"))


def test_the_api_has_no_write(client: TestClient) -> None:
    """Build step 2 is read-only: the only POST reads (the bar); nothing else accepts a write."""
    methods = {(route.path, method) for route in router.routes for method in route.methods}
    writes = {(path, m) for path, m in methods if m not in ("GET", "HEAD")}
    assert writes == {("/api/cards", "POST")}
    assert client.put("/api/profile", json={}).status_code in (404, 405)


# --- 3. nothing but the current cards reaches a guest ---


def test_rejected_pending_archived_and_duplicates_never_reach_a_guest(
    client: TestClient, store: Store
) -> None:
    hidden = (store.rejected, store.pending, store.archived)
    listed = card_ids(client.post("/api/cards", json=bar()))
    assert not listed & set(hidden) and store.duplicate not in listed
    for listing_id in hidden:
        assert client.get(f"/api/posts/{listing_id}").status_code == 404
        assert client.get(f"/api/photos/{listing_id}/a1.jpg").status_code == 404
        assert (store.root / "images" / listing_id / "a1.jpg").is_file()  # on disk, not served


def test_a_duplicates_id_opens_its_canonicals_card(client: TestClient, store: Store) -> None:
    opened = client.get(f"/api/posts/{store.duplicate}")
    assert opened.status_code == 200
    assert opened.json()["id"] == store.active
    assert store.duplicate in opened.json()["post_ids"]


# --- 4. the photo route ---


@pytest.mark.parametrize(
    "path",
    [
        "/api/photos/{active}/a2.jpg",  # not a stored photo of the post
        "/api/photos/{other}/a1.jpg",  # a file of another post, under this one's id
        "/api/photos/{active}/..%2F..%2Fstore.sqlite3",
        "/api/photos/{active}/%2E%2E",
        "/api/photos/nobody/a1.jpg",
    ],
)
def test_only_a_stored_photo_of_a_current_card_is_served(
    client: TestClient, store: Store, path: str
) -> None:
    url = path.format(active=store.active, other=store.other)
    assert client.get(url).status_code == 404


def test_a_stored_photo_missing_on_disk_is_404(client: TestClient, store: Store) -> None:
    (store.root / "images" / store.active / "a1.jpg").unlink()
    assert client.get(f"/api/photos/{store.active}/a1.jpg").status_code == 404


# --- 5. the grouping held in memory (#301, #316) ---


def test_the_grouping_is_computed_once_for_many_requests(client: TestClient, site) -> None:
    first = client.post("/api/cards", json=bar())
    assert "group;dur=" in first.headers["server-timing"]
    for _ in range(5):
        again = client.post("/api/cards", json=bar())
        assert "group;dur=" not in again.headers["server-timing"]
        for name in ("gen", "eval", "order", "json"):
            assert f"{name};dur=" in again.headers["server-timing"]
    client.get("/api/reference")
    assert site.grouping.recomputes == 1


def test_a_store_write_makes_the_next_request_compute_again(
    client: TestClient, site, store: Store
) -> None:
    client.get("/api/cards")
    store.repository.upsert(store.repository.get(store.active))  # unchanged: the counter moves
    assert "group;dur=" in client.get("/api/cards").headers["server-timing"]
    assert site.grouping.recomputes == 2
    store.userdata.mark_viewed(ADMIN_ID, store.active, NOW)  # not a post change
    client.get("/api/cards")
    assert site.grouping.recomputes == 2
    listing = store.repository.get_listing(store.other)
    four_rooms = {"state": "written", "value": 4.0}
    store.userdata.add_correction(make_correction(listing, "rooms", four_rooms))
    opened = client.get(f"/api/posts/{store.other}").json()
    assert site.grouping.recomputes == 3
    assert opened["rooms"] == four_rooms  # the post as users see it


def test_concurrent_requests_compute_one_grouping(site) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        held = list(pool.map(lambda _: site.grouping.current(), range(16)))
    assert site.grouping.recomputes == 1
    assert len({id(h.snapshot) for h in held}) == 1


# --- 6. the bar: a transient profile, never saved ---


def test_the_bar_filters_and_is_never_saved(
    client: TestClient, store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("the bar was saved")

    monkeypatch.setattr(SqliteUserDataStore, "save_profile", refuse)
    before = hashlib.sha256(store.db.read_bytes()).hexdigest()
    # The posts' kind is not written, so both options evaluate them (#273): cap both.
    capped = client.post(
        "/api/cards", json=bar(room__price_max=6000, whole_apartment__price_max=6000)
    )
    assert card_ids(capped) == {store.active}
    assert hashlib.sha256(store.db.read_bytes()).hexdigest() == before
    with closing(sqlite3.connect(store.db)) as conn:
        assert conn.execute("SELECT count(*) FROM profiles").fetchone() == (1,)  # the admin's


SQM_IN_ROOM = RangeCriterion[float](min=10.0, max=None, level="preference").model_dump(mode="json")


@pytest.mark.parametrize(
    "body",
    [
        json.dumps(bar(whole_apartment__price_min=7000, whole_apartment__price_max=6000)),
        json.dumps(bar(room__size_sqm=SQM_IN_ROOM)),
        json.dumps({**bar(), "user_id": "secret-value-1"}),
        json.dumps({"room": {}}),
        "not json at all",
        "",
    ],
)
def test_an_invalid_bar_is_422_and_echoes_nothing(client: TestClient, body: str) -> None:
    response = client.post("/api/cards", content=body, headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert "secret-value-1" not in response.text


# --- 8. the headers and the telemetry ---


def test_every_response_carries_the_two_headers(client: TestClient, store: Store) -> None:
    responses = [
        client.get("/api/reference"),
        client.post("/api/cards", json=bar()),
        client.post("/api/cards", content="{"),
        client.get(f"/api/posts/{store.rejected}"),
        client.get(f"/api/photos/{store.active}/a1.jpg"),
        client.get("/nothing-here"),
    ]
    assert [r.status_code for r in responses] == [200, 200, 422, 404, 200, 404]
    for response in responses:
        assert response.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
        assert response.headers["referrer-policy"] == "no-referrer"


def test_fastapis_own_pages_are_off(client: TestClient) -> None:
    """The docs page loads its scripts from a CDN (invariant 15)."""
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_telemetry_is_not_configured(site, monkeypatch: pytest.MonkeyPatch) -> None:
    """FastAPI 0.143.0: exporters only on opt-in; the site turns everything off explicitly, which
    overrides the environment variable. No OpenTelemetry SDK is installed."""
    monkeypatch.setenv("FASTAPI_OTEL_AUTO_CONFIGURE", "true")
    app = create_app(site)
    config = app._telemetry
    assert config["auto_configure"] is False
    assert (config["tracing"], config["metrics"], config["logs"]) == (False, False, False)
    assert importlib.util.find_spec("opentelemetry.sdk") is None


# --- serve: a dated copy, never the store ---


def _moved_under_a_repo(tmp_path: Path, store: Store) -> Path:
    """`serve` finds the store under `repo_root / store_root`: the test store is moved there."""
    store_root = YamlConfig(CONFIG_ROOT).collection().store_root
    target = tmp_path / "repo" / store_root
    target.parent.mkdir(parents=True)
    store.root.rename(target)
    return tmp_path / "repo"


def test_serve_copies_the_store_and_serves_the_copy(tmp_path: Path, store: Store) -> None:
    repo = _moved_under_a_repo(tmp_path, store)
    database = repo / YamlConfig(CONFIG_ROOT).collection().store_root / SQLITE_FILENAME
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    served: list[Any] = []

    def run(app: Any, **kwargs: Any) -> None:
        served.append(kwargs)
        assert TestClient(app).get("/api/cards").status_code == 200

    out = io.StringIO()
    assert serve.main(["--copy"], repo_root=repo, clock=lambda: NOW, stream=out, run=run) == 0
    assert served == [{"host": "127.0.0.1", "port": 8000}]
    copy = database.parent / "site" / "tlv_hunter.2026-10-13.site.sqlite3"
    assert copy.is_file() and f"serving the copy: {copy}" in out.getvalue()
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    with closing(sqlite3.connect(copy)) as conn:
        assert conn.execute("SELECT count(*) FROM raw_posts").fetchone() == (6,)
    # Without --copy, the newest copy; a second --copy the same day gets the time in its name.
    quiet = io.StringIO()
    assert serve.main([], repo_root=repo, clock=lambda: NOW, stream=quiet, run=run) == 0
    assert serve.main(["--copy"], repo_root=repo, clock=lambda: NOW, stream=quiet, run=run) == 0
    assert len(list(copy.parent.iterdir())) == 2


def test_serve_with_no_copy_is_refused(tmp_path: Path, store: Store) -> None:
    repo = _moved_under_a_repo(tmp_path, store)
    out = io.StringIO()
    code = serve.main([], repo_root=repo, clock=lambda: NOW, stream=out, run=lambda *a, **k: None)
    assert code == 1 and "run with --copy first" in out.getvalue()


def test_serve_never_serves_the_store_itself(tmp_path: Path) -> None:
    database = tmp_path / SQLITE_FILENAME
    database.write_bytes(b"")
    with pytest.raises(serve.Refused, match="#331"):
        serve._not_the_store(database, database)
