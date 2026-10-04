# Backlog

**The single place that answers "what is open?"**

`BASELINE.md` records *what the system is*. `DECISIONS.md` records *why*. `SCHEMA.md` records *what
is approved*. `SESSION_LOG.md` records *what happened*. None of them tracks whether a decision
actually reached the code, which is how decisions #37 and #38 were approved on 2026-09-14 and were
still unimplemented on 2026-10-02.

**Last updated:** 2026-10-04

## Rules

1. Every decision that requires a code change gets a row in "Decisions pending implementation" in
   the same session it is recorded in `DECISIONS.md`. The row leaves only when the code and its
   tests are in.
2. A session starts by reading this file and ends by updating it, before `SESSION_LOG.md`.
3. An item is removed when done, not ticked. History belongs to `SESSION_LOG.md`.
4. This file holds no rationale and no schema. It points at the file that does.

---

## Next sprint (in order)

Phase 1, as detailed in `PHASE_1.md`.

| # | Item | Source | Needs |
|---|---|---|---|
| 1 | Task 1.3: dedup stage A and the repost log | `PHASE_1.md` 1.3 | **Open, for 1.3 planning:** "a repost of an archived post makes it active again" does not distinguish a post that was active from one rejected for another reason or never classified; a re-fetched post's `upsert` overwrites the stored derived fields (`is_canonical`, `duplicate_of`), and an edited text changes the stored `text_hash` (`PHASE_1.md` 1.3) |
| 2 | Tasks 1.12–1.14: image download, watermark logic, `run_once` | `PHASE_1.md` | Item above. **Open, for 1.12 planning:** exactly which posts get their images downloaded; when canonical and repost are new in the same run, whether the repost downloads depends on the order of downloads (`PHASE_1.md` 1.12). **Open, for 1.14 planning:** the store step — the sequence of `get_lifecycle`, `upsert` / `upsert_with_lifecycle` and `save_lifecycle`, and who calls `pre_model_reason`, `initial_lifecycle` and `recheck` (task 1.11); which step calls `find_without_lifecycle` and what it does with a non-empty result; who creates the `store_root` directory (`SqliteRepository` does not, `local_json` does); where the production constant for `tlv_hunter.sqlite3` lives; where `ThedoorProvider` gets the Apify token (`APIFY_TOKEN` in `.env`; the provider takes it as a constructor argument) (`PHASE_1.md` 1.14) |

---

## Decisions pending implementation

| Decision | State of the code (checked 2026-10-04) | What has to change |
|---|---|---|
| #57 the name next to a phone number | Phones are extracted and stored once per post; no name is captured | Gate B defines it (`DECISIONS.md` #57) |
| #63 Gate E: post lifecycle record, `GroupWatermark` | `PostLifecycle` and `GroupWatermark` exist and are stored (task 1.10); the initial record and the pre-model re-check are built by `premodel/rejects.py` (task 1.11), and nothing stores them yet. The Gate A media fallback is in the mapper (task 1.1) | Task 1.14: store the record that task 1.11 builds (`pending` / `rejected`, `no_text` and `no_images`). Task 1.3: `last_published_at` from duplicates (never backwards; a phone-only match is not a duplicate); repost log derived from `duplicate_of`. Task 1.12: photos only, one retry, failures recorded in `images`, the identical-hash repost rule. Task 1.13: when `GroupWatermark` advances, written through `WatermarkStore.save_all` |
| #64, #65 the SQLite store and `state/` | Built and tested (task 1.10). `pipeline.py` still calls `upsert` only, and nothing constructs `SqliteRepository` or `SqliteWatermarkStore` | Task 1.14: store posts through `upsert_with_lifecycle` (the initial record is built by `initial_lifecycle`, task 1.11), and construct both modules on `<store_root>/tlv_hunter.sqlite3` |
| #67–#70, #72, #73 `no_images` means no media at all; a re-fetched pre-model reject, or `pending` post, is re-checked against both rules; media through an identical-hash repost | Task 1.11 done: `pre_model_reason`, `initial_lifecycle` and `recheck` in `premodel/rejects.py` (#67, #72.1, #72.6, #73.1–#73.3). Nothing calls them yet | Task 1.14: call them in the store step and write the result. Task 1.3: #70, the canonical returns to `pending` when an identical-hash repost with media arrives, video or reel only included (#72.4); for an archived `no_images` canonical, `pending` wins over "active again" (#72.5). Task 1.12: #70, #72.3, the repost's photos downloaded while the canonical has no `PostImage` with a `local_path`, or when it is archived, and recorded in the canonical's `images`; "what we hold" is any such `PostImage`, including one from an earlier repost, for every canonical (#73.5). #72.2 adds no code. #72.7: Gate D |
| #47 profiles live in the database; no per-user group subscriptions | `config/users/ron.yaml` holds `user_id` and subscribed groups; the config interface exposes them | Remove the per-user YAML and its interface methods when the user records arrive in phase 3. Until then it is unused, not wrong |
| #49 lifecycle and rejection reasons | `PostLifecycle` and its storage exist (task 1.10); the pre-model state and reason are computed (task 1.11) but not stored | Gate E approved (#63); tasks 1.3 and 1.14; model-decided reasons in phase 2 |
| #46 archive and deletion | Nothing exists | Stored shape approved at Gate E (#63); the jobs in phase 5 |
| #45 sniper removed | Not in the package. Research copies may sit in `data/raw/` (gitignored) | Nothing in code. Ron may delete the research copies |
| #51, #52 filter model and alert rules | `policy` is a stub | Gate C in phase 3; alerts in phase 4 |
| #56 the bot listens | `notify` is a stub | Phase 4 |
| #61 admin-set run interval and a manual "run now" | No scheduler exists | Phase 5, with the scheduler. Interval and last-run record approved then |
| #62 viewed posts, per user | Nothing exists | Gate C in phase 3 (the per-user record); trigger and "mark as not viewed" in the phase 3 UI design |

---

## Recorded for a later phase

Approved by Ron, 2026-10-04. No code until the phase or gate named.

| Item | When |
|---|---|
| The failure alert to the admin names the reason for a failed run (for example, most rows failed to map — the provider may have changed its response shape, `DECISIONS.md` #71 D) | Phase 5 |
| The digest reports the rows skipped below the #71 D ceiling | Phase 5 |
| On a card whose media came through a repost (`DECISIONS.md` #70, #72.4), the video link comes from the repost, not from the canonical | Phase 3 UI design |
| #70 under dedup B: a repost with rewritten text (`DECISIONS.md` #72.7) | Gate D |
| The archive job: whether archiving clears the `PostImage` entries or only deletes the files | Phase 5 |

---

## Open technical choices

Left open on purpose until their phase is planned (`DECISIONS.md` #23).

| Choice | Decide when |
|---|---|
| Dashboard framework and how the site is served | Planning phase 3 |
| Telegram library | Planning phase 4 |
| How the scheduler runs inside the container. It must be interval-based (the interval is an admin setting) and support a manual run that resets the timer on success (`DECISIONS.md` #61) | Planning phase 5 |
| Public source for Tel Aviv areas and streets (`ASSUMPTIONS.md` A1) | Before Gate B |
| SQLite journal mode: the default rollback journal now; WAL is the candidate once the dashboard reads while a run writes (`DECISIONS.md` #65) | Planning phase 3 |
| What the watermark does when a group returns `max_posts` rows or more in a run (the window may be cut off). `fetch()` only logs a warning (`DECISIONS.md` #71, J) | Planning task 1.13 (`PHASE_1.md` 1.13) |
| A shared post with its own caption: its `text` is the caption, and `sharedPost.text` (the shared listing) never reaches the model. Gate A unchanged (`DECISIONS.md` #71, H; `ASSUMPTIONS.md` P16) | Gate B (phase 2) |
| Concurrent writes to `PostLifecycle`. `save_lifecycle` is a whole-record replace, last write wins: a user flagging a post while a run writes the same record loses one of the two changes. Phase 1 has one writer. A contract test pins the current behaviour (`DECISIONS.md` #65) | Planning phase 3 |

---

## Doc debt

| Item | Where |
|---|---|
| `CLAUDE.md` lists no run commands: the `jobs.*` commands were removed because they do not exist. Add them back when task 1.14 writes them | `CLAUDE.md`, Commands |
| Not recorded outside `SESSION_LOG.md`: documented top-level `user_id` absent from the real response; `RawPost` validators; `FixtureProvider` inclusive `since` | `ASSUMPTIONS.md` / `SCHEMA.md` |

---

## Future (recorded, not planned)

| Item | Note |
|---|---|
| memo23 failover | `BASELINE.md` §12, phase 6 |
| Editing the schedule and the group list from the dashboard | `BASELINE.md` §12, phase 6 |
| UI polish from Ron's screenshots | `BASELINE.md` §12, phase 6 |
| Yad2 as an additional source | `DECISIONS.md` #60. Open points from the old plan: `RawPost` is Facebook-shaped (`group_id` required, `source` accepts two values); whether structured Yad2 listings pass through the model; dedup across sources; terms of use |
| Comments scraping | Not planned |
