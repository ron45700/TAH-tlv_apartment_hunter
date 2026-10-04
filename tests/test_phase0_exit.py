"""The Phase 0 exit test, ported to `run_once` (DECISIONS.md #79 O1): 20 posts in, 20 identical
posts out, the second run leaves the store unchanged, the first `fetched_at` is kept. No model."""

import socket
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.conftest import (
    CONFIG_ROOT,
    FETCHED_AT,
    KNOWN_DUPLICATE_PAIRS,
    SQLITE_FILENAME,
    THEDOOR_20,
    NetworkBlockedError,
    load_thedoor_items,
)
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.images.download import ImageResponse
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.pipeline import run_once
from tlv_hunter.providers.fixture import FixtureProvider
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.base import Repository

SINCE = datetime(2026, 9, 1, tzinfo=UTC)
JPEG = ImageResponse(200, "image/jpeg", b"\xff\xd8\xff\xe0" + b"jpeg body")

# Runs against every Repository through the make_repository fixture (PHASE_1.md 1.10 DoD).
MakeRepository = Callable[[], Repository]


class SpyRepository:
    def __init__(self, inner: Repository) -> None:
        self._inner = inner
        self.upserted: list[RawPost] = []

    def upsert(self, post: RawPost) -> RawPost:
        raise AssertionError("run_once stores through upsert_with_lifecycle only (#64)")

    def get(self, listing_id: str) -> RawPost | None:
        return self._inner.get(listing_id)

    def upsert_with_lifecycle(self, post: RawPost, initial: PostLifecycle) -> RawPost:
        self.upserted.append(post)
        return self._inner.upsert_with_lifecycle(post, initial)

    def save_lifecycle(self, record: PostLifecycle) -> PostLifecycle:
        return self._inner.save_lifecycle(record)

    def get_lifecycle(self, listing_id: str) -> PostLifecycle | None:
        return self._inner.get_lifecycle(listing_id)

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


def _run(make_repository: MakeRepository, tmp_path: Path) -> SpyRepository:
    repository = SpyRepository(make_repository())
    # A bootstrap run, also the second time, so that both runs fetch all 20 posts (#79 O4).
    run_once(
        provider=FixtureProvider(THEDOOR_20, lambda: FETCHED_AT),
        repository=repository,
        watermarks=SqliteWatermarkStore(tmp_path / SQLITE_FILENAME),
        group_ids=YamlConfig(CONFIG_ROOT).collection().group_ids,
        max_posts=50,
        store_root=tmp_path / "store",
        clock=lambda: FETCHED_AT,
        bootstrap_window=FETCHED_AT - SINCE,
        image_transport=lambda url: JPEG,
    )
    return repository


def _snapshot(repository: Repository) -> dict[str, tuple[RawPost, PostLifecycle | None]]:
    return {
        post.listing_id: (post, repository.get_lifecycle(post.listing_id))
        for post in repository.query()
    }


def test_raw_file_passes_the_pipeline_offline_and_round_trips(
    make_repository: MakeRepository, tmp_path: Path
) -> None:
    with pytest.raises(NetworkBlockedError):
        socket.create_connection(("example.com", 443))

    items = load_thedoor_items()
    expected_ids = {compute_listing_id(item["post_id"]) for item in items}
    items_by_id = {compute_listing_id(item["post_id"]): item for item in items}

    repository = _run(make_repository, tmp_path)

    assert len(repository.upserted) == 20
    fresh = {post.listing_id: post for post in make_repository().query()}
    assert set(fresh) == expected_ids
    for handed_in in repository.upserted:
        assert fresh[handed_in.listing_id] == handed_in
        assert fresh[handed_in.listing_id].raw == items_by_id[handed_in.listing_id]

    stored = list(fresh.values())
    assert all(post.no_text is False and post.phones is not None for post in stored)
    assert len({post.text_hash for post in stored}) == 17
    assert all(make_repository().get_lifecycle(post.listing_id) for post in stored)

    duplicates = [post for post in stored if not post.is_canonical]
    pairs = {
        frozenset({fresh[post.duplicate_of].source_post_id, post.source_post_id})
        for post in duplicates
    }
    assert pairs == KNOWN_DUPLICATE_PAIRS


def test_second_run_on_the_same_store_changes_nothing(
    make_repository: MakeRepository, tmp_path: Path
) -> None:
    _run(make_repository, tmp_path)
    first = _snapshot(make_repository())

    _run(make_repository, tmp_path)
    second = _snapshot(make_repository())

    assert second == first
    assert len(second) == 20
