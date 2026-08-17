-- ============================================================================
-- Migration: 0009_cms_audit_lead
-- Let cms_audit name a lead (task X-0154).
--
-- APPLIED 2026-07-31 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0009_cms_audit_lead`). This file is the repo mirror.
--
-- WHY THIS EXISTS, AND WHY IT WAS NOT PLANNED
-- PLAN-contact-leads.md requires two cms_audit writes that name a lead: marking
-- an enquiry handled in /admin/leads (§3 step 5), and recording a failed
-- notification as entity 'lead', action 'notify_failed' (§6). Neither is
-- possible: cms_audit_entity_check admits only
-- ('page','post','asset','editor','author'), so both writes are refused by the
-- database. The plan does not mention it. Flagged rather than worked around —
-- the alternatives were filing a lead under some other entity, which is a false
-- record, or dropping the audit row, which is the silent-failure habit this
-- whole task exists to break.
--
-- This is the SECOND time this constraint has been the thing in the way, and
-- the precedent is followed exactly. Migration 0006 widened it for 'author'
-- with the same reasoning: an auditable write existed that `entity` had no
-- value to name, so the row could not be written truthfully.
--
-- Purely additive. Every existing value stays legal, so nothing that writes
-- cms_audit today can be affected by this.
--
-- WHY A LEAD IS AN AUDITABLE ENTITY AT ALL
-- 'handled' is a claim by a named person that a member of the public has been
-- dealt with. On a licensed FSP, "who said they answered this enquiry, and
-- when" is exactly the kind of question the audit table exists to answer. And
-- from X-0156 onward, a lead nobody was emailed about leaves a record of that
-- fact rather than an absence — which is the mechanism that keeps a best-effort
-- notification from decaying quietly into no notification at all.
-- ============================================================================

alter table public.cms_audit drop constraint if exists cms_audit_entity_check;
alter table public.cms_audit add constraint cms_audit_entity_check
    check (entity in ('page', 'post', 'asset', 'editor', 'author', 'lead'));

comment on column public.cms_audit.entity_id is
$c$page_slug for entity=page; a uuid for post/asset/editor/author/lead.$c$;
