# TLV Apartment Hunter — Macro Plan

**Status:** architecture agreed, phases agreed. Phase 1 detailed separately in `PHASE_1.md`.
**Last updated:** 2026-09-13
**Owner:** Ron
**Companion document:** `HANDOFF.md` (research, verified facts, provider details, legal position)

> Written in English because it is a technical spec destined for Claude Code.
> Conversation language is Hebrew.

---

## 0. Changes since HANDOFF.md

Two decisions were changed after the handoff was written. They are recorded here because
they reshape the architecture more than they appear to.

### C1 — The deterministic sniper is out of v1

`sniper.py` and `test_sniper.py` stay in the repo, outside the execution path. The sniper becomes
a second implementation of the `Classifier` protocol, switchable on later in shadow mode without
touching the pipeline.

The three traps proven on real data (§8 of HANDOFF) remain documented and must not be undone if
the sniper is ever revived.

**Consequence:** post #18 (`אנחנו שני שותפים שמחפשים דירת 3 חדרים` → `seeking`) is no longer covered
by the sniper. It moves into the Gemini regression set. This was listed as "not blocking" in the
handoff *because* the sniper caught it — that reasoning no longer holds.

### C2 — Rich filtering moves to the dashboard; v1 pushes everything

The LLM-populated fields are no longer a v1 notification filter. They become dashboard facets
(has address / has balcony / master room / etc.). v1 is a **calibration mode**: every non-duplicate
post is pushed to Telegram carrying the reason it was classified as it was, so Ron can judge
extraction quality against real output and tune the prompt.

**This produces the central architectural principle:**

> The pipeline always classifies and stores everything.
> The policy layer decides only what to **notify** — never what to **store**.

Everything downstream follows from this:

- The dashboard is a **read-side** feature. It reads the same Firestore the pipeline writes.
  It requires zero pipeline changes.
- Adding a new extracted field is a change in three places: the pydantic model, a paragraph in the
  prompt, and a test.
- Because `raw` is preserved untouched, a **reclassification job** can re-run a new schema over all
  stored history and backfill the new field onto old posts. This job is a first-class citizen of the
  design, not an afterthought.

### C3 — Direction beyond v1 (shape only, not a plan)

Ron may eventually offer the system to a friend with different criteria — an empty apartment rather
than a room in a shared flat, or a sublet. That means per-user groups, per-user filter and ranking
rules, per-user Telegram alerts, and a simple user store. The dashboard becomes the primary
interface and Telegram becomes a targeted alerter driven by dashboard-defined ranking.

**This is not planned here, and no multi-user work happens in v1.** It is recorded because it
changes a handful of decisions that are expensive to reverse, all of which are now anchors in
`PHASE_1.md` §1.0:

- **Collection is shared; evaluation is personal.** A post is fetched, classified, and stored once
  regardless of how many users exist. What differs per user is which groups they subscribe to,
  which posts pass their filter, how those posts rank, and what reaches their bot.
- **Extraction is objective; ranking is subjective.** What a post *says* (price, area, type,
  balcony, floor) is the same for everyone and is classified once. How *good* a post is for a given
  person is a calculation over those stored fields. A per-user prompt would mean N model calls and
  N copies of history for no gain; a second user should cost zero model calls.
- **The `Listing` schema covers every listing type**, not only what Ron searches for. See Gate B.
- **Collection settings are shared, user settings are personal.** `maxPosts`, `sortingOrder`, and
  schedule frequency belong to the run; group subscriptions and filter rules belong to the user.
  The watermark stays per group and global.

### C4 — Schema approval gates

No schema, field, or filter rule is created or changed without Ron's explicit approval.
See §6. This is an invariant, recorded in `CLAUDE.md`.

---

## 1. Architecture

```
Cloud Scheduler ──> Cloud Run Job ──> Apify (sync API) ──> provider normalize ──> text normalize
   (every 30m)            │                                                              │
                          │                                                         dedup stage A
                          │                                                              │
                          │                                                           Gemini
                          │                                                              │
                          │                                                         dedup stage B
                          │                                                              │
                          │                                                           policy
                          │                                                              │
                          └──── watermark (per group) ◄──── Firestore ◄──── persist ──> Telegram
                                 advances only on success                                + daily digest
```

Pipeline order, canonical:

```
fetch → provider normalize → text normalize + phone extract → dedup A → Gemini
      → dedup B → policy → persist → notify
```

---

## 2. Modules and seams

What makes this modular is **where the seams are**, not how many files exist. Seven seams, each with
an explicit contract. If a file does not know which seam it belongs to, it is in the wrong place.

| Module | Contract | Why it is a seam |
|---|---|---|
| `providers/` | `fetch(group_ids, since) -> list[RawPost]` | A provider was already blocked mid-project. thedoor and memo23 sit behind one Protocol. |
| `classify/` | `classify(RawPost) -> Listing` | Allows reviving the sniper, swapping models, or running two classifiers in parallel for comparison. |
| `store/` | Repository — `upsert`, `find_by_hash`, `find_by_phone`, `query` | Firestore in cloud, local JSON in dev and tests. The dashboard will read through the same interface. |
| `config/` | One read interface | YAML now, datastore later when a UI edits it. "Add a group from the dashboard" becomes one implementation swap instead of ten call sites. |
| `policy/` | `decide(Listing) -> Decision` | **The module that changes most often.** Fully separated from classification and from storage. |
| `notify/` | `send(Listing, Decision)` | Channel protocol. Telegram in v1; email or dashboard later. |
| `state/` | per-group watermark, `consecutive_failures` | The one thing that must never advance on a failed run. Phase 2. |

`pipeline.py` wires these together and contains no business logic of its own.
Configuration lives in YAML behind the `config/` interface, never read directly by another module.

### Repository layout

```
tlv_hunter/
├── config/            base.py (interface) · yaml_config.py
├── contracts/         RawPost, Listing, Decision, GroupWatermark, Notification
├── parsing/           single-implementation parsers: datetime, price, listing_id
├── providers/         base.py (Protocol) · thedoor.py · memo23.py · fixture.py
├── textnorm/          hash-oriented normalization + phone extraction
├── dedup/             stage_a.py (deterministic) · stage_b.py (post-classification)
├── classify/          base.py (Protocol) · gemini.py · prompt.py · sniper.py (dormant)
├── policy/            always_notify.py + rejection-reason computation
├── store/             base.py (Repository) · local_json.py · firestore.py
├── notify/            base.py (Channel) · telegram.py · formatting.py
├── state/             watermarks, consecutive_failures
├── pipeline.py        wiring only, no logic
└── jobs/              run_once.py · bootstrap.py · digest.py · reclassify.py

config/               collection.yaml · users/<user_id>.yaml   (repo root, not in the package)
tests/                top-level; reads fixtures in place from data/raw/
data/                 gitignored — real phone numbers. Never copied into the package.
```

`jobs/reclassify.py` is written early even though it will not run for a while. It is the insurance
policy on every future field.

---

## 3. Two kinds of normalization

The word appears in two unrelated places in `HANDOFF.md`. They are different things.

### Provider normalization
**Location:** inside the adapter, between fetch and everything else.
**Job:** convert one provider's JSON into a uniform `RawPost`. This is where the field map from
HANDOFF §4 lives: `post_id` vs `legacyId`, `creation_time` (RFC 2822) vs `time` (ISO) — both emitted
as tz-aware UTC `datetime`. Provider quirks land here too: `post_type: "shared"` arriving with empty
`text` and real content in `sharedPost`; HTML-escaped `groupTitle`.

**This is the only line in the codebase that knows which provider the data came from.** Past it,
no module knows whether the data came from thedoor or memo23. That is what makes provider swap cheap.
`raw` is preserved untouched so reclassification can always return to the source.

### Text normalization
**Location:** between `RawPost` and dedup, and nowhere else.
**Job:** produce a string from which a hash is computed, so that two posts with identical content but
different nikud / quote marks / whitespace / emoji produce the same hash.

**Its output is single-use, for hashing only.** It is not stored, not displayed, and never sent to the
model. Gemini always receives the original text verbatim.

Because the sniper is out, this normalization can be **aggressive** with no risk. The `שותף/ה` trap
was about keyword matching, not hashing — two copies of the same post fold identically and collide
either way.

---

## 4. Dedup — before enrichment, in two stages

### Stage A — before the model, fully deterministic
1. `source_post_id` — exact repeats, chiefly the deliberate 10–15 min watermark overlap
2. **hash of normalized text** — catches the same-group pairs with different `post_id`. *The one that matters.*
3. **phone number** — regex on the text, no model needed. A one-directional signal: a shared phone
   is strong evidence of the same listing, a missing or differing one carries no information.
   Present in only ~50% of posts — see `DECISIONS.md` #26.

A stage A hit is stored as a duplicate pointing at the canonical post. **The model is never called**
and no message is sent. Saves tokens and, more importantly, saves a duplicate notification.

### Stage B — after the model
Layer 4 only: `price + rooms + street`. Requires structured fields that exist only after
classification. Catches the same apartment reposted with **rewritten text** — a hash will not catch
that, and the phone will not catch it if the poster changed. The model call is already spent here,
but at ~50 posts/day that is fractions of a cent, and the duplicate message is avoided.

### Two things that are easy to miss
- Dedup must compare **against DB history and within the current batch**. Both same-group duplicates
  in the sample appeared in the same window; a DB-only check would have missed them.
- The `Notification` entity is a **third and separate** safety net: even if every dedup layer misses,
  checking "have I already sent this `listing_id`" prevents a duplicate message. This is why it was
  separated from post dedup in the original design.

---

## 5. Tech stack

| Choice | Rationale |
|---|---|
| **Python 3.12 · pydantic v2 · uv · ruff · pytest** | pydantic is already the core of `schema.py`. **The Gemini response schema is derived from the model at runtime** — never maintain two sources of truth for the schema. |
| **Cloud Run Job + Cloud Scheduler** | A job, not a service. No endpoint, no webhook, nothing to keep alive. 48 runs/day of a few seconds each fit the free tier comfortably. |
| **Firestore (native mode)** | As decided in HANDOFF §5. |
| **`httpx` directly against Apify and Telegram** | Not `python-telegram-bot` — that is a library for bots that **listen**. Push-only v1 is `sendMessage` and `sendMediaGroup`: two HTTP calls, no event loop, no dependency that drags you toward a webhook prematurely. |
| **`google-genai` SDK** | Structured output, `temperature=0`. |
| **Secret Manager** | Apify, Telegram, Gemini tokens. |
| **Cloud Build + Artifact Registry** | Image build and storage. |
| **`gcloud` in a Makefile for v1** | Terraform is more overhead than it is worth for one job and one scheduler. Add it when it justifies itself. |
| **JSON logs to Cloud Logging** | `run_id` on every line. |

### Apify call shape — resolved design point

`postsNewerThan` is a **single value per run**, but the watermark is **per group**. These conflict.

**Decision:** one run with all 6 URLs, `postsNewerThan = min(all watermarks) - buffer`, then filter
per group locally. The watermark stays per group as designed, the overlap simply grows a little, and
dedup absorbs it. Cheaper than 6 separate runs (memo23 also bills $0.008 per start). Bonus:
"group returned nothing" detection falls out of this for free.

`maxPosts = 30` per group gives headroom against the measured ~8/day.

**This behaviour is `ASSUMED`, not `VERIFIED`** — it is verified first in Phase 1, task 1.1a.

### Expected cost
~1,500 posts/month ≈ $2.25 Apify · Gemini Flash negligible · Firestore and Cloud Run within free tier.

---

## 6. Schema approval gates

**Invariant: no schema, field, or filter rule is created or modified without Ron's explicit approval.**
Recorded in `CLAUDE.md` so Claude Code does not invent fields on its own initiative.

Each gate is a task with its own DoD: *field table presented → Ron approved → table copied into
`SCHEMA.md` with a date*. `SCHEMA.md` is the source of truth for approved schemas.

| Gate | Before | What gets settled |
|---|---|---|
| **A** | task 1.1 | `RawPost` schema: fields at the provider boundary, what goes into `raw` vs a first-class field, `media[]` shape, `native_price` / `price_source` |
| **B** | task 1.4 | `Listing` schema — **the heavy gate**. The full field list the model will populate, including fields with no v1 use that will be dashboard facets later (balcony, master room, floor, elevator, furnished, has-address…). Types, allowed values, and which fields may be `null`. |
| **C** | task 1.5 | Filter rules. **Primary filter**: hard conditions (price, areas, `listing_type`) and what counts as a failure. **Secondary filter**: which `missing_field` is critical vs unimportant, and the display order of reasons. |
| **D** | task 1.6 | Dedup B key: which fields compose `price + rooms + street`, and behaviour when one is `null` |
| **Future** | Phase 6 | New faceting fields, and **before any `reclassify` run** |

Gate B is where most of the discussion time should go. Every field not defined there will require a
`reclassify` over all history later.

Gate C is deliberately separate from Gate B: filtering lives in `policy` and changes without touching
the schema. That separation is exactly what lets Ron calibrate without reclassifying.

---

## 7. Phases

| Phase | Contents | Done means |
|---|---|---|
| **0** | Repo skeleton, config, contracts, local store. No cloud. | The raw 20-post file passes end-to-end offline and round-trips out of the store |
| **1** | thedoor adapter + normalize + dedup + Gemini + Telegram. Bootstrap mode. Manual runs. | A real message about a real apartment lands in a private channel |
| **2** | Firestore + watermark + idempotency | Two consecutive runs never send the same post twice |
| **3** | Container, Cloud Run Job, Scheduler every 30m, Secret Manager | Runs two days straight with no intervention |
| **4** | Daily digest, run metrics, silent-group detection, `price_mismatch` | Silence and failure no longer look the same |
| **5** | memo23 adapter + failover, reclassify job | Killing the primary provider on purpose does not stop the system |
| **6+** | Dashboard, image re-hosting, comments | — |

Phases 0–2 run entirely locally. Real Telegram alerts arrive **before** GCP is touched — which is
also why putting `store` behind an interface pays off on day one.

### Phase 0 — skeleton and contracts
**Goal:** that everything afterwards drops into a shape that already exists.
**Build:** pydantic contracts, `store/local_json.py`, `pipeline.py` wired end-to-end with stubs,
YAML config behind an interface, `uv` + `ruff` + `pytest`.
**Verifies:** that the 20 real posts actually fit the schema. If any field cannot survive real data,
better to learn it here.

> **Corrected 2026-09-14.** The done-criterion originally read "`test_posts.json` passes
> end-to-end". That file holds only `{post_id, text}` for 17 posts and cannot produce a `RawPost`.
> The gate is the raw 20-post thedoor response in `data/raw/`, the only artifact with the full
> provider shape.

### Phase 1 — local end-to-end
Detailed in `PHASE_1.md`. This is the bottleneck phase: it closes three open `ASSUMED` items and
produces real value before GCP exists.

### Phase 2 — persistent state
**Build:** `store/firestore.py` behind the same Repository · per-group watermark ·
`min(watermarks) - buffer` as the single Apify input with local per-group filtering ·
`Notification` entity as the third safety net · **watermark advances only on a successful run**.
**Done:** killing a run mid-flight does not advance the watermark, and the next run picks up the
missed window.
**Verifies:** Firestore free-tier fit at real volume.

### Phase 3 — cloud
**Build:** GCP project creation · Secret Manager · Dockerfile · Cloud Build + Artifact Registry ·
Cloud Run Job · Cloud Scheduler every 30m · JSON logs with `run_id`.
**Verifies:** real Apify cost and real Gemini billing — both `UNKNOWN` in HANDOFF §9.

### Phase 4 — observability, not a nice-to-have
**Build:** daily digest (collected / deduped / classified / sent, per group) · `price_mismatch` ·
failure alert to Telegram on `consecutive_failures` · **silent-group detection**.

Silent-group detection is the hard part: thedoor returns no diagnostic rows, so a private group and
a group with no new posts look identical. Working rule — known rate is ~8 posts/group/day, i.e. one
post every ~3h. A group returning zero for **8 consecutive runs** (4h) is flagged as suspect in the
digest; **48 consecutive runs** (24h) raises an alert. This threshold is `ASSUMED` and gets calibrated
against a week of real data.

**Done:** removing a group from config on purpose produces an alert within 24 hours.

### Phase 5 — resilience
**Build:** `providers/memo23.py` · automatic failover · `jobs/reclassify.py` actually run once over
history.
**Done:** killing thedoor on purpose — the system continues on memo23, and the only difference in
messages is image resolution.
Running reclassify here is the real test of the modularity promise, before the dashboard depends on it.

### Phase 6+ — read side
Dashboard, faceting over the fields, image re-hosting to Cloud Storage, comments. Zero pipeline
changes. Gate: new field list approved before implementation, and before any reclassify run.

---

## 8. Planning method

**Semi-macro planning is done one phase ahead, not for all phases up front.**

Rationale: Phase 1 closes three `ASSUMED` items that everything else rests on. Detailed planning of
later phases now would be the same failure `HANDOFF.md` §2 warns about — building on `ASSUMED`.
It is only planning rather than code, but a detailed spec creates commitment: it is harder to throw
away a plan you wrote in detail than a row in a table.

There is also a practical point: planning resolution degrades with distance even without errors.
Phase 4 planned after a week of real messages will be far better than Phase 4 planned today.

**The one exception** is decisions that are expensive to reverse from Phase 1 — chiefly data shape.
Those are the mandatory anchors in `PHASE_1.md` §1.0. They are not forward planning; they are
avoidance of irreversible damage.

**At the end of each phase:** stop and update `HANDOFF.md` and `ASSUMPTIONS.md` — what was verified,
what turned out wrong, what changed in the plan. Only then plan the next phase. This is what makes
later planning *better* rather than merely *later*, and it continues the VERIFIED / ASSUMED / UNKNOWN
method directly.

---

## 9. Open decision points (deliberately unresolved)

| Item | Note |
|---|---|
| `new_north` boundary | Included at launch; revisit after a week of real data |
| Scheduler frequency | 30 min is an assumption. Possibly 15 in the evening, 60 at night |
| Narrowing from push-everything | Only after calibration shows where the model errs |
| Apify plan | Free tier until real monthly cost is measured |
| Comments | `thedoor/facebook-comment-scraper` if ever needed. Not v1 |
| **Yad2 as an additional source** | Recorded 2026-10-02 as a future direction, **not planned**. Ron may add Yad2 listings later, so the design must stay open to it. The `providers/` seam is the intended entry point. Known gaps to settle when it is planned: `RawPost` is Facebook-shaped (`group_id` is required, `source` accepts only `thedoor` / `memo23`); Yad2 listings are already structured, so whether they pass through the model at all is undecided; dedup across sources; and how Yad2 can be read at all, including its terms of use, is `UNKNOWN`. |
| **Legal status if a second user is added** | `HANDOFF.md` §7 records that the personal-use exclusion from the Israeli Privacy Protection Law holds **only while the project stays personal and non-commercial**, and that sharing or publishing moves it under the full law. Offering the system to a friend sits exactly on that line. Not a blocker, and not legal advice — but a decision that needs checking before a second user exists, rather than something to drift into. |

---

## 10. Continuity files

```
CLAUDE.md
docs/
├── HANDOFF.md         living document, updated at the end of each phase
├── MACRO_PLAN.md      this file
├── DECISIONS.md       the 15 decisions + what was added since, with rationale
├── ASSUMPTIONS.md     VERIFIED / ASSUMED / UNKNOWN register
├── SCHEMA.md          approved schemas only — written after an approval gate passes
├── PROVIDERS.md       field map + per-provider traps
├── PHASE_1.md         phase 1 semi-macro
└── SESSION_LOG.md     what was done each session and what the next step is
```

### `CLAUDE.md` contents
- Project purpose in one paragraph
- **The invariants** (see below)
- Run and test commands
- Code conventions
- Pointer to `docs/`
- **All git operations are Ron's, never the tool's**

### Invariants
1. No schema, field, or filter rule is created or changed without Ron's explicit approval
2. The watermark never advances on a failed run
3. Nothing is ever deleted — rejected posts are stored with the reason
4. `raw` is never trimmed
5. `pfbid` (`user.id`) is never an identity key
6. `sortingOrder` is always `newest_posts`, never `newest_activity`
7. `fetchAllComments` is always explicitly `false`
8. Normalized text is for hashing only — the model always receives the original text
