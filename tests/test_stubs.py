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


def deletes(cls: type) -> set[str]:
    return {name for name in dir(cls) if "delete" in name or "remove" in name}


def test_the_repository_has_one_delete_and_only_retention_calls_it() -> None:
    """Invariant 3: a stored post is removed only by the retention job (DECISIONS.md #471)."""
    for cls in (Repository, LocalJsonRepository, SqliteRepository):
        assert deletes(cls) == {"delete_post"}
    package = Path(__file__).resolve().parent.parent / "tlv_hunter"
    callers = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*.py")
        if ".delete_post(" in path.read_text(encoding="utf-8")
    }
    assert callers == {"jobs/retention.py"}


def test_sqlite_implementations_satisfy_their_protocols(tmp_path: Path) -> None:
    path = tmp_path / SQLITE_FILENAME
    assert isinstance(SqliteRepository(path), Repository)
    assert isinstance(SqliteWatermarkStore(path), WatermarkStore)


def test_the_watermark_store_has_no_delete() -> None:
    for cls in (WatermarkStore, SqliteWatermarkStore):
        assert deletes(cls) == set()


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
