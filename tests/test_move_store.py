"""`jobs/move_store.py` (`PHASE_3.md` 3.9 (k) 5; DECISIONS.md #416), the one-time move of the store
into the Docker volume, against temporary folders only: never the production store."""

import hashlib
import io
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME, make_listing
from tests.test_userdata_store import ADMIN_ID, NOW, admin
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.jobs import move_store
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def source(tmp_path: Path, posts) -> Path:
    """A store as the Windows folder holds it: the database, photos, a run's files, a reclassify
    report, an old backup and a site copy (the last two are not moved)."""
    root = tmp_path / "import"
    root.mkdir()
    database = root / SQLITE_FILENAME
    repository = SqliteRepository(database)
    for post in posts[:3]:
        repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    lifecycle = repository.get_lifecycle(posts[0].listing_id)
    repository.save_classification(
        make_listing(posts[0].listing_id),
        lifecycle.model_copy(update={"state": "active"}),
        expected=lifecycle,
    )
    SqliteWatermarkStore(database)
    SqliteUserDataStore(database).create_admin(admin(), new_profile(ADMIN_ID, NOW))
    (root / "images" / posts[0].listing_id).mkdir(parents=True)
    (root / "images" / posts[0].listing_id / "0.jpg").write_bytes(b"\xff\xd8 a photo")
    (root / "classify_runs").mkdir()
    (root / "classify_runs" / "run.jsonl").write_text("{}\n", encoding="utf-8")
    (root / "reclassify" / "r1").mkdir(parents=True)
    (root / "reclassify" / "r1" / "summary.json").write_text("{}", encoding="utf-8")
    (root / "tlv_hunter.2026-10-14.backup.sqlite3").write_bytes(b"an old backup")
    (root / "site").mkdir()
    (root / "site" / "tlv_hunter.2026-10-15.site.sqlite3").write_bytes(b"a copy")
    return root


def test_it_moves_the_store_and_every_check_passes(source: Path, tmp_path: Path) -> None:
    target = tmp_path / "volume"
    before = _sha256(source / SQLITE_FILENAME)
    out = io.StringIO()
    assert move_store.move(source, target, out) == 0
    output = out.getvalue()
    for name in (
        "integrity check ok",
        "RawPost rows identical",
        "every table's row count identical",
        "store generation identical",
        "layout versions identical",
        "every copied file identical",
        "source unchanged",
    ):
        assert f"check: {name}: True" in output
    assert "moved: the store is in" in output
    assert (target / SQLITE_FILENAME).is_file()
    assert (target / "images").is_dir() and (
        target / "reclassify" / "r1" / "summary.json"
    ).is_file()
    assert (target / "classify_runs" / "run.jsonl").is_file()
    # The old backups and the site's copies stay where they are.
    assert not (target / "site").exists()
    assert not list(target.glob("*.backup.sqlite3"))
    # The source was only read.
    assert _sha256(source / SQLITE_FILENAME) == before
    with closing(sqlite3.connect(target / SQLITE_FILENAME)) as conn:
        assert conn.execute("SELECT count(*) FROM raw_posts").fetchone() == (3,)
        assert conn.execute("SELECT count(*) FROM users").fetchone() == (1,)


def test_the_command_reads_its_source_and_writes_the_configured_store_root(
    source: Path, tmp_path: Path
) -> None:
    repo = tmp_path / "app"
    out = io.StringIO()
    assert move_store.main(["--source", str(source)], repo_root=repo, stream=out) == 0
    assert (repo / "data" / "store" / SQLITE_FILENAME).is_file()
    # A second run refuses: the target now holds a store.
    again = io.StringIO()
    assert move_store.main(["--source", str(source)], repo_root=repo, stream=again) == 1
    assert "already holds a store; nothing was written" in again.getvalue()


def test_it_refuses_a_target_that_already_holds_a_store(source: Path, tmp_path: Path) -> None:
    target = tmp_path / "volume"
    target.mkdir()
    (target / SQLITE_FILENAME).write_bytes(b"a store")
    with pytest.raises(move_store.Refused, match="already holds a store"):
        move_store.move(source, target, io.StringIO())
    assert (target / SQLITE_FILENAME).read_bytes() == b"a store"


def test_it_refuses_a_target_with_photos_already_in_it(source: Path, tmp_path: Path) -> None:
    target = tmp_path / "volume"
    (target / "images" / "x").mkdir(parents=True)
    (target / "images" / "x" / "0.jpg").write_bytes(b"other")
    with pytest.raises(move_store.Refused, match="already holds files"):
        move_store.move(source, target, io.StringIO())
    assert not (target / SQLITE_FILENAME).exists()


def test_it_refuses_a_missing_source_and_one_with_a_journal(tmp_path: Path, source: Path) -> None:
    with pytest.raises(move_store.Refused, match="no store at"):
        move_store.move(tmp_path / "nowhere", tmp_path / "volume", io.StringIO())
    (source / f"{SQLITE_FILENAME}-journal").write_bytes(b"")
    with pytest.raises(move_store.Refused, match="rollback journal"):
        move_store.move(source, tmp_path / "volume", io.StringIO())
    assert not (tmp_path / "volume").exists()


def test_a_photo_that_differs_fails_the_move_and_leaves_the_copy(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "volume"
    real_copytree = move_store.shutil.copytree

    def copytree_then_damage(src, dst, *args, **kwargs):  # it calls itself for each subfolder
        real_copytree(src, dst, *args, **kwargs)
        for photo in Path(dst).rglob("*.jpg"):
            photo.write_bytes(b"damaged")

    monkeypatch.setattr(move_store.shutil, "copytree", copytree_then_damage)
    out = io.StringIO()
    assert move_store.move(source, target, out) == 1
    assert "check: every copied file identical: False" in out.getvalue()
    assert "the copy is left in" in out.getvalue()
    assert (target / SQLITE_FILENAME).is_file()
