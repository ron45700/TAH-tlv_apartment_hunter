"""New keys, session tokens and opaque ids, and the SHA-256 the store keeps of a key or token
(SCHEMA.md, Gate C, "Secrets are stored as hashes only"; DECISIONS.md #262, #266, #288).

Every value comes from `secrets`, the operating system's secure random source.
"""

import hashlib
import secrets

KEY_BYTES = 16  # 128 random bits (#266)
SESSION_TOKEN_BYTES = 32  # 256 random bits (#263)
OPAQUE_ID_BYTES = 16  # 32 hex characters (#262, #288)
LINK_CODE_BYTES = 24  # 32 URL-safe characters: a deep link's parameter allows 64 (#453)


def new_key() -> str:
    """A one-time key, URL-safe text; shown once to the admin and never stored (#266)."""
    return secrets.token_urlsafe(KEY_BYTES)


def new_session_token() -> str:
    """A session token, URL-safe text; it lives only in the user's cookie (#263)."""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def new_link_code() -> str:
    """A Telegram link code: 192 random bits as 32 characters of `A-Za-z0-9_-`, the characters a
    deep link's `start` parameter allows; shown once, in the link (#453)."""
    return secrets.token_urlsafe(LINK_CODE_BYTES)


def new_opaque_id() -> str:
    """A `user_id` or `key_id`: 32 lower-case hex characters."""
    return secrets.token_hex(OPAQUE_ID_BYTES)


def secret_hash(value: str) -> str:
    """The SHA-256 (lower-case hex) of a key or a session token: what the store keeps."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
