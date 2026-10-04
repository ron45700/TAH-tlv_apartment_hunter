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

---

## 2026-10-04 (continued) — Decisions #69 and #70 (docs only)

### Done

Two decisions approved by Ron, 2026-10-04, answering the two questions left open under #68 for
task 1.11 planning. Docs only; no code or tests changed.

- **#69:** a post rejected as `no_text` and fetched again (the same post) with text returns to
  `"pending"` and goes to the model. Extends #68.
- **#70:** when the canonical was rejected as `no_images` and an identical-hash repost arrives with
  media, the canonical returns to `"pending"`; the repost's photos are downloaded into the
  canonical's `images` (`PostImage.listing_id` = the repost's); the repost stays a repost; the card
  link stays the canonical's permalink. Gate E "Reposts" rule gains a third case.
- **Files touched:** `DECISIONS.md` (#69, #70; #68's open paragraph replaced by a pointer; a note
  on #63's identical-hash repost bullet), `SCHEMA.md` (Gate E "Reposts" rule, Gate E reasons line,
  "Last updated"), `PHASE_1.md` (1.11 open questions replaced by the two rules; 1.3 gains the #70
  state change; 1.12 open point names the third case), `BASELINE.md` (§5 "No text" and "No images"
  rows, amendment line), `BACKLOG.md` (item 2 needs nothing; the #67 row is now #67–#70 with the
  task split), this log.
- **Task split (mine, from the data path in `BASELINE.md` §4):** 1.11 builds #67, #68, #69; 1.3
  builds the #70 return to `"pending"`, because pre-model rejects run before dedup and only dedup
  knows a post is a repost; 1.12 builds the #70 download.

No field or type changed; `schema_version` stays 1.

### For Ron

Cases the wording leaves undefined. Not resolved.

1. **A post returning to `"pending"`: are the pre-model rules run again?** A `no_text` post
   re-fetched with text but with no media at all would meet #67's `no_images` rule, while #69 says
   it returns to `"pending"`.
2. **A `no_text` post re-fetched with text whose hash matches a stored post.** It now has
   duplicates. Does it return to `"pending"` and go to the model, or become a repost of that
   canonical (no card of its own)?
3. **"The canonical has no media at all" (#70): its own media, or its `images` record?** Read as its
   own media, every later identical-hash repost also downloads its photos, since the canonical's
   own media stays empty.
4. **A repost whose media is only video or reel.** By #67 the canonical has media through it and
   returns to `"pending"`; by the download rule no photo is downloaded, so its `images` stays empty.
   Confirm this is intended.
5. **An archived canonical rejected as `no_images`.** `PHASE_1.md` 1.3 says a repost of an archived
   post makes it active again; #70 says the canonical returns to `"pending"`. Which applies when
   both hold?
6. **Canonical and repost new in the same run.** Whether the canonical is first stored as
   `"rejected"` and then moved to `"pending"`, or stored as `"pending"` directly. The end state is
   the same; it decides whether 1.11 or 1.3 owns the case.
7. **Not covered:** a repost found by dedup B in phase 2 (rewritten text). #70 names only an
   identical text hash.

### Next

Task 1.1 plan (Part 2 of this session), awaiting Ron.

---

## 2026-10-04 (continued) — Task 1.1: thedoor `fetch()`; decision #71

### Done

Ron's decisions on the 1.1 plan recorded as `DECISIONS.md` #71 (amends #20: the regular call,
not a synchronous one). No real Apify run.

- **Code:** `providers/thedoor.py`:
  - `ThedoorProvider.fetch()`: start the run with `maxTotalChargeUsd`, poll it to a terminal
    status (`waitForFinish` ≤ 60 s), abort and raise past `run_timeout_secs`, raise unless
    `SUCCEEDED` or when rows ≥ `options.maxItems`, read the dataset.
  - Row handling: a row that fails to map is skipped and logged at error level (D); a row from a
    group that was not requested is dropped with a warning (E); a group at `max_posts` gets a
    warning (J). The `since` filter matches `FixtureProvider`. One info line per run: per-group
    counts (zeros included), skipped, dropped, kept, `usageTotalUsd`.
  - `build_actor_input` and `posts_newer_than` (#36, rounded up). `urllib_transport`, stdlib
    only, token in the header only.
  - Mapper: a shared post is detected by `sharedPost` present. Text falls back to
    `sharedPost.text` when the post's own text is blank. Media falls back to `sharedPost.media`,
    with `width` / `height` taken when present (G). `UnverifiedSharedPostError` removed.
- **Config:** `include_top_comment` (`Literal[False]`), `max_total_charge_usd` (0.50),
  `run_timeout_secs` (300) in `CollectionConfig` and `config/collection.yaml`.
- **Tests:**
  - `tests/test_thedoor_fetch.py` (new): fake transport over the spike 1.1a dataset and run
    object. Covers the input (equal to the spike's stored `INPUT`), polling, failed statuses,
    deadline and abort, failed abort, the cap, D, E, J, no text or phones in the logs, and the
    real transport with `urlopen` faked.
  - `tests/test_thedoor.py`: shared-post mapping on the spike fixture.
  - `tests/test_config.py`: the three keys.
  - `tests/test_fixture_policy.py`: a missing spike fixture fails.
- **Abort endpoint** (Ron chose the free no-op check): one authenticated
  `POST /v2/actor-runs/GcarNt1rhe8tuSDuV/abort` on the finished spike run. HTTP 200, the run
  object under `data`, status unchanged. Saved as `data/raw/apify_abort_noop_2026-10-04.json`.
- **Files touched:**
  - Code and config: `tlv_hunter/providers/thedoor.py`, `tlv_hunter/config/base.py`,
    `config/collection.yaml`.
  - Tests: `tests/conftest.py`, `tests/test_config.py`, `tests/test_thedoor.py`,
    `tests/test_thedoor_fetch.py` (new), `tests/test_fixture_policy.py`.
  - Docs: `docs/BACKLOG.md`, `docs/DECISIONS.md` (#71, #20), `docs/SCHEMA.md` (G),
    `docs/ASSUMPTIONS.md` (P15–P19, P6), `docs/PHASE_1.md` (1.1 complete, 1.13 and 1.14 open
    points, P6 row), `docs/RESEARCH.md` (§3 call bullet), `docs/SPIKE_1_1a.md` (cost
    correction), `.claude/skills/external-contract-verification/SKILL.md` (I), this log.
  - `CLAUDE.md` unchanged: no line found stale.

### Verified

- `uv run pytest`: 241 passed. `uv run ruff check .`: all checks passed.
  `uv run ruff format --check .`: 68 files already formatted.
- Read today, without a token: actor build still `1.0.195` (`hePeml26EwGHFdamf`), input schema
  and pricing unchanged since the spike. Apify API spec `v2-2026-10-01T153946Z`: the run, poll,
  dataset and abort endpoints, `ActorJobStatus` values, bearer auth.
- **Cost correction:** spike run 1 now reads 105 results charged and $0.1625. The 99 and
  $0.1535 read at the end of the run were preliminary (`ASSUMPTIONS.md` P19).

### Not verified

- That abort stops a *running* run (P18). What a run does at the charge cap (P17). The control
  run's final cost.
- `fetch()` against the live API. Its first real run is the 1.14 DoD run.

### For Ron

1. **A row with no readable `group_id`** is treated as a row that fails to map (D, error, counted
   as skipped), not as an unrequested group (E). That call is mine.
2. **"Log the exception" (D)** is implemented as the exception type plus the missing key or the
   failing field names, never the message. Some messages (pydantic, the price parser) can carry
   post content.
3. **The deadline** runs from the start of `fetch()` and covers starting and polling the run, not
   the dataset read.
4. **Still stale, not fixed:**
   - `RESEARCH.md` §3 still says per-group behaviour is "not yet verified (P1)" with a six-run
     fallback. P1 was verified in spike 1.1a.
   - The skill:
     - It still lists Firestore, in its description and under its links; the store is SQLite
       (#44).
     - Its anti-pattern "rather than the actor's own input page" conflicts with its own rule not
       to use the Input tab.
     - Its actor "OpenAPI definition" link is the store page. The machine-readable definition
       read today is
       `https://api.apify.com/v2/acts/thedoor~facebook-group-post-scraper/builds/default/openapi.json`.
5. **J uses equality** with `max_posts`, as written. A count above it (never seen) is not warned.

### Next

Task 1.11, pre-model rejects (`BACKLOG.md` item 1).

---

## 2026-10-04 (continued) — Task 1.1 review: three fixes

### Done

Approved by Ron, 2026-10-04. No real Apify run.

1. **A ceiling on D** (`DECISIONS.md` #71 D, amended). `fetch()` raises `ProviderRunError` when
   more than half of the rows failed to map **and** at least 3 failed (`MIN_SKIPPED_TO_FAIL`).
   The count is over the rows of requested groups, with rows dropped under E excluded. A row with
   no readable `group_id` is a mapping failure (the call recorded in the previous entry), so it
   counts on both sides. Below the ceiling, nothing changes.
2. **J is `>=`** `max_posts`, not `==`. The warning names the row count. #71 J, `PHASE_1.md` 1.13
   and the `BACKLOG.md` row now read "`max_posts` rows or more".
3. **Stale wording:**
   - `RESEARCH.md` §3 now states the per-group window as verified (P1, spike 1.1a); the six-run
     fallback is gone. The six-run cost comparison stays, as a comparison.
   - The skill: Firestore removed from the description and the links. The thedoor OpenAPI link is
     now the machine-readable definition read for task 1.1. The anti-pattern line points at the
     actor's OpenAPI definition instead of its input page. No rule changed.
- **Tests** (`tests/test_thedoor_fetch.py`):
  - The ceiling: 2 broken of 105 pass (the existing test), all broken raises, 2 of 3 does not
    raise, 3 of 5 raises, and 3 broken with 4 dropped raises (3 of 3, not 3 of 7).
  - J: with `max_posts` 28, the groups at 30 and at 28 are both warned.
- **Files touched:** `tlv_hunter/providers/thedoor.py`, `tests/test_thedoor_fetch.py`,
  `docs/DECISIONS.md`, `docs/BACKLOG.md`, `docs/PHASE_1.md`, `docs/RESEARCH.md`,
  `.claude/skills/external-contract-verification/SKILL.md`, this log.

### Verified

`uv run pytest`: 246 passed. `uv run ruff check .`: all checks passed.
`uv run ruff format --check .`: 68 files already formatted.

### For Ron

- The memo23 OpenAPI link in the skill still points at the store page. Its machine-readable
  definition was not read, so it was left as is.

### Next

Task 1.11, pre-model rejects (`BACKLOG.md` item 1).

---

## 2026-10-04 (continued) — Decision #72 recorded; task 1.11 planned, not built

### Done

Docs only. No code, no test change, no git. Approved by Ron, 2026-10-04.

- **`DECISIONS.md` #72, "Pre-model rejects: the seven open cases"**, with the reasons as presented
  to Ron: re-evaluation of a re-fetched pre-model reject against both rules (1); a `no_text` post
  that comes back with text goes through dedup normally (2); the identical-hash repost download
  rule reads by what we hold (3); a video- or reel-only repost returns the canonical to `pending`
  (4); `pending` wins over "active again" for an archived `no_images` canonical (5); 1.11 evaluates
  each post alone, 1.3 applies #70 afterwards (6); #70 under dedup B deferred to Gate D (7).
- **Pointers and rewording:** #63 (the repost bullet), #68, #69 and #70 point at #72; #70's
  "Reposts" bullet reworded per #72.3, its old wording kept in the note.
- **`SCHEMA.md`** Gate E "Reposts" reworded (#72.3), the Gate E reasons line, and the "Last
  updated" header. No field or type change; `schema_version` stays 1.
- **`PHASE_1.md`:** 1.11 (re-fetch rule is #72.1; #72.6; #72.2 pointer), 1.3 (#72.2, .4, .5, .6,
  .7, and the open point on "active again"), 1.12 (the repost condition per #72.3).
- **`BASELINE.md`:** header; §5 "active again" exception (#72.5); the "No text" and "No images"
  rows (#72.1, #72.3, #72.4).
- **`BACKLOG.md`:** the #67–#70 row now covers #72 and splits it across 1.11, 1.3 and 1.12; the
  1.3 open point in "Next sprint"; a new section "Recorded for a later phase" with the four rows
  (failure-alert reason and digest skipped rows in phase 5, the repost video link in phase 3 UI
  design, #72.7 at Gate D).
- **Files touched:** `docs/DECISIONS.md`, `docs/SCHEMA.md`, `docs/PHASE_1.md`, `docs/BASELINE.md`,
  `docs/BACKLOG.md`, this log. `CLAUDE.md`, `RESEARCH.md`, `ASSUMPTIONS.md` unchanged: no line
  found stale.

### Verified

- Fixture counts for the 1.11 tests, read today with the existing mapper and `annotate`:
  - Spike 1.1a main (105 rows): 8 posts with no media (all `regular`), 0 `no_text`, 1 reel-only,
    15 shared, all 15 with media after the fallback.
  - Spike 1.1a control (180 rows): 22 with no media, **1 `no_text`** (a `sale_post`, blank text,
    4 photos), 5 reel-only, 19 shared, all with media.
  - All 105 main-run posts are also in the control run, with identical text and media.
  - No video-only post and no post with neither text nor media in either dataset.

### For Ron

Cases #72 does not define, left as they are:

1. **#72.3, "what we hold":** read as any `PostImage` with a `local_path` in the canonical's
   `images`, including one that came from an earlier repost. The rule now applies to every
   canonical, not only one rejected as `no_images`: an active canonical with only video gets the
   photos of its next repost.
2. **#72.3 within one run:** when canonical and repost are both new and the canonical has photos,
   whether the repost downloads depends on whether the canonical's downloads ran first. For 1.12
   planning.
3. **Archive and `images`:** whether the archive job clears the `PostImage` entries or only the
   files is not defined. #72.3's "or when the canonical is archived" covers the archived state,
   not a canonical made active again whose entries still point at deleted files. Phase 5.
4. **#72.1 and an archived post** whose kept reason is `no_text` or `no_images`: #72.1 speaks of
   a rejected post. Also in the 1.11 plan.

### Next

Task 1.11 plan presented to Ron; waiting for his decisions before any code.

---

## 2026-10-04 (continued) — Task 1.11: pre-model rejects, built

### Done

Approved by Ron, 2026-10-04, with the changes recorded as `DECISIONS.md` #73. No git.

- **Code:** `tlv_hunter/premodel/rejects.py` (new, with an empty `__init__.py`). Pure functions,
  no storage (#73.6):
  - `pre_model_reason(post)`: `"no_text"` (reads `post.no_text`), then `"no_images"`
    (`not post.media`), else `None`. Raises `ValueError` when `no_text` is `None` (textnorm has
    not run, #73.1). Nothing extra for shared posts: the mapper's fallback already puts
    `sharedPost.media` in `media`.
  - `initial_lifecycle(post)`: schema version 1, `pending` or `rejected` with the reason, no flag,
    `last_published_at = posted_at`, `images = []`.
  - `recheck(existing, post)`: re-checks both rules only when the record is `pending`, or
    `rejected` with `no_text` / `no_images`; any other record is returned as is (#72.1, #73.2,
    #73.3). Every other field is kept. Raises `ValueError` when the record belongs to another post,
    the same guard as `upsert_with_lifecycle`.
- **Tests:** `tests/test_premodel_rejects.py` (new, 34 tests). Real data:
  - the 8 no-media posts of spike 1.1a main (97 pass);
  - the control run's 1 `no_text` post (22 `no_images`, 157 pass);
  - 6 reel-only posts;
  - all 15 shared posts pass on their shared media;
  - the 105 posts re-fetched unchanged in the control run.

  Constructed from real posts:
  - video-only;
  - no text and no media (`no_text` first);
  - emoji-only text;
  - a shared post with both media lists emptied, through the mapper;
  - each re-fetch transition;
  - pending → `no_images` / `no_text`;
  - the untouched records (active, the four model reasons, flagged, archived with `no_text`,
    `no_images` or no reason).
- `tests/conftest.py`: the `load_spike_1_1a` docstring names `_control`.
- **Docs:**
  - `BACKLOG.md`: 1.11 removed from the sprint; the 1.3, 1.12 and 1.14 open points; the #63,
    #64/#65, #67–#73 and #49 rows; the archive-job row.
  - `DECISIONS.md`: #73, and a pointer from #72.
  - `BASELINE.md`: header; §4 order; the "No text" row.
  - `PHASE_1.md`: status, 1.11 complete and reworded (not stored here), the 1.3, 1.12 and 1.14
    open points.
  - `CLAUDE.md`: one line on `premodel/`.
  - This log.
- **Files touched:** `tlv_hunter/premodel/__init__.py`, `tlv_hunter/premodel/rejects.py`,
  `tests/test_premodel_rejects.py`, `tests/conftest.py`, `docs/BACKLOG.md`, `docs/DECISIONS.md`,
  `docs/BASELINE.md`, `docs/PHASE_1.md`, `CLAUDE.md`, `docs/SESSION_LOG.md`. `pipeline.py`,
  `SCHEMA.md` and the contracts unchanged.

### Verified

`uv run pytest`: 280 passed. `uv run ruff check .`: all checks passed.
`uv run ruff format --check .`: 71 files already formatted.

### Not verified

Nothing calls the three functions yet; the store step is 1.14.

### Next

Task 1.3, dedup stage A and the repost log (`BACKLOG.md` item 1).

---

## 2026-10-04 (continued) — Decision #74, and the task 1.3 plan

### Done

Docs only. No code, no test change, no git. #74 approved by Ron, 2026-10-04.

- **`DECISIONS.md` #74, "A repost of an archived post returns it to the state it had"**: active →
  `"active"`; rejected by the model or flagged → `"rejected"` with the same reason; rejected as
  `no_images` with a repost that has media → `"pending"` (#72.5, unchanged); never classified →
  `"pending"`. The consequence (no field says whether an archived post was classified; phase 1
  returns an archived post with no reason to `"pending"`; Gate B settles phase 2) recorded, no
  field added. A pointer from #72.
- **`PHASE_1.md` 1.3:** "makes it active again" replaced by #74; the #72.5 bullet points at #74;
  open point 1 removed, the remaining one kept.
- **`BASELINE.md`:** header; §5, the sentence on a repost of an archived post.
- **`BACKLOG.md`:** item 1 loses the "active again" open point; the #67–#73 row becomes #67–#74,
  with #74 for task 1.3; a Gate B row in "Recorded for a later phase" for the consequence.
- **Files touched:** `docs/DECISIONS.md`, `docs/PHASE_1.md`, `docs/BASELINE.md`,
  `docs/BACKLOG.md`, this log. `SCHEMA.md` unchanged: no wording there states what a repost of an
  archived post does (the `state` row and "an archived post keeps its reason" agree with #74).
  `CLAUDE.md`, `RESEARCH.md`, `ASSUMPTIONS.md` unchanged: no line found stale. #72.5's own text
  ("wins over task 1.3's 'active again'") is left as recorded, with the pointer.

### Verified

Fixture facts for the 1.3 plan, read today with the existing mapper and `annotate` (no network):

- 20-post fixture: 3 hash groups, each a pair, all three within one group; no `posted_at` ties.
- Spike main (105): 17 hash groups (13 pairs, 4 triples), 4 within one group; no ties; 6 phones
  shared by posts with different hashes (phone-only matches).
- Spike control (180): 23 hash groups (17 pairs, 5 triples, 1 of four), 8 within one group; no
  ties; 10 phone-only matches; 1 `no_text`.
- All 105 main posts are in the control run with unchanged `text_hash` and `posted_at`.
- **4 control posts not in the main run share a hash with a main post and are older than it**:
  the late-arriving older duplicate occurs in the fixtures (the control run's wider window).

### For Ron

Cases #74 does not define, left as they are:

1. An archived canonical rejected as `no_images`, and a repost **with no media**: #74 names only
   the repost with media.
2. Which duplicates count as "a repost" for #74: one new to the store only, or also a stored
   duplicate re-fetched by the watermark overlap.
3. A new duplicate older than the archived post's `last_published_at`: the clock does not move
   (never backwards), so the post returns to its state and the next archive job archives it again.
4. A post returned to `"active"` from archive has had its images deleted. #72.3's re-download
   condition reads "when the canonical is archived"; whether it is read before or after #74 changes
   the state is a 1.12 point.
5. An archived post with reason `no_text`: unreachable through layer 2, since a `no_text` post is
   never hashed.

### Next

Task 1.3 plan presented to Ron; waiting for his decisions before any code.

---

## 2026-10-04 (continued) — Task 1.3: dedup stage A, built

### Done

Approved by Ron, 2026-10-04, with the decisions recorded as `DECISIONS.md` #75. No git.

- **Code:**
  - `tlv_hunter/dedup/stage_a.py` (new, with an empty `__init__.py`): `dedup_a(batch, repository)
    -> DedupResult(posts, lifecycles)`. Reads only (#75 F1).
    - Layer 1: a repeat within the batch kept once (first in provider order, logged); a re-fetched
      post keeps its stored `is_canonical` / `duplicate_of` (sticky), also after a text edit.
    - Layer 2: new posts grouped by hash; a group joins the stored canonical its hash reaches,
      following stored duplicates to their canonical (the earliest if two, D4); otherwise the
      earliest `posted_at`, tie to the smaller `listing_id` (A, D2). A `no_text` post is
      `True / None` (D3); a stored `no_text` post back with text goes through as new (#72.2).
    - Layer 3: nothing (C).
    - Lifecycle, in order (F2): `initial_lifecycle` or `recheck` per batch post (a stored
      canonical with no record gets `initial_lifecycle`, F4); per canonical, #74 with E1–E3, then
      #70 / #72.4 over batch and stored duplicates (D1), then `last_published_at` as the max over
      the record and the duplicates, never backwards.
    - Raises `ValueError` on a stored post with `is_canonical=None` (D5), and on a `duplicate_of`
      that does not reach a stored canonical.
  - `Repository.get(listing_id) -> RawPost | None` in `store/base.py`, `store/sqlite.py`,
    `store/local_json.py` (F3); the spy in `tests/test_phase0_exit.py` forwards it.
- **Tests:** `tests/test_dedup_stage_a.py` (new, 35 tests × 2 stores = 70); one contract test for
  `get` in `tests/test_repository_contract.py` (× 2).
- **Docs:**
  - `BACKLOG.md`: item 1.3 removed; the 1.12 open point (#72.3 vs #74) and the 1.14 store-step
    wording; the #63, #67–#74 and #49 rows; a #75 row; five rows in "Recorded for a later phase"
    (phase 3 UI earliest time, Gate B, phase 3 admin lists, phase 5 duplicate retention, Gate D
    phone).
  - `DECISIONS.md`: #75; pointers from #63, #64, #70, #74.
  - `PHASE_1.md`: status; §1.0 canonical anchor; 1.3 complete, layer table, #75 bullets, tests;
    the 1.12 open point 3; the 1.14 open points 1 and 5.
  - `BASELINE.md`: header; §4 "Dedup A".
  - `CLAUDE.md`: `get` in the `store/` seam row; one line on `dedup/stage_a.py`.
  - This log.
- **Files touched:** `tlv_hunter/dedup/__init__.py`, `tlv_hunter/dedup/stage_a.py`,
  `tlv_hunter/store/base.py`, `tlv_hunter/store/sqlite.py`, `tlv_hunter/store/local_json.py`,
  `tests/test_dedup_stage_a.py`, `tests/test_repository_contract.py`, `tests/test_phase0_exit.py`,
  `docs/BACKLOG.md`, `docs/DECISIONS.md`, `docs/PHASE_1.md`, `docs/BASELINE.md`, `CLAUDE.md`,
  `docs/SESSION_LOG.md`. `pipeline.py`, `SCHEMA.md`, the contracts and `premodel/` unchanged.

### Verified

`uv run pytest`: 352 passed. `uv run ruff check .`: all checks passed.
`uv run ruff format --check .`: 74 files already formatted.

On the fixtures: the 20 posts give 17 canonicals in all 50 orders; spike main then control keeps
all 105 main results and records (except `last_published_at` moving forward); the 4 late, older
control posts become duplicates of the stored canonical, where control alone would have made a
different post canonical; real phone-only matches stay apart.

### Not verified

Nothing calls `dedup_a` yet; the store step is 1.14.

### Notes

- `CLAUDE.md` is listed in `.gitignore` (line 36), so its edit does not show in `git status`.
- `dedup_a` raises when a stored duplicate points at a canonical that is not stored. Phase 5
  retention must not delete a canonical before its duplicates (`BACKLOG.md`, phase 5 row).

### Next

Task 1.12, image download (`BACKLOG.md` item 1).

---

## 2026-10-04 (continued) — Decision #76, and the task 1.12 plan

### Done

Docs only. No code, no test change, no git. #76 approved by Ron, 2026-10-04.

- **`DECISIONS.md` #76, "Which canonicals get their photos downloaded":** photos for every
  canonical post that has photos, whatever its state, a `no_text` post included; the duplicate rule
  unchanged (#72.3, as read in #73.5); photos only. Replaces "for canonical non-rejected posts" in
  `PHASE_1.md` 1.12. A pointer from #63's "images are downloaded for posts the model will reject".
- **`PHASE_1.md` 1.12:** the opening sentence no longer says "canonical non-rejected"; a "Which
  posts" list (canonicals by #76, duplicates by Gate E / #72.3 / #73.5, photos only); open point 1
  ("exactly which posts") replaced by the two points still open for the plan: retry on a later run,
  and where the files live on disk. Open points 2 and 3 kept.
- **`BACKLOG.md`:** item 1's 1.12 open points updated the same way; a #76 row in "Decisions
  pending implementation"; a new section "Known limits, not handled now" with one row: `dedup_a`
  finds a canonical's stored duplicates only through the hashes of the canonical and of its batch
  duplicates, so a stored duplicate with media whose text was edited later is not found, #70 (D1)
  can miss it, and a canonical with no media can return to `"rejected"`.
- **Files touched:** `docs/DECISIONS.md`, `docs/PHASE_1.md`, `docs/BACKLOG.md`, this log.
  `SCHEMA.md` unchanged: Gate E says images are downloaded "also for posts the model will reject"
  and never limits downloads to non-rejected posts, so no wording there contradicts #76.
  `BASELINE.md` unchanged: §3 and §5 say nothing about which posts' images are downloaded.
  `CLAUDE.md`, `RESEARCH.md`, `ASSUMPTIONS.md` unchanged: no line found stale.

### Verified

Fixture facts for the 1.12 plan, read today from `data/raw/` with no network:

- Media types across the three fixtures: `Photo`, `Video`, `Reel` only.
- At most 5 photos per post in the spike datasets; `photo_count` equals the own-media photo count
  on every row.
- Two `media_id` values have the form `GenericAttachmentMedia:EntityID:<digits>`: a `media_id` is
  not safe as a file name (`:` is illegal on Windows).
- Photo link paths end in `.jpg`, `.png` or `.webp` (spike main 339 / 53 / 20, control
  555 / 57 / 20). Spike 1.1a downloaded 5 JPEGs only; PNG and WebP were never downloaded.
- The spike 1.1a download script sent `User-Agent: Mozilla/5.0`; no download without that header
  was tried.
- The spike links' `oe` values read as 2026-10-08 05:32–09:32 UTC (`ASSUMPTIONS.md` I7).

### For Ron

Cases #76 does not define, left as they are:

1. Whether #76 applies only the first time a canonical is stored, or on every fetch of it (a
   re-fetched canonical whose photos are held, or whose downloads failed). Same question as the
   1.12 retry point.
2. An archived canonical fetched again by the same post (not a repost). #76 says "whatever its
   state"; Gate E deletes an archived post's images. Unreachable in normal runs: a post is archived
   25 days after its last publication, far outside the fetch window.
3. `SCHEMA.md` Gate E does not state #76 positively ("images are downloaded also for posts the
   model will reject" says nothing about pre-model rejects). Not a contradiction, so not changed;
   a wording amendment would need approval.

### Next

Task 1.12 plan presented to Ron; waiting for his decisions before any code.

---

## 2026-10-04 (continued) — Task 1.12: image download, built

### Done

#77 approved by Ron, 2026-10-04: the download check, D1–D5d, the location, and the Gate E wording.
No git.

- **Check first** (`scratch/check_1_12_images.py`, throwaway): the 632 photo links of the spike
  control dataset, one at a time, `User-Agent: Mozilla/5.0`, 30 s socket timeout, 60 s and 20 MB
  caps; then 5 links without the header. Metadata only, in
  `data/raw/spike_1_12_images_2026-10-04/` (`results.json`, `REPORT.md`). No Apify call. Both of
  Ron's criteria held, so the code followed.
- **Code:** `tlv_hunter/images/download.py` — `download_images(result, repository, store_root,
  transport, clock) -> DedupResult`, `urllib_image_transport`, `ImageFetchError`,
  `ImageWriteError`. Rules as in `PHASE_1.md` 1.12 and #77. Nothing calls it; `pipeline.py`
  untouched.
- **Tests:** `tests/test_image_download.py`, 30 test functions, 79 runs (parametrized, and over
  both stores), fake transport, no network.
- **Docs:**
  - `BACKLOG.md`: item 1 is now 1.13–1.14, with two 1.14 points (where `download_images` is
    called; the time budget against a bootstrap run); the #63 and #67–#74 rows say 1.12 is done;
    the #76 row became "#76, #77 photo download"; a #77 D4b row (phase 5); the phase 5 row on
    `PostImage` at archive replaced by a phase 5 row for a sweep of unreferenced image files.
  - `DECISIONS.md`: #77; pointers from #63 (two bullets), #72 and #76.
  - `SCHEMA.md` Gate E, wording only as approved: #76 in the download rule; `images` is one entry
    per photo attempted; retry on a later run (D2); the "Reposts" rule with D3 and D4; header and
    reasons line.
  - `PHASE_1.md`: status; 1.12 complete; the §2 I6 row.
  - `ASSUMPTIONS.md`: I6 extended; I9 (the link's extension does not say what is served, FALSE),
    I10 (no header needed, 5 links), I11 (632 links unthrottled, about 1.6 s each).
  - `CLAUDE.md`: one line on `images/download.py`.
  - This log.
- **Files touched:** `tlv_hunter/images/__init__.py`, `tlv_hunter/images/download.py`,
  `tests/test_image_download.py`, `scratch/check_1_12_images.py`,
  `data/raw/spike_1_12_images_2026-10-04/results.json`,
  `data/raw/spike_1_12_images_2026-10-04/REPORT.md`, `docs/BACKLOG.md`, `docs/DECISIONS.md`,
  `docs/SCHEMA.md`, `docs/PHASE_1.md`, `docs/ASSUMPTIONS.md`, `CLAUDE.md`, this log. `scratch/`,
  `data/` and `CLAUDE.md` are gitignored. `pipeline.py`, the contracts, `dedup/`, `premodel/` and
  the stores unchanged.

### Verified

- The check: 632 of 632 HTTP 200, `image/jpeg`, JPEG bytes — `.jpg` 555, `.png` 57, `.webp` 20.
  No failure, no 403 or 429. 1,010 s in all (median 1.77 s for `.jpg`, 0.55 s `.png`, 0.73 s
  `.webp`; at most 2.97 s). Without the header: 5 of 5, JPEG, 0.42–0.66 s.
- `uv run pytest`: 431 passed. `uv run ruff check .`: all checks passed.
  `uv run ruff format --check .`: 77 files already formatted.

### Not verified

- Nothing calls `download_images` yet; the store step is 1.14.
- Downloads from the home server; behaviour after a link's `oe` time; concurrent requests.

### For Ron

1. **The 10-minute budget against a bootstrap run.** At about 1.6 s per photo (I11), 10 minutes
   covers about 375 photos. A bootstrap run of six groups at `max_posts` 30 holds about 540
   canonical photos (the control run had 632 photo links over 180 posts). The rest are recorded as
   `"not attempted: time budget"`, and D2 retries them only if their post is fetched again — which
   a bootstrap post outside the next run's overlap is not, so those photos are lost. A normal run
   (tens of photos) is far below the budget. Recorded as a 1.14 point in `BACKLOG.md` item 1.
2. **D2 on a repost, as built:** a duplicate's photo with an error entry in the canonical's record
   is retried when the duplicate is fetched again, even if the canonical now holds a photo. A photo
   of that duplicate with no entry follows the repost rule (downloaded only while the canonical
   holds nothing). #77 D2 says "each of its photos that is not held is attempted again"; the
   repost rule says a repost downloads nothing while the canonical holds. This reading retries only
   what was attempted before.
3. **D4, as built:** for a canonical brought back from archive this run, "holds" counts only photos
   downloaded in this run, so an entry left from before archive (none exist before phase 5, and
   D4b removes them) does not stop the bringing repost. A duplicate of such a canonical that did
   not bring it back downloads only what it retries.
4. **D5b, as built:** a retry that the budget stops keeps the first attempt's error, not "not
   attempted": the photo was attempted.
5. **A canonical in the batch that is archived** downloads its photos by #76 ("whatever its
   state"). Unreachable in normal runs (see the #76 entry above).
6. `BASELINE.md` §14 still says image download is verified "5 of 5"; not in this task's doc list,
   left unchanged.

### Next

Task 1.13, the per-group watermark logic (`BACKLOG.md` item 1).

---

## 2026-10-04 (continued) — Task 1.12 review: budget, reposts, BASELINE

### Done

Two changes and one doc fix, approved by Ron. No network, no git.

1. **The time budget is 30 minutes** (#77 D5b amended): `TIME_BUDGET_SECS = 1800` in
   `images/download.py`. The bootstrap open point is removed from `BACKLOG.md` item 1 (it was not
   in `PHASE_1.md`); one line kept in the `BACKLOG.md` scheduler row (phase 5) and in `PHASE_1.md`
   1.12: a run can now last longer than the 30-minute interval, one run at a time (#61).
2. **A repost's photos, retries included, are attempted only while the canonical holds no image**
   (#77 D2 amended for reposts). Once the canonical holds an image, a repost's failed photo keeps
   its error entry. D2 is unchanged for a canonical's own photos. D4 unchanged: for a canonical
   brought back from archive this run, "holds" still means a photo downloaded in this run; the
   reposts that brought it back download, and another duplicate retries only what it attempted
   before, both only while the canonical holds nothing from this run. `repost_photos` rewritten;
   the re-fetched repost test is now parametrized: the canonical holds an image → nothing
   attempted, the error entry stays; the canonical holds nothing → both failed photos attempted.
3. **`BASELINE.md` §14:** the image-download row now says 5 of 5 in spike 1.1a, then 632 of 632 in
   the task 1.12 check, all JPEG (I6), from the laptop; the home server still unverified.

- **Docs:** `BACKLOG.md` (item 1, the #76/#77 row, the scheduler row); `DECISIONS.md` #77 (header,
  D2 amendment, D5b amendment); `SCHEMA.md` Gate E download rule and header, wording only;
  `PHASE_1.md` 1.12; `BASELINE.md` §14; this log.
- **Files touched:** `tlv_hunter/images/download.py`, `tests/test_image_download.py`,
  `docs/BACKLOG.md`, `docs/DECISIONS.md`, `docs/SCHEMA.md`, `docs/PHASE_1.md`, `docs/BASELINE.md`,
  this log.

### Verified

`uv run pytest`: 433 passed. `uv run ruff check .`: all checks passed.
`uv run ruff format --check .`: 77 files already formatted.

### Next

Task 1.13, the per-group watermark logic (`BACKLOG.md` item 1).
