from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost


class StaleRecordError(RuntimeError):
    """The stored record is not the one the writer read: another writer came between the read
    and the write. Nothing was written (DECISIONS.md #260, #289). Raised for a `PostLifecycle`,
    and by `userdata/` for its records (#289: compare and set "as for PostLifecycle")."""

    def __init__(self, record_id: str) -> None:
        super().__init__(f"{record_id}: the stored record changed since it was read")
        self.record_id = record_id
        self.listing_id = record_id  # the post's, for a PostLifecycle


@runtime_checkable
class Repository(Protocol):
    def upsert(self, post: RawPost) -> RawPost: ...

    def get(self, listing_id: str) -> RawPost | None: ...

    def upsert_with_lifecycle(self, post: RawPost, initial: PostLifecycle) -> RawPost:
        """Upsert the post; store `initial` only if the post has no lifecycle record yet."""
        ...

    def save_lifecycle(
        self, record: PostLifecycle, *, expected: PostLifecycle | None
    ) -> PostLifecycle:
        """Compare and set (DECISIONS.md #260): a whole-record replace, written only if the stored
        record, read through `PostLifecycle.from_stored_json`, equals `expected`, the record the
        writer read; `expected=None` writes only if the post has no record yet. Otherwise raises
        `StaleRecordError` and writes nothing. KeyError if the post is not stored."""
        ...

    def get_lifecycle(self, listing_id: str) -> PostLifecycle | None: ...

    def find_without_lifecycle(self) -> list[RawPost]: ...

    def find_lifecycles_with_image_errors(self, prefixes: Sequence[str]) -> list[PostLifecycle]:
        """The records with at least one image entry whose `error` starts with one of `prefixes`,
        ordered by listing_id. Which errors to ask for is the caller's rule (DECISIONS.md #80)."""
        ...

    def save_classification(
        self, listing: Listing, lifecycle: PostLifecycle, *, expected: PostLifecycle | None
    ) -> None:
        """Write the Listing and the post's lifecycle record together (DECISIONS.md #131). Replaces
        an earlier Listing; the lifecycle record is written by compare and set against `expected`,
        as in `save_lifecycle`, and on a stale record neither is written (#260). KeyError if the
        post is not stored, ValueError if the two belong to different posts. Never writes the
        RawPost (invariant 14)."""
        ...

    def get_listing(self, listing_id: str) -> Listing | None: ...

    def find_pending_canonicals(self) -> list[RawPost]:
        """The canonical posts whose lifecycle state is "pending", ordered by listing_id (#75 B)."""
        ...

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]: ...

    def find_by_phone(self, phone: str) -> list[RawPost]: ...

    def query(self) -> list[RawPost]: ...
