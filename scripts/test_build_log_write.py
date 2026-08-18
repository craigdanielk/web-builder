"""
build_log write contract — measured against the LIVE schema.

Why this test is shaped this way: log_build() used to send two columns that do
not exist (`db_template_count`, `token_ledger`). Every insert 400'd with
PGRST204, the return value was unchecked at both call sites, and the build
exited 0 having recorded nothing. A test with a mocked HTTP layer would have
passed throughout — the mock has no schema. So:

  * the payload assertion compares against columns read from the live database
    (supabase_client.table_columns), not a hardcoded list, so it keeps working
    when the schema changes;
  * one test performs a REAL insert and deletes the row it created.

If the database is unreachable, every test here SKIPS. It must never pass on an
absent measurement.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from lib import supabase_client as sc  # noqa: E402

TABLE = "build_log"

# Database-assigned; log_build must never send these even though they exist.
_ASSIGNED_BY_DB = {"id", "build_timestamp"}


def _live_columns() -> set:
    """Live build_log columns, or skip the test when the database is unreachable."""
    try:
        cols = sc.table_columns(TABLE)
    except Exception as exc:  # transport, auth, or table gone
        pytest.skip(f"NOT_MEASURED: cannot read {TABLE} schema: {exc}")
    if not cols:
        pytest.skip(f"NOT_MEASURED: {TABLE} reported zero columns")
    return set(cols)


def _capture_payload(monkeypatch, **kwargs) -> dict:
    """Run log_build with the insert intercepted; return the row it would send."""
    captured = {}

    def fake_post(path, data):
        captured["path"] = path
        captured["row"] = data[0]
        return 201, [dict(data[0], id=-1)]

    monkeypatch.setattr(sc, "_post_returning", fake_post)
    base = dict(
        project_name="payload-shape-probe",
        industry="fintech",
        page_type="homepage",
        sections_from_template=3,
        sections_from_llm=0,
        total_sections=3,
    )
    base.update(kwargs)
    assert sc.log_build(**base) is True
    return captured["row"]


def test_payload_contains_only_real_columns(monkeypatch):
    """Every key log_build sends must be a column build_log actually has."""
    live = _live_columns()
    row = _capture_payload(
        monkeypatch,
        # Every optional parameter, so the widest possible payload is checked.
        build_duration_ms=1000,
        api_cost_usd=0.5,
        status="completed",
        target_platform="vercel",
        bos_line_items=5,
        sections_reconciled={"a": 1},
        tenant_id="cape-crypto",
        page_count=6,
        assets_bound=5,
        app_routes_scaffolded=2,
        deploy_url="https://example.invalid",
        harvested_copy_ratio=0.9,
        render_audit_status="passed",
        contrast_defect_count=0,
        broken_image_count=0,
        published_sha="deadbeef",
        # The two orphans. Accepted by the signature, never persisted.
        db_template_count=71,
        token_ledger={"input": 1, "output": 2},
    )
    unknown = sorted(set(row) - live)
    assert not unknown, f"log_build sends non-existent build_log column(s): {unknown}"


def test_payload_omits_the_two_orphan_fields(monkeypatch):
    """db_template_count and token_ledger have no column and must not be sent."""
    row = _capture_payload(monkeypatch, db_template_count=71, token_ledger={"i": 1})
    assert "db_template_count" not in row
    assert "token_ledger" not in row


def test_payload_omits_database_assigned_columns(monkeypatch):
    row = _capture_payload(monkeypatch)
    assert not (set(row) & _ASSIGNED_BY_DB)


def test_declared_allowlist_matches_the_live_schema():
    """_BUILD_LOG_COLUMNS must not drift from the database."""
    live = _live_columns()
    stale = sorted(sc._BUILD_LOG_COLUMNS - live)
    assert not stale, f"_BUILD_LOG_COLUMNS names columns that no longer exist: {stale}"
    missing = sorted(live - sc._BUILD_LOG_COLUMNS - _ASSIGNED_BY_DB)
    assert not missing, (
        f"build_log gained column(s) {missing}; add them to _BUILD_LOG_COLUMNS "
        "so log_build can persist them"
    )


def test_real_write_round_trip():
    """A REAL insert against the live database, read back, then cleaned up."""
    _live_columns()  # skips if unreachable
    project = f"test-build-log-write-{uuid.uuid4().hex[:12]}"
    filt = f"project_name=eq.{project}"
    try:
        ok = sc.log_build(
            project_name=project,
            industry="fintech",
            page_type="homepage",
            sections_from_template=3,
            db_template_count=71,
            sections_from_llm=0,
            total_sections=3,
            build_duration_ms=1234,
            status="completed",
            target_platform="vercel",
            token_ledger={"input": 10, "output": 20},
        )
        assert ok is True, f"log_build failed: {sc.LAST_BUILD_LOG_ERROR}"
        assert sc.LAST_BUILD_LOG_ERROR is None

        rows = sc._get(TABLE, f"{filt}&select=*")
        assert len(rows) == 1, f"expected exactly one row back, got {len(rows)}"
        assert rows[0]["total_sections"] == 3
        assert rows[0]["target_platform"] == "vercel"
        assert rows[0]["id"] is not None
    finally:
        sc._delete(TABLE, filt)

    assert sc._get(TABLE, f"{filt}&select=id") == [], "cleanup did not remove the row"


def test_failed_write_is_reported_and_does_not_raise(monkeypatch):
    """A write failure must return False, record the error, and not raise."""
    def boom(path, data):
        raise RuntimeError("simulated transport failure")

    monkeypatch.setattr(sc, "_post_returning", boom)
    result = sc.log_build(
        project_name="failure-probe", industry="fintech", page_type="homepage"
    )
    assert result is False
    assert sc.LAST_BUILD_LOG_ERROR is not None
    assert "simulated transport failure" in sc.LAST_BUILD_LOG_ERROR
    sc.LAST_BUILD_LOG_ERROR = None
