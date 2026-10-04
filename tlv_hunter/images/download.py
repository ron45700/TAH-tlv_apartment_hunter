"""Task 1.12: photo download (DECISIONS.md #63, #70, #72.3, #73.5, #76, #77, #80).

Reads the Repository and writes nothing to it: the lifecycle records are returned, and the store
step is task 1.14. Files are written under `<store_root>/images/`. A failed download fails neither
the run nor the post; a disk write error fails the run (#77 D5a). A network error waits on a fixed
schedule, and failed photos of stored posts are retried from the stored link (#80).
"""

import hashlib
import http.client
import logging
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from tlv_hunter.contracts.post_lifecycle import PostImage, PostLifecycle
from tlv_hunter.contracts.raw_post import Media, RawPost
from tlv_hunter.dedup.stage_a import DedupResult
from tlv_hunter.store.base import Repository

PHOTO = "Photo"
IMAGES_DIR = "images"
# Sent as in spike 1.1a. Not a login or a cookie (invariant 13); kept even though the 2026-10-04
# check downloaded without it (#77 D5c).
USER_AGENT = "Mozilla/5.0"
SOCKET_TIMEOUT_SECS = 30
IMAGE_CAP_SECS = 60
MAX_IMAGE_BYTES = 20 * 1024 * 1024
# The whole download step; a hanging CDN must not hang the run (#77 D5b).
TIME_BUDGET_SECS = 1800
NOT_ATTEMPTED = "not attempted: time budget"
# After a network error the whole step waits, then tries the same photo again, per outage (#80).
# The waits count inside TIME_BUDGET_SECS.
NETWORK_WAITS_SECS = (60, 180, 300, 600)
# A stored link is retried only while its post was first fetched less than this long ago: links
# live about 4.4 days (ASSUMPTIONS.md I7), and what an expired one returns is unknown (#80 U5).
STORED_LINK_MAX_AGE = timedelta(days=4)
TIMEOUT = "timeout"
NETWORK = "network: "
# The errors retried from the stored link (#80 decision 2): the network-type ones, and the budget.
RETRYABLE_ERRORS = (NETWORK, TIMEOUT, NOT_ATTEMPTED)
_CHUNK_BYTES = 64 * 1024

logger = logging.getLogger(__name__)


class ImageFetchError(Exception):
    """A download failed before a response could be judged. `reason` goes to `PostImage.error`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ImageWriteError(RuntimeError):
    """A photo could not be written to disk. Fails the run (#77 D5a)."""


@dataclass(frozen=True)
class ImageResponse:
    status: int
    content_type: str | None
    body: bytes


class ImageTransport(Protocol):
    def __call__(self, url: str) -> ImageResponse:
        """One GET. Raises ImageFetchError for a network error, a timeout or an oversize body."""
        ...


def urllib_image_transport(url: str) -> ImageResponse:
    """A plain GET: no token, no cookie, no login (invariant 13)."""
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=SOCKET_TIMEOUT_SECS) as response:
            body = bytearray()
            while chunk := response.read(_CHUNK_BYTES):
                body += chunk
                if len(body) > MAX_IMAGE_BYTES:
                    raise ImageFetchError("too large")
                if time.monotonic() - started > IMAGE_CAP_SECS:
                    raise ImageFetchError(TIMEOUT)
            return ImageResponse(response.status, response.headers.get("Content-Type"), bytes(body))
    except urllib.error.HTTPError as error:
        return ImageResponse(error.code, error.headers.get("Content-Type"), b"")
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise ImageFetchError(TIMEOUT) from None
        raise ImageFetchError(f"{NETWORK}{type(error.reason).__name__}") from None
    except TimeoutError:
        raise ImageFetchError(TIMEOUT) from None
    except (OSError, http.client.HTTPException) as error:
        raise ImageFetchError(f"{NETWORK}{type(error).__name__}") from None


def is_network_error(reason: str | None) -> bool:
    """A network-type failure (#80): DNS, connection, TLS, and both timeouts (U1). Never an HTTP
    status or a judged response."""
    return reason is not None and (reason == TIMEOUT or reason.startswith(NETWORK))


def download_images(
    result: DedupResult,
    repository: Repository,
    store_root: Path,
    transport: ImageTransport = urllib_image_transport,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] | None = None,
    now: datetime | None = None,
) -> DedupResult:
    """`dedup_a`'s result with the photos downloaded and recorded in the lifecycle records.

    `posts` is returned unchanged. `lifecycles` keeps its records and order, with `images`
    updated; a stored canonical outside it whose record changed is added at the end: it gained
    images, or a stored link was retried (#80). `now` is the run's start, for the age of a
    stored link. `sleep` defaults to `time.sleep`, looked up at the call so that tests can
    refuse it.
    """
    run = _Run(
        repository, Path(store_root), transport, clock, time.sleep if sleep is None else sleep
    )
    for record in result.lifecycles:
        run.records[record.listing_id] = record

    groups: dict[str, list[RawPost]] = {}
    for post in result.posts:
        canonical_id = post.listing_id if post.is_canonical else post.duplicate_of
        if canonical_id is None:
            raise ValueError(f"post {post.listing_id} has no dedup result")
        groups.setdefault(canonical_id, []).append(post)

    for canonical_id in sorted(groups):
        members = groups[canonical_id]
        canonical = next((post for post in members if post.is_canonical), None)
        duplicates = sorted(
            (post for post in members if not post.is_canonical),
            key=lambda post: (post.posted_at, post.listing_id),
        )
        if canonical is not None:
            # #76: every canonical with photos, whatever its state; #77 D2: what is not held.
            run.download(canonical_id, canonical, _photos(canonical))
        for duplicate in duplicates:
            run.download(canonical_id, duplicate, run.repost_photos(canonical_id, duplicate))

    # After the batch, whose links are fresh (#80 decision 2).
    run.retry_stored(
        {post.listing_id for post in result.posts}, datetime.now(UTC) if now is None else now
    )

    logger.info(
        "images: %d held, %d failed, %d not attempted; stored links: %d retried, %d held",
        run.held,
        run.failed,
        run.not_attempted,
        run.retried,
        run.retried_held,
    )
    lifecycles = tuple(run.records[record.listing_id] for record in result.lifecycles)
    added = tuple(run.records[listing_id] for listing_id in run.added)
    return DedupResult(posts=result.posts, lifecycles=lifecycles + added)


class _Run:
    def __init__(
        self,
        repository: Repository,
        store_root: Path,
        transport: ImageTransport,
        clock: Callable[[], float],
        sleep: Callable[[float], None],
    ) -> None:
        self._repository = repository
        self._store_root = store_root
        self._transport = transport
        self._clock = clock
        self._sleep = sleep
        self._started = clock()
        # The schedule ran out: each photo is tried once, without waiting, until any reply (#80 U3).
        self._network_down = False
        self.retried = self.retried_held = 0
        self.records: dict[str, PostLifecycle] = {}
        self.added: list[str] = []
        """Stored canonicals outside `dedup_a`'s result whose record changed, in order. Their final
        record is in `records`, so that every change after the first is kept too."""
        self._stored: dict[str, PostLifecycle | None] = {}
        self._held_this_run: set[str] = set()
        self.held = self.failed = self.not_attempted = 0

    def record(self, canonical_id: str) -> PostLifecycle:
        if canonical_id in self.records:
            return self.records[canonical_id]
        stored = self.stored(canonical_id)
        if stored is None:
            raise ValueError(f"canonical {canonical_id} has no lifecycle record")
        return stored

    def stored(self, listing_id: str) -> PostLifecycle | None:
        if listing_id not in self._stored:
            self._stored[listing_id] = self._repository.get_lifecycle(listing_id)
        return self._stored[listing_id]

    def repost_photos(self, canonical_id: str, duplicate: RawPost) -> list[Media]:
        """The duplicate's photos to download into the canonical's record (#72.3, #73.5, #77).

        Only while the canonical holds no image, retries included: once it holds one, a repost's
        failed photo keeps its error entry (#77 D2 for reposts).
        """
        record = self.record(canonical_id)
        photos = _photos(duplicate)
        if record.state == "archived":
            # #77 D4: a canonical still archived downloads nothing.
            return []
        before = self.stored(canonical_id)
        if before is not None and before.state == "archived":
            # #77 D4: brought back by #74 this run, so only what was downloaded this run is held.
            # The reposts that brought it back download; any other retries what it attempted
            # before.
            if canonical_id in self._held_this_run:
                return []
            brought_back = (
                self._repository.get(duplicate.listing_id) is None
                and duplicate.posted_at > before.last_published_at
            )
            return photos if brought_back else self._attempted_before(record, duplicate)
        if any(image.local_path is not None for image in record.images):
            return []
        return photos

    @staticmethod
    def _attempted_before(record: PostLifecycle, duplicate: RawPost) -> list[Media]:
        return [
            photo
            for photo in _photos(duplicate)
            if _entry(record, duplicate.listing_id, photo.media_id) is not None
        ]

    def download(self, canonical_id: str, post: RawPost, photos: list[Media]) -> None:
        """Attempt each photo not held, then retry the failures once (#63). The post's retry
        finishes before the next post is checked (#77 D3)."""
        attempted = [
            photo
            for photo in photos
            if not _is_held(self.record(canonical_id), post.listing_id, photo.media_id)
        ]
        pending = attempted
        for attempt in (1, 2):
            failed = []
            for photo in pending:
                if self._out_of_time():
                    # #77 D5b. A retry not attempted keeps the first attempt's error.
                    if attempt == 1:
                        self._set(canonical_id, _failure(post, photo, NOT_ATTEMPTED))
                    continue
                image = self._attempt(post, photo, wait=True)
                self._set(canonical_id, image)
                if image.local_path is not None:
                    self._held_this_run.add(canonical_id)
                elif not is_network_error(image.error):
                    # The one retry within a run (#63) is for other errors; a network error has
                    # had its waits instead (#80).
                    failed.append(photo)
            pending = failed
        for photo in attempted:
            entry = _entry(self.record(canonical_id), post.listing_id, photo.media_id)
            assert entry is not None
            if entry.local_path is not None:
                self.held += 1
            elif entry.error == NOT_ATTEMPTED:
                self.not_attempted += 1
            else:
                self.failed += 1
                logger.warning(
                    "image failed: listing %s media %s: %s",
                    post.listing_id,
                    photo.media_id,
                    entry.error,
                )

    def retry_stored(self, batch_ids: Collection[str], now: datetime) -> None:
        """#80 decision 2: the failed photos of stored posts, from the stored link, with no Apify
        call. One attempt each per run, never a wait (U4); the budget still applies."""
        for stored in self._repository.find_lifecycles_with_image_errors(RETRYABLE_ERRORS):
            canonical_id = stored.listing_id
            if canonical_id in batch_ids:
                continue  # the batch path retried it with a fresh link (#77 D2)
            before = self.stored(canonical_id)
            if self.record(canonical_id).state == "archived" or (
                before is not None and before.state == "archived"
            ):
                continue  # #77 D4: an archived post downloads nothing
            entries = [
                image
                for image in self.record(canonical_id).images
                if image.local_path is None
                and image.error is not None
                and image.error.startswith(RETRYABLE_ERRORS)
                and image.listing_id not in batch_ids
            ]
            for entry in entries:
                if entry.listing_id == canonical_id:
                    self._retry(canonical_id, entry, now)
            reposts = [entry for entry in entries if entry.listing_id != canonical_id]
            for entry, post in self._in_canonical_order(reposts):
                # #77 D2 for reposts: only while the canonical holds no image (U7).
                if any(image.local_path for image in self.record(canonical_id).images):
                    break
                self._retry(canonical_id, entry, now, post)

    def _in_canonical_order(self, entries: list[PostImage]) -> list[tuple[PostImage, RawPost]]:
        """#77 D3: reposts in canonical-rule order. An entry whose post is gone is skipped."""
        found = [(entry, self._repository.get(entry.listing_id)) for entry in entries]
        ordered = [(entry, post) for entry, post in found if post is not None]
        return sorted(ordered, key=lambda pair: (pair[1].posted_at, pair[1].listing_id))

    def _retry(
        self, canonical_id: str, entry: PostImage, now: datetime, post: RawPost | None = None
    ) -> None:
        if self._out_of_time():
            return  # the entry stays as it is; the next run tries again
        post = self._repository.get(entry.listing_id) if post is None else post
        if post is None or now - post.fetched_at >= STORED_LINK_MAX_AGE:
            return  # U5: the link may have expired; the entry stays
        photo = next((item for item in _photos(post) if item.media_id == entry.media_id), None)
        if photo is None:
            return  # U6: the stored post no longer has this photo; the entry is left as is
        image = self._attempt(post, photo, wait=False)
        self._set(canonical_id, image)
        self.retried += 1
        if image.local_path is not None:
            self.retried_held += 1
            self._held_this_run.add(canonical_id)
        else:
            logger.warning(
                "stored link failed: listing %s media %s: %s",
                post.listing_id,
                photo.media_id,
                image.error,
            )

    def _attempt(self, post: RawPost, photo: Media, *, wait: bool) -> PostImage:
        """One photo. A network error waits on the schedule and tries the same photo again (#80
        decision 1); any reply restarts the schedule. The waits count inside the budget, and a
        wait stops when the budget runs out (#80 §4)."""
        image = self._fetch(post, photo)
        if not is_network_error(image.error):
            self._network_down = False
            return image
        if not wait or self._network_down:
            return image
        for number, seconds in enumerate(NETWORK_WAITS_SECS, start=1):
            remaining = TIME_BUDGET_SECS - (self._clock() - self._started)
            if remaining <= 0:
                return image
            logger.warning(
                "network error (%s) on listing %s media %s: waiting %d s (%d of %d)",
                image.error,
                post.listing_id,
                photo.media_id,
                seconds,
                number,
                len(NETWORK_WAITS_SECS),
            )
            self._sleep(min(seconds, remaining))
            if self._out_of_time():
                return image
            image = self._fetch(post, photo)
            if not is_network_error(image.error):
                return image
        # U3: the rest of the run's photos are tried once each, without waiting, until any reply.
        self._network_down = True
        logger.error(
            "network still down after %d s of waiting; trying each remaining photo once",
            sum(NETWORK_WAITS_SECS),
        )
        return image

    def _out_of_time(self) -> bool:
        return self._clock() - self._started >= TIME_BUDGET_SECS

    def _fetch(self, post: RawPost, photo: Media) -> PostImage:
        try:
            response = self._transport(photo.uri)
        except ImageFetchError as error:
            return _failure(post, photo, error.reason)
        reason, extension = _judge(response)
        if reason is not None:
            return _failure(post, photo, reason)
        relative = _relative_path(post.listing_id, photo.media_id, extension)
        _write(self._store_root / relative, response.body)
        return PostImage(
            listing_id=post.listing_id, media_id=photo.media_id, local_path=relative, error=None
        )

    def _set(self, canonical_id: str, image: PostImage) -> None:
        """Replace the entry of this photo in place (#77 D2), or append it."""
        record = self.record(canonical_id)
        images = list(record.images)
        for index, existing in enumerate(images):
            if (existing.listing_id, existing.media_id) == (image.listing_id, image.media_id):
                images[index] = image
                break
        else:
            images.append(image)
        updated = PostLifecycle(**{**dict(record), "images": images})
        if canonical_id not in self.records:
            self.added.append(canonical_id)
        self.records[canonical_id] = updated


def _photos(post: RawPost) -> list[Media]:
    """Photos only (Gate E): video, reel and any other type are never downloaded."""
    return [item for item in post.media if item.type == PHOTO]


def _entry(record: PostLifecycle, listing_id: str, media_id: str) -> PostImage | None:
    return next(
        (
            image
            for image in record.images
            if image.listing_id == listing_id and image.media_id == media_id
        ),
        None,
    )


def _is_held(record: PostLifecycle, listing_id: str, media_id: str) -> bool:
    entry = _entry(record, listing_id, media_id)
    return entry is not None and entry.local_path is not None


def _failure(post: RawPost, photo: Media, reason: str) -> PostImage:
    return PostImage(
        listing_id=post.listing_id, media_id=photo.media_id, local_path=None, error=reason
    )


def _judge(response: ImageResponse) -> tuple[str | None, str]:
    """A failure reason, or None and the file extension read from the bytes."""
    if response.status != 200:
        return f"http {response.status}", ""
    content_type = (response.content_type or "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        return f"not an image: {content_type or 'no content type'}", ""
    if not response.body:
        return "empty body", ""
    extension = _extension(response.body)
    if extension is None:
        return "unrecognized bytes", ""
    return None, extension


def _extension(body: bytes) -> str | None:
    # The link's own extension says nothing: `.png` and `.webp` links served JPEG in the
    # 2026-10-04 check (ASSUMPTIONS.md I9).
    if body.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "webp"
    return None


def _relative_path(listing_id: str, media_id: str, extension: str) -> str:
    """#77 D1: relative to `store_root`, with "/". A `media_id` can hold ":", so it is hashed."""
    name = hashlib.sha256(media_id.encode("utf-8")).hexdigest()[:16]
    return f"{IMAGES_DIR}/{listing_id}/{name}.{extension}"


def _write(path: Path, body: bytes) -> None:
    """Written under a temporary name and renamed: a crash never leaves half a file in place."""
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(body)
        os.replace(temporary, path)
    except OSError as error:
        raise ImageWriteError(f"cannot write {path}: {error.strerror or error}") from error
