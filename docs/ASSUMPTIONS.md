# Assumptions Register

**Purpose:** every external contract detail and every empirical claim this project relies on,
tagged `VERIFIED`, `ASSUMED`, or `UNKNOWN`.

**The rule:** nothing moves to implementation while resting on `ASSUMED`. If an `ASSUMED` item
blocks progress, the next step is a spike that resolves it — not code that hopes.

**Last updated:** 2026-10-05 (task 2.2) — A1b and A1c no longer needed: the model decides the area (`DECISIONS.md` #167). Earlier, 2026-10-05 (spike 2.1) — O1, O3, O5, O7 and O10 verified, O4 and O11 in part, O12 added (❌ FALSE), I3 measured; O2 waits for the bill, O8 still UNKNOWN (`SPIKE_2_1_2026-10-05.md`). Earlier on 2026-10-05 — the model provider is OpenAI (`DECISIONS.md` #126): O1–O11 added from its documentation (`RESEARCH.md` §15); G1–G9 kept as the Gemini alternative; I3 re-estimated for `gpt-6-luna`. Earlier on 2026-10-05 — phase 2 plan: G1–G9 added (the Gemini API, from its documentation; `RESEARCH.md` §13), A1c added (UNKNOWN), C3 no longer applies. Earlier on 2026-10-05 — Gate B content: A1a chosen by Ron and re-read (still ✅ VERIFIED); A1b's source chosen, OpenStreetMap, its completeness UNKNOWN (status unchanged); P16 kept as a known limit, with the count from the real runs. Earlier, 2026-10-04 — end of phase 1: P7 contradicted (❌ FALSE, too low; the daily volume UNKNOWN), P21 added (UNKNOWN), A1 split into A1a (✅ VERIFIED) and A1b (❌ FALSE as a published list), evidence added to D2, D5 and I3. Earlier the same day: runs C and D: evidence added to P1c, P6, P19, P20 and I11; no status changed. Earlier the same day: run B: evidence added to P6, P19, P20, I6 and I11; no status changed. Earlier the same day: #80: I8's minimum raised to 3.38.0 for the store module; no status changed. Earlier the same day: run A, task 1.14: P20 added; evidence added to P6, P7 (contradicted once, still ASSUMED), P19, I6, I9 and I11; no other status changed. Earlier the same day: P1b and P1c wording: the window formula and the buffer of `DECISIONS.md` #78, task 1.13; no status changed. Earlier the same day: I6 extended and I9–I11 added, task 1.12 download check. Earlier the same day: P15–P19 added and P6 corrected, task 1.1. Earlier the same day: I8 (SQLite version in the container) added, task 1.10. Earlier the
same day: spike 1.1a results applied (`SPIKE_1_1a.md`)

> Written in English like every document in `docs/`, and like replies to Ron.
>
> `HANDOFF.md` and `MACRO_PLAN.md` are in `docs/archive/`. Research findings are in `RESEARCH.md`;
> the plan is `BASELINE.md`. Task numbers 1.4–1.9 belonged to the old Phase 1 and are retired; the
> entries below name the phase instead.

---

## Tag meanings

| Tag | Means |
|---|---|
| `VERIFIED` | Confirmed in current documentation **and** observed in a real captured response |
| `ASSUMED` | Documented but not observed, or observed once without documentation |
| `UNKNOWN` | Not established |

---

## Dedup and text normalization

Resolved by task 1.2, run 2026-09-14 against the raw 20-post thedoor response
(`data/raw/thedoor_20posts_2026-09-13.json`). Script: `scratch/dedup_check.py`.

| # | Claim | Tag | Evidence |
|---|---|---|---|
| D1 | A hash of aggressively normalized text catches the duplicate pairs | ✅ VERIFIED | 17 distinct hashes from 20 posts; 3 colliding groups, each exactly a pair. No group larger than 2. |
| D2 | The normalization produces no false collisions | ✅ VERIFIED | No colliding group contains genuinely different posts; no non-colliding pair scores ≥ 0.90 similarity on normalized text, so no expected pair narrowly missed. **The real runs, 2026-10-04:** 39 of 266 stored posts (14.7%) are hash duplicates; not inspected for false collisions (`RESEARCH.md` §11). |
| D3 | Near-duplicate matching (Jaccard over shingles) is **not** required | ✅ VERIFIED | Follows from D1 + D2. This was the one failure mode that would have been a scope change. It did not occur. |
| D4 | The three colliding pairs are the three known duplicate pairs | ✅ VERIFIED | Count verified by script; identity confirmed by Ron on inspection, 2026-09-14. The script was not given the expected `post_id` list and could only verify the count. |
| D5 | Phone numbers are present in only about half of posts | ✅ VERIFIED | 10 of 20 posts contained a phone number. **The real runs, 2026-10-04:** a phone in 161 of 266 posts (61%) (`RESEARCH.md` §11). |
| D6 | Phone number cannot serve as a primary dedup key | ✅ VERIFIED | Follows from D5, and from pair 3 below: both posts in that pair have no phone at all. Relying on phone as the key would have missed one of three duplicate pairs. |
| D7 | A shared phone number is strong positive evidence of the same listing | ⚠️ ASSUMED | Pairs 1 and 2 each shared a phone (`0548008244`, `050-9184537`). Two cases is suggestive, not conclusive. Treated as a one-directional signal: a match is evidence, a non-match carries no information. |
| D8 | The phone regex covers the formats that appear in real posts | ✅ VERIFIED | Recall cross-check against any 7–13 digit run found zero candidates missed. Dot-separated formats (`054.800.8244`) are covered by neither the regex nor the cross-check, but were judged out of scope: Israelis do not write phone numbers that way in Facebook posts. |
| D9 | `+972` international format appears in these groups | ⚠️ ASSUMED | Zero occurrences in the sample. The regex branch exists and is kept — it costs nothing — but is unexercised. Expected to stay rare: these are Israeli groups for Israeli apartments. |

---

## Sample composition

Established by a read-only inspection of `data/raw/thedoor_20posts_2026-09-13.json` during the
Phase 0 plan review, 2026-09-14. These are facts about the sample, and they bound what can be
tested without synthetic data.

| Fact | Tag |
|---|---|
| 20 posts: **12 `regular`, 8 `sale_post`, 0 `shared`** | ✅ VERIFIED |
| All 8 `sale_post` posts carry a price string. The posts with no `native_price` are the 12 `regular` ones | ✅ VERIFIED |
| **0 posts have empty text.** `no_text=True`, `text_source="none"` / `"shared_post"`, and `text_hash=None` can only be exercised with synthetic cases | ✅ VERIFIED |
| 82 media items total. 2 are `Video` items that **omit the `width` and `height` keys entirely** — they are not `null`. Typing them as `int` fails those 2 posts; a missing key maps to `None`. `Video` items also carry an extra `thumbnail` key, and their `page_url` is a `/videos/` page rather than `photo/?fbid=` | ✅ VERIFIED |
| 2 posts have an empty `media` array. Under the "no images" rule (`BASELINE.md` §5) these are rejected before the model: about 10% of the sample | ✅ VERIFIED |
| `topComment` is present on exactly 3 posts despite `includeTopComment: false` | ✅ VERIFIED |
| The sample spans only 2 groups × 10 posts, so "within the same group" and "across groups" coincide for all three duplicate pairs | ✅ VERIFIED |

---

## Normalization choices made in `scratch/dedup_check.py`

Disclosed 2026-09-14. `PHASE_1.md` names this script the starting point for the `textnorm/` module,
so these are contract details, not implementation trivia.

| Choice | Tag | Note |
|---|---|---|
| Lowercases the text | ✅ accepted | Harmless for Hebrew; affects embedded English consistently |
| Strips plain and curly quotes, not only geresh and gershayim | ✅ accepted | Wider than first described, but consistent, which is all hashing needs |
| The "emoji" range also removes arrows (U+2190–21FF) and U+2B00–2BFF symbols | ✅ accepted | Same reasoning |
| The `+972` branch matches mobile numbers only (`+972 5X`) | ⚠️ ASSUMED | Unexercised in the sample. Landline international format would be missed |
| The shared-post fallback triggers on `post_type == "shared"`, not on empty text | ✅ **answered** 2026-10-04 | Neither: a shared post is detected by `sharedPost` being present. Spike 1.1a found `shared`, `shared_reel` and `__reel__` all carrying a `sharedPost`. Settled in the Gate A amendment (`SCHEMA.md`, `DECISIONS.md` #63) |

### The three duplicate pairs, for the record
| Pair | post_ids | group_id | Shared phone |
|---|---|---|---|
| 1 | `10163683432542695` / `10163683412257695` | `35819517694` | `0548008244` |
| 2 | `2178554076041449` / `2178430789387111` | `333022240594651` | `050-9184537` |
| 3 | `2178092279420962` / `2177447349485455` | `333022240594651` | neither post has a phone |

Pair 3 is the load-bearing case: hash was the only layer that caught it.

---

## Provider contract — thedoor

| # | Claim | Tag | Evidence |
|---|---|---|---|
| P1 | `postsNewerThan` applies **per group** in a single run with multiple URLs | ✅ VERIFIED | 2026-10-04, spike 1.1a. Run `GcarNt1rhe8tuSDuV` log: one cutoff, applied by each group independently (five groups stopped at 22, 17, 0, 8, 28 posts). Exact match, post ID for post ID, against control run `9TShaAS1e6c2fv56t`. One run for all six groups stands. `SPIKE_1_1a.md` Q1. |
| P1b | `postsNewerThan` accepts **minute** granularity | ✅ VERIFIED | The actor's OpenAPI definition (current build, 2026-09-12) gives the pattern `^\d{4}-\d{2}-\d{2}$\|^(\d+(?:\.\d+)?)\s*(minute\|hour\|day\|week\|month\|year)s?$`. The **absolute** form is date-only — a full ISO datetime is rejected. The **relative** form accepts minutes and decimals (`"45 minutes"`, `"1.5 hours"`). Decision: always send relative minutes, computed as `now - min(watermark) - buffer`. See `DECISIONS.md` #36. *Since #78 (2026-10-04): `now - (last successful run's start - 15 minutes)`.* |
| P1c | Relative windows are measured from **run start**, not from our calculation | ⚠️ ASSUMED | **Observed 2026-10-04** in the spike 1.1a log: the cutoff was the actor's own start minus the window (≈1 s after Apify's `startedAt`). Not stated in the documentation, so it stays ASSUMED by the tag rule. A delayed run start shifts the window by the delay; the overlap buffer (15 minutes, `DECISIONS.md` #78 W2) absorbs it — an additional reason not to shrink that buffer. **Run D, 2026-10-04 (`data/runs/run_D_2026-10-04/REPORT.md`):** the actor returned one row older than the run's `since`, which `fetch()` dropped (34 rows, 33 kept) and which was billed. Consistent with `postsNewerThan` rounded up to whole minutes and measured from the actor's own start; status unchanged. |
| P2 | `sharedPost` content is at `sharedPost.text` | ✅ VERIFIED | 2026-10-04, spike 1.1a: shared text at `sharedPost.text`, images at `sharedPost.media`, 19 of 19 rows. `sharedPost.time` is `null` on all 19. `post_type` values `shared_reel` and `__reel__` can also carry a `sharedPost`. `SPIKE_1_1a.md` Q6. |
| P3 | `fetchAllComments` defaults to **`false`** | ✅ VERIFIED | Changed: the OpenAPI definition of build 1.0.195 (2026-10-03) gives `"default": false`; it was `true`. Still always sent explicitly as `false`. `SPIKE_1_1a.md` Q3. |
| P4 | `sortingOrder: newest_activity` mixes bumped old posts into the feed | ✅ VERIFIED | `RESEARCH.md` §2. Always `newest_posts`. |
| P5 | Failed or private groups are silent — no diagnostic rows in the dataset | ✅ VERIFIED | `RESEARCH.md` §2. Errors go to the run log only. Zero results and a failure are indistinguishable from the data alone. **The run log carries per-group status** (`Posts: N \| Reason: …`, `Successful groups: x/6`), seen 2026-10-04 in spike 1.1a. |
| P6 | Actor pricing is ~$1.50 / 1,000 results | ✅ VERIFIED | **Real bill, 2026-10-04 (spike 1.1a):** $0.0015 per result, $0.005 per start event, one start event per run at 1 GB. Results charged were first read as fewer than rows returned (99/105, 165/180); that was a preliminary figure, see P19. Confirmed by Ron, 2026-09-13. The store page header shows "from $1.00 / 1,000 results", which is the **floor** of a tiered per-event scheme, not the working rate; the actor's own description on the same page reads "⚡1.5$". A cached older snapshot of the Input tab shows $3.00. Three numbers, one page — always read the Pricing tab, never the header. **Run A, 2026-10-04 (task 1.14):** 212 items and 1 start charged, $0.323 = 212 × $0.0015 + $0.005, read about 10 minutes after the run; charged items equal rows returned. **Run B, 2026-10-04:** 33 items and 1 start charged, $0.0545 = 33 × $0.0015 + $0.005. **Runs C and D, 2026-10-04:** 30 items and 1 start, $0.05; 34 items and 1 start, $0.056. |
| P8 | `sortingOrder` has a fourth value, `buy_sell_listings` | ✅ VERIFIED | Full enum: `newest_posts`, `newest_activity`, `most_relevant`, `buy_sell_listings`. Buy/Sell mode **skips ordinary posts**. Not used. Invariant 6 stands. |
| P9 | `includeTopComment` defaults to **`true`**, and `false` suppresses `topComment` | ✅ VERIFIED | Default from the OpenAPI definition. Suppression verified 2026-10-04, spike 1.1a: the flag is in both runs' stored input, and 0 of 285 rows carry a non-null `topComment` (the key stays, as `null`). The research run's 3 of 20 remain unexplained, most likely the flag was not sent then. `SPIKE_1_1a.md` Q3. |
| P10 | `maxPosts` has no maximum in the current schema | ✅ VERIFIED | Default 50, minimum 1, no upper bound. A cached older snapshot claims a maximum of 500. |
| P11 | `topComment` is an array | ❌ FALSE | The README documents an array; the real response carries an object or `null`. Per skill principle P2, the real response wins. |
| P12 | The actor's human-readable **Input tab is stale** | ✅ VERIFIED | It serves an April-2026 snapshot (603 users, 12K runs, $3.00, only `url` / `maxPosts` / `isNewPosts`) while the API pages of the same actor show the current build (4.5K users, 28K runs, modified 2026-09-12). **`/api/openapi` is the source of truth for an Apify actor's input schema**, not the Input tab. |
| P13 | The run log's per-group status lines are stable enough to rely on for silent-group detection | ⚠️ ASSUMED | Seen in two runs, 2026-10-04. The log format is not a documented contract. |
| P14 | `Photo` media items can also lack `width`/`height` | ✅ VERIFIED | 2026-10-04, spike 1.1a: 9 `Photo` and 11 `Video` items without the keys. Until then only videos were known to omit them. |
| P7 | Post volume is **~150 posts/day across the six groups** | ❌ FALSE — too low | Measured 2026-10-04 (spike 1.1a): 75 posts in a 24-hour window from five groups, plus ~73/day for `101875683484689`; Friday night to Saturday. **Contradicted by the real runs, 2026-10-04 (`RESEARCH.md` §11):** more than 212 posts in run A's 24 hours (Saturday 12:55 to Sunday 12:55 UTC), two groups cut off at `maxPosts` 50; about 13–15 new posts an hour on the Sunday afternoon (runs B and D). **The real daily volume is UNKNOWN: one day of data.** A week of real runs measures it (`BACKLOG.md`). The silent-group thresholds (`RESEARCH.md` §9) and the monthly cost (§3) depend on it. |
| P15 | What `run-sync-get-dataset-items` returns when the run fails, is aborted or hits the charge cap | ❓ UNKNOWN | Not documented in the Apify API spec `v2-2026-10-01T153946Z`. The spec documents no run-ID header on the sync response, a 408 after 300 s, and "if the connection breaks, you will not receive any information about the run". Not used: `fetch()` uses the regular call (`DECISIONS.md` #71 A). |
| P16 | A shared post with its own caption: its `text` is the caption, and `sharedPost.text` (the shared listing) does not reach the model | ✅ VERIFIED (known gap) | 1 of the 15 shared posts in spike 1.1a run 1. Gate A as approved: `text` falls back to `sharedPost.text` only when the post's own text is blank. Media still falls back. Kept as is by Ron (`DECISIONS.md` #71 H). **Kept as a known limit at Gate B**, Ron, 2026-10-05 (#107). **The real runs, 2026-10-04 (store read 2026-10-05):** 35 of 266 stored posts carry a `sharedPost`; 1 of them has both its own text and a non-blank `sharedPost.text`. |
| P17 | What a run does when it reaches `maxTotalChargeUsd` (final status, partial dataset) | ❓ UNKNOWN | Not documented. What is verified: the platform sets the run's `options.maxItems` from the cap (333 at $0.50, spike 1.1a). `fetch()` treats rows returned ≥ `options.maxItems` as a failed run (`DECISIONS.md` #71). |
| P18 | `POST /v2/actor-runs/{runId}/abort` stops a running run | ⚠️ ASSUMED | Documented in the Apify API spec. **Path, auth and response shape VERIFIED 2026-10-04** by one no-op call on the finished spike run `GcarNt1rhe8tuSDuV` (Ron's choice, no actor run): HTTP 200, the run object under `data`, status still `SUCCEEDED`. Saved as `data/raw/apify_abort_noop_2026-10-04.json`. Stopping a *running* run has not been observed. `fetch()` raises after the abort whatever it returns, so a failed abort costs money (up to the cap), never a watermark. |
| P19 | Run cost read at the end of a run is final | ❌ FALSE | Read again on 2026-10-04, run 1 shows 105 results charged and $0.1625; at the end of the run it showed 99 and $0.1535. The "results charged fewer than rows returned" in spike 1.1a was a preliminary figure, as the API spec warns. The control run was not re-read. `fetch()` logs the end-of-run figure anyway (`DECISIONS.md` #71); the monthly projection already priced every row. **Run A, 2026-10-04:** $0.32 at the end of the run, as `fetch()` logged it; $0.323 and 212 items charged, read about 10 minutes later. **Run B, 2026-10-04:** `fetch()` logged $0.005 at the end of the run, the start fee alone; read 12 to 13 minutes later, three times, it was $0.0545 with 33 items charged. The logged figure can miss every row. **Runs C and D, 2026-10-04:** logged $0.0485 and $0.041 at the end of the run; read later, $0.05 and $0.056. |
| P20 | `fetch()`'s regular (non-sync) call works against the live API: start with the charge cap, poll `waitForFinish` to a terminal status, read the dataset, map every row | ✅ VERIFIED | 2026-10-04, run A (`data/runs/run_A_2026-10-04/REPORT.md`): Apify run `PI0qBslZY0nAeaIi5` `SUCCEEDED` in 60 s; 212 rows, mapped 212, skipped 0, dropped 0. The run object shows `maxTotalChargeUsd` 0.5 and `maxItems` 333, so the cap was received. How many polls it took is not logged; the deadline abort and a run at the cap were not exercised. Run B, 2026-10-04: `SUCCEEDED` in 14 s, 33 rows, mapped 33, skipped 0, dropped 0 (run B (`data/runs/run_B_2026-10-04/REPORT.md`)). Runs C and D, 2026-10-04: `SUCCEEDED`, 30 and 34 rows, mapped all, skipped 0, dropped 0 (`data/runs/run_C_2026-10-04/REPORT.md`, `data/runs/run_D_2026-10-04/REPORT.md`). |
| P21 | The actor returns every photo of a post | ❓ UNKNOWN | The real runs, 2026-10-04 (`RESEARCH.md` §11): no post has more than 5 media items, and `photo_count` never exceeds 5 either; 134 of the 231 posts with their own media have exactly 5. Whether posts with more photos are cut at 5 by the actor, or by Facebook's logged-out view, is not established. Nothing is built on it. |

---

## Provider contract — memo23 (backup)

| # | Claim | Tag |
|---|---|---|
| M1 | Field map as recorded in `RESEARCH.md` §2 | ✅ VERIFIED — against real output at research time |
| M2 | Input uses `startUrls`, not `url` | ⚠️ ASSUMED — different from thedoor; re-verify before writing the failover adapter |
| M3 | Still available and not under maintenance | ⚠️ ASSUMED — re-check when the failover adapter is built, not now |

---

## Classification

| # | Claim | Tag | Evidence |
|---|---|---|---|
| C1 | Gemini Flash classifies these posts accurately at `temperature=0` | ✅ VERIFIED | 10/10 on real posts including 4 adversarial cases. `RESEARCH.md` §7. |
| C2 | Post #18 (`אנחנו שני שותפים שמחפשים דירת 3 חדרים`) classifies as `seeking` | ❓ UNKNOWN | Never tested. **Raised in importance 2026-10-03:** "seeking" is now a rejection reason and rests on the model alone (`DECISIONS.md` #45). Must be in the regression set when the classifier is built in phase 2. |
| C3 | `confidence` discriminates usefully | No longer applies | 0.9 on the sparsest post, 1.0 elsewhere. One data point of variation. **2026-10-05:** Gate B has no `confidence` field (`SCHEMA.md`, Gate B draft), so nothing rests on it. |
| C4 | The pydantic-derived JSON schema is accepted by the Gemini structured-output API | ⚠️ ASSUMED | Not every pydantic construct survives the conversion. Verify in phase 2. |
| G1 | The model ids and stages of `RESEARCH.md` §13 (`gemini-3.8-flash`, `gemini-3.5-flash-lite` stable) | ⚠️ ASSUMED | Models page, last updated 2026-10-01. No call made |
| G2 | The prices of `RESEARCH.md` §13 | ⚠️ ASSUMED | Pricing page, last updated 2026-10-01. Read off a real bill before any monthly figure is relied on, as for Apify (P6, P19). 3.8 Flash doubles on 2027-01-01 |
| G3 | Thinking tokens per post, at the lowest level each model allows | ❓ UNKNOWN | Billed as output. `gemini-3.8-flash` cannot go below "low"; `gemini-3.5-flash-lite` defaults to "minimal". Measured in the phase 2 spike from usage metadata |
| G4 | Tokens per character of Hebrew post text | ❓ UNKNOWN | The docs give ~4 characters per token without naming a language. The stored pending canonicals average 523 characters (median 442, at most 2,842), read 2026-10-05 |
| G5 | A Gemini 3.x model at `temperature=0` classifies these posts without looping or degrading | ❓ UNKNOWN | The docs "strongly recommend" the default 1.0 for all Gemini 3 models; `BASELINE.md` §4 says 0. C1 was measured on an earlier Flash generation |
| G6 | The project's rate limits on the paid tier | ❓ UNKNOWN | Not published; shown in AI Studio per project and tier. Tier 1 also has a $10-per-10-minutes spend limit |
| G7 | The free tier uses submitted posts to improve Google's products, with human review; the paid tier does not | ✅ VERIFIED | Gemini API terms, last updated 2026-04-28, read 2026-10-05: "Do not submit sensitive, confidential, or personal information to the Unpaid Services." Israel is not under the EEA / Switzerland / UK exception. The posts carry real phone numbers |
| G8 | AI Studio's project spend cap is a hard stop | ❌ FALSE | Billing page, 2026-09-28: "Experimental"; billing data can lag about 10 minutes; overages beyond the cap are possible, batch jobs included. A run needs its own cap |
| G9 | `models.generate_content` with `response_json_schema` from a pydantic model works on the chosen model | ⚠️ ASSUMED | Documented in `google-genai` 2.28.0 (2026-10-02); the API docs' examples now use the Interactions API. Together with C4, settled by the phase 2 spike |
| C5 | `schema.py` and `prompt.py` in `data/raw/` are suitable for production use | ❌ **NO** | They are research artifacts from the initial feasibility test. They proved Gemini works; they were not designed to cover every listing type or the future dashboard facets. **They are input to Gate B and Gate C, never a starting point to be extended silently.** |

---

## Classification — OpenAI (the provider since `DECISIONS.md` #126)

Read from the documentation on 2026-10-05 (`RESEARCH.md` §15); no call made. G1–G9 above are
Gemini, now a researched alternative.

| # | Claim | Tag | Evidence |
|---|---|---|---|
| O1 | `gpt-6-luna` is a current model, called by that id | ✅ VERIFIED | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): 121 responses, every one reporting `"model": "gpt-6-luna"`, the alias with no dated version. What the alias points at can still change without notice; the reported value is logged (`DECISIONS.md` #149) |
| O2 | `gpt-6-luna` costs $0.10 input, $0.01 cached input, $0.125 cache write, $0.50 output per 1M tokens; batch and flex half | ⚠️ ASSUMED | The model page and the pricing page agree, and match the review chat's read. Confirmed on a real bill before any monthly figure is relied on (P6, P19). Spike 2.1, 2026-10-05: $0.0273 by the usage metadata at these prices; the dashboard figure is still to be read and compared (`BACKLOG.md`) |
| O3 | At `reasoning.effort` `none` the model produces no reasoning tokens; the default is `medium`; reasoning tokens bill as output | ✅ VERIFIED (`none`, `low`) | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): `reasoning_tokens` 0 on all 80 calls at `none`; at `low` 153 a call on average (at most 289), counted inside `output_tokens`. `medium` was not tried |
| O4 | `temperature` is accepted only at effort `none` | ⚠️ ASSUMED (half observed) | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): temperature 0 at `none` was accepted on 40 calls. Sending it at `low` was not tried (the documentation says to remove it). **Temperature 0 is not deterministic:** see O12 |
| O5 | The schema pydantic derives for the response model passes strict structured outputs (every field required, `additionalProperties: false`, the root an object, `$defs`, `anyOf`, `format: date`) | ✅ VERIFIED | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): the approved `ListingExtraction` passed unchanged, ten `$defs` and `anyOf` included; 120 of 120 answers validated. An `allOf` is refused with HTTP 400 `invalid_json_schema`, at no cost |
| O6 | API data is not used for training by default; abuse-monitoring logs keep prompts and responses up to 30 days; the Responses API stores application state for 30 days unless `store: false` | ✅ VERIFIED (documentation) | Data-controls guide, read 2026-10-05. The Services Agreement itself returned HTTP 403 and was not read. Every call sends `store: false` (`DECISIONS.md` #147); the 30-day abuse log cannot be switched off without OpenAI's approval (Zero Data Retention), and Ron accepted it (#146) |
| O7 | Prompt caching: a prefix of at least 1,024 tokens; explicit breakpoints keep the post out of the cache; a write is 1.25× input, a read 0.1×; a prefix lives at least 30 minutes | ✅ VERIFIED (except the lifetime) | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): explicit mode; the 2,514-token prefix (instructions and schema) written once, then read on every call; no call wrote more than the prefix. `cache_write_tokens` are counted inside `input_tokens`. The cache survived a change of temperature; a change of effort wrote it again. The 30-minute lifetime was not tested. The prices are O2 |
| O8 | Ron's organization's usage tier, and so its rate limits and monthly usage limit | ❓ UNKNOWN | Tier 1 for `gpt-6-luna`: 500 requests and 500,000 tokens a minute; a $100 monthly usage limit. The free tier does not support the model. Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): 123 calls one after another (3–5 s each) met no 429 and no refusal; the rate-limit headers were not recorded. The account holds about $9 of credit (`DECISIONS.md` #155) |
| O9 | A project hard spend limit stops a run in time | ❌ FALSE | Spend-limits guide: "enforcement is not instantaneous, so recorded spend can slightly exceed" it. Set as a second line; the script's own cap is the first (as G8 for Gemini) |
| O10 | Tokens per post: the instructions and schema, the Hebrew text, the output | ✅ VERIFIED (20 posts) | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): the instructions and schema 2,514 tokens (cached); the post 248 uncached tokens on average (at most 568); the output 272–286 at `none` (at most 496), 476 at `low` (at most 784). Steady cost per post $0.00019 at `none`, $0.00029 at `low`, at list prices (O2) |
| O11 | `openai` 3.24.0's `client.responses.parse(..., text_format=Model)` sends the pydantic schema strict and returns `output_parsed` | ⚠️ ASSUMED (in part) | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): the SDK's own schema helper (`type_to_text_format_param`, the one `parse` uses) produced the strict schema that passed; the calls used `responses.create` and parsed the JSON with pydantic. `responses.parse` itself was not called |
| O12 | `gpt-6-luna` at temperature 0 gives the same answer twice | ❌ FALSE | Spike 2.1, 2026-10-05 (`SPIKE_2_1_2026-10-05.md`): two passes over 20 posts at effort `none`, temperature 0: 6 posts differed in some field, one of them in `post_nature` (`rental_offer`, then `not_listing`). With temperature omitted 10 differed; at `low` 7. The regression set has to run a setting more than once |
| O13 | The failure shapes the spike never saw. A refusal is an output content item `{"type": "refusal", "refusal": "<text>"}`. The 429 codes: `project_spend_limit_exceeded` and `organization_spend_limit_exceeded` (spend limits), `credit_balance_exhausted` and `organization_usage_limit_exceeded` (quota), `slow_down` (`rate_limit_error`), and a rate 429 with no code. 503 is `server_is_overloaded` (`service_unavailable_error`). `Retry-After` is in seconds. In `openai` 3.24.0, `RateLimitError`, `InternalServerError`, `APITimeoutError`, `APIConnectionError` and the error body's `code` | ⚠️ ASSUMED | Read 2026-10-05, the error-codes, structured-outputs, rate-limits and spend-limits guides, and the SDK's `_exceptions.py` and `_client.py`. **Documentation and the SDK only; none was observed.** Ron accepted building on them (`DECISIONS.md` #181); the first real one is captured into `data/raw/`. The error-codes page no longer lists `insufficient_quota` (it lists `credit_balance_exhausted`); the transport maps both to a quota stop. `openai` 3.24.0 depends on `httpx2`, not `httpx` |

## Telegram

| # | Claim | Tag |
|---|---|---|
| T1 | Media caption is capped at 1024 characters while posts run to 1,572 | ⚠️ ASSUMED — verify against the Bot API docs in phase 4 |
| T2 | `sendMediaGroup` accepts at most 10 items | ⚠️ ASSUMED — verify in phase 4 |
| T3 | Signed image URLs survive long enough for Telegram to download on send | ✅ VERIFIED at research time. Less relevant now: images are downloaded at fetch time |
| T4 | The bot needs no public address: updates by long polling (`getUpdates`), sends by outbound calls. Undelivered updates are kept up to 24 hours | ✅ VERIFIED — Bot API docs, read 2026-10-02 |
| T5 | A Mini App loads from a tailnet-only HTTPS address on a device with Tailscale on | ⚠️ ASSUMED — the docs require an HTTPS URL and do not say whether it must be publicly reachable. Spike in phase 4. If it fails, the plain site still works |

---

## Cost and infrastructure

| # | Claim | Tag |
|---|---|---|
| I1 | Firestore free tier absorbs thousands of rows and 48 runs/day | No longer applies — SQLite on the home server (`DECISIONS.md` #44). Relevant again only if the GCP fallback is used |
| I2 | Cloud Run Job + Scheduler at 48 runs/day stays within free tier | No longer applies — same reason |
| I3 | Gemini Flash cost at ~150 posts/day is negligible | ⚠️ ASSUMED — measure in phase 2. The volume is higher than ~150/day (P7: more than 212 on 2026-10-04). **Estimated 2026-10-05 from the documented prices** (`PHASE_2.md` §2.8, token counts assumed, G3, G4): about $7–23 a month on `gemini-3.5-flash-lite`, $18–60 on `gemini-3.8-flash` through 2026, $36–128 from 2027-01-01. Not negligible for 3.8 Flash against collection's $20–26. **Re-estimated 2026-10-05 for `gpt-6-luna`** (O2, O10; `PHASE_2.md` 2.8): about $0.0002–0.0013 a post, about $1–11 a month. **Measured in spike 2.1, 2026-10-05:** $0.00019 a post at effort `none`, $0.00029 at `low`; about $1.2–1.9 a month at `none`, $1.6–2.6 at `low`, at list prices. Still an estimate until a real bill and a real working day confirm it |
| I4 | Tailscale Serve publishes a local service over HTTPS to the tailnet only, and device sharing gives an outside Tailscale user access to one machine | ✅ VERIFIED — Tailscale docs, read 2026-10-02 |
| I5 | Device sharing covers the number of friends on the free plan | ❓ UNKNOWN — check before phase 5 |
| I6 | Images can be downloaded from the signed Facebook links at fetch time | ✅ VERIFIED — 2026-10-04, spike 1.1a: 5 of 5, plain GET with no token or cookies, HTTP 200, JPEG. Task 1.12 check, the same day, about 8.5 hours after the control run: 632 of 632 photo links of the control dataset, HTTP 200, `image/jpeg`, JPEG bytes, 10 KB – 591 KB (`data/raw/spike_1_12_images_2026-10-04/REPORT.md`). From the laptop only; the home server is unverified. **Run A, 2026-10-04, task 1.14:** 415 photos downloaded through `download_images`; the 273 that failed all failed DNS resolution after the laptop's network dropped at 13:05:37Z; the 546 attempts took 1.25 s, how long the outage lasted is unknown (run A (`data/runs/run_A_2026-10-04/REPORT.md`)), none was refused by the CDN. **Run B, 2026-10-04 (#80):** 214 photos downloaded from links stored by run A about 2 hours earlier, with no Apify call; 0 failed (run B (`data/runs/run_B_2026-10-04/REPORT.md`)) |
| I9 | The extension in a photo link's path says what is served | ❌ FALSE — 2026-10-04, task 1.12 check: the 57 `.png` and 20 `.webp` links served JPEG with `image/jpeg`. The downloader reads the type from the bytes (`DECISIONS.md` #77 D1). Run A, 2026-10-04: all 415 photos held were JPEG |
| I10 | A photo link downloads without a `User-Agent` header | ✅ VERIFIED for 5 links — 2026-10-04, task 1.12 check: one `.jpg`, one `.png`, one `.webp` and two more `.jpg`, all HTTP 200 and JPEG. The header is sent anyway (`DECISIONS.md` #77 D5c) |
| I11 | Downloading a bootstrap run's photos one at a time is not throttled, and takes about 1.6 s per photo | ✅ VERIFIED from the laptop — 2026-10-04, task 1.12 check: 632 links in 1,010 s, no 403, 429 or timeout; median 1.77 s for `.jpg`, at most 2.97 s. Concurrent requests and the home server: not tried. **Run A, 2026-10-04:** 415 photos in about 564 s, about 1.36 s each, no 403, 429 or timeout (run A (`data/runs/run_A_2026-10-04/REPORT.md`)). **Run B, 2026-10-04:** 308 photos in 679 s, about 2.2 s each, slower than runs before it; no 403, 429 or timeout (run B (`data/runs/run_B_2026-10-04/REPORT.md`)). **Run D, 2026-10-04:** 95 photos in 74 s, about 0.78 s each (`data/runs/run_D_2026-10-04/REPORT.md`) |
| I7 | Signed image links expire ≈ 4.4 days after fetch | ⚠️ ASSUMED — read from the `oe` query parameter as a hex Unix timestamp (4.3–4.5 days on all 355 links in run 1). That reading is not documented; nothing was re-downloaded later |
| I8 | The home-server container's SQLite is at least 3.38.0, the store module's minimum (the JSON functions built in by default, `DECISIONS.md` #80; read on sqlite.org/json1.html, 2026-10-04); the state module needs 3.24.0 (#65) | ❓ UNKNOWN — checked when the image is built (phase 5); Ron: the server will be set up to match what the code needs, and `BACKLOG.md` has the phase 5 check. Ron's laptop: Python 3.12.9 with SQLite 3.45.3, run 2026-10-04. Below the minimum, both modules refuse to start and name the found and required versions |

---

## Location

| # | Claim | Tag |
|---|---|---|
| A1 | A public source lists Tel Aviv areas and the streets in each, including a north/south split of the Old North | Split below, 2026-10-04 (`RESEARCH.md` §12). No single source does both |
| A1a | A public source lists Tel Aviv's areas, with the Old North split north/south | ✅ VERIFIED — the municipality's `שכונות` open dataset (GIS layer 511, read 2026-10-04): 71 neighbourhoods, among them `הצפון הישן - החלק הצפוני` (30) and `הצפון הישן-החלק הדרומי` (31); loaded 2024-11-18. Under the open-data portal's licence (as-is, no named licence). **Chosen by Ron, 2026-10-05** (`DECISIONS.md` #81): all 71 entries are the closed list. **Re-read 2026-10-05** under the `external-contract-verification` skill: 71 features, `ms_shchuna` 1–71 with no gap, fields `ms_shchuna` (integer) and `shem_shchuna` (string), every row `date_import` `18/11/2024 00:59:04`. Five names carry the geresh or parenthesis at the logical start (5, 7, 17, 18, 49). Saved as `data/raw/tlv_gis_layer511_rows_2026-10-05.json` and `…_meta_2026-10-05.json`; the list is in `SCHEMA.md`, Gate B draft |
| A1b | A public source maps every street to its areas | ❌ FALSE as a published list — none found. Derivable by placing streets in the neighbourhood polygons: from OpenStreetMap (ODbL; completeness for Tel Aviv not measured) or from the municipality's address layer (52,176 points with street code and house number; not on the open-data portal, and the website's terms forbid copying and automated access). The CBS assigns main streets only to statistical areas (`RESEARCH.md` §12). **Source chosen by Ron, 2026-10-05** (`DECISIONS.md` #84): derived from OpenStreetMap; the municipality's address layer is not used. **OSM's completeness for Tel Aviv: ❓ UNKNOWN, not measured.** It is checked against the Population Authority's street register before the derived table is relied on; nothing is built on the table until then **No longer needed, 2026-10-05:** the model decides the area (`DECISIONS.md` #167); no street table in phase 2 (#168) |
| A1c | Layer 511 returns its polygons in WGS84 when asked (`outSR=4326`), to place OSM streets in them | ❓ UNKNOWN | Stored in EPSG:2039 (`RESEARCH.md` §14). Checked by the street-table task **No longer needed, 2026-10-05** (#167, #168) |

---

## Legal

| # | Claim | Tag |
|---|---|---|
| L1 | Use by several close friends keeps the tool within personal use under the Israeli Privacy Protection Law | ❓ UNKNOWN — never checked legally. Ron's decision (2026-10-02): the users are close friends searching with him or alongside him, and he treats the tool as personal for them too. Not legal advice. |

---

## Closed

| Claim | Outcome |
|---|---|
| Near-duplicate matching may be required if hashes do not collide | Closed 2026-09-14. Did not occur — see D1–D3. No scope change. |
| Phone number is the real primary key of a listing | Closed 2026-09-14. **False.** Present in only 50% of posts; absent from both sides of one duplicate pair. Demoted to a one-directional signal. |
