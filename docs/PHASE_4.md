# Phase 4 — Telegram

**Status (2026-10-18, round 31): APPROVED and BUILT; the real-bot test and the deploy wait for Ron.** Ron answered
points 1–14 (`DECISIONS.md` #452–#456): 1–11 and 13 as recommended, **Gate F approved** (#453), point 12 replaced by a
`scheduler` service (#454), point 14: the token in the laptop's `.env` for this round's tests (#455), and a
`send_test_alert` command (#456). Built: 4.1–4.8 and the scheduler, with tests (§4.5 below). **The real-bot test ran
(round 32, #457): passed by Ron's report, T5 VERIFIED; the check found steps 5–7's writes not as reported (§4.6's
result), and Ron confirmed the copy reflects what he did: no defect).** Next: the deploy (§4.7), DoD 1's real alert
(4.9), and the menu button for every linked user (Ron's step).
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
