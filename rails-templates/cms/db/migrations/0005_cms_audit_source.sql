-- ============================================================================
-- Migration: 0005_cms_audit_source
-- Let a non-human write DECLARE ITSELF in the audit log (task X-0100, B2 amendment).
--
-- APPLIED 2026-07-30 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0005_cms_audit_source`). This file is the repo
-- mirror — prod must stay a function of a commit.
--
-- WHY
-- B2 originally read "no cms_blocks row written since attribution landed has a
-- NULL updated_by". Measured on 2026-07-30, that assertion is unsatisfiable in
-- this repo: seed scripts (db/seed/*.seed.mjs) write cms_blocks directly, and
-- 43 rows across 11 pages were inserted or updated that way in a single
-- afternoon. A seed is not a person. Giving it an `updated_by` would mean
-- inventing an editor and pinning real content on someone who did not write it
-- — fabricated attribution on a licensed FSP's content store, which is the one
-- thing this project never does.
--
-- The fix is not to exempt seeds from the assertion. It is to make an
-- unattributed write EXPLAIN ITSELF: a seed writes a cms_audit row with
-- `editor_id` NULL and `source` naming the script. B2 then becomes
--
--     no unattributed write is UNEXPLAINED
--
-- which is checkable, and which still fails loudly if anything writes to
-- cms_blocks without declaring who or what it was. An absence becomes a record.
--
-- `source` is deliberately NOT a second author field. `editor_id` answers "which
-- person", `source` answers "which program", and a row may legitimately have
-- neither (pre-0004 history) or exactly one. A row with both would be a
-- contradiction, so it is refused.
-- ============================================================================

alter table public.cms_audit add column if not exists source text;

-- A write is either a person or a program, never both. Catching that at the
-- database means a caller cannot half-populate a row and leave B2 reading a
-- seed as if a human had done it.
alter table public.cms_audit drop constraint if exists cms_audit_actor_exclusive;
alter table public.cms_audit add constraint cms_audit_actor_exclusive
    check (editor_id is null or source is null);

-- The B2 lookup: "is there a declared non-human write for this page, near this
-- time?" — scans by entity and time, filtered to rows that named a source.
create index if not exists cms_audit_source_idx
    on public.cms_audit (tenant_id, entity, entity_id, at desc)
    where source is not null;

comment on column public.cms_audit.source is
$c$Which PROGRAM performed an unattributed write, e.g. 'db/seed/pages.seed.mjs'.
Mutually exclusive with editor_id: editor_id names a person, source names a
script, and no write is both. NULL on human edits.

Exists so that a write with no human author is a RECORDED FACT rather than an
absence — see the B2 amendment in docs/deliverables/blog/NODE7-tierB-end-state.md.
Never invent an editor_id for a script: fabricated attribution is worse than
declared anonymity.$c$;
