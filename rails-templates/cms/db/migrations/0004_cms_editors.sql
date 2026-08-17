-- ============================================================================
-- Migration: 0004_cms_editors
-- Per-user admin accounts + edit attribution for the Xago CMS (task X-0100).
--
-- APPLIED 2026-07-30 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0004_cms_editors`). This file is the repo mirror —
-- prod must stay a function of a commit (see .claude/rules/vercel-deploy-sop.md),
-- so the SQL that ran lives here too.
--
-- WHY NOT auth.users
-- This database is SHARED with the north-star control-tower substrate, and
-- `auth.users` already holds 10 control-tower identities. Registering Xago
-- client staff there would mint a JWT that is valid for the WHOLE project, with
-- RLS as the only boundary between a marketing-site editor and the control
-- tower. A tenant-scoped editors table sitting behind the existing HMAC cookie
-- keeps the blast radius on the website. Ratified 2026-07-30, contract §1.2.
--
-- WHY NOT citext for email
-- citext is not installed here and `create extension` is a project-wide change
-- on a shared database. Case-insensitivity is enforced instead by a unique
-- index on lower(email) plus a CHECK that the stored value is already
-- lower-cased, so the constraint holds even if a future writer forgets to
-- normalise.
--
-- Tenant isolation mirrors cms_blocks/cms_assets/cms_posts: tenant_id on every
-- row + RLS.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- cms_editors — one row per human who may sign in to /admin.
--
-- Seeded with exactly ONE bootstrap owner. Who else at Xago may publish to a
-- licensed CASP's website is a client decision (human gate H-B3), so no client
-- staff accounts are invented here.
-- ---------------------------------------------------------------------------
create table if not exists public.cms_editors (
    id            uuid primary key default gen_random_uuid(),
    tenant_id     uuid not null,

    -- Always stored lower-cased; see the CHECK below and the unique index.
    email         text not null
        constraint cms_editors_email_lowercase check (email = lower(email))
        constraint cms_editors_email_shape     check (position('@' in email) > 1),

    -- scrypt, encoded as `scrypt$N$r$p$<salt b64>$<derived b64>`. NEVER a
    -- reversible encoding, and never verified in middleware: Web Crypto (edge)
    -- has no scrypt, so verification runs only in the Node server-action path.
    pw_hash       text not null,

    -- 'owner' may manage other editors; 'editor' may only edit content.
    role          text not null default 'editor'
        constraint cms_editors_role_check check (role in ('owner', 'editor')),

    invited_at    timestamptz not null default now(),

    -- The revocation switch. Checked by MIDDLEWARE on every /admin request, not
    -- only at login: a revoked editor whose signed cookie stays usable until it
    -- expires is a broken revocation, not a nuance (contract §3, B3).
    revoked_at    timestamptz,

    last_seen_at  timestamptz,

    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

-- Case-insensitive uniqueness per tenant. Two tenants may each have a
-- craig@example.com; one tenant may not have two.
create unique index if not exists cms_editors_unique_email
    on public.cms_editors (tenant_id, lower(email));

-- Roster listing: active first, newest invite first.
create index if not exists cms_editors_tenant_idx
    on public.cms_editors (tenant_id, revoked_at, invited_at desc);

-- ---------------------------------------------------------------------------
-- Attribution columns.
--
-- -> cms_editors.id, deliberately NOT a foreign key, matching how the rest of
-- the CMS references its own rows (cms_posts.cover_asset_id, .author_id): an
-- editor row may be hard-deleted for a data-protection request without
-- destroying the history of what they published. Nullable because every row
-- that predates this migration was written by the shared-password gate and has
-- no author to name — backfilling one would be inventing attribution.
-- ---------------------------------------------------------------------------
alter table public.cms_blocks add column if not exists updated_by uuid;
alter table public.cms_posts  add column if not exists updated_by uuid;

-- ---------------------------------------------------------------------------
-- cms_audit — append-only record of who changed what.
--
-- `before`/`after` hold the payload rather than a diff: reconstructing "what
-- did this page look like on Tuesday" from diffs requires every intermediate
-- row to be intact, and the publish path for blocks is delete-all-then-insert,
-- so a diff would frequently be "everything".
-- ---------------------------------------------------------------------------
create table if not exists public.cms_audit (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid not null,

    -- -> cms_editors.id. Nullable so a system/seed write can be recorded
    -- honestly as unattributed rather than pinned on a person who did not do it.
    editor_id  uuid,

    entity     text not null
        constraint cms_audit_entity_check check (entity in ('page', 'post', 'asset', 'editor')),

    -- The addressed thing: a page_slug for 'page', a uuid for the others.
    entity_id  text not null,

    action     text not null,

    before     jsonb,
    after      jsonb,

    at         timestamptz not null default now()
);

create index if not exists cms_audit_tenant_at_idx
    on public.cms_audit (tenant_id, at desc);

create index if not exists cms_audit_entity_idx
    on public.cms_audit (tenant_id, entity, entity_id, at desc);

-- ---------------------------------------------------------------------------
-- updated_at trigger — same shape as the other three tables.
-- ---------------------------------------------------------------------------
create or replace function public.cms_editors_touch_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

drop trigger if exists cms_editors_set_updated_at on public.cms_editors;
create trigger cms_editors_set_updated_at
    before update on public.cms_editors
    for each row execute function public.cms_editors_touch_updated_at();

-- ---------------------------------------------------------------------------
-- RLS — mirrors cms_assets/cms_posts exactly.
--
-- cms_audit gets no UPDATE or DELETE path beyond the service role by design:
-- an audit log an editor can edit is not an audit log.
-- ---------------------------------------------------------------------------
alter table public.cms_editors enable row level security;
alter table public.cms_audit   enable row level security;

drop policy if exists cms_editors_tenant_isolation on public.cms_editors;
create policy cms_editors_tenant_isolation
    on public.cms_editors
    as permissive
    for all
    using  (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
    with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

drop policy if exists cms_audit_tenant_isolation on public.cms_audit;
create policy cms_audit_tenant_isolation
    on public.cms_audit
    as permissive
    for all
    using  (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
    with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

-- ---------------------------------------------------------------------------
-- Comments
-- ---------------------------------------------------------------------------
comment on table  public.cms_editors is 'Xago CMS sign-in identities, tenant-scoped. Deliberately NOT auth.users: this Supabase project is shared with the control tower, so a project-wide JWT is the wrong boundary for client website staff.';
comment on column public.cms_editors.pw_hash    is 'scrypt hash, `scrypt$N$r$p$salt$derived`. Verified only in the Node server-action path — the edge runtime has no scrypt.';
comment on column public.cms_editors.revoked_at is 'Set to revoke access. Middleware re-reads this on EVERY /admin request, so revocation takes effect on the next request rather than at cookie expiry.';
comment on column public.cms_editors.role       is 'owner may manage the roster; editor may only edit content.';

comment on table  public.cms_audit is 'Append-only record of CMS mutations: who, what, before, after. Written by the same server action that performs the write, in the same request.';
comment on column public.cms_audit.entity_id is 'page_slug for entity=page; a uuid for post/asset/editor.';
comment on column public.cms_audit.editor_id is 'cms_editors.id, nullable: a seed or system write is recorded as unattributed rather than pinned on a person.';

comment on column public.cms_blocks.updated_by is 'cms_editors.id of the last human to write this block. NULL on rows written before 0004 (the shared-password era) — backfilling one would be inventing attribution.';
comment on column public.cms_posts.updated_by  is 'cms_editors.id of the last human to write this post. NULL on the 12 rows imported from WordPress.';
