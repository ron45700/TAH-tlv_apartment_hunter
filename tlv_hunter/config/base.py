from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CollectionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: Literal["thedoor", "memo23"]
    group_ids: list[str] = Field(min_length=1)
    group_names: dict[str, str] = Field(default_factory=dict)
    """Each group's Hebrew name, by id, for what Ron reads (the digest, the failure alert); a
    group with no name is shown by its id (`group_name`)."""
    max_posts: int = Field(gt=0)
    sorting_order: Literal["newest_posts"]
    fetch_all_comments: Literal[False]
    include_top_comment: Literal[False]
    max_total_charge_usd: float = Field(gt=0)
    run_timeout_secs: int = Field(gt=0)
    store_root: str

    @model_validator(mode="after")
    def _names_of_configured_groups(self) -> Self:
        unknown = sorted(set(self.group_names) - set(self.group_ids))
        if unknown:
            raise ValueError(f"group_names names groups not in group_ids: {unknown}")
        if any(not name.strip() for name in self.group_names.values()):
            raise ValueError("a group name is blank")
        return self

    def group_name(self, group_id: str) -> str:
        return self.group_names.get(group_id, group_id)


@runtime_checkable
class ConfigSource(Protocol):
    """Collection settings only. User profiles are not config: they live in the store
    (DECISIONS.md #47; `userdata/`, #267)."""

    def collection(self) -> CollectionConfig: ...
