"""Font loading: a declared typeface must be FETCHED and APPLIED, not just named.

WHAT THIS GUARDS
----------------
The THURIS build declared Bodoni Moda (display) + Inter (body). The generated
layout.tsx imported only Inter, never applied `inter.className`, and set an
inline `fontFamily: 'Bodoni Moda', system-ui` on <body>. Three compounding
defects, one visible result: every heading rendered in system sans.

  1. Bodoni Moda was absent from `font_match.CATALOG`, so it was not
     "servable" and no import was emitted.
  2. `next/font/google` serves a HASHED family name (`__Inter_ab12`), so CSS
     naming `"Inter"` matches nothing unless the loader's CSS variable or
     className is applied. It was neither.
  3. The inline body style overrode the CSS body font with the heading face.

The contract now: each served family is imported with a `variable`, the
variables are applied on <html>, and globals.css reads them through
`--font-heading` / `--font-body`. No inline font style.

Run: `python3 -m pytest scripts/test_font_loading.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.font_match import SERVABLE, classify  # noqa: E402
from orchestrate import (  # noqa: E402
    fetched_font_weights, font_loader, font_stack, parse_font_weights, preset_file_text)


def test_bodoni_moda_is_servable_and_a_didone():
    assert "Bodoni Moda" in SERVABLE
    assert classify("Bodoni Moda") == "didone-serif"


def test_both_families_imported_with_variables_and_declared_weights():
    fl = font_loader("Bodoni Moda", "Inter", ["400", "500"], ["400", "500", "600"])
    assert fl["import_line"] == 'import { Bodoni_Moda, Inter } from "next/font/google";'
    joined = "\n".join(fl["const_lines"])
    assert 'Bodoni_Moda({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-heading-face"' in joined
    assert 'Inter({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-body-face"' in joined
    # Both variables must reach the DOM, or the hashed families are never named.
    assert "bodoni_moda.variable" in fl["html_class"]
    assert "inter.variable" in fl["html_class"]
    assert fl["unservable"] == []


def test_same_family_for_both_roles_is_imported_once_and_carries_both_variables():
    fl = font_loader("Inter", "Inter", ["400"], ["400", "500"])
    assert fl["import_line"] == 'import { Inter } from "next/font/google";'
    assert len(fl["const_lines"]) == 2  # two instances: one per CSS variable
    assert "--font-heading-face" in fl["const_lines"][0]
    assert "--font-body-face" in fl["const_lines"][1]


def test_unservable_family_is_reported_never_silently_dropped():
    fl = font_loader("Capsule Sans Text", "Inter", ["400"], ["400"])
    assert fl["unservable"] == ["Capsule Sans Text"]
    assert "Capsule" not in fl["import_line"]


def test_font_stack_reads_the_loader_variable_and_falls_back_by_genre():
    assert font_stack("heading", "Bodoni Moda") == 'var(--font-heading-face), "Bodoni Moda", serif'
    assert font_stack("body", "Inter") == 'var(--font-body-face), "Inter", sans-serif'


@pytest.mark.parametrize("text,role,expected", [
    ("heading_weights: 400, 500\nbody_weights: 400, 500, 600", "heading", ["400", "500"]),
    ("heading_weights: 400, 500\nbody_weights: 400, 500, 600", "body", ["400", "500", "600"]),
    ("heading_weight: 400", "heading", ["400"]),
    ("", "body", ["400", "500", "700"]),
])
def test_parse_font_weights(text, role, expected):
    assert parse_font_weights(text, role) == expected


def test_generator_emits_no_inline_body_font_and_applies_loader_variables():
    src = (Path(__file__).resolve().parent / "orchestrate.py").read_text(encoding="utf-8")
    # The inline style overrode globals.css with the (unloaded) heading face.
    assert "fontFamily: \"{font_family}\"" not in src
    assert '<html lang="en"{html_class_attr}>' in src


def test_weights_line_does_not_swallow_the_next_line():
    text = "heading_weights: 400, 500\n700_line: x"
    assert parse_font_weights(text, "heading") == ["400", "500"]


def test_tenant_preset_weights_win_over_a_synthetic_industry_preset():
    # An --industry build swaps preset_content for Supabase's synthetic preset
    # (body weight 300 for luxury-premium); the tenant file's list must win.
    tenant = "heading_weights: 400, 500\nbody_weights: 400, 500, 600"
    synthetic = "heading_weight: 400\nbody_weight: 300"
    assert fetched_font_weights(tenant, synthetic, "body", 400) == ["400", "500", "600"]
    assert fetched_font_weights("", synthetic, "body", 400) == ["300", "400"]


def test_thuris_preset_file_is_read_by_name():
    text = preset_file_text("thuris")
    assert "heading_weights: 400, 500" in text
    assert preset_file_text("no-such-preset-xyz") == ""
