from pipeline.discover import apply_result, candidate_links, discover_lab, score_link
from pipeline.labs import merge_labs, parse_epfl_labs_page
from pipeline.models import Lab

HOME = "https://www.epfl.ch/labs/vision/"


def lab(lab_id="sti-vision", homepage=HOME):
    return Lab(id=lab_id, acronym="VISION", name="Vision", faculty="STI", homepage_url=homepage)


def test_score_link():
    assert score_link("Student Projects", HOME + "students/") == 10
    assert score_link("Master thesis", HOME + "x/") == 10
    assert score_link("Join us", HOME + "join/") == 5
    assert score_link("Teaching", HOME + "teaching/") == 5
    assert score_link("Completed student projects", HOME + "completed/") == 0
    assert score_link("Publications", HOME + "pubs/") == 0


def test_candidate_links_scope_and_order():
    html = """
    <a href="/labs/vision/join-us/">Join us</a>
    <a href="/labs/vision/student-projects/">Student projects</a>
    <a href="/labs/other/student-projects/">Other lab projects</a>
    <a href="/labs/vision/past-projects/">Past student projects</a>
    """
    urls = [c.url for c in candidate_links(html, HOME)]
    assert urls == [
        "https://www.epfl.ch/labs/vision/student-projects/",
        "https://www.epfl.ch/labs/vision/join-us/",
    ]


def test_discover_strong_link(web, make_fetcher):
    web.add(HOME, '<main><a href="/labs/vision/student-projects/">Student projects</a></main>')
    result = discover_lab(make_fetcher(), lab())
    assert result.status == "found"
    assert result.url == "https://www.epfl.ch/labs/vision/student-projects/"


def test_discover_follows_medium_link_one_level(web, make_fetcher):
    web.add(HOME, '<main><a href="/labs/vision/join-us/">Join us</a></main>')
    web.add(
        HOME + "join-us/",
        '<main><a href="/labs/vision/join-us/semester-projects/">Semester projects</a></main>',
    )
    result = discover_lab(make_fetcher(), lab())
    assert result.status == "found"
    assert result.url.endswith("/join-us/semester-projects/")


def test_discover_medium_only_and_none(web, make_fetcher):
    web.add(HOME, '<main><a href="/labs/vision/join-us/">Join us</a></main>')
    web.add(HOME + "join-us/", "<main><p>We hire PhD students.</p></main>")
    result = discover_lab(make_fetcher(), lab())
    assert result.status == "found_medium" and result.url.endswith("/join-us/")

    web.add("https://other.epfl.ch/", "<main><a href='/pubs'>Publications</a></main>")
    assert discover_lab(make_fetcher(), lab("sti-o", "https://other.epfl.ch/")).status == "none"


def test_apply_result_flags_for_review(web, make_fetcher):
    web.add(HOME, '<main><a href="/labs/vision/student-projects/">Student projects</a></main>')
    x = lab()
    apply_result(x, discover_lab(make_fetcher(), x))
    assert x.projects_url.endswith("/student-projects/")
    assert "review" in x.notes and "high confidence" in x.notes


EPFL_LIST = """
<select id="select-institute"><option value="all">All</option><option value="IEM">IEM</option>
<option value="IA">IA</option></select>
<div class="site-row"><div class="site-title">ALCHEMY</div>
  <div><a class="site-url" href="https://www.epfl.ch/labs/alchemy/">
    <span class="site-tagline">Chemistry of Materials</span></a></div>
  <div class="site-tags" data-tags="STI;IEM;materials">
    <a class="site-tags-faculty">STI</a></div></div>
<div class="site-row"><div class="site-title">CVLAB</div>
  <div><a class="site-url" href="https://www.epfl.ch/labs/cvlab/">
    <span class="site-tagline">Computer Vision</span></a></div>
  <div class="site-tags" data-tags="IC"><a class="site-tags-faculty">IC</a></div></div>
"""


def test_parse_epfl_list_and_merge_keeps_existing():
    incoming = parse_epfl_labs_page(EPFL_LIST)
    alchemy = next(x for x in incoming if x.acronym == "ALCHEMY")
    assert alchemy.id == "sti-alchemy" and alchemy.institutes == ["IEM"]
    assert alchemy.homepage_url == "https://www.epfl.ch/labs/alchemy/"
    assert alchemy.projects_url is None

    existing = [
        Lab(
            id="ic-cvlab",
            acronym="CVLAB",
            name="Computer Vision",
            faculty="IC",
            projects_url="https://www.epfl.ch/labs/cvlab/projects/",
            notes="hand-made note",
        )
    ]
    merged, added, updated = merge_labs(existing, incoming)
    assert added == 1 and updated == 1
    cvlab = next(x for x in merged if x.id == "ic-cvlab")
    assert cvlab.projects_url == "https://www.epfl.ch/labs/cvlab/projects/"  # kept
    assert cvlab.notes == "hand-made note"  # kept
    assert cvlab.homepage_url == "https://www.epfl.ch/labs/cvlab/"  # added
    assert "epfl-all" in cvlab.listed_in


def test_malformed_href_is_ignored():
    html = '<a href="http://[bad/student-projects">Student projects</a>'
    html += '<a href="/labs/vision/student-projects/">Student projects</a>'
    assert [c.url for c in candidate_links(html, HOME)] == [
        "https://www.epfl.ch/labs/vision/student-projects/"
    ]
