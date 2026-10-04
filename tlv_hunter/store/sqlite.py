import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.textnorm.phones import canonical_phone

# UPSERT with a conflict target (INSERT ... ON CONFLICT(col) DO UPDATE / DO NOTHING), 3.24.0.
MIN_SQLITE_VERSION = (3, 24, 0)
LAYOUT_MODULE = "store"
LAYOUT_VERSION = 1

_CREATE_LAYOUT_VERSION = (
    "CREATE TABLE IF NOT EXISTS layout_version (module TEXT PRIMARY KEY, version INTEGER NOT NULL)"
)
_CREATE_TABLES = (
    "CREATE TABLE raw_posts (listing_id TEXT PRIMARY KEY, text_hash TEXT, doc TEXT NOT NULL)",
    "CREATE INDEX raw_posts_text_hash ON raw_posts (text_hash)",
    "CREATE TABLE post_lifecycle ("
    "listing_id TEXT PRIMARY KEY REFERENCES raw_posts (listing_id), doc TEXT NOT NULL)",
)


class SqliteRepository:
    """Repository over one SQLite file: a JSON document per record, plus lookup columns only.

    Datetimes live inside the documents, serialized and validated by the pydantic models; none is
    passed to sqlite3 as a parameter. One connection per operation.
    """

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
                for statement in _CREATE_TABLES:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO layout_version (module, version) VALUES (?, ?)",
                    (LAYOUT_MODULE, LAYOUT_VERSION),
                )
            elif row[0] != LAYOUT_VERSION:
                raise RuntimeError(
                    f"{self._path}: module {LAYOUT_MODULE!r} expects layout version "
                    f"{LAYOUT_VERSION}, found {row[0]}; no automatic migration"
                )

    def upsert(self, post: RawPost) -> RawPost:
        with self._transaction() as conn:
            return _upsert(conn, post)

    def get(self, listing_id: str) -> RawPost | None:
        posts = self._select_posts("SELECT doc FROM raw_posts WHERE listing_id = ?", (listing_id,))
        return posts[0] if posts else None

    def upsert_with_lifecycle(self, post: RawPost, initial: PostLifecycle) -> RawPost:
        if initial.listing_id != post.listing_id:
            raise ValueError(
                f"lifecycle record {initial.listing_id} does not belong to post {post.listing_id}"
            )
        with self._transaction() as conn:
            stored = _upsert(conn, post)
            conn.execute(
                "INSERT INTO post_lifecycle (listing_id, doc) VALUES (?, ?) "
                "ON CONFLICT (listing_id) DO NOTHING",
                (initial.listing_id, initial.model_dump_json()),
            )
            return stored

    def save_lifecycle(self, record: PostLifecycle) -> PostLifecycle:
        with self._transaction() as conn:
            exists = conn.execute(
                "SELECT 1 FROM raw_posts WHERE listing_id = ?", (record.listing_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(record.listing_id)
            conn.execute(
                "INSERT INTO post_lifecycle (listing_id, doc) VALUES (?, ?) "
                "ON CONFLICT (listing_id) DO UPDATE SET doc = excluded.doc",
                (record.listing_id, record.model_dump_json()),
            )
        return record

    def get_lifecycle(self, listing_id: str) -> PostLifecycle | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT doc FROM post_lifecycle WHERE listing_id = ?", (listing_id,)
            ).fetchone()
        return None if row is None else PostLifecycle.model_validate_json(row[0])

    def find_without_lifecycle(self) -> list[RawPost]:
        return self._select_posts(
            "SELECT p.doc FROM raw_posts p "
            "LEFT JOIN post_lifecycle l ON l.listing_id = p.listing_id "
            "WHERE l.listing_id IS NULL ORDER BY p.listing_id"
        )

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]:
        if text_hash is None:
            return []
        return self._select_posts(
            "SELECT doc FROM raw_posts WHERE text_hash = ? ORDER BY listing_id", (text_hash,)
        )

    def find_by_phone(self, phone: str) -> list[RawPost]:
        wanted = canonical_phone(phone)
        return [post for post in self.query() if post.phones and wanted in post.phones]

    def query(self) -> list[RawPost]:
        return self._select_posts("SELECT doc FROM raw_posts ORDER BY listing_id")

    def _select_posts(self, sql: str, params: tuple[str, ...] = ()) -> list[RawPost]:
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [RawPost.model_validate_json(doc) for (doc,) in rows]

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, autocommit=True)
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


def _upsert(conn: sqlite3.Connection, post: RawPost) -> RawPost:
    row = conn.execute(
        "SELECT doc FROM raw_posts WHERE listing_id = ?", (post.listing_id,)
    ).fetchone()
    if row is not None:
        post = post.with_changes(fetched_at=RawPost.model_validate_json(row[0]).fetched_at)
    conn.execute(
        "INSERT INTO raw_posts (listing_id, text_hash, doc) VALUES (?, ?, ?) "
        "ON CONFLICT (listing_id) DO UPDATE SET text_hash = excluded.text_hash, doc = excluded.doc",
        (post.listing_id, post.text_hash, post.model_dump_json()),
    )
    return post
