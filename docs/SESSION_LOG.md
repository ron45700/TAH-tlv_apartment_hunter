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
