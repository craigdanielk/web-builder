#!/usr/bin/env python3
"""The section_presets export must fail loudly when it stops matching the table.

A stale export is worse than none: it is a library entry that looks
authoritative and is not. So every assertion here is written to fail on a
*divergence*, and the divergence is manufactured in-process — no test depends
on the network being down, and none depends on it being up.

Two layers, matching the two ways the export can rot:

  offline  the file drifted from itself (hand-edited, re-sorted, a row dropped,
           the meta bumped without re-exporting). Always runs.
  live     the file drifted from the table. The comparison logic is exercised
           against a stubbed fetch so it is deterministic; the real network run
           is the CLI's `verify --live`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import export_section_presets as ex  # noqa: E402


# ─── The tracked artefact ─────────────────────────────────────────


def test_export_and_meta_exist():
    assert ex.EXPORT_PATH.exists(), f"no export at {ex.EXPORT_PATH}"
    assert ex.META_PATH.exists(), f"no meta at {ex.META_PATH}"


def test_offline_verify_passes_on_the_tracked_export():
    ok, problems = ex.verify_offline()
    assert ok, f"tracked export is not self-consistent: {problems}"


def test_export_holds_the_measured_row_count():
    """995 measured live on 2026-08-18. If the table legitimately grew, the
    number changes here AND in the export in the same commit — which is the
    point: the count becomes a reviewable fact rather than a surprise."""
    rows, _ = ex.read_export()
    meta = json.loads(ex.META_PATH.read_text())
    assert len(rows) == 995
    assert meta["row_count"] == 995


def test_export_carries_no_timestamp_columns():
    """Timestamps would churn the diff on every reseed while recording nothing
    about what the store decided."""
    _, text = ex.read_export()
    header = text.splitlines()[0]
    for banned in ("created_at", "updated_at", "id"):
        assert banned not in header.split(","), f"{banned} leaked into the export"


def test_sort_key_is_a_total_order_over_the_export():
    rows, _ = ex.read_export()
    keys = [tuple(r[c] for c in ex.SORT_KEY) for r in rows]
    assert len(set(keys)) == len(keys), "sort key does not uniquely order the rows"


def test_render_is_byte_stable():
    """Re-rendering the parsed export reproduces it byte for byte, or the file
    is not re-derivable and the hash means nothing."""
    rows, text = ex.read_export()
    assert ex.render_csv(ex.sort_rows(rows)) == text


# ─── Offline divergence — the mutation the commit body records ────


def _tamper(tmp_path, monkeypatch, mutate):
    """Copy export + meta into tmp, apply `mutate(text) -> text`, point the
    module at the copy."""
    csv_copy = tmp_path / "section_presets.csv"
    meta_copy = tmp_path / "section_presets.meta.json"
    csv_copy.write_text(mutate(ex.EXPORT_PATH.read_text()))
    meta_copy.write_text(ex.META_PATH.read_text())
    monkeypatch.setattr(ex, "EXPORT_PATH", csv_copy)
    monkeypatch.setattr(ex, "META_PATH", meta_copy)


def test_offline_verify_fails_when_one_row_is_edited(tmp_path, monkeypatch):
    """THE mutation: change a single field in a single row."""

    def mutate(text):
        lines = text.splitlines(keepends=True)
        lines[1] = lines[1].replace("required", "optional", 1)
        return "".join(lines)

    _tamper(tmp_path, monkeypatch, mutate)
    ok, problems = ex.verify_offline()
    assert not ok
    assert any("content hash" in p for p in problems), problems


def test_offline_verify_fails_when_a_row_is_dropped(tmp_path, monkeypatch):
    def mutate(text):
        lines = text.splitlines(keepends=True)
        return "".join(lines[:1] + lines[2:])

    _tamper(tmp_path, monkeypatch, mutate)
    ok, problems = ex.verify_offline()
    assert not ok
    assert any("row count" in p for p in problems), problems


def test_offline_verify_fails_when_rows_are_reordered(tmp_path, monkeypatch):
    def mutate(text):
        lines = text.splitlines(keepends=True)
        body = list(reversed(lines[1:]))
        return "".join(lines[:1] + body)

    _tamper(tmp_path, monkeypatch, mutate)
    ok, problems = ex.verify_offline()
    assert not ok
    assert any("not sorted" in p for p in problems), problems


def test_offline_verify_fails_when_the_header_changes(tmp_path, monkeypatch):
    def mutate(text):
        lines = text.splitlines(keepends=True)
        lines[0] = lines[0].replace("priority", "prio", 1)
        return "".join(lines)

    _tamper(tmp_path, monkeypatch, mutate)
    ok, problems = ex.verify_offline()
    assert not ok
    assert any("header" in p for p in problems), problems


# ─── Live divergence, deterministically ───────────────────────────


def _raw_rows_from_export():
    """The export, shaped like raw Supabase rows, so a stubbed fetch can
    return it."""
    rows, _ = ex.read_export()
    return [dict(r, id=i, created_at="x", updated_at="x") for i, r in enumerate(rows)]


def test_live_verify_passes_when_the_table_matches(monkeypatch):
    monkeypatch.setattr(ex, "_fetch_live_rows", _raw_rows_from_export)
    ok, problems = ex.verify_live()
    assert ok, problems


def test_live_verify_fails_when_the_table_has_a_row_the_export_lacks(monkeypatch):
    def fetch():
        raw = _raw_rows_from_export()
        extra = dict(raw[0], industry="zzz-new-industry", id=99999)
        return raw + [extra]

    monkeypatch.setattr(ex, "_fetch_live_rows", fetch)
    ok, problems = ex.verify_live()
    assert not ok
    assert any("row count diverged" in p for p in problems), problems
    assert any("in table, not in export" in p for p in problems), problems


def test_live_verify_fails_when_a_row_changed_in_place(monkeypatch):
    """Same row count, different content — the case a count check alone misses,
    which is why the contract is count AND hash."""

    def fetch():
        raw = _raw_rows_from_export()
        raw[0] = dict(raw[0], content_direction="edited in the table")
        return raw

    monkeypatch.setattr(ex, "_fetch_live_rows", fetch)
    ok, problems = ex.verify_live()
    assert not ok
    assert any("content diverged" in p for p in problems), problems
    assert not any("row count diverged" in p for p in problems), problems


def test_live_verify_fails_when_the_table_lost_rows(monkeypatch):
    def fetch():
        return _raw_rows_from_export()[:-5]

    monkeypatch.setattr(ex, "_fetch_live_rows", fetch)
    ok, problems = ex.verify_live()
    assert not ok
    assert any("-5" in p for p in problems), problems


# ─── Three-state honesty ──────────────────────────────────────────


def test_unreachable_supabase_is_not_measured_not_pass(monkeypatch, capsys):
    def boom():
        raise ex.NotMeasured("simulated outage")

    monkeypatch.setattr(ex, "_fetch_live_rows", boom)
    code = ex.cmd_verify(type("A", (), {"live": True})())
    assert code == ex.EXIT_NOT_MEASURED
    assert "NOT_MEASURED" in capsys.readouterr().out


def test_verify_without_live_does_not_claim_the_table_was_checked(capsys):
    code = ex.cmd_verify(type("A", (), {"live": False})())
    assert code == ex.EXIT_OK
    out = capsys.readouterr().out
    assert "NOT_MEASURED" in out, "a skipped live check must say so, not read as a pass"


def test_module_has_no_supabase_write_path():
    """READ-ONLY by contract. A POST/PATCH/DELETE appearing here would let a
    verify command mutate the store it is supposed to be auditing."""
    src = Path(ex.__file__).read_text()
    for verb in ('method="POST"', 'method="PATCH"', 'method="DELETE"', 'method="PUT"'):
        assert verb not in src, f"write path {verb} present in a read-only exporter"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
