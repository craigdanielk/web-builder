-- ============================================================================
-- Migration: 0003_cms_posts
-- Blog / newsroom content model for the Xago CMS (task X-0114).
--
-- APPLIED 2026-07-30 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0003_cms_posts`). This file is the repo mirror —
-- prod must stay a function of a commit (see .claude/rules/vercel-deploy-sop.md),
-- so the SQL that ran lives here too.
--
-- Posts get their OWN table rather than living in `cms_blocks` because the
-- publish path for blocks is delete-all-then-insert per page: correct for a
-- section stack, destructive for an append-only archive.
-- See docs/deliverables/blog/NODE7-blog-end-state.md §1.8.
--
-- Tenant isolation mirrors cms_assets/cms_blocks: tenant_id on every row + RLS.
-- This database is SHARED with the north-star control-tower substrate, so
-- tenant scoping is not optional.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- cms_authors — bylines.
--
-- Ships seeded with a PLACEHOLDER byline. `/wp-json/wp/v2/users` returns 401
-- (`rest_user_cannot_view`), so only numeric WP author ids are retrievable:
-- 7 (11 posts) and 10 (the NGPES press release). Real names come from Jürgen or
-- Vee's WP access and backfill as one UPDATE keyed on wp_author_id. A generated
-- name is never acceptable — this is a licensed FSP's newsroom.
-- ---------------------------------------------------------------------------
create table if not exists public.cms_authors (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null,

    name            text not null,
    role            text,

    -- -> cms_assets.id. Deliberately NOT a foreign key, matching how the rest
    -- of the CMS references assets: a row may be authored before its avatar is
    -- uploaded, and asset replacement mints a new asset row.
    avatar_asset_id uuid,

    -- The mapping key that makes the placeholder -> real-byline backfill
    -- deterministic, and makes re-import idempotent.
    wp_author_id    integer,

    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    constraint cms_authors_unique_wp_id unique (tenant_id, wp_author_id)
);

create index if not exists cms_authors_tenant_idx
    on public.cms_authors (tenant_id, name);

-- ---------------------------------------------------------------------------
-- cms_posts — the newsroom archive.
-- ---------------------------------------------------------------------------
create table if not exists public.cms_posts (
    id              uuid primary key default gen_random_uuid(),
    tenant_id       uuid not null,

    slug            text not null,
    title           text not null,
    excerpt         text,

    -- The four categories that actually exist in the live WordPress taxonomy,
    -- measured 2026-07-30 from /wp-json/wp/v2/categories and ratified the same
    -- day. The Insight/Announcement/Company/Education set proposed by an
    -- earlier research pass exists in NO source system and is rejected here so
    -- an invented label cannot reach the database.
    category        text not null
        constraint cms_posts_category_check
        check (category in ('news', 'insights', 'press-releases', 'jurgen-kuhnel-insights')),

    body            jsonb not null,

    -- -> cms_assets.id. NULLABLE by design: featured_media is 0 on all 12 WP
    -- posts, covers are extracted from the first inline <img>, and 4 posts
    -- carry no image at all (they get the typographic no-cover treatment).
    cover_asset_id  uuid,

    -- -> cms_authors.id.
    author_id       uuid,

    status          text not null default 'draft'
        constraint cms_posts_status_check
        check (status in ('draft', 'published')),
    published_at    timestamptz,

    -- The original root-level WordPress permalink path, e.g. '/xago-milestones/'.
    -- Post URLs were bare root slugs, never under /news/, so the 12 legacy
    -- redirects (X-0126) are GENERATED from this column. Not optional.
    legacy_path     text,

    -- Source WP post id, so re-running the import updates rather than duplicates.
    wp_post_id      integer,

    seo_title       text,
    seo_description text,

    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),

    constraint cms_posts_unique_slug   unique (tenant_id, slug),
    constraint cms_posts_unique_wp_id  unique (tenant_id, wp_post_id)
);

-- Read path 1: the /news index — newest published first.
create index if not exists cms_posts_tenant_status_published_idx
    on public.cms_posts (tenant_id, status, published_at desc);

-- Read path 2: /news/category/[cat] archives.
create index if not exists cms_posts_tenant_category_idx
    on public.cms_posts (tenant_id, category, status, published_at desc);

-- Redirect-map generation (X-0126) scans by legacy path.
create index if not exists cms_posts_legacy_path_idx
    on public.cms_posts (tenant_id, legacy_path);

-- ---------------------------------------------------------------------------
-- updated_at triggers — same shape as cms_assets_touch_updated_at.
-- ---------------------------------------------------------------------------
create or replace function public.cms_posts_touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists cms_posts_set_updated_at on public.cms_posts;
create trigger cms_posts_set_updated_at
    before update on public.cms_posts
    for each row execute function public.cms_posts_touch_updated_at();

drop trigger if exists cms_authors_set_updated_at on public.cms_authors;
create trigger cms_authors_set_updated_at
    before update on public.cms_authors
    for each row execute function public.cms_posts_touch_updated_at();

-- ---------------------------------------------------------------------------
-- RLS — mirrors cms_assets exactly.
-- ---------------------------------------------------------------------------
alter table public.cms_posts   enable row level security;
alter table public.cms_authors enable row level security;

drop policy if exists cms_posts_tenant_isolation on public.cms_posts;
create policy cms_posts_tenant_isolation
    on public.cms_posts
    as permissive
    for all
    using  (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
    with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

drop policy if exists cms_authors_tenant_isolation on public.cms_authors;
create policy cms_authors_tenant_isolation
    on public.cms_authors
    as permissive
    for all
    using  (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
    with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

-- ---------------------------------------------------------------------------
-- Comments
-- ---------------------------------------------------------------------------
comment on table  public.cms_posts is 'Xago newsroom archive: one row per post, tenant-scoped. Separate from cms_blocks because the block publish path is delete-all-then-insert per page, which is wrong for an append-only archive.';

comment on column public.cms_posts.body is
$c$Structured document. Node vocabulary, CORRECTED against the measured 12-post WordPress corpus (2026-07-30):

  paragraph
  heading(level 2|3)
  list(ordered|unordered) + item
  link
  strong
  em
  figure(image, caption)

Anything else is dropped at import.

WHY this differs from the earlier research proposal (p/h2/a/strong/figure):
  - The corpus contains ZERO h2 and ZERO h3. Headings arrive as h4 (27) and h5
    (4) — WordPress-theme artefacts, not semantic levels — and are RE-LEVELLED
    to h2/h3 on import, or the article ships a broken heading outline.
  - Lists are real content: 32 <li> across 6 <ul> + 5 <ol>. The proposed schema
    had no list node at all, so it could not represent the corpus.
  - span (76) and div (70) are theme wrappers carrying no meaning: stripped.
  - b (21) and i (3) are presentational duplicates: normalised to strong / em.$c$;

comment on column public.cms_posts.category       is 'One of the four categories that exist in the live WP taxonomy. Enforced by CHECK so an invented label cannot be written.';
comment on column public.cms_posts.legacy_path    is 'Original root-level WP permalink path (e.g. /xago-milestones/). The redirect map is generated FROM this column — posts were never served under /news/.';
comment on column public.cms_posts.wp_post_id     is 'Source WordPress post id. Unique per tenant so re-import is idempotent.';
comment on column public.cms_posts.cover_asset_id is 'cms_assets.id. Nullable: featured_media is 0 on every WP post, covers are the extracted first inline <img>, and 4 posts have no image (typographic no-cover treatment).';

comment on table  public.cms_authors              is 'Xago newsroom bylines, tenant-scoped. Seeded with a placeholder until a human supplies the real names — never a generated one.';
comment on column public.cms_authors.wp_author_id is 'Source WP author id (7 or 10). The mapping key that makes the placeholder -> real-byline backfill a single deterministic UPDATE.';
