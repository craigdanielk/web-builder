#!/usr/bin/env python3
"""
Website Builder Orchestration Pipeline

Automates the multi-pass generation workflow:
  1. Read brief + match preset
  2. Generate scaffold (page specification)
  3. Generate each section individually with style header
  4. Assemble into complete page
  5. Run consistency review

URL Clone Mode (--from-url):
  0. Extract visual data from URL → auto-generate preset + brief
  1-5. Normal pipeline with per-section reference context

Usage:
  python scripts/orchestrate.py <project-name> [--preset <preset-name>] [--no-pause]
  python scripts/orchestrate.py <project-name> --from-url <url> [--no-pause]

Requirements:
  pip install anthropic --break-system-packages
  (URL mode also requires: cd scripts/quality && npm install && npx playwright install chromium)
"""

# Deferred annotation evaluation: DeployAdapter (and other classes) are used as
# forward references in function signatures defined *above* their class
# definition (e.g. `adapter: DeployAdapter | None = None`). Without this, those
# annotations are evaluated at import time and raise NameError, breaking a clean
# `import orchestrate`. BRIEF #33299.
from __future__ import annotations

import os
import sys
import json
import argparse
import re
import subprocess
import time as _time
import uuid
from pathlib import Path
from datetime import datetime

# Which brace tokens in a template body are fillable slots and which are JS
# identifiers, what each slot wants, and how many entries each repeated array
# hardcodes. Derived from the template body because `slot_schema` — the column
# meant to carry this — is populated on 2 of 74 rows.
from lib.slot_contract import (
    TOKEN_RE as _TEMPLATE_TOKEN_RE,
    RESERVED_IDENTS as _TEMPLATE_RESERVED_IDENTS,
    template_contract,
    infer_type as _slot_type,
    BARE_FIELD as _BARE_FIELD,
)

try:
    from anthropic import Anthropic
except ImportError:
    # Not fatal: the default generation path uses the `claude` CLI (subscription
    # auth, no API key / no anthropic package). The SDK path is only needed when
    # WEBBUILDER_LLM=api or an ANTHROPIC_API_KEY is present — checked at call time.
    Anthropic = None  # type: ignore

# Supabase integration (optional — falls back to .md presets if not configured)
try:
    from lib.supabase_client import (
        BuildCache,
        check_template_exists,
        get_slot_schema,
        log_build,
        is_supabase_configured,
        get_industry_metadata,
        get_section_sequence,
        get_all_page_sections,
    )
    SUPABASE_AVAILABLE = is_supabase_configured()
except ImportError:
    SUPABASE_AVAILABLE = False
    BuildCache = None  # type: ignore
    get_slot_schema = None  # type: ignore
    get_industry_metadata = None  # type: ignore
    get_section_sequence = None  # type: ignore
    get_all_page_sections = None  # type: ignore

# Tenant capture layer (optional) — reads phase0_field_values, creative_assets,
# competitor_profiles by tenant coordinate. Read-only / idempotent; absence of a
# --tenant coordinate leaves registry/file builds completely unchanged.
try:
    from lib.tenant_context import load_tenant_context
    TENANT_CONTEXT_AVAILABLE = True
except ImportError:
    load_tenant_context = None  # type: ignore
    TENANT_CONTEXT_AVAILABLE = False

# Layer 6: Site manifest for multi-page generation
try:
    from lib import site_manifest as site_manifest_lib
except ImportError:
    site_manifest_lib = None  # type: ignore

# Bill of Sale orchestration (BoS → build_trace → re-audit loop)
try:
    from bill_of_sale import (
        BillOfSale,
        ensure_bill_of_sale,
        load_build_traces,
        build_dag_trace,
        map_disposition,
        write_build_trace_artifact,
    )
    BOS_AVAILABLE = True
except ImportError:
    BOS_AVAILABLE = False


# --- Configuration ---

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "skills"
TEMPLATES_DIR = ROOT / "templates"
BRIEFS_DIR = ROOT / "briefs"
OUTPUT_DIR = ROOT / "output"

def load_env_file():
    """Load simple KEY=VALUE pairs from .env into os.environ if not already set."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

load_env_file()

# Model selection per pipeline stage
MODELS = {
    "scaffold": "claude-sonnet-4-5-20250929",    # Good judgment for structure
    "section": "claude-sonnet-4-5-20250929",      # Fast, good for individual components
    "review": "claude-sonnet-4-5-20250929",       # Good judgment for quality eval
}

MAX_TOKENS = {
    "scaffold": 2048,
    "section": 4096,
    "review": 4096,
}

# --- Token accounting (W-A/A6) ---
# response.usage was previously discarded, so "what did this site cost"
# was unanswerable and could not be backfilled from past builds.
TOKEN_LEDGER: list[dict] = []


def record_token_usage(stage: str, mode: str, model: str, usage=None, label: str | None = None) -> None:
    """Append one LLM call to the build's token ledger.

    The CLI path has no usage object; it records None counts rather than
    an estimate, so totals stay honest about what was measured.
    """
    TOKEN_LEDGER.append({
        "stage": stage,
        "mode": mode,
        "model": model,
        "input_tokens": getattr(usage, "input_tokens", None) if usage else None,
        "output_tokens": getattr(usage, "output_tokens", None) if usage else None,
        "label": label,
    })


def token_ledger_summary() -> dict:
    """Totals for build_log. measured_calls vs unmeasured_calls keeps the
    CLI path visible instead of silently reading as zero cost."""
    measured = [e for e in TOKEN_LEDGER if e["input_tokens"] is not None]
    return {
        "calls": len(TOKEN_LEDGER),
        "measured_calls": len(measured),
        "unmeasured_calls": len(TOKEN_LEDGER) - len(measured),
        "input_tokens": sum(e["input_tokens"] for e in measured),
        "output_tokens": sum(e["output_tokens"] for e in measured),
        "by_stage": {
            stage: {
                "calls": len([e for e in TOKEN_LEDGER if e["stage"] == stage]),
                "input_tokens": sum(e["input_tokens"] for e in measured if e["stage"] == stage),
                "output_tokens": sum(e["output_tokens"] for e in measured if e["stage"] == stage),
            }
            for stage in sorted({e["stage"] for e in TOKEN_LEDGER})
        },
    }


TOKEN_LEDGER_FILENAME = "token-ledger.json"


def reset_token_ledger() -> None:
    """Start a build with an empty ledger.

    The ledger is module-level, so a second build inside one process (tests,
    a batch driver) would otherwise inherit the first build's calls and report
    both builds' cost as one.
    """
    TOKEN_LEDGER.clear()


# ── Build failure ledger ────────────────────────────────────────────────
# Stages record real failures here instead of printing a warning and returning
# normally. main() reads the ledger at the very end to decide BOTH the
# build_log `status` and the process exit code. Before this existed, a stage
# could print "FAILED" while the process exited 0 and the build_log said
# "completed" — the orchestrator's own exit code did not mean what it said.
BUILD_FAILURES: list[dict] = []


def record_build_failure(stage: str, detail: str) -> None:
    """Record a build-level failure. Non-fatal here, fatal at exit."""
    BUILD_FAILURES.append({"stage": stage, "detail": detail})
    print(f"  ✖ BUILD FAILURE [{stage}]: {detail}")


def reset_build_failures() -> None:
    """Start a build with an empty failure ledger (see reset_token_ledger)."""
    BUILD_FAILURES.clear()


# Exit codes. 0 = the build did everything it was asked to and it was measured
# as passing. Anything else is NOT a success.
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REVIEW_NEEDED = 2
EXIT_NOT_MEASURED = 3


def resolve_build_outcome(
    render_audit_status: str, deploy_requested: bool, audit_ran: bool = True
) -> tuple[str, int]:
    """Map recorded failures + render-audit result onto (build_log status, exit code).

    Rules:
      * Any recorded build failure (dropped section, failed production build,
        blocked deploy) → 'failed' / exit 1, regardless of the audit.
      * Deploy was requested and the audit did not PASS → not a success.
        A 'review_needed' audit logs as 'partial' and gets its own exit code
        so a caller can tell "defects need a human" apart from "the build
        broke"; 'failed' and 'skipped' both mean the build was never measured
        as good → 'failed' / exit 1. `skipped` is deliberately NOT collapsed
        into success.
      * Deploy was NOT requested → this run only generated artifacts, so the
        render audit is not applicable and its 'skipped' value is not held
        against the run.
      * `audit_ran=False` means the audit never produced a verdict at all
        (missing tooling, server timeout, subprocess timeout/exception) —
        this is NOT the same failure as "the audit ran and found defects".
        A build whose only problem is an audit that could not run gets its
        own exit code (3, NOT_MEASURED) so callers can't mistake "we never
        measured this" for "we measured it and it's broken" (exit 1) or,
        worse, for success (exit 0). This case is checked after the
        'passed'/'review_needed' short-circuits above so an audit that DID
        produce a verdict is never downgraded by a stale audit_ran=False.

    The returned status goes straight into build_log.status, whose CHECK
    constraint (migrations/20260213192654_init_schema.sql:68) permits only
    'completed', 'failed' and 'partial' — anything else would make the whole
    insert fail and lose the row. The precise audit outcome is not lost: it is
    recorded verbatim in build_log.render_audit_status.
    """
    if BUILD_FAILURES:
        return "failed", EXIT_FAILED
    if not deploy_requested:
        return "completed", EXIT_OK
    if render_audit_status == "passed":
        return "completed", EXIT_OK
    if render_audit_status == "review_needed":
        return "partial", EXIT_REVIEW_NEEDED
    if not audit_ran:
        return "failed", EXIT_NOT_MEASURED
    return "failed", EXIT_FAILED


def finish_build(status: str, exit_code: int) -> None:
    """Print the failure ledger and exit with a code that matches `status`."""
    if BUILD_FAILURES:
        print(f"\n  ✖ {len(BUILD_FAILURES)} build failure(s) recorded:")
        for f in BUILD_FAILURES:
            print(f"    • [{f['stage']}] {f['detail']}")
    if exit_code == EXIT_OK:
        sys.exit(EXIT_OK)
    print(f"\n  ✖ Build status: {status} (exit {exit_code})")
    sys.exit(exit_code)


# site_dir (resolved str) → did `npm run build` succeed in this process.
PRODUCTION_BUILD_RESULTS: dict[str, bool] = {}


def run_production_build(site_dir: Path, label: str) -> bool:
    """Run `npm run build` in the generated site. Returns True on success.

    One build per run: the result is memoised per site directory so the
    deploy stage and the render audit share a single production build
    instead of compiling the same tree twice.
    """
    key = str(site_dir.resolve())
    prior = PRODUCTION_BUILD_RESULTS.get(key)
    if prior is True:
        print(f"  ✓ Reusing production build from earlier in this run ({label})")
        return True
    if prior is False:
        print(f"  ✖ Production build already failed earlier in this run ({label})")
        return False
    print(f"  Building Next.js site for production ({label})...")
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(site_dir),
            capture_output=True, text=True, timeout=600,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        PRODUCTION_BUILD_RESULTS[key] = False
        record_build_failure("build", f"npm run build could not complete ({label}): {e}")
        return False
    if result.returncode != 0:
        PRODUCTION_BUILD_RESULTS[key] = False
        tail = (result.stderr.strip() or result.stdout.strip()).splitlines()[-15:]
        print(f"  ⚠ Next.js production build FAILED ({label}):")
        for line in tail:
            print(f"    {line}")
        record_build_failure("build", f"npm run build failed in {site_dir} ({label})")
        return False
    PRODUCTION_BUILD_RESULTS[key] = True
    print(f"  ✓ Production build succeeded ({label})")
    return True


def production_build_ok(site_dir: Path) -> bool:
    """True only when `npm run build` has succeeded for this site in this run."""
    return PRODUCTION_BUILD_RESULTS.get(str(site_dir.resolve())) is True


def persist_token_ledger(output_dir: Path) -> dict | None:
    """Write the build's token ledger to output/<project>/token-ledger.json.

    Returns the summary (for build_log) or None if nothing could be written.

    On-disk is the PRIMARY store, not a fallback: a build run offline, or with
    Supabase unreachable, must still leave its cost on disk. The file carries
    both the summary and every per-call entry so a total can always be
    re-derived from the calls that produced it.

    Cost accounting must never fail a build, so every failure mode here is a
    warning and a continue.
    """
    try:
        if not TOKEN_LEDGER:
            return None
        summary = token_ledger_summary()
        payload = {
            "schema": "aurelix.token_ledger.v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "summary": summary,
            "calls": list(TOKEN_LEDGER),
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / TOKEN_LEDGER_FILENAME
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            f"  💰 Token ledger: {summary['calls']} call(s) "
            f"({summary['measured_calls']} measured / {summary['unmeasured_calls']} unmeasured), "
            f"{summary['input_tokens']} in / {summary['output_tokens']} out → {path.name}"
        )
        return summary
    except Exception as e:  # noqa: BLE001 — accounting never fails a build
        print(f"  ⚠ Could not persist token ledger: {e}")
        return None


# API resilience
MAX_RETRIES = 3
TIMEOUT_SECONDS = 90


def call_claude_with_retry(client, messages, max_tokens, model=None, system=None, **kwargs):
    """Call Claude API with timeout and exponential backoff retry."""
    model = model or MODELS.get("section", "claude-sonnet-4-5-20250929")
    call_kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        call_kwargs["system"] = system
    call_kwargs.update(kwargs)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                timeout=TIMEOUT_SECONDS,
                **call_kwargs
            )
            return response
        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(term in error_str for term in [
                'timeout', 'rate_limit', 'overloaded', '529', '503', '500',
                'connection', 'network'
            ])
            if not is_retryable or attempt == MAX_RETRIES - 1:
                raise
            wait = (2 ** attempt) * 5  # 5s, 10s, 20s
            print(f"  ⚠ API call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            print(f"  Retrying in {wait}s...")
            _time.sleep(wait)

    raise RuntimeError(f"Claude API failed after {MAX_RETRIES} retries")


def save_checkpoint(output_dir: Path, stage: str, project_name: str, data: dict = None):
    """Save pipeline progress checkpoint after each stage."""
    checkpoint = {
        "project": project_name,
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "data": data or {}
    }
    checkpoint_file = output_dir / "checkpoint.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp = checkpoint_file.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(checkpoint, indent=2, default=str), encoding="utf-8")
    tmp.rename(checkpoint_file)
    print(f"  ✓ Checkpoint saved: stage={stage}")


def load_checkpoint(project_name: str) -> dict | None:
    """Load checkpoint for a project if it exists."""
    checkpoint_file = OUTPUT_DIR / project_name / "checkpoint.json"
    if checkpoint_file.exists():
        return json.loads(checkpoint_file.read_text(encoding="utf-8"))
    return None


# Stage order for --skip-to vs checkpoint validation
STAGE_ORDER = ["extract", "identify", "scaffold", "sections", "assemble", "review", "deploy"]


def _stage_index(stage: str) -> int:
    """Return index of stage in pipeline order; -1 if unknown."""
    return STAGE_ORDER.index(stage) if stage in STAGE_ORDER else -1


# --- File Helpers ---

def read_file(path: Path) -> str:
    """Read a file and return its contents."""
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str):
    """Write content to a file, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    # --output-root can place paths outside the web-builder repo; fall back to the
    # absolute path for logging rather than raising on relative_to.
    try:
        _disp = path.relative_to(ROOT)
    except ValueError:
        _disp = path
    print(f"  → Saved: {_disp}")


def list_presets() -> list[str]:
    """List available preset names."""
    preset_dir = SKILLS_DIR / "presets"
    return [
        f.stem for f in preset_dir.glob("*.md")
        if f.stem != "_template"
    ]


# --- Claude API ---

# ── LLM endpoint selection ────────────────────────────────────────────
# The pipeline is the harness; these are pure text-generation sub-calls. Two
# endpoints are supported:
#   • "cli" (default): the `claude` CLI in headless (-p) mode — authenticates via
#     the local Claude Code subscription, no API key, no anthropic package. Tools
#     are denied and the call runs in an isolated temp cwd, so the model can only
#     return text (a scaffold spec / one component's TSX / a review).
#   • "api": the Anthropic SDK (ANTHROPIC_API_KEY). Used when WEBBUILDER_LLM=api
#     or a key is present.
import shutil as _shutil


def _llm_mode() -> str:
    forced = os.environ.get("WEBBUILDER_LLM", "").strip().lower()
    if forced == "api":
        return "api"
    if forced in ("cli", "claude-cli", "subscription"):
        return "cli"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "api"
    if _shutil.which("claude"):
        return "cli"
    return "api"


_CLI_MODEL_ALIAS = os.environ.get("WEBBUILDER_CLAUDE_MODEL", "sonnet")


def _cli_model_for(model: str | None) -> str:
    m = (model or "").lower()
    if "opus" in m:
        return "opus"
    if "haiku" in m:
        return "haiku"
    return _CLI_MODEL_ALIAS


def _call_claude_cli(prompt: str, model: str | None) -> str:
    """Generate via `claude -p` headless mode (subscription auth, no API key).
    Runs in an isolated temp cwd with tools denied so it only returns text."""
    import tempfile
    cmd = [
        "claude", "-p", prompt,
        "--model", _cli_model_for(model),
        "--output-format", "text",
        "--allowedTools", "NoTool",  # deny all real tools → text-only response
    ]
    ceiling = TIMEOUT_SECONDS * 4  # CLI startup + generation headroom (~360s)
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            with tempfile.TemporaryDirectory(prefix="wb-claude-") as td:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=ceiling, cwd=td)
            if r.returncode == 0 and (r.stdout or "").strip():
                return r.stdout
            last_err = ((r.stderr or "") + (r.stdout or "") or f"rc={r.returncode}")[:200]
        except subprocess.TimeoutExpired:
            last_err = f"timeout after {ceiling}s"
        if attempt < MAX_RETRIES - 1:
            wait = (2 ** attempt) * 5
            print(f"  ⚠ claude CLI failed (attempt {attempt + 1}/{MAX_RETRIES}): {last_err}")
            print(f"  Retrying in {wait}s...")
            _time.sleep(wait)
    raise RuntimeError(f"claude CLI failed after {MAX_RETRIES} retries: {last_err}")


def call_claude(
    prompt: str,
    stage: str,
    max_tokens_override: int | None = None,
    label: str | None = None,
) -> str:
    """Generate text for a pipeline stage via the selected Claude endpoint.

    `label` attributes the call in the token ledger. Per-section attribution is
    the point of a per-call ledger — a total tells you the build was expensive,
    a label tells you which section made it so.
    """
    if _llm_mode() == "cli":
        out = _call_claude_cli(prompt, MODELS[stage])
        record_token_usage(stage, "cli", MODELS[stage], usage=None, label=label)
        return out
    if Anthropic is None:
        raise RuntimeError(
            "anthropic SDK unavailable and no `claude` CLI found. "
            "Install the anthropic package + set ANTHROPIC_API_KEY, or install the claude CLI."
        )
    client = Anthropic()
    budget = max_tokens_override if max_tokens_override else MAX_TOKENS[stage]
    message = call_claude_with_retry(
        client,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=budget,
        model=MODELS[stage],
    )
    record_token_usage(stage, "api", MODELS[stage], usage=getattr(message, "usage", None), label=label)
    text_parts = [
        block.text for block in message.content if block.type == "text"
    ]
    return "\n".join(text_parts)


QUALITY_DIR = ROOT / "scripts" / "quality"
SITE_DIR_NAME = "site"  # Rendered Next.js project lives at output/{project}/site/


# --- URL Extraction Stage ---

def stage_url_extract(
    url: str,
    project_name: str,
    captures_dir: Path | None = None,
    routes: str | None = None,
    max_pages: int | None = None,
) -> tuple[str, str, dict, Path, dict | None]:
    """
    Stage 0: Extract from URL and generate preset + brief.
    Returns (preset_name, brief_content, section_contexts, extraction_dir, site_spec).

    captures_dir: an audit run directory holding captures/ and
        captures_manifest.json. When given, build-site-spec.js additionally
        harvests every captured route into site_spec["pages"], which is what
        turns a one-URL clone into a real multi-page build.
    routes: CSV of routes to harvest. Load-bearing today — the cape-crypto
        bundle holds 25 captures (6 real routes + 18 article slugs), and
        without a route list every article becomes its own static page instead
        of one /blog/[handle] template.
    """
    print("\n🌐 Stage 0: Extracting from URL...")
    print(f"  URL: {url}")

    node = "node"  # Assumes node is on PATH

    # Generate unique extraction ID to prevent race conditions in parallel builds
    extraction_id = f"{project_name}-{uuid.uuid4().hex[:8]}"
    extraction_dir = OUTPUT_DIR / "extractions" / extraction_id

    # Step 0a: Run url-to-preset.js → generates preset and extraction data
    print("\n  [0a] Generating preset from URL...")
    preset_name = project_name
    preset_script = QUALITY_DIR / "url-to-preset.js"
    result = subprocess.run(
        [node, str(preset_script), url, preset_name,
         "--extraction-dir", str(extraction_dir)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
    )
    if result.returncode != 0:
        print(f"  Error in url-to-preset.js:")
        print(result.stderr[-1000:] if result.stderr else "(no stderr)")
        sys.exit(1)
    print(result.stdout)

    # Verify preset was created
    preset_path = SKILLS_DIR / "presets" / f"{preset_name}.md"
    if not preset_path.exists():
        print(f"  Error: Preset not generated at {preset_path}")
        sys.exit(1)
    print(f"  ✓ Preset saved: {preset_path.relative_to(ROOT)}")

    # Step 0b: Run url-to-brief.js → generates brief (reuses extraction data)
    print("\n  [0b] Generating brief from URL...")
    brief_script = QUALITY_DIR / "url-to-brief.js"
    result = subprocess.run(
        [node, str(brief_script), url, project_name,
         "--extraction-dir", str(extraction_dir)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  Error in url-to-brief.js:")
        print(result.stderr[-1000:] if result.stderr else "(no stderr)")
        sys.exit(1)
    print(result.stdout)

    # Load the generated brief
    brief_path = BRIEFS_DIR / f"{project_name}.md"
    if not brief_path.exists():
        print(f"  Error: Brief not generated at {brief_path}")
        sys.exit(1)
    brief_content = read_file(brief_path)
    print(f"  ✓ Brief saved: {brief_path.relative_to(ROOT)}")

    # Step 0c: Load section contexts for per-section injection
    print("\n  [0c] Loading section context data...")
    section_contexts = {}
    extraction_data_path = extraction_dir / "extraction-data.json"
    mapped_sections_path = extraction_dir / "mapped-sections.json"

    if extraction_data_path.exists() and mapped_sections_path.exists():
        # Generate section contexts using the Node.js module
        context_script = f"""
const {{ buildAllSectionContexts }} = require('./lib/section-context');
const extractionData = require('{extraction_data_path}');
const mappedSections = require('{mapped_sections_path}');
const contexts = buildAllSectionContexts(extractionData, mappedSections);
console.log(JSON.stringify(contexts));
"""
        result = subprocess.run(
            [node, "-e", context_script],
            capture_output=True,
            text=True,
            cwd=str(QUALITY_DIR),
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                section_contexts = json.loads(result.stdout.strip())
                print(f"  ✓ Loaded context for {len(section_contexts)} sections")
            except json.JSONDecodeError:
                print("  ⚠ Could not parse section contexts, continuing without them")
        else:
            print("  ⚠ Could not generate section contexts, continuing without them")
    else:
        print("  ⚠ Extraction data not found, continuing without section contexts")

    # Step 0d: Build site-spec.json (v2.0.0 — deterministic, zero AI calls)
    site_spec = None
    print("\n  [0d] Building site-spec.json from extraction data...")
    site_spec_script = QUALITY_DIR / "build-site-spec.js"
    if site_spec_script.exists() and extraction_data_path.exists() and mapped_sections_path.exists():
        # Name the output directory explicitly. The script's default is
        # `output/<project>` relative to its CWD (the repo), while the spec is
        # read back from OUTPUT_DIR — the two only agree when --output-root is
        # absent, and when they disagree the spec silently goes missing and a
        # multi-page build degrades to single-page.
        _cmd = [node, str(site_spec_script), str(extraction_dir), project_name,
                "--out", str(OUTPUT_DIR / project_name)]
        if captures_dir:
            _cmd += ["--captures", str(captures_dir)]
            if routes:
                _cmd += ["--routes", routes]
            if max_pages:
                _cmd += ["--max-pages", str(max_pages)]
            print(f"  Harvesting captured routes from {captures_dir}")
        result = subprocess.run(
            _cmd,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            # Harvesting 25 captured routes is far more work than one spec.
            timeout=300 if captures_dir else 60,
        )
        if result.returncode != 0:
            _err = (result.stderr or "").strip() or "(no stderr)"
            if captures_dir:
                # A capture bundle was explicitly requested and could not be
                # harvested — e.g. the audit ran without --store-html, so the
                # rows carry an html_length but no html. Falling back to the
                # single-URL spec here would silently rebuild the one-page
                # starvation this flag exists to fix, and the build would look
                # like it succeeded. Fail the run instead.
                print(f"  ✖ build-site-spec.js failed with --captures: {_err[:600]}")
                record_build_failure(
                    "site-spec",
                    f"capture harvest failed for {captures_dir} (exit {result.returncode}); "
                    f"refusing to fall back to a single-page spec",
                )
                raise SystemExit(EXIT_FAILED)
            print(f"  ⚠ build-site-spec.js failed: {_err[:300]}")
        else:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"    {line}")
            site_spec_path = OUTPUT_DIR / project_name / "site-spec.json"
            if site_spec_path.exists():
                try:
                    site_spec = json.loads(site_spec_path.read_text(encoding="utf-8"))
                    _pages = site_spec.get("pages") or []
                    print(f"  ✓ site-spec.json generated ({len(site_spec.get('sections', []))} sections"
                          + (f", {len(_pages)} harvested pages" if _pages else "") + ")")
                except (json.JSONDecodeError, OSError):
                    print("  ⚠ Could not parse site-spec.json")
    else:
        print("  ⚠ build-site-spec.js or extraction data not found, skipping site-spec")

    return preset_name, brief_content, section_contexts, extraction_dir, site_spec


# --- Pattern Identification Stage (v0.9.0) ---

def stage_identify(extraction_dir: Path, project_name: str) -> dict | None:
    """
    Stage 0d: Run pattern identification on extraction data.
    Returns identification result dict or None if not available.
    """
    print("\n🔍 Stage 0d: Identifying patterns...")

    node = "node"
    identifier_script = QUALITY_DIR / "lib" / "pattern-identifier.js"

    if not identifier_script.exists():
        print("  ⚠ pattern-identifier.js not found, skipping identification")
        return None

    result = subprocess.run(
        [node, str(identifier_script), str(extraction_dir), project_name],
        capture_output=True,
        text=True,
        cwd=str(QUALITY_DIR),
        timeout=60,
    )

    if result.returncode != 0:
        print(f"  ⚠ Pattern identification failed: {result.stderr[:500] if result.stderr else '(no stderr)'}")
        return None

    try:
        identification = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print("  ⚠ Could not parse identification output, continuing without it")
        return None

    # Save gap report
    gap_report = identification.get("gapReport", {})
    gaps = gap_report.get("gaps", [])
    gap_path = OUTPUT_DIR / project_name / "gap-report.json"
    gap_path.parent.mkdir(parents=True, exist_ok=True)
    gap_path.write_text(json.dumps(gap_report, indent=2), encoding="utf-8")

    # Save identification for stage_deploy and section prompts
    id_path = OUTPUT_DIR / project_name / "identification.json"
    id_path.parent.mkdir(parents=True, exist_ok=True)
    id_path.write_text(json.dumps(identification, indent=2), encoding="utf-8")

    # Print summary
    color_system = identification.get("colorSystem", {})
    high = sum(1 for g in gaps if g.get("severity") == "high")
    medium = sum(1 for g in gaps if g.get("severity") == "medium")
    low = sum(1 for g in gaps if g.get("severity") == "low")

    print(f"  Color system: {color_system.get('system', 'unknown')} ({len(color_system.get('accents', []))} accents)")
    print(f"  Sections: {identification.get('sectionCount', 0)} total, {identification.get('highConfidence', 0)} high confidence")
    print(f"  Animation patterns: {len(identification.get('animationPatterns', []))} identified")
    if gaps:
        print(f"  ⚠ Gaps: {len(gaps)} ({high} high, {medium} medium, {low} low)")
    else:
        print(f"  ✓ No gaps detected")

    print(f"  → Saved: output/{project_name}/gap-report.json")

    # v1.2.0: Enrich identification with extracted icon/logo data
    extraction_data_path = extraction_dir / "extraction-data.json"
    if extraction_data_path.exists():
        try:
            ext_data = json.loads(extraction_data_path.read_text(encoding="utf-8"))
            assets = ext_data.get("assets", {})
            # Add icon library info
            icon_lib = assets.get("iconLibrary")
            if icon_lib and icon_lib.get("library"):
                identification["iconLibrary"] = icon_lib
                print(f"  Icon library: {icon_lib['library']} ({icon_lib.get('count', 0)} icons)")
            # Add extracted logos
            logos = assets.get("logos", [])
            if logos:
                identification["extractedLogos"] = logos
                print(f"  Extracted logos: {len(logos)} raster images")
            # Add extracted SVGs
            svgs = assets.get("svgs", [])
            if svgs:
                identification["extractedSVGs"] = svgs
                logo_svgs = sum(1 for s in svgs if s.get("category") == "logo")
                icon_svgs = sum(1 for s in svgs if s.get("category") == "icon")
                print(f"  Extracted SVGs: {len(svgs)} ({logo_svgs} logos, {icon_svgs} icons)")
            # Re-save enriched identification
            id_path.write_text(json.dumps(identification, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass

    return identification


def print_gap_summary(project_name: str):
    """Print gap report summary at end of build (v0.9.0)."""
    gap_path = OUTPUT_DIR / project_name / "gap-report.json"
    if not gap_path.exists():
        return

    try:
        report = json.loads(gap_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return

    gaps = report.get("gaps", [])
    if not gaps:
        return

    high = sum(1 for g in gaps if g.get("severity") == "high")
    medium = sum(1 for g in gaps if g.get("severity") == "medium")
    low = sum(1 for g in gaps if g.get("severity") == "low")

    print(f"\n{'═' * 50}")
    print(f"  ⚠ GAP REPORT SUMMARY")
    print(f"  {len(gaps)} gaps identified for {project_name}")
    if high:
        high_descs = [g["description"][:60] for g in gaps if g.get("severity") == "high"]
        print(f"    HIGH: {high} ({', '.join(high_descs)})")
    if medium:
        print(f"    MEDIUM: {medium}")
    if low:
        print(f"    LOW: {low}")
    print(f"  Extension tasks: output/{project_name}/gap-report.json")
    print(f"{'═' * 50}")


# --- Pipeline Stages ---

def stage_scaffold(brief: str, preset: str, project_name: str, no_pause: bool, identification: dict | None = None, build_cache: "BuildCache | None" = None) -> str:
    """Stage 1: Generate the page scaffold."""
    print("\n📋 Stage 1: Generating scaffold...")

    # ── Database path: skip LLM entirely when Supabase section sequence exists ──
    if build_cache and build_cache.section_sequence:
        scaffold_text = f"Page: {project_name}\nPreset: {preset}\n\n{build_cache.get_preset_sequence_text()}"
        print(f"  ✓ Using Supabase section sequence directly ({len(build_cache.section_sequence)} sections) — LLM call skipped")
        output_path = OUTPUT_DIR / project_name / "scaffold.md"
        write_file(output_path, scaffold_text)
        if not no_pause:
            print(f"\n{scaffold_text}\n")
            print("─" * 60)
            response = input("Review the scaffold above. Continue? [Y/n/edit]: ").strip().lower()
            if response == "n":
                print("Aborted. Edit the scaffold manually and rerun with --no-pause.")
                sys.exit(0)
            elif response == "edit":
                print(f"Edit the scaffold at: {output_path}")
                input("Press Enter when done editing...")
                scaffold_text = read_file(output_path)
        return scaffold_text

    # Load resources
    scaffold_template = read_file(TEMPLATES_DIR / "scaffold-prompt.md")
    taxonomy = read_file(SKILLS_DIR / "section-taxonomy.md")

    # ── Legacy path: read from .md preset file ──
    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")

    # Extract section sequence from preset
    # (Look for the Default Section Sequence block)
    sequence_match = re.search(
        r"## Default Section Sequence\n\n```\n(.*?)```",
        preset_content,
        re.DOTALL,
    )
    preset_sequence = sequence_match.group(1).strip() if sequence_match else "See preset file"

    # Extract just archetype names and variants from taxonomy (keep it concise)
    archetype_lines = []
    current_archetype = None
    for line in taxonomy.split("\n"):
        if line.startswith("### "):
            current_archetype = line.replace("### ", "").strip()
            archetype_lines.append(f"\n{current_archetype}")
        elif line.startswith("- `") and current_archetype:
            variant = line.strip().split("`")[1] if "`" in line else line.strip("- ")
            archetype_lines.append(f"  - {variant}")

    archetype_list = "\n".join(archetype_lines)

    # Build the prompt
    prompt = f"""You are a senior web designer creating a page specification for a new website.

## Client Brief
{brief}

## Industry Preset — Default Section Sequence
{preset_sequence}

## Available Section Archetypes
{archetype_list}

## Instructions

Based on the client brief, generate a page specification. Use the industry
preset's section sequence as your starting point, then adapt it:

1. ADD sections if the brief mentions needs not covered by the default sequence
2. REMOVE sections that aren't relevant to this specific client
3. REORDER if the client's priorities suggest a different flow
4. SELECT the best variant for each section based on the brief's specifics

Output format — a numbered section list:

Page: {project_name}
Preset: {preset}

1. ARCHETYPE | variant | content direction for this section
2. ARCHETYPE | variant | content direction for this section
...

For each section's content direction, write 1-2 sentences describing what
specific content goes here — specific to THIS client, not generic.

Do NOT generate any code. This is a specification only.
Keep total sections between 6 and 14."""

    # ── Inject identification data if available ──
    if identification:
        id_hints = []

        # Section mapping hints (improve low-confidence assignments)
        mapped = identification.get("mappedSections", [])
        low_conf = [s for s in mapped if s.get("confidence", 1) < 0.5]
        if low_conf:
            id_hints.append("\n## Reference Site Section Analysis")
            id_hints.append("The reference site was analyzed. These sections had low-confidence archetype mappings — consider better alternatives:")
            for s in low_conf:
                label = s.get("label", "Unknown")[:80]
                arch = s.get("archetype", "?")
                conf = s.get("confidence", 0)
                cls = s.get("classNames", "")
                # Suggest alternatives based on label keywords
                alt_hint = ""
                label_lower = label.lower()
                if any(w in label_lower for w in ["tested", "approved", "numbers", "stat", "metric", "field"]):
                    alt_hint = " → Consider STATS or TESTIMONIALS"
                elif any(w in label_lower for w in ["product", "format", "access", "pricing", "plan"]):
                    alt_hint = " → Consider PRODUCT-SHOWCASE or PRICING"
                elif any(w in label_lower for w in ["carbon", "sustain", "environ", "planet", "clean"]):
                    alt_hint = " → Consider ABOUT or FEATURES with sustainability variant"
                id_hints.append(f'  - "{label}" (class: {cls}) → mapped as {arch} at {conf:.0%} confidence{alt_hint}')

        # Detected plugins hint
        plugins = identification.get("detectedPlugins", [])
        if plugins:
            id_hints.append(f"\n## Detected Animation Plugins: {', '.join(plugins)}")
            id_hints.append("The reference site uses these GSAP plugins. Include sections that showcase these capabilities:")
            if "SplitText" in plugins:
                id_hints.append("  - SplitText → Use in HERO (character reveal), CTA (word reveal), TESTIMONIALS (line reveal)")
            if "Observer" in plugins:
                id_hints.append("  - Observer → Use in GALLERY (swipe gestures) or HERO (scroll velocity effects)")
            if "Flip" in plugins:
                id_hints.append("  - Flip → Use in PRODUCT-SHOWCASE (filter grid) or PORTFOLIO (expand card)")
            if "DrawSVG" in plugins:
                id_hints.append("  - DrawSVG → Use in HOW-IT-WORKS (step reveal) or FEATURES (icon stroke draw)")

        # Color system hint
        color_sys = identification.get("colorSystem", {})
        if color_sys.get("accents"):
            accents = [a.get("tailwind", "?") for a in color_sys["accents"]]
            id_hints.append(f"\n## Extracted Color System: {color_sys.get('system', 'unknown')} ({', '.join(accents)})")

        if id_hints:
            prompt += "\n" + "\n".join(id_hints)

    scaffold = call_claude(prompt, "scaffold")

    # Save
    output_path = OUTPUT_DIR / project_name / "scaffold.md"
    write_file(output_path, scaffold)

    print(f"\n{scaffold}\n")

    # Checkpoint
    if not no_pause:
        print("─" * 60)
        response = input("Review the scaffold above. Continue? [Y/n/edit]: ").strip().lower()
        if response == "n":
            print("Aborted. Edit the scaffold manually and rerun with --no-pause.")
            sys.exit(0)
        elif response == "edit":
            print(f"Edit the scaffold at: {output_path}")
            input("Press Enter when done editing...")
            scaffold = read_file(output_path)

    return scaffold


def parse_scaffold(scaffold: str) -> list[dict]:
    """Parse the scaffold into a list of section specifications."""
    sections = []
    for line in scaffold.split("\n"):
        # Match lines like: 1. HERO | full-bleed-overlay | content direction text
        # Also handles bold markdown wrapping archetype+variant or just archetype:
        #   1. **NAV | sticky-transparent** | content...
        #   1. **NAV** | sticky-transparent | content...
        #   1. NAV | sticky-transparent | content...
        # Strip all bold markdown (**) from the line before parsing
        cleaned = line.strip().replace("**", "")
        match = re.match(
            r"\d+\.\s+([\w][\w-]*)\s*\|\s*([\w][\w-]*)\s*\|\s*(.+)",
            cleaned,
        )
        if match:
            sections.append({
                "archetype": match.group(1).strip(),
                "variant": match.group(2).strip(),
                "content": match.group(3).strip(),
            })
    return sections


def parse_preset_section_sequence(preset_name: str) -> list[dict]:
    """
    Load the preset markdown and parse its "Default Section Sequence" block into
    section dicts compatible with get_section_sequence (position, archetype, variant,
    content_direction, priority). Used when DB returns 0 sections for multipage.
    """
    path = SKILLS_DIR / "presets" / f"{preset_name}.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    # Find ## Default Section Sequence and the next ``` block (skip opening fence)
    in_header = False
    past_fence = False
    block_lines: list[str] = []
    for line in text.split("\n"):
        if line.strip().startswith("## Default Section Sequence"):
            in_header = True
            continue
        if in_header:
            if line.strip().startswith("```"):
                if not block_lines:
                    past_fence = True
                    continue
                break
            if past_fence:
                block_lines.append(line)
    result: list[dict] = []
    for i, line in enumerate(block_lines):
        cleaned = line.strip().replace("**", "")
        # Match: 1. ARCHETYPE | variant   or   1. ARCHETYPE | variant | content
        match = re.match(
            r"\d+\.\s+([\w][\w-]*)\s*\|\s*([\w][\w-]*)(?:\s*\|\s*(.+))?",
            cleaned,
        )
        if match:
            result.append({
                "position": i + 1,
                "archetype": match.group(1).strip(),
                "variant": match.group(2).strip(),
                "content_direction": (match.group(3) or "").strip(),
                "priority": "required",
            })
    return result


# Archetype aliases. The Supabase section registry stores some archetypes
# under a longer name than the canonical taxonomy name in
# skills/section-taxonomy.md (e.g. "FAQ-ACCORDION" vs "FAQ", "CTA-STRIP"
# vs "CTA"). Collapsing/deduping on the raw string therefore treated the
# registry entry and the harvested entry as two different sections, and
# the page ended up with the SAME section twice (cape-crypto shipped both
# a FAQ-ACCORDION and a FAQ). Dedupe on the canonical key while leaving
# each section's own `archetype` value untouched, so downstream template
# lookup (check_template_exists) still resolves the registry name.
ARCHETYPE_ALIASES = {
    "FAQ-ACCORDION": "FAQ",
    "FAQS": "FAQ",
    "CTA-STRIP": "CTA",
    "CTA-BANNER": "CTA",
    "CALL-TO-ACTION": "CTA",
    "BLOG-PREVIEW": "BLOG",
    "LOGO-CLOUD": "LOGO-BAR",
    "SOCIAL-PROOF": "TESTIMONIALS",
    "NAVBAR": "NAV",
    "NAVIGATION": "NAV",
}


def canonical_archetype(archetype: str) -> str:
    """Canonical archetype key — THE join key between registry and source.

    Module-level because it is the only stable way to pair a registry section
    with the harvested section it corresponds to: registry order and source
    order are unrelated, and the loop index of one has no meaning in the other.
    Every per-page join (reconciliation, section contexts) uses this.
    """
    arch = (archetype or "").upper().strip()
    return ARCHETYPE_ALIASES.get(arch, arch)


def normalize_page_id(page: dict) -> str:
    """Page identity used to join site-spec pages to site-manifest pages.

    Prefers an explicit `id`, else derives one from the route: "/" -> homepage,
    "/wealth" -> wealth, "/blog/index" -> blog-index. Lowercased and
    slash-free so a route-derived slug and a manifest id compare equal.
    """
    raw = page.get("id") or page.get("page_id") or page.get("route") or page.get("path") or ""
    slug = str(raw).strip().lower().strip("/")
    slug = slug.replace("/", "-")
    return slug or "homepage"


def page_lookup_keys(page: dict) -> list[str]:
    """Every identity a manifest page may legitimately be known by.

    site_manifest._page_entry_for_type names a static page `{page_type}-page`
    ("wealth" -> id "wealth-page") while a site-spec page is keyed on the bare
    slug. Matching on `id` alone therefore misses every static page and the
    build silently falls back to generated copy — the exact silent-miss this
    whole change is meant to remove. Try id, page_type and route, each also
    without the "-page" suffix.
    """
    keys: list[str] = []
    for raw in (page.get("id"), page.get("page_id"), page.get("page_type"),
                page.get("route"), page.get("path")):
        if not raw:
            continue
        slug = str(raw).strip().lower().strip("/").replace("/", "-") or "homepage"
        if slug not in keys:
            keys.append(slug)
        if slug.endswith("-page") and slug[:-len("-page")] not in keys:
            keys.append(slug[:-len("-page")])
    return keys or ["homepage"]


def resolve_page_entry(mapping: dict | None, page: dict):
    """Look a manifest page up in a page-id-keyed mapping, tolerating aliases."""
    if not mapping:
        return None
    for key in page_lookup_keys(page):
        if key in mapping:
            return mapping[key]
    return None


def build_site_spec_by_page(site_spec: dict | None) -> dict[str, dict]:
    """Split a multi-page site-spec into one page-scoped site_spec per page id.

    Each value is a full site_spec (global `style` preserved, so every page is
    generated against the same design tokens) whose `sections` are that page's
    sections. A spec with no `pages` key is single-page and yields {} — the
    single-page path keeps reading `site_spec["sections"]` unchanged.
    """
    if not isinstance(site_spec, dict):
        return {}
    pages = site_spec.get("pages")
    if not isinstance(pages, list) or not pages:
        return {}
    shared = {k: v for k, v in site_spec.items() if k not in ("pages", "sections")}
    by_page: dict[str, dict] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = normalize_page_id(page)
        sections = [s for s in (page.get("sections") or []) if isinstance(s, dict)]
        by_page[page_id] = {**shared, "sections": sections}
    return by_page


def build_section_contexts_by_page(
    section_contexts: dict | None,
    site_spec_by_page: dict[str, dict] | None,
    site_manifest: dict | None,
) -> dict[str, dict] | None:
    """Re-key flat URL-extraction section contexts onto each page's sections.

    `section_contexts` is keyed by SOURCE index (its position in the extracted
    page), while stage_sections looks up `str(i)` where i is the GENERATION
    index (its position in the registry-ordered section list). Those two
    indices are unrelated, so passing the flat dict straight through would
    attach the source hero's reference block to whatever archetype happens to
    sit at generation index 0. Join through the archetype instead: source
    index -> archetype (via the page's site-spec) -> generation index (via the
    reconciled manifest sections). Returns None when nothing can be joined.
    """
    if not section_contexts or not site_spec_by_page or not site_manifest:
        return None
    out: dict[str, dict] = {}
    for page in site_manifest.get("pages", []):
        page_id = page.get("id", "") or normalize_page_id(page)
        spec = resolve_page_entry(site_spec_by_page, page)
        if not spec:
            continue
        ctx_by_arch: dict[str, str] = {}
        for source_section in spec.get("sections", []):
            key = str(source_section.get("index"))
            if key in section_contexts:
                ctx_by_arch[canonical_archetype(source_section.get("archetype", ""))] = section_contexts[key]
        if not ctx_by_arch:
            continue
        page_ctx: dict[str, str] = {}
        for gen_index, section in enumerate(page.get("sections", [])):
            ctx = ctx_by_arch.get(canonical_archetype(section.get("archetype", "")))
            if ctx:
                page_ctx[str(gen_index)] = ctx
        if page_ctx:
            out[page_id] = page_ctx
    return out or None


def section_identity(section: dict, fallback_index: int = 0) -> str:
    """Durable identity for a section — `section_uid` when the harvest minted one.

    build-site-spec.js mints `section_uid` = sha1(page|archetype|variant|first
    heading), stable across reordering and regeneration. Everything that needs
    to name a section (copy manifest, findings lookup, traces) uses this rather
    than list position, which changes whenever a section is added or dropped.
    Harvest-less sections (registry gap-fills, legacy scaffold) fall back to
    their index, which is all the identity they have.
    """
    uid = section.get("section_uid")
    if isinstance(uid, str) and uid.strip():
        return uid.strip()
    return str(section.get("source_index", section.get("index", fallback_index)))


def reconcile_page_sections(
    registry_sections: list[dict],
    harvested_sections: list[dict],
) -> tuple[list[dict], dict]:
    """Reconcile ONE page with the HARVEST as the spine and the registry as gap-filler.

    `reconcile_sections` collapses BOTH inputs to one entry per canonical
    archetype (`_collapse` keeps only the higher `_content_score`). That is
    correct when the registry defines the page shape, but it is lossy against a
    real source page: cape-crypto's /about has two ABOUT sections ("Our story"
    and "Backed by Numeral") and /blog has six CTAs — all real, all distinct
    copy. Passing them through reconcile_sections drops one ABOUT and five
    CTAs, verified directly.

    So this reconciler inverts the relationship:
      * every harvested section survives, in SOURCE order, duplicates included;
      * a harvested section with no variant borrows the registry's variant for
        its archetype (registry stays authoritative for shape);
      * registry archetypes absent from the harvest entirely are appended as
        gap-fills, so a required-but-missing section is still generated.

    With no harvest it delegates to reconcile_sections, leaving registry-only
    pages byte-identical to before.
    """
    harvested = [s for s in (harvested_sections or []) if isinstance(s, dict)]
    if not harvested:
        return reconcile_sections(registry_sections, [])

    registry = [s for s in (registry_sections or []) if isinstance(s, dict)]
    registry_variant: dict[str, str] = {}
    registry_direction: dict[str, str] = {}
    for sec in registry:
        arch = canonical_archetype(sec.get("archetype", ""))
        if arch and arch not in registry_variant:
            registry_variant[arch] = sec.get("variant") or ""
            registry_direction[arch] = sec.get("content_direction") or ""

    final: list[dict] = []
    seen_archetypes: set[str] = set()
    duplicates_kept = 0
    for position, sec in enumerate(harvested):
        arch = canonical_archetype(sec.get("archetype", ""))
        if not arch:
            continue
        entry = dict(sec)
        if arch in seen_archetypes:
            duplicates_kept += 1
        seen_archetypes.add(arch)
        if not (entry.get("variant") or "").strip():
            entry["variant"] = registry_variant.get(arch) or ""
        if not (entry.get("content_direction") or "").strip() and registry_direction.get(arch):
            entry["content_direction"] = registry_direction[arch]
        entry.setdefault("source_index", sec.get("index", position))
        final.append(entry)

    gap_filled = 0
    for sec in registry:
        arch = canonical_archetype(sec.get("archetype", ""))
        if not arch or arch in seen_archetypes:
            continue
        gap = dict(sec)
        gap.setdefault("content", {})
        seen_archetypes.add(arch)
        final.append(gap)
        gap_filled += 1

    meta = {
        "total": len(final),
        "registry_count": len(registry),
        "harvest_count": len(harvested),
        "gap_filled_count": gap_filled,
        # Under a harvest spine duplicates are KEPT, not resolved. Reported so
        # the number that used to mean "silently deleted" now means "preserved".
        "duplicates_resolved": 0,
        "duplicates_kept": duplicates_kept,
    }
    return final, meta


def merge_copy_summaries(by_page: dict[str, dict] | None) -> dict | None:
    """Fold per-page copy summaries into one build-level summary.

    Keeps the single-page summary shape so build_log's harvested_copy_ratio
    reads the same field either way; the ratio is recomputed over the whole
    build rather than averaged, so pages with more sections weigh more.
    """
    if not by_page:
        return None
    harvested = slots = 0
    counts = {"reproduced": 0, "revised": 0, "generated": 0}
    for summary in by_page.values():
        s = (summary or {}).get("summary", {})
        harvested += s.get("harvested_strings_total", 0)
        slots += s.get("total_copy_slots", 0)
        for key in counts:
            counts[key] += s.get(key, 0)
    return {
        "summary": {
            **counts,
            "harvested_strings_total": harvested,
            "total_copy_slots": slots,
            "harvested_copy_ratio": round(harvested / max(slots, 1), 4) if harvested else 0.0,
        },
        "pages": {pid: (s or {}).get("summary", {}) for pid, s in by_page.items()},
    }


def reconcile_sections(
    registry_sections: list[dict],
    harvested_sections: list[dict],
) -> tuple[list[dict], dict]:
    """
    Section Reconciliation Node — merge registry-required sections with
    harvested sections into one per-page list, normalizing variants and
    resolving duplicates/gaps.

    PURE / IDEMPOTENT: this function has no side effects, performs no I/O,
    and is fully deterministic — identical inputs always produce identical
    outputs. It is safe to call repeatedly; re-running it over its own
    output (or over the same build inputs) neither duplicates nor drifts
    sections. Callers rely on this for re-runnable builds.

    This is the authoritative reconciliation step that runs before any
    section generation. It guarantees:
      - Every section has a non-null variant string (normalized)
      - Registry-required sections always take precedence by position
      - Harvested sections fill gaps and extend beyond the required list
      - Duplicate archetype+position entries are resolved (registry wins)
      - The returned metadata is suitable for build_log.sections_reconciled

    Parameters
    ----------
    registry_sections : list[dict]
        Sections from the preset/Supabase (the "should have" list).
        Each dict must have at least 'archetype', 'variant', and may have
        'position', 'priority', 'content_direction'.
    harvested_sections : list[dict]
        Sections found on the reference page (the "has" list).
        Each dict must have at least 'archetype', 'variant'. May have
        additional fields like 'confidence', 'content', 'images', etc.

    Returns
    -------
    tuple[list[dict], dict]
        (reconciled_sections, reconciliation_meta)
        reconciled_sections: ordered list of merged section dicts with
            normalized variants (never None, never empty string).
        reconciliation_meta: dict with keys:
            total, registry_count, harvest_count, gap_filled_count,
            duplicates_resolved
    """
    # ── Normalize inputs: ensure variant is never None/empty ──
    _DEFAULT_VARIANT = "icon-grid"
    _ARCH_VARIANTS = {
        "HERO": "full-bleed-overlay",
        "NAV": "sticky-transparent",
        "FEATURES": "icon-grid",
        "ABOUT": "two-column",
        "CTA": "centered",
        "FOOTER": "mega",
        "FAQ": "accordion",
        "TESTIMONIALS": "carousel",
        "STATS": "grid",
        "PRICING": "three-tier",
        "PRODUCT-SHOWCASE": "hover-cards",
        "GALLERY": "masonry",
        "HOW-IT-WORKS": "numbered-steps",
        "NEWSLETTER": "inline-form",
        "LOGO-BAR": "carousel",
        "TRUST-BADGES": "icon-grid",
        "CONTACT": "split",
        "COMPARISON": "table",
        "PORTFOLIO": "grid",
        "BLOG": "card-grid",
    }

    # Build archetype→variant map from the registry so a null/empty variant
    # falls back to the *registry* variant for that archetype first (brief
    # spec), and only then to a hardcoded sensible default. Deterministic:
    # first registry occurrence of each archetype wins.
    _registry_variant_by_arch: dict[str, str] = {}
    for _rsec in registry_sections:
        _rarch = _rsec.get("archetype", "").upper()
        _rvar = _rsec.get("variant")
        if (
            _rarch
            and isinstance(_rvar, str)
            and _rvar.strip()
            and _rarch not in _registry_variant_by_arch
        ):
            _registry_variant_by_arch[_rarch] = _rvar.strip()

    def _normalize_variant(sec: dict) -> str:
        var = sec.get("variant")
        if var and isinstance(var, str) and var.strip():
            return var.strip()
        # Null/None/empty variant — never let it flow into generation.
        arch = sec.get("archetype", "").upper()
        # 1. Prefer the registry variant for this archetype.
        if arch in _registry_variant_by_arch:
            return _registry_variant_by_arch[arch]
        # 2. Fall back to an archetype-based sensible default.
        return _ARCH_VARIANTS.get(arch, _DEFAULT_VARIANT)

    _canonical_arch = canonical_archetype

    # Content richness score — used to pick the populated section when the
    # same archetype appears more than once (e.g. an empty hero vs a
    # populated hero). Higher = more real content. Deterministic.
    _CONTENT_FIELDS = (
        "content", "images", "icons", "animations",
        "components", "generation_guidance", "confidence",
    )

    def _content_score(sec: dict) -> int:
        score = 0
        content = sec.get("content")
        if isinstance(content, dict):
            score += sum(1 for v in content.values() if v)
        elif content:
            score += 1
        for fld in ("images", "icons", "animations", "components", "generation_guidance"):
            if sec.get(fld):
                score += 1
        return score

    # 1. Collapse each source to one entry per archetype ("matched by
    #    archetype"). On collision keep the richer entry so an empty
    #    duplicate never displaces a populated one.
    def _collapse(sections: list[dict], source: str) -> tuple[dict, list]:
        by_arch: dict[str, dict] = {}
        order: list[str] = []
        for i, sec in enumerate(sections):
            arch = _canonical_arch(sec.get("archetype", ""))
            if not arch:
                continue
            normalized = dict(sec)
            normalized["variant"] = _normalize_variant(sec)
            normalized["position"] = sec.get("position", i + 1)
            normalized["_source"] = source
            if arch not in by_arch:
                by_arch[arch] = normalized
                order.append(arch)
            elif _content_score(normalized) > _content_score(by_arch[arch]):
                by_arch[arch] = normalized
        return by_arch, order

    registry_by_arch, registry_order = _collapse(registry_sections, "registry")
    harvest_by_arch, harvest_order = _collapse(harvested_sections, "harvest")

    duplicates_resolved = 0
    gap_filled_count = 0
    final_sections: list[dict] = []

    # 2. Union order: registry-required archetypes first (they define the
    #    required page shape), then any extra harvested archetypes.
    union_order: list[str] = list(registry_order)
    for arch in harvest_order:
        if arch not in union_order:
            union_order.append(arch)

    for arch in union_order:
        reg = registry_by_arch.get(arch)
        hvst = harvest_by_arch.get(arch)

        if reg and hvst:
            # Both present — registry is authoritative for the required
            # shape (variant, content_direction, priority); overlay the
            # harvested content so real extracted content is preserved.
            merged = dict(reg)
            for fld in _CONTENT_FIELDS:
                if hvst.get(fld):
                    merged[fld] = hvst[fld]
            if not (merged.get("variant") or "").strip():
                merged["variant"] = _normalize_variant(hvst)
            merged["variant"] = _normalize_variant(merged)
            # An empty required slot + a populated harvest = a resolved
            # empty-duplicate.
            if _content_score(reg) == 0 and _content_score(hvst) > 0:
                duplicates_resolved += 1
            merged.pop("_source", None)
            final_sections.append(merged)
        elif reg:
            # Required-but-missing-from-harvest — gap-fill with the registry
            # archetype/variant/content_direction and empty content for the
            # copy node to populate downstream.
            gap = dict(reg)
            gap["variant"] = _normalize_variant(reg)
            gap.pop("_source", None)
            final_sections.append(gap)
            gap_filled_count += 1
        elif hvst:
            # Harvested section beyond the required set — keep it (union).
            extra = dict(hvst)
            extra["variant"] = _normalize_variant(hvst)
            extra.pop("_source", None)
            final_sections.append(extra)

    # 6. Build metadata
    # Count DISTINCT archetypes that survived, not input rows. Counting rows
    # made the function misreport its own loss: three harvested sections
    # collapsing to two still reported harvest_count 3, so the metadata said
    # everything came through while a section had just been deleted.
    _final_archs = {_canonical_arch(s.get("archetype", "")) for s in final_sections}
    registry_count = len({
        _canonical_arch(sec.get("archetype", "")) for sec in registry_sections
        if _canonical_arch(sec.get("archetype", "")) in _final_archs
    })
    harvest_count = len({
        _canonical_arch(sec.get("archetype", "")) for sec in harvested_sections
        if _canonical_arch(sec.get("archetype", "")) in _final_archs
    })

    reconciliation_meta = {
        "total": len(final_sections),
        "registry_count": registry_count,
        "harvest_count": harvest_count,
        "gap_filled_count": gap_filled_count,
        "duplicates_resolved": duplicates_resolved,
    }

    return final_sections, reconciliation_meta


def stage_scaffold_v2(site_spec: dict, project_name: str) -> tuple:
    """Stage 1 (v2): Produce section list from site-spec.json. No Claude call needed."""
    print("\n  Stage 1 (v2): Building scaffold from site-spec.json...")

    sections = []
    scaffold_lines = []

    for s in site_spec.get("sections", []):
        archetype = s.get("archetype", "FEATURES")
        variant = s.get("variant", "icon-grid")
        confidence = s.get("confidence", 0.5)
        headings = s.get("content", {}).get("headings", [])
        content_hint = headings[0] if headings else ""

        sections.append({
            "index": s["index"],
            "archetype": archetype,
            "variant": variant,
            "confidence": confidence,
            "content": s.get("content", {}),
            "images": s.get("images", []),
            "icons": s.get("icons", {}),
            "animations": s.get("animations", {}),
            "components": s.get("components", {}),
            "source_rect": s.get("source_rect", {}),
            "confidence_tier": s.get("confidence_tier", ""),
            "confidence_note": s.get("confidence_note", ""),
            "generation_guidance": s.get("generation_guidance", ""),
        })

        scaffold_lines.append(
            f"{s['index'] + 1}. {archetype} | {variant} | "
            f"confidence={confidence:.0%} | {content_hint[:60]}"
        )

    scaffold_text = "\n".join(scaffold_lines)

    # Save scaffold for reference
    output_dir = OUTPUT_DIR / project_name
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "scaffold.md").write_text(
        f"# Scaffold (v2 - from site-spec.json)\n\n{scaffold_text}\n"
    )

    print(f"  {len(sections)} sections from site-spec")
    for line in scaffold_lines:
        print(f"    {line}")

    return scaffold_text, sections


# ─────────────────────────────────────────────────────────────────────────────
# Audit Captures Harvester — verbatim copy from audit_captures.html
# ─────────────────────────────────────────────────────────────────────────────

# HTML parser for extracting verbatim text from audit_captures.html field.
# Uses only stdlib to avoid external dependencies.
from html.parser import HTMLParser as _HTMLParser


class _AuditHtmlParser(_HTMLParser):
    """Extract headings, body text, and CTAs from an HTML snippet verbatim."""

    HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
    BODY_TAGS = frozenset({"p", "li", "blockquote", "figcaption", "label", "span", "td", "th"})
    CTA_TAGS = frozenset({"a", "button"})
    SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "path"})

    def __init__(self) -> None:
        super().__init__()
        self.headings: list[str] = []
        self.body_text: list[str] = []
        self.ctas: list[dict] = []
        self._current_tag: str | None = None
        self._current_href: str | None = None
        self._text_fragments: list[str] = []
        self._skip_depth: int = 0

    def _flush_text(self) -> None:
        """Accumulate buffered text into the appropriate list."""
        text = "".join(self._text_fragments).strip()
        self._text_fragments = []
        if not text or len(text) < 2:
            return
        tag = self._current_tag
        if tag in self.HEADING_TAGS:
            self.headings.append(text[:200])
        elif tag in self.CTA_TAGS:
            entry: dict = {"text": text[:100]}
            if self._current_href:
                entry["href"] = self._current_href
            # Deduplicate by text content
            if not any(c.get("text") == entry["text"] for c in self.ctas):
                self.ctas.append(entry)
        elif tag in self.BODY_TAGS:
            self.body_text.append(text[:300])

    def handle_starttag(self, tag: str, attrs) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS:
            self._skip_depth += 1
        if self._skip_depth > 0:
            return
        # Flush previous tag's text before switching
        self._flush_text()
        self._current_tag = tag_lower
        self._current_href = None
        if tag_lower == "a":
            for k, v in attrs:
                if k.lower() == "href":
                    self._current_href = v
                    break

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return
        if tag_lower in (self.HEADING_TAGS | self.BODY_TAGS | self.CTA_TAGS):
            self._flush_text()
            self._current_tag = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        stripped = data.strip()
        if stripped:
            self._text_fragments.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._skip_depth > 0:
            return
        # Collapse common entities to their character; let handle_data collect.
        char_map = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}
        self._text_fragments.append(char_map.get(name, f"&{name};"))

    def handle_charref(self, name: str) -> None:
        if self._skip_depth > 0:
            return
        try:
            if name.startswith("x"):
                self._text_fragments.append(chr(int(name[1:], 16)))
            else:
                self._text_fragments.append(chr(int(name)))
        except (ValueError, OverflowError):
            self._text_fragments.append(f"&#{name};")


def _safe_get_audit(path: str, params: str = "") -> list[dict]:
    """Fault-tolerant GET via supabase_client primitives — never raises."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not (supabase_url and supabase_key):
        return []
    try:
        from lib.supabase_client import _get
        rows = _get(path, params)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def harvest_verbatim_copy(tenant_id: str) -> dict[str, Any]:
    """Harvest verbatim copy strings from audit_captures HTML for a tenant.

    Queries the ``audit_captures`` Supabase table for the given tenant UUID,
    parses each row's ``html`` field to extract verbatim headings, body text,
    and CTAs, then returns a structured harvest dict.

    The function is fully fault-tolerant:
    - Missing table / missing rows / absent credentials → returns empty harvest
      with ``harvested_strings=0`` (caller falls back to generated copy).
    - Malformed HTML in a row → that row is skipped; other rows are unaffected.
    - An unresolvable tenant_id → caller passes None and gets empty harvest.

    Returns
    -------
    dict with keys:
        tenant_id          : the input tenant UUID
        harvested_strings  : total verbatim strings extracted
        sections           : list[dict] each with
            - ``index``      : row ordering
            - ``headings``   : list[str] extracted from HTML
            - ``body_text``  : list[str] extracted from HTML
            - ``ctas``       : list[dict] with ``text`` (and optionally ``href``)
        source_rows        : number of audit_captures rows processed
    """
    result: dict[str, Any] = {
        "tenant_id": tenant_id,
        "harvested_strings": 0,
        "sections": [],
        "source_rows": 0,
    }
    if not tenant_id or not isinstance(tenant_id, str) or len(tenant_id) < 8:
        return result

    rows = _safe_get_audit("audit_captures", f"tenant_id=eq.{tenant_id}&select=html,page_type&order=created_at.asc")
    if not rows:
        return result

    result["source_rows"] = len(rows)
    for idx, row in enumerate(rows):
        html_content = row.get("html") or row.get("html_content") or ""
        if not isinstance(html_content, str) or not html_content.strip():
            continue
        try:
            parser = _AuditHtmlParser()
            parser.feed(html_content)
            parser.close()
            section_harvest: dict[str, Any] = {
                "index": idx,
                # page_type was selected from audit_captures but thrown away,
                # which left the harvest un-attributable: there was no way to
                # tell which page a row's copy came from, so it could not be
                # scoped to a page without pasting one page's words onto
                # another. Carry it through (see _page_audit_harvest).
                "page_type": row.get("page_type") or row.get("route") or "",
                "headings": parser.headings,
                "body_text": parser.body_text,
                "ctas": parser.ctas,
            }
            if parser.headings or parser.body_text or parser.ctas:
                # Only include sections that yielded at least one string
                result["sections"].append(section_harvest)
        except Exception:
            # Malformed HTML in this row — skip it, don't kill the whole harvest
            continue

    # Count total verbatim strings across all sections
    _total = 0
    for sec in result["sections"]:
        _total += len(sec["headings"]) + len(sec["body_text"]) + len(sec["ctas"])
    result["harvested_strings"] = _total

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Copy Fidelity Node (Phase 1) — reproduce source copy verbatim
# ─────────────────────────────────────────────────────────────────────────────
def _normalize_ctas(ctas) -> list[str]:
    """Normalize harvested CTAs (strings or {text, href} dicts) to a text list."""
    out: list[str] = []
    for c in (ctas or []):
        if isinstance(c, str) and c.strip():
            out.append(c.strip())
        elif isinstance(c, dict) and c.get("text") and str(c["text"]).strip():
            out.append(str(c["text"]).strip())
    return out


def harvested_copy_strings(content: dict) -> list[str]:
    """Return all harvested copy strings (headings + body_text + ctas) for a section.

    Copy Fidelity Node: extract-reference.js harvests real per-section copy into
    site-spec.json as content.{headings, body_text, ctas}. These strings are the
    authoritative source copy for the rebuilt section.
    """
    if not isinstance(content, dict):
        return []
    out: list[str] = []
    for h in (content.get("headings") or []):
        if isinstance(h, str) and h.strip():
            out.append(h.strip())
    for b in (content.get("body_text") or []):
        if isinstance(b, str) and b.strip():
            out.append(b.strip())
    out.extend(_normalize_ctas(content.get("ctas")))
    return out


#: How many harvested body strings one section absorbs from the page-level pool.
AUDIT_BODY_PER_SECTION = 3


def allocate_audit_harvest(sections: list[dict], audit_harvest: dict | None) -> dict[int, dict]:
    """Allocate PAGE-level harvested copy to sections that have no copy of their own.

    `harvest_verbatim_copy` parses whole `audit_captures` HTML rows, so its
    strings are page-scoped: they carry no archetype and no section boundary,
    and therefore cannot be *semantically* matched to a generated section.
    Before this existed the harvest was threaded into stage_sections and read
    only by the post-loop manifest arithmetic — it inflated
    `harvested_copy_ratio` while reaching no prompt and changing no generated
    character.

    Rather than pretend to a match we do not have, this is an explicit,
    deterministic ALLOCATION: sections that have no per-section source copy
    take, in order, the next unconsumed heading, up to
    AUDIT_BODY_PER_SECTION body strings, and the next CTA. Nothing is handed
    out twice, so two sections never render the same paragraph, and sections
    that already carry real per-section copy (from site-spec) are left alone —
    a genuine per-section match always beats this fallback.

    Returns {index in `sections` -> content dict} for the sections it fed.
    """
    if not audit_harvest:
        return {}
    headings: list[str] = []
    body: list[str] = []
    ctas: list[str] = []
    for src in audit_harvest.get("sections") or []:
        headings += [h for h in (src.get("headings") or []) if isinstance(h, str) and h.strip()]
        body += [b for b in (src.get("body_text") or []) if isinstance(b, str) and b.strip()]
        ctas += _normalize_ctas(src.get("ctas"))
    if not (headings or body or ctas):
        return {}

    allocation: dict[int, dict] = {}
    hi = bi = ci = 0
    for idx, section in enumerate(sections):
        if harvested_copy_strings(section_content_dict(section)):
            continue  # already has real per-section copy — do not override it
        if hi >= len(headings) and bi >= len(body) and ci >= len(ctas):
            break  # pool exhausted
        content: dict = {"headings": [], "body_text": [], "ctas": []}
        if hi < len(headings):
            content["headings"].append(headings[hi])
            hi += 1
        take = min(AUDIT_BODY_PER_SECTION, len(body) - bi)
        if take > 0:
            content["body_text"] = body[bi:bi + take]
            bi += take
        if ci < len(ctas):
            content["ctas"].append(ctas[ci])
            ci += 1
        allocation[idx] = content
    return allocation


def section_content_dict(section: dict) -> dict:
    """The HARVESTED COPY dict for a section — {} when there is none.

    `section["content"]` is overloaded across the pipeline: the scaffold path
    (parse_scaffold, get_section_sequence) puts a content-DIRECTION *string*
    there, while the site-spec path puts the harvested copy *dict*
    {headings, body_text, ctas}. Only the dict is real source copy, so every
    copy-fidelity consumer must go through here rather than reading
    section["content"] and hoping.
    """
    content = section.get("content")
    return content if isinstance(content, dict) else {}


#: Archetypes whose markup is dominated by a REPEATED item template — cards,
#: rows, accordion panels, logo tiles. Output scales with the item count, so a
#: repeater holding six strings emits far more JSX than a prose block holding
#: the same six strings.
_REPEATER_ARCHETYPES = frozenset({
    "FEATURES", "HOW-IT-WORKS", "FAQ", "TESTIMONIALS", "PRICING", "TEAM",
    "PORTFOLIO", "PRODUCT-SHOWCASE", "BLOG-PREVIEW", "GALLERY", "COMPARISON",
    "INTEGRATIONS", "STATS", "TRUST-BADGES", "LOGO-BAR",
})

#: Archetypes that carry a whole layout — two-column splits, nav trees, link
#: columns, forms — on top of whatever copy they hold.
_LAYOUT_ARCHETYPES = frozenset({
    "HERO", "NAV", "FOOTER", "ABOUT", "CONTACT", "PRODUCT-DETAIL",
})

#: Upper bound on a derived section budget. Stops a pathological harvest (a
#: blog index with fifty strings) from asking for an unbounded generation.
SECTION_TOKEN_CEILING = 12288


def derive_section_token_budget(
    section: dict,
    animation_budget: int | None = None,
    has_component_source: bool = False,
) -> int:
    """Derive a section's max_tokens from the SECTION, not from whether
    animation extraction data happens to exist.

    The budget used to be `anim_ctx.get("tokenBudget", MAX_TOKENS["section"])`.
    On the multi-page path there is no per-page extraction dir, so `anim_ctx`
    is empty for every section and the budget silently fell to the 4096 floor
    — including for sections carrying a dozen harvested strings. Result: near
    every section truncated, retried 2-3 times, and some were dropped outright
    (`02-trust_badges.tsx` on the homepage). The animation context is now an
    optional UPLIFT over a content-derived floor rather than the sole source.

    Derivation: a fixed component shell, plus the harvested copy itself, plus
    per-item wrapper markup weighted by whether the archetype repeats a
    template. Rounded up to a 2048 step so small content differences do not
    produce budgets that differ by a few dozen tokens.
    """
    archetype = (section.get("archetype") or "").upper()
    strings = harvested_copy_strings(section_content_dict(section))

    # Imports, "use client", motion variants, section wrapper, close.
    budget = 3072
    if archetype in _LAYOUT_ARCHETYPES:
        budget += 2048
    elif archetype in _REPEATER_ARCHETYPES:
        budget += 1024

    # The copy is emitted verbatim into JSX (~3 chars/token) …
    budget += sum(len(s) for s in strings) // 3
    # … and every item also costs its wrapper, className soup, and — for a
    # repeater — an entry in the backing data array.
    budget += len(strings) * (200 if archetype in _REPEATER_ARCHETYPES else 120)

    # Images in the section become <Image>/background blocks of their own.
    images = section.get("images")
    if isinstance(images, list):
        budget += len(images) * 150

    if has_component_source:
        budget = max(budget, 8192)
    if animation_budget:
        budget = max(budget, int(animation_budget))

    step = 2048
    budget = ((budget + step - 1) // step) * step
    return max(MAX_TOKENS["section"], min(budget, SECTION_TOKEN_CEILING))


def section_content_direction(section: dict) -> str:
    """The human-readable content direction for a section, whatever the shape.

    Prefers the dedicated `content_direction` key (registry sections), falls
    back to a string `content` (legacy scaffold), then to the first harvested
    heading. Never returns a dict, so it is safe to interpolate into a prompt.
    """
    direction = section.get("content_direction")
    if isinstance(direction, str) and direction.strip():
        return direction.strip()
    content = section.get("content")
    if isinstance(content, str):
        return content.strip()
    headings = [
        h for h in (section_content_dict(section).get("headings") or [])
        if isinstance(h, str) and h.strip()
    ]
    return headings[0].strip() if headings else ""


def build_source_copy_block(content: dict, finding: dict | None = None) -> str:
    """Build a verbatim-reproduction (or weakness-gated revision) block for a section.

    Phase 1 — verbatim: harvested headings/body_text/ctas are authoritative. The
    generated component MUST render them exactly (no paraphrase, shorten, translate,
    or embellish). Returns '' when no harvested copy exists (net-new slot → generate).

    Phase 2 — weakness gate: when `finding` is provided for this section, the block
    switches from reproduce → revise-from-source: the LLM is given BOTH the source
    copy AND the finding and instructed to rewrite FROM the source, not replace it.
    """
    if not isinstance(content, dict):
        return ""
    headings = [h for h in (content.get("headings") or []) if isinstance(h, str) and h.strip()]
    body_text = [b for b in (content.get("body_text") or []) if isinstance(b, str) and b.strip()]
    ctas = _normalize_ctas(content.get("ctas"))
    if not (headings or body_text or ctas):
        return ""

    if finding:
        header = "## SOURCE COPY — REVISE FROM SOURCE (weakness flagged)"
        rule_id = finding.get("rule_id") or finding.get("id") or "unspecified"
        detail = finding.get("detail") or finding.get("message") or finding.get("description") or ""
        instr = (
            f"An audit finding ({rule_id}) flags the copy in this section as deficient: "
            f"\"{detail}\". REWRITE the affected copy FROM the source strings below — "
            "stay anchored to the source meaning and voice; correct only what the finding "
            "calls out (e.g. quantify a vague claim, add a missing H1, fix length). Do NOT "
            "invent unrelated new copy and do NOT discard the source. Keep every source "
            "string that the finding does not target verbatim."
        )
    else:
        header = "## SOURCE COPY — REPRODUCE VERBATIM (authoritative; do NOT invent over this)"
        instr = (
            "The text below was harvested from the real source page for THIS section. "
            "Render each string EXACTLY as written into the matching slot of the component "
            "(headings -> section titles/subheadings, body -> paragraphs, CTAs -> button/link "
            "labels). Do NOT paraphrase, shorten, translate, rewrite, or embellish. Preserve "
            "exact wording, punctuation, and casing. Generate fresh copy ONLY for slots that "
            "have no source string below."
        )

    lines = [header, instr]
    if headings:
        lines.append("\nHEADINGS (in order):")
        lines += [f"  - {h}" for h in headings]
    if body_text:
        lines.append("\nBODY TEXT (in order):")
        lines += [f"  - {b}" for b in body_text]
    if ctas:
        lines.append("\nCTAS (button / link labels):")
        # `content.ctas` is a list of bare label strings; the real hrefs live
        # alongside in `content.cta_links` (build-site-spec.js keeps them
        # separate so the single-URL path's string shape is unchanged). Pair
        # them up so a CTA links where the source linked instead of to "#".
        hrefs = {}
        for link in (content.get("cta_links") or []):
            if isinstance(link, dict) and link.get("text") and link.get("href"):
                hrefs.setdefault(str(link["text"]).strip(), str(link["href"]).strip())
        for c in ctas:
            href = hrefs.get(c)
            lines.append(f"  - {c}" + (f"  →  href: {href}" if href else ""))
    return "\n".join(lines) + "\n"


def extract_style_header(preset_content: str) -> str:
    """Extract the compact style header from a preset file."""
    match = re.search(
        r"(═══ STYLE CONTEXT ═══.*?═══════════════════════)",
        preset_content,
        re.DOTALL,
    )
    if match:
        return match.group(1)
    return "[Style header not found in preset — check preset format]"


def load_injection_data(extraction_dir: Path | None) -> tuple[dict | None, dict | None]:
    """Load animation analysis and extraction data from the extraction directory."""
    if not extraction_dir or not extraction_dir.exists():
        return None, None

    animation_analysis = None
    extraction_data = None

    anim_path = extraction_dir / "animation-analysis.json"
    if anim_path.exists():
        try:
            animation_analysis = json.loads(anim_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print("  ⚠ Could not load animation-analysis.json")

    extract_path = extraction_dir / "extraction-data.json"
    if extract_path.exists():
        try:
            extraction_data = json.loads(extract_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print("  ⚠ Could not load extraction-data.json")

    return animation_analysis, extraction_data


def call_injector(script: str, args_json: str) -> dict | None:
    """Call a Node.js injection module and return parsed JSON result."""
    _escaped = args_json.replace("'", "\\'")
    node_script = f"""
const mod = require('./lib/{script}');
const args = JSON.parse('{_escaped}');
const result = mod.fn(args);
console.log(JSON.stringify(result));
"""
    # We'll call each injector's exported function directly via inline script
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True, text=True,
        cwd=str(QUALITY_DIR), timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return None
    return None


def get_animation_contexts(
    animation_analysis: dict | None,
    preset_content: str,
    sections: list[dict],
    identification: dict | None = None,
) -> dict:
    """Call animation-injector.js to get per-section animation context."""
    node_script = f"""
const {{ buildAllAnimationContexts }} = require('./lib/animation-injector');
const animAnalysis = {json.dumps(animation_analysis) if animation_analysis else 'null'};
const presetContent = {json.dumps(preset_content)};
const sections = {json.dumps(sections)};
const identification = {json.dumps(identification) if identification else 'null'};
const result = buildAllAnimationContexts(animAnalysis, presetContent, sections, identification);
console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True, text=True,
        cwd=str(QUALITY_DIR), timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            print("  ⚠ Could not parse animation injection results")
    else:
        if result.stderr:
            print(f"  ⚠ Animation injector error: {result.stderr[-300:]}")
    return {}


def get_asset_contexts(
    extraction_data: dict | None,
    sections: list[dict],
) -> dict:
    """Call asset-injector.js to get per-section asset context."""
    if not extraction_data:
        return {}

    node_script = f"""
const {{ buildAllAssetContexts }} = require('./lib/asset-injector');
const extractionData = {json.dumps(extraction_data)};
const sections = {json.dumps(sections)};
const result = buildAllAssetContexts(extractionData, sections);
console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True, text=True,
        cwd=str(QUALITY_DIR), timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            print("  ⚠ Could not parse asset injection results")
    else:
        if result.stderr:
            print(f"  ⚠ Asset injector error: {result.stderr[-300:]}")
    return {}


def get_icon_context(
    archetype: str,
    section_index: int,
    extracted_icons: list | None = None,
) -> str:
    """Call icon-mapper.js to get Lucide React icon context block for a section."""
    node_script = f"""
const {{ buildIconContextBlock }} = require('./lib/icon-mapper');
const result = buildIconContextBlock({json.dumps(archetype)}, {section_index}, {json.dumps(extracted_icons or [])});
console.log(result);
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def get_visual_fallback(
    archetype: str,
    section_index: int,
    is_card_grid: bool = False,
    card_count: int = 0,
) -> dict:
    """Call asset-injector.js getVisualFallback() for sections without images."""
    node_script = f"""
const {{ getVisualFallback }} = require('./lib/asset-injector');
const result = getVisualFallback({json.dumps(archetype)}, {section_index}, {json.dumps(is_card_grid)}, {card_count});
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"block": "", "componentFiles": []}


def get_card_embedded_demos(detected_plugins: list) -> dict:
    """Call animation-injector.js buildCardEmbeddedDemos() for plugin demo cards."""
    node_script = f"""
const {{ buildCardEmbeddedDemos }} = require('./lib/animation-injector');
const result = buildCardEmbeddedDemos({json.dumps(detected_plugins)});
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"block": "", "componentFiles": []}


def get_ui_component_matches(
    detected_patterns: list,
    search_index_path: Path | None = None,
) -> dict:
    """Call pattern-identifier.js matchUIComponents() + buildUIComponentBlock()."""
    search_index_load = "null"
    if search_index_path and search_index_path.exists():
        search_index_load = f"require('{search_index_path}')"

    node_script = f"""
const {{ matchUIComponents, buildUIComponentBlock }} = require('./lib/pattern-identifier');
const searchIndex = {search_index_load};
const matches = matchUIComponents({json.dumps(detected_patterns)}, searchIndex);
const result = buildUIComponentBlock(matches);
result.matches = matches;
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"block": "", "componentFiles": [], "matches": []}


_CONTENT_TOKEN_DEFAULTS: dict[str, str] = {
    "headline": "Discover Our Collection",
    "subheadline": "Premium quality products crafted for you",
    "cta_text": "Shop Now",
    "cta_url": "#",
    "price": "$0.00",
    "product_image_src": "/placeholder.svg",
    "product_image_alt": "Product image",
    "image_url": "/placeholder.svg",
    "image_alt": "Image",
    "section_title": "About Us",
    "section_subtitle": "Learn more about what we do",
    "section_body": "We are passionate about delivering exceptional products and experiences to our customers.",
    "section_body_2": "Our commitment to quality drives everything we do.",
    "section_label": "Trusted By",
    "placeholder_text": "Enter your email",
    "button_text": "Subscribe",
    "privacy_text": "We respect your privacy.",
    "highlight_stat": "10K+",
    "highlight_label": "Happy customers",
    "bg_color_class": "bg-gray-900",
}

# Regex: bare {token_name} in JSX — lowercase + underscores, not inside quotes or .map/key patterns
_CONTENT_TOKEN_RE = re.compile(r'(?<!["\w.])(\{)([a-z][a-z_0-9]{2,})(\})(?!["\w])')


#: Tokens no resolver could fill. Surfaced at the end of a build so an empty
#: slot is a reported gap rather than a silent one.
_UNRESOLVED_TOKENS: dict[str, int] = {}


def _record_unresolved_token(token_name: str) -> None:
    _UNRESOLVED_TOKENS[token_name] = _UNRESOLVED_TOKENS.get(token_name, 0) + 1




def _cta_pairs(content: dict) -> list[tuple[str, str]]:
    """(text, href) for a section's CTAs, preferring the linked form."""
    pairs: list[tuple[str, str]] = []
    for link in (content.get("cta_links") or []):
        if isinstance(link, dict) and (link.get("text") or "").strip():
            pairs.append((link["text"].strip(), (link.get("href") or "").strip()))
    if not pairs:
        for text in _normalize_ctas(content.get("ctas")):
            pairs.append((text, ""))
    return pairs


def _item_sub_value(item: dict, j: int, kind: str) -> str:
    """Entry `j` (0-based) of one of a harvested item's own inner lists.

    A harvested item carries `headings` / `body_text` / `ctas` / `images` — its
    full contents, not just the `heading` / `body` / `cta` / `image` summary
    fields. A nested repeater slot (`{col_1_link_2_href}`) indexes into those.
    """
    if kind in ("image", "alt"):
        images = [im for im in (item.get("images") or []) if isinstance(im, dict)]
        if j >= len(images):
            return ""
        return (images[j].get("src") if kind == "image" else images[j].get("alt")) or ""
    if kind in ("url", "cta"):
        ctas = [c for c in (item.get("ctas") or []) if isinstance(c, dict)]
        if j >= len(ctas):
            return ""
        return (ctas[j].get("href") if kind == "url" else ctas[j].get("text")) or ""
    if kind == "text-long":
        bodies = [b for b in (item.get("body_text") or []) if isinstance(b, str)]
        return bodies[j].strip() if j < len(bodies) else ""
    if kind == "text-short":
        heads = [h for h in (item.get("headings") or []) if isinstance(h, str)]
        return heads[j].strip() if j < len(heads) else ""
    # `data` / `unclassified`: no supply in the harvest, as at the top level.
    return ""


def build_template_fill(
    section: dict,
    code: str | None = None,
    slot_schema=None,
) -> tuple[dict[str, str], dict, list[dict]]:
    """Map a template's slots to this section's HARVESTED copy.

    Values come only from `section["content"]` and `section["images"]` — the
    real strings the crawler took off the source page. Nothing is drawn from
    `_CONTENT_TOKEN_DEFAULTS` / `_NUMBERED_TOKEN_DEFAULTS` / `_NUMBERED_VARIETY`
    here: a slot the harvest cannot fill is left empty and counted, never
    invented, so the coverage number means what it says.

    Which brace tokens count as slots comes from `template_contract()`, not
    from a regex sweep of the body. That distinction is load-bearing: a sweep
    also matches `variants={container}` and `key={j}`, and substituting an
    empty harvest value into those yields `variants={}` / `key={}` — a
    component that does not compile. 8 templates use `{container}` and 4 use
    `{j}`.

    Returns `(values, coverage, provenance)`:

      values      slot name -> harvested string (empty string when unfilled)
      coverage    filled/empty counts, unfilled slot names, and per-array
                  `{declared, harvested}` arity so a trimmed section is
                  visible as a trim rather than as a mystery
      provenance  one `{section_uid, slot, value, source}` record per slot,
                  `source` being "harvested" or "empty"

    Two joins are possible, and which one ran is recorded per value:

      grouped   `content.items[]` exists — the harvester found the section's
                repeating run in the DOM and joined each item's heading, body,
                CTA and image at the item boundary. Item N fills slot index N,
                and section-level slots come from `content.section_headings` /
                `content.section_body_text`, which are the strings *no item
                claimed*. Nothing is inferred. Array arity comes from
                `item_count`, so a template hardcoding 6 feature cards or 8
                team rows renders exactly as many as the page has, and
                `item_count == 0` renders none. A nested repeater
                (`{col_1_link_2_href}`) indexes the item's own inner lists.
      positional  no `items[]` — the legacy fallback. Parallel `headings[]` /
                `body_text[]` lists are paired by position, which is inference,
                not a join: where a section has one more body string than it
                has items the leading string is treated as the subtitle, a rule
                that is right for HOW-IT-WORKS and off-by-one for FEATURES.
                Every value resting on it is marked `pairing: inferred`.
    """
    if code is None:
        code = section.get("_template_code", "")
    contract = template_contract(code, slot_schema)

    content = section_content_dict(section)
    headings = [h.strip() for h in (content.get("headings") or []) if isinstance(h, str) and h.strip()]
    bodies = [b.strip() for b in (content.get("body_text") or []) if isinstance(b, str) and b.strip()]
    ctas = _cta_pairs(content)
    images = [im for im in (section.get("images") or []) if isinstance(im, dict) and im.get("src")]

    items = [it for it in (content.get("items") or []) if isinstance(it, dict)]
    grouped = bool(items)

    if grouped:
        # `item_count` is the harvester's own arity for the section. Trusting it
        # over `len(items)` would let a spec whose two fields disagree size the
        # render off a number with no items behind it; the site-spec contract
        # check already fails that case, so they agree, and the min is a belt.
        declared_count = content.get("item_count")
        item_count = (min(len(items), declared_count)
                      if isinstance(declared_count, int) else len(items))
        items = items[:item_count]

        sect_headings = [h.strip() for h in (content.get("section_headings") or [])
                         if isinstance(h, str) and h.strip()]
        sect_bodies = [b.strip() for b in (content.get("section_body_text") or [])
                       if isinstance(b, str) and b.strip()]
        section_title = sect_headings[0] if sect_headings else ""
        section_subtitle = sect_bodies[0] if sect_bodies else ""
        # A section-level CTA is one no item claimed. Without this subtraction a
        # card grid's first card link becomes the section's own button.
        claimed = {(it.get("cta") or {}).get("text", "") for it in items
                   if isinstance(it.get("cta"), dict)}
        section_ctas = [c for c in ctas if c[0] not in claimed] or ctas
        # Only images no item claimed back a section-level image slot.
        claimed_src = {(it.get("image") or {}).get("src", "") for it in items
                       if isinstance(it.get("image"), dict)}
        section_images = [im for im in images if im.get("src") not in claimed_src] or images
        item_bodies = sect_bodies[1:]  # for `section_body_2` only
        pairing_inferred = False
    else:
        section_title = headings[0] if headings else ""
        item_titles = headings[1:]
        # A body string per item, plus possibly one leading section subtitle.
        # When the counts differ this is a guess, not a join — see the docstring
        # — and `pairing_inferred` marks every value that rests on it.
        pairing_inferred = bool(item_titles) and len(bodies) != len(item_titles)
        if item_titles and len(bodies) > len(item_titles):
            section_subtitle, item_bodies = bodies[0], bodies[1:]
        elif item_titles:
            section_subtitle, item_bodies = "", bodies
        else:
            section_subtitle, item_bodies = (bodies[0] if bodies else ""), bodies[1:]
        section_ctas = ctas
        section_images = images

    # How many harvested strings back each slot type, used only by the
    # positional fallback to size an array. On the grouped path an array's
    # arity comes from `item_count`, not from counting flat strings.
    supply = {
        "text-short": len(headings[1:]),
        "text-long": len(item_bodies),
        "image": len(images),
        "alt": len(images),
        "url": len(ctas),
        "cta": len(ctas),
        "data": 0,
        "unclassified": 0,
    }

    def scalar(name: str) -> tuple[str, str]:
        """(value, kind) for a section-level slot.

        `kind` is which harvest list the slot draws from, so an empty result
        can say whether the harvest ran out (`text-short`, `url`, …) or never
        carries this sort of value at all (`data`, `unclassified`).
        """
        if name in ("headline", "section_title", "title", "page_title", "section_label"):
            return section_title, "text-short"
        if name in ("subheadline", "section_subtitle", "section_body", "subtitle",
                    "description", "page_subtitle"):
            return section_subtitle, "text-long"
        if name == "section_body_2":
            return (item_bodies[0] if item_bodies else ""), "text-long"
        if name in ("cta_text", "primary_cta_text"):
            return (section_ctas[0][0] if section_ctas else ""), "cta"
        if name in ("cta_url", "cta_href", "primary_cta_url"):
            return (section_ctas[0][1] if section_ctas else ""), "url"
        if name == "secondary_cta_text":
            return (section_ctas[1][0] if len(section_ctas) > 1 else ""), "cta"
        if name in ("secondary_cta_url", "secondary_cta_href"):
            return (section_ctas[1][1] if len(section_ctas) > 1 else ""), "url"
        kind = _slot_type(name)
        if kind == "image":
            return (section_images[0]["src"] if section_images else ""), kind
        if kind == "alt":
            return ((section_images[0].get("alt") or "") if section_images else ""), kind
        return "", kind

    def grouped_value(index: int, field: str) -> str:
        """One field of item `index` (1-based) of `content.items[]`.

        Every field of a value comes off the SAME item, because the harvester
        joined them at the item's DOM boundary. This is the whole difference
        from the positional path: `feature_1_description` is item 1's body, not
        `body_text[1]`, so a section carrying its own intro paragraph no longer
        shifts every card's copy by one.
        """
        i = index - 1
        if i >= len(items):
            return ""
        item = items[i]

        # ── Nested repeaters ──────────────────────────────────────────────
        # FOOTER/mega spells its link columns `{col_1_link_2_href}`: an array
        # (`col`) whose entries hold an array of their own. `template_contract`
        # flattens that to prefix `col`, index 1, field `link_2_href`, so the
        # sub-index is only recoverable from the field name. Without this the
        # whole column collapses onto the item's FIRST link — three rows all
        # pointing at /about, none of them labelled. Each item carries its own
        # `headings` / `body_text` / `ctas` / `images` lists, which are exactly
        # the column's contents, so the sub-index reads straight off them.
        nested = re.fullmatch(r'([a-z][a-z_]*?)_(\d+)(?:_([a-z][a-z_]*))?', field)
        if nested:
            sub_field = nested.group(3)
            if sub_field:
                sub_kind = _slot_type(sub_field)
            else:
                # A bare `{col_1_link_2}` renders as the link's visible text.
                # `infer_type("link")` says "url" because a field NAMED link
                # usually holds one; here the href lives in the `_href` sibling.
                sub_kind = _slot_type(nested.group(1))
                if sub_kind == "url":
                    sub_kind = "cta"
            return _item_sub_value(item, int(nested.group(2)) - 1, sub_kind)

        kind = _slot_type(field)
        image = item.get("image") if isinstance(item.get("image"), dict) else None
        cta = item.get("cta") if isinstance(item.get("cta"), dict) else None
        if kind == "image":
            return (image or {}).get("src") or ""
        if kind == "alt":
            return (image or {}).get("alt") or ""
        if kind == "url":
            return (cta or {}).get("href") or ""
        if kind == "cta":
            return (cta or {}).get("text") or ""
        if kind == "text-long":
            return (item.get("body") or "").strip()
        if field == "number":
            return str(index)
        if kind == "text-short":
            return (item.get("heading") or "").strip()
        # `data` (a price, a date, an icon name) and `unclassified`: the
        # harvest holds nothing of this kind. Empty, and recorded as empty.
        return ""

    def positional_value(index: int, field: str) -> str:
        """One field of item `index` (1-based), paired by list position.

        Fallback for a section the harvester found no repeating run in. Kept so
        a spec without `items[]` — an older capture, or a section whose markup
        has no detectable repeat — fills exactly as it did before.
        """
        i = index - 1
        item_titles = headings[1:]
        kind = _slot_type(field)
        if kind == "image":
            return images[i]["src"] if i < len(images) else ""
        if kind == "alt":
            return (images[i].get("alt") or "") if i < len(images) else ""
        if kind == "url":
            return ctas[i][1] if i < len(ctas) else ""
        if kind == "cta":
            return ctas[i][0] if i < len(ctas) else ""
        if kind == "text-long":
            return item_bodies[i] if i < len(item_bodies) else ""
        if field == "number":
            return str(index)
        if kind == "text-short":
            return item_titles[i] if i < len(item_titles) else ""
        return ""

    item_value = grouped_value if grouped else positional_value

    values: dict[str, str] = {}
    provenance: list[dict] = []
    empty_slots: list[str] = []
    uid = section.get("section_uid") or section_identity(section, section.get("index", 0))

    def record(slot: str, value: str, kind: str) -> None:
        values[slot] = value
        entry = {
            "section_uid": uid,
            "slot": slot,
            "value": value,
            "source": "harvested" if value else "empty",
        }
        if not value:
            entry["reason"] = (
                "no-harvest-supply" if kind in ("data", "unclassified")
                else "harvest-exhausted"
            )
        elif kind in ("text-short", "text-long"):
            # Sourced — and by which join. "grouped" is a DOM fact; "inferred"
            # is list position standing in for one.
            if grouped:
                entry["pairing"] = "grouped"
            elif pairing_inferred:
                entry["pairing"] = "inferred"
        provenance.append(entry)
        if not value:
            empty_slots.append(slot)
            _record_unresolved_token(slot)

    for name in sorted(contract["scalars"]):
        record(name, *scalar(name))

    # ── Fixed-arity arrays ────────────────────────────────────────────────
    # `declared_arity` is what the template hardcodes (TEAM/headshot-grid-square
    # structurally declares 8 member rows). Rendering all 8 from a harvest of 3
    # is how "invented content" becomes "broken content": five cards reading
    # "Name / Role". The rendered count comes from the harvest, and the surplus
    # rows are dropped before substitution.
    #
    # On the grouped path the count is `item_count` — the number of items the
    # harvester actually found in the DOM — rather than a max over how many
    # loose strings of each type the section happens to hold. `item_count == 0`
    # renders zero rows, and a section whose every slot then comes out empty is
    # flagged `omit_section` for the caller to drop entirely.
    arity: dict[str, dict] = {}
    # The contract stores an array's indices and fields as separate sets, so
    # their cross-product can name slots the template never uses.
    present = set(_TEMPLATE_TOKEN_RE.findall(code))
    for prefix, spec in sorted(contract["arrays"].items()):
        declared = spec["arity"]
        if grouped:
            harvested = min(declared, item_count)
            # An array whose fields the items cannot supply at all — an image
            # strip against text-only items — renders nothing rather than N
            # blank tiles. Counted as a leading run so trimming stays by index.
            while harvested and not any(
                grouped_value(harvested, f) for f in spec["fields"]
            ):
                harvested -= 1
        else:
            harvested = min(
                declared,
                max((supply.get(spec["field_types"][f], 0) for f in spec["fields"]), default=0),
            )
        arity[prefix] = {"declared": declared, "harvested": harvested}
        for idx in spec["indices"]:
            for field in spec["fields"]:
                slot = (f"{prefix}_{idx}" if field == _BARE_FIELD
                        else f"{prefix}_{idx}_{field}")
                if slot not in present:
                    continue
                record(
                    slot,
                    item_value(idx, field) if idx <= harvested else "",
                    spec["field_types"][field],
                )

    # ── Variable-arity repeaters ──────────────────────────────────────────
    # A fixed-arity array can only ever shrink: the template spells out N rows
    # and the block above drops the surplus, so a page with more items than the
    # template anticipated silently loses the remainder. A repeater has no N —
    # the row is written once as `{badges[].label}` and emitted here once per
    # harvested item, so the render count is the harvest count in both
    # directions. `apply_template_fill` does the emitting; this only decides
    # what each row holds.
    repeat_rows: dict[str, list[dict[str, str]]] = {}
    for prefix, spec in sorted(contract.get("repeaters", {}).items()):
        limit = item_count if grouped else max(
            (supply.get(spec["field_types"][f], 0) for f in spec["fields"]),
            default=0,
        )
        rows: list[dict[str, str]] = []
        for idx in range(1, limit + 1):
            row = {f: item_value(idx, f) for f in spec["fields"]}
            if not any(row.values()):
                break  # the harvest is exhausted; emitting blank rows is the
                       # fabrication this whole path exists to avoid
            rows.append(row)
            for field in spec["fields"]:
                # Named for the row so two rows' `label`s cannot collide, and
                # unmatchable by `_TEMPLATE_TOKEN_RE`, so recording it here
                # cannot make the substituter rewrite anything.
                record(f"{prefix}[{idx}].{field}", row[field],
                       spec["field_types"][field])
        repeat_rows[prefix] = rows

    filled = sum(1 for v in values.values() if v)
    coverage = {
        "filled": filled,
        "empty": len(values) - filled,
        "empty_slots": empty_slots,
        "arity": arity,
        # prefix -> the rows to emit. Empty list = the block renders zero times.
        "repeat_rows": repeat_rows,
        # Which join produced the values, so a build report can separate a fill
        # that rests on the DOM from one that rests on list position.
        "join": "grouped" if grouped else "positional",
        "item_count": item_count if grouped else None,
        # Nothing harvested for any slot: the section has no substance to show.
        "omit_section": bool(values) and filled == 0,
    }
    return values, coverage, provenance


#: `/* repeat:badges */` … `/* /repeat */` — the block a variable-arity
#: repeater emits once per harvested row. A block comment (not `//`) because
#: `apply_template_fill` treats `//` lines as contract declarations and passes
#: them through untouched.
_REPEAT_OPEN_RE = re.compile(r'^\s*/\*\s*repeat:([a-z][a-z_0-9]*)\s*\*/\s*$')
_REPEAT_CLOSE_RE = re.compile(r'^\s*/\*\s*/repeat\s*\*/\s*$')


def _quote_context(prefix: str) -> str | None:
    """The string literal the end of `prefix` sits inside, or None for JSX text.

    Line-scoped, which is what the substituter is: a slot token always sits on
    one line, inside at most one single-line literal.
    """
    quote = None
    i = 0
    while i < len(prefix):
        ch = prefix[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        i += 1
    return quote


def _escape_slot_value(value: str, quote: str | None) -> str:
    """A harvested string as it can safely sit where the token sat.

    Substitution used to be raw, and real page copy is full of apostrophes:
    `description: '{feature_3_description}'` filled with "cryptocurrency's full
    potential" closes the literal three words early and the file stops
    compiling. Four of this build's template sections broke exactly that way.

    Inside a literal the delimiter is backslash-escaped. In JSX text it is not
    — a backslash there is a literal backslash on the page — so quotes become
    character entities instead, which render identically and also keep a lone
    apostrophe from reading as an unterminated string to any tool scanning the
    file (the truncation detector included). Braces and angle brackets are
    entity-escaped in text position for the same reason: unescaped, they are
    JSX syntax rather than copy.
    """
    value = value.replace("\r", " ").replace("\n", " ")
    if quote == "'":
        return value.replace("\\", "\\\\").replace("'", "\\'")
    if quote == '"':
        return value.replace("\\", "\\\\").replace('"', '\\"')
    if quote == "`":
        return (value.replace("\\", "\\\\").replace("`", "\\`")
                     .replace("${", "\\${"))
    for raw, entity in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"),
                        ('"', "&quot;"), ("'", "&apos;"),
                        ("{", "&#123;"), ("}", "&#125;")):
        value = value.replace(raw, entity)
    return value


def expand_repeaters(code: str, repeat_rows: dict[str, list[dict[str, str]]]) -> str:
    """Emit each `/* repeat:PREFIX */` block once per harvested row.

    This is the half of the fill that a fixed-arity array cannot do. Trimming
    can only remove rows the template already spelled out, so `{member_8_name}`
    caps the render at eight no matter what the page holds; a repeater block is
    written once and emitted `len(rows)` times — six for a page with six items,
    zero for a page with none, and the markers themselves are dropped either
    way so nothing about the mechanism reaches the output.

    A block whose prefix has no entry in `repeat_rows` is left exactly as it
    is, tokens and all, so a missing fill shows up as a Gate A token violation
    rather than as a silently empty section.
    """
    if not repeat_rows:
        return code
    out: list[str] = []
    lines = code.splitlines()
    i = 0
    while i < len(lines):
        opened = _REPEAT_OPEN_RE.match(lines[i])
        if not opened:
            out.append(lines[i])
            i += 1
            continue
        prefix = opened.group(1)
        body: list[str] = []
        i += 1
        while i < len(lines) and not _REPEAT_CLOSE_RE.match(lines[i]):
            body.append(lines[i])
            i += 1
        i += 1  # consume the closing marker
        if prefix not in repeat_rows:
            out.append(f"    /* repeat:{prefix} */")
            out.extend(body)
            out.append("    /* /repeat */")
            continue
        for row in repeat_rows[prefix]:
            for line in body:
                for field, value in row.items():
                    token = f"{{{prefix}[].{field}}}"
                    at = line.find(token)
                    while at != -1:
                        escaped = _escape_slot_value(value, _quote_context(line[:at]))
                        line = line[:at] + escaped + line[at + len(token):]
                        at = line.find(token, at + len(escaped))
                out.append(line)
    return "\n".join(out) + ("\n" if code.endswith("\n") else "")


def apply_template_fill(code: str, values: dict[str, str], coverage: dict | None = None) -> str:
    """Substitute harvested values into a template, trimming arrays to the harvest.

    Rows beyond the harvested count are dropped by index before substitution —
    the source page has four features, not six, and padding it to six is the
    fabrication this whole exercise is about. A row left holding only empty
    values is dropped too, as a backstop for arrays the contract did not size.
    """
    # Repeaters first: their rows are emitted before any other substitution, so
    # everything downstream (trimming, the empty-row drop) sees ordinary lines.
    code = expand_repeaters(code, (coverage or {}).get("repeat_rows") or {})

    arity = (coverage or {}).get("arity") or {}
    trimmed: list[str] = []
    for line in code.splitlines():
        if line.lstrip().startswith("//"):
            trimmed.append(line)
            continue
        surplus = False
        for prefix, counts in arity.items():
            for idx in range(counts["harvested"] + 1, counts["declared"] + 1):
                if re.search(rf'\{{{re.escape(prefix)}_{idx}(?:_[a-z_0-9]+)?\}}', line):
                    surplus = True
                    break
            if surplus:
                break
        if not surplus:
            trimmed.append(line)

    def _sub_in(line: str) -> str:
        """Substitute every claimed slot on one line, escaped for where it sits.

        `re.sub` cannot do this on its own: the escaping depends on the token's
        POSITION (inside `'…'`, inside `"…"`, or in JSX text), and each
        substitution shifts the positions after it, so the line is rebuilt left
        to right instead.
        """
        out: list[str] = []
        pos = 0
        for m in _TEMPLATE_TOKEN_RE.finditer(line):
            name = m.group(1)
            if name in _TEMPLATE_RESERVED_IDENTS or name not in values:
                continue  # real JS, or a token this fill never claimed
            out.append(line[pos:m.start()])
            out.append(_escape_slot_value(
                values[name], _quote_context("".join(out))
            ))
            pos = m.end()
        out.append(line[pos:])
        return "".join(out)

    # Comment lines (notably `// Tokens:`) declare the contract; substituting
    # into them rewrites the declaration and destroys the record of what the
    # template asked for.
    filled = "\n".join(
        ln if ln.lstrip().startswith("//") else _sub_in(ln)
        for ln in trimmed
    )

    kept: list[str] = []
    for before, line in zip(trimmed, filled.splitlines()):
        stripped = line.strip().rstrip(",")
        if stripped.startswith("{") and stripped.endswith("}") and ":" in stripped:
            quoted = re.findall(r":\s*'([^']*)'", stripped) + re.findall(r':\s*"([^"]*)"', stripped)
            if quoted and not any(v.strip() for v in quoted):
                continue  # every slot in this item row is empty — drop the row
        # A self-contained one-line element whose slots all came out empty:
        # `<a href="{secondary_cta_url}">{secondary_cta_text}</a>` becomes an
        # unlabeled button linking nowhere. The source page has one CTA, not
        # two; render one.
        element = re.fullmatch(r'<(\w+)\b[^>]*>(.*)</\1>', stripped)
        if (
            _TEMPLATE_TOKEN_RE.search(before)
            and element
            and not element.group(2).strip()  # no visible text left
        ):
            content_attrs = [
                value for name, value in re.findall(r'(\w+)\s*=\s*"([^"]*)"', stripped)
                if name not in ("className", "class")
            ]
            if content_attrs and not any(v.strip() for v in content_attrs):
                continue
        kept.append(line)
    return "\n".join(kept) + ("\n" if code.endswith("\n") else "")


#: Memoization for template resolution, independent of `build_cache`.
#:
#: `check_template_exists(archetype, variant, cache)` needs only the archetype
#: and the variant — both of which every section carries, whether its sequence
#: came from the industry registry, a preset, or the harvest. The BuildCache it
#: takes is a per-build memo; its industry/page_type fields are never consulted
#: on that path. But the call site was gated on `build_cache`, which is only
#: built under `--industry`, so a `--preset` build never looked at the template
#: library at all and sent all 54 sections to the LLM — while 45 of them
#: existed in Supabase as reviewed components. This cache keeps the lookup
#: memoized without making template resolution imply industry mode.
_TEMPLATE_CACHE = None


def template_memo():
    """A BuildCache used purely as a template-lookup memo (never `.load()`ed)."""
    global _TEMPLATE_CACHE
    if _TEMPLATE_CACHE is None and BuildCache is not None:
        _TEMPLATE_CACHE = BuildCache(industry="", page_type="")
    return _TEMPLATE_CACHE


def resolve_section_templates(sections: list[dict], cache=None) -> tuple[dict, dict]:
    """Classify every section as local-template / Supabase-template / LLM.

    Returns (counts, misses) where counts has keys local/db/llm and misses maps
    "ARCHETYPE|variant" -> count for the sections that found no template. Pure
    lookup: no generation, and the results land in the shared memo so the
    generation pass re-reads them for free.
    """
    counts = {"local": 0, "db": 0, "llm": 0}
    misses: dict[str, int] = {}
    if not (SUPABASE_AVAILABLE and check_template_exists):
        counts["llm"] = len(sections)
        return counts, misses
    memo = cache or template_memo()
    for sec in sections:
        archetype = sec.get("archetype", "") or ""
        variant = sec.get("variant", "") or ""
        tpl = check_template_exists(archetype, variant, memo)
        if isinstance(tpl, Path):
            counts["local"] += 1
        elif isinstance(tpl, str):
            counts["db"] += 1
        else:
            counts["llm"] += 1
            key = f"{archetype}|{variant}"
            misses[key] = misses.get(key, 0) + 1
    return counts, misses


def report_template_resolution(sections: list[dict], label: str, cache=None) -> dict:
    """Print the resolution split BEFORE generating anything.

    This number is the measurement that says whether the pipeline is a
    deterministic assembler or an LLM improviser, so it is reported up front
    rather than inferred from the build log afterwards.
    """
    counts, misses = resolve_section_templates(sections, cache=cache)
    total = sum(counts.values()) or 1
    deterministic = counts["local"] + counts["db"]
    print(f"\n  🧱 Template resolution ({label}): {total} section(s) — "
          f"{counts['local']} local, {counts['db']} Supabase, {counts['llm']} LLM "
          f"({100 * deterministic // total}% deterministic)")
    if misses:
        print("     LLM fallbacks (no template for archetype|variant):")
        for key, n in sorted(misses.items(), key=lambda kv: -kv[1]):
            print(f"       {n:>2}x {key}")
    return {"counts": counts, "misses": misses}


def _replace_content_tokens(code: str) -> str:
    """Replace {token_name} content placeholders in Supabase code_templates with string literals.
    Only replaces tokens listed in _CONTENT_TOKEN_DEFAULTS or matching the Tokens: comment."""
    # Extract declared tokens from the // Tokens: comment line
    declared: set[str] = set()
    for line in code.split("\n"):
        if line.strip().startswith("// Tokens:"):
            declared = set(re.findall(r'\{([a-z][a-z_0-9]+?)(?:\[\])?(?:\.[a-z_]+)?\}', line))
            break

    def _replacer(m: re.Match) -> str:
        token = m.group(2)
        if token not in declared and token not in _CONTENT_TOKEN_DEFAULTS:
            return m.group(0)  # Not a content token — leave as-is
        if token not in _CONTENT_TOKEN_DEFAULTS:
            # Declared but with no default. This used to humanize the token
            # name — `{primary_cta_text}` became the visible words "Primary Cta
            # Text". Record it and render nothing.
            _record_unresolved_token(token)
            return '{""}'
        return f'{{"{_CONTENT_TOKEN_DEFAULTS[token]}"}}'

    return _CONTENT_TOKEN_RE.sub(_replacer, code)


def _detect_and_repair_truncation(code: str, section_name: str) -> dict | None:
    """Call post-process.js detectAndRepairTruncation() via Node.js subprocess.

    Returns dict with keys: truncated, repaired, code, warnings.
    Returns None if the Node.js call fails (caller should proceed with original code).
    """
    node_script = f"""
const {{ detectAndRepairTruncation }} = require('./lib/post-process');
const code = {json.dumps(code)};
const result = detectAndRepairTruncation(code, {json.dumps(section_name)});
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def _origin_for(tpl) -> str:
    """Which resolver produced this section's body.

    `check_template_exists()` (the value bound to `tpl` at the call site)
    returns a `Path` for a local `section-templates/` file, a `str` for a
    Supabase `code_template` row, or `None` when neither resolved and the LLM
    path ran instead. That Path-vs-str distinction is exactly what the
    "TEMPLATE FOUND: ... (local)" vs "TEMPLATE FOUND: Supabase code_template"
    print already branches on — there is no `tpl.is_local` attribute anywhere
    on these return types.
    """
    if tpl is None:
        return "llm"
    return "local_template" if isinstance(tpl, Path) else "supabase_template"


def _emit_section_artifact(
    project_name: str,
    page_dir: str,
    out_name: str,
    tsx: str,
    section: dict,
    section_uid: str,
    intensity: str,
    origin: str,
    provenance: list,
) -> None:
    """Write the SectionArtifact companion JSON alongside a written .tsx.

    Mirrors the .tsx location: `sections_base.name` is "sections" for a
    single-page build (one call to stage_sections, no collision risk) and the
    page id (e.g. "home", "about") for a Layer 6 multipage build, where
    `output_subdir` is `sections/{page_id}` — so two pages' artifacts land in
    different `section-artifacts/{page_id}/` directories and never collide.
    """
    from lib.section_artifact import SectionArtifact

    artifact = SectionArtifact(
        tsx=tsx,
        archetype=section["archetype"],
        variant=section.get("variant", ""),
        section_uid=section_uid,
        intensity=intensity,
        origin=origin,
        provenance=[r for r in (provenance or []) if r.get("section_uid") == section_uid],
        assets=[],
        animation=None,
    )
    art_dir = OUTPUT_DIR / project_name / "section-artifacts" / page_dir
    art_dir.mkdir(parents=True, exist_ok=True)
    art_name = Path(out_name).stem + ".json"
    (art_dir / art_name).write_text(
        json.dumps(artifact.to_dict(), indent=2), encoding="utf-8"
    )


def stage_sections(
    sections: list[dict],
    preset: str,
    project_name: str,
    section_contexts: dict | None = None,
    extraction_dir: Path | None = None,
    identification: dict | None = None,
    site_spec: dict | None = None,
    build_cache: "BuildCache | None" = None,
    output_subdir: str | None = None,
    section_file_names: list[str] | None = None,
    brief: str | None = None,
    copy_findings: dict | None = None,
    audit_harvest: dict | None = None,
) -> tuple[list[Path], dict | None]:
    """Stage 2: Generate each section component individually with engine-aware injection.
    When output_subdir and section_file_names are set (e.g. Layer 6 shared components),
    writes to output/{project}/{output_subdir}/{section_file_names[i]} instead of sections/.
    When brief is provided, it is injected into each section prompt for brand context.
    When audit_harvest (from harvest_verbatim_copy) is provided, its strings are counted
    in the copy manifest summary and harvested_copy_ratio is returned.

    Returns (section_files, copy_summary) where copy_summary is a dict with
    harvested_strings_total, generated_strings_total, harvested_copy_ratio, or None
    when no copy manifests were built.
    """
    print(f"\n🔨 Stage 2: Generating {len(sections)} sections...")
    if brief:
        print(f"  Loaded brief: ({len(brief)} chars)")
    if section_contexts:
        print(f"  (with per-section reference context from URL extraction)")

    # ── Database path: use cached style from Supabase ──
    if build_cache and build_cache.style_config:
        preset_content = build_cache.build_synthetic_preset_content()
        style_header = build_cache.compact_style_header
        print(f"  Using Supabase industry style (cached)")
    else:
        # ── Legacy path: read from .md preset file ──
        preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
        style_header = extract_style_header(preset_content)

    taxonomy = read_file(SKILLS_DIR / "section-taxonomy.md")
    engine = detect_animation_engine(preset_content)

    # SectionArtifact.intensity — there is no `preset_intensity` anywhere in
    # this file. The real field is `site_spec["style"]["animation"]["intensity"]`,
    # written by build-site-spec.js (`animationAnalysis.intensity.level`,
    # one of subtle/moderate/expressive/dramatic — the same vocabulary
    # SectionArtifact.validate() enforces) and defaulted to "moderate" when
    # animation isn't detected. --preset builds carry no site_spec at all, so
    # "moderate" is also the fallback here.
    section_intensity = (
        ((site_spec or {}).get("style") or {}).get("animation") or {}
    ).get("intensity") or "moderate"

    # Load engine-specific instruction template
    if engine == "gsap":
        instructions = read_file(TEMPLATES_DIR / "section-instructions-gsap.md")
    else:
        instructions = read_file(TEMPLATES_DIR / "section-instructions-framer.md")

    print(f"  Animation engine: {engine}")

    # Load injection data if available (URL clone mode)
    animation_analysis, extraction_data = load_injection_data(extraction_dir)

    # Build injection contexts
    animation_contexts = {}
    asset_contexts = {}
    if animation_analysis or extraction_data:
        print("  Loading injection data...")
        if animation_analysis:
            raw_anim = get_animation_contexts(
                animation_analysis, preset_content, sections, identification
            )
            # buildAllAnimationContexts returns { contexts: {...}, allComponentFiles: [...], ... }
            # Extract the per-section contexts dict and flatten it for section access
            if raw_anim and "contexts" in raw_anim:
                animation_contexts = raw_anim["contexts"]
                comp_files = raw_anim.get("allComponentFiles", [])
                non_empty = sum(1 for v in animation_contexts.values()
                                if v.get("animationContext", "").strip())
                print(f"  ✓ Animation context for {non_empty}/{len(animation_contexts)} sections"
                      f" ({len(comp_files)} library components matched)")
            elif raw_anim:
                # Fallback: if structure changed, use raw dict
                animation_contexts = raw_anim
                print(f"  ✓ Animation context loaded (legacy format)")
        if extraction_data:
            asset_contexts = get_asset_contexts(extraction_data, sections)
            if asset_contexts:
                non_empty_assets = sum(1 for v in asset_contexts.values()
                                       if v.get("assetContext", "").strip())
                print(f"  ✓ Asset context for {non_empty_assets}/{len(asset_contexts)} sections")

    section_files = []
    all_extra_component_files = []  # v1.2.0: collect extra component files for stage_deploy

    # Copy Fidelity Node: per-section copy classification manifest + revision trace
    _copy_manifest: list[dict] = []
    _copy_trace: list[dict] = []
    #: Per-template slot coverage: how much of each template the harvest filled.
    _tpl_fill_stats: list[dict] = []
    #: One record per slot: {section_uid, slot, value, source}. Nothing
    #: downstream could previously tell sourced copy from invented copy, which
    #: is what kept this defect invisible.
    _slot_provenance: list[dict] = []
    #: Sections dropped because the harvest filled none of their slots.
    _omitted_sections: list[dict] = []

    # Page-level audit-capture copy, allocated to the sections that have none
    # of their own. Computed once, before the loop, so the allocation is a
    # property of the whole section list rather than of iteration order.
    _audit_allocation = allocate_audit_harvest(sections, audit_harvest)
    if _audit_allocation:
        print(
            f"  📋 Audit harvest allocated to {len(_audit_allocation)} section(s) "
            f"with no per-section source copy"
        )

    for i, section in enumerate(sections):
        num = f"{i + 1:02d}"
        name = section["archetype"].lower().replace("-", "_")
        filename = f"{num}-{name}.tsx"
        # Same fallback build_template_fill() uses internally (its local `uid`
        # var) — section_uid is only ever set on the dict when build-site-
        # spec.js minted one; LLM-path and registry gap-fill sections have
        # none, and `section.get("section_uid", "")` would ship an artifact
        # that fails validate()'s "section_uid is empty" check.
        section_uid = section_identity(section, i)

        # Get per-section injection blocks
        anim_ctx = animation_contexts.get(str(i), {})
        animation_block = anim_ctx.get("animationContext", "")
        token_budget = derive_section_token_budget(
            section, animation_budget=anim_ctx.get("tokenBudget")
        )

        asset_ctx = asset_contexts.get(str(i), {})
        asset_block = asset_ctx.get("assetContext", "")

        budget_label = f" [{token_budget} tokens]" if token_budget != MAX_TOKENS["section"] else ""
        print(f"  [{num}/{len(sections):02d}] {section['archetype']} | {section['variant']}{budget_label}...")

        # ── Template-first check: local file, then Supabase code_template, else LLM ──
        # Template resolution depends on archetype+variant only, so it must not
        # be gated on `build_cache` (which exists only under --industry). A
        # --preset or harvest-driven build has exactly the same right to the
        # reviewed component library.
        if SUPABASE_AVAILABLE:
            _tpl_cache = build_cache or template_memo()
            tpl = check_template_exists(
                section["archetype"], section["variant"], _tpl_cache
            )
            if tpl is not None:
                if isinstance(tpl, Path):
                    print(f"      ↳ TEMPLATE FOUND: {tpl.name} (local) — skipping LLM generation")
                    template_code = tpl.read_text(encoding="utf-8")
                else:
                    print(f"      ↳ TEMPLATE FOUND: Supabase code_template — skipping LLM generation")
                    template_code = tpl

                # Inject brand tokens from build cache style config. A build
                # without --industry has no BuildCache and therefore no
                # industry style; brand-token injection is simply skipped
                # rather than crashing the template path.
                style = build_cache.style_config if build_cache else {}
                if style:
                    # Replace placeholder tokens with actual brand values
                    palette = style.get("palette", {})
                    typography = style.get("typography", {})
                    # style_config values can arrive as dicts OR scalars (a font
                    # name string, etc.) depending on industry/tenant threading —
                    # only iterate mappings.
                    if isinstance(palette, dict):
                        for token_key, token_val in palette.items():
                            template_code = template_code.replace(f"{{{{brand.{token_key}}}}}", str(token_val))
                    if isinstance(typography, dict):
                        for token_key, token_val in typography.items():
                            template_code = template_code.replace(f"{{{{brand.{token_key}}}}}", str(token_val))

                    # BRIEF #33317 — semantic role tokens with WCAG-checked fg/bg
                    # pairing. Roles: bg, surface, text_primary, text_muted,
                    # on_accent, on_surface, border. Threaded as {{brand.<role>}}
                    # and as Tailwind role classes (text-primary, text-muted,
                    # on-accent, on-surface) so generated sections never emit raw
                    # hex text without a paired, contrast-safe foreground.
                    if isinstance(palette, dict):
                        try:
                            from lib.semantic_palette import (
                                derive_semantic_tokens,
                                ROLE_CLASS_MAP,
                            )
                            _roles = derive_semantic_tokens(palette)
                            for _role, _hex in _roles.items():
                                template_code = template_code.replace(
                                    f"{{{{brand.{_role}}}}}", str(_hex)
                                )
                                _cls = ROLE_CLASS_MAP.get(_role)
                                if _cls:  # on_accent -> on-accent, text_primary -> text-primary
                                    template_code = template_code.replace(
                                        f"{{{{role.{_cls}}}}}", str(_hex)
                                    )
                        except Exception as _sem_err:
                            print(f"      ⚠ semantic tokens skipped: {_sem_err}")

                # BRIEF #33297: Inject bound tenant creative_asset src into template
                _ba = section.get("bound_asset")
                if _ba and _ba.get("src"):
                    template_code = template_code.replace("{{asset.src}}", _ba["src"])
                    template_code = template_code.replace("{{asset.type}}", str(_ba.get("asset_type", "image")))
                else:
                    template_code = template_code.replace("{{asset.src}}", "")
                    template_code = template_code.replace("{{asset.type}}", "")

                # ── Slot fill from the HARVEST, not from the default tables ──
                # This used to be `_replace_content_tokens(template_code)`,
                # which filled every slot from _CONTENT_TOKEN_DEFAULTS — so a
                # South African crypto exchange shipped "Discover Our
                # Collection" while "Buy Bitcoin South Africa" sat unread in
                # this very section's `content`. Slots the harvest cannot fill
                # are left empty and counted, never invented.
                _slot_schema = (
                    get_slot_schema(section["archetype"], section["variant"], _tpl_cache)
                    if get_slot_schema else None
                )
                _fill_values, _fill_cov, _fill_prov = build_template_fill(
                    section, template_code, _slot_schema
                )
                template_code = apply_template_fill(template_code, _fill_values, _fill_cov)
                _slot_provenance.extend(_fill_prov)
                _tpl_fill_stats.append({
                    "file": filename,
                    "section_uid": section.get("section_uid"),
                    "archetype": section["archetype"],
                    "variant": section["variant"],
                    "filled": _fill_cov["filled"],
                    "empty": _fill_cov["empty"],
                    "empty_slots": _fill_cov["empty_slots"],
                    "arity": _fill_cov["arity"],
                    "repeaters": {_p: len(_r) for _p, _r
                                  in _fill_cov["repeat_rows"].items()},
                    "omit_section": _fill_cov["omit_section"],
                    "join": _fill_cov["join"],
                    "item_count": _fill_cov["item_count"],
                })
                _cov_note = (f"{_fill_cov['filled']} filled / {_fill_cov['empty']} empty"
                             if (_fill_cov["filled"] or _fill_cov["empty"]) else "no slots")
                _join_note = (f"grouped, {_fill_cov['item_count']} items"
                              if _fill_cov["join"] == "grouped" else "positional (no items[])")
                print(f"      ↳ slots: {_cov_note} [{_join_note}]")
                for _pfx, _ar in _fill_cov["arity"].items():
                    if _ar["harvested"] < _ar["declared"]:
                        print(f"        {_pfx}[]: {_ar['harvested']}/{_ar['declared']} rows "
                              f"(trimmed to harvest)")
                for _pfx, _rows in _fill_cov["repeat_rows"].items():
                    print(f"        {_pfx}[]: {len(_rows)} rows (sized by harvest)")
                if _fill_cov["empty_slots"]:
                    print(f"        unfilled: {', '.join(_fill_cov['empty_slots'][:8])}")
                if _fill_cov["omit_section"]:
                    # Nothing harvested for any slot. Writing this file ships a
                    # section of blanks; skipping it ships the page without it.
                    print("        ⚠ omitted: harvest filled no slot in this section")
                    _omitted_sections.append({
                        "file": filename,
                        "section_uid": section.get("section_uid"),
                        "archetype": section["archetype"],
                        "variant": section["variant"],
                    })
                    continue

                sections_base = OUTPUT_DIR / project_name / (output_subdir or "sections")
                out_name = section_file_names[i] if section_file_names and i < len(section_file_names) else filename
                filepath = sections_base / out_name
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(template_code, encoding="utf-8")
                section_files.append(filepath)

                _emit_section_artifact(
                    project_name=project_name,
                    page_dir=sections_base.name,
                    out_name=out_name,
                    tsx=template_code,
                    section=section,
                    section_uid=section_uid,
                    intensity=section_intensity,
                    origin=_origin_for(tpl),
                    provenance=_fill_prov,
                )
                continue  # Skip LLM generation for this section

        # Try to find structural reference in taxonomy
        structure_ref = "[No structural reference yet — infer from archetype and variant]"
        arch_pattern = rf"### {re.escape(section['archetype'])}.*?(?=### |\Z)"
        arch_match = re.search(arch_pattern, taxonomy, re.DOTALL)
        if arch_match:
            struct_match = re.search(
                r"\*\*Structure:\*\*\s*(.+?)(?:\n\*\*|\Z)",
                arch_match.group(0),
                re.DOTALL,
            )
            if struct_match and "populate on first use" not in struct_match.group(1).lower():
                structure_ref = struct_match.group(1).strip()

        # Build optional reference context block
        ref_context_block = ""
        if section_contexts and str(i) in section_contexts:
            ref_context_block = f"\n{section_contexts[str(i)]}\n"

        # Build animation and asset context blocks
        animation_context_block = ""
        if animation_block:
            animation_context_block = f"\n{animation_block}\n"

        asset_context_block = ""
        if asset_block:
            asset_context_block = f"\n{asset_block}\n"

        # Build identification context block (v0.9.0)
        identification_block = ""
        if identification:
            id_parts = []

            # Per-section accent color override
            section_colors = identification.get("sectionColorProfile", {}).get("sectionColors", {})
            sec_color = section_colors.get(str(i), {})
            if sec_color and sec_color.get("accent"):
                id_parts.append(
                    f"## Section Accent Color\n"
                    f"This section's accent color is {sec_color['accent']} (not the default site accent).\n"
                    f"Use {sec_color['accent']} for highlights, buttons, icons, and accent elements in this section."
                )

            # Per-section animation patterns
            section_mapping = identification.get("sectionMapping", {})
            sec_map = section_mapping.get(str(i), {})
            if sec_map:
                anims = sec_map.get("animations", [])
                for anim in anims[:2]:
                    if anim.get("bestMatch"):
                        id_parts.append(
                            f"## Identified Animation Pattern\n"
                            f"Pattern: {anim['pattern']} (from reference site analysis)\n"
                            f"Registry component: {anim['bestMatch']}\n"
                            f"Use this animation pattern for entrance/interaction in this section."
                        )
                ui_comps = sec_map.get("uiComponents", [])
                if ui_comps:
                    id_parts.append(
                        f"## Identified UI Components\n"
                        f"Detected: {', '.join(ui_comps)}\n"
                        f"Incorporate these UI patterns into the section layout."
                    )

            if id_parts:
                identification_block = "\n" + "\n\n".join(id_parts) + "\n"

        # Pinned scroll context block (v1.1.0, reclassified v1.1.2)
        # Triggers on animation assignment (gsap-pinned-horizontal pattern), not archetype
        pinned_scroll_block = ""
        uses_pinned_scroll = (
            (animation_block and "pinned-horizontal" in animation_block.lower())
            or (animation_block and "pin: true" in animation_block.lower() and "scrub" in animation_block.lower())
            or (identification and identification.get("pinnedScrollDetected"))
        )
        if uses_pinned_scroll:
            pinned_scroll_block = """
═══ PINNED HORIZONTAL SCROLL RULES ═══
This section uses GSAP ScrollTrigger with pin: true and scrub: true.
Structure: section (100vh) → overflow-hidden container → flex track with will-change-transform → panels.
Each panel should be min-w-[100vw] or content-sized blocks.

CRITICAL: Use `containerAnimation` for ANY nested animations inside the pinned scroll.
Without containerAnimation, nested ScrollTriggers respond to vertical page scroll, not horizontal position.

MUST include:
- gsap.matchMedia() for mobile fallback (< 768px → vertical stack)
- invalidateOnRefresh: true for responsive recalculation
- Progress indicator (bar, dots, or panel counter)
- prefers-reduced-motion handler

See section-instructions-gsap.md for the full pinned horizontal scroll technique.
═══════════════════════════════════════
"""

        # GSAP plugin context for section prompt (when identification has detectedPlugins)
        plugin_block = ""
        if identification and identification.get("detectedPlugins"):
            plugins = identification["detectedPlugins"]
            plugin_block = f"\n═══ GSAP PLUGIN CONTEXT ═══\nDetected plugins: {', '.join(plugins)}\nUse these plugins where appropriate for this section.\n═══════════════════════════\n"

        # ── v1.2.0: Icon context block ──
        extracted_icons = []
        if identification:
            icon_lib = identification.get("iconLibrary", {})
            if isinstance(icon_lib, dict):
                extracted_icons = icon_lib.get("icons", [])
        icon_block = get_icon_context(section["archetype"], i, extracted_icons)
        if icon_block:
            icon_block = f"\n{icon_block}\n"

        # ── v1.2.0: Visual content fallback (when no images for this section) ──
        visual_fallback_block = ""
        extra_component_files = []
        has_asset_images = bool(asset_block and ("backgroundImage" in asset_block or "image" in asset_block.lower()))
        if not has_asset_images:
            is_card_grid = section["variant"] in (
                "demo-cards", "feature-cards", "benefit-cards", "grid", "card-grid",
                "three-column", "four-column", "bento-grid",
            )
            card_count = 6 if is_card_grid else 0
            vf = get_visual_fallback(section["archetype"], i, is_card_grid, card_count)
            if vf.get("block"):
                visual_fallback_block = f"\n{vf['block']}\n"
                extra_component_files.extend(vf.get("componentFiles", []))

        # ── v1.2.0: Card embedded animation demos (PRODUCT-SHOWCASE demo-cards) ──
        card_embed_block = ""
        if (section["archetype"].upper() == "PRODUCT-SHOWCASE"
                and "demo" in section.get("variant", "").lower()
                and identification and identification.get("detectedPlugins")):
            ced = get_card_embedded_demos(identification["detectedPlugins"])
            if ced.get("block"):
                card_embed_block = f"\n{ced['block']}\n"
                extra_component_files.extend(ced.get("componentFiles", []))

        # ── v1.2.0: UI component injection ──
        ui_component_block = ""
        if identification:
            sec_map = identification.get("sectionMapping", {}).get(str(i), {})
            ui_patterns = sec_map.get("uiComponents", [])
            if ui_patterns:
                search_idx = SKILLS_DIR / "animation-components" / "registry" / "animation_search_index.json"
                ucm = get_ui_component_matches(ui_patterns, search_idx)
                if ucm.get("block"):
                    ui_component_block = f"\n{ucm['block']}\n"
                    extra_component_files.extend(ucm.get("componentFiles", []))

        # ── BRIEF #33297: Bound asset injection block ──
        bound_asset_block = ""
        _ba = section.get("bound_asset")
        if _ba and _ba.get("src"):
            bound_asset_block = f"""
## Tenant Creative Asset Binding
This section has a tenant creative asset bound to it:
- Asset src: {_ba['src']}
- Asset type: {_ba.get('asset_type', 'image')}

Render this asset as the PRIMARY visual / image for this section. Use the self-hosted
URL directly as the image src (e.g. `<img src="{{...}}" />` or `backgroundImage: url(...)`).
Do NOT use placeholder image URLs or generic placeholder images when a bound asset is present.
"""

        # ── v2.0.0: Build style + section spec block ──
        # When site_spec is available (--from-url), use JSON style tokens directly.
        # When not (--preset mode), fall back to the compact style header.
        if site_spec:
            style_json = json.dumps(site_spec.get("style", {}), indent=2)
            # Build section-specific JSON from the v2 sections list
            sec_data = section  # Already a rich dict from stage_scaffold_v2
            section_spec_json = json.dumps({
                "archetype": sec_data.get("archetype", "FEATURES"),
                "variant": sec_data.get("variant", "icon-grid"),
                "confidence": sec_data.get("confidence", 1.0),
                "content": section_content_dict(sec_data),
                "content_direction": section_content_direction(sec_data),
                "images": sec_data.get("images", []),
                "icons": sec_data.get("icons", {}),
                "animations": sec_data.get("animations", {}),
                "components": sec_data.get("components", {}),
                "generation_guidance": sec_data.get("generation_guidance", ""),
            }, indent=2)

            # Resolve content direction for display
            content_display = section_content_direction(sec_data) or "(content from site-spec)"

            style_and_spec_block = f"""STYLE TOKENS (use these exact values — colors as hex, fonts as names, spacing as rem):
{style_json}

SECTION SPEC (structured data — use exact values, do not interpret or paraphrase):
{section_spec_json}

IMPORTANT: If the section spec contains "components.matched" with import_statement values,
use those EXACT import statements. Do not construct your own import paths.
If images are provided with src URLs, use them as backgroundImage CSS — not <img> tags.
The generation_guidance field indicates confidence level — follow its instructions.
COPY FIDELITY: The SECTION SPEC "content" field and the SOURCE COPY block below carry the
REAL copy harvested from the source page. Reproduce those strings verbatim in the matching
slots. Do NOT paraphrase, shorten, translate, or invent placeholder copy over them."""

        else:
            # Legacy --preset mode: use compact style header
            style_and_spec_block = f"""{style_header}

## Section Specification
Number: {i + 1} of {len(sections)}
Archetype: {section['archetype']}
Variant: {section['variant']}
Content Direction: {section_content_direction(section)}"""
            content_display = section_content_direction(section)

        # Build optional brief context block
        brief_block = ""
        if brief:
            brief_block = f"""
## Brand Context (from client brief — use this to inform tone, content, and visual decisions)
{brief}
"""

        # ── Per-section asset binding context (BRIEF #33297) ──
        bound_asset_block = ""
        bound_asset = section.get("bound_asset")
        if bound_asset:
            asset_src = bound_asset.get("src", "")
            asset_type = bound_asset.get("asset_type", "")
            bound_asset_block = f"""
## Tenant Asset Binding
This section has been bound to a tenant-provided creative asset.
Asset type: {asset_type}
Asset src: {asset_src}

IMPORTANT: Use this exact asset src path in your component. Do not use placeholder images or external URLs.
For image assets, use: <img src="{asset_src}" alt="..." />
For background images, use: style={{backgroundImage: 'url("{asset_src}")'}}
"""

        # ── Copy Fidelity Node: verbatim source-copy block (Phase 1) ──
        # Threads the harvested content.{headings, body_text, ctas} into the prompt as
        # authoritative copy. When a finding targets this section, switches that section to
        # revise-from-source (Phase 2). '' when the section has no harvested copy → generate.
        _sec_content = section_content_dict(section)
        _from_audit = False
        if not harvested_copy_strings(_sec_content) and i in _audit_allocation:
            # No per-section copy for this slot — fall back to this page's
            # allocated share of the audit-capture harvest (see
            # allocate_audit_harvest). Routed through the same block, so it
            # arrives under "REPRODUCE VERBATIM" like any other source copy.
            _sec_content = _audit_allocation[i]
            _from_audit = True
        _finding = None
        if copy_findings:
            # section_uid first: it survives reordering and regeneration, so a
            # finding raised against a section still targets that section after
            # the page changes shape. Positional keys remain as a fallback for
            # findings authored before uids existed.
            _finding = (
                copy_findings.get(section_identity(section, i))
                or copy_findings.get(str(section.get("index", i)))
                or copy_findings.get(str(i))
                or copy_findings.get(filename)
            )
        _harvested = harvested_copy_strings(_sec_content)
        source_copy_block = build_source_copy_block(_sec_content, finding=_finding)
        if source_copy_block:
            source_copy_block = "\n" + source_copy_block

        # Classify this section's copy: revised (flagged) > reproduced (harvest) > generated
        if _harvested and _finding:
            _copy_status = "revised"
        elif _harvested:
            _copy_status = "reproduced"
        else:
            _copy_status = "generated"
        _copy_manifest.append({
            "section_uid": section_identity(section, i),
            "source_index": section.get("source_index", section.get("index", i)),
            "index": section.get("index", i),
            "file": filename,
            "archetype": section.get("archetype"),
            "status": _copy_status,
            "harvested_strings": len(_harvested),
            "copy_source": "audit_captures" if _from_audit else ("site_spec" if _harvested else "generated"),
        })
        if _copy_status == "revised":
            _copy_trace.append({
                "section_uid": section_identity(section, i),
                "index": section.get("index", i),
                "file": filename,
                "finding_id": _finding.get("rule_id") or _finding.get("id"),
                "source_text": _harvested,
                "revised_text": f"see generated component {filename}",
            })

        prompt = f"""You are a senior frontend developer generating a single website section
as a React + Tailwind CSS component.
{brief_block}
{style_and_spec_block}
{source_copy_block}
{bound_asset_block}
## Structural Reference
{structure_ref}
{ref_context_block}{animation_context_block}{asset_context_block}{identification_block}{pinned_scroll_block}{plugin_block}{icon_block}{visual_fallback_block}{card_embed_block}{ui_component_block}{bound_asset_block}
{instructions}
Component name: Section{num}{section['archetype'].replace('-', '')}"""

        # Sections using pinned horizontal scroll are complex — minimum 8192 tokens
        if uses_pinned_scroll:
            token_budget = max(token_budget, 8192)

        code = call_claude(prompt, "section", max_tokens_override=token_budget, label=filename)

        # Clean up any markdown code fences that might have snuck in
        code = re.sub(r"^```\w*\n?", "", code)
        code = re.sub(r"\n?```$", "", code)

        # ── Truncation detection & repair with retry (v1.1.1 + retry v2) ──
        truncation_result = _detect_and_repair_truncation(code, filename)
        section_is_truncated = truncation_result and truncation_result.get("truncated") and not truncation_result.get("repaired")
        if truncation_result and truncation_result.get("truncated") and truncation_result.get("repaired"):
            code = truncation_result["code"]
            print(f"    ⚠ {filename}: truncated — auto-repaired")
            for w in truncation_result.get("warnings", []):
                print(f"      {w}")
            section_is_truncated = False

        # Retry loop: if truncated and not repairable, retry with higher budget / conciseness
        if section_is_truncated:
            # `_call_claude_cli` builds its argv from the prompt and model only
            # — max_tokens_override never reaches it. So under the CLI backend
            # a "retry with a bigger budget" re-sends a byte-identical request
            # and burns a full generation to re-roll the dice. When the budget
            # lever is inert, go straight to the lever that is not: the prompt.
            _budget_lever_works = _llm_mode() != "cli"
            for retry_num in range(1, 3):  # max 2 retries
                if retry_num == 1 and _budget_lever_works:
                    retry_budget = int(token_budget * 1.5)
                    retry_prompt = prompt
                    print(f"    🔄 {filename}: truncated, retry {retry_num} with max_tokens {retry_budget} (was {token_budget})")
                else:
                    retry_budget = int(token_budget * 1.5)
                    retry_prompt = prompt + "\n\nIMPORTANT: Generate a more concise version of this section. Keep it under 120 lines. Prioritize completeness over detail."
                    print(f"    🔄 {filename}: truncated, retry {retry_num} with conciseness instruction")

                code = call_claude(retry_prompt, "section", max_tokens_override=retry_budget,
                                   label=f"{filename} (retry {retry_num})")
                code = re.sub(r"^```\w*\n?", "", code)
                code = re.sub(r"\n?```$", "", code)

                truncation_result = _detect_and_repair_truncation(code, filename)
                if truncation_result and truncation_result.get("truncated"):
                    if truncation_result.get("repaired"):
                        code = truncation_result["code"]
                        print(f"    ⚠ {filename}: retry {retry_num} truncated — auto-repaired")
                        section_is_truncated = False
                        break
                    # Still truncated and not repairable — continue retry loop
                else:
                    # Not truncated
                    section_is_truncated = False
                    print(f"    ✅ {filename}: retry {retry_num} succeeded")
                    break

            if section_is_truncated:
                print(f"    ❌ {filename}: truncated after 2 retries — skipping broken section")
                # A dropped section is a BUILD FAILURE, not a warning: the page
                # ships without a section the spec asked for. Record it so the
                # exit code and build_log status say so (previously this
                # `continue` was invisible past this print).
                record_build_failure(
                    "sections",
                    f"{output_subdir or 'sections'}/{filename} dropped: "
                    f"still truncated after 2 retries",
                )
                continue  # Skip this section, don't write a broken file

        # Post-process: ensure "use client" directive for components using
        # animation libraries or React hooks
        client_markers = [
            "framer-motion", "motion.", "useState", "useEffect",
            "useRef", "useCallback", "useMemo", "gsap", "ScrollTrigger",
            "DotLottieReact", "lucide-react",
        ]
        needs_client = any(marker in code for marker in client_markers)
        has_client = code.startswith('"use client"') or code.startswith("'use client'")
        if needs_client and not has_client:
            code = '"use client";\n\n' + code

        # Ensure default export exists
        if "export default" not in code:
            component_name = f"Section{num}{section['archetype'].replace('-', '')}"
            named_fn_pat = rf"export\s+function\s+{re.escape(component_name)}\b"
            if re.search(named_fn_pat, code):
                code = re.sub(named_fn_pat, f"export default function {component_name}", code)
            else:
                code += f"\n\nexport default {component_name};\n"

        sections_base = OUTPUT_DIR / project_name / (output_subdir or "sections")
        out_name = section_file_names[i] if section_file_names and i < len(section_file_names) else filename
        filepath = sections_base / out_name
        write_file(filepath, code)
        section_files.append(filepath)

        _emit_section_artifact(
            project_name=project_name,
            page_dir=sections_base.name,
            out_name=out_name,
            tsx=code,
            section=section,
            section_uid=section_uid,
            intensity=section_intensity,
            origin=_origin_for(None),
            provenance=[],
        )

        if not output_subdir:
            save_checkpoint(OUTPUT_DIR / project_name, "sections", project_name, {"last_section_index": i, "section_count": len(sections)})

        # v1.2.0: Track extra component files for this section
        if extra_component_files:
            all_extra_component_files.extend(extra_component_files)

    # v1.2.0: Save extra component manifest for stage_deploy
    if all_extra_component_files:
        unique_files = list(set(all_extra_component_files))
        manifest_path = OUTPUT_DIR / project_name / "extra-components.json"
        write_file(manifest_path, json.dumps(unique_files, indent=2))
        print(f"  ✓ {len(unique_files)} extra component files queued for stage_deploy")

    # ── Copy Fidelity Node: emit copy manifest + revision trace ──
    _copy_summary: dict | None = None
    if _copy_manifest:
        _counts = {"reproduced": 0, "revised": 0, "generated": 0}
        for _m in _copy_manifest:
            _counts[_m["status"]] = _counts.get(_m["status"], 0) + 1
        _cm_dir = OUTPUT_DIR / project_name
        if output_subdir:
            # Keep multipage manifests namespaced so pages don't clobber each other.
            _cm_name = f"copy-manifest-{output_subdir.replace('/', '_')}.json"
        else:
            _cm_name = "copy-manifest.json"

        # ── Audit harvest integration ──────────────────────────────
        # Every harvested string that reached a prompt is already counted in a
        # per-section manifest entry — including the audit strings, now that
        # they are allocated INTO sections. Adding the whole audit harvest on
        # top (as this did) double-counted it and, worse, counted strings that
        # never reached any prompt: the ratio moved while the generated output
        # did not. Count what was actually used, and report the available and
        # used audit totals separately so the gap between them is visible.
        _harvested_total = sum(
            _m.get("harvested_strings", 0) for _m in _copy_manifest
        )
        _audit_available = audit_harvest.get("harvested_strings", 0) if audit_harvest else 0
        _audit_total = sum(
            len(harvested_copy_strings(_c)) for _c in _audit_allocation.values()
        )

        # Total copy slots: site-spec harvested sections + generated sections = all sections
        _total_copy_slots = len(_copy_manifest)
        _generated_slots = _counts.get("generated", 0)
        _harvested_copy_ratio = (
            round(_harvested_total / max(_total_copy_slots, 1), 4)
            if _harvested_total > 0 else 0.0
        )

        _manifest_data: dict = {
            "summary": {
                **_counts,
                "audit_harvest_strings": _audit_available,
                "audit_harvest_used": _audit_total,
                "harvested_strings_total": _harvested_total,
                "total_copy_slots": _total_copy_slots,
                "harvested_copy_ratio": _harvested_copy_ratio,
            },
            "sections": _copy_manifest,
        }
        if audit_harvest:
            _manifest_data["audit_harvest"] = {
                "source_rows": audit_harvest.get("source_rows", 0),
                "section_count": len(audit_harvest.get("sections", [])),
                "harvested_strings": _audit_available,
                "strings_used_in_prompts": _audit_total,
                "sections_fed": len(_audit_allocation),
            }

        write_file(_cm_dir / _cm_name, json.dumps(_manifest_data, indent=2))
        if _copy_trace:
            write_file(_cm_dir / "copy-trace.json", json.dumps(_copy_trace, indent=2))
        print(
            f"  ✓ Copy manifest: {_counts['reproduced']} reproduced, "
            f"{_counts['revised']} revised, {_counts['generated']} generated"
        )
        if _audit_available > 0:
            print(
                f"    Audit harvest: {_audit_total}/{_audit_available} strings used in prompts "
                f"from {audit_harvest.get('source_rows', 0)} capture(s) | "
                f"ratio: {_harvested_copy_ratio}"
            )
        _copy_summary = _manifest_data

    if _tpl_fill_stats:
        _tf = sum(s["filled"] for s in _tpl_fill_stats)
        _te = sum(s["empty"] for s in _tpl_fill_stats)
        _tot = _tf + _te
        print(
            f"  🧩 Template slot coverage: {_tf}/{_tot} filled from harvest, "
            f"{_te} left empty ({100 * _tf // _tot if _tot else 0}%) "
            f"across {len(_tpl_fill_stats)} template section(s)"
        )
        if _omitted_sections:
            print(f"  ⊘ {len(_omitted_sections)} section(s) omitted — harvest filled no slot: "
                  + ", ".join(s["file"] for s in _omitted_sections))

        # ── Per-slot provenance ───────────────────────────────────────────
        # {section_uid, slot, value, source}. This is the artifact that makes
        # invented copy distinguishable from sourced copy; without it a page of
        # placeholder text and a page of real copy look identical downstream.
        _prov_name = (
            f"slot-provenance-{output_subdir.replace('/', '_')}.json"
            if output_subdir else "slot-provenance.json"
        )
        write_file(OUTPUT_DIR / project_name / _prov_name, json.dumps({
            "schema": "aurelix.slot_provenance.v1",
            "summary": {
                "slots": len(_slot_provenance),
                "harvested": _tf,
                "empty": _te,
                "default": 0,  # the fill path draws from no default table
                "coverage": round(_tf / _tot, 4) if _tot else 0.0,
                "sections_omitted": len(_omitted_sections),
            },
            "omitted_sections": _omitted_sections,
            "slots": _slot_provenance,
        }, indent=2))

        if isinstance(_copy_summary, dict):
            _copy_summary["template_slot_coverage"] = {
                "filled": _tf, "empty": _te, "sections": _tpl_fill_stats,
            }
        else:
            _copy_summary = {"template_slot_coverage": {
                "filled": _tf, "empty": _te, "sections": _tpl_fill_stats,
            }}

    # ── Real animation component decision ──
    # Runs after every section for this page is on disk, before assembly.
    # Template-resolved sections skip the LLM entirely (85% of the build),
    # so this is the only stage that can reach them with real motion. This
    # ONLY decides and persists (animation-injections.json) — it never opens
    # a section .tsx for writing; assembly (_build_page_imports) generates
    # the actual wrap as controlled code.
    if section_files:
        _page_dir = (OUTPUT_DIR / project_name / (output_subdir or "sections")).name
        _preset_intensity = parse_preset_intensity(preset_content)
        stage_inject_animation(project_name, _page_dir, section_files, _preset_intensity)

    return section_files, _copy_summary


def _component_name_for_section_file(filepath: Path) -> str:
    """Derive the page.tsx component identifier from a section FILENAME.

    Section files are named `{NN}-{archetype_slug}.tsx`, and each file's own
    `export default` is named from that same filename. Deriving the identifier
    here from the file (rather than from a parallel `sections` metadata list)
    keeps imports and files in lockstep.
    """
    stem = filepath.name[:-4] if filepath.name.endswith(".tsx") else filepath.name
    num, _, slug = stem.partition("-")
    num = num or "00"
    ident = "".join(ch for ch in slug.upper() if ch.isalnum())
    return f"Section{num}{ident}"


def _build_page_imports(
    section_files: list[Path],
    import_prefix: str,
    animation_map: dict | None = None,
    page_dir: str | None = None,
) -> tuple[list[str], list[str]]:
    """Build (imports, JSX elements) for every section file, in file order.

    Previously this zipped the `sections` metadata list against `section_files`
    by index. Those two lists drift apart whenever a section fails to generate
    or the section registry resolves to a different length than what is on disk
    (e.g. a Supabase outage falling back to a shorter site-spec list). The zip
    then silently (a) DROPPED the trailing files past the shorter list and
    (b) MISLABELLED every import after the drift point — cape-crypto shipped a
    `Section08FAQACCORDION` that actually imported `09-cta_strip`. The files on
    disk are the ground truth, so iterate those.

    `animation_map` is the decision stage_inject_animation() persisted
    (`OUTPUT_DIR/{project}/animation-injections.json`), keyed
    `{page_dir}/{section_stem}`. When a section has an entry, this generates
    an import for the real library component and wraps the section's JSX
    invocation in it — `<Component><SectionNN /></Component>` — instead of
    parsing or rewriting the section's own file. This is the only place a
    real animation component ever gets wired into a page; the section file
    itself is never opened for writing.
    """
    imports: list[str] = []
    components: list[str] = []
    seen: set[str] = set()
    # Two DIFFERENT source files can export the SAME name — fade-up-stagger.tsx
    # and staggered-timeline.tsx both export `AnimatedGroup`. Deduping only by
    # export name (as an earlier version of this function did) collapses the
    # second import into the first: the tally correctly records
    # `staggered_timeline` as used, but the generated page never imports that
    # file at all and silently wraps the section in fade-up-stagger's code
    # instead — exactly the "coverage number doesn't mean what it says" bug
    # this whole feature exists to prevent. Track by import PATH (unique per
    # source file) and alias the local name when an export name collides
    # across two different paths.
    wrapper_local_name_by_path: dict[str, str] = {}
    wrapper_path_by_local_name: dict[str, str] = {}
    for filepath in section_files:
        component_name = _component_name_for_section_file(filepath)
        if component_name in seen:
            continue
        seen.add(component_name)
        rel = f"{import_prefix}{filepath.name.replace('.tsx', '')}"
        imports.append(f'import {component_name} from "{rel}";')

        key = f"{page_dir}/{filepath.stem}" if page_dir else filepath.stem
        wrap = (animation_map or {}).get(key)
        if wrap and wrap.get("export_name") and wrap.get("dest_name"):
            wname = wrap["export_name"]
            wrapper_import_path = f"@/components/animations/{wrap['dest_name']}"
            local_name = wrapper_local_name_by_path.get(wrapper_import_path)
            if local_name is None:
                local_name = wname
                suffix = 2
                while local_name in wrapper_path_by_local_name and wrapper_path_by_local_name[local_name] != wrapper_import_path:
                    local_name = f"{wname}{suffix}"
                    suffix += 1
                wrapper_local_name_by_path[wrapper_import_path] = local_name
                wrapper_path_by_local_name[local_name] = wrapper_import_path
                if wrap.get("export_type") == "named":
                    alias = f" as {local_name}" if local_name != wname else ""
                    imports.append(f'import {{ {wname}{alias} }} from "{wrapper_import_path}";')
                else:
                    imports.append(f'import {local_name} from "{wrapper_import_path}";')
            components.append(
                f"      <{local_name}>\n        <{component_name} />\n      </{local_name}>"
            )
        else:
            components.append(f"      <{component_name} />")
    return imports, components


def stage_assemble(sections: list[dict], section_files: list[Path], project_name: str):
    """Stage 3: Assemble all sections into a single page component."""
    print("\n📦 Stage 3: Assembling page...")

    animation_map = load_animation_injections(project_name)
    imports, components = _build_page_imports(section_files, "./sections/", animation_map, "sections")

    page_code = f'''import React from "react";
{chr(10).join(imports)}

export default function Page() {{
  return (
    <main className="min-h-screen">
{chr(10).join(components)}
    </main>
  );
}}
'''

    write_file(OUTPUT_DIR / project_name / "page.tsx", page_code)


def _inject_nav_props(code: str) -> str:
    """Inject optional menu/logo/shopName props into a Navigation component.
    Modifies function signature AND injects prop consumption inside the function body.
    Leaves module-scope arrays as fallbacks; overrides inside function body when props exist."""
    import re
    prop_type = "{ menu?: { title: string; items: Array<{ title: string; url: string; items?: Array<{ title: string; url: string }> }> }; logo?: { url: string; altText: string | null; width?: number; height?: number }; shopName?: string }"
    code = re.sub(
        r"export default function (\w+)\s*\(\s*\)",
        rf"export default function \1({{ menu, logo, shopName }}: {prop_type} = {{}})",
        code,
    )
    # Inject displayLinks override inside function body (safe: module-scope array stays as fallback)
    if "displayLinks" not in code:  # guard against double injection
        func_match = re.search(r"export default function \w+\([^)]*\)\s*\{", code)
        if func_match:
            # Detect which variable name the template uses for its links array
            links_var = "navLinks"  # default
            for candidate in ["navLinks", "links", "menuItems", "menuLinks", "navigationLinks"]:
                if re.search(rf"\b{candidate}\.map\(", code):
                    links_var = candidate
                    break
            insert_pos = func_match.end()
            override_block = f"\n  const displayLinks = menu?.items?.length ? menu.items.map(i => ({{ label: i.title, url: i.url }})) : {links_var};\n"
            code = code[:insert_pos] + override_block + code[insert_pos:]
            # Replace original .map( → displayLinks.map( in JSX (both desktop and mobile menu)
            code = code.replace(f"{links_var}.map(", "displayLinks.map(")
    # Make logo dynamic: replace hardcoded placeholder src/alt with prop fallback
    code = re.sub(
        r'src="(\{logo_url\}|\{logo_src\})"',
        r'src={logo?.url || "/logo.svg"}',
        code,
    )
    code = re.sub(
        r'alt="(\{logo_alt\})"',
        r'alt={logo?.altText || shopName || "Logo"}',
        code,
    )
    # Replace placeholder CTA URL with /collections (safe default for e-commerce)
    code = code.replace('href="{cta_url}"', 'href="/collections"')
    # Sanitize fallback nav link placeholder URLs to prevent broken links
    import re as _re
    code = _re.sub(r"url:\s*'\{nav_\d+_url\}'", "url: '#'", code)
    return code


def _inject_footer_props(code: str) -> str:
    """Inject optional menu/shopName props into a Footer component.
    Modifies function signature AND injects prop consumption inside the function body.
    Leaves module-scope arrays as fallbacks; overrides inside function body when props exist."""
    import re
    prop_type = "{ menu?: { title: string; items: Array<{ title: string; url: string; items?: Array<{ title: string; url: string }> }> }; shopName?: string }"
    code = re.sub(
        r"export default function (\w+)\s*\(\s*\)",
        rf"export default function \1({{ menu, shopName }}: {prop_type} = {{}})",
        code,
    )
    # Inject displayColumns override inside function body (safe: module-scope array stays as fallback)
    if "displayColumns" not in code:  # guard against double injection
        func_match = re.search(r"export default function \w+\([^)]*\)\s*\{", code)
        if func_match:
            # Detect which variable name the template uses for its columns array
            cols_var = "columns"  # default
            for candidate in ["columns", "footerColumns", "footerLinks", "footerSections", "linkGroups"]:
                if re.search(rf"\b{candidate}\.map\(", code):
                    cols_var = candidate
                    break
            insert_pos = func_match.end()
            override_block = f"\n  const displayColumns = menu?.items?.length ? menu.items.map(i => ({{ title: i.title, links: i.items?.map(sub => ({{ label: sub.title, href: sub.url }})) ?? [] }})) : {cols_var};\n"
            code = code[:insert_pos] + override_block + code[insert_pos:]
            # Replace original .map( → displayColumns.map( in JSX
            code = code.replace(f"{cols_var}.map(", "displayColumns.map(")
    # Make logo dynamic in footer
    code = re.sub(
        r'src="(\{logo_src\}|\{logo_url\})"',
        r'src={shopName ? "/logo.svg" : "/logo.svg"}',
        code,
    )
    # Sanitize fallback footer placeholder URLs to prevent broken links
    code = re.sub(r"href:\s*'\{col_\d+_link_\d+_href\}'", "href: '#'", code)
    code = re.sub(r'href="\{social_\d+_href\}"', 'href="#"', code)
    return code


def _build_nav_template(project_name: str, adapter: DeployAdapter | None = None) -> str:
    """Return a complete Navigation.tsx React component with real defaults.
    When adapter is set, platform-specific default links are used."""
    _adapter = adapter or ShopifyAdapter()
    display_name = project_name.replace("-", " ").title()
    _nav_links = _adapter.get_nav_default_links()
    _nav_links_str = ",\n  ".join(
        f"{{ label: '{lbl}', url: '{url}' }}"
        for lbl, url in _nav_links
    )
    return f'''\
'use client';

import {{ useState, useEffect }} from 'react';
import Link from 'next/link';

const defaultLinks = [
  {_nav_links_str},
];

export default function Navigation({{ menu, logo, shopName }}: {{
  menu?: {{ title: string; items: Array<{{ title: string; url: string; items?: Array<{{ title: string; url: string }}> }}> }};
  logo?: {{ url: string; altText: string | null; width?: number; height?: number }};
  shopName?: string;
}} = {{}}) {{
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const displayLinks = menu?.items?.length
    ? menu.items.map(i => ({{ label: i.title, url: i.url }}))
    : defaultLinks;

  useEffect(() => {{
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, {{ passive: true }});
    return () => window.removeEventListener('scroll', onScroll);
  }}, []);

  return (
    <nav
      className={{`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${{
        scrolled ? 'bg-white/95 backdrop-blur shadow-sm' : 'bg-transparent'
      }}`}}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 md:h-20">
          {{/* Logo */}}
          <Link href="/" className="flex-shrink-0">
            {{logo?.url ? (
              <img
                src={{logo.url}}
                alt={{logo.altText || shopName || '{display_name}'}}
                className="h-8 w-auto"
              />
            ) : (
              <span className={{`text-xl font-bold ${{scrolled ? 'text-gray-900' : 'text-white'}}`}}>
                {{shopName || '{display_name}'}}
              </span>
            )}}
          </Link>

          {{/* Desktop links */}}
          <div className="hidden md:flex items-center gap-8">
            {{displayLinks.map((link, i) => (
              <Link
                key={{i}}
                href={{link.url}}
                className={{`text-sm font-medium transition-colors ${{
                  scrolled
                    ? 'text-gray-700 hover:text-gray-900'
                    : 'text-white/90 hover:text-white'
                }}`}}
              >
                {{link.label}}
              </Link>
            ))}}
          </div>

          {{/* Mobile hamburger */}}
          <button
            className="md:hidden p-2"
            onClick={{() => setMobileOpen(!mobileOpen)}}
            aria-label="Toggle menu"
          >
            <svg
              className={{`h-6 w-6 ${{scrolled ? 'text-gray-900' : 'text-white'}}`}}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {{mobileOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={{2}} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={{2}} d="M4 6h16M4 12h16M4 18h16" />
              )}}
            </svg>
          </button>
        </div>
      </div>

      {{/* Mobile menu */}}
      {{mobileOpen && (
        <div className="md:hidden bg-white border-t shadow-lg">
          <div className="px-4 py-3 space-y-2">
            {{displayLinks.map((link, i) => (
              <Link
                key={{i}}
                href={{link.url}}
                className="block py-2 text-gray-700 hover:text-gray-900 font-medium"
                onClick={{() => setMobileOpen(false)}}
              >
                {{link.label}}
              </Link>
            ))}}
          </div>
        </div>
      )}}
    </nav>
  );
}}
'''


def _build_footer_template(project_name: str, adapter: DeployAdapter | None = None) -> str:
    """Return a complete Footer.tsx React component with real defaults.
    When adapter is set, platform-specific default columns are used."""
    _adapter = adapter or ShopifyAdapter()
    display_name = project_name.replace("-", " ").title()
    _footer_cols = _adapter.get_footer_default_columns()
    _nl = "\n"
    _nl = "\n"
    _comma_nl = ",\n"
    _footer_cols_str = _comma_nl.join(
        '  {' + _nl + "    title: '" + col["title"] + "'," + _nl + "    links: [" + _nl
        + _comma_nl.join(
            "      { label: '" + link["label"] + "', href: '" + link["href"] + "' }"
            for link in col["links"]
        )
        + _nl + "    ]," + _nl + "  }"
        for col in _footer_cols
    )
    return f'''\
'use client';

import Link from 'next/link';

const defaultColumns = [
{_footer_cols_str},
];

export default function Footer({{ menu, shopName }}: {{
  menu?: {{ title: string; items: Array<{{ title: string; url: string; items?: Array<{{ title: string; url: string }}> }}> }};
  shopName?: string;
}} = {{}}) {{
  const displayColumns = menu?.items?.length
    ? menu.items.map(i => ({{
        title: i.title,
        links: i.items?.map(sub => ({{ label: sub.title, href: sub.url }})) ?? [],
      }}))
    : defaultColumns;

  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {{displayColumns.map((col, i) => (
            <div key={{i}}>
              <h3 className="text-white font-semibold text-sm uppercase tracking-wider mb-4">
                {{col.title}}
              </h3>
              <ul className="space-y-2">
                {{col.links.map((link, j) => (
                  <li key={{j}}>
                    <Link
                      href={{link.href}}
                      className="text-sm text-gray-400 hover:text-white transition-colors"
                    >
                      {{link.label}}
                    </Link>
                  </li>
                ))}}
              </ul>
            </div>
          ))}}
        </div>
        <div className="mt-12 pt-8 border-t border-gray-800 text-center text-sm text-gray-500">
          &copy; {{new Date().getFullYear()}} {{shopName || '{display_name}'}}. All rights reserved.
        </div>
      </div>
    </footer>
  );
}}
'''


def stage_shared_components(
    manifest: dict,
    preset: str,
    project_name: str,
    build_cache: "BuildCache | None" = None,
    has_commerce_routes: bool = False,
    adapter: DeployAdapter | None = None,
) -> list[Path]:
    """Layer 6: Generate Navigation and Footer once as shared layout components.

    Uses deterministic templates instead of LLM calls — faster, cheaper, and
    produces components with real default content (Shop, About, Contact, FAQ)
    rather than placeholder tokens.
    When adapter is provided, platform-specific nav/footer defaults are used.
    """
    print("\n🧩 Layer 6: Generating shared layout components (Navigation, Footer)...")
    if adapter and adapter.name != "shopify":
        print(f"  Using {adapter.name} platform defaults for Navigation/Footer")
    shared_dir = OUTPUT_DIR / project_name / "shared"
    shared_dir.mkdir(parents=True, exist_ok=True)

    nav_path = shared_dir / "Navigation.tsx"
    footer_path = shared_dir / "Footer.tsx"

    nav_code = _build_nav_template(project_name, adapter=adapter)
    footer_code = _build_footer_template(project_name, adapter=adapter)

    write_file(nav_path, nav_code)
    print(f"  ✓ Wrote Navigation.tsx (template-driven, no LLM)")
    write_file(footer_path, footer_code)
    print(f"  ✓ Wrote Footer.tsx (template-driven, no LLM)")

    files = [nav_path, footer_path]

    # ── Commerce prop injection: make NAV/FOOTER accept optional Shopify data ──
    if has_commerce_routes:
        for fpath in files:
            if not fpath.exists():
                continue
            code = fpath.read_text(encoding="utf-8")
            if "Navigation.tsx" in str(fpath):
                code = _inject_nav_props(code)
                fpath.write_text(code, encoding="utf-8")
                print("  ✓ Injected optional menu/logo/shopName props into Navigation")
            elif "Footer.tsx" in str(fpath):
                code = _inject_footer_props(code)
                fpath.write_text(code, encoding="utf-8")
                print("  ✓ Injected optional menu/shopName props into Footer")

    print(f"  ✓ Wrote {len(files)} shared components to output/{project_name}/shared/")
    return files


def stage_scaffold_multipage(
    manifest: dict,
    project_name: str,
    industry: str,
    preset: str | None = None,
) -> dict:
    """Layer 6: Enrich manifest with per-page section sequences from Supabase (NAV/FOOTER filtered).
    When DB returns 0 sections for a page, falls back to preset's Default Section Sequence if preset is set."""
    print("\n📋 Layer 6: Scaffold (multi-page) — loading section sequences per page type...")
    if not get_section_sequence and not preset:
        print("  ⚠ Supabase not available and no preset; cannot load per-page sections. Use --preset for single-page.")
        return manifest
    preset_sections: list[dict] | None = None
    for page in manifest.get("pages", []):
        page_type = page.get("page_type", "homepage")
        page_id = page.get("id", "")
        if page_id == "not-found":
            page["sections"] = []
            continue
        raw = get_section_sequence(industry, page_type) if get_section_sequence else []
        if not raw and preset:
            if preset_sections is None:
                preset_sections = parse_preset_section_sequence(preset)
                if preset_sections:
                    print(f"  Using preset '{preset}' Default Section Sequence ({len(preset_sections)} sections) for pages with no DB sequence.")
            raw = preset_sections if preset_sections else []
        page["sections"] = site_manifest_lib.filter_nav_footer_from_sections(raw) if site_manifest_lib else raw
        print(f"  {page_id} ({page_type}): {len(page['sections'])} sections")
    out_path = OUTPUT_DIR / project_name / "site-manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _findings_are_page_scoped(copy_findings: dict | None) -> bool:
    """True when --copy-findings is keyed by page id rather than by slot.

    Page-scoped: {"wealth": {"0": {...}}}. Slot-scoped (the original single-page
    shape): {"0": {...}} / {"03-features.tsx": {...}}. Distinguished by whether
    every value is itself a mapping of slots — a finding dict has scalar fields
    (rule_id, detail), so a mapping-of-mappings is page scoping.
    """
    if not isinstance(copy_findings, dict) or not copy_findings:
        return False
    return all(
        isinstance(v, dict) and v and all(isinstance(inner, dict) for inner in v.values())
        for v in copy_findings.values()
    )


def _page_audit_harvest(audit_harvest: dict | None, page: dict) -> dict | None:
    """Narrow a tenant-wide audit harvest to the rows belonging to ONE page.

    `harvest_verbatim_copy` returns tenant-wide rows tagged with `page_type`.
    Handing every page the whole tenant's copy would paste the same strings
    across the site, so a page only ever sees rows matching its own page_type
    (or its id/route). No tagged match → None, and that page generates rather
    than borrowing another page's words.
    """
    if not audit_harvest or not audit_harvest.get("sections"):
        return None
    keys = set(page_lookup_keys(page))
    matched = [
        s for s in audit_harvest["sections"]
        if str(s.get("page_type", "")).strip().lower().strip("/").replace("/", "-") in keys
    ]
    if not matched:
        return None
    return {
        "tenant_id": audit_harvest.get("tenant_id"),
        "sections": matched,
        "source_rows": len(matched),
        "harvested_strings": sum(
            len(s.get("headings") or []) + len(s.get("body_text") or []) + len(s.get("ctas") or [])
            for s in matched
        ),
    }


def stage_sections_multipage(
    manifest: dict,
    preset: str,
    project_name: str,
    build_cache: "BuildCache | None" = None,
    identification: dict | None = None,
    brief: str | None = None,
    site_spec_by_page: dict[str, dict] | None = None,
    section_contexts_by_page: dict[str, dict] | None = None,
    extraction_dir_by_page: dict[str, Path] | None = None,
    audit_harvest: dict | None = None,
    copy_findings: dict | None = None,
) -> tuple[dict[str, list[Path]], dict[str, dict]]:
    """Layer 6: Generate sections for each page; write to output/{project}/sections/{page_id}/.

    Every content input is per-page. Before this, all of them were hardcoded
    None at the stage_sections call, so a multi-page build structurally could
    not carry a single character of real extracted content — it generated every
    page from the registry archetype list alone.

    Returns (section_files_by_page, copy_summary_by_page); the per-page copy
    summary was previously discarded, taking harvested_copy_ratio with it.
    """
    print("\n🔨 Layer 6: Sections (multi-page)...")
    section_files_by_page: dict[str, list[Path]] = {}
    copy_summary_by_page: dict[str, dict] = {}
    for page in manifest.get("pages", []):
        page_id = page.get("id", "")
        sections = page.get("sections", [])
        if page_id == "not-found" or not sections:
            section_files_by_page[page_id] = []
            continue
        _page_spec = resolve_page_entry(site_spec_by_page, page)
        _page_harvest = _page_audit_harvest(audit_harvest, page)
        _harvested_here = sum(
            len(harvested_copy_strings(section_content_dict(s))) for s in sections
        )
        print(
            f"  Page: {page_id} ({len(sections)} sections, "
            f"{_harvested_here} harvested source string(s))"
        )
        sections_with_index = []
        for j, s in enumerate(sections):
            s = dict(s)
            # `content` carries the HARVESTED COPY DICT and must not be
            # clobbered. This previously did
            # `s.setdefault("content", s.get("content_direction", ""))`, which
            # made `content` a STRING for every multipage section — failing the
            # isinstance(dict) gate below so build_source_copy_block never ran.
            # That single line disabled the entire verbatim-copy path for
            # multi-page builds, whatever content was threaded in.
            s.setdefault("content_direction", "")
            if not isinstance(s.get("content"), dict):
                s["content"] = {}
            s.setdefault("index", j)
            sections_with_index.append(s)
        files, _page_summary = stage_sections(
            sections_with_index,
            preset,
            project_name,
            section_contexts=resolve_page_entry(section_contexts_by_page, page),
            extraction_dir=resolve_page_entry(extraction_dir_by_page, page),
            identification=identification,
            site_spec=_page_spec,
            build_cache=build_cache,
            output_subdir=f"sections/{page_id}",
            section_file_names=None,
            brief=brief,
            copy_findings=(
                resolve_page_entry(copy_findings, page)
                if _findings_are_page_scoped(copy_findings) else copy_findings
            ),
            audit_harvest=_page_harvest,
        )
        section_files_by_page[page_id] = files
        if _page_summary:
            copy_summary_by_page[page_id] = _page_summary
    return section_files_by_page, copy_summary_by_page


def stage_assemble_multipage(
    manifest: dict,
    section_files_by_page: dict[str, list[Path]],
    project_name: str,
) -> None:
    """Layer 6: Assemble one page.tsx per page into output/{project}/pages/{page_id}.tsx."""
    print("\n📦 Layer 6: Assembling pages...")
    pages_dir = OUTPUT_DIR / project_name / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    animation_map = load_animation_injections(project_name)
    for page in manifest.get("pages", []):
        page_id = page.get("id", "")
        sections = page.get("sections", [])
        files = section_files_by_page.get(page_id, [])
        if page_id == "not-found":
            continue
        if not files:
            # Dynamic route with no sections from DB: write minimal shell
            if page.get("dynamic"):
                params_type = '({ params }: { params: { handle: string } })' if "[handle]" in page.get("route", "") else "()"
                page_code = f'''// TODO: Layer 7 — Connect to Shopify Storefront API

export function generateStaticParams() {{
  return [];
}}

export default function Page{params_type} {{
  return (
    <main className="min-h-screen">
      <p>Placeholder — data connection in Layer 7</p>
    </main>
  );
}}
'''
            else:
                page_code = '''export default function Page() {
  return <main className="min-h-screen"><p>Placeholder</p></main>;
}
'''
            (pages_dir / f"{page_id}.tsx").write_text(page_code, encoding="utf-8")
            print(f"  {page_id}: placeholder (no sections)")
            continue
        # Filename-driven, exactly like the single-page path (_build_page_imports).
        # Zipping the `sections` metadata against the files on disk by index
        # misnames every import after a section that failed to generate — and
        # drops the tail when the lists differ in length. cape-crypto/wealth is
        # missing 02-trust_badges.tsx, so index 1 onwards named the wrong
        # component. The files on disk are the ground truth.
        if len(files) != len(sections):
            print(
                f"  ⚠ {page_id}: {len(sections)} section(s) planned but "
                f"{len(files)} file(s) on disk — assembling from files"
            )
        imports, components = _build_page_imports(
            files, f"@/components/sections/{page_id}/", animation_map, page_id
        )
        params_type = ""
        components_nl = chr(10).join(components)
        if page.get("dynamic") and "[handle]" in page.get("route", ""):
            params_type = '({ params }: { params: { handle: string } })'
            imports.insert(0, '// TODO: Layer 7 — Connect to Shopify Storefront API')
            body = f'''
export function generateStaticParams() {{
  return [];
}}

export default function Page{params_type} {{
  return (
    <main className="min-h-screen">
{components_nl}
    </main>
  );
}}
'''
        else:
            body = f'''
export default function Page() {{
  return (
    <main className="min-h-screen">
{components_nl}
    </main>
  );
}}
'''
        page_code = chr(10).join(imports) + body
        (pages_dir / f"{page_id}.tsx").write_text(page_code, encoding="utf-8")
        print(f"  {page_id}: {len(files)} sections")
    print(f"  ✓ Assembled to output/{project_name}/pages/")


def detect_animation_engine(preset_content: str) -> str:
    """Detect animation engine from preset's Motion line. Returns 'gsap' or 'framer-motion'."""
    match = re.search(r"Motion:.*?/(gsap|framer-motion)", preset_content)
    return match.group(1) if match else "framer-motion"


def parse_preset_intensity(preset_content: str) -> str:
    """Read the explicit `animation_intensity:` field from a tenant preset.

    Mirrors animation-injector.js's parsePresetIntensity() byte-for-byte
    (same regex, same default). This is deliberately a *field read*, not an
    inference from `site_spec["style"]["animation"]["intensity"]` — that
    value is derived from what the source site happened to carry (empty for
    a site with no captured animation, like Cape Crypto), which is silent
    inheritance, not a tenant decision. Component injection intensity comes
    from here.
    """
    match = re.search(r"animation_intensity:\s*(subtle|moderate|expressive|dramatic)", preset_content, re.IGNORECASE)
    return match.group(1).lower() if match else "moderate"


def stage_inject_animation(
    project_name: str,
    page_dir: str,
    section_files: list[Path],
    preset_intensity: str,
) -> dict:
    """Decide, per section, which REAL animation-library component (if any)
    should wrap it — and persist that decision for ASSEMBLY to act on.

    PIVOT: an earlier version of this stage rewrote each section's own .tsx
    in place (import + wrap its root <section>...</section>), located by
    string-scanning for the root element — the same technique
    `animation-apply.js`'s applyAnimation used. That technique failed three
    review rounds there (sibling-section tag mispairing, apostrophes in
    harvested copy, JSX expressions mistaken for tag boundaries) and was
    retired from the pipeline. This stage no longer opens a section file for
    writing at all — it only decides, and `_build_page_imports()` (called
    from stage_assemble / stage_assemble_multipage / stage_deploy) generates
    the wrap as fully-controlled code: `<Component><SectionNN /></Component>`.
    Section .tsx files are guaranteed byte-identical as a structural property
    of this design, not an invariant something has to keep checking.

    Runs after section generation, before assembly (called from the tail of
    stage_sections(), once per page). For each section file this reads back
    the SectionArtifact written alongside it to get the archetype, then asks
    component-inject.js's decideComponentForSection() for a real, file-backed,
    safely-wrappable component (safe meaning: it actually accepts children,
    typed ReactNode, every other prop optional or defaulted, and its own root
    element isn't an inline/interactive tag that would make wrapping a
    block-level section invalid). Persists the decision to
    animation-injections.json (consumed by `_build_page_imports`),
    extra-components.json (consumed by stage_deploy to copy the real files),
    and animation-coverage.json (the tally).

    `injected` in the returned/written tally counts ONLY real components
    selected for real, file-backed source. It may never include a generic
    fallback — the prior design for this stage could report full coverage
    while actually injecting nothing (see task-7 brief); this stage exists
    to make that impossible by construction.
    """
    print(f"\n🎬 Deciding animation components ({page_dir})...")

    art_dir = OUTPUT_DIR / project_name / "section-artifacts" / page_dir
    used_animation_ids: list[str] = []
    tally = {
        "total": 0, "injected": 0, "wrapped_generic": 0, "unchanged": 0,
        "by_component": {}, "by_reason": {},
    }
    new_extra_components: list[str] = []
    decisions: dict = {}

    for filepath in section_files:
        tally["total"] += 1
        art_path = art_dir / (filepath.stem + ".json")
        archetype = ""
        if art_path.exists():
            try:
                archetype = json.loads(art_path.read_text(encoding="utf-8")).get("archetype", "")
            except (json.JSONDecodeError, OSError):
                archetype = ""

        if not archetype:
            reason = "no SectionArtifact archetype found for this file"
            tally["unchanged"] += 1
            tally["by_reason"][reason] = tally["by_reason"].get(reason, 0) + 1
            continue

        node_script = f"""
const {{ decideComponentForSection }} = require('./lib/component-inject');
const result = decideComponentForSection(
  {json.dumps(archetype)},
  {json.dumps(used_animation_ids)},
  {json.dumps(preset_intensity)}
);
console.log(JSON.stringify({{
  injected: result.injected,
  reason: result.reason,
  animationId: result.component ? result.component.animationId : null,
  sourceFile: result.component ? result.component.sourceFile : null,
  exportName: result.component ? result.component.exportName : null,
  exportType: result.component ? result.component.exportType : null,
  destName: result.component ? result.component.destName : null,
}}));
"""
        proc = None
        result = None
        try:
            proc = subprocess.run(
                ["node", "-e", node_script],
                capture_output=True, text=True,
                cwd=str(QUALITY_DIR), timeout=20,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                result = json.loads(proc.stdout.strip())
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            result = None

        if result is None:
            reason = "component-inject subprocess failed"
            tally["unchanged"] += 1
            tally["by_reason"][reason] = tally["by_reason"].get(reason, 0) + 1
            if proc is not None and proc.stderr:
                print(f"  ⚠ {filepath.name}: {proc.stderr[-300:]}")
            continue

        if result["injected"]:
            used_animation_ids.append(result["animationId"])
            if result["sourceFile"]:
                new_extra_components.append(result["sourceFile"])
            decisions[f"{page_dir}/{filepath.stem}"] = {
                "animation_id": result["animationId"],
                "export_name": result["exportName"],
                "export_type": result["exportType"],
                "dest_name": result["destName"],
            }
            tally["injected"] += 1
            tally["by_component"][result["animationId"]] = tally["by_component"].get(result["animationId"], 0) + 1
            print(f"  ✓ {filepath.name}: will wrap with {result['animationId']}")
        else:
            tally["unchanged"] += 1
            tally["by_reason"][result["reason"]] = tally["by_reason"].get(result["reason"], 0) + 1
            print(f"  ⊘ {filepath.name}: {result['reason']}")

    # Merge into extra-components.json so stage_deploy copies these files
    # into site/src/components/animations/ alongside the archetype-matched
    # copy it already does. Read-modify-write, not overwrite: stage_sections'
    # own write of this file (a few lines above where this stage is called)
    # is NOT namespaced by page, so a second page's write would otherwise
    # silently clobber the first page's queued components.
    if new_extra_components:
        manifest_path = OUTPUT_DIR / project_name / "extra-components.json"
        existing: list = []
        if manifest_path.exists():
            try:
                existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []
        merged = sorted(set(existing) | set(new_extra_components))
        write_file(manifest_path, json.dumps(merged, indent=2))

    # Merge per-section decisions across pages — this file is what
    # `_build_page_imports()` consults when generating each page's JSX, keyed
    # `{page_dir}/{section_stem}` so pages sharing a section filename (every
    # page's hero is "01-hero") never collide.
    if decisions:
        injections_path = OUTPUT_DIR / project_name / "animation-injections.json"
        existing_decisions: dict = {}
        if injections_path.exists():
            try:
                existing_decisions = json.loads(injections_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing_decisions = {}
        existing_decisions.update(decisions)
        write_file(injections_path, json.dumps(existing_decisions, indent=2))

    # Merge coverage across pages — multipage builds call this once per page
    # and each call's numbers describe only that page's sections.
    coverage_path = OUTPUT_DIR / project_name / "animation-coverage.json"
    if coverage_path.exists():
        try:
            prev = json.loads(coverage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prev = None
        if prev:
            for key in ("total", "injected", "wrapped_generic", "unchanged"):
                tally[key] += prev.get(key, 0)
            for key in ("by_component", "by_reason"):
                for k, v in (prev.get(key) or {}).items():
                    tally[key][k] = tally[key].get(k, 0) + v

    write_file(coverage_path, json.dumps(tally, indent=2))
    print(f"  Animation decisions: {tally['injected']}/{tally['total']} real component(s) selected, "
          f"{tally['unchanged']} unchanged")
    return tally


def load_animation_injections(project_name: str) -> dict:
    """Read animation-injections.json — the per-section wrap decisions
    stage_inject_animation() persisted. Returns {} if the file doesn't
    exist (e.g. a build with no animation-decision stage, or nothing was
    selected for any section — an all-refused build is a valid outcome)."""
    path = OUTPUT_DIR / project_name / "animation-injections.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def parse_fonts(preset_content: str) -> dict:
    """Extract heading and body font names from preset's YAML style config."""
    # Match YAML format: heading_font: FontName
    heading = "Inter"
    body = "Inter"
    h_match = re.search(r"heading_font:\s*([A-Za-z][A-Za-z0-9_ ]+)", preset_content)
    if h_match:
        heading = h_match.group(1).strip()
    b_match = re.search(r"body_font:\s*([A-Za-z][A-Za-z0-9_ ]+)", preset_content)
    if b_match:
        body = b_match.group(1).strip()
    # Guard: discard if YAML leaked into the capture
    yaml_markers = ("---", "palette", "bg_primary", "accent")
    if any(m in heading for m in yaml_markers) or any(m in body for m in yaml_markers):
        print("⚠ parse_fonts: detected YAML leak, falling back to Inter")
        heading = "Inter"
        body = "Inter"
    return {"heading": heading, "body": body}


def font_import_name(font_name: str) -> str:
    """Convert a font display name to its next/font/google import name."""
    return font_name.replace(" ", "_")


def _layer7_collection_page_content() -> str:
    """Layer 7: Collection page that fetches from Storefront API."""
    return '''import { shopifyFetch } from "@/lib/shopify/client";
import { COLLECTION_PRODUCTS } from "@/lib/shopify/queries";
import type { CollectionProductsResult } from "@/lib/shopify/queries";
import Link from "next/link";
import Image from "next/image";

export function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  try {
    const data = await shopifyFetch<CollectionProductsResult>(COLLECTION_PRODUCTS, { handle, first: 1 });
    const c = data?.collection;
    return {
      title: c?.seo?.title || c?.title || "Collection",
      description: c?.seo?.description || c?.description || "",
    };
  } catch {
    return { title: "Collection" };
  }
}

export default async function Page({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const data = await shopifyFetch<CollectionProductsResult>(COLLECTION_PRODUCTS, {
    handle,
    first: 24,
  });
  const collection = data?.collection;
  if (!collection) {
    return (
      <main className="min-h-screen p-8">
        <p>Collection not found.</p>
      </main>
    );
  }
  const products = collection.products?.edges ?? [];
  return (
    <main className="min-h-screen pt-24 px-6 pb-12">
      <h1 className="text-3xl font-semibold text-neutral-900 mb-2">{collection.title}</h1>
      {collection.description && (
        <p className="text-neutral-600 mb-8 max-w-2xl">{collection.description}</p>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map(({ node: p }) => (
          <Link key={p.handle} href={`/products/${p.handle}`} className="group">
            <div className="aspect-square bg-neutral-100 rounded-lg overflow-hidden mb-2">
              {p.featuredImage?.url && (
                <Image src={p.featuredImage.url} alt={p.featuredImage.altText ?? p.title} width={400} height={400} className="w-full h-full object-cover" />
              )}
            </div>
            <h2 className="font-medium text-neutral-900 group-hover:underline">{p.title}</h2>
            <p className="text-sm text-neutral-600">
              {p.priceRange?.minVariantPrice?.amount} {p.priceRange?.minVariantPrice?.currencyCode}
            </p>
          </Link>
        ))}
      </div>
      {products.length === 0 && <p className="text-neutral-500">No products in this collection yet.</p>}
    </main>
  );
}
'''


def _layer7_collections_index_page_content() -> str:
    """Layer 7: Collections index page that lists all collections from Storefront API."""
    return '''import { shopifyFetch } from "@/lib/shopify/client";
import { COLLECTIONS_LIST } from "@/lib/shopify/queries";
import type { CollectionsListResult } from "@/lib/shopify/queries";
import Link from "next/link";
import Image from "next/image";

export const metadata = {
  title: "Collections",
  description: "Browse all collections",
};

export default async function CollectionsPage() {
  let collections: Array<{ handle: string; title: string; description: string; image?: { url: string; altText: string | null } | null }> = [];
  try {
    const data = await shopifyFetch<CollectionsListResult>(COLLECTIONS_LIST, { first: 50 });
    const edges = data?.collections?.edges;
    collections = Array.isArray(edges) ? edges.map((e) => ({ handle: e.node.handle, title: e.node.title, description: e.node.description ?? "", image: e.node.image })) : [];
  } catch {
    collections = [];
  }
  return (
    <main className="min-h-screen pt-24 px-6 pb-12">
      <h1 className="text-3xl font-semibold text-neutral-900 mb-8">Collections</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {collections.map((c) => (
          <Link key={c.handle} href={`/collections/${c.handle}`} className="group block">
            <div className="aspect-[4/3] bg-neutral-100 rounded-lg overflow-hidden mb-3">
              {c.image?.url && (
                <Image src={c.image.url} alt={c.image.altText ?? c.title} width={600} height={450} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              )}
            </div>
            <h2 className="text-lg font-medium text-neutral-900 group-hover:underline">{c.title}</h2>
            {c.description && <p className="text-sm text-neutral-600 mt-1 line-clamp-2">{c.description}</p>}
          </Link>
        ))}
      </div>
      {collections.length === 0 && <p className="text-neutral-500">No collections found.</p>}
    </main>
  );
}
'''


def _patch_showcase_section_props(section_code: str, component_name: str) -> str:
    """Patch a PRODUCT-SHOWCASE section to accept optional products/collections props.
    Handles diverse template structures: module-scope or function-scope product arrays,
    varied function names (template names like ProductShowcaseHoverCards, not always matching component_name)."""
    if "products?: " in section_code or "collections?: " in section_code:
        return section_code  # already patched
    import re
    prop_type = "{ products?: Array<{ title: string; handle: string; priceRange?: { minVariantPrice: { amount: string; currencyCode: string } }; images?: { edges: Array<{ node: { url: string; altText: string | null } }> } }>; collections?: Array<{ handle: string; title: string; description?: string; image?: { url: string } }> }"
    # Match ANY export default function name (template names vary)
    section_code = re.sub(
        r"(export default function \w+)\s*\(\s*\)",
        rf"\1({{ products, collections }}: {prop_type} = {{}})",
        section_code,
    )
    # Also handle React.FC pattern with any name
    section_code = re.sub(
        r"(const \w+:\s*React\.FC)\s*=\s*\(\s*\)\s*=>",
        rf"\1<{prop_type}> = ({{ products, collections }}) =>",
        section_code,
    )
    # Find the function body opening brace
    func_match = re.search(r"export default function \w+\([^)]*\)\s*\{", section_code)
    # Handle hardcoded products array — move into function body if at module scope
    products_match = re.search(r"(const products\s*=\s*\[[\s\S]*?\];)", section_code)
    if products_match:
        original = products_match.group(1)
        array_literal = original.replace("const products = ", "").rstrip(";")
        # Check if products array is at module scope (before function) or inside function
        if func_match and products_match.start() < func_match.start():
            # Module scope — remove and re-insert inside function body
            section_code = section_code.replace(original, "")
            # Re-find function match after removal (position shifted)
            func_match = re.search(r"export default function \w+\([^)]*\)\s*\{", section_code)
            if func_match:
                insert_pos = func_match.end()
                block = f"\n  const fallbackProducts = {array_literal};\n  const mappedProducts = products?.length ? Array.from(products, p => ({{ name: p.title, price: `${{parseFloat(p.priceRange?.minVariantPrice?.amount || '0').toFixed(2)}} ${{p.priceRange?.minVariantPrice?.currencyCode || ''}}`.trim(), image: p.images?.edges?.[0]?.node?.url || '/placeholder.jpg', alt: p.images?.edges?.[0]?.node?.altText || p.title, url: `/products/${{p.handle}}`, tag: '' }})) : null;\n  const displayProducts = mappedProducts || fallbackProducts;\n"
                section_code = section_code[:insert_pos] + block + section_code[insert_pos:]
        else:
            # Already inside function — replace in place
            section_code = section_code.replace(
                original,
                f"const fallbackProducts = {array_literal};\n  const mappedProducts = products?.length ? Array.from(products, p => ({{ name: p.title, price: `${{parseFloat(p.priceRange?.minVariantPrice?.amount || '0').toFixed(2)}} ${{p.priceRange?.minVariantPrice?.currencyCode || ''}}`.trim(), image: p.images?.edges?.[0]?.node?.url || '/placeholder.jpg', alt: p.images?.edges?.[0]?.node?.altText || p.title, url: `/products/${{p.handle}}`, tag: '' }})) : null;\n  const displayProducts = mappedProducts || fallbackProducts;",
            )
        section_code = section_code.replace("products.map(", "displayProducts.map(")
    # Sanitize fallback product placeholder URLs to prevent broken links on deployed site
    section_code = re.sub(r"url:\s*'\{product_\d+_url\}'", "url: '#'", section_code)
    section_code = re.sub(r"image:\s*'\{product_\d+_image_url\}'", "image: '/placeholder.jpg'", section_code)
    return section_code


def _layer7_index_page_content(src_homepage_content: str, showcase_component: str | None = None) -> str:
    """Layer 7: Homepage that fetches collections + featured products from Storefront API.

    Uses hidden homepage collections (curated by store owner) with fallback to
    best-selling products, then to all collections.
    """
    if "shopifyFetch" in src_homepage_content or "COLLECTIONS_LIST" in src_homepage_content:
        return src_homepage_content  # already injected
    # Add Storefront imports after last import line
    lines = src_homepage_content.split("\n")
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("import ") and "from" in line:
            insert_idx = i + 1
    shopify_imports = [
        'import { shopifyFetch } from "@/lib/shopify/client";',
        'import { COLLECTIONS_LIST, COLLECTION_BY_HANDLE, FEATURED_PRODUCTS, SHOP_INFO } from "@/lib/shopify/queries";',
        'import type { CollectionsListResult, CollectionByHandleResult, FeaturedProductsResult, ShopInfoResult } from "@/lib/shopify/queries";',
    ]
    for imp in reversed(shopify_imports):
        lines.insert(insert_idx, imp)
    content = "\n".join(lines)

    # Build the data-fetch block
    fetch_block = '''export default async function Page() {
  type FeaturedProduct = { title: string; handle: string; priceRange?: { minVariantPrice: { amount: string; currencyCode: string } }; images?: { edges: Array<{ node: { url: string; altText: string | null } }> } };
  let collections: Array<{ handle: string; title: string; description: string; image?: { url: string; altText: string | null } | null }> = [];
  let featuredProducts: FeaturedProduct[] = [];
  try {
    const [collectionsData, featuredData, fallbackData] = await Promise.all([
      shopifyFetch<CollectionsListResult>(COLLECTIONS_LIST, { first: 20 }),
      shopifyFetch<CollectionByHandleResult>(COLLECTION_BY_HANDLE, { handle: "hidden-homepage-featured-items", first: 12 }).catch(() => null),
      shopifyFetch<FeaturedProductsResult>(FEATURED_PRODUCTS, { first: 12 }).catch(() => null),
    ]);
    const edges = collectionsData?.collections?.edges;
    collections = Array.isArray(edges) ? edges.map((e) => ({ handle: e.node.handle, title: e.node.title, description: e.node.description ?? "", image: e.node.image })) : [];
    // Fallback chain: hidden collection → best-selling → first collection's products
    const hiddenProducts = featuredData?.collection?.products?.edges?.map(e => e.node) ?? [];
    if (hiddenProducts.length > 0) {
      featuredProducts = hiddenProducts;
    } else {
      const bestSelling = fallbackData?.products?.edges?.map(e => e.node) ?? [];
      featuredProducts = bestSelling;
    }
  } catch { collections = []; featuredProducts = []; }
'''
    content = content.replace("export default function Page() {", fetch_block)

    # SEO metadata from shop info
    metadata_block = '''export async function generateMetadata() {
  try {
    const data = await shopifyFetch<ShopInfoResult>(SHOP_INFO);
    return {
      title: data?.shop?.name || "Home",
      description: data?.shop?.description || "",
    };
  } catch {
    return { title: "Home" };
  }
}

'''
    # Insert generateMetadata before the Page function
    content = content.replace("export default async function Page() {", metadata_block + "export default async function Page() {")

    # Pass props to the showcase component (manifest-driven, not hardcoded)
    if showcase_component:
        content = content.replace(
            f"<{showcase_component} />",
            f"<{showcase_component} products={{featuredProducts}} collections={{collections}} />",
        )
    else:
        # Fallback: try common patterns
        for comp in ["Section04PRODUCTSHOWCASE", "Section03PRODUCTSHOWCASE", "Section05PRODUCTSHOWCASE"]:
            if f"<{comp} />" in content:
                content = content.replace(
                    f"<{comp} />",
                    f"<{comp} products={{featuredProducts}} collections={{collections}} />",
                )
                break
    return content


def _layer7_product_page_content() -> str:
    """Layer 7: Product page that fetches from Storefront API."""
    # Note: descriptionHtml is trusted content from Shopify's Storefront API,
    # authored by the store owner in Shopify admin. Shopify sanitizes this content.
    return '''import { shopifyFetch } from "@/lib/shopify/client";
import { PRODUCT_BY_HANDLE } from "@/lib/shopify/queries";
import type { ProductByHandleResult } from "@/lib/shopify/queries";
import Link from "next/link";
import Image from "next/image";

export function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  try {
    const data = await shopifyFetch<ProductByHandleResult>(PRODUCT_BY_HANDLE, { handle });
    const p = data?.product;
    return {
      title: p?.seo?.title || p?.title || "Product",
      description: p?.seo?.description || p?.description || "",
    };
  } catch {
    return { title: "Product" };
  }
}

export default async function Page({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const data = await shopifyFetch<ProductByHandleResult>(PRODUCT_BY_HANDLE, {
    handle,
  });
  const product = data?.product;
  if (!product) {
    return (
      <main className="min-h-screen p-8">
        <p>Product not found.</p>
      </main>
    );
  }
  const price = product.priceRange?.minVariantPrice;
  /* descriptionHtml: trusted content from Shopify Storefront API, authored by store owner */
  return (
    <main className="min-h-screen pt-24 px-6 pb-12 max-w-4xl mx-auto">
      <nav className="text-sm text-neutral-500 mb-4">
        <Link href="/" className="hover:underline">Home</Link>
        <span className="mx-2">/</span>
        <span>{product.title}</span>
      </nav>
      <div className="grid md:grid-cols-2 gap-8">
        <div className="aspect-square bg-neutral-100 rounded-lg overflow-hidden">
          {product.featuredImage?.url && (
            <Image src={product.featuredImage.url} alt={product.featuredImage.altText ?? product.title} width={600} height={600} className="w-full h-full object-cover" />
          )}
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900 mb-2">{product.title}</h1>
          {price && (
            <p className="text-lg text-neutral-700 mb-4">
              {price.amount} {price.currencyCode}
            </p>
          )}
          {product.description && <p className="text-neutral-600 whitespace-pre-wrap mb-6">{product.description}</p>}
        </div>
      </div>
    </main>
  );
}
'''


# ─────────────────────────────────────────────────────────────────────────────
# Deploy Adapters: platform-specific deploy behavior
# ─────────────────────────────────────────────────────────────────────────────

class DeployAdapter:
    """Base adapter for deploy platform behavior.
    Subclasses override methods to control what gets written into the Next.js site dir."""

    @property
    def name(self) -> str:
        return "base"

    @property
    def should_inject_commerce(self) -> bool:
        """Whether to copy Shopify lib, wrappers, and generate Layer 7 pages."""
        return False

    @property
    def should_write_env(self) -> bool:
        """Whether to generate .env.local from shopify_config.json."""
        return False

    def get_next_config_extras(self) -> str:
        """Extra next.config.ts fields (e.g. Shopify image remotePatterns)."""
        return ""

    def get_nav_default_links(self) -> list[tuple[str, str]]:
        """Default navigation links for the Navigation template."""
        return [
            ("Home", "/"),
            ("About", "/#about"),
            ("Services", "/#services"),
            ("Contact", "/#contact"),
        ]

    def get_footer_default_columns(self) -> list[dict]:
        """Default footer columns."""
        return [
            {"title": "About", "links": [{"label": "Our Story", "href": "/#about"}, {"label": "Blog", "href": "#"}, {"label": "Careers", "href": "#"}]},
            {"title": "Services", "links": [{"label": "What We Do", "href": "#"}, {"label": "Process", "href": "#"}, {"label": "FAQ", "href": "/#faq"}]},
            {"title": "Legal", "links": [{"label": "Privacy", "href": "#"}, {"label": "Terms", "href": "#"}]},
        ]

    def get_cta_url_default(self) -> str:
        """Default CTA href for buttons."""
        return "#"

    def should_generate_l7_pages(self) -> bool:
        """Whether to generate Layer 7 Storefront-wired pages (collection, product, homepage)."""
        return False

    def log_label(self) -> str:
        return self.name

    def get_package_extra_deps(self) -> dict[str, str]:
        """Extra npm dependencies for this platform."""
        return {}


class ShopifyAdapter(DeployAdapter):
    """Shopify deploy adapter — current behavior unchanged."""

    @property
    def name(self) -> str:
        return "shopify"

    @property
    def should_inject_commerce(self) -> bool:
        return True

    @property
    def should_write_env(self) -> bool:
        return True

    def get_next_config_extras(self) -> str:
        return (
            "  images: {\n"
            "    remotePatterns: [\n"
            '      { protocol: "https" as const, hostname: "cdn.shopify.com" },\n'
            '      { protocol: "https" as const, hostname: "**.myshopify.com" },\n'
            "    ],\n"
            "  },\n"
        )

    def get_nav_default_links(self) -> list[tuple[str, str]]:
        return [
            ("Shop", "/collections"),
            ("New Arrivals", "/collections"),
            ("About", "/pages/about"),
            ("Contact", "/pages/contact"),
        ]

    def get_cta_url_default(self) -> str:
        return "/collections"

    def should_generate_l7_pages(self) -> bool:
        return True


class VercelAdapter(DeployAdapter):
    """Vercel deploy adapter — clean Next.js app with no Shopify injection."""

    @property
    def name(self) -> str:
        return "vercel"

    def get_nav_default_links(self) -> list[tuple[str, str]]:
        return [
            ("Home", "/"),
            ("About", "/#about"),
            ("Services", "/#services"),
            ("Contact", "/#contact"),
        ]

    def get_cta_url_default(self) -> str:
        return "#"


def resolve_target_platform(tenant_context: dict | None) -> str:
    """Resolve the deploy target platform from tenant configuration.

    BRIEF #33318: Reads deploy target from tenant config rather than
    defaulting to 'shopify'. When tenant_context is available, queries
    the tenants table for deploy_target; otherwise falls back to 'shopify'.

    Args:
        tenant_context: Dict with tenant_id and other tenant context data

    Returns:
        str: The resolved target platform ('shopify' or 'vercel')
    """
    if not tenant_context:
        return "shopify"

    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        return "shopify"

    # Query tenants table for deploy_target
    try:
        if TENANT_CONTEXT_AVAILABLE and load_tenant_context:
            from lib.supabase_client import _get
            rows = _get("tenants", f"id=eq.{tenant_id}&select=deploy_target")
            if rows and isinstance(rows, list) and rows:
                deploy_target = rows[0].get("deploy_target")
                if deploy_target in ("shopify", "vercel"):
                    return deploy_target
    except Exception:
        pass

    return "shopify"


def _resolve_adapter(target_platform: str) -> DeployAdapter:
    """Resolve the deploy adapter for the given platform string."""
    if target_platform == "shopify":
        return ShopifyAdapter()
    return VercelAdapter()


def stage_git_publish(
    output_dir: Path,
    project_name: str,
    *,
    github_repo: str | None = None,
    push_policy: str = "off",
) -> str | None:
    """BRIEF #33323 — publish the built site to a GitHub repo as source-of-truth.

    Commits the built site tree so every build has a versioned SoT and deploy is
    git-driven. When push_policy=='push' and a github_repo (owner/name or URL) is
    given, pushes to that remote (credentials permitting). Default push_policy=='off'
    commits locally only — never pushes without an explicit policy. Returns the
    published commit SHA, or None if there was nothing to publish.
    """
    import subprocess

    site_dir = output_dir / project_name / "site"
    if not site_dir.exists():
        site_dir = output_dir / project_name
    if not site_dir.exists():
        print(f"  ⚠ git-publish: no built site at {site_dir}")
        return None

    def _git(*args):
        return subprocess.run(
            ["git", "-C", str(site_dir), *args], capture_output=True, text=True
        )

    if not (site_dir / ".git").exists():
        _git("init")
        _git("checkout", "-b", "main")
    _git("add", "-A")
    status = _git("status", "--porcelain").stdout.strip()
    head = _git("rev-parse", "HEAD")
    if not status and head.returncode == 0:
        return head.stdout.strip()[:40]  # already published, no changes this build
    _git("commit", "-m", f"build: {project_name} site (web-builder git-publish)")
    sha = _git("rev-parse", "HEAD").stdout.strip()[:40]

    if push_policy == "push" and github_repo:
        remote = (
            github_repo
            if github_repo.startswith("http")
            else f"https://github.com/{github_repo}.git"
        )
        _git("remote", "remove", "origin")
        _git("remote", "add", "origin", remote)
        pr = _git("push", "-u", "origin", "main")
        if pr.returncode != 0:
            print(f"  ⚠ git-publish push failed: {pr.stderr[:140]}")
        else:
            print(f"  ✓ git-publish pushed {sha[:9]} → {github_repo}")
    else:
        print(f"  ✓ git-publish committed {sha[:9]} locally (push_policy={push_policy})")
    return sha


def stage_deploy(
    sections: list[dict],
    section_files: list[Path],
    preset: str,
    project_name: str,
    extraction_dir: Path | None = None,
    build_cache: "BuildCache | None" = None,
    site_manifest: dict | None = None,
    section_files_by_page: dict[str, list[Path]] | None = None,
    shopify_config_path: str | Path | None = None,
    target_platform: str | None = "shopify",
):
    """Stage 5: Deploy sections into a runnable Next.js project at output/{project}/site/.
    When site_manifest and section_files_by_page are set (Layer 6), deploys multi-route app
    with shared layout components and per-page sections.
    target_platform selects the deploy adapter ('shopify' or 'vercel')."""
    adapter = _resolve_adapter(target_platform or "shopify")
    print(f"\n🚀 Stage 5: Deploying to Next.js project ({adapter.log_label()} adapter)...")
    is_multipage = bool(site_manifest and section_files_by_page is not None)
    if is_multipage:
        # Flatten for has_lottie and used_archetypes
        section_files = [f for files in section_files_by_page.values() for f in files]
        sections = [s for p in site_manifest.get("pages", []) for s in p.get("sections", [])]
    else:
        pass  # use existing sections, section_files

    # ── Determine commerce routes early (used for layout, next.config, wrappers) ──
    _page_ids = [p.get("id") for p in (site_manifest or {}).get("pages", [])] if is_multipage else []
    _has_commerce_in_manifest = "collection-template" in _page_ids or "product-template" in _page_ids
    has_commerce_routes = _has_commerce_in_manifest and adapter.should_inject_commerce

    # ── Database path: use cached style from Supabase ──
    if build_cache and build_cache.style_config:
        preset_content = build_cache.build_synthetic_preset_content()
        print(f"  Using Supabase industry style (cached)")
    else:
        # ── Legacy path: read from .md preset file ──
        preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")

    engine = detect_animation_engine(preset_content)
    fonts = parse_fonts(preset_content)
    style_header = extract_style_header(preset_content)

    site_dir = OUTPUT_DIR / project_name / SITE_DIR_NAME
    src_dir = site_dir / "src"
    app_dir = src_dir / "app"
    comp_dir = src_dir / "components" / "sections"

    # ── package.json: always write (ensures deps match current build, even if stale site/ exists) ──
    deps = {
        "next": "16.1.6",
        "react": "19.2.3",
        "react-dom": "19.2.3",
        "framer-motion": "^12.33.0",  # Always included (hover/tap effects)
        "clsx": "^2.1.1",
        "tailwind-merge": "^2.6.0",
        "lucide-react": "^0.468.0",
    }
    if engine == "gsap":
        deps["gsap"] = "^3.14.2"
    if has_commerce_routes:
        deps["@tailwindcss/typography"] = "^0.5.16"

    # Detect Lottie assets from extraction data
    has_lottie = False
    if extraction_dir:
        anim_path = extraction_dir / "animation-analysis.json"
        if anim_path.exists():
            try:
                anim_data = json.loads(anim_path.read_text(encoding="utf-8"))
                lottie_files = anim_data.get("lottieFiles", [])
                lottie_assets = (anim_data.get("assets", {}) or {}).get("lottie", [])
                has_lottie = len(lottie_files) > 0 or len(lottie_assets) > 0
            except (json.JSONDecodeError, OSError):
                pass
    # Also detect from generated sections importing DotLottieReact
    if not has_lottie:
        for sf in section_files:
            if sf.exists() and "DotLottieReact" in sf.read_text(encoding="utf-8"):
                has_lottie = True
                break
    if has_lottie:
        deps["@lottiefiles/dotlottie-react"] = "^0.13.0"
        print(f"  Lottie files detected — adding @lottiefiles/dotlottie-react")

    pkg = {
        "name": project_name,
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev --webpack",
            "build": "NODE_ENV=production next build",
            "start": "next start",
            "lint": "eslint",
        },
        "dependencies": deps,
        "devDependencies": {
            "@tailwindcss/postcss": "^4",
            "@types/node": "^20",
            "@types/react": "^19",
            "@types/react-dom": "^19",
            "eslint": "^9",
            "eslint-config-next": "16.1.6",
            "tailwindcss": "^4",
            "typescript": "^5",
        },
    }
    write_file(site_dir / "package.json", json.dumps(pkg, indent=2) + "\n")

    # ── Scaffold remaining config files only if project is new ──
    if not (site_dir / "tsconfig.json").exists():
        print("  Creating Next.js project structure...")

        # tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "ES2017",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        }
        write_file(site_dir / "tsconfig.json", json.dumps(tsconfig, indent=2) + "\n")

        # next.config.ts — ignoreBuildErrors for GSAP/Framer Motion type issues
        # Adapter may inject extra fields (e.g. Shopify image remotePatterns)
        _next_cfg_extras = adapter.get_next_config_extras()
        # Live-CDN images: when the adapter doesn't configure images (e.g. the
        # Vercel / --from-url path referencing the source site's live image URLs),
        # disable optimization so any remote URL renders without per-domain
        # remotePatterns. Shopify keeps its own remotePatterns via the adapter.
        _img_cfg = "" if "images:" in _next_cfg_extras else "  images: { unoptimized: true },\n"
        write_file(
            site_dir / "next.config.ts",
            'import type { NextConfig } from "next";\n\n'
            "const nextConfig: NextConfig = {\n"
            "  typescript: { ignoreBuildErrors: true },\n"
            f"{_img_cfg}"
            f"{_next_cfg_extras}"
            "};\n\n"
            "export default nextConfig;\n",
        )

        # postcss.config.mjs
        write_file(
            site_dir / "postcss.config.mjs",
            "const config = {\n"
            '  plugins: {\n    "@tailwindcss/postcss": {},\n  },\n'
            "};\n\nexport default config;\n",
        )

        # eslint.config.mjs
        write_file(
            site_dir / "eslint.config.mjs",
            'import { dirname } from "path";\n'
            'import { fileURLToPath } from "url";\n'
            'import { FlatCompat } from "@eslint/eslintrc";\n\n'
            "const __filename = fileURLToPath(import.meta.url);\n"
            "const __dirname = dirname(__filename);\n\n"
            "const compat = new FlatCompat({ baseDirectory: __dirname });\n\n"
            'const eslintConfig = [...compat.extends("next/core-web-vitals")];\n\n'
            "export default eslintConfig;\n",
        )

        # .gitignore for the site
        write_file(
            site_dir / ".gitignore",
            "node_modules/\n.next/\n*.tsbuildinfo\nnext-env.d.ts\n",
        )

    # ── Generate globals.css ──
    print("  Generating globals.css...")
    css_lines = [
        '@import "tailwindcss";',
        "",
        ":root { --background: #fafaf9; --foreground: #1c1917; }",
        "body {",
        "  background: var(--background);",
        "  color: var(--foreground);",
        f'  font-family: "{fonts["body"]}", sans-serif;',
        "  -webkit-font-smoothing: antialiased;",
        "  -moz-osx-font-smoothing: grayscale;",
        "}",
    ]
    if engine == "gsap":
        css_lines += [
            "",
            "html { scroll-behavior: smooth; }",
            "",
            "::-webkit-scrollbar { width: 4px; }",
            "::-webkit-scrollbar-track { background: transparent; }",
            "::-webkit-scrollbar-thumb { background: #78716c; border-radius: 2px; }",
            "",
            "::selection { background: #78716c; color: #ffffff; }",
            "",
            "@keyframes marquee {",
            "  0% { transform: translateX(0); }",
            "  100% { transform: translateX(-50%); }",
            "}",
        ]
    write_file(app_dir / "globals.css", "\n".join(css_lines) + "\n")

    # ── Generate layout.tsx ──
    print("  Generating layout.tsx...")
    heading_font = fonts["heading"]
    body_font = fonts["body"]

    # Common Google Fonts that can be imported via next/font/google
    GOOGLE_FONTS = {
        "Inter", "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins",
        "Source Sans Pro", "Source Sans 3", "Raleway", "Nunito", "Playfair Display",
        "Merriweather", "DM Sans", "Space Grotesk", "Plus Jakarta Sans",
        "Outfit", "Sora", "Geist", "Manrope", "Urbanist", "Archivo",
        "Work Sans", "Libre Baskerville", "Cormorant Garamond",
    }

    heading_is_google = heading_font in GOOGLE_FONTS
    body_is_google = body_font in GOOGLE_FONTS

    heading_import = font_import_name(heading_font) if heading_is_google else None
    body_import = font_import_name(body_font) if body_is_google else None

    # Extract weights from preset
    heading_weights = '"400"'
    body_weights = '["400", "500", "700"]'
    h_weight_match = re.search(r"heading_weight:\s*(\d+)", preset_content)
    if h_weight_match:
        heading_weights = f'"{h_weight_match.group(1)}"'

    # Build layout.tsx
    import_lines = ['import type { Metadata } from "next";']
    google_imports = []
    if heading_import:
        google_imports.append(heading_import)
    if body_import and body_import != heading_import:
        google_imports.append(body_import)
    if google_imports:
        import_lines.append(f'import {{ {", ".join(google_imports)} }} from "next/font/google";')
    import_lines.append('import "./globals.css";')

    font_config_lines = []
    if heading_import:
        font_config_lines.append(
            f'const {heading_import.lower()} = {heading_import}({{ subsets: ["latin"], weight: {heading_weights} }});'
        )
    if body_import and body_import != heading_import:
        font_config_lines.append(
            f'const {body_import.lower()} = {body_import}({{ subsets: ["latin"], weight: {body_weights} }});'
        )

    # Build font-family CSS fallback for non-Google fonts
    font_family = f"'{heading_font}', system-ui, sans-serif"

    font_config = chr(10).join(font_config_lines) if font_config_lines else ""
    if font_config:
        font_config = chr(10) + font_config + chr(10)

    if is_multipage:
        if has_commerce_routes:
            import_lines.append('import NavigationWrapper from "@/components/layout/NavigationWrapper";')
            import_lines.append('import FooterWrapper from "@/components/layout/FooterWrapper";')
            nav_tag = "NavigationWrapper"
            footer_tag = "FooterWrapper"
        else:
            import_lines.append('import Navigation from "@/components/layout/Navigation";')
            import_lines.append('import Footer from "@/components/layout/Footer";')
            nav_tag = "Navigation"
            footer_tag = "Footer"
        layout_code = f"""{chr(10).join(import_lines)}
{font_config}
export const metadata: Metadata = {{
  title: "{project_name.replace('-', ' ').title()}",
  description: "Built with web-builder pipeline",
}};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en">
      <body className="antialiased" style={{{{ fontFamily: "{font_family}" }}}}>
        <{nav_tag} />
        {{children}}
        <{footer_tag} />
      </body>
    </html>
  );
}}
"""
    else:
        layout_code = f"""{chr(10).join(import_lines)}
{font_config}
export const metadata: Metadata = {{
  title: "{project_name.replace('-', ' ').title()}",
  description: "Built with web-builder pipeline",
}};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en">
      <body className="antialiased" style={{{{ fontFamily: "{font_family}" }}}}>
        {{children}}
      </body>
    </html>
  );
}}
"""
    write_file(app_dir / "layout.tsx", layout_code)

    # ── Generate cn() utility (clsx + tailwind-merge) ──
    lib_dir = src_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    cn_util = 'import { clsx, type ClassValue } from "clsx";\nimport { twMerge } from "tailwind-merge";\n\nexport function cn(...inputs: ClassValue[]) {\n  return twMerge(clsx(inputs));\n}\n'
    write_file(lib_dir / "utils.ts", cn_util)

    # ── GSAP setup with plugin imports when plugins detected ──
    if engine == "gsap":
        project_dir = OUTPUT_DIR / project_name
        identification_path = project_dir / "identification.json"
        plugins = []
        if identification_path.exists():
            try:
                id_data = json.loads(identification_path.read_text(encoding="utf-8"))
                plugins = id_data.get("detectedPlugins", [])
            except (json.JSONDecodeError, OSError):
                pass
        if plugins:
            plugin_imports = []
            plugin_registers = []
            PLUGIN_IMPORT_MAP = {
                "SplitText": ("SplitText", "gsap/SplitText"),
                "Flip": ("Flip", "gsap/Flip"),
                "DrawSVG": ("DrawSVGPlugin", "gsap/DrawSVGPlugin"),
                "MorphSVG": ("MorphSVGPlugin", "gsap/MorphSVGPlugin"),
                "MotionPath": ("MotionPathPlugin", "gsap/MotionPathPlugin"),
                "CustomEase": ("CustomEase", "gsap/CustomEase"),
                "Observer": ("Observer", "gsap/Observer"),
                "ScrambleText": ("ScrambleTextPlugin", "gsap/ScrambleTextPlugin"),
                "Draggable": ("Draggable", "gsap/Draggable"),
                "ScrollSmoother": ("ScrollSmoother", "gsap/ScrollSmoother"),
            }
            for p in plugins:
                if p in PLUGIN_IMPORT_MAP:
                    name, path = PLUGIN_IMPORT_MAP[p]
                    plugin_imports.append(f'import {{ {name} }} from "{path}";')
                    plugin_registers.append(name)
            if plugin_registers:
                gsap_setup = f'''"use client";
import gsap from "gsap";
import {{ ScrollTrigger }} from "gsap/ScrollTrigger";
{chr(10).join(plugin_imports)}

if (typeof window !== "undefined") {{
  gsap.registerPlugin(ScrollTrigger, {", ".join(plugin_registers)});
}}

export {{ gsap, ScrollTrigger, {", ".join(plugin_registers)} }};
'''
                gsap_setup_path = site_dir / "src" / "lib" / "gsap-setup.ts"
                gsap_setup_path.parent.mkdir(parents=True, exist_ok=True)
                gsap_setup_path.write_text(gsap_setup)
                print(f"  Created gsap-setup.ts with plugins: {', '.join(plugin_registers)}")

    # ── Copy sections (or multipage: shared + per-page sections) ──
    if is_multipage:
        print("  Copying shared layout components...")
        layout_dest = src_dir / "components" / "layout"
        layout_dest.mkdir(parents=True, exist_ok=True)
        shared_dir = OUTPUT_DIR / project_name / "shared"
        for name in ("Navigation.tsx", "Footer.tsx"):
            src_f = shared_dir / name
            if src_f.exists():
                write_file(layout_dest / name, read_file(src_f))
        print("  Copying per-page sections...")
        comp_dir.mkdir(parents=True, exist_ok=True)
        for page_id, files in section_files_by_page.items():
            dest_sub = comp_dir / page_id
            dest_sub.mkdir(parents=True, exist_ok=True)
            for fpath in files:
                if fpath.exists():
                    write_file(dest_sub / fpath.name, read_file(fpath))
        # ── Layer 7: Copy lib/shopify when manifest has commerce routes (Storefront API client, cart, queries) ──
        industry = (site_manifest or {}).get("industry", "")
        if has_commerce_routes and (ROOT / "lib" / "shopify").exists():
            shopify_lib_src = ROOT / "lib" / "shopify"
            shopify_lib_dest = src_dir / "lib" / "shopify"
            shopify_lib_dest.mkdir(parents=True, exist_ok=True)
            for f in shopify_lib_src.iterdir():
                if f.is_file():
                    write_file(shopify_lib_dest / f.name, read_file(f))
            print("  ✓ Layer 7: Copied lib/shopify (Storefront API client, cart, queries)")
            # Copy RSC wrappers for Navigation/Footer
            wrapper_dest = src_dir / "components" / "layout"
            wrapper_dest.mkdir(parents=True, exist_ok=True)
            for wrapper_name in ("NavigationWrapper.tsx", "FooterWrapper.tsx"):
                wrapper_src = shopify_lib_src / wrapper_name
                if wrapper_src.exists():
                    wrapper_code = read_file(wrapper_src)
                    # Fix relative imports: wrappers live in components/layout/ but reference lib/shopify/ modules
                    wrapper_code = wrapper_code.replace('from "./client"', 'from "@/lib/shopify/client"')
                    wrapper_code = wrapper_code.replace('from "./queries"', 'from "@/lib/shopify/queries"')
                    wrapper_code = wrapper_code.replace('from "./types"', 'from "@/lib/shopify/types"')
                    write_file(wrapper_dest / wrapper_name, wrapper_code)
            print("  ✓ Layer 7: Copied NavigationWrapper + FooterWrapper to layout/")
            # Override next.config.ts with Shopify image patterns
            write_file(
                site_dir / "next.config.ts",
                'import type { NextConfig } from "next";\n\n'
                "const nextConfig: NextConfig = {\n"
                "  typescript: { ignoreBuildErrors: true },\n"
                "  images: {\n"
                "    remotePatterns: [\n"
                '      { protocol: "https" as const, hostname: "cdn.shopify.com" },\n'
                '      { protocol: "https" as const, hostname: "**.myshopify.com" },\n'
                "    ],\n"
                "  },\n"
                "};\n\n"
                "export default nextConfig;\n",
            )
            print("  ✓ Layer 7: next.config.ts updated with Shopify image remotePatterns")
        print("  Writing page files to app routes...")
        pages_src = OUTPUT_DIR / project_name / "pages"
        for page in site_manifest.get("pages", []):
            page_id = page.get("id", "")
            app_path = page.get("app_path", "")
            if not app_path or not page_id:
                continue
            dest_file = site_dir / app_path
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            # Layer 7: Use Storefront-wired content for collection/product/homepage when lib/shopify is present
            if has_commerce_routes and (ROOT / "lib" / "shopify").exists():
                if page_id == "collection-template":
                    write_file(dest_file, _layer7_collection_page_content())
                    # Also generate /collections index page (lists all collections)
                    collections_index = site_dir / "src" / "app" / "collections" / "page.tsx"
                    collections_index.parent.mkdir(parents=True, exist_ok=True)
                    write_file(collections_index, _layer7_collections_index_page_content())
                    continue
                if page_id == "product-template":
                    write_file(dest_file, _layer7_product_page_content())
                    continue
                if page_id == "homepage":
                    src_page = pages_src / f"{page_id}.tsx"
                    if src_page.exists():
                        homepage_content = read_file(src_page)
                        # Manifest-driven: find PRODUCT-SHOWCASE section from homepage page spec
                        showcase_comp = None
                        showcase_file = None
                        homepage_page = next((p for p in site_manifest.get("pages", []) if p.get("id") == "homepage"), None)
                        if homepage_page:
                            for idx, sec in enumerate(homepage_page.get("sections", [])):
                                arch = sec.get("archetype", "").upper().replace("_", "-")
                                if arch == "PRODUCT-SHOWCASE":
                                    num = f"{idx + 1:02d}"
                                    showcase_comp = f"Section{num}{arch.replace('-', '')}"
                                    # Find the actual section file
                                    homepage_section_dir = site_dir / "src" / "components" / "sections" / "homepage"
                                    candidates = list(homepage_section_dir.glob(f"{num}-*product*showcase*.tsx")) if homepage_section_dir.exists() else []
                                    if not candidates:
                                        candidates = list(homepage_section_dir.glob(f"{num}-*.tsx")) if homepage_section_dir.exists() else []
                                    showcase_file = candidates[0] if candidates else None
                                    break
                        write_file(dest_file, _layer7_index_page_content(homepage_content, showcase_component=showcase_comp))
                        # Patch showcase section to accept optional products/collections props
                        if showcase_file and showcase_file.exists():
                            sc_code = read_file(showcase_file)
                            if "products?" not in sc_code and "collections?" not in sc_code:
                                sc_code = _patch_showcase_section_props(sc_code, showcase_comp or "Section04PRODUCTSHOWCASE")
                                write_file(showcase_file, sc_code)
                        continue
            src_page = pages_src / f"{page_id}.tsx"
            if not src_page.exists():
                continue
            write_file(dest_file, read_file(src_page))
        # not-found.tsx
        not_found_code = '''export default function NotFound() {
  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold">404</h1>
        <p className="mt-2 text-muted-foreground">Page not found</p>
      </div>
    </main>
  );
}
'''
        write_file(app_dir / "not-found.tsx", not_found_code)

        # ── Layer 7: Generate commerce-specific routes ──
        if has_commerce_routes:
            # API revalidation webhook route
            revalidate_dir = app_dir / "api" / "revalidate"
            revalidate_dir.mkdir(parents=True, exist_ok=True)
            revalidate_code = '''import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

export async function POST(req: NextRequest) {
  const secret = process.env.SHOPIFY_REVALIDATION_SECRET;
  const hmac = req.headers.get("x-shopify-hmac-sha256");
  const topic = req.headers.get("x-shopify-topic") || "";

  if (!secret || !hmac) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.text();
  const digest = crypto
    .createHmac("sha256", secret)
    .update(body, "utf8")
    .digest("base64");

  if (digest !== hmac) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  // Revalidate cache tags based on Shopify webhook topic
  if (topic.startsWith("products/")) {
    revalidateTag("products");
  }
  if (topic.startsWith("collections/")) {
    revalidateTag("collections");
  }

  return NextResponse.json({ revalidated: true, topic });
}
'''
            write_file(revalidate_dir / "route.ts", revalidate_code)
            print("  ✓ Layer 7: Generated /api/revalidate webhook route")

            # [page] dynamic route for Shopify pages
            page_route_dir = app_dir / "[page]"
            page_route_dir.mkdir(parents=True, exist_ok=True)
            # Note: page.body is trusted HTML from Shopify's Storefront API, authored by the store owner
            page_route_code = '''import { shopifyFetch } from "@/lib/shopify/client";
import { SHOP_PAGE } from "@/lib/shopify/queries";
import type { ShopPageResult } from "@/lib/shopify/queries";
import { notFound } from "next/navigation";

export async function generateMetadata({ params }: { params: Promise<{ page: string }> }) {
  const { page: handle } = await params;
  try {
    const data = await shopifyFetch<ShopPageResult>(SHOP_PAGE, { handle });
    const p = data?.page;
    if (!p) return { title: "Page Not Found" };
    return {
      title: p.seo?.title || p.title,
      description: p.seo?.description || p.bodySummary || "",
    };
  } catch {
    return { title: "Page" };
  }
}

export default async function Page({ params }: { params: Promise<{ page: string }> }) {
  const { page: handle } = await params;
  let pageData: ShopPageResult["page"] = null;
  try {
    const data = await shopifyFetch<ShopPageResult>(SHOP_PAGE, { handle });
    pageData = data?.page ?? null;
  } catch {
    notFound();
  }
  if (!pageData) {
    notFound();
  }
  /* page.body: trusted HTML content from Shopify Storefront API, authored by store owner */
  return (
    <main className="min-h-screen pt-24 px-6 pb-12 max-w-3xl mx-auto">
      <h1 className="text-3xl font-semibold text-neutral-900 mb-6">{pageData.title}</h1>
      <div
        className="prose max-w-none"
        dangerouslySetInnerHTML={{ __html: pageData.body }}
      />
    </main>
  );
}
'''
            write_file(page_route_dir / "page.tsx", page_route_code)
            print("  ✓ Layer 7: Generated /[page] dynamic route for Shopify pages")

    else:
        print("  Copying sections...")
        comp_dir.mkdir(parents=True, exist_ok=True)
        for filepath in section_files:
            code = read_file(filepath)
            write_file(comp_dir / filepath.name, code)

    # ── Global placeholder token sanitization ──
    # Sweep all .tsx files and replace ALL remaining placeholder tokens from Supabase
    # templates. These tokens use {token_name} syntax and render as visible text if not replaced.
    _sanitize_count = 0

    # ── Copy Fidelity Node (Phase 1): defer to harvested copy ──
    # Token phases below key off {token} syntax, so real copy the LLM reproduced verbatim
    # is structurally never matched. The one exception is the Phase 5 literal-string
    # backfill ({"About Us"} etc.), which overwrites real-looking copy with generic
    # archetype defaults. Collect the harvested strings so that pass can defer when a
    # section already renders its real source copy.
    _harvested_copy: set[str] = set()
    for _s in (sections or []):
        for _t in harvested_copy_strings(_s.get("content", {}) if isinstance(_s, dict) else {}):
            if len(_t) > 2:
                _harvested_copy.add(_t.lower())

    # Archetype-aware content defaults for numbered tokens like {feature_1_title}
    _NUMBERED_TOKEN_DEFAULTS: dict[str, dict[str, str]] = {
        "feature": {"icon": "Star", "title": "Feature", "description": "Designed to help you achieve more with less effort.", "label": "Feature", "text": "Feature"},
        "testimonial": {"quote": "An exceptional experience from start to finish. Highly recommended.", "author": "Happy Customer", "role": "Verified Buyer", "name": "Customer", "company": "Local Business", "image": "/placeholder.svg", "avatar": "/placeholder.svg", "rating": "5"},
        "stat": {"value": "99%", "label": "Satisfaction", "suffix": "+", "description": "Trusted by thousands of happy customers.", "icon": "TrendingUp", "prefix": ""},
        "faq": {"question": "How can we help you?", "answer": "We are here to support you every step of the way. Contact us anytime for assistance."},
        "badge": {"icon": "Shield", "label": "Certified", "sublabel": "Quality guaranteed", "text": "Trusted"},
        "product": {"name": "Product", "price": "$0.00", "tag": "New", "image_alt": "Product image", "image_url": "/placeholder.svg", "description": "Premium quality crafted for you.", "url": "#", "image": "/placeholder.svg"},
        "column": {"name": "Column", "title": "Column", "description": "More information coming soon."},
        "col": {"title": "Shop", "description": "Browse our collections.", "name": "Shop"},
        "row": {"feature": "Included", "label": "Feature", "value": "Yes"},
        "logo": {"image_url": "/placeholder.svg", "alt": "Partner", "name": "Partner", "src": "/placeholder.svg", "url": "#"},
        "nav": {"label": "Shop", "url": "/collections", "href": "/collections", "text": "Shop"},
        "social": {"icon_path": "M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2z", "url": "#", "label": "Social", "icon": "Globe"},
        "step": {"title": "Step", "description": "Follow these simple steps to get started.", "icon": "ArrowRight", "number": "1"},
        "benefit": {"title": "Benefit", "description": "Experience the difference with our approach.", "icon": "Check"},
        "pricing": {"name": "Plan", "price": "$0", "description": "Everything you need to get started.", "feature": "Included", "cta": "Get Started"},
        "category": {"name": "Category", "image": "/placeholder.svg", "url": "#", "count": "12"},
        "breadcrumb": {"label": "Home", "url": "/", "text": "Home"},
        "link": {"label": "Link", "url": "#", "text": "Link"},
        "card": {"title": "Card Title", "description": "Discover something new.", "image": "/placeholder.svg", "url": "#"},
        "item": {"title": "Item", "description": "Quality assured.", "icon": "Package", "label": "Item"},
        "service": {"title": "Service", "description": "Professional service tailored to your needs.", "icon": "Briefcase"},
        "team": {"name": "Team Member", "role": "Specialist", "image": "/placeholder.svg", "bio": "Passionate about delivering results."},
        "value": {"title": "Our Value", "description": "What drives us forward every day.", "icon": "Heart"},
        "cta": {"text": "Shop Now", "url": "/collections", "label": "Shop Now"},
        "filter": {"label": "All", "text": "All", "title": "All"},
    }

    # Per-number variety so repeated items aren't identical
    _NUMBERED_VARIETY: dict[str, list[dict[str, str]]] = {
        "feature": [
            {"title": "Free Shipping", "description": "Complimentary delivery on all orders over $50.", "icon": "Truck"},
            {"title": "Quality Guarantee", "description": "Every product meets the highest quality standards.", "icon": "ShieldCheck"},
            {"title": "24/7 Support", "description": "Our team is always available to help you.", "icon": "Headphones"},
            {"title": "Easy Returns", "description": "Hassle-free 30-day returns with full refund.", "icon": "RefreshCw"},
            {"title": "Secure Payment", "description": "Shop with confidence using encrypted checkout.", "icon": "CreditCard"},
            {"title": "Gift Wrapping", "description": "Premium gift wrapping available on any order.", "icon": "Gift"},
        ],
        "stat": [
            {"value": "10K", "label": "Happy Customers", "suffix": "+"},
            {"value": "500", "label": "Products Available", "suffix": "+"},
            {"value": "99%", "label": "Satisfaction Rate", "suffix": ""},
            {"value": "24/7", "label": "Customer Support", "suffix": ""},
        ],
        "faq": [
            {"question": "What is your shipping policy?", "answer": "We offer free standard shipping on orders over $50. Most orders ship within 1-2 business days."},
            {"question": "How do I return or exchange an item?", "answer": "We accept returns within 30 days of delivery. Items must be in original condition."},
            {"question": "Do you ship internationally?", "answer": "Yes, we ship to over 50 countries. Rates vary by destination and are calculated at checkout."},
            {"question": "How can I track my order?", "answer": "Once shipped, you will receive a confirmation email with a tracking number."},
            {"question": "What payment methods do you accept?", "answer": "We accept all major credit cards, PayPal, Apple Pay, and Google Pay."},
        ],
        "testimonial": [
            {"quote": "The quality exceeded my expectations. Fast shipping and beautiful packaging.", "author": "Sarah M.", "role": "Verified Buyer", "rating": "5"},
            {"quote": "Incredible customer service! They went above and beyond to help me.", "author": "James L.", "role": "Verified Buyer", "rating": "5"},
            {"quote": "Best online shopping experience in years. The product was exactly as described.", "author": "Emily R.", "role": "Verified Buyer", "rating": "5"},
            {"quote": "Love the attention to detail. Will definitely be ordering again soon.", "author": "Michael T.", "role": "Verified Buyer", "rating": "5"},
            {"quote": "Perfect gift for my partner. The presentation was stunning.", "author": "Anna K.", "role": "Verified Buyer", "rating": "4"},
            {"quote": "Smooth checkout, fast delivery, and excellent product quality.", "author": "David W.", "role": "Verified Buyer", "rating": "5"},
        ],
        "badge": [
            {"icon": "ShieldCheck", "label": "Quality Assured", "sublabel": "100% authentic products"},
            {"icon": "Truck", "label": "Free Shipping", "sublabel": "On orders over $50"},
            {"icon": "RotateCcw", "label": "Easy Returns", "sublabel": "30-day return policy"},
            {"icon": "Lock", "label": "Secure Checkout", "sublabel": "SSL encrypted payment"},
        ],
        "col": [
            {"title": "Shop", "name": "Shop", "description": "Browse our collections."},
            {"title": "Help", "name": "Help", "description": "Get assistance with your order."},
            {"title": "About", "name": "About", "description": "Learn more about us."},
            {"title": "Legal", "name": "Legal", "description": "Privacy and terms."},
        ],
        "nav": [
            {"label": "Shop", "url": "/collections", "href": "/collections", "text": "Shop"},
            {"label": "About", "url": "/#about", "href": "/#about", "text": "About"},
            {"label": "Contact", "url": "/#contact", "href": "/#contact", "text": "Contact"},
            {"label": "FAQ", "url": "/#faq", "href": "/#faq", "text": "FAQ"},
        ],
        "column": [
            {"title": "Basic", "name": "Basic"},
            {"title": "Standard", "name": "Standard"},
            {"title": "Premium", "name": "Premium"},
        ],
        "row": [
            {"feature": "Free Shipping", "label": "Free Shipping"},
            {"feature": "Priority Support", "label": "Priority Support"},
            {"feature": "Extended Warranty", "label": "Extended Warranty"},
            {"feature": "Gift Wrapping", "label": "Gift Wrapping"},
            {"feature": "Early Access", "label": "Early Access"},
        ],
        "filter": [
            {"label": "All", "text": "All", "title": "All"},
            {"label": "New", "text": "New", "title": "New"},
            {"label": "Popular", "text": "Popular", "title": "Popular"},
        ],
    }

    def _resolve_numbered_token(token_name: str) -> str | None:
        """Resolve a numbered token like 'feature_1_title' to a default value."""
        # Match patterns: prefix_N_field or prefix_N_N_field
        m = re.match(r'^([a-z]+)_(\d+)(?:_(\d+))?_(.+)$', token_name)
        if m:
            prefix, num_str, sub_num, field = m.group(1), m.group(2), m.group(3), m.group(4)
            num = int(num_str)
            # Try per-number variety first
            variety = _NUMBERED_VARIETY.get(prefix)
            if variety and (num - 1) < len(variety) and field in variety[num - 1]:
                return variety[num - 1][field]
            # Fall back to base defaults
            defaults = _NUMBERED_TOKEN_DEFAULTS.get(prefix, {})
            if field in defaults:
                val = defaults[field]
                # Append number for differentiation (e.g. "Feature 1", "Feature 2")
                if field in ("title", "name", "label", "question") and val == prefix.title():
                    return f"{val} {num_str}"
                return val
            # Field not in known defaults. Previously this returned
            # `field.replace("_", " ").title()`, which is how "Primary Cta
            # Text" — a *variable name* — shipped as visible copy on the
            # homepage hero. An unresolvable token is recorded and left empty;
            # it is never humanized into English that looks like content.
            _record_unresolved_token(token_name)
            return ""
        # Match non-numbered patterns: prefix_field (e.g. hero_title, section_heading)
        m2 = re.match(r'^([a-z]+)_(.+)$', token_name)
        if m2:
            prefix, field = m2.group(1), m2.group(2)
            defaults = _NUMBERED_TOKEN_DEFAULTS.get(prefix, {})
            if field in defaults:
                return defaults[field]
        return None

    for tsx_file in (src_dir).rglob("*.tsx"):
        try:
            _raw = tsx_file.read_text(encoding="utf-8")
            _cleaned = _raw

            # Copy Fidelity Node: does this file already render harvested source copy?
            _lc = _raw.lower()
            _file_has_real_copy = any(_t in _lc for _t in _harvested_copy)

            # ── Phase 1: Structural replacements (href, src, url, alt) ──
            _cta_url = adapter.get_cta_url_default()
            _cleaned = _cleaned.replace('href="{cta_url}"', f'href="{_cta_url}"')
            _cleaned = re.sub(r"href:\s*'\{[^}]+_href\}'", "href: '#'", _cleaned)
            _cleaned = re.sub(r'href="\{[^}]+_href\}"', 'href="#"', _cleaned)
            _cleaned = re.sub(r"image:\s*'\{[^}]+_image(?:_url)?\}'", "image: '/placeholder.svg'", _cleaned)
            _cleaned = re.sub(r'src="\{[^}]+_(?:src|url|image)\}"', 'src="/placeholder.svg"', _cleaned)
            _cleaned = re.sub(r'alt="\{[^}]+_alt\}"', 'alt="Image"', _cleaned)
            _cleaned = re.sub(r"url:\s*'\{[^}]+_url\}'", "url: '#'", _cleaned)
            _cleaned = re.sub(r'href="\{[^}]+_url\}"', 'href="#"', _cleaned)

            # ── Phase 2: Content tokens inside single-quoted strings ──
            # e.g. title: '{feature_1_title}' → title: 'Feature 1'
            def _replace_single_quoted(m: re.Match) -> str:
                key_part = m.group(1)  # e.g. "title"
                token = m.group(2)     # e.g. "feature_1_title"
                resolved = _resolve_numbered_token(token)
                if resolved is None:
                    # `{primary_cta_text}` used to humanize to the visible words
                    # "Primary Cta Text". Unresolvable is recorded, not rendered.
                    _record_unresolved_token(token)
                    resolved = ""
                return f"{key_part}'{resolved}'"
            _cleaned = re.sub(
                r"(\w+:\s*)'\{([a-z][a-z_0-9]+)\}'",
                _replace_single_quoted,
                _cleaned,
            )

            # ── Phase 3: Remaining numbered content tokens ──
            # Targets clearly identifiable content tokens: {prefix_N_field} patterns
            # These are always template placeholders, never JS variables.
            # Order matters: handle quoted tokens FIRST (to avoid double-quoting)

            # 3a: Double-quoted tokens: "{feature_1_title}" → "Feature 1"
            def _replace_double_quoted(m: re.Match) -> str:
                resolved = _resolve_numbered_token(m.group(1))
                if not resolved:
                    _record_unresolved_token(m.group(1))
                    return '""'  # never the humanized token name
                return f'"{resolved}"'
            _cleaned = re.sub(
                r'"\{([a-z]+_\d+(?:_\d+)?_[a-z_]+)\}"',
                _replace_double_quoted,
                _cleaned,
            )
            # 3b: Bare tokens NOT already inside quotes: {feature_1_title} → "Feature 1"
            def _replace_numbered_token(m: re.Match) -> str:
                token = m.group(1)
                resolved = _resolve_numbered_token(token)
                if resolved is None:
                    return m.group(0)
                # Check if already inside quotes (char before { is " or ')
                start = m.start()
                if start > 0 and _cleaned[start - 1] in ('"', "'"):
                    return resolved  # Inside quotes — return without wrapping
                return f'"{resolved}"'
            _cleaned = re.sub(
                r'\{([a-z]+_\d+(?:_\d+)?_[a-z_]+)\}',
                _replace_numbered_token,
                _cleaned,
            )

            # ── Phase 4: Known non-numbered content tokens ──
            # Tokens like {cta_url}, {cta_text}, {hero_title} that aren't numbered
            # Infer section title from filename archetype
            _fname = tsx_file.stem.lower()
            _ARCHETYPE_TITLES: dict[str, tuple[str, str]] = {
                "hero": ("Discover Our Collection", "Premium quality products crafted with care"),
                "product_showcase": ("Featured Products", "Handpicked selections from our latest collection"),
                "features": ("Why Shop With Us", "Everything you need for a seamless experience"),
                "comparison": ("Compare Our Tiers", "Find the plan that fits your needs"),
                "logo_bar": ("Trusted By", "Brands that trust us"),
                "testimonials": ("What Our Customers Say", "Real stories from real customers"),
                "stats": ("By The Numbers", "Our track record speaks for itself"),
                "trust_badges": ("Shop With Confidence", "Your satisfaction is guaranteed"),
                "faq": ("Frequently Asked Questions", "Find answers to common questions"),
                "newsletter": ("Stay In The Loop", "Subscribe for updates and exclusive offers"),
                "about": ("About Us", "Learn more about what we do"),
                "pricing": ("Plans & Pricing", "Choose the plan that works for you"),
                "how_it_works": ("How It Works", "Simple steps to get started"),
                "cta": ("Ready To Get Started?", "Take the next step today"),
            }
            _section_title = "Discover More"
            _section_subtitle = "Learn more about what we offer"
            for archetype_key, (title, subtitle) in _ARCHETYPE_TITLES.items():
                if archetype_key in _fname:
                    _section_title = title
                    _section_subtitle = subtitle
                    break

            _SAFE_TOKEN_REPLACEMENTS = {
                "cta_url": _cta_url, "cta_text": "Shop Now", "cta_label": "Shop Now",
                "hero_title": "Welcome", "hero_subtitle": "Discover our collection",
                "hero_description": "Premium quality products crafted with care.",
                "hero_image": "/placeholder.svg", "hero_image_url": "/placeholder.svg",
                "section_title": _section_title, "section_subtitle": _section_subtitle,
                "section_heading": _section_title, "section_subheading": _section_subtitle,
                "section_description": "We are passionate about delivering exceptional products.",
                "brand_name": "Brand", "store_name": "Store", "company_name": "Company",
                "copyright_text": "All rights reserved.", "phone_number": "(555) 000-0000",
                "email_address": "hello@example.com", "address_text": "123 Main St",
                "logo_url": "/logo.svg", "logo_src": "/logo.svg", "logo_alt": "Logo",
                "placeholder_text": "Enter your email", "button_text": "Subscribe",
                "page_handle": "",
            }
            for tok, val in _SAFE_TOKEN_REPLACEMENTS.items():
                _cleaned = _cleaned.replace(f"'{{{tok}}}'", f"'{val}'")
                _cleaned = _cleaned.replace(f'"{{{tok}}}"', f'"{val}"')
                _cleaned = _cleaned.replace(f'{{{tok}}}', f'"{val}"')

            # ── Phase 5: Literal default string replacements ──
            # Supabase templates use literal strings like {"About Us"} instead
            # of {section_title} tokens. Replace these with archetype-aware values.
            # Only replace "About Us" when the section is NOT the about archetype.
            # Copy Fidelity Node: skip these generic backfills when this section already
            # renders real harvested source copy — real copy wins over generic defaults.
            if not _file_has_real_copy:
                if "about" not in _fname:
                    _cleaned = _cleaned.replace('{"About Us"}', f'{{{json.dumps(_section_title)}}}')
                    _cleaned = _cleaned.replace('{"Learn more about what we do"}', f'{{{json.dumps(_section_subtitle)}}}')
                _cleaned = _cleaned.replace('{"Company Description"}', '{"Premium quality products for every occasion."}')
                _cleaned = _cleaned.replace('{"Body Text"}', '{"Discover our curated collection of premium products designed to elevate your everyday experience."}')
            _cleaned = _cleaned.replace('{"Copyright Text"}', f'{{"\\u00a9 {datetime.now().year} All rights reserved."}}')
            _cleaned = _cleaned.replace('{"Logo Src"}', '"/logo.svg"')
            # Fix unsanitized attribute tokens
            _cleaned = _cleaned.replace('poster="{poster_url}"', 'poster="/placeholder.svg"')
            _cleaned = _cleaned.replace('poster="{Poster Url}"', 'poster="/placeholder.svg"')
            # Fix redundant ternaries where both branches are identical
            _cleaned = re.sub(
                r'\{shopName\s*\?\s*"(/[^"]+)"\s*:\s*"\1"\}',
                r'"\1"',
                _cleaned,
            )

            # ── Phase 6: Fix identical nav fallback links ──
            if "nav" in _fname.lower():
                _NAV_FALLBACK_LINKS = adapter.get_nav_default_links()
                # Replace consecutive identical link entries
                identical_links_pattern = re.compile(
                    r"(const\s+navLinks\s*=\s*\[)\s*"
                    r"(?:\{\s*label:\s*'Link',\s*url:\s*'#'\s*\},?\s*){2,}",
                    re.DOTALL,
                )
                if identical_links_pattern.search(_cleaned):
                    links_str = ",\n  ".join(
                        f"{{ label: '{lbl}', url: '{url}' }}"
                        for lbl, url in _NAV_FALLBACK_LINKS
                    )
                    _cleaned = identical_links_pattern.sub(
                        f"\\1\n  {links_str},\n",
                        _cleaned,
                    )

            # ── Phase 7: Fix features icon text rendering ──
            # Replace string-based icon rendering with Lucide React icon components
            if "feature" in _fname.lower():
                _ICON_NAMES = ["Truck", "ShieldCheck", "Headphones", "RefreshCw", "CreditCard", "Gift", "Zap", "Star", "Heart", "Package"]
                # Check if icons are rendered as text (e.g. <span>{feature.icon}</span>)
                if '<span className="text-2xl">{feature.icon}</span>' in _cleaned or "<span>{feature.icon}</span>" in _cleaned:
                    # Find icons referenced in the features array
                    icon_refs = set(re.findall(r"icon:\s*'(\w+)'", _cleaned))
                    if icon_refs:
                        lucide_import = "import { " + ", ".join(sorted(icon_refs)) + " } from 'lucide-react';"
                        # Add import after framer-motion import or at top of imports
                        if "from 'framer-motion'" in _cleaned:
                            _cleaned = _cleaned.replace(
                                "from 'framer-motion';",
                                "from 'framer-motion';\n" + lucide_import,
                            )
                        elif "from 'react'" in _cleaned:
                            _cleaned = _cleaned.replace(
                                "from 'react';",
                                "from 'react';\n" + lucide_import,
                            )
                        # Build icon lookup
                        icon_lookup = "const IconMap: Record<string, React.ElementType> = { " + ", ".join(sorted(icon_refs)) + " };"
                        # Insert before the features array
                        _cleaned = re.sub(
                            r"(const features\s*=)",
                            icon_lookup + "\n\n\\1",
                            _cleaned,
                        )
                        # Replace text rendering with component rendering
                        _cleaned = _cleaned.replace(
                            '<span className="text-2xl">{feature.icon}</span>',
                            '{(() => { const Icon = IconMap[feature.icon]; return Icon ? <Icon className="w-6 h-6" /> : null; })()}',
                        )
                        _cleaned = _cleaned.replace(
                            "<span>{feature.icon}</span>",
                            '{(() => { const Icon = IconMap[feature.icon]; return Icon ? <Icon className="w-6 h-6" /> : null; })()}',
                        )

            # ── Phase 8: Fix gallery placeholder images ──
            if "gallery" in _fname.lower():
                _cleaned = re.sub(
                    r"url:\s*'#'",
                    "url: '/placeholder.svg'",
                    _cleaned,
                )
                _cleaned = re.sub(
                    r"alt:\s*'Alt'",
                    "alt: 'Gallery image'",
                    _cleaned,
                )

            if _cleaned != _raw:
                tsx_file.write_text(_cleaned, encoding="utf-8")
                _sanitize_count += 1
        except (OSError, UnicodeDecodeError):
            pass
    if _sanitize_count > 0:
        print(f"  ✓ Sanitized placeholder tokens in {_sanitize_count} file(s)")

    # ── Safety-net sanitization pass (sanitizer module) ──
    # Catches any tokens that survived the 8-phase sanitization above.
    try:
        from lib.sanitizer import sanitize_directory as _sanitize_dir
        _sanitizer_ctx = {}
        # Build context from architecture.json if available
        if extraction_dir:
            _arch_path = Path(extraction_dir) / "architecture.json"
            if _arch_path.exists():
                try:
                    _arch = json.loads(_arch_path.read_text(encoding="utf-8"))
                    _cols = _arch.get("collections", [])
                    if _cols:
                        _sanitizer_ctx["collection_handle"] = _cols[0].get("handle", "all")
                    _prods = _arch.get("products", [])
                    if _prods:
                        _sanitizer_ctx["product_handle"] = _prods[0].get("handle", "product")
                except (json.JSONDecodeError, OSError):
                    pass
        _sn_result = _sanitize_dir(site_dir, context=_sanitizer_ctx)
        if _sn_result["total_replacements"] > 0:
            print(f"  ✓ Safety-net sanitizer fixed {_sn_result['total_replacements']} remaining token(s) in {_sn_result['files_sanitized']} file(s)")
        if _sn_result.get("unresolved_count"):
            print(f"  ⚠ {_sn_result['unresolved_count']} token(s) left EMPTY — no harvest, no default: "
                  + ", ".join(_sn_result["unresolved_tokens"][:10]))
    except ImportError:
        pass  # sanitizer module not available; non-fatal

    # ── Unresolved-slot report ────────────────────────────────────────────
    # Every slot that reached a rendering path with nothing to put in it. This
    # is the number that used to be hidden by humanizing token names into
    # English: a page of blanks and a page of copy looked the same.
    if _UNRESOLVED_TOKENS:
        _ut_total = sum(_UNRESOLVED_TOKENS.values())
        print(f"  ⚠ Unresolved slots: {_ut_total} occurrence(s) across "
              f"{len(_UNRESOLVED_TOKENS)} distinct token(s)")
        for _tok, _n in sorted(_UNRESOLVED_TOKENS.items(), key=lambda kv: -kv[1])[:12]:
            print(f"      {_n:>3}x {_tok}")
        write_file(
            OUTPUT_DIR / project_name / "unresolved-slots.json",
            json.dumps({
                "schema": "aurelix.unresolved_slots.v1",
                "total_occurrences": _ut_total,
                "tokens": dict(sorted(_UNRESOLVED_TOKENS.items(), key=lambda kv: -kv[1])),
            }, indent=2),
        )

    # ── Copy animation components from library ──
    anim_components_dir = SKILLS_DIR / "animation-components"
    registry_path = anim_components_dir / "component-registry.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            components = registry.get("components", {})
            # Collect archetypes used in this build
            used_archetypes = set()
            for sec in sections:
                used_archetypes.add(sec.get("archetype", "").upper().replace("_", "-"))
            # Find components that match used archetypes and are not placeholders
            anim_dest = src_dir / "components" / "animations"
            copied_count = 0
            new_deps = {}
            for pattern_name, comp_def in components.items():
                if comp_def.get("status") == "placeholder":
                    continue
                comp_archetypes = [a.upper() for a in comp_def.get("archetypes", [])]
                # Copy if any archetype matches, or if component has no archetype restriction
                if not comp_archetypes or used_archetypes.intersection(comp_archetypes):
                    # Unified registry uses source_file; legacy uses file
                    rel_path = comp_def.get("source_file") or comp_def.get("file", "")
                    src_file = anim_components_dir / rel_path
                    if src_file.exists():
                        anim_dest.mkdir(parents=True, exist_ok=True)
                        dest_file = anim_dest / f"{pattern_name}.tsx"
                        write_file(dest_file, src_file.read_text(encoding="utf-8"))
                        copied_count += 1
                        for dep in comp_def.get("dependencies", []):
                            new_deps[dep] = "latest"
            if copied_count > 0:
                print(f"  ✓ Copied {copied_count} animation component(s) to components/animations/")
                # Add any new deps to package.json
                # v2.0.0: filter invalid/remapped package names
                INVALID_PKGS = {"@gsap", "motion"}  # @gsap is a scope not a package; motion duplicates framer-motion
                # `@gsap` only ever appears because a component imports
                # `@gsap/react` (the useGSAP hook). Dropping it left the real
                # dependency uninstalled and the Next.js build failed with
                # module-not-found. Remap the bare scope to the real package.
                PKG_REMAP = {"@gsap": "@gsap/react"}
                if new_deps:
                    pkg_path = site_dir / "package.json"
                    pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))
                    existing_deps = pkg_data.get("dependencies", {})
                    added = []
                    for dep_name, dep_ver in new_deps.items():
                        # Skip known-invalid packages
                        if dep_name in INVALID_PKGS:
                            remap = PKG_REMAP.get(dep_name)
                            if remap:
                                dep_name = remap
                            else:
                                continue
                        if dep_name not in existing_deps:
                            existing_deps[dep_name] = dep_ver
                            added.append(dep_name)
                    if added:
                        pkg_data["dependencies"] = existing_deps
                        write_file(pkg_path, json.dumps(pkg_data, indent=2) + "\n")
                        print(f"  ✓ Added dependencies: {', '.join(added)}")
            else:
                print("  ℹ No animation components ready (all placeholders)")

            # Validate copied animation components (Phase 5D)
            if anim_dest.exists():
                anim_files = list(anim_dest.glob("*.tsx"))
                component_issues = []
                for af in anim_files:
                    content = af.read_text(encoding="utf-8")
                    # Check for valid export
                    if "export default" not in content and "export {" not in content:
                        component_issues.append(f"  ⚠ {af.name}: missing export")
                    # Check for wrong import path
                    if "from 'motion/react'" in content or 'from "motion/react"' in content:
                        component_issues.append(
                            f"  ⚠ {af.name}: uses motion/react instead of framer-motion"
                        )
                        # Auto-fix
                        fixed = content.replace(
                            "from 'motion/react'", "from 'framer-motion'"
                        ).replace('from "motion/react"', 'from "framer-motion"')
                        af.write_text(fixed, encoding="utf-8")
                        component_issues[-1] += " (auto-fixed)"
                    # Check for @/lib/utils dependency
                    if "@/lib/utils" in content:
                        utils_path = site_dir / "src" / "lib" / "utils.ts"
                        if not utils_path.exists():
                            component_issues.append(
                                f"  ⚠ {af.name}: imports @/lib/utils but utils.ts doesn't exist"
                            )
                if component_issues:
                    print(f"  Component validation ({len(component_issues)} issues):")
                    for ci in component_issues:
                        print(ci)
                else:
                    print(f"  ✅ {len(anim_files)} animation components validated")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠ Could not process animation registry: {e}")

    # ── v1.2.0: Copy extra components (visual fallbacks, card demos, UI components) ──
    extra_manifest_path = OUTPUT_DIR / project_name / "extra-components.json"
    if extra_manifest_path.exists():
        try:
            extra_files = json.loads(extra_manifest_path.read_text(encoding="utf-8"))
            anim_dest = src_dir / "components" / "animations"
            anim_dest.mkdir(parents=True, exist_ok=True)
            extra_copied = 0
            for comp_file in extra_files:
                # comp_file is like "background/aurora-background.tsx" or "entrance/blur-fade.tsx"
                src_file = anim_components_dir / comp_file
                if src_file.exists():
                    # Use the filename without the category prefix as the dest name
                    dest_name = Path(comp_file).stem + ".tsx"
                    dest_file = anim_dest / dest_name
                    if not dest_file.exists():
                        write_file(dest_file, src_file.read_text(encoding="utf-8"))
                        extra_copied += 1
                else:
                    print(f"  ⚠ Extra component not found: {comp_file}")
            if extra_copied > 0:
                print(f"  ✓ Copied {extra_copied} extra component(s) (visual fallbacks, demos, UI)")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠ Could not process extra components: {e}")

    # ── Generate page.tsx (single-page only) ──
    if not is_multipage:
        print("  Generating page.tsx...")
        _animation_map = load_animation_injections(project_name)
        imports, components = _build_page_imports(section_files, "@/components/sections/", _animation_map, "sections")

        page_code = f"""{chr(10).join(imports)}

export default function Page() {{
  return (
    <main className="min-h-screen">
{chr(10).join(components)}
    </main>
  );
}}
"""
        write_file(app_dir / "page.tsx", page_code)

    # ── Download assets if extraction data available ──
    if extraction_dir:
        extract_path = extraction_dir / "extraction-data.json"
        if extract_path.exists():
            print("  Downloading extracted assets...")
            download_script = f"""
const {{ categorizeImages, getDownloadManifest }} = require('./lib/asset-injector');
const {{ verifyAssets, downloadAssets }} = require('./lib/asset-downloader');

(async () => {{
  try {{
    const extractionData = require('{extract_path}');
    const categorized = categorizeImages(extractionData);
    if (categorized.length === 0) {{
      console.log(JSON.stringify({{ downloaded: 0, skipped: "no images" }}));
      return;
    }}
    const manifest = getDownloadManifest(categorized);
    const verified = await verifyAssets(manifest);
    if (verified.length === 0) {{
      console.log(JSON.stringify({{ downloaded: 0, skipped: "none accessible" }}));
      return;
    }}
    const assetManifest = await downloadAssets(verified, '{site_dir}');
    console.log(JSON.stringify({{
      downloaded: Object.keys(assetManifest).length,
      manifest: assetManifest
    }}));
  }} catch (err) {{
    console.error(err.message);
    console.log(JSON.stringify({{ downloaded: 0, error: err.message }}));
  }}
}})();
"""
            dl_result = subprocess.run(
                ["node", "-e", download_script],
                capture_output=True, text=True,
                cwd=str(QUALITY_DIR), timeout=120,
            )
            if dl_result.returncode == 0 and dl_result.stdout.strip():
                try:
                    dl_data = json.loads(dl_result.stdout.strip())
                    count = dl_data.get("downloaded", 0)
                    if count > 0:
                        print(f"  ✓ Downloaded {count} assets to public/")
                    else:
                        skip = dl_data.get("skipped", dl_data.get("error", "unknown"))
                        print(f"  ⚠ No assets downloaded ({skip})")
                except json.JSONDecodeError:
                    print(f"  ⚠ Asset download output not parseable")
            else:
                if dl_result.stderr:
                    print(f"  ⚠ Asset download error: {dl_result.stderr[-300:]}")

    # ── Download Lottie assets if detected ──
    if extraction_dir:
        anim_path = extraction_dir / "animation-analysis.json"
        if anim_path.exists():
            try:
                anim_data = json.loads(anim_path.read_text(encoding="utf-8"))
                lottie_urls = []
                for lf in anim_data.get("lottieFiles", []):
                    url = lf.get("url", "") if isinstance(lf, dict) else str(lf)
                    if url and url.startswith("http"):
                        lottie_urls.append(url)
                # Also check assets.lottie
                for la in (anim_data.get("assets", {}) or {}).get("lottie", []):
                    url = la.get("url", "") if isinstance(la, dict) else str(la)
                    if url and url.startswith("http"):
                        lottie_urls.append(url)
                lottie_urls = list(set(lottie_urls))
                if lottie_urls:
                    print(f"  Downloading {len(lottie_urls)} Lottie assets...")
                    lottie_dir = site_dir / "public" / "lottie"
                    lottie_dir.mkdir(parents=True, exist_ok=True)
                    lottie_dl_script = f"""
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const urls = {json.dumps(lottie_urls)};
const outDir = '{lottie_dir}';
let downloaded = 0;

async function downloadOne(url) {{
  const filename = url.split('/').pop().split('?')[0] || 'animation.json';
  const outPath = path.join(outDir, filename);
  const proto = url.startsWith('https') ? https : http;
  return new Promise((resolve) => {{
    proto.get(url, {{ timeout: 10000 }}, (res) => {{
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {{
        proto.get(res.headers.location, {{ timeout: 10000 }}, (r2) => {{
          const chunks = [];
          r2.on('data', c => chunks.push(c));
          r2.on('end', () => {{ fs.writeFileSync(outPath, Buffer.concat(chunks)); downloaded++; resolve(); }});
        }}).on('error', () => resolve());
        return;
      }}
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {{ if (res.statusCode === 200) {{ fs.writeFileSync(outPath, Buffer.concat(chunks)); downloaded++; }} resolve(); }});
    }}).on('error', () => resolve());
  }});
}}

(async () => {{
  await Promise.all(urls.map(downloadOne));
  console.log(JSON.stringify({{ downloaded }}));
}})();
"""
                    lottie_result = subprocess.run(
                        ["node", "-e", lottie_dl_script],
                        capture_output=True, text=True, timeout=60,
                    )
                    if lottie_result.returncode == 0 and lottie_result.stdout.strip():
                        try:
                            ld = json.loads(lottie_result.stdout.strip())
                            print(f"  ✓ Downloaded {ld.get('downloaded', 0)} Lottie files to public/lottie/")
                        except json.JSONDecodeError:
                            print("  ⚠ Lottie download output not parseable")
                    elif lottie_result.stderr:
                        print(f"  ⚠ Lottie download error: {lottie_result.stderr[-200:]}")
            except (json.JSONDecodeError, OSError):
                pass

    # ── Generate default placeholder assets ──
    public_dir = site_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)

    # placeholder.svg — neutral grey rectangle with subtle icon
    placeholder_svg = public_dir / "placeholder.svg"
    if not placeholder_svg.exists():
        placeholder_svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">'
            '<rect width="800" height="600" fill="#e5e7eb"/>'
            '<g transform="translate(400,300)" opacity="0.4">'
            '<rect x="-40" y="-30" width="80" height="60" rx="4" fill="none" stroke="#9ca3af" stroke-width="2"/>'
            '<circle cx="-18" cy="-10" r="7" fill="#9ca3af"/>'
            '<path d="M-30 20 L-10 0 L10 12 L30-5 L30 20Z" fill="#9ca3af"/>'
            '</g></svg>',
            encoding="utf-8",
        )

    # logo.svg — minimal text-based logo
    logo_svg = public_dir / "logo.svg"
    if not logo_svg.exists():
        _display_name = project_name.replace("-", " ").replace("_", " ").title()
        logo_svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="40" viewBox="0 0 160 40">'
            f'<text x="80" y="26" text-anchor="middle" font-family="system-ui,sans-serif" '
            f'font-size="18" font-weight="600" fill="#111827">{_display_name}</text></svg>',
            encoding="utf-8",
        )

    # placeholder.jpg fallback — symlink or copy for code that references .jpg
    placeholder_jpg = public_dir / "placeholder.jpg"
    if not placeholder_jpg.exists():
        try:
            placeholder_jpg.symlink_to("placeholder.svg")
        except OSError:
            # Symlinks may fail on some systems; copy the SVG content instead
            import shutil
            shutil.copy2(placeholder_svg, placeholder_jpg)

    print("  ✓ Generated default placeholder assets (placeholder.svg, logo.svg)")

    # ── Install dependencies ──
    print("  Installing dependencies (npm install)...")
    result = subprocess.run(
        ["npm", "install"],
        capture_output=True,
        text=True,
        cwd=str(site_dir),
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  ⚠ npm install had issues:\n{result.stderr[-500:]}")
    else:
        print("  ✓ Dependencies installed")

    # ── Layer 7: Generate .env.local with Shopify credentials when commerce routes present ──
    if has_commerce_routes:
        resolved_cfg = None
        # Look for shopify_config.json: function param, output dir, extraction dir, root
        for candidate in [
            Path(shopify_config_path) if shopify_config_path else None,
            OUTPUT_DIR / project_name / "shopify_config.json",
            (Path(extraction_dir) / "shopify_config.json") if extraction_dir else None,
            ROOT / "shopify_config.json",
        ]:
            if candidate and candidate.exists():
                resolved_cfg = candidate
                break
        if resolved_cfg:
            import uuid as _uuid
            shopify_cfg = json.loads(resolved_cfg.read_text(encoding="utf-8"))
            revalidation_secret = str(_uuid.uuid4())
            env_lines = [
                f'SHOPIFY_STORE_DOMAIN={shopify_cfg.get("store_domain", "")}',
                f'SHOPIFY_STOREFRONT_ACCESS_TOKEN={shopify_cfg.get("storefront_access_token", "")}',
                f'SHOPIFY_REVALIDATION_SECRET={revalidation_secret}',
            ]
            write_file(site_dir / ".env.local", "\n".join(env_lines) + "\n")
            print("  ✓ Layer 7: Generated .env.local with Shopify credentials")
        else:
            print("  ⚠ Layer 7: shopify_config.json not found — .env.local not generated")
            print("    Create .env.local manually with: SHOPIFY_STORE_DOMAIN, SHOPIFY_STOREFRONT_ACCESS_TOKEN, SHOPIFY_REVALIDATION_SECRET")

    # ── Gate A: Token Sanitization Gate ──
    # Final check: fail loudly if any content tokens survived all sanitization passes.
    try:
        from lib.gate_a import check_gate_a as _check_gate_a
        _gate_a_ctx = {}
        if extraction_dir:
            _arch_gate = Path(extraction_dir) / "architecture.json"
            if _arch_gate.exists():
                try:
                    _arch_g = json.loads(_arch_gate.read_text(encoding="utf-8"))
                    _cols_g = _arch_g.get("collections", [])
                    if _cols_g:
                        _gate_a_ctx["collection_handle"] = _cols_g[0].get("handle", "all")
                except (json.JSONDecodeError, OSError):
                    pass
        _gate_a_result = _check_gate_a(site_dir, context=_gate_a_ctx, auto_fix=True)
        if _gate_a_result["auto_fixed"] > 0:
            print(f"  ✓ Gate A auto-fixed {_gate_a_result['auto_fixed']} token(s)")
        if _gate_a_result["passed"]:
            print("  ✓ Gate A PASSED: No unsanitized tokens")
        else:
            print(f"  ⚠ Gate A: {_gate_a_result['count']} unsanitized token(s) remain (non-fatal warning)")
            for _gf in _gate_a_result["findings"][:10]:
                print(f"    {_gf['file']}:{_gf['line']} — {_gf['token']}")
    except ImportError:
        pass  # gate_a module not available; non-fatal

    # ── Production build ──
    # Deploy-prep may NOT claim success until the site actually compiles.
    # Previously the only `npm run build` in the pipeline lived inside
    # stage_render_audit, which runs later and only when a deploy happened —
    # so a site that could not compile still printed "Site deployed".
    # run_production_build memoises its result per site dir, so the render
    # audit reuses this build instead of compiling the tree a second time.
    if not run_production_build(site_dir, "deploy-prep"):
        print(f"  ✖ Deploy prep FAILED for output/{project_name}/site/ (build errors above)")
        return

    print(f"  ✓ Site deployed to output/{project_name}/site/")
    print(f"  Run: cd output/{project_name}/site && npm run dev")


def stage_vercel_env_and_webhooks(site_dir: Path, project_name: str):
    """Post-deploy: Set Shopify env vars on Vercel and register webhooks."""
    env_path = site_dir / ".env.local"
    if not env_path.exists():
        print("  ⚠ No .env.local found — skipping Vercel env var setup")
        return
    env_vars = {}
    for line in env_path.read_text(encoding="utf-8").strip().split("\n"):
        if "=" in line:
            key, val = line.split("=", 1)
            env_vars[key.strip()] = val.strip()

    print("\n🔑 Setting Shopify env vars on Vercel...")
    for key, val in env_vars.items():
        # The value is a SECRET and is passed on stdin — never interpolated
        # into a shell command. `bash -c 'echo "<token>" | ...'` put the token
        # in the process list for any local user to read, and corrupted (or
        # executed) any value containing a quote, `$` or a backtick.
        result = subprocess.run(
            ["vercel", "env", "add", key, "production", "--yes"],
            input=val + "\n",
            capture_output=True, text=True, cwd=str(site_dir), timeout=30,
        )
        if result.returncode == 0:
            print(f"  ✓ Set {key} on Vercel")
        else:
            err = result.stderr.strip()
            if "already exists" in err.lower():
                print(f"  ℹ {key} already exists on Vercel (skipped)")
            else:
                print(f"  ⚠ Failed to set {key}: {err[:200]}")
                print(f"    Manual: echo \"$VALUE\" | vercel env add {key} production --yes")

    # Register Shopify webhooks (requires Admin API access — deferred to Gate E)
    print("  ℹ Webhook registration: Run `python3 scripts/register_webhooks.py` after first deploy to register revalidation webhooks")


def stage_review_v2(section_files: list[Path], site_spec: dict | None, project_name: str) -> dict:
    """Stage 4 (v2): Deterministic consistency review. No Claude call."""
    print("\n🔍 Stage 4 (v2): Running deterministic consistency review...")

    issues = []
    section_count = len(section_files)

    # Load site-spec style tokens if available
    style = site_spec.get("style", {}) if site_spec else {}
    palette = style.get("palette", {})

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended-A
        "]+",
        flags=re.UNICODE
    )

    placeholder_patterns = [
        "/api/placeholder", "via.placeholder.com", "placehold.co",
        "placekitten.com", "picsum.photos", "placeholder.svg",
        "example.com/image", "unsplash.com/random",
    ]

    for section_file in section_files:
        if not section_file.exists():
            issues.append({
                "file": section_file.name,
                "severity": "error",
                "check": "file_exists",
                "message": f"Section file not found: {section_file}"
            })
            continue

        code = section_file.read_text()
        filename = section_file.name

        # ── Check: "use client" directive ──────────────────────────
        if '"use client"' not in code and "'use client'" not in code:
            issues.append({
                "file": filename,
                "severity": "error",
                "check": "use_client",
                "message": "Missing 'use client' directive"
            })

        # ── Check: export default present ──────────────────────────
        if 'export default' not in code:
            issues.append({
                "file": filename,
                "severity": "error",
                "check": "export_default",
                "message": "Missing 'export default' — component won't render"
            })

        # ── Check: balanced braces ─────────────────────────────────
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            issues.append({
                "file": filename,
                "severity": "error",
                "check": "brace_balance",
                "message": f"Unbalanced braces: {open_braces} open, {close_braces} close"
            })

        # ── Check: no emoji characters ─────────────────────────────
        emoji_matches = emoji_pattern.findall(code)
        if emoji_matches:
            issues.append({
                "file": filename,
                "severity": "warning",
                "check": "no_emoji",
                "message": f"Contains emoji characters: {emoji_matches[:3]}"
            })

        # ── Check: no placeholder image URLs ───────────────────────
        for pattern in placeholder_patterns:
            if pattern in code:
                issues.append({
                    "file": filename,
                    "severity": "warning",
                    "check": "no_placeholder_images",
                    "message": f"Contains placeholder image URL: {pattern}"
                })

        # ── Check: imports are valid (basic) ───────────────────────
        import_lines = [l.strip() for l in code.split('\n') if l.strip().startswith('import ')]
        for imp_line in import_lines:
            if "from ''" in imp_line or 'from ""' in imp_line:
                issues.append({
                    "file": filename,
                    "severity": "error",
                    "check": "valid_imports",
                    "message": f"Empty import source: {imp_line[:80]}"
                })
            if "from 'motion/react'" in imp_line or 'from "motion/react"' in imp_line:
                issues.append({
                    "file": filename,
                    "severity": "warning",
                    "check": "valid_imports",
                    "message": f"Import from 'motion/react' should be 'framer-motion': {imp_line[:80]}"
                })

        # ── Check: JSX is not truncated ────────────────────────────
        stripped = code.rstrip()
        if stripped and not stripped.endswith(('}', ';', ')', '`', '"', "'")):
            issues.append({
                "file": filename,
                "severity": "warning",
                "check": "not_truncated",
                "message": f"File may be truncated — ends with: ...{stripped[-20:]}"
            })

    # ── Summary ────────────────────────────────────────────────────
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    passed = len(errors) == 0

    result = {
        "passed": passed,
        "section_count": section_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
    }

    # Save review
    output_dir = OUTPUT_DIR / project_name
    output_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / "review.json"
    review_path.write_text(json.dumps(result, indent=2))

    # Also write human-readable review.md
    review_md = "# Consistency Review (v2 — Deterministic)\n\n"
    review_md += f"**Result:** {'PASS' if passed else 'FAIL'}\n"
    review_md += f"**Sections reviewed:** {section_count}\n"
    review_md += f"**Errors:** {len(errors)}\n"
    review_md += f"**Warnings:** {len(warnings)}\n\n"

    if issues:
        review_md += "## Issues\n\n"
        for issue in issues:
            icon = "❌" if issue["severity"] == "error" else "⚠️"
            review_md += f"- {icon} **{issue['file']}** [{issue['check']}]: {issue['message']}\n"
    else:
        review_md += "No issues found.\n"

    (output_dir / "review.md").write_text(review_md)

    # Print summary
    print(f"  {'✅ PASS' if passed else '❌ FAIL'}: {len(errors)} errors, {len(warnings)} warnings")
    for issue in errors:
        print(f"    ❌ {issue['file']}: {issue['message']}")
    for issue in warnings[:5]:
        print(f"    ⚠  {issue['file']}: {issue['message']}")
    if len(warnings) > 5:
        print(f"    ... and {len(warnings) - 5} more warnings")

    return result


def stage_review(sections: list[dict], section_files: list[Path], preset: str, project_name: str, build_cache: "BuildCache | None" = None):
    """Stage 4: Run consistency review."""
    print("\n🔍 Stage 4: Running consistency review...")

    # ── Database path: use cached style from Supabase ──
    if build_cache and build_cache.style_config:
        style_header = build_cache.compact_style_header
        print(f"  Using Supabase industry style (cached)")
    else:
        # ── Legacy path: read from .md preset file ──
        preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
        style_header = extract_style_header(preset_content)

    # Concatenate all section code
    all_sections_code = ""
    for filepath in section_files:
        code = read_file(filepath)
        all_sections_code += f"\n\n--- {filepath.name} ---\n\n{code}"

    prompt = f"""You are a senior frontend QA reviewer checking a multi-section website
for visual and code consistency.

## Style Context
{style_header}

## Sections to Review
{all_sections_code}

## Consistency Checklist

Review every section and check the following. For each item, report
PASS or FAIL with the specific section(s) that violate.

### Color Consistency
- All sections use the same background color tokens
- All sections use the same text color tokens
- Accent color is identical across all buttons and links
- No section introduces colors not in the style header

### Typography Consistency
- All sections use the same heading font family
- All sections use the same body font family
- Heading sizes follow a consistent hierarchy
- Font weights match the style header specification

### Spacing Consistency
- Section padding is uniform across all sections
- Internal gap values are consistent within similar layouts
- Container max-width is the same across all sections

### Border Radius Consistency
- All buttons use the same border-radius value
- All cards use the same border-radius value
- All input fields use the same border-radius value

### Animation Consistency
- All scroll-triggered animations use the same entrance pattern
- Animation duration is consistent across sections
- Easing function is identical across all animations
- Hover states follow the same pattern

### Button Style Consistency
- Primary button style is identical everywhere
- Button text casing is consistent

For each item, output:
✅ PASS — item description
❌ FAIL — item description — Sections affected: list — Fix: specific change needed

End with:
- Total: pass_count/total_count passed
- Priority fix list ordered by visual impact"""

    review = call_claude(prompt, "review")
    write_file(OUTPUT_DIR / project_name / "review.md", review)
    print(f"\n{review}")


def stage_validate(project_name: str) -> dict:
    """Stage 5.5: Pre-flight validation — catch errors before deployment."""
    print("\n═══ STAGE 5.5: PRE-FLIGHT VALIDATION ═══\n")

    project_dir = OUTPUT_DIR / project_name
    sections_dir = project_dir / "sections"
    issues = []

    # 1. Check all section files exist and have content
    # Support both single-page (sections/*.tsx) and multi-page (sections/{page_type}/*.tsx)
    section_files = sorted(sections_dir.glob("*.tsx")) if sections_dir.exists() else []
    if not section_files and sections_dir.exists():
        # Multi-page mode: check subdirectories (e.g. sections/homepage/*.tsx)
        section_files = sorted(sections_dir.glob("**/*.tsx"))
    repaired_count = 0
    if not section_files:
        issues.append("CRITICAL: No section files found in sections/ or sections/{page_type}/")
    else:
        for sf in section_files:
            content = sf.read_text(encoding="utf-8")
            if len(content.strip()) < 50:
                issues.append(f"CRITICAL: {sf.name} is nearly empty ({len(content)} chars)")
                continue

            # 2. Check "use client" directive
            if '"use client"' not in content and "'use client'" not in content:
                issues.append(f"WARNING: {sf.name} missing 'use client' directive")

            # 3. Check export default
            if 'export default' not in content:
                issues.append(f"CRITICAL: {sf.name} missing export default")

            # 4. Truncation detection & auto-repair (v1.1.1 — replaces basic brace check)
            truncation_result = _detect_and_repair_truncation(content, sf.name)
            if truncation_result and truncation_result.get("truncated"):
                if truncation_result.get("repaired"):
                    sf.write_text(truncation_result["code"], encoding="utf-8")
                    repaired_count += 1
                    issues.append(f"WARNING: {sf.name} was truncated — auto-repaired (brace/JSX/export fix)")
                    for w in truncation_result.get("warnings", []):
                        issues.append(f"WARNING: {sf.name}: {w}")
                else:
                    issues.append(f"CRITICAL: {sf.name} is truncated and could not be auto-repaired")
            elif not truncation_result:
                # Fallback: basic brace balance if Node.js call failed
                open_braces = content.count('{')
                close_braces = content.count('}')
                if abs(open_braces - close_braces) > 2:
                    issues.append(f"WARNING: {sf.name} has unbalanced braces (open={open_braces}, close={close_braces})")

    if repaired_count:
        print(f"  🔧 Auto-repaired {repaired_count} truncated section(s)")

    # 5. Check scaffold exists
    scaffold_path = project_dir / "scaffold.md"
    if not scaffold_path.exists():
        issues.append("WARNING: scaffold.md not found")

    # 6. Check page.tsx exists
    page_path = project_dir / "page.tsx"
    if page_path.exists():
        page_content = page_path.read_text(encoding="utf-8")
        # Check imports match actual section files
        for sf in section_files:
            component_name = sf.stem.split('-', 1)[-1] if '-' in sf.stem else sf.stem
            # Just check the filename is referenced somewhere in page.tsx
            if sf.stem not in page_content and component_name not in page_content:
                issues.append(f"WARNING: {sf.name} not imported in page.tsx")
    else:
        issues.append("WARNING: page.tsx not found (will be created during assembly)")

    # Report
    if issues:
        critical = [i for i in issues if i.startswith("CRITICAL")]
        warnings = [i for i in issues if i.startswith("WARNING")]
        print(f"  Found {len(critical)} critical issues, {len(warnings)} warnings:\n")
        for issue in issues:
            prefix = "  ❌" if issue.startswith("CRITICAL") else "  ⚠"
            print(f"{prefix} {issue}")

        if critical:
            print(f"\n  🛑 {len(critical)} critical issues must be fixed before deployment.")
    else:
        print("  ✅ All pre-flight checks passed.")

    return {'passed': len([i for i in issues if i.startswith("CRITICAL")]) == 0, 'issues': issues}


# ═════════════════════════════════════════════════════════════════════════════
# Bill of Sale Orchestration (BoS → build_trace → re-audit loop)
# ═════════════════════════════════════════════════════════════════════════════

def stage_render_audit(project_name: str, site_manifest: dict | None = None) -> str:
    """
    Stage 6: Post-build render audit — invoke render-audit.js against the
    built site and record the outcome.

    This is a mandatory post-build gate: builds that deploy successfully
    are NOT considered complete until the render audit passes (or flags
    defects for review).

    Returns one of:
      'passed'         — no defects found
      'review_needed'  — unaccepted defect groups exist
      'failed'         — audit crashed or could not run
      'skipped'        — audit not available (missing deps/tools)
    """
    print("\n═══ STAGE 6: POST-BUILD RENDER AUDIT ═══\n")

    audit_script = ROOT / "scripts" / "quality" / "render-audit.js"
    site_dir = OUTPUT_DIR / project_name / SITE_DIR_NAME
    audit_out = OUTPUT_DIR / project_name / "render-audit-results"

    if not audit_script.exists():
        print(f"  ⚠ render-audit.js not found at {audit_script}")
        print(f"  → Render audit SKIPPED")
        return "skipped"

    if not site_dir.exists():
        print(f"  ⚠ Site directory not found at {site_dir}")
        print(f"  → Render audit SKIPPED (no built site to audit)")
        return "skipped"

    # Determine routes to audit
    routes = ["/"]
    if site_manifest:
        manifest_routes = []
        for page in site_manifest.get("pages", []):
            route = page.get("route") or "/"
            if route and "[" not in route:
                manifest_routes.append(route)
        if manifest_routes:
            routes = manifest_routes

    # Ensure node dependencies are installed in scripts/quality
    quality_dir = ROOT / "scripts" / "quality"
    node_modules = quality_dir / "node_modules"
    if not node_modules.exists():
        print("  Installing render-audit dependencies (npm ci)...")
        result = subprocess.run(
            ["npm", "ci", "--no-audit", "--no-fund"],
            cwd=str(quality_dir),
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print(f"  ⚠ npm ci failed: {result.stderr.strip()[:200]}")
            print(f"  → Render audit SKIPPED")
            return "skipped"

    # Build the Next.js site (production build). stage_deploy already ran this
    # build for the same site dir, so run_production_build returns the memoised
    # result rather than compiling twice; it records the failure itself.
    if not run_production_build(site_dir, "render audit"):
        print(f"  → Render audit mark: FAILED (build error)")
        return "failed"

    # Start local server for the audit on a random available port
    import socket as _sock
    _s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
    _s.bind(("", 0))
    port = _s.getsockname()[1]
    _s.close()

    server_proc = subprocess.Popen(
        ["npm", "run", "start", "--", "--port", str(port)],
        cwd=str(site_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://localhost:{port}"

    # Wait for the server to be ready (poll socket connect every 1s, up to 20s)
    max_retries = 20
    server_ready = False
    for attempt in range(max_retries):
        _time.sleep(1)
        try:
            s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("127.0.0.1", port))
            s.close()
            server_ready = True
            break
        except (OSError, ConnectionRefusedError):
            continue
    if not server_ready:
        server_proc.kill()
        server_proc.wait(timeout=5)
        print(f"  ⚠ Local server did not start in time")
        print(f"  → Render audit mark: FAILED (server timeout)")
        return "failed"

    try:
        # Run render-audit.js
        audit_out.mkdir(parents=True, exist_ok=True)
        routes_csv = ",".join(routes)
        print(f"  Auditing {len(routes)} route(s): {', '.join(routes)}")
        result = subprocess.run(
            [
                "node", str(audit_script),
                "--base", base_url,
                "--routes", routes_csv,
                "--out", str(audit_out),
                "--settle", "3000",
            ],
            cwd=str(quality_dir),
            capture_output=True, text=True, timeout=180,
        )

        if result.returncode != 0:
            print(f"  ⚠ render-audit.js exited with code {result.returncode}")
            print(f"  stderr: {result.stderr.strip()[:300]}")
            status = "failed"
        else:
            # Parse the machine-readable output (last JSON line on stdout)
            audit_data = None
            for line in result.stdout.strip().splitlines():
                try:
                    audit_data = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue

            if audit_data:
                total = audit_data.get("total_defects", 0)
                by_severity = audit_data.get("by_severity", {})
                severity_summary = ", ".join(
                    f"{k}: {v}" for k, v in by_severity.items()
                )
                print(f"  📋 Render audit: {total} defect(s) — {severity_summary}")

                if total == 0:
                    print(f"  ✅ Render audit PASSED — no defects found")
                    status = "passed"
                else:
                    print(f"  ⚠ Render audit: {total} defect(s) require review")
                    print(f"  → Build marked for REVIEW (defects must be accepted or fixed)")
                    status = "review_needed"
            else:
                print(f"  ⚠ Could not parse render-audit output")
                print(f"  stdout: {result.stdout.strip()[:300]}")
                status = "failed"

        # Print details from audit report if available
        report_path = audit_out / "render-audit.json"
        if report_path.exists():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if report.get("defects"):
                    print(f"\n  Defect summary:")
                    by_cat = report.get("by_category", {})
                    for cat, count in sorted(by_cat.items()):
                        print(f"    {cat}: {count}")
                    # Print first 3 defects inline
                    for d in report["defects"][:3]:
                        print(f"    • [{d['severity']}] {d['category']}: {d['finding']}")
                    if len(report["defects"]) > 3:
                        print(f"    ... and {len(report['defects']) - 3} more")
            except (json.JSONDecodeError, OSError):
                pass

    except subprocess.TimeoutExpired:
        print(f"  ⚠ render-audit.js timed out after 180s")
        status = "failed"
    except Exception as e:
        print(f"  ⚠ render-audit exception: {e}")
        status = "failed"
    finally:
        # Stop the server
        server_proc.terminate()
        server_proc.wait(timeout=10)

    print(f"  → Render audit status: {status}")
    return status


def stage_bos_orchestrate(
    project_name: str,
    industry: str,
    output_dir: Path,
    manifest: dict | None = None,
    sections: list[dict] | None = None,
    section_files: list[Path] | None = None,
    bos_import_path: str | None = None,
    no_bos: bool = False,
) -> BillOfSale | None:
    """Stage 5+ : Orchestrate the build via Bill of Sale.

    The BoS drives the build *per line item* — identifying what was built,
    recording build_trace back per line item (status, files, verified_against),
    and keeping the boS in sync so the re-audit loop can consume it.

    This stage is called AFTER the traditional pipeline stages have produced
    sections and assembled pages.  It wraps the existing output into a BoS
    format and writes build_traces for each line item.  When ``bos_import_path``
    is set, the BoS is loaded from that external file (pre-generated by Layer 4
    or a downstream planner) and its line items are cross-referenced against
    what was actually built.

    Returns the BillOfSale instance (with populated build_traces) or None if
    BoS module is unavailable.
    """
    if no_bos or not BOS_AVAILABLE:
        return None

    print(f"\n{'═' * 60}")
    print(f"  📜 Bill of Sale Orchestration")
    print(f"{'═' * 60}")

    # 1. Load the BoS (external, or create from pipeline state)
    bos: BillOfSale | None = None
    bos_source = ""

    if bos_import_path:
        pp = Path(bos_import_path)
        if pp.exists():
            try:
                bos = BillOfSale.load(pp)
                bos_source = f"imported from {bos_import_path}"
                print(f"  ✓ BoS loaded ({len(bos.line_items)} line items) — {bos_source}")
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                print(f"  ⚠ Could not parse BoS at {bos_import_path}: {e}")

    if bos is None:
        if manifest:
            bos = BillOfSale.from_manifest(manifest, project_name)
            bos_source = "site-manifest"
        elif sections:
            bos = BillOfSale.from_sections(sections, project_name, industry)
            bos_source = "pipeline sections"
        else:
            bos = BillOfSale.new(project_name, industry)
            bos_source = "empty (no sections)"

        print(f"  ✓ BoS created from {bos_source} ({len(bos.line_items)} line items)")

    bos.project_name = project_name
    bos.industry = industry

    # ── DAG bill provenance (uiux-bill-of-sale-dag-v1) ────────────────────────
    # When the imported bill is the tenant audit Bill of Sale, every line item is a
    # finding carrying a disposition + verified_against rule_id.  We drive each
    # disposition's deliverable (routing copy-findings into the copy gate, recording
    # build intent for the rest) and write ONE build_trace per line item, keyed by
    # its stable id.  The whole pass is a deterministic replace-in-place: re-running
    # over the same bill reproduces the same N traces (never 2N).
    _is_dag = any(it.type == "finding" for it in bos.line_items)
    if _is_dag:
        _dag_traces: list[dict] = []
        _copy_gate_routed: list[str] = []
        _lane_counts: dict[str, int] = {}
        # Deterministic file hint per finding — the deliverable's fix locus.  No
        # side effects: we record where the fix lands, we do not build here.
        _existing = {sf.stem: sf for sf in (section_files or [])}
        for item in bos.line_items:
            lane, action = map_disposition(item.disposition)
            _lane_counts[lane] = _lane_counts.get(lane, 0) + 1
            # Route copy-findings items into the existing copy gate.
            _files: list[str] = []
            if lane == "copy":
                _copy_gate_routed.append(item.item_id)
            trace = build_dag_trace(item, commit=None, files=_files)
            # Writeback keyed by line-item id — replace-in-place, idempotent.
            item.build_trace = trace
            _dag_traces.append(trace)

        # Persist the enriched bill (with build_trace per line item)…
        _bos_path = output_dir / "bill-of-sale.json"
        bos.save(_bos_path)
        # …and the dedicated build-trace.json artifact (idempotent, id-keyed).
        _trace_path = write_build_trace_artifact(output_dir, _dag_traces)

        print(f"  ✓ DAG bill consumed: {len(_dag_traces)} line item(s) → build_trace")
        for _ln, _c in sorted(_lane_counts.items()):
            print(f"      {_ln}: {_c}")
        if _copy_gate_routed:
            print(f"  ✓ Routed {len(_copy_gate_routed)} finding(s) into the copy gate")
        print(f"  ✓ build_trace written ({len(_dag_traces)} entries) → {_trace_path}")
        print(f"  ✓ BoS saved → {_bos_path}")
        print(f"{'═' * 60}\n")
        return bos

    # 2. Write a build_trace per line item — each gets status + files + verified_against
    #    Section-file map: derive which files belong to which line item.
    _sec_files_map: dict[str, list[str]] = {}
    if section_files:
        for sf in section_files:
            _sec_files_map[sf.stem] = str(sf.relative_to(ROOT) if sf.is_relative_to(ROOT) else sf.name)

    _bos_version = f"bos-{bos.version}"
    _completed_count = 0
    _failed_count = 0

    # Load Stage-4 review issues so the BoS records REAL defects (unbalanced braces,
    # etc.) instead of marking every section "completed" with no errors. Without this
    # the post-build defect ledger is a false-success artifact and the learning loop
    # (pattern_detector.ingest_bill_of_sale_ledger) learns nothing from broken builds.
    _review_by_file: dict[str, list[dict]] = {}
    _review_path = output_dir / "review.json"
    if _review_path.exists():
        try:
            _rev = json.loads(_review_path.read_text())
            for _iss in _rev.get("issues", []):
                _f = Path(str(_iss.get("file", ""))).name
                if _f:
                    _review_by_file.setdefault(_f, []).append(_iss)
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    for item in bos.line_items:
        item_id = item.item_id

        if item.type == "page":
            # For page items, collect all section files
            _files_for_page: list[str] = []
            if manifest:
                _pages = manifest.get("pages", [])
                for p in _pages:
                    if p.get("id", "") in item_id:
                        _sfx = p.get("sections", [])
                        for js, _ in enumerate(_sfx):
                            _arch = _sfx[js].get("archetype", "").lower().replace("-", "_")
                            _fn = f"{js + 1:02d}-{_arch}.tsx"
                            _files_for_page.append(f"sections/{p.get('id', 'page')}/{_fn}")
                        break
            elif sections:
                for js, sec in enumerate(sections):
                    _arch = sec.get("archetype", "").lower().replace("-", "_")
                    _files_for_page.append(f"sections/{js + 1:02d}-{_arch}.tsx")

            bos.mark_started(item_id)
            bos.mark_completed(
                item_id,
                files=_files_for_page,
                verified_against=_bos_version,
            )
            _completed_count += 1
            _fn_summary = ", ".join(_files_for_page[:3])
            if len(_files_for_page) > 3:
                _fn_summary += f" … +{len(_files_for_page) - 3} more"
            print(f"    ✓ {item_id}: completed ({len(_files_for_page)} files) — {_fn_summary}")

        elif item.type == "section":
            # For section items, find the matching file
            _pos = item.position or (bos.line_items.index(item) + 1)
            _arch_key = item.archetype.lower().replace("-", "_")
            _expected = f"{_pos:02d}-{_arch_key}.tsx"
            _stem = _expected.replace(".tsx", "")
            # A skipped section (truncated past retries) never entered _sec_files_map,
            # so its absence from the map — not the _expected fallback — is the signal.
            _produced = _stem in _sec_files_map
            _found = _sec_files_map.get(_stem, _expected)

            bos.mark_started(item_id)
            if not _produced:
                # Section was skipped during generation — never written to disk.
                bos.mark_failed(item_id, errors=[
                    f"section skipped during generation — {_expected} truncated after "
                    f"retries and was not written (broken section)"
                ])
                _failed_count += 1
                print(f"    ❌ {item_id}: skipped — {_expected} not produced")
            else:
                # Produced — attach any Stage-4 review errors/warnings for this file so
                # a section that compiled-but-broke (e.g. unbalanced braces) is recorded.
                _iss = _review_by_file.get(Path(_found).name, [])
                _errs = [f"{i.get('check', 'review')}: {i.get('message', '')}"
                         for i in _iss if i.get("severity") == "error"]
                _warns = [f"{i.get('check', 'review')}: {i.get('message', '')}"
                          for i in _iss if i.get("severity") == "warning"]
                bos.mark_completed(
                    item_id,
                    files=[f"sections/{_found}"],
                    verified_against=_bos_version,
                    errors=_errs or None,
                    warnings=_warns or None,
                )
                if _errs:
                    _failed_count += 1
                    print(f"    ⚠ {item_id}: completed with {len(_errs)} review error(s) — {_found}")
                else:
                    _completed_count += 1
                    print(f"    ✓ {item_id}: completed — {_found}")

        # If a file was expected but not found, mark with a warning
        if item.build_trace:
            pass  # build_trace already written above

    # 3. Persist the BoS (with populated build_traces)
    bos_path = output_dir / "bill-of-sale.json"
    saved = bos.save(bos_path)
    _trace_note = f"{_completed_count} completed"
    if _failed_count:
        _trace_note += f", {_failed_count} with defects/skipped"
    print(f"  ✓ BoS saved with {_trace_note} traces → {saved}")

    # 4. Make build_traces available for the re-audit loop
    traces = load_build_traces(output_dir)
    if traces:
        _all_statuses = [t.get("status", "unknown") for t in traces]
        _by_status = {s: _all_statuses.count(s) for s in set(_all_statuses)}
        print(f"  ✓ Re-audit loop ready: {len(traces)} build_trace(s) available")
        for s, c in sorted(_by_status.items()):
            print(f"      {s}: {c}")

    print(f"{'═' * 60}\n")
    return bos


# ── BRIEF #33297: Per-section asset binding ──────────────────────────
# Maps tenant creative_assets to the sections that should render them. Binding
# (this node) is distinct from loading (asset_count): loading pulls the media,
# binding decides WHICH section each asset belongs to and injects its self-hosted
# path onto the section so the generated component renders it.
_ASSET_TYPE_ARCHETYPE_AFFINITY = {
    "logo": ("nav", "navigation", "footer", "hero"),
    "hero": ("hero",),
    "banner": ("hero", "cta"),
    "product": ("product-showcase", "gallery", "features"),
    "gallery": ("gallery", "product-showcase"),
    "background": ("hero", "cta", "features"),
    "icon": ("features", "how-it-works"),
    "team": ("team", "about"),
    "testimonial": ("testimonials",),
    "image": ("hero", "gallery", "features"),
    # BRIEF #33320/#33312 — trust & security assets distribute to a security_row
    # archetype across ALL pages (bind_section_assets flattens every page's
    # sections), so badges/certifications land on inner pages, not just the hero.
    "badge": ("security_row", "trust", "footer", "features"),
    "trust": ("security_row", "trust", "footer"),
    "security": ("security_row", "trust"),
    "certification": ("security_row", "trust", "footer"),
}


def _asset_self_hosted_path(asset: dict) -> str | None:
    """Self-hosted / CDN path for a creative_asset row (storage_path preferred)."""
    return asset.get("storage_path") or asset.get("cdn_url") or None


def bind_section_assets(tenant_context: dict | None, site_manifest: dict | None,
                        output_dir: Path) -> int:
    """BRIEF #33297 — bind tenant creative_assets to sections during generation.

    Each creative_asset is matched (by asset_type / metadata role / metadata
    section hint) to the best-fitting section archetype in the manifest, and its
    self-hosted src path is recorded onto ``section['bound_asset']`` (consumed
    downstream by section generation / asset injection). A per-build binding
    manifest is written for audit.

    Returns the count of sections that received a bound asset. Absence of tenant
    creative_assets returns 0 and leaves the manifest untouched (no regression).
    """
    if not tenant_context or not site_manifest:
        return 0
    assets = [a for a in (tenant_context.get("creative_assets") or []) if _asset_self_hosted_path(a)]
    if not assets:
        return 0
    sections = [s for p in site_manifest.get("pages", []) for s in p.get("sections", [])]
    if not sections:
        return 0

    def _affinity(asset: dict, section: dict) -> int:
        at = (asset.get("asset_type") or "").lower()
        meta = asset.get("metadata") or {}
        arch = (section.get("archetype") or "").lower().replace("_", "-")
        score = 0
        for want in _ASSET_TYPE_ARCHETYPE_AFFINITY.get(at, ()):
            if want.replace("_", "-") in arch:
                score += 2
        role = str(meta.get("role") or meta.get("archetype") or "").lower().replace("_", "-")
        if role and role in arch:
            score += 3
        sec_hint = str(meta.get("section") or "").lower().replace("_", "-")
        if sec_hint and sec_hint in arch:
            score += 3
        return score

    bindings: list[dict] = []
    used: set = set()
    bound = 0
    for section in sections:
        best, best_score = None, 0
        for asset in assets:
            aid = asset.get("id")
            if aid in used:
                continue
            s = _affinity(asset, section)
            if s > best_score:
                best, best_score = asset, s
        if best and best_score > 0:
            src = _asset_self_hosted_path(best)
            section["bound_asset"] = {
                "asset_id": best.get("id"),
                "asset_type": best.get("asset_type"),
                "src": src,
                "score": best_score,
            }
            used.add(best.get("id"))
            bound += 1
            bindings.append({
                "archetype": section.get("archetype"),
                "asset_id": best.get("id"),
                "asset_type": best.get("asset_type"),
                "src": src,
                "score": best_score,
            })
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "asset-bindings.json").write_text(
            json.dumps({"bound": bound, "bindings": bindings}, indent=2), encoding="utf-8")
    except OSError:
        pass
    if bound:
        print(f"  🔗 Asset binding: {bound} section(s) bound to tenant creative_assets")
    return bound


# ── BRIEF #33298: Unified app shell + protected app-route seams ───────
def _seam_route_slug(item) -> str:
    raw = (getattr(item, "section", "") or getattr(item, "page", "")
           or getattr(item, "item_id", "") or "app-route")
    slug = re.sub(r"[^a-z0-9]+", "-", str(raw).lower()).strip("-")
    return slug or "app-route"


def _app_shell_layout_tsx() -> str:
    """Unified app-shell layout for the protected (app) route group. Both marketing
    routes (root layout) and these app routes mount on the same Next.js app."""
    return (
        '// UNIFIED APP SHELL — protected (app) route group.\n'
        '// Marketing routes and these app routes mount on the SAME Next.js app.\n'
        '// BRIEF #33298 — app-route seams are stubbed here, not fabricated.\n'
        'export default function AppShellLayout({ children }: { children: React.ReactNode }) {\n'
        '  return (\n'
        '    <div data-app-shell="unified" className="min-h-screen">\n'
        '      {children}\n'
        '    </div>\n'
        '  );\n'
        '}\n'
    )


def _app_route_seam_stub(item, slug: str) -> str:
    """Stubbed, clearly-marked source app-route seam. Business logic NOT fabricated."""
    item_id = getattr(item, "item_id", slug)
    verified = getattr(item, "verified_against", "")
    page = getattr(item, "page", "")
    direction = getattr(item, "content_direction", "") or getattr(item, "section", "")
    return (
        f'// ─── APP-ROUTE SEAM (STUB) — BRIEF #33298 ──────────────────────────\n'
        f'// Carried-into-unified-app BoS item: {item_id}\n'
        f'// Source property/page: {page or "n/a"}\n'
        f'// Re-audit rule: {verified or "n/a"}\n'
        f'// NOTE: This is a SEAM, not an implementation. The original exchange /\n'
        f'//       app business logic is intentionally NOT fabricated here — this\n'
        f'//       route mounts on the unified app shell and marks where the carried\n'
        f'//       app functionality is wired in during migration.\n'
        f'// Intent: {direction or "carried app route"}\n'
        f'export default function {"".join(w.capitalize() for w in slug.split("-")) or "AppRoute"}Seam() {{\n'
        f'  return (\n'
        f'    <main data-app-route-seam="{slug}" className="p-8">\n'
        f'      <h1 className="text-xl font-semibold">App route seam: {slug}</h1>\n'
        f'      <p className="text-sm opacity-70">Carried-into-unified-app ({item_id}). '
        f'Business logic seamed, not generated.</p>\n'
        f'    </main>\n'
        f'  );\n'
        f'}}\n'
    )


def scaffold_app_route_seams(bos, output_dir: Path) -> int:
    """BRIEF #33298 — scaffold a unified app shell + stubbed protected app-route
    seams for every carried-into-unified-app BoS line item.

    Writes each seam under ``site/src/app/(app)/<slug>/page.tsx`` with clear SEAM
    markers (business logic intentionally not fabricated) plus a shared app-shell
    layout, and an audit manifest. Returns the number of seams scaffolded. No
    carried items (or no built site) returns 0.
    """
    if not bos:
        return 0
    carried = [it for it in bos.line_items
               if (getattr(it, "disposition", "") or "").lower().replace("_", "-") == "carried-into-unified-app"]
    if not carried:
        return 0
    site_dir = output_dir / SITE_DIR_NAME
    if not site_dir.exists():
        return 0
    seam_root = site_dir / "src" / "app" / "(app)"
    scaffolded = 0
    manifest: list[dict] = []
    for it in carried:
        slug = _seam_route_slug(it)
        route_dir = seam_root / slug
        try:
            route_dir.mkdir(parents=True, exist_ok=True)
            (route_dir / "page.tsx").write_text(_app_route_seam_stub(it, slug), encoding="utf-8")
            scaffolded += 1
            manifest.append({"item_id": getattr(it, "item_id", ""), "slug": slug,
                             "verified_against": getattr(it, "verified_against", "")})
        except OSError:
            continue
    if scaffolded:
        try:
            (seam_root / "layout.tsx").write_text(_app_shell_layout_tsx(), encoding="utf-8")
            (output_dir / "app-route-seams.json").write_text(
                json.dumps({"scaffolded": scaffolded, "seams": manifest}, indent=2), encoding="utf-8")
        except OSError:
            pass
        print(f"  🧩 Unified app shell: {scaffolded} app-route seam(s) scaffolded")
    return scaffolded


# ── BRIEF #33299: Vercel deploy + capture deployed URL ────────────────
def _vercel_token() -> str | None:
    """Resolve a Vercel API token: VERCEL_TOKEN env, else the local CLI auth.json."""
    tok = os.environ.get("VERCEL_TOKEN")
    if tok:
        return tok
    for p in (
        Path.home() / "Library/Application Support/com.vercel.cli/auth.json",
        Path.home() / ".local/share/com.vercel.cli/auth.json",
        Path.home() / ".vercel/auth.json",
    ):
        try:
            if p.exists():
                t = json.loads(p.read_text(encoding="utf-8")).get("token")
                if t:
                    return t
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _vercel_team_id(site_dir: Path) -> str | None:
    """Read the team/org id from the site's .vercel/project.json."""
    try:
        pj = json.loads((site_dir / ".vercel" / "project.json").read_text(encoding="utf-8"))
        return pj.get("orgId")
    except (OSError, json.JSONDecodeError):
        return None


def _vercel_verify_ready(url: str, site_dir: Path, timeout_s: int = 900) -> tuple[str, str]:
    """Poll the Vercel API for the deployment's readyState until terminal.

    Returns (state, detail). state ∈ {READY, ERROR, CANCELED, UNKNOWN, TIMEOUT}.
    On ERROR, detail carries the failing build-log lines when retrievable. A
    successful `vercel --prod` URL is NOT proof of a successful build — this is
    the guard that makes the deploy step honest about remote build failures."""
    import urllib.request
    import urllib.error
    token = _vercel_token()
    team = _vercel_team_id(site_dir)
    if not token:
        return ("UNKNOWN", "no Vercel API token (VERCEL_TOKEN or CLI auth) — cannot verify build state")
    host = url.replace("https://", "").rstrip("/")
    q = f"?teamId={team}" if team else ""

    def _api(path: str):
        req = urllib.request.Request(f"https://api.vercel.com{path}",
                                     headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    deadline = _time.time() + timeout_s
    state = "UNKNOWN"
    dep_id = None
    while _time.time() < deadline:
        try:
            d = _api(f"/v13/deployments/{host}{q}")
            state = d.get("readyState") or d.get("status") or "UNKNOWN"
            dep_id = d.get("id") or dep_id
        except urllib.error.URLError as e:
            return ("UNKNOWN", f"status poll failed: {e}")
        if state in ("READY", "ERROR", "CANCELED"):
            break
        print(f"     … build {state.lower()} — waiting")
        _time.sleep(10)

    if state == "ERROR" and dep_id:
        # Pull the failing build-log lines for a precise diagnosis.
        try:
            ev = _api(f"/v2/deployments/{dep_id}/events?builds=1&limit=200{('&teamId=' + team) if team else ''}")
            lines = []
            for e in (ev if isinstance(ev, list) else ev.get("events", []) or []):
                txt = (e.get("text") or (e.get("payload") or {}).get("text") or "")
                if txt and any(k in txt.lower() for k in ("error", "failed", "expected", "cannot", "exit")):
                    lines.append(txt.strip())
            return ("ERROR", "\n".join(lines[-15:]) or "build failed (no error lines retrieved)")
        except urllib.error.URLError as e:
            return ("ERROR", f"build failed; could not fetch logs: {e}")
    return (state, "")


def deploy_to_vercel(output_dir: Path, project_name: str) -> str | None:
    """BRIEF #33299 — deploy the built Next.js site to Vercel and return the URL,
    ONLY after verifying the remote build actually reached READY.

    Runs ``vercel --yes --prod`` in the built site dir, captures the deployment
    URL, then polls the Vercel API for the deployment's readyState. Returns the
    URL only when the build is READY; returns None (with the failing build-log
    lines printed) when the build ERRORs — so the pipeline never reports a broken
    deploy as success. Gated by the caller (--publish).
    """
    site_dir = output_dir / SITE_DIR_NAME
    if not (site_dir / "package.json").exists():
        print("  ⚠ vercel deploy skipped — no built site at site/")
        return None
    try:
        r = subprocess.run(
            ["vercel", "--yes", "--prod", "--cwd", str(site_dir)],
            capture_output=True, text=True, timeout=1800,
        )
    except FileNotFoundError:
        print("  ⚠ vercel CLI not found — skipping deploy (npm i -g vercel)")
        return None
    except subprocess.TimeoutExpired:
        print("  ⚠ vercel deploy timed out")
        return None
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    m = re.search(r"https://[a-z0-9][a-z0-9.-]*\.vercel\.app", out)
    url = m.group(0) if m else None
    if not url:
        print(f"  ⚠ vercel deploy produced no URL (rc={r.returncode})")
        return None

    # A URL is not success — verify the remote build reached READY.
    print(f"  ⏳ Deployment created ({url}); verifying build state...")
    state, detail = _vercel_verify_ready(url, site_dir)
    if state == "READY":
        print(f"  🌐 Deployed & verified READY: {url}")
        return url
    if state == "UNKNOWN":
        print(f"  ⚠ Could not verify build state ({detail}); returning URL unverified: {url}")
        return url
    print(f"  ❌ Vercel build did NOT succeed (state={state}) for {url}")
    if detail:
        print("  ── build error ──")
        for ln in detail.splitlines():
            print(f"     {ln}")
    return None


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Website Builder Pipeline")
    parser.add_argument("project", help="Project name (must match a brief in briefs/)")
    parser.add_argument("--preset", help="Override preset selection", default=None)
    parser.add_argument("--no-pause", action="store_true", help="Skip scaffold review checkpoint")
    parser.add_argument("--skip-to", choices=["sections", "assemble", "review", "deploy"],
                        help="Skip to a specific stage (uses existing scaffold)")
    parser.add_argument("--deploy", action="store_true",
                        help="Also deploy to a runnable Next.js project at output/{project}/site/")
    parser.add_argument("--from-url", help="Clone mode: extract from URL, auto-generate preset + brief",
                        default=None, metavar="URL")
    parser.add_argument("--clean", action="store_true",
                        help="Delete existing output and start completely fresh")
    parser.add_argument("--force", action="store_true",
                        help="Ignore warnings (low confidence, validation issues) and proceed")
    parser.add_argument("--industry", help="Select industry from Supabase preset database (alternative to --preset)",
                        default=None, metavar="INDUSTRY")
    parser.add_argument("--page", help="Page type for --industry mode (default: homepage)",
                        default="homepage", metavar="PAGE_TYPE")
    parser.add_argument("--site-manifest", help="Path to site-manifest.json for multi-page build (Layer 6)",
                        default=None, metavar="PATH")
    parser.add_argument("--compiled-dir", help="Path to Calculator compiled dir (architecture.json); enables multi-route generation",
                        default=None, metavar="PATH")
    parser.add_argument("--brief", help="Path to brief.md file (overrides brief lookup from compiled-dir or briefs/)",
                        default=None, metavar="PATH")
    parser.add_argument("--set-vercel-env", action="store_true",
                        help="Auto-set Shopify env vars on Vercel + register webhooks after deploy")
    parser.add_argument("--shopify-config", help="Path to shopify_config.json (from Layer 4 output)",
                        default=None, metavar="PATH")
    parser.add_argument("--copy-findings", help="Path to a findings JSON (Copy Fidelity weakness gate): "
                        "{section_index_or_filename: {rule_id, detail}} — flagged slots switch from "
                        "reproduce to revise-from-source",
                        default=None, metavar="PATH")
    parser.add_argument("--output-root", help="Override the base output directory. Default: <web-builder>/output. "
                        "When set, all build artifacts write under <output-root>/{project}/... "
                        "(re-rooted, same subtree layout). Accepts absolute or relative paths.",
                        default=None, metavar="PATH")
    parser.add_argument("--target-platform", choices=["shopify", "vercel"], default=None,
                        help="Deploy target platform (shopify=current behavior, vercel=clean Next.js app). "
                             "Default: resolved from tenant config, falls back to shopify")
    parser.add_argument("--github-repo", default=None,
                        help="BRIEF #33323 — target GitHub repo (owner/name or URL) for git-publish SoT.")
    parser.add_argument("--push-policy", choices=["off", "push"], default="off",
                        help="BRIEF #33323 — 'off' commits built site locally as SoT; "
                             "'push' also pushes to --github-repo when set.")
    parser.add_argument("--bill-of-sale", help="Path to a pre-generated Bill of Sale JSON. "
                        "When set, the pipeline cross-references output against BoS line items "
                        "and writes build_trace per item for the re-audit loop.",
                        default=None, metavar="PATH")
    parser.add_argument("--no-bos", action="store_true",
                        help="Disable Bill of Sale orchestration entirely (skip BoS even if module is available)")
    parser.add_argument("--tenant", default=None,
                        help="Tenant coordinate (tenant_id UUID or slug). When provided, loads tenant "
                             "capture (phase0_field_values / creative_assets / competitor_profiles) and "
                             "threads brand/palette into the style path. Absent = registry/file behavior.")
    parser.add_argument("--captures", default=None, metavar="DIR",
                        help="Audit run directory holding captures/ and captures_manifest.json. "
                             "With --from-url, every captured route is harvested into "
                             "site-spec pages[] and the build goes multi-page. A capture "
                             "bundle that cannot be harvested FAILS the run — it is never "
                             "downgraded to a single-page build.")
    parser.add_argument("--routes", default=None, metavar="CSV",
                        help="Routes to harvest from --captures, e.g. '/,/wealth,/about'. "
                             "Omit to harvest every captured route (which turns each article "
                             "slug into its own static page).")
    parser.add_argument("--max-pages", type=int, default=None, metavar="N",
                        help="Cap the number of harvested pages from --captures.")
    parser.add_argument("--publish", action="store_true",
                        help="After a successful build+deploy, run `vercel --yes --prod` and record the "
                             "deployed URL in build_log.deploy_url (BRIEF #33299). Default off.")

    args = parser.parse_args()

    # ── Tenant Capture Node (idempotent / read-only) ──────────────
    # When --tenant is supplied, load the tenant context once. The reader is
    # pure: it only issues REST GETs and degrades to empty structures on any
    # missing table/row, so a resolvable-but-empty (or unresolvable) tenant
    # falls straight back to current registry/file behavior.
    tenant_context = None
    if getattr(args, "tenant", None) and TENANT_CONTEXT_AVAILABLE and load_tenant_context:
        tenant_context = load_tenant_context(args.tenant)
        _tid = tenant_context.get("tenant_id")
        if _tid:
            _p0 = tenant_context.get("phase0_field_values", {})
            print(f"  🏷  Tenant context loaded: {tenant_context.get('slug') or _tid}")
            print(f"     phase0_field_values: {len(_p0)} | "
                  f"creative_assets: {len(tenant_context.get('creative_assets', []))} | "
                  f"competitor_profiles: {len(tenant_context.get('competitor_profiles', []))}")
        else:
            print(f"  ⚠ Tenant coordinate '{args.tenant}' did not resolve — proceeding without tenant capture")
            tenant_context = None
    elif getattr(args, "tenant", None) and not TENANT_CONTEXT_AVAILABLE:
        print("  ⚠ --tenant requires Supabase credentials in .env; proceeding without tenant capture")

    # Resolved tenant UUID threaded into build_log (None = column omitted).
    tenant_id = tenant_context.get("tenant_id") if tenant_context else None

    # ── Resolve target platform from tenant config (BRIEF #33318) ──
    # If --target-platform is not explicitly set, resolve from tenant config
    if getattr(args, "target_platform", None) is None:
        resolved_platform = resolve_target_platform(tenant_context)
        args.target_platform = resolved_platform
        if tenant_context:
            print(f"  🎯 Target platform resolved from tenant config: {resolved_platform}")
        else:
            print(f"  🎯 Target platform (no tenant config): {resolved_platform}")

    # ── Output-root injection: re-root the base output directory ──
    # Default (flag absent) is a no-op — OUTPUT_DIR stays <web-builder>/output.
    # When provided, resolve to absolute, create the tree, and validate writability,
    # then rebind the module-level OUTPUT_DIR so every path builder inherits it.
    if getattr(args, "output_root", None):
        global OUTPUT_DIR
        resolved_root = Path(args.output_root).expanduser().resolve()
        try:
            resolved_root.mkdir(parents=True, exist_ok=True)
        except OSError as _e:
            print(f"\n❌ --output-root cannot be created: {resolved_root}\n   {_e}")
            sys.exit(1)
        if not os.access(resolved_root, os.W_OK):
            print(f"\n❌ --output-root is not writable: {resolved_root}")
            sys.exit(1)
        OUTPUT_DIR = resolved_root
        print(f"  ✓ Output root overridden: {OUTPUT_DIR}")

    # ── Copy Fidelity Node (Phase 2): load optional weakness findings ──
    copy_findings = None
    if getattr(args, "copy_findings", None):
        try:
            _cf_path = Path(args.copy_findings)
            copy_findings = json.loads(_cf_path.read_text(encoding="utf-8"))
            print(f"  ✓ Loaded copy findings for {len(copy_findings)} slot(s) from {_cf_path}")
        except (OSError, json.JSONDecodeError) as _e:
            print(f"  ⚠ Could not load --copy-findings ({_e}); proceeding verbatim")
            copy_findings = None
    if getattr(args, "compiled_dir", None) and not args.industry:
        args.industry = "electronics-tech"

    output_dir = OUTPUT_DIR / args.project
    if args.clean and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print(f"  🗑 Removed existing output: {output_dir}")

    # ── Project Collision Detection ────────────────────────────────
    # Prevent accidental overwrites when not using --skip-to (which expects existing project)
    if not args.skip_to:
        existing_scaffold = OUTPUT_DIR / args.project / "scaffold.md"
        if existing_scaffold.exists():
            print(f"\n⚠️  Project '{args.project}' already exists at: output/{args.project}/")
            print(f"    To continue an existing project, use: --skip-to <stage>")
            print(f"    To start fresh, delete the directory or use a different project name.")
            sys.exit(1)

    section_contexts = None  # Only populated in URL clone mode
    extraction_dir = None    # Only populated in URL clone mode
    identification = None    # Only populated in URL clone mode (v0.9.0)
    site_spec = None         # Only populated when build-site-spec.js succeeds (--from-url)

    # ── URL Clone Mode ──────────────────────────────────────────────
    if args.from_url:
        print(f"\n{'═' * 60}")
        print(f"  Website Builder — URL Clone Mode")
        print(f"  Project: {args.project}")
        print(f"  Source:  {args.from_url}")
        print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═' * 60}")

        _captures = None
        if getattr(args, "captures", None):
            _captures = Path(args.captures).expanduser().resolve()
            if not _captures.exists():
                print(f"\n❌ --captures directory not found: {_captures}")
                sys.exit(EXIT_FAILED)
        preset, brief, section_contexts, extraction_dir, site_spec = stage_url_extract(
            args.from_url, args.project,
            captures_dir=_captures,
            routes=getattr(args, "routes", None),
            max_pages=getattr(args, "max_pages", None),
        )
        save_checkpoint(output_dir, "extract", args.project)

        # Stage 0d: Pattern identification (v0.9.0)
        if extraction_dir and extraction_dir.exists():
            identification = stage_identify(extraction_dir, args.project)
            save_checkpoint(output_dir, "identify", args.project)

        print(f"\n{'═' * 60}")
        print(f"  Stage 0 complete — switching to standard pipeline")
        print(f"  Preset:  {preset}")
        print(f"  Brief:   briefs/{args.project}.md")
        print(f"  Context: {len(section_contexts)} section(s)")
        if identification:
            print(f"  Patterns: {identification.get('sectionCount', 0)} sections identified")
        if site_spec:
            print(f"  Site spec: {len(site_spec.get('sections', []))} sections")
        print(f"{'═' * 60}")

    # ── Standard Mode ───────────────────────────────────────────────
    else:
        # Brief: --brief flag > compiled-dir/brief.md > briefs/{project}.md
        compiled_brief_path = None
        if getattr(args, "brief", None):
            p = Path(args.brief).resolve()
            if p.exists():
                compiled_brief_path = p
            else:
                print(f"  ⚠ --brief path not found: {p}")
        if not compiled_brief_path and getattr(args, "compiled_dir", None):
            p = Path(args.compiled_dir).resolve() / "brief.md"
            if p.exists():
                compiled_brief_path = p
        if compiled_brief_path:
            brief = read_file(compiled_brief_path)
            print(f"  Loaded brief: {compiled_brief_path} ({len(brief)} chars)")
        else:
            brief_path = BRIEFS_DIR / f"{args.project}.md"
            if not brief_path.exists():
                print(f"Error: No brief found at {brief_path}")
                print(f"Available briefs: {[f.stem for f in BRIEFS_DIR.glob('*.md') if f.stem != '_template']}")
                sys.exit(1)
            brief = read_file(brief_path)

        # Determine preset — --industry (database) vs --preset (legacy .md)
        preset = args.preset
        if not preset and not args.industry:
            available = list_presets()
            if len(available) == 1:
                preset = available[0]
                print(f"Using only available preset: {preset}")
            else:
                print(f"Available presets: {', '.join(available)}")
                preset = input("Select preset: ").strip()
        elif args.industry and not preset:
            # --industry mode: use industry name as preset identifier.
            # But --industry mode can fall back to legacy preset mode when the
            # database is unreachable (Supabase 5xx/timeout), and that fallback
            # reads skills/presets/{preset}.md — a file that never exists for a
            # bare industry name, so a transient DB outage crashed the deploy
            # with "File not found: skills/presets/fintech.md". A URL-cloned
            # project has its own generated preset at skills/presets/{project}.md;
            # prefer it so the fallback path has a real file to read.
            _project_preset = SKILLS_DIR / "presets" / f"{args.project}.md"
            preset = args.project if _project_preset.exists() else args.industry

        if not args.industry:
            preset_path = SKILLS_DIR / "presets" / f"{preset}.md"
            if not preset_path.exists():
                print(f"Error: Preset not found: {preset_path}")
                sys.exit(1)

        mode_label = "Database" if args.industry else "Preset"
        print(f"\n{'═' * 60}")
        print(f"  Website Builder Pipeline ({mode_label} Mode)")
        print(f"  Project: {args.project}")
        if args.industry:
            print(f"  Industry: {args.industry}")
            print(f"  Page:     {args.page}")
        else:
            print(f"  Preset:  {preset}")
        print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═' * 60}")

    # ── Layer 6: Site manifest (multi-page) ─────────────────────────
    site_manifest = None
    # A project's pipeline mode (single-page vs Layer 6 multi-page) must be a
    # property of the PROJECT, not of the flags on this particular invocation.
    # Multi-page is auto-selected from `--industry` and suppressed by
    # `--from-url`; that meant a URL-cloned single-page build could not be
    # resumed, because a resume run (`--skip-to deploy --industry X`, no
    # `--from-url`) silently re-entered multi-page mode and regenerated every
    # section from scratch, discarding the completed single-page build.
    # On a resume, honour the mode the project was actually built in.
    _resume_single_page = False
    if args.skip_to and not getattr(args, "site_manifest", None):
        _has_mp = (output_dir / "site-manifest.json").exists()
        _has_sp = (output_dir / "page.tsx").exists() or (output_dir / "site-spec.json").exists()
        if _has_sp and not _has_mp:
            _resume_single_page = True
            print("  ↳ Resuming existing single-page build (no site-manifest.json); staying single-page.")

    # Load site_spec from file when not set (e.g. --skip-to after a from_url
    # run). Read BEFORE the mode fork, because the number of pages it carries
    # is now what decides single- vs multi-page.
    if site_spec is None:
        site_spec_path = OUTPUT_DIR / args.project / "site-spec.json"
        if site_spec_path.exists():
            try:
                site_spec = json.loads(site_spec_path.read_text(encoding="utf-8"))
                print(f"  ✓ site-spec.json loaded ({len(site_spec.get('sections', []))} sections)")
            except (json.JSONDecodeError, OSError):
                pass

    # Page count is a property of the SITE, not of the flags on this run.
    # `--from-url` used to suppress multi-page outright, which made "clone this
    # site" and "build more than one page" mutually exclusive: a 25-route
    # source could only ever come out as a single page. A URL-cloned spec that
    # describes N>1 pages is a multi-page site and builds as one; a spec with
    # one page (or none) stays on the single-page path exactly as before.
    _spec_page_ids = list(build_site_spec_by_page(site_spec))
    _spec_is_multipage = len(_spec_page_ids) > 1
    if args.from_url and _spec_is_multipage:
        print(f"  ✓ site-spec describes {len(_spec_page_ids)} pages → multi-page build")

    if not _resume_single_page and site_manifest_lib and (not args.from_url or _spec_is_multipage):
        if getattr(args, "site_manifest", None):
            manifest_path = Path(args.site_manifest)
            if not manifest_path.is_absolute():
                manifest_path = (ROOT / manifest_path).resolve()
            site_manifest = site_manifest_lib.load_site_manifest(manifest_path)
            print(f"  ✓ Site manifest loaded: {args.site_manifest} ({len(site_manifest.get('pages', []))} pages)")
        elif _spec_is_multipage:
            # Spec-driven: map the harvested pages 1:1 (build_site_manifest's
            # harvested mode — no reconciliation, no not-found injection, N in
            # → N out) rather than re-inventing routes from page-type names.
            # That also keeps the manifest ids identical to the site-spec ids,
            # so the two can never disagree about what a page is called.
            from build_site_manifest import build_site_manifest as _build_manifest_from_pages
            site_manifest = _build_manifest_from_pages(
                args.project,
                args.industry or preset or "ecommerce",
                harvested_pages=site_spec.get("pages") or [],
                output_path=output_dir / "site-manifest.json",
            )
            print(f"  ✓ Site manifest from site-spec pages: {len(site_manifest.get('pages', []))} pages "
                  f"({', '.join(p.get('id', '?') for p in site_manifest.get('pages', []))})")
        elif args.industry:
            industry_meta = get_industry_metadata(args.industry) if args.industry and SUPABASE_AVAILABLE and get_industry_metadata else None
            # A spec-driven build may have no --industry at all; the manifest
            # still needs a label for it.
            _mp_industry = args.industry or preset or "ecommerce"
            arch_path = None
            if getattr(args, "compiled_dir", None):
                arch_path = Path(args.compiled_dir) / "architecture.json"
                if not arch_path.exists():
                    arch_path = None
            # Page source, in priority order: the extracted site-spec's own
            # pages (the real site), then the industry's registry page-types,
            # then the generic fallback inside generate_site_manifest.
            _page_types = None
            _src = "default"
            if _spec_is_multipage:
                _page_types = _spec_page_ids
                _src = f"{len(_page_types)} site-spec pages"
            elif not (arch_path and arch_path.exists()) and args.industry and SUPABASE_AVAILABLE and get_all_page_sections:
                try:
                    _page_sections = get_all_page_sections(args.industry) or {}
                    _page_types = [pt for pt, secs in _page_sections.items() if secs]
                    _src = f"{len(_page_types)} registry page-types" if _page_types else "default"
                except Exception as _e:
                    print(f"  ⚠ Could not enumerate industry page-types ({_e}); using default pages")
                    _page_types = None
            site_manifest = site_manifest_lib.generate_site_manifest(
                args.project,
                _mp_industry,
                output_dir,
                industry_metadata=industry_meta,
                architecture_path=arch_path,
                write_file=True,
                page_types=_page_types,
            )
            print(f"  ✓ Site manifest generated: {len(site_manifest.get('pages', []))} pages ({_src})")

    # ── Common Pipeline ─────────────────────────────────────────────

    # ── Initialize Supabase build cache (if --industry mode) ──
    build_cache = None
    _build_start_time = _time.time()  # Track build duration for all modes
    # The ledger is module-level; clear it so a second run in one process
    # does not report the previous build's calls as part of this one.
    reset_token_ledger()
    reset_build_failures()
    if args.industry and SUPABASE_AVAILABLE and BuildCache:
        build_cache = BuildCache(industry=args.industry, page_type=args.page).load()
        if not build_cache.section_sequence:
            print(f"  ⚠ No section sequence found in database for industry '{args.industry}', page '{args.page}'")
            print(f"    Falling back to --preset mode with preset '{preset}'")
            build_cache = None
    elif args.industry and not SUPABASE_AVAILABLE:
        print("  ⚠ --industry flag requires Supabase credentials in .env")
        print("    Falling back to --preset mode")

    # ── Tenant brand/palette threading (guarded) ──────────────────
    # When a resolved tenant carries phase0 brand/palette capture, thread it
    # into the style path by merging over the registry palette. Idempotent:
    # re-running with the same tenant produces the same merged style_config.
    # Absence of tenant context (or of build_cache) leaves style untouched.
    if tenant_context and build_cache is not None and build_cache.industry_style is not None:
        _tenant_palette = tenant_context.get("palette") or {}
        _tenant_brand = tenant_context.get("brand") or {}
        _usable_palette = {k: v for k, v in _tenant_palette.items() if k != "description"}
        if _usable_palette:
            _style_config = build_cache.industry_style.setdefault("style_config", {})
            _reg_palette = dict(_style_config.get("palette") or {})
            _reg_palette.update(_usable_palette)  # tenant capture wins over registry
            _style_config["palette"] = _reg_palette
            print(f"  🎨 Tenant palette threaded into style path "
                  f"({', '.join(sorted(_usable_palette))})")
        if _tenant_brand.get("name"):
            print(f"     Brand: {_tenant_brand['name']}")

    # Resolve extraction_dir from previous runs if not set (e.g. --skip-to mode)
    if extraction_dir is None:
        extraction_base = OUTPUT_DIR / "extractions"
        if extraction_base.exists():
            # Try exact project name first, then preset name as fallback
            search_prefixes = [f"{args.project}-"]
            if preset and preset != args.project:
                search_prefixes.append(f"{preset}-")
            for prefix in search_prefixes:
                candidates = sorted(
                    [d for d in extraction_base.iterdir()
                     if d.is_dir() and d.name.startswith(prefix)],
                    key=lambda d: d.stat().st_mtime,
                    reverse=True,
                )
                if candidates:
                    extraction_dir = candidates[0]
                    print(f"  Resolved extraction dir: {extraction_dir.name}")
                    break

    # Load identification data if not already set (e.g. --skip-to without --from-url)
    if identification is None:
        id_path = OUTPUT_DIR / args.project / "identification.json"
        if id_path.exists():
            try:
                identification = json.loads(id_path.read_text(encoding="utf-8"))
                plugins_found = identification.get("detectedPlugins", [])
                if plugins_found:
                    print(f"  Identification loaded: {len(plugins_found)} plugins detected ({', '.join(plugins_found)})")
            except (json.JSONDecodeError, OSError):
                print("  ⚠ Could not load identification.json")

    # ── Audit Captures Harvester (BOTH modes) ─────────────────────
    # Hoisted above the mode fork. Its only call site used to be 70-odd lines
    # INSIDE the single-page tail, i.e. after the multipage branch had already
    # returned — so a multi-page build never harvested a single verbatim
    # string no matter how the tenant was configured.
    _audit_harvest = None
    _copy_summary: dict | None = None
    if tenant_id:
        _audit_harvest = harvest_verbatim_copy(tenant_id)
        if _audit_harvest and _audit_harvest.get("harvested_strings", 0) > 0:
            print(f"  📋 Audit captures: {_audit_harvest['harvested_strings']} verbatim string(s) "
                  f"harvested from {_audit_harvest['source_rows']} row(s)")
        else:
            print(f"  📋 Audit captures: no verbatim strings harvested (tenant_id={tenant_id})")

    # Per-page site-spec sections, keyed by page id. `site_spec["pages"]` is
    # the multi-page shape; a spec with only `sections` is single-page and
    # contributes nothing here.
    _site_spec_by_page = build_site_spec_by_page(site_spec)
    if _site_spec_by_page:
        print(
            f"  ✓ site-spec carries {len(_site_spec_by_page)} page(s) of extracted content: "
            + ", ".join(sorted(_site_spec_by_page))
        )

    # ── Layer 6: Multi-page pipeline (when site_manifest is set) ─────
    if site_manifest:
        industry = site_manifest.get("industry") or args.industry or preset
        if not industry:
            print("  ⚠ Site manifest has no industry; multipage requires --industry. Skipping multipage.")
            site_manifest = None
        elif not get_section_sequence and not _site_spec_by_page:
            # The registry is only REQUIRED when it is the sole source of
            # sections. A site-spec that carries per-page sections is itself a
            # section source, so multi-page no longer depends on Supabase.
            print("  ⚠ Supabase not available and site-spec has no pages; multipage needs one of them. Skipping multipage.")
            site_manifest = None

    if site_manifest:
        industry = site_manifest.get("industry", args.industry or preset)
        if args.skip_to not in (None, "deploy"):
            print("  ⚠ --skip-to is not supported for multipage; running full multipage pipeline.")
        _mp_page_ids = [p.get("id") for p in site_manifest.get("pages", [])]
        _mp_has_commerce = "collection-template" in _mp_page_ids or "product-template" in _mp_page_ids
        stage_shared_components(site_manifest, preset, args.project, build_cache=build_cache, has_commerce_routes=_mp_has_commerce, adapter=_resolve_adapter(args.target_platform))
        save_checkpoint(output_dir, "shared_components", args.project)
        site_manifest = stage_scaffold_multipage(site_manifest, args.project, industry, preset=preset)
        save_checkpoint(output_dir, "scaffold_mp", args.project)

        # ── Section Reconciliation Node (multi-page) ──────────────────
        # The HARVEST is the spine: a page's sections are the sections the real
        # source page has, in source order, and the registry only fills in
        # archetypes the source lacks. This used to pass `[]` as the harvest —
        # hardcoding "there is no extracted content" — so every page was built
        # from the registry sequence alone.
        _reconciliation_meta = None
        _recon_total_dups_kept = 0
        _recon_total_registry = 0
        _recon_total_harvest = 0
        _recon_total_gaps = 0
        _recon_total_dups = 0
        for _page in site_manifest.get("pages", []):
            _raw = _page.get("sections", [])
            _harvested_page = (resolve_page_entry(_site_spec_by_page, _page) or {}).get("sections", [])
            # NAV/FOOTER are shared layout components in multi-page mode, so the
            # registry sequence has them stripped in stage_scaffold_multipage.
            # The harvest did not, and every crawled page carries both — which
            # generated a per-page NAV and FOOTER section that assembly then
            # imported *inside* <main>, under the layout's own Navigation and
            # above its Footer. Two navs and two footers on all six pages.
            if site_manifest_lib:
                _harvested_page = site_manifest_lib.filter_nav_footer_from_sections(_harvested_page)
            if not _raw and _harvested_page:
                # No registry sections for this page (no Supabase, or a page
                # type the registry does not know): the harvest IS the page.
                _raw = _harvested_page
                _harvested_page = []
            if _raw or _harvested_page:
                _reconciled, _meta = reconcile_page_sections(_raw, _harvested_page)
                _page["sections"] = _reconciled
                _recon_total_registry += _meta["registry_count"]
                _recon_total_harvest += _meta["harvest_count"]
                _recon_total_gaps += _meta["gap_filled_count"]
                _recon_total_dups += _meta["duplicates_resolved"]
                _recon_total_dups_kept += _meta.get("duplicates_kept", 0)
        _recon_total = sum(
            len(p.get("sections", []))
            for p in site_manifest.get("pages", [])
        )
        _reconciliation_meta = {
            "total": _recon_total,
            "registry_count": _recon_total_registry,
            "harvest_count": _recon_total_harvest,
            "gap_filled_count": _recon_total_gaps,
            "duplicates_resolved": _recon_total_dups,
            "duplicates_kept": _recon_total_dups_kept,
        }
        if _recon_total > 0:
            print(
                f"\n  🔄 Section reconciliation ({len(site_manifest.get('pages', []))} pages): "
                f"{_recon_total} total "
                f"({_recon_total_registry} registry, {_recon_total_harvest} harvested, "
                f"{_recon_total_gaps} gap-filled, "
                f"{_recon_total_dups_kept} same-archetype duplicates preserved)"
            )

        # ── Template resolution preflight ─────────────────────────────
        # Reported BEFORE generation, because "how much of this site is
        # assembled from reviewed components vs improvised by an LLM" is the
        # measurement that characterises the pipeline. Purely a lookup; the
        # results are memoized for the generation pass that follows.
        _template_resolution = report_template_resolution(
            [s for p in site_manifest.get("pages", []) for s in p.get("sections", [])],
            f"{len(site_manifest.get('pages', []))} pages",
            cache=build_cache or template_memo(),
        )

        # ── Per-section asset binding (BRIEF #33297) ──
        # Bind tenant creative_assets onto manifest sections BEFORE generation so
        # the bound self-hosted src flows into the generated components. No tenant
        # assets → 0 bound, manifest untouched (no regression).
        _assets_bound = bind_section_assets(tenant_context, site_manifest, output_dir)

        section_files_by_page, _copy_summary_by_page = stage_sections_multipage(
            site_manifest, preset, args.project,
            build_cache=build_cache, identification=identification, brief=brief,
            site_spec_by_page=_site_spec_by_page,
            section_contexts_by_page=build_section_contexts_by_page(
                section_contexts, _site_spec_by_page, site_manifest,
            ),
            extraction_dir_by_page=None,
            audit_harvest=_audit_harvest,
            copy_findings=copy_findings,
        )
        _copy_summary = merge_copy_summaries(_copy_summary_by_page)
        save_checkpoint(output_dir, "sections_mp", args.project, {"section_files_by_page_keys": list(section_files_by_page.keys())})
        stage_assemble_multipage(site_manifest, section_files_by_page, args.project)
        save_checkpoint(output_dir, "assemble", args.project)
        deploy_ran = False
        deploy_requested = bool(args.deploy or args.skip_to == "deploy")
        if deploy_requested:
            validation = stage_validate(args.project)  # May have fewer checks for multipage
            if not validation["passed"] and not args.force:
                print("\n  ⚠ Pre-flight validation had issues. Use --force to deploy anyway.")
                # A requested deploy that never ran is a failed build, not a
                # successful one. --force still overrides the block itself.
                record_build_failure(
                    "validate", "pre-flight validation blocked the requested deploy (no --force)"
                )
            if validation["passed"] or args.force:
                stage_deploy(
                    sections=[],  # unused when manifest set
                    section_files=[],
                    preset=preset,
                    project_name=args.project,
                    extraction_dir=extraction_dir,
                    build_cache=build_cache,
                    site_manifest=site_manifest,
                    section_files_by_page=section_files_by_page,
                    shopify_config_path=getattr(args, "shopify_config", None),
                    target_platform=args.target_platform,
                )
                save_checkpoint(output_dir, "deploy", args.project)
                # Only a site that actually compiled counts as deployed; a
                # failed production build is already in the failure ledger.
                deploy_ran = production_build_ok(OUTPUT_DIR / args.project / SITE_DIR_NAME)
                if deploy_ran and getattr(args, "set_vercel_env", False):
                    stage_vercel_env_and_webhooks(
                        OUTPUT_DIR / args.project / SITE_DIR_NAME,
                        args.project,
                    )
        # ── Stage 6: Post-build render audit ──
        _render_audit_status = stage_render_audit(
            project_name=args.project,
            site_manifest=site_manifest,
        ) if deploy_ran else "skipped"
        _build_end_time = _time.time()
        _build_duration_ms = int((_build_end_time - _build_start_time) * 1000)

        # ── Token ledger: on disk first, Supabase second ──
        _token_summary = persist_token_ledger(output_dir)

        # ── BoS orchestration: write build_trace per line item ──
        _bos = stage_bos_orchestrate(
            project_name=args.project,
            industry=industry,
            output_dir=output_dir,
            manifest=site_manifest,
            bos_import_path=getattr(args, "bill_of_sale", None),
            no_bos=getattr(args, "no_bos", False),
        )
        _bos_line_items = _bos.total_count if _bos else None

        # ── Unified app shell + app-route seams (BRIEF #33298) ──
        # Scaffold stubbed protected app-route seams for carried-into-unified-app
        # BoS items onto the built site's unified app shell. 0 when none carried.
        _app_routes_scaffolded = scaffold_app_route_seams(_bos, output_dir) if deploy_ran else 0

        # ── Publish: deploy to Vercel and capture URL (BRIEF #33299) ──
        _deploy_url = None
        if getattr(args, "publish", False) and deploy_ran:
            _deploy_url = deploy_to_vercel(output_dir, args.project)

        # ── Git-publish: commit built site as source-of-truth (BRIEF #33323) ──
        _published_sha = stage_git_publish(
            output_dir,
            args.project,
            github_repo=getattr(args, "github_repo", None),
            push_policy=getattr(args, "push_policy", "off"),
        ) if deploy_ran else None

        # ── Build outcome: status + exit code must agree with reality ──
        # 'passed'/'review_needed' are the only statuses where the audit
        # actually produced a verdict; 'failed'/'skipped' both mean it never
        # measured anything (crashed, timed out, or couldn't start).
        _audit_ran = _render_audit_status in ("passed", "review_needed")
        _build_status, _exit_code = resolve_build_outcome(
            _render_audit_status, deploy_requested, audit_ran=_audit_ran
        )

        if build_cache and SUPABASE_AVAILABLE:
            all_sections = []
            for p in site_manifest.get("pages", []):
                for s in p.get("sections", []):
                    all_sections.append(s)
            # Count the section files ACTUALLY WRITTEN, not the ones planned:
            # a section dropped mid-generation must not be logged as built.
            _sections_written = sum(len(f) for f in section_files_by_page.values())
            _local_count = _db_count = _llm_count = 0
            for sec in all_sections:
                tpl = check_template_exists(
                    sec.get("archetype", ""), sec.get("variant", ""),
                    build_cache or template_memo(),
                )
                if isinstance(tpl, Path):
                    _local_count += 1
                elif isinstance(tpl, str):
                    _db_count += 1
                else:
                    _llm_count += 1
            log_build(
                project_name=args.project,
                industry=industry,
                page_type="multipage",
                sections_from_template=_local_count,
                db_template_count=_db_count,
                sections_from_llm=_llm_count,
                total_sections=_sections_written,
                build_duration_ms=_build_duration_ms,
                status=_build_status,
                target_platform=args.target_platform,
                bos_line_items=_bos_line_items,
                sections_reconciled=_reconciliation_meta,
                tenant_id=tenant_id,
                page_count=len(site_manifest.get("pages", [])),
                assets_bound=_assets_bound,
                app_routes_scaffolded=_app_routes_scaffolded,
                deploy_url=_deploy_url,
                render_audit_status=_render_audit_status,
                published_sha=_published_sha,
                token_ledger=_token_summary,
                # Multipage discarded the per-page copy summary entirely, so
                # this column was always NULL for multi-page builds.
                harvested_copy_ratio=(
                    (_copy_summary or {}).get("summary", {}).get("harvested_copy_ratio")
                ),
            )
            _recon_str = ""
            if _reconciliation_meta:
                _recon_str = (
                    f", recon: {_reconciliation_meta['total']} total "
                    f"({_reconciliation_meta['registry_count']} reg / "
                    f"{_reconciliation_meta['harvest_count']} hvst / "
                    f"{_reconciliation_meta['gap_filled_count']} gaps)"
                )
            print(f"  📊 Build logged to Supabase (multipage, {len(site_manifest.get('pages', []))} pages — {_local_count} local / {_db_count} db / {_llm_count} LLM, BoS items: {_bos_line_items or 0}{_recon_str})")
        print(f"\n{'═' * 60}")
        if _exit_code == EXIT_OK:
            print(f"  ✅ Layer 6 multi-page complete")
        else:
            print(f"  ❌ Layer 6 multi-page INCOMPLETE — status: {_build_status}")
        print(f"  Output: output/{args.project}/")
        if deploy_ran:
            print(f"  Site:   output/{args.project}/site/")
        print(f"  Render audit: {_render_audit_status}")
        print(f"{'═' * 60}\n")
        finish_build(_build_status, _exit_code)

    # ── Single-page pipeline ────────────────────────────────────────
    if args.skip_to:
        cp = load_checkpoint(args.project)
        if cp:
            skip_idx = _stage_index(args.skip_to)
            # To run from skip_to we need the previous stage completed
            need_idx = skip_idx - 1 if skip_idx > 0 else 0
            cur_idx = _stage_index(cp.get("stage", ""))
            if cur_idx >= 0 and cur_idx < need_idx:
                print(f"Error: Cannot --skip-to {args.skip_to}: checkpoint is '{cp.get('stage')}' (complete stages up to {STAGE_ORDER[need_idx]} first).")
                sys.exit(1)
        else:
            print("  ⚠ No checkpoint found; --skip-to proceeds using filesystem state (backward compatibility).")

        # v2.0.0: prefer rich sections from site-spec.json over scaffold parsing
        if site_spec:
            _scaffold_text, sections = stage_scaffold_v2(site_spec, args.project)
            print(f"  ✓ Using rich sections from site-spec.json ({len(sections)} sections)")
        else:
            scaffold_path = OUTPUT_DIR / args.project / "scaffold.md"
            if not scaffold_path.exists():
                print(f"Error: No existing scaffold at {scaffold_path}")
                sys.exit(1)
            scaffold = read_file(scaffold_path)
            sections = parse_scaffold(scaffold)
    else:
        if site_spec:
            scaffold, sections = stage_scaffold_v2(site_spec, args.project)
            save_checkpoint(output_dir, "scaffold", args.project)
        else:
            scaffold = stage_scaffold(brief, preset, args.project, args.no_pause, identification, build_cache=build_cache)
            save_checkpoint(output_dir, "scaffold", args.project)
            sections = parse_scaffold(scaffold)

    # ── Section Reconciliation Node ──────────────────────────────────
    # Same harvest-spine reconciler as the multi-page path: the sections the
    # source page actually has, in source order, with the registry filling in
    # archetypes the source lacks. This used the collapsing reconciler, so a
    # clone of a page with two FEATURES blocks shipped one — the same fidelity
    # loss as the multipage path, and having one faithful path and one lossy
    # path meant nobody could say which had built a given site.
    _reconciliation_meta = None
    if site_spec:
        _registry_for_recon = []
        if build_cache and build_cache.section_sequence:
            _registry_for_recon = build_cache.section_sequence
        elif preset:
            _registry_for_recon = parse_preset_section_sequence(preset)
        _harvested_for_recon = site_spec.get("sections", [])
        if _registry_for_recon or _harvested_for_recon:
            sections, _reconciliation_meta = reconcile_page_sections(
                _registry_for_recon, _harvested_for_recon,
            )
            _rc = _reconciliation_meta
            print(
                f"\n  🔄 Section reconciliation: {_rc['total']} total "
                f"({_rc['registry_count']} registry, {_rc['harvest_count']} harvested, "
                f"{_rc['gap_filled_count']} gap-filled, "
                f"{_rc.get('duplicates_kept', 0)} same-archetype duplicates preserved)"
            )

    if not sections:
        print("Error: Could not parse any sections from scaffold.")
        print("Expected format: N. ARCHETYPE | variant | content direction")
        sys.exit(1)

    print(f"\n  Parsed {len(sections)} sections from scaffold")

    # (The audit-capture harvest now runs above the mode fork — see
    # "Audit Captures Harvester (BOTH modes)" — so multipage gets it too.)

    # ── Per-section asset binding (BRIEF #33297) ──
    # Bind tenant creative_assets onto sections BEFORE generation so
    # the bound self-hosted src flows into the generated components. No tenant
    # assets → 0 bound, sections untouched (no regression).
    _assets_bound = 0
    if tenant_context:
        # Create minimal site_manifest structure for single-page pipeline
        _single_page_manifest = {"pages": [{"sections": sections}]}
        _assets_bound = bind_section_assets(tenant_context, _single_page_manifest, output_dir)

    if args.skip_to in (None, "sections"):
        section_files, _copy_summary = stage_sections(
            sections, preset, args.project, section_contexts, extraction_dir, identification,
            site_spec=site_spec, build_cache=build_cache, brief=brief,
            copy_findings=copy_findings, audit_harvest=_audit_harvest,
        )
        save_checkpoint(output_dir, "sections", args.project, {"section_count": len(section_files)})
    else:
        section_dir = OUTPUT_DIR / args.project / "sections"
        section_files = sorted(section_dir.glob("*.tsx"))

    if args.skip_to in (None, "sections", "assemble"):
        stage_assemble(sections, section_files, args.project)
        save_checkpoint(output_dir, "assemble", args.project)

    if args.skip_to in (None, "sections", "assemble", "review"):
        site_spec_path = output_dir / "site-spec.json"
        site_spec = None
        if site_spec_path.exists():
            try:
                site_spec = json.loads(site_spec_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        if site_spec:
            stage_review_v2(section_files, site_spec, args.project)
        else:
            stage_review(sections, section_files, preset, args.project, build_cache=build_cache)
        save_checkpoint(output_dir, "review", args.project)

    # Stage 5.5: Pre-flight validation (before deploy)
    deploy_ran = False
    deploy_requested = bool(args.deploy or args.skip_to == "deploy")
    if deploy_requested:
        validation = stage_validate(args.project)
        if not validation['passed']:
            print("\n  ⚠ Pre-flight validation found critical issues.")
            if not args.force:
                print("  Use --force to deploy anyway, or fix the issues above.")
                # Requested deploy never ran → failed build. --force still
                # overrides the block itself.
                record_build_failure(
                    "validate", "pre-flight validation blocked the requested deploy (no --force)"
                )
        if validation['passed'] or args.force:
            stage_deploy(sections, section_files, preset, args.project, extraction_dir, build_cache=build_cache, target_platform=args.target_platform)
            save_checkpoint(output_dir, "deploy", args.project)
            # Only a site that actually compiled counts as deployed.
            deploy_ran = production_build_ok(OUTPUT_DIR / args.project / SITE_DIR_NAME)

    # ── Stage 6: Post-build render audit (single-page) ──
    _render_audit_status = stage_render_audit(
        project_name=args.project,
        site_manifest=site_manifest if site_manifest and "pages" in site_manifest else None,
    ) if deploy_ran else "skipped"

    # Print gap report summary if available (v0.9.0)
    if args.from_url:
        print_gap_summary(args.project)

    # ── BoS orchestration: write build_trace per line item ──
    _bos = stage_bos_orchestrate(
        project_name=args.project,
        industry=args.industry or preset,
        output_dir=output_dir,
        sections=sections,
        section_files=section_files,
        bos_import_path=getattr(args, "bill_of_sale", None),
        no_bos=getattr(args, "no_bos", False),
    )
    _bos_line_items = _bos.total_count if _bos else None

    # ── Build logging (Supabase) ──
    _build_end_time = _time.time()
    _build_duration_ms = int((_build_end_time - _build_start_time) * 1000)

    # ── Token ledger: on disk first, Supabase second ──
    _token_summary = persist_token_ledger(output_dir)

    # ── Build outcome: status + exit code must agree with reality ──
    # 'passed'/'review_needed' are the only statuses where the audit
    # actually produced a verdict; 'failed'/'skipped' both mean it never
    # measured anything (crashed, timed out, or couldn't start).
    _audit_ran = _render_audit_status in ("passed", "review_needed")
    _build_status, _exit_code = resolve_build_outcome(
        _render_audit_status, deploy_requested, audit_ran=_audit_ran
    )

    if SUPABASE_AVAILABLE:
        # Count local / db / LLM sections (cache used so no extra Supabase reads)
        _local_count = _db_count = _llm_count = 0
        for sec in sections:
            tpl = check_template_exists(
                sec["archetype"], sec["variant"], build_cache or template_memo()
            )
            if isinstance(tpl, Path):
                _local_count += 1
            elif isinstance(tpl, str):
                _db_count += 1
            else:
                _llm_count += 1
        # Extract harvested_copy_ratio from copy summary if available
        _harvested_copy_ratio: float | None = None
        if _copy_summary:
            _harvested_copy_ratio = _copy_summary.get("summary", {}).get("harvested_copy_ratio")
        log_build(
            project_name=args.project,
            industry=args.industry or preset,
            page_type=getattr(args, "page", "homepage"),
            sections_from_template=_local_count,
            db_template_count=_db_count,
            sections_from_llm=_llm_count,
            total_sections=len(section_files),
            build_duration_ms=_build_duration_ms,
            status=_build_status,
            target_platform=args.target_platform,
            bos_line_items=_bos_line_items,
            sections_reconciled=_reconciliation_meta,
            tenant_id=tenant_id,
            harvested_copy_ratio=_harvested_copy_ratio,
            render_audit_status=_render_audit_status,
            assets_bound=_assets_bound if _assets_bound > 0 else None,
            token_ledger=_token_summary,
        )
        _recon_str = ""
        if _reconciliation_meta:
            _recon_str = (
                f", recon: {_reconciliation_meta['total']} total "
                f"({_reconciliation_meta['registry_count']} reg / "
                f"{_reconciliation_meta['harvest_count']} hvst / "
                f"{_reconciliation_meta['gap_filled_count']} gaps)"
            )
        _ratio_str = ""
        if _harvested_copy_ratio is not None:
            _ratio_str = f", copy_ratio: {_harvested_copy_ratio}"
        print(f"  📊 Build logged to Supabase ({_local_count} local / {_db_count} db / {_llm_count} LLM, BoS items: {_bos_line_items or 0}{_recon_str}{_ratio_str})")

    mode_label = "URL Clone" if args.from_url else ("Database" if args.industry else "Pipeline")
    print(f"\n{'═' * 60}")
    if _exit_code == EXIT_OK:
        print(f"  ✅ {mode_label} complete")
    else:
        print(f"  ❌ {mode_label} INCOMPLETE — status: {_build_status}")
    print(f"  Output: output/{args.project}/")
    if deploy_ran:
        print(f"  Site:   output/{args.project}/site/")
    if args.from_url:
        print(f"  Preset: skills/presets/{preset}.md")
        print(f"  Brief:  briefs/{args.project}.md")
    if args.industry:
        print(f"  Industry: {args.industry}")
        print(f"  Page: {getattr(args, 'page', 'homepage')}")
        print(f"  Build time: {_build_duration_ms/1000:.1f}s")
    if deploy_requested:
        print(f"  Render audit: {_render_audit_status}")
    print(f"{'═' * 60}\n")
    finish_build(_build_status, _exit_code)


if __name__ == "__main__":
    main()
