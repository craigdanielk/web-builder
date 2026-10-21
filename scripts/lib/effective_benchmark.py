"""The benchmark a build is held to: the market benchmark plus the tenant's
declared overrides.

Operator decision 2026-10-21 (THURIS): the conformance gate asserts against
the EFFECTIVE style. Against the raw benchmark, every declared override reads
as a violation, so a build that faithfully renders the operator's palette
fails — the gate reporting the decision itself as the defect.

Exactly the fields `style.tenant_overrides` lists are applied, plus the
declared light palette as tone-qualified roles (`bg_primary@light`, read by
the audit's palette-role rules). Compiler contrast adjustments are NOT folded
in: they are the compiler's, not a declaration, and the gate should still see
them. Everything not declared stays as measured — the type scale included.
"""
from __future__ import annotations

import copy
import re
from typing import Any


def _px(value: Any) -> int | None:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:px)?\s*", str(value))
    return int(float(m.group(1))) if m else None


def effective_benchmark(benchmark: dict, style: dict | None) -> dict:
    eff = copy.deepcopy(benchmark)
    style = style or {}
    overrides = [o for o in (style.get("tenant_overrides") or [])
                 if isinstance(o, dict) and isinstance(o.get("field"), str)]
    fonts: dict[str, str] = {}

    for o in overrides:
        section, _, key = o["field"].partition(".")
        value = o.get("value")
        if section in ("palette_roles", "type_scale", "rhythm") and key:
            eff.setdefault(section, {})[key] = value
        elif section == "fonts" and key in ("heading", "body") and isinstance(value, str):
            fonts[key] = value
        elif section == "border_radius" and key in ("card", "button"):
            px = _px(value)
            if px is not None:
                target = "card_system" if key == "card" else "cta_buttons"
                eff.setdefault(target, {})["radius_px"] = [px]

    if fonts:
        families = [f for f in (fonts.get("heading"), fonts.get("body")) if f]
        eff.setdefault("font_system", {})["families"] = list(dict.fromkeys(families))

    tones = ["base"]
    light = style.get("palette_light")
    if isinstance(light, dict) and light:
        roles = eff.setdefault("palette_roles", {})
        for role, value in light.items():
            if not role.startswith("_") and isinstance(value, str):
                roles[f"{role}@light"] = value
        tones.append("light")

    eff["_effective"] = {
        "basis": "benchmark + style.tenant_overrides",
        "benchmark_market": (benchmark.get("_meta") or {}).get("market"),
        "declared_deviations": overrides,
        "tones": tones,
    }
    return eff
