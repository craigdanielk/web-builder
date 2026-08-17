#!/usr/bin/env python3
"""findings-to-verdicts — every finding is routed or counted, never dropped.

WHY THIS EXISTS
---------------
`orchestrate.py` has consumed a `--copy-findings` file since the Copy Fidelity
node landed and nothing has ever written one, so 208 non-PASS findings on the
cape-crypto bundle were unactionable. The compiler closes that wire.

Two properties make it trustworthy, and both are asserted here against the REAL
consumer rather than a restatement of it:

  1. **Accounting.** verdict findings + unroutable findings == input findings.
     The measured fact this guards is census §2–§3: on a default audit run 100%
     of findings carry a route and 0 of 322 carry a section identity. A compiler
     that only emitted what it could map would look clean while silently
     discarding the majority — the exact "degrade toward fabrication rather than
     toward stopping" failure the standing rules exist to prevent.
  2. **Shape.** The consumer swallows a load error with a warning and proceeds
     verbatim, so a wrong shape is a SILENT no-op in the build, not a failure.
     So the assertions import `_findings_are_page_scoped`, `resolve_page_entry`
     and `section_identity` from `orchestrate.py` and require that the real
     lookup path resolves a real verdict.

Run: python3 scripts/test_findings_verdicts.py
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPILER = ROOT / "scripts" / "quality" / "findings-to-verdicts.py"

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")
        if detail:
            print(f"      {detail}")


def load_compiler():
    """Import the dashed-name module by path (its siblings are dashed too)."""
    spec = importlib.util.spec_from_file_location("findings_to_verdicts", COMPILER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_orchestrator():
    """The consumer itself — the only authority on the schema it accepts."""
    spec = importlib.util.spec_from_file_location(
        "orch_fv", ROOT / "scripts" / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch_fv"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures — one per routability class named in the census
# ---------------------------------------------------------------------------

def fixture_report():
    """A findings report covering every lane the compiler must distinguish."""
    def ev(page_url, selector=None):
        return [{"source": "html_capture", "page_url": page_url,
                 "selector": selector, "observed": {}, "expected": {},
                 "confidence": 0.9, "reproducibility": "deterministic",
                 "metadata": {}}]

    return {
        "page_count": 2,
        "findings": [
            # 0000 — route-only, copy-actionable, target archetype present with copy
            {"rule_id": "social_proof", "state": "FAIL", "layer": "L8_conversion_architecture",
             "severity": "low", "issue": "No social proof elements detected",
             "affected_pages": ["https://example.com"], "prevalence": 1.0,
             "evidence": ev("https://example.com")},
            # 0001 — PASS: counted, routed nowhere
            {"rule_id": "h1_presence", "state": "PASS", "layer": "L1_strategic_ux",
             "severity": "info", "issue": "H1 present",
             "affected_pages": ["https://example.com"], "prevalence": 1.0,
             "evidence": ev("https://example.com")},
            # 0002 — axe selector naming a section by its uid
            {"rule_id": "axe:heading-order", "state": "FAIL", "layer": "L5_accessibility",
             "severity": "medium", "issue": "Heading levels skip a level",
             "affected_pages": ["https://example.com"], "prevalence": 0.5,
             "evidence": ev("https://example.com",
                            '[data-section-uid="aaa111"] > h3')},
            # 0003 — axe selector naming a section by its archetype class
            {"rule_id": "axe:link-name", "state": "FAIL", "layer": "L5_accessibility",
             "severity": "high", "issue": "Link has no discernible name",
             "affected_pages": ["https://example.com/about"], "prevalence": 0.5,
             "evidence": ev("https://example.com/about", ".cta > a:nth-child(2)")},
            # 0004 — axe selector matching nothing on the built page
            {"rule_id": "axe:heading-order", "state": "FAIL", "layer": "L5_accessibility",
             "severity": "medium", "issue": "Heading levels skip a level",
             "affected_pages": ["https://example.com/about"], "prevalence": 0.5,
             "evidence": ev("https://example.com/about",
                            ".lp-step:nth-child(2) > .lp-step__text")},
            # 0005 — dna_*: site-scoped, page_url is pages[0] not a route
            {"rule_id": "dna_heading_weight", "state": "FAIL", "layer": "L4_visual_systems",
             "severity": "high", "issue": "12 of 24 headings use a weight outside the set",
             "affected_pages": ["https://example.com", "https://example.com/about"],
             "prevalence": 0.5, "evidence": ev("https://example.com")},
            # 0006 — not copy-actionable (a Lighthouse passthrough)
            {"rule_id": "lh:unminified-css", "state": "FAIL", "layer": "L6_frontend_engineering",
             "severity": "medium", "issue": "Minify CSS",
             "affected_pages": ["https://example.com"], "prevalence": 1.0,
             "evidence": ev("https://example.com")},
            # 0007 — route not built
            {"rule_id": "social_proof", "state": "FAIL", "layer": "L8_conversion_architecture",
             "severity": "low", "issue": "No social proof elements detected",
             "affected_pages": ["https://example.com/blog"], "prevalence": 1.0,
             "evidence": ev("https://example.com/blog")},
            # 0008 — no route at all
            {"rule_id": "cta_presence", "state": "FAIL", "layer": "L8_conversion_architecture",
             "severity": "medium", "issue": "No CTA found",
             "affected_pages": [], "prevalence": 1.0, "evidence": []},
            # 0009 — copy-actionable, but the page has no section of that archetype
            # (loading_state_feedback targets SIGNUP-FORM / CONTACT-FORM; the
            # fixture homepage is HERO / TRUST-BADGES / FOOTER)
            {"rule_id": "loading_state_feedback", "state": "FAIL",
             "layer": "L3_interaction_architecture",
             "severity": "low", "issue": "No loading state feedback on submit",
             "affected_pages": ["https://example.com"], "prevalence": 1.0,
             "evidence": ev("https://example.com")},
            # 0010 — copy-selector rule that carried no selector
            {"rule_id": "axe:button-name", "state": "FAIL", "layer": "L5_accessibility",
             "severity": "high", "issue": "Button has no discernible name",
             "affected_pages": ["https://example.com"], "prevalence": 1.0,
             "evidence": ev("https://example.com")},
            # 0011 — target archetype present but holds no harvested copy → inert
            {"rule_id": "h1_uniqueness", "state": "FAIL", "layer": "L1_strategic_ux",
             "severity": "medium", "issue": "Two H1 elements on the page",
             "affected_pages": ["https://example.com/about"], "prevalence": 1.0,
             "evidence": ev("https://example.com/about")},
        ],
    }


def fixture_spec():
    """A two-page site-spec in the shape build-site-spec.js emits."""
    def content(n):
        return {"headings": [f"Heading {i}" for i in range(n)],
                "body_text": ["Some real harvested body copy."] if n else [],
                "ctas": ["Sign up"] if n else []}

    return {
        "version": 1,
        "project": "fixture",
        "pages": [
            {"id": "homepage", "route": "/", "page_type": "homepage", "sections": [
                {"index": 0, "archetype": "HERO", "variant": "gradient-split",
                 "section_uid": "aaa111", "content": content(2)},
                {"index": 1, "archetype": "TRUST-BADGES", "variant": "icon-strip",
                 "section_uid": "bbb222", "content": content(1)},
                {"index": 2, "archetype": "FOOTER", "variant": "columns",
                 "section_uid": "ccc333", "content": content(4)},
            ]},
            {"id": "about", "route": "/about", "page_type": "about", "sections": [
                {"index": 0, "archetype": "HERO", "variant": "centered",
                 "section_uid": "ddd444", "content": content(0)},
                {"index": 1, "archetype": "CTA", "variant": "centered",
                 "section_uid": "eee555", "content": content(1)},
            ]},
        ],
    }


def write_fixtures(tmp):
    import yaml
    report = tmp / "audit_result.yaml"
    report.write_text(yaml.safe_dump(fixture_report(), sort_keys=True),
                      encoding="utf-8")
    spec = tmp / "site-spec.json"
    spec.write_text(json.dumps(fixture_spec(), indent=2, sort_keys=True),
                    encoding="utf-8")
    return report, spec


def run_cli(report, spec, out_dir):
    return subprocess.run(
        [sys.executable, str(COMPILER), str(report),
         "--site-spec", str(spec), "--out-dir", str(out_dir)],
        capture_output=True, text=True, cwd=str(ROOT))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_accounting_and_lanes():
    print("\nAccounting — mapped + unroutable == input")
    mod = load_compiler()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report, spec = write_fixtures(tmp)
        section_map = mod.load_section_map(spec)
        result = mod.compile_verdicts(fixture_report(), section_map)

    summary = result["unroutable"]["summary"]
    placed = sorted({k for page in result["copy_findings"].values()
                     for slot in page.values()
                     for k in slot["contributing_findings"]})
    n_in = len(fixture_report()["findings"])

    test("input count is read from findings[]", summary["input_findings"] == n_in,
         f"{summary['input_findings']} != {n_in}")
    test("verdicts + unroutable == input findings",
         summary["verdict_findings"] + summary["unroutable_findings"] == n_in,
         f"{summary['verdict_findings']} + {summary['unroutable_findings']} != {n_in}")
    test("verdict count equals distinct findings actually placed",
         summary["verdict_findings"] == len(placed),
         f"summary says {summary['verdict_findings']}, walked {len(placed)}")
    test("no finding appears in both outputs",
         not (set(placed) & {r["finding_key"] for r
                             in result["unroutable"]["findings"]}))

    reasons = {r["finding_key"]: r["reason"] for r
               in result["unroutable"]["findings"]}
    expected = {
        "0001:h1_presence": "state-not-actionable",
        "0004:axe:heading-order": "selector-no-section-match",
        "0005:dna_heading_weight": "dna-site-scoped",
        "0006:lh:unminified-css": "rule-not-copy-actionable",
        "0007:social_proof": "route-not-built",
        "0008:cta_presence": "no-route",
        "0009:loading_state_feedback": "target-archetype-absent",
        "0010:axe:button-name": "no-section-identity",
        "0011:h1_uniqueness": "target-sections-no-copy",
    }
    for key, reason in expected.items():
        test(f"{key} → {reason}", reasons.get(key) == reason,
             f"got {reasons.get(key)!r}")

    cf = result["copy_findings"]
    test("route-only copy rule lands on its target archetype",
         "bbb222" in cf.get("homepage", {}),
         f"homepage slots: {sorted(cf.get('homepage', {}))}")
    test("axe selector with a section uid lands on that section",
         "aaa111" in cf.get("homepage", {})
         and cf["homepage"]["aaa111"]["match"] == "section-uid",
         json.dumps(cf.get("homepage", {}), sort_keys=True))
    test("axe selector with an archetype class token lands on that archetype",
         "eee555" in cf.get("about", {})
         and cf["about"]["eee555"]["match"] == "archetype-class",
         json.dumps(cf.get("about", {}), sort_keys=True))
    test("a section with no harvested copy never receives a verdict",
         "ddd444" not in cf.get("about", {}))
    test("every unroutable reason is from the declared vocabulary",
         all(r["reason"] in mod.REASONS for r in result["unroutable"]["findings"]))


def test_consumed_schema_is_the_consumers_own():
    print("\nShape — asserted with orchestrate.py's own functions")
    mod = load_compiler()
    orch = load_orchestrator()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _, spec = write_fixtures(tmp)
        result = mod.compile_verdicts(fixture_report(), mod.load_section_map(spec))
    cf = result["copy_findings"]

    test("consumer classifies the output as page-scoped",
         orch._findings_are_page_scoped(cf) is True,
         json.dumps(cf, sort_keys=True)[:400])

    spec_pages = fixture_spec()["pages"]
    home = spec_pages[0]
    page_entry = orch.resolve_page_entry(cf, home)
    test("consumer's resolve_page_entry finds the homepage verdicts",
         isinstance(page_entry, dict) and page_entry,
         f"got {page_entry!r}")

    # Walk the consumer's own four-key lookup for a section we flagged.
    section = home["sections"][1]
    found = (page_entry.get(orch.section_identity(section, 1))
             or page_entry.get(str(section.get("index", 1)))
             or page_entry.get(str(1)))
    test("consumer's key resolution reaches the verdict via section_identity",
         isinstance(found, dict) and found.get("rule_id") == "social_proof",
         f"got {found!r}")
    test("the two fields the consumer reads are both present and non-empty",
         bool(str(found.get("rule_id", "")).strip())
         and bool(str(found.get("detail", "")).strip()),
         f"got {found!r}")

    # build_source_copy_block must actually flip to revise-from-source.
    block = orch.build_source_copy_block(section["content"], finding=found)
    test("build_source_copy_block flips to REVISE FROM SOURCE",
         "REVISE FROM SOURCE" in block, block[:200])
    test("the finding's rule_id reaches the prompt",
         "social_proof" in block, block[:300])

    # A malformed shape must raise, not warn — the consumer would swallow it.
    raised = False
    try:
        mod.validate_consumed_shape({"homepage": {"aaa111": {"rule_id": ""}}})
    except ValueError:
        raised = True
    test("validate_consumed_shape rejects a verdict with no rule_id", raised)
    raised = False
    try:
        mod.validate_consumed_shape({"aaa111": {"rule_id": "x", "detail": "y"}})
    except ValueError:
        raised = True
    test("validate_consumed_shape rejects a shape the consumer would mis-detect",
         raised)


def test_determinism_byte_identical():
    print("\nDeterminism — two runs, byte-identical")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        report, spec = write_fixtures(tmp)
        a, b = tmp / "run-a", tmp / "run-b"
        r1 = run_cli(report, spec, a)
        r2 = run_cli(report, spec, b)
        test("first run exits 0", r1.returncode == 0, r1.stderr[-400:])
        test("second run exits 0", r2.returncode == 0, r2.stderr[-400:])
        for name in ("copy-findings.json", "unroutable-findings.json"):
            # Guarded: a refused run writes nothing, and a missing file must
            # read as a failure here rather than as a traceback that hides the
            # remaining assertions.
            if not (a / name).is_file() or not (b / name).is_file():
                test(f"{name} written by both runs", False, "output missing")
                continue
            first = (a / name).read_bytes()
            second = (b / name).read_bytes()
            test(f"{name} byte-identical across runs", first == second,
                 f"{len(first)} vs {len(second)} bytes")
        register = a / "unroutable-findings.json"
        test("no timestamp leaked into the outputs",
             register.is_file()
             and not any(tok in register.read_text()
                         for tok in ("generated_at", "timestamp", "202")),
             register.read_text()[:200] if register.is_file() else "missing")


def test_not_measured_is_not_a_pass():
    print("\nThree-state — a report with no findings is NOT_MEASURED, not PASS")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _, spec = write_fixtures(tmp)
        empty = tmp / "empty.yaml"
        empty.write_text("meta: {}\naudit_summary: {}\n", encoding="utf-8")
        r = run_cli(empty, spec, tmp / "out")
        test("exit 3 (NOT_MEASURED) when findings[] is absent",
             r.returncode == 3, f"exit {r.returncode}: {r.stderr[-300:]}")
        test("says NOT_MEASURED out loud", "NOT_MEASURED" in r.stderr,
             r.stderr[-300:])
        missing = tmp / "nope.yaml"
        r = run_cli(missing, spec, tmp / "out2")
        test("exit 64 (usage) on a missing report", r.returncode == 64,
             f"exit {r.returncode}")


def test_no_section_map_is_counted():
    print("\nNo site-spec — findings are counted, not mapped")
    mod = load_compiler()
    result = mod.compile_verdicts(fixture_report(), {})
    summary = result["unroutable"]["summary"]
    n_in = len(fixture_report()["findings"])
    test("nothing is mapped without a section map",
         summary["verdict_findings"] == 0)
    test("every finding is still accounted for",
         summary["unroutable_findings"] == n_in,
         f"{summary['unroutable_findings']} != {n_in}")
    test("copy-actionable findings say why: no-section-map",
         summary["by_reason"].get("no-section-map", 0) > 0,
         json.dumps(summary["by_reason"], sort_keys=True))


def main():
    print("=" * 66)
    print("  findings-to-verdicts — routed or counted, never dropped")
    print("=" * 66)
    test_accounting_and_lanes()
    test_consumed_schema_is_the_consumers_own()
    test_determinism_byte_identical()
    test_not_measured_is_not_a_pass()
    test_no_section_map_is_counted()
    print("\n" + "=" * 66)
    print(f"  {PASS} passed, {FAIL} failed")
    print("=" * 66)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
