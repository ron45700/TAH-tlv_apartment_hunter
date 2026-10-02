from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.decision_stub import DecisionStub
from tlv_hunter.contracts.listing_stub import ListingStub


@runtime_checkable
class Policy(Protocol):
    def decide(self, listing: ListingStub) -> DecisionStub: ...
