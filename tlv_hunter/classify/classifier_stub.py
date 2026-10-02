from tlv_hunter.contracts.listing_stub import ListingStub
from tlv_hunter.contracts.raw_post import RawPost


class ClassifierStub:
    def classify(self, post: RawPost) -> ListingStub:
        return ListingStub(listing_id=post.listing_id)
