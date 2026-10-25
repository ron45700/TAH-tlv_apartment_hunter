# Phase 6 — Yad2

**Status (2026-10-24, round 44): APPROVED by Ron** (§6.12, all 25 points, #502–#511; §6.14 and §6.8, #512–#519). The
schema is in `SCHEMA.md` (Gates A, B, E, G for Yad2). **Build steps 1 and 2 are built, and instructions version 7 is
written** (§6.13, §6.13b). C7 answered: a bump adds no repost line (#520). **Round 45 (#521):** the block check
passed (the request shape VERIFIED, `ASSUMPTIONS.md` O14); **the regression run of version 7 failed on
`apartment_kind`**, new against version 5 (§6.4, "Results"). **Round 46 (#522): version 8** (the Yad2 section
scoped to posts that carry the block) **restores `apartment_kind` and `areas`**; version 7 is never deployed.
**Round 47: version 8 accepted (#523), deployed with the collector in one deploy; #524 (a bump returns an archived
listing), #525 (the bootstrap's no-alert rule, step 6); build step 4 built** (§6.13c), on saved pages, no browser run.
**Round 48: #526–#532** (no cap on listing pages; Yad2 from 06:00; Facebook first; Yad2 off at the deploy, its first
run the bootstrap; one failed Yad2 run alerts; Playwright's image; the stack and the deploy, §6.16); **build step 5
built** (§6.13d), not run: no image built, no browser run.
**Round 49: #533–#535** (the badge, Yad2's wording, the digest's counts); **build step 6 built** (§6.13e). Every build
step is built; what is left is the deploy (step 7, §6.16).
**Owner:** Ron
**Parent:** `BASELINE.md` §1, §4, §12 (the phase 6 row), §13 · **After:** Phase 5 (closed, #476) · **Evidence:**
`docs/SPIKE_YAD2_2026-10-22.md` (spike 1, §1–§10; spike 2, §S2.1–§S2.6) · **Decisions:** #489–#519 · **Schema:**
`SCHEMA.md` Gates A, B, E, G

**Phase goal:** Yad2's Tel Aviv-Yafo rental listings reach the same site and the same alerts as the Facebook posts,
collected unattended on `homeserver` by a headed browser, classified once by the same model with Yad2's own form fields
taken as they are, each card showing its source, and a block reported to the admin.

**Phase DoD (approved, #502 point 22):**
1. On `homeserver`, Yad2 runs unattended for two days at its rhythm, daytime only; no Yad2 run overlaps any other run;
   every run leaves a `RunRecord`.
2. A new Yad2 listing appears as a card with the Yad2 badge, the link to Yad2 and no WhatsApp button, and alerts a
   linked user whose profile it passes, once; the bootstrap alerts nothing; a bump moves the card's time and alerts nothing (no repost line, #520).
3. A block (the top document on `validate.perfdrive.com`, or no request reaching `gw.yad2.co.il`) fails the run, marks no
   token as seen, and raises the failure alert once; a page that carries the background reCAPTCHA frame does not.
4. Tests (no network) pin: Facebook's `RawPost`, `Listing` and `listing_id` unchanged; the Yad2 mapping on fixtures read
   in place; invariants 2, 4, 8, 9, 13, 14 and 15 for Yad2; no phone request in the collector's code.
5. The regression run (§6.4) passes on the existing set, or Ron accepts its result.

---

## 6.0 Mandatory anchors

| Rule | What it means here |
|---|---|
| Invariant 1 | Gates A, B, E and G for Yad2 are approved (#502) and written into `SCHEMA.md`; the names in §6.14 wait for Ron |
| Invariant 2 (#492) | A failed Yad2 run marks no token as seen and moves no `GroupWatermark` field; its new posts are stored at the end, only on success (#502 point 18) |
| Invariant 4 (#494) | `raw` is the listing page's `data`, whole |
| Invariants 8, 14 (#498, #503) | The model reads the description verbatim; the labelled block goes beside it, never inside it, never normalized; with no description the block alone (#509) |
| Invariant 9 (#492) | `updatedAt` is Israel local time with no zone: converted to UTC at the mapping, in `parsing/datetimes.py` (single implementation rule). **Built** |
| Invariant 13 (#499) | No account, no login, no user's cookie; Yad2's own visitor cookies in the profile, on the server, outside git and the image |
| Invariant 15 | No personal identifier in any request to Yad2; the profile holds only Yad2's visitor cookies |
| #140 | Never two runs of any kind at once: the scheduler runs Facebook's and Yad2's jobs one at a time (#506) |
| #497 | No phone request in the collector, ever: no click on "show number". A test pins it on the `yad2/` package |
| `external-contract-verification` | Every Yad2 path and field is from the spikes' captured responses; the Playwright image from its docs (§6.5) |

## Order of work: build steps

| Step | What | State |
|---|---|---|
| 1 | **The contracts and the mapping** (no Docker, no browser): `RawPost`'s third source and Yad2's `listing_id`; `Listing.field_sources`, version 2; `RunRecord.source` and `ScheduleSettings`' Yad2 rhythm, version 2, stored rows read with defaults; a listing page's `data` to `RawPost` and to the form's part of `Listing`; the 22 kinds; `updatedAt` → UTC; tests on the spikes' pages read in place | **Built, round 43**; the media (#512) in round 44 (§6.13) |
| 2 | **Yad2's rules around the model**: the pre-model `not_listing` by kind, no call (#502 point 11); no `no_text` and no `no_images` rejection for Yad2 (#509, #510); dedup A skipped for agency listings (#508); the merge of the form and the model's answer with `field_sources` (§6.3), the form's `streets` and `stated_area_names` exempt from #162 (#502 point 8); the city by `native_location` (#214); dedup A and the Gate D key never across sources (#500); `no_text` when nothing is left for the model (#518). Tests with a fake classifier, no model call | **Built, round 44** (§6.13b) |
| 3 | **The block and instructions version 7** (#498, #503): the block as a second input item, the instructions' paragraph, `PROMPT_VERSION` "7" with its fingerprint; then **the regression run on the existing set and the block check** (paid, on Ron's go, #511, #519; §6.4) | **Version 7 written, round 44**; the two paid runs wait for Ron's go (the block check needs a small command first) |
| 4 | **The Yad2 seam** (#507, §6.5): the list pages in both shapes, paging (§6.8's numbers), the new tokens' pages, the bump checks (#504), block detection (§6.6), all tested on saved HTML; the browser wrapper (Playwright) the only part not run in tests; the run's store write at the end (#502 point 18); its `RunRecord` (`source` `"yad2"`) and the `GroupWatermark` `yad2-tel-aviv` | **Built, round 47** (§6.13c); the `RunRecord` is written by step 5's command from the run's counts |
| 5 | **The job, the scheduler, the image** (#506): the Yad2 run command; the scheduler reading Yad2's rhythm and running both sources one at a time; the second image, the scheduler moved to it, the GitHub Action building both; the profile's folder; the digest's Yad2 line and the schedule page's Yad2 fields | **Built, round 48** (§6.13d), but the digest's Yad2 line, moved to step 6 |
| 6 | **The card and the alert**: the source badge, "open on Yad2", no WhatsApp, Yad2's neighbourhood and street; the photos (after §6.14 C1); **the alert pass skips the first succeeded Yad2 run's posts** (#525); **the digest's Yad2 line** (§6.7) | **Built, round 49** (§6.13e) |
| 7 | **The deploy** on `homeserver` (Ron): the bootstrap, 3 pages, no alerts (#493); two days unattended (DoD 1); Ron judges Yad2's classification on the real cards (#511) | Ron |

---

## 6.1 What Yad2 gives (from the spikes)

- **The list** (`/realestate/rent/tel-aviv-area?area=1&city=5000`): the page's own HTML carries the feed in
  `__NEXT_DATA__` (`["realestate-rent-feed", {...}]`): 40 listings a page, no date, no text; `pagination.total` (4,438).
  **Two shapes** (§S2.2): `private` 20 + `agency` 20, or one `yad2` list of 40 in a fixed pattern. Both are read.
  Pages by the page's own links ("2", "3", …). The default sort is by date; **private listings newest first by
  `updatedAt`; agency listings are not in date order** (§S2.3).
- **The listing page** (`/realestate/item/tel-aviv-area/<token>`): `__NEXT_DATA__` →
  `props.pageProps.dehydratedState.queries[]`, the query whose key starts with `"item"` → `state.data`: the form
  fields, the description, the dates, the poster's name, no phone. (An agency page's rendered HTML may hold the agency's
  number in a WhatsApp link, outside `data`: never read, never stored.)
- **Photos** on `img.yad2.co.il`, no query string (not signed, by their form).
- **The map** (`gw.yad2.co.il/realestate-feed/rent/map`) ignores the city and the neighbourhoods and is capped at 200:
  not used for collection. Its arrival is one sign that the page was not blocked (§6.6).
- **Volume** (§S2.3, one Saturday): at least about 37–48 private listings updated an hour, new and bumped together;
  at least about 600 a day; at least about 70 new private listings a day by the stock's 45-day renewal.

## 6.2 Gate A for Yad2: `RawPost` (#494, #496, #502; Facebook unchanged) — approved, in `SCHEMA.md`

`d` is the listing page's `data` object.

| `RawPost` field | Yad2 source | Note |
|---|---|---|
| `schema_version` | 1 | Unchanged (#502 point 2) |
| `source` | `"yad2"` | #496 |
| `source_post_id` | `d.token` | 8 lower-case letters and digits |
| `listing_id` | `sha256("yad2:" + d.token)` | #496 |
| `group_id` | `"yad2-tel-aviv"` | #496: its `GroupWatermark`, silent-group detection |
| `group_title` | `"יד2 · תל אביב-יפו"` | Shown where a group's name shows today; the source badge is separate (§6.9) |
| `permalink` | `https://www.yad2.co.il/realestate/item/tel-aviv-area/<token>` | The list card's own path without its tracking query |
| `posted_at` | `d.dates.updatedAt`, Israel time → UTC | #492; `rebouncedAt` never used |
| `fetched_at` | our clock when the listing page was read | As today; kept on re-fetch |
| `raw` | `d`, whole | #494. Holds the poster's name (as Facebook's `raw` does), no phone |
| `text` | `d.metaData.description` | `""` when absent |
| `text_source` | `"text"`, or `"none"` when there is no description | |
| `post_type` | `"yad2_listing"` | A constant; Facebook's values unchanged |
| `media[]` | `d.metaData.images[]` → `{type: "Photo", uri, width: None, height: None, media_id: uri, page_url: permalink}`; `d.metaData.video` → one `{type: "Video", …}` the same way | #512 (§6.14 C1): no type change. Built |
| `native_price` | `d.price` when > 0, else `None` | #501: 0 means no price; above 20,000 kept |
| `native_price_raw` | `str(d.price)` when > 0, else `None` | |
| `native_currency` | `"ILS"` when there is a price | Stated, not parsed from a symbol (#502 point 3) |
| `native_title` | `None` | |
| `native_location` | `d.address.city.text` (`"תל אביב יפו"`) | So #214 rules the city: never `other_city` |
| `author_name` | `d.customer.name` | #502 point 4 |
| `author_id_raw` | `str(d.customer.id)` | Never a key (invariant 5) |
| `author_profile_url` | `None` | |
| `top_comment`, `reactions_count`, `comments_count`, `shares_count` | `None` | |
| `text_hash`, `phones`, `no_text` | `textnorm` over `text`, as today | `phones` only from the description's own text, never from Yad2's phone response (#497) |
| `is_canonical`, `duplicate_of` | dedup A for a private listing; **an agency listing is not deduplicated** (#508) | |

## 6.3 Gate B for Yad2: `Listing`, the form and the model (#495, #501, #502) — approved, in `SCHEMA.md`

**Rule (#495):** the form wins wherever it covers a field; the model decides `apartment_kind`, `post_nature` and
`gender`, and every field the form left empty; **the form's property kind wins for `post_nature` / `apartment_kind`
where §6.3.1 maps it** (#502 point 25). **The source of each value is recorded in `field_sources`** (#502 point 5):
`dict[str, "form" | "model"]` on `Listing`, one entry per field outside the provenance for a Yad2 post, `{}` for a
Facebook post; `Listing.schema_version` 2 (a stored version-1 `Listing` reads as version 2 with `{}`). `price_source`
keeps its meaning: `"native"` when the price came from Yad2's form. **A form flag:** `true` → `True`; `false` →
`False`; absent → the model.

| `Listing` field | From Yad2's form | Else |
|---|---|---|
| `post_nature` | the property kind, where §6.3.1 maps it | model |
| `apartment_kind` | the property kind, where §6.3.1 maps it | model |
| `price` | `d.price` > 0 → `[d.price]`, `price_source` `"native"` | model (from the description) |
| `entry_date_written` | — (the form's date is not "as written", #96) | model |
| `entry_date` | `d.inProperty.isImmediateEntrance` true → `"immediate"`; else `d.additionalDetails.entranceDate` → its calendar date | model |
| `rooms` | `d.additionalDetails.roomsCount` (a positive multiple of 0.5) | model |
| `floor` | `d.address.house.floor`: 0 the ground floor, a basement −1 (#502 point 6) | model |
| `building_floors` | `d.additionalDetails.buildingTopFloor` | model |
| `size_sqm` | `d.additionalDetails.squareMeter` (not `squareMeterBuild`, #502 point 6) | model |
| `room_size_sqm` | — | model |
| `broker` | `d.adType`: `commercial` → `True`, `private` → `False` (#501) | model, for another value |
| `balcony` | `d.additionalDetails.balconiesCount` > 0 or `d.inProperty.includeBalcony` true → `True`; `includeBalcony` false → `False` | model |
| `parking` | as `balcony`, with `parkingSpacesCount` and `includeParking` | model |
| `elevator` | `d.inProperty.includeElevator` | model |
| `air_conditioning` | `d.inProperty.includeAirconditioner` | model |
| `furnished` | `d.inProperty.includeFurniture` false → `"no"` | model (true: the model chooses, with `furnitureInfo` in the block, #502 point 7) |
| `arnona` | `d.propertyTax` > 0 (no period stated; as written, #116) | model |
| `house_committee` | `d.houseCommittee` > 0 | model |
| `gender` | — | model (#495) |
| `streets` | `d.address.street.text`, with `d.address.house.number` when present (#484's form) | the model's own streets from the description added after it (#502 point 8) |
| `stated_area_names` | `d.address.neighborhood.text`, as given (#498) | the model's own names added after it (#502 point 8) |
| `areas` | — | model, with the labelled block (#498, #503, §6.4) |
| `other_city` | — | the model's answer kept, never edited; `native_location` decides (#214) |
| `phone_names` | — | model, matched against `RawPost.phones` as today (#105) |

The form's `streets` and `stated_area_names` are exempt from #162's "not in the text" drop (#502 point 8). Not
mapped, kept in `raw` (backfillable, Gate A's rule): `isForPartners`, `isPetsAllowed`, `includeSecurityRoom`,
`includeWarehouse`, `isRenovated`, `propertyCondition`, `squareMeterGarden`, `isLongTermContract`, `paymentsInYear`,
`furnitureInfo` (text; in the block, #503), `tags`, `priceBeforeTag`, `abovePrice`.

### 6.3.1 The 22 property kinds (#501, #502 points 10, 25) — approved

From the rent search's own options (`base-search-options`); a test pins the table against Yad2's saved options.

| id | Kind | Group | `post_nature` | `apartment_kind` |
|---|---|---|---|---|
| 1 | דירה | דירות | model | model |
| 3 | דירת גן | דירות | model | model |
| 6 | גג/ פנטהאוז | דירות | model | model |
| 7 | דופלקס | דירות | model | model |
| 51 | טריפלקס | דירות | model | model |
| 49 | מרתף/ פרטר | דירות | model | model |
| 4 | סטודיו/ לופט | דירות | model | `whole_apartment` (a studio is one, #94) |
| 11 | יחידת דיור | דירות | model | `whole_apartment` (#501) |
| 43 | סאבלט | דירות | `sublet_offer` (#501) | model |
| 31 | החלפת דירות | דירות | `not_listing` (#501) | — |
| 25 | תיירות ונופש | דירות | `not_listing` | — |
| 5 | בית פרטי/ קוטג' | בתים | model | model |
| 39 | דו משפחתי | בתים | model | model |
| 32 | משק חקלאי/ נחלה | בתים | `not_listing` | — |
| 55 | משק עזר | בתים | `not_listing` | — |
| 30 | חניה | נכסים | `not_listing` (#501) | — |
| 45 | מחסן | נכסים | `not_listing` (#501) | — |
| 33 | מגרשים | נכסים | `not_listing` | — |
| 44 | בניין מגורים | נכסים | `not_listing` | — |
| 61 | דיור מוגן | נכסים | `not_listing` | — |
| 50 | קב' רכישה/ זכות לנכס | נכסים | `not_listing` | — |
| 41 | כללי | נכסים | model | model |

**A kind mapped to `not_listing` is rejected before the model, with no call** (#502 point 11): stored and rejected
`not_listing` (Gate E's existing reason). A kind not in the table (Yad2 added one) decides nothing: the model decides
both (decided in round 43, §6.13).

## 6.4 The model's block for Yad2 (#498, #503), the version and the regression run (#511)

- **The block**, sent as a **second input item after the post's text**, never inside it, its values verbatim (not
  normalized); wording proposed, settled in step 3:
  ```
  [Yad2 listing form — not the poster's text]
  property kind: <d.additionalDetails.property.text>
  neighbourhood: <d.address.neighborhood.text>
  street: <d.address.street.text> <d.address.house.number>
  suitable for roommates: yes            (only when d.inProperty.isForPartners is true)
  furniture: <d.furnitureInfo>
  ```
  A missing value's line is left out. **With no description, the block is the model's only input** (#509): the empty
  text is not invented or replaced.
- **The instructions** gain a paragraph: some posts come with this block; it is the listing site's form, not the
  poster's words; use it for `areas` by #88's rules (a Yad2 neighbourhood that joins several of the 71 gives every one,
  #498), and for `apartment_kind` and `furnished`; never copy it into `streets` or `stated_area_names` (code fills those
  from the form, §6.3).
- **`PROMPT_VERSION` "6" → "7" and `PROMPT_FINGERPRINT` together** (#179): the instructions change for every post.
- **Built (round 44):** the block (`yad2.mapping.model_block`: the lines above, values verbatim, the furniture
  text with its own line breaks); the request sends the description, when not blank, then the block as a second
  `input_text` part; the block alone when there is no description (#509); a post with neither is refused (#518
  rejects it before the model). Facebook's request is unchanged. Instructions version 7: a "YAD2 LISTINGS" section
  after the opening paragraph (1,272 characters); `PROMPT_VERSION` "7", `PROMPT_FINGERPRINT` `1dada328…`.
- **The regression run — the plan, for Ron's go (not run):** `docker compose run --rm jobs python -m
  tlv_hunter.jobs.regression_run --check` (free), then `docker compose run --rm jobs python -m
  tlv_hunter.jobs.regression_run` (two passes, **cap $0.10**). **The calculation:** version 5's run (round 15) was
  108 calls, two passes over the set, for $0.024295: about $0.000223 a call (`PHASE_2.md`, "Round 15"). Version 7
  adds 1,272 characters, about 400 tokens, to the instructions, cached after the first call: about 108 × 400 cached
  tokens, under $0.001 more. **Expected about $0.025; the cap is four times that.** Compared with version 6 (#511).
  Facebook posts never get the block: the run shows that the new section changes nothing for them. **No Yad2
  labelled set** (#511).
- **The block check (#519) — the plan, for Ron's go (not run):** 3 calls on the saved pages
  `yad2_listing_private_1`, `yad2_listing_private_3` and `yad2_listing_agency_1`, **cap $0.01**. The calculation: a
  call is about $0.000223 with the instructions cached; the first call writes them (about 4,000 tokens), so 3 calls
  stay well under $0.002. The responses are saved to `data/raw/` with a dated name; nothing is stored. **It needs a
  small command first**: `regression_run` reads only the labelled set; the command is built with step 3's remainder,
  on Ron's word.
- **Results (round 45, #521).** **The block check** (`jobs/yad2_block_check.py`): 3 of 3 accepted (`completed`), $0.000616
  in all, each answer valid and using the block; the request shape is VERIFIED (`ASSUMPTIONS.md` O14). Private 1:
  `rental_offer`, `whole_apartment`, furnished `partial`, `no_restriction`, Yad2's "נווה עופר, תל כביר" → area 50
  only (תל כביר is neither one of the 71 names nor a known place). Private 3: the same kind, furnished `yes`, "גני
  צהלה, רמות צהלה" → area 22, whose own name it is. The agency page (outside Tel Aviv-Yafo, "עיר היין") → no area, as
  it should; its city rules it `other_city` by `native_location` (#214). `field_sources`: 11–14 fields `"form"` on
  each, the rest `"model"`. **The regression run** (`v7-none-1dada328-b5db1eb3aa49`): 108 calls, **$0.024969** of the
  $0.10 cap; both passes `fail`. **Against version 5's run** (`09f15e8dac9f`, the last: version 6 had none, #484),
  with #367's corrected truths: positions 3, 58, 59, 60 failed before and still do (`furnished`, `parking`,
  `entry_date_written`); **new: `apartment_kind` fails its 0.95 bar (2 of 32 in pass 1, positions 8 and 9; 1 in pass
  2)**, and pass 1's areas miss one post (37: [31] → []; the exact rate 0.81 → 0.74). In pass 1, 8 posts went from
  `whole_apartment` to not written (4, 8, 9, 13, 21, 24, 56, and 20 in pass 2). **The likely reason:** version 7's
  section tells the model to use the block "for apartment_kind"; on a Facebook post, with no block, it now leaves the
  kind not written where the text says it. Not proven: version 6 had no run of its own (#484), though it changed
  streets only. The other changes are expected or noise: streets now with their house number (version 6, #484); a
  prefix letter dropped or kept on names; prices of millions on sale-like posts; the two passes disagreeing as before
  (25 flips, against 29). **Not deployed.**
- **Version 8 (round 46, #522).** The "YAD2 LISTINGS" section only, reworded: it now opens with "This section applies
  only to a post that comes with a second part starting with "[Yad2 listing form — not the poster's text]". A post
  without that part is classified exactly as before, from its text alone, by the rules below: every field,
  apartment_kind included, is read from the text as usual, and nothing in this section applies to it.", and its four
  rules are for "such a post only". `PROMPT_VERSION` "8", `PROMPT_FINGERPRINT` `16202ae9…`. **The block's handling is
  unchanged** (the same request, the same block, the same rules for a post that carries it): the block check is not
  run again (#522). **Its regression run** (`v8-none-16202ae9-5364752fe609`): 109 calls (one retried), **$0.025091**
  of $0.10; both passes `fail`, on the non-deciding fields that failed for version 5. **`apartment_kind`: 0 of 32 in
  both passes** (version 7: 2 and 1; version 5: 0); the 8 posts version 7 left not written are `whole_apartment`
  again. **`areas`: 0 errors** in both passes (version 7: 1 in pass 1); the exact rate 0.806 and 0.742 (version 5:
  0.806 in both). Every other deciding field clean, as for version 5. **Against version 5 with #367's truths:**
  `furnished` 3 and 2 of 9 (version 5: 3 and 3); `parking` 2 and 1 (1 and 1: position 9 answered `True` for "unclear"
  in pass 1 only); `entry_date_written` 2 and 2 (1 and 1: position 2 now copies "הכניסה מידית" for "מידית", also
  seen in version 7's pass 2); `broker` 0 and 1 (0 and 1); `house_committee` 0 and 0 (0 and 1). **Not deployed.**

## 6.5 The collector (#490, #506, #507): the browser, its image, and the Yad2 seam

**The browser:** Playwright for Python in `mcr.microsoft.com/playwright/python:v1.63.0-noble` (named in Playwright's
Docker page and present in Microsoft's registry; the Python package installed separately, `playwright==1.63.0`; spike
2), headed under `xvfb-run -a -s '-screen 0 1920x1080x24'`, as `pwuser` with Playwright's seccomp profile (the page's
form for crawling), with `--init --ipc=host`. The launch flag and the persistent profile as in the spikes; nothing else
(#490). **The profile** in its own folder on the server, `./appdata/yad2-profile/` in homelab's stack, bind-mounted
(outside git and the image, #499).

**Where it runs (#506, option A):** a second image (the Playwright image above plus the package); **the `scheduler`
service moves to it** and runs Facebook's jobs and Yad2's one at a time (#140 holds with no lock); every other service
keeps the slim image; the GitHub Action builds both. The scheduler then runs as `pwuser` with the seccomp profile.

**The seam (#507, option C): Yad2 is its own seam; `providers/` and its contract are unchanged.** Ron's answer says
"name and contract proposed in the plan"; round 42's plan named neither (it listed the option only). **Proposed now,
for Ron (§6.14 C2):**

| Module | Contract |
|---|---|
| `yad2/` | `Yad2Collector.collect(known: Mapping[str, datetime], *, bootstrap: bool) -> Yad2Collection` — the only code that knows Yad2's pages. `known` is every stored Yad2 post's `listing_id` → `last_published_at`, passed in by the pipeline: the seam reads no store. `Yad2Collection`: the new tokens' `RawPost`s (with the form's part of their `Listing`), the bumps found (`listing_id`, `updatedAt` as UTC), the list pages read; raises `Yad2Blocked` (§6.6). Writes nothing. Its pure parts (`pages.py`, `mapping.py`, `kinds.py`) are built in step 1 |

It answers round 42's three misfits: "new" is decided inside the seam against `known` (1); the stop rule is the seam's,
not a time (2); a bump is a known token, told by `known` (3).

**Reading both list shapes:** the seam reads the feed's `private`, `agency` and `yad2` lists, whichever are present,
and ignores the promoted lists (`platinum`, `kingOfTheHar`, `trio`, `booster`, `leadingBroker`, `lookalike`; #502
point 16).

**Paging (#492):** from page 1, by the page's own links, while a page holds a new token, at least the minimum and at
most the cap (§6.8). **Bootstrap (#493):** pages 1–3, every listing new, no alert. A new token's listing page is opened
once; one that fails to load is tried again at the next run (its token not marked seen).

**Bump detection (#504):** a **known token anywhere on the pages read** whose stored `last_published_at` is older than
a threshold has its listing page opened to read `updatedAt`; a later `updatedAt` is a bump (#492): it moves `last_published_at` only, with no repost line (#520); an archived listing bumped also returns to its state before the archive, its photos downloaded again (#524). At most a cap of
such pages per run (§6.8).

**Invariant 2 (#502 point 18):** a Yad2 run stores its new posts and its bumps **at the end, in one transaction, only
when the run succeeded**; a failed run stores nothing and marks no token as seen.

**Not used:** the map; the phone (#497); `rebouncedAt` (#492); Yad2's API outside the page.

## 6.6 Block detection and the failure alert (#490)

A run is **blocked** when either holds (spike 1 §8, spike 2 §S2.5):
1. the top document leaves Yad2 for `validate.perfdrive.com` (Radware's challenge page), or
2. no request reaches `gw.yad2.co.il` while the page loads.

**Never the word "captcha"**: every Yad2 page carries a background reCAPTCHA frame
(`www.google.com/recaptcha/api2/aframe`). A blocked run fails (`failure_kind` "blocked: …"), stores nothing, marks no
token, and the existing failure alert tells the admin once per problem (`telegram/health.py`), as a failed Facebook run
does. Headless is never used (it is blocked, spike 1's run 4).

## 6.7 The scheduler, the run record and the digest (#502 point 19) — Gate G approved, in `SCHEMA.md`

- **Rhythm** (#490): lower than Facebook's, daytime only; the numbers proposed in §6.8. One run at a time across both
  sources (#140); a Yad2 run is followed by `classify_pending`, as Facebook's is.
- **`RunRecord` version 2:** `source` (`"facebook"` / `"yad2"`; a stored version-1 run reads as `"facebook"`). A Yad2
  run writes one as `run_once` does: `trigger`, `started_at`, `finished_at`, `status`, `failure_kind`, `window_since`
  (`None`: Yad2 has no time window), `window_capped` `false`; `rows_fetched` the listings read on the list pages,
  `rows_skipped` the listing pages that failed to map. **Its Apify fields are always `None`** (`apify_run_id`,
  `charged_events`, `cost_usd`, `cost_settled_at`; the contract refuses them on a Yad2 run), so `settle_costs` skips it.
  **Built** (step 1).
- **`ScheduleSettings` version 2:** Yad2's interval and daytime hours (names in §6.14 C4; all `None` means no Yad2 runs,
  as a stored version-1 row reads). **Built** (step 1).
- **The digest:** a Yad2 line of its own (runs, failed runs, new listings, list pages read), apart from the Apify cost
  line; the group "יד2 · תל אביב-יפו" among the groups, its silence counted as any group's (#496). **As built (#535):**
  runs, failed and of them blocks, listings read (no record holds list pages), new listings, bumped listings; step 6.
- **The schedule page:** Yad2's interval and hours beside Facebook's. Step 5.

## 6.8 The paging numbers and the rhythm — APPROVED (#514), with Ron's two amendments

**Amended in round 48:** Yad2's runs start from **06:00**, not 07:00 (#527); **no cap on the listing pages a run
opens**, the morning run included (#526): the list pages stay 3 to 10 and the bump checks 10.

**Approved:** every 60 minutes; runs start between 07:00 and 23:00 Israel time; at least 3 and at most 10 list pages;
only private listings decide whether a page holds a new token (the minimum of 3 covers the agency listings at the
bottom of pages 2–3); a bump check only when the stored `last_published_at` is over 3 hours old, **at most 10
bump-check pages a run** (Ron: not 30). **Added by Ron: a pause between page loads. Chosen (round 44): 4 seconds plus a
random 0–2 seconds** before every page load after a run's first, list and listing pages alike; nothing beyond that
(#490). With up to 10 list pages and about 40–60 listing pages, the pauses add about 4–6 minutes: a run of about
15–20 minutes. The proposal as it stood before Ron's answer:

**What was measured** (§S2.3, one Saturday's midday, the laptop's shape, 20 private listings a page): private listings
are updated (new or bumped) at **37–48 an hour**; all 60 on pages 1–3 turned over in 98 minutes; the agency list is not
in date order. Not measured: the night, a weekday, an unattended run's time per page. The proposals below allow **twice
the measured rate, about 100 an hour**, for a weekday.

| # | Number | Proposed | The calculation |
|---|---|---|---|
| N1 | **The interval** | **60 minutes** | #490's own example ("hourly or every two hours"). At 37–48 private updates an hour a run finds 2–2.5 pages of them; at 100 an hour, 5: always inside the cap. Listing pages a day do not depend on the interval (they follow the updates, about 600–770); a 2-hour interval saves only list pages (about 8 runs × 3–5 pages a day) and doubles the delay to a card |
| N2 | **The daytime hours** | **runs start from 07:00 to 23:00** Israel time: 16 runs a day | Facebook's quiet hours end at 07:00 (#442); 23:00 keeps an hour before them. The night's updates (8 hours, not measured) are read by the 07:00 run |
| N3 | **The minimum of list pages** | **3** | 60 private listings: 75–95 minutes of updates at the measured rate, more than one interval, so a quiet hour still reaches the last run's listings; in the mixed shape 3 pages hold 36 agency listings, for the fixed pattern #492 names; the same 3 pages as the bootstrap (#493) |
| N4 | **The cap of list pages** | **10** | The largest expected need: the 07:00 run after 8 night hours (at a third of the day's rate, about 15 an hour: about 120 updates, 6 pages); a failed run doubling the gap (2 × 48 ≈ 100, 5 pages); a weekday hour at 100 (5 pages). 10 pages (200 private) covers each with room; at the spike's 19–63 s a page, 3–10 minutes |
| N5 | **"A page holds a new token" counts private listings only** | **Yes** (refines #492: §6.14 C3) | Measured: the agency list moves up and down regardless of date, and unseen agency tokens stand at the bottom of pages 2–3 (§S2.3). Counted on every token, the paging would run to the cap on most runs until the whole agency stock (about 1,300) is seen; counted on the private list (newest first), it stops when the private listings are known. Agency tokens on the pages read are still collected when new |
| N6 | **The cap of bump-check pages** | **30 a run, private tokens first** (approved as **10**, #514) | Once the stock is seen, nearly every private update on the pages read is a bump of a known token: 37–48 an hour, about 40 a run. With the new tokens' pages (falling as bumps rise) a run then opens about 40–60 listing pages; 30 bump checks keep it near that and leave the rest to later runs while they stay on the pages read. Private first because their position means a recent update; a known agency token's position does not (it would fill the cap every run) |
| N7 | **The bump threshold** (§6.5) | **`last_published_at` older than 3 hours** | Pages 1–3 hold 75–95 minutes of private updates at the measured rate: a known private token there whose stored time is over 3 hours old has been bumped, with a margin for slower hours. A false check costs one page and finds the same `updatedAt` (no repost) |

**A run's time, estimated** (not measured unattended): 3–10 list pages at 20–60 s, plus 40–60 listing pages at about
10 s, **10–15 minutes**; Facebook's next run waits for it (#140). **Page loads on Yad2 a day:** about 50–160 list pages
(16 runs × 3–10) and about 600–900 listing pages, steady after the first weeks; how many a profile can make without a
challenge is not measured (spike §10). The first unattended days measure both, and the numbers are editable on the
schedule page.

## 6.9 Photos, retention, the card, alerts

- **Photos:** downloaded at fetch from `img.yad2.co.il` by the existing download (no host rule there), into
  `<store_root>/images/`, as Facebook's; a listing removed from Yad2 keeps its photos until retention. **The media's
  shape waits for §6.14 C1.** **A listing with no photo is not rejected** (#510): it shows as usual, without a photo.
- **Retention (#471, the rule unchanged; #502 point 20):** archive at 25 days, delete at 40 days from
  `last_published_at`; **a bump resets the clock** (it moves `last_published_at`). **A listing removed from Yad2** is
  not seen by the collector: it ages out by the same rule. Nothing more.
- **The card:** a source badge (Facebook or Yad2, #500); Yad2's neighbourhood and street as given (#498); the
  description as the original text (none for a listing with no description, #509); **"open on Yad2"** (the permalink)
  in place of the Facebook link; **no WhatsApp button** and no phone (#497). The alert's buttons the same way.
- **Alerts:** the same rules (`policy/alert.py`); the bootstrap alerts nothing (#493); a bump alerts nothing (#492); a
  post published (`updatedAt`) more than 24 hours before the alert pass never alerts (#473). **In the first weeks a
  bump of a listing never seen is a new token** (§S2.3, §6.14 C5).

## 6.10 Tests, with no network

- **Fixtures read in place from `data/raw/`**, gitignored, copied once from the spikes with dated names (round 43):
  `yad2_listing_private_{1,2,3}_2026-10-24.html`, `yad2_listing_agency_1_2026-10-22.html` (spike 1's agency page,
  outside Tel Aviv-Yafo: read for the agency's fields only), `yad2_list_page1_2026-10-24.html` (the laptop's shape; the
  kinds' search options). **Copied in round 47:** `yad2_list_page{2,3}_2026-10-24.html` (the same list run as page 1),
  `yad2_list_mixed_page1_2026-10-24.html` (the server's shape), `yad2_challenge_2026-10-22.html` (spike 1's run 4) and
  `yad2_radware_interstitial_2026-10-24.html` (Radware's check page, the server run's first document). **A missing fixture fails the test**, as today. **The phone
  responses are never fixtures** (#494; deleted, #505).
- What they pin: the `RawPost` table (§6.2) field by field; the form's part (§6.3) and `field_sources`; the 22 kinds
  against Yad2's own options; `updatedAt` → UTC (also across a daylight-saving change); Yad2's `listing_id`, and
  Facebook's unchanged; the stored version-1 rows read as version 2; no phone request in the `yad2/` package (step 1).
  Later steps: the block beside the text, never inside it, not normalized (invariants 8, 14); block detection on the
  challenge page and not on a normal page with the reCAPTCHA frame; a failed run storing nothing (invariant 2);
  Facebook's tests unchanged.
- The browser itself is not run in tests: the seam's page reading is tested on saved HTML.

## 6.11 Cost (updated from the measured volume, §S2.3)

- **Yad2 costs no Apify money.** The model: on the measured day, 168 calls cost $0.044 by the usage metadata (#448)
  and the bill for the day was $0.06 (#449): about $0.0003–0.0004 a call. A Yad2 call carries a longer description
  (313–386 characters on spike 2's private listings) and the block (#503): estimate **$0.0004 a call**.
- **Model calls a day = new Yad2 tokens a day**, less the kinds rejected before the model (parking and storage were 12
  of spike 1's 200 map markers, about 6%).
  - **The first weeks** (most updates are tokens never seen, §S2.3): about 600–770 private a day, plus the agency stock
    (about 1,300) seen over the first days: **about 700–900 calls a day, $0.28–0.36 a day, about $8–11 for the first
    month.**
  - **After about 45 days** (the stock seen; new listings only): at least about 70 private a day plus agency's (not
    measured): **about 100–200 calls a day, $0.04–0.08 a day, about $1–2.5 a month.**
- One-off: the regression run, under its $0.10 cap (§6.4, #511).
- The server: one Chromium and one Xvfb per run, 16 runs a day of 10–15 minutes (§6.8).

## 6.12 For Ron — answered (2026-10-24, `DECISIONS.md` #502–#511)

| # | Point | Answer |
|---|---|---|
| 1 | The Gate A table (§6.2) | As proposed (#502); the media row: §6.14 C1 |
| 2 | `RawPost.schema_version` with the new `source` value | Stays 1 (#502) |
| 3 | `native_currency` `"ILS"` stated for Yad2 | As proposed (#502) |
| 4 | `author_name` = the poster's name | As proposed (#502) |
| 5 | `field_sources`, `Listing` version 2 | As proposed (#502) |
| 6 | Floor 0 / −1; `squareMeter` | As proposed, checked on the bootstrap's posts (#502) |
| 7 | `includeFurniture` true | The model chooses (#502) |
| 8 | `streets`, `stated_area_names` from the form, exempt from #162 | As proposed (#502) |
| 9 | Dedup A on Yad2's description | **B: not for agency listings** (#508) |
| 10 | The proposed kinds | `not_listing` (#502) |
| 11 | `not_listing` kinds before the model | Yes (#502) |
| 12 | What the block carries | Neighbourhood, street, **and the property kind, `isForPartners`, `furnitureInfo`** (#503, amends #498) |
| 13 | The regression run and a Yad2 set | **The regression run only; no Yad2 labelled set** (#511) |
| 14 | Where the browser runs | **A: a second image; the scheduler moves to it; the Action builds both** (#506) |
| 15 | The `providers/` contract | **C: Yad2 its own seam** (#507); name and contract: §6.5, §6.14 C2 |
| 16 | Ignore the promoted lists | Yes (#502) |
| 17 | Bump detection | **Open the page, with a cap; a known token checked wherever it stands on the pages read** (#504) |
| 18 | Store at the end, on success | Yes (#502) |
| 19 | Gate G: `RunRecord.source`; Yad2's rhythm in `ScheduleSettings` | Yes, version 2 on each (#502); names §6.14 C4 |
| 20 | A listing removed from Yad2 | Nothing beyond retention (#502) |
| 21 | The three phone responses | **Deleted in round 43** (#505) |
| 22 | The DoD | As drafted (#502) |
| 23 | A listing with no description | **B: not `no_text`; the form fills, the model gets the block only** (#509) |
| 24 | A listing with no photo | **B: not rejected, shown without a photo** (#510) |
| 25 | #495 and #501 together | As proposed (#502) |

## 6.13 Build step 1 (round 43): what is built

- `parsing/datetimes.py`: `parse_israel_local_utc` (Yad2's `updatedAt`, Israel time → UTC; the autumn change's
  repeated hour reads as summer time, the spring gap with winter time) and `parse_local_date` (`entranceDate`, the
  calendar date as written). `parsing/ids.py`: `compute_listing_id(…, source=)`, Yad2's `sha256("yad2:" + token)`;
  Facebook's unchanged.
- `contracts/raw_post.py`: `source` `"yad2"`; the `listing_id` check by source. `contracts/listing.py`: `field_sources`
  (default `{}`), version 2, `Listing.from_stored_json` (a version-1 one reads as version 2), read by both stores.
  `contracts/run_record.py`: `source` (default `"facebook"`), version 2, `from_stored_json`; a Yad2 run refuses Apify
  fields. `contracts/schedule_settings.py`: the Yad2 rhythm (default `None`), version 2, `from_stored_json`.
  `state/runs.py` reads every row through them. Reclassify leaves `field_sources` out of the compared fields.
- `yad2/pages.py` (the page's `__NEXT_DATA__` and the `"item"` query's `data`), `yad2/kinds.py` (the 22 kinds),
  `yad2/mapping.py` (`to_raw_post`, `form_fields`, `photo_urls`).
- Tests: `tests/test_yad2_mapping.py` (the spikes' pages, read in place), `tests/test_phase6_contracts.py` (no fixture).
  **Facebook's tests pass; no test of Facebook's behaviour changed.** Five test files that pin a schema's version or
  field list were updated for the approved versions: the `ListingExtraction` drift test (`field_sources` among the
  fields code fills, Gate B's own list), `test_listing.py`'s field list, `test_gate_g.py`'s "unknown version" example
  (2 → 3), and the reclassify tests' hard-coded current `Listing` version (1 → `LISTING_SCHEMA_VERSION`).
- **A stored version-1 `Listing` reads as version 2** (as the earlier gates read their records), so reclassify's
  triple (#217) does not select every stored Facebook `Listing` for the added field alone.

## 6.14 Contradictions and names: all answered (C1–C6 round 44, #512–#517; C7 round 45, #520)

| # | What | Options | Proposed |
|---|---|---|---|
| C1 | **The media row contradicts Gate A** (presented, not resolved). The approved §6.2 row gives a Yad2 photo `media_id: None` and `page_url: None`; Gate A types both `str` (not nullable); the photo download keys each `PostImage` on `media_id` (`PostImage.media_id: str`), and the alert finds its photo by `media_id`. With `None` every photo of a listing would share one key | **A.** `media_id` = the photo's URL (unique per photo, unsigned, stable by its form), `page_url` = the listing's permalink: no type change. **B.** Both nullable: a Gate A type change, and a new key for the download and the alert | A. Until then step 1 maps `media` as `[]`; the photos stay in `raw` |
| C2 | **The seam's name and contract** (#507 says "proposed in the plan"; round 42's plan had neither) | §6.5's `yad2/` and `Yad2Collector.collect(known, *, bootstrap) -> Yad2Collection`; or another shape | As in §6.5; listed so in CLAUDE.md's seam table |
| C3 | **#492's stop rule meets the measured agency order** (§S2.3): "while a page holds a new token" would page to the cap on most runs | Count private tokens only (N5); or keep every token and accept the cap | Private only |
| C4 | **`ScheduleSettings`' Yad2 field names** (#502 point 19 approved the fields, not their names) | `yad2_interval_minutes`, `yad2_hours_from`, `yad2_hours_until` (Israel time, `HH:MM`, from before until; runs start inside; all three `None` = no Yad2 runs), as built | As built |
| C5 | **Old listings bumped look new in the first weeks** (§S2.3): a token never seen is new (#492), so a long-listed apartment bumped today becomes a card and can alert | Accept; or a later rule on `createdAt` (a filter change, not proposed) | Accept; watch the first week |
| C6 | **`field_sources` for `streets` and `stated_area_names`** when the form gives one and the model adds more (#502 point 8) | `"form"` when the form gave a value; or `"model"` | `"form"` (the form's value leads the list) |
| C7 | **A bump has no carrier for its repost line — answered: A (#520).** #492: a bump "updates `last_published_at` and the repost log gets a line". The repost log is derived from the duplicate records pointing at the post (Gate E, "Repost log"; not stored); a Yad2 bump keeps its token, so its `listing_id` (#496): no record holds the second publication. `last_published_at` can move; the repost line has nowhere to come from | **A.** No repost line for a Yad2 bump: the card's time moves, nothing else (amends #492). **B.** A stored record of each bump (a new record or field: a Gate E change). **C.** Each bump stored as a duplicate `RawPost` with its own id (breaks #496's `listing_id`) | A, the simplest; B if Ron wants the history |

**Answers (round 44):** C1 option A (#512); C2 as proposed (#513); C3 private only (#514); C4 as built (#515); C5
accepted (#516); C6 `"form"` (#517). Also #518 (nothing for the model: `no_text`) and #519 (the block check).

## 6.13b Build step 2 and version 7 (round 44): what is built

- `yad2/mapping.py`: the media (#512); `model_block` (#503); `is_agency` (#508).
- `premodel/rejects.py`: Yad2's pre-model rules (`not_listing` by kind; `no_text` only with nothing for the block,
  #518; never `no_images`); `rejected_before_model`, so a model's `not_listing` is never re-checked back to pending.
- `dedup/stage_a.py`: text hashes match only within one source; an agency listing is never grouped, as a new post
  or as a stored match. `dedup/stage_b.py`: `pair_rules` never ties a Facebook post and a Yad2 listing (#500).
- `classify/complete.py`: the form merged over the model's answer, `field_sources` for every field, the form's names
  first and exempt from #162, a model name equal to the form's merged, not counted as dropped.
  `classify/openai_classifier.py`: the request's parts (§6.4). `classify/instructions.txt`: version 7.
- Tests: `tests/test_yad2_rules.py` (40, no fixture); `tests/test_yad2_mapping.py` (the media and the block on the
  saved pages). Facebook's tests unchanged but for `test_classify_instructions.py`'s pinned version ("6" → "7").

## 6.13c Build step 4 (round 47): what is built

- `yad2/feed.py`: the feed's `private`, `agency` and `yad2` lists in the page's order, the promoted lists left out; the
  page's own pagination link labelled with the next number (never one leaving `www.yad2.co.il`).
- `yad2/block.py`: `PageLoad` (the address asked, the final address, the last Yad2 document's body, the hosts that
  answered) and the two signs of §6.6; no word in a page or a frame is looked at (a test pins that no `yad2/` module
  holds it).
- `yad2/collector.py`: `Yad2Collector.collect(known, *, bootstrap)` with §6.8's numbers (3 to 10 list pages, private
  tokens decide, bootstrap 3 pages and no bump check; bump checks over 3 hours, at most 10, private first; 4 s plus
  0–2 s before every load but the first); a listing page that fails to load or to map is skipped (`skipped`, the
  `RunRecord`'s `rows_skipped`), its token not stored; a list page that fails fails the run; a block raises
  `Yad2Blocked` at once.
- `yad2/browser.py`: Playwright, headed, the spikes' profile and flag, only the calls the spikes ran (`ASSUMPTIONS.md`
  Y1); imported when the browser opens, so the slim image needs no Playwright. Not run in this round.
- `yad2_run.py`: the run's wiring: `known` from the store, the collection, dedup A, the bumps (#520, #524: a duplicate's
  bump also moves its canonical's clock, as a repost does), the photos, then **one transaction**
  (`Repository.save_batch`, new on the Repository contract, both stores), then the `yad2-tel-aviv` record
  (`watermark.window.advance_group`, the per-group rule Facebook's `advance` now calls too): its rows are the new
  listings and the bumps.
- `dedup/stage_a.py`: `bumped_lifecycle` (#524), sharing #74's state rule.
- Tests: `test_yad2_collector.py` (synthetic pages, no fixture: the rules), `test_yad2_list_pages.py` (the saved pages:
  both shapes, the links, the challenge and check pages, a bootstrap over pages 1–3), `test_yad2_run.py` (the store,
  invariant 2, the bumps, the archive return with its photos), `save_batch` in `test_repository_contract.py`.

## 6.13d Build step 5 (round 48): what is built

- `jobs/run_yad2.py`: the Yad2 run command (no key read). It bootstraps itself with no `yad2-tel-aviv` record (#529);
  writes its `RunRecord` (`source` `"yad2"`; `rows_fetched` the listings read, `rows_skipped` the pages skipped; a
  block's own reason as `failure_kind`; the Apify fields `None`), closing a record left running first; opens the
  browser on `data/yad2-profile/`.
- `schedule.py`: each source's `timer_base`; `yad2_rhythm_of` (Yad2's interval, its off-hours as the quiet hours);
  `YAD2_DEFAULTS` (60, 06:00, 23:00).
- `jobs/scheduler.py`: both sources, one run at a time, **Facebook's looked at first on every pass** (#528); Yad2 only
  while its three settings are set and inside its hours, Facebook's quiet hours not applying to it; `run_yad2 --trigger
  scheduled` under `xvfb-run -a -s '-screen 0 1920x1080x24'`, then `classify_pending --cap 0.05`; "run now" stays
  Facebook's; a change of Yad2's settings logged.
- `telegram/health.py`, `watch.py`: `failed_runs` and `no_run` on Facebook's runs; `yad2_failed` (the newest Yad2
  run failed) and `yad2_no_run` (Yad2's own rhythm, while it is on); no "no run" while any run is in progress (#530).
- `web/admin.py` and the schedule page: Yad2's switch and three fields (off by default, 60 / 06:00 / 23:00 offered),
  its next run, each run's source; the save takes the three, or three nulls.
- `Dockerfile.browser` (#531) on Playwright's image pinned by digest, the `browser` dependency group
  (`playwright==1.63.0`, locked, installed only there), uid 10001, the scheduler as its command; the Action builds and
  publishes `…-browser` beside the slim image.
- homelab's `stacks/tlv-hunter/`: the scheduler on the browser image, the `yad2` service, Playwright's seccomp profile
  (§6.16).
- Tests: `test_run_yad2_job.py`, the Yad2 parts of `test_scheduler.py`, `test_watch.py`, `test_schedule.py`,
  `test_web_schedule.py`, `test_deploy_files.py`.

## 6.13e Build step 6 (round 49): what is built

- `web/cards.py`: each card and opened post carries `source` ("facebook" / "yad2"); a Yad2 post's `whatsapp` is `None`
  and its `phones` empty (`shown_phones`), whatever its description holds (#497, #534); `web/admin_rows.py` the same
  for the admin's rows and opened post.
- The front end: the source pill at the end of the kind row (#533); the link "יד2" in place of "פייסבוק"; the location
  as Yad2 gave it (the form's neighbourhood and street, first in their lists, #517), the colour still the area's;
  "פורסם … · יד2" in the opened post; "צפייה בסרטון ביד2"; the admin's "המודעה ביד2", and its city ruling "לפי שדה
  העיר של יד2" for a Yad2 post.
- `notify/alert.py`: the "יד2" button with the listing's link, no WhatsApp; "- שכונה:", "- רחוב:" as given (#534).
- `telegram/alerts.py`: `yad2_bootstrap_end` and `due_alerts(…, yad2_end=)`: no Yad2 post first stored by the first
  succeeded Yad2 run alerts, and none before it (#525); the bot reads the run records until it is found. A bump and a
  return from archive were already held back by the post's own times (#520, #524): pinned by tests.
- `telegram/digest.py`: "-ריצות פייסבוק-" counts Facebook's runs; "-יד2-" (#535) when Yad2 ran in the window; a failed
  Yad2 run listed as "יד2 · …"; the bot names the group "יד2 · תל אביב-יפו".
- Tests: `test_yad2_card_alert.py` (12), the Yad2 cards in `Card.test.tsx` (3), one heading in `test_watch.py`.
- **Checked and unchanged:** the filters (no rule names a source; the broker filter reads the form's value, #501);
  the Gate D key and dedup A (already within a source, #500); the price-mismatch line (text-sourced prices only, so
  never a Yad2 post); retention (the same rule, #502 point 20).

## 6.16 The stack and the deploy (#532) — for step 7, after step 6 is built

**Images:** `ghcr.io/ron45700/tah-tlv_apartment_hunter:latest` (slim: `site`, `jobs`, `bot`) and
`ghcr.io/ron45700/tah-tlv_apartment_hunter-browser:latest` (`scheduler`, `yad2`), each also `:sha-<short>`.
Playwright's base is 1,014 MB compressed (amd64); the unpacked size is seen at the first pull.

**homelab's `stacks/tlv-hunter/compose.yaml`:** `scheduler` on the browser image, `ipc: host`,
`security_opt: seccomp=./seccomp_profile.json` (Playwright v1.63.0's, in the stack folder, in git), the new folder
`./appdata/yad2-profile:/app/data/yad2-profile`, `stop_grace_period: 90m`; a `yad2` service (profile `jobs`, the same
image, folders and options, no key) for a Yad2 run by hand:
`docker compose run --rm yad2 xvfb-run -a -s '-screen 0 1920x1080x24' python -m tlv_hunter.jobs.run_yad2`, the
scheduler stopped first (#140). Every other service unchanged.

**The deploy (Ron; nothing here has run):**
0. Commit and push both repos; the Action builds both images. **On the new `…-browser` package's page, make it public
   as the slim one is** (it is private on its first publish; making it public cannot be undone).
1. On `homeserver`: `cd ~/homelab && git pull && cd stacks/tlv-hunter`, then
   `mkdir -p appdata/yad2-profile && sudo chown 10001:10001 appdata/yad2-profile && chmod 700 appdata/yad2-profile`.
2. **A fresh backup first** (the rollback point: the deploy writes version-2 `Listing`, `RunRecord` and
   `ScheduleSettings` rows an older image cannot read): `docker compose run --rm jobs python -m
   tlv_hunter.jobs.export_backup --no-photos`. A rollback is this backup and the previous `sha-` tags.
3. **Dockge "Update" with no run in progress** (`docker logs --tail 3 tlv-hunter-scheduler` ends with an `exit` line or
   the quiet hours' line). Then `docker logs --tail 5 tlv-hunter-scheduler`: `… yad2 off`.
4. On the site, "תזמון": Yad2 shows off; tick it, keep 60 / 06:00 / 23:00, save. The scheduler logs `===== yad2 every
   60 minutes, starting 06:00-23:00`; inside the hours the first Yad2 run starts at once and is the bootstrap (3 pages).
5. Read its run on the schedule page (source "יד2", rows) and the cards; `docker image prune` afterwards.

## 6.15 Out of this plan

Cross-source dedup and perceptual photo comparison (#500, "Future"); the phone (#497); Yad2 outside Tel Aviv-Yafo
(#491); a Yad2 labelled set (#511).
