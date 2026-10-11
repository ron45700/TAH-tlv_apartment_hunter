"""`jobs/create_admin.py` (DECISIONS.md #244, #290), against a temporary store only: never the
production store. `input` and `getpass.getpass` are patched; nothing is typed on a command line."""

import io
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest
from argon2 import PasswordHasher, profiles

from tests.conftest import SQLITE_FILENAME
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.jobs import create_admin
from tlv_hunter.jobs.common import CONFIG_ROOT, raw_post_rows
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

CLOCK = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
PASSWORD = "admin-password-1"
CHEAPEST = PasswordHasher.from_parameters(profiles.CHEAPEST)


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / STORE_ROOT / SQLITE_FILENAME
    path.parent.mkdir(parents=True)
    SqliteRepository(path)  # a store as the job commands leave it, with no userdata tables
    return path


def _answers(monkeypatch: pytest.MonkeyPatch, username: str, passwords: list[str]) -> list[str]:
    """Patches the prompts; returns the prompts `getpass` was called with."""
    asked: list[str] = []
    typed: Iterator[str] = iter(passwords)

    def fake_getpass(prompt: str = "Password: ", stream: object = None) -> str:
        asked.append(prompt)
        return next(typed)

    monkeypatch.setattr("builtins.input", lambda prompt="": username)
    monkeypatch.setattr("getpass.getpass", fake_getpass)
    return asked


def _run(tmp_path: Path) -> tuple[int, str]:
    stream = io.StringIO()
    code = create_admin.main(
        [],
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        clock=lambda: CLOCK,
        stream=stream,
        hasher=CHEAPEST,
    )
    return code, stream.getvalue()


def _has_userdata_tables(database: Path) -> bool:
    with closing(sqlite3.connect(database)) as conn:
        found = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
    return found is not None


def _backups(database: Path) -> list[Path]:
    return sorted(database.parent.glob("*.backup*"))


def test_it_creates_the_one_admin_with_no_key_after_a_backup(
    tmp_path: Path, database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = raw_post_rows(database)
    asked = _answers(monkeypatch, "ron", [PASSWORD, PASSWORD])
    code, output = _run(tmp_path)
    assert code == create_admin.EXIT_DONE, output
    assert asked == ["Password: ", "Password again: "]
    (admin,) = SqliteUserDataStore(database).list_users()
    assert (admin.username, admin.is_admin, admin.signup_key_id) == ("ron", True, None)
    assert admin.created_at == CLOCK
    assert SqliteUserDataStore(database).get_profile(admin.user_id) == new_profile(
        admin.user_id, CLOCK
    )
    assert len(_backups(database)) == 1
    assert raw_post_rows(database) == rows
    assert "identical to the backup's: True" in output
    assert PASSWORD not in output and admin.password_hash not in output
    assert "$argon2" not in output


def test_a_second_run_is_refused(
    tmp_path: Path, database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _answers(monkeypatch, "ron", [PASSWORD, PASSWORD])
    assert _run(tmp_path)[0] == create_admin.EXIT_DONE
    _answers(monkeypatch, "other", [PASSWORD, PASSWORD])
    code, output = _run(tmp_path)
    assert code == create_admin.EXIT_FAILED
    assert "there is already an admin" in output
    assert [user.username for user in SqliteUserDataStore(database).list_users()] == ["ron"]
    assert PASSWORD not in output


@pytest.mark.parametrize(
    ("username", "passwords", "expected"),
    [
        ("ron", [PASSWORD, "another-password"], "the two passwords differ"),
        ("ron", ["seven77", "seven77"], "password_too_short"),
        ("r", [PASSWORD, PASSWORD], "username_invalid"),
        ("רון", [PASSWORD, PASSWORD], "username_invalid"),
    ],
)
def test_a_refusal_before_the_backup_writes_nothing(
    tmp_path: Path,
    database: Path,
    monkeypatch: pytest.MonkeyPatch,
    username: str,
    passwords: list[str],
    expected: str,
) -> None:
    before = database.read_bytes()
    _answers(monkeypatch, username, passwords)
    code, output = _run(tmp_path)
    assert code == create_admin.EXIT_FAILED
    assert expected in output
    assert database.read_bytes() == before
    assert not _has_userdata_tables(database)
    assert _backups(database) == []
    for password in passwords:
        assert password not in output


def test_a_missing_store_is_refused_and_not_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _answers(monkeypatch, "ron", [PASSWORD, PASSWORD])
    code, output = _run(tmp_path)
    assert code == create_admin.EXIT_FAILED
    assert "no store at" in output
    assert not (tmp_path / STORE_ROOT / SQLITE_FILENAME).exists()
