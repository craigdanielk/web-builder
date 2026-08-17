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
