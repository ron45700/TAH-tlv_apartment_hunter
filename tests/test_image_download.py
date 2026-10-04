"""Task 1.12: photo download (DECISIONS.md #63, #70, #72.3, #73.5, #76, #77). Every test that
reads history runs against local_json and SQLite (make_repository). No network: a fake transport,
and the socket guard in conftest."""

import hashlib
import urllib.error
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FETCHED_AT, load_spike_1_1a
from tlv_hunter.contracts.post_lifecycle import PostImage, PostLifecycle
from tlv_hunter.contracts.raw_post import Media, RawPost
from tlv_hunter.dedup.stage_a import DedupResult, dedup_a
from tlv_hunter.images import download
from tlv_hunter.images.download import (
    NOT_ATTEMPTED,
    TIME_BUDGET_SECS,
    ImageFetchError,
    ImageResponse,
    ImageWriteError,
    download_images,
    urllib_image_transport,
)
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.store.base import Repository
from tlv_hunter.textnorm.annotate import annotate

MakeRepository = Callable[[], Repository]
JPEG = b"\xff\xd8\xff\xe0" + b"jpeg body"
PNG = b"\x89PNG\r\n\x1a\n" + b"png body"
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"webp body"
OK = ImageResponse(200, "image/jpeg", JPEG)
FLAG = {"flagged_by": "ron", "flagged_at": datetime(2026, 10, 4, 9, 0, tzinfo=UTC)}


def _media(media_id: str, kind: str = "Photo") -> Media:
    return Media(
        type=kind,
        uri=f"https://img.invalid/{media_id}",
        width=None,
        height=None,
        media_id=media_id,
        page_url=f"https://www.facebook.com/photo/?fbid={media_id}",
    )


class FakeTransport:
    """Answers per media id, in order; the last answer repeats. Records every call."""

    def __init__(self, answers: dict[str, list[Any]] | None = None, on_call=None) -> None:
        self.answers = answers or {}
        self.calls: list[str] = []
        self.on_call = on_call

    def __call__(self, url: str) -> ImageResponse:
        media_id = url.rsplit("/", 1)[1]
        self.calls.append(media_id)
        if self.on_call is not None:
            self.on_call()
        queue = self.answers.get(media_id, [OK])
        answer = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


@pytest.fixture
def repo(make_repository: MakeRepository) -> Repository:
    return make_repository()


@pytest.fixture
def base(posts: list[RawPost]) -> RawPost:
    """A post with its own text; every test post below is a copy of it."""
    return next(p for p in posts if p.text_source == "text" and not p.no_text)


def _post(base: RawPost, source_post_id: str, media: list[Media], minutes: int = 0) -> RawPost:
    """Another Facebook post with the base's text: a repost of every other `_post`."""
    return base.with_changes(
        source_post_id=source_post_id,
        listing_id=compute_listing_id(source_post_id),
        media=media,
        posted_at=base.posted_at + timedelta(minutes=minutes),
    )


def _seed(repo: Repository, post: RawPost, **lifecycle: Any) -> RawPost:
    """Store a canonical as an earlier run would have, with the given record fields."""
    stored = post.with_changes(is_canonical=True, duplicate_of=None)
    record = PostLifecycle(**{**dict(initial_lifecycle(stored)), **lifecycle})
    repo.upsert_with_lifecycle(stored, record)
    return stored


def _held(listing_id: str, media_id: str) -> PostImage:
    return PostImage(
        listing_id=listing_id,
        media_id=media_id,
        local_path=f"images/{listing_id}/x.jpg",
        error=None,
    )


def _failed(listing_id: str, media_id: str, error: str = "http 500") -> PostImage:
    return PostImage(listing_id=listing_id, media_id=media_id, local_path=None, error=error)


def _run(
    repo: Repository, batch: list[RawPost], root: Path, transport: FakeTransport, **kwargs: Any
) -> DedupResult:
    return download_images(dedup_a(batch, repo), repo, root, transport, **kwargs)


def _record(result: DedupResult, post: RawPost) -> PostLifecycle:
    return next(r for r in result.lifecycles if r.listing_id == post.listing_id)


def _outcomes(record: PostLifecycle) -> list[tuple[str, str, bool]]:
    return [(i.listing_id, i.media_id, i.local_path is not None) for i in record.images]


# --- which photos: canonicals (#76) ---


def test_photos_only(repo, base, tmp_path) -> None:
    post = _post(base, "1", [_media("p1"), _media("v1", "Video"), _media("r1", "Reel")])
    transport = FakeTransport()
    result = _run(repo, [post], tmp_path, transport)
    assert transport.calls == ["p1"]
    assert _outcomes(_record(result, post)) == [(post.listing_id, "p1", True)]


def test_a_pending_canonical_downloads_its_photos(repo, base, tmp_path) -> None:
    post = _post(base, "1", [_media("p1"), _media("p2")])
    result = _run(repo, [post], tmp_path, FakeTransport())
    record = _record(result, post)
    assert record.state == "pending"
    assert _outcomes(record) == [(post.listing_id, "p1", True), (post.listing_id, "p2", True)]


def test_a_no_text_canonical_downloads_its_photos(repo, base, tmp_path) -> None:
    empty = annotate(
        _post(base, "1", [_media("p1")]).with_changes(
            text="", text_source="none", no_text=None, text_hash=None, phones=None
        )
    )
    result = _run(repo, [empty], tmp_path, FakeTransport())
    record = _record(result, empty)
    assert (record.state, record.rejection_reason) == ("rejected", "no_text")
    assert _outcomes(record) == [(empty.listing_id, "p1", True)]


@pytest.mark.parametrize(
    ("reason", "flag"), [("other_city", {}), ("not_listing", {}), ("flagged", FLAG)]
)
def test_a_canonical_with_a_verdict_downloads_its_photos(
    repo, base, tmp_path, reason, flag
) -> None:
    post = _post(base, "1", [_media("p1")])
    _seed(repo, post, state="rejected", rejection_reason=reason, **flag)
    result = _run(repo, [post], tmp_path, FakeTransport())
    record = _record(result, post)
    assert (record.state, record.rejection_reason) == ("rejected", reason)
    assert _outcomes(record) == [(post.listing_id, "p1", True)]


def test_a_canonical_without_photos_downloads_nothing(repo, base, tmp_path) -> None:
    post = _post(base, "1", [])
    transport = FakeTransport()
    result = _run(repo, [post], tmp_path, transport)
    assert transport.calls == []
    assert _record(result, post).images == []


# --- which photos: duplicates (#70, #72.3, #72.4, #73.5) ---


def test_a_repost_downloads_nothing_while_the_canonical_holds_a_photo(repo, base, tmp_path) -> None:
    canonical = _seed(repo, _post(base, "1", [_media("c1")]))
    repo.save_lifecycle(
        repo.get_lifecycle(canonical.listing_id).model_copy(
            update={"images": [_held(canonical.listing_id, "c1")]}
        )
    )
    repost = _post(base, "2", [_media("r1")], minutes=10)
    transport = FakeTransport()
    result = _run(repo, [repost], tmp_path, transport)
    assert transport.calls == []
    assert _record(result, canonical).images == [_held(canonical.listing_id, "c1")]


def test_a_repost_downloads_into_the_canonical_record_when_it_holds_nothing(
    repo, base, tmp_path
) -> None:
    canonical = _seed(repo, _post(base, "1", []))
    repost = _post(base, "2", [_media("r1"), _media("v1", "Video")], minutes=10)
    result = _run(repo, [repost], tmp_path, FakeTransport())
    record = _record(result, canonical)
    assert record.state == "pending"  # #70
    assert _outcomes(record) == [(repost.listing_id, "r1", True)]
    assert _record(result, repost).images == []


def test_an_image_held_from_an_earlier_repost_counts(repo, base, tmp_path) -> None:
    """#73.5: what we hold includes a photo that came through an earlier repost."""
    canonical = _seed(repo, _post(base, "1", []))
    earlier = _post(base, "2", [_media("e1")], minutes=5)
    repo.save_lifecycle(
        repo.get_lifecycle(canonical.listing_id).model_copy(
            update={
                "state": "pending",
                "rejection_reason": None,
                "images": [_held(earlier.listing_id, "e1")],
            }
        )
    )
    transport = FakeTransport()
    _run(repo, [_post(base, "3", [_media("r1")], minutes=10)], tmp_path, transport)
    assert transport.calls == []


def test_a_video_only_repost_downloads_nothing(repo, base, tmp_path) -> None:
    """#72.4: the canonical returns to pending, and nothing is downloaded."""
    canonical = _seed(repo, _post(base, "1", []))
    transport = FakeTransport()
    result = _run(repo, [_post(base, "2", [_media("v1", "Video")], 10)], tmp_path, transport)
    assert transport.calls == []
    assert _record(result, canonical).state == "pending"
    assert _record(result, canonical).images == []


def test_a_stored_canonical_outside_the_result_is_returned_at_the_end(repo, base, tmp_path) -> None:
    """A late, older duplicate leaves the canonical's record unchanged in dedup_a's result; the
    record that gains images is read from the repository and added at the end."""
    canonical = _seed(repo, _post(base, "1", [_media("c1")], minutes=60))
    repo.save_lifecycle(
        repo.get_lifecycle(canonical.listing_id).model_copy(
            update={"images": [_failed(canonical.listing_id, "c1")]}
        )
    )
    late = _post(base, "2", [_media("r1")], minutes=0)
    deduped = dedup_a([late], repo)
    assert [r.listing_id for r in deduped.lifecycles] == [late.listing_id]
    transport = FakeTransport()
    result = download_images(deduped, repo, tmp_path, transport)
    assert transport.calls == ["r1"]  # the canonical is not in the batch: c1 is not retried
    assert [r.listing_id for r in result.lifecycles] == [late.listing_id, canonical.listing_id]
    assert _outcomes(result.lifecycles[-1]) == [
        (canonical.listing_id, "c1", False),
        (late.listing_id, "r1", True),
    ]


def test_every_change_to_a_stored_canonical_outside_the_result_is_kept(
    repo, base, tmp_path
) -> None:
    """Regression, found building #80: only the first photo recorded into such a record was
    returned; the second was lost."""
    canonical = _seed(repo, _post(base, "1", [_media("c1")], minutes=60))
    repo.save_lifecycle(
        repo.get_lifecycle(canonical.listing_id).model_copy(
            update={"images": [_failed(canonical.listing_id, "c1")]}
        )
    )
    late = _post(base, "2", [_media("r1"), _media("r2")], minutes=0)
    result = download_images(dedup_a([late], repo), repo, tmp_path, FakeTransport())
    assert [r.listing_id for r in result.lifecycles] == [late.listing_id, canonical.listing_id]
    assert _outcomes(result.lifecycles[-1]) == [
        (canonical.listing_id, "c1", False),
        (late.listing_id, "r1", True),
        (late.listing_id, "r2", True),
    ]


# --- #77 D1: where the files live ---


@pytest.mark.parametrize(("body", "extension"), [(JPEG, "jpg"), (PNG, "png"), (WEBP, "webp")])
def test_files_live_under_store_root_by_listing_and_hashed_media_id(
    repo, base, tmp_path, body, extension
) -> None:
    media_id = "GenericAttachmentMedia:EntityID:1478726540741964"
    post = _post(base, "1", [_media(media_id)])
    transport = FakeTransport({media_id: [ImageResponse(200, "image/jpeg", body)]})
    result = _run(repo, [post], tmp_path, transport)
    name = hashlib.sha256(media_id.encode()).hexdigest()[:16]
    expected = f"images/{post.listing_id}/{name}.{extension}"
    assert _record(result, post).images[0].local_path == expected
    assert (tmp_path / expected).read_bytes() == body
    assert not list(tmp_path.rglob("*.tmp"))


def test_a_second_download_overwrites_the_same_file(repo, base, tmp_path) -> None:
    """A run that fails before the store step leaves files; the next run writes the same paths."""
    post = _post(base, "1", [_media("p1")])
    deduped = dedup_a([post], repo)
    first = download_images(deduped, repo, tmp_path, FakeTransport())
    second = download_images(deduped, repo, tmp_path, FakeTransport())
    assert first == second
    assert len([p for p in (tmp_path / "images").rglob("*") if p.is_file()]) == 1


# --- one retry within the run (#63), failures recorded, nothing else fails ---


def test_a_failure_then_success_gives_one_held_entry(repo, base, tmp_path) -> None:
    post = _post(base, "1", [_media("p1")])
    transport = FakeTransport({"p1": [ImageResponse(503, None, b""), OK]})
    result = _run(repo, [post], tmp_path, transport)
    assert transport.calls == ["p1", "p1"]
    assert _outcomes(_record(result, post)) == [(post.listing_id, "p1", True)]


@pytest.mark.parametrize(
    ("answer", "error"),
    [
        (ImageResponse(404, "text/html", b""), "http 404"),
        (ImageResponse(200, "text/html; charset=utf-8", b"<html>"), "not an image: text/html"),
        (ImageResponse(200, None, JPEG), "not an image: no content type"),
        (ImageResponse(200, "image/jpeg", b""), "empty body"),
        (ImageResponse(200, "image/jpeg", b"GIF89a..."), "unrecognized bytes"),
        (ImageFetchError("too large"), "too large"),
    ],
)
def test_two_failures_are_recorded_and_fail_nothing(repo, base, tmp_path, answer, error) -> None:
    # Errors that are not network-type: the one retry within the run, and never a wait. A network
    # error or a timeout waits instead (DECISIONS.md #80, tests/test_image_network.py).
    post = _post(base, "1", [_media("bad"), _media("good")])
    transport = FakeTransport({"bad": [answer]})
    slept: list[float] = []
    result = _run(repo, [post], tmp_path, transport, sleep=slept.append)
    assert transport.calls == ["bad", "good", "bad"]
    assert slept == []
    record = _record(result, post)
    assert record.images[0] == _failed(post.listing_id, "bad", error)
    assert record.images[1].local_path is not None


def test_posts_are_returned_unchanged(repo, base, tmp_path) -> None:
    deduped = dedup_a([_post(base, "1", [_media("p1")])], repo)
    assert download_images(deduped, repo, tmp_path, FakeTransport()).posts is deduped.posts


# --- #77 D2: retry on a later run ---


def test_a_refetched_canonical_retries_what_is_not_held_in_place(repo, base, tmp_path) -> None:
    post = _post(base, "1", [_media("p1"), _media("p2")])
    _seed(repo, post, images=[_failed(post.listing_id, "p1"), _held(post.listing_id, "p2")])
    transport = FakeTransport()
    result = _run(repo, [post], tmp_path, transport)
    assert transport.calls == ["p1"]
    assert _outcomes(_record(result, post)) == [
        (post.listing_id, "p1", True),
        (post.listing_id, "p2", True),
    ]


@pytest.mark.parametrize(
    ("r1_held", "calls", "r2_held"),
    [
        # The canonical holds an image (r1): r2 keeps its error entry, not attempted again.
        (True, [], False),
        # The canonical holds nothing: the repost's failed photos are attempted again.
        (False, ["r1", "r2"], True),
    ],
)
def test_a_refetched_repost_retries_only_while_the_canonical_holds_nothing(
    repo, base, tmp_path, r1_held, calls, r2_held
) -> None:
    canonical = _seed(repo, _post(base, "1", []))
    repost = _post(base, "2", [_media("r1"), _media("r2")], minutes=10)
    repo.upsert(repost.with_changes(is_canonical=False, duplicate_of=canonical.listing_id))
    repo.save_lifecycle(initial_lifecycle(repost))
    r1 = _held(repost.listing_id, "r1") if r1_held else _failed(repost.listing_id, "r1")
    repo.save_lifecycle(
        repo.get_lifecycle(canonical.listing_id).model_copy(
            update={
                "state": "pending",
                "rejection_reason": None,
                "images": [r1, _failed(repost.listing_id, "r2")],
            }
        )
    )
    transport = FakeTransport()
    result = _run(repo, [repost], tmp_path, transport)
    assert transport.calls == calls
    record = next(
        (r for r in result.lifecycles if r.listing_id == canonical.listing_id),
        repo.get_lifecycle(canonical.listing_id),
    )
    assert _outcomes(record) == [
        (repost.listing_id, "r1", True),
        (repost.listing_id, "r2", r2_held),
    ]
    if not r2_held:
        assert record.images[1] == _failed(repost.listing_id, "r2")


# --- #77 D3: canonical and reposts new in the same run ---


def test_a_canonical_that_holds_after_its_retry_stops_its_reposts(repo, base, tmp_path) -> None:
    canonical = _post(base, "1", [_media("c1")])
    reposts = [_post(base, "2", [_media("r1")], 10), _post(base, "3", [_media("s1")], 20)]
    transport = FakeTransport({"c1": [ImageResponse(500, None, b""), OK]})
    result = _run(repo, [*reposts, canonical], tmp_path, transport)
    assert transport.calls == ["c1", "c1"]
    assert _outcomes(_record(result, canonical)) == [(canonical.listing_id, "c1", True)]


def test_when_the_canonical_fails_the_earliest_repost_downloads(repo, base, tmp_path) -> None:
    canonical = _post(base, "1", [_media("c1")])
    later = _post(base, "2", [_media("s1")], 20)
    earlier = _post(base, "3", [_media("r1")], 10)
    transport = FakeTransport({"c1": [ImageResponse(500, None, b"")]})
    result = _run(repo, [later, canonical, earlier], tmp_path, transport)
    assert transport.calls == ["c1", "c1", "r1"]
    assert _outcomes(_record(result, canonical)) == [
        (canonical.listing_id, "c1", False),
        (earlier.listing_id, "r1", True),
    ]


# --- #77 D4: a canonical archived before #74 ---


def test_the_repost_that_brings_an_archived_post_back_downloads(repo, base, tmp_path) -> None:
    """Read before #74: the stored record was archived. An entry left from before archive does
    not count as held."""
    canonical = _post(base, "1", [_media("c1")])
    _seed(repo, canonical, state="archived", images=[_held(canonical.listing_id, "c1")])
    first = _post(base, "2", [_media("r1")], 10)
    second = _post(base, "3", [_media("s1")], 20)
    transport = FakeTransport()
    result = _run(repo, [second, first], tmp_path, transport)
    record = _record(result, canonical)
    assert record.state == "pending"
    assert transport.calls == ["r1"]
    assert _outcomes(record)[-1] == (first.listing_id, "r1", True)


def test_a_canonical_still_archived_downloads_nothing(repo, base, tmp_path) -> None:
    canonical = _post(base, "1", [_media("c1")], minutes=60)
    _seed(repo, canonical, state="archived")
    older = _post(base, "2", [_media("r1")], minutes=0)  # #75 E2: does not bring it back
    transport = FakeTransport()
    result = _run(repo, [older], tmp_path, transport)
    assert transport.calls == []
    assert all(
        r.state == "archived" for r in result.lifecycles if r.listing_id == canonical.listing_id
    )


# --- #77 D5a: a disk write error fails the run ---


def test_a_disk_write_error_raises(repo, base, tmp_path) -> None:
    store_root = tmp_path / "store"
    store_root.write_text("a file where the store directory should be")
    with pytest.raises(ImageWriteError):
        _run(repo, [_post(base, "1", [_media("p1")])], store_root, FakeTransport())


# --- #77 D5b: the time budget ---


def test_photos_past_the_time_budget_are_not_attempted(repo, base, tmp_path) -> None:
    now = [0.0]

    def tick() -> None:
        now[0] += TIME_BUDGET_SECS / 2

    post = _post(base, "1", [_media("p1"), _media("p2"), _media("p3")])
    transport = FakeTransport(on_call=tick)
    result = _run(repo, [post], tmp_path, transport, clock=lambda: now[0])
    assert transport.calls == ["p1", "p2"]
    assert _record(result, post).images[2] == _failed(post.listing_id, "p3", NOT_ATTEMPTED)


def test_a_retry_past_the_time_budget_keeps_the_first_error(repo, base, tmp_path) -> None:
    now = [0.0]

    def tick() -> None:
        now[0] += TIME_BUDGET_SECS

    post = _post(base, "1", [_media("p1")])
    transport = FakeTransport({"p1": [ImageResponse(500, None, b"")]}, on_call=tick)
    result = _run(repo, [post], tmp_path, transport, clock=lambda: now[0])
    assert transport.calls == ["p1"]
    assert _record(result, post).images == [_failed(post.listing_id, "p1", "http 500")]


# --- #77 D5c: the urllib transport ---


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str = "image/jpeg") -> None:
        self._body = body
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self, size: int) -> bytes:
        chunk, self._body = self._body[:size], self._body[size:]
        return chunk

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def test_the_transport_sends_the_spike_user_agent(monkeypatch) -> None:
    seen = []

    def urlopen(request, timeout):
        seen.append((request.get_header("User-agent"), request.get_header("Cookie"), timeout))
        return _FakeResponse(JPEG)

    monkeypatch.setattr(download.urllib.request, "urlopen", urlopen)
    response = urllib_image_transport("https://img.invalid/p1")
    assert response == ImageResponse(200, "image/jpeg", JPEG)
    assert seen == [("Mozilla/5.0", None, download.SOCKET_TIMEOUT_SECS)]


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (urllib.error.URLError(TimeoutError()), "timeout"),
        (TimeoutError(), "timeout"),
        (urllib.error.URLError(ConnectionRefusedError()), "network: ConnectionRefusedError"),
        (ConnectionResetError(), "network: ConnectionResetError"),
    ],
)
def test_the_transport_maps_network_errors(monkeypatch, raised, expected) -> None:
    def urlopen(request, timeout):
        raise raised

    monkeypatch.setattr(download.urllib.request, "urlopen", urlopen)
    with pytest.raises(ImageFetchError) as error:
        urllib_image_transport("https://img.invalid/p1")
    assert error.value.reason == expected


def test_the_transport_returns_an_http_error_as_a_status(monkeypatch) -> None:
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", Message(), None)

    monkeypatch.setattr(download.urllib.request, "urlopen", urlopen)
    assert urllib_image_transport("https://img.invalid/p1").status == 403


def test_the_transport_stops_an_oversize_body(monkeypatch) -> None:
    monkeypatch.setattr(download, "MAX_IMAGE_BYTES", 10)
    monkeypatch.setattr(
        download.urllib.request, "urlopen", lambda r, timeout: _FakeResponse(JPEG * 4)
    )
    with pytest.raises(ImageFetchError) as error:
        urllib_image_transport("https://img.invalid/p1")
    assert error.value.reason == "too large"


# --- #77 D5d: entries already held are kept ---


def test_a_post_that_lost_a_photo_keeps_its_entry(repo, base, tmp_path) -> None:
    post = _post(base, "1", [_media("p2")])
    other = _post(base, "9", [_media("x1")], 5)
    _seed(repo, post, images=[_held(other.listing_id, "x1"), _held(post.listing_id, "p1")])
    result = _run(repo, [post], tmp_path, FakeTransport())
    assert _outcomes(_record(result, post)) == [
        (other.listing_id, "x1", True),
        (post.listing_id, "p1", True),
        (post.listing_id, "p2", True),
    ]


# --- the spike data ---


def test_spike_main_downloads_every_canonical_photo(repo, tmp_path) -> None:
    batch = [annotate(to_raw_post(item, FETCHED_AT)) for item in load_spike_1_1a()]
    transport = FakeTransport()
    result = _run(repo, batch, tmp_path, transport)
    by_id = {post.listing_id: post for post in result.posts}
    records = {record.listing_id: record for record in result.lifecycles}
    canonical_photos = 0
    for post in result.posts:
        photos = [m.media_id for m in post.media if m.type == "Photo"]
        if post.is_canonical:
            canonical_photos += len(photos)
            own = [
                i.media_id
                for i in records[post.listing_id].images
                if i.listing_id == post.listing_id
            ]
            assert own == photos
        else:
            assert records[post.listing_id].images == []
    entries = [image for record in records.values() for image in record.images]
    assert all(image.local_path is not None for image in entries)
    assert len(entries) == len(transport.calls) >= canonical_photos > 0
    # A repost downloads only into a canonical that has no photo of its own.
    for image in entries:
        post = by_id[image.listing_id]
        if not post.is_canonical:
            assert not [m for m in by_id[post.duplicate_of].media if m.type == "Photo"]
