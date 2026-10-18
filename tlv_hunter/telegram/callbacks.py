"""The data the alert's report buttons carry (`PHASE_4.md` point 11 A; DECISIONS.md #364, #452).

`callback_data` is 1-64 bytes, and a `listing_id` is 64 hex characters, so a button carries a
short reference: the first 16 hex characters of the post's `listing_id`, resolved by the bot
against the posts of the current cards; a reference that matches none, or more than one, is
refused. Pure: text in, text out.

    r:<ref>                the "report" button: opens the two choices
    l:<ref>                "lied": asks to confirm
    L:<ref>                "lied", confirmed: the flag is written
    w:<ref>:<mask>         "wrong classification": the fields as toggles, `mask` the ones chosen
    t:<ref>:<mask>:<i>     toggle field number `i`
    s:<ref>:<mask>         send the chosen fields: then the optional note
    k:<ref>:<mask>         skip the note: the report is written
    b:<ref>                back to the alert's own buttons

The fields' numbers are their order in `ReportableField`, the mask a hex bit set over them.
"""

import re
from dataclasses import dataclass
from typing import Literal, get_args

from tlv_hunter.contracts.classification_report import ReportableField

REF_LENGTH = 16
FIELDS: tuple[ReportableField, ...] = get_args(ReportableField)
Action = Literal["r", "l", "L", "w", "t", "s", "k", "b"]
_FORM = re.compile(
    r"(?P<action>[rlLwtskb]):(?P<ref>[0-9a-f]{16})(?::(?P<mask>[0-9a-f]{1,6}))?(?::(?P<i>\d{1,2}))?"
)
_WITH_MASK = {"w", "t", "s", "k"}


@dataclass(frozen=True)
class Callback:
    action: Action
    ref: str
    mask: int = 0
    index: int | None = None

    def data(self) -> str:
        if self.action == "t":
            return f"t:{self.ref}:{self.mask:x}:{self.index}"
        if self.action in _WITH_MASK:
            return f"{self.action}:{self.ref}:{self.mask:x}"
        return f"{self.action}:{self.ref}"

    @property
    def fields(self) -> tuple[ReportableField, ...]:
        return tuple(name for i, name in enumerate(FIELDS) if self.mask >> i & 1)


def ref_of(listing_id: str) -> str:
    return listing_id[:REF_LENGTH]


def parse(data: str) -> Callback | None:
    """The callback, or `None` for data this bot never sent."""
    found = _FORM.fullmatch(data)
    if found is None:
        return None
    action = found["action"]
    has_mask = found["mask"] is not None
    if has_mask != (action in _WITH_MASK) or (found["i"] is not None) != (action == "t"):
        return None
    mask = int(found["mask"], 16) if has_mask else 0
    if mask >> len(FIELDS):
        return None
    index = int(found["i"]) if found["i"] is not None else None
    if index is not None and index >= len(FIELDS):
        return None
    return Callback(action, found["ref"], mask, index)  # type: ignore[arg-type]


def toggled(callback: Callback) -> int:
    """The mask with field `index` switched."""
    assert callback.index is not None
    return callback.mask ^ (1 << callback.index)
