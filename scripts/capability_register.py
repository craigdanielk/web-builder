#!/usr/bin/env python3
"""Compile the Aurelix capability register from the instruments themselves.

WHY THIS EXISTS
---------------
On 2026-08-18 five checkers were hand-written that duplicated instruments
already present in `scripts/quality/`.  Run once, at the end of that day, the
REAL conformance gate found three defects the hand-written one is structurally
incapable of seeing.  The instruments were not missing and 22 of 31 already
parse argv — they were undiscoverable and undescribed.

The obvious fix is a document listing them.  That fix fails: a document goes
stale the first time a flag changes and nothing fails when it does.
`control-tower/registry/capability-matrix.yaml` is the proof — every row carries
`last_measured: '2026-05-09'` and it is still shipping.

So the register is not written.  It is COMPILED, from `--describe` declarations
that live in the instruments' own source files, exactly as `benchmarks/index.json`
is compiled from the benchmark files.  A flag change and its description change
in one edit, or `compile --check` fails the suite.

THE ONE RULE
------------
No entry may claim an outcome that was not produced by running the thing.
`status` and `evidence` are owned by this compiler and may not be declared — an
instrument does not get to grade itself.  A declaration with no matching
execution record is `NOT_VERIFIED`, never "working".

    VERIFIED      an execution record exists whose exit code is in the declared
                  exit_contract
    BROKEN        `--describe` failed to load, or a run returned a code the
                  declaration does not admit
    NOT_RUN       recorded deliberately, with a reason: costs money, or mutates
                  a live store
    NOT_VERIFIED  declared, never run.  The honest default

EXIT CODES — the same three-state contract as every other gate here
    0   PASS / the act succeeded
    1   FAIL — the register disagrees with the instruments, or a declaration is invalid
    3   NOT_MEASURED — nothing to compile
    64  usage error

USAGE
    python3 scripts/capability_register.py compile           # write the register
    python3 scripts/capability_register.py compile --check   # fail on drift
    python3 scripts/capability_register.py verify            # re-run --describe, record loadability
    python3 scripts/capability_register.py record --id <id> --argv '<cmd>' --exit <n> [--note ...]
    python3 scripts/capability_register.py record --id <id> --not-run 'needs a live Shopify store'
    python3 scripts/capability_register.py list [--status BROKEN]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import yaml  # noqa: E402

from lib.capability import (  # noqa: E402
    COMPILER_OWNED,
    CapabilityInvalid,
    validate,
)

ROOT = HERE.parent
REGISTRY_DIR = ROOT / "registry"
REGISTER_PATH = REGISTRY_DIR / "capability-register.yaml"
EVIDENCE_PATH = REGISTRY_DIR / "capability-evidence.json"
SCENARIOS_PATH = REGISTRY_DIR / "scenarios.yaml"

# A scenario step must say what it costs and what skipping it ships. A sequence
# that lists tools without stating the consequence of omitting one is a list, and
# a list is what failed on 2026-08-18 — the instruments were already listed in
# their own directory.
SCENARIO_STEP_REQUIRED = ("capability", "why", "cost", "skipping_ships")
SCENARIO_REQUIRED = ("id", "question", "steps")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_MEASURED = 3
EXIT_USAGE = 64
TOOL = "capability_register.py"

DESCRIBE_TIMEOUT_S = 60

# Where instruments live.  A root that does not exist is skipped, not an error —
# submodules are frequently uninitialised (CLAUDE.md §3.1).
SCAN_ROOTS: tuple[Path, ...] = (
    ROOT / "scripts",
    ROOT.parent / "aurelix-uiux-audit",
    ROOT.parent / "shopify-integration-layer",
)

# A file is a CANDIDATE if it carries one of these markers.  Grep first, execute
# second: running `--describe` against 4,000 files would be slower than the thing
# it documents.
#
# THE EXPLICIT MARKER, AND WHY IT IS NOT JUST THE IMPORT
# An instrument that cannot import the helper still has to be discoverable.  A
# shell script cannot import Python, and an instrument in a sibling repo must
# not: `web-builder` and `aurelix-uiux-audit` BOTH ship a top-level package
# named `lib`, the first import wins for the process, and adding
# `from lib.capability import describe` to `conformance_runner.py` during the
# 2026-08-18 fan-out killed its later `from lib.design_conformance import ...`.
# Those instruments emit the JSON literally under `--describe` and declare
# themselves discoverable with the marker below.
#
# Losing nothing by it: `capability_register.py` re-validates EVERY declaration
# through `lib.capability.validate` whatever produced the JSON, so the schema is
# enforced identically.  What a no-import declaration gives up is only the
# fail-fast check at the instrument's own call site.
CAPABILITY_MARKER = "AURELIX-CAPABILITY"
_MARKERS = (CAPABILITY_MARKER, "lib/capability", "lib.capability",
            "from lib import capability")

_RUNNER = {".js": ["node"], ".mjs": ["node"], ".py": [sys.executable], ".sh": ["bash"]}

_SKIP_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", "output", "fixtures", ".pytest_cache",
})


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def candidate_files(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[Path]:
    """Every file that declares a capability, sorted for a deterministic register."""
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in _RUNNER:
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            # The declaration helpers, this compiler, and the tests that exercise
            # them import `capability` without BEING instruments. Excluding them
            # by name is deliberate and narrow: anything else that imports the
            # helper is expected to declare, and is reported when it does not.
            if path.name in {"capability.js", "capability.py", "capability_register.py"}:
                continue
            if path.name.startswith("test_") or path.name.endswith((".test.js", ".test.mjs")):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(m in text for m in _MARKERS):
                found.append(path)
    return sorted(set(found), key=lambda p: p.as_posix())


def run_describe(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Execute `<runner> <path> --describe`.  Returns `(spec, detail)`.

    A file that cannot be loaded returns `(None, why)` — and that is the point of
    executing rather than parsing a comment.  `shopify_bulk_importer` is the
    cautionary case: `--help` works and 53 tests pass while every subcommand
    raises ImportError, because argparse builds its parser before the lazy
    import.  A parsed comment would have called that tool healthy.
    """
    cmd = _RUNNER[path.suffix] + [str(path), "--describe"]
    try:
        proc = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, timeout=DESCRIBE_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return None, f"--describe timed out after {DESCRIBE_TIMEOUT_S}s"
    except OSError as exc:
        return None, f"could not execute: {exc}"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return None, f"--describe exited {proc.returncode}: {tail[-1] if tail else 'no output'}"
    try:
        spec = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return None, f"--describe did not emit JSON ({exc})"
    return spec, "ok"


# --------------------------------------------------------------------------
# evidence
# --------------------------------------------------------------------------

def load_evidence(path: Path = EVIDENCE_PATH) -> dict[str, list[dict[str, Any]]]:
    """Execution records, keyed by capability id.  A missing store is empty, not an error."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return {}
    by_id: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        if isinstance(rec, dict) and isinstance(rec.get("id"), str):
            by_id.setdefault(rec["id"], []).append(rec)
    return by_id


def save_evidence(by_id: dict[str, list[dict[str, Any]]], path: Path = EVIDENCE_PATH) -> None:
    """Deterministic on disk: sorted by id then by argv, so a re-record is a no-op diff."""
    records = [rec for _id in sorted(by_id) for rec in
               sorted(by_id[_id], key=lambda r: (str(r.get("argv") or ""), str(r.get("exit"))))]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"records": records}, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def _script_token(command: str) -> str:
    """The script a command line runs, by basename.

    HONEST LIMIT: this is how an execution record is matched to a declaration.
    It proves the same file was run; it does not prove the same flags were used.
    Flags are kept verbatim in the record so a human can see them, and a run
    whose exit code is not in the declared contract is BROKEN regardless of
    which flags produced it.
    """
    for token in command.split():
        low = token.lower()
        if low.endswith((".js", ".mjs", ".py", ".sh")):
            return Path(token).name
    return ""


def derive_status(spec: dict[str, Any], records: list[dict[str, Any]]) -> tuple[str, str]:
    """`(status, evidence)` — the compiler's verdict.  Never the instrument's."""
    declared = _script_token(str(spec.get("invocation", "")))
    contract = {str(k) for k in (spec.get("exit_contract") or {})}

    not_run = [r for r in records if r.get("not_run")]
    runs = [r for r in records
            if not r.get("not_run") and _script_token(str(r.get("argv") or "")) == declared]

    off_contract = [r for r in runs if str(r.get("exit")) not in contract]
    if off_contract:
        r = off_contract[0]
        return "BROKEN", (f"ran `{r.get('argv')}` → exit {r.get('exit')}, which the declared "
                          f"exit_contract does not admit ({', '.join(sorted(contract))})"
                          + (f". {r['note']}" if r.get("note") else ""))
    if runs:
        best = sorted(runs, key=lambda r: str(r.get("exit")))[0]
        note = f". {best['note']}" if best.get("note") else ""
        return "VERIFIED", f"ran `{best.get('argv')}` → exit {best.get('exit')}{note}"
    if not_run:
        return "NOT_RUN", str(not_run[0].get("not_run"))
    return "NOT_VERIFIED", "declared, never run"


# --------------------------------------------------------------------------
# compile
# --------------------------------------------------------------------------

def build_entries(paths: list[Path], evidence: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], list[str]]:
    """`(entries, problems)`.  A problem is a refusal, never a silent omission."""
    entries: list[dict[str, Any]] = []
    problems: list[str] = []
    seen: dict[str, Path] = {}
    for path in paths:
        rel = path.relative_to(ROOT.parent).as_posix()
        spec, detail = run_describe(path)
        if spec is None:
            # WHY an entry rather than a skip: an instrument that declares a
            # capability and then fails to load is the single most important
            # thing this register can tell you.  Dropping it would report the
            # toolbox as healthier than it is.
            problems.append(f"{rel}: {detail}")
            entries.append({
                "id": f"unloadable.{path.stem.replace('_', '-').replace('.', '-')}",
                "name": f"{path.name} (declaration unreadable)",
                "source_file": rel,
                "language": path.suffix.lstrip("."),
                "status": "BROKEN",
                "evidence": detail,
            })
            continue
        try:
            validate(spec, rel)
        except CapabilityInvalid as exc:
            problems.append(str(exc))
            continue
        ident = str(spec["id"])
        if ident in seen:
            problems.append(f"duplicate id {ident!r}: {rel} and {seen[ident].relative_to(ROOT.parent).as_posix()}")
            continue
        seen[ident] = path
        status, why = derive_status(spec, evidence.get(ident, []))
        entry = {k: v for k, v in spec.items() if k not in COMPILER_OWNED}
        entry["source_file"] = rel
        entry["language"] = path.suffix.lstrip(".")
        entry["status"] = status
        entry["evidence"] = why
        entries.append(entry)
    entries.sort(key=lambda e: str(e["id"]))
    return entries, problems


def register_payload(entries: list[dict[str, Any]]) -> str:
    """The register's bytes.

    No timestamp, on purpose — an unchanged toolbox must compile to identical
    bytes, or `--check` becomes noise and gets switched off.  Same reasoning as
    `benchmarks/index.json`.
    """
    counts: dict[str, int] = {}
    for e in entries:
        counts[str(e.get("status"))] = counts.get(str(e.get("status")), 0) + 1
    doc = {
        "_meta": {
            "generated_by": f"scripts/{TOOL} compile",
            "instrument_count": len(entries),
            "status_counts": dict(sorted(counts.items())),
            "note": ("GENERATED — do not edit. Declarations live in each instrument's "
                     "source file behind `--describe`. Edit there and recompile."),
        },
        "capabilities": entries,
    }
    return yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True, width=100)


def check_register(entries: list[dict[str, Any]], path: Path = REGISTER_PATH) -> tuple[bool, str]:
    """Does the persisted register still describe the instruments on disk?

    Never raises on a missing or corrupt register — both are disagreements.
    """
    want = register_payload(entries)
    if not path.exists():
        return False, (f"{path.name} does not exist. Generate it: "
                       f"python3 scripts/{TOOL} compile")
    have = path.read_text(encoding="utf-8")
    if have == want:
        return True, f"{path.name} agrees with {len(entries)} instrument(s) on disk"
    try:
        had = yaml.safe_load(have) or {}
        old = {str(e.get("id")): e for e in (had.get("capabilities") or [])}
    except yaml.YAMLError as exc:
        return False, f"{path.name} is not readable YAML ({exc}). Regenerate: python3 scripts/{TOOL} compile"
    new = {str(e.get("id")): e for e in entries}
    lines = [f"{path.name} disagrees with the instruments on disk:"]
    for ident in sorted(set(old) | set(new)):
        if ident not in old:
            lines.append(f"    + {ident} declared on disk, absent from the register")
        elif ident not in new:
            lines.append(f"    - {ident} in the register, no longer declared on disk")
        else:
            for field in sorted(set(old[ident]) | set(new[ident])):
                if old[ident].get(field) != new[ident].get(field):
                    lines.append(f"    ~ {ident}.{field} changed")
    lines.append(f"    regenerate: python3 scripts/{TOOL} compile")
    return False, "\n".join(lines)


# --------------------------------------------------------------------------
# scenarios — the part that makes the register usable
# --------------------------------------------------------------------------

def validate_scenarios(doc: Any, entries: list[dict[str, Any]]) -> list[str]:
    """Every problem with `scenarios.yaml`, against the register that exists.

    WHY THIS IS VALIDATED AND NOT MERELY WRITTEN
    A scenario naming a tool that does not exist is worse than no scenario: it
    sends an operator looking for an instrument, and when they cannot find it
    they build a worse one. That is the exact failure this register exists to
    prevent, so a dangling reference is a hard error.
    """
    known = {str(e["id"]): e for e in entries if e.get("id")}
    problems: list[str] = []
    if not isinstance(doc, dict):
        return [f"{SCENARIOS_PATH.name}: expected a mapping at the top level"]
    scenarios = doc.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return [f"{SCENARIOS_PATH.name}: `scenarios` must be a non-empty list"]

    seen: set[str] = set()
    for index, scenario in enumerate(scenarios):
        label = f"scenario[{index}]"
        if not isinstance(scenario, dict):
            problems.append(f"{label}: expected a mapping")
            continue
        label = str(scenario.get("id") or label)
        for field in SCENARIO_REQUIRED:
            if not scenario.get(field):
                problems.append(f"{label}: missing `{field}`")
        if scenario.get("id") in seen:
            problems.append(f"{label}: duplicate scenario id")
        seen.add(str(scenario.get("id")))

        steps = scenario.get("steps")
        if not isinstance(steps, list) or not steps:
            problems.append(f"{label}: `steps` must be a non-empty ordered list")
            continue
        for position, step in enumerate(steps, start=1):
            where = f"{label} step {position}"
            if not isinstance(step, dict):
                problems.append(f"{where}: expected a mapping")
                continue
            for field in SCENARIO_STEP_REQUIRED:
                value = step.get(field)
                if not isinstance(value, str) or not value.strip():
                    problems.append(f"{where}: `{field}` must be a non-empty string")
            capability = step.get("capability")
            if isinstance(capability, str) and capability not in known:
                problems.append(
                    f"{where}: capability {capability!r} is not in the register. "
                    f"A sequence may not name an instrument that does not exist"
                )
            elif isinstance(capability, str):
                status = str(known[capability].get("status"))
                if status == "BROKEN":
                    problems.append(
                        f"{where}: capability {capability!r} is BROKEN — a scenario "
                        f"may not route an operator to a tool known not to work"
                    )
    return problems


def check_scenarios(entries: list[dict[str, Any]], path: Path = SCENARIOS_PATH) -> tuple[bool, str]:
    """`(ok, detail)`. A missing scenarios file is NOT an error — the register is
    useful before the sequences are written. A malformed one is."""
    if not path.exists():
        return True, f"{path.name} not present (no scenarios declared)"
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return False, f"{path.name} is not readable YAML ({exc})"
    problems = validate_scenarios(doc, entries)
    if problems:
        return False, f"{path.name} is invalid:\n    - " + "\n    - ".join(problems)
    count = len(doc.get("scenarios") or [])
    steps = sum(len(s.get("steps") or []) for s in doc.get("scenarios") or [])
    return True, f"{path.name}: {count} scenario(s), {steps} step(s), every capability resolves"


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def _collect() -> tuple[list[dict[str, Any]], list[str], list[Path]]:
    paths = candidate_files()
    entries, problems = build_entries(paths, load_evidence())
    return entries, problems, paths


def cmd_compile(args: argparse.Namespace) -> int:
    entries, problems, paths = _collect()
    if not paths:
        print(f"NOT_MEASURED: no instrument declares a capability under "
              f"{', '.join(str(r) for r in SCAN_ROOTS)}", file=sys.stderr)
        return EXIT_NOT_MEASURED
    for p in problems:
        print(f"{TOOL}: REFUSED {p}", file=sys.stderr)

    if args.check:
        agrees, detail = check_register(entries)
        scen_ok, scen_detail = check_scenarios(entries)
        ok = agrees and scen_ok and not problems
        print(f"{TOOL}: {detail}", file=sys.stdout if agrees else sys.stderr)
        print(f"{TOOL}: {scen_detail}", file=sys.stdout if scen_ok else sys.stderr)
        if problems and agrees:
            print(f"{TOOL}: {len(problems)} declaration(s) refused", file=sys.stderr)
        return EXIT_OK if ok else EXIT_FAILED

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    REGISTER_PATH.write_text(register_payload(entries), encoding="utf-8")
    counts: dict[str, int] = {}
    for e in entries:
        counts[str(e["status"])] = counts.get(str(e["status"]), 0) + 1
    print(f"{TOOL}: wrote {REGISTER_PATH.relative_to(ROOT)}")
    print(f"  instruments  {len(entries)} from {len(paths)} declaring file(s)")
    for status in sorted(counts):
        print(f"  {status:<13}{counts[status]}")
    if problems:
        print(f"  REFUSED      {len(problems)} (see above) — not in the register")
        return EXIT_FAILED
    return EXIT_OK


def cmd_verify(args: argparse.Namespace) -> int:
    """Re-run `--describe` everywhere and record loadability as evidence.

    This is the cheapest true statement the register can make: the file loads.
    It is NOT a claim that the instrument works — that needs a real run, recorded
    with `record`.
    """
    paths = candidate_files()
    if not paths:
        print(f"NOT_MEASURED: nothing declares a capability", file=sys.stderr)
        return EXIT_NOT_MEASURED
    loaded = broken = 0
    for path in paths:
        rel = path.relative_to(ROOT.parent).as_posix()
        spec, detail = run_describe(path)
        if spec is None:
            broken += 1
            print(f"  BROKEN  {rel}: {detail}")
        else:
            loaded += 1
            print(f"  loads   {rel}  ({spec.get('id')})")
    print(f"{TOOL}: {loaded} loaded, {broken} broken, {len(paths)} declaring file(s)")
    return EXIT_FAILED if broken else EXIT_OK


def cmd_record(args: argparse.Namespace) -> int:
    if not args.not_run and (args.argv is None or args.exit is None):
        print(f"{TOOL}: record needs either --argv and --exit, or --not-run <reason>",
              file=sys.stderr)
        return EXIT_USAGE
    evidence = load_evidence()
    rec: dict[str, Any] = {"id": args.id}
    if args.not_run:
        rec["not_run"] = args.not_run
    else:
        rec["argv"] = args.argv
        rec["exit"] = args.exit
    if args.note:
        rec["note"] = args.note
    bucket = evidence.setdefault(args.id, [])
    # Replace an identical prior record rather than accumulating duplicates: the
    # evidence store is committed, and a re-run must be a no-op diff.
    key = (rec.get("argv"), rec.get("not_run"))
    bucket[:] = [r for r in bucket if (r.get("argv"), r.get("not_run")) != key]
    bucket.append(rec)
    save_evidence(evidence)
    print(f"{TOOL}: recorded {args.id} → "
          f"{'NOT_RUN: ' + args.not_run if args.not_run else 'exit ' + str(args.exit)}")
    print(f"  recompile to fold it in: python3 scripts/{TOOL} compile")
    return EXIT_OK


def cmd_scenarios(args: argparse.Namespace) -> int:
    """Answer "what should I run before X?" without reading orchestrate.py."""
    if not SCENARIOS_PATH.exists():
        print(f"NOT_MEASURED: {SCENARIOS_PATH.name} does not exist", file=sys.stderr)
        return EXIT_NOT_MEASURED
    entries, _problems, _paths = _collect()
    ok, detail = check_scenarios(entries)
    if args.check:
        print(f"{TOOL}: {detail}", file=sys.stdout if ok else sys.stderr)
        return EXIT_OK if ok else EXIT_FAILED
    if not ok:
        print(f"{TOOL}: {detail}", file=sys.stderr)
        return EXIT_FAILED

    by_id = {str(e["id"]): e for e in entries}
    doc = yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8")) or {}
    wanted = (args.question or "").lower()
    shown = 0
    for scenario in doc.get("scenarios") or []:
        text = f"{scenario.get('id')} {scenario.get('question')}".lower()
        if wanted and wanted not in text:
            continue
        shown += 1
        print(f"\n\"{scenario['question']}\"   [{scenario['id']}]")
        if scenario.get("note"):
            print(f"  {scenario['note']}")
        for position, step in enumerate(scenario["steps"], start=1):
            entry = by_id.get(step["capability"], {})
            print(f"\n  {position}. {entry.get('name', step['capability'])}"
                  f"   [{entry.get('status', '?')}]")
            print(f"     $ {entry.get('invocation', '—')}")
            print(f"     why      {step['why']}")
            print(f"     cost     {step['cost']}")
            print(f"     skipping {step['skipping_ships']}")
        for excluded in scenario.get("not_applicable") or []:
            print(f"\n  NOT APPLICABLE  {excluded.get('capability')}"
                  f"\n     {excluded.get('why')}")
    if not shown:
        print(f"NOT_MEASURED: no scenario matches {args.question!r}", file=sys.stderr)
        return EXIT_NOT_MEASURED
    print()
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    if not REGISTER_PATH.exists():
        print(f"NOT_MEASURED: {REGISTER_PATH.name} does not exist. "
              f"Generate it: python3 scripts/{TOOL} compile", file=sys.stderr)
        return EXIT_NOT_MEASURED
    doc = yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8")) or {}
    entries = doc.get("capabilities") or []
    if args.status:
        entries = [e for e in entries if str(e.get("status")) == args.status]
    for e in entries:
        print(f"{str(e.get('status')):<13}{str(e.get('id')):<40}{e.get('name')}")
        print(f"             {e.get('invocation', '—')}")
    print(f"{TOOL}: {len(entries)} instrument(s)"
          + (f" with status {args.status}" if args.status else ""))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog=TOOL,
        description="Compile the capability register from the instruments themselves.")
    sub = ap.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="compile the register from every declaration")
    p_compile.add_argument("--check", action="store_true",
                           help="do not write; exit 1 if the register disagrees with disk")
    p_compile.set_defaults(func=cmd_compile)

    p_verify = sub.add_parser("verify", help="re-run --describe everywhere; report what loads")
    p_verify.set_defaults(func=cmd_verify)

    p_record = sub.add_parser("record", help="record a real execution as evidence")
    p_record.add_argument("--id", required=True, help="capability id the run exercised")
    p_record.add_argument("--argv", help="the exact command line that was run")
    p_record.add_argument("--exit", type=int, help="the exit code it returned")
    p_record.add_argument("--not-run", help="reason this cannot be run (costs money, mutates a live store)")
    p_record.add_argument("--note", help="one line of context for a human")
    p_record.set_defaults(func=cmd_record)

    p_scen = sub.add_parser("scenarios", help="print or validate the scenario sequences")
    p_scen.add_argument("--check", action="store_true", help="validate only; print nothing on success")
    p_scen.add_argument("--question", help="substring match on a scenario's question or id")
    p_scen.set_defaults(func=cmd_scenarios)

    p_list = sub.add_parser("list", help="print the register")
    p_list.add_argument("--status", help="filter: VERIFIED | BROKEN | NOT_RUN | NOT_VERIFIED")
    p_list.set_defaults(func=cmd_list)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
