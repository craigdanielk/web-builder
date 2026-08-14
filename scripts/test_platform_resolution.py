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

Platform is COLLECTED, never inferred. Deriving it from `tech_stack` prose is
forbidden by the plan (Task 0.1) for the same reason fuzzy benchmark matching
is: a guess that looks like a decision.

The four failures that used to be one answer are now distinct:
  no context / no declaration / unknown value  -> refuse, naming which
  a declared value                             -> that value

Run: python3 scripts/test_platform_resolution.py
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")
        if detail:
            print(f"      {detail}")


def _orchestrate():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("orch", ROOT / "scripts" / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch"] = mod
    spec.loader.exec_module(mod)
    return mod


def ctx(**phase0):
    """A tenant context shaped like lib.tenant_context.load_tenant_context."""
    return {
        "tenant_id": "ad98688a-c384-4785-8d96-12544a13cfa7",
        "slug": "cape-crypto",
        "available": True,
        "phase0_field_values": dict(phase0),
    }


class PlatformRefused(Exception):
    pass


def _refuses(fn, argument, must_mention=None):
    """True when fn refuses `argument` explicitly rather than answering."""
    try:
        result = fn(argument)
    except SystemExit as exc:
        return (must_mention is None) or (must_mention in str(exc))
    except Exception as exc:  # noqa: BLE001 — any explicit refusal
        return (must_mention is None) or (must_mention in str(exc))
    return False, result


def test_target_platform():
    print("\nresolve_target_platform")
    orch = _orchestrate()
    resolve = orch.resolve_target_platform

    got = resolve(ctx(target_platform="vercel"))
    test("a declared vercel target resolves to vercel", got == "vercel", f"got {got!r}")

    got = resolve(ctx(target_platform="shopify"))
    test("a declared shopify target resolves to shopify", got == "shopify", f"got {got!r}")

    r = _refuses(resolve, ctx())
    test("an undeclared target refuses", r is True,
         f"returned {r[1]!r} instead of refusing" if isinstance(r, tuple) else "")

    r = _refuses(resolve, None)
    test("no tenant context refuses", r is True,
         f"returned {r[1]!r} instead of refusing" if isinstance(r, tuple) else "")

    r = _refuses(resolve, ctx(target_platform="netlify"), must_mention="netlify")
    test("an unrecognised value refuses, naming the value", r is True,
         f"returned {r[1]!r} instead of refusing" if isinstance(r, tuple) else "")

    # The forbidden shortcut: prose that a fuzzy matcher would happily read.
    r = _refuses(resolve, ctx(tech_stack=["Ghost 6.53", "Cloudflare"],
                              _connector_github_vercel=True))
    test("does NOT infer a target from tech_stack prose or connector flags",
         r is True,
         f"inferred {r[1]!r} from prose" if isinstance(r, tuple) else "")


def test_source_platform():
    print("\nresolve_source_platform")
    orch = _orchestrate()
    resolve = getattr(orch, "resolve_source_platform", None)
    if resolve is None:
        test("resolve_source_platform exists", False, "orchestrate.py has no resolve_source_platform")
        return

    got = resolve(ctx(source_platform="ghost"))
    test("a declared ghost source resolves to ghost", got == "ghost", f"got {got!r}")

    got = resolve(ctx(source_platform="shopify"))
    test("a declared shopify source resolves to shopify", got == "shopify", f"got {got!r}")

    r = _refuses(resolve, ctx())
    test("an undeclared source refuses", r is True,
         f"returned {r[1]!r} instead of refusing" if isinstance(r, tuple) else "")

    r = _refuses(resolve, ctx(source_platform="drupal"), must_mention="drupal")
    test("an unrecognised source refuses, naming the value", r is True,
         f"returned {r[1]!r} instead of refusing" if isinstance(r, tuple) else "")

    r = _refuses(resolve, ctx(tech_stack=["Ghost 6.53 (marketing site CMS)"]))
    test("does NOT infer a source from tech_stack prose", r is True,
         f"inferred {r[1]!r} from prose" if isinstance(r, tuple) else "")


def test_modules_for_platform():
    """The resolved platform selects which modules and packages get loaded."""
    print("\nplatform_modules — declaration drives what is loaded")
    orch = _orchestrate()
    modules_for = getattr(orch, "platform_modules", None)
    if modules_for is None:
        test("platform_modules exists", False, "orchestrate.py has no platform_modules")
        return

    shopify = modules_for(target_platform="shopify", source_platform="shopify")
    vercel = modules_for(target_platform="vercel", source_platform="ghost")

    test("shopify target injects the commerce library",
         shopify.get("inject_commerce") is True, f"got {shopify!r}")
    test("vercel target does not inject the commerce library",
         vercel.get("inject_commerce") is False, f"got {vercel!r}")

    test("shopify target carries its storefront image host",
         any("shopify" in h for h in shopify.get("image_hosts", [])),
         f"hosts={shopify.get('image_hosts')!r}")
    test("vercel target does not carry a shopify image host",
         not any("shopify" in h for h in vercel.get("image_hosts", [])),
         f"hosts={vercel.get('image_hosts')!r}")

    test("the two targets do not resolve to the same module set",
         shopify != vercel, "both platforms produced an identical module set")

    test("the resolved set names its source platform",
         vercel.get("source_platform") == "ghost", f"got {vercel!r}")


def main():
    print("=" * 64)
    print("  Platform resolution — collected, never inferred; able to refuse")
    print("=" * 64)
    test_target_platform()
    test_source_platform()
    test_modules_for_platform()
    print("\n" + "=" * 64)
    print(f"  {PASS} passed, {FAIL} failed")
    print("=" * 64)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
