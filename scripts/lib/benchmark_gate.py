"""The benchmark ratification gate — Task B3.

WHY THIS EXISTS
---------------
`orchestrate.py` resolved the design authority like this:

    _bm_market = args.benchmark or site_manifest.industry or args.industry or ...
    _bm_path   = ROOT / "benchmarks" / f"{_bm_market}.json"
    if _bm_path.exists():  compile_style(load_benchmark(_bm_path))
    else:                  design_source = "source_extraction"   # the crawl

The `else` is a silent default with a warning on it. A market with no benchmark
did not stop the build; it quietly reverted the design authority to the crawled
source — the exact substitution `design_system` exists to remove — and the run
still exited 0. A warning in a status list reads as passed.

This module replaces that resolution with a gate that has three outcomes and
always leaves a record. It does NOT re-invent refusal of a bad benchmark:
`design_system.load_benchmark` already raises `BenchmarkError` naming the
missing generation-half keys, and a commissioned benchmark omits four of them by
construction, so an unratified file already fails to load. This gate formalises
*ratification* — the operator act that supplies those four fields — and the
*always-prompt*, so a library hit is still an offer to override rather than a
fait accompli.

THE FOUR BRANCHES (`resolve_benchmark`)
---------------------------------------
  a. `--benchmark <slug>`      rule `operator-flagged`. The named file loads, or
                               its own loader error is surfaced and the gate
                               refuses. With `--ratify` it may be ratified first.
  b. `--reference-url <url>`   commission via `commission_benchmark.py`. The
                               product is `ratified: false` and does NOT build
                               in the same run unless `--ratify` and the four
                               operator fields are also passed
                               (`commissioned-and-ratified`). Without them the
                               gate persists the file and refuses, naming the
                               flags that would ratify it.
  c. neither, non-interactive  exactly one ratified library benchmark matching
                               the resolved market -> rule `library-match`, and
                               the always-prompt line is printed anyway. Zero
                               matches or several -> refusal.
  d. neither, interactive TTY  the same resolution, genuinely prompted. A
                               reference URL typed at the prompt re-enters (b).

Every branch — including every refusal — produces a resolution record, written
into the build record the same way `record_industry_resolution` writes the
industry node's winner (`orchestrate.py:9447`, commit `a0bce7d5`).

MEASURED FACTS THIS MODULE IS BUILT ON (2026-08-17, all reproducible)
---------------------------------------------------------------------
1. `load_benchmark` requires `_meta.captured_from`, eight `palette_roles`, four
   `rhythm` keys, four `type_scale` keys, `density` and `motion.intensity`
   (`design_system.py:88-124`).
2. A commissioned benchmark can lack exactly FOUR of those:
   `palette_roles.accent`, `palette_roles.on_accent` (absent unless
   `--tenant-accent` is declared), `density` (never measurable — no code path
   emits "spacious"), and `motion.intensity` (absent when the corpus carries no
   `animations.profile`). Measured by commissioning B2's synthetic fixture and
   reading the loader's own error. `RATIFY_FIELDS` is exactly that set: the
   ratification surface is derived from what the loader demands, not invented.
   `font_system.families` and `palette_roles.surface_inverse` are also
   unmeasurable but are NOT load-required, so they are not ratification args.
3. **None of the three library files carries a `ratified` key at all**, and all
   three load today. `enterprise-payments-bvnk.json` is the ratified benchmark
   cape-crypto builds depend on. Refusing them for a missing flag would break
   every existing build, so a file with no `ratified` key that carries all four
   operator fields classifies as `legacy` — recorded as such, never restated as
   an explicit ratification.
4. **`_meta.market` is not the filename slug.** `enterprise-payments-bvnk.json`
   declares market `enterprise-stablecoin-payments`; `consumer-crypto-robinhood.json`
   declares `consumer-crypto-exchange`. Library matching therefore tries both
   and records which one matched (`matched_by`). Matching on either alone would
   miss the ratified file.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .design_system import BenchmarkError, load_benchmark

#: The chain's and the node's shared NOT_MEASURED code. A gate that cannot
#: measure is neither a pass (0) nor a build failure (1).
EXIT_NOT_MEASURED = 3

#: Printed on EVERY library resolution, hit included. The operator's standing
#: requirement: taste enters once, explicitly, and a library hit must still
#: announce that it can be overridden. A default nobody was offered a choice
#: about is a silent default with extra steps.
ALWAYS_PROMPT = ("benchmark {slug} resolved from library; pass --reference-url "
                 "to override")

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class RatifyField:
    """One load-required key a commissioned benchmark cannot measure."""

    flag: str            # the CLI flag that declares it
    dest: str            # argparse dest
    path: tuple[str, ...]  # where it lands in the benchmark dict
    choices: tuple[str, ...] | None  # None => free hex value

    @property
    def dotted(self) -> str:
        return ".".join(self.path)

    def validate(self, value: str) -> str | None:
        """Return an error string, or None when the value is acceptable."""
        if self.choices is not None:
            if value not in self.choices:
                return (f"{self.flag} must be one of "
                        f"{'|'.join(self.choices)}, got {value!r}")
            return None
        if not _HEX.match(value):
            return f"{self.flag} must be #rrggbb, got {value!r}"
        return None


#: Derived from `design_system.load_benchmark` ∩ what `commission_benchmark.py`
#: leaves absent — see the module note, fact 2. Adding a field here without a
#: loader requirement behind it re-opens the door this gate closes.
RATIFY_FIELDS: tuple[RatifyField, ...] = (
    RatifyField("--ratify-accent", "ratify_accent",
                ("palette_roles", "accent"), None),
    RatifyField("--ratify-on-accent", "ratify_on_accent",
                ("palette_roles", "on_accent"), None),
    RatifyField("--ratify-density", "ratify_density", ("density",),
                ("compact", "comfortable", "spacious")),
    #: `animation-detector.js:552-557` maps its score onto exactly these four.
    RatifyField("--ratify-motion-intensity", "ratify_motion_intensity",
                ("motion", "intensity"),
                ("none", "subtle", "moderate", "expressive")),
)

#: The four fields whose presence makes a key-less legacy file usable. Same set
#: as `RATIFY_FIELDS` by construction: it IS the operator-declared half.
_OPERATOR_PATHS = tuple(f.path for f in RATIFY_FIELDS)

COMMISSIONER = "scripts/commission_benchmark.py"
CAPTURE_STEP = "scripts/quality/capture-benchmark-pages.js"


class BenchmarkNotMeasured(Exception):
    """The gate could not resolve a benchmark. Exit 3, never 0, never 1.

    Carries the resolution record so the refusal is written into the build
    record too: a refusal that leaves no trace is indistinguishable from a
    question nobody asked.
    """

    def __init__(self, message: str, record: dict[str, Any]):
        super().__init__(message)
        self.message = message
        self.record = record


class BenchmarkUsage(Exception):
    """Flags that cannot mean anything together. Exit 64."""


# ── the library ──────────────────────────────────────────────────────────────
def _dig(data: dict[str, Any], path: Sequence[str]) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _plant(data: dict[str, Any], path: Sequence[str], value: Any) -> None:
    cur = data
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def classify(path: Path) -> dict[str, Any]:
    """One library file's ratification status. Never raises on bad JSON.

    `ratification` is one of:
      declared    `_meta.ratified is True` — stamped by this gate or by hand
      legacy      no `ratified` key, but all four operator fields present. The
                  three files in the library today are all this, and
                  cape-crypto's build depends on one of them (module note, 3).
      unratified  `_meta.ratified is False`, or operator fields missing
      unreadable  not JSON, or not an object
    """
    record: dict[str, Any] = {
        "slug": path.stem,
        "path": path.name,
        "market": None,
        "aliases": [],
        "captured_at": None,
        "corpus": None,
        "ratification": "unreadable",
        "ratified": False,
        "missing_operator_fields": [],
        "loads": False,
        "load_error": None,
    }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        record["load_error"] = str(exc)
        return record
    if not isinstance(data, dict):
        record["load_error"] = "benchmark is not a JSON object"
        return record

    meta = data.get("_meta") or {}
    record["market"] = meta.get("market")
    # A benchmark belongs to a MARKET; the filename is an accident of who wrote
    # it. Two of the library's files are named after the site they were measured
    # from rather than the market they describe, and the gate used to reconcile
    # that with an undeclared rule in a docstring. `_meta.aliases` lets the file
    # declare its own back-compat handles instead.
    aliases = meta.get("aliases")
    record["aliases"] = sorted(a for a in (aliases or []) if isinstance(a, str))
    record["captured_at"] = meta.get("captured_at")
    record["corpus"] = meta.get("corpus")
    missing = [".".join(p) for p in _OPERATOR_PATHS if _dig(data, p) in (None, "")]
    record["missing_operator_fields"] = missing

    flag = meta.get("ratified")
    if flag is True:
        record["ratification"] = "declared"
    elif flag is False:
        record["ratification"] = "unratified"
    elif missing:
        record["ratification"] = "unratified"
    else:
        record["ratification"] = "legacy"
    record["ratified"] = record["ratification"] in ("declared", "legacy")
    if isinstance(meta.get("ratification"), dict):
        record["ratified_by"] = meta["ratification"].get("by")

    try:
        load_benchmark(path)
        record["loads"] = True
    except BenchmarkError as exc:
        record["load_error"] = str(exc)
    return record


#: The generated index itself is a `benchmarks/*.json` file and is not a
#: benchmark. Excluded by name so `library_index` cannot classify its own
#: output as an unreadable benchmark.
INDEX_FILENAME = "index.json"


def library_index(benchmarks_dir: Path) -> list[dict[str, Any]]:
    """Every `benchmarks/*.json`, classified, sorted by slug."""
    if not benchmarks_dir.is_dir():
        return []
    return sorted(
        (classify(p) for p in benchmarks_dir.glob("*.json")
         if p.name != INDEX_FILENAME),
        key=lambda r: r["slug"],
    )


def build_index(benchmarks_dir: Path) -> dict[str, Any]:
    """The library's market -> file map, derived wholly from the files.

    GENERATED, NEVER HAND-MAINTAINED. There is no clock in here: `captured_at`
    and the ratification date are read from the files, so regenerating an
    unchanged library produces identical bytes. A hand-edited index is a second
    source of truth that drifts, and a stale index is worse than none — it
    answers confidently and wrongly. `check_index` exists to make that
    impossible to leave in the tree.
    """
    entries = library_index(benchmarks_dir)
    markets: dict[str, Any] = {}
    aliases: dict[str, str] = {}
    collisions: list[dict[str, Any]] = []

    for e in entries:
        market = e["market"] or e["slug"]
        row = {
            "file": e["path"],
            "slug": e["slug"],
            "market": market,
            "aliases": e["aliases"],
            "ratified": e["ratified"],
            "ratification": e["ratification"],
            "captured_at": e["captured_at"],
            "corpus": e["corpus"],
            "loads": e["loads"],
        }
        if market in markets:
            # Two files claiming one market is exactly the ambiguity the gate
            # refuses on. The index records it rather than letting last-write
            # win: an index that silently drops one of them would hide the
            # reason the gate refuses.
            collisions.append({"market": market,
                               "files": sorted([markets[market]["file"],
                                                e["path"]])})
        markets[market] = row
        for alias in e["aliases"]:
            aliases[alias] = market
        if e["slug"] not in aliases and e["slug"] != market:
            aliases[e["slug"]] = market

    return {
        "_meta": {
            "generated_by": "scripts/benchmark_library.py index",
            "note": ("GENERATED — do not hand-edit. Regenerate with "
                     "`python3 scripts/benchmark_library.py index`; "
                     "`--check` fails if this disagrees with the files on "
                     "disk. There is no timestamp here on purpose: an "
                     "unchanged library must regenerate to identical bytes."),
            "market_count": len(markets),
            "file_count": len(entries),
        },
        "markets": {k: markets[k] for k in sorted(markets)},
        "aliases": {k: aliases[k] for k in sorted(aliases)},
        "collisions": sorted(collisions, key=lambda c: c["market"]),
    }


def index_payload(benchmarks_dir: Path) -> str:
    return json.dumps(build_index(benchmarks_dir), indent=2) + "\n"


def check_index(benchmarks_dir: Path) -> tuple[bool, str]:
    """Does the persisted index still describe the files on disk?

    Returns `(agrees, detail)`. Never raises on a missing or corrupt index —
    both are disagreements, not crashes.
    """
    path = benchmarks_dir / INDEX_FILENAME
    want = index_payload(benchmarks_dir)
    if not path.exists():
        return False, (f"{path.name} does not exist. Generate it: "
                       f"python3 scripts/benchmark_library.py index")
    have = path.read_text(encoding="utf-8")
    if have == want:
        return True, f"{path.name} agrees with {len(library_index(benchmarks_dir))} file(s) on disk"

    try:
        hi = json.loads(have)
        if not isinstance(hi, dict):
            hi = {}
    except json.JSONDecodeError as exc:
        return False, (f"{path.name} is not readable JSON ({exc}). "
                       f"Regenerate: python3 scripts/benchmark_library.py index")
    wi = json.loads(want)
    lines = [f"{path.name} disagrees with the files on disk:"]
    hm, wm = (hi.get("markets") or {}), wi["markets"]
    for m in sorted(set(hm) | set(wm)):
        if m not in hm:
            lines.append(f"    + market {m!r} on disk, absent from the index")
        elif m not in wm:
            lines.append(f"    - market {m!r} in the index, absent on disk")
        elif hm[m] != wm[m]:
            for k in sorted(set(hm[m]) | set(wm[m])):
                if hm[m].get(k) != wm[m].get(k):
                    lines.append(f"    ~ {m}.{k}: index says "
                                 f"{hm[m].get(k)!r}, disk says {wm[m].get(k)!r}")
    if len(lines) == 1:
        lines.append("    (the market map agrees; aliases, collisions or "
                     "_meta counts differ — regenerate)")
    lines.append("  Regenerate: python3 scripts/benchmark_library.py index")
    return False, "\n".join(lines)


def match_library(index: Iterable[dict[str, Any]],
                  market_keys: Sequence[str]) -> list[dict[str, Any]]:
    """Ratified benchmarks matching a key, by market identity first.

    PRECEDENCE, and why it is this way round:
      1. `_meta.market`     the benchmark's identity. A benchmark describes a
                            market; this is the thing it IS.
      2. `_meta.aliases`    handles the file declares for itself, so a rename
                            that never happened cannot break a caller.
      3. filename slug      back-compat. Two library files are named after the
                            site they were measured from, not the market they
                            describe, and `--benchmark <filename>` is the handle
                            in every recorded invocation. It resolves, and is
                            recorded as the weakest match so a build record
                            never implies the file declared a market it did not.

    `matched_by` records which rule fired.
    """
    keys = [k for k in market_keys if k]
    out: list[dict[str, Any]] = []
    for entry in index:
        if not entry["ratified"]:
            continue
        # Rule-major, not key-major: the strongest RULE wins regardless of the
        # order the caller happened to resolve its market keys in.
        rules = (
            ("_meta.market", lambda k: bool(entry["market"]) and entry["market"] == k),
            ("_meta.aliases", lambda k: k in (entry.get("aliases") or [])),
            ("filename", lambda k: entry["slug"] == k),
        )
        hit = None
        for name, fires in rules:
            match = next((k for k in keys if fires(k)), None)
            if match is not None:
                hit = (name, match)
                break
        if hit:
            out.append({**entry, "matched_by": hit[0], "matched_key": hit[1]})
    return out


# ── ratification ─────────────────────────────────────────────────────────────
def collect_ratify_values(args: Any) -> dict[str, str]:
    """The operator's declared values, keyed by dotted path. Validates each."""
    values: dict[str, str] = {}
    for f in RATIFY_FIELDS:
        raw = getattr(args, f.dest, None)
        if raw in (None, ""):
            continue
        err = f.validate(str(raw))
        if err:
            raise BenchmarkUsage(err)
        values[f.dotted] = str(raw)
    return values


def ratify(benchmark: dict[str, Any], *, values: dict[str, str],
           ratified_at: str, by: str = "operator-flag",
           source_path: str | None = None) -> dict[str, Any]:
    """Stamp `ratified: true` and record exactly what the operator declared.

    Returns a NEW dict; the caller writes it. `ratified_at` is a passed date and
    never `datetime.now()` — a benchmark that changes bytes by the day cannot be
    the thing a determinism check compares against.
    """
    if not _DATE.match(ratified_at):
        raise BenchmarkUsage(
            f"--ratified-at must be YYYY-MM-DD, got {ratified_at!r}")
    out = json.loads(json.dumps(benchmark))  # deep copy, JSON-shaped by contract
    meta = out.setdefault("_meta", {})

    overrides: list[dict[str, Any]] = []
    for f in RATIFY_FIELDS:
        if f.dotted not in values:
            continue
        was = _dig(out, f.path)
        _plant(out, f.path, values[f.dotted])
        overrides.append({
            "field": f.dotted,
            "flag": f.flag,
            "value": values[f.dotted],
            # An operator field that was already present is an OVERRIDE of a
            # measurement; one that was absent is a DECLARATION of something no
            # tool can measure. The record distinguishes them.
            "was": was,
            "kind": "override" if was not in (None, "") else "declaration",
        })

    # `_unmeasured` must stop naming what the operator has now declared, or the
    # file simultaneously claims a value and claims it was never measured.
    declared = {o["field"] for o in overrides}
    if isinstance(out.get("_unmeasured"), list):
        remaining = [u for u in out["_unmeasured"]
                     if u.get("field") not in declared]
        resolved = [u["field"] for u in out["_unmeasured"]
                    if u.get("field") in declared]
        out["_unmeasured"] = remaining
    else:
        resolved = []

    meta["ratified"] = True
    meta["ratification"] = {
        "by": by,
        "date": ratified_at,
        "overrides": overrides,
        "resolved_from_unmeasured": sorted(resolved),
        "source": source_path,
        "note": ("Fields under `overrides` are OPERATOR DECLARATIONS, not "
                 "measurements. `_source` provenance is not written for them: a "
                 "declared value that claimed a measured provenance would be "
                 "fabrication with a citation."),
    }
    return out


def missing_for_load(path: Path) -> list[str]:
    """The load-required fields this file lacks, from the loader's own error."""
    try:
        load_benchmark(path)
        return []
    except BenchmarkError as exc:
        text = str(exc)
        # The field names contain dots (`palette_roles.accent`), so the
        # terminator must be the sentence, not the next period. A `[^.]+` here
        # returned `["palette_roles"]` — a refusal that named a block instead of
        # the three fields the operator has to declare.
        m = re.search(r"generation-half keys missing: (.+?)\. These are required",
                      text)
        if m:
            return [k.strip() for k in m.group(1).split(",") if k.strip()]
        return [text]


def ratification_hint(missing: Sequence[str]) -> list[str]:
    """The exact flags that would ratify a file missing `missing`."""
    by_field = {f.dotted: f for f in RATIFY_FIELDS}
    flags = ["--ratify", "--ratified-at YYYY-MM-DD"]
    for name in missing:
        f = by_field.get(name)
        if f is None:
            continue
        flags.append(
            f"{f.flag} {'|'.join(f.choices) if f.choices else '#rrggbb'}")
    return flags


# ── commissioning (branch b) ─────────────────────────────────────────────────
def default_commission_runner(
    *, root: Path, corpus: Path, market: str, captured_at: str,
    reference_host: str | None, out: Path,
) -> subprocess.CompletedProcess:
    """Invoke the real producer as a subprocess.

    Subprocess rather than an import, for the same reason the node tools are:
    `commission_benchmark.py` owns an exit-code contract (0 / 3 / 64) and its
    refusals are stderr text. Importing it would put this gate in the business
    of re-deciding what its refusals mean.
    """
    cmd = [sys.executable, str(root / COMMISSIONER), str(corpus),
           "--market", market, "--captured-at", captured_at,
           "--out", str(out)]
    if reference_host:
        cmd += ["--reference-host", reference_host]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))


def host_of(url: str) -> str:
    m = re.match(r"^[a-z]+://([^/]+)", (url or "").strip(), re.I)
    return (m.group(1) if m else (url or "").strip()).lower()


def slugify_host(url: str) -> str:
    host = re.sub(r"^www\.", "", host_of(url))
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")
    return slug or "reference"


def corpus_dir_for(root: Path, market: str) -> Path:
    """Where `capture-benchmark-pages.js` writes, per its own default."""
    return root / "benchmarks" / "corpora" / market


def capture_command(market: str, url: str) -> str:
    return (f"node {CAPTURE_STEP} --market {market} "
            f"--page 'home|{url}|HERO, NAV, FOOTER'")


# ── the prompt (branch d) ────────────────────────────────────────────────────
def prompt_benchmark(hit_slug: str | None, *, input_fn: Callable[[str], str],
                     write: Callable[[str], None]) -> tuple[str, str | None]:
    """Deliberately dumb, and injectable so it is testable without a TTY.

    Returns `("use", slug)`, `("reference-url", url)` or `("abort", None)`.
    A blank answer accepts the offered slug on a hit and aborts on a miss —
    never "pick something for me".
    """
    if hit_slug:
        write(f"  benchmark '{hit_slug}' resolved from library.\n")
        answer = input_fn(
            f"  use '{hit_slug}'? [Y/n] or enter a reference URL: ").strip()
        if answer == "" or answer.lower() in ("y", "yes"):
            return "use", hit_slug
        if answer.lower() in ("n", "no"):
            return "abort", None
    else:
        write("  no ratified benchmark matches this market.\n")
        answer = input_fn(
            "  enter a reference URL to commission one, or blank to abort: "
        ).strip()
        if answer == "":
            return "abort", None
    if re.match(r"^https?://", answer, re.I):
        return "reference-url", answer
    return "abort", None


# ── the record ───────────────────────────────────────────────────────────────
def _record(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "gate": "NOT_MEASURED",
        "benchmark": None,
        "path": None,
        "rule": None,
        "ratified": False,
        "ratification": None,
        "ratified_by": None,
        "reference_url": None,
        "market_keys": [],
        "matched_by": None,
        "matched_key": None,
        "candidates": [],
        "prompt": None,
        "reason": None,
        "interactive": False,
        "missing": [],
    }
    base.update(kw)
    return base


def record_benchmark_resolution(site_spec: dict, resolution: dict) -> dict:
    """Stamp the resolution into the build record.

    Same contract as `record_industry_resolution` (`orchestrate.py:9447`): the
    key is written unconditionally, including when the answer was a refusal. An
    omitted key reads as a question nobody asked.
    """
    site_spec["benchmark_resolution"] = dict(resolution)
    return site_spec


def print_benchmark_resolution(resolution: dict,
                               write: Callable[[str], None]) -> None:
    if resolution.get("gate") != "PASS":
        write(f"  ⊘ Benchmark NOT_MEASURED: {resolution.get('reason')}\n")
        return
    write(f"  📐 Benchmark '{resolution['benchmark']}' by rule "
          f"{resolution['rule']} (ratification: "
          f"{resolution.get('ratification')})\n")
    if resolution.get("matched_by"):
        write(f"     matched on {resolution['matched_by']} = "
              f"{resolution.get('matched_key')!r}\n")
    if resolution.get("prompt"):
        write(f"     ↪ {resolution['prompt']}\n")


# ── the gate ─────────────────────────────────────────────────────────────────
def _two_ways(market_keys: Sequence[str]) -> str:
    keys = ", ".join(repr(k) for k in market_keys if k) or "(none resolved)"
    return (
        f"no ratified benchmark in the library matches market {keys}. There are "
        f"exactly two ways to satisfy this gate:\n"
        f"    1. name an existing one:  --benchmark <slug>\n"
        f"    2. commission a new one:  --reference-url <url> "
        f"--benchmark-captured-at YYYY-MM-DD\n"
        f"       (then ratify it: {' '.join(ratification_hint([f.dotted for f in RATIFY_FIELDS]))})\n"
        f"  The design authority is never silently the crawl."
    )


def resolve_benchmark(
    *,
    root: Path,
    benchmark_flag: str | None = None,
    reference_url: str | None = None,
    captured_at: str | None = None,
    do_ratify: bool = False,
    ratified_at: str | None = None,
    ratify_values: dict[str, str] | None = None,
    market_keys: Sequence[str] = (),
    interactive: bool | None = None,
    input_fn: Callable[[str], str] | None = None,
    write: Callable[[str], None] | None = None,
    commission_runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> dict[str, Any]:
    """Resolve the design authority, or refuse. Never a silent default.

    Raises `BenchmarkNotMeasured` (carrying the record) on a refusal and
    `BenchmarkUsage` on flags that cannot mean anything together. Returns the
    resolution record with `gate: "PASS"` and `path` pointing at a file that
    `load_benchmark` accepts — verified by loading it, not by assuming.
    """
    write = write or (lambda s: sys.stdout.write(s))
    ratify_values = dict(ratify_values or {})
    benchmarks_dir = root / "benchmarks"
    keys = [k for k in market_keys if k]
    commission_runner = commission_runner or default_commission_runner

    if benchmark_flag and reference_url:
        raise BenchmarkUsage(
            "--benchmark and --reference-url both name a design authority. "
            "Pass one: --benchmark uses the library, --reference-url "
            "commissions a new benchmark.")
    if do_ratify and not ratified_at:
        raise BenchmarkUsage(
            "--ratify requires --ratified-at YYYY-MM-DD. A ratification with "
            "no date is not a record of an operator act.")
    if ratified_at and not _DATE.match(ratified_at):
        raise BenchmarkUsage(
            f"--ratified-at must be YYYY-MM-DD, got {ratified_at!r}")
    if ratify_values and not do_ratify:
        raise BenchmarkUsage(
            "ratification values were passed without --ratify: "
            f"{', '.join(sorted(ratify_values))}. Declaring a field is the act; "
            "--ratify is the consent.")

    if interactive is None:
        interactive = bool(getattr(sys.stdin, "isatty", lambda: False)())

    # ── (b) commission from a reference URL ──────────────────────────────────
    if reference_url:
        return _branch_commission(
            root=root, benchmarks_dir=benchmarks_dir, reference_url=reference_url,
            captured_at=captured_at, do_ratify=do_ratify,
            ratified_at=ratified_at, ratify_values=ratify_values, keys=keys,
            interactive=interactive, write=write,
            commission_runner=commission_runner)

    # ── (a) operator-flagged slug ────────────────────────────────────────────
    if benchmark_flag:
        return _branch_flagged(
            benchmarks_dir=benchmarks_dir, slug=benchmark_flag,
            do_ratify=do_ratify, ratified_at=ratified_at,
            ratify_values=ratify_values, keys=keys, interactive=interactive,
            write=write)

    # ── (c)/(d) the library ──────────────────────────────────────────────────
    index = library_index(benchmarks_dir)
    matches = match_library(index, keys)
    hit = matches[0] if len(matches) == 1 else None

    if interactive:
        choice, value = prompt_benchmark(
            hit["slug"] if hit else None,
            input_fn=input_fn or input, write=write)
        if choice == "reference-url":
            return _branch_commission(
                root=root, benchmarks_dir=benchmarks_dir, reference_url=value,
                captured_at=captured_at, do_ratify=do_ratify,
                ratified_at=ratified_at, ratify_values=ratify_values, keys=keys,
                interactive=interactive, write=write,
                commission_runner=commission_runner)
        if choice == "abort":
            reason = ("the operator declined the offered benchmark"
                      if hit else _two_ways(keys))
            raise BenchmarkNotMeasured(reason, _record(
                rule="refused", reason=reason, market_keys=keys,
                interactive=True, reference_url=None,
                candidates=[m["slug"] for m in matches]))
        # choice == "use" -> fall through to the library-hit path below.

    if len(matches) > 1:
        slugs = ", ".join(sorted(m["slug"] for m in matches))
        reason = (
            f"{len(matches)} ratified benchmarks match market "
            f"{', '.join(repr(k) for k in keys)}: {slugs}. Ambiguity is not a "
            f"default — name one with --benchmark <slug>.")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", reason=reason, market_keys=keys,
            candidates=sorted(m["slug"] for m in matches),
            interactive=interactive))

    if not matches:
        reason = _two_ways(keys)
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", reason=reason, market_keys=keys,
            candidates=sorted(e["slug"] for e in index if e["ratified"]),
            interactive=interactive))

    entry = matches[0]
    path = benchmarks_dir / entry["path"]
    if not entry["loads"]:
        missing = missing_for_load(path)
        reason = (
            f"library benchmark '{entry['slug']}' matched but does not load: "
            f"{entry['load_error']}\n  ratify it with: "
            f"{' '.join(ratification_hint(missing))} --benchmark {entry['slug']}")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=entry["slug"], path=str(path),
            reason=reason, market_keys=keys, missing=missing,
            ratification=entry["ratification"], interactive=interactive))

    prompt = ALWAYS_PROMPT.format(slug=entry["slug"])
    write(f"  {prompt}\n")
    return _record(
        gate="PASS", benchmark=entry["slug"], path=str(path),
        rule="library-match", ratified=True,
        ratification=entry["ratification"],
        ratified_by=entry.get("ratified_by"),
        market_keys=keys, matched_by=entry["matched_by"],
        matched_key=entry["matched_key"],
        candidates=[entry["slug"]], prompt=prompt, interactive=interactive,
        reason=(f"exactly one ratified benchmark matched "
                f"({entry['matched_by']}={entry['matched_key']!r})"))


def _branch_flagged(*, benchmarks_dir: Path, slug: str, do_ratify: bool,
                    ratified_at: str | None, ratify_values: dict[str, str],
                    keys: Sequence[str], interactive: bool,
                    write: Callable[[str], None]) -> dict[str, Any]:
    path = benchmarks_dir / f"{slug}.json"
    if not path.exists():
        reason = (
            f"--benchmark {slug} names {path.name}, which does not exist. "
            f"Commission it: --reference-url <url> --benchmark-captured-at "
            f"YYYY-MM-DD")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=slug, path=str(path), reason=reason,
            market_keys=list(keys), interactive=interactive))

    entry = classify(path)
    if do_ratify:
        _apply_ratification(path, values=ratify_values, ratified_at=ratified_at,
                            write=write)
        entry = classify(path)

    if not entry["loads"]:
        missing = missing_for_load(path)
        # The loader's own error is surfaced verbatim: it already names the
        # missing fields, and paraphrasing it is how a precise refusal becomes
        # a vague one.
        reason = (f"--benchmark {slug} is not usable: {entry['load_error']}\n"
                  f"  ratify it with: {' '.join(ratification_hint(missing))} "
                  f"--benchmark {slug}")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=slug, path=str(path), reason=reason,
            market_keys=list(keys), missing=missing,
            ratification=entry["ratification"], interactive=interactive))

    if not entry["ratified"]:
        reason = (
            f"--benchmark {slug} loads but is stamped ratified: false. A "
            f"benchmark that loads is not thereby ratified — ratify it "
            f"explicitly: {' '.join(ratification_hint([]))} --benchmark {slug}")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=slug, path=str(path), reason=reason,
            market_keys=list(keys), ratification=entry["ratification"],
            interactive=interactive))

    return _record(
        gate="PASS", benchmark=slug, path=str(path), rule="operator-flagged",
        ratified=True, ratification=entry["ratification"],
        ratified_by=entry.get("ratified_by"), market_keys=list(keys),
        candidates=[slug], interactive=interactive,
        reason="named explicitly with --benchmark")


def _apply_ratification(path: Path, *, values: dict[str, str],
                        ratified_at: str | None,
                        write: Callable[[str], None]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    stamped = ratify(data, values=values, ratified_at=str(ratified_at),
                     source_path=path.name)
    path.write_text(json.dumps(stamped, indent=2) + "\n", encoding="utf-8")
    declared = ", ".join(o["field"] for o in
                         stamped["_meta"]["ratification"]["overrides"]) or "nothing"
    write(f"  ✍ ratified {path.name} at {ratified_at} — declared: {declared}\n")


def _branch_commission(*, root: Path, benchmarks_dir: Path, reference_url: str,
                       captured_at: str | None, do_ratify: bool,
                       ratified_at: str | None, ratify_values: dict[str, str],
                       keys: Sequence[str], interactive: bool,
                       write: Callable[[str], None],
                       commission_runner) -> dict[str, Any]:
    if not captured_at:
        raise BenchmarkUsage(
            "--reference-url requires --benchmark-captured-at YYYY-MM-DD. The "
            "date is never the clock: the same corpus must compile to the same "
            "bytes on any day.")
    if not _DATE.match(captured_at):
        raise BenchmarkUsage(
            f"--benchmark-captured-at must be YYYY-MM-DD, got {captured_at!r}")

    # The market slug names the output file. A resolved market key is preferred
    # over the reference host: the benchmark belongs to a MARKET, and naming it
    # after the site it was measured from is how a library ends up with
    # `consumer-crypto-robinhood` whose declared market is something else.
    slug = next((k for k in keys if _SLUG.match(k or "")), None)
    slug_source = "market_key" if slug else "reference_host"
    slug = slug or slugify_host(reference_url)

    corpus = corpus_dir_for(root, slug)
    usable = corpus.is_dir() and (corpus / "index.json").exists()
    if not usable:
        # THE GATE NEVER CRAWLS. Capture needs the network and Playwright, and a
        # gate that reaches for either turns a build into a crawler. Capture is
        # out-of-band, like media generation.
        reason = (
            f"no capture corpus for market '{slug}' at "
            f"{corpus.relative_to(root) if corpus.is_relative_to(root) else corpus}. "
            f"This gate never crawls — capture is out-of-band:\n"
            f"    {capture_command(slug, reference_url)}\n"
            f"  then re-run with --reference-url {reference_url} "
            f"--benchmark-captured-at {captured_at}")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=slug, reference_url=reference_url,
            reason=reason, market_keys=list(keys), interactive=interactive))

    out = benchmarks_dir / f"{slug}.json"
    proc = commission_runner(
        root=root, corpus=corpus, market=slug, captured_at=captured_at,
        reference_host=host_of(reference_url), out=out)
    if proc.returncode != 0:
        # The producer's exit code is the verdict; 3 stays 3.
        reason = (
            f"commissioning '{slug}' from {reference_url} did not produce a "
            f"benchmark (exit {proc.returncode}):\n"
            f"{(proc.stderr or proc.stdout or '').strip()}")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=slug, reference_url=reference_url,
            reason=reason, market_keys=list(keys), interactive=interactive))
    write(f"  🧪 commissioned {out.name} from {reference_url} "
          f"(corpus {corpus.name}, unratified by construction)\n")

    if not do_ratify:
        missing = missing_for_load(out)
        reason = (
            f"commissioned {out.name} and PERSISTED it — it is stamped "
            f"ratified: false and does not load "
            f"(missing: {', '.join(missing) or 'nothing'}). A benchmark this "
            f"run produced is not a benchmark this run may build on. Ratify "
            f"it:\n    {' '.join(ratification_hint(missing))} "
            f"--benchmark {slug}")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=slug, path=str(out),
            reference_url=reference_url, reason=reason, market_keys=list(keys),
            missing=missing, ratification="unratified",
            interactive=interactive))

    _apply_ratification(out, values=ratify_values, ratified_at=ratified_at,
                        write=write)
    entry = classify(out)
    if not entry["loads"]:
        missing = missing_for_load(out)
        reason = (
            f"{out.name} was ratified but still does not load: "
            f"{entry['load_error']}\n  supply the remaining fields: "
            f"{' '.join(ratification_hint(missing))}")
        raise BenchmarkNotMeasured(reason, _record(
            rule="refused", benchmark=slug, path=str(out),
            reference_url=reference_url, reason=reason, market_keys=list(keys),
            missing=missing, ratification=entry["ratification"],
            interactive=interactive))

    return _record(
        gate="PASS", benchmark=slug, path=str(out),
        rule="commissioned-and-ratified", ratified=True,
        ratification=entry["ratification"], ratified_by="operator-flag",
        reference_url=reference_url, market_keys=list(keys),
        matched_by=slug_source, matched_key=slug, candidates=[slug],
        interactive=interactive,
        reason=(f"commissioned from {reference_url} and ratified at "
                f"{ratified_at}"))


def add_arguments(parser: Any) -> None:
    """The gate's CLI surface. Exactly the four load-required fields, no more.

    Called from `orchestrate.py`'s parser so the flag set has one home.
    `--benchmark` already exists there and is NOT redeclared here.
    """
    parser.add_argument(
        "--reference-url",
        help="commission a benchmark from this reference site (Task B2). The "
             "product is ratified: false and does not build without --ratify.")
    parser.add_argument(
        "--benchmark-captured-at", metavar="YYYY-MM-DD",
        help="capture date for --reference-url. Required with it; never the "
             "clock, so the same corpus compiles to the same bytes.")
    parser.add_argument(
        "--ratify", action="store_true",
        help="ratify the resolved benchmark. The operator act that supplies "
             "the fields no tool can measure.")
    parser.add_argument(
        "--ratified-at", metavar="YYYY-MM-DD",
        help="date of the ratification. Required with --ratify.")
    for f in RATIFY_FIELDS:
        parser.add_argument(
            f.flag, dest=f.dest,
            choices=list(f.choices) if f.choices else None,
            metavar=None if f.choices else "#rrggbb",
            help=f"declare {f.dotted} at ratification (required by "
                 f"design_system.load_benchmark; not measurable).")
