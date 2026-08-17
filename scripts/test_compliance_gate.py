"""Tests for the build-time compliance gate.

The declarations used here are the REAL cape-crypto and xago declarations,
copied verbatim from `docs/census/2026-08-17-phase0-declarations.md` §2 Q5.
They are inlined rather than loaded from Supabase so the suite is
hermetic — a network flake must never turn a compliance test green.

The load-bearing case is `test_the_four_real_disclaimers_are_not_violations`:
cape-crypto's required disclaimer #3 reads "…does not constitute advice,
inducement or recommendation to invest in crypto-currencies", which sits one
word from the prohibited `recommendation to buy` and contains `advice`. A
naive scanner fails the build on the tenant's own mandatory disclosure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.compliance_gate import (  # noqa: E402
    ComplianceFailure,
    compliance_gate,
)

# ─── The real declarations (census X1, 2026-08-17) ────────────────

CAPE_DISCLAIMERS = [
    "Cape Crypto (Pty) Ltd is an authorised financial services provider (FSP No. 53746).",
    "Investing in crypto assets may result in the loss of capital.",
    "Information is provided for informational purposes only and does not "
    "constitute advice, inducement or recommendation to invest in crypto-currencies.",
    "Non-US citizen attestation at registration",
]

CAPE_PROHIBITED = [
    "investment advice",
    "financial advice",
    "recommendation to buy",
    "guaranteed returns",
    "risk-free",
    "guaranteed profit",
    "get rich",
    "we recommend",
    "you should buy",
]

CAPE_CTX = {
    "slug": "cape-crypto",
    "phase0_field_values": {
        "required_disclaimers": CAPE_DISCLAIMERS,
        "prohibited_terms": CAPE_PROHIBITED,
        "prohibited_language": [
            "financial advice framing",
            "return guarantees",
            "price predictions stated as fact",
            "urgency/FOMO pressure tactics",
        ],
        "licenses": ["FSP No. 53746"],
        "regulatory_body": "FSCA (South Africa)",
    },
}

XAGO_CTX = {
    "slug": "xago",
    "phase0_field_values": {
        "required_disclaimers": [
            "Cryptocurrencies are volatile by nature and represent a high-risk "
            "investment. Do not invest money you cannot afford to lose."
        ],
        "prohibited_terms": [],
        "licenses": ["FSP No. 53416 (FSCA)"],
        "regulatory_body": "FSCA (South Africa); AUSTRAC (Australia)",
    },
}

#: A tenant whose context loaded as empty. `load_tenant_context` never raises
#: (`tenant_context.py:58-67`), so this is indistinguishable from an
#: unreachable Supabase — which is exactly why it must not be a PASS.
UNDECLARED_CTX = {"slug": "nobody", "phase0_field_values": {}}


# ─── Site fixture ─────────────────────────────────────────────────

def _footer(disclaimers, extra_body=""):
    paras = "\n".join(
        '          <p key={%d} className="leading-relaxed">{%s}</p>'
        % (i, json.dumps(d))
        for i, d in enumerate(disclaimers)
    )
    return (
        '"use client";\n\n'
        "export default function Footer() {\n"
        "  return (\n"
        '    <footer className="border-t">\n'
        '      <div className="mx-auto max-w-6xl px-6 py-12">\n'
        f"{extra_body}\n"
        f"{paras}\n"
        "      </div>\n"
        "    </footer>\n"
        "  );\n"
        "}\n"
    )


def make_site(tmp_path, *, disclaimers=None, hero_body="", footer_extra=""):
    """A minimal but structurally real generated site tree."""
    site = tmp_path / "site"
    (site / "src" / "app").mkdir(parents=True)
    (site / "src" / "components" / "layout").mkdir(parents=True)
    (site / "src" / "components" / "sections" / "homepage").mkdir(parents=True)

    (site / "src" / "components" / "layout" / "Footer.tsx").write_text(
        _footer(CAPE_DISCLAIMERS if disclaimers is None else disclaimers,
                extra_body=footer_extra)
    )
    (site / "src" / "app" / "layout.tsx").write_text(
        'import Footer from "@/components/layout/Footer";\n'
        "export default function RootLayout({ children }) {\n"
        "  return <html><body>{children}<Footer /></body></html>;\n"
        "}\n"
    )
    (site / "src" / "components" / "sections" / "homepage" / "01-hero.tsx").write_text(
        '"use client";\n\n'
        "export default function Hero() {\n"
        "  return (\n"
        "    <section>\n"
        "      <h1>Buy and sell crypto in South Africa</h1>\n"
        f"{hero_body}\n"
        "    </section>\n"
        "  );\n"
        "}\n"
    )
    # node_modules must never be scanned — it is not this build's copy.
    (site / "node_modules" / "junk").mkdir(parents=True)
    (site / "node_modules" / "junk" / "index.js").write_text(
        "// we recommend guaranteed returns\nexport const x = 'guaranteed profit';\n"
    )
    return site


def make_artifacts(tmp_path, slots):
    """Harvested provenance beside the site, as the real build writes it."""
    d = tmp_path / "section-artifacts" / "homepage"
    d.mkdir(parents=True)
    (d / "02-trust_badges.json").write_text(json.dumps({
        "archetype": "TRUST-BADGES",
        "provenance": [
            {"section_uid": "52b1e8601cf7", "slot": slot,
             "value": value, "source": "harvested"}
            for slot, value in slots
        ],
    }))
    return d


# ─── The disclaimer/prohibited-term collision ─────────────────────

def test_the_four_real_disclaimers_are_not_violations(tmp_path):
    """cape-crypto's own mandatory disclosure must never fail its own ban list."""
    site = make_site(tmp_path)
    r = compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert r["status"] == "pass", r
    assert r["violations"] == []
    assert r["missing_disclaimers"] == []


def test_violation_on_the_page_carrying_the_disclaimers_is_still_caught(tmp_path):
    """Exempting the disclaimer spans must not blind the rest of the file."""
    site = make_site(
        tmp_path,
        footer_extra='          <p>We recommend the Growth plan for new traders.</p>',
    )
    with pytest.raises(ComplianceFailure) as e:
        compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    msg = str(e.value)
    assert "we recommend" in msg
    assert "Footer.tsx" in msg
    # …and the disclaimers on that same file are still recognised as present.
    assert "missing" not in msg.lower()


# ─── Prohibited terms ─────────────────────────────────────────────

def test_injected_prohibited_term_fails_naming_term_and_file(tmp_path):
    site = make_site(tmp_path, hero_body="      <p>Guaranteed returns, every month.</p>")
    with pytest.raises(ComplianceFailure) as e:
        compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    msg = str(e.value)
    assert "guaranteed returns" in msg
    assert "01-hero.tsx" in msg

    r = e.value.result
    assert r["status"] == "fail"
    assert len(r["violations"]) == 1
    v = r["violations"][0]
    assert v["term"] == "guaranteed returns"
    assert v["file"].endswith("01-hero.tsx")
    assert "Guaranteed returns" in v["excerpt"]

    # The reported line is the line the phrase is actually on, 1-based —
    # derived from the file, not hardcoded, so the fixture can grow.
    hero = Path(v["file"]).read_text().splitlines()
    assert "Guaranteed returns" in hero[v["line"] - 1]


def test_a_comment_is_not_markup(tmp_path):
    """`a95d7128` — a template's prose about a phrase is not the phrase shipping."""
    site = make_site(
        tmp_path,
        hero_body=(
            "      {/* Never write copy promising guaranteed returns here. */}\n"
            "      // we recommend nothing; this is a note\n"
        ),
    )
    r = compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert r["status"] == "pass", r["violations"]


def test_node_modules_is_not_scanned(tmp_path):
    site = make_site(tmp_path)
    r = compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert r["status"] == "pass", r["violations"]


def test_harvested_copy_is_scanned(tmp_path):
    site = make_site(tmp_path)
    make_artifacts(tmp_path, [("badges[1].detail", "Risk-free trading, always")])
    with pytest.raises(ComplianceFailure) as e:
        compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    msg = str(e.value)
    assert "risk-free" in msg
    assert "02-trust_badges.json" in msg
    assert "badges[1].detail" in msg


def test_clean_harvested_copy_passes(tmp_path):
    site = make_site(tmp_path)
    make_artifacts(tmp_path, [("badges[1].detail", "Years operating")])
    r = compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert r["status"] == "pass", r["violations"]


def test_negated_occurrence_is_allowed_but_reported(tmp_path):
    site = make_site(
        tmp_path,
        hero_body="      <p>Cape Crypto does not offer guaranteed returns.</p>",
    )
    r = compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert r["status"] == "pass"
    assert [h["term"] for h in r["allowed_negated"]] == ["guaranteed returns"]


# ─── Required disclaimers ─────────────────────────────────────────

def test_missing_required_disclaimer_fails_naming_it(tmp_path):
    site = make_site(tmp_path, disclaimers=CAPE_DISCLAIMERS[1:])
    with pytest.raises(ComplianceFailure) as e:
        compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    msg = str(e.value)
    assert "FSP" in msg
    assert e.value.result["missing_disclaimers"] == [CAPE_DISCLAIMERS[0]]


def test_all_disclaimers_missing_fails_naming_all_four(tmp_path):
    site = make_site(tmp_path, disclaimers=[])
    with pytest.raises(ComplianceFailure) as e:
        compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert e.value.result["missing_disclaimers"] == CAPE_DISCLAIMERS


def test_a_disclaimer_only_in_a_comment_does_not_count_as_present(tmp_path):
    """The same masking rule, pointed the other way: prose is not disclosure."""
    site = make_site(tmp_path, disclaimers=CAPE_DISCLAIMERS[1:],
                     footer_extra="          {/* %s */}" % CAPE_DISCLAIMERS[0])
    with pytest.raises(ComplianceFailure) as e:
        compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert e.value.result["missing_disclaimers"] == [CAPE_DISCLAIMERS[0]]


def test_disclaimer_match_is_whitespace_flexible(tmp_path):
    """JSX wraps long strings; a line break inside the text is still the text."""
    wrapped = list(CAPE_DISCLAIMERS)
    site = make_site(tmp_path, disclaimers=wrapped[1:])
    (site / "src" / "components" / "layout" / "Extra.tsx").write_text(
        "export const D = (\n  <p>\n    Cape Crypto (Pty) Ltd is an authorised\n"
        "    financial services provider (FSP No. 53746).\n  </p>\n);\n"
    )
    r = compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert r["status"] == "pass", r


# ─── NOT_MEASURED — the failure this system must never make ───────

def test_no_tenant_is_not_measured_not_pass(tmp_path):
    site = make_site(tmp_path)
    r = compliance_gate(site, tenant=None)
    assert r["status"] == "not_measured"
    assert r["violations"] == []


def test_empty_declaration_is_not_measured_not_pass(tmp_path):
    """An unreachable Supabase and an empty tenant are indistinguishable."""
    site = make_site(tmp_path)
    r = compliance_gate(site, tenant="nobody", tenant_context=UNDECLARED_CTX)
    assert r["status"] == "not_measured"
    assert "declar" in r["reason"].lower()


def test_missing_site_dir_is_not_measured_not_pass(tmp_path):
    r = compliance_gate(tmp_path / "does-not-exist", tenant="cape-crypto",
                        tenant_context=CAPE_CTX)
    assert r["status"] == "not_measured"


def test_site_dir_with_no_scannable_files_is_not_measured(tmp_path):
    empty = tmp_path / "site"
    (empty / "src").mkdir(parents=True)
    r = compliance_gate(empty, tenant="cape-crypto", tenant_context=CAPE_CTX)
    assert r["status"] == "not_measured"


def test_not_measured_never_raises(tmp_path):
    """NOT_MEASURED is a third outcome, not a failure and not a pass."""
    site = make_site(tmp_path)
    r = compliance_gate(site, tenant=None, raise_on_fail=True)
    assert r["status"] == "not_measured"


# ─── xago: zero prohibited terms is a declaration, not a gap ──────

def test_xago_declares_zero_prohibited_terms_and_passes(tmp_path):
    site = make_site(tmp_path, disclaimers=XAGO_CTX["phase0_field_values"]
                     ["required_disclaimers"])
    r = compliance_gate(site, tenant="xago", tenant_context=XAGO_CTX)
    assert r["status"] == "pass", r
    assert r["prohibited_terms_declared"] == 0


def test_xago_still_fails_on_its_missing_disclaimer(tmp_path):
    site = make_site(tmp_path, disclaimers=[])
    with pytest.raises(ComplianceFailure) as e:
        compliance_gate(site, tenant="xago", tenant_context=XAGO_CTX)
    assert "volatile by nature" in str(e.value)


def test_cape_prohibited_terms_do_not_apply_to_xago(tmp_path):
    site = make_site(
        tmp_path,
        disclaimers=XAGO_CTX["phase0_field_values"]["required_disclaimers"],
        hero_body="      <p>Guaranteed returns on every trade.</p>",
    )
    r = compliance_gate(site, tenant="xago", tenant_context=XAGO_CTX)
    assert r["status"] == "pass"


# ─── Contract shape ───────────────────────────────────────────────

def test_raise_on_fail_false_returns_the_same_verdict(tmp_path):
    site = make_site(tmp_path, hero_body="      <p>Guaranteed returns.</p>")
    r = compliance_gate(site, tenant="cape-crypto", tenant_context=CAPE_CTX,
                        raise_on_fail=False)
    assert r["status"] == "fail"
    assert {"term", "file", "line", "excerpt"} <= set(r["violations"][0])
