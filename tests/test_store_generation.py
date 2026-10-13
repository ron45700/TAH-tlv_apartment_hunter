"""The store generation counter (DECISIONS.md #301, #316; `store_generation.py`): it moves on every
change of `raw_posts`, `post_lifecycle`, `listings` and `corrections`, through every store method
that writes them, and on nothing else. Temporary stores only."""

import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import timedelta
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME, make_listing
from tests.test_userdata_store import (
    ADMIN_ID,
    NOW,
    _hash,
    _with_friend,
    admin,
    correction,
    report,
    session,
    signup_key,
)
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / SQLITE_FILENAME


def moved(repository: SqliteRepository, write: Callable[[], object]) -> int:
    """How much `write` moved the counter."""
    before = repository.store_generation()
    write()
    return repository.store_generation() - before


def test_a_new_store_starts_at_zero_and_a_reader_sees_it(path: Path) -> None:
    SqliteRepository(path)
    assert SqliteRepository(path, read_only=True).store_generation() == 0


def test_every_repository_write_moves_it(path: Path, posts) -> None:
    repository = SqliteRepository(path)
    first, second = posts[0], posts[1]
    assert moved(repository, lambda: repository.upsert(first)) > 0
    # An upsert conflict with an unchanged value still moves it: the UPDATE trigger fires.
    assert moved(repository, lambda: repository.upsert(first)) > 0
    pending = initial_lifecycle(second)
    assert moved(repository, lambda: repository.upsert_with_lifecycle(second, pending)) > 0
    # Again: the post's upsert moves it once; the lifecycle's DO NOTHING changes no row.
    assert moved(repository, lambda: repository.upsert_with_lifecycle(second, pending)) == 1
    stored = repository.get_lifecycle(second.listing_id)
    later = stored.model_copy(
        update={"last_published_at": stored.last_published_at + timedelta(hours=1)}
    )
    assert moved(repository, lambda: repository.save_lifecycle(later, expected=stored)) > 0
    unchanged = repository.get_lifecycle(second.listing_id)
    assert moved(repository, lambda: repository.save_lifecycle(unchanged, expected=unchanged)) > 0
    active = unchanged.model_copy(update={"state": "active"})
    classified = moved(
        repository,
        lambda: repository.save_classification(
            make_listing(second.listing_id), active, expected=unchanged
        ),
    )
    assert classified == 2  # the listing and the lifecycle


def test_corrections_move_it_and_the_other_user_data_does_not(path: Path, posts) -> None:
    repository = SqliteRepository(path)
    store = SqliteUserDataStore(path)
    still = {
        "create_admin": lambda: store.create_admin(admin(), new_profile(ADMIN_ID, NOW)),
        "create_user": lambda: _with_friend(store),
        "save_user": lambda: store.save_user(
            store.get_user(ADMIN_ID).model_copy(update={"failed_sign_ins": 1}),
            expected=store.get_user(ADMIN_ID),
        ),
        "add_key": lambda: store.add_key(signup_key(7, "secret-7")),
        "save_key": lambda: store.save_key(
            store.find_key_by_hash(_hash("secret-7")).model_copy(update={"cancelled_at": NOW}),
            expected=store.find_key_by_hash(_hash("secret-7")),
        ),
        "add_session": lambda: store.add_session(session(ADMIN_ID, "t")),
        "end_session": lambda: store.end_session(_hash("t"), NOW),
        "end_sessions": lambda: store.end_sessions(ADMIN_ID, NOW),
        "save_profile": lambda: store.save_profile(
            store.get_profile(ADMIN_ID).model_copy(update={"include_sublets": True})
        ),
        "mark_viewed": lambda: store.mark_viewed(ADMIN_ID, posts[0].listing_id, NOW),
        "unmark_viewed": lambda: store.unmark_viewed(ADMIN_ID, [posts[0].listing_id]),
        "add_report": lambda: store.add_report(report(1, ADMIN_ID)),
        "save_report": lambda: store.save_report(
            report(1, ADMIN_ID, status="left_out", resolved_by=ADMIN_ID, resolved_at=NOW),
            expected=report(1, ADMIN_ID),
        ),
    }
    for name, write in still.items():
        assert moved(repository, write) == 0, name
    added = correction(1)
    assert moved(repository, lambda: store.add_correction(added)) == 1
    removed = added.model_copy(update={"removed_by": ADMIN_ID, "removed_at": NOW})
    assert moved(repository, lambda: store.save_correction(removed, expected=added)) == 1


def test_the_watermarks_do_not_move_it(path: Path) -> None:
    repository = SqliteRepository(path)
    watermarks = SqliteWatermarkStore(path)
    assert moved(repository, lambda: watermarks.save_all(watermarks.get_all())) == 0


@pytest.mark.parametrize("table", ["raw_posts", "post_lifecycle", "listings", "corrections"])
def test_a_delete_in_any_of_the_four_tables_moves_it(path: Path, posts, table: str) -> None:
    """No store method deletes yet (the retention job is Phase 5's); the trigger is there."""
    repository = SqliteRepository(path)
    store = SqliteUserDataStore(path)
    post = posts[0]
    repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    lifecycle = repository.get_lifecycle(post.listing_id)
    repository.save_classification(
        make_listing(post.listing_id),
        lifecycle.model_copy(update={"state": "active"}),
        expected=lifecycle,
    )
    store.add_correction(correction(1))

    def delete_only(name: str) -> int:
        with closing(sqlite3.connect(path)) as conn, conn:
            if name == "raw_posts":  # its children first, for the foreign keys
                conn.execute("DELETE FROM listings")
                conn.execute("DELETE FROM post_lifecycle")
            before = conn.execute("SELECT generation FROM store_generation").fetchone()[0]
            conn.execute(f"DELETE FROM {name}")
            return conn.execute("SELECT generation FROM store_generation").fetchone()[0] - before

    assert delete_only(table) == 1


def test_another_connection_moves_it_too(path: Path, posts) -> None:
    """The triggers are in the file, so a writer in another process moves the counter."""
    repository = SqliteRepository(path)
    repository.upsert(posts[0])
    before = repository.store_generation()
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("UPDATE raw_posts SET doc = doc")
    assert repository.store_generation() == before + 1


def test_the_user_data_store_can_lay_out_a_new_file_first(path: Path) -> None:
    """Whichever seam opens a new file first creates the counter's table; the other reuses it."""
    store = SqliteUserDataStore(path)
    store.add_correction(correction(1))
    repository = SqliteRepository(path)
    assert repository.store_generation() == 1
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("SELECT count(*) FROM store_generation").fetchone() == (1,)
