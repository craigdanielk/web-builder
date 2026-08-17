"""What a copy verdict can and cannot do on the TEMPLATE path.

K1 (`scripts/quality/findings-to-verdicts.py`) compiles audit findings into
verdicts. K3 (`scripts/cvr_loop.py`) drives a build with them. K3's first real
run measured the hole this module fills:

    `--copy-findings` is consumed at exactly ONE site in orchestrate.py — inside
    the LLM section-generation branch — and a deterministic build resolves every
    section from a template and makes 0 LLM calls, so the branch never runs. The
    verdicts were loaded into nothing.

This module is the consumer on the path a deterministic build actually takes.


WHAT "REVISE FROM SOURCE" COULD MEAN HERE, AND WHY IT DOES NOT MEAN IT YET
─────────────────────────────────────────────────────────────────────────
The content rule is *sourced or empty, never invented*, so deterministically a
verdict cannot rewrite a slot — the only legal move is to RE-SELECT: skip the
incumbent harvested string and take the next-best one.

That requires a candidate set. **There is none.** Measured in
`orchestrate.py::build_template_fill` (2026-08-17): every slot value is produced
by exactly one of three functions — `scalar()`, `grouped_value()`,
`positional_value()` — and each returns a single string read from a *fixed
index* into a harvest list:

  * `scalar("headline")`      -> `section_title`, i.e. `sect_headings[0]`
  * `grouped_value(n, field)` -> field `field` of `items[n-1]`, and nothing else
                                 can fill it: item n's heading is item n's only
                                 heading
  * `positional_value(n, f)`  -> `headings[n]` / `item_bodies[n-1]` / `ctas[n]`

No ranked set is ever constructed, no alternates are carried, and no ordering
over candidates exists to be "next" in. Latent unused strings do exist for a
few section-level scalars (`sect_headings[1:]` is read by nothing on the grouped
path; `sect_bodies[1:]` is read only by `section_body_2`), but promoting one of
those to "next-best" would be a candidate model *invented here*, with an
ordering nothing in the harvest justifies. That is out of scope by instruction
and would be worse than the gap: it would make the pipeline substitute copy on a
licensed FSP's site on the strength of a rule an agent made up.

So `revised` is declared vocabulary and is **unreachable in this build**. It is
kept, not stubbed, because the day a candidate model lands the recording path
should not need rewriting — and because a disposition file whose schema cannot
express success would quietly redefine "unactionable" as "everything".


WHAT THIS MODULE DOES DO
────────────────────────
It makes the verdicts' fate *recorded* instead of *inert*. Every verdict handed
to a page gets exactly one disposition, written to a build-root register that
matches the glob `copy-manifest*.json` that `cvr_loop.py::verdict_effect`
already reads.

    dispositions == verdicts in scope

is enforced, not reported: `compute_dispositions` raises
`DispositionAccountingError` rather than emitting a register that has silently
dropped a verdict. A verdict that vanishes from the register is the exact defect
class this repo keeps finding — a count that only ever agrees because the
disagreeing rows were never written.

Reason selection is a strict, documented priority (first match wins), so two
runs over the same build produce the same reason for the same verdict:

  1. `section-not-in-build`                 no section with this uid on this page
  2. `section-generated-not-template-filled` the section exists but the generation
                                             path wrote it; that path's own
                                             consumer owns the verdict
  3. `section-omitted-from-build`            the section was dropped (harvest
                                             filled no slot / no template)
  4. `slot-empty-source-exhausted`           emitted, but >=1 slot is empty
                                             because the harvest ran out. Remedy
                                             is a new harvest, not a verdict
  5. `slot-empty-no-harvest-supply`          emitted, but >=1 slot is empty
                                             because the harvest never carries
                                             that KIND of value (a price, a
                                             date, an icon name). Remedy is a
                                             phase-0 declaration
  6. `no-alternate-candidate`                emitted and every slot filled — the
                                             verdict is well-targeted and
                                             re-selection is what is missing

4 outranks 5 because "the harvest ran out" is the recoverable case and naming it
first is what makes the register a re-crawl backlog. 6 is last because it is the
only reason that indicts this pipeline rather than its inputs.

SCOPE OF THE INVARIANT. `stage_sections` receives ONE page's slice of the
verdicts, so the invariant is per-slice and the register records which page keys
it covered. A verdict addressed to a page the manifest does not build never
reaches this module at all; `pages_covered` is what lets a reader see that gap
instead of reading a self-consistent register as full coverage.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "aurelix.copy_revision.v1"

#: Closed disposition vocabulary. `revised` is unreachable in this build — see
#: the module docstring — and is validated rather than removed.
DISPOSITIONS = ("revised", "unactionable")

#: Closed reason vocabulary, in the strict priority order documented above.
#: Order is load-bearing: `reason_for` returns the FIRST match.
REASONS = (
    "section-not-in-build",
    "section-generated-not-template-filled",
    "section-omitted-from-build",
    "slot-empty-source-exhausted",
    "slot-empty-no-harvest-supply",
    "no-alternate-candidate",
)

#: What would have to change for the verdict to become actionable. Closed, and
#: paired 1:1 with a reason so the register is a backlog rather than a tally.
REMEDY = {
    "section-not-in-build": "a section with this uid on this page",
    "section-generated-not-template-filled": "the generation path's own consumer",
    "section-omitted-from-build": "a template for this archetype, or a harvest "
                                  "that fills a slot",
    "slot-empty-source-exhausted": "a new harvest carrying more source strings",
    "slot-empty-no-harvest-supply": "a phase-0 declaration for this field",
    "no-alternate-candidate": "a candidate model in build_template_fill",
}

#: Outcome kinds a build can report for one section. `template` is the only kind
#: whose provenance rows are read.
OUTCOME_KINDS = ("template", "omitted", "generated")

#: `provenance[].reason` values written by `build_template_fill` for an empty
#: slot, mapped to the disposition reason each one implies.
_EMPTY_REASON_TO_DISPOSITION = {
    "harvest-exhausted": "slot-empty-source-exhausted",
    "no-harvest-supply": "slot-empty-no-harvest-supply",
}


class DispositionAccountingError(Exception):
    """A verdict was handed in and no disposition came out (or vice versa)."""


def section_outcome(
    kind: str,
    *,
    file: str = "",
    archetype: str = "",
    variant: str = "",
    provenance: list[dict] | None = None,
    reason: str = "",
    cause: str = "",
) -> dict:
    """One section's fate, as the build knows it at the moment it decides.

    `provenance` is the exact list `build_template_fill` returned for the
    section — `{section_uid, slot, value, source, reason?}` rows. Only the
    `template` kind uses it; the others carry the build's own omission reason.
    """
    if kind not in OUTCOME_KINDS:
        raise ValueError(f"unknown outcome kind {kind!r}; expected one of {OUTCOME_KINDS}")
    return {
        "kind": kind,
        "file": file,
        "archetype": archetype,
        "variant": variant,
        "provenance": list(provenance or []),
        "build_reason": reason,
        "build_cause": cause,
    }


def _empty_slots(provenance: list[dict]) -> dict[str, list[str]]:
    """Empty slot names grouped by the fill reason, each list sorted.

    Sorted because the register is compared byte-for-byte across two runs; the
    provenance list's own order is emission order and is stable, but sorting
    removes the question.
    """
    out: dict[str, list[str]] = {}
    for row in provenance:
        if row.get("source") != "empty":
            continue
        out.setdefault(str(row.get("reason") or "unspecified"), []).append(
            str(row.get("slot") or "")
        )
    return {k: sorted(v) for k, v in sorted(out.items())}


def reason_for(outcome: dict | None) -> str:
    """The single disposition reason for a verdict against `outcome`.

    First match in `REASONS` order wins. `None` means the build reported no
    section with the verdict's uid on this page.
    """
    if outcome is None:
        return "section-not-in-build"
    kind = outcome.get("kind")
    if kind == "generated":
        return "section-generated-not-template-filled"
    if kind == "omitted":
        return "section-omitted-from-build"

    empty = _empty_slots(outcome.get("provenance") or [])
    filled = [r for r in (outcome.get("provenance") or [])
              if r.get("source") in ("harvested", "phase0")]
    if not filled:
        # Emitted with nothing sourced at all. `omit_section` normally catches
        # this, so reaching here means a template with zero declared slots or a
        # coverage decision that let it through — either way the harvest is the
        # thing that is missing, not the selection.
        return "slot-empty-source-exhausted"
    for fill_reason, disposition_reason in (
        ("harvest-exhausted", "slot-empty-source-exhausted"),
        ("no-harvest-supply", "slot-empty-no-harvest-supply"),
    ):
        if empty.get(fill_reason):
            return disposition_reason
    return "no-alternate-candidate"


def disposition_for(slot_key: str, verdict: dict, outcome: dict | None) -> dict:
    """One record: what happened to one verdict, and what would unblock it."""
    reason = reason_for(outcome)
    empty = _empty_slots((outcome or {}).get("provenance") or [])
    filled = sorted(
        str(r.get("slot") or "") for r in ((outcome or {}).get("provenance") or [])
        if r.get("source") in ("harvested", "phase0")
    )
    record = {
        "slot": slot_key,
        "rule_id": str(verdict.get("rule_id") or verdict.get("id") or "unspecified"),
        # `unactionable` for every reason in this build: no candidate model
        # exists, so nothing can be re-selected. See the module docstring.
        "disposition": "unactionable",
        "reason": reason,
        "remedy": REMEDY[reason],
        "section_kind": (outcome or {}).get("kind") or "absent",
        "file": (outcome or {}).get("file") or "",
        "archetype": (outcome or {}).get("archetype") or "",
        "slots_filled": len(filled),
        "slots_empty": sum(len(v) for v in empty.values()),
        "empty_slots_by_reason": empty,
        "contributing_findings": sorted(verdict.get("contributing_findings") or []),
    }
    build_reason = (outcome or {}).get("build_reason") or ""
    if build_reason:
        record["build_reason"] = build_reason
    build_cause = (outcome or {}).get("build_cause") or ""
    if build_cause:
        record["build_cause"] = build_cause
    if record["disposition"] not in DISPOSITIONS:
        raise ValueError(f"disposition {record['disposition']!r} outside {DISPOSITIONS}")
    if record["reason"] not in REASONS:
        raise ValueError(f"reason {record['reason']!r} outside {REASONS}")
    return record


def compute_dispositions(verdicts: dict | None, outcomes: dict) -> list[dict]:
    """One disposition per verdict in `verdicts`, sorted by slot key.

    `verdicts` is ONE page's slice: `{slot_key: verdict}` where `slot_key` is the
    section uid K1 placed the finding at. `outcomes` is `{section_uid: outcome}`
    as the build recorded it.

    Raises `DispositionAccountingError` unless exactly one disposition came out
    per verdict that went in. Every non-mapping verdict still gets a record — a
    malformed verdict is a measured fact, not a licence to drop a row.
    """
    rows = [
        disposition_for(
            str(slot_key),
            verdict if isinstance(verdict, dict) else {},
            outcomes.get(str(slot_key)),
        )
        for slot_key, verdict in sorted((verdicts or {}).items(), key=lambda kv: str(kv[0]))
    ]
    expected = len(verdicts or {})
    if len(rows) != expected:
        raise DispositionAccountingError(
            f"{expected} verdict(s) in, {len(rows)} disposition(s) out"
        )
    if len({r["slot"] for r in rows}) != expected:
        raise DispositionAccountingError(
            f"{expected} verdict(s) in, {len({r['slot'] for r in rows})} distinct slot(s) out"
        )
    return rows


def _summarise(rows: list[dict]) -> dict:
    return {
        "verdicts": len(rows),
        "dispositions": len(rows),
        "revised": sum(1 for r in rows if r["disposition"] == "revised"),
        "unactionable": sum(1 for r in rows if r["disposition"] == "unactionable"),
        "by_reason": {
            reason: sum(1 for r in rows if r["reason"] == reason)
            for reason in REASONS
            if any(r["reason"] == reason for r in rows)
        },
    }


def build_register(by_page: dict[str, list[dict]]) -> dict:
    """The whole-build register document. Deterministic: every key sorted."""
    ordered = {page: rows for page, rows in sorted(by_page.items())}
    flat = [r for rows in ordered.values() for r in rows]
    return {
        "schema": SCHEMA,
        # Named so a reader can tell coverage from consistency: the invariant
        # below holds within each page, and a verdict addressed to a page absent
        # from this list never reached the consumer at all.
        "pages_covered": sorted(ordered),
        "summary": {
            **_summarise(flat),
            "note": (
                "disposition 'revised' is unreachable in this build: template "
                "slot fill is 1:1 with the harvest and carries no candidate "
                "set, so a verdict has no next-best string to re-select. See "
                "lib/copy_revision.py."
            ),
        },
        "by_page": {
            page: {"summary": _summarise(rows), "dispositions": rows}
            for page, rows in ordered.items()
        },
    }


def register_path(build_dir: Path) -> Path:
    """Where the register lives.

    Named to match the `copy-manifest*.json` glob `cvr_loop.py::verdict_effect`
    already searches the build root for — that function is the reader and is not
    edited by this task, so the writer conforms to it rather than the reverse.
    """
    return Path(build_dir) / "copy-manifest-verdicts.json"


def write_register(build_dir: Path, page_key: str, rows: list[dict]) -> dict:
    """Merge this page's dispositions into the build-root register.

    Idempotent by page, like `omitted-sections.json`: this page's rows REPLACE
    any previous rows for the same page rather than appending. Re-running a page
    is the documented way three other counters in this pipeline inflated.
    """
    path = register_path(build_dir)
    by_page: dict[str, list[dict]] = {}
    if path.exists():
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            for page, entry in (prev.get("by_page") or {}).items():
                if page != page_key and isinstance(entry, dict):
                    by_page[page] = list(entry.get("dispositions") or [])
        except Exception:
            by_page = {}  # a corrupt register is rebuilt, never appended to
    by_page[page_key] = rows
    doc = build_register(by_page)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return doc
