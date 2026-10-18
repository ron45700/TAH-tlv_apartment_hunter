from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.conftest import CONFIG_ROOT, FETCHED_AT, SQLITE_FILENAME, THEDOOR_20
from tlv_hunter.config.base import ConfigSource
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.notify.base import Notifier
from tlv_hunter.notify.telegram import TelegramNotifier
from tlv_hunter.providers.base import Provider
from tlv_hunter.providers.fixture import FixtureProvider
from tlv_hunter.state.base import WatermarkStore
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.base import Repository
from tlv_hunter.store.local_json import LocalJsonRepository
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.telegram.client import TelegramClient


def test_the_phase_0_stubs_are_gone() -> None:
    # ListingStub and DecisionStub stayed for notify/ until Phase 4 (DECISIONS.md #295); Phase 4
    # built notify/ (#452), so no stub contract is left.
    package = Path(__file__).resolve().parent.parent / "tlv_hunter"
    assert not list(package.rglob("*_stub.py"))


def test_implementations_satisfy_their_protocols(tmp_path: Path) -> None:
    assert isinstance(FixtureProvider(THEDOOR_20, lambda: FETCHED_AT), Provider)
    assert isinstance(LocalJsonRepository(tmp_path), Repository)
    assert isinstance(YamlConfig(CONFIG_ROOT), ConfigSource)
    client = TelegramClient("1:" + "a" * 35, transport=lambda *args: (200, b"{}"))
    assert isinstance(TelegramNotifier(client), Notifier)


def test_repository_has_no_delete() -> None:
    assert not any("delete" in name or "remove" in name for name in dir(Repository))
    assert not any("delete" in name or "remove" in name for name in dir(LocalJsonRepository))


def test_sqlite_implementations_satisfy_their_protocols(tmp_path: Path) -> None:
    path = tmp_path / SQLITE_FILENAME
    assert isinstance(SqliteRepository(path), Repository)
    assert isinstance(SqliteWatermarkStore(path), WatermarkStore)


def test_sqlite_store_and_watermark_store_have_no_delete() -> None:
    for cls in (SqliteRepository, WatermarkStore, SqliteWatermarkStore):
        assert not any("delete" in name or "remove" in name for name in dir(cls))


@pytest.mark.raw_fixtures
def test_fixture_provider_filters_by_group_and_since() -> None:
    provider = FixtureProvider(THEDOOR_20, lambda: FETCHED_AT)
    early = datetime(2026, 9, 1, tzinfo=UTC)
    assert len(provider.fetch(["35819517694", "333022240594651"], early)) == 20
    assert {p.group_id for p in provider.fetch(["35819517694"], early)} == {"35819517694"}
    assert len(provider.fetch(["35819517694"], early)) == 10
    assert (
        provider.fetch(["35819517694", "333022240594651"], datetime(2027, 1, 1, tzinfo=UTC)) == []
    )
