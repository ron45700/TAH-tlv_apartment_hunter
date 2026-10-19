"""The bot service (`PHASE_4.md` 4.3–4.7, points 2, 3, 5, 9, 11; DECISIONS.md #356, #358, #364,
#365, #452). Wiring, like `pipeline.py`.

It listens by long polling (`getUpdates`, #56), and between two polls it looks at the store
generation counter (#316): when it moved, the grouping is computed again and the alert pass runs
(`alerts.py`). It is a store writer beside the site and the job commands (#260): the link fields
of a `User` and a code's use (`accounts/linking.py`), the sent-alert records, and the report
button's flag or report, written by the site's own functions (`web/writes.py`: compare and set, the
flag on every member of the card, the report on the shown post, #300). Never a `RawPost` or a
`Listing` (invariant 14), nothing per user on a post (invariant 12).

Private chats only; a chat that is not linked gets an answer only to `/start <code>` or a code
typed by hand (point 5). What a user writes (a note) is never logged. Every callback is answered
(`answerCallbackQuery`), also when nothing else is done. No username, name or phone of a user is
ever sent to Telegram (invariant 15): the bot's own words, and the chat's id, only.
"""

import html
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from tlv_hunter.accounts import linking
from tlv_hunter.accounts.actions import Refused
from tlv_hunter.contracts.classification_report import NOTE_LIMIT
from tlv_hunter.contracts.user import User
from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.jobs.common import describe
from tlv_hunter.notify.alert import alert_keyboard
from tlv_hunter.notify.telegram import TelegramNotifier
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.telegram import callbacks
from tlv_hunter.telegram.alerts import AlertPass
from tlv_hunter.telegram.callbacks import Callback
from tlv_hunter.telegram.client import BOT_USERNAME, Button, Keyboard, TelegramClient, TelegramError
from tlv_hunter.telegram.digest import digest_due, digest_messages, window_start
from tlv_hunter.telegram.watch import Watch
from tlv_hunter.userdata.base import OpenReportExists, UserDataStore
from tlv_hunter.web.grouping import Grouping
from tlv_hunter.web.writes import REPORT_LABELS, flag_card, report_post

logger = logging.getLogger(__name__)

POLL_SECONDS = 25
NOTE_WAIT = timedelta(minutes=15)
BACKOFF_SECONDS = (5, 15, 60)
MENU_RETRY = timedelta(hours=1)
MENU_TEXT = "האתר"
DEFAULT_MENU: dict[str, Any] = {"type": "default"}


def site_menu_button(site_url: str) -> dict[str, Any]:
    """The Web App menu button every linked chat carries (the spike's, T5, #457)."""
    return {"type": "web_app", "text": MENU_TEXT, "web_app": {"url": site_url.rstrip("/") + "/"}}


COMMANDS = (
    ("site", "פתיחת האתר"),
    ("stop", "ביטול הקישור וההתראות"),
)

# What the bot says (Hebrew, as the site).
LINKED = (
    "החשבון קושר לטלגרם. ✅\n"
    "<b>{count}</b> מודעות מתאימות כרגע להעדפות שלך.\n"
    "מעכשיו תגיע לכאן התראה על כל מודעה חדשה שמתאימה להעדפות."
)
ALREADY_LINKED = "הצ'אט הזה כבר מקושר. התראות יגיעו לכאן. /stop לביטול הקישור."
CODE_REFUSED = "הקוד לא תקף או שפג תוקפו. צרו קוד חדש בעמוד ההעדפות באתר."
CODE_DELAYED = "יותר מדי ניסיונות. נסו שוב בעוד {seconds} שניות."
CHAT_ELSEWHERE = (
    "הצ'אט הזה מקושר לחשבון אחר באתר. שלחו /stop כדי לבטל את הקישור הקיים, ואז נסו שוב."
)
UNLINKED = "הקישור בוטל. לא יישלחו לכאן עוד התראות. אפשר לקשר שוב מעמוד ההעדפות באתר."
HELP = "התראות על מודעות חדשות יגיעו לכאן. /site לאתר, /stop לביטול הקישור."
SITE_WORDS = "האתר:"
FAILURE_HEAD = "⚠️ <b>התראת תקלה באיסוף</b>"
BUTTON_TO_SITE = "לאתר"

CHOOSE = "מה לא בסדר במודעה?"
BUTTON_LIED = "המודעה משקרת"
BUTTON_WRONG = "סיווג שגוי"
BUTTON_BACK = "חזרה"
BUTTON_CONFIRM_LIED = "כן, המודעה משקרת"
BUTTON_CANCEL = "ביטול"
BUTTON_SEND = "שליחה"
BUTTON_SKIP = "דילוג"
NOTE_PROMPT = "אפשר להוסיף הערה למנהל: כתבו אותה כאן בהודעה אחת (עד {limit} תווים), או לחצו דילוג."
NOTE_TOO_LONG = "ההערה ארוכה מ-{limit} תווים. כתבו הערה קצרה יותר, או לחצו דילוג."

ANSWERS = {
    "not_linked": "הצ'אט הזה לא מקושר לחשבון.",
    "password_due": "יש להחליף סיסמה באתר לפני דיווח.",
    "gone": "המודעה כבר לא ברשימה.",
    "choose_fields": "בחרו לפחות שדה אחד.",
    "flagged": "תודה. המודעה סומנה כמשקרת והוסרה מהרשימה.",
    "flag_partial": "סומנו {written} מתוך {of} פרסומים. נסו שוב בעוד רגע.",
    "already_reported": "כבר דיווחת על המודעה הזאת, והדיווח עוד פתוח.",
    "reported_removed": "תודה. הדיווח נשלח, והמודעה הוסרה מהרשימה עד שהמנהל יבדוק אותה.",
    "reported": "תודה. הדיווח נשלח למנהל.",
    "note_now": "כתבו את ההערה בהודעה אחת, או לחצו דילוג.",
}


@dataclass(frozen=True)
class PendingNote:
    """A "wrong classification" waiting for its optional note, in this process only."""

    callback: Callback
    alert_message_id: int | None
    prompt_message_id: int | None
    until: datetime


class Bot:
    def __init__(
        self,
        client: TelegramClient,
        posts: SqliteRepository,
        userdata: UserDataStore,
        grouping: Grouping,
        area_names: Mapping[int, str],
        *,
        site_url: str,
        store_root: Path,
        clock: Callable[[], datetime],
        sleep: Callable[[float], None],
        watch: Watch | None = None,
    ) -> None:
        self._client = client
        self._watch = watch
        self._problems_sent: set[str] = set()
        self._last_digest: datetime | None = None
        self._posts = posts
        self._userdata = userdata
        self._grouping = grouping
        self._site_url = site_url.rstrip("/")
        self._clock = clock
        self._sleep = sleep
        self._alerts = AlertPass(
            userdata,
            TelegramNotifier(client),
            area_names,
            site_url=site_url,
            store_root=store_root,
            clock=clock,
            sleep=sleep,
        )
        self._attempts = linking.CodeAttempts()
        self._pending: dict[int, PendingNote] = {}
        self._offset: int | None = None
        self._alerted_generation: int | None = None
        self._menu_chats: set[int] = set()
        self._menu_retry_at: dict[int, datetime] = {}

    # --- the service ---

    def start(self) -> None:
        """The token works, it is our bot, no webhook is set (getUpdates would refuse), and the
        commands are set."""
        me = self._client.get_me()
        if me.get("username") != BOT_USERNAME:
            raise RuntimeError(f"the token is not @{BOT_USERNAME}'s")
        if self._client.get_webhook_info().get("url"):
            raise RuntimeError("a webhook is set: getUpdates does not work while one is")
        self._client.set_my_commands(COMMANDS)
        logger.info("bot started: @%s", BOT_USERNAME)

    def run(self, should_stop: Callable[[], bool]) -> None:
        failures = 0
        while not should_stop():
            self.sync_menus()
            self.alert_if_moved(should_stop)
            self.watch_collection()
            if should_stop():
                break
            try:
                updates = self._client.get_updates(self._offset, POLL_SECONDS)
            except TelegramError as error:
                wait = BACKOFF_SECONDS[min(failures, len(BACKOFF_SECONDS) - 1)]
                failures += 1
                logger.warning("getUpdates failed (%s); again in %d s", error, wait)
                self._sleep(wait)
                continue
            failures = 0
            for update in updates:
                self._offset = int(update["update_id"]) + 1
                self.handle(update)
        logger.info("bot stopped")

    def sync_menus(self) -> None:
        """The menu button follows the link. A linked chat gets the site's Web App button; a chat
        this process gave it that is no longer linked (`/stop`, or the site's unlink, which has no
        token) gets Telegram's default back. Run before each poll, so the first pass after a start
        sets it for every chat already linked, and a link shows it within one poll. The state is
        this process's only (no record, invariant 1): a chat unlinked on the site while the bot was
        down keeps the button, which opens the site and does nothing else. A failed call is tried
        again in an hour, not at every poll (a user who blocked the bot answers 403 for ever)."""
        now = self._clock()
        try:
            linked = {
                user.telegram_chat_id
                for user in self._userdata.list_users()
                if user.telegram_chat_id is not None
            }
        except Exception as error:
            logger.error("menu sync failed: %s", describe(error))
            return
        for chat_id in sorted(linked - self._menu_chats):
            self._set_menu(chat_id, site_menu_button(self._site_url), now, True)
        for chat_id in sorted(self._menu_chats - linked):
            self._set_menu(chat_id, DEFAULT_MENU, now, False)

    def _set_menu(self, chat_id: int, button: Mapping[str, Any], now: datetime, site: bool) -> None:
        if self._menu_retry_at.get(chat_id, now) > now:
            return
        try:
            self._client.set_chat_menu_button(chat_id, button)
        except TelegramError as error:
            self._menu_retry_at[chat_id] = now + MENU_RETRY
            logger.warning("menu button not set: %s", error)
            return
        self._menu_retry_at.pop(chat_id, None)
        if site:
            self._menu_chats.add(chat_id)
        else:
            self._menu_chats.discard(chat_id)

    def watch_collection(self) -> None:
        """Phase 5 (points 7, 10; #471): the failure alert, once per problem until it clears, and
        the daily digest at 08:00 Israel time, both to the admin's chat only. A failed send is
        tried again at the next poll."""
        if self._watch is None:
            return
        try:
            now = self._clock()
            chat = self._watch.admin_chat()
            found = self._watch.problems(now)
            standing = {problem.key for problem in found}
            self._problems_sent &= standing  # a problem that cleared alerts again if it returns
            new = [problem for problem in found if problem.key not in self._problems_sent]
            if new and chat is not None:
                lines = [FAILURE_HEAD, *(f"• {html.escape(problem.text)}" for problem in new)]
                self._say(chat, "\n".join(lines))
                self._problems_sent |= {problem.key for problem in new}
                logger.info("failure alert sent: %s", ", ".join(p.key for p in new))
            settings = self._watch.settings()
            last = self._last_digest if settings is None else settings.last_digest_at
            if chat is not None and digest_due(last, now, self._watch.zone):
                digest = self._watch.digest(window_start(last, now), now)
                for text in digest_messages(digest, self._watch.zone):
                    self._say(chat, text)
                self._last_digest = now
                self._watch.runs.set_last_digest(now)
                logger.info("digest sent")
        except Exception as error:
            logger.error("collection watch failed: %s", describe(error))

    def alert_if_moved(self, should_stop: Callable[[], bool] = lambda: False) -> None:
        """The alert pass, when the store changed since the last one that finished."""
        try:
            snapshot = self._grouping.current().snapshot
            if snapshot.generation == self._alerted_generation:
                return
            self._alerts.run(snapshot.cards, should_stop)
            if not should_stop():
                self._alerted_generation = snapshot.generation
        except Exception as error:
            logger.error("alert pass failed: %s", describe(error))

    def handle(self, update: Mapping[str, Any]) -> None:
        try:
            if "message" in update:
                self._message(update["message"])
            elif "callback_query" in update:
                self._callback(update["callback_query"])
        except Exception as error:
            logger.error("update %s failed: %s", update.get("update_id"), describe(error))

    # --- messages ---

    def _message(self, message: Mapping[str, Any]) -> None:
        chat = message.get("chat") or {}
        if chat.get("type") != "private" or not isinstance(chat.get("id"), int):
            return
        chat_id: int = chat["id"]
        text = (message.get("text") or "").strip()
        command, _, argument = text.partition(" ")
        command = command.split("@", 1)[0]
        user = self._userdata.find_user_by_chat(chat_id)
        if command == "/start":
            if argument.strip():
                self._link(chat_id, argument.strip())
            elif user is not None:
                self._say(chat_id, ALREADY_LINKED)
            return
        if user is None:
            if linking.looks_like_code(text):
                self._link(chat_id, text)
            return
        if command == "/stop":
            linking.unlink(self._userdata, user.user_id)
            self._pending.pop(chat_id, None)
            self._say(chat_id, UNLINKED)
            return
        if command == "/site":
            self._say(chat_id, SITE_WORDS, [[Button(BUTTON_TO_SITE, url=self._site_url + "/")]])
            return
        pending = self._pending.get(chat_id)
        if pending is not None and pending.until > self._clock() and not text.startswith("/"):
            if len(text) > NOTE_LIMIT:
                self._say(chat_id, NOTE_TOO_LONG.format(limit=NOTE_LIMIT))
                return
            self._finish_report(chat_id, user, pending, text or None)
            return
        self._say(chat_id, HELP)

    def _link(self, chat_id: int, code: str) -> None:
        now = self._clock()
        wait = self._attempts.wait_left(chat_id, now)
        if wait is not None:
            self._say(chat_id, CODE_DELAYED.format(seconds=wait))
            return
        try:
            user = linking.link_chat(self._userdata, code, chat_id, now)
        except Refused as refusal:
            if refusal.reason == "chat_linked_elsewhere":
                self._say(chat_id, CHAT_ELSEWHERE)
                return
            self._attempts.failed(chat_id, now)
            self._say(chat_id, CODE_REFUSED)
            return
        self._attempts.succeeded(chat_id)
        self._say(
            chat_id,
            LINKED.format(count=self.matching_count(user)),
            [[Button(BUTTON_TO_SITE, url=self._site_url + "/")]],
        )

    def matching_count(self, user: User) -> int:
        """#358's N: the current cards the user's saved profile shows, as the site counts them."""
        profile = self._userdata.get_profile(user.user_id)
        if profile is None:
            return 0
        now = self._clock()
        cards = self._grouping.current().snapshot.cards
        return sum(1 for card in cards if evaluate(card.shown.seen, profile, now).shown)

    # --- the report button (point 11 A) ---

    def _callback(self, query: Mapping[str, Any]) -> None:
        answer: str | None = None
        try:
            answer = self._callback_answer(query)
        finally:
            try:
                self._client.answer_callback(str(query.get("id", "")), answer)
            except TelegramError as error:
                logger.warning("answerCallbackQuery failed: %s", error)

    def _callback_answer(self, query: Mapping[str, Any]) -> str | None:
        message = query.get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") != "private" or not isinstance(chat.get("id"), int):
            return None
        chat_id: int = chat["id"]
        found_id = message.get("message_id")
        message_id = found_id if isinstance(found_id, int) else None
        parsed = callbacks.parse(str(query.get("data", "")))
        if parsed is None:
            return None
        user = self._userdata.find_user_by_chat(chat_id)
        if user is None or user.disabled_at is not None:
            return ANSWERS["not_linked"]
        if user.must_change_password:
            return ANSWERS["password_due"]
        card = self._card(parsed.ref)
        if card is None:
            return ANSWERS["gone"]

        def edit(keyboard: Keyboard) -> None:
            self._edit(chat_id, message_id, keyboard)

        ref = parsed.ref
        match parsed.action:
            case "r":
                edit(
                    [
                        [
                            Button(BUTTON_LIED, callback_data=Callback("l", ref).data()),
                            Button(BUTTON_WRONG, callback_data=Callback("w", ref).data()),
                        ],
                        [Button(BUTTON_BACK, callback_data=Callback("b", ref).data())],
                    ]
                )
                return CHOOSE
            case "l":
                edit(
                    [
                        [Button(BUTTON_CONFIRM_LIED, callback_data=Callback("L", ref).data())],
                        [Button(BUTTON_CANCEL, callback_data=Callback("b", ref).data())],
                    ]
                )
                return None
            case "L":
                result = flag_card(self._posts, card, user.user_id, self._clock(), None)
                edit(alert_keyboard(card, self._site_url, report=False))
                if not result.written:
                    return ANSWERS["gone"]
                if result.not_written:
                    return ANSWERS["flag_partial"].format(
                        written=len(result.written), of=len(card.canonical_ids)
                    )
                return ANSWERS["flagged"]
            case "w" | "t":
                mask = callbacks.toggled(parsed) if parsed.action == "t" else parsed.mask
                edit(fields_keyboard(ref, mask))
                return None
            case "s":
                if not parsed.mask:
                    return ANSWERS["choose_fields"]
                edit(alert_keyboard(card, self._site_url))
                skip = Callback("k", ref, parsed.mask).data()
                prompt = self._say(
                    chat_id,
                    NOTE_PROMPT.format(limit=NOTE_LIMIT),
                    [[Button(BUTTON_SKIP, callback_data=skip)]],
                )
                self._pending[chat_id] = PendingNote(
                    callback=parsed,
                    alert_message_id=message_id,
                    prompt_message_id=prompt,
                    until=self._clock() + NOTE_WAIT,
                )
                return ANSWERS["note_now"]
            case "k":
                pending = self._pending.get(chat_id)
                if pending is None or pending.callback.ref != ref:
                    # The bot restarted since "send": the skip button carries the fields itself.
                    pending = PendingNote(parsed, None, message_id, self._clock())
                return self._finish_report(chat_id, user, pending, None)
            case "b":
                edit(alert_keyboard(card, self._site_url))
                return None
        return None

    def _finish_report(
        self, chat_id: int, user: User, pending: PendingNote, note: str | None
    ) -> str:
        """The "wrong classification" report written as the linked user; its outcome said in the
        chat and returned for the callback's answer."""
        self._pending.pop(chat_id, None)
        self._edit(chat_id, pending.prompt_message_id, [])
        card = self._card(pending.callback.ref)
        if card is None:
            words = ANSWERS["gone"]
        else:
            try:
                result = report_post(
                    self._posts,
                    self._userdata,
                    card,
                    user.user_id,
                    list(pending.callback.fields),
                    note,
                    self._clock(),
                )
            except OpenReportExists:
                words = ANSWERS["already_reported"]
            else:
                words = ANSWERS["reported_removed" if result.removed else "reported"]
            self._edit(
                chat_id,
                pending.alert_message_id,
                alert_keyboard(card, self._site_url, report=False),
            )
        self._say(chat_id, words)
        return words

    def _card(self, ref: str) -> Card | None:
        """The one current card holding a post whose id starts with `ref`; `None` for none, or
        more than one (point 11)."""
        snapshot = self._grouping.current().snapshot
        found = {
            id(card): card
            for listing_id, card in snapshot.card_of.items()
            if listing_id.startswith(ref)
        }
        return next(iter(found.values())) if len(found) == 1 else None

    # --- sending ---

    def _say(self, chat_id: int, text: str, keyboard: Keyboard | None = None) -> int:
        sent = self._client.send_message(chat_id, text, keyboard)
        return int(sent["message_id"])

    def _edit(self, chat_id: int, message_id: int | None, keyboard: Keyboard) -> None:
        if message_id is None:
            return
        try:
            self._client.edit_keyboard(chat_id, message_id, keyboard)
        except TelegramError as error:
            # "message is not modified", or a message too old to edit: the answer still goes.
            logger.info("keyboard not edited: %s", error)


def fields_keyboard(ref: str, mask: int) -> Keyboard:
    """The reportable fields as toggles, two to a row, then "send" and "cancel"."""
    buttons = [
        Button(
            ("✓ " if mask >> index & 1 else "") + REPORT_LABELS[name],
            callback_data=Callback("t", ref, mask, index).data(),
        )
        for index, name in enumerate(callbacks.FIELDS)
    ]
    rows: list[list[Button]] = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append(
        [
            Button(BUTTON_SEND, callback_data=Callback("s", ref, mask).data()),
            Button(BUTTON_CANCEL, callback_data=Callback("b", ref).data()),
        ]
    )
    return rows


def site_url_or_refusal(value: str) -> str:
    """`SITE_URL`: the site's own `https://` address, no path (the alerts' buttons open it)."""
    value = value.strip().rstrip("/")
    host = value.removeprefix("https://")
    if not value.startswith("https://") or not host or "/" in host or " " in host:
        raise ValueError("SITE_URL must be the site's https:// address, with no path")
    return value
