#!/usr/bin/env python3
"""
Layer 9: Go-Live — set Vercel env vars and optionally trigger redeploy.
Requires Vercel CLI or Vercel API token (VERCEL_TOKEN) and project link.

Usage:
  python layer9_go_live.py --project-dir output/PROJECT/site --shopify-config path/to/shopify_config.json
  python layer9_go_live.py --project-dir output/PROJECT/site --env-only  # only print env for manual set
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WEB_BUILDER_ROOT = Path(__file__).resolve().parent.parent

# Match Vercel deploy URLs (Production: https://... or Aliased: https://...)
VERCEL_URL_PATTERN = re.compile(r"https://[a-zA-Z0-9][-a-zA-Z0-9.]*\.vercel\.app(?:\s|$|[\]\)])")


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 9: Go-Live")
    parser.add_argument("--project-dir", type=Path, default=None, help="output/PROJECT/site (Next.js app)")
    parser.add_argument("--app-dir", type=Path, default=None, help="Alias for --project-dir")
    parser.add_argument("--shopify-config", type=Path, default=None, help="shopify_config.json path")
    parser.add_argument("--env-only", action="store_true", help="Only print env vars for manual set")
    parser.add_argument("--deploy", action="store_true", help="Run vercel --prod (default when not --env-only)")
    args = parser.parse_args()
    project_dir = (args.app_dir or args.project_dir)

    if not project_dir:
        print("Provide --project-dir or --app-dir", file=sys.stderr)
        return 1
    project_dir = project_dir.resolve()
    if not (project_dir / "package.json").exists():
        print("Project dir must contain package.json", file=sys.stderr)
        return 1

    env_vars: dict[str, str] = {}
    if args.shopify_config and args.shopify_config.exists():
        config = json.loads(args.shopify_config.read_text(encoding="utf-8"))
        domain = (config.get("store_domain") or "").strip()
        token = (config.get("storefront_access_token") or "").strip()
        if domain:
            env_vars["SHOPIFY_STORE_DOMAIN"] = domain
        if token and not token.startswith("["):
            env_vars["SHOPIFY_STOREFRONT_ACCESS_TOKEN"] = token

    if args.env_only:
        for k, v in env_vars.items():
            print(f"{k}={v}")
        print("\nSet these on Vercel project (Dashboard > Settings > Environment Variables) or:")
        print("  vercel env add SHOPIFY_STORE_DOMAIN")
        print("  vercel env add SHOPIFY_STOREFRONT_ACCESS_TOKEN")
        return 0

    if not env_vars:
        print("No shopify_config.json or missing store_domain/storefront_access_token", file=sys.stderr)
        return 1

    # Vercel CLI: link project first, then add env
    for key, value in env_vars.items():
        try:
            subprocess.run(
                ["vercel", "env", "add", key, "production", "--force"],
                cwd=project_dir,
                input=value + "\n",
                text=True,
                capture_output=True,
                timeout=10,
            )
        except FileNotFoundError:
            print("Vercel CLI not found. Install: npm i -g vercel", file=sys.stderr)
            print("Or set env vars manually in Vercel Dashboard.", file=sys.stderr)
            for k, v in env_vars.items():
                print(f"  {k}=***")
            return 1
        except subprocess.TimeoutExpired:
            print(f"Timeout setting {key}", file=sys.stderr)

    if args.deploy:
        r = subprocess.run(
            ["vercel", "--prod", "--yes"],
            cwd=project_dir,
            timeout=300,
            capture_output=True,
            text=True,
        )
        combined = (r.stdout or "") + "\n" + (r.stderr or "")
        if r.returncode != 0:
            print(combined, file=sys.stderr)
            print("Deploy failed. Check Vercel CLI and project link.", file=sys.stderr)
            return 1
        # Parse deploy URL for pipeline (Gate D/E)
        # Prefer the "Aliased:" URL (production alias, no deployment protection)
        # over the "Production:" URL (deployment-specific, may have protection)
        deploy_url: str | None = None
        for line in combined.splitlines():
            m = VERCEL_URL_PATTERN.search(line)
            if m:
                url_candidate = m.group(0).strip().rstrip("]) \t\n")
                deploy_url = url_candidate  # keep updating — last match wins
        if deploy_url:
            deploy_url = deploy_url.strip().rstrip("])")
            print(f"AURELIX_DEPLOY_URL={deploy_url}")
        print("Deployed. URL is shown above (or set GATE_D_URL from Vercel dashboard).", file=sys.stderr)
    else:
        print("Env vars set. Run with --deploy or 'vercel --prod' in project dir to deploy.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
