"""Corpus sections carry an archetype, or say NOT_MEASURED — never a guess.

WHY THIS DRIVES NODE RATHER THAN REIMPLEMENTING THE CLASSIFIER
--------------------------------------------------------------
The classifier is `mapSectionsToArchetypes()` in
`scripts/quality/lib/archetype-mapper.js`, and the annotation wrapper
`annotateSectionArchetypes()` sits directly on top of it. A Python
reimplementation of the heuristics would be a test of the reimplementation.
These tests call the real function the way `extract-reference.js` calls it.

WHAT IS ACTUALLY GUARDED
------------------------
`mapSectionsToArchetypes` never returns null: its last branch assigns FEATURES
at 0.30 confidence with method `fallback`. Used unfiltered it stamps a guess
onto the corpus that is indistinguishable from a measurement. The invariant
below is therefore the whole point:

    no section may carry a non-null `archetype` at a confidence below the
    threshold, on any corpus, ever.

Run: `python3 -m pytest scripts/test_corpus_archetypes.py -v` from web-builder/.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

WEB_BUILDER = Path(__file__).resolve().parent.parent
QUALITY_DIR = WEB_BUILDER / "scripts" / "quality"
BVNK_CORPUS = (
    WEB_BUILDER / "benchmarks" / "corpora" / "enterprise-stablecoin-payments-measured"
)

THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Driving the real annotator
# ---------------------------------------------------------------------------

_NODE_ANNOTATE = """
const { annotateSectionArchetypes } = require('./lib/archetype-mapper');
const input = %s;
console.log(JSON.stringify(annotateSectionArchetypes(input.sections, input.textContent)));
"""


def annotate(sections: list[dict], text_content: list[dict] | None = None) -> dict:
    payload = json.dumps({"sections": sections, "textContent": text_content or []})
    proc = subprocess.run(
        ["node", "-e", _NODE_ANNOTATE % payload],
        cwd=QUALITY_DIR,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def section(index: int, **kw) -> dict:
    """A corpus section record in the shape extract-reference.js writes."""
    rec = {
        "index": index,
        "tag": "section",
        "id": "",
        "classNames": "",
        "role": "",
        "label": "",
        "rect": {"x": 0, "y": index * 800, "width": 1440, "height": 800},
        "content": {"headings": [], "body_text": [], "ctas": [], "image_count": 0},
        "images": [],
    }
    rec.update(kw)
    return rec


# ---------------------------------------------------------------------------
# The record shape
# ---------------------------------------------------------------------------


def test_annotation_is_one_to_one_with_input():
    """Deduplication would drop records; the annotation must stay aligned.

    Adjacent sections that classify to the same non-FEATURES archetype are
    exactly what the mapper's dedupe path collapses (FEATURES is exempt there,
    so a FEATURES run would not exercise this). A collapsed list silently
    re-indexes every section after it, so section 4's archetype would end up
    describing section 2's DOM.
    """
    secs = [
        section(0, classNames="hero"),
        section(1, classNames="faq"),
        section(2, classNames="faq"),
        section(3, classNames="faq"),
        section(4, classNames="pricing"),
    ]
    out = annotate(secs)
    assert len(out["sections"]) == 5
    assert [s["index"] for s in out["sections"]] == [0, 1, 2, 3, 4]
    assert out["sections"][4]["archetype"] == "PRICING"


def test_original_fields_survive_annotation():
    secs = [section(0, classNames="hero", label="Money unlocked.", id="top")]
    out = annotate(secs)["sections"][0]
    for key in ("index", "tag", "id", "classNames", "role", "label", "rect",
                "content", "images"):
        assert key in out, f"annotation dropped {key}"
    assert out["label"] == "Money unlocked."
    assert out["id"] == "top"


def test_measured_section_carries_archetype_and_variant():
    out = annotate([section(0, classNames="hero")])["sections"][0]
    assert out["archetype_status"] == "MEASURED"
    assert out["archetype"] == "HERO"
    assert out["archetype_variant"]
    assert out["archetype_confidence"] >= THRESHOLD
    assert out["archetype_method"]
    assert "archetype_below_threshold" not in out


def test_unclassifiable_section_is_not_measured_not_a_default():
    """The fallback branch must not reach the corpus as a claim.

    A mid-page section with no class signal, no label, no headings and no
    images is exactly what `mapSectionsToArchetypes` assigns FEATURES at 0.30.
    """
    secs = [
        section(0, classNames="hero"),
        section(1),
        section(2, classNames="faq"),
    ]
    out = annotate(secs)["sections"][1]
    assert out["archetype_status"] == "NOT_MEASURED"
    assert out["archetype"] is None
    assert out["archetype_variant"] is None
    # The rejected candidate is kept as evidence, under a name that cannot be
    # mistaken for a claim.
    assert out["archetype_below_threshold"]["archetype"] == "FEATURES"
    assert out["archetype_below_threshold"]["confidence"] < THRESHOLD
    assert out["archetype_method"] == "fallback"


def test_counts_partition_the_sections():
    secs = [section(0, classNames="hero"), section(1), section(2, classNames="faq")]
    out = annotate(secs)
    assert out["measured"] + out["notMeasured"] == len(secs)
    assert out["minConfidence"] == THRESHOLD


def test_threshold_is_configurable_and_lowering_it_admits_the_guess():
    """A threshold nobody can move is a constant pretending to be a policy."""
    payload = json.dumps({"sections": [section(0, classNames="hero"), section(1)]})
    src = (
        "const { annotateSectionArchetypes } = require('./lib/archetype-mapper');\n"
        f"const input = {payload};\n"
        "console.log(JSON.stringify(annotateSectionArchetypes("
        "input.sections, [], { minConfidence: 0.1 })));"
    )
    proc = subprocess.run(["node", "-e", src], cwd=QUALITY_DIR,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["notMeasured"] == 0
    assert out["sections"][1]["archetype_status"] == "MEASURED"


# ---------------------------------------------------------------------------
# The invariant, on the real persisted corpus
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not BVNK_CORPUS.is_dir(), reason="BVNK corpus not on disk")
def test_bvnk_corpus_classifies_every_page():
    index = json.loads((BVNK_CORPUS / "index.json").read_text())
    proc = subprocess.run(
        ["node", "annotate-corpus-archetypes.js", str(BVNK_CORPUS), "--json"],
        cwd=QUALITY_DIR,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert len(report["pages"]) == len(index)
    for page in report["pages"]:
        assert page["status"] == "MEASURED", page
        assert page["section_count"] == len(page["sequence"])
        assert page["measured"] + page["not_measured"] == page["section_count"]


@pytest.mark.skipif(not BVNK_CORPUS.is_dir(), reason="BVNK corpus not on disk")
def test_no_corpus_section_claims_an_archetype_below_threshold():
    """The honesty invariant, asserted over every section of every page."""
    proc = subprocess.run(
        ["node", "annotate-corpus-archetypes.js", str(BVNK_CORPUS), "--json"],
        cwd=QUALITY_DIR,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    offenders = [
        (page["slug"], s)
        for page in report["pages"]
        for s in page["sequence"]
        if s["archetype"] is not None and s["confidence"] < THRESHOLD
    ]
    assert not offenders, f"archetype claimed below threshold: {offenders}"

    not_measured = [
        (page["slug"], s)
        for page in report["pages"]
        for s in page["sequence"]
        if s["status"] == "NOT_MEASURED" and s["archetype"] is not None
    ]
    assert not not_measured, f"NOT_MEASURED section carries an archetype: {not_measured}"


@pytest.mark.skipif(not BVNK_CORPUS.is_dir(), reason="BVNK corpus not on disk")
def test_corpus_sequences_are_ordered_by_dom_position():
    """A sequence whose order is not the page's order is not a sequence."""
    proc = subprocess.run(
        ["node", "annotate-corpus-archetypes.js", str(BVNK_CORPUS), "--json"],
        cwd=QUALITY_DIR,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    for page in report["pages"]:
        indices = [s["index"] for s in page["sequence"]]
        assert indices == sorted(indices), page["slug"]
