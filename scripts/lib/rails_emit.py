"""Emit the CMS + email rails into a scaffolded site, for a tenant that declares them.

WHAT THIS IS. `platform_modules()` resolves whether a tenant declared
`cms: block-store` / `email: resend` (see `lib/tenant_context.declared_cms` and
the R2 commit). This module is what a declaration BUYS: a Supabase-table-backed
block store with a Puck editor, a media library, a lead-capture endpoint, and
the Resend notifier — copied out of `rails-templates/cms/` with the tenant's
declared values injected.

WHERE THE TEMPLATES CAME FROM. The Xago tenant repo at commit
`ff5c5cd8` — the only implementation of this CMS that exists — read READ-ONLY
and censused in `docs/census/2026-08-17-xago-rails.md`. Per-file provenance,
every substitution applied, and the list of source files deliberately NOT
emitted are in `rails-templates/cms/MANIFEST.json`. At ~5,800 lines the
templates are files on disk, not string literals in this file: `stage_deploy`
already ships `lib/shopify` as string literals and that is at the limit of what
is readable.

THE ONE CONSTRAINT FROM THE OPERATOR — `section_key` IS `section_uid`.
See `generate_registry`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

try:  # imported both as `lib.rails_emit` and as a sibling of orchestrate.py
    from . import slot_contract
except ImportError:  # pragma: no cover - direct-script import path
    import slot_contract  # type: ignore

#: `rails-templates/` lives beside `scripts/`, at the web-builder repo root.
TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "rails-templates" / "cms"


class RailsDeclarationMissing(Exception):
    """A declared module needs a value the tenant has not collected.

    Distinct from `PlatformNotDeclared` (the MODULE itself is undeclared, and the
    stage is then absent). Here the module IS declared and a required value is
    missing, which is a build refusal naming the field — not a default. A
    fabricated bucket name writes media into a bucket nobody owns; a fabricated
    host allowlist serves a tenant-branded credential surface on a host the
    tenant does not control, which is the phishing shape the Xago middleware
    exists to refuse.
    """


# ── Token resolution ───────────────────────────────────────────────────────
# Free-form declared values, so they are read straight off `phase0_field_values`
# rather than through `declared_platform()`'s closed-vocabulary reader. The
# vocabulary readers own `cms` and `email` themselves; these are the parameters
# of an already-resolved declaration.

#: Fields a declared `cms: block-store` cannot be emitted without.
CMS_REQUIRED_FIELDS = ("cms_media_bucket", "cms_admin_hosts")

#: Fields a declared `email: resend` is emitted WITHOUT when absent — recorded,
#: not refused. The sender reports itself unconfigured at runtime and the
#: un-notified count in /admin/leads is the visible consequence; that is what
#: `cms_leads.notified_at` was created (with no writer) to make visible. A build
#: refusal here would block a whole site on a mailbox address.
EMAIL_SOFT_FIELDS = ("email_send_domain", "email_notify_to")


def _field(tenant_context: dict | None, key: str) -> str:
    values = (tenant_context or {}).get("phase0_field_values") or {}
    raw = values.get(key)
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple)):
        return ",".join(str(v).strip() for v in raw if str(v).strip())
    return str(raw).strip()


def resolve_tokens(
    tenant_context: dict | None,
    *,
    tenant_slug: str,
    page_ids: list[str],
    emit_email: bool,
) -> dict:
    """The declared parameters of this emission, or refuse naming the field.

    Returns ``{"tokens": {...}, "undeclared": [...], "editable_pages": [...]}``.
    `undeclared` names every soft field that was absent, so the emission manifest
    records the difference between "declared and empty" and "never collected".
    """
    missing = [f for f in CMS_REQUIRED_FIELDS if not _field(tenant_context, f)]
    if missing:
        raise RailsDeclarationMissing(
            f"tenant '{tenant_slug}' declares cms=block-store but does not declare "
            f"{', '.join(missing)}. Collect them at phase 0. They are not defaulted: "
            "a guessed media bucket writes into storage nobody owns, and a guessed "
            "admin host allowlist serves a tenant-branded login page on a host the "
            "tenant does not control."
        )

    declared_pages = [p for p in _field(tenant_context, "cms_editable_pages").split(",") if p.strip()]
    declared_pages = [p.strip() for p in declared_pages]
    if declared_pages:
        # A declared page the build did not produce is dropped rather than
        # emitted: /admin would offer an editor a page with no sections behind it.
        editable = [p for p in declared_pages if p in page_ids]
    else:
        editable = list(page_ids)

    hosts = [h.strip().lower() for h in _field(tenant_context, "cms_admin_hosts").split(",") if h.strip()]
    canonical = _field(tenant_context, "canonical_domain")

    undeclared: list[str] = []
    if not declared_pages:
        undeclared.append("cms_editable_pages")
    if not canonical:
        undeclared.append("canonical_domain")
    email_tokens = {"EMAIL_SEND_DOMAIN": "", "EMAIL_NOTIFY_TO": ""}
    if emit_email:
        for f in EMAIL_SOFT_FIELDS:
            value = _field(tenant_context, f)
            if not value:
                undeclared.append(f)
            email_tokens[f.upper()] = value

    tokens = {
        # R2's env_names for cms: block-store. The name, never a value.
        "CMS_TENANT_ENV": "CMS_TENANT_ID",
        "MEDIA_BUCKET": _field(tenant_context, "cms_media_bucket"),
        "COOKIE_PREFIX": re.sub(r"[^a-z0-9]+", "_", tenant_slug.lower()).strip("_") or "cms",
        "ADMIN_HOSTS_JSON": json.dumps(hosts),
        "BRAND_NAME": _brand_name(tenant_context, tenant_slug),
        "LOGO_SRC": _field(tenant_context, "logo_url") or "/logo.svg",
        "CANONICAL_DOMAIN": canonical or "the website",
        **email_tokens,
    }
    return {"tokens": tokens, "undeclared": undeclared, "editable_pages": editable}


def _brand_name(tenant_context: dict | None, tenant_slug: str) -> str:
    declared = _field(tenant_context, "brand_name") or _field(tenant_context, "company_name")
    if declared:
        return declared
    return " ".join(w.capitalize() for w in re.split(r"[-_]+", tenant_slug) if w)


# ── The build's own section identity ───────────────────────────────────────

def load_section_index(output_dir: Path) -> dict:
    """`{page_id: [{"uid", "file", "component", "archetype", "variant", "tsx"}]}`.

    Read from `output/<project>/section-artifacts/<page_id>/<NN>-<name>.json`,
    which is where the build records what it actually emitted — including
    `section_uid`. Reading the artifacts rather than zipping `site_manifest`
    against `section_files_by_page` matters: an omitted section is absent from
    the artifacts and present in the manifest, so zipping would shift every
    subsequent uid by one and silently mis-key the whole registry.
    """
    base = output_dir / "section-artifacts"
    index: dict[str, list[dict]] = {}
    if not base.is_dir():
        return index
    for page_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        entries: list[dict] = []
        for art_path in sorted(page_dir.glob("*.json")):
            try:
                art = json.loads(art_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            uid = str(art.get("section_uid") or "").strip()
            if not uid:
                continue
            entries.append({
                "uid": uid,
                "file": art_path.stem,
                "archetype": art.get("archetype") or "",
                "variant": art.get("variant") or "",
                "tsx": art.get("tsx") or "",
                "index": art.get("section_index", 0),
            })
        if entries:
            index[page_dir.name] = entries
    return index


def _component_ident(page_id: str, entry: dict, seen: set[str]) -> str:
    """A unique TS identifier for one section's default import."""
    base = "S" + re.sub(r"[^A-Za-z0-9]", "", page_id.title()) + re.sub(
        r"[^A-Za-z0-9]", "", entry["file"].title()
    )
    ident = base
    n = 2
    while ident in seen:
        ident = f"{base}{n}"
        n += 1
    seen.add(ident)
    return ident


def _anchor(entry: dict) -> str:
    """A human anchor id for a section, from its archetype and ordinal.

    `section_key` is a `section_uid` under this emission, so the Xago rule —
    strip the numeric prefix off "04b-why_choose" — has nothing to strip. The
    anchor is derived from the artifact's file stem, which IS the ordered,
    archetype-named identity the build gave the section.
    """
    stem = re.sub(r"^\d+[a-z]?-", "", entry["file"])
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or entry["uid"]


# ── Generated files ────────────────────────────────────────────────────────

def generate_registry(index: dict, editable_pages: list[str]) -> str:
    """`src/lib/cms.registry.tsx` — section_key -> component.

    ═══ THE OPERATOR'S CONSTRAINT, AND WHY IT IS HERE ═══

    Every key below is a SectionArtifact's `section_uid`, VERBATIM. Not a
    hand-named slug like Xago's "04b-why_choose", and not a re-derivation: the
    exact twelve hex characters `stage_sections` wrote into
    `section-artifacts/<page>/<file>.json` and stamped into the component's own
    `data-section-uid` attribute.

    One coordinate system, end to end. A comment left on a CMS block names
    `(page_slug, section_key)`; a copy-finding names `(page_id, section_uid)`;
    `cms_blocks`' unique constraint is on `(tenant_id, page_slug, section_key,
    position)`. With `section_key ≡ section_uid` those are the same coordinate
    and a comment routes to a finding with ZERO mapping. Introduce any
    translation here — a slug, a positional index, a display name — and the
    routing needs a lookup table that can be wrong, which is how a comment on
    one section becomes a finding against another.
    """
    lines = [
        "// section_key -> section component registry. GENERATED by",
        "// scripts/lib/rails_emit.py from this build's own section-artifacts.",
        "//",
        "// EVERY KEY IS A section_uid, VERBATIM — the same value the component",
        "// carries in its data-section-uid attribute and the same value a",
        "// copy-finding names. Do not rename these to slugs: cms_blocks.section_key,",
        "// the finding coordinate and this key are one coordinate system, which is",
        "// what lets a comment on a block route to a finding with no mapping.",
        "",
        'import type { ComponentType } from "react";',
        "",
    ]
    seen: set[str] = set()
    idents: dict[str, dict[str, str]] = {}
    for page_id in sorted(index):
        idents[page_id] = {}
        for entry in index[page_id]:
            ident = _component_ident(page_id, entry, seen)
            idents[page_id][entry["uid"]] = ident
            lines.append(
                f'import {ident} from "@/components/sections/{page_id}/{entry["file"]}";'
            )
    lines += [
        "",
        "// Sections are prop-driven, not `content`-driven: the build bakes each",
        "// harvested value in as a default prop and the CMS overrides it by name.",
        "export type SectionComponent = ComponentType<Record<string, unknown>>;",
        "",
        "type PageDef = {",
        "  registry: Record<string, SectionComponent>;",
        "  order: string[];",
        "  /** section_uid -> the human anchor id the wrapper renders. */",
        "  anchors: Record<string, string>;",
        "};",
        "",
        "export const PAGES: Record<string, PageDef> = {",
    ]
    for page_id in sorted(index):
        if page_id not in editable_pages:
            continue
        entries = index[page_id]
        reg = ", ".join(f'"{e["uid"]}": {idents[page_id][e["uid"]]}' for e in entries)
        order = ", ".join(f'"{e["uid"]}"' for e in entries)
        anchors = ", ".join(f'"{e["uid"]}": "{_anchor(e)}"' for e in entries)
        lines += [
            f'  {json.dumps(page_id)}: {{',
            f"    registry: {{ {reg} }},",
            f"    order: [{order}],",
            f"    anchors: {{ {anchors} }},",
            "  },",
        ]
    lines += ["};", ""]
    return "\n".join(lines)


def generate_pages(editable_pages: list[str]) -> str:
    listed = ", ".join(json.dumps(p) for p in editable_pages)
    return f'''// Server-safe list of pages that have a Puck editor config. GENERATED.
//
// The Puck config (config.tsx) is a "use client" module, so a Server Component
// cannot read its keys. Server code (the /admin picker and the editor route's
// existence check) reads this plain data list instead.
//
// Derived from the tenant's declared `cms_editable_pages`, intersected with the
// pages this build actually produced — a declared page with no sections behind
// it would show in the picker and open on nothing.
export const EDITABLE_PAGES = [{listed}] as const;

export function isEditablePage(slug: string): boolean {{
  return (EDITABLE_PAGES as readonly string[]).includes(slug);
}}
'''


def generate_page_meta(editable_pages: list[str], index: dict) -> str:
    """`page-meta.ts` — labels for the picker.

    Xago's version is 35 lines of hand-authored prose ("Per-transaction pricing
    tiers and trust badges") and is TENANT-SPECIFIC: it cannot be scaffolded.
    What CAN be derived is the slug's title case, the public route, and a
    factual description — the section archetypes the page is built from. That
    reads as a machine wrote it, which is true, and it is strictly better than
    an invented sentence about a page this code has never seen.
    """
    rows = []
    for slug in editable_pages:
        entries = index.get(slug, [])
        archs = ", ".join(dict.fromkeys(e["archetype"].lower() for e in entries if e["archetype"]))
        label = " ".join(w.capitalize() for w in re.split(r"[-_]+", slug) if w)
        route = "/" if slug == "homepage" else f"/{slug}"
        desc = f"{len(entries)} sections: {archs}." if archs else f"{len(entries)} sections."
        rows.append(
            f"  {json.dumps(slug)}: {{ label: {json.dumps(label)}, "
            f"description: {json.dumps(desc)}, route: {json.dumps(route)}, "
            f'group: "Pages" }},'
        )
    body = "\n".join(rows)
    return f'''// Human-facing metadata for the CMS page picker. GENERATED.
//
// The reference implementation's version is hand-authored prose and is tenant
// specific — it cannot be scaffolded. What is derivable is the slug, the public
// route, and the archetypes the page is composed of. A description that names
// the sections is a fact about the page; an invented sentence about its purpose
// would not be.
export type PageMeta = {{ label: string; description: string; route: string | null; group: string }};

export const PAGE_META: Record<string, PageMeta> = {{
{body}
}};

export const GROUP_ORDER = ["Pages"] as const;

export function metaFor(slug: string): PageMeta {{
  return PAGE_META[slug] ?? {{ label: slug, description: "", route: null, group: "Other" }};
}}
'''


# ── Puck field derivation ──────────────────────────────────────────────────
# VERDICT: DERIVABLE, and derived from two sources that must agree.
#
#   1. The section's own `interface <X>Props` — the authority on WHICH props
#      exist and which are arrays. A field offered for a prop the component does
#      not accept is a field an editor can fill with no effect, which is the
#      specific dishonesty this must not ship.
#   2. `lib/slot_contract.infer_type()` on the prop's snake_case name — the
#      authority on WHAT KIND of value it wants (short text, long text, image,
#      url). It is the same inference the fill path uses, so the editor is
#      offered the same shape the build filled.

_PROP_RE = re.compile(r"^\s*(\w+)\??:\s*([\w\[\]]+);", re.M)
_ARRAY_T_RE = re.compile(r"^(\w+)\[\]$")

#: slot_contract type -> field helper in the emitted `puck/fields.tsx`.
_FIELD_FOR_TYPE = {
    "text-short": "text",
    "cta": "text",
    "data": "text",
    "alt": "text",
    "url": "text",
    "unclassified": "text",
    "text-long": "textarea",
    "disclaimer": "textarea",
    "image": "media",
}


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _iface_body(tsx: str, name: str) -> str | None:
    m = re.search(r"(?:interface|type)\s+" + re.escape(name) + r"\s*=?\s*\{(.*?)\n\}", tsx, re.S)
    return m.group(1) if m else None


def derive_section_fields(tsx: str) -> dict:
    """`{prop_name: {"field": "text"|"textarea"|"media"|"array", ...}}`.

    Returns `{}` when the component declares no Props interface — which is a
    section with no editable slots at all (CTA/centered, for one), and the
    correct emission for it is a component with an empty field set rather than
    a guessed one.
    """
    m = re.search(r"interface\s+(\w*Props)\s*\{", tsx)
    if not m:
        return {}
    body = _iface_body(tsx, m.group(1))
    if body is None:
        return {}
    out: dict[str, dict] = {}
    for prop, tstr in _PROP_RE.findall(body):
        arr = _ARRAY_T_RE.match(tstr)
        if arr:
            item_body = _iface_body(tsx, arr.group(1))
            item_fields: dict[str, str] = {}
            if item_body:
                for sub, subt in _PROP_RE.findall(item_body):
                    if _ARRAY_T_RE.match(subt):
                        continue  # nested arrays are not offered; recorded as skipped
                    item_fields[sub] = _FIELD_FOR_TYPE.get(
                        slot_contract.infer_type(_snake(sub)), "text"
                    )
            if not item_fields:
                # An array whose item shape cannot be read is NOT offered as a
                # free-form array: Puck would let an editor add empty rows the
                # component renders as blanks.
                continue
            out[prop] = {"field": "array", "item_fields": item_fields}
        elif tstr == "string":
            out[prop] = {"field": _FIELD_FOR_TYPE.get(
                slot_contract.infer_type(_snake(prop)), "text"
            )}
        # booleans, numbers and unresolvable types are deliberately skipped:
        # `fields.tsx` has a `bool` helper but nothing here can tell a boolean
        # that toggles a visual variant from one that gates a legal notice.
    return out


def _label(prop: str) -> str:
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", prop).replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def generate_puck_config(index: dict, editable_pages: list[str]) -> tuple[str, dict]:
    """`src/lib/puck/config.tsx` plus a coverage record.

    The coverage record is the honest half: it counts, per page, how many
    sections got a non-empty field set and how many did not, so
    `rails-emission.json` says how much of the editor is real.
    """
    header = [
        '"use client";',
        'import type { Config, Field } from "@measured/puck";',
        'import { text, textarea, array, media } from "@/lib/puck/fields";',
        "",
        "// GENERATED by scripts/lib/rails_emit.py.",
        "//",
        "// Every field below corresponds to a prop the section's own Props interface",
        "// declares. Nothing is offered that the component does not accept: a field",
        "// an editor can fill with no visible effect is worse than a missing one,",
        "// because it reads as a broken section rather than an unfinished editor.",
        "// The field KIND comes from lib/slot_contract.infer_type() on the prop's",
        "// snake_case name — the same inference the build's fill path used.",
        "",
    ]
    seen: set[str] = set()
    idents: dict[str, dict[str, str]] = {}
    for page_id in sorted(index):
        if page_id not in editable_pages:
            continue
        idents[page_id] = {}
        for entry in index[page_id]:
            ident = "C" + _component_ident(page_id, entry, seen)[1:]
            idents[page_id][entry["uid"]] = ident
            header.append(
                f'import {ident} from "@/components/sections/{page_id}/{entry["file"]}";'
            )

    body = [
        "",
        "type Comp = NonNullable<Config[\"components\"]>[string];",
        "const wrap = (",
        "  label: string,",
        "  fields: Record<string, Field>,",
        "  Component: React.ComponentType<Record<string, unknown>>,",
        "): Comp => ({",
        "  label,",
        "  fields,",
        "  defaultProps: {},",
        "  // Props are SPREAD, not passed as `content`: the generated sections take",
        "  // named props with the harvested value as each default.",
        "  render: ({ puck, editMode, id, ...props }: Record<string, unknown>) => (",
        "    <Component {...props} />",
        "  ),",
        "});",
        "",
        'const rootPassthrough = { render: ({ children }: { children?: React.ReactNode }) => <>{children}</> };',
        "",
    ]

    coverage: dict[str, dict] = {}
    page_vars: list[tuple[str, str]] = []
    for page_id in sorted(index):
        if page_id not in editable_pages:
            continue
        var = "cfg_" + re.sub(r"[^A-Za-z0-9]", "_", page_id)
        page_vars.append((page_id, var))
        with_fields = 0
        body.append(f'const {var}: Config["components"] = {{')
        for entry in index[page_id]:
            fields = derive_section_fields(entry["tsx"])
            if fields:
                with_fields += 1
            rendered = []
            for prop, spec in fields.items():
                if spec["field"] == "array":
                    inner = ", ".join(
                        f"{sub}: {helper}({json.dumps(_label(sub))})"
                        for sub, helper in spec["item_fields"].items()
                    )
                    rendered.append(
                        f"{prop}: array({{ {inner} }}, undefined, {json.dumps(_label(prop))})"
                    )
                else:
                    rendered.append(
                        f"{prop}: {spec['field']}({json.dumps(_label(prop))})"
                    )
            label = f'{entry["archetype"] or entry["file"]} · {entry["variant"]}'.strip(" ·")
            key = f'{page_id}__{entry["uid"]}'
            body.append(
                f'  {json.dumps(key)}: wrap({json.dumps(label)}, '
                f'{{ {", ".join(rendered)} }}, {idents[page_id][entry["uid"]]}),'
            )
        body.append("};")
        body.append("")
        coverage[page_id] = {
            "sections": len(index[page_id]),
            "sections_with_editable_fields": with_fields,
            "sections_with_no_editable_fields": len(index[page_id]) - with_fields,
        }

    body.append("// page_slug -> Puck config (which components may appear on that page).")
    body.append("export const CONFIGS: Record<string, Config> = {")
    for page_id, var in page_vars:
        body.append(f"  {json.dumps(page_id)}: {{ components: {var}, root: rootPassthrough }},")
    body.append("};")
    body.append("")
    return "\n".join(header + body), coverage


# ── Emission ───────────────────────────────────────────────────────────────

#: Template paths that are only emitted when `email: resend` is declared. The
#: block store stands on its own; lead capture without a notifier does not need
#: to be cut, but the notifier without a declaration must not be emitted.
EMAIL_ONLY = ("src/lib/notify.ts",)

#: Admin nav entries, keyed by the route each needs. Generated rather than
#: fixed so the nav lists only what THIS emission emitted — the reference
#: implementation's five-entry list points at two routes this slice cuts.
_NAV = [
    ("pages", "/admin", "Pages"),
    ("leads", "/admin/leads", "Enquiries"),
]

#: Every route the emission creates. The gate asserts each one exists in the
#: `next build` output; a template that stops emitting a route must show up as
#: a gate failure, not as a route that quietly disappeared.
EMITTED_ROUTES = (
    "/admin",
    "/admin/login",
    "/admin/[page]",
    "/admin/leads",
    "/admin/media",
    "/api/contact",
)


def emit_rails(
    site_dir: Path,
    output_dir: Path,
    *,
    tenant_context: dict | None,
    tenant_slug: str,
    declared_cms: str,
    declared_email: str,
    templates_root: Path | None = None,
) -> dict:
    """Copy + inject the rails into `site_dir`. Returns the emission manifest.

    Raises `RailsDeclarationMissing` when a declared module lacks a required
    declared value. Never called for an undeclared module — an undeclared
    tenant's stage is ABSENT, which is the caller's decision, not a branch here.
    """
    if declared_cms != "block-store":
        raise ValueError(f"emit_rails called with cms={declared_cms!r}")
    root = templates_root or TEMPLATES_ROOT
    manifest = json.loads((root / "MANIFEST.json").read_text())

    index = load_section_index(output_dir)
    emit_email = declared_email == "resend"
    resolved = resolve_tokens(
        tenant_context,
        tenant_slug=tenant_slug,
        page_ids=sorted(index),
        emit_email=emit_email,
    )
    tokens, editable = resolved["tokens"], resolved["editable_pages"]
    tokens["ADMIN_NAV_LINKS"] = "[\n" + "".join(
        f'  {{ key: "{k}", href: "{h}", label: {json.dumps(l)} }},\n' for k, h, l in _NAV
    ) + "]"

    written: list[str] = []
    unresolved: list[str] = []
    for entry in manifest["files"]:
        rel = entry["path"]
        if rel in EMAIL_ONLY and not emit_email:
            continue
        text = (root / rel).read_text()
        for token, value in tokens.items():
            text = text.replace("{{%s}}" % token, value)
        left = re.findall(r"\{\{([A-Z_]+)\}\}", text)
        if left:
            unresolved.append(f"{rel}: {', '.join(sorted(set(left)))}")
        dest = site_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        written.append(rel)

    # notify.ts is in the manifest only if the template build put it there; it is
    # a fresh file, so emit it explicitly when email is declared.
    if emit_email and "src/lib/notify.ts" not in written:
        text = (root / "src/lib/notify.ts").read_text()
        for token, value in tokens.items():
            text = text.replace("{{%s}}" % token, value)
        (site_dir / "src/lib/notify.ts").parent.mkdir(parents=True, exist_ok=True)
        (site_dir / "src/lib/notify.ts").write_text(text)
        written.append("src/lib/notify.ts")

    if unresolved:
        raise RailsDeclarationMissing(
            "unresolved template tokens after injection — a token with no value is "
            "a `{{NAME}}` shipped into a running site:\n  " + "\n  ".join(unresolved)
        )

    generated = {
        "src/lib/cms.registry.tsx": generate_registry(index, editable),
        "src/lib/puck/pages.ts": generate_pages(editable),
        "src/lib/puck/page-meta.ts": generate_page_meta(editable, index),
    }
    config_src, coverage = generate_puck_config(index, editable)
    generated["src/lib/puck/config.tsx"] = config_src
    for rel, text in generated.items():
        dest = site_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
        written.append(rel)

    emission = {
        "cms": declared_cms,
        "email": declared_email,
        "tenant": tenant_slug,
        "provenance": manifest["provenance"],
        "templates_emitted": len([w for w in written if w not in generated]),
        "generated_emitted": sorted(generated),
        "files": sorted(written),
        "lines": sum(
            len((site_dir / w).read_text().splitlines()) for w in written
        ),
        "editable_pages": editable,
        # section_key ≡ section_uid, stated in the artifact as well as in code.
        "section_key_is_section_uid": True,
        "section_keys": {p: [e["uid"] for e in index[p]] for p in editable if p in index},
        "puck_config": {
            "verdict": "DERIVED",
            "derived_from": [
                "the section's own `interface <X>Props` (which props exist)",
                "lib/slot_contract.infer_type() on the snake_case prop name (what kind)",
            ],
            "coverage": coverage,
        },
        "undeclared_fields": resolved["undeclared"],
        "migrations_emitted_not_applied": sorted(
            w for w in written if w.startswith("db/migrations/")
        ),
        "cut": manifest["cut"],
        "routes": list(EMITTED_ROUTES),
    }
    (output_dir / "rails-emission.json").write_text(json.dumps(emission, indent=2) + "\n")
    return emission
