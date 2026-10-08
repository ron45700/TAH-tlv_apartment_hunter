# TLV Apartment Hunter — Baseline

**Status:** Approved by Ron, 2026-10-02. Amended 2026-10-03 after the cross-check of the other docs.
Amended 2026-10-04: run interval and manual run (`DECISIONS.md` #61), viewed posts (#62), Gate E
(#63), the SQLite file shared by `store` and `state` (#64, #65), "no images" means no media at
all (#67, #68), a `no_text` post that comes back with text (#69), media that arrives through a
repost (#70), the pre-model rejects' open cases (#72), text normalize before the pre-model
rejects (#73), the state a repost of an archived post returns to (#74), and dedup A's canonical
rule (#75).
Amended 2026-10-05: the source of areas and streets and who decides the area (`DECISIONS.md`
#81–#88), and the Gate B content that touches §4, §6 and §7 (#89–#107); §13's row on flagged posts
corrected to §5. Amended again 2026-10-05: Ron's answers on Gate B (#108–#119) in §6 and §7, and
three card rules (#120–#122) in §6. Amended again 2026-10-05: Gate B's last two points (#123,
#124) in §6–§7; OpenAI as the model provider and provider-neutral rules (#126, #129) in §4 and §12. Then the
spike's decisions: the setting (#157) in §4, prefix letters and names not in the text (#158, #162)
in §7. Then the model decides the area (#167–#170): §4 and §7 rewritten.
Amended 2026-10-08: Gate D's key (`DECISIONS.md` #230, amended by #232) and that dedup B's result is
derived from the stored posts, not stored, with its use in Phase 3 (#231): §4 and §12.
**Owner:** Ron

> This file is the description of what the system is and how it is built. It replaces
> `HANDOFF.md` and `MACRO_PLAN.md`, which are in `docs/archive/` and describe the old direction.
> Research findings that still hold (providers, field map, traps, test results) are in
> `docs/RESEARCH.md`.
>
> `SCHEMA.md` stays the only source of truth for field names and types. This file states
> **requirements**; it does not name fields. Names and types are settled at the gates (§12).

---

## 1. What this is

A personal, non-commercial tool for Ron and a few close friends. It collects rental posts from
public Tel Aviv apartment Facebook groups, classifies each post once with an LLM, shows them in a
dashboard with per-user filtering, and pushes a Telegram alert when a new post matches a user's
saved profile.

**The problem it solves:** manually scanning several groups several times a day for the few posts
that fit.

**Sources:** Facebook public groups through Apify actors. The group list is one shared list: every
user sees posts from all of them. Editing the list from the dashboard is a later addition. Yad2 is
also a later addition and will probably need its own scraper; the design must stay open to it
(see §13).

---

## 2. Principles

| # | Principle |
|---|---|
| 1 | No Facebook account, no login, no cookies. Public groups only, through Apify. |
| 2 | Provider adapter layer. Two providers (thedoor primary, memo23 backup) sit behind one interface; past it, no module knows which provider the data came from. |
| 3 | The LLM classifies; all filtering is done on structured fields. |
| 4 | The model classifies only. It never summarizes and never adds text of its own. |
| 5 | "Not written" is information, not failure. It is kept distinct from "unclear" (§6). |
| 6 | Collection is shared; evaluation is personal. A post is fetched and classified once. Filtering, ordering and alerts are computed per user over the stored fields, with no extra model call. |
| 7 | No keyword sniper. It is removed from the project, not kept dormant. |
| 8 | Every external tool, API or data source is verified against its own current documentation before anything is built on it. Tags: `VERIFIED` / `ASSUMED` / `UNKNOWN`. Nothing is built on `ASSUMED`. |
| 9 | No schema, field or filter rule is created or changed without Ron's approval (gates, §12). |
| 10 | Post comments are not collected. Both comment flags are set off explicitly. |
| 11 | Retention is bounded (§5). This replaces the old rule "nothing is ever deleted". |

---

## 3. Hosting

| Item | Decision |
|---|---|
| Machine | Ron's home server (a laptop being converted), running 24/7. Development and first runs on Ron's personal laptop. |
| OS | Ubuntu Server LTS or Debian, no desktop. |
| Runtime | Docker Compose. The same compose file runs on the personal laptop and on the server. |
| Database | SQLite, one file, behind the `store` interface (posts and their lifecycle records) and the `state` interface (per-group watermarks). Postgres stays a cheap swap. |
| Images | Downloaded at fetch time to a directory on disk (Facebook image links expire within days). |
| Remote access | Tailscale. The dashboard is published with Tailscale Serve (HTTPS, tailnet only). Friends get access through Tailscale device sharing. |
| Telegram | Outbound only: long polling (`getUpdates`) and send calls. No public address or open port. |
| Fallback | GCP, as in the original plan, if the home server proves unworkable. |

Each friend needs a Tailscale account and the app active on every device they use for the
dashboard or the Mini App. Telegram alerts arrive regardless.

Laptop-as-server settings: no suspend on lid close, battery charge limit if the BIOS allows,
power-on after power loss, wired network.

---

## 4. Data path

```
scheduler -> Apify (thedoor) -> provider normalize -> text normalize -> pre-model rejects
          -> dedup A -> image download -> store ("pending")
          -> the model (extraction, the area included) -> rejection derived by code
          -> update the stored post
          -> dedup B: the same listing, derived by the Gate D key, not stored (phase 3)
          -> per-user evaluation -> Telegram alert
```

- **Stored before the model** (`DECISIONS.md` #79): in phase 1 the post is stored before the
  model, as `"pending"`; the model updates the stored post later.
- **Schedule:** every 30 minutes by default. No scheduled runs between 01:00 and 07:00 Israel
  time. The 07:00 run covers the whole night: its window starts at the last successful run. The hours live in config;
  later they are editable by the admin from the dashboard.
- **Interval and manual run** (`DECISIONS.md` #61, phase 5): the interval is an admin setting, and
  a change takes effect at once — the next run is the last run's start plus the new interval. The
  admin can start a run now, also during the quiet hours. A manual run is an ordinary run; when it
  succeeds, the next scheduled run is its start plus the interval, and when it fails the timer is
  not reset. One run at a time: a manual request during a run is refused or waits, and two runs
  never overlap.
- **Watermark:** per group, the highest post time seen, never moving backwards. The run's window
  starts at the last successful run's start minus a 15-minute overlap, the same for every group;
  all groups advance together, only on a successful run (`DECISIONS.md` #78).
- **Bootstrap:** the first run stores everything and alerts nothing.
- **Dedup A (before the model):** post ID and hash of normalized text, checked within the batch
  and against history. A phone-only match is not a duplicate; the phone is a candidate signal for
  dedup B. The canonical is the earliest publication among posts that arrive together; a stored
  canonical never changes, so an older copy that arrives later becomes its duplicate
  (`DECISIONS.md` #75).
- **Dedup B (after the model; derived, not stored):** same apartment reposted with rewritten text. The
  Gate D key (`DECISIONS.md` #230, #232): two posts with different text hashes, within 72 hours of each
  other, among the active canonical posts that have a classification, are the same listing when they share a
  phone that is not an agent number (a number found in four or more of those posts) **and** the fields match
  (price sets equal, rooms equal, an area in common), **or** they hold a byte-identical photo **and** one of
  those two matches. Nothing else merges: a phone, the fields or a photo alone never does. The result is
  **computed from the stored posts when it is needed**, never written onto a post (#231): the dashboard's
  lists and cards in phase 3, the alerts in phase 4. How it is computed and shown is planned with phase 3.
- **Reposts:** a repost does not create a new card and does not alert again. It updates the post's
  "last published" time and adds a line to a small repost log on the card, so it is easy to see
  that an apartment has been pushed for a while and is still not rented.
- **Model:** the provider is OpenAI, for now (`DECISIONS.md` #126); `gpt-6-luna` is the first
  model to try (#127). The model and its settings (reasoning effort, temperature) are settled after
  the spike: reasoning effort `none`, temperature 0, confirmed on the regression set run twice;
  `low` is the fallback (#157). Structured output,
  schema derived from the pydantic model (#22). The original text is sent verbatim. Every call
  sends `store: false` (#147); the instructions are cached with an explicit breakpoint, and a post
  is never written to the cache (#150). OpenAI's 30-day abuse-monitoring log is accepted (#146). The model returns facts only; code derives the
  rejection and its reason from them (`DECISIONS.md` #92), so a rule change needs no
  reclassification.
- **Street and area:** the model returns the areas itself, from the 71 in its instructions, and
  the streets and neighbourhood names as written (§7, `DECISIONS.md` #167).

Provider inputs, the field map, traps, the duplicate rate and the group IDs are in
`docs/RESEARCH.md`.

---

## 5. Post lifecycle

| State | Meaning | Visible to |
|---|---|---|
| **Pending** | Stored, passed the pre-model rejects, not classified yet. In phase 2 the model moves it to active or rejected | Admin |
| **Active** | Classified, not rejected | All users, through their filters |
| **Rejected** | Stored with a reason; never shown in the regular list | Admin only, for every reason. It exists so Ron can check that what was rejected belongs there |
| **Archived** | 25 days since last publication with no repost. Hidden. Images deleted; text and raw data kept. A post that was rejected keeps its rejection reason | Admin |
| **Deleted** | 40 days since last publication. Removed entirely | — |

A repost resets the clock. A repost of an archived post returns it to the state it had: active if
it was active; rejected, with the same reason, if the model rejected it or a user flagged it;
pending if it was never classified, or if it was rejected for having no images and the repost has
media (`DECISIONS.md` #72.5, #74). A repost extends a post's life; it does not change what is known
about it.

### Rejection reasons

| Reason | Decided | Notes |
|---|---|---|
| No text | Before the model | Not sent to the model. A post rejected before the model and fetched again is checked against both pre-model rules on its current content: it returns to pending and goes to the model only if it passes both; otherwise it stays rejected, with the first reason that applies. A pending post fetched again is re-checked the same way; a post with a verdict, or an archived one, is left as it is (`DECISIONS.md` #69, #72.1, #73) |
| No images | Before the model | Not sent to the model. Means **no media at all**: a post whose only media is video or reel is not rejected. A post that shares another post is checked first: it is rejected only if the shared post has no media either. A post rejected for this and fetched again is re-checked as in "No text" (`DECISIONS.md` #67, #68, #72.1). The post also returns to pending when a repost of it with identical text arrives with media, video or reel included: the repost's photos are downloaded and kept with the post while the post holds no downloaded image or when it is archived, and the repost stays a repost (#70, #72.3, #72.4). Which media are downloaded (photos only) is a separate rule |
| Other city | By Facebook's location field when the post has one, else by the model (#214) | The post is in a city that is not Tel Aviv–Yafo: its location field's locality (the part before the first comma) is another city, or, with no usable locality, the model finds that the text names one. The city is shown next to the post. Applies to all users. A nearby city mentioned as a landmark ("5 minutes from Givatayim") is not a rejection. Only about a quarter of the posts carry the field (thedoor's structured listings, `RawPost.native_location`) |
| Seeking | By the model | The poster is looking for an apartment, not offering one |
| For sale | By the model | Facebook's `sale_post` type does **not** mean sale; it is mostly rentals |
| Not a listing | By the model | Furniture, a parking space, an office, anything that is not an apartment or a room |
| Flagged "lied" | By a user | See below |

**Flagging.** Any user can flag a post that passed but is not what it claims (for example, an
apartment in Netanya that looked like Tel Aviv). The post moves to rejected for everyone and
records who flagged it. The admin can review flags by user and restore a post. Flagged posts are
exempt from deletion: the full record, including the raw data and not only the text, is kept as a
permanent regression set for the prompt. Their images are deleted at archive like any post's. A
restored post follows normal retention.

Fields and rules: `SCHEMA.md`, Gate E (`DECISIONS.md` #63).

---

## 6. What a card shows

**Always:**
- The poster's full original text, unchanged
- Images
- Link to the original post
- Price. A post can give several prices: all are shown, as "X/Y", and filtering uses the lowest
  (`DECISIONS.md` #95)
- Entry date, as the poster wrote it. "כניסה מיידית" counts as a stated entry date; it is not
  only for calendar dates. A comparable value (immediate, or a date) is stored next to the text
  for filtering; it never replaces it (#96). Its year, completed by code when the post gives none,
  is never displayed (#115). A month with no day counts as its 1st (#123)
- Location: street and or area
- Listing kind, and a sublet mark when it is one
- Phone, when present. Every distinct number in the post is shown; an identical number appears
  once. If the post gives a name with the number it is shown as `name-number`
  (`דני-0541234567`); with no name, the number alone
- Publication time: the **last** publication (the latest repost), shown relative: minutes up to an
  hour, hours up to 24 h, days after that. Earlier publications, the first included, are in the
  repost log (#122)

**Marked fields** (each shows one of the states below):
- Broker: yes / no
- Number of rooms (always the total in the apartment, also for a room in a shared flat). On a room
  post: "1 of N" when the total is written, a room with no "of" when it is not; the "1" comes from
  the listing kind, not from the text (#120)
- Floor (ground = 0). Shown as "floor/floors" only when the building's floor count is written
  (#98, #106)
- Size in sqm: the apartment's; the room's too, only when written (#99). On a room post: "X sqm
  for the room, of Y" when both are written; "X sqm for the room" when only the room's is (#121)
- Balcony (not written is shown as "not known")
- Parking (not written is shown as "none")
- Arnona and house committee, as two separate fields
- "Women only"
- "Women preferred" (עדיפות לבנות). This is not "women only": it is a mark on the card and hides
  nothing. Both come from one gender field with no "not written" state: a post that says nothing
  about gender has no restriction (#117)
- Elevator, air conditioning (card only, never a filter)
- Furnished: yes / partially / no (card only, never a filter; #102)

### Field states

| State | Meaning | Look |
|---|---|---|
| Present and matches | | Green / lit |
| Present and does not match the user's preference | | Red |
| Not written | The poster did not mention it | Grey / off |
| Unclear | The poster wrote something ambiguous ("option for parking", "all included"). Nothing read is kept for it (#109); the original text is on the card | Orange |
| Important and missing | Price or entry date not written | Its own colour, stronger than grey. Chosen at UI stage |

Balcony and parking are both **stored** as "not written"; the difference above is a display rule
only, so it can change without reclassifying.

---

## 7. Location

**Amended 2026-10-05** (`DECISIONS.md` #81–#83, #167–#170): the model decides the area. *An earlier
amendment of the same day had code decide it through a street table and a translation table
(#84–#88, #110, #111); superseded by #167.*

- **The model returns the areas:** municipal numbers from the closed list of 71, which is given in
  its instructions, stored on the post (#167). It also returns the streets and neighbourhood names
  as written, kept for the card and for error analysis; a name or other city the post does not
  contain is dropped (#162, #180). The model never touches the source text, so a wrong area is visible beside the
  original and can be counted and corrected. The other-city rejection is not the model's alone:
  when the post has Facebook's own location field, its locality decides (#214).
- **The areas** are a closed list: the municipality's open `שכונות` dataset (GIS layer 511), all
  71 entries, the Old North in its two parts, non-residential entries included (#81), in
  `reference/areas.yaml`. Any grouping is a display rule, decided at Gate C (#82). An area is
  identified by its municipal number; the name is a label (#83).
- **The rules, given to the model as instructions** (#88, #112, #124, #167): a stated area decides;
  a street only refines inside it (for example, which part of the Old North); several possible
  areas are all returned (a long street such as Dizengoff, with nothing to settle it); nothing the
  model can place returns no area. With no area name and no street, a well-known landmark that
  places the apartment decides ("ליד שוק הכרמל"), every area it touches on a border; a general
  distance phrase places nothing (#178). Colloquial names ("הצפון הישן", "לב העיר", "יפו") are
  given as examples (#86). Filtering is always by area, never by street.
- **Known limit** (#170): for a post with only a street, the area rests on what the model knows of
  Tel Aviv. The regression set measures it (90% on `areas`, by reach: #198). A street table as an aid is recorded
  for later, only if the regression set shows the model weak on such posts (#169).
- **The colour comes from the stored areas** (#110, #112, #113): one area, definite; two or more,
  unclear (orange), matching and alerting if any is chosen, also when one stated name covers
  several entries (Gate C may drop the orange for a user who chose all of them); none, and the
  post gave a street or an area name, unclear and never alerted; none, and no location given, not
  written. Shown at the bottom, never alerted, when unclear with no area.

---

## 8. Filtering and profile

Each user has one profile. The dashboard can show everything; the profile is the saved filter, and
the same profile drives that user's Telegram alerts. Changing it affects alerts from then on.

| Level | Categories | Behaviour |
|---|---|---|
| **Listing kind** (hard) | Room in a shared flat · empty apartment · sublet | Only checked kinds are shown. Sublet is a basic flag: a post is a sublet or not, with no duration or other detail |
| **Critical, fixed** | Area (multi-select) · price range (min and max both optional) | A post that fails is not shown and does not alert. The user cannot downgrade these. No value entered = not applied |
| **Critical by default, user may turn off** | "Women only" | Negative only: such posts are hidden. If turned off, they are shown with a red icon |
| **Preference by default, user may make critical** | Rooms · floor range · sqm range · broker · parking · balcony · entry date | As a preference: affects order and field colour only. As critical: failing posts are not shown |
| **Don't care** | Any of the above with no value | No effect on display or order |

Within one profile, room and empty apartment each carry their own values (a room's price range is
not an apartment's), and every card shows clearly which option it answers.

**Order of display:** posts that meet the preferences first; then posts that meet the critical
conditions but not the preferences; at the bottom, posts where a filtered value is not written or
unclear. Posts that are known to fail a critical condition are not shown.

**Viewed posts** (`DECISIONS.md` #62): each user sees which posts they have already viewed. All
unviewed posts come first, then the viewed ones; within each of the two, the order above. "Viewed"
belongs to the user and is never written on the post. It survives a repost, since a repost updates
the existing card, and goes when the post is deleted. The exact trigger is decided in the phase 3
UI design, with a manual "mark as not viewed".

---

## 9. Alerts

A post alerts a user when all of these hold:

1. It is new (not a repost) and not rejected.
2. Its kind is one the user checked.
3. It passes every critical condition of that user.
4. It has an explicit price.
5. Its location is understood: either a definite area, or a street whose possible areas include
   one the user chose (alerted with the area marked orange). A post with no location, or one that
   could not be placed (§7), does not alert.

Preferences never block an alert. If a category the user made critical is not written in the
post, the alert is still sent and names the missing item.

A new user sees all existing posts in the dashboard but is alerted only on posts that arrive after
signing up.

---

## 10. Users and access

- An account is created with a one-time key issued by Ron. A used key cannot create another account.
- Sign-in on the site with a password. Telegram is linked by a code the site shows and the user
  sends to the bot. Site and Telegram share the same profile.
- Tailscale sharing is a second gate in front of the site.
- The site is built first, with a basic design. The Telegram Mini App is an adaptation of the same
  site.

## 11. Admin (Ron)

- Rejected posts, all reasons. No other user sees them
- Flag review by user, and restore
- Archive
- Daily digest: collected / deduplicated / classified / rejected / alerted, per group; silent-group
  detection; failures. Admin only.
- Key issuing
- Run interval, 30 minutes by default, and a "run now" button (phase 5, `DECISIONS.md` #61)
- Schedule hours (later)
- `max_posts` (later, phase 6): one value for all groups; a value where groups × `max_posts`
  reaches the charge cap's `maxItems` is refused on save

---

## 12. Build order

Phase 0 (skeleton, contracts, local store, text normalization, thedoor mapping, 97 tests) is done
and stays valid. Gate A (`RawPost`) stays approved. **Phase 1 is complete (2026-10-04):** four
real runs met its DoD (`PHASE_1.md`, `RESEARCH.md` §11).

| Phase | Contents | Done means |
|---|---|---|
| **1. Collection** | Fixes for decisions #37 and #38 · Apify spike (task 1.1a) · **Gate E** (post lifecycle fields) · SQLite store · thedoor fetch · pre-model rejects · dedup A · repost log · image download · per-group watermark | A real run stores posts and images with no duplicates, and a second run does not repeat them |
| **2. Classification** | **Gate B** (field schema from §5–§7) · the model · post-model rejects · street and area · **Gate D** (the key, #230; its use is phase 3's, #231) · reclassify job | Every post has fields and a state |
| **3. Basic dashboard** | **Gate C** (filter rules, and the user, key, profile and viewed-post records) · users and keys · profile and filters · cards · viewed posts · rejected list · flagging · the same-listing grouping, derived by the Gate D key (#231) | Ron filters and sees real apartments in a browser |
| **4. Telegram** | Bot · account linking · alerts by profile · sent-alert record per user and post, so nothing is alerted twice · Mini App spike | A real alert arrives according to Ron's profile |
| **5. Server** | Compose on the home server · Tailscale · scheduler with quiet hours, admin-set interval and a manual "run now" · archive and deletion job · digest, including native-price vs model-price mismatches · failure alert to the admin · silent-group detection | Two days unattended; first friend connected |
| **6. Later** | memo23 failover · UI polish from Ron's screenshots · editing the quiet hours, the group list and `max_posts` from the dashboard · Yad2 | |

Phases 1–4 run on Ron's personal laptop in Docker.

**Gates.** A (`RawPost`) and E (post lifecycle record and `GroupWatermark`, 2026-10-04) are
approved. B, C and D are settled with Ron before the code that depends on them. Gate E covers what
the lifecycle adds to a stored post: state, rejection reason, who flagged it, last publication
time, the repost log, and local image paths.

**Detailed planning is one phase ahead.** `PHASE_1.md` details phase 1 only. Two technical choices
are deliberately left for when their phase is planned: the dashboard framework (phase 3) and the
Telegram library (phase 4).

Because history is at most 40 days, adding a field later means reclassifying 40 days of posts, not
everything. The field list can start lean.

---

## 13. What changed against the old documents

| Old | New |
|---|---|
| #5 Everything in GCP | Home server + Tailscale; GCP is the fallback |
| #9 Telegram push only, no dashboard in v1 | Dashboard first, then bot and Mini App |
| #12 / #16 Sniper in shadow / dormant | Removed |
| #13 Nothing is ever deleted (invariant 3) | Archive at 25 days, full deletion at 40; flagged posts kept whole, `raw` included, images deleted at archive (§5) |
| #15 `new_north` included at launch | Areas are chosen per user |
| #17 v1 pushes every post (calibration mode) | Alerts only on profile match; calibration is done through the rejected list and flagging |
| #21 `httpx`, push-only bot | The bot also listens (account linking). Library choice reopened |
| #39 No-text posts are notified | Rejected, admin-only view, not classified |
| #41 Three view-time filters | The full model in §8 |
| Single user in v1 | Friends from the start; #25 (shared collection, personal evaluation) is now live |
| Firestore, Cloud Run, Cloud Scheduler | SQLite, Docker Compose, a scheduler in the container |
| Image re-hosting deferred to Phase 6 | Images downloaded at fetch time |
| Phases 0–6 of `MACRO_PLAN.md` | §12 |
| Yad2 through `providers/` | Still future; likely its own scraper |

Unchanged: no Facebook login, adapter layer, classification without summaries, null as
information, watermark rules, dedup layers and findings, schema gates, verification method,
bootstrap mode, Gate A.

---

## 14. To verify and open items

### To verify before building on it

| Item | Tag |
|---|---|
| A Telegram Mini App loads from a tailnet-only HTTPS address on a phone with Tailscale on | `ASSUMED` — spike in Phase 4. If it fails, the plain site still works |
| Tailscale device sharing covers the number of friends on the free plan | `UNKNOWN` |
| Public source for Tel Aviv areas, the Old North split, and streets per area | Chosen by Ron 2026-10-05 (`DECISIONS.md` #81, #84). The areas and the Old North split: `VERIFIED`, the municipality's open `שכונות` dataset (71 entries, re-read 2026-10-05). Streets per area: not needed since the model decides the area (#167); a street table is recorded for later (#169) |
| Image download from the signed Facebook links works at fetch time | `VERIFIED` 2026-10-04 from the laptop: spike 1.1a, 5 of 5; then the task 1.12 check, 632 of 632, all JPEG; then the four real runs, 818 photos held (`ASSUMPTIONS.md` I6, `RESEARCH.md` §11). From the home server itself: still unverified |
| Apify spike: time window per group, all groups return data, comment flag honoured, real cost | `VERIFIED` 2026-10-04 (`SPIKE_1_1a.md`) |
| Shared-post content path | `VERIFIED` 2026-10-04: `sharedPost.text` and `sharedPost.media` |

### Open for Ron

What is open today is in `PHASE_2.md` §4 (the version 4 prompt items, the bill; Gate D is settled, #230). The measured
working day is Phase 3's (#225) and Ron's sign-off on the review of the first run is given (#224). Gate B,
the model's response and the Gate E failure fields are approved (#125, #151, #152).

### Recorded, not verified

Ron's position is that the tool stays personal: users are close friends searching with him or
alongside him. Whether the personal-use exclusion in the Privacy Protection Law covers this was
never checked legally (`ASSUMPTIONS.md` L1).
