"""There is exactly one platform vocabulary, and orchestrate.py imports it.

A1 could not edit orchestrate.py, so `TARGET_PLATFORMS`, `SOURCE_PLATFORMS` and
the declaration reader were written a second time in
`scripts/lib/tenant_context.py` behind a `TODO(A1-followup)`. Two copies of the
allowed set is how "shopify" becomes the default again: a platform added to one
list and not the other is refused by one resolver and accepted by the other,
and the disagreement surfaces as a build that silently picked the wrong
adapter.

These tests assert IDENTITY (`is`), not equality — two tuples that happen to
hold the same strings today are exactly the state this file exists to forbid.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


@pytest.fixture(scope="module")
def orch():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("orch_vocab", SCRIPTS / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch_vocab"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tenant_ctx():
    sys.path.insert(0, str(SCRIPTS))
    from lib import tenant_context

    return tenant_context


def test_target_platforms_is_the_same_object(orch, tenant_ctx):
    assert orch.TARGET_PLATFORMS is tenant_ctx.TARGET_PLATFORMS


def test_source_platforms_is_the_same_object(orch, tenant_ctx):
    assert orch.SOURCE_PLATFORMS is tenant_ctx.SOURCE_PLATFORMS


def test_the_refusal_is_the_same_exception_class(orch, tenant_ctx):
    """Two same-named exception classes means `except` silently misses one."""
    assert orch.PlatformNotDeclared is tenant_ctx.PlatformNotDeclared


def test_only_one_file_defines_the_vocabulary():
    """A grep-level guard: a future copy-paste re-introduces the defect.

    A LITERAL definition (`= (...)`) is the copy. An alias (`= module.NAME`) is
    a re-export of the one definition and is what the identity tests above pin.
    """
    literal = re.compile(r"^(TARGET|SOURCE)_PLATFORMS\s*=\s*\(", re.M)
    definers = []
    for path in sorted(SCRIPTS.rglob("*.py")):
        if path.name.startswith("test_"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if literal.search(text):
            definers.append(str(path.relative_to(ROOT)))
    assert definers == ["scripts/lib/tenant_context.py"], definers


def test_orchestrate_no_longer_carries_its_own_reader():
    text = (SCRIPTS / "orchestrate.py").read_text(encoding="utf-8")
    assert not re.search(r"^def _declared_platform", text, re.M), (
        "orchestrate.py still defines its own declaration reader"
    )


def test_resolver_signatures_are_unchanged(orch):
    """scripts/test_platform_resolution.py reaches the resolver through these."""
    import inspect

    for name in ("resolve_target_platform", "resolve_source_platform"):
        fn = getattr(orch, name)
        params = list(inspect.signature(fn).parameters)
        assert params == ["tenant_context"], (name, params)


def test_a_platform_added_to_the_vocabulary_is_visible_to_the_resolver(orch, tenant_ctx, monkeypatch):
    """The falsifiable core: one edit, both readers see it.

    With two copies this passed only for the copy that was edited.
    """
    extended = tenant_ctx.TARGET_PLATFORMS + ("netlify",)
    monkeypatch.setattr(tenant_ctx, "TARGET_PLATFORMS", extended)
    ctx = {
        "slug": "fixture",
        "available": True,
        "phase0_field_values": {"target_platform": "netlify"},
    }
    assert orch.resolve_target_platform(ctx) == "netlify"
