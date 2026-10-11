"""The one place that hashes and checks passwords (SCHEMA.md, Gate C; DECISIONS.md #262, #264,
#290).

Argon2id through `argon2-cffi`, with the parameters named explicitly so they do not change with
the platform: RFC 9106's low-memory profile (`PHASE_3.md` 3.5). The stored value is the library's
encoded string. Tests pass `profiles.CHEAPEST` in, never the production profile.

A password, a hash or a key is never logged and never put in an exception's message.
"""

from argon2 import PasswordHasher, profiles
from argon2.exceptions import VerifyMismatchError

MIN_PASSWORD_LENGTH = 8  # #262
PRODUCTION_PARAMETERS = profiles.RFC_9106_LOW_MEMORY
PRODUCTION_HASHER = PasswordHasher.from_parameters(PRODUCTION_PARAMETERS)

# What the dummy check of an unknown username verifies against (#264, R1): never anyone's password.
_DUMMY_PASSWORD = "the dummy check of an unknown username"
_dummy_hashes: dict[tuple[object, ...], str] = {}


class PasswordTooShort(ValueError):
    """A password has at least 8 characters (#262)."""


def require_password_length(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordTooShort(f"a password has at least {MIN_PASSWORD_LENGTH} characters")


def hash_password(password: str, hasher: PasswordHasher = PRODUCTION_HASHER) -> str:
    """The Argon2id encoded string, with a random salt. Refuses a password under 8 characters."""
    require_password_length(password)
    return hasher.hash(password)


def check_password(
    stored_hash: str, password: str, hasher: PasswordHasher = PRODUCTION_HASHER
) -> bool:
    """`True` if the password matches. A wrong password is `False`, never an exception; a stored
    hash the library cannot read (`InvalidHashError`) still raises: that is a broken record."""
    try:
        return hasher.verify(stored_hash, password)
    except VerifyMismatchError:
        return False


def needs_rehash(stored_hash: str, hasher: PasswordHasher = PRODUCTION_HASHER) -> bool:
    """Whether the hash was made with other parameters; checked after each successful sign-in."""
    return hasher.check_needs_rehash(stored_hash)


def dummy_check(password: str, hasher: PasswordHasher = PRODUCTION_HASHER) -> None:
    """One check against a fixed dummy hash, so that an unknown username takes as long as a known
    one (#264, R1). The dummy hash is made once per process and per set of parameters."""
    check_password(_dummy_hash(hasher), password, hasher)


def _dummy_hash(hasher: PasswordHasher) -> str:
    parameters = (
        hasher.type,
        hasher.time_cost,
        hasher.memory_cost,
        hasher.parallelism,
        hasher.hash_len,
        hasher.salt_len,
    )
    if parameters not in _dummy_hashes:
        _dummy_hashes[parameters] = hasher.hash(_DUMMY_PASSWORD)
    return _dummy_hashes[parameters]
