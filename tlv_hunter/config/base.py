from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class CollectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: Literal["thedoor", "memo23"]
    group_ids: list[str] = Field(min_length=1)
    max_posts: int = Field(gt=0)
    sorting_order: Literal["newest_posts"]
    fetch_all_comments: Literal[False]
    include_top_comment: Literal[False]
    max_total_charge_usd: float = Field(gt=0)
    run_timeout_secs: int = Field(gt=0)
    store_root: str


@runtime_checkable
class ConfigSource(Protocol):
    """Collection settings only. User profiles are not config: they live in the store
    (DECISIONS.md #47; `userdata/`, #267)."""

    def collection(self) -> CollectionConfig: ...
