"""Classification loss — the content the classifier drops before any register sees it.

Task D5 of docs/superpowers/plans/2026-08-17-aurelix-complete-dag.md.

Two defects, one root cause:

  * A source block classified as an archetype whose slot contract cannot hold
    its items loses those items silently. `/merchants` 6 feature cards were
    classified `CTA/centered` (a template with no repeater) and emitted with a
    headline only; `/wealth` 3 cards were classified `PORTFOLIO/filtered-grid`
    (no template at all) and omitted as a library gap. Both were counted as
    successes.
  * Nothing compares what entered the harvest against what left it, because
    the classifier's output *is* the omission register's input.

The gate here answers the question no register asks: which harvested strings
left no trace in any emitted section.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from orchestrate import (  # noqa: E402
    ROOT,
    OUTPUT_DIR,
    archetype_item_capacity,
    classification_loss_report,
    item_shape_target,
    reclassify_sections_by_arity,
    reconcile_page_sections,
    omission_cause_for,
    nearest_variant_in_library,
    template_memo,
)
from lib.supabase_client import check_template_exists  # noqa: E402


def resolve_template(archetype, variant):
    return check_template_exists(archetype, variant, template_memo())


# ---------------------------------------------------------------------------
# Fixtures — synthetic blocks in the shape `build-site-spec.js` emits
# ---------------------------------------------------------------------------

def card(heading, body, image=None):
    return {
        "heading": heading,
        "body": body,
        "image": image,
        "cta": None,
        "headings": [heading],
        "body_text": [body] if body else [],
        "ctas": [],
        "images": [image] if image else [],
    }


def block(archetype, variant, index=0, items=(), section_headings=(), section_body=()):
    items = list(items)
    return {
        "index": index,
        "archetype": archetype,
        "variant": variant,
        "confidence": 0.6,
        "method": "embedded-body-keyword",
        "content": {
            "headings": list(section_headings) + [i["heading"] for i in items],
            "body_text": list(section_body) + [i["body"] for i in items if i["body"]],
            "ctas": [],
            "items": items,
            "item_count": len(items),
            "item_grouping": {"method": "sibling-repeat", "period": 1} if items else None,
            "section_headings": list(section_headings),
            "section_body_text": list(section_body),
        },
        "images": [],
    }


SIX_CARDS = [
    card("Crypto as a service", "We act as the crypto rails behind the scenes."),
    card("Load and verify your customers", "Onboard your own users through our API."),
    card("Fully developed API", "A mature, production REST API covering accounts."),
    card("Regulated and licensed", "Operate on the rails of a licensed South African FSP."),
    card("Built for scale", "High-volume infrastructure that grows with you."),
    card("Your brand, our engine", "Deliver a seamless crypto experience in your product."),
]


# ---------------------------------------------------------------------------
# 1. The gate
# ---------------------------------------------------------------------------

def test_gate_passes_when_every_harvested_string_is_placed():
    page = {"page_id": "merchants", "sections": [
        block("FEATURES", "icon-grid", items=SIX_CARDS,
              section_headings=["The crypto infrastructure behind your product"]),
    ]}
    rendered = " ".join(
        [c["heading"] + " " + c["body"] for c in SIX_CARDS]
        + ["The crypto infrastructure behind your product"]
    )
    report = classification_loss_report([page], {"merchants": rendered})
    assert report["verdict"] == "PASS", report
    assert report["summary"]["blocks_lost"] == 0
    assert report["summary"]["items_lost"] == 0


def test_gate_counts_a_block_that_left_no_trace_at_all():
    page = {"page_id": "about", "sections": [
        block("LOGO-BAR", "scrolling-marquee", items=[
            card("Aluma partner logo", ""), card("Numeral partner logo", "")]),
    ]}
    report = classification_loss_report([page], {"about": "Our story. Proudly South African."})
    assert report["verdict"] == "FAIL"
    assert report["summary"]["blocks_lost"] == 1
    assert report["pages"]["about"]["blocks"][0]["block_placed"] is False


def test_gate_counts_items_dropped_by_a_block_that_was_itself_placed():
    """The `/merchants` failure exactly: the block is emitted, the cards are not.

    This is the case every existing register calls a success, and it is the
    reason the gate compares items and not just blocks.
    """
    page = {"page_id": "merchants", "sections": [
        block("CTA", "centered", items=SIX_CARDS,
              section_headings=["The crypto infrastructure behind your product"]),
    ]}
    rendered = "The crypto infrastructure behind your product. Get started."
    report = classification_loss_report([page], {"merchants": rendered})
    assert report["verdict"] == "FAIL"
    assert report["summary"]["blocks_lost"] == 0, "the block itself was placed"
    assert report["summary"]["items_lost"] == 6
    lost = report["pages"]["merchants"]["blocks"][0]
    assert lost["archetype"] == "CTA"
    assert [i["heading"] for i in lost["items_lost_detail"]] == [c["heading"] for c in SIX_CARDS]


def test_gate_returns_not_measured_when_there_is_no_harvest():
    report = classification_loss_report([], {})
    assert report["verdict"] == "NOT_MEASURED"
    assert report["summary"]["blocks_total"] == 0


def test_gate_ignores_strings_too_short_to_trace():
    """A two-character string matches by accident; it is reported, never counted."""
    page = {"page_id": "about", "sections": [
        block("TRUST-BADGES", "icon-strip", items=[card("5+", ""), card("R1B+", "")]),
    ]}
    report = classification_loss_report([page], {"about": "nothing relevant here at all"})
    assert report["pages"]["about"]["blocks"][0]["items_untraceable"] == 2
    assert report["summary"]["items_lost"] == 0


# ---------------------------------------------------------------------------
# 2. Capacity + shape — the classifier signal
# ---------------------------------------------------------------------------

def test_a_template_with_a_repeater_can_hold_any_arity():
    cap = archetype_item_capacity("TRUST-BADGES", "icon-strip")
    assert cap >= 100, "badges[] is a repeater — it has no ceiling"


def test_a_template_with_no_repeater_and_no_array_can_hold_nothing():
    assert archetype_item_capacity("HERO", "centered") == 0


def test_an_archetype_the_library_does_not_carry_can_hold_nothing():
    assert archetype_item_capacity("PORTFOLIO", "filtered-grid") == 0


def test_heading_plus_body_cards_are_a_features_grid():
    assert item_shape_target(SIX_CARDS) == ("FEATURES", "icon-grid")


def test_image_only_items_are_a_logo_bar():
    logos = [card("Aluma", "", image={"src": "/a.svg", "alt": "Aluma"}),
             card("Numeral", "", image={"src": "/n.svg", "alt": "Numeral"})]
    assert item_shape_target(logos) == ("LOGO-BAR", "scrolling-marquee")


def test_person_cards_are_a_team_grid():
    people = [
        card("Leon Kowalski", "Founder and CEO. Built the exchange in 2020.",
             image={"src": "/leon.jpg", "alt": "Leon"}),
        card("Dave van Niekerk", "Backer. Chairman of Numeral.",
             image={"src": "/dave.jpg", "alt": "Dave"}),
    ]
    assert item_shape_target(people) == ("TEAM", "headshot-grid-square")


def test_a_single_item_is_not_a_repeater():
    assert item_shape_target([card("One thing", "One description")]) is None


# ---------------------------------------------------------------------------
# 3. Reclassification
# ---------------------------------------------------------------------------

def test_six_cards_under_cta_are_reclassified_to_features():
    sections = [block("CTA", "centered", items=SIX_CARDS,
                      section_headings=["The crypto infrastructure behind your product"])]
    out, moves = reclassify_sections_by_arity(sections)
    assert out[0]["archetype"] == "FEATURES"
    assert out[0]["variant"] == "icon-grid"
    assert moves[0]["from"] == "CTA/centered"
    assert moves[0]["item_count"] == 6
    assert moves[0]["capacity"] == 0


def test_three_cards_under_an_archetype_with_no_template_are_reclassified():
    sections = [block("PORTFOLIO", "filtered-grid", items=SIX_CARDS[:3])]
    out, _ = reclassify_sections_by_arity(sections)
    assert (out[0]["archetype"], out[0]["variant"]) == ("FEATURES", "icon-grid")


def test_a_footer_whose_repeater_holds_its_columns_is_left_alone():
    """FOOTER/mega columns are heading+links — the FEATURES shape. Capacity saves it."""
    cols = [card("Overview", "About"), card("Product", "Instant buy"),
            card("Support", "Help Centre")]
    out, moves = reclassify_sections_by_arity([block("FOOTER", "mega", items=cols)])
    assert out[0]["archetype"] == "FOOTER"
    assert moves == []


def test_a_hero_with_two_call_to_action_buttons_is_left_alone():
    ctas = [card("Get started", ""), card("Talk to sales", "")]
    out, moves = reclassify_sections_by_arity([block("HERO", "centered", items=ctas)])
    assert out[0]["archetype"] == "HERO"
    assert moves == []


def test_a_nav_is_never_reclassified_whatever_its_items_look_like():
    links = [card("Buy crypto", "Instant buy and sell"), card("Wealth", "For advisors"),
             card("Merchants", "Crypto rails"), card("About", "Our story")]
    out, moves = reclassify_sections_by_arity([block("NAV", "sticky-transparent", items=links)])
    assert out[0]["archetype"] == "NAV"
    assert moves == []


def test_reclassification_does_not_mutate_the_input():
    sections = [block("CTA", "centered", items=SIX_CARDS)]
    reclassify_sections_by_arity(sections)
    assert sections[0]["archetype"] == "CTA"


def test_reconcile_applies_the_arity_fix_to_the_harvest_spine():
    registry = [{"archetype": "HERO", "variant": "centered"},
                {"archetype": "FEATURES", "variant": "icon-grid"}]
    harvested = [block("CTA", "centered", items=SIX_CARDS)]
    final, meta = reconcile_page_sections(registry, harvested)
    assert final[0]["archetype"] == "FEATURES"
    assert meta["reclassified_count"] == 1
    # FEATURES is now present in the spine, so it is no longer gap-filled.
    assert [s["archetype"] for s in final if s.get("_registry_gap_fill")] == ["HERO"]


# ---------------------------------------------------------------------------
# 4. The omission register's causes
# ---------------------------------------------------------------------------

def test_a_gap_fill_omission_is_not_reported_as_a_harvest_failure():
    gap = {"archetype": "FAQ", "variant": "accordion", "content": {},
           "_registry_gap_fill": True}
    reason, cause = omission_cause_for(gap, {"filled": 0, "empty": 4})
    assert cause == "registry_gap_fill_no_source"
    assert "registry" in reason


def test_a_harvested_section_that_filled_nothing_is_still_a_harvest_failure():
    harvested = block("FAQ", "accordion", section_headings=["Questions"])
    reason, cause = omission_cause_for(harvested, {"filled": 0, "empty": 4})
    assert cause == "no_sourced_content"


def test_a_header_only_section_with_an_empty_repeater_is_an_omission():
    """`homepage/06-faq` renders `null`: title filled, zero Q&A rows."""
    harvested = block("FAQ", "accordion", section_headings=["Questions"])
    coverage = {"filled": 2, "empty": 2,
                "filled_slots": ["section_title", "section_subtitle"],
                "repeat_rows": {"faqs": []}}
    reason, cause = omission_cause_for(harvested, coverage)
    assert cause == "declared_repeater_no_rows"


def test_a_section_with_real_body_copy_and_an_empty_repeater_is_kept():
    harvested = block("ABOUT", "editorial-split", section_body=["Our story begins in 2020."])
    coverage = {"filled": 2, "empty": 1,
                "filled_slots": ["section_title", "section_body"],
                "repeat_rows": {"paragraphs": []}}
    assert omission_cause_for(harvested, coverage) is None


# ---------------------------------------------------------------------------
# 5. Nearest-variant fallback
# ---------------------------------------------------------------------------

def test_an_unknown_variant_falls_back_to_a_sibling_the_library_carries():
    got = nearest_variant_in_library("HERO", "banner-with-video")
    assert got, "HERO has siblings in the library"
    assert resolve_template("HERO", got) is not None, f"HERO/{got} does not resolve"


def test_a_variant_the_library_carries_is_never_rewritten():
    assert nearest_variant_in_library("HERO", "centered") is None


def test_an_archetype_the_library_does_not_carry_has_no_nearest_variant():
    assert nearest_variant_in_library("CODE-BLOCK", "api-reference") is None


# ---------------------------------------------------------------------------
# 6. The live build — real data, no rebuild required
# ---------------------------------------------------------------------------

CAPE = OUTPUT_DIR / "cape-crypto" / "site-spec.json"


def live_pages():
    if not CAPE.exists():
        pytest.skip("no cape-crypto build on disk")
    return json.loads(CAPE.read_text()).get("pages", [])


def page_named(pages, page_id):
    for p in pages:
        if p.get("page_id") == page_id:
            return p
    pytest.skip(f"no {page_id} page in the live site-spec")


def test_live_merchants_feature_block_is_reclassified_off_cta():
    page = page_named(live_pages(), "merchants")
    out, moves = reclassify_sections_by_arity(page["sections"])
    moved = [m for m in moves if m["item_count"] == 6]
    assert moved, f"the 6-card block was not moved: {moves}"
    assert moved[0]["to"] == "FEATURES/icon-grid"
    assert moved[0]["from"] == "CTA/centered"


def test_live_wealth_feature_block_is_reclassified_off_portfolio():
    page = page_named(live_pages(), "wealth")
    _, moves = reclassify_sections_by_arity(page["sections"])
    assert [m["from"] for m in moves] == ["PORTFOLIO/filtered-grid"]


def test_live_nav_and_footer_survive_reclassification_on_every_page():
    for page in live_pages():
        out, _ = reclassify_sections_by_arity(page["sections"])
        before = [s["archetype"] for s in page["sections"]]
        after = [s["archetype"] for s in out]
        for i, arch in enumerate(before):
            if arch in ("NAV", "FOOTER", "HERO"):
                assert after[i] == arch, f"{page['page_id']}[{i}] {arch} -> {after[i]}"
