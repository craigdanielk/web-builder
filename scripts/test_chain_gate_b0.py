#!/usr/bin/env python3
"""Gate B-0 must be ON the shopify chain, BEFORE layer4, and OFF the vercel chain.

WHY THIS TEST EXISTS
--------------------
`shopify-integration-layer/verify_gate_b0.py` was written, tested and never
called — measured 2026-08-18: zero references across `run_pipeline.py`,
`web-builder/scripts/` and its own directory. Meanwhile `stage_layer4` runs
`layer4_store_setup.py`, which creates smart collections, products,
Headless-channel publications, menus and redirects on a LIVE store with no
rollback. The chain performed an irreversible mutation with its pre-flight check
bypassed, and nothing failed when it did. That is what this file guards.

The ORDER assertion is the whole point. A `gate_b0` that exists somewhere in the
chain but after `layer4` is not a pre-flight check — it is a post-mortem — and a
membership test alone would pass on it.

The vercel assertion guards the other half of the rule: a stage that cannot
apply must be ABSENT from the chain, never skipped-with-a-warning, because a
skipped stage in a status list reads as passed. A storefront-less tenant has no
Admin API to check.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHAIN_PATH = REPO_ROOT / "run_pipeline.py"


def _load_chain():
    """Import the repo-root chain module without polluting sys.path.

    `run_pipeline.py` lives one repo up from this submodule and inserts its own
    root on sys.path at import time; both repos ship a top-level `lib`, so this
    loads it by file location rather than by name resolution.
    """
    spec = importlib.util.spec_from_file_location("aurelix_run_pipeline", CHAIN_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def chain_mod():
    if not CHAIN_PATH.exists():
        pytest.skip(f"NOT_MEASURED: {CHAIN_PATH} not found")
    return _load_chain()


def _names(stages) -> list:
    return [s["name"] for s in stages]


def test_shopify_chain_contains_gate_b0(chain_mod):
    names = _names(chain_mod.select_chain("shopify"))
    assert "gate_b0" in names, (
        "The shopify chain has no gate_b0. layer4 mutates a live store "
        f"irreversibly and its pre-flight check is unwired. Chain: {names}"
    )


def test_gate_b0_runs_before_layer4(chain_mod):
    """A pre-flight check after the mutation is a post-mortem."""
    for kwargs in (
        {},
        {"from_url": True},
        {"with_media": True},
        {"with_products": False},
        {"from_url": True, "with_media": True, "with_products": False},
    ):
        names = _names(chain_mod.select_chain("shopify", **kwargs))
        assert "gate_b0" in names and "layer4" in names, (
            f"select_chain('shopify', **{kwargs}) lost a stage: {names}"
        )
        assert names.index("gate_b0") < names.index("layer4"), (
            f"gate_b0 runs AFTER layer4 with **{kwargs} — the store is already "
            f"mutated by then. Chain: {names}"
        )


def test_gate_b0_is_declared_a_gate(chain_mod):
    """Its verdict must reach handle_gate, not the plain-stage branch.

    A `kind='step'` stage treats exit 1 as a stage failure rather than a gate
    failure and never lands in `failed_gates`.
    """
    stage = next(s for s in chain_mod.select_chain("shopify") if s["name"] == "gate_b0")
    assert stage["kind"] == "gate", (
        f"gate_b0 is declared kind={stage['kind']!r}; a gate's verdict must go "
        "through handle_gate's three-state mapping"
    )


def test_vercel_chain_does_not_contain_gate_b0(chain_mod):
    names = _names(chain_mod.select_chain("vercel"))
    assert "gate_b0" not in names, (
        "The vercel chain gained gate_b0. A storefront-less tenant has no Admin "
        f"API to check, and a stage that cannot apply must be absent. Chain: {names}"
    )


def test_gate_b0_is_a_valid_stop_for_shopify_only(chain_mod):
    """STOPS_BY_PLATFORM is derived from the chain — verify it actually derived."""
    assert "gate_b0" in chain_mod.STOPS_BY_PLATFORM["shopify"], (
        "gate_b0 is not a --stop-at value for shopify, so an operator cannot "
        "stop the chain immediately before the irreversible stage. Stops: "
        f"{chain_mod.STOPS_BY_PLATFORM['shopify']}"
    )
    assert "gate_b0" not in chain_mod.STOPS_BY_PLATFORM["vercel"], (
        "gate_b0 is offered as a vercel stop for a stage the vercel chain does "
        f"not contain. Stops: {chain_mod.STOPS_BY_PLATFORM['vercel']}"
    )


def test_missing_credential_is_not_measured_not_fail(chain_mod, monkeypatch, caplog):
    """No credential ⇒ exit 3, which --continue-on-gate-failure cannot override.

    FAIL (1) is overridable and the very next stage has no undo, so a chain that
    could not ask the store anything must not be arguable into asking it to
    mutate. See the docstring on `stage_gate_b0`.
    """
    for key in ("SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_ACCESS_TOKEN", "SHOPIFY_STORE_DOMAIN"):
        monkeypatch.delenv(key, raising=False)

    class _Ctx:
        class logger:
            @staticmethod
            def error(*a, **k):
                pass

    code = chain_mod.stage_gate_b0(_Ctx())
    assert code == chain_mod.GATE_NOT_MEASURED, (
        f"stage_gate_b0 returned {code} with no credential in the environment; "
        "expected 3 (NOT_MEASURED). Exit 1 would be overridable with "
        "--continue-on-gate-failure, straight into an irreversible live-store "
        "mutation."
    )


def test_describe_declares_the_chain(chain_mod):
    """The capability declaration must exist and name this chain."""
    cap = chain_mod.CAPABILITY
    assert cap["id"] == "aurelix.harness.pipeline-chain"
    assert cap["kind"] == "harness"
    assert cap["cannot_see"], "`cannot_see` may not be empty"
    for owned in ("status", "evidence", "source_file", "language"):
        assert owned not in cap, f"`{owned}` is compiler-owned and may not be declared"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
