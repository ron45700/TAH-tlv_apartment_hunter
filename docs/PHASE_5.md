# Phase 5 — The server, unattended

**Status (2026-10-19, round 35): DRAFT, for Ron. Nothing is decided and nothing is built.** Points 1–13 below each have
options and a recommendation. Two need Ron's explicit word because they touch a rule: **point 5** (two new records, a Gate
G: invariant 1) and **point 12** (a deliberate skip of a window against invariant 2). Written under the
`external-contract-verification` skill for the Apify cost (§5.1); no call was made, nothing paid.
**Owner:** Ron
**Parent:** `BASELINE.md` §4 (schedule), §5 (lifecycle), §11 (admin), §12 (the Phase 5 row) · **After:** Phase 4 (closed,
`DECISIONS.md` #469) · **Schema:** `SCHEMA.md` (a Gate G is proposed in point 5 below, not written there)

**Phase goal:** the system runs for days with no one at the keyboard. Posts are collected on a schedule Ron sets from the
site; old posts are archived and deleted by rule; every morning Ron gets a digest on Telegram with real numbers and the
real Apify cost; when something stops (a run, a group, the scheduler itself) he is told, once.

**Phase DoD (draft, for Ron; `BASELINE.md` §12 says "two days unattended", #427):**
1. Two days (48 hours, the quiet hours included) with no manual command on the server: the scheduler runs, the digest
   arrives each morning with plausible numbers, nothing is alerted twice, no run is left "running".
2. The interval and the quiet hours are changed from the site and take effect without a restart; "run now" starts a run
   (also in the quiet hours), refuses a second one while one runs, and moves the next scheduled run as #61 says.
3. The retention job, on a dated copy of the server's store first, archives at 25 days and deletes at 40 days from the last
   publication, spares what the rules spare, deletes the photos at archive, and leaves no orphan photo; its dry run
   matches what it then does.
4. A scheduler stopped on purpose, and a group made silent on a copy, each produce the failure alert once.
5. The digest's cost line equals the Apify bill for the same day within a few cents (#449's two open points answered).
6. WAL and the recompute: measured on the server over the two days, and decided (point 13).
7. Tests pin: retention deletes nothing but by its rule (invariant 3) and never edits a `RawPost` (14); the watermark
   rule (2) as point 12 settles it; the token only in the `bot` service and the Apify key only in the commands (#444, #452).

---

## 5.0 Mandatory anchors

| Anchor | Source | State |
|---|---|---|
| Archive at 25 days since the last publication, delete at 40; a repost resets the clock; a repost of an archived post returns it | `BASELINE.md` §5; #46, #63, #74 | Approved |
| Archive deletes the image files and removes their `PostImage` entries; text and `raw` stay | #77 D4b | Approved, not built |
| A flagged post, and a post reported as wrongly classified while the report stands, is never deleted (kept whole, `raw` included; only its images go at archive); a report and a correction are never deleted | Invariant 3; #255 | In force |
| `ViewedPost`, `SentAlert`, `HiddenPost` are deleted with their post | #62, #453, #464 | Approved; no method exists yet (`BACKLOG.md`) |
| A duplicate's retention: its own clock or its canonical's; a stored duplicate pointing at a missing canonical makes `dedup_a` raise | #75 B | Open: point 3 |
| Interval an admin setting, effective at once; "run now"; one run at a time; a manual run resets the timer only when it succeeds | #61 | Approved; the stored record is approved "when Phase 5 is built" (point 5) |
| The daily digest, admin only, on Telegram; green / orange / red, the admin's matches | `BASELINE.md` §11; #359 | Approved |
| Apify's real cost from the charged events or the pricing model, not `usageTotalUsd` | #450 | Approved; the fields verified here (§5.1) |
| `consecutive_failures` counts successful runs in which a group returned zero rows; the thresholds are Phase 5's | #78 W5b; `RESEARCH.md` §9 | Approved; thresholds open: point 9 |
| A run after a pause looks back at most X hours | #443 | Ron's request; conflicts with invariant 2: point 12 |
| Quiet hours 00:00–07:00 Israel time | #442 | In force |
| The scheduler has no Telegram token; the bot has no Apify or OpenAI key; one token holder | #444, #452, #454 | In force |
| The watermark advances only on a successful run | Invariant 2 | In force |

## Order of work (draft)

```
5.1 Gate G: the run record and the schedule record (point 5)      ← Ron's approval first
  →  5.2 the run record written by the commands; settle_costs (points 5, 6)
  →  5.3 retention: archive, delete, user-data cleanup, the sweep (points 1–4)   [free; can start before 5.2]
  →  5.4 the scheduler reads the site's settings; "run now" (points 8, 11, 12)
  →  5.5 the digest, the failure alert, the silent groups, on the bot (points 7, 9, 10)
  →  5.6 the measurements (point 13)  →  5.7 the deploy and the two days (DoD 1)
```

---

## 5.1 What was read (2026-10-19, `external-contract-verification`)

**Apify, documentation** (docs.apify.com/api/v2, "Get run"; the run object): `usageTotalUsd` "Total cost in USD for this
run. Represents what you actually pay"; `usageUsd` "only present if you own the run AND are paying for platform usage",
"not available for standard Pay-Per-Event Actors"; `chargedEventCounts` a map of event name → "the number of times each
event was charged during this run"; `pricingInfo.pricingModel` one of `PAY_PER_EVENT`, `PRICE_PER_DATASET_ITEM`,
`FLAT_PRICE_PER_MONTH`, `FREE`; `pricingInfo.pricingPerEvent.actorChargeEvents` per event `eventPriceUsd` (or tiered);
`platformUsageBillingModel` "which party covers platform usage costs". **"The first response after completion can still
show preliminary `stats`, costs, and event counts … For stable figures, wait about 10 seconds and call the endpoint
again."** Without a token `usageTotalUsd` and `usageUsd` are hidden.

**Apify, our real captured runs** (`data/raw/thedoor_spike_1_1a_2026-10-04_run.json` and `…_control_run.json`, read in
place, no call): `pricingModel` `PAY_PER_EVENT`; `actorChargeEvents`: `apify-default-dataset-item` (title "result")
`eventPriceUsd` 0.0015, and `apify-actor-start` 0.005 ("one event per GB, minimum one event"); `chargedEventCounts`
`{"apify-default-dataset-item": 99, "apify-actor-start": 1}` with `usageTotalUsd` 0.1535 = 99 × 0.0015 + 0.005, and 165 / 1
with 0.2525 = 165 × 0.0015 + 0.005; `usageUsd` null; `platformUsageBillingModel` `DEVELOPER`.

| Detail | What it says | Tag |
|---|---|---|
| A run's cost | Σ over `chargedEventCounts` of count × `eventPriceUsd` from the same run object's `pricingInfo`; `usageTotalUsd` equals it in both captured runs | VERIFIED for the fields and the formula (documentation + two real runs, 2026-10-04) |
| The start fee | `apify-actor-start` was charged once per run on 2026-10-04 | VERIFIED for then; whether it is charged now is #449 point 2 and is **UNKNOWN** until a settled run of the measured day is read |
| "Platform usage only" (#449 point 1, Ron's reading) | In the captured runs `usageUsd` is null and `usageTotalUsd` is exactly the events' sum: the field is not platform usage alone. The end-of-run figure is preliminary (P19) | Fits P19, not the platform-only reading; **not proved for the measured day** (its runs were not captured after settling) |
| The settling time | Documentation: about 10 s; observed on 2026-10-04: still growing at 10–13 minutes (P19) | ASSUMED: read a run's cost no sooner than 15 minutes after it ends, and flag a younger one "provisional" |
| Reading a run later | `GET /v2/actor-runs/{runId}` with the token; the Apify run id of each run is already in the commands' log lines | Documentation; the read itself is free |

**SQLite WAL, documentation** (sqlite.org/wal.html): readers and writers do not block each other, but "there can only be
one writer at a time"; WAL "does not work over a network filesystem"; every process needs write access to the `-shm`
file or its directory; a read-only WAL database is readable since 3.22.0 only if `-wal`/`-shm` exist and are readable, the
directory is writable, or the connection uses `immutable`; **WAL mode is persistent in the file**; the `-wal` file is
recycled at a checkpoint, not truncated, and grows without bound while a reader is always active.

**Telegram** (documentation, `PHASE_4.md` §4.1): a message is 1–4096 characters after parsing; one message a second to
a chat.

**Found in the code:** the stored `RawPost.fetched_at` and `Listing.classified_at` give the digest its per-day,
per-group counts of what was collected and classified without a new field. **No record holds a run** (its rows, its
Apify run id, its charged events, its outcome): the scheduler's log files are the only trace, and they are text. The
scheduler's slots are the multiples of the interval (:00, :30), not "the last run's start plus the interval" that #61
says (point 8). There is no `archived_at`: the archive's moment is `last_published_at` + 25 days, so retention needs no
new field on a post. Photos sit in `<store_root>/images/<listing_id>/<name>.<ext>`.

## 5.2 What I could not verify

- Whether the start fee is still charged, and whether the measured day's logged `usageTotalUsd` ($0.302) is the
  preliminary figure: both need one **free** `GET` of a settled run of the measured day, on the server (the key is
  there). On Ron's go; it makes no charge.
- The per-group silence of the six groups over more days than the laptop's copy holds (it ends on 2026-10-18; the
  server's store was not read).
- That the admin's pages (reports, corrections) cope with a post that retention has deleted: to be read at the build.
- Whether the start event's count depends on memory (one per GB): the captured runs used 1 GB.

---

## 5.3 Points for Ron

Each with options and a recommendation; nothing below is decided.

### Retention

**1. What the retention job is and when it runs.**
- **A. A job command `retention`** (free, no key): dry run by default, `--apply` writes, after a dated backup (as
  `rederive_rejections`); the scheduler runs it with `--apply` once a day inside the quiet hours (after the day's last
  slot, serial and never beside a run, #140). One command does both steps: archive, then delete.
- **B. Two commands** (archive, delete) on separate schedules: more to run, no gain.
- **C. Inside the site or the bot:** a store writer that deletes, in a process that serves users. Against the pattern.
- **Recommended: A.** First on a dated copy of the server's store, its dry run read by Ron; then the scheduler runs it.

**2. The archive step and the delete step, exactly.**
- **Archive** (state `active`, `rejected` or `pending`; `last_published_at` older than 25 × 24 hours, UTC, invariant 9):
  the state becomes `archived`, the rejection reason kept (`BASELINE.md` §5), the post's image files deleted and its
  `PostImage` entries removed (#77 D4b), `raw` and text kept; by compare and set (#260): a record that changed since it
  was read is skipped and counted. A flagged or reported post is exempt from deletion but **not from the archive's image
  deletion** (invariant 3): its images go, its record stays whole.
- **Delete** (older than 40 × 24 hours, not exempt): the `RawPost`, `PostLifecycle` and `Listing` go in one transaction,
  with the post's user-data (point 3). Nothing else deletes (invariant 3).
- **Recommended as written.** No new field: the archive's moment is derived.

**3. Duplicates, user-data, and what outlives its post.**
- **A duplicate's clock (#75 B):** *A.* **follows its canonical's** (a repost already moves the canonical's last
  publication): a duplicate is archived and deleted with its canonical, duplicates first, so `dedup_a` never meets a
  duplicate whose canonical is gone. *B.* its own clock: a canonical could go while a duplicate stays, and the next run
  raises.
- **User-data deleted with the post (#62):** a new `UserDataStore` method deleting `ViewedPost`, `SentAlert` and
  `HiddenPost` for a set of listing ids (three tables, one transaction). **No schema change** (rows only). Reports and
  corrections stay (#255): they hold the field, the model's value and the corrected value, so they need no post; the
  admin's pages must show "post deleted" (to be read and, if needed, fixed at the build).
- **A restored post** follows normal retention (invariant 3); its report and correction stay.
- **Recommended: A,** the method, and the admin's pages tolerant of a missing post.

**4. The orphan-image sweep.** Files under `<store_root>/images/<listing_id>/` that no `PostImage` points at: a run that
failed between the download and the store step (`BACKLOG.md`).
- **A. In the retention job:** a folder whose listing has no record, or a file no entry names, and older than 24 hours (the
  scheduler is serial, but the age is a second guard) is deleted; the dry run prints the count and the bytes.
- **B. A separate command.**
- **Recommended: A.**

### Records, the cost, the digest

**5. (Gate G, a schema change: Ron's explicit approval) The run record and the schedule record.** Invariant 1 forbids
inventing fields; these are **proposals**, written into `SCHEMA.md` only when Ron approves.
- **`RunRecord`** (one per collection run; its own table and layout row, `store.runs` 1, created when absent, as Gate F's
  and `userdata.hidden`: no migration command): `run_id` (the log's), `trigger` (`scheduled` | `manual`), `started_at`,
  `finished_at` (null while running), `status` (`running` | `succeeded` | `failed`), `failure_kind` (the reason, #71 D
  among them; null on success), `rows_fetched`, `rows_skipped`, `window_since` (the run's `since`), `window_capped`
  (point 12), `apify_run_id`, `charged_events` (the map), `cost_usd` (null until settled), `cost_settled_at`. Written by
  `run_once` at its start and its end; `settle_costs` (point 6) fills the cost. It is also the source of the failure alert
  (point 10) and of the site's "last run".
- **`ScheduleSettings`** (one row): `interval_minutes`, `quiet_from`, `quiet_until` (Israel local time as `HH:MM`
  text; conversion only at the schedule, invariant 9), `run_now_requested_at` (null or UTC), `last_digest_at` (UTC; so a
  restart of the bot neither repeats nor skips a digest), `updated_by`, `updated_at`. Written by the site's admin
  endpoints and the bot; read by the scheduler at every slot.
- **A. These two records** (recommended). **B. No `RunRecord`:** parse the scheduler's text logs for the digest and the
  alert (fragile; logs rotate; no place for the settled cost). **C. `RunRecord` as a file** (JSON lines) in the store
  folder: no table, but no compare and set, and the site could not read it safely.
- **Recommended: A.** The store generation counter does not count these tables (the site groups on none of them).

**6. The real Apify cost (#450).**
- **A. `settle_costs`**, a free job command with the Apify key (the scheduler runs it after each classification): for
  every `RunRecord` finished 15 minutes ago or more and not settled, `GET /v2/actor-runs/{id}`; cost = Σ
  `chargedEventCounts` × `eventPriceUsd` from that run's `pricingInfo` (#450), stored in `cost_usd`; the settled
  `usageTotalUsd` is compared and a difference of more than half a cent is logged (not stored), a check of the formula.
  A run younger than 15 minutes shows "provisional" in the digest.
- **B. Read at the end of the run:** wrong by P19 (preliminary).
- **C. Use `usageTotalUsd` of a settled read:** the same number as the events' sum in the captured runs, but #450 chose
  the events; it stays the cross-check.
- **Recommended: A.** The first settled reads of the measured day's runs also answer #449's two points (the start fee;
  why the logged figure was low): a free read, on Ron's go.

**7. The daily digest: who sends it, when, what it holds.**
- **Sender. A:** **the `bot` service** (the one token holder, #444): it composes the digest from the store (read-only for
  posts) and the `RunRecord`s and sends it to the admin's chat. *B.* the scheduler gets the token (against #444 and
  #452). *C.* a job command with the token (a second holder). **Recommended: A.**
- **When:** 08:00 Israel time (after the 07:00 run), once a day; the window is the time since `last_digest_at`.
  *Or:* the previous calendar day. Recommended as written.
- **Holds** (`BASELINE.md` §11, #359, the Phase 5 row, `BACKLOG.md`): per group, collected / deduplicated / classified
  / rejected (from `fetched_at`, `classified_at` and the lifecycle); alerted (`SentAlert`); green, orange and red
  counts (independent of any profile) and the day's new posts that match the admin's own profile (`policy.evaluate`);
  native-price vs model-price mismatches; rows skipped under #71 D; failed runs with their reason; the cost line (point 6:
  the settled runs, and the provisional ones named); the silent-group and failure state (points 9, 10); retention's
  last numbers. Under 4096 characters; a longer digest goes as two messages in order. **Which counts derive from stored
  timestamps and which need the run record** is checked at the build; a count needing a field outside point 5 comes
  back to Ron, not added.
- **Recommended** as written; the exact Hebrew text is shown to Ron as a mock before it is built, as the alert was.

### Collection health

**8. The scheduler's rhythm, and "run now" (#61).**
- **A. Rolling, as #61 says:** the next run is the last run's start plus the interval; a manual run that succeeds moves
  it; one that fails does not. The first run after the quiet hours is at their end. The scheduler reads
  `ScheduleSettings` at every slot, so a new interval or quiet hours apply at once.
- **B. The multiples of the interval** (:00 and :30, as built, #454): a manual run does not move the grid. Simpler in the
  logs; breaks #61's "no scheduled run follows sooner than one interval".
- **"Run now" (site → scheduler):** the site has no Apify key, so it only writes `run_now_requested_at`; the scheduler
  (a loop that wakes every few seconds to read it) starts the run, also in the quiet hours. A request while a run is in
  progress is **refused with the reason on the page** ("a run started 3 minutes ago is in progress"), not queued; one run
  at a time stays the scheduler's own rule (#140). The page shows the last run (`RunRecord`), "running now", and the next
  run's time. A run costs about $0.02–0.03 at the measured size; the button asks once.
- **The `.env` settings** (`RUN_INTERVAL_MINUTES`, `QUIET_FROM`, `QUIET_UNTIL`) become the fallback used while no
  `ScheduleSettings` row exists, then are retired from the stack's `.env`.
- **Moves a Phase 6 item:** `BASELINE.md` §11 and §12 list editing the quiet hours as "later / Phase 6"; this plan edits
  them here, as the brief asks. **`BASELINE.md` §11 and §12 are amended when this is approved.**
- **Recommended: A,** with the page as above.

**9. Silent groups (#78 W5b, `RESEARCH.md` §9).** The counter is built; only the thresholds are open. Measured: a healthy
group went 31 hours without a post; the busiest posts about 73 a day and the quietest about 4; the quiet hours skip runs
and do not count. One threshold for six groups either misses a dead group or flags a quiet one.
- **A. A fixed pair for all groups** (suspect at 8 counted runs, alert at 48): the old plan; flags a quiet group on an
  ordinary day; `RESEARCH.md` §9 itself says it needs recalibrating.
- **B. Per group, from its own stored history:** the alert threshold is the longest gap between two consecutive
  `posted_at` of that group over the stored days (free, read-only) times 1.5, with a floor of 48 counted runs (about a
  day of active hours). The digest lists a group as *suspect* at half its threshold; the alert fires at the threshold.
  Recomputed weekly; the thresholds are printed in the digest's footer.
- **C. As B, plus W4's run-log detection** (a group failing inside a successful run): its own task, needing a small paid
  test (about $0.01) and a provider contract change; **not in this phase** (`BACKLOG.md`'s row stays).
- **Recommended: B,** measured first on the server's store (free) before it is built.

**10. The failure alert (what triggers it, how often).** To the admin on Telegram, from the bot, once per episode and
again only if it still stands at the next digest:
- a collection run failed, 3 in a row (the reason from `RunRecord.failure_kind`: #71 D's "most rows failed to map — the
  provider may have changed its response shape" among them);
- **no run at all** for 2 intervals outside the quiet hours (the scheduler is dead or stuck: the newest `RunRecord` is the
  heartbeat; a `running` record older than the run's deadline plus a margin counts as dead);
- classification failing: pending posts older than 2 hours, or every call of the last pass failed;
- a silent group over its alert threshold (point 9).
- **A. As listed** (recommended). **B. Fewer:** the first two only. The bot can die too, and then nothing alerts:
  recommended guard is the stack's restart policy and the digest's absence (Ron notices no digest); no second watcher.
- The scheduler, with no token (#454), cannot report its own failure: the heartbeat above is how the bot notices it.

**11. Who may change the settings.** The admin only (`require_admin`, the `Origin` check, #330 point 19); an interval
from 5 minutes to 24 hours (what the scheduler already allows); any pair of quiet times; refused values named in Hebrew
on the page. Recommended as written.

### The skip, WAL, measurements

**12. ⚠ The pause rule (#443) against invariant 2. Ron's.** After a pause (the stack stopped for days) a run's window is
the whole gap, bounded only by `max_posts` per group (50): at most the newest 300 rows, within the $0.50 charge cap. Ron
wants a run after a pause to look back at most X hours. But **invariant 2: "a skipped window is a permanently missed
apartment"**; a cap at X is a deliberate skip. What really hurts after a pause is the **burst of alerts** (a post
classified within 24 hours of the pass alerts, whatever its age), not the collection.
- **A. Cap the window at X hours** (Ron's request as written): `since = max(last success − buffer, now − X)`; the cut is
  recorded in `window_capped`, shown in the digest, and invariant 2 amended in words ("except the pause rule"). X = 48
  hours if chosen (the newest 300 rows rarely reach further back).
- **B. No cap on collection; the alert rule ignores a post published more than X hours before the alert pass** (a rule
  in `policy/alert.py`, pure; the post is stored and on the site as always): nothing is lost, no burst. X = 24 hours.
- **C. Both:** B with X = 24, and A with a wide X = 7 days as a last bound (retention archives at 25 days).
- **Recommended: B.** It does what the cap is for without breaking invariant 2. If Ron still wants A, amending the
  invariant is his to word.

**13. WAL, the busy timeout, the recompute (#259, #385).**
- **What is measured**, over the two days on the server: (1) every write that waited more than 1 second for a lock (a
  log line from `sqlite_busy`, no behaviour change) and any `database is locked` error; (2) the grouping recompute's
  duration against the store's size (one log line per recompute); (3) the store's size and post count. Writers now: the
  scheduler's commands, the bot, the site.
- **A. Measure, then decide:** keep the rollback journal if no wait exceeds 1 second and no error appears; switch to WAL
  only if they do. WAL changes the file itself (persistent); it needs the bind mount on one host (it is), write access
  to the folder for every opener (`read_only` openers on a Windows mount would break unless the folder is writable or
  the connection uses `immutable`), and a `-wal` file beside the store (the backups use SQLite's online backup, which
  handles it; restic already excludes `appdata/store/`).
- **B. Switch to WAL now:** fewer waits, but it changes the file and the read-only openers (`move_store`, the labelling
  pages on Windows) before any wait was seen.
- **C. Drop the measurement** (`BACKLOG.md` offered it).
- **Recommended: A.** The measurement is two log lines, no schema.

---

## 5.4 Out of this plan (recorded elsewhere)

- The daily wide run covering 24 hours (about $5 a month, #78 W1): `BACKLOG.md`, still open; Ron may add it as a point.
- W4's run-log detection; groups × `max_posts` and a new group's watermark (Phase 6).
- Friends, sharing, `max_posts` editing, memo23 failover (Phase 6 / written procedures).
- Restic and the server's own backups: homelab's, already in place (#447).
