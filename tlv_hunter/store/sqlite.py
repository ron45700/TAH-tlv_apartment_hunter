import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.textnorm.phones import canonical_phone

# The JSON functions and operators built in by default, used by
# find_lifecycles_with_image_errors: 3.38.0, read on sqlite.org/json1.html on 2026-10-04
# (DECISIONS.md #80). It covers UPSERT with a conflict target, 3.24.0 (#65).
MIN_SQLITE_VERSION = (3, 38, 0)
LAYOUT_MODULE = "store"
LAYOUT_VERSION = 1
# The listings table has its own layout row, created when absent, so a store at layout 1 opens
# unchanged and needs no migration (DECISIONS.md #65; task 2.2, option C).
LISTINGS_LAYOUT_MODULE = "store.listings"
LISTINGS_LAYOUT_VERSION = 1

_CREATE_LAYOUT_VERSION = (
    "CREATE TABLE IF NOT EXISTS layout_version (module TEXT PRIMARY KEY, version INTEGER NOT NULL)"
)
_CREATE_TABLES = (
    "CREATE TABLE raw_posts (listing_id TEXT PRIMARY KEY, text_hash TEXT, doc TEXT NOT NULL)",
    "CREATE INDEX raw_posts_text_hash ON raw_posts (text_hash)",
    "CREATE TABLE post_lifecycle ("
    "listing_id TEXT PRIMARY KEY REFERENCES raw_posts (listing_id), doc TEXT NOT NULL)",
)
_CREATE_LISTINGS_TABLES = (
    "CREATE TABLE listings ("
    "listing_id TEXT PRIMARY KEY REFERENCES raw_posts (listing_id), doc TEXT NOT NULL)",
)


class SqliteRepository:
    """Repository over one SQLite file: a JSON document per record, plus lookup columns only.

    Datetimes live inside the documents, serialized and validated by the pydantic models; none is
    passed to sqlite3 as a parameter. One connection per operation.

    `read_only=True` opens an existing file with SQLite's read-only mode, for the local pages of
    tasks 2.6 and 2.7: it creates nothing, adds no layout row, and every write raises
    `sqlite3.OperationalError`. A missing file raises instead of being created.
    """

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
            raise RuntimeError(
                f"SQLite {sqlite3.sqlite_version} is too old; module {LAYOUT_MODULE!r} needs "
                f"{'.'.join(map(str, MIN_SQLITE_VERSION))} or later"
            )
        self._path = Path(path)
        self._read_only = read_only
        self._has_listings = True
        if read_only:
            with self._connect() as conn:
                self._check_layout(conn, LAYOUT_MODULE, LAYOUT_VERSION, required=True)
                # A store no writer has opened since task 2.2 has no listings table yet.
                self._has_listings = self._check_layout(
                    conn, LISTINGS_LAYOUT_MODULE, LISTINGS_LAYOUT_VERSION, required=False
                )
            return
        with self._transaction() as conn:
            conn.execute(_CREATE_LAYOUT_VERSION)
            self._ensure_layout(conn, LAYOUT_MODULE, LAYOUT_VERSION, _CREATE_TABLES)
            self._ensure_layout(
                conn, LISTINGS_LAYOUT_MODULE, LISTINGS_LAYOUT_VERSION, _CREATE_LISTINGS_TABLES
            )

    def _ensure_layout(
        self,
        conn: sqlite3.Connection,
        module: str,
        version: int,
        statements: tuple[str, ...],
    ) -> None:
        """Create the tables of a layout row that is absent; refuse a version mismatch."""
        if not self._check_layout(conn, module, version, required=False):
            for statement in statements:
                conn.execute(statement)
            conn.execute(
                "INSERT INTO layout_version (module, version) VALUES (?, ?)", (module, version)
            )

    def _check_layout(
        self, conn: sqlite3.Connection, module: str, version: int, *, required: bool
    ) -> bool:
        """Whether the layout row exists; a version mismatch, or a required row absent, raises."""
        row = conn.execute(
            "SELECT version FROM layout_version WHERE module = ?", (module,)
        ).fetchone()
        if row is None:
            if required:
                raise RuntimeError(f"{self._path}: no layout row for module {module!r}")
            return False
        if row[0] != version:
            raise RuntimeError(
                f"{self._path}: module {module!r} expects layout version "
                f"{version}, found {row[0]}; no automatic migration"
            )
        return True

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
        return None if row is None else PostLifecycle.from_stored_json(row[0])

    def find_without_lifecycle(self) -> list[RawPost]:
        return self._select_posts(
            "SELECT p.doc FROM raw_posts p "
            "LEFT JOIN post_lifecycle l ON l.listing_id = p.listing_id "
            "WHERE l.listing_id IS NULL ORDER BY p.listing_id"
        )

    def find_lifecycles_with_image_errors(self, prefixes: Sequence[str]) -> list[PostLifecycle]:
        if not prefixes:
            return []
        wanted = ", ".join("(?)" for _ in prefixes)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT l.doc FROM post_lifecycle l WHERE EXISTS ("
                "SELECT 1 FROM json_each(l.doc, '$.images') AS image, "
                f"(VALUES {wanted}) AS wanted "
                "WHERE substr(image.value ->> '$.error', 1, length(wanted.column1)) "
                "= wanted.column1) ORDER BY l.listing_id",
                tuple(prefixes),
            ).fetchall()
        return [PostLifecycle.from_stored_json(doc) for (doc,) in rows]

    def save_classification(self, listing: Listing, lifecycle: PostLifecycle) -> None:
        if listing.listing_id != lifecycle.listing_id:
            raise ValueError(
                f"listing {listing.listing_id} and lifecycle record {lifecycle.listing_id} "
                "belong to different posts"
            )
        with self._transaction() as conn:
            exists = conn.execute(
                "SELECT 1 FROM raw_posts WHERE listing_id = ?", (listing.listing_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(listing.listing_id)
            conn.execute(
                "INSERT INTO listings (listing_id, doc) VALUES (?, ?) "
                "ON CONFLICT (listing_id) DO UPDATE SET doc = excluded.doc",
                (listing.listing_id, listing.model_dump_json()),
            )
            conn.execute(
                "INSERT INTO post_lifecycle (listing_id, doc) VALUES (?, ?) "
                "ON CONFLICT (listing_id) DO UPDATE SET doc = excluded.doc",
                (lifecycle.listing_id, lifecycle.model_dump_json()),
            )

    def get_listing(self, listing_id: str) -> Listing | None:
        if not self._has_listings:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT doc FROM listings WHERE listing_id = ?", (listing_id,)
            ).fetchone()
        return None if row is None else Listing.model_validate_json(row[0])

    def find_pending_canonicals(self) -> list[RawPost]:
        return self._select_posts(
            "SELECT p.doc FROM raw_posts p JOIN post_lifecycle l ON l.listing_id = p.listing_id "
            "WHERE l.doc ->> '$.state' = 'pending' AND p.doc ->> '$.is_canonical' = 1 "
            "ORDER BY p.listing_id"
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
        if self._read_only:
            # mode=ro never creates the file; the URI form is the only way to pass it.
            target = f"{self._path.resolve().as_uri()}?mode=ro"
            conn = sqlite3.connect(target, uri=True, autocommit=True)
        else:
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
