# Backlog

**The single place that answers "what is open?"**

`BASELINE.md` records *what the system is*. `DECISIONS.md` records *why*. `SCHEMA.md` records *what
is approved*. `SESSION_LOG.md` records *what happened*. None of them tracks whether a decision
actually reached the code, which is how decisions #37 and #38 were approved on 2026-09-14 and were
still unimplemented on 2026-10-02.

**Last updated:** 2026-10-05

## Rules

1. Every decision that requires a code change gets a row in "Decisions pending implementation" in
   the same session it is recorded in `DECISIONS.md`. The row leaves only when the code and its
   tests are in.
2. A session starts by reading this file and ends by updating it, before `SESSION_LOG.md`.
3. An item is removed when done, not ticked. History belongs to `SESSION_LOG.md`.
4. This file holds no rationale and no schema. It points at the file that does.

---

## Next sprint (in order)

Phase 1 is complete (2026-10-04, `PHASE_1.md`). Phase 2 is being planned: Gate B approved on
2026-10-05 (`DECISIONS.md` #81–#125); the model provider is OpenAI, for now (#126); `PHASE_2.md`
approved, the spike run (#126–#156); the model decides the area (#167); tasks 2.2 and 2.3 (reduced) built (#174, #175).

| # | Item | Source | Needs |
|---|---|---|---|
| 1 | After 2026-10-08: one free GET on an expired run A photo link, to see what an expired link returns (an HTTP status, or a network error or timeout). No Apify call. Record it under `ASSUMPTIONS.md` I7 (`DECISIONS.md` #80 U5) | `DECISIONS.md` #80 | Approved by Ron, 2026-10-04. The 4-day limit on stored-link retries does not rest on the answer |
| 2 | Ron reads the spike's cost in the OpenAI dashboard and compares it with the usage-metadata total, $0.0273 (`docs/SPIKE_2_1_2026-10-05.md` §5) | `ASSUMPTIONS.md` O2, P19's lesson | Ron, some minutes after the run (2026-10-05) |
| 3 | Ron reviews the code of task 2.2 (`Listing` storage, the Gate E fields, #89) and of the reduced task 2.3 (`reference/areas.yaml` and its reader); then the plan for task 2.4 is written | `PHASE_2.md` 2.2, 2.3, §4; `SESSION_LOG.md` 2026-10-05 | Ron, then the plan. No 2.4 code before its plan is approved |

---

## Decisions pending implementation

| Decision | State of the code (checked 2026-10-04) | What has to change |
|---|---|---|
| #57 the name next to a phone number | Phones are extracted and stored once per post; no name is captured | Settled by #105 (Gate B approved, #125): the model returns name-number pairs; a name is kept only when its number equals one already extracted. Built in phase 2 (`PHASE_2.md` 2.4), after the response model's names (#137) |
| #81–#83, #119, #167 the 71 areas, and the model deciding the area | `reference/areas.yaml` and `areas/reference.py` built (task 2.3, reduced), waiting for review | Phase 2 (2.4): the instructions carry the 71 and the area rules (#88, #112, #124) and #86's rows as examples |
| #89–#106, #108, #109, #114, #115, #117, #118, #123, #125 the `Listing` record and its fields | `Listing` and its storage built (task 2.2), waiting for review | Phase 2 (2.4): the classifier with the response model (#137, #151, `areas` in it since #167), the native-price floor (#114), the entry-date year and the month rule (#115, #123), the code that derives the rejection (#92) |
| #126–#130, #146–#150 OpenAI as the provider; `gpt-6-luna`; `OPENAI_API_KEY` in the entry point only; `store: false`; effort from `none`; the reported model value logged; explicit caching | The spike's throwaway script only (`scratch/`) | Phase 2: the classifier's call (2.4) |
| #138–#141, #152 `classify_pending`; three failed runs and the Gate E failure fields (`schema_version` 2); never beside `run_once`; an edited post keeps its `Listing` | Nothing exists | Phase 2 (2.5) |
| #142, #143, #171, #172 the regression set; the labelling page (areas picked from the 71) and the review report (errors per field; corrected posts join the regression set), in `data/labeling/` | Nothing exists | Phase 2 (2.6, 2.7) |
| #144 reclassify, manual, replace with a diff report | Nothing exists | Phase 2 (2.9) |
| #145 Gate D after the first paid run | Nothing exists | Phase 2 (2.10) |
| #157 effort `none`, temperature 0 | The spike's throwaway script only | Phase 2 (2.4), confirmed on the regression set run twice (2.6) |
| #159–#162 sublet, one amount for several charges, "דירת N שותפים", a name not in the text dropped, the model never computes | Nothing exists | Phase 2 (2.4): the prompt and the checks in code |
| #163 invariant 14: classification never touches the source text | `save_classification` never writes `raw_posts`; a contract test pins it on both stores (task 2.2) | Phase 2 (2.5): the job, with its own test |
| #89 closes #74's open point: a reposted archived post with no rejection reason returns to `"active"` if a classification record exists, `"pending"` if not | Built in `dedup/stage_a.py` (task 2.2), waiting for review | Nothing more |
| #77 D4b archiving deletes the image files and removes their `PostImage` entries | Nothing exists; task 1.12 already reads a record archived before #74 without counting its old entries (#77 D4) | Phase 5, the archive job |
| #47 profiles live in the database; no per-user group subscriptions | `config/users/ron.yaml` holds `user_id` and subscribed groups; the config interface exposes them | Remove the per-user YAML and its interface methods when the user records arrive in phase 3. Until then it is unused, not wrong |
| #49 lifecycle and rejection reasons | `PostLifecycle` and its storage exist (task 1.10); the pre-model state and reason (task 1.11) and the repost changes (task 1.3) are stored by `run_once` (task 1.14) | Model-decided reasons in phase 2 |
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
| Image files with no `PostImage` pointing at them: written by a run that failed after the download and before the store step, for a post that never comes back. A sweep of unreferenced files under `<store_root>/images/` (`DECISIONS.md` #77, plan §3) | Phase 5 |
| The repost log shows the earliest `posted_at` of the post and its duplicates: the stored canonical can be later than a duplicate that arrived after it (`DECISIONS.md` #75 A). The card's main time is the last publication (#122). A display rule | Phase 3 UI design |
| Phase 2 classifies only posts that are `pending` **and** canonical (`is_canonical`); a duplicate's own record can be `pending`, since it is built from its own content (`DECISIONS.md` #75 B) | Phase 2 (`PHASE_2.md` task 2.5) |
| The admin lists (rejected, pending, archive) show canonicals only (`DECISIONS.md` #75 B) | Phase 3 |
| Whether a duplicate's retention follows its own clock or its canonical's (`DECISIONS.md` #75 B). Note: `dedup_a` raises when a stored duplicate points at a canonical that is not stored, so deleting a canonical before its duplicates would block the run | Phase 5 |
| The phone as a candidate signal for dedup B; layer 3 of dedup A produces nothing (`DECISIONS.md` #75 C) | Gate D |
| Measure a week of real runs before concluding on volume and monthly cost. Run A, a weekday, returned 212 rows in 24 h with two groups cut off at 50, against the ~125–150 estimated from weekend data (`ASSUMPTIONS.md` P7); the ~$12–16/month Ron accepted may be low. Approved by Ron, 2026-10-04 | Before any conclusion on volume or cost; each run is paid and approved by Ron |
| A daily wide run covering 24 h, about $5/month, to heal a per-group miss within a day (`DECISIONS.md` #78 W1) | Phase 5, the scheduler |
| Check the container's SQLite version against the store module's minimum, 3.38.0 (the JSON functions built in by default, `DECISIONS.md` #80); the constructor refuses an older one. `ASSUMPTIONS.md` I8 | Phase 5, when the server is set up |
| The alert thresholds on `consecutive_failures` (zero-row successful runs). A healthy group can be silent for 31 h, about 49 runs (`DECISIONS.md` #78 W5b, `RESEARCH.md` §9) | Phase 5 |
| Detect a group that fails inside a successful run from the run log, and hold back only that group (`DECISIONS.md` #78 W4). Needs the run-log endpoint verified under the `external-contract-verification` skill, one small test run against an unreachable group (about $0.01; Ron approves it when planned), and `fetch()` returning per-group status (a provider contract change). Rests on P13, ASSUMED | Its own task, when Ron schedules it |
| Groups × `max_posts` must stay below the charge cap's `maxItems` (333 at $0.50); a seventh group at 50 crosses it (`DECISIONS.md` #78 W3) | Planning group editing (phase 6) |
| Adding a group needs a way to create its `GroupWatermark` without a full bootstrap; outside bootstrap a configured group with no record raises (`DECISIONS.md` #78 W7) | Planning group editing (phase 6) |
| `DECISIONS.md` #11 says the first run "sends one summary"; `BASELINE.md` §4 says a bootstrap run alerts nothing. Not resolved | Ron decides when phase 4 is planned |
| Which size the sqm filter uses in a room search: the apartment's or the room's (`DECISIONS.md` #99). Approved by Ron, 2026-10-05 | Gate C |
| Grouping of the 71 areas in the area filter (`DECISIONS.md` #82). Approved by Ron, 2026-10-05 | Gate C |
| A "wrong classification" action on a card, naming the field; the post moves to the rejected list for everyone with its own reason; the admin sees the reports grouped by field, corrects by hand and restores, or leaves it out (`DECISIONS.md` #173). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| The schema for #173: a new rejection reason and a corrections record, stored apart from the model's answer, so the card shows the corrected value and the model's answer stays for error analysis. Approved by Ron, 2026-10-05 | Gate C |
| Hiding the non-residential entries of the 71 from the area filter; they stay in the list (`DECISIONS.md` #81). Approved by Ron, 2026-10-05 | Gate C |
| No orange on the area for a user who chose every entry a stated name covers (for example 30 and 31 for "הצפון הישן"): a per-user display rule (`DECISIONS.md` #112). Approved by Ron, 2026-10-05 | Gate C |
| The card's main time is the last publication (the latest repost), shown relative: minutes up to an hour, hours up to 24 h, days after that; earlier publications are in the repost log (`DECISIONS.md` #122). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Rooms on a room post: "1 of N" when the total is written, a room with no "of" when it is not; the "1" comes from the apartment kind (`DECISIONS.md` #120). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Size on a room post: "X sqm for the room, of Y" when both are written; "X sqm for the room" when only the room's is (`DECISIONS.md` #121). Not stated: a room post that gives only the apartment's size. Approved by Ron, 2026-10-05 | Phase 3 UI design |
| The entry date's year is never displayed (`DECISIONS.md` #115). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Regression set: English posts (27 of 266 stored posts are mostly English, by the review chat's count; not reproduced exactly, see `SESSION_LOG.md` 2026-10-05). Approved by Ron, 2026-10-05 | Building the regression set (phase 2) |
| Regression set: "seeking a roommate for our flat" (an offer) against "seeking a roommate to search with" (seeking). Approved by Ron, 2026-10-05 | Building the regression set (phase 2) |
| Regression set: the 20 posts of spike 2.1 (`data/spike_openai_2026-10-05/listing_ids.json`; 19 from the store, #45's case from `data/raw/test_posts.json`). Approved by Ron, 2026-10-05 | Building the regression set (phase 2) |
| Regression set: a real "seeking" post and a real Jaffa post from the store (`DECISIONS.md` #165); the spike's two were sale posts. Approved by Ron, 2026-10-05 | Building the regression set (phase 2) |
| Regression set: #45's untested seeking case, `אנחנו שני שותפים שמחפשים דירת 3 חדרים` (`ASSUMPTIONS.md` C2, `RESEARCH.md` §7). Approved by Ron, 2026-10-05 | Building the regression set (phase 2) |

---

## Known limits, not handled now

| Limit | Effect |
|---|---|
| A group that fails inside a successful run advances like the others; its window is lost (`DECISIONS.md` #78 W4) | Posts missed for good, until the run-log task above exists |
| A group at `max_posts` short of its window still advances; `advance` reports it (`DECISIONS.md` #78 W3) | The posts between its window start and its oldest returned post may be missed for good. A row skipped under #71 D lowers the count, and such a group can go unreported |
| A repost's photo that failed while its canonical held nothing keeps its error once the canonical holds an image (`DECISIONS.md` #77 D2, #80 U7) | The record still reads `network: …` for that photo; it is never retried. The stored-link query returns the record on every run, and it is skipped |
| A run killed during `fetch()` (Ctrl+C, `taskkill`) does not abort its Apify run: only the run deadline aborts (`DECISIONS.md` #71 F, #79) | The Apify run finishes and is billed, up to the $0.50 cap; its dataset is never read. The watermark does not move |
| A shared post with its own caption: its `text` is the caption, and `sharedPost.text` (the shared listing) never reaches the model (`DECISIONS.md` #71 H, kept by #107; `ASSUMPTIONS.md` P16) | The model classifies the caption only. 1 of the 35 shared posts in the store, 2026-10-05 |
| Arnona and house committee keep no period: "400 per two months" and "400 a month" are both stored as 400 (`DECISIONS.md` #116) | A filter or colour on them treats the two alike; the card's original text shows the period |
| A post that gives only a street: its area rests on what the model knows of Tel Aviv (`DECISIONS.md` #170) | Measured by the regression set's 95% bar on `areas`; a street table as an aid is recorded for later (#169) |
| `dedup_a` finds a canonical's stored duplicates through the hashes of the canonical and of its batch duplicates (`DECISIONS.md` #75 D1). A stored duplicate with media whose text was edited later has a different hash and is not found | #70 can miss it, and a canonical with no media can return to `"rejected"` |

---

## Open technical choices

Left open on purpose until their phase is planned (`DECISIONS.md` #23).

| Choice | Decide when |
|---|---|
| Dashboard framework and how the site is served | Planning phase 3 |
| Telegram library | Planning phase 4 |
| How the scheduler runs inside the container. It must be interval-based (the interval is an admin setting) and support a manual run that resets the timer on success (`DECISIONS.md` #61). One run at a time: a run can last longer than the 30-minute interval, since the image download alone may take up to 30 minutes (#77 D5b). `run_once` takes no lock; a run overtaken by a later one fails at `advance` and moves no watermark (`DECISIONS.md` #79 O9) | Planning phase 5 |
| SQLite journal mode: the default rollback journal now; WAL is the candidate once the dashboard reads while a run writes (`DECISIONS.md` #65) | Planning phase 3 |
| Concurrent writes to `PostLifecycle`. `save_lifecycle` is a whole-record replace, last write wins: a user flagging a post while a run writes the same record loses one of the two changes. Phase 1 has one writer; phase 2 adds `classify_pending`, never run beside `run_once` (`DECISIONS.md` #140). A contract test pins the current behaviour (`DECISIONS.md` #65) | Planning phase 3 |

---

## Doc debt

| Item | Where |
|---|---|
| Not recorded outside `SESSION_LOG.md`: documented top-level `user_id` absent from the real response; `RawPost` validators; `FixtureProvider` inclusive `since` | `ASSUMPTIONS.md` / `SCHEMA.md` |

---

## Future (recorded, not planned)

| Item | Note |
|---|---|
| memo23 failover | `BASELINE.md` §12, phase 6 |
| Editing the schedule and the group list from the dashboard | `BASELINE.md` §12, phase 6 |
| `max_posts` editable by the admin | `BASELINE.md` §11, §12 phase 6. Approved by Ron, 2026-10-04; recorded, not built. One value for all groups (the actor takes one `maxPosts` per run). On save, the system refuses a value where groups × `max_posts` reaches the charge cap's `maxItems`. Open, decided when planned: whether the charge cap itself is editable |
| UI polish from Ron's screenshots | `BASELINE.md` §12, phase 6 |
| A street table as an aid to the model's area (`DECISIONS.md` #169) | Only if the regression set shows the model weak on posts that give a street and no area. The superseded plan is in `PHASE_2.md`'s appendix; the sources in `RESEARCH.md` §12, §14 |
| Gemini's free tier as the model provider | A possible later switch, not planned (`DECISIONS.md` #126; `RESEARCH.md` §13). A free-tier run would need a separate Google project with no billing |
| Yad2 as an additional source | `DECISIONS.md` #60. Open points from the old plan: `RawPost` is Facebook-shaped (`group_id` required, `source` accepts two values); whether structured Yad2 listings pass through the model; dedup across sources; terms of use |
| Comments scraping | Not planned |
| Parallel image downloads, if runs prove too long | Not planned; recorded 2026-10-04 with Ron's approval. Ron chose the 30-minute budget instead (`DECISIONS.md` #77 D5b). Would need its own check for throttling (`ASSUMPTIONS.md` I11 covers sequential requests only), and must keep #77 D3's order inside each group |
