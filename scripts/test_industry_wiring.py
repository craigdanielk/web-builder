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

P1 (2026-08-17) added the middle outcome. Measured first: `phase0.industry` is
absent for BOTH live tenants and `verticals` is declared for both, so the
"declared handle is not a registry handle" branch was not an edge case — it was
every real build, and `registry_handle` was therefore always None. The node now
has exactly three outcomes:

    declared   phase0.industry / tenants.industry / --industry, used verbatim
    derived    verticals[0] mapped through the versioned data table at
               skills/verticals-to-industry.json, recorded as
               source="derived-from-verticals" with derived_from + version
    refused    neither, or a vertical with no row — exit 3 (NOT_MEASURED)

Two assertions below changed with that contract and say so at the point of
change. The mapping is DATA — an operator-authored, diffable decision — which
is what separates it from the `"electronics-tech"` guess this node replaced;
a vertical the table does not name is still never defaulted.
"""

from __future__ import annotations

import ast
import importlib.util
import json
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
    def __init__(self, industry=None, compiled_dir=None, tenant=None):
        self.industry = industry
        self.compiled_dir = compiled_dir
        self.tenant = tenant


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
    """CHANGED BY P1. Was: handle == "Crypto exchange (retail)", source
    "phase0". A verticals-sourced handle is now derived through the mapping
    table and labelled a derivation, because the raw string is not an
    `industry_styles` handle and returning it verbatim left every real build
    with registry_handle None."""
    r = orch.resolve_build_industry(Args(), ctx(verticals=["Crypto exchange (retail)"]))
    assert r["field"] == "verticals[0]"
    assert r["source"] == "derived-from-verticals", r
    assert r["handle"] == "fintech"
    assert r["derived_from"] == "Crypto exchange (retail)"
    assert r["mapping_key"] == "crypto-exchange-retail"
    assert r["mapping_version"] == 1


def test_a_derivation_is_never_recorded_as_the_tenants_own_declaration(orch):
    """The whole point of the label. An operator reading the build record must
    be able to tell "the tenant said fintech" from "we mapped their vertical"."""
    r = orch.resolve_build_industry(Args(), ctx(verticals=["Crypto exchange (retail)"]))
    assert r["source"] != "phase0"
    spec = {}
    orch.record_industry_resolution(spec, r)
    assert spec["industry_resolution"]["source"] == "derived-from-verticals"
    assert spec["industry_resolution"]["derived_from"] == "Crypto exchange (retail)"
    assert spec["industry_resolution"]["mapping_version"] == 1


def test_a_declared_industry_is_not_derived(orch):
    """The declared branch must not go near the mapping table."""
    r = orch.resolve_build_industry(Args(), ctx(industry="saas", verticals=["Stablecoins"]))
    assert r["handle"] == "saas"
    assert r["source"] == "phase0"
    assert r["field"] == "phase0.industry"
    assert r.get("derived_from") is None


def test_a_vertical_with_no_row_in_the_table_is_refused_not_defaulted(orch):
    r = orch.resolve_build_industry(Args(), ctx(verticals=["Competitive ferret grooming"]))
    assert r["source"] == "unmapped_vertical", r
    assert r["handle"] is None
    assert r["registry_handle"] is None
    assert "no row in" in r["reason"]


def test_the_mapping_table_is_data_and_every_value_is_a_registry_handle(orch):
    """A mapping onto a handle `industry_styles` does not hold would resolve to
    an empty preset that reads as "this tenant has no style"."""
    table = orch.load_verticals_industry_map()
    assert table["error"] is None, table
    assert table["mappings"], "the table is empty"
    raw = json.loads(orch.VERTICALS_MAP_PATH.read_text(encoding="utf-8"))
    handles = set(raw["registry"]["handles"])
    for key, row in table["mappings"].items():
        assert key == orch.slugify_vertical(key), f"{key} is not its own slug"
        assert row["industry"] in handles, f"{key} -> {row['industry']} is not a handle"
        assert row.get("grounding"), f"{key} has no grounding"


def test_an_unreadable_mapping_table_is_not_measured_not_a_default(orch, tmp_path):
    empty = tmp_path / "missing.json"
    table = orch.load_verticals_industry_map(empty)
    assert table["error"], table
    assert table["mappings"] == {}
    assert orch.derive_industry_from_vertical("Crypto exchange (retail)", table) is None


def test_nothing_declared_is_undeclared_not_a_guess(orch):
    r = orch.resolve_build_industry(Args(), ctx())
    assert r["source"] == "undeclared", r
    assert r["handle"] is None
    assert r["registry_handle"] is None


def test_a_refusal_names_both_missing_fields(orch):
    r = orch.resolve_build_industry(Args(), ctx())
    assert set(r["missing_fields"]) == {"phase0.industry", "phase0.verticals"}


def test_the_refusal_exits_3_not_1(orch, capsys):
    """NOT_MEASURED, not FAILED. Exit 1 would bucket an incomplete declaration
    with a compile error, and the chain reads that column."""
    args = Args(tenant="cape-crypto")
    code = orch.refuse_unresolved_industry(args, orch.resolve_build_industry(args, ctx()))
    assert code == orch.EXIT_NOT_MEASURED
    assert code == 3
    assert code != 1
    out = capsys.readouterr().out
    assert "phase0.industry" in out and "phase0.verticals" in out


def test_an_unmapped_vertical_also_refuses_with_3(orch):
    args = Args(tenant="cape-crypto")
    r = orch.resolve_build_industry(args, ctx(verticals=["Competitive ferret grooming"]))
    assert orch.refuse_unresolved_industry(args, r) == 3


def test_an_unmeasurable_context_refuses_rather_than_building_on_an_implied_industry(orch):
    args = Args(tenant="cape-crypto")
    r = orch.resolve_build_industry(args, {"available": False, "load_status": "unreachable"})
    assert r["source"] == "not_measured"
    assert orch.refuse_unresolved_industry(args, r) == 3


def test_a_resolved_industry_does_not_refuse(orch):
    args = Args(tenant="cape-crypto")
    for context in (ctx(industry="saas"), ctx(verticals=["Crypto exchange (retail)"])):
        r = orch.resolve_build_industry(args, context)
        assert orch.refuse_unresolved_industry(args, r) is None, r


def test_a_build_with_no_tenant_is_not_refused(orch):
    """Without --tenant there is no declaration surface to consult; design
    authority is --preset/--benchmark and the recorded not_measured state is
    already honest. Refusing here would break every non-tenant build."""
    args = Args()
    assert orch.refuse_unresolved_industry(args, orch.resolve_build_industry(args, ctx())) is None


def test_main_gates_the_build_on_the_refusal(orch):
    tree = ast.parse((SCRIPTS / "orchestrate.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    body = ast.unparse(fn)
    assert "refuse_unresolved_industry(" in body, (
        "main resolves the industry but never refuses on an unresolved one"
    )


def test_an_unmeasurable_context_is_not_measured_not_undeclared(orch):
    """An outage must not be recorded as an operator's failure to fill a form."""
    r = orch.resolve_build_industry(Args(), {"available": False, "load_status": "unreachable"})
    assert r["source"] == "not_measured", r
    assert r["handle"] is None


def test_a_declared_handle_absent_from_the_registry_is_not_a_registry_handle(orch):
    """CHANGED BY P1. The example moved, the rule did not. A declared handle
    industry_styles does not hold still never becomes a registry lookup — but
    'Crypto exchange (retail)' is no longer that example, because a vertical is
    now mapped through the table rather than returned verbatim. An undeclarable
    free-text industry is."""
    r = orch.resolve_build_industry(Args(), ctx(industry="Crypto exchange (retail)"))
    assert r["source"] == "phase0"
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
