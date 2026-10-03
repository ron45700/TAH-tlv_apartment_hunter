from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.textnorm.normalize import compute_text_hash, normalizes_to_nothing
from tlv_hunter.textnorm.phones import extract_phones


def annotate(post: RawPost) -> RawPost:
    return post.with_changes(
        no_text=normalizes_to_nothing(post.text),
        text_hash=compute_text_hash(post.text),
        phones=extract_phones(post.text),
    )
