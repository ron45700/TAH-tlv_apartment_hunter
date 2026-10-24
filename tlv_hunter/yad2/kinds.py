"""Yad2's 22 property kinds (`PHASE_6.md` §6.3.1; DECISIONS.md #501, and #495 where they meet): the
rent search's own options (`base-search-options`), with what each kind decides for `post_nature`
and `apartment_kind`. `None` means the model decides. A kind whose `post_nature` is `not_listing`
is rejected before the model, with no call (point 11).

Read from `d.additionalDetails.property.id`. A kind not in the table (Yad2 added one) decides
nothing: the model decides both, as for `כללי`.
"""

from dataclasses import dataclass
from typing import Literal

PostNature = Literal["rental_offer", "sublet_offer", "seeking", "for_sale", "not_listing"]
ApartmentKind = Literal["room", "whole_apartment"]

APARTMENTS = "דירות"
HOUSES = "בתים"
PROPERTIES = "נכסים"


@dataclass(frozen=True)
class Kind:
    title: str
    group: str
    post_nature: PostNature | None
    apartment_kind: ApartmentKind | None

    @property
    def rejected_before_model(self) -> bool:
        return self.post_nature == "not_listing"


KINDS: dict[int, Kind] = {
    1: Kind("דירה", APARTMENTS, None, None),
    3: Kind("דירת גן", APARTMENTS, None, None),
    6: Kind("גג/ פנטהאוז", APARTMENTS, None, None),
    7: Kind("דופלקס", APARTMENTS, None, None),
    51: Kind("טריפלקס", APARTMENTS, None, None),
    49: Kind("מרתף/ פרטר", APARTMENTS, None, None),
    4: Kind("סטודיו/ לופט", APARTMENTS, None, "whole_apartment"),  # a studio is one (#94)
    11: Kind("יחידת דיור", APARTMENTS, None, "whole_apartment"),  # #501
    43: Kind("סאבלט", APARTMENTS, "sublet_offer", None),  # #501
    31: Kind("החלפת דירות", APARTMENTS, "not_listing", None),  # #501
    25: Kind("תיירות ונופש", APARTMENTS, "not_listing", None),
    5: Kind("בית פרטי/ קוטג'", HOUSES, None, None),
    39: Kind("דו משפחתי", HOUSES, None, None),
    32: Kind("משק חקלאי/ נחלה", HOUSES, "not_listing", None),
    55: Kind("משק עזר", HOUSES, "not_listing", None),
    30: Kind("חניה", PROPERTIES, "not_listing", None),  # #501
    45: Kind("מחסן", PROPERTIES, "not_listing", None),  # #501
    33: Kind("מגרשים", PROPERTIES, "not_listing", None),
    44: Kind("בניין מגורים", PROPERTIES, "not_listing", None),
    61: Kind("דיור מוגן", PROPERTIES, "not_listing", None),
    50: Kind("קב' רכישה/ זכות לנכס", PROPERTIES, "not_listing", None),
    41: Kind("כללי", PROPERTIES, None, None),
}

_UNKNOWN = Kind("", "", None, None)


def kind_ruling(kind_id: int | None) -> Kind:
    """The kind's row; an unknown or missing kind decides nothing."""
    return KINDS.get(kind_id, _UNKNOWN) if kind_id is not None else _UNKNOWN
