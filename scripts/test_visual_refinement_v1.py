"""Mechanics added for THURIS "Homepage Visual Refinement V1" (2026-10-21).

WHAT THIS GUARDS
----------------
The operator brief declared display sizes (H1 56–68, H2 40–48, H3 26–32), a
1200px measure with 24–72px gutters, a visible wordmark, one nav action and a
separate phone composition for the hero. Each became a tenant DECLARATION the
compiler reads, never a THURIS literal in a template:

  - `type_scale.heading_tiers_px` (+ `_min_px` phone floors) beat the
    benchmark's measured tiers and emit fluid `clamp()` tiers that reach the
    declared ceiling by 1280px, so the 1440px render probe measures exactly
    what the conformance gate is held to (the effective benchmark's scale_px);
  - `layout` emits `--container-max` / `--gutter` and an `.aurelix-container`
    rule ONLY when declared — an undeclared tenant's CSS is unchanged;
  - `Brand mark: <file>` inlines the operator's artwork; a missing file raises;
  - `Nav action: <label>` renders that one link as the nav button;
  - a hero's second source image fills `{mobile_image_url}`.

Run: `python3 -m pytest scripts/test_visual_refinement_v1.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.design_system import BenchmarkError, compile_style, load_benchmark  # noqa: E402
from lib.effective_benchmark import effective_benchmark  # noqa: E402
from orchestrate import (  # noqa: E402
    _build_nav_template,
    brand_mark_src,
    build_template_fill,
    container_css_lines,
    fluid_px,
    layout_vars,
    type_tier_vars,
)

MEASURED = Path(__file__).resolve().parent.parent / "benchmarks" / "enterprise-stablecoin-payments-measured.json"


@pytest.fixture(scope="module")
def bm():
    return load_benchmark(MEASURED)


# ── type tiers ────────────────────────────────────────────────────────────

def test_declared_tiers_beat_the_measured_ones_and_are_logged(bm):
    style = compile_style(bm, tenant_overrides={"type_scale": {"heading_tiers_px": [64, 44, 28, 20]}})
    assert style["type_scale"]["heading_tiers_px"] == [64, 44, 28, 20]
    assert any(o["field"] == "type_scale.heading_tiers_px" for o in style["tenant_overrides"])


def test_a_floor_above_its_ceiling_is_refused(bm):
    with pytest.raises(BenchmarkError, match="exceeds its ceiling"):
        compile_style(bm, tenant_overrides={"type_scale": {
            "heading_tiers_px": [64, 44], "heading_tiers_min_px": [70, 32]}})
    with pytest.raises(BenchmarkError, match="largest first"):
        compile_style(bm, tenant_overrides={"type_scale": {"heading_tiers_px": [20, 64]}})


def test_fluid_tiers_reach_the_ceiling_by_1280():
    assert fluid_px(40, 64) == "clamp(40px, calc(40px + 24 * ((100vw - 375px) / 905)), 64px)"
    assert fluid_px(32, 32) == "32px"
    assert type_tier_vars({"heading_tiers_px": [64, 44], "heading_tiers_min_px": [40, 32]})["--type-h1"].startswith("clamp(40px")
    # No floor declared: the old fixed tiers, byte for byte.
    assert type_tier_vars({"heading_tiers_px": [32, 24]}) == {"--type-h1": "32px", "--type-h2": "24px"}


def test_the_gate_is_held_to_the_declared_tiers():
    eff = effective_benchmark({"type_system": {"scale_px": [14, 32]}, "type_scale": {}},
                              {"tenant_overrides": [{"field": "type_scale.heading_tiers_px",
                                                     "value": [64, 44, 28, 20]}]})
    assert eff["type_system"]["scale_px"] == [64, 44, 28, 20]


# ── layout ────────────────────────────────────────────────────────────────

def test_layout_is_emitted_only_when_declared():
    assert layout_vars({"section_py_px": 96}, None) == {"--section-py": "96px"}
    assert container_css_lines(None) == []
    declared = layout_vars({"section_py_px": 128, "section_py_min_px": 64},
                           {"max_width_px": 1200, "gutter_min_px": 24, "gutter_max_px": 72})
    assert declared["--container-max"] == "1200px"
    assert declared["--gutter"].startswith("clamp(24px")
    assert declared["--section-py"].startswith("clamp(64px")
    assert ".aurelix-container {" in container_css_lines({"max_width_px": 1200})


def test_layout_keys_outside_the_allow_list_are_refused(bm):
    with pytest.raises(BenchmarkError, match="not overridable"):
        compile_style(bm, tenant_overrides={"layout": {"columns": 12}})


# ── nav ───────────────────────────────────────────────────────────────────

def test_a_declared_mark_file_must_exist():
    with pytest.raises(ValueError, match="not a file"):
        brand_mark_src("intake/thuris/assets/logos/does-not-exist.svg")
    assert brand_mark_src("none") is None and brand_mark_src(None) is None


def test_nav_action_becomes_the_button_and_leaves_the_link_list():
    links = [{"label": "Origin", "href": "#origin"}, {"label": "Reserve", "href": "#collection"}]
    code = _build_nav_template("x", harvested_nav=links, nav_action="Reserve")
    assert code.count('"Reserve"') == 2          # desktop button + mobile button
    assert 'label: "Reserve"' not in code         # not also a plain link
    assert "var(--accent)" in code
    with pytest.raises(ValueError, match="names no navigation link"):
        _build_nav_template("x", harvested_nav=links, nav_action="Buy")


# ── hero mobile art direction ─────────────────────────────────────────────

CODE = ("// Tokens: {headline} {image_url} {mobile_image_url} {mobile_image_alt}\n"
        "<div>{headline}{image_url}{mobile_image_url}{mobile_image_alt}</div>")


def _hero(images):
    return {"archetype": "HERO", "section_uid": "h", "images": images,
            "content": {"headings": ["T"], "body_text": [], "ctas": [], "items": [], "item_count": 0}}


def test_the_second_image_is_the_phone_composition():
    values, _, _ = build_template_fill(_hero([{"src": "/d.webp", "alt": ""},
                                              {"src": "/m.webp", "alt": "Phone"}]), CODE)
    assert values["image_url"] == "/d.webp"
    assert values["mobile_image_url"] == "/m.webp"
    assert values["mobile_image_alt"] == "Phone"


def test_one_image_leaves_the_phone_slot_empty():
    values, _, _ = build_template_fill(_hero([{"src": "/d.webp", "alt": ""}]), CODE)
    assert values["mobile_image_url"] == ""
