"""
Tenant Context Reader
─────────────────────────────────────────────────────────
Read-only loader for *tenant capture by coordinate* from the canonical
Supabase (the same project as the preset registry / build_log).

Given a tenant coordinate (a tenant_id UUID **or** a tenant slug) it loads:
  - phase0_field_values  — brand/domain/etc. key/value capture rows
  - creative_assets       — tenant media (logos, imagery, campaign assets)
  - competitor_profiles   — benchmark / competitor data

COMPLIANCE
──────────
Phase 0 also captures the tenant's regulatory position — `required_disclaimers`,
`prohibited_terms`, `licenses`, `regulatory_body`. Those rows are declarations
about a licensed entity, so they get a typed surface of their own rather than
being fished out of the raw key/value map at each call site:
``compliance_declaration`` / ``required_disclaimers`` /
``assert_no_prohibited_terms``, and a normalised ``compliance`` key on the
loaded context. Declared text is carried verbatim and is never paraphrased,
generated, or inferred from `jurisdiction`.

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

import json
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


# ─── Compliance declaration ───────────────────────────────────────
# Phase 0 collects the tenant's regulatory position as data:
#
#   required_disclaimers  text that MUST appear on the site, verbatim
#   prohibited_terms      phrases that must NOT appear, verbatim
#   prohibited_language   *categories* of phrasing to avoid, in prose
#   licenses / regulatory_body   who authorises the tenant and under what number
#
# These are declarations, never inferences. Nothing here derives a disclaimer
# from `jurisdiction`, or a prohibited term from `brand_voice`: for a licensed
# FSP an approximated disclosure is a regulatory liability, and a fabricated one
# is worse than none. A tenant that declares nothing gets nothing.
#
# `prohibited_language` is deliberately NOT enforced mechanically. Its entries
# ("financial advice framing", "urgency/FOMO pressure tactics") name a rhetorical
# posture, not a string; matching them literally would flag nothing real and
# missing them silently would suggest a check that is not happening. It is
# surfaced for human/LLM copy review and excluded from `scan_prohibited_terms`.


class ComplianceNotDeclared(RuntimeError):
    """A build that must carry declared regulatory text has none to carry."""


class ProhibitedTermFound(RuntimeError):
    """Generated copy contains a phrase the tenant declared prohibited."""


#: Cues that flip a prohibited phrase from a claim into its own denial. The FSP
#: disclaimer itself reads "does not constitute advice, inducement or
#: recommendation to invest" — the literal presence of a banned phrase inside a
#: negation is the tenant SATISFYING the rule, not breaking it. Matched over the
#: 60 characters preceding the hit.
_NEGATION_RE = re.compile(
    r"\b(?:not|never|no|nothing|none|nor|without|neither|excludes?|"
    r"doesn'?t|don'?t|isn'?t|aren'?t|cannot|can'?t)\b",
    re.I,
)
_NEGATION_WINDOW = 60


def _str_list(value: Any) -> list[str]:
    """Normalise a phase-0 value to a list of non-empty strings.

    jsonb round-trips arrive as a real list; a hand-entered value can arrive as
    a JSON-encoded string or as a single bare string. All three are the same
    declaration and all three are accepted. Anything else yields [] — a shape
    this function does not understand is not silently coerced into copy.
    """
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text[0] in "[{":
            try:
                value = json.loads(text)
            except (ValueError, TypeError):
                return [text]
        else:
            return [text]
    if isinstance(value, list):
        return [v.strip() for v in value if isinstance(v, str) and v.strip()]
    return []


def compliance_declaration(tenant_context: dict | None) -> dict[str, Any]:
    """The tenant's declared regulatory position, normalised.

    Always returns the full shape so callers never branch on key presence; the
    lists are empty when the tenant declares nothing, and `declared` is False.
    """
    values = (tenant_context or {}).get("phase0_field_values") or {}
    regulator = values.get("regulatory_body")
    out = {
        "required_disclaimers": _str_list(values.get("required_disclaimers")),
        "prohibited_terms": _str_list(values.get("prohibited_terms")),
        "prohibited_language": _str_list(values.get("prohibited_language")),
        "licenses": _str_list(values.get("licenses")),
        "regulatory_body": regulator.strip() if isinstance(regulator, str) else "",
    }
    out["regulated"] = bool(out["licenses"] or out["regulatory_body"])
    out["declared"] = bool(
        out["required_disclaimers"] or out["prohibited_terms"] or out["regulated"]
    )
    return out


def required_disclaimers(
    tenant_context: dict | None, *, require: bool = False
) -> list[str]:
    """Verbatim disclosure text the site MUST carry, straight from phase 0.

    `require=True` refuses instead of returning an empty list — the mode for a
    build that already knows the tenant is regulated. The default is permissive
    because registry/demo builds legitimately have no tenant at all.
    """
    decl = compliance_declaration(tenant_context)
    disclaimers = decl["required_disclaimers"]
    if disclaimers or not require:
        return disclaimers

    if not tenant_context:
        raise ComplianceNotDeclared(
            "no tenant context, so no required_disclaimers to read — "
            "pass --tenant <slug>. A regulated site cannot ship with a footer "
            "whose disclosures were never loaded."
        )
    slug = tenant_context.get("slug") or tenant_context.get("coordinate") or "<unknown tenant>"
    raise ComplianceNotDeclared(
        f"tenant '{slug}' declares no required_disclaimers"
        + (f" despite being authorised by {decl['regulatory_body']}" if decl["regulatory_body"] else "")
        + ". Collect the exact disclosure text at phase 0; it is never "
        "paraphrased, generated or inferred from jurisdiction."
    )


def prohibited_terms(tenant_context: dict | None) -> list[str]:
    """Phrases the tenant's copy must not contain."""
    return compliance_declaration(tenant_context)["prohibited_terms"]


def _term_pattern(term: str) -> re.Pattern:
    """Word-bounded, case-insensitive, whitespace-flexible match for `term`.

    Word boundaries stop "risk-free" matching inside "risk-free-form"; flexible
    whitespace lets a phrase match across the line wrap JSX puts in the middle
    of it.
    """
    parts = [re.escape(w) for w in term.split()]
    return re.compile(r"\b" + r"[\s ]+".join(parts) + r"\b", re.I)


def scan_prohibited_terms(
    text: str,
    terms: list[str],
    *,
    exempt: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Every occurrence of a prohibited term in `text`.

    Each hit is ``{term, match, start, excerpt, negated}``. `negated` marks a
    hit whose preceding 60 characters carry a negation cue — the shape the FSP
    disclaimer takes ("does not constitute ... recommendation to invest"). It is
    reported rather than dropped so the caller can see what was let through, and
    `assert_no_prohibited_terms` treats only non-negated hits as violations.

    `exempt` — verbatim strings that are themselves declared compliant copy
    (the disclaimers). Their spans are removed before scanning, so a tenant's
    own disclosure can never trip its own ban list.
    """
    if not text or not terms:
        return []

    scanned = text
    for phrase in exempt or []:
        # Blank the exempt span rather than delete it, so offsets stay true.
        scanned = scanned.replace(phrase, " " * len(phrase))

    hits: list[dict[str, Any]] = []
    for term in terms:
        for m in _term_pattern(term).finditer(scanned):
            before = scanned[max(0, m.start() - _NEGATION_WINDOW):m.start()]
            hits.append({
                "term": term,
                "match": text[m.start():m.end()],
                "start": m.start(),
                "excerpt": " ".join(
                    text[max(0, m.start() - 50):m.end() + 50].split()
                ),
                "negated": bool(_NEGATION_RE.search(before)),
            })
    hits.sort(key=lambda h: h["start"])
    return hits


def assert_no_prohibited_terms(
    sources: dict[str, str],
    tenant_context: dict | None,
) -> list[dict[str, Any]]:
    """Fail the build if any source carries a prohibited term.

    `sources` maps an origin label (a file path, a section uid, a slot name) to
    the text to scan, so the error names WHERE the phrase is rather than only
    that it exists. Returns the negated hits it deliberately allowed, so a
    caller can log what the negation rule let through instead of it being
    invisible.

    Raises `ProhibitedTermFound` on the first build that would ship banned copy.
    A tenant with no declared terms is a no-op.
    """
    decl = compliance_declaration(tenant_context)
    terms = decl["prohibited_terms"]
    if not terms:
        return []
    exempt = decl["required_disclaimers"]

    violations: list[str] = []
    allowed: list[dict[str, Any]] = []
    for origin, text in sources.items():
        for hit in scan_prohibited_terms(text, terms, exempt=exempt):
            hit = {**hit, "origin": origin}
            if hit["negated"]:
                allowed.append(hit)
            else:
                violations.append(
                    f"  {origin}: {hit['term']!r} — …{hit['excerpt']}…"
                )

    if violations:
        slug = (tenant_context or {}).get("slug") or "<unknown tenant>"
        raise ProhibitedTermFound(
            f"tenant '{slug}' declares {len(terms)} prohibited term(s) and the "
            f"build produced {len(violations)} occurrence(s):\n"
            + "\n".join(violations)
            + "\n\nThese are declared regulatory constraints, not style "
            "preferences. Remove the phrasing at source (the harvest or the "
            "template) — the ban list is not the thing to edit."
        )
    return allowed


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
        compliance           : normalised regulatory declaration — see
                               ``compliance_declaration``
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
        "compliance": compliance_declaration(None),
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
    ctx["compliance"] = compliance_declaration(ctx)
    ctx["available"] = bool(
        phase0 or ctx["creative_assets"] or ctx["competitor_profiles"]
    )
    return ctx
