"""Task C2 — sections composed from declared facts.

Precedence: **harvested > phase0 > omitted.** These tests pin all three arms,
plus the two things that make composition safe: nothing undeclared is composed,
and a composed section claims its archetype so the registry gap-fill does not
append the same archetype a second time with an empty content dict (the D5
mechanism from the previous wave).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.phase0_content import compose_declared_sections, declared_content  # noqa: E402
from orchestrate import reconcile_page_sections  # noqa: E402
from test_phase0_content import CAPE_CRYPTO_CTX  # noqa: E402

CAPE_DECL = declared_content(CAPE_CRYPTO_CTX)

HERO_BLOCK = {
    "archetype": "HERO",
    "variant": "centered",
    "index": 0,
    "content": {"headings": ["Buy Bitcoin in South Africa"], "body_text": []},
}

PRODUCTS_BLOCK = {
    "archetype": "FEATURES",
    "variant": "icon-grid",
    "index": 1,
    "content": {
        "items": [{"heading": "Spot exchange", "body": "Order book trading"}],
        "item_count": 1,
    },
}


def _composed(harvested, declared):
    covered = {s["archetype"] for s in harvested}
    return compose_declared_sections(declared, covered)


def test_declared_products_become_a_section_with_phase0_provenance():
    sections, _ = _composed([HERO_BLOCK], CAPE_DECL)
    products = [s for s in sections if s["archetype"] == "FEATURES"]
    assert products, "7 declared products produced no section"
    prov = products[0]["_phase0_provenance"]
    assert len(prov) == 7
    assert {p["source"] for p in prov} == {"phase0"}
    assert all(p["field_key"] for p in prov)
    assert products[0]["content"]["item_count"] == 7


def test_a_declared_section_never_duplicates_a_harvested_one():
    """If the source page already says it, harvested wins — no double telling."""
    sections, omissions = _composed([HERO_BLOCK, PRODUCTS_BLOCK], CAPE_DECL)
    assert [s for s in sections if s["archetype"] == "FEATURES"] == []
    reasons = {o["group"]: o["reason"] for o in omissions}
    assert reasons["products"] == "harvested_covers"


def test_nothing_undeclared_is_composed():
    sections, omissions = _composed([], {"products": [], "pillars": []})
    assert sections == []            # empty, never padded
    assert {o["reason"] for o in omissions} == {"not_declared"}


def test_a_composed_section_carries_no_fabricated_heading():
    """A section heading is not a declared fact — the slot stays empty."""
    sections, _ = _composed([HERO_BLOCK], CAPE_DECL)
    content = sections[0]["content"]
    assert content["section_headings"] == []
    assert content["section_body_text"] == []
    # And no crawl index is invented for a section that was never crawled.
    assert "index" not in sections[0]


def test_a_composed_section_has_a_durable_uid_distinct_per_page():
    """`_emit_section_artifact` keeps only the provenance rows whose
    section_uid matches the artifact's. A composed section with no uid falls
    back to a list position that differs between the fill call and the emit
    call, and every phase0 row is filtered out of the artifact it belongs to —
    observed as 9 phase0 slots in slot-provenance and 0 in the artifact."""
    dev, _ = compose_declared_sections(CAPE_DECL, set(), page_id="developers")
    dev_again, _ = compose_declared_sections(CAPE_DECL, set(), page_id="developers")
    merch, _ = compose_declared_sections(CAPE_DECL, set(), page_id="merchants")
    assert dev[0]["section_uid"]
    assert dev[0]["section_uid"] == dev_again[0]["section_uid"]   # deterministic
    assert dev[0]["section_uid"] != merch[0]["section_uid"]       # per page


def test_one_archetype_is_claimed_once_products_before_pillars():
    sections, omissions = _composed([HERO_BLOCK], CAPE_DECL)
    assert len(sections) == 1
    assert sections[0]["_phase0_group"] == "products"
    reasons = {o["group"]: o["reason"] for o in omissions}
    assert reasons["pillars"] == "archetype_already_composed"


# ─── Wiring: the composer runs inside the reconciler ──────────────

def test_reconciler_inserts_the_composed_section_before_gap_fill():
    registry = [{"archetype": "HERO", "variant": "centered"},
                {"archetype": "FEATURES", "variant": "impact-metrics"},
                {"archetype": "CTA", "variant": "centered"}]
    sections, meta = reconcile_page_sections(
        registry, [HERO_BLOCK], declared=CAPE_DECL,
    )
    assert meta["phase0_composed_count"] == 1
    features = [s for s in sections if s["archetype"] == "FEATURES"]
    # Composed once, and the registry gap-fill did NOT append a second empty one.
    assert len(features) == 1
    assert features[0].get("_phase0_composed") is True
    assert features[0].get("_registry_gap_fill") is not True
    # The registry stays authoritative for shape.
    assert features[0]["variant"] == "impact-metrics"
    # The composed section is ordered after the harvest spine, before gap-fill.
    assert sections[0]["archetype"] == "HERO"
    assert sections[1]["archetype"] == "FEATURES"
    assert sections[2]["archetype"] == "CTA"
    assert sections[2].get("_registry_gap_fill") is True


def test_reconciler_without_a_declaration_is_unchanged():
    registry = [{"archetype": "HERO", "variant": "centered"},
                {"archetype": "FEATURES", "variant": "impact-metrics"}]
    before, meta_before = reconcile_page_sections(registry, [HERO_BLOCK])
    after, meta_after = reconcile_page_sections(registry, [HERO_BLOCK], declared=None)
    assert before == after
    assert meta_after["phase0_composed_count"] == 0
    assert [s["archetype"] for s in before] == ["HERO", "FEATURES"]
    assert before[1]["_registry_gap_fill"] is True


def test_composition_is_idempotent_across_repeated_runs():
    """Re-running the build must not accumulate composed sections.

    `animation-coverage.json` once ACCUMULATED and doubled on a repeat run, and
    `asset_resolver` carries a comment about re-resolution corrupting its tally.
    A composer that appends on every run is worse than one that never runs,
    because the second failure is invisible — the site simply grows a second
    identical card grid and nothing reports it.

    Two guards, and they fail differently. The first pins the reconciler as a
    pure function of its inputs: same registry, same harvest, same declaration
    → byte-identical sections and identical meta, so nothing is carried between
    calls in module state. The second pins the case that actually bit before —
    a second pass over a plan that ALREADY contains the composed section, which
    is what a resumed or re-entered build hands it. The composed FEATURES is
    indistinguishable from a harvested one by archetype, so precedence catches
    it as `harvested_covers` and composes nothing.
    """
    registry = [{"archetype": "HERO", "variant": "centered"},
                {"archetype": "FEATURES", "variant": "impact-metrics"}]

    first, meta_first = reconcile_page_sections(
        registry, [HERO_BLOCK], declared=CAPE_DECL, page_id="developers",
    )
    second, meta_second = reconcile_page_sections(
        registry, [HERO_BLOCK], declared=CAPE_DECL, page_id="developers",
    )
    assert first == second
    assert meta_first == meta_second
    assert meta_second["phase0_composed_count"] == 1

    # Feed the FIRST run's output back in as the harvest — the shape a resumed
    # build sees. Exactly one FEATURES survives; none of them is a second
    # composition.
    third, meta_third = reconcile_page_sections(
        registry, first, declared=CAPE_DECL, page_id="developers",
    )
    assert meta_third["phase0_composed_count"] == 0
    features = [s for s in third if s["archetype"] == "FEATURES"]
    assert len(features) == 1, f"composed section accumulated: {len(features)} FEATURES"
    assert {o["group"]: o["reason"] for o in meta_third["phase0_omissions"]}["products"] == (
        "harvested_covers"
    )

    # And the provenance rows do not double either: one row per declared entry.
    assert len(features[0]["_phase0_provenance"]) == len(CAPE_DECL["products"])


def test_harvested_covering_the_archetype_suppresses_composition_in_the_reconciler():
    registry = [{"archetype": "HERO", "variant": "centered"}]
    sections, meta = reconcile_page_sections(
        registry, [HERO_BLOCK, PRODUCTS_BLOCK], declared=CAPE_DECL,
    )
    assert meta["phase0_composed_count"] == 0
    features = [s for s in sections if s["archetype"] == "FEATURES"]
    assert len(features) == 1
    assert features[0].get("_phase0_composed") is not True
