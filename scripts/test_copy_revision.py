"""Tests for the copy-verdict consumer on the TEMPLATE path.

Run from web-builder/:  python3 -m pytest scripts/test_copy_revision.py -v

What is actually under test here is an ACCOUNTING claim, not a transformation:
`lib/copy_revision.py` cannot revise copy (no candidate model exists in
`build_template_fill` — see that module's docstring), so the only thing it can
get wrong is the record. Two failure modes matter and each has a test that
fails when the guard is removed:

  * a verdict handed in and no row out — `DispositionAccountingError`, never a
    register that is self-consistent because the disagreeing row was dropped
  * a reason chosen by iteration order rather than by rule — two runs must
    produce byte-identical registers

Everything else is vocabulary containment: a reason or disposition outside the
closed sets must raise rather than ship.
"""

from __future__ import annotations

import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib import copy_revision as cr  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures — provenance rows in the exact shape build_template_fill emits
# ---------------------------------------------------------------------------

def prov(slot: str, source: str, reason: str = "") -> dict:
    """One `build_template_fill` provenance row.

    Measured shape (orchestrate.py::build_template_fill.record, 2026-08-17):
    `{section_uid, slot, value, source}` plus `reason` only when the value is
    empty, `pairing` only when it is sourced text.
    """
    row = {"section_uid": "hero-1", "slot": slot,
           "value": "" if source == "empty" else f"{slot}-value",
           "source": source}
    if reason:
        row["reason"] = reason
    return row


VERDICT = {
    "rule_id": "copy_generic_headline",
    "detail": "headline is generic",
    "severity": "high",
    "contributing_findings": ["0007:copy_generic_headline",
                              "0002:copy_generic_headline"],
}


def template(*rows: dict, **kw) -> dict:
    return cr.section_outcome("template", file="01-hero.tsx", archetype="HERO",
                              variant="split", provenance=list(rows), **kw)


# ---------------------------------------------------------------------------
# every reason in the closed vocabulary is reachable, at its documented rank
# ---------------------------------------------------------------------------

REASON_CASES = {
    "section-not-in-build": None,
    "section-generated-not-template-filled": cr.section_outcome(
        "generated", file="01-hero.tsx", archetype="HERO"),
    "section-omitted-from-build": cr.section_outcome(
        "omitted", file="01-hero.tsx", archetype="HERO",
        reason="harvest filled no slot", cause="harvest-miss"),
    "slot-empty-source-exhausted": template(
        prov("headline", "harvested"),
        prov("feature_2_title", "empty", "harvest-exhausted")),
    "slot-empty-no-harvest-supply": template(
        prov("headline", "harvested"),
        prov("stat_1_value", "empty", "no-harvest-supply")),
    "no-alternate-candidate": template(
        prov("headline", "harvested"), prov("subheadline", "harvested")),
}


@pytest.mark.parametrize("expected,outcome", sorted(
    REASON_CASES.items(), key=lambda kv: kv[0]))
def test_every_reason_is_reachable_and_named(expected, outcome):
    assert cr.reason_for(outcome) == expected


def test_the_case_table_covers_the_whole_vocabulary():
    """A reason nothing can produce is dead vocabulary; one with no test is
    worse. Fails the moment REASONS grows without a case."""
    assert sorted(REASON_CASES) == sorted(cr.REASONS)


def test_exhausted_outranks_no_supply_when_both_are_present():
    """Documented priority 4 before 5: "the harvest ran out" is the recoverable
    case, and naming it first is what makes the register a re-crawl backlog."""
    outcome = template(prov("headline", "harvested"),
                       prov("stat_1_value", "empty", "no-harvest-supply"),
                       prov("feature_2_title", "empty", "harvest-exhausted"))
    assert cr.reason_for(outcome) == "slot-empty-source-exhausted"


def test_a_section_with_nothing_sourced_is_a_harvest_problem():
    outcome = template(prov("headline", "empty", "harvest-exhausted"))
    assert cr.reason_for(outcome) == "slot-empty-source-exhausted"


def test_phase0_counts_as_filled():
    """`phase0` is a legal provenance source, produced when a section is
    composed from the tenant's declaration. Treating it as unfilled would
    report a well-sourced section as harvest-starved."""
    outcome = template(prov("required_disclaimer_1", "phase0"))
    assert cr.reason_for(outcome) == "no-alternate-candidate"


def test_every_reason_has_a_remedy():
    assert sorted(cr.REMEDY) == sorted(cr.REASONS)
    assert all(cr.REMEDY[r].strip() for r in cr.REASONS)


# ---------------------------------------------------------------------------
# the empty-slot verdict is recorded unactionable — never filled
# ---------------------------------------------------------------------------

def test_empty_slot_verdict_is_unactionable_and_fills_nothing():
    outcome = template(prov("headline", "harvested"),
                       prov("feature_2_title", "empty", "harvest-exhausted"))
    row = cr.disposition_for("hero-1", VERDICT, outcome)
    assert row["disposition"] == "unactionable"
    assert row["reason"] == "slot-empty-source-exhausted"
    assert row["remedy"] == cr.REMEDY["slot-empty-source-exhausted"]
    assert row["slots_filled"] == 1
    assert row["slots_empty"] == 1
    assert row["empty_slots_by_reason"] == {
        "harvest-exhausted": ["feature_2_title"]}
    # No copy in the record: this module never carries a replacement string,
    # because it has none to carry.
    assert "value" not in row and "revised_text" not in row


def test_no_verdict_is_ever_recorded_as_revised_in_this_build():
    rows = cr.compute_dispositions(
        {k: VERDICT for k in ("hero-1", "features-2", "cta-3")},
        {"hero-1": REASON_CASES["no-alternate-candidate"],
         "features-2": REASON_CASES["section-omitted-from-build"]})
    assert {r["disposition"] for r in rows} == {"unactionable"}
    assert cr.build_register({"home": rows})["summary"]["revised"] == 0


def test_revised_stays_declared_vocabulary():
    """Kept, not stubbed: a register whose schema cannot express success would
    quietly redefine "unactionable" as "everything"."""
    assert "revised" in cr.DISPOSITIONS


def test_a_disposition_outside_the_vocabulary_raises(monkeypatch):
    monkeypatch.setattr(cr, "REMEDY", dict(cr.REMEDY))
    monkeypatch.setattr(cr, "DISPOSITIONS", ("revised",))
    with pytest.raises(ValueError):
        cr.disposition_for("hero-1", VERDICT, None)


def test_an_unknown_outcome_kind_raises():
    with pytest.raises(ValueError):
        cr.section_outcome("llm")


# ---------------------------------------------------------------------------
# the counting invariant: a dropped verdict raises, it does not ship
# ---------------------------------------------------------------------------

def test_one_disposition_per_verdict_including_unactionable_ones():
    """THE invariant. Every verdict in this slice is unactionable, so a
    consumer that filtered unactionable rows out of the register would emit a
    file reporting fewer verdicts than it was handed — the exact defect class
    this repo keeps finding. Under that mutation compute_dispositions raises
    DispositionAccountingError and this test fails; it never passes quietly."""
    verdicts = {"hero-1": VERDICT, "features-2": VERDICT, "cta-3": VERDICT}
    rows = cr.compute_dispositions(verdicts, {
        "hero-1": REASON_CASES["no-alternate-candidate"],
        "features-2": REASON_CASES["section-omitted-from-build"]})
    assert len(rows) == len(verdicts)
    assert [r["slot"] for r in rows] == ["cta-3", "features-2", "hero-1"]
    assert all(r["disposition"] == "unactionable" for r in rows)


def test_dropping_a_row_raises_rather_than_writing_a_short_register(monkeypatch):
    """The guard itself, exercised by forcing the failure it exists to catch."""
    monkeypatch.setattr(cr, "disposition_for",
                        lambda slot, verdict, outcome: {"slot": "collapsed"})
    with pytest.raises(cr.DispositionAccountingError):
        cr.compute_dispositions({"hero-1": VERDICT, "cta-3": VERDICT}, {})


def test_a_malformed_verdict_still_gets_a_row():
    rows = cr.compute_dispositions({"hero-1": None, "cta-3": "not-a-dict"}, {})
    assert len(rows) == 2
    assert {r["rule_id"] for r in rows} == {"unspecified"}


def test_no_verdicts_is_an_empty_register_not_a_missing_one():
    assert cr.compute_dispositions(None, {}) == []
    doc = cr.build_register({"home": []})
    assert doc["summary"]["verdicts"] == 0
    assert doc["pages_covered"] == ["home"]


def test_summary_counts_agree_with_the_rows():
    rows = cr.compute_dispositions(
        {"hero-1": VERDICT, "features-2": VERDICT},
        {"hero-1": REASON_CASES["no-alternate-candidate"],
         "features-2": REASON_CASES["section-generated-not-template-filled"]})
    doc = cr.build_register({"home": rows})
    assert doc["summary"]["verdicts"] == doc["summary"]["dispositions"] == 2
    assert doc["summary"]["unactionable"] == 2
    assert doc["summary"]["by_reason"] == {
        "section-generated-not-template-filled": 1,
        "no-alternate-candidate": 1}
    assert sum(doc["summary"]["by_reason"].values()) == 2


def test_pages_covered_shows_coverage_not_just_consistency():
    doc = cr.build_register({"wealth": [], "home": []})
    assert doc["pages_covered"] == ["home", "wealth"]
    assert doc["schema"] == cr.SCHEMA


# ---------------------------------------------------------------------------
# determinism — two runs byte-identical
# ---------------------------------------------------------------------------

VERDICT_SLICE = {"hero-1": VERDICT, "features-2": VERDICT, "cta-3": VERDICT,
                 "absent-9": VERDICT}
OUTCOME_SLICE = {
    "hero-1": template(prov("subheadline", "harvested"),
                       prov("headline", "harvested"),
                       prov("stat_2_value", "empty", "no-harvest-supply"),
                       prov("stat_1_value", "empty", "no-harvest-supply")),
    "features-2": REASON_CASES["section-omitted-from-build"],
    "cta-3": REASON_CASES["section-generated-not-template-filled"],
}


def test_two_runs_are_byte_identical():
    a = json.dumps(cr.build_register({"home": cr.compute_dispositions(
        VERDICT_SLICE, OUTCOME_SLICE)}), indent=2)
    b = json.dumps(cr.build_register({"home": cr.compute_dispositions(
        VERDICT_SLICE, OUTCOME_SLICE)}), indent=2)
    assert a == b


def test_two_writes_produce_the_same_file_bytes(tmp_path):
    rows = cr.compute_dispositions(VERDICT_SLICE, OUTCOME_SLICE)
    cr.write_register(tmp_path, "home", rows)
    first = cr.register_path(tmp_path).read_bytes()
    cr.write_register(tmp_path, "home", rows)
    assert cr.register_path(tmp_path).read_bytes() == first


def test_empty_slot_lists_are_sorted_not_emission_ordered():
    rows = cr.compute_dispositions({"hero-1": VERDICT}, OUTCOME_SLICE)
    assert rows[0]["empty_slots_by_reason"] == {
        "no-harvest-supply": ["stat_1_value", "stat_2_value"]}
    assert rows[0]["contributing_findings"] == [
        "0002:copy_generic_headline", "0007:copy_generic_headline"]


def test_the_register_reads_back_as_json(tmp_path):
    cr.write_register(tmp_path, "home",
                      cr.compute_dispositions(VERDICT_SLICE, OUTCOME_SLICE))
    doc = json.loads(cr.register_path(tmp_path).read_text(encoding="utf-8"))
    assert doc["schema"] == cr.SCHEMA
    assert doc["by_page"]["home"]["summary"]["verdicts"] == 4
    assert len(doc["by_page"]["home"]["dispositions"]) == 4


def test_register_filename_matches_the_glob_cvr_loop_reads():
    """`cvr_loop.py::verdict_effect` globs `copy-manifest*.json` at the build
    root. The writer conforms to the reader, which is not edited here."""
    from fnmatch import fnmatch
    assert fnmatch(cr.register_path("/tmp/build").name, "copy-manifest*.json")


# ---------------------------------------------------------------------------
# the register is merged by page, and a corrupt one is rebuilt
# ---------------------------------------------------------------------------

def test_pages_merge_and_a_rerun_replaces_rather_than_appends(tmp_path):
    rows = cr.compute_dispositions({"hero-1": VERDICT}, OUTCOME_SLICE)
    cr.write_register(tmp_path, "home", rows)
    cr.write_register(tmp_path, "wealth", rows)
    doc = cr.write_register(tmp_path, "home", rows)
    assert doc["pages_covered"] == ["home", "wealth"]
    assert doc["summary"]["verdicts"] == 2          # 1 per page, not 3
    assert len(doc["by_page"]["home"]["dispositions"]) == 1


def test_a_corrupt_register_is_rebuilt_not_appended_to(tmp_path):
    cr.register_path(tmp_path).write_text("{not json at all",
                                          encoding="utf-8")
    rows = cr.compute_dispositions({"hero-1": VERDICT}, OUTCOME_SLICE)
    doc = cr.write_register(tmp_path, "home", rows)
    assert doc["pages_covered"] == ["home"]
    assert doc["summary"]["verdicts"] == 1
    assert json.loads(cr.register_path(tmp_path).read_text(
        encoding="utf-8"))["by_page"]["home"]["summary"]["verdicts"] == 1


def test_a_register_with_a_junk_by_page_is_rebuilt(tmp_path):
    cr.register_path(tmp_path).write_text(
        json.dumps({"by_page": {"wealth": "not-a-dict"}}), encoding="utf-8")
    doc = cr.write_register(tmp_path, "home",
                            cr.compute_dispositions({"hero-1": VERDICT},
                                                    OUTCOME_SLICE))
    assert doc["pages_covered"] == ["home"]


def test_write_register_creates_the_build_root(tmp_path):
    target = tmp_path / "does" / "not" / "exist"
    cr.write_register(target, "home", [])
    assert cr.register_path(target).exists()


# ---------------------------------------------------------------------------
# provenance vocabulary is read, never rewritten
# ---------------------------------------------------------------------------

def test_provenance_vocabulary_is_untouched():
    """The module reads `harvested | phase0 | empty` and the two empty reasons
    build_template_fill writes. It must add no source of its own — `default` is
    rejected by SectionArtifact.validate() and must stay unproducible."""
    assert set(cr._EMPTY_REASON_TO_DISPOSITION) == {"harvest-exhausted",
                                                    "no-harvest-supply"}
    rows = [prov("headline", "harvested"), prov("cta_text", "empty",
                                                "harvest-exhausted")]
    before = copy.deepcopy(rows)
    outcome = template(*rows)
    cr.disposition_for("hero-1", VERDICT, outcome)
    assert rows == before
    assert outcome["provenance"] == before


def test_a_default_sourced_row_is_not_counted_as_filled():
    """If a `default` row ever appears, it must not be laundered into evidence
    that the slot was sourced."""
    outcome = template(prov("headline", "default"))
    assert cr.reason_for(outcome) == "slot-empty-source-exhausted"
    row = cr.disposition_for("hero-1", VERDICT, outcome)
    assert row["slots_filled"] == 0


def test_an_unknown_empty_reason_is_recorded_not_silently_dropped():
    outcome = template(prov("headline", "harvested"),
                       prov("mystery", "empty"))
    row = cr.disposition_for("hero-1", VERDICT, outcome)
    assert row["empty_slots_by_reason"] == {"unspecified": ["mystery"]}
    assert row["reason"] == "no-alternate-candidate"
    assert row["slots_empty"] == 1


def test_the_build_reason_travels_with_an_omission():
    row = cr.disposition_for("features-2", VERDICT,
                             REASON_CASES["section-omitted-from-build"])
    assert row["build_reason"] == "harvest filled no slot"
    assert row["build_cause"] == "harvest-miss"
    assert row["section_kind"] == "omitted"


def test_an_absent_section_says_absent():
    row = cr.disposition_for("nowhere-9", VERDICT, None)
    assert row["section_kind"] == "absent"
    assert row["reason"] == "section-not-in-build"
    assert row["file"] == "" and row["archetype"] == ""
