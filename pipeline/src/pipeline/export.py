"""Build data/projects.json and data/labs.json for the website.

Inputs: labs.yaml (curated lab list), state/crawl_state.json (pages, dates),
state/extractions.json (projects extracted per page).

- A project found on a lab's index page and again on its own sub-page is merged
  (same normalised title within the lab); the sub-page becomes its description URL.
- On pages shared by several labs, a project goes to the lab named by `lab_acronym`;
  without it, it is attributed to all the labs sharing the page.
- When a sub-page's parent list contains projects, the list is authoritative about what
  is open: a project found only on a sub-page (e.g. the abstract of an on-going or
  completed project linked from the list) is dropped. Sub-pages of index pages that list
  no project themselves (links only) remain the source.
- Students' names are never present: the extraction only returns supervisors.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

from pipeline.crawl import load_state, save_json
from pipeline.evaluate import MATCH_THRESHOLD, norm, title_similarity
from pipeline.extract import load_extractions
from pipeline.fetch import now_utc
from pipeline.models import Lab

LIST_FIELDS = ("project_types", "domains", "skills", "supervisors")


def project_id(lab_ids: list[str], title: str) -> str:
    return hashlib.sha1(f"{'+'.join(sorted(lab_ids))}|{norm(title)}".encode()).hexdigest()[:12]


def _attribute(project: dict, page_lab_ids: list[str], labs_by_id: dict[str, Lab]) -> list[str]:
    if len(page_lab_ids) > 1 and project.get("lab_acronym"):
        wanted = norm(project["lab_acronym"])
        named = [
            i for i in page_lab_ids if i in labs_by_id and norm(labs_by_id[i].acronym) == wanted
        ]
        if named:
            return named
    return list(page_lab_ids)


def _merge(base: dict, other: dict) -> dict:
    """Merges two records of the same project; `base` comes from the more specific page."""
    for key in LIST_FIELDS:
        base[key] = list(dict.fromkeys(base[key] + other[key]))
    for key in ("summary", "academic_period", "page_updated_at"):
        if not base.get(key) and other.get(key):
            base[key] = other[key]
    if base["status"] == "unknown":
        base["status"] = other["status"]
    if base["language"] == "unknown":
        base["language"] = other["language"]
    base["first_seen_at"] = min(filter(None, [base["first_seen_at"], other["first_seen_at"]]))
    base["last_seen_at"] = max(filter(None, [base["last_seen_at"], other["last_seen_at"]]))
    base["source_pages"] = list(dict.fromkeys(base["source_pages"] + other["source_pages"]))
    return base


def build_projects(labs: list[Lab], crawl_state: dict, extractions: dict) -> list[dict]:
    labs_by_id = {lab.id: lab for lab in labs}
    merged: dict[tuple[str, str], dict] = {}
    for url, entry in extractions["pages"].items():
        page = crawl_state["pages"].get(url)
        if page is None or entry.get("error"):
            continue  # page no longer crawled, or extraction failed
        parent_url = page.get("parent_url")
        parent = extractions["pages"].get(parent_url) if parent_url else None
        if parent_url and (parent is None or parent.get("error")):
            continue  # list page not extracted: cannot tell which sub-pages are still open
        parent_titles = [p["title"] for p in parent["projects"]] if parent else []
        for raw in entry["projects"]:
            lab_ids = [i for i in _attribute(raw, page["lab_ids"], labs_by_id) if i in labs_by_id]
            if not lab_ids:
                continue
            merge_title = raw["title"]
            if parent_titles:
                best = max(parent_titles, key=lambda t: title_similarity(t, raw["title"]))
                if title_similarity(best, raw["title"]) < MATCH_THRESHOLD:
                    continue  # not offered on the parent list: probably taken or past
                merge_title = best  # merge with the list entry even if worded differently
            record = {
                "lab_ids": lab_ids,
                "title": raw["title"].strip(),
                "summary": raw["summary"].strip(),
                "description_url": url,
                "project_types": raw["project_types"],
                "domains": [d.lower() for d in raw["domains"]],
                "skills": raw["skills"],
                "language": raw["language"],
                "supervisors": raw["supervisors"],
                "status": raw["status"],
                "academic_period": raw["academic_period"],
                "page_updated_at": entry.get("page_updated_at"),
                "first_seen_at": page.get("first_seen_at"),
                "last_seen_at": page.get("last_checked_at"),
                "source_pages": [url],
                "_specific": page.get("parent_url") is not None,
            }
            key = ("+".join(sorted(lab_ids)), norm(merge_title))
            if key not in merged:
                merged[key] = record
            elif record["_specific"] and not merged[key]["_specific"]:
                merged[key] = _merge(record, merged[key])
            else:
                merged[key] = _merge(merged[key], record)

    projects = []
    for record in merged.values():
        record.pop("_specific")
        record["id"] = project_id(record["lab_ids"], record["title"])
        projects.append({"id": record.pop("id"), **record})
    return sorted(projects, key=lambda p: (p["lab_ids"], norm(p["title"])))


def build_labs(labs: list[Lab], crawl_state: dict, projects: list[dict]) -> list[dict]:
    counts = Counter(lab_id for p in projects for lab_id in p["lab_ids"])
    result = []
    for lab in labs:
        state = crawl_state["labs"].get(lab.id, {})
        result.append(
            {
                "id": lab.id,
                "acronym": lab.acronym,
                "name": lab.name,
                "faculty": lab.faculty,
                "joint_faculties": lab.joint_faculties,
                "heads": lab.heads,
                "ic_domains": lab.ic_domains,
                "research_interests": lab.research_interests,
                "projects_url": lab.projects_url,
                "status": state.get("status", lab.source_type),
                "last_checked_at": state.get("last_checked_at"),
                "project_count": counts.get(lab.id, 0),
            }
        )
    return result


def export(labs: list[Lab], state_dir: Path, data_dir: Path) -> dict:
    crawl_state = load_state(state_dir / "crawl_state.json")
    extractions = load_extractions(state_dir / "extractions.json")
    projects = build_projects(labs, crawl_state, extractions)
    labs_out = build_labs(labs, crawl_state, projects)
    generated_at = now_utc().isoformat(timespec="seconds")
    save_json(data_dir / "projects.json", {"generated_at": generated_at, "projects": projects})
    save_json(data_dir / "labs.json", {"generated_at": generated_at, "labs": labs_out})

    crawled = [u for u in crawl_state["pages"]]
    extracted = [u for u in crawled if u in extractions["pages"]]
    report = {
        "generated_at": generated_at,
        "labs": len(labs_out),
        "labs_by_status": dict(Counter(lab["status"] for lab in labs_out)),
        "labs_with_projects": sum(1 for lab in labs_out if lab["project_count"]),
        "projects": len(projects),
        "projects_by_status": dict(Counter(p["status"] for p in projects)),
        "pages_crawled": len(crawled),
        "pages_extracted": len(extracted),
        "pages_failed": sum(1 for u in extracted if extractions["pages"][u].get("error")),
        "pages_not_yet_extracted": len(crawled) - len(extracted),
        "extraction_tokens_in": sum(
            e.get("input_tokens", 0) for e in extractions["pages"].values()
        ),
        "extraction_tokens_out": sum(
            e.get("output_tokens", 0) for e in extractions["pages"].values()
        ),
    }
    save_json(state_dir / "export_report.json", report)
    return report
