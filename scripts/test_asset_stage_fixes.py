#!/usr/bin/env python3
"""Regression tests for Task 9 fix round 1 (two Criticals).

Critical 1: a registry gap-fill section must never be assigned a
FABRICATED `section_index` (its list position, "j", from
stage_sections_multipage's reconciled-sections loop). `j` and a real
extraction-crawl sectionIndex are different numbering spaces that happen
to overlap in small integers — a gap-fill landing at the same position as
a real crawl index can bind a real, correctly-downloaded extracted image
to a section that was never harvested and never asked for it.

Critical 2: `stage_resolve_assets` must degrade toward RETRY, not toward
silent permanent divergence, if the process dies between writing the
sibling .tsx and writing the artifact JSON that (via a non-empty `assets`
list) marks a section as already resolved.

No pytest — plain PASS/FAIL harness matching this repo's convention.
Python 3.9-compatible. No network (download_fn is monkeypatched).
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "lib"))

import orchestrate  # noqa: E402
from lib.section_artifact import SectionArtifact  # noqa: E402
import lib.asset_resolver as ar  # noqa: E402

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


TMP_ROOT = Path("/private/tmp/claude-501/-Users-craigkunte-Developer-GitHub-services-aurelix-ag"
                 "/2e699588-fe6c-49c4-a52f-a2a0b5536ac4/scratchpad/test-asset-stage-fixes")


def _fresh(name: str) -> Path:
    d = TMP_ROOT / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return d


def _fake_download(url, dest):
    """Deterministic local 'download': valid PNG magic bytes, no network."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    return dest.stat().st_size


def _patched_resolve_assets_default():
    """Swap resolve_assets' bound default download_fn for the fake one, for
    the duration of a call. Needed because orchestrate.stage_resolve_assets
    doesn't expose a download_fn override — it calls Task 8's resolve_assets
    with its own default. Returns the original defaults tuple to restore."""
    old_defaults = ar.resolve_assets.__defaults__
    ar.resolve_assets.__defaults__ = (old_defaults[0], _fake_download)
    return old_defaults


# ─────────────────────────────────────────────────────────────────────────
# CRITICAL 1: gap-fill sections must not inherit a fabricated section_index
# ─────────────────────────────────────────────────────────────────────────
print("\nCritical 1: gap-fill section_index is never a fabricated position\n")

proj1 = _fresh("critical1")

# `extraction_data` carries exactly one section-scoped image, tagged with
# sectionIndex 1. Nothing in this build's real harvest has crawl index 1 —
# only the HERO does (index 0). If a gap-fill section's fabricated index
# (its list position) happened to be 1, the OLD code would incorrectly let
# it claim this image via resolve_assets' section-scoped fill.
extraction_data_c1 = {
    "assets": {
        "images": [
            {"src": "https://example.com/should-not-leak.png", "alt": "", "sectionIndex": 1},
        ]
    }
}

# Section 0: harvested HERO, real crawl index 0 (site-spec.json's own key —
# survives reconcile_page_sections unchanged).
hero_section = {"archetype": "HERO", "variant": "split", "content": {}, "index": 0}

# Section 1 (by LIST POSITION): a registry gap-fill. reconcile_page_sections
# never sets "index" on a gap-fill (get_section_sequence() only carries
# "position"; the gap-fill branch does `gap = dict(sec)` with no "index"
# key added) — so this section, as it really looks post-reconciliation, has
# NO "index" key at all.
gapfill_section = {"archetype": "ABOUT", "variant": "editorial", "content": {}}

raw_sections = [hero_section, gapfill_section]

# Call the REAL production transform — stage_sections_multipage's loop now
# just does `[_normalize_reconciled_section(s, j) for j, s in enumerate(...)]`,
# so this test exercises the actual function, not a hand-copied replica of
# it (a replica would keep passing even if the real function regressed).
sections_with_index = [
    orchestrate._normalize_reconciled_section(s, j) for j, s in enumerate(raw_sections)
]

test(
    "gap-fill section carries no 'index' key after the loop (not fabricated to its position)",
    "index" not in sections_with_index[1],
    str(sections_with_index[1]),
)
test(
    "harvested section's real crawl index (0) survives the loop untouched",
    sections_with_index[0].get("index") == 0,
)

# Now run each section through the REAL _emit_section_artifact +
# resolve_assets (Task 8/9's actual production functions, not a
# reimplementation) exactly as stage_sections() does per section.
sec_page_dir = proj1 / "sections" / "about"
sec_page_dir.mkdir(parents=True)

# _emit_section_artifact writes under OUTPUT_DIR / project_name / ..., not
# under our tmp dir directly — point OUTPUT_DIR at our scratch root for this
# call so the real function's paths land where the test expects.
old_output_dir = orchestrate.OUTPUT_DIR
orchestrate.OUTPUT_DIR = proj1.parent
for i, sec in enumerate(sections_with_index):
    fname = f"{i + 1:02d}-{sec['archetype'].lower()}.tsx"
    tsx = '<section><img src="/placeholder.svg" alt="" /></section>'
    (sec_page_dir / fname).write_text(tsx)
    orchestrate._emit_section_artifact(
        project_name="critical1",
        page_dir="about",
        out_name=fname,
        tsx=tsx,
        section=sec,
        section_uid=orchestrate.section_identity(sec, i),
        intensity="moderate",
        origin="llm",
        provenance=[],
    )
orchestrate.OUTPUT_DIR = old_output_dir

hero_artifact = json.loads((proj1 / "section-artifacts" / "about" / "01-hero.json").read_text())
gapfill_artifact = json.loads((proj1 / "section-artifacts" / "about" / "02-about.json").read_text())

test("HERO artifact.section_index == 0 (real crawl index threaded through)",
     hero_artifact["section_index"] == 0, str(hero_artifact["section_index"]))
test("gap-fill artifact.section_index is None (never fabricated)",
     gapfill_artifact["section_index"] is None, str(gapfill_artifact["section_index"]))

old_defaults = _patched_resolve_assets_default()
counts_c1 = orchestrate.stage_resolve_assets(proj1, extraction_data_c1)
ar.resolve_assets.__defaults__ = old_defaults

gapfill_after = json.loads((proj1 / "section-artifacts" / "about" / "02-about.json").read_text())
gapfill_origins = [a["origin"] for a in gapfill_after["assets"]]
gapfill_tsx = (proj1 / "sections" / "about" / "02-about.tsx").read_text()

test("gap-fill resolves NO image (no 'extracted' origin in its assets)",
     "extracted" not in gapfill_origins, str(gapfill_after["assets"]))
test("gap-fill's placeholder src is untouched (never bound to the sectionIndex=1 image)",
     'src="/placeholder.svg"' in gapfill_tsx, gapfill_tsx)
test("gap-fill's slot is recorded unresolved, not silently dropped",
     gapfill_origins == ["unresolved"], str(gapfill_origins))


# ─────────────────────────────────────────────────────────────────────────
# CRITICAL 2: a crash between the .tsx write and the artifact write must
# degrade toward retry, not permanent divergence.
# ─────────────────────────────────────────────────────────────────────────
print("\nCritical 2: interrupted write degrades toward retry, not divergence\n")


def _setup_unresolved_artifact(proj: Path, page: str, fname_stem: str, tsx: str):
    art_dir = proj / "section-artifacts" / page
    # Mirrors stage_resolve_assets' own page_dir == "sections" flat-case
    # rule: a single-page build's .tsx sits directly under sections/, not
    # nested under sections/sections/.
    sec_dir = proj / "sections" if page == "sections" else proj / "sections" / page
    art_dir.mkdir(parents=True, exist_ok=True)
    sec_dir.mkdir(parents=True, exist_ok=True)
    art = SectionArtifact(
        tsx=tsx, archetype="LOGO-BAR", variant="strip", section_uid="u1",
        intensity="moderate", origin="llm", section_index=0,
    )
    (art_dir / f"{fname_stem}.json").write_text(json.dumps(art.to_dict(), indent=2))
    (sec_dir / f"{fname_stem}.tsx").write_text(tsx)
    return art_dir / f"{fname_stem}.json", sec_dir / f"{fname_stem}.tsx"


extraction_data_c2 = {
    "assets": {"images": [{"src": "https://example.com/logo.png", "alt": "", "sectionIndex": 0}]}
}
tsx_c2 = '<section><img src="https://example.com/logo.png" alt="" /></section>'

# Scenario A: NEW (fixed) order. Simulate a crash that happens AFTER the
# .tsx write but BEFORE the artifact write, by writing the resolved .tsx by
# hand and leaving the artifact JSON in its original, unresolved state
# (assets == []) — exactly what a real interruption under the fixed
# ordering leaves behind.
projA = _fresh("critical2_new_order")
art_path_a, tsx_path_a = _setup_unresolved_artifact(projA, "sections", "01-logo_bar", tsx_c2)
# The resolved local path is content-addressed (see asset_resolver's
# `_local_rel_path` — collision-proofing hashes the full URL, not just the
# basename), so derive it the same way rather than guessing a filename.
_expected_local_rel = ar._local_rel_path("https://example.com/logo.png")
tsx_path_a.write_text(f'<section><img src="/{_expected_local_rel}" alt="" /></section>')  # tsx already rewritten
# artifact JSON left untouched: still assets == [] (the crash point)

old_defaults = _patched_resolve_assets_default()
old_output_dir = orchestrate.OUTPUT_DIR
orchestrate.OUTPUT_DIR = projA.parent
counts_a = orchestrate.stage_resolve_assets(projA, extraction_data_c2)
orchestrate.OUTPUT_DIR = old_output_dir
ar.resolve_assets.__defaults__ = old_defaults

art_after_a = json.loads(art_path_a.read_text())
tsx_after_a = tsx_path_a.read_text()

test("rerun after an interrupted .tsx-then-artifact write RESOLVES the artifact (converges, not stuck)",
     bool(art_after_a["assets"]) and art_after_a["assets"][0]["origin"] == "extracted",
     str(art_after_a["assets"]))
test("rerun leaves the .tsx pointing at the real resolved local path",
     "/images/" in tsx_after_a and "example.com" not in tsx_after_a,
     tsx_after_a)
test("artifact and .tsx agree with each other after convergence (artifact.tsx == sections/*.tsx)",
     art_after_a["tsx"] == tsx_after_a, "artifact/tsx mismatch after convergence")

# Scenario B (documents the OLD, now-impossible-by-construction failure
# mode): if the artifact were written first and the .tsx write never
# happened, the guard's "assets non-empty -> already resolved, skip" check
# means a rerun can NEVER repair the stale .tsx — it is invisible to the
# idempotency guard forever. This demonstrates why write order, not the
# guard, is what has to prevent that state from ever being reached.
projB = _fresh("critical2_old_order_would_strand")
art_path_b, tsx_path_b = _setup_unresolved_artifact(projB, "sections", "01-logo_bar", tsx_c2)
# Hand-construct the OLD order's crash state: artifact ALREADY marked
# resolved (non-empty assets, rewritten tsx field) but the standalone .tsx
# file on disk was never updated (still the stale remote URL).
_expected_local_rel_b = ar._local_rel_path("https://example.com/logo.png")
stale_resolved_artifact = SectionArtifact(
    tsx=f'<section><img src="/{_expected_local_rel_b}" alt="" /></section>',
    archetype="LOGO-BAR", variant="strip", section_uid="u1", intensity="moderate",
    origin="llm", section_index=0,
    assets=[{"slot": "image", "src": f"/{_expected_local_rel_b}", "origin": "extracted", "bytes": 40}],
)
art_path_b.write_text(json.dumps(stale_resolved_artifact.to_dict(), indent=2))
# tsx_path_b still holds the stale content from _setup_unresolved_artifact (tsx_c2, remote URL)

old_defaults = _patched_resolve_assets_default()
old_output_dir = orchestrate.OUTPUT_DIR
orchestrate.OUTPUT_DIR = projB.parent
orchestrate.stage_resolve_assets(projB, extraction_data_c2)
orchestrate.OUTPUT_DIR = old_output_dir
ar.resolve_assets.__defaults__ = old_defaults

tsx_after_b = tsx_path_b.read_text()
test(
    "documents the danger the fix removes: an artifact marked 'resolved' with a stale .tsx "
    "is NOT self-healed by a rerun (this state must never be reached — which is exactly "
    "what writing .tsx before the artifact guarantees)",
    "example.com" in tsx_after_b,
    tsx_after_b,
)

# Scenario C: a direct, black-box-proof check of the write ORDER itself.
# Scenario A can't distinguish "write tsx then artifact" from "write
# artifact then tsx" by outcome alone — a single uninterrupted call writes
# both either way, so the two orders produce the same end state when the
# process never actually dies mid-call. The property under test IS the
# order, so assert the order directly: wrap Path.write_text to record every
# call this stage makes, in sequence, and require the .tsx write to appear
# before its corresponding artifact JSON write for the same section.
projC = _fresh("critical2_write_order")
art_path_c, tsx_path_c = _setup_unresolved_artifact(projC, "sections", "01-logo_bar", tsx_c2)

_write_log = []
_orig_write_text = Path.write_text


def _logging_write_text(self, *args, **kwargs):
    _write_log.append(str(self))
    return _orig_write_text(self, *args, **kwargs)


old_defaults = _patched_resolve_assets_default()
old_output_dir = orchestrate.OUTPUT_DIR
orchestrate.OUTPUT_DIR = projC.parent
Path.write_text = _logging_write_text
try:
    orchestrate.stage_resolve_assets(projC, extraction_data_c2)
finally:
    Path.write_text = _orig_write_text
orchestrate.OUTPUT_DIR = old_output_dir
ar.resolve_assets.__defaults__ = old_defaults

tsx_writes = [p for p in _write_log if p == str(tsx_path_c)]
art_writes = [p for p in _write_log if p == str(art_path_c)]
test("both the .tsx and the artifact JSON were written exactly once",
     len(tsx_writes) == 1 and len(art_writes) == 1, str(_write_log))
test(".tsx is written BEFORE the artifact JSON that marks the section resolved",
     _write_log.index(str(tsx_path_c)) < _write_log.index(str(art_path_c)),
     str(_write_log))


print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)
