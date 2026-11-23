import json
from datetime import timedelta

import httpx

from pipeline.crawl import Crawler
from pipeline.models import Lab

LONG = "This project studies robust perception for drones in the wild. " * 5


def lab(lab_id, url, source_type="auto"):
    return Lab(
        id=lab_id,
        acronym=lab_id,
        name=lab_id,
        faculty="IC",
        projects_url=url,
        source_type=source_type,
    )


def seed_page(extra=""):
    return f"""<html><body><main>
    <h1>Student projects</h1><p>{LONG}</p>
    <a href="/labs/vision/projects/drones/">Drone perception</a>
    <a href="/labs/vision/projects/completed/">Completed projects</a>
    <a href="/labs/vision/files/topic.pdf">Topic sheet</a>
    {extra}
    </main></body></html>"""


def setup_site(web):
    web.add("https://www.epfl.ch/labs/vision/projects/", seed_page())
    web.add(
        "https://www.epfl.ch/labs/vision/projects/drones/",
        f"<html><body><main><h1>Drones</h1><p>{LONG}</p></main></body></html>",
    )
    web.add(
        "https://www.epfl.ch/labs/vision/files/topic.pdf",
        b"not really a pdf",
        **{"content-type": "application/pdf"},
    )
    web.add("https://www.epfl.ch/labs/vision/projects/completed/", "<main>students…</main>")


def run(crawler_factory, labs, **kwargs):
    crawler = crawler_factory()
    return crawler, crawler.run(labs, **kwargs)


def make_crawler_factory(make_fetcher, tmp_path, **fetcher_kwargs):
    def factory():
        return Crawler(
            make_fetcher(**fetcher_kwargs),
            tmp_path / "cache",
            tmp_path / "state",
            log=lambda *_: None,
        )

    return factory


def test_crawl_follows_subpages_and_skips_archives(web, make_fetcher, tmp_path):
    setup_site(web)
    factory = make_crawler_factory(make_fetcher, tmp_path)
    crawler, report = run(factory, [lab("ic-vision", "https://www.epfl.ch/labs/vision/projects/")])

    state = crawler.state
    pages = state["labs"]["ic-vision"]["pages"]
    assert pages == [
        "https://www.epfl.ch/labs/vision/projects/",
        "https://www.epfl.ch/labs/vision/projects/drones/",
    ]
    assert web.count("https://www.epfl.ch/labs/vision/projects/completed/") == 0
    # the fake PDF cannot be parsed: reported as an error, the crawl goes on
    assert report.pages_error == 1 and report.pages_new == 2
    assert state["labs"]["ic-vision"]["status"] == "ok"
    saved = json.loads((tmp_path / "state" / "crawl_state.json").read_text(encoding="utf-8"))
    assert saved["pages"]["https://www.epfl.ch/labs/vision/projects/drones/"]["lab_ids"] == [
        "ic-vision"
    ]
    drones = saved["pages"]["https://www.epfl.ch/labs/vision/projects/drones/"]
    assert drones["link_text"] == "Drone perception"
    text_file = drones["text_file"]
    assert "Drones" in (tmp_path / "cache" / "text" / text_file).read_text(encoding="utf-8")


def test_second_run_detects_unchanged_and_changed_pages(web, make_fetcher, tmp_path):
    setup_site(web)
    labs = [lab("ic-vision", "https://www.epfl.ch/labs/vision/projects/")]
    run(make_crawler_factory(make_fetcher, tmp_path), labs)

    # only the seed page changes; menus outside <main> must not count as a change
    web.add(
        "https://www.epfl.ch/labs/vision/projects/",
        seed_page("<p>New project: tactile sensing</p>").replace("<body>", "<body><nav>x</nav>"),
    )
    _, report = run(make_crawler_factory(make_fetcher, tmp_path, max_age=timedelta(0)), labs)
    assert report.pages_changed == 1
    assert report.pages_unchanged == 1


def test_lab_status_restricted_blocked_and_hints(web, make_fetcher, tmp_path):
    web.add(
        "https://gitlab.lab.ch/projects",
        "",
        status=302,
        location="https://gitlab.lab.ch/users/sign_in",
    )
    web.add("https://gitlab.lab.ch/users/sign_in", "<html>Sign in</html>")
    web.add("https://rgl.lab.ch/projects", "nope", status=403)
    labs = [
        lab("ic-login", "https://gitlab.lab.ch/projects"),
        lab("ic-403", "https://rgl.lab.ch/projects"),
        lab("ic-person", "https://people.epfl.ch/x", source_type="none"),
        lab("ic-notion", "https://x.notion.site/p", source_type="js_rendered"),
        lab("ic-nourl", None),
    ]
    crawler, report = run(make_crawler_factory(make_fetcher, tmp_path), labs)
    statuses = {k: v["status"] for k, v in crawler.state["labs"].items()}
    assert statuses == {
        "ic-login": "restricted",
        "ic-403": "blocked",
        "ic-person": "none",
        "ic-notion": "js_rendered",
        "ic-nourl": "none",
    }
    # hinted labs are never fetched
    assert not any("people.epfl.ch" in str(r.url) or "notion" in str(r.url) for r in web.requests)


def test_shared_page_is_fetched_once_and_linked_to_both_labs(web, make_fetcher, tmp_path):
    url = "https://www.epfl.ch/schools/ic/ipg/proposed-projects/"
    web.add(url, f"<html><body><main><p>{LONG}</p></main></body></html>")
    labs = [lab("ic-lthc", url), lab("ic-lthi", url)]
    crawler, _ = run(make_crawler_factory(make_fetcher, tmp_path), labs)
    assert web.count(url) == 1
    assert crawler.state["pages"][url]["lab_ids"] == ["ic-lthc", "ic-lthi"]


def test_partial_run_keeps_other_labs(web, make_fetcher, tmp_path):
    web.add("https://a.lab.ch/p", f"<main><p>{LONG}</p></main>")
    web.add("https://b.lab.ch/p", f"<main><p>{LONG} B</p></main>")
    labs = [lab("ic-a", "https://a.lab.ch/p"), lab("ic-b", "https://b.lab.ch/p")]
    run(make_crawler_factory(make_fetcher, tmp_path), labs)
    crawler, _ = run(make_crawler_factory(make_fetcher, tmp_path), labs[:1], partial=True)
    assert set(crawler.state["labs"]) == {"ic-a", "ic-b"}
    assert "https://b.lab.ch/p" in crawler.state["pages"]


def test_network_error_is_reported(make_fetcher, tmp_path, web):
    def boom(request):
        raise httpx.ConnectError("getaddrinfo failed", request=request)

    web.routes["https://gone.lab.ch/p"] = boom
    crawler, report = run(
        make_crawler_factory(make_fetcher, tmp_path, max_retries=1),
        [lab("ic-gone", "https://gone.lab.ch/p")],
    )
    assert crawler.state["labs"]["ic-gone"]["status"] == "error"
    assert "ConnectError" in crawler.state["labs"]["ic-gone"]["error"]


def test_duplicate_content_under_another_url_is_skipped(web, make_fetcher, tmp_path):
    body = (
        f"<html><body><main><p>{LONG}</p>"
        + '<a href="/projects/subject.html">All projects</a>'
        + '<a href="/projects/p1.html">Project one</a></main></body></html>'
    )
    web.add("https://lib.lab.ch/projects/", body)
    web.add("https://lib.lab.ch/projects/subject.html", body)  # same page, other name
    web.add("https://lib.lab.ch/projects/p1.html", f"<main><p>{LONG} one</p></main>")
    factory = make_crawler_factory(make_fetcher, tmp_path)
    crawler, report = run(factory, [lab("sti-lib", "https://lib.lab.ch/projects/")])
    assert crawler.state["labs"]["sti-lib"]["pages"] == [
        "https://lib.lab.ch/projects/",
        "https://lib.lab.ch/projects/p1.html",
    ]
    assert report.pages_duplicate == 1
