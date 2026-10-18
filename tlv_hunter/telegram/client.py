"""Our own small Telegram Bot API client over the standard library (`PHASE_4.md` 4.2, point 1 A;
DECISIONS.md #452). Synchronous, like the rest of the code; the tests replace the transport.

What was read, and what the real calls returned, is in `PHASE_4.md` 4.1 and `ASSUMPTIONS.md` (the
T rows; Bot API 10.3). Every method is a POST to `https://api.telegram.org/bot<token>/<method>`:
**the token is in the address**, so no request address is ever logged, put in an error or kept on
an exception (the transport's own errors are replaced, `from None`). The token is checked for its
form and then held only inside the address. Every answer is `{"ok": true, "result": …}` or
`{"ok": false, "error_code": …, "description": …, "parameters": {"retry_after": …}}`; a 429 with
`retry_after` is waited out and the call made again, at most `RATE_LIMIT_WAITS` times.

Invariant 15, as amended (#452 point 8): a Telegram `chat_id` goes in requests to
`api.telegram.org` only, and nothing else of a user does; the User-Agent names the tool only.
"""

import json
import logging
import re
import secrets
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

API = "https://api.telegram.org"
BOT_USERNAME = "tlv_apartment_hunter_bot"  # @tlv_apartment_hunter_bot (#356), checked by getMe
USER_AGENT = "tlv-hunter-bot"
TOKEN_FORM = re.compile(r"[0-9]+:[A-Za-z0-9_-]{30,}")
RATE_LIMIT_WAITS = 3
LONGEST_WAIT = 120  # seconds; a longer retry_after fails the call
CALLBACK_DATA_BYTES = 64  # InlineKeyboardButton.callback_data: 1-64 bytes

# url, body, content type, timeout in seconds -> HTTP status, body
Transport = Callable[[str, bytes, str, float], tuple[int, bytes]]

logger = logging.getLogger(__name__)


class TelegramError(Exception):
    """A refused or failed call: the method, Telegram's `error_code` (None for a network failure)
    and its `description`. Never the address or the token."""

    def __init__(
        self,
        method: str,
        error_code: int | None,
        description: str,
        retry_after: int | None = None,
    ) -> None:
        code = "network" if error_code is None else error_code
        super().__init__(f"{method}: {code} {description}")
        self.method = method
        self.error_code = error_code
        self.description = description
        self.retry_after = retry_after


class TransportFailure(Exception):
    """The request got no HTTP answer; its message names the error's kind only."""


def urllib_transport(url: str, body: bytes, content_type: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": content_type, "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        # A refusal carries Telegram's JSON answer; the error object itself holds the address.
        return error.code, error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise TransportFailure(type(error).__name__) from None


@dataclass(frozen=True)
class Button:
    """An `InlineKeyboardButton` with one action: `url`, `callback_data` or `web_app_url`."""

    text: str
    url: str | None = None
    callback_data: str | None = None
    web_app_url: str | None = None

    def __post_init__(self) -> None:
        actions = [a for a in (self.url, self.callback_data, self.web_app_url) if a is not None]
        if len(actions) != 1:
            raise ValueError("a button has exactly one action")
        if self.callback_data is not None:
            size = len(self.callback_data.encode("utf-8"))
            if not 1 <= size <= CALLBACK_DATA_BYTES:
                raise ValueError(f"callback_data is 1-{CALLBACK_DATA_BYTES} bytes, got {size}")

    def as_json(self) -> dict[str, Any]:
        if self.url is not None:
            return {"text": self.text, "url": self.url}
        if self.callback_data is not None:
            return {"text": self.text, "callback_data": self.callback_data}
        return {"text": self.text, "web_app": {"url": self.web_app_url}}


Keyboard = Sequence[Sequence[Button]]


def keyboard_json(keyboard: Keyboard) -> dict[str, Any]:
    """An `InlineKeyboardMarkup`."""
    return {"inline_keyboard": [[button.as_json() for button in row] for row in keyboard]}


@dataclass(frozen=True)
class Upload:
    """A new file, sent by multipart/form-data."""

    field: str
    filename: str
    content_type: str
    data: bytes


class TelegramClient:
    def __init__(
        self,
        token: str,
        *,
        transport: Transport = urllib_transport,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not TOKEN_FORM.fullmatch(token):
            raise ValueError("TELEGRAM_BOT_TOKEN is not in a bot token's form")
        self._base = f"{API}/bot{token}/"
        self._token = token
        self._transport = transport
        self._sleep = sleep

    def __repr__(self) -> str:
        return "TelegramClient(<token not shown>)"

    def call(
        self,
        method: str,
        params: Mapping[str, Any] | None = None,
        *,
        upload: Upload | None = None,
        timeout: float = 30,
    ) -> Any:
        """The method's `result`, or `TelegramError`. A 429 is waited out (`retry_after`)."""
        body, content_type = _encode(dict(params or {}), upload)
        for attempt in range(RATE_LIMIT_WAITS + 1):
            try:
                status, raw = self._transport(self._base + method, body, content_type, timeout)
            except TransportFailure as failure:
                raise TelegramError(method, None, str(failure)) from None
            try:
                payload = json.loads(raw)
            except ValueError:
                raise TelegramError(method, status, "the answer is not JSON") from None
            if not isinstance(payload, dict):
                raise TelegramError(method, status, "the answer is not a JSON object")
            if payload.get("ok") is True:
                return payload.get("result")
            code = payload.get("error_code")
            code = code if isinstance(code, int) else status
            description = self._redact(str(payload.get("description", "")))
            parameters = payload.get("parameters")
            retry_after = parameters.get("retry_after") if isinstance(parameters, dict) else None
            retry_after = retry_after if isinstance(retry_after, int) else None
            waitable = retry_after is not None and 0 <= retry_after <= LONGEST_WAIT
            if code == 429 and waitable and attempt < RATE_LIMIT_WAITS:
                logger.warning("telegram %s: 429, waiting %d s", method, retry_after)
                self._sleep(retry_after)
                continue
            raise TelegramError(method, code, description, retry_after)
        raise AssertionError("unreachable")

    def _redact(self, text: str) -> str:
        return text.replace(self._token, "<token>")

    # --- the methods used (PHASE_4.md 4.3, point 1) ---

    def get_me(self) -> dict[str, Any]:
        return self.call("getMe")

    def get_webhook_info(self) -> dict[str, Any]:
        return self.call("getWebhookInfo")

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        """Long polling: the answer waits up to `timeout` seconds for an update."""
        params: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            params["offset"] = offset
        return self.call("getUpdates", params, timeout=timeout + 15)

    def send_message(
        self, chat_id: int, text: str, keyboard: Keyboard | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        if keyboard:
            params["reply_markup"] = keyboard_json(keyboard)
        return self.call("sendMessage", params)

    def send_photo(
        self, chat_id: int, photo: Upload, caption: str, keyboard: Keyboard | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
        if keyboard:
            params["reply_markup"] = keyboard_json(keyboard)
        return self.call("sendPhoto", params, upload=photo, timeout=60)

    def answer_callback(self, callback_id: str, text: str | None = None) -> None:
        params: dict[str, Any] = {"callback_query_id": callback_id}
        if text:
            params["text"] = text
        self.call("answerCallbackQuery", params)

    def edit_keyboard(self, chat_id: int, message_id: int, keyboard: Keyboard) -> None:
        self.call(
            "editMessageReplyMarkup",
            {"chat_id": chat_id, "message_id": message_id, "reply_markup": keyboard_json(keyboard)},
        )

    def set_my_commands(self, commands: Sequence[tuple[str, str]]) -> None:
        self.call(
            "setMyCommands",
            {"commands": [{"command": c, "description": d} for c, d in commands]},
        )

    def set_chat_menu_button(self, chat_id: int, menu_button: Mapping[str, Any]) -> None:
        self.call("setChatMenuButton", {"chat_id": chat_id, "menu_button": dict(menu_button)})

    def get_chat_menu_button(self, chat_id: int) -> dict[str, Any]:
        return self.call("getChatMenuButton", {"chat_id": chat_id})


def _encode(params: dict[str, Any], upload: Upload | None) -> tuple[bytes, str]:
    if upload is None:
        return json.dumps(params, ensure_ascii=False).encode("utf-8"), "application/json"
    boundary = "tlvhunter" + secrets.token_hex(16)
    parts: list[bytes] = []
    for name, value in params.items():
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
            + text.encode("utf-8")
            + b"\r\n"
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{upload.field}"; '
        f'filename="{upload.filename}"\r\nContent-Type: {upload.content_type}\r\n\r\n'.encode()
        + upload.data
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"
