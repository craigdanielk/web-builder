#!/usr/bin/env python3
"""Invariants for `commission_benchmark.py` — the benchmark producer recovered
from `9805e275^` and parameterised.

FIXTURES ARE LOCAL AND SYNTHETIC. No network, no Playwright, no external site
is touched. The fixture recipe is the census's (`docs/census/
2026-08-17-benchmark-production.md` §4): a hand-built extraction in
`extract-reference.js`'s shape — `renderedDOM[].{styles,rect}`,
`textContent[].{styles,isHeading}`, `assets.fonts`, plus the
`animations.profile` block the capture step writes.

WHAT IS GUARDED
  1. determinism      — two runs over the same corpus produce identical bytes
  2. the refusal gate — MIN_BANDING fires as NOT_MEASURED, exit 3, nothing
                        written. This is the gate the ratified BVNK file
                        violates (census §3.1) and that must not be relaxed
  3. honesty          — every unmeasurable field is ABSENT and named in
                        `_unmeasured`, never defaulted
  4. corpus           — the capture directory is persisted and named in `_meta`

Run: python3 scripts/test_commission_benchmark.py     (exit 0 = green)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from commission_benchmark import (  # noqa: E402
    EXIT_NOT_MEASURED,
    MIN_BANDING,
    NotMeasured,
    commission,
    contrast,
)

WEB_BUILDER = HERE.parent
PRODUCER = HERE / "commission_benchmark.py"
CAPTURE_JS = HERE / "quality" / "capture-benchmark-pages.js"

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f"\n         {detail}" if detail else ""))


# ── fixture: an extraction in extract-reference.js's shape ───────────────────
def _el(bg=None, *, w=1200, h=400, radius=None, pad=None, gap=None,
        border=None, bw=None, shadow=None):
    styles = {}
    if bg:
        styles["backgroundColor"] = bg
    if radius is not None:
        styles["borderRadius"] = f"{radius}px"
    if pad is not None:
        styles["padding"] = f"{pad}px 24px"
    if gap is not None:
        styles["gap"] = f"{gap}px"
    if border:
        styles["borderColor"] = border
        styles["borderWidth"] = f"{bw or 1}px"
    if shadow:
        styles["boxShadow"] = shadow
    return {"styles": styles, "rect": {"width": w, "height": h}}


def _text(colour, size, weight, *, heading=False, family="Circular"):
    return {
        "isHeading": heading,
        "styles": {"color": colour, "fontSize": f"{size}px",
                   "fontWeight": str(weight), "fontFamily": f'"{family}", sans-serif'},
    }


#: A light palette whose banding step clears MIN_BANDING and whose text clears
#: AA. Chosen by computing the ratios, not by eye — the assertions below
#: recompute them so a fixture that stops satisfying the premise fails loudly.
BG_PRIMARY = "rgb(255, 255, 255)"
BG_BANDING = "rgb(226, 232, 240)"
SURFACE = "rgb(244, 246, 248)"
TEXT_PRIMARY = "rgb(26, 34, 48)"
TEXT_MUTED = "rgb(74, 90, 106)"
BORDER_SEP = "rgb(223, 228, 234)"
#: On a light ground an *emphasis* outline is the DARK one — it is what
#: exceeds MAX_SEPARATOR_CONTRAST against #ffffff. (On the dark Robinhood
#: reference the same role was filled by a neon #ccff00 CTA ring.)
BORDER_EMPHASIS = "rgb(0, 51, 102)"


def _extraction(*, banding: str, with_profile: bool = True) -> dict:
    dom = []
    dom += [_el(BG_PRIMARY, w=1400, h=600) for _ in range(30)]
    dom += [_el(banding, w=1400, h=500) for _ in range(12)]
    # rounded card backgrounds -> surface, card_pad_px, card radius
    dom += [_el(SURFACE, w=380, h=240, radius=16, pad=40) for _ in range(18)]
    dom += [_el(SURFACE, w=380, h=240, radius=24, pad=40) for _ in range(6)]
    # full-width blocks -> section_py_px (modal 120, runner-up 180)
    dom += [_el(BG_PRIMARY, w=1400, h=900, pad=120) for _ in range(13)]
    dom += [_el(BG_PRIMARY, w=1400, h=900, pad=180) for _ in range(9)]
    # gaps -> block_gap_px
    dom += [_el(BG_PRIMARY, w=1200, h=300, gap=24) for _ in range(20)]
    dom += [_el(BG_PRIMARY, w=1200, h=300, gap=16) for _ in range(7)]
    # buttons -> cta radius
    dom += [_el(BG_PRIMARY, w=180, h=48, radius=100) for _ in range(11)]
    # borders: separators plus one emphasis outline that must be excluded
    dom += [_el(BG_PRIMARY, w=1200, h=100, border=BORDER_SEP, bw=1)
            for _ in range(9)]
    dom += [_el(BG_PRIMARY, w=200, h=52, border=BORDER_EMPHASIS, bw=2)
            for _ in range(14)]
    # shadows
    dom += [_el(SURFACE, w=380, h=240, radius=16,
                shadow="rgba(0, 0, 0, 0.08) 0px 2px 8px 0px") for _ in range(5)]

    text = []
    text += [_text(TEXT_PRIMARY, 16, 400) for _ in range(40)]
    text += [_text(TEXT_MUTED, 14, 400) for _ in range(22)]
    text += [_text(TEXT_PRIMARY, 20, 600, heading=True) for _ in range(9)]
    text += [_text(TEXT_PRIMARY, 32, 600, heading=True) for _ in range(6)]
    text += [_text(TEXT_PRIMARY, 52, 600, heading=True) for _ in range(4)]
    # a single 165px outlier: the walker's most_common(8) trim hid one of these
    text += [_text(TEXT_PRIMARY, 165, 600, heading=True)]

    extraction = {
        "url": "https://fixture.invalid/",
        "renderedDOM": dom,
        "textContent": text,
        "assets": {"fonts": ["Circular", "Circular"]},
        "sections": [],
    }
    if with_profile:
        extraction["animations"] = {
            "evidence": {},
            "profile": {
                "libraries": [{"name": "GSAP", "version": "3.14", "confidence": 1},
                              {"name": "Lottie", "version": None, "confidence": 0.7}],
                "intensity": {"level": "expressive", "score": 39.2,
                              "confidence": 1.0},
                "engine": "gsap",
            },
        }
    return extraction


def build_corpus(root: Path, *, banding: str, pages=("home", "about"),
                 with_profile: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    index = []
    for slug in pages:
        (root / slug).mkdir(parents=True, exist_ok=True)
        (root / slug / "extraction.json").write_text(
            json.dumps(_extraction(banding=banding, with_profile=with_profile),
                       indent=2),
            encoding="utf-8")
        index.append({"slug": slug, "url": f"https://fixture.invalid/{slug}",
                      "why": f"{slug.upper()} archetypes", "ok": True})
    (root / "index.json").write_text(json.dumps(index, indent=2),
                                     encoding="utf-8")
    return root


ARGS = dict(market="fixture-market", captured_at="2026-08-17",
            reference_host="fixture.invalid")


# ── 0. the fixture satisfies its own premise ─────────────────────────────────
print("\n0. fixture premise (recomputed, not asserted by eye)")
_HEX = {"rgb(255, 255, 255)": "#ffffff", "rgb(226, 232, 240)": "#e2e8f0",
        "rgb(26, 34, 48)": "#1a2230", "rgb(253, 253, 253)": "#fdfdfd"}
step = contrast(_HEX[BG_BANDING], _HEX[BG_PRIMARY])
test("the good fixture's banding clears MIN_BANDING",
     step >= MIN_BANDING, f"{step:.3f} vs {MIN_BANDING}")
test("the good fixture's text clears AA on its banding",
     contrast(_HEX[TEXT_PRIMARY], _HEX[BG_BANDING]) >= 4.5,
     f"{contrast(_HEX[TEXT_PRIMARY], _HEX[BG_BANDING]):.2f}:1")
flat = contrast(_HEX["rgb(253, 253, 253)"], _HEX[BG_PRIMARY])
test("the refusal fixture's banding is BELOW MIN_BANDING",
     flat < MIN_BANDING, f"{flat:.3f} vs {MIN_BANDING}")

tmp = Path(tempfile.mkdtemp(prefix="commission-benchmark-test-"))
try:
    good = build_corpus(tmp / "good", banding=BG_BANDING)
    b = commission(good, corpus_ref="benchmarks/corpora/fixture-market", **ARGS)

    # ── 1. determinism ───────────────────────────────────────────────────────
    print("\n1. determinism — same corpus, same bytes")
    a1 = json.dumps(commission(good, corpus_ref="benchmarks/corpora/"
                               "fixture-market", **ARGS), indent=2)
    a2 = json.dumps(commission(good, corpus_ref="benchmarks/corpora/"
                               "fixture-market", **ARGS), indent=2)
    test("two in-process runs are byte-identical", a1 == a2)

    out1, out2 = tmp / "one.json", tmp / "two.json"
    for out in (out1, out2):
        r = subprocess.run(
            [sys.executable, str(PRODUCER), str(good), "--market",
             "fixture-market", "--captured-at", "2026-08-17",
             "--reference-host", "fixture.invalid", "--out", str(out)],
            capture_output=True, text=True)
        test(f"CLI run exits 0 ({out.name})", r.returncode == 0,
             r.stderr[-500:])
    test("two CLI runs are byte-identical",
         out1.read_bytes() == out2.read_bytes())
    test("captured_at is the passed value, never the clock",
         json.loads(out1.read_text())["_meta"]["captured_at"] == "2026-08-17")

    # reordering the corpus index must not change the output
    idx = json.loads((good / "index.json").read_text())
    (good / "index.json").write_text(json.dumps(list(reversed(idx)), indent=2))
    reordered = json.dumps(commission(good, corpus_ref="benchmarks/corpora/"
                                      "fixture-market", **ARGS), indent=2)
    (good / "index.json").write_text(json.dumps(idx, indent=2))
    test("index order does not change the output", reordered == a1)

    # ── 2. the refusal gates ─────────────────────────────────────────────────
    print("\n2. refusal gates — NOT_MEASURED, exit 3, nothing written")
    flat_corpus = build_corpus(tmp / "flat", banding="rgb(253, 253, 253)")
    raised = None
    try:
        commission(flat_corpus, **ARGS)
    except NotMeasured as exc:
        raised = str(exc)
    test("MIN_BANDING refusal raises NotMeasured", raised is not None,
         "a fixture whose only banding candidate is #fdfdfd compiled anyway")
    test("the refusal names the gate and the remedy",
         bool(raised) and "banding" in raised and "Widen the capture" in raised,
         raised)

    refused_out = tmp / "refused.json"
    r = subprocess.run(
        [sys.executable, str(PRODUCER), str(flat_corpus), "--market",
         "fixture-market", "--captured-at", "2026-08-17", "--out",
         str(refused_out)],
        capture_output=True, text=True)
    test("the CLI exits 3 on the refusal (not 0, not 1)",
         r.returncode == EXIT_NOT_MEASURED, f"exit {r.returncode}")
    test("NOT_MEASURED appears on stderr", "NOT_MEASURED" in r.stderr, r.stderr)
    test("nothing is written on a refusal", not refused_out.exists())

    # text-contrast refusal: every measured text colour is unreadable
    unreadable = build_corpus(tmp / "unreadable", banding=BG_BANDING)
    for slug in ("home", "about"):
        p = unreadable / slug / "extraction.json"
        d = json.loads(p.read_text())
        for t in d["textContent"]:
            t["styles"]["color"] = "rgb(250, 250, 250)"
        p.write_text(json.dumps(d, indent=2))
    raised2 = None
    try:
        commission(unreadable, **ARGS)
    except NotMeasured as exc:
        raised2 = str(exc)
    test("the 4.5:1 text refusal fires", raised2 is not None)
    test("it names the threshold and refuses to darken",
         bool(raised2) and "4.5:1" in raised2 and "darkening" in raised2,
         raised2)

    # ── 3. honesty — unmeasurable fields are ABSENT ───────────────────────────
    print("\n3. unmeasurable fields are absent, not defaulted")
    test("density is absent", "density" not in b)
    test("palette_roles.surface_inverse is absent",
         "surface_inverse" not in b["palette_roles"])
    test("palette_roles.accent is absent without --tenant-accent",
         "accent" not in b["palette_roles"])
    test("palette_roles.on_accent is absent without --tenant-accent",
         "on_accent" not in b["palette_roles"])
    test("font_system.families is absent",
         "families" not in b["font_system"])
    test("font_system.measured_families IS emitted",
         b["font_system"]["measured_families"] == ["Circular"],
         b["font_system"]["measured_families"])
    test("motion.duration_ms is absent",
         "duration_ms" not in b["motion"])

    names = {u["field"] for u in b["_unmeasured"]}
    for field in ("density", "palette_roles.surface_inverse",
                  "palette_roles.accent", "palette_roles.on_accent",
                  "font_system.families", "motion.duration_ms"):
        test(f"_unmeasured names {field}", field in names, sorted(names))
    test("every _unmeasured entry carries a reason and a resolution",
         all(u.get("reason") and u.get("resolution") for u in b["_unmeasured"]))

    test("ratified is stamped false", b["_meta"]["ratified"] is False)
    test("the tool identity is stamped",
         b["_meta"]["tool"]["name"] == "commission_benchmark.py"
         and "extract-reference.js" in b["_meta"]["tool"]["extractor"])
    test("the reference host is stamped",
         b["_meta"]["reference_host"] == "fixture.invalid")
    test("captured_from lists the captured URLs",
         b["_meta"]["captured_from"] == ["https://fixture.invalid/about",
                                         "https://fixture.invalid/home"],
         b["_meta"]["captured_from"])
    test("page_selection_rationale carries every page's why",
         all(b["_meta"]["page_selection_rationale"].get(s)
             for s in ("home", "about")))

    # the strict build-side loader must REFUSE an unratified benchmark, by name
    sys.path.insert(0, str(HERE))
    from lib.design_system import BenchmarkError, load_benchmark  # noqa: E402
    unratified = tmp / "unratified.json"
    unratified.write_text(json.dumps(b, indent=2))
    loader_error = None
    try:
        load_benchmark(unratified)
    except BenchmarkError as exc:
        loader_error = str(exc)
    test("design_system.load_benchmark refuses the unratified file",
         loader_error is not None)
    test("it refuses by naming the fields ratification must supply",
         bool(loader_error) and "density" in loader_error
         and "palette_roles.accent" in loader_error, loader_error)

    # ── 4. corpus persistence ────────────────────────────────────────────────
    print("\n4. the corpus is persisted and named in _meta")
    test("the corpus directory exists", good.is_dir())
    test("_meta.corpus names it",
         b["_meta"]["corpus"] == "benchmarks/corpora/fixture-market",
         b["_meta"]["corpus"])
    cli = json.loads(out1.read_text())
    test("the CLI stamps a repo-relative corpus path when it can",
         cli["_meta"]["corpus"] == str(good.resolve()),
         cli["_meta"]["corpus"])
    test("the capture step defaults the corpus under benchmarks/corpora/",
         "'benchmarks', 'corpora', args.market" in CAPTURE_JS.read_text(),
         "capture-benchmark-pages.js no longer writes a named in-repo corpus")
    test("the capture step requires `why`",
         '"why" is required' in CAPTURE_JS.read_text())
    test("the capture step wires the animation detector",
         "analyzeAnimationEvidence(" in CAPTURE_JS.read_text())

    # ── 5. the measured half ─────────────────────────────────────────────────
    print("\n5. the measured half is measured")
    roles = b["palette_roles"]
    test("bg_primary is the modal opaque background",
         roles["bg_primary"] == "#ffffff", roles["bg_primary"])
    test("bg_secondary is the banding colour", roles["bg_secondary"] == "#e2e8f0",
         roles["bg_secondary"])
    test("surface is the rounded-element background",
         roles["surface"] == "#f4f6f8", roles["surface"])
    test("text_primary / text_muted are the AA-clearing text colours",
         (roles["text_primary"], roles["text_muted"]) == ("#1a2230", "#4a5a6a"),
         (roles["text_primary"], roles["text_muted"]))
    test("border is the separator, not the neon emphasis outline",
         roles["border"] == "#dfe4ea", roles["border"])
    test("the excluded emphasis outline is recorded",
         "#003366" in roles["_source"].get("_border_emphasis_excluded", ""),
         roles["_source"].get("_border_emphasis_excluded"))
    test("every provenance string names the reference host, not 'robinhood'",
         all("fixture.invalid" in v for k, v in roles["_source"].items()
             if k in ("bg_primary", "bg_secondary", "text_primary",
                      "text_muted", "border"))
         and not any("robinhood" in v for v in roles["_source"].values()),
         roles["_source"])

    test("type_scale is measured",
         b["type_scale"] == {"ratio": 1.625, "base_px": 16,
                             "heading_weight": 600, "body_weight": 400},
         b["type_scale"])
    test("rhythm is measured",
         b["rhythm"]["section_py_px"] == 120
         and b["rhythm"]["block_gap_px"] == 24
         and b["rhythm"]["card_pad_px"] == 40
         and b["rhythm"]["grid_px"] == 8,
         b["rhythm"])
    test("card and cta radii are measured",
         b["card_system"]["radius_px"] == [16, 24]
         and b["cta_buttons"]["radius_px"] == [100],
         (b["card_system"], b["cta_buttons"]))
    test("motion.intensity comes from the detector, not a duration histogram",
         b["motion"]["intensity"] == "expressive"
         and b["motion"]["evidence"]["score"] == 39.2
         and "analyzeAnimationEvidence" in b["motion"]["_source"]["intensity"],
         b["motion"])

    # ── 6. distributions, not silent picks ───────────────────────────────────
    print("\n6. full distributions are emitted, not silent modal picks")
    test("the section padding distribution shows the 180px runner-up",
         b["_distributions"]["section_py_px"] == {"120": 26, "180": 18},
         b["_distributions"]["section_py_px"])
    test("_source.section_py_px surfaces the runner-up for ratification",
         "180px on 18" in b["rhythm"]["_source"]["section_py_px"],
         b["rhythm"]["_source"]["section_py_px"])
    test("the heading-size distribution carries the 165px outlier",
         b["_distributions"]["heading_sizes_px"].get("165.0") == 2,
         b["_distributions"]["heading_sizes_px"])
    test("heading_sizes_px is the full ladder, not a most_common(8) trim",
         b["type_system"]["heading_sizes_px"] == [20, 32, 52, 165],
         b["type_system"]["heading_sizes_px"])
    test("card_pad_px distribution backs the absent density field",
         b["_distributions"]["card_pad_px"] == {"40": 48},
         b["_distributions"]["card_pad_px"])

    # ── 7. elements_measured is defined ──────────────────────────────────────
    print("\n7. _meta.elements_measured states what it counts")
    em = b["_meta"]["elements_measured"]
    test("it separates DOM elements from text nodes",
         em["renderedDOM_elements"] == 308 and em["text_nodes"] == 164, em)
    test("it declares the per-page DOM cap", em["per_page_dom_cap"] == 500)
    test("it carries a definition naming both quantities and the cap",
         "renderedDOM" in em["definition"] and "text_nodes" in em["definition"]
         and "per_page_dom_cap" in em["definition"])
    test("it does not exceed pages * cap",
         em["renderedDOM_elements"] <= em["pages"] * em["per_page_dom_cap"], em)

    # ── 8. accent is declared, never measured ────────────────────────────────
    print("\n8. tenant accent is declared or absent")
    d = commission(good, tenant_accent="#004e89", **ARGS)
    test("--tenant-accent emits accent", d["palette_roles"]["accent"] == "#004e89")
    test("on_accent is derived for contrast",
         d["palette_roles"]["on_accent"] == "#ffffff")
    test("the accent provenance says DECLARED, not measured",
         "DECLARED" in d["palette_roles"]["_source"]["accent"]
         and "NOT measured" in d["palette_roles"]["_source"]["accent"],
         d["palette_roles"]["_source"]["accent"])
    test("accent no longer appears in _unmeasured",
         "palette_roles.accent" not in {u["field"] for u in d["_unmeasured"]})

    # ── 9. a corpus that measured nothing refuses ────────────────────────────
    print("\n9. an unmeasurable corpus refuses rather than writing")
    empty = tmp / "empty"
    (empty / "home").mkdir(parents=True)
    (empty / "home" / "extraction.json").write_text(
        json.dumps({"renderedDOM": [], "textContent": []}))
    (empty / "index.json").write_text(json.dumps(
        [{"slug": "home", "url": "https://fixture.invalid/", "why": "x",
          "ok": True}]))
    raised3 = None
    try:
        commission(empty, **ARGS)
    except NotMeasured as exc:
        raised3 = str(exc)
    test("an empty extraction refuses", raised3 is not None, raised3)

    nocaps = tmp / "nocaps"
    nocaps.mkdir()
    (nocaps / "index.json").write_text(json.dumps(
        [{"slug": "home", "url": "https://fixture.invalid/", "why": "x",
          "ok": False, "error": "timeout"}]))
    raised4 = None
    try:
        commission(nocaps, **ARGS)
    except NotMeasured as exc:
        raised4 = str(exc)
    test("a corpus with 0 ok pages refuses, naming the count",
         bool(raised4) and "0 with ok=true" in raised4, raised4)

    # ── 10. a corpus with no animation profile says so ───────────────────────
    print("\n10. a missing animation profile is NOT_MEASURED, not 'subtle'")
    noprof = build_corpus(tmp / "noprof", banding=BG_BANDING,
                          with_profile=False)
    n = commission(noprof, **ARGS)
    test("motion is absent entirely", "motion" not in n)
    test("_unmeasured names motion.intensity",
         "motion.intensity" in {u["field"] for u in n["_unmeasured"]},
         sorted(u["field"] for u in n["_unmeasured"]))
    test("no intensity was guessed from a CSS duration histogram",
         "subtle" not in json.dumps(n))

    # ── 11. usage errors are 64, not 3 ───────────────────────────────────────
    print("\n11. usage errors are distinguishable from refusals")
    r = subprocess.run(
        [sys.executable, str(PRODUCER), str(good), "--market", "m",
         "--captured-at", "today", "--out", str(tmp / "x.json")],
        capture_output=True, text=True)
    test("a non-ISO --captured-at exits 64", r.returncode == 64,
         f"exit {r.returncode}")
    r = subprocess.run(
        [sys.executable, str(PRODUCER), str(good), "--market", "m",
         "--captured-at", "2026-08-17", "--tenant-accent", "blue",
         "--out", str(tmp / "x.json")],
        capture_output=True, text=True)
    test("a non-hex --tenant-accent exits 64", r.returncode == 64,
         f"exit {r.returncode}")

    # ── 12. the ground is elected by painted area, not element count ─────────
    #
    # Measured on the real BVNK corpus: `#f1f7ff` sits on 15 elements, every
    # one of them rounded (a card tint), while `#ffffff` sits on 10 and covers
    # 22x the painted area. Count-election returned the card tint as the page
    # ground, and the bg_secondary gate then correctly refused the whole corpus
    # because nothing was both a visible step from a card tint and readable
    # against the measured text. The fixture below reproduces that shape: the
    # tint wins on count 30:6, white wins on area by ~19x.
    print("\n12. bg_primary is the ground, not the most-repeated tint")
    tint = "rgb(241, 247, 255)"
    dom = ([_el(BG_PRIMARY, w=1400, h=2400) for _ in range(6)]
           + [_el(tint, w=380, h=240, radius=16, pad=40) for _ in range(30)]
           + [_el(BG_BANDING, w=1400, h=500) for _ in range(4)])
    area_ex = {
        "renderedDOM": dom,
        "textContent": [_text(TEXT_PRIMARY, 16, 400) for _ in range(40)]
        + [_text(TEXT_MUTED, 14, 400) for _ in range(6)]
        + [_text(TEXT_PRIMARY, 48, 600, heading=True) for _ in range(8)]
        + [_text(TEXT_PRIMARY, 32, 600, heading=True) for _ in range(6)],
        "assets": {"fonts": ["Circular"]},
        "animations": {"profile": {
            "intensity": {"level": "expressive", "score": 39.2,
                          "confidence": 1.0}, "engine": "gsap"}},
    }
    area_root = tmp / "area"
    (area_root / "home").mkdir(parents=True, exist_ok=True)
    (area_root / "home" / "extraction.json").write_text(
        json.dumps(area_ex, indent=2), encoding="utf-8")
    (area_root / "index.json").write_text(json.dumps(
        [{"slug": "home", "url": "https://fixture.invalid/home",
          "why": "HERO", "ok": True}], indent=2), encoding="utf-8")
    ab = commission(area_root, corpus_ref="benchmarks/corpora/area", **ARGS)
    adist = ab["_distributions"]
    test("the fixture's tint really does win on element count",
         adist["backgrounds"]["#f1f7ff"] > adist["backgrounds"]["#ffffff"],
         adist["backgrounds"])
    test("bg_primary is the area winner, not the count winner",
         ab["palette_roles"]["bg_primary"] == "#ffffff",
         ab["palette_roles"]["bg_primary"])
    test("the count winner is elected as surface instead",
         ab["palette_roles"]["surface"] == "#f1f7ff",
         ab["palette_roles"]["surface"])
    test("the provenance states the area AND the element count",
         ("px^2" in ab["palette_roles"]["_source"]["bg_primary"]
          and "elements" in ab["palette_roles"]["_source"]["bg_primary"]),
         ab["palette_roles"]["_source"]["bg_primary"])
    test("both distributions are emitted so the election is auditable",
         adist["background_area_px2"]["#ffffff"]
         > adist["background_area_px2"]["#f1f7ff"],
         adist["background_area_px2"])

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
