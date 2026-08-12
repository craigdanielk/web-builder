#!/usr/bin/env python3
"""Invariants for animation-coverage.json — the artifact stage_inject_animation
writes. These are the checks that make `injected` mean "a real library
component is rendering here" and nothing else; a coverage report that
violates any of these is lying about what the library contributed (see
task-7 brief: the original design could report full coverage while
injecting nothing).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import orchestrate  # noqa: E402  (adds parse_preset_intensity, stage_inject_animation)

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


# ── Fixture build: a small set of real section files in a scratch project ──
FIXTURE_PROJECT = "test-animation-coverage-fixture"
FIXTURE_DIR = orchestrate.OUTPUT_DIR / FIXTURE_PROJECT

WRAPPABLE_SECTION = """'use client';

import { motion } from 'framer-motion';

export default function HeroCentered() {
  return (
    <section className="py-24 bg-white">
      <motion.h1 initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Hello</motion.h1>
    </section>
  );
}
"""

UNWRAPPABLE_SECTION = """'use client';

export default function Bare() {
  return <div>no section root here</div>;
}
"""


def build_fixture():
    sections_dir = FIXTURE_DIR / "sections" / "home"
    art_dir = FIXTURE_DIR / "section-artifacts" / "home"
    sections_dir.mkdir(parents=True, exist_ok=True)
    art_dir.mkdir(parents=True, exist_ok=True)

    (sections_dir / "01-hero.tsx").write_text(WRAPPABLE_SECTION, encoding="utf-8")
    (art_dir / "01-hero.json").write_text(json.dumps({"archetype": "HOW-IT-WORKS"}), encoding="utf-8")

    (sections_dir / "02-bare.tsx").write_text(UNWRAPPABLE_SECTION, encoding="utf-8")
    (art_dir / "02-bare.json").write_text(json.dumps({"archetype": "HOW-IT-WORKS"}), encoding="utf-8")

    return [sections_dir / "01-hero.tsx", sections_dir / "02-bare.tsx"]


def cleanup_fixture():
    import shutil
    if FIXTURE_DIR.exists():
        shutil.rmtree(FIXTURE_DIR)


node_available = subprocess.run(["node", "--version"], capture_output=True).returncode == 0
test("node is available to drive component-inject.js", node_available)

if node_available:
    cleanup_fixture()
    section_files = build_fixture()

    tally = orchestrate.stage_inject_animation(FIXTURE_PROJECT, "home", section_files, "moderate")
    check_tally_shape(tally, "fixture (2 sections, 1 wrappable, 1 not)")

    test("fixture: exactly 2 sections seen", tally["total"] == 2, f"got {tally['total']}")
    test("fixture: the wrappable HOW-IT-WORKS section was injected",
         tally["injected"] == 1, f"got injected={tally['injected']}")
    test("fixture: the bare-div section was left unchanged with a reason",
         tally["unchanged"] == 1 and len(tally["by_reason"]) >= 1)

    hero_tsx = (FIXTURE_DIR / "sections" / "home" / "01-hero.tsx").read_text(encoding="utf-8")
    test("fixture: injected section actually changed on disk", hero_tsx != WRAPPABLE_SECTION)
    test("fixture: injected section still contains the original motion.h1 untouched",
         "initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Hello</motion.h1>" in hero_tsx)

    bare_tsx = (FIXTURE_DIR / "sections" / "home" / "02-bare.tsx").read_text(encoding="utf-8")
    test("fixture: refused section is byte-identical on disk", bare_tsx == UNWRAPPABLE_SECTION)

    coverage_path = FIXTURE_DIR / "animation-coverage.json"
    test("fixture: animation-coverage.json was written", coverage_path.exists())
    if coverage_path.exists():
        on_disk = json.loads(coverage_path.read_text(encoding="utf-8"))
        test("fixture: on-disk coverage matches the returned tally", on_disk == tally)

    extra_path = FIXTURE_DIR / "extra-components.json"
    test("fixture: extra-components.json queues the real component for stage_deploy",
         extra_path.exists() and len(json.loads(extra_path.read_text(encoding="utf-8"))) >= 1)

    # Re-running against the SAME already-wrapped file must refuse
    # (idempotence), not double-wrap or silently re-count as injected. The
    # returned tally MERGES across calls (multipage builds call this once
    # per page and accumulate), so the real signal is that `injected` does
    # NOT grow on the second pass — it stays at 1, not 2.
    tally2 = orchestrate.stage_inject_animation(FIXTURE_PROJECT, "home", section_files, "moderate")
    test("re-run over an already-wrapped section refuses rather than double-wrapping",
         tally2["injected"] == tally["injected"],
         f"got injected={tally2['injected']} on re-run, expected it to stay at {tally['injected']}")

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
