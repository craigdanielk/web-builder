#!/usr/bin/env python3
"""Invariants for the real-component-injection pipeline: stage_inject_animation()
(decides), animation-injections.json (the decision), animation-coverage.json
(the tally), and _build_page_imports() (assembly — the ONLY place a decision
becomes code).

PIVOT: an earlier version of stage_inject_animation() rewrote each section's
own .tsx in place by string-scanning for its root <section> element — the
same technique animation-apply.js's applyAnimation used, which failed three
review rounds (mismatched sibling-section tag pairing, apostrophes in
harvested copy, JSX expressions mistaken for tag boundaries) and was retired
from the pipeline. This suite now asserts the structural property that makes
that whole bug class unreachable: section .tsx files are BYTE-IDENTICAL
before and after the full decide -> assemble pipeline, because nothing in it
ever opens one for writing. The wrap only ever appears in generated page
code (`page.tsx` / `pages/{page_id}.tsx`), which this suite also verifies.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import orchestrate  # noqa: E402

ROOT = Path(__file__).parent
QUALITY_DIR = ROOT / "quality"

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


def check_tally_shape(tally: dict, label: str):
    test(f"{label}: has all required keys",
         {"total", "injected", "wrapped_generic", "unchanged", "by_component", "by_reason"} <= set(tally.keys()))
    test(f"{label}: injected + unchanged == total",
         tally["injected"] + tally["unchanged"] == tally["total"],
         f"got injected={tally['injected']} unchanged={tally['unchanged']} total={tally['total']}")
    test(f"{label}: wrapped_generic is always 0 — this stage never counts a generic fallback as injected",
         tally["wrapped_generic"] == 0, f"got {tally['wrapped_generic']}")
    test(f"{label}: by_component values sum to injected",
         sum(tally["by_component"].values()) == tally["injected"],
         f"sum={sum(tally['by_component'].values())} injected={tally['injected']}")
    test(f"{label}: by_reason values sum to unchanged",
         sum(tally["by_reason"].values()) == tally["unchanged"],
         f"sum={sum(tally['by_reason'].values())} unchanged={tally['unchanged']}")
    test(f"{label}: no negative counts",
         tally["total"] >= 0 and tally["injected"] >= 0 and tally["unchanged"] >= 0)


# ── Fixture build: a small set of section files in a scratch project ──
FIXTURE_PROJECT = "test-animation-coverage-fixture"
FIXTURE_DIR = orchestrate.OUTPUT_DIR / FIXTURE_PROJECT

# Deliberately messy JSX that would defeat a string-scanning insertion-point
# finder: an apostrophe in harvested prose, and a ternary containing `>` — the
# exact two shapes that broke applyAnimation in review. Assembly-level
# wrapping never looks inside this file at all, so neither should matter.
SECTION_TEMPLATE = """'use client';

import {{ motion }} from 'framer-motion';

export default function Section{n}() {{
  const width = 4;
  return (
    <section className="py-24 bg-white" data-x={{width > 2 ? 1 : 0}}>
      <motion.h1 initial={{{{ opacity: 0 }}}} animate={{{{ opacity: 1 }}}}>We've got answers #{n}</motion.h1>
    </section>
  );
}}
"""

# At `moderate` intensity, HOW-IT-WORKS's role fallback order (scroll ->
# entrance -> interactive -> ...) has exactly 4 safe, unused, real
# candidates available (fade-up-stagger, staggered-timeline, hover-glow,
# hover-lift — aurora-background is excluded, it derives 'dramatic'). 5
# identical-archetype sections forces the 5th to genuinely exhaust the pool,
# giving both a real "injected" case and a real "unchanged" case without
# needing a contrived per-section shape.
FIXTURE_SECTION_COUNT = 5


def build_fixture():
    sections_dir = FIXTURE_DIR / "sections" / "home"
    art_dir = FIXTURE_DIR / "section-artifacts" / "home"
    sections_dir.mkdir(parents=True, exist_ok=True)
    art_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for i in range(1, FIXTURE_SECTION_COUNT + 1):
        name = f"{i:02d}-section"
        (sections_dir / f"{name}.tsx").write_text(SECTION_TEMPLATE.format(n=i), encoding="utf-8")
        (art_dir / f"{name}.json").write_text(json.dumps({"archetype": "HOW-IT-WORKS"}), encoding="utf-8")
        files.append(sections_dir / f"{name}.tsx")
    return files


def cleanup_fixture():
    import shutil
    if FIXTURE_DIR.exists():
        shutil.rmtree(FIXTURE_DIR)


node_available = subprocess.run(["node", "--version"], capture_output=True).returncode == 0
test("node is available to drive component-inject.js", node_available)

if node_available:
    cleanup_fixture()
    section_files = build_fixture()
    original_bytes = {f: f.read_bytes() for f in section_files}

    tally = orchestrate.stage_inject_animation(FIXTURE_PROJECT, "home", section_files, "moderate")
    check_tally_shape(tally, f"fixture ({FIXTURE_SECTION_COUNT} sections, pool of 4 real components)")

    test(f"fixture: exactly {FIXTURE_SECTION_COUNT} sections seen", tally["total"] == FIXTURE_SECTION_COUNT,
         f"got {tally['total']}")
    test("fixture: the pool of 4 safe real components was fully decided",
         tally["injected"] == 4, f"got injected={tally['injected']}")
    test("fixture: the 5th section (pool exhausted) was left unchanged with a reason",
         tally["unchanged"] == 1 and len(tally["by_reason"]) >= 1)

    # ── The load-bearing structural guarantee ──
    for f in section_files:
        test(f"fixture: {f.name} is byte-identical after stage_inject_animation "
             f"(decision-only — never opens a section file for writing)",
             f.read_bytes() == original_bytes[f])

    injections_path = FIXTURE_DIR / "animation-injections.json"
    test("fixture: animation-injections.json was written", injections_path.exists())
    injections = {}
    if injections_path.exists():
        injections = json.loads(injections_path.read_text(encoding="utf-8"))
        test("fixture: decision is keyed 'home/01-section'", "home/01-section" in injections)
        test("fixture: decision carries export_name + dest_name",
             bool(injections.get("home/01-section", {}).get("export_name"))
             and bool(injections.get("home/01-section", {}).get("dest_name")))
        test("fixture: no decision recorded for the pool-exhausted 5th section",
             "home/05-section" not in injections)
        test("fixture: exactly 4 decisions recorded (matches injected count)",
             len(injections) == 4)

    coverage_path = FIXTURE_DIR / "animation-coverage.json"
    test("fixture: animation-coverage.json was written", coverage_path.exists())
    if coverage_path.exists():
        on_disk = json.loads(coverage_path.read_text(encoding="utf-8"))
        test("fixture: on-disk coverage matches the returned tally", on_disk == tally)

    extra_path = FIXTURE_DIR / "extra-components.json"
    test("fixture: extra-components.json queues the real component(s) for stage_deploy",
         extra_path.exists() and len(json.loads(extra_path.read_text(encoding="utf-8"))) == 4)

    # ── Assembly: the decision becomes code, and ONLY here ──
    animation_map = orchestrate.load_animation_injections(FIXTURE_PROJECT)
    imports, components = orchestrate._build_page_imports(
        section_files, "@/components/sections/home/", animation_map, "home"
    )
    page_code = "\n".join(imports) + "\n\n" + "\n".join(components)

    wrap = injections.get("home/01-section", {})
    wname = wrap.get("export_name")
    test("assembly: generated page imports the real library component",
         wname is not None and f'components/animations/{wrap.get("dest_name")}' in page_code)
    test("assembly: the decided section is wrapped in the component's JSX tags",
         wname is not None and f"<{wname}>" in page_code and f"</{wname}>" in page_code)
    test("assembly: the wrapped section still renders its own component invocation inside the wrap",
         wname is not None and "<Section01SECTION />" in page_code)
    # The pool-exhausted section must appear on its own line, not nested inside any wrapper tag.
    bare_line = next((ln for ln in components if "Section05SECTION" in ln), "")
    test("assembly: the unchanged section's JSX line is a bare self-closing tag (no wrapper)",
         bare_line.strip() == "<Section05SECTION />")

    # ── Regression: two DIFFERENT components sharing one export name ──
    # entrance__fade_up_stagger and entrance__staggered_timeline both export
    # `AnimatedGroup` from different files. An earlier version of
    # _build_page_imports deduped wrapper imports by export name alone, so
    # the second one silently collapsed into the first: the tally correctly
    # recorded staggered_timeline as used, but the generated page never
    # imported that file and wrapped the section in fade-up-stagger's code
    # instead. Sections 1 and 2 of this fixture are exactly that pair.
    animation_ids_used = {k: v["animation_id"] for k, v in injections.items()}
    export_names_used = {k: v["export_name"] for k, v in injections.items()}
    test("fixture: sections 1 and 2 got two DIFFERENT real components",
         animation_ids_used.get("home/01-section") != animation_ids_used.get("home/02-section"))
    test("fixture: those two different components share an export name (the exact collision case)",
         export_names_used.get("home/01-section") == export_names_used.get("home/02-section")
         == "AnimatedGroup")

    import_lines_for_animations = [ln for ln in imports if "components/animations/" in ln]
    test("regression: two distinct import paths were emitted for the two AnimatedGroup components",
         len({ln.split("from")[-1] for ln in import_lines_for_animations
              if "fade-up-stagger" in ln or "staggered-timeline" in ln}) == 2)
    fade_up_import = next((ln for ln in imports if "fade-up-stagger" in ln), "")
    staggered_import = next((ln for ln in imports if "staggered-timeline" in ln), "")
    test("regression: fade-up-stagger's AnimatedGroup keeps its own name",
         fade_up_import == 'import { AnimatedGroup } from "@/components/animations/fade-up-stagger";')
    test("regression: staggered-timeline's AnimatedGroup is imported under an alias, not dropped",
         staggered_import.startswith('import { AnimatedGroup as ')
         and 'staggered-timeline' in staggered_import)
    section2_line = next((ln for ln in components if "Section02SECTION" in ln), "")
    test("regression: section 2's wrap tag uses the ALIASED local name, not the collided 'AnimatedGroup'",
         "<AnimatedGroup>" not in section2_line and "AnimatedGroup" in section2_line)

    # ── CRITICAL regression: re-running the SAME page against the SAME
    # output dir (a resumed/retried build — `--skip-to sections`, a normal
    # pattern this repo's own CLAUDE.md documents) must not double the
    # coverage numbers. An earlier version read animation-coverage.json and
    # ADDED this page's numbers onto whatever was already on disk: a second
    # run on an already-populated output dir doubled `total`/`unchanged`
    # while `injected` stayed flat — the file whose entire job is to stop a
    # number overstating reality was itself producing one. No cleanup
    # between these two calls — that's the point.
    coverage_first = json.loads((FIXTURE_DIR / "animation-coverage.json").read_text(encoding="utf-8"))
    tally_rerun = orchestrate.stage_inject_animation(FIXTURE_PROJECT, "home", section_files, "moderate")
    coverage_second = json.loads((FIXTURE_DIR / "animation-coverage.json").read_text(encoding="utf-8"))

    test("idempotence: total is identical across two runs on the same output dir (no doubling)",
         coverage_first["total"] == coverage_second["total"] == FIXTURE_SECTION_COUNT,
         f"first={coverage_first['total']} second={coverage_second['total']}")
    test("idempotence: injected is identical across two runs on the same output dir",
         coverage_first["injected"] == coverage_second["injected"] == 4,
         f"first={coverage_first['injected']} second={coverage_second['injected']}")
    test("idempotence: unchanged is identical across two runs on the same output dir",
         coverage_first["unchanged"] == coverage_second["unchanged"] == 1,
         f"first={coverage_first['unchanged']} second={coverage_second['unchanged']}")
    test("idempotence: returned value matches the on-disk aggregate on the second run too",
         tally_rerun == coverage_second)

    print("\n  === animation-coverage.json — run 1 ===")
    print(json.dumps(coverage_first, indent=2))
    print("\n  === animation-coverage.json — run 2 (same output dir, no cleanup) ===")
    print(json.dumps(coverage_second, indent=2))

    # ── Determinism: re-deciding the same input yields the same decisions ──
    cleanup_fixture()
    section_files2 = build_fixture()
    tally_a = orchestrate.stage_inject_animation(FIXTURE_PROJECT, "home", section_files2, "moderate")
    decisions_a = json.loads((FIXTURE_DIR / "animation-injections.json").read_text(encoding="utf-8"))
    cleanup_fixture()
    section_files3 = build_fixture()
    tally_b = orchestrate.stage_inject_animation(FIXTURE_PROJECT, "home", section_files3, "moderate")
    decisions_b = json.loads((FIXTURE_DIR / "animation-injections.json").read_text(encoding="utf-8"))
    test("decision is deterministic: same inputs, same animation_id chosen per section",
         decisions_a == decisions_b)
    test("decision is deterministic: injected count matches across identical runs",
         tally_a["injected"] == tally_b["injected"])

    cleanup_fixture()

# ── If a real build already has a coverage file on disk, validate it too ──
for candidate in orchestrate.OUTPUT_DIR.glob("*/animation-coverage.json"):
    try:
        real_tally = json.loads(candidate.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        continue
    check_tally_shape(real_tally, f"real build: {candidate.parent.name}")

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)
