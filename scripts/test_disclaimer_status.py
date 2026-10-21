"""Footer disclaimers: three states, never collapsed.

Measured 2026-10-21 (thuris): a build run WITH --tenant printed "NO TENANT BOUND
(no --tenant)" because the tenant loaded but did not declare
`required_disclaimers`. "Nobody read the record", "the record does not declare
the field" and "the record declares these" are different facts; the first two
were one message, and that message named the wrong cause.

Run: `python3 -m pytest scripts/test_disclaimer_status.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrate import declared_disclaimers  # noqa: E402


def test_no_tenant_context_is_unbound():
    assert declared_disclaimers(None) == (None, "unbound")


def test_loaded_tenant_without_the_field_is_undeclared_not_unbound():
    ctx = {"tenant_id": "x", "phase0_field_values": {"trading_name": "T"}}
    assert declared_disclaimers(ctx) == (None, "undeclared")


def test_declared_list_is_returned_and_blank_entries_dropped():
    ctx = {"tenant_id": "x", "phase0_field_values": {"required_disclaimers": ["A", " ", "B"]}}
    assert declared_disclaimers(ctx) == (["A", "B"], "declared")


def test_declared_empty_list_is_declared_none():
    ctx = {"tenant_id": "x", "phase0_field_values": {"required_disclaimers": []}}
    assert declared_disclaimers(ctx) == ([], "declared")
