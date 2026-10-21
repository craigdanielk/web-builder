"""The harvested kicker fills `{eyebrow}` and is no longer the subtitle.

WHAT THIS GUARDS
----------------
THURIS's hero source is: eyebrow <p>, <h1>, <h2> tagline, subhead <p>, a
90-bottle <p>, two CTAs. The fill took body_text[0] — the eyebrow — as the
subheadline, left `{eyebrow}` empty ("no-harvest-supply"), and had no slot for
the tagline or the second paragraph, so three approved lines never rendered.

Now `content.kicker` (harvest: the short line before the first heading) fills
`{eyebrow}` and is subtracted from the body lists; `{tagline}` is the second
section heading; `{supporting_text}` the next paragraph.

Run: `python3 -m pytest scripts/test_kicker_fill.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrate import build_template_fill  # noqa: E402

CODE = ("// Tokens: {eyebrow} {headline} {tagline} {subheadline} {supporting_text}\n"
        "<div>{eyebrow}{headline}{tagline}{subheadline}{supporting_text}</div>")

HERO = {
    "archetype": "HERO", "variant": "centered", "section_uid": "u1",
    "content": {
        "headings": ["The Founding Collection", "A trace of origin."],
        "body_text": ["THURIS · BOTANICAL FRAGRANCE HOUSE",
                      "Three rare botanical essences.",
                      "The Founding Release is limited to 90 bottles."],
        "section_headings": ["The Founding Collection", "A trace of origin."],
        "section_body_text": ["THURIS · BOTANICAL FRAGRANCE HOUSE",
                              "Three rare botanical essences.",
                              "The Founding Release is limited to 90 bottles."],
        "ctas": [], "items": [], "item_count": 0,
        "kicker": "THURIS · BOTANICAL FRAGRANCE HOUSE",
    },
}


def test_kicker_fills_eyebrow_and_every_line_has_a_home():
    values, _, prov = build_template_fill(HERO, CODE)
    assert values["eyebrow"] == "THURIS · BOTANICAL FRAGRANCE HOUSE"
    assert values["headline"] == "The Founding Collection"
    assert values["tagline"] == "A trace of origin."
    assert values["subheadline"] == "Three rare botanical essences."
    assert values["supporting_text"] == "The Founding Release is limited to 90 bottles."
    assert {p["slot"]: p["source"] for p in prov}["eyebrow"] == "harvested"


def test_grouped_section_subtracts_the_kicker_from_section_body():
    sec = {
        "archetype": "ABOUT", "section_uid": "u2",
        "content": {
            "headings": ["Rare materials.", "Item"], "body_text": ["THE HOUSE", "Intro.", "Item body"],
            "section_headings": ["Rare materials."], "section_body_text": ["THE HOUSE", "Intro."],
            "ctas": [], "item_count": 1,
            "items": [{"heading": "Item", "body": "Item body", "headings": ["Item"],
                       "body_text": ["Item body"], "ctas": [], "images": []}],
            "kicker": "THE HOUSE",
        },
    }
    values, _, _ = build_template_fill(sec, "// Tokens: {eyebrow} {section_title} {section_body}\n<p>{eyebrow}{section_title}{section_body}</p>")
    assert values["eyebrow"] == "THE HOUSE"
    assert values["section_body"] == "Intro."


def test_no_kicker_leaves_eyebrow_empty_and_body_untouched():
    sec = {**HERO, "content": {**HERO["content"], "kicker": None}}
    values, _, _ = build_template_fill(sec, CODE)
    assert values["eyebrow"] == ""
    assert values["subheadline"] == "THURIS · BOTANICAL FRAGRANCE HOUSE"
