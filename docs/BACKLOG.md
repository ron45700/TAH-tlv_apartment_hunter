# Backlog

**The single place that answers "what is open?"**

`BASELINE.md` records *what the system is*. `DECISIONS.md` records *why*. `SCHEMA.md` records *what
is approved*. `SESSION_LOG.md` records *what happened*. None of them tracks whether a decision
actually reached the code, which is how decisions #37 and #38 were approved on 2026-09-14 and were
still unimplemented on 2026-10-02.

**Last updated:** 2026-10-15 (round 17)

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
approved, the spike run (#126–#156); the model decides the area (#167); tasks 2.2 to 2.5 built and accepted (#174–#184). Task 2.6 (set, labelling page, runner), 2.7 (review report) built; **2.9 (reclassify, #217-#222) built and accepted by Ron on 2026-10-08; its first real `--run` (five posts) was made on 2026-10-09, no `--apply` yet**; instructions version 3 (the known places, #205, approved #209) passed `areas` by reach in both passes. **The first run over the store (2.8) was made on 2026-10-06** (#213): 194 of 195 pending canonicals classified. **DoD 5 is signed off (#224); DoD 4, the measured working day, moved to Phase 3 (#225).** **Task 2.10 is done: Gate D's key is decided (#230, rule 1 amended by #232); dedup B is not built, its use moves to Phase 3 as a derived result (#231).** **Phase 2's build is closed (Ron, 2026-10-09).** Instructions version 4 are written (2026-10-08, #233–#237, `PROMPT_VERSION` "4") and accepted (#238); its regression run is marked `fail` in both passes only by position 3's `furnished` (#241, deferred, item 3); #239 and #240 narrow what is compared on review and other-city posts. Two items are deferred (items 3 and 4). Every stored `Listing` is still at version 3: nothing has been applied (item 5).

**Phase 3 was opened by Ron on 2026-10-10** and the content of Gate C approved (`DECISIONS.md` #242–#257). On the
same day Ron answered Gate C's 31 open points (#262–#287), chose the technical options (#258–#260), approved the area
grouping (#261), `PHASE_3.md`'s task order and DoD, **Gate C's names and types (#288)** and the plans for 3.4 and 3.5
(#289, #290). **Task 3.4 (store) is built** (round 3). On 2026-10-11 Ron settled 3.4's three open points (#291–#293)
and **task 3.5 (accounts) was built** (round 4). **Ron created the admin on the production store on 2026-10-11** (backup
made; stored `RawPost`s identical). Round 5: `jobs/reset_admin_password.py` built (#294); 3.6's plan written. **Round 6: 3.6's plan and points
approved (#295–#300) and 3.6 built; #301 recorded for 3.7** (item 6). **Round 7: #302 built (a post with no written
price always at the bottom); Ron's direction for the site recorded (#303–#315); 3.7's plan written with 26 points, and a
static mock in `data/mock/`** (item 6). **Round 8 (2026-10-12): 3.7's plan and its 26 points approved with Ron's notes on the
mock (#316–#331); one sublet switch per profile (#317) and the orange-location cap (#320) built; four new points (27–30)
and a new mock** (item 6). **Round 9 (2026-10-12): points 27–30 and Ron's notes on the round-8 mock (#332–#339);
`Profile.from_stored_json`; 3.7's build step 1 built (the store generation counter, `jobs/add_store_generation.py`),
not run on the production store** (item 6). **Round 10 (2026-10-13): Ron ran the migration; Ron's notes on the
round-9 mock (#340–#343); 3.7's build step 2 built (the read-only API for a guest, `web/`, `jobs/serve.py`)** (item 6).
**Round 11 (2026-10-13): `PHASE_3.md`'s lost block restored; #344–#348; 3.7's build step 3 built (the site itself for a
guest, `frontend/`)** (item 6). **Round 12 (2026-10-14): #349–#351 (3.7's rebuilt text and points 33–35 accepted; the
card's buttons packed to the left); 3.7's build steps 4 and 5 built (the filter bar, sign-in, sign-up, the forced
password change, the preferences page, the session cookie)** (item 6). **Round 13 (2026-10-14): #352–#354 (points 36–39;
the phone's bar compacted, built; Ron's studio rule written as instructions version 5, its regression run planned, item 8);
3.7's build step 6 built (viewed, "mark as not viewed", the "lied" flag, the "wrong classification" report)** (item 6).
**Round 14 (2026-10-14): round 13's two errors corrected (the 16:57 write was Ron's `apply_reclassify`, four `Listing`s at
version 4, #355); #355–#365 recorded (Ron's session with the reviewer); O2 and I5 VERIFIED; version 5's regression run made:
both passes `fail` on review fields version 5 did not touch, every deciding field clean, the studio rule followed (item 8).**
**Round 15 (2026-10-14): version 5 accepted (#366); four truths of the studio posts corrected and the run's verdict recomputed
(#367, still `fail` in both passes, item 8); the plan for 3.7's step 7 measurements written, waiting for Ron (item 6).**
**Round 16 (2026-10-14/15): #368-#370 (points 40-42 as recommended); step 7's measurements made on today's store and a 40-day synthetic one: both targets met on today's store, both missed on the 40-day one (warm request 554 ms, first cards 3.0 s, cold 15 s to 2 minutes); Lighthouse, the accessibility review, the colour-vision check and the critique done; nothing changed, Ron chooses (item 6).**
**Round 17 (2026-10-15): #371–#375 (43: A, C, D; 44–46 yes; 47 leave); round 16's scratch stores deleted; C (gzip), the touch areas, the grey and Label in Name with the focus return built and checked at six sizes; A and D planned, waiting for Ron (item 6).**

| # | Item | Source | Needs |
|---|---|---|---|
| 1 | After 2026-10-08: one free GET on an expired run A photo link, to see what an expired link returns (an HTTP status, or a network error or timeout). No Apify call. Record it under `ASSUMPTIONS.md` I7 (`DECISIONS.md` #80 U5) | `DECISIONS.md` #80 | Approved by Ron, 2026-10-04. The 4-day limit on stored-link retries does not rest on the answer |
| 3 | **Deferred (Ron, 2026-10-09): position 3 keeps failing `furnished` in the regression run.** `DECISIONS.md` #241 (Ron's ruling: `partial`, not `unclear`, on post `0555aa32…`) has no carrier in the set: it needs a Ron-approved changed value of a field measured from the review, a new kind of entry in `label_overrides.json` (a change to its shape) and a few lines in `labeling/regression.py`. Not built now. Ron's reason: not essential, he wants to move on to Phase 3. With that one truth the recomputed verdict of run `47e96cac0e8d` would be `pass` in both passes (`SESSION_LOG.md`, 2026-10-09) | `DECISIONS.md` #238–#241 | Ron, if he ever wants it |
| 4 | **Deferred (Ron, 2026-10-09): the reclassify of the remaining stored `Listing`s is not scheduled.** On 2026-10-14 Ron applied four of run `dcb4c0cb4b24`'s proposals (`31bd9205…`, `b330d3fc…`, `d269d280…`, `e6a8b9bb…`, now at version 4; `4c5bbcaf…` left out on purpose, #355); **190 stored `Listing`s are at version 3** (read-only, 2026-10-14). New posts are classified at the current version (5 from 2026-10-14, #354); the old ones leave by retention. Ron decides later whether to reclassify them (`--limit 194 --cap 0.10`, about $0.042, `PHASE_2.md` 2.9). Until then the store holds several versions side by side (#217) | `DECISIONS.md` #144, #217–#222, #355 | Ron, later |
| 6 | **Task 3.7 (the site): build steps 1 to 6 are built.** **To run it: build the pages once with `cd frontend`, `npm ci`, `npm run build` (again after any change to `frontend/`, so this round's pages are served); then from the repository's root `uv run python -m tlv_hunter.jobs.serve` (the newest dated copy in `data/store/site/`; `--copy` makes a new one from the store first) and open `http://127.0.0.1:8000/` in Chrome; sign in with "התחבר".** **To try step 6, signed in:** open a card: it is marked viewed (close it: the card is dimmed with "נצפה"; the list puts it after the unviewed on the next load, a reload or a bar change); in the opened post "סימון כלא נצפה" (on a phone in "פעולות" at the top) takes the mark off. "דיווח" at the left of a card's foot (or of the opened post's foot) opens a small menu: "המודעה משקרת" asks first, then flags every publication of the card and the card leaves the list (try it on a card "פורסם 2 פעמים"); "סיווג שגוי" opens the post with the form: pick the fields, a note if you like, "שליחת הדיווח": the card leaves the list. **Everything stays in the copy (#331)**: a new `--copy` starts from the store again, and the production store never sees a flag or report before 3.9. Sign-up still needs a key from the admin pages (3.8). **Step 7 measured (round 16); Ron chose A, C and D (#371) and points 44–46 (#372–#374). Built in round 17: gzip on every response (the list 458 KB → 70 KB; it adds about 15 ms per warm request today), a 44 px touch area on every small control of the card, the bar and the header (nothing grows), the darker grey, Label in Name, the focus returned to the card on closing a post. Planned, waiting for Ron (`PHASE_3.md` 3.7 (l), "Plan for A", "Plan for D"): A, the first 48 cards with the whole ordered id list and the rest by id as the user scrolls; D, the grouping at start and after a change in the background, the site's own flags and reports removed at once by an overlay; points 48–56 (55: #372 as built; 56: the photo counter's contrast). Round 16's scratch stores are deleted.** The screenshots of round 13 are in `data/ui_checks/r13_*` (gitignored) | `PHASE_3.md` 3.7; `DECISIONS.md` #300-#353, #368-#370 | Ron
| 7 | **If Ron ever forgets the admin password:** `uv run python -m tlv_hunter.jobs.reset_admin_password`, in a terminal (it asks the new password twice, hidden), not beside `run_once` or `classify_pending` (#140). Built and tested on a temporary store; never run on the production store | `DECISIONS.md` #294; `PHASE_3.md` 3.5 | Ron, only when needed |
| 8 | **Instructions version 5 (the studio rule, #354) is accepted (#366, round 15)** on regression run `09f15e8dac9f` (108 calls, $0.024295). New posts are classified at version 5. **#367's four corrected truths are in `corrections.json`** (`62a41d3d…` parking no and furnished `partial`, `71ada783…` `entry_date_written` "כניסה ב18.10", `a7ba462d…` furnished `partial`); the run's verdict recomputed with them (free): **both passes still `fail`**, now on `furnished` 3/9, `parking` 1/9 and `entry_date_written` 1/9 in each pass (version 5 answered on these three posts as version 3 had), and in pass 2 `broker` and `house_committee` 1/9 each; every deciding field clean (`PHASE_2.md`, "Round 15"). **For the next regression run:** the passes disagreed on 23 posts / 29 flips against version 4's 13 / 15, mostly prices not compared; to watch, nothing to change now (#366). **Deferred (Ron, round 15): step 2, reclassifying the 7 stored studio posts, is not scheduled**; they leave by retention | `PHASE_2.md`, "Instructions version 5"; `DECISIONS.md` #354, #366, #367 | Ron, at the next regression run |

### For phase 3 (`DECISIONS.md` #214, #225)

Planned in `PHASE_3.md` (draft, 2026-10-10), §3.

| Item | Source |
|---|---|
| **`ASSUMPTIONS.md` I3 (the model's cost is small), re-planned with DoD 4:** it is the same measurement, so it closes with the working day below | `DECISIONS.md` #228 |
| **DoD 4, the measured working day (moved from Phase 2):** the number of calls, the tokens and the cost of a day's classification, from the usage metadata and then the OpenAI bill; every paid run under its cap. Done once a dashboard exists, so Ron can also judge how the interface looks on that day | `DECISIONS.md` #225; `PHASE_2.md` DoD 4 |
| **The same-listing grouping is derived by the Gate D key** (`DECISIONS.md` #230, rule 1 amended by #232), for the lists, the cards and the repost log, and is never written onto a post (#231). **Built in 3.6 (`dedup/stage_b.py`, 2026-10-11).** Measured read-only on 2026-10-11 (266 posts): the pairing takes under 1 ms (21 ms on 5,004 synthetic members); reading the store and hashing the photos (0.4 s together at the build, 1.0 s in round 5's measurement) are what grow. **How the site holds it (#301) is 3.7's plan** (item 6) | `DECISIONS.md` #231, #301 |
| **The 4 pairs the key finds today, as a first check** of the derivation: `54ecb1d0…` / `00f17259…`, `7253eefa…` / `40f7f193…`, `e81273e6…` / `8ae80944…`, `9136a715…` / `9a6252c1…` (read-only, 2026-10-08, 139 active canonicals; Ron judged all four `same_listing`, #229). No post is in two pairs, and none of the eight has an exact-hash duplicate. **Checked again read-only on 2026-10-11 (round 5, a scratch script) and at 3.6's build (round 6, the built `dedup/stage_b.py`): the four still tie, and nothing else; four cards of two posts** (the store unchanged since 2026-10-08). The check is to be made again once the store holds more days | `DECISIONS.md` #230; `PHASE_2.md` 2.10; `PHASE_3.md` 3.6 |
| **Notes from the dedup B plan worth keeping** (`PHASE_2.md` 2.10, "Plan for dedup B", not built): the agent-number threshold of 4 was a gap in one day's data and is to be re-measured on a week of data with `gate_d_pairs` (the count over every post, duplicates included, would give 3 agent numbers instead of 2); **alerts (Phase 4) must not fire for a post the key ties to an earlier one**; the key reads only active canonical posts that have a `Listing`, so a post waiting for its classification is not tied; a derived grouping follows a change of the key at once, so the key can be revised after Phase 3 | `DECISIONS.md` #230–#232 |
| **The `gate_d_pairs` command runs again on a larger store** (`DECISIONS.md` #226, point 5), to record the rate with its window; it implements the candidate rules, not the key | `DECISIONS.md` #226 |
| **The key's first lists and cards:** the card's main time is the last publication and the repost log shows the earliest `posted_at` (rows under "Recorded for a later phase"); the retention of a duplicate (Phase 5 row) applies to what the key ties | `DECISIONS.md` #122, #75 |
| **3.9: behind Tailscale Serve, check that the `Host` header the site receives matches the browser's `Origin`**, or `web/auth.check_write` refuses every write (403). Verify it at 3.9 before relying on it (Ron's note, round 13; not a decision) | `PHASE_3.md` 3.9; `web/auth.py` |
| **The card's city for an other-city post is derived, not stored:** call `postmodel.rejects.other_city_name(post, seen)` with the post as users see it (`SeenListing`, so a correction of `other_city` in force decides first, #296) (or `other_city_ruling`, which also says whether the city came from a correction, Facebook's location field or the model). For `26e8a28b…` the `Listing`'s `other_city` is null and the card must show "רמת גן". Never read `Listing.other_city` alone for the rejected list or the card | `DECISIONS.md` #214, option A |

### From the first run over the store, 2026-10-06 (for Ron; the stored records were then re-derived on 2026-10-08, #214)

| Item | Source |
|---|---|
| 1 post failed (`json_invalid` twice: the answer was not valid JSON; the bilingual rooftop post `73aebb24…`). It is counted once and retried by the next `classify_pending` run (#139) | `SESSION_LOG.md` 2026-10-06 |
| **Resolved by #214 (2026-10-08):** `2bac260c…` was rejected as `other_city` ("עין ורד", from the text) while the provider's location says Tel Aviv-Yafo and Ron confirms it is a Tel Aviv apartment: it is active now. The model's error stays here, out of the regression count (`corrections_excluded`, #216). Also from the rule: `26e8a28b…` (a Ramat Gan apartment whose text never names the city) is rejected `other_city` and `7d467bbe…` is `other_city`, not `not_listing` | post `2bac260c…` |
| A malformed price ("7,2000₪") became 72,000; the provider's native price is 7,200 and the text's own digits decide (#114). Version 4 adds the sentence (#234): the model should now return the price as unclear, and #114 then keeps it unclear, so the card would show no price (the 7,200 native price is not used) | post `e6a8b9bb…` |
| Two near-identical sublet posts are both canonical (different text, so dedup A keeps both) and both took the provider's price, 1,000, as the monthly rent (a native price of at least 500 is used when the text has none, #114) | posts `9136a715…`, `9a6252c1…`; Gate D |
| One dropped area name: "פלורנטין המערבית" does not match exactly because the text has two spaces; the area [52] was still returned (#162's match is exact, #179) | post `e6a8b9bb…` |
| 12 active posts have no area: 6 give only a street the model could not place (#170), 6 give no location | `SESSION_LOG.md` 2026-10-06 |
| A post that says only "Jaffa" returns all 8 Jaffa areas (the examples of #88); one post has 5 areas and one has 4 | `SESSION_LOG.md` 2026-10-06 |

---

## Decisions pending implementation

| Decision | State of the code (checked 2026-10-04) | What has to change |
|---|---|---|
| #142, #143, #157, #171, #172, #177, #183 the regression set, run twice at effort `none`, temperature 0; the labelling page (areas picked from the 71; `other_city` labelled blind; no controls for streets and area names) and the review report (errors per field; streets and area names judged there only; the dropped-names files of `classify_runs/`; corrected posts join the regression set), in `data/labeling/` | Built: the set, the labelling page, the runner (`label_overrides.json`, #196) and the review report (2026-10-06). Version 3 passed `areas` in both passes; `gender` failed in pass 2 and pass 1 was incomplete. Version 4 ran on 2026-10-08, accepted by Ron (#238); position 3's `furnished` still fails (#241, deferred, item 3) | Ron signed off the review of the first run (DoD 5, #224); what remains is the review of pass 1 (`review_page --run`, #193). The row leaves when Ron accepts the set |
| #144, #217–#222 reclassify: two commands (`jobs/reclassify.py`, paid, store read-only, writes the diff report and two list files; `jobs/apply_reclassify.py`, free, the fourth store writer, `--allow` / `--allow-file`, no apply all); `find_reviewed` reads the replaced `Listing`s | Built 2026-10-08 and accepted. The first real `--run` was made on 2026-10-09 (five posts, item 5). No real `--apply`: it waits for Ron's go. The remaining 189 are not scheduled (item 4) | Ron's reading of `diff.html`, then his go for `--apply` (item 5) |
| #77 D4b archiving deletes the image files and removes their `PostImage` entries | Nothing exists; task 1.12 already reads a record archived before #74 without counting its old entries (#77 D4) | Phase 5, the archive job |
| #46 archive and deletion | Nothing exists | Stored shape approved at Gate E (#63); the jobs in phase 5 |
| #45 sniper removed | Not in the package. Research copies may sit in `data/raw/` (gitignored) | Nothing in code. Ron may delete the research copies |
| #51, #52 filter model and alert rules | The evaluation built (3.6, `policy/`, 2026-10-11); alerts not | Alerts in phase 4 |
| #56 the bot listens | `notify` is a stub | Phase 4 |
| #61 admin-set run interval and a manual "run now" | No scheduler exists | Phase 5, with the scheduler. Interval and last-run record approved then |
| #242–#244 accounts: username and password, no email, admin reset; one-time keys (no expiry, cancel, label, used by and when); one admin created by a command | Records, storage (3.4), logic (3.5, `accounts/`, `jobs/create_admin.py`, `jobs/reset_admin_password.py`, #294); the cookie and the pages (sign-in, sign-up, the password change) built in 3.7 steps 4–5 (round 12) | The admin's key and user pages (3.8) |
| #251, #281–#283 restore: one rule for flagged and reported posts; removes the flag or reports only; the state derived from the corrected values; an archived post stays archived | `PostLifecycle` v3 and `"misclassified"` built (3.4); the derived record built (3.6, `postmodel/rejects.restored_lifecycle`); the writes are not | Gate E amendment E-3 (proposed); `PHASE_3.md` 3.4, 3.8 |
| #254–#256, #296 the "wrong classification" report, its retention, the admin's corrections (a correction of `other_city` outranks the native location) | Records and storage built (3.4); the corrections applied wherever a post is read for a user (3.6); the report itself and its form built (3.7 step 6, round 13: `web/writes.py`) | The correction pages (3.8). The retention exemption is applied by phase 5's job |
| #257 the polished UI in phase 3 | The list and the opened post (step 3), the bar, sign-in and the preferences page (steps 4–5), viewed, the flag and the report (step 6, round 13), each with `frontend-design` | Step 7 made (round 16); #372–#374 built (round 17); the photo counter's contrast (point 56) and #372 as built (point 55) wait for Ron |
| #258 the framework: React + TypeScript with Vite, hand-written CSS, `@fontsource`; FastAPI + uvicorn serve the API and the static build; one image, two-stage | Built (rounds 10, 11): FastAPI and uvicorn; `frontend/` with React, TypeScript, Vite, hand-written CSS and the bundled font, served by `serve` | The image (3.9) |
| #259 the busy timeout (10 s, `sqlite_busy.py`) is built (3.4); WAL reconsidered in Phase 5 | Built 2026-10-10: every connection passes it | Measured on the working day (3.10). The row leaves then |
| #262–#266, #291 accounts: opaque `user_id`, the username's rules, Argon2id with 8 characters minimum, the admin's temporary password; sessions of 30 days, ended by a reset; the delay after 5 failures; disable (then end the sessions, #291), never delete; keys shown once, never un-cancelled | Built 2026-10-11 (3.5); the cookie built and read in a test and in Chrome (3.7 step 5, round 12: `HttpOnly`, `Secure`, `SameSite=Strict`, 30 days) | The admin's pages (3.8): reset, disable, keys |
| #276–#280, #284–#287 viewed (first time kept); the report's fields and 500-character note, one open report per reporter, `"misclassified"` last, `flagged_by` the first reporter; corrections stored and removed; `PostLifecycle` v3; left out not final; the Gate D key on corrected values | Built: records and storage (3.4), the key on corrected values (3.6), viewed and the report's writes and form (3.7 step 6, round 13) | The admin's corrections and restore (3.8) |
| #321–#330 the display rules from Ron's answers | Built in steps 3–6 (rounds 11–13), the report button included | The 40-day measurement (step 7) |
| #345, #346 the cold grouping and the list's size are measured at step 7 before anything changes (precomputing the grouping; sending the first lines only) | Ron chose A and D with C (#371, round 17); A and D planned, waiting for Ron (points 48–54); #346 (first lines) not taken | Step 7's measurement (`PHASE_3.md` 3.7 (h)) |
| #371 A the list in pages (first 48 cards, the ordered ids, the rest by id) and D the grouping in the background with a removal overlay | C built (round 17); A and D planned (`PHASE_3.md` 3.7 (l)) | Ron's points 48–54, then the build and step 7's measurement again |
| #331 until 3.9 the site runs on a dated copy of the store; what Ron saves there stays in the copy | Built: `serve` serves a dated copy only (round 10); from step 5 the site writes the copy's user-data tables (round 12) | 3.9 |

---

## Recorded for a later phase

Approved by Ron, 2026-10-04. No code until the phase or gate named.

| Item | When |
|---|---|
| The failure alert to the admin names the reason for a failed run (for example, most rows failed to map — the provider may have changed its response shape, `DECISIONS.md` #71 D) | Phase 5 |
| The digest reports the rows skipped below the #71 D ceiling | Phase 5 |
| On a card whose media came through a repost (`DECISIONS.md` #70, #72.4), the video link comes from the repost, not from the canonical | Phase 3 UI design |
| Image files with no `PostImage` pointing at them: written by a run that failed after the download and before the store step, for a post that never comes back. A sweep of unreferenced files under `<store_root>/images/` (`DECISIONS.md` #77, plan §3) | Phase 5 |
| The repost log shows the earliest `posted_at` of the post and its duplicates: the stored canonical can be later than a duplicate that arrived after it (`DECISIONS.md` #75 A). The card's main time is the last publication (#122). A display rule | Phase 3 UI design |
| The admin lists (rejected, pending, archive) show canonicals only (`DECISIONS.md` #75 B) | Phase 3 |
| **The run conflict the merge does not cover** (`DECISIONS.md` #292): the run and the site both changed the state and the fresh record has no flag or report; built: the run fails at once (`run_merge.py`). Look at it again with the retention job. Two notes from the review: (a) `merge_run_record` keeps the fresh state whenever its reason is `"flagged"` or `"misclassified"`, also when the run was bringing the post back from archive; (b) `ViewedPost` records are "deleted with their post" (#62) but `UserDataStore` has no method for it yet | Phase 5, the retention job |
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
| The card's main time is the last publication (the latest repost), shown relative: minutes up to an hour, hours up to 24 h, days after that; earlier publications are in the repost log (`DECISIONS.md` #122). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Rooms on a room post: "1 of N" when the total is written, a room with no "of" when it is not; the "1" comes from the apartment kind (`DECISIONS.md` #120). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Size on a room post: "X sqm for the room, of Y" when both are written; "X sqm for the room" when only the room's is (`DECISIONS.md` #121). Not stated: a room post that gives only the apartment's size. Approved by Ron, 2026-10-05 | Phase 3 UI design |
| The entry date's year is never displayed (`DECISIONS.md` #115). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| **The condition of #307:** guests view posts without signing in only because Tailscale is the gate. **If the site is ever served outside the tailnet, signing in becomes mandatory for viewing** (`BASELINE.md` §10). Approved by Ron, 2026-10-11 | Whenever serving outside the tailnet is planned (not planned) |
| **On linking Telegram, one message:** "N posts currently match your preferences", with a link to the site; for every user (`DECISIONS.md` #358) | Phase 4 |
| **The daily digest adds** green (active, price, location and kind clear), orange (active, one of the three unclear or missing), red (rejected), independent of any profile, and the count of the day's new posts matching the admin's own profile; admin only, to Ron on Telegram (`DECISIONS.md` #359; `BASELINE.md` §11) | Phase 5 |
| **A post whose kind is unclear or not written never alerts**; it stays on the site at the bottom (#273) (`DECISIONS.md` #360) | Phase 4 |
| **Tailscale sharing is VERIFIED**: no limit on the number of friends on the free plan, nothing paid (`DECISIONS.md` #361; `ASSUMPTIONS.md` I5) | Recorded; no action |
| **The model's cost matches the OpenAI bill** (`ASSUMPTIONS.md` O2 VERIFIED, `DECISIONS.md` #362); I3 closes with the measured working day | 3.10 |
| **The alert's layout** (`DECISIONS.md` #363): the first photo; kind (+ sublet), price, neighbourhood, street when written, rooms ("1/2.5" on a room post), entry date; only the user's set categories, 🟢/🔴/🟠/⚪; "⚠️ חסר: …" for a critical category not written; 🔴 "women only" when that filter is off; the relative time; buttons: the site (later the Mini App), Facebook, WhatsApp (with a mobile), report. No save, no map. The exact template and Telegram's caption limits verified when Phase 4 is planned (`external-contract-verification`) | Phase 4 |
| **The alert's "report" button** offers "lied" and "wrong classification" (fields by buttons, note optional), written as the linked user by the site's rules (#260, #300) (`DECISIONS.md` #364) | Phase 4 |
| **The bot's menu button opens the site** (later the Mini App); works only with Tailscale on the phone; covered by the Mini App spike (`DECISIONS.md` #365; `ASSUMPTIONS.md` T5) | Phase 4 |

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
| Telegram library | Planning phase 4 |
| How the scheduler runs inside the container. It must be interval-based (the interval is an admin setting) and support a manual run that resets the timer on success (`DECISIONS.md` #61). One run at a time: a run can last longer than the 30-minute interval, since the image download alone may take up to 30 minutes (#77 D5b). `run_once` takes no lock; a run overtaken by a later one fails at `advance` and moves no watermark (`DECISIONS.md` #79 O9) | Planning phase 5 |

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
| Favourites (a heart on a card) | `DECISIONS.md` #310: not built in 3.7; a later feature that needs its own record (Gate C has none), approved separately |
| memo23 failover | `BASELINE.md` §12, phase 6 |
| Editing the schedule and the group list from the dashboard | `BASELINE.md` §12, phase 6 |
| `max_posts` editable by the admin | `BASELINE.md` §11, §12 phase 6. Approved by Ron, 2026-10-04; recorded, not built. One value for all groups (the actor takes one `maxPosts` per run). On save, the system refuses a value where groups × `max_posts` reaches the charge cap's `maxItems`. Open, decided when planned: whether the charge cap itself is editable |
| A street table as an aid to the model's area (`DECISIONS.md` #169) | Only if the regression set shows the model weak on posts that give a street and no area. The superseded plan is in `PHASE_2.md`'s appendix; the sources in `RESEARCH.md` §12, §14 |
| Gemini's free tier as the model provider | A possible later switch, not planned (`DECISIONS.md` #126; `RESEARCH.md` §13). A free-tier run would need a separate Google project with no billing |
| Yad2 as an additional source | `DECISIONS.md` #60. Open points from the old plan: `RawPost` is Facebook-shaped (`group_id` required, `source` accepts two values); whether structured Yad2 listings pass through the model; dedup across sources; terms of use |
| Comments scraping | Not planned |
| Parallel image downloads, if runs prove too long | Not planned; recorded 2026-10-04 with Ron's approval. Ron chose the 30-minute budget instead (`DECISIONS.md` #77 D5b). Would need its own check for throttling (`ASSUMPTIONS.md` I11 covers sequential requests only), and must keep #77 D3's order inside each group |
