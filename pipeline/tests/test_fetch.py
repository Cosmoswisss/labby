from datetime import timedelta

import httpx

from pipeline.fetch import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


def test_rate_limiter_spaces_requests_per_host():
    c = FakeClock()
    limiter = RateLimiter(1.0, clock=c.clock, sleep=c.sleep)
    limiter.wait("a.ch")
    limiter.wait("b.ch")  # other host: no wait
    c.t += 0.3
    limiter.wait("a.ch")  # 0.3 s after the first: waits 0.7 s
    assert c.slept == [0.7]


def test_robots_disallow_blocks_without_fetching(web, make_fetcher):
    web.add(
        "https://lab.ch/robots.txt",
        "User-agent: *\nDisallow: /private/",
        **{"content-type": "text/plain"},
    )
    web.add("https://lab.ch/private/projects", "<html>secret</html>")
    fetcher = make_fetcher()
    result = fetcher.fetch("https://lab.ch/private/projects")
    assert result.robots_disallowed
    assert web.count("https://lab.ch/private/projects") == 0


def test_missing_robots_allows_everything(web, make_fetcher):
    web.add("https://lab.ch/projects", "<html>ok</html>")
    result = make_fetcher().fetch("https://lab.ch/projects")
    assert result.ok and result.body == b"<html>ok</html>"


def test_robots_5xx_means_disallow(web, make_fetcher):
    web.add("https://lab.ch/robots.txt", "oops", status=500)
    web.add("https://lab.ch/projects", "<html>ok</html>")
    result = make_fetcher(max_retries=1).fetch("https://lab.ch/projects")
    assert result.robots_disallowed


def test_retries_transient_errors(web, make_fetcher):
    calls = {"n": 0}

    def flaky(_request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, content=b"finally", headers={"content-type": "text/html"})

    web.routes["https://lab.ch/projects"] = flaky
    result = make_fetcher(max_retries=3).fetch("https://lab.ch/projects")
    assert result.ok and calls["n"] == 3


def test_fresh_cache_avoids_network(web, make_fetcher):
    web.add("https://lab.ch/projects", "<html>v1</html>")
    fetcher = make_fetcher()
    fetcher.fetch("https://lab.ch/projects")
    second = fetcher.fetch("https://lab.ch/projects")
    assert second.from_cache and web.count("https://lab.ch/projects") == 1


def test_stale_cache_is_revalidated_with_etag(web, make_fetcher):
    web.add("https://lab.ch/projects", "<html>v1</html>", etag='"abc"')
    make_fetcher().fetch("https://lab.ch/projects")

    def not_modified(request):
        assert request.headers.get("if-none-match") == '"abc"'
        return httpx.Response(304)

    web.routes["https://lab.ch/projects"] = not_modified
    result = make_fetcher(max_age=timedelta(0)).fetch("https://lab.ch/projects")
    assert result.ok and result.body == b"<html>v1</html>"


def test_offline_mode_uses_cache_only(web, make_fetcher):
    web.add("https://lab.ch/projects", "<html>v1</html>")
    make_fetcher().fetch("https://lab.ch/projects")
    n_requests = len(web.requests)
    offline = make_fetcher(offline=True)
    assert offline.fetch("https://lab.ch/projects").ok
    assert offline.fetch("https://lab.ch/other").error is not None
    assert len(web.requests) == n_requests


def test_definitive_errors_are_cached_for_offline_replay(web, make_fetcher):
    web.add("https://lab.ch/projects", "forbidden", status=403)
    make_fetcher().fetch("https://lab.ch/projects")
    replay = make_fetcher(offline=True).fetch("https://lab.ch/projects")
    assert replay.status == 403


def test_sends_explicit_user_agent(web, make_fetcher):
    web.add("https://lab.ch/projects", "<html>ok</html>")
    make_fetcher().fetch("https://lab.ch/projects")
    assert all("LabbyBot" in r.headers["user-agent"] for r in web.requests)
