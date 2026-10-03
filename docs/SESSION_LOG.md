# Session Log

Append-only. One entry per working session: what was done, what was verified, what is next.

---

## 2026-09-14 — Phase 0 implemented

### Done

Phase 0 built to the plan approved in the Phase 0 plan review (Q1–Q15, `DECISIONS.md` #31–#35).

- `pyproject.toml` (Python 3.12, pydantic, pyyaml; pytest and ruff for dev), `.python-version`, `uv.lock`
- `tlv_hunter/parsing/`: `parse_rfc2822_utc`, `parse_native_price`, `compute_listing_id`
- `tlv_hunter/contracts/`: `RawPost` + `Media` exactly per `SCHEMA.md` (31 and 6 fields),
  `ListingStub`, `DecisionStub`
- `tlv_hunter/textnorm/`: normalization and phone extraction ported from `scratch/dedup_check.py`,
  plus `annotate()`, which fills `text_hash`, `phones` and `no_text`
- `tlv_hunter/providers/`: `Provider` protocol, pure `thedoor.to_raw_post(item, fetched_at)` with no
  `fetch()`, and `FixtureProvider`
- `tlv_hunter/config/`: `ConfigSource` interface and `YamlConfig`; `config/collection.yaml` and
  `config/users/ron.yaml` hold only the approved keys
- `tlv_hunter/store/`: `Repository` protocol and `LocalJsonRepository`
  (`<root>/raw_posts/<listing_id>.json`, atomic replace, first `fetched_at` kept)
- `tlv_hunter/classify|policy|notify/`: protocols plus `*_stub.py` implementations
- `tlv_hunter/pipeline.py`: wiring only
- `tests/`: 97 tests, including the socket guard, the fail-not-skip fixture check, and
  `test_phase0_exit.py`

Not created, as scoped: `dedup/`, `state/`, `jobs/`, `Notification`, `GroupWatermark`.

### Verified

- `uv run pytest`: 97 passed. `uv run ruff check .` and `ruff format --check .` are clean.
- **Phase 0 exit gate:** all 20 raw posts pass through `pipeline.py` with stubs and zero network
  calls. They round-trip out of a freshly opened store identical to what went in, and `raw`
  deep-equals the file item. A second run leaves the store unchanged.
- The ported textnorm reproduces `scratch/dedup_check.py` exactly: 20/20 identical hashes and phone
  lists, 17 distinct hashes, and the 3 known pairs.
- `external-contract-verification` was run for the thedoor response shape. Every field the mapper
  reads is in the actor's output docs (read 2026-09-14) and in the captured response.

### Needs Ron — corrections and decisions

**1. The media width/height wording in `SCHEMA.md` (Media) and `ASSUMPTIONS.md` (Sample
composition) is inaccurate.** The 2 Video items do not have `width`/`height` set to `null`: they
**omit both keys**. Photo items always have them. Video items also carry an extra `thumbnail` key,
and their `url` is a `/videos/` page, not `photo/?fbid=`. The approved type `int | None` still holds,
and the mapper maps a missing key to `None`. The wrong wording came from a `.get()`-based inspection
in the plan review.

**2. Discrepancies between the actor's documentation and the real response or `HANDOFF.md` §4.**
Not yet recorded in `ASSUMPTIONS.md` (skill step 5).
- `postsNewerThan` absolute format is documented as **`YYYY-MM-DD`**, a date only. `HANDOFF.md` §4
  says "absolute ISO". If the actor truncates to a date, the watermark cannot be finer than a day.
  Relevant to 1.1a and P1.
- `topComment` is documented as an array. The real response has an object or `null`.
- A top-level `user_id` is documented. The real response has no such key; it has `user_name`, and
  the id is at `user.id`.
- `includeTopComment` defaults to `true`. `sortingOrder` also allows `most_relevant` and
  `buy_sell_listings`.
- The actor page shows "from $1.00 per 1,000 results", against ~$1.50 in `HANDOFF.md` (P6).

**3. Choices made during implementation that are not covered by the docs.**
- Text that is not blank but normalizes to nothing, such as an emoji-only post, raises
  `UnhashableTextError`. Hashing it would collide with other such posts; `None` would contradict
  `no_text=False`. It has not been seen in real data, but a real case would fail the run.
- `phones` are stored as written (`050-9184537`), including repeats within a post, as in the 1.2
  script. `find_by_phone` compares through `canonical_phone`. A Firestore `array-contains` query in
  Phase 2 would need a canonical stored form.
- Posts with `no_text=True` are stored but not classified (#29). Because `decide` needs a listing,
  they also get no decision and no notification. Whether they notify in calibration mode is
  undecided.
- The v1 `user_id` value is `ron`.
- `source` and `text_source` accept only their documented values. `RawPost` validators reject
  inconsistent records: a `listing_id` that does not match; `text_hash` or `phones` before textnorm
  ran; `no_text` that disagrees with the text; `text_source` that disagrees with blank text.
- `FixtureProvider` filters `group_ids` locally and applies `since` inclusively (`posted_at >= since`).

### Next

1. Ron reviews the Phase 0 code and the items above. Corrections to `SCHEMA.md` and `ASSUMPTIONS.md`
   are his.
2. Phase 1 starts with task 1.1a. Before writing the spike, settle whether `postsNewerThan` accepts
   a datetime or only a date (item 2).

---

## 2026-10-02 — Docs sync (no code changes)

### Recorded retroactively

Ron's review of the Phase 0 build took place on 2026-09-14, after the entry above, but no session
entry was written for it. This is reconstructed from the other documents, not from memory of the
session.

The "Needs Ron" items of the previous entry were resolved as follows:

| Item | Resolution |
|---|---|
| 1. Media width/height wording | Corrected in `SCHEMA.md` (Media) and `ASSUMPTIONS.md` (Sample composition) |
| 2. `postsNewerThan` date-only absolute form | `DECISIONS.md` #36, `ASSUMPTIONS.md` P1b — always relative minutes |
| 2. `topComment` documented as array | `ASSUMPTIONS.md` P11 |
| 2. `includeTopComment` default, `sortingOrder` enum | `ASSUMPTIONS.md` P9, P8 |
| 2. "from $1.00" pricing | `ASSUMPTIONS.md` P6 |
| 3. Text that normalizes to nothing | `DECISIONS.md` #37 — `no_text`, never an error |
| 3. Phone storage format | `DECISIONS.md` #38 — stored normalized |
| 3. No-text posts and notification | `DECISIONS.md` #39 — notified in a minimal format |
| Stale actor Input tab | `DECISIONS.md` #40 |

Still recorded nowhere except the previous entry: the documented top-level `user_id` that the real
response lacks; the `RawPost` validators; `FixtureProvider` applying `since` inclusively; the v1
`user_id` value `ron`.

### Found during this sync

- **Code lags `DECISIONS.md` #38.** `tlv_hunter/textnorm/phones.py::extract_phones` still returns
  phones as written (`match.group(0)`); `canonical_phone` exists but is not applied on storage.
- `DECISIONS.md` #37 was **not** checked against the code in this session. Verify that
  `UnhashableTextError` is gone and an emoji-only post yields `no_text=True`.
- `PHASE_1.md` header was stale ("planned, not started"). Updated.

### Requirement clarified by Ron — not yet a decision

Ron is searching for **two** things, not one:

1. A room in an existing shared flat, entering alone (what `HANDOFF.md` §1 describes).
2. An empty apartment to enter together with two friends.

He wants to switch between these searches freely with filters over the collected posts.

Nothing was written to `SCHEMA.md` or `DECISIONS.md` (invariant 1). What it touches:

- **Gate B** already requires the `Listing` schema to cover every listing type, so no change of
  direction — but whole-apartment fields (total rent, room count) are now a v1 need of Ron's own,
  not only of a hypothetical second user.
- **Gate C** currently assumes one filter rule set per user. Two searches by one user means
  several named filter profiles per user. To be settled at Gate C; it may also affect how
  `Decision` is keyed (`PHASE_1.md` §1.0 keys it by user only).
- `HANDOFF.md` §1 "What Ron is looking for" describes only search 1.

### Sequencing

Ron prefers to defer task 1.1a (it needs an Apify token and a paid run). Nothing offline depends on
it: it gates only `fetch()` in the thedoor adapter and the Phase 2 watermark input. It must run
before `fetch()` is written. The Apify API exposes everything the spike needs with a token alone
(dataset items, the run's `usageTotalUsd` and `chargedEventCounts`, and the run log), so Claude Code
can run it and report without manual steps beyond supplying the token in `.env`.

### Next

1. Task 1.3 — dedup stage A, offline against the fixture. Bring `textnorm` in line with #37 and #38
   in the same pass.
2. Gate B — `Listing` schema, with both of Ron's searches in view.
3. Task 1.1a — before `fetch()` in task 1.1.

---

## 2026-10-02 (continued) — Alignment session (docs only, no code changes)

### Done

- **`DECISIONS.md` #41 recorded:** filtering is a view-time layer over all collected posts, with
  three filters (listing kind, optional price bounds, number of rooms). This replaces the
  "several named filter profiles per user" reading in the entry above.
- **Yad2** recorded as a future, unplanned source in `MACRO_PLAN.md` §9.
- **`docs/BACKLOG.md` created** as the single list of open work, with a table of decisions that
  have not reached the code. `CLAUDE.md` now points at it.
- **`PHASE_1.md`:** task 1.2b added for the `textnorm` fixes.

### Verified

- **Decision #37 is not implemented.** `compute_text_hash` still raises `UnhashableTextError`,
  `annotate` derives `no_text` from `is_blank` only, the `RawPost` validator rejects `no_text=True`
  on non-blank text, and a test asserts the old behaviour.
- Decision #38 is not implemented (as found earlier today).

### Sequencing — supersedes the "Next" list above

Ron will bring the Apify token before the next session, so task 1.1a is no longer deferred. The
order is in `BACKLOG.md`, "Next sprint".

### Open for Ron

1. Where the #41 filters live in v1, given that the dashboard is Phase 6+.
2. Whether a post with `null` in a filtered field is shown or hidden.
3. Whether repeated phone numbers within one post are kept or collapsed (#38 does not say).

---

## 2026-10-02 / 2026-10-03 — New baseline and docs cross-check (docs only, no code changes)

### Done

Ron brought a revised handoff with several large changes of direction. It was worked through with
him question by question, and the result is `docs/BASELINE.md`, approved 2026-10-02.

The main changes: home server with Tailscale instead of GCP; friends as users from the start;
dashboard before Telegram; alerts only on a profile match; the keyword sniper removed; bounded
retention (archive at 25 days, delete at 40); a rejected list with reasons, admin-only; a filter
model with fixed-critical, default-critical and preference levels. `BASELINE.md` §13 lists what
changed against the old documents.

Then every other document was cross-checked against the baseline, in a fixed order:

| File | What was done |
|---|---|
| `BASELINE.md` | Marked approved. Amended: shared group list, the shared-post exception to the no-images rule, "women preferred", entry date wording, Gate E, and four items missing from the build order (watermark, reclassify job, sent-alert record, price mismatch in the digest) |
| `RESEARCH.md` | **New.** Verified facts, providers, field map, traps, dedup findings and model test results, carried from the two archived documents with later corrections folded in. Replaces the never-created `PROVIDERS.md` |
| `DECISIONS.md` | #5, #9, #12, #13, #15, #16, #17, #21, #39, #41 marked superseded; #18, #29, #31 corrected; #8, #19, #25, #38 extended or amended; #42–#60 added |
| `ASSUMPTIONS.md` | Firestore and Cloud Run items marked as no longer applying; references repointed to `RESEARCH.md`; new items for Telegram long polling, the Mini App on a tailnet, Tailscale sharing, image download, and the areas source |
| `SCHEMA.md` | Wording only. No field, type or rule changed. Gate E added to the gate table and Gate C widened |
| `PHASE_1.md` | Rewritten as the collection phase. Task numbers 1.1a, 1.1, 1.2, 1.2b, 1.3 kept; 1.4–1.9 retired; new tasks from 1.10 |
| `BACKLOG.md` | Rewritten for the new order |
| `HANDOFF.md`, `MACRO_PLAN.md` | Moved to `docs/archive/` with an "archived" header |

### Verified

- Telegram needs no public address for a bot: long polling and outbound sends (Bot API docs).
- Tailscale Serve is tailnet-only HTTPS; device sharing admits an outside user to one machine
  (Tailscale docs).
- The sniper is not in the package: `tlv_hunter/classify/` holds only the protocol and the stub.

### Found

- `HANDOFF.md` had no §7 (the legal section three documents pointed at) and no "What Ron is looking
  for" section. Ron confirmed the legal section is not needed; the open legal question is
  `ASSUMPTIONS.md` L1.
- About 10% of the sample (2 of 20 posts) has no images and will be rejected before the model. Ron
  confirmed the rule, with the shared-post exception.

### Not done in this pass

- `CLAUDE.md` was deliberately left for a separate review with Ron. It still describes the old
  direction in several places (`BACKLOG.md`, "Doc debt"). **Until that review, `BASELINE.md` wins
  wherever the two disagree.**

### Next

1. Review `CLAUDE.md` with Ron.
2. Phase 1 in the order given in `BACKLOG.md`. Ron brings the Apify token for task 1.1a.

---

## 2026-10-03 (continued) — `CLAUDE.md` aligned (docs only)

### Done

`CLAUDE.md` reviewed with Ron against `BASELINE.md` and rewritten in place. Twelve corrections:
the project description and current phase; the three `jobs.*` commands removed (they do not exist
yet); invariants 3, 5, 7 and 9 reworded; the seams table brought in line (profiles live in the
store, `policy` and `notify` are stubs until phases 3 and 4, `state` is phase 1); two domain traps
corrected; the files table now lists `BASELINE.md` and `RESEARCH.md` and no archived or
never-created file.

Three invariants added with Ron's approval, numbered 11–13 so that existing references to
invariants 1–10 stay valid: the model classifies only; collection never filters by a user's
criteria; no Facebook login with any provider.

This closes the "Not done in this pass" item of the previous entry. All active documents now agree
with `BASELINE.md`.

### Next

Phase 1 in the order given in `BACKLOG.md`. Ron brings the Apify token for task 1.1a.

---

## 2026-10-03 (continued) — Task 1.2b: `textnorm` fixes for #37, #38, #57

### Done

- **#37.** `compute_text_hash` returns `None` when the normalized text is empty; `UnhashableTextError`
  is removed (grep: it was referenced only in `normalize.py` and `test_textnorm.py`, never caught in
  the pipeline). A new `normalize.py::normalizes_to_nothing` is the single definition of `no_text`,
  used by both `annotate` and the `RawPost` validator. The `text_source` checks still use
  `is_blank`, so `text_source="text"` with `no_text=True` is valid.
- **#38, #57.** `extract_phones` returns `canonical_phone` output, an identical number once, in
  order of first appearance. `find_by_phone` still normalizes its input and now compares directly
  against the stored (already canonical) phones. Before simplifying it: the configured store root
  (`data/store`) does not exist, so no records with as-written phones were stored.
- Tests: the raising test replaced by a `None` test; new tests for an emoji-only post through
  `to_raw_post` + `annotate`, the validator accepting/rejecting emoji-only `no_text`, and a number
  repeated in three formats within one post. `PHONES_FROM_TASK_1_2` and `test_phone_formats` now
  expect canonical form.

### Verified

- `uv run pytest`: 101 passed. `ruff check` and `ruff format`: clean.
- Fixture results unchanged: 20 posts, 17 distinct hashes, the same 3 colliding pairs, phones in 10
  of 20 posts, 0 `no_text`.
- `RESEARCH.md` and `ASSUMPTIONS.md` hold no statement made stale by this change.

### Open for Ron

- `SCHEMA.md`, `phones` row: says "stored normalized" but does not state the once-per-post rule from
  #57. Not edited; Ron decides whether to add it.
- `PHASE_1.md` still lists 1.2b without a completion mark. Not edited in this task.
- The name next to a number (#57) remains a Gate B requirement, recorded in `DECISIONS.md` #57.

### Next

Task 1.1a, the spike. Needs `APIFY_TOKEN` in `.env`.

---

## 2026-10-04 — Part A doc fixes; task 1.1a, the spike

### Done

- **Doc fixes (approved by Ron, wording only):** `SCHEMA.md` `phones` row states the #57
  once-per-post rule (no field or type changed); `PHASE_1.md` marks 1.2b complete; `BACKLOG.md`
  has a row for #57's name-next-to-number, pointing at Gate B.
- **Contract read before any paid call** (`external-contract-verification`): the build's OpenAPI
  definition (build 1.0.195, rebuilt 2026-10-03), the actor's pricing, the build's actor
  definition, and the Apify API spec `v2-2026-10-01T153946Z`.
- **Two paid runs**, approved by Ron, $0.50 cap each: run 1 `GcarNt1rhe8tuSDuV` (24-hour window)
  and control `9TShaAS1e6c2fv56t` (no window). 5 images downloaded. Report: `docs/SPIKE_1_1a.md`.
  Raw responses, run objects, stored inputs and logs in `data/raw/thedoor_spike_1_1a_2026-10-04*`.
  Script: `scratch/spike_1_1a.py`. The token was read from `.env` and sent only in the
  `Authorization` header to `api.apify.com`; it was never printed.

### Verified

- **P1: the time window applies per group.** Five groups stopped independently at the same cutoff;
  each matches the control exactly. One run for all six groups stands.
- `maxPosts` is per group (control: 30 × 6 = 180).
- All six groups reachable. One group returned 0 rows because it had not posted for 31 hours; the
  run log, not the dataset, says so (`Reason: time_frame_reached`).
- `includeTopComment=false` works: 0 of 285 rows carry a `topComment`.
- Shared posts: text at `sharedPost.text`, images at `sharedPost.media`, 19 of 19.
- Images download at fetch time with a plain GET: 5 of 5 JPEG.
- Cost: $0.1535 + $0.2525 = $0.4060. $0.0015 per result, $0.005 per start; one start event per
  run, since the actor gives itself 1 GB for under 40 URLs.

### Found

- `fetchAllComments` now defaults to `false`; `CLAUDE.md` invariant 7 says `true` (not edited;
  doc-debt row added).
- Response shape changed since 2026-09-13: `actors` and `text_preview` gone, ten keys added, new
  `post_type` values `shared_reel` and `__reel__`. The mapper maps all 251 non-shared rows.
- Volume is ~150 posts/day, not ~48. Projected cost ~$12–16/month for one run per slot (~$39–43
  for six). `RESEARCH.md`'s $2.25/month is stale.
- The silent-group thresholds in `RESEARCH.md` §9 would flag a healthy quiet group.
- Charged results are fewer than rows returned (99/105, 165/180); cause unknown.

### Not done

- `ASSUMPTIONS.md` and `RESEARCH.md` not edited; the proposed changes are listed at the end of
  `SPIKE_1_1a.md`.
- `PHASE_1.md` does not yet mark 1.1a complete.

### Next

Ron reviews `SPIKE_1_1a.md` and its proposed edits. Then Gate E. Task 1.1 is unblocked on the
window question.

---

## 2026-10-04 (continued) — Spike follow-up docs; decisions #61 and #62 (docs only)

### Done

All approved by Ron. No code changes.

- **`ASSUMPTIONS.md`:** the 8 changes from `SPIKE_1_1a.md`. P1, P2, P9, I6 → VERIFIED; P5 and P6
  extended; new P13 (run-log format, ASSUMED), P14 (`Photo` without `width`/`height`), I7 (link
  expiry ≈ 4.4 days, ASSUMED). The `fetchAllComments` default change was applied to the existing
  P3 row rather than as a new row, so that no row contradicts it.
- **`RESEARCH.md`:** the 6 changes. §3 records that Ron accepted the projected ~$12–16/month for
  one run covering all 6 groups.
- **`CLAUDE.md`** invariant 7: wording only. `includeTopComment` defaults to `true`,
  `fetchAllComments` to `false`; both still sent as `false`.
- **`SCHEMA.md`** `Media`: wording only, `Photo` items can also omit `width`/`height`. No field or
  type changed.
- **`PHASE_1.md`:** 1.1a complete; P1, P2, P5, P6, P9, I6 marked in §2.
- **Decision #61** (amends #55): admin-set run interval, 30 minutes by default; a "run now"
  button; manual runs allowed in quiet hours; one run at a time. Phase 5. `DECISIONS.md`,
  `BASELINE.md` §4, §11, §12. The phase 6 item now reads "editing the quiet hours and the group
  list", since the interval moved to phase 5.
- **Decision #62:** viewed posts per user, a separate record settled at Gate C; unviewed first.
  `DECISIONS.md`, `BASELINE.md` §8, §12 (Gate C and phase 3).
- **`BACKLOG.md`:** spike-review item and the invariant-7 doc-debt row removed; shared-post images
  row added (Gate A amendment, with Gate E, undecided); rows for #61 and #62; the scheduler choice
  notes the interval and manual-run requirements.

### Still stale, not in this pass's scope

- `ASSUMPTIONS.md` P7 (~8 posts/group/day, ASSUMED) is contradicted by the measured ~150/day; P1c
  (window measured from run start) was observed in the spike log; the "Normalization choices" row
  on the shared-post trigger (`post_type` vs empty text) is answered by the spike — `sharedPost`
  is non-null on all 19 shared rows, across three `post_type` values.
- `RESEARCH.md` "Media items" still says only `Video` items omit `width`/`height`.
- `SCHEMA.md` `post_type` row still says `shared` is not yet observed, and lists neither
  `shared_reel` nor `__reel__`.
- `ASSUMPTIONS.md` I3 still sizes Gemini cost at ~50 posts/day.

### Next

Gate E, together with the shared-post images question (`BACKLOG.md` items 1 and 2).

---

## 2026-10-04 (continued) — Gate E approved; decision #63 (docs only)

### Done

All approved by Ron, 2026-10-04. No code changes.

- **`SCHEMA.md`:** Gate E marked approved; new "GATE E" section (post lifecycle record, keyed by
  `listing_id` and separate from `RawPost`; the rules with no field of their own; `GroupWatermark`).
  Gate A amended: `media[]` falls back to `sharedPost.media[]` (`id` → `media_id`, `url` →
  `page_url`, `width`/`height` `None`); a shared post is detected by `sharedPost` being present.
  `post_type` row lists the observed values. Stub-contracts paragraph updated. `schema_version`
  not bumped.
- **`DECISIONS.md`:** #63 with the reasons; #59 marked settled by #63.
- **`CLAUDE.md`** invariant 3: flagged posts are exempt from deletion (wording only).
- **`BASELINE.md`:** §5 adds `pending`, flagged posts keep the full record including raw, an
  archived post keeps its reason; §12 Gate E approved; §14 spike items, shared-post path and
  fetch-time download VERIFIED, download from the home server still unverified.
- **`PHASE_1.md`:** Gate E approved; 1.13 has the open point on a per-group failure inside a
  successful run.
- **Stale wording fixed:** `ASSUMPTIONS.md` P7, P1c, "Normalization choices", I3; `RESEARCH.md`
  "Media items"; `SCHEMA.md` `post_type`.
- **`BACKLOG.md`:** Gate E and shared-post images rows removed; #63 row pointing to tasks 1.10,
  1.11, 1.3, 1.12, 1.13; #46 and #49 rows note Gate E is approved.

### Verified

- The Gate A amendment's condition, checked against both spike datasets with no network: all 65
  `sharedPost.media[].url` values are `www.facebook.com` page links (`photo/?fbid=…`,
  `video.php?v=…`, `reel/…`), the same forms as own `page_url`, with no `oe` or signature
  parameter. Recorded in `SCHEMA.md` under the fallback. "Never expires" rests on link form, as for
  `page_url`.

### For Ron

- **`schema_version`:** not bumped, and I think no bump is needed. No `RawPost` field or type
  changed, and the fallback only changes the output for shared posts, which the mapper has refused
  until now — no stored record anywhere was produced the old way.
- **`schema_version` on the Gate E records:** `PHASE_1.md` §1.0 says "`schema_version` on every
  record". The approved lifecycle and `GroupWatermark` tables have none. Not added.
- **Record names:** the lifecycle record has no code name in `SCHEMA.md`; it gets one in task 1.10.
- **Tags kept `ASSUMED`:** P1c (observed in the spike log, but not documented) and P7 (one 24-hour
  window), per the tag rule in `ASSUMPTIONS.md`.
- **The reasons in #63** were written from the rules and the earlier decisions; Ron gave the rules,
  not every reason.

### Next

Task 1.10, the SQLite store (`BACKLOG.md` item 1).

**Follow-up (approved by Ron):** `schema_version: int` (starts at 1) added to the post lifecycle
record and `GroupWatermark` in `SCHEMA.md`; the #63 reason for downloading images of posts the
model will reject replaced; `GroupWatermark` removed from the "no approval gate yet" sentence in
"Stub contracts".

---

## 2026-10-04 (continued) — Task 1.10: SQLite store and `state/`; decisions #64–#68

### Done

Decisions approved by Ron, 2026-10-04, recorded as `DECISIONS.md` #64 (scope and interfaces), #65
(SQLite layout), #66 (Gate E types and consistency rules), #67 (`no_images` means no media at all),
#68 (a re-fetched `no_images` post with media returns to `"pending"`).

- **Code:** `contracts/post_lifecycle.py` (`PostLifecycle`, `PostImage`),
  `contracts/group_watermark.py` (`GroupWatermark`), `store/sqlite.py` (`SqliteRepository`),
  `state/base.py` (`WatermarkStore`), `state/sqlite.py` (`SqliteWatermarkStore`). `Repository`
  gains `upsert_with_lifecycle`, `save_lifecycle`, `get_lifecycle`, `find_without_lifecycle`;
  `local_json` implements them. `require_utc` in `parsing/datetimes.py`, now used by `RawPost` and
  the new records. `pipeline.py` untouched.
- **Tests:** contract tests shared by both repositories (`test_repository_contract.py`, run through
  the `make_repository` fixture); `test_sqlite_store.py`, `test_watermark_store.py`,
  `test_post_lifecycle.py`; the Phase 0 exit test runs against both repositories.
- **Docs:** `SCHEMA.md` Gate E (#66, #67), `PHASE_1.md` (1.10 complete, 1.11, 1.13, 1.14 wiring),
  `BASELINE.md` §3 and §5, `DECISIONS.md` #64–#68 and a note on #49, `ASSUMPTIONS.md` I8 and the
  language line, `BACKLOG.md`, `CLAUDE.md` (language line, `store/` and `state/` rows).

### Verified

- `uv run pytest`: 197 passed. `uv run ruff check .`: clean. `uv run ruff format --check .`: 67
  files formatted.
- The 101 tests as they stand at `HEAD`, exported unchanged and run against the new code: 101
  passed.
- Phase 0 exit test: both tests pass for `local_json` and for `sqlite`.
- SQLite thresholds, read on sqlite.org on 2026-10-04: UPSERT added in 3.24.0 (a conflict target
  required until 3.35.0; the code always gives one); generated columns 3.31.0, `RETURNING` 3.35.0,
  built-in JSON 3.38.0, none of them used; foreign keys 3.6.19, off by default per connection and a
  no-op inside a transaction. Minimum set to 3.24.0.
- On Ron's laptop (Python 3.12.9, SQLite 3.45.3), by running it: the default `datetime` adapter
  raises `DeprecationWarning` (not used); pydantic's ISO strings do not sort lexically when
  microseconds vary (no datetime columns); a file with an open connection cannot be deleted on
  Windows (one connection per operation, and a test for it); explicit `BEGIN IMMEDIATE` / `ROLLBACK`
  work under `autocommit=True`.

### Not verified

- The home-server container's SQLite version (`ASSUMPTIONS.md` I8).
- Behaviour with two processes writing the same file. Phase 1 has one writer; the concurrent case
  is an open choice in `BACKLOG.md`.

### For Ron

- **`listing_id` on `PostLifecycle`.** Gate E says the record is "keyed by `listing_id`" but has no
  `listing_id` row. The model carries it, since `save_lifecycle(record)` takes only the record.
  Should a row be added to the table?
- **Guards not in the approval:** `upsert_with_lifecycle` raises `ValueError` when the record's
  `listing_id` differs from the post's; `save_all` raises `ValueError` on a duplicate `group_id`.
- **Pre-existing contradictions, not fixed:** `PHASE_1.md` 1.12 says images are downloaded "for
  canonical non-rejected posts", while Gate E downloads for posts the model will reject and for some
  reposts. `PHASE_1.md` 1.1 still calls the shared-post path "unverified" (P2 is verified).
- **The `CLAUDE.md` single-implementation list** (normalization, datetime parsing, `listing_id`,
  price parsing) does not name the UTC check. Not added.
- **`CLAUDE.md` is gitignored and not tracked**, so its edits do not appear in `git status`.
- **The file name `tlv_hunter.sqlite3`** is only in `tests/conftest.py` for now. Where its
  production constant lives is decided with the 1.14 wiring.

### Next

Task 1.1, thedoor `fetch()` (`BACKLOG.md` item 1).

**Follow-up — 1.10 review (docs only, approved by Ron, 2026-10-04):** `SCHEMA.md` Gate E has an
explicit `listing_id` row on the post lifecycle record (noted as #66 item 8; `schema_version` stays
1). The two guards are recorded as approved in #64. `CLAUDE.md` single-implementation rule names
`require_utc`. `PHASE_1.md` 1.1: shared-post path marked verified (P2). `PHASE_1.md` 1.12 and
`BACKLOG.md`: open point on exactly which posts get their images downloaded; the rule itself is
unchanged. `PHASE_1.md` 1.14 and `BACKLOG.md`: open points on who calls `find_without_lifecycle`,
who creates `store_root`, and where the `tlv_hunter.sqlite3` constant lives. `BACKLOG.md` #49 row
brought up to date. No code or tests changed.
