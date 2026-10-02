from tlv_hunter.contracts.decision_stub import DecisionStub
from tlv_hunter.contracts.listing_stub import ListingStub


class AlwaysNotifyPolicyStub:
    def __init__(self, user_id: str) -> None:
        self._user_id = user_id

    def decide(self, listing: ListingStub) -> DecisionStub:
        return DecisionStub(user_id=self._user_id, listing_id=listing.listing_id, notify=True)
