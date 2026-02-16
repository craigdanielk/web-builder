"""
Aurelix Supabase Client
─────────────────────────────────────────────────────────
Lightweight REST-only client for the aurelix-presets database.
Uses httpx/urllib — no external supabase SDK dependency needed at runtime.

CACHING RULE: get_section_sequence() and get_industry_style() are called
ONCE at build start and cached for the entire build. Only log_build()
writes to Supabase (once, at build end). A typical build: 2 reads + 1 write.
"""

import json
import os
import re
import ssl
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


def check_template_exists(archetype: str, variant: str) -> Path | None:
    """
    Check if a parameterized TSX template exists for this archetype+variant.
    Returns the template Path if found, None otherwise.
    """
    template_dir = _ROOT / "section-templates" / archetype
    template_file = template_dir / f"{variant}.tsx"
    if template_file.exists():
        return template_file
    return None


def log_build(
    project_name: str,
    industry: str,
    page_type: str,
    sections_from_template: int = 0,
    sections_from_llm: int = 0,
    total_sections: int = 0,
    build_duration_ms: int | None = None,
    api_cost_usd: float | None = None,
    status: str = "completed",
) -> bool:
    """
    Write a build log entry to the build_log table.
    Returns True on success, False on failure.
    """
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

    try:
        _post("build_log", [row])
        return True
    except Exception as e:
        print(f"  ⚠ Failed to write build log: {e}")
        return False


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
