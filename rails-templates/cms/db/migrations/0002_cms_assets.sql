-- ============================================================================
-- Migration: 0002_cms_assets
-- Media asset registry for the Xago templatised CMS (task X-0108).
--
-- APPLIED 2026-07-29 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0002_cms_assets`). This file is the repo mirror —
-- prod must stay a function of a commit (see .claude/rules/vercel-deploy-sop.md),
-- so the SQL that ran lives here too.
--
-- One row per uploaded original. Renditions are NOT stored: Vercel Image
-- Optimization derives every size on request from `storage_path`, so the
-- bucket holds exactly one normalised WebP master per asset.
--
-- Companion storage bucket (created via the storage API, not SQL):
--   `xago-media` — public read, 15MB cap, image mime types only.
--
-- Tenant isolation mirrors cms_blocks: tenant_id on every row + RLS. This
-- database is SHARED with the north-star control-tower substrate, so tenant
-- scoping is not optional.
-- ============================================================================

create table if not exists public.cms_assets (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid not null,

    -- Path inside the storage bucket. CONTENT-HASHED and never overwritten:
    -- Vercel caches transforms for max(upstream max-age, minimumCacheTTL) and
    -- does NOT invalidate on redeploy, so reusing a path would serve a stale
    -- image. Replacing an image creates a new asset row, not a new file here.
    storage_path  text not null,

    -- Default alt text. Per-usage overrides live on the consuming block, since
    -- the same image often needs different alt text on different pages.
    alt           text not null default '',

    -- Focal point in normalised 0..1 coords. Vercel's transform API exposes
    -- only w/q and cannot crop, so art direction is CSS object-position driven
    -- from these. Defaults to dead centre.
    focal_x       numeric not null default 0.5 check (focal_x between 0 and 1),
    focal_y       numeric not null default 0.5 check (focal_y between 0 and 1),

    -- Intrinsic dimensions of the master, for next/image sizing without a fetch.
    width         integer,
    height        integer,
    mime          text not null default 'image/webp',
    bytes         integer,

    -- sha256 of the ORIGINAL upload: lets a re-upload of the same file resolve
    -- to the existing asset instead of duplicating it.
    checksum      text,

    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now(),

    constraint cms_assets_unique_path unique (tenant_id, storage_path)
);

create index if not exists cms_assets_tenant_idx
    on public.cms_assets (tenant_id, created_at desc);

create index if not exists cms_assets_checksum_idx
    on public.cms_assets (tenant_id, checksum);

create or replace function public.cms_assets_touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists cms_assets_set_updated_at on public.cms_assets;
create trigger cms_assets_set_updated_at
    before update on public.cms_assets
    for each row execute function public.cms_assets_touch_updated_at();

alter table public.cms_assets enable row level security;

drop policy if exists cms_assets_tenant_isolation on public.cms_assets;
create policy cms_assets_tenant_isolation
    on public.cms_assets
    as permissive
    for all
    using  (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
    with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

comment on table  public.cms_assets              is 'Xago CMS media registry: one row per uploaded original, tenant-scoped. Renditions derived at the CDN, never stored.';
comment on column public.cms_assets.storage_path is 'Content-hashed path in the media bucket. Never overwritten — replacement creates a new row (Vercel transform cache does not invalidate on redeploy).';
comment on column public.cms_assets.focal_x      is 'Normalised focal point X (0..1). Drives CSS object-position; Vercel cannot crop.';
comment on column public.cms_assets.checksum     is 'sha256 of the original upload, for de-duplicating re-uploads.';
