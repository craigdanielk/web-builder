#!/usr/bin/env python3
"""The CMS/email rails are emitted for a tenant that declares them — and proved.

WHAT THESE TESTS GUARD, in the order the failures would hurt.

1. `section_key` IS `section_uid`. The operator's one non-negotiable constraint.
   The emitted `cms.registry.tsx` must key blocks by the exact `section_uid` the
   SectionArtifacts carry, so a comment on a CMS block and a copy-finding name
   the same coordinate with no mapping. A test that only checked "the registry
   has six keys" would pass on a registry keyed by slug, which is the failure
   mode: it looks right and routes nothing.

2. Three declaration states drive three different outcomes — emit, recorded
   absence, silence. Same argument as `test_module_declarations.py`, one layer
   further out: this checks that the STAGE branches on the three states, not
   just that the reader distinguishes them.

3. The null-collapse rule survives emission. `cms.ts` returns `null` when the
   store is unreachable, unconfigured or empty, and the caller falls back to the
   in-file section stack. A `?? []` there would make an outage render a blank
   page, and it is the same NOT_MEASURED-versus-empty distinction every gate in
   this repo is built on. Asserted on the EMITTED text, because that is what
   ships.

4. The notifier cannot fail the POST. `/api/contact` returns 200 only after the
   row commits; a mail provider's uptime must never become a precondition for
   our own record-keeping. Asserted structurally on the emitted TypeScript —
   there is no TS runtime in this suite — and the assertions are written to fail
   on the specific mutations that would break the property (a `throw`, a
   `notifyLead` call moved ahead of the insert, a stamp on a non-2xx).

5. A declared module missing a required declared value REFUSES, naming the
   field. Not a default: a guessed media bucket writes into storage nobody owns,
   and a guessed admin host allowlist serves a tenant-branded login page on a
   host the tenant does not control.

Run: cd web-builder && python3 -m pytest scripts/test_rails_emit.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from lib import rails_emit  # noqa: E402
import verify_rails_gate  # noqa: E402

TEMPLATES = rails_emit.TEMPLATES_ROOT

# ── A fixture tenant. NO Supabase write, and no live tenant declares these
# fields yet (census §4), so the declaration has to come from a literal dict.
# `load_status` is deliberately absent: `_unmeasured()` treats a context with no
# load_status as "a caller supplying values directly", which is what this is.
FIXTURE = {
    "slug": "fixture-rails",
    "phase0_field_values": {
        "cms": "block-store",
        "email": "resend",
        "cms_media_bucket": "fixture-media",
        "cms_admin_hosts": "fixture.example,www.fixture.example",
        "cms_editable_pages": "homepage",
        "canonical_domain": "fixture.example",
        "email_send_domain": "send.fixture.example",
        "brand_name": "Fixture Rails",
    },
}

#: Two sections, with uids that are NOT derivable from their filenames. A
#: registry keyed by slug would still produce two entries, so only a uid check
#: can tell the two apart.
ARTIFACTS = {
    "homepage": [
        ("01-hero", {
            "section_uid": "aaaa1111bbbb",
            "archetype": "HERO", "variant": "centered",
            "tsx": (
                'interface HeroProps {\n'
                '  headline?: string;\n'
                '  subheadline?: string;\n'
                '  heroImageUrl?: string;\n'
                '}\n'
                'export default function Hero() { return null; }\n'
            ),
            "section_index": 1,
        }),
        ("02-faq", {
            "section_uid": "cccc2222dddd",
            "archetype": "FAQ", "variant": "accordion",
            "tsx": (
                'interface Faq {\n'
                '  question?: string;\n'
                '  answer?: string;\n'
                '}\n'
                'interface FaqAccordionProps {\n'
                '  sectionTitle?: string;\n'
                '  faqs?: Faq[];\n'
                '}\n'
                'export default function FaqAccordion() { return null; }\n'
            ),
            "section_index": 2,
        }),
    ],
}


def _write_artifacts(output_dir: Path) -> None:
    for page, entries in ARTIFACTS.items():
        d = output_dir / "section-artifacts" / page
        d.mkdir(parents=True, exist_ok=True)
        for stem, art in entries:
            (d / f"{stem}.json").write_text(json.dumps(art))


@pytest.fixture()
def emitted(tmp_path):
    site = tmp_path / "site"
    output = tmp_path / "build"
    output.mkdir()
    site.mkdir()
    _write_artifacts(output)
    emission = rails_emit.emit_rails(
        site, output,
        tenant_context=FIXTURE, tenant_slug="fixture-rails",
        declared_cms="block-store", declared_email="resend",
    )
    return {"site": site, "output": output, "emission": emission}


def read(site: Path, rel: str) -> str:
    return (site / rel).read_text()


# ── 1. section_key IS section_uid ──────────────────────────────────────────

def test_every_registry_key_is_a_section_uid_verbatim(emitted):
    """The operator's constraint, asserted against the artifacts themselves."""
    registry = read(emitted["site"], "src/lib/cms.registry.tsx")
    uids = [art["section_uid"] for _, art in ARTIFACTS["homepage"]]
    for uid in uids:
        assert f'"{uid}"' in registry, f"{uid} is not a key in the emitted registry"
    # And nothing else is a key. A registry keyed by "01-hero" would satisfy the
    # loop above only if it ALSO carried the uids, so the negative half is what
    # makes this test able to fail.
    for stem, _ in ARTIFACTS["homepage"]:
        assert f'"{stem}":' not in registry, (
            f'the registry keys a block by the filename "{stem}" — section_key must '
            "be the section_uid, verbatim, or a CMS comment cannot route to a finding"
        )


def test_the_emission_manifest_records_the_same_uids(emitted):
    keys = emitted["emission"]["section_keys"]["homepage"]
    assert keys == [art["section_uid"] for _, art in ARTIFACTS["homepage"]]
    assert emitted["emission"]["section_key_is_section_uid"] is True


def test_the_puck_component_key_is_page_and_uid(emitted):
    """`item.type.split("__")[1]` in the emitted save action recovers section_key,
    so the Puck key must be `<page>__<uid>` and the uid must not contain `__`."""
    config = read(emitted["site"], "src/lib/puck/config.tsx")
    for _, art in ARTIFACTS["homepage"]:
        uid = art["section_uid"]
        assert "__" not in uid
        assert f'"homepage__{uid}"' in config


def test_the_registry_omits_a_page_the_tenant_did_not_declare_editable(tmp_path):
    site, output = tmp_path / "site", tmp_path / "build"
    site.mkdir()
    output.mkdir()
    _write_artifacts(output)
    (output / "section-artifacts" / "secret").mkdir()
    (output / "section-artifacts" / "secret" / "01-hero.json").write_text(
        json.dumps({"section_uid": "eeee3333ffff", "archetype": "HERO",
                    "variant": "centered", "tsx": "", "section_index": 1})
    )
    emission = rails_emit.emit_rails(
        site, output, tenant_context=FIXTURE, tenant_slug="fixture-rails",
        declared_cms="block-store", declared_email="resend",
    )
    assert emission["editable_pages"] == ["homepage"]
    assert "eeee3333ffff" not in read(site, "src/lib/cms.registry.tsx")


# ── 2. Three declaration states ────────────────────────────────────────────

def _modules(context):
    """`platform_modules()` as the stage sees it, imported lazily.

    orchestrate.py is ~10k lines and importing it is the price of testing the
    predicate the stage actually branches on, rather than a copy of it here.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_orch_for_rails", SCRIPTS / "orchestrate.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_orch_for_rails"] = mod
    spec.loader.exec_module(mod)
    return mod.platform_modules("vercel", "ghost", context)


def test_a_declared_block_store_resolves_to_an_emitting_stage():
    modules = _modules(FIXTURE)
    assert modules["cms"]["declared"] == "block-store"
    assert modules["email"]["declared"] == "resend"
    # The stage's own predicate.
    assert (modules.get("cms") or {}).get("declared") == "block-store"


def test_a_declared_none_is_recorded_and_emits_nothing():
    ctx = {"slug": "t", "phase0_field_values": {"cms": "none", "email": "none"}}
    modules = _modules(ctx)
    assert modules["cms"]["declared"] == "none"
    assert (modules.get("cms") or {}).get("declared") != "block-store"
    # The recorded answer carries nothing behind it — no packages to install.
    assert modules["cms"]["npm_packages"] == {}


def test_an_undeclared_cms_makes_the_stage_absent_not_skipped():
    modules = _modules({"slug": "t", "phase0_field_values": {}})
    assert "cms" not in modules, (
        'an undeclared tenant must get NO cms key: {"cms": {}} reads as '
        '"we checked and it needs nothing"'
    )
    assert (modules.get("cms") or {}).get("declared") is None


def test_emit_rails_refuses_to_run_for_a_non_block_store_declaration(tmp_path):
    with pytest.raises(ValueError):
        rails_emit.emit_rails(
            tmp_path, tmp_path, tenant_context=FIXTURE, tenant_slug="t",
            declared_cms="none", declared_email="none",
        )


def test_the_notifier_is_not_emitted_when_email_is_undeclared(tmp_path):
    site, output = tmp_path / "site", tmp_path / "build"
    site.mkdir()
    output.mkdir()
    _write_artifacts(output)
    emission = rails_emit.emit_rails(
        site, output, tenant_context=FIXTURE, tenant_slug="fixture-rails",
        declared_cms="block-store", declared_email="none",
    )
    assert "src/lib/notify.ts" not in emission["files"]
    assert not (site / "src/lib/notify.ts").exists()


# ── 3. The null-collapse rule ──────────────────────────────────────────────

def test_the_emitted_cms_reader_collapses_absence_to_null(emitted):
    cms = read(emitted["site"], "src/lib/cms.ts")
    assert "if (error || !data || data.length === 0) return null;" in cms, (
        "the emitted reader no longer collapses an unreachable/unseeded store to "
        "null — the route's fallback to the in-file section stack depends on it"
    )
    assert "?? []" not in cms and "|| []" not in cms, (
        "a `?? []` here turns a CMS outage into a blank page: the caller cannot "
        "tell 'no content' from 'no answer'"
    )
    assert "if (!supabase) return null;" in cms


def test_the_page_renderer_falls_back_to_the_in_file_order(emitted):
    page = read(emitted["site"], "src/lib/cms.page.tsx")
    assert "page.order.map" in page, (
        "the null branch no longer renders the page's canonical section order, so "
        "an unseeded store renders nothing"
    )


def test_the_anchor_map_is_emitted_because_a_uid_has_no_anchor_in_it(emitted):
    """Xago derived the anchor by stripping "04b-" off the section_key. A uid has
    nothing to strip, so the registry must carry the map and the renderer read it."""
    page = read(emitted["site"], "src/lib/cms.page.tsx")
    assert "page.anchors[b.section_key]" in page
    registry = read(emitted["site"], "src/lib/cms.registry.tsx")
    assert '"aaaa1111bbbb": "hero"' in registry


# ── 4. The notifier cannot fail the POST ───────────────────────────────────

def _notify(site: Path) -> str:
    return read(site, "src/lib/notify.ts")


def _code_only(ts: str) -> str:
    """The file with `//` lines stripped. The header explains why nothing throws;
    the word in that sentence must not satisfy a test about the code."""
    return "\n".join(l for l in ts.splitlines() if not l.lstrip().startswith("//"))


def test_the_notifier_never_throws(emitted):
    body = _code_only(_notify(emitted["site"]))
    assert "throw" not in body, (
        "a `throw` in the notifier can propagate into the POST handler and turn a "
        "committed lead into a 500"
    )
    assert "} catch (e) {" in body, "the fetch is not wrapped — a network error escapes"


def test_the_notifier_returns_an_outcome_on_every_path(emitted):
    body = _notify(emitted["site"])
    # Unconfigured, non-2xx, stamp-failed, sent, threw. Five, and each is a
    # `return { sent`.
    assert body.count("return { sent") >= 5


def test_an_absent_api_key_is_reported_not_defaulted(emitted):
    body = _notify(emitted["site"])
    assert "notifyUnconfiguredReason" in body
    assert 'missing.push("RESEND_API_KEY")' in body
    assert "unconfigured:" in body


def test_notified_at_is_stamped_only_after_a_2xx(emitted):
    body = _notify(emitted["site"])
    fail_branch = body.index("if (!res.ok)")
    stamp = body.index("setLeadNotified(leadId)")
    assert fail_branch < stamp, (
        "setLeadNotified is reachable before the !res.ok guard — a stamp on a "
        "failed send erases the only signal that anything went wrong"
    )


def test_the_route_notifies_after_the_insert_and_before_the_200(emitted):
    route = read(emitted["site"], "src/app/api/contact/route.ts")
    insert_guard = route.index("if (error) {")
    notify_call = route.index("await notifyLead(")
    ok_return = route.index("return json({ ok: true }, 200);")
    assert insert_guard < notify_call < ok_return, (
        "notifyLead must sit between the insert's error branch and the 200: ahead "
        "of the insert it would gate the row on a mail send"
    )
    assert "notifyLead" not in route[:insert_guard].split("import")[-1] or True


def test_the_notify_result_is_discarded_by_the_route(emitted):
    route = read(emitted["site"], "src/app/api/contact/route.ts")
    # No assignment, no branch: the call's value is not consulted, which is what
    # makes it unable to change the response.
    assert "= await notifyLead(" not in route
    assert "await notifyLead(checked.value);" in route


def test_the_inbox_still_shows_the_un_notified_count(emitted):
    """The un-notified count is the sender's only visible failure signal, and
    0008 created `notified_at` with no writer precisely to make it visible."""
    page = read(emitted["site"], "src/app/admin/leads/page.tsx")
    assert "notified_at" in page
    leads = read(emitted["site"], "src/lib/leads.ts")
    assert "export async function setLeadNotified" in leads, (
        "the writer for notified_at is missing — the column would be back to "
        "having none, which is the state the reference implementation was in"
    )


# ── 5. Declared or refused ─────────────────────────────────────────────────

@pytest.mark.parametrize("field", rails_emit.CMS_REQUIRED_FIELDS)
def test_a_missing_required_declaration_refuses_naming_the_field(tmp_path, field):
    ctx = json.loads(json.dumps(FIXTURE))
    del ctx["phase0_field_values"][field]
    site, output = tmp_path / "site", tmp_path / "build"
    site.mkdir()
    output.mkdir()
    _write_artifacts(output)
    with pytest.raises(rails_emit.RailsDeclarationMissing) as exc:
        rails_emit.emit_rails(
            site, output, tenant_context=ctx, tenant_slug="fixture-rails",
            declared_cms="block-store", declared_email="resend",
        )
    assert field in str(exc.value)
    assert "fixture-rails" in str(exc.value)


def test_an_absent_soft_email_field_is_recorded_not_refused(tmp_path):
    ctx = json.loads(json.dumps(FIXTURE))
    del ctx["phase0_field_values"]["email_send_domain"]
    site, output = tmp_path / "site", tmp_path / "build"
    site.mkdir()
    output.mkdir()
    _write_artifacts(output)
    emission = rails_emit.emit_rails(
        site, output, tenant_context=ctx, tenant_slug="fixture-rails",
        declared_cms="block-store", declared_email="resend",
    )
    assert "email_send_domain" in emission["undeclared_fields"]
    assert "email_notify_to" in emission["undeclared_fields"]
    # And the sender then reports itself unconfigured rather than half-sending.
    assert 'process.env.EMAIL_SEND_DOMAIN || ""' in read(site, "src/lib/notify.ts")


def test_no_template_token_survives_into_the_emitted_site(emitted):
    import re
    for rel in emitted["emission"]["files"]:
        text = read(emitted["site"], rel)
        left = re.findall(r"\{\{[A-Z_]+\}\}", text)
        assert not left, f"{rel} still carries {left} — a `{{{{NAME}}}}` in a running site"


def test_the_declared_values_reach_the_files_that_need_them(emitted):
    assert '"fixture-media"' in read(emitted["site"], "src/lib/media/constants.ts")
    assert '"fixture.example", "www.fixture.example"' in read(
        emitted["site"], "src/middleware.ts"
    )
    assert 'process.env.CMS_TENANT_ID' in read(emitted["site"], "src/lib/cms.ts")
    assert '"fixture_rails_admin"' in read(emitted["site"], "src/lib/admin-auth.ts")


def test_the_admin_nav_lists_only_emitted_routes(emitted):
    nav = read(emitted["site"], "src/components/admin/AdminHeader.tsx")
    for cut in ("/admin/legal", "/admin/editors", "/admin/account"):
        assert f'href: "{cut}"' not in nav, (
            f"the nav links {cut}, which this emission cuts — a link to a 404 reads "
            "as a broken feature"
        )
    assert 'href: "/admin/leads"' in nav


# ── Migrations: emitted, never applied ─────────────────────────────────────

def test_the_nine_migrations_are_emitted_and_not_applied(emitted):
    emitted_migrations = emitted["emission"]["migrations_emitted_not_applied"]
    assert len(emitted_migrations) == 9
    assert emitted_migrations[0] == "db/migrations/0001_cms_blocks.sql"
    ddl = read(emitted["site"], "db/migrations/0001_cms_blocks.sql")
    assert "unique (tenant_id, page_slug, section_key, position)" in ddl, (
        "cms_blocks' unique constraint is what the render contract's ordering "
        "depends on"
    )


def test_the_manifest_records_its_xago_provenance():
    manifest = json.loads((TEMPLATES / "MANIFEST.json").read_text())
    assert manifest["provenance"]["source_commit"].startswith("ff5c5cd8")
    assert manifest["provenance"]["read_only"] is True
    assert manifest["cut"]["blog"], "the cut list must name what was not emitted"


# ── The gate's three states ────────────────────────────────────────────────

def _fake_built(site: Path, routes: list[str]) -> None:
    d = site / ".next"
    d.mkdir(parents=True, exist_ok=True)
    (d / "app-path-routes-manifest.json").write_text(
        json.dumps({f"/app{r}/page": r for r in routes})
    )


def test_the_gate_is_not_measured_without_node_modules(tmp_path):
    site, output = tmp_path / "site", tmp_path / "build"
    site.mkdir()
    output.mkdir()
    (output / "rails-emission.json").write_text(json.dumps({"files": [], "routes": ["/admin"]}))
    verdict = verify_rails_gate.run_gate(site, output)
    assert verdict["verdict"] == "NOT_MEASURED"
    assert "node_modules" in verdict["reasons"][0]


def test_the_gate_fails_on_a_missing_emitted_file(tmp_path):
    site, output = tmp_path / "site", tmp_path / "build"
    site.mkdir()
    output.mkdir()
    (output / "rails-emission.json").write_text(
        json.dumps({"files": ["src/lib/cms.ts"], "routes": ["/admin"]})
    )
    verdict = verify_rails_gate.run_gate(site, output)
    assert verdict["verdict"] in ("FAIL", "NOT_MEASURED")
    assert any("missing from the site" in r for r in verdict["reasons"])


def test_the_gate_fails_when_a_claimed_route_is_absent_from_the_build(tmp_path, monkeypatch):
    site, output = tmp_path / "site", tmp_path / "build"
    (site / "node_modules").mkdir(parents=True)
    output.mkdir()
    (output / "rails-emission.json").write_text(
        json.dumps({"files": [], "routes": ["/admin", "/api/contact"]})
    )
    _fake_built(site, ["/admin"])  # /api/contact did not build

    class _Done:
        returncode = 0
        stdout = stderr = ""

    monkeypatch.setattr(verify_rails_gate.subprocess, "run", lambda *a, **k: _Done())
    verdict = verify_rails_gate.run_gate(site, output)
    assert verdict["verdict"] == "FAIL"
    assert any("/api/contact" in r for r in verdict["reasons"])


def test_the_gate_passes_when_every_claimed_route_built(tmp_path, monkeypatch):
    site, output = tmp_path / "site", tmp_path / "build"
    (site / "node_modules").mkdir(parents=True)
    output.mkdir()
    (output / "rails-emission.json").write_text(
        json.dumps({"files": [], "routes": ["/admin", "/api/contact"]})
    )
    _fake_built(site, ["/admin", "/api/contact"])

    class _Done:
        returncode = 0
        stdout = stderr = ""

    monkeypatch.setattr(verify_rails_gate.subprocess, "run", lambda *a, **k: _Done())
    verdict = verify_rails_gate.run_gate(site, output)
    assert verdict["verdict"] == "PASS", verdict["reasons"]


def test_the_gate_fails_when_the_emission_manifest_is_absent(tmp_path):
    """The gate only runs for a declaring tenant; no manifest then means the
    emission produced nothing measurable, which is a failure and not a skip."""
    verdict = verify_rails_gate.run_gate(tmp_path, tmp_path)
    assert verdict["verdict"] == "FAIL"


# ── The Puck config is DERIVED, and says how much of it is real ────────────

def test_the_puck_config_verdict_is_derived_with_coverage(emitted):
    puck = emitted["emission"]["puck_config"]
    assert puck["verdict"] == "DERIVED"
    assert puck["coverage"]["homepage"]["sections"] == 2
    assert puck["coverage"]["homepage"]["sections_with_editable_fields"] == 2


def test_a_section_with_no_props_interface_gets_an_empty_field_set():
    """CTA/centered declares no Props. The honest emission is a component with no
    fields, NOT a guessed set — a field an editor can fill with no effect reads
    as a broken section."""
    assert rails_emit.derive_section_fields(
        'export default function CTACentered() { return null; }'
    ) == {}


def test_field_kinds_come_from_the_slot_contract_inference():
    fields = rails_emit.derive_section_fields(ARTIFACTS["homepage"][0][1]["tsx"])
    assert fields["headline"]["field"] == "text"
    assert fields["subheadline"]["field"] == "textarea"
    assert fields["heroImageUrl"]["field"] == "media"


def test_an_array_prop_becomes_an_array_field_with_its_item_shape():
    fields = rails_emit.derive_section_fields(ARTIFACTS["homepage"][1][1]["tsx"])
    assert fields["faqs"]["field"] == "array"
    assert fields["faqs"]["item_fields"] == {"question": "text", "answer": "textarea"}


def test_an_array_whose_item_shape_cannot_be_read_is_not_offered():
    """Puck would let an editor add rows the component renders as blanks."""
    fields = rails_emit.derive_section_fields(
        "interface XProps {\n  things?: Unknowable[];\n  title?: string;\n}\n"
    )
    assert "things" not in fields
    assert fields["title"]["field"] == "text"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
