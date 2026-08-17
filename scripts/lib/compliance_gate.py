"""Build-time compliance gate.

Cape Crypto is FSCA-licensed (FSP No. 53746). A prohibited claim or a dropped
disclosure in generated copy is a regulatory liability, not a styling defect —
so it must be able to STOP a build. The scanner
(`tenant_context.scan_prohibited_terms`) and the footer rendering
(`stage_shared_components`) both already exist. What was missing, until this
module, is that neither could fail anything: repo-wide grep on 2026-08-17
found zero production callers of `assert_no_prohibited_terms`.

WHAT IS CHECKED
───────────────
1. **Prohibited terms** — every phrase the tenant declared in
   `phase0_field_values.prohibited_terms` must be absent from generated markup
   AND from harvested copy. A violation names the term, the file and the line.
2. **Required disclaimers** — every string in
   `phase0_field_values.required_disclaimers` must appear verbatim in the
   generated site.

WHAT IS DELIBERATELY NOT CHECKED
────────────────────────────────
- `prohibited_language` ("financial advice framing", "urgency/FOMO pressure
  tactics") names a rhetorical posture, not a string. Matching it literally
  would flag nothing real while implying a check that is not happening. It is
  surfaced in the result for human/LLM copy review and never enforced — the
  same decision `tenant_context.py:157-161` records.
- **Per-route reachability.** This gate proves a disclaimer is present in the
  generated tree, not that every route renders it. In the current build the
  disclaimers live in `Footer.tsx`, which the root `layout.tsx` mounts, so
  presence does imply every route — but that is a property of this build's
  shape, not something measured here. Claiming per-route coverage without
  walking the import graph would be a gate that says more than it knows.

THREE OUTCOMES, NOT TWO
───────────────────────
`load_tenant_context` never raises: `_safe_get` swallows every error and
returns `[]` (`tenant_context.py:58-67`), so an unreachable Supabase, a dropped
table and a genuinely empty tenant are indistinguishable. A gate that read "no
prohibited terms declared" off a dead database and printed PASS would be the
worst failure this system can produce. **No declaration loaded ⇒ NOT_MEASURED
(exit 3), never PASS.** Likewise a missing or empty site directory: there is
nothing to measure, so nothing is asserted.

A tenant that declares `prohibited_terms: []` while declaring disclaimers or a
regulator (xago) has made a real, empty declaration — that is a PASS, not a
NOT_MEASURED.

COMMENTS ARE NOT MARKUP
───────────────────────
Section templates document the copy rules they follow, in prose, in the file.
A comment reading "never promise guaranteed returns" is the rule being obeyed,
not broken. Commit `a95d7128` fixed exactly this class of false positive for
asset scanning; the same `_mask_comments` is reused here, and it cuts both
ways — a disclaimer that appears ONLY inside a comment does not count as
present.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import shape depends on how the package is loaded
    from .asset_resolver import _mask_comments
    from .tenant_context import (
        compliance_declaration,
        load_tenant_context,
        scan_prohibited_terms,
    )
except ImportError:  # fallback when imported as a top-level module
    from asset_resolver import _mask_comments  # type: ignore
    from tenant_context import (  # type: ignore
        compliance_declaration,
        load_tenant_context,
        scan_prohibited_terms,
    )


#: Generated text worth scanning. Everything the pipeline emits as copy is
#: JSX/TS; `.md`/`.mdx` are included because a content route could be either.
SCAN_EXTS = {".tsx", ".ts", ".jsx", ".js", ".mdx", ".md"}

#: Never this build's own copy.
SKIP_DIRS = {"node_modules", ".next", ".git", "dist", "build", ".turbo",
             "__pycache__", ".vercel"}

#: Where harvested slot values are written, relative to the site directory's
#: parent (`output/<project>/section-artifacts/<page>/<section>.json`).
ARTIFACTS_DIRNAME = "section-artifacts"


class ComplianceFailure(RuntimeError):
    """A build carries banned copy, or is missing declared disclosure text.

    Carries the full gate result on `.result` so a caller that catches it does
    not have to re-parse the message.
    """

    def __init__(self, message: str, result: dict[str, Any]):
        super().__init__(message)
        self.result = result


# ─── Helpers ──────────────────────────────────────────────────────

def _line_of(text: str, offset: int) -> int:
    """1-based line number of `offset` in `text`."""
    return text.count("\n", 0, offset) + 1


def _presence_pattern(phrase: str) -> re.Pattern:
    """Whitespace-flexible verbatim match for a declared disclaimer.

    JSX wraps long strings across lines, so "…is an authorised\\n financial
    services provider…" is the same disclosure as the single-line form. Every
    other character is matched exactly: this is verbatim disclosure text and
    a near-miss is not a match.
    """
    return re.compile(r"\s+".join(re.escape(w) for w in phrase.split()))


def _generated_files(site_dir: Path) -> list[Path]:
    """Every generated source file under `site_dir` worth scanning."""
    root = site_dir / "src" if (site_dir / "src").is_dir() else site_dir
    out = []
    for p in sorted(root.rglob("*")):
        if p.suffix not in SCAN_EXTS or not p.is_file():
            continue
        if SKIP_DIRS & set(p.relative_to(root).parts):
            continue
        out.append(p)
    return out


def _harvested_values(artifacts_dir: Path) -> list[tuple[str, int, str, str]]:
    """`(origin, line, slot, value)` for every harvested slot value on disk.

    Only `source == "harvested"` entries are returned: a slot recorded empty
    carries no copy, and a phase-0 value is the tenant's own declaration.
    """
    out: list[tuple[str, int, str, str]] = []
    if not artifacts_dir.is_dir():
        return out
    for p in sorted(artifacts_dir.rglob("*.json")):
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw)
        except (OSError, ValueError):
            continue
        for entry in (data or {}).get("provenance") or []:
            if not isinstance(entry, dict) or entry.get("source") != "harvested":
                continue
            value = entry.get("value")
            slot = entry.get("slot") or "<unnamed slot>"
            if not isinstance(value, str) or not value.strip():
                continue
            idx = raw.find(json.dumps(value))
            line = _line_of(raw, idx) if idx >= 0 else 0
            out.append((str(p), line, slot, value))
    return out


def _not_measured(reason: str, tenant, decl) -> dict[str, Any]:
    return {
        "status": "not_measured",
        "reason": reason,
        "tenant": tenant,
        "violations": [],
        "missing_disclaimers": [],
        "allowed_negated": [],
        "prohibited_language": (decl or {}).get("prohibited_language", []),
        "prohibited_terms_declared": len((decl or {}).get("prohibited_terms", [])),
        "required_disclaimers_declared": len(
            (decl or {}).get("required_disclaimers", [])),
        "files_scanned": 0,
        "harvested_values_scanned": 0,
    }


# ─── The gate ─────────────────────────────────────────────────────

def compliance_gate(
    site_dir,
    tenant: str | None = None,
    *,
    tenant_context: dict | None = None,
    artifacts_dir=None,
    raise_on_fail: bool = True,
) -> dict[str, Any]:
    """Check a generated site against its tenant's declared regulatory position.

    Parameters
    ----------
    site_dir
        The generated Next.js app (``output/<project>/site``). Its `src/` tree
        is scanned when present, otherwise the whole directory.
    tenant
        Tenant coordinate (slug or UUID). ``None`` ⇒ NOT_MEASURED.
    tenant_context
        A pre-loaded context, to avoid a second Supabase round-trip (and to
        let tests be hermetic). When omitted, `load_tenant_context(tenant)`.
    artifacts_dir
        Harvested provenance directory. Defaults to
        ``site_dir.parent / "section-artifacts"``.
    raise_on_fail
        Raise `ComplianceFailure` on a FAIL verdict (default). The verdict is
        identical either way; only the delivery differs. NOT_MEASURED never
        raises — it is a third outcome, not a soft failure.

    Returns
    -------
    dict with ``status`` ∈ {"pass", "fail", "not_measured"},
    ``violations`` (each ``{term, file, line, excerpt, origin}``),
    ``missing_disclaimers``, ``allowed_negated``, and the declaration counts.
    """
    site_dir = Path(site_dir)
    if artifacts_dir is None:
        artifacts_dir = site_dir.parent / ARTIFACTS_DIRNAME
    artifacts_dir = Path(artifacts_dir)

    # ── 1. The declaration. Absent ⇒ NOT_MEASURED, never PASS.
    if tenant_context is None:
        if not tenant:
            return _not_measured(
                "no tenant coordinate — pass --tenant <slug>. A site whose "
                "regulatory declaration was never loaded has not been checked, "
                "and 'no prohibited terms found' would be a statement about a "
                "record nobody opened.",
                tenant, None)
        tenant_context = load_tenant_context(tenant)

    decl = compliance_declaration(tenant_context)
    slug = (tenant_context or {}).get("slug") or tenant or "<unknown tenant>"

    if not decl["declared"]:
        return _not_measured(
            f"tenant '{slug}' loaded no compliance declaration — no "
            "required_disclaimers, no prohibited_terms, no licence or "
            "regulator. load_tenant_context never raises, so this is "
            "indistinguishable from an unreachable Supabase or a dropped "
            "table. NOT_MEASURED, not PASS.",
            slug, decl)

    # ── 2. Something to measure.
    if not site_dir.is_dir():
        return _not_measured(
            f"site directory does not exist: {site_dir}", slug, decl)

    files = _generated_files(site_dir)
    if not files:
        return _not_measured(
            f"no generated source files under {site_dir} — nothing was built, "
            "so nothing was checked.", slug, decl)

    terms = decl["prohibited_terms"]
    disclaimers = decl["required_disclaimers"]

    violations: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    disclaimers_seen: set[int] = set()

    # ── 3. Generated markup.
    for path in files:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Masking is length-preserving, so offsets stay true against `raw`.
        masked = _mask_comments(raw)

        for i, phrase in enumerate(disclaimers):
            if i not in disclaimers_seen and _presence_pattern(phrase).search(masked):
                disclaimers_seen.add(i)

        for hit in scan_prohibited_terms(masked, terms, exempt=disclaimers):
            record = {
                "term": hit["term"],
                "file": str(path),
                "line": _line_of(raw, hit["start"]),
                "excerpt": hit["excerpt"],
                "origin": "generated",
                "match": hit["match"],
            }
            (allowed if hit["negated"] else violations).append(record)

    # ── 4. Harvested copy. Scanned separately because it is text, not markup:
    #     it has no comments, and it is where a source site's own phrasing
    #     enters the build unedited.
    harvested = _harvested_values(artifacts_dir)
    for origin_file, line, slot, value in harvested:
        for hit in scan_prohibited_terms(value, terms, exempt=disclaimers):
            record = {
                "term": hit["term"],
                "file": f"{origin_file}:{slot}",
                "line": line,
                "excerpt": hit["excerpt"],
                "origin": "harvested",
                "slot": slot,
                "match": hit["match"],
            }
            (allowed if hit["negated"] else violations).append(record)

    missing = [d for i, d in enumerate(disclaimers) if i not in disclaimers_seen]

    result: dict[str, Any] = {
        "status": "fail" if (violations or missing) else "pass",
        "reason": "",
        "tenant": slug,
        "violations": violations,
        "missing_disclaimers": missing,
        "allowed_negated": allowed,
        "prohibited_language": decl["prohibited_language"],
        "prohibited_terms_declared": len(terms),
        "required_disclaimers_declared": len(disclaimers),
        "files_scanned": len(files),
        "harvested_values_scanned": len(harvested),
    }

    if result["status"] == "fail" and raise_on_fail:
        raise ComplianceFailure(_failure_message(result), result)
    return result


def _failure_message(result: dict[str, Any]) -> str:
    lines = [
        f"COMPLIANCE GATE FAIL — tenant '{result['tenant']}'",
    ]
    if result["violations"]:
        lines.append(
            f"\n{len(result['violations'])} prohibited-term occurrence(s) "
            f"(of {result['prohibited_terms_declared']} declared term(s)):"
        )
        for v in result["violations"]:
            lines.append(f"  {v['file']}:{v['line']}  {v['term']!r}"
                         f"  [{v['origin']}]\n      …{v['excerpt']}…")
    if result["missing_disclaimers"]:
        lines.append(
            f"\n{len(result['missing_disclaimers'])} required disclaimer(s) "
            "absent from the generated site:"
        )
        for d in result["missing_disclaimers"]:
            lines.append(f"  MISSING: {d}")
    lines.append(
        "\nThese are declared regulatory constraints, not style preferences. "
        "Fix the copy at source (the harvest or the template) and render the "
        "declared disclosure verbatim — the declaration is not the thing to edit."
    )
    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────

def main(argv=None) -> int:
    """Exit 0 = PASS, 1 = FAIL, 3 = NOT_MEASURED."""
    ap = argparse.ArgumentParser(
        description="Fail a build that ships banned copy or drops a declared "
                    "disclosure. Exit 0 pass / 1 fail / 3 not measured.")
    ap.add_argument("--site", required=True, help="output/<project>/site")
    ap.add_argument("--tenant", default=None, help="tenant slug or UUID")
    ap.add_argument("--artifacts", default=None,
                    help="section-artifacts dir (default: <site>/../section-artifacts)")
    ap.add_argument("--json", action="store_true", help="emit the result as JSON")
    args = ap.parse_args(argv)

    try:
        result = compliance_gate(args.site, args.tenant,
                                 artifacts_dir=args.artifacts,
                                 raise_on_fail=False)
    except Exception as exc:  # a crash is not a pass
        print(f"COMPLIANCE GATE: NOT_MEASURED — gate itself failed: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(result, indent=2))

    status = result["status"]
    if status == "not_measured":
        print(f"COMPLIANCE GATE: NOT_MEASURED — {result['reason']}", file=sys.stderr)
        return 3
    if status == "fail":
        print(_failure_message(result), file=sys.stderr)
        return 1

    print(f"COMPLIANCE GATE: PASS — tenant '{result['tenant']}', "
          f"{result['prohibited_terms_declared']} prohibited term(s) and "
          f"{result['required_disclaimers_declared']} required disclaimer(s) "
          f"checked against {result['files_scanned']} generated file(s) and "
          f"{result['harvested_values_scanned']} harvested value(s); "
          f"{len(result['allowed_negated'])} negated occurrence(s) allowed.")
    if result["prohibited_language"]:
        print("  NOT machine-checked (human/LLM copy review): "
              + " · ".join(result["prohibited_language"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
