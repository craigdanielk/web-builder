"""
Gate A — Token Sanitization Gate

Runs after assembly/sanitization, before deploy.
Fails the pipeline if any unsanitized content tokens remain in the generated site.

Uses the audit_tokens.py audit() function from the testing directory as the
detection engine, and the sanitizer module as the remediation engine.

Usage:
    from scripts.lib.gate_a import check_gate_a

    result = check_gate_a("/path/to/site")
    if not result["passed"]:
        print(f"Gate A FAILED: {result['count']} unsanitized tokens")
        for f in result["findings"]:
            print(f"  {f['file']}:{f['line']} — {f['token']}")
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure testing/ and web-builder/scripts/ are importable
_repo_root = Path(__file__).resolve().parent.parent.parent.parent
_testing_dir = _repo_root / "testing"
_scripts_dir = Path(__file__).resolve().parent.parent

if str(_testing_dir) not in sys.path:
    sys.path.insert(0, str(_testing_dir))
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))


def check_gate_a(
    site_dir: str | Path,
    context: dict | None = None,
    auto_fix: bool = True,
    max_passes: int = 2,
) -> dict:
    """Run Gate A token sanitization check.

    1. Runs audit_tokens.audit() to detect unsanitized tokens.
    2. If auto_fix=True and tokens found, runs sanitizer then re-audits.
    3. Returns pass/fail with details.

    Args:
        site_dir: Path to the generated site directory.
        context: Optional build context for the sanitizer.
        auto_fix: If True, attempt to fix tokens before failing.
        max_passes: Maximum sanitization+audit cycles.

    Returns:
        Dict with keys: passed (bool), count (int), findings (list),
        auto_fixed (int), passes_run (int).
    """
    from audit_tokens import audit
    from lib.sanitizer import sanitize_directory

    site_path = Path(site_dir)
    total_auto_fixed = 0

    for pass_num in range(1, max_passes + 1):
        findings = audit(site_path)

        if not findings:
            return {
                "passed": True,
                "count": 0,
                "findings": [],
                "auto_fixed": total_auto_fixed,
                "passes_run": pass_num,
            }

        if auto_fix and pass_num < max_passes:
            result = sanitize_directory(site_path, context)
            total_auto_fixed += result["total_replacements"]
            if result["total_replacements"] == 0:
                # Sanitizer couldn't fix anything more; stop trying
                break
        else:
            break

    # Final audit
    findings = audit(site_path)

    return {
        "passed": len(findings) == 0,
        "count": len(findings),
        "findings": findings,
        "auto_fixed": total_auto_fixed,
        "passes_run": max_passes,
    }


def run_gate_a_cli(site_dir: str | Path, context: dict | None = None) -> int:
    """CLI-friendly gate check. Returns exit code 0 (pass) or 1 (fail)."""
    result = check_gate_a(site_dir, context=context, auto_fix=True)

    if result["auto_fixed"] > 0:
        print(f"[Gate A] Auto-fixed {result['auto_fixed']} token(s)")

    if result["passed"]:
        print(f"[Gate A] PASS: No unsanitized tokens in {site_dir}")
        return 0

    print(f"[Gate A] FAIL: {result['count']} unsanitized token(s) remain in {site_dir}")
    for f in result["findings"]:
        print(f"  {f['file']}:{f['line']} — {f['token']}")
        print(f"    {f['context']}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m lib.gate_a <site_dir>", file=sys.stderr)
        sys.exit(1)
    sys.exit(run_gate_a_cli(sys.argv[1]))
