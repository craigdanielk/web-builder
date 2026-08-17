#!/usr/bin/env python3
"""
Platform resolution — a resolver that cannot return a second value is not a
resolver.

WHY THIS EXISTS
---------------
`resolve_target_platform` queried `tenants.deploy_target`. That column does not
exist. The query raised HTTPError 400, a bare `except Exception: pass` swallowed
it, and the function returned "shopify". Every input shape — None, empty dict,
bogus id, and a tenant that declares it is explicitly NOT an e-commerce
merchant — produced the same answer, indistinguishable from a real resolution.
Fixed in 06266458.

Platform is COLLECTED, never inferred. Deriving it from `tech_stack` prose is
forbidden by the plan (Task 0.1) for the same reason fuzzy benchmark matching
is: a guess that looks like a decision.

The four failures that used to be one answer are now distinct:
  no context / no declaration / unknown value  -> refuse, naming which
  a declared value                             -> that value

WHAT THIS FILE GUARDS
---------------------
Both historical shapes of the defect must be caught:
  1. the body collapsing to `return "shopify"`, and
  2. the refusal path collapsing to `except Exception: return "shopify"`.
Every refusal assertion below therefore checks that the call RAISED — never
merely that it "did not return vercel", which a silent default would satisfy.

The previous version of this file was a hand-rolled runner: its `test()` helper
took positional args (pytest read them as missing fixtures) and its three
`test_*` aggregators recorded failures into a module-global counter that only
`main()` ever read. Under pytest they passed unconditionally, whatever the
resolver did. Coverage is preserved here as real assertions.

These tests reach the resolver only through the public functions
`resolve_target_platform` / `resolve_source_platform`, never through the
`TARGET_PLATFORMS` / `SOURCE_PLATFORMS` / `_declared_platform` internals, so
moving those into `scripts/lib/tenant_context.py` does not break this file.

Run: cd web-builder && python3 -m pytest scripts/test_platform_resolution.py -v
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

#: Sentinel distinguishing "the resolver returned x" from "the resolver raised".
RETURNED = "RETURNED"


def _load_orchestrate():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("orch", ROOT / "scripts" / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def orch():
    return _load_orchestrate()


@pytest.fixture(scope="module")
def resolve_target(orch):
    fn = getattr(orch, "resolve_target_platform", None)
    assert fn is not None, "orchestrate.py exposes no resolve_target_platform"
    return fn


@pytest.fixture(scope="module")
def resolve_source(orch):
    fn = getattr(orch, "resolve_source_platform", None)
    assert fn is not None, "orchestrate.py exposes no resolve_source_platform"
    return fn


def ctx(**phase0):
    """A tenant context shaped like lib.tenant_context.load_tenant_context."""
    return {
        "tenant_id": "ad98688a-c384-4785-8d96-12544a13cfa7",
        "slug": "cape-crypto",
        "available": True,
        "phase0_field_values": dict(phase0),
    }


def outcome(fn, argument):
    """Return ("RETURNED", value) or ("RAISED", message).

    The distinction is the entire point: a silent default and a refusal both
    fail an `!= "vercel"` assertion, so every guard below must be able to tell
    them apart.
    """
    try:
        value = fn(argument)
    except SystemExit as exc:  # an explicit abort is a refusal too
        return ("RAISED", str(exc))
    except Exception as exc:  # noqa: BLE001 — any explicit refusal
        return ("RAISED", f"{type(exc).__name__}: {exc}")
    return (RETURNED, value)


def assert_refuses(fn, argument, *must_mention):
    """Assert fn RAISED on `argument`, and that the message names each fragment."""
    kind, payload = outcome(fn, argument)
    assert kind == "RAISED", (
        "resolver answered instead of refusing: returned {!r} for {!r}. "
        "This is the historical defect — an undeclared input must raise, not "
        "fall back to a platform.".format(payload, argument)
    )
    lowered = payload.lower()
    for fragment in must_mention:
        assert fragment.lower() in lowered, (
            "refusal did not name {!r}; message was: {}".format(fragment, payload)
        )
    return payload


# --------------------------------------------------------------------------
# Inputs that must NOT produce a platform.
#
# These four shapes are the original defect verbatim: each one returned
# "shopify" before 06266458. The last is a tenant whose own phase-0 record says
# it is not an e-commerce merchant — the case where answering "shopify" is not
# merely unhelpful but wrong.
# --------------------------------------------------------------------------

UNDECLARED_SHAPES = [
    pytest.param(None, id="none"),
    pytest.param({}, id="empty-dict"),
    pytest.param({"phase0_field_values": {}}, id="empty-phase0"),
    pytest.param({"tenant_id": "nope"}, id="bogus-tenant-id"),
    pytest.param(
        ctx(is_ecommerce_merchant=False, business_model="licensed FSP, no storefront"),
        id="declared-not-a-merchant",
    ),
    pytest.param(ctx(target_platform=None), id="explicit-null"),
    pytest.param(ctx(target_platform="   "), id="whitespace-only"),
    pytest.param(ctx(target_platform=""), id="empty-string"),
]


@pytest.mark.parametrize("bad", UNDECLARED_SHAPES)
def test_target_refuses_every_undeclared_shape(resolve_target, bad):
    assert_refuses(resolve_target, bad)


@pytest.mark.parametrize("bad", UNDECLARED_SHAPES)
def test_source_refuses_every_undeclared_shape(resolve_source, bad):
    assert_refuses(resolve_source, bad)


def test_target_refusal_names_the_missing_field(resolve_target):
    """The refusal has to say what to collect, or it is a dead end."""
    assert_refuses(resolve_target, ctx(), "target_platform")


def test_source_refusal_names_the_missing_field(resolve_source):
    assert_refuses(resolve_source, ctx(), "source_platform")


def test_no_tenant_context_refusal_says_so(resolve_target):
    assert_refuses(resolve_target, None, "tenant context")


# --------------------------------------------------------------------------
# Inputs that must produce a platform — and more than one of them.
# --------------------------------------------------------------------------


def test_cape_crypto_declared_context_resolves_to_vercel(resolve_target):
    assert resolve_target(ctx(target_platform="vercel")) == "vercel"


def test_declared_shopify_target_resolves_to_shopify(resolve_target):
    assert resolve_target(ctx(target_platform="shopify")) == "shopify"


def test_target_resolver_can_return_more_than_one_value(resolve_target):
    """The falsifiable core. Before the fix this was impossible."""
    answers = {resolve_target(ctx(target_platform=p)) for p in ("shopify", "vercel")}
    assert answers == {"shopify", "vercel"}, (
        "resolver produced {!r} across two distinct declarations — a resolver "
        "that cannot be made to return a second value is not a resolver".format(answers)
    )


@pytest.mark.parametrize(
    "declared", ["shopify", "woocommerce", "magento", "wordpress", "ghost", "custom"]
)
def test_declared_source_resolves_to_itself(resolve_source, declared):
    assert resolve_source(ctx(source_platform=declared)) == declared


def test_source_unknown_is_a_declared_value_not_an_absence(resolve_source):
    """"We looked and could not tell" is a collected answer.

    It must resolve, while the field being absent must refuse — collapsing the
    two is how "nobody asked" becomes indistinguishable from "we checked".
    """
    assert resolve_source(ctx(source_platform="unknown")) == "unknown"
    assert_refuses(resolve_source, ctx(), "source_platform")


def test_declaration_is_case_and_whitespace_normalised(resolve_target, resolve_source):
    assert resolve_target(ctx(target_platform="  Vercel ")) == "vercel"
    assert resolve_source(ctx(source_platform="GHOST")) == "ghost"


def test_target_and_source_are_read_independently(resolve_target, resolve_source):
    """One context, two fields. Cross-reading them would hide a defect in either."""
    both = ctx(target_platform="vercel", source_platform="shopify")
    assert resolve_target(both) == "vercel"
    assert resolve_source(both) == "shopify"


# --------------------------------------------------------------------------
# Values that are declared but not supported.
# --------------------------------------------------------------------------


def test_unknown_target_value_refuses_naming_value_and_allowed_set(resolve_target):
    msg = assert_refuses(
        resolve_target, ctx(target_platform="netlify"), "netlify", "shopify", "vercel"
    )
    assert "netlify" in msg


def test_unknown_source_value_refuses_naming_value_and_allowed_set(resolve_source):
    assert_refuses(
        resolve_source, ctx(source_platform="drupal"), "drupal", "woocommerce", "ghost"
    )


def test_a_target_value_valid_only_as_a_source_is_refused(resolve_target):
    """The two allowed sets are not interchangeable."""
    assert_refuses(resolve_target, ctx(target_platform="wordpress"), "wordpress")


# --------------------------------------------------------------------------
# The forbidden shortcut: inference.
# --------------------------------------------------------------------------


def test_target_is_not_inferred_from_tech_stack_or_connector_flags(resolve_target):
    assert_refuses(
        resolve_target,
        ctx(tech_stack=["Ghost 6.53", "Cloudflare"], _connector_github_vercel=True),
    )


def test_source_is_not_inferred_from_tech_stack_prose(resolve_source):
    assert_refuses(resolve_source, ctx(tech_stack=["Ghost 6.53 (marketing site CMS)"]))


def test_source_is_not_inferred_from_a_myshopify_domain(resolve_source):
    assert_refuses(resolve_source, ctx(primary_domain="cape-crypto.myshopify.com"))


# --------------------------------------------------------------------------
# The declaration drives what the build loads.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def platform_modules(orch):
    fn = getattr(orch, "platform_modules", None)
    assert fn is not None, "orchestrate.py exposes no platform_modules"
    return fn


def test_shopify_target_injects_commerce_and_vercel_does_not(platform_modules):
    shopify = platform_modules(target_platform="shopify", source_platform="shopify")
    vercel = platform_modules(target_platform="vercel", source_platform="ghost")
    assert shopify.get("inject_commerce") is True
    assert vercel.get("inject_commerce") is False


def test_image_hosts_follow_the_target(platform_modules):
    shopify = platform_modules(target_platform="shopify", source_platform="shopify")
    vercel = platform_modules(target_platform="vercel", source_platform="ghost")
    assert any("shopify" in h for h in shopify.get("image_hosts", []))
    assert not any("shopify" in h for h in vercel.get("image_hosts", []))


def test_the_two_targets_do_not_resolve_to_the_same_module_set(platform_modules):
    shopify = platform_modules(target_platform="shopify", source_platform="shopify")
    vercel = platform_modules(target_platform="vercel", source_platform="ghost")
    assert shopify != vercel, "both platforms produced an identical module set"


def test_the_resolved_set_names_its_source_platform(platform_modules):
    vercel = platform_modules(target_platform="vercel", source_platform="ghost")
    assert vercel.get("source_platform") == "ghost"


def test_resolution_feeds_module_selection_end_to_end(resolve_target, resolve_source, platform_modules):
    """The declaration a tenant makes is the one the build acts on."""
    both = ctx(target_platform="vercel", source_platform="shopify")
    modules = platform_modules(
        target_platform=resolve_target(both), source_platform=resolve_source(both)
    )
    assert modules["target_platform"] == "vercel"
    assert modules["source_platform"] == "shopify"
    assert modules["inject_commerce"] is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
