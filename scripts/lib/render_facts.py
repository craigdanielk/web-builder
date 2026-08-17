"""Read `render-audit-results/report.json` — the facts the probe measured.

The render probe (`scripts/quality/render-audit.js`) writes two files. The
build read only `render-audit.json`, the defect summary. `report.json` carries
`routes[].facts` — the page box, the per-section geometry/fingerprint/paint
census, the rendered image boxes, and the full contrast measurement including
its denominator — and had NO Python consumer at all.

This module is that consumer. It turns the facts into six checks, each with
three outcomes:

    PASS           measured, nothing found
    FAIL           measured, findings listed with the evidence
    NOT_MEASURED   the probe did not record what the check needs

NOT_MEASURED is never collapsed into PASS. "0 contrast failures" off a report
with no contrast denominator is not a clean site, it is an unread instrument.

Two traps this module handles, both recorded by C2 (3ccf9444):

  * Section records include a wrapper `<div>` AND its inner `<section>`, so
    identical `textFp` values WITHIN one route are nesting, not duplication.
    Fingerprints are deduplicated per route before any cross-route comparison.
  * `facts.page` is absent when the probe crashed before recording it (and on
    every report written before C2). That is NOT_MEASURED, not "no overflow".

This module measures and reports. It does not fail a build: the thresholds for
aspect distortion and duplication are not ratified, and turning an unratified
threshold into a build-stopper is how a gate stops being believed. The status
it returns is recorded so a later task (D2) can decide consequence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PASS = "pass"
FAIL = "fail"
NOT_MEASURED = "not_measured"

#: Rendered-vs-natural aspect ratios differing by more than this read as
#: distortion. 5% absorbs sub-pixel layout rounding on a 1440px viewport.
ASPECT_TOLERANCE = 0.05

#: `object-fit` values that preserve or intentionally crop the aspect ratio.
#: Only `fill` (the CSS default) stretches, so only `fill` can be distorted.
_ASPECT_SAFE_FITS = ("cover", "contain", "scale-down", "none")

#: Below this, two routes sharing a fingerprint is a heading or a button label,
#: not a duplicated section.
MIN_DUPLICATION_TEXT_LEN = 200

CHECKS = (
    "horizontal_overflow",
    "zero_dimension",
    "empty_section",
    "aspect_distortion",
    "contrast",
    "cross_route_duplication",
)


def _check(status: str, reason: str = "", **extra) -> dict:
    out = {"status": status, "findings": []}
    if reason:
        out["reason"] = reason
    out.update(extra)
    return out


def _routes(report: dict) -> list[dict]:
    return [r for r in (report.get("routes") or []) if isinstance(r, dict)]


def _facts(route: dict) -> dict:
    f = route.get("facts")
    return f if isinstance(f, dict) else {}


def _sections(route: dict) -> list[dict]:
    return [s for s in (_facts(route).get("sections") or []) if isinstance(s, dict)]


def _images(route: dict) -> list[dict]:
    return [i for i in (_facts(route).get("images") or []) if isinstance(i, dict)]


# ── the six checks ─────────────────────────────────────────────────


def _horizontal_overflow(routes: list[dict]) -> dict:
    findings, measured = [], 0
    pages_missing = []
    for r in routes:
        page = _facts(r).get("page")
        if not (isinstance(page, dict) and "overflowX" in page):
            # C2's trap: `facts.page` is null when the probe crashed before it
            # recorded the page box. That route's layout is unmeasured, and a
            # section-level sweep must not be reported as covering it.
            pages_missing.append(r.get("route"))
        else:
            measured += 1
            if page.get("overflowX"):
                findings.append({
                    "route": r.get("route"),
                    "scope": "page",
                    "scrollWidth": page.get("scrollWidth"),
                    "clientWidth": page.get("clientWidth"),
                })
        for s in _sections(r):
            if "overflowX" not in s:
                continue
            measured += 1
            if s.get("overflowX"):
                findings.append({
                    "route": r.get("route"),
                    "scope": "section",
                    "selector": s.get("selector") or s.get("cls"),
                    "scrollWidth": s.get("scrollWidth"),
                    "clientWidth": s.get("clientWidth"),
                })
    if not measured:
        return _check(
            NOT_MEASURED,
            "no route recorded a page box or a section scrollWidth — the probe "
            "predates the measurement, or crashed before taking it",
        )
    if findings:
        out = _check(FAIL, boxes_measured=measured, pages_missing=pages_missing)
        out["findings"] = findings
        return out
    if pages_missing:
        return _check(
            NOT_MEASURED,
            "no page box recorded for route(s) "
            + ", ".join(str(p) for p in pages_missing)
            + " — their layout was never measured, so this is not a clean result",
            boxes_measured=measured,
            pages_missing=pages_missing,
        )
    return _check(PASS, boxes_measured=measured, pages_missing=[])


def _zero_dimension(routes: list[dict]) -> dict:
    findings, candidates, measured = [], 0, 0
    for r in routes:
        for s in _sections(r):
            if "belowThreshold" not in s:
                continue
            measured += 1
            if not s.get("belowThreshold"):
                continue
            candidates += 1
            if int(s.get("h") or s.get("height") or 0) == 0:
                findings.append({
                    "route": r.get("route"),
                    "selector": s.get("selector") or s.get("cls"),
                    "tag": s.get("tag"),
                    "h": 0,
                })
    if not measured:
        return _check(
            NOT_MEASURED,
            "no section carries belowThreshold — sub-40px blocks were filtered "
            "out before they could be recorded",
        )
    out = _check(FAIL if findings else PASS, candidates=candidates, sections_measured=measured)
    out["findings"] = findings
    return out


def _empty_section(routes: list[dict]) -> dict:
    findings, measured = [], 0
    for r in routes:
        for s in _sections(r):
            if "imgCount" not in s or "hasBg" not in s or "textLen" not in s:
                continue
            if s.get("belowThreshold"):
                continue  # wrapper noise, covered by the zero-dimension check
            measured += 1
            if int(s.get("textLen") or 0) == 0 and int(s.get("imgCount") or 0) == 0 \
                    and not s.get("hasBg"):
                findings.append({
                    "route": r.get("route"),
                    "selector": s.get("selector") or s.get("cls"),
                    "tag": s.get("tag"),
                    "h": s.get("h"),
                })
    if not measured:
        return _check(
            NOT_MEASURED,
            "sections carry no imgCount/hasBg — 'renders nothing' is not "
            "distinguishable from 'has no text'",
        )
    out = _check(FAIL if findings else PASS, sections_measured=measured)
    out["findings"] = findings
    return out


def _aspect_distortion(routes: list[dict]) -> dict:
    findings, measured = [], 0
    for r in routes:
        for img in _images(r):
            if img.get("kind") != "img":
                continue
            w, h, rw, rh = (img.get("w"), img.get("h"), img.get("rw"), img.get("rh"))
            if not all(isinstance(v, (int, float)) and v > 0 for v in (w, h, rw, rh)):
                continue
            measured += 1
            if str(img.get("objectFit") or "fill").lower() in _ASPECT_SAFE_FITS:
                continue
            natural, rendered = w / h, rw / rh
            drift = abs(rendered - natural) / natural
            if drift > ASPECT_TOLERANCE:
                findings.append({
                    "route": r.get("route"),
                    "selector": img.get("selector"),
                    "src": img.get("src"),
                    "natural": [w, h],
                    "rendered": [rw, rh],
                    "objectFit": img.get("objectFit"),
                    "drift": round(drift, 3),
                })
    if not measured:
        return _check(
            NOT_MEASURED,
            "no image carries both a natural size and a rendered box — "
            "distortion had a denominator and no numerator",
        )
    out = _check(FAIL if findings else PASS, images_measured=measured)
    out["findings"] = findings
    return out


def _contrast(routes: list[dict]) -> dict:
    measured = passed = failed = 0
    saw_summary = False
    findings = []
    for r in routes:
        summary = _facts(r).get("contrastSummary")
        if not isinstance(summary, dict):
            continue
        saw_summary = True
        measured += int(summary.get("measured") or 0)
        passed += int(summary.get("passed") or 0)
        failed += int(summary.get("failed") or 0)
        for entry in _facts(r).get("lowContrast") or []:
            if not isinstance(entry, dict):
                continue
            findings.append({
                "route": r.get("route"),
                "selector": entry.get("selector"),
                "tag": entry.get("tag"),
                "fg": entry.get("fg"),
                "bg": entry.get("bg"),
                "ratio": entry.get("ratio"),
                "need": entry.get("need"),
            })
    if not saw_summary:
        return _check(
            NOT_MEASURED,
            "no route recorded contrastSummary — a failure count with no "
            "denominator is not a contrast result",
        )
    if measured == 0:
        return _check(NOT_MEASURED, "contrast was measured on 0 elements",
                      measured=0, passed=0, failed=0)
    out = _check(FAIL if failed else PASS, measured=measured, passed=passed, failed=failed)
    out["findings"] = findings
    return out


def _cross_route_duplication(routes: list[dict]) -> dict:
    # Fingerprints are deduplicated WITHIN a route first: the probe records a
    # wrapper div and the <section> inside it, which share their text.
    per_route: dict[str, set[str]] = {}
    measured_routes = 0
    for r in routes:
        fps = set()
        saw = False
        for s in _sections(r):
            fp = s.get("textFp")
            if not fp:
                continue
            saw = True
            if s.get("belowThreshold"):
                continue
            if int(s.get("textLen") or 0) < MIN_DUPLICATION_TEXT_LEN:
                continue
            fps.add(fp)
        if saw:
            measured_routes += 1
            per_route[str(r.get("route"))] = fps

    if measured_routes < 2:
        return _check(
            NOT_MEASURED,
            "duplication needs at least two routes carrying textFp; "
            f"{measured_routes} available",
            routes_measured=measured_routes,
        )

    where: dict[str, list[str]] = {}
    for route_name, fps in per_route.items():
        for fp in fps:
            where.setdefault(fp, []).append(route_name)
    findings = [
        {"textFp": fp, "routes": sorted(rs)}
        for fp, rs in sorted(where.items())
        if len(rs) > 1
    ]
    out = _check(FAIL if findings else PASS, routes_measured=measured_routes)
    out["findings"] = findings
    return out


# ── the reading ────────────────────────────────────────────────────


def analyse_render_facts(report: dict) -> dict[str, Any]:
    """Turn a parsed report.json into six checks and one aggregate status."""
    routes = _routes(report)
    if not routes:
        return {
            "status": NOT_MEASURED,
            "reason": "report.json carries no routes — the probe rendered nothing",
            "schema": report.get("schema"),
            "routes_measured": 0,
            "checks": {name: _check(NOT_MEASURED, "no routes") for name in CHECKS},
        }

    checks = {
        "horizontal_overflow": _horizontal_overflow(routes),
        "zero_dimension": _zero_dimension(routes),
        "empty_section": _empty_section(routes),
        "aspect_distortion": _aspect_distortion(routes),
        "contrast": _contrast(routes),
        "cross_route_duplication": _cross_route_duplication(routes),
    }
    statuses = [c["status"] for c in checks.values()]
    if FAIL in statuses:
        status = FAIL
    elif PASS in statuses:
        status = PASS
    else:
        status = NOT_MEASURED

    return {
        "status": status,
        "schema": report.get("schema"),
        "routes_measured": len(routes),
        "routes": [r.get("route") for r in routes],
        "checks": checks,
        "findings_total": sum(len(c["findings"]) for c in checks.values()),
        "checks_not_measured": [n for n, c in checks.items() if c["status"] == NOT_MEASURED],
    }


def read_render_facts(report_path: Path | str) -> dict[str, Any]:
    """Load report.json and analyse it. A missing/unreadable file is NOT_MEASURED."""
    path = Path(report_path)
    if not path.exists():
        return {
            "status": NOT_MEASURED,
            "reason": f"no report.json at {path}",
            "routes_measured": 0,
            "checks": {name: _check(NOT_MEASURED, "no report.json") for name in CHECKS},
        }
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": NOT_MEASURED,
            "reason": f"report.json at {path} could not be read: {exc}",
            "routes_measured": 0,
            "checks": {name: _check(NOT_MEASURED, "unreadable report.json") for name in CHECKS},
        }
    result = analyse_render_facts(report)
    result["source"] = str(path)
    return result


def format_render_facts(result: dict) -> list[str]:
    """One line per check, for the build log. Says NOT_MEASURED out loud."""
    mark = {PASS: "✓", FAIL: "✖", NOT_MEASURED: "⊘"}
    lines = [
        f"  📐 Render facts: {result['status'].upper()} "
        f"({result.get('routes_measured', 0)} route(s), "
        f"{result.get('findings_total', 0)} finding(s))"
    ]
    for name, check in (result.get("checks") or {}).items():
        detail = ""
        if check["status"] == NOT_MEASURED:
            detail = f" — {check.get('reason', 'not measured')}"
        elif check["findings"]:
            detail = f" — {len(check['findings'])} finding(s)"
        lines.append(f"     {mark.get(check['status'], '?')} {name}: "
                     f"{check['status'].upper()}{detail}")
    return lines
