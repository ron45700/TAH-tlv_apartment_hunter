from pydantic import BaseModel, ConfigDict


class DecisionStub(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    user_id: str
    listing_id: str
    notify: bool
