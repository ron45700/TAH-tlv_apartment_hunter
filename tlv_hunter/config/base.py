from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class CollectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: Literal["thedoor", "memo23"]
    group_ids: list[str] = Field(min_length=1)
    max_posts: int = Field(gt=0)
    sorting_order: Literal["newest_posts"]
    fetch_all_comments: Literal[False]
    store_root: str


class UserConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    user_id: str
    subscribed_group_ids: list[str]


@runtime_checkable
class ConfigSource(Protocol):
    def collection(self) -> CollectionConfig: ...

    def user(self, user_id: str) -> UserConfig: ...
