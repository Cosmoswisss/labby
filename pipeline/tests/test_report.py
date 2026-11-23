import json

from pipeline.report import diff_projects, render_markdown


def proj(pid, title, **kw):
    return {
        "id": pid,
        "lab_ids": ["ic-a"],
        "title": title,
        "summary": "",
        "status": "available",
        "project_types": [],
        "supervisors": [],
        "academic_period": None,
        **kw,
    }


def test_diff_projects():
    old = [proj("1", "Kept"), proj("2", "Removed"), proj("3", "Changed")]
    new = [proj("1", "Kept"), proj("3", "Changed", status="reserved"), proj("4", "Added")]
    d = diff_projects(old, new)
    assert [p["title"] for p in d["added"]] == ["Added"]
    assert [p["title"] for p in d["removed"]] == ["Removed"]
    assert [p["title"] for p in d["changed"]] == ["Changed"]


def test_render_markdown(tmp_path):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps({"projects": [proj("1", "Old one")]}), encoding="utf-8")
    new.write_text(json.dumps({"projects": [proj("2", "New one")]}), encoding="utf-8")
    extract = tmp_path / "extract.json"
    extract.write_text(
        json.dumps(
            {
                "pages_extracted": 3,
                "input_tokens": 12000,
                "stopped_reason": "token budget reached (400,000)",
            }
        )
    )
    md = render_markdown(old, new, None, extract)
    assert "1 → 1 (+1 new, −1 removed, 0 updated)" in md
    assert "- **ic-a**: New one" in md and "### Removed projects" in md
    assert "Stopped early: token budget" in md.replace("**", "")
    assert "Co-Authored" not in md and "Claude" not in md


def test_missing_old_file_counts_everything_as_new(tmp_path):
    new = tmp_path / "new.json"
    new.write_text(json.dumps({"projects": [proj("2", "New one")]}), encoding="utf-8")
    assert "0 → 1 (+1 new" in render_markdown(tmp_path / "missing.json", new)
