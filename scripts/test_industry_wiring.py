"""Industry resolution has one source, and the build states which won.

A3 (66fe4507) built `lib.industry.resolve_industry` with declared precedence —
phase0.industry (then verticals[0]) > tenants.industry > the audit resolver —
and refused rather than guessing. Nothing was repointed at it. Meanwhile
orchestrate.py carried, verbatim:

    if getattr(args, "compiled_dir", None) and not args.industry:
        args.industry = "electronics-tech"

a hardcoded guess with no declaration involved, which then fed the preset
lookup, the section-sequence lookup, the benchmark filename and the build
record.

These tests cover the build-side wiring: one resolver, the CLI flag as an
explicit override that is recorded as such, and a declared handle that is NOT
in the registry never silently becoming a registry lookup.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


@pytest.fixture(scope="module")
def orch():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("orch_ind", SCRIPTS / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch_ind"] = mod
    spec.loader.exec_module(mod)
    return mod


class Args:
    def __init__(self, industry=None, compiled_dir=None):
        self.industry = industry
        self.compiled_dir = compiled_dir


def ctx(**phase0):
    return {
        "tenant_id": "ad98688a-c384-4785-8d96-12544a13cfa7",
        "slug": "cape-crypto",
        "available": True,
        "load_status": "ok",
        "phase0_field_values": dict(phase0),
    }


def test_the_cli_flag_is_an_override_and_is_recorded_as_one(orch):
    r = orch.resolve_build_industry(Args(industry="ecommerce"), ctx(industry="fintech"))
    assert r["handle"] == "ecommerce"
    assert r["source"] == "cli"


def test_a_declaration_wins_when_no_flag_is_passed(orch):
    r = orch.resolve_build_industry(Args(), ctx(industry="saas"))
    assert r["handle"] == "saas"
    assert r["source"] == "phase0"


def test_verticals_are_read_when_industry_is_absent(orch):
    r = orch.resolve_build_industry(Args(), ctx(verticals=["Crypto exchange (retail)"]))
    assert r["handle"] == "Crypto exchange (retail)"
    assert r["source"] == "phase0"
    assert r["field"] == "verticals[0]"


def test_nothing_declared_is_undeclared_not_a_guess(orch):
    r = orch.resolve_build_industry(Args(), ctx())
    assert r["source"] == "undeclared", r
    assert r["handle"] is None
    assert r["registry_handle"] is None


def test_an_unmeasurable_context_is_not_measured_not_undeclared(orch):
    """An outage must not be recorded as an operator's failure to fill a form."""
    r = orch.resolve_build_industry(Args(), {"available": False, "load_status": "unreachable"})
    assert r["source"] == "not_measured", r
    assert r["handle"] is None


def test_a_declared_handle_absent_from_the_registry_is_not_a_registry_handle(orch):
    """cape-crypto declares 'Crypto exchange (retail)'; industry_styles has 29
    handles and that is not one of them. Picking `fintech` on the tenant's
    behalf is invention; issuing the lookup anyway is a silent empty preset."""
    r = orch.resolve_build_industry(Args(), ctx(verticals=["Crypto exchange (retail)"]))
    assert r["handle_in_registry"] is not True
    assert r["registry_handle"] is None


def test_the_hardcoded_electronics_tech_guess_is_gone():
    src = (SCRIPTS / "orchestrate.py").read_text(encoding="utf-8")
    assert 'args.industry = "electronics-tech"' not in src, (
        "orchestrate.py still assigns a hardcoded industry with no declaration"
    )


def test_main_resolves_the_industry_once(orch):
    tree = ast.parse((SCRIPTS / "orchestrate.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    body = ast.unparse(fn)
    assert body.count("resolve_build_industry(") == 1, (
        "the industry must be resolved once per build, found "
        f"{body.count('resolve_build_industry(')} call(s)"
    )


def test_the_resolution_reaches_the_site_spec(orch, tmp_path):
    spec = {"style": {}}
    r = orch.resolve_build_industry(Args(), ctx(industry="saas"))
    orch.record_industry_resolution(spec, r)
    assert spec["industry_resolution"]["handle"] == "saas"
    assert spec["industry_resolution"]["source"] == "phase0"


def test_the_site_spec_records_undeclared_rather_than_omitting_it(orch):
    spec = {}
    orch.record_industry_resolution(spec, orch.resolve_build_industry(Args(), ctx()))
    assert spec["industry_resolution"]["source"] == "undeclared"


def test_a_disagreement_is_recorded_never_reconciled(orch):
    """phase0 wins, and the fact that `tenants` said something else survives."""
    context = ctx(industry="saas")
    context["tenant"] = {"industry": "fintech"}
    r = orch.resolve_build_industry(Args(), context)
    assert r["handle"] == "saas"
    assert r["disagreement"] and "fintech" in r["disagreement"]
