-- ============================================================================
-- Migration: 0008_cms_leads
-- The store for public contact-form submissions (task X-0151).
--
-- APPLIED 2026-07-31 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0008_cms_leads`). This file is the repo mirror —
-- prod must stay a function of a commit (.claude/rules/vercel-deploy-sop.md).
--
-- WHY THIS TABLE EXISTS AT ALL
-- Until today the contact form on this site had no `action`, no `fetch` and no
-- `name` attribute on any input. It set a flag in the browser and told the
-- visitor "Thanks — we'll be in touch." The message was discarded in the tab.
-- The site of an FSCA-authorised FSP promised a human reply that no human could
-- ever make, because no human ever saw the message. This table is where that
-- message now lands, and it is the SINGLE SOURCE OF TRUTH for a lead: the
-- notification in X-0156 is a courtesy on top of a committed row, never a
-- precondition for one (see the argument in
-- docs/deliverables/golive-plans/PLAN-contact-leads.md §6).
--
-- WHY RLS IS ENABLED WITH ZERO POLICIES — A DELIBERATE DIVERGENCE
-- cms_editors, cms_audit and cms_login_attempts each carry a permissive
-- `for all` policy keyed on `auth.jwt() ->> 'tenant_id'`. Copying that here
-- would grant read of every lead to ANY bearer of a JWT carrying this tenant id.
-- Those three tables hold tenant CONFIGURATION; this one holds unvetted personal
-- data typed in by members of the public — a name, an address they expect to be
-- used to reply to them, and free text that may contain anything. There is no
-- caller that should reach it except the service role, and the service role
-- bypasses RLS entirely and therefore needs no policy at all.
--
-- So: RLS on, policy count zero. Enabled-with-no-policies denies every
-- non-service caller by default, which is the intent stated exactly. The policy
-- COUNT is asserted (contract C1) rather than only the anon read, because a
-- permissive policy added later would leave an anon read passing today and
-- failing silently the first time a tenant-scoped JWT exists.
--
-- WHY ip_hash AND NOT ip
-- The endpoint is throttled per client address (5 per 15 minutes, contract C6).
-- That needs a stable key per address; it does not need the address back. A raw
-- client IP stored beside a name, an email and free text is a materially larger
-- personal-data holding for a licensed FSP, kept for a purpose that has no use
-- for reversibility. So the stored value is
-- HMAC-SHA256(ip, ADMIN_SESSION_SECRET) truncated to 32 hex characters:
-- throttleable, not reversible.
--
-- The trade, stated rather than discovered later: reusing ADMIN_SESSION_SECRET
-- couples two purposes, and rotating it resets every throttle count to zero.
-- That is the whole consequence, it is bounded, and it avoids introducing a new
-- environment variable on cutover day.
--
-- WHY notified_at EXISTS BEFORE ANYTHING WRITES IT
-- X-0156 (the Resend notification) is blocked on a human. It is nonetheless
-- decided that a lead is captured even when notification fails — and the
-- objection to that ("an unnotified lead nobody checks is functionally lost") is
-- answered by making the failure VISIBLE rather than fatal. That visibility
-- costs exactly this one nullable column, and /admin/leads shows the
-- un-notified count from day one. Adding it later would mean a second migration
-- against a table already holding live client data.
--
-- WHAT IS NOT DECIDED HERE
-- The RETENTION PERIOD. How long an FSCA-authorised FSP keeps unsolicited
-- personal data is a compliance decision, and nobody has made it (human gate
-- H-C1). The table comment says so explicitly rather than implying a policy
-- exists by staying silent.
-- ============================================================================

create table if not exists public.cms_leads (
    id          uuid primary key default gen_random_uuid(),
    tenant_id   uuid not null,

    name        text not null
        constraint cms_leads_name_length check (length(name) between 1 and 200),

    -- Stored lower-cased for the same reason cms_editors.email is: so two
    -- capitalisations of one address cannot read as two different people.
    email       text not null
        constraint cms_leads_email_lowercase check (email = lower(email))
        constraint cms_leads_email_length    check (length(email) between 3 and 254),

    -- Optional on the form, and optional here. A prospect who will not name
    -- their employer is still a prospect.
    company     text
        constraint cms_leads_company_length check (company is null or length(company) <= 200),

    -- 5000 is the limit the endpoint enforces, mirrored here so a future caller
    -- that forgets cannot write an unbounded blob. INCLUSIVE at 5000: the
    -- boundary is asserted in both directions (contract C4) because an
    -- off-by-one here rejects a legitimate long enquiry, which is the same
    -- category of loss this whole table exists to stop.
    message     text not null
        constraint cms_leads_message_length check (length(message) between 1 and 5000),

    -- Which surface produced this row. 'contact' is the public form; the
    -- verification oracle writes 'verify:<run id>' and deletes its own rows
    -- before it exits, so a stray marker row is legible as test residue rather
    -- than being mistaken for a real enquiry in front of the client.
    source      text not null default 'contact'
        constraint cms_leads_source_length check (length(source) between 1 and 64),

    -- HMAC of the client address, never the address. See the header.
    -- Null when nothing identified the caller — that request is simply not
    -- throttleable, which is preferable to inventing one shared bucket that a
    -- single flooder could use to lock out every anonymous visitor.
    ip_hash     text
        constraint cms_leads_ip_hash_shape check (ip_hash is null or ip_hash ~ '^[0-9a-f]{32}$'),

    created_at  timestamptz not null default now(),

    -- Set by /admin/leads when a person marks the enquiry dealt with (X-0154).
    handled_at  timestamptz,

    -- Set by X-0156 on a successful notification; left NULL on failure. NULL is
    -- therefore "nobody has been emailed about this yet", and /admin/leads
    -- counts them. See the header.
    notified_at timestamptz
);

-- The inbox read: newest first, for one tenant.
create index if not exists cms_leads_inbox_idx
    on public.cms_leads (tenant_id, created_at desc);

-- The throttle read: "how many rows for this hashed address since the window
-- opened?". Covers the exact predicate — equality on tenant/hash, then a
-- descending time range. Partial, because a row with no hash is never counted.
create index if not exists cms_leads_throttle_idx
    on public.cms_leads (tenant_id, ip_hash, created_at desc)
    where ip_hash is not null;

-- ---------------------------------------------------------------------------
-- RLS — ENABLED, WITH NO POLICIES. Read the header before adding one.
-- ---------------------------------------------------------------------------
alter table public.cms_leads enable row level security;

-- ---------------------------------------------------------------------------
-- Comments
-- ---------------------------------------------------------------------------
comment on table public.cms_leads is
$c$Public contact-form submissions (X-0151). One row per enquiry.

THE SOURCE OF TRUTH FOR A LEAD. The email notification (X-0156) is best-effort
on top of a committed row: a failed send leaves notified_at NULL and is surfaced
in /admin/leads, it never vetoes the insert. An outbound mail provider's uptime
must not be a precondition for our own record-keeping.

RLS is enabled and there are DELIBERATELY NO POLICIES — unlike cms_editors /
cms_audit / cms_login_attempts, which carry a permissive tenant policy. This
table holds unvetted public personal data, not tenant configuration, and the
only legitimate reader is the service role, which bypasses RLS. A tenant-scoped
policy here would grant every lead to any bearer of a matching JWT.

RETENTION IS UNDECIDED. No policy exists for how long an FSCA-authorised FSP
keeps unsolicited personal data; that is a compliance decision and nobody has
made it (gate H-C1 in docs/deliverables/golive-plans/PLAN-contact-leads.md §5).
This comment records the absence rather than letting silence imply a policy.
Once decided, the deletion is a dated statement of the form:

    delete from public.cms_leads where created_at < now() - interval '<agreed>';$c$;

comment on column public.cms_leads.ip_hash is
$c$HMAC-SHA256(client ip, ADMIN_SESSION_SECRET), truncated to 32 hex chars.

The address itself is never stored. Rate limiting needs a stable key per client,
not the client — and a raw IP alongside a name, an address and free text is a
larger personal-data holding than the purpose requires.

Null when clientIp() identified nothing. Such a request is not counted at all,
rather than being pooled under a shared key: one shared bucket is a lockout one
caller can inflict on every other visitor, on the only lead path this site has.

Reused secret, stated trade: rotating ADMIN_SESSION_SECRET resets throttle
counts to zero. Bounded, and it avoids adding an env var on cutover day.$c$;

comment on column public.cms_leads.notified_at is
$c$Set when X-0156 successfully notified Xago about this lead; NULL when it did
not, including before X-0156 exists at all.

NULL is a REAL STATE, not an absence: /admin/leads shows "N leads not yet
emailed" whenever the count is non-zero, and a send failure additionally writes
a cms_audit row (entity 'lead', action 'notify_failed'). A silent best-effort
failure is what let the original discard-the-message defect live; this is the
mechanism that makes the same failure loud instead.$c$;

comment on column public.cms_leads.source is
$c$Which surface produced the row. 'contact' is the public form.

Rows written by scripts/verify/contact-form.mjs carry 'verify:<run id>' and are
deleted by that script before it exits, on every path including its failure
paths. The prefix exists so residue from an interrupted run is identifiable as
residue rather than being read as a real enquiry by whoever opens the inbox.$c$;

comment on column public.cms_leads.handled_at is
$c$Set when someone marks the enquiry dealt with in /admin/leads. Deliberately a
timestamp and not a status enum: 'has anyone dealt with this' is the only
question the client asked for, and a workflow nobody requested is a workflow
invented at a cutover.$c$;
