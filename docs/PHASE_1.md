# Phase 1 — Collection (semi-macro)

**Status:** in progress. Phase 0 complete (2026-09-14). Gates A and E approved. Tasks 1.2, 1.2b, 1.1a, 1.10 and 1.1 complete.
**Rewritten:** 2026-10-03 to match `BASELINE.md`. The previous version is in git history.
**Owner:** Ron
**Parent:** `BASELINE.md` §12 · **Research:** `RESEARCH.md`

**Phase goal:** a real run from the laptop collects posts from the real groups and stores them,
with their images, in SQLite: no duplicates, reposts logged, posts without text or images set
aside. No model, no dashboard, no Telegram.

**Phase DoD:**
1. A real run against all six groups stores posts and their images.
2. A second run 15 minutes later stores nothing twice and leaves the watermark correct.
3. Killing a run mid-flight does not advance the watermark; the next run picks up the missed window.
4. The `ASSUMED` items in §2 are resolved to `VERIFIED` or explicitly re-planned.

**Task numbers.** 1.1a, 1.1, 1.2, 1.2b and 1.3 keep their numbers. 1.4–1.9 belonged to the old
Phase 1 (classifier, policy, Telegram) and are **retired**: that work moved to phases 2–4. New
tasks start at 1.10 so that no old reference points at the wrong thing.

---

## 1.0 Mandatory anchors

Decided before code. These are the choices that, settled wrong now, leave stored history broken.

| Anchor | Decision |
|---|---|
| **Approval gates** | No schema, field, or filter rule is created or changed without Ron's explicit approval. |
| `schema_version` | On every record. `reclassify` depends on it. |
| `raw` | The provider's JSON is stored whole and untouched for as long as the post exists. |
| Time | tz-aware `datetime` in UTC everywhere. Conversion to Israel time happens only at display, and in the schedule's quiet hours. |
| `listing_id` | `sha256(source_post_id)`, `source` excluded (`DECISIONS.md` #28). |
| Canonical | For duplicates, the post with the earliest `posted_at` is canonical; the others point at it. |
| Retention | Archive at 25 days from last publication, delete at 40 (`BASELINE.md` §5). The jobs that do it are phase 5; the stored shape that lets them work is Gate E, now. |
| `user_id` | On every personal record. Users are real from phase 3. |
| Post vs verdict | Stored separately. A post record holds what the post says; what a given user's profile makes of it is never written onto the post. |
| `config` interface | Collection settings are read through one interface. No module reads a YAML file directly. |
| Shared collection | One run serves everyone. The group list, `maxPosts`, `sortingOrder` and the schedule are shared. The watermark is per group, never per user. |

---

## Order of work

```
1.2b  →  1.1a  →  Gate E  →  1.10  →  1.1  →  1.11  →  1.3  →  1.12  →  1.13  →  1.14
```

---

## 1.2 `textnorm` + phone extraction — ✅ COMPLETE (2026-09-14)

17 distinct hashes from 20 posts; exactly 3 colliding pairs, matching the 3 known duplicates; no
false collisions. Phones in 10 of 20 posts. Findings: `RESEARCH.md` §6, `ASSUMPTIONS.md` D1–D9.

---

## 1.2b `textnorm` fixes — ✅ COMPLETE (2026-10-04)

Decisions #37 and #38 were approved on 2026-09-14 and never reached the code. Decision #57 adds one
rule to #38. Dedup reads `text_hash`, `no_text` and `phones`, so these come first. The exact code
changes are in `BACKLOG.md`.

**DoD:** an emoji-only post yields `no_text=True`, `text_hash=None` and raises nothing; stored
phones are digits only with `+972` converted to a leading `0`; a number repeated within one post is
stored once; tests updated; `uv run pytest` green.

---

## 1.1a Spike — one real run against all six groups — ✅ COMPLETE (2026-10-04)

Report: `SPIKE_1_1a.md`. The time window applies per group; one run for all six groups stands.

Needs `APIFY_TOKEN` in `.env`. A throwaway script: one call to thedoor with all 6 URLs,
`maxPosts=30`, `fetchAllComments=false` and `includeTopComment=false` set explicitly, and
`postsNewerThan` as relative minutes. Start the run with the regular (non-sync) call and keep the
run ID, so that cost and the run log can be read afterwards. Cap the run with `maxTotalChargeUsd`.

**What it has to answer:**
1. Does the time window apply **per group**, or globally across the 6 URLs? (`ASSUMPTIONS.md` P1)
2. Do all six groups return data, or is one silently empty? (P5)
3. Does `includeTopComment=false` actually suppress `topComment`? (P9)
4. What did the run really cost? (P6)
5. Can the images be downloaded from the returned links? (I6)
6. If a `shared` post appears: where its text and its images sit. (P2)

**Output:** the raw response saved to `data/raw/` with a dated filename, and a written report.
Every later adapter test runs against that file with no network.

**If the per-group window fails:** six separate runs, and task 1.1 is updated before it is written.

---

## GATE E — post lifecycle fields (before 1.10) — ✅ APPROVED (2026-10-04)

Approved and copied into `SCHEMA.md`, Gate E, with the Gate A media amendment. Reasons:
`DECISIONS.md` #63.

Gate A approved what the provider gives. The baseline adds things a stored post must carry that
Gate A does not have. Settle with Ron:

- state (active, rejected, archived) and rejection reason
- who flagged it
- last publication time and the repost log
- local image paths, and what is recorded when a download fails
- for a shared post: whether its images count as the post's images (needed by the no-images rule)
- the `GroupWatermark` record

**DoD:** field table presented → Ron approved → copied into `SCHEMA.md` with a date.

---

## 1.10 SQLite store — ✅ COMPLETE (2026-10-04)

Storage for both Gate E records, on one SQLite file (`DECISIONS.md` #64, #65):

- `SqliteRepository` (`store/sqlite.py`), a second implementation of `Repository` next to
  `local_json`. `Repository` gains the lifecycle methods (`upsert_with_lifecycle`,
  `save_lifecycle`, `get_lifecycle`, `find_without_lifecycle`); `local_json` implements them too.
  The same contract tests run against both. `local_json` stays for tests.
- `WatermarkStore` and `SqliteWatermarkStore` in `state/`, for `GroupWatermark`. Not part of
  `Repository`.
- `PostLifecycle`, `PostImage` and `GroupWatermark` in `contracts/`, with the Gate E rules.

Not in 1.10: wiring into `pipeline.py` (1.14), building the initial lifecycle record (1.11), and
when the watermark advances (1.13).

**DoD:** the Phase 0 exit test passes against SQLite: 20 posts in, 20 identical posts out, second
run leaves the store unchanged, first `fetched_at` preserved. *Met:* the exit test runs against both
`local_json` and SQLite.

---

## 1.1 thedoor `fetch()` — ✅ COMPLETE (2026-10-04)

`ThedoorProvider.fetch()` in `providers/thedoor.py`: one regular (non-sync) run for all groups,
polled to a terminal status, with the charge cap, the run deadline and the row rules of
`DECISIONS.md` #71. The mapper takes a shared post's text and media from `sharedPost`
(Gate A amendment). Tests run against the spike 1.1a fixture through a fake transport.

**Input:** group IDs, `since` → **Output:** `list[RawPost]`. The mapper already exists
(`to_raw_post`); this adds the network call.

`postsNewerThan` is always relative minutes (`DECISIONS.md` #36). Both comment flags explicit.
Follow the `external-contract-verification` skill before writing it.

| Trap | Handling |
|---|---|
| `post_type: "shared"` | `text` is empty; real content sits in `sharedPost`: the text at `sharedPost.text`, the media at `sharedPost.media` (verified, `ASSUMPTIONS.md` P2) |
| `creation_time` | RFC 2822 → UTC |
| missing `group_title` | thedoor does not provide it; must not crash or fabricate |
| silent group | zero rows and a failure look the same; count rows per group every run |

**Tests:** against the 1.1a fixture. Zero network calls.

---

## 1.11 Pre-model rejects

A post is set aside before any model call when:

- it has no text (`no_text`), or
- it has no media at all (`no_images`, `DECISIONS.md` #67). A post whose only media is video or
  reel is **not** rejected. A post that shares another post is checked first: it is rejected only
  if the shared post has no media either. This is the rejection rule; which media are downloaded
  (photos only) is the separate download rule in 1.12.

It is stored with its reason and is never classified. About 10% of the sample has no media.

The initial `PostLifecycle` (`"pending"`, or `"rejected"` with its reason) is built here and stored
through `Repository.upsert_with_lifecycle` (1.10), which never overwrites an existing record.

**Re-fetched with media** (`DECISIONS.md` #68): a post rejected as `no_images` and fetched again
with media returns to `"pending"` and goes to the model. It does not stay rejected.

**Re-fetched with text** (`DECISIONS.md` #69): a post rejected as `no_text` and fetched again (the
same post) with text returns to `"pending"` and goes to the model, the same as #68.

**Media through a repost** (`DECISIONS.md` #70): when the canonical was rejected as `no_images` and
a repost with an identical text hash arrives with media, the canonical returns to `"pending"` and
goes to the model. The repost is found by dedup, so this part is built in 1.3; the repost's photos
are downloaded in 1.12. A `no_text` post is never hashed, so it has no reposts.

---

## 1.3 Dedup stage A, and the repost log

**Input:** batch of `RawPost` + Repository → **Output:** canonicals, and duplicates with
`duplicate_of`.

| Layer | Role |
|---|---|
| 1. `source_post_id` | Exact repeats, chiefly the watermark overlap |
| 2. **`text_hash`** | **The primary key.** Caught 3/3 pairs in the sample |
| 3. phone | One-directional signal only |

Compared **within the batch and against history**. A `no_text` post is never hashed.

A duplicate of a post already stored is a **repost**: it creates no new card, updates the
canonical's last publication time, and adds a line to its repost log. A repost of an archived post
makes it active again.

A repost with an identical text hash that has media, of a canonical rejected as `no_images`,
returns the canonical to `"pending"` (`DECISIONS.md` #70). The repost stays a repost, and the
canonical rule (earliest `posted_at`) is unchanged.

**Test:** the 20 posts in random order return the same canonical set on every run.

---

## 1.12 Image download

At fetch time, for canonical non-rejected posts: download each image to disk, record the local
path. A failed download must not fail the run or the post; it is recorded, and the post keeps its
other images.

**Open point — decided when 1.12 is planned.** The text above says images are downloaded "for
canonical non-rejected posts". `SCHEMA.md` Gate E adds the repost exception (a repost with an
identical text hash downloads its images when the canonical is archived, or all of its downloads
failed, or the canonical has no media at all, `DECISIONS.md` #70; the repost's photos are recorded
in the canonical's `images`) and says images are also downloaded for posts the model will reject. The plan for 1.12
states exactly which posts get their images downloaded.

---

## 1.13 Per-group watermark

The watermark **logic** only: when it advances. Its storage (`GroupWatermark`, `WatermarkStore`)
was built in 1.10; all groups are written together through `WatermarkStore.save_all`, one
transaction.

Rules in `RESEARCH.md` §4. The run input is `min(all watermarks) - buffer`, filtered per group
locally. The watermark advances only when the whole run succeeded.

**Open point — a group at `max_posts`.** When a group returns `max_posts` rows or more in one
run, its window may be cut off: older posts inside the window were not returned. `fetch()` logs a
warning (`DECISIONS.md` #71 J) and changes nothing. What the watermark does then is decided when
1.13 is planned.

**Open point — a per-group failure inside a successful run.** Posts arrive newest first, so a group
that fails midway would advance its watermark past posts it never returned (invariant 2). The run
log reports per-group status, but its format is `ASSUMED` (`ASSUMPTIONS.md` P13). Decided when 1.13
is planned.

---

## 1.14 Wiring `run_once`, and bootstrap

`pipeline.py` holds no logic of its own. `run_id` on every log line. An error at any stage means no
watermark write.

Storage wiring (1.10): posts are stored through `upsert_with_lifecycle`; `SqliteRepository` and
`SqliteWatermarkStore` are both constructed on `<store_root>/tlv_hunter.sqlite3`.

Bootstrap is an explicit flag, never auto-detected: the first run stores everything and initializes
the watermarks. Once alerts exist (phase 4), a bootstrap run sends none.

**Open points — decided when 1.14 is planned:**
1. Which step calls `find_without_lifecycle`, and what it does with a non-empty result.
2. Who creates the `store_root` directory: `SqliteRepository` does not, `local_json` does.
3. Where the production constant for `tlv_hunter.sqlite3` lives.
4. Where `ThedoorProvider` gets the Apify token (`APIFY_TOKEN` in `.env`); the provider takes it as
   a constructor argument.

---

## 2. `ASSUMED` items this phase must close

Full register: `ASSUMPTIONS.md`.

| Item | Task | Status |
|---|---|---|
| P1: `postsNewerThan` applies per group in one multi-URL run | 1.1a | ✅ VERIFIED 2026-10-04 |
| P5: all six groups return data | 1.1a | ✅ VERIFIED 2026-10-04. One group returned 0 rows because it was quiet; the run log shows per-group status (P13, ASSUMED) |
| P9: `includeTopComment=false` suppresses `topComment` | 1.1a | ✅ VERIFIED 2026-10-04. 0 of 285 rows |
| P6: real cost of a run | 1.1a | ✅ VERIFIED 2026-10-04. $0.1535 and $0.2525 as read at the end of the runs; run 1's final figure, read later, is $0.1625 (`ASSUMPTIONS.md` P19). ~$12–16/month projected, accepted by Ron |
| I6: images download from the signed links | 1.1a, 1.12 | ✅ VERIFIED 2026-10-04 at fetch time, 5 of 5. Link lifetime ≈ 4.4 days is ASSUMED (I7) |
| P2: where a shared post's content sits | 1.1a, 1.1 | ✅ VERIFIED 2026-10-04. `sharedPost.text`, `sharedPost.media` |

Closed earlier: minute granularity (P1b), duplicate pairs collide on hash (D1–D4), phone regex
coverage (D8), actor pricing (P6 rate).

---

## 3. End of phase

Before planning phase 2:
1. Update `RESEARCH.md` with what the real runs showed.
2. Update `ASSUMPTIONS.md`: move the items above out of `ASSUMED`.
3. Update `BACKLOG.md` and `SESSION_LOG.md`.
4. Find and verify the public source for Tel Aviv areas and streets (`ASSUMPTIONS.md` A1). Gate B
   cannot define the area field without it.
5. Only then plan phase 2 in detail.
