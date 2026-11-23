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

# Below this many characters, the <main> extraction is considered a miss.
MIN_MAIN_CHARS = 200
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
    """Main content of an HTML page as plain text.

    EPFL's WordPress sites wrap the content in <main>, which is the most reliable
    signal; other sites fall back to trafilatura (generic main-content extraction).
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    main_text = ""
    if main is not None:
        for tag in main.find_all(NOISE_TAGS):
            tag.decompose()
        for tag in main.select('[class*="breadcrumb"]'):
            tag.decompose()
        main_text = normalize_text(main.get_text("\n"))
        if len(main_text) >= MIN_MAIN_CHARS:
            return main_text

    extracted = trafilatura.extract(
        html, include_tables=True, include_comments=False, favor_recall=True
    )
    candidates = [main_text, normalize_text(extracted or "")]
    best = max(candidates, key=len)
    if best:
        return best

    body = soup.body or soup
    for tag in body.find_all(NOISE_TAGS):
        tag.decompose()
    return normalize_text(body.get_text("\n"))


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
