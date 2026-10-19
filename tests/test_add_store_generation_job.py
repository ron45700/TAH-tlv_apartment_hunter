"""`jobs/add_store_generation.py` (DECISIONS.md #316), the one-time migration that installs the
store generation counter, against temporary stores only: never the production store."""

import hashlib
import io
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME, make_listing, sqlite_dump
from tests.test_userdata_store import ADMIN_ID, NOW, admin, correction
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.jobs import add_store_generation
from tlv_hunter.jobs.common import CONFIG_ROOT
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

CLOCK = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)
STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
COUNTED = ("raw_posts", "post_lifecycle", "listings", "corrections")
ALL_TABLES = (*COUNTED, "users", "profiles", "sessions", "viewed_posts", "group_watermarks")


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / STORE_ROOT / SQLITE_FILENAME
    path.parent.mkdir(parents=True)
    return path


def _filled(path: Path, posts, *, with_userdata: bool = True) -> None:
    """A store with posts, a classification, a watermark table, and (optionally) the admin and a
    correction."""
    repository = SqliteRepository(path)
    for post in posts[:3]:
        repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    lifecycle = repository.get_lifecycle(posts[0].listing_id)
    repository.save_classification(
        make_listing(posts[0].listing_id),
        lifecycle.model_copy(update={"state": "active"}),
        expected=lifecycle,
    )
    SqliteWatermarkStore(path)
    if with_userdata:
        store = SqliteUserDataStore(path)
        store.create_admin(admin(), new_profile(ADMIN_ID, NOW))
        store.add_correction(correction(1))


def _as_layout_1(path: Path) -> None:
    """The file as every round before round 9 left it: no counter table, no triggers, layout 1."""
    with closing(sqlite3.connect(path)) as conn, conn:
        names = conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall()
        for (name,) in names:
            conn.execute(f"DROP TRIGGER {name}")
        conn.execute("DROP TABLE store_generation")
        conn.execute("UPDATE layout_version SET version = 1 WHERE module != 'state'")


def _layout(path: Path) -> dict[str, int]:
    with closing(sqlite3.connect(path)) as conn:
        return dict(conn.execute("SELECT module, version FROM layout_version").fetchall())


def _contents(path: Path) -> dict[str, list[tuple]]:
    with closing(sqlite3.connect(path)) as conn:
        present = {name for (name,) in conn.execute("SELECT name FROM sqlite_master")}
        return {
            table: conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ALL_TABLES
            if table in present
        }


def _triggers(path: Path) -> set[str]:
    with closing(sqlite3.connect(path)) as conn:
        return {
            name
            for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _backups(path: Path) -> list[Path]:
    return sorted(path.parent.glob("*.backup*"))


def _run(tmp_path: Path) -> tuple[int, str]:
    stream = io.StringIO()
    code = add_store_generation.main(
        [], config_root=CONFIG_ROOT, repo_root=tmp_path, clock=lambda: CLOCK, stream=stream
    )
    return code, stream.getvalue()


def test_it_migrates_after_a_backup_and_changes_no_record(
    tmp_path: Path, database: Path, posts
) -> None:
    _filled(database, posts)
    _as_layout_1(database)
    contents = _contents(database)
    dump = sqlite_dump(database)

    code, output = _run(tmp_path)

    assert code == 0, output
    (backup,) = _backups(database)
    assert backup.name == "tlv_hunter.2026-10-12.backup.sqlite3"
    assert sqlite_dump(backup) == dump  # the store before, row for row (#424 point 89)
    # Gate F's tables (#453) have their own row, which the migration leaves as it is.
    telegram = {"userdata.telegram": 1, "userdata.hidden": 1}  # and HiddenPost's (#468)
    assert _layout(backup) == {
        "store": 1,
        "store.listings": 1,
        "userdata": 1,
        "state": 1,
        **telegram,
    }
    assert _layout(database) == {
        "store": 2,
        "store.listings": 2,
        "userdata": 2,
        "state": 1,
        **telegram,
    }
    assert _contents(database) == contents
    assert _triggers(database) == {
        f"{table}_generation_{event}"
        for table in COUNTED
        for event in ("insert", "update", "delete")
    }
    assert "stored RawPost documents identical to the backup's: True" in output
    assert "store generation: 0" in output
    assert output.index("backup:") < output.index("migrated:")


def test_after_the_migration_the_counter_moves_and_every_opener_opens(
    tmp_path: Path, database: Path, posts
) -> None:
    _filled(database, posts)
    _as_layout_1(database)
    assert _run(tmp_path)[0] == 0
    repository = SqliteRepository(database)
    SqliteRepository(database, read_only=True)
    store = SqliteUserDataStore(database)
    repository.upsert(posts[0])
    store.add_correction(correction(2, listing_id=posts[1].listing_id))
    assert repository.store_generation() == 2


def test_a_second_run_is_refused_and_writes_nothing(tmp_path: Path, database: Path, posts) -> None:
    _filled(database, posts)
    _as_layout_1(database)
    assert _run(tmp_path)[0] == 0
    before = _sha256(database)

    code, output = _run(tmp_path)

    assert code == 1
    assert "refused: the store is already migrated" in output
    assert len(_backups(database)) == 1
    assert _sha256(database) == before


def test_a_new_file_is_already_at_the_new_layout(tmp_path: Path, database: Path, posts) -> None:
    _filled(database, posts)
    code, output = _run(tmp_path)
    assert code == 1 and "already migrated" in output
    assert _backups(database) == []


def test_every_opener_refuses_an_unmigrated_file_and_names_the_command(
    database: Path, posts
) -> None:
    _filled(database, posts)
    _as_layout_1(database)
    before = _sha256(database)
    for opener in (
        lambda: SqliteRepository(database),
        lambda: SqliteRepository(database, read_only=True),
        lambda: SqliteUserDataStore(database),
    ):
        with pytest.raises(RuntimeError, match="found 1.*add_store_generation"):
            opener()
    assert _sha256(database) == before


def test_a_file_with_no_user_data_yet_is_migrated_and_lays_it_out_later(
    tmp_path: Path, database: Path, posts
) -> None:
    _filled(database, posts, with_userdata=False)
    _as_layout_1(database)
    code, output = _run(tmp_path)
    assert code == 0, output
    assert "migrated: store, store.listings" in output
    assert _layout(database) == {"store": 2, "store.listings": 2, "state": 1}
    store = SqliteUserDataStore(database)  # lays out userdata at version 2, with its trigger
    store.add_correction(correction(1))
    assert SqliteRepository(database).store_generation() == 1


@pytest.mark.parametrize(
    ("module", "version"), [("store", 0), ("store.listings", 2), ("userdata", 3)]
)
def test_any_other_layout_is_refused_before_the_backup(
    tmp_path: Path, database: Path, posts, module: str, version: int
) -> None:
    _filled(database, posts)
    _as_layout_1(database)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("UPDATE layout_version SET version = ? WHERE module = ?", (version, module))
    before = _sha256(database)
    code, output = _run(tmp_path)
    assert code == 1
    assert "refused: expected layout version 1" in output
    assert _backups(database) == [] and _sha256(database) == before


def test_no_store_is_refused(tmp_path: Path, database: Path) -> None:
    code, output = _run(tmp_path)
    assert code == 1 and "no store at" in output
    assert not database.exists()
