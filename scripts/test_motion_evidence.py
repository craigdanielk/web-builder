"""The corpus's animation evidence must reach the compiled style, unaltered.

WHAT WAS WRONG
--------------
`design_system.compile_style()` emitted `libraries: [], keyframes: [],
durations: [], easings: []` — four hardcoded empty lists. The corpus behind the
benchmark has carried all four since capture: per page, `libraries[]` with
confidence and `detectedVia`, `cssKeyframes[]` with bodies, and every
intercepted GSAP call's duration and ease. The commissioner lowered
`motion.intensity` and threw the rest away, so a build could not have known the
reference site used GSAP, ScrollTrigger, SplitText, Draggable, Inertia,
Observer, CustomEase and Lottie even though the file on disk said so.

These tests read the corpus themselves and compare. They never assert a
hardcoded expectation of what the corpus contains — a test that pins
"8 libraries" passes just as well against a lowering that invented eight.

Run: `python3 -m pytest scripts/test_motion_evidence.py -v` from web-builder/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WEB_BUILDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB_BUILDER / "scripts"))

from lib.design_system import compile_style, load_benchmark  # noqa: E402

MEASURED = WEB_BUILDER / "benchmarks" / "enterprise-stablecoin-payments-measured.json"
NO_CORPUS = WEB_BUILDER / "benchmarks" / "enterprise-payments-bvnk.json"
EVIDENCE_KEYS = ("libraries", "keyframes", "durations", "easings")


def _animation(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"no benchmark at {path}")
    return compile_style(load_benchmark(path))["animation"]


def _corpus_pages(benchmark_path: Path) -> list[Path]:
    corpus = (json.loads(benchmark_path.read_text(encoding="utf-8"))
              .get("_meta") or {}).get("corpus")
    if not corpus:
        pytest.skip(f"{benchmark_path.name} declares no _meta.corpus")
    pages = sorted((WEB_BUILDER / corpus).glob("*/extraction.json"))
    if not pages:
        pytest.skip(f"no page extractions under {corpus}")
    return pages


def _corpus_evidence(benchmark_path: Path) -> list[dict]:
    out = []
    for p in _corpus_pages(benchmark_path):
        data = json.loads(p.read_text(encoding="utf-8"))
        out.append((data.get("animations") or {}).get("evidence") or {})
    return out


# ---------------------------------------------------------------------------
# The measured branch
# ---------------------------------------------------------------------------


def test_every_library_the_corpus_detected_reaches_the_style():
    """Not "some libraries" — the exact set, both directions.

    A subset assertion would pass a lowering that dropped Lottie; a superset
    assertion would pass one that invented a library.
    """
    anim = _animation(MEASURED)
    in_corpus = {
        lib["name"]
        for ev in _corpus_evidence(MEASURED)
        for lib in (ev.get("libraries") or [])
        if lib.get("name")
    }
    assert in_corpus, "fixture assumption: the corpus must detect some libraries"
    assert {l["name"] for l in anim["libraries"]} == in_corpus


def test_library_confidence_and_detection_method_are_carried_not_dropped():
    """The census names confidence and detectedVia as measured. Both must survive."""
    anim = _animation(MEASURED)
    by_name = {
        lib["name"]: lib
        for ev in _corpus_evidence(MEASURED)
        for lib in (ev.get("libraries") or [])
        if lib.get("name")
    }
    for lowered in anim["libraries"]:
        source = by_name[lowered["name"]]
        assert lowered["confidence"] == source["confidence"]
        assert source["detectedVia"] in lowered["detected_via"]
        assert lowered["pages"], "a lowered library must name the pages it came from"


def test_keyframes_are_carried_with_their_bodies():
    anim = _animation(MEASURED)
    in_corpus = {
        (kf["name"], kf["body"])
        for ev in _corpus_evidence(MEASURED)
        for kf in (ev.get("cssKeyframes") or [])
        if kf.get("name") and kf.get("body")
    }
    assert in_corpus, "fixture assumption: the corpus must carry css keyframes"
    assert {(k["name"], k["body"]) for k in anim["keyframes"]} == in_corpus


def test_durations_and_easings_are_the_intercepted_gsap_calls():
    """Counted, not averaged, and not filtered.

    The corpus contains a 60000ms marquee alongside 300ms micro-transitions;
    an average of the two describes nothing that happens on the page. It also
    contains `e.ease||`, a fragment of minified source the extractor captured
    as an easing — that stays visible rather than being quietly dropped.
    """
    anim = _animation(MEASURED)
    durations: dict[int, int] = {}
    easings: dict[str, int] = {}
    for ev in _corpus_evidence(MEASURED):
        for call in ev.get("gsapCalls") or []:
            for node in [call] + list(call.get("steps") or []):
                secs = node.get("duration")
                if isinstance(secs, (int, float)) and not isinstance(secs, bool):
                    ms = int(round(secs * 1000))
                    durations[ms] = durations.get(ms, 0) + 1
                ease = node.get("ease")
                if isinstance(ease, str) and ease:
                    easings[ease] = easings.get(ease, 0) + 1
    assert durations and easings, "fixture assumption: the corpus must carry gsap calls"
    assert {d["ms"]: d["count"] for d in anim["durations"]} == durations
    assert {e["name"]: e["count"] for e in anim["easings"]} == easings


def test_no_evidence_field_is_still_hardcoded_empty():
    """The defect itself: four keys that existed and were always [].

    This is the assertion that fails if any one of them is reverted.
    """
    anim = _animation(MEASURED)
    empty = [k for k in EVIDENCE_KEYS if not anim.get(k)]
    assert not empty, (
        f"{empty} are empty on a benchmark whose corpus carries them — "
        "the fields are hardcoded again"
    )


def test_the_style_names_where_the_evidence_came_from():
    anim = _animation(MEASURED)
    assert anim["evidence_source"] == (
        json.loads(MEASURED.read_text(encoding="utf-8"))["_meta"]["corpus"]
    )
    assert anim["evidence_pages"] == sorted(p.parent.name for p in _corpus_pages(MEASURED))


# ---------------------------------------------------------------------------
# The NOT_MEASURED branch
# ---------------------------------------------------------------------------


def test_a_benchmark_with_no_corpus_reports_not_measured_and_omits_the_fields():
    """An empty list reads as "measured, found none". That is the lie to avoid.

    `enterprise-payments-bvnk.json` is the RATIFIED benchmark and declares no
    `_meta.corpus`, so its animation evidence genuinely cannot be re-read. The
    four keys are absent, and `evidence_source` says so.
    """
    anim = _animation(NO_CORPUS)
    assert anim["evidence_source"].startswith("NOT_MEASURED")
    assert "_meta.corpus" in anim["evidence_source"]
    for key in EVIDENCE_KEYS:
        assert key not in anim, f"{key} was emitted on an unmeasured benchmark"
    # The measured half of motion still comes through — this is not a refusal.
    assert anim["intensity"]
    assert anim["engine"]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_the_same_corpus_produces_byte_identical_output():
    a = json.dumps(_animation(MEASURED), sort_keys=False)
    b = json.dumps(_animation(MEASURED), sort_keys=False)
    assert a == b


def test_every_lowered_collection_is_totally_ordered():
    """Determinism has to be structural, not a lucky dict iteration order."""
    anim = _animation(MEASURED)
    assert anim["libraries"] == sorted(anim["libraries"], key=lambda x: x["name"])
    assert anim["keyframes"] == sorted(anim["keyframes"], key=lambda x: (x["name"], x["body"]))
    assert anim["durations"] == sorted(anim["durations"], key=lambda x: x["ms"])
    assert anim["easings"] == sorted(anim["easings"], key=lambda x: (-x["count"], x["name"]))
    for lib in anim["libraries"]:
        assert lib["detected_via"] == sorted(lib["detected_via"])
        assert lib["pages"] == sorted(lib["pages"])
