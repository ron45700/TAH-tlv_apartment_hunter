"""The Telegram client (`PHASE_4.md` 4.2, point 1 A; DECISIONS.md #452): its requests, the 429
wait, the token kept out of every error and log line, invariant 15 as amended (point 8), and the
report buttons' data within 64 bytes. A fake transport only: no request leaves the machine.

`FakeTelegram` is the fake every Telegram test uses: it records each call (method, parameters,
upload) and answers as the Bot API documents (`{"ok": true, "result": …}`), or with what a test
queues for a method.
"""

import json
import logging
import urllib.error
import urllib.request
from collections import defaultdict, deque
from typing import Any

import pytest

from tlv_hunter.telegram import callbacks
from tlv_hunter.telegram.callbacks import Callback
from tlv_hunter.telegram.client import (
    API,
    BOT_USERNAME,
    Button,
    TelegramClient,
    TelegramError,
    TransportFailure,
    Upload,
    keyboard_json,
    urllib_transport,
)

TOKEN = "123456789:" + "AAbbCCddEEffGGhhIIjjKKllMMnnOOppQQr"


class FakeTelegram:
    """A fake transport: `calls` holds (method, params, upload) in order; `queue(method, …)` sets
    the next answers of a method, as (HTTP status, JSON body)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], bytes | None]] = []
        self.urls: list[str] = []
        self.bodies: list[bytes] = []
        self._queued: dict[str, deque[tuple[int, dict[str, Any]]]] = defaultdict(deque)
        self._message_id = 100

    def queue(self, method: str, status: int, body: dict[str, Any]) -> None:
        self._queued[method].append((status, body))

    def __call__(self, url: str, body: bytes, content_type: str, timeout: float):
        self.urls.append(url)
        self.bodies.append(body)
        method = url.rsplit("/", 1)[1]
        if content_type == "application/json":
            params, upload = json.loads(body), None
        else:
            params, upload = _multipart(body, content_type), body
        self.calls.append((method, params, upload))
        if self._queued[method]:
            status, answer = self._queued[method].popleft()
            return status, json.dumps(answer).encode()
        return 200, json.dumps({"ok": True, "result": self._result(method, params)}).encode()

    def _result(self, method: str, params: dict[str, Any]) -> Any:
        if method == "getMe":
            return {"id": 1, "is_bot": True, "first_name": "TAH", "username": BOT_USERNAME}
        if method == "getWebhookInfo":
            return {"url": "", "has_custom_certificate": False, "pending_update_count": 0}
        if method == "getUpdates":
            return []
        if method in ("sendMessage", "sendPhoto"):
            self._message_id += 1
            return {"message_id": self._message_id, "chat": {"id": params.get("chat_id")}}
        if method == "getChatMenuButton":
            return {"type": "default"}
        return True

    def of(self, method: str) -> list[dict[str, Any]]:
        return [params for name, params, _ in self.calls if name == method]

    def methods(self) -> list[str]:
        return [name for name, _, _ in self.calls]


def _multipart(body: bytes, content_type: str) -> dict[str, Any]:
    boundary = content_type.split("boundary=", 1)[1].encode()
    fields: dict[str, Any] = {}
    for part in body.split(b"--" + boundary)[1:-1]:
        head, _, value = part.strip(b"\r\n").partition(b"\r\n\r\n")
        name = head.split(b'name="', 1)[1].split(b'"', 1)[0].decode()
        if b"filename=" not in head:
            text = value.decode()
            try:
                fields[name] = json.loads(text)
            except ValueError:
                fields[name] = text
    return fields


def client(fake: FakeTelegram, sleeps: list[float] | None = None) -> TelegramClient:
    waits = [] if sleeps is None else sleeps
    return TelegramClient(TOKEN, transport=fake, sleep=waits.append)


# --- requests ---


def test_a_call_posts_json_to_the_bot_api_and_returns_the_result() -> None:
    fake = FakeTelegram()
    me = client(fake).get_me()
    assert me["username"] == BOT_USERNAME
    assert fake.urls == [f"{API}/bot{TOKEN}/getMe"]
    assert fake.calls[0][1] == {}


def test_send_message_is_html_with_no_link_preview_and_its_keyboard() -> None:
    fake = FakeTelegram()
    keyboard = [[Button("site", url="https://x.example/post/1")], [Button("r", callback_data="a")]]
    client(fake).send_message(42, "<b>hi</b>", keyboard)
    ((method, params, _),) = fake.calls
    assert method == "sendMessage"
    assert params == {
        "chat_id": 42,
        "text": "<b>hi</b>",
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "site", "url": "https://x.example/post/1"}],
                [{"text": "r", "callback_data": "a"}],
            ]
        },
    }


def test_send_photo_uploads_the_file_by_multipart() -> None:
    fake = FakeTelegram()
    photo = Upload("photo", "a1.jpg", "image/jpeg", b"\xff\xd8 jpeg bytes")
    client(fake).send_photo(42, photo, "caption ✓", [[Button("x", callback_data="y")]])
    ((method, params, upload),) = fake.calls
    assert method == "sendPhoto"
    assert params["chat_id"] == 42 and params["caption"] == "caption ✓"
    assert params["parse_mode"] == "HTML"
    assert params["reply_markup"] == {"inline_keyboard": [[{"text": "x", "callback_data": "y"}]]}
    assert upload is not None
    assert b'name="photo"; filename="a1.jpg"\r\nContent-Type: image/jpeg' in upload
    assert b"\xff\xd8 jpeg bytes" in upload


def test_get_updates_long_polls_messages_and_callbacks_only() -> None:
    fake = FakeTelegram()
    client(fake).get_updates(7, 25)
    assert fake.of("getUpdates") == [
        {"timeout": 25, "allowed_updates": ["message", "callback_query"], "offset": 7}
    ]


def test_the_menu_button_and_commands_calls() -> None:
    fake = FakeTelegram()
    bot = client(fake)
    bot.set_chat_menu_button(42, {"type": "default"})
    bot.set_my_commands([("site", "the site")])
    bot.edit_keyboard(42, 9, [])
    bot.answer_callback("q1", "done")
    assert fake.calls == [
        ("setChatMenuButton", {"chat_id": 42, "menu_button": {"type": "default"}}, None),
        ("setMyCommands", {"commands": [{"command": "site", "description": "the site"}]}, None),
        (
            "editMessageReplyMarkup",
            {"chat_id": 42, "message_id": 9, "reply_markup": {"inline_keyboard": []}},
            None,
        ),
        ("answerCallbackQuery", {"callback_query_id": "q1", "text": "done"}, None),
    ]


# --- refusals and the 429 wait ---


def test_a_refusal_is_a_telegram_error_with_its_code_and_description() -> None:
    fake = FakeTelegram()
    fake.queue("sendMessage", 403, {"ok": False, "error_code": 403, "description": "Forbidden"})
    with pytest.raises(TelegramError) as raised:
        client(fake).send_message(42, "x")
    assert raised.value.error_code == 403 and raised.value.description == "Forbidden"
    assert str(raised.value) == "sendMessage: 403 Forbidden"


def flood(seconds: int) -> dict[str, Any]:
    return {
        "ok": False,
        "error_code": 429,
        "description": f"Too Many Requests: retry after {seconds}",
        "parameters": {"retry_after": seconds},
    }


def test_a_429_is_waited_out_by_retry_after_then_the_call_is_made_again() -> None:
    fake = FakeTelegram()
    fake.queue("sendMessage", 429, flood(3))
    fake.queue("sendMessage", 429, flood(5))
    sleeps: list[float] = []
    sent = client(fake, sleeps).send_message(42, "x")
    assert sleeps == [3, 5]
    assert fake.methods() == ["sendMessage"] * 3
    assert sent["message_id"] == 101


def test_429_waits_are_bounded_and_a_too_long_wait_fails_at_once() -> None:
    fake = FakeTelegram()
    for _ in range(5):
        fake.queue("getMe", 429, flood(1))
    sleeps: list[float] = []
    with pytest.raises(TelegramError) as raised:
        client(fake, sleeps).get_me()
    assert sleeps == [1, 1, 1] and raised.value.error_code == 429
    fake = FakeTelegram()
    fake.queue("getMe", 429, flood(3600))
    sleeps = []
    with pytest.raises(TelegramError):
        client(fake, sleeps).get_me()
    assert sleeps == []


def test_an_answer_that_is_not_json_is_an_error() -> None:
    def broken(url: str, body: bytes, content_type: str, timeout: float):
        return 502, b"<html>bad gateway</html>"

    with pytest.raises(TelegramError, match="not JSON"):
        TelegramClient(TOKEN, transport=broken).get_me()


# --- the token: never in an error, a log line or a repr (#356, #128) ---


def test_the_token_is_never_in_an_error_a_repr_or_a_log_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    fake = FakeTelegram()
    fake.queue("getMe", 401, {"ok": False, "error_code": 401, "description": f"bad {TOKEN}"})
    fake.queue("getMe", 429, flood(1))
    bot = client(fake)
    with pytest.raises(TelegramError) as raised:
        bot.get_me()
    assert TOKEN not in str(raised.value) and "<token>" in str(raised.value)
    bot.get_me()
    assert TOKEN not in repr(bot)
    assert "429" in caplog.text
    assert TOKEN not in caplog.text and "api.telegram.org" not in caplog.text


def test_a_network_failure_carries_neither_the_address_nor_the_token() -> None:
    def down(url: str, body: bytes, content_type: str, timeout: float):
        raise TransportFailure("URLError")

    with pytest.raises(TelegramError) as raised:
        TelegramClient(TOKEN, transport=down).get_me()
    assert raised.value.error_code is None
    assert str(raised.value) == "getMe: network URLError"
    assert raised.value.__cause__ is None and raised.value.__suppress_context__


def test_a_token_not_in_a_tokens_form_is_refused_without_echoing_it() -> None:
    with pytest.raises(ValueError) as raised:
        TelegramClient("not a token, secret-ish")
    assert "secret-ish" not in str(raised.value)


class _Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self, *args: Any) -> bytes:
        return self._data

    def close(self) -> None:
        pass


def test_the_urllib_transport_names_the_tool_and_hides_the_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[urllib.request.Request] = []

    def refuse(request: urllib.request.Request, timeout: float):
        seen.append(request)
        raise urllib.error.URLError(OSError("no route"))

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    url = f"{API}/bot{TOKEN}/getMe"
    with pytest.raises(TransportFailure) as raised:
        urllib_transport(url, b"{}", "application/json", 5)
    assert str(raised.value) == "URLError"
    assert raised.value.__cause__ is None and raised.value.__suppress_context__
    (request,) = seen
    assert request.get_method() == "POST"
    assert request.get_header("User-agent") == "tlv-hunter-bot"

    def refused(request: urllib.request.Request, timeout: float):
        raise urllib.error.HTTPError(url, 400, "Bad Request", {}, _Body(b'{"ok": false}'))  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", refused)
    assert urllib_transport(url, b"{}", "application/json", 5) == (400, b'{"ok": false}')


# --- invariant 15, as amended (#452 point 8) ---


def test_every_request_goes_to_the_bot_api_and_nowhere_else() -> None:
    fake = FakeTelegram()
    bot = client(fake)
    bot.get_me()
    bot.send_message(42, "x")
    bot.send_photo(42, Upload("photo", "a.jpg", "image/jpeg", b"j"), "c")
    assert all(url.startswith(f"{API}/bot{TOKEN}/") for url in fake.urls)


# --- buttons ---


def test_a_button_has_exactly_one_action_and_callback_data_at_most_64_bytes() -> None:
    with pytest.raises(ValueError):
        Button("x")
    with pytest.raises(ValueError):
        Button("x", url="https://a", callback_data="b")
    with pytest.raises(ValueError):
        Button("x", callback_data="")
    with pytest.raises(ValueError):
        Button("x", callback_data="é" * 33)
    assert Button("x", callback_data="a" * 64).callback_data == "a" * 64
    assert keyboard_json([[Button("m", web_app_url="https://s/")]]) == {
        "inline_keyboard": [[{"text": "m", "web_app": {"url": "https://s/"}}]]
    }


# --- the report buttons' data (point 11 A) ---

REF = "3f9a12b4c5d6e7f8"


@pytest.mark.parametrize(
    "callback",
    [
        Callback("r", REF),
        Callback("l", REF),
        Callback("L", REF),
        Callback("w", REF, 0),
        Callback("t", REF, 5, 3),
        Callback("s", REF, 5),
        Callback("k", REF, 5),
        Callback("b", REF),
    ],
)
def test_every_callback_round_trips(callback: Callback) -> None:
    assert callbacks.parse(callback.data()) == callback


def test_the_longest_callback_is_well_under_64_bytes() -> None:
    every = (1 << len(callbacks.FIELDS)) - 1
    data = Callback("t", REF, every, len(callbacks.FIELDS) - 1).data()
    assert len(data.encode()) <= 64
    Button("x", callback_data=data)


def test_the_mask_names_the_chosen_fields_in_their_order() -> None:
    callback = Callback("s", REF, 0b101)
    assert callback.fields == (callbacks.FIELDS[0], callbacks.FIELDS[2])
    assert callbacks.toggled(Callback("t", REF, 0b101, 1)) == 0b111


@pytest.mark.parametrize(
    "data",
    [
        "",
        "r",
        "r:short",
        f"x:{REF}",
        f"r:{REF}:1",
        f"w:{REF}",
        f"t:{REF}:1",
        f"t:{REF}:1:99",
        f"s:{REF}:ffffffff",
        f"R:{REF}",
        f"r:{REF.upper()}",
    ],
)
def test_data_this_bot_never_sent_is_refused(data: str) -> None:
    assert callbacks.parse(data) is None


def test_a_reference_is_the_first_16_hex_characters() -> None:
    assert callbacks.ref_of("ab" * 32) == "ab" * 8
