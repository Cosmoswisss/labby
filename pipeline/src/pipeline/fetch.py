"""Polite HTTP fetching: per-host rate limit, robots.txt, retries and a disk cache.

Every network access of the pipeline goes through `Fetcher.fetch`, so the crawling
rules (robots.txt, ~1 request/second per host, explicit User-Agent, never re-download
needlessly) are enforced in a single place.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import truststore

from pipeline import tls
from pipeline.config import USER_AGENT

MAX_BODY_BYTES = 20 * 1024 * 1024
RETRY_STATUSES = {429, 500, 502, 503, 504}


def now_utc() -> datetime:
    return datetime.now(UTC)


def host_of(url: str) -> str:
    return urlsplit(url).netloc.lower()


class RateLimiter:
    """Ensures at least `min_interval` seconds between two requests to the same host."""

    def __init__(
        self,
        min_interval: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            delay = self.min_interval - (self._clock() - last)
            if delay > 0:
                self._sleep(delay)
        self._last[host] = self._clock()


@dataclass
class FetchResult:
    url: str
    final_url: str | None = None
    status: int | None = None
    content_type: str | None = None
    body: bytes = b""
    fetched_at: str | None = None
    from_cache: bool = False
    error: str | None = None  # network error, robots disallow, not cached in offline mode…
    robots_disallowed: bool = False
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and 200 <= self.status < 300

    @property
    def is_pdf(self) -> bool:
        ctype = (self.content_type or "").lower()
        return "application/pdf" in ctype or self.body[:5] == b"%PDF-"


class DiskCache:
    """Stores the raw body and metadata of every successful download."""

    def __init__(self, root: Path) -> None:
        self.root = root / "raw"

    @staticmethod
    def key(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]

    def _paths(self, url: str) -> tuple[Path, Path]:
        k = self.key(url)
        return self.root / f"{k}.body", self.root / f"{k}.json"

    def get(self, url: str) -> FetchResult | None:
        body_path, meta_path = self._paths(url)
        if not (body_path.exists() and meta_path.exists()):
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.pop("body", None)
        result = FetchResult(**meta)
        result.body = body_path.read_bytes()
        result.from_cache = True
        return result

    def put(self, result: FetchResult) -> None:
        body_path, meta_path = self._paths(result.url)
        self.root.mkdir(parents=True, exist_ok=True)
        body_path.write_bytes(result.body)
        meta = asdict(result)
        meta.pop("body")
        meta["from_cache"] = False
        meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")


class Fetcher:
    """Fetches URLs while respecting the crawling rules.

    - `offline=True`: only the disk cache is used (development, tests).
    - A cached copy younger than `max_age` is reused without any request.
    - Older copies are revalidated with ETag / Last-Modified (HTTP 304 = unchanged).
    """

    def __init__(
        self,
        cache_dir: Path,
        *,
        offline: bool = False,
        max_age: timedelta = timedelta(hours=24),
        min_interval: float = 1.0,
        max_retries: int = 3,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
        rate_limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        chain_fixer: Callable[[str], ssl.SSLContext | None] = tls.completed_chain_context,
        client_factory: Callable[[ssl.SSLContext], httpx.Client] | None = None,
    ) -> None:
        self.cache = DiskCache(cache_dir)
        self.offline = offline
        self.max_age = max_age
        self.max_retries = max_retries
        self.rate_limiter = rate_limiter or RateLimiter(min_interval)
        self._sleep = sleep
        self._robots: dict[str, RobotFileParser | None] = {}
        self.stats = {"network": 0, "cache_hits": 0, "not_modified": 0, "errors": 0}
        if client is None:
            # Use the OS certificate store (works behind antivirus / proxy TLS inspection).
            ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            client = httpx.Client(
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=timeout,
                verify=ssl_ctx,
            )
        self.client = client
        self._timeout = timeout
        # Hosts whose certificate chain is incomplete get their own client trusting the
        # missing intermediate (see tls.py); everything else uses self.client.
        self._chain_fixer = chain_fixer
        self._client_factory = client_factory or self._default_client
        self._host_clients: dict[str, httpx.Client] = {}
        self._chain_fix_tried: set[str] = set()

    def _default_client(self, ssl_ctx: ssl.SSLContext) -> httpx.Client:
        return httpx.Client(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=self._timeout,
            verify=ssl_ctx,
        )

    def _client_for(self, url: str) -> httpx.Client:
        return self._host_clients.get(host_of(url), self.client)

    def _try_chain_fix(self, url: str) -> bool:
        """Once per host: build a client that trusts the site's missing intermediate."""
        host = host_of(url)
        if host in self._chain_fix_tried:
            return False
        self._chain_fix_tried.add(host)
        ctx = self._chain_fixer(host.split(":")[0])
        if ctx is None:
            return False
        self._host_clients[host] = self._client_factory(ctx)
        return True

    def close(self) -> None:
        self.client.close()
        for client in self._host_clients.values():
            client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- robots.txt ---------------------------------------------------------------

    def _robots_for(self, url: str) -> RobotFileParser | None:
        """Returns the parsed robots.txt for the URL's host (None = everything allowed)."""
        parts = urlsplit(url)
        host = parts.netloc.lower()
        if host in self._robots:
            return self._robots[host]
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        parser: RobotFileParser | None = None
        result = self._fetch_network(robots_url, conditional_from=None)
        if result.error is None and result.status is not None:
            if 200 <= result.status < 300 and "html" not in (result.content_type or ""):
                parser = RobotFileParser()
                parser.parse(result.body.decode("utf-8", errors="replace").splitlines())
            elif result.status >= 500:
                # RFC 9309: an unreachable robots.txt means "assume complete disallow".
                parser = RobotFileParser()
                parser.parse(["User-agent: *", "Disallow: /"])
            # 4xx (and HTML served instead of robots.txt) -> no rules, everything allowed.
        self._robots[host] = parser
        return parser

    def allowed(self, url: str) -> bool:
        parser = self._robots_for(url)
        return parser is None or parser.can_fetch(USER_AGENT, url)

    # -- fetching -----------------------------------------------------------------

    def fetch(self, url: str) -> FetchResult:
        cached = self.cache.get(url)
        if self.offline:
            if cached is None:
                return FetchResult(url=url, error="not in cache (offline mode)")
            self.stats["cache_hits"] += 1
            return cached

        if cached is not None and cached.fetched_at and self._is_fresh(cached.fetched_at):
            self.stats["cache_hits"] += 1
            return cached

        if not self.allowed(url):
            result = FetchResult(
                url=url,
                error="disallowed by robots.txt",
                robots_disallowed=True,
                fetched_at=now_utc().isoformat(timespec="seconds"),
            )
            self.cache.put(result)
            return result

        conditional = cached if cached is not None and cached.ok else None
        result = self._fetch_network(url, conditional_from=conditional)
        if result.status == 304 and conditional is not None:
            self.stats["not_modified"] += 1
            conditional.fetched_at = result.fetched_at
            conditional.from_cache = True
            self.cache.put(conditional)
            return conditional
        if not result.ok:
            self.stats["errors"] += 1
        # Cache definitive answers (2xx, 401/403/404…) so offline runs reproduce them;
        # transient failures (network errors, 429, 5xx) are retried next time instead.
        if result.status is not None and result.status not in RETRY_STATUSES:
            self.cache.put(result)
        return result

    def _is_fresh(self, fetched_at: str) -> bool:
        try:
            when = datetime.fromisoformat(fetched_at)
        except ValueError:
            return False
        return now_utc() - when < self.max_age

    def _fetch_network(self, url: str, conditional_from: FetchResult | None) -> FetchResult:
        headers: dict[str, str] = {}
        if conditional_from is not None:
            etag = conditional_from.headers.get("etag")
            last_modified = conditional_from.headers.get("last-modified")
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified

        last_error = "unknown error"
        for attempt in range(1, self.max_retries + 1):
            self.rate_limiter.wait(host_of(url))
            self.stats["network"] += 1
            try:
                response = self._client_for(url).get(url, headers=headers)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"[:300]
                if tls.is_missing_issuer_error(exc) and self._try_chain_fix(url):
                    continue  # retry at once with the completed chain
                if attempt < self.max_retries:
                    self._sleep(2**attempt)
                continue

            if response.status_code in RETRY_STATUSES and attempt < self.max_retries:
                self._sleep(_retry_delay(response, attempt))
                continue

            body = response.content
            if len(body) > MAX_BODY_BYTES:
                return FetchResult(url=url, status=response.status_code, error="body too large")
            return FetchResult(
                url=url,
                final_url=str(response.url),
                status=response.status_code,
                content_type=response.headers.get("content-type"),
                body=body,
                fetched_at=now_utc().isoformat(timespec="seconds"),
                headers={
                    k: response.headers[k]
                    for k in ("etag", "last-modified")
                    if k in response.headers
                },
            )
        return FetchResult(url=url, error=last_error)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after", "")
    if retry_after.isdigit():
        return min(float(retry_after), 30.0)
    return float(2**attempt)
