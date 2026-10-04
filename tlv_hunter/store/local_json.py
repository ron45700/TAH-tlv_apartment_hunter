import json
import os
import uuid
from pathlib import Path

from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.textnorm.phones import canonical_phone

RAW_POSTS_COLLECTION = "raw_posts"
POST_LIFECYCLE_COLLECTION = "post_lifecycle"


class LocalJsonRepository:
    """One JSON file per record at <root>/<collection>/<listing_id>.json. No index.

    For tests only. Each file write is atomic, but a write spanning two files is not:
    `upsert_with_lifecycle` writes the post, then the lifecycle record, and a crash between the
    two leaves a post with no record. `find_without_lifecycle` finds such posts.
    """

    def __init__(self, root: Path) -> None:
        self._posts_dir = Path(root) / RAW_POSTS_COLLECTION
        self._lifecycle_dir = Path(root) / POST_LIFECYCLE_COLLECTION

    def upsert(self, post: RawPost) -> RawPost:
        path = self._post_path(post.listing_id)
        if path.exists():
            post = post.with_changes(fetched_at=_read(path).fetched_at)
        self._posts_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, json.dumps(post.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return post

    def get(self, listing_id: str) -> RawPost | None:
        path = self._post_path(listing_id)
        return _read(path) if path.exists() else None

    def upsert_with_lifecycle(self, post: RawPost, initial: PostLifecycle) -> RawPost:
        _require_same_post(post, initial)
        stored = self.upsert(post)
        if not self._lifecycle_path(post.listing_id).exists():
            self._write_lifecycle(initial)
        return stored

    def save_lifecycle(self, record: PostLifecycle) -> PostLifecycle:
        if not self._post_path(record.listing_id).exists():
            raise KeyError(record.listing_id)
        self._write_lifecycle(record)
        return record

    def get_lifecycle(self, listing_id: str) -> PostLifecycle | None:
        path = self._lifecycle_path(listing_id)
        if not path.exists():
            return None
        return PostLifecycle.model_validate_json(path.read_text(encoding="utf-8"))

    def find_without_lifecycle(self) -> list[RawPost]:
        return [post for post in self.query() if not self._lifecycle_path(post.listing_id).exists()]

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]:
        if text_hash is None:
            return []
        return [post for post in self.query() if post.text_hash == text_hash]

    def find_by_phone(self, phone: str) -> list[RawPost]:
        wanted = canonical_phone(phone)
        return [post for post in self.query() if post.phones and wanted in post.phones]

    def query(self) -> list[RawPost]:
        if not self._posts_dir.is_dir():
            return []
        return [_read(path) for path in sorted(self._posts_dir.glob("*.json"))]

    def _post_path(self, listing_id: str) -> Path:
        return self._posts_dir / f"{listing_id}.json"

    def _lifecycle_path(self, listing_id: str) -> Path:
        return self._lifecycle_dir / f"{listing_id}.json"

    def _write_lifecycle(self, record: PostLifecycle) -> None:
        self._lifecycle_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            self._lifecycle_path(record.listing_id),
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )


def _require_same_post(post: RawPost, initial: PostLifecycle) -> None:
    if initial.listing_id != post.listing_id:
        raise ValueError(
            f"lifecycle record {initial.listing_id} does not belong to post {post.listing_id}"
        )


def _read(path: Path) -> RawPost:
    return RawPost.model_validate_json(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
