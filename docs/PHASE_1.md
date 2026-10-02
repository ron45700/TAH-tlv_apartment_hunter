# Phase 1 — Local End-to-End (semi-macro)

**Status:** in progress. Phase 0 complete (2026-09-14). Task 1.2 complete, Gate A approved.
Task 1.1a not yet run. Next buildable task: 1.3.
**Last updated:** 2026-10-02
**Owner:** Ron
**Parent:** `MACRO_PLAN.md` · **Research:** `HANDOFF.md`

> Written in English because it is a technical spec destined for Claude Code.
> Conversation language is Hebrew.

**Phase goal:** a real alert about a real apartment, sent from the laptop, with no cloud involved.

**Phase DoD:**
1. A real message from a real group lands in the private Telegram channel.
2. Two consecutive runs with a 15-minute overlap do not send the same post twice.
3. The three `ASSUMED` items listed in §2 are resolved to `VERIFIED` or explicitly re-planned.

---

## 1.0 Mandatory anchors

Decided before a line of code. These are the choices that, if settled wrong in Phase 1, leave
collected history unfixable retroactively.

| Anchor | Decision |
|---|---|
| **Approval gates** | No schema, field, or filter rule is created or changed without Ron's explicit approval. Also an invariant in `CLAUDE.md`. |
| `schema_version` | On every record. Separate versions for `RawPost` and `Listing`. `reclassify` depends on it entirely. |
| `raw` | The provider's JSON is stored whole and untouched. Never trimmed "because we don't need that field". |
| `media[]` | Stored even though the URLs are known to expire, together with `fetched_at`. Future re-hosting needs the list. |
| Time | tz-aware `datetime` in UTC everywhere. Conversion to Israel time happens only in message formatting. |
| `listing_id` | Our own deterministic key: `sha256(source_post_id)`. **`source` is deliberately excluded** so the same post from either provider yields one record during failover — see `SCHEMA.md` and `DECISIONS.md` #28. `pfbid` never enters a key. |
| `canonical_id` | For duplicates: the post with the earliest `posted_at` is canonical; the others point at it. |
| Deletion | None. A rejected post is stored with its reason. |
| `user_id` | On every personal record (`Decision`, `Notification`, user config), with a single fixed value in v1. Costs nothing now; avoids a full backfill when a second user arrives. `Notification` is keyed `(user_id, listing_id)`. |
| Post vs verdict | Stored **separately**. A post record holds what the post says; a verdict record holds what a given user's rules made of it. If a verdict lives on the post record, a second user means rewriting all history. |
| `config` interface | Configuration is read through one interface, like `store`. YAML implementation in v1, datastore implementation when a UI needs to edit it. No module reads a YAML file directly. |
| Collection vs user settings | Collection settings (`maxPosts`, `sortingOrder`, schedule frequency, the union of all groups fetched) are **shared** — one run serves everyone. User settings (which groups they subscribe to, filter rules, ranking) are **personal**. The watermark is per group and global, never per user. |
| Extraction vs ranking | Extraction is objective and shared: one classification per post, forever. Ranking is personal and is a calculation over stored fields — never a second model call and never a per-user prompt. |

---

## 1.1a Spike — verify `postsNewerThan` per-group behaviour (first, before anything else)

> **Sequencing note 2026-10-02.** Deferred at Ron's request. "Before anything else" means before
> anything that depends on it: `fetch()` in task 1.1 and the Phase 2 watermark input. Offline work
> against the fixture (task 1.3, Gate B) does not rest on P1 and proceeds first. See `SESSION_LOG.md`.

A throwaway script. One synchronous call to thedoor with **all 6 URLs**, `maxPosts=30`, and
**`fetchAllComments=false` and `includeTopComment=false` both set explicitly** — the OpenAPI
definition confirms both default to `true`, and both cost money.

`postsNewerThan` is sent as **relative minutes** (`"90 minutes"`), per `DECISIONS.md` #36. The
absolute form is date-only and would cap the watermark at one day; the relative form accepts
minutes. That half is already `VERIFIED` — the spike no longer has to establish it.

**What the spike still has to answer:**
1. Does the time window apply **per group**, or globally across the 6 URLs? (`ASSUMPTIONS.md` P1)
2. Do all six groups return data, or is one silently empty? (P5)
3. Does `includeTopComment=false` actually suppress `topComment`, or does the actor ignore it? (P9)
4. What is the real billed cost of the run? (P6)

**Output:** the raw response saved to `data/raw/` with a dated filename — every later adapter test
runs against it with no network calls.

**If the per-group behaviour fails:** fall back to 6 separate runs, and update task 1.1 *before*
writing it. This is exactly the failure mode `HANDOFF.md` §2 exists to prevent.

---

## GATE A — `RawPost` schema (before 1.1)

Settle: the field list at the provider boundary · what goes into `raw` vs a first-class field ·
the `media[]` shape · `native_price` and `price_source`.

**Why here:** `RawPost` is written to history. A field not stored now is permanently lost.

**DoD:** field table presented → Ron approved → table copied into `SCHEMA.md` with a date.

---

## 1.1 thedoor adapter + provider normalization

**Input:** `group_ids`, `since` → **Output:** `list[RawPost]`

Field map from `HANDOFF.md` §4. Four traps that each need their own test:

| Trap | Handling |
|---|---|
| `post_type: "shared"` | `text` is empty; real content sits in `sharedPost` |
| `creation_time` | RFC 2822 → `email.utils.parsedate_to_datetime` → UTC |
| missing `group_title` | thedoor does not provide it; must not crash or fabricate |
| `sale_post.price` | → `native_price`, with `price_source = "native"` |

**Tests:** against the 1.1a fixture. Zero network calls.

---

## 1.2 `textnorm` + phone extraction — ✅ COMPLETE (2026-09-14)

**Input:** raw text → **Output:** `norm_text`, `text_hash`, `phones[]`

Aggressive normalization: nikud, quote marks, whitespace, emoji, final letter forms. The output is
single-use — not stored, never sent to the model.

**Result:** 17 distinct hashes from 20 posts; exactly 3 colliding pairs, matching the 3 known
duplicates; no false collisions; no near-miss pair above 0.90 similarity. Phone numbers found in
10 of 20 posts. Full findings in `ASSUMPTIONS.md` D1–D9.

The draft implementation lives in `scratch/dedup_check.py` and is the starting point for the real
`textnorm/` module — subject to the empty-text rule in 1.3.

---

## 1.2b `textnorm` fixes carried over (before 1.3)

Decisions #37 and #38 were approved on 2026-09-14 but never reached the code (checked 2026-10-02).
Dedup stage A reads `text_hash`, `no_text` and `phones`, so both are fixed first. The exact changes
are listed in `BACKLOG.md`, "Decisions pending implementation".

**DoD:** an emoji-only post yields `no_text=True`, `text_hash=None` and raises nothing; stored
phones are digits only with `+972` converted to a leading `0`; tests updated; `uv run pytest` green.

---

## 1.3 Dedup stage A

**Input:** batch of `RawPost` + Repository → **Output:** canonicals / duplicates with `duplicate_of`

Three layers, in this order and with these weights (revised 2026-09-14 after task 1.2):

| Layer | Role | Weight |
|---|---|---|
| 1. `source_post_id` | Exact repeats, chiefly the deliberate watermark overlap | unchanged |
| 2. **`text_hash`** | **The primary key.** Caught 3/3 pairs in the sample | primary |
| 3. phone | **One-directional signal only.** A shared phone is strong evidence of the same listing; a missing or differing phone means nothing. Present in ~50% of posts | demoted from "key" |

`user.id` is never part of the hash — it is a rotating `pfbid` (invariant 5). Neither is the
poster's **name**: the same apartment posted by two different flatmates must still collide, and
adding the name would prevent exactly that.

**Within the batch and against history** — both same-group duplicates in the sample were in the same
window, so a history-only check would have missed them.

**Empty text handling.** A post whose text is empty after extraction (typically a `shared` post, or
one whose content is entirely in an image) must **not** be hashed — two empty strings would collide
with each other and produce a false duplicate. Such a post is:

- stored, never rejected
- flagged `no_text`
- **not sent to Gemini** (we do not analyse images)
- excluded from ranking, but retrievable as its own bucket in the future dashboard

**Test:** the 17 posts in random order return the same canonical set on every run.

---

## GATE B — `Listing` schema (before 1.4)

**The heavy gate.** Settle: the full list of fields the model will populate — including fields with
no v1 use that will become dashboard facets later (balcony, master room, floor, elevator, furnished,
has-address, and others) · the type and allowed values of each field · which fields may be `null`.

**The schema must cover every listing type, not only what Ron is looking for.** Whole empty
apartments, rooms in shared flats, sublets. `room_in_shared` is **Ron's filter**, not a schema
limit. A future user searching for an empty apartment must be servable from already-classified
history, with zero new model calls — otherwise adding them means a `reclassify` over everything.
This is the strongest reason to spend time in this gate.

**Why here:** every field not defined now will require a `reclassify` over all history later.
Most of the discussion time for this phase belongs in this gate.

Carried forward from `HANDOFF.md` §6: `listing_type` and `duration` stay separate fields —
`סאבלט ארוך` posts are simultaneously a room in a shared flat and a sublet.

**DoD:** field table presented → Ron approved → table copied into `SCHEMA.md` with a date.

---

## 1.4 Gemini classifier

**Input:** `RawPost` → **Output:** `Listing`

`temperature=0`, structured output, **schema derived from the pydantic model**. The original text is
sent verbatim. Retry with backoff. Token count and per-call cost logged.

Two known fixes from `HANDOFF.md` §6 go into the prompt:
1. `entry_date` must return the Hebrew as written, not `"immediate"`.
2. Tighten the never-invent rule (one case inferred `has_living_room` from apartment size).

**Regression test:** the 10 cases from §6, including all four adversarial ones.
**Post #18** (`אנחנו שני שותפים שמחפשים דירת 3 חדרים` → `seeking`) joins the set — the sniper no
longer covers it.

---

## GATE C — filter rules (before 1.5)

Settle:
- **Primary filter** — the hard conditions (price, areas, `listing_type`) and what counts as a failure.
- **Secondary filter** — which `missing_field` is critical vs unimportant, and the display order of
  reasons in the message.

**Why separate from Gate B:** filtering lives in `policy` and changes without touching the schema.
That separation is what lets calibration happen without reclassifying.

**DoD:** rule table presented → Ron approved → copied into `SCHEMA.md` with a date.

---

## 1.5 Policy + reasons

**Input:** `Listing` → **Output:** `Decision(notify=True, reasons[])`

`always_notify` in v1, but reasons are computed in full.

**The critical distinction:**

| Reason type | Meaning | Example |
|---|---|---|
| `filter_fail` | The model extracted correctly; the value does not match | `price 4,500 > 4,000` · `area: florentin` |
| `missing_field` | The model did not extract it | `area: null` · `is_agent: null` |

These are two completely different bugs — one is a filter-tuning problem, the other is an
extraction problem — and they are easy to confuse. This distinction is the heart of calibration mode.

---

## GATE D — dedup B key (before 1.6)

Settle: which fields compose the `price + rooms + street` key, and the behaviour when one is `null`.

**Upgraded in importance 2026-09-14.** This was scoped as a minor gate. Task 1.2 showed that phone
numbers cover only half of posts and cannot act as a key, which leaves layer 4 as the only thing
catching a listing reposted with **rewritten text and no phone**. It now carries real weight rather
than being a rare backstop. Decide deliberately: which fields, how many must match, and what a
`null` on either side means.

---

## 1.6 Dedup stage B

`price + rooms + street` over classified fields. Catches reposts with rewritten text — the case
neither the hash nor the phone can reach.

---

## 1.7 Formatting and Telegram send

**The real deliverable of this phase.** In calibration mode this message *is* the working instrument.

**Message structure:**
- Header with shortened `listing_id`
- Price · area
- **The full original text**
- Permalink
- The fields the model populated — `null` shown explicitly as "not written", never swallowed
- `confidence`
- Reasons block (`filter_fail` and `missing_field` visually separated)

**No-text posts get their own minimal form** (`DECISIONS.md` #39): link, images, and a line saying
there is no text and the content is probably in the image. No fields, no `confidence`, no reasons
block — there is nothing to fill. They are notified rather than dropped so that a silently discarded
post and a genuinely absent one never look the same.

**Two real constraints:**
1. Media caption is capped at 1024 characters; posts run to 1,572. Therefore `sendMediaGroup`
   followed by a **separate** text message — not a caption.
2. `sendMediaGroup` is capped at 10 images; some posts have more.
3. An image failure must not bring down the message.

**Test:** manually send all 17 posts to the private channel and read them by eye. That judgement
decides whether the format works.

---

## 1.8 Bootstrap mode

First run: everything is written to the store, **one summary message** is sent, watermarks are
initialized. An explicit flag — never auto-detected.

---

## 1.9 Wiring `run_once`

`pipeline.py` with no logic of its own. `run_id` on every log line. An error at any stage means no
watermark write (relevant now, enforced in Phase 2).

---

## 2. `ASSUMED` items this phase must close

Full register: `ASSUMPTIONS.md`. Status as of 2026-09-14:

| # | Assumption | Task | Status |
|---|---|---|---|
| 1 | `postsNewerThan` applies per group in a single multi-URL run | 1.1a | ⚠️ open. If it fails: 6 separate runs; one file changes |
| 1b | `postsNewerThan` supports minute granularity | — | ✅ **closed 2026-09-14.** Absolute form is date-only; the **relative** form accepts minutes. Always send relative minutes. No design change |
| 2 | The three duplicate pairs collide on normalized-text hash | 1.2 | ✅ **closed 2026-09-14.** 3/3 collided, no false collisions, no near-misses. Near-duplicate matching is not required — **no scope change** |
| 3 | Phone regex covers the real formats in the sample | 1.2 | ✅ **closed 2026-09-14.** Zero candidates missed on a recall cross-check. `+972` unexercised; dot-separated formats judged out of scope |
| 4 | `sharedPost` content is at `sharedPost.text` | 1.1 | ⚠️ open. Zero `shared` posts in the sample, so the path never executed. Field name is a guess — verify per the `external-contract-verification` skill |
| 5 | Actor pricing is ~$1.50 / 1,000 results | — | ✅ **closed 2026-09-13.** Confirmed by Ron. The store header's "from $1.00" is a tiered floor, not the rate |
| 6 | `includeTopComment=false` actually suppresses `topComment` | 1.1a | ⚠️ open. Defaults to `true` and bills per result; 3 of 20 sampled posts carried one despite the documented input |

---

## 3. Calibration loop

Without a dashboard, the simple thing that works: every message carries a shortened `listing_id`.
Ron maintains `calibration.jsonl` — one line per error:

```json
{"listing_id": "...", "field": "area", "got": null, "expected": "old_north", "note": "street name only, no area word"}
```

The file becomes a growing regression set, and `reclassify` will later be able to run a corrected
prompt over it and show how many errors closed. No infrastructure required.

---

## 4. End of phase

Before starting Phase 2:
1. Update `HANDOFF.md` — what was verified, what turned out wrong.
2. Update `ASSUMPTIONS.md` — move the three items above out of `ASSUMED`.
3. Update `SESSION_LOG.md`.
4. Only then plan Phase 2 semi-macro, with knowledge instead of guesswork.
