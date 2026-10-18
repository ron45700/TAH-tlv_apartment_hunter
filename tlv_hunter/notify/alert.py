"""The alert itself: its lines and its buttons (`PHASE_4.md` §4.2; DECISIONS.md #321, #363, #452
point 13). Pure but for one read: whether the shown post's first stored photo can be sent.

The lines, HTML-escaped (only `<`, `>` and `&` need it outside a tag, Bot API "HTML style"): the
kind (and sublet); the price; the neighbourhood (🟠 when the location is not certain, §9 rule 5);
the street when written; the rooms ("1/2.5" on a room post); the entry date as written; then only
the categories the user set, each 🟢 met, 🔴 not met, 🟠 unclear, ⚪ not stated; "⚠️ חסר: …" for
a critical category not written; 🔴 "נשים בלבד" when that filter is off; the relative time of the
last publication. No post text (#363), so the caption stays far under 1,024 characters; it is
checked. Buttons: the site's post page, Facebook, WhatsApp (with a mobile number only), report.

The photo: the first stored photo of the card's shown post, uploaded from the store (its Facebook
link expires); a photo over 10 MB, out of Telegram's proportions or of another type, or no photo:
a text message with the same lines and buttons.
"""

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.policy.alert import missing_critical, set_categories
from tlv_hunter.policy.base import Evaluation
from tlv_hunter.telegram import callbacks
from tlv_hunter.telegram.client import Button, Keyboard
from tlv_hunter.web.cards import whatsapp_links

CAPTION_LIMIT = 1024  # sendPhoto caption, after entities parsing
TEXT_LIMIT = 4096  # sendMessage text
PHOTO_BYTES = 10 * 1024 * 1024  # "at most 10 MB"
PHOTO_SIDES = 10000  # "width and height must not exceed 10000 in total"
PHOTO_RATIO = 20  # "width and height ratio must be at most 20"
PHOTO_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

KIND_WORDS = {"room": "חדר בדירת שותפים", "whole_apartment": "דירה שלמה"}
NOT_STATED = "לא צוין"
STATE_MARKS = {"match": "🟢", "mismatch": "🔴", "unclear": "🟠", "not_written": "⚪"}
# The user's categories in the alert's words; "women only" has its own line (§8).
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


def build_alert(
    card: Card,
    evaluation: Evaluation,
    profile: Profile,
    area_names: Mapping[int, str],
    *,
    site_url: str,
    store_root: Path,
    now: datetime,
) -> Alert:
    shown = card.shown
    listing = shown.seen.listing
    if evaluation.listing_id != shown.listing_id:
        raise ValueError(f"the evaluation of {evaluation.listing_id} is not of {shown.listing_id}")
    lines = [
        f"🏠 <b>{_e(_kind_words(listing))}</b>",
        f"💰 {_e(price_words(listing) or NOT_STATED)}",
        _area_line(listing, evaluation, area_names),
    ]
    if listing.streets:
        lines.append(f"🛣 {_e('רחוב: ' + ', '.join(listing.streets))}")
    lines.append(f"🚪 {_e(rooms_words(listing))}")
    lines.append(f"📅 {_e(entry_words(listing))}")
    categories = set_categories(profile, evaluation)
    marks = [
        f"{STATE_MARKS[state]} {_e(CATEGORY_WORDS[name])}"
        for name in categories
        if name in CATEGORY_WORDS and (state := evaluation.fields.get(name)) in STATE_MARKS
    ]
    if marks:
        lines.append("")
        lines.extend(marks)
    missing = [CATEGORY_WORDS[name] for name in missing_critical(profile, evaluation)]
    if missing:
        lines.append(f"⚠️ {_e('חסר: ' + ', '.join(missing))}")
    if evaluation.women_only_icon:
        lines.append(f"🔴 {_e('נשים בלבד')}")
    lines.append("")
    lines.append(f"🕒 {_e(relative_time(card.last_published_at, now))}")
    photo = first_photo(card, store_root)
    text = "\n".join(lines)
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
    """The alert's own buttons; without "report" once the user has reported it."""
    shown = card.shown
    rows: list[list[Button]] = [
        [Button(BUTTON_SITE, url=f"{site_url.rstrip('/')}/post/{shown.listing_id}")]
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


# --- the values in words, as the site's own formatters put them (frontend/src/format.ts) ---


def _kind_words(listing: Listing) -> str:
    kind = listing.apartment_kind.value
    words = KIND_WORDS[kind] if kind is not None else "סוג לא ברור"
    return words + (" · סאבלט" if listing.post_nature == "sublet_offer" else "")


def price_words(listing: Listing) -> str | None:
    """Every amount, "₪5,000/5,500" (#95)."""
    if listing.price.state == "unclear":
        return "המחיר לא ברור"
    if listing.price.value is None:
        return None
    first, *rest = listing.price.value
    return "/".join([f"₪{first:,}", *(f"{amount:,}" for amount in rest)])


def rooms_words(listing: Listing) -> str:
    """A room post "חדרים: 1/2.5" (#325), "חדר 1 (סה״כ לא צוין)" with no total; else the
    apartment's rooms."""
    rooms = listing.rooms
    total = _number(rooms.value) if rooms.value is not None else None
    if listing.apartment_kind.value == "room":
        if total is not None:
            return f"חדרים: 1/{total}"
        return f"חדר 1 (סה״כ {'לא ברור' if rooms.state == 'unclear' else NOT_STATED})"
    if total is not None:
        return f"{total} חדרים"
    return f"חדרים: {'לא ברור' if rooms.state == 'unclear' else NOT_STATED}"


def entry_words(listing: Listing) -> str:
    """The entry date as the poster wrote it (#96); its year never shown (#115)."""
    entry = listing.entry_date
    if entry.state == "not_written":
        return f"כניסה: {NOT_STATED}"
    if listing.entry_date_written:
        return f"כניסה: {listing.entry_date_written}"
    if entry.state == "unclear":
        return "כניסה: לא ברור"
    if entry.value == "immediate":
        return "כניסה מיידית"
    assert isinstance(entry.value, date)
    return f"כניסה: {entry.value.day}.{entry.value.month}"


def relative_time(moment: datetime, now: datetime) -> str:
    """Minutes up to an hour, hours up to 24 hours, days after that (#122)."""
    minutes = max(0, int((now - moment).total_seconds() // 60))
    if minutes < 1:
        return "פורסם עכשיו"
    if minutes < 60:
        return "פורסם " + _ago(minutes, "דקה", "שתי דקות", "דקות")
    hours = minutes // 60
    if hours < 24:
        return "פורסם " + _ago(hours, "שעה", "שעתיים", "שעות")
    return "פורסם " + _ago(hours // 24, "יום", "יומיים", "ימים")


def _ago(count: int, one: str, two: str, many: str) -> str:
    if count == 1:
        return f"לפני {one}"
    if count == 2:
        return f"לפני {two}"
    return f"לפני {count} {many}"


def _area_line(listing: Listing, evaluation: Evaluation, area_names: Mapping[int, str]) -> str:
    names = " · ".join(area_names[number] for number in listing.areas)
    if evaluation.area_orange:
        return f"🟠 {_e(names + ' (המיקום לא ודאי)')}"
    return f"📍 {_e(names)}"


def _number(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def _e(text: str) -> str:
    return html.escape(text, quote=False)
