"""`jobs/reset_admin_password.py` (DECISIONS.md #294), against a temporary store only: never the
production store. `getpass.getpass` is patched; nothing is typed on a command line."""

import io
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from argon2 import PasswordHasher, profiles

from tests.conftest import SQLITE_FILENAME
from tlv_hunter.accounts import actions
from tlv_hunter.accounts.passwords import check_password
from tlv_hunter.accounts.tokens import secret_hash
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs import reset_admin_password
from tlv_hunter.jobs.common import CONFIG_ROOT, raw_post_rows
from tlv_hunter.sqlite_busy import BUSY_TIMEOUT_SECONDS
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

CREATED = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
CLOCK = CREATED + timedelta(days=3)
STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
OLD_PASSWORD = "forgotten-password-1"
NEW_PASSWORD = "new-admin-password-1"
CHEAPEST = PasswordHasher.from_parameters(profiles.CHEAPEST)


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / STORE_ROOT / SQLITE_FILENAME
    path.parent.mkdir(parents=True)
    SqliteRepository(path)  # a store as the job commands leave it, with no userdata tables
    return path


@pytest.fixture
def admin_tokens(database: Path) -> list[str]:
    """The admin with two open sessions, then locked by the delay after 5 failures (#264)."""
    store = SqliteUserDataStore(database)
    actions.create_admin(store, "ron", OLD_PASSWORD, CREATED, hasher=CHEAPEST)
    tokens = [
        actions.sign_in(store, "ron", OLD_PASSWORD, CREATED, hasher=CHEAPEST).token for _ in "ab"
    ]
    for _ in range(actions.FAILURES_BEFORE_DELAY):
        with pytest.raises(actions.Refused):
            actions.sign_in(store, "ron", "a wrong guess", CLOCK, hasher=CHEAPEST)
    return tokens


def _answers(monkeypatch: pytest.MonkeyPatch, passwords: list[str]) -> list[str]:
    """Patches `getpass`; returns the prompts it was called with."""
    asked: list[str] = []
    typed: Iterator[str] = iter(passwords)

    def fake_getpass(prompt: str = "Password: ", stream: object = None) -> str:
        asked.append(prompt)
        return next(typed)

    monkeypatch.setattr("getpass.getpass", fake_getpass)
    return asked


def _run(tmp_path: Path) -> tuple[int, str]:
    stream = io.StringIO()
    code = reset_admin_password.main(
        [],
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        clock=lambda: CLOCK,
        stream=stream,
        hasher=CHEAPEST,
    )
    return code, stream.getvalue()


def _backups(database: Path) -> list[Path]:
    return sorted(database.parent.glob("*.backup*"))


def _has_userdata_tables(database: Path) -> bool:
    with closing(sqlite3.connect(database)) as conn:
        found = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
    return found is not None


def test_it_sets_a_final_password_and_ends_every_session_after_a_backup(
    tmp_path: Path, database: Path, admin_tokens: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    store = SqliteUserDataStore(database)
    (admin,) = store.list_users()
    assert admin.failed_sign_ins == actions.FAILURES_BEFORE_DELAY
    rows = raw_post_rows(database)
    asked = _answers(monkeypatch, [NEW_PASSWORD, NEW_PASSWORD])

    code, output = _run(tmp_path)

    assert code == reset_admin_password.EXIT_DONE, output
    assert asked == ["New password: ", "New password again: "]
    reset = store.get_user(admin.user_id)
    assert reset is not None
    assert check_password(reset.password_hash, NEW_PASSWORD, CHEAPEST)
    assert not check_password(reset.password_hash, OLD_PASSWORD, CHEAPEST)
    assert (
        reset.must_change_password,
        reset.failed_sign_ins,
        reset.last_failed_sign_in_at,
        reset.password_changed_at,
    ) == (False, 0, None, CLOCK)
    changed = {"password_hash", "password_changed_at", "failed_sign_ins", "last_failed_sign_in_at"}
    assert reset.model_dump(exclude=changed) == admin.model_dump(exclude=changed)
    for token in admin_tokens:
        session = store.find_session(secret_hash(token))
        assert session is not None and session.ended_at == CLOCK
        assert actions.session_user(store, token, CLOCK) is None
    signed_in = actions.sign_in(store, "ron", NEW_PASSWORD, CLOCK, hasher=CHEAPEST)
    assert signed_in.must_change_password is False
    assert len(_backups(database)) == 1
    assert raw_post_rows(database) == rows
    assert "identical to the backup's: True" in output
    for secret in (NEW_PASSWORD, OLD_PASSWORD, reset.password_hash, "$argon2"):
        assert secret not in output


def test_it_refuses_a_store_with_no_userdata_tables_and_creates_none(
    tmp_path: Path, database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = database.read_bytes()
    asked = _answers(monkeypatch, [NEW_PASSWORD, NEW_PASSWORD])
    code, output = _run(tmp_path)
    assert code == reset_admin_password.EXIT_FAILED
    assert "refused: no_admin" in output
    assert asked == []  # refused before any question
    assert database.read_bytes() == before
    assert not _has_userdata_tables(database)
    assert _backups(database) == []


def test_it_refuses_when_the_userdata_tables_hold_no_admin(
    tmp_path: Path, database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    SqliteUserDataStore(database)
    before = database.read_bytes()
    asked = _answers(monkeypatch, [NEW_PASSWORD, NEW_PASSWORD])
    code, output = _run(tmp_path)
    assert code == reset_admin_password.EXIT_FAILED
    assert "refused: no_admin" in output
    assert asked == []
    assert database.read_bytes() == before
    assert _backups(database) == []


@pytest.mark.parametrize(
    ("passwords", "expected"),
    [
        ([NEW_PASSWORD, "another-password"], "the two passwords differ"),
        (["seven77", "seven77"], "password_too_short"),
    ],
)
def test_a_refusal_before_the_backup_writes_nothing(
    tmp_path: Path,
    database: Path,
    admin_tokens: list[str],
    monkeypatch: pytest.MonkeyPatch,
    passwords: list[str],
    expected: str,
) -> None:
    before = database.read_bytes()
    _answers(monkeypatch, passwords)
    code, output = _run(tmp_path)
    assert code == reset_admin_password.EXIT_FAILED
    assert expected in output
    assert database.read_bytes() == before
    assert _backups(database) == []
    for password in passwords:
        assert password not in output


def test_a_missing_store_is_refused_and_not_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _answers(monkeypatch, [NEW_PASSWORD, NEW_PASSWORD])
    code, output = _run(tmp_path)
    assert code == reset_admin_password.EXIT_FAILED
    assert "no store at" in output
    assert not (tmp_path / STORE_ROOT / SQLITE_FILENAME).exists()


def test_its_read_only_check_passes_the_busy_timeout(
    database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = sqlite3.connect
    timeouts: list[Any] = []

    def recording(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        timeouts.append(kwargs.get("timeout"))
        return real(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", recording)
    assert reset_admin_password._has_userdata_tables(database) is False
    assert timeouts == [BUSY_TIMEOUT_SECONDS]
