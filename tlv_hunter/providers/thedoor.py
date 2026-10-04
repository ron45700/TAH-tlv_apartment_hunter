import copy
import json
import logging
import math
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from pydantic import ValidationError

from tlv_hunter.config.base import CollectionConfig
from tlv_hunter.contracts.raw_post import RAW_POST_SCHEMA_VERSION, Media, RawPost
from tlv_hunter.parsing.datetimes import parse_rfc2822_utc, require_utc
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.parsing.prices import UNPARSED_PRICE, parse_native_price
from tlv_hunter.textnorm.blank import is_blank

SOURCE = "thedoor"
ACTOR_ID = "thedoor~facebook-group-post-scraper"
API_BASE = "https://api.apify.com/v2"

# The API's maximum for waitForFinish on GET /actor-runs/{runId}.
POLL_WAIT_SECS = 60
# Allowance on top of the server-side wait before the HTTP client gives up.
HTTP_SLACK_SECS = 30
# ActorJobStatus values that are not final (Apify API spec v2-2026-10-01).
TRANSITIONAL_STATUSES = frozenset({"READY", "RUNNING", "TIMING-OUT", "ABORTING"})
# Skipped rows fail the run when they are more than half of the rows considered and at least this
# many: a changed response shape must not pass as an empty success (DECISIONS.md #71 D).
MIN_SKIPPED_TO_FAIL = 3

logger = logging.getLogger(__name__)


class ApifyApiError(RuntimeError):
    """An Apify API call answered with an HTTP error."""


class ProviderRunError(RuntimeError):
    """The run cannot be trusted as complete; nothing it returned may advance a watermark."""


class Transport(Protocol):
    def __call__(
        self, method: str, url: str, *, token: str, body: dict[str, Any] | None, timeout: float
    ) -> Any: ...


def urllib_transport(
    method: str, url: str, *, token: str, body: dict[str, Any] | None, timeout: float
) -> Any:
    """One JSON call to the Apify API. The token travels only in the Authorization header."""
    headers = {"Authorization": f"Bearer {token}"}
    if body is None:
        data = b"" if method == "POST" else None
    else:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        path = urllib.parse.urlsplit(url).path
        raise ApifyApiError(f"{method} {path} -> HTTP {error.code}") from None


def posts_newer_than(since: datetime, now: datetime) -> str:
    """`postsNewerThan` as relative minutes (DECISIONS.md #36), rounded up to cover `since`."""
    seconds = (require_utc(now) - require_utc(since)).total_seconds()
    if seconds <= 0:
        raise ValueError(f"since {since.isoformat()} is not before now {now.isoformat()}")
    return f"{math.ceil(seconds / 60)} minutes"


def build_actor_input(
    config: CollectionConfig, group_ids: Sequence[str], since: datetime, now: datetime
) -> dict[str, Any]:
    if not group_ids:
        raise ValueError("group_ids is empty")
    if len(set(group_ids)) != len(group_ids):
        raise ValueError("group_ids contains duplicates")
    return {
        "url": [f"https://www.facebook.com/groups/{group_id}/" for group_id in group_ids],
        "maxPosts": config.max_posts,
        "sortingOrder": config.sorting_order,
        "fetchAllComments": config.fetch_all_comments,
        "includeTopComment": config.include_top_comment,
        "postsNewerThan": posts_newer_than(since, now),
    }


class ThedoorProvider:
    """One regular (non-sync) actor run for all groups (DECISIONS.md #20, #71)."""

    def __init__(
        self,
        config: CollectionConfig,
        token: str,
        transport: Transport = urllib_transport,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not token:
            raise ValueError("Apify token is empty")
        self._config = config
        self._token = token
        self._transport = transport
        self._clock = clock

    def fetch(self, group_ids: Sequence[str], since: datetime) -> list[RawPost]:
        started = self._clock()
        run_input = build_actor_input(self._config, group_ids, since, started)
        query = urllib.parse.urlencode({"maxTotalChargeUsd": self._config.max_total_charge_usd})
        run = self._call("POST", f"/actors/{ACTOR_ID}/runs?{query}", body=run_input)["data"]
        run = self._wait(run, deadline=started + timedelta(seconds=self._config.run_timeout_secs))
        run_id = run["id"]
        if run["status"] != "SUCCEEDED":
            raise ProviderRunError(f"apify_run {run_id} ended {run['status']}")

        items = self._call("GET", f"/datasets/{run['defaultDatasetId']}/items?format=json")
        max_items = run["options"]["maxItems"]
        if len(items) >= max_items:
            raise ProviderRunError(
                f"apify_run {run_id} returned {len(items)} rows, at the charge cap's maxItems "
                f"{max_items}; the dataset may be cut off"
            )
        return self._to_posts(run, items, group_ids, since)

    def _wait(self, run: dict[str, Any], deadline: datetime) -> dict[str, Any]:
        while run["status"] in TRANSITIONAL_STATUSES:
            remaining = (deadline - self._clock()).total_seconds()
            if remaining <= 0:
                self._abort(run["id"])
                raise ProviderRunError(
                    f"apify_run {run['id']} still {run['status']} after "
                    f"{self._config.run_timeout_secs}s; aborted"
                )
            wait = min(POLL_WAIT_SECS, math.ceil(remaining))
            run = self._call("GET", f"/actor-runs/{run['id']}?waitForFinish={wait}")["data"]
        return run

    def _abort(self, run_id: str) -> None:
        try:
            self._call("POST", f"/actor-runs/{run_id}/abort")
        except (ApifyApiError, OSError) as error:
            # The run is failed either way; a failed abort only means it may keep billing.
            logger.error("apify_run %s: abort failed: %s", run_id, error)

    def _to_posts(
        self,
        run: dict[str, Any],
        items: list[Any],
        group_ids: Sequence[str],
        since: datetime,
    ) -> list[RawPost]:
        run_id = run["id"]
        requested = set(group_ids)
        rows_per_group = Counter({group_id: 0 for group_id in group_ids})
        fetched_at = self._clock()
        mapped: list[RawPost] = []
        skipped = dropped = 0
        for item in items:
            group_id = item.get("group_id") if isinstance(item, dict) else None
            post_id = item.get("post_id") if isinstance(item, dict) else None
            if isinstance(group_id, str) and group_id not in requested:
                logger.warning(
                    "apify_run %s: dropped post_id %s from group %s, which was not requested",
                    run_id,
                    post_id,
                    group_id,
                )
                dropped += 1
                continue
            if isinstance(group_id, str):
                rows_per_group[group_id] += 1
            try:
                mapped.append(to_raw_post(item, fetched_at))
            except Exception as error:  # one broken row must not block every group's window
                logger.error(
                    "apify_run %s: skipped post_id %s in group %s: %s",
                    run_id,
                    post_id,
                    group_id,
                    _describe(error),
                )
                skipped += 1

        considered = len(items) - dropped
        if skipped >= MIN_SKIPPED_TO_FAIL and skipped * 2 > considered:
            raise ProviderRunError(
                f"apify_run {run_id}: {skipped} of {considered} rows failed to map; "
                "the response shape may have changed"
            )

        for group_id in group_ids:
            if rows_per_group[group_id] >= self._config.max_posts:
                logger.warning(
                    "apify_run %s: group %s returned %d rows, at or above max_posts (%d); "
                    "its window may be cut off",
                    run_id,
                    group_id,
                    rows_per_group[group_id],
                    self._config.max_posts,
                )

        posts = [post for post in mapped if post.posted_at >= since]
        logger.info(
            "apify_run %s: %s, %d rows, per group %s, mapped %d, skipped %d, dropped %d, "
            "kept %d since %s, usageTotalUsd %s",
            run_id,
            run["status"],
            len(items),
            dict(rows_per_group),
            len(mapped),
            skipped,
            dropped,
            len(posts),
            since.isoformat(),
            run.get("usageTotalUsd"),
        )
        return posts

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        return self._transport(
            method,
            f"{API_BASE}{path}",
            token=self._token,
            body=body,
            timeout=POLL_WAIT_SECS + HTTP_SLACK_SECS,
        )


def _describe(error: Exception) -> str:
    """The failure without the row's content: no post text or phone numbers reach the log."""
    if isinstance(error, ValidationError):
        details = (
            f"{'.'.join(str(part) for part in entry['loc']) or '<post>'}: {entry['type']}"
            for entry in error.errors(include_input=False, include_url=False)
        )
        return f"ValidationError ({'; '.join(details)})"
    if isinstance(error, KeyError):
        return f"KeyError (missing key {error.args[0]!r})"
    return type(error).__name__


def to_raw_post(item: dict[str, Any], fetched_at: datetime) -> RawPost:
    # A shared post is detected by sharedPost being present, never by post_type (Gate A amendment).
    shared = item["sharedPost"]
    own_text = item["text"]
    if not is_blank(own_text):
        text, text_source = own_text, "text"
    elif shared is not None and not is_blank(shared["text"]):
        text, text_source = shared["text"], "shared_post"
    else:
        text, text_source = own_text, "none"
    media_items = item["media"]
    if not media_items and shared is not None:
        media_items = shared["media"]

    sale_post = item["sale_post"]
    if sale_post is None:
        price_raw = title = location = None
        price = UNPARSED_PRICE
    else:
        price_raw = sale_post["price"]
        price = parse_native_price(price_raw)
        title = sale_post["title"]
        location = sale_post["location"]

    user = item["user"]
    return RawPost(
        schema_version=RAW_POST_SCHEMA_VERSION,
        source=SOURCE,
        source_post_id=item["post_id"],
        listing_id=compute_listing_id(item["post_id"]),
        group_id=item["group_id"],
        group_title=None,
        permalink=item["post_url"],
        posted_at=parse_rfc2822_utc(item["creation_time"]),
        fetched_at=fetched_at,
        raw=copy.deepcopy(item),
        text=text,
        text_source=text_source,
        post_type=item["post_type"],
        media=[_to_media(entry) for entry in media_items],
        native_price=price.amount,
        native_price_raw=price_raw,
        native_currency=price.currency,
        native_title=title,
        native_location=location,
        author_name=user["name"],
        author_id_raw=user["id"],
        author_profile_url=user["profileUrl"],
        top_comment=copy.deepcopy(item["topComment"]),
        reactions_count=item["reactions_count"],
        comments_count=item["comments_count"],
        shares_count=item["shares_count"],
    )


def _to_media(entry: dict[str, Any]) -> Media:
    # Own and shared media alike: Video items, and some Photo items, omit width/height entirely.
    return Media(
        type=entry["type"],
        uri=entry["uri"],
        width=entry.get("width"),
        height=entry.get("height"),
        media_id=entry["id"],
        page_url=entry["url"],
    )
