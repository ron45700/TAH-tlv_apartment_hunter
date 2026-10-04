# Research

Findings from the research phase and from Phase 0 that still hold: verified facts, provider
details, field map, traps, dedup results, and model test results.

This file records **what was found**. What the system does with it is in `BASELINE.md`; whether a
claim is `VERIFIED`, `ASSUMED` or `UNKNOWN` is tracked in `ASSUMPTIONS.md`; field names and types
are in `SCHEMA.md`.

**Compiled:** 2026-10-03 from `archive/HANDOFF.md` and `archive/MACRO_PLAN.md`, with the
corrections made since (Gate A, task 1.2, Phase 0 build) folded in.
**Updated:** 2026-10-04 with the results of spike 1.1a (`SPIKE_1_1a.md`).

---

## 1. Verified facts

All verified against a real 20-post run on 2026-09-13 (cost: under $0.10).

| Fact | Evidence |
|---|---|
| The Facebook Graph Groups API is dead | Removed 2026-04-22 across all API versions. No sanctioned path exists |
| Public group posts are readable logged out | Meta's Nov-2025 change; both actors return data with no cookies |
| Hebrew post text arrives complete | 108–1,572 chars, all end naturally. No truncation, no "See more" |
| `creation_time` parses cleanly | 20/20 with `email.utils.parsedate_to_datetime` (thedoor, RFC 2822 GMT) |
| Images are available | 18/20 posts, 82 items. thedoor `media[].uri` at `mx1200x1600`. 2 posts had no media at all |
| Image URLs expire within days | Signed `scontent.*.fbcdn.net` links. Images must be downloaded at fetch time |
| Post volume | **Measured 2026-10-04 (spike 1.1a): ~150 posts/day across the six groups**, from ~4/day (`733810383372996`) to ~73/day (`101875683484689`). Not ~48: the research estimate (20 posts over 30.6h across 2 groups ≈ 8 posts/group/day) was about 3× too low. The measured window was Friday night to Saturday; a weekday may be higher |
| Duplicates are severe | 3 duplicate pairs in 20 posts (15%). Two pairs were **within the same group**: different `post_id`, identical text. `post_id` dedup is not sufficient |
| `sale_post` means **rental**, not sale | 8/20 flagged. Titles: `להשכרה 3 חדרים`, `Room Only`. Rejecting on post type would lose 40% of the data |
| Structured listings carry a price | thedoor: `sale_post.price` / `title` / `location`. memo23: `marketplacePrice`. `sale_post.price` is a **string with a currency symbol** (`"₪3,600"`) |
| Model price equals native price | Two independent sources agreed exactly on both structured posts (₪3,560 / ₪8,700) |
| `user.id` is not a usable identity | Mostly a rotating `pfbid…`, sometimes a plain numeric ID with a real profile URL. No way to tell in advance. Never a key |
| The marketplace flag is `sale_post.isOnMarketplace` | It was `false` on a structured `sale_post` that had a price and a location. "Structured listing" and "on Marketplace" are different things |
| Gemini classification accuracy | 10/10 on real posts, including 4 deliberately adversarial cases. See §7 |

---

## 2. Providers

### Primary: `thedoor/facebook-group-post-scraper`
~$1.50 / 1,000 results.

```json
{
  "url": ["https://www.facebook.com/groups/XXXX/"],
  "maxPosts": 30,
  "sortingOrder": "newest_posts",
  "fetchAllComments": false,
  "includeTopComment": false
}
```

- `maxPosts` is **per group**, not total. Default 50, no maximum.
- `sortingOrder` must be `newest_posts`. **Never `newest_activity`**: it mixes old bumped posts
  into the feed, which breaks both the date filter and the watermark. `buy_sell_listings` skips
  ordinary posts and is not used.
- `postsNewerThan` is always sent as **relative minutes** (`"90 minutes"`). The absolute form is
  date-only and would cap the watermark at one day. Relative is measured from run start.
- `includeTopComment` **defaults to `true`**; `fetchAllComments` defaults to `false` since build
  1.0.195 (2026-10-03; it was `true`). Both are always set to `false` explicitly. With
  `includeTopComment=false`, `topComment` is present on every row as `null`.
- **No diagnostic rows.** Private or failed groups are silent in the dataset; errors go to the run
  log only. "Group returned nothing" has to be detected on our side. **The run log does carry
  per-group diagnostics:** a line per group `done … | Posts: N | Reason: time_frame_reached` or
  `target_reached`, transient `Proxy/session error … blocked` lines, and a final
  `Successful groups: x/6`. The log format is undocumented (`ASSUMPTIONS.md` P13).
- `post_type: "shared"` arrives with empty `text`; the real content sits in `sharedPost`: text at
  `sharedPost.text`, images at `sharedPost.media` (verified 2026-10-04, 19 of 19). `post_type`
  values `shared_reel` and `__reel__` also exist and can carry a `sharedPost`. Media items can
  have `type: "Reel"`.
- **Memory:** the actor sets its own default, `min(4096, (floor(url.length / 40) + 1) * 1024)` MB:
  1 GB for under 40 URLs. One start event per run.
- `topComment` is documented as an array; the real response carries an object or `null`.
- The actor's human-readable Input tab is stale. **`/api/openapi` is the source of truth** for its
  input schema.

### Backup: `memo23/facebook-public-group-posts-scraper`
$1.50/1K + $0.10/1K additional + $0.008 per start. Verified working on the same groups at research
time. Loses `title`, `location` and image resolution. Its input field is `startUrls`, not `url`.

### Field map

| Canonical | thedoor | memo23 |
|---|---|---|
| `source_post_id` | `post_id` | `legacyId` (`id` is base64) |
| `permalink` | `post_url` | `url` |
| `text` | `text` | `text` |
| `posted_at` | `creation_time`, RFC 2822, `parsedate_to_datetime` | `time`, ISO, `fromisoformat` |
| `group_id` | `group_id` | `facebookId` |
| `group_title` | not provided | `groupTitle` (often empty, HTML-escaped) |
| images | `media[].uri` (mx1200x1600) | `attachments[].thumbnail` (s590x590) |
| listing price | `sale_post.price` | `marketplacePrice` |
| listing title | `sale_post.title` | not provided |
| listing location | `sale_post.location` | not provided |

Both providers' post IDs are Facebook's own post ID, so the same post carries the same number from
either one.

### Media items
`Video` items omit the `width` and `height` keys entirely (they are not `null`), carry an extra
`thumbnail` key, and their page link is a `/videos/` page rather than `photo/?fbid=`. Some `Photo`
items omit `width` and `height` too (9 in spike 1.1a), so the keys are never assumed present.

### Groups (all public, verified)
```
35819517694        (דירות מפה לאוזן בת"א)
333022240594651
101875683484689
5612809662118963
733810383372996
295395253832427
```

### Rejected providers
- `apify/facebook-groups-scraper`: official and well built, but ~$5/1K.
- `bombi_carl/crazy-cheap-facebook-group-posts`: $0.10/1K but marked "Under maintenance", untouched
  for 6 months.
- `dami_studio/facebook-groups-scraper`: relies on a shared Facebook session baked into the actor.
  It was blocked during this project, which is what proved the adapter layer necessary.

---

## 3. Apify call shape

- **API paths:** the Apify API spec (`v2-2026-10-01`) lists `/v2/actors/…`; the older
  `/v2/acts/…` form still answers.
- **The regular (non-sync) call**, not webhooks (`DECISIONS.md` #71): start the run, poll it to a
  terminal status, read the dataset. The run ID gives the status, cost and log: the run object
  carries `usageTotalUsd` and `chargedEventCounts` (preliminary right after the run ends,
  `ASSUMPTIONS.md` P19). The sync call (`run-sync-get-dataset-items`) is not used: it returns no
  run ID. `maxTotalChargeUsd` caps the cost of a run.
- **Our scheduler, not Apify's.** Apify's scheduler injects static input; `postsNewerThan` changes
  every run.
- **One run for all groups.** `postsNewerThan` is one value per run while the watermark is per
  group, so the run uses `min(all watermarks) - buffer` and the result is filtered per group
  locally. The window applies per group inside one run: verified in spike 1.1a
  (`ASSUMPTIONS.md` P1, `SPIKE_1_1a.md` Q1).

Expected cost (from spike 1.1a, `SPIKE_1_1a.md`): 36 runs/day, ~150 posts/day, $0.0015 per
result and $0.005 per run start. **One run covering all 6 groups: ~$12–16/month**; six separate
runs: ~$39–43/month. **Accepted by Ron, 2026-10-04.** The earlier "~1,500 posts/month ≈ $2.25"
ignored the start fee and underestimated volume. Gemini Flash is not included.

---

## 4. Watermark rules

1. The watermark is the **highest `posted_at` seen**, not the run time.
2. Always subtract a **10–15 minute overlap**; dedup absorbs the repeats. Zero overlap loses posts
   silently.
3. **Per group**, never global, and never per user.
4. **Advance only on a successful run.** A throttled run that advances the window loses that window
   for good.

---

## 5. Two kinds of normalization

**Provider normalization** lives inside the adapter. It converts one provider's JSON into a uniform
`RawPost`. It is the only code that knows which provider the data came from. `raw` is kept whole.

**Text normalization** sits between `RawPost` and dedup, and nowhere else. It produces a string for
hashing, so that two posts with the same content but different nikud, quote marks, whitespace or
emoji produce the same hash. It is aggressive on purpose. Its output is never stored, never
displayed, and never sent to the model.

---

## 6. Dedup findings

Task 1.2, run 2026-09-14 against the 20-post sample.

- 17 distinct hashes from 20 posts; exactly 3 colliding pairs, matching the 3 known duplicates. No
  false collisions; no non-colliding pair above 0.90 similarity. Near-duplicate matching is not
  needed.
- Phone numbers appear in only **10 of 20** posts. In one of the three duplicate pairs neither post
  has a phone. A shared phone is strong evidence of the same listing; a missing or differing phone
  carries no information.
- The poster's name and `user.id` are never part of the hash: the same apartment posted by two
  different flatmates must still collide.
- Dedup must compare **within the current batch and against history**. Both same-group duplicates
  in the sample appeared in the same window.

| Layer | Stage | Role |
|---|---|---|
| 1. Post ID | A, before the model | Exact repeats, chiefly the watermark overlap |
| 2. Hash of normalized text | A | The primary key. Caught 3/3 pairs |
| 3. Phone | A | One-directional signal only |
| 4. Price + rooms + street | B, after the model | The same apartment reposted with rewritten text. Carries real weight, because phone covers only half of posts |

A sent-alert record per user and post is a separate safety net: even if every dedup layer misses,
the same post is never alerted twice.

---

## 7. Model test results

Gemini Flash, `temperature=0`, structured output. 10/10 on real posts.

| Case | Expected | Got |
|---|---|---|
| `מחפשים שותף/ה` | any gender | correct |
| `מחפש שותף/שותפה` | any gender | correct |
| `עדיפות לבנות` | women preferred, not women only | correct |
| `סבלט ארוך` + room | room in a shared flat **and** sublet | correct |
| Arlozorov + `צפון חדש` | new north, not old north | correct |
| `3,333` suspicious price | literal from the text | correct, not a hallucination |
| No broker signal | broker: not written | correct, did not guess |

Kind and sublet were separate fields in the research schema, forced by real data: a long sublet of a
room is both at once.

### Known prompt issues
1. Entry date sometimes came back as `"immediate"` instead of the Hebrew as written.
2. One case inferred a living room from apartment size with no textual basis. Isolated, but the
   never-invent rule should be tightened.

### Never tested
`אנחנו שני שותפים שמחפשים דירת 3 חדרים` should classify as **seeking**. This matters more now,
because "seeking" is a rejection reason.

The research schema and prompt in `data/raw/` proved that Gemini works. They are input to Gate B,
never a starting point to be extended silently.

---

## 8. Hebrew traps

1. In anything a user reads, never fold final letter forms and never strip `/`. `מחפשים שותף/ה`
   turns into `מחפשים שותפה` and reads as a different post. Hash normalization is exempt and folds
   on purpose.
2. Negation: `לא סאבלט` is not a sublet.
3. A nearby city used as a landmark (`5 דקות מגבעתיים`) in a Tel Aviv flat is not another city.
4. A post that says "we are two" can be a seeking post, not an offer.

---

## 9. Silent-group detection

The provider returns no diagnostic rows, so a private group and a group with no new posts look
identical. Working rule from the measured ~8 posts/group/day: a group returning zero for 8
consecutive runs is marked suspect in the digest; 48 consecutive runs raises an alert. The
thresholds are `ASSUMED` and get calibrated against a week of real data. Runs skipped during the
quiet hours do not count.

**These thresholds need recalibrating (spike 1.1a, 2026-10-04).** A live group went 31 hours
without a post, and the busiest group posts ~73/day while the quietest posts ~4/day. A single
threshold for all six groups will either miss failures or flag quiet groups. The run log's
per-group reason may be a better signal than counting zeros.

---

## 10. Tools

Python 3.12 · pydantic v2 · uv · ruff · pytest · `google-genai`. The Gemini response schema is
derived from the pydantic model at runtime, never maintained by hand. JSON logs with a `run_id` on
every line.
