# Decisions

Every decision that shapes this project, with the reasoning behind it.

**Read this before proposing to reverse something.** A decision recorded here was made against a
specific constraint; if that constraint still holds, the decision still holds. If it no longer
holds, say so explicitly and change the entry — do not quietly work around it.

Superseded decisions are kept, marked, and left in place. Deleting them would lose the fact that
the question was considered at all.

**Last updated:** 2026-10-03

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
`postsNewerThan` is a single value per run, but the watermark is per group. Resolution: one
synchronous run with all 6 URLs, `postsNewerThan = min(all watermarks) - buffer`, filtered per
group locally.

*Why:* cheaper than 6 runs (memo23 also bills per start), the watermark stays per group as
designed, dedup absorbs the wider overlap, and silent-group detection falls out for free.
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
**Extends #19.** Gate E: what the lifecycle adds to a stored post (state, rejection reason, flagger,
last publication, repost log, image paths). Gate C now also covers the user, key and profile
records.

### 60 — Yad2 stays future, and will likely need its own scraper
Not through an Apify provider. The design stays open to it.

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
