"""Linking a Telegram chat to a user (`PHASE_4.md` 4.4, point 5 A; SCHEMA.md, Gate F; DECISIONS.md
#452, #453; `BASELINE.md` §10: "Telegram is linked by a code the site shows and the user sends to
the bot").

The site makes a one-time code for the signed-in user (`new_link_code`) and shows it once, in the
deep link `https://t.me/tlv_apartment_hunter_bot?start=<code>`; the store keeps its SHA-256. The
bot receives `/start <code>` (or the code typed by hand) and links the chat (`link_chat`). Single
use, valid for 15 minutes; one chat per user and one user per chat. Unlinking: the preferences page
or `/stop` (`unlink`). A refusal is `actions.Refused`, its message only its reason: never a code or
a hash. The log lines name `user_id` only.

Failed codes are delayed as failed sign-ins are (#264): from the 5th consecutive failure in a chat,
an attempt within 30 seconds of the last is refused without a look (`CodeAttempts`, in the bot's
memory: no record holds it).
"""

import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from tlv_hunter.accounts.actions import (
    FAILURES_BEFORE_DELAY,
    SIGN_IN_DELAY,
    STORE_ATTEMPTS,
    Refused,
    _signed_in,
)
from tlv_hunter.accounts.tokens import new_link_code as _new_code
from tlv_hunter.accounts.tokens import secret_hash
from tlv_hunter.contracts.telegram_link_code import (
    LINK_CODE_LIFETIME,
    TELEGRAM_LINK_CODE_SCHEMA_VERSION,
    TelegramLinkCode,
)
from tlv_hunter.contracts.user import User
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.telegram.client import BOT_USERNAME
from tlv_hunter.userdata.base import ChatLinkedElsewhere, LinkCodeNotUsable, UserDataStore

logger = logging.getLogger(__name__)

CODE_FORM = re.compile(r"[A-Za-z0-9_-]{32}")
DEEP_LINK = "https://t.me/{bot}?start={code}"


@dataclass(frozen=True)
class IssuedLinkCode:
    """A new code, shown once to its user: in `link`, and by itself to type to the bot."""

    code: str = field(repr=False)
    link: str = field(repr=False)
    expires_at: datetime


def new_link_code(store: UserDataStore, token: str, now: datetime) -> IssuedLinkCode:
    """A code for the session's user (signed in, no password change due)."""
    user = _signed_in(store, token, now)
    code = _new_code()
    store.add_link_code(
        TelegramLinkCode(
            schema_version=TELEGRAM_LINK_CODE_SCHEMA_VERSION,
            code_hash=secret_hash(code),
            user_id=user.user_id,
            created_at=now,
            used_at=None,
        )
    )
    logger.info("telegram link code made: user %s", user.user_id)
    return IssuedLinkCode(
        code=code,
        link=DEEP_LINK.format(bot=BOT_USERNAME, code=code),
        expires_at=now + LINK_CODE_LIFETIME,
    )


def looks_like_code(text: str) -> bool:
    return CODE_FORM.fullmatch(text) is not None


def link_chat(store: UserDataStore, code: str, chat_id: int, now: datetime) -> User:
    """The chat linked to the code's user; `Refused("code_not_usable")` (unknown, used, expired,
    or its user disabled) or `Refused("chat_linked_elsewhere")`."""
    if not looks_like_code(code):
        raise Refused("code_not_usable")
    try:
        user = store.link_telegram(secret_hash(code), chat_id, now)
    except LinkCodeNotUsable as error:
        logger.info("telegram link refused: no usable code")
        raise Refused("code_not_usable") from error
    except ChatLinkedElsewhere as error:
        logger.info("telegram link refused: the chat is linked to another user")
        raise Refused("chat_linked_elsewhere") from error
    logger.info("telegram linked: user %s", user.user_id)
    return user


def unlink(store: UserDataStore, user_id: str) -> User:
    """No chat on the user any more; the alerts stop. Compare and set, as every `User` write."""
    for _ in range(STORE_ATTEMPTS):
        current = store.get_user(user_id)
        if current is None:
            raise Refused("unknown_user")
        if current.telegram_chat_id is None:
            return current
        updated = User.model_validate(
            {**current.model_dump(), "telegram_chat_id": None, "telegram_linked_at": None}
        )
        try:
            store.save_user(updated, expected=current)
        except StaleRecordError:
            continue
        logger.info("telegram unlinked: user %s", user_id)
        return updated
    raise StaleRecordError(user_id)


def unlink_session_user(store: UserDataStore, token: str, now: datetime) -> User:
    """The preferences page's "unlink": the session's own user."""
    return unlink(store, _signed_in(store, token, now).user_id)


@dataclass
class CodeAttempts:
    """Failed codes per chat, in memory (#264's rule, applied to codes)."""

    _failures: dict[int, tuple[int, datetime]] = field(default_factory=dict)

    def wait_left(self, chat_id: int, now: datetime) -> int | None:
        """Whole seconds to wait, or `None` when the attempt is looked at."""
        count, last = self._failures.get(chat_id, (0, now))
        if count < FAILURES_BEFORE_DELAY:
            return None
        left = last + SIGN_IN_DELAY - now
        return math.ceil(left.total_seconds()) if left > timedelta(0) else None

    def failed(self, chat_id: int, now: datetime) -> None:
        count, _ = self._failures.get(chat_id, (0, now))
        self._failures[chat_id] = (count + 1, now)

    def succeeded(self, chat_id: int) -> None:
        self._failures.pop(chat_id, None)
