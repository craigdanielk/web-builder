"""
Aurelix Supabase Client
─────────────────────────────────────────────────────────
Lightweight REST-only client for the aurelix-presets database.
Uses httpx/urllib — no external supabase SDK dependency needed at runtime.

CACHING RULE: get_section_sequence() and get_industry_style() are called
ONCE at build start and cached for the entire build. Only log_build()
writes to Supabase (once, at build end). A typical build: 2 reads + 1 write.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


# ─── Configuration ────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent.parent  # web-builder/

def _load_env():
    """Load .env if vars not already present."""
    env_path = _ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

_load_env()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
_SSL_CTX = ssl.create_default_context()

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


# ─── Low-level HTTP ───────────────────────────────────────────────

def _get(path: str, params: str = "") -> list[dict]:
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if params:
        url += f"?{params}"
    req = urllib.request.Request(url, headers=_HEADERS, method="GET")
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
    return json.loads(resp.read().decode("utf-8"))


def _post(path: str, data: Any) -> Any:
    """POST to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    body = json.dumps(data).encode("utf-8")
    headers = dict(_HEADERS)
    headers["Prefer"] = "return=minimal"
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
    return resp.status


def _post_returning(path: str, data: Any) -> tuple[int, list[dict]]:
    """
    POST to Supabase REST API asking for the inserted row(s) back.

    Unlike _post(), this surfaces the response body so a caller can report the
    row it actually created. HTTPError bodies are NOT swallowed here — the
    PostgREST error payload (e.g. PGRST204 "column ... does not exist") is the
    only thing that names the real cause, and urllib's str(HTTPError) reduces it
    to "HTTP Error 400: Bad Request". That reduction is why an unknown-column
    insert failed unnoticed on every build.
    """
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    body = json.dumps(data).encode("utf-8")
    headers = dict(_HEADERS)
    headers["Prefer"] = "return=representation"
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
    raw = resp.read().decode("utf-8")
    return resp.status, (json.loads(raw) if raw.strip() else [])


def _http_error_detail(exc: Exception) -> str:
    """Render an exception, unwrapping a PostgREST HTTPError body when present."""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            payload = exc.read().decode("utf-8")
        except Exception:
            payload = ""
        return f"HTTP {exc.code} {exc.reason}: {payload or '<empty body>'}"
    return f"{type(exc).__name__}: {exc}"


def _delete(path: str, filters: str) -> int:
    """DELETE from Supabase REST API. Used by tests to clean up rows they wrote."""
    url = f"{SUPABASE_URL}/rest/v1/{path}?{filters}"
    req = urllib.request.Request(url, method="DELETE", headers=_HEADERS)
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
    return resp.status


def table_columns(table: str) -> list[str]:
    """
    The live column list for `table`, read from PostgREST's OpenAPI document.

    This is the schema itself, not a guess. Tests use it to assert that the
    build_log payload contains only columns that exist, so the assertion keeps
    working when the schema changes. Raises on any transport or parse failure —
    an unreachable database must read as NOT_MEASURED at the call site, never as
    an empty column list (which would make every payload look wrong).
    """
    url = f"{SUPABASE_URL}/rest/v1/"
    req = urllib.request.Request(url, headers=_HEADERS, method="GET")
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=20)
    spec = json.loads(resp.read().decode("utf-8"))
    return list(spec["definitions"][table]["properties"].keys())


def _patch(path: str, filters: str, data: Any) -> Any:
    """PATCH to Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}?{filters}"
    body = json.dumps(data).encode("utf-8")
    headers = dict(_HEADERS)
    headers["Prefer"] = "return=minimal"
    req = urllib.request.Request(url, data=body, method="PATCH", headers=headers)
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
    return resp.status


def _rpc(fn_name: str, params: dict) -> list[dict]:
    """Call Supabase RPC function."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    body = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers=_HEADERS)
    resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
    return json.loads(resp.read().decode("utf-8"))


# ─── Query Functions ──────────────────────────────────────────────

def get_section_sequence(industry: str, page_type: str = "homepage") -> list[dict]:
    """
    Fetch the ordered section sequence for an industry + page type.
    Uses the get_page_sections() database function.

    Returns list of dicts:
        [{"position": 1, "archetype": "HERO", "variant": "full-bleed-overlay",
          "content_direction": "...", "priority": "required"}, ...]
    """
    rows = _rpc("get_page_sections", {
        "p_industry": industry,
        "p_page_type": page_type,
    })

    # Map the out_ prefixed columns back to clean names
    return [
        {
            "position": r.get("out_position", 0),
            "archetype": r.get("out_section_archetype", ""),
            "variant": r.get("out_section_variant", ""),
            "content_direction": r.get("out_content_direction", ""),
            "priority": r.get("out_priority", "required"),
        }
        for r in rows
    ]


def get_industry_style(industry: str) -> dict | None:
    """
    Fetch the full industry style config from industry_styles.
    Returns the style_config JSONB as a Python dict, or None if not found.
    """
    rows = _get("industry_styles", f"industry=eq.{industry}&select=*")
    if not rows:
        return None
    return rows[0]


def get_industry_metadata(industry: str) -> dict | None:
    """
    Fetch industry row from industries table (handle, display_name, default_nav_variant, default_footer_variant).
    Used by Layer 6 site manifest to set shared Navigation and Footer variants.
    """
    rows = _get(
        "industries",
        f"handle=eq.{industry}&select=handle,display_name,default_nav_variant,default_footer_variant",
    )
    if not rows:
        return None
    return rows[0]


def get_all_page_sections(industry: str) -> dict[str, list[dict]]:
    """
    Fetch section sequences for ALL page types for an industry in one RPC call.
    Uses get_build_spec(industry). Returns dict mapping page_type to list of section dicts.
    Section dicts have: position, archetype, variant, content_direction, priority.
    """
    try:
        rows = _rpc("get_build_spec", {"p_industry": industry})
    except Exception:
        return {}

    by_page: dict[str, list[dict]] = {}
    for r in rows:
        page_type = r.get("out_page_type") or "homepage"
        if page_type not in by_page:
            by_page[page_type] = []
        by_page[page_type].append({
            "position": r.get("out_position", 0),
            "archetype": r.get("out_section_archetype", ""),
            "variant": r.get("out_section_variant", ""),
            "content_direction": r.get("out_content_direction", ""),
            "priority": r.get("out_priority", "required"),
        })

    # Sort each page's sections by position
    for pt in by_page:
        by_page[pt].sort(key=lambda s: s["position"])
    return by_page


def check_template_exists(
    archetype: str,
    variant: str,
    cache: BuildCache | None = None,
) -> Path | str | None:
    """
    Check if a parameterized TSX template exists for this archetype+variant.
    Resolution order: (1) cache, (2) local file, (3) Supabase code_template.
    Returns Path (local file), str (code from Supabase), or None (LLM fallback).

    Alongside the resolved template, the Supabase branch also fetches the
    template's ``slot_schema`` (the JSON contract describing the template's
    fillable slots) and makes it available via ``cache.slot_schema_cache``,
    keyed by ``(archetype, variant)``. Callers can read the slot schema for a
    resolved template with ``get_slot_schema(archetype, variant, cache)``.
    Local-file and LLM-fallback resolutions have no slot schema (``None``).
    """
    # 1. Check per-build cache
    if cache is not None:
        key = (archetype, variant)
        if key in cache.template_cache:
            return cache.template_cache[key]

    # 2. Check local filesystem
    template_dir = _ROOT / "section-templates" / archetype
    template_file = template_dir / f"{variant}.tsx"
    if template_file.exists():
        result: Path | str | None = template_file
        if cache is not None:
            cache.template_cache[(archetype, variant)] = result
        return result

    # 3. Query Supabase section_archetypes.code_template (fault-tolerant)
    if not (SUPABASE_URL and SUPABASE_KEY):
        if cache is not None:
            cache.template_cache[(archetype, variant)] = None
        return None

    # Safe for REST query params: alphanumeric, hyphen, underscore only
    if not re.match(r"^[A-Za-z0-9_-]+$", archetype) or not re.match(r"^[A-Za-z0-9_-]+$", variant):
        if cache is not None:
            cache.template_cache[(archetype, variant)] = None
        return None

    try:
        params = "&".join([
            f"archetype=eq.{urllib.parse.quote(archetype)}",
            f"variant=eq.{urllib.parse.quote(variant)}",
            "has_template=eq.true",
            "select=code_template,slot_schema",
        ])
        rows = _get("section_archetypes", params)
        if rows and len(rows) > 0:
            code = rows[0].get("code_template")
            if isinstance(code, str) and code.strip():
                if cache is not None:
                    cache.template_cache[(archetype, variant)] = code
                    # Surface the slot_schema alongside the code_template so
                    # callers can resolve the template's fillable-slot contract
                    # from the same lookup (None if the column is absent/empty).
                    cache.slot_schema_cache[(archetype, variant)] = rows[0].get("slot_schema")
                return code
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, KeyError):
        pass  # Fall through to LLM

    if cache is not None:
        cache.template_cache[(archetype, variant)] = None
    return None


def get_slot_schema(
    archetype: str,
    variant: str,
    cache: BuildCache | None = None,
) -> Any | None:
    """
    Return the slot_schema resolved alongside code_template by
    check_template_exists() for this archetype+variant.

    check_template_exists() must have been called first (it populates
    cache.slot_schema_cache). Returns None when no cache is provided, the
    template was not Supabase-resolved, or the row had no slot_schema.
    """
    if cache is None:
        return None
    return cache.slot_schema_cache.get((archetype, variant))


# ─── build_log schema ─────────────────────────────────────────────

# The columns build_log actually has, read from PostgREST's OpenAPI document on
# 2026-08-18 (28 columns; `id` and `build_timestamp` are database-assigned and
# are therefore never sent). Re-measure with table_columns("build_log").
#
# This is a declared allowlist, not a retry heuristic. The previous code sent
# two columns that do not exist (`db_template_count`, `token_ledger`), got a 400
# PGRST204, and retried having stripped only one of them — so the retry 400'd
# identically and every build recorded nothing while exiting 0. Guessing one
# name at a time cannot converge; filtering against the schema can.
_BUILD_LOG_COLUMNS = frozenset({
    "project_name", "industry", "page_type", "build_duration_ms", "api_cost_usd",
    "sections_from_template", "sections_from_llm", "total_sections",
    "was_customized", "status", "target_platform", "tenant_id", "brand_ci_ref",
    "sections_reconciled", "asset_count", "bos_line_items", "benchmark_grade",
    "page_count", "assets_bound", "app_routes_scaffolded", "deploy_url",
    "contrast_defect_count", "broken_image_count", "harvested_copy_ratio",
    "render_audit_status", "published_sha",
})

# Last log_build() failure, as a human-readable string; None after a success.
# Exposed so a caller that wants to surface "this build recorded nothing" can,
# without log_build() needing to raise.
LAST_BUILD_LOG_ERROR: str | None = None


def log_build(
    project_name: str,
    industry: str,
    page_type: str,
    sections_from_template: int = 0,
    db_template_count: int = 0,
    sections_from_llm: int = 0,
    total_sections: int = 0,
    build_duration_ms: int | None = None,
    api_cost_usd: float | None = None,
    status: str = "completed",
    target_platform: str | None = None,
    bos_line_items: int | None = None,
    sections_reconciled: dict | None = None,
    tenant_id: str | None = None,
    page_count: int | None = None,
    assets_bound: int | None = None,
    app_routes_scaffolded: int | None = None,
    deploy_url: str | None = None,
    harvested_copy_ratio: float | None = None,
    render_audit_status: str | None = None,
    contrast_defect_count: int | None = None,
    broken_image_count: int | None = None,
    published_sha: str | None = None,
    token_ledger: dict | None = None,
) -> bool:
    """
    Write a build log entry to the build_log table.

    TWO PARAMETERS ARE ACCEPTED AND DELIBERATELY NOT PERSISTED, because
    build_log has no column for either and this code may not add one to a shared
    database:

      * db_template_count (Supabase code_template count) — there is no column
        for it and no honest home for it. sections_from_template means something
        else (local .tsx count), and sections_reconciled is a typed jsonb record
        of section reconciliation, not a metadata bag; smuggling an unrelated
        integer into it would make that column mean two things. Dropped. The
        figure is a build-time diagnostic, recoverable from the build console
        and from output/<project>/ artifacts.
      * token_ledger (LLM token totals, see orchestrate.token_ledger_summary) —
        likewise no column. It is already persisted in full to
        output/<project>/token-ledger.json, which is the record of record.
        Dropped here rather than costing the whole row.

    If either is ever given a real column, add its name to _BUILD_LOG_COLUMNS
    and pass it through; nothing else needs to change.

    sections_from_template = local .tsx file count.
    target_platform records the deploy adapter used ('shopify' or 'vercel').
    bos_line_items records the number of Bill of Sale line items addressed in this build.
    tenant_id records the tenant coordinate (UUID) when the build was driven by a
    tenant capture; omitted entirely when absent so non-tenant builds are unchanged.
    page_count records the number of pages built (multipage builds); omitted when
    absent so single-page builds are unchanged and rely on the column default.
    assets_bound records how many sections were bound to a tenant creative_asset
    (self-hosted path injected); omitted when no tenant assets were present so
    registry/file builds are unchanged (no regression).
    app_routes_scaffolded records how many protected app-route seams were stubbed
    onto the unified app shell; omitted when no seams were requested.
    deploy_url records the deployed site URL when a composed end-to-end tenant
    build deploys; omitted for build-only runs.
    harvested_copy_ratio records the ratio of verbatim harvested strings to total
    copy slots for the build, providing a copy-fidelity metric (0.0 = all generated,
    1.0+ = harvested exceeds slots). Omitted when no harvest data is available so
    registry/file builds are unchanged (no regression).
    render_audit_status records the post-build render audit outcome ('passed',
    'review_needed', 'failed', 'skipped') from stage_render_audit. Omitted
    when no audit ran so pre-existing builds are unchanged (no regression).
    Returns True on success, False on failure. A failure prints a loud,
    distinctive line carrying the PostgREST error body and records it in
    LAST_BUILD_LOG_ERROR. It deliberately does NOT raise: recording a build is
    not the build's purpose, and a logging outage must not fail a good build.
    Returning False silently is what let this defect live for days, so the
    failure is now unmissable in the console and inspectable in-process.
    """
    global LAST_BUILD_LOG_ERROR

    row = {
        "project_name": project_name,
        "industry": industry,
        "page_type": page_type,
        "sections_from_template": sections_from_template,
        "sections_from_llm": sections_from_llm,
        "total_sections": total_sections,
        "status": status,
    }
    if build_duration_ms is not None:
        row["build_duration_ms"] = build_duration_ms
    if api_cost_usd is not None:
        row["api_cost_usd"] = api_cost_usd
    if target_platform is not None:
        row["target_platform"] = target_platform
    if bos_line_items is not None:
        row["bos_line_items"] = bos_line_items
    if sections_reconciled is not None:
        row["sections_reconciled"] = sections_reconciled
    if tenant_id is not None:
        row["tenant_id"] = tenant_id
    if page_count is not None:
        row["page_count"] = page_count
    if assets_bound is not None:
        row["assets_bound"] = assets_bound
    if app_routes_scaffolded is not None:
        row["app_routes_scaffolded"] = app_routes_scaffolded
    if deploy_url is not None:
        row["deploy_url"] = deploy_url
    if harvested_copy_ratio is not None:
        row["harvested_copy_ratio"] = harvested_copy_ratio
    if render_audit_status is not None:
        row["render_audit_status"] = render_audit_status
    if contrast_defect_count is not None:
        row["contrast_defect_count"] = contrast_defect_count
    if broken_image_count is not None:
        row["broken_image_count"] = broken_image_count
    if published_sha is not None:
        row["published_sha"] = published_sha

    # Safety net for schema drift. The two known orphans are handled above by
    # never entering the row, so this should never fire; if it does, something
    # newly added here has no column and saying so beats a 400 nobody reads.
    unknown = sorted(k for k in row if k not in _BUILD_LOG_COLUMNS)
    if unknown:
        print(
            "  ⚠ BUILD LOG: dropping field(s) with no build_log column: "
            + ", ".join(unknown)
            + " — add them to _BUILD_LOG_COLUMNS if the column now exists"
        )
        for k in unknown:
            row.pop(k)

    try:
        status, created = _post_returning("build_log", [row])
    except Exception as e:
        LAST_BUILD_LOG_ERROR = _http_error_detail(e)
        print("  ✗ BUILD LOG WRITE FAILED — this build recorded nothing.")
        print(f"    {LAST_BUILD_LOG_ERROR}")
        print(f"    payload keys: {sorted(row)}")
        return False

    LAST_BUILD_LOG_ERROR = None
    row_id = created[0].get("id") if created else None
    print(f"  ✓ build_log row written (HTTP {status}, id={row_id})")
    return True


# ─── Build Cache ──────────────────────────────────────────────────

class BuildCache:
    """
    Per-build cache for Supabase reads.

    Usage:
        cache = BuildCache(industry="artisan-food", page_type="homepage")
        cache.load()  # Makes exactly 2 Supabase reads
        sections = cache.section_sequence  # List of dicts
        style = cache.industry_style       # Dict with style_config etc.
    """

    def __init__(self, industry: str, page_type: str = "homepage"):
        self.industry = industry
        self.page_type = page_type
        self.section_sequence: list[dict] = []
        self.industry_style: dict | None = None
        self._loaded = False
        self.template_cache: dict[tuple[str, str], Path | str | None] = {}
        # Slot-schema contract for each Supabase-resolved template, populated by
        # check_template_exists() alongside code_template.
        self.slot_schema_cache: dict[tuple[str, str], Any | None] = {}

    def load(self) -> "BuildCache":
        """Fetch section sequence and industry style from Supabase (2 reads total)."""
        if self._loaded:
            return self

        print(f"  📡 Loading build config from Supabase...")
        print(f"     Industry: {self.industry} | Page: {self.page_type}")

        try:
            self.section_sequence = get_section_sequence(self.industry, self.page_type)
            print(f"     ✓ Section sequence: {len(self.section_sequence)} sections")
        except Exception as e:
            print(f"     ⚠ Failed to fetch section sequence: {e}")
            self.section_sequence = []

        try:
            self.industry_style = get_industry_style(self.industry)
            if self.industry_style and self.industry_style.get("style_config"):
                print(f"     ✓ Industry style loaded")
            else:
                print(f"     ⚠ No style_config for industry '{self.industry}'")
        except Exception as e:
            print(f"     ⚠ Failed to fetch industry style: {e}")
            self.industry_style = None

        self._loaded = True
        return self

    @property
    def style_config(self) -> dict:
        """Get the JSONB style config as a dict (empty dict if missing)."""
        if self.industry_style and self.industry_style.get("style_config"):
            return self.industry_style["style_config"]
        return {}

    @property
    def compact_style_header(self) -> str:
        """Get the compact style header string for prompt injection."""
        if self.industry_style and self.industry_style.get("compact_style_header"):
            return self.industry_style["compact_style_header"]
        return "[Style header not available from database]"

    @property
    def content_direction(self) -> dict:
        """Get the content direction metadata."""
        if self.industry_style and self.industry_style.get("content_direction"):
            return self.industry_style["content_direction"]
        return {}

    def get_preset_sequence_text(self) -> str:
        """
        Format the section sequence as text matching the preset format:
        1. ARCHETYPE | variant | content direction
        """
        lines = []
        for sec in self.section_sequence:
            pos = sec["position"]
            arch = sec["archetype"]
            var = sec["variant"]
            cd = sec.get("content_direction", "")
            lines.append(f"{pos}. {arch} | {var} | {cd}")
        return "\n".join(lines) if lines else "No sections defined for this industry/page combo"

    def build_synthetic_preset_content(self) -> str:
        """
        Build a synthetic preset content string that mimics the .md preset format.
        This allows existing functions like detect_animation_engine(), parse_fonts(),
        and extract_style_header() to work unchanged.
        """
        config = self.style_config
        if not config:
            return ""

        lines = ["## Style Configuration\n\n```yaml"]

        # Reconstruct YAML-ish blocks from the config dict
        for key, val in config.items():
            if isinstance(val, dict):
                lines.append(f"{key}:")
                for k2, v2 in val.items():
                    lines.append(f"  {k2}: {v2}")
            else:
                lines.append(f"{key}: {val}")

        lines.append("```\n")

        # Add compact style header if available
        header = self.compact_style_header
        if header and not header.startswith("["):
            lines.append(header)

        # Add section sequence
        lines.append("\n## Default Section Sequence\n\n```")
        lines.append(self.get_preset_sequence_text())
        lines.append("```\n")

        return "\n".join(lines)


def is_supabase_configured() -> bool:
    """Check if Supabase credentials are configured."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def list_variants_for_archetype(archetype: str) -> list[str]:
    """Every variant the registry holds for one archetype, template-backed only.

    `check_template_exists` answers "does THIS archetype+variant resolve"; this
    answers "what does the library actually have for this archetype". The
    difference matters on the failure path: a request for
    `BLOG-PREVIEW/card-grid` falls through to the LLM while
    `BLOG-PREVIEW/grid` sits unused, and without this the omission record can
    say only that something was missing, not that a near neighbour existed.

    Filters on `has_template=eq.true` so a row with no `code_template` is never
    reported as available — the same condition `check_template_exists` requires
    to resolve, so the two cannot disagree about what is usable.

    Returns [] on any failure. This is diagnostic output on an error path;
    it must never be the thing that raises.
    """
    if not (SUPABASE_URL and SUPABASE_KEY):
        return []
    if not re.match(r"^[A-Za-z0-9_-]+$", archetype or ""):
        return []
    try:
        params = "&".join([
            f"archetype=eq.{urllib.parse.quote(archetype)}",
            "has_template=eq.true",
            "select=variant",
        ])
        rows = _get("section_archetypes", params) or []
        return sorted({r["variant"] for r in rows if r.get("variant")})
    except Exception:
        return []
