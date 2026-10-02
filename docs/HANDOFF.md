# TLV Apartment Hunter — Project Handoff

**Status:** planning complete, all external dependencies verified, ready for architecture + implementation planning.
**Last updated:** 2026-09-13
**Owner:** Ron

> Written in English because it is a technical spec destined for Claude Code.
> Conversation language is Hebrew.

---

## 1. What this is

A personal, non-commercial tool that monitors public Tel Aviv apartment Facebook groups,
classifies posts with an LLM, and pushes matching listings to Telegram in near real time.

**The problem it solves:** good rooms in TLV go within hours. Manually scanning 6+ groups
several times a day is not feasible, and a post that appeared 10 hours ago is usually gone.

---

## 2. Decision log (with rationale)

| # | Decision | Why |
|---|---|---|
| 1 | **No Facebook account. No login. Public groups only.** | Meta made public-group content visible to logged-out visitors. Removes account-ban risk entirely — the single largest risk in the original plan. |
| 2 | **Never paste own `sessionCookies` into any actor** | Hands credentials to a third party and reintroduces exactly the account risk decision 1 removed. Hard line. |
| 3 | **Buy collection from Apify, don't build a scraper** | Selector rot is the real maintenance killer (weeks, not months). Outsourcing it moves the fragile part to someone else's problem. |
| 4 | **Provider adapter layer from day one** | Already proven necessary: the first provider was blocked mid-project. Three providers evaluated, all with incompatible schemas. |
| 5 | **Everything runs in the cloud (GCP)** | Once collection moved to Apify, the home/residential IP stopped being an asset. No Raspberry Pi, no home laptop, no local collector. |
| 6 | **LLM classifies; we filter on structured fields** | Keyword pre-filtering is fragile in Hebrew (negation, prefixes, `/` forms). Filtering on model output is re-runnable and changeable without re-scraping. |
| 7 | **The model classifies only — never summarizes** | Ron always reads the original text. A summary adds tokens and hallucination surface for zero value. |
| 8 | **`null` is information, not failure** | Distinguishes "the poster didn't write it" from "we don't know". Drives triage ranking, not rejection. |
| 9 | **Telegram push only in v1. No buttons, no dashboard.** | Dashboard comes after the bot works. Interactive buttons would require webhook + state for no v1 benefit. |
| 10 | **Daily digest message is v1, not a nice-to-have** | Ron's criteria are narrow. Silence and failure look identical without it. It is a measuring instrument. |
| 11 | **Bootstrap mode on first run** | First run pulls a backlog and would fire ~30 messages in a row. First run writes to DB and sends one summary. |
| 12 | **Keyword sniper runs in shadow, as QC — not as a filter** | Kept because it is already written and tested. Disagreements with the model flag posts worth eyeballing. |
| 13 | **Nothing is ever deleted** | Rejected posts are stored with the reason. Feeds the future "rejected" dashboard pane. |
| 14 | **Never advance the watermark on a failed run** | A skipped window is a permanently missed apartment. |
| 15 | **Include `new_north` in the allowed areas at launch** | Derech Namir / Arlozorov sit on the old-north/new-north boundary. Better a little noise than a missed border listing. |

### Working method (keep doing this)
Every external dependency is tagged `VERIFIED` / `ASSUMED` / `UNKNOWN`.
**Nothing moves to implementation while resting on `ASSUMED`.**
This came from a past project (Anizai) where a nearly complete Reddit producer was built
before discovering the API no longer existed.

---

## 3. Verified facts

All verified against a real 20-post run on 2026-09-13 (cost: under $0.10).

| Fact | Status | Evidence |
|---|---|---|
| Facebook Graph **Groups API is dead** | ✅ VERIFIED | Removed 2026-04-22 across all API versions. No sanctioned path exists. |
| Public group posts readable **logged out** | ✅ VERIFIED | Meta Nov-2025 change; both actors return data with no cookies. |
| Hebrew post text arrives **complete** | ✅ VERIFIED | 108–1,572 chars, all end naturally (phone numbers, closing lines). No truncation, no "See more". |
| `creation_time` parses cleanly | ✅ VERIFIED | 20/20 with `email.utils.parsedate_to_datetime` (thedoor, RFC 2822 GMT). |
| Images available | ✅ VERIFIED | 18/20 posts, 82 items. thedoor `media[].uri` at `mx1200x1600`. |
| **Image URLs expire within days** | ✅ VERIFIED | Signed `scontent.*.fbcdn.net` links. Fine for Telegram (downloads on send), breaks a dashboard. |
| Post volume | ✅ VERIFIED | 20 posts spanned 30.6h across 2 groups ≈ **8 posts/group/day**. 6 groups ≈ 50/day. Very cheap. |
| **Duplicates are severe** | ⚠️ VERIFIED | **3 duplicate pairs in 20 posts (15%)**. Two pairs were *within the same group* — different `post_id`, identical text. `post_id` dedup is NOT sufficient. |
| `sale_post` / `isMarketplaceListing` means **rental**, not sale | ✅ VERIFIED | 8/20 flagged. Titles: `להשכרה 3 חדרים`, `Room Only`. Rejecting on type would lose 40% of data. |
| Marketplace listings carry **structured price** | ✅ VERIFIED | thedoor: `sale_post.price/title/location`. memo23: `marketplacePrice`. |
| Model price == marketplace price | ✅ VERIFIED | Two independent sources agreed exactly on both marketplace posts (₪3,560 / ₪8,700). |
| `user.id` is a rotating `pfbid…` | ⚠️ VERIFIED (partially) | Same in both providers. **Never use as an identity key.** |
| Gemini classification accuracy | ✅ VERIFIED | **10/10** on real posts, including 4 deliberately adversarial cases. See §6. |

> **Corrected 2026-09-14 (Gate A).** `user.id` is **not always** a rotating `pfbid`. At least one
> post in the 20-post sample returns a plain numeric ID (`558703982`) with a real vanity profile
> URL. The rule is unchanged — never use it as an identity key — but the reason is stronger: it is
> sometimes stable and sometimes not, with no way to tell in advance. See `SCHEMA.md`, Author.
>
> Also corrected: the marketplace flag in thedoor output is `sale_post.isOnMarketplace`, not
> `isMarketplaceListing`, and it was **`false`** on a structured `sale_post` with a price and a
> location. "Structured listing" and "appears on Marketplace" are two different things.
> `sale_post.price` is a **string with a currency symbol** (`"₪3,600"`), not a number.

---

## 4. Providers

### Primary: `thedoor/facebook-group-post-scraper`
4.5K users · 232 MAU · 4.2★ (8) · 28K runs · ~$1.50/1K results

```json
{
  "url": ["https://www.facebook.com/groups/XXXX/"],
  "maxPosts": 10,
  "sortingOrder": "newest_posts",
  "fetchAllComments": false,
  "includeTopComment": false
}
```

- `maxPosts` is **per group**, not total.
- `sortingOrder` must be `newest_posts`. **Never `newest_activity`** — it mixes old bumped
  posts into the feed, which breaks both the date filter and the watermark.
- `postsNewerThan` accepts relative (`30 minutes`) or absolute ISO. This is the watermark hook.
- ⚠️ `fetchAllComments` **defaults to `true`** and bills per result. Always set it false.
- ⚠️ **No diagnostic rows.** Private/failed groups are silent in the dataset; errors go to the
  **run log only**. We must detect "group returned nothing" ourselves.
- ⚠️ `post_type: "shared"` arrives with empty `text`; real content sits in `sharedPost`.

### Backup: `memo23/facebook-public-group-posts-scraper`
1.2K users · 443 MAU · 5.0★ (3) · 52K runs · $1.50/1K + $0.10/1K additional + $0.008 start ·
9.7h issue response

Verified working on the same groups. Loses `title`, `location`, and image resolution.

### Field mapping (both verified against real output)

| Canonical | thedoor | memo23 |
|---|---|---|
| `source_post_id` | `post_id` | `legacyId` (`id` is base64) |
| `permalink` | `post_url` | `url` |
| `text` | `text` | `text` |
| `posted_at` | `creation_time` — RFC 2822 str, `parsedate_to_datetime` | `time` — ISO, `fromisoformat` |
| `group_id` | `group_id` | `facebookId` |
| `group_title` | ❌ | `groupTitle` (often empty, HTML-escaped) |
| images | `media[].uri` (mx1200x1600) | `attachments[].thumbnail` (s590x590) |
| listing price | `sale_post.price` | `marketplacePrice` |
| listing title | `sale_post.title` ✅ | ❌ |
| listing location | `sale_post.location` ✅ | ❌ |

### Groups (all public, verified)
```
35819517694        (דירות מפה לאוזן בת"א)
333022240594651
101875683484689
5612809662118963
733810383372996
295395253832427
```

### Rejected providers
- `apify/facebook-groups-scraper` — official, well-built, but ~$5/1K → ~$1,200/mo at target polling.
- `bombi_carl/crazy-cheap-facebook-group-posts` — $0.10/1K but **marked "Under maintenance"**, untouched 6 months, 5 MAU.
- `dami_studio/facebook-groups-scraper` — good design and honest README, but relies on a
  **shared Facebook session baked into the actor**; it got blocked during this project.
  This is what proved the adapter layer necessary.

---

## 5. Architecture

```
Cloud Scheduler ──> Cloud Run Job ──> Apify (sync API) ──> Normalize ──> Dedup ──> Gemini ──> Firestore
   (every 30m)            │                                                                       │
                          └────────── Watermark (per group) ◄──────────────── Telegram push + daily digest
```

**Key choices:**
- **Synchronous Apify call** (`run-sync-get-dataset-items`), not webhooks. Runs return tens of
  posts; async would add run-state management for nothing.
- **Our scheduler, not Apify's.** Apify's scheduler injects static input; `postsNewerThan` is
  dynamic per run.
- **Firestore.** Thousands of rows and 48 runs/day fit the free tier with no instance to manage.
- **`price_source` field.** `native` when from marketplace metadata, `llm` otherwise.
  Log a `price_mismatch` in the digest when both exist and disagree.

### Contracts

**`RawPost`** — provider-agnostic boundary
`source`, `source_post_id`, `group_id`, `group_title`, `permalink`, `text`, `posted_at` (UTC),
`fetched_at`, `media[]`, `native_price`, `raw` (untouched original JSON)

**`Listing`** — LLM output, pydantic-validated. Wraps `RawPost`, never replaces it. See `schema.py`.

**`GroupWatermark`** — `group_id`, `last_post_ts`, `last_success_at`, `consecutive_failures`

**`Notification`** — `listing_id`, `sent_at`, `channel`. Separate from post dedup.

### Watermark rules (all four matter)
1. Watermark = **highest `posted_at` seen**, not run time.
2. Always subtract a **10–15 min overlap buffer**; dedup catches the repeats. Zero overlap loses posts silently.
3. **Per group**, never global.
4. **Only advance on a successful run.** A throttled run that advances the window loses that window forever.

### Dedup (verified essential — 15% duplicate rate)
1. `source_post_id` — exact repeats
2. **Hash of normalized text** — catches reposts with new IDs. *This is the one that matters.*
3. Phone number — a one-directional signal, not a key
4. Fallback: price + rooms + street

> **Corrected 2026-09-14 (task 1.2).** Layer 3 originally read "the real primary key of a listing."
> That was wrong. Phone numbers appear in only **10 of 20** posts, and **both** posts in one of the
> three duplicate pairs have no phone at all — relying on phone as the key would have missed a
> third of the duplicates. A shared phone is strong evidence of the same listing; a missing or
> differing phone carries no information. Layer 2 is the primary key; layer 4 carries more weight
> than originally assumed, because it covers the rewritten-text case that phone cannot.
> See `ASSUMPTIONS.md` D5–D7.

---

## 6. LLM extraction

**Gemini Flash, `temperature=0`, structured output.** Files: `gemini_system_prompt.txt`,
`gemini_response_schema.json`, `schema.py`, `prompt.py`.

**`listing_type` and `duration` are separate fields.** Forced by real data: `סאבלט ארוך`
posts are simultaneously a room in a shared flat *and* a sublet. One field loses one of them.

### Test results — 10/10 on real posts

| Case | Expected | Got |
|---|---|---|
| `מחפשים שותף/ה` | `any` | ✅ |
| `מחפש שותף/שותפה` | `any` | ✅ |
| `עדיפות לבנות` | `women_preferred` | ✅ |
| `סבלט ארוך` + room | `room_in_shared` + `sublet` | ✅ |
| Arlozorov + `צפון חדש` | `new_north` (not `old_north`) | ✅ |
| `3,333` suspicious price | literal from text | ✅ not a hallucination |
| No broker signal | `is_agent: null` | ✅ did not guess |

`confidence` does discriminate (0.9 on the sparsest post, 1.0 elsewhere).

### Known minor issues (fix in prompt)
1. `entry_date` sometimes returns `"immediate"` instead of the Hebrew as written.
2. One case inferred `has_living_room: true` from apartment size with no textual basis.
   Isolated, not a pattern — tighten the never-invent rule anyway.

### Not yet tested
Post #18 (`אנחנו שני שותפים שמחפשים דירת 3 חדרים`) → should be `seeking`.
Not blocking: the deterministic sniper catches it.

---


## 8. Keyword sniper (QC, not a filter)

`sniper.py` — deterministic, tested, **7/20 on real data, all correct**.

### Three traps proven on real data — do not undo these
1. **Never fold final letter forms, never strip `/`.** `מחפשים שותף/ה` normalizes into
   `מחפשים שותפה` and gets falsely rejected. Both of the best listings in the sample used this form.
2. **Negation guard.** `לא סאבלט` must not match `סאבלט`.
3. **Tiered rules with overrides.**
   - `seeker` rules are cancelled by an offering signal (`חדר פנוי`, `מתפנה`, `יש לנו`)
   - `city` rules are cancelled by any TLV indicator — `5 דקות מגבעתיים` in a TLV flat is fine

Normalization touches only: nikud, Hebrew quote marks, whitespace collapse. Nothing else.

Fixes already applied from real data: removed `אנחנו שני` as an offering signal (it appears in a
seeker post), broadened `דירה` → `דיר[הת]`, added `עדיפות לבנות`.

---

## 9. Open items

| Item | Note |
|---|---|
| GCP project | Account with active billing exists; project **not yet created** (deliberate) |
| Apify plan | Free tier so far; measure real monthly cost before subscribing |
| Gemini pricing | Verify current rates — volume is ~50 posts/day, expected to be trivial |
| Area boundary | `new_north` included at launch; revisit after a week of real data |
| Comments | Post comments sometimes hold price/phone. `thedoor/facebook-comment-scraper` if needed later. Not v1. |
| Image re-hosting | Cloud Storage bucket needed **only** when the dashboard arrives. Schema must preserve `media[]` now so history survives. |

---

## 10. Next steps

1. **Architecture + tech stack + implementation phases summary** ← next conversation starts here
2. Macro plan, then semi-macro plan
3. Phase-1 spec for Claude Code, including:
   - which of Ron's existing GitHub plugin skills apply
   - `CLAUDE.md` structure
   - documentation files that preserve continuity across sessions

---

## Attached files
- `sniper.py` — deterministic Hebrew keyword sniper
- `test_sniper.py` — trap demonstrations
- `schema.py` — `Listing` pydantic model, `passes_filter`, `completeness`
- `prompt.py` — system prompt + Gemini response schema
- `gemini_system_prompt.txt` / `gemini_response_schema.json` — paste-ready
- `test_posts.json` — 17 deduplicated real posts (regression set)
