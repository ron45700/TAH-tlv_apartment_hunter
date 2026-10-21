"""Who is alerted and what the alert says (`PHASE_4.md` 4.5, 4.6; `BASELINE.md` §9; DECISIONS.md
#230–#232, #357, #360, #363, #452, #453): `policy.alert`, `notify.alert`, `telegram.alerts`.

Cards built in memory (`dedup/stage_b`); users and sent-alert records in a temporary SQLite store.
"""

import re
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import make_listing
from tests.test_gate_d import make_post, written
from tests.test_userdata_store import ADMIN_ID, admin, friend
from tlv_hunter.contracts.post_lifecycle import PostImage
from tlv_hunter.contracts.profile import DateRangeCriterion, Profile, RangeCriterion, new_profile
from tlv_hunter.dedup.stage_b import Card, KeyInputs, KeyPost, TiedPair, cards, derive_cards
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.notify.alert import (
    CAPTION_LIMIT,
    Alert,
    alert_keyboard,
    build_alert,
    first_photo,
    reference_area_words,
    relative_words,
    visible_length,
    without_entry_word,
)
from tlv_hunter.policy.alert import (
    PUBLISHED_WINDOW,
    missing_critical,
    no_alert_reason,
    published_too_long_ago,
    set_categories,
)
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.postmodel.rejects import classified_lifecycle
from tlv_hunter.postmodel.seen import seen_listing
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.telegram.alerts import ALERT_WINDOW, SEND_GAP_SECONDS, AlertPass, due_alerts
from tlv_hunter.telegram.client import TelegramError
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

LINKED_AT = datetime(2026, 10, 13, 8, 0, tzinfo=UTC)
NOW = LINKED_AT + timedelta(hours=3)
SITE = "https://tlvapthunter.x.ts.net"
AREAS = reference_area_words()
APARTMENT = written("whole_apartment")
ROOM = written("room")
NOT_WRITTEN = {"state": "not_written", "value": None}


def key_post(
    n: int,
    *,
    kind: dict[str, Any] | None = None,
    price: tuple[int, ...] | None = (5000,),
    areas: tuple[int, ...] = (30,),
    fetched: datetime = LINKED_AT + timedelta(hours=1),
    classified: datetime = NOW - timedelta(hours=1),
    posted: datetime | None = None,
    text: str | None = None,
    root: Path | None = None,
    photo: str | None = None,
    **listing: Any,
) -> KeyPost:
    at = posted if posted is not None else fetched
    body = text if text is not None else f"flat words {n} " + "x" * n
    post = make_post(n, body, at=at).with_changes(fetched_at=fetched)
    record = make_listing(
        post.listing_id,
        apartment_kind=APARTMENT if kind is None else kind,
        price=written(list(price)) if price is not None else NOT_WRITTEN,
        price_source="text" if price is not None else None,
        areas=list(areas),
        classified_at=classified,
        **listing,
    )
    lifecycle = classified_lifecycle(initial_lifecycle(post), record, post)
    if photo is not None and root is not None:
        local = f"images/{post.listing_id}/{photo}"
        (root / local).parent.mkdir(parents=True, exist_ok=True)
        (root / local).write_bytes(b"\xff\xd8 jpeg")
        image = PostImage(
            listing_id=post.listing_id, media_id=f"media-{n}", local_path=local, error=None
        )
        lifecycle = lifecycle.model_copy(update={"images": [image]})
    return KeyPost(post, lifecycle, seen_listing(record, []), frozenset())


def card_of(*members: KeyPost) -> Card:
    inputs = KeyInputs(members=members, duplicates={})
    if len(members) == 1:
        (card,) = derive_cards(inputs)
        return card
    first, second = sorted(m.listing_id for m in members)
    (card,) = cards(inputs, [TiedPair(first, second, ("photo",))])
    return card


def linked(**changes: Any):
    return admin(telegram_chat_id=42, telegram_linked_at=LINKED_AT, **changes)


def profile(**option_values: Any) -> Profile:
    base = new_profile(ADMIN_ID, NOW)
    option = base.whole_apartment.model_copy(update=option_values)
    return base.model_copy(update={"whole_apartment": option, "room": option})


def reason(member: KeyPost, wanted: Profile | None = None) -> str | None:
    evaluation = evaluate(member.seen, wanted or profile(), NOW)
    return no_alert_reason(member.seen, evaluation)


# --- §9's rules on one post (policy.alert) ---


def test_a_post_with_its_kind_a_price_and_an_area_alerts() -> None:
    assert reason(key_post(1)) is None


def test_a_post_whose_kind_is_unclear_or_not_written_never_alerts() -> None:
    assert reason(key_post(1, kind=NOT_WRITTEN)) == "kind_unclear"
    assert reason(key_post(2, kind={"state": "unclear", "value": None})) == "kind_unclear"


def test_a_post_with_no_explicit_price_never_alerts() -> None:
    assert reason(key_post(1, price=None)) == "no_price"
    member = key_post(2)
    unclear = make_listing(
        member.listing_id,
        apartment_kind=APARTMENT,
        price={"state": "unclear", "value": None},
        price_source="text",
        areas=[30],
    )
    seen = seen_listing(unclear, [])
    assert no_alert_reason(seen, evaluate(seen, profile(), NOW)) == "no_price"


def test_a_post_with_no_area_never_alerts_even_with_a_street() -> None:
    assert reason(key_post(1, areas=())) == "no_location"
    assert reason(key_post(2, areas=(), streets=["דיזנגוף"])) == "no_location"


def test_a_post_failing_a_critical_condition_or_an_option_off_never_alerts() -> None:
    assert reason(key_post(1, price=(9000,)), profile(price_max=6000)) == "not_shown"
    assert reason(key_post(2, areas=(52,)), profile(areas=[30])) == "not_shown"
    base = new_profile(ADMIN_ID, NOW)
    off = base.model_copy(
        update={"whole_apartment": base.whole_apartment.model_copy(update={"enabled": False})}
    )
    assert reason(key_post(3), off) == "not_shown"
    assert reason(key_post(4, post_nature="sublet_offer")) == "not_shown"  # sublets off (#268)


def test_the_chip_alerts_through_the_same_rolling_window() -> None:
    """#458: the alert reads the same evaluation, with its own `now`; the window moves by itself."""
    wanted = profile(
        entry_date=DateRangeCriterion(earliest=None, latest=None, immediate=True, level="critical")
    )
    soon = key_post(1, entry_date=written(date(2026, 12, 1)))
    later = key_post(2, entry_date=written(date(2027, 2, 1)))  # NOW is 2026-10-13
    assert reason(soon, wanted) is None
    assert reason(later, wanted) == "not_shown"
    evaluation = evaluate(later.seen, wanted, NOW + timedelta(days=31))
    assert no_alert_reason(later.seen, evaluation) is None


def test_several_areas_alert_when_one_is_chosen_with_the_area_orange() -> None:
    member = key_post(1, areas=(30, 31))
    evaluation = evaluate(member.seen, profile(areas=[31]), NOW)
    assert no_alert_reason(member.seen, evaluation) is None and evaluation.area_orange


def test_preferences_never_block_and_a_critical_category_not_written_is_named() -> None:
    wanted = profile(
        parking="critical",
        balcony="preference",
        rooms=RangeCriterion[float](min=4.0, max=None, level="preference"),
    )
    member = key_post(1, rooms=written(2.0))
    evaluation = evaluate(member.seen, wanted, NOW)
    assert no_alert_reason(member.seen, evaluation) is None
    assert missing_critical(wanted, evaluation) == ("parking",)
    # "Women only" hides by default (#268): set, critical; the message has its own line for it.
    assert list(set_categories(wanted, evaluation)) == ["women_only", "rooms", "parking", "balcony"]


def test_the_evaluation_must_be_of_the_post() -> None:
    first, second = key_post(1), key_post(2)
    with pytest.raises(ValueError):
        no_alert_reason(first.seen, evaluate(second.seen, profile(), NOW))


# --- the message (§4.2, #481) ---


def alert_of(member: KeyPost, wanted: Profile | None = None, root: Path = Path(".")) -> Alert:
    wanted = wanted or profile()
    evaluation = evaluate(member.seen, wanted, NOW)
    return build_alert(
        card_of(member), evaluation, wanted, AREAS, site_url=SITE, store_root=root, now=NOW
    )


def blocks_of(member: KeyPost, wanted: Profile | None = None) -> list[list[str]]:
    return [block.split("\n") for block in alert_of(member, wanted).text.split("\n\n")]


def test_the_blocks_type_location_values_and_time() -> None:
    member = key_post(
        1,
        price=(5000, 5500),
        areas=(52,),
        streets=["הרצל"],
        rooms=written(3.5),
        floor=written(3),
        building_floors=written(4),
        entry_date=written("immediate"),
        entry_date_written="כניסה מיידית",
        fetched=NOW - timedelta(minutes=20),
        text="שורה ראשונה",
    )
    blocks = blocks_of(member)
    assert blocks[0] == ["- <b>דירה שלמה</b>"]
    assert blocks[1] == [
        "- אזור: דרום העיר",
        "- שכונה: פלורנטין",
        "- רחוב: הרצל",
        "- מחיר: ₪5,000/5,500",
        "- כניסה: מיידית",  # the leading word dropped for display (#485)
        "- חדרים: 3.5",
        "- קומה: 3/4",
    ]
    assert blocks[2] == ["<blockquote>שורה ראשונה</blockquote>"]
    # 10:40 UTC on 13.10 is 13:40 Israel time (IDT, +3).
    assert blocks[-1] == ["- פורסם: לפני 20 דקות (13.10, 13:40)"]
    every = [line for block in blocks for line in block if not line.startswith("<blockquote>")]
    assert all(line.startswith("- ") for line in every)


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        ("כניסה מיידית", "מיידית"),
        ("כניסה: 1.11", "1.11"),
        ("כניסה ב18.10", "ב18.10"),
        ("מיידית", "מיידית"),
        ("כניסה", "כניסה"),  # nothing after it: kept whole
        ("כניסתך מיידית", "כניסתך מיידית"),  # not the word itself
    ],
)
def test_the_entry_line_drops_a_leading_entry_word_for_display_only(text: str, shown: str) -> None:
    assert without_entry_word(text) == shown
    member = key_post(1, entry_date=written("immediate"), entry_date_written=text)
    assert f"- כניסה: {shown}" in blocks_of(member)[1]
    assert member.seen.listing.entry_date_written == text  # the stored text, verbatim (#96)


def test_one_area_with_no_street_names_the_region_and_the_neighbourhood_only() -> None:
    location = blocks_of(key_post(1, areas=(37,)))[1][:3]
    assert location == ["- אזור: מרכז העיר", "- שכונה: לב תל-אביב", "- מחיר: ₪5,000"]


def test_several_areas_and_a_street_show_the_street_alone_marked_not_exact() -> None:
    member = key_post(1, areas=(30, 31), streets=["אבן גבירול"])
    location = blocks_of(member, profile(areas=[31]))[1]
    assert location[0] == "- רחוב: אבן גבירול (מיקום מדויק לא ודאי)"
    assert not any(line.startswith(("- אזור", "- שכונה")) for line in location)
    numbered = key_post(2, areas=(30, 31), streets=["אבן גבירול 40"])
    assert blocks_of(numbered, profile(areas=[31]))[1][0] == "- רחוב: אבן גבירול 40"


def test_several_areas_and_no_street_show_the_regions_and_an_uncertain_neighbourhood() -> None:
    same_region = blocks_of(key_post(1, areas=(30, 31)), profile(areas=[31]))[1][:2]
    assert same_region == ["- אזור: הצפון הישן והחדש", "- שכונה: לא ודאי"]
    two = blocks_of(key_post(2, areas=(11, 52)), profile(areas=[52]))[1][0]
    assert two == "- אזור: דרום העיר, אזורים שאינם למגורים"  # the area filter's order


def test_the_values_not_written_read_not_stated() -> None:
    lines = blocks_of(key_post(1))[1]
    assert lines[2:] == [
        "- מחיר: ₪5,000",
        "- כניסה: לא צוין",
        "- חדרים: לא צוין",
        "- קומה: לא צוין",
    ]
    floor = blocks_of(key_post(2, floor=written(0)))[1][-1]
    assert floor == "- קומה: קרקע"  # no building floors: no "/"


def test_a_room_post_reads_1_of_n_and_a_sublet_says_so() -> None:
    member = key_post(1, kind=ROOM, rooms=written(2.5), post_nature="sublet_offer")
    wanted = new_profile(ADMIN_ID, NOW).model_copy(update={"include_sublets": True})
    blocks = blocks_of(member, wanted)
    assert blocks[0][0].startswith("- <b>חדר בדירת שותפים · סאבלט</b>")
    assert "- חדרים: 1/2.5" in blocks[1]
    assert "- חדרים: 1 (סה״כ לא צוין)" in blocks_of(key_post(2, kind=ROOM))[1]


def test_the_tier_circle_is_the_sites_glow_and_absent_without_a_preference() -> None:
    wanted = profile(balcony="preference")
    assert blocks_of(key_post(1, balcony=written(True)), wanted)[0] == ["- <b>דירה שלמה</b> 🟢"]
    assert blocks_of(key_post(2), wanted)[0] == ["- <b>דירה שלמה</b> 🟠"]
    bottom = profile(balcony="preference", parking="critical")
    assert blocks_of(key_post(3), bottom)[0] == ["- <b>דירה שלמה</b> 🔴"]
    assert blocks_of(key_post(4))[0] == ["- <b>דירה שלמה</b>"]  # no preference: no glow


def test_fees_and_furniture_only_when_written() -> None:
    member = key_post(
        1,
        arnona=written(450),
        house_committee={"state": "unclear", "value": None},
        furnished=written("partial"),
    )
    assert blocks_of(member)[2] == ["- ארנונה: ₪450", "- ועד בית: לא ברור", "- ריהוט: חלקי"]
    included = blocks_of(key_post(2, arnona=written("included")))[2]
    assert included == ["- ארנונה: כלול"]
    unfurnished = alert_of(key_post(3, furnished=written("no"))).text
    assert "ריהוט" not in unfurnished and "ארנונה" not in unfurnished


def test_the_colour_block_by_the_posts_own_value() -> None:
    member = key_post(
        1,
        balcony=written(True),
        parking=written(False),
        elevator={"state": "unclear", "value": None},
        broker=written(False),
    )
    assert blocks_of(member)[2] == ["- 🟢 מרפסת", "- 🔴 חניה", "- 🟠 מעלית", "- 🟢 ללא תיווך"]
    agent = blocks_of(key_post(2, air_conditioning=written(True), broker=written(True)))
    assert agent[2] == ["- 🟢 מזגן", "- 🔴 תיווך"]
    plain = alert_of(key_post(3)).text
    assert not any(mark in plain for mark in ("🟢", "🔴", "🟠", "⚪", "⚠️")) and "נשים" not in plain


def test_the_colour_block_ignores_the_profile_then_women_only_and_missing() -> None:
    wanted = profile(parking="critical", broker="preference", hide_women_only=False)
    member = key_post(1, broker=written(True), gender="women_only")
    assert blocks_of(member, wanted)[2] == ["- 🔴 תיווך", "- 🔴 נשים בלבד", "- חסר: חניה"]


def test_the_text_its_first_three_lines_verbatim_escaped_and_cut() -> None:
    member = key_post(1, text="\n  שותף/ה <דחוף> & מהר  \n\nשנייה\nשלישית\nרביעית")
    quote = blocks_of(member)[-2]
    assert quote == ["<blockquote>שותף/ה &lt;דחוף&gt; &amp; מהר", "שנייה", "שלישית…</blockquote>"]
    long = alert_of(key_post(2, text="א" * 500)).text
    (inside,) = re.findall(r"<blockquote>(.*)</blockquote>", long)
    assert len(inside) == 200 and inside.endswith("…")


def test_every_written_value_is_html_escaped() -> None:
    member = key_post(
        1,
        streets=["<b>א&ב</b>"],
        entry_date=written("immediate"),
        entry_date_written="<i>&now",
    )
    text = alert_of(member).text
    assert "&lt;b&gt;א&amp;ב&lt;/b&gt;" in text and "&lt;i&gt;&amp;now" in text
    assert "<i>" not in text


def test_the_caption_stays_under_1024_characters() -> None:
    member = key_post(1, streets=["רחוב"] * 3, rooms=written(3.0), text="מילה " * 300)
    wanted = profile(parking="critical", balcony="critical", broker="critical")
    assert visible_length(alert_of(member, wanted).text) < CAPTION_LIMIT // 2
    assert visible_length("<b>a&amp;b</b>") == 3


def test_the_caption_limit_is_checked_for_a_photo(tmp_path: Path) -> None:
    member = key_post(1, streets=["א" * 1030], root=tmp_path, photo="a1.jpg")
    with pytest.raises(ValueError, match="over 1024"):
        alert_of(member, root=tmp_path)


def test_the_time_line_now_hours_and_days() -> None:
    assert relative_words(NOW, NOW) == "עכשיו"
    assert relative_words(NOW - timedelta(hours=2), NOW) == "לפני שעתיים"
    assert relative_words(NOW - timedelta(days=5), NOW) == "לפני 5 ימים"
    member = key_post(1, fetched=NOW)
    assert blocks_of(member)[-1] == ["- פורסם: עכשיו (13.10, 14:00)"]


def test_the_buttons_site_in_the_mini_app_facebook_whatsapp_with_a_mobile_and_report() -> None:
    member = key_post(1, text="flat words call 054-123-4567")
    card = card_of(member)
    rows = alert_keyboard(card, SITE)
    assert [[b.text for b in row] for row in rows] == [
        ["פתיחה באתר"],
        ["פייסבוק", "וואטסאפ"],
        ["דיווח"],
    ]
    site = rows[0][0]
    assert site.url is None and site.web_app_url == f"{SITE}/post/{member.listing_id}"
    assert site.as_json() == {
        "text": "פתיחה באתר",
        "web_app": {"url": f"{SITE}/post/{member.listing_id}"},
    }
    assert rows[1][0].url == member.post.permalink
    assert rows[1][1].url == "https://wa.me/972541234567"
    assert rows[2][0].callback_data == f"r:{member.listing_id[:16]}"
    landline = card_of(key_post(2, text="flat words call 03-5551234"))
    assert [b.text for b in alert_keyboard(landline, SITE)[1]] == ["פייסבוק"]
    assert len(alert_keyboard(card, SITE, report=False)) == 2


def test_the_first_stored_photo_is_sent_or_a_text_message(tmp_path: Path) -> None:
    with_photo = key_post(1, root=tmp_path, photo="a1.jpg")
    photo = first_photo(card_of(with_photo), tmp_path)
    assert photo is not None and photo.content_type == "image/jpeg"
    assert photo.path == tmp_path / str(with_photo.lifecycle.images[0].local_path)
    assert first_photo(card_of(key_post(2)), tmp_path) is None
    webp = key_post(3, root=tmp_path, photo="a1.webp")
    assert first_photo(card_of(webp), tmp_path) is None
    tall = key_post(4, root=tmp_path, photo="a1.jpg")
    media = tall.post.media[0].model_copy(update={"width": 100, "height": 2500})
    tall = KeyPost(tall.post.with_changes(media=[media]), tall.lifecycle, tall.seen, frozenset())
    assert first_photo(card_of(tall), tmp_path) is None  # a ratio over 20
    gone = key_post(5, root=tmp_path, photo="a1.jpg")
    (tmp_path / str(gone.lifecycle.images[0].local_path)).unlink()
    assert first_photo(card_of(gone), tmp_path) is None


# --- who is alerted, when (telegram.alerts.due_alerts) ---


def due(*found: KeyPost | Card, user=None, sent: set[str] | None = None) -> list[str]:
    built = [item if isinstance(item, Card) else card_of(item) for item in found]
    alerts = due_alerts(user or linked(), profile(), built, sent or set(), NOW)
    return [card.shown_id for card, _ in alerts]


def test_a_post_first_stored_after_linking_alerts_and_one_before_does_not() -> None:
    after, before = key_post(1), key_post(2, fetched=LINKED_AT - timedelta(minutes=1))
    assert due(after, before) == [after.listing_id]
    assert due(key_post(3, fetched=LINKED_AT)) == []


def test_a_bootstrap_runs_posts_never_alert() -> None:
    # A bootstrap run creates the store: every post in it is stored before anyone links (#357).
    bootstrap = [key_post(n, fetched=LINKED_AT - timedelta(days=2)) for n in range(1, 4)]
    assert due(*bootstrap) == []


def test_a_post_the_key_ties_to_an_earlier_one_never_alerts() -> None:
    earlier = key_post(1, fetched=LINKED_AT - timedelta(hours=1))
    rewritten = key_post(2, fetched=LINKED_AT + timedelta(hours=1))
    card = card_of(earlier, rewritten)
    assert card.shown_id == earlier.listing_id
    assert due(card) == []


def test_a_card_with_any_alerted_post_does_not_alert_again() -> None:
    later = key_post(1, posted=LINKED_AT + timedelta(minutes=30))
    older = key_post(2, posted=LINKED_AT + timedelta(minutes=10))
    card = card_of(later, older)
    assert card.shown_id == older.listing_id
    assert due(card, sent={later.listing_id}) == []
    assert due(card) == [older.listing_id]


def test_a_post_classified_outside_the_window_does_not_alert() -> None:
    assert due(key_post(1, classified=NOW - ALERT_WINDOW - timedelta(seconds=1))) == []
    assert due(key_post(2, classified=NOW - ALERT_WINDOW + timedelta(minutes=1))) != []


def test_an_unlinked_or_disabled_user_is_alerted_nothing() -> None:
    assert due(key_post(1), user=admin()) == []
    disabled = friend(2, "dana", "b" * 32).model_copy(
        update={"telegram_chat_id": 7, "telegram_linked_at": LINKED_AT, "disabled_at": NOW}
    )
    assert due(key_post(1), user=disabled) == []


def test_a_post_published_more_than_24_hours_before_the_pass_never_alerts() -> None:
    """Point 12 B (#473): after a pause the run brings older posts; they are collected, classified
    and stored after linking, and still never alert."""
    old = key_post(1, posted=NOW - PUBLISHED_WINDOW - timedelta(minutes=1))
    recent = key_post(2, posted=NOW - PUBLISHED_WINDOW + timedelta(minutes=1))
    assert due(old, recent) == [recent.listing_id]
    assert published_too_long_ago(old.post.posted_at, NOW)
    assert not published_too_long_ago(recent.post.posted_at, NOW)
    assert PUBLISHED_WINDOW == timedelta(hours=24)


def test_the_due_alerts_come_in_publication_order() -> None:
    late = key_post(1, posted=LINKED_AT + timedelta(hours=2))
    early = key_post(2, posted=LINKED_AT + timedelta(hours=1))
    assert due(late, early) == [early.listing_id, late.listing_id]


# --- the pass: sends, records, never twice ---


class RecordingNotifier:
    def __init__(self, fail_for: set[int] | None = None) -> None:
        self.sent: list[tuple[int, Alert]] = []
        self._fail_for = fail_for or set()

    def send(self, chat_id: int, alert: Alert) -> int:
        if chat_id in self._fail_for:
            raise TelegramError("sendMessage", 403, "Forbidden: bot was blocked by the user")
        self.sent.append((chat_id, alert))
        return len(self.sent)


@pytest.fixture
def userdata(tmp_path: Path) -> SqliteUserDataStore:
    store = SqliteUserDataStore(tmp_path / SQLITE_FILENAME)
    store.create_admin(linked(), new_profile(ADMIN_ID, NOW))
    return store


def a_pass(userdata, notifier, sleeps: list[float], root: Path) -> AlertPass:
    return AlertPass(
        userdata,
        notifier,
        AREAS,
        site_url=SITE,
        store_root=root,
        clock=lambda: NOW,
        sleep=sleeps.append,
    )


def sent_rows(path: Path) -> list[tuple[str, str]]:
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute("SELECT user_id, listing_id FROM sent_alerts ORDER BY rowid").fetchall()


def test_the_pass_sends_each_due_alert_once_and_records_it(
    userdata: SqliteUserDataStore, tmp_path: Path
) -> None:
    notifier: RecordingNotifier = RecordingNotifier()
    sleeps: list[float] = []
    first, second = key_post(1), key_post(2, posted=LINKED_AT + timedelta(hours=2))
    held = [card_of(first), card_of(second)]
    result = a_pass(userdata, notifier, sleeps, tmp_path).run(held)
    assert result.sent == 2 and [chat for chat, _ in notifier.sent] == [42, 42]
    assert sleeps == [SEND_GAP_SECONDS, SEND_GAP_SECONDS]
    assert sent_rows(tmp_path / SQLITE_FILENAME) == [
        (ADMIN_ID, first.listing_id),
        (ADMIN_ID, second.listing_id),
    ]
    assert a_pass(userdata, notifier, sleeps, tmp_path).run(held).sent == 0
    assert len(notifier.sent) == 2


def test_a_failed_send_records_nothing_and_the_next_pass_tries_again(
    userdata: SqliteUserDataStore, tmp_path: Path
) -> None:
    held = [card_of(key_post(1))]
    result = a_pass(userdata, RecordingNotifier({42}), [], tmp_path).run(held)
    assert result.sent == 0 and result.failed_users == (ADMIN_ID,)
    assert sent_rows(tmp_path / SQLITE_FILENAME) == []
    assert a_pass(userdata, RecordingNotifier(), [], tmp_path).run(held).sent == 1


def test_a_stop_ends_the_pass_between_two_sends(
    userdata: SqliteUserDataStore, tmp_path: Path
) -> None:
    notifier = RecordingNotifier()
    held = [card_of(key_post(1)), card_of(key_post(2))]
    stops = iter([False, False, True, True])
    a_pass(userdata, notifier, [], tmp_path).run(held, lambda: next(stops))
    assert len(notifier.sent) == 1


def test_the_pass_writes_nothing_on_a_post(userdata: SqliteUserDataStore, tmp_path: Path) -> None:
    member = key_post(1)
    before = (member.post.model_dump(), member.seen.listing.model_dump(), member.lifecycle)
    a_pass(userdata, RecordingNotifier(), [], tmp_path).run([card_of(member)])
    assert (member.post.model_dump(), member.seen.listing.model_dump(), member.lifecycle) == before
    with closing(sqlite3.connect(tmp_path / SQLITE_FILENAME)) as conn:
        tables = {n for (n,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "raw_posts" not in tables and "sent_alerts" in tables  # user data only
