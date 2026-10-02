from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.decision_stub import DecisionStub
from tlv_hunter.contracts.listing_stub import ListingStub


@runtime_checkable
class Notifier(Protocol):
    def send(self, listing: ListingStub, decision: DecisionStub) -> None: ...
