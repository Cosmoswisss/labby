"""Find each lab's student-project page from its homepage.

The official list of EPFL labs links to homepages. For each lab without a projects_url,
the homepage is fetched (politely, through the Fetcher) and every in-scope link is scored
by its text and URL: strong signals ("student projects", "semester projects", "master
thesis"…) beat medium ones ("join us", "open positions", "teaching"). When only a medium
link is found, that page is opened too, looking for a strong link one level deeper.
Results are written to labs.yaml with a note asking for a human review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup

from pipeline.crawl import classify
from pipeline.fetch import Fetcher
from pipeline.models import Lab
from pipeline.text import ARCHIVE_RE, SKIP_URL_RE, in_scope, normalize_text, site_scope

STRONG = re.compile(
    r"student[s-]? ?projects?|projects? for students|semester[- ]projects?|"
    r"master'?s?[- ](projects?|thes[ie]s)|bachelor[- ]projects?|available[- ]projects?|"
    r"proposed[- ]projects?|projects? proposals?|open[- ]projects?|offered[- ]projects?|"
    r"student[- ]opportunit|projets?[- ](étudiants?|de semestre|de master)|"
    r"travaux[- ]pratiques|studentprojects|student_projects|sprojects",
    re.IGNORECASE,
)
MEDIUM = re.compile(
    r"\b(join[- ]us|join[- ]the[- ]lab|openings?|open[- ]positions?|opportunit(y|ies)|"
    r"positions?|vacanc(y|ies)|students?|teaching|education|enseignement|"
    r"for[- ]students|work[- ]with[- ]us)\b",
    re.IGNORECASE,
)
NEGATIVE = re.compile(
    r"\b(publications?|people|team|members|news|events?|contact|seminars?|"
    r"phd[- ]positions?|postdoc|alumni|courses?)\b",
    re.IGNORECASE,
)
STRONG_SCORE, MEDIUM_SCORE = 10, 5


@dataclass
class Candidate:
    url: str
    text: str
    score: int


@dataclass
class DiscoverResult:
    lab_id: str
    status: str  # found | found_medium | none | error
    url: str | None = None
    link_text: str | None = None
    detail: str | None = None
    tried: list[str] = field(default_factory=list)


def score_link(text: str, url: str) -> int:
    path = urlsplit(url).path.replace("-", " ").replace("_", " ")
    haystack = f"{text} {path}"
    if ARCHIVE_RE.search(haystack):
        return 0
    if STRONG.search(text) or STRONG.search(urlsplit(url).path):
        return STRONG_SCORE
    if MEDIUM.search(haystack) and not NEGATIVE.search(text):
        return MEDIUM_SCORE
    return 0


def candidate_links(html: str, page_url: str) -> list[Candidate]:
    soup = BeautifulSoup(html, "lxml")
    scope = site_scope(page_url)
    seen: dict[str, Candidate] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")) or "@" in href:
            continue
        url, _ = urldefrag(urljoin(page_url, href))
        if url.rstrip("/") == page_url.rstrip("/") or SKIP_URL_RE.search(url):
            continue
        if not in_scope(url, scope):
            continue
        text = normalize_text(a.get_text(" ")).replace("\n", " ")[:120]
        score = score_link(text, url)
        if score and (url not in seen or seen[url].score < score):
            seen[url] = Candidate(url, text, score)
    # Best first; ties: shorter URL (closer to the lab's root), then page order.
    return sorted(seen.values(), key=lambda c: (-c.score, len(c.url)))


def discover_lab(fetcher: Fetcher, lab: Lab) -> DiscoverResult:
    if not lab.homepage_url:
        return DiscoverResult(lab.id, "none", detail="no homepage")
    home = fetcher.fetch(lab.homepage_url)
    status, error = classify(home)
    if status != "ok" or home.is_pdf:
        return DiscoverResult(lab.id, "error", detail=error or "homepage is not HTML")
    base = home.final_url or lab.homepage_url
    candidates = candidate_links(home.body.decode("utf-8", errors="replace"), base)
    result = DiscoverResult(lab.id, "none", tried=[base])
    if not candidates:
        return result
    best = candidates[0]
    if best.score >= STRONG_SCORE:
        return DiscoverResult(lab.id, "found", best.url, best.text, tried=[base])

    # Only medium links ("Join us", "Teaching"…): look one level deeper for a strong one.
    for medium in candidates[:3]:
        page = fetcher.fetch(medium.url)
        result.tried.append(medium.url)
        if classify(page)[0] != "ok" or page.is_pdf:
            continue
        deeper = candidate_links(
            page.body.decode("utf-8", errors="replace"), page.final_url or medium.url
        )
        if deeper and deeper[0].score >= STRONG_SCORE:
            return DiscoverResult(
                lab.id, "found", deeper[0].url, deeper[0].text, tried=result.tried
            )
    return DiscoverResult(lab.id, "found_medium", best.url, best.text, tried=result.tried)


def apply_result(lab: Lab, result: DiscoverResult) -> None:
    """Writes a discovery result into the lab (labs.yaml), flagged for review."""
    if result.status in ("found", "found_medium"):
        lab.projects_url = result.url
        confidence = "high" if result.status == "found" else "low"
        lab.notes = f"auto-discovered ({confidence} confidence, link '{result.link_text}'), review"
    elif result.status == "none":
        lab.notes = "no student-project link found on the homepage, review"
    else:
        lab.notes = f"homepage unreachable during discovery ({result.detail}), review"
