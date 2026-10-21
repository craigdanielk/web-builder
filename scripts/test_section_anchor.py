"""Section anchors: a source section id becomes the wrapper id on the built page.

WHAT THIS GUARDS
----------------
A one-page site's nav is fragment links (`#collection`). The generated page
had no ids, so every nav link would scroll nowhere. A planned section that
carries an `anchor` (from the source `<section id>`) is wrapped in
`<div id="...">`, combined with its tone wrapper when it has one.

The anchor is harvested, i.e. untrusted, and is interpolated into TSX — so it
is re-checked here against the same allowlist the harvest applies, and a
value that fails is dropped, never escaped-and-kept.

Run: `python3 -m pytest scripts/test_section_anchor.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrate import _build_page_imports, anchor_by_section_stem  # noqa: E402


def test_anchor_by_stem_keeps_only_allowlisted_ids():
    sections = [
        {"archetype": "HERO", "anchor": "hero"},
        {"archetype": "PRODUCT-SHOWCASE", "anchor": "collection"},
        {"archetype": "ABOUT", "anchor": 'x" onload="evil()'},
        {"archetype": "FAQ"},
    ]
    assert anchor_by_section_stem(sections) == {
        "01-hero": "hero", "02-product_showcase": "collection"}


def test_wrapper_carries_id_and_tone_together(tmp_path):
    files = [tmp_path / "01-hero.tsx", tmp_path / "02-about.tsx", tmp_path / "03-faq.tsx"]
    _, comps = _build_page_imports(
        files, "@/components/sections/homepage/",
        tone_by_stem={"01-hero": "dark", "02-about": "light"},
        anchor_by_stem={"01-hero": "hero", "03-faq": "faq"},
    )
    assert comps[0].startswith('      <div id="hero" data-tone="dark">')
    assert comps[1].startswith('      <div data-tone="light">')
    assert comps[2].startswith('      <div id="faq">')
