"""The process exit code must carry what main() decided.

`main()` was invoked as a bare call, so every `return` inside it was discarded
and the interpreter exited 0. The one early return in main() is the guard that
refuses to `rmtree` a tenant checkout: it printed a refusal and then reported
success, so a chain reading the exit code proceeded as though the directory had
been cleaned.

A second collision: argparse exits 2 on a usage error, and 2 is
EXIT_REVIEW_NEEDED — "the build completed, a human should look at it". A
mistyped flag must not be readable as a completed build.

These tests drive the real CLI in a subprocess, because the defect lives in the
entry point and is invisible from inside the module.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
ORCHESTRATE = SCRIPTS / "orchestrate.py"

# Imported rather than retyped so a change to the constants breaks the test.
sys.path.insert(0, str(SCRIPTS))
from orchestrate import (  # noqa: E402
    EXIT_FAILED,
    EXIT_NOT_MEASURED,
    EXIT_OK,
    EXIT_REVIEW_NEEDED,
    EXIT_USAGE,
)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ORCHESTRATE), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.fixture()
def repo_shaped_output(tmp_path: Path) -> Path:
    """An --output-root holding <project>/ that is a git checkout."""
    root = tmp_path / "scratch-root"
    (root / "tenant-site" / ".git").mkdir(parents=True)
    (root / "tenant-site" / "TENANT.yaml").write_text("slug: tenant-site\n", encoding="utf-8")
    return root


def test_clean_refusal_on_a_git_repo_exits_non_zero(repo_shaped_output: Path, tmp_path: Path):
    proc = _run(
        [
            "tenant-site",
            "--clean",
            "--target-platform",
            "vercel",
            "--output-root",
            str(repo_shaped_output),
        ],
        cwd=SCRIPTS.parent,
    )
    assert "REFUSING --clean" in proc.stdout, proc.stdout[-2000:]
    assert proc.returncode != EXIT_OK, (
        "the guard refused and the process still reported success; "
        f"exit={proc.returncode}"
    )


def test_clean_refusal_carries_the_failed_code_not_review_needed(repo_shaped_output: Path):
    """A refusal is a failure, not 'built, needs review'."""
    proc = _run(
        [
            "tenant-site",
            "--clean",
            "--target-platform",
            "vercel",
            "--output-root",
            str(repo_shaped_output),
        ],
        cwd=SCRIPTS.parent,
    )
    assert proc.returncode == EXIT_FAILED, (
        f"expected EXIT_FAILED={EXIT_FAILED}, got {proc.returncode}"
    )


def test_the_refusal_did_not_delete_the_checkout(repo_shaped_output: Path):
    _run(
        [
            "tenant-site",
            "--clean",
            "--target-platform",
            "vercel",
            "--output-root",
            str(repo_shaped_output),
        ],
        cwd=SCRIPTS.parent,
    )
    assert (repo_shaped_output / "tenant-site" / ".git").is_dir()
    assert (repo_shaped_output / "tenant-site" / "TENANT.yaml").is_file()


def test_usage_error_is_distinguishable_from_review_needed():
    proc = _run(["--no-such-flag"], cwd=SCRIPTS.parent)
    assert proc.returncode != EXIT_OK
    assert proc.returncode != EXIT_REVIEW_NEEDED, (
        "an argparse usage error exits with EXIT_REVIEW_NEEDED, so a mistyped "
        "flag reads as 'build completed, review needed'"
    )
    assert proc.returncode == EXIT_USAGE


def test_missing_required_argument_is_a_usage_error():
    proc = _run([], cwd=SCRIPTS.parent)
    assert proc.returncode == EXIT_USAGE, proc.stderr[-2000:]


def test_help_still_exits_zero():
    proc = _run(["--help"], cwd=SCRIPTS.parent)
    assert proc.returncode == EXIT_OK


def test_exit_codes_are_all_distinct():
    codes = [EXIT_OK, EXIT_FAILED, EXIT_REVIEW_NEEDED, EXIT_NOT_MEASURED, EXIT_USAGE]
    assert len(set(codes)) == len(codes), codes
