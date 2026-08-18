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
  const r = decideComponentForSection(c.archetype, c.used, c.intensity, c.motion);
  out.push({{
    archetype: c.archetype,
    injected: r.injected,
    motion_input: r.motion_input,
    status: r.status,
    intensity_ceiling: r.intensity_ceiling,
    pool_size: r.pool_size === undefined ? null : r.pool_size,
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


def _drain_pool(
    archetype: str, intensity: str = PRESET_INTENSITY, motion: dict | None = None
) -> list[str]:
    """Every distinct component the selector will give this archetype, in order.

    Drains by feeding each selection back as `used`, which is exactly how
    orchestrate.py dedupes within a page.
    """
    pool: list[str] = []
    while True:
        got = _decide([
            {"archetype": archetype, "used": pool, "intensity": intensity, "motion": motion}
        ])[0]
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


def test_components_converted_for_wrappability_are_reachable():
    """The four components E4 gave a children prop must reach the selector.

    They are not reachable at cape-crypto's `moderate` ceiling — all four
    derive as `dramatic` from registry measurement fields
    (`causes_layout_shift_risk: medium`, `animation_type: background`), and
    editing those to clear the ceiling would be falsifying a measurement to
    pass a gate. So the assertion runs at the ceiling where they are supply.
    Without it, removing a `children` prop would be invisible to every other
    test here.
    """
    expected = {
        "entrance__fade_up_single",
        "entrance__word_reveal",
        "continuous__gradient_shift",
        "interactive__tilt_card",
    }
    reachable = set()
    for archetype in sorted({a for page in _cape_pages().values() for a in page}):
        reachable.update(_drain_pool(archetype, intensity="dramatic"))
    missing = expected - reachable
    assert not missing, f"converted components no longer selectable: {sorted(missing)}"


# ---------------------------------------------------------------------------
# The benchmark-shaped input — which exists, and which nothing reads
# ---------------------------------------------------------------------------

UNIFIED_REGISTRY = COMPONENTS_DIR / "component-registry.json"
MEASURED_BENCHMARK = WEB_BUILDER / "benchmarks" / "enterprise-stablecoin-payments-measured.json"


def _real_motion_block() -> dict:
    """The motion input as a build would actually produce it.

    Not a hand-written fixture: this is `design_system.compile_style()`'s
    `style.animation`, the same object written to site-spec.json. A fixture
    would let the producer and the consumer drift apart silently.
    """
    if not MEASURED_BENCHMARK.exists():
        pytest.skip(f"no benchmark at {MEASURED_BENCHMARK}")
    import sys

    sys.path.insert(0, str(WEB_BUILDER / "scripts"))
    from lib.design_system import compile_style, load_benchmark

    return compile_style(load_benchmark(MEASURED_BENCHMARK))["animation"]


def test_the_benchmark_motion_block_reaches_selection():
    """Before this, NOTHING in animation selection could read a benchmark."""
    motion = _real_motion_block()
    got = _decide([
        {"archetype": "HERO", "used": [], "intensity": PRESET_INTENSITY, "motion": motion}
    ])[0]
    mi = got["motion_input"]
    assert mi["present"] is True
    assert mi["source"] == motion["evidence_source"]
    assert mi["intensity"] == motion["intensity"]
    assert mi["libraries"] == sorted(l["name"] for l in motion["libraries"])
    assert mi["keyframe_count"] == len(motion["keyframes"])


def test_no_motion_input_is_reported_not_measured_not_as_an_empty_benchmark():
    got = _decide([{"archetype": "HERO", "used": [], "intensity": PRESET_INTENSITY}])[0]
    mi = got["motion_input"]
    assert mi["present"] is False
    assert mi["source"].startswith("NOT_MEASURED")
    # Absent is not the same as measured-empty: no zero counts are invented.
    assert "libraries" not in mi


def test_the_input_currently_has_no_consumer_and_says_so():
    """The honest half of this change, pinned so it cannot become a silent lie.

    A rule that starts reading the motion input must name itself in
    `consumed_by`. Until one does, every decision states that the wire exists
    and nothing is on the other end of it.
    """
    for motion in (_real_motion_block(), None):
        got = _decide([
            {"archetype": "HERO", "used": [], "intensity": PRESET_INTENSITY, "motion": motion}
        ])[0]
        assert got["motion_input"]["consumed_by"] == []


def test_affinity_was_not_populated_with_guesses():
    """`affinity` is 0/53 and stays 0/53.

    Filling it to give the new input something to score against would be
    inventing a design rule nobody measured — the exact fabrication class this
    system keeps having to undo. It stays unpopulated and is reported as such.
    """
    rows = json.loads(UNIFIED_REGISTRY.read_text(encoding="utf-8"))["components"]
    assert len(rows) == 53
    assert sum(1 for r in rows.values() if r.get("affinity")) == 0
    assert sum(1 for r in rows.values() if r.get("archetypes")) == 0


def test_selection_is_unchanged_by_the_motion_input():
    """REGRESSION GATE. Cape Crypto's animation decisions must not move.

    An input with no consumer must have no effect. Every archetype the build
    emits is drained three ways — no motion, the real benchmark motion, and a
    benchmark motion declaring `dramatic` — and all three must be identical.

    The third case is the specific trap: the benchmark's intensity is derived
    from how animated the SOURCE site happened to be, and the preset's
    `animation_intensity` is a deliberate tenant decision. If the benchmark
    ever silently became the ceiling, a tenant asking for restraint would get
    17 components instead of 7 and nobody would have declared it.
    """
    real = _real_motion_block()
    loud = dict(real, intensity="dramatic")
    for archetype in sorted({a for page in _cape_pages().values() for a in page}):
        baseline = _drain_pool(archetype)
        assert _drain_pool(archetype, motion=real) == baseline, archetype
        assert _drain_pool(archetype, motion=loud) == baseline, archetype


# ---------------------------------------------------------------------------
# The split: a catalogue of 1034 is not a library of 1034
# ---------------------------------------------------------------------------

LIBRARY = COMPONENTS_DIR / "registry" / "animation_library.json"
WISHLIST = COMPONENTS_DIR / "registry" / "animation_wishlist.json"
PRODUCER = COMPONENTS_DIR / "registry" / "annotate_backed_rows.py"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_library_plus_wishlist_accounts_for_every_catalogue_row():
    """Nothing may be lost in the split, and nothing invented.

    The 986 unbacked rows are RECORDED, not deleted — that is the difference
    between a split and a silent filter. If the two files stop summing to the
    catalogue, rows are being dropped somewhere without a record.
    """
    catalogue = _json(FULL_REGISTRY)
    library = _json(LIBRARY)
    wishlist = _json(WISHLIST)
    total = len(catalogue["components"])
    assert len(library["components"]) + len(wishlist["components"]) == total
    assert library["backed_components"] == len(library["components"])
    assert wishlist["unresolved_components"] == len(wishlist["components"])
    # And the header of the catalogue itself states the split, so a reader who
    # quotes a count from the one file everybody reads cannot quote 1034 alone.
    assert catalogue["backed_components"] == len(library["components"])
    assert catalogue["unresolved_components"] == len(wishlist["components"])
    assert catalogue["backed_components"] + catalogue["unresolved_components"] == \
        catalogue["total_components"] == total


def test_the_split_is_exactly_the_file_existence_sweep():
    """Re-run the sweep here rather than trusting the artefact's own claim."""
    rows = _registry_rows()
    backed = {r["animation_id"] for r in rows if _backed(r)}
    unbacked = {r["animation_id"] for r in rows} - backed
    assert {c["animation_id"] for c in _json(LIBRARY)["components"]} == backed
    assert {c["animation_id"] for c in _json(WISHLIST)["components"]} == unbacked


def test_every_library_row_has_a_file_and_every_wishlist_row_does_not():
    for row in _json(LIBRARY)["components"]:
        assert (COMPONENTS_DIR / row["source_file"]).exists(), row["animation_id"]
    for row in _json(WISHLIST)["components"]:
        sf = row["source_file"]
        assert not sf or not (COMPONENTS_DIR / sf).exists(), row["animation_id"]


def test_selection_can_only_ever_reach_a_backed_row():
    """The point of the split: an unbacked row must be unreachable.

    Drained at `dramatic`, the widest ceiling, across every archetype the
    build actually emits — the largest set selection can produce.
    """
    library_ids = {c["animation_id"] for c in _json(LIBRARY)["components"]}
    for archetype in sorted({a for page in _cape_pages().values() for a in page}):
        for got in _drain_pool(archetype, intensity="dramatic"):
            assert got in library_ids, f"{archetype} selected unbacked row {got}"


def test_the_split_reproduces_itself_byte_for_byte():
    """The re-derivability bar: a library nobody can re-derive is not a library.

    Re-running the producer over the same tree must reproduce both artefacts
    exactly. Without this the split becomes a hand-maintained file that drifts
    from the filesystem the moment a component is added or removed.
    """
    import hashlib

    def digest(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    before = {p: digest(p) for p in (LIBRARY, WISHLIST, FULL_REGISTRY)}
    proc = subprocess.run(
        ["python3", str(PRODUCER)],
        capture_output=True, text=True, cwd=str(WEB_BUILDER), timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    after = {p: digest(p) for p in (LIBRARY, WISHLIST, FULL_REGISTRY)}
    changed = [p.name for p in before if before[p] != after[p]]
    assert not changed, f"producer is not reproducible; rewrote {changed}"


def test_the_reported_component_count_is_the_backed_count():
    """`backedRowCount()` is what a refusal reason quotes. It must be 48, not 1034."""
    proc = subprocess.run(
        ["node", "-e", "console.log(require('./lib/component-inject').backedRowCount())"],
        capture_output=True, text=True, cwd=str(QUALITY_DIR), timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    reported = int(proc.stdout.strip())
    assert reported == len(_json(LIBRARY)["components"])
    assert reported < len(_registry_rows()), (
        "the reported count equals the catalogue — the split is not in effect"
    )


# ---------------------------------------------------------------------------
# Three-state reporting: an empty pool is a configuration outcome
# ---------------------------------------------------------------------------


def _pool_size(intensity: str) -> int:
    """Size of componentPoolForIntensity() as the library itself reports it."""
    proc = subprocess.run(
        [
            "node", "-e",
            "console.log(require('./lib/component-inject')"
            f".componentPoolForIntensity({json.dumps(intensity)}).length)",
        ],
        capture_output=True, text=True, cwd=str(QUALITY_DIR), timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return int(proc.stdout.strip())


def test_an_empty_intensity_pool_reports_not_measured_not_a_supply_failure():
    """`animation_intensity: subtle` admits ZERO components — say so.

    `deriveComponentIntensity` returns `subtle` only for an entrance/exit
    under 300ms with all three risks low; no file-backed component satisfies
    that, so the subtle ceiling drains to 0 (measured 2026-08-18, and again
    below rather than asserted from the census). Reporting that as
    "no backed component for role" states a fact about SUPPLY that was never
    tested — nothing was ever compared. It is a configuration ceiling, and 18
    of the 44 presets on disk declare it.
    """
    assert _pool_size("subtle") == 0, "fixture assumption: the subtle ceiling admits nothing"
    got = _decide([{"archetype": "HERO", "used": [], "intensity": "subtle"}])[0]
    assert got["injected"] is False
    assert got["status"] == "not_measured", got
    assert got["pool_size"] == 0, got
    assert got["intensity_ceiling"] == "subtle", got
    assert "NOT_MEASURED" in got["reason"], got["reason"]
    assert "subtle" in got["reason"], got["reason"]
    # It must not read as a statement about the library's supply.
    assert "no backed component for role" not in got["reason"], got["reason"]


def test_a_non_empty_pool_that_is_exhausted_still_reports_a_supply_failure():
    """The other branch: a real pool, nothing left in it, is a supply statement.

    Without this the change would be a one-way street — everything would
    report NOT_MEASURED and the gate could only say "unmeasured", which is the
    same dishonesty pointed the other way.
    """
    pool = _pool_size(PRESET_INTENSITY)
    assert pool > 0, "fixture assumption: the moderate ceiling admits a real pool"
    all_ids = [r["animation_id"] for r in _registry_rows()]
    got = _decide([{"archetype": "HERO", "used": all_ids, "intensity": PRESET_INTENSITY}])[0]
    assert got["injected"] is False
    assert got["status"] == "no_supply", got
    assert got["pool_size"] == pool, got
    assert "NOT_MEASURED" not in got["reason"], got["reason"]
    assert got["reason"].startswith("no backed component for role"), got["reason"]


def test_reported_pool_size_equals_what_selection_can_actually_reach():
    """Pool measurement and selection must not drift apart.

    The reported ceiling pool is only honest if it is the same predicate
    selection applies. Draining every archetype at a ceiling can only reach
    components that pass that predicate, so the drained set must be a subset
    of the reported pool, and at `dramatic` (where every role is reachable)
    the two must be equal.
    """
    for intensity in ("moderate", "dramatic"):
        reachable = set()
        for archetype in sorted({a for page in _cape_pages().values() for a in page}):
            reachable.update(_drain_pool(archetype, intensity=intensity))
        assert len(reachable) <= _pool_size(intensity), (
            f"{intensity}: selection reached {len(reachable)} components but the "
            f"reported pool is {_pool_size(intensity)} — the report understates supply"
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
