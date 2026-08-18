#!/usr/bin/env python3
"""A MARKET may default a tech choice. A TENANT always outranks it.

WHY THIS EXISTS
---------------
Census 2026-08-18 §3.3e measured the gap: **0 of 924 phase-0 rows declare `cms`
or `email`**, `_MODULE_CATALOGUE` is keyed by the declared value, and there was
no layer above the tenant — so nothing in the system could express *"sites in
this market ship a block store"*. The resolver, the closed vocabulary and the
three-state refusal already worked (`5ec3f919`), so the fix is a lookup UNDER
`_module_entry`, not a second mechanism.

The precedence is the whole of the contract, and it is the thing that can
silently go wrong:

  tenant declaration  >  market default  >  absent

Each arrow is a separate test here, and the middle one has a trap on either
side of it:

  * a market must NOT answer for a tenant whose context never loaded.
    NOT_MEASURED is not silence. Filling it from a market turns "we could not
    read this tenant" into a confident stack decision — the substitution this
    repo keeps removing.
  * a market must NOT answer for a tenant that declared something invalid. That
    tenant HAS answered; replacing a wrong declaration with a plausible one
    loses the operator's error.

`_MARKET_MODULE_DEFAULTS` ships EMPTY and a test holds it empty, so no live
tenant's resolution moves. Populating it is a design-authority act by an
operator; nothing measured today supports an entry (the one CMS in the library
came from one tenant repo, which is a fact about that tenant, not its market).

Run: cd web-builder && python3 -m pytest scripts/test_market_module_defaults.py -v
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

#: The eight keys `platform_modules()` returns for a tenant that declares
#: neither module. A ninth is a regression for cape-crypto.
BASE_KEYS = {
    "target_platform", "source_platform", "adapter", "inject_commerce",
    "write_env", "generate_l7_pages", "image_hosts", "npm_packages",
}

MARKET = "enterprise-stablecoin-payments"


def _load_orchestrate():
    spec = importlib.util.spec_from_file_location("orch_mm", ROOT / "scripts" / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch_mm"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def orch():
    return _load_orchestrate()


@pytest.fixture
def with_market_default(orch, monkeypatch):
    """Install a fixture market table. The shipped one is empty on purpose."""
    def install(table):
        monkeypatch.setattr(orch, "_MARKET_MODULE_DEFAULTS", table)
    return install


def ctx(**fields):
    """A context that READ CLEANLY and declares exactly `fields`."""
    return {"load_status": "ok", "slug": "fixture-tenant",
            "phase0_field_values": dict(fields)}


def unreadable():
    """A context whose load FAILED — nothing is known about any field."""
    return {"load_status": "unreachable", "slug": "fixture-tenant",
            "phase0_field_values": {}, "load_errors": ["fixture: transport error"]}


def cape_crypto_shaped():
    """cape-crypto's declared platform fields, and nothing else.

    It declares `target_platform` and `source_platform` and neither module —
    measured, census §3.1. This is the regression subject.
    """
    return ctx(target_platform="vercel", source_platform="ghost")


# ── the shipped table ─────────────────────────────────────────────────────────

def test_the_shipped_market_table_is_empty(orch):
    """Sourced or empty, never invented — the library obeys it too.

    A market default is a claim about a market. Nothing measured supports one
    today, so the mechanism ships inert and an operator populates it. This test
    failing means someone asserted a market's tech stack: that is a real
    decision and it should be argued in a commit, not slipped in under a test
    that never looked.
    """
    assert orch._MARKET_MODULE_DEFAULTS == {}


# ── precedence: tenant > market ───────────────────────────────────────────────

def test_a_tenant_declaration_beats_the_market_default(orch, with_market_default):
    with_market_default({MARKET: {"cms": "block-store", "email": "resend"}})
    got = orch.platform_modules("vercel", "ghost",
                                ctx(cms="none", email="none"), market=MARKET)
    assert got["cms"]["declared"] == "none"
    assert got["email"]["declared"] == "none"
    assert got["cms"]["source"] == "tenant"
    assert got["email"]["source"] == "tenant"
    assert got["cms"]["market"] is None
    # And the market's packages did NOT come along for the ride.
    assert got["npm_packages"] == {}


def test_a_tenant_declaring_the_other_value_still_beats_the_market(orch, with_market_default):
    """`none` beating `block-store` is the case that matters — an operator who
    said "no CMS" must not get one because the market ships one."""
    with_market_default({MARKET: {"cms": "block-store"}})
    got = orch.platform_modules("vercel", "ghost", ctx(cms="none"), market=MARKET)
    assert got["cms"] == {"declared": "none", "source": "tenant", "market": None,
                          "npm_packages": {}, "env_names": []}
    assert "@measured/puck" not in got["npm_packages"]


# ── precedence: market > absent ───────────────────────────────────────────────

def test_the_market_default_applies_where_the_tenant_is_silent(orch, with_market_default):
    with_market_default({MARKET: {"cms": "block-store", "email": "resend"}})
    got = orch.platform_modules("vercel", "ghost", ctx(), market=MARKET)
    assert got["cms"]["declared"] == "block-store"
    assert got["cms"]["source"] == "market"
    assert got["cms"]["market"] == MARKET
    assert got["email"]["declared"] == "resend"
    # A resolved module folds its pins in, whichever layer answered it.
    assert got["npm_packages"]["@measured/puck"] == "^0.20.2"
    assert got["cms"]["env_names"], "a resolved cms declares env names"


def test_a_market_default_for_one_field_leaves_the_other_absent(orch, with_market_default):
    with_market_default({MARKET: {"cms": "block-store"}})
    got = orch.platform_modules("vercel", "ghost", ctx(), market=MARKET)
    assert got["cms"]["source"] == "market"
    assert "email" not in got, "a field no layer answered stays ABSENT"


def test_a_market_with_no_entry_leaves_both_absent(orch, with_market_default):
    with_market_default({"some-other-market": {"cms": "block-store"}})
    got = orch.platform_modules("vercel", "ghost", ctx(), market=MARKET)
    assert "cms" not in got and "email" not in got


def test_undeclared_everywhere_stays_absent(orch):
    """No tenant declaration, no market at all — no key. Not "none"."""
    got = orch.platform_modules("vercel", "ghost", ctx(), market=None)
    assert "cms" not in got and "email" not in got


# ── the two traps around the middle arrow ─────────────────────────────────────

def test_a_market_default_does_NOT_answer_for_an_unreadable_context(orch, with_market_default):
    """NOT_MEASURED is not silence, and a market must not convert one to the other."""
    with_market_default({MARKET: {"cms": "block-store", "email": "resend"}})
    got = orch.platform_modules("vercel", "ghost", unreadable(), market=MARKET)
    assert "cms" not in got, (
        "an unreachable tenant record resolved a CMS from the market — that is "
        "NOT_MEASURED reported as a decision"
    )
    assert "email" not in got


def test_an_out_of_vocabulary_tenant_declaration_is_not_replaced_by_the_market(
        orch, with_market_default):
    """The tenant answered, wrongly. The refusal stands; the error is not hidden."""
    with_market_default({MARKET: {"cms": "block-store"}})
    got = orch.platform_modules("vercel", "ghost", ctx(cms="wordpress"), market=MARKET)
    assert "cms" not in got


# ── the market table is on the closed vocabulary ──────────────────────────────

def test_a_market_default_outside_the_vocabulary_raises(orch, with_market_default):
    with_market_default({MARKET: {"cms": "wordpress"}})
    with pytest.raises(ValueError) as exc:
        orch.platform_modules("vercel", "ghost", ctx(), market=MARKET)
    assert "vocabulary" in str(exc.value)


def test_no_market_key_resolves_nothing(orch, with_market_default):
    with_market_default({MARKET: {"cms": "block-store"}})
    assert orch.market_module_default(None, "cms") is None
    assert orch.market_module_default("", "cms") is None


# ── the build record names the answering layer ────────────────────────────────

def test_the_record_names_the_layer_for_each_field(orch, with_market_default):
    with_market_default({MARKET: {"cms": "block-store"}})
    modules = orch.platform_modules("vercel", "ghost", ctx(email="resend"),
                                    market=MARKET)
    record = orch.module_resolution_record(modules, MARKET)
    assert record["market"] == MARKET
    assert record["fields"]["cms"] == {
        "declared": "block-store", "source": "market", "market": MARKET}
    assert record["fields"]["email"]["source"] == "tenant"
    assert record["fields"]["email"]["market"] is None


def test_the_record_writes_absent_as_absent_never_as_none(orch):
    modules = orch.platform_modules("vercel", "ghost", ctx(), market=None)
    record = orch.module_resolution_record(modules, None)
    for field in ("cms", "email"):
        assert record["fields"][field]["source"] == "absent"
        assert record["fields"][field]["declared"] is None, (
            "'absent' must not be recorded as a declared value — nobody asked "
            "is not the same answer as asked and answered 'none'"
        )


def test_the_printed_line_says_which_layer_answered(orch, with_market_default):
    with_market_default({MARKET: {"cms": "block-store"}})
    modules = orch.platform_modules("vercel", "ghost", ctx(email="none"),
                                    market=MARKET)
    lines = []
    orch.report_module_resolution(modules, MARKET, write=lines.append)
    text = "\n".join(lines)
    assert "MARKET default" in text and MARKET in text
    assert "TENANT" in text


# ── cape-crypto regression ────────────────────────────────────────────────────

def test_cape_crypto_resolution_is_unchanged_by_this_layer(orch):
    """It declares neither module and its market has no default in this change.

    Both halves are asserted: the resolution with the market is byte-identical
    to the resolution without one, and it carries exactly the eight keys it
    carried before cms/email existed. A market default silently reaching a
    tenant that never asked for one fails here.
    """
    without = orch.platform_modules("vercel", "ghost", cape_crypto_shaped(),
                                    market=None)
    with_market = orch.platform_modules("vercel", "ghost", cape_crypto_shaped(),
                                        market=MARKET)
    assert set(without) == BASE_KEYS
    assert set(with_market) == BASE_KEYS
    # `adapter` is an instance; compare everything else exactly.
    strip = lambda d: {k: v for k, v in d.items() if k != "adapter"}  # noqa: E731
    assert strip(without) == strip(with_market)
    assert without["npm_packages"] == {}


def test_cape_cryptos_market_carries_no_default_in_the_shipped_table(orch):
    assert orch.market_module_default(MARKET, "cms") is None
    assert orch.market_module_default(MARKET, "email") is None
