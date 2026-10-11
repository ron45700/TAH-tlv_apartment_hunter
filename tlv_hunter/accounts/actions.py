"""The account actions over `UserDataStore` (task 3.5; SCHEMA.md, Gate C; DECISIONS.md #242–#244,
#262–#266, #288 R1, R3, R5, R7, R8, #290, #291, #293).

Sign-up with a one-time key, sign-in with the delay after failures, sign-out, the session check,
the user's own password change, and the admin's actions: reset, disable and enable, issue and
cancel keys, and the one admin's creation. **The admin-only checks are here, not in the pages**:
every admin action takes the acting session's token and refuses unless it is the admin's.

A refusal is `Refused`, whose message is only its reason: never a password, a key, a token or a
hash. The log lines name `user_id` and `key_id` only (opaque, #262), never a username.

Writes of a `User` or a `SignupKey` are compare and set; on a stale record the change is applied
again to a fresh read, at most `STORE_ATTEMPTS` times in all.
"""

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from argon2 import PasswordHasher
from pydantic import BaseModel

from tlv_hunter.accounts.passwords import (
    PRODUCTION_HASHER,
    PasswordTooShort,
    check_password,
    dummy_check,
    hash_password,
    needs_rehash,
    require_password_length,
)
from tlv_hunter.accounts.tokens import new_key, new_opaque_id, new_session_token, secret_hash
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.contracts.session import SESSION_LIFETIME, SESSION_SCHEMA_VERSION, Session
from tlv_hunter.contracts.signup_key import SIGNUP_KEY_SCHEMA_VERSION, SignupKey
from tlv_hunter.contracts.user import USER_SCHEMA_VERSION, USERNAME, User
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.userdata.base import KeyNotUsable, UserDataStore, UsernameTaken

logger = logging.getLogger(__name__)

# The delay after failed sign-ins (#264, R1).
FAILURES_BEFORE_DELAY = 5
SIGN_IN_DELAY = timedelta(seconds=30)
STORE_ATTEMPTS = 3

RefusalReason = Literal[
    "not_signed_in",
    "must_change_password",
    "not_admin",
    "username_invalid",
    "username_taken",
    "password_too_short",
    "key_not_usable",
    "wrong_credentials",
    "delayed",
    "disabled",
    "changed",
    "unknown_user",
    "admin_cannot_be_disabled",
    "label_empty",
    "unknown_key",
    "key_used",
]


class Refused(Exception):
    """An action refused. `retry_after_seconds` is set for `"delayed"` only (#264, R1)."""

    def __init__(self, reason: RefusalReason, retry_after_seconds: int | None = None) -> None:
        super().__init__(reason)
        self.reason: RefusalReason = reason
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class SignedIn:
    """A new session. `token` goes into the cookie (3.7) and nowhere else; the store keeps its
    hash. With `must_change_password`, the session reaches only the password change."""

    user_id: str
    must_change_password: bool
    token: str = field(repr=False)


@dataclass(frozen=True)
class IssuedKey:
    """A new key, shown once to the admin (#266); the store keeps only its hash."""

    key_id: str
    key: str = field(repr=False)


# --- the admin's account (#244) ---


def create_admin(
    store: UserDataStore,
    username: str,
    password: str,
    now: datetime,
    *,
    hasher: PasswordHasher = PRODUCTION_HASHER,
) -> User:
    """The one admin, with no key, and their profile (#244, #268). `AdminExists` if there is one;
    `Refused` for a username or password that breaks Gate C's rules."""
    require_new_credentials(username, password)
    user = _new_user(
        username, _hash_or_refuse(password, hasher), now, is_admin=True, signup_key_id=None
    )
    try:
        store.create_admin(user, new_profile(user.user_id, now))
    except UsernameTaken as error:
        raise Refused("username_taken") from error
    logger.info("admin created: user %s", user.user_id)
    return user


# --- sign-up, sign-in, sign-out, the session ---


def sign_up(
    store: UserDataStore,
    key: str,
    username: str,
    password: str,
    now: datetime,
    *,
    hasher: PasswordHasher = PRODUCTION_HASHER,
) -> User:
    """A new user with a usable key (#243): the user, their profile with #268's defaults, and the
    key marked used, in one transaction. The user signs in afterwards."""
    require_new_credentials(username, password)
    password_hash = _hash_or_refuse(password, hasher)
    key_hash = secret_hash(key)
    found = store.find_key_by_hash(key_hash)
    if found is None or not found.usable:
        logger.info("sign-up refused: no usable key")
        raise Refused("key_not_usable")
    user = _new_user(username, password_hash, now, is_admin=False, signup_key_id=found.key_id)
    try:
        store.create_user(user, new_profile(user.user_id, now), key_hash, now)
    except KeyNotUsable as error:
        logger.info("sign-up refused: no usable key")
        raise Refused("key_not_usable") from error
    except UsernameTaken as error:
        logger.info("sign-up refused: username taken")
        raise Refused("username_taken") from error
    logger.info("signed up: user %s with key %s", user.user_id, found.key_id)
    return user


def sign_in(
    store: UserDataStore,
    username: str,
    password: str,
    now: datetime,
    *,
    hasher: PasswordHasher = PRODUCTION_HASHER,
) -> SignedIn:
    """A new session of 30 days (#263, R5), or `Refused`: `"wrong_credentials"` (also for an
    unknown username, after a dummy check, storing nothing), `"delayed"` (from the 5th
    consecutive failure, within 30 seconds of the last, with no password check), `"disabled"`."""
    user = store.find_user_by_username(username) if USERNAME.fullmatch(username) else None
    if user is None:
        dummy_check(password, hasher)
        logger.info("sign-in refused: unknown username")
        raise Refused("wrong_credentials")
    wait = _delay_left(user, now)
    if wait is not None:
        logger.info("sign-in refused: delayed, user %s", user.user_id)
        raise Refused("delayed", retry_after_seconds=wait)
    if not check_password(user.password_hash, password, hasher):
        _update_user(store, user.user_id, lambda fresh: _with_failure(fresh, now))
        logger.info("sign-in refused: wrong password, user %s", user.user_id)
        raise Refused("wrong_credentials")
    if user.disabled_at is not None:
        logger.info("sign-in refused: disabled, user %s", user.user_id)
        raise Refused("disabled")
    _update_user(store, user.user_id, lambda fresh: _after_success(fresh, password, hasher))
    token = new_session_token()
    store.add_session(
        Session(
            schema_version=SESSION_SCHEMA_VERSION,
            token_hash=secret_hash(token),
            user_id=user.user_id,
            created_at=now,
            expires_at=now + SESSION_LIFETIME,
            ended_at=None,
        )
    )
    logger.info("signed in: user %s", user.user_id)
    return SignedIn(
        user_id=user.user_id, must_change_password=user.must_change_password, token=token
    )


def sign_out(store: UserDataStore, token: str, now: datetime) -> None:
    """Ends the session, if it is still open."""
    store.end_session(secret_hash(token), now)


def session_user(store: UserDataStore, token: str, now: datetime) -> User | None:
    """The session's user while the session is valid (SCHEMA.md, `Session`): not ended, not
    expired, its user not disabled. Else `None`. The caller sends a user whose
    `must_change_password` is `True` to the password change only."""
    session = store.find_session(secret_hash(token))
    if session is None or session.ended_at is not None or now >= session.expires_at:
        return None
    user = store.get_user(session.user_id)
    if user is None or user.disabled_at is not None:
        return None
    return user


# --- passwords ---


def change_password(
    store: UserDataStore,
    token: str,
    current_password: str,
    new_password: str,
    now: datetime,
    *,
    hasher: PasswordHasher = PRODUCTION_HASHER,
) -> None:
    """The user's own change, also the one a temporary password requires (#262). Ends the user's
    other sessions and keeps this one (R3)."""
    user = session_user(store, token, now)
    if user is None:
        raise Refused("not_signed_in")
    if not check_password(user.password_hash, current_password, hasher):
        logger.info("password change refused: wrong password, user %s", user.user_id)
        raise Refused("wrong_credentials")
    new_hash = _hash_or_refuse(new_password, hasher)

    def change(fresh: User) -> User:
        if fresh.password_hash != user.password_hash:
            raise Refused("changed")
        return _changed(
            fresh, password_hash=new_hash, must_change_password=False, password_changed_at=now
        )

    _update_user(store, user.user_id, change)
    store.end_sessions(user.user_id, now, keep=secret_hash(token))
    logger.info("password changed: user %s", user.user_id)


def reset_password(
    store: UserDataStore,
    token: str,
    user_id: str,
    temporary_password: str,
    now: datetime,
    *,
    hasher: PasswordHasher = PRODUCTION_HASHER,
) -> None:
    """The admin sets a temporary password (#262): the user must change it at the next sign-in,
    the failure count goes to 0 (#264), and every session of the user ends (#263)."""
    admin = _require_admin(store, token, now)
    new_hash = _hash_or_refuse(temporary_password, hasher)
    _update_user(
        store,
        user_id,
        lambda fresh: _changed(
            fresh,
            password_hash=new_hash,
            must_change_password=True,
            password_changed_at=now,
            failed_sign_ins=0,
            last_failed_sign_in_at=None,
        ),
    )
    store.end_sessions(user_id, now)
    logger.info("password reset: user %s, by %s", user_id, admin.user_id)


# --- disabling (#265) ---


def disable_user(store: UserDataStore, token: str, user_id: str, now: datetime) -> None:
    """Two calls in a fixed order (#291): the user is disabled first, then their sessions end. A
    failure between them leaves the user locked out, since a disabled user's session is invalid
    already; disabling again ends the sessions left. The admin cannot be disabled (R8)."""
    admin = _require_admin(store, token, now)

    def disable(fresh: User) -> User:
        if fresh.is_admin:
            raise Refused("admin_cannot_be_disabled")
        return fresh if fresh.disabled_at is not None else _changed(fresh, disabled_at=now)

    _update_user(store, user_id, disable)
    store.end_sessions(user_id, now)
    logger.info("user disabled: user %s, by %s", user_id, admin.user_id)


def enable_user(store: UserDataStore, token: str, user_id: str, now: datetime) -> None:
    """The user can sign in again; their ended sessions stay ended."""
    admin = _require_admin(store, token, now)
    _update_user(store, user_id, lambda fresh: _changed(fresh, disabled_at=None))
    logger.info("user enabled: user %s, by %s", user_id, admin.user_id)


# --- keys (#243, #266) ---


def issue_key(store: UserDataStore, token: str, label: str, now: datetime) -> IssuedKey:
    """A new key with its label, shown once: the store keeps only its hash (#266)."""
    admin = _require_admin(store, token, now)
    if not label.strip():
        raise Refused("label_empty")
    key = new_key()
    record = SignupKey(
        schema_version=SIGNUP_KEY_SCHEMA_VERSION,
        key_id=new_opaque_id(),
        key_hash=secret_hash(key),
        label=label,
        created_at=now,
        used_by=None,
        used_at=None,
        cancelled_at=None,
    )
    store.add_key(record)
    logger.info("key issued: key %s, by %s", record.key_id, admin.user_id)
    return IssuedKey(key_id=record.key_id, key=key)


def cancel_key(store: UserDataStore, token: str, key_id: str, now: datetime) -> None:
    """Cancels an unused key (#243); a cancelled key stays cancelled, at its first time (#266)."""
    admin = _require_admin(store, token, now)
    for _ in range(STORE_ATTEMPTS):
        current = next((key for key in store.list_keys() if key.key_id == key_id), None)
        if current is None:
            raise Refused("unknown_key")
        if current.used_by is not None:
            raise Refused("key_used")
        if current.cancelled_at is not None:
            return
        try:
            store.save_key(_changed(current, cancelled_at=now), expected=current)
        except StaleRecordError:
            continue
        logger.info("key cancelled: key %s, by %s", key_id, admin.user_id)
        return
    raise StaleRecordError(key_id)


# --- helpers ---


def require_new_credentials(username: str, password: str) -> None:
    """Gate C's rules for a new account (#262), checked before anything is written: the
    username's characters and length, the password's length."""
    if not USERNAME.fullmatch(username):
        raise Refused("username_invalid")
    try:
        require_password_length(password)
    except PasswordTooShort as error:
        raise Refused("password_too_short") from error


def _hash_or_refuse(password: str, hasher: PasswordHasher) -> str:
    try:
        return hash_password(password, hasher)
    except PasswordTooShort as error:
        raise Refused("password_too_short") from error


def _new_user(
    username: str,
    password_hash: str,
    now: datetime,
    *,
    is_admin: bool,
    signup_key_id: str | None,
) -> User:
    return User(
        schema_version=USER_SCHEMA_VERSION,
        user_id=new_opaque_id(),
        username=username,
        password_hash=password_hash,
        is_admin=is_admin,
        created_at=now,
        signup_key_id=signup_key_id,
        must_change_password=False,
        password_changed_at=now,
        disabled_at=None,
        failed_sign_ins=0,
        last_failed_sign_in_at=None,
    )


def _signed_in(store: UserDataStore, token: str, now: datetime) -> User:
    user = session_user(store, token, now)
    if user is None:
        raise Refused("not_signed_in")
    if user.must_change_password:
        raise Refused("must_change_password")
    return user


def _require_admin(store: UserDataStore, token: str, now: datetime) -> User:
    user = _signed_in(store, token, now)
    if not user.is_admin:
        logger.warning("admin action refused: user %s is not the admin", user.user_id)
        raise Refused("not_admin")
    return user


def _delay_left(user: User, now: datetime) -> int | None:
    """Whole seconds to wait, or `None` when the attempt is checked (#264, R1)."""
    if user.failed_sign_ins < FAILURES_BEFORE_DELAY or user.last_failed_sign_in_at is None:
        return None
    left = user.last_failed_sign_in_at + SIGN_IN_DELAY - now
    return math.ceil(left.total_seconds()) if left > timedelta(0) else None


def _with_failure(user: User, now: datetime) -> User:
    return _changed(user, failed_sign_ins=user.failed_sign_ins + 1, last_failed_sign_in_at=now)


def _after_success(user: User, password: str, hasher: PasswordHasher) -> User:
    """The failure count back to 0; the hash remade if its parameters are not the hasher's."""
    changes: dict[str, object] = {"failed_sign_ins": 0, "last_failed_sign_in_at": None}
    if needs_rehash(user.password_hash, hasher):
        changes["password_hash"] = hash_password(password, hasher)
    return _changed(user, **changes)


def _update_user(store: UserDataStore, user_id: str, change: Callable[[User], User]) -> User:
    """Compare and set, the change applied again to a fresh read on a stale record."""
    for _ in range(STORE_ATTEMPTS):
        current = store.get_user(user_id)
        if current is None:
            raise Refused("unknown_user")
        updated = change(current)
        if updated == current:
            return current
        try:
            return store.save_user(updated, expected=current)
        except StaleRecordError:
            continue
    raise StaleRecordError(user_id)


def _changed[M: BaseModel](record: M, **changes: object) -> M:
    """A copy with `changes`, validated: `model_copy` alone skips the validators."""
    return type(record).model_validate({**record.model_dump(), **changes})
