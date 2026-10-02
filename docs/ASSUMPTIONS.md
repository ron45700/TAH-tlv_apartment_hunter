# Assumptions Register

**Purpose:** every external contract detail and every empirical claim this project relies on,
tagged `VERIFIED`, `ASSUMED`, or `UNKNOWN`.

**The rule:** nothing moves to implementation while resting on `ASSUMED`. If an `ASSUMED` item
blocks progress, the next step is a spike that resolves it — not code that hopes.

**Last updated:** 2026-09-14

> Written in English like every document in `docs/`. Conversation is in Hebrew; documentation is not.

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
| D2 | The normalization produces no false collisions | ✅ VERIFIED | No colliding group contains genuinely different posts; no non-colliding pair scores ≥ 0.90 similarity on normalized text, so no expected pair narrowly missed. |
| D3 | Near-duplicate matching (Jaccard over shingles) is **not** required | ✅ VERIFIED | Follows from D1 + D2. This was the one failure mode that would have been a scope change. It did not occur. |
| D4 | The three colliding pairs are the three known duplicate pairs | ✅ VERIFIED | Count verified by script; identity confirmed by Ron on inspection, 2026-09-14. The script was not given the expected `post_id` list and could only verify the count. |
| D5 | Phone numbers are present in only about half of posts | ✅ VERIFIED | 10 of 20 posts contained a phone number. |
| D6 | Phone number cannot serve as a primary dedup key | ✅ VERIFIED | Follows from D5, and from pair 3 below: both posts in that pair have no phone at all. Relying on phone as the key would have missed one of three duplicate pairs. Supersedes the "real primary key of a listing" wording in `HANDOFF.md` §5 — corrected there. |
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
| 2 posts have an empty `media` array | ✅ VERIFIED |
| `topComment` is present on exactly 3 posts despite `includeTopComment: false` | ✅ VERIFIED |
| The sample spans only 2 groups × 10 posts, so "within the same group" and "across groups" coincide for all three duplicate pairs | ✅ VERIFIED |

---

## Normalization choices made in `scratch/dedup_check.py`

Disclosed 2026-09-14. `PHASE_1.md` names this script the starting point for the `textnorm/` module,
so these are contract details, not implementation trivia.

| Choice | Tag | Note |
|---|---|---|
| Lowercases the text | ✅ accepted | Harmless for Hebrew; affects embedded English consistently |
| Strips plain and curly quotes, not only geresh and gershayim | ✅ accepted | Wider than described in `MACRO_PLAN.md` §3, but consistent, which is all hashing needs |
| The "emoji" range also removes arrows (U+2190–21FF) and U+2B00–2BFF symbols | ✅ accepted | Same reasoning |
| The `+972` branch matches mobile numbers only (`+972 5X`) | ⚠️ ASSUMED | Unexercised in the sample. Landline international format would be missed |
| The shared-post fallback triggers on `post_type == "shared"`, not on empty text | ⚠️ **open question** | These are not the same condition. `post_type` is what the provider claims; empty text is what actually happened. Tied to P2, still unverified |

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
| P1 | `postsNewerThan` applies **per group** in a single run with multiple URLs | ⚠️ ASSUMED | Never tested. `maxPosts` is verified per-group; that does not establish the same for the time window. Resolved by task 1.1a. If false: 6 separate runs, one file changes. |
| P1b | `postsNewerThan` accepts **minute** granularity | ✅ VERIFIED | The actor's OpenAPI definition (current build, 2026-09-12) gives the pattern `^\d{4}-\d{2}-\d{2}$\|^(\d+(?:\.\d+)?)\s*(minute\|hour\|day\|week\|month\|year)s?$`. The **absolute** form is date-only — a full ISO datetime is rejected. The **relative** form accepts minutes and decimals (`"45 minutes"`, `"1.5 hours"`). Decision: always send relative minutes, computed as `now - min(watermark) - buffer`. See `DECISIONS.md` #36. |
| P1c | Relative windows are measured from **run start**, not from our calculation | ⚠️ ASSUMED | Follows from the format but unobserved. A delayed run start shifts the window by the delay. The 10–15 min overlap buffer absorbs it — an additional reason not to shrink that buffer. |
| P2 | `sharedPost` content is at `sharedPost.text` | ⚠️ ASSUMED | Zero `post_type: "shared"` posts in the 20-post sample, so the fallback path has never executed. The field name is a guess, verified against neither documentation nor a real response. Resolved in 1.1. |
| P3 | `fetchAllComments` defaults to `true` and bills per result | ✅ VERIFIED | `HANDOFF.md` §4. Always set explicitly to `false`. |
| P4 | `sortingOrder: newest_activity` mixes bumped old posts into the feed | ✅ VERIFIED | `HANDOFF.md` §4. Always `newest_posts`. |
| P5 | Failed or private groups are silent — no diagnostic rows in the dataset | ✅ VERIFIED | `HANDOFF.md` §4. Errors go to the run log only. Zero results and a failure are indistinguishable from the data alone. |
| P6 | Actor pricing is ~$1.50 / 1,000 results | ✅ VERIFIED | Confirmed by Ron, 2026-09-13. The store page header shows "from $1.00 / 1,000 results", which is the **floor** of a tiered per-event scheme, not the working rate; the actor's own description on the same page reads "⚡1.5$". A cached older snapshot of the Input tab shows $3.00. Three numbers, one page — always read the Pricing tab, never the header. |
| P8 | `sortingOrder` has a fourth value, `buy_sell_listings` | ✅ VERIFIED | Full enum: `newest_posts`, `newest_activity`, `most_relevant`, `buy_sell_listings`. Buy/Sell mode **skips ordinary posts**. Not used. Invariant 6 stands. |
| P9 | `includeTopComment` defaults to **`true`** | ✅ VERIFIED | From the OpenAPI definition. This is a second billing-relevant default alongside `fetchAllComments`. `HANDOFF.md` §4 shows it set to `false` in the research input, yet 3 of 20 posts carry a `topComment` — so either the run did not send the flag or the actor ignores it. Establish which in 1.1a; it costs money either way. |
| P10 | `maxPosts` has no maximum in the current schema | ✅ VERIFIED | Default 50, minimum 1, no upper bound. A cached older snapshot claims a maximum of 500. |
| P11 | `topComment` is an array | ❌ FALSE | The README documents an array; the real response carries an object or `null`. Per skill principle P2, the real response wins. |
| P12 | The actor's human-readable **Input tab is stale** | ✅ VERIFIED | It serves an April-2026 snapshot (603 users, 12K runs, $3.00, only `url` / `maxPosts` / `isNewPosts`) while the API pages of the same actor show the current build (4.5K users, 28K runs, modified 2026-09-12). **`/api/openapi` is the source of truth for an Apify actor's input schema**, not the Input tab. |
| P7 | Post volume is ~8 posts/group/day | ⚠️ ASSUMED | Derived from 20 posts over 30.6h across 2 groups. A single window, not a measured rate. The silent-group detection thresholds in Phase 4 depend on this. |

---

## Provider contract — memo23 (backup)

| # | Claim | Tag |
|---|---|---|
| M1 | Field map as recorded in `HANDOFF.md` §4 | ✅ VERIFIED — against real output at research time |
| M2 | Input uses `startUrls`, not `url` | ⚠️ ASSUMED — different from thedoor; re-verify before writing the adapter in Phase 5 |
| M3 | Still available and not under maintenance | ⚠️ ASSUMED — re-check at Phase 5, not now |

---

## Classification

| # | Claim | Tag | Evidence |
|---|---|---|---|
| C1 | Gemini Flash classifies these posts accurately at `temperature=0` | ✅ VERIFIED | 10/10 on real posts including 4 adversarial cases. `HANDOFF.md` §6. |
| C2 | Post #18 (`אנחנו שני שותפים שמחפשים דירת 3 חדרים`) classifies as `seeking` | ❓ UNKNOWN | Never tested. Was previously covered by the deterministic sniper, which is now out of v1. Moves into the Gemini regression set in task 1.4. |
| C3 | `confidence` discriminates usefully | ⚠️ ASSUMED | 0.9 on the sparsest post, 1.0 elsewhere. One data point of variation. |
| C4 | The pydantic-derived JSON schema is accepted by the Gemini structured-output API | ⚠️ ASSUMED | Not every pydantic construct survives the conversion. Verify in 1.4. |
| C5 | `schema.py` and `prompt.py` in `data/raw/` are suitable for production use | ❌ **NO** | They are research artifacts from the initial feasibility test. They proved Gemini works; they were not designed to cover every listing type or the future dashboard facets. **They are input to Gate B and Gate C, never a starting point to be extended silently.** |

---

## Telegram

| # | Claim | Tag |
|---|---|---|
| T1 | Media caption is capped at 1024 characters while posts run to 1,572 | ⚠️ ASSUMED — verify against the Bot API docs in 1.7 |
| T2 | `sendMediaGroup` accepts at most 10 items | ⚠️ ASSUMED — verify in 1.7 |
| T3 | Signed image URLs survive long enough for Telegram to download on send | ✅ VERIFIED — `HANDOFF.md` §3 |

---

## Cost and infrastructure

| # | Claim | Tag |
|---|---|---|
| I1 | Firestore free tier absorbs thousands of rows and 48 runs/day | ⚠️ ASSUMED — measure in Phase 2 |
| I2 | Cloud Run Job + Scheduler at 48 runs/day stays within free tier | ⚠️ ASSUMED — measure in Phase 3 |
| I3 | Gemini Flash cost at ~50 posts/day is negligible | ⚠️ ASSUMED — measure in Phase 3 |

---

## Legal

| # | Claim | Tag |
|---|---|---|
| L1 | Personal, non-commercial collection falls under the §3 exclusion of the Israeli Privacy Protection Law | ⚠️ ASSUMED — `HANDOFF.md` §7. Not legal advice. |
| L2 | The exclusion survives adding a second user | ❓ UNKNOWN — must be decided before a second user exists, not drifted into. See `MACRO_PLAN.md` §9. |

---

## Closed

| Claim | Outcome |
|---|---|
| Near-duplicate matching may be required if hashes do not collide | Closed 2026-09-14. Did not occur — see D1–D3. No scope change. |
| Phone number is the real primary key of a listing | Closed 2026-09-14. **False.** Present in only 50% of posts; absent from both sides of one duplicate pair. Demoted to a one-directional signal. `HANDOFF.md` §5 corrected. |
