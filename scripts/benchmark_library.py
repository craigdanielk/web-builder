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

from lib.capability import describe  # noqa: E402
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

# What this instrument is, in its own words. Compiled into the capability
# register by `scripts/capability_register.py`; see that file for why it lives here.
CAPABILITY = {
    "id": "aurelix.compiler.benchmark-library",
    "name": "Benchmark library CLI — index the library, ratify a benchmark",
    "kind": "compiler",
    "invocation": "python3 scripts/benchmark_library.py index [--check] | "
                  "python3 scripts/benchmark_library.py ratify <slug> --ratified-at YYYY-MM-DD "
                  "--ratify-accent <hex> --ratify-on-accent <hex> --ratify-density <d> "
                  "--ratify-motion-intensity <i>",
    "preconditions": [
        "benchmarks/ exists and holds the benchmark JSON files",
        "for ratify: the named benchmarks/<slug>.json exists, and the operator supplies the "
        "four fields no tool can measure (accent, on_accent, density, motion.intensity)",
        "for ratify: --ratified-at is mandatory — a ratification with no date is not a record "
        "of an operator act",
    ],
    "inputs": [
        "benchmarks/*.json — each file's declared market identity and aliases",
        "benchmarks/index.json when --check compares it against those files",
    ],
    "outputs": [
        "benchmarks/index.json (index, without --check) — GENERATED, timestamp-free so an "
        "unchanged library recompiles to identical bytes",
        "the ratified benchmark file's _meta.ratification block (ratify), written by "
        "lib/benchmark_gate.resolve_benchmark",
    ],
    "outcome": "index: whether the persisted index still agrees with the files on disk, plus "
               "any market claimed by two files. ratify: whether an operator declaration was "
               "recorded, or the gate's refusal",
    "exit_contract": {
        0: "the act succeeded — index written, index agrees under --check, or the benchmark ratified",
        1: "index --check only: the persisted index disagrees with the files on disk. "
           "NOTE the module docstring omits this code; the code (cmd_index) returns it",
        3: "NOT_MEASURED — benchmarks/ does not exist, or the ratification gate refused and "
           "nothing was written",
        64: "usage — ratify without --ratified-at, or --reference-url passed here instead of "
            "to scripts/commission_benchmark.py",
    },
    "measures": [
        "the market identity each benchmark file declares, and its filename alias",
        "collisions: two files claiming one market, which the gate then refuses for ambiguity",
        "whether benchmarks/index.json is byte-identical to what the files on disk imply",
        "whether the four unmeasurable ratification fields have been declared by an operator",
    ],
    "cannot_see": [
        "whether a benchmark's NUMBERS are right. It indexes and ratifies identity and "
        "declarations; enterprise-payments-bvnk carries basis 'inference' and corpus null, so "
        "its measured half is not re-derivable and this tool cannot tell you that by looking",
        "whether the corpus a benchmark claims to be compiled from still reproduces it — that "
        "is scripts/test_benchmark_corpus.py, a separate instrument",
        "who actually ratified: --ratified-by is free text and is never authenticated",
        "which tenants or builds depend on the benchmark it is about to overwrite — ratify "
        "mutates a file that live builds read",
        "a benchmark file that is malformed but uniquely named: index reads identity, not the "
        "loader's eight palette_roles / four rhythm / four type_scale requirements",
    ],
    "reachable_from": [
        "scripts/lib/benchmark_gate.py:281,366-423 — every refusal and the generated index "
        "name this command as the remedy; no code path executes it",
        "scripts/test_benchmark_index.py:38 (runs the CLI)",
        "standalone CLI",
    ],
    "cost": "index: under a second over a four-market library, no network, no database. "
            "ratify: sub-second, but it WRITES a tracked benchmark file",
}


def cmd_ratify(args: argparse.Namespace) -> int:
    try:
        record = resolve_benchmark(
            root=ROOT,
            benchmark_flag=args.slug,
            do_ratify=True,
            ratified_at=args.ratified_at,
            ratified_by=getattr(args, "ratified_by", None),
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
    # Before parse_args: the subparser is required=True, so `--describe` alone
    # would die on a usage error rather than describe.
    if describe(CAPABILITY, argv):
        return EXIT_OK
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
