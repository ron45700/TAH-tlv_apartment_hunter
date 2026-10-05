from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost


@runtime_checkable
class Repository(Protocol):
    def upsert(self, post: RawPost) -> RawPost: ...

    def get(self, listing_id: str) -> RawPost | None: ...

    def upsert_with_lifecycle(self, post: RawPost, initial: PostLifecycle) -> RawPost:
        """Upsert the post; store `initial` only if the post has no lifecycle record yet."""
        ...

    def save_lifecycle(self, record: PostLifecycle) -> PostLifecycle:
        """Whole-record replace, last write wins. KeyError if the post is not stored."""
        ...

    def get_lifecycle(self, listing_id: str) -> PostLifecycle | None: ...

    def find_without_lifecycle(self) -> list[RawPost]: ...

    def find_lifecycles_with_image_errors(self, prefixes: Sequence[str]) -> list[PostLifecycle]:
        """The records with at least one image entry whose `error` starts with one of `prefixes`,
        ordered by listing_id. Which errors to ask for is the caller's rule (DECISIONS.md #80)."""
        ...

    def save_classification(self, listing: Listing, lifecycle: PostLifecycle) -> None:
        """Write the Listing and the post's lifecycle record together (DECISIONS.md #131). Replaces
        an earlier Listing; the lifecycle record is a whole-record replace. KeyError if the post is
        not stored, ValueError if the two belong to different posts. Never writes the RawPost
        (invariant 14)."""
        ...

    def get_listing(self, listing_id: str) -> Listing | None: ...

    def find_pending_canonicals(self) -> list[RawPost]:
        """The canonical posts whose lifecycle state is "pending", ordered by listing_id (#75 B)."""
        ...

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]: ...

    def find_by_phone(self, phone: str) -> list[RawPost]: ...

    def query(self) -> list[RawPost]: ...
