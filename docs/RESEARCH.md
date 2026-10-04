# Research

Findings from the research phase and from Phase 0 that still hold: verified facts, provider
details, field map, traps, dedup results, and model test results.

This file records **what was found**. What the system does with it is in `BASELINE.md`; whether a
claim is `VERIFIED`, `ASSUMED` or `UNKNOWN` is tracked in `ASSUMPTIONS.md`; field names and types
are in `SCHEMA.md`.

**Compiled:** 2026-10-03 from `archive/HANDOFF.md` and `archive/MACRO_PLAN.md`, with the
corrections made since (Gate A, task 1.2, Phase 0 build) folded in.
**Updated:** 2026-10-04 with the results of spike 1.1a (`SPIKE_1_1a.md`), the watermark rules
of task 1.13 (`DECISIONS.md` #78), the four real runs that closed phase 1 (§11), and the
candidate sources for Tel Aviv areas and streets (§12).

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
| Post volume | **More than 212 posts in one 24-hour window** (run A, Saturday 12:55 to Sunday 12:55 UTC; Sunday is a working day in Israel), with two groups cut off at `max_posts` 50, and **about 13–15 new posts an hour** on a Sunday afternoon (runs B and D). §11. The spike's ~150/day (Friday night to Saturday) and the research estimate of ~8 posts/group/day were both too low. **One day of data:** the daily figure is not yet measured (`BACKLOG.md`, a week of real runs) |
| Duplicates are severe | 3 duplicate pairs in 20 posts (15%). Two pairs were **within the same group**: different `post_id`, identical text. `post_id` dedup is not sufficient. **The real runs: 39 of 266 stored posts (14.7%) are hash duplicates, 12 of them in the same group as their canonical** (§11) |
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
  "maxPosts": 50,
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
- **One run for all groups.** `postsNewerThan` is one value per run. The run's window starts at
  the last successful run's start minus the buffer, the same for every group, and nothing is
  filtered per group locally (`DECISIONS.md` #78 W1, W6). The window applies per group inside one
  run: verified in spike 1.1a (`ASSUMPTIONS.md` P1, `SPIKE_1_1a.md` Q1).

**Cost, from the real runs (§11).** The rate is confirmed on four runs: $0.0015 per returned row
(rows older than `since` included) and $0.005 per run start. A normal run asks for about 45
minutes (30 plus the 15-minute buffer), so at the afternoon rate it returns about 10–11 rows,
about $0.021. Over a day, 36 runs cost $0.18 in start fees, and each post is billed about 1.5 times
on average (the overlap). At 212 posts a day (the one-day lower bound), that is about 318 rows,
$0.48, **about $0.66/day, about $20/month**; at about 14 new posts an hour for the 18 hours of
runs plus the night, about 300 posts and 450 rows, **about $0.86/day, about $26/month**. Above the
~$12–16/month Ron accepted on 2026-10-04 from the spike's weekend figures. **One day of data**: a
week of real runs measures it (`BACKLOG.md`). Gemini Flash is not included. *The spike's
projection, kept for the record: ~150 posts/day gave ~$12–16/month for one run covering all six
groups and ~$39–43/month for six runs; the earlier "~1,500 posts/month ≈ $2.25" ignored the start
fee and underestimated volume.*

**The projection holds only with a short window.** It assumes each run asks for about 30 minutes
plus the buffer. Under the earlier rule, `min(all watermarks) - buffer` with the watermark as the
highest `posted_at`, every run reached back to the quietest group's last post. Simulated over the
spike control dataset (20 runs every 30 minutes, a 15-minute buffer, the 10.7 hours in which all
six groups are covered, a Saturday): a median window of 26.7 h, about 107 rows per run, the busiest
group at `max_posts` on every run, **about $179/month**. With the window at the last successful
run's start minus the buffer: about 5.8 rows per run, **about $15/month**. Hence `DECISIONS.md`
#78 W1. Billing is per returned result, so `max_posts` (50, #78 W3) costs nothing on a normal run.

---

## 4. Watermark rules

*Amended 2026-10-04 by `DECISIONS.md` #78: the run's window no longer comes from the watermark.*

1. A group's watermark is the **highest `posted_at` seen**, not the run time. It is stored, and it
   never moves backwards, but it does not set the run's window: with one run for all groups, the
   quietest group's last post would set every run's window (§3).
2. **The run's window starts at the last successful run's start** (`last_success_at`, read from
   our clock before `fetch()`), **minus a 15-minute overlap**; dedup absorbs the repeats. Zero
   overlap loses posts silently, and the actor measures the relative window from its own start
   (`ASSUMPTIONS.md` P1c).
3. **Per group**, never global, and never per user.
4. **Advance only on a successful run.** A throttled run that advances the window loses that window
   for good. A failed run writes nothing, so the next window covers it.
5. **A group at `max_posts` still advances.** Posts arrive newest first, so asking for the same
   window again returns the same newest posts; holding the watermark back recovers nothing. The
   group is reported for the run log.
6. **A group that fails inside a successful run advances too.** Nothing in the data tells it apart
   from a quiet group; the run log might (P13, ASSUMED). A known limit.

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
without a post, and the busiest group posts ~73/day while the quietest posts ~4/day. **The real
runs agree:** in run A's 24 hours the groups returned from 7 to 50 posts (two cut off at 50);
`5612809662118963` then returned no row in runs B, C and D, about 4 hours, after 18 posts in A
(§11). A single
threshold for all six groups will either miss failures or flag quiet groups. The run log's
per-group reason may be a better signal than counting zeros.

The counter is `GroupWatermark.consecutive_failures`: consecutive successful runs in which the
group returned zero rows (`DECISIONS.md` #78 W5b). The thresholds are decided in phase 5.

---

## 10. Tools

Python 3.12 · pydantic v2 · uv · ruff · pytest · `google-genai`. The Gemini response schema is
derived from the pydantic model at runtime, never maintained by hand. JSON logs with a `run_id` on
every line.

---

## 11. The real runs that closed phase 1

Four runs on 2026-10-04 from the laptop, through `run_once` (task 1.14). Reports with every figure:
`data/runs/run_A_2026-10-04/` … `run_D_2026-10-04/REPORT.md` (gitignored). **Every figure here is
from one day** (a Sunday, a working day in Israel). A week of real runs is in `BACKLOG.md`.

| Run | What | Rows | New posts | Photos held | Cost (read after the run) |
|---|---|---|---|---|---|
| A | bootstrap, 24 h back | 212 (38, 49, 50, 18, 7, 50) | 212 | 415 (273 failed: the network dropped) | $0.323 |
| B | normal, about 2 h later | 33 | 28 | 94 + 214 retried from stored links (#80) | $0.0545 |
| C | normal, killed in the photo step | 30 | 0 stored | 4 orphan files | $0.05 |
| D | the recovery | 34 (33 kept) | 26 | 95 | $0.056 |

- **Volume.** More than 212 posts in 24 hours: `101875683484689` and `295395253832427` hit
  `max_posts` 50 (their 50 newest covered about 4.7 h and about 19.6 h). New posts in the
  afternoon: 28 in the 1 h 53 min between A's and B's starts, 26 in the 1 h 56 min between B's and
  D's: **about 13–15 an hour**. Per group in 24 hours: 7 to 50+.
- **Duplicates in the store:** 39 of 266 posts (**14.7%**) are hash duplicates of a canonical; 12
  of the 39 are in the same group as their canonical. The 20-post sample's 15% holds.
- **Rejected before the model:** `no_images` 25 of 266 (**9.4%**; 23 of 227 canonicals, 10.1%);
  `no_text` 9 (**3.4%**; 4.0% of canonicals). Pending: 232.
- **Content:** 68 `sale_post` (26%), 35 shared posts (13%), a phone number in 161 (61%).
- **Media:** 973 photos, 17 videos, 8 reels. **Photos per post: 3.66 on average, at most 5**; 231
  of 266 posts have at least one photo, and 134 of the 231 with their own media have exactly 5.
  `photo_count` never exceeds 5 either: whether posts with more photos are cut at 5 by the actor
  is UNKNOWN (`ASSUMPTIONS.md` P21).
- **Photo download, one at a time:** about **1.36 s** per photo in run A, **2.2 s** in run B
  (including 214 stored links), 0.78 s in run D; no 403, 429 or timeout. About 0.147 MB per photo:
  120 MB for 818 photos.
- **Store:** 266 posts and 818 photos in 3.3 MB of SQLite and 120 MB of image files.
- **Network.** Run A's laptop network dropped during the download; 273 photos failed at once.
  #80 now waits on such a drop, and run B recovered all of them from the stored links except 45
  repost photos, which the repost rule never retries.
- **Cost.** $0.0015 per returned row and $0.005 per start, on all four runs; the figure logged at
  the end of a run is preliminary and can miss every row (`ASSUMPTIONS.md` P19). A row older
  than `since` can be returned and is billed (run D). The monthly projection is in §3.

---

## 12. Tel Aviv areas and streets: candidate sources

Research for Gate B (`ASSUMPTIONS.md` A1, `BASELINE.md` §7), 2026-10-04. Read from the sources
themselves; nothing downloaded into the repo. **Not chosen**: Ron chooses at Gate B.

The requirement: a closed list of areas, the Old North split north/south, and the streets of each
area, a street that crosses several areas included, from an existing public source.

| | Municipality open data | Municipality GIS (addresses) | CBS | Population Authority (data.gov.il) | OpenStreetMap |
|---|---|---|---|---|---|
| Publisher | Tel Aviv-Yafo Municipality | Tel Aviv-Yafo Municipality | Central Bureau of Statistics | Population and Immigration Authority | OSM contributors |
| What | `שכונות` (neighbourhoods), `רובעים`, `תת רובעים`, `אזורים סטטיסטיים` datasets; the same names in GIS layer 511 | GIS layer 527 `כתובות`: 52,176 address points, each with a street code, street name and house number | `statistical_areas_2022` polygons: locality, statistical area, quarter, sub-quarter, a function code | The street register: every street of every locality, official name, street code, synonyms | Street geometry; neighbourhood polygons under the municipal names |
| Format | Open-data portal; ArcGIS REST (JSON, GeoJSON) | ArcGIS REST, 2,000 records per request | File Geodatabase | CSV, XML | OSM data (PBF, Overpass, Nominatim) |
| Terms | The portal's licence: "ניתן לשתף את המידע ולעשות בו כל שימוש" provided its conditions are met; as-is, no warranty, no guarantee it stays available; no named licence | **Not on the open-data portal.** The website's terms forbid copying, building a database from the content and automated access; GIS maps fall under them | No terms on the GIS page; not read in the readme | No licence on the dataset (empty field); the portal's general terms not read | ODbL: attribution, and share-alike for a distributed derived database |
| Current | Neighbourhoods loaded 2024-11-18; the service published 2026-08-27 | Same service | 2022 (published 2022-10-02) | Updated weekly, last 2026-10-04 | Live |
| Areas list | **Yes: 71 neighbourhoods** | — | Statistical areas and numbered quarters, no names in the layer | No | Yes, under the municipal names (completeness not counted: Overpass timed out) |
| Old North split | **Yes: `הצפון הישן - החלק הצפוני` (30) and `הצפון הישן-החלק הדרומי` (31)**; the New North in three | — | No | No | Yes: `הצפון הישן - החלק הצפוני` is a polygon (`place=suburb`, way 803404213) |
| Streets per area | **No** | **Derivable**: each address point placed in a neighbourhood polygon gives the streets of each area, with house-number ranges; a street that crosses areas appears in each | Main streets only, in a separate key file (`שיוך הרחובות העיקריים והשכונות לכל אזור סטטיסטי`), not read | No | **Derivable**: street lines placed against neighbourhood polygons |
| Missing | Streets | An open licence | Area names; all streets | Geometry, areas | A count of its neighbourhoods; house numbers are sparse in OSM (not checked) |

Also seen, not candidates: Hebrew Wikipedia defines the Old North as municipal quarter 3 by its
boundary streets, with no internal split and no streets per part. Real-estate sites (Madlan, ad.co.il)
use the municipal names but a **four-part** Old North (`החלק המרכזי` among them) and publish street
lists per neighbourhood; commercial, terms not read. The municipality's GIS layer 510
(`רובעים-למס`) is a tax zoning of 15 numbered zones, not the CBS quarters.

**No single public source covers the requirement.** What would:
1. **The areas and the Old North split:** the municipality's `שכונות` open dataset, 71
   neighbourhoods, under the portal's licence.
2. **Streets per area, derived** by placing streets in those polygons, from one of:
   - OpenStreetMap streets: an open licence (ODbL; attribution, share-alike if distributed). OSM's
     completeness for Tel Aviv was not measured.
   - The municipality's address layer: complete, with house numbers, but outside the open-data
     licence; using it needs the municipality's permission or Ron's reading of its terms.
3. **Street names as posts write them:** the Population Authority's register with synonyms, for
   matching spellings to a street.

**For Ron to decide:** which of these; whether 71 neighbourhoods is the closed list or they are
grouped (for example, by quarter); whether the municipality's two-part Old North is the split
(Madlan's is four); how a derived street table is kept current; and, for the address layer, its
terms.
