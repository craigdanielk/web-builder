#!/usr/bin/env python3
"""Commission the pictures a build asked for. Hand-run, out of band, cached.

    python3 scripts/quality/commission-media.py \
        --jobs output/<project>/image-jobs.json \
        --cache tenants/<tenant>/assets/generated \
        --dry-run                 # cost estimate; no credits, no files
    ... same command without --dry-run to spend.

**Python, not Node** (the plan offered either): the job specs, the hash, the
schema and the runner it shells out to are all Python, and `run_job.py` is
importable — a Node commissioner would have to re-implement `job_hash` in a
second language, which is exactly the way two implementations of one digest
drift apart and a cache silently stops hitting.

Three properties, in order of how much they matter:

1. **A cached hash is never regenerated.** The cache is checked before the
   provider is looked at, so a rebuild — or a rerun after a crash halfway
   through the set — costs nothing. This is the difference between a cache and
   a folder of pictures.
2. **`--dry-run` spends nothing.** It resolves the same set, skips the same
   hits, and asks the provider only for a cost estimate.
3. **This file is not on the build path.** `orchestrate.py` neither imports nor
   invokes it; the build reads the cache and reports a miss. Verified by a
   grep assertion in `scripts/test_media_cache.py`, because "we agreed not to"
   is not a mechanism.

The provider is reached through `services/image-pipeline/core/run_job.py` — the
deterministic runner, which compiles the spec, records a compile hash, and
persists through its own output adapter. Calling the Higgsfield CLI directly
from here would produce an image outside the cache chain that nobody could
reproduce.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB_BUILDER = HERE.parent.parent
sys.path.insert(0, str(WEB_BUILDER / "scripts"))

from lib.image_jobs import (                             # noqa: E402
    job_hash, media_type_of, ENGINE_REMOTION, ENGINE_GENERATIVE,
    MEDIA_TYPE_VIDEO,
)
from lib.media_cache import cache_path, resolve_cached   # noqa: E402
from lib.capability import describe                      # noqa: E402

#: What this commissioner is, in its own words. Compiled into the capability
#: register by `scripts/capability_register.py`.
#:
#: THIS IS THE ONE INSTRUMENT IN THIS SHARD THAT SPENDS MONEY. Without
#: `--dry-run` it calls the higgsfield CLI through the image-pipeline runner and
#: consumes generation credits, one charge per uncached job.
CAPABILITY = {
    "id": "aurelix.generator.media-commission",
    "name": "Media commissioner — generate the pictures a build asked for",
    "kind": "generator",
    "invocation": (
        "python3 scripts/quality/commission-media.py --jobs output/<project>/image-jobs.json "
        "--cache tenants/<tenant>/assets/generated [--dry-run] [--only <hash,...>] [--json]"
    ),
    "preconditions": [
        "image-jobs.json must hold LOWERED job specs ({jobs: [{job_hash, job, demands}]}); a bare "
        "gap list is refused by name — rebuild with a stage_resolve_assets that calls to_job_v1",
        "every entry's recorded job_hash must equal job_hash(spec), or the run aborts: a cache keyed "
        "on a stale hash is a cache keyed on a lie",
        "for stills and generative motion: the image-pipeline checkout at $IMAGE_PIPELINE_ROOT "
        "(default ~/Developer/GitHub/services/image-pipeline), and an AUTHENTICATED `higgsfield` CLI "
        "session — `hf auth login`. There is no API-key env var; the credential is the CLI's session",
        "for remotion motion jobs: web-builder/motion/node_modules installed (`npm install`)",
        "WITHOUT --dry-run this SPENDS GENERATION CREDITS, one charge per uncached job",
    ],
    "inputs": [
        "output/<project>/image-jobs.json — the lowered job specs the build emitted",
        "the cache directory, checked before the provider is even looked at",
    ],
    "outputs": [
        "one file per generated job at <cache>/<job_hash>.<ext> — exactly one legal name per hash, "
        "staged through a tempdir so the runner's auto-incrementing versions never accumulate",
        "a per-job console ledger and, with --json, a machine-readable summary as the last line",
    ],
    "outcome": (
        "how many of the build's demanded images/videos already exist in the cache, what the "
        "uncached ones would cost (--dry-run), and — when told to spend — which were produced, "
        "which failed, and which are UNRENDERED with a named reason"
    ),
    "exit_contract": {
        "0": "done — every job cached, generated, estimated or explicitly skipped",
        "1": "at least one job FAILED (the provider errored or produced no file); also the refusals "
             "raised as SystemExit: a bare gap list, or a job_hash mismatch",
        "2": "argparse usage error (a missing --jobs / --cache). argparse's own exit",
        "3": "NOT_MEASURED — at least one job is UNRENDERED with a reason (missing remotion "
             "node_modules, a missing entry, or generative motion, whose cost was never measured). "
             "Folding this into 0 would make a missing toolchain read as a completed commission",
    },
    "measures": [
        "cache hit/miss per job_hash, before any provider is consulted — this is what makes a rerun "
        "after a crash cost nothing",
        "a provider cost estimate per uncached job under --dry-run, reported verbatim, and as the "
        "raw line when it does not parse",
        "which renderer each job belongs to, from media_type + motion.engine",
    ],
    "cannot_see": [
        "whether the image it commissioned is any GOOD, on brief, or even depicts the subject. It "
        "moves exactly one produced file to <hash>.<ext> and never looks at the pixels; a provider "
        "that returns a plausible wrong picture is indistinguishable from success here",
        "whether the build will use what it generated. This file is deliberately OFF the build path "
        "— orchestrate.py neither imports nor invokes it (asserted by a grep in "
        "scripts/test_media_cache.py) — so a commissioned asset only lands if a later build reads "
        "the cache with the same hash",
        "the cost of generative MOTION. That path is NOT_MEASURED by declaration: the census could "
        "not obtain a price (docs/census/2026-08-17-motion-engine.md §6), so it refuses rather than "
        "spend against an unmeasured figure",
        "that a palette change just invalidated every hash. job_hash digests the palette by design "
        "(lib/image_jobs.py:704), so one token change cache-misses the entire set at once and this "
        "file will happily re-commission all of it",
        "whether the higgsfield session is still authenticated until it fails — an expired login "
        "surfaces as a FAILED job, not as a precondition error",
    ],
    "reachable_from": [
        "hand-run only — by design",
        "scripts/test_media_cache.py:256 and scripts/test_motion_jobs.py:482 (as a subprocess, with "
        "MEDIA_COMMISSION_FAKE_PROVIDER=1)",
    ],
    "cost": (
        "REAL MONEY without --dry-run: generation credits, one charge per uncached job, unbounded "
        "by the number of jobs in the file (use --only to cap it). --dry-run spends nothing and "
        "takes ~1s per uncached job. Remotion motion is compute-only, ~5s per 390 frames warm"
    ),
}

#: The deterministic runner. A sibling service repo, not a submodule — resolved
#: by env override first so a checkout somewhere else still works, and reported
#: as missing rather than assumed.
IMAGE_PIPELINE = Path(
    os.environ.get("IMAGE_PIPELINE_ROOT")
    or (Path.home() / "Developer/GitHub/services/image-pipeline")
)


def _load_jobs(path: Path) -> list:
    """Read `image-jobs.json` and return `[{job_hash, job, demands}]`.

    Accepts the lowered object the build now writes. A bare list of gap rows —
    what this file used to contain, before `to_job_v1` had a caller — is
    refused by name rather than half-understood: those rows are not job specs
    and cannot be generated from.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        raise SystemExit(
            "%s is a bare gap list, not lowered job specs. Rebuild with a "
            "version of stage_resolve_assets that calls to_job_v1." % path)
    jobs = data.get("jobs") or []
    for entry in jobs:
        computed = job_hash(entry["job"])
        if entry.get("job_hash") != computed:
            raise SystemExit(
                "hash mismatch on %s: file says %s, spec hashes to %s. The "
                "cache would be keyed on a lie." % (
                    entry["job"].get("id"), entry.get("job_hash"), computed))
    return jobs


def _run_pipeline(job: dict, out_dir: Path, dry_run: bool) -> dict:
    """Shell out to `core/run_job.py` for one job. Returns its parsed result.

    Shelling out rather than importing: the runner does `sys.path.insert` on
    its own directory and imports a dozen sibling modules by bare name, so
    importing it into this process would put that whole namespace on our path.
    A subprocess keeps the seam honest and keeps a provider crash out of the
    commissioner.
    """
    runner = IMAGE_PIPELINE / "core" / "run_job.py"
    if not runner.exists():
        raise SystemExit(
            "image-pipeline runner not found at %s. Set IMAGE_PIPELINE_ROOT."
            % runner)

    with tempfile.TemporaryDirectory() as tmp:
        spec = dict(job)
        spec.setdefault("output", {})["dir"] = str(out_dir)
        job_file = Path(tmp) / ("%s.job.json" % spec["id"])
        job_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")

        cmd = [sys.executable, str(runner), str(job_file)]
        if dry_run:
            cmd.append("--dry-run")
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              cwd=str(IMAGE_PIPELINE))
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            return {"ok": False, "log": out[-2000:]}
        return {"ok": True, "log": out}


# ── Motion: the second out-of-band renderer ────────────────────────────────
#
# A `media_type: "video"` job with `motion.engine == "remotion"` is rendered by
# the contained Remotion project (`web-builder/motion/`), NOT by the
# image-pipeline runner — there is no prompt and no provider, only a composition
# and its props. Everything else is identical: the cache is checked first, the
# hash names the file, and the build never calls this.
#
# `--dry-run` reports a cost of "compute only". That is the measured fact
# (census §6: 5.0 s for 390 frames warm, no per-render billing), not an
# optimistic default — and it is why the Remotion path can be re-rendered freely
# while a generative one cannot.


def _remotion_project(entry: Path) -> Path:
    """The nearest ancestor of the entry that holds a `package.json`.

    Derived rather than hardcoded to `motion/`: the job declares its entry, and
    a second composition project would otherwise need a code change here.
    """
    for parent in [entry.parent, *entry.parents]:
        if (parent / "package.json").is_file():
            return parent
    raise FileNotFoundError(
        "no package.json above %s — the Remotion entry names no project" % entry)


def _run_remotion(job: dict, out_dir: Path, dry_run: bool) -> dict:
    """Render one Remotion job. Returns `{ok, log}` — and `ok: False` with a
    named reason when the project's dependencies are not installed.

    An uninstalled `motion/node_modules` is an UNRENDERED JOB WITH A REASON, not
    a failure of the contract: the schema, the lowering and the cache are all
    correct and the artefact is simply absent, which is exactly what an
    un-commissioned slot already looks like everywhere else in this system.
    """
    motion = job.get("motion") or {}
    remo = job.get("remotion") or {}
    entry = WEB_BUILDER / str(remo.get("entry") or "")
    if not entry.is_file():
        return {"ok": False, "log": "UNRENDERED: entry %s does not exist" % entry}
    try:
        project = _remotion_project(entry)
    except FileNotFoundError as e:
        return {"ok": False, "log": "UNRENDERED: %s" % e}
    if not (project / "node_modules").is_dir():
        return {"ok": False, "log":
                "UNRENDERED: %s/node_modules is not installed — run `npm "
                "install` in %s. The job spec is valid and uncached; nothing "
                "was spent." % (project.name, project)}

    frames = int(motion.get("duration_frames") or 0)
    if dry_run:
        return {"ok": True, "log":
                "DRY RUN cost estimate: %s" % json.dumps({
                    "engine": ENGINE_REMOTION,
                    "composition": remo.get("composition_id"),
                    "frames": frames,
                    "billing": "compute only — no per-render charge",
                })}

    out_dir.mkdir(parents=True, exist_ok=True)
    container = motion.get("container") or "mp4"
    out_file = out_dir / ("%s.%s" % (job["id"], container))

    with tempfile.TemporaryDirectory() as tmp:
        # Props go to a file, not to an inline --props string: they carry the
        # full token set and the provenance rows, and an argv-length limit is a
        # silently truncated render.
        props_file = Path(tmp) / "props.json"
        props_file.write_text(json.dumps(remo.get("props") or {}, indent=2),
                              encoding="utf-8")
        cmd = [
            "npx", "remotion", "render",
            str(entry.relative_to(project)),
            str(remo.get("composition_id")),
            str(out_file),
            "--props=%s" % props_file,
            "--log=error",
        ]
        # Dimensions and frame rate are AUTHORITATIVE ON THE JOB, so they are
        # passed as overrides rather than left to the composition's defaults.
        # This is what makes a mobile cut a second job rather than a second file
        # name for the same render.
        for flag, key in (("--width", "width"), ("--height", "height"),
                          ("--fps", "fps")):
            if motion.get(key):
                cmd.append("%s=%d" % (flag, int(motion[key])))
        if frames >= 1:
            cmd.append("--frames=0-%d" % (frames - 1))
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              cwd=str(project))
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0 or not out_file.is_file():
            return {"ok": False, "log": out[-2000:] or "remotion produced no file"}
        return {"ok": True, "log": out}


def _run_generative_motion(job: dict, out_dir: Path, dry_run: bool) -> dict:
    """The generative motion path, which is NOT MEASURED and says so.

    The engine policy reserves generation for atmospheric backdrops, and the
    census could not obtain a cost for it (`hf auth` expired; no generation was
    performed and nothing was spent). Rendering into that gap would be spending
    against an unmeasured price, so the job is recorded as unrendered with the
    reason and the command that closes it.
    """
    return {"ok": False, "log":
            "UNRENDERED (NOT_MEASURED): generative motion has no cost-measured "
            "adapter path. docs/census/2026-08-17-motion-engine.md §6 — run "
            "`hf auth login` then `higgsfield generate cost <model> --duration "
            "<s> --json` and report the figure BEFORE any generate. Nothing "
            "was spent."}


def _dispatch(job: dict):
    """Which renderer this job belongs to, by the DEFAULTING discriminator.

    `media_type_of` is the only reader of `media_type` — a bare
    `job["media_type"]` here would turn every existing `job-v1` artefact into a
    KeyError.
    """
    if media_type_of(job) != MEDIA_TYPE_VIDEO:
        return _run_pipeline
    engine = ((job.get("motion") or {}).get("engine") or "").lower()
    if engine == ENGINE_REMOTION:
        return _run_remotion
    if engine == ENGINE_GENERATIVE:
        return _run_generative_motion
    raise SystemExit("job %s declares motion.engine %r, which no renderer "
                     "claims" % (job.get("id"), engine))


def _fake_provider(job: dict, out_dir: Path, dry_run: bool) -> dict:
    """Test double, enabled only by `MEDIA_COMMISSION_FAKE_PROVIDER=1`.

    Exists so the cache/dry-run/refusal logic is testable without a network or
    a credit. It is opt-in via env and never the default: a fallback that
    silently produced fake art would be the fabrication failure this repo keeps
    having, in a new medium.
    """
    if dry_run:
        return {"ok": True, "log": "FAKE dry run"}
    out_dir.mkdir(parents=True, exist_ok=True)
    if media_type_of(job) == MEDIA_TYPE_VIDEO:
        # The container comes from the job, so the fake exercises the same
        # extension the real renderer would cache — a fake that always wrote
        # .png would leave the motion cache path untested.
        container = (job.get("motion") or {}).get("container") or "mp4"
        p = out_dir / ("%s__fake__v1.%s" % (job["id"], container))
        p.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 128)
    else:
        p = out_dir / ("%s__fake__v1.png" % job["id"])
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 128)
    return {"ok": True, "log": "FAKE generated %s" % p}


def _cost_from_log(log: str):
    """Pull the runner's `DRY RUN cost estimate: {...}` line out of its output.

    Reported verbatim when it parses and as the raw line when it does not —
    an unparsed estimate is still evidence, and swallowing it would leave a
    spend decision with nothing behind it.
    """
    for line in (log or "").splitlines():
        if "DRY RUN cost estimate:" in line:
            raw = line.split("DRY RUN cost estimate:", 1)[1].strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
    return None


def main(argv=None):
    if describe(CAPABILITY, argv):
        return 0
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", required=True, help="path to image-jobs.json")
    ap.add_argument("--cache", required=True,
                    help="cache dir, e.g. tenants/<tenant>/assets/generated")
    ap.add_argument("--dry-run", action="store_true",
                    help="cost estimate only — no credits, no files")
    ap.add_argument("--only", default=None,
                    help="comma-separated job hashes to act on (budget control)")
    ap.add_argument("--json", action="store_true",
                    help="print a machine-readable summary as the last line")
    a = ap.parse_args(argv)

    jobs = _load_jobs(Path(a.jobs))
    cache = Path(a.cache)
    only = {h.strip() for h in a.only.split(",")} if a.only else None
    fake = os.environ.get("MEDIA_COMMISSION_FAKE_PROVIDER") == "1"

    summary = {"total": len(jobs), "cached": 0, "would_generate": 0,
               "generated": 0, "failed": 0, "unrendered": 0, "skipped": 0,
               "estimates": [], "cache_dir": str(cache), "dry_run": a.dry_run,
               "by_media_type": {}}

    for entry in jobs:
        h, job = entry["job_hash"], entry["job"]
        demands = len(entry.get("demands") or [])
        media_type = media_type_of(job)
        summary["by_media_type"][media_type] = \
            summary["by_media_type"].get(media_type, 0) + 1
        # Per job, not once for the whole set: one `image-jobs.json` may carry
        # stills and motion, and each goes to its own renderer.
        provider = _fake_provider if fake else _dispatch(job)
        label = "%s  %s  [%s]  (%d section%s)" % (
            h, job.get("id", "?"), media_type, demands,
            "" if demands == 1 else "s")

        if resolve_cached(cache, h, media_type) is not None:
            summary["cached"] += 1
            print("  = cached   %s" % label)
            continue
        if only is not None and h not in only:
            summary["skipped"] += 1
            print("  - skipped  %s  (not in --only)" % label)
            continue

        if a.dry_run:
            summary["would_generate"] += 1
            with tempfile.TemporaryDirectory() as tmp:
                res = provider(job, Path(tmp), dry_run=True)
            cost = _cost_from_log(res.get("log", ""))
            summary["estimates"].append(
                {"job_hash": h, "id": job.get("id"), "sections": demands,
                 "cost": cost, "ok": res["ok"]})
            print("  ? estimate %s -> %s" % (label, json.dumps(cost)[:200]))
            if not res["ok"]:
                print(res["log"][-800:])
            continue

        # Generate into a staging dir, then move exactly one file to
        # <hash>.<ext>. Staging first because the runner's output adapter names
        # files `<id>__<imgtype>__v<N>.png` and auto-increments; the cache has
        # one legal name per hash and must never accumulate versions.
        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp)
            res = provider(job, staging, dry_run=False)
            produced = sorted(p for p in staging.rglob("*") if p.is_file())
            if not res["ok"] and res.get("log", "").startswith("UNRENDERED"):
                # A named, non-fatal absence: the spec is valid, the cache is
                # empty, nothing was spent. Distinguished from FAILED because a
                # missing toolchain and a broken composition are different facts
                # and a status list that conflates them reads as a pass.
                summary["unrendered"] += 1
                print("  ○ UNRENDERED %s" % label)
                print("      %s" % res["log"])
                continue
            if not res["ok"] or not produced:
                summary["failed"] += 1
                print("  ✗ FAILED   %s" % label)
                print(res.get("log", "")[-1500:])
                continue
            src = produced[0]
            dest = cache_path(cache, h, src.suffix.lstrip(".") or "png")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            summary["generated"] += 1
            print("  + generated %s -> %s (%d bytes)"
                  % (label, dest, dest.stat().st_size))

    print("\n  %d job(s) %s: %d cached, %d generated, %d would-generate, "
          "%d failed, %d unrendered, %d skipped"
          % (summary["total"], json.dumps(summary["by_media_type"]),
             summary["cached"], summary["generated"],
             summary["would_generate"], summary["failed"],
             summary["unrendered"], summary["skipped"]))
    if a.json:
        print(json.dumps(summary))
    # Three states, the same three the rest of this repo uses: 1 is a real
    # failure, 3 is NOT_MEASURED (a job that could not be attempted, with its
    # reason printed), 0 is done. Folding 3 into 0 would make a missing
    # toolchain read as a completed commission.
    if summary["failed"]:
        return 1
    if summary["unrendered"]:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
