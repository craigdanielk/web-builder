#!/usr/bin/env python3
"""The library's evidence test: every measured number must be re-derivable.

WHY THIS IS THE LOAD-BEARING TEST OF THE WHOLE LIBRARY
A benchmark is a pile of numbers asserted about a market. Without the capture
corpus it was compiled from, there is no way to check any of them, and no way
to recompile when the compiler improves — B1's census had to reconstruct how the
ratified BVNK file was produced by git archaeology precisely because both prior
corpora were written into session scratchpads and died there.

So: a benchmark that names a corpus must name one that EXISTS, and recompiling
that corpus must reproduce the benchmark's measured fields byte-identically. If
that holds, every number in the file is evidence rather than assertion.

WHAT IS EXCLUDED FROM THE COMPARISON, AND WHY
The commissioner cannot emit the operator-declared half — that is the entire
point of ratification — so those fields are excluded EXPLICITLY, by name, and
the exclusion list is asserted to be exactly `RATIFY_FIELDS` plus the
ratification bookkeeping. Excluding anything else would let a hand edit hide
inside the exemption.

    palette_roles.accent      declared: tenant identity, never measurable
    palette_roles.on_accent   declared: derived from the accent
    density                   declared: no code path emits "spacious"
    motion.intensity          declared at ratification
    _meta.ratified            written by ratify()
    _meta.ratification        written by ratify()
    _meta.aliases             a library-identity declaration, not a measurement
    _unmeasured               ratify() removes what the operator has declared

BENCHMARKS WITH NO CORPUS
Three files predate corpus persistence and their corpora are gone. They declare
`corpus: null` with a reason. They are NOT silently skipped: the test asserts
each carries an explicit reason, so "no corpus" is a recorded state rather than
an absent one. A benchmark that names no corpus AND gives no reason fails.

Run: python3 scripts/test_benchmark_corpus.py     (exit 0 = green)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB_BUILDER = HERE.parent
sys.path.insert(0, str(HERE))

from lib.benchmark_gate import RATIFY_FIELDS, library_index  # noqa: E402

BENCHMARKS = WEB_BUILDER / "benchmarks"
COMMISSIONER = HERE / "commission_benchmark.py"

#: Exactly the operator-declared half plus ratification bookkeeping. Asserted
#: below to be derived from RATIFY_FIELDS, not hand-listed.
EXCLUDED_META = ("ratified", "ratification", "aliases")
EXCLUDED_TOP = ("_unmeasured",)

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


def _prune(path, data):
    cur = data
    for key in path[:-1]:
        if not isinstance(cur, dict):
            return
        cur = cur.get(key)
    if isinstance(cur, dict):
        cur.pop(path[-1], None)


def measured_half(benchmark: dict) -> dict:
    """The benchmark minus everything an operator declared."""
    out = json.loads(json.dumps(benchmark))
    for f in RATIFY_FIELDS:
        _prune(f.path, out)
    for k in EXCLUDED_META:
        (out.get("_meta") or {}).pop(k, None)
    for k in EXCLUDED_TOP:
        out.pop(k, None)
    return out


print("\n0. the exclusion list is derived, not hand-maintained")
test("the excluded value fields are exactly RATIFY_FIELDS",
     {f.dotted for f in RATIFY_FIELDS}
     == {"palette_roles.accent", "palette_roles.on_accent", "density",
         "motion.intensity"},
     json.dumps(sorted(f.dotted for f in RATIFY_FIELDS)))

index = library_index(BENCHMARKS)
test("the library is non-empty", len(index) >= 1, str(len(index)))

with_corpus = []
without_corpus = []
for entry in index:
    data = json.loads((BENCHMARKS / entry["path"]).read_text(encoding="utf-8"))
    (with_corpus if data["_meta"].get("corpus") else without_corpus).append(
        (entry, data))

print("\n1. a benchmark with no corpus says so, and says why")
for entry, data in without_corpus:
    meta = data["_meta"]
    test(f"{entry['slug']}: declares corpus: null explicitly",
         "corpus" in meta and meta["corpus"] is None, json.dumps(meta.get("corpus")))
    test(f"{entry['slug']}: records WHY there is no corpus",
         bool((meta.get("corpus_absent_reason") or "").strip()),
         meta.get("corpus_absent_reason"))
    test(f"{entry['slug']}: records that its numbers are not replayable",
         "not re-derivable" in (meta.get("corpus_absent_reason") or "")
         or "no evidence" in (meta.get("corpus_absent_consequence") or ""),
         meta.get("corpus_absent_consequence"))

print("\n2. a benchmark that names a corpus names one that exists")
test("at least one benchmark in the library is backed by a corpus",
     len(with_corpus) >= 1,
     f"{len(with_corpus)} with, {len(without_corpus)} without")
for entry, data in with_corpus:
    corpus = WEB_BUILDER / data["_meta"]["corpus"]
    test(f"{entry['slug']}: the corpus directory exists", corpus.is_dir(),
         str(corpus))
    test(f"{entry['slug']}: the corpus carries an index.json",
         (corpus / "index.json").exists())
    pages = json.loads((corpus / "index.json").read_text(encoding="utf-8"))
    test(f"{entry['slug']}: every indexed page has an extraction.json",
         all((corpus / p["slug"] / "extraction.json").exists()
             for p in pages if p.get("ok")),
         json.dumps([p["slug"] for p in pages]))
    test(f"{entry['slug']}: the corpus covers every URL in _meta.captured_from",
         sorted(p["url"] for p in pages if p.get("ok"))
         == sorted(data["_meta"]["captured_from"]),
         json.dumps(sorted(p["url"] for p in pages if p.get("ok"))))

print("\n3. re-compiling the corpus reproduces the measured half, byte for byte")
tmp = Path(tempfile.mkdtemp(prefix="benchmark-corpus-test-"))
try:
    for entry, data in with_corpus:
        meta = data["_meta"]
        out = tmp / f"{entry['slug']}.json"
        # Every argument is read from the benchmark itself: the file describes
        # how to reproduce it. Nothing is supplied by this test that the file
        # does not already declare.
        base = [sys.executable, str(COMMISSIONER),
                str(WEB_BUILDER / meta["corpus"]),
                "--market", meta["market"],
                "--captured-at", meta["captured_at"]]
        if meta.get("reference_host"):
            base += ["--reference-host", meta["reference_host"]]
        cmd = base + ["--out", str(out)]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           cwd=str(WEB_BUILDER))
        test(f"{entry['slug']}: the recorded command still exits 0",
             r.returncode == 0, (r.stderr or r.stdout).strip()[:400])
        if r.returncode != 0:
            continue
        fresh = measured_half(json.loads(out.read_text(encoding="utf-8")))
        shipped = measured_half(data)
        same = (json.dumps(fresh, sort_keys=True)
                == json.dumps(shipped, sort_keys=True))
        detail = ""
        if not same:
            diffs = []

            def walk(a, b, p=""):
                if isinstance(a, dict) and isinstance(b, dict):
                    for k in sorted(set(a) | set(b)):
                        walk(a.get(k), b.get(k), f"{p}.{k}" if p else k)
                elif a != b:
                    diffs.append(f"{p}: shipped={b!r} fresh={a!r}")
            walk(fresh, shipped)
            detail = "\n         ".join(diffs[:12])
        test(f"{entry['slug']}: recompiles to the shipped measured half", same,
             detail)

        # Determinism: the same corpus twice, the same bytes.
        out2 = tmp / f"{entry['slug']}-2.json"
        r2 = subprocess.run(base + ["--out", str(out2)], capture_output=True,
                            text=True, cwd=str(WEB_BUILDER))
        test(f"{entry['slug']}: two compiles of one corpus are identical bytes",
             r2.returncode == 0 and out2.exists()
             and out.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8"),
             (r2.stderr or "").strip()[:200])

        # The operator half really is absent from a fresh compile — proving the
        # exclusions above are exemptions the commissioner needs, not cover.
        raw = json.loads(out.read_text(encoding="utf-8"))
        absent = [f.dotted for f in RATIFY_FIELDS
                  if f.dotted in {u["field"] for u in raw.get("_unmeasured", [])}]
        test(f"{entry['slug']}: the excluded fields are excluded because the "
             f"commissioner refuses to invent them",
             sorted(absent) == sorted(f.dotted for f in RATIFY_FIELDS
                                      if f.dotted != "motion.intensity"),
             json.dumps({"named_unmeasured": absent}))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
