# Assumptions Register

**Purpose:** every external contract detail and every empirical claim this project relies on,
tagged `VERIFIED`, `ASSUMED`, or `UNKNOWN`.

**The rule:** nothing moves to implementation while resting on `ASSUMED`. If an `ASSUMED` item
blocks progress, the next step is a spike that resolves it — not code that hopes.

**Last updated:** 2026-10-04 — P1b and P1c wording: the window formula and the buffer of `DECISIONS.md` #78, task 1.13; no status changed. Earlier the same day: I6 extended and I9–I11 added, task 1.12 download check. Earlier the same day: P15–P19 added and P6 corrected, task 1.1. Earlier the same day: I8 (SQLite version in the container) added, task 1.10. Earlier the
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
| D2 | The normalization produces no false collisions | ✅ VERIFIED | No colliding group contains genuinely different posts; no non-colliding pair scores ≥ 0.90 similarity on normalized text, so no expected pair narrowly missed. |
| D3 | Near-duplicate matching (Jaccard over shingles) is **not** required | ✅ VERIFIED | Follows from D1 + D2. This was the one failure mode that would have been a scope change. It did not occur. |
| D4 | The three colliding pairs are the three known duplicate pairs | ✅ VERIFIED | Count verified by script; identity confirmed by Ron on inspection, 2026-09-14. The script was not given the expected `post_id` list and could only verify the count. |
| D5 | Phone numbers are present in only about half of posts | ✅ VERIFIED | 10 of 20 posts contained a phone number. |
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
| P1c | Relative windows are measured from **run start**, not from our calculation | ⚠️ ASSUMED | **Observed 2026-10-04** in the spike 1.1a log: the cutoff was the actor's own start minus the window (≈1 s after Apify's `startedAt`). Not stated in the documentation, so it stays ASSUMED by the tag rule. A delayed run start shifts the window by the delay; the overlap buffer (15 minutes, `DECISIONS.md` #78 W2) absorbs it — an additional reason not to shrink that buffer. |
| P2 | `sharedPost` content is at `sharedPost.text` | ✅ VERIFIED | 2026-10-04, spike 1.1a: shared text at `sharedPost.text`, images at `sharedPost.media`, 19 of 19 rows. `sharedPost.time` is `null` on all 19. `post_type` values `shared_reel` and `__reel__` can also carry a `sharedPost`. `SPIKE_1_1a.md` Q6. |
| P3 | `fetchAllComments` defaults to **`false`** | ✅ VERIFIED | Changed: the OpenAPI definition of build 1.0.195 (2026-10-03) gives `"default": false`; it was `true`. Still always sent explicitly as `false`. `SPIKE_1_1a.md` Q3. |
| P4 | `sortingOrder: newest_activity` mixes bumped old posts into the feed | ✅ VERIFIED | `RESEARCH.md` §2. Always `newest_posts`. |
| P5 | Failed or private groups are silent — no diagnostic rows in the dataset | ✅ VERIFIED | `RESEARCH.md` §2. Errors go to the run log only. Zero results and a failure are indistinguishable from the data alone. **The run log carries per-group status** (`Posts: N \| Reason: …`, `Successful groups: x/6`), seen 2026-10-04 in spike 1.1a. |
| P6 | Actor pricing is ~$1.50 / 1,000 results | ✅ VERIFIED | **Real bill, 2026-10-04 (spike 1.1a):** $0.0015 per result, $0.005 per start event, one start event per run at 1 GB. Results charged were first read as fewer than rows returned (99/105, 165/180); that was a preliminary figure, see P19. Confirmed by Ron, 2026-09-13. The store page header shows "from $1.00 / 1,000 results", which is the **floor** of a tiered per-event scheme, not the working rate; the actor's own description on the same page reads "⚡1.5$". A cached older snapshot of the Input tab shows $3.00. Three numbers, one page — always read the Pricing tab, never the header. |
| P8 | `sortingOrder` has a fourth value, `buy_sell_listings` | ✅ VERIFIED | Full enum: `newest_posts`, `newest_activity`, `most_relevant`, `buy_sell_listings`. Buy/Sell mode **skips ordinary posts**. Not used. Invariant 6 stands. |
| P9 | `includeTopComment` defaults to **`true`**, and `false` suppresses `topComment` | ✅ VERIFIED | Default from the OpenAPI definition. Suppression verified 2026-10-04, spike 1.1a: the flag is in both runs' stored input, and 0 of 285 rows carry a non-null `topComment` (the key stays, as `null`). The research run's 3 of 20 remain unexplained, most likely the flag was not sent then. `SPIKE_1_1a.md` Q3. |
| P10 | `maxPosts` has no maximum in the current schema | ✅ VERIFIED | Default 50, minimum 1, no upper bound. A cached older snapshot claims a maximum of 500. |
| P11 | `topComment` is an array | ❌ FALSE | The README documents an array; the real response carries an object or `null`. Per skill principle P2, the real response wins. |
| P12 | The actor's human-readable **Input tab is stale** | ✅ VERIFIED | It serves an April-2026 snapshot (603 users, 12K runs, $3.00, only `url` / `maxPosts` / `isNewPosts`) while the API pages of the same actor show the current build (4.5K users, 28K runs, modified 2026-09-12). **`/api/openapi` is the source of truth for an Apify actor's input schema**, not the Input tab. |
| P13 | The run log's per-group status lines are stable enough to rely on for silent-group detection | ⚠️ ASSUMED | Seen in two runs, 2026-10-04. The log format is not a documented contract. |
| P14 | `Photo` media items can also lack `width`/`height` | ✅ VERIFIED | 2026-10-04, spike 1.1a: 9 `Photo` and 11 `Video` items without the keys. Until then only videos were known to omit them. |
| P7 | Post volume is **~150 posts/day across the six groups** | ⚠️ ASSUMED | Measured 2026-10-04 (spike 1.1a): 75 posts in a 24-hour window from five groups, plus ~73/day for `101875683484689`, which hit `maxPosts`. Per group from ~4/day to ~73/day. One window, Friday night to Saturday; a weekday may be higher. Replaces the research estimate of ~8 posts/group/day. The silent-group detection thresholds depend on this (`RESEARCH.md` §9); runs skipped in the quiet hours do not count toward them. |
| P15 | What `run-sync-get-dataset-items` returns when the run fails, is aborted or hits the charge cap | ❓ UNKNOWN | Not documented in the Apify API spec `v2-2026-10-01T153946Z`. The spec documents no run-ID header on the sync response, a 408 after 300 s, and "if the connection breaks, you will not receive any information about the run". Not used: `fetch()` uses the regular call (`DECISIONS.md` #71 A). |
| P16 | A shared post with its own caption: its `text` is the caption, and `sharedPost.text` (the shared listing) does not reach the model | ✅ VERIFIED (known gap) | 1 of the 15 shared posts in spike 1.1a run 1. Gate A as approved: `text` falls back to `sharedPost.text` only when the post's own text is blank. Media still falls back. Kept as is by Ron (`DECISIONS.md` #71 H); for Gate B (`BACKLOG.md`). |
| P17 | What a run does when it reaches `maxTotalChargeUsd` (final status, partial dataset) | ❓ UNKNOWN | Not documented. What is verified: the platform sets the run's `options.maxItems` from the cap (333 at $0.50, spike 1.1a). `fetch()` treats rows returned ≥ `options.maxItems` as a failed run (`DECISIONS.md` #71). |
| P18 | `POST /v2/actor-runs/{runId}/abort` stops a running run | ⚠️ ASSUMED | Documented in the Apify API spec. **Path, auth and response shape VERIFIED 2026-10-04** by one no-op call on the finished spike run `GcarNt1rhe8tuSDuV` (Ron's choice, no actor run): HTTP 200, the run object under `data`, status still `SUCCEEDED`. Saved as `data/raw/apify_abort_noop_2026-10-04.json`. Stopping a *running* run has not been observed. `fetch()` raises after the abort whatever it returns, so a failed abort costs money (up to the cap), never a watermark. |
| P19 | Run cost read at the end of a run is final | ❌ FALSE | Read again on 2026-10-04, run 1 shows 105 results charged and $0.1625; at the end of the run it showed 99 and $0.1535. The "results charged fewer than rows returned" in spike 1.1a was a preliminary figure, as the API spec warns. The control run was not re-read. `fetch()` logs the end-of-run figure anyway (`DECISIONS.md` #71); the monthly projection already priced every row. |

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
| C3 | `confidence` discriminates usefully | ⚠️ ASSUMED | 0.9 on the sparsest post, 1.0 elsewhere. One data point of variation. |
| C4 | The pydantic-derived JSON schema is accepted by the Gemini structured-output API | ⚠️ ASSUMED | Not every pydantic construct survives the conversion. Verify in phase 2. |
| C5 | `schema.py` and `prompt.py` in `data/raw/` are suitable for production use | ❌ **NO** | They are research artifacts from the initial feasibility test. They proved Gemini works; they were not designed to cover every listing type or the future dashboard facets. **They are input to Gate B and Gate C, never a starting point to be extended silently.** |

---

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
| I3 | Gemini Flash cost at ~150 posts/day is negligible | ⚠️ ASSUMED — measure in phase 2 |
| I4 | Tailscale Serve publishes a local service over HTTPS to the tailnet only, and device sharing gives an outside Tailscale user access to one machine | ✅ VERIFIED — Tailscale docs, read 2026-10-02 |
| I5 | Device sharing covers the number of friends on the free plan | ❓ UNKNOWN — check before phase 5 |
| I6 | Images can be downloaded from the signed Facebook links at fetch time | ✅ VERIFIED — 2026-10-04, spike 1.1a: 5 of 5, plain GET with no token or cookies, HTTP 200, JPEG. Task 1.12 check, the same day, about 8.5 hours after the control run: 632 of 632 photo links of the control dataset, HTTP 200, `image/jpeg`, JPEG bytes, 10 KB – 591 KB (`data/raw/spike_1_12_images_2026-10-04/REPORT.md`). From the laptop only; the home server is unverified |
| I9 | The extension in a photo link's path says what is served | ❌ FALSE — 2026-10-04, task 1.12 check: the 57 `.png` and 20 `.webp` links served JPEG with `image/jpeg`. The downloader reads the type from the bytes (`DECISIONS.md` #77 D1) |
| I10 | A photo link downloads without a `User-Agent` header | ✅ VERIFIED for 5 links — 2026-10-04, task 1.12 check: one `.jpg`, one `.png`, one `.webp` and two more `.jpg`, all HTTP 200 and JPEG. The header is sent anyway (`DECISIONS.md` #77 D5c) |
| I11 | Downloading a bootstrap run's photos one at a time is not throttled, and takes about 1.6 s per photo | ✅ VERIFIED from the laptop — 2026-10-04, task 1.12 check: 632 links in 1,010 s, no 403, 429 or timeout; median 1.77 s for `.jpg`, at most 2.97 s. Concurrent requests and the home server: not tried |
| I7 | Signed image links expire ≈ 4.4 days after fetch | ⚠️ ASSUMED — read from the `oe` query parameter as a hex Unix timestamp (4.3–4.5 days on all 355 links in run 1). That reading is not documented; nothing was re-downloaded later |
| I8 | The home-server container's SQLite is at least 3.24.0, the minimum the store and state modules require (`DECISIONS.md` #65) | ❓ UNKNOWN — checked when the image is built (phase 5). Ron's laptop: Python 3.12.9 with SQLite 3.45.3, run 2026-10-04. Below the minimum, both modules refuse to start and name the found and required versions |

---

## Location

| # | Claim | Tag |
|---|---|---|
| A1 | A public source lists Tel Aviv areas and the streets in each, including a north/south split of the Old North | ❓ UNKNOWN — Ron expects one exists. Find and verify before Gate B |

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
