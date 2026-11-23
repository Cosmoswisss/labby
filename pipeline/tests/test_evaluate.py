from pipeline.evaluate import (
    FieldScore,
    count_meta_summaries,
    last_names,
    match_projects,
    score_page,
    title_similarity,
)


def proj(title, types=(), sups=(), status="available", lab=None):
    return {
        "title": title,
        "project_types": list(types),
        "supervisors": list(sups),
        "status": status,
        "lab_acronym": lab,
    }


def fields():
    return {k: FieldScore() for k in ("project_types", "supervisors", "status", "lab_acronym")}


def test_title_similarity():
    assert title_similarity("3D Sound Localization", "3d sound localization") == 1.0
    assert (
        title_similarity(
            "Quantum constraint satisfaction problems (SMILS)",
            "Quantum constraint satisfaction problems",
        )
        == 1.0
    )
    assert title_similarity("Plasma headphones", "Plasmacoustic headphones") < 1.0
    assert title_similarity("Drone perception", "Protein design") < 0.8


def test_last_names():
    assert last_names(["Prof. Andrea Cavallaro", "Cavallaro, Andrea"]) == {"cavallaro"}
    assert last_names(["Hervé Lissek"]) == {"lissek"}


def test_matching_is_one_to_one():
    pred = [proj("Plasmacoustic headphones"), proj("Plasmacoustic headphones v2")]
    gold = [proj("Plasmacoustic headphones")]
    assert len(match_projects(pred, gold)) == 1


def test_score_page_counts_and_fields():
    gold = [
        {"title": "A project", "project_types": ["master_thesis"], "supervisors": ["Jane Doe"]},
        {"title": "B project", "project_types": None, "supervisors": [], "status": ["reserved"]},
        {"title": "Optional area", "project_types": None, "supervisors": None, "optional": True},
        {"title": "C project", "project_types": None, "supervisors": []},
    ]
    pred = [
        proj("A project", ["master_thesis", "semester_master"], ["Dr. Jane Doe"]),
        proj("B project", status="available"),
        proj("Optional area"),
        proj("Completely different", sups=["John Student"]),
    ]
    f = fields()
    ps = score_page("x", pred, gold, f)
    assert (ps.tp, ps.fp, ps.fn) == (2, 1, 1)  # optional neither tp nor fn
    assert ps.missed == ["C project"]
    assert f["project_types"].accuracy == 0.0  # A: extra level
    assert f["supervisors"].correct == 2  # A (title prefix ignored) and B (both empty)
    assert f["status"].correct == 1  # B should be reserved
    assert ps.unexpected_names == ["John Student"]


def test_empty_gold_page():
    ps = score_page("x", [proj("Not a project")], [], fields())
    assert (ps.tp, ps.fp, ps.fn) == (0, 1, 0)


def test_count_meta_summaries():
    projects = [
        {"summary": "Study coral reefs with 3D vision. The page gives only the title."},
        {"summary": "No further details are provided."},
        {"summary": "Build a perception stack for drones."},
    ]
    assert count_meta_summaries(projects) == 2


def test_clean_summary_drops_meta_sentences():
    from pipeline.summaries import clean_summary

    assert (
        clean_summary("Study coral reefs with 3D vision. The page gives only the title.")
        == "Study coral reefs with 3D vision."
    )
    assert (
        clean_summary("Train complex denoisers. The page lists it as an available master project.")
        == "Train complex denoisers."
    )
    assert (
        clean_summary("Build a perception stack for drones.")
        == "Build a perception stack for drones."
    )
    assert clean_summary("No further details are provided.") == ""
