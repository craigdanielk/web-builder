// The cms_leads data access layer (task X-0152). NODE RUNTIME ONLY.
//
// Written against PostgREST with plain `fetch`, in the same idiom as
// editor-directory.ts. Its `query()` is deliberately NOT imported here: that
// module is loaded by the edge middleware on every /admin request, and pulling
// a node:crypto HMAC into its import graph would break the one property it is
// written to have. Two small readers, each honest about its runtime, beat one
// shared reader that cannot say which runtime it is in.
//
// Every read filters tenant_id and every write carries it (CLAUDE.md rule 1/2);
// this database is shared with the control-tower substrate.

import { createHmac } from "node:crypto";
import { LOGIN_WINDOW_MS } from "@/lib/editor-directory";

// Read per call, never captured at module load — see the same note in
// editor-directory.ts. A module-level const binds whatever the environment held
// at import time, which makes the module silently tenant-less under a test
// runner and produces a failure that looks like "the table is empty".
function tenantId(): string {
  return process.env.{{CMS_TENANT_ENV}} ?? "";
}

export type Lead = {
  id: string;
  name: string;
  email: string;
  company: string | null;
  message: string;
  source: string;
  created_at: string;
  handled_at: string | null;
  notified_at: string | null;
};

export const LEAD_COLS = "id,name,email,company,message,source,created_at,handled_at,notified_at";

/**
 * How far back submissions are counted, and therefore how long a flooder waits.
 *
 * Reuses the login window rather than declaring a second one: two windows that
 * mean "recently" and drift apart is a bug nobody notices until they are
 * debugging the wrong one.
 */
export const LEAD_WINDOW_MS = LOGIN_WINDOW_MS;

/**
 * Submissions allowed per hashed address per window.
 *
 * Five, and the number is a judgement about a marketing form rather than about
 * security. A real person sending a second enquiry, or correcting one they sent
 * badly, must never meet this. A crawler pushing junk should. Off-Vercel the
 * address is caller-supplied and therefore spoofable (see clientIp), so this is
 * a spam speed bump and not a control — stated plainly so nobody later mistakes
 * it for one.
 */
export const LEAD_MAX_PER_WINDOW = 5;

/** The endpoint's own limit on a message, INCLUSIVE. Mirrored by a CHECK in 0008. */
export const MESSAGE_MAX = 5000;
export const NAME_MAX = 200;
export const COMPANY_MAX = 200;

type Rest = { url: string; key: string };

function rest(): Rest | null {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key || !tenantId()) return null;
  return { url: url.replace(/\/+$/, ""), key };
}

async function query<T>(
  path: string,
  init: RequestInit = {},
): Promise<{ data: T | null; error: string | null }> {
  const cfg = rest();
  if (!cfg) return { data: null, error: "supabase env not configured" };

  try {
    const res = await fetch(`${cfg.url}/rest/v1/${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        apikey: cfg.key,
        authorization: `Bearer ${cfg.key}`,
        "content-type": "application/json",
        ...(init.headers ?? {}),
      },
    });
    if (!res.ok) return { data: null, error: `${res.status} ${await res.text()}` };
    // PostgREST answers a write with an EMPTY body unless asked for a
    // representation. Parsing that as JSON throws, and a successful insert
    // reported that way looks exactly like a database failure.
    const body = await res.text();
    if (!body) return { data: null, error: null };
    return { data: JSON.parse(body) as T, error: null };
  } catch (e) {
    return { data: null, error: e instanceof Error ? e.message : String(e) };
  }
}

/**
 * The throttle key for a client address: HMAC-SHA256 truncated to 32 hex chars.
 *
 * The address itself is never stored. Rate limiting needs a stable key per
 * client, not the client — and a raw IP beside a name, an address and free text
 * is a larger personal-data holding than the purpose justifies, on a licensed
 * FSP. See the header of db/migrations/0008_cms_leads.sql.
 *
 * Returns null when there is nothing to key on, INCLUDING when the secret is
 * absent. Null means "this request is not counted", never a shared bucket: one
 * constant fallback key would let a single flooder spend the budget of every
 * anonymous visitor at once, and this is the only lead path on the site.
 */
export function hashIp(ip: string | null, secret: string | undefined): string | null {
  if (!ip || !secret) return null;
  return createHmac("sha256", secret).update(ip).digest("hex").slice(0, 32);
}

export type LeadThrottle = {
  limited: boolean;
  /** Seconds until the oldest counted submission ages out. 0 when not limited. */
  retryAfterSec: number;
  recent: number;
  /** Set when the store could not be read. The caller must not treat this as "fine". */
  error: string | null;
};

/**
 * Has this address already had its five?
 *
 * Counts rows in cms_leads itself. No second table, and deliberately NOT
 * cms_login_attempts: that table's CHECK constraints admit only
 * ('identifier','ip') and ('failure','success'), and a contact submission has
 * no failure/success duality — every valid submission is a success, and success
 * is exactly what has to be limited. Reusing it would mean widening a
 * constraint on the login throttle to make the marketing form fit, which is how
 * an authentication control acquires an unrelated caller.
 *
 * A null key is not counted at all — see hashIp.
 */
export async function leadThrottleState(ipHash: string | null): Promise<LeadThrottle> {
  if (!ipHash) return { limited: false, retryAfterSec: 0, recent: 0, error: null };

  const since = new Date(Date.now() - LEAD_WINDOW_MS).toISOString();
  const { data, error } = await query<{ created_at: string }[]>(
    `cms_leads?select=created_at&tenant_id=eq.${tenantId()}` +
      `&ip_hash=eq.${ipHash}&created_at=gte.${encodeURIComponent(since)}` +
      `&order=created_at.asc&limit=${LEAD_MAX_PER_WINDOW + 1}`,
  );

  // A readable-but-empty result is `[]`. A null body means the read did not
  // happen, and is reported as unreadable rather than as "no submissions" —
  // the difference between failing closed and failing open.
  if (error || !data) {
    return { limited: false, retryAfterSec: 0, recent: 0, error: error ?? "lead store unreadable" };
  }

  if (data.length < LEAD_MAX_PER_WINDOW) {
    return { limited: false, retryAfterSec: 0, recent: data.length, error: null };
  }

  // Ascending, so the first row is the one whose expiry frees a slot.
  const releasesMs = new Date(data[0].created_at).getTime() + LEAD_WINDOW_MS - Date.now();
  return {
    limited: true,
    retryAfterSec: Math.max(1, Math.ceil(releasesMs / 1000)),
    recent: data.length,
    error: null,
  };
}

/** The inbox: newest first. Every enquiry, handled or not. */
export async function listLeads(): Promise<Lead[]> {
  const { data } = await query<Lead[]>(
    `cms_leads?select=${LEAD_COLS}&tenant_id=eq.${tenantId()}&order=created_at.desc`,
  );
  return data ?? [];
}

const uuidLike = /^[0-9a-f-]{36}$/i;

/**
 * Mark one enquiry dealt with, or put it back.
 *
 * Returns the row as it now stands so the caller can write a truthful audit
 * `after` rather than the value it hoped it wrote.
 */
export async function setLeadHandled(
  id: string,
  handled: boolean,
): Promise<{ lead: Lead | null; error: string | null }> {
  if (!uuidLike.test(id)) return { lead: null, error: "invalid lead id" };
  const { data, error } = await query<Lead[]>(
    `cms_leads?id=eq.${id}&tenant_id=eq.${tenantId()}&select=${LEAD_COLS}`,
    {
      method: "PATCH",
      headers: { prefer: "return=representation" },
      body: JSON.stringify({ handled_at: handled ? new Date().toISOString() : null }),
    },
  );
  return { lead: data?.[0] ?? null, error };
}

/**
 * Write one lead. Returns the error rather than throwing, and the caller
 * decides — but there is only one correct decision and the route makes it: a
 * failed insert is a 500. A route that swallows this and answers 200 is the
 * same lie the component used to tell, one layer down.
 */
export async function insertLead(lead: {
  name: string;
  email: string;
  company: string | null;
  message: string;
  source: string;
  ipHash: string | null;
}): Promise<{ error: string | null }> {
  const { error } = await query("cms_leads", {
    method: "POST",
    body: JSON.stringify({
      tenant_id: tenantId(),
      name: lead.name,
      email: lead.email,
      company: lead.company,
      message: lead.message,
      source: lead.source,
      ip_hash: lead.ipHash,
    }),
  });
  return { error };
}


/**
 * Record that a lead notification was delivered.
 *
 * `notified_at` shipped in 0008 with no writer, deliberately — the migration
 * header says why: the column exists before its writer so that a later
 * notification failure is VISIBLE (as a null in the inbox count) rather than
 * needing a second migration against live client data. This is that writer.
 *
 * Returns the error rather than throwing. The only caller is the best-effort
 * notifier, which must not be able to fail the request that committed the row:
 * a lead that was mailed but not stamped is a duplicate notification at worst,
 * a lead that was stored and then 500'd because the stamp failed is lost work.
 */
export async function setLeadNotified(id: string): Promise<{ error: string | null }> {
  if (!uuidLike.test(id)) return { error: "invalid lead id" };
  const { error } = await query(
    `cms_leads?id=eq.${id}&tenant_id=eq.${tenantId()}`,
    {
      method: "PATCH",
      body: JSON.stringify({ notified_at: new Date().toISOString() }),
    },
  );
  return { error };
}
