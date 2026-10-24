# TLV Apartment Hunter — Baseline

**Status:** Approved by Ron, 2026-10-02. Amended 2026-10-03 after the cross-check of the other docs.
Amended 2026-10-04: run interval and manual run (`DECISIONS.md` #61), viewed posts (#62), Gate E
(#63), the SQLite file shared by `store` and `state` (#64, #65), "no images" means no media at
all (#67, #68), a `no_text` post that comes back with text (#69), media that arrives through a
repost (#70), the pre-model rejects' open cases (#72), text normalize before the pre-model
rejects (#73), the state a repost of an archived post returns to (#74), and dedup A's canonical
rule (#75).
Amended 2026-10-05: the source of areas and streets and who decides the area (`DECISIONS.md`
#81–#88), and the Gate B content that touches §4, §6 and §7 (#89–#107); §13's row on flagged posts
corrected to §5. Amended again 2026-10-05: Ron's answers on Gate B (#108–#119) in §6 and §7, and
three card rules (#120–#122) in §6. Amended again 2026-10-05: Gate B's last two points (#123,
#124) in §6–§7; OpenAI as the model provider and provider-neutral rules (#126, #129) in §4 and §12. Then the
spike's decisions: the setting (#157) in §4, prefix letters and names not in the text (#158, #162)
in §7. Then the model decides the area (#167–#170): §4 and §7 rewritten.
Amended 2026-10-08: Gate D's key (`DECISIONS.md` #230, amended by #232) and that dedup B's result is
derived from the stored posts, not stored, with its use in Phase 3 (#231): §4 and §12.
Amended 2026-10-10: the content of Gate C (`DECISIONS.md` #242–#257): §5 (the restore rule, the "wrong
classification" report and its retention, the admin's corrections), §8 (two search options, sublets, the sqm filter,
the area filter, the area's colour per user, the viewed trigger) and §12 (Gate C's state; the polished UI moves from
phase 6 to phase 3).
Amended again 2026-10-10 (round 2): Ron's answers (`DECISIONS.md` #258–#287): §3 (the eighth seam's interface), §5
(restore, one rule for flags and reports, from the corrected values), §7, §8 (the profile's defaults and values, the area
grouping), §9 (the search options), §10, §11, §12 (the phase's name, the choices made), §14.
Amended 2026-10-11: §4 (the same-listing grouping is computed once for all users and held in memory, #301), §5 and §14
(stale lines: Gate C approved), §8 (the order of display: an unknown preference counts as not met, #298; parking not
written is unknown, #299).
Amended again 2026-10-11 (round 7): §6 (the field colours, #309), §8 (a post with no written price at the bottom, #302;
the saved preferences and the home page's filter, #314, #315), §10 (guests view without signing in; Tailscale the only
gate for viewing, with its condition, #306, #307).
Amended 2026-10-12 (round 8): §5 (the stale line on the reported reason's name, approved as `"misclassified"`, #288),
§6 ("not stated" in grey for every attribute not written, #321; the closed card shows only green chips, #326), §8 (one
sublet switch per profile, #317; an orange location caps the tier at the middle, #320; no green glow while the option
holds no preference, #322), §9 (the sublet switch, #317).
Amended again 2026-10-12 (round 9): §8 (the bar resets to the saved preferences; "save as my preferences" removed for
now, #335, amending #315).
**Amended 2026-10-16 (round 24; approved by Ron in round 25):** §3 (the laptop serves the site locally only; on the home server
the site gets its own tailnet machine, `tlvapthunter`; deployed from git; `DECISIONS.md` #417, #419, #420) and §12 (Phase 3's
line reworded, #418; Phase 5's row: `tlvapthunter`, Serve, the `Host`/`Origin` check, DoD 2 and 5 on the real store, deploy
from git, #419–#423; the laptop for development, #417).
Amended again 2026-10-16 (round 25): §12 (the server deployment step between Phase 3 and Phase 4, taken from Phase 5,
`DECISIONS.md` #426; Phase 5's row keeps the rest) and §14 (the Mini App spike against `tlvapthunter`, #426).
Amended 2026-10-17 (round 26): §12 (Phase 3's line over a copy of the store; the store moved once into the server's
volume and the measured working day at the deployment step; "first friend connected" there; `DECISIONS.md` #427, #428).
Amended 2026-10-18 (round 30): §12 (the server deployment row marked done, `DECISIONS.md` #451).
Amended again 2026-10-18 (round 31, Ron's answers on `PHASE_4.md`): §9 (alerted only on posts first stored after linking
Telegram, #452 point 10), §4 (quiet hours 00:00–07:00, #442; the bridge scheduler, #454), §12 (Phase 4 built).
Amended 2026-10-19 (round 36, Phase 5 approved, `DECISIONS.md` #471–#474): §4 (the schedule is the admin's, rolling;
no cap after a pause, old posts never alert), §5 (retention's details), §11 (the schedule page; the quiet hours moved
from "later"), §12 (Phase 5 built; Phase 6 no longer holds the quiet hours).
Amended again 2026-10-17 (round 28): §3 (the same image, not the same compose file, #433; the server's store in
`./appdata/store/`, #432) and §12 (the deployment row: a fresh store, the first friend as a procedure, the new "done
means", `DECISIONS.md` #436–#440).
Amended 2026-10-24 (round 42, Yad2, `DECISIONS.md` #489–#501): §1 (Yad2 the second source), §4 (Yad2's path, what is
decided only), §12 (phase 6 is Yad2, planned in `PHASE_6.md`; the later items move to phase 7), §13 (Yad2's own
scraper). What `PHASE_6.md` still proposes (names, tables, numbers) is not here.
Amended 2026-10-24 (round 43, `PHASE_6.md` approved, `DECISIONS.md` #502–#511): §3 (the scheduler in a second image with
the browser, #506), §4 (Yad2's own seam, #507; the block's content, #503; dedup A not for agency listings, #508; no
`no_text` or `no_images` rejection for Yad2, #509, #510; the regression run, no Yad2 labelled set, #511), §5 (the two
rejection rows), §12 (phase 6 approved). The paging numbers and the rhythm (`PHASE_6.md` §6.8) are still proposals.
**Owner:** Ron

> This file is the description of what the system is and how it is built. It replaces
> `HANDOFF.md` and `MACRO_PLAN.md`, which are in `docs/archive/` and describe the old direction.
> Research findings that still hold (providers, field map, traps, test results) are in
> `docs/RESEARCH.md`.
>
> `SCHEMA.md` stays the only source of truth for field names and types. This file states
> **requirements**; it does not name fields. Names and types are settled at the gates (§12).

---

## 1. What this is

A personal, non-commercial tool for Ron and a few close friends. It collects rental posts from
public Tel Aviv apartment Facebook groups, classifies each post once with an LLM, shows them in a
dashboard with per-user filtering, and pushes a Telegram alert when a new post matches a user's
saved profile.

**The problem it solves:** manually scanning several groups several times a day for the few posts
that fit.

**Sources:** Facebook public groups through Apify actors. The group list is one shared list: every
user sees posts from all of them. Editing the list from the dashboard is a later addition. **Yad2 is
the second source** (`DECISIONS.md` #489–#501): Tel Aviv-Yafo rental listings of every kind,
private and agency, collected by its own scraper, a headed browser on the home server, unattended,
at a lower daytime rhythm than the Facebook runs (#490, #491). Each card shows its source (#500).

---

## 2. Principles

| # | Principle |
|---|---|
| 1 | No Facebook account, no login, no cookies. Public groups only, through Apify. |
| 2 | Provider adapter layer. Two providers (thedoor primary, memo23 backup) sit behind one interface; past it, no module knows which provider the data came from. |
| 3 | The LLM classifies; all filtering is done on structured fields. |
| 4 | The model classifies only. It never summarizes and never adds text of its own. |
| 5 | "Not written" is information, not failure. It is kept distinct from "unclear" (§6). |
| 6 | Collection is shared; evaluation is personal. A post is fetched and classified once. Filtering, ordering and alerts are computed per user over the stored fields, with no extra model call. |
| 7 | No keyword sniper. It is removed from the project, not kept dormant. |
| 8 | Every external tool, API or data source is verified against its own current documentation before anything is built on it. Tags: `VERIFIED` / `ASSUMED` / `UNKNOWN`. Nothing is built on `ASSUMED`. |
| 9 | No schema, field or filter rule is created or changed without Ron's approval (gates, §12). |
| 10 | Post comments are not collected. Both comment flags are set off explicitly. |
| 11 | Retention is bounded (§5). This replaces the old rule "nothing is ever deleted". |

---

## 3. Hosting

| Item | Decision |
|---|---|
| Machine | Ron's home server (a laptop being converted), running 24/7. Development and first runs on Ron's personal laptop. |
| OS | Ubuntu Server LTS or Debian, no desktop. |
| Runtime | Docker Compose. **The same image runs on the personal laptop and on the server (#433)**: the laptop's compose file is the repo's `compose.yaml`, which builds it; the server's is homelab's `stacks/tlv-hunter/`, which pulls it from ghcr. *Until 2026-10-17: "The same compose file runs on the personal laptop and on the server."* **Every command that opens the store runs in a container (#416); on the laptop the store is in a named Docker volume, on the server in the stack's `./appdata/store/` (#432).** The server's deployment is from git; never `.env` or the volume in git or the image; an update never touches the volume; a backup before each update (#420, Phase 5). **From phase 6 a second image** holds the headed browser for Yad2; the `scheduler` service runs from it, every other service from the slim image, and the GitHub Action builds both (#506). |
| Database | SQLite, one file, behind the `store` interface (posts and their lifecycle records), the `state` interface (per-group watermarks) and, from phase 3, a third interface for what users and the admin write through the site, `userdata/` (`DECISIONS.md` #267, #289). The rollback journal with an explicit busy timeout in phase 3 (#259). Postgres stays a cheap swap. |
| Images | Downloaded at fetch time to a directory on disk (Facebook image links expire within days). |
| Remote access | Tailscale, **on the home server only** (amended 2026-10-16, #417, #419). The site gets its own tailnet machine, `tlvapthunter`: a Tailscale container beside the site on `homeserver`, publishing it with Tailscale Serve (HTTPS, tailnet only). Friends are shared `tlvapthunter` only (device sharing). **The laptop is for development: the site there is served on 127.0.0.1 only, with no Serve and no sharing;** no one but Ron uses the system before it runs on the server. *Until 2026-10-16: "The dashboard is published with Tailscale Serve (HTTPS, tailnet only). Friends get access through Tailscale device sharing."* |
| Telegram | Outbound only: long polling (`getUpdates`) and send calls. No public address or open port. |
| Fallback | GCP, as in the original plan, if the home server proves unworkable. |

Each friend needs a Tailscale account and the app active on every device they use for the
dashboard or the Mini App. Telegram alerts arrive regardless.

Laptop-as-server settings: no suspend on lid close, battery charge limit if the BIOS allows,
power-on after power loss, wired network.

---

## 4. Data path

```
scheduler -> Apify (thedoor) -> provider normalize -> text normalize -> pre-model rejects
          -> dedup A -> image download -> store ("pending")
          -> the model (extraction, the area included) -> rejection derived by code
          -> update the stored post
          -> dedup B: the same listing, derived by the Gate D key, not stored (phase 3)
          -> per-user evaluation -> Telegram alert
```

- **Stored before the model** (`DECISIONS.md` #79): in phase 1 the post is stored before the
  model, as `"pending"`; the model updates the stored post later.
- **Schedule:** every 30 minutes by default. No scheduled runs between **00:00** and 07:00 Israel
  time (#442; *until 2026-10-18: 01:00*). The 07:00 run covers the whole night: its window starts at the last successful
  run. **From Phase 4 a `scheduler` service runs on the server** (#454); **from Phase 5 the interval and the quiet
  hours are the admin's, set on the site's schedule page** (Gate G's `ScheduleSettings`, #472, #474) and read by the
  scheduler at every pass; its `.env` values only write the first row. **After a pause** a run looks back over the
  whole gap, bounded by `max_posts` per group, and a post published more than 24 hours before the alert pass never
  alerts (#473, replacing #443).
- **Interval and manual run** (`DECISIONS.md` #61, phase 5): the interval is an admin setting, and
  a change takes effect at once — the next run is the last run's start plus the new interval. The
  admin can start a run now, also during the quiet hours. A manual run is an ordinary run; when it
  succeeds, the next scheduled run is its start plus the interval, and when it fails the timer is
  not reset. One run at a time: a manual request during a run is refused or waits, and two runs
  never overlap. *Built in round 36 (#471): a request during a run is refused on the page; one older than 15 minutes
  is not started.*
- **Watermark:** per group, the highest post time seen, never moving backwards. The run's window
  starts at the last successful run's start minus a 15-minute overlap, the same for every group;
  all groups advance together, only on a successful run (`DECISIONS.md` #78).
- **Bootstrap:** the first run stores everything and alerts nothing.
- **Dedup A (before the model):** post ID and hash of normalized text, checked within the batch
  and against history. A phone-only match is not a duplicate; the phone is a candidate signal for
  dedup B. The canonical is the earliest publication among posts that arrive together; a stored
  canonical never changes, so an older copy that arrives later becomes its duplicate
  (`DECISIONS.md` #75).
- **Dedup B (after the model; derived, not stored):** same apartment reposted with rewritten text. The
  Gate D key (`DECISIONS.md` #230, #232): two posts with different text hashes, within 72 hours of each
  other, among the active canonical posts that have a classification, are the same listing when they share a
  phone that is not an agent number (a number found in four or more of those posts) **and** the fields match
  (price sets equal, rooms equal, an area in common), **or** they hold a byte-identical photo **and** one of
  those two matches. Nothing else merges: a phone, the fields or a photo alone never does. The result is
  **derived from the stored posts and never written onto a post** (#231). It is a fact about the posts, the same for
  every user: **computed once for all users, held in the site's memory, and computed again only when the store changed**
  (a collection run, a classification run, a flag, a report, a restore, a correction); only each user's filtering and
  order are computed per request (#301). It serves the dashboard's lists and cards in phase 3 and the alerts in phase 4.
  The derivation is `dedup/stage_b.py` (task 3.6); how the site holds it is 3.7's plan.
- **Reposts:** a repost does not create a new card and does not alert again. It updates the post's
  "last published" time and adds a line to a small repost log on the card, so it is easy to see
  that an apartment has been pushed for a while and is still not rented.
- **Model:** the provider is OpenAI, for now (`DECISIONS.md` #126); `gpt-6-luna` is the first
  model to try (#127). The model and its settings (reasoning effort, temperature) are settled after
  the spike: reasoning effort `none`, temperature 0, confirmed on the regression set run twice;
  `low` is the fallback (#157). Structured output,
  schema derived from the pydantic model (#22). The original text is sent verbatim. Every call
  sends `store: false` (#147); the instructions are cached with an explicit breakpoint, and a post
  is never written to the cache (#150). OpenAI's 30-day abuse-monitoring log is accepted (#146). The model returns facts only; code derives the
  rejection and its reason from them (`DECISIONS.md` #92), so a rule change needs no
  reclassification.
- **Street and area:** the model returns the areas itself, from the 71 in its instructions, and
  the streets and neighbourhood names as written (§7, `DECISIONS.md` #167).
- **Yad2** (`DECISIONS.md` #489–#501; the plan is `PHASE_6.md`): its own collector, a headed browser
  on a virtual display on the home server, at a lower daytime rhythm; never two runs of any kind at
  once (#140). **Yad2 is its own seam, not a provider** (#507). The scheduler runs in a second image that
  holds the browser and runs both sources one at a time; the other services keep the slim image (#506). Each run pages Yad2's Tel Aviv-Yafo list from page 1 while new listings appear, with a
  minimum and a cap of pages (#492); a listing is new when its token was never seen, and only a new
  one's own page is opened; a failed run marks no token as seen (invariant 2). The bootstrap takes the
  first 3 list pages and alerts nothing (#493). The stored original (`raw`) is the listing page's
  data, whole; the phone is never fetched or stored (#494, #497). The posting time is the listing's
  last update, converted from Israel time to UTC (#492). A listing back at the top is a repost: it
  updates the last publication (the card's time), with no repost line, no new card and no alert (#492, #520). The model
  reads the description verbatim and, beside it in a separate labelled block, Yad2's neighbourhood,
  street, property kind, "suitable for roommates" and furniture text (#498, #503); Yad2's own form fields
  win wherever they cover a field, and the source of each value is recorded (#495). Non-apartments are
  rejected by their property kind before the model, with no call (#491, #501, #502). A listing with no
  description is classified from the form and the block (with an empty block too it is `no_text`, #518),
  and one with no photo shows without one (#509, #510). No dedup across sources for now, in dedup A or the
  same-listing key (#500), and none for agency listings (#508).
  New instructions are checked by a regression run on the existing set; Yad2's classification is judged
  on the real cards (#511). A block raises the failure alert (#490).

Provider inputs, the field map, traps, the duplicate rate and the group IDs are in
`docs/RESEARCH.md`.

---

## 5. Post lifecycle

| State | Meaning | Visible to |
|---|---|---|
| **Pending** | Stored, passed the pre-model rejects, not classified yet. In phase 2 the model moves it to active or rejected | Admin |
| **Active** | Classified, not rejected | All users, through their filters |
| **Rejected** | Stored with a reason; never shown in the regular list | Admin only, for every reason. It exists so Ron can check that what was rejected belongs there |
| **Archived** | 25 days since last publication with no repost. Hidden. Images deleted; text and raw data kept. A post that was rejected keeps its rejection reason | Admin |
| **Deleted** | 40 days since last publication. Removed entirely | — |

A repost resets the clock. A repost of an archived post returns it to the state it had: active if
it was active; rejected, with the same reason, if the model rejected it or a user flagged or reported it;
pending if it was never classified, or if it was rejected for having no images and the repost has
media (`DECISIONS.md` #72.5, #74). A repost extends a post's life; it does not change what is known
about it.

**The retention job** (Phase 5, #471; `PHASE_5.md` points 1–4): once a night inside the quiet hours. A duplicate
follows its canonical's clock and is deleted before it. Deleting a post deletes its lifecycle record, its `Listing`,
its photos and the users' viewed, hidden and sent-alert marks on it; reports and corrections stay. A post flagged,
reported, left out, or with an open report is never deleted; its photos still go at archive. Photo files no record
names are swept after 24 hours. It runs as a dry run until Ron allows `--apply` (`RETENTION_APPLY`).

### Rejection reasons

| Reason | Decided | Notes |
|---|---|---|
| No text | Before the model | Not sent to the model. A post rejected before the model and fetched again is checked against both pre-model rules on its current content: it returns to pending and goes to the model only if it passes both; otherwise it stays rejected, with the first reason that applies. A pending post fetched again is re-checked the same way; a post with a verdict, or an archived one, is left as it is (`DECISIONS.md` #69, #72.1, #73) **Not for a Yad2 listing** (#509): one with no description is classified from Yad2's form and its labelled block. |
| No images | Before the model | Not sent to the model. Means **no media at all**: a post whose only media is video or reel is not rejected. A post that shares another post is checked first: it is rejected only if the shared post has no media either. A post rejected for this and fetched again is re-checked as in "No text" (`DECISIONS.md` #67, #68, #72.1). The post also returns to pending when a repost of it with identical text arrives with media, video or reel included: the repost's photos are downloaded and kept with the post while the post holds no downloaded image or when it is archived, and the repost stays a repost (#70, #72.3, #72.4). Which media are downloaded (photos only) is a separate rule **Not for a Yad2 listing** (#510): it shows without a photo. |
| Other city | By Facebook's location field when the post has one, else by the model (#214) | The post is in a city that is not Tel Aviv–Yafo: its location field's locality (the part before the first comma) is another city, or, with no usable locality, the model finds that the text names one. The city is shown next to the post. Applies to all users. A nearby city mentioned as a landmark ("5 minutes from Givatayim") is not a rejection. Only about a quarter of the posts carry the field (thedoor's structured listings, `RawPost.native_location`) |
| Seeking | By the model | The poster is looking for an apartment, not offering one |
| For sale | By the model | Facebook's `sale_post` type does **not** mean sale; it is mostly rentals |
| Not a listing | By the model | Furniture, a parking space, an office, anything that is not an apartment or a room |
| Flagged "lied" | By a user | See below |
| Wrong classification | By a user | See below (#173, #254). Stored as `"misclassified"` (approved at Gate C, #288) |

**Flagging.** Any user can flag a post that passed but is not what it claims (for example, an
apartment in Netanya that looked like Tel Aviv). The post moves to rejected for everyone and
records who flagged it. The admin can review flags by user and restore a post. Flagged posts are
exempt from deletion: the full record, including the raw data and not only the text, is kept as a
permanent regression set for the prompt. Their images are deleted at archive like any post's. A
restored post follows normal retention.

**Wrong classification** (#173, #254–#256). Any user can report, on a card, that the post was classified wrongly:
they pick one or more fields from a list, with an optional note. The post moves to rejected for everyone, with its
own reason. The admin sees the reports grouped by field and corrects by hand and restores, or leaves the post out; a
left-out post can still be restored later (#286). One open report per reporter; the post stays rejected while any report
is open; a post both flagged "lied" and reported shows as flagged (#278, #279). While reported, the post is exempt from
deletion like a flagged one; once corrected and restored it follows normal retention. The report and the correction (the field, the model's value, the corrected value) are always kept.
**Only the admin corrects.** A correction overrides the model's answer, on the card and in the filters, also after a
later reclassify, until the admin removes it; the model's answer is kept beside it, and the card marks the field
"corrected by hand".

**Restore** (#251, #281–#283, changing the rule approved at Gate E): one rule for a post flagged "lied" and a reported
post. Restore removes the flag or the reports only; the post's state is then what it would be without them, derived
from the post as users see it (the model's answer with the admin's corrections applied): active, or rejected with the
derived reason. An archived post stays archived, its reason re-derived.

Fields and rules: `SCHEMA.md`, Gate E (`DECISIONS.md` #63), amended for Gate C on 2026-10-10; Gate C's records are
approved (#288).

---

## 6. What a card shows

**Always:**
- The poster's full original text, unchanged
- Images
- Link to the original post
- Price. A post can give several prices: all are shown, as "X/Y", and filtering uses the lowest
  (`DECISIONS.md` #95)
- Entry date, as the poster wrote it. "כניסה מיידית" counts as a stated entry date; it is not
  only for calendar dates. A comparable value (immediate, or a date) is stored next to the text
  for filtering; it never replaces it (#96). Its year, completed by code when the post gives none,
  is never displayed (#115). A month with no day counts as its 1st (#123)
- Location: street and or area
- Listing kind, and a sublet mark when it is one
- Phone, when present. Every distinct number in the post is shown; an identical number appears
  once. If the post gives a name with the number it is shown as `name-number`
  (`דני-0541234567`); with no name, the number alone
- Publication time: the **last** publication (the latest repost), shown relative: minutes up to an
  hour, hours up to 24 h, days after that. Earlier publications, the first included, are in the
  repost log (#122)

**Marked fields** (each shows one of the states below):
- Broker: yes / no
- Number of rooms (always the total in the apartment, also for a room in a shared flat). On a room
  post: "1 of N" when the total is written, a room with no "of" when it is not; the "1" comes from
  the listing kind, not from the text (#120)
- Floor (ground = 0). Shown as "floor/floors" only when the building's floor count is written
  (#98, #106)
- Size in sqm: the apartment's; the room's too, only when written (#99). On a room post: "X sqm
  for the room, of Y" when both are written; "X sqm for the room" when only the room's is (#121)
- Balcony
- Parking
- Arnona and house committee, as two separate fields
- "Women only"
- "Women preferred" (עדיפות לבנות). This is not "women only": it is a mark on the card and hides
  nothing. Both come from one gender field with no "not written" state: a post that says nothing
  about gender has no restriction (#117)
- Elevator, air conditioning (card only, never a filter)
- Furnished: yes / partially / no (card only, never a filter; #102)

### Field states

| State | Meaning | Look |
|---|---|---|
| Present and matches | | Green / lit |
| Present and does not match the user's preference | | Red |
| Not written | The poster did not mention it | Grey / off |
| Unclear | The poster wrote something ambiguous ("option for parking", "all included"). Nothing read is kept for it (#109); the original text is on the card | Orange |
| Important and missing | Price or entry date not written | Its own colour, stronger than grey. Chosen at UI stage |

**Not stated** (2026-10-12, #321): every attribute that is not written is shown as "לא צוין" ("not stated") in grey,
balcony and parking included. *Until 2026-10-12 parking not written was shown as "none" and balcony as "not known".* A
display rule only: nothing stored changes, and in the evaluation parking not written stays unknown (#299). Price and
entry date not written keep the important-missing style.

**The colours, refined (2026-10-11, #309):** green for every known positive value (no broker, a balcony, parking, an
elevator, air conditioning), also when no preference is set and for a guest; red only when the user set a preference
and it is not met; a known negative value with no preference is shown plain; grey for not written; orange for unclear.
How the card maps them: `PHASE_3.md` 3.7 (d).

**The closed card and the opened post** (2026-10-12, #326): the closed card shows only the green chips, plus three items
that are not green: the red "women only" icon, the important-missing badge ("no price", "no entry date"), and the orange
location line. The opened post shows every chip in its colour (green, orange, grey, plain). Every item and where it sits:
`PHASE_3.md` 3.7 (c).

**A viewed card** (#467, 2026-10-18) looks faded and stays clickable: the photo faded most, the plain text in a muted ink
that keeps its contrast, a red or green value in its colour, the glow's ring without its halo, and the word "נצפה". A
hidden card that is shown (§8, #465) is faded the same way, tagged "מוסתרת", and has "בטל הסתרה". "הסתר" and "בטל הסתרה"
are a small pill on the photo's top-right corner, opposite the "i", so the foot does not change (#341, #351); in the
opened post they sit in the foot beside "סימון כלא נצפה" (#468, `PHASE_4.md` appendix A, point 12).

---

## 7. Location

**Amended 2026-10-05** (`DECISIONS.md` #81–#83, #167–#170): the model decides the area. *An earlier
amendment of the same day had code decide it through a street table and a translation table
(#84–#88, #110, #111); superseded by #167.*

- **The model returns the areas:** municipal numbers from the closed list of 71, which is given in
  its instructions, stored on the post (#167). It also returns the streets and neighbourhood names
  as written, kept for the card and for error analysis; a name or other city the post does not
  contain is dropped (#162, #180). The model never touches the source text, so a wrong area is visible beside the
  original and can be counted and corrected. The other-city rejection is not the model's alone:
  when the post has Facebook's own location field, its locality decides (#214).
- **The areas** are a closed list: the municipality's open `שכונות` dataset (GIS layer 511), all
  71 entries, the Old North in its two parts, non-residential entries included (#81), in
  `reference/areas.yaml`. The grouping in the area filter is a display rule (#82, #248, #261; §8). An area is
  identified by its municipal number; the name is a label (#83).
- **The rules, given to the model as instructions** (#88, #112, #124, #167): a stated area decides;
  a street only refines inside it (for example, which part of the Old North); several possible
  areas are all returned (a long street such as Dizengoff, with nothing to settle it); nothing the
  model can place returns no area. With no area name and no street, a well-known landmark that
  places the apartment decides ("ליד שוק הכרמל"), every area it touches on a border; a general
  distance phrase places nothing (#178). Colloquial names ("הצפון הישן", "לב העיר", "יפו") are
  given as examples (#86). Filtering is always by area, never by street.
- **Known limit** (#170): for a post with only a street, the area rests on what the model knows of
  Tel Aviv. The regression set measures it (90% on `areas`, by reach: #198). A street table as an aid is recorded
  for later, only if the regression set shows the model weak on such posts (#169).
- **The colour comes from the stored areas** (#110, #112, #113): one area, definite; two or more,
  unclear (orange), matching and alerting if any is chosen, also when one stated name covers
  several entries (for a user who chose every one of the post's areas it is not orange, §8, #250); none, and the
  post gave a street or an area name, unclear and never alerted; none, and no location given, not
  written. Shown at the bottom, never alerted, when unclear with no area.

---

## 8. Filtering and profile

Each user has one profile. The dashboard can show everything; the profile is the saved filter, and
the same profile drives that user's Telegram alerts. Changing it affects alerts from then on.

**Two search options** (#245–#247): the profile holds a "room in a shared flat" search and an "empty apartment"
search. Each can be switched on or off and holds its own full, separate set of the values below, each category with
its own level. The UI offers "copy from the other option" (every value but on/off; never the sqm range into the room
search, #272). A post is evaluated by the option its kind belongs to; a post whose kind is unclear or not written is
evaluated against every enabled option and shown at the bottom, its kind marked (#273). A new profile has both options
on, nothing set, sublets off, "women only" hidden (#268). **Sublets are one switch for the whole profile** (#317,
2026-10-12; until then one per option): a sublet is shown only when the switch is on and the option of its kind is on,
and is evaluated with that option's values. Broker, parking and balcony have a fixed wanted value (no
broker, has parking, has a balcony): the user only turns them on and picks the level (#269). Half rooms and a basement
can be chosen (#271). The entry date is a range, both ends optional; a post whose entry is "immediate" compares as the date
of the evaluation (#270). **The quick chip "מיידי"** (#458, 2026-10-18, replacing #270's chip rule) means entry **no later
than 3 calendar months from today, with no lower bound, rolling**: re-computed each day at evaluation, saved in the profile
as an "immediate" marker, never as fixed dates (Ron: past entry dates in a post effectively mean "available now", and a
rolling window never goes stale). *Until 2026-10-18 the chip saved "until the day it was pressed", which went stale in the
saved preferences and the alerts.* The marker is `DateRangeCriterion.immediate` (approved 2026-10-19, #468; a stored
profile with the old chip shape reads as the marker).
Typing "מתאריך" while "עד תאריך" is empty fills "עד תאריך" three calendar months on, a fixed date the user can change
(#459; the page only).

| Level | Categories | Behaviour |
|---|---|---|
| **Listing kind** (hard) | Room in a shared flat · empty apartment, as two search options, each on or off; and one "show sublets too" for the profile, off by default (#317) | Only posts of a switched-on option are shown. Sublet is a basic flag: a post is a sublet or not, with no duration or other detail. A sublet is shown only with the profile's switch on, and is evaluated against the values of the option its kind belongs to; no third option and no sublet-specific values (#246, #317) |
| **Critical, fixed** | Area (multi-select) · price range (min and max both optional) | A post that fails is not shown and does not alert. The user cannot downgrade these. No value entered = not applied |
| **Critical by default, user may turn off** | "Women only" | Negative only: such posts are hidden. If turned off, they are shown with a red icon |
| **Preference by default, user may make critical** | Rooms · floor range · sqm range (empty-apartment search only, #247) · broker · parking · balcony · entry date | As a preference: affects order and field colour only. As critical: failing posts are not shown |
| **Don't care** | Any of the above with no value | No effect on display or order |

Within one profile, room and empty apartment each carry their own values (a room's price range is
not an apartment's), and every card shows clearly which option it answers. A room search has no sqm
filter; the card shows both sizes when written (#247).

**The area filter** (#248, #249): the 71 areas are shown grouped under region headings, each with "select all in
group"; the non-residential entries are not hidden but sit in a separate collapsed group at the bottom. What is stored
is always the municipal numbers; the grouping is display only. The groups and the non-residential entries: `PHASE_3.md`
§6 (#261).

**The area's colour, per user** (#250, #275): the area is not orange for a user when all of the post's areas are in that
user's selection, whatever produced the several areas; with no areas chosen, a several-area post stays orange. Computed
per user at display, never written on the post.

**Order of display:** posts that meet the preferences first; then posts that meet the critical
conditions but not the preferences; at the bottom, posts where a critical value is not written or
unclear. A preference that is not written or unclear counts as not met: the post is in the middle group, not at the
bottom (#298). Parking that is not written is unknown, as stored (#299). **A post with no written price is always at
the bottom, also when the user set no price range** (#302). **An orange location caps a post at the middle group**
(#320, Ron, 2026-10-12: "first the certain things, and only then those that are unsure of something"): it is never in
the first group when its areas are two or more and not all chosen, or when it has no area but gives a street or an area
name and no areas are chosen; with areas chosen such a post is already at the bottom. A post that gives no location at
all is not covered. Posts that are known to fail a critical condition are not shown.

**The glow** (#308, #322): green for the first group, orange for the middle, red for the bottom; **no green glow while
the option that admits the post holds no preference at all** (the card then has no glow). The glow does not change the
order.

**The saved preferences and the home page's filter are two things** (#314, #315). The profile above is what is saved on
the account and, from Phase 4, what drives the alerts. The filter bar on the home page is what the user is looking at
now: for a signed-in user it starts from the saved profile and a change there is for this visit only; when the bar
differs from the saved profile, a "ההעדפות שלי" button resets it to them. **The bar never saves: the preferences are
changed only on the preferences page** (#335, 2026-10-12, amending #315, which had a "save as my preferences" in the bar;
Ron: "so that, at least for now, the two states are clear"). The order and the card's colours follow what the bar holds
at that moment. A guest's bar starts empty and is never saved (§10).

**Viewed posts** (`DECISIONS.md` #62): each user sees which posts they have already viewed. All
unviewed posts come first, then the viewed ones; within each of the two, the order above. "Viewed"
belongs to the user and is never written on the post. It survives a repost, since a repost updates
the existing card, and goes when the post is deleted. Opening the card marks it viewed; scrolling past does not. An
open card has "mark as not viewed". A card stays viewed when a further publication is grouped into it by the Gate D
key (#253). **A viewed card moves below the unviewed ones when its post is closed** (#467, 2026-10-18; until then only at
the next load of the list).

**Hidden posts** (#464–#466, 2026-10-18; the record `HiddenPost` approved 2026-10-19, #468): a signed-in user can
hide a post. It is a per-user record like the viewed one, never written on the post (invariant 12), not available to a
guest, deleted with its post. **Hiding applies only while the bar shows the saved preferences**; in a temporary filter
everything is shown. A "הצגת מוסתרים" switch in the bar shows the hidden ones, and a hidden card that is shown has "בטל
הסתרה". "הסתר" is offered on a card in the middle and bottom tiers always, and in the top tier only once viewed: by tier,
not by glow, since a card with no preference has no glow. The server decides whether the bar is on the saved preferences.
A hidden card stays hidden when a further publication is grouped into it (as viewed, #253). On the saved preferences with
the switch off the count leaves the hidden cards out and the bar says how many are hidden; the switch shows only there,
and is never saved. In a temporary filter "הסתר" is still offered: the card stays in place, marked "מוסתרת". A hidden card
that is shown keeps its place, faded as a viewed card, with the tag "מוסתרת".

---

## 9. Alerts

A post alerts a user when all of these hold:

1. It is new (not a repost) and not rejected.
2. It falls under one of the user's enabled search options: the option of its kind, and for a sublet the profile's
   one "show sublets too" switch (#245, #246, #274, #317).
3. It passes every critical condition of that user.
4. It has an explicit price.
5. Its location is understood: either a definite area, or a street whose possible areas include
   one the user chose (alerted with the area marked orange). A post with no location, or one that
   could not be placed (§7), does not alert.

Preferences never block an alert. If a category the user made critical is not written in the
post, the alert is still sent and names the missing item.

A new user sees all existing posts in the dashboard but is alerted only on posts first stored after **linking
Telegram** (`DECISIONS.md` #452 point 10, 2026-10-18). *Until 2026-10-18: "that arrive after signing up".* A post is
alerted to a user at most once (the sent-alert record, Gate F, #453); a post the Gate D key ties to an earlier one, or a
repost, never alerts; a post whose kind is unclear or not written never alerts (#360).

---

## 10. Users and access

- An account is created with a one-time key issued by Ron. A used key cannot create another account. A key has a
  label, does not expire, is shown once, and can be cancelled while unused; a cancelled key stays cancelled (#243,
  #266). Ron's own admin account is created by a one-time command on the machine (#244).
- Sign-in on the site with a username and a password; no email (#242, #262). After 5 failed attempts, a short delay
  (#264). A session lasts 30 days (#263). A forgotten password is reset by the admin with a temporary password that
  must be changed, and the reset ends every session (#262, #263). A user is never deleted, only disabled and enabled
  again by the admin (#265). Telegram is linked by a code the site shows and the user sends to the bot. Site and
  Telegram share the same profile.
- **Viewing needs no account** (#306, #307, amended 2026-10-11): anyone who reaches the site can scroll and filter
  without signing in. **Tailscale is the only gate for viewing posts**; the one-time key guards creating an account, not
  viewing. A guest's filter lives in the browser only; a guest cannot save preferences, mark a post viewed, flag or
  report it. An account is needed to save preferences, and from Phase 4 for alerts. **Condition: if the site is ever
  served outside the tailnet, signing in becomes mandatory for viewing.** *Until 2026-10-11: "Tailscale sharing is a
  second gate in front of the site."*
- The site is built first, with a polished UI built in phase 3 (#257). The Telegram Mini App is an adaptation of the
  same site.

## 11. Admin (Ron)

- Rejected posts, all reasons, canonicals only (#75 B). No other user sees them
- Pending posts, with the reason of a failed classification and a "retry" (Gate E, #139)
- Flag review by user, and restore (#251)
- "Wrong classification" reports grouped by field: restore, correct by hand, or leave out; the corrections in force,
  and their removal (#173, #254–#256)
- Archive
- Daily digest: collected / deduplicated / classified / rejected / alerted, per group (by its name from the config,
  #482); silent-group detection; failures. Admin only.
- The pages in three sections (#483): posts review (the lists above), data analysis (a placeholder, planned after
  Phase 5), system management (the schedule, keys, users)
- Key issuing, the key list and cancelling (#243); users: password reset, disable and enable (#262, #265)
- The schedule page: the run interval (30 minutes by default) and the quiet hours (00:00–07:00 by default), a "run now"
  button, the last runs with their Apify cost (phase 5, `DECISIONS.md` #61, #471, #474; the quiet hours moved here from
  "later")
- `max_posts` (later, phase 7): one value for all groups; a value where groups × `max_posts`
  reaches the charge cap's `maxItems` is refused on save

---

## 12. Build order

Phase 0 (skeleton, contracts, local store, text normalization, thedoor mapping, 97 tests) is done
and stays valid. Gate A (`RawPost`) stays approved. **Phase 1 is complete (2026-10-04):** four
real runs met its DoD (`PHASE_1.md`, `RESEARCH.md` §11).

| Phase | Contents | Done means |
|---|---|---|
| **1. Collection** | Fixes for decisions #37 and #38 · Apify spike (task 1.1a) · **Gate E** (post lifecycle fields) · SQLite store · thedoor fetch · pre-model rejects · dedup A · repost log · image download · per-group watermark | A real run stores posts and images with no duplicates, and a second run does not repeat them |
| **2. Classification** | **Gate B** (field schema from §5–§7) · the model · post-model rejects · street and area · **Gate D** (the key, #230; its use is phase 3's, #231) · reclassify job | Every post has fields and a state |
| **3. Dashboard** | **Gate C** (filter rules, and the user, key, session, profile, viewed-post, report and correction records) · users and keys · profile with two search options and filters · cards · viewed posts · rejected list · flagging · "wrong classification" reports and the admin's corrections · the admin lists · the same-listing grouping, derived by the Gate D key (#231) · **the polished UI** (#257) | Ron filters and sees real apartments in a browser, from the site in Docker on his laptop, over a copy of the store in its volume (#428) |
| **Server deployment** (between 3 and 4, #426) — **DONE 2026-10-18 (#441, #451)** | After Phase 3, taken from Phase 5: the image on `homeserver`, published from git by the repo's GitHub Action and pulled by homelab's `stacks/tlv-hunter/` (#420, #433) · the site's own tailnet machine `tlvapthunter`, a Tailscale container with Serve (#419) · a fresh store: `run_once --bootstrap` (30 posts per group, #437), then `create_admin`; the Windows store is not moved (#436) · the `Host`/`Origin` probe through Serve and a real sign-in (#422) · the measured working day, Phase 3's DoD 6 (#428) · "Adding the first friend" as a written procedure, run when Ron adds one: the sharing rule, DoD 2 and 5 on the real store (#438, #440). Planned in `docs/DEPLOY.md` | The site is reached at `tlvapthunter.<tailnet>.ts.net`, the probe passes, and Ron signs in as the admin on the server (#440) |
| **4. Telegram** — **DONE 2026-10-19 (#469)** | Bot · account linking · alerts by profile · sent-alert record per user and post, so nothing is alerted twice · Mini App spike, against `tlvapthunter` (#426) · a bridge `scheduler` for continuous collection on the server (#454) · the `web_app` menu button on every linked chat (#470) | A real alert arrives according to Ron's profile |
| **5. Server** (`docs/PHASE_5.md`) — **DONE 2026-10-21 (#476)**; built in round 36 (#471–#474) | The home server already runs the system from the deployment step (#426); Phase 5 adds the scheduler with the admin-set interval and quiet hours (#474) and a manual "run now" · the run and schedule records (Gate G, #472) · archive and deletion job · digest, including native-price vs model-price mismatches and the real Apify cost (#450) · failure alert to the admin · silent-group detection · no burst of alerts after a pause (#473) | Two days unattended (#427) |
| **6. Yad2** (`docs/PHASE_6.md`, approved 2026-10-24; `DECISIONS.md` #489–#511; build step 1 built in round 43) | The second source: Tel Aviv-Yafo listings collected by a headed browser on the home server, unattended (#490, #491) · Gate A and Gate B for Yad2 (#495, #496) · the model combined with Yad2's form (#495, #498) · bumps as reposts, bootstrap without alerts (#492, #493) · the card's source, a link to Yad2, no phone (#497, #500) | `PHASE_6.md`'s DoD (#502 point 22): two days unattended at its rhythm, a Yad2 card that alerts once, a block reported once |
| **7. Later** | memo23 failover · editing the group list and `max_posts` from the dashboard | |

Phases 1–4 are developed on Ron's personal laptop in Docker, **for development only (#417)**: no one but Ron uses the
system before it runs on the home server, from the server deployment step (#426), which comes after Phase 3 and before
Phase 4 so that Phase 4's buttons and the Mini App spike work against the real address from a phone.

**Gates.** A (`RawPost`) and E (post lifecycle record and `GroupWatermark`, 2026-10-04) are
approved. B (2026-10-05) and D (2026-10-08) are settled. **C is approved** (2026-10-10, `DECISIONS.md` #242–#257,
#262–#288): its records, names and types are in `SCHEMA.md`, and Gate E is amended for it (`"misclassified"`, the
restore rule, the exemption of a reported post, `schema_version` 3). Gate E covers what
the lifecycle adds to a stored post: state, rejection reason, who flagged it, last publication
time, the repost log, and local image paths.

**Detailed planning is one phase ahead.** `PHASE_1.md` details phase 1 only. Two technical choices
are deliberately left for when their phase is planned: the dashboard framework (phase 3) and the
Telegram library (phase 4). The dashboard framework is chosen (#258): React and TypeScript with Vite, hand-written
CSS, served with the API by FastAPI and uvicorn from one image (`PHASE_3.md` §5.1).

**The UI** (#257): the dashboard gets a polished UI in phase 3, built with Ron's design skills when the UI task is
reached; §6–§8 stay binding, and the visual design is that task's.

Because history is at most 40 days, adding a field later means reclassifying 40 days of posts, not
everything. The field list can start lean.

---

## 13. What changed against the old documents

| Old | New |
|---|---|
| #5 Everything in GCP | Home server + Tailscale; GCP is the fallback |
| #9 Telegram push only, no dashboard in v1 | Dashboard first, then bot and Mini App |
| #12 / #16 Sniper in shadow / dormant | Removed |
| #13 Nothing is ever deleted (invariant 3) | Archive at 25 days, full deletion at 40; flagged posts kept whole, `raw` included, images deleted at archive (§5) |
| #15 `new_north` included at launch | Areas are chosen per user |
| #17 v1 pushes every post (calibration mode) | Alerts only on profile match; calibration is done through the rejected list and flagging |
| #21 `httpx`, push-only bot | The bot also listens (account linking). Library choice reopened |
| #39 No-text posts are notified | Rejected, admin-only view, not classified |
| #41 Three view-time filters | The full model in §8 |
| Single user in v1 | Friends from the start; #25 (shared collection, personal evaluation) is now live |
| Firestore, Cloud Run, Cloud Scheduler | SQLite, Docker Compose, a scheduler in the container |
| Image re-hosting deferred to Phase 6 | Images downloaded at fetch time |
| Phases 0–6 of `MACRO_PLAN.md` | §12 |
| Yad2 through `providers/` | Its own scraper, a headed browser on the home server (`DECISIONS.md` #490); phase 6, planned in `PHASE_6.md` |

Unchanged: no Facebook login, adapter layer, classification without summaries, null as
information, watermark rules, dedup layers and findings, schema gates, verification method,
bootstrap mode, Gate A.

---

## 14. To verify and open items

### To verify before building on it

| Item | Tag |
|---|---|
| A Telegram Mini App loads from a tailnet-only HTTPS address on a phone with Tailscale on | `ASSUMED` — spike in Phase 4, against `tlvapthunter` after the server deployment step (#426). If it fails, the plain site still works |
| Tailscale device sharing covers the number of friends on the free plan | `VERIFIED` 2026-10-14, Ron's check (`DECISIONS.md` #361): friends come through device sharing, not as users of Ron's tailnet, so the free plan sets no limit on their number and nothing is paid (`ASSUMPTIONS.md` I5) |
| Public source for Tel Aviv areas, the Old North split, and streets per area | Chosen by Ron 2026-10-05 (`DECISIONS.md` #81, #84). The areas and the Old North split: `VERIFIED`, the municipality's open `שכונות` dataset (71 entries, re-read 2026-10-05). Streets per area: not needed since the model decides the area (#167); a street table is recorded for later (#169) |
| Image download from the signed Facebook links works at fetch time | `VERIFIED` 2026-10-04 from the laptop: spike 1.1a, 5 of 5; then the task 1.12 check, 632 of 632, all JPEG; then the four real runs, 818 photos held (`ASSUMPTIONS.md` I6, `RESEARCH.md` §11). From the home server itself: still unverified |
| Apify spike: time window per group, all groups return data, comment flag honoured, real cost | `VERIFIED` 2026-10-04 (`SPIKE_1_1a.md`) |
| Shared-post content path | `VERIFIED` 2026-10-04: `sharedPost.text` and `sharedPost.media` |

### Open for Ron

What is open today is in `BACKLOG.md` ("Next sprint") and `PHASE_3.md` §7. Gate C, the plans for 3.4, 3.5 and 3.6 are
approved (#288–#290, #295). The bill stays with Ron (#225); the measured working day is Phase 3's (task 3.10). Gates B and D, the
model's response and the Gate E failure fields are approved (#125, #151, #152, #230).

### Recorded, not verified

Ron's position is that the tool stays personal: users are close friends searching with him or
alongside him. Whether the personal-use exclusion in the Privacy Protection Law covers this was
never checked legally (`ASSUMPTIONS.md` L1).
