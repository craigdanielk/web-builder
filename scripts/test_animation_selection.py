"""Animation-component selection: pool depth, role honouring, registry honesty.

WHY THIS DRIVES NODE RATHER THAN REIMPLEMENTING THE FILTER
----------------------------------------------------------
The selector that actually ran for cape-crypto is
`selectComponentForSection()` in `scripts/quality/lib/component-inject.js`,
and `orchestrate.py` reaches it exactly one way: `node -e` with
`decideComponentForSection(archetype, usedIds, presetIntensity)`
(`orchestrate.py:5240-5265`). These tests call it the same way. A Python
reimplementation of the framework/safety/intensity filtering would be a test
of the reimplementation, not of the thing the build runs — which is the
failure mode the census (`docs/census/2026-08-17-library-demand.md` §4)
spent a day undoing.

Run: `python3 -m pytest scripts/test_animation_selection.py -v` from web-builder/.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

WEB_BUILDER = Path(__file__).resolve().parent.parent
QUALITY_DIR = WEB_BUILDER / "scripts" / "quality"
COMPONENTS_DIR = WEB_BUILDER / "skills" / "animation-components"
FULL_REGISTRY = COMPONENTS_DIR / "registry" / "animation_registry.json"
CAPE_SECTIONS = WEB_BUILDER / "output" / "cape-crypto" / "sections"

# Cape Crypto's ruled preset intensity. A ceiling, not a target.
PRESET_INTENSITY = "moderate"


# ---------------------------------------------------------------------------
# Driving the real selector
# ---------------------------------------------------------------------------

_NODE_DECIDE = """
const {{ decideComponentForSection }} = require('./lib/component-inject');
const calls = {calls};
const out = [];
for (const c of calls) {{
  const r = decideComponentForSection(c.archetype, c.used, c.intensity);
  out.push({{
    archetype: c.archetype,
    injected: r.injected,
    reason: r.reason,
    animationId: r.component ? r.component.animationId : null,
    role: r.component ? r.component.role : null,
  }});
}}
console.log(JSON.stringify(out));
"""


def _decide(calls: list[dict]) -> list[dict]:
    """Run decideComponentForSection for a batch of (archetype, used, intensity)."""
    script = _NODE_DECIDE.format(calls=json.dumps(calls))
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        cwd=str(QUALITY_DIR),
        timeout=120,
    )
    assert proc.returncode == 0, f"node failed: {proc.stderr[-2000:]}"
    return json.loads(proc.stdout.strip())


def _drain_pool(archetype: str, intensity: str = PRESET_INTENSITY) -> list[str]:
    """Every distinct component the selector will give this archetype, in order.

    Drains by feeding each selection back as `used`, which is exactly how
    orchestrate.py dedupes within a page.
    """
    pool: list[str] = []
    while True:
        got = _decide([{"archetype": archetype, "used": pool, "intensity": intensity}])[0]
        if not got["injected"]:
            break
        assert got["animationId"] not in pool, "selector returned a used id"
        pool.append(got["animationId"])
        if len(pool) > 200:  # guard against a non-terminating selector
            break
    return pool


# ---------------------------------------------------------------------------
# The pages this has to serve, read from the real build artifact
# ---------------------------------------------------------------------------


def _archetype_from_filename(name: str) -> str:
    # 04-how_it_works.tsx -> HOW-IT-WORKS
    stem = Path(name).stem
    body = stem.split("-", 1)[1] if "-" in stem else stem
    return body.replace("_", "-").upper()


def _cape_pages() -> dict[str, list[str]]:
    if not CAPE_SECTIONS.is_dir():
        pytest.skip(f"no cape-crypto build artifact at {CAPE_SECTIONS}")
    pages = {}
    for page_dir in sorted(CAPE_SECTIONS.iterdir()):
        if not page_dir.is_dir():
            continue
        pages[page_dir.name] = [
            _archetype_from_filename(f.name) for f in sorted(page_dir.glob("*.tsx"))
        ]
    return pages


def _registry_rows() -> list[dict]:
    return json.loads(FULL_REGISTRY.read_text(encoding="utf-8"))["components"]


def _backed(row: dict) -> bool:
    sf = row.get("source_file")
    return bool(sf) and (COMPONENTS_DIR / sf).exists()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_no_page_exhausts_the_pool():
    """Every section of every cape-crypto page must get a component.

    Baseline before E4: homepage and about have 6 body sections each and the
    usable pool is 3, so sections 4-6 of both pages come back
    `no backed component for role` — reported by animation-coverage.json as
    `unchanged: 6`. That is pool exhaustion, not a role-mapping gap.
    """
    starved = {}
    for page, archetypes in _cape_pages().items():
        used: list[str] = []
        for idx, archetype in enumerate(archetypes, start=1):
            got = _decide([{"archetype": archetype, "used": used, "intensity": PRESET_INTENSITY}])[0]
            if not got["injected"]:
                starved.setdefault(page, []).append((idx, archetype, got["reason"]))
            else:
                used.append(got["animationId"])
    assert not starved, f"pages exhausted the animation pool: {json.dumps(starved, indent=2)}"


def test_pool_per_archetype_is_deeper_than_the_longest_page():
    """A pool shallower than the longest page guarantees starvation.

    The weaker form the task states — "more than one distinct component" —
    is subsumed by this: the longest cape-crypto page is 6 sections.
    """
    longest = max(len(a) for a in _cape_pages().values())
    thin = {}
    for archetype in sorted({a for page in _cape_pages().values() for a in page}):
        pool = _drain_pool(archetype)
        assert len(pool) > 1, f"{archetype} pool has {len(pool)} distinct component(s)"
        if len(pool) < longest:
            thin[archetype] = pool
    assert not thin, (
        f"pool must be >= {longest} (longest page) for every archetype; "
        f"thin: {json.dumps(thin, indent=2)}"
    )


def test_preferred_role_is_honoured_on_a_fresh_page():
    """The first section of a page must draw from the archetype's preferred roles.

    ROLE_BY_ARCHETYPE is a candidate ORDER with every other role as fallback,
    which is right — but if the preferred roles are empty of usable
    components, every archetype silently collapses onto the same first
    fallback. Before E4 all eight archetypes selected
    `entrance__fade_up_stagger`; LOGO-BAR (prefers `continuous`) and FAQ
    (prefers `interactive`) were being served by `entrance`.
    """
    proc = subprocess.run(
        ["node", "-e", "console.log(JSON.stringify(require('./lib/component-inject').ROLE_BY_ARCHETYPE))"],
        capture_output=True, text=True, cwd=str(QUALITY_DIR), timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    role_by_archetype = json.loads(proc.stdout.strip())

    archetypes = sorted({a for page in _cape_pages().values() for a in page})
    results = _decide([{"archetype": a, "used": [], "intensity": PRESET_INTENSITY} for a in archetypes])
    fell_back = {
        r["archetype"]: {"got": r["animationId"], "role": r["role"],
                         "preferred": role_by_archetype.get(r["archetype"], [])}
        for r in results
        if r["injected"] and r["role"] not in role_by_archetype.get(r["archetype"], [])
    }
    assert not fell_back, (
        "archetypes served out of a fallback role because their preferred roles "
        f"hold no usable component: {json.dumps(fell_back, indent=2)}"
    )


# A declared preference that no component can satisfy is aspiration, not
# mapping. This set is frozen in BOTH directions: the test fails if a new
# empty preference appears (a regression) and if one disappears (someone
# closed a gap and should record it here). Widening ROLE_BY_ARCHETYPE cannot
# satisfy it — every added role must itself hold a usable component.
EMPTY_PREFERRED_ROLES = {
    # continuous/ holds marquee (takes `logos[]`, a content-level insert),
    # count-up (no children), gradient-shift (safe, but an 8s infinite
    # background loop derives as `dramatic` and is over the moderate
    # ceiling), motionpath-orbit (needs `pathData`), and floating (a
    # misdescribed circular image menu). None can wrap a section at moderate.
    ("LOGO-BAR", "continuous"),
    # text/ is nine string-splitters: every one takes `text` or
    # `children: string` and emits per-word or per-character spans. None of
    # them can wrap JSX, by construction rather than by omission.
    ("HERO", "text"),
    # background/ holds aurora-background (wrap-safe, but a full-viewport
    # animated gradient derives as `dramatic`) and perspective-grid (no
    # children).
    ("ABOUT", "background"),
    # scroll/ holds gsap-pinned-horizontal (wrap-safe, `dramatic`), two
    # misdescribed demos, a ZoomParallax needing `images[]`, and a
    # FloatingPathsBackground needing `position`.
    ("HOW-IT-WORKS", "scroll"),
}


def test_declared_role_preferences_are_backed_by_a_usable_component():
    proc = subprocess.run(
        ["node", "-e", "console.log(JSON.stringify(require('./lib/component-inject').ROLE_BY_ARCHETYPE))"],
        capture_output=True, text=True, cwd=str(QUALITY_DIR), timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    role_by_archetype = json.loads(proc.stdout.strip())

    empty = set()
    for archetype in sorted({a for page in _cape_pages().values() for a in page}):
        preferred = role_by_archetype.get(archetype, [])
        assert preferred, f"{archetype} declares no preferred role at all"
        # Drain the whole pool to learn which roles are actually reachable.
        drained, roles_hit = [], set()
        while True:
            got = _decide([{"archetype": archetype, "used": drained, "intensity": PRESET_INTENSITY}])[0]
            if not got["injected"]:
                break
            drained.append(got["animationId"])
            roles_hit.add(got["role"])
        for role in preferred:
            if role not in roles_hit:
                empty.add((archetype, role))

    assert empty == EMPTY_PREFERRED_ROLES, (
        f"preferred roles holding no usable component changed.\n"
        f"  now:      {sorted(empty)}\n"
        f"  expected: {sorted(EMPTY_PREFERRED_ROLES)}"
    )


def test_rows_with_no_file_on_disk_are_never_marked_verified():
    """`dependencies_verified` may only be set on a row backed by a real file.

    986 of the 1034 rows point at library files that were never vendored in.
    A row that advertises verified dependencies while its component does not
    exist is worse than one that advertises nothing: the build would add npm
    packages for a component it can never copy.
    """
    offenders = [
        r["animation_id"]
        for r in _registry_rows()
        if r.get("dependencies_verified") and not _backed(r)
    ]
    assert not offenders, f"unbacked rows marked dependencies_verified: {offenders}"


def test_every_backed_row_declares_verified_dependencies():
    """The 48 rows with a file on disk are the ones the build can actually use."""
    missing = [r["animation_id"] for r in _registry_rows() if _backed(r) and not r.get("dependencies_verified")]
    assert not missing, f"file-backed rows with unverified dependencies: {missing}"


def test_selection_never_returns_a_row_whose_id_misdescribes_its_file():
    """`id_describes_file: false` rows must not reach a generated page.

    Six backed rows carry an `animation_id` that describes an animation the
    file does not implement — `entrance__slide_in_left` is a tab bar,
    `interactive__accordion_expand` is a hardcoded FAQ section with lorem
    ipsum body copy. Injecting one puts invented content on a licensed FSP's
    site.
    """
    lying = {r["animation_id"] for r in _registry_rows() if r.get("id_describes_file") is False}
    assert lying, "fixture assumption: the flagged mismatches must be recorded in the registry"
    archetypes = sorted({a for page in _cape_pages().values() for a in page})
    for archetype in archetypes:
        for got in _drain_pool(archetype):
            assert got not in lying, f"{archetype} selected misdescribed row {got}"
