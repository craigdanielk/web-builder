"""The tenant's declared regulatory position reaches the build, or the build stops.

Cape Crypto is an authorised FSP (No. 53746). Its phase-0 record declares four
`required_disclaimers` and nine `prohibited_terms`. Before this layer existed the
build read neither: the footer shipped with no disclosure at all and nothing
checked the copy against the ban list. These tests pin the two rules that makes
that impossible to repeat quietly — declared text is carried verbatim, and
declared bans fail the build loudly.

Run: python3 scripts/test_tenant_compliance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.tenant_context import (  # noqa: E402
    ComplianceNotDeclared,
    ProhibitedTermFound,
    assert_no_prohibited_terms,
    compliance_declaration,
    prohibited_terms,
    required_disclaimers,
    scan_prohibited_terms,
)

FSP_DISCLAIMER = (
    "Cape Crypto (Pty) Ltd is an authorised financial services provider "
    "(FSP No. 53746)."
)
CAPITAL_DISCLAIMER = "Investing in crypto assets may result in the loss of capital."

CAPE_CRYPTO = {
    "slug": "cape-crypto",
    "phase0_field_values": {
        "required_disclaimers": [FSP_DISCLAIMER, CAPITAL_DISCLAIMER],
        "prohibited_terms": [
            "investment advice", "financial advice", "guaranteed returns",
            "risk-free", "we recommend",
        ],
        "prohibited_language": ["financial advice framing", "return guarantees"],
        "licenses": ["FSP No. 53746 — authorised Financial Services Provider"],
        "regulatory_body": "Financial Sector Conduct Authority (FSCA), South Africa",
    },
}

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))
        FAILURES.append(name)


# ── The declaration is read, normalised, and never invented ────────────────

def test_declaration() -> None:
    print("\ncompliance_declaration")
    d = compliance_declaration(CAPE_CRYPTO)
    check("carries both declared disclaimers", d["required_disclaimers"] == [FSP_DISCLAIMER, CAPITAL_DISCLAIMER])
    check("carries the declared ban list", len(d["prohibited_terms"]) == 5)
    check("a licensed tenant reads as regulated", d["regulated"] is True)

    empty = compliance_declaration(None)
    check("no tenant declares nothing", empty["required_disclaimers"] == [] and empty["declared"] is False)
    check("no tenant is not 'regulated'", empty["regulated"] is False)

    # A hand-entered single string and a JSON-encoded list are the same
    # declaration as a jsonb list; anything else is not coerced into copy.
    check("bare string is one disclaimer",
          compliance_declaration({"phase0_field_values": {"required_disclaimers": FSP_DISCLAIMER}})
          ["required_disclaimers"] == [FSP_DISCLAIMER])
    check("JSON-encoded list is unpacked",
          compliance_declaration({"phase0_field_values": {"required_disclaimers": '["a", "b"]'}})
          ["required_disclaimers"] == ["a", "b"])
    check("a dict is not a disclaimer",
          compliance_declaration({"phase0_field_values": {"required_disclaimers": {"text": "x"}}})
          ["required_disclaimers"] == [])
    check("blank entries are dropped",
          compliance_declaration({"phase0_field_values": {"required_disclaimers": ["", "  ", "real"]}})
          ["required_disclaimers"] == ["real"])


def test_required_disclaimers() -> None:
    print("\nrequired_disclaimers")
    check("verbatim, in declared order",
          required_disclaimers(CAPE_CRYPTO) == [FSP_DISCLAIMER, CAPITAL_DISCLAIMER])
    check("no tenant is permissive by default", required_disclaimers(None) == [])

    # `require=True` is the mode for a build that already knows it is shipping a
    # regulated site. Silence is the failure it exists to convert into a stop.
    for label, ctx in (("no tenant context", None),
                       ("tenant declaring none", {"slug": "x", "phase0_field_values": {}})):
        try:
            required_disclaimers(ctx, require=True)
            check(f"require=True refuses on {label}", False, "returned instead of raising")
        except ComplianceNotDeclared as exc:
            check(f"require=True refuses on {label}", True)
            check(f"  … and the message says how to fix it ({label})",
                  "phase 0" in str(exc) or "--tenant" in str(exc))
    check("require=True is a no-op when declared",
          required_disclaimers(CAPE_CRYPTO, require=True) == [FSP_DISCLAIMER, CAPITAL_DISCLAIMER])


# ── The ban list is enforced, with the two exceptions that make it usable ──

def test_scan() -> None:
    print("\nscan_prohibited_terms")
    terms = prohibited_terms(CAPE_CRYPTO)

    hits = scan_prohibited_terms("Our team offers financial advice to every client.", terms)
    check("plain occurrence is found", len(hits) == 1 and hits[0]["term"] == "financial advice")
    check("occurrence is not marked negated", hits[0]["negated"] is False)
    check("hit carries a readable excerpt", "financial advice" in hits[0]["excerpt"])

    check("case is ignored", len(scan_prohibited_terms("GUARANTEED RETURNS", terms)) == 1)
    check("a line wrap does not hide a phrase",
          len(scan_prohibited_terms("guaranteed\n      returns", terms)) == 1)
    check("word boundaries hold",
          scan_prohibited_terms("risk-freedom is not a word", terms) == []
          or all(h["term"] != "risk-free" for h in scan_prohibited_terms("risk-freedom", terms)))
    check("clean copy is clean",
          scan_prohibited_terms("Buy Bitcoin in a minute with the lowest fees in SA.", terms) == [])

    # A disclaimer denying a thing contains the name of the thing. That is the
    # tenant satisfying the rule, so it is reported and not counted.
    neg = scan_prohibited_terms(
        "This does not constitute financial advice or a recommendation.", terms)
    check("a negated occurrence is still reported", len(neg) == 1)
    check("… and is marked negated", neg[0]["negated"] is True)

    # A tenant's own declared disclosure can never trip its own ban list.
    exempt_hits = scan_prohibited_terms(
        f"Sign up today. {FSP_DISCLAIMER}",
        ["financial services provider"],
        exempt=[FSP_DISCLAIMER],
    )
    check("declared disclaimer text is exempt", exempt_hits == [])
    check("… and exemption does not shift other offsets",
          scan_prohibited_terms(
              f"{FSP_DISCLAIMER} We offer financial advice.", terms, exempt=[FSP_DISCLAIMER],
          )[0]["match"] == "financial advice")


def test_assert() -> None:
    print("\nassert_no_prohibited_terms")
    clean = {"01-hero.tsx": "Buy Bitcoin within a minute. Lowest trading fees in South Africa."}
    check("clean build passes", assert_no_prohibited_terms(clean, CAPE_CRYPTO) == [])

    check("a tenant with no ban list is a no-op",
          assert_no_prohibited_terms({"x.tsx": "guaranteed returns"}, None) == [])

    try:
        assert_no_prohibited_terms(
            {"03-cta.tsx": "Open an account for guaranteed returns."}, CAPE_CRYPTO)
        check("a violation stops the build", False, "did not raise")
    except ProhibitedTermFound as exc:
        check("a violation stops the build", True)
        check("… naming the file", "03-cta.tsx" in str(exc))
        check("… naming the term", "guaranteed returns" in str(exc))

    allowed = assert_no_prohibited_terms(
        {"Footer.tsx": "Nothing here is investment advice."}, CAPE_CRYPTO)
    check("a negation passes but is returned, not hidden",
          len(allowed) == 1 and allowed[0]["origin"] == "Footer.tsx")


# ── The live record: the regression this layer exists for ──────────────────

def test_live_tenant() -> None:
    print("\nlive cape-crypto record (skipped without Supabase credentials)")
    try:
        from lib.tenant_context import load_tenant_context
        ctx = load_tenant_context("cape-crypto")
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"  – skipped: {exc}")
        return
    if not ctx.get("available"):
        print("  – skipped: tenant record not reachable")
        return
    d = ctx["compliance"]
    check("live record declares disclaimers", len(d["required_disclaimers"]) > 0,
          "phase 0 has no required_disclaimers for an authorised FSP")
    check("live record declares prohibited terms", len(d["prohibited_terms"]) > 0)
    check("live FSP number is present verbatim",
          any("53746" in s for s in d["required_disclaimers"] + d["licenses"]))
    check("load_tenant_context exposes compliance", "compliance" in ctx)


if __name__ == "__main__":
    test_declaration()
    test_required_disclaimers()
    test_scan()
    test_assert()
    test_live_tenant()
    print()
    if FAILURES:
        print(f"❌ {len(FAILURES)} failed: {', '.join(FAILURES)}")
        sys.exit(1)
    print("✅ all compliance checks passed")
