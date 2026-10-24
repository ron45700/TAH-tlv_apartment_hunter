from typing import Literal

from tlv_hunter.contracts.post_lifecycle import POST_LIFECYCLE_SCHEMA_VERSION, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.parsing.ids import YAD2_SOURCE
from tlv_hunter.yad2.kinds import kind_ruling
from tlv_hunter.yad2.mapping import model_block

PreModelReason = Literal["no_text", "no_images", "not_listing"]


def pre_model_reason(post: RawPost) -> PreModelReason | None:
    """The first pre-model rule that applies, in Gate E order; None when the post passes.

    Facebook: `no_text`, then `no_images`, which means no media of any kind (DECISIONS.md #67). A
    shared post needs nothing more: the mapper already falls back to `sharedPost.media` when the
    post's own media is empty.

    Yad2 (Gate E's Yad2 rules): `no_text` only when there is no description and nothing for the
    labelled block either (#509, #518); never `no_images` (#510); `not_listing` when the property
    kind says so (#502 point 11), with no model call.
    """
    if post.no_text is None:
        raise ValueError("no_text is None: textnorm must run before the pre-model rejects")
    if post.source == YAD2_SOURCE:
        if post.no_text and model_block(post.raw) is None:
            return "no_text"
        if _kind_rejects(post):
            return "not_listing"
        return None
    if post.no_text:
        return "no_text"
    if not post.media:
        return "no_images"
    return None


def _kind_rejects(post: RawPost) -> bool:
    details = post.raw.get("additionalDetails")
    kind = details.get("property", {}).get("id") if isinstance(details, dict) else None
    return kind_ruling(kind if type(kind) is int else None).rejected_before_model


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


def rejected_before_model(record: PostLifecycle, post: RawPost) -> bool:
    """Whether a rejected record's reason is a pre-model one for this post: `no_text` and
    `no_images` always; `not_listing` only for a Yad2 post whose kind decides it (the model's
    `not_listing` is a verdict, never re-checked)."""
    if record.state != "rejected":
        return False
    if record.rejection_reason in ("no_text", "no_images"):
        return True
    return (
        record.rejection_reason == "not_listing"
        and post.source == YAD2_SOURCE
        and _kind_rejects(post)
    )


def recheck(existing: PostLifecycle, post: RawPost) -> PostLifecycle:
    """The record of a re-fetched post, re-checked against the pre-model rules on its current
    content.

    Only a `"pending"` record, or a `"rejected"` one with a pre-model reason, is re-checked
    (DECISIONS.md #72.1, #73). Any other record is returned unchanged: a post with a verdict, and
    an archived post, are left untouched.
    """
    if existing.listing_id != post.listing_id:
        raise ValueError(
            f"lifecycle record {existing.listing_id} does not belong to post {post.listing_id}"
        )
    if existing.state != "pending" and not rejected_before_model(existing, post):
        return existing
    reason = pre_model_reason(post)
    return PostLifecycle(
        **{
            **dict(existing),
            "state": "pending" if reason is None else "rejected",
            "rejection_reason": reason,
        }
    )
