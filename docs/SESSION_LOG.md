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

---

## 2026-10-04 (continued) — BACKLOG row; task 1.13 plan presented

### Done

1. **`BACKLOG.md`, "Future (recorded, not planned)":** parallel image downloads, if runs prove too
   long. Approved by Ron. Not planned: Ron chose the 30-minute budget (#77 D5b); it would need its
   own throttling check (I11 covers sequential requests only) and must keep #77 D3's order inside
   each group.
2. **Task 1.13 plan presented, for Ron's decision. No code.** Nothing decided; no schema, field,
   config or filter-rule change.

### Verified (local, no network)

- **`since = min(all watermarks) - buffer`, with the watermark as the highest `posted_at`, makes
  every run as wide as the quietest group's silence.** In the spike control dataset the quietest
  groups' longest gaps between posts are 28.6 h (`5612809662118963`) and 26.7 h
  (`733810383372996`). A simulation over that dataset (20 runs, every 30 minutes, 15-minute
  buffer, the 10.7 hours in which all six groups are covered; a Saturday) gives a median window of
  26.7 h, **~107 rows per run**, and `101875683484689` at `max_posts` on every run. A window of
  the last successful run's start minus the buffer gives ~5.8 rows per run. At $0.0015 per result
  and $0.005 per start, 36 runs a day: **~$179/month against ~$15/month**. Ron accepted the
  ~$12–16/month projection, which assumed a 30-minute-plus-buffer window. Spike run 1 itself
  (24-hour window, 105 rows, $0.1625) is what a normal run looks like under the documented rule.
  Script: scratchpad, not kept.
- So a higher `max_posts` is free on a normal run only if the window is short; under the
  documented rule it multiplies the cost of every run.
- The spike log's per-group lines (`done … | Posts: N | Reason: …`, `Successful groups: 6/6`) were
  seen only for groups that succeeded; what the actor prints for a group that fails is unobserved.
- `fetch()` returns posts only; per-group row counts before the `since` filter are logged, not
  returned. A cut-off test from the returned posts alone is possible: a group with `max_posts`
  posts whose oldest is later than its own window start.

### Next

Ron decides the task 1.13 points (window basis, buffer, a group at `max_posts`, per-group failure,
the rules for `last_success_at` and `consecutive_failures`, the local filter, a group with no
record outside bootstrap). Then 1.13 is built.

---

## 2026-10-04 (continued) — Task 1.13: per-group watermark, built

### Done

Task 1.13 approved by Ron with decision #78 (W1–W7, the skipped row, the location), and one more
`BACKLOG.md` row (phase 6: `max_posts` editable by the admin). No network, no git. `pipeline.py`
untouched; nothing from 1.14.

1. **`tlv_hunter/watermark/window.py`**, a plain module, no storage:
   - `BUFFER = timedelta(minutes=15)` (W2).
   - `run_since(records, group_ids) -> datetime`: the configured groups' earliest
     `last_success_at` minus `BUFFER` (W1). Raises `MissingWatermarkError`, naming the groups, when
     a configured group has no record or a record with no `last_success_at` (W7). Records of
     groups no longer configured do not count.
   - `advance(records, group_ids, posts, *, run_started_at, since, max_posts) -> WatermarkAdvance`
     (`records`, one per configured group in configured order; `cut_off`, a `CutOff` per group at
     `max_posts` short of its own window start). `watermark` = the newest `posted_at`, never
     backwards; `last_success_at` = `run_started_at` (W5a); `consecutive_failures` resets on any
     row, otherwise counts up (W5b). A configured group with no record gets one (bootstrap).
   - The plan's `buffer` parameter is gone from both signatures: W2 made it a module constant.
   - Guards: UTC on both datetimes; `since` before `run_started_at`; a run started before a
     group's stored `last_success_at`; a post from a group not configured; duplicate records or
     group IDs; empty group list; `max_posts` not positive.
   - Cut-off test: `max_posts` posts or more, and the oldest later than the group's own window
     start, `max(since, watermark - BUFFER)` (W3).
2. **`config/collection.yaml`:** `max_posts` 30 → 50 (W3). The only config change.
3. **Tests:** `tests/test_watermark_window.py`, 28 tests on the spike 1.1a datasets, one or more
   per decision. `tests/test_thedoor_fetch.py`: the `config` fixture pins the spike's `maxPosts`
   (30, read from its input fixture, fixtures not edited); new test that the repo value reaches the
   actor input. `tests/test_config.py`: expects 50.
4. **`fetch()`'s `max_posts` warning:** unchanged. Its text ("its window may be cut off") does not
   assume the old window and still holds under W1.
5. **Docs:** `BACKLOG.md` (sprint item 1 is now 1.14 with the watermark wiring; #63 row; new #78
   row; the `max_posts` open choice removed; later-phase rows for the daily wide run, the
   `consecutive_failures` thresholds, the run-log detection task, groups × `max_posts`, adding a
   group without bootstrap; two known limits; the phase 6 `max_posts` row), `DECISIONS.md` (#78;
   pointers in #20, #36, #63, #71 J; #20's "silent-group detection falls out for free" corrected
   in place), `SCHEMA.md` (`GroupWatermark` rules, the `posted_at` row, header), `RESEARCH.md`
   (header, §2 `maxPosts` example 50, §3 window bullet and cost paragraph, §4, §9 counter),
   `PHASE_1.md` (status, 1.13 complete, 1.14 open point 5), `BASELINE.md` (§4 watermark bullet and
   the 07:00 line, §11 Admin, §12 phase 6), `ASSUMPTIONS.md` (P1b and P1c wording, header; no
   status changed), `CLAUDE.md` (one line), this log.

### Verified

`uv run pytest`: 462 passed. `uv run ruff check .`: all checks passed.
`uv run ruff format --check .`: 80 files already formatted (after `ruff format` reformatted the two
new files).

### Next

Task 1.14, `run_once` (`BACKLOG.md` item 1), including the watermark wiring.

---

## 2026-10-04 (continued) — Task 1.14: plan presented, not approved

### Done

Plan for task 1.14 (`run_once` and bootstrap) presented to Ron in the session. No code, no test,
no config change, no network call, no paid run, no git. `BACKLOG.md` unchanged: nothing was
decided.

The plan covers: the sequence of one run and what each step's failure leaves behind; the store
step and its crash behaviour; `find_without_lifecycle`; `store_root`, the `tlv_hunter.sqlite3`
constant and `APIFY_TOKEN`; the run command, the `--bootstrap` flag and `run_id` logging; the
zero-network tests; the bootstrap window options; the four real runs that close the DoD (planned,
not run).

### Found while planning

1. **The store step must write canonicals before duplicates.** The provider returns posts newest
   first, so a duplicate normally comes before its canonical. Stored in that order, a crash between
   the two leaves a stored duplicate pointing at a canonical that is not stored, and every later
   `dedup_a` raises ("not a stored canonical"): collection stops for good. Read from
   `dedup/stage_a.py` (`_Reader.canonical_of`), not run.
2. **A stored canonical's changed record must be saved before the new duplicate that changed it.**
   Otherwise, after a crash, #75 E1 sees the duplicate as already stored and an archived canonical
   never comes back (#74), and the #77 D4 repost download is lost.
3. **Bootstrap numbers** at `max_posts` 50, estimated from the spike control dataset (180 posts,
   632 photos, Friday night to Saturday): 6 h ≈ 46 rows, 12 h ≈ 87, 24 h ≈ 125, 48 h ≈ 207,
   72 h ≈ 237, 7 days ≈ 280; worst case 300 rows, $0.455, below the cap's `maxItems` 333.
4. `uv run --env-file .env` exists in the installed uv (0.12.11, read from `uv run --help`): the
   token can come from the process environment with no new dependency.
5. Contradictions listed for Ron: #11's bootstrap summary message against "alerts nothing";
   "stores everything" against a window that is always sent; `run_pipeline` and the Phase 0 exit
   test (classifier stub, `upsert` only, `is_canonical is None`) against phase 1 and #64; "15
   minutes later" against runs longer than 30 minutes (#77 D5b); two different run IDs in one log
   line; the `BASELINE.md` §4 data path stores after the model.

### Next

Ron decides: the bootstrap window and where its value lives; the open points (store-step
location, `find_without_lifecycle`, bootstrap on an existing store, `store_root` resolution,
`run_pipeline`, a failing `annotate`, the log format, re-reading the watermarks before `advance`);
`APIFY_TOKEN` read from the environment, by name; the real-run plan and its budget. Then 1.14 is
built; the real runs follow only on Ron's separate approval.

---

## 2026-10-04 (continued) — Task 1.14: `run_once` and bootstrap, built

### Done

Task 1.14 approved by Ron with decision #79 (D1, D2, O1–O4, O6–O9, the names). Code, tests and
docs. No network, no paid run, no git. `data/store` was not created.

1. **`tlv_hunter/pipeline.py`:** `run_pipeline` replaced by `run_once` (O1), which returns a
   `RunResult`. Steps: repair any stored post with no lifecycle record (O3); `run_started_at`;
   `since` from `run_since`, or `run_started_at - bootstrap_window`, with a warning naming the
   groups that already have records (O4); `fetch`; `annotate`; `dedup_a`; `download_images`; the
   store step `_store` (O2); `advance` on the records read again (O9); `save_all`. A failure at any
   step is logged as "run failed at step X (Type)" and raised. Afterwards the cut-off groups and a
   summary line are logged. The classifier, policy and notifier stubs are no longer called; they
   stay as seams.
2. **`tlv_hunter/jobs/run_once.py`** (new, with `jobs/__init__.py`): `main()` with `--bootstrap`.
   Holds `SQLITE_FILENAME`, `BOOTSTRAP_WINDOW` (24 h, D1) and `REPO_ROOT`. Reads `APIFY_TOKEN` from
   the environment. Resolves `store_root` against the repo root (O6). Creates it under
   `--bootstrap`, and otherwise refuses when the SQLite file is missing, before any constructor
   runs. Refuses a provider other than thedoor. JSON log lines on stderr with a 12-hex `run_id`,
   set through a `ContextVar` and a handler filter (O8). On a failure: exit 1, the exception
   without input values (a pydantic `ValidationError` reduced to location and type), and the
   traceback frames only.
3. **`providers/thedoor.py`:** its log lines and exception messages name the Apify run ID
   `apify_run`. No other change.
4. **Tests:**
   - `tests/test_run_once.py` (new, 46 tests, local_json and SQLite): bootstrap; the cut-off log;
     bootstrap on a store with records; a normal run with no record (the provider is never
     called); `since` from the last success; a second run over the same data; a normal run 40
     minutes later.
   - The same file, failures: a failure at each step (annotate, dedup, images, fetch with a
     `KeyboardInterrupt` too, a disk error leaving 2 orphan files, store, advance, save
     watermarks); a run overtaken by a later one.
   - The same file, the store step: its write order; a crash before every write of the store step
     converging to the uninterrupted store (the three known pairs plus two posts, newest first);
     the same after an archived canonical is saved.
   - The same file, the rest: the repair; no post text in the log; the DoD sequence A, B, killed
     C, D against a reference A, B, D.
   - `tests/test_run_once_job.py` (new, 9 tests): the command through `FakeApify`.
     `tests/test_phase0_exit.py` ported to `run_once`. `tests/test_thedoor_fetch.py`: three
     assertions read `apify_run`. `tests/conftest.py` imports `SQLITE_FILENAME` from the entry.
5. **Docs:** `BACKLOG.md` (sprint item 1 is now the four real runs; the done rows for #63, #64/#65,
   #67–#74, #75, #76/#77 and #78 removed; #49 updated; a later-phase row for #11 against a silent
   bootstrap; a known limit: a kill during the fetch does not abort the Apify run; the scheduler
   row notes no lock; the `CLAUDE.md` commands doc debt removed). `DECISIONS.md` #79. `PHASE_1.md`
   (status, DoD item 2, 1.14 built with the real-run table). `BASELINE.md` §4 (diagram and one
   bullet). `CLAUDE.md` (two paid commands; one line on `jobs/run_once.py`). This log.

### Verified

- The store-step order guards against the finding. With the order temporarily reverted to the
  provider's (and the out-of-batch saves last), both crash tests failed on SQLite, one with
  `dedup_a`'s "…which is not a stored canonical". Restored.
- `uv run pytest`: 517 passed in 325 s. `test_run_once.py` alone takes about 135 s, most of it in
  local_json: 42 s for the DoD sequence, 25 s for the second-run test.
- `uv run ruff check .`: all checks passed. `uv run ruff format --check .`: 84 files already
  formatted.
- `uv run python -m tlv_hunter.jobs.run_once --help` prints the flag. No run was started.

### Next

Ron's code review of task 1.14, then his separate go for the real runs A–D (#79 D2, `BACKLOG.md`
item 1). Then `PHASE_1.md` §3, end of phase.

---

## 2026-10-04 (continued) — Run A, the bootstrap run

### Done

Run A, approved by Ron (#79 D2), run once:
`uv run --env-file .env python -m tlv_hunter.jobs.run_once --bootstrap`, 12:55:08 → 13:05:42 UTC,
**exit 0**. No code or config change; no git. Runs B, C and D were not started.

- **Before the run:** `uv run pytest` 517 passed; `ruff check` and `ruff format --check` clean.
  `data/store` did not exist. `.env` holds `APIFY_TOKEN`: 46 characters, unquoted, delivered the
  same way by `uv run --env-file` (lengths checked, value never printed).
- **Saved in `data/runs/run_A_2026-10-04/`** (gitignored): the JSON log, exit code, start and end
  times, the output of two read-only check scripts (`scratch/check_run_A.py`,
  `scratch/check_run_A_failures.py`, counts and hostnames only, the database opened with `mode=ro`),
  and `REPORT.md`.
- **`ASSUMPTIONS.md`:** P20 added (`fetch()`'s regular call against the live API, VERIFIED).
  Evidence added to P6, P7 (contradicted once, still ASSUMED), P19, I6, I9 and I11.
- **`BACKLOG.md`:** item 1 marks A done and records the photo finding for Ron.

### Verified

- **Fetch:** Apify run `PI0qBslZY0nAeaIi5` `SUCCEEDED` in 60 s. 212 rows: 38, 49, 50, 18, 7 and 50
  per group; skipped 0, dropped 0.
  - `101875683484689` and `295395253832427` were cut off at 50. Their oldest posts were
    2026-10-04 08:11Z and 2026-10-03 17:20Z, against a window start of 2026-10-03 12:55Z.
  - The plan estimated about 125 rows.
- **Store:**
  - 212 posts: 184 canonical, 28 duplicate. 0 duplicates pointing at a missing or non-canonical
    post; 0 canonicals sharing a hash; **0 posts without a lifecycle record**.
  - States: `pending` 183, `rejected` 29 (`no_images` 21, `no_text` 8).
  - Images 58.5 MB, database 2.6 MB.
- **Photos:**
  - 688 entries: 415 held, 273 failed, 0 not attempted; 45 entries from reposts.
  - 415 files on disk against 415 references, matching both ways; all JPEG.
  - The download took 564 s, about 1.36 s per photo, with no 403, 429 or timeout.
- **Watermarks:** six records, `last_success_at` 2026-10-04T12:55:09.201Z, all
  `consecutive_failures` 0 (`5612809662118963` returned 18 rows this time). Each `watermark` is
  its group's newest post.
- **Cost:** read about 10 minutes after the run: $0.323, with 212 items and 1 start charged
  (212 × $0.0015 + $0.005). The run logged $0.32 at its end. The cap was received:
  `maxTotalChargeUsd` 0.5, `maxItems` 333.
- **Log:** one `run_id` (`32526fbcf616`) on all 281 lines; the token appears nowhere in it.

### Found — reported, not fixed

**273 of 688 photos failed with `network: gaierror` (DNS resolution).**
- All 546 attempts (two per photo) fell between 13:05:37.6Z and 13:05:38.9Z, right after the last
  photo written (13:05:37.4Z).
- They span 23 CDN hosts, the same hosts that served the photos held.
- Posts split cleanly: 104 with every photo held, 53 with none, at the end of the download order.
- A minute later the Apify API answered, and three of the failed hosts resolved again. The cause
  on the laptop is unknown.
- How long the outage lasted is unknown: 1.25 s is how long the 546 attempts took, because the
  downloader did not wait (corrected 2026-10-04 on Ron's reading).
- The code behaved as designed (#63, #77). The consequence: 53 posts (52 `pending`) hold no photo.
  Under #77 D2 they are retried only when fetched again, and only 3 of them fall in run B's window
  (from 12:40:09Z). The other 50 lose their photos for good unless they are re-fetched before the
  links expire (about 4.4 days, I7 ASSUMED).

### Next

Ron decides what to do about the 50 posts with no photo, and whether that changes the plan for B,
C and D. Then a separate go for run B (a normal run, started at least 15 minutes after A ended,
that is after 13:20:42Z).

---

## 2026-10-04 (continued) — Photo download after run A: plan presented, not approved

### Done

Ron approved two changes to the photo download before run B. (1) A network-type error waits 1,
3, 5 and 10 minutes, per outage, then the rest of the run's photos are recorded as network
failures. (2) Failed photos are retried from the stored link on every run, with no Apify call.
Both are to be recorded as `DECISIONS.md` #80 with the plan. The plan was presented in the
session; no code, no network, no paid run, no git. `DECISIONS.md` is not written yet.

- **Wording corrected, on Ron's reading:** the outage did not last 1.25 s. That is how long the
  546 attempts took, because the downloader did not wait; how long the outage lasted is unknown.
  Fixed in `data/runs/run_A_2026-10-04/REPORT.md`, `BACKLOG.md`, this log's run A entry, and
  `ASSUMPTIONS.md` I6 (same wording, not named by Ron).
- **`BACKLOG.md`:**
  - Sprint item 1 is now the photo-download change; the runs B–D are item 2.
  - New row, approved by Ron: measure a week of real runs before concluding on volume and monthly
    cost. Run A returned 212 rows in 24 h with two groups cut off, against ~125–150 estimated
    (P7); ~$12–16/month may be low.

### Found while planning (read-only, from the run A store)

- All 273 failed entries would qualify under decision 2: 228 are the canonicals' own photos, and
  45 are repost entries on 7 canonicals.
- No record is archived, and every failed record is a canonical.
- Under the repost rule (#77 D2 amended, D3 order), once a canonical's own photos are held its
  repost entries are not attempted again. Expected after run B, if the links still live: 228
  retried and held, and the 45 repost entries left as `network: gaierror` by design.
- The lifecycle table holds 212 records in 194 KB, and SQLite's JSON functions work on the laptop
  (3.45.3).

### Next

Ron decides the plan's open points: whether the waits count in the 30-minute budget, which
`timeout` is network-type, the reason for photos skipped after the schedule, one unreachable
host, whether retries wait, the new Repository method by name. Then #80 is recorded and built.
Run A's links expire around 2026-10-08 (I7, ASSUMED).

---

## 2026-10-04 (continued) — #80: network waits and stored-link retries, built

### Done

#80 approved by Ron (decisions 1 and 2, §4, U1–U7, the contract, the names). Code, tests and
docs. No paid run, no git. The only network access was one read of sqlite.org/json1.html, as
Ron's instructions asked: the JSON functions are built in by default as of SQLite 3.38.0
(2022-02-22), and `->` / `->>` date from the same release.

**Two points settled with Ron while building:**
- **U2's text is dropped.** Under U3 every remaining photo is tried once, so nothing would ever
  write `not attempted: network down`.
- **Any reply restarts the schedule,** an HTTP error included (U3's "first success").

1. **`images/download.py`:**
   - **Constants:** `NETWORK_WAITS_SECS = (60, 180, 300, 600)`; `STORED_LINK_MAX_AGE` (4 days,
     U5); `RETRYABLE_ERRORS`; the error texts `TIMEOUT` and `NETWORK`, already in use.
   - **`is_network_error`:** `network: …` and `timeout` (U1).
   - **`_Run._attempt` (decision 1):** waits on the schedule and tries the same photo again.
     - The waits count inside the budget, and a wait is cut when the budget runs out (§4).
     - After the schedule, each remaining photo is tried once until any reply (U3).
     - A network error no longer goes into #63's second pass.
   - **`_Run.retry_stored` (decision 2):** after the batch, using the new Repository query.
     - It skips posts in the batch, archived posts (stored or in-run), links of posts 4 days old
       or more (U5), and photos gone from the stored post (U6).
     - It tries the canonical's own photos first, then repost photos in canonical-rule order
       while the canonical holds nothing (U7).
     - One attempt each and never a wait (U4); entries past the budget are left as they are.
   - **`download_images`** takes `sleep` (default `time.sleep`, looked up at the call) and `now`
     (the run's start). Its log line counts the stored-link retries.
2. **A bug found and fixed (task 1.12's code):**
   - **What was wrong:** a stored canonical outside `dedup_a`'s result kept only its first change
     of the run. `_Run.added` held the record from its first `_set`, and later photos were lost.
   - **The fix:** `added` now holds IDs, and the final record is read from `records`.
   - **Proof:** two regression tests fail on the old code (4 failures across both stores, run
     with a temporary file copy, no git) and pass on the fix.
   - **Run A:** not affected; every canonical was in its batch.
3. **`store/`:**
   - `Repository.find_lifecycles_with_image_errors(prefixes)` in the protocol, `SqliteRepository`
     (`json_each` over `$.images`, `->>` on `error`, an exact prefix match by `substr`) and
     `LocalJsonRepository`.
   - The store module's `MIN_SQLITE_VERSION` is 3.38.0; `state` keeps 3.24.0. No layout change.
4. **`pipeline.py`:** `run_once` takes `image_sleep` and passes it, and `now=run_started_at`, to
   `download_images`.
5. **Tests:**
   - `tests/test_image_network.py` (new, 25 test functions, most on both stores): one or more per decision, U1–U7,
     §4, and the 4-day limit on both sides. A network error on a stored-link retry: no wait, and
     the entry stays.
   - `tests/conftest.py`: a guard that makes any real `time.sleep` in a test raise.
   - `tests/test_repository_contract.py`: three contract tests for the new method.
   - `tests/test_image_download.py`: the #63 test now covers non-network errors only, and asserts
     no wait; plus the regression test.
   - `tests/test_sqlite_store.py`: expects 3.38.0.
   - `tests/test_run_once.py`: run A's case end to end (the network drops, the schedule runs
     once, the next run recovers from the stored links); the wrappers pass the new method through.
   - `tests/test_phase0_exit.py`: the wrapper passes the new method through.
6. **Docs:**
   - `BACKLOG.md`: item 1 is runs B–D; item 2 the free GET on an expired link after 2026-10-08
     (U5); a phase 5 row to check the container's SQLite against 3.38.0; a known limit (U7).
   - `DECISIONS.md` #80, with pointers in #63, #64, #65 and #77 D2.
   - `SCHEMA.md` Gate E download rule, wording only.
   - `PHASE_1.md` 1.12 (the amended line, a #80 note) and the 1.14 run B check.
   - `ASSUMPTIONS.md` I8 (minimum 3.38.0; status unchanged).
   - `CLAUDE.md` seam table.

### Verified

- `uv run pytest`: 602 passed in 361 s.
- `uv run ruff check .`: all checks passed. `uv run ruff format --check .`: 85 files already
  formatted.
- The first attempt at the image tests ran for minutes: the existing network-error tests really
  slept, because `time.sleep` was the default. That is why `sleep` is now looked up at the call,
  and why conftest refuses a real sleep.

### Next

Ron's code review of #80, then his separate go for run B. Run A's links live about until
2026-10-08 (I7, ASSUMED). Expected in B: run A's 228 failed own photos retried from the stored
links and held; its 45 repost entries keep `network: gaierror` (U7).

---

## 2026-10-04 (continued) — Run B, a normal run

### Done

Run B, approved by Ron (#79 D2), run once:
`uv run --env-file .env python -m tlv_hunter.jobs.run_once`, 14:48:40 → 15:00:28 UTC, **exit 0**.
No code change, no git. Runs C and D were not started.

- **Before the run:**
  - The working tree was clean at commit `0d33c35` (Ron's commit of #80).
  - No `.py` file was newer than the last full test run (602 passed), so the suite was not run
    again.
  - `APIFY_TOKEN` loads through `uv run --env-file` (46 characters, never printed).
  - A read-only snapshot of the store after A was saved to
    `data/runs/run_B_2026-10-04/snapshot_before_B.json` (IDs, timestamps, dedup results, image
    entries, file times; no text), for the comparison.
- **Saved in `data/runs/run_B_2026-10-04/`** (gitignored): the JSON log, exit code, times,
  `check_store.txt` and `check_apify.txt` (from `scratch/check_run_B.py`, read-only), and
  `REPORT.md`.
- **`BACKLOG.md`:** item 1 is runs C and D.
- **`ASSUMPTIONS.md`:** evidence added to P6, P19, P20, I6 and I11; no status changed.

### Verified

- **Run:** `since` 2026-10-04T12:40:09.201Z, exactly A's start minus 15 minutes.
  - Apify run `Wz3H9VivgTZgAVZcH` `SUCCEEDED`: 33 rows (5, 11, 11, 0, 0, 6 per group).
  - Skipped 0, dropped 0, no group cut off. No network wait logged.
  - The token appears nowhere in the log.
- **DoD item 2 holds:**
  - 240 posts: 28 new, 5 re-fetched, 0 lost.
  - Every post from A keeps its first `fetched_at`, `is_canonical`, `duplicate_of` and
    `text_hash`. 7 new posts are duplicates of posts from A.
  - 0 canonicals share a hash; 0 duplicates point at a missing or non-canonical post; 0 posts
    without a record.
  - None of the 415 photo files from A was rewritten.
  - `last_success_at` is B's start on all six groups; no `watermark` moved backwards.
  - `5612809662118963` and `733810383372996` returned no row: `consecutive_failures` 1.
- **#80 works on real data:**
  - 214 stored links retried and 214 held, 0 failed, no HTTP error; plus 14 photos of re-fetched
    posts through the batch path.
  - Of run A's 273 failed entries, 228 are now held. The 45 left are all repost entries with
    `network: gaierror` (U7); none is an own photo.
  - **All 53 of run A's photo-less posts now hold at least one photo.**
  - 80 photos of new posts, all held. 723 files against 723 references, both ways, no `.tmp`.
  - Images 107.8 MB, database 2.9 MB.
- **Speed:** 308 photos in 679 s, about 2.2 s each, slower than run A's 1.36 s; no 403, 429 or
  timeout.
- **Cost:** $0.0545, with 33 items and 1 start charged, the same in three reads (the last at
  15:01:28Z). `fetch()` logged $0.005 at the end of the run: the start fee only (P19).

### Not established

The summary line's "55 stored canonicals outside the batch updated" is consistent with the 53
posts, plus 5 canonicals changed by B's new duplicates, less the posts in B's own batch. It is not
broken down exactly: the store does not record which posts a run fetched.

### Next

Ron's separate go for runs C (a normal run killed during the photo download) and D (the recovery).
Each sends the $0.50 cap; worst case $0.455 each.

---

## 2026-10-04 (continued) — Runs C (killed) and D (the recovery)

### Done

Runs C and D, approved by Ron (#79 D2). No code change, no git. C did not need repeating. The
end-of-phase steps of `PHASE_1.md` §3 were not started.

- **Before C:**
  - The working tree's code was unchanged since run B: `tlv_hunter/` and `tests/` were identical
    to commit `0d33c35`, and no `.py` file was newer than B's start.
  - A read-only snapshot of the store (240 posts, 240 records, 723 files, the six
    `GroupWatermark` records) was saved to `data/runs/run_C_2026-10-04/snapshot_before_C.json`.
- **Run C** started at 16:43:29 UTC, 1 h 55 min after B's start, from `scratch/run_C_kill.ps1`
  (`Start-Process`, for the Windows PID).
  - The script waited for thedoor's fetch summary (16:43:54.6), waited 3 s more, and ran
    `taskkill /F /T` at 16:43:59.7, in the photo step.
  - `since` was B's start minus 15 minutes. Apify run `XgWDMjgcuuKDxXksJ`: 30 rows.
- **Run D:** 16:44:59 → 16:46:28 UTC, to the end, **exit 0**.
- **Saved** in `data/runs/run_C_2026-10-04/` and `data/runs/run_D_2026-10-04/` (gitignored): the
  logs, the kill's timestamps, the output of `scratch/check_run_CD.py` (read-only, counts only)
  and a `REPORT.md` each.
- **`BACKLOG.md`:** item 1 is now the end of phase 1, waiting for Ron's go.
- **`ASSUMPTIONS.md`:** evidence added to P1c, P6, P19, P20 and I11; no status changed.

### Verified

- **After C, against the snapshot:**
  - The six watermark records are **identical**.
  - Posts and records are 240 / 240, with 0 new, 0 lost and 0 changed.
  - 4 orphan image files (727 on disk, 723 referenced), all under one post; no `.tmp`.
  - The log has 2 parseable lines and ends at the fetch summary.
- **After D:**
  - `since` was 2026-10-04T14:33:40.722Z, **B's start minus 15 minutes**.
  - 34 rows fetched and 33 kept: one row older than `since` was dropped by `fetch()` and still
    billed (P1c).
  - 266 posts: 26 new, 0 lost. 0 canonicals sharing a hash; 0 duplicates pointing at a missing
    post; 0 posts without a record.
  - **818 files against 818 references, both ways; all 4 of C's orphan files are referenced
    now.**
  - `last_success_at` is D's start on all six groups; no `watermark` moved backwards.
  - No network wait. No stored-link retry: the only failed entries are run A's 45 repost
    entries (U7).
  - D downloaded 95 photos in 74 s.
- **Cost:** C $0.05 (30 items), D $0.056 (34 items), each read over a minute after the run ended.
  The end-of-run figures logged were lower ($0.0485, $0.041; P19).
- **The four runs:** $0.323 + $0.0545 + $0.05 + $0.056 = **$0.4835**, against the $1.82 worst
  case.
- **Tokens:** none in any of the four logs.

### The Phase 1 DoD, item by item (items 1–3)

1. **Met.** Run A against all six groups stored 212 posts and 415 photos.
   - The network dropped during its photo step, and 53 posts were left with no photo.
   - Run B recovered all 53 from the stored links (#80).
   - With C and D, the store now holds 266 posts and 818 photos, every file referenced.
2. **Met.** Run B started 1 h 43 min after A ended. It stored nothing twice:
   - every post from A kept its first `fetched_at` and dedup result;
   - no photo was downloaded again;
   - `last_success_at` became B's start on all six groups, and no watermark moved backwards.
3. **Met.** C was killed in the photo step with `taskkill /F`.
   - It moved no watermark and wrote nothing to the store; it left 4 orphan files.
   - D asked from B's start minus 15 minutes, covering C's window, and stored it once.
   - C's orphan files are referenced now.
   - **One limit:** C's 30 post IDs were not compared with D's row by row, since C's dataset was
     not saved. D asked from the same `since`, 89 s later, with at most 12 rows a group against
     `max_posts` 50.

Item 4 (the `ASSUMED` items of §2) was closed before the runs and not re-checked here.

### Next

Ron decides when to start the end of phase 1 (`PHASE_1.md` §3, `BACKLOG.md` item 1). After
2026-10-08: the free GET on an expired run A link (`BACKLOG.md` item 2).

---

## 2026-10-04 (continued) — End of phase 1, and the source for Tel Aviv areas and streets

### Done

Approved by Ron: the end of phase 1 (`PHASE_1.md` §3). Docs and research only: no code, no paid
run, no git. Phase 2 planning was not started, and Gate B was not opened.

**Part 1, closing the phase:**
- **Figures:** computed read-only from the store (counts only) and the run reports.
- **`RESEARCH.md`:**
  - New §11, the four real runs.
  - Replaced: §1's volume row; §3's cost paragraph, now projected from the runs, with the spike's
    projection kept for the record.
  - Added to: §1's duplicates row and §9's group rates.
  - Every run figure is marked as one day's data.
- **`ASSUMPTIONS.md`:**
  - P7 marked ❌ FALSE (too low); the daily volume is UNKNOWN.
  - P21 added (UNKNOWN: whether the actor cuts posts at 5 photos).
  - A1 split into A1a (✅ VERIFIED) and A1b (❌ FALSE as a published list).
  - Evidence added to D2, D5 and I3.
  - DoD item 4 checked: P1, P5, P9, P6, I6 and P2 are all VERIFIED; none is left.
- **`PHASE_1.md`:** status complete; the DoD verdict per item, with where the evidence is; 1.14
  complete; §3 steps 1–3 done, step 4 researched and not chosen, step 5 not started.
- **`BASELINE.md`:** §12 (phase 1 complete); §14 (the area source row, the image download row).
- **`CLAUDE.md`:** the current-phase line and the `PHASE_1.md` row.
- **`BACKLOG.md`:**
  - The end-of-phase item removed.
  - Item 1 is the free GET on an expired link after 2026-10-08.
  - Item 2 is phase 2 planning, not started, blocked on the area source.
  - The open choice for the area source now names the candidates.

**Part 2, the public source for areas and streets** (`RESEARCH.md` §12): research only. The
sources were read through the `external-contract-verification` skill; no data was downloaded
into the repo.
- **Read:** the municipality's GIS service and open-data portal and their terms; the CBS's GIS
  page, layer readme and methodology; the Population Authority's street register on data.gov.il;
  OpenStreetMap (Nominatim, the ODbL page); Hebrew Wikipedia.
- **Tooling:** two CBS PDFs were read through `pypdf`, run with `uv run --no-project --with pypdf`
  in a throwaway environment, outside the project. Overpass timed out twice, so OSM's
  neighbourhood count was not measured.

### Verified

- **The real runs** (one day, a Sunday):
  - Volume: more than 212 posts in 24 h, two groups cut off at 50; about 13–15 new posts an hour
    in the afternoon.
  - Duplicates: 39 of 266 (14.7%), 12 of them in the same group as their canonical.
  - Rejected: `no_images` 9.4%, `no_text` 3.4%.
  - Photos: 3.66 per post on average, at most 5.
  - Photo download: 1.36, 2.2 and 0.78 s per photo.
  - Cost: $0.0015 per row and $0.005 per start, confirmed on four runs. Projected about
    $20–26/month, against the ~$12–16 accepted.
- **The areas source:** the municipality's `שכונות` open dataset (GIS layer 511) has 71
  neighbourhoods, among them `הצפון הישן - החלק הצפוני` (30) and `הצפון הישן-החלק הדרומי` (31);
  loaded 2024-11-18.
- **The terms:** the open-data portal grants use as-is, with no named licence. The website's
  general terms forbid copying, building a database from the content, and automated access.
  Neighbourhoods, quarters, sub-quarters and statistical areas are open datasets; addresses and
  street lines are not.
- **The municipality's address layer (527):** 52,176 points with street code, street name and
  house number, and no area field.
- **The CBS layer `statistical_areas_2022`:** no neighbourhood or street names in its fields (read
  in its readme, contradicting a search summary). The methodology mentions a separate key file
  assigning *main* streets and neighbourhoods to statistical areas; that file was not read.
- **OpenStreetMap:** `הצפון הישן - החלק הצפוני` is a polygon (way 803404213, `place=suburb`).

### Found

- **No single public source publishes streets per area.** The areas and the Old North split come
  from the municipality's open dataset. Streets per area have to be derived: from OSM (open
  licence) or from the municipality's address layer (not open-licensed).
- **Sources differ on the Old North:** the municipality splits it in two; Madlan splits it in four.
- **The 5-photo cap (P21):** no post has more than 5 media items, and `photo_count` never exceeds
  5 either.
- **The cost may be above the accepted figure:** about $20–26/month projected from one day.

### Next

Ron chooses the area and street source at Gate B (`RESEARCH.md` §12, the points listed there).
Phase 2 planning waits for Ron's go. After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 — Gate B content recorded; the Gate B draft; the 71 areas

### Done

Docs only: no code, no paid call, no git. Ron settled the area source and the content of Gate B
with the review chat. This session recorded them and drafted the names and types; nothing in the
draft is approved.

- **`DECISIONS.md`:**
  - #81–#107, one per approved item, with Ron's reasons where given and "no reason recorded"
    elsewhere.
  - Pointer notes on #50 ("kept as text" is stale since #63), #53 (amended by #87), #57 (settled by
    #105), #71 H (kept by #107) and #74 (closed by #89).
- **`SCHEMA.md`:** a Gate B section marked "DRAFT - awaiting Ron". It contains:
  - The proposed record, `Listing`, and the `Marked[T]` state structure.
  - The 71 areas, verbatim.
  - The translation table.
  - A proposal for where the area files live (`reference/`, created for none of them).
  - The "For Ron's decision" list, 13 points.
  - The gate table shows B as a draft.
- **`BASELINE.md`:**
  - §4: the data path, with code deciding the rejection and the area.
  - §6: price list, entry-date comparable value, floor, size, furnished.
  - §7: rewritten to #81–#88.
  - §9 point 5: "the model could not place" reworded.
  - §13: the flagged-posts row corrected to §5. It was a stale row: §5, `SCHEMA.md` Gate E,
    #63 and invariant 3 all say a flagged post is kept whole, `raw` included.
  - §14: the area-source row and "Open for Ron".
- **`CLAUDE.md`:** the current-phase line; the entry-date trap reworded per #96.
- **`ASSUMPTIONS.md`:**
  - A1a: chosen by Ron and re-read.
  - A1b: source chosen (OSM); its completeness is UNKNOWN.
  - P16: kept as a known limit, with the store count.
- **`BACKLOG.md`:** the rows listed under "Next".
- **`RESEARCH.md`:** not changed. The review chat's figures are below, verified; none was written
  there.

### Verified

- **Layer 511** (`https://gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer/511`), read
  under the `external-contract-verification` skill: 71 features, `ms_shchuna` 1–71 with no gap,
  every `date_import` `18/11/2024 00:59:04`. Fixtures saved: `data/raw/tlv_gis_layer511_rows_2026-10-05.json`
  (no geometry) and `data/raw/tlv_gis_layer511_meta_2026-10-05.json`. Five names have the geresh
  or parenthesis at the logical start: 5, 7, 17, 18, 49.
- **The review chat's figures**, recounted read-only from the store (SQLite opened `mode=ro`,
  script in the session scratchpad):

  | Figure | Review chat | Recount |
  |---|---|---|
  | `sale_post` with a `native_price` | 68 of 266 | 68 of 266. No other post type has one |
  | `native_price` not found in the text | 24 | 24, matching the digits plainly, with `,` / `.` / space thousands separators, or as `Nk` |
  | Below 500 | 3 | 3 (1, 1, 6) |
  | Above 15,000 | 5 | **4** (16,000, 16,500, 16,800, 20,000); 5 if 15,000 itself is counted |
  | Mostly English | 27 | **Not reproduced exactly:** 29 have more Latin than Hebrew letters; 21 above 60% Latin. Definition-dependent |
  | `sharedPost` present | 35 | 35 |
  | Own caption and shared text both | 1 | 1 |
  | A phone | 161 | 161 |
  | More than one phone | 5 | 5 |

### Found

- **13 points for Ron** in the Gate B draft's "For Ron's decision" list. The main ones:
  - Whether the final areas are stored or computed (no field for them is approved).
  - Who applies the translation table, the model or code (#104 against #87's reason).
  - A stated area that maps to several entries: definite or unclear.
  - `native_price` values of 1 and 6 as the fallback price.
  - Who computes the comparable entry date.
  - No period on arnona and house committee.
  - "No restriction" against "not written" for gender.
- `CLAUDE.md` is gitignored (`.gitignore`'s last section), so its change is not in `git status`.

### Next

- Ron approves or corrects the Gate B names and types and answers the "For Ron's decision" list.
- The rest of phase 2 planning waits for Ron's go: `PHASE_2.md`, model and SDK, where
  classification runs, the regression set, Gate D, the reclassify job, the derivation script.
- After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 (continued) — Gate B answers applied; the phase 2 plan, drafted

### Done

Docs and a written plan only: no code, no paid call, no git. Gemini, OSM and the street register
were read from their documentation and open APIs, at no cost.

**Part 1, Ron's answers on Gate B:**
- **`DECISIONS.md`:**
  - #108–#119: Ron's answers to the 13 points; point 13 goes to the phase 2 plan.
  - #120–#122: three card rules the review chat had left out.
  - Pointer notes on #75 A, #85, #86, #87, #91, #95, #96, #103 and #104.
- **`SCHEMA.md`, Gate B:** the answers applied:
  - `Listing` named; an unclear field keeps no value.
  - `areas` stored, with the colour derived from it.
  - `stated_area_names` replaces `stated_areas`; code applies the translation table.
  - The native-price floor of 500; the entry date's parts and its nearest year.
  - `gender` plain; sizes decimal; a basement is -1.
  - The five display labels.
  - **Still a draft**, with two open points; the old list is replaced by them.
- **`BASELINE.md`:**
  - §6: the last-publication time, "1 of N", room size, gender, the year never shown.
  - §7: areas stored at classification time, the translation table applied by code, the colour
    rule.
  - §14: open items.
- **`BACKLOG.md`:**
  - Next: Gate B's two points; the phase 2 plan.
  - Pending rows renumbered to the new decisions.
  - Gate C row: no orange for a user who chose every entry a name covers.
  - Phase 3 UI rows: main time, "1 of N", room size, the year. The row on showing both
    publications is replaced; the #75 A row is changed.
  - Known limits: no period on arnona; table changes not re-derived.

**Part 2, the plan:**
- **`PHASE_2.md`:** new, marked "DRAFT - awaiting Ron". It contains:
  - Goal, DoD, anchors, order of work.
  - Tasks 2.1–2.10, with options and recommendations.
  - The items to close, and a "For Ron's decision" list of 22.
- **`RESEARCH.md`:** §13 (Gemini documentation), §14 (the street register, the OSM extract).
- **`ASSUMPTIONS.md`:**
  - G1–G9 and A1c added.
  - C3 no longer applies.
  - I3 given the cost estimate.
- **`CLAUDE.md`:** the phase line; a `PHASE_2.md` row.

### Verified

- **Gemini documentation, read 2026-10-05** (`RESEARCH.md` §13):
  - Current stable Flash: `gemini-3.8-flash`; Flash-Lite: `gemini-3.5-flash-lite`.
  - Prices: 3.8 Flash $0.75 / $3.75 per 1M tokens through 2026, doubling on 2027-01-01;
    3.5 Flash-Lite $0.30 / $2.50.
  - The free tier's terms forbid personal information and allow human review. The paid tier does
    not train on prompts.
  - Gemini 3 docs strongly recommend temperature 1.0.
  - 3.8 Flash's thinking cannot go below "low".
  - AI Studio's project spend cap is experimental and lags about 10 minutes.
  - `google-genai` 2.28.0 is on PyPI.
- **The street register:**
  - 2,768 official Tel Aviv names and 4,655 synonyms, updated 2026-10-05.
  - The Geofabrik extract is 120 MB, dated 2026-10-03.
- **The store, read-only:**
  - 195 pending canonicals; text averages 523 characters.
  - Candidate regression cases counted.
  - #45's case is in `data/raw/test_posts.json`, not in the store.

### Found

- **Gate B: two points still open.**
  - An entry date with a month and no day.
  - A stated area name that maps to nothing, with a street the table places.
- **Temperature:** `BASELINE.md` §4's `temperature=0` conflicts with the Gemini 3 documentation.
  For Ron (`PHASE_2.md` §4, items 4 and 22).
- **Matching street and area names as written** needs either exact matching or amending invariant
  8 to allow a lookup key (`PHASE_2.md` §2.3). For Ron.
- **Cost:** 3.8 Flash would cost about as much as collection, or more from 2027 (I3).
- **No field counts failed classification attempts.** A post that always fails would be billed on
  every run (`PHASE_2.md` §2.5).

### Next

- Ron answers Gate B's two points, then Gate B is marked approved.
- Ron reviews `PHASE_2.md` and its 22 points.
- The spike (2.1) needs its own go.
- After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 (continued) — Gate B approved; OpenAI as the provider; the phase 2 plan rewritten

### Done

Docs and a written plan only: no code, no paid call, no git. The OpenAI documentation was read,
at no cost. `.env` was not opened.

- **`DECISIONS.md`:**
  - #123–#125: a month with no day is the 1st; "end of February" the 28th; an unmapped area name
    lets the street decide; Gate B approved.
  - #126–#130: OpenAI as the provider; `gpt-6-luna` first; `OPENAI_API_KEY` in the entry point
    only; provider-neutral rules; the revised spike.
  - #131–#145: Ron's answers to the 22 points of the draft plan.
  - Pointer notes on #22, #61, #88, #96 and #115.
- **`SCHEMA.md`:**
  - Gate B marked approved; its open points removed; #123, #124 and the lookup key applied.
  - Gate A's three Gemini mentions made neutral.
  - Two proposals added, not approved: the model's response (`ListingExtraction`) and the Gate E
    failure fields.
- **`CLAUDE.md`:**
  - Invariant 8 widened (#135) and made neutral.
  - The opening line, the phase line, `OPENAI_API_KEY`, the Hebrew trap's wording, the
    `PHASE_2.md` row.
- **`BASELINE.md`:**
  - §4: the data path and the model line, which is settled after the spike.
  - §6: the month rule. §7: #124. §12: neutral. §14: open items.
- **`RESEARCH.md`:**
  - §15 new (OpenAI).
  - §13 marked an alternative, with Ron's AI Studio figures.
  - A note on §5.
- **`ASSUMPTIONS.md`:**
  - O1–O11 added.
  - I3 re-estimated for `gpt-6-luna`.
- **`PHASE_2.md`:** rewritten to the decisions. Approved parts are marked; WAITING parts are
  listed in §4.
- **`BACKLOG.md`:**
  - Next: rows 2 and 3.
  - Pending rows for #126–#145.
  - The concurrency row.
  - A Future row for Gemini's free tier.
- **The `external-contract-verification` skill** (`.claude/`, gitignored): OpenAI links added;
  Gemini marked as the alternative.

### Verified (from the documentation; no call made)

- **The model:**
  - `gpt-6-luna` is listed as a current model, as an alias only, with no dated snapshot.
  - Prices: $0.10 input, $0.01 cached, $0.125 cache write, $0.50 output per 1M tokens; batch half.
    These match the review chat's read.
  - Reasoning effort defaults to `medium`; `none` is available.
  - Temperature is accepted only at `none`.
- **Strict structured outputs:** every field required, `additionalProperties: false`, `$defs` and
  `anyOf` supported, `format: date` supported.
- **Caching:**
  - Prompt caching is implicit by default and would write each post into the cache. An explicit
    breakpoint avoids that.
  - The minimum cacheable prefix is 1,024 tokens; a prefix lives 30 minutes.
- **Data:**
  - API data is not used for training.
  - Abuse-monitoring logs keep up to 30 days.
  - The Responses API stores responses for 30 days unless `store: false`.
- **Limits:**
  - Tier 1: 500 requests and 500,000 tokens a minute; the free tier does not support the model.
  - The hard spend limit is not instantaneous.
- **SDK:** `openai` 3.24.0.
- **Not read:** the Services Agreement (HTTP 403).

### Found

- **Spike estimate:** about $0.10, at worst $0.30, against the $2 cap.
- **Running cost:** about $1–11 a month for `gpt-6-luna`; estimates until measured.
- **Retention:** posts with phone numbers sit in OpenAI's abuse-monitoring logs up to 30 days.
  Only an approved Zero Data Retention request avoids that. For Ron.
- **The model alias** can change what answers without notice; Gate B's `model_name` records what
  was sent. For Ron.

### Next

- Ron answers `PHASE_2.md` §4: the spike's go, the two sets of names, the first run's cap, and
  the OpenAI points.
- Before the spike, Ron reads the organization's usage tier.
- After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 (continued) — Ron's answers to `PHASE_2.md` §4; spike 2.1 run

### Done

The spike was paid and run on Ron's go; there is no package code and no git. `.env` was not opened
by hand: the script read the key from the environment and never printed it.

- **`DECISIONS.md`:**
  - #146–#156: the abuse log accepted, `store: false`, effort from `none`, the reported model value
    logged, explicit caching, the response model's names, the Gate E failure fields, the $1 cap, the
    `data/labeling/` files, the dedicated project, the spike's go.
  - Notes on #137 and #139.
- **`SCHEMA.md`:**
  - `ListingExtraction` approved.
  - Gate E amended: `classification_failures`, `last_classification_error`, `schema_version` 2.
    Docs only; the code comes with task 2.5.
- **`PHASE_2.md`:** statuses, the spike's result, the prefix finding, the measured cost, §4.
- **`BASELINE.md`:** §4's model line (`store: false`, caching, effort, the abuse log); §14.
- **`CLAUDE.md`:** the phase line.
- **`BACKLOG.md`:** the next rows (the dashboard check, the setting), pending rows, and a regression
  row for the 20 spike posts.
- **The spike:**
  - **Scripts** (throwaway, under `scratch/`): `spike_2_1_select.py`, `spike_2_1_openai.py`,
    `spike_2_1_analyse.py`, run with `uv run --with openai==3.24.0`.
  - **Calls:** 123, no errors and no cap stop.
  - **Under `data/`:** the raw responses in `data/raw/openai_spike_2026-10-05/`; the posts, their
    `listing_id`s, the results and the review page in `data/spike_openai_2026-10-05/`.
  - **Report:** `docs/SPIKE_2_1_2026-10-05.md`.
- **`ASSUMPTIONS.md`:**
  - O1, O3, O5, O7 and O10 verified; O4 and O11 in part.
  - O12 added (❌ FALSE: temperature 0 is not deterministic).
  - I3 measured; O2 and O6 notes.

### Verified

- **The schema** derived from the approved `ListingExtraction` passed strict mode unchanged; 120 of
  120 answers validated.
- **Caching:** a 2,514-token prefix (instructions and schema), written once, then read. The post
  was never cached.
- **Reasoning:** 0 tokens at `none`; 153 a call on average at `low`.
- **Cost:** $0.00019 per post at `none`, $0.00029 at `low`; $0.0273 in all by the usage metadata.
- **Model:** every response reported `gpt-6-luna`, with no dated version.
- **Probes:**
  - `incomplete`: billed, cut JSON.
  - `allOf`: 400 `invalid_json_schema`.
  - A wrong key: 401 `invalid_api_key`.

### Found

- **Temperature 0 is not deterministic:** one post's `post_nature` changed between passes.
- **Area names come back with Hebrew prefix letters** ("בצפון הישן"). The lookup key or the table
  has to handle them.
- **Two of the crude case labels were wrong:** the "seeking" and "Jaffa" picks are sale posts, and
  the model said `for_sale` every time.
- **Monthly estimate:** about $1.2–2.6, from the measured tokens.

### Next

- Ron reads the dashboard figure and compares it with $0.0273.
- Ron chooses the setting (recommended: `none` with temperature 0, confirmed on the regression
  set) and how prefix letters are handled.
- Ron and the review chat judge the answers in `data/spike_openai_2026-10-05/review.html`.
- The first paid run waits for its own go.
- After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 (continued) — Ron's decisions after the spike; plans for tasks 2.2 and 2.3

### Done

Docs only: no code, no paid call, no git, no download.

- **`DECISIONS.md`:**
  - #157 the setting: effort `none`, temperature 0.
  - #158 prefix letters handled by code.
  - #159 sublet only when the offer is temporary.
  - #160 one amount for several charges is unclear.
  - #161 "דירת N שותפים".
  - #162 a name not in the text is dropped; the model never computes.
  - #163 the source text is never touched.
  - #164 no go for the first paid run.
  - #165 a real seeking post and a real Jaffa post in the regression set.
  - #166 the spike's prompt is a first version.
  - Notes on #93, #101, #106, #135 and #148.
- **`CLAUDE.md`:** invariant 14 (#163); a domain trap on prefix letters (#158).
- **`SCHEMA.md`, Gate B:**
  - `post_nature` (#159), `rooms` (#161), `arnona` (#160).
  - The rules: never computes, names not in the text dropped, matching with prefixes, the source
    text untouched.
- **`BASELINE.md`:** §4 the setting; §7 the prefixes and dropped names; §14; the header.
- **`PHASE_2.md`:**
  - Status, anchors, 2.4, 2.5, 2.6 and 2.8 updated.
  - **The plans for tasks 2.2 and 2.3**, under their sections, marked WAITING.
  - §4 replaced by the 16 points the plans need.
- **`BACKLOG.md`:** next row 3, pending rows for #157–#163, a regression row for #165.

### Answers to the review chat's two questions about the spike (nothing changed)

1. **Do the agreement figures count 3 and 3.0 as the same answer?** Yes. The figures in
   `docs/SPIKE_2_1_2026-10-05.md` compare the answers after validation against the pydantic
   model, where 3 and 3.0 are equal. Recounted from the raw responses (read-only), comparing the
   JSON text field by field, pass 1 against pass 2:

   | Setting | Fields differing as raw text | By value (the report's figure) | Only 3 against 3.0 | Posts identical as raw text |
   |---|---|---|---|---|
   | `none_default` | 21 | 14 | 7 | 7 of 20 |
   | `none_t0` | 11 | 8 | 3 | 12 of 20 |
   | `low` | 11 | 9 | 2 | 12 of 20 |

   So the report's agreement (10, 14 and 13 identical posts; 96.96%, 98.26%, 98.04% of fields)
   already treats 3 and 3.0 as the same. Looking at the raw files by eye shows more differences
   than the report counts, and those extra ones are only 3 against 3.0.

2. **What does `prompt_cache_retention: "24h"` mean when the request set `ttl: "30m"`?** Every
   response echoes `prompt_cache_options` as sent (`mode: "explicit"`, `ttl: "30m"`) and also
   `prompt_cache_retention: "24h"`. The documentation (read 2026-10-05, `RESEARCH.md` §15 sources)
   says:
   - For GPT-5.6 and later, `prompt_cache_options.ttl` "controls the minimum cache lifetime, not
     this maximum application-state retention period".
   - A prefix stays usable at least 30 minutes after its last use, "though OpenAI may retain it
     longer".
   - Prompt caching may store encrypted key/value tensors in GPU-local storage as application
     state, "not retained after the 24-hour expiration".
   - "When Zero Data Retention is not enabled for an organization, all queries use extended prompt
     caching" (`24h`).

   So "24h" is the maximum time the cached state may be kept: the organization has no Zero Data
   Retention (#146). Only the instructions and the schema are cached (#150), never a post.

### Found while planning

- **#65 forbids automatic migration**, and a `listings` table changes the store's layout. Plan A
  proposes an explicit, hand-run migration command.
- **The existing normalization keeps hyphens.** Folding them in the shared steps would change
  every stored `text_hash`; plan B proposes a key-only step (against #135's wording).
- **`PHASE_1.md`'s anchor says no module reads YAML directly.** Plan B proposes one reader for
  `reference/`.
- **The 15 m buffer needs metres,** so `pyproj` too, beyond #133's two libraries.
- **`osmium`, `shapely` and `pyproj` all have Windows and Linux wheels** for Python 3.12 (PyPI,
  2026-10-05).

### Next

- Ron answers `PHASE_2.md` §4 (16 points).
- Ron reads the spike's cost in the OpenAI dashboard and compares it with $0.0273.
- After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 (continued) — The model decides the area; task 2.2 and a reduced task 2.3 built

### Done

There were no paid calls, no downloads and no git. The real store was not opened, only a copy of
it.

**Decisions:**
- **#167:** the model decides the area. It supersedes #84, #85, #87, #133–#136 and #158, and
  parts of #86, #110 and #111.
- **#168:** what leaves phase 2; invariant 8 goes back to "a hash only".
- **#169:** a street table as an aid, for later.
- **#170:** the known limit for a post with only a street.
- **#171:** the labelling page picks areas from the 71.
- **#172, #173:** reporting a wrong classification, in phase 2 and in phase 3.
- **#174:** task 2.2 approved with Ron's answers.
- **#175:** task 2.3, reduced.
- Superseded and partial notes on the entries they replace (none deleted).

**Code, task 2.2:**
- `tlv_hunter/contracts/listing.py` (new): `Listing`, `Marked`, `PhoneName`, with the approved
  validators.
- `tlv_hunter/contracts/post_lifecycle.py`:
  - `classification_failures` and `last_classification_error`; `schema_version` 2.
  - `from_stored_json`, which reads version-1 documents as version 2.
  - A record built at any other version is refused.
- `tlv_hunter/store/base.py`, `local_json.py`, `sqlite.py`: `save_classification`, `get_listing`,
  `find_pending_canonicals`. SQLite gets a `listings` table under its own layout row,
  `store.listings` 1, created when absent.
- `tlv_hunter/dedup/stage_a.py`: #89. An archived post with no reason that is reposted returns to
  `"active"` when it has a `Listing`. The lookup is lazy: only for such posts.
- `tlv_hunter/premodel/rejects.py`: `initial_lifecycle` passes the two new fields.

**Code, task 2.3 reduced:**
- `reference/areas.yaml`: 71 entries from the fixture, the five labels, a source block.
- `tlv_hunter/areas/reference.py`: `load_areas()`, the only reader of `reference/`.

**Tests:**
- New: `tests/test_listing.py`, `tests/test_reference_areas.py`.
- Contract tests for the three methods, on both stores. Among them: `save_classification` leaves
  every stored `RawPost` identical (invariant 14), and a crash inside it rolls back.
- SQLite: a layout-1 file opens with its posts and records byte-identical; a layout mismatch on
  `store.listings` is refused; an orphan `listings` row is refused.
- Dedup #89, active and pending.
- Version-1 records, read and written back.
- Updated for the change: the lifecycle helpers (version 2), `test_premodel_rejects`,
  `test_stubs`, `test_config` (the YAML anchor), `test_watermark_store` (three layout rows), and
  `get_listing` passed through in two test wrappers.

**Docs:**
- `SCHEMA.md`: `areas` from the model and in `ListingExtraction`; the matching rules removed;
  colloquial names as examples.
- `CLAUDE.md`: invariant 8; the store row; `areas/reference.py`; the domain trap; the phase line.
- `PHASE_1.md`: the YAML anchor reworded.
- `BASELINE.md`: §4, §7 and §14 rewritten for #167.
- `PHASE_2.md`:
  - 2.2 built, with its deviations; 2.3 rewritten as reduced.
  - 2.4, 2.6, 2.7, 2.8 and 2.9 updated; §3 and §4.
  - The superseded 2.3 kept in an appendix, since the file is not in git yet.
- `ASSUMPTIONS.md`: A1b and A1c no longer needed.
- `RESEARCH.md`: a note on §14.
- `BACKLOG.md`: next, pending, Gate C and phase 3 rows, a known limit, Future.

### Verified

- **`uv run pytest`:** 673 passed in 368 s.
- **`uv run ruff check .`:** all checks passed. **`uv run ruff format --check .`:** 92 files
  already formatted.
- **Before the change,** a run that overlapped my edits gave 601 passed and 1 failed
  (`test_stub_names_say_stub`, which pins #33's stub-era rule); it was not a clean baseline.
- **On a copy of `data/store/tlv_hunter.sqlite3`**, opened with the new code:
  - 266 posts, 266 lifecycle records and 6 watermarks byte-identical.
  - Layout rows `state` 1, `store` 1, and the new `store.listings` 1.
  - All 266 records read as version 2 with 0 and `None`.
  - `find_pending_canonicals` returns 195.
  - The real file's SHA-256 was the same before and after.

### Deviations from the approved plan

- **Version-1 records are read through `PostLifecycle.from_stored_json`,** not a before-validator.
  A before-validator makes pydantic validate stored JSON in strict Python mode, which refused the
  datetime strings: 21 tests failed that way before the change. The approved effect is unchanged.
  A record built in code must now be version 2 with both fields.
- **`test_stub_names_say_stub`** no longer asserts that `contracts/listing.py` is absent.
- **`Marked` uses Python 3.12 type parameters** (ruff UP046).

### Conflicts found

None open. Three rules were changed as Ron decided, each with its test: invariant 8 (#168),
`PHASE_1.md`'s YAML anchor (#175), and #33's stub-era file rule. The real store gains the empty
`listings` table and its layout row the first time anything opens it with this code: option C,
approved (#174).

### Next

- Ron reviews the code of tasks 2.2 and 2.3.
- Then the plan for task 2.4.
- Open in `PHASE_2.md` §4: how the regression set compares streets and area names (proposed: as
  written, ignoring surrounding whitespace).
- Ron reads the spike's cost in the OpenAI dashboard and compares it with $0.0273.
- After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 (continued) — Ron accepts 2.2 and 2.3; the plans for tasks 2.4 and 2.5

### Done

Plans only. No code, no paid call, no git, no download. The real store was not opened.

**Decisions** (recorded first, as Ron asked):
- **#176:** the code of 2.2 and 2.3 accepted, `from_stored_json` included.
- **#177:** `areas` is the only location field labelled blind. Streets and area names are neither
  labelled nor compared; Ron judges them in the review report. Notes added on #142 and #143.

**Docs:**
- `PHASE_2.md`:
  - The status line.
  - 2.2 and 2.3 marked accepted.
  - 2.6 and 2.7 changed for #177.
  - **The plan for task 2.4:** layout, the call, the completion rules, the rejection module, tokens
    and cost, tests, order, conflicts.
  - **The plan for task 2.5:** the command, the loop, the attempts table, the cap, the log, the
    dropped-names record, #140, tests, order, conflicts.
  - §4 replaced by 14 open points.
- **`docs/INSTRUCTIONS_V1_DRAFT.md` (new):** the full proposed instructions text, and a 64-row
  table: each rule, its decision, its sentence. 11 rows are marked proposed. The file is to be
  deleted when the text moves into the package.
- `BACKLOG.md`: the header line; next row 3; the regression set's pending row (#177).

### Verified

- **Prompt size:** the proposed instructions render to 8,722 characters with the 71 areas (from
  `load_areas()`), against the spike's 4,790. The token estimate is a range from that count; the
  prefix was not tokenized.
- **The spike's raw responses carry no `areas`** (they predate #167). The fixture keys were read
  with a script, and no post content was printed.
- `openai` is not a project dependency; the spike ran it through `uv run --with`.

### Found while planning

- **Tests and fixtures:**
  - The spike's answers cannot serve unchanged as version 1 answers in tests; the plan adds
    `areas` in memory.
  - A refusal, a 429, a 5xx and a timeout were never observed, so their tests rest on the
    documentation.
- **Settings and records:**
  - `Listing` has no field for the setting (effort, temperature). Proposed: `prompt_version` covers
    the whole request apart from the post, pinned by a fingerprint test.
  - The names dropped by #162 have no approved record for the review report. Proposed: a
    JSON-lines file per run.
- **Rules:**
  - A blank `other_city` string would reject a Tel Aviv post. Proposed: read as `None`.
  - `CLAUDE.md` names `run_once` the only constructor of the production store; `classify_pending`
    needs it too.
  - #177's wording could also take `other_city` off the labelling page. The plan keeps it, and asks
    Ron.

### Next

- Ron answers `PHASE_2.md` §4 (14 points), and reads `docs/INSTRUCTIONS_V1_DRAFT.md`.
- Then the code of task 2.4, starting with the `external-contract-verification` skill on the
  Responses API. Then 2.5.
- Ron reads the spike's cost in the OpenAI dashboard and compares it with $0.0273.
- After 2026-10-08: the free GET on an expired run A link.

## 2026-10-05 (continued) — Ron's answers; tasks 2.4 and 2.5 built

### Done

There were no paid calls and no git. The real store was not opened.

**Decisions**, recorded first:
- **#178:** the instructions approved with all 11 proposed rows, plus two additions:
  - a two-digit year is 20YY;
  - a well-known landmark places the apartment when there is no area name and no street.
- **#179:** the 2.4 plan approved.
- **#180:** #162's check also covers `other_city`.
- **#181:** the failure shapes the spike never saw are tested from the documentation.
- **#182:** the 2.5 plan approved, with option A for the dropped names.
- **#183:** `other_city` stays labelled blind.
- Notes on #142 and #143 (from #177).

**The `external-contract-verification` skill, reading only.** No call was made. Read: the
error-codes, structured-outputs, rate-limits and spend-limits guides, and the source of `openai`
3.24.0 (`_exceptions.py`, `_client.py`, the schema helper). Recorded as `ASSUMPTIONS.md` O13
(ASSUMED). Two findings:
- the error-codes page now lists `credit_balance_exhausted`, not `insufficient_quota`;
- `openai` 3.24.0 depends on `httpx2`.

**Code, task 2.4:**
- `pyproject.toml`, `uv.lock`: `openai==3.24.0`.
- `contracts/listing_extraction.py`: `ListingExtraction`, `EntryDateParts`, `PhoneNamePair`.
- `parsing/prices.py`: `NATIVE_PRICE_FLOOR`, `native_price_fallback`.
- `parsing/datetimes.py`: `nearest_occurrence`.
- `classify/`:
  - `base.py`: the protocol returns `Listing`; `ClassificationError` and its kinds.
  - `instructions.txt`: the approved text.
  - `instructions.py`: the renderer, the setting, `PROMPT_VERSION` "1" and its fingerprint.
  - `complete.py`, `cost.py`, `transport.py`, `openai_classifier.py`.
  - `classifier_stub.py` deleted.
- `postmodel/rejects.py`: `model_reason`, `classified_lifecycle`, `failed_lifecycle`.

**Code, task 2.5:**
- `jobs/common.py`, moved from `run_once.py`, which now uses it.
- `classification_run.py`: the loop and the attempts table.
- `jobs/classify_pending.py`: the command.

**Tests:**
- New:
  - `test_listing_extraction.py`, `test_classify_complete.py`, `test_classify_instructions.py`;
  - `test_openai_classifier.py`, `test_openai_transport.py`, `test_postmodel_rejects.py`;
  - `test_classification_run.py`, `test_classify_pending_job.py`.
- Extended: `test_parsing.py`.
- Changed: `test_stubs.py` (the classifier stub is gone); `conftest.py` (the spike 2.1 fixtures,
  `post_with_text`, `SQLITE_FILENAME` from `jobs/common.py`).

**Docs:**
- `DECISIONS.md`, `ASSUMPTIONS.md` (O13).
- `SCHEMA.md`: `other_city`, the dropped-names rule, the area rules, the year.
- `BASELINE.md` §7.
- `PHASE_2.md`:
  - status;
  - "built" notes and deviations under both plans;
  - the rule table moved in from the draft, with the two additions;
  - the size, 9,025 characters;
  - §4.
- `CLAUDE.md`: the phase line, the commands, the `classify/` row, the instructions, `postmodel/`,
  and the job commands.
- `docs/INSTRUCTIONS_V1_DRAFT.md` deleted (the text is in the package).
- `BACKLOG.md`.

### Verified

- **`uv run pytest`:** 873 passed in 146 s, 200 more than the 673 before.
  - The first full run gave 872 passed and 1 failed: `test_no_module_outside_config_reads_yaml_directly`,
    which greps source text, found "areas.yaml" in a docstring of `classify/instructions.py`.
  - That module reads no YAML. The docstring was reworded, and the run repeated clean.
- **`uv run ruff check .`:** all checks passed. **`uv run ruff format --check .`:** 110 files
  already formatted.

- **The derived schema** equals the spike's `schema_sent.json` except for `areas` and the `value`
  descriptions; a test pins this.
- **All 120 spike answers** validate once `areas` is added. Without it they are refused.
- **The 20 `none_t0` answers** complete into `Listing`s through a fake transport, each with its own
  post read in place.
- **`run_once`'s 57 tests** pass unchanged after the move to `jobs/common.py`.

### Deviations from the approved plans

Listed under each plan in `PHASE_2.md`:
- the billed usage goes on the meter's `CallRecord`, not on the error;
- `classify_completed` sits beside `classify`;
- the setting lives in `instructions.py`;
- the classifier refuses to start on a fingerprint mismatch;
- a `not_found` kind;
- the current 429 codes;
- code reads a year below 100 as 20YY;
- `job_logging()` and `log_failure()` helpers;
- the error text is cut at 200 characters;
- a discarded failure is not counted;
- `--cap` above 0;
- no dropped-names file when nothing is written.

### Found

- **`CLAUDE.md` is gitignored** (`.gitignore` line 36), though it calls itself "checked into the
  codebase": its edits do not show in `git status`.
- **The prefix ב replaces the ה** of "הצפון הישן" ("בצפון הישן"). If the model returns the name
  without the prefix, #162's exact match drops it. The instructions ask for the name as written, with
  prefix letters.

### Next

- Ron reviews the code of 2.4 and 2.5.
- The plan for 2.6, the regression set; its passes are the first real calls, on their own go.
- Ron reads the spike's cost in the OpenAI dashboard and compares it with $0.0273.
- After 2026-10-08: the free GET on an expired run A link.
