#!/usr/bin/env python3
"""The supply register must not be able to under-report.

The register exists because demand without supply used to be invisible until a
build tripped over one pair and the pressure was to invent something. The way
that failure comes back is not a crash — it is a record quietly going missing
while the headline count still reads authoritative. So most of these tests
attack the balance between the summary and the records it summarises.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import supply_register as sr  # noqa: E402


@pytest.fixture()
def register():
    return sr.build_register(sr.load_demand(), sr.load_supply())


# ─── The measured state ───────────────────────────────────────────


def test_sources_are_version_controlled_and_present():
    assert sr.DEMAND_PATH.exists(), "demand must come from the tracked export"
    assert sr.SUPPLY_PATH.exists(), "supply must come from the tracked manifest"


def test_the_measured_twentyseven(register):
    """Measured 2026-08-18: 99 demanded, 76 supplied, 27 with no template.
    Reproduced live against section_archetypes (74 rows) — identical 27."""
    s = register["summary"]
    assert s["demanded_pairs"] == 99
    assert s["supplied_pairs"] == 76
    assert s["missing"] == 27


def test_every_record_names_a_cause_from_the_shared_vocabulary(register):
    allowed = {sr.CAUSE_ARCHETYPE_ABSENT, sr.CAUSE_VARIANT_MISSING}
    for rec in register["missing"]:
        assert rec["cause"] in allowed, rec


def test_every_record_names_who_demanded_it(register):
    """A pair with no attribution cannot be acted on — that is the whole point
    of counting it rather than gap-filling it."""
    for rec in register["missing"]:
        assert rec["demanded_by"], rec
        assert rec["page_types"], rec
        assert rec["industries"], rec
        assert rec["demand_rows"] >= 1, rec
        for d in rec["demanded_by"]:
            assert d["industry"] and d["page_type"], rec


def test_records_are_deterministically_ordered(register):
    pairs = [(r["archetype"], r["variant"]) for r in register["missing"]]
    assert pairs == sorted(pairs)


def test_no_missing_pair_is_also_supplied(register):
    supply = sr.load_supply()
    for rec in register["missing"]:
        assert rec["variant"] not in supply.get(rec["archetype"], set()), rec


# ─── Balance — the mutation the commit body records ───────────────


def test_dropping_a_record_silently_fails_the_balance(register):
    """THE mutation: remove one missing pair from the records and leave the
    summary claiming 27."""
    register["missing"].pop(5)
    with pytest.raises(AssertionError, match="summary.missing"):
        sr.assert_balanced(register)


def test_dropping_a_record_and_the_count_still_fails_on_cause_totals(register):
    """Covering the obvious cover-up: decrement the headline too. by_cause and
    the unsatisfiable-row total still do not add up."""
    register["missing"].pop(5)
    register["summary"]["missing"] -= 1
    with pytest.raises(AssertionError, match="by_cause"):
        sr.assert_balanced(register)


def test_a_fully_covered_deletion_still_fails_on_demand_rows(register):
    """And the thorough cover-up: fix missing AND by_cause AND
    archetypes_absent. The demand-row total is derived from the records, so it
    is the last thing that has to agree — and it does not."""
    rec = register["missing"].pop(5)
    register["summary"]["missing"] -= 1
    register["summary"]["by_cause"][rec["cause"]] -= 1
    register["summary"]["archetypes_absent"] = sorted(
        {r["archetype"] for r in register["missing"]
         if r["cause"] == sr.CAUSE_ARCHETYPE_ABSENT}
    )
    with pytest.raises(AssertionError, match="demand_rows"):
        sr.assert_balanced(register)


def test_the_untouched_register_balances(register):
    sr.assert_balanced(register)  # must not raise


def test_archetypes_absent_must_match_the_records(register):
    register["summary"]["archetypes_absent"] = []
    with pytest.raises(AssertionError, match="archetypes_absent"):
        sr.assert_balanced(register)


def test_a_record_cannot_claim_absence_and_list_variants(register):
    for rec in register["missing"]:
        if rec["cause"] == sr.CAUSE_ARCHETYPE_ABSENT:
            rec["variants_available"] = ["invented"]
            break
    with pytest.raises(AssertionError, match="claims the archetype is absent"):
        sr.assert_balanced(register)


def test_a_variant_gap_must_list_the_variants_that_do_exist(register):
    for rec in register["missing"]:
        if rec["cause"] == sr.CAUSE_VARIANT_MISSING:
            rec["variants_available"] = []
            break
    with pytest.raises(AssertionError, match="claims the archetype is present"):
        sr.assert_balanced(register)


# ─── Sensitivity: the register tracks the sources, not a constant ─


def test_adding_supply_removes_a_record():
    demand = sr.load_demand()
    supply = sr.load_supply()
    before = sr.build_register(demand, supply)
    gap = before["missing"][0]
    supply.setdefault(gap["archetype"], set()).add(gap["variant"])
    after = sr.build_register(demand, supply)
    assert after["summary"]["missing"] == before["summary"]["missing"] - 1


def test_adding_demand_for_an_unsupplied_pair_adds_a_record():
    demand = sr.load_demand()
    supply = sr.load_supply()
    before = sr.build_register(demand, supply)
    demand.append({
        "industry": "test-industry", "page_type": "homepage", "position": "1",
        "component_type": "page_section", "section_archetype": "NO-SUCH",
        "section_variant": "nope", "priority": "required",
        "content_direction": "", "template_path": "",
    })
    after = sr.build_register(demand, supply)
    assert after["summary"]["missing"] == before["summary"]["missing"] + 1
    rec = [r for r in after["missing"] if r["archetype"] == "NO-SUCH"][0]
    assert rec["cause"] == sr.CAUSE_ARCHETYPE_ABSENT
    assert rec["demanded_by"] == [{"industry": "test-industry", "page_type": "homepage"}]


# ─── A missing source is not an empty register ────────────────────


def test_missing_demand_source_raises_rather_than_reporting_zero(tmp_path, monkeypatch):
    """An empty register reads as 'the library is complete'. It must be
    impossible to produce one by losing a file."""
    monkeypatch.setattr(sr, "DEMAND_PATH", tmp_path / "gone.csv")
    with pytest.raises(sr.SourceMissing):
        sr.load_demand(sr.DEMAND_PATH)


def test_missing_supply_source_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(sr, "SUPPLY_PATH", tmp_path / "gone.json")
    with pytest.raises(sr.SourceMissing):
        sr.load_supply(sr.SUPPLY_PATH)


def test_empty_supply_manifest_raises(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"archetypes": {}}))
    with pytest.raises(sr.SourceMissing):
        sr.load_supply(p)


# ─── Build annotation is read-only and optional ───────────────────


def test_build_block_names_the_routes_that_demanded_an_unsupplied_pair():
    manifest = {
        "project": "t", "industry": "i",
        "pages": [
            {"route": "/", "sections": [{"archetype": "NO-SUCH", "variant": "nope"}]},
            {"route": "/x", "sections": [{"archetype": "NO-SUCH", "variant": "nope"}]},
        ],
    }
    reg = sr.build_register(sr.load_demand(), sr.load_supply(), manifest)
    b = reg["build"]
    assert b["pairs_unsupplied"] == 1
    assert b["unsupplied"][0]["routes"] == ["/", "/x"]
    assert b["unsupplied"][0]["in_registry_demand"] is False


def test_build_block_absent_when_no_manifest_given(register):
    assert "build" not in register


def test_emit_writes_a_balanced_register(tmp_path):
    out = tmp_path / "supply-register.json"
    reg = sr.emit_supply_register(out)
    assert out.exists()
    sr.assert_balanced(json.loads(out.read_text()))
    assert reg["summary"]["missing"] == 27


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
