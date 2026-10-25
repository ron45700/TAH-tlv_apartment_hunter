"""Yad2 on the card, in the alert and in the digest (`PHASE_6.md` build step 6; DECISIONS.md #497,
#498, #520, #524, #525, #533–#535): the source, the link, no phone and no WhatsApp, the location as
given, the bootstrap's posts never alerting, a bump never alerting, Yad2's own digest section.
Synthetic posts through the real mapping (`tests/yad2_synthetic.py`); no fixture, no network."""

from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from tests.conftest import make_listing
from tests.test_alerts import AREAS, LINKED_AT, NOW, SITE, card_of, key_post, linked, profile
from tests.test_gate_d import written
from tests.test_gate_g import run_record
from tests.yad2_synthetic import listing_data, token
from tlv_hunter.dedup.stage_b import KeyPost
from tlv_hunter.notify.alert import alert_keyboard, build_alert, location_lines
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.postmodel.rejects import classified_lifecycle
from tlv_hunter.postmodel.seen import seen_listing
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.telegram.alerts import due_alerts, yad2_bootstrap_end
from tlv_hunter.telegram.digest import build_digest, digest_messages
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.web.cards import card_payload, post_payload
from tlv_hunter.web.grouping import Snapshot
from tlv_hunter.yad2.mapping import PERMALINK, to_raw_post

ZONE = ZoneInfo("Asia/Jerusalem")
NEIGHBOURHOOD = "נווה עופר, תל כביר"
STREET = "שלמה 12"
PHONE_TEXT = "דירה יפה, לפרטים 050-1234567"
YAD2_RUN = {"source": "yad2", "apify_run_id": None, "charged_events": None, "window_since": None}


def yad2_post(
    n: int,
    *,
    fetched=LINKED_AT + timedelta(hours=1),
    updated_at: str = "2026-10-13T12:30:00",
    **listing: Any,
) -> KeyPost:
    """A classified Yad2 listing, its text holding a mobile number, its form a place."""
    d = listing_data(token(n), updated_at=updated_at, metaData={"description": PHONE_TEXT})
    post = annotate(to_raw_post(d, fetched_at=fetched)).with_changes(
        is_canonical=True, duplicate_of=None
    )
    assert post.phones, "the description's number is extracted, as for any post"
    record = make_listing(
        post.listing_id,
        apartment_kind=written("whole_apartment"),
        price=written([6500]),
        price_source="native",
        areas=[50],
        stated_area_names=[NEIGHBOURHOOD, "יפו"],
        streets=[STREET, "רחוב אחר"],
        classified_at=NOW - timedelta(hours=1),
        **listing,
    )
    lifecycle = classified_lifecycle(initial_lifecycle(post), record, post)
    return KeyPost(post, lifecycle, seen_listing(record, []), frozenset())


# --- the card ---


def test_a_yad2_card_names_its_source_and_has_no_phone_or_whatsapp() -> None:
    member = yad2_post(1)
    card = card_of(member)
    evaluation = evaluate(member.seen, profile(), NOW)
    payload = card_payload(card, evaluation, profile(), AREAS.names)
    assert payload["source"] == "yad2"
    assert payload["permalink"] == PERMALINK.format(token=token(1))
    assert payload["whatsapp"] is None
    assert payload["text"] == PHONE_TEXT  # the original text, whole (invariant 11)
    opened = post_payload(card, AREAS.names)
    assert opened["source"] == "yad2" and opened["phones"] == []


def test_a_facebook_card_names_its_source_and_keeps_its_whatsapp() -> None:
    member = key_post(1, text="דירה, 050-1234567")
    card = card_of(member)
    evaluation = evaluate(member.seen, profile(), NOW)
    payload = card_payload(card, evaluation, profile(), AREAS.names)
    assert payload["source"] == "facebook" and payload["whatsapp"] is not None
    assert post_payload(card, AREAS.names)["phones"]


# --- the alert ---


def test_a_yad2_alerts_buttons_are_the_site_yad2_and_report_with_no_whatsapp() -> None:
    rows = alert_keyboard(card_of(yad2_post(1)), SITE)
    assert [[button.text for button in row] for row in rows] == [["פתיחה באתר"], ["יד2"], ["דיווח"]]
    assert rows[1][0].url == PERMALINK.format(token=token(1))


def test_a_yad2_alerts_location_is_as_yad2_gave_it() -> None:
    listing = yad2_post(1).seen.listing
    assert location_lines(listing, AREAS, source="yad2") == [
        f"- שכונה: {NEIGHBOURHOOD}",
        f"- רחוב: {STREET}",
    ]
    # Facebook's rule is unchanged for the same fields.
    assert location_lines(listing, AREAS)[0].startswith("- אזור: ")


def test_a_yad2_alert_builds_with_the_same_layout(tmp_path) -> None:
    member = yad2_post(1)
    card = card_of(member)
    evaluation = evaluate(member.seen, profile(), NOW)
    alert = build_alert(
        card, evaluation, profile(), AREAS, site_url=SITE, store_root=tmp_path, now=NOW
    )
    assert f"שכונה: {NEIGHBOURHOOD}" in alert.text and "מיקום מדויק לא ודאי" not in alert.text
    assert "וואטסאפ" not in [button.text for row in alert.keyboard for button in row]


# --- who is alerted (#520, #524, #525) ---


def _due(member: KeyPost, *, yad2_end):
    return due_alerts(linked(), profile(), [card_of(member)], set(), NOW, yad2_end=yad2_end)


def test_the_bootstraps_posts_never_alert_and_later_ones_do() -> None:
    end = LINKED_AT + timedelta(hours=1, minutes=30)
    bootstrap = yad2_post(1, fetched=LINKED_AT + timedelta(hours=1))
    later = yad2_post(2, fetched=LINKED_AT + timedelta(hours=2))
    assert _due(bootstrap, yad2_end=end) == []
    assert [card.shown_id for card, _ in _due(later, yad2_end=end)] == [later.post.listing_id]


def test_no_yad2_post_alerts_before_a_yad2_run_succeeded() -> None:
    assert _due(yad2_post(2, fetched=LINKED_AT + timedelta(hours=2)), yad2_end=None) == []
    # Facebook's posts do not wait for Yad2.
    assert _due(key_post(3), yad2_end=None)


def test_a_bump_never_alerts() -> None:
    """#520: a bump moves the clock only; the post's own times stay those of its first reading,
    before the user linked."""
    member = yad2_post(1, fetched=LINKED_AT - timedelta(days=2))
    bumped = KeyPost(
        member.post,
        member.lifecycle.model_copy(update={"last_published_at": NOW - timedelta(minutes=5)}),
        member.seen,
        frozenset(),
    )
    assert _due(bumped, yad2_end=LINKED_AT - timedelta(days=3)) == []


def test_a_listing_a_bump_brings_back_from_archive_never_alerts() -> None:
    """#524: classified again now, first read after the user linked, but published 26 days ago."""
    member = yad2_post(
        1, fetched=LINKED_AT + timedelta(minutes=5), updated_at="2026-09-17T12:00:00"
    )
    assert _due(member, yad2_end=LINKED_AT) == []


def test_the_bootstrap_ends_with_the_first_succeeded_yad2_run() -> None:
    first = run_record(
        **YAD2_RUN, run_id="y1", started_at=NOW, finished_at=NOW + timedelta(minutes=9)
    )
    failed = run_record(
        **YAD2_RUN,
        run_id="y0",
        status="failed",
        failure_kind="blocked: x",
        started_at=NOW - timedelta(hours=1),
        finished_at=NOW - timedelta(minutes=50),
    )
    later = run_record(
        **YAD2_RUN,
        run_id="y2",
        started_at=NOW + timedelta(hours=1),
        finished_at=NOW + timedelta(hours=2),
    )
    facebook = run_record(run_id="f", started_at=NOW - timedelta(hours=3), finished_at=NOW)
    assert yad2_bootstrap_end([later, first, failed, facebook]) == NOW + timedelta(minutes=9)
    assert yad2_bootstrap_end([failed, facebook]) is None


# --- the digest (#535) ---


def test_the_digest_counts_yad2_in_its_own_section_beside_facebooks() -> None:
    start, end = NOW - timedelta(hours=12), NOW + timedelta(hours=12)
    new = yad2_post(1, fetched=NOW)
    old = yad2_post(2, fetched=NOW - timedelta(days=3), updated_at="2026-10-10T12:00:00")
    bumped = KeyPost(
        old.post,
        old.lifecycle.model_copy(update={"last_published_at": NOW - timedelta(hours=2)}),
        old.seen,
        frozenset(),
    )
    snapshot = Snapshot(
        generation=1,
        cards=(),
        members={new.post.listing_id: new, bumped.post.listing_id: bumped},
        card_of={},
        others={},
        duplicates={},
    )
    runs = [
        run_record(**YAD2_RUN, run_id="y2", started_at=NOW, finished_at=NOW, rows_fetched=120),
        run_record(
            **YAD2_RUN,
            run_id="y1",
            status="failed",
            failure_kind="blocked: the page moved to validate.perfdrive.com",
            started_at=NOW - timedelta(hours=1),
            finished_at=NOW - timedelta(hours=1),
            rows_fetched=None,
        ),
        run_record(
            run_id="f1", started_at=NOW - timedelta(hours=2), finished_at=NOW, rows_fetched=12
        ),
    ]
    names = {"yad2-tel-aviv": "יד2 · תל אביב-יפו"}
    digest = build_digest(snapshot, runs, [], None, [], [], start, end, group_names=names)
    assert digest.runs == 1 and digest.rows_fetched == 12  # Facebook's only
    yad2 = digest.yad2
    assert (yad2.runs, yad2.failed, yad2.blocked, yad2.listings_read) == (2, 1, 1, 120)
    assert (yad2.new, yad2.bumped) == (1, 1)
    lines = "\n".join(digest_messages(digest, ZONE)).replace("‏", "").split("\n")
    at = lines.index("<b>-יד2-</b>")
    assert lines[at + 1 : at + 6] == [
        "• 2 ריצות",
        "• 1 נכשלו (1 חסימות)",
        "• 120 מודעות נקראו ברשימה",
        "• 1 מודעות חדשות",
        "• 1 הוקפצו",
    ]
    facebook = lines.index("<b>-ריצות פייסבוק-</b>")
    assert lines[facebook + 1 : facebook + 3] == ["• 1 ריצות", "• 0 נכשלו"]
    assert "<b>-יד2 · תל אביב-יפו-</b>" in lines
    assert any("יד2 · blocked: the page moved" in line for line in lines)


def test_without_a_yad2_run_the_digest_has_no_yad2_section() -> None:
    snapshot = Snapshot(generation=1, cards=(), members={}, card_of={}, others={}, duplicates={})
    digest = build_digest(snapshot, [], [], None, [], [], NOW - timedelta(hours=1), NOW)
    assert "<b>-יד2-</b>" not in "\n".join(digest_messages(digest, ZONE))
