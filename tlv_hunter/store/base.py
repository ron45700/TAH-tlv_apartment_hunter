from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.raw_post import RawPost


@runtime_checkable
class Repository(Protocol):
    def upsert(self, post: RawPost) -> RawPost: ...

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]: ...

    def find_by_phone(self, phone: str) -> list[RawPost]: ...

    def query(self) -> list[RawPost]: ...
