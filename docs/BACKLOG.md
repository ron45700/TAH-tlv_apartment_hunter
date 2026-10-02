# Backlog

**The single place that answers "what is open?"**

`DECISIONS.md` records *why*. `SCHEMA.md` records *what is approved*. `SESSION_LOG.md` records
*what happened*. None of them tracks whether a decision actually reached the code — which is how
decisions #37 and #38 were approved on 2026-09-14 and were still unimplemented on 2026-10-02.

**Last updated:** 2026-10-02

## Rules

1. Every decision that requires a code change gets a row in "Decisions pending implementation" in
   the same session it is recorded in `DECISIONS.md`. The row leaves only when the code and its
   tests are in.
2. A session starts by reading this file and ends by updating it, before `SESSION_LOG.md`.
3. An item is removed when done, not ticked. History belongs to `SESSION_LOG.md`.
4. This file holds no rationale and no schema. It points at the file that does.

---

## Next sprint (in order)

| # | Item | Source | Needs |
|---|---|---|---|
| 1 | Task 1.1a spike: one thedoor run over all 6 groups, report on P1, P5, P9, P6 | `PHASE_1.md` 1.1a | `APIFY_TOKEN` in `.env` (Ron brings it) |
| 2 | Fix `textnorm` to match decision #37 | see below | — |
| 3 | Fix `textnorm` to match decision #38 | see below | Ron: keep or drop repeated phones within one post? |
| 4 | Task 1.3: dedup stage A | `PHASE_1.md` 1.3 | items 2 and 3 done first |
| 5 | Gate B: `Listing` schema | `PHASE_1.md` Gate B | Ron's approval; must carry the fields behind decision #41 |
| 6 | Resolve where the #41 filters live in v1 | `DECISIONS.md` #41, open point | Ron's decision |

---

## Decisions pending implementation

| Decision | State of the code (checked 2026-10-02) | What has to change |
|---|---|---|
| #36 relative minutes for `postsNewerThan` | No `fetch()` exists yet | Applies when `fetch()` is written in task 1.1 |
| #37 text that normalizes to nothing is `no_text` | **Not implemented.** `normalize.py::compute_text_hash` still raises `UnhashableTextError`; `annotate.py` sets `no_text` from `is_blank` only; the `RawPost` validator rejects `no_text=True` on non-blank text; `test_text_that_normalizes_to_nothing_raises` asserts the old behaviour | Return `None` instead of raising; `no_text=True` when the normalized text is empty; relax the validator through one shared helper (single-implementation rule); replace the test; remove `UnhashableTextError` |
| #38 phones stored normalized | **Not implemented.** `phones.py::extract_phones` returns phones as written; `canonical_phone` exists but is not applied on storage; tests expect the as-written form | Store `canonical_phone` output; update `PHONES_FROM_TASK_1_2` and `test_phone_formats`; `find_by_phone` normalizes its input |
| #39 no-text posts notified in a minimal format | `policy` and `notify` are stubs | Applies in tasks 1.5 and 1.7 |
| #41 view-time filters | Nothing exists | Gate B fields, then Gate C, then the read side |

---

## Doc debt

| Item | Where |
|---|---|
| Invariant 5 still says `user.id` is a rotating `pfbid`; corrected elsewhere on 2026-09-14 | `CLAUDE.md` |
| Domain trap still names `isMarketplaceListing`; the real flag is `sale_post.isOnMarketplace` | `CLAUDE.md` |
| Commands list `tlv_hunter.jobs.*`, which does not exist yet | `CLAUDE.md` |
| `docs/PROVIDERS.md` is referenced but was never created | `CLAUDE.md`, `MACRO_PLAN.md` §10 |
| "What Ron is looking for" describes one fixed search; superseded by decision #41 | `HANDOFF.md` §1 |
| Not recorded outside `SESSION_LOG.md`: documented top-level `user_id` absent from the real response; `RawPost` validators; `FixtureProvider` inclusive `since`; v1 `user_id` value `ron` | `ASSUMPTIONS.md` / `SCHEMA.md` |

---

## Future (recorded, not planned)

| Item | Note |
|---|---|
| Yad2 as an additional source | `MACRO_PLAN.md` §9 |
| Second user | `MACRO_PLAN.md` C3, §9 (legal status) |
| Comments scraping, image re-hosting | `MACRO_PLAN.md` Phase 6+ |
