"""Retention (`PHASE_5.md` points 1–4; DECISIONS.md #471; invariant 3; `BASELINE.md` §5): the rule
(`tlv_hunter/retention.py`: archive at 25 days, delete at 40, from the canonical's last
publication; duplicates follow their canonical; flagged, reported and open-report posts never
deleted, their photos still deleted at archive) and the command (`jobs/retention.py`: a dry run
that writes nothing, `--apply` after a backup, by compare and set, the users' marks deleted with
their post, the orphan sweep). Temporary stores; photos are a few bytes on disk."""

import io
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import (
    CONFIG_ROOT,
    SQLITE_FILENAME,
    AnotherWriterFirst,
    overwrite_lifecycle,
    sqlite_dump,
)
from tests.test_gate_d import add, add_pending, make_member, make_post
from tests.test_userdata_store import ADMIN_ID, admin
from tlv_hunter.contracts.classification_report import (
    CLASSIFICATION_REPORT_SCHEMA_VERSION,
    ClassificationReport,
)
from tlv_hunter.contracts.post_lifecycle import PostImage, PostLifecycle
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.jobs import retention as job
from tlv_hunter.jobs.common import raw_post_rows
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.retention import ARCHIVE_AFTER, DELETE_AFTER, plan
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)
FRESH, OLD, GONE = NOW - timedelta(days=10), NOW - timedelta(days=26), NOW - timedelta(days=41)


def flagged(record: PostLifecycle, reason: str = "flagged") -> PostLifecycle:
    return PostLifecycle.model_validate(
        {
            **record.model_dump(),
            "state": "rejected",
            "rejection_reason": reason,
            "flagged_by": ADMIN_ID,
            "flagged_at": record.last_published_at,
        }
    )


# --- the rule ---


def test_the_ages_are_25_and_40_days() -> None:
    assert (ARCHIVE_AFTER, DELETE_AFTER) == (timedelta(days=25), timedelta(days=40))


def in_memory(*entries: tuple[RawPost, PostLifecycle]) -> tuple[list[RawPost], dict]:
    return [post for post, _ in entries], {post.listing_id: record for post, record in entries}


def test_the_plan_archives_at_25_days_and_deletes_at_40_with_the_duplicates() -> None:
    fresh = make_post(1, "fresh words", at=FRESH)
    old = make_post(2, "old words", at=OLD)
    gone = make_post(3, "gone words", at=GONE)
    copy = make_post(4, "gone copy words", at=GONE, canonical=False).with_changes(
        duplicate_of=gone.listing_id
    )
    posts, records = in_memory(*((p, initial_lifecycle(p)) for p in (fresh, old, gone, copy)))
    result = plan(posts, records, set(), NOW)
    assert [g.canonical for g in result.archive] == [old.listing_id]
    assert result.to_delete == (copy.listing_id, gone.listing_id)  # duplicates first
    assert result.kept == ()


@pytest.mark.parametrize("why", ["flagged", "misclassified", "open_report"])
def test_a_flagged_or_reported_post_is_never_deleted_but_its_photos_go(why: str) -> None:
    post = make_post(1, "kept words", at=GONE)
    record = initial_lifecycle(post).model_copy(
        update={
            "images": [
                PostImage(
                    listing_id=post.listing_id,
                    media_id="m",
                    local_path="images/x/a.jpg",
                    error=None,
                )
            ]
        }
    )
    if why != "open_report":
        record = flagged(record, why)
    posts, records = in_memory((post, record))
    result = plan(posts, records, {post.listing_id} if why == "open_report" else set(), NOW)
    assert result.delete == ()
    assert [g.exempt_because for g in result.kept] == [why]
    assert [g.canonical for g in result.archive] == [post.listing_id]


def test_an_archived_post_with_no_photos_waits_for_its_deletion() -> None:
    post = make_post(1, "archived words", at=OLD)
    record = initial_lifecycle(post).model_copy(update={"state": "archived"})
    posts, records = in_memory((post, record))
    assert plan(posts, records, set(), NOW).archive == ()


def test_a_duplicate_whose_canonical_is_not_stored_keeps_its_own_clock() -> None:
    lost = make_post(5, "lost copy words", at=GONE, canonical=False).with_changes(
        duplicate_of="f" * 64
    )
    posts, records = in_memory((lost, initial_lifecycle(lost)))
    assert plan(posts, records, set(), NOW).to_delete == (lost.listing_id,)


# --- the command ---


class Shelf:
    """A store under `<repo>/data/store`, as the job finds it: a fresh post, an old one with a
    duplicate and photos, a gone one with photos and users' marks, a gone flagged one with a
    photo, a gone one with an open report, two orphan files (one young)."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.root = repo / "data" / "store"
        self.root.mkdir(parents=True)
        self.db = self.root / SQLITE_FILENAME
        self.repository = SqliteRepository(self.db)
        self.userdata = SqliteUserDataStore(self.db)
        self.userdata.create_admin(admin(), new_profile(ADMIN_ID, NOW))
        fresh = make_member(1, price=[5000], areas=[30], at=FRESH)
        old = make_member(2, price=[6000], areas=[30], at=OLD)
        gone = make_member(3, price=[7000], areas=[30], at=GONE)
        kept = make_member(4, price=[8000], areas=[30], at=GONE)
        reported = make_member(5, price=[9000], areas=[30], at=GONE)
        for member in (fresh, old, gone, kept, reported):
            add(self.repository, member)
        copy = make_post(6, "old copy words", at=OLD, canonical=False).with_changes(
            duplicate_of=old.listing_id
        )
        add_pending(self.repository, copy)
        self.fresh, self.old, self.gone = fresh.listing_id, old.listing_id, gone.listing_id
        self.kept, self.reported, self.copy = kept.listing_id, reported.listing_id, copy.listing_id
        for listing_id in (self.fresh, self.old, self.copy, self.gone, self.kept):
            self.photo(listing_id)
        stored = self.repository.get_lifecycle(self.kept)
        assert stored is not None
        overwrite_lifecycle(self.repository, flagged(stored))
        self.userdata.add_report(
            ClassificationReport(
                schema_version=CLASSIFICATION_REPORT_SCHEMA_VERSION,
                report_id="c" * 32,
                listing_id=self.reported,
                reported_by=ADMIN_ID,
                reported_at=GONE,
                fields=["price"],
                note=None,
                status="open",
                resolved_by=None,
                resolved_at=None,
            )
        )
        self.userdata.mark_viewed(ADMIN_ID, self.gone, NOW)
        self.userdata.hide(ADMIN_ID, self.gone, NOW)
        self.userdata.mark_viewed(ADMIN_ID, self.fresh, NOW)
        self.orphan = self.file("images/" + "e" * 64 + "/x.jpg", age=timedelta(days=2))
        self.young_orphan = self.file("images/" + "e" * 64 + "/y.jpg", age=timedelta(hours=1))

    def file(self, relative: str, age: timedelta = timedelta(days=30)) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\xd8 photo")
        stamp = (NOW - age).timestamp()
        os.utime(path, (stamp, stamp))
        return path

    def photo(self, listing_id: str) -> None:
        relative = f"images/{listing_id}/a1.jpg"
        self.file(relative)
        stored = self.repository.get_lifecycle(listing_id)
        assert stored is not None
        image = PostImage(listing_id=listing_id, media_id="m1", local_path=relative, error=None)
        overwrite_lifecycle(self.repository, stored.model_copy(update={"images": [image]}))


@pytest.fixture
def shelf(tmp_path: Path) -> Shelf:
    return Shelf(tmp_path / "repo")


def run_job(shelf: Shelf, *argv: str) -> tuple[int, str]:
    out = io.StringIO()
    code = job.main(
        list(argv), config_root=CONFIG_ROOT, repo_root=shelf.repo, clock=lambda: NOW, stream=out
    )
    return code, out.getvalue()


def test_a_dry_run_writes_nothing_and_says_what_apply_would_do(shelf: Shelf) -> None:
    before = sqlite_dump(shelf.db)
    files = sorted(p for p in shelf.root.rglob("*") if p.is_file())
    code, out = run_job(shelf)
    assert code == 0
    assert sqlite_dump(shelf.db) == before
    assert sorted(p for p in shelf.root.rglob("*") if p.is_file()) == files
    assert "retention DRY RUN" in out
    # The old one; the flagged one's and the reported one's photos (kept, but archived).
    assert "ARCHIVE: 3 posts" in out
    assert "1 duplicates with them" in out
    assert "DELETE: 1 posts and 0 duplicates" in out
    assert "KEPT past 40 days by an exemption: 2 {'flagged': 1, 'open_report': 1}" in out
    assert "ORPHAN photo files (no record names them, older than 24 hours): 1," in out
    assert shelf.gone[:12] in out


def test_apply_archives_deletes_and_sweeps_after_a_backup(shelf: Shelf) -> None:
    kept_rows = {row[0]: row for row in raw_post_rows(shelf.db) if row[0] != shelf.gone}
    code, out = run_job(shelf, "--apply")
    assert code == 0, out
    assert list(shelf.root.glob("tlv_hunter.*.backup.sqlite3"))
    repository = SqliteRepository(shelf.db)
    # Archived: the canonical's state, no photo entries, its files gone; the duplicate's photos
    # go with it, its record otherwise unchanged.
    old = repository.get_lifecycle(shelf.old)
    assert old is not None and old.state == "archived" and old.images == []
    assert not (shelf.root / f"images/{shelf.old}/a1.jpg").exists()
    copy = repository.get_lifecycle(shelf.copy)
    assert copy is not None and copy.state == "pending" and copy.images == []
    # Deleted: the post, its record, its Listing, its photo folder, the users' marks.
    assert repository.get(shelf.gone) is None
    assert repository.get_lifecycle(shelf.gone) is None
    assert repository.get_listing(shelf.gone) is None
    assert not (shelf.root / f"images/{shelf.gone}").exists()
    assert shelf.userdata.viewed_listing_ids(ADMIN_ID) == {shelf.fresh}
    assert shelf.userdata.hidden_listing_ids(ADMIN_ID) == set()
    # Kept: the flagged post whole but its photo; the reported one; the fresh one untouched.
    kept = repository.get_lifecycle(shelf.kept)
    assert kept is not None and kept.rejection_reason == "flagged" and kept.images == []
    assert repository.get(shelf.reported) is not None
    assert (shelf.root / f"images/{shelf.fresh}/a1.jpg").exists()
    # The orphan sweep: the old orphan only.
    assert not shelf.orphan.exists() and shelf.young_orphan.exists()
    # Nothing else touched a stored post (invariant 14): the kept rows are identical.
    assert {row[0]: row for row in raw_post_rows(shelf.db)} == kept_rows
    # A second pass finds nothing more to do.
    before = sqlite_dump(shelf.db)
    assert run_job(shelf, "--apply")[0] == 0
    assert [s for s in sqlite_dump(shelf.db) if "layout" not in s] == [
        s for s in before if "layout" not in s
    ]


def test_a_record_another_writer_changed_is_skipped(
    shelf: Shelf, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = SqliteRepository

    def repository(path: Path, *, read_only: bool = False) -> Any:
        inner = real(path, read_only=read_only)
        return inner if read_only else AnotherWriterFirst(inner, times=1)

    monkeypatch.setattr(job, "SqliteRepository", repository)
    code, out = run_job(shelf, "--apply")
    assert code == 0 and "archive skipped: changed 1" in out
    # The first record in the plan's order (the flagged one) met the other writer: it keeps its
    # photo and its entry; the others were archived.
    assert (shelf.root / f"images/{shelf.kept}/a1.jpg").exists()
    kept = SqliteRepository(shelf.db).get_lifecycle(shelf.kept)
    assert kept is not None and len(kept.images) == 1
    assert not (shelf.root / f"images/{shelf.old}/a1.jpg").exists()


def test_as_of_is_a_dry_run_only_and_a_copy_can_be_planned(shelf: Shelf, tmp_path: Path) -> None:
    code, out = run_job(shelf, "--apply", "--as-of", "2027-01-01")
    assert code == 1 and out.startswith("refused: --as-of is for a dry run only")
    code, out = run_job(shelf, "--as-of", "2026-11-20")  # 19 days before NOW: nothing gone yet
    assert code == 0 and "DELETE: 0 posts" in out
    copy = tmp_path / "copy" / SQLITE_FILENAME
    copy.parent.mkdir()
    copy.write_bytes(shelf.db.read_bytes())
    code, out = run_job(shelf, "--database", str(copy))
    assert code == 0 and "DELETE: 1 posts" in out and str(copy) in out
    code, out = run_job(shelf, "--database", str(tmp_path / "missing.sqlite3"))
    assert code == 1 and "no store at" in out
