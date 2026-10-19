# Schema

**The only source of truth for fields, types, and filter rules.**

Nothing here is written without Ron's explicit approval. Nothing outside this file redefines it —
code, prompts, and other documents reference it, never restate it.

**Last updated:** 2026-10-18 (round 31) — **Gate F approved by Ron (`DECISIONS.md` #453):** `telegram_chat_id` and `telegram_linked_at` on `User` (schema version 2; a stored version-1 user reads as 2), `TelegramLinkCode` and `SentAlert`; the Phase 0 stub contracts removed. Before that, 2026-10-12 (round 8) — **a field moved, approved explicitly by Ron (`DECISIONS.md` #317):**
`include_sublets` is now one switch on `Profile` (schema version 2), no longer one per `SearchOption`; a stored version-1
profile reads as version 2. Before that, 2026-10-11 (round 6) — rule text only, approved by Ron: a correction of `other_city` in force
outranks Facebook's location field (Gate B, "The city comes from…", `DECISIONS.md` #296); the gate table's row D says
the grouping is computed once for all users and held in memory, never written on a post (#301). No field or type
changed.

**Earlier, 2026-10-11 —** R7 reworded (`DECISIONS.md` #291): disabling a user and ending their sessions are two
calls in a fixed order, the disable first. No field or type changed.

**Earlier, 2026-10-10, round 3 —** **Gate C approved by Ron** (`DECISIONS.md` #288): its names and types, points
R1–R9, and the Gate E amendments E-1 to E-5, now written into Gate E's text (amended 2026-10-10); the "PROPOSED"
table removed. No other gate changed.

**Earlier, 2026-10-10, round 2 —** **Gate C revised after Ron's answers** (`DECISIONS.md` #258–#287): a `Session` record,
`disabled_at` and the sign-in delay fields on `User`, `CriterionLevel` in place of `wanted`, every answered point written
in; still DRAFT, NOT APPROVED, with one table of names and types for Ron. Gate E's proposed amendments E-1 to E-5
revised; its approved text unchanged.

**Earlier on 2026-10-10:** **Gate C drafted, NOT APPROVED:** its content is approved by Ron (`DECISIONS.md`
#242–#257); the records, names and types below are proposals, with open points. Proposed amendments to Gate E sit
next to its approved text, which is unchanged. No approved field, type or rule changed.

**Earlier, 2026-10-05 (task 2.2):** **The model decides the area** (`DECISIONS.md` #167):
`areas` moves into `ListingExtraction`, still stored on `Listing` as approved; the area rules and
the translation table's rows become instructions; the lookup key and the prefix rule are
superseded (#168). Approved by Ron. No field or type of `Listing` changed.

**Earlier on 2026-10-05 (spike day):** **Approved by Ron:** the model's response
(`ListingExtraction`, `DECISIONS.md` #151) and the Gate E classification-failure fields with
`PostLifecycle` `schema_version` 2 (#152). Docs only; no code yet.

**Earlier on 2026-10-05:** **Gate B approved by Ron** (`DECISIONS.md` #123–#125): a
month with no day is the 1st, "end of February" the 28th; an unmapped area name lets the street
decide. Lookup keys for street and area names (#135). Two proposals added, not approved: the
model's response (`ListingExtraction`, #137) and the Gate E classification-failure fields (#139).
Rules name "the model", not a provider (#129).

**Earlier on 2026-10-05:** **Gate B: names and types approved by Ron, with his changes
(`DECISIONS.md` #108–#119).** `areas` added, `stated_areas` replaced by `stated_area_names`,
`gender` plain, sizes decimal, unclear keeps no value, the native price floor. Still a draft: two
open points remain. Gates A and E untouched.

**Earlier on 2026-10-05:** **Gate B draft added, not approved.** Its content was approved in
substance by Ron (`DECISIONS.md` #81–#107); the names and types in it are a proposal awaiting Ron.
No approved field or type changed; Gates A and E untouched.

**Earlier, 2026-10-04 (#80):** **Gate E download rule, wording only:** a network error waits on a fixed
schedule instead of the one retry within a run; a failed photo is also retried from the stored link
while its post is less than 4 days old. Approved by Ron (`DECISIONS.md` #80). No field or type changed;
`schema_version` stays 1.

**Earlier on 2026-10-04 (task 1.13):** **`GroupWatermark` rules, rule text only:**
`watermark`, `last_success_at` and `consecutive_failures` have their rules; the `posted_at` row
says that "never run time" is about `watermark`, while the run's window starts from
`last_success_at`. Approved by Ron (`DECISIONS.md` #78 W1, W5a, W5b). No field or type changed;
`schema_version` stays 1.

**Earlier on 2026-10-04 (task 1.12 review):** **Gate E download rule, wording only:** a
repost's photos, retries included, are attempted only while the canonical holds no image
(`DECISIONS.md` #77 D2, amended). Approved by Ron. No field or type changed; `schema_version`
stays 1.

**Earlier on 2026-10-04 (task 1.12):** **Gate E, wording only:** the download rule states
`DECISIONS.md` #76 (every canonical with photos, whatever its state); the `images` row is one
entry per photo attempted; the "Reposts" and retry rules reflect #77 D2–D4. Approved by Ron
(`DECISIONS.md` #77). No field or type changed; `schema_version` stays 1.

**Earlier on 2026-10-04 (task 1.11 planning):** **Gate E, "Reposts" rule reworded:** an
identical-hash repost downloads its photos while the canonical has no successfully downloaded image
(no `PostImage` with a `local_path`), or when the canonical is archived. This replaces the "all of
its images failed" and "no media at all" cases. Approved by Ron (`DECISIONS.md` #72.3). No field or
type changed; `schema_version` stays 1.

**Earlier on 2026-10-04 (task 1.1):** **Gate A shared-post fallback wording:** `width` /
`height` of a shared media item are taken when present, `None` when absent, like own media.
Approved by Ron (`DECISIONS.md` #71 G). No field or type changed; `schema_version` stays 1.

**Earlier on 2026-10-04:** **Gate E, "Reposts" rule:** a third case, approved by Ron
(`DECISIONS.md` #70): an identical-hash repost also downloads its images when the canonical has no
media at all. No field or type changed; `schema_version` stays 1.

**Earlier on 2026-10-04 (task 1.10):** **Gate E amended** (`DECISIONS.md` #66, #67), approved
by Ron: `flagged_by` is `str | None`; `PostImage` typed; consistency rules on `rejection_reason`,
the flag and `PostImage`; `no_images` means no media at all, stated apart from the download rule;
"Stub contracts" wording on where `GroupWatermark` is built; an explicit `listing_id` row on the
post lifecycle record (its key, already in the code). No other field added or removed;
`schema_version` stays 1 on every record.

**Earlier on 2026-10-04:** **Gate E approved** (post lifecycle record, `GroupWatermark`).
**Gate A amended:** `media[]` falls back to `sharedPost.media`; a shared post is detected by
`sharedPost` being present. Both approved by Ron, 2026-10-04 (`DECISIONS.md` #63). `post_type`
wording updated to the observed values. No `RawPost` field or type changed; `schema_version` stays 1.

**Earlier on 2026-10-04:** `Media` wording: `Photo` items, not only `Video`, can omit
`width`/`height` (spike 1.1a). Earlier the same day: the `phones` row states the `DECISIONS.md` #57
rule (an identical number within one post is stored once). **No field or type was changed.**

**Previously:** 2026-10-03 — wording aligned to `BASELINE.md`. No field, type or rule was changed.
Gate E was added to the table and Gate C widened, per `DECISIONS.md` #59.

| Gate | Covers | Status |
|---|---|---|
| A | `RawPost` | ✅ Approved 2026-09-14 |
| E | Post lifecycle record (state, rejection reason, flag, last publication, images, classification failures) and `GroupWatermark` | ✅ Approved 2026-10-04; classification-failure fields approved 2026-10-05 (#139, #152); amended 2026-10-10 for Gate C (`"misclassified"`, the restore rule, the exemption, `schema_version` 3; #288) |
| B | `Listing`, and the model's response `ListingExtraction` | ✅ Approved 2026-10-05 (#81–#125; the response #137, #151) |
| D | Dedup stage B key | ✅ Key decided 2026-10-08 (#230, rule 1 amended by #232: a shared phone that is not an agent number and the fields rule, or an identical photo and one of the two rules; nothing else merges). **Nothing is stored:** the result is derived from the stored posts and never written onto a post (#231); it is the same for every user, computed once for all users, held in the site's memory and computed again only when the store changed (#301); no field, record or schema change |
| C | Filter rules, and the user, key, session, profile, viewed-post, report and correction records | ✅ Approved 2026-10-10: content #242–#257, #262–#287; names and types, R1–R9 and the Gate E amendments #288 |
| F | Telegram: the link on `User`, `TelegramLinkCode`, `SentAlert` | ✅ Approved 2026-10-18 (#453) |

---

# GATE A — `RawPost`

**Approved:** 2026-09-14
**Schema version:** 1

## Purpose

`RawPost` is the **provider boundary**. Its single job is to be the shape after which no module in
the system knows whether the data came from thedoor or memo23. That is what makes swapping a
blocked provider a one-file change.

It is **not** an understanding of the listing. It does not know the price, the area, or whether
this is a room in a shared flat — that is `Listing`, and that is Gate B. `RawPost` knows only what
the provider said.

## Why this gate is cheap and Gate B is expensive

**Every `RawPost` field is a pure function of `raw`.** If we later decide we want a field we did
not promote, we run a script over stored `raw` and backfill it. No model call, no cost, no lost
history.

This is **not** true of `Listing`, where every new field costs a model call per post across all
history. Hence: promote conservatively here, deliberate exhaustively at Gate B.

**The only exception** is data determined at fetch time and absent from `raw`: `source` and
`fetched_at`. Those must be right from the start.

## The promotion criterion

Since `raw` is stored whole, the question is never "might I need this?" — everything is kept
regardless. The question is: **will I filter, query, or dedup on it?** If not, it stays in `raw`.

---

## Fields

### Identity and provenance

| Field | Type | Source (thedoor) | Rationale |
|---|---|---|---|
| `schema_version` | `int` | — | `reclassify` depends on it entirely. Without it there is no way to know which records need reprocessing. |
| `source` | `str` | — | `"thedoor"` / `"memo23"`. Set at fetch time, not present in `raw`. The only trace of origin after normalization. |
| `source_post_id` | `str` | `post_id` | Facebook's own post ID, as the provider gave it. Dedup layer 1. |
| `listing_id` | `str` | derived | `sha256(source_post_id)`. **`source` is deliberately excluded** — see below. |
| `group_id` | `str` | `group_id` | Per-group watermark, silent-group detection. |
| `group_title` | `str \| None` | ❌ (memo23 has it) | Displayed on the card. |
| `permalink` | `str` | `post_url` | The link Ron clicks. |
| `posted_at` | `datetime` (UTC) | `creation_time` — RFC 2822, `parsedate_to_datetime` | **A group's `watermark` is the max of this**, never run time. The run's window starts from `last_success_at`, the last successful run's start (`DECISIONS.md` #78 W1). |
| `fetched_at` | `datetime` (UTC) | — | **When we first saw it.** The gap from `posted_at` measures how slow we are. On re-fetch the rest of the record is overwritten but this value is **kept** — the watermark overlap re-fetches the same post almost every run, so overwriting would destroy the measurement. Set at fetch time. |
| `raw` | `dict` | whole response item | Untouched. The basis for `reclassify` and for every future field. |

### `listing_id` — what it is and is not

`listing_id` is **our record identifier**: the stored record's ID and what a sent-alert record
points at. It is **not** part of dedup logic.

Two records can be the same apartment and still have different `listing_id` values — exactly the
three duplicate pairs found in task 1.2. **`listing_id` is unique per post, not per apartment.**
Apartment-level identity is the canonical `listing_id`, and `duplicate_of` points at it.

**`source` is excluded from the hash on purpose.** thedoor's `post_id` and memo23's `legacyId` are
both Facebook's post ID — the same post carries the same number from either provider. Including
`source` would make one post produce two records the moment a failover happens, which is precisely
the provider-failover scenario. Excluding it lets dedup layer 1 work across providers, not only within one.

### Content

| Field | Type | Source | Rationale |
|---|---|---|---|
| `text` | `str` | `text`, falling back to `sharedPost` | What is sent to the model **verbatim**. |
| `text_source` | `str` | derived | `"text"` / `"shared_post"` / `"none"`. When a post comes out `no_text`, this separates "empty share" from "post that is entirely an image" — two different cases Ron will want to tell apart in the admin's rejected list. |
| `post_type` | `str` | `post_type` | Observed: `regular`, `sale_post`, `shared`, `shared_reel`, `__reel__` (spike 1.1a, 2026-10-04). Not used to detect a shared post: `shared`, `shared_reel` and `__reel__` can all carry a `sharedPost`, so a shared post is detected by `sharedPost` being present. |

### Media

| Field | Type | Source | Rationale |
|---|---|---|---|
| `media[]` | `list[Media]` | `media[]`, falling back to `sharedPost.media[]` | `{type, uri, width, height, media_id, page_url}`. `width` and `height` are `int \| None`: `Video` items, and some `Photo` items, **omit the keys entirely** — a missing key maps to `None`. |

`uri` is a signed `scontent.*.fbcdn.net` link that expires within days, which is why images are
downloaded at fetch time (`BASELINE.md` §3). **`page_url` does not expire** — it is the fallback
when a download failed, and a reason `media[]` is stored even though the URLs rot. Its shape depends on the item type: `facebook.com/photo/?fbid=…` for photos, a
`/videos/` page for videos. Do not assume the photo form.

**Shared-post fallback (Gate A amendment, 2026-10-04).** When the post's own `media[]` is empty and
`sharedPost` is present, `media[]` is mapped from `sharedPost.media[]`: `type` → `type`, `uri` →
`uri`, `id` → `media_id`, `url` → `page_url`, and `width` / `height` are taken when the item
carries them and are `None` when the keys are absent, the same as own media (most shared items
carry neither; a `Reel` item in spike 1.1a carries both). *Wording amended 2026-10-04,
`DECISIONS.md` #71 G.* No type changes. **Condition:** before task 1.1 relies on it, verify against the
spike data that `sharedPost.media[].url` is a non-expiring Facebook page link like `page_url`, not a
signed CDN link. *Checked 2026-10-04 against both spike datasets:* all 65 `sharedPost.media[].url`
values are `www.facebook.com` page links (`photo/?fbid=…`, `video.php?v=…`, `reel/…`), the same
forms as the posts' own `page_url`, with no `oe` or signature parameter; the signed CDN link is in
`uri`. That they never expire rests on the same basis as `page_url`: link form, not observation
over time.

`Video` items also carry an extra `thumbnail` key that photos do not. Not promoted — it stays in
`raw`, backfillable if it ever earns promotion.

Not promoted: `thumbnail` (duplicates `media[0]`), `text_preview` (a truncation of `text`).

### Structured listing metadata

Present only on `post_type: "sale_post"`.

| Field | Type | Source | Rationale |
|---|---|---|---|
| `native_price` | `int \| None` | `sale_post.price` | Parsed from `"₪3,600"` to `3600`. Two independent providers agreed exactly on this value — a source of truth that did not pass through a model. |
| `native_price_raw` | `str \| None` | `sale_post.price` | The original string. If parsing is wrong, the source must be visible. |
| `native_currency` | `str \| None` | derived | `"ILS"`. Parsed from the symbol, not assumed. |
| `native_title` | `str \| None` | `sale_post.title` | Sometimes more concise than the post text. Note: contains bidi control marks (U+200E) — strip before display. |
| `native_location` | `str \| None` | `sale_post.location` | A location field that never passed through a model. |

`price_source` (`"native"` / `"llm"`) belongs to `Listing`, not here — `RawPost` only records what
the provider supplied.

**Not promoted, left in `raw`:** `sale_post.isOnMarketplace` and `sale_post.isSold`. Neither will
be filtered or grouped on. `isOnMarketplace` was `false` even on a structured `sale_post`, so it
does not mean what the research notes first implied; `isSold` is provider-reported and unverifiable for a
rental — `false` does not mean the room is free. Both remain backfillable from `raw` if they ever
earn promotion.

### Author

| Field | Type | Source | Rationale |
|---|---|---|---|
| `author_name` | `str \| None` | `user.name` | Never part of the hash. But one name posting fifteen listings is a broker — a signal that cannot be computed without storing it. |
| `author_id_raw` | `str \| None` | `user.id` | Stored, **never a key**. See below. |
| `author_profile_url` | `str \| None` | `user.profileUrl` | The only way to reach a poster when there is no phone — and there is no phone in half the posts. |

**`user.id` is not always a rotating `pfbid`.** Most posts return `pfbid0uUyZMG…`, but at least one
returns a plain numeric ID (`558703982`) with a real vanity profile URL. The research notes first
stated it is always a rotating `pfbid`; that is inaccurate. The rule is unchanged — never use it as an
identity key — and the justification is now stronger: it is sometimes stable and sometimes not, and
there is no way to tell in advance. A key that is sometimes stable is worse than one that never is.

Not promoted: `actors[]` — a duplicate of `user` in every observed post. Recorded as `ASSUMED`;
stays in `raw`.

### Opportunistic fields

Captured when the provider supplies them, never requested and never paid for.

| Field | Type | Source | Rationale |
|---|---|---|---|
| `top_comment` | `dict \| None` | `topComment` | Arrives sometimes even with `includeTopComment: false`. Comments occasionally carry a price or phone. Keep what is free; do not fetch more. Most posters write "details in DM", so expected value is low. |
| `reactions_count` | `int \| None` | `reactions_count` | Zero on all 20 sampled posts — possibly a logged-out limitation. Kept in case they start arriving: a listing with 30 comments has probably already gone. |
| `comments_count` | `int \| None` | `comments_count` | As above. |
| `shares_count` | `int \| None` | `shares_count` | As above. |

### Derived fields (populated by `textnorm` and `dedup`)

**All five are nullable, and `None` means "not computed yet"** — not "computed and found empty".
This matters because the code that fills them arrives across two phases, and a non-nullable field
would force an early phase to store a claim it cannot support.

The pair `(no_text, text_hash)` resolves the ambiguity: `no_text=True` with `text_hash=None` means
"deliberately unhashed"; `no_text=None` means "textnorm has not run".

| Field | Type | Computed in | Rationale |
|---|---|---|---|
| `text_hash` | `str \| None` | Phase 0 | sha256 of aggressively normalized text. Dedup layer 2, the primary key. `None` when `no_text` is `True` — two empty strings must never collide — or when textnorm has not run. |
| `phones` | `list[str] \| None` | Phase 0 | Dedup layer 3, a one-directional signal. ~50% coverage. **Stored normalized**: digits only, `+972` converted to a leading `0`, so `05X-XXXXXXX` and `+9725XXXXXXXX` both become `05XXXXXXXX`. One stored format is what makes an equality lookup in the store possible; nothing is lost, since the card always shows the full original text and `raw` keeps the rest. An identical number within one post is stored once, in order of first appearance (`DECISIONS.md` #57). `find_by_phone` normalizes its input before comparing. `None` means not extracted; `[]` means extracted and none found. |
| `no_text` | `bool \| None` | Phase 0 | Stored, and rejected with the reason "no text" (`BASELINE.md` §5). **Not sent to the model** — we do not analyse images. Seen only in the admin's rejected list. True when the text is absent, whitespace-only, **or normalizes to nothing** (an emoji-only post). A post that normalizes to nothing must never raise: a failed run does not advance the watermark, so one throwaway post would block the window permanently. `text_source` still records where the text came from — `"text"` with `no_text=True` means it arrived and was unusable. |
| `is_canonical` | `bool \| None` | Phase 1 (task 1.3) | Dedup result. A property of the post, not of any user, so it lives here and not on `Decision`. |
| `duplicate_of` | `str \| None` | Phase 1 (task 1.3) | The canonical `listing_id` this post duplicates. `None` is ambiguous on its own — read it together with `is_canonical`. |

---

## Provider coverage

`RawPost` is provider-agnostic, which means some fields are `None` under one provider and populated
under the other.

| Field | thedoor | memo23 |
|---|---|---|
| `group_title` | ❌ | ✅ |
| `native_title` | ✅ | ❌ |
| `native_location` | ✅ | ❌ |
| `native_price` | `sale_post.price` | `marketplacePrice` |
| media resolution | `mx1200x1600` | `s590x590` |

**`None` in `RawPost` means "this provider does not supply the field", not "the poster did not
write it."** The second meaning belongs to `Listing`. Do not conflate them.

memo23 has **not** been verified against a real response by anyone but Ron, at research time. Its
input field is `startUrls`, not `url`. See `ASSUMPTIONS.md` M1–M3; verification happens when the
failover adapter is built.

---

## Invariants for this schema

1. `raw` is stored whole and never trimmed.
2. `author_id_raw` is never a key, never part of a hash.
3. `author_name` is never part of the hash — the same apartment posted by two different flatmates
   must still collide.
4. `text_hash` is `None` whenever `no_text` is `True`, and whenever textnorm has not run.
5. All datetimes are tz-aware UTC; conversion to Israel time happens only in message formatting.
6. Adding a field here later is a backfill script over `raw`, not a reclassification.
7. On upsert of an existing `listing_id`, `fetched_at` is preserved from the first write.

---

# GATE E — post lifecycle and `GroupWatermark`

**Approved:** 2026-10-04 · **Reasons:** `DECISIONS.md` #63, amended by #66, #67, #70, #72, #76,
#77, and #139 / #152 (2026-10-05) ·
**Lifecycle:** `BASELINE.md` §5

## Post lifecycle record (`PostLifecycle`)

A **separate record per post, keyed by `listing_id`. Not added to `RawPost`**: Gate A stays a pure
function of `raw`, and these fields change after fetch.

**Amended 2026-10-04** (`DECISIONS.md` #66), approved by Ron: the `flagged_by` type, the
`PostImage` types, and the consistency rules on `rejection_reason`, the flag and `PostImage`. Then
an explicit `listing_id` row, the key the record already had. No other field was added or removed;
`schema_version` stays 1.

**Amended 2026-10-05** (`DECISIONS.md` #139, #152), approved by Ron: `classification_failures` and
`last_classification_error`; `schema_version` goes to 2. A stored record at version 1 reads as 0
and `None`. Docs only until task 2.5 (`PHASE_2.md`).

**Amended 2026-10-10** (`DECISIONS.md` #251, #254, #255, #279–#283, #285, #286; names approved with Gate C, #288),
approved by Ron: the rejection reason `"misclassified"` (E-1), `flagged_by`'s meaning (E-2), the restore rule (E-3),
the deletion exemption of a reported post (E-4), and `schema_version` 3 (E-5). Every write of the record is a compare
and set against the record as the writer read it (#260; not a schema change).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | 1 until #152's fields are built, then 2; a version-1 record reads with the two new fields at 0 and `None`. **3 from 2026-10-10** (`"misclassified"`, #285): a version-1 or version-2 record reads as version 3 and is written back as 3 on its next save. On every record (`PHASE_1.md` §1.0) |
| `listing_id` | `str` | The post this record belongs to, and the record's key |
| `state` | `"pending"` / `"active"` / `"rejected"` / `"archived"` | On store: `"pending"`, or `"rejected"` if a pre-model reject applies. In phase 2 the model moves it to `"active"` or `"rejected"`. A repost record has no card of its own; that is `is_canonical` / `duplicate_of` from Gate A, not a state |
| `rejection_reason` | `"no_text"` / `"no_images"` / `"other_city"` / `"seeking"` / `"for_sale"` / `"not_listing"` / `"flagged"` / `"misclassified"` / `None` | One reason, the first that applies, in that order. `"misclassified"` (2026-10-10, #279) is set while any "wrong classification" report of the post is open (Gate C); a post both flagged "lied" and reported shows `"flagged"`. `"other_city"` is decided by Facebook's location field when the post has a usable one, else by the model (#214). `None` when `state` is `"pending"` or `"active"`; required when `"rejected"`; optional when `"archived"` (an archived post keeps its reason) |
| `flagged_by` | `str` / `None` | A `User.user_id` (Gate C), never a username. Set by a "lied" flag, or by a report: the first reporter (#280), so a reclassify treats a reported post as flagged (#217 (5)). Set together with `flagged_at`: both or neither |
| `flagged_at` | `datetime` UTC / `None` | Set together with `flagged_by`: both or neither; for a report, the first report's time. `rejection_reason` `"flagged"` or `"misclassified"` requires both |
| `flag_note` | `str` / `None` | Optional short note from the flagger |
| `last_published_at` | `datetime` UTC | The latest `posted_at` of the post and all its duplicates (any dedup layer: A now, B in phase 2). A phone-only match is not a duplicate. Never moves backwards |
| `images` | `list[PostImage]` | One entry per photo attempted: a failed download is recorded too. See below |
| `classification_failures` | `int` | Starts at 0. Plus 1 for each run of the classification job in which the post failed after that run's retries; at 3 the job skips the post, which shows in the admin's pending list with its reason. Not counted for a failed reclassify (the old `Listing` stays), nor when the job stops for its own cap or the project's spend limit. Left as it is after a later success; set back to 0 by hand only (the admin's "retry" in phase 3) (#139, #152) |
| `last_classification_error` | `str` / `None` | A short reason for the latest failure (`"timeout"`, `"schema: …"`, `"refusal"`, `"incomplete"` and so on). `None` while there has been none. Left as it is after a later success (#139, #152) |

### `PostImage`

| Field | Type | Rule |
|---|---|---|
| `listing_id` | `str` | The record the image came from |
| `media_id` | `str` | |
| `local_path` | `str` / `None` | `None` when the download failed |
| `error` | `str` / `None` | A short reason when the download failed |

Exactly one of `local_path` and `error` is set.

### Rules with no field of their own

- **Repost log:** derived from the records whose `duplicate_of` points at the post. Not stored.
- **Restore** (amended 2026-10-10, #251, #281–#283): one rule for a post flagged "lied" and a reported post.
  Restore clears `flagged_by`, `flagged_at` and `flag_note`, marks every open or left-out report of the post
  `"restored"` (#278, #286), and sets `state` and `rejection_reason` to what they would be with no flag or report,
  derived by `postmodel.rejects` (the `other_city` rule of #214 included) from the `Listing` with the admin's
  corrections in force applied (#281): `"active"`, or `"rejected"` with the derived reason. A post that is
  `"archived"` stays `"archived"`, its reason re-derived (#283). *Until 2026-10-10: restore cleared the flag and
  `rejection_reason` and set `state` to `"active"`.*
- **Flagged posts:** archived at 25 days (images deleted) and never deleted. The full record,
  including `raw`, is kept as the prompt regression set. A restored post follows normal retention.
  **The same for a post whose `rejection_reason` is `"misclassified"`** while it is reported, a left-out post
  included (2026-10-10, #255, #286). **The report and correction records (Gate C) are never deleted**, also after
  their post is (#255).
- **Rejection as `no_images`** (`DECISIONS.md` #67): only when the post has **no media at all**. A
  post whose only media is video or reel is not rejected. For a post that shares another post, the
  same test applies to the shared post's media: it is rejected only if the shared post has no media
  either. This is the rejection rule; the download rule below is separate.
- **Images (download):** photos are downloaded for every canonical post that has photos, whatever
  its state, a `no_text` post included (`DECISIONS.md` #76). Photos only, no video or reels (a
  video shows its `page_url` link). One retry within a run for an error that is not a network
  error; a network error (DNS, connection, timeout) waits 1, 3, 5 and 10 minutes, per outage,
  inside the run's download budget (`DECISIONS.md` #80). On a later run, whenever a post is
  fetched again, each of its own photos not held is attempted again and its error entry is
  replaced by the new result (#77 D2). On every run, a photo whose entry is a network error or
  `not attempted: time budget` is also attempted once from the stored link, without a fetch,
  while its post is less than 4 days old; an HTTP error replaces the entry and ends it (#80). A repost's photos, retries included, are attempted only
  while the canonical holds no image; once it holds one, a repost's failed photo keeps its error
  entry (#77 D2, amended). A failed download fails neither the run nor the post.
- Images are downloaded also for posts the model will reject, and deleted at archive like any post.
- **Reposts:** a repost with an identical text hash downloads no images, except while the
  canonical has no successfully downloaded image (no `PostImage` with a `local_path`), or when the
  canonical is archived; then the repost's photos are downloaded (`DECISIONS.md` #70, #72.3).
  "Archived" is read on the stored record, before a repost returns it from archive: the reposts
  that brought it back this run download; a canonical still archived downloads nothing (#77 D4).
  A canonical and its reposts new in the same run: the canonical first, its retry included, then
  its duplicates in canonical-rule order, each checked after the previous one finishes (#77 D3).

## `GroupWatermark`

One record per group.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1. On every record (`PHASE_1.md` §1.0) |
| `group_id` | `str` | |
| `watermark` | `datetime` UTC / `None` | The highest `posted_at` seen in the group; never moves backwards. `None` until the group returns its first post. Does not set the run's window (`DECISIONS.md` #78 W1) |
| `last_success_at` | `datetime` UTC / `None` | The start of the last successful run, read from our clock before `fetch()` (#78 W5a). The run's window starts at the earliest of these, minus the buffer |
| `consecutive_failures` | `int` | Per group: consecutive successful runs in which the group returned zero rows; reset to 0 when it returns any row (#78 W5b). Not a count of failed runs: nothing is written after a failed run |

Every field changes only after a successful run, for all configured groups together (invariant 2).

---

# GATE B — `Listing`

**Approved:** 2026-10-05 · **Reasons:** `DECISIONS.md` #81–#107 (content), #108–#119 (names and
types), #123–#125 (the last two points). The stubs below (`ListingStub`) are replaced by it, not
extended. The model's response shape, `ListingExtraction`, follows this gate (#151).

**Schema version:** 1

## The record

A **separate record per post, keyed by `listing_id`** (#89), like `PostLifecycle`. Not added to
`RawPost`: Gate A stays a pure function of `raw`. The record's existence means the post was
classified.

It holds what the model extracted (#92), the areas included (#167), and its provenance (#90). It holds no rejection and no user's view of the post: the
rejection reason is derived by code and written on `PostLifecycle` with Gate E's values (#92); a
user's evaluation is never written on the post (invariant 12).

What the model returns is not exactly this record (code adds the provenance, `price_source`, the
native fallback and the completed entry-date year, drops unmatched phone names, and drops a street,
area name or other city the post does not contain). The
response shape, `ListingExtraction`, is below, after this gate (#137, #151).

### `Marked[T]` — the state structure (#91, #109)

| Field | Type | Rule |
|---|---|---|
| `state` | `"written"` / `"not_written"` / `"unclear"` | |
| `value` | `T` / `None` | Required when `state` is `"written"`; `None` when `"not_written"` or `"unclear"`: nothing read is kept for an unclear field |

"No" is a written value (`state="written"`, `value=False`), never `"not_written"`.

### Provenance

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `listing_id` | `str` | The post this record belongs to, and the record's key |
| `model_name` | `str` | The model identifier as sent in the call |
| `prompt_version` | `str` | Changes whenever the prompt changes, with or without a schema change |
| `classified_at` | `datetime` UTC | When the model's answer was received |

### Kind of post

| Field | Type | Rule |
|---|---|---|
| `post_nature` | `"rental_offer"` / `"sublet_offer"` / `"seeking"` / `"for_sale"` / `"not_listing"` | Plain, not `Marked`: there is no "unclear" (#93). A sublet is a post that says so or states an explicit temporary period, and only when the offer itself is temporary: a sublet offered as an option before a regular lease is `"rental_offer"` (#159); someone seeking a sublet is `"seeking"`. `"seeking"`, `"for_sale"` and `"not_listing"` lead to the Gate E reasons of the same names, derived by code (#92). `"sublet_offer"` is not a rejection |
| `apartment_kind` | `Marked["room" / "whole_apartment"]` | `"room"` is a room in a shared flat. "3 rooms, suits roommates" and a studio are `"whole_apartment"` (#94) |

### Price and entry

| Field | Type | Rule |
|---|---|---|
| `price` | `Marked[list[int]]` | ILS, usually one item. From the text. Only when the text has no price at all, from `RawPost.native_price`, and only if it is at least 500 (a constant, not config; below it the post has no price) (#114). When both exist and differ, the text wins. A per-roommate price for a whole apartment, or another currency: `"unclear"`, and an unclear text price stays unclear even when a `native_price` exists (#95, #114). Filtering uses the lowest; the card shows `X/Y` (#95) |
| `price_source` | `"text"` / `"native"` / `None` | `None` exactly when `price.state` is `"not_written"` |
| `entry_date_written` | `str` / `None` | The entry date exactly as written, never replaced (#96). `None` when the post gives none |
| `entry_date` | `Marked["immediate" / date]` | The comparable value next to it. The model gives the day and month (and the year when written), or "immediate"; start / middle / end of a month are the 1st / 15th / last day (#96); a month with no day is the 1st, written; "end of February" is the 28th (#123). Code completes a missing year with the occurrence nearest to the post's publication date, before or after, on the UTC date (#115). "Flexible": `"unclear"`. A calendar `date`, not a `datetime`. The year is never displayed |

### The apartment

| Field | Type | Rule |
|---|---|---|
| `rooms` | `Marked[float]` | Whole or half numbers only. Always the total in the apartment, also for a room (#97). "דירת N שותפים / שותפות" gives N, or N+1 when the post says there is a living room: Ron's explicit exception to #106 (#161). On a room post the card shows "1 of N" (#120) |
| `floor` | `Marked[int]` | Ground floor = 0; a basement is -1 (#98, #118) |
| `building_floors` | `Marked[int]` | Only when written (#98). `floor` shows as `X/Y` only when this is `"written"` (#106) |
| `size_sqm` | `Marked[float]` | The apartment's size (#99, #118) |
| `room_size_sqm` | `Marked[float]` | The room's size, only when written (#99, #118). Card: #121 |
| `broker` | `Marked[bool]` | (#100) |
| `balcony` | `Marked[bool]` | A shared balcony is `True` (#100) |
| `parking` | `Marked[bool]` | Street parking is `False`; "option for parking" is `"unclear"` (#100) |
| `elevator` | `Marked[bool]` | (#100) |
| `air_conditioning` | `Marked[bool]` | (#100) |
| `furnished` | `Marked["yes" / "partial" / "no"]` | "Option to leave furniture": `"unclear"` (#102) |
| `arnona` | `Marked[int / "included"]` | An amount in ILS, or `"included"` in the price. "All included": `"unclear"`; one amount covering several charges ("200 for arnona, internet and cable"): `"unclear"` (#160). Stored as written, with no period: "400 per two months" is 400; never divided (#101, #116) |
| `house_committee` | `Marked[int / "included"]` | As `arnona` (#101, #116) |
| `gender` | `"no_restriction"` / `"women_preferred"` / `"women_only"` | Plain, not `Marked`. A post that says nothing about gender is `"no_restriction"`. No "men only" value. Feminine-only wording (`מחפשות שותפה`) is `"women_only"` (#103, #117) |

### Location

| Field | Type | Rule |
|---|---|---|
| `streets` | `list[str]` | The streets as written, in order of appearance; `[]` when none (#104). Stored never folded or normalized, for the card and for error analysis (#167) |
| `stated_area_names` | `list[str]` | The neighbourhood names the text itself points at, as written; `[]` when none. Plain, not `Marked` (#111). Stored never folded or normalized, for the card and for error analysis (#167) |
| `areas` | `list[int]` | Municipal numbers (`ms_shchuna`, 1–71), sorted, no repeats, **returned by the model** from the 71-entry list given in its instructions, by #88's rules given as instructions (#167). Known limit: for a post with only a street, it rests on what the model knows of Tel Aviv (#170) |
| `other_city` | `str` / `None` | The city as written, only when it is not Tel Aviv-Yafo; a city used as a landmark is not one (`BASELINE.md` §5). A city the post's text does not contain is dropped (read as `None`) and counted, as #162 does for names (#180). Code derives the `other_city` rejection from it, unless the post has Facebook's own location field, which then decides (#214); this field is the model's answer either way and is never edited |

**The area's colour** is derived from `areas`, with no field of its own (#110): one area, definite;
two or more, unclear (orange), matching and alerting if any is chosen; empty and the post gave a
street or an area name, unclear, no alert; empty and the post gave no location, not written.

### Contact

| Field | Type | Rule |
|---|---|---|
| `phone_names` | `list[PhoneName]` | Kept pairs only: a pair returned by the model is kept only when its number, normalized by the one phone normalization (`textnorm`), equals a number in `RawPost.phones` (#105). `[]` when none |

`PhoneName`: `phone: str` (normalized, as in `RawPost.phones`), `name: str` (as written).

### Rules with no field of their own

- **A value that is not written is never filled in** (#106). The model never derives a value from
  another (no rooms from the size, no total from a per-roommate price), and never computes one
  ("3.50*3.50" is not 12.25 sqm) (#162). The one exception: "דירת N שותפים" (#161).
- **A street, area name or other city the post does not contain is dropped** by code before the
  `Listing` is written, and counted in the report (#162, #180). The match is exact: a name in a
  different case is dropped (#179).
- **The source text is never touched** (#163, invariant 14): the classification job never writes a
  `RawPost`.
- **The rejection** is derived by code from the city and `post_nature`, in Gate E's order, and
  written to `PostLifecycle.rejection_reason`. A rule change re-derives; it does not reclassify
  (#92).
- **The city comes from `RawPost.native_location` when it has a usable locality** (#214): the part
  before the first comma, with format characters removed and whitespace collapsed; never "תל אביב"
  searched anywhere in the string, since the district after the comma reads "תל אביב" for Holon and
  Ramat Gan. A locality whose comparison key (dash-like characters read as a space) is "תל אביב יפו"
  or "תל אביב" is Tel Aviv-Yafo: never `other_city`, even when the model returned one. Any other
  locality is `other_city`, even when the model returned `None`. A locality with no Hebrew letter,
  or an empty one, is absent: the model decides. Nothing is stored for it: the source and the city
  to show are derived by `postmodel.rejects.other_city_name` from the `RawPost` and the `Listing`.
  **An admin's correction of `other_city` in force (Gate C) decides first**, its value or its null, before the
  native locality (2026-10-11, #296); the post as users see it is passed for it.
- **The area rules** (#88, #112, #124) are instructions to the model (#167): a stated area decides;
  a street only refines inside it; several possible areas are all returned; nothing the model can
  place returns no area. With no area name and no street, a well-known landmark that places the
  apartment decides, every area it touches when it lies on a border; a general distance phrase
  places nothing (#178). Filtering is by area, never by street.
- **Not carried over from the research schema** (`data/raw/research_listing_model_2026-09-13.py.txt`,
  `ASSUMPTIONS.md` C5), since the approved content does not list them: `confidence`, `flags`,
  `language`, `total_roommates`, `has_living_room`, `price_includes_bills`, a `duration`, and
  `"men_only"` / `"men_preferred"`.

## The 71 areas (#81)

Read 2026-10-05 from the municipality's GIS service, layer 511 `שכונות`
(`https://gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer/511`), under the
`external-contract-verification` skill: 71 features, `ms_shchuna` 1–71 with no gap, all loaded
`18/11/2024 00:59:04`. Saved as `data/raw/tlv_gis_layer511_rows_2026-10-05.json` (attributes, no
geometry) and `data/raw/tlv_gis_layer511_meta_2026-10-05.json`. `shem_shchuna` is verbatim. The
display label is the same name, except for the five entries whose geresh or parenthesis the source
places at the logical start; those carry a hand-corrected label next to the verbatim name (#119).

| `ms_shchuna` | `shem_shchuna` (verbatim) | Display label, where it differs |
|---|---|---|
| 1 | גלילות | |
| 2 | צוקי אביב | |
| 3 | אזור שדה דב | |
| 4 | נופי ים | |
| 5 | 'תכנית ל | תכנית ל' |
| 6 | כוכב הצפון | |
| 7 | 'רמת אביב ג | רמת אביב ג' |
| 8 | אפקה | |
| 9 | נוה אביבים וסביבתה | |
| 10 | רמת-אביב | |
| 11 | אוניברסיטת ת"א | |
| 12 | מרכז הירידים | |
| 13 | פארק הירקון | |
| 14 | תל ברוך צפון | |
| 15 | תל ברוך | |
| 16 | מעוז אביב | |
| 17 | 'נאות אפקה ב | נאות אפקה ב' |
| 18 | 'נאות אפקה א | נאות אפקה א' |
| 19 | הדר-יוסף | |
| 20 | קרית שאול | |
| 21 | המשתלה | |
| 22 | גני צהלה, רמות צהלה | |
| 23 | צהלה | |
| 24 | נוה שרת | |
| 25 | רביבים | |
| 26 | נוה דן | |
| 27 | רמת החייל | |
| 28 | עתידים | |
| 29 | נמל תל-אביב | |
| 30 | הצפון הישן - החלק הצפוני | |
| 31 | הצפון הישן-החלק הדרומי | |
| 32 | בבלי | |
| 33 | הצפון החדש - החלק הצפוני | |
| 34 | הצפון החדש-סביבת ככר המדינה | |
| 35 | הצפון החדש-החלק הדרומי | |
| 36 | צמרות איילון | |
| 37 | לב תל-אביב | |
| 38 | כרם התימנים | |
| 39 | נוה צדק | |
| 40 | גני שרונה | |
| 41 | מונטיפיורי | |
| 42 | צפון יפו | |
| 43 | גבעת הרצל, אזור המלאכה-יפו | |
| 44 | יפו העתיקה,נמל יפו | |
| 45 | עג'מי וגבעת עליה | |
| 46 | צהלון ושיכוני חסכון | |
| 47 | יפו ג' ונוה גולן | |
| 48 | מכללת יפו תל אביב ודקר | |
| 49 | (יפו ד' (גבעת התמרים | יפו ד' (גבעת התמרים) |
| 50 | נוה עופר | |
| 51 | אזור תעסוקה-צומת חולון | |
| 52 | פלורנטין | |
| 53 | נוה שאנן | |
| 54 | שפירא | |
| 55 | פארק החורשות | |
| 56 | קרית שלום | |
| 57 | נחלת יצחק | |
| 58 | ביצרון ורמת ישראל | |
| 59 | תל-חיים | |
| 60 | רמת הטייסים | |
| 61 | אורות | |
| 62 | יד אליהו | |
| 63 | התקוה | |
| 64 | עזרא והארגזים | |
| 65 | לבנה,ידידיה | |
| 66 | פארק דרום | |
| 67 | כפיר | |
| 68 | נוה ברבור, כפר שלם מערב | |
| 69 | נוה אליעזר וכפר שלם מזרח | |
| 70 | נוה חן | |
| 71 | ניר אביב | |

## Colloquial names (#86, #167)

Examples in the model's instructions, not a table in code (#167). The starting content:

| Written | Entries |
|---|---|
| הצפון הישן | 30, 31 |
| הצפון החדש | 33, 34, 35 |
| כיכר המדינה | 34 |
| לב העיר, לב תל אביב, מרכז העיר | 37 |
| יפו, with no detail | 42–49 |
| כפר שלם | 68, 69 |
| שרונה | 40 |

The 71 areas live in `reference/areas.yaml`, read only through `tlv_hunter/areas/reference.py`
(#175).

---

# The model's response (`ListingExtraction`)

**Approved:** 2026-10-05 (`DECISIONS.md` #137, #151). A separate pydantic response model next to
`Listing`, its JSON schema derived at runtime (#22), and a contract test asserting that every
`Listing` field is either in this model with the same name and type, or in the code-filled list
below.

| Field | Type | Rule |
|---|---|---|
| `post_nature`, `apartment_kind`, `price`, `entry_date_written`, `rooms`, `floor`, `building_floors`, `size_sqm`, `room_size_sqm`, `broker`, `balcony`, `parking`, `elevator`, `air_conditioning`, `furnished`, `arnona`, `house_committee`, `gender`, `streets`, `stated_area_names`, `areas` (#167), `other_city` | As in `Listing` | The same names, types and rules. `price` here is the text's price only; the native fallback is code's (#114) |
| `entry_date_parts` | `Marked[EntryDateParts]` | What the model reads; code turns it into `Listing.entry_date` (#115). "Flexible": `"unclear"` |
| `phone_name_pairs` | `list[PhoneNamePair]` | Every name-number pair the post gives, unfiltered; code keeps a pair only when its number matches `RawPost.phones` (#105). `[]` when none |

`EntryDateParts`:

| Field | Type | Rule |
|---|---|---|
| `immediate` | `bool` | `True` for "immediate"; then `day`, `month` and `year` are `None` |
| `day` | `int` / `None` | 1–31. Start / middle / end of a month: 1 / 15 / the last day; a month with no day: 1; "end of February": 28 (#96, #123). Required when `immediate` is `False` |
| `month` | `int` / `None` | 1–12. Required when `immediate` is `False` |
| `year` | `int` / `None` | Only when the post writes it; a two-digit year is 20YY (#178). Otherwise code completes it (#115) |

`PhoneNamePair`: `phone: str` (as written in the post), `name: str` (as written).

**Code-filled `Listing` fields** (in `Listing`, not in the response): `schema_version`,
`listing_id`, `model_name`, `prompt_version`, `classified_at`, `price_source`, `entry_date`,
`phone_names`.

The provider's structured-output rules (`RESEARCH.md` §15): every field required (an optional
value is a `null` union), `additionalProperties: false` on every object, the root an object.
Whether the schema pydantic derives passes them is the spike's first question.

---

# GATE C — users, keys, sessions, profiles, viewed posts, reports and corrections

**Approved:** 2026-10-10 · **Reasons:** `DECISIONS.md` #242–#257 (content), #262–#287 (round 1's open points), #288
(names and types, points R1–R9, the Gate E amendments) · **Amended 2026-10-12:** #317 (one sublet switch per
profile) · **Amended 2026-10-19:** #468 (`DateRangeCriterion.immediate`, #458; `HiddenPost`, #464) · **Schema version:** 1
on every record but `Profile`, which is 3 (#317, #468)

Telegram's fields (account linking, sent alerts) are Gate F's, below (#453). The Gate E amendments this gate needs
are written into Gate E (amended 2026-10-10).

**Common to every record below:**
- **Per-user data is never on the post** (invariant 12): each record is its own table, keyed by user and/or post.
  `RawPost`, `Listing` and `PostLifecycle` gain no per-user field.
- Every record has `schema_version` (`int`, starts at 1), as every stored record does (`PHASE_1.md` §1.0).
- Datetimes are tz-aware UTC (invariant 9), checked by the one `require_utc`.
- **Where they are stored** (#267): a new interface beside `state/`, in the same SQLite file, an eighth seam; it is
  `userdata/`, `UserDataStore` (#289; `PHASE_3.md` 3.4).
- Ids (`user_id`, `key_id`, `report_id`, `correction_id`) are random and opaque: 32 hex characters from the operating
  system's secure random source (#262 for `user_id`; the same form for the others, #288).

**Secrets are stored as hashes only.**
- **Passwords: Argon2id** (#262), stored as the library's encoded string (algorithm, version, parameters, salt and hash
  in one field). *Why (the assistant's proposal, approved):* a password is chosen by a person and has little entropy, so it needs a slow,
  memory-hard hash with a per-password salt. The parameters are the library's default profile, RFC 9106's low-memory
  option (`PHASE_3.md` 3.5, read 2026-10-10). Minimum length 8 (#262).
- **One-time keys and session tokens: SHA-256** of the value. *Why (the assistant's proposal, approved):* both are generated by the system
  with at least 128 random bits (keys) or 256 (session tokens), so a fast hash cannot be brute-forced, and an unsalted
  hash lets the store find the record by its hash in one lookup. The key is shown once, to the admin, at creation (#266);
  the session token lives only in the user's cookie.

## `User`

One record per account, keyed by `user_id`. Never deleted (#265).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `user_id` | `str` | Random and opaque, separate from the username (#262). The key every per-user record points at, and what `PostLifecycle.flagged_by` holds. Never shown |
| `username` | `str` | Picked at sign-up: Latin letters, digits, `_`, `.` and `-` only, 3 to 32 characters (#262). Unique case-insensitively: stored as typed, compared in lower case. Cannot be changed in this version (#262). No email (#242) |
| `password_hash` | `str` | The Argon2id encoded string. Never the password; never logged. A password has at least 8 characters (#262) |
| `is_admin` | `bool` | `True` on exactly one record, Ron's (#244) |
| `created_at` | `datetime` UTC | A new user is alerted only on posts that arrive after it (`BASELINE.md` §9) |
| `signup_key_id` | `str` / `None` | The `SignupKey` used. `None` exactly when `is_admin` is `True`: the admin's account is created by a one-time command on the machine (#244) |
| `must_change_password` | `bool` | `True` after the admin sets a temporary password (#262); the user must set a new one at the next sign-in before anything else |
| `password_changed_at` | `datetime` UTC | Set at creation and at every change or reset |
| `disabled_at` | `datetime` UTC / `None` | #265. Set by the admin to disable the user; `None` when enabled. A disabled user cannot sign in, and disabling ends their sessions; profile, viewed records and reports are kept; enabling sets it back to `None`. The admin cannot be disabled (R8) |
| `failed_sign_ins` | `int` | #264, R1. Consecutive failed sign-ins for this username; 0 after a success or a reset |
| `last_failed_sign_in_at` | `datetime` UTC / `None` | #264, R1. The time of the last failure; `None` when `failed_sign_ins` is 0 |
| `telegram_chat_id`, `telegram_linked_at` | | Gate F (#453): the link to Telegram, below; `User` is at version 2 |

**The delay after failed sign-ins (#264, R1).** From the 5th consecutive failure on, an attempt made
less than 30 seconds after the last failure is refused without checking the password, and says when to try again. A
success, or the admin's reset, sets the count to 0. An unknown username stores nothing and gets the same answer, after a
dummy Argon2id check so that it takes the same time.

## `SignupKey`

The one-time key the admin issues (#47, #243). Keyed by `key_id`. Never deleted.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `key_id` | `str` | Random and opaque; shown in the admin's key list. Not the key |
| `key_hash` | `str` | SHA-256 (hex) of the key. The key (128 random bits, URL-safe text) is shown once, at creation, and never stored (#266) |
| `label` | `str` | Set by the admin at creation, not empty (#243). Never sent anywhere (invariant 15) |
| `created_at` | `datetime` UTC | |
| `used_by` | `str` / `None` | The `user_id` created with it. Set together with `used_at`: both or neither (#243) |
| `used_at` | `datetime` UTC / `None` | |
| `cancelled_at` | `datetime` UTC / `None` | Set by the admin, only on an unused key (#243). Never set back to `None` (#266) |

**Rules.** No expiry (#243). A key is usable when `used_by` and `cancelled_at` are both `None`. Using it and creating the
`User` happen in one transaction, so a key creates one account at most (`BASELINE.md` §10).

## `Session` (#263)

A signed-in browser. Keyed by `token_hash`.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `token_hash` | `str` | SHA-256 (hex) of the session token. The token (256 random bits) is only in the user's cookie |
| `user_id` | `str` | |
| `created_at` | `datetime` UTC | The sign-in |
| `expires_at` | `datetime` UTC | `created_at` plus 30 days (#263); not extended by use (R5) |
| `ended_at` | `datetime` UTC / `None` | Set when the session ends before it expires: sign-out, a password reset (every session of the user, #263), the user's own password change (the other sessions, R3), or disabling the user (#265) |

**Rules.** A session is valid when `ended_at` is `None`, `expires_at` is in the future, and its user is not disabled. A
session of a user whose `must_change_password` is `True` reaches only the password change. Sessions are not deleted in
Phase 3 (R9; their removal, if ever, is Phase 5's retention).

## `Profile`

One per user (#245), created with the user. Keyed by `user_id`. The saved filter, and in Phase 4 what drives that user's
alerts (`BASELINE.md` §8).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | 3 since 2026-10-19 (#468; 2 since 2026-10-12, #317). A stored version-1 profile reads as version 2: its two per-option `include_sublets` become the profile's one, `True` when either was. A stored version-2 (or 1) profile reads as version 3: every `entry_date` gains `immediate` `False`, except the old chip shape (`earliest` `None`, `latest` on or before the UTC date of `updated_at` plus one day), which reads as `immediate` `True` with no dates (#458, #468, point 3). Read-time only; written as version 3 at its next save |
| `user_id` | `str` | The user it belongs to, and the key |
| `room` | `SearchOption` | The "room in a shared flat" search: posts whose `apartment_kind` is `"room"` (#245) |
| `whole_apartment` | `SearchOption` | The "empty apartment" search: posts whose `apartment_kind` is `"whole_apartment"` (#245). The name follows Gate B's value |
| `include_sublets` | `bool` | **One switch for the profile** (#317, amending #246 and #274; until 2026-10-12 one per `SearchOption`). "Show sublets too", `False` by default. A post whose `post_nature` is `"sublet_offer"` shows only when this is `True` **and** the option of its kind is `enabled`; it is evaluated with that option's values |
| `updated_at` | `datetime` UTC | The last save. A change affects alerts from then on (§8) |

**A new profile** (#268): both options `enabled`, every value unset (`[]` or `None`), `hide_women_only` `True`; the
profile's `include_sublets` `False` (#317).

**"Copy from the other option"** (#272), a UI action that writes one option's values over the other's: every field except
`enabled` (the sublet switch is the profile's, #317, so it is not copied). Into `room`, `size_sqm` is not copied (it stays `None`, #247); into
`whole_apartment`, its own `size_sqm` is left as it was.

### `SearchOption`

| Field | Type | Rule |
|---|---|---|
| `enabled` | `bool` | The option is on or off (#245). Off: no post is shown or alerted through it |
| `areas` | `list[int]` | Municipal numbers (`ms_shchuna`, 1–71), sorted, no repeats (#83). `[]` means not applied. **Critical, fixed** (#51). A post matches when any of its areas is in the list (#110) |
| `price_min` | `int` / `None` | ILS. **Critical, fixed** (#51). Compared with the post's lowest price (#95). `None` means not applied |
| `price_max` | `int` / `None` | As `price_min`. When both are set, `price_min` ≤ `price_max` |
| `hide_women_only` | `bool` | **Critical by default, may be turned off** (§8): `True` hides posts whose `gender` is `"women_only"`; `False` shows them with a red icon |
| `rooms` | `RangeCriterion[float]` / `None` | `None` is "don't care". Whole or half numbers (#271). Compared with `Listing.rooms` (the total in the apartment, #97) |
| `floor` | `RangeCriterion[int]` / `None` | -1 (basement) or more (#271). Ground floor 0 (#98, #118) |
| `size_sqm` | `RangeCriterion[float]` / `None` | **Only in `whole_apartment`; always `None` in `room`** (#247). Compared with `Listing.size_sqm` |
| `broker` | `CriterionLevel` / `None` | `None` is "don't care". The wanted value is fixed: no broker (#269) |
| `parking` | `CriterionLevel` / `None` | The wanted value is fixed: has parking (#269) |
| `balcony` | `CriterionLevel` / `None` | The wanted value is fixed: has a balcony (#269) |
| `entry_date` | `DateRangeCriterion` / `None` | Compared with `Listing.entry_date`; `"immediate"` compares as the date of the evaluation (#270): the UTC calendar date of the evaluation's moment (R2). With `immediate` (#458): met when the post's date is on or before that date plus 3 calendar months, no lower bound |

**`CriterionLevel`:** `"preference"` / `"critical"`; a category that is turned on starts at `"preference"` (§8).
**`RangeCriterion[T]`:** `min: T / None`, `max: T / None` (at least one set; `min` ≤ `max` when both), `level:
CriterionLevel`. **`DateRangeCriterion`:** `earliest: date / None`, `latest: date / None`, `immediate: bool` (#458,
#468), `level: CriterionLevel`. With `immediate` `False`, at least one end is set (#270) and `earliest` ≤ `latest` when
both; with `immediate` `True` (the quick chip "מיידי"), both ends are `None`: entry no later than 3 calendar months from
the date of the evaluation, no lower bound, rolling. The 3 is a constant in `policy/`, not a field. A day the target month
lacks becomes its last (30.11 → 28.2).

**Rules with no field of their own.**
- **Which option evaluates a post:** the one its `apartment_kind` names (`"room"` or `"whole_apartment"`); a sublet through
  the same option's values, when the profile's `include_sublets` is on (#246, #274, #317). A post whose `apartment_kind`
  is `"unclear"` or `"not_written"` is evaluated against every enabled option and shown at the bottom, with its kind
  marked (#273); a sublet of unclear kind only with the profile's switch on (#317).
- **The area's colour, per user** (#250, #275): not orange when every one of the post's areas is in the option's `areas`;
  with `areas` `[]` a several-area post stays orange. Computed at display, never stored.
- **The post a user sees** is the `Listing` with the admin's corrections in force applied (#256). The evaluation, the
  restore's derived state (#281) and the Gate D key (#287) all read it.

## `ViewedPost`

Which posts a user has viewed (#62, #253). Key: (`user_id`, `listing_id`).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `user_id` | `str` | |
| `listing_id` | `str` | The post the card shows (#276) |
| `viewed_at` | `datetime` UTC | Written when the user opens the card; scrolling past writes nothing (#253). A reopen keeps the first time (#276) |

**Rules.** A card is viewed, for a user, when any post the card stands for (its canonical, the canonical's dedup A
duplicates, and the posts the Gate D key ties to it, #231) has a record for that user, so a further publication grouped
into the card leaves it viewed (#253). "Mark as not viewed" deletes that user's records for every post of the card. A
record is deleted with its post (#62). Kept for a disabled user (#265).

## `HiddenPost` (#464–#466, approved 2026-10-19, #468)

Which posts a user has hidden. Key: (`user_id`, `listing_id`). Table `hidden_posts`, the same shape as `viewed_posts`,
with its own layout row `userdata.hidden` (version 1), created when absent, as Gate F's `userdata.telegram`.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `user_id` | `str` | A signed-in user; a guest has none |
| `listing_id` | `str` | The post the card shows (as #276 for viewed) |
| `hidden_at` | `datetime` UTC | Written when the user presses "הסתר"; pressing again keeps the first time |

**Rules.** A card is hidden, for a user, when any post the card stands for has a record (as `ViewedPost`, #253), so a later
publication grouped into it stays hidden; "בטל הסתרה" deletes that user's records for every post of the card. Hiding applies
only while the bar shows the saved preferences, decided by the server (#465; `PHASE_4.md` appendix A, point 10). Never
written on the post (invariant 12). Deleted with its post, by Phase 5's retention job (with `ViewedPost` and
`SentAlert`). Kept for a disabled user.

## `ClassificationReport`

A user's "wrong classification" report (#173, #254). Keyed by `report_id`. Never deleted, also after its post is (#255).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `report_id` | `str` | Random and opaque |
| `listing_id` | `str` | The post reported: the post the card shows |
| `reported_by` | `str` | The reporter's `user_id` |
| `reported_at` | `datetime` UTC | |
| `fields` | `list[ReportableField]` | One or more, no repeats (#254, #277) |
| `note` | `str` / `None` | The optional free note, at most 500 characters (#277) |
| `status` | `"open"` / `"restored"` / `"left_out"` | `"open"` when made. `"restored"` when the admin restores the post: every open or left-out report of the post (#278, #286). `"left_out"` when the admin leaves the post out; not final, the admin can restore later (#286) |
| `resolved_by` | `str` / `None` | The admin's `user_id`. Set together with `resolved_at`, exactly when `status` is not `"open"` |
| `resolved_at` | `datetime` UTC / `None` | The latest change of `status` |

**`ReportableField`** (#277): `"post_nature"`, `"apartment_kind"`, `"price"`, `"entry_date"`, `"rooms"`, `"floor"`,
`"building_floors"`, `"size_sqm"`, `"room_size_sqm"`, `"broker"`, `"balcony"`, `"parking"`, `"elevator"`,
`"air_conditioning"`, `"furnished"`, `"arnona"`, `"house_committee"`, `"gender"`, `"areas"`, `"streets"`, `"other_city"`,
`"phone_names"` — Gate B's names. The labels a user sees are the UI task's (#277).

**Rules.** One report per reporter (#278), read here as at most one `"open"` report per reporter and post; the same user can
report again after a restore (R4). While any report of the post is `"open"` the post is rejected with
`"misclassified"`, unless it is flagged "lied", which shows (#279). The admin's view groups the reports by field (#173).

## `FieldCorrection`

The admin's hand correction of one field of one post (#173, #256). Keyed by `correction_id`. Never deleted (#255).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `correction_id` | `str` | Random and opaque |
| `listing_id` | `str` | The post corrected |
| `field` | `ReportableField` | The correctable fields are the reportable list (#284) |
| `model_value` | the field's Gate B type | The `Listing`'s value of that field when the correction was made, as stored (a `Marked` field keeps its state and value): the model's answer, kept beside the correction (#255, #256) |
| `corrected_value` | the field's Gate B type | Validated by the same rules as the field in Gate B (#284) |
| `corrected_by` | `str` | The admin's `user_id` (#256) |
| `corrected_at` | `datetime` UTC | |
| `report_id` | `str` / `None` | The report it answers, if any |
| `removed_by` | `str` / `None` | Set by the admin, together with `removed_at`: both or neither (#256) |
| `removed_at` | `datetime` UTC / `None` | A removed correction no longer applies; the record stays (#284) |

**Rules.** At most one correction in force (`removed_at` `None`) per `listing_id` and `field`. While in force it replaces
the model's value of that field wherever the post is read for a user (the card, the filters, the order, in Phase 4 the
alerts), in the restore's derived state (#281) and in the Gate D key (#287); also after a reclassify replaces the `Listing`
(#256). The `Listing` is never edited. The card shows a "corrected by hand" mark on the field (#256).

## Round 1's open points: answered

All 31 points of 2026-10-10's first draft are answered by Ron (`DECISIONS.md` #262–#287) and written into the records
above: 1–5 #262; 6 #263; 7 #264; 8 #265; 9 #266; 10 #267; 11 #268; 12 #269; 13 #270; 14 #271; 15 #272; 16 #273; 17 #274;
18 #275; 19 #276; 20 #277; 21 #278; 22 #279; 23 #280; 24 #281; 25 #282; 26 #283; 27, 28 #284; 29 #285; 30 #286; 31 #287.

## Points R1–R9: approved (#288)

The details the answers asked the assistant to propose, approved as proposed and written into the records above:
R1 the delay (30 seconds from the 5th consecutive failure, per username); R2 "immediate" as the UTC date; R3 a
user's own password change ends their other sessions; R4 one open report per reporter and post; R5 30 days from
sign-in, not extended; R6 `ended_at` with no stored reason; R7 disabling a user and ending their sessions are two
calls in a fixed order, the disable first, then the sessions ended (amended 2026-10-11, #291: a session of a disabled
user is already invalid, so a failure between the two leaves the user locked out); R8 the admin cannot be disabled;
R9 sessions are not deleted in Phase 3.

## Every name and type (approved 2026-10-10, #288; `include_sublets` moved to `Profile` on 2026-10-12, #317; `immediate` and `HiddenPost` added 2026-10-19, #468)

Every record, field and type above, in one table. The rules are in each record's table.

| Record | Field | Type |
|---|---|---|
| `User` | `schema_version` | `int` |
| | `user_id` | `str` |
| | `username` | `str` |
| | `password_hash` | `str` |
| | `is_admin` | `bool` |
| | `created_at` | `datetime` UTC |
| | `signup_key_id` | `str` / `None` |
| | `must_change_password` | `bool` |
| | `password_changed_at` | `datetime` UTC |
| | `disabled_at` | `datetime` UTC / `None` |
| | `failed_sign_ins` | `int` |
| | `last_failed_sign_in_at` | `datetime` UTC / `None` |
| | `telegram_chat_id` | `int` / `None` (Gate F) |
| | `telegram_linked_at` | `datetime` UTC / `None` (Gate F) |
| `SignupKey` | `schema_version` | `int` |
| | `key_id` | `str` |
| | `key_hash` | `str` |
| | `label` | `str` |
| | `created_at` | `datetime` UTC |
| | `used_by` | `str` / `None` |
| | `used_at` | `datetime` UTC / `None` |
| | `cancelled_at` | `datetime` UTC / `None` |
| `Session` | `schema_version` | `int` |
| | `token_hash` | `str` |
| | `user_id` | `str` |
| | `created_at` | `datetime` UTC |
| | `expires_at` | `datetime` UTC |
| | `ended_at` | `datetime` UTC / `None` |
| `Profile` | `schema_version` | `int` |
| | `user_id` | `str` |
| | `room` | `SearchOption` |
| | `whole_apartment` | `SearchOption` |
| | `include_sublets` | `bool` (#317, moved from `SearchOption`) |
| | `updated_at` | `datetime` UTC |
| `SearchOption` (inside `Profile`) | `enabled` | `bool` |
| | `areas` | `list[int]` |
| | `price_min` | `int` / `None` |
| | `price_max` | `int` / `None` |
| | `hide_women_only` | `bool` |
| | `rooms` | `RangeCriterion[float]` / `None` |
| | `floor` | `RangeCriterion[int]` / `None` |
| | `size_sqm` | `RangeCriterion[float]` / `None` |
| | `broker` | `CriterionLevel` / `None` |
| | `parking` | `CriterionLevel` / `None` |
| | `balcony` | `CriterionLevel` / `None` |
| | `entry_date` | `DateRangeCriterion` / `None` |
| `RangeCriterion[T]` | `min` | `T` / `None` |
| | `max` | `T` / `None` |
| | `level` | `CriterionLevel` |
| `DateRangeCriterion` | `earliest` | `date` / `None` |
| | `latest` | `date` / `None` |
| | `immediate` | `bool` (#468) |
| | `level` | `CriterionLevel` |
| `CriterionLevel` | (a value) | `"preference"` / `"critical"` |
| `ViewedPost` | `schema_version` | `int` |
| | `user_id` | `str` |
| | `listing_id` | `str` |
| | `viewed_at` | `datetime` UTC |
| `HiddenPost` (#468) | `schema_version` | `int` |
| | `user_id` | `str` |
| | `listing_id` | `str` |
| | `hidden_at` | `datetime` UTC |
| `ClassificationReport` | `schema_version` | `int` |
| | `report_id` | `str` |
| | `listing_id` | `str` |
| | `reported_by` | `str` |
| | `reported_at` | `datetime` UTC |
| | `fields` | `list[ReportableField]` |
| | `note` | `str` / `None` |
| | `status` | `"open"` / `"restored"` / `"left_out"` |
| | `resolved_by` | `str` / `None` |
| | `resolved_at` | `datetime` UTC / `None` |
| `ReportableField` | (a value) | the 22 Gate B field names listed under `ClassificationReport` |
| `FieldCorrection` | `schema_version` | `int` |
| | `correction_id` | `str` |
| | `listing_id` | `str` |
| | `field` | `ReportableField` |
| | `model_value` | the field's Gate B type |
| | `corrected_value` | the field's Gate B type |
| | `corrected_by` | `str` |
| | `corrected_at` | `datetime` UTC |
| | `report_id` | `str` / `None` |
| | `removed_by` | `str` / `None` |
| | `removed_at` | `datetime` UTC / `None` |
| `PostLifecycle` (Gate E, amended 2026-10-10) | `rejection_reason` | adds `"misclassified"` |
| | `flagged_by` | `str` / `None` (a `user_id`) |
| | `schema_version` | `int`, value 3 |

---

# GATE F — Telegram: the link and the sent alerts

**Approved:** 2026-10-18 (`DECISIONS.md` #453; the content, `PHASE_4.md` points 4 and 5, #452)
**Schema version:** 1 on `SentAlert` and `TelegramLinkCode`; `User` is at version 2 (its two fields below)

The same rules as Gate C's records: per user, never on the post (invariant 12); datetimes tz-aware UTC; stored by
`UserDataStore` (`userdata/`), in its own tables with their own layout row (`userdata.telegram`, version 1); a secret
stored as its SHA-256 only. *Replaces the Phase 0 stubs (`ListingStub`, `DecisionStub`), kept for `notify/` until
this phase and removed with it.*

## On `User` (version 2)

| Field | Type | Rule |
|---|---|---|
| `telegram_chat_id` | `int` / `None` | The linked Telegram chat; `None` when not linked. One chat per user and one user per chat. Sent only to `api.telegram.org` (invariant 15 as amended, #452 point 8) |
| `telegram_linked_at` | `datetime` UTC / `None` | When the chat was linked; set together with `telegram_chat_id`. **A user is alerted only on posts first stored after it** (#452 point 10). Linking the same chat again keeps it |

A stored version-1 `User` reads as version 2 with both `None` (read-time only, as `Profile`, #317).

## `TelegramLinkCode`

The one-time code the site shows on the preferences page, in a deep link `https://t.me/tlv_apartment_hunter_bot?start=<code>`
(32 characters of `A-Za-z0-9_-`, 192 random bits). Keyed by `code_hash`. Never deleted.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `code_hash` | `str` | SHA-256 (hex) of the code. The code is shown once and never stored |
| `user_id` | `str` | The user the code links |
| `created_at` | `datetime` UTC | The code is usable for 15 minutes from it |
| `used_at` | `datetime` UTC / `None` | Set when the bot links a chat with it; single use. Not before `created_at` |

## `SentAlert`

One per user and post: "nothing alerted twice" means "no record yet". Keyed by (`user_id`, `listing_id`). A card whose
posts include one with a record does not alert again. Deleted with its post (as `ViewedPost`, #62), by Phase 5's
retention job.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `user_id` | `str` | The alerted user |
| `listing_id` | `str` | The post alerted: the card's shown post |
| `sent_at` | `datetime` UTC | When Telegram accepted the alert |

**Not stored:** the alert's tier or colours (an `Evaluation` is never stored), the message's id, the chat's history.

---

# GATE G — collection runs and the schedule

**Approved:** 2026-10-19 (`DECISIONS.md` #472; the content, `PHASE_5.md` point 5, approved with every point as
recommended, #471). **Schema version:** 1 on both.

Stored by `SqliteRunStore` (`state/runs.py`) in the same SQLite file, in their own tables (`run_records`,
`schedule_settings`) with their own layout row (`store.runs`, version 1, created when absent, as `userdata.telegram`):
no migration command, and an older image still opens the file. Datetimes tz-aware UTC. Neither record moves the store
generation counter. Nothing per user and nothing about a post (invariant 12).

## `RunRecord`

One per collection run, keyed by `run_id`; listed in the order the runs started. Written by `run_once` when the run
starts and when it ends; its cost by `settle_costs` later (#450). Never deleted.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `run_id` | `str` | The run's `run_id` in its log lines; not empty |
| `trigger` | `"scheduled"` / `"manual"` | The scheduler's runs are `scheduled`; "run now" and a run by hand `manual` |
| `started_at` | `datetime` UTC | When the run started |
| `finished_at` | `datetime` UTC / `None` | `None` exactly while `running`; not before `started_at` |
| `status` | `"running"` / `"succeeded"` / `"failed"` | A record left `running` is closed `failed` when the next run starts ("abandoned") |
| `failure_kind` | `str` / `None` | Set exactly when `failed`: the error's kind and message (at most 300 characters; no post content) |
| `rows_fetched` | `int` / `None` | The rows the Apify dataset returned (what is billed); `None` until known; not negative |
| `rows_skipped` | `int` / `None` | The rows that failed to map (#71 D); `None` until known; not negative |
| `window_since` | `datetime` UTC / `None` | The run's `since`; `None` when the run failed before it was used |
| `window_capped` | `bool` | Always `false`: collection is never capped after a pause (#473, point 12 B) |
| `apify_run_id` | `str` / `None` | The Apify run's id; `None` when no Apify run started |
| `charged_events` | map `str` → `int` / `None` | The run's `chargedEventCounts`: the end-of-run (preliminary) map, then the settled one |
| `cost_usd` | `float` / `None` | Σ `charged_events` × each event's `eventPriceUsd` (#450), set by `settle_costs` 15 minutes or more after the run; not negative; never on a running run |
| `cost_settled_at` | `datetime` UTC / `None` | When `cost_usd` was set; set together with it |

## `ScheduleSettings`

One row. Written by the admin's schedule page (the settings, "run now"), the bot (`last_digest_at` only) and, once, the
scheduler (the first row, from its `.env`). Read by the scheduler at every pass (#61).

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1 |
| `interval_minutes` | `int` | 5 to 1440. The next scheduled run starts this long after the start of the last run that was scheduled, or manual and succeeded (#61) |
| `quiet_from` | `str` `HH:MM` | Israel local time (converted by the schedule only, invariant 9) |
| `quiet_until` | `str` `HH:MM` | Israel local time; equal to `quiet_from`: no quiet hours; across midnight when earlier |
| `run_now_requested_at` | `datetime` UTC / `None` | The admin's last "run now"; started by the scheduler within 15 minutes, once |
| `last_digest_at` | `datetime` UTC / `None` | When the bot last sent the daily digest |
| `updated_by` | `str` / `None` | The admin's `user_id` who last changed the settings; `None` for the scheduler's first row |
| `updated_at` | `datetime` UTC | When the settings were last changed |
