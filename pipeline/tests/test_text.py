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


def test_site_scope_on_other_hosts_stays_in_page_folder():
    assert site_scope("https://dlab.epfl.ch/openings/") == ("dlab.epfl.ch", "/openings/")
    assert site_scope("https://indy.epfl.ch/projects") == ("indy.epfl.ch", "/")
    assert site_scope("http://bigwww.epfl.ch/teaching/projects/subject.html") == (
        "bigwww.epfl.ch",
        "/teaching/projects/",
    )


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


def test_find_subpage_links_skips_views_emails_ongoing_and_out_of_folder():
    page = "http://bigwww.epfl.ch/teaching/projects/subject.html"
    html = """
    <a href="subject.html?view=card">Card view of projects</a>
    <a href="abstract.html?f=00474">Phase retrieval project</a>
    <a href="ongoing.html">On-going projects</a>
    <a href="leyla.candogan@epfl.ch">Contact for the project</a>
    <a href="/tutorials/unser_mads_2020.pdf">Tutorial</a>
    <a href="/research/projects/">Research projects</a>
    """
    urls = [link.url for link in find_subpage_links(html, page)]
    assert urls == ["http://bigwww.epfl.ch/teaching/projects/abstract.html?f=00474"]


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


def test_find_subpage_links_treats_index_file_as_folder():
    html = '<a href="index.php?keyword=4">Robotics projects</a><a href="p.php?id=1">Project</a>'
    links = find_subpage_links(html, "https://biorob.epfl.ch/students/projects/")
    assert [link.url for link in links] == ["https://biorob.epfl.ch/students/projects/p.php?id=1"]


def test_page_title_is_prepended_when_missing_from_content():
    html = (
        "<html><head><title>INDY Lab - Probabilistic Proofs in Lean</title></head>"
        f"<body><main><p>{LONG}</p></main></body></html>"
    )
    text = html_to_text(html)
    assert text.splitlines()[0] == "INDY Lab - Probabilistic Proofs in Lean"
    assert "Federated learning" in text


def test_h1_outside_main_is_kept_and_title_not_duplicated():
    html = (
        "<html><head><title>Projects</title></head><body><h1>Drone perception</h1>"
        "<main><h2>Projects</h2><p>Short.</p></main></body></html>"
    )
    assert html_to_text(html).splitlines() == ["Drone perception", "Projects", "Short."]


def test_short_main_is_trusted_over_site_menus():
    html = (
        "<html><body><nav>" + "Menu item " * 100 + "</nav>"
        "<main><a href='a'>Master projects</a> <a href='b'>Bachelor projects</a></main>"
        "</body></html>"
    )
    assert "Menu item" not in html_to_text(html)


CARDS = """<html><head><title>INDY Lab - Projects</title></head><body>
<nav>Home Projects People</nav>
<ul><li><a href="#available">Available</a></li><li><a href="#ongoing">Ongoing</a></li></ul>
<div class="tab-content">
  <div class="tab-pane active" id="available">
    <div class="card"><h5 class="card-title"><a href="/project/82">Proofs in Lean</a></h5>
      <p>{long}</p></div>
    <div class="card"><h5 class="card-title"><a href="/project/81">Slow graph components</a></h5>
      <p>{long}</p></div>
    <div class="card"><h5 class="card-title"><a href="/project/80">AMG solver in JAX</a></h5>
      <p>{long}</p></div>
  </div>
  <div class="tab-pane" id="ongoing">
    <div class="card"><h5><a href="/project/12">Assigned project</a></h5><p>Student: John</p></div>
  </div>
  <div class="tab-pane" id="completed">
    <div class="card"><h5><a href="/project/3">Old project</a></h5></div>
  </div>
</div></body></html>""".replace("{long}", LONG)


def test_card_titles_kept_and_ongoing_completed_panes_removed():
    text = html_to_text(CARDS)
    for title in ("Proofs in Lean", "Slow graph components", "AMG solver in JAX"):
        assert title in text
    assert "Assigned project" not in text and "Old project" not in text
    assert "Student: John" not in text


def test_links_inside_ongoing_or_completed_panes_are_not_followed():
    urls = [link.url for link in find_subpage_links(CARDS, "https://indy.epfl.ch/projects")]
    assert urls == [
        "https://indy.epfl.ch/project/82",
        "https://indy.epfl.ch/project/81",
        "https://indy.epfl.ch/project/80",
    ]
