#!/usr/bin/env python3
"""The benchmark library's own command line.

WHY THIS EXISTS
---------------
`lib/benchmark_gate.py` owns ratification, and its flags are registered onto
`orchestrate.py`'s parser (`orchestrate.py:10592`). That is the only place they
exist, so **ratifying a benchmark required running a build** — a design act
gated behind a compile. The library is meant to be the durable half of this
system: corpora and benchmarks accumulate, and the build consumes them. It
needs a surface of its own.

This command does NOT reimplement the gate. `ratify` calls
`benchmark_gate.resolve_benchmark(..., do_ratify=True)` and returns its verdict;
every refusal, every validation rule and the exit-code contract are the gate's.

EXIT CODES — the same three-state contract as every other gate here
    0   the act succeeded
    3   NOT_MEASURED — the gate refused; nothing was written
    64  usage error

USAGE
    python3 scripts/benchmark_library.py ratify <slug> \\
        --ratified-at YYYY-MM-DD \\
        --ratify-accent '#004e89' --ratify-on-accent '#ffffff' \\
        --ratify-density spacious --ratify-motion-intensity expressive
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib.benchmark_gate import (  # noqa: E402
    EXIT_NOT_MEASURED,
    BenchmarkNotMeasured,
    BenchmarkUsage,
    add_arguments,
    collect_ratify_values,
    resolve_benchmark,
)

ROOT = HERE.parent
EXIT_OK = 0
EXIT_USAGE = 64
TOOL = "benchmark_library.py"


def cmd_ratify(args: argparse.Namespace) -> int:
    try:
        record = resolve_benchmark(
            root=ROOT,
            benchmark_flag=args.slug,
            do_ratify=True,
            ratified_at=args.ratified_at,
            ratify_values=collect_ratify_values(args),
            interactive=False,
            write=lambda s: sys.stdout.write(s),
        )
    except BenchmarkUsage as exc:
        print(f"{TOOL}: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except BenchmarkNotMeasured as exc:
        print(f"NOT_MEASURED: {exc.message}", file=sys.stderr)
        print(f"{TOOL}: nothing ratified.", file=sys.stderr)
        return EXIT_NOT_MEASURED
    print(f"{TOOL}: {record['benchmark']} — {record['gate']} "
          f"(ratification: {record['ratification']})")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog=TOOL,
        description="Operate the benchmark library without running a build.")
    sub = ap.add_subparsers(dest="command", required=True)

    p_ratify = sub.add_parser(
        "ratify",
        help="ratify a library benchmark by declaring the fields no tool can "
             "measure. Delegates to lib/benchmark_gate.resolve_benchmark.")
    p_ratify.add_argument("slug", help="benchmark slug (benchmarks/<slug>.json)")
    # The gate's own flags, registered from the gate, so this command cannot
    # drift from what a build accepts. `--reference-url` and
    # `--benchmark-captured-at` come along; commissioning is
    # commission_benchmark.py's job and they are not wired here.
    add_arguments(p_ratify)
    p_ratify.set_defaults(func=cmd_ratify)

    args = ap.parse_args(argv)
    if getattr(args, "reference_url", None):
        print(f"{TOOL}: --reference-url is not accepted here. Commission with "
              f"scripts/commission_benchmark.py, then ratify the product.",
              file=sys.stderr)
        return EXIT_USAGE
    if not args.ratified_at:
        print(f"{TOOL}: ratify requires --ratified-at YYYY-MM-DD. A "
              f"ratification with no date is not a record of an operator act.",
              file=sys.stderr)
        return EXIT_USAGE
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
