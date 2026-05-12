import json
import os
import ssl
import urllib.request
from pathlib import Path
from typing import Any

try:
    from lib.virtual_db import get_virtual_section_sequence, get_virtual_industry_style
except ImportError:
    def get_virtual_section_sequence(i, p): return []
    def get_virtual_industry_style(i): return None

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_KEY", "")
)
_SSL_CTX = ssl.create_default_context()
_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

def _get(path, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if params: url += f"?{params}"
    req = urllib.request.Request(url, headers=_HEADERS, method="GET")
    try:
        resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except: return []

def _post(path, data):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), method="POST", headers=_HEADERS)
    try:
        resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
        return resp.status
    except: return 500

def _rpc(fn_name, params):
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    req = urllib.request.Request(url, data=json.dumps(params).encode("utf-8"), method="POST", headers=_HEADERS)
    try:
        resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=15)
        return json.loads(resp.read().decode("utf-8"))
    except: return []

def _parse_page_section_rows(rows: list) -> list[dict]:
    if not rows:
        return []
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


def get_section_sequence_sources(industry: str, page_type: str = "homepage") -> tuple[list[dict], list[dict]]:
    """Return (sections_from_supabase_rpc, sections_from_virtual_csv) without merging."""
    raw = _rpc("get_page_sections", {"p_industry": industry, "p_page_type": page_type})
    rpc_parsed = _parse_page_section_rows(raw) if raw else []
    virtual = get_virtual_section_sequence(industry, page_type)
    return rpc_parsed, virtual


def get_section_sequence(industry, page_type="homepage"):
    rpc_parsed, virtual = get_section_sequence_sources(industry, page_type)
    if rpc_parsed:
        return rpc_parsed
    return virtual

def get_industry_style(industry):
    rows = _get("industry_styles", f"industry=eq.{industry}&select=*")
    if not rows: return get_virtual_industry_style(industry)
    return rows[0]

def get_industry_metadata(industry):
    rows = _get("industries", f"handle=eq.{industry}&select=*")
    if not rows: return {"handle": industry, "display_name": industry.replace("-", " ").title(), "default_nav_variant": "sticky-transparent", "default_footer_variant": "mega"}
    return rows[0]

def check_template_exists(archetype, variant, cache=None):
    template_dir = Path("/Users/craigkunte/Developer/GitHub/Personal/Aurelix_AG/web-builder/section-templates") / archetype
    template_file = template_dir / f"{variant}.tsx"
    return template_file if template_file.exists() else None

def log_build(project_name, industry, page_type, status="completed", **kwargs):
    row = {"project_name": project_name, "industry": industry, "page_type": page_type, "status": status}
    row.update(kwargs)
    return _post("build_log", [row]) == 201

class BuildCache:
    def __init__(self, industry, page_type="homepage"):
        self.industry = industry
        self.page_type = page_type
        self.section_sequence = []
        self.industry_style = None
        self._loaded = False
        self.template_cache = {}

    def load(self):
        if self._loaded: return self
        self.section_sequence = get_section_sequence(self.industry, self.page_type)
        self.industry_style = get_industry_style(self.industry)
        self._loaded = True
        return self

    @property
    def style_config(self):
        if self.industry_style and self.industry_style.get("style_config"):
            return self.industry_style["style_config"]
        return {}

    @property
    def compact_style_header(self):
        if self.industry_style and self.industry_style.get("compact_style_header"):
            return self.industry_style["compact_style_header"]
        return "[Style not found]"

def is_supabase_configured() -> bool:
    url = (SUPABASE_URL or "").strip()
    key = (SUPABASE_KEY or "").strip()
    return bool(url and key)
