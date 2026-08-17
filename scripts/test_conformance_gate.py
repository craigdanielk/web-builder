"""Tests for the pre-deploy conformance gate (Task C3).

The gate serves an already-built Next.js site on a free local port and runs the
existing `aurelix-uiux-audit/lib/design_conformance.py` analyser against it. It
is the first thing in the chain that can say "the compiled design did not reach
the rendered page" before anything is published.

THE TEST THAT MATTERS MOST is `test_the_gate_fails_the_pre_gate_build`: a gate
that passes the build that existed before it was written has measured nothing.

Two classes of test here, deliberately:

  * end-to-end (~5s each) — really serves a real build with `next start` on a
    dynamically chosen free port and really drives Chromium over every static
    route. These are the only tests that prove the gate measures anything.
  * decision-layer (fast) — feed the gate a rule-results file via
    `--results-json` and assert the PASS / FAIL / NOT_MEASURED mapping. A gate
    that can only say no is as broken as one that can only say yes, and an
    end-to-end "conforming build" fixture does not exist to prove otherwise.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
WEB_BUILDER = SCRIPTS.parent
REPO = WEB_BUILDER.parent
GATE = SCRIPTS / "quality" / "conformance-gate.js"

BASELINE_BUILD = WEB_BUILDER / "output" / "_prev-cape-crypto-20260813" / "site"
CURRENT_BUILD = WEB_BUILDER / "output" / "cape-crypto" / "site"
BENCHMARK = WEB_BUILDER / "benchmarks" / "enterprise-payments-bvnk.json"

# Exit-code contract. NOT_MEASURED != PASS.
EXIT_PASS, EXIT_FAIL, EXIT_NOT_MEASURED = 0, 1, 3


def run_gate(*args: str, timeout: int = 600) -> tuple[int, dict, str]:
    """Invoke the gate. Returns (exit_code, parsed conformance.json or {}, stderr)."""
    out_dir = None
    argv = list(args)
    for i, a in enumerate(argv):
        if a == "--output":
            out_dir = Path(argv[i + 1])
    proc = subprocess.run(
        ["node", str(GATE), *argv],
        cwd=str(WEB_BUILDER), capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "NODE_ENV": "production"},
    )
    report: dict = {}
    if out_dir is not None:
        path = out_dir / "conformance.json"
        if path.exists():
            report = json.loads(path.read_text(encoding="utf-8"))
    return proc.returncode, report, proc.stderr


def write_results(path: Path, results: list) -> Path:
    path.write_text(json.dumps({"results": results}), encoding="utf-8")
    return path


def rule(rule_id: str, state: str, observed=None, expected=None) -> dict:
    """A rule-result in the shape `conformance_runner.py` emits."""
    return {
        "rule_id": rule_id,
        "layer": "L4_visual_systems",
        "state": state,
        "severity": "high",
        "issue": f"{rule_id} is {state}",
        "prevalence": 0.5,
        "affected_pages": ["http://127.0.0.1:1/"],
        "evidence": [{"observed": observed, "expected": expected,
                      "page_url": "http://127.0.0.1:1/", "selector": None}],
    }


# ── The test that matters most ────────────────────────────────────────────

def test_the_gate_fails_the_pre_gate_build(tmp_path):
    """If it passes the build that existed before this gate, the gate is broken."""
    assert BASELINE_BUILD.is_dir(), f"baseline build missing: {BASELINE_BUILD}"
    code, report, err = run_gate(
        "--build-dir", str(BASELINE_BUILD),
        "--benchmark", str(BENCHMARK),
        "--output", str(tmp_path),
    )
    assert report, f"gate wrote no conformance.json (stderr: {err[-2000:]})"
    assert report["status"] == "fail", report.get("reason", report["status"])
    assert code == EXIT_FAIL
    assert len(report["violations"]) >= 3, report["violations"]
    for v in report["violations"]:
        assert v["measured"] is not None, f"a violation with no measurement: {v}"
        assert v["expected"] is not None, f"is an opinion, not a finding: {v}"
        assert set(v) >= {"layer", "rule", "measured", "expected", "route", "section"}


def test_the_current_build_is_measured_and_every_violation_carries_numbers(tmp_path):
    """Whatever today's build scores, the report must be measured, not asserted."""
    assert CURRENT_BUILD.is_dir(), f"current build missing: {CURRENT_BUILD}"
    code, report, err = run_gate(
        "--build-dir", str(CURRENT_BUILD),
        "--benchmark", str(BENCHMARK),
        "--output", str(tmp_path),
    )
    assert report, f"gate wrote no conformance.json (stderr: {err[-2000:]})"
    assert code in (EXIT_PASS, EXIT_FAIL), (
        f"the current build must be measurable, got {code}: {report.get('reason')}")
    assert report["routes_measured"], "no routes were measured"
    assert report["counts"]["pass"] + report["counts"]["fail"] > 0
    for v in report["violations"]:
        assert v["measured"] is not None, v
        assert v["expected"] is not None, v


# ── NOT_MEASURED is never PASS ────────────────────────────────────────────

def test_an_unservable_build_reports_not_measured_never_pass(tmp_path):
    empty = tmp_path / "not-a-build"
    empty.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    code, report, _ = run_gate(
        "--build-dir", str(empty),
        "--benchmark", str(BENCHMARK),
        "--output", str(out),
        timeout=180,
    )
    assert code == EXIT_NOT_MEASURED, code
    assert report["status"] == "not_measured"
    assert report["reason"]
    assert report["violations"] == []


def test_a_missing_benchmark_is_not_measured_not_a_failure(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    code, report, _ = run_gate(
        "--build-dir", str(CURRENT_BUILD),
        "--benchmark", str(tmp_path / "nope.json"),
        "--output", str(out),
        timeout=180,
    )
    assert code == EXIT_NOT_MEASURED, code
    assert report["status"] == "not_measured"


# ── Decision layer: the gate can say yes, no, and "I could not tell" ──────

def test_a_conforming_measurement_passes(tmp_path):
    res = write_results(tmp_path / "r.json",
                        [rule("dna_heading_weight", "PASS", {"400": 12}, ["400"]),
                         rule("dna_type_scale", "PASS", {"32": 4}, [32])])
    out = tmp_path / "out"
    out.mkdir()
    code, report, _ = run_gate("--results-json", str(res), "--output", str(out))
    assert code == EXIT_PASS, report
    assert report["status"] == "pass"
    assert report["violations"] == []


def test_any_failing_rule_fails_the_gate(tmp_path):
    res = write_results(tmp_path / "r.json",
                        [rule("dna_heading_weight", "PASS", {"400": 12}, ["400"]),
                         rule("dna_card_radius", "FAIL", {"48": 3}, "<= 32px")])
    out = tmp_path / "out"
    out.mkdir()
    code, report, _ = run_gate("--results-json", str(res), "--output", str(out))
    assert code == EXIT_FAIL
    assert report["status"] == "fail"
    assert [v["rule"] for v in report["violations"]] == ["dna_card_radius"]
    assert report["violations"][0]["measured"] == {"48": 3}
    assert report["violations"][0]["expected"] == "<= 32px"


def test_unmeasured_rules_with_no_failure_report_not_measured(tmp_path):
    res = write_results(tmp_path / "r.json",
                        [rule("dna_heading_weight", "PASS", {"400": 12}, ["400"]),
                         rule("dna_palette_size", "NOT_MEASURED")])
    out = tmp_path / "out"
    out.mkdir()
    code, report, _ = run_gate("--results-json", str(res), "--output", str(out))
    assert code == EXIT_NOT_MEASURED, report
    assert report["status"] == "not_measured"
    assert [n["rule"] for n in report["not_measured"]] == ["dna_palette_size"]


def test_a_failure_with_no_measurement_is_not_reported_as_a_violation(tmp_path):
    """A violation with no measured value is an opinion. It cannot fail a build."""
    res = write_results(tmp_path / "r.json",
                        [rule("dna_heading_weight", "PASS", {"400": 12}, ["400"]),
                         rule("dna_font_families", "FAIL", None, None)])
    out = tmp_path / "out"
    out.mkdir()
    code, report, _ = run_gate("--results-json", str(res), "--output", str(out))
    assert report["violations"] == [], report["violations"]
    assert [n["rule"] for n in report["not_measured"]] == ["dna_font_families"]
    assert code == EXIT_NOT_MEASURED
    assert report["status"] == "not_measured"


def test_the_gate_exists_and_is_executable_by_node():
    assert GATE.exists(), f"{GATE} does not exist"
    proc = subprocess.run(["node", str(GATE), "--help"],
                          capture_output=True, text=True, timeout=60)
    assert "conformance" in (proc.stdout + proc.stderr).lower()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
