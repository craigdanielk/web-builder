#!/usr/bin/env python3
"""
Build Outcome Verification — exit codes must distinguish "the audit could
not run" (NOT_MEASURED) from "the audit ran and found problems" (FAILED)
from "the audit ran and passed" (OK).

Extracts resolve_build_outcome() (+ its BUILD_FAILURES ledger and EXIT_*
constants) from orchestrate.py via AST, mirroring test_deploy_adapter.py.
orchestrate.py cannot be imported directly under Python 3.9 (PEP 604
`dict | None` annotations); resolve_build_outcome()'s own signature and body
are plain 3.9-compatible syntax, so extracting just that source and exec'ing
it in an isolated namespace sidesteps the import-time failure entirely.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def extract_defs(filepath: Path, names: set) -> str:
    """Extract top-level assignment/function source for the given names."""
    source = filepath.read_text()
    tree = ast.parse(source)
    chunks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            chunks.append(ast.get_source_segment(source, node))
        elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) in names:
            chunks.append(ast.get_source_segment(source, node))
        elif isinstance(node, ast.Assign):
            targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if targets & names:
                chunks.append(ast.get_source_segment(source, node))
    return "\n\n".join(chunks)


PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


print("\n═══ Build Outcome Verification ═══\n")

orch = ROOT / "scripts" / "orchestrate.py"
chunk = extract_defs(orch, {
    "BUILD_FAILURES", "record_build_failure", "reset_build_failures",
    "EXIT_OK", "EXIT_FAILED", "EXIT_REVIEW_NEEDED", "EXIT_NOT_MEASURED",
    "resolve_build_outcome",
})

ns = {"__name__": "__build_outcome__"}
exec(compile(chunk, str(orch), "exec"), ns)

resolve_build_outcome = ns["resolve_build_outcome"]
reset_build_failures = ns["reset_build_failures"]
record_build_failure = ns["record_build_failure"]
EXIT_OK = ns["EXIT_OK"]
EXIT_FAILED = ns["EXIT_FAILED"]
EXIT_REVIEW_NEEDED = ns["EXIT_REVIEW_NEEDED"]
EXIT_NOT_MEASURED = ns["EXIT_NOT_MEASURED"]

test("EXIT_NOT_MEASURED is its own code, distinct from OK/FAILED/REVIEW_NEEDED",
     len({EXIT_OK, EXIT_FAILED, EXIT_REVIEW_NEEDED, EXIT_NOT_MEASURED}) == 4)

# ── Deploy not requested: audit is not applicable regardless of audit_ran ──
reset_build_failures()
status, code = resolve_build_outcome("skipped", False)
test("no deploy requested → completed / OK", (status, code) == ("completed", EXIT_OK))

# ── Audit ran and passed ──
reset_build_failures()
status, code = resolve_build_outcome("passed", True, audit_ran=True)
test("audit passed → completed / OK", (status, code) == ("completed", EXIT_OK))

# ── Audit ran and found defects needing review ──
reset_build_failures()
status, code = resolve_build_outcome("review_needed", True, audit_ran=True)
test("audit review_needed → partial / REVIEW_NEEDED", (status, code) == ("partial", EXIT_REVIEW_NEEDED))

# ── Audit could not run at all (timeout, missing tooling, server never started) ──
# This is the real-world case: render-audit.js timed out after 180s, nothing
# else was wrong, and the old code collapsed it into exit 1 — indistinguishable
# from "the audit ran and found the site broken".
reset_build_failures()
status, code = resolve_build_outcome("failed", True, audit_ran=False)
test("audit could not run → NOT success", code != EXIT_OK)
test("audit could not run → exit NOT_MEASURED, not exit FAILED", code == EXIT_NOT_MEASURED)
test("audit could not run → status stays in the build_log CHECK constraint set",
     status in ("completed", "failed", "partial"))

reset_build_failures()
status, code = resolve_build_outcome("skipped", True, audit_ran=False)
test("audit skipped (no tooling) → exit NOT_MEASURED", code == EXIT_NOT_MEASURED)

# ── Default audit_ran=True preserves the pre-existing two call sites ──
# Neither original call site passed audit_ran; the parameter must default to
# True so unmodified call sites keep their old behavior verbatim.
reset_build_failures()
status, code = resolve_build_outcome("failed", True)
test("audit_ran defaults to True (old call-site signature unaffected)",
     (status, code) == ("failed", EXIT_FAILED))

# ── A recorded build failure always wins, regardless of the audit ──
reset_build_failures()
record_build_failure("sections", "dropped section 04")
status, code = resolve_build_outcome("passed", True, audit_ran=True)
test("recorded build failure outranks a passing audit", (status, code) == ("failed", EXIT_FAILED))

reset_build_failures()
record_build_failure("build", "npm run build failed")
status, code = resolve_build_outcome("skipped", True, audit_ran=False)
test("recorded build failure outranks NOT_MEASURED too — it's a real failure, not just unmeasured",
     (status, code) == ("failed", EXIT_FAILED))

reset_build_failures()

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)
