#!/usr/bin/env python3
"""Gate: the emitted CMS/email rails compile, and every route they claim exists.

THREE OUTCOMES, and the third is the one that matters.

  PASS          `next build` succeeded and every route in `rails-emission.json`
                is in the build output.
  FAIL          the rails were emitted and are broken — the build failed, a
                claimed route is missing, or the emission manifest is absent
                after an emission. FATAL by default (exit 1).
  NOT_MEASURED  nothing could be measured: no node_modules, no npm, the build
                timed out. Exit 3. **NOT a pass.** The repo's standing rule is
                that a gate which cannot apply must be absent from the chain,
                never skipped-with-a-warning; here the stage DID apply and the
                measurement did not happen, which is a distinct third answer and
                must not be reported as the first.

A tenant that declares no `cms` has no `rails-emission.json`, and this gate is
then ABSENT — not run and not reported. That is the caller's decision (see
`stage_deploy`), deliberately not a fourth exit code here: a gate that reports
"skipped" in a status list reads as a gate that passed.

What this gate does NOT check: any secret. `RESEND_API_KEY` is declared-not-valued
by design, and its absence is a runtime condition the emitted sender reports for
itself (`notifyUnconfiguredReason`) and the /admin/leads un-notified count makes
visible. Failing a build on a missing mailbox key would block a whole site on a
credential that is deliberately supplied later.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_NOT_MEASURED = 3


def _routes_in_build(site_dir: Path) -> set[str] | None:
    """Routes Next actually built, or None when the output cannot be read."""
    next_dir = site_dir / ".next"
    manifest = next_dir / "app-path-routes-manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        # values are the public paths ("/admin", "/api/contact"); "/" for root.
        return {str(v) for v in data.values()}
    # Fall back to the compiled tree, so a Next version that renames the
    # manifest degrades to a weaker check rather than to NOT_MEASURED.
    app = next_dir / "server" / "app"
    if not app.is_dir():
        return None
    found: set[str] = set()
    for path in app.rglob("*.js"):
        if path.stem not in ("page", "route"):
            continue
        rel = path.parent.relative_to(app).as_posix()
        found.add("/" + rel if rel != "." else "/")
    return found


def run_gate(site_dir: Path, output_dir: Path, *, timeout: int = 900) -> dict:
    """Measure, and return the verdict record written to `rails-gate.json`."""
    emission_path = output_dir / "rails-emission.json"
    if not emission_path.exists():
        return {
            "verdict": "FAIL",
            "reasons": [
                f"{emission_path} is absent. This gate is only run for a tenant that "
                "declares cms, and a declaring tenant whose emission left no manifest "
                "emitted nothing measurable."
            ],
        }
    emission = json.loads(emission_path.read_text())
    claimed = list(emission.get("routes") or [])
    reasons: list[str] = []

    # ── every emitted file is still on disk ──
    missing_files = [f for f in emission.get("files", []) if not (site_dir / f).exists()]
    if missing_files:
        reasons.append(
            f"{len(missing_files)} emitted file(s) missing from the site: "
            + ", ".join(sorted(missing_files)[:10])
        )

    if not (site_dir / "node_modules").is_dir():
        # A missing FILE is a measured fact and survives into this verdict — an
        # unmeasurable compile does not erase what was already established. Dropping
        # `reasons` here would report a broken emission as "nothing is known".
        return {
            "verdict": "FAIL" if missing_files else "NOT_MEASURED",
            "reasons": reasons + [
                "node_modules is absent — `next build` cannot run, so nothing was "
                "compiled and nothing is known about whether it compiles."
            ],
            "emitted_files": len(emission.get("files", [])),
            "routes_claimed": claimed,
        }

    env = dict(os.environ)
    # NODE_ENV=development in the shell makes Next 16 fail with a useContext
    # null error that looks like a code defect (see web-builder/CLAUDE.md).
    env["NODE_ENV"] = "production"
    try:
        proc = subprocess.run(
            ["npx", "--no-install", "next", "build"],
            cwd=str(site_dir), capture_output=True, text=True, timeout=timeout, env=env,
        )
    except FileNotFoundError:
        return {
            "verdict": "NOT_MEASURED",
            "reasons": ["npx not on PATH — the compile was never attempted."],
            "routes_claimed": claimed,
        }
    except subprocess.TimeoutExpired:
        return {
            "verdict": "NOT_MEASURED",
            "reasons": [f"`next build` exceeded {timeout}s and was killed; the result "
                        "is unknown, which is not the same as broken."],
            "routes_claimed": claimed,
        }

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-3000:]
        reasons.append(f"`next build` exited {proc.returncode}")
        return {
            "verdict": "FAIL",
            "reasons": reasons,
            "build_exit_code": proc.returncode,
            "build_output_tail": tail,
            "routes_claimed": claimed,
        }

    built = _routes_in_build(site_dir)
    if built is None:
        reasons.append("`next build` succeeded but its route manifest could not be read")
        return {"verdict": "NOT_MEASURED", "reasons": reasons, "routes_claimed": claimed}

    absent = [r for r in claimed if r not in built]
    if absent:
        reasons.append(
            "emitted route(s) absent from the build output: " + ", ".join(absent)
        )

    return {
        "verdict": "FAIL" if reasons else "PASS",
        "reasons": reasons,
        "build_exit_code": 0,
        "routes_claimed": claimed,
        "routes_built": sorted(built),
        "emitted_files": len(emission.get("files", [])),
        "puck_config_verdict": (emission.get("puck_config") or {}).get("verdict"),
        "undeclared_fields": emission.get("undeclared_fields", []),
    }


def write_verdict(output_dir: Path, verdict: dict) -> Path:
    path = output_dir / "rails-gate.json"
    path.write_text(json.dumps(verdict, indent=2) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--site-dir", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args(argv)

    verdict = run_gate(args.site_dir, args.output_dir, timeout=args.timeout)
    path = write_verdict(args.output_dir, verdict)
    print(f"VERIFY RAILS GATE: {verdict['verdict']}")
    for reason in verdict.get("reasons", []):
        print(f"  - {reason}")
    print(f"  verdict written to {path}")
    return {"PASS": EXIT_PASS, "FAIL": EXIT_FAIL}.get(
        verdict["verdict"], EXIT_NOT_MEASURED
    )


if __name__ == "__main__":
    sys.exit(main())
