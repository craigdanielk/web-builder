#!/usr/bin/env python3
"""The capability register's own tests.

WHAT THESE GUARD
----------------
The register is only worth having if it CANNOT quietly go stale, and if a
declaration cannot claim more than it earned. So the tests that matter are the
refusals: an empty `cannot_see`, an instrument grading itself, a register that
disagrees with the source, a status of VERIFIED with no execution behind it.

Mutation runs recorded 2026-08-18 (standing rule: a test that cannot fail is not
a test) — both against the real gates, not fixtures:

    MUTATION 1  changed `cost` in compile-gate.js's declaration
                compile --check → exit 1, "~ aurelix.gate.compile.cost changed"
    MUTATION 2  emptied `cannot_see` in conformance-gate.js
                node conformance-gate.js --describe → exit 3 (the gate refuses
                to run at all), compile --check → exit 1
    RESTORED    compile --check → exit 0

Run: python3 -m pytest scripts/test_capability_register.py -v
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from capability_register import (  # noqa: E402
    build_entries,
    check_register,
    derive_status,
    register_payload,
)
from lib.capability import COMPILER_OWNED, REQUIRED, CapabilityInvalid, validate  # noqa: E402

ROOT = SCRIPTS.parent
REGISTER = ROOT / "registry" / "capability-register.yaml"

VALID = {
    "id": "aurelix.gate.example",
    "name": "Example gate",
    "kind": "gate",
    "invocation": "node scripts/quality/example-gate.js --build-dir <dir>",
    "preconditions": ["a production build"],
    "inputs": ["the built site"],
    "outputs": ["example.json"],
    "outcome": "whether the example conforms",
    "exit_contract": {0: "PASS", 1: "FAIL", 3: "NOT_MEASURED"},
    "measures": ["the example"],
    "cannot_see": ["everything that is not the example"],
    "reachable_from": [],
    "cost": "~1s",
}


def _without(field: str) -> dict:
    spec = copy.deepcopy(VALID)
    spec.pop(field)
    return spec


# ── the declaration contract ──────────────────────────────────────────────

def test_a_valid_declaration_passes():
    assert validate(copy.deepcopy(VALID)) is not None


@pytest.mark.parametrize("field", REQUIRED)
def test_every_required_field_is_actually_required(field):
    """No field is quietly optional. Drop any one and the declaration is refused."""
    with pytest.raises(CapabilityInvalid) as exc:
        validate(_without(field))
    assert f"`{field}`" in str(exc.value)


def test_empty_cannot_see_is_refused():
    """The field the whole register turns on.

    An instrument that believes it sees everything is wrong, and two instruments
    that look redundant are how a gate gets deleted. There is no escape value.
    """
    spec = copy.deepcopy(VALID)
    spec["cannot_see"] = []
    with pytest.raises(CapabilityInvalid) as exc:
        validate(spec)
    assert "cannot_see" in str(exc.value)


@pytest.mark.parametrize("field", sorted(COMPILER_OWNED))
def test_an_instrument_may_not_grade_itself(field):
    """`status`, `evidence`, `source_file` and `language` are the compiler's."""
    spec = copy.deepcopy(VALID)
    spec[field] = "VERIFIED"
    with pytest.raises(CapabilityInvalid) as exc:
        validate(spec)
    assert field in str(exc.value)


def test_unknown_kind_is_refused():
    spec = copy.deepcopy(VALID)
    spec["kind"] = "thingamajig"
    with pytest.raises(CapabilityInvalid):
        validate(spec)


def test_malformed_id_is_refused():
    spec = copy.deepcopy(VALID)
    spec["id"] = "Not A Dotted Id"
    with pytest.raises(CapabilityInvalid):
        validate(spec)


def test_empty_exit_contract_is_refused():
    """Every instrument returns something. A gate with no declared codes is a
    gate whose NOT_MEASURED is indistinguishable from its PASS."""
    spec = copy.deepcopy(VALID)
    spec["exit_contract"] = {}
    with pytest.raises(CapabilityInvalid):
        validate(spec)


def test_all_problems_are_reported_at_once():
    """A validator that stops at the first problem turns one fix into five trips."""
    spec = copy.deepcopy(VALID)
    del spec["cost"]
    del spec["measures"]
    spec["kind"] = "nonsense"
    with pytest.raises(CapabilityInvalid) as exc:
        validate(spec)
    text = str(exc.value)
    assert "`cost`" in text and "`measures`" in text and "nonsense" in text


# ── status is earned, never declared ──────────────────────────────────────

def test_no_evidence_means_not_verified():
    status, why = derive_status(VALID, [])
    assert status == "NOT_VERIFIED"
    assert "never run" in why


def test_a_run_in_contract_earns_verified():
    status, why = derive_status(
        VALID, [{"id": VALID["id"], "argv": "node scripts/quality/example-gate.js --build-dir x", "exit": 1}]
    )
    assert status == "VERIFIED"
    assert "exit 1" in why


def test_an_exit_code_outside_the_contract_is_broken():
    """The declaration said 0/1/3. A 2 means the contract is wrong, the tool is
    wrong, or both — and none of those is 'working'."""
    status, why = derive_status(
        VALID, [{"id": VALID["id"], "argv": "node scripts/quality/example-gate.js --build-dir x", "exit": 2}]
    )
    assert status == "BROKEN"
    assert "exit_contract does not admit" in why


def test_evidence_for_a_different_script_does_not_verify():
    """Running some OTHER tool cannot verify this one."""
    status, _ = derive_status(
        VALID, [{"id": VALID["id"], "argv": "node scripts/quality/something-else.js", "exit": 0}]
    )
    assert status == "NOT_VERIFIED"


def test_not_run_carries_its_reason():
    status, why = derive_status(VALID, [{"id": VALID["id"], "not_run": "mutates a live Shopify store"}])
    assert status == "NOT_RUN"
    assert "live Shopify store" in why


# ── the anti-rot gate ─────────────────────────────────────────────────────

def test_register_payload_is_deterministic():
    """An unchanged toolbox must compile to identical bytes, or --check becomes
    noise and gets switched off. Same reasoning as benchmarks/index.json."""
    entries = [dict(VALID, status="NOT_VERIFIED", evidence="declared, never run",
                    source_file="x.js", language="js")]
    assert register_payload(entries) == register_payload(entries)


def test_register_carries_no_timestamp():
    payload = register_payload([dict(VALID, status="NOT_VERIFIED", evidence="x",
                                     source_file="x.js", language="js")])
    assert not re.search(r"\d{4}-\d{2}-\d{2}T|generated_at|timestamp", payload)


def test_check_detects_a_changed_declaration(tmp_path):
    base = [dict(VALID, status="NOT_VERIFIED", evidence="declared, never run",
                 source_file="x.js", language="js")]
    path = tmp_path / "capability-register.yaml"
    path.write_text(register_payload(base), encoding="utf-8")
    assert check_register(base, path)[0] is True

    changed = copy.deepcopy(base)
    changed[0]["cost"] = "~90s"
    agrees, detail = check_register(changed, path)
    assert agrees is False
    assert "cost changed" in detail


def test_check_detects_a_new_instrument(tmp_path):
    base = [dict(VALID, status="NOT_VERIFIED", evidence="x", source_file="x.js", language="js")]
    path = tmp_path / "capability-register.yaml"
    path.write_text(register_payload(base), encoding="utf-8")
    added = base + [dict(VALID, id="aurelix.gate.newcomer", status="NOT_VERIFIED",
                         evidence="x", source_file="y.js", language="js")]
    agrees, detail = check_register(added, path)
    assert agrees is False
    assert "aurelix.gate.newcomer" in detail and "absent from the register" in detail


def test_a_missing_register_is_a_disagreement_not_a_crash(tmp_path):
    agrees, detail = check_register([], tmp_path / "nope.yaml")
    assert agrees is False
    assert "does not exist" in detail


# ── the two validators may not drift ──────────────────────────────────────

def test_js_and_python_declare_the_same_required_fields():
    """`capability.js` fails fast at the instrument; `capability.py` is
    authoritative at compile. If they disagree, an instrument passes its own
    check and is refused by the compiler — or worse, the reverse."""
    js = (SCRIPTS / "quality" / "lib" / "capability.js").read_text(encoding="utf-8")
    block = re.search(r"const REQUIRED = \[(.*?)\];", js, re.S)
    assert block, "REQUIRED not found in capability.js"
    js_fields = re.findall(r"'([a-z_]+)'", block.group(1))
    assert js_fields == list(REQUIRED)


def test_js_and_python_declare_the_same_kinds():
    from lib.capability import KINDS
    js = (SCRIPTS / "quality" / "lib" / "capability.js").read_text(encoding="utf-8")
    block = re.search(r"const KINDS = new Set\(\[(.*?)\]\);", js, re.S)
    assert block, "KINDS not found in capability.js"
    assert set(re.findall(r"'([a-z]+)'", block.group(1))) == set(KINDS)


# ── the real instruments, not fixtures ────────────────────────────────────

def test_the_committed_register_agrees_with_the_instruments():
    """The anti-rot gate itself. This is the test that fails when someone changes
    a flag and forgets to recompile."""
    entries, problems = build_entries(_declaring_files(), _evidence())
    assert not problems, "declarations refused:\n" + "\n".join(problems)
    agrees, detail = check_register(entries, REGISTER)
    assert agrees, detail


def test_every_registered_instrument_declares_a_blindness():
    import yaml
    if not REGISTER.exists():
        pytest.skip("register not compiled yet")
    doc = yaml.safe_load(REGISTER.read_text(encoding="utf-8")) or {}
    for entry in doc.get("capabilities") or []:
        if entry.get("status") == "BROKEN" and "cannot_see" not in entry:
            continue  # an unloadable file has no declaration to read
        assert entry.get("cannot_see"), f"{entry.get('id')} declares no blindness"


def _declaring_files():
    from capability_register import candidate_files
    return candidate_files()


def _evidence():
    from capability_register import load_evidence
    return load_evidence()
