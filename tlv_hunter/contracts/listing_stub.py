from pydantic import BaseModel, ConfigDict


class ListingStub(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    listing_id: str
