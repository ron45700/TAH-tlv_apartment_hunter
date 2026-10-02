from tlv_hunter.contracts.decision_stub import DecisionStub
from tlv_hunter.contracts.listing_stub import ListingStub


class RecordingNotifierStub:
    def __init__(self) -> None:
        self.sent: list[tuple[ListingStub, DecisionStub]] = []

    def send(self, listing: ListingStub, decision: DecisionStub) -> None:
        self.sent.append((listing, decision))
