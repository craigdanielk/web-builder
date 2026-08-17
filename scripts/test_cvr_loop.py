#!/usr/bin/env python3
"""Tests for scripts/cvr_loop.py — the CVR loop driver (Task K3).

No test runs a real build. The loop takes its build, audit and serve commands
through three seams — `--orchestrate-cmd`, `--audit-cmd`, `--serve-cmd` — each a
shlex-split command prefix with argv appended. A stub build script parses `--output-root`,
`--copy-findings` and the project name off that argv and plants a fixture build
dir; a stub audit script plants a fixture `audit_result.yaml`. The stubs decide
their own exit code and stdout, so the tests drive the loop's control flow —
which is what is under test, not the compiler K1 and K2 already test.

What is asserted:
  * a compliance FAIL on either build aborts with the BUILD's exit code, and
    the report records where — never a partial report that swallows it;
  * a NOT_MEASURED audit lane still produces a funnel-only report at exit 0,
    with the reason named;
  * the merge preserves both sources' counts (the accounting invariant), at the
    SLOT level — a page-level dict update would drop slots and is caught;
  * the report's control field flags a changed non-verdict input;
  * nothing-measured is exit 3, usage is exit 64, and the output/ guard holds.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent

_spec = importlib.util.spec_from_file_location("cvr_loop", SCRIPTS / "cvr_loop.py")
cvr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cvr)

PASSED = 0
FAILED = 0


def test(name: str, cond: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  ✓ {name}")
    else:
        FAILED += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


# ─────────────────────────────────────────────────────────────────────────────
# fixtures
# ─────────────────────────────────────────────────────────────────────────────

STUB_BUILD = r"""#!/usr/bin/env python3
# Stub build. Plants a MULTIPAGE build fixture K1 and K2 can both read.
#
# Not a mock of the compiler — a minimum real artefact set: site-spec.json with
# `section_uid` per section (K1's preferred slot key), site-manifest.json with
# the route, page_type and nav K2 grades, and section-artifacts/<page>/NN-*.json
# with `provenance[]` rows (K2 reads slot values from provenance, not from TSX).
# Exit code and compliance line come from the environment.
import json, os, sys
from pathlib import Path

argv = sys.argv[1:]
project = argv[0]
root = Path(argv[argv.index("--output-root") + 1])
copy_findings = None
if "--copy-findings" in argv:
    copy_findings = Path(argv[argv.index("--copy-findings") + 1])

bd = root / project
(bd / "section-artifacts" / "homepage").mkdir(parents=True, exist_ok=True)
(bd / "sections" / "homepage").mkdir(parents=True, exist_ok=True)
# A servable-looking site dir: serve_site's preconditions are real checks and
# the test drives them separately; here they must simply be satisfied.
for sub in (".next", "node_modules"):
    (bd / "site" / sub).mkdir(parents=True, exist_ok=True)
(bd / "site" / "package.json").write_text('{"name":"stub"}')

HERO = {"section_uid": "aaa", "archetype": "HERO", "index": 0,
        "content": {"headings": ["Move money"], "body_text": ["Sourced body."],
                    "ctas": [{"text": "Open an account", "url": "/signup"}]}}
CTA = {"section_uid": "bbb", "archetype": "CTA", "index": 1,
       "content": {"headings": ["Ready?"], "body_text": ["Also sourced."],
                   "ctas": [{"text": "Start", "url": "/signup"}]}}
PAGE = {"page_id": "homepage", "route": "/", "page_type": "homepage",
        "nav": {"links": [{"href": "/"}, {"href": "/signup"}]},
        "sections": [HERO, CTA]}
(bd / "site-spec.json").write_text(json.dumps({"pages": [PAGE]}, indent=2))
(bd / "site-manifest.json").write_text(json.dumps({"pages": [PAGE]}, indent=2))
(bd / "asset-coverage.json").write_text(
    json.dumps({"total": 3, "extracted": 3, "generated": 0, "unresolved": 0}))

# The second section's body changes iff a verdicts file was passed — that is
# what "sections revised" means to the loop, made observable without a real
# revise-from-source pass.
revised = "revised" if copy_findings else "verbatim"
(bd / "section-artifacts" / "homepage" / "01-hero.json").write_text(json.dumps({
    "section_uid": "aaa", "section_index": 0, "archetype": "HERO",
    "variant": "split", "origin": "template",
    "provenance": [{"slot": "headline", "value": "Move money", "source": "harvested"},
                   {"slot": "primary_cta_text", "value": "Open an account",
                    "source": "harvested"},
                   {"slot": "primary_cta_url", "value": "/signup",
                    "source": "harvested"}]}, indent=2))
(bd / "section-artifacts" / "homepage" / "02-cta.json").write_text(json.dumps({
    "section_uid": "bbb", "section_index": 1, "archetype": "CTA",
    "variant": "centered", "origin": "template", "mode": revised,
    "provenance": [{"slot": "headline", "value": "Ready?", "source": "harvested"},
                   {"slot": "primary_cta_text", "value": "Start", "source": "harvested"},
                   # The harvest was exhausted here: an emitted <a href=""> with
                   # no destination. funnel_conversion_has_a_sourced_action is
                   # about exactly this, and it is SECTION-scoped, so it becomes
                   # a verdict — which is what gives the merge two sources.
                   {"slot": "primary_cta_url", "value": "", "source": "empty"}]},
    indent=2))
(bd / "sections" / "homepage" / "01-hero.tsx").write_text("export const Hero = 1\n")
(bd / "sections" / "homepage" / "02-cta.tsx").write_text(
    f"export const Cta = '{revised}'\n")

print("  building " + project)
print("  " + os.environ.get("STUB_COMPLIANCE_LINE", "✓ GATE compliance: PASS"))
sys.exit(int(os.environ.get("STUB_BUILD_RC", "0")))
"""

# A trivial server, so the audit lane's control flow can be driven without
# Next.js. The real default is `npm run start --`.
STUB_SERVER = r"""#!/usr/bin/env python3
import http.server, socketserver, sys
port = int(sys.argv[sys.argv.index("--port") + 1])
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", port),
                            http.server.SimpleHTTPRequestHandler) as srv:
    srv.serve_forever()
"""

STUB_AUDIT = r'''#!/usr/bin/env python3
"""Stub audit. Writes audit_result.yaml into --output-dir, or nothing."""
import os, sys
from pathlib import Path

argv = sys.argv[1:]
out = Path(argv[argv.index("--output-dir") + 1])
if os.environ.get("STUB_AUDIT_SILENT"):
    sys.exit(int(os.environ.get("STUB_AUDIT_RC", "1")))
out.mkdir(parents=True, exist_ok=True)
(out / "audit_result.yaml").write_text(os.environ["STUB_AUDIT_YAML"])
print("audit written")
sys.exit(int(os.environ.get("STUB_AUDIT_RC", "0")))
'''

# Findings K1 can act on: two `h1_presence` findings on "/" (a rule in K1's
# COPY_RULE_TARGETS table, targeting HERO) plus a `dna_*` one it must refuse,
# so the register is non-empty and the counting invariant has both sides.
AUDIT_YAML = """\
pages:
  - url: http://127.0.0.1:1/
findings:
  - rule_id: h1_presence
    state: FAIL
    severity: high
    layer: L1_strategic_ux
    issue: the hero states no value proposition
    recommended_fix: restate the harvested value proposition in the h1
    affected_pages:
      - http://127.0.0.1:1/
    evidence:
      - source: heuristics
        page_url: http://127.0.0.1:1/
        selector: null
  - rule_id: dna_palette_conformance
    state: FAIL
    severity: medium
    layer: L4_visual_systems
    issue: accent drifts from the benchmark
    affected_pages:
      - http://127.0.0.1:1/
    evidence:
      - source: design_conformance
        page_url: http://127.0.0.1:1/
        selector: null
  - rule_id: h1_presence
    state: PASS
    severity: low
    layer: L1_strategic_ux
    issue: fine
    affected_pages:
      - http://127.0.0.1:1/
    evidence:
      - source: heuristics
        page_url: http://127.0.0.1:1/
        selector: null
"""


def write_stub(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(0o755)
    return path


def loop(tmp: Path, *extra: str, env: dict | None = None,
         audit: bool = True, project: str = "stub-proj") -> subprocess.CompletedProcess:
    """Run cvr_loop.py in a subprocess against the stubs."""
    build_stub = write_stub(tmp / "stub_build.py", STUB_BUILD)
    audit_stub = write_stub(tmp / "stub_audit.py", STUB_AUDIT)
    serve_stub = write_stub(tmp / "stub_server.py", STUB_SERVER)
    out_root = tmp / "scratch"
    argv = [sys.executable, str(SCRIPTS / "cvr_loop.py"), project,
            "--output-root", str(out_root),
            "--orchestrate-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(build_stub))}",
            "--audit-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(audit_stub))}",
            "--serve-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(serve_stub))}",
            *extra]
    if not audit:
        argv.append("--no-audit-built")
    e = dict(os.environ)
    e["STUB_AUDIT_YAML"] = AUDIT_YAML
    e.update(env or {})
    return subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True, env=e)


def read_report(tmp: Path) -> dict:
    return json.loads((tmp / "scratch" / "cvr-loop-report.json").read_text())


# ─────────────────────────────────────────────────────────────────────────────
# 1. the merge — the accounting invariant, at the slot level
# ─────────────────────────────────────────────────────────────────────────────

print("\n─── merge_verdicts: both sources' counts survive ───")

AUDIT_CF = {
    "homepage": {"aaa": {"rule_id": "h1_presence", "detail": "x"}},
    "about": {"ccc": {"rule_id": "h1_presence", "detail": "y"}},
}
FUNNEL_CF = {
    # Same page as the audit, DIFFERENT slot — a page-level dict update would
    # drop the audit's slot here. This is the bug the slot-level merge exists
    # to avoid, and the assertion below is what catches it.
    "homepage": {"bbb": {"rule_id": "funnel_route_closes_with_conversion", "detail": "z"}},
    "wealth": {"ddd": {"rule_id": "funnel_trust_precedes_first_conversion", "detail": "w"}},
}

m = cvr.merge_verdicts(AUDIT_CF, FUNNEL_CF)
test("merged slot count == audit slots + funnel slots",
     m["accounting"]["merged_slots"] == 4, json.dumps(m["accounting"]))
test("accounting invariant holds", m["accounting"]["consistent"] is True)
test("audit slot survives a shared page",
     m["copy_findings"]["homepage"].get("aaa", {}).get("rule_id") == "h1_presence",
     json.dumps(m["copy_findings"].get("homepage")))
test("funnel slot lands on the shared page",
     m["copy_findings"]["homepage"].get("bbb", {}).get("rule_id")
     == "funnel_route_closes_with_conversion")
test("audit-only page kept", "ccc" in m["copy_findings"]["about"])
test("funnel-only page kept", "ddd" in m["copy_findings"]["wealth"])
test("no collisions on disjoint slots", m["accounting"]["collisions"] == 0)
test("per-source counts recorded separately",
     (m["accounting"]["audit_slots"], m["accounting"]["funnel_slots"]) == (2, 2))

coll = cvr.merge_verdicts(
    {"homepage": {"aaa": {"rule_id": "h1_presence"}}},
    {"homepage": {"aaa": {"rule_id": "funnel_route_offers_an_action"}}})
test("a slot collision is counted, not silently dropped",
     coll["accounting"]["collisions"] == 1 and coll["accounting"]["consistent"] is True,
     json.dumps(coll["accounting"]))
test("the audit verdict wins a collision; the loser is named",
     coll["copy_findings"]["homepage"]["aaa"]["rule_id"] == "h1_presence"
     and coll["collisions"][0]["displaced"] == "funnel_route_offers_an_action")

def _validate_ok(cf) -> bool:
    try:
        cvr.validate_consumed_shape(cf)
        return True
    except ValueError:
        return False


test("validate_consumed_shape accepts the merged shape", _validate_ok(m["copy_findings"]))
test("validate_consumed_shape rejects a flat (scalar-valued) shape",
     not _validate_ok({"homepage": 3}))
test("validate_consumed_shape rejects an empty page mapping",
     not _validate_ok({"homepage": {}}))

# The real consumer's own detector, imported rather than restated: if the merge
# ever produced something orchestrate reads as flat, the verdicts would address
# the wrong slots silently.
sys.path.insert(0, str(SCRIPTS))
try:
    import orchestrate  # type: ignore
    test("orchestrate._findings_are_page_scoped accepts the merged file",
         orchestrate._findings_are_page_scoped(m["copy_findings"]) is True)
except Exception as exc:  # pragma: no cover - import failure is itself reportable
    test("orchestrate._findings_are_page_scoped accepts the merged file", False,
         f"import failed: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. build_is_fatal — the abort predicate
# ─────────────────────────────────────────────────────────────────────────────

print("\n─── build_is_fatal ───")
test("compliance FAIL is fatal even on exit 0",
     cvr.build_is_fatal({"compliance_gate": "fail", "exit_code": 0})[0] is True)
test("a non-zero exit is fatal",
     cvr.build_is_fatal({"compliance_gate": "pass", "exit_code": 7})[0] is True)
test("compliance NOT_MEASURED on exit 0 is not fatal",
     cvr.build_is_fatal({"compliance_gate": "not_measured", "exit_code": 0})[0] is False)
test("a clean build is not fatal",
     cvr.build_is_fatal({"compliance_gate": "pass", "exit_code": 0})[0] is False)


# ─────────────────────────────────────────────────────────────────────────────
# 3. the loop end to end, against the stubs
# ─────────────────────────────────────────────────────────────────────────────

print("\n─── loop: happy pass (audit lane measured) ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-happy-"))
r = loop(tmp)
rep = read_report(tmp) if (tmp / "scratch" / "cvr-loop-report.json").exists() else {}
test("exit 0", r.returncode == 0, r.stdout[-800:] + r.stderr[-800:])
test("outcome completed", rep.get("outcome") == "completed")
it = (rep.get("iterations") or [{}])[0]
test("both builds ran and exited 0",
     it.get("build_a", {}).get("exit_code") == 0
     and it.get("build_b", {}).get("exit_code") == 0)
test("audit lane measured", it.get("audit_a", {}).get("state") == "measured",
     json.dumps(it.get("audit_a")))
test("K1 produced a verdict from the built-site audit",
     it.get("merged", {}).get("accounting", {}).get("audit_slots", 0) >= 1,
     json.dumps(it.get("merged", {}).get("accounting")))
test("K1's counting invariant is carried into the report's per-source block",
     (it.get("merged", {}).get("per_source", {}).get("audit_findings_input")
      == (it["merged"]["per_source"]["audit_findings_placed"]
          + it["merged"]["per_source"]["audit_findings_unroutable"])),
     json.dumps(it.get("merged", {}).get("per_source")))
test("the rebuild revised the verdict-bearing section",
     it.get("section_diff", {}).get("changed") == ["homepage/02-cta.json"],
     json.dumps(it.get("section_diff")))
test("the emitted TSX changed too",
     it.get("emitted_diff", {}).get("changed") == ["homepage/02-cta.tsx"],
     json.dumps(it.get("emitted_diff")))
test("control field says the non-verdict inputs did not change",
     it.get("control", {}).get("non_verdict_inputs_unchanged") is True,
     json.dumps(it.get("control", {}).get("changed_inputs")))
test("a merged verdicts file was written",
     Path(it.get("merged", {}).get("path", "/nonexistent")).is_file())
test("the second build was passed --copy-findings",
     "--copy-findings" in (it.get("build_b", {}).get("argv") or []))
test("the first build was NOT passed --copy-findings",
     "--copy-findings" not in (it.get("build_a", {}).get("argv") or []))
test("verdict effect is 'applied' when the rebuild changed a section",
     it.get("verdict_effect", {}).get("state") == "applied",
     json.dumps(it.get("verdict_effect")))
test("the audit was handed the built routes, not a crawl",
     it.get("audit_a", {}).get("mode") == "urls"
     and it["audit_a"]["routes_audited"] == ["/"],
     json.dumps(it.get("audit_a", {}).get("mode")))
test("--publish is never passed",
     "--publish" not in (it.get("build_a", {}).get("argv") or [])
     and "--publish" not in (it.get("build_b", {}).get("argv") or []))
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── loop: compliance FAIL on build A aborts with the build's code ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-compA-"))
r = loop(tmp, env={"STUB_COMPLIANCE_LINE": "✖ GATE compliance: FAIL — prohibited term",
                   "STUB_BUILD_RC": "1"})
rep = read_report(tmp) if (tmp / "scratch" / "cvr-loop-report.json").exists() else {}
test("aborts with the build's exit code", r.returncode == 1, f"got {r.returncode}")
test("outcome names build_a", rep.get("outcome") == "aborted-at-build_a",
     str(rep.get("outcome")))
it = (rep.get("iterations") or [{}])[0]
test("the abort record names the compliance channel",
     "compliance" in (it.get("aborted", {}).get("why", "")),
     json.dumps(it.get("aborted")))
test("no second build was attempted after the abort", "build_b" not in it)
test("no merged verdicts file was written after the abort",
     not (tmp / "scratch" / "pass1-verdicts" / "merged-copy-findings.json").exists())
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── loop: a compliance FAIL that still exits 0 is caught anyway ───")
# The compliance gate records a build failure and so should exit 1; if that
# link ever breaks, the loop must still refuse the build on the gate line.
tmp = Path(tempfile.mkdtemp(prefix="cvr-comp0-"))
r = loop(tmp, env={"STUB_COMPLIANCE_LINE": "✖ GATE compliance: FAIL — prohibited term",
                   "STUB_BUILD_RC": "0"})
rep = read_report(tmp) if (tmp / "scratch" / "cvr-loop-report.json").exists() else {}
test("aborts even though the build exited 0", r.returncode != 0, f"got {r.returncode}")
test("outcome names build_a", rep.get("outcome") == "aborted-at-build_a",
     str(rep.get("outcome")))
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── loop: NOT_MEASURED audit lane still produces a funnel-only report ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-noaudit-"))
r = loop(tmp, audit=False)
rep = read_report(tmp) if (tmp / "scratch" / "cvr-loop-report.json").exists() else {}
it = (rep.get("iterations") or [{}])[0]
test("exit 0 — a missing audit lane is not a loop failure", r.returncode == 0,
     r.stdout[-600:] + r.stderr[-600:])
test("audit lane NOT_MEASURED with a reason",
     it.get("audit_a", {}).get("state") == "not_measured"
     and bool(it.get("audit_a", {}).get("reason")),
     json.dumps(it.get("audit_a")))
test("the reason is surfaced in the report's not_measured_lanes",
     any(row["lane"] == "audit-built-site" for row in rep.get("not_measured_lanes", [])),
     json.dumps(rep.get("not_measured_lanes")))
test("K1 is NOT_MEASURED, not silently zero",
     it.get("k1", {}).get("state") == "not_measured")
test("no audit-sourced verdicts",
     it.get("merged", {}).get("accounting", {}).get("audit_slots") == 0)
test("findings closed/remaining is NOT_MEASURED, not reported as 0 closed",
     "findings_fate" not in it
     and any(row["lane"] == "findings-closed-remaining"
             for row in rep.get("not_measured_lanes", [])),
     json.dumps(rep.get("not_measured_lanes")))
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── loop: the audit ran and wrote nothing → NOT_MEASURED, named ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-auditfail-"))
r = loop(tmp, env={"STUB_AUDIT_SILENT": "1", "STUB_AUDIT_RC": "2"})
rep = read_report(tmp) if (tmp / "scratch" / "cvr-loop-report.json").exists() else {}
it = (rep.get("iterations") or [{}])[0]
test("exit 0 — the loop continues", r.returncode == 0, r.stderr[-500:])
test("audit lane NOT_MEASURED", it.get("audit_a", {}).get("state") == "not_measured")
test("no findings were invented",
     it.get("merged", {}).get("accounting", {}).get("audit_slots") == 0)
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── loop: control field flags a CHANGED non-verdict input ───")
# The funnel rules file is a declared non-verdict input. A --rules file that is
# mutated between build A and build B must make the control field false, because
# the diff is then no longer attributable to the verdicts alone. The audit stub
# is the seam that mutates it: it runs between the two digest snapshots.
tmp = Path(tempfile.mkdtemp(prefix="cvr-control-"))
rules_copy = tmp / "funnel-rules.json"
shutil.copy(ROOT / "skills" / "funnel-rules.json", rules_copy)
mutating_audit = write_stub(tmp / "stub_audit.py", STUB_AUDIT.replace(
    'print("audit written")',
    f'Path({str(rules_copy)!r}).write_text('
    f'Path({str(rules_copy)!r}).read_text() + "\\n")\nprint("audit written")'))
build_stub = write_stub(tmp / "stub_build.py", STUB_BUILD)
serve_stub = write_stub(tmp / "stub_server.py", STUB_SERVER)
e = dict(os.environ, STUB_AUDIT_YAML=AUDIT_YAML)
r = subprocess.run(
    [sys.executable, str(SCRIPTS / "cvr_loop.py"), "stub-proj",
     "--output-root", str(tmp / "scratch"),
     "--rules", str(rules_copy),
     "--orchestrate-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(build_stub))}",
     "--audit-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(mutating_audit))}",
     "--serve-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(serve_stub))}"],
    cwd=str(ROOT), capture_output=True, text=True, env=e)
rep = read_report(tmp) if (tmp / "scratch" / "cvr-loop-report.json").exists() else {}
it = (rep.get("iterations") or [{}])[0]
test("the loop still completes", r.returncode == 0, r.stderr[-600:])
test("control.non_verdict_inputs_unchanged is False",
     it.get("control", {}).get("non_verdict_inputs_unchanged") is False,
     json.dumps(it.get("control")))
test("the changed input is named",
     "funnel_rules" in (it.get("control", {}).get("changed_inputs") or []),
     json.dumps(it.get("control", {}).get("changed_inputs")))
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── loop: usage and the output/ guard ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-usage-"))
r = subprocess.run([sys.executable, str(SCRIPTS / "cvr_loop.py")],
                   cwd=str(ROOT), capture_output=True, text=True)
test("no args → 64", r.returncode == cvr.EXIT_USAGE, f"got {r.returncode}")
r = subprocess.run([sys.executable, str(SCRIPTS / "cvr_loop.py"), "cape-crypto",
                    "--output-root", str(ROOT / "output" / "cape-crypto")],
                   cwd=str(ROOT), capture_output=True, text=True)
test("refuses to write under output/ → 64", r.returncode == cvr.EXIT_USAGE,
     f"got {r.returncode}: {r.stderr[-200:]}")
test("the refusal names the guarded path", "output" in r.stderr)
r = subprocess.run([sys.executable, str(SCRIPTS / "cvr_loop.py"), "p",
                    "--output-root", str(tmp), "--max-iterations", "0"],
                   cwd=str(ROOT), capture_output=True, text=True)
test("--max-iterations 0 → 64", r.returncode == cvr.EXIT_USAGE, f"got {r.returncode}")
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── loop: nothing measurable at all → exit 3 ───")
# No audit lane AND a build dir with no sections: K2 exits 3 (no funnel to
# grade) and K1 was never run. Nothing was measured, so the loop must say 3 and
# not 0-with-an-empty-report.
tmp = Path(tempfile.mkdtemp(prefix="cvr-nm-"))
empty_build = write_stub(tmp / "empty_build.py", (
    "#!/usr/bin/env python3\n"
    "import sys\nfrom pathlib import Path\n"
    "argv = sys.argv[1:]\n"
    "root = Path(argv[argv.index('--output-root') + 1])\n"
    "(root / argv[0]).mkdir(parents=True, exist_ok=True)\n"
    "print('  ✓ GATE compliance: PASS')\n"))
r = subprocess.run(
    [sys.executable, str(SCRIPTS / "cvr_loop.py"), "empty-proj",
     "--output-root", str(tmp / "scratch"), "--no-audit-built",
     "--orchestrate-cmd", f"{shlex.quote(sys.executable)} {shlex.quote(str(empty_build))}"],
    cwd=str(ROOT), capture_output=True, text=True)
rep = read_report(tmp) if (tmp / "scratch" / "cvr-loop-report.json").exists() else {}
test("exit 3 when nothing could be measured", r.returncode == cvr.EXIT_NOT_MEASURED,
     f"got {r.returncode}: {r.stderr[-300:]}")
test("outcome not-measured", rep.get("outcome") == "not-measured", str(rep.get("outcome")))
test("both lanes' reasons are recorded",
     {row["lane"] for row in rep.get("not_measured_lanes", [])}
     >= {"audit-built-site", "k1-audit-verdicts", "k2-funnel-verdicts"},
     json.dumps(rep.get("not_measured_lanes")))
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── built_routes: the audit is handed what was built ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-routes-"))
test("no manifest → no routes", cvr.built_routes(tmp) == [])
(tmp / "site-manifest.json").write_text(json.dumps({"pages": [
    {"route": "/"}, {"route": "/wealth"}, {"route": "/products/[handle]"},
    {"route": "/wealth"}]}))
test("routes are de-duplicated and dynamic segments dropped",
     cvr.built_routes(tmp) == ["/", "/wealth"], json.dumps(cvr.built_routes(tmp)))
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── verdict_effect: four states, none of them a shrug ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-effect-"))
log = tmp / "b.log"
a, b = tmp / "a", tmp / "b"
a.mkdir(); b.mkdir()
log.write_text("  ✓ Loaded copy findings for 2 slot(s) from /x\n")
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": []}, 2)
test("loaded, nothing changed, no copy-manifest → loaded-but-inert",
     e["state"] == "loaded-but-inert", e["state"])
test("the reason names the LLM branch as the mechanism",
     "LLM section-generation branch" in e["reason"], e["reason"])
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": ["homepage/02-cta.json"]}, 2)
test("a changed section → applied", e["state"] == "applied", e["state"])
log.write_text("no mention of the file at all\n")
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": []}, 2)
test("never loaded → not-loaded", e["state"] == "not-loaded", e["state"])

# ── the fourth state: every verdict got a disposition, none could act ──
log.write_text("  ✓ Loaded copy findings for 2 slot(s) from /x\n")


def _register(**summary) -> None:
    (b / "copy-manifest-verdicts.json").write_text(json.dumps({
        "schema": "aurelix.copy_revision.v1",
        "pages_covered": ["homepage"],
        "summary": {"verdicts": 2, "dispositions": 2, "revised": 0,
                    "unactionable": 2,
                    "by_reason": {"no-alternate-candidate": 2}, **summary},
    }))


_register()
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": []}, 2)
test("a balanced register, nothing changed → recorded-unactionable",
     e["state"] == "recorded-unactionable", e["state"])
test("the reason names the per-verdict reasons, not just a count",
     "no-alternate-candidate" in e["reason"], e["reason"])
test("the disposition summary travels in the field",
     (e.get("dispositions") or {}).get("dispositions") == 2,
     json.dumps(e.get("dispositions")))

# A register that does not balance cannot testify. It must fall back to inert,
# never be believed on the strength of its filename.
_register(dispositions=1)
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": []}, 2)
test("a short register is not evidence → loaded-but-inert",
     e["state"] == "loaded-but-inert", e["state"])
_register(verdicts=0, dispositions=0)
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": []}, 2)
test("an empty register is not evidence → loaded-but-inert",
     e["state"] == "loaded-but-inert", e["state"])
(b / "copy-manifest-verdicts.json").write_text(json.dumps(
    {"schema": "aurelix.copy_manifest.v9", "summary":
     {"verdicts": 2, "dispositions": 2}}))
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": []}, 2)
test("a copy-manifest of another schema is not read as a register",
     e["state"] == "loaded-but-inert", e["state"])
(b / "copy-manifest-verdicts.json").write_text("{not json")
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": []}, 2)
test("a corrupt register is not evidence → loaded-but-inert",
     e["state"] == "loaded-but-inert", e["state"])
# A real copy change still outranks the register: `applied` means copy moved.
_register()
e = cvr.verdict_effect({"log": str(log)}, a, b, {"changed": ["h/02-cta.json"]}, 2)
test("a changed section still wins over the register → applied",
     e["state"] == "applied", e["state"])
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── serve_site refuses without a production build ───")
tmp = Path(tempfile.mkdtemp(prefix="cvr-serve-"))
proc, port, reason = cvr.serve_site(tmp / "site")
test("no package.json → refused with a reason",
     proc is None and "package.json" in reason, reason)
(tmp / "site").mkdir()
(tmp / "site" / "package.json").write_text("{}")
proc, port, reason = cvr.serve_site(tmp / "site")
test("no .next → refused naming --deploy", proc is None and "--deploy" in reason, reason)
(tmp / "site" / ".next").mkdir()
proc, port, reason = cvr.serve_site(tmp / "site")
test("no node_modules → refused with a reason",
     proc is None and "node_modules" in reason, reason)
shutil.rmtree(tmp, ignore_errors=True)


print("\n─── diff_inventories ───")
d = cvr.diff_inventories({"a": "1", "b": "2", "c": "3"}, {"a": "1", "b": "9", "d": "4"})
test("changed only counts keys present on both sides", d["changed"] == ["b"])
test("added and removed are separate", d["added"] == ["d"] and d["removed"] == ["c"])


print(f"\nRESULTS: {PASSED} passed, {FAILED} failed")
if FAILED:
    sys.exit(1)
