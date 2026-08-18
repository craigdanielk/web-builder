#!/usr/bin/env python3
"""Build web-builder/rails-templates/cms/ from the Xago tenant repo (READ-ONLY).

Every substitution applied is recorded in MANIFEST.json so the emission is
reproducible and drift from the source is detectable by sha256.

Two modes:

    python3 build_templates.py            re-emit from the source repo
    python3 build_templates.py --verify   re-hash the emitted templates against
                                          MANIFEST.json's recorded shas

`--verify` needs neither the source repo nor the network. It answers three
states per file — MATCH / DRIFTED / MISSING — and exits 0 (all match), 1 (any
drift or absence) or 3 (the manifest itself is absent or unreadable, so nothing
was measured; NOT_MEASURED is not a pass).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

XAGO = Path("/Users/craigkunte/Developer/GitHub/tenants/xago")
SITE = XAGO / "site"
DEST = Path(__file__).resolve().parent / "cms"
XAGO_COMMIT = "ff5c5cd8d294f9943b591b6d9fb853d81978537f"

TENANT_ENV = ("process.env.XAGO_TENANT_ID", "process.env.{{CMS_TENANT_ENV}}")

# (path relative to site/, [ (find, replace, why) ])
FILES: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("src/lib/cms.ts", [
        ("// Xago CMS render layer", "// CMS render layer", "brand out of a comment"),
        TENANT_ENV + ("tenant id env var name",),
    ]),
    ("src/lib/cms.page.tsx", [
        ("        anchor: sectionAnchorId(b.section_key),",
         "        anchor: page.anchors[b.section_key] ?? sectionAnchorId(b.section_key),",
         "section_key is a section_uid here, not a '04-how_it_works' slug, so the "
         "anchor cannot be derived from it; the generated registry carries the map"),
        ("        anchor: sectionAnchorId(k),",
         "        anchor: page.anchors[k] ?? sectionAnchorId(k),",
         "same, on the no-CMS fallback branch"),
    ]),
    ("src/lib/cms-attribution.ts", [TENANT_ENV + ("tenant id env var name",)]),
    ("src/lib/admin-auth.ts", [
        ('export const ADMIN_COOKIE = "xago_admin";',
         'export const ADMIN_COOKIE = "{{COOKIE_PREFIX}}_admin";',
         "cookie name is per-tenant so two tenant sites on one apex do not collide"),
    ]),
    ("src/lib/admin-flash.ts", [
        ('export const FLASH_COOKIE = "xago_admin_flash";',
         'export const FLASH_COOKIE = "{{COOKIE_PREFIX}}_admin_flash";',
         "same"),
    ]),
    ("src/lib/editor-password.ts", []),
    ("src/lib/editor-directory.ts", [TENANT_ENV + ("tenant id env var name",)]),
    ("src/lib/safe-href.ts", []),
    ("src/lib/leads.ts", [
        TENANT_ENV + ("tenant id env var name",),
        # setLeadNotified is APPENDED, not substituted — see append_leads() below.
    ]),
    ("src/lib/media/constants.ts", [
        ('export const MEDIA_BUCKET = "xago-media";',
         'export const MEDIA_BUCKET = "{{MEDIA_BUCKET}}";',
         "declared bucket name"),
    ]),
    ("src/lib/media/asset.ts", []),
    ("src/lib/media/normalize.ts", [
        ("// Pure image normalisation for the Xago CMS media pipeline",
         "// Pure image normalisation for the CMS media pipeline", "brand out of a comment"),
    ]),
    ("src/lib/media/store.ts", [TENANT_ENV + ("tenant id env var name",)]),
    ("src/lib/puck/media.ts", []),
    ("src/lib/puck/media-hydrate.ts", [TENANT_ENV + ("tenant id env var name",)]),
    ("src/lib/puck/media-validation.ts", []),
    ("src/lib/puck/fields.tsx", []),
    ("src/middleware.ts", [
        ('    "xago.io",\n    "www.xago.io",\n', "    ...{{ADMIN_HOSTS_JSON}},\n",
         "the declared host allowlist"),
    ]),
    ("src/components/admin/AdminHeader.tsx", [
        ('const LINKS: { key: AdminNavKey; href: string; label: string }[] = [\n'
         '  { key: "pages", href: "/admin", label: "Pages" },\n'
         '  { key: "legal", href: "/admin/legal", label: "Legal & FAQ" },\n'
         '  { key: "leads", href: "/admin/leads", label: "Enquiries" },\n'
         '  { key: "editors", href: "/admin/editors", label: "People" },\n'
         '  { key: "account", href: "/admin/account", label: "Your password" },\n'
         '];',
         'const LINKS: { key: AdminNavKey; href: string; label: string }[] = {{ADMIN_NAV_LINKS}};',
         "the nav must list the routes THIS emission actually emitted — a link to a "
         "cut route is a 404 that reads as a broken feature"),
        ('  <img src="/xago-logo.png" alt="Xago" ', '  <img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" ',
         "tenant mark"),
    ]),
    ("src/components/admin/AssetGrid.tsx", []),
    ("src/components/admin/AssetPicker.tsx", []),
    ("src/components/admin/AssetUploadButton.tsx", []),
    ("src/components/admin/MediaLibrary.tsx", []),
    ("src/app/admin/actions.ts", [TENANT_ENV + ("tenant id env var name",)]),
    ("src/app/admin/page.tsx", [
        ('export const metadata = { title: "Xago CMS" };',
         'export const metadata = { title: "{{BRAND_NAME}} CMS" };', "tenant mark"),
        ('<li><strong>Everyone signs in as themselves.</strong> Each change is recorded against the person who made it, and you can see who edited a page last on the cards above. Manage who has access under <Link href="/admin/editors" style={{ color: "#57534e" }}>People</Link>.</li>',
         '<li><strong>Everyone signs in as themselves.</strong> Each change is recorded against the person who made it, and you can see who edited a page last on the cards above.</li>',
         "the /admin/editors route is CUT from this emission (see MANIFEST.cut); a "
         "link to it would 404"),
    ]),
    ("src/app/admin/login/page.tsx", [
        ('export const metadata = { title: "Xago CMS — Sign in" };',
         'export const metadata = { title: "{{BRAND_NAME}} CMS — Sign in" };', "tenant mark"),
        ('<img src="/xago-logo.png" alt="Xago" ', '<img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" ',
         "tenant mark"),
        ("Back to xago.io", "Back to {{CANONICAL_DOMAIN}}", "the tenant's own domain"),
    ]),
    ("src/app/admin/[page]/page.tsx", [TENANT_ENV + ("tenant id env var name",)]),
    ("src/app/admin/[page]/Editor.tsx", []),
    ("src/app/admin/media/page.tsx", [
        ('export const metadata = { title: "Xago CMS — Images" };',
         'export const metadata = { title: "{{BRAND_NAME}} CMS — Images" };', "tenant mark"),
        ('<img src="/xago-logo.png" alt="Xago" ', '<img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" ',
         "tenant mark"),
    ]),
    ("src/app/admin/media/actions.ts", []),
    ("src/app/admin/leads/page.tsx", [
        ('export const metadata = { title: "Xago CMS — Enquiries" };',
         'export const metadata = { title: "{{BRAND_NAME}} CMS — Enquiries" };', "tenant mark"),
        ('<img src="/xago-logo.png" alt="Xago" ', '<img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" ',
         "tenant mark"),
    ]),
    ("src/app/admin/leads/actions.ts", []),
    ("src/app/api/contact/route.ts", [
        # the notify step, on top of a committed row
        ("""    return json({ ok: true }, 200);""",
         """    // X-0156, built here for the first time: the notification the Xago repo
    // specified and never got. It runs AFTER the row is committed and its
    // result is DISCARDED — a mail failure must never turn a saved enquiry
    // into a 500. What it failed to do stays visible in /admin/leads, which
    // counts rows with a null notified_at.
    await notifyLead(checked.value);

    return json({ ok: true }, 200);""",
         "the sender call — best-effort, on top of a committed row"),
        ('} from "@/lib/leads";',
         '} from "@/lib/leads";\nimport { notifyLead } from "@/lib/notify";',
         "import the sender"),
    ]),
]

MIGRATIONS = [f"db/migrations/{n}" for n in (
    "0001_cms_blocks.sql", "0002_cms_assets.sql", "0003_cms_posts.sql",
    "0004_cms_editors.sql", "0005_cms_audit_source.sql",
    "0006_cms_authors_editor.sql", "0007_cms_login_attempts.sql",
    "0008_cms_leads.sql", "0009_cms_audit_lead.sql",
)]

LEADS_APPEND = '''

/**
 * Record that a lead notification was delivered.
 *
 * `notified_at` shipped in 0008 with no writer, deliberately — the migration
 * header says why: the column exists before its writer so that a later
 * notification failure is VISIBLE (as a null in the inbox count) rather than
 * needing a second migration against live client data. This is that writer.
 *
 * Returns the error rather than throwing. The only caller is the best-effort
 * notifier, which must not be able to fail the request that committed the row:
 * a lead that was mailed but not stamped is a duplicate notification at worst,
 * a lead that was stored and then 500'd because the stamp failed is lost work.
 */
export async function setLeadNotified(id: string): Promise<{ error: string | null }> {
  if (!uuidLike.test(id)) return { error: "invalid lead id" };
  const { error } = await query(
    `cms_leads?id=eq.${id}&tenant_id=eq.${tenantId()}`,
    {
      method: "PATCH",
      body: JSON.stringify({ notified_at: new Date().toISOString() }),
    },
  );
  return { error };
}
'''


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_NOT_MEASURED = 3

MANIFEST_NAME = "MANIFEST.json"


def load_manifest(dest: Path) -> dict:
    """Read dest/MANIFEST.json, or raise NotMeasured naming why it could not.

    A manifest that is absent, unparseable, or carries no `files` list cannot
    verify anything. That is NOT_MEASURED, never a pass.
    """
    path = dest / MANIFEST_NAME
    try:
        manifest = json.loads(path.read_text())
    except FileNotFoundError:
        raise NotMeasured(f"no manifest at {path}")
    except OSError as exc:
        raise NotMeasured(f"manifest unreadable at {path}: {exc}")
    except json.JSONDecodeError as exc:
        raise NotMeasured(f"manifest at {path} is not JSON: {exc}")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise NotMeasured(f"manifest at {path} carries no files[] list")
    return manifest


class NotMeasured(Exception):
    """The manifest could not be read, so no verdict exists for any file."""


def verify(dest: Path = DEST) -> tuple[list[tuple[str, str]], list[str]]:
    """Re-hash every emitted template against its recorded template_sha256.

    Returns (verdicts, unlisted) where verdicts is [(path, MATCH|DRIFTED|MISSING)]
    in manifest order, and unlisted is on-disk files the manifest does not name.
    Raises NotMeasured if the manifest itself cannot be read.
    """
    manifest = load_manifest(dest)
    verdicts: list[tuple[str, str]] = []
    named = {MANIFEST_NAME}

    for entry in manifest["files"]:
        rel = entry.get("path")
        if not rel:
            raise NotMeasured("a manifest entry carries no path")
        named.add(rel)
        recorded = entry.get("template_sha256")
        if not recorded:
            raise NotMeasured(f"{rel} has no template_sha256 to verify against")
        target = dest / rel
        try:
            text = target.read_text()
        except OSError:
            verdicts.append((rel, "MISSING"))
            continue
        verdicts.append((rel, "MATCH" if sha(text) == recorded else "DRIFTED"))

    unlisted = sorted(
        str(p.relative_to(dest)) for p in dest.rglob("*")
        if p.is_file() and str(p.relative_to(dest)) not in named
    )
    return verdicts, unlisted


def run_verify(dest: Path = DEST) -> int:
    try:
        verdicts, unlisted = verify(dest)
    except NotMeasured as exc:
        print(f"VERIFY rails-templates: NOT_MEASURED — {exc}")
        return EXIT_NOT_MEASURED

    for rel, verdict in verdicts:
        if verdict != "MATCH":
            print(f"  {verdict:<8} {rel}")
    for rel in unlisted:
        print(f"  UNLISTED {rel}  (on disk, not in the manifest)")

    counts = {v: sum(1 for _, got in verdicts if got == v)
              for v in ("MATCH", "DRIFTED", "MISSING")}
    print(
        f"VERIFY rails-templates: {len(verdicts)} files — "
        f"{counts['MATCH']} MATCH · {counts['DRIFTED']} DRIFTED · "
        f"{counts['MISSING']} MISSING"
    )
    failed = counts["DRIFTED"] + counts["MISSING"]
    print("VERIFY rails-templates: PASS" if not failed else "VERIFY rails-templates: FAIL")
    return EXIT_OK if not failed else EXIT_DRIFT


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    inventory = []
    total_lines = 0

    for rel, subs in FILES:
        src = SITE / rel
        text = src.read_text()
        src_sha = sha(text)
        applied = []
        for find, repl, why in subs:
            if find not in text:
                raise SystemExit(f"SUBSTITUTION MISS in {rel}: {find[:70]!r}")
            n = text.count(find)
            text = text.replace(find, repl)
            applied.append({"find": find, "replace": repl, "why": why, "occurrences": n})
        if rel == "src/lib/leads.ts":
            text += LEADS_APPEND
            applied.append({
                "append": "setLeadNotified",
                "why": "the writer for the notified_at column 0008 shipped without one",
            })
        dest = DEST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        lines = len(text.splitlines())
        total_lines += lines
        tokens = sorted({t for t in (
            "CMS_TENANT_ENV", "MEDIA_BUCKET", "COOKIE_PREFIX", "ADMIN_HOSTS_JSON",
            "BRAND_NAME", "LOGO_SRC", "CANONICAL_DOMAIN", "ADMIN_NAV_LINKS",
        ) if "{{%s}}" % t in text})
        inventory.append({
            "path": rel,
            "lines": lines,
            "classification": "parametric" if tokens else ("altered" if applied else "generic"),
            "tokens": tokens,
            "source_sha256": src_sha,
            "template_sha256": sha(text),
            "substitutions": applied,
        })

    # The sender. Written fresh (census §0.1: the source repo has 0 lines of
    # mail-sending code), so it has no source sha — it is not a copy of anything.
    notify = (DEST / "src/lib/notify.ts").read_text()
    notify_lines = len(notify.splitlines())
    total_lines += notify_lines
    inventory.append({
        "path": "src/lib/notify.ts",
        "lines": notify_lines,
        "classification": "fresh",
        "tokens": ["EMAIL_SEND_DOMAIN", "EMAIL_NOTIFY_TO"],
        "source_sha256": None,
        "template_sha256": sha(notify),
        "substitutions": [],
        "note": "Not ported. The source repo contains zero lines of mail-sending "
                "code; this is the writer that db/migrations/0008 created "
                "notified_at for and never got.",
    })

    for rel in MIGRATIONS:
        text = (SITE / rel).read_text()
        dest = DEST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        lines = len(text.splitlines())
        total_lines += lines
        inventory.append({
            "path": rel, "lines": lines, "classification": "generic",
            "tokens": [], "source_sha256": sha(text), "template_sha256": sha(text),
            "substitutions": [],
        })

    manifest = {
        "provenance": {
            "source_repo": str(XAGO),
            "source_commit": XAGO_COMMIT,
            "census": "docs/census/2026-08-17-xago-rails.md",
            "read_only": True,
            "copied": "2026-08-17",
        },
        "totals": {
            "template_files": len(inventory),
            "template_lines": total_lines,
        },
        "generated_not_templated": {
            "src/lib/cms.registry.tsx": "section_key -> component map. DERIVED from the "
                "build's own section-artifacts: the key IS the SectionArtifact's "
                "section_uid, verbatim.",
            "src/lib/puck/pages.ts": "the declared editable-page slug list.",
            "src/lib/puck/page-meta.ts": "labels for the picker, derived from the page ids.",
            "src/lib/puck/config.tsx": "per-section Puck field schemas, DERIVED from "
                "scripts/lib/slot_contract.template_contract() over each artifact's tsx.",
            "src/lib/notify.ts": "the Resend sender. Written fresh — the Xago repo has "
                "0 lines of mail-sending code (census §0.1).",
        },
        "cut": {
            "why": "This is a vertical slice: block store + media + lead capture + "
                   "sender + gate. Each cut file is present in the source repo and was "
                   "deliberately not emitted, so a later pass can add it without "
                   "re-censusing.",
            "blog": ["src/lib/blog/docx.ts", "src/lib/blog/editor-adapter.ts",
                     "src/lib/blog/editor-extensions.ts", "src/lib/blog/editor-schema.ts",
                     "src/lib/blog/schema.ts", "src/lib/blog/normalize.ts",
                     "src/lib/blog/query.ts", "src/app/admin/posts/*"],
            "legal": ["src/lib/legal/documents.ts", "src/lib/legal/editor-extensions.ts",
                      "src/lib/legal/html.ts", "src/lib/legal/schema.ts",
                      "src/app/admin/legal/*"],
            "editors_admin": ["src/app/admin/editors/*", "src/app/admin/account/*"],
            "consequence": "No blog or statutory-document editor is emitted, and editor "
                           "accounts must be provisioned by SQL rather than through the "
                           "UI. The emitted AdminHeader nav lists only emitted routes, so "
                           "nothing links to a cut surface.",
        },
        "tenant_specific_never_emitted": {
            "src/lib/puck/page-meta.ts": "hand-authored labels — GENERATED instead",
            "src/components/sections/contact-page/01-contact.tsx": "Xago's own copy",
            "scripts/ops/check-resend-dns.mjs": "the xago.io zone and Xago's DKIM key",
        },
        "files": inventory,
    }
    (DEST / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(inventory)} files, {total_lines} lines -> {DEST}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--verify", action="store_true",
        help="re-hash the emitted templates against MANIFEST.json instead of "
             "re-emitting; exit 0 all-match, 1 on drift, 3 if the manifest is unreadable",
    )
    args = parser.parse_args()
    if args.verify:
        sys.exit(run_verify())
    main()
