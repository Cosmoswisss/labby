from pipeline.text import (
    content_hash,
    find_subpage_links,
    html_to_text,
    in_scope,
    looks_like_login,
    normalize_text,
    site_scope,
)

LONG = "Federated learning across hospitals without sharing patient data. " * 5

EPFL_PAGE = f"""
<html><body>
<header><nav>EPFL menu Education Research</nav></header>
<main>
  <nav class="breadcrumb">Home > Labs > CVLAB</nav>
  <h1>Student projects</h1>
  <h2>Project A</h2><p>{LONG}</p>
  <script>var x = 1;</script>
  <aside>Lab menu</aside>
</main>
<footer>Contact EPFL</footer>
</body></html>
"""


def test_html_to_text_keeps_main_content_only():
    text = html_to_text(EPFL_PAGE)
    assert "Project A" in text and "Federated learning" in text
    for noise in ("EPFL menu", "breadcrumb", "Home > Labs", "var x", "Lab menu", "Contact EPFL"):
        assert noise not in text


def test_html_without_main_falls_back():
    html = f"<html><body><div><h1>Projects</h1><p>{LONG}</p></div></body></html>"
    assert "Federated learning" in html_to_text(html)


def test_hash_ignores_whitespace_changes():
    assert content_hash("Project A\n\n  details ") == content_hash("Project A\ndetails")
    assert content_hash("Project A") != content_hash("Project B")


def test_normalize_text():
    assert normalize_text("  a \xa0 b\n\n\n c  ") == "a b\nc"


def test_site_scope_on_epfl_www_stays_in_lab_folder():
    assert site_scope("https://www.epfl.ch/labs/cvlab/projects/") == ("www.epfl.ch", "/labs/cvlab/")
    assert site_scope("https://www.epfl.ch/schools/ic/ipg/proposed-projects/") == (
        "www.epfl.ch",
        "/schools/ic/ipg/",
    )
    assert site_scope("https://dlab.epfl.ch/openings/") == ("dlab.epfl.ch", "/")


def test_in_scope():
    scope = ("www.epfl.ch", "/labs/cvlab/")
    assert in_scope("https://www.epfl.ch/labs/cvlab/projects/x/", scope)
    assert in_scope("https://www.epfl.ch/labs/cvlab", scope)
    assert not in_scope("https://www.epfl.ch/labs/other/projects/", scope)
    assert not in_scope("https://www.epfl.ch/education/", scope)


def test_find_subpage_links_filters_scope_archives_and_duplicates():
    html = """
    <a href="/labs/cvlab/projects/kite">Kite tracking</a>
    <a href="/labs/cvlab/projects/kite/">Kite tracking (again)</a>
    <a href="/labs/cvlab/projects/completed-projects/">Completed projects</a>
    <a href="/labs/cvlab/past/">Previous student projects</a>
    <a href="/labs/cvlab/files/offer.pdf">Offer (PDF)</a>
    <a href="/labs/cvlab/people/">People</a>
    <a href="/labs/other-lab/projects/">Another lab</a>
    <a href="https://github.com/x/projects">GitHub</a>
    <a href="mailto:someone@epfl.ch">Mail</a>
    <a href="#top">Top</a>
    <a href="/labs/cvlab/feed/">Feed</a>
    """
    links = find_subpage_links(html, "https://www.epfl.ch/labs/cvlab/projects/")
    urls = [link.url for link in links]
    assert urls == [
        "https://www.epfl.ch/labs/cvlab/projects/kite",
        "https://www.epfl.ch/labs/cvlab/files/offer.pdf",
    ]


def test_find_subpage_links_uses_anchor_text():
    html = '<a href="/labs/lcn/student-html/page-28063-en-html/">Semester Projects</a>'
    links = find_subpage_links(html, "https://www.epfl.ch/labs/lcn/student-html/")
    assert len(links) == 1


def test_find_subpage_links_respects_limit():
    html = "".join(f'<a href="/labs/x/projects/p{i}">Project {i}</a>' for i in range(40))
    assert len(find_subpage_links(html, "https://www.epfl.ch/labs/x/projects/", limit=5)) == 5


def test_looks_like_login():
    assert looks_like_login("https://gitlab.epfl.ch/users/sign_in")
    assert looks_like_login("https://sb-projects.epfl.ch/en/login/?next=/en/")
    assert looks_like_login("https://tequila.epfl.ch/cgi-bin/tequila/auth")
    assert not looks_like_login("https://www.epfl.ch/labs/cvlab/projects/")
    assert not looks_like_login(None)
