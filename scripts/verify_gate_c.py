#!/usr/bin/env python3
"""
VERIFY GATE C: Generated app is ready for deployment.
- Expected app structure (app or src/app with page.tsx)
- npm run build succeeds in generated app dir
- Without --app-dir there is no generated app: NOT_MEASURED (exit 3), never PASS.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

WEB_BUILDER_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.capability import describe  # noqa: E402

# Exit codes: 0 PASS - 1 FAIL - 3 NOT_MEASURED. NOT_MEASURED is not PASS.
NOT_MEASURED = 3

# `npm run build` is killed after this many seconds. A build that runs longer has
# not been measured — it has not been shown to be broken either.
BUILD_TIMEOUT = 180

# What this gate is, in its own words. Compiled into the capability register by
# `scripts/capability_register.py`; see that file for why it lives here.
CAPABILITY = {
    "id": "aurelix.gate.verify-c",
    "name": "Gate C — the generated app exists and compiles",
    "kind": "gate",
    "invocation": "python3 scripts/verify_gate_c.py --site-dir <output/PROJECT/site>",
    "preconditions": [
        "a generated app directory produced by a build (orchestrate.py <project>)",
        "npm on PATH and node_modules installed inside that app dir — `npm run build` "
        "is run there directly, this gate installs nothing",
    ],
    "inputs": [
        "--site-dir / --app-dir: the generated app directory",
        "that dir's package.json and app/page.tsx or src/app/page.tsx",
    ],
    "outputs": [],
    "outcome": "whether the generated Next.js app has the expected entry structure and "
               "whether `npm run build` succeeds inside it",
    "exit_contract": {
        0: "PASS — structure present and `npm run build` returned 0",
        1: "FAIL — no package.json, no app/page.tsx or src/app/page.tsx, or the build exited non-zero",
        3: "NOT_MEASURED — no --site-dir/--app-dir was given, so there is no generated app to "
           "verify. This branch used to inspect the web-builder's OWN lib/shopify template "
           "files and print PASS; NOT_MEASURED is not PASS. ALSO returned when the app dir "
           "was given but the build could not be measured: `npm run build` exceeded the 180s "
           "timeout and was killed, or npm is not on PATH. Both used to escape main() as a "
           "traceback, which a status list reads as FAIL",
    },
    "measures": [
        "presence of package.json in the app dir",
        "presence of an App Router entry: app/page.tsx or src/app/page.tsx",
        "the exit code of `npm run build` with NODE_ENV=production, 180s timeout — a build "
        "that exceeds it is killed and reported as NOT_MEASURED, never as FAIL",
    ],
    "cannot_see": [
        "anything at all without --site-dir/--app-dir — the no-argument branch measures "
        "nothing and returns 3; a chain that treats 3 as a pass has an unbuilt app",
        "WHY a build failed beyond the first 800 characters of stderr, which is all it prints",
        "whether the compiled output is correct — a build that succeeds while rendering an "
        "empty page passes here; that is the render audit's and the conformance gate's job",
        "type errors that `next build` does not surface (a project with typescript.ignoreBuildErrors "
        "compiles green); the compile gate reads tsc, this gate reads npm's exit code",
        "WHY a build exceeded the timeout — it is killed and reported NOT_MEASURED with the "
        "limit stated, and the partial stdout/stderr of the killed process is discarded",
        "the Pages Router, and any entry file other than the two paths hardcoded above",
    ],
    "reachable_from": [
        "run_pipeline.py:612 (stage_gate_c, both the shopify and vercel chains)",
        "scripts/test_gate_outcomes.py:28",
        "standalone CLI",
    ],
    "cost": "seconds with no app dir; a full `npm run build` (tens of seconds to minutes) with one",
}


def main() -> int:
    if describe(CAPABILITY):
        return 0

    parser = argparse.ArgumentParser(description="VERIFY GATE C: generated app structure + build")
    parser.add_argument("--site-dir", type=Path, default=None, help="Generated app dir (output/PROJECT/site)")
    parser.add_argument("--app-dir", type=Path, default=None, help="Alias for --site-dir")
    args = parser.parse_args()
    app_dir = args.app_dir or args.site_dir

    if app_dir:
        app_dir = app_dir.resolve()
        if not (app_dir / "package.json").exists():
            print(f"FAIL: Gate C: no package.json in {app_dir}", file=sys.stderr)
            return 1
        app_router = app_dir / "app" / "page.tsx"
        src_app = app_dir / "src" / "app" / "page.tsx"
        if not app_router.exists() and not src_app.exists():
            print(f"FAIL: Gate C: expected app/page.tsx or src/app/page.tsx in {app_dir}", file=sys.stderr)
            return 1
        env = os.environ.copy()
        env["NODE_ENV"] = "production"
        try:
            r = subprocess.run(
                ["npm", "run", "build"],
                cwd=app_dir,
                capture_output=True,
                text=True,
                timeout=BUILD_TIMEOUT,
                env=env,
            )
        except subprocess.TimeoutExpired:
            # A timeout is the definition of "I could not measure": the build was
            # killed mid-flight, so nothing is known about whether it compiles.
            # Letting TimeoutExpired escape reported that as a traceback and a
            # non-zero exit, which a status list cannot tell apart from FAIL.
            print(
                f"VERIFY GATE C: NOT_MEASURED - `npm run build` exceeded "
                f"{BUILD_TIMEOUT}s in {app_dir} and was killed; the result is "
                f"unknown, which is not the same as broken"
            )
            return NOT_MEASURED
        except FileNotFoundError:
            # Same class of defect: npm absent raised out of main() as a
            # traceback. Nothing was compiled, so nothing is known.
            print(
                f"VERIFY GATE C: NOT_MEASURED - npm is not on PATH, so "
                f"`npm run build` was never attempted in {app_dir}"
            )
            return NOT_MEASURED
        if r.returncode != 0:
            print(f"FAIL: Gate C: npm run build failed: {r.stderr[:800]}", file=sys.stderr)
            return 1
        print("VERIFY GATE C: PASS")
        print(f"  App dir: {app_dir}")
        print("  npm run build: OK")
        return 0

    # No app dir: nothing was built, so nothing can be verified. The old
    # behaviour here checked the web-builder's own lib/shopify template files
    # and reported PASS — success for a generated app that does not exist.
    print(
        "VERIFY GATE C: NOT_MEASURED - no generated app to verify; "
        "pass --site-dir (or --app-dir) pointing at output/PROJECT/site"
    )
    return NOT_MEASURED


if __name__ == "__main__":
    sys.exit(main())
