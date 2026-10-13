"""The site's sign-in, sign-up, password change and saved profile (`PHASE_3.md` 3.7 (g), (l), build
steps 4 and 5): test groups 1 (the cookie), 2 (a guest's writes are 401), 6 (the bar is never saved;
`save_profile` only through `PUT /api/profile`), the write checks (JSON only, `Origin`, #330 point
19), the refusals of 3.5, and no password, key or token in any log.

Temporary stores only (`tests/test_web.py`'s `Store`); every hash is made with `profiles.CHEAPEST`.
The client speaks `https://testserver`, so it keeps and sends the `Secure` cookie as a browser does.
"""

import logging
import sqlite3
from contextlib import closing
from datetime import timedelta
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

import pytest
from argon2 import PasswordHasher, profiles
from fastapi.testclient import TestClient

from tests.test_web import (
    NOW,
    Store,
    _event_loop_self_pipe,  # noqa: F401  (#344: the same one exception)
    bar,
)
from tlv_hunter.accounts import actions
from tlv_hunter.contracts.profile import RangeCriterion, new_profile
from tlv_hunter.contracts.session import SESSION_LIFETIME
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.app import create_app, site_over
from tlv_hunter.web.auth import COOKIE_NAME

ORIGIN = "https://testserver"
ADMIN_PASSWORD = "admin-password-1"
FRIEND_PASSWORD = "friend-password-1"
HASHER = PasswordHasher.from_parameters(profiles.CHEAPEST)


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self):
        return self.now


@pytest.fixture
def store(tmp_path: Path) -> Store:
    built = Store(tmp_path / "store")
    # The fixture's admin "ron" has a placeholder hash: give it a real one.
    actions.reset_admin_password(built.userdata, ADMIN_PASSWORD, NOW, hasher=HASHER)
    return built


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(store: Store, clock: Clock) -> TestClient:
    site = site_over(store.db, store.root, clock=clock, hasher=HASHER)
    return TestClient(create_app(site), base_url=ORIGIN)


def write(client: TestClient, method: str, path: str, body: Any = None, **headers: str):
    return client.request(
        method, path, json=body if body is not None else {}, headers={"origin": ORIGIN, **headers}
    )


def sign_in(client: TestClient, username: str = "ron", password: str = ADMIN_PASSWORD):
    return write(client, "POST", "/api/sign-in", {"username": username, "password": password})


def set_cookie(response) -> SimpleCookie:
    headers = response.headers.get_list("set-cookie")
    assert len(headers) == 1, headers
    parsed: SimpleCookie = SimpleCookie()
    parsed.load(headers[0])
    return parsed


def issue_key(store: Store, label: str = "for dana") -> str:
    token = actions.sign_in(store.userdata, "ron", ADMIN_PASSWORD, NOW, hasher=HASHER).token
    return actions.issue_key(store.userdata, token, label, NOW).key


def sign_up_body(key: str, username: str = "dana", password: str = FRIEND_PASSWORD) -> dict:
    return {"key": key, "username": username, "password": password}


def disable(store: Store, username: str) -> None:
    user = store.userdata.find_user_by_username(username)
    assert user is not None
    store.userdata.save_user(user.model_copy(update={"disabled_at": NOW}), expected=user)


# --- 1. the cookie ---


def test_sign_in_sets_the_cookie_with_exactly_its_attributes(client: TestClient) -> None:
    response = sign_in(client)
    assert response.status_code == 200
    assert response.json() == {
        "user": {"username": "ron", "is_admin": True, "must_change_password": False}
    }
    raw = response.headers["set-cookie"]
    attributes = {part.strip().split("=")[0].lower() for part in raw.split(";")[1:]}
    assert attributes == {"httponly", "max-age", "path", "samesite", "secure"}  # no Domain
    morsel = set_cookie(response)[COOKIE_NAME]
    assert morsel["max-age"] == "2592000" == str(int(SESSION_LIFETIME.total_seconds()))
    assert morsel["path"] == "/" and morsel["samesite"].lower() == "strict"
    assert morsel["httponly"] is True and morsel["secure"] is True
    assert morsel.value and morsel.value not in response.text  # the token only in the cookie
    assert client.get("/api/session").json()["user"]["username"] == "ron"


def test_no_cookie_is_a_guest_and_nothing_is_cleared(client: TestClient) -> None:
    response = client.get("/api/session")
    assert response.json() == {"user": None}
    assert "set-cookie" not in response.headers


def _assert_cleared(response) -> None:
    morsel = set_cookie(response)[COOKIE_NAME]
    assert morsel.value == "" and morsel["max-age"] == "0"
    assert morsel["secure"] is True and morsel["httponly"] is True and morsel["path"] == "/"


def test_an_unknown_token_is_a_guest_and_the_cookie_is_cleared(client: TestClient) -> None:
    client.cookies.set(COOKIE_NAME, "not-a-session-token")
    response = client.get("/api/session")
    assert response.json() == {"user": None}
    _assert_cleared(response)
    client.cookies.set(COOKIE_NAME, "not-a-session-token")
    refused = client.get("/api/profile")  # a refusal clears it too
    assert refused.status_code == 401
    _assert_cleared(refused)


def test_an_ended_token_is_a_guest_and_the_cookie_is_cleared(client: TestClient) -> None:
    sign_in(client)
    token = client.cookies[COOKIE_NAME]
    signed_out = write(client, "POST", "/api/sign-out")
    assert signed_out.status_code == 200
    _assert_cleared(signed_out)
    client.cookies.set(COOKIE_NAME, token)  # a browser that kept it
    response = client.get("/api/session")
    assert response.json() == {"user": None}
    _assert_cleared(response)


def test_an_expired_session_is_a_guest_and_the_cookie_is_cleared(
    client: TestClient, clock: Clock
) -> None:
    sign_in(client)
    clock.now = NOW + SESSION_LIFETIME - timedelta(seconds=1)
    assert client.get("/api/session").json()["user"] is not None
    clock.now = NOW + SESSION_LIFETIME
    response = client.get("/api/session")
    assert response.json() == {"user": None}
    _assert_cleared(response)


def test_a_disabled_users_session_is_a_guest_and_the_cookie_is_cleared(
    client: TestClient, store: Store
) -> None:
    assert write(client, "POST", "/api/sign-up", sign_up_body(issue_key(store))).status_code == 200
    disable(store, "dana")
    response = client.get("/api/session")
    assert response.json() == {"user": None}
    _assert_cleared(response)


def test_signing_in_again_ends_the_session_the_browser_held(
    client: TestClient, store: Store
) -> None:
    sign_in(client)
    first = client.cookies[COOKIE_NAME]
    sign_in(client)
    assert client.cookies[COOKIE_NAME] != first
    with closing(sqlite3.connect(store.db)) as conn:
        docs = [row[0] for row in conn.execute("SELECT doc FROM sessions")]
    assert len(docs) == 2 and sum('"ended_at":null' in doc for doc in docs) == 1


# --- the write checks: JSON only, from the site's own page ---


@pytest.mark.parametrize(
    "headers",
    [
        {},  # no Origin
        {"origin": "null"},
        {"origin": "https://evil.example"},
        {"origin": "https://testserver.evil.example"},
    ],
)
def test_a_write_from_another_origin_or_none_is_403(client: TestClient, headers: dict) -> None:
    body = {"username": "ron", "password": ADMIN_PASSWORD}
    response = client.post("/api/sign-in", json=body, headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers


def test_the_origin_is_compared_by_host_not_scheme(client: TestClient) -> None:
    """Behind Tailscale Serve the browser speaks https and the site hears http (3.9)."""
    body = {"username": "ron", "password": ADMIN_PASSWORD}
    response = client.post("/api/sign-in", json=body, headers={"origin": "http://testserver"})
    assert response.status_code == 200


def test_a_write_that_is_not_json_is_415(client: TestClient) -> None:
    response = client.post(
        "/api/sign-in",
        content="username=ron&password=admin-password-1",
        headers={"origin": ORIGIN, "content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 415


# --- 2. a guest's writes ---


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", "/api/sign-out"), ("POST", "/api/password"), ("PUT", "/api/profile")],
)
def test_every_write_of_a_guest_is_401(client: TestClient, method: str, path: str) -> None:
    assert write(client, method, path, {}).status_code == 401


def test_a_guest_has_no_profile_and_writes_nothing(client: TestClient, store: Store) -> None:
    before = store.db.read_bytes()
    assert client.get("/api/profile").status_code == 401
    assert client.put("/api/profile", json=bar()).status_code == 401
    assert store.db.read_bytes() == before


# --- sign-in: the refusals of 3.5 ---


def test_a_wrong_password_and_an_unknown_username_read_the_same(client: TestClient) -> None:
    wrong = sign_in(client, password="not-the-password")
    unknown = sign_in(client, username="nobody")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"refusal": "wrong"}
    assert "set-cookie" not in wrong.headers


def test_the_fifth_failure_delays_with_the_seconds_to_wait(
    client: TestClient, clock: Clock
) -> None:
    for _ in range(5):
        assert sign_in(client, password="not-the-password").status_code == 401
    clock.now = NOW + timedelta(seconds=12)
    delayed = sign_in(client)  # the right password: not even checked
    assert delayed.status_code == 429
    assert delayed.json() == {"refusal": "delayed", "retry_after_seconds": 18}
    assert delayed.headers["retry-after"] == "18"
    clock.now = NOW + timedelta(seconds=30)
    assert sign_in(client).status_code == 200


def test_a_disabled_user_is_refused_in_words(client: TestClient, store: Store) -> None:
    write(client, "POST", "/api/sign-up", sign_up_body(issue_key(store)))
    disable(store, "dana")
    response = sign_in(client, "dana", FRIEND_PASSWORD)
    assert response.status_code == 403 and response.json() == {"refusal": "disabled"}


def test_a_sign_in_body_with_an_extra_field_is_422(client: TestClient) -> None:
    body = {"username": "ron", "password": ADMIN_PASSWORD, "remember": True}
    assert write(client, "POST", "/api/sign-in", body).status_code == 422


# --- sign-up with a key (#336: no filter field) ---


def test_sign_up_creates_the_user_with_the_default_profile_and_signs_in(
    client: TestClient, store: Store
) -> None:
    response = write(client, "POST", "/api/sign-up", sign_up_body(issue_key(store)))
    assert response.status_code == 200
    assert response.json()["user"] == {
        "username": "dana",
        "is_admin": False,
        "must_change_password": False,
    }
    assert set_cookie(response)[COOKIE_NAME].value
    profile = client.get("/api/profile").json()
    defaults = new_profile("d" * 32, NOW).model_dump(mode="json")
    assert profile["room"] == defaults["room"] == profile["whole_apartment"]
    assert profile["include_sublets"] is False


@pytest.mark.parametrize(
    ("body_change", "status", "refusal"),
    [
        ({"username": "Ron"}, 409, "username_taken"),
        ({"username": "דנה"}, 422, "username_invalid"),
        ({"username": "da"}, 422, "username_invalid"),
        ({"password": "short"}, 422, "password_too_short"),
        ({"key": "not-a-key"}, 403, "key_not_usable"),
    ],
)
def test_sign_up_refusals(
    client: TestClient, store: Store, body_change: dict, status: int, refusal: str
) -> None:
    body = {**sign_up_body(issue_key(store)), **body_change}
    response = write(client, "POST", "/api/sign-up", body)
    assert response.status_code == status and response.json() == {"refusal": refusal}
    assert "set-cookie" not in response.headers


def test_a_used_key_cannot_sign_up_again(client: TestClient, store: Store) -> None:
    key = issue_key(store)
    write(client, "POST", "/api/sign-up", sign_up_body(key))
    again = write(client, "POST", "/api/sign-up", sign_up_body(key, username="noa"))
    assert again.status_code == 403 and again.json() == {"refusal": "key_not_usable"}


def test_sign_up_has_no_filter_field(client: TestClient, store: Store) -> None:
    body = {**sign_up_body(issue_key(store)), "filter": bar()}
    assert write(client, "POST", "/api/sign-up", body).status_code == 422
    assert store.userdata.find_user_by_username("dana") is None


# --- the forced password change ---


def _with_temporary_password(client: TestClient, store: Store) -> None:
    write(client, "POST", "/api/sign-up", sign_up_body(issue_key(store)))
    dana = store.userdata.find_user_by_username("dana")
    assert dana is not None
    admin_token = actions.sign_in(store.userdata, "ron", ADMIN_PASSWORD, NOW, hasher=HASHER).token
    actions.reset_password(
        store.userdata, admin_token, dana.user_id, "temporary-1", NOW, hasher=HASHER
    )
    signed = sign_in(client, "dana", "temporary-1")
    assert signed.json()["user"]["must_change_password"] is True


def test_while_a_change_is_due_only_the_change_and_sign_out_are_reachable(
    client: TestClient, store: Store
) -> None:
    _with_temporary_password(client, store)
    assert client.get("/api/profile").status_code == 403
    assert write(client, "PUT", "/api/profile", bar()).status_code == 403
    changed = write(
        client, "POST", "/api/password", {"current": "temporary-1", "new": "a-new-password"}
    )
    assert changed.status_code == 200
    assert changed.json()["user"]["must_change_password"] is False
    assert client.get("/api/profile").status_code == 200


def test_sign_out_is_reachable_while_a_change_is_due(client: TestClient, store: Store) -> None:
    _with_temporary_password(client, store)
    assert write(client, "POST", "/api/sign-out").status_code == 200
    assert client.get("/api/session").json() == {"user": None}


def test_a_password_change_refuses_a_wrong_current_or_a_short_new(client: TestClient) -> None:
    sign_in(client)
    wrong = write(client, "POST", "/api/password", {"current": "nope", "new": "a-new-password"})
    assert wrong.status_code == 401 and wrong.json() == {"refusal": "wrong"}
    assert client.get("/api/session").json()["user"] is not None  # still signed in
    short = write(client, "POST", "/api/password", {"current": ADMIN_PASSWORD, "new": "short"})
    assert short.status_code == 422 and short.json() == {"refusal": "password_too_short"}


def test_a_password_change_ends_the_other_sessions_and_keeps_this_one(client: TestClient) -> None:
    other = TestClient(client.app, base_url=ORIGIN)
    sign_in(other)
    sign_in(client)
    body = {"current": ADMIN_PASSWORD, "new": "a-new-password"}
    assert write(client, "POST", "/api/password", body).status_code == 200
    assert client.get("/api/session").json()["user"] is not None
    assert other.get("/api/session").json() == {"user": None}


# --- the saved profile ---


def test_a_user_reads_and_saves_the_profile(client: TestClient, store: Store) -> None:
    sign_in(client)
    before = client.get("/api/profile").json()
    assert set(before) == {"room", "whole_apartment", "include_sublets", "updated_at"}
    wanted = bar(room__price_max=4500, whole_apartment__areas=[30, 31])
    wanted["include_sublets"] = True
    saved = write(client, "PUT", "/api/profile", wanted)
    assert saved.status_code == 200
    assert {k: saved.json()[k] for k in wanted} == wanted
    assert {k: client.get("/api/profile").json()[k] for k in wanted} == wanted
    ron = store.userdata.find_user_by_username("ron")
    assert ron is not None
    stored = store.userdata.get_profile(ron.user_id)
    assert stored is not None and stored.room.price_max == 4500 and stored.include_sublets


SQM_IN_ROOM = RangeCriterion[float](min=10.0, max=None, level="preference").model_dump(mode="json")


@pytest.mark.parametrize(
    "body",
    [
        bar(room__size_sqm=SQM_IN_ROOM),
        bar(room__price_min=6000, room__price_max=5000),
        {**bar(), "user_id": "b" * 32},
    ],
)
def test_an_invalid_profile_is_422_and_nothing_is_saved(client: TestClient, body: dict) -> None:
    sign_in(client)
    before = client.get("/api/profile").json()
    assert write(client, "PUT", "/api/profile", body).status_code == 422
    assert client.get("/api/profile").json() == before


# --- 6. the bar is never saved: `save_profile` only through PUT /api/profile ---


def test_save_profile_is_called_by_put_profile_alone(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    original = SqliteUserDataStore.save_profile

    def recording(self: SqliteUserDataStore, profile: Any) -> Any:
        calls.append(profile.user_id)
        return original(self, profile)

    monkeypatch.setattr(SqliteUserDataStore, "save_profile", recording)
    sign_in(client)
    client.get("/api/session")
    client.get("/api/profile")
    client.get("/api/cards")
    for changed in (bar(room__price_max=3000), bar(whole_apartment__areas=[52])):
        assert client.post("/api/cards", json=changed).status_code == 200
    write(client, "POST", "/api/password", {"current": ADMIN_PASSWORD, "new": "a-new-password"})
    write(client, "POST", "/api/sign-out")
    sign_in(client, password="a-new-password")
    assert calls == []
    assert write(client, "PUT", "/api/profile", bar(room__price_max=3000)).status_code == 200
    assert len(calls) == 1


def test_the_site_writes_no_post_table(client: TestClient, store: Store) -> None:
    """Steps 4 and 5 write user-data tables only (#331): the posts' tables and the store
    generation are unchanged, so the grouping is not computed again."""

    def post_tables() -> list:
        with closing(sqlite3.connect(store.db)) as conn:
            return [
                conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()  # noqa: S608
                for table in ("raw_posts", "post_lifecycle", "listings", "store_generation")
            ]

    before = post_tables()
    write(client, "POST", "/api/sign-up", sign_up_body(issue_key(store)))
    write(client, "PUT", "/api/profile", bar(room__price_max=3000))
    write(client, "POST", "/api/password", {"current": FRIEND_PASSWORD, "new": "a-new-password"})
    write(client, "POST", "/api/sign-out")
    sign_in(client)
    assert post_tables() == before


# --- no password, key or token in any log ---


def test_no_password_key_or_token_reaches_a_log(
    client: TestClient, store: Store, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    key = issue_key(store)
    secrets = {key, FRIEND_PASSWORD, ADMIN_PASSWORD, "a-new-password", "wrong-password-9"}
    write(client, "POST", "/api/sign-up", sign_up_body(key))
    secrets.add(client.cookies[COOKIE_NAME])
    write(client, "POST", "/api/password", {"current": FRIEND_PASSWORD, "new": "a-new-password"})
    write(client, "POST", "/api/sign-out")
    sign_in(client, "dana", "wrong-password-9")
    sign_in(client)
    secrets.add(client.cookies[COOKIE_NAME])
    text = "\n".join(
        f"{record.getMessage()} {record.args!r} {record.__dict__!r}" for record in caplog.records
    )
    assert caplog.records  # the actions log, by opaque id
    assert not [secret for secret in secrets if secret in text]
