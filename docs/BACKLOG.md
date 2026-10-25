# Backlog

**The single place that answers "what is open?"**

`BASELINE.md` records *what the system is*. `DECISIONS.md` records *why*. `SCHEMA.md` records *what
is approved*. `SESSION_LOG.md` records *what happened*. None of them tracks whether a decision
actually reached the code, which is how decisions #37 and #38 were approved on 2026-09-14 and were
still unimplemented on 2026-10-02.

**Last updated:** 2026-10-25 (round 49)

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
**Round 18 (2026-10-15): #376–#384 (48–56 as recommended); A (the list in pages), D (the grouping in the background with the removal overlay and "loading") and the counter's pill built; step 7 measured again on today's store and a rebuilt 40-day store: both targets met on both (item 6).**
**Round 19 (2026-10-15): #385–#388 (57 and 58 leave, the recompute measured again at 3.10; 59: S1 and S2 deleted); task 3.7 complete; 3.8's plan written (the admin's pages), points 60–76 wait for Ron; no code (item 6).**
**Round 20 (2026-10-15): #389–#406 (3.8's plan and points 60–76 as recommended; point 66's other option under "Future"); 3.8's build steps 1–3 built (the admin's read API, the read pages, keys and users), checked in Chrome at 1440 × 900 and 390 × 844, Lighthouse accessibility 100 (item 6).**
**Round 21 (2026-10-15): 3.8's steps 4–6 built and checked: the post writes (retry, restore, leave out, remove from the list, the `version`), corrections (the value form, correct, replace, remove, the restore's preview), the DoD 5 walk on a fresh scratch copy (a flag → restore; a report → correct → restore; a report → leave out → restore later), Lighthouse accessibility 100; two layout bugs fixed; the design critique not run (its skills absent); points 77–83 for Ron (item 6).**
**Round 22 (2026-10-15): #407–#414 (77: no design critique for 3.8; 78–83 as recommended; round 21's deviation 1 accepted); 78–83 built (focus into the correction form and back, the live regions, the correction error in Hebrew, focus to the message after a write, each "שחזור" named by its post, the Facebook link 24 px) and a heading-order bug on the flags page fixed; Lighthouse accessibility 100 again, no sideways scroll at 390 (item 6).**
**Round 23 (2026-10-15): Ron walked the admin's pages himself on a dated copy (steps 1–11; DoD 2 and 5 shown on the copy) and closed 3.8 (#415); 3.9's plan written (`PHASE_3.md` 3.9: the image, the compose file, Tailscale Serve, the move to the production store), points 84–95 wait for Ron; nothing built (item 6).**
**Round 24 (2026-10-16): Ron's answers on 84–95 (#416–#424): the store in a named Docker volume (#416); 3.9 on the laptop is Docker locally only, no Serve, no sharing, no friend (#417); DoD 1 reworded (#418); the server gets its own tailnet machine `tlvapthunter` (#419) and is deployed from git (#420), both Phase 5; 87, 92 and the probe through Serve moved to Phase 5 (#422); DoD 2 and 5 accepted as shown on the copy (#423); 88–91, 93–95 as recommended (#424). 3.9's plan rewritten; points 96–97 for Ron; docs only (item 6).**
**Round 25 (2026-10-16): #425 (Phase 3's goal reworded) and #426 (the server deployment comes after 3.10 and before Phase 4); `BASELINE.md` §3 and §12 approved and §12 updated for #426; three stale lines fixed; 3.9's build step 1 built (the code, no Docker): `serve --store`/`--host`, `backup_store` by online backup, `move_store`, `export_backup`, `Dockerfile`, `.dockerignore`, `compose.yaml`, the tests; points 98–102 for Ron (item 6).**
**Round 26 (2026-10-17): #427 (points 98–102), #428 (production runs from the server; the laptop's volume holds a development copy; 3.9's step 3 dropped; DoD 1 reworded; DoD 6 to the deployment step), #429 (less process); the photo export built; 3.9's step 2 run: the image built, I8 and I13 verified, the development copy moved into `tlv-hunter-store` (every check True), the site healthy at `http://127.0.0.1:8000/` and left running (item 6).**
**Round 27 (2026-10-17): Ron opened the site and signed in (DoD 1): Phase 3 complete (#430); #429's wording fixed; the
server deployment step planned in `docs/DEPLOY.md`, points 1–8 wait for Ron; docs only (item 6).**
**Round 28 (2026-10-17): Ron's answers on `DEPLOY.md`'s points (#431–#440): DoD 8 met; the store in `./appdata/store/`; homelab's stack; the marker; restic; **no move, a fresh store on the server** (#436); the bootstrap at 30 a group; the friend as a written procedure. Built: DEPLOY.md steps 1 (the real phones out of HEAD, the marker, the Action, `run_once --max-posts`) and 2 (homelab's `stacks/tlv-hunter/`) (item 6).**
**Round 29 (2026-10-17): the server deployment is LIVE (#441: Ron deployed, bootstrapped and signed in through `tlvapthunter`; I25 VERIFIED); quiet hours 00:00–07:00 (#442); a pause's look-back for Phase 5 (#443); the bot token in the stack's `.env` (#444); `measure_day.sh` built and tested with a fake (#445); `export_backup --no-photos` (#446); the 7 newest backups kept (#447) (item 6).**
**Round 30 (2026-10-18): the measured day done (#448: 34 runs, none failed, 398 rows, 165 posts, $0.044 by the usage metadata); the bills $0.06 OpenAI, $0.90 Apify, about $19–20 a month, accepted (#449; two points left open); Apify's cost from charged events, not `usageTotalUsd` (#450); DoD 6 met, the server deployment complete (#451); Phase 4 drafted in `PHASE_4.md`, points 1–14 for Ron (item 6).**
**Round 31 (2026-10-18): Ron's answers on `PHASE_4.md` (#452–#456; Gate F approved, #453; point 12 replaced by a `scheduler` service, #454); Phase 4 built: the client, the bot service, linking, the alert rules, the message, the report flow, the spike's menu button, `send_test_alert`, the scheduler, the stack's `bot` and `scheduler`; the image built; the real-bot test prepared, not started (item 6).**
**Round 32 (2026-10-18): the real-bot test passed (#457, T5 and T9 VERIFIED) (item 6).**
**Round 33 (2026-10-18): a fix round after Phase 4, not part of its deploy: #458–#467 recorded; built #459 (the "עד
תאריך" fill), #460 (the "i" on a phone), #461 (the home-screen icon), #462 ("back to top"), #463 (the stuck header),
#467 (viewed faded, moved on close); #458 and #464–#466 planned, waiting for Ron (item 9).**
**Round 34 (2026-10-19): appendix A approved as recommended (#468); A.1 ("מיידי" as a rolling marker, `Profile` version 3) and A.2 (hiding) built; rounds 33 and 34 ride with §4.7's deploy (item 9).**
**Round 35 (2026-10-19): Phase 4 closed, DoD 1 met (#469); the `web_app` menu button for every linked chat built (#470; the bot sets it itself, so the deploy is the bot's restart); `PHASE_5.md` drafted, points 1–13 for Ron, point 5 (Gate G) and point 12 (invariant 2) need his explicit word (item 10).**
**Round 36 (2026-10-19): Phase 5 approved (#471–#474: points 1–13 as recommended, Gate G, point 12 as B replacing #443, the quiet hours' editing into Phase 5) and built (5.1–5.6); round 35 corrected (#475); the deploy, the free Apify read, the retention dry run and the two days wait for Ron (item 10).**
**Round 37 (2026-10-19): the public README with screenshots from synthetic data.**
**Round 38 (2026-10-21): Phase 5 CLOSED (#476: every DoD point met or decided; #477 #449 answered, about $24–25 a
month; #478 retention applied; #479 WAL not adopted; #480); built: the new alert (#481), the digest with the groups'
names (#482), the admin's pages in three sections (#483). Follow-up: instructions version 6, streets with their house number (#484, item 14); the doubled "כניסה" dropped for display (#485); `noEmit` and the `.gitignore` line against compiled twins.**
**Round 39 (2026-10-21): the alert's text first and plain, every line opened by U+200F (#487); the digest's dashed headings, bullets, group spacing and four colour lines (#488); for the iPhone.**
**Round 40 (2026-10-22): rounds 38 and 39 deployed on `homeserver` by Ron, the test alert and digest read and approved on his phone: closed. Yad2 opened (#489, amends #60): the read-only spike script written in `data/spike_yad2/`, for Ron to run (item 15).**
**Round 41 (2026-10-24): Yad2 goes ahead (#490: unattended on `homeserver`, headed on a virtual display, a lower daytime rhythm, a block raises the failure alert, terms accepted, no evasion); T12 VERIFIED, T13 closed; spike 2's script written (`data/spike_yad2/spike_yad2_2.py`), for Ron to run (item 15).**
**Round 42 (2026-10-24): Ron's eleven decisions on Yad2 (#491–#501); invariant 13 reworded (#499); `BASELINE.md` §1, §4, §12 (phase 6 is Yad2, the later items phase 7), §13; the README as a product page; `docs/PHASE_6.md` drafted for Ron's approval (item 15); a later round for "the owner" in docs/ (item 16).**
**Round 43 (2026-10-24): `PHASE_6.md` approved, all 25 points (#502–#511); the three phone responses deleted (#505);
Yad2's build step 1 built (the contracts at version 2, the mapping, the 22 kinds); §S2.3 measured and §6.8's numbers
proposed; six points for Ron in §6.14 (item 15).**
**Round 44 (2026-10-24): §6.14 and §6.8 answered (#512–#519); Yad2's build step 2 built (the rules around the model,
the media, dedup kept within a source) and instructions version 7 written; the regression run and the block check
planned, not run (item 15).**
**Round 45 (2026-10-24): C7 answered (#520, a bump adds no repost line); the two paid runs (#521): the block check
passed (O14 VERIFIED, $0.000616); the regression run of version 7 failed on `apartment_kind` ($0.024969): version 7
to be reworded and run again (item 15).**
**Round 46 (2026-10-24): version 8 (#522: the Yad2 section scoped to the block) restores `apartment_kind` and
`areas` ($0.025091); version 7 never deployed (item 15).**
**Round 47 (2026-10-24): version 8 accepted (#523; deployed with the collector, one deploy, one backup); #524 (a bump
returns an archived listing, as #74), #525 (the Yad2 bootstrap's no-alert rule, for step 6); build step 4 built (the
Yad2 seam, on saved pages; no browser run) (item 15).**
**Round 48 (2026-10-25): #526–#532 (no cap on listing pages; Yad2 from 06:00; Facebook first; Yad2 off at the deploy,
its first run the bootstrap; one failed Yad2 run alerts; Playwright's image; the stack and the deploy); build step 5
built (the command, the scheduler, the alert per source, the schedule page, the browser image, the Action, homelab's
stack), not run (item 15).**
**Round 49 (2026-10-25): #533–#535 (the source pill; Yad2's wording; the digest counts Yad2 from what is stored);
build step 6 built (the card, the alert with #525's rule, the digest's Yad2 section); every build step built; the
deploy waits for Ron (item 15).**

| # | Item | Source | Needs |
|---|---|---|---|
| 1 | After 2026-10-08: one free GET on an expired run A photo link, to see what an expired link returns (an HTTP status, or a network error or timeout). No Apify call. Record it under `ASSUMPTIONS.md` I7 (`DECISIONS.md` #80 U5) | `DECISIONS.md` #80 | Approved by Ron, 2026-10-04. The 4-day limit on stored-link retries does not rest on the answer |
| 3 | **Deferred (Ron, 2026-10-09): position 3 keeps failing `furnished` in the regression run.** `DECISIONS.md` #241 (Ron's ruling: `partial`, not `unclear`, on post `0555aa32…`) has no carrier in the set: it needs a Ron-approved changed value of a field measured from the review, a new kind of entry in `label_overrides.json` (a change to its shape) and a few lines in `labeling/regression.py`. Not built now. Ron's reason: not essential, he wants to move on to Phase 3. With that one truth the recomputed verdict of run `47e96cac0e8d` would be `pass` in both passes (`SESSION_LOG.md`, 2026-10-09) | `DECISIONS.md` #238–#241 | Ron, if he ever wants it |
| 4 | **Deferred (Ron, 2026-10-09): the reclassify of the remaining stored `Listing`s is not scheduled.** **This concerns the laptop's development store only: the server's store started fresh at version 5 (#436).** On 2026-10-14 Ron applied four of run `dcb4c0cb4b24`'s proposals (`31bd9205…`, `b330d3fc…`, `d269d280…`, `e6a8b9bb…`, now at version 4; `4c5bbcaf…` left out on purpose, #355); **190 stored `Listing`s are at version 3** (read-only, 2026-10-14). New posts are classified at the current version (5 from 2026-10-14, #354; 6 from round 38's deploy, #484); the old ones leave by retention. Ron decides later whether to reclassify them (`--limit 194 --cap 0.10`, about $0.042, `PHASE_2.md` 2.9). Until then the store holds several versions side by side (#217) | `DECISIONS.md` #144, #217–#222, #355 | Ron, later |
| 7 | **If Ron ever forgets the admin password:** on the server, from homelab's `stacks/tlv-hunter/`, with **the site stopped** (#424 point 90): `docker compose stop site`, then `docker compose run --rm jobs python -m tlv_hunter.jobs.reset_admin_password` in a terminal (it asks the new password twice, hidden), then `docker compose up -d site`; never beside another job command (#140). On the laptop's Windows development store: `uv run python -m tlv_hunter.jobs.reset_admin_password`, with no `serve` running. Built and tested on a temporary store; never run on a real store | `DECISIONS.md` #294; `PHASE_3.md` 3.5; homelab's README | Ron, only when needed |
| 8 | **Instructions version 5 (the studio rule, #354) is accepted (#366, round 15)** on regression run `09f15e8dac9f` (108 calls, $0.024295). New posts are classified at version 5. **#367's four corrected truths are in `corrections.json`** (`62a41d3d…` parking no and furnished `partial`, `71ada783…` `entry_date_written` "כניסה ב18.10", `a7ba462d…` furnished `partial`); the run's verdict recomputed with them (free): **both passes still `fail`**, now on `furnished` 3/9, `parking` 1/9 and `entry_date_written` 1/9 in each pass (version 5 answered on these three posts as version 3 had), and in pass 2 `broker` and `house_committee` 1/9 each; every deciding field clean (`PHASE_2.md`, "Round 15"). **For the next regression run:** the passes disagreed on 23 posts / 29 flips against version 4's 13 / 15, mostly prices not compared; to watch, nothing to change now (#366). **Deferred (Ron, round 15): step 2, reclassifying the 7 stored studio posts, is not scheduled**; they leave by retention. **The stored posts named here are the laptop's development store's only: the server's store started fresh at version 5 (#436)** | `PHASE_2.md`, "Instructions version 5"; `DECISIONS.md` #354, #366, #367 | Ron, at the next regression run |
| 12 | **Ron reads the first applied retention's log line** (the first archive is due about 2026-11-11, the first delete about 2026-11-26): the scheduler's nightly `retention --apply`. Not a blocker | `DECISIONS.md` #478 | Ron, around 2026-11-11 |
| 13 | **"ניתוח מידע" (the admin's data analysis) is a placeholder page** (#483): its content is planned after round 38. Open from Phase 5 for the same planning: whether the digest should carry retention's last numbers (not built: no record holds them, a Gate G change) | `DECISIONS.md` #471, #483 | Ron: the content |
| 14 | **Ron checks v6 streets on real alerts** (#484): instructions version 6 copies a street with its house number; no regression run was made for it (Ron's decision). On the next real alerts, a multi-area post whose text gives a number should show "- רחוב: <street> <number>" with no " (מיקום מדויק לא ודאי)". A number written apart from the name is kept with it, and a number not in the text is dropped with the name kept (#486, amending #162); watch the classify log's dropped-names line for streets still dropped. Stored posts keep their version-5 streets (no reclassify) | `DECISIONS.md` #484, #486 | Ron, on the next alerts |
| 15 | **Yad2 (phase 6, `docs/PHASE_6.md`)**: decisions #489–#535; **every build step built** (1, 2, 4, 5, 6; §6.13–§6.13e), none run on the server; version 8 accepted (#523). Not yet seen running: the browser wrapper (`ASSUMPTIONS.md` Y1) and the browser image (Y3). **Next: the deploy** (step 7, §6.16; Ron: one backup; make the `…-browser` package public; Yad2 turned on from the schedule page), then two days unattended (DoD 1) and Ron's reading of the real cards (#511) | `DECISIONS.md` #60, #489–#535 | Ron: the deploy |
| 16 | **A separate later round (not round 42): "Ron" becomes "the owner" across `docs/`.** Mechanical, the content unchanged; a quote of Ron's becomes "the owner's words". `README.md` already names neither (round 42: "user" and "admin" only) | Ron, round 42 | A round of its own, when Ron schedules it |

### For phase 3 (`DECISIONS.md` #214, #225)

Planned in `PHASE_3.md` (draft, 2026-10-10), §3.

| Item | Source |
|---|---|
| **The background recompute under real traffic and the busy timeout** (#385, #259): **measured on the server and decided (#479):** the recompute 0.66–1.06 s at 640 canonical posts, no write waited over 1 s; the rollback journal stays. Revisit only if a "sqlite write lock" line ever appears | `DECISIONS.md` #385, #471, #479 |
| **The same-listing grouping is derived by the Gate D key** (`DECISIONS.md` #230, rule 1 amended by #232), for the lists, the cards and the repost log, and is never written onto a post (#231). **Built in 3.6 (`dedup/stage_b.py`, 2026-10-11).** Measured read-only on 2026-10-11 (266 posts): the pairing takes under 1 ms (21 ms on 5,004 synthetic members); reading the store and hashing the photos (0.4 s together at the build, 1.0 s in round 5's measurement) are what grow. **How the site holds it (#301) is 3.7's plan** (item 6) | `DECISIONS.md` #231, #301 |
| **The 4 pairs the key finds today, as a first check** of the derivation: `54ecb1d0…` / `00f17259…`, `7253eefa…` / `40f7f193…`, `e81273e6…` / `8ae80944…`, `9136a715…` / `9a6252c1…` (read-only, 2026-10-08, 139 active canonicals; Ron judged all four `same_listing`, #229). No post is in two pairs, and none of the eight has an exact-hash duplicate. **Checked again read-only on 2026-10-11 (round 5, a scratch script) and at 3.6's build (round 6, the built `dedup/stage_b.py`): the four still tie, and nothing else; four cards of two posts** (the store unchanged since 2026-10-08). The check is to be made again once the store holds more days | `DECISIONS.md` #230; `PHASE_2.md` 2.10; `PHASE_3.md` 3.6 |
| **Notes from the dedup B plan worth keeping** (`PHASE_2.md` 2.10, "Plan for dedup B", not built): the agent-number threshold of 4 was a gap in one day's data and is to be re-measured on a week of data with `gate_d_pairs` (the count over every post, duplicates included, would give 3 agent numbers instead of 2); **alerts (Phase 4) must not fire for a post the key ties to an earlier one**; the key reads only active canonical posts that have a `Listing`, so a post waiting for its classification is not tied; a derived grouping follows a change of the key at once, so the key can be revised after Phase 3 | `DECISIONS.md` #230–#232 |
| **The `gate_d_pairs` command runs again on a larger store** (`DECISIONS.md` #226, point 5), to record the rate with its window; it implements the candidate rules, not the key | `DECISIONS.md` #226 |
| **The key's first lists and cards:** the card's main time is the last publication and the repost log shows the earliest `posted_at` (rows under "Recorded for a later phase"); a duplicate's retention follows its canonical (#471 point 3); the key ties cards, not records | `DECISIONS.md` #122, #75 |
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
| #45 sniper removed | Not in the package. Research copies may sit in `data/raw/` (gitignored) | Nothing in code. Ron may delete the research copies |
| #502–#535 Yad2 (phase 6): the Yad2 seam (#507), the second image and the scheduler (#506), the block and version 7 (#503, #511), dedup A not for agency (#508), no `no_text` / `no_images` for Yad2 (#509, #510), `not_listing` by kind before the model, the form/model merge, the store at the end (#502) | Every build step built (rounds 43, 44, 47, 48, 49); version 8 accepted (#523); #524–#535 built (`PHASE_6.md` §6.13–§6.13e) | Nothing to build: the deploy (§6.16), Ron's; the row leaves when the deploy has run |
| #258 the framework: React + TypeScript with Vite, hand-written CSS, `@fontsource`; FastAPI + uvicorn serve the API and the static build; one image, two-stage | Built (rounds 10, 11): FastAPI and uvicorn; `frontend/` with React, TypeScript, Vite, hand-written CSS and the bundled font, served by `serve` | The image (3.9, planned in round 23: `PHASE_3.md` 3.9 (b)) |

---

## Recorded for a later phase

Approved by Ron, 2026-10-04. No code until the phase or gate named.

| Item | When |
|---|---|
| On a card whose media came through a repost (`DECISIONS.md` #70, #72.4), the video link comes from the repost, not from the canonical | Phase 3 UI design |
| The repost log shows the earliest `posted_at` of the post and its duplicates: the stored canonical can be later than a duplicate that arrived after it (`DECISIONS.md` #75 A). The card's main time is the last publication (#122). A display rule | Phase 3 UI design |
| The admin lists (rejected, pending, archive) show canonicals only (`DECISIONS.md` #75 B) | Phase 3 |
| **The run conflict the merge does not cover** (`DECISIONS.md` #292): the run and the site both changed the state and the fresh record has no flag or report; built: the run fails at once (`run_merge.py`). A note from the review: `merge_run_record` keeps the fresh state whenever its reason is `"flagged"` or `"misclassified"`, also when the run was bringing the post back from archive. *(The users' marks deleted with their post are built, round 36, #471.)* The retention job writes by compare and set and skips a changed record | Ron, if the case is ever seen |
| The phone as a candidate signal for dedup B; layer 3 of dedup A produces nothing (`DECISIONS.md` #75 C). **What the key settles:** the phone is a signal, never alone, and never an agent number (#230, #232); dedup B is derived, not stored (#231). **What is left:** dedup A's layer 3 still produces nothing, and nothing writes a phone match onto a post | Phase 3 planning |
| Measure a week of real runs before concluding on volume and monthly cost. Run A, a weekday, returned 212 rows in 24 h with two groups cut off at 50, against the ~125–150 estimated from weekend data (`ASSUMPTIONS.md` P7); the ~$12–16/month Ron accepted may be low. Approved by Ron, 2026-10-04 | Before any conclusion on volume or cost; each run is paid and approved by Ron |
| A daily wide run covering 24 h, about $5/month, to heal a per-group miss within a day (`DECISIONS.md` #78 W1) | Not in Phase 5's plan (`PHASE_5.md` §5.4): Ron, if he wants it |
| Detect a group that fails inside a successful run from the run log, and hold back only that group (`DECISIONS.md` #78 W4). Needs the run-log endpoint verified under the `external-contract-verification` skill, one small test run against an unreachable group (about $0.01; Ron approves it when planned), and `fetch()` returning per-group status (a provider contract change). Rests on P13, ASSUMED | Its own task, when Ron schedules it |
| Groups × `max_posts` must stay below the charge cap's `maxItems` (333 at $0.50); a seventh group at 50 crosses it (`DECISIONS.md` #78 W3) | Planning group editing (phase 7) |
| Adding a group needs a way to create its `GroupWatermark` without a full bootstrap; outside bootstrap a configured group with no record raises (`DECISIONS.md` #78 W7) | Planning group editing (phase 7) |
| The first real refusal, 429, 5xx or timeout from the model is captured into `data/raw/`, and the documentation-based tests compared with it (`DECISIONS.md` #181, `ASSUMPTIONS.md` O13) | When it happens |
| The card's main time is the last publication (the latest repost), shown relative: minutes up to an hour, hours up to 24 h, days after that; earlier publications are in the repost log (`DECISIONS.md` #122). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Rooms on a room post: "1 of N" when the total is written, a room with no "of" when it is not; the "1" comes from the apartment kind (`DECISIONS.md` #120). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| Size on a room post: "X sqm for the room, of Y" when both are written; "X sqm for the room" when only the room's is (`DECISIONS.md` #121). Not stated: a room post that gives only the apartment's size. Approved by Ron, 2026-10-05 | Phase 3 UI design |
| The entry date's year is never displayed (`DECISIONS.md` #115). Approved by Ron, 2026-10-05 | Phase 3 UI design |
| **`measure_day.sh`'s totals still sum the logged `usageTotalUsd`** (#450): the digest's cost line is built from the charged events (round 36); the script changes when next touched | `measure_day.sh` when next changed |
| **The condition of #307:** guests view posts without signing in only because Tailscale is the gate. **If the site is ever served outside the tailnet, signing in becomes mandatory for viewing** (`BASELINE.md` §10). Approved by Ron, 2026-10-11 | Whenever serving outside the tailnet is planned (not planned) |
| **Tailscale sharing is VERIFIED**: no limit on the number of friends on the free plan, nothing paid (`DECISIONS.md` #361; `ASSUMPTIONS.md` I5) | Recorded; no action |

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
| None open | |

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
| A restore of a post rejected by the model through a correction and a re-derivation of its state (`DECISIONS.md` #396, point 66's other option) | Needs a Gate E amendment first (a new lifecycle rule; with #394's other option, a removal re-deriving too). Ron decides after using the admin's pages |
| Favourites (a heart on a card) | `DECISIONS.md` #310: not built in 3.7; a later feature that needs its own record (Gate C has none), approved separately |
| memo23 failover | `BASELINE.md` §12, phase 7 |
| Editing the group list from the dashboard | `BASELINE.md` §12, phase 7. The schedule's editing was built in Phase 5 (the schedule page, #471–#474) |
| `max_posts` editable by the admin | `BASELINE.md` §11, §12 phase 7. Approved by Ron, 2026-10-04; recorded, not built. One value for all groups (the actor takes one `maxPosts` per run). On save, the system refuses a value where groups × `max_posts` reaches the charge cap's `maxItems`. Open, decided when planned: whether the charge cap itself is editable |
| A street table as an aid to the model's area (`DECISIONS.md` #169) | Only if the regression set shows the model weak on posts that give a street and no area. The superseded plan is in `PHASE_2.md`'s appendix; the sources in `RESEARCH.md` §12, §14 |
| Gemini's free tier as the model provider | A possible later switch, not planned (`DECISIONS.md` #126; `RESEARCH.md` §13). A free-tier run would need a separate Google project with no billing |
| Comments scraping | Not planned |
| Parallel image downloads, if runs prove too long | Not planned; recorded 2026-10-04 with Ron's approval. Ron chose the 30-minute budget instead (`DECISIONS.md` #77 D5b). Would need its own check for throttling (`ASSUMPTIONS.md` I11 covers sequential requests only), and must keep #77 D3's order inside each group |
