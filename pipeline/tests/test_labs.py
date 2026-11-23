from pipeline.labs import (
    dump_labs_yaml,
    guess_source_type,
    load_labs,
    parse_faculties,
    parse_labs_page,
)

PAGE = """
<html><body><main>
<table>
<tr><th>School</th><th>URL</th><th>Lab</th><th>Supervisor</th><th>IC Domain</th>
    <th>Research Interests</th></tr>
<tr><td>IC/SV<br>(joint)</td><td><a href="https://aimm.epfl.ch/openings/">AIMM</a></td>
    <td>AI in Molecular Medicine</td><td>Bunne, Charlotte</td><td>AIML, CV</td>
    <td>machine learning, biology</td></tr>
<tr><td>IC</td><td><a href="https://www.epfl.ch/labs/lap/students-projets/">LAP</a></td>
    <td>Processor Architecture</td><td>Ienne, Paolo</td><td>CAIS</td><td>FPGA</td></tr>
<tr><td>IC</td><td><a href="https://www.epfl.ch/labs/lap/students-projets/">LAP</a></td>
    <td>Processor Architecture</td><td>Kluter, Ties</td><td>CAIS</td><td>FPGA</td></tr>
<tr><td>IC</td><td>SIN-GE</td><td>Computer Science Section</td>
    <td><a href="https://people.epfl.ch/michel.schinz">Schinz, Michel</a></td>
    <td></td><td></td></tr>
<tr><td>IC</td><td>UPWEI</td><td>Security</td><td>Wei, Miranda<br>(starts Nov 2026)</td>
    <td>SP</td><td>security</td></tr>
</table>
<table>
<tr><th>School</th><th>URL</th><th>Lab</th><th>Supervisor</th><th>Research Interests</th></tr>
<tr><td>CDM</td><td><a href="https://www.epfl.ch/labs/entc/projects/">ENTC</a></td>
    <td>Entrepreneurship</td><td>Gruber, Marc<br>Bavato, Davide</td><td>innovation</td></tr>
<tr><td>ENT-R</td><td><a href="https://epflvita.notion.site/x">VITA</a></td>
    <td>Visual Intelligence</td><td>Alahi, Alexandre</td><td>robots</td></tr>
</table>
</main></body></html>
"""


def by_id(labs):
    return {lab.id: lab for lab in labs}


def test_parse_faculties():
    assert parse_faculties("IC/SV (joint)") == ("IC", ["SV"])
    assert parse_faculties("SB/IC (courtesy)") == ("SB", ["IC"])
    assert parse_faculties("ENT-R") == ("ENT", [])
    assert parse_faculties("") == ("OTHER", [])


def test_guess_source_type():
    assert guess_source_type(None) == "none"
    assert guess_source_type("https://people.epfl.ch/someone") == "none"
    assert guess_source_type("https://gitlab.epfl.ch/x/student-projects/") == "restricted"
    assert guess_source_type("https://lab.notion.site/projects") == "js_rendered"
    assert guess_source_type("https://www.epfl.ch/labs/cvlab/projects/") == "auto"


def test_parse_labs_page():
    labs = by_id(parse_labs_page(PAGE))
    assert set(labs) == {
        "ic-aimm",
        "ic-lap",
        "ic-sin-ge-schinz-michel",
        "ic-upwei",
        "cdm-entc",
        "ent-vita",
    }

    aimm = labs["ic-aimm"]
    assert aimm.joint_faculties == ["SV"]
    assert aimm.ic_domains == ["AIML", "CV"]
    assert aimm.projects_url == "https://aimm.epfl.ch/openings/"
    assert aimm.source_type == "auto"

    # duplicate rows of the same lab are merged
    assert labs["ic-lap"].heads == ["Ienne, Paolo", "Kluter, Ties"]
    # several supervisors separated by <br>
    assert labs["cdm-entc"].heads == ["Gruber, Marc", "Bavato, Davide"]
    # teacher without lab: personal page -> no public list
    schinz = labs["ic-sin-ge-schinz-michel"]
    assert schinz.source_type == "none"
    # remark in the supervisor cell becomes a note
    assert labs["ic-upwei"].heads == ["Wei, Miranda"]
    assert labs["ic-upwei"].notes == "starts Nov 2026"
    assert labs["ic-upwei"].source_type == "none"
    assert labs["ent-vita"].source_type == "js_rendered"


def test_yaml_roundtrip(tmp_path):
    labs = parse_labs_page(PAGE)
    path = tmp_path / "labs.yaml"
    dump_labs_yaml(labs, path)
    assert load_labs(path) == labs
    assert b"\r\n" not in path.read_bytes()
