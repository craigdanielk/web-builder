"""One industry source, with declared precedence.

Industry is declared in three places and, until this module, in no stated
order:

  1. ``phase0_field_values.industry`` — and, when that key is absent, the first
     entry of ``phase0_field_values.verticals``. This is the tenant's own
     declaration. **It wins.**
  2. ``tenants.industry`` — a real column (NULL for both live tenants as of
     2026-08-17). Second.
  3. ``aurelix-uiux-audit/lib/industry_resolver.py`` — keyword and URL-pattern
     scoring. **Fallback only, when both declarations are silent**, and its
     confidence is recorded on the result.

Disagreement between a declaration and any lower-precedence source is
*recorded*, never silently reconciled. With no source at all the function
refuses (``IndustryUndeclared``) rather than guessing.

Two things this module deliberately does not do
-----------------------------------------------
**It does not map a declared value onto a registry handle.** cape-crypto
declares ``"Crypto exchange (retail)"``; the ``industry_styles`` table has 29
handles and that is not one of them. Choosing ``fintech`` on the tenant's
behalf is invention. The declared string is returned verbatim and
``handle_in_registry`` says whether a preset lookup can use it directly
(``None`` when the registry itself could not be read).

**It does not treat an unmeasurable context as an undeclared one.**
``load_tenant_context`` never raises — ``_safe_get`` swallows every error and
returns ``[]`` — so an unreachable Supabase and a genuinely empty tenant are
indistinguishable from the returned dict alone. A context with no
``tenant_id`` and ``available`` false is NOT_MEASURED: it raises
``IndustryContextUnmeasured`` and the keyword guesser is never consulted,
because an outage must not become a confident industry.

A note on the resolver's real capability (measured 2026-08-17)
-------------------------------------------------------------
``industry_resolver.resolve_industry(captures=[{"url": u}])`` returns
``(None, 0.0)`` for *any* url when the capture carries no HTML — it early-
returns on empty text before URL scoring is reached. So there is no
url-only entry point in the audit module. For the url-only case this module
scores the URL with the resolver's **own** ``_INDUSTRY_SIGNALS`` table and
``_score_industry`` function, at the resolver's own 0.50 threshold. No second
signal table is introduced. When captures are available, pass them: the real
resolver runs unmodified.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG = logging.getLogger(__name__)

# scripts/lib/industry.py -> lib -> scripts -> web-builder -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUDIT_LIB = Path(
    os.environ.get("AURELIX_AUDIT_LIB", _REPO_ROOT / "aurelix-uiux-audit" / "lib")
)

# The resolver's own threshold (industry_resolver.resolve_industry, step 2).
_RESOLVER_MIN_CONFIDENCE = 0.50


class IndustryUndeclared(Exception):
    """No industry declared by any source, and none resolvable."""


class IndustryContextUnmeasured(IndustryUndeclared):
    """The tenant context could not be measured — not the same as empty.

    Subclasses ``IndustryUndeclared`` so callers that only care "no handle
    came back" keep working, while callers that must distinguish an outage
    from an empty tenant can.
    """


# ── the audit resolver, imported without colliding with scripts/lib ────────

_resolver_module: Any = None
_resolver_error: Optional[str] = None


def _load_resolver():
    """Import ``aurelix-uiux-audit/lib/industry_resolver.py``.

    That tree's package is also called ``lib``, which is this package's name,
    so a plain ``sys.path`` insert would shadow one with the other. Register a
    synthetic parent package instead, whose ``__path__`` points at the audit
    lib dir, so the module's ``from .registry_client import ...`` resolves.

    Returns the module, or None with the reason recorded in
    ``_resolver_error`` (a missing resolver is NOT_MEASURED, not a zero score).
    """
    global _resolver_module, _resolver_error
    if _resolver_module is not None or _resolver_error is not None:
        return _resolver_module

    path = _AUDIT_LIB / "industry_resolver.py"
    if not path.is_file():
        _resolver_error = f"industry_resolver.py not found at {path}"
        return None

    pkg_name = "aurelix_audit_lib"
    try:
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(_AUDIT_LIB)]  # type: ignore[attr-defined]
            sys.modules[pkg_name] = pkg
        mod_name = pkg_name + ".industry_resolver"
        if mod_name in sys.modules:
            _resolver_module = sys.modules[mod_name]
            return _resolver_module
        spec = importlib.util.spec_from_file_location(mod_name, str(path))
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        _resolver_module = module
    except Exception as exc:  # noqa: BLE001 - report why, do not pretend zero
        _resolver_error = f"{type(exc).__name__}: {exc}"
        return None
    return _resolver_module


def _resolver_guess(url=None, captures=None):
    """Best-effort resolver guess. Returns ``(handle|None, confidence|None)``.

    ``confidence is None`` means the resolver could not be run at all
    (NOT_MEASURED) — distinct from ``(None, 0.0)``, which means it ran and
    nothing reached threshold.
    """
    mod = _load_resolver()
    if mod is None:
        LOG.warning("[industry] resolver unavailable — %s", _resolver_error)
        return None, None

    if captures:
        handle, confidence = mod.resolve_industry(captures=captures)
        return handle, float(confidence)

    if not url:
        return None, 0.0

    # URL-only: the audit resolver early-returns on empty capture text, so
    # score the URL directly with its own signal table.
    scores = []
    for industry, signals in mod._INDUSTRY_SIGNALS.items():
        scores.append((industry, mod._score_industry(industry, "", [url], signals)))
    scores.sort(key=lambda x: (-x[1], x[0]))
    best_industry, best_score = scores[0] if scores else (None, 0.0)
    if best_score < _RESOLVER_MIN_CONFIDENCE:
        return None, 0.0
    return best_industry, round(float(best_score), 3)


# ── registry handles (advisory only) ──────────────────────────────────────

_registry_handles: Optional[List[str]] = None
_registry_checked = False


def _known_handles() -> Optional[List[str]]:
    """Handles in ``industry_styles``, or None if the table could not be read."""
    global _registry_handles, _registry_checked
    if _registry_checked:
        return _registry_handles
    _registry_checked = True
    try:
        from . import supabase_client  # noqa: WPS433 - local, keeps import cheap

        rows = supabase_client._get("industry_styles", "select=industry")
        handles = sorted({r.get("industry") for r in rows if r.get("industry")})
        _registry_handles = handles or None
    except Exception as exc:  # noqa: BLE001
        LOG.warning("[industry] industry_styles unreadable — %s", exc)
        _registry_handles = None
    return _registry_handles


def _in_registry(handle: str) -> Optional[bool]:
    handles = _known_handles()
    if handles is None:
        return None
    return handle in handles


# ── the one entry point ───────────────────────────────────────────────────

def resolve_industry(
    tenant_context: Optional[Dict[str, Any]],
    url: Optional[str] = None,
    captures: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    """Resolve the tenant's industry from exactly one ranked source.

    Args:
        tenant_context: the dict from ``lib.tenant_context.load_tenant_context``.
            Reads ``phase0_field_values`` and, when the caller has loaded it,
            ``tenant`` (the ``tenants`` row). ``load_tenant_context`` does not
            populate ``tenant`` today; when it does, this picks it up.
        url: source URL, used only when both declarations are silent.
        captures: capture bundle records, used only when both declarations are
            silent. Preferred over ``url`` — the audit resolver reads page HTML.

    Returns:
        {"handle": str,
         "source": "phase0" | "tenants" | "resolver",
         "confidence": float | None,      # None for declared sources
         "disagreement": str | None,      # e.g. "tenants.industry=fintech"
         "field": str,                    # which field the handle came from
         "handle_in_registry": bool | None}

    Raises:
        IndustryContextUnmeasured: the context could not be measured.
        IndustryUndeclared: measured, and no source declares or resolves one.
    """
    if tenant_context is None:
        raise IndustryContextUnmeasured(
            "NOT_MEASURED: no tenant context supplied — industry is unmeasurable, "
            "not undeclared; refusing to fall back to the keyword resolver"
        )

    if not tenant_context.get("tenant_id") and not tenant_context.get("available"):
        raise IndustryContextUnmeasured(
            "NOT_MEASURED: tenant context for coordinate "
            f"{tenant_context.get('coordinate') or tenant_context.get('slug')!r} "
            "resolved no tenant_id and reports available=False. load_tenant_context "
            "never raises, so this is indistinguishable from an unreachable "
            "Supabase; refusing to fall back to the keyword resolver"
        )

    values = tenant_context.get("phase0_field_values") or {}
    tenant_row = tenant_context.get("tenant") or {}

    declared = values.get("industry")
    field = "phase0.industry"
    if not declared:
        verticals = values.get("verticals") or []
        if isinstance(verticals, list) and verticals:
            declared = verticals[0]
            field = "verticals[0]"
    if isinstance(declared, str):
        declared = declared.strip() or None

    column = tenant_row.get("industry")
    if isinstance(column, str):
        column = column.strip() or None

    if declared:
        disagreement = (
            "tenants.industry={0}".format(column)
            if column and column != declared
            else None
        )
        if disagreement:
            LOG.warning(
                "[industry] declaration %r wins; lower-precedence %s recorded, not reconciled",
                declared,
                disagreement,
            )
        return {
            "handle": declared,
            "source": "phase0",
            "confidence": None,
            "disagreement": disagreement,
            "field": field,
            "handle_in_registry": _in_registry(declared),
        }

    if column:
        return {
            "handle": column,
            "source": "tenants",
            "confidence": None,
            "disagreement": None,
            "field": "tenants.industry",
            "handle_in_registry": _in_registry(column),
        }

    if url or captures:
        handle, confidence = _resolver_guess(url=url, captures=captures)
        if handle:
            LOG.info(
                "[industry] no declaration; resolver guessed %r at confidence %s",
                handle,
                confidence,
            )
            return {
                "handle": handle,
                "source": "resolver",
                "confidence": confidence,
                "disagreement": None,
                "field": "industry_resolver",
                "handle_in_registry": _in_registry(handle),
            }
        if confidence is None:
            raise IndustryContextUnmeasured(
                "NOT_MEASURED: no industry declared and the industry_resolver "
                "could not be loaded ({0})".format(_resolver_error)
            )

    raise IndustryUndeclared(
        "no industry declared (phase0.industry, phase0.verticals, tenants.industry "
        "all silent) and none resolvable from the url/captures supplied"
    )
