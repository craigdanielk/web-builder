"""Task C1 — the build reads phase 0, and says so.

The fact under test: `phase0` is a legal provenance source and the build has
never produced one, while cape-crypto declares 7 products and 5 content pillars
across 86 phase-0 fields.

The fixture below is the REAL cape-crypto declaration, read from Supabase on
2026-08-17 (`load_tenant_context("cape-crypto")["phase0_field_values"]`) and
inlined so these tests need no network.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from lib.phase0_content import (  # noqa: E402
    DECLARED_FIELDS,
    DeclarationNotMeasured,
    declared_content,
    field_key_for_slot,
)

CAPE_PRODUCTS = [
    "Spot exchange (order book)",
    "Quick Buy / Quick Sell",
    "Bitcoin Lightning send/receive",
    "Cape Crypto Wealth — managed crypto for FSPs and advisors "
    "(DCA, automated buying, portfolio management)",
    "Merchant Services — crypto-as-a-service rails for fintechs and banks",
    "Developer REST API v2 (accounts, funding, trading, market data, "
    "withdrawals, webhooks)",
    "iOS and Android apps",
]

CAPE_PILLARS = [
    "South African crypto regulation and exchange-control policy",
    "Bitcoin macro and price context for a ZAR-denominated audience",
    "Stablecoins and cross-border payment rails in Africa",
    "Blockchain applied to South African public-sector and institutional problems",
    "AI x crypto and emerging technology",
]

CAPE_CRYPTO_CTX = {
    "slug": "cape-crypto",
    "load_status": "ok",
    "phase0_field_values": {
        "product_list": CAPE_PRODUCTS,
        "content_pillars": CAPE_PILLARS,
        "competitive_positioning": '"Lowest trade fees in SA" — 0.07% taker '
                                   "on the order book.",
        "licenses": [
            "FSP No. 53746 — authorised Financial Services Provider "
            "(FSCA, South Africa)"
        ],
    },
}


def test_products_and_pillars_are_read_with_their_field_keys():
    dc = declared_content(CAPE_CRYPTO_CTX)
    assert len(dc["products"]) == 7
    assert len(dc["pillars"]) == 5
    assert all(p["field_key"] for p in dc["products"])
    assert dc["products"][0]["field_key"] == "product_list[0]"
    assert dc["pillars"][4]["field_key"] == "content_pillars[4]"
    # The declared entry is preserved verbatim alongside the split.
    assert dc["products"][0]["value"] == CAPE_PRODUCTS[0]


def test_a_declared_entry_splits_into_title_and_body_without_authoring():
    dc = declared_content(CAPE_CRYPTO_CTX)
    wealth = dc["products"][3]
    assert wealth["title"] == "Cape Crypto Wealth"
    assert wealth["body"].startswith("managed crypto for FSPs and advisors")
    # An entry with no separator keeps its whole text as the title and has no
    # body — nothing is written to fill the gap.
    assert dc["products"][0]["title"] == "Spot exchange (order book)"
    assert dc["products"][0]["body"] == ""


def test_an_undeclared_field_is_absent_not_empty_string():
    dc = declared_content({"phase0_field_values": {}})
    assert dc["products"] == []
    assert dc["pillars"] == []
    assert dc["proof"] == []
    assert dc["positioning"] is None


def test_unmeasurable_context_refuses():
    """load_tenant_context never raises; an unreachable Supabase must not read
    as 'this tenant declared nothing'."""
    with pytest.raises(DeclarationNotMeasured):
        declared_content({"load_status": "unreachable"})
    with pytest.raises(DeclarationNotMeasured):
        declared_content({"load_status": "unconfigured"})
    with pytest.raises(DeclarationNotMeasured):
        declared_content(None)


def test_positioning_and_proof_are_read():
    dc = declared_content(CAPE_CRYPTO_CTX)
    assert dc["positioning"].startswith('"Lowest trade fees in SA"')
    assert len(dc["proof"]) == 1
    assert dc["proof"][0]["field_key"] == "licenses[0]"


def test_field_key_for_slot_names_the_declared_entry():
    # Array slots — the spelling FEATURES/icon-grid actually uses.
    assert field_key_for_slot("features[4].title", "product_list") == "product_list[3]"
    assert field_key_for_slot("features[1].description", "product_list") == "product_list[0]"
    # Flat numbered slots — the other spelling in the library.
    assert field_key_for_slot("feature_3_title", "product_list") == "product_list[2]"
    assert field_key_for_slot("feature_1_description", "product_list") == "product_list[0]"
    assert field_key_for_slot("section_title", "product_list") == "product_list"


def test_declared_fields_are_named_once():
    """The field names are the join to Supabase; a second copy would drift."""
    assert DECLARED_FIELDS["products"] == "product_list"
    assert DECLARED_FIELDS["pillars"] == "content_pillars"
