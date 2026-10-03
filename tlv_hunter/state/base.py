from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.group_watermark import GroupWatermark


@runtime_checkable
class WatermarkStore(Protocol):
    def get(self, group_id: str) -> GroupWatermark | None: ...

    def get_all(self) -> list[GroupWatermark]: ...

    def save_all(self, records: Sequence[GroupWatermark]) -> None:
        """Writes every record in one transaction: all of them or none."""
        ...
