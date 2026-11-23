"""Markdown summary of a data update, used as the body of the automatic pull request."""

from __future__ import annotations

import json
from pathlib import Path


def _load(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def diff_projects(old: list[dict], new: list[dict]) -> dict:
    old_by_id = {p["id"]: p for p in old}
    new_by_id = {p["id"]: p for p in new}
    added = [new_by_id[i] for i in new_by_id.keys() - old_by_id.keys()]
    removed = [old_by_id[i] for i in old_by_id.keys() - new_by_id.keys()]
    watched = ("title", "summary", "status", "project_types", "supervisors", "academic_period")
    changed = [
        new_by_id[i]
        for i in new_by_id.keys() & old_by_id.keys()
        if any(new_by_id[i].get(k) != old_by_id[i].get(k) for k in watched)
    ]
    key = lambda p: (p["lab_ids"], p["title"].lower())  # noqa: E731
    return {
        "added": sorted(added, key=key),
        "removed": sorted(removed, key=key),
        "changed": sorted(changed, key=key),
    }


def _lines(projects: list[dict], limit: int = 40) -> list[str]:
    lines = [f"- **{', '.join(p['lab_ids'])}**: {p['title']}" for p in projects[:limit]]
    if len(projects) > limit:
        lines.append(f"- … and {len(projects) - limit} more")
    return lines


def render_markdown(
    old_projects_path: Path | None,
    new_projects_path: Path,
    crawl_report_path: Path | None = None,
    extract_report_path: Path | None = None,
) -> str:
    old = _load(old_projects_path).get("projects", [])
    new = _load(new_projects_path).get("projects", [])
    crawl = _load(crawl_report_path)
    extract = _load(extract_report_path)
    d = diff_projects(old, new)

    out = [
        "## Weekly data update",
        "",
        f"**Projects:** {len(old)} → {len(new)} "
        f"(+{len(d['added'])} new, −{len(d['removed'])} removed, {len(d['changed'])} updated)",
    ]
    if crawl:
        out.append(
            f"**Crawl:** {crawl.get('pages_total', 0)} pages, {crawl.get('pages_new', 0)} new, "
            f"{crawl.get('pages_changed', 0)} changed, {crawl.get('pages_error', 0)} errors"
        )
    if extract:
        out.append(
            f"**Extraction:** {extract.get('pages_extracted', 0)} pages sent to the model, "
            f"{extract.get('pages_failed', 0)} failed, {extract.get('pages_left', 0)} left for "
            f"next run · {extract.get('input_tokens', 0):,} input / "
            f"{extract.get('output_tokens', 0):,} output tokens"
        )
        if extract.get("stopped_reason"):
            out.append(f"**Stopped early:** {extract['stopped_reason']}")
    for title, key in (
        ("New projects", "added"),
        ("Removed projects", "removed"),
        ("Updated projects", "changed"),
    ):
        if d[key]:
            out += ["", f"### {title}", *_lines(d[key])]
    errors = crawl.get("errors", []) if crawl else []
    if errors:
        out += ["", "### Crawl errors"]
        out += [f"- {e['lab']}: {e['status']} {e['url']}" for e in errors[:20]]
    out += [
        "",
        "Check the Vercel preview of this pull request, then merge to publish.",
    ]
    return "\n".join(out) + "\n"
