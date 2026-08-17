// The cms_editors / cms_audit data access layer (task X-0100).
//
// Written against PostgREST with plain `fetch` rather than @supabase/supabase-js
// for one reason: `editorIsActive()` is called from MIDDLEWARE, which runs on
// the edge runtime, and this way the exact same code path serves the edge check
// and the Node server actions. One implementation, one set of tenant filters.
//
// Every read filters tenant_id and every write carries it (CLAUDE.md rule 1/2);
// this database is shared with the control-tower substrate.

// Read per call, not captured at module load. A module-level const binds
// whatever the environment happened to hold at import time, which makes the
// module silently tenant-less if anything loads it before the environment is
// populated — exactly what happens under a test runner, and a failure mode that
// looks like "the table is empty" rather than like a configuration error.
function tenantId(): string {
  return process.env.{{CMS_TENANT_ENV}} ?? "";
}

export type Editor = {
  id: string;
  email: string;
  role: "owner" | "editor";
  invited_at: string;
  revoked_at: string | null;
  last_seen_at: string | null;
};

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
    // representation — 204 for PATCH/DELETE, but 201 for INSERT. Parsing that as
    // JSON throws, and an audit write reported that way looks like a database
    // failure when it in fact succeeded.
    const body = await res.text();
    if (!body) return { data: null, error: null };
    return { data: JSON.parse(body) as T, error: null };
  } catch (e) {
    return { data: null, error: e instanceof Error ? e.message : String(e) };
  }
}

const EDITOR_COLS = "id,email,role,invited_at,revoked_at,last_seen_at";
const uuidLike = /^[0-9a-f-]{36}$/i;

/**
 * Is this a plausible email address?
 *
 * Used to REJECT input, never to sanitise it. Sanitising a hostile value leaves
 * you reasoning about what survived the scrub; rejecting it means the value the
 * query sees is one this predicate already vouched for. Deliberately stricter
 * than RFC 5322 — no quoted local parts, no spaces, no `%` or `_` — because the
 * addresses that must work here are ordinary staff mailboxes, and every
 * character this does not allow is a character no filter downstream has to
 * survive.
 */
export function isPlausibleEmail(value: string): boolean {
  return /^[^\s@%_,()"'\\]+@[^\s@%_,()"'\\]+\.[a-z]{2,}$/i.test(value) && value.length <= 254;
}

/**
 * Is this editor still allowed in? Called by middleware on EVERY /admin request.
 *
 * FAILS CLOSED. A missing row, a revoked row, a misconfigured environment or an
 * unreachable database all return false, which signs the user out. The
 * alternative — treating an error as "probably fine" — means a revoked editor
 * keeps access for as long as the database is unhappy, and B3 exists precisely
 * to forbid that.
 */
export async function editorIsActive(editorId: string): Promise<boolean> {
  if (!uuidLike.test(editorId)) return false;
  const { data } = await query<{ revoked_at: string | null }[]>(
    `cms_editors?select=revoked_at&id=eq.${editorId}&tenant_id=eq.${tenantId()}&limit=1`,
  );
  return Boolean(data && data.length === 1 && data[0].revoked_at === null);
}

export async function getEditor(editorId: string): Promise<Editor | null> {
  if (!uuidLike.test(editorId)) return null;
  const { data } = await query<Editor[]>(
    `cms_editors?select=${EDITOR_COLS}&id=eq.${editorId}&tenant_id=eq.${tenantId()}&limit=1`,
  );
  return data?.[0] ?? null;
}

/** Roster for /admin/editors: active first, then most recently invited. */
export async function listEditors(): Promise<Editor[]> {
  const { data } = await query<Editor[]>(
    `cms_editors?select=${EDITOR_COLS}&tenant_id=eq.${tenantId()}&order=revoked_at.asc.nullsfirst,invited_at.desc`,
  );
  return data ?? [];
}

/**
 * Login lookup. EXACT match, never a pattern.
 *
 * This used `email=ilike.${encodeURIComponent(email)}`, which was wrong in a way
 * worth recording. `encodeURIComponent` escapes `%` to `%25`, but PostgREST
 * URL-decodes the value back to `%` before it reaches the LIKE operator, so a
 * submitted email of `%` became a wildcard matching EVERY editor row — verified
 * against the live table, which returned all four. `limit=1` then handed the
 * caller an arbitrary account, with no ORDER BY and therefore no defined choice
 * of which one. `_` survives encoding untouched and matches any single
 * character.
 *
 * That was not a password bypass — the supplied password is still checked
 * against whatever row came back — but it made the identity being authenticated
 * depend on database row order, which is not a property an authentication path
 * may have.
 *
 * `eq` compares the value literally, so metacharacters carry no meaning at all.
 * The `cms_editors_email_lowercase` CHECK already guarantees stored addresses
 * are lower-case, so `ilike` was buying nothing in the first place. The shape
 * guard is defence in depth: it rejects rather than escapes.
 */
export async function findEditorForLogin(
  email: string,
): Promise<{ id: string; pw_hash: string; revoked_at: string | null } | null> {
  const normalised = email.trim().toLowerCase();
  if (!isPlausibleEmail(normalised)) return null;

  const { data } = await query<{ id: string; pw_hash: string; revoked_at: string | null }[]>(
    `cms_editors?select=id,pw_hash,revoked_at&tenant_id=eq.${tenantId()}&email=eq.${encodeURIComponent(normalised)}&limit=1`,
  );
  return data?.[0] ?? null;
}

export async function createEditor(
  email: string,
  pwHash: string,
  role: "owner" | "editor",
): Promise<{ editor: Editor | null; error: string | null }> {
  const { data, error } = await query<Editor[]>("cms_editors", {
    method: "POST",
    headers: { prefer: "return=representation" },
    body: JSON.stringify({
      tenant_id: tenantId(),
      email: email.trim().toLowerCase(),
      pw_hash: pwHash,
      role,
    }),
  });
  return { editor: data?.[0] ?? null, error };
}

export async function setRevoked(editorId: string, revoked: boolean): Promise<string | null> {
  if (!uuidLike.test(editorId)) return "invalid editor id";
  const { error } = await query(
    `cms_editors?id=eq.${editorId}&tenant_id=eq.${tenantId()}`,
    {
      method: "PATCH",
      body: JSON.stringify({ revoked_at: revoked ? new Date().toISOString() : null }),
    },
  );
  return error;
}

/**
 * The stored hash for an ALREADY-AUTHENTICATED editor, by id (task X-0181).
 *
 * Separate from `findEditorForLogin`, which resolves an identity from a
 * submitted address. This one starts from a verified session and asks a
 * different question: "prove the person holding this session also knows the
 * current password". Keeping them apart means the login lookup never grows an
 * id-shaped entry point, and this one never grows an email-shaped one.
 */
export async function getPasswordHash(editorId: string): Promise<string | null> {
  if (!uuidLike.test(editorId)) return null;
  const { data } = await query<{ pw_hash: string }[]>(
    `cms_editors?select=pw_hash&id=eq.${editorId}&tenant_id=eq.${tenantId()}&limit=1`,
  );
  return data?.[0]?.pw_hash ?? null;
}

export async function setRole(editorId: string, role: "owner" | "editor"): Promise<string | null> {
  if (!uuidLike.test(editorId)) return "invalid editor id";
  const { error } = await query(`cms_editors?id=eq.${editorId}&tenant_id=eq.${tenantId()}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
  return error;
}

/**
 * How many people can still manage the roster.
 *
 * Exists so a demotion can be refused BEFORE it strands the CMS. A CMS with zero
 * owners cannot invite, revoke, reset a password or restore an owner — and
 * nothing inside the CMS can repair that, because every repair is owner-gated.
 * It would take a direct database write, which is the situation X-0182 was
 * raised to end.
 *
 * Counts only ACTIVE owners: a revoked owner cannot sign in, so they are not a
 * way back in.
 *
 * Returns null when the count could not be read, and the caller must refuse on
 * null rather than treat it as zero or as plenty — an unreadable count is not
 * evidence that a demotion is safe.
 */
export async function countActiveOwners(): Promise<number | null> {
  const { data, error } = await query<{ id: string }[]>(
    `cms_editors?select=id&tenant_id=eq.${tenantId()}&role=eq.owner&revoked_at=is.null`,
  );
  if (error || !data) return null;
  return data.length;
}

export async function setPasswordHash(editorId: string, pwHash: string): Promise<string | null> {
  if (!uuidLike.test(editorId)) return "invalid editor id";
  const { error } = await query(`cms_editors?id=eq.${editorId}&tenant_id=eq.${tenantId()}`, {
    method: "PATCH",
    body: JSON.stringify({ pw_hash: pwHash }),
  });
  return error;
}

/** Best-effort: a failed heartbeat must never block a sign-in. */
export async function touchLastSeen(editorId: string): Promise<void> {
  if (!uuidLike.test(editorId)) return;
  await query(`cms_editors?id=eq.${editorId}&tenant_id=eq.${tenantId()}`, {
    method: "PATCH",
    body: JSON.stringify({ last_seen_at: new Date().toISOString() }),
  });
}

// ---------------------------------------------------------------------------
// Login throttling (task X-0135)
//
// scrypt at N=32768 costs an attacker ~100ms a guess, which bounds one core to
// roughly ten a second. That is a speed bump, not a control: ten a second is
// 864,000 a day, against four accounts on a licensed CASP's CMS whose passwords
// were distributed by message.
//
// THE COUNTED THING IS A FAILURE, NOT A REQUEST — the difference between a
// control and a punishment. An editor who mistypes twice, reloads and tries
// again has made five requests and two mistakes; an attacker has made five
// mistakes. A request counter cannot tell them apart. It is also why the
// platform's own WAF rate limit does not solve this: it counts requests at the
// edge and has no idea whether the password was right.
//
// STATE IS IN THE DATABASE, AND THAT IS THE POINT. See the header of
// db/migrations/0007_cms_login_attempts.sql — a module-scoped counter is per
// function instance, so it is not a control at all while looking exactly like one.
// ---------------------------------------------------------------------------

export type LoginScope = "identifier" | "ip";

/** How far back failures are counted — and therefore how long a lockout lasts. */
export const LOGIN_WINDOW_MS = 15 * 60 * 1000;

/**
 * Failures within the window that trip a lockout, per scope.
 *
 * The IP budget is deliberately larger than the identifier budget: several
 * editors may sign in from one office NAT, and locking the address because one
 * of them fumbled a password would take the whole team out. It is set BELOW the
 * roster's combined budget (4 accounts x 6 = 24) so a single host walking every
 * account is stopped by the IP limit before it can lock all four humans out of
 * their own CMS — an attacker's cheapest win here is not a break-in, it is
 * denial of service against the editors.
 */
export const LOGIN_MAX_FAILURES: Record<LoginScope, number> = { identifier: 6, ip: 20 };

/**
 * How long to stall a rejected sign-in, from the failure count.
 *
 * Capped at two seconds ON PURPOSE. The instinct when hardening this is to let
 * the delay grow without limit, but the delay is spent inside a serverless
 * function: a long sleep burns the invocation's duration budget and, past it,
 * the request dies with a timeout — an ambiguous outcome that reads to the
 * caller like an outage rather than a refusal. Friction is all the delay is for.
 * The lockout is the actual control, and holding one costs nothing.
 *
 * Pure and exported so the curve can be asserted without a database.
 */
export function loginFailureDelayMs(failures: number): number {
  if (failures <= 2) return 0;
  if (failures === 3) return 250;
  if (failures === 4) return 500;
  if (failures === 5) return 1000;
  return 2000;
}

/**
 * The client address, best effort.
 *
 * Precedence is not cosmetic. `x-vercel-forwarded-for` is written by the
 * platform and cannot be set by the caller, so on Vercel it is the only header
 * that is ever consulted. `x-forwarded-for` is last precisely BECAUSE a caller
 * can send it: off-Vercel — a local server, or any future host without a trusted
 * proxy — the address is whatever the client claims and the IP scope degrades to
 * an honour system. That is a known limit, not an oversight; it is why the
 * identifier scope exists and why it depends on no network attribution at all.
 * An attacker who forges this header still gets six guesses per address.
 *
 * Returns null when nothing identifies the caller, rather than inventing a
 * shared bucket: one constant fallback would put every anonymous request into a
 * single budget, so one attacker would lock out every real editor at once.
 */
export function clientIp(headers: Headers): string | null {
  for (const name of ["x-vercel-forwarded-for", "x-real-ip", "x-forwarded-for"]) {
    const raw = headers.get(name);
    if (!raw) continue;
    // A forwarded-for chain is "client, proxy1, proxy2" — the client is first.
    const first = raw.split(",")[0].trim().toLowerCase();
    if (first && first.length <= 254) return first;
  }
  return null;
}

/**
 * The counted form of a submitted address, or null if there is nothing to count.
 *
 * A submission that is not a plausible email is NOT counted in the identifier
 * scope, for two independent reasons.
 *
 * The security reason: a caller who types their PASSWORD into the email field
 * would otherwise have that password written into the database in clear text, on
 * the CMS of a licensed CASP. A password is very unlikely to satisfy
 * `isPlausibleEmail`, so this keeps credentials out of a table nobody would
 * think to search for them.
 *
 * The correctness reason, found by running the sibling oracles after this
 * landed: the first version bucketed every malformed submission under one
 * literal `"(malformed)"` key. That is a SHARED counter, so six unrelated
 * malformed attempts locked the bucket and every later malformed submission was
 * refused by the lockout instead of by the check that was supposed to refuse it.
 * B1 and B1b both post deliberately malformed values and assert on the refusal
 * — so within one window they would have stopped exercising the login filter at
 * all while still reporting PASS. A throttle that quietly converts a real
 * assertion into a tautology is worse than no throttle.
 *
 * Nothing is lost by not counting these: an address this predicate rejects can
 * never match an account, so there is no account for the identifier scope to
 * protect. The volume is still bounded — the IP scope counts every attempt,
 * malformed or not.
 */
export function loginIdentifier(submitted: string): string | null {
  const normalised = submitted.trim().toLowerCase();
  return isPlausibleEmail(normalised) ? normalised : null;
}

export type LoginThrottle = {
  locked: boolean;
  /** Milliseconds until enough counted failures age out. 0 when not locked. */
  retryAfterMs: number;
  /** Recorded failures in the window, per scope, since that scope's last success. */
  failures: Record<LoginScope, number>;
  /** Which scope tripped, for the audit record. */
  trippedBy: LoginScope | null;
  /** Set when the store could not be read — the caller MUST refuse. */
  error: string | null;
};

/**
 * Failure timestamps for one key since its last success, newest first.
 *
 * A success resets the count rather than deleting rows: the table is appended
 * to, never rewritten, so an editor who fumbles four times and then signs in
 * correctly starts clean instead of carrying four failures for the rest of the
 * window and being locked out by one later typo. The successful sign-in stays
 * on the record.
 *
 * The 100-row cap cannot truncate a live count: recording stops once a key is
 * locked (see `loginThrottleState`), so a key's failures never approach the cap,
 * and rows arrive newest-first so the cap discards the least relevant end.
 */
async function failuresSinceSuccess(
  scope: LoginScope,
  key: string,
): Promise<{ times: number[]; error: string | null }> {
  const since = new Date(Date.now() - LOGIN_WINDOW_MS).toISOString();
  const { data, error } = await query<{ outcome: string; at: string }[]>(
    `cms_login_attempts?select=outcome,at&tenant_id=eq.${tenantId()}` +
      `&scope=eq.${scope}&key=eq.${encodeURIComponent(key)}` +
      `&at=gte.${encodeURIComponent(since)}&order=at.desc&limit=100`,
  );
  // A readable-but-empty table answers `[]`. A null body on a SELECT means the
  // read did not happen, and is treated as unreadable rather than as "no
  // failures" — that is the difference between failing closed and failing open.
  if (error || !data) return { times: [], error: error ?? "login attempt store unreadable" };

  const times: number[] = [];
  for (const row of data) {
    if (row.outcome === "success") break;
    times.push(new Date(row.at).getTime());
  }
  return { times, error: null };
}

/**
 * Should this sign-in be refused before the password is even considered?
 *
 * FAILS CLOSED, matching `editorIsActive`. If the store cannot be read, every
 * sign-in is refused. The consequence is worth stating plainly rather than
 * discovering later: a database outage takes the CMS admin offline. The
 * alternative is that anyone able to degrade the database is handed an
 * unthrottled login form, and a brute-force control that switches itself off
 * under load is not a control.
 *
 * Either key may be null — nothing identified the caller, or the submitted
 * address was not countable (see `loginIdentifier`). That scope is then not
 * counted at all, rather than every such request sharing one budget: a shared
 * fallback bucket is a lockout that one caller can inflict on every other.
 */
export async function loginThrottleState(
  identifier: string | null,
  ip: string | null,
): Promise<LoginThrottle> {
  const none = Promise.resolve({ times: [], error: null });
  const [byId, byIp] = await Promise.all([
    identifier ? failuresSinceSuccess("identifier", identifier) : none,
    ip ? failuresSinceSuccess("ip", ip) : none,
  ]);

  const error = byId.error ?? byIp.error;
  if (error) {
    return {
      locked: true,
      retryAfterMs: LOGIN_WINDOW_MS,
      failures: { identifier: 0, ip: 0 },
      trippedBy: null,
      error,
    };
  }

  const failures: Record<LoginScope, number> = {
    identifier: byId.times.length,
    ip: byIp.times.length,
  };

  // A scope is locked while its window still holds enough failures. Because
  // nothing is recorded once locked, the count cannot grow, so a lock expires a
  // fixed window after the burst that caused it and CANNOT be held open
  // indefinitely by an attacker who keeps hammering. Lockout as a denial of
  // service against the real editors is a likelier goal than a successful
  // guess, and this is what bounds it.
  let locked = false;
  let retryAfterMs = 0;
  let trippedBy: LoginScope | null = null;

  for (const scope of ["identifier", "ip"] as const) {
    const times = scope === "identifier" ? byId.times : byIp.times;
    const limit = LOGIN_MAX_FAILURES[scope];
    if (times.length < limit) continue;

    // `times` is newest-first. The lock lifts once enough of the oldest have
    // aged out to leave fewer than `limit` in the window — that is, when the
    // failure sitting `limit` back from the newest end finally expires.
    const ascending = [...times].sort((a, b) => a - b);
    const releases = ascending[times.length - limit] + LOGIN_WINDOW_MS - Date.now();
    if (releases <= 0) continue;

    locked = true;
    if (releases > retryAfterMs) {
      retryAfterMs = releases;
      trippedBy = scope;
    }
  }

  return { locked, retryAfterMs, failures, trippedBy, error: null };
}

/**
 * Record one attempt, in every scope that applies.
 *
 * Best-effort, and the asymmetry is deliberate. On the FAILURE path a lost write
 * means one guess went uncounted; it is not an evasion route, because a store an
 * attacker could render unwritable is a store `loginThrottleState` has already
 * failed closed on. On the SUCCESS path a lost write means the counter is not
 * reset, which errs toward locking rather than toward admitting.
 */
export async function recordLoginAttempt(entry: {
  identifier: string | null;
  ip: string | null;
  outcome: "failure" | "success";
  editorId?: string | null;
}): Promise<void> {
  const scopes: { scope: LoginScope; key: string }[] = [];
  if (entry.identifier) scopes.push({ scope: "identifier", key: entry.identifier });
  if (entry.ip) scopes.push({ scope: "ip", key: entry.ip });
  if (!scopes.length) return; // nothing countable — an unroutable, malformed attempt

  await query("cms_login_attempts", {
    method: "POST",
    body: JSON.stringify(
      scopes.map(({ scope, key }) => ({
        tenant_id: tenantId(),
        scope,
        key,
        outcome: entry.outcome,
        // Only a success may name a person. The database refuses the other case
        // outright (cms_login_attempts_failure_is_anonymous); mirroring the rule
        // here means a caller never quietly depends on the constraint to catch it.
        editor_id: entry.outcome === "success" ? (entry.editorId ?? null) : null,
      })),
    ),
  });
}

export type AuditEntry = {
  editorId: string | null;
  // 'author' widened in migration 0006 (X-0133): a byline is reader-visible
  // content, so creating or renaming one is an auditable content write.
  // 'lead' widened in migration 0009 (X-0154): marking an enquiry handled is a
  // named person claiming a member of the public has been dealt with, and from
  // X-0156 a failed notification records itself here rather than vanishing.
  entity: "page" | "post" | "asset" | "editor" | "author" | "lead";
  entityId: string;
  action: string;
  before?: unknown;
  after?: unknown;
  /**
   * Names the PROGRAM behind an unattributed write; never set alongside
   * editorId (migration 0005, cms_audit_actor_exclusive). A failed sign-in uses
   * it: the attempt has no authenticated person, and pinning editor_id on the
   * account being guessed at would record the victim as the actor.
   */
  source?: string | null;
};

/**
 * Append one audit row.
 *
 * Returns the error instead of throwing, and the caller decides. For content
 * writes the caller treats a failed audit as a failed write: an unrecorded edit
 * on a licensed FSP's site is the thing this table exists to prevent.
 */
export async function writeAudit(entry: AuditEntry): Promise<string | null> {
  const { error } = await query("cms_audit", {
    method: "POST",
    body: JSON.stringify({
      tenant_id: tenantId(),
      editor_id: entry.editorId,
      entity: entry.entity,
      entity_id: entry.entityId,
      action: entry.action,
      before: entry.before ?? null,
      after: entry.after ?? null,
      source: entry.source ?? null,
    }),
  });
  return error;
}
