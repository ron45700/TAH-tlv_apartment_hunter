from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.raw_post import RawPost


@runtime_checkable
class Provider(Protocol):
    def fetch(self, group_ids: Sequence[str], since: datetime) -> list[RawPost]: ...
