"""The conformance gate runs pre-deploy, and a FAIL fails the build.

C3 (102658e2) built `scripts/quality/conformance-gate.js`: it serves the
already-built site locally, drives Chromium through the ratified benchmark's
rules, and returns 0/1/3. It had no call site — the only thing between a
compiled design and a site that ignored it was a human looking at the page.

These tests exercise orchestrate.py's wiring, driven through the gate's OWN
verdict seam (`--results-json`, which C3 built so the three outcomes can be
reached without serving a site). The verdict logic itself is C3's and is
covered by scripts/test_conformance_gate.py; what is asserted here is that the
build calls it, reads the artifact rather than the exit code, and lets a FAIL
stop the build.
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
    spec = importlib.util.spec_from_file_location("orch_conf", SCRIPTS / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch_conf"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def clean_ledgers(orch):
    orch.reset_build_failures()
    orch.reset_gate_results()
    yield
    orch.reset_build_failures()
    orch.reset_gate_results()


def results_file(tmp_path: Path, results: list[dict]) -> Path:
    p = tmp_path / "runner-results.json"
    p.write_text(json.dumps({"results": results, "urls_reached": ["http://127.0.0.1:1/"]}),
                 encoding="utf-8")
    return p


CONFORMING = [{"rule_id": "dna_card_radius", "layer": "L4", "state": "PASS"}]

VIOLATING = [
    {
        "rule_id": "dna_type_scale",
        "layer": "L4",
        "state": "FAIL",
        "severity": "high",
        "issue": "off-scale type sizes",
        "evidence": [{"observed": {"44": 7, "92": 5}, "expected": [96, 64, 48, 32]}],
    }
]

OPINION = [
    # A FAIL carrying no measurement. C3 records it as NOT_MEASURED — a
    # violation with no measurement is an opinion and can never fail a build.
    {"rule_id": "dna_shadow_layers", "layer": "L4", "state": "FAIL", "evidence": [{}]}
]


def test_a_conforming_build_passes(orch, tmp_path):
    res = orch.run_conformance_gate(
        tmp_path / "site", results_json=results_file(tmp_path, CONFORMING),
        output_dir=tmp_path,
    )
    assert res["status"] == "pass", res
    assert not orch.BUILD_FAILURES


def test_a_measured_violation_fails_the_build(orch, tmp_path):
    res = orch.run_conformance_gate(
        tmp_path / "site", results_json=results_file(tmp_path, VIOLATING),
        output_dir=tmp_path,
    )
    assert res["status"] == "fail", res
    assert orch.BUILD_FAILURES, "a conformance FAIL did not reach the failure ledger"
    assert orch.BUILD_FAILURES[0]["stage"] == "conformance"
    assert "dna_type_scale" in orch.BUILD_FAILURES[0]["detail"]


def test_a_violation_with_no_measurement_is_not_measured_not_a_failure(orch, tmp_path):
    res = orch.run_conformance_gate(
        tmp_path / "site", results_json=results_file(tmp_path, OPINION),
        output_dir=tmp_path,
    )
    assert res["status"] == "not_measured", res
    assert not orch.BUILD_FAILURES


def test_not_measured_is_recorded_as_itself(orch, tmp_path):
    orch.run_conformance_gate(
        tmp_path / "site", results_json=results_file(tmp_path, OPINION),
        output_dir=tmp_path,
    )
    assert orch.GATE_RESULTS.get("conformance") == "not_measured", orch.GATE_RESULTS


def test_no_built_site_is_not_measured_never_pass(orch, tmp_path):
    """The gate does not build. An absent .next is unmeasured, not conforming."""
    site = tmp_path / "site"
    site.mkdir()
    res = orch.run_conformance_gate(site, output_dir=tmp_path)
    assert res["status"] == "not_measured", res
    assert res["status"] != "pass"
    assert "not_measured_reason" in res


def test_the_verdict_is_read_off_the_artifact_not_the_exit_code(orch, tmp_path):
    orch.run_conformance_gate(
        tmp_path / "site", results_json=results_file(tmp_path, VIOLATING),
        output_dir=tmp_path,
    )
    written = json.loads((tmp_path / "conformance.json").read_text(encoding="utf-8"))
    assert written["status"] == "fail"
    assert written["violations"][0]["rule"] == "dna_type_scale"


def _main_source() -> str:
    tree = ast.parse((SCRIPTS / "orchestrate.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    return ast.unparse(fn)


def test_both_deploy_branches_call_the_gate():
    body = _main_source()
    assert body.count("run_conformance_gate(") == 2, (
        "expected the conformance gate on both deploy branches, found "
        f"{body.count('run_conformance_gate(')}"
    )
