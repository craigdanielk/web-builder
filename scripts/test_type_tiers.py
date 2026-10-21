"""Headings take their sizes from the benchmark's measured type scale.

WHAT THIS GUARDS
----------------
Operator decision 2026-10-21: snap templates to the scale. The conformance
gate measured 12 of 22 THURIS headings at 48/56/96px — sizes hardcoded in the
templates — against a luxury-botanical-oils scale whose largest heading is
32px. A type scale is a closed set; a template that names its own display
sizes cannot carry a benchmark's.

`heading_tiers()` picks the four most-used measured heading sizes (the
reference's real tiers; ties to the larger size), falling back to the four
largest declared sizes. The build emits them as `--type-h1..h4`, and every
section-heading template reads those variables (its old size survives only as
the `var()` fallback for a build that compiled no scale).

Run: `python3 -m pytest scripts/test_type_tiers.py -v` from web-builder/.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.design_system import heading_tiers  # noqa: E402
from orchestrate import type_tier_vars  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def test_tiers_are_the_most_used_measured_sizes():
    bm = {"type_system": {"heading_sizes_px": [14, 16, 18, 20, 24, 30, 31, 32]},
          "_distributions": {"heading_sizes_px": {"14.0": 24, "18.0": 10, "24.0": 10, "32.0": 10,
                                                  "16.0": 8, "20.0": 3, "31.0": 3, "30.0": 2}}}
    assert heading_tiers(bm) == [32, 24, 18, 14]


def test_without_a_distribution_the_largest_declared_sizes():
    assert heading_tiers({"type_system": {"scale_px": [11, 12, 14, 16, 20, 30, 48]}}) == [48, 30, 20, 16]
    assert heading_tiers({}) == []


def test_tiers_become_css_variables():
    assert type_tier_vars({"heading_tiers_px": [32, 24, 18, 14]}) == {
        "--type-h1": "32px", "--type-h2": "24px", "--type-h3": "18px", "--type-h4": "14px"}
    assert type_tier_vars({}) == {}


CONVERTED = [
    "HERO/centered.tsx", "ABOUT/editorial-split.tsx", "PRODUCT-SHOWCASE/hover-cards.tsx",
    "FEATURES/icon-grid.tsx", "HOW-IT-WORKS/numbered-steps.tsx", "FAQ/accordion.tsx",
    "CTA/dark-band.tsx", "CTA/centered.tsx",
    "HERO/product-hero.tsx", "CTA/split-with-image.tsx",
]


def test_section_headings_read_the_tier_variables_not_hardcoded_display_sizes():
    for rel in CONVERTED:
        src = (ROOT / "section-templates" / rel).read_text(encoding="utf-8")
        blocks = re.findall(r"<(?:motion\.)?h[12]\b(.*?)>", src, re.S)
        assert blocks, rel
        for attrs in blocks:
            assert "var(--type-h" in attrs, f"{rel}: heading without a tier variable"
            assert not re.search(r"(?:md:|lg:)?text-\[\d+(?:\.\d+)?rem\]", attrs), \
                f"{rel}: hardcoded display size survives"
