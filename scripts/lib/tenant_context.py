"""
Tenant Context Reader
─────────────────────────────────────────────────────────
Read-only loader for *tenant capture by coordinate* from the canonical
Supabase (the same project as the preset registry / build_log).

Given a tenant coordinate (a tenant_id UUID **or** a tenant slug) it loads:
  - phase0_field_values  — brand/domain/etc. key/value capture rows
  - creative_assets       — tenant media (logos, imagery, campaign assets)
  - competitor_profiles   — benchmark / competitor data

IDEMPOTENT / PURE NODE
──────────────────────
This module performs *only* REST GET reads against Supabase. It has no side
effects, writes nothing, and returns the same structure whether called once
or a thousand times with the same coordinate. Every fetch is fault-tolerant:
a missing table, missing row, absent credentials, or any transport error
degrades gracefully to an empty structure — so registry/file builds that do
NOT pass a tenant coordinate are completely unaffected.

Reuses the existing REST client primitives in ``supabase_client`` (same
SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY sourced from web-builder ``.env``).
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

# Reuse the existing Supabase REST primitives (same .env-sourced credentials).
try:  # pragma: no cover - import shape depends on how the package is loaded
    from .supabase_client import _get, SUPABASE_URL, SUPABASE_KEY
except ImportError:  # fallback when imported as a top-level module
    from supabase_client import _get, SUPABASE_URL, SUPABASE_KEY  # type: ignore


_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


# ─── Fault-tolerant read ──────────────────────────────────────────

def _safe_get(path: str, params: str = "") -> list[dict]:
    """GET wrapper that never raises — returns [] on any error / missing config."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        return []
    try:
        rows = _get(path, params)
        return rows if isinstance(rows, list) else []
    except Exception:
        # Missing table (404/PGRST), transport error, bad JSON — degrade to empty.
        return []


def _unwrap(value: Any) -> Any:
    """
    phase0_field_values.value is jsonb; simple scalars are stored wrapped as
    ``{"v": <value>}``. Unwrap that shape; pass structured objects through.
    """
    if isinstance(value, dict) and set(value.keys()) == {"v"}:
        return value["v"]
    return value


# ─── Coordinate resolution ────────────────────────────────────────

def resolve_tenant(coordinate: str) -> tuple[str | None, str | None]:
    """
    Resolve a coordinate (UUID or slug) to ``(tenant_id, slug)``.

    - A UUID-shaped coordinate is used directly; slug is looked up best-effort.
    - Otherwise the coordinate is treated as a slug and resolved via the
      ``tenants`` table.
    Returns ``(None, coordinate)`` when the coordinate cannot be resolved.
    """
    coord = (coordinate or "").strip()
    if not coord:
        return (None, None)

    if _UUID_RE.match(coord):
        rows = _safe_get("tenants", f"id=eq.{coord}&select=id,slug")
        slug = rows[0].get("slug") if rows else None
        return (coord, slug)

    enc = urllib.parse.quote(coord, safe="")
    rows = _safe_get("tenants", f"slug=eq.{enc}&select=id,slug")
    if rows:
        return (rows[0].get("id"), rows[0].get("slug"))
    return (None, coord)


# ─── Brand / palette extraction ───────────────────────────────────

_BRAND_NAME_KEYS = ("trading_name", "entity_name", "legal_name", "company_name")


def _extract_brand(phase0: dict[str, Any]) -> dict[str, Any]:
    """Pull a compact brand descriptor out of the phase0 capture map."""
    brand: dict[str, Any] = {}
    for key in _BRAND_NAME_KEYS:
        val = phase0.get(key)
        if isinstance(val, str) and val.strip():
            brand["name"] = val.strip()
            break
    for src, dst in (("domain", "domain"), ("logo_url", "logo_url"),
                     ("brand_voice", "voice")):
        val = phase0.get(src)
        if isinstance(val, str) and val.strip():
            brand[dst] = val.strip()
    return brand


def _extract_palette(phase0: dict[str, Any]) -> dict[str, Any]:
    """
    Pull a palette dict out of phase0 ``color_palette``. Structured palettes
    (``{"primary": "#...", ...}``) pass through; a free-text palette is kept
    under ``description`` so callers can still surface it without breaking.
    """
    raw = phase0.get("color_palette")
    if isinstance(raw, dict):
        # Keep only simple scalar entries — these are what the style path uses.
        palette = {k: v for k, v in raw.items() if isinstance(v, (str, int, float))}
        return palette
    if isinstance(raw, str) and raw.strip():
        return {"description": raw.strip()}
    return {}


# ─── Public entry point ───────────────────────────────────────────

def load_tenant_context(coordinate: str) -> dict[str, Any]:
    """
    Load the full tenant context for ``coordinate`` (tenant_id UUID or slug).

    Always returns the same well-formed dict shape (idempotent / pure). When
    the coordinate is unresolvable or the tables are absent, the collections
    come back empty and ``available`` is ``False`` — a signal to callers to
    keep the current registry/file behavior unchanged.

    Returns
    -------
    dict with keys:
        coordinate           : the input coordinate
        tenant_id            : resolved UUID (or None)
        slug                 : resolved slug (or None)
        phase0_field_values  : {field_key: value} (jsonb unwrapped)
        creative_assets      : list[dict]
        competitor_profiles  : list[dict]
        brand                : {name, domain, logo_url, voice} (best-effort)
        palette              : {primary, secondary, ...} or {description}
        available            : True if any tenant capture data was found
    """
    ctx: dict[str, Any] = {
        "coordinate": coordinate,
        "tenant_id": None,
        "slug": None,
        "phase0_field_values": {},
        "creative_assets": [],
        "competitor_profiles": [],
        "brand": {},
        "palette": {},
        "available": False,
    }

    tenant_id, slug = resolve_tenant(coordinate)
    ctx["tenant_id"] = tenant_id
    ctx["slug"] = slug
    if not tenant_id:
        return ctx

    # phase0_field_values — key/value capture rows for this tenant.
    p0_rows = _safe_get(
        "phase0_field_values",
        f"tenant_id=eq.{tenant_id}&select=field_key,value,fill_status,source",
    )
    phase0: dict[str, Any] = {}
    for r in p0_rows:
        k = r.get("field_key")
        if k:
            phase0[k] = _unwrap(r.get("value"))
    ctx["phase0_field_values"] = phase0

    # creative_assets — tenant media.
    ctx["creative_assets"] = _safe_get(
        "creative_assets", f"tenant_id=eq.{tenant_id}&select=*"
    )

    # competitor_profiles — benchmark data.
    ctx["competitor_profiles"] = _safe_get(
        "competitor_profiles", f"tenant_id=eq.{tenant_id}&select=*"
    )

    ctx["brand"] = _extract_brand(phase0)
    ctx["palette"] = _extract_palette(phase0)
    ctx["available"] = bool(
        phase0 or ctx["creative_assets"] or ctx["competitor_profiles"]
    )
    return ctx
