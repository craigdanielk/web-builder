#!/usr/bin/env python3
"""
Industry precedence — one declared source, ranked, never silently reconciled.

WHY THIS EXISTS
---------------
Industry is declared in three places with no stated precedence:

  1. `phase0_field_values.industry` / `.verticals`  (the tenant's own declaration)
  2. `tenants.industry`                             (a column, NULL for both live tenants)
  3. `aurelix-uiux-audit/lib/industry_resolver.py`  (keyword + URL pattern -> handle + confidence)

Nothing said which wins, so preset selection and benchmark selection could
silently disagree about what the tenant *is*. `resolve_industry` fixes the
order — phase0 > tenants > resolver — records disagreement instead of
reconciling it, and refuses when no source exists rather than guessing.

Two honesty rules are under test here as much as the precedence:

  * An UNMEASURABLE context is not an undeclared one. `load_tenant_context`
    never raises (`_safe_get` swallows every error and returns []), so an
    unreachable Supabase and a genuinely empty tenant look identical. We treat
    `available=False` / no `tenant_id` as NOT_MEASURED and refuse — we do not
    fall through to the keyword guesser, which would turn an outage into a
    confident industry.
  * A declared handle is returned verbatim. It is NOT mapped onto the 29
    `industry_styles` handles; `handle_in_registry` reports whether it is one,
    and consumers that need a registry handle must check. Mapping free text
    onto a handle would be invention.

Run: python3 scripts/test_industry_precedence.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.industry import (  # noqa: E402
    IndustryContextUnmeasured,
    IndustryUndeclared,
    resolve_industry,
)

FAILURES = []


def check(name, fn):
    try:
        fn()
    except AssertionError as exc:
        FAILURES.append((name, f"AssertionError: {exc}"))
        print("FAIL  " + name + f"  -- {exc}")
    except Exception as exc:  # noqa: BLE001 - a crash is a failure, reported as one
        FAILURES.append((name, f"{type(exc).__name__}: {exc}"))
        print("ERROR " + name + f"  -- {type(exc).__name__}: {exc}")
    else:
        print("ok    " + name)


def _ctx(phase0=None, tenant=None, available=True, tenant_id="00000000-0000-0000-0000-000000000001"):
    return {
        "tenant_id": tenant_id,
        "slug": "fixture",
        "phase0_field_values": phase0 or {},
        "tenant": tenant or {},
        "available": available,
    }


# ── Precedence ────────────────────────────────────────────────────────────

def test_phase0_declaration_wins_over_tenants_column():
    r = resolve_industry(_ctx({"industry": "crypto-exchange"}, {"industry": "fintech"}))
    assert r["handle"] == "crypto-exchange", r
    assert r["source"] == "phase0", r
    assert r["confidence"] is None, r
    assert r["disagreement"] == "tenants.industry=fintech", r


def test_agreeing_sources_record_no_disagreement():
    r = resolve_industry(_ctx({"industry": "fintech"}, {"industry": "fintech"}))
    assert r["source"] == "phase0", r
    assert r["disagreement"] is None, r


def test_verticals_first_entry_is_the_phase0_declaration_when_industry_absent():
    """cape-crypto's real shape: no `industry` key, `verticals` list[3]."""
    r = resolve_industry(_ctx({"verticals": ["Crypto exchange (retail)", "Wealth management"]}))
    assert r["handle"] == "Crypto exchange (retail)", r
    assert r["source"] == "phase0", r
    assert r["field"] == "verticals[0]", r
    assert r["handle_in_registry"] is False, r


def test_tenants_column_used_when_phase0_is_silent():
    r = resolve_industry(_ctx({}, {"industry": "fintech"}))
    assert r["handle"] == "fintech", r
    assert r["source"] == "tenants", r
    assert r["confidence"] is None, r
    assert r["handle_in_registry"] is True, r


def test_resolver_is_fallback_only_and_records_confidence():
    r = resolve_industry(_ctx({}), url="https://example.com/crypto-exchange/pricing")
    assert r["source"] == "resolver", r
    assert 0.0 <= r["confidence"] <= 1.0, r
    assert r["confidence"] > 0.0, r


def test_resolver_not_consulted_when_anything_is_declared():
    """A declared industry must not be second-guessed by the keyword guesser."""
    r = resolve_industry(
        _ctx({"industry": "artisan-food"}), url="https://example.com/crypto-exchange/pricing"
    )
    assert r["source"] == "phase0", r
    assert r["handle"] == "artisan-food", r


# ── Refusal ───────────────────────────────────────────────────────────────

def test_no_source_refuses():
    try:
        resolve_industry(_ctx({}), url=None)
    except IndustryUndeclared:
        return
    raise AssertionError("expected IndustryUndeclared, got a handle")


def test_url_with_no_signal_refuses_rather_than_guessing():
    """`capecrypto.com` scores 0.0 against every signal — no \\b before 'crypto'."""
    try:
        resolve_industry(_ctx({}), url="https://capecrypto.com")
    except IndustryUndeclared:
        return
    raise AssertionError("expected IndustryUndeclared for an unscoreable url")


def test_unmeasurable_context_is_not_an_undeclared_one():
    """Supabase down looks exactly like an empty tenant. Refuse, do not guess."""
    ctx = _ctx({}, available=False, tenant_id=None)
    try:
        resolve_industry(ctx, url="https://example.com/crypto-exchange/pricing")
    except IndustryContextUnmeasured as exc:
        assert "NOT_MEASURED" in str(exc), exc
        return
    raise AssertionError("expected IndustryContextUnmeasured; resolver must not run")


def test_none_context_is_unmeasured_not_undeclared():
    try:
        resolve_industry(None)
    except IndustryContextUnmeasured:
        return
    raise AssertionError("expected IndustryContextUnmeasured for a None context")


# ── Live tenants ──────────────────────────────────────────────────────────

def test_real_cape_crypto_context_resolves_to_its_declared_vertical():
    from lib.tenant_context import load_tenant_context

    ctx = load_tenant_context("cape-crypto")
    if not ctx.get("available"):
        raise AssertionError("cape-crypto context unavailable — NOT_MEASURED, not a pass")
    r = resolve_industry(ctx)
    assert r["source"] == "phase0", r
    assert r["handle"] == "Crypto exchange (retail)", r
    assert r["disagreement"] is None, r  # tenants.industry is NULL


def test_real_cape_crypto_declaration_survives_a_scoreable_url():
    """The live case the precedence exists for: a real declaration + a URL the
    keyword guesser would happily classify as `fintech`."""
    from lib.tenant_context import load_tenant_context

    ctx = load_tenant_context("cape-crypto")
    if not ctx.get("available"):
        raise AssertionError("cape-crypto context unavailable — NOT_MEASURED, not a pass")
    r = resolve_industry(ctx, url="https://capecrypto.com/buy-crypto")
    assert r["source"] == "phase0", r
    assert r["handle"] == "Crypto exchange (retail)", r
    assert r["confidence"] is None, r


def test_real_xago_context_resolves_to_its_declared_vertical():
    from lib.tenant_context import load_tenant_context

    ctx = load_tenant_context("xago")
    if not ctx.get("available"):
        raise AssertionError("xago context unavailable — NOT_MEASURED, not a pass")
    r = resolve_industry(ctx)
    assert r["source"] == "phase0", r
    assert r["handle"] == "Cross-border payments", r


TESTS = [
    ("phase0_declaration_wins_over_tenants_column", test_phase0_declaration_wins_over_tenants_column),
    ("agreeing_sources_record_no_disagreement", test_agreeing_sources_record_no_disagreement),
    ("verticals_first_entry_is_the_phase0_declaration", test_verticals_first_entry_is_the_phase0_declaration_when_industry_absent),
    ("tenants_column_used_when_phase0_is_silent", test_tenants_column_used_when_phase0_is_silent),
    ("resolver_is_fallback_only_and_records_confidence", test_resolver_is_fallback_only_and_records_confidence),
    ("resolver_not_consulted_when_anything_is_declared", test_resolver_not_consulted_when_anything_is_declared),
    ("no_source_refuses", test_no_source_refuses),
    ("url_with_no_signal_refuses_rather_than_guessing", test_url_with_no_signal_refuses_rather_than_guessing),
    ("unmeasurable_context_is_not_an_undeclared_one", test_unmeasurable_context_is_not_an_undeclared_one),
    ("none_context_is_unmeasured_not_undeclared", test_none_context_is_unmeasured_not_undeclared),
    ("real_cape_crypto_context", test_real_cape_crypto_context_resolves_to_its_declared_vertical),
    ("real_cape_crypto_declaration_survives_scoreable_url", test_real_cape_crypto_declaration_survives_a_scoreable_url),
    ("real_xago_context", test_real_xago_context_resolves_to_its_declared_vertical),
]


def main():
    print("industry precedence — phase0 > tenants > resolver\n")
    for name, fn in TESTS:
        check(name, fn)
    print(f"\n{len(TESTS) - len(FAILURES)}/{len(TESTS)} passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
