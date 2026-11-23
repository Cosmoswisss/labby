"""Build labs.yaml from the public IC "projects in labs" page.

The page has three HTML tables (IC labs, accredited labs of other schools, centers)
with columns such as School / URL / Lab / Supervisor / IC Domain / Research Interests.
Columns are read by header name, so a reordering on the page does not break parsing.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from bs4 import BeautifulSoup, Tag

from pipeline.models import Lab

SOURCE_ID = "ic-mcs"
KNOWN_FACULTIES = {"IC", "STI", "SB", "SV", "ENAC", "CDM", "CDH"}

# Header names on the page -> our internal column keys
HEADER_KEYS = {
    "school": "school",
    "url": "acronym",  # the "URL" column holds the acronym, linked to the projects page
    "lab": "name",
    "center": "name",
    "supervisor": "heads",
    "ic domain": "ic_domains",
    "research interests": "research_interests",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _split_list(text: str, sep: str = ",") -> list[str]:
    return [item for item in (_clean(x) for x in text.split(sep)) if item]


def parse_faculties(school_cell: str) -> tuple[str, list[str]]:
    """'IC/SV (joint)' -> ('IC', ['SV']); 'ENT-R' -> ('ENT', [])."""
    text = re.sub(r"\(.*?\)", "", school_cell)
    parts = [p.strip().upper() for p in text.split("/") if p.strip()]
    faculties = []
    for part in parts:
        if part in KNOWN_FACULTIES:
            faculties.append(part)
        elif part.startswith("ENT"):
            faculties.append("ENT")
        else:
            faculties.append("OTHER")
    if not faculties:
        return "OTHER", []
    return faculties[0], [f for f in faculties[1:] if f != faculties[0]]


def guess_source_type(url: str | None) -> str:
    """Pre-fills the source hint from the URL alone; refined by hand in labs.yaml."""
    if not url:
        return "none"
    host = urlsplit(url).netloc.lower()
    if host == "people.epfl.ch":
        return "none"
    if host == "gitlab.epfl.ch" or host.startswith("inside.epfl.ch"):
        return "restricted"
    if host.endswith("notion.site") or host.endswith("notion.so"):
        return "js_rendered"
    return "auto"


def _table_rows(table: Tag) -> list[dict]:
    rows = table.find_all("tr")
    if not rows:
        return []
    headers = [_clean(th.get_text(" ")).lower() for th in rows[0].find_all(["th", "td"])]
    keys = [HEADER_KEYS.get(h) for h in headers]
    parsed = []
    for tr in rows[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        row: dict = {"links": {}}
        for key, cell in zip(keys, cells, strict=False):
            if key is None:
                continue
            if key == "heads":
                # Several supervisors are separated by ";" or by line breaks (<br>).
                row[key] = ";".join(cell.get_text("\n").split("\n"))
            else:
                row[key] = _clean(cell.get_text(" "))
            link = cell.find("a", href=True)
            if link:
                row["links"][key] = link["href"].strip()
        parsed.append(row)
    return parsed


def parse_labs_page(html: str) -> list[Lab]:
    """Parses the IC page into Lab objects, merging duplicate rows of the same lab."""
    soup = BeautifulSoup(html, "lxml")
    labs: dict[str, Lab] = {}
    for table in soup.find_all("table"):
        for row in _table_rows(table):
            acronym = row.get("acronym", "")
            raw_heads = _split_list(row.get("heads", ""), ";")
            # Remarks such as "(starts Nov 2026)" sit in the supervisor cell: keep them as notes.
            heads = [h for h in raw_heads if not h.startswith("(")]
            remarks = [h.strip("()") for h in raw_heads if h.startswith("(")]
            # The projects link is on the acronym; a link on the supervisor is a personal page.
            projects_url = row["links"].get("acronym")
            faculty, joint = parse_faculties(row.get("school", ""))

            if not acronym or acronym.upper() == "SIN-GE":
                # Teachers without a lab: one entry per person, keyed by their name.
                person = heads[0] if heads else "unknown"
                lab_id = f"{faculty.lower()}-{_slug(acronym or 'teacher')}-{_slug(person)}"
                projects_url = projects_url or row["links"].get("heads")
                name = row.get("name") or person
            else:
                lab_id = f"{faculty.lower()}-{_slug(acronym)}"
                name = row.get("name", acronym)

            if lab_id in labs:
                existing = labs[lab_id]
                for head in heads:
                    if head not in existing.heads:
                        existing.heads.append(head)
                continue

            labs[lab_id] = Lab(
                id=lab_id,
                acronym=acronym or (heads[0] if heads else ""),
                name=name,
                faculty=faculty,
                joint_faculties=joint,
                heads=heads,
                ic_domains=_split_list(row.get("ic_domains", "")),
                research_interests=_split_list(row.get("research_interests", "")),
                projects_url=projects_url,
                source_type=guess_source_type(projects_url),
                listed_in=[SOURCE_ID],
                notes="; ".join(remarks) or None,
            )
    return sorted(labs.values(), key=lambda lab: lab.id)


HEADER_COMMENT = """\
# Labby — labs crawled by the pipeline.
# Generated by `uv run pipeline labs`, then reviewed by hand: edits are kept
# (the command refuses to overwrite this file without --force).
#
# source_type:
#   auto         the crawler fetches projects_url and decides
#   none         no public project list (personal / contact page only)
#   restricted   list behind a login or the EPFL network: only the link is shown
#   js_rendered  rendered by JavaScript (Notion…): not crawled in V1
#   blocked      the site refuses crawlers (robots.txt / 403)
"""


def dump_labs_yaml(labs: list[Lab], path: Path) -> None:
    data = [lab.model_dump(exclude_defaults=False) for lab in labs]
    body = yaml.safe_dump(
        {"labs": data}, sort_keys=False, allow_unicode=True, width=100, default_flow_style=False
    )
    path.write_text(HEADER_COMMENT + "\n" + body, encoding="utf-8")


def load_labs(path: Path) -> list[Lab]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [Lab.model_validate(item) for item in data.get("labs", [])]
