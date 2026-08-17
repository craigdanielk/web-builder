"""Route planning — the transform a web developer does in their head, written down.

A developer rebuilding a page looks at

  (a) what the current page contains          -> `harvest`      (site-spec.json)
  (b) what the audit said is wrong with it    -> `findings`     (audit_result.yaml)
  (c) what was lost or omitted last time      -> `omissions`
  (d) what the business declared about itself -> `declaration`  (phase-0 rows)
  (e) the design system                       -> `design`       (benchmark JSON)

and decides the section sequence, what art is needed, and what copy is needed.
`plan_route` is that decision as a pure function: same inputs, same output. No
wall clock, no randomness, no iteration over an unsorted dict.

THE PRECEDENCE, and the only one:

    harvested  >  phase0  >  omitted

If the source page says it, the source's words are used. If the source is silent
and the declaration covers it, the section is composed from the declaration and
stamped ``source: "phase0"``. If neither says it, the section is **omitted with a
recorded reason** — never padded, never invented.

WHAT THIS MODULE DELIBERATELY DOES NOT DO

* It does not guess which section a page-level finding belongs to. A default
  audit run carries a route on 100% of findings and a section identity on 0%
  (`docs/census/2026-08-17-audit-findings.md` §3.1, measured over 322 findings).
  Unbindable findings go to `unactioned` with ``reason: "no section identity"``.
* It does not treat `dna_*` conformance findings as route input. Those are
  site-level aggregates whose `page_url` is `pages[0]`, not where the offence is
  (census §3.3). They are listed in `unactioned` so nothing is silently dropped,
  and they never produce a section.
* It does not infer art demand from an archetype. An archetype does not imply
  what its imagery should depict, so art demand is emitted only where the design
  system *declares* an art slot. A design that declares none produces none.
* It does not write files, call a network, or read the environment.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

__all__ = [
    "plan_route",
    "plan_json",
    "ArtIntentUndeclared",
    "COMPOSERS",
    "ART_INTENTS",
]


class ArtIntentUndeclared(ValueError):
    """A design declared an art slot whose intent is not in the legal set.

    Raised at the emitter rather than left to a reviewer's judgement: media may
    be generated only when it carries no factual assertion. `staff_photo`,
    `certification`, `screenshot` and friends depict claims, so they can never
    become a generation job.
    """


# Media that carries no factual assertion. Anything outside this set depicts
# something claim-like and is refused (plan §"Global Constraints").
ART_INTENTS = frozenset({"abstract", "product", "scene", "texture", "diagram"})

# Sections that frame a page rather than carry its argument. Composed sections
# are inserted before the trailing run of these, never after the footer.
TERMINAL_ARCHETYPES = ("CTA", "FOOTER")

# What a section is *for*. An authored taxonomy of the archetype library, not a
# statement about any tenant's content.
ARCHETYPE_INTENT = {
    "ABOUT": "narrative",
    "BLOG-PREVIEW": "insight",
    "COMPARISON": "differentiate",
    "CONTACT": "contact",
    "CONTENT": "explain",
    "CTA": "convert",
    "CURRENCY-MAP": "reach",
    "FAQ": "objection",
    "FEATURES": "products",
    "FOOTER": "close",
    "GALLERY": "showcase",
    "HERO": "orient",
    "HOW-IT-WORKS": "explain",
    "LOGO-BAR": "association",
    "NAV": "navigate",
    "NEWSLETTER": "capture",
    "PORTFOLIO": "showcase",
    "PRICING": "pricing",
    "PRODUCT-SHOWCASE": "showcase",
    "STATS": "evidence",
    "TEAM": "people",
    "TESTIMONIALS": "social-proof",
    "TRUST-BADGES": "credibility",
    "VIDEO": "demonstrate",
}

# Fallback when the caller passes no library. Every value is a variant that
# exists in `section-templates/manifest.json`.
PHASE0_DEFAULT_VARIANT = {
    "ABOUT": "inline-blurb",
    "BLOG-PREVIEW": "grid",
    "FEATURES": "icon-grid",
    "LOGO-BAR": "static-grid",
    "PRICING": "tiered-cards",
    "TEAM": "grid",
    "TRUST-BADGES": "icon-strip",
}


@dataclass(frozen=True)
class Composer:
    """One declared phase-0 field (or group) that can become one section.

    `scope`:
      ``route_filtered`` — the declared items are themselves route-specific, so
        the composer fires wherever the route's own name appears in an item. The
        declaration is the evidence for the placement.
      ``site_wide`` — the fact is true of the whole business (a licence, the
        team, the company description). Repeating it on every route would be
        padding, so it fires **only when something asks**: an audit
        `missing_archetype` finding for that archetype on this route, or a
        prior omission of that archetype on this route.
    """

    archetype: str
    intent: str
    field_keys: tuple
    scope: str


# Order is the composed-section order. Deterministic by construction.
COMPOSERS = (
    Composer("FEATURES", "products", ("product_list",), "route_filtered"),
    Composer("PRICING", "pricing", ("revenue_streams",), "route_filtered"),
    Composer("BLOG-PREVIEW", "insight", ("content_pillars",), "route_filtered"),
    Composer("LOGO-BAR", "association", ("integrations",), "route_filtered"),
    Composer("TRUST-BADGES", "credibility", ("licenses", "regulatory_body"), "site_wide"),
    Composer("ABOUT", "narrative", ("description",), "site_wide"),
    Composer("TEAM", "people", ("team",), "site_wide"),
)


# ── small pure helpers ───────────────────────────────────────────────────────

def _sha(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def _norm_route(route: str) -> str:
    r = (route or "").strip()
    if "://" in r:
        r = "/" + r.split("://", 1)[1].split("/", 1)[1] if "/" in r.split("://", 1)[1] else "/"
    if not r.startswith("/"):
        r = "/" + r
    if len(r) > 1:
        r = r.rstrip("/") or "/"
    return r


def _route_tokens(route: str) -> set:
    """Words that identify this route inside a declared string.

    `/merchants` -> {"merchants", "merchant"}. The root route has no token: it
    is the whole business, so route-filtered composers take every declared item.
    """
    r = _norm_route(route)
    if r == "/":
        return set()
    tokens = set()
    for part in r.strip("/").split("/"):
        part = part.lower()
        if not part:
            continue
        tokens.add(part)
        if part.endswith("s") and len(part) > 3:
            tokens.add(part[:-1])
    return tokens


def _pages(harvest: Any) -> list:
    if isinstance(harvest, dict) and isinstance(harvest.get("pages"), list):
        return harvest["pages"]
    if isinstance(harvest, dict) and "sections" in harvest:
        return [harvest]
    if isinstance(harvest, list):
        return harvest
    return []


def _harvest_page(harvest: Any, route: str) -> dict:
    want = _norm_route(route)
    for page in _pages(harvest):
        if isinstance(page, dict) and _norm_route(page.get("route") or "") == want:
            return page
    return {}


def _findings_list(findings: Any) -> list:
    if isinstance(findings, dict):
        return list(findings.get("findings") or [])
    return list(findings or [])


def _finding_route(f: dict) -> str | None:
    pages = f.get("affected_pages") or []
    if not pages:
        return None
    return _norm_route(str(pages[0]))


def _is_site_level(f: dict) -> bool:
    # `dna_*` findings are aggregates over every audited page: `page_url` is
    # `pages[0]` and `affected_pages` is the whole site. They carry neither a
    # route nor a section, so they are not a route input — listed, never routed.
    return str(f.get("rule_id") or "").startswith("dna_")


def _selectors(f: dict) -> list:
    out = []
    for ev in f.get("evidence") or []:
        if isinstance(ev, dict) and ev.get("selector"):
            out.append(str(ev["selector"]))
    return out


def _omitted_docs(omissions: Any) -> tuple:
    """Accepts ``{"omitted_sections": ..., "classification_loss": ...}`` and,
    for convenience, a bare omitted-sections document."""
    if not isinstance(omissions, dict):
        return ({}, {})
    if "omitted_sections" in omissions or "classification_loss" in omissions:
        return (
            omissions.get("omitted_sections") or {},
            omissions.get("classification_loss") or {},
        )
    if "omitted" in omissions:
        return (omissions, {})
    return ({}, omissions if "pages" in omissions else {})


def _page_matches(value: str, page_id: str, route: str) -> bool:
    """`omitted-sections.json` keys pages as `sections/<page_id>`;
    `classification-loss.json` keys them as `<page_id>`."""
    v = str(value or "").strip().strip("/")
    tail = v.rsplit("/", 1)[-1]
    return tail == page_id or _norm_route(tail) == _norm_route(route)


def _declared(declaration: Any, key: str) -> Any:
    if not isinstance(declaration, dict):
        return None
    fields = declaration.get("phase0_field_values")
    if isinstance(fields, dict):
        return fields.get(key)
    return declaration.get(key)


def _as_items(value: Any) -> list:
    if value is None or value == "" or value == [] or value == {}:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in (None, "", [], {})]
    return [value]


def _library_variants(design: Any, archetype: str) -> list:
    """Variant names for an archetype, from a `section-templates/manifest.json`
    -shaped `design["library"]` (or a plain archetype -> [names] map)."""
    lib = (design or {}).get("library") if isinstance(design, dict) else None
    if not isinstance(lib, dict):
        return []
    entry = lib.get("archetypes", lib).get(archetype) if isinstance(lib, dict) else None
    if isinstance(entry, dict):
        entry = entry.get("variants") or []
    if not isinstance(entry, list):
        return []
    names = []
    for v in entry:
        if isinstance(v, dict) and v.get("name"):
            names.append(str(v["name"]))
        elif isinstance(v, str):
            names.append(v)
    return sorted(set(names))


def _choose_variant(archetype: str, route: str, design: Any) -> str | None:
    """Deterministic rotation over the library, so five routes do not all open
    with the same variant. Falls back to a known-good local variant."""
    names = _library_variants(design, archetype)
    if names:
        idx = int(_sha(_norm_route(route), archetype), 16) % len(names)
        return names[idx]
    return PHASE0_DEFAULT_VARIANT.get(archetype)


def _art_slots(design: Any, archetype: str, variant: str | None) -> list:
    decl = (design or {}).get("art_slots") if isinstance(design, dict) else None
    if not isinstance(decl, dict):
        return []
    slots = decl.get("%s/%s" % (archetype, variant)) if variant else None
    if slots is None:
        slots = decl.get(archetype)
    if not isinstance(slots, list):
        return []
    for s in slots:
        intent = (s or {}).get("intent") if isinstance(s, dict) else None
        if intent not in ART_INTENTS:
            raise ArtIntentUndeclared(
                "art slot %r on %s declares intent %r, which is not one of %s — "
                "media may carry no factual assertion"
                % ((s or {}).get("slot"), archetype, intent, sorted(ART_INTENTS))
            )
    return slots


# ── the function ─────────────────────────────────────────────────────────────

def plan_route(
    route: str,
    harvest: Any,
    findings: Any,
    omissions: Any,
    declaration: Any,
    design: Any,
    page_id: str | None = None,
) -> dict:
    """Decide one route's section sequence, art demand and copy demand.

    `page_id` is read from the harvest page when present; the keyword exists
    only for callers whose harvest does not carry one (the omission registers
    are keyed by page_id, not by route).
    """
    route = _norm_route(route)
    page = _harvest_page(harvest, route)
    pid = page_id or str(page.get("page_id") or page.get("id") or "")

    omitted_doc, loss_doc = _omitted_docs(omissions)

    sections: list = []
    art_demand: list = []
    copy_demand: list = []
    unactioned: list = []
    actioned: list = []
    omitted: list = []

    # ── (a) what the page already contains ───────────────────────────────────
    harvested_blocks = list(page.get("sections") or [])
    for i, blk in enumerate(harvested_blocks):
        archetype = str(blk.get("archetype") or "").strip()
        if not archetype:
            continue
        uid = str(blk.get("section_uid") or "") or "h%d-%s" % (i, _sha(route, str(i))[:8])
        sections.append(
            {
                "section_uid": uid,
                "archetype": archetype,
                "variant": blk.get("variant"),
                "intent": ARCHETYPE_INTENT.get(archetype, "present"),
                "source": "harvested",
                "content_ref": uid,
                "reason": "harvested from %s at source index %s"
                % (page.get("source_url") or route, blk.get("index", i)),
            }
        )
    harvested_archetypes = {s["archetype"] for s in sections}
    blocks_by_uid = {
        str(b.get("section_uid")): b for b in harvested_blocks if b.get("section_uid")
    }

    # ── (b) the audit's demands, before composition so they can drive it ─────
    route_findings = []
    seen_ids: dict = {}
    for f in _findings_list(findings):
        if not isinstance(f, dict):
            continue
        site_level = _is_site_level(f)
        if not site_level and _finding_route(f) != route:
            continue  # belongs to another route's plan
        base = str(f.get("finding_id") or f.get("id") or "")
        if not base:
            base = "%s@%s" % (f.get("rule_id"), "site" if site_level else route)
        n = seen_ids.get(base, 0) + 1
        seen_ids[base] = n
        fid = base if n == 1 else "%s#%d" % (base, n)
        route_findings.append((fid, f, site_level))

    demanded_archetypes: dict = {}
    for fid, f, site_level in route_findings:
        if site_level:
            unactioned.append(
                {
                    "finding_id": fid,
                    "reason": "site-level conformance aggregate; carries neither "
                    "route nor section identity",
                }
            )
            continue
        state = str(f.get("state") or "").upper()
        if state != "FAIL":
            unactioned.append(
                {
                    "finding_id": fid,
                    "reason": "state=%s; nothing to action" % (state or "UNKNOWN"),
                }
            )
            continue
        rule_id = str(f.get("rule_id") or "")
        if rule_id.startswith("missing_archetype:"):
            demanded_archetypes.setdefault(rule_id.split(":", 1)[1].strip(), []).append(fid)
            continue
        # A FAIL with a DOM path can be bound only if a harvested section says
        # which class it renders. Nothing else in the tree can make that join.
        bound = _bind(f, harvested_blocks)
        if bound:
            uid, selector = bound
            copy_demand.append(
                {
                    "section_uid": uid,
                    "slot": selector,
                    "field_key": None,
                    "reason": "audit finding %s: %s" % (fid, f.get("issue") or rule_id),
                }
            )
            actioned.append(
                {
                    "finding_id": fid,
                    "effect": "copy demand on section %s (slot %s)" % (uid, selector),
                }
            )
        else:
            unactioned.append({"finding_id": fid, "reason": "no section identity"})

    # ── (c) what the previous build omitted for want of sourced content ──────
    prior_omissions: dict = {}
    for row in omitted_doc.get("omitted") or []:
        if not isinstance(row, dict):
            continue
        if not _page_matches(row.get("page") or "", pid, route):
            continue
        prior_omissions.setdefault(str(row.get("archetype") or ""), []).append(
            str(row.get("reason") or row.get("cause") or "omitted")
        )

    # ── (d) compose from the declaration ─────────────────────────────────────
    tokens = _route_tokens(route)
    composed: list = []
    for comp in COMPOSERS:
        if comp.archetype in harvested_archetypes:
            omitted.append(
                {
                    "archetype": comp.archetype,
                    "field_key": comp.field_keys[0],
                    "reason": "harvested section already covers %s; the declared %s "
                    "is not told twice" % (comp.archetype, comp.field_keys[0]),
                }
            )
            if comp.archetype in demanded_archetypes:
                for fid in demanded_archetypes.pop(comp.archetype):
                    actioned.append(
                        {
                            "finding_id": fid,
                            "effect": "archetype %s already present from harvest"
                            % comp.archetype,
                        }
                    )
            continue

        # Claimed here so both branches below (and the actioned rows) see the
        # same list, and so a demand that cannot be met falls through to the
        # unactioned sweep rather than being popped and forgotten.
        demand_fids = demanded_archetypes.get(comp.archetype) or []

        items = []
        for key in comp.field_keys:
            for value in _as_items(_declared(declaration, key)):
                items.append({"value": value, "field_key": key})

        if not items:
            omitted.append(
                {
                    "archetype": comp.archetype,
                    "field_key": comp.field_keys[0],
                    "reason": "nothing declared under %s; the section is omitted "
                    "rather than padded" % ", ".join(comp.field_keys),
                }
            )
            continue

        if comp.scope == "route_filtered" and tokens:
            kept = [
                it
                for it in items
                if any(t in str(it["value"]).lower() for t in sorted(tokens))
            ]
            if not kept:
                omitted.append(
                    {
                        "archetype": comp.archetype,
                        "field_key": comp.field_keys[0],
                        "reason": "no declared %s item names this route (%s)"
                        % (comp.field_keys[0], "/".join(sorted(tokens))),
                    }
                )
                continue
            why = "%d of %d declared %s items name this route" % (
                len(kept),
                len(items),
                comp.field_keys[0],
            )
            items = kept
        elif comp.scope == "route_filtered":
            why = "the whole declared %s, on the root route" % comp.field_keys[0]
        else:
            # site_wide: a business-level fact. Only compose it where something
            # asked, otherwise repeating it on every route is padding.
            prior = prior_omissions.get(comp.archetype) or []
            if demand_fids:
                why = "audit demanded %s on this route (%s); declared %s answers it" % (
                    comp.archetype,
                    ", ".join(demand_fids),
                    ", ".join(comp.field_keys),
                )
            elif prior:
                why = (
                    "the previous build omitted %s here (%s); declared %s answers it"
                    % (comp.archetype, prior[0], ", ".join(comp.field_keys))
                )
            else:
                omitted.append(
                    {
                        "archetype": comp.archetype,
                        "field_key": comp.field_keys[0],
                        "reason": "declared %s is a site-level fact and nothing on "
                        "this route asked for %s" % (comp.field_keys[0], comp.archetype),
                    }
                )
                continue

        variant = _choose_variant(comp.archetype, route, design)
        if not variant:
            omitted.append(
                {
                    "archetype": comp.archetype,
                    "field_key": comp.field_keys[0],
                    "reason": "no variant known for %s in the supplied library"
                    % comp.archetype,
                }
            )
            continue

        uid = "p0-" + _sha(route, comp.archetype, comp.field_keys[0])[:12]
        composed.append(
            {
                "section_uid": uid,
                "archetype": comp.archetype,
                "variant": variant,
                "intent": comp.intent,
                "source": "phase0",
                "content_ref": comp.field_keys[0],
                "reason": "composed from the declaration: %s (%d item%s)"
                % (why, len(items), "" if len(items) == 1 else "s"),
            }
        )
        demanded_archetypes.pop(comp.archetype, None)
        for fid in demand_fids:
            actioned.append(
                {
                    "finding_id": fid,
                    "effect": "composed %s section %s from declared %s"
                    % (comp.archetype, uid, comp.field_keys[0]),
                }
            )
        # A declared product is a fact, not a headline. C3 phrases it; the plan
        # only says which declared field the phrasing must trace to.
        for slot in ("headline", "body"):
            copy_demand.append(
                {
                    "section_uid": uid,
                    "slot": slot,
                    "field_key": comp.field_keys[0],
                    "reason": "declared %s places facts; the %s must be phrased from "
                    "them and trace back to that field"
                    % (comp.field_keys[0], slot),
                }
            )

    # Any archetype the audit demanded that no composer and no harvest can fill.
    for archetype in sorted(demanded_archetypes):
        for fid in demanded_archetypes[archetype]:
            unactioned.append(
                {
                    "finding_id": fid,
                    "reason": "no harvested or declared content for archetype %s; "
                    "a section would have to be invented" % archetype,
                }
            )

    # ── insert composed sections before the trailing CTA/FOOTER run ──────────
    cut = len(sections)
    while cut > 0 and sections[cut - 1]["archetype"] in TERMINAL_ARCHETYPES:
        cut -= 1
    sections = sections[:cut] + composed + sections[cut:]

    # ── content the previous build lost -> copy demand, never silence ────────
    for blk in _loss_blocks(loss_doc, pid, route):
        uid = str(blk.get("section_uid") or "")
        lost = int(blk.get("items_lost") or 0)
        if not uid or lost <= 0:
            continue
        headings = [
            str((d or {}).get("heading") or "").strip()
            for d in (blk.get("items_lost_detail") or [])
        ]
        headings = [h for h in headings if h]
        copy_demand.append(
            {
                "section_uid": uid,
                "slot": "items",
                "field_key": None,
                "reason": "%d harvested item%s were lost by the previous build: %s"
                % (lost, "" if lost == 1 else "s", "; ".join(headings) or "unnamed"),
            }
        )

    # ── art demand: declared by the design, never inferred ───────────────────
    for sec in sections:
        slots = _art_slots(design, sec["archetype"], sec.get("variant"))
        if not slots:
            continue
        blk = blocks_by_uid.get(sec["content_ref"]) if sec["source"] == "harvested" else None
        source_has_art = bool((blk or {}).get("images"))
        for slot in slots:
            if source_has_art:
                continue
            art_demand.append(
                {
                    "section_uid": sec["section_uid"],
                    "slot": slot.get("slot"),
                    "intent": slot.get("intent"),
                    "aspect": slot.get("aspect"),
                    "reason": "the design declares %s on %s and the source supplies "
                    "no imagery for it" % (slot.get("slot"), sec["archetype"]),
                }
            )

    return {
        "route": route,
        "sections": sections,
        "art_demand": art_demand,
        "copy_demand": copy_demand,
        "unactioned": unactioned,
        "actioned": actioned,
        "omitted": omitted,
    }


def _bind(f: dict, harvested_blocks: Iterable) -> tuple | None:
    """Resolve an audit selector to a harvested section, or None.

    The only join available: a harvested block that records the CSS class its
    source rendered (`root_class` / `source_selector`). Absent that, a selector
    is a DOM path against a page whose sections we cannot name — and guessing
    would be an invented fact.
    """
    for selector in _selectors(f):
        for blk in harvested_blocks:
            if not isinstance(blk, dict):
                continue
            uid = str(blk.get("section_uid") or "")
            if not uid:
                continue
            for attr in ("root_class", "source_selector"):
                cls = str(blk.get(attr) or "").strip().lstrip(".")
                if cls and cls in selector:
                    return (uid, selector)
    return None


def _loss_blocks(loss_doc: Any, page_id: str, route: str) -> list:
    pages = (loss_doc or {}).get("pages") if isinstance(loss_doc, dict) else None
    if not isinstance(pages, dict):
        return []
    for key in sorted(pages):
        if _page_matches(key, page_id, route):
            entry = pages[key] or {}
            return [b for b in (entry.get("blocks") or []) if isinstance(b, dict)]
    return []


def plan_json(plan: dict) -> str:
    """Canonical serialisation — the determinism assertion runs on this."""
    return json.dumps(plan, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
