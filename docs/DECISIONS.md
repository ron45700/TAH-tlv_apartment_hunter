# Decisions

Every decision that shapes this project, with the reasoning behind it.

**Read this before proposing to reverse something.** A decision recorded here was made against a
specific constraint; if that constraint still holds, the decision still holds. If it no longer
holds, say so explicitly and change the entry — do not quietly work around it.

Superseded decisions are kept, marked, and left in place. Deleting them would lose the fact that
the question was considered at all.

**Last updated:** 2026-10-04

> Written in English like every document in `docs/`.
>
> `HANDOFF.md` and `MACRO_PLAN.md` are in `docs/archive/`. Where an entry below names them, it is
> recording where the decision came from at the time. The current plan is `BASELINE.md`; research
> findings are in `RESEARCH.md`.

---

## Legend

| Status | Means |
|---|---|
| **Active** | In force |
| **Superseded** | Replaced by a later decision, named in the entry |
| **Corrected** | Still in force, but its stated reasoning was found wrong and has been fixed |

---

## Original decisions (research phase)

| # | Decision | Why | Status |
|---|---|---|---|
| 1 | **No Facebook account. No login. Public groups only.** | Meta made public-group content visible to logged-out visitors. Removes account-ban risk entirely — the single largest risk in the original plan. | Active |
| 2 | **Never paste own `sessionCookies` into any actor** | Hands credentials to a third party and reintroduces exactly the account risk decision 1 removed. Hard line. | Active |
| 3 | **Buy collection from Apify, don't build a scraper** | Selector rot is the real maintenance killer (weeks, not months). Outsourcing it moves the fragile part to someone else's problem. | Active |
| 4 | **Provider adapter layer from day one** | Already proven necessary: the first provider was blocked mid-project. Three providers evaluated, all with incompatible schemas. | Active |
| 5 | **Everything runs in the cloud (GCP)** | Once collection moved to Apify, the home/residential IP stopped being an asset. No Raspberry Pi, no home laptop, no local collector. | **Superseded by #43** |
| 6 | **LLM classifies; we filter on structured fields** | Keyword pre-filtering is fragile in Hebrew (negation, prefixes, `/` forms). Filtering on model output is re-runnable and changeable without re-scraping. | Active — see #51 for where the filtering now happens |
| 7 | **The model classifies only — never summarizes** | Ron always reads the original text. A summary adds tokens and hallucination surface for zero value. | Active |
| 8 | **`null` is information, not failure** | Distinguishes "the poster didn't write it" from "we don't know". Drives triage ranking, not rejection. | Active — extended by #54 |
| 9 | **Telegram push only in v1. No buttons, no dashboard.** | Dashboard comes after the bot works. Interactive buttons would require webhook + state for no v1 benefit. | **Superseded by #48** |
| 10 | **Daily digest message is v1, not a nice-to-have** | Ron's criteria are narrow. Silence and failure look identical without it. It is a measuring instrument. | Active — sent to the admin only |
| 11 | **Bootstrap mode on first run** | First run pulls a backlog and would fire ~30 messages in a row. First run writes to DB and sends one summary. | Active |
| 12 | **Keyword sniper runs in shadow, as QC — not as a filter** | Kept because it is already written and tested. Disagreements with the model flag posts worth eyeballing. | **Superseded by #16, then #45** |
| 13 | **Nothing is ever deleted** | Rejected posts are stored with the reason. Feeds the future "rejected" dashboard pane. | **Superseded by #46** |
| 14 | **Never advance the watermark on a failed run** | A skipped window is a permanently missed apartment. | Active |
| 15 | **Include `new_north` in the allowed areas at launch** | Derech Namir / Arlozorov sit on the old-north/new-north boundary. Better a little noise than a missed border listing. | **Superseded by #51** |

---

## Planning decisions (2026-09-13/14)

### 16 — The deterministic sniper is out of v1
**Status: superseded by #45.** **Supersedes #12.** `sniper.py` and `test_sniper.py` stay in the repo, outside the execution path.
The sniper becomes a second implementation of the `Classifier` protocol, switchable on later in
shadow mode without touching the pipeline.

*Consequence:* post #18 (`אנחנו שני שותפים שמחפשים דירת 3 חדרים` → `seeking`) is no longer covered.
It was listed as "not blocking" in `HANDOFF.md` §6 *because* the sniper caught it; that reasoning no
longer holds. It moves into the Gemini regression set.

### 17 — v1 pushes everything, with reasons. Rich filtering moves to the dashboard
**Status: superseded by #48 and #52.**

v1 is a **calibration mode**: every non-duplicate post is pushed to Telegram carrying the reason it
was classified as it was, so extraction quality can be judged against real output and the prompt
tuned. The LLM-populated fields become dashboard facets rather than v1 notification filters.

*Consequence:* the message must distinguish `filter_fail` (the model extracted correctly, the value
does not match) from `missing_field` (the model did not extract it). Two completely different bugs.

### 18 — The pipeline always stores; `policy` decides only what to notify
**Status: corrected by #46 and #49.** Still the principle: collection never filters by anyone's
criteria. Two limits now apply. Posts rejected before the model (no text, no images) are stored but
not classified, and stored posts are removed after the retention period.

**The central architectural principle.** Classification and storage happen for every post
regardless of anyone's criteria. The policy layer decides notification only.

*Consequence:* the dashboard is a read-side feature requiring zero pipeline changes; adding an
extracted field is three changes (model, prompt, test); and because `raw` is preserved, a
reclassification job can backfill a new field onto all history.

### 19 — Approval gates before any schema
**Status: active, extended by #59** (Gate E added; Gate C widened).

No schema, field, or filter rule is created or changed without Ron's explicit approval.
`docs/SCHEMA.md` is the only source of truth. Gates A (RawPost), B (Listing), C (filter rules),
D (dedup B key). Recorded as invariant 1 in `CLAUDE.md`.

*Why:* a schema written without deliberation costs a full reclassification to fix.

### 20 — One Apify run for all groups, not one run per group
**Amended by #71 (2026-10-04):** the run is started with the regular (non-sync) call, not a
synchronous one. "One run for all groups" stands.
**Amended by #78 (2026-10-04):** the run's window starts at the last successful run's start minus
the buffer, not at `min(all watermarks) - buffer`, and there is no per-group local filter. "One run
for all groups" stands.

`postsNewerThan` is a single value per run, but the watermark is per group. Resolution: one
run with all 6 URLs, `postsNewerThan = min(all watermarks) - buffer`, filtered per
group locally.

*Why:* cheaper than 6 runs (memo23 also bills per start), the watermark stays per group as
designed, and dedup absorbs the wider overlap. *Corrected 2026-10-04 (#78): this entry also said
"silent-group detection falls out for free". It does not: a quiet group and a failed one both
return zero rows (`ASSUMPTIONS.md` P5, `SPIKE_1_1a.md` Q2).*
*Status:* the per-group behaviour of `postsNewerThan` is `ASSUMED` — verified in task 1.1a.

### 21 — `httpx` directly against Telegram, not `python-telegram-bot`
**Status: superseded by #56.**

That library is for bots that **listen**. Push-only v1 is two HTTP calls: no event loop, no
dependency that drags the design toward a webhook prematurely.

### 22 — The Gemini response schema is derived from pydantic at runtime
Never hand-written, never maintained in parallel. Two sources of truth for a schema drift, and the
drift is silent.

### 23 — Semi-macro planning one phase ahead only
Detailed planning of later phases rests on assumptions that Phase 1 has not yet resolved — the same
failure `HANDOFF.md` §2 warns about. A detailed plan also creates commitment: it is harder to
discard than a row in a table. Each phase ends with a stop to update `BASELINE.md`, `RESEARCH.md`
and `ASSUMPTIONS.md` before the next phase is planned.

*Exception:* decisions expensive to reverse from an early phase (chiefly data shape) are settled
up front as the anchors in `PHASE_1.md` §1.0.

### 24 — karpathy-skills enabled; superpowers and ECC disabled for this project
**karpathy** is four principles in a ~65-line file at near-zero context cost, and maps closely onto
the VERIFIED/ASSUMED method. Because it is on, `CLAUDE.md` does not restate "don't assume, ask
first, prefer simplicity" — that budget goes to invariants and domain traps instead.

**superpowers** auto-triggers `using-git-worktrees` and `finishing-a-development-branch`, which
conflict directly with Ron handling all git himself, and its `brainstorming` / `writing-plans`
skills duplicate planning already done. Revisit at Phase 1 implementation if execution discipline
proves lacking.

**ECC** is 441 components whose own README warns about context footprint, and its rules/memory
system competes with `docs/`.

*Consequence:* `CLAUDE.md` carries an explicit line that the module seams are decided architecture,
not premature abstraction — karpathy lists over-abstraction as an anti-pattern with `Protocol` and
`ABC` as its examples, which is exactly what `providers/` and `classify/` look like.

### 25 — Collection is shared; evaluation is personal
**Status: active, amended by #47.** It is no longer a future direction: friends are users from the
start. The group list is shared by all users, so "which groups a user subscribes to" below no
longer applies. The legal note at the end refers to a research section that no longer exists; the question is
tracked in `ASSUMPTIONS.md` L1.

A post is fetched, classified, and stored **once**, regardless of how many users exist. What is
personal: which groups a user subscribes to, which posts pass their filter, how those posts rank,
and what reaches their bot.

**Extraction is objective; ranking is subjective.** What a post *says* (price, area, type, balcony)
is the same for everyone and is classified once. How *good* a post is for a given person is a
calculation over those stored fields — never a second model call, never a per-user prompt. A second
user must cost zero model calls.

*Consequence:* `user_id` on every personal record from day one with a fixed v1 value; post and
verdict stored separately; the `Listing` schema covers every listing type, not only what Ron
searches for; collection settings (`maxPosts`, `sortingOrder`, schedule) are shared while group
subscriptions and filter rules are personal; the watermark stays per group and global.

*Open:* `HANDOFF.md` §7 records that the personal-use exclusion from the Israeli Privacy Protection
Law holds only while the project stays personal and non-commercial. A second user sits on that
line. Not a blocker and not legal advice, but a decision to be made deliberately rather than
drifted into.

---

## Decisions forced by findings (2026-09-14, task 1.2 and Gate A)

### 26 — Text hash is the primary dedup key; phone is a one-directional signal
**Corrects `HANDOFF.md` §5**, which called the phone number "the real primary key of a listing."

Phone numbers appear in only **10 of 20** posts, and **both** posts in one of the three duplicate
pairs have no phone at all. Relying on phone as the key would have missed a third of the duplicates.

A shared phone is strong evidence of the same listing; a missing or differing phone carries **no
information**. Layer 2 (text hash) is the key. Layer 4 (`price + rooms + street`) carries more
weight than originally assumed, because it covers the rewritten-text case phone cannot — which is
why Gate D was upgraded in importance.

### 27 — The poster's name is never part of the hash
Neither is `user.id`. The name looks like a stabilising ingredient but does the opposite: the same
apartment posted by two different flatmates must still collide, and adding the name would prevent
exactly that. Text alone is better.

### 28 — `listing_id = sha256(source_post_id)`, without `source`
thedoor's `post_id` and memo23's `legacyId` are both Facebook's post ID — the same post carries the
same number from either provider. Including `source` in the hash would make one post produce two
records the moment a failover happens, which is precisely the provider-failover scenario. Excluding it lets
dedup layer 1 work across providers, not only within one.

`source` remains its own field for provenance.

### 29 — Empty text: stored, flagged, never classified
**Status: corrected by #49.** Still stored, flagged and never classified. It is now a rejection
reason ("no text") seen by the admin only, not a dashboard bucket.

A post with no text after extraction (a `shared` post, or one whose content is entirely in an image)
is stored, never rejected, flagged `no_text`, **not sent to Gemini** (we do not analyse images),
excluded from ranking, and retrievable as its own bucket in the dashboard.

It gets **no hash**: two empty strings would collide with each other and manufacture a false
duplicate.

### 30 — Promote conservatively in `RawPost`
Every `RawPost` field is a pure function of `raw`. A field not promoted today can be backfilled by a
script over stored `raw` — no model call, no cost, no lost history. This is **not** true of
`Listing`, where each new field costs a Gemini call per post across all history.

Hence Gate A is cheap to revisit and Gate B is expensive. Applied immediately:
`sale_post.isOnMarketplace` and `sale_post.isSold` were proposed as first-class fields and demoted
back into `raw`.

*Only exception:* data determined at fetch time and absent from `raw` — `source` and `fetched_at`.

---

## Decisions from the Phase 0 plan review (2026-09-14)

### 31 — Config splits along the shared/personal line, not by topic
**Status: corrected by #47.** The shared half stands: `collection.yaml` holds collection settings,
now including the schedule and quiet hours. The personal half moves out of YAML: a user's profile
is stored in the database and edited from the dashboard, and there are no per-user group
subscriptions.

`collection.yaml` (shared): provider, group IDs, `maxPosts`, `sortingOrder`, `fetchAllComments`,
store root. `users/<user_id>.yaml` (personal): `user_id`, subscribed groups; filter rules join at
Gate C. Secrets come only from environment variables, never from a file.

*Why:* the originally proposed `groups.yaml` / `runtime.yaml` / `filters.yaml` split cuts **across**
decision #25 — `groups.yaml` would have mixed which groups are fetched (shared, one run for
everyone) with which groups a user subscribes to (personal). `filters.yaml` is Gate C content and
must not exist before that gate opens.

### 32 — The five derived fields are nullable, and `None` means "not computed"
`text_hash`, `phones`, `no_text`, `is_canonical`, `duplicate_of`. The code that fills them arrives
across two phases, and a non-nullable field forces an early phase to store a claim it cannot
support — `is_canonical=True` would be false for the three known duplicate pairs.

Phase 0 computes `text_hash`, `phones` and `no_text` (that code is already written and verified in
task 1.2). `is_canonical` and `duplicate_of` stay `None` until dedup A exists in task 1.3.

The pair `(no_text, text_hash)` resolves the ambiguity: `no_text=True` with `text_hash=None` means
deliberately unhashed; `no_text=None` means textnorm has not run.

*Rejected:* pulling dedup A into Phase 0 to avoid the nullability. That is task 1.3 and a real scope
breach.

### 33 — Stub contracts are named `Stub`, in files named `_stub`
`ListingStub` in `contracts/listing_stub.py`, `DecisionStub` in `contracts/decision_stub.py`.
Invariant 1 applies to stubs, so their Phase 0 field sets are approved explicitly (see `SCHEMA.md`).

*Why the naming:* a class named `Listing` sitting in the codebase looks like an approved starting
point. That is exactly the confusion that made `data/raw/schema.py` worth renaming to
`research_listing_model_2026-09-13.py.txt`. Gate B **replaces** these stubs; it does not extend them.

### 34 — `fetched_at` records the **first** time we saw a post
On upsert of an existing `listing_id`, the rest of the record is overwritten but `fetched_at` is
preserved.

*Why:* the field exists to measure the gap from `posted_at` — how slow we are to see a listing. The
deliberate 10–15 minute watermark overlap re-fetches the same post on almost every run, so
overwriting would reset the measurement continuously and make the field meaningless. If "last seen"
is ever wanted, it is a separate field, not an overwrite of this one.

### 35 — Fixtures are never copied into the package
`data/` is gitignored because it holds real people's phone numbers. Tests read fixtures **in place**
from `data/raw/`, and a missing fixture makes a test **fail, not skip**, so a clean clone cannot pass
silently.

*Why:* `CLAUDE.md` originally placed provider fixtures in `tlv_hunter/providers/fixtures/`, which
would have put real phone numbers into a git-tracked path. Caught in the Phase 0 plan review.

---

## Decisions from the Phase 0 build review (2026-09-14)

### 36 — `postsNewerThan` is always sent as **relative minutes**, never as a date
The actor's OpenAPI pattern allows two forms: absolute `YYYY-MM-DD` (date only — a full ISO datetime
is rejected) or relative `<number> <minute|hour|day|week|month|year>`, decimals permitted.

The absolute form alone would cap the watermark at one-day granularity, which would make the whole
incremental design pointless. The relative form accepts minutes, so the window stays fine-grained:
send `now - min(watermark) - buffer`, expressed in minutes.

*Consequence:* the watermark itself keeps second resolution; only the actor input changes shape.
No design change. Note that relative is measured from **run start**, so a delayed start shifts the
window by the delay — one more reason the 10–15 minute overlap buffer must not shrink.

*Amended by #78 (2026-10-04): the window is `now - (last successful run's start - buffer)`,
expressed in minutes; the buffer is 15 minutes. Relative minutes and the reasoning above stand.*

### 37 — A post that normalizes to nothing is `no_text`, never an error
An emoji-only post produces an empty normalized string. Hashing it would collide with every other
such post, so it must not be hashed — but **raising is the wrong remedy**: a failed run does not
advance the watermark (invariant 2), so one throwaway post would block that window permanently, and
every subsequent run would re-fetch it and fail again.

`no_text=True`, `text_hash=None`, not classified. `text_source` still records where the text came
from: `"text"` with `no_text=True` means it arrived and was unusable.

### 38 — Phone numbers are stored normalized
**Status: active, extended by #57.**

Digits only, `+972` converted to a leading `0`. `050-9184537` and `+972509184537` both become
`0509184537`. `find_by_phone` normalizes its input before comparing.

*Why:* a store lookup by phone is an equality query and cannot match across formats. Nothing is
lost — the card always shows the full original text, and `raw` keeps everything.

### 39 — No-text posts **are** notified, in a minimal distinct format
**Status: superseded by #49.**

Link, images, and a line stating there is no text and the content is probably in the image. No
fields, no `confidence`, no reasons block — there is nothing to fill.

*Why:* the dashboard bucket for these is Phase 6 and the digest that would count them is Phase 4. If
they do not notify in v1 they simply vanish, and Ron cannot tell whether the pipeline is filtering
them or dropping them. That is exactly the failure calibration mode exists to prevent. Zero such
posts in the 20-post sample, so the noise risk is low — and if it turns out otherwise, it is one line
in `policy`, the module built to change.

### 40 — For an Apify actor, `/api/openapi` is the source of truth, not the Input tab
The thedoor actor's human-readable Input page serves an April-2026 snapshot — 603 users, $3.00/1K,
and only three input fields — while the API pages of the same actor show the current build with
`sortingOrder`, `fetchAllComments`, `includeTopComment` and `postsNewerThan`. The OpenAPI definition
is tied to a build ID and was current.

Recorded in the `external-contract-verification` skill.

---

## Decisions from the alignment session (2026-10-02)

### 41 — Filtering is a view-time layer over all collected posts, with three filters
**Status: superseded by #51.** Both open points at the end are closed there.

Stated by Ron, 2026-10-02. The model is a listings site such as Yad2: everything is collected and
stored, and Ron narrows **what is displayed**. Collection never filters.

The filters:

| Filter | Behaviour |
|---|---|
| Listing kind | Room in an existing shared flat **or** a whole empty apartment |
| Price | Optional lower bound and optional upper bound. Neither is required; either can be used alone |
| Number of rooms | Relevant to a whole empty apartment |

Everything else a post carries — location, phone number and the rest — is **card content**: shown
on the post's card when the information exists, and not a filter.

*Why:* Ron runs two searches in parallel — a room for himself in an existing shared flat, and an
empty apartment to enter with two friends — and wants to move between them freely. A fixed set of
criteria baked into collection or notification cannot do that.

*Consequences:*
- `HANDOFF.md` §1 "What Ron is looking for" is no longer the definition of what the system
  searches for. It describes one of two searches.
- Consistent with #18 and #25: this is the read side, over fields classified once.
- **Gate B** must define the fields behind these three filters. Their names, types and allowed
  values are settled there, not here.
- **Gate C** is reduced to these three filters plus two open points below.

*Open, to be settled with Ron:*
1. **Where the filters live in v1.** The dashboard is Phase 6+ and v1 is Telegram push of every
   post (#17). Until a read-side UI exists there is nowhere to apply a filter interactively.
2. **A post whose filtered field is `null`** (no price written, room count missing): shown or
   hidden when that filter is active? By #8, `null` is information, not failure.

---

## Baseline decisions (2026-10-02 and 2026-10-03)

Made by Ron in the alignment sessions that produced `BASELINE.md`. Each entry states the decision
and what it replaces. The detail lives in `BASELINE.md` and is not repeated here.

### 42 — `BASELINE.md` is the plan
It replaces `HANDOFF.md` and `MACRO_PLAN.md`, which move to `docs/archive/`. Research findings that
still hold are in `RESEARCH.md`.

*Why:* Ron revised the direction in several large ways at once. Patching two documents written
for the old direction would have left contradictions for Claude Code to trip over.

### 43 — Home server with Tailscale; GCP is the fallback
**Supersedes #5.** `BASELINE.md` §3.

*Why:* Ron prefers to run it on his own machine. Telegram needs no public address (long polling and
outbound calls only), and Tailscale Serve plus device sharing gives friends HTTPS access without
exposing anything publicly, which is also a second access gate.

### 44 — Docker Compose, SQLite, images on disk
Replaces the Cloud Run, Cloud Scheduler and Firestore choices of the old plan. `BASELINE.md` §3.

*Why:* the same compose file runs on Ron's laptop and on the server. At ~50 posts a day and a
handful of users SQLite is enough and its backup is one file. The `store` interface keeps Postgres
a cheap swap.

### 45 — The keyword sniper is removed
**Supersedes #12 and #16.** Not dormant, not a second classifier: gone.

*Why:* the model scored 10/10 on real posts including adversarial cases. *Consequence:* detecting
"other city" and "seeking" rests on the model alone, as schema fields. The seeking case that was
never tested (`ASSUMPTIONS.md` C2) must be in the regression set.

### 46 — Retention is bounded
**Supersedes #13.** 25 days after last publication a post is archived and its images deleted; at 40
days it is deleted entirely. `BASELINE.md` §5.

*Why:* an apartment post that old is no longer relevant, and 40 days is enough for debugging.
*Consequence:* reclassifying after a schema change covers 40 days, not all history, so the field
list can start lean.

### 47 — Friends are users from the start
One-time key from Ron, password on the site, Telegram linked by a code, one profile for both.
The group list is shared by all users. `BASELINE.md` §1, §10. **Amends #25 and #31.**

*Open, recorded:* whether the personal-use position holds with several users was never checked
legally. Ron's position: close friends only, still personal. `ASSUMPTIONS.md` L1.

### 48 — Dashboard first; alerts only on a profile match
**Supersedes #9 and #17.** The site is built before the bot. There is no calibration mode that
pushes every post. `BASELINE.md` §12.

*Why:* the filters need somewhere to live, and judging extraction quality is done better in a list
Ron can scan than in a stream of messages.

### 49 — Post lifecycle and rejection reasons
Active, rejected, archived, deleted. Rejection reasons: no text, no images, other city, seeking,
for sale, not a listing, flagged. The rejected list is admin-only. `BASELINE.md` §5.
**Supersedes #39; corrects #18 and #29.**

A post with no images that shares another post is rejected only if the shared post has no images
either.

*Clarified by #67 (2026-10-04): "no images" means no media at all.*

### 50 — Flagging replaces the calibration file
Any user can flag a post as not what it claims. It moves to rejected for everyone, with the
flagger's name, and the admin can restore it. Flagged posts are kept as text, past the retention
period, as the regression set. Replaces `calibration.jsonl`.

### 51 — The filter model
**Supersedes #41 and #15.** Listing kind is a hard filter; area and price are fixed critical;
"women only" is critical by default and can be turned off; the rest are preferences that a user
can make critical; no value means no effect. One profile holds separate values for a room and for
an empty apartment. `BASELINE.md` §8.

### 52 — Alert rules
A new, non-rejected post that passes the user's kind and critical conditions, has an explicit
price and an understood location. Preferences never block an alert. `BASELINE.md` §9.

### 53 — Area is decided by the model from the street and the hints in the text
A street that crosses several areas with nothing to settle it carries all of them and is marked
unclear; it still matches and alerts if one of them was chosen. A location the model cannot place
gets no area and never alerts. Areas come from a closed list taken from a public source.
`BASELINE.md` §7.

### 54 — Field states
**Extends #8.** Present, not written, unclear, and a separate stronger mark when price or entry
date is missing. Balcony and parking are both stored as "not written"; they differ in display only.
`BASELINE.md` §6.

### 55 — Runs every 30 minutes, none between 01:00 and 07:00
**Status: active, amended by #61** (30 minutes is the default interval, editable by the admin; a
manual run is added).

The hours are config, later editable by the admin. Closes the old open point on scheduler
frequency.

### 56 — The bot listens
**Supersedes #21.** Account linking needs the bot to receive a code, by long polling. Which library
to use is decided when phase 4 is planned.

### 57 — Phones: every distinct number, an identical one once, with the name when given
**Extends #38.** Closes the question #38 left open. The name next to a number is a new requirement
for Gate B, since the phone itself is extracted without the model.

### 58 — Sublet is a basic flag; "women only" is negative only
A post is a sublet or it is not, with no duration. "Women only" hides a post; "women preferred" is
a mark on the card and hides nothing.

### 59 — Gate E, and a wider Gate C
**Status: Gate E settled by #63** (approved 2026-10-04).

**Extends #19.** Gate E: what the lifecycle adds to a stored post (state, rejection reason, flagger,
last publication, repost log, image paths). Gate C now also covers the user, key and profile
records.

### 60 — Yad2 stays future, and will likely need its own scraper
Not through an Apify provider. The design stays open to it.

---

## Decisions from 2026-10-04

### 61 — The run interval is an admin setting, and the admin can run now
**Amends #55.**
- The interval is an admin setting. 30 minutes is the default, not a fixed value. A change takes
  effect immediately: the next run is the last run's start plus the new interval.
- The admin dashboard has a "run now" button. A manual run is an ordinary run. When it succeeds,
  the next scheduled run is its start plus the interval, so no scheduled run follows sooner than
  one interval. A manual run that fails does not reset the timer.
- A manual run is allowed during the quiet hours (01:00–07:00). Scheduled runs still do not run
  then.
- One run at a time. A manual request while a run is in progress is refused or waits; two runs
  never overlap (invariant 2).
- Built in phase 5, with the scheduler. No schema change now: the stored interval and the last-run
  record are approved when phase 5 is built.

### 62 — Each user sees which posts they have already viewed
- "Viewed" is per user and never written on the post (invariant 12). It is a separate per-user
  record (user, post, time), settled at Gate C in phase 3.
- It survives a repost, since a repost updates the existing card. It is deleted with the post.
- The exact trigger is decided in the phase 3 UI design, together with a manual "mark as not
  viewed".
- Display order: all unviewed posts first, then the viewed ones; within each group, the order in
  `BASELINE.md` §8.

### 63 — Gate E: the post lifecycle record and `GroupWatermark`
**Extends #59; amends Gate A** (approved 2026-10-04). Fields and types are in `SCHEMA.md`, Gate E, and the Gate A
media fallback. The rules and why:

- **The lifecycle is a separate record, not `RawPost` fields.** Gate A stays a pure function of
  `raw` and stays backfillable; state, flags and images change after fetch.
- **A `"pending"` state.** In phase 1 nothing has been classified. Storing such a post as
  `"active"` would claim a verdict nobody has made, and phase 2 needs to find the posts the model
  has not seen.
- **One rejection reason, the first that applies, in a fixed order.** The pre-model reasons come
  first because they are decided first and are cheapest; a post rejected before the model never
  gets a model reason. One reason is what the admin's rejected list shows. An archived post keeps
  its reason, so the record still says why it was hidden.
- **A phone-only match is not a repost.** A phone is a one-directional signal
  (`ASSUMPTIONS.md` D7): one landlord or agent posts different apartments with one number.
  Treating such a match as a repost would hide a different apartment and move its last
  publication time.
- **`last_published_at` never moves backwards.** It drives the retention clock; a late-arriving
  older duplicate must not shorten a post's life. *Since #75 A (2026-10-04), such a duplicate
  does not become the canonical either.*
- **Images: photos only, one retry, a failure fails nothing.** Videos are not analysed and are
  shown as their link. A failed run blocks the window (invariant 2), so a lost image must never
  fail the run or the post. *Since #77 (2026-10-04): one retry within a run, and again on a
  later run when the post is fetched again (D2); a disk write error fails the run (D5a).*
- **Images are downloaded for posts the model will reject.** Image download runs before the
  model in the data path, so at download time no verdict exists. For a rejected post what matters
  is its original text and link, so downloading its images costs nothing important. *Extended by
  #76 (2026-10-04): photos for every canonical that has photos, whatever its state, a `no_text`
  post included.*
- **An identical-hash repost downloads no images**, since they duplicate the canonical's, unless
  the canonical is archived (its images are gone) or all its downloads failed. *Extended by #70
  (2026-10-04): also when the canonical has no media at all. Reworded by #72.3 (2026-10-04): while
  the canonical has no successfully downloaded image, or when it is archived. Read on the stored
  state, before #74, and retried on a later run: #77 D2, D4 (2026-10-04).*
- **Flagged posts are kept whole and never deleted.** A flag marks a model mistake, and the full
  record, including `raw`, is what is needed to re-run the prompt on it. Images are deleted at
  archive like any post's, since the model never sees images.
- **Shared posts take their images from `sharedPost.media`, and are detected by `sharedPost` being
  present.** Spike 1.1a found three `post_type` values carrying a `sharedPost`, with the post's own
  `media` empty on all of them. Without the fallback, every shared post would be rejected as having
  no images, against the rule in `BASELINE.md` §5.
- **`GroupWatermark` per group, with `consecutive_failures`.** The watermark is per group
  (`RESEARCH.md` §4) and the failure count feeds silent-group detection. *The rules for
  `last_success_at` and `consecutive_failures`, and what sets the run's window: #78
  (2026-10-04).*

### 64 — Task 1.10 stores both Gate E records; the watermark has its own interface
Approved by Ron, 2026-10-04.

- **Scope.** Task 1.10 builds the storage of both Gate E records: the post lifecycle record and
  `GroupWatermark`. Task 1.13 keeps only the watermark logic (when it advances).
- **Names.** `PostLifecycle` and `PostImage` in `contracts/post_lifecycle.py`; `GroupWatermark` in
  `contracts/group_watermark.py`.
- **`Repository` gains:** `save_lifecycle(record) -> PostLifecycle`, a whole-record replace;
  `get_lifecycle(listing_id) -> PostLifecycle | None`;
  `upsert_with_lifecycle(post, initial) -> RawPost`, which upserts the post (keeping the first
  `fetched_at`) and stores `initial` only if the post has no lifecycle record — create-only, never a
  merge or an overwrite, in one transaction in SQLite; and `find_without_lifecycle() -> list[RawPost]`.
  `upsert` keeps its signature. `save_lifecycle` requires a stored post and raises `KeyError`
  otherwise. local_json implements all of them, and the same contract tests run on both.
- **No merge and no "never backwards" logic in the storage layer.** That belongs to task 1.3. Who
  builds the `initial` record is task 1.11.
- **`GroupWatermark` is not in `Repository`.** It has its own interface, `WatermarkStore` in
  `state/` (`get`, `get_all`, and `save_all` in one transaction), backed by the same SQLite file.
  SQLite implementation only.
- **Guards** (approved in the 1.10 review, 2026-10-04): `upsert_with_lifecycle` raises `ValueError`
  when the record's `listing_id` differs from the post's; `save_all` raises `ValueError` on a
  duplicate `group_id`.

*Amended by #75 F3 (2026-10-04): `Repository` gains `get(listing_id) -> RawPost | None`.*

*Why:* `state/` is the seam already listed in `CLAUDE.md` for the watermark.
`upsert_with_lifecycle` and `find_without_lifecycle` exist because two separate writes could leave
a stored post with no lifecycle record after a crash; phase 2 looks for `"pending"` posts, so such a
post would never be classified. The atomic method prevents the gap in SQLite; the query finds it in
local_json, which cannot write two files atomically, and anywhere else. No reason was recorded for
the names, for `KeyError`, for SQLite being the only `WatermarkStore`, or for the guards.

### 65 — SQLite layout
Approved by Ron, 2026-10-04.

- **One JSON document per record**, written and read by the pydantic model, plus lookup columns
  only. `raw` is inside the document, whole. The one lookup column is `text_hash`, a plain column
  written by `upsert` in the same statement as the document. Phones are filtered in Python through
  the existing phone normalization.
- **`images` sit inside the lifecycle document**, not in a table of their own.
- **One connection per operation.**
- **The default rollback journal.** WAL is an open choice for phase 3 (`BACKLOG.md`).
- **Each module creates its own tables; no helper is shared between `store` and `state`.**
- **The file is `<store_root>/tlv_hunter.sqlite3`,** the same path passed to both modules. No
  config change.
- **Layout version per module:** a `layout_version` table with one row per module; SQLite's
  `user_version` is not used. On a mismatch, older or newer, the module refuses to open and names
  the module, the expected version and the version found. No automatic migration.
- **Minimum SQLite version:** each module's constructor checks `sqlite3.sqlite_version_info` against
  a minimum constant and raises below it. The minimum is 3.24.0, the release that added UPSERT
  (`INSERT … ON CONFLICT (target) DO UPDATE / DO NOTHING`), checked against sqlite.org on
  2026-10-04. The container's version is unknown (`ASSUMPTIONS.md` I8).
- **Known limit:** `save_lifecycle` is last-write-wins. Phase 1 has one writer. A contract test pins
  the behaviour, and the concurrent case is an open choice for phase 3 (`BACKLOG.md`).

*Why:* a generated `text_hash` column would need SQLite 3.31, and the home-server container's
version is unverified; a plain column removes that dependency. No reason was recorded for the other
points.

### 66 — Gate E additions: types and consistency rules
Approved by Ron, 2026-10-04. Written into `SCHEMA.md`, Gate E. `schema_version` stays 1.

1. `flagged_by` is `str | None`. Gate C may refine it.
2. `PostImage`: `listing_id: str`, `media_id: str`, `local_path: str | None`, `error: str | None`.
3. Exactly one of `local_path` and `error` is set.
4. `rejection_reason` is `None` when `state` is `"pending"` or `"active"`, required when
   `"rejected"`, optional when `"archived"`.
5. `flagged_by` and `flagged_at` are set together or both `None`; `rejection_reason` `"flagged"`
   requires both.
6. One UTC check, `require_utc` in `parsing/datetimes.py`, used by `RawPost` and by the new records.
   `RawPost`'s behaviour is unchanged.
7. `GroupWatermark` storage is built in task 1.10, its logic in task 1.13.
8. *Added in the 1.10 review, 2026-10-04:* the post lifecycle record has an explicit `listing_id`
   row (`str`; the post this record belongs to, and the record's key). The code already had the
   field.

*Why:* no reason recorded.

### 67 — `no_images` means the post has no media at all
Approved by Ron, 2026-10-04. **Clarifies #49.**

- The pre-model `no_images` rejection applies only when the post has no media of any kind. A post
  whose only media is video or reel is **not** rejected.
- The same applies to a shared post's media: the post is rejected only if the shared post has no
  media either.
- Gate E's "Images: photos only" stays as the **download** rule. The two are separate rules: one
  decides whether a post is rejected, the other which media are downloaded.

*Why:* no reason recorded.

### 68 — A rejected `no_images` post that comes back with media returns to `"pending"`
Approved by Ron, 2026-10-04.

A post rejected before the model as `no_images`, and fetched again with media, returns to
`"pending"` and goes to the model. It does not stay rejected.

The two questions left open here for task 1.11 planning were answered on 2026-10-04: a `no_text`
post that comes back with text is #69; media that arrives through a repost is #70. The rule behind
#68 and #69, re-checking both pre-model rules on the post's current content, is #72.1.

*Why:* no reason recorded.

### 69 — A rejected `no_text` post that comes back with text returns to `"pending"`
Approved by Ron, 2026-10-04. **Extends #68.**

A post rejected before the model as `no_text`, and fetched again (the same post) with text, returns
to `"pending"` and goes to the model. Same behaviour as #68.

*Why:* Ron does not expect this to happen, but if it does, the post should go to the model.

*The general rule, both pre-model rules re-checked on the current content: #72.1 (2026-10-04).*

### 70 — Media that arrives through a repost
Approved by Ron, 2026-10-04. **Extends #63 (the identical-hash repost rule) and #68.**

The case: the canonical post was rejected as `no_images`, and a different post with an identical
text hash (a repost) arrives with media.

- The canonical returns to `"pending"` and goes to the model.
- The repost's photos are downloaded and recorded in the canonical's `images`
  (`PostImage.listing_id` is the repost's `listing_id`, as the field already allows).
- The repost stays a repost: no card of its own, a line in the repost log, `last_published_at`
  updated. The canonical rule (earliest `posted_at`) is unchanged.
- The card's link stays the canonical's permalink; the repost's link appears in the repost log.
- `SCHEMA.md` Gate E, "Reposts": a repost with an identical text hash downloads its photos while
  the canonical has no successfully downloaded image (no `PostImage` with a `local_path`), or when
  the canonical is archived. *Reworded by #72.3 (2026-10-04); it read: "when the canonical is
  archived, or all of its images failed, or the canonical has no media at all".*
- The question does not exist for `no_text`: a `no_text` post is never hashed, so it has no
  duplicates. (One that comes back with text goes through dedup like any post: #72.2.)

No field or type changed; `schema_version` stays 1.

*Why:* without it, a real apartment with photos stays in the rejected list; and it keeps the
canonical rule intact.

The cases this left open were settled by #72: a repost whose only media is video or reel (#72.4),
an archived canonical (#72.5), canonical and repost new in the same run (#72.6), and dedup B
(#72.7, deferred to Gate D).

*Extended by #75 D1 (2026-10-04): the repost with media may be a stored duplicate, not only one in
the batch. "The canonical rule" reads as amended by #75 A.*

### 71 — Task 1.1: thedoor `fetch()`
Approved by Ron, 2026-10-04. **Amends #20.** Each point was presented to Ron as a recommendation
with the reason given here, and he approved it.

- **A. The regular (non-sync) call.** Start the run, poll until a terminal status, read the
  dataset. #20's "one run for all groups" stands; its word "synchronous" goes.
  *Why:* the sync call gives no run ID, and a cut-off run could look successful and advance the
  watermark (invariant 2).
- **Charge cap.** `maxTotalChargeUsd` is sent on every run, from the config key
  `max_total_charge_usd` (0.50). `fetch()` raises when the rows returned are at or above the run's
  `options.maxItems`.
  *Why:* a normal run costs at most $0.275; the cap stops a runaway run.
- **C.** Config key `include_top_comment`, typed `Literal[False]`, always sent. The same pattern as
  `fetch_all_comments`.
- **D. A row that fails to map is skipped, not fatal.** Logged at error level with its `post_id`
  and `group_id` (when readable) and the exception; the per-run log line carries the skipped
  count. Post text and phone numbers are never logged.
  *Why:* otherwise one broken post blocks every group's window permanently, the same concern as
  #37.
  **Amended 2026-10-04 (task 1.1 review), approved by Ron — a ceiling:** `fetch()` raises
  `ProviderRunError` when more than half of the run's rows failed to map **and** at least 3 rows
  failed. The count is over the rows of requested groups; rows dropped under E are excluded.
  Below the ceiling, rows are skipped and logged as above.
  *Why:* if the provider changes its response shape, every row fails, `fetch()` returns an empty
  list as a success, and the watermark advances past a window that was never stored
  (invariant 2). One broken post still must not block the window.
- **E.** A row whose `group_id` was not requested is dropped and logged as a warning.
- **F. Run deadline.** Config key `run_timeout_secs` (300). Past the deadline, `fetch()` aborts the
  run and raises.
  *Why:* the spike runs took about 30 s.
- **G. Shared media sizes.** `width` / `height` are taken when a shared media item carries them and
  are `None` when the keys are absent, the same as own media. `SCHEMA.md` Gate A amendment wording
  updated. No type change; `schema_version` stays 1.
- **H. A shared post with its own caption: unchanged.** Its `text` is the caption (Gate A as
  approved). Recorded as a known gap (`ASSUMPTIONS.md` P16), for Gate B.
- **I.** The stale references in the `external-contract-verification` skill are fixed.
- **J. A group at `max_posts`.** `fetch()` logs a warning for every group whose row count, before
  the `since` filter, is at or above `max_posts` (`>=`; amended from "equals" in the task 1.1
  review, 2026-10-04): its window may be cut off. Log only. What the watermark
  does then is an open point for task 1.13. *Settled by #78 W3 (2026-10-04): the group still
  advances, `advance` reports it, and `max_posts` is 50.*
- **Comments are not collected.** Both comment flags stay explicitly `false` (invariant 7);
  `RawPost.top_comment` is not touched.
- **Cost:** `usageTotalUsd` is logged as read at the end of the run, with no wait for the final
  figure.

For C, E, G, J and the cost line, no reason was recorded.

### 72 — Pre-model rejects: the seven open cases
Approved by Ron, 2026-10-04. **Generalizes #68 and #69; rewords #70 and the Gate E "Reposts"
rule.** Each point was presented to Ron as a recommendation with the reason given here, and he
approved it.

1. **Re-evaluation.** A post rejected before the model (`no_text` or `no_images`) that is fetched
   again (the same post) is checked again against **both** pre-model rules, on its current
   content. It returns to `"pending"` only if it now passes both; otherwise it stays `"rejected"`
   and its reason is updated to the first rule that applies. This is the rule behind #68 and #69.
   *Why:* a post with no media must not reach the model (#67); one rule covers both decisions.
2. **A `no_text` post re-fetched with text whose hash matches a stored post:** no special rule.
   Once it passes the check in (1) it goes through dedup like any post that arrived now; task
   1.3's normal rules decide which is canonical.
   *Why:* otherwise the same apartment gets two cards. Adds no code to task 1.11.
3. **#70 and the Gate E "Reposts" rule read by what we hold**, not by the canonical's own media:
   an identical-hash repost downloads its photos only while the canonical has no successfully
   downloaded image (no `PostImage` with a `local_path`), or when the canonical is archived. This
   replaces "all of its images failed" and "the canonical has no media at all" with the one
   condition. `SCHEMA.md` Gate E "Reposts" and #70's wording updated. No field or type change;
   `schema_version` stays 1.
   *Why:* read by own media, every later repost downloads the same photos again.
4. **A repost whose only media is video or reel:** the canonical returns to `"pending"` and
   nothing is downloaded. Intended.
   *Why:* consistent with #67 — the same as an ordinary video-only post. By (3), a later repost
   with photos still downloads them.
5. **An archived canonical rejected as `no_images`, when a repost with media arrives:**
   `"pending"` wins over task 1.3's "active again".
   *Why:* the post was never classified; `"active"` would claim a verdict nobody made (as in
   #63).
6. **Canonical and repost new in the same run:** task 1.11 evaluates each post alone; task 1.3
   applies #70 afterwards. The end state is the same (`"pending"`).
   *Why:* 1.11 stays simple and all cross-post logic sits in 1.3, in the same code that handles a
   repost against history.
7. **#70 under dedup B** (a repost with rewritten text): deferred to Gate D.
   *Why:* dedup B's key is not defined yet.

*Extended by #73 (2026-10-04): the re-check in (1) also applies to a `"pending"` post (#73.2), not
to an archived one (#73.3); (3) is read as #73.5. (5) is kept by #74, which replaces "active
again" for every archived post. (3)'s "when the canonical is archived" is read on the stored
state, before #74: #77 D4.*

### 73 — Task 1.11: pre-model rejects
Approved by Ron, 2026-10-04. **Amends `BASELINE.md` §4 (data path order); extends #72.1;
settles the reading of #72.3.** Each point was presented to Ron as a recommendation with the reason
given here, and he approved it.

1. **Text normalize runs before the pre-model rejects** in the data path. The `no_text` rule reads
   the stored `post.no_text`.
   *Why:* `no_text` is computed once and the rule only reads it.
2. **A `"pending"` post re-fetched with its text or media gone** is re-checked against both rules,
   like #72.1. A post with a verdict (active, rejected by the model, flagged) is left untouched.
   *Why:* otherwise an empty post reaches the model; a post with a verdict does not go back to it.
3. **An archived post that kept a pre-model reason, re-fetched:** left untouched.
4. **The code lives in `tlv_hunter/premodel/rejects.py`**, a plain module, not a seam. `CLAUDE.md`
   names it in one line; the seam table is unchanged.
5. **#72.3 as read:** "what we hold" is any `PostImage` with a `local_path` in the canonical's
   `images`, including one from an earlier repost, and the rule covers every canonical.
6. **No writes in task 1.11.** It delivers the pure functions only: `pre_model_reason(post)`,
   `initial_lifecycle(post)` and `recheck(existing, post)`. `recheck` changes a record only when
   its state is `"pending"`, or `"rejected"` with a pre-model reason (points 2 and 3). The store
   step (the sequence of `get_lifecycle`, `upsert` / `upsert_with_lifecycle` and `save_lifecycle`,
   and who calls the three functions) is an open point for task 1.14.
   *Why:* the data path stores after dedup. A write at the pre-model step means task 1.3 cannot
   adjust the record before it is stored (#72.6), and a re-fetched post's `upsert` would overwrite
   the `is_canonical` / `duplicate_of` that dedup already stored.

For 3, 4 and 5, no reason was recorded.

### 74 — A repost of an archived post returns it to the state it had
Approved by Ron, 2026-10-04. **Replaces task 1.3's "a repost of an archived post makes it active
again"; keeps #72.5.**

A repost of an archived post returns it to the state it had, not always `"active"`:

- It was active (classified, not rejected): `"active"`.
- It was rejected by the model (`other_city`, `seeking`, `for_sale`, `not_listing`) or flagged:
  `"rejected"`, with the same reason.
- It was rejected as `no_images` and the repost has media: `"pending"` (#72.5, unchanged).
- It was never classified: `"pending"`.

*Why:* a repost extends a post's life; it does not change what the system knows about it. An
apartment in Netanya posted again is still in Netanya.

**Consequence, recorded, not solved:** the lifecycle record has no field saying whether an archived
post was classified. In phase 1 nothing is classified, so an archived post with no rejection reason
returns to `"pending"`. In phase 2 the distinction comes from whether a classification record
exists; settled at Gate B. No field is added now.

*Which reposts bring a post back, and an archived `no_images` post whose repost has no media:
#75 E1–E3 (2026-10-04).*

### 75 — Task 1.3: dedup stage A
Approved by Ron, 2026-10-04. **Amends the canonical anchor (`PHASE_1.md` §1.0) and #64 (F3);
extends #70 (D1) and #74 (E1–E3).** Each point was presented to Ron as a recommendation with the
reason given here, and he approved it. The rest of the task 1.3 plan was approved as presented,
including: a re-fetched post keeps its stored `is_canonical` / `duplicate_of`, also after a text
edit (only its `text_hash` changes); a stored `no_text` post that comes back with text goes
through dedup as new (#72.2); a duplicate points at the canonical, never at another duplicate.

- **A. A stored canonical never changes.** A post that arrives later with an earlier `posted_at`
  becomes its duplicate. The canonical is the earliest `posted_at` among posts that arrive
  together. The card shows the group's earliest publication time: a display rule, phase 3 UI
  design.
  *Why:* the card, its alerts and "viewed" records stay stable; moving the canonical would mean
  moving everything accumulated on it, and a miss makes the apartment alert again as new.
- **B. A duplicate gets an ordinary lifecycle record, built from its own content.** No new state;
  Gate E unchanged. Phase 2 classifies only posts that are `"pending"` **and** canonical (Gate B),
  and the admin lists show canonicals only (phase 3). Whether a duplicate's retention follows its
  own clock or the canonical's: phase 5.
  *Why:* no schema change.
- **C. Layer 3 (phone) produces nothing in task 1.3.** The phone stays a candidate signal for
  Gate D.
  *Why:* a phone-only match is not a duplicate (#63) and nothing uses the result today.
- **D1. #70 also looks at stored members of the group**, not only at the batch, so it holds on
  every run.
  *Why:* otherwise the canonical flips between `"pending"` and rejected on each re-fetch.
- **D2. A tie on `posted_at`:** the smaller `listing_id` is canonical.
  *Why:* the result must be the same on every run.
- **D3. A `no_text` post** gets `is_canonical=True`, `duplicate_of=None`.
- **D4. After a text edit, when one hash reaches two stored canonicals,** a new post joins the
  earliest. Stored groups are never merged.
  *Why:* consistent with A — what is stored does not move.
- **D5. A stored post with `is_canonical=None` raises.**
- **E1. (#74)** Only a duplicate new to the store counts as a repost that brings a post back from
  archive; a stored duplicate fetched again does not.
- **E2. (#74)** A new duplicate whose `posted_at` is not later than the archived post's
  `last_published_at` does not bring it back.
  *Why:* the clock cannot move backwards, so the post would return and be archived again at once.
- **E3. (#74)** An archived `no_images` post whose repost has no media returns to `"rejected"`
  with the same reason.
- **F1. The code lives in `tlv_hunter/dedup/stage_a.py`**, a plain module, with no writes.
  `CLAUDE.md` names it in one line.
- **F2. Task 1.3 calls `initial_lifecycle` and `recheck` itself,** then, per canonical, #74, #70
  and `last_published_at`, in that order.
- **F3. `Repository` gains `get(listing_id) -> RawPost | None`,** in both stores, with contract
  tests. Amends #64.
  *Why:* without it dedup scans the whole store on every run.
- **F4. A stored canonical with no lifecycle record:** task 1.3 builds it with
  `initial_lifecycle`. Overlaps the task 1.14 open point on `find_without_lifecycle`.

For D3, D5, E1, E3, F1, F2 and F4, no reason was recorded.

### 76 — Which canonicals get their photos downloaded
Approved by Ron, 2026-10-04. **Replaces "for canonical non-rejected posts" in `PHASE_1.md` 1.12;
extends #63's "images are downloaded for posts the model will reject".**

- Photos are downloaded for every canonical post that has photos, whatever its state, a `no_text`
  post included.
- The rule for duplicates is unchanged (#72.3, as read in #73.5).
- Photos only, as in Gate E.

*Why:* one simple rule. In the admin's rejected list the photos of a `no_text` post are its whole
content, and the signed links expire within days. The cost is disk space only.

*Built in task 1.12, with the download rules of #77 (2026-10-04).*

### 77 — Task 1.12: image download
Approved by Ron, 2026-10-04; D2 (reposts) and D5b amended the same day in the task 1.12 review.
**Extends #63 (retry), #72.3 (reposts, as read in #73.5) and #76; settles the phase 5 archive
point on `PostImage` (D4b).** Each point was presented to Ron as a
recommendation with the reason given here, and he approved it. The rest of the task 1.12 plan was
approved as written: photos are `Media.type == "Photo"`; one at a time, a 30 s socket timeout, a
60 s and 20 MB cap per image; the retry as a second pass over the failures; the failure kinds and
the short `error` reasons; the function's input and output; tests through a fake transport.

- **Check.** Before the code, a throwaway download check: the 632 photo links of the spike 1.1a
  control dataset, one at a time, with the same header and timeouts, plus 5 links without the
  header. Metadata only, no image file, in `data/raw/spike_1_12_images_2026-10-04/`. No Apify
  call. *Result:* 632 of 632 HTTP 200, `image/jpeg`, JPEG bytes, including the `.png` and `.webp`
  links; 1,010 s in all; 5 of 5 without the header (`ASSUMPTIONS.md` I6, I9–I11).
  *Why:* only 5 jpg links were ever downloaded; png/webp and bootstrap volume were unverified, and
  the links expire on 2026-10-08.
- **D1. Files live at `<store_root>/images/<listing_id>/<sha256(media_id)[:16]>.<ext>`**, the
  extension read from the bytes. `local_path` is stored relative to `store_root`, with `/`. No new
  config key.
  *Why:* a relative path keeps working when the store moves from the laptop to the server.
- **D2. Retry on a later run.** Whenever a batch post is fetched again, each of its photos that is
  not held is attempted again, and the error entry is replaced by the new result. Gate E's "one
  retry within the same run" is a limit within one run.
  *Why:* the re-fetch brings a fresh link; the watermark overlap limits it to one or two retries.
  **Amended 2026-10-04 (task 1.12 review), approved by Ron — reposts:** this applies to a post's
  own photos in its own record (canonicals). A repost's photos, retries included, are attempted
  only while the canonical holds no image; once it holds one, a repost's photo that failed before
  is not attempted again and its error entry stays. The archive case (D4) is unchanged.
  *Why:* one rule for reposts, and no duplicate photos on the card, which is the reason behind
  #72.3.
- **D3. Canonical and reposts new in the same run:** the canonical first, its retry included; then
  its duplicates in canonical-rule order, each checked after the previous one finishes.
  *Why:* otherwise the same photos are stored twice.
- **D4. #72.3's "when the canonical is archived" is read on the stored state, before #74:** a
  repost downloads when the stored record was archived and `dedup_a` brought it back this run, for
  the reposts that brought it back, in D3 order. A canonical that is still archived downloads
  nothing.
  *Why:* the original images were deleted at archive and their links have expired.
- **D4b. Phase 5, the archive job:** archiving deletes the image files **and** removes their
  `PostImage` entries.
  *Why:* the record always reflects what is on disk.
- **D5a. A disk write error (disk full, permissions) fails the run.** It is not "a failed
  download".
  *Why:* otherwise a full disk silently loses a whole window's images.
- **D5b. A time budget for the download step**, a module constant. Photos not attempted in time
  are recorded as failures (`"not attempted: time budget"`) and follow D2.
  *Why:* a hanging CDN must not hang the run.
  **Amended 2026-10-04 (task 1.12 review), approved by Ron: 30 minutes, not 10.**
  *Why:* the check measured about 1.6 s per photo, so 10 minutes covers about 375 photos and a
  bootstrap run holds about 540–630; photos past the budget are lost for posts that are never
  fetched again. 30 minutes covers about 1,100. A normal run is far below either figure.
  Consequence: a run can last longer than the 30-minute interval; the phase 5 scheduler runs one
  run at a time (#61).
- **D5c. The `User-Agent: Mozilla/5.0` header is sent**, as in the spike. It is not a login or a
  cookie (invariant 13). Kept whatever the no-header requests show (they all succeeded).
- **D5d. A re-fetched post that lost photos to an edit keeps the entries already held.** A
  canonical may hold both its own photos and an earlier repost's.
- **Location.** `tlv_hunter/images/download.py`, a plain module, not a seam. `CLAUDE.md` names it
  in one line.
- **`SCHEMA.md` Gate E, wording only:** #76 in the download rule; the `images` row is one entry per
  photo attempted; the "Reposts" and retry rules reflect D2–D4. No field or type change;
  `schema_version` stays 1.

For D5c, D5d and the location, no reason was recorded.

### 78 — Task 1.13: the per-group watermark
Approved by Ron, 2026-10-04. **Amends #20 and #36's formula, `RESEARCH.md` §4 and `PHASE_1.md`
1.13; settles #71 J; sets the rules of `last_success_at` and `consecutive_failures` (Gate E).**
Each point was presented to Ron as a recommendation with the reason given here, and he approved
it. The rest of the task 1.13 plan was approved as written.

- **W1. The run's window starts at the last successful run's start minus the buffer.** The
  group's `watermark` stays the highest `posted_at` seen and is still stored, but it no longer
  sets the window. `SCHEMA.md`'s "never run time" still holds for `watermark`.
  *Why:* under the documented rule (`min(all watermarks) - buffer`) every run reaches back to the
  quietest group's last post (gaps of 26.7 h and 28.6 h in the spike data): about 107 rows per run
  and about $179/month, against the ~$12–16/month Ron accepted. Invariant 2 holds:
  `last_success_at` moves only after a successful run, so a failed run widens the next window.
  A daily wide run covering 24 h, about $5/month, to heal a per-group miss within a day: phase 5,
  the scheduler (`BACKLOG.md`). Recorded, not built.
- **W2. The buffer is 15 minutes**, a module constant (`BUFFER` in `watermark/window.py`), not a
  config key.
  *Why:* about $2.5/month in rows billed twice; no reason to edit it from the dashboard.
- **W3. `max_posts` goes from 30 to 50** in `config/collection.yaml`. A group at `max_posts` still
  advances; `advance` returns the cut-off groups so that task 1.14 logs them with the `run_id`. A
  group is cut off when it returned `max_posts` posts or more and its oldest is later than its own
  window start (its watermark minus the buffer, never before the run's `since`). Holding the
  watermark back is ruled out: posts arrive newest first, so the same window returns the same
  newest posts.
  *Why:* billing is per returned result, so under W1 a higher `max_posts` costs nothing on a
  normal run and covers a longer outage (about 16 h of the busiest group instead of about 10).
  50 and not more: the $0.50 cap derives `maxItems` 333, and 6 × 50 = 300 stays below it; above
  55 a run after a long outage would fail, and keep failing. When group editing is planned:
  groups × `max_posts` must stay below the cap's `maxItems` (a seventh group at 50 crosses it;
  `BACKLOG.md`).
- **W4. A group that fails inside a successful run is a known limit.** Detecting it from the run
  log and holding back only the failed group is its own task (`BACKLOG.md`): it needs the run-log
  endpoint verified under the skill, one small test run against an unreachable group (about
  $0.01, approved by Ron when planned), and `fetch()` returning per-group status.
  *Why:* that detection rests on a log format that is ASSUMED (`ASSUMPTIONS.md` P13); nothing is
  built on ASSUMED.
- **W5a. `last_success_at` is the start of the last successful run,** read from our clock before
  `fetch()`.
- **W5b. `consecutive_failures` counts consecutive successful runs in which the group returned
  zero rows;** it resets to 0 when the group returns any row. The field is not renamed. The alert
  thresholds are decided in phase 5: a healthy group can be silent for 31 h, about 49 runs
  (`BACKLOG.md`). Rule text in `SCHEMA.md`; no field or type change; `schema_version` stays 1.
  *Why:* nothing is written after a failed run, so the field cannot count failed runs.
- **W6. No per-group local filter for storage:** every fetched post goes on, and dedup handles
  repeats.
  *Why:* under W1 the run's window is the same for every group.
- **W7. A configured group with no record, outside bootstrap, raises an error that names the
  group.** Records of groups no longer configured are left untouched and do not count toward the
  window. When group editing is planned, adding a group needs a way to create its record without
  a full bootstrap (`BACKLOG.md`).
  *Why:* a loud failure is better than a run that silently skips a group.
- **A row skipped under #71 D that is newer than its group's watermark:** no change. The watermark
  advances past it when the group has a newer post; the row would fail to map the same way on
  every run.
- **Location.** `tlv_hunter/watermark/window.py`, a plain module with no storage of its own:
  `run_since(records, group_ids)` and `advance(records, group_ids, posts, *, run_started_at,
  since, max_posts) -> WatermarkAdvance` (the records and the cut-off groups). Task 1.13 writes
  nothing; task 1.14 calls `WatermarkStore.save_all`. `CLAUDE.md` names it in one line.

For W5a, the skipped row and the location, no reason was recorded.

### 79 — Task 1.14: `run_once` and bootstrap
Approved by Ron, 2026-10-04. **Settles the six open points of `PHASE_1.md` 1.14; amends the Phase 1
DoD item 2 and `BASELINE.md` §4 (wording).** Each point was presented to Ron as a recommendation
with the reason given here, and he approved it. The rest of the task 1.14 plan was approved as
written.

- **D1. The bootstrap window is 24 hours,** a module constant next to the flag (`BOOTSTRAP_WINDOW`
  in `tlv_hunter/jobs/run_once.py`).
  *Why:* about 125 rows, about $0.19, up to 13 minutes of downloads; it leaves a wide margin under
  the 30-minute budget on a busy day. (72 h was the alternative: more posts from quiet groups,
  closer to the budget.)
- **D2. The four real runs that close the DoD are approved as a plan:** A bootstrap; B a normal run
  started at least 15 minutes after A ends; C a normal run killed during the photo download; D the
  recovery. Each sends the $0.50 cap. Worst case 4 × $0.455 = $1.82, hard ceiling $2.00 ($2.50 if C
  is repeated once). They run only after Ron's separate go.
- **O1. `run_once` replaces `run_pipeline`; the Phase 0 exit test is ported.**
  *Why:* `run_pipeline` calls the classifier stub and stores through `upsert` only, against "no
  model in phase 1" and #64.
- **O2. The store step,** a private function in `pipeline.py`. The order: the records of stored
  canonicals outside the batch, then the batch canonicals, then the batch duplicates. Every post
  goes through `upsert_with_lifecycle`, then `save_lifecycle`.
  *Why (a finding of the 1.14 planning, confirmed by a test that fails under the provider's
  order):* each write is its own transaction. The provider returns posts newest first, so a
  duplicate usually comes before its canonical; a stored duplicate pointing at a canonical that is
  not stored makes every later `dedup_a` raise, and collection stops for good. A stored canonical's
  record saved after the new duplicate that changed it means, after a crash between the two, that
  the duplicate is no longer new to the store (#75 E1): an archived canonical never comes back
  (#74), and the #77 D4 repost download is lost.
- **O3. A stored post with no lifecycle record,** found by `find_without_lifecycle` at the start of
  every run, before the fetch: its record is built with `initial_lifecycle` and saved, and the run
  logs at error level the count and the `listing_id`s.
  *Why:* it should not happen; repairing and continuing is better than stopping collection.
- **O4. `--bootstrap` on a store that already has records is allowed,** with a warning naming the
  groups.
  *Why:* today it is the only way to add a group (#78 W7).
- **O6.** A relative `store_root` resolves against the repo root, not the working directory.
- **O7. `annotate` raising on a post fails the run.**
  *Why:* it is our own code, so a failure is a bug that must be seen.
- **O8.** Log lines are JSON on stderr, each with the run's `run_id`.
- **O9.** The watermark records are read again just before `advance`: a run overtaken by a later
  one fails there and moves no watermark backwards.
- **`store_root`:** created by a `--bootstrap` run; a normal run with no
  `<store_root>/tlv_hunter.sqlite3` stops before anything is constructed. `SQLITE_FILENAME` lives in
  the entry, `tlv_hunter/jobs/run_once.py`, the only code that constructs both modules (#65).
- **Names, approved:** the `APIFY_TOKEN` environment variable, read in the entry only and never
  logged; the module `tlv_hunter/jobs/run_once.py`; the `--bootstrap` flag.
- **Wording:** Phase 1 DoD item 2 reads "a second run started at least 15 minutes after the first
  ends". A bootstrap run stores everything inside its window, up to `max_posts` per group.
  `BASELINE.md` §4: in phase 1 the post is stored before the model, as `"pending"`; the model
  updates the stored post later. thedoor's log lines name the Apify run ID `apify_run`, so that
  `run_id` is only ours.
- **Not resolved:** #11 says the first run "sends one summary"; `BASELINE.md` §4 says a bootstrap
  run alerts nothing. Ron decides when phase 4 is planned (`BACKLOG.md`).

For O6, O8, O9, `store_root`, `SQLITE_FILENAME` and the names, no reason was recorded.

---

## Corrections to recorded facts

These are not decisions but findings that invalidated something previously written down. Kept here
so the corrections are visible in one place.

| What was believed | What is true | Found |
|---|---|---|
| Phone number is the real primary key of a listing | Present in 50% of posts; absent from both sides of one duplicate pair | Task 1.2, 2026-09-14 |
| `user.id` is always a rotating `pfbid` | Sometimes a plain numeric ID with a real vanity profile URL. The rule (never a key) is unchanged; the reason is stronger — sometimes stable, sometimes not, no way to tell | Gate A, 2026-09-14 |
| The marketplace flag is `isMarketplaceListing` | It is `sale_post.isOnMarketplace`, and it was `false` on a structured `sale_post` that had both a price and a location. "Structured listing" and "on Marketplace" are different things | Gate A, 2026-09-14 |
| `sale_post.price` is a price | It is a **string with a currency symbol** (`"₪3,600"`) and needs parsing | Gate A, 2026-09-14 |
| Video media items have `width` and `height` set to `null` | They **omit the keys entirely**. A missing key maps to `None` | Phase 0 build, 2026-09-14 |
| `page_url` is always `facebook.com/photo/?fbid=…` | Photos yes; videos get a `/videos/` page | Phase 0 build, 2026-09-14 |
| The actor's absolute date filter accepts full ISO | Date only. Minute granularity comes from the **relative** form instead | 2026-09-14, OpenAPI |
| The actor page's "from $1.00" is the price | It is a tiered floor. The working rate is $1.50 | 2026-09-14 |
| Near-duplicate matching might be required | It is not. 3/3 pairs collided on hash, no false collisions, no near-misses above 0.90 | Task 1.2, 2026-09-14 |
