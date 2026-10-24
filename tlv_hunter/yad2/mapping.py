"""A Yad2 listing page's `data` to a `RawPost` (Gate A for Yad2, `PHASE_6.md` §6.2; DECISIONS.md
#494, #496) and to the form's part of a `Listing` (Gate B for Yad2, §6.3; #495, #501). Pure: no
store, no network, no model.

`d` is the page's `data` (`pages.listing_data`), stored whole as `raw`. `updatedAt` is Israel local
time with no zone: converted by the one datetime module (invariant 9). The description is the text,
verbatim (invariants 8, 14). The phone is never read: the page holds none, and Yad2's phone
response is never fetched (#497).

**Media are not mapped yet** (`PHASE_6.md` §6.2, the contradiction for Ron): Gate A's `Media` has
`media_id` and `page_url` as `str`, the photo download keys on `media_id`, and the approved table
gives Yad2 `None` for both. Until Ron decides, `media` is `[]`; the photos stay in `raw`
(`photo_urls` reads them).
"""

import copy
from datetime import datetime
from typing import Any

from tlv_hunter.contracts.raw_post import RAW_POST_SCHEMA_VERSION, RawPost
from tlv_hunter.parsing.datetimes import parse_israel_local_utc, parse_local_date
from tlv_hunter.parsing.ids import YAD2_SOURCE, compute_listing_id
from tlv_hunter.textnorm.blank import is_blank
from tlv_hunter.yad2.kinds import kind_ruling

GROUP_ID = "yad2-tel-aviv"
GROUP_TITLE = "יד2 · תל אביב-יפו"
POST_TYPE = "yad2_listing"
CURRENCY = "ILS"
PERMALINK = "https://www.yad2.co.il/realestate/item/tel-aviv-area/{token}"
_BROKER_BY_AD_TYPE = {"commercial": True, "private": False}


def to_raw_post(d: dict[str, Any], fetched_at: datetime) -> RawPost:
    token = d["token"]
    description = _get(d, "metaData", "description")
    text = description if isinstance(description, str) else ""
    price = d.get("price")
    native_price = price if _positive_int(price) else None
    customer_id = _get(d, "customer", "id")
    return RawPost(
        schema_version=RAW_POST_SCHEMA_VERSION,
        source=YAD2_SOURCE,
        source_post_id=token,
        listing_id=compute_listing_id(token, source=YAD2_SOURCE),
        group_id=GROUP_ID,
        group_title=GROUP_TITLE,
        permalink=PERMALINK.format(token=token),
        posted_at=parse_israel_local_utc(d["dates"]["updatedAt"]),
        fetched_at=fetched_at,
        raw=copy.deepcopy(d),
        text=text,
        text_source="none" if is_blank(text) else "text",
        post_type=POST_TYPE,
        media=[],
        native_price=native_price,
        native_price_raw=None if native_price is None else str(native_price),
        native_currency=None if native_price is None else CURRENCY,
        native_title=None,
        native_location=_text(_get(d, "address", "city", "text")),
        author_name=_text(_get(d, "customer", "name")),
        author_id_raw=None if customer_id is None else str(customer_id),
        author_profile_url=None,
        top_comment=None,
        reactions_count=None,
        comments_count=None,
        shares_count=None,
    )


def photo_urls(d: dict[str, Any]) -> list[str]:
    """The listing's photos as Yad2 lists them (`metaData.images`), in order."""
    images = _get(d, "metaData", "images")
    return [url for url in images if isinstance(url, str)] if isinstance(images, list) else []


def form_fields(d: dict[str, Any]) -> dict[str, Any]:
    """The `Listing` values Yad2's form gives, by field name, in `Listing`'s own form (a `Marked`
    field as `{"state": "written", "value": …}`); a field the form leaves empty is absent, for the
    model (§6.3). `price_source` comes with a form price. A form flag counts when it is `true` or
    `false`; an absent one is the model's."""
    form: dict[str, Any] = {}
    kind = kind_ruling(_get(d, "additionalDetails", "property", "id"))
    if kind.post_nature is not None:
        form["post_nature"] = kind.post_nature
    if kind.apartment_kind is not None:
        form["apartment_kind"] = _written(kind.apartment_kind)

    price = d.get("price")
    if _positive_int(price):
        form["price"] = _written([price])
        form["price_source"] = "native"

    if _flag(d, "isImmediateEntrance") is True:
        form["entry_date"] = _written("immediate")
    elif isinstance(entrance := _get(d, "additionalDetails", "entranceDate"), str):
        form["entry_date"] = _written(parse_local_date(entrance))

    rooms = _get(d, "additionalDetails", "roomsCount")
    if _positive_number(rooms) and rooms * 2 == int(rooms * 2):
        form["rooms"] = _written(float(rooms))
    floor = _get(d, "address", "house", "floor")
    if type(floor) is int:
        form["floor"] = _written(floor)
    top_floor = _get(d, "additionalDetails", "buildingTopFloor")
    if _positive_int(top_floor):
        form["building_floors"] = _written(top_floor)
    size = _get(d, "additionalDetails", "squareMeter")
    if _positive_number(size):
        form["size_sqm"] = _written(float(size))

    broker = _BROKER_BY_AD_TYPE.get(d.get("adType"))
    if broker is not None:
        form["broker"] = _written(broker)
    for field, count, flag in (
        ("balcony", "balconiesCount", "includeBalcony"),
        ("parking", "parkingSpacesCount", "includeParking"),
    ):
        if _positive_int(_get(d, "additionalDetails", count)) or _flag(d, flag) is True:
            form[field] = _written(True)
        elif _flag(d, flag) is False:
            form[field] = _written(False)
    for field, flag in (
        ("elevator", "includeElevator"),
        ("air_conditioning", "includeAirconditioner"),
    ):
        if (value := _flag(d, flag)) is not None:
            form[field] = _written(value)
    if _flag(d, "includeFurniture") is False:
        form["furnished"] = _written("no")

    for field, key in (("arnona", "propertyTax"), ("house_committee", "houseCommittee")):
        if _positive_int(amount := d.get(key)):
            form[field] = _written(amount)

    street = _text(_get(d, "address", "street", "text"))
    if street is not None:
        number = _get(d, "address", "house", "number")
        form["streets"] = [f"{street} {number}" if _positive_int(number) else street]
    neighbourhood = _text(_get(d, "address", "neighborhood", "text"))
    if neighbourhood is not None:
        form["stated_area_names"] = [neighbourhood]
    return form


def _written(value: Any) -> dict[str, Any]:
    return {"state": "written", "value": value}


def _get(node: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _flag(d: dict[str, Any], name: str) -> bool | None:
    value = _get(d, "inProperty", name)
    return value if isinstance(value, bool) else None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and not is_blank(value) else None


def _positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _positive_number(value: Any) -> bool:
    return type(value) in (int, float) and value > 0
