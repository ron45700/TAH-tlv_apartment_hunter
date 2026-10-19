# Phase 4 — Telegram

**Status (2026-10-19, round 35): CLOSED.** DoD 1 is met: real alerts arrived on Ron's phone from the server, from the
scheduler's runs, on 2026-10-18 and 19 (`DECISIONS.md` #469). History: Ron answered points 1–14 (#452–#456): 1–11 and
13 as recommended, **Gate F approved** (#453), point 12 replaced by a `scheduler` service (#454), point 14: the token in
the laptop's `.env` for the tests (#455), and a `send_test_alert` command (#456). Built: 4.1–4.8 and the scheduler (§4.5).
The real-bot test (round 32, #457) passed, T5 VERIFIED (§4.6's result). **Round 35:** the `web_app` menu button "האתר" for
every linked chat, and the default back on unlinking, built (#470, §4.8 below). **What the DoD still leaves open** is
listed in §4.8. Next: Phase 5, drafted in `PHASE_5.md`.
*Round 30's draft follows unchanged up to §4.4; where it says "recommended", Ron approved it.*
**Owner:** Ron
**Parent:** `BASELINE.md` §9 (alerts), §10 (linking), §12 (the Phase 4 row) · **Schema:** `SCHEMA.md` (Gates A–E; Gate C
says "Telegram fields … are Phase 4's") · **After:** the server deployment (complete, `DECISIONS.md` #451)

**Phase goal:** Ron links his Telegram account from the site; a new post that matches his profile arrives as a Telegram
alert in the approved layout (#363), with its buttons; he can report it from the alert (#364); the bot's menu button opens
the site (#365); the Mini App spike answers `ASSUMPTIONS.md` T5. Friends get the same once they are added (`DEPLOY.md` §6).

**Phase DoD (draft, for Ron):**
1. A real alert arrives according to Ron's profile (`BASELINE.md` §12), on the server, from a real collection run.
2. Linking: a code the site shows, sent to the bot, links the account; the bot then sends one message, "N posts currently
   match your preferences", with a link to the site (#358).
3. Nothing is alerted twice to one user (the sent-alert record); a post the Gate D key ties to an earlier one never
   alerts (`PHASE_3.md` §3, #230–#232); a bootstrap run alerts nothing (`BASELINE.md` §4); a post whose kind is unclear or
   not written never alerts (#360); a post failing §9's rules never alerts.
4. The alert's "report" writes the flag or the report as the linked user, by the site's rules (#260, #300, #364).
5. The bot's menu button opens the site (#365); the Mini App spike's result is recorded (T5).
6. Tests pin: no user action through the bot writes a `RawPost` or a `Listing` (invariant 14); no per-user value is
   written on a post (invariant 12); the token is never logged, printed or put in an error (#356, #128); invariant 15 as
   amended by point 8.

---

## 4.0 Mandatory anchors

| Anchor | Source | State |
|---|---|---|
| When a post alerts a user | `BASELINE.md` §9: new and not rejected; its option; every critical condition; an explicit price; the location understood. Preferences never block; a missing critical category is named | Approved |
| A kind unclear or not written never alerts | #360 | Approved |
| A post the key ties to an earlier one never alerts | `PHASE_3.md` §3 ("Notes from the dedup B plan"); #230–#232 | Approved |
| A bootstrap run alerts nothing; a new user is alerted only on posts that arrive after signing up | `BASELINE.md` §4, §9; #357 | Approved (point 10 asks: signing up, or linking) |
| The linking message with the count | #358 | Approved |
| The alert's layout and buttons | #363 | Approved; checked against the limits here (§4.2) |
| The report button: "lied" and "wrong classification" | #364 | Approved |
| The menu button opens the site; the Mini App spike against `tlvapthunter` | #365, #426; T5 | Approved |
| The bot listens (long polling) | #56; `BASELINE.md` §3 ("outbound only: long polling and send calls") | Approved |
| The bot @tlv_apartment_hunter_bot exists; its token `TELEGRAM_BOT_TOKEN` is never read before this phase's plan names the code that reads it | #356; on the server in the stack's `.env`, passed to no service (#444) | In force |
| Collection never filters by a user; an `Evaluation` is never stored | Invariant 12; `policy/` | In force |
| The bot's modules and library are chosen in this plan, not before | `CLAUDE.md` | This plan, point 1 |

## Order of work (draft)

```
4.1 Gate F: the link and sent-alert records (points 4, 5)  ┐
4.2 the Telegram client (point 1)                          ├─ Ron's decisions first
4.3 the bot service (point 2)                              ┘
  →  4.4 linking (point 5)  →  4.5 the alert: who is alerted, when (points 3, 6, 10)
  →  4.6 the message and its buttons (§4.2, point 7)  →  4.7 the report from Telegram (point 11)
  →  4.8 the menu button and the Mini App spike (point 9)  →  4.9 a real alert on the server (DoD 1)
```

---

## 4.1 What was read (2026-10-18, under the `external-contract-verification` skill)

Documentation only; no call to Telegram, the token not read. **Bot API 10.3** (August 24, 2026, the newest entry under
"Recent changes" of core.telegram.org/bots/api).

| Piece | What the documentation says | Tag |
|---|---|---|
| `getUpdates` | Long polling: `offset` ("must be greater by one than the highest among the identifiers of previously received updates"), `limit` 1–100, `timeout` in seconds (0 = short polling), `allowed_updates`; updates are kept "not … longer than 24 hours"; it does not work while a webhook is set | Documentation (T4 VERIFIED 2026-10-02) |
| `sendPhoto` | `photo`: a `file_id`, an HTTP URL, or a new upload by `multipart/form-data`; at most 10 MB, width + height ≤ 10000, ratio ≤ 20. `caption` **0–1024 characters after entities parsing**; `parse_mode` | Documentation: **T1's 1024 confirmed**; ASSUMED until a real send |
| `sendMessage` | `text` **1–4096 characters** after entities parsing | Documentation |
| `sendMediaGroup` | `media` "must include **2–10** items" | Documentation: **T2 confirmed**; not used (one photo, #363) |
| HTML `parse_mode` | Only the listed tags; "All `<`, `>` and `&` symbols that are not a part of a tag or an HTML entity must be replaced with the corresponding HTML entities"; the named entities `&lt;` `&gt;` `&amp;` `&quot;` only | Documentation |
| `InlineKeyboardButton` | `url`: "HTTP or tg:// URL"; `callback_data`: **1–64 bytes**; `web_app`: "Available only in private chats between a user and the bot" | Documentation |
| Callback buttons | "Telegram clients will display a progress bar until you call `answerCallbackQuery`. It is, therefore, necessary to react by calling `answerCallbackQuery` even if no notification to the user is needed" | Documentation |
| `setChatMenuButton`, `MenuButtonWebApp` | The menu button of one private chat, or the default one; `MenuButtonWebApp` (`type` `web_app`, `text`, `web_app: WebAppInfo`) launches a Web App | Documentation |
| Deep linking (core.telegram.org/bots/features) | `https://t.me/<bot>?start=<parameter>`; "A-Z, a-z, 0-9, _ and - are allowed"; "up to 64 characters"; the bot receives the message `/start <parameter>` | Documentation |
| Mini Apps (core.telegram.org/bots/webapps; bots/features) | "Production links should use HTTPS"; `initData` is validated on the server: HMAC-SHA-256 of the sorted data-check-string, the secret key being HMAC-SHA-256 of the bot's token with the key `WebAppData`; `initDataUnsafe` "should not be trusted" | Documentation; T5 stays ASSUMED (the spike) |
| Rate limits (core.telegram.org/bots/faq) | "In a single chat, avoid sending more than one message per second"; about 30 messages per second overall; past the limits, 429 errors; `ResponseParameters.retry_after`: "the number of seconds left to wait before the request can be repeated" | Documentation |
| The token in the address | Every method is called as `https://api.telegram.org/bot<token>/<method>`: **the token is in the URL**, so no request URL is ever logged | Documentation (the API's own form) |
| Libraries (pypi.org, 2026-10-18) | `python-telegram-bot` 22.8 (2026-06-12; `httpx>=0.27,<0.29`, asyncio); `aiogram` 3.31.0 (2026-08-26; `aiohttp`, `pydantic<2.14`, asyncio) | Read |

**Found:** a `listing_id` is `sha256(source_post_id)` in hex, 64 characters (`SCHEMA.md`), so it does not fit in a
button's `callback_data` (64 bytes, with any prefix): a report button needs a shorter reference (point 11). The site
already opens one post at `/post/<listing_id>` (`frontend/src/route.ts`), so "open on the site" is a `url` button.

## 4.2 The alert, from #363 (checked against the limits above)

A photo message (`sendPhoto`, the post's first stored photo uploaded from `<store_root>/images/` by multipart: the
Facebook links expire, so never by URL), or a text message when the post has no photo. The caption, HTML-escaped, well
under 1,024 characters (no post text is included, #363): the kind (+ sublet); the price; the neighbourhood; the street
when written; the rooms ("1/2.5" on a room post); the entry date; then only the categories the user set, each 🟢 / 🔴 / 🟠 /
⚪ (#321) from `policy/colours.py`; "⚠️ חסר: …" for a critical category not written; 🔴 "women only" when that filter is off;
the relative publication time. Buttons: **open on the site** (`url`: `https://tlvapthunter.<tailnet>.ts.net/post/<id>`),
**Facebook** (`url`), **WhatsApp** (`url` `https://wa.me/…`, only with a mobile number), **report** (callback, point 11).
The exact Hebrew template is shown to Ron as a mock before it is built.

---

## 4.3 Points for Ron

Each with options and a recommendation; nothing below is decided.

**1. The Telegram library.**
- **A. Our own small client over the standard library** (`urllib`, as `providers/thedoor.py` does): the eight or so
  methods used (`getMe`, `getUpdates`, `sendMessage`, `sendPhoto` with a multipart upload, `answerCallbackQuery`,
  `editMessageReplyMarkup`, `setChatMenuButton`, `setMyCommands`), a `Transport` the tests replace with a fake (as
  `FakeApify` does), synchronous like the rest of the code; no new dependency. Risk: the multipart body, the 429 handling
  (`retry_after`) and long polling are ours to write and test.
- **B. `python-telegram-bot` 22.8:** complete and maintained; asyncio, `httpx` pinned below 0.29 (a second HTTP stack beside
  the code's `urllib`), its own application loop.
- **C. `aiogram` 3.31:** asyncio, `aiohttp`, and a pin of `pydantic<2.14` that would bind the project's pydantic.
- **Recommended: A.** The bot needs few methods, the project's other clients are written the same way, the socket guard
  and a fake transport test it offline, and nothing new is pinned.

**2. How the bot runs.**
- **A. Its own service, `bot`, in the server's stack:** the same image, `python -m tlv_hunter.jobs.bot`, `restart:
  unless-stopped`, long polling for ever; `TELEGRAM_BOT_TOKEN` passed to this service only (`environment:` from the stack's
  `.env`, #444); the store mounted as for the site. It is a store writer beside the site and the job commands (sent-alert
  records, links, the report's writes), by compare and set (#260).
- **B. Inside the site's process** (a background thread, as the grouping): one process fewer, but the token would reach
  the site's container (against #424 point 91's rule) and a bot failure would touch the site.
- **C. A job command run after each collection** (as `measure_day.sh` runs them): no listening between runs, so linking and
  the report buttons would wait for the next run.
- **Recommended: A.**

**3. When alerts are evaluated and sent.**
- **A. By the bot service:** it watches `SqliteRepository.store_generation()` (as the site does, #316) and, when it moves,
  evaluates the posts classified since its last pass for every linked user (the grouping by the Gate D key, then
  `policy.evaluate`), and sends. The classification job stays extraction only.
- **B. At the end of `classify_pending`:** the job would call `notify/` per user, so it would need the token and the user
  data, and a failed send could fail a classification run.
- **C. A separate job command `send_alerts`**, run after each classification: no token in the classification job, but the
  same waiting as point 2 C.
- **Recommended: A.** One sender, one place that holds the token.

**4. The sent-alert record (Gate F, a schema change).**
- **A. Minimal:** `user_id`, `listing_id` (the post alerted: the card's shown post), `sent_at` (UTC). One per user and post;
  "nothing alerted twice" means "no record yet"; a card whose members include an already alerted post does not alert again.
  Deleted with its post (as `ViewedPost`, #62).
- **B. A, plus `message_id`:** to edit or delete the alert later (for example when the post is flagged). Telegram's
  callback already carries the message, so the report flow does not need it.
- **C. A, plus the alert's tier or colours:** **not offered**: an `Evaluation` is never stored (`policy/`).
- **Recommended: A.**

**5. Linking by a code (Gate F).**
- **A. A deep link with a one-time code:** the preferences page shows "link Telegram"; it opens
  `https://t.me/tlv_apartment_hunter_bot?start=<code>` (the code 32 characters from `A-Za-z0-9_-`, within the 64 allowed);
  the bot receives `/start <code>`, links the chat to the user and sends #358's message. The code is stored as its SHA-256
  (as keys and sessions, `accounts/tokens.py`), single use, valid for 15 minutes; it can also be typed to the bot by hand.
  On the user: `telegram_chat_id` (integer, or none) and `telegram_linked_at` (UTC); a `TelegramLinkCode` record: the
  code's hash, `user_id`, `created_at`, `used_at`. One chat per user and one user per chat; unlinking from the preferences
  page (and `/stop` to the bot).
- **B. The code typed by hand only** (no deep link): one more step for the user.
- **Recommended: A.** The bot answers nothing to a chat that is not linked, except a `/start <code>`; failed codes are
  delayed as failed sign-ins are (#264).

**6. Alerts and the morning's batch.** No run starts 00:00–07:00 (#442), so the 07:00 run brings the night's posts at once.
- **A. Send as they come**, at most one message a second per chat (the documented limit), in publication order.
- **B. As A, but silently** (`disable_notification`) before 08:00.
- **Recommended: A** (no alert is sent in the quiet hours anyway).

**7. Which address the alert's "open on the site" button opens.**
- **A. The site's own post page** (`https://tlvapthunter.<tailnet>.ts.net/post/<listing_id>`), in the phone's browser;
  works with Tailscale on.
- **B. The Mini App** (a `web_app` button): only after the spike passes (point 9).
- **Recommended: A now, B if the spike passes** (#363: "the site, later the Mini App").

**8. Invariant 15 and the chat id. ⚠ A contradiction between docs: Ron's.** Invariant 15 says: "No outgoing request ever
carries a personal identifier of … any user". Every send to Telegram must carry the user's `chat_id`, which Telegram itself
issued.
- **A. Amend invariant 15:** a Telegram `chat_id` is allowed in requests to `api.telegram.org` only, never elsewhere (and
  the token only in that address); the rest of the invariant unchanged; a test pins both.
- **B. Leave it as is:** then no alert can be sent.
- **Recommended: A.** Also: the WhatsApp button carries a post author's number (`wa.me/…`) to Telegram; that is the post's
  own data, not a user's, and it is what #363 approved.

**9. The Mini App spike (T5).**
- **A. A menu button with `MenuButtonWebApp` pointing at `https://tlvapthunter.<tailnet>.ts.net/`** on Ron's chat only
  (`setChatMenuButton` with his `chat_id`); open it on his phone with Tailscale on, and with it off. Recorded: does it load;
  does the sign-in cookie hold inside Telegram's view. No `initData` validation is built for the spike (it is needed only if
  the Mini App is adopted, and then on the server, with the token).
- **B. Skip the spike; the menu button is a plain link** (`MenuButtonDefault` and a `/site` command with a `url` button).
- **Recommended: A**; then the default menu button for everyone points at whatever the spike shows works.

**10. A new user is alerted only on posts after "signing up" (`BASELINE.md` §9), or after linking?**
- **A. After linking:** a post alerts a user only if it was first stored after their `telegram_linked_at`; a user who links
  a month after signing up gets no backlog.
- **B. After signing up, as written:** on linking, posts since the sign-up that match would alert at once (#358's count
  message already reports them).
- **Recommended: A**, with `BASELINE.md` §9's sentence amended.

**11. The report from the alert (#364).**
- **A.** The "report" button opens two buttons, "שיקר" (lied) and "סיווג שגוי" (wrong classification). "Lied" asks a
  confirmation, then flags the card's members (#300). "Wrong classification" shows the reportable fields as toggle
  buttons (the keyboard edited in place), then "send", then an optional note by a reply message ("or press skip"). Each
  callback is answered (`answerCallbackQuery`). **The 64-byte limit:** the buttons carry a short reference, a kind letter
  and the first 16 hex characters of the `listing_id` (`r:3f9a…`), resolved by the bot against the user's sent-alert
  records; a reference that matches none, or more than one, is refused. Written as the linked user, by compare and set;
  "gone" when the post has left the list (as the site's 409).
- **B. The button opens the post on the site**, where the user reports it (no report flow in the bot).
- **Recommended: A** (Ron's reason in #364: reporting in Telegram is much easier).

**12. Runs during Phase 4.** Alerts need collection runs; the scheduler is Phase 5's.
- **A. Ron runs `measure_day.sh` again** for the days he tests alerts (paid, on his go; the same caps).
- **B. Manual runs** (`run_once`, then `classify_pending`) when he tests.
- **C. Bring Phase 5's scheduler forward.**
- **Recommended: A** for DoD 1; the scheduler stays Phase 5's.

**13. Which photo, and a post with none.** The first stored photo of the card's shown post (#363), uploaded from the
store; with no photo, a text message with the same lines and buttons; a photo over 10 MB or out of Telegram's proportions,
the text message. Recommended as written; no option needed unless Ron wants another.

**14. The token on the laptop.** For development the bot runs only against a fake transport; a real call from the laptop
would need the token in the laptop's `.env`. Recommended: the token stays on the server only (#444); every real send is
made there.

---

## 4.4 What I could not verify

- A real send: that Telegram accepts our multipart photo and the caption with its emoji within 1,024 characters (a real
  call, on the server, at the build).
- T5: whether a Mini App loads from a tailnet-only address (the spike).
- Telegram's answer when a user has blocked the bot (a 403 is expected; read in the documentation at the build).
- Whether a bot can message a user who never pressed Start (the FAQ and the features page do not say; linking needs the
  user to start the bot anyway).

---

## 4.5 What was built (round 31)

| Piece | Where | What it does |
|---|---|---|
| Gate F's records (#453) | `contracts/user.py` (version 2), `contracts/sent_alert.py`, `contracts/telegram_link_code.py`; `userdata/` (`add_link_code`, `link_telegram`, `find_user_by_chat`, `add_sent_alert`, `sent_listing_ids`) | Their own tables and layout row, `userdata.telegram` 1, created when absent (as `store.listings`): **no migration command**; a stored version-1 `User` reads as version 2 |
| The Telegram client (point 1) | `telegram/client.py` | `urllib`, JSON or multipart; a 429 waited out by `retry_after` (at most 3 times, 120 s each); the token only in the address, never in an error, a repr or a log line; no address logged; the transport's errors replaced (`from None`) |
| Linking (point 5) | `accounts/linking.py`; the site's `GET`/`DELETE /api/telegram`, `POST /api/telegram/link`; `frontend/src/components/TelegramLink.tsx` on the preferences page | The code (32 characters, 192 bits) shown once, its hash stored; 15 minutes; `/start <code>` or the code typed; one chat per user and per chat; 5 failures, then 30 s (#264); `/stop` and the page unlink |
| The alert rules (points 3, 10; §9; #360) | `policy/alert.py` (pure), `telegram/alerts.py` | §9 on the card's shown post: shown by an enabled option, its kind written, an explicit price, at least one area; the shown post first stored after `telegram_linked_at` (so a tied or reposted post, and a bootstrap's, never alerts); no `SentAlert` on any post of the card; classified within the last 24 hours; publication order, one second between two sends to a chat |
| The message (§4.2, point 13) | `notify/alert.py`, `notify/telegram.py` (the `notify/` seam; the stub gone) | The lines of #363, HTML-escaped, checked against 1,024 (a photo) or 4,096; the first stored photo by upload, else a text message; a photo Telegram refuses is sent again as text; buttons: the site's post page, Facebook, WhatsApp (a mobile only), report |
| The report flow (point 11) | `telegram/callbacks.py`, `telegram/bot.py` | "דיווח" → "המודעה משקרת" / "סיווג שגוי"; "lied" asks to confirm, then flags every member by `web/writes.flag_card`; "wrong classification": the 22 fields as toggles, "שליחה", then a note (one message, at most 500) or "דילוג", written by `web/writes.report_post` on the shown post; every callback answered; the reference (16 hex) resolved against the current cards |
| The bot service (point 2) | `telegram/bot.py`, `jobs/bot.py`; `compose.yaml` (laptop, profile `bot`), homelab's `bot` | Long polling (25 s); the alert pass between two polls when the store generation moved; private chats only; `setMyCommands` (`/site`, `/stop`) at start; refuses another bot's token or a webhook |
| The spike's menu button (point 9) | `jobs/telegram_menu.py` | `--spike`: a `MenuButtonWebApp` on one user's chat (the admin's by default) opening `SITE_URL`; `--default`; `--show` |
| `send_test_alert` (#456) | `jobs/send_test_alert.py` | The alert of one card, exactly as a real one, to a linked user; prints whether it would really alert and why not; writes no record |
| The scheduler (#454) | `jobs/scheduler.py`; homelab's `scheduler` | Slots on the interval's multiples, none in the quiet hours (Israel time, `tzdata`); `run_once` then `classify_pending --cap 0.05` as subprocesses in their own session; stdout and `data/measure/scheduler.<date>.log` in `measure_day.sh`'s form; 3 failures logged, never an exit; a stop lets the command finish |

**Decided in the build (reported to Ron):** the record layout without a migration; the 24-hour window of the alert
pass; the reference resolved against the current cards (so `send_test_alert`'s buttons work too); the `tzdata`
package; the laptop's `jobs` service given its two keys by name (no longer the whole `.env`, which holds the token);
the scheduler's log in `appdata/measure/scheduler/` (a folder owned by the image's user); its `stop_grace_period` of 40
minutes. No field was changed.

## 4.6 The real-bot test (with Ron, in this chat, on the laptop)

Against the laptop's development copy (the `tlv-hunter-store` volume). Free: no Apify, no OpenAI (#455). **No bot may
run on the server meanwhile** (none is deployed yet). The phone cannot reach the laptop's site (127.0.0.1 only, #417),
so the code comes from the laptop's browser; the phone gets every message, since the chat is the same on every device.

1. **Start** (PowerShell, in the repo):
   ```powershell
   docker compose up -d site
   $env:SITE_URL = "https://tlvapthunter.<tailnet>.ts.net"
   docker compose up -d bot
   docker compose logs bot --tail 5
   ```
   Expected: `bot started: @tlv_apartment_hunter_bot`.
2. **Link.** On the laptop: `http://127.0.0.1:8000/`, sign in, "ההעדפות שלי" → the card "התראות בטלגרם" → "קישור
   לטלגרם". Either click "פתיחת הבוט בטלגרם" (Telegram Desktop or Web) and press Start, or send the code shown to the
   bot from the phone. Expected on the phone, within seconds: "החשבון קושר לטלגרם. ✅ / **N** מודעות מתאימות כרגע
   להעדפות שלך…" with a "לאתר" button (#358), N the same as the preferences page's live count; the page then shows
   "מקושר מאז …" within about 4 seconds. Also: `/site` answers with the site's button; a wrong 32-character code
   answers "הקוד לא תקף…".
3. **Parking critical in the room search** (on the laptop's preferences page: the tab "חדר בדירת שותפים" → חניה →
   "חובה" → save): needed for test alert 3's missing line.
4. **Three test alerts** (the same PowerShell, `SITE_URL` still set):
   ```powershell
   docker compose run --rm bot python -m tlv_hunter.jobs.send_test_alert --listing 1121aaad36bc
   docker compose run --rm bot python -m tlv_hunter.jobs.send_test_alert --listing e75310053330
   docker compose run --rm bot python -m tlv_hunter.jobs.send_test_alert --listing 0555aa328a77
   ```
   Each prints "a real alert would be sent to this user" and "sent … no record written". Expected on the phone (rendered
   read-only from the copy on 2026-10-18; the age grows):
   - **1121aaad36bc, a photo:** the photo, the caption under it: `🏠 דירה שלמה` (bold) · `💰 ₪14,500` · `📍 נוה צדק` ·
     `🚪 3 חדרים` · `📅 כניסה: 15/10` · `🕒 פורסם לפני 14 ימים`; buttons `פתיחה באתר` / `פייסבוק` `וואטסאפ` / `דיווח`.
   - **e75310053330, no photo:** a text message: `🏠 דירה שלמה` · `💰 ₪3,200` · `🟠 נוה ברבור, כפר שלם מערב · נוה
     אליעזר וכפר שלם מזרח (המיקום לא ודאי)` · `🚪 חדרים: לא צוין` · `📅 כניסה: לא צוין` · the time; the same buttons.
   - **0555aa328a77, a room post, parking critical and not stated:** the photo; `🏠 חדר בדירת שותפים` · `💰 ₪2,900` ·
     `🟠 הצפון החדש-סביבת ככר המדינה · הצפון החדש-החלק הדרומי (המיקום לא ודאי)` · `🛣 רחוב: ארלוזורוב, הנרייטה סאלד` ·
     `🚪 חדרים: 1/3` · `📅 כניסה: 12.10` · `⚪ חניה` · `⚠️ חסר: חניה` · the time; the same buttons.

   Check on the phone: the Hebrew reads right to left, nothing is cut, the emoji show. "פתיחה באתר" opens
   `tlvapthunter…/post/<id>` (with Tailscale on): **the server's store does not hold the copy's posts, so the server's
   site answers "not found" there; on the laptop test only the address is checked.** "פייסבוק" opens the post;
   "וואטסאפ" opens a chat with the poster's number (send nothing).
5. **"Lied", with the confirmation** (on alert 1): דיווח → "המודעה משקרת" → "כן, המודעה משקרת". Expected: "תודה. המודעה
   סומנה כמשקרת והוסרה מהרשימה." and the report button gone. **The write:** on the laptop, the admin's flags page lists
   it, flagged by Ron; **restore it there.**
6. **"Wrong classification" with fields and a note** (on alert 3): דיווח → "סיווג שגוי" → toggle "חניה" and "מחיר" (each
   gets ✓) → "שליחה" → the bot asks for a note → reply with one message, for example "בדיקה". Expected: "תודה. הדיווח
   נשלח…". **The write:** the admin's reports page shows it with the two fields and the note; **restore it there.**
7. **"Wrong classification" with "skip"** (on alert 2): דיווח → "סיווג שגוי" → toggle "אזור" → "שליחה" → "דילוג".
   Expected: "תודה. הדיווח נשלח…"; the reports page shows it with no note; **restore it.** I then check read-only that
   the copy's `RawPost` and `Listing` rows are unchanged and that no `SentAlert` was written.
8. **The menu button, the spike (T5):**
   ```powershell
   docker compose run --rm bot python -m tlv_hunter.jobs.telegram_menu --spike
   ```
   On the phone, the bot's menu button (left of the attachment icon) reads "האתר". With **Tailscale on**: does
   `tlvapthunter` load inside Telegram? Sign in there: does the sign-in hold after closing and reopening it? With
   **Tailscale off**: what does it show? Recorded under T5. Then `--default`, or keep it (it is per chat, and stays
   with the server's bot).
9. **Stop:**
   ```powershell
   docker compose stop bot
   docker compose ps
   ```
   The bot must be stopped before the server's starts (one `getUpdates` consumer per bot, #455). Ron's link stays in the
   copy only; on the server he links again.

**Result (2026-10-18, round 32, #457):** Ron ran every step and reports them passed; T5 and T9 VERIFIED. The check
after it: the copy's `RawPost` and `Listing` rows identical to the Windows store's, no `SentAlert`. **Not as reported:**
in the copy `1121aaad36bc` is still flagged, `0555aa328a77` has one open report (`parking` only, no note) and is still
off the list, and `e75310053330` has no report. **Closed by Ron:** the copy reflects what he actually did (other fields
toggled, nothing restored); no defect; the test flag and report stay on the development copy. **Next, Ron's step:** a `web_app` menu button for every linked user, pointing at the
site (points 7 and 9), not built.

## 4.7 The deploy to the server (after the commit; nothing that runs there now is stopped)

**Rounds 33 and 34 ride with this deploy (#468).** Before step 4 (the new image's first start), with the old image still
running: `docker compose run --rm jobs python -m tlv_hunter.jobs.export_backup --no-photos` (a fresh dated backup). The
new image's first opener of the store (the site, the bot or a job) then creates the table `hidden_posts` and the layout row
`userdata.hidden` by itself; no command. From the first profile saved on the site, profiles are version 3 (`immediate`),
which the previous image cannot read: **a rollback to the previous image needs that backup restored** (its other tables
and the new row are harmless to it: checked in round 34 on a scratch copy).

1. Ron commits and pushes both repos; the TLV repo's Action builds and publishes the image (`latest`).
2. On `homeserver`: `cd ~/homelab && git pull`, then `cd stacks/tlv-hunter`.
3. In `.env` add `SITE_URL=https://tlvapthunter.<tailnet>.ts.net` (`TELEGRAM_BOT_TOKEN` is there, #444); the
   scheduler's three settings may stay empty (30, 00:00, 07:00).
4. The scheduler's log folder, owned by the image's user:
   `mkdir -p appdata/measure/scheduler && sudo chown 10001:10001 appdata/measure/scheduler`.
5. A fresh backup, the site running (an online backup):
   `docker compose run --rm jobs python -m tlv_hunter.jobs.export_backup --no-photos`.
6. `docker compose pull`, then `docker compose up -d site` (the new site lays out Gate F's tables). **Name the
   services:** a bare `docker compose up -d` would start the scheduler too.
7. **The laptop's bot stopped** (§4.6 step 9), then `docker compose up -d bot` and
   `docker logs --tail 20 tlv-hunter-bot`: `bot started: @tlv_apartment_hunter_bot`.
8. Ron links on his phone, through `tlvapthunter`'s preferences page (the deep link opens Telegram): #358's message.
9. **PAID, on Ron's go:** `docker compose up -d scheduler`; `docker logs -f tlv-hunter-scheduler` shows the header and,
   at the next :00 or :30 outside the quiet hours, the first slot.
10. **DoD 1:** the first real alert that matches Ron's profile arrives; nothing is alerted twice.
11. From then on: `docker compose stop scheduler` before any manual job command (homelab's README).

## 4.8 Closed (round 35): the DoD, and what it leaves open

| DoD | State |
|---|---|
| 1. A real alert, on the server, from a real run | **Met** (Ron's report, 2026-10-18/19, #469) |
| 2. Linking and #358's message | Passed on the laptop's real bot (#457); on the server Ron linked through `tlvapthunter` (§4.7 step 8): his report names only DoD 1, so the server's linking message is not separately reported |
| 3. Nothing alerted twice; a tied post, a bootstrap's post, an unclear kind never alerts | Pinned by tests (`tests/test_alerts.py`, `tests/test_telegram_bot.py`); not separately reported from the server |
| 4. The report from the alert writes as the linked user | Passed on the laptop (#457; the check found Ron's own steps differed from what he reported, no defect) |
| 5. The menu button opens the site; T5 recorded | T5 VERIFIED (#457); **the button for every linked user is built (#470)** and reaches the server with the image |
| 6. Tests pin invariants 12, 14, 15 and the token | In the suite |

**Open, none blocking:** (a) the deploy of round 35's image (`Dockerfile` unchanged; the bot service restarts on the new
image and sets the button for every linked chat by itself: Dockge "Update" when no run is in progress, since the
scheduler's stop waits for a running command, `stop_grace_period` 40 minutes); (b) ~~BotFather's `/setjoingroups`
(T7)~~ already disabled by Ron on 2026-10-18 (#475);
(c) #449's two open points, moved to Phase 5 (`PHASE_5.md` point 6); (d) "Adding the first friend" (`DEPLOY.md` §6), when
Ron has a friend; (e) whether rounds 33–34 reached the server with Phase 4's image (the repo shows them committed;
`BACKLOG.md` item 9 waits for Ron's word).

---

## Appendix A — Round 33's plan for #458 and #464–#466 (for Ron's approval; not part of §4.7's deploy)

**Status: approved by Ron on 2026-10-19, every point as recommended (`DECISIONS.md` #468); built in round 34.** Point 3's
rule is kept in UTC (invariant 9): the old chip shape is a `latest` on or before the UTC date of `updated_at` plus one day,
which covers every Israel date the chip could have saved. Items 2–6 and 10 of the same round are built (`DECISIONS.md` #459–#463, #467). The
proposed fields and record are in `SCHEMA.md`, "Proposed in round 33". Each point has a recommendation; "or" is the
other option.

### A.1 "מיידי" as a rolling window (#458)

1. **The field.** `DateRangeCriterion.immediate: bool` (proposed name). `True`: no `earliest`, no `latest`; the window is
   "no later than today + 3 calendar months", no lower bound. `False`: the range as today. The 3 is a constant in
   `policy/` (`IMMEDIATE_MONTHS`), not a field. *Or:* a separate type beside `DateRangeCriterion` in a union (more
   shapes to validate, no gain).
2. **The evaluation** (`policy/evaluate.py`, `_entry_date`): with `immediate`, a post's date is met when it is on or
   before `add_months(today, 3)`; a past date is met; a post's "immediate" compares as today (#270's post side) and is
   met. A day the month lacks becomes its last (30.11 → 28.2), as the page's fill (#459) does. `today` stays R2's UTC
   date of the evaluation: **between 00:00 and 02:00/03:00 Israel time the window ends a day earlier.** Recommended: keep
   R2 (one "today" for every comparison). *Or:* Israel's date for this window only.
3. **Stored profiles** (`Profile.from_stored_json`): `Profile` to version 3; a version-2 (or 1) profile reads as 3 with
   `immediate` false, at read time only, written as 3 at its next save (as #317). **The old chip shape** (`earliest` null,
   `latest` a date): recommended, **convert** a criterion whose `latest` is on or before the Israel date of the profile's
   `updated_at` into `immediate` true (only the chip saves "until a day not after the save"; a user who typed today's
   date into "עד תאריך" is read the same way, accepted). *Or:* read as is (it stays stale until the user presses the chip
   again). Counted: the laptop's development copy holds 1 profile, with no entry date; **the server's were not read**
   (a read-only count there on Ron's go).
4. **The alerts:** nothing changes in `policy/alert.py` or `telegram/alerts.py`: both evaluate with `now`, so the window
   moves each day by itself. No new alert for an older post (the 24-hour window, #452).
5. **The page:** "מיידי" sets `immediate` true (the dates empty); a date typed clears it; the words stay "כניסה מיידית";
   the bar's JSON carries the field (an older bar kept in the tab reads it as false). The site's bar validation is the
   profile's own (strict), so the API and the page change together.
6. **Tests:** the contract (immediate with an end refused; alone accepted); `from_stored_json` (the chip shape converted,
   a future `latest` kept, version 1 to 3); the evaluation (today + 3 months met, one day later failed, a past date met, a
   post's "immediate" met, the month-end case, critical hides); the alert pass through the same evaluation; the web's
   bar round trip and its 422 in words; `bar.test.ts` (the chip, the words, "changed").
7. **The production store:** no table or layout change: the profile is a JSON document. After the deploy the site
   writes version-3 profiles, which **an older image cannot read** (a rollback needs the backup taken before). It reaches
   the server with Ron's commit and deploy, `export_backup` first.

### A.2 Hiding (#464–#466)

8. **The record** `HiddenPost` (`SCHEMA.md`, proposed): `schema_version`, `user_id`, `listing_id` (the card's shown post),
   `hidden_at`; key (`user_id`, `listing_id`); table `hidden_posts`, as `viewed_posts`. **Its own layout row
   `userdata.hidden` (version 1), created when absent**, as Gate F's `userdata.telegram`: no migration command, the
   `userdata` row stays 2, and an older image still opens the store (every opener reads only its own module's row;
   checked). *Or:* `userdata` to version 3 with a migration command, as `add_store_generation` (heavier, no gain).
   `UserDataStore` gains three methods: hide, unhide (every post of the card), and the user's hidden ids.
9. **The endpoints:** `POST` and `DELETE /api/hidden/{listing_id}` (signed in, `Origin` checked, a post gone is 409, as
   viewed). The list (`POST /api/cards`, `/api/cards/by-id`) takes `show_hidden` (default false); a signed-in user's
   card carries `hidden` (a guest's has no such field, as `viewed`); the first answer carries the count hidden.
10. **Who decides "on the saved preferences":** recommended, **the server**: it hides only for a signed-in user whose bar
    equals the stored profile (values compared, as the page's "changed" does) and with `show_hidden` false; the hidden
    cards are dropped before the order. *Or:* the page says so in the request (simpler, but a page bug would hide in a
    temporary filter).
11. **A grouped card** is hidden when any of its posts has a mark (as viewed, #253); "בטל הסתרה" deletes the marks on
    every post of the card. **A later publication grouped into a hidden card keeps it hidden**, as viewed (recommended).
    *Or:* a new publication brings the card back.
12. **Where the buttons sit.** Recommended (A): **a small "הסתר" pill on the photo's top-right corner**, opposite the "i",
    drawn like it (faded background, text in words), so the foot and its packing rule (#341, #351) do not change; "בטל
    הסתרה" in the same place; also in the opened post's foot beside "סימון כלא נצפה". On a phone the 118 px photo holds
    the "i" (28 px) and the pill (about 52 px). *Or (B):* in the foot, packed after the report button (#351): at a phone's
    334 px the three buttons take about 222 px beside the time, a fourth crowds them, and at the narrowest card (296 px)
    it does not fit. *Or (C):* in the "דיווח" menu (it is not a report).
13. **In a temporary filter** (everything shown, #465): recommended, "הסתר" is still offered (by tier, #466); pressed, the
    card stays in place marked "מוסתרת" with "בטל הסתרה", and leaves when the bar is back on the saved preferences.
    *Or:* no "הסתר" in a temporary filter, only "בטל הסתרה" on the hidden cards.
14. **A hidden card that is shown** (the switch on, or a temporary filter) keeps its place in the order, faded as a viewed
    card, with a "מוסתרת" tag (recommended). *Or:* all hidden cards at the end.
15. **The count and the switch.** On the saved preferences with the switch off, the count leaves the hidden out and the
    status line adds "· M מוסתרות" when there are any; "הצגת מוסתרים" shows only on the saved preferences (in a temporary
    filter it would change nothing), for a signed-in user; its state lives in the tab, as the bar's, and is never saved
    (no profile field). Pressing "הסתר" on the saved preferences takes the card out in place, the count one less (as a
    flag, #377).
16. **Alerts:** unaffected. A post is alerted before it can be hidden, and a later publication grouped into a card never
    alerts (#360).
17. **Deletion with the post:** `UserDataStore` has no delete-with-post method yet for `ViewedPost` or `SentAlert`
    (`BACKLOG.md`, "Recorded for a later phase", the run-conflict row); `HiddenPost` joins them for Phase 5's retention
    job. Until then a deleted post's marks match no card and do nothing.
18. **The production store's layout is written:** the first opener of the store with the new image (the site, the bot or
    a job) creates `hidden_posts` and the row `userdata.hidden`. It reaches the server only with Ron's commit and deploy,
    after `export_backup`; an older image still opens the store afterwards (point 8).
19. **Tests:** the record's contract; the store's three methods and the layout row created when absent on a store
    without it (and left alone on one with it); the endpoints (guest 401, `Origin`, 409); the list hiding only on the saved
    preferences, by any post of a grouped card, the count; `hidden` absent for a guest; the page: where the button shows
    by tier and viewed (#466), the switch, the in-place removal.

**Order of build when approved:** A.1 first (small, no layout change), then A.2.
