"""Section tone: a declared light ground re-declares the WHOLE token set.

WHAT THIS GUARDS
----------------
The token chain emitted one palette plus a single `--surface-inverse` ground.
A light section on a dark base therefore inherited the base text colour —
Warm Ivory on Bone, unreadable. A section the source marks `data-tone="light"`
is wrapped in `<div data-tone="light">`, and `globals.css` re-declares every
role for that scope from `style.palette_light`.

Two refusals matter as much as the happy path:
- no `palette_light` => no light rule at all (never a guessed light palette);
- a file whose stem does not match its planned section gets no wrapper (the
  files on disk are ground truth; a drifted plan must not mis-tone them).

Run: `python3 -m pytest scripts/test_section_tone.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrate import _build_page_imports, tone_by_section_stem, tone_css_lines  # noqa: E402

LIGHT = {
    "bg_primary": "#F4F0E8", "bg_secondary": "#E7DED2", "surface": "#FBF8F2",
    "text_primary": "#241F1B", "text_muted": "#736A61", "border": "#CFC5B8",
    "accent": "#241F1B", "on_accent": "#F4F0E8",
}


def test_light_rule_redeclares_every_role_and_paints_its_ground():
    css = "\n".join(tone_css_lines(LIGHT))
    assert '[data-tone="light"]' in css
    for var, hexv in (("--background", "#F4F0E8"), ("--foreground", "#241F1B"),
                      ("--muted", "#736A61"), ("--accent", "#241F1B"),
                      ("--on-accent", "#F4F0E8"), ("--border", "#CFC5B8"),
                      ("--surface", "#E7DED2")):
        assert f"{var}: {hexv};" in css, var
    assert "background: var(--background);" in css
    assert "color: var(--foreground);" in css


def test_no_light_palette_emits_no_light_rule():
    assert tone_css_lines(None) == []


def test_tone_map_keys_by_generated_file_stem():
    sections = [
        {"archetype": "HERO", "tone": "dark"},
        {"archetype": "ABOUT", "tone": "light"},
        {"archetype": "HOW-IT-WORKS", "tone": "light"},
        {"archetype": "FAQ"},
    ]
    assert tone_by_section_stem(sections) == {
        "01-hero": "dark", "02-about": "light", "03-how_it_works": "light",
    }


def test_page_wraps_toned_sections_and_leaves_others_alone():
    files = [Path("01-hero.tsx"), Path("02-about.tsx"), Path("03-faq.tsx")]
    _, components = _build_page_imports(
        files, "@/s/", None, "home", tone_by_stem={"02-about": "light"})
    assert '<div data-tone="light">' in components[1]
    assert "data-tone" not in components[0]
    assert "data-tone" not in components[2]


def test_a_stem_that_does_not_match_the_plan_is_not_toned():
    files = [Path("02-features.tsx")]
    _, components = _build_page_imports(
        files, "@/s/", None, "home", tone_by_stem={"02-about": "light"})
    assert "data-tone" not in components[0]


def test_only_allowlisted_tones_reach_generated_source():
    """`data-tone` is harvested, i.e. untrusted. A value that could close the
    attribute and inject JSX must never be interpolated into a .tsx file."""
    hostile = '"><script>alert(1)</script><div x="'
    assert tone_by_section_stem([{"archetype": "HERO", "tone": hostile}]) == {}
    assert tone_by_section_stem([{"archetype": "HERO", "tone": "Light "}]) == {}
    _, components = _build_page_imports(
        [Path("01-hero.tsx")], "@/s/", None, "home", tone_by_stem={"01-hero": hostile})
    assert "script" not in components[0] and "data-tone" not in components[0]


def test_no_tone_map_is_byte_identical_to_before():
    files = [Path("01-hero.tsx"), Path("02-about.tsx")]
    assert _build_page_imports(files, "@/s/", None, "home") == \
        _build_page_imports(files, "@/s/", None, "home", tone_by_stem=None)
