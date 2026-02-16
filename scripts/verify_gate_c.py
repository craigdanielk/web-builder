#!/usr/bin/env python3
"""
VERIFY GATE C: Generated app is ready for deployment.
- Expected app structure (app or src/app with page.tsx)
- npm run build succeeds in generated app dir
- Optional: lib/shopify/client.ts in template when not using --app-dir
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

WEB_BUILDER_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
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
        r = subprocess.run(
            ["npm", "run", "build"],
            cwd=app_dir,
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )
        if r.returncode != 0:
            print(f"FAIL: Gate C: npm run build failed: {r.stderr[:800]}", file=sys.stderr)
            return 1
        print("VERIFY GATE C: PASS")
        print(f"  App dir: {app_dir}")
        print("  npm run build: OK")
        return 0

    lib_client = WEB_BUILDER_ROOT / "lib" / "shopify" / "client.ts"
    if not lib_client.exists():
        print("FAIL: lib/shopify/client.ts not found", file=sys.stderr)
        return 1
    text = lib_client.read_text(encoding="utf-8")
    if "shopifyFetch" not in text:
        print("FAIL: client.ts does not export shopifyFetch", file=sys.stderr)
        return 1
    print("VERIFY GATE C (template): PASS (lib/shopify present). Use --app-dir for generated app + build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
