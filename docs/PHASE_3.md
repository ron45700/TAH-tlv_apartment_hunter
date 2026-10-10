# Phase 3 — The dashboard (semi-macro)

**Status:** a plan, written 2026-10-10 and revised the same day after Ron's answers. **Approved by Ron (2026-10-10):**
the content of Gate C (`DECISIONS.md` #242–#257) and its 31 open points (#262–#287); the task order and the DoD; the
technical choices (§5, #258–#260); the area grouping (§6, #261). **Still waiting for Ron:** Gate C's names and types
(`SCHEMA.md`, Gate C, DRAFT, one table to approve, and the small points R1–R9); the plans for 3.4 and 3.5 (written below,
with their own points). No code before a task's plan is approved; no paid call before its own go.
**Owner:** Ron
**Parent:** `BASELINE.md` §12 · **Schema:** `SCHEMA.md`, Gate C (DRAFT, not approved), Gates A, B, E (approved), Gate D
(the key, #230, #232) · **Research:** `RESEARCH.md` §16 (the area grouping check)

**Phase goal:** Ron and his friends sign in to a site on the tailnet, set their profile, and see the real active posts
that fit it, in a polished UI (#257); the admin works the rejected, pending and archive lists, the flags, the reports and
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
| Gate C's names and types; the Gate E amendments | `SCHEMA.md`, Gate C ("For Ron's approval") and "PROPOSED amendments" under Gate E | **DRAFT, waiting for Ron** |
| The technical choices: the framework, the journal mode, compare and set | #258, #259, #260 | Approved 2026-10-10 |
| The area grouping | #261 | Approved 2026-10-10 |
| The card, the field states, the colours | `BASELINE.md` §6, §7, §8 | Approved; binding on the UI (#257) |
| The same-listing grouping is derived by the Gate D key, never stored | #230, #231, #232 | Approved |
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

## 3.1 Gate C: names and types — content decided; NAMES WAITING for Ron

`SCHEMA.md`, Gate C (DRAFT): `User`, `SignupKey`, `Session`, `Profile` with two `SearchOption`s, `ViewedPost`,
`ClassificationReport`, `FieldCorrection`; the Gate E amendments E-1 to E-5. Round 1's 31 open points are answered
(#262–#287). **Needs from Ron:** the one table "For Ron's approval: every name and type", and points R1–R9 (details the
answers asked the assistant to propose). Approved like Gate B: in writing, then recorded in `DECISIONS.md`.

## 3.2 Technical choices — DECIDED (#258–#260, 2026-10-10)

The framework (§5.1, option A), the rollback journal with an explicit busy timeout (§5.2), compare and set for every
`PostLifecycle` writer (§5.3). Sessions (#263) and where the records live (#267) are decided with Gate C's points. What is
left is in the 3.4 and 3.5 plans.

## 3.3 Area grouping — DECIDED (#261, 2026-10-10)

§6 as proposed, with the four undecided entries in regular groups. Nothing left for Ron.

## 3.4 Store: the Gate C records and the lifecycle writes — content approved; PLAN written 2026-10-10, WAITING for Ron

**The plan assumes Ron approves Gate C's names as drafted** (`SCHEMA.md`, Gate C, "For Ron's approval"). Nothing is
written, installed or changed until Ron approves this plan. No paid call, no network call; the production store is not
opened for writing by any step of this task.

**Scope.** (a) The eighth seam and its SQLite store; (b) the Gate C records as contracts; (c) `PostLifecycle` version 3
and `"misclassified"`; (d) compare and set for every `PostLifecycle` writer, in both stores, and every caller (#260);
(e) the explicit busy timeout (#259); (f) the per-user YAML removed (#47). **Not in 3.4:** the account logic (3.5), the
evaluation (3.6), the site (3.7), any write of a report or a flag (3.7, 3.8).

### (a) The eighth seam — name and contract proposed (#267)

**Proposed name: `userdata/`, interface `UserDataStore`.** Proposed row for `CLAUDE.md`'s seam table (not written into
`CLAUDE.md` until Ron approves the name):

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

## 3.5 Accounts — content approved (#242–#244, #262–#266); PLAN written 2026-10-10, WAITING for Ron

**The plan assumes Ron approves Gate C's names as drafted, and 3.4.** Nothing is installed until Ron approves it.

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

- `argon2-cffi` 25.1.0's release date: the PyPI page was cut off before it.
- That the bindings' wheel installs in the container's base image: depends on the image chosen in 3.9 (ASSUMED until then).
- `get_default_parameters()` on Windows: not read; the plan does not depend on it, since the profile is named explicitly.
- The time one hash takes on the laptop and the home server, and the memory under several sign-ins at once (64 MiB
  each): not measured; small for a few users.

### Points for Ron (3.5)

1. The module names: `accounts/` (`passwords.py`, `tokens.py`, `actions.py`) and `jobs/create_admin.py`.
2. The dependency `argon2-cffi`, with the parameters named explicitly (`RFC_9106_LOW_MEMORY`).
3. `create_admin` is a new command that writes the production file (the `userdata` tables only); `CLAUDE.md`'s writer
   paragraph names it.
4. No command to issue keys before the admin's pages (3.8): the first friend signs up after 3.8.

## 3.6 Evaluation (`policy/`) — content approved, plan to be written

`policy/` stops being a stub. Pure code over the stored records; nothing written on a post (invariant 12); no model call
(`BASELINE.md` §2, principle 6).
- **The post as a user sees it:** the `Listing` with the admin's corrections in force applied over it (#256), never
  edited.
- **The same-listing grouping, derived by the Gate D key** (#230, #232), for the lists, the cards and the repost log;
  never written (#231). **Its first check: the 4 pairs the key finds today** (§4). Open, from #231: whether deriving it
  stays fast enough as the store grows; measured here, on the real store.
- **The two search options** (#245–#247): which option evaluates a post, the critical conditions, the preferences, the
  order of display (§8), viewed before unviewed (#62), the area's colour per user (#250).
- **The other-city name for the card and the rejected list** comes from `postmodel.rejects.other_city_name(post,
  listing)` (or `other_city_ruling`), never from `Listing.other_city` alone (#214, option A). For `26e8a28b…` the card
  shows "רמת גן" while its `other_city` is null.
- **Decided for it** (#269–#275, #281, #287): fixed wanted values; the entry-date range and "immediate"; a post of
  unclear kind at the bottom, under every enabled option; sublets; orange with no areas chosen; corrected values read
  everywhere, the Gate D key included.
- **Needs from Ron:** the names (3.1) and point R2 ("immediate" as the UTC date); the plan's approval.

## 3.7 The site — content approved, plan and design to be written

The lists and the cards (`BASELINE.md` §6) with these approved display rules (`BACKLOG.md`, "Recorded for a later
phase"): the card's main time is the last publication, shown relative (#122); the repost log shows the earliest
`posted_at` of the post and its duplicates (#75 A); rooms on a room post, "1 of N" (#120); size on a room post (#121);
the entry date's year never displayed (#115); on a card whose media came through a repost, the video link comes from
the repost (#70, #72.4). The profile editor with the two options, the sublet switch, "copy from the other option"
(#245–#247), and the area filter grouped (#248, #249). Viewed: opening a card, "mark as not viewed" (#253). Flag "lied"
and "wrong classification" (#173, #254).
**The polished UI is built here (#257)**, with Ron's design skills, when this task is reached; `BASELINE.md` §6–§8 stay
binding. The framework is decided (#258). **Needs from Ron:** the plan's approval; the design direction, at the task.

## 3.8 The admin lists — content approved (`BASELINE.md` §11; #75 B, #173, #243, #251, #254–#256), plan to be written

- **Rejected,** every reason, canonicals only (#75 B), the city shown through `other_city_name` (#214).
- **Pending,** canonicals only (#75 B), with each post's `last_classification_error`; the "retry" that sets
  `classification_failures` back to 0 (Gate E, #139, #152).
- **Archive,** canonicals only (#75 B). Nothing is archived until Phase 5's job; the list exists and is empty.
- **Flags by user, and restore** (`BASELINE.md` §11; #251).
- **Reports grouped by field** (#173, #254), with restore, correct by hand (#256), or leave out; the corrections in
  force, and their removal.
- **Keys and users** (#243, #265, #266): issue, list, cancel; the password reset (#262); disable and enable a user.
- **Reports whose post was not rejected** (3.4 point 3), with a retry.
- **Needs from Ron:** the plan's approval.

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

Where the grouping lives in code (a table beside `reference/areas.yaml`, read through `areas/reference.py`, or in the
site's code) is decided in 3.7's plan.

---

## 7. For Ron's decision

1. Gate C's names and types: the one table in `SCHEMA.md` ("For Ron's approval: every name and type"), with the
   Gate E amendments E-1 to E-5, and points R1–R9 — 3.1.
2. The plan for 3.4 and its eight points.
3. The plan for 3.5 and its four points.
4. Unchanged from Phase 2 and not in this phase: the bill (Ron), the five reclassify proposals waiting in
   `dcb4c0cb4b24`, the deferred carrier of #241 and the reclassify of the other 189 (`BACKLOG.md`).

Decided on 2026-10-10 (round 2) and so closed here: the task order and the DoD; the technical choices (#258–#260); the
area grouping (#261); round 1's 31 open points (#262–#287).
