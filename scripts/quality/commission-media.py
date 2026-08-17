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

from lib.image_jobs import job_hash                      # noqa: E402
from lib.media_cache import cache_path, resolve_cached   # noqa: E402

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
    provider = _fake_provider if fake else _run_pipeline

    summary = {"total": len(jobs), "cached": 0, "would_generate": 0,
               "generated": 0, "failed": 0, "skipped": 0,
               "estimates": [], "cache_dir": str(cache), "dry_run": a.dry_run}

    for entry in jobs:
        h, job = entry["job_hash"], entry["job"]
        demands = len(entry.get("demands") or [])
        label = "%s  %s  (%d section%s)" % (
            h, job.get("id", "?"), demands, "" if demands == 1 else "s")

        if resolve_cached(cache, h) is not None:
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

    print("\n  %d job(s): %d cached, %d generated, %d would-generate, "
          "%d failed, %d skipped"
          % (summary["total"], summary["cached"], summary["generated"],
             summary["would_generate"], summary["failed"], summary["skipped"]))
    if a.json:
        print(json.dumps(summary))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
