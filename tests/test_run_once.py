"""Task 1.14: `run_once` (DECISIONS.md #79). Every test runs against local_json and SQLite, with
`SqliteWatermarkStore`, a fake image transport and the socket guard in conftest. No network."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import (
    CONFIG_ROOT,
    KNOWN_DUPLICATE_PAIRS,
    SPIKE_1_1A_PREFIX,
    SQLITE_FILENAME,
    load_spike_1_1a,
    load_thedoor_items,
)
from tlv_hunter import pipeline
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.group_watermark import GroupWatermark
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.images import download
from tlv_hunter.images.download import ImageFetchError, ImageResponse, ImageWriteError
from tlv_hunter.pipeline import RunResult, run_once
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.providers.fixture import FixtureProvider
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.base import Repository
from tlv_hunter.store.local_json import LocalJsonRepository
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.watermark.window import BUFFER, MissingWatermarkError

GROUP_IDS = YamlConfig(CONFIG_ROOT).collection().group_ids
# Spike 1.1a run 1 started at this instant with a 24-hour window.
T0 = datetime(2026, 10, 3, 21, 32, 6, tzinfo=UTC)
WINDOW = timedelta(hours=24)
SPIKE_MAIN = SPIKE_1_1A_PREFIX.with_name(SPIKE_1_1A_PREFIX.name + ".json")
ZERO_ROW_GROUP = "5612809662118963"
MAX_POSTS_GROUP = "101875683484689"
JPEG = ImageResponse(200, "image/jpeg", b"\xff\xd8\xff\xe0" + b"jpeg body")
# The 2026-09-13 fixture: every post is earlier than this.
T20 = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
WINDOW_20 = timedelta(days=30)


class Crash(Exception):
    """Stands in for a run killed between two writes."""


class Cdn:
    """Serves every photo, or fails DNS on every call while `down` is set."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.down = False
        self.down_after: int | None = None

    def __call__(self, url: str) -> ImageResponse:
        self.calls.append(url)
        if self.down_after is not None and len(self.calls) > self.down_after:
            self.down = True
        if self.down:
            raise ImageFetchError("network: gaierror")
        return JPEG


@dataclass
class ListProvider:
    """Returns the given posts whatever the window, and records each call."""

    posts: Sequence[RawPost]
    calls: list[datetime] = field(default_factory=list)
    on_fetch: Callable[[], None] | None = None

    def fetch(self, group_ids: Sequence[str], since: datetime) -> list[RawPost]:
        self.calls.append(since)
        if self.on_fetch is not None:
            self.on_fetch()
        return list(self.posts)


class CrashingRepository:
    """Raises `Crash` instead of the write numbered `crash_at` (0-based); reads pass through.
    Records every write as (method, listing_id)."""

    def __init__(self, inner: Repository, crash_at: int | None = None) -> None:
        self._inner = inner
        self._crash_at = crash_at
        self.writes: list[tuple[str, str]] = []

    def _write(self, method: str, listing_id: str) -> None:
        if self._crash_at is not None and len(self.writes) == self._crash_at:
            raise Crash(f"killed before write {self._crash_at}")
        self.writes.append((method, listing_id))

    def upsert(self, post: RawPost) -> RawPost:
        self._write("upsert", post.listing_id)
        return self._inner.upsert(post)

    def upsert_with_lifecycle(self, post: RawPost, initial: PostLifecycle) -> RawPost:
        self._write("upsert_with_lifecycle", post.listing_id)
        return self._inner.upsert_with_lifecycle(post, initial)

    def save_lifecycle(self, record: PostLifecycle) -> PostLifecycle:
        self._write("save_lifecycle", record.listing_id)
        return self._inner.save_lifecycle(record)

    def get(self, listing_id: str) -> RawPost | None:
        return self._inner.get(listing_id)

    def get_lifecycle(self, listing_id: str) -> PostLifecycle | None:
        return self._inner.get_lifecycle(listing_id)

    def get_listing(self, listing_id: str) -> Listing | None:
        return self._inner.get_listing(listing_id)

    def find_without_lifecycle(self) -> list[RawPost]:
        return self._inner.find_without_lifecycle()

    def find_lifecycles_with_image_errors(self, prefixes: Sequence[str]) -> list[PostLifecycle]:
        return self._inner.find_lifecycles_with_image_errors(prefixes)

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]:
        return self._inner.find_by_hash(text_hash)

    def find_by_phone(self, phone: str) -> list[RawPost]:
        return self._inner.find_by_phone(phone)

    def query(self) -> list[RawPost]:
        return self._inner.query()


class FailingWatermarks(SqliteWatermarkStore):
    def save_all(self, records: Sequence[GroupWatermark]) -> None:
        raise OSError("disk I/O error")


@dataclass
class Store:
    """One store: a Repository, the watermark store on the same root, and the image files."""

    kind: str
    root: Path
    cdn: Cdn = field(default_factory=Cdn)
    slept: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)  # the entry's job in production

    @property
    def repository(self) -> Repository:
        if self.kind == "local_json":
            return LocalJsonRepository(self.root)
        return SqliteRepository(self.root / SQLITE_FILENAME)

    @property
    def watermarks(self) -> SqliteWatermarkStore:
        return SqliteWatermarkStore(self.root / SQLITE_FILENAME)

    def run(
        self,
        provider: Any,
        at: datetime,
        *,
        window: timedelta | None = None,
        max_posts: int = 50,
        repository: Repository | None = None,
        watermarks: SqliteWatermarkStore | None = None,
    ) -> RunResult:
        return run_once(
            provider=provider,
            repository=self.repository if repository is None else repository,
            watermarks=self.watermarks if watermarks is None else watermarks,
            group_ids=GROUP_IDS,
            max_posts=max_posts,
            store_root=self.root,
            clock=lambda: at,
            bootstrap_window=window,
            image_transport=self.cdn,
            image_sleep=self.slept.append,
        )

    def snapshot(self) -> dict[str, tuple[RawPost, PostLifecycle | None]]:
        repository = self.repository
        return {
            post.listing_id: (post, repository.get_lifecycle(post.listing_id))
            for post in repository.query()
        }

    def files(self) -> set[str]:
        images = self.root / download.IMAGES_DIR
        if not images.exists():
            return set()
        return {path.relative_to(self.root).as_posix() for path in images.rglob("*.*")}

    def referenced(self) -> set[str]:
        return {
            image.local_path
            for _, record in self.snapshot().values()
            if record is not None
            for image in record.images
            if image.local_path is not None
        }


@pytest.fixture(params=["local_json", "sqlite"])
def kind(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture
def store(kind: str, tmp_path: Path) -> Store:
    return Store(kind, tmp_path / "store")


def _posts_20(fetched_at: datetime = T20) -> list[RawPost]:
    return [to_raw_post(item, fetched_at) for item in load_thedoor_items()]


def _newest_first(posts: Sequence[RawPost]) -> list[RawPost]:
    """The provider's order (newest_posts): a duplicate comes before its canonical."""
    return sorted(posts, key=lambda post: post.posted_at, reverse=True)


def _pairs_batch() -> list[RawPost]:
    """The three known duplicate pairs and two more posts, newest first."""
    paired = {post_id for pair in KNOWN_DUPLICATE_PAIRS for post_id in pair}
    posts = _posts_20()
    batch = [post for post in posts if post.source_post_id in paired]
    batch += [post for post in posts if post.source_post_id not in paired][:2]
    return _newest_first(batch)


def _spike_main() -> FixtureProvider:
    load_spike_1_1a()  # a missing fixture fails here with its path, never skips
    return FixtureProvider(SPIKE_MAIN, lambda: T0)


# --- bootstrap ---------------------------------------------------------------------------------


def test_bootstrap_stores_every_post_with_its_record_and_creates_the_watermarks(
    store: Store,
) -> None:
    result = store.run(_spike_main(), T0, window=WINDOW)

    assert result.since == T0 - WINDOW
    expected = {to_raw_post(item, T0).listing_id for item in load_spike_1_1a()}
    snapshot = store.snapshot()
    assert set(snapshot) == expected and len(expected) == 105
    assert all(record is not None for _, record in snapshot.values())
    assert store.repository.find_without_lifecycle() == []
    assert all(post.is_canonical is not None for post, _ in snapshot.values())

    records = {record.group_id: record for record in store.watermarks.get_all()}
    assert list(records) == sorted(GROUP_IDS)
    assert all(record.last_success_at == T0 for record in records.values())
    assert records[ZERO_ROW_GROUP].consecutive_failures == 1
    assert records[ZERO_ROW_GROUP].watermark is None
    assert all(r.consecutive_failures == 0 for g, r in records.items() if g != ZERO_ROW_GROUP)

    assert store.cdn.calls and store.files() == store.referenced()


def test_a_group_at_max_posts_is_logged_as_cut_off(store: Store, caplog) -> None:
    with caplog.at_level(logging.WARNING):
        result = store.run(_spike_main(), T0, window=WINDOW, max_posts=30)
    assert [gap.group_id for gap in result.cut_off] == [MAX_POSTS_GROUP]
    lines = [r.getMessage() for r in caplog.records if "cut off" in r.getMessage()]
    assert len(lines) == 1 and lines[0].startswith(f"group {MAX_POSTS_GROUP} cut off: 30 rows")


def test_bootstrap_on_a_store_with_records_is_allowed_and_names_the_groups(
    store: Store, caplog
) -> None:
    store.run(ListProvider(_posts_20()), T20, window=WINDOW_20)
    with caplog.at_level(logging.WARNING):
        store.run(ListProvider(_posts_20()), T20 + timedelta(hours=1), window=WINDOW_20)
    warnings = [r.getMessage() for r in caplog.records if "already have" in r.getMessage()]
    assert len(warnings) == 1
    assert all(group_id in warnings[0] for group_id in GROUP_IDS)


# --- a normal run ------------------------------------------------------------------------------


def test_a_normal_run_with_no_record_fails_before_fetching(store: Store) -> None:
    provider = ListProvider(_posts_20())
    with pytest.raises(MissingWatermarkError):
        store.run(provider, T20)
    assert provider.calls == []
    assert store.snapshot() == {} and store.watermarks.get_all() == []


def test_a_normal_run_asks_from_the_last_success_minus_the_buffer(store: Store) -> None:
    store.run(ListProvider(_posts_20()[:10]), T20, window=WINDOW_20)
    provider = ListProvider(_posts_20()[10:])
    result = store.run(provider, T20 + timedelta(hours=1))
    assert provider.calls == [T20 - BUFFER] and result.since == T20 - BUFFER
    assert len(store.snapshot()) == 20
    assert {r.last_success_at for r in store.watermarks.get_all()} == {T20 + timedelta(hours=1)}


# --- a second run over the same data -----------------------------------------------------------


def test_a_second_run_over_the_same_data_stores_nothing_twice(store: Store) -> None:
    store.run(_spike_main(), T0, window=WINDOW)
    first = store.snapshot()
    first_marks = {r.group_id: r for r in store.watermarks.get_all()}
    downloads = len(store.cdn.calls)

    later = T0 + timedelta(minutes=40)
    # A bootstrap again, so that every post is fetched again, with a later fetched_at.
    store.run(FixtureProvider(SPIKE_MAIN, lambda: later), later, window=WINDOW)

    assert store.snapshot() == first  # posts, first fetched_at, records
    assert len(store.cdn.calls) == downloads  # every photo already held
    assert store.files() == store.referenced()
    for record in store.watermarks.get_all():
        assert record.last_success_at == later
        assert record.watermark == first_marks[record.group_id].watermark


def test_a_normal_run_fifteen_minutes_after_stores_nothing_twice(store: Store) -> None:
    store.run(_spike_main(), T0, window=WINDOW)
    first = store.snapshot()
    later = T0 + timedelta(minutes=40)
    result = store.run(FixtureProvider(SPIKE_MAIN, lambda: later), later)
    assert result.since == T0 - BUFFER
    assert store.snapshot() == first
    assert {r.last_success_at for r in store.watermarks.get_all()} == {later}


# --- failures: nothing moves the watermark -----------------------------------------------------


def _seeded(store: Store) -> tuple[dict, list[GroupWatermark], set[str]]:
    store.run(ListProvider(_posts_20()[:10]), T20, window=WINDOW_20)
    return store.snapshot(), store.watermarks.get_all(), store.files()


def _fail(monkeypatch: pytest.MonkeyPatch, target: str, error: BaseException) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(pipeline, target, broken)


@pytest.mark.parametrize(
    ("step", "target"),
    [("annotate", "annotate"), ("dedup", "dedup_a"), ("images", "download_images")],
)
def test_a_failure_before_the_store_step_writes_nothing(
    store: Store, monkeypatch, caplog, step: str, target: str
) -> None:
    before, marks, files = _seeded(store)
    _fail(monkeypatch, target, ValueError("boom"))
    with caplog.at_level(logging.ERROR), pytest.raises(ValueError, match="boom"):
        store.run(ListProvider(_posts_20()), T20 + timedelta(hours=1))
    assert store.snapshot() == before
    assert store.watermarks.get_all() == marks
    assert store.files() == files
    assert f"run failed at step {step} (ValueError)" in caplog.text


@pytest.mark.parametrize("error", [RuntimeError("provider down"), KeyboardInterrupt()])
def test_a_failed_or_killed_fetch_writes_nothing(store: Store, caplog, error) -> None:
    before, marks, _ = _seeded(store)

    def raise_error() -> None:
        raise error

    provider = ListProvider(_posts_20(), on_fetch=raise_error)
    with caplog.at_level(logging.ERROR), pytest.raises(type(error)):
        store.run(provider, T20 + timedelta(hours=1))
    assert store.snapshot() == before
    assert store.watermarks.get_all() == marks
    assert f"run failed at step fetch ({type(error).__name__})" in caplog.text


def test_a_disk_error_in_the_download_fails_the_run_and_leaves_the_files_written(
    store: Store, monkeypatch
) -> None:
    before, marks, files = _seeded(store)
    real_write = download._write
    written: list[Path] = []

    def write(path: Path, body: bytes) -> None:
        if len(written) == 2:
            raise ImageWriteError(f"cannot write {path}: disk full")
        real_write(path, body)
        written.append(path)

    monkeypatch.setattr(download, "_write", write)
    with pytest.raises(ImageWriteError):
        store.run(ListProvider(_posts_20()), T20 + timedelta(hours=1))
    assert store.snapshot() == before
    assert store.watermarks.get_all() == marks
    orphans = store.files() - files
    assert len(orphans) == 2  # #77: no PostImage points at them; the phase 5 sweep
    assert not orphans & store.referenced()


@pytest.mark.parametrize("step", ["store", "advance", "save watermarks"])
def test_a_failure_after_fetch_never_moves_the_watermark(
    store: Store, monkeypatch, caplog, step: str
) -> None:
    _, marks, _ = _seeded(store)
    repository, watermarks = None, None
    if step == "store":
        repository = CrashingRepository(store.repository, crash_at=3)
    elif step == "advance":
        _fail(monkeypatch, "advance", ValueError("boom"))
    else:
        watermarks = FailingWatermarks(store.root / SQLITE_FILENAME)
    with caplog.at_level(logging.ERROR), pytest.raises((Crash, ValueError, OSError)):
        store.run(
            ListProvider(_posts_20()),
            T20 + timedelta(hours=1),
            repository=repository,
            watermarks=watermarks,
        )
    assert store.watermarks.get_all() == marks
    assert f"run failed at step {step} (" in caplog.text


def test_a_run_overtaken_by_a_later_one_does_not_move_the_watermark_back(store: Store) -> None:
    store.run(ListProvider(_posts_20()[:10]), T20, window=WINDOW_20)
    later = T20 + timedelta(hours=2)

    def another_run_saves() -> None:
        store.watermarks.save_all(
            [r.model_copy(update={"last_success_at": later}) for r in store.watermarks.get_all()]
        )

    provider = ListProvider(_posts_20(), on_fetch=another_run_saves)
    with pytest.raises(ValueError, match="before its last success"):
        store.run(provider, T20 + timedelta(hours=1))
    assert {r.last_success_at for r in store.watermarks.get_all()} == {later}


# --- the store step: order, and a crash between two writes ------------------------------------


def test_the_store_step_writes_canonicals_before_duplicates(store: Store) -> None:
    repository = CrashingRepository(store.repository)
    result = store.run(ListProvider(_pairs_batch()), T20, window=WINDOW_20, repository=repository)

    duplicates = {post.listing_id for post in result.posts if not post.is_canonical}
    assert len(duplicates) == 3
    order = [listing_id for method, listing_id in repository.writes if method != "save_lifecycle"]
    first_duplicate = min(order.index(listing_id) for listing_id in duplicates)
    assert all(listing_id in duplicates for listing_id in order[first_duplicate:])
    # Every post: create-only, then the replace.
    assert repository.writes[0::2] == [("upsert_with_lifecycle", i) for i in order]
    assert repository.writes[1::2] == [("save_lifecycle", i) for i in order]


def test_a_crash_at_any_write_of_the_store_step_converges(kind: str, tmp_path: Path) -> None:
    batch = _pairs_batch()
    reference = Store(kind, tmp_path / "reference")
    reference.run(ListProvider(batch), T20, window=WINDOW_20)
    writes = 2 * len(batch)

    for crash_at in range(writes):
        store = Store(kind, tmp_path / f"crash_{crash_at}")
        crashing = CrashingRepository(store.repository, crash_at=crash_at)
        with pytest.raises(Crash):
            store.run(ListProvider(batch), T20, window=WINDOW_20, repository=crashing)
        assert store.watermarks.get_all() == []

        store.run(ListProvider(batch), T20, window=WINDOW_20)
        assert store.snapshot() == reference.snapshot(), f"crash before write {crash_at}"
        assert store.watermarks.get_all() == reference.watermarks.get_all()
        assert store.files() == store.referenced() == reference.referenced()


def _archived_pair(store: Store) -> tuple[RawPost, RawPost]:
    """A stored, archived canonical C, and R, its later duplicate, never stored."""
    posts = {post.source_post_id: post for post in _posts_20()}
    for pair in sorted(KNOWN_DUPLICATE_PAIRS, key=sorted):
        canonical, repost = sorted((posts[i] for i in pair), key=lambda p: p.posted_at)
        if repost.posted_at > canonical.posted_at and canonical.media:
            break
    else:
        raise AssertionError("no known pair with a later repost and a canonical with media")
    store.run(ListProvider([canonical]), T20, window=WINDOW_20)
    record = store.repository.get_lifecycle(canonical.listing_id)
    assert record is not None and record.state == "pending"
    store.repository.save_lifecycle(record.model_copy(update={"state": "archived"}))
    return canonical, repost


def test_a_crash_after_an_archived_canonical_is_saved_converges(kind: str, tmp_path: Path) -> None:
    later = T20 + timedelta(hours=1)
    reference = Store(kind, tmp_path / "reference")
    canonical, repost = _archived_pair(reference)
    repository = CrashingRepository(reference.repository)
    reference.run(ListProvider([repost]), later, repository=repository)
    # The repost brought the canonical back (#74), and the canonical was saved first.
    assert reference.snapshot()[canonical.listing_id][1].state == "pending"
    assert repository.writes == [
        ("save_lifecycle", canonical.listing_id),
        ("upsert_with_lifecycle", repost.listing_id),
        ("save_lifecycle", repost.listing_id),
    ]

    for crash_at in range(len(repository.writes)):
        store = Store(kind, tmp_path / f"crash_{crash_at}")
        _archived_pair(store)
        marks = store.watermarks.get_all()
        crashing = CrashingRepository(store.repository, crash_at=crash_at)
        with pytest.raises(Crash):
            store.run(ListProvider([repost]), later, repository=crashing)
        assert store.watermarks.get_all() == marks

        store.run(ListProvider([repost]), later)
        assert store.snapshot() == reference.snapshot(), f"crash before write {crash_at}"
        assert store.watermarks.get_all() == reference.watermarks.get_all()


# --- the network drops during the download (DECISIONS.md #80) ---------------------------------


def test_photos_lost_to_a_network_drop_are_recovered_by_the_next_run(store: Store) -> None:
    """Run A's case: the network drops partway through the download and stays down. The run
    waits the whole schedule once, tries the rest once each, and succeeds; the next run, with
    nothing new in its batch, downloads them from the stored links."""
    store.cdn.down_after = 10
    store.run(ListProvider(_posts_20()), T20, window=WINDOW_20)
    assert store.slept == [60, 180, 300, 600]  # once: then each photo is tried once (U3)
    failed = [
        image
        for _, record in store.snapshot().values()
        if record is not None
        for image in record.images
        if image.error is not None
    ]
    assert failed and all(image.error == "network: gaierror" for image in failed)
    assert store.files() == store.referenced()

    store.cdn.down, store.cdn.down_after = False, None
    store.slept.clear()
    store.run(ListProvider([]), T20 + timedelta(hours=1))
    assert store.slept == []
    for _, record in store.snapshot().values():
        assert record is not None
        left = [image for image in record.images if image.error is not None]
        # U7: a repost's failure stays only where the canonical now holds an image.
        assert all(image.listing_id != record.listing_id for image in left)
        if left:
            assert any(image.local_path for image in record.images)
    assert store.files() == store.referenced()


# --- find_without_lifecycle --------------------------------------------------------------------


def test_a_stored_post_with_no_record_is_repaired_and_logged(store: Store, caplog) -> None:
    post = annotate(_posts_20()[0]).with_changes(is_canonical=True, duplicate_of=None)
    store.repository.upsert(post)
    assert store.repository.find_without_lifecycle() == [post]

    with caplog.at_level(logging.ERROR):
        result = store.run(ListProvider([]), T20, window=WINDOW_20)

    assert result.repaired == (post.listing_id,)
    assert store.repository.get_lifecycle(post.listing_id) == initial_lifecycle(post)
    assert store.repository.find_without_lifecycle() == []
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert errors == [f"repaired 1 stored posts with no lifecycle record: {post.listing_id}"]


def test_a_run_logs_no_post_text(store: Store, caplog) -> None:
    with caplog.at_level(logging.DEBUG):
        store.run(ListProvider(_posts_20()), T20, window=WINDOW_20)
    texts = [post.text for post in _posts_20() if post.text.strip()]
    assert texts and not any(text in caplog.text for text in texts)


# --- the Phase 1 DoD, without a network --------------------------------------------------------


def test_bootstrap_a_run_later_a_killed_run_and_the_recovery(kind: str, tmp_path: Path) -> None:
    """A: bootstrap. B: a normal run after A ends. C: killed in the store step. D: the recovery.
    The reference store runs A, B and D only; D must leave the same store as if C never ran."""
    load_spike_1_1a()
    at_b, at_c = T0 + timedelta(minutes=40), T0 + timedelta(hours=2)
    control = [to_raw_post(item, at_c) for item in load_spike_1_1a("_control")]

    def a_and_b(store: Store) -> None:
        store.run(FixtureProvider(SPIKE_MAIN, lambda: T0), T0, window=WINDOW)
        store.run(FixtureProvider(SPIKE_MAIN, lambda: at_b), at_b)

    reference = Store(kind, tmp_path / "reference")
    a_and_b(reference)
    reference.run(ListProvider(control), at_c)

    store = Store(kind, tmp_path / "store")
    a_and_b(store)
    after_b = store.watermarks.get_all()
    crashing = CrashingRepository(store.repository, crash_at=41)
    with pytest.raises(Crash):
        store.run(ListProvider(control), at_c, repository=crashing)
    assert store.watermarks.get_all() == after_b  # C moved nothing

    result = store.run(ListProvider(control), at_c)  # D asks from B's start, minus the buffer
    assert result.since == at_b - BUFFER
    assert store.snapshot() == reference.snapshot()
    assert store.watermarks.get_all() == reference.watermarks.get_all()
    assert store.repository.find_without_lifecycle() == []
    assert store.files() == store.referenced()
