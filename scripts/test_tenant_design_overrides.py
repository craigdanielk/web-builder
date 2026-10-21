"""Tenant design overrides: declared in the tenant preset, allow-listed, recorded.

WHAT THIS GUARDS
----------------
`design_system` makes the benchmark own palette roles, type scale and rhythm.
Operator decision 2026-10-21 (THURIS): a tenant may override an allow-listed set
of those keys from its own preset. Three properties keep that from becoming
"tenant overrides whatever it likes":

1. **Allow-listed.** A key outside the list is refused, not ignored.
2. **Recorded.** Every override lands in `style.tenant_overrides` with the
   benchmark value it replaced, so the build record distinguishes measured
   from declared.
3. **Still checked.** WCAG AA runs on the overridden palette — an override
   cannot ship unreadable text.

No overrides ⇒ the compiled style is exactly what it was before.

Run: `python3 -m pytest scripts/test_tenant_design_overrides.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB_BUILDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB_BUILDER / "scripts"))

from lib.design_system import (  # noqa: E402
    BenchmarkError,
    compile_style,
    load_benchmark,
    parse_tenant_design_overrides,
)

MEASURED = WEB_BUILDER / "benchmarks" / "enterprise-stablecoin-payments-measured.json"

DARK = {
    "bg_primary": "#09070B", "bg_secondary": "#120D14", "surface": "#18111A",
    "text_primary": "#F4EEE4", "text_muted": "#A69A91", "border": "#312832",
    "accent": "#C1A36B", "on_accent": "#09070B", "surface_inverse": "#F4F0E8",
}
LIGHT = {
    "bg_primary": "#F4F0E8", "bg_secondary": "#E7DED2", "surface": "#FBF8F2",
    "text_primary": "#241F1B", "text_muted": "#736A61", "border": "#CFC5B8",
    "accent": "#241F1B", "on_accent": "#F4F0E8",
}


@pytest.fixture(scope="module")
def bm():
    return load_benchmark(MEASURED)


def test_no_overrides_leaves_the_compiled_style_unchanged(bm):
    assert compile_style(bm) == compile_style(bm, tenant_overrides=None)
    assert "tenant_overrides" not in compile_style(bm)


def test_palette_override_replaces_roles_and_records_what_it_replaced(bm):
    measured = dict(bm["palette_roles"])
    style = compile_style(bm, tenant_overrides={"palette_roles": DARK})
    for role, value in DARK.items():
        assert style["palette"][role] == value
    rec = {r["field"]: r for r in style["tenant_overrides"]}
    assert rec["palette_roles.bg_primary"]["was"] == measured["bg_primary"]
    assert rec["palette_roles.bg_primary"]["value"] == "#09070B"


def test_type_rhythm_radius_and_fonts_are_overridable(bm):
    style = compile_style(bm, tenant_overrides={
        "type_scale": {"base_px": 17},
        "rhythm": {"section_py_px": 140},
        "border_radius": {"button": "0px", "card": "0px"},
        "fonts": {"heading": "Bodoni Moda", "body": "Inter"},
    })
    assert style["type_scale"]["base_px"] == 17
    assert style["rhythm"]["section_py_px"] == 140
    assert style["spacing"]["section_padding"] == "140px"
    assert style["border_radius"] == {"button": "0px", "card": "0px"}
    # Body and heading were one family before; a tenant can now separate them.
    assert style["fonts"]["heading"]["google_fallback"] == "Bodoni Moda"
    assert style["fonts"]["body"]["google_fallback"] == "Inter"


def test_light_palette_is_compiled_alongside_the_base(bm):
    style = compile_style(bm, tenant_overrides={"palette_roles": DARK, "palette_light": LIGHT})
    assert style["palette_light"] == LIGHT


def test_a_key_outside_the_allow_list_is_refused(bm):
    with pytest.raises(BenchmarkError, match="shadow_system"):
        compile_style(bm, tenant_overrides={"shadow_system": {"max_layers": 4}})
    with pytest.raises(BenchmarkError, match="palette_roles.glow"):
        compile_style(bm, tenant_overrides={"palette_roles": {"glow": "#ffffff"}})


def test_an_override_cannot_ship_unreadable_text(bm):
    bad = dict(DARK, text_primary="#18111A")  # black-violet text on black
    with pytest.raises(BenchmarkError, match="WCAG"):
        compile_style(bm, tenant_overrides={"palette_roles": bad})


def test_the_light_set_is_contrast_checked_too(bm):
    bad = dict(LIGHT, text_muted="#E7DED2")  # parchment on bone
    with pytest.raises(BenchmarkError, match="palette_light"):
        compile_style(bm, tenant_overrides={"palette_roles": DARK, "palette_light": bad})


def test_an_overridden_accent_must_carry_its_label(bm):
    """CTA labels sit on the accent. Antique Brass under Bone is 3.62:1."""
    bad = dict(LIGHT, accent="#9A7748", on_accent="#F4F0E8")
    with pytest.raises(BenchmarkError, match="on_accent on accent"):
        compile_style(bm, tenant_overrides={"palette_roles": DARK, "palette_light": bad})


# ---------------------------------------------------------------------------
# The preset declaration
# ---------------------------------------------------------------------------

_PRESET = """# Preset: X (tenant)

## Tenant Design Overrides

```json
{"type_scale": {"base_px": 17}}
```

## Style Configuration
"""


def test_preset_block_parses():
    assert parse_tenant_design_overrides(_PRESET) == {"type_scale": {"base_px": 17}}


def test_absent_block_is_none_not_empty():
    assert parse_tenant_design_overrides("# Preset: X\n\n## Style Configuration\n") is None


def test_malformed_block_is_refused_not_ignored():
    with pytest.raises(BenchmarkError, match="Tenant Design Overrides"):
        parse_tenant_design_overrides(_PRESET.replace('"base_px": 17', "base_px: 17"))
