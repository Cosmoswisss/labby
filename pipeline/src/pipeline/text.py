"""Turn downloaded pages into clean text, and find the sub-pages worth following.

The clean text is what gets hashed (change detection) and, in phase 2, sent to the LLM.
Menus, headers and footers are stripped so that a site-wide menu change does not mark
every page as modified.
"""

from __future__ import annotations

import hashlib
import io
import re
import warnings
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin, urlsplit

import pdfplumber
from bs4 import BeautifulSoup

# trafilatura optionally imports urllib3's SOCKS support and warns when PySocks is
# missing; we never use its downloader, so the warning is irrelevant noise.
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import trafilatura

MAX_PDF_PAGES = 30

NOISE_TAGS = ["script", "style", "noscript", "nav", "aside", "form", "header", "footer", "svg"]


def normalize_text(text: str) -> str:
    """Collapses whitespace, strips lines and drops empty ones."""
    text = text.replace("\xa0", " ").replace("\r", "\n")
    lines = (re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def html_to_text(html: str) -> str:
    """Main content of an HTML page as plain text, headed by the page title.

    EPFL's WordPress sites wrap the content in <main>, which is the most reliable
    signal; other sites fall back to trafilatura (generic main-content extraction).
    The page title is prepended when the content does not contain it: on many lab
    sites a project page's only title is in <title> or in an <h1> outside <main>.
    """
    soup = BeautifulSoup(html, "lxml")
    titles = _page_titles(soup)
    _remove_archive_blocks(soup)
    text = _main_text(soup, html)
    missing = [t for t in titles if t not in text]
    return normalize_text("\n".join(missing + [text])) if missing else text


def _page_titles(soup: BeautifulSoup) -> list[str]:
    titles = []
    if soup.title:
        titles.append(normalize_text(soup.title.get_text(" ")).replace("\n", " "))
    main = soup.find("main")
    for h1 in soup.find_all("h1"):
        if main is None or main not in h1.parents:
            titles.append(normalize_text(h1.get_text(" ")).replace("\n", " "))
    return [t for t in dict.fromkeys(titles) if t]


def _remove_archive_blocks(soup: BeautifulSoup) -> None:
    """Drops blocks whose id/class says they hold completed or on-going projects.

    E.g. tab panes <div id="ongoing">, <div id="completed">, <section class="past-projects">:
    out of scope for Labby, and they often name the students working on them.
    """
    for tag in soup.find_all(True):
        if tag.name in ("html", "body", "main") or tag.decomposed:
            continue
        attrs = " ".join([tag.get("id") or ""] + list(tag.get("class") or []))
        if attrs.strip() and ARCHIVE_RE.search(attrs.replace("-", " ").replace("_", " ")):
            tag.decompose()


def _cleaned_body_text(soup: BeautifulSoup) -> str:
    body = soup.body or soup
    for tag in body.find_all(NOISE_TAGS):
        tag.decompose()
    return normalize_text(body.get_text("\n"))


def _main_text(soup: BeautifulSoup, html: str) -> str:
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    main_text = ""
    if main is not None:
        for tag in main.find_all(NOISE_TAGS):
            tag.decompose()
        for tag in main.select('[class*="breadcrumb"]'):
            tag.decompose()
        main_text = normalize_text(main.get_text("\n"))
        # A non-empty <main> is trusted even when short (e.g. an index page with two
        # links): trafilatura would rather pick up the site menus.
        if main_text:
            return main_text

    headings = [
        normalize_text(h.get_text(" ")).replace("\n", " ")
        for h in (soup.body or soup).find_all(["h2", "h3", "h4", "h5", "h6"])
    ]
    body_text = _cleaned_body_text(soup)
    extracted = normalize_text(
        trafilatura.extract(
            str(soup), include_tables=True, include_comments=False, favor_recall=True
        )
        or ""
    )
    # trafilatura drops headings inside "card" layouts (often the project titles): when it
    # loses several headings, the cleaned body text (menus removed) is the safer choice.
    lost = sum(1 for h in headings if h and h not in extracted)
    if extracted and lost < 3:
        return extracted
    return body_text or extracted


def pdf_to_text(data: bytes, max_pages: int = MAX_PDF_PAGES) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages[:max_pages]:
            parts.append(page.extract_text() or "")
    return normalize_text("\n".join(parts))


# -- login / restricted pages --------------------------------------------------------

LOGIN_URL_RE = re.compile(
    r"(/login|/log-in|/signin|/sign_in|/sign-in|/oidc/|/saml|/wayf|/cas/login|"
    r"tequila\.epfl\.ch|accounts\.google\.com|login\.microsoftonline\.com)",
    re.IGNORECASE,
)


def looks_like_login(final_url: str | None) -> bool:
    return bool(final_url and LOGIN_URL_RE.search(final_url))


# -- sub-page discovery ------------------------------------------------------------

SUBPAGE_HINT_RE = re.compile(
    r"project|projet|semester|thesis|theses|master|bachelor|student|available|propos|"
    r"offer|opening|topic|sujet",
    re.IGNORECASE,
)
# Archived, completed or already-assigned (on-going) projects: never followed. They are
# out of scope for Labby and often list the students working on them.
ARCHIVE_RE = re.compile(
    r"(?<![a-z])(completed?|past|archived?|archives|finished|previous|former|alumni|"
    r"on-?going|in[- ]progress|assigned|taken|termin[ée]s?|anciens?|en[- ]cours)(?![a-z])",
    re.IGNORECASE,
)
SKIP_URL_RE = re.compile(
    r"(/feed/?$|/wp-json/|/wp-login|/comments/|/tag/|/category/|/author/|"
    r"\.(jpe?g|png|gif|svg|webp|zip|gz|mp4|mov|pptx?|docx?|xlsx?|ics)$)",
    re.IGNORECASE,
)
EPFL_HOSTS = {"www.epfl.ch", "epfl.ch"}


@dataclass(frozen=True)
class Link:
    url: str
    text: str

    @property
    def is_pdf(self) -> bool:
        return urlsplit(self.url).path.lower().endswith(".pdf")


def site_scope(url: str) -> tuple[str, str]:
    """(host, path prefix) a lab's sub-pages must stay within.

    - www.epfl.ch hosts every lab: stay under the lab's own folder
      (/labs/<lab>/ or /schools/<school>/<unit>/).
    - Other hosts: stay under the folder of the projects page
      (bigwww.epfl.ch/teaching/projects/subject.html -> /teaching/projects/), so that
      tutorials, research pages or publications of the same site are not followed.
    """
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host not in EPFL_HOSTS:
        return host, parts.path[: parts.path.rfind("/") + 1] or "/"
    segments = [s for s in parts.path.split("/") if s]
    if not segments:
        return host, "/"
    depth = 2 if segments[0] == "labs" else 3
    return host, "/" + "/".join(segments[:depth]) + "/"


def _path_key(url: str) -> str:
    """URL path compared without trailing slash or index file: /a/ == /a/index.php."""
    path = urlsplit(url).path
    path = re.sub(r"/(index|default)\.(html?|php|aspx?)$", "/", path, flags=re.IGNORECASE)
    return path.rstrip("/")


def _canonical(url: str) -> str:
    url, _ = urldefrag(url)
    return url


def in_scope(url: str, scope: tuple[str, str]) -> bool:
    parts = urlsplit(url)
    host = parts.netloc.lower()
    scope_host, prefix = scope
    same_host = host == scope_host or (host in EPFL_HOSTS and scope_host in EPFL_HOSTS)
    path = parts.path if parts.path.endswith("/") else parts.path + "/"
    return parts.scheme in ("http", "https") and same_host and path.startswith(prefix)


def find_subpage_links(html: str, page_url: str, limit: int = 25) -> list[Link]:
    """Links from a lab's project page that probably lead to project descriptions."""
    soup = BeautifulSoup(html, "lxml")
    _remove_archive_blocks(soup)
    scope = site_scope(page_url)
    page = _canonical(page_url).rstrip("/")
    page_path = _path_key(page_url)
    seen: set[str] = set()
    links: list[Link] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")) or "@" in href:
            continue  # "@": e-mail addresses written without mailto:
        url = _canonical(urljoin(page_url, href))
        text = normalize_text(a.get_text(" "))
        key = url.rstrip("/")  # ".../aether-kite" and ".../aether-kite/" are the same page
        if key == page or key in seen:
            continue
        if _path_key(url) == page_path:
            continue  # same page with other query parameters (filters, views, sorting)
        if not in_scope(url, scope) or SKIP_URL_RE.search(url):
            continue
        if ARCHIVE_RE.search(url) or ARCHIVE_RE.search(text):
            continue
        link = Link(url=url, text=text)
        if not (link.is_pdf or SUBPAGE_HINT_RE.search(urlsplit(url).path + " " + text)):
            continue
        seen.add(key)
        links.append(link)
        if len(links) >= limit:
            break
    return links
