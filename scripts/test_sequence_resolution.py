"""Sequence resolution: one key, two vocabularies, and a source that is recorded.

WHAT THIS GUARDS
----------------
1. **The page_type vocabulary bridge.** The harvest and manifest builders speak
   an 8-value page_type vocabulary; `section_presets` speaks a different
   14-value one. Three values do not overlap, and a non-overlapping value
   cannot match a registry row on ANY industry — the query returns 0 and the
   build falls through to a uniform hand-authored sequence with nothing
   recording that the key never had a chance. Measured 2026-08-18 on
   cape-crypto: three `content` pages queried a table whose content key is
   `content-page`.

2. **Per-page-type declared sequences.** A preset used to carry exactly one
   fenced sequence, applied to every page. `parse_sequence_blocks` reads a
   block per page type; `resolve_preset_sequence` says which block answered,
   so "declared for this page type" and "fell back to the default" are
   distinguishable in the manifest.

Run: `python3 -m pytest scripts/test_sequence_resolution.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB_BUILDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB_BUILDER / "scripts" / "lib"))

import site_manifest as sm  # noqa: E402

CAPE_PRESET = WEB_BUILDER / "skills" / "presets" / "cape-crypto.md"


# ---------------------------------------------------------------------------
# The page_type vocabulary bridge
# ---------------------------------------------------------------------------


def test_content_maps_to_the_registrys_content_key():
    """The measured silent miss: `content` is not `content-page`."""
    got = sm.registry_page_type("content")
    assert got["handle"] == "content-page"
    assert got["status"] == "mapped"


@pytest.mark.parametrize("manifest_value,registry_value", [
    ("content", "content-page"),
    ("product", "product-detail"),
    ("blog", "blog-index"),
])
def test_every_non_overlapping_value_is_translated(manifest_value, registry_value):
    got = sm.registry_page_type(manifest_value)
    assert got["handle"] == registry_value, (
        f"{manifest_value} would query a key the registry does not have"
    )


@pytest.mark.parametrize("shared", ["homepage", "about", "contact", "collection"])
def test_overlapping_values_pass_through_as_identity(shared):
    got = sm.registry_page_type(shared)
    assert got["handle"] == shared
    assert got["status"] == "identity"


def test_every_mapped_handle_is_a_real_registry_page_type():
    """A translation onto a key the registry does not have is worse than none."""
    for source in sm._PAGE_TYPE_TO_REGISTRY:
        handle = sm.registry_page_type(source)["handle"]
        assert handle in sm.REGISTRY_PAGE_TYPES, f"{source} -> {handle} is not a registry key"


def test_unmappable_page_type_is_not_measured_not_passed_through():
    """`landing` (the 404 entry's page_type) has no registry key.

    Passing it through would issue a query guaranteed to return 0 rows, and the
    caller could not tell that from an industry with a genuinely empty
    sequence.
    """
    got = sm.registry_page_type("landing")
    assert got["handle"] is None
    assert got["status"] == "unmapped"

    empty = sm.registry_page_type("")
    assert empty["handle"] is None
    assert empty["status"] == "unmapped"


# ---------------------------------------------------------------------------
# Declared sequences, per page type
# ---------------------------------------------------------------------------

_PRESET_WITH_PAGE_BLOCKS = """
# Some Preset

## Default Section Sequence

```
1. HERO      | gradient-split
2. FEATURES  | icon-grid
3. CTA       | dark-band
```

## Section Sequence — content

```
1. HERO       | gradient-split
2. FEATURES   | icon-grid
```

## Style Configuration

Not a sequence.
"""


def test_page_type_block_wins_over_the_default():
    blocks = sm.parse_sequence_blocks(_PRESET_WITH_PAGE_BLOCKS)
    assert set(blocks) == {"default", "content"}

    got = sm.resolve_preset_sequence(blocks, "content")
    assert got["status"] == "page_type"
    assert [s["archetype"] for s in got["sections"]] == ["HERO", "FEATURES"]


def test_page_type_without_a_block_falls_back_and_says_so():
    blocks = sm.parse_sequence_blocks(_PRESET_WITH_PAGE_BLOCKS)
    got = sm.resolve_preset_sequence(blocks, "about")
    assert got["status"] == "default"
    assert len(got["sections"]) == 3


def test_nothing_declared_is_a_status_not_a_silent_empty_page():
    got = sm.resolve_preset_sequence({}, "homepage")
    assert got["sections"] == []
    assert got["status"] == "none"
    assert got["source"] is None


def test_a_heading_that_is_not_a_sequence_is_not_parsed_as_one():
    blocks = sm.parse_sequence_blocks(_PRESET_WITH_PAGE_BLOCKS)
    assert "style" not in blocks and "configuration" not in blocks


def test_positions_are_renumbered_per_block():
    blocks = sm.parse_sequence_blocks(_PRESET_WITH_PAGE_BLOCKS)
    assert [s["position"] for s in blocks["content"]] == [1, 2]


@pytest.mark.skipif(not CAPE_PRESET.exists(), reason="cape-crypto preset absent")
def test_real_preset_parses_and_every_page_type_block_is_a_known_page_type():
    blocks = sm.parse_sequence_blocks(CAPE_PRESET.read_text(encoding="utf-8"))
    assert sm.SEQUENCE_DEFAULT_KEY in blocks, "the default block must still parse"
    for key in blocks:
        if key == sm.SEQUENCE_DEFAULT_KEY:
            continue
        # A block declared for a page type no page can ever have is a sequence
        # that will never be applied — and would look like a working
        # declaration in the file.
        assert sm.registry_page_type(key)["handle"] is not None or key in {
            "landing"
        }, f"preset declares a sequence for unknown page type {key!r}"


@pytest.mark.skipif(not CAPE_PRESET.exists(), reason="cape-crypto preset absent")
def test_real_preset_sequences_name_real_archetypes():
    taxonomy = (WEB_BUILDER / "skills" / "section-taxonomy.md").read_text(encoding="utf-8")
    known = {
        line.replace("### ", "").strip()
        for line in taxonomy.split("\n")
        if line.startswith("### ")
    }
    blocks = sm.parse_sequence_blocks(CAPE_PRESET.read_text(encoding="utf-8"))
    for key, sections in blocks.items():
        for s in sections:
            assert s["archetype"] in known, (
                f"{key} declares {s['archetype']}, which is not in section-taxonomy.md"
            )


# ---------------------------------------------------------------------------
# The resolution chain, as the build runs it
# ---------------------------------------------------------------------------
#
# stage_scaffold_multipage is imported, not reimplemented: what is asserted
# here is what the BUILD records, and a local copy of the chain would pass
# while the build fell through to a uniform sequence.

sys.path.insert(0, str(WEB_BUILDER / "scripts"))


def _stub_registry(monkeypatch, sequences, tmp_path):
    import orchestrate

    monkeypatch.setattr(
        orchestrate, "get_section_sequence",
        lambda industry, page_type: list(sequences.get((industry, page_type), [])),
    )
    monkeypatch.setattr(orchestrate, "OUTPUT_DIR", tmp_path)
    return orchestrate


def _manifest():
    return {
        "project": "seq-test",
        "industry": "fintech",
        "pages": [
            {"id": "homepage", "page_type": "homepage"},
            {"id": "wealth", "page_type": "content"},
            {"id": "about", "page_type": "about"},
            {"id": "not-found", "page_type": "landing"},
        ],
    }


def test_registry_lookup_uses_the_translated_page_type(monkeypatch, tmp_path):
    """The point of the bridge: `content` must reach the registry as
    `content-page`, or a row that exists is never found."""
    row = [{"position": 1, "archetype": "FEATURES", "variant": "icon-grid"}]
    orchestrate = _stub_registry(monkeypatch, {("fintech", "content-page"): row}, tmp_path)

    out = orchestrate.stage_scaffold_multipage(_manifest(), "seq-test", "fintech")
    wealth = next(p for p in out["pages"] if p["id"] == "wealth")
    assert wealth["sequence_status"] == "registry"
    assert wealth["sequence_source"] == "registry:fintech/content-page"
    assert [s["archetype"] for s in wealth["sections"]] == ["FEATURES"]


def test_registry_miss_falls_to_the_preset_and_records_which_block(monkeypatch, tmp_path):
    orchestrate = _stub_registry(monkeypatch, {}, tmp_path)

    out = orchestrate.stage_scaffold_multipage(
        _manifest(), "seq-test", "fintech", preset="cape-crypto"
    )
    by_id = {p["id"]: p for p in out["pages"]}
    assert by_id["wealth"]["sequence_source"] == "preset:cape-crypto#content"
    assert by_id["wealth"]["sequence_status"] == "preset_page_type"
    assert by_id["about"]["sequence_source"] == "preset:cape-crypto#about"
    # The pages must NOT all get the same sequence — that uniformity is the
    # defect this task exists to remove.
    assert (
        [s["archetype"] for s in by_id["wealth"]["sections"]]
        != [s["archetype"] for s in by_id["about"]["sections"]]
    )


def test_no_source_at_all_is_recorded_not_silently_empty(monkeypatch, tmp_path):
    orchestrate = _stub_registry(monkeypatch, {}, tmp_path)

    out = orchestrate.stage_scaffold_multipage(
        _manifest(), "seq-test", "fintech", preset="does-not-exist"
    )
    home = next(p for p in out["pages"] if p["id"] == "homepage")
    assert home["sections"] == []
    assert home["sequence_status"] == "none"
    assert home["sequence_source"] is None


def test_not_found_is_not_applicable_rather_than_empty(monkeypatch, tmp_path):
    orchestrate = _stub_registry(monkeypatch, {}, tmp_path)

    out = orchestrate.stage_scaffold_multipage(
        _manifest(), "seq-test", "fintech", preset="cape-crypto"
    )
    nf = next(p for p in out["pages"] if p["id"] == "not-found")
    assert nf["sequence_status"] == "not_applicable"
