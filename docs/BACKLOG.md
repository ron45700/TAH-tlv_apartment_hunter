# Backlog

**The single place that answers "what is open?"**

`BASELINE.md` records *what the system is*. `DECISIONS.md` records *why*. `SCHEMA.md` records *what
is approved*. `SESSION_LOG.md` records *what happened*. None of them tracks whether a decision
actually reached the code, which is how decisions #37 and #38 were approved on 2026-09-14 and were
still unimplemented on 2026-10-02.

**Last updated:** 2026-10-03

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
| 1 | Task 1.2b: `textnorm` fixes for #37, #38, #57 | `PHASE_1.md` 1.2b | — |
| 2 | Task 1.1a: spike, one real run over all 6 groups, written report | `PHASE_1.md` 1.1a | `APIFY_TOKEN` in `.env` (Ron brings it) |
| 3 | Gate E: post lifecycle fields | `PHASE_1.md` Gate E | Ron's approval |
| 4 | Task 1.10: SQLite store | `PHASE_1.md` 1.10 | — |
| 5 | Task 1.1: thedoor `fetch()` | `PHASE_1.md` 1.1 | item 2 done |
| 6 | Task 1.11: pre-model rejects | `PHASE_1.md` 1.11 | item 3 done |
| 7 | Task 1.3: dedup stage A and the repost log | `PHASE_1.md` 1.3 | items 1 and 3 done |
| 8 | Tasks 1.12–1.14: image download, watermark, `run_once` | `PHASE_1.md` | items above |

---

## Decisions pending implementation

| Decision | State of the code (checked 2026-10-02) | What has to change |
|---|---|---|
| #36 relative minutes for `postsNewerThan` | No `fetch()` exists yet | Applies when `fetch()` is written in task 1.1 |
| #37 text that normalizes to nothing is `no_text` | **Not implemented.** `normalize.py::compute_text_hash` still raises `UnhashableTextError`; `annotate.py` sets `no_text` from `is_blank` only; the `RawPost` validator rejects `no_text=True` on non-blank text; `test_text_that_normalizes_to_nothing_raises` asserts the old behaviour | Return `None` instead of raising; `no_text=True` when the normalized text is empty; relax the validator through one shared helper (single-implementation rule); replace the test; remove `UnhashableTextError` |
| #38 phones stored normalized | **Not implemented.** `phones.py::extract_phones` returns phones as written; `canonical_phone` exists but is not applied on storage; tests expect the as-written form | Store `canonical_phone` output; update `PHONES_FROM_TASK_1_2` and `test_phone_formats`; `find_by_phone` normalizes its input |
| #57 an identical phone within one post is stored once | Not implemented; repeats are kept | Deduplicate after normalization, order preserved. Same pass as #38. The name next to a number waits for Gate B |
| #44 SQLite store | Only `local_json` exists | Task 1.10 |
| #47 profiles live in the database; no per-user group subscriptions | `config/users/ron.yaml` holds `user_id` and subscribed groups; the config interface exposes them | Remove the per-user YAML and its interface methods when the user records arrive in phase 3. Until then it is unused, not wrong |
| #49 lifecycle and rejection reasons | Nothing exists | Gate E, then tasks 1.11 and 1.3; model-decided reasons in phase 2 |
| #46 archive and deletion | Nothing exists | Stored shape at Gate E; the jobs in phase 5 |
| #45 sniper removed | Not in the package. Research copies may sit in `data/raw/` (gitignored) | Nothing in code. Ron may delete the research copies |
| #51, #52 filter model and alert rules | `policy` is a stub | Gate C in phase 3; alerts in phase 4 |
| #56 the bot listens | `notify` is a stub | Phase 4 |

---

## Open technical choices

Left open on purpose until their phase is planned (`DECISIONS.md` #23).

| Choice | Decide when |
|---|---|
| Dashboard framework and how the site is served | Planning phase 3 |
| Telegram library | Planning phase 4 |
| How the scheduler runs inside the container | Planning phase 5 |
| Public source for Tel Aviv areas and streets (`ASSUMPTIONS.md` A1) | Before Gate B |

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
