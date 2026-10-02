import hashlib


def compute_listing_id(source_post_id: str) -> str:
    if not source_post_id:
        raise ValueError("source_post_id must not be empty")
    return hashlib.sha256(source_post_id.encode("utf-8")).hexdigest()
