"""Gate C's records (SCHEMA.md, Gate C; DECISIONS.md #288): the approved names and every rule
that is a validator (task 3.4 (b))."""

import json
import typing
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from tlv_hunter.contracts.classification_report import ClassificationReport, ReportableField
from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.contracts.listing import Listing, Marked
from tlv_hunter.contracts.profile import (
    DateRangeCriterion,
    Profile,
    RangeCriterion,
    SearchOption,
    new_profile,
)
from tlv_hunter.contracts.session import SESSION_LIFETIME, Session
from tlv_hunter.contracts.signup_key import SignupKey
from tlv_hunter.contracts.user import User
from tlv_hunter.contracts.viewed_post import ViewedPost

NOW = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
USER_ID = "1" * 32
ADMIN_ID = "2" * 32
KEY_ID = "3" * 32
HASH = "a" * 64
LISTING_ID = "b" * 64


def user(**changes: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "user_id": USER_ID,
        "username": "dana.k",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA",
        "is_admin": False,
        "created_at": NOW,
        "signup_key_id": KEY_ID,
        "must_change_password": False,
        "password_changed_at": NOW,
        "disabled_at": None,
        "failed_sign_ins": 0,
        "last_failed_sign_in_at": None,
        **changes,
    }


def key(**changes: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "key_id": KEY_ID,
        "key_hash": HASH,
        "label": "Dana",
        "created_at": NOW,
        "used_by": None,
        "used_at": None,
        "cancelled_at": None,
        **changes,
    }


def session(**changes: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "token_hash": HASH,
        "user_id": USER_ID,
        "created_at": NOW,
        "expires_at": NOW + SESSION_LIFETIME,
        "ended_at": None,
        **changes,
    }


def report(**changes: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "report_id": "4" * 32,
        "listing_id": LISTING_ID,
        "reported_by": USER_ID,
        "reported_at": NOW,
        "fields": ["price", "areas"],
        "note": None,
        "status": "open",
        "resolved_by": None,
        "resolved_at": None,
        **changes,
    }


def correction(**changes: Any) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "correction_id": "5" * 32,
        "listing_id": LISTING_ID,
        "field": "areas",
        "model_value": [52],
        "corrected_value": [42, 52],
        "corrected_by": ADMIN_ID,
        "corrected_at": NOW,
        "report_id": None,
        "removed_by": None,
        "removed_at": None,
        **changes,
    }


def option(**changes: Any) -> SearchOption:
    return new_profile(USER_ID, NOW).whole_apartment.model_copy(update=changes)


def round_trip[M: BaseModel](record: M) -> M:
    back = type(record).model_validate_json(record.model_dump_json())
    assert back == record
    return back


# --- the approved names (SCHEMA.md, "Every name and type") ---


@pytest.mark.parametrize(
    ("model", "names"),
    [
        (
            User,
            "schema_version user_id username password_hash is_admin created_at signup_key_id "
            "must_change_password password_changed_at disabled_at failed_sign_ins "
            "last_failed_sign_in_at",
        ),
        (SignupKey, "schema_version key_id key_hash label created_at used_by used_at cancelled_at"),
        (Session, "schema_version token_hash user_id created_at expires_at ended_at"),
        (Profile, "schema_version user_id room whole_apartment include_sublets updated_at"),
        (
            SearchOption,
            "enabled areas price_min price_max hide_women_only rooms "
            "floor size_sqm broker parking balcony entry_date",
        ),
        (DateRangeCriterion, "earliest latest level"),
        (ViewedPost, "schema_version user_id listing_id viewed_at"),
        (
            ClassificationReport,
            "schema_version report_id listing_id reported_by reported_at "
            "fields note status resolved_by resolved_at",
        ),
        (
            FieldCorrection,
            "schema_version correction_id listing_id field model_value "
            "corrected_value corrected_by corrected_at report_id removed_by "
            "removed_at",
        ),
    ],
)
def test_the_field_names_are_the_approved_ones(model: type[BaseModel], names: str) -> None:
    assert list(model.model_fields) == names.split()


def test_range_criterion_has_min_max_and_level() -> None:
    assert list(RangeCriterion[float].model_fields) == ["min", "max", "level"]


def test_every_reportable_field_is_a_listing_field() -> None:
    reportable = typing.get_args(ReportableField)
    assert len(reportable) == 22
    assert set(reportable) <= set(Listing.model_fields)


# --- User ---


def test_a_user_and_the_admin_round_trip() -> None:
    round_trip(User(**user()))
    round_trip(User(**user(user_id=ADMIN_ID, is_admin=True, signup_key_id=None)))


@pytest.mark.parametrize("username", ["dana", "Dana_K-1.x", "abc", "a" * 32])
def test_a_username_of_latin_letters_digits_and_three_signs_is_accepted(username: str) -> None:
    assert User(**user(username=username)).username == username


@pytest.mark.parametrize("username", ["ab", "a" * 33, "דנה", "dana k", "dana@x", "dana!"])
def test_any_other_username_is_refused(username: str) -> None:
    with pytest.raises(ValidationError, match="username"):
        User(**user(username=username))


def test_the_username_is_compared_in_lower_case() -> None:
    assert User(**user(username="Dana.K")).username_key == "dana.k"


@pytest.mark.parametrize("field", ["user_id", "signup_key_id"])
def test_an_id_that_is_not_32_hex_characters_is_refused(field: str) -> None:
    with pytest.raises(ValidationError, match="opaque id"):
        User(**user(**{field: "ron"}))


def test_signup_key_id_is_none_exactly_for_the_admin() -> None:
    with pytest.raises(ValidationError, match="exactly for the admin"):
        User(**user(signup_key_id=None))
    with pytest.raises(ValidationError, match="exactly for the admin"):
        User(**user(is_admin=True))


def test_the_admin_cannot_be_disabled() -> None:
    with pytest.raises(ValidationError, match="R8"):
        User(**user(user_id=ADMIN_ID, is_admin=True, signup_key_id=None, disabled_at=NOW))
    assert User(**user(disabled_at=NOW)).disabled_at == NOW


def test_the_failure_count_and_its_time_go_together() -> None:
    assert User(**user(failed_sign_ins=5, last_failed_sign_in_at=NOW)).failed_sign_ins == 5
    with pytest.raises(ValidationError):
        User(**user(failed_sign_ins=1))
    with pytest.raises(ValidationError):
        User(**user(last_failed_sign_in_at=NOW))
    with pytest.raises(ValidationError):
        User(**user(failed_sign_ins=-1, last_failed_sign_in_at=NOW))


def test_user_datetimes_are_utc() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        User(**user(created_at=datetime(2026, 10, 10, 9, 0)))


# --- SignupKey ---


def test_a_key_round_trips_and_is_usable_until_used_or_cancelled() -> None:
    assert round_trip(SignupKey(**key())).usable
    assert not SignupKey(**key(used_by=USER_ID, used_at=NOW)).usable
    assert not SignupKey(**key(cancelled_at=NOW)).usable


def test_a_key_holds_a_sha256_hash() -> None:
    with pytest.raises(ValidationError, match="SHA-256"):
        SignupKey(**key(key_hash="not-a-hash"))


def test_a_key_has_a_label() -> None:
    with pytest.raises(ValidationError, match="label"):
        SignupKey(**key(label="  "))


def test_used_by_and_used_at_go_together() -> None:
    with pytest.raises(ValidationError):
        SignupKey(**key(used_by=USER_ID))


def test_only_an_unused_key_is_cancelled() -> None:
    with pytest.raises(ValidationError, match="unused"):
        SignupKey(**key(used_by=USER_ID, used_at=NOW, cancelled_at=NOW))


# --- Session ---


def test_a_session_round_trips_and_lasts_thirty_days() -> None:
    round_trip(Session(**session()))
    assert SESSION_LIFETIME == timedelta(days=30)
    with pytest.raises(ValidationError, match="30 days"):
        Session(**session(expires_at=NOW + timedelta(days=31)))


def test_a_session_holds_only_a_hash() -> None:
    assert "token" not in Session.model_fields
    with pytest.raises(ValidationError, match="SHA-256"):
        Session(**session(token_hash="raw-token"))


# --- Profile ---


def test_a_new_profile_has_both_options_on_and_nothing_set() -> None:
    profile = round_trip(new_profile(USER_ID, NOW))
    assert profile.schema_version == 2 and not profile.include_sublets  # one switch (#317)
    for searched in (profile.room, profile.whole_apartment):
        assert searched.enabled and searched.hide_women_only
        assert searched.areas == [] and searched.price_min is None and searched.rooms is None
        assert searched.broker is None and searched.entry_date is None


def test_a_full_option_round_trips() -> None:
    full = option(
        areas=[30, 31, 52],
        price_min=4000,
        price_max=7000,
        rooms=RangeCriterion[float](min=2, max=3.5, level="critical"),
        floor=RangeCriterion[int](min=-1, max=None, level="preference"),
        size_sqm=RangeCriterion[float](min=50.0, max=None, level="preference"),
        broker="critical",
        parking="preference",
        balcony="preference",
        entry_date=DateRangeCriterion(earliest=date(2026, 11, 1), latest=None, level="critical"),
    )
    profile = new_profile(USER_ID, NOW).model_copy(update={"whole_apartment": full})
    round_trip(Profile.model_validate(profile.model_dump()))


def version_1_doc(room_sublets: bool, whole_sublets: bool) -> str:
    """A profile as version 1 stored it: an `include_sublets` in each option, none on the
    profile."""
    data = new_profile(USER_ID, NOW).model_dump(mode="json")
    del data["include_sublets"]
    data["schema_version"] = 1
    data["room"]["include_sublets"] = room_sublets
    data["whole_apartment"]["include_sublets"] = whole_sublets
    return json.dumps(data)


@pytest.mark.parametrize(
    ("room_sublets", "whole_sublets", "switched"),
    [(False, False, False), (True, False, True), (False, True, True), (True, True, True)],
)
def test_a_stored_version_1_profile_reads_as_version_2(
    room_sublets: bool, whole_sublets: bool, switched: bool
) -> None:
    """#317: read-time only, as `PostLifecycle.from_stored_json`; on when either option's
    switch was on. Ron's stored profile has both off."""
    read = Profile.from_stored_json(version_1_doc(room_sublets, whole_sublets))
    assert read == new_profile(USER_ID, NOW).model_copy(update={"include_sublets": switched})
    assert read.schema_version == 2
    assert "include_sublets" not in read.room.model_dump()
    round_trip(read)


def test_a_version_2_profile_with_a_per_option_switch_is_refused() -> None:
    data = json.loads(new_profile(USER_ID, NOW).model_dump_json())
    data["room"]["include_sublets"] = True
    with pytest.raises(ValidationError):
        Profile.from_stored_json(json.dumps(data))


def test_a_version_1_profile_with_a_profile_switch_is_refused() -> None:
    data = json.loads(version_1_doc(False, False))
    data["include_sublets"] = True
    with pytest.raises(ValueError, match="version-1"):
        Profile.from_stored_json(json.dumps(data))


def test_plain_model_validate_json_converts_nothing() -> None:
    """Only `from_stored_json` reads version 1 (the review of round 8): pydantic's own reader is
    untouched and refuses it."""
    with pytest.raises(ValidationError, match="schema_version"):
        Profile.model_validate_json(version_1_doc(True, False))
    assert "model_validate_json" not in Profile.__dict__


@pytest.mark.parametrize("version", [0, 3])
def test_an_unknown_profile_version_is_refused(version: int) -> None:
    data = json.loads(new_profile(USER_ID, NOW).model_dump_json())
    data["schema_version"] = version
    with pytest.raises(ValidationError, match="schema_version"):
        Profile.from_stored_json(json.dumps(data))


@pytest.mark.parametrize("areas", [[0], [72], [31, 30], [30, 30]])
def test_areas_are_sorted_distinct_numbers_1_to_71(areas: list[int]) -> None:
    with pytest.raises(ValidationError, match="areas"):
        SearchOption.model_validate({**option().model_dump(), "areas": areas})


def test_rooms_are_whole_or_half_numbers() -> None:
    fields = option().model_dump()
    with pytest.raises(ValidationError, match="half"):
        SearchOption.model_validate(
            {**fields, "rooms": {"min": 2.25, "max": None, "level": "preference"}}
        )


def test_the_lowest_floor_is_the_basement() -> None:
    fields = option().model_dump()
    with pytest.raises(ValidationError, match="basement"):
        SearchOption.model_validate(
            {**fields, "floor": {"min": -2, "max": None, "level": "preference"}}
        )


def test_a_range_has_an_end_and_its_ends_in_order() -> None:
    with pytest.raises(ValidationError, match="at least one end"):
        RangeCriterion[float](min=None, max=None, level="preference")
    with pytest.raises(ValidationError, match="exceed"):
        RangeCriterion[float](min=4, max=3, level="preference")
    with pytest.raises(ValidationError, match="at least one end"):
        DateRangeCriterion(earliest=None, latest=None, level="preference")
    with pytest.raises(ValidationError, match="after"):
        DateRangeCriterion(earliest=date(2026, 12, 1), latest=date(2026, 11, 1), level="critical")


def test_price_min_does_not_exceed_price_max() -> None:
    with pytest.raises(ValidationError, match="price_min"):
        SearchOption.model_validate({**option().model_dump(), "price_min": 8000, "price_max": 5})


def test_a_level_is_preference_or_critical() -> None:
    with pytest.raises(ValidationError):
        SearchOption.model_validate({**option().model_dump(), "broker": "wanted"})


def test_the_room_search_has_no_sqm_filter() -> None:
    profile = new_profile(USER_ID, NOW)
    sized = option(size_sqm=RangeCriterion[float](min=10.0, max=None, level="preference"))
    with pytest.raises(ValidationError, match="#247"):
        Profile.model_validate({**profile.model_dump(), "room": sized.model_dump()})


# --- ViewedPost ---


def test_a_viewed_post_round_trips() -> None:
    round_trip(ViewedPost(schema_version=1, user_id=USER_ID, listing_id=LISTING_ID, viewed_at=NOW))


# --- ClassificationReport ---


def test_a_report_round_trips_open_and_resolved() -> None:
    round_trip(ClassificationReport(**report(note="המחיר שגוי")))
    round_trip(
        ClassificationReport(**report(status="left_out", resolved_by=ADMIN_ID, resolved_at=NOW))
    )


@pytest.mark.parametrize("fields", [[], ["price", "price"], ["listing_id"]])
def test_a_report_names_one_or_more_distinct_reportable_fields(fields: list[str]) -> None:
    with pytest.raises(ValidationError):
        ClassificationReport(**report(fields=fields))


def test_the_note_is_at_most_500_characters() -> None:
    assert ClassificationReport(**report(note="x" * 500)).note == "x" * 500
    with pytest.raises(ValidationError, match="500"):
        ClassificationReport(**report(note="x" * 501))


def test_resolved_fields_are_set_exactly_when_the_report_is_not_open() -> None:
    with pytest.raises(ValidationError):
        ClassificationReport(**report(status="restored"))
    with pytest.raises(ValidationError):
        ClassificationReport(**report(resolved_by=ADMIN_ID, resolved_at=NOW))


# --- FieldCorrection ---


def test_a_correction_holds_values_of_the_fields_gate_b_type() -> None:
    priced = FieldCorrection(
        **correction(
            field="price",
            model_value={"state": "written", "value": [72000]},
            corrected_value=Marked[list[int]](state="unclear", value=None),
        )
    )
    assert isinstance(priced.model_value, Marked)
    assert round_trip(priced).corrected_value.state == "unclear"
    dated = round_trip(
        FieldCorrection(
            **correction(
                field="entry_date",
                model_value={"state": "written", "value": "2026-11-01"},
                corrected_value={"state": "written", "value": "immediate"},
            )
        )
    )
    assert dated.model_value.value == date(2026, 11, 1)
    assert round_trip(FieldCorrection(**correction())).corrected_value == [42, 52]


def test_a_value_not_of_the_fields_type_is_refused() -> None:
    with pytest.raises(ValidationError):
        FieldCorrection(**correction(corrected_value="Florentin"))
    with pytest.raises(ValidationError):
        FieldCorrection(**correction(field="price", corrected_value=[7200]))


def test_only_a_reportable_field_is_corrected() -> None:
    with pytest.raises(ValidationError):
        FieldCorrection(**correction(field="listing_id", model_value="a", corrected_value="b"))


def test_removed_by_and_removed_at_go_together() -> None:
    assert not FieldCorrection(**correction(removed_by=ADMIN_ID, removed_at=NOW)).in_force
    with pytest.raises(ValidationError):
        FieldCorrection(**correction(removed_by=ADMIN_ID))


# --- every record ---


@pytest.mark.parametrize(
    "build",
    [
        lambda: User(**user(schema_version=2)),
        lambda: SignupKey(**key(schema_version=2)),
        lambda: Session(**session(schema_version=2)),
        lambda: ClassificationReport(**report(schema_version=2)),
        lambda: FieldCorrection(**correction(schema_version=2)),
        lambda: ViewedPost(schema_version=2, user_id=USER_ID, listing_id="x", viewed_at=NOW),
    ],
)
def test_every_record_is_at_schema_version_1(build: Any) -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        build()
