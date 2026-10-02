from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.listing_stub import ListingStub
from tlv_hunter.contracts.raw_post import RawPost


@runtime_checkable
class Classifier(Protocol):
    def classify(self, post: RawPost) -> ListingStub: ...
