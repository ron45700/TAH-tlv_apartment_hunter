import json
import socket
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.jobs.run_once import SQLITE_FILENAME
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.store.base import Repository
from tlv_hunter.store.local_json import LocalJsonRepository
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.textnorm.annotate import annotate

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ROOT = REPO_ROOT / "config"
THEDOOR_20 = REPO_ROOT / "data" / "raw" / "thedoor_20posts_2026-09-13.json"
SPIKE_1_1A_PREFIX = REPO_ROOT / "data" / "raw" / "thedoor_spike_1_1a_2026-10-04"

FETCHED_AT = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)

KNOWN_DUPLICATE_PAIRS = {
    frozenset({"10163683432542695", "10163683412257695"}),
    frozenset({"2178554076041449", "2178430789387111"}),
    frozenset({"2178092279420962", "2177447349485455"}),
}


class NetworkBlockedError(RuntimeError):
    pass


def _refuse_network(*args: Any, **kwargs: Any) -> None:
    raise NetworkBlockedError("tests must not open network connections")


class RealSleepError(RuntimeError):
    pass


def _refuse_sleep(seconds: float) -> None:
    raise RealSleepError(f"tests must not really sleep ({seconds} s); inject a sleep")


@pytest.fixture(autouse=True)
def _block_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """The network waits of the photo download (DECISIONS.md #80) go through an injected sleep."""
    monkeypatch.setattr(time, "sleep", _refuse_sleep)


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket.socket, "connect", _refuse_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse_network)
    monkeypatch.setattr(socket, "create_connection", _refuse_network)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse_network)


def _load_fixture(path: Path) -> Any:
    if not path.is_file():
        pytest.fail(f"fixture missing: {path}. data/ is gitignored; tests fail, never skip.")
    return json.loads(path.read_text(encoding="utf-8"))


def load_thedoor_items() -> list[dict[str, Any]]:
    return _load_fixture(THEDOOR_20)


def load_spike_1_1a(suffix: str = "") -> Any:
    """Spike 1.1a: run 1's dataset (no suffix), `_run` (run object), `_input` (its INPUT), or
    `_control` (the control run's dataset)."""
    return _load_fixture(SPIKE_1_1A_PREFIX.with_name(SPIKE_1_1A_PREFIX.name + suffix + ".json"))


@pytest.fixture
def thedoor_items() -> list[dict[str, Any]]:
    return load_thedoor_items()


@pytest.fixture
def spike_items() -> list[dict[str, Any]]:
    return load_spike_1_1a()


@pytest.fixture
def posts(thedoor_items: list[dict[str, Any]]) -> list[RawPost]:
    return [annotate(to_raw_post(item, FETCHED_AT)) for item in thedoor_items]


@pytest.fixture(params=["local_json", "sqlite"])
def make_repository(request: pytest.FixtureRequest, tmp_path: Path) -> Callable[[], Repository]:
    """Each call returns a fresh instance over the same storage, for every Repository."""
    if request.param == "local_json":
        return lambda: LocalJsonRepository(tmp_path)
    return lambda: SqliteRepository(tmp_path / SQLITE_FILENAME)
