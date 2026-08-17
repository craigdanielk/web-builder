"""The compliance gate runs on every build, and a FAIL fails the build.

D4 (113d2166) built `lib.compliance_gate.compliance_gate`, tested it with 21
tests, and proved it FAILs on a mutated cape-crypto build. Nothing called it.
A fully implemented, fully tested scanner that no build invokes is not a
control — it is a scanner.

These tests exercise orchestrate.py's wiring, not the scanner: that a call site
exists in BOTH deploy branches, that FAIL reaches the build-failure ledger, and
that NOT_MEASURED is recorded as itself and can never be read as a pass.
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
    spec = importlib.util.spec_from_file_location("orch_cw", SCRIPTS / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch_cw"] = mod
    spec.loader.exec_module(mod)
    return mod


#: cape-crypto's real declaration, inlined from the X1 census exactly as D4's
#: own tests do, so a network flake can never turn a compliance test green.
CAPE_CRYPTO_CTX = {
    "tenant_id": "ad98688a-c384-4785-8d96-12544a13cfa7",
    "slug": "cape-crypto",
    "available": True,
    "load_status": "ok",
    "phase0_field_values": {
        "required_disclaimers": [
            "Cape Crypto (Pty) Ltd is an authorised financial services provider (FSP No. 53746).",
        ],
        "prohibited_terms": ["guaranteed returns", "risk-free"],
    },
}

DISCLAIMER = CAPE_CRYPTO_CTX["phase0_field_values"]["required_disclaimers"][0]


def _site(tmp_path: Path, footer_body: str) -> Path:
    site = tmp_path / "site"
    (site / "src" / "components" / "layout").mkdir(parents=True)
    (site / "src" / "components" / "layout" / "Footer.tsx").write_text(
        'export default function Footer() {\n  return (<footer>%s</footer>);\n}\n' % footer_body,
        encoding="utf-8",
    )
    return site


@pytest.fixture(autouse=True)
def clean_ledger(orch):
    orch.reset_build_failures()
    yield
    orch.reset_build_failures()


def test_a_compliant_site_passes(orch, tmp_path):
    site = _site(tmp_path, DISCLAIMER)
    result = orch.run_compliance_gate(site, "cape-crypto", CAPE_CRYPTO_CTX)
    assert result["status"] == "pass", result
    assert not orch.BUILD_FAILURES


def test_a_prohibited_term_fails_the_build(orch, tmp_path):
    site = _site(tmp_path, DISCLAIMER + " Guaranteed returns on every trade.")
    result = orch.run_compliance_gate(site, "cape-crypto", CAPE_CRYPTO_CTX)
    assert result["status"] == "fail", result
    assert orch.BUILD_FAILURES, "a compliance FAIL did not reach the failure ledger"
    assert orch.BUILD_FAILURES[0]["stage"] == "compliance"


def test_a_missing_disclaimer_fails_the_build(orch, tmp_path):
    site = _site(tmp_path, "Cape Crypto (Pty) Ltd.")
    result = orch.run_compliance_gate(site, "cape-crypto", CAPE_CRYPTO_CTX)
    assert result["status"] == "fail", result
    assert orch.BUILD_FAILURES


def test_no_declaration_is_not_measured_never_pass(orch, tmp_path):
    site = _site(tmp_path, "Anything at all.")
    result = orch.run_compliance_gate(site, None, None)
    assert result["status"] == "not_measured", result
    assert result["status"] != "pass"


def test_not_measured_is_recorded_as_itself(orch, tmp_path):
    site = _site(tmp_path, "Anything at all.")
    orch.run_compliance_gate(site, None, None)
    assert orch.GATE_RESULTS.get("compliance") == "not_measured", orch.GATE_RESULTS


def test_not_measured_is_not_a_build_failure(orch, tmp_path):
    """'We never checked' is a different fact from 'we checked and it is bad'."""
    site = _site(tmp_path, "Anything at all.")
    orch.run_compliance_gate(site, None, None)
    assert not orch.BUILD_FAILURES


def test_an_unmeasured_gate_stops_the_build_reporting_success(orch):
    """A build whose compliance was never measured must not exit 0."""
    status, code = orch.resolve_build_outcome(
        "passed", True, audit_ran=True, unmeasured_gates=["compliance"]
    )
    assert code == orch.EXIT_NOT_MEASURED, (status, code)
    assert code != orch.EXIT_OK


def test_no_unmeasured_gates_leaves_the_outcome_unchanged(orch):
    assert orch.resolve_build_outcome("passed", True, audit_ran=True) == (
        "completed",
        orch.EXIT_OK,
    )


def _main_source() -> str:
    tree = ast.parse((SCRIPTS / "orchestrate.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    return ast.unparse(fn)


def test_both_deploy_branches_call_the_gate():
    """Multi-page and single-page. One wired branch is a gate half the builds skip."""
    body = _main_source()
    assert body.count("run_compliance_gate(") == 2, (
        "expected the compliance gate on both deploy branches, found "
        f"{body.count('run_compliance_gate(')}"
    )
