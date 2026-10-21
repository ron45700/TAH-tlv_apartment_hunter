"""The bot (`PHASE_4.md` 4.3–4.8; DECISIONS.md #358, #364, #365, #452, #453, #456): linking in the
store and through the bot, the delay after failed codes, `/stop`, the report button's two flows,
the alert pass when the store changed, the site's linking endpoints, and the three commands.

Temporary stores only (`tests/test_web_writes.py`'s `TiedStore`: one card of two members and its
dedup A duplicate, one other card); every request goes to `FakeTelegram`. Invariants 12, 14 and 15
are checked after the writes.
"""

import io
import json
import sqlite3
import threading
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import CONFIG_ROOT, make_listing
from tests.test_gate_c_contracts import user as user_fields
from tests.test_gate_d import add, make_member, written
from tests.test_telegram_client import TOKEN, FakeTelegram
from tests.test_userdata_store import ADMIN_ID, admin
from tests.test_web import NOW
from tests.test_web_accounts import ADMIN_PASSWORD, HASHER, ORIGIN, Clock, write
from tests.test_web_writes import (  # noqa: F401  (fixtures)
    TiedStore,
    _event_loop_self_pipe,
    clock,
    ron,
    site,
)
from tlv_hunter.accounts import actions, linking
from tlv_hunter.accounts.tokens import secret_hash
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.contracts.sent_alert import SENT_ALERT_SCHEMA_VERSION, SentAlert
from tlv_hunter.contracts.telegram_link_code import (
    LINK_CODE_LIFETIME,
    TELEGRAM_LINK_CODE_SCHEMA_VERSION,
    TelegramLinkCode,
)
from tlv_hunter.contracts.user import User
from tlv_hunter.gate_d.candidates import Member
from tlv_hunter.jobs import bot as bot_job
from tlv_hunter.jobs import send_test_alert, telegram_menu
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.notify.alert import reference_area_words
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.telegram import bot as bot_module
from tlv_hunter.telegram.bot import ANSWERS, Bot, fields_keyboard, site_url_or_refusal
from tlv_hunter.telegram.callbacks import FIELDS, Callback, ref_of
from tlv_hunter.telegram.client import TelegramClient
from tlv_hunter.userdata.base import ChatLinkedElsewhere, LinkCodeNotUsable
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.app import create_app
from tlv_hunter.web.grouping import Grouping

SITE = "https://tlvapthunter.x.ts.net"
CHAT = 4242
POST_TABLES = ("raw_posts", "listings")


@pytest.fixture
def store(tmp_path: Path) -> TiedStore:
    # Under `data/store` of a repo root, as the jobs find it (`config/collection.yaml`).
    return TiedStore(tmp_path / "data" / "store")


def rows(path: Path, table: str) -> list[tuple]:
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()  # noqa: S608


def post_rows(store: TiedStore) -> dict[str, list[tuple]]:
    return {table: rows(store.db, table) for table in POST_TABLES}


def a_code(store: TiedStore, at=NOW) -> str:
    """A link code for Ron, as the site makes it: from his session."""
    signed = actions.sign_in(store.userdata, "ron", ADMIN_PASSWORD, at, hasher=HASHER)
    return linking.new_link_code(store.userdata, signed.token, at).code


class Harness:
    """A bot over the store and `FakeTelegram`, and the updates a phone would send."""

    def __init__(self, store: TiedStore, now: Clock) -> None:
        self.store, self.clock, self.fake = store, now, FakeTelegram()
        self.sleeps: list[float] = []
        grouping = Grouping(
            SqliteRepository(store.db, read_only=True), store.userdata.find_corrections, store.root
        )
        self.bot = Bot(
            TelegramClient(TOKEN, transport=self.fake, sleep=self.sleeps.append),
            SqliteRepository(store.db),
            store.userdata,
            grouping,
            reference_area_words(),
            site_url=SITE,
            store_root=store.root,
            clock=now,
            sleep=self.sleeps.append,
        )
        self._update = 0

    def say(self, text: str, chat: int = CHAT, kind: str = "private") -> None:
        self._update += 1
        self.bot.handle(
            {
                "update_id": self._update,
                "message": {
                    "message_id": self._update,
                    "date": 1,
                    "chat": {"id": chat, "type": kind},
                    "from": {"id": chat, "is_bot": False, "first_name": "R"},
                    "text": text,
                },
            }
        )

    def press(self, data: str, message_id: int = 77, chat: int = CHAT) -> None:
        self._update += 1
        self.bot.handle(
            {
                "update_id": self._update,
                "callback_query": {
                    "id": f"q{self._update}",
                    "from": {"id": chat, "is_bot": False, "first_name": "R"},
                    "chat_instance": "c",
                    "data": data,
                    "message": {
                        "message_id": message_id,
                        "date": 1,
                        "chat": {"id": chat, "type": "private"},
                    },
                },
            }
        )

    def texts(self) -> list[str]:
        return [params["text"] for params in self.fake.of("sendMessage")]

    def answers(self) -> list[str | None]:
        return [params.get("text") for params in self.fake.of("answerCallbackQuery")]

    def last_keyboard(self) -> list[list[dict[str, Any]]]:
        return self.fake.of("editMessageReplyMarkup")[-1]["reply_markup"]["inline_keyboard"]

    def link(self) -> None:
        self.say(f"/start {a_code(self.store)}")

    def ron(self) -> User:
        found = self.store.userdata.find_user_by_username("ron")
        assert found is not None
        return found


@pytest.fixture
def harness(store: TiedStore, clock: Clock) -> Harness:  # noqa: F811
    return Harness(store, clock)


# --- Gate F in the store (#453) ---


def test_a_version_1_user_reads_as_version_2_with_no_link() -> None:
    doc = User(**user_fields()).model_dump(mode="json")
    del doc["telegram_chat_id"], doc["telegram_linked_at"]
    read = User.from_stored_json(json.dumps({**doc, "schema_version": 1}))
    assert read.schema_version == 2 and read.telegram_chat_id is None
    with pytest.raises(ValueError):
        User.from_stored_json(json.dumps({**doc, "schema_version": 1, "telegram_chat_id": 1}))
    with pytest.raises(ValueError):
        User(**user_fields(telegram_chat_id=5))  # the chat and its time together


def test_a_code_links_once_within_15_minutes(tmp_path: Path) -> None:
    userdata = SqliteUserDataStore(tmp_path / SQLITE_FILENAME)
    userdata.create_admin(admin(), new_profile(ADMIN_ID, NOW))

    def code(name: str, at=NOW) -> str:
        userdata.add_link_code(
            TelegramLinkCode(
                schema_version=TELEGRAM_LINK_CODE_SCHEMA_VERSION,
                code_hash=secret_hash(name),
                user_id=ADMIN_ID,
                created_at=at,
                used_at=None,
            )
        )
        return secret_hash(name)

    first = code("first")
    linked = userdata.link_telegram(first, CHAT, NOW + timedelta(minutes=1))
    assert linked.telegram_chat_id == CHAT
    assert linked.telegram_linked_at == NOW + timedelta(minutes=1)
    with pytest.raises(LinkCodeNotUsable):
        userdata.link_telegram(first, CHAT, NOW + timedelta(minutes=2))
    late = code("late")
    with pytest.raises(LinkCodeNotUsable):
        userdata.link_telegram(late, CHAT, NOW + LINK_CODE_LIFETIME)
    with pytest.raises(LinkCodeNotUsable):
        userdata.link_telegram(secret_hash("never made"), CHAT, NOW)
    again = userdata.link_telegram(code("again"), CHAT, NOW + timedelta(minutes=5))
    assert again.telegram_linked_at == NOW + timedelta(minutes=1)  # the same chat keeps its time
    moved = userdata.link_telegram(code("moved"), CHAT + 1, NOW + timedelta(minutes=6))
    assert moved.telegram_chat_id == CHAT + 1  # one chat per user: the old one is left
    assert userdata.find_user_by_chat(CHAT) is None
    assert userdata.find_user_by_chat(CHAT + 1) == moved


def test_one_user_per_chat_and_no_link_for_a_disabled_user(store: TiedStore) -> None:
    userdata = store.userdata
    admin_token = actions.sign_in(userdata, "ron", ADMIN_PASSWORD, NOW, hasher=HASHER).token
    issued = actions.issue_key(userdata, admin_token, "dana", NOW)
    actions.sign_up(userdata, issued.key, "dana", "dana-password-1", NOW, hasher=HASHER)
    dana = actions.sign_in(userdata, "dana", "dana-password-1", NOW, hasher=HASHER)
    linking.link_chat(userdata, a_code(store), CHAT, NOW)
    danas = linking.new_link_code(userdata, dana.token, NOW).code
    with pytest.raises(actions.Refused) as refused:
        linking.link_chat(userdata, danas, CHAT, NOW)
    assert refused.value.reason == "chat_linked_elsewhere"
    with pytest.raises(ChatLinkedElsewhere):
        userdata.link_telegram(secret_hash(danas), CHAT, NOW)
    actions.disable_user(userdata, admin_token, dana.user_id, NOW)
    with pytest.raises(actions.Refused) as refused:
        linking.link_chat(userdata, danas, CHAT + 1, NOW)
    assert refused.value.reason == "code_not_usable"


def test_a_sent_alert_is_recorded_once(tmp_path: Path) -> None:
    userdata = SqliteUserDataStore(tmp_path / SQLITE_FILENAME)
    userdata.create_admin(admin(), new_profile(ADMIN_ID, NOW))
    record = SentAlert(
        schema_version=SENT_ALERT_SCHEMA_VERSION, user_id=ADMIN_ID, listing_id="a" * 64, sent_at=NOW
    )
    assert userdata.add_sent_alert(record) is True
    later = record.model_copy(update={"sent_at": NOW + timedelta(days=1)})
    assert userdata.add_sent_alert(later) is False
    assert userdata.sent_listing_ids(ADMIN_ID) == {"a" * 64}


def test_the_link_code_is_shown_once_and_stored_as_its_hash(store: TiedStore) -> None:
    signed = actions.sign_in(store.userdata, "ron", ADMIN_PASSWORD, NOW, hasher=HASHER)
    issued = linking.new_link_code(store.userdata, signed.token, NOW)
    assert linking.looks_like_code(issued.code)
    assert issued.link == f"https://t.me/tlv_apartment_hunter_bot?start={issued.code}"
    assert issued.expires_at == NOW + LINK_CODE_LIFETIME
    assert issued.code not in repr(issued)
    assert issued.code.encode() not in store.db.read_bytes()
    assert secret_hash(issued.code).encode() in store.db.read_bytes()
    with pytest.raises(actions.Refused):
        linking.new_link_code(store.userdata, "no such session", NOW)


# --- linking through the bot (point 5 A, #358) ---


def test_start_with_a_code_links_and_says_how_many_posts_match(harness: Harness) -> None:
    code = a_code(harness.store)
    harness.say(f"/start {code}")
    assert harness.ron().telegram_chat_id == CHAT
    assert harness.ron().telegram_linked_at == NOW
    (text,) = harness.texts()
    # The two current cards (the tied pair with its duplicate, and the other post) both show for
    # #268's new profile; the rejected, pending and archived posts are on no card.
    assert "<b>2</b> מודעות מתאימות כרגע להעדפות שלך" in text
    (sent,) = harness.fake.of("sendMessage")
    assert sent["reply_markup"] == {"inline_keyboard": [[{"text": "לאתר", "url": f"{SITE}/"}]]}
    assert not any(code.encode() in body for body in harness.fake.bodies)


def test_a_code_typed_by_hand_links_too(harness: Harness) -> None:
    harness.say(a_code(harness.store))
    assert harness.ron().telegram_chat_id == CHAT


def test_a_used_or_wrong_code_is_refused_and_five_failures_delay(harness: Harness) -> None:
    code = a_code(harness.store)
    harness.say(f"/start {code}")
    harness.say("/stop")
    harness.say(f"/start {code}")
    assert harness.texts()[-1] == bot_module.CODE_REFUSED
    for _ in range(4):
        harness.say("/start " + "x" * 32)
    harness.say("/start " + a_code(harness.store))
    assert harness.texts()[-1] == bot_module.CODE_DELAYED.format(seconds=30)
    assert harness.ron().telegram_chat_id is None
    harness.clock.now = NOW + timedelta(seconds=31)
    harness.say("/start " + a_code(harness.store, NOW + timedelta(seconds=31)))
    assert harness.ron().telegram_chat_id == CHAT


def test_an_unlinked_chat_gets_no_answer_and_a_group_is_ignored(harness: Harness) -> None:
    harness.say("hello")
    harness.say("/start")
    harness.say("/site")
    harness.say(f"/start {a_code(harness.store)}", kind="group")
    assert harness.fake.calls == []
    assert harness.ron().telegram_chat_id is None


def test_stop_unlinks_and_site_sends_the_site(harness: Harness) -> None:
    harness.link()
    harness.say("/site")
    keyboard = harness.fake.of("sendMessage")[-1]["reply_markup"]["inline_keyboard"]
    assert keyboard == [[{"text": "לאתר", "url": f"{SITE}/"}]]
    harness.say("anything")
    assert harness.texts()[-1] == bot_module.HELP
    harness.say("/stop")
    assert harness.texts()[-1] == bot_module.UNLINKED
    assert harness.ron().telegram_chat_id is None
    harness.say("anything")
    assert harness.texts()[-1] == bot_module.UNLINKED  # an unlinked chat: no answer


def test_start_sets_the_commands_and_checks_the_bot(harness: Harness) -> None:
    harness.bot.start()
    assert harness.fake.methods() == ["getMe", "getWebhookInfo", "setMyCommands"]
    harness.fake.queue("getWebhookInfo", 200, {"ok": True, "result": {"url": "https://hook"}})
    with pytest.raises(RuntimeError, match="webhook"):
        harness.bot.start()
    harness.fake.queue("getMe", 200, {"ok": True, "result": {"username": "someone_else_bot"}})
    with pytest.raises(RuntimeError, match="not @tlv_apartment_hunter_bot"):
        harness.bot.start()


def test_the_loop_reads_updates_with_the_offset_and_backs_off(harness: Harness) -> None:
    update = {
        "update_id": 10,
        "message": {
            "message_id": 1,
            "date": 1,
            "text": "hi",
            "chat": {"id": CHAT, "type": "private"},
        },
    }
    harness.fake.queue("getUpdates", 200, {"ok": True, "result": [update]})
    harness.fake.queue("getUpdates", 502, {"ok": False, "error_code": 502, "description": "x"})
    harness.bot.run(lambda: len(harness.fake.of("getUpdates")) >= 2)
    offsets = [params.get("offset") for params in harness.fake.of("getUpdates")]
    assert offsets == [None, 11]
    assert harness.sleeps == [5]


# --- the menu button follows the link (round 35, #470) ---

WEB_APP = {"type": "web_app", "text": "האתר", "web_app": {"url": f"{SITE}/"}}


def menu_calls(harness: Harness) -> list[dict[str, Any]]:
    return harness.fake.of("setChatMenuButton")


def test_a_linked_chat_gets_the_site_button_once_and_an_unlinked_one_gets_nothing(
    harness: Harness,
) -> None:
    harness.bot.sync_menus()
    assert harness.fake.calls == []
    harness.link()
    harness.bot.sync_menus()
    harness.bot.sync_menus()
    assert menu_calls(harness) == [{"chat_id": CHAT, "menu_button": WEB_APP}]


def test_the_loop_sets_the_button_for_a_chat_already_linked_before_its_first_poll(
    harness: Harness,
) -> None:
    linking.link_chat(harness.store.userdata, a_code(harness.store), CHAT, NOW)
    harness.bot.run(lambda: len(harness.fake.of("getUpdates")) >= 1)
    assert harness.fake.methods()[:2] == ["setChatMenuButton", "getUpdates"]
    assert menu_calls(harness) == [{"chat_id": CHAT, "menu_button": WEB_APP}]


def test_stop_and_the_sites_unlink_put_the_default_menu_back(harness: Harness) -> None:
    harness.link()
    harness.bot.sync_menus()
    harness.say("/stop")
    harness.bot.sync_menus()
    harness.bot.sync_menus()
    assert [call["menu_button"] for call in menu_calls(harness)] == [WEB_APP, {"type": "default"}]
    harness.link()  # the site's unlink below: the bot is told nothing, the store has no chat
    harness.bot.sync_menus()
    linking.unlink(harness.store.userdata, harness.ron().user_id)
    harness.bot.sync_menus()
    assert [call["menu_button"] for call in menu_calls(harness)][2:] == [
        WEB_APP,
        {"type": "default"},
    ]
    assert {call["chat_id"] for call in menu_calls(harness)} == {CHAT}


def test_a_refused_menu_call_is_tried_again_in_an_hour_not_at_every_poll(
    harness: Harness,
) -> None:
    harness.link()
    blocked = {"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked"}
    harness.fake.queue("setChatMenuButton", 403, blocked)
    harness.bot.sync_menus()
    harness.clock.now = NOW + timedelta(minutes=59)
    harness.bot.sync_menus()
    assert len(menu_calls(harness)) == 1
    harness.clock.now = NOW + timedelta(hours=1)
    harness.bot.sync_menus()
    harness.bot.sync_menus()
    assert [call["menu_button"] for call in menu_calls(harness)] == [WEB_APP, WEB_APP]


def test_the_menu_button_request_carries_the_chat_and_the_sites_address_only(
    harness: Harness,
) -> None:
    harness.link()
    harness.bot.sync_menus()
    (body,) = [
        sent
        for sent, call in zip(harness.fake.bodies, harness.fake.calls, strict=True)
        if call[0] == "setChatMenuButton"
    ]
    assert json.loads(body) == {"chat_id": CHAT, "menu_button": WEB_APP}
    assert harness.fake.urls[-1].endswith("/setChatMenuButton")


# --- the report button (point 11 A, #364) ---


def ref(store: TiedStore) -> str:
    return ref_of(min(store.active, store.tied))


def test_lied_asks_then_flags_every_member_as_the_linked_user(harness: Harness) -> None:
    store = harness.store
    harness.link()
    before = post_rows(store)
    harness.press(f"r:{ref(store)}")
    assert [b["text"] for b in harness.last_keyboard()[0]] == ["המודעה משקרת", "סיווג שגוי"]
    harness.press(f"l:{ref(store)}")
    assert harness.last_keyboard()[0][0]["callback_data"] == f"L:{ref(store)}"
    harness.press(f"L:{ref(store)}")
    for listing_id in (store.active, store.tied):
        lifecycle = store.repository.get_lifecycle(listing_id)
        assert lifecycle is not None and lifecycle.rejection_reason == "flagged"
        assert lifecycle.flagged_by == ADMIN_ID
    assert harness.answers() == [bot_module.CHOOSE, None, ANSWERS["flagged"]]
    assert all(row[0]["text"] != "דיווח" for row in harness.last_keyboard())
    assert post_rows(store) == before  # invariant 14: no RawPost, no Listing written
    harness.press(f"L:{ref(store)}")
    assert harness.answers()[-1] == ANSWERS["gone"]  # the card left the list


def test_wrong_classification_with_fields_and_a_note(harness: Harness) -> None:
    store = harness.store
    harness.link()
    before = post_rows(store)
    price = FIELDS.index("price")
    harness.press(f"w:{ref(store)}:0")
    assert len(harness.last_keyboard()) == len(FIELDS) // 2 + 1
    harness.press(Callback("s", ref(store), 0).data())
    assert harness.answers()[-1] == ANSWERS["choose_fields"]
    harness.press(Callback("t", ref(store), 0, price).data())
    toggled = [b for row in harness.last_keyboard() for b in row if b["text"].startswith("✓ ")]
    assert [b["text"] for b in toggled] == ["✓ מחיר"]
    harness.press(Callback("s", ref(store), 1 << price).data())
    assert harness.texts()[-1].startswith("אפשר להוסיף הערה")
    harness.say("the price is 5,500 & not 5,000")
    (report,) = store.userdata.find_reports()
    assert report.fields == ["price"] and report.note == "the price is 5,500 & not 5,000"
    assert report.listing_id == min(store.active, store.tied)  # the shown post only (#300)
    assert report.reported_by == ADMIN_ID
    assert harness.texts()[-1] in (ANSWERS["reported"], ANSWERS["reported_removed"])
    assert post_rows(store) == before
    assert not any(b"the price is" in body for body in harness.fake.bodies)  # never echoed


def test_wrong_classification_skipping_the_note_and_a_second_report(harness: Harness) -> None:
    store = harness.store
    harness.link()
    mask = 1 << FIELDS.index("rooms")
    harness.press(Callback("s", ref(store), mask).data())
    harness.press(Callback("k", ref(store), mask).data())
    (report,) = store.userdata.find_reports()
    assert report.fields == ["rooms"] and report.note is None
    harness.press(Callback("s", ref(store), mask).data())
    harness.press(Callback("k", ref(store), mask).data())
    assert harness.answers()[-1] in (ANSWERS["already_reported"], ANSWERS["gone"])
    assert len(store.userdata.find_reports()) == 1


def test_a_note_over_500_characters_is_asked_again(harness: Harness) -> None:
    harness.link()
    mask = 1 << FIELDS.index("price")
    harness.press(Callback("s", ref(harness.store), mask).data())
    harness.say("א" * 501)
    assert harness.texts()[-1] == bot_module.NOTE_TOO_LONG.format(limit=500)
    assert harness.store.userdata.find_reports() == []


def test_every_callback_is_answered_also_unlinked_unknown_or_foreign(harness: Harness) -> None:
    harness.press(f"r:{ref(harness.store)}")  # not linked
    harness.link()
    harness.press("r:" + "0" * 16)  # no such post
    harness.press("garbage")
    assert harness.answers() == [ANSWERS["not_linked"], ANSWERS["gone"], None]


def test_the_fields_keyboard_marks_the_chosen_fields() -> None:
    keyboard = fields_keyboard("a" * 16, 0b11)
    assert keyboard[0][0].text.startswith("✓ ") and keyboard[0][1].text.startswith("✓ ")
    assert not keyboard[1][0].text.startswith("✓ ")
    assert [b.text for b in keyboard[-1]] == ["שליחה", "ביטול"]


# --- the alert pass when the store changed (point 3 A) ---


def new_post(store: TiedStore, n: int, fetched) -> str:
    member = make_member(n, price=[5000], rooms=3.0, areas=[30])
    post = member.post.with_changes(fetched_at=fetched, posted_at=fetched)
    record = make_listing(
        post.listing_id,
        apartment_kind=written("whole_apartment"),
        price=written([5000]),
        price_source="text",
        areas=[30],
        classified_at=fetched,
    )
    lifecycle = member.lifecycle.model_copy(update={"last_published_at": fetched})
    add(store.repository, Member(post, lifecycle, record))
    return post.listing_id


def test_a_new_matching_post_alerts_the_linked_user_once(harness: Harness) -> None:
    store = harness.store
    harness.link()
    harness.bot.alert_if_moved()
    assert len(harness.fake.of("sendMessage")) == 1  # the link's message: nothing new since
    fresh = new_post(store, 21, NOW + timedelta(minutes=5))
    harness.clock.now = NOW + timedelta(minutes=10)
    harness.bot.alert_if_moved()
    (sent,) = harness.fake.of("sendMessage")[1:]
    assert sent["chat_id"] == CHAT and sent["text"].startswith("- <b>דירה שלמה</b>")
    assert store.userdata.sent_listing_ids(ADMIN_ID) == {fresh}
    harness.bot.alert_if_moved()
    new_post(store, 22, NOW - timedelta(days=1))  # stored before the link: never alerted
    harness.bot.alert_if_moved()
    assert len(harness.fake.of("sendMessage")) == 2


def test_the_user_and_its_secrets_never_reach_telegram(harness: Harness) -> None:
    store = harness.store
    harness.link()
    new_post(store, 21, NOW + timedelta(minutes=5))
    harness.clock.now = NOW + timedelta(minutes=10)
    harness.bot.alert_if_moved()
    harness.press(f"r:{ref(store)}")
    user = harness.ron()
    for body in harness.fake.bodies:
        text = body.decode("utf-8", "replace")
        assert user.username not in text and user.user_id not in text
        assert user.password_hash not in text
    assert all(url.startswith(f"https://api.telegram.org/bot{TOKEN}/") for url in harness.fake.urls)


# --- the site's linking endpoints ---


def test_the_preferences_page_makes_a_code_and_unlinks(
    site,  # noqa: F811
    ron: TestClient,  # noqa: F811
    store: TiedStore,
) -> None:
    assert ron.get("/api/telegram").json() == {"linked": False, "linked_at": None}
    other_origin = write(ron, "POST", "/api/telegram/link", {}, origin="https://elsewhere")
    assert other_origin.status_code == 403
    response = write(ron, "POST", "/api/telegram/link", {})
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["link"] == f"https://t.me/tlv_apartment_hunter_bot?start={body['code']}"
    linking.link_chat(store.userdata, body["code"], CHAT, NOW)
    linked = ron.get("/api/telegram").json()
    assert linked["linked"] is True and linked["linked_at"] == NOW.isoformat()
    assert write(ron, "DELETE", "/api/telegram", {}).json()["linked"] is False
    assert store.userdata.find_user_by_chat(CHAT) is None


def test_a_guest_cannot_link(site) -> None:  # noqa: F811
    guest = TestClient(create_app(site), base_url=ORIGIN)
    assert guest.get("/api/telegram").status_code == 401
    assert write(guest, "POST", "/api/telegram/link", {}).status_code == 401


# --- the commands ---


def environ(**changes: str) -> dict[str, str]:
    return {"TELEGRAM_BOT_TOKEN": TOKEN, "SITE_URL": SITE, **changes}


def repo_of(store: TiedStore) -> Path:
    return store.root.parent.parent


def test_the_bot_command_refuses_without_its_settings_or_a_store(tmp_path: Path) -> None:
    for env, words in [
        ({"SITE_URL": SITE}, "TELEGRAM_BOT_TOKEN is not set"),
        (environ(SITE_URL="http://127.0.0.1:8000"), "SITE_URL must be"),
        (environ(SITE_URL=f"{SITE}/post"), "SITE_URL must be"),
        (environ(), "no store at"),
    ]:
        log = io.StringIO()
        code = bot_job.main(
            [], environ=env, repo_root=tmp_path, transport=FakeTelegram(), stream=log
        )
        assert code == 1 and words in log.getvalue()
        assert TOKEN not in log.getvalue()


def test_the_bot_command_starts_runs_and_stops(store: TiedStore) -> None:
    stop = threading.Event()
    stop.set()
    fake, log = FakeTelegram(), io.StringIO()
    code = bot_job.main(
        [],
        environ=environ(),
        repo_root=repo_of(store),
        config_root=CONFIG_ROOT,
        transport=fake,
        stream=log,
        stop=stop,
    )
    assert code == 0 and fake.methods() == ["getMe", "getWebhookInfo", "setMyCommands"]
    assert "bot started" in log.getvalue() and TOKEN not in log.getvalue()


def test_site_url_is_https_with_no_path() -> None:
    assert site_url_or_refusal(f" {SITE}/ ") == SITE
    for wrong in ("", "http://x", "https://", "https://x/y", "https://a b"):
        with pytest.raises(ValueError):
            site_url_or_refusal(wrong)


def linked_ron(store: TiedStore) -> None:
    linking.link_chat(store.userdata, a_code(store), CHAT, NOW)


def run_test_alert(store: TiedStore, *args: str) -> tuple[int, str, FakeTelegram]:
    fake, out = FakeTelegram(), io.StringIO()
    code = send_test_alert.main(
        list(args),
        environ=environ(),
        repo_root=repo_of(store),
        transport=fake,
        clock=lambda: NOW,
        stream=out,
    )
    return code, out.getvalue(), fake


def test_send_test_alert_sends_as_a_real_one_and_writes_nothing(store: TiedStore) -> None:
    linked_ron(store)
    before = store.db.read_bytes()
    code, out, fake = run_test_alert(store, "--listing", store.other[:10])
    assert code == 0, out
    (sent,) = fake.of("sendMessage")
    assert sent["chat_id"] == CHAT
    report = sent["reply_markup"]["inline_keyboard"][-1][0]
    assert report["callback_data"] == f"r:{store.other[:16]}"
    assert "kind_unclear" in out  # the test posts' kind is not written: never a real alert
    assert rows(store.db, "sent_alerts") == []
    assert store.db.read_bytes() == before


def test_send_test_alert_finds_a_card_by_any_of_its_posts_and_refuses_otherwise(
    store: TiedStore,
) -> None:
    code, out, _ = run_test_alert(store, "--listing", store.other[:8])
    assert code == 1 and "not linked" in out
    linked_ron(store)
    code, out, _ = run_test_alert(store, "--listing", store.duplicate[:12])
    assert code == 0 and min(store.active, store.tied) in out  # the duplicate's card
    assert run_test_alert(store, "--listing", "abc")[0] == 1
    assert run_test_alert(store, "--listing", "f" * 12)[1].startswith("refused: no post")
    refused = run_test_alert(store, "--listing", store.other[:8], "--user", "nobody")[1]
    assert refused == "refused: no such user\n"


def test_telegram_menu_sets_the_spikes_button_on_one_chat_and_puts_back_the_default(
    store: TiedStore,
) -> None:
    linked_ron(store)

    def run(flag: str) -> FakeTelegram:
        fake = FakeTelegram()
        code = telegram_menu.main(
            [flag],
            environ=environ(),
            repo_root=repo_of(store),
            transport=fake,
            stream=io.StringIO(),
        )
        assert code == 0
        return fake

    web_app = {"type": "web_app", "text": "האתר", "web_app": {"url": f"{SITE}/"}}
    assert run("--spike").of("setChatMenuButton") == [{"chat_id": CHAT, "menu_button": web_app}]
    assert run("--default").of("setChatMenuButton") == [
        {"chat_id": CHAT, "menu_button": {"type": "default"}}
    ]
    assert run("--show").of("setChatMenuButton") == []
