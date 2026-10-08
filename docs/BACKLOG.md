# Backlog

**The single place that answers "what is open?"**

`BASELINE.md` records *what the system is*. `DECISIONS.md` records *why*. `SCHEMA.md` records *what
is approved*. `SESSION_LOG.md` records *what happened*. None of them tracks whether a decision
actually reached the code, which is how decisions #37 and #38 were approved on 2026-09-14 and were
still unimplemented on 2026-10-02.

**Last updated:** 2026-10-08

## Rules

1. Every decision that requires a code change gets a row in "Decisions pending implementation" in
   the same session it is recorded in `DECISIONS.md`. The row leaves only when the code and its
   tests are in.
2. A session starts by reading this file and ends by updating it, before `SESSION_LOG.md`.
3. An item is removed when done, not ticked. History belongs to `SESSION_LOG.md`.
4. This file holds no rationale and no schema. It points at the file that does.

---

## Next sprint (in order)

Phase 1 is complete (2026-10-04, `PHASE_1.md`). Phase 2 is being built: Gate B approved on
2026-10-05 (`DECISIONS.md` #81–#125); the model provider is OpenAI, for now (#126); `PHASE_2.md`
approved, the spike run (#126–#156); the model decides the area (#167); tasks 2.2 to 2.5 built and accepted (#174–#184). Task 2.6 (set, labelling page, runner), 2.7 (review report) built; **2.9 (reclassify, #217-#222) built and accepted by Ron on 2026-10-08, no real `--run` or `--apply` yet**; instructions version 3 (the known places, #205, approved #209) passed `areas` by reach in both passes. **The first run over the store (2.8) was made on 2026-10-06** (#213): 194 of 195 pending canonicals classified. **DoD 5 is signed off (#224); DoD 4, the measured working day, moved to Phase 3 (#225).** **Task 2.10 is done: Gate D's key is decided (#230, rule 1 amended by #232); dedup B is not built, its use moves to Phase 3 as a derived result (#231).**

| # | Item | Source | Needs |
|---|---|---|---|
| 1 | After 2026-10-08: one free GET on an expired run A photo link, to see what an expired link returns (an HTTP status, or a network error or timeout). No Apify call. Record it under `ASSUMPTIONS.md` I7 (`DECISIONS.md` #80 U5) | `DECISIONS.md` #80 | Approved by Ron, 2026-10-04. The 4-day limit on stored-link retries does not rest on the answer |
| 2 | Comparing the costs recorded by the runs with the OpenAI bill. Stays with Ron; does not wait for Phase 3 | `DECISIONS.md` #225; `ASSUMPTIONS.md` O2 | Ron |

### For the next prompt version (`DECISIONS.md` #211)

| Item | Source |
|---|---|
| A range of rooms ("2-3 rooms") is unclear. Regression position 24 came back invalid twice on it: the model returned a `rooms` whose state and value disagree (`SESSION_LOG.md`, 2026-10-06) | Ron, 2026-10-06 |
| A malformed price ("7,2000₪", `e6a8b9bb…`, regression position 45) is read as 72,000: a sentence that a malformed amount is unclear (`SESSION_LOG.md`, 2026-10-06) | Ron, 2026-10-08 |
| No area names on an other-city post: `4c5bbcaf…` (Rishon LeZion) returned `stated_area_names` ["לב העיר"]; Ron's review corrected it to [] (`corrections.json`; its post is regression position 52, where area names are not compared, #177) | Ron's review, 2026-10-08 |
| The streets extracted are wrong in both posts of the pair `d269d280…` / `e81273e6…` (Ron's note in `pair_verdicts.json`, 2026-10-08; he also notes the two posts differ in much else, including different brokers). Not a Gate D matter: a calibration item for the streets field | Ron, 2026-10-08 |
| The gender cases at regression positions 34 (wording for both sexes with an age range and the word "preference": the model says women preferred) and 35 (feminine wording about the roommates who stay: women only in 2 of 6 passes) | Ron, 2026-10-06 |

### For phase 3 (`DECISIONS.md` #214, #225)

| Item | Source |
|---|---|
| **`ASSUMPTIONS.md` I3 (the model's cost is small), re-planned with DoD 4:** it is the same measurement, so it closes with the working day below | `DECISIONS.md` #228 |
| **DoD 4, the measured working day (moved from Phase 2):** the number of calls, the tokens and the cost of a day's classification, from the usage metadata and then the OpenAI bill; every paid run under its cap. Done once a dashboard exists, so Ron can also judge how the interface looks on that day | `DECISIONS.md` #225; `PHASE_2.md` DoD 4 |
| **The same-listing grouping is derived by the Gate D key** (`DECISIONS.md` #230, rule 1 amended by #232), for the lists, the cards and the repost log, and is never written onto a post (#231). How it is computed and shown is planned with Phase 3; whether deriving it stays fast enough as the store grows is not measured | `DECISIONS.md` #231 |
| **The 4 pairs the key finds today, as a first check** of the derivation: `54ecb1d0…` / `00f17259…`, `7253eefa…` / `40f7f193…`, `e81273e6…` / `8ae80944…`, `9136a715…` / `9a6252c1…` (read-only, 2026-10-08, 139 active canonicals; Ron judged all four `same_listing`, #229). No post is in two pairs, and none of the eight has an exact-hash duplicate | `DECISIONS.md` #230; `PHASE_2.md` 2.10 |
| **Notes from the dedup B plan worth keeping** (`PHASE_2.md` 2.10, "Plan for dedup B", not built): the agent-number threshold of 4 was a gap in one day's data and is to be re-measured on a week of data with `gate_d_pairs` (the count over every post, duplicates included, would give 3 agent numbers instead of 2); **alerts (Phase 4) must not fire for a post the key ties to an earlier one**; the key reads only active canonical posts that have a `Listing`, so a post waiting for its classification is not tied; a derived grouping follows a change of the key at once, so the key can be revised after Phase 3 | `DECISIONS.md` #230–#232 |
| **The `gate_d_pairs` command runs again on a larger store** (`DECISIONS.md` #226, point 5), to record the rate with its window; it implements the candidate rules, not the key | `DECISIONS.md` #226 |
| **The key's first lists and cards:** the card's main time is the last publication and the repost log shows the earliest `posted_at` (rows under "Recorded for a later phase"); the retention of a duplicate (Phase 5 row) applies to what the key ties | `DECISIONS.md` #122, #75 |
| **The card's city for an other-city post is derived, not stored:** call `postmodel.rejects.other_city_name(post, listing)` (or `other_city_ruling`, which also says whether the city came from Facebook's location field or from the model). For `26e8a28b…` the `Listing`'s `other_city` is null and the card must show "רמת גן". Never read `Listing.other_city` alone for the rejected list or the card | `DECISIONS.md` #214, option A |

### From the first run over the store, 2026-10-06 (for Ron; the stored records were then re-derived on 2026-10-08, #214)

| Item | Source |
|---|---|
| 1 post failed (`json_invalid` twice: the answer was not valid JSON; the bilingual rooftop post `73aebb24…`). It is counted once and retried by the next `classify_pending` run (#139) | `SESSION_LOG.md` 2026-10-06 |
| **Resolved by #214 (2026-10-08):** `2bac260c…` was rejected as `other_city` ("עין ורד", from the text) while the provider's location says Tel Aviv-Yafo and Ron confirms it is a Tel Aviv apartment: it is active now. The model's error stays here, out of the regression count (`corrections_excluded`, #216). Also from the rule: `26e8a28b…` (a Ramat Gan apartment whose text never names the city) is rejected `other_city` and `7d467bbe…` is `other_city`, not `not_listing` | post `2bac260c…` |
| A malformed price ("7,2000₪") became 72,000; the provider's native price is 7,200 and the text's own digits decide (#114). The malformed-amount sentence was not added (regression position 45) | post `e6a8b9bb…` |
| Two near-identical sublet posts are both canonical (different text, so dedup A keeps both) and both took the provider's price, 1,000, as the monthly rent (a native price of at least 500 is used when the text has none, #114) | posts `9136a715…`, `9a6252c1…`; Gate D |
| One dropped area name: "פלורנטין המערבית" does not match exactly because the text has two spaces; the area [52] was still returned (#162's match is exact, #179) | post `e6a8b9bb…` |
| 12 active posts have no area: 6 give only a street the model could not place (#170), 6 give no location | `SESSION_LOG.md` 2026-10-06 |
| A post that says only "Jaffa" returns all 8 Jaffa areas (the examples of #88); one post has 5 areas and one has 4 | `SESSION_LOG.md` 2026-10-06 |

---

## Decisions pending implementation

| Decision | State of the code (checked 2026-10-04) | What has to change |
|---|---|---|
| #142, #143, #157, #171, #172, #177, #183 the regression set, run twice at effort `none`, temperature 0; the labelling page (areas picked from the 71; `other_city` labelled blind; no controls for streets and area names) and the review report (errors per field; streets and area names judged there only; the dropped-names files of `classify_runs/`; corrected posts join the regression set), in `data/labeling/` | Built: the set, the labelling page, the runner (`label_overrides.json`, #196) and the review report (2026-10-06). Version 3 passed `areas` in both passes; `gender` failed in pass 2 and pass 1 was incomplete | Ron signed off the review of the first run (DoD 5, #224); what remains is the review of pass 1 (`review_page --run`, #193). The row leaves when Ron accepts the set |
| #144, #217–#222 reclassify: two commands (`jobs/reclassify.py`, paid, store read-only, writes the diff report and two list files; `jobs/apply_reclassify.py`, free, the fourth store writer, `--allow` / `--allow-file`, no apply all); `find_reviewed` reads the replaced `Listing`s | Plan approved 2026-10-08; built 2026-10-08, waiting for review (`PHASE_2.md` 2.9). No real `--run` and no real `--apply`: they wait for Ron's separate go and for a change of prompt version, model or schema (0 posts are selected today) | Ron's review of the build; the first real `--run` at `--limit 10 --cap 0.02` |
| #77 D4b archiving deletes the image files and removes their `PostImage` entries | Nothing exists; task 1.12 already reads a record archived before #74 without counting its old entries (#77 D4) | Phase 5, the archive job |
| #47 profiles live in the database; no per-user group subscriptions | `config/users/ron.yaml` holds `user_id` and subscribed groups; the config interface exposes them | Remove the per-user YAML and its interface methods when the user records arrive in phase 3. Until then it is unused, not wrong |
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
| #70 under dedup B: a repost with rewritten text (`DECISIONS.md` #72.7). **What the key settles:** Gate D's key is decided (#230) and the tie is derived, not stored (#231). **What is left:** the key compares only active canonical posts that have a `Listing`, so a post rejected as `no_images` (no media, no `Listing`) is not compared and the key as decided cannot tie it to a repost; whether #70's case needs anything is left for Phase 3's planning | Phase 3 planning |
| Image files with no `PostImage` pointing at them: written by a run that failed after the download and before the store step, for a post that never comes back. A sweep of unreferenced files under `<store_root>/images/` (`DECISIONS.md` #77, plan §3) | Phase 5 |
| The repost log shows the earliest `posted_at` of the post and its duplicates: the stored canonical can be later than a duplicate that arrived after it (`DECISIONS.md` #75 A). The card's main time is the last publication (#122). A display rule | Phase 3 UI design |
| The admin lists (rejected, pending, archive) show canonicals only (`DECISIONS.md` #75 B) | Phase 3 |
| Whether a duplicate's retention follows its own clock or its canonical's (`DECISIONS.md` #75 B). Note: `dedup_a` raises when a stored duplicate points at a canonical that is not stored, so deleting a canonical before its duplicates would block the run | Phase 5 |
| The phone as a candidate signal for dedup B; layer 3 of dedup A produces nothing (`DECISIONS.md` #75 C). **What the key settles:** the phone is a signal, never alone, and never an agent number (#230, #232); dedup B is derived, not stored (#231). **What is left:** dedup A's layer 3 still produces nothing, and nothing writes a phone match onto a post | Phase 3 planning |
| Measure a week of real runs before concluding on volume and monthly cost. Run A, a weekday, returned 212 rows in 24 h with two groups cut off at 50, against the ~125–150 estimated from weekend data (`ASSUMPTIONS.md` P7); the ~$12–16/month Ron accepted may be low. Approved by Ron, 2026-10-04 | Before any conclusion on volume or cost; each run is paid and approved by Ron |
| A daily wide run covering 24 h, about $5/month, to heal a per-group miss within a day (`DECISIONS.md` #78 W1) | Phase 5, the scheduler |
| Check the container's SQLite version against the store module's minimum, 3.38.0 (the JSON functions built in by default, `DECISIONS.md` #80); the constructor refuses an older one. `ASSUMPTIONS.md` I8 | Phase 5, when the server is set up |
| The alert thresholds on `consecutive_failures` (zero-row successful runs). A healthy group can be silent for 31 h, about 49 runs (`DECISIONS.md` #78 W5b, `RESEARCH.md` §9) | Phase 5 |
| Detect a group that fails inside a successful run from the run log, and hold back only that group (`DECISIONS.md` #78 W4). Needs the run-log endpoint verified under the `external-contract-verification` skill, one small test run against an unreachable group (about $0.01; Ron approves it when planned), and `fetch()` returning per-group status (a provider contract change). Rests on P13, ASSUMED | Its own task, when Ron schedules it |
| Groups × `max_posts` must stay below the charge cap's `maxItems` (333 at $0.50); a seventh group at 50 crosses it (`DECISIONS.md` #78 W3) | Planning group editing (phase 6) |
| Adding a group needs a way to create its `GroupWatermark` without a full bootstrap; outside bootstrap a configured group with no record raises (`DECISIONS.md` #78 W7) | Planning group editing (phase 6) |
| The first real refusal, 429, 5xx or timeout from the model is captured into `data/raw/`, and the documentation-based tests compared with it (`DECISIONS.md` #181, `ASSUMPTIONS.md` O13) | When it happens |
| `DECISIONS.md` #11 says the first run "sends one summary"; `BASELINE.md` §4 says a bootstrap run alerts nothing. Not resolved | Ron decides when phase 4 is planned |
| Which size the sqm filter uses in a room search: the apartment's or the room's (`DECISIONS.md` #99). Approved by Ron, 2026-10-05 | Gate C |
| Grouping of the 71 areas in the area filter (`DECISIONS.md` #82). Approved by Ron, 2026-10-05 | Gate C |
| A "wrong classification" action on a card, naming the field; the post moves to the rejected list for everyone with its own reason; the admin sees the reports grouped by field, corrects by hand and restores, or leaves it out (`DECISIONS.md` #173). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| The schema for #173: a new rejection reason and a corrections record, stored apart from the model's answer, so the card shows the corrected value and the model's answer stays for error analysis. Approved by Ron, 2026-10-05 | Gate C |
| Hiding the non-residential entries of the 71 from the area filter; they stay in the list (`DECISIONS.md` #81). Approved by Ron, 2026-10-05 | Gate C |
| No orange on the area for a user who chose every entry a stated name covers (for example 30 and 31 for "הצפון הישן"): a per-user display rule (`DECISIONS.md` #112). Approved by Ron, 2026-10-05 | Gate C |
| Whether "restore" of a flagged post consults `postmodel.rejects.model_reason` after a reclassify. `SCHEMA.md` Gate E says a restore returns the state to `"active"`, without looking at the model's rejection: a restored flagged post whose new `Listing` says `seeking` would come back active. A reclassify keeps a flagged post's flag and state and replaces its `Listing` only (`DECISIONS.md` #144, #217). Not decided (Ron, 2026-10-08) | Gate C |
| The card's main time is the last publication (the latest repost), shown relative: minutes up to an hour, hours up to 24 h, days after that; earlier publications are in the repost log (`DECISIONS.md` #122). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Rooms on a room post: "1 of N" when the total is written, a room with no "of" when it is not; the "1" comes from the apartment kind (`DECISIONS.md` #120). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Size on a room post: "X sqm for the room, of Y" when both are written; "X sqm for the room" when only the room's is (`DECISIONS.md` #121). Not stated: a room post that gives only the apartment's size. Approved by Ron, 2026-10-05 | Phase 3 UI design |
| The entry date's year is never displayed (`DECISIONS.md` #115). Approved by Ron, 2026-10-05 | Phase 3 UI design |

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
| A post that gives only a street: its area rests on what the model knows of Tel Aviv (`DECISIONS.md` #170) | Measured by the regression set's bar on `areas`, 90% by reach (`DECISIONS.md` #198); a street table as an aid is recorded for later (#169) |
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
| Comparing re-encoded photos (perceptual hashing) to find the rewritten reposts the key of #230 misses: in 7 of the 10 `same_listing` pairs no photo file is identical | `DECISIONS.md` #230. Ron decides after he has used the dashboard. No dependency is added for it |
| memo23 failover | `BASELINE.md` §12, phase 6 |
| Editing the schedule and the group list from the dashboard | `BASELINE.md` §12, phase 6 |
| `max_posts` editable by the admin | `BASELINE.md` §11, §12 phase 6. Approved by Ron, 2026-10-04; recorded, not built. One value for all groups (the actor takes one `maxPosts` per run). On save, the system refuses a value where groups × `max_posts` reaches the charge cap's `maxItems`. Open, decided when planned: whether the charge cap itself is editable |
| UI polish from Ron's screenshots | `BASELINE.md` §12, phase 6 |
| A street table as an aid to the model's area (`DECISIONS.md` #169) | Only if the regression set shows the model weak on posts that give a street and no area. The superseded plan is in `PHASE_2.md`'s appendix; the sources in `RESEARCH.md` §12, §14 |
| Gemini's free tier as the model provider | A possible later switch, not planned (`DECISIONS.md` #126; `RESEARCH.md` §13). A free-tier run would need a separate Google project with no billing |
| Yad2 as an additional source | `DECISIONS.md` #60. Open points from the old plan: `RawPost` is Facebook-shaped (`group_id` required, `source` accepts two values); whether structured Yad2 listings pass through the model; dedup across sources; terms of use |
| Comments scraping | Not planned |
| Parallel image downloads, if runs prove too long | Not planned; recorded 2026-10-04 with Ron's approval. Ron chose the 30-minute budget instead (`DECISIONS.md` #77 D5b). Would need its own check for throttling (`ASSUMPTIONS.md` I11 covers sequential requests only), and must keep #77 D3's order inside each group |
