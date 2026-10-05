"""The answer completed in code (`PHASE_2.md` 2.4, step 3; DECISIONS.md #95, #105, #114, #115,
#162, #167, #178, #179, #180). One test or more per rule."""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from tests.conftest import post_with_text
from tlv_hunter.classify.complete import AnswerError, Provenance, complete
from tlv_hunter.contracts.listing import LISTING_SCHEMA_VERSION, Marked, PhoneName
from tlv_hunter.contracts.listing_extraction import ListingExtraction
from tlv_hunter.contracts.raw_post import RawPost

NOT_WRITTEN = {"state": "not_written", "value": None}
UNCLEAR = {"state": "unclear", "value": None}
PROVENANCE = Provenance(
    model_name="gpt-6-luna",
    prompt_version="1",
    classified_at=datetime(2026, 10, 5, 12, 0, tzinfo=UTC),
)
TEXT = 'דירת 3 חדרים ברחוב דיזנגוף בצפון הישן, 5,500 ש"ח. דני 054-1234567. Ramat Gan border'
POSTED = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)


def written(value: Any) -> dict[str, Any]:
    return {"state": "written", "value": value}


def extraction(**changes: Any) -> ListingExtraction:
    fields: dict[str, Any] = {
        "post_nature": "rental_offer",
        "apartment_kind": NOT_WRITTEN,
        "price": NOT_WRITTEN,
        "entry_date_written": None,
        "entry_date_parts": NOT_WRITTEN,
        "rooms": NOT_WRITTEN,
        "floor": NOT_WRITTEN,
        "building_floors": NOT_WRITTEN,
        "size_sqm": NOT_WRITTEN,
        "room_size_sqm": NOT_WRITTEN,
        "broker": NOT_WRITTEN,
        "balcony": NOT_WRITTEN,
        "parking": NOT_WRITTEN,
        "elevator": NOT_WRITTEN,
        "air_conditioning": NOT_WRITTEN,
        "furnished": NOT_WRITTEN,
        "arnona": NOT_WRITTEN,
        "house_committee": NOT_WRITTEN,
        "gender": "no_restriction",
        "streets": [],
        "stated_area_names": [],
        "areas": [],
        "other_city": None,
        "phone_name_pairs": [],
    }
    return ListingExtraction.model_validate({**fields, **changes})


@pytest.fixture
def post(posts: list[RawPost]) -> RawPost:
    return post_with_text(posts[0], TEXT, native_price=None, posted_at=POSTED)


def test_provenance_and_copied_fields(post: RawPost) -> None:
    answer = extraction(rooms=written(3.0), gender="women_only", post_nature="sublet_offer")
    listing = complete(answer, post, PROVENANCE).listing
    assert listing.schema_version == LISTING_SCHEMA_VERSION
    assert listing.listing_id == post.listing_id
    assert listing.model_name == "gpt-6-luna"
    assert listing.prompt_version == "1"
    assert listing.classified_at == PROVENANCE.classified_at
    assert listing.rooms.value == 3.0
    assert (listing.gender, listing.post_nature) == ("women_only", "sublet_offer")


def test_a_naive_classified_at_is_refused(post: RawPost) -> None:
    naive = Provenance("gpt-6-luna", "1", datetime(2026, 10, 5, 12, 0))
    with pytest.raises(ValidationError):
        complete(extraction(), post, naive)


# --- Price (#95, #114) ---


def test_a_text_price_wins_over_the_native_one(post: RawPost) -> None:
    listing = complete(
        extraction(price=written([5500])), post.with_changes(native_price=6000), PROVENANCE
    ).listing
    assert (listing.price.value, listing.price_source) == ([5500], "text")


def test_an_unclear_text_price_stays_unclear_beside_a_native_one(post: RawPost) -> None:
    listing = complete(
        extraction(price=UNCLEAR), post.with_changes(native_price=6000), PROVENANCE
    ).listing
    assert (listing.price.state, listing.price_source) == ("unclear", "text")


@pytest.mark.parametrize(
    ("native", "state", "value", "source"),
    [
        (500, "written", [500], "native"),
        (6000, "written", [6000], "native"),
        (499, "not_written", None, None),
        (None, "not_written", None, None),
    ],
)
def test_the_native_fallback_only_when_the_text_has_no_price(
    post: RawPost, native, state, value, source
) -> None:
    listing = complete(extraction(), post.with_changes(native_price=native), PROVENANCE).listing
    assert (listing.price.state, listing.price.value, listing.price_source) == (
        state,
        value,
        source,
    )


# --- Entry date (#96, #115, #123, #178, #179) ---


def parts(day: int | None, month: int | None, year: int | None = None) -> dict[str, Any]:
    return written({"immediate": False, "day": day, "month": month, "year": year})


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (
            parts(1, 10),
            Marked(state="written", value=date(2026, 10, 1)),
        ),  # "1.10" in a post of 5.10
        (parts(1, 2), Marked(state="written", value=date(2027, 2, 1))),
        (parts(1, 11, 2027), Marked(state="written", value=date(2027, 11, 1))),
        (parts(1, 11, 26), Marked(state="written", value=date(2026, 11, 1))),  # 20YY (#178)
        (parts(31, 11), Marked(state="unclear", value=None)),  # impossible (#179)
        (parts(29, 2, 2027), Marked(state="unclear", value=None)),
        (parts(29, 2), Marked(state="unclear", value=None)),  # none in 2025-2027
        (
            written({"immediate": True, "day": None, "month": None, "year": None}),
            Marked(state="written", value="immediate"),
        ),
        (UNCLEAR, Marked(state="unclear", value=None)),
        (NOT_WRITTEN, Marked(state="not_written", value=None)),
    ],
)
def test_entry_date(post: RawPost, answer: dict[str, Any], expected: Marked) -> None:
    listing = complete(extraction(entry_date_parts=answer), post, PROVENANCE).listing
    assert (listing.entry_date.state, listing.entry_date.value) == (expected.state, expected.value)


def test_entry_date_uses_the_posts_own_utc_date(posts: list[RawPost]) -> None:
    """#115, #179: `posted_at` on the UTC date. 31.12 23:30 UTC is 1.1 in Israel, still 31.12."""
    post = post_with_text(posts[0], TEXT, posted_at=datetime(2026, 12, 31, 23, 30, tzinfo=UTC))
    # From 31.12.2026, 2.7.2026 is 182 days back and 2.7.2027 183 ahead; from 1.1.2027 the reverse.
    listing = complete(extraction(entry_date_parts=parts(2, 7)), post, PROVENANCE).listing
    assert listing.entry_date.value == date(2026, 7, 2)


def test_entry_date_written_is_kept_verbatim(post: RawPost) -> None:
    listing = complete(extraction(entry_date_written=" 1.11 גמיש "), post, PROVENANCE).listing
    assert listing.entry_date_written == " 1.11 גמיש "


# --- Names not in the text (#162, #179, #180) ---


def test_streets_and_area_names_in_the_text_are_kept_with_prefix_letters(post: RawPost) -> None:
    completed = complete(
        extraction(streets=["דיזנגוף"], stated_area_names=["בצפון הישן"]), post, PROVENANCE
    )
    assert completed.listing.streets == ["דיזנגוף"]
    assert completed.listing.stated_area_names == ["בצפון הישן"]
    assert (completed.dropped_streets, completed.dropped_area_names) == ((), ())


def test_names_not_in_the_text_are_dropped_and_returned(post: RawPost) -> None:
    completed = complete(
        extraction(
            streets=["דיזנגוף", "בן יהודה", "  ", ""],
            stated_area_names=["בצפון הישן", "הצפון הישן"],
            areas=[30, 31],
        ),
        post,
        PROVENANCE,
    )
    assert completed.listing.streets == ["דיזנגוף"]
    assert completed.dropped_streets == ("בן יהודה",)
    # The text says "בצפון הישן": the prefix ב replaces the ה, so "הצפון הישן" is not in it.
    assert completed.listing.stated_area_names == ["בצפון הישן"]
    assert completed.dropped_area_names == ("הצפון הישן",)
    assert completed.listing.areas == [30, 31]  # the model decided the areas (#167)


def test_surrounding_whitespace_is_removed_before_the_match(post: RawPost) -> None:
    completed = complete(extraction(streets=[" דיזנגוף "]), post, PROVENANCE)
    assert completed.listing.streets == ["דיזנגוף"]


def test_a_name_in_another_case_is_dropped(post: RawPost) -> None:
    """#179: the match is exact, no normalization (invariant 8)."""
    completed = complete(extraction(stated_area_names=["ramat gan"]), post, PROVENANCE)
    assert completed.listing.stated_area_names == []
    assert completed.dropped_area_names == ("ramat gan",)


def test_other_city_in_the_text_is_kept(post: RawPost) -> None:
    completed = complete(extraction(other_city="Ramat Gan"), post, PROVENANCE)
    assert (completed.listing.other_city, completed.dropped_other_city) == ("Ramat Gan", None)


def test_other_city_not_in_the_text_is_dropped_and_counted(post: RawPost) -> None:
    """#180: an invented city would reject a Tel Aviv post for everyone."""
    completed = complete(extraction(other_city="חולון"), post, PROVENANCE)
    assert (completed.listing.other_city, completed.dropped_other_city) == (None, "חולון")


@pytest.mark.parametrize("blank", ["", "   "])
def test_a_blank_other_city_reads_as_none(post: RawPost, blank: str) -> None:
    completed = complete(extraction(other_city=blank), post, PROVENANCE)
    assert (completed.listing.other_city, completed.dropped_other_city) == (None, None)


# --- Areas (#167) ---


@pytest.mark.parametrize("number", [0, 72, -1])
def test_an_area_outside_1_to_71_is_refused(post: RawPost, number: int) -> None:
    with pytest.raises(AnswerError):
        complete(extraction(areas=[30, number]), post, PROVENANCE)


def test_areas_are_sorted_without_repeats(post: RawPost) -> None:
    listing = complete(extraction(areas=[31, 30, 31, 1]), post, PROVENANCE).listing
    assert listing.areas == [1, 30, 31]


# --- Phone names (#105, #179) ---


def pair(phone: str, name: str) -> dict[str, str]:
    return {"phone": phone, "name": name}


def test_a_phone_name_is_kept_when_its_number_was_extracted(post: RawPost) -> None:
    assert post.phones == ["0541234567"]
    listing = complete(
        extraction(phone_name_pairs=[pair("054-1234567", "דני")]), post, PROVENANCE
    ).listing
    assert listing.phone_names == [PhoneName(phone="0541234567", name="דני")]


def test_a_phone_name_matches_across_formats(post: RawPost) -> None:
    listing = complete(
        extraction(phone_name_pairs=[pair("+972-54-123-4567", "דני")]), post, PROVENANCE
    ).listing
    assert listing.phone_names == [PhoneName(phone="0541234567", name="דני")]


def test_a_phone_name_with_an_unknown_number_is_dropped(post: RawPost) -> None:
    listing = complete(
        extraction(phone_name_pairs=[pair("052-7654321", "רוני")]), post, PROVENANCE
    ).listing
    assert listing.phone_names == []


def test_a_repeated_pair_is_stored_once_and_a_blank_name_dropped(post: RawPost) -> None:
    answer = extraction(
        phone_name_pairs=[
            pair("054-1234567", "דני"),
            pair("0541234567", "דני"),
            pair("054-1234567", " "),
        ]
    )
    assert complete(answer, post, PROVENANCE).listing.phone_names == [
        PhoneName(phone="0541234567", name="דני")
    ]


def test_a_post_without_extracted_phones_is_refused(post: RawPost) -> None:
    with pytest.raises(ValueError, match="textnorm"):
        complete(
            extraction(), post.with_changes(no_text=None, text_hash=None, phones=None), PROVENANCE
        )
