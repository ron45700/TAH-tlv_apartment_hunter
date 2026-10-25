"""One Yad2 run's wiring (`yad2_run.py`; `PHASE_6.md` §6.5; DECISIONS.md #492, #493, #502 point 18,
#520, #524): the store at the end, in one transaction, only on success (invariant 2); the bumps;
the `yad2-tel-aviv` record. A fake collector and a temporary SQLite store; no browser, no
network."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import make_listing, sqlite_dump
from tests.yad2_synthetic import lid, listing_data, token
from tlv_hunter.contracts.group_watermark import GROUP_WATERMARK_SCHEMA_VERSION, GroupWatermark
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.dedup.stage_a import bumped_lifecycle
from tlv_hunter.images.download import ImageResponse
from tlv_hunter.parsing.datetimes import parse_israel_local_utc
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.base import Repository, StaleRecordError
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.watermark.window import MissingWatermarkError
from tlv_hunter.yad2.collector import Bump, NewListing, Yad2Blocked, Yad2Collection
from tlv_hunter.yad2.mapping import GROUP_ID, form_fields, to_raw_post
from tlv_hunter.yad2_run import run_yad2

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
EARLIER = NOW - timedelta(hours=1)
JPEG = b"\xff\xd8\xff\xe0" + b"jpeg body"
PHOTO = "https://img.yad2.co.il/Pic/202610/24/2_1/o/made_up_1.jpeg"
BUMPED_AT = parse_israel_local_utc("2026-10-24T14:00:00")


class FakeCollector:
    def __init__(self, collection: Yad2Collection | Exception) -> None:
        self.collection = collection
        self.calls: list[tuple[dict[str, datetime], bool]] = []

    def collect(self, known: Mapping[str, datetime], *, bootstrap: bool) -> Yad2Collection:
        self.calls.append((dict(known), bootstrap))
        if isinstance(self.collection, Exception):
            raise self.collection
        return self.collection


def _post(value: str, fetched_at: datetime = NOW, **changes: Any) -> RawPost:
    return to_raw_post(listing_data(value, **changes), fetched_at=fetched_at)


def _collection(
    values: Sequence[str] = (), bumps: Sequence[Bump] = (), **changes: Any
) -> Yad2Collection:
    listings = []
    for value in values:
        d = listing_data(value, **changes)
        listings.append(NewListing(post=to_raw_post(d, fetched_at=NOW), form=form_fields(d)))
    return Yad2Collection(
        listings=tuple(listings), bumps=tuple(bumps), list_pages=3, listings_read=120, skipped=()
    )


@pytest.fixture
def database(tmp_path: Path) -> Path:
    return tmp_path / "store.sqlite"


def _run(
    database: Path,
    collector: FakeCollector,
    *,
    bootstrap: bool = False,
    repository: Repository | None = None,
):
    return run_yad2(
        collector=collector,  # type: ignore[arg-type]
        repository=repository or SqliteRepository(database),
        watermarks=SqliteWatermarkStore(database),
        store_root=database.parent,
        clock=lambda: NOW,
        bootstrap=bootstrap,
        image_transport=lambda url: ImageResponse(200, "image/jpeg", JPEG),
        image_sleep=lambda seconds: None,
    )


def _watermark(database: Path, **changes: Any) -> GroupWatermark:
    fields = {
        "schema_version": GROUP_WATERMARK_SCHEMA_VERSION,
        "group_id": GROUP_ID,
        "watermark": EARLIER - timedelta(hours=5),
        "last_success_at": EARLIER,
        "consecutive_failures": 0,
    }
    record = GroupWatermark(**{**fields, **changes})
    SqliteWatermarkStore(database).save_all([record])
    return record


def _stored(database: Path, value: str, **changes: Any) -> tuple[RawPost, PostLifecycle]:
    """A Yad2 listing already in the store, first read 30 days ago, published at 10:00."""
    post = annotate(
        _post(
            value, fetched_at=NOW - timedelta(days=30), updated_at="2026-10-24T10:00:00", **changes
        )
    )
    post = post.with_changes(is_canonical=True, duplicate_of=None)
    lifecycle = initial_lifecycle(post)
    SqliteRepository(database).upsert_with_lifecycle(post, lifecycle)
    return post, lifecycle


def test_a_bootstrap_stores_every_listing_and_creates_the_record(database: Path) -> None:
    collection = _collection([token(1), token(2), token(1, "a")])
    result = _run(database, FakeCollector(collection), bootstrap=True)
    repository = SqliteRepository(database)
    for listing in collection.listings:
        stored = repository.get(listing.post.listing_id)
        assert stored is not None
        assert stored.raw == listing.post.raw  # invariant 4: whole
        assert stored.text == listing.post.text  # invariant 14: the original, verbatim
        assert stored.is_canonical
        record = repository.get_lifecycle(listing.post.listing_id)
        assert record is not None and record.state == "pending"
    assert len(result.posts) == 3
    watermark = SqliteWatermarkStore(database).get(GROUP_ID)
    assert watermark == result.watermark
    assert watermark is not None
    assert watermark.watermark == parse_israel_local_utc("2026-10-24T14:30:00")
    assert (watermark.last_success_at, watermark.consecutive_failures) == (NOW, 0)


def test_a_kind_rejected_before_the_model_is_stored_rejected(database: Path) -> None:
    parking = {"property": {"id": 30, "text": "חניה"}}
    collection = _collection([token(1)], additionalDetails=parking)
    _run(database, FakeCollector(collection), bootstrap=True)
    record = SqliteRepository(database).get_lifecycle(lid(token(1)))
    assert record is not None
    assert (record.state, record.rejection_reason) == ("rejected", "not_listing")


def test_a_run_outside_bootstrap_needs_the_record(database: Path) -> None:
    collector = FakeCollector(_collection([token(1)]))
    with pytest.raises(MissingWatermarkError):
        _run(database, collector)
    assert collector.calls == []
    assert SqliteRepository(database).query() == []


def test_known_is_every_stored_yad2_listing_by_its_clock(database: Path) -> None:
    _watermark(database)
    post, record = _stored(database, token(7))
    bumped_at = NOW - timedelta(hours=4)
    SqliteRepository(database).save_lifecycle(
        record.model_copy(update={"last_published_at": bumped_at}), expected=record
    )
    collector = FakeCollector(_collection())
    _run(database, collector)
    assert collector.calls == [({post.listing_id: bumped_at}, False)]


def test_a_blocked_run_stores_nothing_and_moves_no_record(database: Path) -> None:
    """Invariant 2 (#492): a failed run marks no token as seen."""
    _watermark(database)
    _stored(database, token(7))
    before = sqlite_dump(database)
    blocked = Yad2Blocked("blocked: the page moved to validate.perfdrive.com")
    with pytest.raises(Yad2Blocked):
        _run(database, FakeCollector(blocked))
    assert sqlite_dump(database) == before


class AnotherWriterAtTheBatch:
    """Before each of its first `times` batch writes, the site changes a stored record's
    `flag_note` (a field it owns), so the batch meets a stale record."""

    def __init__(self, inner: SqliteRepository, listing_id: str, times: int) -> None:
        self._inner = inner
        self._listing_id = listing_id
        self.times = times

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def save_batch(self, posts, records) -> None:
        if self.times > 0:
            self.times -= 1
            current = self._inner.get_lifecycle(self._listing_id)
            assert current is not None
            changed = current.model_copy(update={"flag_note": f"the site {self.times}"})
            self._inner.save_lifecycle(changed, expected=current)
        self._inner.save_batch(posts, records)


def test_a_record_changed_during_the_run_is_merged_and_the_batch_written(database: Path) -> None:
    _watermark(database)
    post, _ = _stored(database, token(7))
    collection = _collection([token(1)], [Bump(listing_id=post.listing_id, updated_at=BUMPED_AT)])
    repository = AnotherWriterAtTheBatch(SqliteRepository(database), post.listing_id, times=1)
    _run(database, FakeCollector(collection), repository=repository)  # type: ignore[arg-type]
    record = SqliteRepository(database).get_lifecycle(post.listing_id)
    assert record is not None
    assert (record.last_published_at, record.flag_note) == (BUMPED_AT, "the site 0")
    assert SqliteRepository(database).get(lid(token(1))) is not None


def test_a_batch_that_keeps_meeting_another_writer_stores_nothing_of_the_run(
    database: Path,
) -> None:
    _watermark(database)
    post, _ = _stored(database, token(7))
    collection = _collection([token(1)], [Bump(listing_id=post.listing_id, updated_at=BUMPED_AT)])
    repository = AnotherWriterAtTheBatch(SqliteRepository(database), post.listing_id, times=3)
    watermark = SqliteWatermarkStore(database).get(GROUP_ID)
    with pytest.raises(StaleRecordError):
        _run(database, FakeCollector(collection), repository=repository)  # type: ignore[arg-type]
    store = SqliteRepository(database)
    assert store.get(lid(token(1))) is None  # the new listing is not seen
    record = store.get_lifecycle(post.listing_id)
    assert record is not None and record.last_published_at != BUMPED_AT
    assert SqliteWatermarkStore(database).get(GROUP_ID) == watermark


def test_a_bump_moves_last_published_at_only(database: Path) -> None:
    """#520: no repost line, no new post; the RawPost untouched; the state kept."""
    _watermark(database)
    post, record = _stored(database, token(7))
    collection = _collection([], [Bump(listing_id=post.listing_id, updated_at=BUMPED_AT)])
    result = _run(database, FakeCollector(collection))
    repository = SqliteRepository(database)
    assert repository.get(post.listing_id) == post
    assert repository.get_lifecycle(post.listing_id) == record.model_copy(
        update={"last_published_at": BUMPED_AT}
    )
    assert len(repository.query()) == 1
    assert result.bumped == (post.listing_id,)
    watermark = SqliteWatermarkStore(database).get(GROUP_ID)
    assert watermark is not None and watermark.watermark == BUMPED_AT


def test_a_bump_of_a_duplicate_moves_its_canonicals_clock_too(database: Path) -> None:
    _watermark(database)
    canonical, _ = _stored(database, token(7))
    duplicate = annotate(_post(token(8), fetched_at=NOW - timedelta(days=30)))
    duplicate = duplicate.with_changes(is_canonical=False, duplicate_of=canonical.listing_id)
    SqliteRepository(database).upsert_with_lifecycle(duplicate, initial_lifecycle(duplicate))
    _run(database, FakeCollector(_collection([], [Bump(duplicate.listing_id, NOW)])))
    repository = SqliteRepository(database)
    for listing_id in (duplicate.listing_id, canonical.listing_id):
        record = repository.get_lifecycle(listing_id)
        assert record is not None and record.last_published_at == NOW


@pytest.mark.parametrize(("classified", "state"), [(True, "active"), (False, "pending")])
def test_a_bump_returns_an_archived_listing_with_its_photos(
    database: Path, classified: bool, state: str
) -> None:
    """#524: as #74, and its photos downloaded again from the stored post (archive cleared them)."""
    _watermark(database)
    post, _ = _stored(database, token(7), metaData={"description": "דירה", "images": [PHOTO]})
    repository = SqliteRepository(database)
    if classified:
        pending = repository.get_lifecycle(post.listing_id)
        assert pending is not None
        active = pending.model_copy(update={"state": "active"})
        repository.save_classification(make_listing(post.listing_id), active, expected=pending)
    current = repository.get_lifecycle(post.listing_id)
    assert current is not None
    archived = current.model_copy(update={"state": "archived", "images": []})
    repository.save_lifecycle(archived, expected=current)

    _run(database, FakeCollector(_collection([], [Bump(post.listing_id, NOW)])))
    record = SqliteRepository(database).get_lifecycle(post.listing_id)
    assert record is not None
    assert (record.state, record.last_published_at) == (state, NOW)
    assert [image.media_id for image in record.images] == [PHOTO]
    assert record.images[0].local_path is not None
    assert (database.parent / record.images[0].local_path).read_bytes() == JPEG


def test_a_new_listings_photos_are_downloaded(database: Path) -> None:
    collection = _collection([token(1)], metaData={"description": "דירה", "images": [PHOTO]})
    _run(database, FakeCollector(collection), bootstrap=True)
    record = SqliteRepository(database).get_lifecycle(lid(token(1)))
    assert record is not None and [image.media_id for image in record.images] == [PHOTO]


def test_a_run_with_nothing_new_counts_a_silent_run(database: Path) -> None:
    before = _watermark(database, consecutive_failures=2)
    result = _run(database, FakeCollector(_collection()))
    assert result.watermark.consecutive_failures == 3
    assert result.watermark.watermark == before.watermark
    assert result.watermark.last_success_at == NOW


def test_a_yad2_run_leaves_facebooks_records_alone(database: Path) -> None:
    facebook = GroupWatermark(
        schema_version=GROUP_WATERMARK_SCHEMA_VERSION,
        group_id="123456789",
        watermark=EARLIER,
        last_success_at=EARLIER,
        consecutive_failures=0,
    )
    SqliteWatermarkStore(database).save_all([facebook])
    _run(database, FakeCollector(_collection([token(1)])), bootstrap=True)
    assert SqliteWatermarkStore(database).get("123456789") == facebook


def test_the_bump_rule_on_its_own() -> None:
    """`bumped_lifecycle`: not later, no bump; an archived rejection returns rejected (#74)."""
    post = annotate(_post(token(7)))
    record = initial_lifecycle(post)
    assert bumped_lifecycle(record, record.last_published_at, lambda _: True) is None
    rejected = record.model_copy(update={"state": "archived", "rejection_reason": "other_city"})
    later = record.last_published_at + timedelta(minutes=1)
    back = bumped_lifecycle(rejected, later, lambda _: True)
    assert back is not None
    assert (back.state, back.rejection_reason, back.last_published_at) == (
        "rejected",
        "other_city",
        later,
    )
