#!/usr/bin/env python3
"""Evaluate the funnel rules over a BUILT site. Rules are data; this is the engine.

    python3 scripts/quality/funnel-verdicts.py BUILD_DIR --out-dir DIR
                                               [--rules skills/funnel-rules.json]

Exit codes: 0 evaluated · 1 accounting failure or bad rule file ·
3 NOT_MEASURED (the build dir carries no built sections) · 64 usage.

WHY THIS EXISTS
---------------
Task K1 wired the audit's findings to the build's one copy-revision lever. The
audit measures accessibility, performance and design conformance; it does not
measure whether the site asks the visitor for anything. On the committed
cape-crypto build the homepage — the route every visitor lands on — carries six
built sections and no conversion section at all, because its planned closing
CTA was omitted for lack of sourced copy. No audit finding says so. This does.

LANGUAGE CHOICE: Python — same reasons as its sibling
`scripts/quality/findings-to-verdicts.py` (Task K1): the artifacts it reads are
Python-written, the verdict consumer is `orchestrate.py`, and the two files
share the verdict schema, the closed reason vocabulary and the counting
invariant. A second language across one verdict stream would mean two copies of
the schema.

WHAT IS AUTHORITATIVE — MEASURED, NOT ASSUMED
---------------------------------------------
`site-manifest.json` carries `pages[].sections[]`: that is the PLAN. On
cape-crypto (2026-08-17) it plans 8 identical sections on each of 5 routes — 40
— while `section-artifacts/<page>/NN-<archetype>.json` holds 21, because
`omitted-sections.json` records 23 omissions with reasons. So:

    routes, page identity and nav  ← site-manifest.json
    the section SEQUENCE           ← section-artifacts/<page>/*.json
    slot values                    ← each artifact's provenance[] rows

Grading the manifest's sections would grade a funnel nobody can visit. The
homepage's missing CTA is precisely the difference between the two.

`provenance[]` rows are `{slot, value, source}` with `source ∈ harvested |
phase0 | empty`. A slot with source `empty` still rendered its markup —
merchants/02-cta emits `<a href="">` with no label — so a rule about an action
asks provenance whether the action was sourced. It never reads the TSX: parsing
generated JSX to recover a value the emitter already recorded would be a second,
weaker source of truth for the same fact.

THE VERDICT STREAM — K1'S SHAPE, UNCHANGED
------------------------------------------
`funnel-verdicts.json` carries three keys:

  copy_findings   { "<page_id>": { "<slot_key>": {rule_id, detail, ...} } }
                  Byte-for-byte the shape K1's `copy-findings.json` holds at its
                  top level, so the two merge by dict update and the consumer
                  (`orchestrate._findings_are_page_scoped`) cannot tell them
                  apart. Only the TWO fields the consumer reads are load-bearing
                  — `rule_id` and `detail`; the rest is provenance for humans.
                  Rule ids are namespaced `funnel_*` so they can never collide
                  with an audit rule id.
  rule_verdicts   one three-state record per (rule × route) cell: PASS · FAIL ·
                  NOT_MEASURED with a reason. This is the funnel lane's own
                  report and has no analogue in K1.
  unrouted        the FAILs that name no responsible section, with a reason from
                  a closed vocabulary — K1's `unroutable-findings.json`
                  discipline: a defect is routed or counted, never dropped.

Not every FAIL can be a verdict. A verdict flips ONE section from *reproduce
verbatim* to *revise from source*, so it needs a section to blame. "This route
ends in a FAQ" blames the absence of a section; revising the FAQ's copy would
not add a CTA. Such rules declare `verdict_scope: "route"` in the rule file and
their FAILs land in `unrouted` with reason `route-scoped-rule`. Two of the eight
rules are section-scoped, and both name the artifact whose copy is at fault.

ACCOUNTING INVARIANT
--------------------
    pass + fail + not_measured == len(rules) × len(routes)
    routed_fails + unrouted_fails == fail

Both are asserted before anything is written; a mismatch is exit 1, never a
warning. A cell is never omitted, so a rule cannot go quiet.

DETERMINISM
-----------
No clock, no randomness, no network, no LLM. Routes come from the manifest's
declared order, sections from a lexicographic sort of the artifact filenames
(they are zero-padded by the emitter), rules from the rule file's declared
order, and every mapping is written `sort_keys=True`. Two runs are
byte-identical.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_MEASURED = 3
EXIT_USAGE = 64

PASS = "PASS"
FAIL = "FAIL"
NOT_MEASURED = "NOT_MEASURED"

DEFAULT_RULES = Path(__file__).resolve().parent.parent.parent / "skills" / "funnel-rules.json"

# Severity ranks, identical to K1's (from the audit's one declaration site,
# aurelix-uiux-audit/lib/evidence.py) so a merged stream orders consistently.
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
DEFAULT_SEVERITY_RANK = 2

# Slot sources that mean a value actually exists. `empty` is the emitter's own
# word for "the markup rendered but nothing filled it" (reason
# `harvest-exhausted`), which is the defect several of these rules are about.
SOURCED = ("harvested", "phase0")

# Closed vocabulary for a FAIL that carries no verdict. A typo cannot invent a
# new reason: the evaluator asserts membership, exactly as K1 does.
UNROUTED_REASONS = (
    "route-scoped-rule",        # the rule's verdict_scope is "route"
    "no-responsible-section",   # section-scoped rule that named no section
    "section-has-no-slot-key",  # named a section with no uid and no index
)

# Closed vocabulary for the predicate kinds. Adding a kind is a code change AND
# a data change; an unknown kind is a hard error, never a skip.
APPLIES_KINDS = (
    "every_built_route",
    "route_contains_family",
    "route_contains_family_with_sourced_url",
    "route_contains_at_least_n_of_family",
)
ASSERTION_KINDS = (
    "last_section_in_family",
    "first_section_in_family",
    "route_has_sourced_url",
    "family_sections_have_sourced_action_pair",
    "family_sourced_urls_reachable_from_nav",
    "family_precedes_family",
    "first_family_position_at_most",
    "no_adjacent_family_pair",
)


class RuleFileError(ValueError):
    """The rule file is not usable. Reported, never worked around."""


# ---------------------------------------------------------------------------
# Route + page identity — K1's vocabulary, restated
# ---------------------------------------------------------------------------
# `scripts/quality/findings-to-verdicts.py` is the authority on these two
# functions; they are restated rather than imported so the two lanes have no
# runtime dependency on each other's file paths. `scripts/test_funnel_verdicts.py`
# imports BOTH and asserts they agree on a table of inputs, so the copy cannot
# drift silently.

def slugify_route(raw: str | None) -> str:
    """Normalise a route/id to the slug vocabulary `page_lookup_keys` uses."""
    if raw is None:
        return "homepage"
    text = str(raw).strip()
    if "://" in text:
        text = text.split("://", 1)[1]
        text = text[text.find("/"):] if "/" in text else ""
    text = text.split("?", 1)[0].split("#", 1)[0]
    slug = text.strip().lower().strip("/").replace("/", "-")
    return slug or "homepage"


def page_keys(page: dict) -> list[str]:
    """Every slug a page may be known by — same order as page_lookup_keys()."""
    keys: list[str] = []
    for raw in (page.get("id"), page.get("page_id"), page.get("page_type"),
                page.get("route"), page.get("path")):
        if not raw:
            continue
        slug = slugify_route(raw)
        if slug not in keys:
            keys.append(slug)
        if slug.endswith("-page") and slug[: -len("-page")] not in keys:
            keys.append(slug[: -len("-page")])
    return keys or ["homepage"]


def normalise_url(raw: str) -> str:
    """Scheme, fragment, query and trailing slash stripped; lowercased.

    Used only for nav-reachability prefix matching. `https://Support.example.com
    /hc/en-za/requests/new?x=1#top` -> `support.example.com/hc/en-za/requests/new`.
    A relative route keeps its leading slash so `/contact` and `contact` compare
    equal.
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    if "://" in text:
        text = text.split("://", 1)[1]
    text = text.split("#", 1)[0].split("?", 1)[0]
    text = text.strip().lower()
    if len(text) > 1:
        text = text.rstrip("/")
    return text.lstrip("/") if text.startswith("/") else text


def url_reachable(target: str, nav_urls: list[str]) -> bool:
    """True iff a nav link equals the target or is a path-prefix of it.

    Prefix, not equality: a nav link to `support.example.com/hc/en-za` does give
    the visitor a route to `.../hc/en-za/requests/new`. The boundary check on the
    next character prevents `example.com/sign` from claiming `example.com/signup`.
    """
    t = normalise_url(target)
    if not t:
        return False
    for nav in nav_urls:
        n = normalise_url(nav)
        if not n:
            continue
        if t == n or (t.startswith(n) and t[len(n):len(n) + 1] in ("/", "?", "#")):
            return True
    return False


# ---------------------------------------------------------------------------
# Loading the build
# ---------------------------------------------------------------------------

def load_rules(path: Path) -> dict:
    """Read the rule file and validate every declared kind against the closed set."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise RuleFileError(f"{path}: not an object")
    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        raise RuleFileError(f"{path}: rules[] is missing or empty")
    families = doc.get("families") or {}
    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise RuleFileError(f"{path}: a rules[] entry is not an object")
        rid = str(rule.get("id") or "")
        if not rid.startswith("funnel_"):
            raise RuleFileError(f"{path}: rule id {rid!r} is not in the funnel_* "
                                "namespace; it could collide with an audit rule id")
        if rid in seen:
            raise RuleFileError(f"{path}: duplicate rule id {rid!r}")
        seen.add(rid)
        if str(rule.get("verdict_scope")) not in ("route", "section"):
            raise RuleFileError(f"{rid}: verdict_scope must be 'route' or 'section'")
        if not str(rule.get("description") or "").strip():
            raise RuleFileError(f"{rid}: no description")
        if not str(rule.get("remedy_hint") or "").strip():
            raise RuleFileError(f"{rid}: no remedy_hint")
        applies = rule.get("applies_to") or {}
        assertion = rule.get("assertion") or {}
        if applies.get("kind") not in APPLIES_KINDS:
            raise RuleFileError(f"{rid}: unknown applies_to.kind "
                                f"{applies.get('kind')!r}")
        if assertion.get("kind") not in ASSERTION_KINDS:
            raise RuleFileError(f"{rid}: unknown assertion.kind "
                                f"{assertion.get('kind')!r}")
        if applies["kind"] != "every_built_route" and \
                not str(applies.get("not_measured_reason") or "").strip():
            raise RuleFileError(f"{rid}: a conditional applies_to needs a "
                                "not_measured_reason")
        for block in (applies, assertion):
            for key in ("family", "before_family", "after_family"):
                fam = block.get(key)
                if fam is not None and fam not in families:
                    raise RuleFileError(f"{rid}: undeclared family {fam!r}")
            # Resolve slot-vocabulary references now: an unresolvable reference
            # is a rule-file defect and must fail at load, not mid-evaluation
            # where half the cells would already be emitted.
            for key in ("url_slots", "pairs"):
                if key in block:
                    resolve_ref(doc, block[key])
    return doc


def resolve_ref(doc: dict, value):
    """`"action_slots.url"` -> the list at doc["action_slots"]["url"].

    Rules name shared slot vocabularies by reference so the same list is not
    copied into eight rules and drifted in one of them. A plain list passes
    through unchanged.
    """
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    node = doc
    for part in value.split("."):
        if not isinstance(node, dict) or part not in node:
            raise RuleFileError(f"unresolvable reference {value!r}")
        node = node[part]
    if not isinstance(node, list):
        raise RuleFileError(f"reference {value!r} is not a list")
    return node


def load_section(path: Path) -> dict:
    """One artifact -> the facts a funnel rule needs. No TSX parsing."""
    data = json.loads(path.read_text(encoding="utf-8"))
    slots: dict[str, dict] = {}
    for row in data.get("provenance") or []:
        if not isinstance(row, dict):
            continue
        slot = str(row.get("slot") or "").strip()
        if not slot:
            continue
        # Last writer wins, matching the emitter's own append order.
        slots[slot] = {
            "value": str(row.get("value") or ""),
            "source": str(row.get("source") or ""),
        }
    uid = data.get("section_uid")
    uid = str(uid).strip() if isinstance(uid, str) else ""
    index = data.get("section_index")
    return {
        "file": path.name,
        "archetype": str(data.get("archetype") or "").upper(),
        "variant": str(data.get("variant") or ""),
        "origin": str(data.get("origin") or ""),
        "section_uid": uid,
        "section_index": index,
        # Slot key resolution is the CONSUMER's order, mirrored from K1:
        # section_uid -> str(index). A section with neither cannot be addressed.
        "slot_key": uid or ("" if index is None else str(index)),
        "slots": slots,
    }


def load_build(build_dir: Path) -> dict:
    """{routes: [...]} from site-manifest.json + section-artifacts/.

    A manifest page with no artifact directory is still a route, with zero built
    sections — that is a measurable fact, not an absence. An artifact directory
    with no manifest page is also still a route, with no nav; both appear in the
    output so neither can go missing.
    """
    manifest_path = build_dir / "site-manifest.json"
    artifacts_root = build_dir / "section-artifacts"
    manifest_pages: list[dict] = []
    if manifest_path.is_file():
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        pages = doc.get("pages")
        if isinstance(pages, list):
            manifest_pages = [p for p in pages if isinstance(p, dict)]

    routes: list[dict] = []
    claimed: set[str] = set()
    for page in manifest_pages:
        page_id = page_keys(page)[0]
        if page_id in claimed:
            continue
        claimed.add(page_id)
        nav_urls = []
        for link in ((page.get("nav") or {}).get("links") or []):
            if isinstance(link, dict) and str(link.get("href") or "").strip():
                nav_urls.append(str(link["href"]).strip())
        routes.append({
            "page_id": page_id,
            "route": str(page.get("route") or "/"),
            "page_type": str(page.get("page_type") or ""),
            "in_manifest": True,
            "nav_declared": bool(nav_urls),
            "nav_urls": nav_urls,
            "sections": read_sections(artifacts_root / page_id),
        })

    if artifacts_root.is_dir():
        for child in sorted(p for p in artifacts_root.iterdir() if p.is_dir()):
            page_id = slugify_route(child.name)
            if page_id in claimed:
                continue
            claimed.add(page_id)
            routes.append({
                "page_id": page_id,
                "route": "/" + ("" if child.name == "homepage" else child.name),
                "page_type": "",
                "in_manifest": False,
                "nav_declared": False,
                "nav_urls": [],
                "sections": read_sections(child),
            })
    return {"routes": routes}


def read_sections(page_dir: Path) -> list[dict]:
    """Built sections in visit order — the emitter zero-pads, so sorted() is it."""
    if not page_dir.is_dir():
        return []
    out = []
    for i, path in enumerate(sorted(page_dir.glob("*.json")), start=1):
        section = load_section(path)
        section["position"] = i  # position among BUILT sections, 1-based
        out.append(section)
    return out


# ---------------------------------------------------------------------------
# The predicates
# ---------------------------------------------------------------------------

def family_archetypes(doc: dict, name: str) -> tuple[str, ...]:
    fam = (doc.get("families") or {}).get(name) or {}
    return tuple(str(a).upper() for a in (fam.get("archetypes") or []))


def in_family(section: dict, archetypes: tuple[str, ...]) -> bool:
    return section["archetype"] in archetypes


def sourced(section: dict, slot: str) -> str:
    """The slot's value if it was sourced, else "". """
    row = section["slots"].get(slot)
    if not row or row["source"] not in SOURCED:
        return ""
    return row["value"].strip()


def sourced_urls(section: dict, url_slots) -> list[str]:
    return [v for v in (sourced(section, s) for s in url_slots) if v]


def evaluate_applies(doc: dict, rule: dict, route: dict) -> tuple[bool, str]:
    """(applicable, not_measured_reason)."""
    applies = rule["applies_to"]
    kind = applies["kind"]
    reason = str(applies.get("not_measured_reason") or "")
    if not route["sections"]:
        # Every rule here reads the built sequence; with none there is nothing
        # measured, whatever the rule. This is the ONE reason that overrides a
        # rule's own — and it is a measurement, not a skip.
        return False, "route built no sections"
    if kind == "every_built_route":
        return True, ""
    fam = family_archetypes(doc, applies["family"])
    members = [s for s in route["sections"] if in_family(s, fam)]
    if kind == "route_contains_family":
        return bool(members), reason
    if kind == "route_contains_at_least_n_of_family":
        return len(members) >= int(applies["n"]), reason
    if kind == "route_contains_family_with_sourced_url":
        url_slots = resolve_ref(doc, applies["url_slots"])
        return any(sourced_urls(s, url_slots) for s in members), reason
    raise RuleFileError(f"{rule['id']}: unhandled applies_to.kind {kind!r}")


def evaluate_assertion(doc: dict, rule: dict, route: dict) -> tuple[bool, str, list[dict]]:
    """(held, detail, responsible_sections). Pure; reads only the loaded build."""
    a = rule["assertion"]
    kind = a["kind"]
    sections = route["sections"]

    if kind == "last_section_in_family":
        fam = family_archetypes(doc, a["family"])
        last = sections[-1]
        if in_family(last, fam):
            return True, (f"the route closes with {last['archetype']}/"
                          f"{last['variant']} at position {last['position']}"), []
        return False, (f"the route closes with {last['archetype']}/{last['variant']} "
                       f"at position {last['position']}; no section of "
                       f"{'/'.join(fam)} is last"), []

    if kind == "first_section_in_family":
        fam = family_archetypes(doc, a["family"])
        first = sections[0]
        if in_family(first, fam):
            return True, (f"the route opens with {first['archetype']}/"
                          f"{first['variant']}"), []
        return False, (f"the route opens with {first['archetype']}/"
                       f"{first['variant']}, not {'/'.join(fam)}"), []

    if kind == "route_has_sourced_url":
        url_slots = resolve_ref(doc, a["url_slots"])
        hits = [(s, u) for s in sections for u in sourced_urls(s, url_slots)]
        if hits:
            return True, (f"{len(hits)} sourced destination(s); first is "
                          f"{hits[0][1]} on {hits[0][0]['archetype']} at position "
                          f"{hits[0][0]['position']}"), []
        return False, ("no section on the route carries a sourced destination in "
                       f"{', '.join(url_slots)}"), []

    if kind == "family_sections_have_sourced_action_pair":
        fam = family_archetypes(doc, a["family"])
        pairs = resolve_ref(doc, a["pairs"])
        offenders, details = [], []
        for section in [s for s in sections if in_family(s, fam)]:
            complete = [p for p in pairs
                        if sourced(section, p[0]) and sourced(section, p[1])]
            if complete:
                continue
            offenders.append(section)
            missing = sorted({slot for p in pairs for slot in p
                              if slot in section["slots"]
                              and not sourced(section, slot)})
            details.append(
                f"{section['archetype']}/{section['variant']} at position "
                f"{section['position']} ({section['file']}) has no complete "
                f"(label, destination) pair"
                + (f"; unsourced: {', '.join(missing)}" if missing else ""))
        if not offenders:
            return True, ("every conversion section carries a sourced label and "
                          "destination"), []
        return False, "; ".join(details), offenders

    if kind == "family_sourced_urls_reachable_from_nav":
        fam = family_archetypes(doc, a["family"])
        url_slots = resolve_ref(doc, a["url_slots"])
        offenders, details, checked = [], [], 0
        for section in [s for s in sections if in_family(s, fam)]:
            unreachable = [u for u in sourced_urls(section, url_slots)
                           if not url_reachable(u, route["nav_urls"])]
            checked += len(sourced_urls(section, url_slots))
            if not unreachable:
                continue
            offenders.append(section)
            details.append(
                f"{section['archetype']} at position {section['position']} "
                f"({section['file']}) points at {', '.join(sorted(unreachable))}, "
                f"which none of the {len(route['nav_urls'])} nav link(s) reach")
        if not offenders:
            return True, (f"all {checked} sourced conversion destination(s) are "
                          f"reachable from the {len(route['nav_urls'])} nav "
                          f"link(s)"), []
        return False, "; ".join(details), offenders

    if kind == "family_precedes_family":
        before = family_archetypes(doc, a["before_family"])
        after = family_archetypes(doc, a["after_family"])
        first_after = next((s for s in sections if in_family(s, after)), None)
        if first_after is None:
            # applies_to guarantees a member exists, so this is a rule-file bug.
            raise RuleFileError(f"{rule['id']}: applies_to admitted a route with "
                                "no after_family section")
        earlier = [s for s in sections
                   if in_family(s, before) and s["position"] < first_after["position"]]
        if earlier:
            return True, (f"{earlier[0]['archetype']} at position "
                          f"{earlier[0]['position']} precedes "
                          f"{first_after['archetype']} at position "
                          f"{first_after['position']}"), []
        present = [s['archetype'] for s in sections if in_family(s, before)]
        return False, (f"the first {first_after['archetype']} is at position "
                       f"{first_after['position']} and no section of "
                       f"{'/'.join(before)} precedes it"
                       + (f" (present later: {', '.join(present)})" if present
                          else " (none built on this route)")), []

    if kind == "first_family_position_at_most":
        fam = family_archetypes(doc, a["family"])
        limit = int(a["max_position"])
        first = next((s for s in sections if in_family(s, fam)), None)
        if first is None:
            raise RuleFileError(f"{rule['id']}: applies_to admitted a route with "
                                "no family member")
        if first["position"] <= limit:
            return True, (f"the first {first['archetype']} is at built position "
                          f"{first['position']} of {len(sections)} (limit "
                          f"{limit})"), []
        return False, (f"the first {first['archetype']} is at built position "
                      f"{first['position']} of {len(sections)}, deeper than the "
                      f"limit of {limit}"), []

    if kind == "no_adjacent_family_pair":
        fam = family_archetypes(doc, a["family"])
        flags = [in_family(s, fam) for s in sections]
        pairs = [(sections[i], sections[i + 1]) for i in range(len(sections) - 1)
                 if flags[i] and flags[i + 1]]
        if not pairs:
            return True, (f"no two of {'/'.join(fam)} are adjacent among "
                          f"{len(sections)} built section(s)"), []
        details = [f"{x['file']} at position {x['position']} is immediately "
                   f"followed by {y['file']}" for x, y in pairs]
        return False, "; ".join(details), []

    raise RuleFileError(f"{rule['id']}: unhandled assertion.kind {kind!r}")


# ---------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------

def evaluate(doc: dict, build: dict) -> dict:
    """rules × routes -> the verdict stream. Pure: no I/O, no clock."""
    rules = doc["rules"]
    routes = build["routes"]

    cells: list[dict] = []
    verdicts: dict[str, dict[str, dict]] = {}
    unrouted: list[dict] = []

    for rule in rules:
        rid = rule["id"]
        severity = str(rule.get("severity") or "medium").lower()
        scope = rule["verdict_scope"]
        for route in routes:
            page_id = route["page_id"]
            applicable, reason = evaluate_applies(doc, rule, route)
            if not applicable:
                cells.append({
                    "rule_id": rid, "page_id": page_id, "route": route["route"],
                    "state": NOT_MEASURED, "severity": severity,
                    "detail": reason or "the rule does not apply to this route",
                    "sections_named": [],
                })
                continue
            held, detail, offenders = evaluate_assertion(doc, rule, route)
            if held:
                cells.append({
                    "rule_id": rid, "page_id": page_id, "route": route["route"],
                    "state": PASS, "severity": severity, "detail": detail,
                    "sections_named": [],
                })
                continue

            named = [s["slot_key"] for s in offenders if s["slot_key"]]
            cells.append({
                "rule_id": rid, "page_id": page_id, "route": route["route"],
                "state": FAIL, "severity": severity, "detail": detail,
                "sections_named": sorted(named),
            })

            if scope == "route":
                unrouted.append({"rule_id": rid, "page_id": page_id,
                                 "route": route["route"], "severity": severity,
                                 "detail": detail, "reason": "route-scoped-rule"})
                continue
            if not offenders:
                unrouted.append({"rule_id": rid, "page_id": page_id,
                                 "route": route["route"], "severity": severity,
                                 "detail": detail,
                                 "reason": "no-responsible-section"})
                continue
            # Each offender is either routed to its own slot or counted with a
            # reason. A section with neither a uid nor an index cannot be
            # addressed by the consumer's key order, so a verdict on it would
            # never be found — it is counted, not guessed at.
            for section in offenders:
                if not section["slot_key"]:
                    unrouted.append({"rule_id": rid, "page_id": page_id,
                                     "route": route["route"], "severity": severity,
                                     "detail": f"{section['file']}: {detail}",
                                     "reason": "section-has-no-slot-key"})
                    continue
                place(verdicts, page_id, section["slot_key"], rid, detail,
                      severity, route["route"], rule["remedy_hint"])

    for row in unrouted:
        assert row["reason"] in UNROUTED_REASONS, \
            f"undeclared unrouted reason {row['reason']!r}"

    ordered: dict[str, dict[str, dict]] = {}
    for page_id in sorted(verdicts):
        ordered[page_id] = {}
        for slot in sorted(verdicts[page_id]):
            entry = verdicts[page_id][slot]
            entry["contributing_rules"] = sorted(entry["contributing_rules"])
            ordered[page_id][slot] = {k: entry[k] for k in sorted(entry)}
    unrouted.sort(key=lambda r: (r["rule_id"], r["page_id"], r["reason"]))
    cells.sort(key=lambda c: (c["rule_id"], c["page_id"]))

    counts = {state: sum(1 for c in cells if c["state"] == state)
              for state in (PASS, FAIL, NOT_MEASURED)}
    routed_fail_cells = sorted({(c["rule_id"], c["page_id"]) for c in cells
                               if c["state"] == FAIL and c["sections_named"]
                               and _is_section_scoped(rules, c["rule_id"])})
    return {
        "schema": "aurelix.funnel_verdicts.v1",
        "summary": {
            "rules": len(rules),
            "routes": len(routes),
            "cells": len(cells),
            "pass": counts[PASS],
            "fail": counts[FAIL],
            "not_measured": counts[NOT_MEASURED],
            "verdict_pages": len(ordered),
            "verdict_slots": sum(len(p) for p in ordered.values()),
            "routed_fail_cells": len(routed_fail_cells),
            "unrouted_fail_records": len(unrouted),
            "by_rule": {
                rule["id"]: {
                    state: sum(1 for c in cells
                               if c["rule_id"] == rule["id"] and c["state"] == state)
                    for state in (PASS, FAIL, NOT_MEASURED)
                } for rule in rules
            },
            "unrouted_by_reason": {
                reason: sum(1 for r in unrouted if r["reason"] == reason)
                for reason in UNROUTED_REASONS
                if any(r["reason"] == reason for r in unrouted)
            },
        },
        "copy_findings": ordered,
        "rule_verdicts": cells,
        "unrouted": unrouted,
    }


def _is_section_scoped(rules: list[dict], rule_id: str) -> bool:
    for rule in rules:
        if rule["id"] == rule_id:
            return rule["verdict_scope"] == "section"
    return False


def place(verdicts: dict, page_id: str, slot_key: str, rule_id: str, detail: str,
          severity: str, route: str, remedy: str) -> None:
    """Write/merge one verdict at one slot. Highest severity wins the text.

    Merge order is K1's exactly: severity rank, then the rule id as a total
    order, so a slot carrying two funnel FAILs — or one funnel FAIL merged with a
    K1 audit verdict later — resolves the same way every run.
    """
    slot = verdicts.setdefault(page_id, {}).setdefault(slot_key, {
        "rule_id": "", "detail": "", "severity": "", "layer": "funnel",
        "route": route, "match": "funnel-rule", "remedy_hint": "",
        "contributing_rules": [],
    })
    incoming = SEVERITY_RANK.get(severity, DEFAULT_SEVERITY_RANK)
    current = SEVERITY_RANK.get(slot["severity"], -1)
    if incoming > current or (incoming == current
                              and (not slot["rule_id"] or rule_id < slot["rule_id"])):
        slot["rule_id"] = rule_id
        slot["detail"] = detail
        slot["severity"] = severity
        slot["remedy_hint"] = remedy
    if rule_id not in slot["contributing_rules"]:
        slot["contributing_rules"].append(rule_id)


def validate_consumed_shape(copy_findings: dict) -> None:
    """Assert the output is what `_findings_are_page_scoped()` calls page-scoped.

    The consumer swallows a load error and proceeds verbatim, so a shape defect
    is a SILENT no-op in the build. K1 validates the same property for the same
    reason; a funnel verdict that does not merge cleanly is worse than none.
    """
    if not copy_findings:
        return
    page_scoped = all(
        isinstance(v, dict) and v and all(isinstance(i, dict) for i in v.values())
        for v in copy_findings.values())
    if not page_scoped:
        raise ValueError("output would not be detected as page-scoped by "
                         "_findings_are_page_scoped()")
    for page_id, slots in copy_findings.items():
        for slot_key, finding in slots.items():
            if not str(slot_key).strip():
                raise ValueError(f"{page_id}: empty slot key")
            if not str(finding.get("rule_id") or "").strip():
                raise ValueError(f"{page_id}/{slot_key}: verdict has no rule_id")
            if not str(finding.get("rule_id")).startswith("funnel_"):
                raise ValueError(f"{page_id}/{slot_key}: rule_id "
                                 f"{finding['rule_id']!r} is outside the funnel_* "
                                 "namespace")


def check_accounting(result: dict) -> str:
    """"" when the invariants hold, else the failure."""
    s = result["summary"]
    if s["pass"] + s["fail"] + s["not_measured"] != s["cells"]:
        return (f"{s['cells']} cells, but {s['pass']}+{s['fail']}+"
                f"{s['not_measured']} accounted for")
    if s["cells"] != s["rules"] * s["routes"]:
        return (f"{s['rules']} rules x {s['routes']} routes = "
                f"{s['rules'] * s['routes']} cells, {s['cells']} emitted")
    fails = {(c["rule_id"], c["page_id"]) for c in result["rule_verdicts"]
             if c["state"] == FAIL}
    accounted = {(r["rule_id"], r["page_id"]) for r in result["unrouted"]}
    accounted |= {(c["rule_id"], c["page_id"]) for c in result["rule_verdicts"]
                  if c["state"] == FAIL and c["sections_named"]}
    if fails - accounted:
        return (f"{len(fails - accounted)} FAIL cell(s) neither routed nor "
                f"counted: {sorted(fails - accounted)}")
    return ""


def write_outputs(result: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "funnel-verdicts.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the funnel rules over a built site.")
    parser.add_argument("build_dir", help="output/<project>/ — site-manifest.json "
                                          "+ section-artifacts/")
    parser.add_argument("--out-dir", required=True, help="Directory for "
                                                        "funnel-verdicts.json")
    parser.add_argument("--rules", default=str(DEFAULT_RULES),
                        help=f"Rule file (default {DEFAULT_RULES})")
    args = parser.parse_args(argv)

    build_dir = Path(args.build_dir)
    rules_path = Path(args.rules)
    if not build_dir.is_dir():
        print(f"✗ no build dir at {build_dir}", file=sys.stderr)
        return EXIT_USAGE
    if not rules_path.is_file():
        print(f"✗ no rule file at {rules_path}", file=sys.stderr)
        return EXIT_USAGE

    try:
        doc = load_rules(rules_path)
    except (RuleFileError, ValueError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return EXIT_FAILED

    build = load_build(build_dir)
    if not any(r["sections"] for r in build["routes"]):
        print("⚠ NOT_MEASURED: no built sections under "
              f"{build_dir / 'section-artifacts'} — there is no funnel to grade. "
              "This is not a pass.", file=sys.stderr)
        return EXIT_NOT_MEASURED

    try:
        result = evaluate(doc, build)
        validate_consumed_shape(result["copy_findings"])
    except (RuleFileError, ValueError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return EXIT_FAILED

    problem = check_accounting(result)
    if problem:
        print(f"✗ accounting failure: {problem}", file=sys.stderr)
        return EXIT_FAILED

    path = write_outputs(result, Path(args.out_dir))
    s = result["summary"]
    print(f"  {s['rules']} rule(s) x {s['routes']} route(s) = {s['cells']} cell(s): "
          f"{s['pass']} PASS · {s['fail']} FAIL · {s['not_measured']} NOT_MEASURED")
    for rule in doc["rules"]:
        counts = s["by_rule"][rule["id"]]
        print(f"      {rule['id']:<48} {counts[PASS]}P {counts[FAIL]}F "
              f"{counts[NOT_MEASURED]}N")
    print(f"  {s['verdict_slots']} verdict slot(s) on {s['verdict_pages']} page(s), "
          f"{s['unrouted_fail_records']} FAIL(s) counted not routed")
    print(f"  ✓ {path}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
