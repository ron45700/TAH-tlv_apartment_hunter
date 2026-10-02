import socket
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.conftest import (
    CONFIG_ROOT,
    FETCHED_AT,
    THEDOOR_20,
    NetworkBlockedError,
    load_thedoor_items,
)
from tlv_hunter.classify.classifier_stub import ClassifierStub
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.listing_stub import ListingStub
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.notify.notifier_stub import RecordingNotifierStub
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.pipeline import run_pipeline
from tlv_hunter.policy.policy_stub import AlwaysNotifyPolicyStub
from tlv_hunter.providers.fixture import FixtureProvider
from tlv_hunter.store.local_json import LocalJsonRepository

SINCE = datetime(2026, 9, 1, tzinfo=UTC)


class SpyRepository:
    def __init__(self, inner: LocalJsonRepository) -> None:
        self._inner = inner
        self.upserted: list[RawPost] = []

    def upsert(self, post: RawPost) -> RawPost:
        self.upserted.append(post)
        return self._inner.upsert(post)

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]:
        return self._inner.find_by_hash(text_hash)

    def find_by_phone(self, phone: str) -> list[RawPost]:
        return self._inner.find_by_phone(phone)

    def query(self) -> list[RawPost]:
        return self._inner.query()


class SpyClassifier(ClassifierStub):
    def __init__(self) -> None:
        self.seen: list[str] = []

    def classify(self, post: RawPost) -> ListingStub:
        self.seen.append(post.listing_id)
        return super().classify(post)


def _run(store_root: Path):
    config = YamlConfig(CONFIG_ROOT)
    user = config.user("ron")
    repository = SpyRepository(LocalJsonRepository(store_root))
    classifier = SpyClassifier()
    notifier = RecordingNotifierStub()
    result = run_pipeline(
        provider=FixtureProvider(THEDOOR_20, lambda: FETCHED_AT),
        repository=repository,
        classifier=classifier,
        policy=AlwaysNotifyPolicyStub(user.user_id),
        notifier=notifier,
        group_ids=config.collection().group_ids,
        since=SINCE,
    )
    return result, repository, classifier, notifier


def test_raw_file_passes_the_pipeline_offline_and_round_trips(tmp_path: Path) -> None:
    with pytest.raises(NetworkBlockedError):
        socket.create_connection(("example.com", 443))

    items = load_thedoor_items()
    expected_ids = {compute_listing_id(item["post_id"]) for item in items}
    items_by_id = {compute_listing_id(item["post_id"]): item for item in items}

    result, repository, classifier, notifier = _run(tmp_path)

    assert {post.listing_id for post in result.stored} == expected_ids
    assert len(repository.upserted) == 20
    assert set(classifier.seen) == expected_ids and len(classifier.seen) == 20
    assert {listing.listing_id for listing, _ in notifier.sent} == expected_ids
    assert all(decision.user_id == "ron" and decision.notify for _, decision in notifier.sent)

    fresh = {post.listing_id: post for post in LocalJsonRepository(tmp_path).query()}
    assert set(fresh) == expected_ids
    for handed_in in repository.upserted:
        assert fresh[handed_in.listing_id] == handed_in
        assert fresh[handed_in.listing_id].raw == items_by_id[handed_in.listing_id]

    stored = list(fresh.values())
    assert all(post.no_text is False and post.phones is not None for post in stored)
    assert all(post.is_canonical is None and post.duplicate_of is None for post in stored)
    assert len({post.text_hash for post in stored}) == 17


def test_second_run_on_the_same_store_changes_nothing(tmp_path: Path) -> None:
    _run(tmp_path)
    first = {post.listing_id: post for post in LocalJsonRepository(tmp_path).query()}

    _, _, _, notifier = _run(tmp_path)
    second = {post.listing_id: post for post in LocalJsonRepository(tmp_path).query()}

    assert second == first
    assert len(list((tmp_path / "raw_posts").iterdir())) == 20
    assert len(notifier.sent) == 20
