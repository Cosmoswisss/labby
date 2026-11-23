from pipeline.export import build_labs, build_projects
from pipeline.models import Lab


def lab(lab_id, acronym):
    return Lab(id=lab_id, acronym=acronym, name=acronym, faculty="IC")


def raw(title, **kw):
    base = {
        "title": title,
        "lab_acronym": None,
        "summary": "",
        "project_types": [],
        "domains": [],
        "skills": [],
        "language": "EN",
        "supervisors": [],
        "status": "unknown",
        "academic_period": None,
    }
    return {**base, **kw}


def page(lab_ids, parent=None, first="2026-11-01T00:00:00+00:00", last="2026-11-23T00:00:00+00:00"):
    return {
        "lab_ids": lab_ids,
        "parent_url": parent,
        "first_seen_at": first,
        "last_checked_at": last,
    }


def extraction(projects, error=None, updated=None):
    return {"error": error, "projects": projects, "page_updated_at": updated}


def test_index_and_subpage_are_merged_with_subpage_url():
    labs = [lab("ic-cvlab", "CVLAB")]
    crawl = {
        "pages": {
            "https://x/projects/": page(["ic-cvlab"]),
            "https://x/projects/kite/": page(["ic-cvlab"], parent="https://x/projects/"),
        }
    }
    ext = {
        "pages": {
            "https://x/projects/": extraction([raw("Kite tracking", summary="Short.")]),
            "https://x/projects/kite/": extraction(
                [
                    raw(
                        "Kite Tracking",
                        supervisors=["Jane Doe"],
                        status="available",
                        project_types=["master_thesis"],
                    )
                ]  # fmt: skip
            ),
        }
    }
    projects = build_projects(labs, crawl, ext)
    assert len(projects) == 1
    p = projects[0]
    assert p["description_url"] == "https://x/projects/kite/"
    assert p["supervisors"] == ["Jane Doe"] and p["status"] == "available"
    assert p["summary"] == "Short."  # filled from the index entry
    assert set(p["source_pages"]) == {"https://x/projects/", "https://x/projects/kite/"}


def test_shared_page_uses_lab_acronym():
    labs = [lab("ic-smils", "SMILS"), lab("ic-linx", "LINX"), lab("ic-lthc", "LTHC")]
    crawl = {"pages": {"https://ipg/": page(["ic-lthc", "ic-smils", "ic-linx"])}}
    ext = {
        "pages": {
            "https://ipg/": extraction(
                [raw("Quantum CSP", lab_acronym="SMILS"), raw("Untagged project")]
            )
        }
    }
    by_title = {p["title"]: p for p in build_projects(labs, crawl, ext)}
    assert by_title["Quantum CSP"]["lab_ids"] == ["ic-smils"]
    assert by_title["Untagged project"]["lab_ids"] == ["ic-lthc", "ic-smils", "ic-linx"]


def test_failed_or_uncrawled_pages_are_skipped_and_labs_counted():
    labs = [lab("ic-a", "A"), lab("ic-b", "B")]
    crawl = {"pages": {"https://a/": page(["ic-a"]), "https://b/": page(["ic-b"])},
             "labs": {"ic-a": {"status": "ok"}}}  # fmt: skip
    ext = {
        "pages": {
            "https://a/": extraction([raw("P1"), raw("P2")]),
            "https://b/": extraction([raw("P3")], error="timeout"),
            "https://gone/": extraction([raw("P4")]),
        }
    }
    projects = build_projects(labs, crawl, ext)
    assert [p["title"] for p in projects] == ["P1", "P2"]
    labs_out = {x["id"]: x for x in build_labs(labs, crawl, projects)}
    assert labs_out["ic-a"]["project_count"] == 2 and labs_out["ic-a"]["status"] == "ok"
    assert labs_out["ic-b"]["project_count"] == 0 and labs_out["ic-b"]["status"] == "auto"


def test_project_ids_are_stable():
    labs = [lab("ic-a", "A")]
    crawl = {"pages": {"https://a/": page(["ic-a"])}}
    ext = {"pages": {"https://a/": extraction([raw("My  Project!")])}}
    first = build_projects(labs, crawl, ext)[0]["id"]
    ext2 = {"pages": {"https://a/": extraction([raw("my project")])}}
    assert build_projects(labs, crawl, ext2)[0]["id"] == first
