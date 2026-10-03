# Schema

**The only source of truth for fields, types, and filter rules.**

Nothing here is written without Ron's explicit approval. Nothing outside this file redefines it —
code, prompts, and other documents reference it, never restate it.

**Last updated:** 2026-10-03 — wording aligned to `BASELINE.md`. **No field, type or rule was
changed.** Gate E was added to the table and Gate C widened, per `DECISIONS.md` #59.

| Gate | Covers | Status |
|---|---|---|
| A | `RawPost` | ✅ Approved 2026-09-14 |
| E | What the lifecycle adds to a stored post: state, rejection reason, flagger, last publication, repost log, image paths | ⬜ Not opened — phase 1 |
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
| `posted_at` | `datetime` (UTC) | `creation_time` — RFC 2822, `parsedate_to_datetime` | **The watermark is the max of this**, never run time. |
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
| `post_type` | `str` | `post_type` | Observed: `regular`, `sale_post`. Documented but not yet observed: `shared`. Lets us find the `shared` cases when they first arrive. |

### Media

| Field | Type | Source | Rationale |
|---|---|---|---|
| `media[]` | `list[Media]` | `media[]` | `{type, uri, width, height, media_id, page_url}`. `width` and `height` are `int \| None`: `Video` items **omit the keys entirely** — a missing key maps to `None`. |

`uri` is a signed `scontent.*.fbcdn.net` link that expires within days, which is why images are
downloaded at fetch time (`BASELINE.md` §3). **`page_url` does not expire** — it is the fallback
when a download failed, and a reason `media[]` is stored even though the URLs rot. Its shape depends on the item type: `facebook.com/photo/?fbid=…` for photos, a
`/videos/` page for videos. Do not assume the photo form.

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
| `phones` | `list[str] \| None` | Phase 0 | Dedup layer 3, a one-directional signal. ~50% coverage. **Stored normalized**: digits only, `+972` converted to a leading `0`, so `050-9184537` and `+972509184537` both become `0509184537`. One stored format is what makes an equality lookup in the store possible; nothing is lost, since the card always shows the full original text and `raw` keeps the rest. `find_by_phone` normalizes its input before comparing. `None` means not extracted; `[]` means extracted and none found. |
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

# Stub contracts (Phase 0 only)

**Approved:** 2026-09-14

`Listing`, `Decision`, `Notification` and `GroupWatermark` have no approval gate yet. Invariant 1
applies to stubs too, so their Phase 0 shapes are approved explicitly and narrowly.

| Stub | Fields | Notes |
|---|---|---|
| `ListingStub` | `listing_id` | Not persisted in Phase 0 |
| `DecisionStub` | `user_id`, `listing_id`, `notify` | Not persisted in Phase 0 |

`Notification` and `GroupWatermark` are **not** created in Phase 0. `GroupWatermark` arrives with
the watermark in phase 1 and the sent-alert record with alerts in phase 4; each field set is
approved before it is written.

**The class and module names must contain `Stub`** (`contracts/listing_stub.py`, `ListingStub`).
A class named `Listing` sitting in the codebase looks like an approved starting point, which is
exactly the confusion that made `schema.py` worth renaming. Gate B replaces these; it does not
extend them.
