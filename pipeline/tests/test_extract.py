import json
from datetime import date

from pipeline.crawl import save_json
from pipeline.engines import EngineResult, FakeEngine, parse_claude_output
from pipeline.extract import Extractor, build_user_prompt
from pipeline.models import Lab, PageExtraction

PROJECT = {
    "title": "Drone perception",
    "lab_acronym": None,
    "summary": "Build a perception stack for drones.",
    "project_types": ["master_thesis"],
    "domains": ["computer vision"],
    "skills": ["Python"],
    "language": "EN",
    "supervisors": ["Jane Doe"],
    "status": "available",
    "academic_period": "Spring 2027",
}
RESPONSE = {"page_kind": "project_list", "page_updated_at": None, "projects": [PROJECT]}


def lab(lab_id, acronym="VIS"):
    return Lab(id=lab_id, acronym=acronym, name=f"{acronym} lab", faculty="IC")


def setup_state(tmp_path, pages):
    """pages: {url: (lab_ids, text, content_hash)}"""
    (tmp_path / "cache" / "text").mkdir(parents=True)
    state = {"version": 1, "updated_at": None, "labs": {}, "pages": {}}
    for i, (url, (lab_ids, text, digest)) in enumerate(pages.items()):
        name = f"p{i}.txt"
        (tmp_path / "cache" / "text" / name).write_text(text, encoding="utf-8")
        state["pages"][url] = {
            "lab_ids": lab_ids,
            "parent_url": None,
            "content_hash": digest,
            "text_chars": len(text),
            "text_file": name,
        }
    save_json(tmp_path / "state" / "crawl_state.json", state)
    return state


def make_extractor(tmp_path, engine):
    return Extractor(
        engine,
        tmp_path / "cache",
        tmp_path / "state",
        today=date(2026, 11, 23),
        log=lambda *_: None,
    )


def test_extracts_and_stores_projects(tmp_path):
    setup_state(tmp_path, {"https://a.ch/p": (["ic-vis"], "Drone perception ...", "h1")})
    engine = FakeEngine([RESPONSE])
    report = make_extractor(tmp_path, engine).run([lab("ic-vis")])
    assert report.pages_extracted == 1 and report.projects_found == 1
    store = json.loads((tmp_path / "state" / "extractions.json").read_text(encoding="utf-8"))
    entry = store["pages"]["https://a.ch/p"]
    assert entry["projects"][0]["title"] == "Drone perception"
    assert entry["error"] is None
    # the page text and lab are in the prompt
    assert "Drone perception ..." in engine.calls[0][1] and "VIS: VIS lab" in engine.calls[0][1]


def test_unchanged_pages_are_not_sent_again(tmp_path):
    setup_state(tmp_path, {"https://a.ch/p": (["ic-vis"], "text", "h1")})
    make_extractor(tmp_path, FakeEngine([RESPONSE])).run([lab("ic-vis")])
    engine = FakeEngine([])
    report = make_extractor(tmp_path, engine).run([lab("ic-vis")])
    assert engine.calls == [] and report.pages_up_to_date == 1


def test_changed_page_is_extracted_again(tmp_path):
    setup_state(tmp_path, {"https://a.ch/p": (["ic-vis"], "text", "h1")})
    make_extractor(tmp_path, FakeEngine([RESPONSE])).run([lab("ic-vis")])
    setup_state_again = {"https://a.ch/p": (["ic-vis"], "new text", "h2")}
    (tmp_path / "cache" / "text" / "p0.txt").unlink()
    (tmp_path / "cache" / "text").rmdir()
    setup_state(tmp_path, setup_state_again)
    engine = FakeEngine([RESPONSE])
    make_extractor(tmp_path, engine).run([lab("ic-vis")])
    assert len(engine.calls) == 1


def test_invalid_output_is_retried_then_recorded_as_error(tmp_path):
    setup_state(tmp_path, {"https://a.ch/p": (["ic-vis"], "text", "h1")})
    bad = {"page_kind": "project_list", "projects": [{"title": "x"}]}  # missing fields
    engine = FakeEngine([bad, EngineResult(None, error="claude error: overloaded")])
    report = make_extractor(tmp_path, engine).run([lab("ic-vis")])
    assert len(engine.calls) == 2 and report.pages_failed == 1
    # failed pages stay pending for the next run
    assert make_extractor(tmp_path, FakeEngine([])).pending_pages() == ["https://a.ch/p"]


def test_retry_succeeds(tmp_path):
    setup_state(tmp_path, {"https://a.ch/p": (["ic-vis"], "text", "h1")})
    engine = FakeEngine([EngineResult(None, error="timeout"), RESPONSE])
    report = make_extractor(tmp_path, engine).run([lab("ic-vis")])
    assert report.pages_extracted == 1 and report.pages_failed == 0


def test_limit_and_dry_run(tmp_path):
    pages = {f"https://a.ch/p{i}": (["ic-vis"], "x" * 400, f"h{i}") for i in range(3)}
    setup_state(tmp_path, pages)
    dry = make_extractor(tmp_path, FakeEngine([])).run([lab("ic-vis")], dry_run=True)
    assert dry.pages_left == 3 and dry.input_tokens == int((3 * 100 + 3 * 2000) * 1.75)
    engine = FakeEngine([RESPONSE])
    report = make_extractor(tmp_path, engine).run([lab("ic-vis")], limit=1)
    assert len(engine.calls) == 1 and report.pages_left == 2


def test_lab_filter(tmp_path):
    setup_state(
        tmp_path,
        {"https://a.ch/p": (["ic-a"], "a", "h1"), "https://b.ch/p": (["ic-b"], "b", "h2")},
    )
    ex = make_extractor(tmp_path, FakeEngine([]))
    assert ex.pending_pages({"ic-b"}) == ["https://b.ch/p"]


def test_shared_page_prompt_lists_all_labs():
    prompt = build_user_prompt(
        "https://x.ch/p", "text", [lab("ic-a", "LTHC"), lab("ic-b", "LTHI")], None, date(2026, 1, 1)
    )
    assert "shared by several labs: yes" in prompt and "LTHC" in prompt and "LTHI" in prompt


def test_schema_is_strict():
    schema = PageExtraction.model_json_schema()
    assert schema["additionalProperties"] is False
    project = schema["$defs"]["ExtractedProject"]
    assert set(project["required"]) == set(PROJECT)


def test_parse_claude_output():
    ok = json.dumps(
        {
            "is_error": False,
            "subtype": "success",
            "structured_output": RESPONSE,
            "usage": {"input_tokens": 2, "cache_creation_input_tokens": 1000, "output_tokens": 50},
        }
    )
    result = parse_claude_output(0, ok, "")
    assert result.error is None and result.data == RESPONSE and result.input_tokens == 1002
    assert parse_claude_output(1, "Not logged in", "").error.startswith("exit 1")
    err = json.dumps({"is_error": True, "result": "Usage limit reached", "usage": {}})
    assert "Usage limit" in parse_claude_output(1, err, "").error


def test_link_text_is_given_as_title_hint_for_subpages():
    prompt = build_user_prompt(
        "https://lts2.epfl.ch/projects/146",
        "Supervision: ...",
        [lab("sti-lts2", "LTS2")],
        "https://lts2.epfl.ch/projects/list",
        date(2026, 1, 1),
        link_text="Controlling the timbre of wind instruments",
    )
    assert '"Controlling the timbre of wind instruments"' in prompt


def test_pages_no_longer_crawled_are_pruned(tmp_path):
    setup_state(tmp_path, {"https://a.ch/p": (["ic-vis"], "text", "h1")})
    make_extractor(tmp_path, FakeEngine([RESPONSE])).run([lab("ic-vis")])
    (tmp_path / "cache" / "text" / "p0.txt").unlink()
    (tmp_path / "cache" / "text").rmdir()
    setup_state(tmp_path, {"https://b.ch/p": (["ic-vis"], "text", "h2")})
    make_extractor(tmp_path, FakeEngine([RESPONSE])).run([lab("ic-vis")])
    store = json.loads((tmp_path / "state" / "extractions.json").read_text(encoding="utf-8"))
    assert list(store["pages"]) == ["https://b.ch/p"]
