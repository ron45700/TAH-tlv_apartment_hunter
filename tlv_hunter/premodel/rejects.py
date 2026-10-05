from typing import Literal, get_args

from tlv_hunter.contracts.post_lifecycle import POST_LIFECYCLE_SCHEMA_VERSION, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost

PreModelReason = Literal["no_text", "no_images"]
_PRE_MODEL_REASONS = get_args(PreModelReason)


def pre_model_reason(post: RawPost) -> PreModelReason | None:
    """The first pre-model rule that applies, in Gate E order; None when the post passes both.

    `no_images` means no media of any kind (DECISIONS.md #67). A shared post needs nothing more:
    the mapper already falls back to `sharedPost.media` when the post's own media is empty.
    """
    if post.no_text is None:
        raise ValueError("no_text is None: textnorm must run before the pre-model rejects")
    if post.no_text:
        return "no_text"
    if not post.media:
        return "no_images"
    return None


def initial_lifecycle(post: RawPost) -> PostLifecycle:
    """The lifecycle record of a post seen for the first time. Never stored here."""
    reason = pre_model_reason(post)
    return PostLifecycle(
        schema_version=POST_LIFECYCLE_SCHEMA_VERSION,
        listing_id=post.listing_id,
        state="pending" if reason is None else "rejected",
        rejection_reason=reason,
        flagged_by=None,
        flagged_at=None,
        flag_note=None,
        last_published_at=post.posted_at,
        images=[],
        classification_failures=0,
        last_classification_error=None,
    )


def recheck(existing: PostLifecycle, post: RawPost) -> PostLifecycle:
    """The record of a re-fetched post, re-checked against both rules on its current content.

    Only a `"pending"` record, or a `"rejected"` one with a pre-model reason, is re-checked
    (DECISIONS.md #72.1, #73). Any other record is returned unchanged: a post with a verdict, and
    an archived post, are left untouched.
    """
    if existing.listing_id != post.listing_id:
        raise ValueError(
            f"lifecycle record {existing.listing_id} does not belong to post {post.listing_id}"
        )
    rejected_before_model = (
        existing.state == "rejected" and existing.rejection_reason in _PRE_MODEL_REASONS
    )
    if existing.state != "pending" and not rejected_before_model:
        return existing
    reason = pre_model_reason(post)
    return PostLifecycle(
        **{
            **dict(existing),
            "state": "pending" if reason is None else "rejected",
            "rejection_reason": reason,
        }
    )
