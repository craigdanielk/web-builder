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


def _deploy_env_manifest(target_platform: str, shopify_config: Path | None) -> dict:
    """The target adapter's env manifest.

    The adapters live in `orchestrate.py`, which is the one authority on what a
    deploy target needs. Imported lazily so `--help` and the arg parsing do not
    pay for a 10k-line import, and so a tree without it still runs this script
    with an honest, empty manifest rather than a Shopify-shaped assumption.
    """
    config: dict | None = None
    if shopify_config and shopify_config.exists():
        config = json.loads(shopify_config.read_text(encoding="utf-8"))

    sys.path.insert(0, str(WEB_BUILDER_ROOT / "scripts"))
    try:
        from orchestrate import _resolve_adapter, platform_modules
    except Exception as exc:  # noqa: BLE001 - report, never guess a platform
        print(f"Could not load deploy adapters ({exc})", file=sys.stderr)
        return {
            "platform": target_platform, "source": "unavailable",
            "declared": [], "values": {}, "unvalued": [],
            "reads_shopify_config": False,
        }
    adapter = _resolve_adapter(target_platform)
    return adapter.deploy_env(
        shopify_config=config, modules=platform_modules(adapter.name)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 9: Go-Live")
    parser.add_argument("--project-dir", type=Path, default=None, help="output/PROJECT/site (Next.js app)")
    parser.add_argument("--app-dir", type=Path, default=None, help="Alias for --project-dir")
    parser.add_argument("--shopify-config", type=Path, default=None, help="shopify_config.json path")
    parser.add_argument("--env-only", action="store_true", help="Only print env vars for manual set")
    parser.add_argument("--deploy", action="store_true", help="Run vercel --prod (default when not --env-only)")
    parser.add_argument(
        "--target-platform", default="shopify",
        help="Deploy target whose adapter supplies the env manifest (default shopify, "
             "which preserves the historical behaviour of this script)",
    )
    args = parser.parse_args()
    project_dir = (args.app_dir or args.project_dir)

    if not project_dir:
        print("Provide --project-dir or --app-dir", file=sys.stderr)
        return 1
    project_dir = project_dir.resolve()
    if not (project_dir / "package.json").exists():
        print("Project dir must contain package.json", file=sys.stderr)
        return 1

    # Env comes from the target's adapter (P2), not from this script reading a
    # Shopify artifact. Until then, `env_vars` was populated ONLY from
    # shopify_config.json and an empty result was `return 1` — so a correct
    # Vercel build for a tenant with no storefront failed Layer 9 on the absence
    # of a file that target never produces.
    manifest = _deploy_env_manifest(args.target_platform, args.shopify_config)
    env_vars: dict[str, str] = dict(manifest["values"])

    if args.env_only:
        for k, v in env_vars.items():
            print(f"{k}={v}")
        for name in manifest["unvalued"]:
            print(f"# {name}=  (declared, not valued here)")
        print("\nSet these on Vercel project (Dashboard > Settings > Environment Variables) or:")
        for name in manifest["declared"] or env_vars:
            print(f"  vercel env add {name}")
        return 0

    if not env_vars:
        # An empty manifest is only a failure when this target declares env it
        # should have been able to value. A target that declares none is
        # complete with none — that is not a NOT_MEASURED and not a failure.
        if manifest["declared"]:
            print(
                f"{manifest['platform']}: {len(manifest['unvalued'])} declared env var(s) "
                f"unvalued from {manifest['source']} — "
                + ", ".join(manifest["unvalued"]),
                file=sys.stderr,
            )
            return 1
        print(f"{manifest['platform']}: no env declared by this target; nothing to set.")

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
    elif env_vars:
        print(f"{len(env_vars)} env var(s) set. Run with --deploy or 'vercel --prod' to deploy.")
    else:
        # "Env vars set." printed here regardless of whether any were, which is
        # the class of message this repo bans: true when written, false by the
        # time anything reads it.
        print("No env vars to set. Run with --deploy or 'vercel --prod' to deploy.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
