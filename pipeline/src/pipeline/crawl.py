"""Crawl every lab's project page (+ one level of sub-pages) and detect changes.

Outputs:
- cache/text/<key>.txt      clean text of each page (input of phase 2, gitignored)
- state/crawl_state.json    per-lab status and per-page hash / dates (committed)
- state/crawl_report.json   summary of the last run (committed)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.fetch import DiskCache, Fetcher, FetchResult, now_utc
from pipeline.models import CrawlStatus, Lab
from pipeline.text import (
    content_hash,
    find_subpage_links,
    html_to_text,
    looks_like_login,
    pdf_to_text,
)

STATE_VERSION = 1
LITTLE_TEXT_CHARS = 80


@dataclass
class PageOutcome:
    url: str
    status: CrawlStatus
    kind: str = "html"  # html | pdf
    http_status: int | None = None
    final_url: str | None = None
    text: str = ""
    html: str = ""
    fetched_at: str | None = None
    error: str | None = None


@dataclass
class CrawlReport:
    started_at: str
    finished_at: str = ""
    duration_s: float = 0.0
    offline: bool = False
    labs_total: int = 0
    labs_by_status: dict[str, int] = field(default_factory=dict)
    pages_total: int = 0
    pages_new: int = 0
    pages_changed: int = 0
    pages_unchanged: int = 0
    pages_error: int = 0
    pages_duplicate: int = 0  # same text as another page of the lab, skipped
    pages_stale: int = 0  # unreachable this run: previous version kept
    little_text_pages: list[str] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    fetcher: dict[str, int] = field(default_factory=dict)


def classify(result: FetchResult) -> tuple[CrawlStatus, str | None]:
    """Maps a fetch result to a crawl status (+ error message)."""
    if result.robots_disallowed:
        return "blocked", result.error
    if result.error is not None and result.status is None:
        return "error", result.error
    if result.status == 401:
        return "restricted", "HTTP 401"
    if result.status == 403:
        return "blocked", "HTTP 403"
    if result.status is None or not (200 <= result.status < 300):
        return "error", f"HTTP {result.status}"
    if looks_like_login(result.final_url):
        return "restricted", f"redirected to login: {result.final_url}"
    return "ok", None


def is_transient(outcome: PageOutcome) -> bool:
    """Failures worth riding out with the previous version of the page.

    Network errors, timeouts, 5xx and 403 (some sites block cloud IP ranges, e.g. GitHub
    Actions runners) are often temporary. A 404/410 (page gone) or a robots.txt
    disallow (the site's explicit choice) is not.
    """
    if outcome.http_status in (404, 410):
        return False
    return not (outcome.error and "robots" in outcome.error)


def process_page(fetcher: Fetcher, url: str) -> PageOutcome:
    result = fetcher.fetch(url)
    status, error = classify(result)
    outcome = PageOutcome(
        url=url,
        status=status,
        http_status=result.status,
        final_url=result.final_url,
        fetched_at=result.fetched_at,
        error=error,
    )
    if status != "ok":
        return outcome
    try:
        if result.is_pdf:
            outcome.kind = "pdf"
            outcome.text = pdf_to_text(result.body)
        else:
            outcome.html = result.body.decode("utf-8", errors="replace")
            outcome.text = html_to_text(outcome.html)
    except Exception as exc:  # malformed PDF / HTML must not stop the crawl
        outcome.status = "error"
        outcome.error = f"text extraction failed: {type(exc).__name__}: {exc}"[:300]
    return outcome


class Crawler:
    def __init__(
        self,
        fetcher: Fetcher,
        cache_dir: Path,
        state_dir: Path,
        *,
        max_subpages: int = 25,
        log=print,
    ) -> None:
        self.fetcher = fetcher
        self.text_dir = cache_dir / "text"
        self.state_dir = state_dir
        self.max_subpages = max_subpages
        self.log = log
        self.state = load_state(state_dir / "crawl_state.json")

    def run(self, labs: list[Lab], *, partial: bool = False) -> CrawlReport:
        t0 = time.monotonic()
        report = CrawlReport(started_at=now_utc().isoformat(timespec="seconds"))
        report.offline = self.fetcher.offline
        old_pages: dict = self.state["pages"]
        new_pages: dict = dict(old_pages) if partial else {}
        if partial:  # forget the previous pages of the labs re-crawled now
            ids = {lab.id for lab in labs}
            for url, page in list(new_pages.items()):
                page["lab_ids"] = [i for i in page["lab_ids"] if i not in ids]
                if not page["lab_ids"]:
                    del new_pages[url]
        outcomes: dict[str, PageOutcome] = {}  # each URL is fetched once per run

        for n, lab in enumerate(labs, 1):
            self.log(f"[{n}/{len(labs)}] {lab.id}")
            lab_state = self._crawl_lab(lab, outcomes, old_pages, new_pages, report)
            self.state["labs"][lab.id] = lab_state
            report.labs_by_status[lab_state["status"]] = (
                report.labs_by_status.get(lab_state["status"], 0) + 1
            )

        if not partial:
            known = {lab.id for lab in labs}
            self.state["labs"] = {k: v for k, v in self.state["labs"].items() if k in known}
        self.state["pages"] = dict(sorted(new_pages.items()))
        self.state["updated_at"] = now_utc().isoformat(timespec="seconds")

        report.labs_total = len(labs)
        report.pages_total = len(outcomes)
        report.fetcher = dict(self.fetcher.stats)
        report.finished_at = now_utc().isoformat(timespec="seconds")
        report.duration_s = round(time.monotonic() - t0, 1)
        save_json(self.state_dir / "crawl_state.json", self.state)
        save_json(self.state_dir / "crawl_report.json", report.__dict__)
        return report

    def _crawl_lab(self, lab, outcomes, old_pages, new_pages, report) -> dict:
        lab_state = {
            "status": lab.source_type,
            "projects_url": lab.projects_url,
            "pages": [],
            "last_checked_at": None,
            "error": None,
        }
        if lab.source_type != "auto" or not lab.projects_url:
            lab_state["status"] = lab.source_type if lab.projects_url else "none"
            return lab_state

        # Hashes of the pages kept for this lab: the same content reached through another
        # URL (index.html, ?view=card…) is skipped instead of being extracted twice.
        lab_hashes: set[str] = set()
        ctx = (lab, lab_hashes, outcomes, old_pages, new_pages, report)

        seed, _ = self._visit(lab.projects_url, None, None, *ctx)
        lab_state["status"] = seed.status
        lab_state["error"] = seed.error
        lab_state["last_checked_at"] = seed.fetched_at
        if seed.status != "ok":
            previous = self.state["labs"].get(lab.id)
            if is_transient(seed) and previous and previous.get("pages"):
                # Temporary failure: keep last run's pages (and so their projects).
                for url in previous["pages"]:
                    self._keep_previous(url, lab, seed.error, old_pages, new_pages, report)
                return {**previous, "error": f"kept previous data: {seed.error}"}
            return lab_state
        lab_state["pages"].append(seed.url)

        if seed.kind == "html":
            for link in find_subpage_links(
                seed.html, seed.final_url or seed.url, self.max_subpages
            ):
                _, kept = self._visit(link.url, seed.url, link.text, *ctx)
                if kept:
                    lab_state["pages"].append(link.url)
        return lab_state

    def _keep_previous(self, url, lab, error, old_pages, new_pages, report) -> bool:
        """Carries a page's previous entry over to this run (unreachable right now)."""
        previous = old_pages.get(url)
        if previous is None:
            return False
        entry = new_pages.get(url) or {**previous, "lab_ids": [], "last_error": error}
        if lab.id not in entry["lab_ids"]:
            entry["lab_ids"].append(lab.id)
        if url not in new_pages:
            report.pages_stale += 1
        new_pages[url] = entry
        return True

    def _visit(
        self, url, parent, link_text, lab, lab_hashes, outcomes, old_pages, new_pages, report
    ) -> tuple[PageOutcome, bool]:
        """Fetches and records a page. Returns (outcome, kept for this lab).

        `link_text` is the anchor text of the link that led to a sub-page: often the
        project title, which some project pages do not repeat.
        """
        if url in outcomes:  # page shared with another lab, already fetched this run
            outcome = outcomes[url]
            page = new_pages.get(url)
            if page is None or page["content_hash"] in lab_hashes:
                return outcome, False
            if lab.id not in page["lab_ids"]:
                page["lab_ids"].append(lab.id)
            lab_hashes.add(page["content_hash"])
            return outcome, True

        outcome = process_page(self.fetcher, url)
        outcomes[url] = outcome
        if outcome.status != "ok":
            report.pages_error += 1
            report.errors.append(
                {"lab": lab.id, "url": url, "status": outcome.status, "error": outcome.error}
            )
            if is_transient(outcome) and url in old_pages:
                kept = self._keep_previous(url, lab, outcome.error, old_pages, new_pages, report)
                if kept:
                    lab_hashes.add(new_pages[url]["content_hash"])
                return outcome, kept
            return outcome, False

        digest = content_hash(outcome.text)
        if digest in lab_hashes:
            report.pages_duplicate += 1
            return outcome, False
        lab_hashes.add(digest)
        previous = old_pages.get(url)
        if previous is None:
            report.pages_new += 1
            first_seen, last_changed = outcome.fetched_at, outcome.fetched_at
        elif previous.get("content_hash") != digest:
            report.pages_changed += 1
            first_seen, last_changed = previous.get("first_seen_at"), outcome.fetched_at
        else:
            report.pages_unchanged += 1
            first_seen, last_changed = (
                previous.get("first_seen_at"),
                previous.get("last_changed_at"),
            )
        if len(outcome.text) < LITTLE_TEXT_CHARS:
            report.little_text_pages.append(url)

        self.text_dir.mkdir(parents=True, exist_ok=True)
        text_file = self.text_dir / f"{DiskCache.key(url)}.txt"
        text_file.write_text(outcome.text, encoding="utf-8", newline="\n")

        lab_ids = list(new_pages.get(url, {}).get("lab_ids", []))
        if lab.id not in lab_ids:
            lab_ids.append(lab.id)
        new_pages[url] = {
            "lab_ids": lab_ids,
            "parent_url": parent,
            "link_text": link_text or None,
            "kind": outcome.kind,
            "final_url": outcome.final_url,
            "content_hash": digest,
            "text_chars": len(outcome.text),
            "text_file": text_file.name,
            "first_seen_at": first_seen,
            "last_checked_at": outcome.fetched_at,
            "last_changed_at": last_changed,
        }
        return outcome, True


def load_state(path: Path) -> dict:
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("version") == STATE_VERSION:
            return state
    return {"version": STATE_VERSION, "updated_at": None, "labs": {}, "pages": {}}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
