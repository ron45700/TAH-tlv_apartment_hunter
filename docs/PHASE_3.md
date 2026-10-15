# Phase 3 — The dashboard (semi-macro)

**Status:** a plan, written 2026-10-10 and revised the same day after Ron's answers. **Approved by Ron (2026-10-10):**
the content of Gate C (`DECISIONS.md` #242–#257) and its 31 open points (#262–#287); the task order and the DoD; the
technical choices (§5, #258–#260); the area grouping (§6, #261); Gate C's names and types and R1–R9 (#288, R7 amended
by #291); the plans for 3.4 and 3.5 (#289, #290). **Built:** 3.4 (2026-10-10, round 3), 3.5 (2026-10-11, round 4);
the admin created on the production store by Ron (2026-10-11); `jobs/reset_admin_password.py` (#294, 2026-10-11, round
5). **3.6: plan and its 16 points approved (#295–#300, 2026-10-11); built in round 6 (2026-10-11).** **Round 7
(2026-10-11):** #302 built (a post with no written price always at the bottom); Ron's direction for the site recorded
(#303–#315); 3.7's plan written, with 26 points. **Round 8 (2026-10-12): 3.7's plan and its 26 points approved, with
Ron's notes on the mock (#316–#331)**; built in the round: one sublet switch per profile (#317) and the orange-location
cap (#320); a new mock. **Round 9 (2026-10-12): points 27–30 and Ron's notes on the round-8 mock approved
(#332–#339); the bar redesigned; `Profile.from_stored_json`; 3.7's build step 1 built (the store generation counter and
its migration command, #316). **Round 10 (2026-10-13): Ron ran the migration on the production store; Ron's notes on
the round-9 mock (#340–#343); 3.7's build step 2 built: the read-only API for a guest, served from a dated copy of the
store.** **Round 11 (2026-10-13): this file's lost block restored; Ron's answers on round 10 (#344–#348: points 31 and 32,
the screen sizes, the mock retired); 3.7's build step 3 built: the site itself for a guest (`frontend/`, the list and
the opened post, `policy/colours.py`).** **Round 12 (2026-10-14): Ron's answers on round 11 (#349–#351: 3.7's rebuilt
text and points 33–35 accepted; the card's buttons packed to the left); 3.7's build steps 4 and 5 built: the filter
bar, sign-in, sign-up, the forced password change, the preferences page and the session cookie (`web/auth.py`).**
**Round 13 (2026-10-14): Ron's answers on round 12 (#352, #353: points 36–39; the phone's bar compacted, built); Ron's
studio rule for the model (#354, instructions version 5 written, its regression run planned in `PHASE_2.md`); 3.7's build
step 6 built: viewed, "mark as not viewed", the "lied" flag and the "wrong classification" report (`web/writes.py`).**
**Rounds 14–18:** step 7 measured, then A, C, D built and measured again (both targets met). **Round 19 (2026-10-15): points
57–59 decided (#385–#387, the scratch stores deleted); 3.7 complete (#388); 3.8's plan written.** **Round 20 (2026-10-15):
3.8's plan and points 60–76 approved (#389–#406); 3.8's build steps 1–3 built (the admin's read API, the read pages, keys
and users).** **Round 21 (2026-10-15): 3.8's steps 4–6 built and checked (the post writes, corrections, the DoD 5 walk);
points 77–83 wait for Ron.** **Round 22 (2026-10-15): points 77–83 decided (#407–#413) and 78–83
built; round 21's deviation 1 accepted (#414); Ron tries the pages, then 3.8 closes.** No code before a task's plan is approved; no paid call before its
own go.
**Owner:** Ron
**Parent:** `BASELINE.md` §12 · **Schema:** `SCHEMA.md`, Gates A, B, C, E (approved), Gate D
(the key, #230, #232) · **Research:** `RESEARCH.md` §16 (the area grouping check)

**Phase goal:** anyone on the tailnet opens the site and scrolls and filters the real active posts without signing in
(#306, #307); Ron and his friends, signed in, save their profile, mark posts viewed, flag and report them, in a polished
UI (#257); the admin works the rejected, pending and archive lists, the flags, the reports and
the corrections. No Telegram (Phase 4), no scheduler (Phase 5): collection and classification stay commands Ron starts.

**Phase DoD (approved by Ron, 2026-10-10):**
1. **`BASELINE.md` §12's line:** Ron filters and sees real apartments in a browser, through Tailscale Serve, on his
   laptop in Docker.
2. A second account is created with a one-time key (#243) and signs in with a username and a password (#242); the
   admin resets its password (#242) and cancels an unused key (#243).
3. Each user's two search options (#245, #246, #247) filter and order the posts as `BASELINE.md` §8 says; the area is
   orange or not per user (#250); viewed posts come after unviewed ones (#62, #253).
4. A post the Gate D key ties to another shows as one card (#231); the four known pairs (§4) are the first check.
5. A flag ("lied") and a "wrong classification" report move a post to rejected for everyone; the admin restores it
   (#251), corrects a field (#256), or leaves it out; the report and the correction are kept (#255).
6. **DoD 4 moved from Phase 2 (#225), with `ASSUMPTIONS.md` I3 (#228):** a real working day is measured: the number of
   calls, the tokens and the cost of a day's classification, from the usage metadata and then the OpenAI bill; every
   paid run under its cap. Ron also judges how the interface looks on that day.
7. Tests pin: no user action writes a `RawPost` or a `Listing` (invariant 14); no per-user value is written on a post
   (invariant 12); no outgoing request carries a personal identifier (invariant 15).
8. The per-user YAML is gone (#47), and the items of §3 are resolved or explicitly re-planned.

---

## 3.0 Mandatory anchors

| Anchor | Source | State |
|---|---|---|
| Gate C's content | `DECISIONS.md` #242–#257, #262–#287 | Approved 2026-10-10 |
| Gate C's names and types; the Gate E amendments | `SCHEMA.md`, Gate C, and Gate E (amended 2026-10-10) | Approved 2026-10-10 (#288) |
| The technical choices: the framework, the journal mode, compare and set | #258, #259, #260 | Approved 2026-10-10 |
| The area grouping | #261 | Approved 2026-10-10 |
| The card, the field states, the colours | `BASELINE.md` §6, §7, §8 | Approved; binding on the UI (#257) |
| The same-listing grouping is derived by the Gate D key and never written on a post; computed once for all users, held in the site's memory, computed again only when the store changed | #230, #231, #232, #301 | Approved |
| The other-city name on the card is derived | #214 (`postmodel.rejects.other_city_name`) | Approved |
| Collection never filters by a user's criteria; per-user data never on the post | Invariants 12, 14 | In force |
| No personal identifier in any outgoing request | Invariant 15, #212 | In force |
| Libraries and site modules are chosen when this phase is planned, not before | `CLAUDE.md`; #23 | The framework chosen (#258); each library is added with its task's approved plan |

---

## Order of work (approved by Ron, 2026-10-10)

```
3.1 Gate C names and types  ┐
3.2 technical choices        ├─ Ron's decisions, no code
3.3 area grouping            ┘
  →  3.4 store: the Gate C records, the Gate E amendments, the lifecycle writes  →  3.5 accounts
  →  3.6 evaluation (policy/): corrections, the same-listing grouping, the two options, the order
  →  3.7 the site: lists, cards, profile, viewed, flag, report (the polished UI, #257)
  →  3.8 the admin lists  →  3.9 serving on the tailnet  →  3.10 the measured working day
```

3.6 needs no UI and can be built and tested beside 3.5. 3.7's visual design starts once 3.6 returns real data.

---

## 3.1 Gate C: names and types — DECIDED (#288, 2026-10-10)

`SCHEMA.md`, Gate C, approved: `User`, `SignupKey`, `Session`, `Profile` with two `SearchOption`s, `ViewedPost`,
`ClassificationReport`, `FieldCorrection`; points R1–R9; the Gate E amendments, written into Gate E. Nothing left for
Ron.

## 3.2 Technical choices — DECIDED (#258–#260, 2026-10-10)

The framework (§5.1, option A), the rollback journal with an explicit busy timeout (§5.2), compare and set for every
`PostLifecycle` writer (§5.3). Sessions (#263) and where the records live (#267) are decided with Gate C's points. What is
left is in the 3.4 and 3.5 plans.

## 3.3 Area grouping — DECIDED (#261, 2026-10-10)

§6 as proposed, with the four undecided entries in regular groups. Nothing left for Ron.

## 3.4 Store: the Gate C records and the lifecycle writes — PLAN APPROVED (#289); BUILT 2026-10-10 (round 3)

**Approved by Ron, with its eight points as proposed (#289)**; Gate C's names are approved (#288). **Built in round 3
(2026-10-10)**, with the deviations listed in `SESSION_LOG.md` (2026-10-10, round 3); one gap is open for Ron: R7
and the method table (below, "Open after the build"). No paid call, no network call; the production store is not
opened for writing by any step of this task.

**Scope.** (a) The eighth seam and its SQLite store; (b) the Gate C records as contracts; (c) `PostLifecycle` version 3
and `"misclassified"`; (d) compare and set for every `PostLifecycle` writer, in both stores, and every caller (#260);
(e) the explicit busy timeout (#259); (f) the per-user YAML removed (#47). **Not in 3.4:** the account logic (3.5), the
evaluation (3.6), the site (3.7), any write of a report or a flag (3.7, 3.8).

### (a) The eighth seam (#267; name approved, #289)

**`userdata/`, interface `UserDataStore`.** Its row in `CLAUDE.md`'s seam table:

| Module | Contract |
|---|---|
| `userdata/` | `UserDataStore`: what users and the admin write through the site — `User`, `SignupKey`, `Session`, `Profile`, `ViewedPost`, `ClassificationReport`, `FieldCorrection`. Not part of Repository; it never reads or writes a `RawPost`, `Listing` or `PostLifecycle`. SQLite only, in the same file as `store/` and `state/`, with its own tables and layout row |

**Methods (a Protocol in `userdata/base.py`, SQLite in `userdata/sqlite.py`; SQLite only, as `state/` is, #64):**

| Method | Contract |
|---|---|
| `create_admin(user, profile) -> User` | Inserts the admin and their profile in one transaction; raises if an admin exists or the username is taken |
| `create_user(user, profile, key_hash, now) -> User` | One transaction: finds the key by its hash, refuses unless it is usable (`KeyNotUsable`), marks it used by the new user at `now`, inserts the user and the profile; raises `UsernameTaken` (case-insensitive) |
| `get_user(user_id)`, `find_user_by_username(username)`, `list_users()` | Reads; the username is compared in lower case |
| `save_user(record, expected) -> User` | Compare and set, as for `PostLifecycle` below (sign-in counters, reset, disable) |
| `add_key(key)`, `list_keys()`, `save_key(record, expected)` | `save_key` is compare and set (cancel) |
| `find_key_by_hash(key_hash) -> SignupKey \| None` | The key with that hash, used or not; sign-up's lookup (#293, added 2026-10-11) |
| `add_session(session)`, `find_session(token_hash)` | |
| `end_session(token_hash, now)`, `end_sessions(user_id, now, keep=None)` | Sets `ended_at` on one session, or on every open session of the user except `keep` (#263, R3, R7) |
| `get_profile(user_id)`, `save_profile(profile)` | Whole-record replace (point 4 below) |
| `mark_viewed(user_id, listing_id, at)` | Inserts only if absent: a reopen keeps the first time (#276) |
| `unmark_viewed(user_id, listing_ids)`, `viewed_listing_ids(user_id) -> set[str]` | |
| `add_report(report)` | Refuses a second open report by the same reporter for the same post (#278, R4) |
| `find_reports(listing_id=None, status=None)`, `save_report(record, expected)` | `save_report` is compare and set |
| `add_correction(correction)` | Refuses a second correction in force for the same post and field |
| `find_corrections(listing_id=None, in_force=True)`, `save_correction(record, expected)` | `save_correction` is compare and set (removal) |

**Storage**, as #65 stores records: one JSON document per record, written and read by the pydantic model, plus lookup
columns only: `users` (`user_id` key, `username_lower` unique), `signup_keys` (`key_id` key, `key_hash` unique),
`sessions` (`token_hash` key, `user_id`), `profiles` (`user_id` key), `viewed_posts` (key `user_id` + `listing_id`),
`reports` (`report_id` key, `listing_id`, `reported_by`, `status`), `corrections` (`correction_id` key, `listing_id`,
`field`, and a unique index on `listing_id` + `field` over the corrections in force). A `layout_version` row `userdata`
= 1; a mismatch refuses to open, naming the module (#65). The same minimum SQLite version check as `store/` (3.38.0).
One connection per operation; writes in `BEGIN IMMEDIATE`.

**Two seams, two transactions.** A report (in `userdata/`) and the post's move to rejected (`PostLifecycle`, in
`store/`) cannot be one transaction without merging the seams. Proposed order: the report first, then the lifecycle;
if the lifecycle write fails, the report is stored and the admin's reports list shows "report stored, post not
rejected", with a retry (3.8). Point 3 below.

### (b) The Gate C records as contracts

`contracts/user.py` (`User`), `contracts/signup_key.py` (`SignupKey`), `contracts/session.py` (`Session`),
`contracts/profile.py` (`Profile`, `SearchOption`, `RangeCriterion`, `DateRangeCriterion`, `CriterionLevel`),
`contracts/viewed_post.py` (`ViewedPost`), `contracts/classification_report.py` (`ClassificationReport`,
`ReportableField`), `contracts/field_correction.py` (`FieldCorrection`). Strict pydantic models like `PostLifecycle`,
datetimes checked by `require_utc`. Every rule of Gate C's tables is a validator: the username's characters and length;
the pairs set together (`used_by`/`used_at`, `resolved_by`/`resolved_at`, `removed_by`/`removed_at`); `signup_key_id`
`None` exactly for the admin; ranges with at least one end and `min` ≤ `max`; half rooms; floor ≥ -1; `size_sqm` `None`
in `room`; `price_min` ≤ `price_max`; areas 1–71, sorted, distinct; the note ≤ 500 characters; `fields` non-empty and
distinct. `FieldCorrection.model_value` and `corrected_value` are validated against the Gate B type of `field`, read from
`Listing`'s own field definition, so there is no second copy of Gate B's types (#284).

### (c) `PostLifecycle` version 3

`"misclassified"` added to `rejection_reason`; the consistency rule "`"flagged"` or `"misclassified"` requires
`flagged_by` and `flagged_at`"; `schema_version` 3 (#285). `PostLifecycle.from_stored_json` reads a version-1 or
version-2 document as version 3 (no field differs between 2 and 3); a record is written back as version 3 on its next save,
as version 2 was (#152, task 2.2). The value goes last in the `rejection_reason` `Literal` of
`contracts/post_lifecycle.py`, which is where Gate E's order is written today (#279); `postmodel/rederive.MODEL_REASONS`
is unchanged (it is not a model reason). Gate E's approved text is
amended in `SCHEMA.md` only when Ron approves E-1 to E-5.

### (d) Compare and set for every `PostLifecycle` writer (#260)

**The contract change (both stores, `store/base.py`, `store/sqlite.py`, `store/local_json.py`):**
- `save_lifecycle(record, *, expected: PostLifecycle | None) -> PostLifecycle`. `expected=None`: writes only if the post
  has no lifecycle record. Otherwise: writes only if the stored record, read through `PostLifecycle.from_stored_json`,
  **equals** `expected` (model equality, so a version-1 document read as version 3 compares equal to what the writer
  read). Else raises `StaleRecordError(listing_id)` (new, in `store/base.py`) and writes nothing. `KeyError` if the post
  is not stored, as today.
- `save_classification(listing, lifecycle, *, expected: PostLifecycle)`: the same check on the lifecycle; on a stale
  record neither the `Listing` nor the lifecycle is written.
- **SQLite:** the read, the comparison and the write are in the one `BEGIN IMMEDIATE` transaction, so no other writer
  can come between them. **local_json:** read, compare, write, with no lock: correct for one process only; it is the test
  store (point 8).
- `upsert_with_lifecycle` is unchanged: it already creates only.

**Every caller (found by search, 2026-10-10):**

| Caller | Today | With compare and set | On `StaleRecordError` |
|---|---|---|---|
| `pipeline._repair_missing_lifecycles` | `save_lifecycle(initial)` | `expected=None` | Another writer created it: logged, skipped |
| `pipeline._store` (stored canonicals outside the batch; batch posts after `upsert_with_lifecycle`) | `save_lifecycle(record)` with the record dedup built | `expected=` the record dedup **read** from the store; `DedupResult` gains those records. A post that had no record is written by `upsert_with_lifecycle` alone | **Merge, then retry** (point 2): re-read; the site's fields (`flagged_by`, `flagged_at`, `flag_note`, a `"flagged"` or `"misclassified"` state and reason, and `classification_failures` / `last_classification_error` set back by the admin's retry) are taken from the fresh record; the run's fields (`last_published_at`, `images`, a state change from a repost of an archived post or from the pre-model re-check) from the run's. When both changed the state, the flag or report wins. At most 3 attempts; then the run fails and no watermark moves (invariant 2) |
| `classification_run` (`save_classification`, `_save_failure`) | Re-reads right before writing (#182) | `expected=` that fresh read | Re-read once; if still `"pending"`, derive again and write; else `"discarded"`, as today |
| `jobs/rederive_rejections` | Re-reads, raises if the status changed | `expected=` that read | Not written; reported, as a changed record is today |
| `reclassification_run.apply_proposals` | Re-reads; "not written" if changed (#220) | `expected=` that read | "not written", listed; exit code 2 (#220) |
| The site (3.7, 3.8) | — | `expected=` the record the page read | The user is told the post changed; the page reloads |

The contract test `test_save_lifecycle_is_whole_record_replace_and_last_write_wins` is replaced by the compare-and-set
tests below. `CLAUDE.md`'s Repository row and store-writer paragraph change with it (written this round: the decision;
the method signature when built).

### (e) The busy timeout (#259)

Every `sqlite3.connect` in `store/`, `state/`, `userdata/` and `jobs/common.raw_post_rows` passes `timeout=` explicitly,
from one constant. Python 3.12's documented default is 5.0 seconds ("How many seconds the connection should wait before
raising an OperationalError when a table is locked", docs.python.org, 3.12.15, read 2026-10-10). **Proposed: 10
seconds** (point 6); measured on the working day (3.10).

### (f) The per-user YAML removed (#47)

`config/users/ron.yaml`, `UserConfig` and `user()` in `config/base.py` and `config/yaml_config.py`, and the three uses in
`tests/test_config.py` (lines 57, 118, 124). No other code calls them (search, 2026-10-10).

### Tests (3.4)

1. **Contracts:** one test per validator above; a JSON round trip per record; `schema_version` 1 on each; a `Session` or
   key never holds a raw token (only the hash field exists).
2. **`PostLifecycle` v3:** `"misclassified"` without `flagged_by` is refused; a version-1 and a version-2 document read as
   version 3; a v3 record dumps `schema_version` 3.
3. **Repository contract, both stores:** an unchanged record is written; a changed one raises `StaleRecordError` and
   leaves the store byte-identical; `expected=None` creates only; a stored version-1 document compares equal to its read;
   `save_classification` on a stale record writes neither the `Listing` nor the lifecycle. Replaces the last-write-wins
   test.
4. **The pipeline:** a flag set between dedup's read and the store step survives the run, and the run's
   `last_published_at` and images survive the flag; three conflicts in a row fail the run and move no watermark.
5. **`classification_run`, `rederive_rejections`, `apply_reclassify`:** each conflict path in the table above.
6. **`UserDataStore` contract (SQLite, temporary file):** every method; username uniqueness ignores case; a key creates
   one account (a second `create_user` with it is refused, also when the first failed on the username — the key stays
   usable then); a cancelled key is refused; one open report per reporter and post; one correction in force per post and
   field; `mark_viewed` keeps the first time; compare and set on `save_user`, `save_key`, `save_report`,
   `save_correction`; the `userdata` layout row, and refusal on a mismatch.
7. **The seams stay apart:** opening and writing `UserDataStore` on a copy of a store file leaves `raw_posts`,
   `post_lifecycle`, `listings` and `group_watermarks` byte-identical (invariants 12, 14).
8. **The busy timeout:** every connection in the four modules is opened with the constant (a test that patches
   `sqlite3.connect` and checks the argument).
9. **Config:** the YAML user tests removed; `YamlConfig` still reads `collection.yaml`.
10. The suite stays offline (the socket guard); no test reads the production store.

### What I could not verify (3.4)

- That model equality is the right comparison for every stored lifecycle document: true for version 1 and 2 as read
  today (`from_stored_json`); checked by test 3 when built, not now.
- How often the pipeline would meet a conflict: depends on how often users flag during a run (up to 30 minutes of image
  download, #77 D5b). Not measurable before the site exists.
- The busy timeout's effect: only the working day (3.10) shows whether 10 seconds is enough.

### Points for Ron (3.4)

1. The seam's name, `userdata/` and `UserDataStore`, and its row for `CLAUDE.md`.
2. The pipeline's merge on a conflict (the table above) and its 3 attempts before the run fails.
3. A report and the post's move to rejected are two transactions in two seams; the report is written first, and the
   admin's list shows one whose post was not rejected, with a retry.
4. `save_profile` is a whole-record replace with no compare and set: only its own user writes a profile (two open tabs:
   the last save wins).
5. `StaleRecordError` as the exception's name.
6. The busy timeout: 10 seconds.
7. The method names of the table in (a).
8. local_json's compare and set is check-then-write with no lock: right for the tests, not for two processes.

### Open after the build (for Ron, before 3.5) — SETTLED by Ron, 2026-10-11 (#291–#293)

Point 1: two calls in a fixed order, the disable first; R7 reworded (#291), built in 3.5's `disable_user`. Point 2:
stays as built, the run fails; Phase 5 looks at it again with the retention job (#292, `BACKLOG.md`). Point 3:
`find_key_by_hash` added (#293); sign-up uses it. The text below is the question as it was put.

1. **R7 and the method table.** R7 says disabling a user ends their sessions "in the same transaction"; the approved
   method table has `save_user` (the disable) and `end_sessions` as two methods, so two transactions. Built as tabled;
   disabling is 3.5's, so nothing depends on it yet. Either a method that does both, or `save_user` ending the
   sessions when it disables, or R7 read as "in the same action".
2. **A conflict the merge rule does not cover:** the run and the site both changed the state and the fresh record has no
   flag or report (for example the admin restored an archived post that a repost brought back). Built: the run fails at
   once, no watermark moves, the next run reads the new record (`run_merge.py`).
3. **How sign-up knows the key's id:** `create_user(user, profile, key_hash, now)` checks that the key with that hash is
   `user.signup_key_id`; 3.5's sign-up finds the id through `list_keys()` (no method finds a key by its hash).

## 3.5 Accounts — PLAN APPROVED (#290, 2026-10-10); BUILT 2026-10-11 (round 4)

**Approved by Ron, with its four points as proposed, the dependency included (#290).** **Built in round 4
(2026-10-11)** with #293 (`find_key_by_hash`) and #291 (disable, then end the sessions); the deviations are listed in
`SESSION_LOG.md` (2026-10-11). `argon2-cffi` 25.1.0 and `argon2-cffi-bindings` 26.1.0 are installed. `create_admin`
is tested on a temporary store only: Ron runs it on the production store himself. **Ron ran it on 2026-10-11:** the
backup was made, the admin was created, and the stored `RawPost` documents were identical to the backup's.

**Added 2026-10-11 (round 5, #294): `jobs/reset_admin_password.py`**, the admin's fallback for a forgotten password (a
reset needs a signed-in admin, and `create_admin` refuses once an admin exists). In the pattern of `create_admin`: it
refuses when there is no admin (read before any question and before the backup, so nothing is written), asks for the
new password twice with `getpass`, refuses two that differ or one under 8 characters, makes the dated backup, sets the
new hash through `actions.reset_admin_password` (`must_change_password` `False`, the failure count 0,
`password_changed_at`), ends every session of the admin, and checks the stored `RawPost`s against the backup. The
action takes no session token and is called only by this command. Tested on a temporary store only
(`tests/test_reset_admin_password_job.py`, two tests in `tests/test_accounts.py`); not run on the production store.

**The documentation re-read on 2026-10-11** (argon2-cffi.readthedocs.io, "argon2-cffi 25.1.0 documentation";
pypi.org JSON) and checked against the installed package: the table below holds. Two details differ from what it
records or leaves out: `get_default_parameters()` is in `argon2.profiles`, not at the top of `argon2` (on this Windows
laptop it equals `RFC_9106_LOW_MEMORY`); `InvalidHashError` is a `ValueError`, not a `VerificationError`, so a wrong
password and a broken stored hash are told apart. 25.1.0's files were uploaded on 2025-06-03. One hash at the
production parameters took 0.056 s on the laptop, one check 0.057 s (one measurement each).

**Scope.** The account logic over `UserDataStore`, with no web code: the one-time admin command (#244); keys (#243,
#266); sign-up, sign-in with the delay (#264), sign-out; sessions (#263); the password change and the admin's reset
(#262); disabling and enabling a user (#265). The cookie and the pages are 3.7's; the admin's pages are 3.8's.

### Modules

- **`accounts/`, plain modules** (like `postmodel/`: no storage of their own; they call `UserDataStore` and take `now`
  as an argument):
  - `accounts/passwords.py`: the one place that hashes and checks passwords (Argon2id, below): `hash_password`,
    `check_password` (returns a result, never raises on a wrong password), `needs_rehash`, the length check (8 or more,
    #262), and a fixed dummy hash for unknown usernames (#264, R1).
  - `accounts/tokens.py`: new keys (128 random bits) and session tokens (256 random bits) from Python's `secrets`; their
    SHA-256; new opaque ids (32 hex characters).
  - `accounts/actions.py`: `sign_up(store, key, username, password, now)`, `sign_in(store, username, password, now)` →
    a session token or a refusal (wrong, delayed with the seconds to wait, disabled, must change password), `sign_out`,
    `session_user(store, token, now)` (valid or not, #263), `change_password` (ends the other sessions, R3),
    `reset_password` by the admin (temporary password, `must_change_password`, every session ended, the failure count
    to 0, #262, #263), `disable_user` / `enable_user` (#265, R7, R8), `issue_key(store, label, now)` → the key, shown
    once (#266), `cancel_key` (#243). The admin-only checks are here, not in the pages.
- **`jobs/create_admin.py`, a one-time command on the machine (#244):** asks for the username and the password twice
  with `getpass` (never on the command line, never logged), refuses if an admin exists, writes the admin and their
  profile through `UserDataStore.create_admin`. It writes the production file, but only the `userdata` tables: a new store
  writer, which `CLAUDE.md`'s writer paragraph must name (point 3). It reads no key and calls no network.
- **Cookie attributes, for 3.7 (recorded here, not built):** proposed `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`,
  30 days. Not verified against FastAPI's documentation yet; 3.7 does that.

### The dependency for Argon2id: `argon2-cffi` (read 2026-10-10 under the `external-contract-verification` skill)

| What | What the documentation says |
|---|---|
| Package | `argon2-cffi` **25.1.0** on PyPI; licence MIT; `requires_python >= 3.8`; depends on `argon2-cffi-bindings` (pypi.org JSON API) |
| Bindings | `argon2-cffi-bindings` **26.1.0**, `requires_python >= 3.10`; `cp310-abi3` wheels (they cover CPython 3.12) for `win_amd64`, `manylinux_2_28_x86_64` and `manylinux_2_28_aarch64`, uploaded 2026-08-20 |
| API (argon2-cffi.readthedocs.io, "argon2-cffi 25.1.0 documentation") | `PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, encoding='utf-8', type=Type.ID)`. The defaults are `argon2.profiles.RFC_9106_LOW_MEMORY` (about 64 MiB), "but they may vary depending on the platform" (`get_default_parameters()`, added in 25.1.0). `hash(password)` returns the encoded hash with a random salt; `verify(hash, password)` returns `True` or raises `VerifyMismatchError` (a `VerificationError`), `InvalidHashError` for a malformed hash; `check_needs_rehash(hash)`, recommended after each successful sign-in; `PasswordHasher.from_parameters(params)`; `profiles.CHEAPEST` is "for testing only" |
| Guidance (OWASP Password Storage Cheat Sheet, read 2026-10-10, no date on the page) | Argon2id first, "with a minimum configuration of 19 MiB of memory, an iteration count of 2, and 1 degree of parallelism"; scrypt only where Argon2id is unavailable |

**Proposed use:** `PasswordHasher.from_parameters(argon2.profiles.RFC_9106_LOW_MEMORY)`, named explicitly so the
parameters do not change with the platform; 64 MiB and 3 iterations is above OWASP's minimum. `check_needs_rehash` after
a successful sign-in, rehashing then (a `save_user` compare and set). Tests pass `profiles.CHEAPEST` in, never the
production profile. Added with `uv add argon2-cffi` once Ron approves; it is the first new runtime dependency of Phase 3
(FastAPI and uvicorn come with 3.7's plan).

### Tests (3.5)

1. **Passwords:** a hash verifies; a wrong password is a refusal, not an exception; fewer than 8 characters is refused; the
   stored string starts with `$argon2id$`; the production hasher's parameters equal `RFC_9106_LOW_MEMORY`; no password
   appears in any log record (a log capture over every action).
2. **Sign-up:** with a usable key it creates the user, the profile with #268's defaults, and marks the key used; an unknown,
   used or cancelled key is refused; a username with another letter case, with a Hebrew letter, of 2 or 33 characters is
   refused (#262).
3. **Sign-in and the delay:** a success resets the count; the 5th failure starts the delay; an attempt 29 seconds later is
   refused without a password check, 30 seconds later is checked (R1); an unknown username gets the same answer and runs a
   check against the dummy hash; a disabled user is refused; a user who must change the password gets only that.
4. **Sessions:** valid for 30 days from sign-in, not after (R5); sign-out ends one; the admin's reset ends all; the user's
   own change ends the others and keeps the current one (R3); disabling ends all (R7); only the token's hash is stored.
5. **Keys:** issued keys are shown once (the record holds only the hash); a cancelled key stays cancelled (#266); a used
   key cannot be cancelled.
6. **Admin rules:** only the admin can issue, cancel, reset, disable; the admin cannot be disabled (R8).
7. **`create_admin`:** creates the one admin with no key; a second run is refused; it reads the password through `getpass`
   (patched in the test) and prints neither the password nor any hash.
8. Invariant 15: no action makes an outgoing request (the socket guard covers it).

### What I could not verify (3.5)

- ~~`argon2-cffi` 25.1.0's release date~~: read on 2026-10-11, 2025-06-03 (pypi.org JSON for the version).
- That the bindings' wheel installs in the container's base image: depends on the image chosen in 3.9 (ASSUMED until then).
- ~~`get_default_parameters()` on Windows~~: read on 2026-10-11, equal to `RFC_9106_LOW_MEMORY` (`argon2.profiles`).
- The time one hash takes on the laptop and the home server, and the memory under several sign-ins at once (64 MiB
  each): not measured; small for a few users.

### Points for Ron (3.5)

1. The module names: `accounts/` (`passwords.py`, `tokens.py`, `actions.py`) and `jobs/create_admin.py`.
2. The dependency `argon2-cffi`, with the parameters named explicitly (`RFC_9106_LOW_MEMORY`).
3. `create_admin` is a new command that writes the production file (the `userdata` tables only); `CLAUDE.md`'s writer
   paragraph names it.
4. No command to issue keys before the admin's pages (3.8): the first friend signs up after 3.8.

## 3.6 Evaluation (`policy/`) — PLAN APPROVED (#295–#300, 2026-10-11); BUILT 2026-10-11 (round 6)

**Amended after the build by:** #302 (a post with no written price always at the bottom; (d)'s tier rule), #317 (one sublet switch per profile, not per option; (d)), #320 (an orange location caps the tier at the middle; (d), (f)), #321 (parking not written shown "לא צוין", not "none"; (d), point 9). #318 and #319 confirmed points of it as built.

**The content is approved** (#245–#256, #268–#287, R2 of #288); Gate C's names are approved (#288). **The plan and its
16 points were approved by Ron on 2026-10-11:** points 1, 2, 3, 5, 7, 10, 11, 13, 14, 15, 16 as proposed (#295); point 4,
a correction of `other_city` outranks the native location (#296); point 6, the earliest post (#297); point 8, an unknown
preference is not met (#298); point 9, parking not written is unknown (#299); point 12, option (b) (#300). Ron's
clarification #301 (the grouping computed once for all users, held in memory) is for 3.7. **Built in round 6**, with
the deviations listed in `SESSION_LOG.md` (2026-10-11, round 6); the four-pair check was run read-only at the build (§4).
The text below is the plan as written in round 5; where a point was decided otherwise, the decision rules.

**Scope.** (a) The post as a user sees it: the `Listing` with the corrections in force applied, and every reader of it;
(b) the restore's derived state, as a pure function (the write is 3.8's); (c) the Gate D key and the cards it derives,
never stored; (d) the evaluation of a post against one user's profile, the two search options; (e) the order of a
user's list, viewed after unviewed; (f) the area's colour per user. **Not in 3.6:** any write (a flag, a report, a
correction, a restore, a viewed mark: 3.7, 3.8); the pages and the API (3.7); alerts (Phase 4: they read what 3.6
derives); the admin lists (3.8).

**What every module of 3.6 keeps** (`BASELINE.md` §2 principle 6; invariants 12, 14): pure functions over records the
caller has read; **nothing written** (no Repository write method, no `UserDataStore` write method is called; one
function reads image files, read-only); **no model call** and no network; no per-user value on a post. The only
readers of the store are the loader in (c), which takes a Repository opened by its caller, and the caller's own reads
of `UserDataStore` (`find_corrections`, `get_profile`, `viewed_listing_ids`), passed in as values.

### (a) The post as a user sees it (#256, #281, #287)

**`postmodel/seen.py`** (new, a plain module beside `rejects.py`):

| Function or type | Contract |
|---|---|
| `SeenListing` (frozen dataclass) | `listing: Listing`, the post as users see it, a valid Gate B `Listing`; `corrected: frozenset[ReportableField]`, the fields a correction in force replaced (for the card's "corrected by hand" mark, #256) |
| `seen_listing(listing, corrections) -> SeenListing` | Applies every correction **in force** (`removed_at` `None`) of `listing.listing_id` over a copy: the field takes `corrected_value`. A removed correction is ignored. Raises `ValueError` for a correction of another post, or two in force on one field (the store forbids it; #284). The result is validated as a `Listing` (`model_validate` of the dump with the fields replaced), so it obeys Gate B's rules. **The stored `Listing` is never edited** (#256). With no correction it returns the `Listing` itself and an empty set |

**The one gap the validation meets — `price_source`** (point 3): Gate B requires `price_source` `None` exactly when
`price` is `"not_written"`. A correction of `price` from `"not_written"` to a written or unclear value, or the reverse,
breaks that rule in the copy. Proposed: in the seen copy, `price_source` becomes `None` when the corrected `price` is
`"not_written"`, and `"text"` when the model's was `None` and the corrected one is not (the admin read it in the post's
text); otherwise it is kept. `price_source` is not a reportable field, so nothing else moves it.

**Every reader of the post as a user sees it** (`SCHEMA.md`, Gate C, "The post a user sees"):

| Reader | Where | What it reads |
|---|---|---|
| The evaluation, the order, the area's colour | `policy/` (d)–(f) | `SeenListing.listing` of the card's shown post |
| The card (3.7): every field, the "corrected by hand" marks, the city | 3.7's wiring | `SeenListing`; the city through `postmodel.rejects.other_city_name(post, seen.listing)` (#214, below) |
| The restore's derived state | `postmodel.rejects.restored_lifecycle` (b) | `SeenListing.listing` |
| The Gate D key | `dedup/stage_b.py` (c) | `SeenListing.listing` of each compared post (#287) |
| The admin's rejected list (3.8) | 3.8's wiring | the city through `other_city_name(post, seen.listing)` |

Nothing reads `Listing` directly for a user. The corrections come from one `UserDataStore.find_corrections()` call
(every correction in force, all posts), grouped by `listing_id` by the caller.

### (b) The restore's derived state (#251, #281–#283)

**Where it lives: `postmodel/rejects.py`, beside `classified_lifecycle`.** One new pure function:

| Function | Contract |
|---|---|
| `restored_lifecycle(existing, post, seen) -> PostLifecycle` | `existing` is the post's record with a flag or a report (`flagged_by` set); `seen` is `SeenListing.listing` of the post. Returns the record with `flagged_by`, `flagged_at`, `flag_note` cleared and the state derived: when `existing.state` is `"archived"`, it stays `"archived"` and `rejection_reason` becomes `model_reason(post, seen)` (`None` allowed, Gate E) (#283); otherwise `"active"` when `model_reason(post, seen)` is `None`, else `"rejected"` with that reason (#251, #281, #282). Every other field (`last_published_at`, `images`, the failure fields) is kept. Raises `ValueError` for a record with no flag and no report, or whose `listing_id` is not the post's |

**How it reuses `postmodel.rejects`:** the reason comes from **`model_reason(post, listing)`**, the function
`classified_lifecycle` already uses — Gate E's order, `other_city` first through `other_city_ruling` (Facebook's location
field when usable, else the model's city, #214), then `post_nature`. There is no second copy of the order or of the
city rule. The only difference from a classification is the `Listing` passed: the seen one. `rederive.MODEL_REASONS`
is unchanged. **A pre-model reason** (`no_text`, `no_images`) cannot apply: a flag or a report is made on a card, and only
an active post has a card.

**What 3.8 adds around it (not 3.6):** read the record, the `RawPost`, the `Listing` and the corrections; call
`seen_listing` then `restored_lifecycle`; write with `save_lifecycle(…, expected=the record read)` (#260); mark every open
or left-out report of the post `"restored"` (#278, #286) through `save_report`. The order of those writes is 3.8's plan.

**The other-city name** (#214, option A): the card, the rejected list and the restore all go through
`other_city_ruling` / `other_city_name` over the seen `Listing`; never `Listing.other_city` alone. For `26e8a28b…` the
card shows "רמת גן" while its `other_city` is null (its `native_location` decides). **A correction of `other_city`
meets #214** (point 4): by #214 the native locality decides "even when the model returned one", so a correction of
`other_city` changes the result only for a post with no usable `native_location`.

### (c) The same-listing grouping, derived by the Gate D key (#230–#232, #287), never stored (#231)

**`dedup/stage_b.py`** (new, a plain module beside `stage_a.py`: reads, writes nothing):

| Function or type | Contract |
|---|---|
| `KeyPost` (frozen dataclass) | `post: RawPost`, `lifecycle: PostLifecycle`, `seen: SeenListing`, `photo_hashes: frozenset[str]` |
| `PhotoHashes` | An in-process memo: `of(store_root, lifecycle) -> frozenset[str]`, the SHA-256 of each stored photo file (`PostImage.local_path` under `<store_root>`), keyed by the file's path, size and modification time. Kept in memory only, never written (#231). A missing file adds nothing |
| `load_key_posts(store, corrections, store_root, photos) -> KeyInputs` | Read-only. `KeyInputs.members`: the compared posts — canonical (`is_canonical` `True`), a stored `text_hash`, `"active"`, with a `Listing` — as the 2.10 rules define them (#226, #230), each with its seen `Listing`. `KeyInputs.duplicates`: every dedup A duplicate, by its `duplicate_of`. Uses `query()`, `get_lifecycle`, `get_listing` (no Repository change) |
| `tied_pairs(members) -> tuple[TiedPair, ...]` | The key (#230, rule 1 as amended by #232): two members with **different** text hashes, `posted_at` at most 72 hours apart (inclusive, as `gate_d`), tie when (1) they share a phone that is not an agent number **and** the fields rule matches, or (2) they share a photo hash **and** (a shared non-agent phone **or** the fields rule). **Nothing else ties.** Agent numbers: found in 4 or more members. The fields rule: both prices written and equal as sets, both rooms written and equal, an area in common, **read on the seen `Listing`** (#287). `TiedPair` holds the two ids and which rule fired. Pairs are looked for only among members that share a non-agent phone or a photo hash (both rules need one), not over every pair |
| `cards(inputs, pairs) -> tuple[Card, ...]` | Every member in exactly one card. **A card** = a connected group of tied members (point 5) and, for each, its dedup A duplicates. `Card.shown_id`: the post the card shows (point 6); `Card.canonical_ids`: the members, by `posted_at` then `listing_id`; `Card.post_ids`: the members and their dedup A duplicates (what `ViewedPost` and "mark as not viewed" cover, `SCHEMA.md` `ViewedPost`); `Card.last_published_at`: the latest of the members' `last_published_at` (each already holds its dedup A duplicates', Gate E) — the card's main time (#122); `Card.publications`: `(listing_id, posted_at)` of every post of the card, earliest first — the repost log's input; its first entry is the earliest `posted_at` (#75 A) |

**Single implementation** (`CLAUDE.md`): the fields rule and the agent-number count already exist in
`gate_d/candidates.py` (`matched_fields`, `agent_numbers`, `WINDOW`, `AGENT_NUMBER_POSTS`); the key is defined as "among
the posts the 2.10 rules compare" (#230). Proposed: `stage_b` imports them, and `gate_d` stays the evidence (its own
rules, its page) and decides nothing (point 7).

**Not tied, on purpose** (from the notes of `PHASE_2.md` 2.10, #231): a post waiting for its classification (no
`Listing`); a rejected or archived post (a flagged or reported one included); dedup A duplicates (compared through their
canonical). Phase 4 must not alert a post the key ties to an earlier one (`BACKLOG.md`); 3.6 provides `Card`, which
Phase 4 reads.

**Measured on the real store, read-only (2026-10-11).** A scratch script (scratchpad, not in the repo) opened the store
with `SqliteRepository(read_only=True)`, counted the `userdata` rows over a `mode=ro` connection, read the image files,
and ran the key as above with `gate_d`'s `matched_fields` and `agent_numbers`; the store file's SHA-256 was
`04cefd603c8b…` before and after.
- **The store:** 266 posts; 139 members (active canonicals with a `Listing`); 38 pending; no correction, no report, no
  viewed record, no session; one user.
- **The four known pairs (§4) still come out tied, and nothing else:** 4 tied pairs, 4 cards of two posts. `54ecb1d0…` /
  `00f17259…` (rule 1), `7253eefa…` / `40f7f193…` (rule 2), `e81273e6…` / `8ae80944…` (both rules), `9136a715…` /
  `9a6252c1…` (rule 2). All eight active; none has a dedup A duplicate. Agent numbers: 2. The same result as on
  2026-10-08 (the store has not changed since then: 266 posts, 139 members).
- **Times on Ron's laptop (one run each):** reading the posts (`query`) 0.058 s; `get_lifecycle` and `get_listing` for
  every post, 532 reads, 0.336 s; the SHA-256 of the 620 photo files of the members, 0.669 s (cache state of the disk not
  controlled); the pairs over every pair of members 35.0 ms, over the members sharing a phone or a photo 0.8 ms (the
  same 4 pairs).
- **Scale, synthetic:** the 139 members copied 10 and 36 times (posted 4 days apart, phones and photo hashes made distinct
  per copy, so no copy ties another): 1,390 members, 8 ms with the shared-phone-or-photo search (every pair: 0.89 s);
  5,004 members, 21 ms (every pair not run).
- **Reading:** the key itself stays fast as the store grows; **what grows is reading the store and hashing the photos.**
  A linear estimate for a store of 40 days (about 8,500 posts at run A's 212 a day; not measured): about 2 s for
  `query`, about 11 s for the per-post reads, and 10–20 s to hash the photos cold. Hence the in-process photo memo above,
  and point 13.

### (d) The evaluation of a post against a profile (#245–#247, #268–#275, R2)

**`policy/evaluate.py`** (new); `policy/base.py`'s Protocol becomes `evaluate`; `policy/policy_stub.py` is removed
(point 15).

| Function or type | Contract |
|---|---|
| `evaluate(seen, profile, now) -> Evaluation` | `seen` is the `SeenListing` of the card's shown post; `now` a UTC datetime (`require_utc`). Pure |
| `Evaluation` (frozen, not stored; names proposed, point 2) | `listing_id`; `shown: bool`; `option: "room" / "whole_apartment" / None` (the option that admits it); `kind_marked: bool` (#273); `tier: "preferences_met" / "critical_met" / "unknown" / None` (`None` when not shown); `fields: Mapping[str, FieldState]`, `FieldState` = `"match"` / `"mismatch"` / `"not_written"` / `"unclear"` / `"not_applied"`, one entry per profile category; `missing_important: frozenset` (`price`, `entry_date` not written, `BASELINE.md` §6); `area_orange: bool` (f); `women_only_icon: bool`; `corrected: frozenset` (from `seen`) |

**Which option evaluates a post** (`SCHEMA.md`, Gate C, "Rules with no field of their own"):
- `apartment_kind` written `"room"` → the `room` option; `"whole_apartment"` → `whole_apartment`. Not shown when that
  option is off (#245).
- **A sublet** (`post_nature` `"sublet_offer"`): through the same option's values, shown only when the option is on
  **and** its `include_sublets` is on (#246, #274). A `"rental_offer"` ignores the switch.
- **A post of unclear or unwritten kind** (#273): evaluated against **every enabled option** (a sublet needing that
  option's switch); shown when one admits it, always in the `"unknown"` tier (the bottom), `kind_marked` `True`. Which
  option's colours the card shows when both admit it: point 11.
- Only `"rental_offer"` and `"sublet_offer"` posts are ever active (Gate E's reasons), so no other nature reaches here.

**Each category, as one outcome: met, failed, or unknown** (unknown = the post's value is `"not_written"` or
`"unclear"`). A category with no value in the option (`[]`, `None`) is `"not_applied"` and has no effect (§8 "Don't
care").

| Category | Level | Met when | Read from the seen `Listing` |
|---|---|---|---|
| Area | critical, fixed (`areas` non-empty) | any of the post's areas is in the option's (#110) | `areas`; `[]` is unknown |
| Price | critical, fixed (`price_min` or `price_max` set) | the **lowest** amount within the set ends, inclusive (#95) | `price` |
| "Women only" | critical while `hide_women_only` | `gender` is not `"women_only"`; with the switch off, a `"women_only"` post is shown with `women_only_icon` | `gender` (plain: never unknown, #117) |
| Rooms | the criterion's `level` | within `min`/`max`, inclusive; halves allowed (#271) | `rooms` (the total in the apartment, #97) |
| Floor | `level` | within the range, inclusive; -1 a basement (#271) | `floor` |
| Size | `level`; **`whole_apartment` only** (#247) | within the range, inclusive | `size_sqm` |
| Broker / parking / balcony | the level set (`CriterionLevel`) | fixed wanted values (#269): broker `False`, parking `True`, balcony `True` | `broker`, `parking`, `balcony` |
| Entry date | `level` | within `earliest`/`latest`, inclusive. **"immediate" compares as the UTC calendar date of `now`** (#270, R2) | `entry_date` |

**From outcomes to what is shown** (`BASELINE.md` §8): a **failed critical** category → not shown. Otherwise the tier:
an **unknown critical** category → `"unknown"` (the bottom); else every preference met → `"preferences_met"`; else
`"critical_met"`. How an unknown **preference** counts is point 8; parking that is not written (shown "none" on the card,
§6) is point 9. **The field states for the card** (§6): met → `"match"`, failed → `"mismatch"`, `"not_written"` and
`"unclear"` as stored; `missing_important` for a price or an entry date not written.

### (e) The order of a user's list (`BASELINE.md` §8; #62, #253, #276)

**`policy/order.py`** (new):

| Function | Contract |
|---|---|
| `card_viewed(card, viewed_ids) -> bool` | `True` when any of `card.post_ids` is in `viewed_ids` (the user's `viewed_listing_ids`), so a card stays viewed when a further publication joins it (#253) |
| `ordered(entries, viewed_ids) -> list[(Card, Evaluation)]` | Drops what is not shown; then **all unviewed cards before all viewed ones** (#62); inside each, `"preferences_met"`, then `"critical_met"`, then `"unknown"`; inside a tier, the newest `card.last_published_at` first, then `shown_id` (point 10) |

### (f) The area's colour per user (`BASELINE.md` §7, §8; #110, #112, #113, #250, #275)

In `evaluate`, against the option that evaluates the post: **no areas** → `"unclear"` when the post gives a street or an
area name (`streets` or `stated_area_names` non-empty), else `"not_written"`; **one area** → definite, never orange;
**two or more** → orange, **unless every one of them is in the option's `areas`** (#250); with the option's `areas` `[]`,
orange (#275). Computed per user at evaluation, never written (invariant 12).

### Tests (3.6)

1. **The seen `Listing`:** each reportable field corrected; a removed correction ignored; two fields corrected; the
   stored `Listing` unchanged (equal before and after); `corrected` lists exactly the replaced fields; a correction of
   another post, or two in force on one field, raise; the result is a valid `Listing`, `price_source` by point 3.
2. **The restore's state:** a flagged active post restores to active; a reported post with `post_nature` corrected to
   `"for_sale"` restores to rejected `for_sale`; an other-city post by `native_location` stays rejected `other_city`; an
   archived post stays archived with the reason re-derived (`None` or one); the flag fields cleared and every other field
   kept; a record with no flag or report is refused. **One implementation:** for a table of cases,
   `restored_lifecycle`'s reason equals `classified_lifecycle`'s on the same seen `Listing`.
3. **The key, rule by rule:** rule 1; rule 2 with a phone; rule 2 with the fields; **nothing else ties** (a phone alone,
   the fields alone, a photo alone, an agent phone with the fields, a photo with only an agent phone); the 72-hour bound
   (72 h ties, 72 h and a second does not); the same text hash is not compared; only members (pending, rejected,
   archived, duplicates, no `Listing` are not tied); **corrected values** (#287): a correction that makes the fields match
   ties, one that breaks them unties; the shared-phone-or-photo search equals the every-pair search on seeded random
   populations.
4. **Cards:** a connected group is one card; the shown post (point 6); dedup A duplicates in `post_ids` and
   `publications`; `last_published_at` the latest; `publications` earliest first; every member in one card.
5. **The evaluation:** the option by kind; an option off; the sublet switch (#274); unclear and unwritten kind under
   both options, at the bottom, marked (#273); each critical category failing (hidden) and unknown (bottom); "women only"
   both ways; each preference met, failed, unknown; the fixed wanted values (#269); inclusive ends; half rooms and floor -1
   (#271); no size in the room option (#247); **"immediate" on the UTC date (R2):** at 22:30 UTC on 2026-10-11 (01:30 on
   10-12 in Israel) it compares as 2026-10-11; a corrected field read instead of the model's.
6. **The area's colour:** one area never orange; two areas all chosen, not orange; one of two chosen, orange; none chosen,
   orange (#275); no area with a street, unclear; no area and no location, not written.
7. **The order:** unviewed before viewed; the tiers; newest first inside a tier; a card viewed through another of its
   posts (#253).
8. **Invariants:** a full derivation (load, key, cards, evaluation, order) over a temporary SQLite store leaves the file
   byte-identical (invariants 12, 14); nothing in `policy/`, `postmodel/seen.py` or `dedup/stage_b.py` calls a write
   method (a Repository and a `UserDataStore` double that raise on any write); the socket guard covers invariant 15.
9. **The four known pairs (§4), the first check:** tests never read the production store (3.4, test 10), so the check is
   a read-only run at the build (`load_key_posts` over `SqliteRepository(read_only=True)`, the store's SHA-256 before and
   after), reported in `SESSION_LOG.md` (point 14). Today's result is above: the four tied, nothing else.

### What I could not verify (3.6)

- **The times at the store's full size:** only today's 266 posts were measured; the 40-day figures are a linear estimate,
  and the synthetic copies measure the pairing only. The photo hashing ran once, with the disk cache in an unknown state.
- **The agent-number count as the store grows:** the key counts a number over every member (#230), so at 40 days more
  numbers will reach 4 than over the 27 hours measured; `BACKLOG.md` already re-measures it on a week of data.
- **The shown post's stability:** a post that arrives later with an earlier `posted_at`, or a change of the key, changes
  which post a card shows; `ViewedPost` covers every post of the card, so "viewed" survives it (#253), but a report made on
  the old shown post stays on that post.
- **How often a correction meets a native location** (point 4): none exists today (0 corrections).

### Points for Ron (3.6)

1. **The modules:** `postmodel/seen.py` (the seen `Listing`), `postmodel/rejects.restored_lifecycle` (the restore's
   state), `dedup/stage_b.py` (the key, the cards, the photo memo, the loader), `policy/evaluate.py` and `policy/order.py`;
   `CLAUDE.md`'s `policy/` row becomes "`evaluate(seen, profile, now) -> Evaluation`", and the plain-modules paragraph
   names `postmodel/seen.py` and `dedup/stage_b.py`.
2. **The evaluation's result, `Evaluation` and `FieldState`** (names and values above). It is never stored, but it
   replaces an approved stub contract (`DecisionStub`, `SCHEMA.md` "Stub contracts"), so it is put to Ron.
3. **`price_source` in the seen copy** when `price` is corrected across `"not_written"`: `None` for a corrected
   `"not_written"`, `"text"` when the model's was `None`, else kept. Or: refuse such a correction in 3.8, or make the seen
   post a type other than `Listing`.
4. **A correction of `other_city` against Facebook's location (#214):** as built today the native locality decides, so
   the admin's correction counts only on a post with no usable `native_location`. Or: a correction in force outranks the
   native locality.
5. **A card is a connected group** (A tied to B and B to C: one card, even if A and C are not tied, or are more than 72
   hours apart). Or: pairs only, a post joining the earliest post it is tied to (the "chains" rule of `PHASE_2.md` 2.10's
   void plan).
6. **The post a card shows, and evaluates:** the earliest `posted_at` among the card's members, then the smaller
   `listing_id` (as #75 A, D2: the first stays). Its seen `Listing` gives the fields, the evaluation and the colours; the
   other members' answers are not read for it. Or: the latest member.
7. **The fields rule and the agent numbers imported from `gate_d/candidates.py`** (one implementation). Or: move them into
   `dedup/stage_b.py` and have `gate_d` import them.
8. **An unknown preference** (not written or unclear): proposed, it counts as **not met** (tier `"critical_met"`) and
   only an unknown **critical** category sends a post to the bottom, reading §8's "a filtered value" as a critical one.
   Or: any unknown category with a value set, preference included, sends it to the bottom.
9. **Parking not written** (the card shows "none", §6): proposed, unknown, as stored, so a critical parking sends it to
   the bottom rather than hiding it. Or: read as "no parking", so it fails.
10. **Inside a tier:** the newest last publication first. Or another order.
11. **A post of unclear kind admitted by both options:** proposed, the card shows the `room` option's colours when both
    admit it in the same tier, else the better tier's; both options' prices are compared. Or: shown once per option.
12. **A flag or a report on a card that groups several posts** (3.7, 3.8, raised here because the card is 3.6's): the
    flag or report is written on the shown post, which leaves the members (rejected posts are not members), so **the
    other posts the key tied to it come back as their own card**. Options: (a) as is; (b) the site writes a "lied" flag on
    every member of the card, and a report on the shown post only; (c) every member, for both. Recommended: (b).
13. **Speed at the store's size:** 3.6 uses the existing Repository reads and the in-process photo memo; a bulk read (one
    query for the members' posts, records and `Listing`s, a Repository contract change) is proposed only if 3.7's
    measurement on the real page needs it. *Settled by #301:* the grouping is computed once for all users, held in the
    site's memory and computed again only when the store changed; only each user's filtering and order per request.
    How the site knows the store changed is 3.7's plan.
14. **The four-pair check** stays a read-only run at the build, reported in the session log; no new command and no test
    on the production store.
15. **The stubs:** `policy/policy_stub.py` and `policy/base.py`'s `decide(ListingStub) -> DecisionStub` are replaced;
    `ListingStub` and `DecisionStub` stay for `notify/` until Phase 4; `tests/test_stubs.py` loses its policy tests.
16. **`restored_lifecycle` is built and tested in 3.6** (pure); 3.8 wires the writes and the reports.

## 3.7 The site — COMPLETE (#388, 2026-10-15). PLAN APPROVED 2026-10-12 (round 8, #316–#331; round 9, #332–#339); build steps 1 to 6 built; step 7 measured (round 16); C, 44–46 built (round 17); A, D and 56 built and step 7 measured again, both targets met (round 18); points 57–59 decided (#385–#387)

The lists and the cards (`BASELINE.md` §6) with these approved display rules (`BACKLOG.md`, "Recorded for a later
phase"): the card's main time is the last publication, shown relative (#122); the repost log shows the earliest
`posted_at` of the post and its duplicates (#75 A); rooms on a room post, "1 of N" (#120); size on a room post (#121);
the entry date's year never displayed (#115); on a card whose media came through a repost, the video link comes from
the repost (#70, #72.4). The profile editor with the two options, the profile's one sublet switch (#317), "copy from the
other option" (#245–#247, #272), and the area filter grouped (#248, #249). Viewed: opening a card, "mark as not viewed" (#253). Flag "lied"
and "wrong classification" (#173, #254).
**The polished UI is built here (#257)**, with Ron's design skills, when this task is reached; `BASELINE.md` §6–§8 stay
binding. The framework is decided (#258). **Needs from Ron:** the plan's approval; the design direction, at the task.

**Required of 3.7's plan by #301 (Ron, 2026-10-11):** the same-listing grouping (`dedup/stage_b.derive_cards`) is
computed **once for all users**, held in the site's memory, and computed again **only when the store changed** (a
collection run, a classification run, a flag, a report, a restore, a correction); only each user's evaluation, filtering
and order (`policy/`) run per request. The plan must say **how the site knows the store changed**, and must **measure a
real page load**. From 3.6 (#300): a "lied" flag on a card is written on every one of `Card.canonical_ids`; a "wrong
classification" report on `Card.shown_id` only.

**The plan below was written on 2026-10-11 (round 7) and approved by Ron on 2026-10-12 (round 8), with his answers
and his notes on the mock written into it (#316–#331); in round 9 Ron's notes on the round-8 mock (#332–#339); in round 10 his notes on the round-9 mock (#340–#343).** It follows Ron's direction (#303–#315), #302 (a post with no
written price is always at the bottom) and #320 (an orange location caps a post at the middle), both built. Build steps 1
(the store generation counter) and 2 (the read-only API for a guest) are built (rounds 9 and 10), and 3 (the list and
the opened post for a guest, round 11). **The mock is retired (#348):** `data/mock/` keeps round 10's, no longer
updated; from step 3 Ron reviews the site itself. **The site is laid out for each screen (#347):** a 27" monitor, a
laptop, an 11" iPad both ways and a phone.

**Until 3.9 the site runs on a dated copy of the production store (#331): anything Ron saves there (preferences, viewed
marks, flags, reports) stays in the copy** and never reaches the production store.

### (a) Scope

**In 3.7:** the API and the pages for everyone who is not the admin acting as admin: the list (home), the opened post,
the filter bar, sign-in, sign-up with a key, the forced password change, the preferences page; the user's writes
(viewed, "mark as not viewed", a "lied" flag, a "wrong classification" report, saving the preferences); the session
cookie; the same-listing grouping held in memory (#301); a command that serves the site on the laptop. **Not in 3.7:**
the admin's pages (3.8; the admin signs in through 3.7's page); serving through Tailscale and Docker (3.9); Telegram
(Phase 4); favourites, a map, a language switch (#310).

### (b) What I took from Ron's reference screenshots, and what I did differently

| Reference | Taken | Different, or left out |
|---|---|---|
| The phone list | One card under the other (#303); the photo at the start (the right, in Hebrew) beside a large price; the location line with a pin; the relative time; feature chips; a WhatsApp button beside a wide button | No heart (favourites, #310); no floating "map" button (#310); no language switch (#310); the wide button opens the post on our site, and the link to the original sits inside (c) |
| The opened post on a phone | Full screen, a back arrow at the top (#313); a photo carousel with dots; a price block; a rows table (rooms, floor, sqm, entry date), not written shown as "לא צוין" in grey (#321); a "features" block of chips, the known ones lit and the unstated ones grey; a sticky bottom bar with the main action | Our chips use the colours of #309 (green, plain, red, grey, orange), not just lit and grey; no chips for features we do not store (a safe room, a shelter, renovated, pets); the bottom bar holds "to the original post" and WhatsApp, no map |
| The desktop grid | A grid (#303); the photo on top; the first lines of text as the heading (here the poster's own text, #312); a grey location line; a row of four stats with icons | The source badge (we have one source); our fourth stat is the entry date, the time moves to the card's foot; the glow (#308) |
| The preferences pages | Sections as white cards on a warm background; a range as two number boxes and a slider, with a "don't care" button (it is our `None`); entry-date quick chips ("immediate", "from the 1st of next month", "another date"); feature tiles with an icon that light up when chosen; a summary with "edit" per section; a live count "with the current settings: N posts" | Not a step-by-step wizard: one page, two tabs (room, empty apartment) and "copy from the other option" (#272); every category carries its level, "preference" or "must" (§8), where the reference has one global "also show posts that do not mention a feature"; no property types we do not have (an apartment for roommates as a third kind); no email; it is not the filter (#314): the home page has its own bar |

What the references show and the approved rules do not have, listed for Ron (point 25), not added: a filter by street,
a map, favourites, pets, a safe room or shelter, "renovated", a third kind "apartment for roommates", an email, the
source badge, a "results include only the last week" line.

### (c) Every item, on the closed card and in the opened post (#303, Ron's request f) — APPROVED with #321–#328 (#330, point 9)

`BASELINE.md` §6, §7, §8 and the marks Ron listed, with Ron's notes on the mock (2026-10-12). "Desktop" is the grid card
and the dialog (#304); "phone" is the stacked card and the full-screen post (#313). **—** means not shown there.

**The rules over the whole table.** No glyphs anywhere, on the card or inside: colour plus words only, each item keeping
its accessible name (#323). Every attribute not written reads "לא צוין" in grey (#321), except price and entry date,
which take the important-missing badge. **On the closed card only the green chips** (#326), plus three items that are
not green: the red "women only" icon, the important-missing badge, the orange location line. The price, the location
line, the four stats, the kind and the foot are not chips and stay (#332). **The kind is "דירה שלמה" everywhere**
(#339). **The three buttons of the foot are outlined in their colour** (#338): "פייסבוק" blue, "וואטסאפ" green (another
green than the tier's glow), "דיווח" a soft light red. **The card is built of fixed slots** (#341): the photo, the kind
line, the price, three lines of text, two lines of location, the four stats, one row of chips, and a foot of two fixed
rows; each slot keeps its place and size when it is empty, so every card is the same height and nothing moves,
whatever it holds (WhatsApp or not, the report button or not, reposts or not, no photo, a short or long text, no price,
the "women only" icon, an orange location). **The foot** (#340): the time at the right with the three button slots at
the left, in fixed places; under the time, on its own line, "פורסם N פעמים" only when there was a repost, its line kept
when there was none. A guest's report slot stays, empty (#341). *Amended by #351 (round 12) for the button row
only: the buttons pack to the left with no reserved place; from the left report, WhatsApp, Facebook; an absent one
leaves no gap.* **Inside, every chip in its colour**
(green, orange, grey, plain, and red for a preference not met).

| # | Item | Closed card, desktop | Closed card, phone | Opened post, desktop (dialog) | Opened post, phone (full screen) |
|---|---|---|---|---|---|
| 1 | Photos (#327; lazy-loaded, #330) | **A carousel of every photo on the card itself** (4:3, cropped): arrows on hover, dots, "1/5" in a corner (#332, point 30); only the first photo is loaded with the page, the rest as they come into view | **A carousel at the start, swiped**, square, dots | A carousel of every photo, arrows and dots; click enlarges | A swiping carousel at the top, dots |
| 2 | Video or reel (photos only are downloaded) | A "וידאו" chip on the photo, in words. **A post with no photo but a video or reel** (round 9, Ron's instruction after the check of A4: three of 139 active posts, each a single reel) shows, in the photo's place, the link "צפייה בסרטון בפייסבוק", never "אין תמונות" | The same | "Watch the video on Facebook" link per video; from the repost when the media came through one (#70, #72.4) | The same |
| 3 | The poster's full original text | The first 3 lines, cut, as the card's heading (#312) | The first 2 lines | The whole text, unchanged, line breaks kept, `dir="auto"` | The same |
| 4 | **Link to the original post** | A small "פייסבוק" button in the card's foot, outlined in blue (#338); following it does not mark the card viewed (#330, point 10) | The same, in the foot | **A main button "to the original post" in the dialog's foot** | **In the sticky bottom bar**, beside WhatsApp |
| 5 | Price, "X/Y" when several (#95) | Large, at the top of the text column | Large, at the top beside the photo | The price block, large | The same |
| 6 | Price not written | The important-missing badge "אין מחיר" (a dark slate badge, words only, #330 point 6) | The same | The same, in the price block | The same |
| 7 | Entry date as written; its year never shown (#96, #115) | The fourth stat: the text as written, cut to one line | In the line under the price | A row, the text as written in full | The same |
| 8 | Entry date not written | The fourth stat: the badge "אין תאריך כניסה" | The same | The row, the same badge | The same |
| 9 | Location: areas and streets | One line: the areas' names · the streets as written; plain, green on `"match"`, **orange when the location is orange** (#250, #320) | The same, two lines at most | Rows: "area" (each name), "street" (as written), the names the post itself gave (as written) | The same |
| 10 | No area: unclear (a street given) or not written (#110) | The orange line "האזור לא ברור" with the street / "מיקום: לא צוין" in grey | The same | The same, in the rows | The same |
| 11 | Listing kind, sublet mark (#246) | The kind in words, "חדר בדירת שותפים" / "דירה שלמה" (the one name, #339), and "סאבלט", above the price (not a chip; §8: every card shows the option it answers) | The same | The same, under the price | The same |
| 12 | Kind unclear or not written, marked (#273), and the option it answers (§8) | The orange mark "סוג לא ברור · מוצג כ: חדר" in the kind's place (#332) | The same | The same | The same |
| 13 | Phone(s), `name-number` (§6) | — | — | Each number as a `tel:` link, with its name | The same |
| 14 | **WhatsApp** (#311), when the post has a mobile number (#330, point 22) | A small "וואטסאפ" button in the foot, outlined in green (#338) | A WhatsApp button, outlined in green | A button per mobile number | In the sticky bottom bar (the first mobile number; the others in the rows) |
| 15 | Publication time: the last publication, relative (#122) | In the foot's first row: "לפני 5 שעות" | The same, in the foot | In the price block | The same |
| 16 | Repost log, earliest first (#75 A) | "פורסם 3 פעמים" on its own line under the time, only when there was a repost (#340) | The same | A list: each publication, relative and Israel time, the earliest first | The same, collapsed |
| 17 | Broker (no broker is positive, #309) | A chip only when green ("ללא תיווך") | The same | Features block, in its colour ("לא צוין" grey) | The same |
| 18 | Rooms; on a room post "1/N" closed (#325), "1 of N" inside (#120) | First stat; a room post "1/2.5"; total not written: "1" with a grey "סה״כ לא צוין" under it (#332) | In the line under the price | A row, #120's wording | The same |
| 19 | Floor, "X/Y" when the floors are written (#98, #106); 0 ground, -1 basement | Third stat; "לא צוין" grey | — | A row | The same |
| 20 | Size; on a room post "X sqm for the room, of Y" (#99, #121) | Second stat; "לא צוין" grey | — | A row | The same |
| 21 | Balcony | A chip only when green | The same | Features block, in its colour; not written "לא צוין" grey (#321) | The same |
| 22 | Parking | A chip only when green | The same | Features block; not written "לא צוין" grey (#321, replacing §6's "none") | The same |
| 23 | Elevator, air conditioning | Chips only when green | The same | Features block | The same |
| 24 | Furnished yes / partial / no (#102) | — | — | Features block; "yes" plain (#330, point 8) | The same |
| 25 | Arnona, house committee (#101, #116) | — | — | Two rows: the amount, "included", orange "unclear", or "לא צוין" grey | The same |
| 26 | "Women only" shown because the bar does not hide it (§8) | **The red "נשים בלבד" icon chip** (kept, #326) | The same | The same, under the price | The same |
| 27 | "Women preferred" (#117) | — (a plain chip, #326, #332) | — | A plain chip under the price | The same |
| 28 | **The glow** (#308, #322) and the tier (#323) | The ring and soft shadow in the tier's colour; **no glow while the option holds no preference**; a small "i" **in the card's top-left corner, over the photo and inside the card, on a faded semi-transparent background** (#337) shows the tier's label on hover; no label text | The same, over the photo's top-left corner; the "i" on tap | The tier's label and the reason for the bottom tier, in words, at the top of the price block (#332) | The same |
| 29 | The field colours (#309) | Only the green chips (#326) | The same | On every row and chip | The same |
| 30 | "Corrected by hand" (#256) | The word "תוקן" beside a corrected item that is shown closed | The same | "תוקן ידנית" on each corrected row or chip | The same |
| 31 | Viewed (#62, #253); signed-in only | The card dimmed, the word tag "נצפה" | The same | "Mark as not viewed" in the foot | In the top bar's menu |
| 32 | Flag "lied" (#300); signed-in only | **A report button "דיווח" in the card's foot** (#328), outlined in a soft light red (#338): a small menu, "the post lies" (with a confirmation) | The same | In the foot's menu, with a confirmation | In the top bar's menu |
| 33 | "Wrong classification" report (#254); signed-in only | The same report button: "wrong classification" opens the post with the form | The same | The same menu: a form, the fields as Hebrew labels, a note of up to 500 characters | The same, full screen |
| 34 | The other city (#214) | — (an other-city post is rejected and never reaches a user; the admin's list shows it, 3.8) | — | — | — |

**The link to the original post** (Ron: it must exist, its place the reviewer's recommendation, approved, #330 point
10): a main button in the opened post and a small link on the closed card; following the link from the closed card does
not mark the card viewed (#253 marks on opening).

### (d) The glow (#308) and the field colours (#309) — DECIDED (#320, #322, #323, #330 points 4, 5)

**The glow** (#330, point 4): a thin ring and a soft shadow in the tier's colour, strongest for green; **green** for
`"preferences_met"`, **orange** for `"critical_met"`, **red** for the bottom (`"unknown"`). **No green glow while the
option that admits the post holds no preference at all** (#322): every category of that option is `None` or at the
level `"critical"`; such a card has no glow. Orange and red are unchanged. The glow never changes the order.

**The tier's label** is not text on the closed card (#323): a small "i" in the card's corner shows it on hover (desktop)
or tap (phone): "מתאים לכל ההעדפות", "מתאים חלקית", "חסר מידע: …" with the reason for the bottom ("no price", "kind
unclear", "area unclear", "entry date not written" for a critical one). The "i" is a button whose accessible name is the
label, so a screen reader reads it.

**An orange location** caps the tier at the middle (#320, built in `policy/evaluate.py`): such a card glows orange at
most, never green.

**Colour blindness** (#323, #330 point 5). **No glyphs anywhere**: no ✓, no warning sign, no ✕ or ? on the tier or the
chips; colour plus words only. Every chip carries its value in words ("מרפסת", "ללא תיווך", "חניה: לא צוין"), and every
chip and the card keep an accessible name that says the state ("balcony: yes, matches your preference"). The hues are
picked apart in lightness as well as hue (a blue-leaning green, an amber, a crimson) and checked in the build with a
colour-vision simulation (chrome-devtools' rendering emulation) and the accessibility review. **Ron accepts that a
colour-blind user needs the "i" to read the tier** (#323).

**How the field colours (#309) sit with 3.6's `FieldState`.** `Evaluation.fields` holds a `FieldState` for the ten
profile categories only, for the option that admitted the post. The colour of a field is:

| `FieldState` | Colour |
|---|---|
| `"match"` | green |
| `"mismatch"` | red (only a preference can show it: a failed critical category hides the post) |
| `"not_written"` | grey, the words "לא צוין" (#321) |
| `"unclear"` | orange |
| `"not_applied"` (no value in the option), and every field that is not a category (elevator, air conditioning, furnished, arnona, house committee, building floors, room size) | from the post's own value: a **known positive** green (broker `False`, balcony, parking, elevator, air conditioning `True`); a known negative plain; not written grey "לא צוין"; unclear orange; a field with no positive or negative (rooms, floor, size, price, entry date, arnona, house committee, furnished, "yes" included, #330 point 8) plain |
| the area | orange when `area_orange` or no area and a street given; grey "לא צוין" with no location; green on `"match"`; else plain |
| price and entry date not written | the important-missing badge (a dark slate badge with the words, #330 point 6), not grey |

**`policy/colours.py`** (#330, point 18), a small pure function, `field_colours(seen, evaluation) -> Mapping[str,
Colour]`, computes the table above on the server, so the browser holds no rule, and says whether the card glows (#322,
from the admitting option's values). It imports the wanted values from `policy/evaluate.WANTED` (one implementation,
#269) and adds the two the card alone uses (elevator, air conditioning `True`, #309). **Built in round 11:**
`field_colours(listing, evaluation)` (with no evaluation, a post's own colours, for an opened post the list does not
hold), `glow(evaluation, profile)` and `tier_reasons(listing, evaluation, profile)`, the reasons the "i" and the opened
post put into words (`web/cards.py`); the glow needs the profile, to read the admitting option's levels (#322).

### (e) The header, the filter bar on the home page, and the preferences page (#305, #314, #315) — DECIDED (#317, #324, #329, #330, #333–#336, #339); the bar redesigned in round 9

**Right to left, nothing on the left (#324), but the logo (#333).** The site is Hebrew only. The header and the bar
start at the right edge, as Hebrew reads; **the one deliberate exception is the logo, on the left** (#333). On a wide
screen nothing else sits on the left side of the header or the bar.

**(i) The header** (#333, #334). At the right, **the user area**: a guest sees "התחבר" (sign in) and beside it "הירשם"
(sign up); a signed-in user sees their username, and clicking it opens a menu with "ההעדפות שלי" (the preferences page)
and under it "התנתק" (sign out). At the left, **the logo** "TLV Apartment Hunter": a designed mark and wordmark, light
and cool (pale sky and teal), not the name set in the page's font. Nothing between them. **The header has its own
background** (#342), a cool tint, distinct from the white filter bar under it. **The user button** (#343): one pill
with a round avatar (the username's first letter on a sky-to-teal gradient), the username and a chevron; on a phone the
avatar and the chevron only. A guest's "התחבר" and "הירשם" are pills of the same height.

**(ii) The filter bar, redesigned (round 9, the reviewer's proposal for #335).** Ron found round 8's bar unclear. Its
two hard parts were the "option being edited" (one row of controls that silently edited whichever kind chip was last
clicked) and two buttons about saving. The new bar removes both. Under the header, sticky as the list scrolls:

- **Row 1, what is shown:** three labelled switches, "חדר בדירת שותפים", "דירה שלמה" (#339) and "גם סאבלט" (the
  profile's one switch, #317, #329). A switch reads on or off by its track and position, with its label always in
  words. **When both kinds are off the sublet switch is disabled, with the line "בחרו חדר או דירה שלמה כדי לראות
  סאבלטים".**
- **One values row per kind that is on, labelled with the kind's name.** "חדר בדירת שותפים:" then its controls; "דירה
  שלמה:" then its own. Each kind's values are visibly its own (#245), and no control edits a hidden target. Each row:
  "אזורים" (the grouped popover of §6, #248, #249, #261), "מחיר" (min and max, #95), "חדרים" (halves, #271), and "עוד"
  (floor, sqm in the "דירה שלמה" row only (#247), no broker, parking, balcony, entry date with "immediate" as a quick
  chip (#270), "hide women only"; each category with its level, "העדפה" or "חובה", #330 point 15). A control holding a
  value is a filled chip with the value in words ("מחיר עד ₪5,500"; a "must" adds the word "חובה", no glyph, #323); its
  "נקה" clears it to "don't care". A kind that is off has no row.
- **The status line, at the end of row 1 (still from the right): the count and where the bar stands, in words.** As
  saved: "102 מודעות · לפי ההעדפות השמורות". Changed: "87 מודעות · סינון זמני, שונה מההעדפות שלך" and **the button
  "ההעדפות שלי", which resets the bar to the saved preferences** (#335). A guest's line says only the count. **There is
  no "save as my preferences"** (#335, amending #315): preferences change only on the preferences page.
- **On a phone:** row 1 with the three switches (they wrap to two lines when needed), then the status line with "סינון
  (3)" (the number of controls holding a value) and, when changed, "ההעדפות שלי". "סינון" opens a full-screen sheet
  with the kind rows, labelled as on a desktop, and "הצגת 87 מודעות" at its foot. *Amended by #353 (round 13): the three
  switches stay on one row (a long label wraps inside its own switch), and the status line and "סינון (N)" make one dense
  row under them, about 90–100 px in all (built: 91 px at 390 × 844); a changed bar's words read "סינון זמני" on a phone,
  the reset button beside them saying the rest.*
- **How the bar's state is evaluated** (unchanged): it holds the profile's shape, the two `SearchOption`s and
  `include_sublets`; each list request sends it; the server builds a **transient `Profile`**, validated by `Profile`'s
  own rules and never stored, and passes it to `policy.evaluate`. "Changed" is the bar's state compared, field by field,
  with the saved profile, in the browser (a guest has no saved profile, so no "changed").
- **Its lifetime:** the tab's memory and `sessionStorage` (#330, point 14): a reload keeps a changed bar; a new visit
  starts again from the saved profile (signed in) or empty (a guest).

**(iii) The preferences page.** One page, reached from the user menu's "ההעדפות שלי" (#334). **At the top, the
profile's one sublet switch** (#317), with the line "sublets are shown in the options you switched on". Then two tabs,
"חדר בדירת שותפים" and "דירה שלמה" (#339), each with its on/off switch and "copy from the other option" (#272: every
value but on/off; never the sqm range into the room option; the sublet switch is the profile's and is not copied).
Sections as cards: areas (the grouped list in full); price; rooms; floor; sqm ("דירה שלמה" only); entry date (from and
until, quick chips); features (no broker, parking, balcony as tiles, #269); "women only". Each range is two number boxes
with a slider and a "don't care" button; **each category has its level** as a two-way switch "preference / must", with
one line saying what a "must" hides. A summary at the top and the live count "with these preferences: N posts" (#330,
point 24). A sticky "save" bar at the right; leaving with unsaved changes asks first. **The only place preferences are
saved** (#335). From Phase 4 the page also says these preferences drive the alerts.

**Which settings where.** Every value of the profile is in both, since the bar must hold a whole `Profile` for
`evaluate`. **Only on the preferences page:** saving, "copy from the other option", the summary, the explanation of the
levels, and (Phase 4) the Telegram link. **In the bar:** the kinds and the sublet switch, then per kind areas, price,
rooms and "עוד".

**Sign-up** (#336, amending #330 point 13): the key, a username, the password twice; **no "use my current filter"
box**. A new user starts with #268's defaults and sets preferences on the preferences page.

### (f) The screens

| Screen | Who | Contents |
|---|---|---|
| The list (home) | Everyone | A header (#333, #334): at the right the user area ("התחבר" and "הירשם" for a guest; the username and its menu, "ההעדפות שלי" and "התנתק", signed in); at the left the logo; the filter bar of (e); the count; the grid (desktop) or the stacked list (phone); an empty state ("no post fits; clear a filter"); unviewed before viewed (#62) |
| The opened post | Everyone; writes signed-in only | The dialog over the list on a desktop (#304), full screen with a back arrow on a phone (#313); its own address (`/post/<id>`), so the browser's back closes it; (c)'s items |
| Sign-in | A guest | Username, password; the refusals of 3.5 (wrong, the delay with the seconds to wait, disabled) |
| Sign-up with a key | A guest | The key, a username (the rules of #262 shown), the password twice (no "use my current filter", #336); signed in on success |
| The forced password change | A user with `must_change_password` | The only screen reachable (Gate C, `Session`); the same form serves "change password" from the menu |
| The preferences page | A user | (e)(ii) |

The admin's pages are 3.8's.

### (g) The API

One origin: FastAPI serves `/api/*` and the built pages. Every response is JSON, except the photos and the pages.
**Guest** = no valid session; **user** = a valid session; **admin** = the admin's session. Every `/api` write takes JSON
only and checks the `Origin` header (point 19).

| Endpoint | Who | Returns |
|---|---|---|
| `GET /api/session` | Everyone | `{user: null}` or `{username, is_admin, must_change_password}` |
| `POST /api/sign-in` `{username, password}` | Guest | Sets the cookie; or a refusal: `wrong`, `delayed` (with the seconds), `disabled` (3.5) |
| `POST /api/sign-out` | User | Ends the session (`accounts.sign_out`), clears the cookie |
| `POST /api/sign-up` `{key, username, password}` | Guest | Creates the user (`accounts.sign_up`) with #268's default profile (#336), signs in; or a refusal (the key not usable, the username taken or invalid, the password too short) |
| `POST /api/password` `{current, new}` | User (also with `must_change_password`) | `accounts.change_password`: the other sessions end (R3) |
| `GET /api/reference` | Everyone | The 71 areas with their display names, the region groups (§6), the reportable fields (#277) |
| `GET /api/profile` | User | The saved profile's two options and its sublet switch (#317) |
| `PUT /api/profile` `{room, whole_apartment, include_sublets}` | User | `save_profile` (whole record, #289 point 4); the saved profile |
| `POST /api/cards` `{room, whole_apartment, include_sublets}` | Everyone | The ordered cards for that filter (`policy.order.ordered`): for each, the shown post's summary (the closed card's items of (c)), its tier, whether it glows (#322), option, kind mark, field colours, area orange, women-only icon, corrected fields, every photo's address (the closed card's carousel, #327; loaded lazily by the page), the last publication and the number of publications, and `viewed` for a user; and the count |
| `GET /api/posts/{listing_id}` | Everyone | The opened post of the card holding that post (any of `Card.post_ids` finds its card): every item of (c), every photo's address, the publications, phones, WhatsApp links; 404 for anything else |
| `GET /api/photos/{listing_id}/{file}` | Everyone | The photo file from `<store_root>/images/`, only when it is a `PostImage.local_path` of a post of a current card; 404 otherwise (no path is built from the request) |
| `POST /api/viewed/{listing_id}` | User | `mark_viewed(user, Card.shown_id, now)` (#276) |
| `DELETE /api/viewed/{listing_id}` | User | `unmark_viewed(user, Card.post_ids)` |
| `POST /api/flag/{listing_id}` `{note?}` | User | The "lied" flag on every one of `Card.canonical_ids` (#300), (i) below |
| `POST /api/report/{listing_id}` `{fields, note?}` | User | The report on `Card.shown_id` (#300), (i) below |
| Every other path | Everyone | The built page (`index.html`), so `/post/<id>` and `/preferences` load the site |

**No rejected, pending or archived post is ever returned to a non-admin:** the cards come only from
`dedup/stage_b.derive_cards` (its members are active canonicals with a `Listing`) and only those `evaluate` shows;
`/api/posts` and `/api/photos` answer only for a post of a current card. A test pins each state (j). The admin's
endpoints are 3.8's.

**The session cookie** (read 2026-10-11: starlette.dev "Responses", `Response.set_cookie(key, value, max_age=None,
expires=None, path="/", domain=None, secure=False, httponly=False, samesite="lax", partitioned=False)`, where FastAPI's
"Response Cookies" page sends; MDN "Set-Cookie", modified 2026-09-01). **Proposed:** name `tlv_session`; the value the
session token of 3.5; `httponly=True` (no script reads it); `secure=True` (MDN: sent only over `https:`, "except on
localhost", so the laptop's `http://localhost` works and Tailscale Serve's HTTPS does); `samesite="strict"` (MDN: sent
only for requests from the same site); `path="/"`; `max_age=2592000` (30 days, as the session's `expires_at`, R5; MDN:
`Max-Age` has precedence over `Expires`); no `domain` (the host only); `partitioned` not passed (Python 3.14+ only). Every
request checks the token with `accounts.session_user` (valid, not ended, not expired, the user not disabled); a cookie
that fails it is cleared. Starlette's defaults (`secure=False`, `samesite="lax"`) are never relied on: each attribute is
passed, and a test reads the `Set-Cookie` header.

### (h) The grouping held in memory (#301), how the site knows the store changed, and the measured page load

**Held:** one `Grouping` object in the site's process: the cards (`derive_cards`), each card's shown `KeyPost` (its seen
`Listing`, for `evaluate`), and the store generation it was computed at; the photo memo (`PhotoHashes`) lives beside it
across recomputes, so only changed files are hashed again. Per request, only the per-user part runs: `evaluate` of each
card's shown post against the bar's transient profile, the user's `viewed_listing_ids`, `ordered`, the field colours.
One recompute at a time (a lock); requests during it wait for it, so a user who just flagged never sees the old card.

**How the site knows the store changed** (the job commands are separate processes, so nothing in the site's memory
hears them). **Decided: option 1 (#316)**; the migration command is built at build step 1. The two ways weighed, point
11:

| | How | For | Against |
|---|---|---|---|
| **1 (recommended)** | **A store generation counter kept by SQLite itself:** a one-row table and `AFTER INSERT`, `AFTER UPDATE` and `AFTER DELETE` triggers on `raw_posts`, `post_lifecycle`, `listings` (store) and `corrections` (userdata) that add 1. Each request reads the one row (one small query); a different number means recompute. Triggers are part of the database schema (sqlite.org "CREATE TRIGGER": only `TEMP` triggers are limited to the connection that made them), so every writer, in every process, present or future, moves it, and no job command changes | Exact: recomputes on a post change only, never on a viewed mark, a sign-in or a profile save. **Checked in memory (scratchpad, SQLite 3.45.3, 2026-10-11): the store's `INSERT … ON CONFLICT DO UPDATE` fires the `INSERT` trigger for a new row and the `UPDATE` trigger on a conflict, also when the value is unchanged**; sqlite.org's UPSERT page does not say | **A layout change** of `store` and `userdata` (a table and triggers: layout versions 2), so a one-time migration of the production file, with a dated backup, by a new command (a seventh store writer) |
| 2 | `PRAGMA data_version` on one connection the site keeps open (sqlite.org: two calls on the same connection differ "if changes were committed to the database by any other connection in the interim", other processes included) | No layout change | It moves on **every** commit by another connection, the site's own viewed marks, sign-ins and profile saves included, so the grouping is recomputed far more often than the store's posts change; at 40 days a recompute costs seconds (3.6's estimate) |

**First numbers, build step 2 (2026-10-13, round 10):** `serve --copy` on Ron's laptop, today's store (139 compared
posts, 123 cards for a new guest's empty bar, 400 KB of JSON). **Cold**, the first request after start: `gen` 1.1 ms,
**`group` 1324.4 ms** (reading the store and hashing every photo), `eval` 1.2, `order` 0.2, `json` 7.4; 1.69 s at the
client. **Warm** (5 requests): `gen` 0.7–1.3 ms, `eval` 1.1–2.1, `order` 0.2–0.5, `json` 6.9–13.9; **14–39 ms at the
client**. `/api/reference` 3 ms, `/api/posts/{id}` 5 ms, a 47 KB photo 67 ms. The warm target (300 ms on the server) is
met by far; the cold first request (one per store change or start) is above the 1.5 s first-cards target and is measured
again in the browser at step 7 (point 31).

**Measuring a real page load** (#301). At build step 7 (l), on a dated copy of the production store (the site writes
`userdata`, and even opening `SqliteUserDataStore` starts a write transaction, so the real file is not served before
3.9, #331), **and on a synthetic store of 40 days' size** (#330, point 20), built as in 3.6's measurement:
1. **On the server:** `POST /api/cards` returns a `Server-Timing` header (MDN, modified 2026-07-28: `name;dur=…`,
   shown in the browser's network timings) with `gen` (the generation read), `group` (a recompute, when one ran), `eval`,
   `order` and `json`; logged too.
2. **In the browser:** chrome-devtools' performance trace and Lighthouse, on a desktop window and a phone viewport: the
   time to the first cards and the total, cold (the first request after the site starts: the whole grouping and the
   photo hashes), warm, and after a store change (a `classify_pending --limit 1` is not needed: a test write on the copy).
3. Reported in `SESSION_LOG.md` with each store's size. **The targets (#330, point 20):** a warm `POST /api/cards` under
   300 ms on the server; the first cards drawn under 1.5 s on Ron's laptop; on today's store and on the 40-day one. A
   bulk read (3.6 point 13) is proposed only if the measurement misses them.

### (i) The writes a user makes (#260, #300), and what the user sees on a conflict

| Write | How | On a conflict or a failure |
|---|---|---|
| Viewed (#253, #276) | `mark_viewed(user_id, Card.shown_id, now)` when the opened post loads; insert only if absent (`userdata`, no lifecycle) | None possible beyond a database error: the card simply stays unviewed |
| Not viewed | `unmark_viewed(user_id, Card.post_ids)` | The same |
| **"Lied" flag on every member** (#300) | For each of `Card.canonical_ids`: read the lifecycle; when `"active"`, write `state` `"rejected"`, `rejection_reason` `"flagged"`, `flagged_by` the user, `flagged_at` now, the note, by **`save_lifecycle(record, expected=the record read)`**; a member that is no longer active is skipped. The record is built by a new pure function in `postmodel/rejects.py`, `flagged_lifecycle(existing, user_id, now, note)` (one place for Gate E's flag rule) | `StaleRecordError`: re-read once and try again if the post is still active; else that member is reported. The user sees "flagged" when every member was written, "flagged 1 of 2: the post changed meanwhile, try again" otherwise, and the list reloads (the card is gone) |
| **Report on the shown post** (#300, #278) | `add_report` first (a second open report by the same user is refused: "you already reported this post"), then the lifecycle by compare and set through `reported_lifecycle(existing, user_id, now)` in `postmodel/rejects.py`: `"rejected"`, `"misclassified"` unless already `"flagged"`; `flagged_by`/`flagged_at` set only by the first reporter (#280) | Two seams, two transactions (#289 point 3): when the lifecycle write fails after one retry, the report stays stored and the user sees "report saved; the post will be removed by the admin", and the admin's list shows it (3.8) |
| Save the preferences | `save_profile` (whole record, #289 point 4) | A database error: "not saved, try again"; the bar keeps its values |

**A stale page:** a write names a post that is no longer in a current card (someone flagged it, a run rejected it): 409,
"this post was removed meanwhile", and the list reloads. Every write leaves `RawPost` and `Listing` untouched
(invariant 14) and writes no per-user value on a post (invariant 12): only the lifecycle's flag fields, as Gate E
allows.

### (j) Invariant 15 on the page

- **No request to any other host.** Fonts bundled by `@fontsource` into the build and served by the site; no CDN; no
  analytics; no external image: photos come from `/api/photos` (the local store); the Facebook link, the video links
  and WhatsApp are links the user clicks, never fetched by the page.
- **Headers on every response:** `Content-Security-Policy: default-src 'self'; img-src 'self' data:; font-src 'self';
  connect-src 'self'; frame-ancestors 'none'` (so a request to another host fails in the browser even if one slipped in),
  and `Referrer-Policy: no-referrer` (the tailnet address is not sent to Facebook or WhatsApp when a link is followed;
  links also carry `rel="noopener noreferrer"`).
- **FastAPI's telemetry stays off.** FastAPI 0.143.0 depends on `opentelemetry-api` and, since that release (2026-10-08,
  its release notes), sets up an exporter only on opt-in (`FASTAPI_OTEL_AUTO_CONFIGURE` or `telemetry=`); the plain
  package installs no SDK. The site never opts in; a test checks it and the socket guard covers the rest.
- **Checked:** a pytest that every response carries the two headers; a check that the built files name no other host
  except the link targets (`facebook.com`, `wa.me`); and in chrome-devtools at each build step, the network panel shows no
  request leaving the site.

### (k) Dependencies (read 2026-10-11 under the `external-contract-verification` skill; nothing installed)

| Package | Version, licence | What was read | Use |
|---|---|---|---|
| `fastapi` | 0.143.0 (2026-10-08), MIT, Python ≥ 3.10 | pypi.org JSON: requires `starlette>=0.46.0`, `pydantic>=2.9.0`, `typing-extensions`, `typing-inspection`, `annotated-doc`, `opentelemetry-api>=1.44.0`; extras not used. Docs: "Response Cookies" (set on a `Response` parameter or a returned response; parameters in Starlette's docs); "Static Files" (`app.mount(path, StaticFiles(directory=…), name=…)`); "Testing" (`TestClient`, "first install httpx") | The API and the static pages; no extras |
| `starlette` | 1.7.0, BSD-3-Clause (pulled by FastAPI) | pypi.org JSON; starlette.dev "Responses" (`set_cookie`, `delete_cookie`, `FileResponse`), "Test Client" (default `base_url` `"http://testserver"`) | Cookies, `FileResponse`, `StaticFiles`, `TestClient` |
| `uvicorn` | 0.54.0, BSD-3-Clause, Python ≥ 3.10 | pypi.org JSON: `click`, `h11`; the `standard` extra (uvloop, watchfiles, websockets, httptools) not used | The server, bound to `127.0.0.1` |
| `httpx` (dev) | 0.28.1 (2024-12-06), BSD-3-Clause | pypi.org JSON | For `TestClient`, as FastAPI's page says; **but** starlette.dev's "Test Client" now speaks of `httpx2` and starlette 1.7.0's `full` extra lists both `httpx2>=2.0.0` and `httpx<0.29`: which one 1.7.0's `TestClient` imports is **unknown** until installed (point 17) |
| `react`, `react-dom` | 19.3.0, MIT (`react-dom` needs `scheduler ^0.28.0`) | registry.npmjs.org | The pages; the same as event-seeker |
| `vite` | 8.3.4, MIT; Node `^20.19.0 \|\| >=22.12.0` (Ron's 24.11.1 fits) | registry.npmjs.org | Build and dev server |
| `@vitejs/plugin-react` | 6.1.2, MIT; peer `vite ^8.0.0` | registry.npmjs.org | JSX |
| `typescript` | 7.0.2, Apache-2.0 (native compiler, per-platform packages) | registry.npmjs.org | Type checking (`tsc --noEmit`, as event-seeker) |
| `@fontsource/ibm-plex-sans-hebrew` | 5.3.0, OFL-1.1 | registry.npmjs.org (woff/woff2 files; the subsets were not listed) | The font event-seeker uses (point 16) |
| `vitest` (dev) | 5.0.3, MIT; Node `^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0`; peer `vite` | registry.npmjs.org | Tests of the pure TypeScript (formatting), no DOM: `jsdom` and Testing Library not added |
| `@types/react`, `@types/react-dom` (dev) | not read | — | Read at the install, with event-seeker's ranges (`^19.3.0`) |

**Event-seeker's own `frontend/package.json`** (read on the laptop, 2026-10-11) holds this exact set (React 19.3, Vite
8.3.4, plugin-react 6.1.2, TypeScript 7.0.2, Vitest 5.0.3, an IBM Plex Sans Hebrew font, no router), so the method of
#257 carries over. No router library: a small history-based route for `/`, `/post/<id>`, `/preferences`, `/sign-in`,
`/sign-up`, `/password`.

**Installed 2026-10-13 (build step 2), read again under the skill (`ASSUMPTIONS.md` I15–I18):** `fastapi` 0.143.0,
`starlette` 1.7.0, `uvicorn` 0.54.0, and `httpx2` 2.13.1 (dev) — the client the installed `TestClient` imports
(`starlette/testclient.py`: `httpx2`, with `httpx` only as a deprecated fallback; FastAPI's testing page still says
`httpx`, Starlette's says `httpx2`). Starlette 1.8.0 was published the same morning and was not taken. **On Windows
`TestClient` opens a loopback socket pair** (the event loop's self-pipe, I17): the web tests make that one pair without the
guarded `connect`; the guard stays on for everything else.

**Installed 2026-10-13 (build step 3), read again under the skill (`ASSUMPTIONS.md` I19–I22):** `react`, `react-dom`
19.3.0, `vite` 8.3.4, `@vitejs/plugin-react` 6.1.2, `typescript` 7.0.2, `vitest` **5.0.3** (5.0.4 was one day old and
not taken), `@types/react`, `@types/react-dom` 19.3.0, `@fontsource/ibm-plex-sans-hebrew` 5.3.0 (its Hebrew files
checked), exact versions in `frontend/package.json` with `package-lock.json`; no `@types/node`. **WhatsApp's link read
in Chrome:** `https://wa.me/<number>`, the international number with no `+` (I21).

**Pinned exactly (#330, point 17):** every package above at the exact version read at the install (`==` in
`pyproject.toml`, exact versions in `package.json` with the lock file), read again under the
`external-contract-verification` skill if the install is later than 2026-10-11. **At the install, before any test is
written on it:** which client Starlette's `TestClient` imports (`httpx` or `httpx2`), and that it opens no socket. **Before
building the WhatsApp link (step 6):** its format read in a browser.

**Could not verify:** which client 1.7.0's `TestClient` uses (above); that it makes no socket connection (the docs imply
it calls the app in process; the suite's socket guard will say); the font's Hebrew subset files; WhatsApp's link format
(`https://wa.me/<number>`, international, no `+`): its help page did not render to the fetcher, to read in a browser at
step 6; the transitive npm packages' licences; whether TypeScript 7's native packages install on Linux in 3.9's image.

### (l) The module layout, the tests, and the build in steps

**Python (wiring, like `pipeline.py`; the logic stays in `policy/`, `postmodel/`, `dedup/`, `accounts/`):**
- `tlv_hunter/web/` (not `site`, which is a Python standard module): `app.py` (`create_app(store_path, store_root)`: the
  routes, the static pages, the headers), `auth.py` (the cookie and `accounts.session_user`), `grouping.py` (the held
  grouping and the generation check, (h)), `cards.py` (the card and opened-post payloads, pure), `filters.py` (the bar's
  JSON to a transient `Profile`), `routes.py`.
- `policy/colours.py` (`field_colours`, (d)); `postmodel/rejects.py` gains `flagged_lifecycle` and `reported_lifecycle`
  (i); **the area groups** in `reference/area_groups.yaml`, read only through `areas/reference.py` (the one reader of
  `reference/`), so the grouping of §6 is data beside the 71 (point 23).
- `jobs/serve.py`: runs uvicorn on `127.0.0.1` with the store's path (until 3.9 a dated copy, #331); free; the site
  becomes a store writer beside the jobs (#260). `jobs/add_store_generation.py` (#316): the one-time migration (dated
  backup, `RawPost` check, as `create_admin`), the seventh store writer.
- `CLAUDE.md`: a row or paragraph for `web/` and the new commands.

**Front end:** `frontend/` at the repository's root (event-seeker's layout): `src/main.tsx`, `src/api.ts`,
`src/types.ts`, `src/route.ts`, `src/screens/` (List, Post, SignIn, SignUp, Password, Preferences),
`src/components/` (Card, FilterBar, AreaPicker, RangeField, Chip, Glow, Carousel), `src/format.ts` (relative time,
"X/Y", "1 of N", sizes), `src/styles/`. `frontend/dist/` and `node_modules/` gitignored; FastAPI serves `dist/`.

**Tests (the suite stays offline: the socket guard; `TestClient` in process; temporary stores only):**
1. The cookie: the exact `Set-Cookie` attributes; a bad, ended or expired token is a guest and the cookie is cleared.
2. Guests: list, open, photos, reference work; every write is 401; no viewed field in a guest's cards.
3. **No rejected, pending, archived or duplicate post reaches a non-admin:** a temporary store with one post in each
   state: absent from `/api/cards`, 404 from `/api/posts` and `/api/photos`; a duplicate's id opens its canonical's card.
4. The photo route: only a stored `local_path` of a current card; `..` and other posts' files refused.
5. The grouping: computed once for many requests (a counter on `derive_cards`); recomputed after a write through each
   store method (#316: the counter moves for `raw_posts`, `post_lifecycle`, `listings`, `corrections`, and not for
   viewed, sessions, profiles, users); the migration command (backup, `RawPost` rows identical, refuses a second run).
6. The bar: a transient profile never saved (a `UserDataStore` double: `save_profile` is called only by `PUT
   /api/profile`, the preferences page; #335, #336); an invalid bar (`min` > `max`, sqm in the room option) is 422.
7. The writes: a flag on a two-post card writes both members with `expected`; a conflict on one gives the partial
   answer; a report writes the shown post only, refuses a second open one; `RawPost` and `Listing` rows byte-identical
   after every write (invariant 14); nothing per user in the post tables (invariant 12).
8. The headers (CSP, `Referrer-Policy`) on every response; FastAPI's telemetry not configured.
9. `policy/colours.py`: each row of (d)'s table; the glow, none while the option holds no preference (#322);
   `flagged_lifecycle`, `reported_lifecycle`: Gate E's rules (#279, #280).
10. Front end (Vitest, no DOM): the formatters (#120 and the closed card's "1/N", #325; #121, #122, #115, #95), "לא צוין"
    for every attribute not written (#321), and which chips the closed card keeps (#326).

**The build, in steps, each ending in something Ron can look at or run:**
1. **Built in round 9 (2026-10-12):** the generation table and triggers (#316, `store_generation.py`), layout
   versions `store`, `store.listings`, `userdata` 2, `SqliteRepository.store_generation()`, the migration command
   `jobs/add_store_generation.py`, their tests. **Ron runs the migration** on the production store (a dated backup is
   made); until then every command refuses the store and names the command. **Ron ran it on 2026-10-13:** layout
   `store`, `store.listings`, `userdata` 1 → 2, backup `tlv_hunter.2026-10-13.backup.sqlite3`, `RawPost`s identical, counter
   0.
2. The read-only API: `web/`, the held grouping, `/api/cards`, `/api/posts`, `/api/photos`, `/api/reference`,
   `jobs/serve.py`, on a dated copy of the store (#331). The dependencies installed, pinned exactly; `TestClient`'s
   client checked before its first test (#330, point 17). **Ron runs** `serve` and opens the JSON; the first `Server-Timing`
   numbers. **Built 2026-10-13 (round 10):** `web/` (`app.py`, `grouping.py`, `filters.py`, `cards.py`, `routes.py`),
   `jobs/serve.py` (`--copy` makes a dated copy in `<store_root>/site/` by SQLite's online backup from a read-only
   connection; without it the newest copy; never the store itself), `reference/area_groups.yaml` with
   `areas.reference.load_area_groups`; `GET /api/reference`, `POST /api/cards` (and `GET /api/cards`, a new guest's empty
   bar, so the list opens in a browser), `GET /api/posts/{id}`, `GET /api/photos/{id}/{file}`; `Server-Timing`; the two
   headers; FastAPI's pages and telemetry off. Tests: `tests/test_web.py` (groups 2–6, 8, `serve`). **Not yet in the
   payload:** the field colours and the glow (`policy/colours.py`, step 3, with the page that uses them) and WhatsApp
   (step 6, its link format read first).
3. The list and the opened post for a guest, **desktop grid and phone list together** (#303), the dialog (#304) and the
   full-screen post (#313), the glow, the "i" and the colours (#322, #323), the closed card's carousel with lazy-loaded
   photos (#327, #330), only green chips closed (#326), built with `frontend-design` and checked in chrome-devtools at
   1440 px and as a real 390 × 844 page in the same step (screenshots, console, network). **Ron looks at it** with real
   posts. **Built 2026-10-13 (round 11):** `frontend/` (React 19.3, Vite 8.3.4, TypeScript 7.0.2, hand-written CSS, IBM
   Plex Sans Hebrew; `src/format.ts` the formatters, `src/components/` `Card`, `Carousel`, `InfoButton`, `PostView`,
   `Header`; no router library, `/` and `/post/<id>`); `policy/colours.py`; the card payload gains `glow`, `tier_label`,
   `colours` and `whatsapp`, the opened post `own_colours` and a WhatsApp link per mobile (`textnorm.phones.
   whatsapp_number`, so WhatsApp moved here from step 6); `web/app.py` serves the build beside the API (`/assets`, the
   build's own files, `index.html` for every other path not under `/api`); `serve` serves `frontend/dist` when it is
   built. **The layout (#347):** one centred column up to 2240 px that the header shares, cards of 296 px or more: 2
   columns on an iPad upright, 3 sideways, 4 on a laptop, 6 on a 27" screen; under 700 px the phone's stacked list.
   Checked at 2560×1440, 1440×900, 1366×768, 834×1194, 1194×834 and 390×844 (`data/ui_checks/`). Tests: `tests/
   test_colours.py`, `tests/test_web.py` (payload and pages), `frontend/src/format.test.ts`.
4. The header (the logo, the user area, #333, #334) and the redesigned filter bar of (e), desktop and phone sheet: the
   switches, one values row per kind, the status line and the "ההעדפות שלי" reset (#335). **Ron filters** for real.
5. Sign-in, sign-up with a key (no filter box, #336), the forced password change, the cookie; the preferences page, the
   only place preferences are saved (#335). **Ron signs in**, saves his preferences.
   **Steps 4 and 5 built together, 2026-10-14 (round 12):** `web/auth.py` (the cookie exactly as (g): `tlv_session`,
   `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`, `Max-Age` 2,592,000, no `Domain`; every request through
   `accounts.session_user`; a cookie that fails is cleared on any response; writes JSON only, 415 otherwise, and
   `Origin`'s host equal to `Host`, 403 otherwise; I23, I24); `routes.py`: `GET /api/session`, `POST /api/sign-in`
   (`wrong` 401, `delayed` 429 with `Retry-After` and the seconds, `disabled` 403), `POST /api/sign-out`, `POST
   /api/sign-up` (no `filter`; signed in after it), `POST /api/password`, `GET` and `PUT /api/profile`; a user whose
   password change is due reaches only the change and sign-out (403 elsewhere); a guest's write is 401. The site writes
   the copy's user-data tables only (#331): sessions, users, profiles, and a key marked used at sign-up.
   `frontend/`: `bar.ts` (the profile's shape, "changed" field by field, "copy from the other option", the values
   in words, Israel's date for "immediate", a 422 in words), `components/FilterBar.tsx`, `fields.tsx` (the area
   picker and every field), `controls.tsx` (the switch, the level, the popover, the number box, the two-thumb
   slider), `Header.tsx` (the user menu), `screens/Account.tsx` (sign-in, sign-up, the password change),
   `screens/Preferences.tsx`; `route.ts` gains the four screens and the question before leaving unsaved changes;
   the bar in `sessionStorage` (key `tlv.bar`, kept per viewer). The card's buttons pack to the left (#351).
   Tests: `tests/test_web_accounts.py` (groups 1, 2, 6, the write checks, the refusals, the logs);
   `frontend/src/bar.test.ts`, `frontend/src/components/Card.test.tsx`. Checked in Chrome at the six sizes of round
   11 over a scratch copy (`SESSION_LOG.md`, round 12).
6. Viewed, not viewed, the report button on the closed card (#328), the flag, the report, the conflict messages;
   WhatsApp's link format read first. **Ron flags and reports** on the copy (they stay in it, #331).
   **Built 2026-10-14 (round 13):** `postmodel/rejects.py` `flagged_lifecycle` and `reported_lifecycle` (Gate E's flag and
   report rules, #279, #280; pure); `web/writes.py` (wiring: `flag_card` writes every one of `Card.canonical_ids` by
   compare and set, a member no longer active skipped, one re-read on `StaleRecordError`, so a result can be partial,
   #330 point 21; `report_post` writes the report first, then the shown post's record, one re-read, else the report stays
   and the admin handles it; the reportable fields' Hebrew labels, #277); `routes.py`: `POST` and `DELETE
   /api/viewed/{id}`, `POST /api/flag/{id}` (`{flagged, of, remaining}`), `POST /api/report/{id}` (`{removed}`; a second
   open report 409 `already_reported`), a post no longer in a current card 409 `gone`; a user's cards carry `viewed` and
   are ordered by it (#62), a guest's carry none; `/api/reference` gives each reportable field with its label. `web/app.py`
   opens a second, writable Repository on the copy for the two lifecycle writes. **The site writes the copy only (#331):**
   now also `viewed_posts`, `reports` and `post_lifecycle`; never a `RawPost` or a `Listing`. `frontend/`:
   `components/actions.tsx` (the report menu, the confirmation, the report form, the notice), the card's "דיווח" button
   furthest left and its viewed state (dimmed, "נצפה"), the opened post's foot ("סימון כלא נצפה", "דיווח") on a desktop and
   the top bar's "פעולות" on a phone, `App.tsx` (the flag's confirmation, the notices with a retry, the list reloaded
   after a flag or a report), `styles/actions.css`; the phone's bar compacted (#353). Tests: `tests/test_web_writes.py`
   (group 7), `tests/test_postmodel_rejects.py` (group 9's two functions), `Card.test.tsx`. Checked in Chrome at the six
   sizes on a scratch copy (`SESSION_LOG.md`, round 13).
7. The measured page load (h), on the copy and on a 40-day synthetic store (#330), Lighthouse, the `design` plugin's
   critique and accessibility review, a colour-vision check. **Ron reviews** the numbers and the look.
   **The plan for step 7's measurements: APPROVED by Ron with points 40–42 as recommended (#368–#370, round 16); MEASURED 2026-10-14/15 (round 16): the results follow the plan, below. Two targets are missed on the 40-day store; nothing was changed.**

#### Step 7's measurements — the plan (round 15, for Ron's approval)

Free throughout: no model call, no Apify call, nothing installed. **The production store is only ever read** (`mode=ro`,
its SHA-256 checked before and after); every store measured is a scratch file in the session's scratchpad, outside the
repository, served by a scratch launcher (`web.app.site_over` and uvicorn on 127.0.0.1, as in round 13). No repository
code changes for the measurements: `Server-Timing` (h) is already on `POST /api/cards`.

**The two stores.**

| | S1, today | S2, 40 days (synthetic) |
|---|---|---|
| Made how | SQLite's online backup of the production store from a read-only connection (as `serve --copy`), into the scratchpad; photos read in place from `data/store/images/` | S1, then 31 more copies of every post added (below), with their own photo files in a scratch `images/` |
| Posts | 266 (139 active with a `Listing`, 89 rejected, 38 pending) | about 8,512 (32 × 266; 40 days × run A's 212 a day is 8,480, 3.6's figure) |
| Members (active canonicals with a `Listing`) | 139 | about 4,448 |
| Cards for a guest's empty bar | 123 | about 3,936 |
| Members' photo files | 620, 94 MB | about 19,840, about 3.0 GB (155 GB free on the disk) |
| The list's JSON for that bar | about 400 KB | about 13 MB, estimated linearly: what #346 asks |

**How S2 is built** (a scratch script, the method of 3.6 (c)'s synthetic scale, but written to a real file so the site
reads it). Today's 266 posts span 27 hours (2026-10-03 13:41 to 10-04 16:43 UTC), so 32 copies 1.25 days apart cover 40
days. Copy *k* (1 to 31) of every post, in every state, so the mix stays today's:
- `RawPost`: a new `source_post_id` and its `listing_id` (`compute_listing_id`, the one implementation); `posted_at` and
  the lifecycle's `last_published_at` moved back *k* × 1.25 days, the whole set shifted so the newest copy is today; the
  text with a short copy marker appended (so its `text_hash` differs; the hash by `textnorm`, the one implementation);
  every phone (`RawPost.phones`, the `Listing`'s `phone_names`) mapped to a synthetic number, **the same map inside a
  copy and a different one per copy**. So the four real pairs still tie inside each copy (about 128 two-post cards) and
  no copy ties another (the key needs a shared non-agent phone or a shared photo, 3.6 (c)).
- Photos: for a member, each file copied to a new path with a few bytes appended (a JPEG reads to its end marker), so each
  copy has distinct bytes and a distinct hash, and the cold hashing reads 3 GB as it would. Hard links would cost no disk
  but would read the same cached bytes, which hides the cold cost. A non-member's image entries keep the original paths
  (the site never reads them).
- Written through the Repository (`upsert_with_lifecycle`, `save_classification` on the scratch file), so every record
  passes its contract; the `Listing` copied with the new `listing_id` and phones, nothing else changed. The pending posts
  stay pending (no `Listing` is invented).
- **No post is archived**, though at 40 days Phase 5's job would have archived the posts older than 25 days. Until Phase 5
  nothing archives, so this is the store the site will actually face, and an upper bound on the steady state (point 40).

**What is measured, on S1 and on S2.**
1. **On the server** (a scratch client on 127.0.0.1, reading `Server-Timing` and the wall time; each step's `gen`,
   `group`, `eval`, `order`, `json`): `POST /api/cards` for a guest's empty bar **cold** (the first request after a start:
   the whole grouping and every photo hashed), three starts; **warm**, ten requests (median and maximum); **after a store
   change** (a test write on the scratch file, a flag through the API, then the next request recomputes). The same warm for
   a signed-in user's saved preferences (the admin, a test password set on the scratch copy only, as round 13); `GET
   /api/posts/{id}`; the preferences page's live count (the same endpoint, #352 point 38). The response's size in bytes and
   the site process's memory after the grouping. The disk cache is not controlled (Windows): cold means the site's own
   memory, not the disk's.
2. **In Chrome** (chrome-devtools, Ron's laptop, no throttling: the targets are on his laptop): a performance trace with a
   reload at 1440 × 900 and at 390 × 844 (phone, touch): the time to the first cards drawn (the first card element in the
   DOM, read by a script in the page, and the trace's LCP), the whole load, long tasks; cold, warm, after a store change.
   On S2 also the DOM's size and the page's memory with about 3,900 cards, and whether scrolling stays smooth (the trace
   while scrolling). One phone trace with 4× CPU and "Fast 4G" for information only.
3. **Lighthouse** (chrome-devtools' `lighthouse_audit`: accessibility, best practices, SEO; this version of the tool
   leaves performance to the trace of 2) on the list, an opened post, sign-in and the preferences page, desktop and
   mobile, on S1.
4. **The `design` plugin's critique and accessibility review** (`design:design-critique`, `design:accessibility-review`)
   on screenshots at the six sizes of round 11 (#347), a guest and signed in, on S1; keyboard and screen-reader names
   checked in the page (the accessibility tree).
5. **Colour vision** (#323): chrome-devtools' `emulate` in this version has no vision-deficiency setting, so the page is
   filtered in place by a script that adds an SVG colour matrix (protanopia, deuteranopia, tritanopia, achromatopsia;
   Machado et al. 2009 matrices) to the scratch page only, with screenshots of the glow, the chips and the badges; and the
   tokens' contrast ratios computed. An approximation of what Chrome's own emulation does (point 41).

**Reported** in `SESSION_LOG.md` with each store's size, against the targets (#330 point 20): warm `POST /api/cards` under
300 ms on the server; first cards under 1.5 s; on S1 and S2. **If a target is missed, nothing is changed in step 7:** the
options already recorded (#345 the grouping computed at start and after a change in the background; #346 the first lines in
the list; a bulk read, 3.6 point 13) are proposed to Ron with the numbers, and anything new (for example paging the list,
or compressing the response) as a new point. The design and accessibility findings are fixed in step 7 only where they
break an approved rule; the rest are listed for Ron.

**Kept and removed:** S2 (about 3 GB) and the scratch copies stay in the scratchpad until Ron has read the numbers, then
are deleted; nothing of them enters the repository or `data/`.

**New points (for Ron):**
- 40. **S2 without archiving** (recommended: the store the site meets until Phase 5, an upper bound). Or: the posts older
  than 25 days archived (their photos removed), the steady state after Phase 5, about 5,300 active posts instead of 8,512.
- 41. **The colour-vision check by an injected filter** (recommended; no install). Or: Chrome's own rendering emulation by
  hand in DevTools' Rendering panel, which Ron would do himself, since the tool does not reach it.
- 42. **The copies' photo bytes on disk** (recommended: distinct files, about 3 GB in the scratchpad, deleted after). Or:
  hard links (no disk), with the cold hashing under-measured.

#### Step 7's results (round 16, 2026-10-14/15) — nothing changed in the repository

**What was made.** S1: SQLite's online backup of the production store (read-only connection): 266 posts, 139 members, 123
cards, photos in place. S2: S1 plus 31 synthetic copies, built through `SqliteRepository` on a scratch file with every
record validated: **8,512 posts, 4,448 members, 3,967 cards for an unfiltered bar, 19,840 member photo files, 2.9 GB of
photos, 108 MB of database**, no archiving (#368), each photo with its own bytes (#370), built in 140 s. Copy *k* is
shifted back *k* × 1.25 days (the newest copy is the real data, 10 days old), phones mapped per copy, `text_hash` derived
from the original's and the copy number (so the dedup A classes stay), the texts **not** marked (the stored hash is what the
key reads: deviation 1). The four real pairs still tie in each copy. The site ran from a scratch launcher (`web.app.site_over`,
uvicorn on 127.0.0.1); the production store's SHA-256 `5df9bc9a…` the same before and after; no model, no network beyond
127.0.0.1; nothing installed.

**On the server** (a scratch client; `Server-Timing`; Ron's laptop, SQLite 3.45.3):

| | S1 (123 cards) | S2 (3,967 cards) | Target |
|---|---|---|---|
| Cold, first request after a start, OS cache warm (3 starts) | 402–502 ms (`group` 384–485) | 15.4 s and 16.1 s (`group` 15.1, 15.8) | none (#345 decides) |
| Cold, files not in the OS cache | — | **127.8 s** (`group` 127.4) in the first run; **120.0 s** (`group` 118.3) in Chrome's run | none |
| Warm, a guest's empty bar, median (max) of 10 | **34 ms** (44) | **554 ms** (627): `eval` 36, `order` 13, **`json` 372** | **300 ms** |
| Warm, signed in with the saved profile, median (max) | 37 ms (60) | 462 ms (619): `json` 264 | 300 ms |
| After a store change (a flag), the next request | 266 ms (`group` 245), then 27 ms | **10.6 s** (`group` 10.1), then 346–532 ms | — |
| The response | 457,674 B | **14,768,550 B** | — |
| The opened post / one photo | 16 ms / 16 ms | 12 ms / 2.5 ms | — |
| The site's memory after the first grouping (at the end) | 75 MB (76) | 354 MB (519) | — |

**In Chrome** (chrome-devtools, 1440 × 900 and 390 × 844 touch, no throttling, the first card drawn read from the DOM):

| | S1 desktop | S1 phone | S2 desktop | S2 phone | Target |
|---|---|---|---|---|---|
| First cards drawn, warm server (reload) | **0.21 s** | **0.22 s** | **3.0 s** | **3.3 s** | **1.5 s** |
| First cards drawn, cold server, OS cache warm | about 0.7 s (derived: 0.5 s server + 0.2 s) | same | about 18 s (derived) | same | 1.5 s |
| First cards drawn, cold server, cold disk | — | — | **121 s** (measured; the page shows "טוען מודעות…" throughout) | — | 1.5 s |
| `/api/cards` response end | 0.13 s | 0.16 s | 1.6 s | 1.7 s | — |
| Longest frame | 0.23 s | 0.18 s | **4.8 s** | **5.4 s** | — |
| DOM nodes, JS heap | 6,933, 9 MB | 6,914, 5 MB | **221,453, 84–136 MB** | similar, 80 MB | — |
| Scrolling the whole list, per frame (median / p95) | — | — | — | **137 ms / 185 ms** (about 7 fps) | — |

The S1 cold browser load was not measured cleanly (the page had already asked for the cards before the restart took
effect); the cold figures marked "derived" add the server's cold request to the warm browser figure.

**Reading against the targets (#330 point 20).** On today's store both are met by a wide margin (warm 34 ms, first cards
0.2 s). **On the 40-day store without archiving both are missed:** the warm request is 554 ms (the JSON build of 14.8 MB is
two thirds of it), and the first cards take 3.0 s warm, of which about 1.4 s is the request and most of the rest the draw of
3,967 cards (a 4.8 s long frame, 221,000 DOM nodes). The cold request is 15 s warm-cache and 2 minutes on a cold disk
(hashing 19,840 files, 2.9 GB), and a store change makes the next request wait 10 s. S2 is an upper bound: with the posts
older than 25 days archived after Phase 5 (point 40's alternative, about 62% of S2) a linear estimate is about 345 ms warm.
**The unfiltered bar is the worst case: a user with a price or area range sees far fewer cards; that was not measured.**

**What Ron would have to choose, with the numbers (none built):**

| Option | Recorded as | Moves | Does not move |
|---|---|---|---|
| **A. Send the first N cards and the count; the rest on scroll** (paging or a window) | new point | `json` (372 ms) and the response (14.8 MB) scale with N: N = 100 is about 370 KB, S1's size, about 35 ms warm; the DOM falls from 221,000 nodes to about 6,000 and the 4.8 s frame with it; scrolling stays at S1's smoothness | the grouping's cold 15 s and the 10 s after a change |
| **B. The first lines of the text only** | #346 | 23% of the JSON is the text (105 of 458 KB on S1): about 3.4 MB of 14.8; `json` about 285 ms | the DOM, the grouping; alone it still misses 300 ms |
| **C. Compress the response** (gzip) | new point | 15% of the size (69.5 KB of 458 KB): 14.8 MB to about 2.2 MB, which matters over Tailscale to a phone; no library to install (Starlette's `GZipMiddleware`) | the server's `json` time (the middleware adds some) and the render |
| **D. Compute the grouping at start and after a change, in the background** | #345 | no visitor waits the 15 s (or 10 s after a flag); the 2 minutes of a cold disk is paid at the start, not at the first visit | the warm request and the render |
| **E. Keep the photo hashes between runs** (on disk) | needs a decision: #231 says the memo is never written | the 118 s of a cold disk becomes seconds after a restart | the list |
| **F. Archive at 25 days (Phase 5)** | `BACKLOG.md` | the store the site meets is about 62% of S2 | the same shape, a smaller number |

The reviewer's reading, for Ron to confirm or reject: **A plus D** answer both missed targets and the 15 s cold request;
B and C are smaller and independent; E only if a restart on a cold disk matters (the site restarts rarely). The N = 100 and
35 ms figures are estimates from S1's measured size, not measured.

**Lighthouse** (chrome-devtools; accessibility, best practices, SEO; desktop and mobile; S1; the list, an opened post, the
preferences page and sign-in; the reports are in the session's scratchpad): **accessibility 100 on the list, preferences and
sign-in, 97 on the opened post; best practices 100 everywhere; SEO 82–83.** What failed:
- `color-contrast` (opened post): the grey "לא צוין" chips, #69717b on #f2f1ee, **4.37:1** (4.5:1 needed; the token's
  comment says 4.8:1 on white); on the desktop dialog the photo counter "1/5" (aria-hidden, over a photo) 1.74:1.
- `label-content-name-mismatch` (WCAG 2.5.3, Label in Name): the logo (`aria-label` "TLV Apartment Hunter, לעמוד
  הראשי"), the card's "i" button (visible "i", name the tier's reason), the user pill (name "החשבון של …").
- `cumulative-layout-shift`: 0.059 on the list, **0.42 on the opened post at its own address (desktop)**.
- `meta-description`, `robots.txt` (the site answers `/robots.txt` with the page, "16 errors"), `llms.txt`: search-engine
  items that do not apply to a site only the tailnet reaches (#307); listed, not recommended.

**The `design` plugin's accessibility review** (its WCAG 2.1 AA list, on the scratch copy, by script and by eye; not a
screen reader):
- *Perceivable:* as above (contrast). Colours never carry meaning alone: every chip, the kind, the tier ("i") and the
  buttons carry words.
- *Operable:* **the closed card's controls are small for touch** — the "i" 28 × 28, the three foot buttons 26 px high
  (Facebook 62, report 46, WhatsApp 69 wide; 123 of each on the list), the carousel's arrows 34, the bar's chips 34, the
  user pill 40, "סינון" 34; the 44 px of 2.5.5 is met by none of them, the 24 px of WCAG 2.2's 2.5.8 by all. **The dialog is
  `role="dialog"` `aria-modal`, focus moves into it and Escape closes it; the focus is not returned to the card that
  opened it (it lands on the page).** No `h1` or `h2` on the list or the opened post (the preferences page, the forms and
  the report dialogs have them); landmarks: one `header`, one `main`.
- *Not done:* a pass of the keyboard order over every control; a screen reader (NVDA, VoiceOver); 200% zoom as such (at 390
  px and 1440 px nothing scrolls sideways); the preferences page's and the forms' touch targets.

**Colour vision** (point 41, an SVG colour matrix on the page of the scratch copy; Machado et al. 2009, severity 1.0; the
tokens computed too): the tier colours as seen, CIE76 ΔE between green / amber / red: normal 85 / 100 / 65 (green-amber,
green-red, amber-red); **protanopia 49 / 22 / 62; deuteranopia 63 / 18 / 45**; tritanopia 83 / 111 / 31; **achromatopsia 6 /
8 / 14** (all three at lightness 45–59). Green and red are close under protanopia and deuteranopia, and the three are
indistinguishable in grayscale; as #323 accepts, the "i" and the words carry the tier. In the grayscale screenshot the green
chips, the grey chips and the plain text read as three weights of grey, and the three foot buttons differ only by their
words. (The admin's profile on S1 shows no green card, so the green ring itself was judged from the tokens.)

**The design critique** (the phone list and the opened post, S1, signed in): the hierarchy is clear (kind, price, place,
text, stats, foot), the viewed card is dimmed and worded, the photo carries the "i" and the dots. Two things to look at:
**the opened post on a phone shows a wall of six grey "לא צוין" chips** before the first useful row when little is written
(one line saying "not written: parking, balcony, …" would carry the same facts), and **the closed card's reserved slots
(#341) leave a gap above the foot** on a card with no chips. Neither breaks an approved rule; both are Ron's calls.

**Deviations:** (1) the copies' texts were not marked with a copy tag (the key reads `text_hash`, which was derived);
(2) S2's newest copy is the real data (10 days old), not today; (3) the S1 cold browser load was not measured cleanly;
(4) the "after a store change" case was measured on the server, not in the browser; (5) traces were taken for S1 phone and S2
desktop (saved in the scratchpad); the time to the first card was read from the DOM on all four combinations.

**New points for Ron (3.7):**
- 43. **The two missed targets on S2:** which of A–F (above), if any. Recommended: A and D. **Decided: A, C and D (#371).**
- 44. **The small touch targets of the closed card** (the "i" 28 px, the foot's 26 px buttons): enlarge to 44 px on a
  touch screen (the foot rows #341 grow), or keep (above 24 px). Recommended: enlarge on touch. **Decided: yes (#372); built as a touch area, point 55.**
- 45. **The grey chip's contrast** (4.37:1): darken the grey text one step on the chip's background. Recommended: do it. **Decided: yes (#373), built.**
- 46. **Label in Name and the focus return:** the logo, the "i" and the user pill's names to start with their visible text;
  the focus returned to the card on closing the post. Recommended: do it. **Decided: yes (#374), built.**
- 47. **The six grey chips on a phone's opened post**, and **the gap above a chipless card's foot:** as listed. Recommended:
  leave. **Decided: leave (#375).**

#### Round 17 (2026-10-15): C, 44, 45 and 46 built (#371–#374); A and D planned, waiting for Ron

**Built.**
- **C, gzip (#371).** `web/app.py`: Starlette 1.7.0's `GZipMiddleware` (read in the installed source, `starlette/middleware/
  gzip.py`), `minimum_size` 500, `compresslevel` 6 (its default is 9), its default exclusions passed explicitly, so a JPEG,
  PNG or woff2 is never compressed. It covers every response the site sends, the built JS and CSS too, not only `/api`
  (deviation 1). Measured on today's store: the list **457,674 → 69,525 bytes**, `Vary: Accept-Encoding`; the compression
  **adds about 15 ms** to a warm request (median 34 ms against 19 ms, 10 each, curl on 127.0.0.1), which at the 40-day
  list's 14.8 MB would be about 0.5 s: one more reason A comes with it.
- **44, touch areas (#372).** On a touch screen (`pointer: coarse`) every closed-card and header control has an invisible
  `::after` touch area of at least 44 px: the foot's buttons and the "i" (already there since round 11, widened by 1 px),
  the photo's arrows, the bar's chips and "סינון", the user pill, the logo; the chip's ellipsis kept by `overflow: clip`
  with a margin. Nothing grows, so #341's slots and every card's height are unchanged (point 55).
- **45, the grey (#373).** The `--grey` token, one place: `#69717b` → `#646b75`: 4.77:1 on the chip's `--grey-bg`, 5.4:1 on
  white; every "לא צוין" uses it.
- **46, Label in Name and the focus (#374).** The logo's two words separated (`TLV Apartment Hunter`, as its name starts);
  the "i" and the avatar's letter drawn by CSS (`::before`), icons, so the "i"'s name is the tier's words and the user
  pill's name starts with the username (`<username>, תפריט החשבון`); closing a post opened from the list (Escape, the close
  button or the browser's back) returns the focus to the card's link, which scrolls a half-visible card into view.
- Tests: `tests/test_web.py` +3 (the list gzipped only when asked, the same JSON, `Server-Timing` and the two headers kept; a
  photo never gzipped; a small answer sent as it is); `frontend/src/components/names.test.tsx` (3: the "i" holds no text, the
  logo's words, the pill's name and the avatar's letter).

**Checked in Chrome** (a fresh online backup of the store in the scratchpad, signed in, port 8801):

| Size | Columns, card height, sideways scroll | Touch areas (box → touch area) |
|---|---|---|
| 2560 × 1440 | 6, one height, none | mouse: compact sizes kept |
| 1440 × 900 | 4, 606 px, none | mouse |
| 1366 × 768 | 4, 592 px, none | mouse |
| 1194 × 834 touch | 3, 639 px, none | "i" 28 → 45; foot 26 → 45; arrows 34 → 46; bar chip 34 → 44.7; pill 40 → 45; logo 44 → 52 |
| 834 × 1194 touch | 2, 650 px, none | the same |
| 390 × 844 touch | 1, 318 px, none; the bar still 91 px | "i" 45; foot 45; "סינון" 34 → 45; pill 45; logo 36 → 44 |

The focus returned to the card on Escape and on the browser's back. **Lighthouse after the change:** Label in Name passes
everywhere; the grey chip passes; the opened post is 100 on mobile and 97 on desktop, the list 96 on desktop. Both remaining
failures are the photo counter "1/5" (white on a translucent dark pill over a photo, measured 1.74:1, aria-hidden), a
round-16 finding outside #373 (point 56). The look is unchanged at every size.

#### Plan for A (the first cards, the rest as the user scrolls) — APPROVED (#376–#378); BUILT round 18

**The shape (point 48).** `POST /api/cards` keeps its body (the bar) and adds `first` (default 48). Per request the server
still evaluates and orders **every** card (on the 40-day store `eval` 36 ms and `order` 13 ms, measured), and returns:
`count`; `order`, **the whole ordered list of card ids** (3,967 × 64 hex characters, about 270 KB on the 40-day store, but
nothing to draw); and `cards`, the full payload of the first `first` cards only. A new `POST /api/cards/by-id` `{bar, ids}`
(at most 96 ids) returns those cards' payloads, evaluated against the same bar; an id is any post of a card (as
`/api/posts`), so a card regrouped meanwhile is still found; an id no longer in any card comes back in `gone`.
- **N = 48**: whole rows at 2, 3, 4 and 6 columns; about 180 KB of JSON, about 25 KB gzipped; the page asks the next 48
  when its last card comes within about one and a half screens of the view (an `IntersectionObserver` on a sentinel, no
  library).
- **The order stays right because it is fixed for the load.** The page holds the ordered ids of its load and asks pages
  from it, so nothing is skipped or shown twice whatever happens meanwhile; the order changes only on the next load (a
  bar change, a reload, "ההעדפות שלי"), as the viewed order already does (round 13, deviation 4).
- **The glow and the tier** come with each card's payload, from the same `evaluate` against the same bar, so a page asked
  later glows as the first; **the count** is the first answer's, less the cards the user removed (below).
- **Viewed:** the mark is set on the list's card at once and the order follows on the next load, as today; "mark as not
  viewed" the same. Viewed cards stay where they are in a load.
- **A flag or a report (point 49):** the card leaves the list in place and the count drops by one, **with no reload**, so the
  user keeps their place; today the list reloads, which with paging would send the user back to the top. A 409 `gone`
  does the same.
- **The bar:** any change starts a new load from the top, as today. **The preferences page's live count (point 50)**
  asks `first: 0` and reads `count` (no order, no cards).
- **Estimated on the 40-day store** (from the measured parts, to be measured at the build): a warm list request about
  60–70 ms (evaluation and order 50, the ids and 48 cards' JSON about 10, gzip a few); a page of 48 by id a few
  milliseconds; the first 48 cards drawn well under the 1.5 s target, since the draw is about 2,600 DOM nodes instead of
  221,000.
- **Not in A (point 53):** cards already drawn stay in the page; a user who scrolls through all 3,967 cards of an
  unfiltered 40-day list ends with today's DOM size, reached a page at a time (each append short). Removing far-off cards
  (a virtual list) is a further step, measured first.
- **Tests:** `order` equals today's `ordered`; `first` slices it; `by-id` gives the same payload as the first page for the
  same card; `gone` for a flagged card; the count with `first: 0`; a guest and a user alike; invariant 12 (nothing per user
  written on a post). Vitest: the page's merge of pages (no duplicate, order kept, a removed card skipped). Chrome at the six
  sizes and step 7's measurement again on S1 and a rebuilt S2.

#### Plan for D (the grouping computed in the background) — APPROVED (#379, #380); BUILT round 18

**Today (#301, #316):** a request reads the store generation (about 1 ms); when it moved, the request computes the grouping
while holding the lock, and every request waits for it (15 s at 40 days, 10 s after a flag).

**Proposed:**
1. **At start**, `serve` begins the first grouping in a background thread at once, before any visitor.
2. **A request never computes.** It reads the generation as today; when the generation moved and no recompute is running,
   it starts one in the background (one at a time, the lock as today) and answers at once **from the snapshot it holds**.
   When a recompute ends and the generation moved again meanwhile, one more runs. #301 holds: the grouping is computed once
   for all users, only when the store changed; #316's counter is still how the site knows.
3. **The first grouping after a start (point 52):** there is no snapshot yet. Today a request waits for it (the page shows
   "טוען מודעות…"): at 40 days 15 s, or about 2 minutes on a cold disk. Proposed: the API answers "loading" and the page
   retries every few seconds with the same words, so no request holds a connection for minutes.
4. **A user's own flag or report leaves the list at once (point 51)**, though the snapshot is older than the write: the site
   keeps a small **removal overlay**, the ids of the posts it has itself just made inactive, with the store generation after
   the write. Every list, `by-id`, `/api/posts` and `/api/photos` answer leaves those posts out, and a write on one is
   409 `gone`, exactly as if the grouping were current; an entry is dropped once a snapshot at or after its generation is
   held. It only ever removes, never adds: a post the site made inactive is inactive in the store.
5. **What waits for the background recompute (point 51):** what other processes write (a collection run's new posts, a
   classification run, a run's rejection) and what changes a card without removing it (an admin's correction, 3.8): the
   first visitor after such a write sees the previous list, and the next request after the recompute ends (seconds; about
   10–15 s at 40 days) sees the new one. Today that first visitor waits instead.
6. **Memory:** two snapshots exist while a recompute swaps in; at 40 days about 350 MB each (measured), so about 0.7 GB at the
   peak. To be measured at the build.
7. **Threads:** one daemon thread for the recompute; the Repository opens its own read-only connection per call, as the
   request threads already do; the swap is one assignment under the lock.
- **Tests:** a request during a recompute is answered from the old snapshot without waiting (a `derive` that blocks on an
  event); one recompute at a time, coalesced; the start's background grouping; the overlay: a flag removes the card from
  the next answer before the recompute ends, `/api/posts` 404 and a write 409 `gone` for it, the overlay dropped at the new
  snapshot; the "loading" answer before the first snapshot (if point 52 is taken); `Server-Timing` keeps `group` only where
  a request waited.

**New points for Ron (A and D):**
- 48. **The paging shape:** the first 48 cards with the whole ordered id list, the rest by id from that list; the order
  fixed for a load. Recommended.
- 49. **After a flag or a report the card leaves in place, with no reload** (today the list reloads). Recommended.
- 50. **The preferences page's count asks `first: 0`** (still no separate endpoint). Recommended.
- 51. **With D, other processes' writes and an admin's correction show after the background recompute** (seconds; 10–15 s at
  40 days) rather than making the next visitor wait; the site's own flags and reports leave at once by the overlay.
  Recommended.
- 52. **Before the first grouping after a start:** the API answers "loading" and the page retries (recommended), or the
  request waits as today.
- 53. **No virtual list in A:** cards stay drawn as the user scrolls; measured after A. Recommended.
- 54. **A and D built in one round**, A first (it moves both missed targets), measured with step 7's method on S1 and a
  rebuilt S2 (about 3 GB in the scratchpad again, deleted when Ron says). Recommended.
- 55. **#372 as built:** a 44 px touch area that does not grow the controls (above). Or: the controls drawn at 44 px on a
  touch screen, the foot's rows growing (#341's slots taller on touch). Recommended: as built.
- 56. **The photo counter "1/5"** (1.74:1 as Lighthouse measures it over a photo): a darker pill (for example 90% opacity,
  white text) to pass 4.5:1. Recommended: do it with A. **Decided (#376–#384): 48–56 as recommended; built in round 18.**

#### Round 18 (2026-10-15): A, D and 56 built (#376–#384); step 7 measured again — both targets met on both stores

**Built.**
- **A (#376–#378).** `web/filters.py`: `CardsRequest` (the bar and `first`, 0–96, default 48) and `ByIdRequest` (the bar and
  1–96 ids), both strict. `web/routes.py`: `POST /api/cards` and `GET /api/cards` evaluate and order every card as before and
  return `count`, `order` (every card's shown id) and the first `first` cards; `first: 0` the count alone; `POST
  /api/cards/by-id` the cards holding the ids asked, in that order, evaluated against the same bar, a card asked twice
  once, an id in no shown card in `gone`. `frontend/src/paging.ts` (pure: `firstLoad`, `nextIds`, `withPage`,
  `withoutCard`); `App.tsx`: the load keeps the order, the next 48 asked by an `IntersectionObserver` on a sentinel 1.5
  screens ahead, a failed page asked again; a flag, a report that removed or a 409 `gone` takes the card out in place, the
  count one less, no reload; `Preferences.tsx` asks `first: 0`.
- **D (#379, #380).** `web/grouping.py`: `Grouping(…, background=True)`, which `serve` runs: `start()` begins the first
  grouping at once; a request never computes, it starts a recompute in a daemon thread when the counter moved (one at a
  time; it runs again if the counter moved meanwhile) and answers from the snapshot it holds; before the first snapshot
  `NotReady`, which `web/app.py` answers 503 `{"refusal": "loading"}` with `Retry-After: 2` on every route, and the page
  asks again every 2 s with its "טוען מודעות…". **The overlay:** `Grouping.remove(ids)` after a flag (the members written)
  and after a report that removed the post (the shown one), with the store generation after the write; every answer leaves
  out a card holding one, until a snapshot at or after that generation is held. The foreground mode (the request computes)
  stays the default for the tests and for any caller that does not ask. `Grouping.wait(timeout)` waits for a background
  recompute to end (the tests use it).
- **56 (#384).** The counter's pill 90% opaque (was 72%); a viewed card dims its photos (`.track`), no longer the whole
  carousel with the counter, the dots and the arrows on it.
- **Tests:** `tests/test_web_paging.py` (new, 23: the first answer, the order equal to the whole list's, `first: 0`, `first`
  bounds, a later page equal to the whole list's cards, the same bar hiding a card, any post of a card found once, invalid
  page requests, viewed on a user's page, a flagged card gone by id; before the first grouping every answer "loading" and one
  recompute however many ask, `start()`, a request during a recompute answered from the old snapshot without waiting, one
  recompute for many requests, a user's flag and a removing report leaving every answer at once while the recompute is held
  shut, the overlay dropped at the new snapshot, the foreground mode unchanged); `tests/test_web.py` (the serve test waits for
  the background grouping; the POST list includes `by-id`); `frontend/src/paging.test.ts` (5).

**The stores:** S1, a fresh online backup of the production store (266 posts, 123 cards); S2 rebuilt with round 16's recipe:
8,512 posts, 6,208 `Listing`s, 4,448 active members, 3,967 cards for an unfiltered bar, 19,840 photo files (2.9 GB). Both in
the scratchpad, kept until Ron says (#382).

**On the server** (a scratch client on 127.0.0.1, `Server-Timing`; the site in background mode as `serve` runs it):

| | Round 16, S1 | Round 18, S1 | Round 16, S2 | Round 18, S2 | Target |
|---|---|---|---|---|---|
| Warm list, a guest's empty bar, median (max) | 34 ms (44) | **10 ms** (19) | **554 ms** (627) | **83 ms** (349); rested re-sample 74–90 ms | 300 ms |
| Warm list, signed in with the admin's profile, median (max) | 37 ms (60) | 48 ms (67) | 462 ms (619) | **289 ms** (718): `eval` 168 | 300 ms |
| The list's answer: bytes (gzipped) | 457,674 (69,525 in round 17) | 194,484 (36,138) | 14,768,550 | **455,881 (183,655)** | — |
| A later page of 48 by id, median | — | 28 ms (175 KB) | — | 51 ms (175 KB) | — |
| The count alone (`first: 0`), median | — | 23 ms | — | 239 ms | — |
| The first list after a start | 0.4–0.5 s, the request waiting | 1.8–2.2 s after the process starts (1.55 s of it uvicorn's start); 1–3 "loading" answers | 15–16 s, the request waiting; 120–128 s on a cold disk | **23–27 s** (polled 5 times a second; 39 s polled every 3 s); **336 s on a cold disk** (the first start after the build); "loading" answers meanwhile, each at most 0.4 s | none |
| After a store change (a flag) | the next request 266 ms (recompute), then 27 ms | no request waits: answers median 50 ms (max 287) while the recompute runs; the new grouping held after 2.6 s | the next request 10.6 s | no request waits: answers median 302 ms (max 1.27 s); **the new grouping held after 188 s** with the client asking 10 times a second | — |
| The flagged card in any answer after the flag | — | never | — | never | — |
| Memory after the first grouping (at the end) | 75 MB | — | 354 MB (519) | 348 MB (561) | — |

**In Chrome** (1440 × 900 and 390 × 844 touch, no throttling; the first card drawn read from the DOM):

| | Round 16 | Round 18 | Target |
|---|---|---|---|
| S1 desktop, first cards (warm) | 0.21 s | 0.35 s (the list's answer ended at 0.26 s, 36 KB) | 1.5 s |
| S1 phone, first cards (warm) | 0.22 s | 0.52 s (a first, disturbed load 1.33 s) | 1.5 s |
| **S2 desktop, first cards (warm)** | **3.0 s** | **1.10 s** (the answer 0.62 s, 184 KB) | 1.5 s |
| **S2 phone, first cards (warm)** | **3.3 s** | **0.61 s** | 1.5 s |
| S2 longest frame at the load; DOM nodes | 4.8 s; 221,453 | **0.27 s; 2,734** | — |
| S2 phone, scrolling per frame (median / p95) | 137 / 185 ms | **17 / 94 ms** | — |
| S2 desktop, eight pages scrolled in (432 cards) | — | 48 more cards per page, no duplicate; pages answered in 70–240 ms; each append a frame of 220–420 ms; DOM 23,927 nodes, heap 25 MB; the forced scroll test 64 ms per frame at that size | — |
| S2, the page opened right after a restart | — | "טוען מודעות…", asked again every 2 s (15 times), the cards drawn at 32.7 s, no reload by hand | — |

**Reading.** **Both targets are met on both stores**: a guest's warm list is 83 ms on the 40-day store (was 554), a
signed-in list 289 ms (at the edge: its `eval` is 168 ms, the admin's preferences costing three times an empty bar's), and
the first cards are drawn in 1.10 s on a desktop and 0.61 s on a phone (were 3.0 s and 3.3 s). No visitor waits for the
grouping any more, and a user's own flag leaves every answer at once. **Two things got slower and are named for Ron
(points 57, 58):** the background recompute shares the one Python interpreter with the requests, so while requests keep
coming it is much slower than a request's own (188 s against 10.6 s on S2 under 10 requests a second; 2.6 s against 0.27 s
on S1); and the laptop's own speed varied threefold during the run (`eval` 45 ms rested, up to 160 ms after minutes of
hashing), so every S2 number is from a laptop at work, the rested re-samples given where taken. On today's store the first
cards came later than in round 16 (0.35 s against 0.21 s on a desktop), well inside the target; not investigated.

**Lighthouse after 56** (S1, three viewed cards on the list): accessibility **100** on the list (desktop and mobile) and on
the opened post (desktop), where round 17 had 96 and 97; best practices 100.

**Checked in Chrome at the six sizes** (S1, signed in): no sideways scroll; one card height per size (2560: 619 px, 6
columns; 1440: 606, 4; 1366: 592, 4; 1194 touch: 639, 3; 834 touch: 650, 2; 390 touch: 318, 1); 48 cards and the sentinel at
each; the phone's bar 91 px. **The flag from the page:** on the second page (scrolled to 9,531 px) the card left in place,
the count 123 → 122, the scroll kept, no list request, the notice shown.

**Not verified:** a real phone or iPad; the background recompute's time with real (sparse) traffic, only with a client asking
continuously or every 3 s; the loading state over Tailscale; the S1 cold load in the browser.

**Deviations:** (1) `Grouping.wait()` added for the tests (the suite forbids a real sleep); (2) the viewed card's dimming moved
to the photos (#384's note); (3) the foreground mode kept as the default of `site_over`, `serve` asking for the background.

**New points for Ron (3.7):**
- 57. **The background recompute under traffic** (188 s on S2 while requests come 10 times a second; 2.6 s on S1). Options:
  leave it (real traffic is a few people; recommended, measured again on the working day, 3.10); or run the recompute in a
  separate process, so it does not share the interpreter with the requests (a larger change); or keep the evaluation of a
  bar between requests, which is now the main per-request cost.
- 58. **The signed-in list on S2 at 289 ms** (the target 300 ms, max 718): its `eval` (168 ms) is the cost. Options: leave
  it (recommended: the target is met, and the 40-day store is an upper bound); or keep each bar's evaluation for the
  snapshot (the same as 57's third option).
- 59. **The scratch stores** (S1 11 MB, S2 3.2 GB in the scratchpad): **safe to delete once Ron has read these numbers;**
  not deleted (#382).

**Decided by Ron, 2026-10-15 (round 19):** 57 leave, measured again on the working day, 3.10 (#385); 58 leave (#386); 59
delete: S1 and S2 deleted in round 19 (#387). **3.7 is complete (#388).**

### (m) What I could not verify

- The times of (h) on a 40-day store; today's store holds 266 posts.
- `TestClient`'s client package in Starlette 1.7.0, and that it opens no socket (above).
- WhatsApp's link format (above); the font's subsets.
- How the site and a job command meet on the busy timeout (#259) when a recompute reads during a run: measured on the
  working day (3.10).
- That a dialog with a long Hebrew text and a carousel stays usable at 390 px: the round-8 mock was checked as a real
  390 px page in headless Chrome (screenshots only; chrome-devtools did not connect in round 8), not with real touch.

### (n) Points for Ron (3.7)

**Points 1–26 were decided by Ron on 2026-10-12 (#316–#331).** Each keeps its question as written in round 7, with the
decision after it.

1. **An unclear price with no price range:** as built, #302 covers a price **not written** only; an unclear price
   (another currency, a per-roommate price on a whole apartment) counts only against a set range. Or: an unclear price
   also always at the bottom. **Decided: as built (#318).**
2. **No green glow while the option holds no preference** (d, caution 2). Or: green whenever the tier is
   `"preferences_met"`. **Decided: no green glow (#322).**
3. **"The area unclear" in red:** by 3.6 an unclear area sends a post to the bottom only when the user chose areas.
   Kept so (recommended), or, like the price, always at the bottom. **Decided: kept so (#319); with no areas chosen it is
   capped at the middle by Ron's own rule (#320).**
4. **The glow's form:** A, the ring with a labelled chip (recommended), B or C (d). **Decided: the ring and soft
   shadow, with the "i" of #323, no labelled chip (#330).**
5. **The palette and the glyphs for colour blindness** (d). **Decided: the palette as recommended; no glyphs anywhere
   (#323, #330).**
6. **The important-missing style** (`BASELINE.md` §6 left it to this task): a dark slate badge with a "!" and the words
   ("no price", "no entry date"), stronger than grey and not a tier colour. **Decided: as recommended, without the "!"
   (#323, #330).**
7. **Parking not written:** "no parking" in grey (§6's text with #309's colour), or "parking: not stated".
   **Decided, generalised by Ron: every attribute not written is "לא צוין" in grey (#321).**
8. **Furnished "yes":** plain (not in #309's list, recommended), or green. **Decided: plain (#330).**
9. **The table of (c)**: which items sit on the closed card (Ron's request f). **Decided: (c) with Ron's notes
   (#323–#328, #330).**
10. **The link to the original post:** a main button inside, a small icon on the closed card (recommended). Following
    the icon from the closed card: does not mark the card viewed (#253 marks on opening; recommended), or does.
    **Decided: as recommended (#330).**
11. **How the site knows the store changed:** option 1, the generation counter by triggers, a layout change and a
    one-time migration command with a backup (recommended); or option 2, `PRAGMA data_version`, no layout change, many
    more recomputes. **Decided: option 1 (#316); the migration command at build step 1.**
12. **The list in one response** for a filter (no paging) until the measurement says otherwise; the filter sent in a
    `POST` body. **Decided: as recommended, the photos lazy-loaded (#330).**
13. **A guest's filter at sign-up:** "use my current filter as my preferences", checked when the bar holds a value.
    **Decided: as recommended (#330).**
14. **The bar's lifetime:** the tab's `sessionStorage` (a reload keeps it; a new visit starts from the saved
    preferences, or empty for a guest). **Decided: as recommended (#330).**
15. **Levels in the bar:** inside "more" (recommended), or on the preferences page only. **Decided: inside "more"
    (#330).**
16. **The font:** IBM Plex Sans Hebrew, as event-seeker (recommended), or another. **Decided: IBM Plex Sans Hebrew
    (#330).**
17. **The dependencies of (k)**, FastAPI 0.143.0 (three days old) and uvicorn without extras; `httpx` or `httpx2` for the
    tests, whichever Starlette 1.7.0's `TestClient` imports; Vitest for pure logic only. **Decided: as recommended,
    pinned exactly; `TestClient`'s client checked at the install before any test on it; WhatsApp's link format read
    before building on it (#330).**
18. **The module names of (l):** `tlv_hunter/web/`, `frontend/`, `policy/colours.py`, `flagged_lifecycle` and
    `reported_lifecycle` in `postmodel/rejects.py`, `jobs/serve.py`. **Decided: as recommended (#330).**
19. **Against cross-site requests:** `SameSite=Strict`, JSON-only writes and an `Origin` check, with no extra token.
    **Decided: as recommended (#330).**
20. **The targets of (h):** 300 ms on the server warm; the first cards under 1.5 s. **Decided: as recommended, also
    measured on a synthetic 40-day store (#330).**
21. **A flag on a card of several posts that is written on some members only** (one changed meanwhile): reported to the
    user as partial, with a retry (recommended); or all-or-nothing, which compare and set on two records in one
    transaction does not give (`save_lifecycle` writes one record). **Decided: partial, with a retry (#330).**
22. **What counts as a mobile number for WhatsApp** (#311): a normalized number starting with `05` and 10 digits long,
    decided in one place (`textnorm`, beside the one phone normalization). **Decided: as recommended (#330).**
23. **The area groups as data**, `reference/area_groups.yaml` read through `areas/reference.py` (recommended), or a
    table in the site's code (§6's open "where it lives"). **Decided: the YAML file (#330).**
24. **The count in the bar** ("79 posts") and on the preferences page. **Decided: as recommended (#330).**
25. **What the references show and the rules do not have**, not added: a street filter, a map, favourites, pets, a safe
    room or shelter, "renovated", a third kind "apartment for roommates", an email, a source badge, a "last week only"
    line. Any Ron wants is its own decision. **Decided: none added (#330).**
26. **The group's name** (`RawPost.group_title`) in the opened post: not in §6, so not shown (recommended), or shown.
    **Decided: not shown (#330).**

**New points from round 8 (for Ron; nothing of them is built):**

**Points 27–30 were approved by Ron on 2026-10-12 as recommended (#332).**

27. **A room post's rooms on the closed card when the apartment's total is not written** (#325 leaves it to the
    reviewer). **Recommended:** the stat reads "1" and, under it in grey, "סה״כ לא צוין" (total not stated), so the "1"
    is never read as a one-room apartment and #321's words are kept. Or: "1/" followed by a grey "לא צוין". Inside the
    post #120's wording stays ("a room", with no "of"). The mock shows the recommended form. **Decided: as recommended (#332).**
28. **What "only green chips" (#326) covers.** I read it as the **field chips** (broker, balcony, parking, elevator, air
    conditioning, "women preferred"). Not chips, and so kept on the closed card: the price, the location line (plain,
    green or orange; "מיקום: לא צוין" in grey when there is none), the four stats (rooms, size, floor, entry date, each
    "לא צוין" in grey when not written), the kind with the sublet mark, and the orange "kind unclear · shown as: room"
    (§8 requires every card to show which option it answers; #273 its kind marked). Consequence: "women preferred"
    (plain) moves inside. **Recommended: this reading.** Or: the grey stats and the unclear-kind mark also move inside. **Decided: this reading
    (#332).**
29. **The tier's label inside the opened post.** #323 takes the label's text off the card. **Recommended:** inside the
    opened post the label and, for the bottom, its reason are written in words at the top of the price block (the post
    is where the detail is). Or: the "i" there too. **Decided: in words (#332).**
30. **The closed card's carousel on a desktop** (#327): arrows that appear on hover, plus dots; on a phone a swipe and
    dots. Only the first photo loads with the page; the others as they scroll into view (#330, point 12). The arrows
    are chevrons drawn in CSS, which I read as controls, not state glyphs (#323 names the tier and the chips).
    **Recommended:** keep them. Or: dots only. **Decided: kept (#332).**

**New points from round 10 (for Ron):**

31. **Decided: as recommended (#345).** **The cold first request** takes 1.3 s on the server (1.7 s at the client) on today's store, above the 1.5 s
    first-cards target, once per store change or start; warm requests take 14–39 ms. **Recommended:** keep it lazy for now
    and measure it in the browser at step 7 (with the 40-day store); if it still misses, compute the grouping at start and
    after a store change in the background, so no visitor waits for it. Or: compute it at start now.
32. **Decided: as recommended (#346).** **The list's size:** 400 KB of JSON for 123 cards, since every card carries the poster's whole text (the closed card
    shows 3 lines, the opened post the rest). **Recommended:** keep it whole until step 7's measurement (warm requests
    are fast); if the page is slow, send the first lines in the list and the whole text with the opened post.

**New points from round 11 (for Ron; each is built as described, and changes in a line if Ron prefers the other):**
**Points 33–35 were approved by Ron on 2026-10-14 as built (#350).**

33. **A room post that gives only the apartment's size** (`BASELINE.md` §6 does not state it, #121). **Built:** the closed
    card's size stat reads "80" with a grey "כל הדירה" under it (as the rooms' "סה״כ לא צוין", #332); inside, "80 מ״ר (כל
    הדירה)". Or: shown as "לא צוין" for the room.
34. **The "i" on a card with no glow** (#322: the option holds no preference, as for every guest today). **Built:** the "i"
    is still there and says "לא הוגדרו העדפות בחיפוש הזה", so a guest learns why nothing glows. Or: no "i" on such a card.
35. **When the photos load** (#330 point 12, (c) row 1: "only the first photo is loaded with the page"). **Built:** every
    photo, the first included, loads as it comes near the view (the browser's lazy loading), so a list of 123 cards does
    not fetch 123 photos at once; measured at 1440 px, scrolling the whole list fetched 180 of 544 photos. Or: each
    card's first photo with the page.

**New points from round 12 (for Ron; each is built as described, and changes in a line if Ron prefers the other):**
**Points 36–38 were approved by Ron on 2026-10-14 as built (#352); point 39, option A (the switches stay in the top row,
one dense row under them), by #353, built in round 13.**

36. **Where "שינוי סיסמה" lives.** (f) says the password form "serves 'change password' from the menu", and #334 (later,
    Ron's own) names exactly two menu items, "ההעדפות שלי" and "התנתק". **Built:** the menu keeps #334's two items; the
    link "שינוי סיסמה" sits on the preferences page, under the summary. Or: a third item in the menu.
37. **What the quick chip "מיידי" sets** (#270 makes "immediate" a quick chip; its meaning in the range is not written).
    **Built:** "מיידי" sets the range's end to today in Israel ("until today"), so posts available now match, an
    "immediate" post included (it compares as the evaluation's date, #270). The two date boxes set any range. Or: a chip
    with another meaning, or more chips ("from the 1st of next month").
38. **The live count on the preferences page** (#330 point 24) asks `POST /api/cards` with the page's values, a moment
    after the last change, and reads its count: no count-only endpoint was added to (g). On today's store a warm request
    is tens of milliseconds and about 400 KB. **Built so;** measured with the rest at step 7 (#346), and a count-only
    answer added only if it is slow.
39. **The phone's sticky bar is 149 px** of an 844 px screen: the three switches wrap to two lines (each 44 px tall on
    touch) and the status line with "סינון (N)" is under them, as (e) describes. **Built so.** Or: the sublet switch moves
    into the sheet on a phone (one line saved), which (e) does not say.

## 3.8 The admin's pages — content approved (`BASELINE.md` §11; #75 B, #173, #243, #251, #254–#256); PLAN APPROVED 2026-10-15 with points 60–76 (#389–#406); build steps 1–3 BUILT (round 20), 4–6 BUILT AND CHECKED (round 21); points 77–83 decided and built (round 22, #407–#414)

**The approved content:**
- **Rejected,** every reason, canonicals only (#75 B), the city shown through `other_city_name` (#214).
- **Pending,** canonicals only (#75 B), with each post's `last_classification_error`; the "retry" that sets
  `classification_failures` back to 0 (Gate E, #139, #152).
- **Archive,** canonicals only (#75 B). Nothing is archived until Phase 5's job; the list exists and is empty.
- **Flags by user, and restore** (`BASELINE.md` §11; #251).
- **Reports grouped by field** (#173, #254), with restore, correct by hand (#256), or leave out; the corrections in
  force, and their removal.
- **Keys and users** (#243, #265, #266): issue, list, cancel; the password reset (#262); disable and enable a user.
- **Reports whose post was not rejected** (3.4 point 3), with a retry.

**The plan below is round 19's, for Ron's approval. Nothing of it is built.** The production store was opened read-only
once to size the lists (a `mode=ro` connection; SHA-256 `5df9bc9a…a77ac` before and after): today it holds 87 rejected
canonicals (`no_images` 23, `other_city` 21, `for_sale` 19, `not_listing` 13, `no_text` 9, `seeking` 2), 1 pending post
(1 failure: `73aebb24…`), 0 archived, 0 flags, 0 reports, 0 corrections, 0 keys, 1 user.

**Scope.** (a) Who reaches the pages; (b) where each list comes from, reusing 3.7's grouping and paging; (c) each page, what
it shows and does; (d) the endpoints; (e) every write, its compare and set (#260) and the restore rule (#251, #281–#283);
(f) what the admin can and cannot undo; (g) the invariants; (h) the modules; (i) the tests; (j) the build in steps.
**Not in 3.8:** the daily digest and the run interval / "run now" (Phase 5, #61); `max_posts` and schedule hours (Phase 6);
Telegram (Phase 4); the retention job, which applies the exemptions of #255 (Phase 5); starting a classification from the
site (the retry only makes a post eligible for the next `classify_pending` Ron runs); deleting anything (invariant 3).

### (a) Who reaches the pages

- **The API:** every route under `/api/admin/` checks the session through the one admin check of `accounts/` (point 68):
  a guest 401, a signed-in user who is not the admin 403, the admin while a password change is due 403 (as every 3.7 route).
  Every write is JSON only with its `Origin` checked (`web/auth.check_write`, #330 point 19), as 3.7's.
- **The pages:** `/admin` and its sub-paths in the same single-page app (3.7's history-based route, no router library);
  the header's user menu gains "ניהול" for the admin only (`GET /api/session` already carries `is_admin`). A non-admin who
  types `/admin` gets the page, whose API calls answer 403: the page says "אין הרשאה" and links home.
- **The admin is also a user:** their own list, preferences, viewed marks, flags and reports work as for anyone (3.7).

### (b) Where each list comes from — 3.7's grouping and paging reused

**Post lists (rejected, pending, archive, flags) ride the grouping's snapshot (point 67).** `dedup/stage_b.load_key_posts`
already reads every canonical's `PostLifecycle` in its one pass over `query()` (the members are the active ones with a
`Listing`). Proposed: the same pass also keeps **`KeyInputs.others`**, every canonical that is not a member, each with its
`RawPost`, its lifecycle, its `Listing` or `None`, and its `SeenListing` when it has one (the corrections are already in
hand). `web/grouping.Snapshot` gains `others` by `listing_id`. So:
- one read of the store feeds the users' cards and the admin's lists, at the same store generation, recomputed in the
  background on the same counter (#301, #316, #379); before the first snapshot every admin post list answers 503
  "loading" as the users' list does (#380);
- a list can be seconds behind another process's write (a collection run, `classify_pending`), as the users' list is
  (#379); **the admin's own writes change the row in place** from the write's answer (as A removes a flagged card, #377), and
  the counter moves, so the next snapshot agrees;
- **every action reads fresh from the store**, never from the snapshot: the post's detail page (`GET
  /api/admin/posts/{id}`) reads the `RawPost`, the lifecycle, the `Listing`, the corrections and the reports at that moment,
  and a write compares against what the detail page showed (point 61).
- Canonicals only (#75 B): `others` holds no dedup A duplicate (`KeyInputs.duplicates` already maps each canonical to its
  duplicates; the detail page lists them as the repost log, earliest `posted_at` first, #75 A).
- The Gate D key does not group the admin's lists: it ties only active members (#230, #231), and a rejected or pending post
  is not one. The flags page groups instead by the flag action (point 63).

**The other lists read `UserDataStore` per request:** reports (`find_reports`), corrections (`find_corrections(in_force=…)`),
keys (`list_keys`), users (`list_users`). They are small, and only corrections move the counter. A report's post is read
from the snapshot (its row) and fresh on its detail page.

**Paging, as A (#376):** `POST /api/admin/posts` returns the count, the whole ordered id list and the first 48 rows; `POST
/api/admin/posts/by-id` the next rows as the admin scrolls (an id no longer in that list comes back in `gone`); the order is
fixed for a load. The front end's `paging.ts` (`firstLoad`, `nextIds`, `withPage`, `withoutCard`) and the sentinel are reused
as they are. Order: the newest `last_published_at` first, then `listing_id` (point 73).

**The photos:** `/api/photos` serves only a current card's member (3.7 (g)), so a rejected post's photos need **`GET
/api/admin/photos/{listing_id}/{file}`**, admin only, by the same rule: the file must be a `PostImage.local_path` of that post's
lifecycle in the snapshot (a member, an `others` entry, or a duplicate of one); no path is built from the request. A
missing file (an archived post's photos are deleted at archive, Phase 5) is 404 and the page shows no photo.

### (c) The pages

| Page (path) | Shows | Does |
|---|---|---|
| **Overview** (`/admin`) | One line per list with its count (`GET /api/admin/summary`): rejected by reason, pending (and how many with failures), archive, flag actions and their posts, open reports, reports whose post was not removed, unfinished restores, corrections in force, unused keys, users | Links to each page |
| **Rejected** (`/admin/rejected`) | The rejected canonicals as rows (the first photo, the text's first lines, the reason in Hebrew, the city for `other_city` through `other_city_name(post, seen)` (#214, #296) or, with no `Listing`, none; the last publication relative, the number of publications); chips by reason with their counts (point 73) | Opens a post's detail. **No action on a post rejected by the model or before it** (point 66). A `"flagged"` or `"misclassified"` row links to its flag or its reports |
| **Pending** (`/admin/pending`) | The pending canonicals: the row, `classification_failures`, `last_classification_error` | **"Retry"** on a post with `classification_failures` above 0: the count back to 0 (Gate E, #139, #152); the error is left as it is. The row says "the next `classify_pending` run takes it" |
| **Flags by user** (`/admin/flags`) | The posts rejected `"flagged"` (active or archived), grouped by the user who flagged (username, never the `user_id`) and inside by **flag action**: the posts with the same `flagged_by` and `flagged_at`, which one "lied" flag on a card of several posts wrote (#300; point 63), with the note | **Restore** the whole action (each post by its own compare and set; a partial result is said, as 3.7's flag) or one post of it. Keeping the flag needs no write |
| **Reports by field** (`/admin/reports`) | The **open** reports grouped by field: under each `ReportableField` with its count, every post with an open report naming it (a report of three fields is under each of them, point 71). Per post: its reports (the reporter's username, the time, the fields, the note), and for each reported field the model's value, the correction in force if any, and the value users see. Two marks derived, never stored: **"the report is stored, the post is still on the list"** (3.4 point 3: an open report and a post that is not rejected by a user's reason) and **"the restore did not finish"** (point 62). Tabs: left out, restored (history, read-only) | Per post: **correct a field** (point 65), **restore**, **leave out**; for the first mark, **"remove the post from the list"** (point 72); for the second, **"finish the restore"** |
| **Corrections** (`/admin/corrections`) | In force: per post and field, the model's value → the corrected value, by whom and when, the report it answers. Removed (history): the same with the removal | **Remove** a correction in force (#256, #284) |
| **Archive** (`/admin/archive`) | The archived canonicals, as the rejected rows, with the reason they keep (Gate E). Empty until Phase 5 | None. An archived post that is flagged or reported is restored from the flags or reports page and stays archived (#283) |
| **Post detail** (`/admin/post/<id>`) | 3.7's opened post (`PostView`: the text as stored, every photo through the admin route, the publications and the repost log, the phones), and for the admin: the lifecycle (state, reason, who flagged and when, the note, the failures and the last error), the model's `Listing` field by field beside the seen one with the "corrected by hand" marks, every correction (in force and removed), every report, the city's ruling and its source (`correction`, `native_location`, `model`), and **what a restore would leave now** (point 76) | The actions of the page it was opened from |
| **Keys** (`/admin/keys`) | Every key: its label, created, used by (username) and when, cancelled when; unused first | **Issue** with a label: the key shown once, with a copy button, never again (#266); **cancel** an unused key (#243) |
| **Users** (`/admin/users`) | Every user: username, created, the key's label, admin, disabled since, must change the password, the failed sign-ins | **Reset the password** (the admin types a temporary password of 8 or more characters, #262; the user changes it at the next sign-in; every session ends, #263); **disable** (#265, #291) and **enable**. The admin's own row offers none of the three (R8; the admin's own password is changed from the preferences page or by `reset_admin_password` on the machine, #294) |

### (d) The endpoints (all admin only; reads are `GET`, writes `POST` with JSON)

| Endpoint | Answer |
|---|---|
| `GET /api/admin/summary` | The overview's counts |
| `POST /api/admin/posts` `{list, reason?, first}` | `list` one of `rejected`, `pending`, `archive`, `flags`; `reason` narrows `rejected`; the count, `order` and the first rows (`first` 0–96, default 48, as A) |
| `POST /api/admin/posts/by-id` `{list, reason?, ids}` | Those rows, in the order asked; `gone` for an id no longer in the list |
| `GET /api/admin/posts/{listing_id}` | The detail (c), read fresh, with the post's **`version`** (point 61) |
| `GET /api/admin/photos/{listing_id}/{file}` | The photo, by the rule of (b); 404 otherwise |
| `GET /api/admin/reports?status=open\|left_out\|restored` | The reports grouped by field, each with its post's row and `version` |
| `GET /api/admin/corrections?in_force=true\|false` | The corrections, each with its post's row |
| `GET /api/admin/keys`, `GET /api/admin/users` | The lists (no hash of any kind in them) |
| `POST /api/admin/retry/{listing_id}` `{version}` | The new row |
| `POST /api/admin/restore` `{posts: [{listing_id, version}]}` | Per post: `restored` (with the state it now has), `changed`, `not_restorable`; the flag page's partial result |
| `POST /api/admin/leave-out/{listing_id}` `{version}` | The reports left out |
| `POST /api/admin/apply-reports/{listing_id}` `{version}` | The post removed from the list (point 72) |
| `POST /api/admin/corrections` `{listing_id, field, corrected_value, report_id, version}` | The correction; the detail's new preview |
| `POST /api/admin/corrections/{correction_id}/remove` `{version}` | The removed correction |
| `POST /api/admin/keys` `{label}` | `{key_id, key}`, **once**, with `Cache-Control: no-store`; the key is never logged and never returned again (#266) |
| `POST /api/admin/keys/{key_id}/cancel` | The key |
| `POST /api/admin/users/{user_id}/password` `{temporary_password}` | The user (no hash) |
| `POST /api/admin/users/{user_id}/disable`, `…/enable` | The user |

Refusals as 3.7's: 409 `changed` (the post changed since the page read it), 409 `correction_in_force`, 409 `key_used`, 403
`admin_cannot_be_disabled`, 422 for a value that breaks Gate B or Gate C's rules (named, never echoing a password or a key).

### (e) Every write

**The post's `version` (point 61).** The detail page and every post row carry a `version`: SHA-256 of the canonical JSON of
what a post write depends on: the post's `PostLifecycle`, its reports (every status) and its corrections (in force and
removed). A post write sends it back. The server reads those records again; **a different `version` is 409 `changed`** and
nothing is written (the admin sees the new state and decides again); otherwise each record is written by compare and set
against the record just read (`expected=`, #260), so a write by anyone between that read and the write is still refused
(`StaleRecordError` → 409 `changed`). **No automatic retry for the admin's writes** (3.7's user writes retry once): the admin
decided on what the page showed. Keys and users are written through `accounts.actions` as built in 3.5 (they re-read and
compare and set inside, `STORE_ATTEMPTS`), since cancel, disable, enable and reset mean the same whatever changed meanwhile.

| Write | Records, in order | How #260 is kept | Undo |
|---|---|---|---|
| **Retry** (pending) | The lifecycle: `classification_failures` 0, nothing else (the error kept, Gate E) | Only when `state` is `"pending"` and the count is above 0; `save_lifecycle(…, expected=read)` | None needed: the next run may fail it again (+1) |
| **Restore** a post (flags or reports page; #251, #281–#283) | 1. Read the lifecycle, the `RawPost`, the `Listing`, the corrections in force (→ `seen_listing`), the reports. 2. **The reports first** (point 62): every `"open"` or `"left_out"` report of the post → `"restored"`, `resolved_by` the admin, `resolved_at` now (#278, #286), each by `save_report(…, expected=read)`. 3. **Then the lifecycle**, when `flagged_by` is set: `restored_lifecycle(read, post, seen)` (built in 3.6, pure: flag fields cleared; the state derived from the post as users see it by `model_reason`, the rule a classification uses; an archived post stays archived, its reason re-derived), by `save_lifecycle(…, expected=read)` | Both seams compare and set against step 1's read; a conflict at step 3 leaves the reports restored and the post rejected: **derived and shown as "the restore did not finish"** (a post rejected `"misclassified"` with no open or left-out report), and "finish the restore" runs it again (step 2 then finds nothing). No user can report the post meanwhile: it is rejected, so it has no card | Not undone by the admin: a restored post that is wrong again is flagged or reported again by a user (R4 allows a new report). A post restored to active joins the users' list at the next background recompute, seconds (#379) |
| **Leave out** (reports) | Every `"open"` report of the post → `"left_out"` (`resolved_by`, `resolved_at`), each by `save_report(…, expected=read)`; the lifecycle is not written: the post stays rejected `"misclassified"` and exempt from deletion (#255, #286) | `save_report` compare and set | **Restore later** (#286) |
| **Remove the post from the list** (a report stored, its post not removed; 3.4 point 3) | The lifecycle by `reported_lifecycle(read, first.reported_by, first.reported_at)` (3.7's pure function; `first` the earliest open report, #280, point 72) | Only when the post is still `"active"`; `save_lifecycle(…, expected=read)`. A post no longer active (rejected by a run, pending again, archived) cannot be removed: the admin restores or leaves the reports out | Restore |
| **Correct a field** (#256, #284; point 65) | `add_correction(FieldCorrection(…))`: `model_value` the stored `Listing`'s value of the field now (a `Marked` field with its state), `corrected_value` from the form, `corrected_by` the admin, `report_id` the report it answers. **Validated before it is written** (point 75): by `FieldCorrection`'s own validator (the Gate B type, #284) and by `seen_listing` over the stored `Listing` with the new correction applied, so the seen post is still a valid `Listing`. **The lifecycle is not written:** the post stays rejected until the admin restores it, and the detail's preview shows what restore would now leave (point 76) | `UserDataStore` refuses a second correction in force on the field (`CorrectionInForce` → 409). **Replacing one** is two writes, the old removed then the new added (point 74); a failure between them is said and leaves the field with no correction | **Remove** it |
| **Remove a correction** | `save_correction(record with removed_by, removed_at, expected=read)`; the record stays (#284); never back in force | Compare and set | Not undone: a new correction is added instead. **The post's state is not re-derived** (point 64) |
| **Issue a key** | `accounts.actions.issue_key` (`add_key`): the hash only (#266) | An insert | **Cancel** it while unused |
| **Cancel a key** | `accounts.actions.cancel_key` | `save_key` compare and set inside the action | Never: a cancelled key stays cancelled (#266) |
| **Reset a password** | `accounts.actions.reset_password`: the temporary hash, `must_change_password`, the failure count 0, then every session of the user ended (#262, #263) | `save_user` compare and set inside | Not undone (the old hash is gone); the user sets their own at the next sign-in |
| **Disable / enable** | `accounts.actions.disable_user` (the disable, then the sessions ended, #291) / `enable_user` | `save_user` compare and set inside | Each undoes the other; ended sessions stay ended (the user signs in again) |

**Every write leaves `RawPost` and `Listing` untouched** (invariant 14) and writes nothing per user on a post (invariant 12;
the flag fields Gate E has are cleared by a restore, never set by the admin). A correction and a removal move the store
generation counter (the `corrections` trigger, #316), so every user's cards follow at the next background recompute (#379).
Only a rejected or archived post is ever restored, so no admin write removes a card and the removal overlay (#379) is not
needed for the admin's writes.

### (f) What the admin can and cannot undo

| The admin can | The admin cannot |
|---|---|
| Restore a left-out post later (#286) | Re-open a restored or left-out report (a user reports again, R4) |
| Remove a correction; add another | Put a removed correction back in force (#284), or edit a stored `Listing` (#256) |
| Enable a disabled user; disable again | Disable themself (R8), delete a user (#265), change a username (#262) |
| Cancel an unused key | Un-cancel a key (#266), see a key again, cancel a used key (#243) |
| Reset any other user's password | Undo a reset |
| Retry a pending post | Start the classification from the site (the next `classify_pending`) |
| Restore a flagged or reported post | Flag a post as the admin from the admin's pages (a flag is a user's, on a card: the admin does it from the list like anyone); restore a post rejected by the model or before it (point 66); delete anything (invariant 3) |

### (g) The invariants and the copy

- **Invariant 14:** no admin write touches `raw_posts` or `listings` (a test compares the rows before and after every admin
  write). **Invariant 12:** nothing per user on a post. **Invariant 15:** the pages make no request off the site (3.7 (j)'s
  CSP and checks cover `/admin`). **Invariant 3:** nothing is deleted.
- **No secret leaves the server or a log:** the lists carry no password hash, key hash or session token hash; the issued key
  is in one answer only; a temporary password is never logged or echoed (`accounts/` already logs ids only).
- **Until 3.9 the site serves a dated copy (#331), and so do the admin's pages (point 70):** keys issued, accounts made with
  them, restores and corrections stay in the copy and are gone at the next `serve --copy`. DoD 2 and 5 are shown on the copy
  in 3.8 and made for real once the site serves the store itself (3.9).

### (h) The modules

- **`web/admin.py`** (new, wiring): the `/api/admin` routes of (d), each through the admin check.
- **`web/admin_writes.py`** (new, wiring, as `web/writes.py`): retry, restore, leave out, remove from the list, correct,
  remove a correction; the `version` (`post_version(lifecycle, reports, corrections) -> str`).
- **`web/admin_rows.py`** (new, pure, as `web/cards.py`): a row's and the detail's JSON; it reuses `cards.py`'s field
  formatting (`_listing`, `_marked`, the publications) rather than a second copy.
- **`dedup/stage_b.py`:** `KeyInputs.others` from the same pass (point 67); still reads only, writes nothing.
- **`web/grouping.py`:** `Snapshot.others`.
- **`postmodel/rejects.py`:** one pure function, `report_marks(lifecycle, reports) -> {"not_removed", "restore_unfinished"}`
  (the two derived marks of (c)), beside the Gate E rules it reads.
- **`accounts/actions.py`:** `require_admin(store, token, now) -> User`, today's private `_require_admin` made public, the one
  admin check, called by every admin read (point 68); every action keeps calling it.
- **Front end:** `src/screens/admin/` (`Admin.tsx` the layout and its tabs, `PostRows.tsx`, `AdminPost.tsx`, `Reports.tsx`,
  `Corrections.tsx`, `Keys.tsx`, `Users.tsx`), `src/admin/api.ts`, `src/admin/values.tsx` (the correction's value form by
  Gate B type: a `Marked` field's state and value; yes / no; a number or several amounts for the price; "immediate" or a date;
  a number or "included"; the enums in Hebrew; the area picker of 3.7 for `areas`; lines of text for `streets`; a city or none
  for `other_city`; a phone of the post with a name for `phone_names`), `src/styles/admin.css`; `route.ts` and `Header.tsx`
  gain the admin's paths and menu item. 3.7's tokens, `PostView` and `paging.ts` reused, built with `frontend-design` as 3.7
  (#257).
- `CLAUDE.md`'s `web/` paragraph names the new modules when built.

### (i) Tests (offline; `TestClient` in process; temporary stores only)

1. **Access:** every `/api/admin` route: a guest 401, a user 403, the admin with a password change due 403, the admin 200;
   every write without JSON 415, with a foreign `Origin` 403.
2. **Lists:** canonicals only (a duplicate never a row, #75 B); each state in its list and in no other; the reason filter and
   its counts; paging equal to the whole list; `gone`; "loading" before the first snapshot; `others` read in the same pass
   as the members (a counter on `query`).
3. **The city:** an other-city row by `native_location`, by the model, and by a correction in force (#214, #296).
4. **Photos:** a rejected post's stored file served to the admin and 404 to anyone else; `..` and another post's file
   refused.
5. **Retry:** pending with failures → 0 and the error kept; refused for 0 failures and for a post no longer pending; a stale
   `version` 409.
6. **Restore, for each case of #251, #281–#283:** a flagged active post → active; a reported post whose `post_nature` was
   corrected to `"for_sale"` → rejected `for_sale`; an other-city post by `native_location` → rejected `other_city`; an archived
   post stays archived, its reason re-derived; every open and left-out report → `"restored"` with the admin and the time; a
   flag action of two posts restores both, and a conflict on one gives the partial answer; **the unfinished restore** (the
   lifecycle write made to fail after the reports): the mark derived, "finish" completes it; a stale `version` writes nothing.
7. **Leave out, then restore later (#286);** the post stays rejected `"misclassified"` while left out.
8. **Remove from the list:** an open report on an active post → rejected `"misclassified"`, `flagged_by` the first reporter
   (#280); refused for a post no longer active.
9. **Corrections:** each Gate B type through the form's JSON; a value that breaks Gate B 422 and nothing written; the
   `model_value` the stored one; a second in force 409; replace (remove, add); removal keeps the record; the counter moves and
   the users' cards follow at the recompute (#287: a corrected field that ties or unties two posts).
10. **Keys and users:** the key in one answer with `no-store`, then only its label in the list; cancel; a used key refused;
    reset ends the sessions and the user reaches only the password change; disable ends the sessions; enable; the admin's own
    row refused (R8).
11. **Invariants:** `raw_posts` and `listings` rows byte-identical after every admin write (14); no per-user field on a post
    (12); no hash, token, key or password in any answer or log record (a log capture over every admin route); the socket
    guard (15).
12. **Front end (Vitest):** the value form's JSON per type; the per-field grouping of the reports; the two derived marks.

### (j) The build in steps, each ending in something Ron can look at

1. **The admin's read API:** `require_admin`, `KeyInputs.others`, `Snapshot.others`, `web/admin_rows.py`, the read routes of
   (d), the admin photos; tests 1–4. **Ron opens the JSON** on a scratch copy.
2. **The read pages:** overview, rejected, pending, archive, flags, reports, corrections, keys, users, the post detail; checked
   in Chrome at 1440 × 900 and 390 × 844 (point 69), Lighthouse accessibility. **Ron looks at the lists** with today's 87
   rejected posts.
3. **Keys and users:** issue, cancel, reset, disable, enable; tests 10. **Ron issues a key on the copy and signs a second
   account up with it** (DoD 2 on the copy).
4. **The post writes:** retry, restore (flags and reports), leave out, remove from the list, the `version`; tests 5–8, 11.
   **Ron flags and reports on the copy, then restores and leaves out** (DoD 5 on the copy).
5. **Corrections:** the value form, correct, replace, remove, the restore's preview; tests 9, 12. **Ron corrects a field and
   restores.**
6. **The check:** the whole DoD 5 walk on a fresh scratch copy (a flag → restore; a report → correct → restore; a report →
   leave out → restore later), the two sizes again, the `design` plugin's critique and accessibility review. **Ron reviews**
   the pages; 3.8 is complete when he says.

### (k) What I could not verify

- The size and memory of `others` at 40 days: S2 was deleted (#387); from its counts (8,512 posts, 4,448 members) the
  admin's canonicals would be a few thousand rows, measured at step 1 on today's store only unless Ron wants a 40-day store
  again.
- How often an admin write meets another writer: there is one admin and the jobs run by hand (#140); the `version` and
  compare and set refuse rather than lose a change, whatever the rate.
- That a correction of `phone_names`, `streets` or `areas` through the form is comfortable on a phone: checked at step 5.

### Points for Ron (3.8)

- 60. **The scope and the six build steps of (j)**, with the keys and users first among the writes so a second account can be
  made early. Recommended.
- 61. **The admin's post writes compare against what the page showed:** a `version` over the lifecycle, the reports and the
  corrections; a difference is 409 "changed" with no automatic retry; each record still by compare and set (#260).
  Recommended. Or: re-read at the write and retry once, as 3.7's user writes do.
- 62. **The restore's order across the two seams:** the reports first, then the lifecycle; an unfinished restore is derived
  (rejected `"misclassified"`, no open or left-out report), shown, and finished by running the restore again. Recommended. Or:
  the lifecycle first (an active post with open reports, which breaks #279's "rejected while any report is open" until
  finished).
- 63. **The flags page groups by flag action** (the posts with the same `flagged_by` and `flagged_at`, one "lied" flag on one
  card, #300), restored together or one by one. Recommended. Or: one row per post.
- 64. **Removing a correction changes only what users see; the post's state is not re-derived.** So a post restored to active
  through a correction of `post_nature` or `other_city` stays active when that correction is removed, though users then see,
  for example, "seeking"; the page warns before such a removal. Recommended for 3.8, since re-deriving would be a new
  lifecycle rule (Gate E). Or: a removal re-derives the state of a post that is not flagged or reported (a Gate E amendment,
  approved first).
- 65. **A correction is made from a report only** (the reports page and its post's detail), as §11 places it. Recommended. Or:
  from any post in the admin's lists (which, with 64, changes nothing in a post's state either).
- 66. **No action on a post rejected by the model or before it** (no "un-reject"): the rejected list shows them; a wrong one
  waits for a reclassify (`BACKLOG.md` item 4) or a rule. Recommended. Or: a "restore" for any rejected post through a
  correction and a re-derivation (needs 64's other option).
- 67. **The admin's post lists ride the grouping** (`KeyInputs.others`, `Snapshot.others`: one read of the store, one counter,
  the background recompute); seconds behind another process's write, the admin's own writes shown at once, every action read
  fresh. Recommended. Or: read the store on every list request (about 0.4 s today, about 13 s at 40 days by 3.6's estimate).
- 68. **`accounts.actions.require_admin` made public**, the one admin check for the admin's reads. Recommended.
- 69. **The admin's pages checked at 1440 × 900 and 390 × 844** (usable on the phone, not the six sizes), with 3.7's tokens and
  components. Recommended. Or: the six sizes; or desktop only.
- 70. **Until 3.9 the admin's writes land in the dated copy (#331)**: keys, accounts, restores and corrections made there are
  lost at the next `serve --copy`; DoD 2 and 5 are shown on the copy now and made for real after 3.9. Recommended (as #331).
  Or: plan 3.9 before building 3.8's writes.
- 71. **Reports grouped by field with a report under each field it names** (a three-field report counted under each), the
  post's actions the same from every group; left-out and restored reports in history tabs. Recommended.
- 72. **"Remove the post from the list"** for a report stored while its post stayed (3.4 point 3): `flagged_by` and
  `flagged_at` from the earliest open report (#280). Recommended.
- 73. **Rows ordered by the newest last publication;** the rejected list filterable by reason with counts. Recommended.
- 74. **Replacing a correction in force** is the old removed, then the new added (two writes; a failure between them is said,
  and leaves the field uncorrected). Recommended. Or: no replace; the admin removes, then adds.
- 75. **A correction is checked against the whole post before it is written** (`seen_listing` over the stored `Listing` with it
  applied must be a valid `Listing`), 422 otherwise. Recommended.
- 76. **The post's detail shows what a restore would leave now** (`restored_lifecycle` over the seen post, no write), so the
  admin sees the effect of a correction before restoring. Recommended.

**Decided by Ron, 2026-10-15 (round 20): the plan and points 60–76 as recommended (#389–#406); point 66's other option
recorded under `BACKLOG.md` "Future".**

### Round 20 (2026-10-15): build steps 1, 2 and 3 built

**Built.**
- **Step 1, the read API.** `accounts.actions.require_admin` (public, #398). `dedup/stage_b.py`: `OtherPost` and
  `KeyInputs.others`, read in the same pass as the members (#397). `web/grouping.py`: `Snapshot.others` and
  `Snapshot.duplicates`. `postmodel/rejects.report_marks` (the two derived marks). `web/cards.py`: `listing_json`,
  `post_videos` and `whatsapp_link` made public for reuse. `web/admin_rows.py` (pure) and `web/admin.py`: `GET summary`,
  `POST posts`, `POST posts/by-id`, `GET posts/{id}` (fresh, with the restore's preview, #406), `GET photos/{id}/{file}`,
  `GET reports?status=`, `GET corrections?in_force=`, `GET keys`, `GET users`.
- **Step 2, the read pages.** `frontend/src/screens/admin/` (`Admin.tsx`: the rail with counts and the overview;
  `PostRows.tsx`: rejected with the reason chips and counts, pending, archive, flags by flag action; `AdminPost.tsx`: the
  detail; `Reports.tsx`: reports by field with the marks, corrections; `Accounts.tsx`; `ui.tsx`), `src/admin/` (`types.ts`,
  `api.ts`, `words.ts`), `src/styles/admin.css`; `route.ts` (`/admin`, `/admin/<page>`, `/admin/post/<id>`), `Header.tsx`
  ("ניהול" for the admin), `App.tsx` (the admin's route; no card list loaded there), `api.ts` (`call` exported), `paging.ts`
  (generic, so the rows page as the cards do). Built with `frontend-design`: 3.7's tokens; one accent, the reason's chip
  coloured by who rejected the post (grey before the model, amber the model, red a user).
- **Step 3, keys and users.** `POST keys` (the key in that answer only, `Cache-Control: no-store`), `POST keys/{id}/cancel`,
  `POST users/{username}/password`, `…/disable`, `…/enable`, through 3.5's actions; the pages issue a key with its label and
  show it once with a copy button, cancel an unused key, reset, disable and enable.
- **Tests:** `tests/test_web_admin.py` (new, 45: groups 1–4, the detail, the reports and corrections as read, the marks,
  10, 11); `frontend/src/admin/words.test.ts` (new, 5).

**Checked in Chrome** over a scratch copy of the store (an online backup from a `mode=ro` connection into the scratchpad;
the store's SHA-256 `5df9bc9a…a77ac` before and after; the copy's admin given a scratch password): at 1440 × 900 the
overview (87 rejected by reason, 1 pending with its failure), the rejected list (chips, rows, Ramat Gan's city), a post's
detail (the city "לפי המודל", the 22 fields), a code issued and shown once, a second account (`friend20`) signed up with it
in a separate browser context and refused the admin's pages, then disabled (its session ended) and enabled; at 390 × 844
every admin page with no sideways scroll (scroll width 390). **Lighthouse accessibility 100** on the rejected list, the
detail and the codes page (desktop) and on the rejected list, the detail and the users page (mobile); best practices 100.
No console message; every request to the site itself.

**Deviations (for Ron):**
1. **A user is named by username in the addresses** (`/api/admin/users/{username}/…`), not by `user_id`: Gate C says
   `user_id` is never shown. Usernames are unique and never change (#262).
2. **The admin's photo route reads the post's record fresh** and serves any stored post's own photo, not only one the
   snapshot holds (stricter freshness, the same no-path rule).
3. **The admin's own row is refused a reset by the route** (403 `admin_row`); R8 already refuses its disable.
4. **The post's detail reuses `Carousel` and the formatters, not `PostView`** (a dialog that fetches `/api/posts`, which
   answers only for a current card).
5. **The pages say "קוד הזמנה"**, the sign-up form's own word, not "מפתח" (one name through the flow).
6. **`corrections?in_force=false` returns the removed ones only** (the history tab); `UserDataStore` returns all.
7. The `version` of point 61 comes with the post writes, at step 4.

**Not verified:** a real phone; the admin's lists at 40 days (S2 deleted, #387): `others` costs one more `get_listing` per
non-member canonical in the grouping's read.

### Round 21 (2026-10-15): build steps 4, 5 and 6

**Built.**
- **Step 4, the post writes.** `web/admin_writes.py` (wiring, as `writes.py`): `post_version` (SHA-256 of the post's
  lifecycle, reports and corrections, #391), `read_state`, `retry`, `restore` and `restore_many` (the reports first, then
  `restored_lifecycle`, #392), `leave_out`, `apply_reports` (#402); `Changed` and `Refused`. `web/admin.py`: every row and the
  detail carry `version`; `POST retry/{id}`, `POST restore` (a result per post), `POST leave-out/{id}`, `POST
  apply-reports/{id}` (and the overlay, #379); each write answers the post's fresh detail, 409 `changed` or the reason, 422
  for a value. The pages: the detail's actions ("שחזור", "השלמת השחזור", "השארה בחוץ", "הסרה מהרשימה", "ניסיון סיווג
  חוזר", each with a `confirm` where it cannot be undone) and the flags page's "שחזור" per flag action (#393).
- **Step 5, corrections.** `admin_writes.correct` (from a report, #395; `model_value` the stored value; checked by its Gate
  B type and as the whole post, #405; one in force replaced, the old removed first, #404) and `remove_correction` (#394);
  `POST corrections`, `POST corrections/{id}/remove`. The value form: `frontend/src/admin/values.ts` (each field's Gate B
  shape, both directions) and `screens/admin/ValueForm.tsx` (the state of a Marked field, then the value: radios, a number,
  amounts, a date or "immediate", a fee or "included", 3.7's area picker, streets one per line, a city, a name per phone);
  "תיקון" on every row of the detail's field table, "הסרה" on a correction in force (with #394's warning on `post_nature`
  or `other_city` of an active post); the restore's preview updates after a correction (#406).
- **Tests:** `tests/test_web_admin_writes.py` (new, 50: retry, the stale `version`, the flag action whole and partial, the
  corrected nature, other city, archived, nothing to restore, the unfinished restore finished, leave out then restore
  later, a report applied with the first reporter, every field corrected by its type (24 values), five values refused 422
  with nothing written, no report, replace and remove, the users' cards follow, invariants 12 and 14, every write the
  admin's only); `frontend/src/admin/values.test.ts` (new, 28).

**Step 6, checked on a fresh scratch copy** (an online backup from a `mode=ro` connection; the store's SHA-256
`5df9bc9a…a77ac` before and after; the copy's admin given a scratch password; every write in the copy only), through the pages
in two browser contexts, the admin's and a friend's (`friend21`, signed up with a code issued on the codes page):
1. **A flag → restore:** the friend flagged a card from its "דיווח" menu (it left the list at once); the admin's flags page
   showed `friend21`'s flag action; "שחזור" restored it; the post was on the friend's list again at the next request.
2. **A report → correct → restore:** the friend reported "מספר חדרים" with a note; the reports page grouped it under the
   field; on the detail the admin corrected rooms from "לא צוין" to 2.5 ("תוקן ביד", the model's value kept beside), the
   preview read "פעילה", "שחזור" made it active with its report "שוחזר"; the friend's opened post showed rooms 2.5 and the
   field corrected.
3. **A report → leave out → restore later:** the friend reported the price; "השארה בחוץ" left the report out and the post
   rejected; the reports page's left-out tab held it; "שחזור" from there made it active.
At the end: two reports restored and kept, the correction in force, nothing open, all three posts back (#255).
**Lighthouse accessibility 100** on the detail page (desktop, and with the 79-box area form open), the detail with the price
form open, the reports and corrections pages (mobile), the reports and corrections pages (desktop); best practices 100.
**At 390 × 844** every admin page, four post details included, has no sideways scroll.

**Fixed during the check (bugs, not design):** (1) a post's text with a long unbroken run (a link) widened the phone's page to
699 px: the text panel wraps it (`overflow-wrap: anywhere`); round 20's check had a post with no such text; (2) after a
restore the detail re-mounted and the notice was lost: the detail is read again in place, so "המודעה שוחזרה…" stays.

**The design plugin's critique and accessibility review were not run:** their skills are not installed in this session (the
skill list has no `design:` skills); not judged by eye instead. **The accessibility review was made with `ecc:accessibility`**
(WCAG 2.2 AA), with measurements in Chrome; its findings are points 78–83, nothing changed.

**Deviations (for Ron):**
1. **A correction may be made on any field of a post that has an open or left-out report**, the report being the earliest
   such one, not only on the fields the report named (#395 read as "made from a report").
2. **A restore of a post whose report never removed it** (no flag on its record) marks the reports restored and leaves the
   record as it is.
3. **"השארה בחוץ" is offered only while the post is off the list**; for a report whose post stayed, "הסרה מהרשימה" comes
   first.
4. **A row's `version` uses the snapshot's record** (seconds behind another process's write): a stale row answers 409
   "changed" and the page says so.

**Not verified:** a real phone; screen readers (only the accessibility tree and Lighthouse); the laptop slept during the
test run (1941 passed in 3 h 34 min of wall time; the scratch server died with it and was started again on the same copy).

**New points for Ron (3.8):**
- 77. **The design critique was not run** (the `design` plugin's skills are absent here). Options: enable the plugin and run
  the critique and its accessibility review at a later round (recommended before 3.8 is closed); or take `ecc:accessibility`'s
  review below as enough.
- 78. **Focus when the value form opens** (WCAG 2.4.3): "תיקון" on a low row opens the form up to 1,164 px above, off screen,
  focus left on the row's button. Recommended: move the focus to the form's heading (scrolled into view) and back to the row's
  button on cancel or save.
- 79. **The notices are inserted already filled** (`role="status"`/`"alert"` appear with their text, WCAG 4.1.3): some screen
  readers announce only changes inside a region already present. Recommended: keep one empty live region on the page and set
  its text. 3.7's own notice bar is not changed by this point.
- 80. **The error of an invalid correction is English and technical**, with a stray "bar:" (WCAG 3.3.3): "הערך לא תקין: bar:
  Value error, rooms is a positive multiple of 0.5". Recommended: the server names the rule in Hebrew for Gate B's known
  rules (half rooms, areas 1–71, a written price needs an amount above 0, and so on), and drops the "bar:" prefix.
- 81. **Focus after a write that removes the focused button** (restore, leave out): the focus falls to the page. Recommended:
  move it to the notice that says what happened.
- 82. **The flags page's "שחזור" buttons all share one name** when several flag actions are listed. Recommended: name each
  by its user and count ("שחזור הסימון של friend21, 2 פרסומים").
- 83. **"המודעה בפייסבוק" on the detail is 21 px tall** (WCAG 2.5.8 asks 24, met here only by its spacing). Recommended: 24 px.

**Decided by Ron, 2026-10-15 (round 22):** 77, no design critique for 3.8 (#407); 78–83 as recommended (#408–#413; 82 in
Ron's words, "named by its post"); round 21's deviation 1 accepted (#414).

### Round 22 (2026-10-15): points 78–83 built

- **78 (#408):** `ValueForm.tsx` scrolls itself into view and focuses its heading when it opens; cancel and save return the
  focus to the row's "תיקון" button (`AdminPost.tsx`, `focusAfter`).
- **79 (#409):** `screens/admin/ui.tsx` `Announce`: a `role="status"` and a `role="alert"` always in the page, empty until a
  message fills one; used by the detail, the flags page and the users page; the value form's error region is always present
  too. (The codes page's error region already was.)
- **80 (#410):** `web/admin_writes.py` `Invalid` and `invalid_words`: each Gate B rule a correction can break
  (`contracts/listing.py`'s messages) named in plain Hebrew; any other refusal "הערך לא מתאים לשדה …"; no "bar:", no English.
  The page shows the sentence as it comes.
- **81 (#411):** after any write on the detail page except a correction (restore, leave out, remove from the list, retry, a
  correction's removal) and after a restore on the flags page, the focus moves to the message.
- **82 (#412):** `admin/words.ts` `restoreLabel`: the visible "שחזור" (or "שחזור N הפרסומים") and an accessible name that
  starts with it and adds the post's first words, cut at a whole word ("שחזור: להשכרה דירת פנטהאוז 4 חדרים בשכונת נווה…").
- **83 (#413):** `.apost-fb` at least 24 px tall (measured 25).
- **Found while measuring, fixed (a bug, not design):** the flags page went from h1 to h3 (Lighthouse "heading order", 98):
  each flag action's heading is an h2. Round 20 and 21 audited the flags page empty.
- **Tests:** `tests/test_web_admin_writes.py`: the invalid-value test now pins the Hebrew sentence for each rule (8 cases, was
  5) and that no "bar", "Value error" or field name in English appears; `frontend/src/admin/words.test.ts` +1 (the restore
  label).

**Checked in Chrome** on a fresh scratch copy (an online backup from a `mode=ro` connection; the store's SHA-256 `5df9bc9a…a77ac`
before and after), with a friend's report and flags made through the site's own endpoints: the two live regions present and
empty on load; the form opened from the lowest row with the focus on its heading, in view; cancel and save back on the row's
button; "3.3" rooms answered "מספר החדרים הוא מספר חיובי בקפיצות של חצי, למשל 2 או 2.5."; restore, leave out and the flags
page's restore each left the focus on the message with its text; the Facebook link 25 px. **Lighthouse accessibility 100**:
the detail with the form open (desktop, mobile), the flags page with a flag action (desktop, mobile; 98 before the heading
fix), the users and reports pages (mobile). **At 390 × 844** no admin page scrolls sideways, the form open included.

## 3.9 Serving on the tailnet — plan to be written

Docker Compose on Ron's laptop (`BASELINE.md` §3, §12: phases 1–4 run there), the site published with Tailscale Serve
(HTTPS, tailnet only; `ASSUMPTIONS.md` I4 verified). The collection and classification commands stay manual (#140,
#61). The framework and serving are decided (#258). **Needs from Ron:** the plan's approval.

## 3.10 The measured working day (DoD 4, I3) — approved (#225, #228)

Once a dashboard exists: one real working day of collection and classification, each paid run under a cap Ron sets;
calls, tokens and cost from the usage metadata, then the OpenAI bill. **Needs from Ron:** the go for each paid run, and
the bill.

---

## 3. Items this phase must close

| Item | Source | Task |
|---|---|---|
| DoD 4, the measured working day, and `ASSUMPTIONS.md` I3 (the same measurement) | #225, #228 | 3.10 |
| The same-listing grouping derived by the Gate D key; its first check on the 4 known pairs | #230–#232, #229 | 3.6 |
| The card's city for an other-city post, derived (`other_city_name`) | #214 | 3.6, 3.7, 3.8 |
| Viewed posts per user | #62, #253 | 3.4, 3.6, 3.7 |
| The admin lists show canonicals only | #75 B | 3.8 |
| The card's display rules: the main time, the repost log's earliest `posted_at`, rooms and size on a room post, the entry date's year, the video link from a repost | #122, #75 A, #120, #121, #115, #70 | 3.7 |
| The "wrong classification" report, its schema and the corrections record | #173, #254–#256 | 3.1, 3.4, 3.7, 3.8 |
| The per-user YAML removed | #47 | 3.4 |
| The dashboard framework; the journal mode; concurrent writes to `PostLifecycle` | `BACKLOG.md`, "Open technical choices"; #65 | Decided (#258–#260); built in 3.4, 3.7, 3.9 |
| **Notes from the dedup B plan worth keeping:** **alerts (Phase 4) must not fire for a post the key ties to an earlier one**; the key reads only active canonical posts that have a `Listing`, so a post waiting for its classification is not tied; the agent-number threshold of 4 is re-measured on a week of data | #230–#232; `PHASE_2.md` 2.10 | Recorded; 3.6 builds the derivation that Phase 4 reads |
| `gate_d_pairs` runs again on a larger store, to record the rate with its window | #226, point 5 | Free; after a week of runs. Not a DoD item |
| The phone as a candidate signal for dedup B: dedup A's layer 3 still produces nothing, and nothing writes a phone match onto a post (#75 C; the key settles the rest, #230–#232) | #75 C | **For Ron:** nothing is proposed; left as it is unless Ron wants it |

Settled on 2026-10-10 and so not open: #70 under dedup B (#252); which size a room search filters on (#247); the area
grouping (#248, #249, #261); the orange on the area (#250, #275); restore after a reclassify (#251, as amended by #281
and #282).

---

## 4. The four known pairs (first check of the derived grouping)

`54ecb1d0…` / `00f17259…`, `7253eefa…` / `40f7f193…`, `e81273e6…` / `8ae80944…`, `9136a715…` / `9a6252c1…`
(read-only, 2026-10-08, 139 active canonicals; Ron judged all four `same_listing`, #229). No post is in two pairs, and
none of the eight has an exact-hash duplicate. Each must show as one card; the store will have changed by then, so the
check reads the store as it is and reports any difference.

**Checked at 3.6's build (2026-10-11, round 6), read-only, with the built `dedup/stage_b.py`:** the four pairs tie and
nothing else does; 135 cards, 4 of them of two posts, each showing its earlier post (`54ecb1d0…`, `7253eefa…`,
`9136a715…`, `e81273e6…`). The store's SHA-256 was `04cefd60…` before and after (`SESSION_LOG.md`, 2026-10-11, round 6).

---

## 5. Technical choices — APPROVED by Ron, 2026-10-10 (#258, #259, #260)

Each choice below was approved as recommended: §5.1 option A, §5.2 the rollback journal with an explicit busy timeout,
§5.3 option 1. The comparison is kept as the record of what was weighed. No library is installed yet; versions and
contract details are read under the `external-contract-verification` skill in each task's plan (3.5 for `argon2-cffi`).

### 5.1 The dashboard framework, and how the site is served

**What weighs:** Docker Compose on the laptop and later the home server (`BASELINE.md` §3); Tailscale Serve in front
(HTTPS, tailnet only); the Telegram Mini App later adapts the same site (`BASELINE.md` §10, `ASSUMPTIONS.md` T5); a
polished UI built with Ron's design skills (#257); Hebrew, right to left; the store and all the logic are Python
(`policy/`, `postmodel/`, `store/`), so the site's server is Python or calls Python.

**Ron's design plugins** (the set he used for event-seeker): `frontend-design@anthropic-plugin-directory` (visual
direction, typography, the UI's code), `design@synced` (critique, design system, UX copy, accessibility review,
handoff), and `chrome-devtools` (inside `ecc@ecc`: drives a real Chrome on a page — screenshots, console, network,
Lighthouse, a mobile viewport). `superpowers` is disabled and not relied on. *How well each works with each option is my
reading of what the plugins do; none was used in this round.*

| | A. React 19 + TypeScript, Vite; hand-written CSS; `@fontsource` Hebrew fonts; FastAPI + uvicorn serves the API and the static build; one image, two-stage build *(Ron's event-seeker stack)* | B. FastAPI + Jinja2 templates rendered on the server, htmx for partial updates; hand-written CSS; one stage, no Node | C. A Python UI framework (NiceGUI, Streamlit or similar) | D. A Node full-stack framework (SvelteKit, Next.js) beside a Python API |
|---|---|---|---|---|
| Fits the store and the logic in Python | Yes: the API is Python and calls `policy/` directly | Yes: all Python | Yes | No: two servers, the Node one calling the Python one for every read |
| One image, one process | One image (Node only at build), one process | One image, one process | One image, one process | Two runtimes; two services or one image with two processes |
| A polished, hand-designed UI | Full control; the stack Ron's UI was built with | Full control of markup and CSS; rich interactions (the profile editor, "copy from the other option", the grouped area filter) are more work as partial page swaps | Poor: the framework owns markup and styling | Full control |
| Hebrew, right to left; fonts | CSS `dir="rtl"`; fonts bundled by `@fontsource`, so no font request leaves the device | CSS; fonts self-hosted by hand | Limited by the framework | CSS; fonts bundled |
| The Telegram Mini App later | A single-page app adapts to a webview; the sign-in from Telegram is checked by the API (Phase 4, to verify) | Works in a webview; less client code to adapt | Poor fit | Works |
| Sign-in | A same-origin session cookie: the API and the pages are one origin, so no CORS | The same | The framework's own, or custom | Cross-service |
| `frontend-design` | **Good:** components and hand CSS are its natural output | **Fair to good:** markup and CSS carry over; components must be rewritten as templates | **Poor:** little room for its direction | **Good** |
| `design@synced` | **Good:** works from screens and specs, whatever the stack | **Good** | **Fair:** critique works, applying it is hard | **Good** |
| `chrome-devtools` | **Good:** a running page in Chrome; Vite's dev server reloads on save, for a quick look-and-fix loop; a mobile viewport for the Mini App | **Good:** any served page; no reload on save unless added | **Fair** | **Good** |
| New tooling in this repo | Node and npm for the build and the dev server (on Ron's laptop, checked 2026-10-10: `node` v24.11.1, `npm` 11.6.2; reused, `node_modules` never copied between projects, #258) | None beyond Python packages | Python packages | Node, and a second server |

**Recommendation: A — approved (#258)**, Ron's event-seeker stack. Ron's design work and these three plugins have already produced a UI
he is happy with on this stack; it keeps one image and one Python process that calls `policy/` directly; and a
single-page app is the closest to what the Mini App needs. Its cost is a Node build stage and Node on the laptop for UI
work. **B** is the choice if Ron prefers no Node at all, at the price of more work on the interactive parts. C and D are
not recommended.

**How it would be served (with A or B):** one Docker image; the site's container runs uvicorn on a port bound to
`127.0.0.1` on the host; **Tailscale Serve** on the host publishes that port over HTTPS to the tailnet only
(`ASSUMPTIONS.md` I4). The API and the pages share one origin. The collection and classification commands run from the
same image as one-off commands (the scheduler is Phase 5's). The site's code is wiring, like `pipeline.py`: the logic
stays in `policy/` and `postmodel/`; its module and its libraries are designed in 3.7's plan (`CLAUDE.md`).

### 5.2 SQLite journal mode (#65)

The site reads all day while a run, `classify_pending` or the site itself writes. Today: the default rollback journal,
one connection per operation, every write a short `BEGIN IMMEDIATE` transaction (`store/sqlite.py`), and a reader opened
`read_only` with `mode=ro`.

| | Keep the rollback journal, with an explicit busy timeout | WAL |
|---|---|---|
| A page read during a write | Waits while the writer commits; each write is one short transaction | Never waits for a writer |
| A write during a long read (a full list) | Waits until the read ends: reads must stay short | Not blocked |
| The dated backup (`jobs/common.backup_store`) | Unchanged: it copies the one file | **Must change:** it copies the main file only (`shutil.copy2`), which can miss committed transactions still in the `-wal` file; SQLite's online backup is the replacement |
| `read_only` opening (`mode=ro`) | Unchanged | To verify on sqlite.org before relying on it: a read-only connection to a WAL database has conditions on the `-shm` file |
| Files | One | Three (`-wal`, `-shm`); the mode is stored in the file |
| The laptop (Windows, Docker) and the server (Linux) | Works on both | SQLite documents WAL for a local filesystem; a Windows folder mounted into a Linux container is to be checked |

**Recommendation: keep the rollback journal in Phase 3 — approved (#259)**, set an explicit busy timeout on every
connection, and keep each page's read in one short transaction; measure on the real store during 3.10. WAL is
reconsidered in Phase 5 if waits are seen on the measured day, together with the backup change. *Why (the proposal's):*
it changes nothing that works today (the backup, `read_only`), and the writes are already short. Python 3.12's default
busy timeout is 5.0 seconds (read 2026-10-10); 10 seconds is proposed in 3.4 (e).

### 5.3 Concurrent writes to `PostLifecycle`

`save_lifecycle` is a whole-record replace, last write wins (#65; a contract test pins it). Until now no two writers ran
at once (#140, #220). **The site changes that:** it runs all day and writes `PostLifecycle` when a user flags or reports
a post and when the admin restores or retries one, while `run_once` or `classify_pending` may be writing the same
record (a repost moves `last_published_at`; a classification sets the state). A run that read the record before the
user's flag and writes after it erases the flag; the other order erases the run's change. **#140's "never at the same
time" cannot hold for the site.**

| | Option | Cost |
|---|---|---|
| 1 | **Compare and set** for every writer: `save_lifecycle(record, expected)` writes only if the stored document is still the one read, checked inside the same `BEGIN IMMEDIATE` transaction; otherwise it raises. The site tells the user the post changed and reloads; a run re-reads the record and applies its change once more | A Repository contract change (one parameter, both stores, the contract test replaced). The same "re-read before writing, write nothing if it changed" that `rederive_rejections` and `apply_reclassify` already do (#214, #220) |
| 2 | **Field-level writes** inside one transaction (for example "set the flag", "set the state"), reading and writing in the same transaction | Several new Repository methods; the run's code must move its read-modify-write into the store too, or it still overwrites |
| 3 | **The site waits for runs:** user actions refused while a run is going | A run marker that does not exist yet (Phase 5); flags refused for up to 30 minutes |
| 4 | **User actions never write `PostLifecycle`:** flags and reports live only in their own records, and the visible state is derived (a post with an open flag or report shows as rejected) | Rewrites Gate E's flag fields and the E-1 to E-3 amendments; reclassify's flagged-post rule (#217 (5)) reads `flagged_by` |

**Recommendation: option 1 — approved (#260)**, for every writer of `PostLifecycle`. It keeps Gate E's shape and the
amendments as drafted, uses a pattern the code already has, and fails loudly instead of losing a change. #140's "never at
the same time" no longer covers the site; it still holds among the job commands (`CLAUDE.md` updated). How each caller
uses it: 3.4 (d).

---

## 6. Area grouping — APPROVED by Ron, 2026-10-10 (#261)

**No official grouping that maps to `ms_shchuna` was found** (`RESEARCH.md` §16): the municipality's quarter layers
(510, 847, 512) carry codes and no names, and layer 511 does not point at them. **The grouping below is the assistant's**,
by region, from where the areas lie; it is not a municipal division. It keeps together the entries of the colloquial
names already given to the model (`SCHEMA.md`, "Colloquial names": the Old North 30–31, the New North 33–35, Jaffa
42–49, Kfar Shalem 68–69). Display only: what is stored is the municipal numbers (#83, #248). Ron approved it as proposed,
with the four entries round 1 left open placed in regular groups (1 and 3, 29, 40).

| Group (Hebrew heading) | `ms_shchuna` |
|---|---|
| North of the Yarkon, west (עבר הירקון – מערב) | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17, 18 |
| North of the Yarkon, east (עבר הירקון – מזרח) | 19, 20, 21, 22, 23, 24, 25, 26, 27 |
| The North (הצפון הישן והחדש) | 29, 30, 31, 32, 33, 34, 35, 36 |
| The city centre (מרכז העיר) | 37, 38, 39, 40, 41 |
| Jaffa (יפו) | 42, 43, 44, 45, 46, 47, 48, 49 |
| The south (דרום העיר) | 50, 52, 53, 54, 56 |
| The east (מזרח העיר) | 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71 |
| **Non-residential, collapsed, at the bottom (#249)** | 11, 12, 13, 28, 51, 55, 66 |

All 71 appear once: 64 in the seven groups, 7 in the non-residential group. *The reviewer's reason for the four, approved
by Ron:* when in doubt, a regular group, so "select all in group" does not miss a post. The non-residential seven were
proposed from their names alone (a university, a fairground, a park, a business park, an employment zone); no land-use
data was read. **From the store** (read-only, 2026-10-10, 194 `Listing`s): area 11 is on 1 active post; a collapsed group
still lets a user choose it (#249). 50 נוה עופר sits with the south, 36 צמרות איילון with the North.

Where the grouping lives in code: `reference/area_groups.yaml`, read only through `areas/reference.py` (#330, point 23),
built with 3.7.

---

## 7. For Ron's decision

1. **3.8's plan, the admin's pages** (round 19): its points 60–76 (3.8, "Points for Ron"), then the go for build step 1.
2. Unchanged from Phase 2 and not in this phase: the bill (Ron), the deferred carrier of #241 and the reclassify of the
   190 `Listing`s still at version 3 (`BACKLOG.md` items 3, 4).

Decided and so closed here: the task order and the DoD; the technical choices (#258–#260); the area grouping (#261);
round 1's 31 open points (#262–#287); Gate C's names and types, R1–R9 and the Gate E amendments (#288); the plans for
3.4 and 3.5 (#289, #290) and 3.4's three points left by the build (#291–#293); the admin's password reset on the machine
(#294); the plan for 3.6 and its 16 points (#295–#300); how the grouping is held (#301); the missing price at the bottom
(#302); Ron's direction for the site (#303–#315); the plan for 3.7, its 32 points and the notes on the mocks
(#316–#346); the screen sizes (#347); the mock retired (#348); 3.7's rebuilt text and points 33–35 (#349, #350); the
card's button row (#351); points 36–39 (#352, #353); the studio rule (#354, #366, #367); step 7's plan, results, A, C and D
(#368–#384); points 57–59 and 3.7 complete (#385–#388).
