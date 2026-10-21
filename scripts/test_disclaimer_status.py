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

from lib.tenant_context import compliance_declaration  # noqa: E402
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


# A fourth state (2026-10-21, operator): THURIS's required_disclaimers were an
# `amendment` row with fill_status `needs_confirm` -- internal compliance notes
# that shipped verbatim in the footer. An unconfirmed declaration is not a
# declaration: it renders nothing, is reported as itself, and the compliance
# gate does not demand it on the page.

UNCONFIRMED = {"tenant_id": "x",
               "phase0_field_values": {"required_disclaimers": ["Internal note."]},
               "phase0_fill_status": {"required_disclaimers": "needs_confirm"}}


def test_needs_confirm_disclaimers_are_unconfirmed_and_never_rendered():
    assert declared_disclaimers(UNCONFIRMED) == ([], "unconfirmed")


def test_the_compliance_gate_does_not_require_unconfirmed_disclaimers():
    decl = compliance_declaration(UNCONFIRMED)
    assert decl["required_disclaimers"] == []
    assert decl["unconfirmed"] == ["required_disclaimers"]


def test_a_filled_declaration_still_renders():
    ctx = {**UNCONFIRMED, "phase0_fill_status": {"required_disclaimers": "filled"}}
    assert declared_disclaimers(ctx) == (["Internal note."], "declared")
    assert compliance_declaration(ctx)["required_disclaimers"] == ["Internal note."]
