"""The alert itself: its lines and its buttons (`PHASE_4.md` §4.2; DECISIONS.md #321, #452 point 13;
the layout of #481, which replaces #363's "no post text" and the categories' per-profile colours).
Pure but for one read: whether the shown post's first stored photo can be sent.

HTML-escaped (only `<`, `>` and `&` need it outside a tag, Bot API "HTML style"); every line starts
with "- " but the quoted text; blocks apart by a blank line; no icon but the colour circles:
1. the kind (and sublet), then the card's tier circle, the site's glow (`policy.colours.glow`);
2. the location (one area: its region heading, its label, the street; two or more and a street:
   the street alone, "(מיקום מדויק לא ודאי)" unless it holds a house number; two or more and no
   street: the region headings, the neighbourhood "לא ודאי"), the price, the entry date, the
   rooms, the floor;
3. only when written: arnona, the house committee, the furniture (none: no line);
4. balcony, parking, elevator, air conditioning, broker by the post's own value (🟢 yes, 🔴 no,
   🟠 unclear, no line when not written); 🔴 "נשים בלבד" when that filter is off; "חסר: …" for a
   critical category not written (§9);
5. the first lines of the poster's text, verbatim, in a `<blockquote>`;
6. the relative time of the last publication, with its day, month and Israel time.
The caption's limit is checked. Buttons: the site's post page inside the Mini App (`web_app`),
Facebook, WhatsApp (with a mobile number only), report.

The photo: the first stored photo of the card's shown post, uploaded from the store (its Facebook
link expires); a photo over 10 MB, out of Telegram's proportions or of another type, or no photo:
a text message with the same lines and buttons.
"""

import html
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tlv_hunter.areas.reference import load_area_groups, load_areas
from tlv_hunter.contracts.listing import Listing, Marked
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.policy.alert import missing_critical
from tlv_hunter.policy.base import Evaluation
from tlv_hunter.policy.colours import glow
from tlv_hunter.schedule import ZONE
from tlv_hunter.telegram import callbacks
from tlv_hunter.telegram.client import Button, Keyboard
from tlv_hunter.web.cards import whatsapp_links

CAPTION_LIMIT = 1024  # sendPhoto caption, after entities parsing
TEXT_LIMIT = 4096  # sendMessage text
PHOTO_BYTES = 10 * 1024 * 1024  # "at most 10 MB"
PHOTO_SIDES = 10000  # "width and height must not exceed 10000 in total"
PHOTO_RATIO = 20  # "width and height ratio must be at most 20"
PHOTO_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
EXCERPT_LINES = 3
EXCERPT_CHARS = 200

KIND_WORDS = {"room": "חדר בדירת שותפים", "whole_apartment": "דירה שלמה"}
NOT_STATED = "לא צוין"
UNCLEAR = "לא ברור"
NOT_CERTAIN = "לא ודאי"
STREET_NOT_EXACT = " (מיקום מדויק לא ודאי)"
GLOW_CIRCLES = {"green": "🟢", "orange": "🟠", "red": "🔴"}
YES, NO, UNKNOWN = "🟢", "🔴", "🟠"
# Block 4, in order, before the broker (whose words depend on its value).
YES_NO_WORDS = {
    "balcony": "מרפסת",
    "parking": "חניה",
    "elevator": "מעלית",
    "air_conditioning": "מזגן",
}
# The categories in the "חסר" line's words; "women only" has its own line (§8).
CATEGORY_WORDS = {
    "areas": "אזור",
    "price": "מחיר",
    "rooms": "חדרים",
    "floor": "קומה",
    "size_sqm": "גודל",
    "broker": "ללא תיווך",
    "parking": "חניה",
    "balcony": "מרפסת",
    "entry_date": "תאריך כניסה",
}
FURNISHED_WORDS = {"yes": "יש", "partial": "חלקי"}
# A leading "כניסה" as a whole word, with the spaces, colon or dash after it.
ENTRY_WORD = re.compile(r"\s*כניסה(?=[\s:\-–]|$)[\s:\-–]*")

BUTTON_SITE = "פתיחה באתר"
BUTTON_FACEBOOK = "פייסבוק"
BUTTON_WHATSAPP = "וואטסאפ"
BUTTON_REPORT = "דיווח"


@dataclass(frozen=True)
class Photo:
    path: Path
    content_type: str


@dataclass(frozen=True)
class Alert:
    listing_id: str
    """The card's shown post: what the sent-alert record names."""
    text: str
    """The lines, HTML."""
    keyboard: Keyboard
    photo: Photo | None


@dataclass(frozen=True)
class AreaWords:
    """The areas in the site's words: each number's label, and its region heading in the area
    filter (#261), the headings in the filter's order."""

    names: Mapping[int, str]
    regions: Mapping[int, str]
    headings: Sequence[str]


def reference_area_words() -> AreaWords:
    groups = load_area_groups()
    return AreaWords(
        names={area.number: area.display_name for area in load_areas()},
        regions={number: group.heading for group in groups for number in group.areas},
        headings=tuple(group.heading for group in groups),
    )


def build_alert(
    card: Card,
    evaluation: Evaluation,
    profile: Profile,
    areas: AreaWords,
    *,
    site_url: str,
    store_root: Path,
    now: datetime,
    zone: ZoneInfo | None = None,
) -> Alert:
    shown = card.shown
    listing = shown.seen.listing
    if evaluation.listing_id != shown.listing_id:
        raise ValueError(f"the evaluation of {evaluation.listing_id} is not of {shown.listing_id}")
    circle = GLOW_CIRCLES.get(glow(evaluation, profile) or "")
    colours = colour_lines(listing)
    if evaluation.women_only_icon:
        colours.append(f"- {NO} {_e('נשים בלבד')}")
    missing = [CATEGORY_WORDS[name] for name in missing_critical(profile, evaluation)]
    if missing:
        colours.append(_line("חסר", ", ".join(missing)))
    excerpt = text_excerpt(shown.post.text)
    published = card.last_published_at
    local = published.astimezone(zone or ZoneInfo(ZONE))
    stamp = f"{local.day}.{local.month}, {local:%H:%M}"
    blocks = [
        [f"- <b>{_e(_kind_words(listing))}</b>" + (f" {circle}" if circle else "")],
        [
            *location_lines(listing, areas),
            _line("מחיר", price_words(listing)),
            _line("כניסה", entry_words(listing)),
            _line("חדרים", rooms_words(listing)),
            _line("קומה", floor_words(listing)),
        ],
        fee_lines(listing),
        colours,
        [f"<blockquote>{_e(excerpt)}</blockquote>"] if excerpt else [],
        [_line("פורסם", f"{relative_words(published, now)} ({stamp})")],
    ]
    text = "\n\n".join("\n".join(block) for block in blocks if block)
    photo = first_photo(card, store_root)
    limit = CAPTION_LIMIT if photo is not None else TEXT_LIMIT
    if visible_length(text) > limit:
        raise ValueError(f"the alert of {shown.listing_id} is over {limit} characters")
    return Alert(
        listing_id=shown.listing_id,
        text=text,
        keyboard=alert_keyboard(card, site_url),
        photo=photo,
    )


def alert_keyboard(card: Card, site_url: str, *, report: bool = True) -> Keyboard:
    """The alert's own buttons; without "report" once the user has reported it. The site's
    button opens the post inside the Mini App (`web_app`: private chats only, Bot API 10.3; an
    alert goes to a private chat only)."""
    shown = card.shown
    rows: list[list[Button]] = [
        [Button(BUTTON_SITE, web_app_url=f"{site_url.rstrip('/')}/post/{shown.listing_id}")]
    ]
    links = [Button(BUTTON_FACEBOOK, url=shown.post.permalink)]
    mobiles = whatsapp_links(shown)
    if mobiles:
        links.append(Button(BUTTON_WHATSAPP, url=mobiles[0]))
    rows.append(links)
    if report:
        ref = callbacks.ref_of(shown.listing_id)
        rows.append([Button(BUTTON_REPORT, callback_data=callbacks.Callback("r", ref).data())])
    return rows


def first_photo(card: Card, store_root: Path) -> Photo | None:
    """The shown post's first stored photo, when Telegram takes it as a photo."""
    shown = card.shown
    media = {item.media_id: item for item in shown.post.media}
    for image in shown.lifecycle.images:
        if image.local_path is None:
            continue
        path = Path(store_root) / image.local_path
        content_type = PHOTO_TYPES.get(path.suffix.lower())
        if content_type is None or not path.is_file() or path.stat().st_size > PHOTO_BYTES:
            return None
        item = media.get(image.media_id)
        if item is not None and item.width and item.height:
            if item.width + item.height > PHOTO_SIDES:
                return None
            if max(item.width, item.height) > PHOTO_RATIO * min(item.width, item.height):
                return None
        return Photo(path, content_type)
    return None


def visible_length(text: str) -> int:
    """The length after entities parsing: the tags gone, the entities one character each."""
    return len(html.unescape(re.sub(r"<[^>]+>", "", text)))


# --- the blocks ---


def location_lines(listing: Listing, areas: AreaWords) -> list[str]:
    """Block 2's location (#481): exact with one area; with several, the street alone or the
    region headings. With none (such a post never alerts, §9), the street or "לא צוין"."""
    street = ", ".join(listing.streets)
    if len(listing.areas) == 1:
        (number,) = listing.areas
        lines = [_line("אזור", areas.regions[number]), _line("שכונה", areas.names[number])]
        return lines + ([_line("רחוב", street)] if street else [])
    if street:
        # From instructions version 6 (#484) a street carries its house number when the post gives
        # one; a version-5 `Listing` never does, so its street always takes the suffix.
        exact = any(character.isdigit() for character in street)
        return [_line("רחוב", street + ("" if exact else STREET_NOT_EXACT))]
    if listing.areas:
        found = {areas.regions[number] for number in listing.areas}
        headings = [heading for heading in areas.headings if heading in found]
        return [_line("אזור", ", ".join(headings)), _line("שכונה", NOT_CERTAIN)]
    return [_line("שכונה", NOT_STATED)]


def fee_lines(listing: Listing) -> list[str]:
    """Block 3: arnona, the house committee and the furniture, only when written."""
    lines = []
    for words, fee in (("ארנונה", listing.arnona), ("ועד בית", listing.house_committee)):
        if fee.state == "unclear":
            lines.append(_line(words, UNCLEAR))
        elif fee.state == "written":
            lines.append(_line(words, "כלול" if fee.value == "included" else f"₪{fee.value:,}"))
    furnished = listing.furnished
    if furnished.state == "unclear":
        lines.append(_line("ריהוט", UNCLEAR))
    elif furnished.state == "written" and furnished.value in FURNISHED_WORDS:
        lines.append(_line("ריהוט", FURNISHED_WORDS[furnished.value]))
    return lines


def colour_lines(listing: Listing) -> list[str]:
    """Block 4, by the post's own value, never the profile's: a line only when written."""
    lines = [
        f"- {_circle(getattr(listing, name), True)} {_e(words)}"
        for name, words in YES_NO_WORDS.items()
        if getattr(listing, name).state != "not_written"
    ]
    broker = listing.broker
    if broker.state != "not_written":
        words = "ללא תיווך" if broker.value is False else "תיווך"
        lines.append(f"- {_circle(broker, False)} {_e(words)}")
    return lines


def text_excerpt(text: str) -> str:
    """The first non-empty lines of the poster's text, verbatim, cut with "…" when longer."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    excerpt = "\n".join(lines[:EXCERPT_LINES])
    if len(excerpt) > EXCERPT_CHARS:
        return excerpt[: EXCERPT_CHARS - 1].rstrip() + "…"
    return excerpt + ("…" if len(lines) > EXCERPT_LINES else "")


# --- the values in words, as the site's own formatters put them (frontend/src/format.ts) ---


def _kind_words(listing: Listing) -> str:
    kind = listing.apartment_kind.value
    words = KIND_WORDS[kind] if kind is not None else "סוג לא ברור"
    return words + (" · סאבלט" if listing.post_nature == "sublet_offer" else "")


def price_words(listing: Listing) -> str:
    """Every amount, "₪5,000/5,500" (#95)."""
    if listing.price.state == "unclear":
        return UNCLEAR
    if listing.price.value is None:
        return NOT_STATED
    first, *rest = listing.price.value
    return "/".join([f"₪{first:,}", *(f"{amount:,}" for amount in rest)])


def rooms_words(listing: Listing) -> str:
    """A room post "1/2.5" (#325), "1 (סה״כ לא צוין)" with no total; else the apartment's
    rooms."""
    rooms = listing.rooms
    if listing.apartment_kind.value == "room":
        if rooms.value is not None:
            return f"1/{_number(rooms.value)}"
        return f"1 (סה״כ {UNCLEAR if rooms.state == 'unclear' else NOT_STATED})"
    return _value(rooms, _number)


def floor_words(listing: Listing) -> str:
    """ "3/4" only when the building's floors are written (#98, #106)."""
    total = listing.building_floors.value
    return _value(
        listing.floor,
        lambda floor: _floor_name(floor) + (f"/{total}" if total is not None else ""),
    )


def entry_words(listing: Listing) -> str:
    """The entry date as the poster wrote it (#96); its year never shown (#115)."""
    entry = listing.entry_date
    if entry.state == "not_written":
        return NOT_STATED
    if listing.entry_date_written:
        return without_entry_word(listing.entry_date_written)
    if entry.state == "unclear":
        return UNCLEAR
    if entry.value == "immediate":
        return "מיידית"
    assert isinstance(entry.value, date)
    return f"{entry.value.day}.{entry.value.month}"


def without_entry_word(written: str) -> str:
    """The text as written without a leading word "כניסה", which the line's own label already says
    ("כניסה מיידית" reads "מיידית"). Display only: the stored text stays verbatim (#96)."""
    match = ENTRY_WORD.match(written)
    rest = written[match.end() :] if match else written
    return rest if rest.strip() else written


def relative_words(moment: datetime, now: datetime) -> str:
    """Minutes up to an hour, hours up to 24 hours, days after that (#122)."""
    minutes = max(0, int((now - moment).total_seconds() // 60))
    if minutes < 1:
        return "עכשיו"
    if minutes < 60:
        return _ago(minutes, "דקה", "שתי דקות", "דקות")
    hours = minutes // 60
    if hours < 24:
        return _ago(hours, "שעה", "שעתיים", "שעות")
    return _ago(hours // 24, "יום", "יומיים", "ימים")


def _ago(count: int, one: str, two: str, many: str) -> str:
    if count == 1:
        return f"לפני {one}"
    if count == 2:
        return f"לפני {two}"
    return f"לפני {count} {many}"


def _circle(marked: Marked[bool], good: bool) -> str:
    if marked.state == "unclear":
        return UNKNOWN
    return YES if marked.value is good else NO


def _value[T](marked: Marked[T], words: Callable[[T], str]) -> str:
    if marked.state == "unclear":
        return UNCLEAR
    if marked.value is None:
        return NOT_STATED
    return words(marked.value)


def _floor_name(floor: int) -> str:
    """0 the ground floor, -1 the basement (#98)."""
    return {0: "קרקע", -1: "מרתף"}.get(floor, str(floor))


def _number(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def _line(label: str, value: str) -> str:
    return f"- {_e(label)}: {_e(value)}"


def _e(text: str) -> str:
    return html.escape(text, quote=False)
