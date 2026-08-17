#!/usr/bin/env python3
"""Compile audit findings into the `--copy-findings` verdict file, deterministically.

LANGUAGE CHOICE: Python — the input is YAML (`audit_result.yaml`, `yaml.safe_dump`
from the audit's `lib/report.py`), the consumer is Python (`orchestrate.py`'s
`--copy-findings` load), the mapping inputs are the Python-written
`site-spec.json` / `site-manifest.json`, and the sibling quality tooling that is
not a Node build step is already Python (`conformance_runner.py`,
`commission-media.py`). A JS implementation would have to add a YAML parser to
read its input and could not reuse the consumer's key-resolution order.

WHY THIS EXISTS
---------------
`orchestrate.py` has consumed a `--copy-findings` file since the Copy Fidelity
node landed: a matched finding flips one section's prompt block from
`## SOURCE COPY — REPRODUCE VERBATIM` to
`## SOURCE COPY — REVISE FROM SOURCE (weakness flagged)`. Nothing has ever
written that file. 208 non-PASS findings sat unactioned on the cape-crypto
bundle because there was no wire from the audit's report to the build's one
copy-revision lever.

THE CONSUMED SCHEMA — MEASURED, NOT GUESSED
-------------------------------------------
Measured in `orchestrate.py` on 2026-08-17 (resolve by symbol, not by line —
the file drifts within a session):

* Load — `json.loads` of the `--copy-findings` path. Any exception is swallowed
  with a warning and the build proceeds verbatim, so a malformed file is a
  silent no-op. That is exactly why this compiler validates its own output.
* Two accepted shapes, distinguished by `_findings_are_page_scoped()`:
  page-scoped iff EVERY top-level value is a non-empty mapping whose values are
  all mappings. This file emits the page-scoped shape:

      { "<page_id>": { "<slot_key>": { "rule_id": ..., "detail": ... } } }

  A top-level key that is not a page therefore MUST NOT be added — an extra
  scalar-valued top-level key would flip the shape detection and mis-route
  every verdict. Summary counts live in `unroutable-findings.json` instead.
* Slot key resolution, in order (`section_identity(section, i)` first):
  `section_uid` → `str(section["index"])` → `str(i)` → filename. We emit
  `section_uid` when the spec has one, else the section index.
* Fields read from a finding — only TWO: `rule_id` (alias `id`, default
  "unspecified") and `detail` (aliases `message`, `description`, default "").
  Everything else is ignored by the consumer, so the extra keys written here
  (`severity`, `layer`, `route`, `match`, `contributing_findings`) are
  provenance for humans and for the counting invariant, and are inert to the
  build.
* A finding never fires on a section with no harvested copy —
  `build_source_copy_block()` returns "" before it ever looks at the finding.
  A verdict on such a section is inert, so we refuse to emit one and record the
  finding as unroutable instead of pretending it landed.

WHAT IS MAPPABLE, AND WHAT IS COUNTED
-------------------------------------
`docs/census/2026-08-17-audit-findings.md` §2–§3, measured: on a default audit
run 100% of findings carry a route and **0 of 322 carry a section identity**.
Only `--axe` findings carry real DOM paths; `dna_*` conformance findings carry
neither a route (their `page_url` is `pages[0]`, not where the offence is) nor a
selector. So this compiler maps two lanes and COUNTS everything else:

  1. selector lane  — an axe finding whose selector names a section, either by
     carrying the section's `section_uid` or by carrying a class token equal to
     the section's archetype slug. Both are matches against a known identity,
     not inferences from prose (census §3.4 forbids synthesising identity).
  2. page-rule lane — a finding whose `rule_id` appears in COPY_RULE_TARGETS,
     a declared table of copy-actionable rules and the archetypes each one is
     about. Route resolves to a built page → the verdict lands on that page's
     sections of those archetypes.

Every other finding lands in `unroutable-findings.json` with a reason. The two
outputs' finding counts sum to the input count: nothing lands on the floor.

DETERMINISM
-----------
No timestamps, no randomness, no LLM, no network. Findings are keyed by their
input position, all output mappings are written with sorted keys, and merges
resolve by a total order (severity rank, then finding key). Same inputs →
byte-identical outputs.

    python3 scripts/quality/findings-to-verdicts.py AUDIT_YAML \
        [--site-spec output/<project>/site-spec.json] \
        [--out-dir DIR]

Exit codes: 0 compiled · 1 failed · 3 NOT_MEASURED (report carries no
findings) · 64 usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment defect, reported not hidden
    yaml = None

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_MEASURED = 3
EXIT_USAGE = 64

# States that describe a defect. PASS / NOT_APPLICABLE describe the absence of
# one and NOT_MEASURED describes the absence of a measurement; none of the three
# is something a build can revise copy against.
ACTIONABLE_STATES = ("FAIL",)

# Severity → rank, from the audit's one declaration site (lib/evidence.py):
# critical 2.0 · high 1.2 · medium 0.7 · low 0.35 · info 0.0. An unknown
# severity weights as medium there, so it ranks as medium here.
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
DEFAULT_SEVERITY_RANK = 2

# ---------------------------------------------------------------------------
# COPY_RULE_TARGETS — the declared copy lane.
#
# rule_id → the archetypes whose copy the rule is about. A rule absent from this
# table is not copy-actionable and is counted, never routed: flipping a section
# to revise-from-source for a Lighthouse cache header or a CLS score would spend
# an LLM call and risk rewriting compliance-bearing copy for a defect no copy
# change can fix.
#
# Rule ids are the real vocabulary of the engine, extracted by AST from
# `aurelix-uiux-audit/lib/heuristics.py` (40 ids) plus the `axe:` passthroughs
# observed in the capecrypto bundle. Metadata rules (meta_description,
# open_graph_tags, page_title_quality) are deliberately EXCLUDED: their fix is
# a `<head>` tag, not a section slot, so a section-scoped verdict could not
# close them.
# ---------------------------------------------------------------------------
COPY_RULE_TARGETS: dict[str, tuple[str, ...]] = {
    # L1 — heading copy is hero copy.
    "h1_presence": ("HERO",),
    "h1_uniqueness": ("HERO",),
    "site_h1_coverage": ("HERO",),
    "heading_skip_h2_without_h1": ("HERO",),
    "long_page_low_structure": ("FEATURES", "HOW-IT-WORKS", "ABOUT"),
    # L3 — a button's accessible name is its label copy.
    "button_accessible_name": ("CTA", "HERO", "SIGNUP-FORM"),
    "loading_state_feedback": ("SIGNUP-FORM", "CONTACT-FORM"),
    # L8 — conversion copy.
    "cta_presence": ("CTA", "HERO"),
    "social_proof": ("SOCIAL-PROOF", "TESTIMONIALS", "TRUST-BADGES", "LOGO-BAR", "STATS"),
    "trust_signals": ("TRUST-BADGES", "FOOTER"),
    "contact_patterns": ("CONTACT", "CONTACT-FORM", "FOOTER", "CTA"),
}

# axe rules whose subject is copy. These carry a real DOM selector, so they go
# through the selector lane and need no archetype target.
COPY_SELECTOR_RULES = (
    "axe:heading-order",
    "axe:empty-heading",
    "axe:link-name",
    "axe:button-name",
    "axe:input-button-name",
    "axe:link-in-text-block",
)

# The unroutable reasons, declared so the register's vocabulary is closed and a
# typo cannot invent a new one.
REASONS = (
    "state-not-actionable",        # PASS / NOT_MEASURED / NOT_APPLICABLE
    "dna-site-scoped",            # dna_*: page_url is pages[0], not a route (census §3.3)
    "no-route",                   # affected_pages empty
    "no-section-map",             # no site-spec supplied — nothing to map onto
    "route-not-built",            # the route is not a page of this build
    "rule-not-copy-actionable",   # rule_id outside COPY_RULE_TARGETS / COPY_SELECTOR_RULES
    "no-section-identity",        # copy-selector rule that carried no selector
    "selector-no-section-match",  # selector present, matched no known section
    "target-archetype-absent",    # page carries no section of the rule's archetypes
    "target-sections-no-copy",    # target sections exist but hold no harvested copy
)


# ---------------------------------------------------------------------------
# Route + page identity — mirrors orchestrate.page_lookup_keys()
# ---------------------------------------------------------------------------

def slugify_route(raw: str | None) -> str:
    """Normalise a route/id to the slug vocabulary `page_lookup_keys` uses."""
    if raw is None:
        return "homepage"
    text = str(raw).strip()
    if "://" in text:
        # An absolute URL — keep the path only. affected_pages holds absolute URLs.
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


def harvested_copy_count(section: dict) -> int:
    """How many harvested strings this section holds.

    Mirrors `build_source_copy_block`'s early return: headings + body_text +
    ctas. Zero means a verdict on this section could never fire.
    """
    content = section.get("content")
    if not isinstance(content, dict):
        return 0
    total = 0
    for key in ("headings", "body_text"):
        total += len([s for s in (content.get(key) or [])
                      if isinstance(s, str) and s.strip()])
    ctas = content.get("ctas") or []
    for cta in ctas:
        if isinstance(cta, str) and cta.strip():
            total += 1
        elif isinstance(cta, dict) and str(cta.get("text", "")).strip():
            total += 1
    return total


def load_section_map(spec_path: Path | None) -> dict:
    """Build {page_id: [section rows]} + a slug→page_id index from a site-spec.

    Accepts a site-spec.json (has `section_uid` per section — the consumer's
    preferred key) or a site-manifest.json (no uids; sections fall back to their
    index, which is all the identity they have). Returns {} when no spec was
    supplied, which makes every finding `no-section-map` rather than silently
    mapping nothing.
    """
    if spec_path is None:
        return {}
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"{spec_path} has no pages[] — not a multipage spec")

    by_page: dict[str, list[dict]] = {}
    slug_owner: dict[str, str | None] = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        keys = page_keys(page)
        page_id = keys[0]
        rows = []
        for i, section in enumerate(page.get("sections") or []):
            if not isinstance(section, dict):
                continue
            uid = section.get("section_uid")
            index = section.get("index", section.get("source_index", i))
            rows.append({
                "slot_key": str(uid).strip() if isinstance(uid, str) and uid.strip()
                            else str(index),
                "index": index,
                "archetype": str(section.get("archetype") or "").upper(),
                "section_uid": str(uid).strip() if isinstance(uid, str) else "",
                "harvested": harvested_copy_count(section),
            })
        by_page[page_id] = rows
        for key in keys:
            # An ambiguous slug (two pages both of page_type "content") owns
            # nothing — resolving it would pick a page by list order.
            slug_owner[key] = page_id if key not in slug_owner else None
    return {"pages": by_page, "slugs": slug_owner}


# ---------------------------------------------------------------------------
# Selector → section
# ---------------------------------------------------------------------------

_CLASS_TOKEN = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]*)")
_UID_ATTR = re.compile(r"data-section-uid=[\"']?([A-Za-z0-9]+)")


def match_selector(selector: str, rows: list[dict]) -> tuple[list[dict], str]:
    """Resolve a DOM selector to sections of one page. ([], "") when it cannot.

    Two match kinds, both equality against an identity the build already owns:

      section-uid       — the selector carries the section's uid, either as a
                          `data-section-uid` attribute or as a bare token.
      archetype-class   — a class token equals the section's archetype slug
                          (`.hero` → HERO, `.trust-badges` → TRUST-BADGES).

    Anything looser (nth-child paths on a source site's own classes) is a guess
    about which component a class belongs to, and census §3.4 rules that out.
    """
    if not selector or not rows:
        return [], ""
    uids = {m for m in _UID_ATTR.findall(selector)}
    tokens = {t.lower() for t in _CLASS_TOKEN.findall(selector)}
    # A bare uid can also appear as a class token or id fragment.
    for row in rows:
        uid = row["section_uid"]
        if uid and (uid in uids or uid.lower() in tokens or uid in selector):
            return [row], "section-uid"
    hits = [r for r in rows if r["archetype"] and r["archetype"].lower() in tokens]
    if hits:
        return hits, "archetype-class"
    return [], ""


# ---------------------------------------------------------------------------
# The compiler
# ---------------------------------------------------------------------------

def finding_key(index: int, finding: dict) -> str:
    """Stable per-finding key: input position + rule_id. Deterministic."""
    return f"{index:04d}:{finding.get('rule_id') or 'unspecified'}"


def _severity(finding: dict) -> str:
    sev = str(finding.get("severity") or "").strip().lower()
    return sev if sev in SEVERITY_RANK else "medium"


def _rank(finding: dict) -> int:
    return SEVERITY_RANK.get(_severity(finding), DEFAULT_SEVERITY_RANK)


def compile_verdicts(report: dict, section_map: dict) -> dict:
    """findings[] → (copy_findings, unroutable). Pure; no I/O, no clock."""
    findings = report.get("findings")
    if not isinstance(findings, list):
        findings = None

    verdicts: dict[str, dict[str, dict]] = {}
    unroutable: list[dict] = []
    pass_counts: dict[str, int] = {}

    pages = section_map.get("pages") or {}
    slugs = section_map.get("slugs") or {}

    def reject(key: str, finding: dict, route: str, reason: str) -> None:
        assert reason in REASONS, f"undeclared reason {reason!r}"
        unroutable.append({
            "finding_key": key,
            "rule_id": finding.get("rule_id") or "unspecified",
            "state": finding.get("state"),
            "severity": _severity(finding),
            "layer": finding.get("layer"),
            "route": route,
            "reason": reason,
        })

    def place(page_id: str, row: dict, key: str, finding: dict, route: str,
              match: str) -> None:
        """Write/merge one verdict at one slot. Highest severity wins the text."""
        slot = verdicts.setdefault(page_id, {}).setdefault(row["slot_key"], {
            "rule_id": "",
            "detail": "",
            "severity": "",
            "layer": "",
            "route": route,
            "match": match,
            "contributing_findings": [],
        })
        incoming_rank = _rank(finding)
        current_rank = SEVERITY_RANK.get(slot["severity"], -1)
        if incoming_rank > current_rank or (
                incoming_rank == current_rank
                and (not slot["contributing_findings"]
                     or key < slot["contributing_findings"][0])):
            slot["rule_id"] = finding.get("rule_id") or "unspecified"
            slot["detail"] = str(finding.get("issue")
                                 or finding.get("recommended_fix") or "").strip()
            slot["severity"] = _severity(finding)
            slot["layer"] = finding.get("layer") or ""
            slot["match"] = match
        if key not in slot["contributing_findings"]:
            slot["contributing_findings"].append(key)

    for i, finding in enumerate(findings or []):
        if not isinstance(finding, dict):
            # A non-dict row is still an input row; it must be accounted for.
            unroutable.append({
                "finding_key": f"{i:04d}:malformed", "rule_id": "unspecified",
                "state": None, "severity": "medium", "layer": None,
                "route": "", "reason": "state-not-actionable",
            })
            continue

        key = finding_key(i, finding)
        rule_id = str(finding.get("rule_id") or "unspecified")
        state = str(finding.get("state") or "").upper()
        evidence = [e for e in (finding.get("evidence") or []) if isinstance(e, dict)]

        if state not in ACTIONABLE_STATES:
            pass_counts[state or "UNKNOWN"] = pass_counts.get(state or "UNKNOWN", 0) + 1
            reject(key, finding, "", "state-not-actionable")
            continue

        # dna_* aggregates stamp pages[0] on every evidence record regardless of
        # where the offence is (census §3.3). Treating that as a route would
        # route a site-wide defect at a page it may not be on.
        if rule_id.startswith("dna_"):
            reject(key, finding, "", "dna-site-scoped")
            continue

        affected = [p for p in (finding.get("affected_pages") or []) if p]
        if not affected:
            reject(key, finding, "", "no-route")
            continue
        route = slugify_route(affected[0])

        is_selector_rule = rule_id in COPY_SELECTOR_RULES
        targets = COPY_RULE_TARGETS.get(rule_id)
        if not is_selector_rule and not targets:
            reject(key, finding, route, "rule-not-copy-actionable")
            continue

        if not pages:
            reject(key, finding, route, "no-section-map")
            continue

        page_id = slugs.get(route)
        if not page_id or page_id not in pages:
            reject(key, finding, route, "route-not-built")
            continue
        rows = pages[page_id]

        if is_selector_rule:
            selectors = sorted({str(e.get("selector")).strip() for e in evidence
                                if e.get("selector")})
            if not selectors:
                reject(key, finding, route, "no-section-identity")
                continue
            matched: list[dict] = []
            match_kind = ""
            for selector in selectors:
                hits, kind = match_selector(selector, rows)
                for hit in hits:
                    if hit not in matched:
                        matched.append(hit)
                        match_kind = match_kind or kind
            if not matched:
                reject(key, finding, route, "selector-no-section-match")
                continue
        else:
            matched = [r for r in rows if r["archetype"] in targets]
            match_kind = "archetype-target"
            if not matched:
                reject(key, finding, route, "target-archetype-absent")
                continue

        placeable = [r for r in matched if r["harvested"] > 0]
        if not placeable:
            # The consumer's build_source_copy_block returns "" for a section
            # with no harvested copy, so this verdict would never fire.
            reject(key, finding, route, "target-sections-no-copy")
            continue
        for row in placeable:
            place(page_id, row, key, finding, route, match_kind)

    # Deterministic ordering everywhere.
    ordered: dict[str, dict[str, dict]] = {}
    for page_id in sorted(verdicts):
        ordered[page_id] = {}
        for slot in sorted(verdicts[page_id]):
            entry = verdicts[page_id][slot]
            entry["contributing_findings"] = sorted(entry["contributing_findings"])
            ordered[page_id][slot] = {k: entry[k] for k in sorted(entry)}
    unroutable.sort(key=lambda r: r["finding_key"])

    placed = sorted({k for page in ordered.values() for slot in page.values()
                     for k in slot["contributing_findings"]})
    register = {
        "summary": {
            "input_findings": 0 if findings is None else len(findings),
            "verdict_findings": len(placed),
            "unroutable_findings": len(unroutable),
            "verdict_slots": sum(len(p) for p in ordered.values()),
            "verdict_pages": len(ordered),
            "states_not_actionable": {k: pass_counts[k] for k in sorted(pass_counts)},
            "by_reason": {
                reason: sum(1 for r in unroutable if r["reason"] == reason)
                for reason in REASONS
                if any(r["reason"] == reason for r in unroutable)
            },
        },
        "findings": unroutable,
    }
    return {"copy_findings": ordered, "unroutable": register}


def validate_consumed_shape(copy_findings: dict) -> None:
    """Assert the output is what `_findings_are_page_scoped()` calls page-scoped.

    The consumer swallows a load error and proceeds verbatim, so a shape defect
    here would be a silent no-op in the build. Raises rather than warn.
    """
    if not copy_findings:
        return
    if not isinstance(copy_findings, dict):
        raise ValueError("copy-findings must be an object")
    page_scoped = all(
        isinstance(v, dict) and v and all(isinstance(inner, dict) for inner in v.values())
        for v in copy_findings.values()
    )
    if not page_scoped:
        raise ValueError(
            "output would not be detected as page-scoped by "
            "_findings_are_page_scoped(); every top-level value must be a "
            "non-empty mapping of slot -> finding object"
        )
    for page_id, slots in copy_findings.items():
        for slot_key, finding in slots.items():
            if not str(slot_key).strip():
                raise ValueError(f"{page_id}: empty slot key")
            if not str(finding.get("rule_id") or "").strip():
                raise ValueError(f"{page_id}/{slot_key}: verdict has no rule_id")


def write_outputs(result: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cf = out_dir / "copy-findings.json"
    ur = out_dir / "unroutable-findings.json"
    cf.write_text(json.dumps(result["copy_findings"], indent=2, sort_keys=True) + "\n",
                  encoding="utf-8")
    ur.write_text(json.dumps(result["unroutable"], indent=2, sort_keys=True) + "\n",
                  encoding="utf-8")
    return cf, ur


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile audit findings into a --copy-findings verdict file.")
    parser.add_argument("audit_result", help="Path to the audit's audit_result.yaml")
    parser.add_argument("--site-spec", help="site-spec.json (preferred: carries "
                                            "section_uid) or site-manifest.json")
    parser.add_argument("--out-dir", required=True,
                        help="Directory for copy-findings.json + "
                             "unroutable-findings.json")
    args = parser.parse_args(argv)

    if yaml is None:
        print("✗ PyYAML is not installed; cannot read audit_result.yaml",
              file=sys.stderr)
        return EXIT_FAILED

    report_path = Path(args.audit_result)
    if not report_path.is_file():
        print(f"✗ no audit report at {report_path}", file=sys.stderr)
        return EXIT_USAGE
    spec_path = Path(args.site_spec) if args.site_spec else None
    if spec_path is not None and not spec_path.is_file():
        print(f"✗ no site spec at {spec_path}", file=sys.stderr)
        return EXIT_USAGE

    report = yaml.safe_load(report_path.read_text(encoding="utf-8")) or {}
    if not isinstance(report, dict) or not isinstance(report.get("findings"), list):
        print("⚠ NOT_MEASURED: the report carries no findings[] — nothing to "
              "compile. This is not a pass.", file=sys.stderr)
        return EXIT_NOT_MEASURED

    section_map = load_section_map(spec_path)
    result = compile_verdicts(report, section_map)
    validate_consumed_shape(result["copy_findings"])

    summary = result["unroutable"]["summary"]
    total = summary["verdict_findings"] + summary["unroutable_findings"]
    if total != summary["input_findings"]:
        print(f"✗ accounting failure: {summary['input_findings']} findings in, "
              f"{total} accounted for", file=sys.stderr)
        return EXIT_FAILED

    cf, ur = write_outputs(result, Path(args.out_dir))
    print(f"  {summary['input_findings']} findings in → "
          f"{summary['verdict_findings']} verdict(s) across "
          f"{summary['verdict_slots']} slot(s) on {summary['verdict_pages']} page(s), "
          f"{summary['unroutable_findings']} unroutable")
    for reason, count in sorted(summary["by_reason"].items(),
                                key=lambda kv: (-kv[1], kv[0])):
        print(f"      {reason}: {count}")
    print(f"  ✓ {cf}")
    print(f"  ✓ {ur}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
