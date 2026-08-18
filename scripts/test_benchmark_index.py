#!/usr/bin/env python3
"""Invariants for the benchmark library's generated index.

THE POINT OF THIS FILE
A stale index is worse than no index: it answers confidently and wrongly. The
load-bearing test here is `the persisted index agrees with the files on disk` —
it runs against the REAL `benchmarks/` directory, so adding, ratifying or
renaming a benchmark without regenerating the index turns the suite red rather
than shipping a map of a library that no longer exists.

Everything else is synthetic and local. No network, no Supabase.

Run: python3 scripts/test_benchmark_index.py     (exit 0 = green)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib.benchmark_gate import (  # noqa: E402
    INDEX_FILENAME,
    build_index,
    check_index,
    index_payload,
    library_index,
    match_library,
)

WEB_BUILDER = HERE.parent
REAL_BENCHMARKS = WEB_BUILDER / "benchmarks"
CLI = HERE / "benchmark_library.py"

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f"\n         {detail}" if detail else ""))


def _bench(market, *, aliases=None, ratified=True, captured_at="2026-08-18"):
    """A minimal file that `classify` reads. Not load-valid, and need not be:
    these tests are about identity and the index, not about compiling style."""
    meta = {"market": market, "captured_at": captured_at,
            "ratified": bool(ratified)}
    if aliases:
        meta["aliases"] = aliases
    return {
        "_meta": meta,
        # the four operator fields, so `classify` does not call it unratified
        "palette_roles": {"accent": "#004e89", "on_accent": "#ffffff"},
        "density": "spacious",
        "motion": {"intensity": "expressive"},
    }


def _lib(root: Path, files: dict[str, dict]) -> Path:
    d = root / "benchmarks"
    d.mkdir(parents=True, exist_ok=True)
    for slug, data in files.items():
        (d / f"{slug}.json").write_text(json.dumps(data, indent=2),
                                        encoding="utf-8")
    return d


tmp = Path(tempfile.mkdtemp(prefix="benchmark-index-test-"))
try:
    # ── 1. the real library ──────────────────────────────────────────────────
    print("\n1. the persisted index agrees with the files on disk")
    agrees, detail = check_index(REAL_BENCHMARKS)
    test("benchmarks/index.json is not stale", agrees, detail)
    test("the index is a generated artifact and says so",
         "do not hand-edit" in json.loads(
             (REAL_BENCHMARKS / INDEX_FILENAME).read_text())["_meta"]["note"])
    real = json.loads((REAL_BENCHMARKS / INDEX_FILENAME).read_text())
    test("every indexed market names a file that exists",
         all((REAL_BENCHMARKS / row["file"]).exists()
             for row in real["markets"].values()),
         json.dumps([r["file"] for r in real["markets"].values()]))
    test("no two files claim one market",
         real["collisions"] == [], json.dumps(real["collisions"]))
    test("the index does not index itself",
         INDEX_FILENAME not in {r["file"] for r in real["markets"].values()})

    # ── 2. determinism ───────────────────────────────────────────────────────
    print("\n2. determinism — no clock, stable ordering")
    test("two builds of an unchanged library are identical bytes",
         index_payload(REAL_BENCHMARKS) == index_payload(REAL_BENCHMARKS))
    # Assert on KEYS, not on a substring of the whole document: `_meta.note`
    # contains the word "timestamp" precisely because it explains the absence
    # of one, and a substring check made that self-defeating.
    def _keys(o, acc):
        if isinstance(o, dict):
            for k, v in o.items():
                acc.add(k)
                _keys(v, acc)
        elif isinstance(o, list):
            for v in o:
                _keys(v, acc)
        return acc
    ks = _keys(build_index(REAL_BENCHMARKS), set())
    test("no clock-derived key exists in the index",
         not (ks & {"generated_at", "timestamp", "built_at", "indexed_at"}),
         json.dumps(sorted(ks)))
    test("markets are sorted",
         list(real["markets"]) == sorted(real["markets"]))
    test("aliases are sorted",
         list(real["aliases"]) == sorted(real["aliases"]))

    # ── 3. resolution precedence ─────────────────────────────────────────────
    print("\n3. market identity first, alias next, filename last")
    r3 = tmp / "prec"
    d3 = _lib(r3, {
        "named-after-the-site": _bench("the-real-market",
                                       aliases=["legacy-handle"]),
    })
    idx3 = library_index(d3)
    m = match_library(idx3, ["the-real-market"])
    test("resolves by _meta.market",
         len(m) == 1 and m[0]["matched_by"] == "_meta.market",
         json.dumps([(x["slug"], x["matched_by"]) for x in m]))
    m = match_library(idx3, ["legacy-handle"])
    test("resolves by a declared alias",
         len(m) == 1 and m[0]["matched_by"] == "_meta.aliases",
         json.dumps([(x["slug"], x["matched_by"]) for x in m]))
    m = match_library(idx3, ["named-after-the-site"])
    test("resolves by filename, for back-compat",
         len(m) == 1 and m[0]["matched_by"] == "filename",
         json.dumps([(x["slug"], x["matched_by"]) for x in m]))
    # The precedence must be RULE-major. Keyed the other way round, the caller's
    # incidental key ordering would decide which rule fired.
    m = match_library(idx3, ["named-after-the-site", "the-real-market"])
    test("the strongest rule wins regardless of key order",
         len(m) == 1 and m[0]["matched_by"] == "_meta.market",
         json.dumps([(x["slug"], x["matched_by"]) for x in m]))
    test("an unmatched key resolves to nothing, never to a nearest neighbour",
         match_library(idx3, ["the-real-marketplace"]) == [])

    # ── 4. the index records what the gate will refuse ───────────────────────
    print("\n4. two files claiming one market is recorded, not silently merged")
    r4 = tmp / "collide"
    d4 = _lib(r4, {"a": _bench("shared-market"), "b": _bench("shared-market")})
    ix4 = build_index(d4)
    test("the collision is recorded with both files",
         (len(ix4["collisions"]) == 1
          and ix4["collisions"][0]["files"] == ["a.json", "b.json"]),
         json.dumps(ix4["collisions"]))
    test("...and the gate refuses that market for ambiguity",
         len(match_library(library_index(d4), ["shared-market"])) == 2)

    # ── 5. the stale-index guard actually catches drift ──────────────────────
    print("\n5. --check catches every kind of drift")
    r5 = tmp / "drift"
    d5 = _lib(r5, {"one": _bench("market-one")})
    (d5 / INDEX_FILENAME).write_text(index_payload(d5), encoding="utf-8")
    test("a freshly generated index agrees", check_index(d5)[0])

    _lib(r5, {"two": _bench("market-two")})
    ok, why = check_index(d5)
    test("a NEW benchmark makes the index disagree", not ok, why)
    test("...and the disagreement names the market",
         "market-two" in why, why)

    (d5 / INDEX_FILENAME).write_text(index_payload(d5), encoding="utf-8")
    edited = json.loads((d5 / "one.json").read_text())
    edited["_meta"]["captured_at"] = "1999-01-01"
    (d5 / "one.json").write_text(json.dumps(edited, indent=2), encoding="utf-8")
    ok, why = check_index(d5)
    test("an EDITED benchmark makes the index disagree", not ok, why)
    test("...and the disagreement names the field that moved",
         "captured_at" in why, why)

    (d5 / INDEX_FILENAME).unlink()
    ok, why = check_index(d5)
    test("a MISSING index is a disagreement, not a crash",
         not ok and "does not exist" in why, why)
    (d5 / INDEX_FILENAME).write_text("{ not json", encoding="utf-8")
    ok, why = check_index(d5)
    test("a CORRUPT index is a disagreement, not a crash", not ok, why)

    # ── 6. the CLI's exit codes ──────────────────────────────────────────────
    print("\n6. the CLI honours the exit-code contract")
    r = subprocess.run([sys.executable, str(CLI), "index", "--check"],
                       capture_output=True, text=True, cwd=str(WEB_BUILDER))
    test("--check on an agreeing library exits 0", r.returncode == 0,
         (r.stdout + r.stderr).strip())
    r = subprocess.run([sys.executable, str(CLI), "index", "--check",
                        "--nonsense"], capture_output=True, text=True,
                       cwd=str(WEB_BUILDER))
    test("an unknown flag exits 2 (argparse), not 0", r.returncode != 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
