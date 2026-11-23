"""Test helpers: a fake web served through httpx.MockTransport (no network access)."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from pipeline.config import USER_AGENT
from pipeline.fetch import Fetcher, RateLimiter


class FakeWeb:
    """Maps URL -> response; records every request made."""

    def __init__(self) -> None:
        self.routes: dict[str, Callable[[httpx.Request], httpx.Response] | httpx.Response] = {}
        self.requests: list[httpx.Request] = []

    def add(self, url: str, body: str | bytes = "", status: int = 200, **headers: str) -> None:
        content = body.encode() if isinstance(body, str) else body
        headers.setdefault("content-type", "text/html; charset=utf-8")
        self.routes[url] = httpx.Response(status, content=content, headers=headers)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(str(request.url))
        if route is None:
            return httpx.Response(404, content=b"not found")
        if callable(route):
            return route(request)
        return httpx.Response(route.status_code, content=route.content, headers=route.headers)

    def count(self, url: str) -> int:
        return sum(1 for r in self.requests if str(r.url) == url)


@pytest.fixture
def web() -> FakeWeb:
    return FakeWeb()


@pytest.fixture
def make_fetcher(web: FakeWeb, tmp_path):
    def _make(**kwargs) -> Fetcher:
        client = httpx.Client(
            transport=httpx.MockTransport(web.handler),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        kwargs.setdefault("rate_limiter", RateLimiter(0.0))
        kwargs.setdefault("sleep", lambda _s: None)
        return Fetcher(tmp_path / "cache", client=client, **kwargs)

    return _make
