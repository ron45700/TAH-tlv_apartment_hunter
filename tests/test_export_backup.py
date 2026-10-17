"""`jobs/export_backup.py` (`PHASE_3.md` 3.9 (k) 8; DECISIONS.md #424, point 93), against temporary
stores only: never the production store."""

import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME
from tlv_hunter.jobs import export_backup
from tlv_hunter.jobs.common import raw_post_rows
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.store.sqlite import SqliteRepository

NOW = datetime(2026, 10, 16, 21, 0, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path: Path, posts) -> Path:
    root = tmp_path / "app"
    database = root / "data" / "store" / SQLITE_FILENAME
    database.parent.mkdir(parents=True)
    repository = SqliteRepository(database)
    for post in posts[:2]:
        repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    return root


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_it_exports_a_fresh_checked_backup(repo: Path) -> None:
    out = io.StringIO()
    assert export_backup.main([], repo_root=repo, clock=lambda: NOW, stream=out) == 0
    name = "tlv_hunter.2026-10-16.backup.sqlite3"
    backup = repo / "data" / "store" / name
    exported = repo / "data" / "store_exports" / name
    assert backup.is_file() and exported.is_file()
    assert _sha256(exported) == _sha256(backup)
    assert raw_post_rows(exported) == raw_post_rows(repo / "data" / "store" / SQLITE_FILENAME)
    assert f"exported: {exported}" in out.getvalue()


def test_it_overwrites_nothing(repo: Path) -> None:
    exports = repo / "data" / "store_exports"
    exports.mkdir(parents=True)
    earlier = exports / "tlv_hunter.2026-10-16T210000.backup.sqlite3"
    earlier.write_bytes(b"an earlier export")
    out = io.StringIO()
    assert export_backup.main([], repo_root=repo, clock=lambda: NOW, stream=out) == 0
    # The second export the same day: its backup gets the time, and that name is already taken.
    assert export_backup.main([], repo_root=repo, clock=lambda: NOW, stream=out) == 1
    assert "not overwritten" in out.getvalue()
    assert earlier.read_bytes() == b"an earlier export"


def test_it_refuses_when_there_is_no_store(tmp_path: Path) -> None:
    out = io.StringIO()
    assert export_backup.main([], repo_root=tmp_path, clock=lambda: NOW, stream=out) == 1
    assert "no store at" in out.getvalue()
    assert not (tmp_path / "data" / "store_exports").exists()


def test_it_exports_only_the_photos_not_yet_exported_and_never_overwrites(repo: Path) -> None:
    """#427 point 99: new photo files are copied; one already exported is left as it is; nothing
    is deleted from the exports."""
    images = repo / "data" / "store" / "images"
    (images / "a").mkdir(parents=True)
    (images / "a" / "0.jpg").write_bytes(b"photo a0")
    (images / "a" / "1.jpg").write_bytes(b"photo a1")
    exported = repo / "data" / "store_exports" / "images"
    (exported / "a").mkdir(parents=True)
    (exported / "a" / "0.jpg").write_bytes(b"exported earlier")
    (exported / "gone").mkdir()
    (exported / "gone" / "0.jpg").write_bytes(b"a photo no longer in the store")

    out = io.StringIO()
    assert export_backup.main([], repo_root=repo, clock=lambda: NOW, stream=out) == 0
    assert "photos: 1 new exported, 1 already there" in out.getvalue()
    assert (exported / "a" / "1.jpg").read_bytes() == b"photo a1"
    assert (exported / "a" / "0.jpg").read_bytes() == b"exported earlier"  # not overwritten
    assert (exported / "gone" / "0.jpg").is_file()  # not deleted

    (images / "b").mkdir()
    (images / "b" / "0.jpg").write_bytes(b"photo b0")
    later = datetime(2026, 10, 17, 21, 0, tzinfo=UTC)
    again = io.StringIO()
    assert export_backup.main([], repo_root=repo, clock=lambda: later, stream=again) == 0
    assert "photos: 1 new exported, 2 already there" in again.getvalue()
    assert (exported / "b" / "0.jpg").read_bytes() == b"photo b0"
