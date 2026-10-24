import hashlib

YAD2_SOURCE = "yad2"


def compute_listing_id(source_post_id: str, *, source: str | None = None) -> str:
    """Facebook's providers: `sha256(source_post_id)`, `source` left out on purpose so one post read
    by two providers is one record (Gate A). Yad2: `sha256("yad2:" + token)` (DECISIONS.md #496)."""
    if not source_post_id:
        raise ValueError("source_post_id must not be empty")
    key = f"{YAD2_SOURCE}:{source_post_id}" if source == YAD2_SOURCE else source_post_id
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
