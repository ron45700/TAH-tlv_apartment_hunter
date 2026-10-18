"""`UserDataStore` over the same SQLite file as `store/` and `state/` (DECISIONS.md #267, #289).

One JSON document per record, written and read by the pydantic model, plus lookup columns only
(#65). Its own tables and layout row; it never touches `raw_posts`, `post_lifecycle`, `listings`
or `group_watermarks`. Its layout version 2 adds a trigger on `corrections` that moves the store
generation counter (#316, `store_generation.py`), whose one-row table it creates when it lays out
a new file first. Gate F's tables (#453) have their own layout row, `userdata.telegram`, created
when absent, as `store.listings` is in `store/`; they move no counter (no card changes with them).
A report's or a correction's `listing_id` has no foreign key: they outlive
their post (#255). SQLite only, as `state/` is (#64).
"""

import sqlite3
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from tlv_hunter import store_generation
from tlv_hunter.contracts.classification_report import ClassificationReport
from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.contracts.sent_alert import SentAlert
from tlv_hunter.contracts.session import Session
from tlv_hunter.contracts.signup_key import SignupKey
from tlv_hunter.contracts.telegram_link_code import TelegramLinkCode
from tlv_hunter.contracts.user import User
from tlv_hunter.contracts.viewed_post import VIEWED_POST_SCHEMA_VERSION, ViewedPost
from tlv_hunter.sqlite_busy import BUSY_TIMEOUT_SECONDS
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.userdata.base import (
    AdminExists,
    ChatLinkedElsewhere,
    CorrectionInForce,
    KeyNotUsable,
    LinkCodeNotUsable,
    OpenReportExists,
    UsernameTaken,
)

# The same minimum as `store/` (#289, 3.4 (a)).
MIN_SQLITE_VERSION = (3, 38, 0)
LAYOUT_MODULE = "userdata"
# Version 2 (DECISIONS.md #316): the counter trigger on `corrections`; a file at version 1 is
# refused until `jobs/add_store_generation.py` migrates it.
LAYOUT_VERSION = 2
# Gate F's tables (#453): their own row, created when absent.
TELEGRAM_LAYOUT_MODULE = "userdata.telegram"
TELEGRAM_LAYOUT_VERSION = 1

_CREATE_LAYOUT_VERSION = (
    "CREATE TABLE IF NOT EXISTS layout_version (module TEXT PRIMARY KEY, version INTEGER NOT NULL)"
)
_CREATE_TABLES = (
    "CREATE TABLE users ("
    "user_id TEXT PRIMARY KEY, username_lower TEXT NOT NULL UNIQUE, doc TEXT NOT NULL)",
    "CREATE TABLE signup_keys ("
    "key_id TEXT PRIMARY KEY, key_hash TEXT NOT NULL UNIQUE, doc TEXT NOT NULL)",
    "CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, "
    "user_id TEXT NOT NULL REFERENCES users (user_id), doc TEXT NOT NULL)",
    "CREATE INDEX sessions_user_id ON sessions (user_id)",
    "CREATE TABLE profiles ("
    "user_id TEXT PRIMARY KEY REFERENCES users (user_id), doc TEXT NOT NULL)",
    "CREATE TABLE viewed_posts (user_id TEXT NOT NULL REFERENCES users (user_id), "
    "listing_id TEXT NOT NULL, doc TEXT NOT NULL, PRIMARY KEY (user_id, listing_id))",
    "CREATE TABLE reports (report_id TEXT PRIMARY KEY, listing_id TEXT NOT NULL, "
    "reported_by TEXT NOT NULL REFERENCES users (user_id), status TEXT NOT NULL, "
    "doc TEXT NOT NULL)",
    "CREATE INDEX reports_listing_id ON reports (listing_id)",
    "CREATE UNIQUE INDEX reports_one_open_per_reporter "
    "ON reports (listing_id, reported_by) WHERE status = 'open'",
    "CREATE TABLE corrections (correction_id TEXT PRIMARY KEY, listing_id TEXT NOT NULL, "
    "field TEXT NOT NULL, in_force INTEGER NOT NULL, doc TEXT NOT NULL)",
    "CREATE UNIQUE INDEX corrections_one_in_force "
    "ON corrections (listing_id, field) WHERE in_force = 1",
)

_CREATE_TELEGRAM_TABLES = (
    "CREATE TABLE telegram_link_codes (code_hash TEXT PRIMARY KEY, "
    "user_id TEXT NOT NULL REFERENCES users (user_id), doc TEXT NOT NULL)",
    "CREATE TABLE sent_alerts (user_id TEXT NOT NULL REFERENCES users (user_id), "
    "listing_id TEXT NOT NULL, doc TEXT NOT NULL, PRIMARY KEY (user_id, listing_id))",
)


# What version 2 adds (#316): run after the tables on a new file, and alone by the migration.
USERDATA_GENERATION_STATEMENTS = (
    *store_generation.CREATE_TABLE,
    *store_generation.triggers("corrections"),
)


class SqliteUserDataStore:
    """One connection per operation; every write in `BEGIN IMMEDIATE`."""

    def __init__(self, path: Path) -> None:
        if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
            raise RuntimeError(
                f"SQLite {sqlite3.sqlite_version} is too old; module {LAYOUT_MODULE!r} needs "
                f"{'.'.join(map(str, MIN_SQLITE_VERSION))} or later"
            )
        self._path = Path(path)
        with self._transaction() as conn:
            conn.execute(_CREATE_LAYOUT_VERSION)
            row = conn.execute(
                "SELECT version FROM layout_version WHERE module = ?", (LAYOUT_MODULE,)
            ).fetchone()
            if row is None:
                for statement in (*_CREATE_TABLES, *USERDATA_GENERATION_STATEMENTS):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO layout_version (module, version) VALUES (?, ?)",
                    (LAYOUT_MODULE, LAYOUT_VERSION),
                )
            elif row[0] == LAYOUT_VERSION - 1 == 1:
                raise RuntimeError(
                    store_generation.not_migrated(self._path, LAYOUT_MODULE, LAYOUT_VERSION, row[0])
                )
            elif row[0] != LAYOUT_VERSION:
                raise RuntimeError(
                    f"{self._path}: module {LAYOUT_MODULE!r} expects layout version "
                    f"{LAYOUT_VERSION}, found {row[0]}; no automatic migration"
                )
            row = conn.execute(
                "SELECT version FROM layout_version WHERE module = ?", (TELEGRAM_LAYOUT_MODULE,)
            ).fetchone()
            if row is None:
                for statement in _CREATE_TELEGRAM_TABLES:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO layout_version (module, version) VALUES (?, ?)",
                    (TELEGRAM_LAYOUT_MODULE, TELEGRAM_LAYOUT_VERSION),
                )
            elif row[0] != TELEGRAM_LAYOUT_VERSION:
                raise RuntimeError(
                    f"{self._path}: module {TELEGRAM_LAYOUT_MODULE!r} expects layout version "
                    f"{TELEGRAM_LAYOUT_VERSION}, found {row[0]}; no automatic migration"
                )

    # --- users ---

    def create_admin(self, user: User, profile: Profile) -> User:
        if not user.is_admin:
            raise ValueError("create_admin creates the admin only")
        _require_profile_of(user, profile)
        with self._transaction() as conn:
            for (doc,) in conn.execute("SELECT doc FROM users").fetchall():
                if User.from_stored_json(doc).is_admin:
                    raise AdminExists("there is already an admin (#244)")
            _insert_user(conn, user)
            _put(conn, "profiles", ("user_id",), (profile.user_id,), profile)
        return user

    def create_user(self, user: User, profile: Profile, key_hash: str, now: datetime) -> User:
        if user.is_admin:
            raise ValueError("the admin is created by create_admin, not by a key (#244)")
        _require_profile_of(user, profile)
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT doc FROM signup_keys WHERE key_hash = ?", (key_hash,)
            ).fetchone()
            key = None if row is None else SignupKey.model_validate_json(row[0])
            if key is None or not key.usable or key.key_id != user.signup_key_id:
                raise KeyNotUsable("no usable key with that hash for this user")
            _insert_user(conn, user)
            _put(conn, "profiles", ("user_id",), (profile.user_id,), profile)
            used = key.model_copy(update={"used_by": user.user_id, "used_at": now})
            SignupKey.model_validate(used.model_dump())
            conn.execute(
                "UPDATE signup_keys SET doc = ? WHERE key_id = ?",
                (used.model_dump_json(), key.key_id),
            )
        return user

    def get_user(self, user_id: str) -> User | None:
        return self._get(User, "SELECT doc FROM users WHERE user_id = ?", (user_id,))

    def find_user_by_username(self, username: str) -> User | None:
        return self._get(
            User, "SELECT doc FROM users WHERE username_lower = ?", (username.lower(),)
        )

    def list_users(self) -> list[User]:
        return self._all(User, "SELECT doc FROM users ORDER BY rowid")

    def save_user(self, record: User, *, expected: User) -> User:
        if (record.user_id, record.username) != (expected.user_id, expected.username):
            raise ValueError("a user's id and username never change (#262)")
        with self._transaction() as conn:
            _require_expected(
                conn, User, "SELECT doc FROM users WHERE user_id = ?", record.user_id, expected
            )
            conn.execute(
                "UPDATE users SET doc = ? WHERE user_id = ?",
                (record.model_dump_json(), record.user_id),
            )
        return record

    # --- keys ---

    def add_key(self, key: SignupKey) -> SignupKey:
        if not key.usable:
            raise ValueError("a new key is unused and not cancelled")
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO signup_keys (key_id, key_hash, doc) VALUES (?, ?, ?)",
                (key.key_id, key.key_hash, key.model_dump_json()),
            )
        return key

    def list_keys(self) -> list[SignupKey]:
        return self._all(SignupKey, "SELECT doc FROM signup_keys ORDER BY rowid")

    def find_key_by_hash(self, key_hash: str) -> SignupKey | None:
        return self._get(SignupKey, "SELECT doc FROM signup_keys WHERE key_hash = ?", (key_hash,))

    def save_key(self, record: SignupKey, *, expected: SignupKey) -> SignupKey:
        if (record.key_id, record.key_hash) != (expected.key_id, expected.key_hash):
            raise ValueError("a key's id and hash never change")
        if expected.cancelled_at is not None and record.cancelled_at is None:
            raise ValueError("a cancelled key is not un-cancelled (#266)")
        with self._transaction() as conn:
            _require_expected(
                conn,
                SignupKey,
                "SELECT doc FROM signup_keys WHERE key_id = ?",
                record.key_id,
                expected,
            )
            conn.execute(
                "UPDATE signup_keys SET doc = ? WHERE key_id = ?",
                (record.model_dump_json(), record.key_id),
            )
        return record

    # --- sessions ---

    def add_session(self, session: Session) -> Session:
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO sessions (token_hash, user_id, doc) VALUES (?, ?, ?)",
                (session.token_hash, session.user_id, session.model_dump_json()),
            )
        return session

    def find_session(self, token_hash: str) -> Session | None:
        return self._get(Session, "SELECT doc FROM sessions WHERE token_hash = ?", (token_hash,))

    def end_session(self, token_hash: str, now: datetime) -> None:
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT doc FROM sessions WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            if row is not None:
                _end(conn, Session.model_validate_json(row[0]), now)

    def end_sessions(self, user_id: str, now: datetime, keep: str | None = None) -> int:
        ended = 0
        with self._transaction() as conn:
            rows = conn.execute(
                "SELECT doc FROM sessions WHERE user_id = ? ORDER BY rowid", (user_id,)
            ).fetchall()
            for (doc,) in rows:
                session = Session.model_validate_json(doc)
                if session.token_hash != keep and _end(conn, session, now):
                    ended += 1
        return ended

    # --- profiles ---

    def get_profile(self, user_id: str) -> Profile | None:
        """Through `Profile.from_stored_json`: a version-1 profile reads as version 2 (#317)."""
        with self._connect() as conn:
            row = conn.execute("SELECT doc FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return None if row is None else Profile.from_stored_json(row[0])

    def save_profile(self, profile: Profile) -> Profile:
        with self._transaction() as conn:
            _put(conn, "profiles", ("user_id",), (profile.user_id,), profile)
        return profile

    # --- viewed posts ---

    def mark_viewed(self, user_id: str, listing_id: str, at: datetime) -> None:
        record = ViewedPost(
            schema_version=VIEWED_POST_SCHEMA_VERSION,
            user_id=user_id,
            listing_id=listing_id,
            viewed_at=at,
        )
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO viewed_posts (user_id, listing_id, doc) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, listing_id) DO NOTHING",
                (user_id, listing_id, record.model_dump_json()),
            )

    def unmark_viewed(self, user_id: str, listing_ids: Collection[str]) -> None:
        with self._transaction() as conn:
            conn.executemany(
                "DELETE FROM viewed_posts WHERE user_id = ? AND listing_id = ?",
                [(user_id, listing_id) for listing_id in listing_ids],
            )

    def viewed_listing_ids(self, user_id: str) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT listing_id FROM viewed_posts WHERE user_id = ?", (user_id,)
            ).fetchall()
        return {listing_id for (listing_id,) in rows}

    # --- reports ---

    def add_report(self, report: ClassificationReport) -> ClassificationReport:
        if report.status != "open":
            raise ValueError("a new report is open")
        with self._transaction() as conn:
            found = conn.execute(
                "SELECT 1 FROM reports WHERE listing_id = ? AND reported_by = ? "
                "AND status = 'open'",
                (report.listing_id, report.reported_by),
            ).fetchone()
            if found is not None:
                raise OpenReportExists("the reporter already has an open report on the post")
            conn.execute(
                "INSERT INTO reports (report_id, listing_id, reported_by, status, doc) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    report.report_id,
                    report.listing_id,
                    report.reported_by,
                    report.status,
                    report.model_dump_json(),
                ),
            )
        return report

    def find_reports(
        self, listing_id: str | None = None, status: str | None = None
    ) -> list[ClassificationReport]:
        sql, params = _filtered(
            "SELECT doc FROM reports", {"listing_id": listing_id, "status": status}
        )
        return self._all(ClassificationReport, sql + " ORDER BY rowid", params)

    def save_report(
        self, record: ClassificationReport, *, expected: ClassificationReport
    ) -> ClassificationReport:
        if (record.report_id, record.listing_id, record.reported_by) != (
            expected.report_id,
            expected.listing_id,
            expected.reported_by,
        ):
            raise ValueError("a report's id, post and reporter never change")
        with self._transaction() as conn:
            _require_expected(
                conn,
                ClassificationReport,
                "SELECT doc FROM reports WHERE report_id = ?",
                record.report_id,
                expected,
            )
            conn.execute(
                "UPDATE reports SET status = ?, doc = ? WHERE report_id = ?",
                (record.status, record.model_dump_json(), record.report_id),
            )
        return record

    # --- corrections ---

    def add_correction(self, correction: FieldCorrection) -> FieldCorrection:
        if not correction.in_force:
            raise ValueError("a new correction is in force")
        with self._transaction() as conn:
            found = conn.execute(
                "SELECT 1 FROM corrections WHERE listing_id = ? AND field = ? AND in_force = 1",
                (correction.listing_id, correction.field),
            ).fetchone()
            if found is not None:
                raise CorrectionInForce("the field already has a correction in force")
            conn.execute(
                "INSERT INTO corrections (correction_id, listing_id, field, in_force, doc) "
                "VALUES (?, ?, ?, 1, ?)",
                (
                    correction.correction_id,
                    correction.listing_id,
                    correction.field,
                    correction.model_dump_json(),
                ),
            )
        return correction

    def find_corrections(
        self, listing_id: str | None = None, in_force: bool = True
    ) -> list[FieldCorrection]:
        sql, params = _filtered(
            "SELECT doc FROM corrections",
            {"listing_id": listing_id, "in_force": 1 if in_force else None},
        )
        return self._all(FieldCorrection, sql + " ORDER BY rowid", params)

    def save_correction(
        self, record: FieldCorrection, *, expected: FieldCorrection
    ) -> FieldCorrection:
        if (record.correction_id, record.listing_id, record.field) != (
            expected.correction_id,
            expected.listing_id,
            expected.field,
        ):
            raise ValueError("a correction's id, post and field never change")
        if not expected.in_force and record.in_force:
            raise ValueError("a removed correction is not put back in force (#284)")
        with self._transaction() as conn:
            _require_expected(
                conn,
                FieldCorrection,
                "SELECT doc FROM corrections WHERE correction_id = ?",
                record.correction_id,
                expected,
            )
            conn.execute(
                "UPDATE corrections SET in_force = ?, doc = ? WHERE correction_id = ?",
                (int(record.in_force), record.model_dump_json(), record.correction_id),
            )
        return record

    # --- Gate F: Telegram (#453) ---

    def add_link_code(self, code: TelegramLinkCode) -> TelegramLinkCode:
        if code.used_at is not None:
            raise ValueError("a new code is unused")
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO telegram_link_codes (code_hash, user_id, doc) VALUES (?, ?, ?)",
                (code.code_hash, code.user_id, code.model_dump_json()),
            )
        return code

    def link_telegram(self, code_hash: str, chat_id: int, now: datetime) -> User:
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT doc FROM telegram_link_codes WHERE code_hash = ?", (code_hash,)
            ).fetchone()
            code = None if row is None else TelegramLinkCode.model_validate_json(row[0])
            if code is None or not code.usable(now):
                raise LinkCodeNotUsable("no usable code with that hash")
            users = [User.from_stored_json(doc) for (doc,) in conn.execute("SELECT doc FROM users")]
            user = next((u for u in users if u.user_id == code.user_id), None)
            if user is None or user.disabled_at is not None:
                raise LinkCodeNotUsable("the code's user cannot be linked")
            if any(u.telegram_chat_id == chat_id and u.user_id != user.user_id for u in users):
                raise ChatLinkedElsewhere("the chat is linked to another user")
            if user.telegram_chat_id != chat_id:
                user = User.model_validate(
                    {**user.model_dump(), "telegram_chat_id": chat_id, "telegram_linked_at": now}
                )
                conn.execute(
                    "UPDATE users SET doc = ? WHERE user_id = ?",
                    (user.model_dump_json(), user.user_id),
                )
            used = TelegramLinkCode.model_validate({**code.model_dump(), "used_at": now})
            conn.execute(
                "UPDATE telegram_link_codes SET doc = ? WHERE code_hash = ?",
                (used.model_dump_json(), code_hash),
            )
        return user

    def find_user_by_chat(self, chat_id: int) -> User | None:
        return next((u for u in self.list_users() if u.telegram_chat_id == chat_id), None)

    def add_sent_alert(self, alert: SentAlert) -> bool:
        with self._transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO sent_alerts (user_id, listing_id, doc) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, listing_id) DO NOTHING",
                (alert.user_id, alert.listing_id, alert.model_dump_json()),
            )
            return cursor.rowcount == 1

    def sent_listing_ids(self, user_id: str) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT listing_id FROM sent_alerts WHERE user_id = ?", (user_id,)
            ).fetchall()
        return {listing_id for (listing_id,) in rows}

    # --- plumbing ---

    def _get[M: BaseModel](self, model: type[M], sql: str, params: tuple[object, ...]) -> M | None:
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return None if row is None else _read(model, row[0])

    def _all[M: BaseModel](
        self, model: type[M], sql: str, params: tuple[object, ...] = ()
    ) -> list[M]:
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_read(model, doc) for (doc,) in rows]

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, autocommit=True, timeout=BUSY_TIMEOUT_SECONDS)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")


def _require_profile_of(user: User, profile: Profile) -> None:
    if profile.user_id != user.user_id:
        raise ValueError("the profile belongs to another user")


def _insert_user(conn: sqlite3.Connection, user: User) -> None:
    taken = conn.execute(
        "SELECT 1 FROM users WHERE username_lower = ?", (user.username_key,)
    ).fetchone()
    if taken is not None:
        raise UsernameTaken(f"the username {user.username!r} is taken")
    conn.execute(
        "INSERT INTO users (user_id, username_lower, doc) VALUES (?, ?, ?)",
        (user.user_id, user.username_key, user.model_dump_json()),
    )


def _put(
    conn: sqlite3.Connection,
    table: str,
    keys: tuple[str, ...],
    values: tuple[str, ...],
    record: BaseModel,
) -> None:
    columns = ", ".join(keys)
    marks = ", ".join("?" for _ in keys)
    conn.execute(
        f"INSERT INTO {table} ({columns}, doc) VALUES ({marks}, ?) "
        f"ON CONFLICT ({columns}) DO UPDATE SET doc = excluded.doc",
        (*values, record.model_dump_json()),
    )


def _require_expected[M: BaseModel](
    conn: sqlite3.Connection, model: type[M], sql: str, record_id: str, expected: M
) -> None:
    """Compare and set inside the write's transaction, as for `PostLifecycle` (#289)."""
    row = conn.execute(sql, (record_id,)).fetchone()
    if row is None or _read(model, row[0]) != expected:
        raise StaleRecordError(record_id)


def _read[M: BaseModel](model: type[M], doc: str) -> M:
    """A stored document; a `User` through `User.from_stored_json` (a version-1 one reads as 2)."""
    if model is User:
        return User.from_stored_json(doc)  # type: ignore[return-value]
    return model.model_validate_json(doc)


def _end(conn: sqlite3.Connection, session: Session, now: datetime) -> bool:
    if session.ended_at is not None:
        return False
    ended = session.model_copy(update={"ended_at": now})
    Session.model_validate(ended.model_dump())
    conn.execute(
        "UPDATE sessions SET doc = ? WHERE token_hash = ?",
        (ended.model_dump_json(), session.token_hash),
    )
    return True


def _filtered(sql: str, conditions: dict[str, object]) -> tuple[str, tuple[object, ...]]:
    used = {column: value for column, value in conditions.items() if value is not None}
    if not used:
        return sql, ()
    where = " AND ".join(f"{column} = ?" for column in used)
    return f"{sql} WHERE {where}", tuple(used.values())
