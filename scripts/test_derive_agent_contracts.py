#!/usr/bin/env python3
"""The AURELIX agent contracts must not claim capability nothing measured.

WHY
A contract is read by agents that will not check it. `agents/AURELIX.yaml` said
Aurelix was "owned by KIRA" and listed 9 capability tokens, none of which named
anything runnable, while the register held 55 measured instruments. Nothing
failed. These tests are what fails.

MUTATION RUNS 2026-08-19 (a test that cannot fail is not a test) — see the report
in the session transcript for the exact exit codes.

    python3 -m pytest scripts/test_derive_agent_contracts.py -v
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]          # services/aurelix-ag
GEN = ROOT / "scripts" / "derive_agent_contracts.py"
EXIT_NOT_MEASURED = 3


def _load_module():
    spec = importlib.util.spec_from_file_location("derive_agent_contracts", GEN)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    assert GEN.is_file(), f"{GEN} is missing"
    return _load_module()


@pytest.fixture(scope="module")
def contracts(mod):
    files = mod.contract_files()
    if not files:
        pytest.skip("control-tower not on this machine — NOT_MEASURED, not a pass")
    return files


@pytest.fixture(scope="module")
def register(mod):
    entries = mod.load_register()
    if entries is None:
        pytest.skip("no capability register — NOT_MEASURED, not a pass")
    return entries


def test_every_capability_token_is_grounded(contracts, register, mod):
    """A token names a measured instrument, or says BROKEN and shows the evidence."""
    ids = {str(e["id"]) for e in register}
    ungrounded = []
    for path in contracts:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for token in doc.get("capabilities") or []:
            token = str(token)
            if token.startswith("BROKEN:"):
                assert " — " in token, f"{path.name}: BROKEN token with no evidence: {token!r}"
                continue
            if token not in ids:
                ungrounded.append(f"{path.name}: {token}")
    assert not ungrounded, "capability tokens matching no instrument:\n  " + "\n  ".join(ungrounded)


def test_no_contract_wires_an_authority_that_does_not_exist(contracts, mod):
    """`called_by: [KIRA]` was the fiction. It may not come back through a hand edit."""
    offenders = []
    for path in contracts:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for field in mod.WIRING_FIELDS:
            for wired in doc.get(field) or []:
                if str(wired).strip().upper() in mod.FORBIDDEN_AUTHORITY:
                    offenders.append(f"{path.name}:{field} -> {wired}")
    assert not offenders, "unwired authority named in a wiring field: " + ", ".join(offenders)


def test_an_ownership_claim_must_retire_itself(mod):
    """The prose guard: asserting ownership fails, retiring the assertion passes."""
    asserted = "description: |\n  AURELIX is owned by KIRA and KIRA dispatches it.\n"
    problems = mod.validate(asserted, "T", set())
    assert any("asserts ownership" in p for p in problems), problems

    retired = ("description: |\n  The prior text said it was owned by KIRA. "
               "Nothing owns it; that claim named no call site.\n")
    assert not [p for p in mod.validate(retired, "T", set()) if "asserts ownership" in p]


def test_status_is_three_state_and_never_only_yes(mod):
    """An agent with no measured instrument cannot report operational."""
    by_agent = {
        "A-VERIFIED": [{"id": "x", "status": "VERIFIED", "kind": "gate"}],
        "A-NEVER-RUN": [{"id": "y", "status": "NOT_RUN", "kind": "gate"}],
    }
    assert mod.derive_status("A-VERIFIED", by_agent) == "operational"
    assert mod.derive_status("A-NEVER-RUN", by_agent) == "designed"
    assert mod.derive_status("A-ABSENT", by_agent) == "deprecated"


def test_the_broken_importer_is_marked_broken_not_working(contracts):
    """The measured case: 53 green tests, every subcommand raises ImportError."""
    path = next((p for p in contracts if p.stem == "AURELIX-BULK-IMPORTER"), None)
    if path is None:
        pytest.skip("AURELIX-BULK-IMPORTER.yaml absent")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tokens = [str(t) for t in doc.get("capabilities") or []]
    assert tokens, "the broken importer must keep a token — a deleted token and a "
    assert all(t.startswith("BROKEN:") for t in tokens), tokens
    assert doc.get("status") != "operational", "a CLI whose every subcommand raises is not operational"


def test_no_instrument_routes_to_two_agents(mod, register):
    """Routing must partition, or a token double-counts and the roll-up lies."""
    by_agent, unrouted = mod.routing(register)
    seen: dict[str, str] = {}
    for agent, group in by_agent.items():
        for e in group:
            ident = str(e["id"])
            assert ident not in seen, f"{ident} routes to both {seen[ident]} and {agent}"
            seen[ident] = agent
    assert len(seen) + len(unrouted) == len(register)


def test_the_rollup_is_the_union_of_the_parts(mod, register, contracts):
    """`AURELIX` must not be able to claim more, or less, than its workers hold."""
    by_agent, _ = mod.routing(register)
    rollup = set(mod.derive_capabilities(mod.ROLLUP_AGENT, by_agent))
    parts: set[str] = set()
    for path in contracts:
        if path.stem == mod.ROLLUP_AGENT:
            continue
        parts |= set(mod.derive_capabilities(path.stem, by_agent))
    assert rollup == parts, f"roll-up differs from its parts: {rollup ^ parts}"


def test_curated_fields_survive_a_derivation(mod, contracts, register):
    """Full generation would destroy these. The hybrid must not."""
    by_agent, _ = mod.routing(register)
    for path in contracts:
        original = path.read_text(encoding="utf-8")
        want = mod.derived_text(original, path.stem, by_agent)
        before = yaml.safe_load(original) or {}
        after = yaml.safe_load(want) or {}
        for field in ("apqc_node", "apqc_label", "layer", "industry_class",
                      "node_contract", "related_projects", "description", "calls"):
            assert before.get(field) == after.get(field), \
                f"{path.name}: derivation changed curated field {field}"
        assert "# pre-v7.4" in want, f"{path.name}: lost the apqc_node_legacy provenance comment"


def test_check_agrees_with_the_files_on_disk():
    """The drift gate itself. Three-state: 3 is NOT_MEASURED, never a pass."""
    proc = subprocess.run([sys.executable, str(GEN), "--check"],
                          cwd=ROOT, capture_output=True, text=True)
    if proc.returncode == EXIT_NOT_MEASURED:
        pytest.skip("register or contracts absent — NOT_MEASURED, not a pass")
    assert proc.returncode == 0, proc.stdout + proc.stderr
