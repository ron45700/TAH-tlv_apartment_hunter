from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from tlv_hunter.classify.base import Classifier
from tlv_hunter.contracts.decision_stub import DecisionStub
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.notify.base import Notifier
from tlv_hunter.policy.base import Policy
from tlv_hunter.providers.base import Provider
from tlv_hunter.store.base import Repository
from tlv_hunter.textnorm.annotate import annotate


@dataclass(frozen=True)
class RunResult:
    stored: tuple[RawPost, ...]
    decisions: tuple[DecisionStub, ...]


def run_pipeline(
    *,
    provider: Provider,
    repository: Repository,
    classifier: Classifier,
    policy: Policy,
    notifier: Notifier,
    group_ids: Sequence[str],
    since: datetime,
) -> RunResult:
    posts = [annotate(post) for post in provider.fetch(group_ids, since)]
    verdicts = [
        (listing, policy.decide(listing))
        for listing in (classifier.classify(post) for post in posts if not post.no_text)
    ]
    stored = tuple(repository.upsert(post) for post in posts)
    for listing, decision in verdicts:
        if decision.notify:
            notifier.send(listing, decision)
    return RunResult(stored=stored, decisions=tuple(decision for _, decision in verdicts))
