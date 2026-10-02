from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.conftest import CONFIG_ROOT, FETCHED_AT, THEDOOR_20
from tlv_hunter.classify.base import Classifier
from tlv_hunter.classify.classifier_stub import ClassifierStub
from tlv_hunter.config.base import ConfigSource
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.decision_stub import DecisionStub
from tlv_hunter.contracts.listing_stub import ListingStub
from tlv_hunter.notify.base import Notifier
from tlv_hunter.notify.notifier_stub import RecordingNotifierStub
from tlv_hunter.policy.base import Policy
from tlv_hunter.policy.policy_stub import AlwaysNotifyPolicyStub
from tlv_hunter.providers.base import Provider
from tlv_hunter.providers.fixture import FixtureProvider
from tlv_hunter.store.base import Repository
from tlv_hunter.store.local_json import LocalJsonRepository


def test_listing_stub_fields_are_exactly_approved() -> None:
    assert set(ListingStub.model_fields) == {"listing_id"}


def test_decision_stub_fields_are_exactly_approved() -> None:
    assert set(DecisionStub.model_fields) == {"user_id", "listing_id", "notify"}


def test_stubs_reject_unapproved_fields() -> None:
    with pytest.raises(ValidationError):
        ListingStub(listing_id="x", price=1)
    with pytest.raises(ValidationError):
        DecisionStub(user_id="ron", listing_id="x", notify=True, reasons=[])


def test_stub_names_say_stub() -> None:
    contracts = Path(__file__).resolve().parent.parent / "tlv_hunter" / "contracts"
    assert (contracts / "listing_stub.py").is_file()
    assert (contracts / "decision_stub.py").is_file()
    assert not (contracts / "listing.py").exists()
    assert not (contracts / "decision.py").exists()


def test_implementations_satisfy_their_protocols(tmp_path: Path) -> None:
    assert isinstance(FixtureProvider(THEDOOR_20, lambda: FETCHED_AT), Provider)
    assert isinstance(LocalJsonRepository(tmp_path), Repository)
    assert isinstance(YamlConfig(CONFIG_ROOT), ConfigSource)
    assert isinstance(ClassifierStub(), Classifier)
    assert isinstance(AlwaysNotifyPolicyStub("ron"), Policy)
    assert isinstance(RecordingNotifierStub(), Notifier)


def test_repository_has_no_delete() -> None:
    assert not any("delete" in name or "remove" in name for name in dir(Repository))
    assert not any("delete" in name or "remove" in name for name in dir(LocalJsonRepository))


def test_policy_stub_always_notifies_for_its_user() -> None:
    decision = AlwaysNotifyPolicyStub("ron").decide(ListingStub(listing_id="abc"))
    assert decision == DecisionStub(user_id="ron", listing_id="abc", notify=True)


def test_recording_notifier_captures_calls() -> None:
    notifier = RecordingNotifierStub()
    listing = ListingStub(listing_id="abc")
    decision = DecisionStub(user_id="ron", listing_id="abc", notify=True)
    notifier.send(listing, decision)
    assert notifier.sent == [(listing, decision)]


def test_fixture_provider_filters_by_group_and_since() -> None:
    provider = FixtureProvider(THEDOOR_20, lambda: FETCHED_AT)
    early = datetime(2026, 9, 1, tzinfo=UTC)
    assert len(provider.fetch(["35819517694", "333022240594651"], early)) == 20
    assert {p.group_id for p in provider.fetch(["35819517694"], early)} == {"35819517694"}
    assert len(provider.fetch(["35819517694"], early)) == 10
    assert (
        provider.fetch(["35819517694", "333022240594651"], datetime(2027, 1, 1, tzinfo=UTC)) == []
    )
