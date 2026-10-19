"""The eighth seam, `UserDataStore` (task 3.4 (a); DECISIONS.md #267, #289), on SQLite: a fresh
temporary file per test, never the production store."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import SQLITE_FILENAME, make_listing
from tlv_hunter.contracts.classification_report import ClassificationReport
from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.contracts.hidden_post import HiddenPost
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.contracts.session import SESSION_LIFETIME, Session
from tlv_hunter.contracts.signup_key import SignupKey
from tlv_hunter.contracts.user import User
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.base import (
    AdminExists,
    CorrectionInForce,
    KeyNotUsable,
    OpenReportExists,
    UserDataStore,
    UsernameTaken,
)
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
ADMIN_ID = "a" * 32
LISTING_ID = "c" * 64


def _id(n: int) -> str:
    return f"{n:032x}"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def admin(**changes: Any) -> User:
    return User(
        **{
            "schema_version": 2,
            "user_id": ADMIN_ID,
            "username": "ron",
            "password_hash": "$argon2id$hash",
            "is_admin": True,
            "created_at": NOW,
            "signup_key_id": None,
            "must_change_password": False,
            "password_changed_at": NOW,
            "disabled_at": None,
            "failed_sign_ins": 0,
            "last_failed_sign_in_at": None,
            "telegram_chat_id": None,
            "telegram_linked_at": None,
            **changes,
        }
    )


def friend(n: int, username: str, key_id: str) -> User:
    return admin().model_copy(
        update={"user_id": _id(n), "username": username, "is_admin": False, "signup_key_id": key_id}
    )


def signup_key(n: int, secret: str) -> SignupKey:
    return SignupKey(
        schema_version=1,
        key_id=_id(n),
        key_hash=_hash(secret),
        label=f"friend {n}",
        created_at=NOW,
        used_by=None,
        used_at=None,
        cancelled_at=None,
    )


def session(user_id: str, token: str, at: datetime = NOW) -> Session:
    return Session(
        schema_version=1,
        token_hash=_hash(token),
        user_id=user_id,
        created_at=at,
        expires_at=at + SESSION_LIFETIME,
        ended_at=None,
    )


def report(n: int, reporter: str, **changes: Any) -> ClassificationReport:
    fields: dict[str, Any] = {
        "schema_version": 1,
        "report_id": _id(1000 + n),
        "listing_id": LISTING_ID,
        "reported_by": reporter,
        "reported_at": NOW,
        "fields": ["price"],
        "note": None,
        "status": "open",
        "resolved_by": None,
        "resolved_at": None,
    }
    return ClassificationReport(**{**fields, **changes})


def correction(n: int, **changes: Any) -> FieldCorrection:
    fields: dict[str, Any] = {
        "schema_version": 1,
        "correction_id": _id(2000 + n),
        "listing_id": LISTING_ID,
        "field": "areas",
        "model_value": [52],
        "corrected_value": [42],
        "corrected_by": ADMIN_ID,
        "corrected_at": NOW,
        "report_id": None,
        "removed_by": None,
        "removed_at": None,
    }
    return FieldCorrection(**{**fields, **changes})


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / SQLITE_FILENAME


@pytest.fixture
def store(path: Path) -> SqliteUserDataStore:
    created = SqliteUserDataStore(path)
    created.create_admin(admin(), new_profile(ADMIN_ID, NOW))
    return created


def _with_friend(store: SqliteUserDataStore, n: int = 1, username: str = "dana") -> User:
    key = signup_key(n, f"secret-{n}")
    store.add_key(key)
    user = friend(n, username, key.key_id)
    return store.create_user(user, new_profile(user.user_id, NOW), key.key_hash, NOW)


def test_it_is_a_user_data_store(store: SqliteUserDataStore) -> None:
    assert isinstance(store, UserDataStore)


# --- users and keys ---


def test_the_admin_is_created_once_with_a_profile(store: SqliteUserDataStore) -> None:
    assert store.get_user(ADMIN_ID) == admin()
    assert store.get_profile(ADMIN_ID) == new_profile(ADMIN_ID, NOW)
    second = admin().model_copy(update={"user_id": "b" * 32, "username": "other"})
    with pytest.raises(AdminExists):
        store.create_admin(second, new_profile(second.user_id, NOW))


def test_create_admin_refuses_a_user_who_is_not_the_admin(store: SqliteUserDataStore) -> None:
    with pytest.raises(ValueError, match="admin only"):
        store.create_admin(friend(1, "dana", _id(9)), new_profile(_id(1), NOW))


def test_a_key_creates_one_account_and_is_marked_used(store: SqliteUserDataStore) -> None:
    created = _with_friend(store)
    (key,) = store.list_keys()
    assert (key.used_by, key.used_at) == (created.user_id, NOW)
    assert store.get_profile(created.user_id) == new_profile(created.user_id, NOW)
    second = friend(2, "noa", key.key_id)
    with pytest.raises(KeyNotUsable):
        store.create_user(second, new_profile(second.user_id, NOW), key.key_hash, NOW)
    assert store.get_user(second.user_id) is None


def test_find_key_by_hash_finds_a_key_used_or_not(store: SqliteUserDataStore) -> None:
    key = store.add_key(signup_key(1, "secret-1"))
    store.add_key(signup_key(2, "secret-2"))
    assert store.find_key_by_hash(_hash("secret-1")) == key
    assert store.find_key_by_hash(_hash("unknown")) is None
    created = _with_friend(store, 3, "noa")
    used = store.find_key_by_hash(_hash("secret-3"))
    assert used is not None and used.used_by == created.user_id


def test_an_unknown_cancelled_or_another_users_key_is_refused(store: SqliteUserDataStore) -> None:
    key = store.add_key(signup_key(1, "secret-1"))
    user = friend(1, "dana", key.key_id)
    with pytest.raises(KeyNotUsable):
        store.create_user(user, new_profile(user.user_id, NOW), _hash("wrong"), NOW)
    other = friend(1, "dana", _id(77))
    with pytest.raises(KeyNotUsable):
        store.create_user(other, new_profile(other.user_id, NOW), key.key_hash, NOW)
    store.save_key(key.model_copy(update={"cancelled_at": NOW}), expected=key)
    with pytest.raises(KeyNotUsable):
        store.create_user(user, new_profile(user.user_id, NOW), key.key_hash, NOW)
    assert store.list_users() == [admin()]


def test_a_taken_username_is_refused_ignoring_case_and_the_key_stays_usable(
    store: SqliteUserDataStore,
) -> None:
    key = store.add_key(signup_key(1, "secret-1"))
    user = friend(1, "RON", key.key_id)
    with pytest.raises(UsernameTaken):
        store.create_user(user, new_profile(user.user_id, NOW), key.key_hash, NOW)
    assert store.list_keys()[0].usable
    renamed = user.model_copy(update={"username": "ron2"})
    assert store.create_user(renamed, new_profile(renamed.user_id, NOW), key.key_hash, NOW)


def test_a_user_is_found_by_username_ignoring_case(store: SqliteUserDataStore) -> None:
    created = _with_friend(store, username="Dana.K")
    assert store.find_user_by_username("dana.k") == created
    assert store.find_user_by_username("DANA.K") == created
    assert store.find_user_by_username("noa") is None
    assert [u.user_id for u in store.list_users()] == [ADMIN_ID, created.user_id]


def test_save_user_is_compare_and_set_and_keeps_the_username(store: SqliteUserDataStore) -> None:
    read = store.get_user(ADMIN_ID)
    failed = read.model_copy(update={"failed_sign_ins": 1, "last_failed_sign_in_at": NOW})
    store.save_user(failed, expected=read)
    with pytest.raises(StaleRecordError):
        store.save_user(read.model_copy(update={"must_change_password": True}), expected=read)
    assert store.get_user(ADMIN_ID) == failed
    with pytest.raises(ValueError, match="never change"):
        store.save_user(failed.model_copy(update={"username": "ronk"}), expected=failed)


def test_a_cancelled_key_is_not_un_cancelled(store: SqliteUserDataStore) -> None:
    key = store.add_key(signup_key(1, "secret-1"))
    cancelled = store.save_key(key.model_copy(update={"cancelled_at": NOW}), expected=key)
    with pytest.raises(ValueError, match="un-cancelled"):
        store.save_key(key, expected=cancelled)
    with pytest.raises(StaleRecordError):
        store.save_key(key.model_copy(update={"label": "new"}), expected=key)


def test_a_new_key_is_unused(store: SqliteUserDataStore) -> None:
    with pytest.raises(ValueError, match="unused"):
        store.add_key(signup_key(1, "s").model_copy(update={"cancelled_at": NOW}))


# --- sessions ---


def test_sessions_are_found_by_hash_and_ended(store: SqliteUserDataStore) -> None:
    store.add_session(session(ADMIN_ID, "one"))
    store.add_session(session(ADMIN_ID, "two"))
    store.add_session(session(ADMIN_ID, "three"))
    assert store.find_session(_hash("one")) == session(ADMIN_ID, "one")
    store.end_session(_hash("one"), NOW + timedelta(hours=1))
    assert store.find_session(_hash("one")).ended_at == NOW + timedelta(hours=1)
    later = NOW + timedelta(hours=2)
    assert store.end_sessions(ADMIN_ID, later, keep=_hash("two")) == 1
    assert store.find_session(_hash("two")).ended_at is None
    assert store.find_session(_hash("three")).ended_at == later
    assert store.find_session(_hash("one")).ended_at == NOW + timedelta(hours=1)
    assert store.end_sessions(ADMIN_ID, later) == 1
    assert store.find_session(_hash("missing")) is None


def test_a_session_needs_a_stored_user(store: SqliteUserDataStore) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        store.add_session(session(_id(5), "orphan"))


# --- profiles and viewed posts ---


def test_save_profile_replaces_the_whole_record(store: SqliteUserDataStore) -> None:
    profile = store.get_profile(ADMIN_ID)
    changed = profile.model_copy(
        update={"room": profile.room.model_copy(update={"areas": [30, 31]})}
    )
    store.save_profile(changed)
    assert store.get_profile(ADMIN_ID) == changed
    assert store.get_profile(_id(5)) is None


def test_a_stored_version_1_profile_is_read_as_version_2(store: SqliteUserDataStore) -> None:
    """#317: the one stored profile (Ron's) is version 1 with both switches off; it reads as
    version 2 with the profile's switch off, and the stored row is not rewritten by the read."""
    data = new_profile(ADMIN_ID, NOW).model_dump(mode="json")
    del data["include_sublets"]
    data["schema_version"] = 1
    for name in ("room", "whole_apartment"):
        data[name]["include_sublets"] = False
    stored = json.dumps(data)
    with closing(sqlite3.connect(store._path)) as conn, conn:
        conn.execute("UPDATE profiles SET doc = ? WHERE user_id = ?", (stored, ADMIN_ID))
    assert store.get_profile(ADMIN_ID) == new_profile(ADMIN_ID, NOW)
    with closing(sqlite3.connect(store._path)) as conn:
        (doc,) = conn.execute("SELECT doc FROM profiles WHERE user_id = ?", (ADMIN_ID,)).fetchone()
    assert doc == stored


def test_viewed_keeps_the_first_time_and_is_unmarked(store: SqliteUserDataStore) -> None:
    store.mark_viewed(ADMIN_ID, "p1", NOW)
    store.mark_viewed(ADMIN_ID, "p1", NOW + timedelta(days=1))
    store.mark_viewed(ADMIN_ID, "p2", NOW)
    assert store.viewed_listing_ids(ADMIN_ID) == {"p1", "p2"}
    with closing(sqlite3.connect(store._path)) as conn:
        (doc,) = conn.execute("SELECT doc FROM viewed_posts WHERE listing_id = 'p1'").fetchone()
    assert '"viewed_at":"2026-10-10T09:00:00Z"' in doc
    store.unmark_viewed(ADMIN_ID, ["p1", "p3"])
    assert store.viewed_listing_ids(ADMIN_ID) == {"p2"}


# --- reports ---


def test_one_open_report_per_reporter_and_post(store: SqliteUserDataStore) -> None:
    first = store.add_report(report(1, ADMIN_ID))
    with pytest.raises(OpenReportExists):
        store.add_report(report(2, ADMIN_ID))
    restored = first.model_copy(
        update={"status": "restored", "resolved_by": ADMIN_ID, "resolved_at": NOW}
    )
    store.save_report(restored, expected=first)
    assert store.add_report(report(3, ADMIN_ID))  # after a restore the user can report again (R4)
    assert [r.report_id for r in store.find_reports(LISTING_ID)] == [_id(1001), _id(1003)]
    assert store.find_reports(status="restored") == [restored]
    assert store.find_reports(listing_id="other") == []


def test_save_report_is_compare_and_set(store: SqliteUserDataStore) -> None:
    first = store.add_report(report(1, ADMIN_ID))
    left = first.model_copy(
        update={"status": "left_out", "resolved_by": ADMIN_ID, "resolved_at": NOW}
    )
    store.save_report(left, expected=first)
    with pytest.raises(StaleRecordError):
        store.save_report(first.model_copy(update={"note": "x"}), expected=first)
    with pytest.raises(ValueError, match="open"):
        store.add_report(left)


# --- corrections ---


def test_one_correction_in_force_per_post_and_field(store: SqliteUserDataStore) -> None:
    first = store.add_correction(correction(1))
    with pytest.raises(CorrectionInForce):
        store.add_correction(correction(2))
    rooms = {"model_value": {"state": "unclear", "value": None}}
    store.add_correction(
        correction(3, field="rooms", **rooms, corrected_value={"state": "written", "value": 3.0})
    )
    removed = first.model_copy(update={"removed_by": ADMIN_ID, "removed_at": NOW})
    store.save_correction(removed, expected=first)
    second = store.add_correction(correction(2))
    in_force = store.find_corrections(LISTING_ID)
    assert {c.correction_id for c in in_force} == {_id(2003), second.correction_id}
    every = store.find_corrections(LISTING_ID, in_force=False)
    assert [c.correction_id for c in every] == [_id(2001), _id(2003), _id(2002)]
    assert every[0] == removed  # kept, marked removed (#255, #284)


def test_a_removed_correction_is_not_put_back(store: SqliteUserDataStore) -> None:
    first = store.add_correction(correction(1))
    removed = store.save_correction(
        first.model_copy(update={"removed_by": ADMIN_ID, "removed_at": NOW}), expected=first
    )
    with pytest.raises(ValueError, match="back in force"):
        store.save_correction(first, expected=removed)
    with pytest.raises(StaleRecordError):
        store.save_correction(removed, expected=first)


# --- the layout, and the seams kept apart ---


def test_a_layout_row_and_refusal_on_a_mismatch(path: Path) -> None:
    SqliteUserDataStore(path)
    with closing(sqlite3.connect(path)) as conn:
        rows = conn.execute("SELECT module, version FROM layout_version").fetchall()
        # Gate F's own row (#453) and HiddenPost's (#468)
        assert rows == [("userdata", 2), ("userdata.telegram", 1), ("userdata.hidden", 1)]
        conn.execute("UPDATE layout_version SET version = 3 WHERE module = 'userdata'")
        conn.commit()
    with pytest.raises(RuntimeError, match="'userdata' expects layout version 2, found 3"):
        SqliteUserDataStore(path)


def test_the_hidden_row_and_table_are_created_when_absent_and_left_alone_after(
    path: Path,
) -> None:
    """#468, appendix A point 8: a store laid out before `HiddenPost` (no `hidden_posts`, no row
    `userdata.hidden`) gains both at its next open, and nothing else changes; a second open leaves
    them as they are, a mark kept."""
    store = SqliteUserDataStore(path)
    store.create_admin(admin(), new_profile(ADMIN_ID, NOW))
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("DROP TABLE hidden_posts")
        conn.execute("DELETE FROM layout_version WHERE module = 'userdata.hidden'")
        conn.commit()
        before = conn.execute("SELECT module, version FROM layout_version").fetchall()
    store = SqliteUserDataStore(path)
    assert store.hidden_listing_ids(ADMIN_ID) == set()
    store.hide(ADMIN_ID, "a" * 64, NOW)
    with closing(sqlite3.connect(path)) as conn:
        after = conn.execute("SELECT module, version FROM layout_version").fetchall()
    assert after == [*before, ("userdata.hidden", 1)]
    again = SqliteUserDataStore(path)
    assert again.hidden_listing_ids(ADMIN_ID) == {"a" * 64}
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT module, version FROM layout_version").fetchall() == after
        conn.execute("UPDATE layout_version SET version = 2 WHERE module = 'userdata.hidden'")
        conn.commit()
    with pytest.raises(RuntimeError, match="'userdata.hidden' expects layout version 1, found 2"):
        SqliteUserDataStore(path)


def test_hide_keeps_the_first_time_and_unhide_takes_every_post_of_the_card(path: Path) -> None:
    """#464, #468: per user; pressing again keeps the first `hidden_at`; "בטל הסתרה" deletes the
    marks on every post given (the card's)."""
    store = SqliteUserDataStore(path)
    store.create_admin(admin(), new_profile(ADMIN_ID, NOW))
    store.hide(ADMIN_ID, "a" * 64, NOW)
    store.hide(ADMIN_ID, "a" * 64, NOW + timedelta(hours=1))
    store.hide(ADMIN_ID, "b" * 64, NOW)
    with closing(sqlite3.connect(path)) as conn:
        (doc,) = conn.execute(
            "SELECT doc FROM hidden_posts WHERE listing_id = ?", ("a" * 64,)
        ).fetchone()
    assert HiddenPost.model_validate_json(doc).hidden_at == NOW
    assert store.hidden_listing_ids(ADMIN_ID) == {"a" * 64, "b" * 64}
    assert store.viewed_listing_ids(ADMIN_ID) == set()  # its own record, not the viewed one
    store.unhide(ADMIN_ID, ["a" * 64, "b" * 64, "c" * 64])
    assert store.hidden_listing_ids(ADMIN_ID) == set()


def test_a_userdata_layout_1_is_refused_with_the_migration_command(path: Path) -> None:
    """#316: a file laid out before the counter is refused until it is migrated."""
    SqliteUserDataStore(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("UPDATE layout_version SET version = 1 WHERE module = 'userdata'")
        conn.commit()
    with pytest.raises(RuntimeError, match="found 1.*add_store_generation"):
        SqliteUserDataStore(path)


def _other_tables(path: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(path)) as conn:
        return {
            table: conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("raw_posts", "post_lifecycle", "listings", "group_watermarks")
        }


def test_the_user_data_store_never_touches_the_post_tables(path: Path, posts) -> None:
    """Invariants 12 and 14: what users write is never on a post."""
    repository = SqliteRepository(path)
    for post in posts[:3]:
        repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    repository.save_classification(
        make_listing(posts[0].listing_id),
        initial_lifecycle(posts[0]).model_copy(update={"state": "active"}),
        expected=repository.get_lifecycle(posts[0].listing_id),
    )
    SqliteWatermarkStore(path)
    before = _other_tables(path)

    store = SqliteUserDataStore(path)
    store.create_admin(admin(), new_profile(ADMIN_ID, NOW))
    store.add_session(session(ADMIN_ID, "t"))
    store.mark_viewed(ADMIN_ID, posts[0].listing_id, NOW)
    store.add_report(report(1, ADMIN_ID).model_copy(update={"listing_id": posts[0].listing_id}))
    store.add_correction(correction(1).model_copy(update={"listing_id": posts[0].listing_id}))

    assert _other_tables(path) == before
