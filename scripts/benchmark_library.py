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
    INDEX_FILENAME,
    BenchmarkNotMeasured,
    BenchmarkUsage,
    add_arguments,
    check_index,
    collect_ratify_values,
    index_payload,
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


def cmd_index(args: argparse.Namespace) -> int:
    benchmarks = ROOT / "benchmarks"
    if not benchmarks.is_dir():
        print(f"NOT_MEASURED: {benchmarks} does not exist; there is no library "
              f"to index.", file=sys.stderr)
        return EXIT_NOT_MEASURED
    if args.check:
        agrees, detail = check_index(benchmarks)
        print(f"{TOOL}: {detail}", file=sys.stdout if agrees else sys.stderr)
        return EXIT_OK if agrees else 1
    path = benchmarks / INDEX_FILENAME
    path.write_text(index_payload(benchmarks), encoding="utf-8")
    import json as _json
    data = _json.loads(path.read_text(encoding="utf-8"))
    print(f"{TOOL}: wrote {path.relative_to(ROOT)}")
    print(f"  markets   {data['_meta']['market_count']} "
          f"({data['_meta']['file_count']} file(s))")
    print(f"  aliases   {len(data['aliases'])}")
    if data["collisions"]:
        # Not a failure of the index — a failure the index now makes visible.
        print(f"  COLLISIONS {len(data['collisions'])}: two files claim one "
              f"market; the gate will refuse it for ambiguity")
        for c in data["collisions"]:
            print(f"    {c['market']}: {', '.join(c['files'])}")
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

    p_index = sub.add_parser(
        "index",
        help="regenerate benchmarks/index.json from the files on disk.")
    p_index.add_argument(
        "--check", action="store_true",
        help="do not write; exit 1 if the persisted index disagrees with the "
             "files on disk. A stale index answers confidently and wrongly.")
    p_index.set_defaults(func=cmd_index)

    args = ap.parse_args(argv)
    if args.command == "index":
        return args.func(args)
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
