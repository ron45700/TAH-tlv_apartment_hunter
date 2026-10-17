# The server deployment step — plan

**Status (2026-10-17, round 29): LIVE.** Deployed on `homeserver` by Ron (`DECISIONS.md` #441): steps 1–7 done, the "done means" met (Ron signed in as the admin through `tlvapthunter`; I25 VERIFIED). **Next: step 8, the measured day** (§5, `measure_day.sh`, #445), on Ron's go. §6 waits for the first friend. **Parent:** `BASELINE.md` §12, the "Server deployment" row · **after** Phase 3 (complete, #430) **and before** Phase 4. **Owner:** Ron.

**Scope (#426, #428, #436):** the image on `homeserver`, published from git by the repo's GitHub Action and pulled by
homelab's `stacks/tlv-hunter/` (#420, #433); the site's own tailnet machine `tlvapthunter`, a Tailscale container with
Serve (#419); **a fresh store** on the server (`run_once --bootstrap`, then `create_admin`; the Windows store is not moved,
#436); the `Host`/`Origin` probe and a real sign-in (#422); DoD 6, the measured working day (3.10), on the server (#428).
**Written as a procedure for later** (§6, #440): the sharing rule, the first friend, DoD 2 and 5 on the real store.
**Not here:** the scheduler, archive and deletion, the digest (Phase 5); Telegram (Phase 4).

**Done means (#440):** the site is reached at `https://tlvapthunter.<tailnet>.ts.net`, the probe passes, and Ron signs
in as the admin on the server.

---

## 1. Decided

- **The server's store is `./appdata/store/`** in the stack's folder, a bind mount, with `appdata/labeling`,
  `appdata/gate_d` and `appdata/store_exports`, each `chown`ed once to uid 10001 before the first start (#432).
- **The server's compose file is homelab's `stacks/tlv-hunter/`**, pulling `ghcr.io/ron45700/tah-tlv_apartment_hunter`;
  the repo's `compose.yaml` stays the laptop's; the same image on both (#433, `BASELINE.md` §3).
- **The Action** runs ruff, `pytest -m "not raw_fixtures"` and `npm test`, then publishes on `main`; **Ron's full local
  run is the gate before a server update** (#434).
- **Backups:** restic (Ron is setting it up) backs up `appdata/store_exports/` and `appdata/tailscale/`, never the live
  `appdata/store/`; before each update of the stack, `export_backup` on the server (#435).
- **A fresh store, no move** (#436): the Windows `data/store/` stays on the laptop as the development and regression store
  (the labelled set and its posts).
- **The bootstrap asks 30 posts per group**, 24 hours back (#437): `run_once --bootstrap --max-posts 30`. The regular runs
  keep the configured 50. Each paid run on the server needs Ron's go.
- **The sharing rule** (§6) is approved and applied only when the first friend is added (#438).
- **No real phone number in HEAD** (#439); history is not rewritten.
- Kept from before: the image as built in 3.9 (no `.env`, no `data/`, no tests or docs, uid 10001); the site holds no
  key; `tlvapthunter` serves the tailnet only, never Funnel (#419); nothing served to a friend before the probe and a real
  sign-in (#422, `ASSUMPTIONS.md` I25); never two job commands at once (#140); `reset_admin_password` with the site
  stopped (#424 point 90).

**A fresh store needs no migration (checked in round 28, read-only, on a scratch file):** `run_once --bootstrap`
constructs `SqliteRepository` and `SqliteWatermarkStore`, which lay out `store` 2, `store.listings` 2 and `state` 1 with
the generation counter of #316 (its table, generation 0, and the nine triggers on `raw_posts`, `post_lifecycle`,
`listings`); `create_admin` then lays out `userdata` 2 (the `corrections` triggers) and writes the admin. So
`add_store_generation` is not in the sequence (it refuses such a file: `test_a_new_file_is_already_at_the_new_layout`),
and `create_admin` works on a fresh store (its tests use one, `test_create_admin_job.py`).

### Decided by me (#429)

- **The cap for one run:** `run_once --max-posts N` (1 up to the configured `max_posts`, else refused before anything);
  the run uses a copy of the collection settings with the lower value, so the actor's `maxPosts` and the watermark logic's
  cut-off agree; logged as "max_posts 30 for this run (configured 50)". Two tests.
- **The marker:** `raw_fixtures`, registered in `pyproject.toml`. `tests/conftest.py` marks every test that uses
  `thedoor_items`, `spike_items` or `posts` (directly or through another fixture); 4 files carry it whole
  (`test_dedup_stage_a`, `test_phase0_exit`, `test_premodel_rejects`, `test_run_once`) and 48 other tests one by one, in 12 files.
  Found by running the unmarked set in a copy of exactly the files git holds (no `data/`): **1,108 passed, none failed**;
  873 left out.
- **Item 9's form:** the expected phones of the 20 posts in `data/raw/thedoor_20posts_2026-09-13_phones.json` (a file,
  not hashes: about 10⁸ possible numbers make a hash reversible); the contract test asks the two pairs' numbers from it in
  other forms; the format tests use made-up numbers; the docs show `05X-XXXXXXX`.
- **The keys file:** `jobs.env` for `APIFY_TOKEN` and `OPENAI_API_KEY` (the `jobs` service only), ignored by a
  `.gitignore` in the stack's folder (homelab's root `.gitignore` covers `.env` and `appdata/`, not that name);
  `TS_AUTHKEY` in the stack's `.env`.
- **The sidecar as `dashboard`'s:** `TS_HOSTNAME=tlvapthunter`, `TS_AUTH_ONCE=true`, state in `./appdata/tailscale`,
  `serve.json` from a read-only folder, `TS_USERSPACE=true`, proxy to `http://site:8000`; an untagged, non-reusable,
  non-ephemeral auth key; key expiry disabled by hand. The site keeps `127.0.0.1:8000` on the server only.
- **The Action:** event-seeker's shape (tests, then the image on `main` with `latest` and `sha-<short>`;
  `paths-ignore` `**.md`, `docs/**`), `permissions: contents: read` at the top and `packages: write` on the image job
  only, `persist-credentials: false`, uv 0.12.11 (the lock's).

## 2. What was read (under the `external-contract-verification` skill)

Documentation and source only; no Action has run, no image was pushed or pulled.

| Source | What rests on it | Tag |
|---|---|---|
| GitHub's API, 2026-10-17: each action's latest release and the commit its tag points at | `actions/checkout` v7.0.1 `3d3c42e5…`; `astral-sh/setup-uv` v10.3.0 `1c37ad07…`; `actions/setup-node` v7.1.0 `949feb24…`; `docker/setup-buildx-action` v4.4.1 `f87e5991…`; `docker/login-action` v4.6.0 `dbcb8138…`; `docker/metadata-action` v6.2.0 `dc802804…`; `docker/build-push-action` v7.4.0 `c3c9e263…` | Read |
| Each action's `action.yml` at that commit | Every input used exists under that name (`persist-credentials`, `version`, `enable-cache`, `node-version`, `cache`, `cache-dependency-path`, `registry`, `username`, `password`, `images`, `tags`, `context`, `push`, `labels`, `cache-from`, `cache-to`) | Read; ASSUMED until the first run |
| `docker/metadata-action` README and `src/meta.ts` at that commit | The image name is lowercased (`name.toLowerCase()`): `ghcr.io/ron45700/tah-tlv_apartment_hunter`; it sets `org.opencontainers.image.source`, which links the package to the repository | Read; seen at step 3 |
| docs.github.com (round 27) | `GITHUB_TOKEN` with `packages: write` publishes; a package is private on its first publish; **making it public cannot be undone** | Documentation |
| tailscale.com docker-params, kb/1028; Docker Hub tags (round 27) | `TS_STATE_DIR` must persist; `TS_SERVE_CONFIG` mounted as a folder; Disable Key Expiry per machine; `tailscale/tailscale:latest` = `stable` = v1.104.1 | Documentation; seen working on `dashboard` |
| The `Host` header through Serve | Tailscale's source passes it on | ASSUMED (I25): step 7 |

## 3. The server's stack (built in round 28, `homelab/stacks/tlv-hunter/`)

`compose.yaml` (`site`, `jobs` with profile `jobs`, `tailscale-tlvapthunter`), `.env.example` (`TS_AUTHKEY=`),
`jobs.env.example` (`APIFY_TOKEN=`, `OPENAI_API_KEY=`), `.gitignore` (`jobs.env`), `tailscale/serve.json`; `appdata/` is
git-ignored by homelab's root `.gitignore`. homelab's README has the stack's row and section (first run, updating,
a forgotten password, moving hosts; never `down -v`, never Dockge's Delete). Checked by reading the file: the only published
port is `127.0.0.1:8000`; `site` has no `env_file` and no `environment`; `site` and `jobs` share the image.

---

## 4. The steps

**R** marks what Ron does by hand on the server or in an admin console; I give the commands and check the output with
him. Git is Ron's at every step.

1. **The repository — BUILT (round 28):** #439's change; the marker; `.github/workflows/docker.yml`; `run_once
   --max-posts`. Verified on Windows (§7).
2. **The homelab stack — BUILT (round 28):** §3.
3. **The first publish (R) — DONE 2026-10-17:** Ron commits and pushes both repos. The Action runs on the TLV repo: its test job, then the
   image. On the package page: the image linked to the repository, its name lowercase; **R** makes the package public
   (irreversible; nothing sensitive is in the image). The digest recorded.
4. **The stack on the server (R) — DONE 2026-10-17** (SQLite 3.46.1, I8): `git pull` in `~/homelab`; in `stacks/tlv-hunter/`, the first run's steps 1–3 of
   homelab's README: `.env` and `jobs.env` (`chmod 600`), the `appdata/` folders and their owner, `docker compose pull`,
   SQLite 3.46.1 in the image (I8 on the server). Check that nothing else listens on the server's port 8000 (`ss -ltn`).
5. **The fresh store (R; PAID, each on Ron's go) — DONE 2026-10-17** (219 photos; every post classified but one, which
   failed `invalid` twice and is retried by later runs; the admin `ron45700`; `export_backup` with 219 photos, before #446):
   1. `docker compose run --rm jobs python -m tlv_hunter.jobs.run_once --bootstrap --max-posts 30` — at most $0.50 (the
      charge cap); 6 groups × 30 = at most 180 rows, from the last 24 hours.
   2. `docker compose run --rm jobs python -m tlv_hunter.jobs.classify_pending --cap 0.10`.
   3. `docker compose run --rm jobs python -m tlv_hunter.jobs.create_admin` (free; it asks the username and the password
      twice).
6. **The site and its machine (R) — DONE 2026-10-17:** `docker compose up -d site tailscale-tlvapthunter`; `site` healthy; on the Machines
   page `tlvapthunter` → **Disable Key Expiry**; `TS_AUTHKEY` cleared from `.env`. Ron opens
   `https://tlvapthunter.<tailnet>.ts.net` from his own devices.
7. **A real sign-in (R) — DONE 2026-10-17; the probe was not needed** (#441: a sign-in is a write `check_write` checks
   against `Host`/`Origin`, so it passing is what the probe would have shown; I25 VERIFIED). *As planned:* `POST /api/sign-in` with `{}` and `Origin:
   https://tlvapthunter.<tailnet>.ts.net` → **422** (the `Host` matched); with `Origin: https://example.invalid` →
   **403**; nothing is written. A 403 on the first means Serve rewrote the `Host`: stop, nothing is shared, a fix is
   planned. Then Ron signs in as the admin, saves his preferences, marks a post viewed: I25 VERIFIED. **Done means is met
   here.** Then `export_backup`.
8. **The measured working day (3.10, DoD 6, I3; PAID):** §5.
9. **Close:** `BASELINE.md` §12's row marked done; `ASSUMPTIONS.md` I3 and I25; BACKLOG. Then Phase 4 is planned. §6 waits
   for the day Ron adds a friend.

## 5. The measured working day (3.10) — `measure_day.sh`, on Ron's go (#445)

**The script:** `homelab/stacks/tlv-hunter/measure_day.sh`, run on the server from the stack's folder (its commands and
what they do are in homelab's README, "The measured day"). For 24 hours from its start: a slot every 30 minutes at :00 and
:30, **none starting 00:00–07:00 Israel time** (#442); in each slot, one after the other, `run_once` (the configured 50 per
group, under the $0.50 charge cap, #78 W3) then `classify_pending --cap 0.05`; never two job commands at once (#140). A
failed command is logged and the day goes on; 3 failed collection runs in a row stop it. **Stopping early** (`bash
measure_day.sh stop`) lets the running command finish and then stops: no command is ever killed, so the store is never left
half-written. Every command's output, with a header per slot and the exit codes, goes to `appdata/measure/<start date>.log`.

**The most it can cost:** 34 slots (07:00 to 23:30, 17 hours at two an hour) × ($0.50 + $0.05) = **$18.70 at the caps**, if
every run hit both. Expected far below: with 30-minute windows a run returns few rows (Apify's cost is per row), and each
classification only the posts that are new. The bootstrap's actual figures are in the server's log; the day's totals say.

**Measured and recorded at the end** (`bash measure_day.sh totals`): the slots, the collection runs (done, failed), rows
fetched, posts stored, Apify's cost as each run reported it (`usageTotalUsd`); the classification runs, posts attempted
and their outcomes, model calls, tokens by kind, cost. Then the two bills (Apify's console, OpenAI's usage page) for I3 and
O2; the background recompute and the busy timeout (#385, #259) are judged from the site's behaviour that day; Ron's look at
the interface.

**Tested in round 29 on the laptop, in a local container of the image with a fake `docker compose`** (4-second slots, no
paid call): the aligned slots run serially and end on time; a second start is refused; 3 failed collections stop it; a stop
during a command waits for it, then stops before the classification; the quiet hours (23:30 a slot, 00:00 and 06:30
skipped, 07:00 a slot); the totals from the log; the start works without the file's exec bit; a machine without the
`Asia/Jerusalem` zone is refused (Git Bash on Windows). Not tested: real Docker on the server, a real 24 hours.

## 6. Adding the first friend (a procedure, run the day Ron adds one; #438, #440)

Before: Ron's sign-in has passed (step 7, done); a fresh `export_backup --no-photos`; `measure_day.sh` not running.

1. **The sharing rule (R),** approved as shown (#438), with `tlvapthunter`'s real `100.x` address from the Machines page;
   applied as `03-tailscale-machines.md` says ("Changing the rules safely": copy the current policy first; save; then `ssh
   <USER>@homeserver` from a new window still works):

   ```json
   {
   	"hosts": {
   		"jellyfin":     "100.90.18.96",
   		"homeserver":   "100.80.230.120",
   		"tlvapthunter": "<tlvapthunter's 100.x address, from the Machines page>",
   	},
   	"grants": [
   		{"src": ["autogroup:member"], "dst": ["*"], "ip": ["*"]},
   		{"src": ["autogroup:shared"], "dst": ["jellyfin"],     "ip": ["443"]},
   		{"src": ["autogroup:shared"], "dst": ["homeserver"],   "ip": ["5055", "8765"]},
   		{"src": ["autogroup:shared"], "dst": ["tlvapthunter"], "ip": ["443"]},
   	],
   	"ssh": [
   		{
   			"action": "check",
   			"src":    ["autogroup:member"],
   			"dst":    ["autogroup:self"],
   			"users":  ["autogroup:nonroot", "root"],
   		},
   	],
   }
   ```

   If the policy saved in the console differs from this copy (another change since 2026-10-14), only the `hosts` entry and
   the last grant are added to it.
2. **The share (R):** Machines → `tlvapthunter` → Share; the invite to the friend (a link expires after 30 days). A new
   machine: the friend's shares of `jellyfin` and `homeserver` do not cover it.
3. **The friend:** Tailscale on their phone, the invite accepted; `https://tlvapthunter.<tailnet>.ts.net` opens the list
   as a guest (#306). From their side, `http://100.80.230.120:8000` does not open.
4. **DoD 2 on the real store:** Ron issues a code on the admin's page; the friend signs up with it and signs in. Ron
   issues a second code and cancels it (it stays in the list, cancelled, #243). **The admin's password reset on the
   friend's account, with the friend present**: they sign in with the temporary password and set their own (#262).
5. **DoD 5 on the real store:** a flag → restore on a real post (the restore clears the flag fields); **a report →
   correct → restore only on a post that is truly misclassified**, so the kept report and correction are true (#255); a
   report → leave out the same.
6. **Recorded:** `03-tailscale-machines.md`'s inventory and rules (Ron's docs); `PHASE_3.md` DoD 2 and 5 made for real;
   `SESSION_LOG.md`.

## 7. Verified in round 28 (Windows, offline)

- `uv run pytest`: the full suite, **1983 passed** (10 min 57 s); `uv run ruff check .`: all checks passed; `uv run
  ruff format --check .`: 211 files formatted; `npm test`: 7 files, 84 tests passed.
- The unmarked set in a copy of exactly the files git holds, no `data/`: 1,108 passed, 873 left out, none failed.
- No real phone number left in a tracked file (a search of the working tree for the 8 numbers in any separator form).

## 8. For Ron's own docs (`local_server_docs`, not edited in round 28)

- `02-remote-access/03-tailscale-machines.md`: an inventory row for `tlvapthunter` (sidecar of `homelab/tlv-hunter`,
  HTTPS 443, shared with: nobody yet) once it registers; key expiry disabled; the grant of §6 under "Access rules" when a
  friend is added; "How to connect" row.
- `00-overview/current-state.md`: the `tlv-hunter` stack among the running stacks, 6 stacks managed by Dockge; restic's
  scope including `homelab/stacks/tlv-hunter/appdata/store_exports/` and `appdata/tailscale/`, excluding `appdata/store/`.
- `06-services/homelab.md` (planned): the stack's part, as homelab's README.
- `07-backups/01-restic.md` (being written by Ron): the include and exclude above, and the rule "`export_backup` before
  each update of `tlv-hunter`".
