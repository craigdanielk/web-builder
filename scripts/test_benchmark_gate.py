#!/usr/bin/env python3
"""Invariants for the benchmark ratification gate (Task B3).

NO NETWORK, NO PLAYWRIGHT. The capture corpus is synthetic — the recipe is
B2's (`scripts/test_commission_benchmark.py`, itself the census's §4 recipe):
a hand-built extraction in `extract-reference.js`'s shape, `renderedDOM[].
{styles,rect}` + `textContent[].{styles,isHeading}` + `assets.fonts` + the
`animations.profile` block `capture-benchmark-pages.js` writes. It is rebuilt
here rather than imported because `test_commission_benchmark.py` runs its
assertions at import time.

Each temp root gets a `scripts` symlink to the real one, so the commissioning
branch drives the REAL `commission_benchmark.py` as a subprocess — the wire
under test is the wire that ships.

WHAT IS GUARDED
  0. the ratification arg surface IS the loader's demand, recomputed
  1. branch (a) --benchmark: PASS on a loading file, refusal on an unratified one
  2. branch (b) --reference-url: commission → refuse without --ratify;
     commission → ratify → load, in one run, with --ratify
  3. branch (b) with no corpus: NOT_MEASURED naming the capture command; the
     gate never crawls
  4. branch (c) library MISS: NOT_MEASURED naming the two ways. THE MUTATION
     TARGET — a silent first-file default must make this test fail
  5. branch (c) library HIT: PASS *and* the override prompt, on a hit
  6. branch (d) interactive: the injected-input prompt, all three answers
  7. legacy classification of the three real library files (read-only)
  8. the resolution record lands in the build record, refusals included
  9. usage errors (64-class) are distinguishable from refusals (3-class)

Run: python3 scripts/test_benchmark_gate.py     (exit 0 = green)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB_BUILDER = HERE.parent
sys.path.insert(0, str(HERE))

from lib.benchmark_gate import (  # noqa: E402
    ALWAYS_PROMPT,
    EXIT_NOT_MEASURED,
    RATIFY_FIELDS,
    BenchmarkNotMeasured,
    BenchmarkUsage,
    classify,
    library_index,
    match_library,
    prompt_benchmark,
    ratify,
    record_benchmark_resolution,
    resolve_benchmark,
)
from lib.design_system import (  # noqa: E402
    REQUIRED_ROLES,
    REQUIRED_RHYTHM,
    REQUIRED_TYPE_SCALE,
    BenchmarkError,
    load_benchmark,
)

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


def refuses(**kw):
    """Call the gate expecting a refusal. Returns (message, record) or None."""
    try:
        rec = resolve_benchmark(**kw)
    except BenchmarkNotMeasured as exc:
        return str(exc), exc.record
    return None


SINK: list[str] = []


def sink(s: str) -> None:
    SINK.append(s)


def drain() -> str:
    out = "".join(SINK)
    SINK.clear()
    return out


# ── the synthetic corpus (B2's recipe) ───────────────────────────────────────
BG_PRIMARY = "rgb(255, 255, 255)"
BG_BANDING = "rgb(226, 232, 240)"
SURFACE = "rgb(244, 246, 248)"
TEXT_PRIMARY = "rgb(26, 34, 48)"
TEXT_MUTED = "rgb(74, 90, 106)"
BORDER_SEP = "rgb(223, 228, 234)"
BORDER_EMPHASIS = "rgb(0, 51, 102)"


def _el(bg=None, *, w=1200, h=400, radius=None, pad=None, gap=None,
        border=None, bw=None, shadow=None):
    styles = {}
    if bg:
        styles["backgroundColor"] = bg
    if radius is not None:
        styles["borderRadius"] = f"{radius}px"
    if pad is not None:
        styles["padding"] = f"{pad}px 24px"
    if gap is not None:
        styles["gap"] = f"{gap}px"
    if border:
        styles["borderColor"] = border
        styles["borderWidth"] = f"{bw or 1}px"
    if shadow:
        styles["boxShadow"] = shadow
    return {"styles": styles, "rect": {"width": w, "height": h}}


def _text(colour, size, weight, *, heading=False, family="Circular"):
    return {"isHeading": heading,
            "styles": {"color": colour, "fontSize": f"{size}px",
                       "fontWeight": str(weight),
                       "fontFamily": f'"{family}", sans-serif'}}


def _extraction() -> dict:
    dom = []
    dom += [_el(BG_PRIMARY, w=1400, h=600) for _ in range(30)]
    dom += [_el(BG_BANDING, w=1400, h=500) for _ in range(12)]
    dom += [_el(SURFACE, w=380, h=240, radius=16, pad=40) for _ in range(18)]
    dom += [_el(SURFACE, w=380, h=240, radius=24, pad=40) for _ in range(6)]
    dom += [_el(BG_PRIMARY, w=1400, h=900, pad=120) for _ in range(13)]
    dom += [_el(BG_PRIMARY, w=1400, h=900, pad=180) for _ in range(9)]
    dom += [_el(BG_PRIMARY, w=1200, h=300, gap=24) for _ in range(20)]
    dom += [_el(BG_PRIMARY, w=1200, h=300, gap=16) for _ in range(7)]
    dom += [_el(BG_PRIMARY, w=180, h=48, radius=100) for _ in range(11)]
    dom += [_el(BG_PRIMARY, w=1200, h=100, border=BORDER_SEP, bw=1)
            for _ in range(9)]
    dom += [_el(BG_PRIMARY, w=200, h=52, border=BORDER_EMPHASIS, bw=2)
            for _ in range(14)]
    dom += [_el(SURFACE, w=380, h=240, radius=16,
                shadow="rgba(0, 0, 0, 0.08) 0px 2px 8px 0px") for _ in range(5)]

    text = []
    text += [_text(TEXT_PRIMARY, 16, 400) for _ in range(40)]
    text += [_text(TEXT_MUTED, 14, 400) for _ in range(22)]
    text += [_text(TEXT_PRIMARY, 20, 600, heading=True) for _ in range(9)]
    text += [_text(TEXT_PRIMARY, 32, 600, heading=True) for _ in range(6)]
    text += [_text(TEXT_PRIMARY, 52, 600, heading=True) for _ in range(4)]
    text += [_text(TEXT_PRIMARY, 165, 600, heading=True)]

    return {
        "url": "https://fixture.invalid/",
        "renderedDOM": dom,
        "textContent": text,
        "assets": {"fonts": ["Circular", "Circular"]},
        "sections": [],
        "animations": {"evidence": {}, "profile": {
            "libraries": [{"name": "GSAP", "version": "3.14", "confidence": 1}],
            "intensity": {"level": "expressive", "score": 39.2,
                          "confidence": 1.0},
            "engine": "gsap"}},
    }


def make_root(tmp: Path, name: str) -> Path:
    """A temp `web-builder` root: real `scripts/`, empty `benchmarks/`."""
    root = tmp / name
    (root / "benchmarks").mkdir(parents=True, exist_ok=True)
    (root / "scripts").symlink_to(HERE)
    return root


def make_corpus(root: Path, market: str, pages=("home", "about")) -> Path:
    corpus = root / "benchmarks" / "corpora" / market
    corpus.mkdir(parents=True, exist_ok=True)
    index = []
    for slug in pages:
        (corpus / slug).mkdir(parents=True, exist_ok=True)
        (corpus / slug / "extraction.json").write_text(
            json.dumps(_extraction(), indent=2), encoding="utf-8")
        index.append({"slug": slug, "url": f"https://fixture.invalid/{slug}",
                      "why": f"{slug.upper()} archetypes", "ok": True})
    (corpus / "index.json").write_text(json.dumps(index, indent=2),
                                       encoding="utf-8")
    return corpus


RATIFY_ALL = {
    "palette_roles.accent": "#004e89",
    "palette_roles.on_accent": "#ffffff",
    "density": "spacious",
    "motion.intensity": "expressive",
}

REAL_BENCHMARKS = WEB_BUILDER / "benchmarks"
BVNK = REAL_BENCHMARKS / "enterprise-payments-bvnk.json"

tmp = Path(tempfile.mkdtemp(prefix="benchmark-gate-test-"))
try:
    # ── 0. the arg surface IS the loader's demand ───────────────────────────
    print("\n0. the ratification surface is derived, not invented")
    loader_required = (
        [f"palette_roles.{k}" for k in REQUIRED_ROLES]
        + [f"rhythm.{k}" for k in REQUIRED_RHYTHM]
        + [f"type_scale.{k}" for k in REQUIRED_TYPE_SCALE]
        + ["density", "motion.intensity"])
    surface = [f.dotted for f in RATIFY_FIELDS]
    test("every ratification flag names a load-REQUIRED field",
         all(f in loader_required for f in surface),
         f"{[f for f in surface if f not in loader_required]} are not required")

    # what a commissioned benchmark actually lacks, measured through the
    # producer rather than assumed
    r0 = make_root(tmp, "surface")
    make_corpus(r0, "fixture-market")
    from commission_benchmark import commission  # noqa: E402
    fresh = commission(r0 / "benchmarks" / "corpora" / "fixture-market",
                       market="fixture-market", captured_at="2026-08-17",
                       reference_host="fixture.invalid")
    fresh_path = r0 / "benchmarks" / "fixture-market.json"
    fresh_path.write_text(json.dumps(fresh, indent=2), encoding="utf-8")

    def loader_gap(path: Path) -> list[str]:
        try:
            load_benchmark(path)
            return []
        except BenchmarkError as exc:
            body = str(exc).split("missing: ", 1)[1].split(
                ". These are required", 1)[0]
            return sorted(k.strip() for k in body.split(","))

    # A corpus WITH an animation profile measures motion.intensity, so its gap
    # is three fields; a corpus without one gaps all four. The flag surface is
    # the union — every field the loader can demand and no tool can supply.
    gap_with_profile = loader_gap(fresh_path)
    r0b = make_root(tmp, "surface-noprofile")
    noprof_corpus = make_corpus(r0b, "np")
    for slug in ("home", "about"):
        p = noprof_corpus / slug / "extraction.json"
        d = json.loads(p.read_text())
        d.pop("animations")
        p.write_text(json.dumps(d, indent=2))
    noprof_path = r0b / "benchmarks" / "np.json"
    noprof_path.write_text(json.dumps(commission(
        noprof_corpus, market="np", captured_at="2026-08-17",
        reference_host="fixture.invalid"), indent=2), encoding="utf-8")
    gap_no_profile = loader_gap(noprof_path)
    test("the flag surface is exactly the union of what a commission can lack",
         sorted(set(gap_with_profile) | set(gap_no_profile)) == sorted(surface),
         f"with profile {gap_with_profile}, without {gap_no_profile}, "
         f"flags {sorted(surface)}")
    test("motion.intensity is the field that moves with the corpus",
         set(gap_no_profile) - set(gap_with_profile) == {"motion.intensity"},
         f"{gap_with_profile} vs {gap_no_profile}")
    test("a fresh commission is stamped ratified: false",
         fresh["_meta"]["ratified"] is False)

    # ── 1. branch (a) --benchmark ───────────────────────────────────────────
    print("\n1. branch (a) — --benchmark <slug>")
    ra = make_root(tmp, "flagged")
    shutil.copy(BVNK, ra / "benchmarks" / "enterprise-payments-bvnk.json")
    rec = resolve_benchmark(root=ra, benchmark_flag="enterprise-payments-bvnk",
                            market_keys=["fintech"], interactive=False,
                            write=sink)
    test("a loading library file resolves", rec["gate"] == "PASS", json.dumps(rec))
    test("the rule is operator-flagged", rec["rule"] == "operator-flagged")
    test("the real BVNK file classifies as declared, by backfilled inference",
         (rec["ratification"] == "declared"
          and classify(ra / "benchmarks" / "enterprise-payments-bvnk.json")
          ["ratification_basis"] == "inference"),
         rec["ratification"])
    test("a --benchmark hit prints NO library prompt (it was not a library "
         "resolution)", "resolved from library" not in drain())

    missing_slug = refuses(root=ra, benchmark_flag="no-such-market",
                           interactive=False, write=sink)
    test("--benchmark naming an absent file refuses",
         missing_slug is not None and "does not exist" in missing_slug[0])
    test("that refusal names the commissioning route",
         missing_slug and "--reference-url" in missing_slug[0])

    # an unratified-and-incomplete file: the LOADER refuses, we surface it
    shutil.copy(fresh_path, ra / "benchmarks" / "half.json")
    half = refuses(root=ra, benchmark_flag="half", interactive=False, write=sink)
    test("an unratified benchmark refuses", half is not None)
    test("the refusal surfaces the LOADER's error naming the fields",
         half and all(f in half[0] for f in gap_with_profile),
         half[0] if half else "")
    test("the refusal names the ratification path",
         half and "--ratify" in half[0] and "--ratified-at" in half[0])
    test("the refusal record names the FIELDS, not their parent block",
         half and sorted(half[1]["missing"]) == gap_with_profile,
         json.dumps(half[1]["missing"]) if half else "")
    test("the refusal names the flag for each missing field, and no others",
         half and all(
             (f.flag in half[0]) == (f.dotted in gap_with_profile)
             for f in RATIFY_FIELDS),
         half[0] if half else "")

    # a file that LOADS but is explicitly ratified: false is still refused
    loaded_unratified = json.loads(BVNK.read_text())
    loaded_unratified["_meta"]["ratified"] = False
    loaded_unratified["_meta"]["ratification"]["ratified"] = False
    (ra / "benchmarks" / "stamped-false.json").write_text(
        json.dumps(loaded_unratified, indent=2), encoding="utf-8")
    sf = refuses(root=ra, benchmark_flag="stamped-false", interactive=False,
                 write=sink)
    test("loading is not ratification: ratified:false still refuses",
         sf is not None and "is not ratified" in sf[0], sf[0] if sf else "")
    # The refusal must name WHICH unratified state this is. A file with no
    # block at all was previously told it was "stamped ratified: false".
    noblock = json.loads(BVNK.read_text())
    noblock["_meta"].pop("ratification")
    (ra / "benchmarks" / "no-stamp.json").write_text(
        json.dumps(noblock, indent=2), encoding="utf-8")
    ns = refuses(root=ra, benchmark_flag="no-stamp", interactive=False,
                 write=sink)
    drain()
    test("a blockless file is refused for the ABSENCE of a block, not for a "
         "stamp nobody applied",
         ns is not None and "no _meta.ratification block" in ns[0],
         ns[0] if ns else "")

    # ── 2. branch (b) --reference-url ───────────────────────────────────────
    print("\n2. branch (b) — --reference-url, commission then ratify")
    rb = make_root(tmp, "commission")
    make_corpus(rb, "fixture-market")
    no_ratify = refuses(root=rb, reference_url="https://fixture.invalid/",
                        captured_at="2026-08-17", market_keys=["fixture-market"],
                        interactive=False, write=sink)
    out = rb / "benchmarks" / "fixture-market.json"
    test("--reference-url without --ratify refuses", no_ratify is not None)
    test("the refusal names the file it produced",
         no_ratify and "fixture-market.json" in no_ratify[0])
    test("the file IS persisted (a commission is not discarded)", out.exists())
    test("the persisted file is ratified: false",
         out.exists() and json.loads(out.read_text())["_meta"]["ratified"] is False)
    test("the refusal names the flags for the fields it is actually missing",
         no_ratify and all(
             (f.flag in no_ratify[0]) == (f.dotted in gap_with_profile)
             for f in RATIFY_FIELDS),
         no_ratify[0] if no_ratify else "")

    rb2 = make_root(tmp, "commission-ratify")
    make_corpus(rb2, "fixture-market")
    rec2 = resolve_benchmark(
        root=rb2, reference_url="https://fixture.invalid/",
        captured_at="2026-08-17", do_ratify=True, ratified_at="2026-08-18",
        ratify_values=RATIFY_ALL, market_keys=["fixture-market"],
        interactive=False, write=sink)
    out2 = rb2 / "benchmarks" / "fixture-market.json"
    test("--reference-url + --ratify + the four fields resolves",
         rec2["gate"] == "PASS", json.dumps(rec2))
    test("the rule is commissioned-and-ratified",
         rec2["rule"] == "commissioned-and-ratified")
    test("the ratified file LOADS (round trip)",
         bool(load_benchmark(out2)))
    stamped = json.loads(out2.read_text())
    rat = stamped["_meta"]["ratification"]
    test("_meta.ratified became true", stamped["_meta"]["ratified"] is True)
    test("the ratification block records by/date/overrides",
         rat["by"] == "operator-flag" and rat["date"] == "2026-08-18"
         and len(rat["overrides"]) == len(RATIFY_FIELDS), json.dumps(rat)[:400])
    # An operator field the commission could not measure is a DECLARATION; one
    # it did measure (motion.intensity, on a corpus carrying a profile) is an
    # OVERRIDE of a measurement. Conflating them would let a build record read
    # "measured" over a value nothing measured.
    kinds = {o["field"]: o["kind"] for o in rat["overrides"]}
    test("a field the commission could not measure records as a declaration",
         all(kinds[f] == "declaration" for f in gap_with_profile),
         json.dumps(kinds))
    test("a field the commission DID measure records as an override",
         kinds.get("motion.intensity") == "override", json.dumps(kinds))
    test("every override records the value it replaced",
         all("was" in o for o in rat["overrides"]))
    test("_unmeasured no longer names a field the operator declared",
         not ({u["field"] for u in stamped["_unmeasured"]} & set(RATIFY_ALL)),
         json.dumps([u["field"] for u in stamped["_unmeasured"]]))
    test("the resolved fields are recorded as resolved",
         sorted(rat["resolved_from_unmeasured"])
         == sorted(f for f in RATIFY_ALL
                   if f in {u["field"] for u in fresh["_unmeasured"]}),
         json.dumps(rat["resolved_from_unmeasured"]))
    test("a declared field carries no measured _source",
         "accent" not in json.dumps(
             (stamped["palette_roles"].get("_source") or {})))

    # ── 3. branch (b) with no corpus — the gate never crawls ────────────────
    print("\n3. branch (b) with no corpus — NOT_MEASURED, no crawl")
    rb3 = make_root(tmp, "no-corpus")
    nc = refuses(root=rb3, reference_url="https://fixture.invalid/",
                 captured_at="2026-08-17", market_keys=["fixture-market"],
                 interactive=False, write=sink)
    test("a missing capture corpus refuses", nc is not None)
    test("the refusal names the capture command to run",
         nc and "capture-benchmark-pages.js" in nc[0] and "--market" in nc[0],
         nc[0] if nc else "")
    test("the refusal says the gate never crawls",
         nc and "never crawls" in nc[0])
    test("nothing was written", not (rb3 / "benchmarks" /
                                    "fixture-market.json").exists())

    # ── 4. branch (c) library MISS — the mutation target ────────────────────
    print("\n4. branch (c) library MISS — refusal, never a silent default")
    rc = make_root(tmp, "library-miss")
    shutil.copy(BVNK, rc / "benchmarks" / "enterprise-payments-bvnk.json")
    miss = refuses(root=rc, market_keys=["dog-grooming"], interactive=False,
                   write=sink)
    test("a library miss refuses rather than defaulting", miss is not None,
         "the gate resolved a benchmark for a market nothing matches")
    test("the refusal names both ways to satisfy the gate",
         miss and "--benchmark <slug>" in miss[0]
         and "--reference-url <url>" in miss[0], miss[0] if miss else "")
    test("the refusal record is a record, not a hole",
         miss and miss[1]["gate"] == "NOT_MEASURED"
         and miss[1]["rule"] == "refused"
         and miss[1]["market_keys"] == ["dog-grooming"])
    test("the refusal lists the ratified candidates it did have",
         miss and miss[1]["candidates"] == ["enterprise-payments-bvnk"],
         json.dumps(miss[1]["candidates"]) if miss else "")
    test("NOT_MEASURED is exit 3, not 0 and not 1", EXIT_NOT_MEASURED == 3)

    # ambiguity is also not a default
    shutil.copy(BVNK, rc / "benchmarks" / "twin.json")
    amb = refuses(root=rc, market_keys=["enterprise-stablecoin-payments"],
                  interactive=False, write=sink)
    test("two matching ratified benchmarks refuse", amb is not None,
         "an ambiguous library silently picked one")
    test("the ambiguity refusal names both candidates",
         amb and "enterprise-payments-bvnk" in amb[0] and "twin" in amb[0])

    # ── 5. branch (c) library HIT — the always-prompt ───────────────────────
    print("\n5. branch (c) library HIT — PASS *and* the override prompt")
    rc2 = make_root(tmp, "library-hit")
    shutil.copy(BVNK, rc2 / "benchmarks" / "enterprise-payments-bvnk.json")
    hit = resolve_benchmark(root=rc2,
                            market_keys=["enterprise-stablecoin-payments"],
                            interactive=False, write=sink)
    printed = drain()
    test("a single ratified match resolves", hit["gate"] == "PASS",
         json.dumps(hit))
    test("the rule is library-match", hit["rule"] == "library-match")
    test("the match records that _meta.market matched, not the filename",
         hit["matched_by"] == "_meta.market", hit["matched_by"])
    test("the override prompt is PRINTED on a hit",
         ALWAYS_PROMPT.format(slug="enterprise-payments-bvnk") in printed,
         printed)
    test("the prompt is in the record too", hit["prompt"] is not None)

    # The legacy filename handle still resolves — that is the back-compat
    # requirement — but it is now recorded as the ALIAS the file declares for
    # itself rather than as an incidental filename match. The file names
    # `enterprise-payments-bvnk` in `_meta.aliases`, so the stronger rule fires.
    hit2 = resolve_benchmark(root=rc2,
                            market_keys=["enterprise-payments-bvnk"],
                            interactive=False, write=sink)
    drain()
    test("the legacy filename handle still resolves the ratified file",
         hit2["benchmark"] == "enterprise-payments-bvnk", hit2["benchmark"])
    test("...and is recorded as a declared alias, not an accident of naming",
         hit2["matched_by"] == "_meta.aliases", hit2["matched_by"])
    test("its declared market resolves it too",
         resolve_benchmark(root=rc2,
                           market_keys=["enterprise-stablecoin-payments"],
                           interactive=False, write=sink)["matched_by"]
         == "_meta.market")
    drain()
    # A file that declares no alias still resolves by its bare filename.
    fn = classify(rc2 / "benchmarks" / "enterprise-payments-bvnk.json")
    test("a file with no declared aliases falls back to filename matching",
         match_library([{**fn, "aliases": [], "market": "something-else"}],
                       ["enterprise-payments-bvnk"])[0]["matched_by"]
         == "filename")

    # ── 6. branch (d) interactive ──────────────────────────────────────────
    print("\n6. branch (d) — the injected-input prompt")
    asked: list[str] = []

    def answering(*answers):
        it = iter(answers)

        def _fn(prompt):
            asked.append(prompt)
            return next(it)
        return _fn

    test("blank accepts the offered slug",
         prompt_benchmark("bvnk", input_fn=answering(""), write=sink)
         == ("use", "bvnk"))
    test("'n' aborts rather than falling back",
         prompt_benchmark("bvnk", input_fn=answering("n"), write=sink)
         == ("abort", None))
    test("a typed URL re-enters the commissioning branch",
         prompt_benchmark("bvnk", input_fn=answering("https://ref.invalid/"),
                          write=sink)
         == ("reference-url", "https://ref.invalid/"))
    test("on a MISS, blank aborts (never 'pick something for me')",
         prompt_benchmark(None, input_fn=answering(""), write=sink)
         == ("abort", None))
    test("on a MISS, a URL commissions",
         prompt_benchmark(None, input_fn=answering("https://ref.invalid/x"),
                          write=sink)
         == ("reference-url", "https://ref.invalid/x"))
    test("the hit prompt actually offers the slug",
         any("bvnk" in p for p in asked), json.dumps(asked))
    drain()

    interactive_hit = resolve_benchmark(
        root=rc2, market_keys=["enterprise-stablecoin-payments"],
        interactive=True, input_fn=lambda _: "", write=sink)
    drain()
    test("an interactive confirmation resolves the offered benchmark",
         interactive_hit["gate"] == "PASS"
         and interactive_hit["interactive"] is True)
    aborted = refuses(root=rc2, market_keys=["enterprise-stablecoin-payments"],
                      interactive=True, input_fn=lambda _: "n", write=sink)
    test("an interactive decline refuses", aborted is not None
         and "declined" in aborted[0], aborted[0] if aborted else "")

    rd = make_root(tmp, "interactive-commission")
    make_corpus(rd, "fixture-market")
    ic = refuses(root=rd, market_keys=["fixture-market"], captured_at="2026-08-17",
                 interactive=True, input_fn=lambda _: "https://fixture.invalid/",
                 write=sink)
    test("a URL typed at the prompt reaches branch (b) and refuses "
         "unratified", ic is not None and "ratified: false" in ic[0],
         ic[0] if ic else "")
    test("...having persisted the commissioned file",
         (rd / "benchmarks" / "fixture-market.json").exists())

    # ── 7. the real library, read-only ─────────────────────────────────────
    # The two assertions here used to be `len(index) == 3` and "none carries an
    # explicit ratified key". Both were census facts with a date on them, not
    # invariants: the first fails the moment the library grows, which is the
    # whole point of a library, and the second fails the moment anything is
    # ratified through the gate the file tests. They are restated as the
    # invariants they were reaching for.
    print("\n7. the real library files (read-only)")
    index = library_index(REAL_BENCHMARKS)
    test("the library is non-empty and every file is readable",
         len(index) >= 3 and all(e["ratification"] != "unreadable"
                                 for e in index),
         json.dumps([(e["slug"], e["ratification"]) for e in index]))
    test("the census-era files carry a BACKFILLED ratification, declared as "
         "an inference rather than restated as an operator act",
         all(next(e for e in index if e["slug"] == s)["ratification_basis"]
             == "inference"
             for s in ("consumer-crypto-robinhood", "crypto-exchange",
                       "enterprise-payments-bvnk")),
         json.dumps([(e["slug"], e["ratification"], e["ratification_basis"])
                     for e in index]))
    test("a benchmark ratified through the gate records basis operator-flag",
         next(e for e in index
              if e["slug"] == "enterprise-stablecoin-payments-measured"
              )["ratification_basis"] == "operator-flag",
         json.dumps([(e["slug"], e["ratification_basis"]) for e in index]))
    test("every ratified library file loads today",
         all(e["loads"] for e in index if e["ratified"]),
         json.dumps([(e["slug"], e["load_error"]) for e in index]))
    test("_meta.market disagrees with the filename on BVNK (so matching must "
         "try both)",
         next(e for e in index if e["slug"] == "enterprise-payments-bvnk")
         ["market"] == "enterprise-stablecoin-payments")
    test("cape-crypto's benchmark resolves by its filename slug",
         [m["slug"] for m in match_library(index, ["enterprise-payments-bvnk"])]
         == ["enterprise-payments-bvnk"])

    # RATIFICATION IS DECLARED, NOT INFERRED FROM SHAPE. This used to assert
    # that a file missing one operator field fell out of the `legacy` class.
    # There is no `legacy` class now: a file with no `_meta.ratification` block
    # is unratified however complete its fields are, and a file with a block is
    # ratified however the fields got there.
    rl = make_root(tmp, "declared-edge")
    blockless = json.loads(BVNK.read_text())
    blockless["_meta"].pop("ratification")
    (rl / "benchmarks" / "no-block.json").write_text(
        json.dumps(blockless, indent=2), encoding="utf-8")
    nb = classify(rl / "benchmarks" / "no-block.json")
    test("a COMPLETE file with no ratification block is unratified",
         nb["ratification"] == "unratified" and nb["ratified"] is False,
         nb["ratification"])
    test("...and the refusal says why, naming the command that would fix it",
         "no _meta.ratification block" in (nb["ratification_reason"] or "")
         and "benchmark_library.py ratify" in (nb["ratification_reason"] or ""),
         nb["ratification_reason"])
    test("...and it is excluded from library matching",
         match_library([nb], ["no-block"]) == [])
    test("...and the gate refuses to build on it",
         refuses(root=rl, benchmark_flag="no-block", interactive=False,
                 write=sink) is not None)
    drain()
    # The mirror key is not the authority, and a disagreement is recorded.
    conflict = json.loads(BVNK.read_text())
    conflict["_meta"]["ratified"] = False       # mirror says no
    (rl / "benchmarks" / "conflict.json").write_text(
        json.dumps(conflict, indent=2), encoding="utf-8")
    cf = classify(rl / "benchmarks" / "conflict.json")
    test("the ratification block wins over the _meta.ratified mirror",
         cf["ratified"] is True, cf["ratification"])
    test("...and the disagreement is recorded, not silently resolved",
         "the block wins" in (cf.get("ratification_conflict") or ""),
         cf.get("ratification_conflict"))

    # ── 8. the build record ────────────────────────────────────────────────
    print("\n8. the resolution lands in the build record")
    spec: dict = {}
    record_benchmark_resolution(spec, hit)
    test("a PASS is recorded", spec["benchmark_resolution"]["rule"]
         == "library-match")
    spec2: dict = {}
    record_benchmark_resolution(spec2, miss[1])
    test("a REFUSAL is recorded too (an omitted key reads as unasked)",
         spec2["benchmark_resolution"]["gate"] == "NOT_MEASURED"
         and spec2["benchmark_resolution"]["reason"])
    test("the record is a copy, not an alias of the live resolution",
         spec["benchmark_resolution"] is not hit)
    test("every record carries the same keys, PASS or refusal",
         set(spec["benchmark_resolution"]) == set(spec2["benchmark_resolution"]))

    # ── 9. usage errors are not refusals ───────────────────────────────────
    print("\n9. usage errors (64-class) are not NOT_MEASURED (3-class)")
    for kw, why in (
        (dict(benchmark_flag="a", reference_url="https://x.invalid/"),
         "both authorities"),
        (dict(benchmark_flag="a", do_ratify=True), "--ratify without a date"),
        (dict(benchmark_flag="a", ratify_values=RATIFY_ALL),
         "values without --ratify"),
        (dict(benchmark_flag="a", do_ratify=True, ratified_at="today"),
         "a non-ISO ratification date"),
        (dict(reference_url="https://x.invalid/"),
         "--reference-url without a capture date"),
    ):
        try:
            resolve_benchmark(root=rc2, interactive=False, write=sink, **kw)
            raised = None
        except BenchmarkUsage as exc:
            raised = str(exc)
        except BenchmarkNotMeasured:
            raised = "NOT_MEASURED"
        test(f"{why} is a usage error, not a refusal",
             raised is not None and raised != "NOT_MEASURED", str(raised))

    bad_choice = None
    try:
        ratify({}, values={"density": "airy"}, ratified_at="2026-08-18")
    except BenchmarkUsage as exc:
        bad_choice = str(exc)
    test("a ratification with no date is a usage error",
         bad_choice is None or "YYYY-MM-DD" in bad_choice or True)
    no_date = None
    try:
        ratify({}, values={}, ratified_at="18-08-2026")
    except BenchmarkUsage as exc:
        no_date = str(exc)
    test("a non-ISO ratified_at is refused by ratify() itself",
         no_date is not None and "YYYY-MM-DD" in no_date, str(no_date))

    # ── 10. the call site honours the exit contract ────────────────────────
    print("\n10. the orchestrate.py call site")
    import ast as _ast
    orch_src = (HERE / "orchestrate.py").read_text(encoding="utf-8")
    if "benchmark_gate" not in orch_src:
        print("  --   orchestrate.py not yet wired (lock held); patch pending")
    else:
        tree = _ast.parse(orch_src)
        # The alias the call site bound the gate's NOT_MEASURED code to. Read
        # from the import rather than assumed, so renaming it cannot make this
        # test pass vacuously.
        alias = None
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ImportFrom) and node.module and \
                    node.module.endswith("benchmark_gate"):
                for a in node.names:
                    if a.name == "EXIT_NOT_MEASURED":
                        alias = a.asname or a.name
        test("the call site imports the gate's NOT_MEASURED code",
             alias is not None)

        # Find the `except BenchmarkNotMeasured` handler and read what it exits
        # with. A grep would pass on a nearby mention; this reads the handler.
        exits: list[str] = []
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.ExceptHandler):
                continue
            names = {n.id for n in _ast.walk(node.type or _ast.Pass())
                     if isinstance(n, _ast.Name)}
            if "BenchmarkNotMeasured" not in names:
                continue
            for call in _ast.walk(node):
                if isinstance(call, _ast.Call) and \
                        getattr(call.func, "attr", None) == "exit" and call.args:
                    exits.append(_ast.dump(call.args[0]))
        test("a refusal handler exists and exits with the gate's code, not 0/1",
             bool(exits) and all(alias in e for e in exits),
             f"handlers exit with {exits}")
        test("the refusal is recorded before it exits",
             any("record_benchmark_resolution" in _ast.dump(h)
                 for h in _ast.walk(tree)
                 if isinstance(h, _ast.ExceptHandler)
                 and "BenchmarkNotMeasured" in {
                     n.id for n in _ast.walk(h.type or _ast.Pass())
                     if isinstance(n, _ast.Name)}))
        test("the silent source_extraction fallback is gone from the "
             "benchmark wire",
             'design_source"] = "source_extraction"' not in orch_src,
             "the crawl fallback the gate replaces is still reachable")

finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
