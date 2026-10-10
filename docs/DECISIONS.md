# Decisions

Every decision that shapes this project, with the reasoning behind it.

**Read this before proposing to reverse something.** A decision recorded here was made against a
specific constraint; if that constraint still holds, the decision still holds. If it no longer
holds, say so explicitly and change the entry — do not quietly work around it.

Superseded decisions are kept, marked, and left in place. Deleting them would lose the fact that
the question was considered at all.

**Last updated:** 2026-10-10 (#242–#257, the content of Gate C; #258–#287, Gate C's open points, the technical
choices and the area grouping; #173, #251, #254 and #257 corrected)

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

*Holds for any provider: the model provider is OpenAI since #126 (2026-10-05).*

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

*"Kept as text" is stale: since #63 (2026-10-04) a flagged post is kept whole, `raw` included; only
its images are deleted at archive. Noted 2026-10-05.*

### 51 — The filter model
**Supersedes #41 and #15.** Listing kind is a hard filter; area and price are fixed critical;
"women only" is critical by default and can be turned off; the rest are preferences that a user
can make critical; no value means no effect. One profile holds separate values for a room and for
an empty apartment. `BASELINE.md` §8.

*Refined by #245–#247 (2026-10-10): two search options, each on or off with its own full set of values; sublets
are a switch inside each; the sqm filter only in the empty-apartment search.*

### 52 — Alert rules
A new, non-rejected post that passes the user's kind and critical conditions, has an explicit
price and an understood location. Preferences never block an alert. `BASELINE.md` §9.

### 53 — Area is decided by the model from the street and the hints in the text
A street that crosses several areas with nothing to settle it carries all of them and is marked
unclear; it still matches and alerts if one of them was chosen. A location the model cannot place
gets no area and never alerts. Areas come from a closed list taken from a public source.
`BASELINE.md` §7.

*Amended by #87 (2026-10-05): the model extracts the streets and the neighbourhoods the text points
at; code decides the area, by the rules of #88. The source of the list: #81.*

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

*Settled by #105 (2026-10-05).*

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

*The classification job is covered by "one run at a time" too (#140, 2026-10-05).*

### 62 — Each user sees which posts they have already viewed
- "Viewed" is per user and never written on the post (invariant 12). It is a separate per-user
  record (user, post, time), settled at Gate C in phase 3.
- It survives a repost, since a repost updates the existing card. It is deleted with the post.
- The exact trigger is decided in the phase 3 UI design, together with a manual "mark as not
  viewed".
- Display order: all unviewed posts first, then the viewed ones; within each group, the order in
  `BASELINE.md` §8.

*The trigger and "mark as not viewed": #253 (2026-10-10).*

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
  later run when the post is fetched again (D2); a disk write error fails the run (D5a). Since
  #80 (2026-10-04): a network error waits on a schedule instead of the one retry, and failed
  photos are retried from the stored link.*
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

*Amended by #75 F3 (2026-10-04): `Repository` gains `get(listing_id) -> RawPost | None`. Amended
by #80 (2026-10-04): `Repository` gains `find_lifecycles_with_image_errors(prefixes)`.*

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
  2026-10-04. The container's version is unknown (`ASSUMPTIONS.md` I8). *Amended by #80
  (2026-10-04): the store module's minimum is 3.38.0, for the JSON functions; `state` keeps
  3.24.0.*
- **Known limit:** `save_lifecycle` is last-write-wins. Phase 1 has one writer. A contract test pins
  the behaviour, and the concurrent case is an open choice for phase 3 (`BACKLOG.md`).
  *Settled 2026-10-10: compare and set (#260); the rollback journal stays in Phase 3 (#259).*

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
  approved). Recorded as a known gap (`ASSUMPTIONS.md` P16), for Gate B. *Kept as a known limit
  at Gate B by #107 (2026-10-05).*
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
   *Settled by #252 (2026-10-10): such a post is a new post; nothing ties it to the old one.*

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

*Closed by #89 (2026-10-05): the classification record's existence means the post was classified.*

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
  design. *Display rule amended by #122 (2026-10-05): the card's main time is the last
  publication; the earliest belongs to the repost log.*
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
  *Amended by #80 (2026-10-04): a failed photo is also retried from the stored link, without a
  re-fetch, while its post is less than 4 days old; the repost rule above still applies.*
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

### 80 — The photo download waits on a network error, and retries failed photos from the stored link
Approved by Ron, 2026-10-04, after run A. **Amends #63 (the one retry within a run, for network
errors only), #64 (`Repository` gains a method), #65 (the store module's minimum SQLite version)
and #77 D2 (retry only on re-fetch); amends `PHASE_1.md` 1.12 and the 1.12 plan's "stored posts
outside the batch are never downloaded".** The finding: in run A the laptop's network dropped at
13:05:37Z and the downloader did not wait; every remaining photo failed at once, twice, 546
attempts in 1.25 s. How long the outage lasted is unknown.

1. **A network error waits, on a fixed schedule set by Ron.** When a download fails with a
   network-type error, the whole download step waits 1 minute and tries the same photo again;
   then 3 minutes; then 5; then a last attempt after 10 (`NETWORK_WAITS_SECS = (60, 180, 300,
   600)` in `images/download.py`). Per outage, not per photo: any reply ends the waiting, and a
   later network error starts the schedule again. A network error no longer gets #63's second
   pass; other errors keep it.
   *Why (Ron's words):* network drops are possible, though probably rare at home; a backup like
   this is worth building properly so that data which could easily be saved is not lost.
2. **Failed photos are retried from the stored link.** On every run, after the batch's own
   downloads, the photos of stored posts whose entry is a network-type error or `not attempted:
   time budget` are attempted again from the link already stored, with no Apify call. An HTTP
   error (an expired link) replaces the entry and ends the retries. The repost rules hold: the
   canonical's own photos first, then its reposts' in canonical-rule order, and a repost's only
   while the canonical holds no image (#72.3, #77 D2, D3); an archived post is skipped (#77 D4);
   a post in the batch is left to the batch path.
   *Why:* free, it recovers the 53 posts of run A while their links live (about until
   2026-10-08, I7 ASSUMED), and it heals any later outage and any time-budget overflow by itself.
   A second bootstrap would cost about $0.32 and recover only part: two groups are cut off at 50.

Each point below was presented to Ron as a recommendation with the reason given here, and he
approved it.

- **§4. The waits count inside the 30-minute download budget** (#77 D5b); a wait stops when the
  budget runs out.
  *Why:* a run's length stays bounded; what was not attempted is retried on the next run for
  free. Without it a flapping network stretches a run with no upper bound.
- **U1. A timeout counts as a network error in both cases:** the socket timeout and the 60-second
  cap per photo. Network-type: `network: …` (DNS, connection, TLS, a dropped connection) and
  `timeout`; never an HTTP status or a judged response.
- **U2, as settled with Ron on 2026-10-04 while building:** no new error text. U2 was approved as
  "photos skipped because the network is down are recorded as `not attempted: network down`";
  under U3 no photo is skipped, so nothing would write it, and Ron chose to drop it. Every entry
  records a real attempt.
  *Why (U2's own):* an entry must not claim an attempt that never happened.
- **U3. After the schedule runs out, each remaining photo is tried once without waiting; the first
  reply restarts the schedule.** Settled with Ron while building: any reply counts, an HTTP or
  content error included, since it shows the network is up.
  *Why:* one dead host must not cost every other photo of the run; a real outage costs only fast
  failures.
- **U4. Stored-link retries never wait:** one attempt each per run, a network error stays on the
  entry, and the budget still applies.
  *Why:* one stored link that always fails must not cost 19 minutes on every run.
- **U5. A stored link is retried only while the post's `fetched_at` is less than 4 days old**
  (`STORED_LINK_MAX_AGE`, a module constant), measured from the run's start. For a repost's
  photo, the repost's `fetched_at`. `fetched_at` is the first fetch: a post fetched again later
  carries a newer link than its `fetched_at` says, so the limit errs on the short side.
  *Why:* the design assumes an expired link returns an HTTP error, which has never been observed
  (I7); if it fails as a network error or a timeout instead, hundreds of dead links would be
  attempted on every run until archive. 4 days sits under the ~4.4-day link life and does not
  rest on that assumption. One free GET on an expired run A link after 2026-10-08 is in
  `BACKLOG.md`.
- **U6.** A stored post that no longer contains the photo's `media_id` is skipped, and the entry
  left as is.
- **U7.** Accepted: a repost's entry blocked by the repost rule keeps its network error.
- **Contract (#64 amended):** `Repository.find_lifecycles_with_image_errors(prefixes) ->
  list[PostLifecycle]`, the records with at least one image entry whose `error` starts with one of
  the prefixes, ordered by `listing_id`. Which errors to ask for stays in `images/download.py`.
  SQLite answers with its JSON functions (`json_each` over `$.images`, `->>` on `error`); no layout
  change. Both stores, with contract tests.
  *Why:* without the method the whole store is scanned in Python on every run; the JSON query
  matches the image entries exactly instead of depending on how the document is serialized.
- **Minimum SQLite version (#65 amended):** the store module needs 3.38.0, the first release with
  the JSON functions and operators built in by default (read on sqlite.org/json1.html,
  2026-10-04); its constructor refuses an older SQLite. Ron: there is no constraint on the
  version, since the home server is not built yet and will be set up to match. The `state`
  module, which uses no JSON function, keeps 3.24.0.
- **Names, approved:** `NETWORK_WAITS_SECS`; `find_lifecycles_with_image_errors`. `too slow` is
  not introduced (U1); `not attempted: network down` was dropped (U2).
- **`SCHEMA.md` Gate E download rule:** wording only. No field or type change; `schema_version`
  stays 1.
- **Found while building, fixed:** a stored canonical outside `dedup_a`'s result kept only the
  first photo recorded into its record in one run; the rest were lost. Task 1.12's code; a
  regression test now covers it. Run A was not affected: in a bootstrap every canonical is in the
  batch.

For U1, U6, U7, the minimum version and the names, no reason was recorded.

---

## Decisions from 2026-10-05

Approved by Ron, 2026-10-05, settled with the review chat: the source of areas and streets, and the
content of Gate B. **Approved in substance only:** English field names and exact types are not
approved; they are proposed in `SCHEMA.md` (the Gate B draft) and approved separately. Where an
entry says "no reason recorded", none was given.

### 81 — The closed list of areas is the municipality's `שכונות` dataset, all 71 entries
GIS layer 511, all 71 entries, with the Old North in its two parts (30 and 31). Non-residential
entries stay in the list. **Settles the source in `BASELINE.md` §7 and the choice left open in
`ASSUMPTIONS.md` A1a.**
*Why:* the only verified open source with the split Ron asked for; pruning makes the list differ
from its source.

*Refined by #249 (2026-10-10): the non-residential entries are not hidden from the area filter; they sit in a
collapsed group at its bottom.*

### 82 — The model classifies to the 71 entries; any grouping is a display rule
Any grouping of the entries is decided at Gate C.
*Why:* merging later is free; splitting later costs a reclassification.

*Settled by #248 (2026-10-10): grouped under region headings, display only; which grouping waits for Ron.*

### 83 — An area is identified by its municipal number
The number is `ms_shchuna` in layer 511; the name is a label.
*Why:* a spelling fix must not break classified posts.

### 84 — Streets per area are derived from OpenStreetMap
The table is derived from OpenStreetMap. Its completeness is checked against the Population
Authority's street register before the table is relied on. The municipality's address layer (GIS
layer 527) is not used, because of its terms (`RESEARCH.md` §12). **Settles the choice left open in
`ASSUMPTIONS.md` A1b.** No other reason recorded.

**Status: superseded by #167 (2026-10-05):** the model decides the area; no street table is derived in phase 2 (#168). A street table as an aid is recorded for later (#169).

### 85 — A manual corrections file overrides the derived street table
Small and maintained by Ron. It overrides the derived table and survives regeneration. No reason
recorded.

*Amended by #110 (2026-10-05): a correction reaches only posts classified after it.*

**Status: superseded by #167 (2026-10-05):** the model decides the area; there is no corrections file (#168).

### 86 — A translation table from colloquial names to list entries
It starts with:

| Written | Entries |
|---|---|
| הצפון הישן | 30, 31 |
| הצפון החדש | 33, 34, 35 |
| כיכר המדינה | 34 |
| לב העיר, לב תל אביב, מרכז העיר | 37 |
| יפו, with no detail | 42–49 |
| כפר שלם | 68, 69 |
| שרונה | 40 |

It stays open and grows from real posts only. An area name the model cannot map is stored as
unclear, so that such cases can be collected. No reason recorded.

*Amended by #111 (2026-10-05): code applies the table; an unmapped name is stored as written and maps to nothing.*

*Partly superseded by #167 (2026-10-05): the rows become examples in the model's instructions, not a table in code.*

### 87 — The model extracts; code decides the area
**Amends `BASELINE.md` §7 and #53. Resolves the mismatch between §4 (street and area as a step
after the model) and §7 (the model decides the area).** The model extracts the streets as written
and the neighbourhoods the text itself points at; code decides the final areas.
*Why:* a table fix costs no model call, and a wrong area can be traced to the model or to the
table.

*Amended by #110 (2026-10-05): the areas are stored on `Listing`, computed at classification time.*

**Status: superseded by #167 (2026-10-05):** the model decides the area; code no longer computes it.

### 88 — The area rules, in order
1. An area stated in the post decides. A street only refines inside it (for example, which part of
   the Old North), and is shown on the card.
2. A stated area and a street the table places elsewhere: the stated area wins, with no orange.
3. A street with no stated area: the table decides. If it gives several areas, the post carries all
   of them, marked unclear.
4. Two streets ("X corner Y"): the areas common to both. If there is no common area, all the areas
   of both, marked unclear.
5. A street not in the table and no stated area: the area is unclear. No alert, as in
   `BASELINE.md` §7.
6. Filtering is always by area, never by street.

No reason recorded.

*Clarified by #124 (2026-10-05): an area name that maps to nothing does not decide; the street does.*

*Since #167 (2026-10-05) these rules are instructions to the model, not code.*

### 89 — The classification is its own record per post
Keyed by `listing_id`. The record's existence means the post was classified. **Closes the open
point of #74:** an archived post with no rejection reason that is reposted returns to `"active"` if
it has a classification record, and to `"pending"` if it does not. No reason recorded.

### 90 — The classification record carries its provenance
The schema version, the model name, the prompt version and the classification time.
*Why:* the prompt will change often without a schema change.

### 91 — Every marked field is a state and a value, in one structure
The state is written, not written, or unclear. "No" is a written value. One structure serves every
such field. **Extends #54:** the colours of `BASELINE.md` §6 stay display rules over these states.
No reason recorded.

*Amended by #109 (2026-10-05): an unclear field keeps no value.*

### 92 — The model returns facts; code derives the rejection and its reason
*Amended by #214 (2026-10-08): the city of the other-city rejection comes from Facebook's location
field when the post has a usable one.*
The reasons are Gate E's (`SCHEMA.md`).
*Why:* a rule change needs no reclassification.

### 93 — Post nature
One of: rental offer, sublet offer, seeking, for sale, not a listing. It has no "unclear" value.
A sublet is **not** a rejection: it is hidden through the listing-kind filter, as `BASELINE.md`
§8 says. A post is a sublet when it says so, or when it states an explicit temporary period.
Someone seeking a sublet is "seeking". **Keeps #58** (a sublet has no duration). No reason
recorded.

*Refined by #159 (2026-10-05): a sublet offered as an option before a regular lease is a rental offer.*

### 94 — Apartment kind
Room in a shared flat, or whole apartment, in the state structure (#91). "3 rooms, suits
roommates" and a studio are whole apartments. No reason recorded.

### 95 — Price
A list of prices in ILS, usually one, with its source. The model reads the text. When the text has
no price, the provider's `native_price` is used. When both exist and differ, the text wins. The
card shows "X/Y"; filtering uses the lowest. A price per roommate for a whole apartment, or a price
in another currency, is unclear. No reason recorded.

*Amended by #114 (2026-10-05): a `native_price` below 500 is ignored; an unclear text price stays unclear.*

### 96 — Entry date
The text as written, plus a comparable value: immediate, or a date. "Start", "middle" or "end of
November" give the 1st, the 15th or the last day. A missing year means the nearest such date after
the post's publication. "Flexible" is unclear. **Rewords the `entry_date` trap in `CLAUDE.md`:**
the original text is never replaced; the comparable value sits next to it. No reason recorded.

*Amended by #115 (2026-10-05): the model returns the parts; the year is the nearest occurrence, before or after.*

*Extended by #123 (2026-10-05): a month with no day is the 1st; "end of February" is the 28th.*

### 97 — Rooms
A number, halves allowed, always the total in the apartment. No reason recorded.

### 98 — Floor
A number, with the ground floor as 0, plus the building's floor count only when it is written. No
reason recorded.

### 99 — Size
The apartment's size in sqm, plus the room's size only when it is written. No reason recorded.

*The sqm filter: #247 (2026-10-10), the empty-apartment search only.*

### 100 — Broker, balcony, parking, elevator, air conditioning
Each is yes or no. A shared balcony is yes. Street parking is no. "Option for parking" is unclear.
No reason recorded.

### 101 — Arnona and house committee
Each is an amount, or "included in the price". "All included" is unclear. "400 per two months" is
stored as 400: the model never divides. No reason recorded.

*Refined by #160 (2026-10-05): one amount covering several charges is unclear.*

### 102 — Furnished
Yes, yes partially, or no. "Option to leave furniture" is unclear. No reason recorded.

### 103 — Gender, one field
No restriction, women preferred, or women only. There is no "men only" value. Feminine-only wording
(`מחפשות שותפה`) is women only. **Keeps #58** (women only hides; women preferred is a mark).
*Why, for the feminine wording (Ron):* it always means that. Otherwise no reason recorded.

*Amended by #117 (2026-10-05): a plain field; silence is "no restriction".*

### 104 — Streets, neighbourhoods and city
Streets: a list, as written. Neighbourhoods the text points at: a list of municipal numbers (#83).
The city, as written, only when it is not Tel Aviv-Yafo. No reason recorded.

*Amended by #111 (2026-10-05): the model returns the names as written, not numbers.*

### 105 — Names next to phones
The model returns name-number pairs. A name is kept only when its number equals one the code
already extracted. **Settles #57.** No reason recorded.

### 106 — A value that is not written is never filled in
"3/4" or "X of Y" is shown only when the second part is in the post. No reason recorded.

*Exception by #161 (2026-10-05): "דירת N שותפים" gives rooms = N (N+1 with a living room). Extended by #162: a name not in the text is dropped.*

### 107 — A shared post with its own caption stays a known limit
Its `text` is the caption; `sharedPost.text` does not reach the model. **Keeps #71 H**
(`ASSUMPTIONS.md` P16). No reason recorded.

**Ron's answers to the Gate B draft, 2026-10-05.**

Approved by Ron, 2026-10-05: his answers to the 13 points of the Gate B draft's "For Ron's
decision" list, and three card rules the review chat had left out of the earlier message. Point 13
(the model's response against the stored record) was not decided: it belongs to the phase 2 plan
(`PHASE_2.md`).

### 108 — Gate B names and types approved as proposed, except where changed below
The record is `Listing`. Every name and type in the draft stands unless #109–#119 changes it. No
reason recorded.

### 109 — An unclear `Marked` field keeps no value
When `state` is `"unclear"`, `value` is `None`. Nothing read is kept. **Amends #91.** No reason
recorded.

### 110 — The final areas are stored on `Listing`, in one field
`areas`: the municipal numbers, computed by code at classification time by #88's rules. There is no
separate "unclear" field: the colour is derived from the list.
- One area: definite.
- Two or more: unclear (orange). The post matches, and alerts, if any of them is chosen.
- Empty, and the post gave a street or an area name: unclear, no alert.
- Empty, and the post gave no location: not written.

A change to the translation table or the corrections file applies only to posts classified from
then on. Existing posts are **not** re-derived, and no re-derive mechanism is planned (Ron: not a
disaster). **Amends #87** (the area is still decided by code; it is now stored) and **#85** (a
correction reaches only posts classified after it).
*Why (Ron):* it is one field and saves repeated computation.

*Partly superseded by #167 (2026-10-05): `areas` is returned by the model, not computed by code; it is still stored on `Listing`, and the colour still comes from its length.*

### 111 — Code applies the translation table; the model returns area names as written
The model returns the neighbourhood names as written: `stated_area_names`, a list of strings, `[]`
when none, plain (not `Marked`). It replaces `stated_areas`. Code maps the names to entries through
the translation table. **Amends #104** (no longer municipal numbers from the model) **and #86**
("stored as unclear" becomes: the name is stored as written, and maps to nothing).
*Why:* the table must grow from real posts, and with numbers an unmapped name would not be stored
at all; a new row needs no model call.

*Partly superseded by #167 (2026-10-05): no translation table is applied by code; `stated_area_names` stays, as written, for the card and error analysis.*

### 112 — A stated area that maps to several entries, with no street to refine it, is unclear
Orange, by #110's rule (two or more areas). Gate C gets a row: no orange for a user who chose every
entry the name covers, a per-user display rule. No other reason recorded.

*Since #167 (2026-10-05), an instruction to the model.* *The Gate C row, generalized: #250 (2026-10-10).*

### 113 — The two meanings of "unclear" for the area are intended
Several candidate areas (matches, alerts, orange) and no area at all (no alert). Confirmed by Ron.
No reason recorded.

### 114 — A `native_price` below 500 ILS is ignored
Below 500 the post has no price from `native_price`. A constant, not config. It applies to the
native fallback only, never to a price read from the text. When the text's price is unclear and a
`native_price` exists, the price stays unclear: the fallback is used only when the text has no
price at all. **Amends #95.**
*Why:* no monthly rent in Tel Aviv is below 500. For the rest, no reason recorded.

### 115 — The entry date: the model returns the parts; code completes the year
The model returns the day and the month (and the year, when written), or "immediate". Code
completes a missing year with the occurrence **nearest** to the post's publication date, before or
after: "1.10" in a post of 5.10 is this year. Computed on the UTC date, no exception to invariant 9.
The stored field does not change. The year is never displayed. **Amends #96** ("the nearest date
after the publication" becomes "the nearest").
No reason recorded.

*Extended by #123 (2026-10-05).*

### 116 — Arnona and house committee keep no period
"400 per two months" and "400 a month" are both stored as 400. Accepted as a known limit. No
reason recorded.

### 117 — Gender is a plain field; silence is "no restriction"
`"no_restriction"`, `"women_preferred"` or `"women_only"`, not `Marked`. A post that says nothing
about gender is `"no_restriction"`. Ron had approved this earlier; it was missing from the review
chat's earlier message, an omission, not an open question. **Amends #103** (no state structure).
No reason recorded.

### 118 — Sizes are decimals; a basement is floor -1
`size_sqm` and `room_size_sqm` are decimal numbers. `floor` stays a whole number; a basement is -1.
**Extends #98, #99.** No reason recorded.

### 119 — Five area names get a hand-corrected display label
Entries 5, 7, 17, 18 and 49, whose geresh or parenthesis the source places at the logical start.
The source name is kept verbatim next to the label. **Extends #83** (the name is a label).
No reason recorded.

### 120 — Rooms on a room post
Shown as "1 of N" when the apartment's total is written, and as a room with no "of" when it is
not. The "1" comes from the apartment kind, not from the text. A display rule. Approved by Ron
2026-10-05; omitted from the review chat's earlier message. No reason recorded.

### 121 — Size on a room post
"X sqm for the room, of Y" when both sizes are written; "X sqm for the room" when only the room's
is. A display rule. Approved by Ron 2026-10-05; omitted from the review chat's earlier message. No
reason recorded.

### 122 — The card's main time is the last publication
The latest repost's time, shown relative: minutes up to an hour, hours up to 24 h, days after
that. Earlier publications are in the repost log. **Amends #75 A's display rule** (the card no
longer shows the group's earliest publication as its main time; the earliest time belongs to the
repost log). Approved by Ron 2026-10-05; omitted from the review chat's earlier message. No reason
recorded.

**Gate B closed, the provider, and the phase 2 plan, 2026-10-05.**

Approved by Ron, 2026-10-05: his answers to Gate B's two open points, the move to OpenAI as the
model provider, and his answers to the 22 points of the phase 2 draft (`PHASE_2.md`). Where an
item says "proposed", only the proposal exists; the names wait for Ron.

### 123 — An entry month with no day is the 1st; "end of February" is the 28th
"כניסה בנובמבר" gives the 1st of the month, state written. "End of February" gives the 28th, in
any year. The year is completed as in #115. **Extends #96 and #115.** No reason recorded.

### 124 — An unmapped area name with a placed street: the street decides
When the post's area names map to nothing in the translation table and a street is in the street
table, the street decides, as if no area were stated (#88.3). The unmapped name is still stored in
`stated_area_names` and reported (#111). **Clarifies #88.1.** No reason recorded.

*Since #167 (2026-10-05), an instruction to the model.*

### 125 — Gate B approved
With #123 and #124 applied, Gate B (`Listing`) is approved, 2026-10-05: content #81–#107, names
and types #108–#119, the last two points #123–#124. The model's response shape is not part of
it: its names are proposed separately (#137). No reason recorded.

### 126 — The model provider is OpenAI, for now
Classification uses the OpenAI API. Gemini stays a researched alternative (`RESEARCH.md` §13); its
free tier is a possible later switch, not planned. **Replaces the Gemini choice of `BASELINE.md`
§4** (the model line there is settled after the spike). #22 holds unchanged: the response schema
is derived from pydantic at runtime.
*Why (Ron):* he already has a funded OpenAI API account, and this saves opening a Google project.
He will watch the number of calls and the cost of a real working day.

### 127 — The first model to try is `gpt-6-luna`
The cheapest model on OpenAI's pricing page as the review chat read it on 2026-10-05; verified
against the documentation the same day (`RESEARCH.md` §15). If it misses the regression bar, the
next model and its price go back to Ron: no other model is picked without him. No reason
recorded.

### 128 — `OPENAI_API_KEY` is read only in the entry point, never logged
It is in `.env`. Like `APIFY_TOKEN` (#79), only the command's entry point reads it, and it never
appears in a log line. No reason recorded.

*Amended by #188 (2026-10-05): only the commands that call the model read the key; the regression runner reads it too.*

### 129 — Rules name "the model", not a provider
Where a rule named Gemini (`CLAUDE.md` invariants 8 and 11 and the seams, `BASELINE.md` §2 and
§4, `SCHEMA.md`), it now says "the model". History entries and research keep their wording. No
reason recorded.

### 130 — The spike, revised
`gpt-6-luna` only, about 20 hard posts from the store. It answers: is the schema accepted; tokens
per post (input, cached, output, reasoning); the real cost per post; the behaviour at the
temperature settings the model allows; what failures look like. **Cap $2, enforced by the script
from the usage metadata.** The plan and its cost are presented; it runs only on Ron's separate go.
**Replaces points 2, 3, 4, 5, 19 and 22 of the phase 2 draft** (the tier, the Gemini model, the
temperature, the Gemini spike, the first run's cap, and the model line). No reason recorded.

### 131 — `Listing` and the lifecycle record are written in one transaction
Point 6 of the draft, as recommended: one Repository method writes both, plus `get_listing` and a
query for pending canonicals. A seam contract change (`CLAUDE.md`).
*Why:* a `Listing` saved with the lifecycle still `"pending"` would be classified and billed
again; the reverse leaves an `"active"` post with no fields.

### 132 — The area files live in `reference/`
Point 7, as recommended: `reference/` in git, holding `areas.yaml`, `area_aliases.yaml`,
`street_areas.generated.yaml` and `street_areas.corrections.yaml`.
*Why:* no personal data, they need history, and `config/` holds collection settings only.

### 133 — The street derivation: Geofabrik, `osmium` and `shapely`, a 15 m border buffer
Point 8, as recommended: streets from Geofabrik's `israel-and-palestine` extract, not Overpass;
`osmium` (pyosmium) and `shapely` in a dev-only dependency group, outside the package; a street
within about 15 m of a border belongs to both areas, tuned on known border streets.
*Why:* a file is repeatable and can be kept with its date (Overpass timed out twice); standard
local libraries, no server; streets drawn on a boundary touch both polygons only by rounding.

**Status: superseded by #167 (2026-10-05):** the model decides the area; no derivation and no `osmium`, `shapely` or `pyproj` (#168).

### 134 — The completeness bar is 95%
Point 9, as recommended: at least 95% of the register's official Tel Aviv streets found in OSM,
every miss listed for Ron. Below it, Ron chooses between corrections by hand and another source.
No reason recorded.

**Status: superseded by #167 (2026-10-05):** the model decides the area; no completeness check (#168).

### 135 — Written names are matched through a lookup key; invariant 8 widened
Point 10, option B. **Amends invariant 8:** normalized text exists only to compute a hash, or a
lookup key for street and area names. It is still never stored, never displayed and never sent to
the model. One normalization, the existing one (`textnorm`). The derivation reports every
collision among Tel Aviv street names (two names giving one key) before the table is relied on.
*Why (the draft's):* the same function on both sides cannot drift, and it absorbs spelling
variants without one row per variant.

*Extended by #158 (2026-10-05): exact key first, then leading Hebrew prefix letters stripped; collisions reported.*

**Status: superseded by #167 (2026-10-05):** the model decides the area; no lookup key; invariant 8 returns to its original wording (#168).

### 136 — The unmatched share is reported, with no alarm level, in phase 2
Point 11, as recommended. No reason recorded.

**Status: superseded by #167 (2026-10-05):** the model decides the area; no unmatched share (#168).

### 137 — The model's response is a separate pydantic model, with a drift test
Point 12, as recommended: a response model next to `Listing`; a contract test asserts that every
`Listing` field is either in the response model with the same type or in an explicit list of
code-filled fields. Its own field names (the entry-date parts, the phone pair) are **proposed**
in `SCHEMA.md` and wait for Ron (invariant 1).
*Why:* the two shapes really differ, and the test turns drift into a failing test, which is what
#22 guards against.

*Names approved by #151 (2026-10-05).*

### 138 — Classification runs as a separate job, `classify_pending`
Point 13, as recommended. Run by hand after a collection run in phases 2–4; the phase 5 scheduler
runs it after each collection run.
*Why:* the model can never touch collection or the watermark; a failed post stays pending for the
next run; the first paid run over the stored posts is the same command.

### 139 — A post that fails classification three times stops being retried
Point 14, option A, **a Gate E amendment**: two fields on `PostLifecycle`, a count of failed
classification runs and the last error. After 3 failed runs the job skips the post, which then
shows in the admin's pending list with its reason. Names and types are **proposed** in
`SCHEMA.md` and wait for Ron.
*Why (the draft's):* otherwise a post that always fails is paid for on every run, forever.

*Names, types and rules approved by #152 (2026-10-05).*

### 140 — The job and `run_once` never run at once
Point 15, as recommended: in phase 2 both are started by hand, never together; phase 5's "one run
at a time" (#61) covers the job too. The concurrent-write choice stays with phase 3. No reason
recorded.
*Since #260 (2026-10-10), this covers the job commands only, not the site.*

### 141 — A post edited after classification keeps its `Listing`
Point 16, as recommended, as a post with a verdict keeps its state (#73.2). No reason recorded.

### 142 — The regression set: about 50 posts, deciding fields labelled blind
Point 17: about 50 posts; labelling option C (Ron labels the deciding fields without seeing the
model's answer, and corrects the rest from it). The pass bar as proposed: `post_nature` and
`other_city` no error; `apartment_kind`, `price`, `gender`, `areas` at least 95% exact; every
other field at least 90%; no value filled in where the label says not written. **Added by Ron:**
a post Ron marks as ambiguous is not counted.
*Why (the bar, the draft's):* it follows the cost of each mistake.

*Amended by #177 (2026-10-05): streets and area names as written are not compared.*
*Refined by #190–#193 (2026-10-05): prices compared as a set; `other_city` as Tel Aviv-Yafo or not; each pass on its own; the fields not labelled blind measured from the review.*

### 143 — Labelling and corrections through local static pages in `data/labeling/`
Points 17 and 18, Ron's request. A labelling page, generated as a static HTML file in
`data/labeling/`, with no server and no network: per post, the original text and controls for the
deciding fields only (post nature, apartment kind, price, gender, entry date, streets, area names,
other city), radio buttons for closed values, short inputs for the rest, and an "ambiguous" mark.
It never shows the model's answer for those fields. Progress is kept in the browser; an export
button downloads one file with every answer, which Ron moves into `data/labeling/` once and the
code reads from there. The other fields are corrected afterwards from the model's output. The
review report (`PHASE_2.md` 2.7) uses the same mark-and-export mechanism for corrections,
**replacing the hand-written CSV** of the draft. The file names are fixed in `PHASE_2.md`.
No reason recorded.

*Amended by #177 (2026-10-05): no labelling controls for streets and area names; the areas are
picked from the 71 (#171).*

### 144 — Reclassify: manual, replace with a diff report; no bulk reclassify planned
Point 20, as recommended: started by hand only; the new `Listing` replaces the old, after a diff
report is written to `data/`; flagged posts keep their flag and state. A change to a table still
applies to new posts only (#110). Ron does not expect to reclassify 40 days of posts: no bulk
estimate is part of the phase's DoD. No reason recorded.

### 145 — Gate D is settled after the first paid run
Point 21, as recommended: a read-only script lists about 30 candidate pairs after the first paid
run; Ron judges them; dedup B is built in phase 2 only if rewritten reposts are common, otherwise
Gate D waits until after phase 3 with the measured rate recorded.
*Why:* a key designed before classified data is a guess, and a missed duplicate costs one model
call, not a correctness failure.

*Amended 2026-10-08 by #231: the key is settled in Phase 2 (#230); its use moves to Phase 3, derived and
not stored.*

**Ron's answers to `PHASE_2.md` §4, and the spike's go, 2026-10-05.**

### 146 — The 30-day abuse-monitoring log is accepted
No Zero Data Retention request is made. OpenAI's abuse-monitoring logs may keep the posts sent to
the model, phone numbers included, for up to 30 days (`ASSUMPTIONS.md` O6).
*Why (Ron):* the posts are public, and the API does not train on them.

### 147 — Every call sends `store: false`
The Responses API would otherwise store each response for 30 days (O6). No reason recorded.

### 148 — Reasoning effort starts at `none`
`low` only if accuracy at `none` is not enough. Decided on the spike's numbers, together with
temperature, which exists only at `none` (O4). No reason recorded.

*Settled by #157 (2026-10-05): effort `none`, temperature 0.*

### 149 — `model_name` keeps its rule; the reported version is logged too
`Listing.model_name` stays "the model identifier as sent in the call" (#108). The model value the
response itself reports is also logged, since `gpt-6-luna` is an alias with no dated snapshot
(O1). No reason recorded.

### 150 — Explicit prompt caching, one breakpoint after the instructions
A post is never written to the cache (O7). No reason recorded.

### 151 — The response model's names are approved
`ListingExtraction`, as proposed in `SCHEMA.md` (#137): `entry_date_parts` (`immediate`, `day`,
`month`, `year`) and `phone_name_pairs` (`phone`, `name`). No reason recorded.

### 152 — The Gate E classification-failure fields are approved
`classification_failures` (`int`) and `last_classification_error` (`str` / `None`) on
`PostLifecycle`, with the rules proposed in `SCHEMA.md` (#139): left as they are after a later
success; reset by hand only; a failed reclassify not counted; `schema_version` 2, a version-1
record reading as 0 and `None`. Docs only now; the code comes with task 2.5. No reason recorded.

### 153 — The first paid run's cap is $1
Its go is separate and not given. No reason recorded.

### 154 — The review report and `corrections.json` live in `data/labeling/`
Beside the labelling page: `data/labeling/review.html` and `data/labeling/corrections.json`. The
proposed shape of `labels.json` and `corrections.json` is approved (`PHASE_2.md` 2.6). No reason
recorded.

### 155 — The key belongs to a dedicated OpenAI project
The key in `.env` belongs to a project Ron opened for this app. The account holds about $9 of
credit. The usage tier is not confirmed: if a call is refused for the tier, the run stops and is
reported, with no workaround. No reason recorded.

### 156 — The spike runs, as planned
Ron's go for `PHASE_2.md` 2.1: `gpt-6-luna` only, the 20 posts, three settings, two passes each,
three failure probes, 123 calls, a $2 cap enforced by the script before every call and never
raised. If strict mode rejects the derived schema, the throwaway response model may be adjusted
until it passes, every change recorded; a change to an approved name or shape is listed for Ron,
not kept. One reasonable first prompt, not tuned for accuracy. No reason recorded.

**Ron's decisions after the spike, 2026-10-05.**

### 157 — The setting: effort `none`, temperature 0
Confirmed on the regression set by running it twice (temperature 0 is not deterministic,
`ASSUMPTIONS.md` O12). `low` stays the fallback. **Settles #148.** No reason recorded.

### 158 — Hebrew prefix letters on street and area names are handled by code
The model keeps returning names as written. Matching tries the exact lookup key first; only when
that fails, it strips leading Hebrew prefix letters (ב, ל, מ, ה, ו, ש, כ and their combinations)
and tries again, so names that begin with one of these letters (בבלי, התקוה, לבנה) are not harmed.
Every collision this creates among the 71 names, the translation table and the street table is
reported. **Extends #135.**
*Why (Ron):* the result is deterministic and can be checked against the text; the spike showed the
model changing a name unasked.

**Status: superseded by #167 (2026-10-05):** the model decides the area; no prefix-letter rule (#168).

### 159 — A sublet is only an offer that is itself temporary
A sublet offered as an option before a regular lease (the spike's post 5) is a rental offer.
**Refines #93.** No reason recorded.

### 160 — One amount covering several charges is unclear
"200 for arnona, internet and cable" makes `arnona` and `house_committee` unclear, like "all
included". **Refines #101.** No reason recorded.

### 161 — "דירת N שותפים" gives rooms = N
"דירת N שותפים" or "דירת N שותפות" gives `rooms` = N; N+1 when the post says there is a living
room. Ron's rule, **an explicit exception to #106** (a value not written is never filled in). No
reason recorded.

### 162 — A name the post does not contain is dropped; the model never computes
A check in code: a street or area name the model returns that does not appear in the post's text
is dropped from the `Listing` and counted in the report. The prompt says the model never computes
a value (the spike once turned "3.50*3.50" into 12.25 sqm). **Extends #106 and invariant 11.** No
reason recorded.

*Kept by #167 (2026-10-05): the check that drops a name not in the text stays.*

### 163 — Classification never touches the source text
The model receives a copy and returns a separate answer; the classification job never writes a
`RawPost`; the card always shows the stored original. A new invariant in `CLAUDE.md`, with a test:
the stored `RawPost` is identical before and after a classification run. Ron's rule; no further
reason recorded.

### 164 — The first paid run has no go yet
It comes after the build and a passing regression set, in `PHASE_2.md`'s order. No reason
recorded.

### 165 — The regression set holds a real "seeking" post and a real Jaffa post from the store
The spike's two were for-sale posts picked by a wrong pattern. No reason recorded.

### 166 — The spike's prompt is a first version
Input for task 2.4, not approved text. No reason recorded.

**Ron's decisions of 2026-10-05: the model decides the area, reporting a wrong classification,
and tasks 2.2 and 2.3.**

### 167 — The model decides the area
**A change of direction. Supersedes #84, #85, #87, #133, #134, #135, #136 and #158, and the parts
of #86, #110 and #111 described below.** The model returns the areas itself: municipal numbers
from the 71-entry list (#81), which is given in its instructions. `areas` moves into the model's
response (`ListingExtraction`) and is still stored on `Listing` as approved (`list[int]`, the colour
derived from its length, #110). `streets` and `stated_area_names` stay, as written, for the card
and for error analysis; the check that drops a name not found in the post's text stays (#162). The
area rules of #88, #112 and #124 become instructions to the model: a stated area decides; a street
only refines inside it; several possible areas are all returned; nothing the model can place
returns no area. The translation table's rows (#86) become examples in the instructions, not a
table in code.
*Why (Ron):* deterministic matching will keep failing on how posters write, where a person or a
model understands at once; the model never touches the source text, so a wrong area is visible
beside the original text and can be counted and corrected.

### 168 — What leaves phase 2 with #167
The OSM street table, the corrections file, the alias file, the derivation script, the three
downloads, `osmium` / `shapely` / `pyproj`, the completeness check, the lookup key, the
prefix-letter rule, the hyphen step and the unmatched share. **Invariant 8 returns to its
original wording:** normalized text exists only to compute a hash (the lookup-key widening of #135
is withdrawn). Why: #167's.

### 169 — A street table as an aid, recorded for later
Only if the regression set shows the model is weak on posts that give a street and no area.
`BACKLOG.md`, Future. No reason recorded.

### 170 — Known limit: a post with only a street
Its area rests on what the model knows of Tel Aviv. Measured by the regression set's 95% bar on
`areas` (#142). No reason recorded.

### 171 — The labelling page: areas picked from the 71
Ron picks the areas from the 71 (multi-select, searchable) instead of only writing names
(`PHASE_2.md` 2.6). No reason recorded.

### 172 — Reporting a wrong classification, phase 2
In the review report (`PHASE_2.md` 2.7), the corrections export also yields a count of errors per
field, so weak fields are visible, and every corrected post joins the regression set. Ron's
requirement; no further reason recorded.

### 173 — Reporting a wrong classification, phase 3 (Gate C and the UI design)
A "wrong classification" action on a card, naming the field. The post moves to the rejected list
for everyone, with its own reason. The admin sees the reports grouped by field, corrects by hand
and restores, or leaves the post out. A correction is stored apart from the model's answer, so the
card shows the corrected value and the model's answer stays for error analysis. It needs a new
rejection reason and a corrections record: their schema is settled at Gate C. Ron's requirement;
no code now.
*Why (Ron, 2026-10-05):* he wants the errors collected by type, to learn how to improve the work with the model.
*(Reason added 2026-10-10, from Ron; it was not recorded here before.)*

*Refined by #254–#256 (2026-10-10): fields from a list and a note; retention; corrections admin only.*

### 174 — Task 2.2: the plan approved, with Ron's answers
1. The method names `save_classification`, `get_listing` and `find_pending_canonicals`: approved.
2. **The layout: option C.** The `listings` table has its own layout row (`store.listings`) and is
   created when absent. Layout 1 is untouched, #65 stands, and there is no migration command and
   no manual step. *Why (Ron):* no extra steps, on the laptop or on the server.
3. Reading version-1 lifecycle records as version 2 in memory: approved.
4. The proposed validators (prices above 0, `areas` sorted with no repeats, phone names in the
   stored phone format): approved.
5. #89 is built in dedup in this task.
6. `ListingStub` is replaced in steps: `classify/` in task 2.4; `policy/` and `notify/` in phases 3
   and 4.
7. No migration runs on the real store: the new code opens the existing store and leaves its posts
   and records untouched, with a test on a layout-1 file.

No reason recorded except for point 2.

### 175 — Task 2.3, reduced
`reference/areas.yaml` (the 71 entries from the layer-511 fixture, names verbatim, the five display
labels of #119, a source block) and one module, `tlv_hunter/areas/reference.py`, the only reader of
`reference/`. `PHASE_1.md`'s YAML anchor is reworded to allow it. Nothing else from the plan of
2026-10-05 (superseded by #167). No reason recorded.

**Ron's review of tasks 2.2 and 2.3, and the regression set's location fields, 2026-10-05.**

### 176 — The code of tasks 2.2 and 2.3 is accepted
As built and committed, including the deviation that reads version-1 lifecycle records through
`PostLifecycle.from_stored_json` instead of a before-validator (`PHASE_2.md` 2.2). No reason
recorded.

### 177 — The regression set labels `areas` blind; streets and area names are not compared
`areas` is the only location field labelled blind: Ron picks from the 71 (#171). Streets and area
names as written are not labelled blind and are not compared. They are shown in the review report
(`PHASE_2.md` 2.7), where Ron marks one wrong if it is. **Amends #142** (streets and area names
leave the "every other field at least 90%" bar) **and #143** (no controls for them on the
labelling page). **Closes `PHASE_2.md` §4's open point** on how streets and area names would be
compared. No reason recorded.

**Ron's answers to the plans for tasks 2.4 and 2.5, 2026-10-05.**

Approved by Ron, 2026-10-05: the 14 points of `PHASE_2.md` §4.

### 178 — The classifier's instructions, version 1
The text proposed in `docs/INSTRUCTIONS_V1_DRAFT.md` is approved with all 11 "proposed" rows kept,
plus two additions:
1. **A two-digit year is 20YY** ("1.11.26" is 2026).
2. **A landmark can place the apartment.** A well-known landmark that places the apartment
   ("ליד שוק הכרמל", "מול קניון רמת אביב") decides the area when the post gives no area name and no
   street. A landmark on a border returns every area it touches. A general distance phrase
   ("5 minutes from the sea") still places nothing. `stated_area_names` is unchanged: a landmark
   is still not an area name. **Extends #88** (as instructions to the model, #167).

The text enters the package as `tlv_hunter/classify/instructions.txt`; the draft is deleted.
*Why (Ron), the landmark:* the model should understand a post as a person does, and a wrong area is
visible beside the original text. No other reason recorded.

### 179 — Task 2.4: the plan approved, with Ron's answers
1. The layout: `contracts/listing_extraction.py`, `postmodel/rejects.py`, `ClassificationError`;
   `classify/classifier_stub.py` deleted.
2. `openai==3.24.0`, pinned exactly, with the SDK's schema helper and a test comparing the derived
   schema with the spike's `schema_sent.json`.
3. `prompt_version` covers everything sent except the post (the instructions, the schema, the model,
   the effort, the temperature, the output limit), pinned by a fingerprint test.
4. Output limit 2,000 tokens; timeout 60 s.
5. The six completion points, as proposed:
   - the publication date is the post's own `posted_at`;
   - a tie between two years goes to the later one;
   - an impossible date is `"unclear"`;
   - a repeated phone-name pair is stored once, and a blank name is dropped;
   - a blank `other_city` reads as `None`;
   - #162's match is exact, so a name in a different case is dropped.

No reason recorded.

### 180 — #162's check also covers `other_city`
*Refined by #214 (2026-10-08): when the post has a usable `native_location`, the city is decided by it, not by the model's city.*
A city the model returns that does not appear in the post's text is dropped (read as `None`) and
counted, like a street or an area name. **Extends #162.**
*Why (Ron):* an invented city would reject a Tel Aviv post for everyone, the costliest error.

### 181 — Failure shapes never observed are tested from the documentation
A refusal, a 429, a 5xx and a timeout were not seen in the spike. Their tests rest on the
documentation and the SDK (`ASSUMPTIONS.md` O13). The first real one is captured into `data/raw/`
when it happens. No reason recorded.

### 182 — Task 2.5: the plan approved, with Ron's answers
1. **The command:** `--cap` required with no default, `--limit` optional, exit codes 0 (every post
   attempted), 1 (failed), 2 (stopped early with the store consistent).
2. **The attempts:**
   - 3 for a network error, a timeout, a 429 for rate or a 5xx, waiting 2 s then 10 s, or
     `Retry-After` when longer up to 60 s;
   - 2 for an invalid or incomplete answer; 1 for a refusal.
3. **The job also stops**, with the post not counted, on a quota or credit error, a refused key, a
   refused request (400) and an unknown model (404).
4. **The dropped names: option A.** One JSON-lines file per run, `<store_root>/classify_runs/<run_id>.jsonl`,
   one line per post written, with the dropped streets, area names and `other_city` (#180).
5. **The record is read again right before the write**; an answer for a post no longer pending is
   discarded.
6. **`jobs/common.py`** holds what both commands share. `CLAUDE.md` says: "the two job commands are
   the only code that constructs the production store".

No reason recorded.

### 183 — `other_city` stays on the labelling page, labelled blind
#177 covers streets and area names only. No reason recorded.

**Ron's review of tasks 2.4 and 2.5, 2026-10-05.**

### 184 — The code of tasks 2.4 and 2.5 is accepted
As built and committed, with the deviations listed under each plan in `PHASE_2.md` (2.4: the billed
usage on the meter's `CallRecord`, `classify_completed` beside `classify`, the setting in
`instructions.py`, the refusal to start on a fingerprint mismatch, a `not_found` kind, the current
429 codes, a year below 100 read as 20YY; 2.5: `job_logging()` and `log_failure()`, the error text
cut at 200 characters, a discarded failure not counted, `--cap` above 0, no dropped-names file when
nothing is written). No reason recorded.

### 185 — `CLAUDE.md` stays out of git, on purpose
It is listed in `.gitignore` and is not tracked. The file never said it was checked in: "checked
into the codebase" is the label Claude Code puts on the file when it loads it, which the session of
2026-10-05 read as the file's own words (`SESSION_LOG.md`). The file now says it is kept out of git.
No reason recorded.

**Ron's answers on the regression set, its runner and the review report, 2026-10-05.**

### 186 — The regression set is the 52 proposed posts
`data/labeling/regression_set.json` as proposed on 2026-10-05, with the two pre-model rejects
(`no_images`): the only mostly-English post and the only "seeking a roommate to search with".
**Closes** the backlog row on the set's required cases. No reason recorded.

### 187 — The labelling page's deviations are accepted
- `labels.json` carries `text_sha256` per post.
- The entry date is labelled as parts (`entry_date_parts`).
- The price is labelled from the text only.
- `null` means not labelled; "no area" is `[]`.
- `SqliteRepository` has a `read_only` option.
- The command lives in `jobs/`.
- `CLAUDE.md`'s reworded sentence: the job commands construct the production store for writing;
  the labelling command opens it read-only.

No reason recorded.

### 188 — Only the commands that call the model read `OPENAI_API_KEY`
**Amends #128:** the regression runner reads the key too. The key is still never logged. No reason
recorded.

### 189 — #45's post is dated 2026-09-13
The regression runner builds #45's post from `data/raw/test_posts.json` with `posted_at`
2026-09-13, the day the fixture was captured, for the year completion. No reason recorded.

### 190 — Prices are compared as a set
"3,200/3,500" and "3,500/3,200" are the same answer: the regression set compares the price's state
and its amounts as a set, not in written order. No reason recorded.

### 191 — `other_city` is compared as Tel Aviv-Yafo or not
The bar on `other_city` counts only whether the post is in Tel Aviv-Yafo or not. The city's name is
shown in the report, not compared. No reason recorded.

### 192 — Each pass of the regression set must meet the bar on its own
**Refines #142.** No reason recorded.

### 193 — The fields not labelled blind are measured from Ron's corrections in the review
The truth for a field that is not labelled blind is the reviewed classification with Ron's
corrections (`PHASE_2.md` 2.7): a field Ron did not correct counts as right. **Refines #142.** No
reason recorded.

### 194 — The regression runner's cap is $0.10
No reason recorded.

### 195 — Task 2.7: the plan approved
- A "reviewed" mark per post.
- Two more filters: in the regression set, and not reviewed yet.
- The shape of `corrections.json`: `format_version` 1, `exported_at`, and per `listing_id`:
  `text_sha256`, the reviewed classification's `prompt_version`, `model_name` and `classified_at`,
  `reviewed`, `fields` (each corrected field's right value, in `Listing`'s shape), and `note`.
- **A corrected post joins the regression set automatically,** with the corrected classification
  as its truth.

No reason recorded.

**Ron's decisions on the labels, 2026-10-06.** Ron labelled all 52 posts
(`data/labeling/labels.json`, exported 2026-10-05T20:15Z); the review chat read every label against
its post. Ron will not relabel, and his file stays untouched.

### 196 — Changes on top of `labels.json`, in a separate file
The changes below live in `data/labeling/label_overrides.json`. The regression runner applies them
on top of `labels.json` and lists them in every run report. Each entry carries its reason, and the
file names the SHA-256 of the `labels.json` it was reviewed against.
1. **A post labelled `seeking`, `for_sale`, `not_listing` or `sublet_offer` is compared on
   `post_nature` only.** *Why (Ron):* nothing else matters on such a post.
2. **Removed from the set,** by position in `regression_set.json`: 6, 10, 27, 31, 43, 49. The set
   is 46 posts. No reason recorded.
3. **Label corrections**, each because the post's text is unambiguous:
   - 5: price [2900]; 16: price [9000];
   - 12, 22, 42, 44: entry date not written;
   - 51: entry date day 31, month 10; 17: day 1, month 9;
   - 26: entry date unclear;
   - 35, 39, 50: `other_city` null; 50: areas [68, 69].
4. **Fields not compared:** `areas` on 35 and 39; `price` on 44. No reason recorded.
5. Apart from 1 and 4, a blank deciding field still stops the runner.

*The file's name and shape were proposed by Claude on 2026-10-06 (`PHASE_2.md` 2.6) and wait for
Ron's confirmation; the run of 2026-10-06 used them.*

**Ron's decisions after the failed regression run, 2026-10-06.**

### 197 — `label_overrides.json` and the runner's deviations are accepted
The overrides file's name and shape (#196), and the deviations of the runner and of 2.7: the `truth`
field of a set entry; `--cap` defaulting to $0.10; the entry date held to the 90% bar; exit code 0
whatever the verdict; a stale correction stops the review command; numbers typed on the review
page. No reason recorded.

### 198 — Areas are measured by reach, not by exact match
**Amends #142.** A post passes on `areas` when the model's areas and the label's share at least one
number, or both are empty. An empty answer against a labelled area is an error, and so is an area
against an empty label. The bar is 90%. Still reported, as information and not as a bar: the
exact-match rate, and the average number of areas returned per post, so an answer that lists too
many areas is visible.
*Why (Ron):* in a filter a wrong area hides an apartment, while an extra area only adds an orange
post. The 71 areas are finer than a post's text can settle; several of Ron's own labels were
uncertain.

### 199 — More label changes, on top of `labels.json`
**Extends #196**, each because the post's text is unambiguous (read by the review chat): position
15, entry date not written; position 32, apartment kind whole apartment; position 16, entry date
unclear (the entry depends on a pending permit). Not compared: `price` on 45 (a typo in the post).
No reason recorded beyond the text.

### 200 — The instructions, version 2
Five sentences added, nothing else:
1. Areas lean towards more, not fewer: a street, a corner, a square or a landmark that may lie in
   more than one area, or near the border between areas, gives every area it could be in; one area
   only when the post names it or the place clearly lies inside it.
2. A general phrase ("מרכז תל אביב", "מרכז העיר") beside a precise street or square: the areas of
   the precise place as well.
3. Feminine wording about the roommates who stay ("נשארות שתי שותפות") is not a restriction; only
   wording about the person wanted counts.
4. A date followed by "flexible" ("10.10 גמיש") is the date, written; "flexible" with no date
   stays unclear.
5. An entry that depends on an event with no date (a permit, the end of a renovation) is unclear.

`PROMPT_VERSION` and `PROMPT_FINGERPRINT` change with them (#179). Which streets divide the Old
North's two parts: no sentence; the first one covers it. **Refines #88, #178 and #96.** No reason
recorded.

### 201 — The reasoning effort is an option of a regression run
The regression runner takes `--effort none|low`. The production setting stays `none`, temperature
0 (#157), until Ron decides. At `low` the request carries no temperature (`ASSUMPTIONS.md` O4). The
classifier's fingerprint check pins everything else: the text, the schema, the model and the
output limit. A run records the effort and its own full fingerprint. No reason recorded.

**Ron's decisions after the two regression runs of version 2, 2026-10-06.**

### 202 — The setting stays effort `none`, temperature 0
Confirms #157. *Why (Ron):* `low` cost twice as much, was slower, and did not fix `areas`
(`SESSION_LOG.md`, 2026-10-06).

### 203 — The map check: seven places against layer 511 (a lead)
Done by the review chat, one point query per place against the municipality's layer 511. The
coordinates were its approximations, so the results are a lead, re-derived in the next round (#205):
- 19, Dizengoff Square: 31. The label is right, the model wrong.
- 34, Rabin Square: 31. The label is right.
- 37, Dizengoff Center: 31. The label is right.
- 2, Einstein St. by the Ramat Aviv mall: 10. The label is right.
- 33, Jabotinsky by Ibn Gabirol: 30. The label is right.
- 26, HaYarkon by the Royal Beach hotel: 38. The model is right, the label wrong.
- 3, Arlozorov and Henrietta Szold: 34. Both were wrong.

The pattern (Ron): the model takes "לב תל-אביב" (37) to reach Dizengoff Square and Rabin Square;
the municipality puts them in 31. The model lacks the boundaries, not the understanding.

*Re-derived 2026-10-06 (#205), from OSM coordinates and layer 511's own polygons and point queries:
19 Dizengoff Square: 31. 34 Rabin Square: 31, and 30 within 34 m. 37 Dizengoff Center: 31. 2 the Ramat
Aviv mall: 10. 26 the Royal Beach hotel: 38. 3 the Arlozorov / Henrietta Szold junction: 34, and 35
within 3 m. **33 the Jabotinsky / Ibn Gabirol junction: 34, and 30 within 1 m** (the review chat's
approximation fell on the 30 side). Everything else agrees with the lead.*

### 204 — More label changes, on top of `labels.json`
**Extends #196 and #199.** Position 26: `areas` [38]. Position 3: `areas` [34]; if the re-derived result
differs, it is used and said (position 3 is [34, 35]: the junction is 3 m from 35). Not compared: `apartment_kind` on 38 and `entry_date` on 46 (ambiguous
posts). No reason recorded beyond #203.

### 205 — Known places: a reference file, rendered into the instructions
A new file in `reference/`, read only through `areas/reference.py`:
- **Entries:** a few dozen well-known places (squares, main junctions, markets, malls, hospitals,
  stations, the port, the main beaches and hotels, campuses), spread over the areas people rent in
  (the centre, the Old and New North, Ramat Aviv, Florentin and the south, Jaffa), the seven places
  of #203 included. Each has the name as people write it, its coordinates, the source of the
  coordinates and its date, and the area number.
- **The area** comes from layer 511, by a point query or from its polygons fetched once into
  `data/raw/`. A place on a boundary lists every area it touches.
- **The coordinates** come from a stated free source, never from memory, under the
  `external-contract-verification` skill and the source's usage policy.
- **In the instructions:** the list is generated into them as known places, not typed. Rule (a) of
  version 2 (areas lean towards more) stays.
- **Ron adds entries later;** the file is in git.

The file's name and shape are proposed by Claude in the same round, as with the overrides (#196).
No reason recorded.

### 206 — The instructions, version 3: the known places, and an age preference
Version 3 adds the generated list of known places (#205) and one sentence: an age preference
("25-35") is not a gender restriction. **Refines #103, #117 and #200.** No reason recorded.

### 207 — The stop rule for the regression rounds
After this round the next step is the first run over the whole store (2.8), whatever the areas
figure is. Areas keep improving through Ron's error reports (#172, #173), not through more
regression rounds. *Why (Ron):* the 71 areas are finer than a post's text can settle (#198).

### 208 — The first run over the whole store: Ron's go, on conditions
`classify_pending --cap 1.00`, in the same round as the version 3 regression run, only if all hold:
- in that regression run `post_nature` and `other_city` have no error in both passes, and no pass
  is incomplete;
- the store's SQLite file is copied to a dated backup beside it first, and its path and SHA-256 are
  stated;
- `run_once` is not running.

If the cap or anything else stops it, report and do not rerun. After it: the counts by outcome and
by rejection reason, the cost, the failures, and the review page generated from the store. If a
condition fails, the run is not made and the report says which. Closes the gate of #164 for this
run only. No reason recorded.

**Ron's decisions after the version 3 regression run, 2026-10-06.**

### 209 — The known places file is approved
`reference/known_places.yaml`: its name and shape, the 40 m reach, and one point per place. Position
3's label [34, 35] (#204). The two typed examples in the instructions ("כיכר המדינה: 34", "שרונה: 40")
that also appear in the generated list stay as they are. Confirms #205. No reason recorded.

### 210 — Gender at 93.8% in one pass, and unstable answers between passes, are accepted for now
Tracked through Ron's review of real classifications (#172, #173), not through more regression
rounds (#207). No reason recorded.

### 211 — Version 3 runs as tested; two changes wait for the next prompt version
The instructions are not changed before the first run over the store. Waiting for the next version
(`BACKLOG.md`): a range of rooms ("2-3 rooms") is unclear; and the gender cases at regression
positions 34 and 35. No reason recorded.

*Written 2026-10-08 as version 4: #233–#237.*

### 212 — No outgoing request carries a personal identifier
A new rule (`CLAUDE.md`, invariant 15): no outgoing request ever carries a personal identifier of
Ron or of any user (an email address, a name, a phone number), in a header, a User-Agent, a URL or
a body. A tool name identifies the client. *Why:* the first fetch of the municipality's polygons on
2026-10-06 put Ron's email address in its User-Agent (`SESSION_LOG.md`).

### 213 — The first run over the store: the "no pass incomplete" condition is waived
**Amends #208.** The one failure in the version 3 regression run is a pre-model reject that
production never sends, and the stop rule (#207) makes the whole-store run the next step. Ron's go:
`run_once` not running; a dated backup of the store beside it, its path and SHA-256 stated;
`classify_pending --cap 1.00`, once; if the cap or anything else stops it, report, do not rerun and
do not raise the cap; no other paid call. After it: the counts, the cost, the reported models, the
checks from the store, the dropped names, the distribution of `areas`, and the review page. *Why
(Ron):* #207.

**Ron's review of run 2.8 and the city from Facebook's own location field, 2026-10-08.**

### 214 — The city from `native_location` decides the other-city rejection
**Amends #92 and #180 (the rule); refines BASELINE §5.** When `RawPost.native_location` is present,
its locality decides the other-city rejection; when it is absent, the model decides as before.
- **The locality** is the part before the first comma, trimmed. Never "תל אביב" matched anywhere in
  the string: the part after the comma is the district and reads "תל אביב" for Holon and Ramat Gan.
- **Tel Aviv-Yafo keys,** after the normalisation (format characters removed, whitespace collapsed,
  dash-like characters read as a space): "תל אביב יפו" and **a bare "תל אביב"**, exact match, never a
  substring. *Why (Ron):* a wrong active post stays visible and can be reported; a wrong rejection
  disappears.
- **A Tel Aviv-Yafo locality** is never rejected as `other_city`, even when the model returned one.
  **Any other locality** is rejected as `other_city`, even when the model returned null.
- **A locality with no Hebrew letters is treated as absent** (the model decides), so a provider that
  changes its language cannot hide every apartment. Each classification run logs the count of posts
  rejected by the native field.
- **Gate E order unchanged:** `other_city` first, then `post_nature`. A post rejected only by the
  native city changes reason when the model's nature was `seeking`, `for_sale` or `not_listing`
  (`7d467bbe…`, `not_listing` → `other_city`: confirmed).
- **Where it lives:** `postmodel/rejects.py`: pure code over the stored `RawPost` and `Listing`; no
  model call; the `Listing` is not edited and the `RawPost` is never written (invariant 14).
- **Recording the source: option A.** Nothing new is stored. The source and the city name to show
  are derived by `other_city_name` from the two stored records: no `Listing` or `PostLifecycle`
  schema change. The phase 3 card must call it (`BACKLOG.md`).
- **Re-derivation of the stored records:** `jobs/rederive_rejections.py`, dry run first, a backup
  before `--apply`; `--apply` only for the set of posts Ron allows (the three of the dry run).
  **It is the third command that writes the production store**, with `run_once` and
  `classify_pending`. It takes no lock, as they take none (#79 O9, #140): it must never run beside
  either. Instead it re-reads each record right before writing it and writes nothing for a record that no
  longer holds the status the plan saw.
- **Applied 2026-10-08** (Ron's OK): `2bac260c…` rejected `other_city` → active; `26e8a28b…`
  active → rejected `other_city`; `7d467bbe…` rejected `not_listing` → `other_city` (a relabel by
  Gate E's order, confirmed by Ron). Counts after: 139 active; 21 `other_city`, 19 `for_sale`, 13
  `not_listing`, 2 `seeking`. Backup `data/store/tlv_hunter.2026-10-08.backup.sqlite3`, SHA-256
  `c4e2658e…`; the store's after: `2fcc382e…`; every stored `RawPost` identical to the backup's.

*Data it rests on (read-only, the store of 2026-10-08):* `native_location` is present on 68 of 266
posts, all `sale_post` from thedoor: 65 "תל אביב - יפו, תל אביב", and one each of Holon, Ramat Gan
and Be'er Sheva.

### 215 — Ron's review of run 2.8: findings, no code change
`corrections.json`: 51 posts reviewed (39 rejected, 12 active).
- **6 price corrections,** all sale prices on `for_sale` or other-city posts. The instructions define
  the price as the monthly rent, so the model followed them. **No change.**
- **`632be5dc…`:** Ron's `other_city` "רמת החייל" is not a city correction (Ramat HaHayal is area
  71; he meant the neighbourhood). Excluded from any comparison (#216).
- **`4c5bbcaf…` (Rishon LeZion):** `stated_area_names` ["לב העיר"] on an other-city post. Next prompt
  version: no area names on an other-city post. No change now. Its correction stays a truth.
- **Ron's spot check of about 10 active posts** found no errors.

### 216 — `corrections_excluded` in `label_overrides.json`
**Amends #195.** Pairs (post, field) of Ron's review that no comparison, no error count and no
regression truth uses, each with its reason. Ron's `corrections.json` is never edited.
- `price` on `2d044201…`, `494ada70…`, `4e55319f…`, `551678f8…`, `87fc4917…`, `ac0b0cd6…`: the
  instructions define the monthly rent.
- `other_city` on `632be5dc…`: Ron meant the neighbourhood, not a city.
- `other_city` on `2bac260c…`: Ron marked it reviewed with no city correction, so the model's
  "עין ורד" would join as a truth; the field is now decided by the native-location rule (#214). The
  model's error stays visible in `BACKLOG.md`, not in the regression count.

A reviewed post with at least one correction still joins the set, an excluded one included; its
excluded fields are left out of its truth.

*Applied 2026-10-08.* `review_page` printed 5 posts joining the set (`494ada70…`, `4e55319f…`,
`551678f8…`, `632be5dc…`, `ac0b0cd6…`, positions 53–57; the set is 51 posts after #196's removals) and
the 8 pairs skipped. Three of the corrected posts were already in the set as blind labels (`2d044201…`,
`87fc4917…`, `4c5bbcaf…`): their exclusions apply and they did not join again. `2bac260c…` has no
correction on file: its pair is excluded for later. The errors per field now read `stated_area_names`
1 of 51.

**Ron's answers to the plan for task 2.9 (reclassify), 2026-10-08.** The plan is in `PHASE_2.md` 2.9;
the numbers in brackets are its "For Ron before code" points. Approved as recommended unless marked.

### 217 — Reclassify is two stages and two commands; the selection and its rules
**Refines #144.** (1) `jobs/reclassify.py` selects, calls the model (`--run`, paid) and writes the diff
report; it opens the store read-only. `jobs/apply_reclassify.py` replaces the `Listing`s Ron names,
free, after a backup, and refuses unless the report is complete. (3) `--run` needs `--limit` or
`--allow`. (4) "Not the current one" is "different from" on `prompt_version`, `schema_version` or
`model_name`, not "older". (5) A flagged post is one with `flagged_by` set: its `Listing` is replaced and
its lifecycle record is written back as it was read. (6) A change of state (`active` ↔ `rejected`, or
one reason to another) is applied like any other difference; the report lists it first and apart, with
no extra flag. The selection is a plain function over the existing Repository methods: no Repository
change. *Why (the plan):* the order "report first, then replace" becomes a boundary between two
commands, and the command that writes the store holds no key.

### 218 — No "apply all"; the run writes two list files, and `--allow-file` reads them
**Changes point 2 of the plan.** There is still no flag that applies every proposal. `apply_reclassify
--apply` takes `--allow` (id prefixes of 8 characters or more) and/or `--allow-file <path> [<path>…]`.
`reclassify --run` writes two list files into the run folder: `allow_unchanged.txt` (the posts whose
status is unchanged) and `allow_state_changes.txt` (the posts whose state or reason changes). A list
file holds one `listing_id` per line; blank lines and lines starting with `#` are ignored; an entry is
checked like an `--allow` prefix. The checks are the same for both: every entry must match a proposal
of that run, and nothing may be left over. *Why (Ron):* pasting hundreds of ids on a Windows command
line does not scale as the store grows.

### 219 — The report's place and files
(8) `<store_root>/reclassify/<run_id>/` (`data/store/reclassify/<run_id>/`), gitignored with `data/`:
`proposals.jsonl` (one line per post attempted; the old and the new `Listing`; the source of truth of
the apply, and the archive of every `Listing` it replaces), `summary.json`, `diff.html`, and the two
list files of #218. New stored files, approved as invariant 1 asks (as #182 did for the dropped names).
No schema, field or filter rule changes.

### 220 — A third reader of the key and a fourth writer of the store
(9) `reclassify --run` reads `OPENAI_API_KEY`: the third command, with `classify_pending` and
`regression_run`; amends #128 and #188. `apply_reclassify` reads none. (10) `apply_reclassify --apply`
is the fourth command that writes the production store, with `run_once`, `classify_pending` and
`rederive_rejections`. It takes no lock (#140 extended): it re-reads each record before writing it,
and a post that changed since the run is not written, is listed, and the exit code is 2. Never beside
`run_once`. A lock shared by every writer is phase 5's.

### 221 — A failed reclassify, the caps, and the churn
(11) A failed reclassify leaves the old `Listing` and touches neither `classification_failures` nor
`last_classification_error` (#152); it is recorded in the report and the log only, and a post that
keeps failing is paid for again whenever Ron tries it. (12) The caps are Ron's at each run (`--cap`
has no default): proposed $0.02 for a first `--limit 10`, $0.10 for a full pass of 194. (13) A
reclassify replaces `Listing`s even where nothing needed to change, and the same prompt gives
different answers on many posts (O12): it is used for a change of prompt version, model or schema,
not to refresh. The report page says so at its top.

### 222 — `find_reviewed` also reads the `Listing`s a reclassify replaced
(7, option A) A correction in `corrections.json` names the classification it reviewed. After a
reclassify the store holds another one, and `regression_run` would refuse every reviewed set post
("the reviewed classification is not found"). `labeling/corrections.find_reviewed` also reads the old
`Listing`s kept in `reclassify/*/proposals.jsonl`; the truth of those posts stays Ron's corrected old
classification. The plan and the report mark the posts that have a reviewed correction on file. Until
phase 3's corrections record exists (#173), a card shows the new answer without Ron's correction.

**Ron's review of task 2.9, 2026-10-08.**

### 223 — The size test of the regression set counts the blind entries only
`tests/test_labeling.py::test_the_proposed_set_holds_the_spike_posts_and_about_fifty` bounds the
proposed set (45 to 55) by its entries whose `truth` is `"blind"`; a post that joins from a review
(`"review"`, #195, #216) is not counted, so it can never break the test. The spike-posts and
"for sale" assertions are unchanged. Recorded as its own decision, not a note under #216, because it
changes a test's rule and not #216's. *Why (Ron):* the review keeps adding posts to the set.

**Ron's decisions on the Phase 2 DoD, 2026-10-08.**

### 224 — DoD 5 is signed off
Ron reviewed 51 of the 194 classifications of run 2.8 (#215, #216) and accepts that as enough.
*Why (Ron):* the system does not need to be perfect, and the calibration can go on while it is used.

### 225 — DoD 4, the measured working day, moves to Phase 3
An explicit re-plan of a DoD item, not a waiver. Item 4 of `PHASE_2.md`'s DoD leaves Phase 2 and is
done in Phase 3, once a dashboard exists. Comparing the recorded costs with the OpenAI bill stays with
Ron and does not wait for Phase 3.
*Why (Ron):* on that day he can also judge how things look in the interface, not only the
classification.

**Ron's answers to the plan for task 2.10 (Gate D evidence), 2026-10-08.** The plan is in `PHASE_2.md`
2.10; the numbers in brackets are its "For Ron before code" points.

### 226 — The plan for 2.10 is approved: the rules, the page, the files, the place
Approved as recommended (#145 unchanged). (1) The pairs are two different canonical posts, both
`"active"` with a `Listing`, different stored `text_hash`; 139 posts today. (2) The phone rule lists the
pairs of numbers shared by 2–3 posts; a number shared by 4 or more posts lists only a labelled sample of 3
pairs: 24 pairs today. (3) The fields rule: both prices written and equal as sets, both `areas` non-empty
with a number in common, both `rooms` written and equal. (4) "A few days" is 72 hours on `posted_at`.
(5) Ron judges today's list; the rate is recorded as a lower bound for a 27-hour store; the same free
command runs again on a larger store. (7) The page shows the stored photos (display only, no comparison)
and the author's display name (never a rule). (8) No text-similarity figure. (9) Two new stored files,
approved as invariant 1 asks (as #182 and #219 did): `data/gate_d/candidate_pairs.html` and
`data/gate_d/pair_verdicts.json`. (10) The code is a package of plain modules, `tlv_hunter/gate_d/`, plus
`jobs/gate_d_pairs.py`, tested and kept. No Repository, `SCHEMA.md`, contract or dependency change. The
command decides no Gate D key and no dedup B rule, marks no post a duplicate, writes nothing to the store.

### 227 — Four verdicts; what counts as a rewritten repost; the threshold
**Amends point 3 of the plan (the verdicts) and settles its point 6.** (6) A: dedup B is "common" at 5% or
more of the active canonicals (7 pairs of 139 or more), fixed before the judging. Ron judges each pair
with one of **four verdicts**, stored as:
- `same_listing`: the same offer posted again with other text (a rewritten repost);
- `same_apartment_other_listing`: the same flat but another offer, for example two different rooms of
  one shared flat;
- `different`;
- `not_sure`.

Only `same_listing` counts as a rewritten repost, for the rate and for the threshold. `--measure` reports
`same_apartment_other_listing` as its own line, and per signal too. `not_sure` counts as `different` for
the threshold, with the upper figure (`not_sure` read as `same_listing`) printed beside it.
*Why (Ron):* 9 of the 13 phone pairs have different prices, and two rooms of one flat must not be read as a
repost that dedup B would merge. The stored value names are those above, as Ron wrote them in his answer.

### 228 — Assumption I3 is re-planned to Phase 3 with DoD 4
**Extends #225.** `ASSUMPTIONS.md` I3 (the model's cost is small) is re-planned to Phase 3, together with
DoD 4: it is the same measurement. `PHASE_2.md` §3 closes I3 on that basis (DoD 6 reads "explicitly
re-planned").

**Ron's verdicts on the candidate pairs, 2026-10-08.** From `gate_d_pairs --measure` over
`data/gate_d/pair_verdicts.json` (exported 2026-10-08 13:46 UTC, rules version 1).

### 229 — Gate D's evidence: the measurement, and Ron's reading of it
**The measurement** (the command's own lines): 24 of 24 listed pairs judged: `same_listing` 10,
`same_apartment_other_listing` 0, `different` 14, `not_sure` 0. **10 / 139 = 7.2%** of the active
canonicals (the same figure with `not_sure` read as `same_listing`, there being none); 20 of the 139
(14.4%) are in at least one `same_listing` pair. The threshold of #227 is 5%, 7 pairs of 139: reached.
For scale, dedup A's exact-hash duplicates are 39 of 266 stored posts (14.7%).

| Signal | Judged | `same_listing` | `same_apartment_other_listing` | `different` | `not_sure` | Share `same_listing` |
|---|---|---|---|---|---|---|
| fields and phone | 2 | 2 | 0 | 0 | 0 | 100% |
| fields only | 8 | 3 | 0 | 5 | 0 | 37.5% |
| phone only | 11 | 4 | 0 | 7 | 0 | 36.4% |
| agent-number sample | 3 | 1 | 0 | 2 | 0 | 33.3% |

**Ron's reading.** By #227's definition rewritten reposts are **common**, and the 7.2% is a **lower
bound**: the store spans 27 hours, and the rules miss a repost with a changed price and no shared number,
and a post missing a price, rooms or an area. **No single signal is reliable enough to merge on:** a wrong
merge hides a real apartment, which is worse than a missed one. His notes on the pairs confirm that a
shared phone is often one agent with different apartments (six of the pairs he judged `different`, with a
note saying so: four found by the phone rule and the agent-number sample's two).

**Gate D is not decided.** No key, no dedup B rule and no merge is chosen or proposed here; nothing is
marked a duplicate. What dedup B would be built on is open, for Ron.

**Ron's decision on the Gate D key, 2026-10-08**, after #229 and the photo measurement of
`SESSION_LOG.md` (2026-10-08, "do the pairs share a photo?").

### 230 — Gate D's key: when two posts are the same listing
**Settles Gate D** (`SCHEMA.md`'s Gate D row, #145; answers #75 C, "the phone as a candidate signal for
dedup B"). Two posts with different text hashes are **the same listing** when, **within the 72-hour window
and among the posts the 2.10 rules compare** (canonical, `"active"`, with a `Listing`; #226), **either**:
1. they **share a phone and the fields rule matches** (price sets equal, rooms equal, an area in common)
   (*2026-10-08, #232: the shared phone is not an agent number*); or
2. they **hold a byte-identical photo** (SHA-256 of the stored file) **and at least one of the two rules
   matches**: a shared phone that is not an agent number (a number found in four or more of the compared
   posts), or the fields rule.

**Nothing else merges.** A shared phone alone, the fields alone, or an identical photo alone never merges.
*Why (Ron):* a wrong merge hides a real apartment and is worse than a missed one; on the 24 judged pairs
(#229) this key finds 4 of the 10 rewritten reposts (`same_listing`) and none of the 14 different pairs; it
needs no new dependency. It rests on a small sample of one day, so the key is strict on purpose.

**What this does not decide:** how a merge is written, where dedup B runs, any stored field, the undo. They
are in `PHASE_2.md` 2.10, "Plan for dedup B", which waits for Ron. The key itself is changed only by Ron.

**Recorded for later, not planned** (`BACKLOG.md`, "Future"): comparing re-encoded photos (perceptual
hashing) to find the other rewritten reposts. Ron decides after he has used the dashboard. No dependency is
added for it.

*Amended 2026-10-08 by #232: rule 1's "share a phone" does not include an agent number. Its use moved to
Phase 3 by #231.*

**Ron's decisions on the plan for dedup B, 2026-10-08.** The plan is in `PHASE_2.md` 2.10; it is not built
(#231).

### 231 — Dedup B is not a store-writing command: "the same listing" is derived, and its use moves to Phase 3
**Amends #145** ("dedup B is built in phase 2": the key is settled in Phase 2, its use moves to Phase 3).
The Gate D key stays decided (#230, as amended by #232). Whether two posts are the same listing is
**derived** from the stored posts by the key, **when it is needed** (the dashboard's lists and cards in
Phase 3, the alerts in Phase 4), and is **not written onto any post**. So:
- no fifth store writer (`jobs/dedup_b.py` is not built), no demoted canonical, no merge log, no undo;
- no change to #75 (a stored canonical never changes; stored groups are never merged), to `is_canonical`
  or `duplicate_of`, or to any stored record or `SCHEMA.md` field;
- how it is computed and shown is **planned with Phase 3**, not designed now.

*Why (Ron):* it is rare today (4 merges among 139 active posts), and building it now would stretch the work
for little gain. *Recommended by the reviewing chat and accepted by Ron:* the key rests on 24 pairs from one
day and will probably change, and a derived result follows a key change at once, as the rejection reason
(#92) and the other-city name (#214, option A) already do.

**Open, for Phase 3's planning, not measured:** whether deriving it stays fast enough as the store grows.

`PHASE_2.md`'s "Plan for dedup B" is kept for the record and marked not built; its findings on #75, on the
repointing of duplicates and on the agent-number rule are input for Phase 3. Its 17 points are void.

### 232 — The key, rule 1: "share a phone" does not include an agent number
**Amends #230's rule 1**, which now reads: they share a phone **that is not an agent number** and the fields
rule matches. An agent number is a number found in four or more of the compared posts, as in rule 2.
*Why (the assistant's, accepted by Ron):* two identical flats from one agent are the likeliest wrong merge.
**It changes no result on today's store:** no pair of the compared posts meets the fields rule and shares an
agent number (the 4 pairs the key finds are the same as before, read-only, 2026-10-08).

**Ron's wording for the instructions, version 4, 2026-10-08.** Five changes to `classify/instructions.txt`,
in Ron's approved wording, applied as given (`PROMPT_VERSION` "4", `PROMPT_FINGERPRINT` `0ad0bb4b…`, #179).
Nothing else in the file changed. No schema, field or filter rule changes. One decision per change; Ron gave no
reasons beyond those written here.

### 233 — Version 4: a range of rooms is "unclear"
The rooms paragraph ends with: *A range of rooms ("2-3 חדרים") is "unclear".* This is Ron's ruling of
2026-10-06 (the row "For the next prompt version" of `BACKLOG.md`, #211), now written. **Refines #211.**
No reason recorded.

### 234 — Version 4: a malformed amount is "unclear"
The price paragraph ends with: *An amount whose digits are malformed ("7,2000") is "unclear"; never repair
it.* This is Ron's ruling of 2026-10-08 (the `BACKLOG.md` row, #211). **No code changes with it:** #114
already keeps an unclear text price unclear when a native price exists. **Refines #211.** No reason recorded.

### 235 — Version 4: no area names when the apartment is in another city
The stated_area_names paragraph ends with: *When the apartment is in another city, return [].* From Ron's
review (`corrections.json`, post `4c5bbcaf…`). **Refines #211.** No reason recorded.

### 236 — Version 4: an area named only as nearby is not a stated area name
The stated_area_names paragraph, after the landmark sentence: *An area named only as nearby or within walking
distance ("במרחק הליכה מפלורנטין") is not a stated area name and does not decide the areas.* **Replaces the
`BACKLOG.md` row** "the streets extracted are wrong in both posts of the pair `d269d280…` / `e81273e6…`".
Facts only, from a read-only reading of the store by the reviewing chat (and read again on 2026-10-08):
- the stored streets are `["הרצל"]` and `["קורדוברו"]`, as written in the posts;
- what is wrong is that `d269d280…` returned `stated_area_names` `["פלורנטין"]` and `areas` `[52]` from
  "במרחק הליכה מפלורנטין".

No interpretation of Ron's note in `pair_verdicts.json` is recorded here. No reason recorded.

### 237 — Version 4: the gender paragraph
Three changes, for regression positions 34 and 35 (`BACKLOG.md`, #210, #211):
- **(a) Removed** the sentence *Feminine wording about the roommates who stay (נשארות שתי שותפות) is not a
  restriction; only wording about the person wanted counts.*
- **(b) At the head of the paragraph:** *Decide gender only from the words about the person wanted. Words about
  the people who already live in the flat or stay in it ("נשארות שתי שותפות", "יש שני שותפים ושותפה") say
  nothing about it.*
- **(c) After the sentence on wording for both (שותף/ה):** *A preference worded for both sexes ("עדיפות
  לדיירות/ים") is "no_restriction"; "women_preferred" needs a preference for women alone.*

*Why (Ron), for (a) and (b):* a wrong "women_only" hides the post from him. If position 35 stays unstable after
version 4, it is accepted as in #210 and looked at again in Phase 3. **Refines #206, #210 and #211.**

**Ron's decisions after the version 4 regression run (run `47e96cac0e8d`, `data/labeling/runs/v4-none-0ad0bb4b-47e96cac0e8d`), 2026-10-08.**

### 238 — Version 4 is accepted although both passes of the run are marked "fail"
*The reviewing chat's recommendation, accepted by Ron:* every deciding field is inside its bar in both passes;
positions 24, 34, 35 and 45 behave as intended; the fails come from positions 54, 3 and 56, whose "truth" is an
uncorrected version 3 answer on fields the five sentences do not touch, and 54 and 56 are for-sale posts. Ron's
words: not a disaster. **Recorded as a fact, with no action:** #235 was not followed at position 52
(`stated_area_names` `["בלב העיר"]` in both passes); the field is not compared (#177). Closes the version 4 items
of #233–#237; the run does not change the instructions, the labels or `PROMPT_VERSION`.

### 239 — `nature_only` also applies to a post that joined the set from Ron's review
The existing rule of `label_overrides.json` (#196) applies to posts that entered the set from Ron's review as well:
on such a post only what `nature_only` already compares is compared (`post_nature`), and the filled-in rule does not
read its other fields. *Why (Ron), as given on 2026-10-06:* nothing else matters on such a post. **Built in
`labeling/` only (2026-10-08):** the natures are those of `label_overrides.json` today (`seeking`, `for_sale`,
`not_listing`, `sublet_offer`), not widened; no compared field is added; no label, override or correction file was
edited. The nature tested is that of the post's corrected classification. Refines #196 and #195.

**Ron's decisions of 2026-10-08/09, on the version 4 run.**

### 240 — A post whose truth says the apartment is in another city is compared on its nature and its city only
A post whose truth has `other_city` not null, blind-labelled or from the review, is compared on `post_nature` and
`other_city` only, and the filled-in rule does not read its other fields. *Why (Ron), as given on 2026-10-06:* on a
disqualified post nothing else matters to him. **In addition to #239**, whose natures and field do not change.
Built in `labeling/` only (2026-10-09). The rule needs `other_city` among the fields compared on the post: a city left
out by `not_compared`, or excluded from the review (#216), does not trigger it. **It affects two positions today:** 16
(`0905ca64…`, Holon) and 52 (`4c5bbcaf…`, Rishon LeZion); the other-city review posts (53 to 55) are already covered by
#239. The counted posts per field, before and after: `apartment_kind` 31 → 29, `price` 30 → 28, `gender` 32 → 30,
`entry_date` 31 → 29, `areas` 30 → 28, each field measured from the review 8 → 6; `post_nature` 51 and `other_city`
32 unchanged. Refines #196 and #195.

### 241 — Position 3, `furnished`: the right answer is "partial" (the ruling is recorded; no file carries it yet)
Ron's ruling: on the post `0555aa32…` ("ארון קיר עצום (ללא ריהוט נוסף)") the right answer for `furnished` is `partial`,
not `unclear`. *The reviewing chat's reason, accepted by Ron:* the post says what there is and what there is not.
**Not yet carried by the set.** `label_overrides.json`'s `label_changes` accept the seven deciding fields only (the
`Literal` of `overrides.py`, validated as `labels.json` is), `corrections_excluded` can only leave a field out, and the
other route is an edit to `corrections.json`, which is Ron's. Carrying it needs **a new kind of entry in
`label_overrides.json`** (for instance a changed value of a field measured from the review, with Ron's name, the date and
the reason, applied over the reviewed classification in `labeling/regression.py`), which is a change to that file's shape
and a few lines of code. Not built; it waits for Ron's go. The model answered `partial` at this position in both passes
of run `47e96cac0e8d`.

---

## Phase 3: the content of Gate C (2026-10-10)

**Ron opened Phase 3 (the dashboard) on 2026-10-10 and approved the content of Gate C below.** Field names and types
are **not** approved: they are proposed in `SCHEMA.md`, Gate C (DRAFT), and approved separately, as at Gate B. Where
an entry says "Ron approved the reviewer's recommendation", the reason given, if any, is the reviewer's, not Ron's.

### 242 — Sign-in: a username and a password, no email
A user signs in with a username they pick and a password. No email address is asked for or stored. A forgotten password
is reset by the admin. **Refines #47 and `BASELINE.md` §10.**
*Ron approved the reviewer's recommendation. The reviewer's reason:* the users are a few close friends, and there is no
mail infrastructure.

### 243 — One-time keys: no expiry, cancel by hand, a label, and who used it
A one-time key does not expire. The admin can cancel a key that has not been used, by hand. Each key has a label set at
creation, and records who used it and when. **Refines #47.**
*Ron approved the reviewer's recommendation.* No reason recorded.

### 244 — One admin, Ron, created by a command on the machine
There is one admin, Ron. His account is created by a one-time command run on the machine, not by a key.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 245 — The profile holds two search options, each with its own full set of values
One profile per user. It holds two search options, "room in a shared flat" and "empty apartment". Each option holds
its own full, separate set of values: areas, price range, women-only, rooms, floor range, sqm range (only in the
empty-apartment search, #247), broker, parking, balcony, entry date, and each category's level as in `BASELINE.md` §8.
Each option can be switched on or off. The UI offers "copy from the other option". **Refines #51** ("one profile holds
separate values for a room and for an empty apartment") **and replaces the listing-kind row of `BASELINE.md` §8.**
*Ron approved the reviewer's recommendation. The reviewer's reason:* searching alone and searching with two friends are
two different searches.

### 246 — Sublets: a switch inside each search option
Each search option has a "show sublets too" switch, off by default. A sublet post is evaluated against the values of
the option its `apartment_kind` belongs to. There is no third option and there are no sublet-specific values.
**Refines #58 and #245.**
*Ron approved the reviewer's recommendation.* No reason recorded.

### 247 — The sqm filter exists only in the empty-apartment search
**Settles the question #99 left for Gate C** (which size a room search filters on): in a room search there is no sqm
filter. Both sizes are shown on the card when written (#99, #121).
*Ron approved the reviewer's recommendation.* No reason recorded.

### 248 — The area filter shows the 71 grouped under region headings
**Settles #82's grouping.** The 71 areas are shown grouped under region headings, each with "select all in group".
What is stored is always the municipal numbers (#83); the grouping is display only. Which grouping: a proposal for Ron
(`PHASE_3.md`, "Area grouping"); no official grouping that maps to `ms_shchuna` was found (`RESEARCH.md` §16).
*Ron approved the reviewer's recommendation.* No reason recorded.

### 249 — Non-residential areas are not hidden: a separate collapsed group at the bottom
**Refines #81 and replaces the "hiding" wording** of `BACKLOG.md`'s row for #81. The non-residential entries of the 71
are not hidden from the area filter: they sit in a separate collapsed group at the bottom of it. Which entries are
non-residential: a proposal for Ron (`PHASE_3.md`, "Area grouping").
*Ron approved the reviewer's recommendation. The reviewer's reason:* a post the model placed in a hidden area could be
chosen by nobody and would never be shown.

### 250 — No orange on the area when every one of the post's areas is in the user's selection
**Generalizes #112's Gate C row.** For a given user, the area is not orange when **all** of the post's areas are in
that user's selection, whatever produced the several areas (one stated name covering several entries, a long street,
a landmark on a border). Computed per user at display time, never written on the post (invariant 12).
*Ron approved the reviewer's recommendation.* No reason recorded.

### 251 — Restore removes the report or the flag only; the state is derived, not set to active
**Changes the approved Gate E rule** ("restore … `state` returns to `"active"`"; `SCHEMA.md` Gate E, #63) **and answers
`BACKLOG.md`'s row on restore after a reclassify.** **One rule for a reported post and for a post flagged "lied"**
(#282): restore removes the report or the flag only. The post's state is then what it would be without it, derived
from the post's classification: `"active"`, or `"rejected"` with the derived reason. **The classification read is the
model's answer with the admin's corrections in force applied** (#281). A restored archived post stays archived, its
reason re-derived (#283). The amended rule is proposed in `SCHEMA.md` Gate E, next to the approved text, until Ron
approves the names.
*Amended 2026-10-10 (round 2): first recorded for a reported post only, derived from the model's answer; #281 and #282
widen it.*
*Ron approved the reviewer's recommendation.* No reason recorded.

### 252 — A `no_images` post that comes back with different text and media is a new post
**Settles #72.7** (#70 under dedup B; deferred to Gate D, then left for Phase 3 by #230). A post rejected as `no_images`
that comes back with different text and media is a new post, classified and shown as usual. Nothing is built to tie it
to the old one. The Gate D key (#230, #232) is not widened.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 253 — Viewed: opening the card marks it viewed
**Settles the trigger #62 left for the Phase 3 UI design.** Opening the card marks it viewed for that user; scrolling
past does not. An open card has "mark as not viewed". A card stays viewed when a further publication is grouped into it
by the Gate D key (#231).
*Ron approved the reviewer's recommendation.* No reason recorded.

### 254 — The "wrong classification" report: one or more fields from a list, and an optional note
**Refines #173.** The reporter picks one or more fields from a list, plus an optional free note. The rest of #173
stands: the post moves to the rejected list for everyone with its own reason, and the admin sees the reports grouped by
field, corrects by hand and restores, or leaves the post out.
*Why (Ron, 2026-10-05, #173):* he wants the errors collected by type, to learn how to improve the work with the model.

### 255 — Retention of a reported post; the report and the correction are always kept
While a post is reported as wrongly classified it is exempt from deletion, like a post flagged "lied". Once corrected
and restored it follows normal retention. The report and the correction record (the field, the model's value, the
corrected value) are always kept. **Extends #46 and #63's flagged-post rule; changes invariant 3's wording
(`CLAUDE.md`).**
*Ron approved the reviewer's recommendation.* No reason recorded.

### 256 — Corrections: admin only; they override the model's answer until removed
Only the admin corrects. A correction overrides the model's answer, also after a later reclassify, until the admin
removes it; the model's answer is kept beside it. The card shows a "corrected by hand" mark on the field. **Refines
#173; amends #144's "the new `Listing` replaces the old"** for a corrected field: the new `Listing` is still stored,
and the correction still applies over it. The `Listing` itself is never edited.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 257 — The dashboard gets a polished UI in Phase 3, not in Phase 6
**A scope change to `BASELINE.md` §12.** The dashboard's polished UI is built in Phase 3, not in Phase 6 ("UI polish
from Ron's screenshots" leaves Phase 6). Ron will have the assistant build it with his design skills when the UI task is
reached. Ron's approved card content, field states and colour rules (`BASELINE.md` §6–§8) stay binding; the visual
design is the UI task's. Nothing of it is built in the round that recorded this.
*Ron's own request. Why (Ron):* he has design skills that produced a UI he is happy with on his event-seeker project,
and he wants this UI built the same way.
*(Corrected 2026-10-10: first recorded as the reviewer's recommendation, with no reason.)*

---

## Phase 3: Ron's answers on the first docs round (2026-10-10)

**Ron decided the points below on 2026-10-10, after reviewing the first Phase 3 docs round with the reviewer.** Names
and types stay a draft (`SCHEMA.md`, Gate C) until Ron approves them. Where a point asked the assistant to propose a
detail, the proposal is in `SCHEMA.md` or `PHASE_3.md` and is not part of the decision.

**The technical choices (`PHASE_3.md` §5).**

### 258 — The dashboard framework: React and TypeScript with Vite, served by FastAPI
Option A of `PHASE_3.md` §5.1: React + TypeScript built with Vite, hand-written CSS, Hebrew fonts through `@fontsource`;
FastAPI + uvicorn serve the API and the static build; one Docker image, two-stage build. Node is on Ron's laptop from
event-seeker (checked 2026-10-10: `node` v24.11.1, `npm` 11.6.2) and is reused; `node_modules` are never copied between
projects. Nothing is installed until a task's plan is approved. **Settles the "Dashboard framework" choice of `BACKLOG.md`
(#23).**
*Ron approved the reviewer's recommendation.* No reason recorded.

### 259 — SQLite journal mode: the rollback journal with an explicit busy timeout in Phase 3
**Settles #65's open choice for Phase 3.** The default rollback journal stays; every connection sets an explicit busy
timeout. WAL is reconsidered in Phase 5 if waits are seen on the measured working day (DoD 4).
*Ron approved the reviewer's recommendation.* No reason recorded.

### 260 — Every writer of `PostLifecycle` writes by compare and set; #140 no longer covers the site
Option 1 of `PHASE_3.md` §5.3. `save_lifecycle` (and the lifecycle half of `save_classification`) writes only if the
stored record is still the one the writer read, checked inside the write's transaction; otherwise it refuses. This
applies to every writer: the job commands and the site. **#140's "never at the same time" no longer covers the site**,
which runs beside the jobs; it still holds among the job commands. **Amends #65** (last write wins), **#140** and **#220**.
*Ron approved the reviewer's recommendation.* No reason recorded.

**The area grouping (`PHASE_3.md` §6).**

### 261 — The area filter's groups, and the non-residential group
**Settles #248 and #249's lists.** The seven region groups of `PHASE_3.md` §6, with Hebrew headings, as proposed, and the
four entries left undecided placed in regular groups: 40 in the city centre, 29 in the North, 1 and 3 in "North of the
Yarkon, west". The non-residential group, collapsed at the bottom: 11, 12, 13, 28, 51, 55, 66. Display only; the stored
values stay the municipal numbers (#83). The grouping is the assistant's, not a municipal division (`RESEARCH.md` §16).
*Ron approved the reviewer's recommendation. The reviewer's reason, for the four:* when in doubt, a regular group, so
"select all in group" does not miss a post.

**Gate C's open points (`SCHEMA.md`, Gate C, round 1's list; the number in brackets is the point's).**

### 262 — Accounts: an opaque id, the username's rules, Argon2id, the admin's reset (points 1–5)
(1) `user_id` is random and opaque, separate from the username. (2) A username is Latin letters, digits, `_`, `.` and `-`
only, 3 to 32 characters, unique case-insensitively. (3) A username cannot be changed in this version. (4) Passwords are
hashed with Argon2id; the minimum password length is 8. (5) A reset: the admin sets a temporary password, which must be
changed at the next sign-in. **Refines #242.**
*Ron approved the reviewer's recommendation.* No reason recorded.

### 263 — Sessions: a stored record, valid 30 days; a reset ends them all (point 6)
A session is a stored record, valid 30 days. A password reset ends every existing session of that user. The record is
proposed in `SCHEMA.md`, Gate C.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 264 — A short delay after five failed sign-ins (point 7)
After 5 failed sign-in attempts, a short delay. The details are proposed in `SCHEMA.md`, Gate C.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 265 — A user is never deleted, only disabled (point 8)
The admin can disable a user: a disabled user cannot sign in and their sessions are ended; their profile, viewed records
and reports are kept. The admin can enable the user again. The field is proposed in `SCHEMA.md`, Gate C.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 266 — A key is shown once; a cancelled key stays cancelled (point 9)
As proposed: the key is shown to the admin once, at creation, and never again; a cancelled key is not un-cancelled.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 267 — The Gate C records live behind a new interface beside `state/`: an eighth seam (point 10)
As proposed: a new interface beside `state/`, in the same SQLite file. It is an eighth seam; its name and contract are
proposed in `PHASE_3.md` 3.4 for `CLAUDE.md`'s table, and wait for Ron.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 268 — A new profile: both options on, nothing set (point 11)
A new profile has both search options enabled and no values set; `include_sublets` is off and "hide women-only" is on.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 269 — Broker, parking, balcony: a fixed wanted value; the user picks only on and the level (point 12)
The wanted value is fixed: no broker, has parking, has a balcony. The user only turns the category on and picks its
level. The drafted `wanted` field is dropped.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 270 — The entry date: a range; "immediate" is the date of evaluation (point 13)
The entry-date criterion is a range, both ends optional. A post whose entry date is "immediate" compares as the date of
the evaluation, not the publication date. Which calendar date (invariant 9): proposed in `SCHEMA.md`, Gate C.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 271 — Half rooms and the basement in the ranges (point 14)
Half rooms are allowed in the rooms range; a basement (-1) can be chosen in the floor range.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 272 — "Copy from the other option" (point 15)
It copies every value, `include_sublets` included, but not `enabled`. `size_sqm` is never copied into the room option;
copying into the empty-apartment option leaves its `size_sqm` as it was.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 273 — A post whose kind is unclear or not written (point 16)
It is shown at the bottom, evaluated against every enabled option, with its kind marked.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 274 — A sublet shows only when its option is on and its switch is on (point 17)
Confirmed reading of #246.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 275 — With no areas chosen, a several-area post stays orange (point 18)
**Refines #250.**
*Ron approved the reviewer's recommendation.* No reason recorded.

### 276 — The viewed record (point 19)
`ViewedPost` holds the `listing_id` of the post the card shows; reopening the card keeps the first `viewed_at`.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 277 — The report's fields and note (point 20)
The reportable fields are the list proposed in round 1 (`SCHEMA.md`, Gate C); the note is at most 500 characters. The
Hebrew labels are the UI task's.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 278 — One report per reporter; rejected while any is open; a restore resolves all (point 21)
As proposed.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 279 — The new reason is "misclassified", last in Gate E's order; "flagged" shows when both apply (point 22)
As proposed.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 280 — A report sets `flagged_by` and `flagged_at` to the first reporter (point 23)
As proposed. So a reclassify treats a reported post as a flagged one (#217 (5)).
*Ron approved the reviewer's recommendation.* No reason recorded.

### 281 — After a correction, restore derives the state from the corrected value (point 24)
Restore derives the state from the post as corrected, not from the model's value. **Amends #251.**
*Ron approved the reviewer's recommendation.* No reason recorded.

### 282 — #251's restore rule covers a post flagged "lied" too (point 25)
One rule for both: restoring a flagged post or a reported post removes the flag or the report only and derives the
state. **Amends #251's wording** and `BASELINE.md` §5.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 283 — A restored archived post stays archived (point 26)
As proposed: its reason is re-derived.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 284 — Corrections: which fields, how stored, and their removal (points 27, 28)
As proposed: the correctable fields are the reportable list; a value is stored as the field's Gate B type and validated
as the `Listing` validates it; a removed correction is kept, marked removed.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 285 — `PostLifecycle` goes to `schema_version` 3 (point 29)
For the new rejection reason; a version-1 or version-2 record still reads.
*Ron approved the reviewer's recommendation.* No reason recorded.

### 286 — "Left out" is not final (point 30)
The admin can restore a left-out post later; meanwhile the post is kept (#255).
*Ron approved the reviewer's recommendation.* No reason recorded.

### 287 — The Gate D key compares corrected values (point 31)
The key compares the post as users see it: the `Listing` with the admin's corrections in force applied. **Refines #230
and #231.**
*Ron approved the reviewer's recommendation.* No reason recorded.

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
