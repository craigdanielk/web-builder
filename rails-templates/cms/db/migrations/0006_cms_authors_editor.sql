-- ============================================================================
-- Migration: 0006_cms_authors_editor
-- Join the byline to the sign-in identity (task X-0133).
--
-- APPLIED 2026-07-30 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0006_cms_authors_editor`). This file is the repo
-- mirror — prod must stay a function of a commit
-- (see .claude/rules/vercel-deploy-sop.md).
--
-- WHY
-- The B10 oracle FLAGGED rather than failed: `cms_authors` held ["Xago","Xago"]
-- and `cms_editors` held 4 active identities with NO column joining them, so
-- "the byline resolves to a cms_editors identity" was unsatisfiable by any
-- query. Every article rendered the placeholder "Xago".
--
-- WHY NOT resolve the byline from cms_posts.updated_by
-- "who last saved this" and "who wrote it" are different facts. They agree
-- exactly until the first time someone fixes a typo on a colleague's article,
-- at which point the byline of a licensed FSP's published announcement would
-- silently change to name the wrong person. updated_by stays what it is: the
-- audit answer to "who touched this last", never the reader-facing answer to
-- "who wrote this".
--
-- WHY cms_authors SURVIVES as its own table
-- It is the DISPLAY layer — name, role, avatar — and an author may legitimately
-- have no login: a guest contributor, an agency writer, or the 12 migrated
-- WordPress bylines whose real authors are unknowable
-- (/wp-json/wp/v2/users is 401). Collapsing the two tables would mean either
-- minting a dead login for every guest byline or deleting history. `editor_id`
-- is therefore NULLABLE and stays NULL on every migrated row.
--
-- WHY A FOREIGN KEY HERE, when cms_posts.author_id / .cover_asset_id / .updated_by
-- are deliberately NOT foreign keys
-- Those three record HISTORY — what a post was authored against, who last wrote
-- it — and history must survive a hard delete of the thing it names, so a
-- dangling id there is a preserved fact rather than corruption. `editor_id` is
-- not history; it is a LIVE link asserting "this byline is that login, right
-- now". A link to a deleted login is not a fact worth keeping, it is a wrong
-- answer. So it is a real FK with `on delete set null (editor_id)`: revoking or
-- hard-deleting an editor for a data-protection request drops the link and
-- leaves the byline row — and therefore every article that carries it —
-- untouched.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Tenant-safe target for the FK.
--
-- The reference is COMPOSITE, on (tenant_id, id) rather than (id) alone, so the
-- database itself refuses to link an author in one tenant to an editor in
-- another. CLAUDE.md rules 2 and 3 are enforced in every query by hand; this is
-- the one place the constraint can be made structural, and on a database shared
-- with the control-tower substrate that is worth the extra unique index.
-- ---------------------------------------------------------------------------
alter table public.cms_editors
    drop constraint if exists cms_editors_tenant_id_key;
alter table public.cms_editors
    add constraint cms_editors_tenant_id_key unique (tenant_id, id);

alter table public.cms_authors add column if not exists editor_id uuid;

-- `on delete set null (editor_id)` names the column explicitly (PG 15+, this
-- project is 17.6). Without the column list Postgres would try to NULL
-- tenant_id too, which is NOT NULL, and the editor delete would fail with a
-- constraint violation instead of unlinking the byline.
alter table public.cms_authors
    drop constraint if exists cms_authors_editor_fk;
alter table public.cms_authors
    add constraint cms_authors_editor_fk
    foreign key (tenant_id, editor_id)
    references public.cms_editors (tenant_id, id)
    on delete set null (editor_id);

-- One byline row per login. Two author rows pointing at the same editor would
-- make "the signed-in editor's byline" ambiguous, and the create path
-- (`defaultAuthorId`) picks from exactly this lookup.
--
-- A plain UNIQUE CONSTRAINT, not the partial index `… where editor_id is not
-- null` that this first shipped as. Both express the same rule — Postgres treats
-- NULLs as distinct by default, so the unlimited number of editor-less bylines
-- (guest contributors, the 12 migrated rows) is unaffected either way — but only
-- a constraint can be named by `ON CONFLICT (tenant_id, editor_id)`. PostgREST
-- emits no WHERE predicate, so upserting against the partial index failed with
-- "no unique or exclusion constraint matching the ON CONFLICT specification",
-- which is what db/seed/authors.seed.mjs does on every run.
alter table public.cms_authors drop constraint if exists cms_authors_editor_unique;
drop index if exists public.cms_authors_editor_unique;
alter table public.cms_authors
    add constraint cms_authors_editor_unique unique (tenant_id, editor_id);

-- ---------------------------------------------------------------------------
-- cms_audit may now address an author.
--
-- A byline is reader-visible content on a licensed FSP's site: creating one, or
-- renaming one, changes what a published article says about who wrote it. That
-- is precisely the class of write cms_audit exists to record, and until now
-- `entity` had no value that could name it — db/seed/authors.seed.mjs wrote
-- bylines with no declared source at all. Widened here, and declared by the
-- seed via seedAudit() (src/lib/seed-audit.mjs).
-- ---------------------------------------------------------------------------
alter table public.cms_audit drop constraint if exists cms_audit_entity_check;
alter table public.cms_audit add constraint cms_audit_entity_check
    check (entity in ('page', 'post', 'asset', 'editor', 'author'));

-- ---------------------------------------------------------------------------
-- Comments
-- ---------------------------------------------------------------------------
comment on column public.cms_authors.editor_id is
$c$cms_editors.id — the sign-in identity this byline belongs to. NULL for a
byline that is not a login: a guest contributor, or the 12 posts migrated from
WordPress, whose real authors are not retrievable (/wp-json/wp/v2/users is 401)
and are therefore left on the honest company byline "Xago" rather than assigned
to a staff member who did not write them.

NOT the same fact as cms_posts.updated_by. updated_by is who last SAVED the row;
this is who WROTE it. They diverge the first time someone fixes a typo on a
colleague's article, and the reader-facing byline must follow the second.$c$;

comment on constraint cms_authors_editor_fk on public.cms_authors is
'Composite on (tenant_id, id) so a byline cannot link to another tenant''s editor. ON DELETE SET NULL (editor_id) unlinks the byline and keeps it, so removing a login never rewrites a published article.';
