"""The eighth seam: what users and the admin write through the site (DECISIONS.md #267, #289).

`UserDataStore` holds the Gate C records. It is not part of the Repository and never reads or
writes a `RawPost`, `Listing` or `PostLifecycle`. Compare and set raises the store's
`StaleRecordError`, as for `PostLifecycle` (#289).
"""

from collections.abc import Collection
from datetime import datetime
from typing import Protocol, runtime_checkable

from tlv_hunter.contracts.classification_report import ClassificationReport
from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.contracts.session import Session
from tlv_hunter.contracts.signup_key import SignupKey
from tlv_hunter.contracts.user import User


class KeyNotUsable(RuntimeError):
    """No key with that hash, or it is used or cancelled, or it is not the user's key."""


class UsernameTaken(RuntimeError):
    """Another user has the username, compared case-insensitively (#262)."""


class AdminExists(RuntimeError):
    """There is already an admin (#244)."""


class OpenReportExists(RuntimeError):
    """The reporter already has an open report on the post (#278, R4)."""


class CorrectionInForce(RuntimeError):
    """The post's field already has a correction in force."""


@runtime_checkable
class UserDataStore(Protocol):
    def create_admin(self, user: User, profile: Profile) -> User:
        """The admin and their profile, in one transaction. `AdminExists`, `UsernameTaken`."""
        ...

    def create_user(self, user: User, profile: Profile, key_hash: str, now: datetime) -> User:
        """One transaction: the key with `key_hash` must be usable and be `user.signup_key_id`
        (else `KeyNotUsable`); it is marked used by the user at `now`; the user and the profile
        are inserted. `UsernameTaken` leaves the key usable."""
        ...

    def get_user(self, user_id: str) -> User | None: ...

    def find_user_by_username(self, username: str) -> User | None:
        """Compared case-insensitively (#262)."""
        ...

    def list_users(self) -> list[User]: ...

    def save_user(self, record: User, *, expected: User) -> User:
        """Compare and set against `expected`; a username never changes (#262)."""
        ...

    def add_key(self, key: SignupKey) -> SignupKey:
        """A new key: unused and not cancelled."""
        ...

    def list_keys(self) -> list[SignupKey]: ...

    def save_key(self, record: SignupKey, *, expected: SignupKey) -> SignupKey:
        """Compare and set; a cancelled key is never un-cancelled (#266)."""
        ...

    def add_session(self, session: Session) -> Session: ...

    def find_session(self, token_hash: str) -> Session | None: ...

    def end_session(self, token_hash: str, now: datetime) -> None:
        """Sets `ended_at` on the session if it is still open."""
        ...

    def end_sessions(self, user_id: str, now: datetime, keep: str | None = None) -> int:
        """Sets `ended_at` on every open session of the user except the one whose token hash is
        `keep` (#263, R3); returns how many."""
        ...

    def get_profile(self, user_id: str) -> Profile | None: ...

    def save_profile(self, profile: Profile) -> Profile:
        """Whole-record replace: only its own user writes a profile (#289, point 4)."""
        ...

    def mark_viewed(self, user_id: str, listing_id: str, at: datetime) -> None:
        """Inserted only if absent: a reopen keeps the first time (#276)."""
        ...

    def unmark_viewed(self, user_id: str, listing_ids: Collection[str]) -> None: ...

    def viewed_listing_ids(self, user_id: str) -> set[str]: ...

    def add_report(self, report: ClassificationReport) -> ClassificationReport:
        """An open report. `OpenReportExists` if the reporter has one open on the post (#278)."""
        ...

    def find_reports(
        self, listing_id: str | None = None, status: str | None = None
    ) -> list[ClassificationReport]: ...

    def save_report(
        self, record: ClassificationReport, *, expected: ClassificationReport
    ) -> ClassificationReport:
        """Compare and set."""
        ...

    def add_correction(self, correction: FieldCorrection) -> FieldCorrection:
        """A correction in force. `CorrectionInForce` if the field already has one."""
        ...

    def find_corrections(
        self, listing_id: str | None = None, in_force: bool = True
    ) -> list[FieldCorrection]:
        """`in_force=True`: the corrections in force; `False`: every correction, removed ones
        included."""
        ...

    def save_correction(
        self, record: FieldCorrection, *, expected: FieldCorrection
    ) -> FieldCorrection:
        """Compare and set; a removed correction is never put back in force (#284)."""
        ...
