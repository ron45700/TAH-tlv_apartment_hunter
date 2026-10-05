# Phase 2 — Classification (semi-macro)

**Status:** approved by Ron, 2026-10-05 (`DECISIONS.md` #126–#175). The spike (2.1) ran; the setting
is effort `none`, temperature 0 (#157). **The model decides the area** (#167): the street table and
its machinery left the phase (#168; the old 2.3 is in the appendix). Tasks 2.2 and 2.3 (reduced)
are built and accepted (#176). **Tasks 2.4 and 2.5 are built** on their approved plans
(#178–#183) and wait for review; no model call was made. The first paid run comes after the
build and a passing regression set (#164). No code before a task's plan is approved; no paid call
before its own go.
**Rewritten:** 2026-10-05, from the draft of the same day, after Ron's answers. Not yet in git.
**Owner:** Ron
**Parent:** `BASELINE.md` §12 · **Schema:** `SCHEMA.md`, Gate B (approved) · **Research:**
`RESEARCH.md` §15 (OpenAI), §14 (streets), §13 (Gemini, the alternative)

**Phase goal:** every stored post that is pending and canonical gets a `Listing` and leaves
`"pending"`: `"active"`, or `"rejected"` with a model-decided reason. Ron can check the results
in a local report. No dashboard, no Telegram.

**Phase DoD:**
1. Every pending canonical in the store, and every new one from a collection run, gets a
   `Listing` and an `"active"` or `"rejected"` state through the classification job, with no
   manual step but starting it.
2. The regression set passes the bar (2.6).
3. A model failure or outage leaves collection and every watermark untouched; the post stays
   `"pending"` and is retried, up to three failed runs (2.5).
4. **A real working day is measured:** the number of calls, the tokens and the cost of a day's
   classification, from the usage metadata and then the OpenAI bill. Every paid run stayed under
   its cap.
5. Ron reviewed the report of the first paid run (2.7, 2.8) and signed it off.
6. The items of §3 are resolved or explicitly re-planned.
7. Gate D settled, or deferred with a measured reason (2.10).

No bulk reclassify is part of the DoD (#144).

**Figures used below** (store read 2026-10-05, read-only): 266 posts; **195 pending canonicals**;
post text averages 523 characters (median 442, at most 2,842). About 150–250 classifiable posts a
day, so **4,500–7,500 a month**: from run A's 212 rows in 24 hours with two groups cut off, times
the 73% that are pending canonicals; one day of data (`ASSUMPTIONS.md` P7).

**Every cost figure in this file is an estimate** until the spike and a real bill measure it
(`ASSUMPTIONS.md` O2, O10).

---

## 2.0 Mandatory anchors

| Anchor | Source |
|---|---|
| Gate B: `Listing`, its fields and rules | `SCHEMA.md`, approved 2026-10-05 (#125) |
| The provider is OpenAI, for now; `gpt-6-luna` first; another model only through Ron | #126, #127 |
| The model extracts; code derives the rejection and the areas | #87, #92, #110 |
| The response schema is derived from pydantic at runtime | #22, #137 |
| The model receives the original text verbatim and classifies only | Invariants 8, 11 |
| The model decides the area, from the 71 in its instructions | #167 |
| Only `"pending"` canonicals are classified | #75 B |
| `OPENAI_API_KEY` read only in the entry point, never logged | #128 |
| Effort `none`, temperature 0; `low` the fallback | #157 |
| Classification never touches the source text | Invariant 14, #163 |

---

## Order of work

```
2.1 spike  →  2.2 Listing storage  →  2.3 the 71 areas  →  2.4 classifier
           →  2.5 classify_pending  →  2.6 regression set  →  2.7 review report
           →  2.8 first paid run  →  2.9 reclassify  →  2.10 Gate D
```

2.3 and the labelling page of 2.6 need no model: they can start beside 2.1, so that Ron labels
while the classifier is built. The response model's names are approved (#151).

---

## 2.1 Spike — the OpenAI contract (paid, small) — go given (#156)

Approved in shape (#130): `gpt-6-luna` only, about 20 hard posts, a $2 cap enforced by the script.
**Go given by Ron, 2026-10-05 (#156). Ran the same day:** 123 calls, $0.0273 by the usage
metadata, the schema accepted unchanged. Report: `docs/SPIKE_2_1_2026-10-05.md`; the review page
and the 20 `listing_id`s for the regression set are in `data/spike_openai_2026-10-05/`.

**What it has to answer:**
1. Does the schema pydantic derives for the response model pass strict structured outputs? (O5,
   O11)
2. Tokens per post: input, cached input, cache writes, output, reasoning. (O3, O7, O10)
3. The real cost per post, from the usage metadata and then the bill. (O2)
4. The behaviour at the settings the model allows: effort `none` with temperature omitted and at
   0; effort `low` (no temperature, O4). Agreement between two passes, and any looping or empty
   answer.
5. What failures look like: a refusal, an `incomplete` response, a rejected schema, a bad key.
6. What the response's own `model` field says (O1).

**Before it:** Ron reads the organization's usage tier and limits (O8), and, recommended, sets a
hard spend limit on the project the key belongs to (O9: a second line, not the cap).

**The posts:** about 20 from the store, read-only: seeking against offer, sublet, a shared post,
English, several prices, a `sale_post` whose native price is not in the text, Old North and
Jaffa, feminine-only wording, another city named, a month with no day. Plus #45's case from
`data/raw/test_posts.json`.

**The calls:**

| Setting | Posts | Passes | Calls |
|---|---|---|---|
| effort `none`, temperature omitted | 20 | 2 | 40 |
| effort `none`, temperature 0 | 20 | 2 | 40 |
| effort `low` | 20 | 2 | 40 |
| Failure probes: `max_output_tokens` 16 (an `incomplete`), an unsupported schema keyword, a wrong key | — | — | 3 |

Every call: `store: false` (O6); the instructions in a developer message with an explicit cache
breakpoint at its end, the post after it (O7, so the post is never written to the cache);
`max_output_tokens` 4,000. The response model is the proposed `ListingExtraction` (`SCHEMA.md`),
used here as a throwaway: the spike's result can still change it.

**Cost calculation** (prices O2; token counts assumed, O10: instructions and schema 2,500–3,500,
post 200–700, output 300–700, reasoning at `low` 200–1,000):

| | Per call, low | Per call, high | Calls | Total, high |
|---|---|---|---|---|
| effort `none`, prefix read from the cache | $0.0002 | $0.0005 | 80 | $0.04 |
| effort `low`, prefix read from the cache | $0.0003 | $0.0010 | 40 | $0.04 |
| Cache writes (one per setting and pass, 3,500 tokens) | | $0.0004 | 6 | $0.003 |
| Failure probes | | | 3 | under $0.001 |
| **Estimate** | | | | **about $0.10** |
| **Worst case**, every call at 4,200 input and the full 4,000 output tokens, no cache | | $0.0024 | 123 | **$0.30** |

**The cap: $2.** Before each call the script adds the worst case of that call (its input tokens
plus `max_output_tokens`, at list price) to what the usage metadata says was spent so far, and
stops if the sum would pass $2. The worst case of the whole spike is $0.30, so the cap is a guard
against a bug, not against the plan.

**Output:** the raw responses in `data/raw/` with a dated filename, a report, the O-items updated
in `ASSUMPTIONS.md`. The script is a throwaway under `scratch/`, run with `uv run --env-file .env`;
it reads `OPENAI_API_KEY` itself and never logs it.

**If `gpt-6-luna` misses the regression bar later** (2.6): the next model and its price go back to
Ron (#127). No other model is picked here.

---

## 2.2 `Listing` storage — approved (#131, #174); built 2026-10-05, accepted (#176)

`Listing` in `contracts/`, from `SCHEMA.md`; stored in the same SQLite file, one record per
`listing_id`; `local_json` too, under the same contract tests. One Repository method writes the
`Listing` and the lifecycle record in one transaction; plus `get_listing` and a query for pending
canonicals. A seam contract change, approved.

**Built** with Ron's answers (#174): layout option C (a `store.listings` layout row, the table
created when absent; layout 1 untouched, no migration); #89 in dedup; `ListingStub` kept for
`policy/` and `notify/`. **Deviations from the plan below:**
- Version-1 lifecycle records are read through one classmethod, `PostLifecycle.from_stored_json`,
  used by both stores, not through a `model_validator(mode="before")`: a before-validator makes
  pydantic validate the parsed JSON in strict Python mode, which refuses the stored datetime
  strings. The effect is the one approved: a version-1 document reads as version 2 with 0 and
  `None`, and is written back as version 2 on its next save. A record built in code must now be
  version 2 with both fields (`initial_lifecycle` passes them).
- `test_stub_names_say_stub` no longer asserts that `contracts/listing.py` is absent (#33's rule
  for the stub era); `tests/test_listing.py` pins `Listing`'s approved field list instead.
- `Marked` is written `class Marked[T](BaseModel)` (Python 3.12 type parameters), as ruff asks.
- Checked by hand on a copy of the real store (not the store itself): 266 posts, 266 lifecycle
  records and 6 watermarks byte-identical after opening; one layout row added
  (`store.listings`, 1); every record read as version 2 with 0 and `None`; 195 pending canonicals.

### Plan for task 2.2 — approved (written 2026-10-05)

**Scope:** the `Listing` contract and its storage, and the Gate E amendment (#139, #152). No model
call, no classifier, no job.

**Files touched:**

| File | Change |
|---|---|
| `tlv_hunter/contracts/listing.py` (new) | `Listing`, `Marked[T]`, `PhoneName`, `LISTING_SCHEMA_VERSION = 1`, with `SCHEMA.md` Gate B's rules as validators |
| `tlv_hunter/contracts/post_lifecycle.py` | The two new fields; `POST_LIFECYCLE_SCHEMA_VERSION = 2`; reading a version-1 record |
| `tlv_hunter/store/base.py` | Three `Repository` methods (below) |
| `tlv_hunter/store/local_json.py` | A `listings/` collection and the three methods |
| `tlv_hunter/store/sqlite.py` | A `listings` table and the three methods; the layout change (below) |
| `tlv_hunter/dedup/stage_a.py` | #89: an archived post with no rejection reason that is reposted returns to `"active"` when it has a `Listing` (optional, below) |
| `tests/test_listing.py` (new), `tests/test_post_lifecycle.py`, `tests/test_repository_contract.py`, `tests/test_sqlite_store.py`, `tests/test_dedup_stage_a.py`, `tests/test_premodel_rejects.py` (a literal version 1) | Tests below |
| `CLAUDE.md` | The `store/` row of the seams table lists the new methods |

**The contract changes to `Repository`** (names proposed):
- `save_classification(listing: Listing, lifecycle: PostLifecycle) -> None`: writes both in one
  transaction (#131). The post must be stored (`KeyError` otherwise, as `save_lifecycle`); the two
  `listing_id`s must match (`ValueError`). An existing `Listing` is replaced (reclassify, #144);
  the lifecycle record is a whole-record replace, as `save_lifecycle`. **It never writes
  `raw_posts`** (invariant 14).
- `get_listing(listing_id: str) -> Listing | None`.
- `find_pending_canonicals() -> list[RawPost]`: the posts whose lifecycle `state` is `"pending"`
  and whose `is_canonical` is `True`, ordered by `listing_id` (#75 B). The three-failures rule
  stays in the job (2.5), not in the store.
- Failure counts are written through the existing `save_lifecycle`.

**`local_json`:** one file per `Listing` in `<root>/listings/`. As today, a write spanning two files
is not atomic: `save_classification` writes the `Listing` first, then the lifecycle record; a crash
between them leaves a `Listing` beside a `"pending"` record, which the next run classifies again
(paid once more; tests only, so accepted, as its docstring already says for lifecycle records).

**SQLite:** a table `listings (listing_id TEXT PRIMARY KEY REFERENCES raw_posts (listing_id), doc
TEXT NOT NULL)`, one JSON document per record, as #65. `find_pending_canonicals` reads `state`
and `is_canonical` from the documents with the JSON operators (3.38.0, already the minimum).

**The layout change — conflicts with #65** ("no automatic migration"). The store's layout goes
from 1 to 2, and the real store is at 1, so the new code refuses to open it until something
changes it. Options:
- **A. An explicit migration command** (`tlv_hunter/jobs/migrate_store.py`), run once by hand: it
  checks the file is at layout 1, adds the `listings` table, sets layout 2, in one transaction.
  Ron copies the SQLite file first. #65 holds as written. **Recommended.** *Why:* the one existing
  store changes only when Ron runs it, and the rule that a version mismatch refuses to open stays.
- **B. The constructor upgrades 1 to 2 by itself.** Amends #65.
- **C. A second layout row for the new table** (`store.listings`), created when absent, leaving
  layout 1 untouched. Reads #65's "per module" as "per table group".

**Reading older lifecycle records:** one `model_validator(mode="before")` on `PostLifecycle`: a
document at version 1 is read with `classification_failures = 0`, `last_classification_error =
None` and `schema_version = 2`, in memory; it is written back as version 2 the next time the record
is saved. No bulk rewrite. A version-1 document that already carries either field, or a version
above 2, is refused. Every constructor in the code passes `POST_LIFECYCLE_SCHEMA_VERSION`, so they
become version 2 with the constant.

**The `Listing` validators** (from `SCHEMA.md`; the ones marked *proposed* go beyond its text):
`extra="forbid"`, frozen, strict, like the other contracts; `Marked`: `value` set exactly when
`state` is `"written"`; `price_source` `None` exactly when `price` is not written; a written
`price` a non-empty list; `rooms` a multiple of 0.5; `classified_at` UTC through `require_utc`;
`areas` within 1–71. *Proposed:* written prices greater than 0; `areas` sorted with no repeats;
`phone_names[].phone` in the stored phone format (`canonical_phone`).

**#89 in dedup (optional in this task):** `dedup_a` restores an archived post with no rejection
reason to `"active"` when `get_listing` finds a `Listing`, `"pending"` otherwise. It can wait for
2.5 instead; nothing produces a `Listing` before then.

**`ListingStub`:** `classify/`, `policy/` and `notify/` use it. Recommended: `classify/` moves to
`Listing` in task 2.4; `policy/` and `notify/` keep the stub until phases 3 and 4. `SCHEMA.md`
says Gate B "replaces" the stubs; this would replace them in steps.

**Tests:** in `tests/test_repository_contract.py`, run against both stores: a `Listing` round trip
through a fresh instance; `save_classification` writes both, refuses an unknown post and a
mismatched pair, replaces an earlier `Listing`, and **leaves the stored `RawPost` document
byte-identical** (invariant 14); `find_pending_canonicals` returns exactly the pending canonicals
(duplicates, active, rejected and archived posts left out). In `tests/test_post_lifecycle.py`: a
version-1 document from each store reads with 0 and `None`; the refused cases. In
`tests/test_listing.py`: each validator. In `tests/test_sqlite_store.py`: the migration from a
layout-1 file built in the test (option A), and the refusal to open an unmigrated file. Under the
network guard, no fixture outside `tests/` is needed beyond those already used.

**Order of work:** the `Listing` contract and its tests; `PostLifecycle` version 2 and its tests;
`Repository` and `local_json` with the contract tests; SQLite, the migration and its tests; #89 if
approved; `uv run pytest` and `ruff`; then, on Ron's go, he copies the store and runs the
migration.

**For Ron before code:** the three method names and signatures; the layout option (A, B or C);
the version-1 read; the proposed validators; #89 in this task or in 2.5; the stub sequence;
running the migration on the real store.

---

## 2.3 The 71 areas — reduced (#167, #175); built 2026-10-05, accepted (#176)

Since #167 the model decides the area, so the street table, the alias and corrections files, the
derivation, the downloads, the completeness check, the lookup key, the prefix rule and the
unmatched share leave phase 2 (#168). The earlier 2.3 text and its plan are kept in the appendix.

**Built:**
- `reference/areas.yaml`: the 71 entries from the layer-511 fixture
  (`data/raw/tlv_gis_layer511_rows_2026-10-05.json`), `number` and `name` verbatim, `label` on the
  five entries of #119, and a `source` block.
- `tlv_hunter/areas/reference.py`: `load_areas()`, the only reader of `reference/`; it refuses a
  list that is not numbered 1-71 in order, once each, and any unknown key. `Area.display_name` is
  the label where there is one, else the name. `PHASE_1.md`'s YAML anchor is reworded to allow it.
- `tests/test_reference_areas.py`: 71 entries numbered 1-71; every name equal to the fixture (read
  in place; fails if missing); exactly the five labels; the source block; the refusals.

Task 2.4 gives the model the 71 numbers and display names from this reader.

---

## 2.4 The classifier — approved (#137, #151)

`classify(RawPost) -> Listing`: the prompt from the original text, one call, validation, then
`Listing` completed in code: the native-price fallback and its 500 floor (#114) through the one
price parser; the entry date's year (#115, #123) next to the one datetime parser; the kept phone
names (#105) through the one phone normalization; the provenance (#90). **`areas` comes from the
model** (#167): its instructions carry the 71 numbers with their display names (from
`areas/reference.py`), the rules of #88, #112 and #124 (a stated area decides; a street only
refines inside it; several possible areas are all returned; nothing it can place returns no area)
and #86's rows as examples. Code sorts the returned numbers and removes repeats (the `Listing`
validator requires it) and refuses a number outside 1-71. Known limit (#170): for a post with only
a street, the area rests on what the model knows of Tel Aviv. The rejection is derived outside, by a plain module, from `other_city` and
`post_nature` (#92).

**The response model** (#137): `ListingExtraction`, a separate pydantic model with a drift test.
**Its names are approved (#151):** `entry_date_parts` (`immediate`, `day`, `month`, `year`) and
`phone_name_pairs` (`phone`, `name`).

**The call:** the Responses API; `store: false` (#147); explicit prompt caching with one
breakpoint after the instructions, the post after it and never cached (#150); `max_output_tokens`
set; `reasoning.effort` `none` and temperature 0 (#157), `low` the fallback if the regression set
fails at `none`. `model_name` is the identifier sent; the model value
the response reports is logged too (#149).

**The prompt:** versioned (`prompt_version`), in the package, English with Hebrew examples. It
asks for no summary and sends nothing but the instructions and the post's text. It says the model
never computes a value (#162), and carries #159 (sublet), #160 (one amount for several charges)
and #161 ("דירת N שותפים"). The spike's prompt (`data/raw/openai_spike_2026-10-05/instructions.txt`)
is input, not approved text (#166).

**Checks in code after the answer** (#162): a street or area name the model returns that does not
appear in the post's text is dropped from the `Listing` and counted in the report. The research
prompt in `data/raw/` is input, not a starting point (C5).

### Plan for task 2.4 — approved (#178–#181); built 2026-10-05

**Built 2026-10-05, waiting for review.** No model call was made. The plan below holds, with
these deviations:
- **`ClassificationError(kind, detail, retry_after)`.** The plan put the billed usage on the error;
  it goes on the meter's `CallRecord` instead, for every response, failed or not.
- **`OpenAIClassifier.classify_completed(post)`**, beside `classify`, returns the `Listing` with
  the names #162 and #180 dropped. The job uses it for the dropped-names file. The seam's
  `classify(RawPost) -> Listing` is unchanged.
- **The setting lives with the prompt.** The model, effort, temperature and output limit are in
  `classify/instructions.py`, beside `PROMPT_VERSION`, since the fingerprint covers them (#179);
  the timeout is in `classify/transport.py`.
- **The classifier refuses to start** when the fingerprint of what it would send differs from
  `PROMPT_FINGERPRINT`, beyond the test that pins it.
- **The error kinds:**
  - A `not_found` kind for 404, which the plan stopped on without naming it.
  - The 429 codes follow the error-codes guide as read today (`ASSUMPTIONS.md` O13):
    - `credit_balance_exhausted` and `organization_usage_limit_exceeded` are quota, as is the
      older `insufficient_quota`;
    - `organization_spend_limit_exceeded` is a spend limit, as is the project's.
- **A two-digit year:** code also reads a year below 100 as 20YY. This backs #178's instruction; it
  is not a new rule.
- **`openai` 3.24.0 depends on `httpx2`,** not `httpx`, so the transport tests use
  `httpx2.MockTransport`.

The size, as approved: **9,025 characters** rendered (step 6).

**Scope:** `classify(RawPost) -> Listing`, one call per post; the completion rules; the module that
derives the rejection; their tests. **No job, no store write, no paid call.** The first real call
is the regression set's (2.6), on its own go.

**Before any code:** the `external-contract-verification` skill on the Responses API, reading only.
The spike verified the request, the envelope of a completed answer, `incomplete`, a refused schema
(400) and a wrong key (401). **It never saw a refusal, a 429, a 5xx or a timeout,** so their shapes
come from the documentation and from `openai` 3.24.0's exception classes. The 429 bodies for rate,
`insufficient_quota` and `project_spend_limit_exceeded` need telling apart, and so does
`Retry-After`.

#### 1. The layout, and where the instructions and `prompt_version` live

| File | What |
|---|---|
| `contracts/listing_extraction.py` (new) | `ListingExtraction`, `EntryDateParts`, `PhoneNamePair`, as approved (#137, #151), `areas` included (#167). It reuses `Marked` from `contracts/listing.py`, so the two shapes cannot differ in the state structure. Placed "next to `Listing`" (#137) |
| `classify/base.py` | `Classifier.classify(post: RawPost) -> Listing` (it was `ListingStub`; #174.6). `ClassificationError(kind, detail, call)` for every failure, `call` holding the billed usage when there was one |
| `classify/classifier_stub.py` | Deleted. `ListingStub` stays for `policy/` and `notify/` (#174.6) |
| `classify/instructions.txt` (new) | The template, the text of `docs/INSTRUCTIONS_V1_DRAFT.md` once approved; that file is then deleted |
| `classify/instructions.py` (new) | `render_instructions(areas)`: the template with `<<AREAS>>` replaced by the 71 lines from `load_areas()`. `PROMPT_VERSION` and `PROMPT_FINGERPRINT` (below) |
| `classify/openai_classifier.py` (new) | `OpenAIClassifier(transport, meter, clock)`: builds the request, checks the meter, sends, reads the envelope, validates, completes. The call's constants: model, effort, temperature, output limit, timeout |
| `classify/transport.py` (new) | `ModelTransport`, one method `send(request: dict) -> dict`; `openai_transport(api_key)` built on the SDK. It maps the SDK's exceptions to one `TransportError(kind, status, retry_after)`. The fake used by tests implements the same protocol, like `providers/thedoor.py`'s `Transport` |
| `classify/complete.py` (new) | `complete(extraction, post, provenance) -> Completed`: the `Listing`, plus the names dropped by #162. Pure |
| `classify/cost.py` (new) | O2's list prices as constants; `call_cost(usage)`; `worst_case(request)`; `CostMeter(cap)` with `check(worst)` (raises `CapReached`) and `record(call)` |
| `parsing/prices.py` | `NATIVE_PRICE_FLOOR = 500` and `native_price_fallback(native_price)`, next to the one price parser |
| `parsing/datetimes.py` | `nearest_occurrence(day, month, reference)`, next to the one datetime parser |
| `postmodel/rejects.py` (new) | The rejection derived from the answer (step 4). A plain module, like `premodel/rejects.py` |
| `pyproject.toml`, `uv.lock` | `openai==3.24.0` as a runtime dependency (below) |
| `CLAUDE.md` | The `classify/` contract names `ClassificationError`; `postmodel/rejects.py` among the plain modules |
| `SCHEMA.md` | Nothing: no field and no type changes |

**`prompt_version`:** a readable constant, `"1"`, with a fingerprint beside it: the SHA-256 of
everything sent except the post. That is the rendered instructions, the derived schema, the model,
the effort, the temperature and the output limit. A test recomputes the fingerprint and fails
when it differs, so no change to the prompt, to `reference/areas.yaml`, to the response model or to
the setting can reach a `Listing` under an old version. **For Ron:** this reads "the prompt" as the
whole request apart from the post. `Listing` has no field for the setting, so without this, an
effort change from `none` to `low` (#157) would leave no trace on a `Listing`, and reclassify (#144)
could not select by it.

#### 2. The call

The request, field for field the spike's `none_t0` request except the output limit and the text:

```python
{
    "model": "gpt-6-luna",
    "input": [
        {
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": INSTRUCTIONS,
                    "prompt_cache_breakpoint": {"mode": "explicit"},
                }
            ],
        },
        {"role": "user", "content": [{"type": "input_text", "text": post.text}]},
    ],
    "text": {"format": SCHEMA_FORMAT},
    "store": False,
    "reasoning": {"effort": "none"},
    "temperature": 0,
    "max_output_tokens": 2000,
    "prompt_cache_options": {"mode": "explicit"},
}
```

- **The Responses API** (`client.responses.create`), as the spike called it.
- **The post** goes in alone, verbatim: `post.text`, the stored original (invariant 8, #163).
- **The schema** is derived at runtime from `ListingExtraction` by the SDK helper the spike used,
  `type_to_text_format_param` (#22). It lives in a private module of the SDK (`openai.lib._parsing`),
  so **`openai` is pinned exactly at 3.24.0**. An offline test compares the derived schema with the
  spike's `schema_sent.json`. Only two differences are expected: `areas` added, and the description
  the spike's throwaway `Marked` carried on `value`. Any other difference fails, so an SDK upgrade
  that changes the schema is caught before a call. The alternative, `responses.parse`, is public
  but was never called (O11).
- **Effort `none`, temperature 0** (#157); **`store: false`** (#147); **explicit caching** with one
  breakpoint at the end of the instructions (#150). The schema is part of the cached prefix (O7).
- **Output limit: 2,000 tokens.** The longest answer seen was 496 tokens at `none` (784 at `low`). The
  spike's 4,000 doubles the worst case the cap must reserve for each call.
- **Timeout 60 s** per call (the spike's took 3–5 s). The SDK's own retries are off (`max_retries=0`):
  retries belong to the job (2.5), so that every attempt passes the cap check.
- **The key** is passed by the command to `openai_transport` (2.5) and held by the SDK client only;
  the classifier never sees it. The `openai` and `httpx` loggers are set to WARNING.

**Reading the answer, in order:**

| What comes back | `ClassificationError.kind` | Billed |
|---|---|---|
| The transport raised | `network`, `timeout`, `rate_limit` (with `Retry-After`), `spend_limit`, `quota`, `server`, `auth`, `bad_request` | No |
| `status: "incomplete"` | `incomplete` (with `incomplete_details.reason`) | Yes |
| A `refusal` content item | `refusal`. The refusal's text is not kept: it may quote the post | Yes |
| Any other status than `"completed"` | `invalid` | Yes |
| The text fails `ListingExtraction` | `invalid`, described by field path and error type only, never input values (as `run_once._describe`) | Yes |
| An area outside 1–71, or the `Listing` refuses the completed record | `invalid` | Yes |

Every call that returned a response, failed or not, is recorded through `meter.record(call)`: the
usage, the cost, the model value the response reports (#149), the status and the seconds. That is
how the job (2.5) sees cost and the reported model without changing `classify`'s contract.

#### 3. What code completes after the answer

| Rule | What the code does | Single implementation |
|---|---|---|
| **Native price** (#95, #114) | The answer's `price` is `not_written` → `native_price_fallback(post.native_price)`. At 500 or more, `written [n]`, `price_source` `"native"`. Otherwise `not_written`, `None`. A written **or unclear** text price keeps its state, `price_source` `"text"`: an unclear text price stays unclear even when a native price exists. `native_price` is set only when the provider's string parsed as ILS (`parse_native_price`), so no currency check is added | The floor sits in `parsing/prices.py` beside the one price parser |
| **Entry date** (#96, #115, #123) | The parts `not_written` or `unclear` → the same state. `immediate` → `"immediate"`. A written year → `date(year, month, day)`. No year → `nearest_occurrence(day, month, post.posted_at.date())`. It considers the year before, the same year and the year after, keeps those that exist (29 February), and takes the nearest. `posted_at` is UTC (`require_utc`), so this is the UTC date (#115) | `parsing/datetimes.py` |
| **Phone names** (#105) | A pair is kept when `canonical_phone(pair.phone)` is in `post.phones`; it is stored with the canonical number and the name as written | `textnorm/phones.canonical_phone` |
| **Names not in the text** (#162) | Each entry of `streets` and `stated_area_names` is kept when, with surrounding whitespace removed, it is not empty and occurs in `post.text` exactly. That is Python `in`: case-sensitive, nothing normalized. Invariant 8 allows normalized text only for the hash. The dropped names are returned beside the `Listing` for the job to count. The `areas` the model decided are kept either way (#167) | — |
| **Areas** (#167, #174) | A number outside 1–71 makes the whole answer `invalid` (retried as 2.5 says). Otherwise `sorted(set(areas))` | The `Listing` validator (`AREA_NUMBERS`) checks it again |
| **Provenance** (#90, #149) | `schema_version` `LISTING_SCHEMA_VERSION`; `listing_id` from the post; `model_name` `"gpt-6-luna"`, as sent; `prompt_version`; `classified_at` from the injected clock when the answer arrives, through `require_utc`. The reported model value goes to the call record and the log, not onto `Listing` | `require_utc` |

**Not settled by any decision, so proposed (§4):**
- the publication date is the post's own `posted_at`, not `last_published_at`;
- a tie between two years goes to the later one;
- an impossible date (31.11, or 29.2 of a written non-leap year) makes `entry_date` `"unclear"`
  rather than failing the post three times over a typo;
- an exact repeat of a kept phone-name pair is stored once, and a blank name is dropped;
- a blank `other_city` reads as `None`, since a blank string would otherwise reject a Tel Aviv post
  as `other_city`;
- an English name in a different case ("dizengoff" for "Dizengoff") is dropped by #162's exact
  match.

#### 4. The rejection — `postmodel/rejects.py`

A plain module, the mirror of `premodel/rejects.py`. It is not inside `classify/`, which extracts
only (`CLAUDE.md`), and not in the job's wiring, which holds no rules.
- `model_reason(listing)`: `"other_city"` when `other_city` is set; else `"seeking"`, `"for_sale"`
  or `"not_listing"` from `post_nature`; else `None` (`rental_offer`, `sublet_offer`). That is
  Gate E's order (#92). `no_text` and `no_images` come before it, but a pending post has neither;
  `flagged` comes after and is a user's.
- `classified_lifecycle(existing, listing)`: from a `"pending"` record only (`ValueError`
  otherwise). The state becomes `"active"`, or `"rejected"` with the reason. Every other field is
  unchanged, the two failure fields included (#152).
- `failed_lifecycle(existing, error)` (used by 2.5): `classification_failures` plus 1,
  `last_classification_error` the short reason; the state stays `"pending"`.

A rule change re-derives from the stored `Listing`s without a call (#92); that command is not part
of this task.

#### 5. The instructions

**Approved (#178), in the package:** `tlv_hunter/classify/instructions.txt`, the only copy (the
draft in `docs/` was deleted when it entered the package). `<<AREAS>>` is replaced at runtime by
one line per area, `number: display name`, from `load_areas()`. Ron kept all 11 sentences the
draft marked "proposed" and added two: a two-digit year is 20YY, and a well-known landmark places
the apartment when the post gives no area name and no street.

**Every rule, its decision, and where the text carries it.** The rows marked #178 were proposed in
the draft and approved there. Rules that code applies after the answer are the last rows; they are
not in the text.

| # | Rule | Decision | Where in the text |
|---|---|---|---|
| 1 | The model extracts only; never summarizes or adds text | Invariant 11 | General rule 1 |
| 2 | A value that is not written is never filled in | #106 | General rule 2 |
| 3 | No value derived from another (rooms from size, total from per-roommate) | #106, #162 | General rule 3 |
| 4 | The model never computes ("3.50*3.50" is not 12.25) | #162 | General rule 4 |
| 5 | "דירת N שותפים" is the one exception | #161 | General rule 4; rooms |
| 6 | Text values as written, never folded; prefix letters kept | #104, #111, #167; `CLAUDE.md` domain traps | General rule 5 |
| 7 | "Never return one that is not in the post" (code drops it anyway, #162) | #162 | General rule 5 |
| 8 | State structure: written / not written / unclear; "no" is written | #91 | The state structure |
| 9 | An unclear field keeps no value | #109 | The state structure, "unclear" |
| 10 | Five post natures, no "unclear" | #93 | post_nature |
| 11 | "A roommate for our flat" is an offer | `BACKLOG.md` regression row; the spike's text | post_nature, rental_offer |
| 12 | Facebook's sale format is not a sale | `CLAUDE.md` domain trap (`sale_post`) | post_nature, rental_offer. #178 (the model sees only the text, never `post_type`) |
| 13 | Sublet: says so, or an explicit temporary period | #93 | post_nature, sublet_offer |
| 14 | A sublet offered as an option before a regular lease is a rental offer | #159 | post_nature, sublet_offer |
| 15 | "לא סאבלט" is not a sublet | The spike's text | post_nature, sublet_offer; #178 |
| 16 | Seeking a sublet is seeking; searching together is seeking (#45's case) | #93; `ASSUMPTIONS.md` C2 | post_nature, seeking |
| 17 | for_sale, not_listing | #93 | post_nature. The examples for not_listing: #178 |
| 18 | Apartment kind: room or whole; "suits roommates" and a studio are whole | #94 | apartment_kind |
| 19 | Price: ILS list from the text, usually one; several prices all listed | #95 | price |
| 20 | "In the order written" | — | price; #178 |
| 21 | Per-roommate price for a whole apartment: unclear; another currency: unclear | #95 | price |
| 22 | Not written when the text gives none (the native fallback is code's, row 46) | #95, #114 | price |
| 23 | Entry date as written, never replaced | #96 | entry_date_written |
| 24 | Immediate | #96, #151 | entry_date_parts, first point |
| 25 | Day and month; the year only when written | #115, #151 | entry_date_parts, second point |
| 25a | A two-digit year is 20YY ("1.11.26" is 2026); code holds to it too | #178 | entry_date_parts, second point |
| 26 | Day first: "1.11" is 1 November | — | entry_date_parts, second point; #178 (the Israeli order) |
| 27 | Start / middle / end of a month: 1 / 15 / the last day | #96 | entry_date_parts, third point |
| 28 | "End of February" is the 28th; a bare month is the 1st, written | #123 | entry_date_parts, third point |
| 29 | "Flexible" is unclear | #96 | entry_date_parts, fourth point |
| 30 | Rooms: the total in the apartment, also for a room; halves | #97 | rooms |
| 31 | "דירת N שותפים" gives N; N+1 with a living room | #161 | rooms |
| 32 | Ground floor 0, basement -1 | #98, #118 | floor |
| 33 | Building floors only when written ("3 מתוך 4") | #98, #106 | building_floors |
| 34 | Apartment size; room size only when written; decimals | #99, #118 | size_sqm, room_size_sqm |
| 35 | Broker yes or no | #100 | broker |
| 36 | Shared balcony true; street parking false; "option for parking" unclear; elevator; air conditioning | #100 | balcony, parking, elevator, air_conditioning |
| 37 | Furnished: yes, partial, no; "option to leave furniture" unclear | #102 | furnished |
| 38 | Arnona and house committee: an amount or "included" | #101 | arnona and house_committee |
| 39 | No period, never divided | #101, #116 | arnona and house_committee |
| 40 | "All included" unclear | #101 | arnona and house_committee |
| 41 | One amount for several charges unclear | #160 | arnona and house_committee |
| 42 | Gender: women only, women preferred, no restriction; feminine-only wording is women only; silence is no restriction | #103, #117 | gender |
| 43 | "שותף/ה" is no restriction | `CLAUDE.md` domain trap (Hebrew) | gender; #178 |
| 44 | Streets as written, in order of appearance; "X corner Y" gives both | #104; `SCHEMA.md` `streets` | streets. "Without the house number" is #178 |
| 45 | Area names as written; a landmark is not an area | #111, #167 | stated_area_names. The landmark sentence is #178 |
| — | **Areas** | | |
| 46 | Numbers from the 71 only, returned by the model | #81, #83, #167 | areas, first lines; the generated list |
| 47 | A stated area decides; a street only refines inside it; a street elsewhere does not change it | #88.1, #88.2 | areas, rule 1 |
| 48 | A name covering several entries, no street to refine: all of them | #112 | areas, rule 2 |
| 49 | No stated area, or an unplaceable name: the streets decide; a street in several areas gives all | #88.3, #124 | areas, rule 3 |
| 50 | Two streets: the common areas, else all of both | #88.4 | areas, rule 3 |
| 50a | No area name and no street: a well-known landmark that places the apartment decides; on a border, every area it touches; a general distance phrase places nothing | #178 | areas, rule 4 |
| 51 | Nothing placeable: no area | #88.5, #167 | areas, rule 5 |
| 52 | Another city: no area | — | areas, rule 5; #178 |
| 53 | The colloquial names as examples | #86, #167 | areas, the examples |
| 54 | The same names in English give the same numbers | — | areas, the examples; #178 |
| 55 | The display names of the five entries of #119 | #119 | The generated list |
| 56 | Other city as written, only when not Tel Aviv-Yafo; a landmark city is not one | #104; `BASELINE.md` §5 | other_city |
| 57 | Jaffa is Tel Aviv-Yafo | — | other_city; #178 |
| 58 | Name-number pairs, as written, unfiltered | #105, #151 | phone_name_pairs |
| — | **Applied by code after the answer, not in the text** | | |
| 59 | The native price fallback, only when the text has no price, and only from 500 | #95, #114 | `PHASE_2.md` 2.4 plan, step 3 |
| 60 | The entry date's year: the nearest occurrence to the publication date | #115 | Step 3 |
| 61 | A phone name kept only when its number matches `RawPost.phones` | #105 | Step 3 |
| 62 | A street, area name or other city not in the post's text is dropped and counted | #162, #180 | Step 3 |
| 63 | `areas` within 1–71, sorted, no repeats | #167, #174 | Step 3 |
| 64 | The rejection from `other_city` and `post_nature`, in Gate E's order | #92 | Step 4 |

#### 6. Tokens and cost with the 71 areas

The spike's cached prefix was **2,514 tokens**: 4,790 characters of instructions plus the schema.
Version 1 as approved (#178, with its two additions) renders to **9,025 characters**, 4,235 more:
about 3,290 of them English, digits and spacing, and 949 more Hebrew letters (the 71 names, the
examples). Hebrew costs more tokens per character, so the estimate uses ranges, about 0.22–0.30
tokens a character for the English and 0.5–0.8 for the Hebrew. That adds about **1,200–1,750
tokens**, and `areas` adds a few to the schema. Not tokenized: the first real call reports it.

| | Spike (measured) | Version 1 (estimate) |
|---|---|---|
| Cached prefix | 2,514 tokens | **about 3,700–4,250** |
| The post, uncached | 248 on average | 248 |
| Output | 272 at `none`, temperature 0 | about 285 (`areas` adds a short list) |
| Cost per post, prefix read from the cache | $0.000186 | **about $0.00021** |
| One cache write (first call of a job run, or after 30 minutes idle) | $0.00031 | about $0.00053 |
| First paid run, 195 posts (2.8) | about $0.04 | **about $0.04** |
| Regression set, 50 posts, two passes (2.6) | about $0.02 | about $0.02 |
| **Per month**, 4,500–7,500 posts, 36–48 job runs a day each writing the cache once | $1.2–1.9 | **about $1.5–2.3** |
| Worst case of one call, for the cap: every character a token at the cache-write price, plus the full 2,000 output tokens | — | about $0.003 |

The prefix grows by about half, but the output is most of the cost, so a post costs about 13%
more. Still estimates (O2, O10) until the regression set measures them.

#### 7. Tests, all offline

Under the network guard and the sleep guard (`tests/conftest.py`). The spike's raw responses are read
in place from `data/raw/openai_spike_2026-10-05/`, and a missing file fails the test.
- **`tests/test_listing_extraction.py`:**
  - The drift test (#137): every `Listing` field is in `ListingExtraction` with the same type, or
    in the code-filled list (`schema_version`, `listing_id`, `model_name`, `prompt_version`,
    `classified_at`, `price_source`, `entry_date`, `phone_names`).
  - The derived schema obeys strict mode: every property required, `additionalProperties: false`,
    no `allOf`, `not` or `if`.
  - The schema equals `schema_sent.json` but for the two expected differences.
  - The `EntryDateParts` rules: `immediate` with nulls; day and month required otherwise.
- **`tests/test_classify_instructions.py`:**
  - Rendering from a small `areas.yaml` built in the test puts every entry in once, label where
    there is one.
  - The real render holds all 71.
  - The fingerprint pins `PROMPT_VERSION`.
  - No `<<AREAS>>` is left over.
- **`tests/test_classify_request.py`:** the request a fake transport receives is exactly the one
  above, the user message is `post.text` and nothing else, and no other field is sent.
- **`tests/test_classify_complete.py`, one test or more per completion rule:**
  - The native fallback at 499, 500 and `None`; the text winning over native; an unclear text
    price staying unclear beside a native one.
  - The year: "1.10" in a post of 5.10, December in a post of January, 29 February, a written year,
    `immediate`, unclear and not written.
  - Phone names kept, dropped, and matched across formats ("+972-54…" against "054…").
  - #162: a street kept; a street not in the text dropped and returned; a prefixed name ("בצפון
    הישן") kept when the text has it; a blank entry dropped.
  - `areas` 72 and 0 refused; repeats and order fixed.
  - The provenance, with a fixed clock.
- **`tests/test_openai_classifier.py`:**
  - A completed answer: the spike's `none_t0` responses through a fake transport. They were
    produced before #167 and carry no `areas`, so the test adds `"areas": []` to the answer text in
    memory, and says so.
  - The usage, cost and reported model recorded.
  - **The failure kinds:**
    - a refusal, built from the documented shape (none was observed);
    - an incomplete answer (`probe_incomplete.json`, in place);
    - an invalid answer (a spike answer with a field broken, and one with `areas` [72]);
    - a network error and a timeout raised by the fake transport.
  - The cap stops before the send.
- **`tests/test_openai_transport.py`:** the SDK's exception mapping, through an `httpx.MockTransport`
  (no socket):
  - 401 with `probe_wrong_key.json`'s body, and 400 with `probe_schema.json`'s;
  - 429 rate with `Retry-After`, 429 `insufficient_quota` and 429 `project_spend_limit_exceeded`;
  - 503, and a timeout.
- **`tests/test_postmodel_rejects.py`:** each `post_nature` and `other_city` against the reason, the
  order (`other_city` over `seeking`), `sublet_offer` active, a non-pending record refused, and the
  failure fields kept.
- **`tests/test_stubs.py`:** the classifier stub's test removed; the `ListingStub` tests stay.

#### Order of work

1. The `external-contract-verification` skill (reading only).
2. The dependency, on Ron's approval: `uv add openai==3.24.0`.
3. `ListingExtraction` and its tests (drift, strict schema, against `schema_sent.json`).
4. The two parsing helpers and their tests.
5. `complete.py` and its tests.
6. `postmodel/rejects.py` and its tests.
7. The instructions file, its renderer, the fingerprint, and their tests.
8. `cost.py`, the transport, the classifier, and their tests.
9. The protocol change and the stub's removal.
10. `uv run pytest`, `ruff check`, `ruff format`; `CLAUDE.md`.

#### For Ron before code

- The instructions text, and each "proposed" row of its table.
- The layout above, and the names `ListingExtraction`'s module, `postmodel/` and `ClassificationError`.
- `openai==3.24.0`, pinned exactly, with the private schema helper (or `responses.parse`).
- `prompt_version` covering the whole request apart from the post (the fingerprint).
- The output limit (2,000) and the timeout (60 s).
- The six proposed completion points of step 3.

#### Conflicts with decisions or invariants

- **The spike's fixtures predate #167.** Its answers carry no `areas`, so no test can use them
  unchanged as a version 1 answer. They are read in place and augmented in memory, and no fixture
  file is edited.
- **The refusal, 429, 5xx and timeout shapes were never observed.** Their tests rest on the
  documentation and the SDK, not on a captured response, against the spirit of invariant 10. A
  refusal costs money to provoke and cannot be provoked on purpose. Recommended: accept, and
  capture the first real one into `data/raw/` when it happens.
- **Invariant 8 against #162:** the check compares the model's string with the stored text, exactly.
  The alternative of matching on normalized text would be a second use of normalized text, which
  invariant 8 forbids since #168.
- **The setting is not on `Listing`:** answered by the fingerprint above, if Ron agrees. Otherwise
  a `Listing` field would be needed (invariant 1).

---

## 2.5 `classify_pending` — approved (#138–#141, #152)

A separate job over the pending canonicals, one post at a time, each result written as it comes
(2.2). Run by hand after a collection run in phases 2–4; after each collection run by the phase 5
scheduler. Its command is the only code that reads `OPENAI_API_KEY` (#128).

**Within one run:**
- A network error, a timeout, a 429 for rate (honouring `Retry-After`) or a 5xx: about three
  attempts with backoff, then the post counts one failed run.
- A response that fails validation, or comes back `incomplete`: one retry, then a failed run.
- A refusal: no retry; a failed run.
- **The job's own cap, or a 429 for the project's spend limit** (`project_spend_limit_exceeded`):
  the job stops; **not** counted against any post.
- A disk or store error: the job fails, as in collection.

**Three failed runs** (#139, a Gate E amendment): the job skips the post, which shows in the
admin's pending list with its reason. **Approved (#152), in `SCHEMA.md` Gate E:**
`classification_failures` (`int`) and `last_classification_error` (`str` / `None`), with
`PostLifecycle` `schema_version` 2.

**Never at the same time as `run_once`** (#140): both by hand in phase 2; phase 5's "one run at a
time" covers the job.

**An edited post keeps its `Listing`** (#141).

**The source text is never touched** (#163, invariant 14): the job never writes a `RawPost`. A
test runs the job over a store and checks that every stored `RawPost` document is identical before
and after (2.2's contract test covers the store method itself).

**Cost visibility** (for #126's working-day measure): each run logs its calls, tokens by kind and
cost from the usage metadata, as JSON lines like `run_once`.

### Plan for task 2.5 — approved (#182); built 2026-10-05

**Built 2026-10-05, waiting for review.** No model call was made. The plan below holds, with
these deviations:
- **`jobs/common.py`.** It holds the moved pieces as two helpers, `job_logging()` (the handler,
  level and `run_id`) and `log_failure()`. `run_once.py` uses them; its behaviour and its 57 tests
  are unchanged. `tests/conftest.py` imports `SQLITE_FILENAME` from there.
- **`last_classification_error`** is cut at 200 characters.
- **A failure** whose record left `"pending"` during the call is discarded, as a success is, and
  not counted.
- **The arguments:** `--cap` must be above 0, and `--limit` 1 or more.
- **The dropped-names file** is created with its first line, so a run that writes nothing leaves no
  file.

**Scope:** the command, the loop over pending canonicals, the failure accounting, the cap, the log.
It is built on 2.4 and tested with a fake classifier and a fake transport. **No paid call:** the
first real run is the regression set's (2.6) or the first paid run's (2.8), each on its own go.

#### The command

```bash
uv run --env-file .env python -m tlv_hunter.jobs.classify_pending --cap 1.00             # PAID
uv run --env-file .env python -m tlv_hunter.jobs.classify_pending --cap 0.05 --limit 10  # PAID, a small try
```

- **`--cap` USD is required, with no default:** each run's cap is set by Ron when he starts it
  (#153, as 2.9 says for reclassify). A default can come with the phase 5 scheduler.
- **`--limit N`** (proposed) classifies at most N posts, the first N by `listing_id`.
- **The key:** `OPENAI_API_KEY` is read here and nowhere else (#128). When it is missing, the
  command logs that, exits 1 and opens nothing. It is passed to `openai_transport` and never logged.
- **The store:** the same SQLite file as `run_once`, `store_root` from the collection config. The
  command refuses to start when the file is missing, since SQLite would create an empty one. There
  is no `--bootstrap`.
- **Exit codes** (proposed):
  - 0: every post was attempted, whatever the outcome per post.
  - 2: stopped early, with the store consistent: the cap, the spend limit, the quota, a refused key
    or request.
  - 1: failed (a store or disk error, or anything unexpected), as `run_once`.

#### The loop — `tlv_hunter/classification_run.py`

The wiring, like `pipeline.py`, plus one table of data: the attempts per failure kind (below).
1. `repository.find_pending_canonicals()`, ordered by `listing_id` (#75 B).
2. For each post, its lifecycle record. With `classification_failures` at 3 or more, the post is
   skipped and counted (#139). This check comes before `--limit`, so skipped posts do not use the
   limit.
3. The attempts, through `classifier.classify(post)`. Every attempt passes the cap check first.
4. **Success:** the lifecycle record is **read again, right after the answer and before the
   write**.
   - Still `"pending"`: `save_classification(listing, classified_lifecycle(fresh, listing))`, one
     transaction (#131).
   - No longer pending: the answer is discarded and logged, and nothing is written. Only a
     concurrent `run_once` can cause this, which #140 rules out.
5. **A failed run of the post:** `save_lifecycle(failed_lifecycle(fresh, error))`. The count goes up
   by one and the short reason is recorded: `"timeout"`, `"network"`, `"rate_limit"`,
   `"server: 503"`, `"refusal"`, `"incomplete: max_output_tokens"` or
   `"invalid: price.value: int_type"`. No post text and no refusal text appear in it. At most one
   count per post per run (#139).
6. The job never writes a `RawPost` (#163): it calls no method that can.

**The attempts per failure kind** (approved in 2.5 above; the numbers are proposed):

| Kind | Attempts in this run | Then |
|---|---|---|
| `network`, `timeout`, `rate_limit` (429 for rate), `server` (5xx) | 3, waiting 2 s, then 10 s, or `Retry-After` when longer, up to 60 s. A longer `Retry-After` ends the post's attempts | A failed run |
| `invalid`, `incomplete` | 2 | A failed run |
| `refusal` | 1 | A failed run |
| The job's cap, before a call; `spend_limit` (429 `project_spend_limit_exceeded`) | — | **The job stops**; the post is not counted (approved) |
| `quota` (429 `insufficient_quota`), `auth` (401, 403), `bad_request` (400: the schema refused), 404 (the model) | — | **The job stops**; the post is not counted. *Proposed:* every post would fail the same way; #155 already stops the run on a tier refusal |
| A store or disk error | — | The job fails (exit 1), as collection |

Waits go through an injected `sleep`: the test suite refuses a real one (`tests/conftest.py`).

#### The cost cap, before each call

`CostMeter(cap)` (2.4).
- **Before every attempt:** if the money spent so far plus the worst case of this call would pass
  the cap, the job stops. The worst case counts every character of the request as a token, which
  is about three times the measured rate, at the cache-write price, plus the full 2,000 output
  tokens: about $0.003 a call.
- **Spent:** from the usage metadata of every call that returned a response, failed ones included
  (an `incomplete` or `invalid` answer is billed), at O2's list prices. Cache writes are priced
  inside `input_tokens`, as the spike report computed them.
- **The second line:** the project's hard spend limit, which is not instantaneous (O9).

#### The log lines

JSON lines on stderr, each with the run's `run_id`, as `run_once` writes them. **No post text, name,
phone or key in any line.**
- **Start:** the model, `prompt_version`, effort, temperature, cap, limit, the pending canonicals
  found, and those skipped at three failures.
- **One line per post:**
  - `listing_id`;
  - the outcome: active, rejected with its reason, failed with its kind, or discarded;
  - the attempts, and the seconds;
  - the tokens by kind (input, cached, cache write, output, reasoning) and the cost;
  - **the model value the response reported** (#149);
  - the count of streets and area names dropped by #162.
- **A stop:** its reason, and the post it stopped before.
- **End:**
  - posts attempted, active, rejected by reason, failed by kind, skipped, discarded;
  - calls, tokens by kind, cost against the cap;
  - the reported model values seen, the duration, and the stop reason or none.

#### The dropped names, for the report — FOR RON

The review report (2.7) lists the names dropped by #162 per post, and the log carries counts only.
They need a record, and a new stored file is invariant 1's business. Options:
- **A.** One JSON-lines file per run, `<store_root>/classify_runs/<run_id>.jsonl`. One line per post
  written: `listing_id`, `prompt_version`, the dropped streets, the dropped area names. It is under
  `data/` and gitignored. **Recommended.** *Why:* the report reads it without the store changing
  shape, and it never touches a `Listing`.
- **B.** The names in the per-post log line: post content in the log, against `run_once`'s practice.
- **C.** No record: the report shows counts only, against 2.7's "with counts" per name.

#### Never beside `run_once` (#140)

In phase 2 both are started by hand, never together. The job takes no lock, as `run_once` takes
none (#79 O9). What it does instead:
- it reads each lifecycle record again right before writing it, which shrinks the window from the
  whole run to milliseconds;
- it discards an answer for a post that is no longer pending.

What is left: two runs at once can still lose one write to the same record (last write wins, #65).
A lock file shared by both commands would close it, but it changes `run_once`. Not recommended
before phase 5's "one run at a time".

#### Files touched

| File | Change |
|---|---|
| `tlv_hunter/jobs/classify_pending.py` (new) | The command |
| `tlv_hunter/jobs/common.py` (new) | Moved from `run_once.py`, unchanged: `REPO_ROOT`, `CONFIG_ROOT`, `SQLITE_FILENAME`, the JSON log formatter, the `run_id` filter, `_describe`. `run_once.py` imports them; its behaviour and its tests do not change. `tests/conftest.py` imports `SQLITE_FILENAME` from the new place |
| `tlv_hunter/classification_run.py` (new) | The loop and the attempts table |
| `tlv_hunter/postmodel/rejects.py` | `failed_lifecycle` (2.4 step 4) |
| `tests/test_classification_run.py` (new), `tests/test_classify_pending_job.py` (new) | Below |
| `CLAUDE.md` | The command, marked PAID; the store-constructor sentence (conflict below); `classification_run.py` beside `pipeline.py` |

#### Tests, all offline

Fake classifier and fake transport, injected clock and sleep, temporary stores of both kinds.
- **`tests/test_classification_run.py`:**
  - Pending canonicals become `Listing`s, `"active"` or `"rejected"` with each reason, in
    `listing_id` order.
  - Duplicates, active, rejected and archived posts are not touched.
  - **Invariant 14 (#163):** every stored `RawPost` document is byte-identical before and after a
    run that mixes successes and failures.
  - A failure adds one and records the reason. A third failed run makes the next run skip the post.
    A later success leaves both fields as they are (#152).
  - The attempts per kind, with the waits taken from the fake sleep. `Retry-After` is honoured and
    capped. A refusal is not retried.
  - The cap stops before the call that could pass it, and the post is not counted; the spend limit
    does the same. So do `auth`, `quota` and `bad_request`.
  - A store error propagates.
  - A record that left `"pending"` during the call: the answer is discarded and nothing is written.
  - `--limit`, and skipped posts not using it.
- **`tests/test_classify_pending_job.py`:**
  - The missing key, and the missing store, which is not created.
  - **A sentinel key appears in no log line.**
  - Every line is JSON with the `run_id`. The per-post line carries the reported model.
  - The exit codes 0, 1 and 2.
  - The dropped-names file, if option A.

#### Order of work

1. `jobs/common.py`, then `run_once`'s tests unchanged and green.
2. `failed_lifecycle`.
3. `classification_run.py` with a fake classifier, and its tests.
4. The command, and its tests.
5. `pytest` and `ruff`.
6. `CLAUDE.md`.

#### For Ron before code

- The command, its flags (`--cap` required, `--limit`), and the exit codes.
- The attempt numbers, and the four stop kinds beyond the approved two.
- The dropped-names record (A, B or C).
- Reading the record again before the write, and discarding the answer.
- Moving the shared pieces of `run_once.py` to `jobs/common.py`.

#### Conflicts with decisions or invariants

- **`CLAUDE.md` says `jobs/run_once.py` is "the only code that constructs the production
  store".** `classify_pending` must construct it too. Proposed wording: "the two job commands are
  the only code that constructs the production store".
- **`pipeline.py` "holds no business logic":** `classification_run.py` holds the attempts table.
  It is data, the approved table of 2.5, but it is a rule in a wiring module. The alternative is a
  plain module of its own for one table.
- **#140 rests on discipline in phase 2.** Nothing in code prevents the two from running together.
- **The dropped names need a record that no approved schema holds** (invariant 1): the choice
  above.

---

## 2.6 The regression set — approved (#142, #143)

**About 50 posts** from the store (real phone numbers: it stays in `data/`, gitignored; tests read
it in place and fail when it is missing). Chosen to cover the `BACKLOG.md` rows (English posts;
"seeking a roommate for our flat" against "to search with"; #45's case), the store's hard cases
(seeking, two roommates, sublet, `שותף/ה`, `מחפשות`, native prices not in the text and below 500,
the caption with shared text, several prices or phones, Old North and Jaffa, another city), the 20
posts of the spike, **a real "seeking" post and a real Jaffa post from the store** (#165; the
spike's two were sale posts), and, from phase 3, every flagged post.

**Each run twice** at the chosen setting (#157), since temperature 0 is not deterministic (O12).

**Labelling, option C:** Ron labels the deciding fields blind, then corrects the rest from the
model's output in the review report (2.7).

**The labelling page** (#143). A command writes one static HTML file; no server, no network.

| What | File |
|---|---|
| **Open this to label** | `data/labeling/label_posts.html` |
| **Drop the export here** | `data/labeling/labels.json` |

- Per post: the original text, exactly as stored, and controls for the deciding fields only:
  post nature (five radio buttons); apartment kind (room, whole apartment, not written, unclear);
  price (written, not written, unclear, plus the amounts); gender (three radio buttons); entry date
  (immediate, a date, not written, unclear); **the areas, picked from the 71 (multi-select,
  searchable by name and number, #171)**; other city (a short input, empty for Tel Aviv-Yafo). An
  **"ambiguous"** mark and a short note.
- **No controls for streets or area names as written** (#177): `areas` is the only location field
  labelled blind. Streets and area names are judged in the review report (2.7).
- It **never shows the model's answer** for those fields.
- Progress is kept in the browser's local storage, by `listing_id`, so the page can be closed and
  reopened.
- **Export** downloads `labels.json` (to the browser's download folder). Ron moves it into
  `data/labeling/` once, replacing any older one; the code reads it only from there. A browser
  that names a second download `labels (1).json` needs it renamed.
- Proposed shape of `labels.json`: a format version, the export time, and per `listing_id` the
  deciding fields as `SCHEMA.md` names them, plus `ambiguous` and `note`.

**The pass bar** (#142): `post_nature` and `other_city` no error; `apartment_kind`, `price`,
`gender` and `areas` at least 95% exact; every other field at least 90%; no value filled in where
the label says not written. **A post Ron marks ambiguous is not counted.** `areas` is compared with
the areas Ron picked, as a set. **Streets and area names as written are not compared** (#177): they
are outside the bar, and Ron marks a wrong one in the review report.

**Running it:** paid, about $0.01–0.07 for 50 posts per pass at the estimates of 2.8; on every
prompt or model change, with the result saved next to the prompt version. **If `gpt-6-luna`
misses the bar:** back to Ron with the next model and its price (#127).

---

## 2.7 Ron's review report — approved (#143, #154)

A command reads the store read-only and writes one static HTML file; no server, no framework
(phase 3's choice stays open), no network.

| What | File |
|---|---|
| **Open this to review** | `data/labeling/review.html` |
| **Drop the export here** | `data/labeling/corrections.json` |

- One card per classified post: the original text, every field with its state, the areas with
  their labels, the rejection reason, the prompt version.
- Filters in the page: rejected or active, any field unclear, any street or area name dropped by
  #162.
- The streets and area names dropped by #162, with counts.
- **Streets and area names as written are judged here only** (#177). The labelling page has no
  control for them. Each card shows them beside the original text, and Ron marks one wrong if it is.
- **Corrections by the same mechanism as the labelling page:** a "wrong" mark and the right value
  per field, progress in the browser, an export to `corrections.json`, moved into
  `data/labeling/` and read from there. It replaces the draft's hand-written CSV.
- **From the corrections** (#172): a count of errors per field, so weak fields are visible, and
  every corrected post joins the regression set.

---

## 2.8 The first paid run over the stored posts — cap approved ($1, #153); go after the build and a passing regression set (#164)

After the spike, the regression set passing, and the review report built. Runs only on Ron's
separate go.

**Scope:** the pending canonicals at that moment: 195 on 2026-10-05, more if collection runs
first.

**Estimated cost, `gpt-6-luna`** (O2 prices; O10 tokens assumed as in 2.1; the instructions read
from the cache after the first call):

| | Per post | 195 posts | Per month, 4,500–7,500 posts |
|---|---|---|---|
| effort `none` | $0.0002–0.0008 | $0.04–0.16 | $1–6 |
| effort `low` | $0.0003–0.0013 | $0.06–0.25 | $1.5–10 |
| Cache writes, at most one per job run (up to 48 runs a day) | | | at most about $0.60 |

So **about $1–11 a month**, against collection's $20–26. **Measured in spike 2.1 (20 posts):** $0.00019 a
post at `none`, $0.00029 at `low`; this run about $0.04 at `none`; about $1.2–2.6 a month. Still
estimates until the run and a real working day measure them.

**Cap: $1** for this run (approved, #153), enforced by the job as in 2.1;
the project's hard spend limit as the second line.

**Checked after:** every pending canonical has a `Listing` and left pending, or is listed as
failed; the cost from the usage metadata against the bill read later (as P19 taught); the names
dropped by #162; Ron's review (2.7). Then the first real working day is measured (DoD 4).

---

## 2.9 Reclassify — approved (#144)

Started by hand only. **Which posts:** those whose `Listing` has a `prompt_version`,
`schema_version` or `model_name` that is not the current one, in states `"active"` and
`"rejected"` by the model; not the pre-model rejects; not archived posts. **Flagged posts** keep
their flag and state; their `Listing` may be replaced. **Effect:** a diff report (old against new,
per field) is written to `data/` first, then the new `Listing` replaces the old, `areas` from the
model's new answer, the rejection derived again. Each run has its own cap, set by Ron when he starts it. No bulk reclassify is
planned.

---

## 2.10 Gate D and dedup B — approved (#145)

After the first paid run, a read-only script lists about 30 candidate pairs: a different text
hash, and the same phone, or the same price, area and room count within a few days. Ron judges
them. If rewritten reposts are common, Gate D is settled on the evidence and dedup B is built in
phase 2; if rare, Gate D waits until after phase 3, with the measured rate recorded. #70 under
dedup B (#72.7) and the phone signal (#75 C) wait for the same gate.

---

## 3. Items this phase must close

Full register: `ASSUMPTIONS.md`.

| Item | Task |
|---|---|
| O1: `gpt-6-luna` answers, and as what | 2.1 |
| O2: its prices, on a real bill | 2.1, 2.8 |
| O3, O4: reasoning tokens at `none`; temperature only at `none` | 2.1 |
| O5, O11: the derived schema passes strict mode through the SDK | 2.1 |
| O7: caching with an explicit breakpoint | 2.1 |
| O8: the organization's usage tier | Before 2.1 |
| O10: tokens per post | 2.1 |
| I3: the model's cost is small | 2.8, then a working day (DoD 4) |
| C2: #45's seeking case | 2.6 |

O6 and O9 are settled from the documentation. C3 no longer applies; C4 and G1–G9 belong to Gemini,
now the alternative.

---

## 4. For Ron's decision

Answered 2026-10-05: the 2.2 plan (#174), the reduced 2.3 (#175), the model deciding the area
(#167), the code of 2.2 and 2.3 (#176), the regression set's location fields (#177, #183), the
instructions (#178) and the plans for 2.4 and 2.5 (#179–#182). Open now, not resolved here:

1. **Review of the code of tasks 2.4 and 2.5** (`SESSION_LOG.md`, 2026-10-05), with the deviations
   listed under each plan.
2. **The next task:** the regression set (2.6, the labelling page first, no model needed), then the
   first real calls, which are the regression set's two passes (paid, about $0.02), on their own
   go.

---

## Appendix — superseded 2026-10-05 by `DECISIONS.md` #167

Kept for the record; not to be built. #169 may bring a street table back as an aid.

### 2.3 as it was: Area files and the street table — approved (#132–#136, #158); the plan WAITING

**Files, in `reference/`, tracked in git:** `areas.yaml` (the 71, verbatim names, the five
display labels of #119, source and load date), `area_aliases.yaml` (the translation table),
`street_areas.generated.yaml` (regenerated whole, never edited by hand),
`street_areas.corrections.yaml` (Ron's).

**The derivation** (a script outside the package, run by hand; `osmium` and `shapely` in a
dev-only dependency group):
1. The 71 polygons from layer 511, in WGS84 if the service gives it (A1c), otherwise reprojected
   from EPSG:2039.
2. Every named way with a `highway` tag inside Tel Aviv-Yafo, from Geofabrik's
   `israel-and-palestine` extract, placed in the polygons it crosses, with a border buffer of about
   15 m tuned on known border streets.
3. The output keeps, per street, its areas and the OSM names it came from.

**The completeness check (A1b):** the register's 2,768 official Tel Aviv names (with 4,655
synonyms) against the OSM names, both ways; places that are not streets set apart. **Bar: 95%**
of the register's streets found, every miss listed for Ron.

**Matching a written name** (#135): through a lookup key from the one existing normalization
(`textnorm`), plus a short list of street prefixes to strip (`רחוב`, `רח'`, `שד'`). The key is
never stored, displayed or sent to the model. **The derivation reports every collision among Tel
Aviv street names** (two different names giving one key) before the table is relied on.

**Hebrew prefix letters** (#158): the model returns names as written ("בצפון הישן"). Matching
tries the exact key first; only when that fails it strips leading prefix letters (ב, ל, מ, ה, ו,
ש, כ and their combinations) and tries again, so בבלי, התקוה and לבנה are not harmed. Every
collision this creates among the 71 names, the translation table and the street table is
reported.

**The unmatched share** (#136): on every classification run, the share of streets and area names
that matched nothing, with the strings listed in the review report. No alarm level in phase 2.

#### Plan for task 2.3 — superseded (written 2026-10-05)

**Scope:** the four reference files, the derivation script and its reports, the lookup key with
the prefix rule (#135, #158), and the code that computes `areas` (#88, #110, #124). Nothing is
downloaded in the round that approves this plan.

**What is downloaded, when approved** (all to `data/raw/`, gitignored; no cost):

| What | From | Size |
|---|---|---|
| Layer 511 with its polygons, asked in WGS84 | `gisn.tel-aviv.gov.il/arcgis/rest/services/IView2/MapServer/511/query?where=1=1&outFields=ms_shchuna,shem_shchuna&returnGeometry=true&outSR=4326&f=geojson`, one request | Not known; estimated 1–3 MB for 71 polygons. Answers A1c |
| The OpenStreetMap extract | Geofabrik, `download.geofabrik.de/asia/israel-and-palestine-latest.osm.pbf` (ODbL 1.0) | 120,066,175 bytes (about 120 MB) on 2026-10-03; the file of the download day |
| The street register, Tel Aviv only | data.gov.il CKAN `datastore_search`, resource `bf185c7f-1a4e-4662-88c5-fa118a244bda` (with synonyms), filter `city_code` 5000: 7,423 rows in two pages of 5,000 | Not known; estimated 1–2 MB of JSON |

About 125 MB in all. Only the derived tables and the reports enter git.

**The `reference/` files** (formats proposed; YAML, UTF-8, Hebrew as written):
- `areas.yaml`: a `source` block (layer 511, the URL, the read date, `date_import`), then 71
  entries of `number`, `name` (verbatim) and, for the five of #119 only, `label`.
- `area_aliases.yaml`: entries of `name` (as written) and `areas` (numbers), starting with #86's
  rows. The 71 names and the five labels match without being listed here.
- `street_areas.generated.yaml`: a header (generated at, the OSM file's name, date and SHA-256,
  the layer-511 read date, the border buffer, the script's version, the ODbL attribution), then one
  entry per street: `name` (the register's official name when matched, else OSM's), `register_code`
  (or null), `synonyms` (the register's), `osm_names`, `areas`. Regenerated whole; never edited.
- `street_areas.corrections.yaml`: Ron's entries, `name` plus either `areas` (replaces the derived
  areas) or `remove: true`, with an optional `note`. Applied when the tables are loaded, so
  regeneration never touches it (#85).
- `reports/derivation_<date>.md` (proposed): the completeness check and the collision report, in
  git, since they hold no personal data.

**The derivation script:** `scripts/derive_street_areas.py` (proposed place: tracked, outside the
package, re-run whenever the street table is refreshed).
1. Load the 71 polygons; their union is the city's boundary.
2. Read the PBF with `osmium`: every way with a `highway` tag and a name (`name:he`, else `name`;
   `alt_name` and `old_name` kept as OSM names). **Proposed `highway` values:** `primary`,
   `secondary`, `tertiary`, `unclassified`, `residential`, `living_street`, `pedestrian`, and named
   `service` and `footway`; not `motorway`, `trunk` or the `_link` roads. The report counts each
   type.
3. Work in metres: the polygons and the lines in EPSG:2039, so the 15 m border buffer (#133) is
   15 metres. That needs `pyproj`, beside `osmium` and `shapely` (#133 named only those two).
4. Each street's areas: every polygon its line comes within 15 m of, inside the city.
5. Group the ways by name, match each name to the register (official names and synonyms) through
   the lookup key, write the generated table and the report.

**The completeness check (A1b, #134):** every one of the register's 2,768 official names against
the table's names, both ways. The register also lists places that are not streets. **Proposed:**
the report gives the share twice, over every official name and over the names left after a
keyword filter (`כיכר`, `גן`, `פארק`, `סנטר`, `מתחם`, `שכונת`, `קרית` and the like), and lists
every miss; Ron judges the misses against the 95% bar.

**The lookup key and the prefix rule:** one public function next to the hash, in
`tlv_hunter/textnorm/normalize.py`, built on the same normalization (NFC, niqqud, quotes and
geresh, emoji, final letters, whitespace, lower case). For names it then drops a leading
street-type word (`רחוב`, `רח`, `שדרות`, `שד`, `סמטת`, `סמ`). Matching (#158): the exact key of the
name as written; if nothing matches, the key of the name with one, two, then three leading letters
from ב, ל, מ, ה, ו, ש, כ removed, stopping at the first level that matches. **Proposed:** at most
three letters, and at least two letters must remain; if one level matches two different rows, the
name counts as unmatched and is reported.

**Conflict: hyphens.** The existing normalization keeps `-` and the maqaf, so "בן-יהודה" and
"בן יהודה" give different keys. Changing the normalization changes every stored `text_hash` and
breaks dedup against stored posts. Options:
- **A.** The lookup key also turns hyphens and the maqaf into a space, after the shared steps: one
  normalization, plus one key-only step. Reads #135's "one normalization, the existing one" as the
  shared core. **Recommended.**
- **B.** No change: the hyphenated forms come from the register's synonyms and the translation
  table only.

**The collision report (#158),** over every name in the three tables (the 71 names and five
labels, the aliases, the street names with their synonyms and OSM names):
- Exact collisions: one key reaching two different targets.
- Prefix collisions: a name with one to three leading prefix letters removed giving the key of a
  different target (for example, a written "לבנה" with no exact row would be stripped to "בנה",
  and reach a street of that name if one existed). The derivation does not fail on them: they are listed, and Ron settles each with a
  correction or an alias.

**The code that computes `areas`:** a plain module, proposed `tlv_hunter/areas/`:
- `reference.py`: the only code that reads `reference/`, loading and checking the four files into
  one immutable set of tables (71 entries numbered 1–71, labels only for the five, aliases and
  streets pointing only at 1–71, corrections applied).
- `compute.py`: `compute_areas(streets, stated_area_names, tables)`, pure, returning the areas, the
  unmatched streets and the unmatched area names (for the report, #136). #88 in order: names
  mapped (aliases, then the 71 names and labels) decide, and streets refine inside them; a stated
  area beats a street placed elsewhere; with no mapped name (#124 included) the streets decide,
  one street its areas, several the areas common to all, or all of them when none is common; no
  mapped street and no mapped name, no area. The result is sorted with no repeats.
- #162's check (a name not in the post's text is dropped) belongs to the classifier (2.4), before
  this function.

**Conflict: reading YAML.** `PHASE_1.md`'s anchor says "No module reads a YAML file directly"
(the config interface). Options: **A.** `areas/reference.py` is the one interface for
`reference/`, as the config interface is for `config/`, and the anchor is reworded to say so
(recommended); **B.** route the files through the config interface, against #132 ("`config/` holds
collection settings only"); **C.** JSON files instead of YAML.

**Tests:**
- `tests/test_lookup_key.py`: the shared steps; the street-type words; hyphens (if option A).
- `tests/test_area_matching.py`: בבלי, התקוה and לבנה still match exactly; "בצפון הישן" reaches
  30 and 31 through the alias; two- and three-letter prefixes; the ambiguity rule.
- `tests/test_compute_areas.py`: each rule of #88, #124, and a stated name with several entries
  (#112), on small tables built in the test.
- `tests/test_reference_files.py`: `areas.yaml` holds 71 entries equal to layer 511's names in
  `data/raw/tlv_gis_layer511_rows_2026-10-05.json`, read in place (fails if missing); the five
  labels; aliases and corrections valid; corrections applied over the generated table.
- `tests/test_derive_street_areas.py` (needs the dev-only group): placing synthetic lines in
  synthetic polygons with the buffer; register matching; the collision report on a small table.
  No OSM file needed.
All offline, under the network guard.

**Order of work:** `areas.yaml` and `area_aliases.yaml` from the fixture, the loader, their tests;
the lookup key and matching, their tests; `compute_areas` and its tests; the dev-only group
(`osmium`, `shapely`, `pyproj`: a `pyproject.toml` and `uv.lock` change), the script and its tests
on synthetic data; then, on Ron's go, the three downloads and the first derivation; Ron reads the
completeness and collision reports, and the corrections file is started from them.

**For Ron before code:** the four file formats and the reports' place; the names `scripts/` and
`tlv_hunter/areas/`; adding `pyproj`; the `highway` values; the non-street filter; the prefix depth
and the ambiguity rule; hyphens (A or B); the YAML-reading anchor (A, B or C); the downloads.
