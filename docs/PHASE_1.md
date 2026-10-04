# Phase 1 — Collection (semi-macro)

**Status:** in progress. Phase 0 complete (2026-09-14). Gates A and E approved. Tasks 1.2, 1.2b, 1.1a, 1.10, 1.1, 1.11, 1.3 and 1.12 complete.
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
| Canonical | For duplicates, the earliest `posted_at` among posts that arrive together is canonical (a tie goes to the smaller `listing_id`); the others point at it. A stored canonical never changes (`DECISIONS.md` #75 A, D2). |
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

## 1.11 Pre-model rejects — ✅ COMPLETE (2026-10-04)

Three pure functions in `premodel/rejects.py` (`DECISIONS.md` #73): `pre_model_reason(post)`,
`initial_lifecycle(post)` and `recheck(existing, post)`. No storage: the store step is a 1.14 open
point. Tests run on the spike 1.1a datasets (the control run has the one real `no_text` post) with
no network.

A post is set aside before any model call when:

- it has no text (`no_text`, read from the stored `post.no_text`: text normalize runs first,
  `DECISIONS.md` #73.1), or
- it has no media at all (`no_images`, `DECISIONS.md` #67). A post whose only media is video or
  reel is **not** rejected. A post that shares another post is checked first: it is rejected only
  if the shared post has no media either. This is the rejection rule; which media are downloaded
  (photos only) is the separate download rule in 1.12.

It is stored with its reason and is never classified. About 10% of the sample has no media.

The initial `PostLifecycle` (`"pending"`, or `"rejected"` with its reason) is built here
(`initial_lifecycle`). It is not stored here (`DECISIONS.md` #73.6): the data path stores after
dedup, and the store step is decided in 1.14.

**Re-fetched** (`DECISIONS.md` #72.1, the rule behind #68 and #69): a post rejected before the
model (`no_text` or `no_images`) and fetched again (the same post) is checked again against
**both** pre-model rules, on its current content. It returns to `"pending"`, and goes to the model,
only if it now passes both; otherwise it stays `"rejected"` and its reason is updated to the first
rule that applies. A `"pending"` post fetched again is re-checked the same way (#73.2). A post with a
verdict (active, rejected by the model, flagged) and an archived post are left untouched (#73.2,
#73.3). This is `recheck`.

**Each post alone** (`DECISIONS.md` #72.6): 1.11 evaluates each post on its own content. When a
canonical and its repost are both new in the same run, 1.3 applies #70 afterwards; the end state is
the same.

**Media through a repost** (`DECISIONS.md` #70): when the canonical was rejected as `no_images` and
a repost with an identical text hash arrives with media, the canonical returns to `"pending"` and
goes to the model. The repost is found by dedup, so this part is built in 1.3; the repost's photos
are downloaded in 1.12. A `no_text` post is never hashed, so it has no reposts. One that comes back
with text goes through dedup like any post that arrived now (#72.2).

---

## 1.3 Dedup stage A, and the repost log — ✅ COMPLETE (2026-10-04)

`dedup_a(batch, repository) -> DedupResult` in `tlv_hunter/dedup/stage_a.py`, a plain module that
reads the Repository and writes nothing (`DECISIONS.md` #75). It returns the batch with
`is_canonical` and `duplicate_of` set, and the lifecycle records: one per post in the batch, plus
every stored canonical outside the batch whose record changed. It calls `initial_lifecycle` and
`recheck` itself (#75 F2). `Repository` gained `get(listing_id)` (#75 F3). Nothing calls
`dedup_a` yet: the store step is 1.14.

**Input:** batch of `RawPost` + Repository → **Output:** canonicals, and duplicates with
`duplicate_of`.

| Layer | Role |
|---|---|
| 1. `source_post_id` | Exact repeats, chiefly the watermark overlap. A repeat within the batch is kept once; a re-fetched post keeps its stored result and is never a duplicate of itself |
| 2. **`text_hash`** | **The primary key.** Caught 3/3 pairs in the sample. A new post joins the stored canonical its hash reaches (the earliest, if two, #75 D4) |
| 3. phone | Produces nothing in 1.3: a phone-only match is not a duplicate (#63). A candidate signal for Gate D (#75 C) |

Compared **within the batch and against history**. A `no_text` post is never hashed.

A duplicate of a post already stored is a **repost**: it creates no new card, updates the
canonical's last publication time, and adds a line to its repost log. A repost of an archived post
returns it to the state it had (`DECISIONS.md` #74): `"active"` if it was active; `"rejected"`
with the same reason if it was rejected by the model or flagged; `"pending"` if it was rejected as
`no_images` and the repost has media (#72.5), or if it was never classified. In phase 1 nothing is
classified, so an archived post with no rejection reason returns to `"pending"`.

A repost with an identical text hash that has media, of a canonical rejected as `no_images`,
returns the canonical to `"pending"` (`DECISIONS.md` #70); the repost may be a stored duplicate
(#75 D1). The repost stays a repost, and the canonical rule is unchanged. Settled by #72 and #75:

- A repost whose only media is video or reel also returns the canonical to `"pending"`; nothing is
  downloaded (#72.4).
- An archived canonical rejected as `no_images`, with a repost that has media: `"pending"` (#72.5,
  kept by #74).
- Canonical and repost new in the same run: 1.11 evaluates each alone, and 1.3 applies #70
  afterwards (#72.6).
- A `no_text` post that comes back with text goes through these rules like any post that arrived
  now (#72.2).
- #70 under dedup B is deferred to Gate D (#72.7).
- Only a duplicate new to the store, published after the archived post's `last_published_at`,
  brings it back from archive; an archived `no_images` post whose repost has no media returns to
  `"rejected"` (#75 E1–E3).
- A re-fetched post keeps its stored `is_canonical` / `duplicate_of`, also after a text edit, so the
  1.14 `upsert` writes them back unchanged; only `text_hash` follows the new text (#75). A
  duplicate gets an ordinary lifecycle record from its own content (#75 B).

**Tests:** `tests/test_dedup_stage_a.py`, against both stores, no network: the 20 posts in 50
random orders give the same canonical set; the three known pairs; spike main then control (all 105
main posts keep their result; the 4 late, older posts join the stored canonical); one test per
#75 decision.

---

## 1.12 Image download — ✅ COMPLETE (2026-10-04)

`download_images(result, repository, store_root, transport) -> DedupResult` in
`tlv_hunter/images/download.py`, a plain module (`DECISIONS.md` #76, #77). It takes `dedup_a`'s
result, downloads the photos to `<store_root>/images/`, and returns the result with the lifecycle
records' `images` updated: posts unchanged, and a stored canonical outside the result whose record
gained images added at the end. It reads the Repository and saves nothing; the store step is 1.14.
Nothing calls it yet. A failed download fails neither the run nor the post; a disk write error
fails the run (#77 D5a).

**Which posts:**

- **Canonicals:** every canonical post that has photos, whatever its state, a `no_text` post
  included (#76).
- **Duplicates:** the repost exception of `SCHEMA.md` Gate E: a repost with an identical text hash
  downloads its photos while the canonical has no successfully downloaded image, or when the
  canonical was archived and this repost brought it back (read on the stored record, before #74,
  #77 D4); the repost's photos are recorded in the canonical's `images` (#70, #72.3, #73.5).
  Canonical first, retry included, then its duplicates in canonical-rule order (#77 D3). A
  repost's photos, retries included, are attempted only while the canonical holds no image
  (#77 D2, amended in the review); a canonical's own photos not held are retried whenever it is
  fetched again (D2).
- Photos only, no video or reels (Gate E). Stored posts outside the batch are never downloaded.

**Settled by #77:** where the files live (D1), retry on a later run (D2), the order in one run
(D3), the archived reading (D4), a 30-minute budget (D5b, amended from 10 in the review: a run
can now last longer than the 30-minute interval, for the phase 5 scheduler's "one run at a
time", #61), the `User-Agent` header (D5c), entries
kept after an edit (D5d). The phase 5 archive job removes the `PostImage` entries with the files
(D4b).

**Check, before the code:** the 632 photo links of the spike control dataset, one at a time:
632 of 632 downloaded, all JPEG, in 1,010 s (`data/raw/spike_1_12_images_2026-10-04/REPORT.md`,
`ASSUMPTIONS.md` I6, I9–I11).

**Tests:** `tests/test_image_download.py`, against both stores, through a fake transport, no
network: one test per decision, the retry and failure kinds, the urllib transport's error mapping,
and spike main through `dedup_a`.

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
1. Which step calls `find_without_lifecycle`, and what it does with a non-empty result. 1.3
   already builds a record for a stored canonical that has none (#75 F4).
2. Who creates the `store_root` directory: `SqliteRepository` does not, `local_json` does.
3. Where the production constant for `tlv_hunter.sqlite3` lives.
4. Where `ThedoorProvider` gets the Apify token (`APIFY_TOKEN` in `.env`); the provider takes it as
   a constructor argument.
5. The store step: writing `dedup_a`'s result — each post through `upsert` /
   `upsert_with_lifecycle`, each record through `save_lifecycle` — and in what sequence. 1.3
   already calls `initial_lifecycle` and `recheck` (`DECISIONS.md` #73.6, #75 F2).

---

## 2. `ASSUMED` items this phase must close

Full register: `ASSUMPTIONS.md`.

| Item | Task | Status |
|---|---|---|
| P1: `postsNewerThan` applies per group in one multi-URL run | 1.1a | ✅ VERIFIED 2026-10-04 |
| P5: all six groups return data | 1.1a | ✅ VERIFIED 2026-10-04. One group returned 0 rows because it was quiet; the run log shows per-group status (P13, ASSUMED) |
| P9: `includeTopComment=false` suppresses `topComment` | 1.1a | ✅ VERIFIED 2026-10-04. 0 of 285 rows |
| P6: real cost of a run | 1.1a | ✅ VERIFIED 2026-10-04. $0.1535 and $0.2525 as read at the end of the runs; run 1's final figure, read later, is $0.1625 (`ASSUMPTIONS.md` P19). ~$12–16/month projected, accepted by Ron |
| I6: images download from the signed links | 1.1a, 1.12 | ✅ VERIFIED 2026-10-04 at fetch time, 5 of 5, then 632 of 632 in the 1.12 check (I9–I11). Link lifetime ≈ 4.4 days is ASSUMED (I7) |
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
