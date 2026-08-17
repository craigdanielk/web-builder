-- ============================================================================
-- Migration: 0001_cms_blocks
-- Content store for the Xago templatised CMS.
--
-- Each row is one rendered *block* (a section instance) on a page. The Xago
-- site template (Next.js App-Router, forked from the Trend Digital design
-- system) renders every page by selecting the tenant's blocks for that page,
-- ordered by `position`, and hydrating the matching section component with the
-- block's `content` JSON. This is the substrate the whole site renders from.
--
-- Tenant isolation is non-negotiable (see CLAUDE.md):
--   * every row carries tenant_id
--   * RLS forces every read/write to filter by tenant_id
--
-- End-state assertion satisfied by this migration:
--   xago-cms-content-store-live  ->  db_column_exists(cms_blocks.tenant_id)
--
-- NOTE: This SQL is the *design* deliverable produced by the content/design
-- brief (#33360). Applying it to Supabase is the schema-migration brief
-- (#33363, apply-schema-migration) — the execution plane for #33360 has no DDL
-- credentials (.env.tenant is a names-only scaffold; the MCP is PostgREST-only).
-- ============================================================================

create extension if not exists "pgcrypto";

create table if not exists public.cms_blocks (
    id           uuid primary key default gen_random_uuid(),

    -- Tenant isolation key (the assertion target). Never nullable.
    tenant_id    uuid not null,

    -- Which page this block belongs to, e.g. 'homepage', 'pricing-page'.
    page_slug    text not null,

    -- Stable key of the section component this block hydrates, matching the
    -- component tree, e.g. 'homepage/01-hero', 'pricing-page/02-pricing_table'.
    section_key  text not null,

    -- Design-system archetype/variant (mirrors site-manifest.json), e.g.
    -- archetype 'HERO', variant 'trust-hero'. Kept denormalised for fast render.
    archetype    text,
    variant      text,

    -- Vertical order of the block within the page.
    position     integer not null default 0,

    -- The editable copy/props for the section component, as authored by the CMS.
    content      jsonb not null default '{}'::jsonb,

    -- Publishing lifecycle: 'draft' | 'published' | 'archived'.
    status       text not null default 'draft'
                     check (status in ('draft', 'published', 'archived')),

    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),

    -- One block per (tenant, page, section, position).
    constraint cms_blocks_unique_slot
        unique (tenant_id, page_slug, section_key, position)
);

-- Render path: "give me tenant T's published blocks for page P, in order".
create index if not exists cms_blocks_render_idx
    on public.cms_blocks (tenant_id, page_slug, status, position);

-- keep updated_at fresh
create or replace function public.cms_blocks_touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists cms_blocks_set_updated_at on public.cms_blocks;
create trigger cms_blocks_set_updated_at
    before update on public.cms_blocks
    for each row execute function public.cms_blocks_touch_updated_at();

-- ----------------------------------------------------------------------------
-- Row-level security: every access is scoped to the caller's tenant_id.
-- The tenant is read from the JWT claim `tenant_id` (Supabase auth) so the
-- app can never read or write across tenants.
-- ----------------------------------------------------------------------------
alter table public.cms_blocks enable row level security;

drop policy if exists cms_blocks_tenant_isolation on public.cms_blocks;
create policy cms_blocks_tenant_isolation
    on public.cms_blocks
    as permissive
    for all
    using  (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
    with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

comment on table  public.cms_blocks             is 'Xago templatised CMS content store: one row per rendered section instance, tenant-scoped.';
comment on column public.cms_blocks.tenant_id   is 'Tenant isolation key. RLS forces every read/write to filter on this.';
comment on column public.cms_blocks.section_key is 'Stable key of the Next.js section component this block hydrates.';
comment on column public.cms_blocks.content     is 'Authored copy/props (JSON) passed to the section component at render.';
