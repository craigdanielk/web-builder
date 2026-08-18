#!/usr/bin/env python3
"""
cms / email are DECLARED modules — and "none" is not the same as silence.

WHY THIS EXISTS
---------------
`platform_modules()` returned `npm_packages: {}` for every platform that has
ever been built (measured 2026-08-17: neither adapter overrides
`get_package_extra_deps`). The first real module to fill it is the CMS censused
in the Xago tenant repo — a Supabase-backed block store with a Puck editor —
and the email sender that repo specified and never got.

The failure mode this file guards is not "the wrong package version". It is the
one that has cost this repo the most: a build that quietly decides the answer to
a question nobody asked. There are THREE states here, not two:

  undeclared        nobody has been asked whether this tenant edits its content
  declared "none"   we asked, and it does not
  declared value    we asked, and here is what to emit

Defaulting the first to the second is silent and unrecoverable — the build emits
no admin surface and no artifact records whether that was a decision. So:

  * `declared_cms` / `declared_email` REFUSE on absence. Every assertion below
    checks that the call RAISED, never merely that it "did not return
    block-store", which a silent default would satisfy.
  * `platform_modules()` omits an undeclared module ENTIRELY — no key. An
    `{"cms": {}}` on an undeclared tenant reads as "checked, needs nothing".
  * a declared `"none"` DOES get a key, carrying `declared: "none"`. That is the
    recorded answer.

It also guards two structural properties the census (§6.3) asks for:
cms/email are orthogonal to shopify-vs-vercel and must not live on a
`DeployAdapter`; and cape-crypto, which declares neither, must resolve
byte-identically to the pre-change function.

Run: cd web-builder && python3 -m pytest scripts/test_module_declarations.py -v
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.tenant_context import (  # noqa: E402
    CMS_KINDS,
    EMAIL_SENDERS,
    PlatformNotDeclared,
    PlatformNotMeasured,
    declared_cms,
    declared_email,
)

#: Sentinel distinguishing "the reader returned x" from "the reader raised".
RETURNED = "RETURNED"

#: The eight keys `platform_modules()` returned before cms/email existed. Any
#: ninth key on a tenant that declares neither is a regression.
BASE_KEYS = {
    "target_platform", "source_platform", "adapter", "inject_commerce",
    "write_env", "generate_l7_pages", "image_hosts", "npm_packages",
}

#: The measured pins, restated here so a silent edit to the catalogue fails a
#: test rather than changing what an emitted app installs.
CMS_PACKAGES = {
    "@measured/puck": "^0.20.2",
    "@supabase/supabase-js": "^2.110.8",
    "@tiptap/core": "^3.29.2",
    "@tiptap/pm": "^3.29.2",
    "@tiptap/react": "^3.29.2",
    "sanitize-html": "^2.17.6",
    "sharp": "^0.34.5",
}


def _load_orchestrate():
    spec = importlib.util.spec_from_file_location("orch", ROOT / "scripts" / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def orch():
    return _load_orchestrate()


@pytest.fixture(scope="module")
def modules_of(orch):
    return orch.platform_modules


def ctx(**fields):
    """A tenant context that READ CLEANLY and declares exactly `fields`.

    `load_status: "ok"` is the point: every refusal these fixtures provoke is an
    undeclared field, never a failed read. The two must not be provable by the
    same fixture or the tests cannot tell them apart either.
    """
    return {"load_status": "ok", "slug": "fixture-tenant", "phase0_field_values": dict(fields)}


def unreadable():
    """A context whose load FAILED — nothing is known about any field."""
    return {
        "load_status": "unreachable",
        "slug": "fixture-tenant",
        "phase0_field_values": {},
        "load_errors": ["fixture: transport error"],
    }


# ── the vocabulary ───────────────────────────────────────────────

def test_the_vocabularies_include_none_as_a_value():
    """"none" is IN the closed set. It is an answer, not the absence of one."""
    assert CMS_KINDS == ("none", "block-store")
    assert EMAIL_SENDERS == ("none", "resend")


def test_orchestrate_does_not_carry_a_second_copy_of_the_vocabulary(orch):
    """One definition, in lib/tenant_context.py.

    `TARGET_PLATFORMS` was duplicated in orchestrate.py and the two drifted;
    that is how "shopify" became the default again. If a re-export is ever added
    here it must be the SAME object, so this asserts identity-or-absence rather
    than just absence.
    """
    for name, canonical in (("CMS_KINDS", CMS_KINDS), ("EMAIL_SENDERS", EMAIL_SENDERS)):
        local = getattr(orch, name, None)
        assert local is None or local is canonical, (
            f"orchestrate.py defines its own {name}; two allowed-sets is how a "
            "vocabulary drifts"
        )


# ── the reader: three states ─────────────────────────────────────

@pytest.mark.parametrize("reader,field,value", [
    (declared_cms, "cms", "block-store"),
    (declared_email, "email", "resend"),
    (declared_cms, "cms", "none"),
    (declared_email, "email", "none"),
])
def test_a_declared_value_is_returned(reader, field, value):
    assert reader(ctx(**{field: value})) == value


@pytest.mark.parametrize("reader,field", [(declared_cms, "cms"), (declared_email, "email")])
def test_an_absent_field_refuses_and_never_defaults_to_none(reader, field):
    """The mutation target. A body that ended `return "none"` would pass an
    assertion of the form `assert reader(...) != "block-store"`; it cannot pass
    this one, which requires the call to have raised."""
    got = RETURNED
    with pytest.raises(PlatformNotDeclared) as exc:
        got = reader(ctx())
    assert got is RETURNED
    assert field in str(exc.value)
    assert "fixture-tenant" in str(exc.value)


@pytest.mark.parametrize("reader,field", [(declared_cms, "cms"), (declared_email, "email")])
def test_an_empty_string_is_absence_not_a_value(reader, field):
    with pytest.raises(PlatformNotDeclared):
        reader(ctx(**{field: "   "}))


@pytest.mark.parametrize("reader,field,bogus", [
    (declared_cms, "cms", "contentful"),
    (declared_cms, "cms", "sanity"),
    (declared_email, "email", "sendgrid"),
    (declared_email, "email", "smtp"),
])
def test_a_value_outside_the_vocabulary_refuses_and_names_the_allowed_set(reader, field, bogus):
    """An unsupported CMS is a refusal, not a fallback to the one we have.

    Emitting the block store for a tenant that declared Contentful would be a
    guess wearing a decision's clothes.
    """
    got = RETURNED
    with pytest.raises(PlatformNotDeclared) as exc:
        got = reader(ctx(**{field: bogus}))
    assert got is RETURNED
    assert bogus in str(exc.value)


@pytest.mark.parametrize("reader", [declared_cms, declared_email])
def test_a_failed_read_is_not_measured_not_undeclared(reader):
    """`load_status` carries the difference from the point of failure to here.

    Without it, an unreachable Supabase and a tenant that declares nothing are
    the same empty dict — and a refusal built on emptiness reports a database
    outage as an operator's failure to fill in a form.
    """
    got = RETURNED
    with pytest.raises(PlatformNotMeasured):
        got = reader(unreadable())
    assert got is RETURNED
    # And the two refusals are distinguishable by type, not only by message.
    assert not issubclass(PlatformNotMeasured, PlatformNotDeclared)


@pytest.mark.parametrize("reader", [declared_cms, declared_email])
def test_no_context_at_all_is_not_measured(reader):
    with pytest.raises(PlatformNotMeasured):
        reader(None)


def test_the_reader_works_through_the_real_loader(monkeypatch):
    """The wire shape too, not only a hand-built dict.

    `phase0_field_values.value` is jsonb and arrives wrapped; if the readers only
    ever saw flat fixtures, an unwrapping change would break the build and pass
    the suite.
    """
    import lib.tenant_context as tc

    monkeypatch.setattr(tc, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(tc, "SUPABASE_KEY", "service-role-key")
    tid = "42e9335e-a77a-4ccc-84f9-254aff145707"

    def fake_get(path, params=""):
        if path == "tenants":
            return [{"id": tid, "slug": "fixture-xago"}]
        if path == "phase0_field_values":
            return [
                {"field_key": "cms", "value": {"v": "block-store"}},
                {"field_key": "email", "value": {"v": "resend"}},
            ]
        return []

    monkeypatch.setattr(tc, "_get", fake_get)

    got = tc.load_tenant_context("fixture-xago")
    assert got["load_status"] == "ok"
    assert tc.declared_cms(got) == "block-store"
    assert tc.declared_email(got) == "resend"


# ── module resolution ────────────────────────────────────────────

def test_a_declared_block_store_resolves_the_measured_dependencies(modules_of):
    got = modules_of("vercel", "ghost", ctx(cms="block-store"))
    assert got["cms"]["declared"] == "block-store"
    assert got["cms"]["npm_packages"] == CMS_PACKAGES
    # and the pins reach the set the app actually installs
    assert got["npm_packages"] == CMS_PACKAGES


def test_the_cms_declares_env_names_and_never_values(modules_of):
    got = modules_of("vercel", "ghost", ctx(cms="block-store"))
    env = got["cms"]["env_names"]
    assert env == [
        "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
        "CMS_TENANT_ID", "CMS_MEDIA_BUCKET", "ADMIN_ALLOWED_HOSTS",
        "ADMIN_PASSWORD", "ADMIN_SESSION_SECRET",
    ]
    # NAMES only. A value here would be a secret in a build artifact.
    assert all(isinstance(n, str) and n.isupper() for n in env)


def test_docx_import_is_not_pulled_in(modules_of):
    """`mammoth` is in Xago's package.json and is deliberately out of scope.

    A dependency nothing imports is weight with no evidence behind it.
    """
    got = modules_of("vercel", "ghost", ctx(cms="block-store"))
    assert "mammoth" not in got["npm_packages"]


def test_resend_pulls_no_package_and_that_is_measured(modules_of):
    """Resend's REST API is reachable with `fetch`. An empty package set here is
    a result, not an unfinished catalogue entry — so it is asserted as `== {}`
    rather than left unchecked."""
    got = modules_of("vercel", "ghost", ctx(email="resend"))
    assert got["email"]["declared"] == "resend"
    assert got["email"]["npm_packages"] == {}
    assert got["npm_packages"] == {}
    assert got["email"]["env_names"] == [
        "RESEND_API_KEY", "EMAIL_SEND_DOMAIN", "EMAIL_NOTIFY_TO",
    ]


def test_declared_none_is_recorded_and_is_not_the_same_as_undeclared(modules_of):
    """THE test. Both cases resolve no module; only one of them is an answer.

    Mutating `_module_entry` to default an undeclared field to "none" makes the
    two dicts identical and fails here.
    """
    declared_none = modules_of("vercel", "ghost", ctx(cms="none", email="none"))
    undeclared = modules_of("vercel", "ghost", ctx())

    # `source`/`market` arrived with the market-default layer (census row 12).
    # `source: "tenant"` and `market: None` is the shape that says an operator
    # answered this, not a market — which is what makes the answer auditable.
    for field in ("cms", "email"):
        assert declared_none[field] == {
            "declared": "none", "source": "tenant", "market": None,
            "npm_packages": {}, "env_names": [],
        }

    assert "cms" not in undeclared, (
        "an undeclared cms must be ABSENT from the dict; a key present with "
        "nothing behind it reads as 'checked and needs nothing'"
    )
    assert "email" not in undeclared

    assert declared_none != undeclared
    # Neither adds packages — which is exactly why the DISTINCTION cannot be
    # carried by npm_packages and has to be carried by the key's presence.
    assert declared_none["npm_packages"] == undeclared["npm_packages"] == {}


def test_an_unmeasured_context_resolves_no_module(modules_of):
    got = modules_of("vercel", "ghost", unreadable())
    assert "cms" not in got and "email" not in got


def test_a_value_outside_the_vocabulary_resolves_no_module(modules_of):
    """Refusal, not acceptance. A rejected value must not be silently promoted
    into a resolved module by the caller that catches the refusal."""
    got = modules_of("vercel", "ghost", ctx(cms="contentful", email="mailgun"))
    assert "cms" not in got and "email" not in got


def test_one_declared_module_does_not_imply_the_other(modules_of):
    got = modules_of("vercel", "ghost", ctx(cms="block-store"))
    assert got["cms"]["declared"] == "block-store"
    assert "email" not in got


# ── orthogonality: not on the deploy adapter ─────────────────────

def test_cms_resolves_identically_on_both_deploy_targets(modules_of):
    """A Shopify-target tenant can declare `cms: block-store`.

    If cms/email lived on a `DeployAdapter`, `_resolve_adapter` would have to
    stop being a two-branch platform dispatch. This asserts the resolution is
    the same object-for-object on both branches.
    """
    fixture = ctx(cms="block-store", email="resend")
    vercel = modules_of("vercel", "ghost", fixture)
    shopify = modules_of("shopify", "shopify", fixture)
    assert vercel["cms"] == shopify["cms"]
    assert vercel["email"] == shopify["email"]


def test_no_deploy_adapter_declares_a_cms_or_an_email(orch):
    for adapter_cls in (orch.DeployAdapter, orch.ShopifyAdapter, orch.VercelAdapter):
        for attr in ("cms", "email", "CMS_KINDS", "EMAIL_SENDERS", "get_cms_deps"):
            assert not hasattr(adapter_cls, attr), (
                f"{adapter_cls.__name__}.{attr} — cms/email are orthogonal to the "
                "deploy target and must not be adapter behaviour (census §6.3)"
            )


def test_two_pins_for_one_package_refuse_rather_than_pick_one(orch, monkeypatch):
    """A collision between an adapter pin and a module pin is not resolvable
    here, and choosing silently decides what the app installs."""
    monkeypatch.setattr(
        orch.VercelAdapter, "get_package_extra_deps",
        lambda self: {"sharp": "^0.30.0"}, raising=True,
    )
    with pytest.raises(ValueError) as exc:
        orch.platform_modules("vercel", "ghost", ctx(cms="block-store"))
    assert "sharp" in str(exc.value)


# ── cape-crypto regression ───────────────────────────────────────

#: cape-crypto's platform declarations, measured 2026-08-17. It declares 86
#: fields and NEITHER `cms` NOR `email`.
CAPE_CRYPTO_DECLARED = {
    "target_platform": "vercel",
    "source_platform": "ghost",
    "source_api_access": False,
}


def test_cape_crypto_resolution_is_unchanged_by_cms_and_email(modules_of):
    """The regression proof, stated as an equality rather than a description.

    Passing NO tenant_context reproduces the function's pre-change behaviour
    exactly — the cms/email loop cannot contribute without one. So a
    cape-crypto context resolving equal to that call IS the before/after
    comparison, and it runs on every suite run instead of once by hand.
    """
    before = modules_of("vercel", "ghost")
    after = modules_of("vercel", "ghost", ctx(**CAPE_CRYPTO_DECLARED))

    assert set(before) == BASE_KEYS
    assert set(after) == BASE_KEYS
    for key in BASE_KEYS:
        if key == "adapter":
            assert type(after[key]) is type(before[key])
            continue
        assert after[key] == before[key], f"cape-crypto changed {key}"
    assert after["npm_packages"] == {}


def test_the_shopify_branch_is_also_unchanged_when_nothing_is_declared(modules_of):
    before = modules_of("shopify", "shopify")
    after = modules_of("shopify", "shopify", ctx(**CAPE_CRYPTO_DECLARED))
    assert set(before) == set(after) == BASE_KEYS
    assert after["image_hosts"] == before["image_hosts"] == [
        "cdn.shopify.com", "**.myshopify.com",
    ]
    assert after["npm_packages"] == {}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
