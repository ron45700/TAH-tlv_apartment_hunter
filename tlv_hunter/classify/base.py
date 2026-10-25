from typing import Literal, Protocol, runtime_checkable

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.raw_post import RawPost

ErrorKind = Literal[
    # From the transport: no answer came back, nothing billed.
    "network",
    "timeout",
    "rate_limit",
    "server",
    "spend_limit",
    "quota",
    "auth",
    "bad_request",
    "not_found",
    # A 400 whose code is `invalid_prompt`: OpenAI refused this one post's input (DECISIONS.md
    # #536): a failure of the post, not of the run. Nothing billed.
    "invalid_prompt",
    # From the answer: billed.
    "incomplete",
    "refusal",
    "invalid",
]


class ClassificationError(Exception):
    """One classification attempt failed. `detail` never carries post content or the model's
    text: it is stored as `last_classification_error` and logged (DECISIONS.md #139)."""

    def __init__(
        self,
        kind: ErrorKind,
        detail: str,
        *,
        retry_after: float | None = None,
        provider_message: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind
        self.detail = detail
        self.retry_after = retry_after
        # OpenAI's own message and its `x-request-id`, for the log only, never stored (#536 C).
        self.provider_message = provider_message
        self.request_id = request_id


@runtime_checkable
class Classifier(Protocol):
    def classify(self, post: RawPost) -> Listing:
        """Extraction only (`CLAUDE.md`): one call, completed in code. Writes nothing. Raises
        ClassificationError when the attempt fails."""
        ...
