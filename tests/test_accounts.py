"""Task 3.5, the account logic (`accounts/`; DECISIONS.md #242–#244, #262–#266, #290, #291, #293),
over `SqliteUserDataStore` on a fresh temporary file per test, never the production store.

Every hash is made with `profiles.CHEAPEST`, never the production profile (`PHASE_3.md` 3.5).
"""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from argon2 import PasswordHasher, profiles
from argon2.exceptions import InvalidHashError

from tlv_hunter.accounts import actions
from tlv_hunter.accounts.actions import Refused
from tlv_hunter.accounts.passwords import (
    PRODUCTION_HASHER,
    PasswordTooShort,
    check_password,
    dummy_check,
    hash_password,
    needs_rehash,
)
from tlv_hunter.accounts.tokens import new_key, new_opaque_id, new_session_token, secret_hash
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.contracts.session import SESSION_LIFETIME
from tlv_hunter.contracts.user import OPAQUE_ID, SHA256_HEX, User
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

NOW = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
ADMIN_PASSWORD = "admin-password-1"
FRIEND_PASSWORD = "friend-password-1"


class CountingHasher(PasswordHasher):
    """The cheapest hasher, counting its password checks."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.checks = 0

    def verify(self, hash: str | bytes, password: str | bytes) -> bool:  # noqa: A002
        self.checks += 1
        return super().verify(hash, password)


@pytest.fixture
def hasher() -> CountingHasher:
    return CountingHasher.from_parameters(profiles.CHEAPEST)


@pytest.fixture
def store(tmp_path: Path) -> SqliteUserDataStore:
    return SqliteUserDataStore(tmp_path / "userdata.sqlite3")


@pytest.fixture
def admin_token(store: SqliteUserDataStore, hasher: CountingHasher) -> str:
    actions.create_admin(store, "ron", ADMIN_PASSWORD, NOW, hasher=hasher)
    return actions.sign_in(store, "ron", ADMIN_PASSWORD, NOW, hasher=hasher).token


def _friend(
    store: SqliteUserDataStore,
    admin_token: str,
    hasher: PasswordHasher,
    username: str = "dana",
    password: str = FRIEND_PASSWORD,
) -> User:
    issued = actions.issue_key(store, admin_token, f"for {username}", NOW)
    return actions.sign_up(store, issued.key, username, password, NOW, hasher=hasher)


def _refused(reason: str) -> Any:
    return pytest.raises(Refused, match=f"^{reason}$")


# --- 1. passwords ---


def test_a_hash_verifies_and_a_wrong_password_is_false_not_an_exception(
    hasher: CountingHasher,
) -> None:
    stored = hash_password("correct horse", hasher)
    assert stored.startswith("$argon2id$")
    assert check_password(stored, "correct horse", hasher) is True
    assert check_password(stored, "wrong horse", hasher) is False


def test_a_password_under_8_characters_is_refused(hasher: CountingHasher) -> None:
    with pytest.raises(PasswordTooShort):
        hash_password("seven77", hasher)
    assert hash_password("eight888", hasher).startswith("$argon2id$")


def test_a_stored_hash_the_library_cannot_read_raises(hasher: CountingHasher) -> None:
    with pytest.raises(InvalidHashError):
        check_password("not a hash", "whatever1", hasher)


def test_the_production_hasher_has_rfc_9106_low_memory_parameters() -> None:
    expected = profiles.RFC_9106_LOW_MEMORY
    assert (
        PRODUCTION_HASHER.type,
        PRODUCTION_HASHER.time_cost,
        PRODUCTION_HASHER.memory_cost,
        PRODUCTION_HASHER.parallelism,
        PRODUCTION_HASHER.hash_len,
        PRODUCTION_HASHER.salt_len,
    ) == (
        expected.type,
        expected.time_cost,
        expected.memory_cost,
        expected.parallelism,
        expected.hash_len,
        expected.salt_len,
    )


def test_needs_rehash_when_the_parameters_differ(hasher: CountingHasher) -> None:
    stored = hash_password("correct horse", hasher)
    assert not needs_rehash(stored, hasher)
    assert needs_rehash(stored, PRODUCTION_HASHER)


def test_the_dummy_check_runs_one_password_check(hasher: CountingHasher) -> None:
    dummy_check("anything1", hasher)
    assert hasher.checks == 1


# --- tokens ---


def test_keys_tokens_and_ids_have_their_sizes_and_differ() -> None:
    assert len(new_key()) == 22  # 16 bytes, URL-safe base64 without padding: 128 bits
    assert len(new_session_token()) == 43  # 32 bytes: 256 bits
    assert OPAQUE_ID.fullmatch(new_opaque_id())
    assert SHA256_HEX.fullmatch(secret_hash(new_key()))
    assert len({new_key() for _ in range(50)}) == 50
    assert len({new_session_token() for _ in range(50)}) == 50


# --- the admin (#244) ---


def test_create_admin_makes_the_one_admin_with_no_key_and_a_new_profile(
    store: SqliteUserDataStore, hasher: CountingHasher
) -> None:
    admin = actions.create_admin(store, "ron", ADMIN_PASSWORD, NOW, hasher=hasher)
    assert (admin.is_admin, admin.signup_key_id, admin.disabled_at) == (True, None, None)
    assert store.list_users() == [admin]
    assert store.get_profile(admin.user_id) == new_profile(admin.user_id, NOW)
    assert admin.password_hash.startswith("$argon2id$")


def test_create_admin_refuses_a_bad_username_or_a_short_password(
    store: SqliteUserDataStore, hasher: CountingHasher
) -> None:
    with _refused("username_invalid"):
        actions.create_admin(store, "r", ADMIN_PASSWORD, NOW, hasher=hasher)
    with _refused("password_too_short"):
        actions.create_admin(store, "ron", "short", NOW, hasher=hasher)
    assert store.list_users() == []


# --- 2. sign-up ---


def test_sign_up_with_a_usable_key_creates_the_user_the_profile_and_uses_the_key(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    issued = actions.issue_key(store, admin_token, "for dana", NOW)
    later = NOW + timedelta(hours=1)
    user = actions.sign_up(store, issued.key, "Dana.K", FRIEND_PASSWORD, later, hasher=hasher)
    assert (user.username, user.is_admin, user.signup_key_id) == ("Dana.K", False, issued.key_id)
    assert (user.created_at, user.password_changed_at) == (later, later)
    assert store.get_user(user.user_id) == user
    assert store.get_profile(user.user_id) == new_profile(user.user_id, later)
    key = store.find_key_by_hash(secret_hash(issued.key))
    assert key is not None and (key.used_by, key.used_at) == (user.user_id, later)


def test_an_unknown_used_or_cancelled_key_is_refused(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    with _refused("key_not_usable"):
        actions.sign_up(store, new_key(), "dana", FRIEND_PASSWORD, NOW, hasher=hasher)
    issued = actions.issue_key(store, admin_token, "for dana", NOW)
    actions.sign_up(store, issued.key, "dana", FRIEND_PASSWORD, NOW, hasher=hasher)
    with _refused("key_not_usable"):
        actions.sign_up(store, issued.key, "noa", FRIEND_PASSWORD, NOW, hasher=hasher)
    cancelled = actions.issue_key(store, admin_token, "for noa", NOW)
    actions.cancel_key(store, admin_token, cancelled.key_id, NOW)
    with _refused("key_not_usable"):
        actions.sign_up(store, cancelled.key, "noa", FRIEND_PASSWORD, NOW, hasher=hasher)
    assert [user.username for user in store.list_users()] == ["ron", "dana"]


@pytest.mark.parametrize("username", ["דנה12", "da", "d" * 33, "dana k", "dana@x"])
def test_a_username_outside_the_rules_is_refused(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher, username: str
) -> None:
    issued = actions.issue_key(store, admin_token, "for a friend", NOW)
    with _refused("username_invalid"):
        actions.sign_up(store, issued.key, username, FRIEND_PASSWORD, NOW, hasher=hasher)
    key = store.find_key_by_hash(secret_hash(issued.key))
    assert key is not None and key.usable


def test_a_username_with_another_letter_case_is_taken_and_the_key_stays_usable(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    issued = actions.issue_key(store, admin_token, "for a friend", NOW)
    with _refused("username_taken"):
        actions.sign_up(store, issued.key, "RON", FRIEND_PASSWORD, NOW, hasher=hasher)
    key = store.find_key_by_hash(secret_hash(issued.key))
    assert key is not None and key.usable
    assert actions.sign_up(store, issued.key, "d" * 32, FRIEND_PASSWORD, NOW, hasher=hasher)


def test_sign_up_refuses_a_short_password(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    issued = actions.issue_key(store, admin_token, "for dana", NOW)
    with _refused("password_too_short"):
        actions.sign_up(store, issued.key, "dana", "seven77", NOW, hasher=hasher)


# --- 3. sign-in and the delay ---


def test_a_success_resets_the_failure_count(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)
    for _ in range(3):
        with _refused("wrong_credentials"):
            actions.sign_in(store, "dana", "wrong-password", NOW, hasher=hasher)
    failed = store.get_user(user.user_id)
    assert failed is not None
    assert (failed.failed_sign_ins, failed.last_failed_sign_in_at) == (3, NOW)
    actions.sign_in(store, "DANA", FRIEND_PASSWORD, NOW, hasher=hasher)
    reset = store.get_user(user.user_id)
    assert reset is not None and (reset.failed_sign_ins, reset.last_failed_sign_in_at) == (0, None)


def test_the_fifth_failure_starts_a_30_second_delay_with_no_password_check(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    _friend(store, admin_token, hasher)
    for n in range(4):
        at = NOW + timedelta(seconds=n)
        with _refused("wrong_credentials"):
            actions.sign_in(store, "dana", "wrong-password", at, hasher=hasher)
    fifth = NOW + timedelta(seconds=4)
    # After four failures an immediate attempt is still checked.
    with _refused("wrong_credentials"):
        actions.sign_in(store, "dana", "wrong-password", fifth, hasher=hasher)
    checks = hasher.checks
    with pytest.raises(Refused) as refusal:
        actions.sign_in(
            store, "dana", FRIEND_PASSWORD, fifth + timedelta(seconds=29), hasher=hasher
        )
    assert (refusal.value.reason, refusal.value.retry_after_seconds) == ("delayed", 1)
    assert hasher.checks == checks
    signed_in = actions.sign_in(
        store, "dana", FRIEND_PASSWORD, fifth + timedelta(seconds=30), hasher=hasher
    )
    assert hasher.checks == checks + 1
    assert signed_in.must_change_password is False


def test_an_unknown_username_gets_the_same_answer_after_a_dummy_check_and_stores_nothing(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    users = store.list_users()
    for username in ("nobody", "דנה"):
        checks = hasher.checks
        with _refused("wrong_credentials"):
            actions.sign_in(store, username, "whatever-1", NOW, hasher=hasher)
        assert hasher.checks == checks + 1
    assert store.list_users() == users


def test_a_disabled_user_is_refused(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)
    actions.disable_user(store, admin_token, user.user_id, NOW)
    with _refused("disabled"):
        actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher)


def test_a_user_who_must_change_the_password_reaches_only_the_change(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)
    actions.reset_password(store, admin_token, user.user_id, "temporary-1", NOW, hasher=hasher)
    signed_in = actions.sign_in(store, "dana", "temporary-1", NOW, hasher=hasher)
    assert signed_in.must_change_password is True
    # The must-change check comes before the admin check: any other action is refused by it.
    with _refused("must_change_password"):
        actions.issue_key(store, signed_in.token, "mine", NOW)
    actions.change_password(
        store, signed_in.token, "temporary-1", "new-password-1", NOW, hasher=hasher
    )
    changed = actions.session_user(store, signed_in.token, NOW)
    assert changed is not None and changed.must_change_password is False
    with _refused("not_admin"):
        actions.issue_key(store, signed_in.token, "mine", NOW)


def test_the_admin_must_change_a_reset_password_before_any_admin_action(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    admin = store.find_user_by_username("ron")
    assert admin is not None
    actions.reset_password(store, admin_token, admin.user_id, "temporary-1", NOW, hasher=hasher)
    token = actions.sign_in(store, "ron", "temporary-1", NOW, hasher=hasher).token
    with _refused("must_change_password"):
        actions.issue_key(store, token, "for dana", NOW)


def test_a_successful_sign_in_rehashes_a_hash_made_with_other_parameters(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)
    other = PasswordHasher(time_cost=2, memory_cost=8, parallelism=1, hash_len=4, salt_len=8)
    actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=other)
    rehashed = store.get_user(user.user_id)
    assert rehashed is not None and rehashed.password_hash != user.password_hash
    assert not needs_rehash(rehashed.password_hash, other)
    assert check_password(rehashed.password_hash, FRIEND_PASSWORD, other)
    assert rehashed.password_changed_at == user.password_changed_at


def test_a_failure_written_by_another_sign_in_meanwhile_is_counted(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    """Compare and set: the failure is applied again to the fresh record."""
    user = _friend(store, admin_token, hasher)

    class Racing:
        def __init__(self) -> None:
            self.raced = False

        def __getattr__(self, name: str) -> Any:
            return getattr(store, name)

        def save_user(self, record: User, *, expected: User) -> User:
            if not self.raced:
                self.raced = True
                bumped = expected.model_copy(
                    update={"failed_sign_ins": 1, "last_failed_sign_in_at": NOW}
                )
                store.save_user(bumped, expected=expected)
            return store.save_user(record, expected=expected)

    racing: Any = Racing()
    with _refused("wrong_credentials"):
        actions.sign_in(racing, "dana", "wrong-password", NOW, hasher=hasher)
    counted = store.get_user(user.user_id)
    assert counted is not None and counted.failed_sign_ins == 2


# --- 4. sessions ---


def test_a_session_is_valid_for_30_days_from_sign_in_not_after(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)
    token = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token
    last = NOW + SESSION_LIFETIME - timedelta(seconds=1)
    valid = actions.session_user(store, token, last)
    assert valid is not None and valid.user_id == user.user_id
    assert actions.session_user(store, token, NOW + SESSION_LIFETIME) is None
    assert actions.session_user(store, new_session_token(), NOW) is None


def test_only_the_tokens_hash_is_stored(
    store: SqliteUserDataStore, admin_token: str, tmp_path: Path
) -> None:
    session = store.find_session(secret_hash(admin_token))
    assert session is not None and session.ended_at is None
    assert admin_token.encode() not in (tmp_path / "userdata.sqlite3").read_bytes()


def test_sign_out_ends_one_session(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    _friend(store, admin_token, hasher)
    first = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token
    second = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token
    actions.sign_out(store, first, NOW)
    assert actions.session_user(store, first, NOW) is None
    assert actions.session_user(store, second, NOW) is not None
    actions.sign_out(store, first, NOW + timedelta(minutes=1))
    ended = store.find_session(secret_hash(first))
    assert ended is not None and ended.ended_at == NOW


def test_the_admins_reset_ends_every_session_and_the_failure_count(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)
    tokens = [
        actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token for _ in "ab"
    ]
    with _refused("wrong_credentials"):
        actions.sign_in(store, "dana", "wrong-password", NOW, hasher=hasher)
    later = NOW + timedelta(hours=1)
    actions.reset_password(store, admin_token, user.user_id, "temporary-1", later, hasher=hasher)
    assert all(actions.session_user(store, token, later) is None for token in tokens)
    reset = store.get_user(user.user_id)
    assert reset is not None
    assert (reset.must_change_password, reset.failed_sign_ins, reset.password_changed_at) == (
        True,
        0,
        later,
    )
    assert check_password(reset.password_hash, "temporary-1", hasher)


def test_the_users_own_change_ends_the_other_sessions_and_keeps_this_one(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    _friend(store, admin_token, hasher)
    current = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token
    other = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token
    with _refused("wrong_credentials"):
        actions.change_password(
            store, current, "wrong-password", "new-password-1", NOW, hasher=hasher
        )
    with _refused("password_too_short"):
        actions.change_password(store, current, FRIEND_PASSWORD, "short", NOW, hasher=hasher)
    actions.change_password(store, current, FRIEND_PASSWORD, "new-password-1", NOW, hasher=hasher)
    assert actions.session_user(store, current, NOW) is not None
    assert actions.session_user(store, other, NOW) is None
    with _refused("wrong_credentials"):
        actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher)
    assert actions.sign_in(store, "dana", "new-password-1", NOW, hasher=hasher)
    with _refused("not_signed_in"):
        actions.change_password(store, other, FRIEND_PASSWORD, "x" * 8, NOW, hasher=hasher)


def test_disabling_ends_every_session_and_enabling_does_not_reopen_them(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)
    token = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token
    actions.disable_user(store, admin_token, user.user_id, NOW)
    disabled = store.get_user(user.user_id)
    assert disabled is not None and disabled.disabled_at == NOW
    session = store.find_session(secret_hash(token))
    assert session is not None and session.ended_at == NOW
    assert store.get_profile(user.user_id) is not None  # kept (#265)
    actions.enable_user(store, admin_token, user.user_id, NOW)
    assert actions.session_user(store, token, NOW) is None
    assert actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher)


def test_a_failure_between_disabling_and_ending_the_sessions_leaves_the_user_locked_out(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    """#291: two calls in a fixed order, the disable first."""
    user = _friend(store, admin_token, hasher)
    token = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token

    class FailingEnd:
        def __getattr__(self, name: str) -> Any:
            return getattr(store, name)

        def end_sessions(self, *args: Any, **kwargs: Any) -> int:
            raise OSError("disk full")

    failing: Any = FailingEnd()
    with pytest.raises(OSError):
        actions.disable_user(failing, admin_token, user.user_id, NOW)
    session = store.find_session(secret_hash(token))
    assert session is not None and session.ended_at is None
    assert actions.session_user(store, token, NOW) is None
    later = NOW + timedelta(minutes=1)
    actions.disable_user(store, admin_token, user.user_id, later)
    ended = store.find_session(secret_hash(token))
    assert ended is not None and ended.ended_at == later
    kept = store.get_user(user.user_id)
    assert kept is not None and kept.disabled_at == NOW


# --- 5. keys ---


def test_an_issued_key_is_shown_once_and_only_its_hash_is_stored(
    store: SqliteUserDataStore, admin_token: str, tmp_path: Path
) -> None:
    issued = actions.issue_key(store, admin_token, "for dana", NOW)
    (record,) = store.list_keys()
    assert (record.key_id, record.key_hash, record.label) == (
        issued.key_id,
        secret_hash(issued.key),
        "for dana",
    )
    assert issued.key not in repr(issued)
    assert issued.key.encode() not in (tmp_path / "userdata.sqlite3").read_bytes()


def test_a_key_needs_a_label(store: SqliteUserDataStore, admin_token: str) -> None:
    with _refused("label_empty"):
        actions.issue_key(store, admin_token, "  ", NOW)
    assert store.list_keys() == []


def test_a_cancelled_key_stays_cancelled_and_a_used_key_cannot_be_cancelled(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    issued = actions.issue_key(store, admin_token, "for noa", NOW)
    actions.cancel_key(store, admin_token, issued.key_id, NOW)
    actions.cancel_key(store, admin_token, issued.key_id, NOW + timedelta(days=1))
    (cancelled,) = store.list_keys()
    assert cancelled.cancelled_at == NOW
    used = actions.issue_key(store, admin_token, "for dana", NOW)
    actions.sign_up(store, used.key, "dana", FRIEND_PASSWORD, NOW, hasher=hasher)
    with _refused("key_used"):
        actions.cancel_key(store, admin_token, used.key_id, NOW)
    with _refused("unknown_key"):
        actions.cancel_key(store, admin_token, new_opaque_id(), NOW)


# --- 6. admin rules ---


def test_only_the_admin_can_issue_cancel_reset_disable_and_enable(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    issued = actions.issue_key(store, admin_token, "spare", NOW)
    user = _friend(store, admin_token, hasher)
    token = actions.sign_in(store, "dana", FRIEND_PASSWORD, NOW, hasher=hasher).token
    signed_in = store.get_user(user.user_id)
    calls = [
        lambda t: actions.issue_key(store, t, "mine", NOW),
        lambda t: actions.cancel_key(store, t, issued.key_id, NOW),
        lambda t: actions.reset_password(store, t, user.user_id, "temporary-1", NOW, hasher=hasher),
        lambda t: actions.disable_user(store, t, user.user_id, NOW),
        lambda t: actions.enable_user(store, t, user.user_id, NOW),
    ]
    for call in calls:
        with _refused("not_admin"):
            call(token)
        with _refused("not_signed_in"):
            call(new_session_token())
    assert store.get_user(user.user_id) == signed_in
    spare = store.find_key_by_hash(secret_hash(issued.key))
    assert spare is not None and spare.usable


def test_the_admin_cannot_be_disabled(store: SqliteUserDataStore, admin_token: str) -> None:
    admin = store.find_user_by_username("ron")
    assert admin is not None
    with _refused("admin_cannot_be_disabled"):
        actions.disable_user(store, admin_token, admin.user_id, NOW)
    assert actions.session_user(store, admin_token, NOW) == admin


def test_an_admin_action_on_an_unknown_user_is_refused(
    store: SqliteUserDataStore, admin_token: str
) -> None:
    with _refused("unknown_user"):
        actions.disable_user(store, admin_token, new_opaque_id(), NOW)


def test_compare_and_set_gives_up_after_three_stale_writes(
    store: SqliteUserDataStore, admin_token: str, hasher: CountingHasher
) -> None:
    user = _friend(store, admin_token, hasher)

    class AlwaysStale:
        def __getattr__(self, name: str) -> Any:
            return getattr(store, name)

        def save_user(self, record: User, *, expected: User) -> User:
            raise StaleRecordError(record.user_id)

    stale: Any = AlwaysStale()
    with pytest.raises(StaleRecordError):
        actions.disable_user(stale, admin_token, user.user_id, NOW)


# --- no secret in a log line ---


def test_no_password_key_token_or_hash_reaches_a_log_line_or_a_refusal(
    store: SqliteUserDataStore, hasher: CountingHasher, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    secrets_seen: list[str] = [ADMIN_PASSWORD, FRIEND_PASSWORD, "temporary-1", "new-password-1"]
    refusals: list[str] = []

    def attempt(call: Any) -> None:
        try:
            call()
        except Refused as refusal:
            refusals.append(str(refusal))

    admin = actions.create_admin(store, "ron", ADMIN_PASSWORD, NOW, hasher=hasher)
    admin_token = actions.sign_in(store, "ron", ADMIN_PASSWORD, NOW, hasher=hasher).token
    issued = actions.issue_key(store, admin_token, "for dana", NOW)
    spare = actions.issue_key(store, admin_token, "spare", NOW)
    user = actions.sign_up(store, issued.key, "dana", FRIEND_PASSWORD, NOW, hasher=hasher)
    attempt(lambda: actions.sign_up(store, issued.key, "noa", FRIEND_PASSWORD, NOW, hasher=hasher))
    for _ in range(6):
        attempt(lambda: actions.sign_in(store, "dana", ADMIN_PASSWORD, NOW, hasher=hasher))
    attempt(lambda: actions.sign_in(store, "nobody", FRIEND_PASSWORD, NOW, hasher=hasher))
    actions.reset_password(store, admin_token, user.user_id, "temporary-1", NOW, hasher=hasher)
    token = actions.sign_in(store, "dana", "temporary-1", NOW, hasher=hasher).token
    attempt(lambda: actions.issue_key(store, token, "mine", NOW))
    actions.change_password(store, token, "temporary-1", "new-password-1", NOW, hasher=hasher)
    attempt(lambda: actions.issue_key(store, token, "mine", NOW))
    actions.cancel_key(store, admin_token, spare.key_id, NOW)
    actions.disable_user(store, admin_token, user.user_id, NOW)
    attempt(lambda: actions.disable_user(store, admin_token, admin.user_id, NOW))
    actions.enable_user(store, admin_token, user.user_id, NOW)
    actions.sign_out(store, token, NOW)

    secrets_seen += [issued.key, spare.key, admin_token, token]
    secrets_seen += [secret_hash(value) for value in (issued.key, spare.key, admin_token, token)]
    secrets_seen += [record.password_hash for record in store.list_users()]
    assert caplog.records and refusals
    text = caplog.text + "\n".join(refusals)
    for secret in secrets_seen:
        assert secret not in text
    assert "dana" not in caplog.text  # log lines name user_id, never a username
