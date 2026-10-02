import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ROOT = REPO_ROOT / "config"
THEDOOR_20 = REPO_ROOT / "data" / "raw" / "thedoor_20posts_2026-09-13.json"

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


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket.socket, "connect", _refuse_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse_network)
    monkeypatch.setattr(socket, "create_connection", _refuse_network)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse_network)


def load_thedoor_items() -> list[dict[str, Any]]:
    if not THEDOOR_20.is_file():
        pytest.fail(f"fixture missing: {THEDOOR_20}. data/ is gitignored; tests fail, never skip.")
    return json.loads(THEDOOR_20.read_text(encoding="utf-8"))


@pytest.fixture
def thedoor_items() -> list[dict[str, Any]]:
    return load_thedoor_items()
