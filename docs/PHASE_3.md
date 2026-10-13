# Phase 3 — The dashboard (semi-macro)

**Status:** a plan, written 2026-10-10 and revised the same day after Ron's answers. **Approved by Ron (2026-10-10):**
the content of Gate C (`DECISIONS.md` #242–#257) and its 31 open points (#262–#287); the task order and the DoD; the
technical choices (§5, #258–#260); the area grouping (§6, #261); Gate C's names and types and R1–R9 (#288, R7 amended
by #291); the plans for 3.4 and 3.5 (#289, #290). **Built:** 3.4 (2026-10-10, round 3), 3.5 (2026-10-11, round 4);
the admin created on the production store by Ron (2026-10-11); `jobs/reset_admin_password.py` (#294, 2026-10-11, round
5). **3.6: plan and its 16 points approved (#295–#300, 2026-10-11); built in round 6 (2026-10-11).** **Round 7
(2026-10-11):** #302 built (a post with no written price always at the bottom); Ron's direction for the site recorded
(#303–#315); 3.7's plan written, with 26 points. **Round 8 (2026-10-12): 3.7's plan and its 26 points approved, with
Ron's notes on the mock (#316–#331)**; built in the round: one sublet switch per profile (#317) and the orange-location
cap (#320); a new mock. **Round 9 (2026-10-12): points 27–30 and Ron's notes on the round-8 mock approved
(#332–#339); the bar redesigned; `Profile.from_stored_json`; 3.7's build step 1 built (the store generation counter and
its migration command, #316). **Round 10 (2026-10-13): Ron ran the migration on the production store; Ron's notes on
the round-9 mock (#340–#343); 3.7's build step 2 built: the read-only API for a guest, served from a dated copy of the
store.** No code before a task's plan is approved; no paid call before its
own go.
**Owner:** Ron
**Parent:** `BASELINE.md` §12 · **Schema:** `SCHEMA.md`, Gates A, B, C, E (approved), Gate D
(the key, #230, #232) · **Research:** `RESEARCH.md` §16 (the area grouping check)

**Phase goal:** anyone on the tailnet opens the site and scrolls and filters the real active posts without signing in
(#306, #307); Ron and his friends, signed in, save their profile, mark posts viewed, flag and report them, in a polished
UI (#257); the admin works the rejected, pending and archive lists, the flags, the reports and
the corrections. No Telegram (Phase 4), no scheduler (Phase 5): collection and classification stay commands Ron starts.

**Phase DoD (approved by Ron, 2026-10-10):**
1. **`BASELINE.md` §12's line:** Ron filters and sees real apartments in a browser, through Tailscale Serve, on his
   laptop in Docker.
2. A second account is created with a one-time key (#243) and signs in with a username and a password (#242); the
   admin resets its password (#242) and cancels an unused key (#243).
3. Each user's two search options (#245, #246, #247) filter and order the posts as `BASELINE.md` §8 says; the area is
   orange or not per user (#250); viewed posts come after unviewed ones (#62, #253).
4. A post the Gate D key ties to another shows as one card (#231); the four known pairs (§4) are the first check.
5. A flag ("lied") and a "wrong classification" report move a post to rejected for everyone; the admin restores it
   (#251), corrects a field (#256), or leaves it out; the report and the correction are kept (#255).
6. **DoD 4 moved from Phase 2 (#225), with `ASSUMPTIONS.md` I3 (#228):** a real working day is measured: the number of
   calls, the tokens and the cost of a day's classification, from the usage metadata and then the OpenAI bill; every
   paid run under its cap. Ron also judges how the interface looks on that day.
7. Tests pin: no user action writes a `RawPost` or a `Listing` (invariant 14); no per-user value is written on a post
   (invariant 12); no outgoing request carries a personal identifier (invariant 15).
8. The per-user YAML is gone (#47), and the items of §3 are resolved or explicitly re-planned.

---

## 3.0 Mandatory anchors

| Anchor | Source | State |
|---|---|---|
| Gate C's content | `DECISIONS.md` #242–#257, #262–#287 | Approved 2026-10-10 |
| Gate C's names and types; the Gate E amendments | `SCHEMA.md`, Gate C, and Gate E (amended 2026-10-10) | Approved 2026-10-10 (#288) |
| The technical choices: the framework, the journal mode, compare and set | #258, #259, #260 | Approved 2026-10-10 |
| The area grouping | #261 | Approved 2026-10-10 |
| The card, the field states, the colours | `BASELINE.md` §6, §7, §8 | Approved; binding on the UI (#257) |
| The same-listing grouping is derived by the Gate D key and never written on a post; computed once for all users, held in the site's memory, computed again only when the store changed | #230, #231, #232, #301 | Approved |
| The other-city name on the card is derived | #214 (`postmodel.rejects.other_city_name`) | Approved |
| Collection never filters by a user's criteria; per-user data never on the post | Invariants 12, 14 | In force |
| No personal identifier in any outgoing request | Invariant 15, #212 | In force |
| Libraries and site modules are chosen when this phase is planned, not before | `CLAUDE.md`; #23 | The framework chosen (#258); each library is added with its task's approved plan |

---

## Order of work (approved by Ron, 2026-10-10)

```
3.1 Gate C names and types  ┐
3.2 technical choices        ├─ Ron's decisions, no code
3.3 area grouping            ┘
  →  3.4 store: the Gate C records, the Gate E amendments, the lifecycle writes  →  3.5 accounts
  →  3.6 evaluation (policy/): corrections, the same-listing grouping, the two options, the order
  →  3.7 the site: lists, cards, profile, viewed, flag, report (the polished UI, #257)
  →  3.8 the admin lists  →  3.9 serving on the tailnet  →  3.10 the measured working day
```

3.6 needs no UI and can be built and tested beside 3.5. 3.7's visual design starts once 3.6 returns real data.

---

## 3.1 Gate C: names and types — DECIDED (#288, 2026-10-10)

`SCHEMA.md`, Gate C, approved: `User`, `SignupKey`, `Session`, `Profile` with two `SearchOption`s, `ViewedPost`,
`ClassificationReport`, `FieldCorrection`; points R1–R9; the Gate E amendments, written into Gate E. Nothing left for
Ron.

## 3.2 Technical choices — DECIDED (#258–#260, 2026-10-10)

The framework (§5.1, option A), the rollback journal with an explicit busy timeout (§5.2), compare and set for every
`PostLifecycle` writer (§5.3). Sessions (#263) and where the records live (#267) are decided with Gate C's points. What is
left is in the 3.4 and 3.5 plans.

## 3.3 Area grouping — DECIDED (#261, 2026-10-10)

§6 as proposed, with the four undecided entries in regular groups. Nothing left for Ron.

## 3.4 Store: the Gate C records and the lifecycle writes — PLAN APPROVED (#289); BUILT 2026-10-10 (round 3)

**Approved by Ron, with its eight points as proposed (#289)**; Gate C's names are approved (#288). **Built in round 3
(2026-10-10)**, with the deviations listed in `SESSION_LOG.md` (2026-10-10, round 3); one gap is open for Ron: R7
and the method table (below, "Open after the build"). No paid call, no network call; the production store is not
opened for writing by any step of this task.

**Scope.** (a) The eighth seam and its SQLite store; (b) the Gate C records as contracts; (c) `PostLifecycle` version 3
and `"misclassified"`; (d) compare and set for every `PostLifecycle` writer, in both stores, and every caller (#260);
(e) the explicit busy timeout (#259); (f) the per-user YAML removed (#47). **Not in 3.4:** the account logic (3.5), the
evaluation (3.6), the site (3.7), any write of a report or a flag (3.7, 3.8).

### (a) The eighth seam (#267; name approved, #289)

**`userdata/`, interface `UserDataStore`.** Its row in `CLAUDE.md`'s seam table:

| Module | Contract |
|---|---|
| `userdata/` | `UserDataStore`: what users and the admin write through the site — `User`, `SignupKey`, `Session`, `Profile`, `ViewedPost`, `ClassificationReport`, `FieldCorrection`. Not part of Repository; it never reads or writes a `RawPost`, `Listing` or `PostLifecycle`. SQLite only, in the same file as `store/` and `state/`, with its own tables and layout row |

**Methods (a Protocol in `userdata/base.py`, SQLite in `userdata/sqlite.py`; SQLite only, as `state/` is, #64):**

| Method | Contract |
|---|---|
| `create_admin(user, profile) -> User` | Inserts the admin and their profile in one transaction; raises if an admin exists or the username is taken |
| `create_user(user, profile, key_hash, now) -> User` | One transaction: finds the key by its hash, refuses unless it is usable (`KeyNotUsable`), marks it used by the new user at `now`, inserts the user and the profile; raises `UsernameTaken` (case-insensitive) |
| `get_user(user_id)`, `find_user_by_username(username)`, `list_users()` | Reads; the username is compared in lower case |
| `save_user(record, expected) -> User` | Compare and set, as for `PostLifecycle` below (sign-in counters, reset, disable) |
| `add_key(key)`, `list_keys()`, `save_key(record, expected)` | `save_key` is compare and set (cancel) |
| `find_key_by_hash(key_hash) -> SignupKey \| None` | The key with that hash, used or not; sign-up's lookup (#293, added 2026-10-11) |
| `add_session(session)`, `find_session(token_hash)` | |
| `end_session(token_hash, now)`, `end_sessions(user_id, now, keep=None)` | Sets `ended_at` on one session, or on every open session of the user except `keep` (#263, R3, R7) |
| `get_profile(user_id)`, `save_profile(profile)` | Whole-record replace (point 4 below) |
| `mark_viewed(user_id, listing_id, at)` | Inserts only if absent: a reopen keeps the first time (#276) |
| `unmark_viewed(user_id, listing_ids)`, `viewed_listing_ids(user_id) -> set[str]` | |
| `add_report(report)` | Refuses a second open report by the same reporter for the same post (#278, R4) |
| `find_reports(listing_id=None, status=None)`, `save_report(record, expected)` | `save_report` is compare and set |
| `add_correction(correction)` | Refuses a second correction in force for the same post and field |
| `find_corrections(listing_id=None, in_force=True)`, `save_correction(record, expected)` | `save_correction` is compare and set (removal) |

**Storage**, as #65 stores records: one JSON document per record, written and read by the pydantic model, plus lookup
columns only: `users` (`user_id` key, `username_lower` unique), `signup_keys` (`key_id` key, `key_hash` unique),
`sessions` (`token_hash` key, `user_id`), `profiles` (`user_id` key), `viewed_posts` (key `user_id` + `listing_id`),
`reports` (`report_id` key, `listing_id`, `reported_by`, `status`), `corrections` (`correction_id` key, `listing_id`,
`field`, and a unique index on `listing_id` + `field` over the corrections in force). A `layout_version` row `userdata`
= 1; a mismatch refuses to open, naming the module (#65). The same minimum SQLite version check as `store/` (3.38.0).
One connection per operation; writes in `BEGIN IMMEDIATE`.

**Two seams, two transactions.** A report (in `userdata/`) and the post's move to rejected (`PostLifecycle`, in
`store/`) cannot be one transaction without merging the seams. Proposed order: the report first, then the lifecycle;
if the lifecycle write fails, the report is stored and the admin's reports list shows "report stored, post not
rejected", with a retry (3.8). Point 3 below.

### (b) The Gate C records as contracts

`contracts/user.py` (`User`), `contracts/signup_key.py` (`SignupKey`), `contracts/session.py` (`Session`),
`contracts/profile.py` (`Profile`, `SearchOption`, `RangeCriterion`, `DateRangeCriterion`, `CriterionLevel`),
`contracts/viewed_post.py` (`ViewedPost`), `contracts/classification_report.py` (`ClassificationReport`,
`ReportableField`), `contracts/field_correction.py` (`FieldCorrection`). Strict pydantic models like `PostLifecycle`,
datetimes checked by `require_utc`. Every rule of Gate C's tables is a validator: the username's characters and length;
the pairs set together (`used_by`/`used_at`, `resolved_by`/`resolved_at`, `removed_by`/`removed_at`); `signup_key_id`
`None` exactly for the admin; ranges with at least one end and `min` ≤ `max`; half rooms; floor ≥ -1; `size_sqm` `None`
in `room`; `price_min` ≤ `price_max`; areas 1–71, sorted, distinct; the note ≤ 500 characters; `fields` non-empty and
distinct. `FieldCorrection.model_value` and `corrected_value` are validated against the Gate B type of `field`, read from
`Listing`'s own field definition, so there is no second copy of Gate B's types (#284).

### (c) `PostLifecycle` version 3

`"misclassified"` added to `rejection_reason`; the consistency rule "`"flagged"` or `"misclassified"` requires
`flagged_by` and `flagged_at`"; `schema_version` 3 (#285). `PostLifecycle.from_stored_json` reads a version-1 or
version-2 document as version 3 (no field differs between 2 and 3); a record is written back as version 3 on its next save,
as version 2 was (#152, task 2.2). The value goes last in the `rejection_reason` `Literal` of
`contracts/post_lifecycle.py`, which is where Gate E's order is written today (#279); `postmodel/rederive.MODEL_REASONS`
is unchanged (it is not a model reason). Gate E's approved text is
amended in `SCHEMA.md` only when Ron approves E-1 to E-5.

### (d) Compare and set for every `PostLifecycle` writer (#260)

**The contract change (both stores, `store/base.py`, `store/sqlite.py`, `store/local_json.py`):**
- `save_lifecycle(record, *, expected: PostLifecycle | None) -> PostLifecycle`. `expected=None`: writes only if the post
  has no lifecycle record. Otherwise: writes only if the stored record, read through `PostLifecycle.from_stored_json`,
  **equals** `expected` (model equality, so a version-1 document read as version 3 compares equal to what the writer
  read). Else raises `StaleRecordError(listing_id)` (new, in `store/base.py`) and writes nothing. `KeyError` if the post
  is not stored, as today.
- `save_classification(listing, lifecycle, *, expected: PostLifecycle)`: the same check on the lifecycle; on a stale
  record neither the `Listing` nor the lifecycle is written.
- **SQLite:** the read, the comparison and the write are in the one `BEGIN IMMEDIATE` transaction, so no other writer
  can come between them. **local_json:** read, compare, write, with no lock: correct for one process only; it is the test
  store (point 8).
- `upsert_with_lifecycle` is unchanged: it already creates only.

**Every caller (found by search, 2026-10-10):**

| Caller | Today | With compare and set | On `StaleRecordError` |
|---|---|---|---|
| `pipeline._repair_missing_lifecycles` | `save_lifecycle(initial)` | `expected=None` | Another writer created it: logged, skipped |
| `pipeline._store` (stored canonicals outside the batch; batch posts after `upsert_with_lifecycle`) | `save_lifecycle(record)` with the record dedup built | `expected=` the record dedup **read** from the store; `DedupResult` gains those records. A post that had no record is written by `upsert_with_lifecycle` alone | **Merge, then retry** (point 2): re-read; the site's fields (`flagged_by`, `flagged_at`, `flag_note`, a `"flagged"` or `"misclassified"` state and reason, and `classification_failures` / `last_classification_error` set back by the admin's retry) are taken from the fresh record; the run's fields (`last_published_at`, `images`, a state change from a repost of an archived post or from the pre-model re-check) from the run's. When both changed the state, the flag or report wins. At most 3 attempts; then the run fails and no watermark moves (invariant 2) |
| `classification_run` (`save_classification`, `_save_failure`) | Re-reads right before writing (#182) | `expected=` that fresh read | Re-read once; if still `"pending"`, derive again and write; else `"discarded"`, as today |
| `jobs/rederive_rejections` | Re-reads, raises if the status changed | `expected=` that read | Not written; reported, as a changed record is today |
| `reclassification_run.apply_proposals` | Re-reads; "not written" if changed (#220) | `expected=` that read | "not written", listed; exit code 2 (#220) |
| The site (3.7, 3.8) | — | `expected=` the record the page read | The user is told the post changed; the page reloads |

The contract test `test_save_lifecycle_is_whole_record_replace_and_last_write_wins` is replaced by the compare-and-set
tests below. `CLAUDE.md`'s Repository row and store-writer paragraph change with it (written this round: the decision;
the method signature when built).

> **⚠️ LOST IN ROUND 9, TO BE RESTORED FROM GIT BY RON.** A faulty edit on 2026-10-12 (round 9) deleted everything
> from 3.4's "(e) The busy timeout (#259)" to the end of 3.6: 3.4 (e), (f), its tests, what could not be verified and
> its points, the open points after the build; all of 3.5; all of 3.6. The text was not changed after round 7's commit
> (`9530e16`), so it is intact in git: put it back here, between 3.4's "(d) Compare and set …" and "## 3.7". 3.7's
> heading, opening and (a)–(d), deleted by the same edit, were restored in round 10 from what was read in rounds 8 and 9.

## 3.7 The site — PLAN APPROVED 2026-10-12 (round 8, #316–#331; round 9, #332–#339); build steps 1 and 2 built

The lists and the cards (`BASELINE.md` §6) with these approved display rules (`BACKLOG.md`, "Recorded for a later
phase"): the card's main time is the last publication, shown relative (#122); the repost log shows the earliest
`posted_at` of the post and its duplicates (#75 A); rooms on a room post, "1 of N" (#120); size on a room post (#121);
the entry date's year never displayed (#115); on a card whose media came through a repost, the video link comes from
the repost (#70, #72.4). The profile editor with the two options, the profile's one sublet switch (#317), "copy from the
other option" (#245–#247, #272), and the area filter grouped (#248, #249). Viewed: opening a card, "mark as not viewed" (#253). Flag "lied"
and "wrong classification" (#173, #254).
**The polished UI is built here (#257)**, with Ron's design skills, when this task is reached; `BASELINE.md` §6–§8 stay
binding. The framework is decided (#258). **Needs from Ron:** the plan's approval; the design direction, at the task.

**Required of 3.7's plan by #301 (Ron, 2026-10-11):** the same-listing grouping (`dedup/stage_b.derive_cards`) is
computed **once for all users**, held in the site's memory, and computed again **only when the store changed** (a
collection run, a classification run, a flag, a report, a restore, a correction); only each user's evaluation, filtering
and order (`policy/`) run per request. The plan must say **how the site knows the store changed**, and must **measure a
real page load**. From 3.6 (#300): a "lied" flag on a card is written on every one of `Card.canonical_ids`; a "wrong
classification" report on `Card.shown_id` only.

**The plan below was written on 2026-10-11 (round 7) and approved by Ron on 2026-10-12 (round 8), with his answers
and his notes on the mock written into it (#316–#331); in round 9 Ron's notes on the round-8 mock (#332–#339); in round 10 his notes on the round-9 mock (#340–#343).** It follows Ron's direction (#303–#315), #302 (a post with no
written price is always at the bottom) and #320 (an orange location caps a post at the middle), both built. Build steps 1
(the store generation counter) and 2 (the read-only API for a guest) are built (rounds 9 and 10). The mock, filled from real active posts read-only, is in `data/mock/`
(gitignored: real people's text and phones); the round-10 mock replaces round 9's; it is a look, not the design.

**Until 3.9 the site runs on a dated copy of the production store (#331): anything Ron saves there (preferences, viewed
marks, flags, reports) stays in the copy** and never reaches the production store.

### (a) Scope

**In 3.7:** the API and the pages for everyone who is not the admin acting as admin: the list (home), the opened post,
the filter bar, sign-in, sign-up with a key, the forced password change, the preferences page; the user's writes
(viewed, "mark as not viewed", a "lied" flag, a "wrong classification" report, saving the preferences); the session
cookie; the same-listing grouping held in memory (#301); a command that serves the site on the laptop. **Not in 3.7:**
the admin's pages (3.8; the admin signs in through 3.7's page); serving through Tailscale and Docker (3.9); Telegram
(Phase 4); favourites, a map, a language switch (#310).

### (b) What I took from Ron's reference screenshots, and what I did differently

| Reference | Taken | Different, or left out |
|---|---|---|
| The phone list | One card under the other (#303); the photo at the start (the right, in Hebrew) beside a large price; the location line with a pin; the relative time; feature chips; a WhatsApp button beside a wide button | No heart (favourites, #310); no floating "map" button (#310); no language switch (#310); the wide button opens the post on our site, and the link to the original sits inside (c) |
| The opened post on a phone | Full screen, a back arrow at the top (#313); a photo carousel with dots; a price block; a rows table (rooms, floor, sqm, entry date), not written shown as "לא צוין" in grey (#321); a "features" block of chips, the known ones lit and the unstated ones grey; a sticky bottom bar with the main action | Our chips use the colours of #309 (green, plain, red, grey, orange), not just lit and grey; no chips for features we do not store (a safe room, a shelter, renovated, pets); the bottom bar holds "to the original post" and WhatsApp, no map |
| The desktop grid | A grid (#303); the photo on top; the first lines of text as the heading (here the poster's own text, #312); a grey location line; a row of four stats with icons | The source badge (we have one source); our fourth stat is the entry date, the time moves to the card's foot; the glow (#308) |
| The preferences pages | Sections as white cards on a warm background; a range as two number boxes and a slider, with a "don't care" button (it is our `None`); entry-date quick chips ("immediate", "from the 1st of next month", "another date"); feature tiles with an icon that light up when chosen; a summary with "edit" per section; a live count "with the current settings: N posts" | Not a step-by-step wizard: one page, two tabs (room, empty apartment) and "copy from the other option" (#272); every category carries its level, "preference" or "must" (§8), where the reference has one global "also show posts that do not mention a feature"; no property types we do not have (an apartment for roommates as a third kind); no email; it is not the filter (#314): the home page has its own bar |

What the references show and the approved rules do not have, listed for Ron (point 25), not added: a filter by street,
a map, favourites, pets, a safe room or shelter, "renovated", a third kind "apartment for roommates", an email, the
source badge, a "results include only the last week" line.

### (c) Every item, on the closed card and in the opened post (#303, Ron's request f) — APPROVED with #321–#328 (#330, point 9)

`BASELINE.md` §6, §7, §8 and the marks Ron listed, with Ron's notes on the mock (2026-10-12). "Desktop" is the grid card
and the dialog (#304); "phone" is the stacked card and the full-screen post (#313). **—** means not shown there.

**The rules over the whole table.** No glyphs anywhere, on the card or inside: colour plus words only, each item keeping
its accessible name (#323). Every attribute not written reads "לא צוין" in grey (#321), except price and entry date,
which take the important-missing badge. **On the closed card only the green chips** (#326), plus three items that are
not green: the red "women only" icon, the important-missing badge, the orange location line. The price, the location
line, the four stats, the kind and the foot are not chips and stay (#332). **The kind is "דירה שלמה" everywhere**
(#339). **The three buttons of the foot are outlined in their colour** (#338): "פייסבוק" blue, "וואטסאפ" green (another
green than the tier's glow), "דיווח" a soft light red. **The card is built of fixed slots** (#341): the photo, the kind
line, the price, three lines of text, two lines of location, the four stats, one row of chips, and a foot of two fixed
rows; each slot keeps its place and size when it is empty, so every card is the same height and nothing moves,
whatever it holds (WhatsApp or not, the report button or not, reposts or not, no photo, a short or long text, no price,
the "women only" icon, an orange location). **The foot** (#340): the time at the right with the three button slots at
the left, in fixed places; under the time, on its own line, "פורסם N פעמים" only when there was a repost, its line kept
when there was none. A guest's report slot stays, empty (#341). **Inside, every chip in its colour**
(green, orange, grey, plain, and red for a preference not met).

| # | Item | Closed card, desktop | Closed card, phone | Opened post, desktop (dialog) | Opened post, phone (full screen) |
|---|---|---|---|---|---|
| 1 | Photos (#327; lazy-loaded, #330) | **A carousel of every photo on the card itself** (4:3, cropped): arrows on hover, dots, "1/5" in a corner (#332, point 30); only the first photo is loaded with the page, the rest as they come into view | **A carousel at the start, swiped**, square, dots | A carousel of every photo, arrows and dots; click enlarges | A swiping carousel at the top, dots |
| 2 | Video or reel (photos only are downloaded) | A "וידאו" chip on the photo, in words. **A post with no photo but a video or reel** (round 9, Ron's instruction after the check of A4: three of 139 active posts, each a single reel) shows, in the photo's place, the link "צפייה בסרטון בפייסבוק", never "אין תמונות" | The same | "Watch the video on Facebook" link per video; from the repost when the media came through one (#70, #72.4) | The same |
| 3 | The poster's full original text | The first 3 lines, cut, as the card's heading (#312) | The first 2 lines | The whole text, unchanged, line breaks kept, `dir="auto"` | The same |
| 4 | **Link to the original post** | A small "פייסבוק" button in the card's foot, outlined in blue (#338); following it does not mark the card viewed (#330, point 10) | The same, in the foot | **A main button "to the original post" in the dialog's foot** | **In the sticky bottom bar**, beside WhatsApp |
| 5 | Price, "X/Y" when several (#95) | Large, at the top of the text column | Large, at the top beside the photo | The price block, large | The same |
| 6 | Price not written | The important-missing badge "אין מחיר" (a dark slate badge, words only, #330 point 6) | The same | The same, in the price block | The same |
| 7 | Entry date as written; its year never shown (#96, #115) | The fourth stat: the text as written, cut to one line | In the line under the price | A row, the text as written in full | The same |
| 8 | Entry date not written | The fourth stat: the badge "אין תאריך כניסה" | The same | The row, the same badge | The same |
| 9 | Location: areas and streets | One line: the areas' names · the streets as written; plain, green on `"match"`, **orange when the location is orange** (#250, #320) | The same, two lines at most | Rows: "area" (each name), "street" (as written), the names the post itself gave (as written) | The same |
| 10 | No area: unclear (a street given) or not written (#110) | The orange line "האזור לא ברור" with the street / "מיקום: לא צוין" in grey | The same | The same, in the rows | The same |
| 11 | Listing kind, sublet mark (#246) | The kind in words, "חדר בדירת שותפים" / "דירה שלמה" (the one name, #339), and "סאבלט", above the price (not a chip; §8: every card shows the option it answers) | The same | The same, under the price | The same |
| 12 | Kind unclear or not written, marked (#273), and the option it answers (§8) | The orange mark "סוג לא ברור · מוצג כ: חדר" in the kind's place (#332) | The same | The same | The same |
| 13 | Phone(s), `name-number` (§6) | — | — | Each number as a `tel:` link, with its name | The same |
| 14 | **WhatsApp** (#311), when the post has a mobile number (#330, point 22) | A small "וואטסאפ" button in the foot, outlined in green (#338) | A WhatsApp button, outlined in green | A button per mobile number | In the sticky bottom bar (the first mobile number; the others in the rows) |
| 15 | Publication time: the last publication, relative (#122) | In the foot's first row: "לפני 5 שעות" | The same, in the foot | In the price block | The same |
| 16 | Repost log, earliest first (#75 A) | "פורסם 3 פעמים" on its own line under the time, only when there was a repost (#340) | The same | A list: each publication, relative and Israel time, the earliest first | The same, collapsed |
| 17 | Broker (no broker is positive, #309) | A chip only when green ("ללא תיווך") | The same | Features block, in its colour ("לא צוין" grey) | The same |
| 18 | Rooms; on a room post "1/N" closed (#325), "1 of N" inside (#120) | First stat; a room post "1/2.5"; total not written: "1" with a grey "סה״כ לא צוין" under it (#332) | In the line under the price | A row, #120's wording | The same |
| 19 | Floor, "X/Y" when the floors are written (#98, #106); 0 ground, -1 basement | Third stat; "לא צוין" grey | — | A row | The same |
| 20 | Size; on a room post "X sqm for the room, of Y" (#99, #121) | Second stat; "לא צוין" grey | — | A row | The same |
| 21 | Balcony | A chip only when green | The same | Features block, in its colour; not written "לא צוין" grey (#321) | The same |
| 22 | Parking | A chip only when green | The same | Features block; not written "לא צוין" grey (#321, replacing §6's "none") | The same |
| 23 | Elevator, air conditioning | Chips only when green | The same | Features block | The same |
| 24 | Furnished yes / partial / no (#102) | — | — | Features block; "yes" plain (#330, point 8) | The same |
| 25 | Arnona, house committee (#101, #116) | — | — | Two rows: the amount, "included", orange "unclear", or "לא צוין" grey | The same |
| 26 | "Women only" shown because the bar does not hide it (§8) | **The red "נשים בלבד" icon chip** (kept, #326) | The same | The same, under the price | The same |
| 27 | "Women preferred" (#117) | — (a plain chip, #326, #332) | — | A plain chip under the price | The same |
| 28 | **The glow** (#308, #322) and the tier (#323) | The ring and soft shadow in the tier's colour; **no glow while the option holds no preference**; a small "i" **in the card's top-left corner, over the photo and inside the card, on a faded semi-transparent background** (#337) shows the tier's label on hover; no label text | The same, over the photo's top-left corner; the "i" on tap | The tier's label and the reason for the bottom tier, in words, at the top of the price block (#332) | The same |
| 29 | The field colours (#309) | Only the green chips (#326) | The same | On every row and chip | The same |
| 30 | "Corrected by hand" (#256) | The word "תוקן" beside a corrected item that is shown closed | The same | "תוקן ידנית" on each corrected row or chip | The same |
| 31 | Viewed (#62, #253); signed-in only | The card dimmed, the word tag "נצפה" | The same | "Mark as not viewed" in the foot | In the top bar's menu |
| 32 | Flag "lied" (#300); signed-in only | **A report button "דיווח" in the card's foot** (#328), outlined in a soft light red (#338): a small menu, "the post lies" (with a confirmation) | The same | In the foot's menu, with a confirmation | In the top bar's menu |
| 33 | "Wrong classification" report (#254); signed-in only | The same report button: "wrong classification" opens the post with the form | The same | The same menu: a form, the fields as Hebrew labels, a note of up to 500 characters | The same, full screen |
| 34 | The other city (#214) | — (an other-city post is rejected and never reaches a user; the admin's list shows it, 3.8) | — | — | — |

**The link to the original post** (Ron: it must exist, its place the reviewer's recommendation, approved, #330 point
10): a main button in the opened post and a small link on the closed card; following the link from the closed card does
not mark the card viewed (#253 marks on opening).

### (d) The glow (#308) and the field colours (#309) — DECIDED (#320, #322, #323, #330 points 4, 5)

**The glow** (#330, point 4): a thin ring and a soft shadow in the tier's colour, strongest for green; **green** for
`"preferences_met"`, **orange** for `"critical_met"`, **red** for the bottom (`"unknown"`). **No green glow while the
option that admits the post holds no preference at all** (#322): every category of that option is `None` or at the
level `"critical"`; such a card has no glow. Orange and red are unchanged. The glow never changes the order.

**The tier's label** is not text on the closed card (#323): a small "i" in the card's corner shows it on hover (desktop)
or tap (phone): "מתאים לכל ההעדפות", "מתאים חלקית", "חסר מידע: …" with the reason for the bottom ("no price", "kind
unclear", "area unclear", "entry date not written" for a critical one). The "i" is a button whose accessible name is the
label, so a screen reader reads it.

**An orange location** caps the tier at the middle (#320, built in `policy/evaluate.py`): such a card glows orange at
most, never green.

**Colour blindness** (#323, #330 point 5). **No glyphs anywhere**: no ✓, no warning sign, no ✕ or ? on the tier or the
chips; colour plus words only. Every chip carries its value in words ("מרפסת", "ללא תיווך", "חניה: לא צוין"), and every
chip and the card keep an accessible name that says the state ("balcony: yes, matches your preference"). The hues are
picked apart in lightness as well as hue (a blue-leaning green, an amber, a crimson) and checked in the build with a
colour-vision simulation (chrome-devtools' rendering emulation) and the accessibility review. **Ron accepts that a
colour-blind user needs the "i" to read the tier** (#323).

**How the field colours (#309) sit with 3.6's `FieldState`.** `Evaluation.fields` holds a `FieldState` for the ten
profile categories only, for the option that admitted the post. The colour of a field is:

| `FieldState` | Colour |
|---|---|
| `"match"` | green |
| `"mismatch"` | red (only a preference can show it: a failed critical category hides the post) |
| `"not_written"` | grey, the words "לא צוין" (#321) |
| `"unclear"` | orange |
| `"not_applied"` (no value in the option), and every field that is not a category (elevator, air conditioning, furnished, arnona, house committee, building floors, room size) | from the post's own value: a **known positive** green (broker `False`, balcony, parking, elevator, air conditioning `True`); a known negative plain; not written grey "לא צוין"; unclear orange; a field with no positive or negative (rooms, floor, size, price, entry date, arnona, house committee, furnished, "yes" included, #330 point 8) plain |
| the area | orange when `area_orange` or no area and a street given; grey "לא צוין" with no location; green on `"match"`; else plain |
| price and entry date not written | the important-missing badge (a dark slate badge with the words, #330 point 6), not grey |

**`policy/colours.py`** (#330, point 18), a small pure function, `field_colours(seen, evaluation) -> Mapping[str,
Colour]`, computes the table above on the server, so the browser holds no rule, and says whether the card glows (#322,
from the admitting option's values). It imports the wanted values from `policy/evaluate.WANTED` (one implementation,
#269) and adds the two the card alone uses (elevator, air conditioning `True`, #309).

### (e) The header, the filter bar on the home page, and the preferences page (#305, #314, #315) — DECIDED (#317, #324, #329, #330, #333–#336, #339); the bar redesigned in round 9

**Right to left, nothing on the left (#324), but the logo (#333).** The site is Hebrew only. The header and the bar
start at the right edge, as Hebrew reads; **the one deliberate exception is the logo, on the left** (#333). On a wide
screen nothing else sits on the left side of the header or the bar.

**(i) The header** (#333, #334). At the right, **the user area**: a guest sees "התחבר" (sign in) and beside it "הירשם"
(sign up); a signed-in user sees their username, and clicking it opens a menu with "ההעדפות שלי" (the preferences page)
and under it "התנתק" (sign out). At the left, **the logo** "TLV Apartment Hunter": a designed mark and wordmark, light
and cool (pale sky and teal), not the name set in the page's font. Nothing between them. **The header has its own
background** (#342), a cool tint, distinct from the white filter bar under it. **The user button** (#343): one pill
with a round avatar (the username's first letter on a sky-to-teal gradient), the username and a chevron; on a phone the
avatar and the chevron only. A guest's "התחבר" and "הירשם" are pills of the same height.

**(ii) The filter bar, redesigned (round 9, the reviewer's proposal for #335).** Ron found round 8's bar unclear. Its
two hard parts were the "option being edited" (one row of controls that silently edited whichever kind chip was last
clicked) and two buttons about saving. The new bar removes both. Under the header, sticky as the list scrolls:

- **Row 1, what is shown:** three labelled switches, "חדר בדירת שותפים", "דירה שלמה" (#339) and "גם סאבלט" (the
  profile's one switch, #317, #329). A switch reads on or off by its track and position, with its label always in
  words. **When both kinds are off the sublet switch is disabled, with the line "בחרו חדר או דירה שלמה כדי לראות
  סאבלטים".**
- **One values row per kind that is on, labelled with the kind's name.** "חדר בדירת שותפים:" then its controls; "דירה
  שלמה:" then its own. Each kind's values are visibly its own (#245), and no control edits a hidden target. Each row:
  "אזורים" (the grouped popover of §6, #248, #249, #261), "מחיר" (min and max, #95), "חדרים" (halves, #271), and "עוד"
  (floor, sqm in the "דירה שלמה" row only (#247), no broker, parking, balcony, entry date with "immediate" as a quick
  chip (#270), "hide women only"; each category with its level, "העדפה" or "חובה", #330 point 15). A control holding a
  value is a filled chip with the value in words ("מחיר עד ₪5,500"; a "must" adds the word "חובה", no glyph, #323); its
  "נקה" clears it to "don't care". A kind that is off has no row.
- **The status line, at the end of row 1 (still from the right): the count and where the bar stands, in words.** As
  saved: "102 מודעות · לפי ההעדפות השמורות". Changed: "87 מודעות · סינון זמני, שונה מההעדפות שלך" and **the button
  "ההעדפות שלי", which resets the bar to the saved preferences** (#335). A guest's line says only the count. **There is
  no "save as my preferences"** (#335, amending #315): preferences change only on the preferences page.
- **On a phone:** row 1 with the three switches (they wrap to two lines when needed), then the status line with "סינון
  (3)" (the number of controls holding a value) and, when changed, "ההעדפות שלי". "סינון" opens a full-screen sheet
  with the kind rows, labelled as on a desktop, and "הצגת 87 מודעות" at its foot.
- **How the bar's state is evaluated** (unchanged): it holds the profile's shape, the two `SearchOption`s and
  `include_sublets`; each list request sends it; the server builds a **transient `Profile`**, validated by `Profile`'s
  own rules and never stored, and passes it to `policy.evaluate`. "Changed" is the bar's state compared, field by field,
  with the saved profile, in the browser (a guest has no saved profile, so no "changed").
- **Its lifetime:** the tab's memory and `sessionStorage` (#330, point 14): a reload keeps a changed bar; a new visit
  starts again from the saved profile (signed in) or empty (a guest).

**(iii) The preferences page.** One page, reached from the user menu's "ההעדפות שלי" (#334). **At the top, the
profile's one sublet switch** (#317), with the line "sublets are shown in the options you switched on". Then two tabs,
"חדר בדירת שותפים" and "דירה שלמה" (#339), each with its on/off switch and "copy from the other option" (#272: every
value but on/off; never the sqm range into the room option; the sublet switch is the profile's and is not copied).
Sections as cards: areas (the grouped list in full); price; rooms; floor; sqm ("דירה שלמה" only); entry date (from and
until, quick chips); features (no broker, parking, balcony as tiles, #269); "women only". Each range is two number boxes
with a slider and a "don't care" button; **each category has its level** as a two-way switch "preference / must", with
one line saying what a "must" hides. A summary at the top and the live count "with these preferences: N posts" (#330,
point 24). A sticky "save" bar at the right; leaving with unsaved changes asks first. **The only place preferences are
saved** (#335). From Phase 4 the page also says these preferences drive the alerts.

**Which settings where.** Every value of the profile is in both, since the bar must hold a whole `Profile` for
`evaluate`. **Only on the preferences page:** saving, "copy from the other option", the summary, the explanation of the
levels, and (Phase 4) the Telegram link. **In the bar:** the kinds and the sublet switch, then per kind areas, price,
rooms and "עוד".

**Sign-up** (#336, amending #330 point 13): the key, a username, the password twice; **no "use my current filter"
box**. A new user starts with #268's defaults and sets preferences on the preferences page.

### (f) The screens

| Screen | Who | Contents |
|---|---|---|
| The list (home) | Everyone | A header (#333, #334): at the right the user area ("התחבר" and "הירשם" for a guest; the username and its menu, "ההעדפות שלי" and "התנתק", signed in); at the left the logo; the filter bar of (e); the count; the grid (desktop) or the stacked list (phone); an empty state ("no post fits; clear a filter"); unviewed before viewed (#62) |
| The opened post | Everyone; writes signed-in only | The dialog over the list on a desktop (#304), full screen with a back arrow on a phone (#313); its own address (`/post/<id>`), so the browser's back closes it; (c)'s items |
| Sign-in | A guest | Username, password; the refusals of 3.5 (wrong, the delay with the seconds to wait, disabled) |
| Sign-up with a key | A guest | The key, a username (the rules of #262 shown), the password twice (no "use my current filter", #336); signed in on success |
| The forced password change | A user with `must_change_password` | The only screen reachable (Gate C, `Session`); the same form serves "change password" from the menu |
| The preferences page | A user | (e)(ii) |

The admin's pages are 3.8's.

### (g) The API

One origin: FastAPI serves `/api/*` and the built pages. Every response is JSON, except the photos and the pages.
**Guest** = no valid session; **user** = a valid session; **admin** = the admin's session. Every `/api` write takes JSON
only and checks the `Origin` header (point 19).

| Endpoint | Who | Returns |
|---|---|---|
| `GET /api/session` | Everyone | `{user: null}` or `{username, is_admin, must_change_password}` |
| `POST /api/sign-in` `{username, password}` | Guest | Sets the cookie; or a refusal: `wrong`, `delayed` (with the seconds), `disabled` (3.5) |
| `POST /api/sign-out` | User | Ends the session (`accounts.sign_out`), clears the cookie |
| `POST /api/sign-up` `{key, username, password}` | Guest | Creates the user (`accounts.sign_up`) with #268's default profile (#336), signs in; or a refusal (the key not usable, the username taken or invalid, the password too short) |
| `POST /api/password` `{current, new}` | User (also with `must_change_password`) | `accounts.change_password`: the other sessions end (R3) |
| `GET /api/reference` | Everyone | The 71 areas with their display names, the region groups (§6), the reportable fields (#277) |
| `GET /api/profile` | User | The saved profile's two options and its sublet switch (#317) |
| `PUT /api/profile` `{room, whole_apartment, include_sublets}` | User | `save_profile` (whole record, #289 point 4); the saved profile |
| `POST /api/cards` `{room, whole_apartment, include_sublets}` | Everyone | The ordered cards for that filter (`policy.order.ordered`): for each, the shown post's summary (the closed card's items of (c)), its tier, whether it glows (#322), option, kind mark, field colours, area orange, women-only icon, corrected fields, every photo's address (the closed card's carousel, #327; loaded lazily by the page), the last publication and the number of publications, and `viewed` for a user; and the count |
| `GET /api/posts/{listing_id}` | Everyone | The opened post of the card holding that post (any of `Card.post_ids` finds its card): every item of (c), every photo's address, the publications, phones, WhatsApp links; 404 for anything else |
| `GET /api/photos/{listing_id}/{file}` | Everyone | The photo file from `<store_root>/images/`, only when it is a `PostImage.local_path` of a post of a current card; 404 otherwise (no path is built from the request) |
| `POST /api/viewed/{listing_id}` | User | `mark_viewed(user, Card.shown_id, now)` (#276) |
| `DELETE /api/viewed/{listing_id}` | User | `unmark_viewed(user, Card.post_ids)` |
| `POST /api/flag/{listing_id}` `{note?}` | User | The "lied" flag on every one of `Card.canonical_ids` (#300), (i) below |
| `POST /api/report/{listing_id}` `{fields, note?}` | User | The report on `Card.shown_id` (#300), (i) below |
| Every other path | Everyone | The built page (`index.html`), so `/post/<id>` and `/preferences` load the site |

**No rejected, pending or archived post is ever returned to a non-admin:** the cards come only from
`dedup/stage_b.derive_cards` (its members are active canonicals with a `Listing`) and only those `evaluate` shows;
`/api/posts` and `/api/photos` answer only for a post of a current card. A test pins each state (j). The admin's
endpoints are 3.8's.

**The session cookie** (read 2026-10-11: starlette.dev "Responses", `Response.set_cookie(key, value, max_age=None,
expires=None, path="/", domain=None, secure=False, httponly=False, samesite="lax", partitioned=False)`, where FastAPI's
"Response Cookies" page sends; MDN "Set-Cookie", modified 2026-09-01). **Proposed:** name `tlv_session`; the value the
session token of 3.5; `httponly=True` (no script reads it); `secure=True` (MDN: sent only over `https:`, "except on
localhost", so the laptop's `http://localhost` works and Tailscale Serve's HTTPS does); `samesite="strict"` (MDN: sent
only for requests from the same site); `path="/"`; `max_age=2592000` (30 days, as the session's `expires_at`, R5; MDN:
`Max-Age` has precedence over `Expires`); no `domain` (the host only); `partitioned` not passed (Python 3.14+ only). Every
request checks the token with `accounts.session_user` (valid, not ended, not expired, the user not disabled); a cookie
that fails it is cleared. Starlette's defaults (`secure=False`, `samesite="lax"`) are never relied on: each attribute is
passed, and a test reads the `Set-Cookie` header.

### (h) The grouping held in memory (#301), how the site knows the store changed, and the measured page load

**Held:** one `Grouping` object in the site's process: the cards (`derive_cards`), each card's shown `KeyPost` (its seen
`Listing`, for `evaluate`), and the store generation it was computed at; the photo memo (`PhotoHashes`) lives beside it
across recomputes, so only changed files are hashed again. Per request, only the per-user part runs: `evaluate` of each
card's shown post against the bar's transient profile, the user's `viewed_listing_ids`, `ordered`, the field colours.
One recompute at a time (a lock); requests during it wait for it, so a user who just flagged never sees the old card.

**How the site knows the store changed** (the job commands are separate processes, so nothing in the site's memory
hears them). **Decided: option 1 (#316)**; the migration command is built at build step 1. The two ways weighed, point
11:

| | How | For | Against |
|---|---|---|---|
| **1 (recommended)** | **A store generation counter kept by SQLite itself:** a one-row table and `AFTER INSERT`, `AFTER UPDATE` and `AFTER DELETE` triggers on `raw_posts`, `post_lifecycle`, `listings` (store) and `corrections` (userdata) that add 1. Each request reads the one row (one small query); a different number means recompute. Triggers are part of the database schema (sqlite.org "CREATE TRIGGER": only `TEMP` triggers are limited to the connection that made them), so every writer, in every process, present or future, moves it, and no job command changes | Exact: recomputes on a post change only, never on a viewed mark, a sign-in or a profile save. **Checked in memory (scratchpad, SQLite 3.45.3, 2026-10-11): the store's `INSERT … ON CONFLICT DO UPDATE` fires the `INSERT` trigger for a new row and the `UPDATE` trigger on a conflict, also when the value is unchanged**; sqlite.org's UPSERT page does not say | **A layout change** of `store` and `userdata` (a table and triggers: layout versions 2), so a one-time migration of the production file, with a dated backup, by a new command (a seventh store writer) |
| 2 | `PRAGMA data_version` on one connection the site keeps open (sqlite.org: two calls on the same connection differ "if changes were committed to the database by any other connection in the interim", other processes included) | No layout change | It moves on **every** commit by another connection, the site's own viewed marks, sign-ins and profile saves included, so the grouping is recomputed far more often than the store's posts change; at 40 days a recompute costs seconds (3.6's estimate) |

**First numbers, build step 2 (2026-10-13, round 10):** `serve --copy` on Ron's laptop, today's store (139 compared
posts, 123 cards for a new guest's empty bar, 400 KB of JSON). **Cold**, the first request after start: `gen` 1.1 ms,
**`group` 1324.4 ms** (reading the store and hashing every photo), `eval` 1.2, `order` 0.2, `json` 7.4; 1.69 s at the
client. **Warm** (5 requests): `gen` 0.7–1.3 ms, `eval` 1.1–2.1, `order` 0.2–0.5, `json` 6.9–13.9; **14–39 ms at the
client**. `/api/reference` 3 ms, `/api/posts/{id}` 5 ms, a 47 KB photo 67 ms. The warm target (300 ms on the server) is
met by far; the cold first request (one per store change or start) is above the 1.5 s first-cards target and is measured
again in the browser at step 7 (point 31).

**Measuring a real page load** (#301). At build step 7 (l), on a dated copy of the production store (the site writes
`userdata`, and even opening `SqliteUserDataStore` starts a write transaction, so the real file is not served before
3.9, #331), **and on a synthetic store of 40 days' size** (#330, point 20), built as in 3.6's measurement:
1. **On the server:** `POST /api/cards` returns a `Server-Timing` header (MDN, modified 2026-07-28: `name;dur=…`,
   shown in the browser's network timings) with `gen` (the generation read), `group` (a recompute, when one ran), `eval`,
   `order` and `json`; logged too.
2. **In the browser:** chrome-devtools' performance trace and Lighthouse, on a desktop window and a phone viewport: the
   time to the first cards and the total, cold (the first request after the site starts: the whole grouping and the
   photo hashes), warm, and after a store change (a `classify_pending --limit 1` is not needed: a test write on the copy).
3. Reported in `SESSION_LOG.md` with each store's size. **The targets (#330, point 20):** a warm `POST /api/cards` under
   300 ms on the server; the first cards drawn under 1.5 s on Ron's laptop; on today's store and on the 40-day one. A
   bulk read (3.6 point 13) is proposed only if the measurement misses them.

### (i) The writes a user makes (#260, #300), and what the user sees on a conflict

| Write | How | On a conflict or a failure |
|---|---|---|
| Viewed (#253, #276) | `mark_viewed(user_id, Card.shown_id, now)` when the opened post loads; insert only if absent (`userdata`, no lifecycle) | None possible beyond a database error: the card simply stays unviewed |
| Not viewed | `unmark_viewed(user_id, Card.post_ids)` | The same |
| **"Lied" flag on every member** (#300) | For each of `Card.canonical_ids`: read the lifecycle; when `"active"`, write `state` `"rejected"`, `rejection_reason` `"flagged"`, `flagged_by` the user, `flagged_at` now, the note, by **`save_lifecycle(record, expected=the record read)`**; a member that is no longer active is skipped. The record is built by a new pure function in `postmodel/rejects.py`, `flagged_lifecycle(existing, user_id, now, note)` (one place for Gate E's flag rule) | `StaleRecordError`: re-read once and try again if the post is still active; else that member is reported. The user sees "flagged" when every member was written, "flagged 1 of 2: the post changed meanwhile, try again" otherwise, and the list reloads (the card is gone) |
| **Report on the shown post** (#300, #278) | `add_report` first (a second open report by the same user is refused: "you already reported this post"), then the lifecycle by compare and set through `reported_lifecycle(existing, user_id, now)` in `postmodel/rejects.py`: `"rejected"`, `"misclassified"` unless already `"flagged"`; `flagged_by`/`flagged_at` set only by the first reporter (#280) | Two seams, two transactions (#289 point 3): when the lifecycle write fails after one retry, the report stays stored and the user sees "report saved; the post will be removed by the admin", and the admin's list shows it (3.8) |
| Save the preferences | `save_profile` (whole record, #289 point 4) | A database error: "not saved, try again"; the bar keeps its values |

**A stale page:** a write names a post that is no longer in a current card (someone flagged it, a run rejected it): 409,
"this post was removed meanwhile", and the list reloads. Every write leaves `RawPost` and `Listing` untouched
(invariant 14) and writes no per-user value on a post (invariant 12): only the lifecycle's flag fields, as Gate E
allows.

### (j) Invariant 15 on the page

- **No request to any other host.** Fonts bundled by `@fontsource` into the build and served by the site; no CDN; no
  analytics; no external image: photos come from `/api/photos` (the local store); the Facebook link, the video links
  and WhatsApp are links the user clicks, never fetched by the page.
- **Headers on every response:** `Content-Security-Policy: default-src 'self'; img-src 'self' data:; font-src 'self';
  connect-src 'self'; frame-ancestors 'none'` (so a request to another host fails in the browser even if one slipped in),
  and `Referrer-Policy: no-referrer` (the tailnet address is not sent to Facebook or WhatsApp when a link is followed;
  links also carry `rel="noopener noreferrer"`).
- **FastAPI's telemetry stays off.** FastAPI 0.143.0 depends on `opentelemetry-api` and, since that release (2026-10-08,
  its release notes), sets up an exporter only on opt-in (`FASTAPI_OTEL_AUTO_CONFIGURE` or `telemetry=`); the plain
  package installs no SDK. The site never opts in; a test checks it and the socket guard covers the rest.
- **Checked:** a pytest that every response carries the two headers; a check that the built files name no other host
  except the link targets (`facebook.com`, `wa.me`); and in chrome-devtools at each build step, the network panel shows no
  request leaving the site.

### (k) Dependencies (read 2026-10-11 under the `external-contract-verification` skill; nothing installed)

| Package | Version, licence | What was read | Use |
|---|---|---|---|
| `fastapi` | 0.143.0 (2026-10-08), MIT, Python ≥ 3.10 | pypi.org JSON: requires `starlette>=0.46.0`, `pydantic>=2.9.0`, `typing-extensions`, `typing-inspection`, `annotated-doc`, `opentelemetry-api>=1.44.0`; extras not used. Docs: "Response Cookies" (set on a `Response` parameter or a returned response; parameters in Starlette's docs); "Static Files" (`app.mount(path, StaticFiles(directory=…), name=…)`); "Testing" (`TestClient`, "first install httpx") | The API and the static pages; no extras |
| `starlette` | 1.7.0, BSD-3-Clause (pulled by FastAPI) | pypi.org JSON; starlette.dev "Responses" (`set_cookie`, `delete_cookie`, `FileResponse`), "Test Client" (default `base_url` `"http://testserver"`) | Cookies, `FileResponse`, `StaticFiles`, `TestClient` |
| `uvicorn` | 0.54.0, BSD-3-Clause, Python ≥ 3.10 | pypi.org JSON: `click`, `h11`; the `standard` extra (uvloop, watchfiles, websockets, httptools) not used | The server, bound to `127.0.0.1` |
| `httpx` (dev) | 0.28.1 (2024-12-06), BSD-3-Clause | pypi.org JSON | For `TestClient`, as FastAPI's page says; **but** starlette.dev's "Test Client" now speaks of `httpx2` and starlette 1.7.0's `full` extra lists both `httpx2>=2.0.0` and `httpx<0.29`: which one 1.7.0's `TestClient` imports is **unknown** until installed (point 17) |
| `react`, `react-dom` | 19.3.0, MIT (`react-dom` needs `scheduler ^0.28.0`) | registry.npmjs.org | The pages; the same as event-seeker |
| `vite` | 8.3.4, MIT; Node `^20.19.0 \|\| >=22.12.0` (Ron's 24.11.1 fits) | registry.npmjs.org | Build and dev server |
| `@vitejs/plugin-react` | 6.1.2, MIT; peer `vite ^8.0.0` | registry.npmjs.org | JSX |
| `typescript` | 7.0.2, Apache-2.0 (native compiler, per-platform packages) | registry.npmjs.org | Type checking (`tsc --noEmit`, as event-seeker) |
| `@fontsource/ibm-plex-sans-hebrew` | 5.3.0, OFL-1.1 | registry.npmjs.org (woff/woff2 files; the subsets were not listed) | The font event-seeker uses (point 16) |
| `vitest` (dev) | 5.0.3, MIT; Node `^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0`; peer `vite` | registry.npmjs.org | Tests of the pure TypeScript (formatting), no DOM: `jsdom` and Testing Library not added |
| `@types/react`, `@types/react-dom` (dev) | not read | — | Read at the install, with event-seeker's ranges (`^19.3.0`) |

**Event-seeker's own `frontend/package.json`** (read on the laptop, 2026-10-11) holds this exact set (React 19.3, Vite
8.3.4, plugin-react 6.1.2, TypeScript 7.0.2, Vitest 5.0.3, an IBM Plex Sans Hebrew font, no router), so the method of
#257 carries over. No router library: a small history-based route for `/`, `/post/<id>`, `/preferences`, `/sign-in`,
`/sign-up`, `/password`.

**Installed 2026-10-13 (build step 2), read again under the skill (`ASSUMPTIONS.md` I15–I18):** `fastapi` 0.143.0,
`starlette` 1.7.0, `uvicorn` 0.54.0, and `httpx2` 2.13.1 (dev) — the client the installed `TestClient` imports
(`starlette/testclient.py`: `httpx2`, with `httpx` only as a deprecated fallback; FastAPI's testing page still says
`httpx`, Starlette's says `httpx2`). Starlette 1.8.0 was published the same morning and was not taken. **On Windows
`TestClient` opens a loopback socket pair** (the event loop's self-pipe, I17): the web tests make that one pair without the
guarded `connect`; the guard stays on for everything else.

**Pinned exactly (#330, point 17):** every package above at the exact version read at the install (`==` in
`pyproject.toml`, exact versions in `package.json` with the lock file), read again under the
`external-contract-verification` skill if the install is later than 2026-10-11. **At the install, before any test is
written on it:** which client Starlette's `TestClient` imports (`httpx` or `httpx2`), and that it opens no socket. **Before
building the WhatsApp link (step 6):** its format read in a browser.

**Could not verify:** which client 1.7.0's `TestClient` uses (above); that it makes no socket connection (the docs imply
it calls the app in process; the suite's socket guard will say); the font's Hebrew subset files; WhatsApp's link format
(`https://wa.me/<number>`, international, no `+`): its help page did not render to the fetcher, to read in a browser at
step 6; the transitive npm packages' licences; whether TypeScript 7's native packages install on Linux in 3.9's image.

### (l) The module layout, the tests, and the build in steps

**Python (wiring, like `pipeline.py`; the logic stays in `policy/`, `postmodel/`, `dedup/`, `accounts/`):**
- `tlv_hunter/web/` (not `site`, which is a Python standard module): `app.py` (`create_app(store_path, store_root)`: the
  routes, the static pages, the headers), `auth.py` (the cookie and `accounts.session_user`), `grouping.py` (the held
  grouping and the generation check, (h)), `cards.py` (the card and opened-post payloads, pure), `filters.py` (the bar's
  JSON to a transient `Profile`), `routes.py`.
- `policy/colours.py` (`field_colours`, (d)); `postmodel/rejects.py` gains `flagged_lifecycle` and `reported_lifecycle`
  (i); **the area groups** in `reference/area_groups.yaml`, read only through `areas/reference.py` (the one reader of
  `reference/`), so the grouping of §6 is data beside the 71 (point 23).
- `jobs/serve.py`: runs uvicorn on `127.0.0.1` with the store's path (until 3.9 a dated copy, #331); free; the site
  becomes a store writer beside the jobs (#260). `jobs/add_store_generation.py` (#316): the one-time migration (dated
  backup, `RawPost` check, as `create_admin`), the seventh store writer.
- `CLAUDE.md`: a row or paragraph for `web/` and the new commands.

**Front end:** `frontend/` at the repository's root (event-seeker's layout): `src/main.tsx`, `src/api.ts`,
`src/types.ts`, `src/route.ts`, `src/screens/` (List, Post, SignIn, SignUp, Password, Preferences),
`src/components/` (Card, FilterBar, AreaPicker, RangeField, Chip, Glow, Carousel), `src/format.ts` (relative time,
"X/Y", "1 of N", sizes), `src/styles/`. `frontend/dist/` and `node_modules/` gitignored; FastAPI serves `dist/`.

**Tests (the suite stays offline: the socket guard; `TestClient` in process; temporary stores only):**
1. The cookie: the exact `Set-Cookie` attributes; a bad, ended or expired token is a guest and the cookie is cleared.
2. Guests: list, open, photos, reference work; every write is 401; no viewed field in a guest's cards.
3. **No rejected, pending, archived or duplicate post reaches a non-admin:** a temporary store with one post in each
   state: absent from `/api/cards`, 404 from `/api/posts` and `/api/photos`; a duplicate's id opens its canonical's card.
4. The photo route: only a stored `local_path` of a current card; `..` and other posts' files refused.
5. The grouping: computed once for many requests (a counter on `derive_cards`); recomputed after a write through each
   store method (#316: the counter moves for `raw_posts`, `post_lifecycle`, `listings`, `corrections`, and not for
   viewed, sessions, profiles, users); the migration command (backup, `RawPost` rows identical, refuses a second run).
6. The bar: a transient profile never saved (a `UserDataStore` double: `save_profile` is called only by `PUT
   /api/profile`, the preferences page; #335, #336); an invalid bar (`min` > `max`, sqm in the room option) is 422.
7. The writes: a flag on a two-post card writes both members with `expected`; a conflict on one gives the partial
   answer; a report writes the shown post only, refuses a second open one; `RawPost` and `Listing` rows byte-identical
   after every write (invariant 14); nothing per user in the post tables (invariant 12).
8. The headers (CSP, `Referrer-Policy`) on every response; FastAPI's telemetry not configured.
9. `policy/colours.py`: each row of (d)'s table; the glow, none while the option holds no preference (#322);
   `flagged_lifecycle`, `reported_lifecycle`: Gate E's rules (#279, #280).
10. Front end (Vitest, no DOM): the formatters (#120 and the closed card's "1/N", #325; #121, #122, #115, #95), "לא צוין"
    for every attribute not written (#321), and which chips the closed card keeps (#326).

**The build, in steps, each ending in something Ron can look at or run:**
1. **Built in round 9 (2026-10-12):** the generation table and triggers (#316, `store_generation.py`), layout
   versions `store`, `store.listings`, `userdata` 2, `SqliteRepository.store_generation()`, the migration command
   `jobs/add_store_generation.py`, their tests. **Ron runs the migration** on the production store (a dated backup is
   made); until then every command refuses the store and names the command. **Ron ran it on 2026-10-13:** layout
   `store`, `store.listings`, `userdata` 1 → 2, backup `tlv_hunter.2026-10-13.backup.sqlite3`, `RawPost`s identical, counter
   0.
2. The read-only API: `web/`, the held grouping, `/api/cards`, `/api/posts`, `/api/photos`, `/api/reference`,
   `jobs/serve.py`, on a dated copy of the store (#331). The dependencies installed, pinned exactly; `TestClient`'s
   client checked before its first test (#330, point 17). **Ron runs** `serve` and opens the JSON; the first `Server-Timing`
   numbers. **Built 2026-10-13 (round 10):** `web/` (`app.py`, `grouping.py`, `filters.py`, `cards.py`, `routes.py`),
   `jobs/serve.py` (`--copy` makes a dated copy in `<store_root>/site/` by SQLite's online backup from a read-only
   connection; without it the newest copy; never the store itself), `reference/area_groups.yaml` with
   `areas.reference.load_area_groups`; `GET /api/reference`, `POST /api/cards` (and `GET /api/cards`, a new guest's empty
   bar, so the list opens in a browser), `GET /api/posts/{id}`, `GET /api/photos/{id}/{file}`; `Server-Timing`; the two
   headers; FastAPI's pages and telemetry off. Tests: `tests/test_web.py` (groups 2–6, 8, `serve`). **Not yet in the
   payload:** the field colours and the glow (`policy/colours.py`, step 3, with the page that uses them) and WhatsApp
   (step 6, its link format read first).
3. The list and the opened post for a guest, **desktop grid and phone list together** (#303), the dialog (#304) and the
   full-screen post (#313), the glow, the "i" and the colours (#322, #323), the closed card's carousel with lazy-loaded
   photos (#327, #330), only green chips closed (#326), built with `frontend-design` and checked in chrome-devtools at
   1440 px and as a real 390 × 844 page in the same step (screenshots, console, network). **Ron looks at it** with real
   posts.
4. The header (the logo, the user area, #333, #334) and the redesigned filter bar of (e), desktop and phone sheet: the
   switches, one values row per kind, the status line and the "ההעדפות שלי" reset (#335). **Ron filters** for real.
5. Sign-in, sign-up with a key (no filter box, #336), the forced password change, the cookie; the preferences page, the
   only place preferences are saved (#335). **Ron signs in**, saves his preferences.
6. Viewed, not viewed, the report button on the closed card (#328), the flag, the report, the conflict messages;
   WhatsApp's link format read first. **Ron flags and reports** on the copy (they stay in it, #331).
7. The measured page load (h), on the copy and on a 40-day synthetic store (#330), Lighthouse, the `design` plugin's
   critique and accessibility review, a colour-vision check. **Ron reviews** the numbers and the look.

### (m) What I could not verify

- The times of (h) on a 40-day store; today's store holds 266 posts.
- `TestClient`'s client package in Starlette 1.7.0, and that it opens no socket (above).
- WhatsApp's link format (above); the font's subsets.
- How the site and a job command meet on the busy timeout (#259) when a recompute reads during a run: measured on the
  working day (3.10).
- That a dialog with a long Hebrew text and a carousel stays usable at 390 px: the round-8 mock was checked as a real
  390 px page in headless Chrome (screenshots only; chrome-devtools did not connect in round 8), not with real touch.

### (n) Points for Ron (3.7)

**Points 1–26 were decided by Ron on 2026-10-12 (#316–#331).** Each keeps its question as written in round 7, with the
decision after it.

1. **An unclear price with no price range:** as built, #302 covers a price **not written** only; an unclear price
   (another currency, a per-roommate price on a whole apartment) counts only against a set range. Or: an unclear price
   also always at the bottom. **Decided: as built (#318).**
2. **No green glow while the option holds no preference** (d, caution 2). Or: green whenever the tier is
   `"preferences_met"`. **Decided: no green glow (#322).**
3. **"The area unclear" in red:** by 3.6 an unclear area sends a post to the bottom only when the user chose areas.
   Kept so (recommended), or, like the price, always at the bottom. **Decided: kept so (#319); with no areas chosen it is
   capped at the middle by Ron's own rule (#320).**
4. **The glow's form:** A, the ring with a labelled chip (recommended), B or C (d). **Decided: the ring and soft
   shadow, with the "i" of #323, no labelled chip (#330).**
5. **The palette and the glyphs for colour blindness** (d). **Decided: the palette as recommended; no glyphs anywhere
   (#323, #330).**
6. **The important-missing style** (`BASELINE.md` §6 left it to this task): a dark slate badge with a "!" and the words
   ("no price", "no entry date"), stronger than grey and not a tier colour. **Decided: as recommended, without the "!"
   (#323, #330).**
7. **Parking not written:** "no parking" in grey (§6's text with #309's colour), or "parking: not stated".
   **Decided, generalised by Ron: every attribute not written is "לא צוין" in grey (#321).**
8. **Furnished "yes":** plain (not in #309's list, recommended), or green. **Decided: plain (#330).**
9. **The table of (c)**: which items sit on the closed card (Ron's request f). **Decided: (c) with Ron's notes
   (#323–#328, #330).**
10. **The link to the original post:** a main button inside, a small icon on the closed card (recommended). Following
    the icon from the closed card: does not mark the card viewed (#253 marks on opening; recommended), or does.
    **Decided: as recommended (#330).**
11. **How the site knows the store changed:** option 1, the generation counter by triggers, a layout change and a
    one-time migration command with a backup (recommended); or option 2, `PRAGMA data_version`, no layout change, many
    more recomputes. **Decided: option 1 (#316); the migration command at build step 1.**
12. **The list in one response** for a filter (no paging) until the measurement says otherwise; the filter sent in a
    `POST` body. **Decided: as recommended, the photos lazy-loaded (#330).**
13. **A guest's filter at sign-up:** "use my current filter as my preferences", checked when the bar holds a value.
    **Decided: as recommended (#330).**
14. **The bar's lifetime:** the tab's `sessionStorage` (a reload keeps it; a new visit starts from the saved
    preferences, or empty for a guest). **Decided: as recommended (#330).**
15. **Levels in the bar:** inside "more" (recommended), or on the preferences page only. **Decided: inside "more"
    (#330).**
16. **The font:** IBM Plex Sans Hebrew, as event-seeker (recommended), or another. **Decided: IBM Plex Sans Hebrew
    (#330).**
17. **The dependencies of (k)**, FastAPI 0.143.0 (three days old) and uvicorn without extras; `httpx` or `httpx2` for the
    tests, whichever Starlette 1.7.0's `TestClient` imports; Vitest for pure logic only. **Decided: as recommended,
    pinned exactly; `TestClient`'s client checked at the install before any test on it; WhatsApp's link format read
    before building on it (#330).**
18. **The module names of (l):** `tlv_hunter/web/`, `frontend/`, `policy/colours.py`, `flagged_lifecycle` and
    `reported_lifecycle` in `postmodel/rejects.py`, `jobs/serve.py`. **Decided: as recommended (#330).**
19. **Against cross-site requests:** `SameSite=Strict`, JSON-only writes and an `Origin` check, with no extra token.
    **Decided: as recommended (#330).**
20. **The targets of (h):** 300 ms on the server warm; the first cards under 1.5 s. **Decided: as recommended, also
    measured on a synthetic 40-day store (#330).**
21. **A flag on a card of several posts that is written on some members only** (one changed meanwhile): reported to the
    user as partial, with a retry (recommended); or all-or-nothing, which compare and set on two records in one
    transaction does not give (`save_lifecycle` writes one record). **Decided: partial, with a retry (#330).**
22. **What counts as a mobile number for WhatsApp** (#311): a normalized number starting with `05` and 10 digits long,
    decided in one place (`textnorm`, beside the one phone normalization). **Decided: as recommended (#330).**
23. **The area groups as data**, `reference/area_groups.yaml` read through `areas/reference.py` (recommended), or a
    table in the site's code (§6's open "where it lives"). **Decided: the YAML file (#330).**
24. **The count in the bar** ("79 posts") and on the preferences page. **Decided: as recommended (#330).**
25. **What the references show and the rules do not have**, not added: a street filter, a map, favourites, pets, a safe
    room or shelter, "renovated", a third kind "apartment for roommates", an email, a source badge, a "last week only"
    line. Any Ron wants is its own decision. **Decided: none added (#330).**
26. **The group's name** (`RawPost.group_title`) in the opened post: not in §6, so not shown (recommended), or shown.
    **Decided: not shown (#330).**

**New points from round 8 (for Ron; nothing of them is built):**

**Points 27–30 were approved by Ron on 2026-10-12 as recommended (#332).**

27. **A room post's rooms on the closed card when the apartment's total is not written** (#325 leaves it to the
    reviewer). **Recommended:** the stat reads "1" and, under it in grey, "סה״כ לא צוין" (total not stated), so the "1"
    is never read as a one-room apartment and #321's words are kept. Or: "1/" followed by a grey "לא צוין". Inside the
    post #120's wording stays ("a room", with no "of"). The mock shows the recommended form. **Decided: as recommended (#332).**
28. **What "only green chips" (#326) covers.** I read it as the **field chips** (broker, balcony, parking, elevator, air
    conditioning, "women preferred"). Not chips, and so kept on the closed card: the price, the location line (plain,
    green or orange; "מיקום: לא צוין" in grey when there is none), the four stats (rooms, size, floor, entry date, each
    "לא צוין" in grey when not written), the kind with the sublet mark, and the orange "kind unclear · shown as: room"
    (§8 requires every card to show which option it answers; #273 its kind marked). Consequence: "women preferred"
    (plain) moves inside. **Recommended: this reading.** Or: the grey stats and the unclear-kind mark also move inside. **Decided: this reading
    (#332).**
29. **The tier's label inside the opened post.** #323 takes the label's text off the card. **Recommended:** inside the
    opened post the label and, for the bottom, its reason are written in words at the top of the price block (the post
    is where the detail is). Or: the "i" there too. **Decided: in words (#332).**
30. **The closed card's carousel on a desktop** (#327): arrows that appear on hover, plus dots; on a phone a swipe and
    dots. Only the first photo loads with the page; the others as they scroll into view (#330, point 12). The arrows
    are chevrons drawn in CSS, which I read as controls, not state glyphs (#323 names the tier and the chips).
    **Recommended:** keep them. Or: dots only. **Decided: kept (#332).**

**New points from round 10 (for Ron):**

31. **The cold first request** takes 1.3 s on the server (1.7 s at the client) on today's store, above the 1.5 s
    first-cards target, once per store change or start; warm requests take 14–39 ms. **Recommended:** keep it lazy for now
    and measure it in the browser at step 7 (with the 40-day store); if it still misses, compute the grouping at start and
    after a store change in the background, so no visitor waits for it. Or: compute it at start now.
32. **The list's size:** 400 KB of JSON for 123 cards, since every card carries the poster's whole text (the closed card
    shows 3 lines, the opened post the rest). **Recommended:** keep it whole until step 7's measurement (warm requests
    are fast); if the page is slow, send the first lines in the list and the whole text with the opened post.

## 3.8 The admin lists — content approved (`BASELINE.md` §11; #75 B, #173, #243, #251, #254–#256), plan to be written

- **Rejected,** every reason, canonicals only (#75 B), the city shown through `other_city_name` (#214).
- **Pending,** canonicals only (#75 B), with each post's `last_classification_error`; the "retry" that sets
  `classification_failures` back to 0 (Gate E, #139, #152).
- **Archive,** canonicals only (#75 B). Nothing is archived until Phase 5's job; the list exists and is empty.
- **Flags by user, and restore** (`BASELINE.md` §11; #251).
- **Reports grouped by field** (#173, #254), with restore, correct by hand (#256), or leave out; the corrections in
  force, and their removal.
- **Keys and users** (#243, #265, #266): issue, list, cancel; the password reset (#262); disable and enable a user.
- **Reports whose post was not rejected** (3.4 point 3), with a retry.
- **Needs from Ron:** the plan's approval.

## 3.9 Serving on the tailnet — plan to be written

Docker Compose on Ron's laptop (`BASELINE.md` §3, §12: phases 1–4 run there), the site published with Tailscale Serve
(HTTPS, tailnet only; `ASSUMPTIONS.md` I4 verified). The collection and classification commands stay manual (#140,
#61). The framework and serving are decided (#258). **Needs from Ron:** the plan's approval.

## 3.10 The measured working day (DoD 4, I3) — approved (#225, #228)

Once a dashboard exists: one real working day of collection and classification, each paid run under a cap Ron sets;
calls, tokens and cost from the usage metadata, then the OpenAI bill. **Needs from Ron:** the go for each paid run, and
the bill.

---

## 3. Items this phase must close

| Item | Source | Task |
|---|---|---|
| DoD 4, the measured working day, and `ASSUMPTIONS.md` I3 (the same measurement) | #225, #228 | 3.10 |
| The same-listing grouping derived by the Gate D key; its first check on the 4 known pairs | #230–#232, #229 | 3.6 |
| The card's city for an other-city post, derived (`other_city_name`) | #214 | 3.6, 3.7, 3.8 |
| Viewed posts per user | #62, #253 | 3.4, 3.6, 3.7 |
| The admin lists show canonicals only | #75 B | 3.8 |
| The card's display rules: the main time, the repost log's earliest `posted_at`, rooms and size on a room post, the entry date's year, the video link from a repost | #122, #75 A, #120, #121, #115, #70 | 3.7 |
| The "wrong classification" report, its schema and the corrections record | #173, #254–#256 | 3.1, 3.4, 3.7, 3.8 |
| The per-user YAML removed | #47 | 3.4 |
| The dashboard framework; the journal mode; concurrent writes to `PostLifecycle` | `BACKLOG.md`, "Open technical choices"; #65 | Decided (#258–#260); built in 3.4, 3.7, 3.9 |
| **Notes from the dedup B plan worth keeping:** **alerts (Phase 4) must not fire for a post the key ties to an earlier one**; the key reads only active canonical posts that have a `Listing`, so a post waiting for its classification is not tied; the agent-number threshold of 4 is re-measured on a week of data | #230–#232; `PHASE_2.md` 2.10 | Recorded; 3.6 builds the derivation that Phase 4 reads |
| `gate_d_pairs` runs again on a larger store, to record the rate with its window | #226, point 5 | Free; after a week of runs. Not a DoD item |
| The phone as a candidate signal for dedup B: dedup A's layer 3 still produces nothing, and nothing writes a phone match onto a post (#75 C; the key settles the rest, #230–#232) | #75 C | **For Ron:** nothing is proposed; left as it is unless Ron wants it |

Settled on 2026-10-10 and so not open: #70 under dedup B (#252); which size a room search filters on (#247); the area
grouping (#248, #249, #261); the orange on the area (#250, #275); restore after a reclassify (#251, as amended by #281
and #282).

---

## 4. The four known pairs (first check of the derived grouping)

`54ecb1d0…` / `00f17259…`, `7253eefa…` / `40f7f193…`, `e81273e6…` / `8ae80944…`, `9136a715…` / `9a6252c1…`
(read-only, 2026-10-08, 139 active canonicals; Ron judged all four `same_listing`, #229). No post is in two pairs, and
none of the eight has an exact-hash duplicate. Each must show as one card; the store will have changed by then, so the
check reads the store as it is and reports any difference.

**Checked at 3.6's build (2026-10-11, round 6), read-only, with the built `dedup/stage_b.py`:** the four pairs tie and
nothing else does; 135 cards, 4 of them of two posts, each showing its earlier post (`54ecb1d0…`, `7253eefa…`,
`9136a715…`, `e81273e6…`). The store's SHA-256 was `04cefd60…` before and after (`SESSION_LOG.md`, 2026-10-11, round 6).

---

## 5. Technical choices — APPROVED by Ron, 2026-10-10 (#258, #259, #260)

Each choice below was approved as recommended: §5.1 option A, §5.2 the rollback journal with an explicit busy timeout,
§5.3 option 1. The comparison is kept as the record of what was weighed. No library is installed yet; versions and
contract details are read under the `external-contract-verification` skill in each task's plan (3.5 for `argon2-cffi`).

### 5.1 The dashboard framework, and how the site is served

**What weighs:** Docker Compose on the laptop and later the home server (`BASELINE.md` §3); Tailscale Serve in front
(HTTPS, tailnet only); the Telegram Mini App later adapts the same site (`BASELINE.md` §10, `ASSUMPTIONS.md` T5); a
polished UI built with Ron's design skills (#257); Hebrew, right to left; the store and all the logic are Python
(`policy/`, `postmodel/`, `store/`), so the site's server is Python or calls Python.

**Ron's design plugins** (the set he used for event-seeker): `frontend-design@anthropic-plugin-directory` (visual
direction, typography, the UI's code), `design@synced` (critique, design system, UX copy, accessibility review,
handoff), and `chrome-devtools` (inside `ecc@ecc`: drives a real Chrome on a page — screenshots, console, network,
Lighthouse, a mobile viewport). `superpowers` is disabled and not relied on. *How well each works with each option is my
reading of what the plugins do; none was used in this round.*

| | A. React 19 + TypeScript, Vite; hand-written CSS; `@fontsource` Hebrew fonts; FastAPI + uvicorn serves the API and the static build; one image, two-stage build *(Ron's event-seeker stack)* | B. FastAPI + Jinja2 templates rendered on the server, htmx for partial updates; hand-written CSS; one stage, no Node | C. A Python UI framework (NiceGUI, Streamlit or similar) | D. A Node full-stack framework (SvelteKit, Next.js) beside a Python API |
|---|---|---|---|---|
| Fits the store and the logic in Python | Yes: the API is Python and calls `policy/` directly | Yes: all Python | Yes | No: two servers, the Node one calling the Python one for every read |
| One image, one process | One image (Node only at build), one process | One image, one process | One image, one process | Two runtimes; two services or one image with two processes |
| A polished, hand-designed UI | Full control; the stack Ron's UI was built with | Full control of markup and CSS; rich interactions (the profile editor, "copy from the other option", the grouped area filter) are more work as partial page swaps | Poor: the framework owns markup and styling | Full control |
| Hebrew, right to left; fonts | CSS `dir="rtl"`; fonts bundled by `@fontsource`, so no font request leaves the device | CSS; fonts self-hosted by hand | Limited by the framework | CSS; fonts bundled |
| The Telegram Mini App later | A single-page app adapts to a webview; the sign-in from Telegram is checked by the API (Phase 4, to verify) | Works in a webview; less client code to adapt | Poor fit | Works |
| Sign-in | A same-origin session cookie: the API and the pages are one origin, so no CORS | The same | The framework's own, or custom | Cross-service |
| `frontend-design` | **Good:** components and hand CSS are its natural output | **Fair to good:** markup and CSS carry over; components must be rewritten as templates | **Poor:** little room for its direction | **Good** |
| `design@synced` | **Good:** works from screens and specs, whatever the stack | **Good** | **Fair:** critique works, applying it is hard | **Good** |
| `chrome-devtools` | **Good:** a running page in Chrome; Vite's dev server reloads on save, for a quick look-and-fix loop; a mobile viewport for the Mini App | **Good:** any served page; no reload on save unless added | **Fair** | **Good** |
| New tooling in this repo | Node and npm for the build and the dev server (on Ron's laptop, checked 2026-10-10: `node` v24.11.1, `npm` 11.6.2; reused, `node_modules` never copied between projects, #258) | None beyond Python packages | Python packages | Node, and a second server |

**Recommendation: A — approved (#258)**, Ron's event-seeker stack. Ron's design work and these three plugins have already produced a UI
he is happy with on this stack; it keeps one image and one Python process that calls `policy/` directly; and a
single-page app is the closest to what the Mini App needs. Its cost is a Node build stage and Node on the laptop for UI
work. **B** is the choice if Ron prefers no Node at all, at the price of more work on the interactive parts. C and D are
not recommended.

**How it would be served (with A or B):** one Docker image; the site's container runs uvicorn on a port bound to
`127.0.0.1` on the host; **Tailscale Serve** on the host publishes that port over HTTPS to the tailnet only
(`ASSUMPTIONS.md` I4). The API and the pages share one origin. The collection and classification commands run from the
same image as one-off commands (the scheduler is Phase 5's). The site's code is wiring, like `pipeline.py`: the logic
stays in `policy/` and `postmodel/`; its module and its libraries are designed in 3.7's plan (`CLAUDE.md`).

### 5.2 SQLite journal mode (#65)

The site reads all day while a run, `classify_pending` or the site itself writes. Today: the default rollback journal,
one connection per operation, every write a short `BEGIN IMMEDIATE` transaction (`store/sqlite.py`), and a reader opened
`read_only` with `mode=ro`.

| | Keep the rollback journal, with an explicit busy timeout | WAL |
|---|---|---|
| A page read during a write | Waits while the writer commits; each write is one short transaction | Never waits for a writer |
| A write during a long read (a full list) | Waits until the read ends: reads must stay short | Not blocked |
| The dated backup (`jobs/common.backup_store`) | Unchanged: it copies the one file | **Must change:** it copies the main file only (`shutil.copy2`), which can miss committed transactions still in the `-wal` file; SQLite's online backup is the replacement |
| `read_only` opening (`mode=ro`) | Unchanged | To verify on sqlite.org before relying on it: a read-only connection to a WAL database has conditions on the `-shm` file |
| Files | One | Three (`-wal`, `-shm`); the mode is stored in the file |
| The laptop (Windows, Docker) and the server (Linux) | Works on both | SQLite documents WAL for a local filesystem; a Windows folder mounted into a Linux container is to be checked |

**Recommendation: keep the rollback journal in Phase 3 — approved (#259)**, set an explicit busy timeout on every
connection, and keep each page's read in one short transaction; measure on the real store during 3.10. WAL is
reconsidered in Phase 5 if waits are seen on the measured day, together with the backup change. *Why (the proposal's):*
it changes nothing that works today (the backup, `read_only`), and the writes are already short. Python 3.12's default
busy timeout is 5.0 seconds (read 2026-10-10); 10 seconds is proposed in 3.4 (e).

### 5.3 Concurrent writes to `PostLifecycle`

`save_lifecycle` is a whole-record replace, last write wins (#65; a contract test pins it). Until now no two writers ran
at once (#140, #220). **The site changes that:** it runs all day and writes `PostLifecycle` when a user flags or reports
a post and when the admin restores or retries one, while `run_once` or `classify_pending` may be writing the same
record (a repost moves `last_published_at`; a classification sets the state). A run that read the record before the
user's flag and writes after it erases the flag; the other order erases the run's change. **#140's "never at the same
time" cannot hold for the site.**

| | Option | Cost |
|---|---|---|
| 1 | **Compare and set** for every writer: `save_lifecycle(record, expected)` writes only if the stored document is still the one read, checked inside the same `BEGIN IMMEDIATE` transaction; otherwise it raises. The site tells the user the post changed and reloads; a run re-reads the record and applies its change once more | A Repository contract change (one parameter, both stores, the contract test replaced). The same "re-read before writing, write nothing if it changed" that `rederive_rejections` and `apply_reclassify` already do (#214, #220) |
| 2 | **Field-level writes** inside one transaction (for example "set the flag", "set the state"), reading and writing in the same transaction | Several new Repository methods; the run's code must move its read-modify-write into the store too, or it still overwrites |
| 3 | **The site waits for runs:** user actions refused while a run is going | A run marker that does not exist yet (Phase 5); flags refused for up to 30 minutes |
| 4 | **User actions never write `PostLifecycle`:** flags and reports live only in their own records, and the visible state is derived (a post with an open flag or report shows as rejected) | Rewrites Gate E's flag fields and the E-1 to E-3 amendments; reclassify's flagged-post rule (#217 (5)) reads `flagged_by` |

**Recommendation: option 1 — approved (#260)**, for every writer of `PostLifecycle`. It keeps Gate E's shape and the
amendments as drafted, uses a pattern the code already has, and fails loudly instead of losing a change. #140's "never at
the same time" no longer covers the site; it still holds among the job commands (`CLAUDE.md` updated). How each caller
uses it: 3.4 (d).

---

## 6. Area grouping — APPROVED by Ron, 2026-10-10 (#261)

**No official grouping that maps to `ms_shchuna` was found** (`RESEARCH.md` §16): the municipality's quarter layers
(510, 847, 512) carry codes and no names, and layer 511 does not point at them. **The grouping below is the assistant's**,
by region, from where the areas lie; it is not a municipal division. It keeps together the entries of the colloquial
names already given to the model (`SCHEMA.md`, "Colloquial names": the Old North 30–31, the New North 33–35, Jaffa
42–49, Kfar Shalem 68–69). Display only: what is stored is the municipal numbers (#83, #248). Ron approved it as proposed,
with the four entries round 1 left open placed in regular groups (1 and 3, 29, 40).

| Group (Hebrew heading) | `ms_shchuna` |
|---|---|
| North of the Yarkon, west (עבר הירקון – מערב) | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18 |
| North of the Yarkon, east (עבר הירקון – מזרח) | 19, 20, 21, 22, 23, 24, 25, 26, 27 |
| The North (הצפון הישן והחדש) | 29, 30, 31, 32, 33, 34, 35, 36 |
| The city centre (מרכז העיר) | 37, 38, 39, 40, 41 |
| Jaffa (יפו) | 42, 43, 44, 45, 46, 47, 48, 49 |
| The south (דרום העיר) | 50, 52, 53, 54, 56 |
| The east (מזרח העיר) | 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71 |
| **Non-residential, collapsed, at the bottom (#249)** | 11, 12, 13, 28, 51, 55, 66 |

All 71 appear once: 64 in the seven groups, 7 in the non-residential group. *The reviewer's reason for the four, approved
by Ron:* when in doubt, a regular group, so "select all in group" does not miss a post. The non-residential seven were
proposed from their names alone (a university, a fairground, a park, a business park, an employment zone); no land-use
data was read. **From the store** (read-only, 2026-10-10, 194 `Listing`s): area 11 is on 1 active post; a collapsed group
still lets a user choose it (#249). 50 נוה עופר sits with the south, 36 צמרות איילון with the North.

Where the grouping lives in code: `reference/area_groups.yaml`, read only through `areas/reference.py` (#330, point 23),
built with 3.7.

---

## 7. For Ron's decision

1. **Round 10's points 31 and 32** (3.7 (n)); `serve` and its JSON (`BACKLOG.md` item 6); the round-10 mock in
   `data/mock/`. The plan, its 30 points and the notes on the mocks are approved (#316–#343).
2. Unchanged from Phase 2 and not in this phase: the bill (Ron), the five reclassify proposals waiting in
   `dcb4c0cb4b24`, the deferred carrier of #241 and the reclassify of the other 189 (`BACKLOG.md`).

Decided and so closed here: the task order and the DoD; the technical choices (#258–#260); the area grouping (#261);
round 1's 31 open points (#262–#287); Gate C's names and types, R1–R9 and the Gate E amendments (#288); the plans for
3.4 and 3.5 (#289, #290) and 3.4's three points left by the build (#291–#293); the admin's password reset on the machine
(#294); the plan for 3.6 and its 16 points (#295–#300); how the grouping is held (#301); the missing price at the bottom
(#302); Ron's direction for the site (#303–#315); the plan for 3.7, its 30 points and the notes on the mocks
(#316–#343).
