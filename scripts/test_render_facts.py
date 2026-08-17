"""report.json gets a Python consumer.

C2 made the render probe measure horizontal overflow, rendered image boxes,
per-section image/background/fingerprint, sub-threshold blocks and the contrast
denominator — and serialised all of it to `render-audit-results/report.json`.
Nothing in Python read that file. `orchestrate.py` read only
`render-audit.json`'s defect summary, which is the shape C2 warned about:
facts written to disk and read by nobody are the same thing as a gate that can
only say yes.

Every check here has three outcomes. NOT_MEASURED is asserted separately from
PASS in each case, because the whole point of the facts is that a missing
measurement must not read as a clean one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from lib.render_facts import (  # noqa: E402
    NOT_MEASURED,
    FAIL,
    PASS,
    analyse_render_facts,
    read_render_facts,
)


def section(**kw):
    base = {
        "i": 0,
        "tag": "section",
        "cls": "",
        "selector": "section.hero",
        "h": 600,
        "w": 1440,
        "height": 600,
        "opacity": 1,
        "visible": True,
        "textLen": 400,
        "textFp": "aaaaaaaa",
        "imgCount": 1,
        "hasBg": False,
        "scrollWidth": 1440,
        "clientWidth": 1440,
        "overflowX": False,
        "belowThreshold": False,
        "invisible": False,
    }
    base.update(kw)
    return base


def image(**kw):
    base = {
        "kind": "img",
        "src": "/images/hero.png",
        "alt": "Hero",
        "selector": "img.hero",
        "loaded": True,
        "w": 1200,
        "h": 600,
        "rw": 600,
        "rh": 300,
        "objectFit": "fill",
        "onscreen": True,
    }
    base.update(kw)
    return base


def route(name="/", **facts):
    base_facts = {
        "page": {
            "scrollWidth": 1440,
            "clientWidth": 1440,
            "innerWidth": 1440,
            "scrollHeight": 4000,
            "overflowX": False,
        },
        "sections": [section()],
        "images": [image()],
        "navLinks": [],
        "lowContrast": [],
        "contrast": [],
        "contrastSummary": {"measured": 38, "passed": 38, "failed": 0},
        "textLen": 400,
    }
    base_facts.update(facts)
    return {"route": name, "url": f"http://127.0.0.1:3000{name}", "facts": base_facts}


def report(*routes):
    return {"schema": "aurelix.render_audit.v2", "routes": list(routes), "defects": []}


# ── the file itself ────────────────────────────────────────────────


def test_a_missing_report_is_not_measured(tmp_path):
    result = read_render_facts(tmp_path / "nope.json")
    assert result["status"] == NOT_MEASURED
    assert "report.json" in result["reason"]


def test_an_unparseable_report_is_not_measured(tmp_path):
    p = tmp_path / "report.json"
    p.write_text("{not json", encoding="utf-8")
    assert read_render_facts(p)["status"] == NOT_MEASURED


def test_a_report_with_no_routes_is_not_measured():
    assert analyse_render_facts(report())["status"] == NOT_MEASURED


def test_a_clean_report_passes():
    result = analyse_render_facts(report(route("/")))
    assert result["status"] == PASS, result
    assert result["routes_measured"] == 1


# ── horizontal overflow ────────────────────────────────────────────


def test_page_overflow_is_a_finding():
    r = route("/", page={"scrollWidth": 1600, "clientWidth": 1440, "overflowX": True})
    result = analyse_render_facts(report(r))
    check = result["checks"]["horizontal_overflow"]
    assert check["status"] == FAIL
    assert check["findings"][0]["route"] == "/"


def test_a_null_page_box_is_not_measured_not_passed():
    """The probe crashed before it recorded the page box."""
    r = route("/", page=None)
    check = analyse_render_facts(report(r))["checks"]["horizontal_overflow"]
    assert check["status"] == NOT_MEASURED, check
    assert check["status"] != PASS


def test_section_overflow_is_a_finding():
    r = route("/", sections=[section(overflowX=True, scrollWidth=1800)])
    check = analyse_render_facts(report(r))["checks"]["horizontal_overflow"]
    assert check["status"] == FAIL
    assert any(f.get("scope") == "section" for f in check["findings"])


# ── zero-dimension ─────────────────────────────────────────────────


def test_a_zero_height_block_is_a_finding():
    r = route("/", sections=[section(), section(i=1, h=0, height=0, belowThreshold=True)])
    check = analyse_render_facts(report(r))["checks"]["zero_dimension"]
    assert check["status"] == FAIL
    assert check["findings"][0]["h"] == 0


def test_a_sub_threshold_block_that_is_not_zero_is_a_candidate_not_a_finding():
    """belowThreshold exists to make 0px measurable, not to condemn a 20px rule."""
    r = route("/", sections=[section(), section(i=1, h=20, height=20, belowThreshold=True)])
    check = analyse_render_facts(report(r))["checks"]["zero_dimension"]
    assert check["status"] == PASS
    assert check["candidates"] == 1


def test_zero_dimension_is_not_measured_when_the_probe_predates_the_flag():
    s = section()
    del s["belowThreshold"]
    check = analyse_render_facts(report(route("/", sections=[s])))["checks"]["zero_dimension"]
    assert check["status"] == NOT_MEASURED


# ── empty sections ─────────────────────────────────────────────────


def test_a_section_with_no_text_no_image_and_no_background_is_a_finding():
    r = route("/", sections=[section(textLen=0, imgCount=0, hasBg=False)])
    check = analyse_render_facts(report(r))["checks"]["empty_section"]
    assert check["status"] == FAIL


def test_a_section_with_only_a_background_is_not_empty():
    r = route("/", sections=[section(textLen=0, imgCount=0, hasBg=True)])
    assert analyse_render_facts(report(r))["checks"]["empty_section"]["status"] == PASS


def test_empty_section_is_not_measured_without_imgcount():
    s = section(textLen=0)
    del s["imgCount"]
    del s["hasBg"]
    check = analyse_render_facts(report(route("/", sections=[s])))["checks"]["empty_section"]
    assert check["status"] == NOT_MEASURED


# ── aspect distortion ──────────────────────────────────────────────


def test_a_stretched_fill_image_is_a_finding():
    r = route("/", images=[image(w=1200, h=600, rw=600, rh=600, objectFit="fill")])
    check = analyse_render_facts(report(r))["checks"]["aspect_distortion"]
    assert check["status"] == FAIL
    assert check["findings"][0]["selector"] == "img.hero"


def test_a_cover_image_is_cropped_by_intent_not_distorted():
    r = route("/", images=[image(w=1200, h=600, rw=600, rh=600, objectFit="cover")])
    assert analyse_render_facts(report(r))["checks"]["aspect_distortion"]["status"] == PASS


def test_an_image_at_its_natural_ratio_passes():
    r = route("/", images=[image(w=1200, h=600, rw=600, rh=300, objectFit="fill")])
    assert analyse_render_facts(report(r))["checks"]["aspect_distortion"]["status"] == PASS


def test_aspect_distortion_is_not_measured_without_the_rendered_box():
    img = image()
    del img["rw"]
    del img["rh"]
    check = analyse_render_facts(report(route("/", images=[img])))["checks"]["aspect_distortion"]
    assert check["status"] == NOT_MEASURED


# ── contrast ───────────────────────────────────────────────────────


def test_contrast_failures_are_findings_carrying_the_repair_fields():
    r = route(
        "/",
        lowContrast=[
            {
                "selector": "p.muted",
                "tag": "p",
                "fg": "#9aa0a6",
                "bg": "#ffffff",
                "ratio": 2.4,
                "need": 4.5,
                "pass": False,
            }
        ],
        contrastSummary={"measured": 38, "passed": 37, "failed": 1},
    )
    check = analyse_render_facts(report(r))["checks"]["contrast"]
    assert check["status"] == FAIL
    assert check["measured"] == 38
    f = check["findings"][0]
    assert f["fg"] == "#9aa0a6" and f["bg"] == "#ffffff" and f["need"] == 4.5


def test_contrast_without_a_summary_is_not_measured_even_with_zero_failures():
    """'0 failures' off an absent denominator is the report nobody may trust."""
    r = route("/", contrastSummary=None, lowContrast=[])
    check = analyse_render_facts(report(r))["checks"]["contrast"]
    assert check["status"] == NOT_MEASURED


def test_contrast_with_a_measured_denominator_and_no_failures_passes():
    check = analyse_render_facts(report(route("/")))["checks"]["contrast"]
    assert check["status"] == PASS
    assert check["measured"] == 38 and check["failed"] == 0


# ── cross-route duplication ────────────────────────────────────────


def test_the_same_fingerprint_on_two_routes_is_a_finding():
    a = route("/", sections=[section(textFp="deadbeef", textLen=900)])
    b = route("/about", sections=[section(textFp="deadbeef", textLen=900)])
    check = analyse_render_facts(report(a, b))["checks"]["cross_route_duplication"]
    assert check["status"] == FAIL
    assert set(check["findings"][0]["routes"]) == {"/", "/about"}


def test_a_wrapper_and_its_inner_section_within_one_route_are_nesting_not_duplication():
    """C2's trap: section records include a wrapper div AND its inner <section>.

    Two routes, so the check is measurable; the repeated fingerprint is inside
    ONE of them, which is nesting and must not be reported.
    """
    a = route(
        "/",
        sections=[
            section(i=0, tag="div", textFp="deadbeef", textLen=900),
            section(i=1, tag="section", textFp="deadbeef", textLen=900),
        ],
    )
    b = route("/about", sections=[section(textFp="12345678", textLen=900)])
    check = analyse_render_facts(report(a, b))["checks"]["cross_route_duplication"]
    assert check["status"] == PASS, check


def test_short_shared_text_is_not_reported_as_duplication():
    a = route("/", sections=[section(textFp="cafe0000", textLen=12)])
    b = route("/about", sections=[section(textFp="cafe0000", textLen=12)])
    check = analyse_render_facts(report(a, b))["checks"]["cross_route_duplication"]
    assert check["status"] == PASS


def test_duplication_needs_two_routes_to_be_measured():
    check = analyse_render_facts(report(route("/")))["checks"]["cross_route_duplication"]
    assert check["status"] == NOT_MEASURED


# ── the aggregate ──────────────────────────────────────────────────


def test_one_failing_check_fails_the_whole_reading():
    r = route("/", page={"scrollWidth": 1600, "clientWidth": 1440, "overflowX": True})
    assert analyse_render_facts(report(r))["status"] == FAIL


def test_not_measured_does_not_become_a_pass_in_the_aggregate():
    """Every check unmeasurable => the reading is NOT_MEASURED, never PASS."""
    bare = {"route": "/", "facts": {"sections": [], "images": []}}
    result = analyse_render_facts({"schema": "aurelix.render_audit.v2", "routes": [bare]})
    assert result["status"] == NOT_MEASURED, result


def test_the_build_actually_calls_the_reader():
    """A reader nothing calls is the defect this task exists to remove.

    Asserted against stage_render_audit's own source, so deleting the call site
    fails here even though the reader's unit tests would stay green.
    """
    import ast

    src = (SCRIPTS / "orchestrate.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "stage_render_audit"
    )
    body = ast.unparse(fn)
    assert "read_render_facts(" in body, "stage_render_audit does not read report.json"
    assert "report.json" in body
    assert "render-facts.json" in body, "the reading is not recorded to disk"


def test_the_real_cape_crypto_report_is_readable_if_present():
    """Against the artifact on disk, not a fixture — read-only."""
    p = SCRIPTS.parent / "output" / "cape-crypto" / "render-audit-results" / "report.json"
    if not p.exists():
        pytest.skip("no cape-crypto report.json on disk")
    result = read_render_facts(p)
    assert result["status"] in (PASS, FAIL, NOT_MEASURED)
    assert set(result["checks"]) == {
        "horizontal_overflow",
        "zero_dimension",
        "empty_section",
        "aspect_distortion",
        "contrast",
        "cross_route_duplication",
    }
    # It is JSON-serialisable, because the build writes it back out.
    json.dumps(result)
