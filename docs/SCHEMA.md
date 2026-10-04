# Schema

**The only source of truth for fields, types, and filter rules.**

Nothing here is written without Ron's explicit approval. Nothing outside this file redefines it —
code, prompts, and other documents reference it, never restate it.

**Last updated:** 2026-10-04 (#80) — **Gate E download rule, wording only:** a network error waits on a fixed
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
| E | Post lifecycle record (state, rejection reason, flag, last publication, images) and `GroupWatermark` | ✅ Approved 2026-10-04 |
| B | `Listing` | ⬜ Not opened — phase 2 |
| D | Dedup stage B key | ⬜ Not opened — phase 2 |
| C | Filter rules, and the user, key and profile records | ⬜ Not opened — phase 3 |

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

This is **not** true of `Listing`, where every new field costs a Gemini call per post across all
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
| `text` | `str` | `text`, falling back to `sharedPost` | What is sent to Gemini **verbatim**. |
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
| `phones` | `list[str] \| None` | Phase 0 | Dedup layer 3, a one-directional signal. ~50% coverage. **Stored normalized**: digits only, `+972` converted to a leading `0`, so `050-9184537` and `+972509184537` both become `0509184537`. One stored format is what makes an equality lookup in the store possible; nothing is lost, since the card always shows the full original text and `raw` keeps the rest. An identical number within one post is stored once, in order of first appearance (`DECISIONS.md` #57). `find_by_phone` normalizes its input before comparing. `None` means not extracted; `[]` means extracted and none found. |
| `no_text` | `bool \| None` | Phase 0 | Stored, and rejected with the reason "no text" (`BASELINE.md` §5). **Not sent to Gemini** — we do not analyse images. Seen only in the admin's rejected list. True when the text is absent, whitespace-only, **or normalizes to nothing** (an emoji-only post). A post that normalizes to nothing must never raise: a failed run does not advance the watermark, so one throwaway post would block the window permanently. `text_source` still records where the text came from — `"text"` with `no_text=True` means it arrived and was unusable. |
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

**Approved:** 2026-10-04 · **Reasons:** `DECISIONS.md` #63, amended by #66, #67, #70, #72, #76
and #77 ·
**Lifecycle:** `BASELINE.md` §5

## Post lifecycle record (`PostLifecycle`)

A **separate record per post, keyed by `listing_id`. Not added to `RawPost`**: Gate A stays a pure
function of `raw`, and these fields change after fetch.

**Amended 2026-10-04** (`DECISIONS.md` #66), approved by Ron: the `flagged_by` type, the
`PostImage` types, and the consistency rules on `rejection_reason`, the flag and `PostImage`. Then
an explicit `listing_id` row, the key the record already had. No other field was added or removed;
`schema_version` stays 1.

| Field | Type | Rule |
|---|---|---|
| `schema_version` | `int` | Starts at 1. On every record (`PHASE_1.md` §1.0) |
| `listing_id` | `str` | The post this record belongs to, and the record's key |
| `state` | `"pending"` / `"active"` / `"rejected"` / `"archived"` | On store: `"pending"`, or `"rejected"` if a pre-model reject applies. In phase 2 the model moves it to `"active"` or `"rejected"`. A repost record has no card of its own; that is `is_canonical` / `duplicate_of` from Gate A, not a state |
| `rejection_reason` | `"no_text"` / `"no_images"` / `"other_city"` / `"seeking"` / `"for_sale"` / `"not_listing"` / `"flagged"` / `None` | One reason, the first that applies, in that order. `None` when `state` is `"pending"` or `"active"`; required when `"rejected"`; optional when `"archived"` (an archived post keeps its reason) |
| `flagged_by` | `str` / `None` | A user id. `None` until phase 3. Gate C may refine the type. Set together with `flagged_at`: both or neither |
| `flagged_at` | `datetime` UTC / `None` | Set together with `flagged_by`: both or neither. `rejection_reason` `"flagged"` requires both |
| `flag_note` | `str` / `None` | Optional short note from the flagger |
| `last_published_at` | `datetime` UTC | The latest `posted_at` of the post and all its duplicates (any dedup layer: A now, B in phase 2). A phone-only match is not a duplicate. Never moves backwards |
| `images` | `list[PostImage]` | One entry per photo attempted: a failed download is recorded too. See below |

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
- **Restore:** restoring a flagged post clears `flagged_by`, `flagged_at`, `flag_note` and
  `rejection_reason`; `state` returns to `"active"`.
- **Flagged posts:** archived at 25 days (images deleted) and never deleted. The full record,
  including `raw`, is kept as the prompt regression set. A restored post follows normal retention.
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

# Stub contracts (Phase 0 only)

**Approved:** 2026-09-14

`Listing`, `Decision` and `Notification` have no approval gate yet. Invariant 1
applies to stubs too, so their Phase 0 shapes are approved explicitly and narrowly.

| Stub | Fields | Notes |
|---|---|---|
| `ListingStub` | `listing_id` | Not persisted in Phase 0 |
| `DecisionStub` | `user_id`, `listing_id`, `notify` | Not persisted in Phase 0 |

`Notification` and `GroupWatermark` are **not** created in Phase 0. `GroupWatermark` was approved at
Gate E on 2026-10-04 (above); its storage is built in task 1.10, and the watermark logic (when it
advances) in task 1.13. The sent-alert record arrives with alerts in phase 4; its field set is
approved before it is written.

**The class and module names must contain `Stub`** (`contracts/listing_stub.py`, `ListingStub`).
A class named `Listing` sitting in the codebase looks like an approved starting point, which is
exactly the confusion that made `schema.py` worth renaming. Gate B replaces these; it does not
extend them.
