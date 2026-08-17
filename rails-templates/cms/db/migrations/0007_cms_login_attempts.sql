-- ============================================================================
-- Migration: 0007_cms_login_attempts
-- Brute-force throttling state for /admin/login (task X-0135).
--
-- APPLIED 2026-07-30 to project wwimngjmnuuitowujnif via the Supabase MCP
-- (`apply_migration`, name `0007_cms_login_attempts`). This file is the repo
-- mirror — prod must stay a function of a commit (.claude/rules/vercel-deploy-sop.md).
--
-- WHY A TABLE AND NOT A COUNTER IN MEMORY
-- Vercel functions do not share process state. A module-scoped Map is per
-- instance, so an attacker spreading 500 guesses across instances is counted as
-- 500 separate "first attempts" and the control does nothing at all — while
-- looking, in code review and in a single-process local test, exactly like a
-- working rate limiter. State that must be shared across invocations lives in
-- the database or it does not exist.
--
-- WHY A TABLE AND NOT cms_editors.locked_until
-- A lock hung off the editor row can only count attempts against addresses that
-- ALREADY have an account. Guesses at addresses that do not exist would then be
-- free and uncounted, and — worse — "this address can be locked" would become a
-- test for whether an account exists, which is the enumeration oracle the login
-- form is specifically built not to be. Keying on the SUBMITTED string means an
-- unknown address and a real one behave identically in every observable way.
--
-- WHY ROWS AND NOT A COUNTER COLUMN
-- A counter needs read-modify-write, and concurrent guesses — which is what an
-- attack IS — race on it and undercount. Appending one row per attempt counts
-- correctly under any concurrency, and gives the forensic record for free.
--
-- WHAT THIS TABLE IS NOT
-- It is not the audit log. cms_audit records the decisions (login, login_failed,
-- login_locked) with the same append-only, actor-declaring discipline as every
-- other CMS mutation. This table is throttle STATE: high-volume, narrow, and
-- safe to garbage-collect once outside the counting window (see the note at the
-- foot of this file). Deleting from cms_audit would destroy history; deleting
-- aged rows from here destroys nothing.
-- ============================================================================

create table if not exists public.cms_login_attempts (
    id         uuid primary key default gen_random_uuid(),
    tenant_id  uuid not null,

    -- Which bucket this attempt is counted in. BOTH are recorded for every
    -- attempt, as two rows: either dimension alone is trivially evaded.
    -- 'identifier' alone lets one attacker walk the whole roster from one host;
    -- 'ip' alone is defeated by any proxy pool, and over-punishes a shared
    -- office NAT where several editors sign in from one address.
    scope      text not null
        constraint cms_login_attempts_scope_check check (scope in ('identifier', 'ip')),

    -- The counted value: the lower-cased email AS SUBMITTED (never the resolved
    -- account id — see the header), or the client address. Lower-cased for the
    -- same reason cms_editors.email is: so the constraint holds even if a future
    -- writer forgets to normalise, and `Kevin@…` and `kevin@…` cannot be two
    -- separate budgets.
    key        text not null
        constraint cms_login_attempts_key_lowercase check (key = lower(key))
        constraint cms_login_attempts_key_length    check (length(key) between 1 and 254),

    outcome    text not null
        constraint cms_login_attempts_outcome_check check (outcome in ('failure', 'success')),

    -- -> cms_editors.id, and ONLY ever set on a success. A failed attempt must
    -- not name a person: the whole premise of a brute-force attempt is that the
    -- party submitting it is NOT the account holder, so recording their id would
    -- pin an attack on the victim. Enforced below rather than left to the caller.
    editor_id  uuid
        constraint cms_login_attempts_failure_is_anonymous
        check (outcome = 'success' or editor_id is null),

    at         timestamptz not null default now()
);

-- The hot path: "how many failures for this key since the window opened?".
-- Every login pays for two of these lookups, so the index covers the exact
-- predicate — equality on tenant/scope/key, then a descending time range.
create index if not exists cms_login_attempts_lookup_idx
    on public.cms_login_attempts (tenant_id, scope, key, at desc);

-- Garbage collection scans by age alone, across tenants.
create index if not exists cms_login_attempts_age_idx
    on public.cms_login_attempts (at);

-- ---------------------------------------------------------------------------
-- RLS — mirrors cms_editors/cms_audit exactly.
--
-- Reached only by the service role from the login server action. An editor has
-- no reason to read this table and an attacker even less: the row set is a map
-- of which addresses are being guessed at.
-- ---------------------------------------------------------------------------
alter table public.cms_login_attempts enable row level security;

drop policy if exists cms_login_attempts_tenant_isolation on public.cms_login_attempts;
create policy cms_login_attempts_tenant_isolation
    on public.cms_login_attempts
    as permissive
    for all
    using      (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid)
    with check (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

-- ---------------------------------------------------------------------------
-- Comments
-- ---------------------------------------------------------------------------
comment on table public.cms_login_attempts is
$c$Throttle state for /admin/login (X-0135). One row per attempt per scope, so
every attempt writes two: one 'identifier' (the submitted email) and one 'ip'.

Counted, never trusted as history — cms_audit is the record. Rows older than the
counting window (see LOGIN_WINDOW_MS in src/lib/editor-directory.ts) affect
nothing and may be deleted:

    delete from public.cms_login_attempts where at < now() - interval '7 days';

Deliberately keyed on the SUBMITTED address rather than a cms_editors.id, so an
address with no account is throttled identically to one with an account and the
form cannot be used to discover which is which.$c$;

comment on column public.cms_login_attempts.scope is
$c$'identifier' (submitted email) or 'ip' (client address). Both are counted for
every attempt: an identifier-only limit lets one host walk the whole roster, and
an ip-only limit is defeated by a proxy pool and punishes shared office NAT.$c$;

comment on column public.cms_login_attempts.key is
$c$The counted value, lower-cased: the submitted email, or the client address.

A submission whose address is not plausible (loginIdentifier() in
src/lib/editor-directory.ts) writes NO 'identifier' row — only an 'ip' one. It is
not bucketed under a placeholder: a shared bucket is a lockout one caller can
inflict on every other, and nothing is lost, because an address that shape-check
rejects can never match an account.

For 'ip' the value is best-effort — see clientIp(). Off-Vercel the address is
caller-supplied and therefore spoofable, which is precisely why the identifier
scope exists and does not depend on it.$c$;

comment on column public.cms_login_attempts.editor_id is
$c$Set only on outcome='success'. A failure is recorded anonymously by
construction (cms_login_attempts_failure_is_anonymous): naming the account holder
on an attempt they did not make would pin an attack on its victim.$c$;
