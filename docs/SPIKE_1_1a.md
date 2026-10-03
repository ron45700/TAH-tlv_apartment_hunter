# Spike 1.1a — one real run against all six groups

**Date:** 2026-10-04 (runs started 2026-10-03 21:32 UTC, 00:32 Israel time)
**Task:** `PHASE_1.md` 1.1a · **Approved by Ron:** run 1 plus a control run, `maxTotalChargeUsd` $0.50 each.

**Result: the time window applies per group. Task 1.1 can be written as planned (one run for all
six groups).**

This report contains no phone numbers, poster names or profile links. Groups are named by ID.

---

## Runs

| | Run 1 (windowed) | Control |
|---|---|---|
| Run ID | `GcarNt1rhe8tuSDuV` | `9TShaAS1e6c2fv56t` |
| Started (UTC) | 2026-10-03T21:32:06Z | 2026-10-03T21:32:45Z |
| Status | `SUCCEEDED` | `SUCCEEDED` |
| Input difference | `postsNewerThan: "1440 minutes"` | no `postsNewerThan` |
| Rows returned | 105 | 180 |
| Real cost | **$0.1535** | **$0.2525** |
| Memory the run got | 1024 MB | 1024 MB |
| Runtime | 31 s | 28 s |

Common input, read back from each run's stored `INPUT` record (so the flags are proven sent, not
just intended):

```json
{
  "url": ["https://www.facebook.com/groups/<id>/", "… one per group, 6 in all"],
  "maxPosts": 30,
  "sortingOrder": "newest_posts",
  "fetchAllComments": false,
  "includeTopComment": false
}
```

Build: `1.0.195` (`hePeml26EwGHFdamf`), finished 2026-10-03 02:57 UTC — the actor was rebuilt the
day before this spike. Contract read before the runs from the build's OpenAPI definition and the
Apify API spec `v2-2026-10-01T153946Z`.

Raw files (gitignored), in `data/raw/`:

| File | Content |
|---|---|
| `thedoor_spike_1_1a_2026-10-04.json` | Run 1 dataset, whole and untouched. **The fixture for task 1.1** |
| `thedoor_spike_1_1a_2026-10-04_control.json` | Control dataset |
| `…_run.json`, `…_input.json`, `…_log.txt` | Run object, stored input, run log (each run; `_control` suffix for the control) |
| `thedoor_spike_1_1a_2026-10-04_analysis.json` | Per-group comparison |
| `spike_1_1a_images_2026-10-04/` | The 5 downloaded images and `results.json` |

Script: `scratch/spike_1_1a.py` (gitignored, throwaway).

### Rows per group

"Stop reason" is read from the run log of run 1. "Control in window" counts control posts with
`posted_at` ≥ run 1's cutoff **and earlier than run 1's start**, so a post published between the
two runs cannot appear as a false mismatch.

| Group | Run 1 rows | Run 1 stop reason (log) | Control rows | Control in window | Same post IDs |
|---|---|---|---|---|---|
| 35819517694 | 22 | `time_frame_reached`, 2 older skipped | 30 | 22 | ✅ |
| 333022240594651 | 17 | `time_frame_reached`, 1 older skipped | 30 | 17 | ✅ |
| 101875683484689 | 30 | `target_reached` (hit `maxPosts`) | 30 | 30 | ✅ — not a test of the window, see Q1 |
| 5612809662118963 | **0** | `time_frame_reached`, 3 older skipped | 30 | 0 | ✅ |
| 733810383372996 | 8 | `time_frame_reached`, 1 older skipped | 30 | 8 | ✅ |
| 295395253832427 | 28 | `time_frame_reached`, 2 older skipped | 30 | 28 | ✅ |
| **Total** | **105** | | **180** | **105** | |

No post in run 1 is older than its cutoff. No group ID outside the six appeared. No post ID repeats
within a group.

---

## The six questions

### Q1 — Does the time window apply per group, or globally? **VERIFIED: per group**

- The run log shows one cutoff, `2026-10-02T21:32:07Z` (actor start − 1440 minutes), applied by
  each group's client **independently**: five groups each stopped with `time_frame_reached` at
  different counts (22, 17, 0, 8, 28), and the sixth stopped on its own `maxPosts` target.
  A global window would not let one group stop at 0 while another went on to 30.
- Against the control, the five window-bound groups match **exactly**: the same post IDs, none
  missing, none extra. No group was cut short.
- Group 101875683484689 posted 30 times in the 10.7 hours before the run, so it hit `maxPosts`
  inside the window in both runs. It confirms nothing about the window by itself, and contradicts
  nothing.
- The relative window is measured from the actor's own start (≈1 s after Apify's `startedAt`),
  consistent with `DECISIONS.md` #36.

**`maxPosts` applies per group, not per run — VERIFIED again.** The control returned 30 for every
group, 180 in total; the log shows `target: 30` per group client.

### Q2 — Do all six groups return data, or is one silently empty? **VERIFIED: all six are reachable**

- In run 1, group 5612809662118963 returned **zero rows**. In the dataset alone this is
  indistinguishable from a failure. It was not a failure: the control returned 30 posts for it,
  the newest from 2026-10-02 14:19 UTC — 31 hours before the run — and the run 1 log says
  `Posts: 0 | Reason: time_frame_reached | skippedOlderPosts=3`. The group was simply quiet.
- **The dataset is still silent (P5 holds), but the run log is not.** It carries, per group: a
  start line, `done … | Posts: N | Reason: time_frame_reached | target_reached`, and a final
  `Successful groups: 6/6`. The control log also shows two transient
  `Proxy/session error … blocked` lines; both groups recovered and returned 30.
  This is a usable signal for silent-group detection, but the log format is not a documented
  contract: **ASSUMED** as a signal source until it is seen to stay stable.
- A 31-hour gap in a live group means "zero rows for 8 consecutive runs" (`RESEARCH.md` §9) would
  flag a healthy group as suspect.

### Q3 — Does `includeTopComment=false` suppress `topComment`? **VERIFIED: yes**

- The stored `INPUT` of both runs shows `includeTopComment: false`.
- 0 of 285 rows (105 + 180) carry a non-null `topComment`. The key is still present, as `null`,
  on every row.
- The log reports `Comments fetched: 0 root + 0 replies = 0 total`.
- The research run's 3 of 20 posts with a `topComment` remain unexplained; the most likely reading
  is that the flag was not actually sent then. It does not matter now: the flag works.

**Contract change found: `fetchAllComments` now defaults to `false`.** The build's OpenAPI
definition gives `"default": false`. `CLAUDE.md` invariant 7 and `RESEARCH.md` §2 say it defaults
to `true`. `includeTopComment` still defaults to `true`. Both are sent as `false` explicitly
regardless, so nothing breaks; the documents are stale. `CLAUDE.md` was not edited.

### Q4 — What did the run really cost? **VERIFIED**

See the cost section below. Run 1: $0.1535. Control: $0.2525. Spike total: **$0.4060**.

### Q5 — Can images be downloaded from the returned links? **VERIFIED for download at fetch time**

- 5 images, the first photo of a post in 5 different groups, fetched minutes after the run with a
  plain GET: no token, no cookies, no login.
- 5 of 5: HTTP 200, `Content-Type: image/jpeg`, bytes start with the JPEG signature. Sizes
  42 KB – 570 KB.
- **How long the links live: ASSUMED ≈ 4.4 days.** Every one of the 355 media links in run 1
  carries an `oe` query parameter. Read as a hex Unix timestamp, it gives expiry 4.3–4.5 days after
  the run. That reading of `oe` is not documented anywhere we have checked; it agrees with "expire
  within days" (`CLAUDE.md`). Nothing was re-downloaded later to confirm it.

### Q6 — Where does a shared post's text and images sit? **VERIFIED**

19 rows across both runs carry a `sharedPost` (17 `shared`, 1 `shared_reel`, 1 `__reel__`).

| What | Where | Observed |
|---|---|---|
| The post's own text | `text` | empty in 18 of 19; one shared post carries its own caption |
| The shared content's text | **`sharedPost.text`** | non-empty in 19 of 19 |
| The post's own images | `media` | empty in 19 of 19 |
| The shared content's images | **`sharedPost.media`** | non-empty in 19 of 19 (62 `Photo`, 2 `Reel`, 1 `Video`) |
| Shared media item keys | `type`, `uri`, `id`, `url` | no `width` / `height` |
| `sharedPost.time`, `sharedPost.timestamp` | — | `null` in 19 of 19 |

`sharedPost` keys, identical on all 19: `id`, `media`, `pageName`, `paidPartnership`, `text`,
`time`, `timestamp`, `url`, `user`. Both `sharedPost.user` and `sharedPost.pageName` hold a person
or page identity.

Consequences, for task 1.1 and Gate E to decide, not decided here:
- `post_type` is not the only marker: `shared_reel` and `__reel__` can also carry a `sharedPost`.
  Testing `sharedPost is not None` catches all 19.
- The current mapper refuses every shared row (`UnverifiedSharedPostError`), 34 rows across both
  runs, as designed. It mapped all 251 other rows without error.
- Of the 41 rows with an empty `media`, 19 have their images in `sharedPost.media`; 22 have no
  images anywhere. This is the shared-post question Gate E has to settle for the no-images rule.

---

## Response shape compared with the 2026-09-13 fixture

| Change | Detail |
|---|---|
| Keys removed | `actors`, `text_preview` |
| Keys added | `creation_timestamp`, `feedback_id`, `photo_count`, `topReactionsCount`, `reactionLikeCount`, `reactionLoveCount`, `reactionCareCount`, `reactionHahaCount`, `reactionSadCount`, `user_url` |
| New `post_type` values | `shared_reel`, `__reel__` (alongside `regular`, `sale_post`, `shared`) |
| New media `type` | `Reel`. Video items now carry a `thumbnail` key |
| Media without `width`/`height` | 11 `Video` **and 9 `Photo`** items. Until now only videos were known to omit them |
| Key set per row | identical on all 285 rows |

The mapper does not read either removed key. `raw` keeps the added ones.

Also observed: `user.id` was `pfbid…` on 106 rows and numeric on 74, consistent with invariant 5.
`post_type: "sale_post"` on 50 of 180 rows, each with a non-null `sale_post`.

---

## Cost

### Real cost of each run

Read from each run object (`usageTotalUsd`, `chargedEventCounts`, `pricingInfo`). The rate charged
to this account is $0.0015 per result, $0.005 per start event.

| Run | Start events | Start fee | Results charged | Results fee | Total |
|---|---|---|---|---|---|
| Run 1 | 1 | $0.0050 | 99 | $0.1485 | **$0.1535** |
| Control | 1 | $0.0050 | 165 | $0.2475 | **$0.2525** |
| **Spike** | | $0.0100 | | $0.3960 | **$0.4060** |

- **Results charged are fewer than rows returned**: 99 of 105 and 165 of 180. The cause is
  UNKNOWN; it is in our favour. The projection below prices every returned row.
- The platform set `maxItems: 333` on both runs by itself (= $0.50 / $0.0015).
- The plan's estimate of $0.02 per start was wrong — it assumed the 4 GB shown in the actor's
  `defaultRunOptions`. See "Memory" below.

### Projection for the planned schedule

Assumptions, stated so they can be checked:

- **36 runs a day:** every 30 minutes from 07:00 to 00:30 Israel time; none from 01:00 to 06:30.
- **~150 posts a day across the six groups.** Measured: 75 posts in the 24-hour window from the
  five uncapped groups, plus ~73/day for group 101875683484689 (30 posts in 9.6 hours in the
  control). That window was Friday night to Saturday; a weekday may be higher.
- **Overlap re-fetch:** each run's window is 30 minutes plus a 10–15 minute buffer
  (`RESEARCH.md` §4), so a post can be billed twice. Results billed per day: 150 (no overlap) to
  225 (15-minute buffer on every run).
- One start event per run in both layouts (see "Memory").

| Layout | Starts / day | Start fees / day | Result fees / day | **Total / day** | **Total / month (30 d)** |
|---|---|---|---|---|---|
| One run, all 6 groups | 36 | $0.18 | $0.23 – $0.34 | **$0.41 – $0.52** | **$12.15 – $15.53** |
| 6 separate runs | 216 | $1.08 | $0.23 – $0.34 | **$1.31 – $1.42** | **$39.15 – $42.53** |

The results fee is the same in both layouts; six runs cost six start fees. `RESEARCH.md` §3's
"~1,500 posts/month ≈ $2.25" is 5–7× too low: it ignored the start fee and the measured volume
is roughly 3× the estimate.

### Memory (from documentation only, no extra runs)

- **The actor already runs at 1 GB for us.** The build's actor definition sets
  `defaultMemoryMbytes` to `min(4096, (floor(url.length / 40) + 1) * 1024)`: 1024 MB for 1 to 39
  URLs. Both runs got 1024 MB. The `memoryMbytes: 4096` in the actor's `defaultRunOptions` is not
  what a run gets.
- **Can it go lower?** The Apify API's `memory` query parameter accepts a power of 2, **minimum
  128 MB**. The actor definition sets no minimum or maximum of its own (`minMemoryMbytes` and
  `maxMemoryMbytes` are absent).
- **The start fee would not change.** The start event is "one event per GB, minimum one event", so
  any memory from 128 MB to 1024 MB is charged one event, $0.005. The start fee is already at its
  floor; lowering memory saves nothing on it, and whether the actor works below 1 GB is untested.

---

## What this means for task 1.1 (not acted on)

- One run for all six groups stands. The six-run fallback is not needed.
- `maxPosts: 30` per group is enough at a 30-minute cadence. The busiest group (~73/day) would
  produce ~18 posts over the 6-hour night gap.
- `run 1`'s dataset is the fixture for the adapter tests.

---

## Proposed changes to `ASSUMPTIONS.md` and `RESEARCH.md`

Not made. For Ron to approve.

**`ASSUMPTIONS.md`**

1. **P1** → ✅ VERIFIED (2026-10-04): `postsNewerThan` applies per group in one multi-URL run.
   Evidence: run `GcarNt1rhe8tuSDuV` log, and exact match against control `9TShaAS1e6c2fv56t`.
2. **P2** → ✅ VERIFIED: shared text at `sharedPost.text`, images at `sharedPost.media`;
   `sharedPost.time` is `null`; `shared_reel` and `__reel__` can also carry a `sharedPost`.
3. **P5** → keep VERIFIED for the dataset, and add: the run log carries per-group status
   (`Posts: N | Reason: …`, `Successful groups: x/6`). New item, ⚠️ ASSUMED: the log format is
   stable enough to rely on.
4. **P6** → add the real bill: $0.0015 per result, $0.005 per start event, one start event per run
   at 1 GB. Results charged were fewer than rows returned (cause unknown).
5. **P9** → ✅ VERIFIED: `includeTopComment=false` suppresses `topComment` (0 of 285 rows).
6. **New:** `fetchAllComments` now defaults to `false` (OpenAPI, build 1.0.195); it was `true`.
7. **I6** → ✅ VERIFIED for download at fetch time (5 of 5). New item, ⚠️ ASSUMED: links expire
   ≈ 4.4 days after fetch, from the `oe` parameter.
8. **New:** `Photo` media items can also lack `width`/`height`.

**`RESEARCH.md`**

1. §2: `fetchAllComments` default is now `false`; add `shared_reel`, `__reel__` and media type
   `Reel`; the run log has per-group diagnostics even though the dataset does not.
2. §2 / §3: memory defaults to 1 GB for under 40 URLs; one start event per run.
3. §3: replace the cost line with the projection above (~$12–16/month for one run).
4. §3: the Apify API spec now lists `/v2/actors/…` paths; `/v2/acts/…` still answers.
5. §9: the silent-group thresholds need recalibrating — a live group went 31 hours without a post,
   and the busiest group posts ~73/day while the quietest posts ~4/day. A single threshold for all
   six groups will either miss failures or flag quiet groups. The run log's per-group reason may
   be a better signal than counting zeros.
6. New section or §1 row: measured volume ~150 posts/day across the six groups (not ~48).

**Also stale, outside these two files:** `CLAUDE.md` invariant 7 says both comment flags default
to `true`; `fetchAllComments` no longer does.
