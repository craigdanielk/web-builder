#!/usr/bin/env python3
"""Thin driver: run `aurelix-uiux-audit/lib/design_conformance.py` over a URL list.

WHY THIS FILE EXISTS
--------------------
`design_conformance.py` is a library with three public functions, no `main()`,
no argparse and no exit codes (verified: `grep -n "argparse|__main__|sys.exit"`
returns nothing). Its only caller in the tree is the post-deploy audit. The
pre-deploy gate is `conformance-gate.js`, which serves the build and owns the
verdict; this file is the Python side of that call and does exactly two things:

    load_benchmark + extract_computed + evaluate   ->   JSON on stdout/--out

It deliberately makes NO judgement. It does not decide PASS/FAIL, it does not
filter rules, it does not reshape measurements. Every interpretation lives in
the gate, so there is one place where the verdict is defined. This is a driver,
not a fork.

Exit codes here are transport-level only (0 = the analyser ran; 3 = it could
not be run at all). The gate maps analyser output to the gate contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

# web-builder/scripts/quality/ -> web-builder/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = REPO_ROOT / "aurelix-uiux-audit"
WEB_BUILDER = Path(__file__).resolve().parents[2]

# The neighbours' idiom is `sys.path.insert(0, WEB_BUILDER / "scripts")` and
# `from lib.capability import describe`. Here that idiom BREAKS the file: this
# module later does `sys.path.insert(0, AUDIT_ROOT)` and imports
# `lib.design_conformance` from the AUDIT's `lib` package. Both trees have a
# top-level package named `lib`, and the first one imported wins for the rest of
# the process — importing `lib.capability` first left `lib.__path__` pointing at
# web-builder/scripts/lib, and the analyser import then failed with
# ModuleNotFoundError. Measured, not theorised.
#
# So: take the path, take the name, put both back. `describe` is the only thing
# this file needs, and it needs it before argparse runs.
sys.path.insert(0, str(WEB_BUILDER / "scripts"))
try:
    from lib.capability import describe                   # noqa: E402
finally:
    sys.path.pop(0)
    for _name in [n for n in sys.modules if n == "lib" or n.startswith("lib.")]:
        del sys.modules[_name]

# What this instrument is, in its own words. Compiled into the capability
# register by `scripts/capability_register.py`; see that file for why it lives
# here rather than in a separate document.
CAPABILITY = {
    "id": "aurelix.extractor.conformance-runner",
    "name": "Design-conformance analyser driver",
    "kind": "extractor",
    "invocation": (
        "python3 scripts/quality/conformance_runner.py --benchmark <file> "
        "--url <url> [--url <url> ...] --out <results.json> [--viewport 1440x900]"
    ),
    "preconditions": [
        "the aurelix-uiux-audit submodule is initialised at <repo-root>/aurelix-uiux-audit "
        "(an uninitialised checkout is a directory that exists and imports nothing)",
        "playwright importable inside that submodule, with a chromium browser installed",
        "every --url is already being served — this driver does not start a server; conformance-gate.js does",
        "a ratified benchmark file that load_benchmark() accepts",
    ],
    "inputs": ["a benchmark json", "one or more served route URLs"],
    "outputs": [
        "--out results json: {error, urls_requested, urls_reached, notes, results[]} "
        "where results[] are design_conformance RuleResults flattened to plain JSON"
    ],
    "outcome": (
        "the raw per-rule measured-vs-expected output of the audit's design_conformance "
        "analyser, and which of the requested URLs were actually reached"
    ),
    "exit_contract": {
        "0": "the analyser ran and its results were written. TRANSPORT-LEVEL only — 0 does not mean the rules passed, "
             "and does not even mean a URL was reached: a dead port also exits 0, with urls_reached empty",
        "3": "the analyser could not be run: submodule absent, import failed, benchmark unreadable, no URLs given, or no computed styles collected",
    },
    "measures": [
        "computed style of each served route, via the audit's extract_computed",
        "urls_reached vs urls_requested — a route that failed to load is visible as an absence, not silently folded in",
    ],
    "cannot_see": [
        "PASS or FAIL. By design it renders no verdict, filters no rules and reshapes no measurement — "
        "conformance-gate.js owns the interpretation so there is exactly one place the verdict is defined",
        "WHERE an offence is: evaluate() flattens measured['per_page'] into one aggregate and stamps "
        "pages[0] onto every evidence record, so the URL on a result is 'the first page', not the offending page",
        "that nothing was reached. Measured 2026-08-18 against a dead port: it exits 0 with error=None, "
        "urls_reached=[] and 10 results of which some read PASS. The only honest signal is the EMPTY "
        "urls_reached and a 'conformance skip <url>' line in notes — a caller reading the exit code, "
        "or the results' states, learns that an unserved site conforms",
        "source-level tokens: it reads rendered computed style, never a template or a compiled globals.css",
        "any route it was not handed a --url for; it discovers nothing",
    ],
    "reachable_from": ["scripts/quality/conformance-gate.js:379 (spawnSync)", "standalone CLI"],
    "cost": "a few seconds per URL, all of it inside the audit's playwright extraction; no build, no deploy",
}


def _jsonable(value):
    """RuleResult / EvidenceRecord / RuleState -> plain JSON."""
    if is_dataclass(value):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if hasattr(value, "value") and type(value).__name__ in ("RuleState", "EvidenceSource",
                                                            "Reproducibility"):
        return value.value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def main(argv: list[str] | None = None) -> int:
    if describe(CAPABILITY, argv):
        return 0
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--url", action="append", default=[],
                    help="repeatable; one served route URL per flag")
    ap.add_argument("--out", required=True, help="where to write the results JSON")
    ap.add_argument("--viewport", default="1440x900")
    args = ap.parse_args(argv)

    out = Path(args.out)

    def emit(payload: dict, code: int) -> int:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return code

    if not AUDIT_ROOT.is_dir():
        return emit({"error": f"aurelix-uiux-audit not present at {AUDIT_ROOT}",
                     "results": []}, 3)
    sys.path.insert(0, str(AUDIT_ROOT))
    try:
        from lib.design_conformance import evaluate, extract_computed, load_benchmark
    except Exception as exc:  # noqa: BLE001
        return emit({"error": f"cannot import design_conformance: "
                              f"{type(exc).__name__}: {exc}", "results": []}, 3)

    try:
        benchmark = load_benchmark(args.benchmark)
    except Exception as exc:  # noqa: BLE001
        return emit({"error": f"benchmark unreadable ({args.benchmark}): "
                              f"{type(exc).__name__}: {exc}", "results": []}, 3)

    if not args.url:
        return emit({"error": "no URLs to measure", "results": []}, 3)

    w, _, h = args.viewport.partition("x")
    skipped: list[str] = []
    measured = extract_computed(args.url, viewport=(int(w), int(h)),
                                progress=lambda line: skipped.append(line.strip())
                                if "skip" in line else None)
    if not measured:
        # extract_computed returns {} only when Playwright is not importable.
        return emit({"error": "Playwright unavailable — no computed styles collected",
                     "results": []}, 3)

    reached = sorted(measured.get("per_page", {}).keys())
    results = [_jsonable(r) for r in evaluate(benchmark, measured, args.url)]
    return emit({"error": None,
                 "urls_requested": list(args.url),
                 "urls_reached": reached,
                 "notes": [s for s in skipped if s],
                 "results": results}, 0)


if __name__ == "__main__":
    sys.exit(main())
