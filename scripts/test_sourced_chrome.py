"""Site chrome (footer, metadata, nav brand) is sourced or empty, never invented.

WHAT THIS GUARDS
----------------
The THURIS build shipped three pieces of text no input contains:
  - footer `© 2026 Thuris. All rights reserved.` — the source says
    `© 2026 Aweku Laboratories (Pty) Ltd`; "Thuris" was the project slug
    title-cased and "All rights reserved." a generator literal;
  - metadata title `Thuris` and description `Built with web-builder
    pipeline` — the source page carries a <title> and a meta description;
  - a nav brand `Thuris`, again the slug, where the operator declared no
    logo until production vectors exist.

Harvested builds now render the FOOTER section's own text verbatim, take
title/description from the harvested page, and a preset `Brand mark: none`
renders no brand slot at all. A build with no harvest keeps its generic
chrome, which is not a claim about a real business.

Run: `python3 -m pytest scripts/test_sourced_chrome.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.nav_harvest import derive_footer_text  # noqa: E402
from orchestrate import (  # noqa: E402
    _build_footer_template,
    _build_nav_template,
    parse_brand_mark,
    preset_file_text,
    root_metadata_block,
)

FOOTER_PAGE = {
    "route": "/",
    "title": "THURIS — The Founding Collection",
    "description": "Three 10 ml botanical essences.",
    "sections": [
        {"archetype": "HERO", "content": {"section_body_text": ["not footer"]}},
        {"archetype": "FOOTER", "content": {
            "section_body_text": ["Botanical Fragrance House",
                                  "© 2026 Aweku Laboratories (Pty) Ltd"],
            "items": []}},
    ],
}


def test_footer_text_is_the_harvested_footer_body_verbatim():
    assert derive_footer_text([FOOTER_PAGE]) == [
        "Botanical Fragrance House", "© 2026 Aweku Laboratories (Pty) Ltd"]


def test_footer_text_drops_control_characters_and_is_empty_without_a_footer():
    page = {"sections": [{"archetype": "FOOTER", "content": {
        "section_body_text": ["ok", "bad\nline"]}}]}
    assert derive_footer_text([page]) == ["ok"]
    assert derive_footer_text([{"sections": [{"archetype": "HERO"}]}]) == []


def test_harvested_footer_renders_source_text_and_no_generated_copyright():
    code = _build_footer_template("thuris", harvested_footer=[],
                                  footer_text=derive_footer_text([FOOTER_PAGE]))
    assert '"\\u00a9 2026 Aweku Laboratories (Pty) Ltd"' in code or \
        '"© 2026 Aweku Laboratories (Pty) Ltd"' in code
    assert "All rights reserved" not in code
    assert "'Thuris'" not in code


def test_footer_without_harvest_keeps_generic_line():
    code = _build_footer_template("demo-shop", harvested_footer=None, footer_text=None)
    assert "All rights reserved" in code


def test_metadata_comes_from_the_harvested_page():
    block = root_metadata_block(FOOTER_PAGE, "thuris")
    assert '"title": "THURIS \\u2014 The Founding Collection"' in block or \
        'title: "THURIS — The Founding Collection"' in block
    assert "Three 10 ml botanical essences." in block
    assert "Built with web-builder pipeline" not in block


def test_harvested_page_without_description_emits_no_description():
    block = root_metadata_block({"title": "T"}, "thuris")
    assert "description" not in block


def test_no_harvest_never_emits_the_pipeline_description():
    block = root_metadata_block(None, "demo-shop")
    assert "Built with web-builder pipeline" not in block
    assert "Demo Shop" in block


def test_brand_mark_none_renders_no_brand_slot():
    assert parse_brand_mark("Brand mark: none\n") == "none"
    assert parse_brand_mark("nothing here") is None
    code = _build_nav_template("thuris", harvested_nav=[], brand_mark="none")
    assert "'Thuris'" not in code
    assert "shopName ||" not in code
    default = _build_nav_template("thuris", harvested_nav=[])
    assert "'Thuris'" in default


def test_thuris_preset_declares_no_brand_mark():
    assert parse_brand_mark(preset_file_text("thuris")) == "none"
