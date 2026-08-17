"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { createClient } from "@supabase/supabase-js";
import { ADMIN_COOKIE, makeToken, readToken } from "@/lib/admin-auth";
import { verifyPassword } from "@/lib/editor-password";
import { validateMediaAlt } from "@/lib/puck/media-validation";
import {
  LOGIN_MAX_FAILURES,
  clientIp,
  editorIsActive,
  findEditorForLogin,
  isPlausibleEmail,
  loginFailureDelayMs,
  loginIdentifier,
  loginThrottleState,
  recordLoginAttempt,
  touchLastSeen,
  writeAudit,
} from "@/lib/editor-directory";

const TENANT_ID = process.env.{{CMS_TENANT_ENV}} ?? "";

/**
 * Resolve the signed-in editor, or null.
 *
 * Server actions are directly-invocable POST endpoints — middleware only gates
 * page navigations, so any privileged action must re-check auth itself, INCLUDING
 * the revocation check. A revoked editor who kept an open tab would otherwise
 * still be able to fire a save.
 */
async function currentEditorId(): Promise<string | null> {
  const token = (await cookies()).get(ADMIN_COOKIE)?.value;
  const session = await readToken(token, process.env.ADMIN_SESSION_SECRET ?? "");
  if (!session) return null;
  return (await editorIsActive(session.editorId)) ? session.editorId : null;
}

function db() {
  return createClient(process.env.SUPABASE_URL ?? "", process.env.SUPABASE_SERVICE_ROLE_KEY ?? "", {
    auth: { persistSession: false },
  });
}

// ---- auth ----

const sleep = (ms: number) => (ms > 0 ? new Promise((r) => setTimeout(r, ms)) : Promise.resolve());

/**
 * Sign in with a personal account.
 *
 * There is no shared-password branch and no fallback to one: the whole point of
 * X-0100 is that an edit can be traced to a person, and a password that many
 * people know cannot do that. Wrong email and wrong password produce the SAME
 * message, so the form cannot be used to enumerate who has access.
 *
 * Throttled per submitted address AND per client address (X-0135). Both, because
 * either alone is trivially evaded: one host can walk the whole roster, and one
 * roster entry can be attacked from a proxy pool. See the login-throttling block
 * in editor-directory.ts for the policy and why the state lives in the database.
 */
export async function loginAction(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");
  const next = String(formData.get("next") ?? "/admin");

  const ip = clientIp(await headers());
  const identifier = loginIdentifier(email);

  // Read the throttle BEFORE spending ~100ms of scrypt, so a locked address
  // cannot be used to burn CPU. This returns locked:true when the store is
  // unreadable — fail closed, same posture as editorIsActive.
  const throttle = await loginThrottleState(identifier, ip);

  if (throttle.locked) {
    // Refused with NO delay, NO hash work and NO new record, all deliberate:
    //   - no record, so an attacker who keeps hammering cannot roll the lock
    //     forward forever and hold the real editors out (the lock expires a
    //     fixed window after the burst that caused it);
    //   - no delay, because the lock IS the control and stalling here would
    //     only hold our own invocations open on the attacker's behalf.
    // A fast refusal does disclose that this address is locked. That discloses
    // nothing worth having: the counter is keyed on the SUBMITTED string, so
    // anyone can lock any string they like, including addresses with no account
    // — which is exactly why it cannot be used to tell the two apart.
    const seconds = Math.max(1, Math.ceil(throttle.retryAfterMs / 1000));
    redirect(`/admin/login?error=1&locked=${seconds}`);
  }

  // Reject a malformed address here, before it reaches any query builder. The
  // lookup guards itself too; this is the outer of two independent gates,
  // because "the other layer validates it" is how an unvalidated value
  // eventually reaches a filter.
  const editor =
    isPlausibleEmail(email) && password ? await findEditorForLogin(email) : null;

  // Verify even when there is no such editor, against a hash that cannot match,
  // so a missing account and a wrong password take the same time to reject.
  const stored = editor?.pw_hash ?? "scrypt$32768$8$1$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  const ok = await verifyPassword(password, stored);

  if (!editor || !ok || editor.revoked_at !== null) {
    await recordLoginAttempt({ identifier, ip, outcome: "failure" });

    const failures = throttle.failures.identifier + 1;
    const tripped =
      failures >= LOGIN_MAX_FAILURES.identifier ||
      throttle.failures.ip + 1 >= LOGIN_MAX_FAILURES.ip;

    // Recorded so a burst is legible after the fact. `source` rather than
    // `editorId`: nobody is authenticated on this path, and naming the account
    // being guessed at would file the attack under its victim (migration 0005
    // refuses a row carrying both). Best-effort — a lost audit row must not
    // hand back the sign-in we just refused, and the store that would have to
    // be down for this to fail is the one the throttle already failed closed on.
    await writeAudit({
      editorId: null,
      source: "admin/login",
      entity: "editor",
      // No editor uuid exists on this path — often no account exists at all —
      // so this carries the submitted address instead, and only when
      // `loginIdentifier` vouched for its shape, so a password typed into the
      // email box is never written here in clear text.
      entityId: identifier ?? "(malformed)",
      action: tripped ? "login_locked" : "login_failed",
      after: { ip, failures: { ...throttle.failures }, scope_limits: LOGIN_MAX_FAILURES },
    });

    // The stall is a pure function of the failure count, so an unknown address
    // and a wrong password — which reach this point having done identical work
    // and carrying identical counters — are stalled identically too.
    await sleep(loginFailureDelayMs(failures));
    redirect("/admin/login?error=1");
  }

  await recordLoginAttempt({ identifier, ip, outcome: "success", editorId: editor.id });
  await writeAudit({
    editorId: editor.id,
    entity: "editor",
    entityId: editor.id,
    action: "login",
    after: { ip },
  });

  const token = await makeToken(process.env.ADMIN_SESSION_SECRET ?? "", editor.id);
  // Secure only over https — http://localhost would reject a Secure cookie.
  const isHttps = (await headers()).get("x-forwarded-proto") === "https";
  (await cookies()).set(ADMIN_COOKIE, token, {
    httpOnly: true,
    secure: isHttps,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 12, // 12h
  });
  await touchLastSeen(editor.id);
  redirect(next.startsWith("/admin") ? next : "/admin");
}

export async function logoutAction() {
  (await cookies()).delete(ADMIN_COOKIE);
  redirect("/admin/login");
}

// ---- content mutation (the typed write surface the agent layer will reuse) ----
type PuckItem = { type: string; props?: Record<string, unknown> };

export async function savePageAction(page: string, content: PuckItem[], publish: boolean) {
  const editorId = await currentEditorId();
  if (!editorId) return { ok: false, error: "unauthorized" };

  // Alt-text gate (X-0111, assertion B6). Runs BEFORE the delete-then-insert
  // below, so a rejected save leaves the page exactly as it was rather than
  // half-written. An empty alt is refused unless the image is explicitly marked
  // decorative: empty-by-omission and empty-by-decision look identical in the
  // data, and only the second one is a choice somebody made.
  const alt = validateMediaAlt(content);
  if (!alt.ok) return { ok: false, error: alt.messages.join(" "), violations: alt.violations };

  const supabase = db();
  const status = publish ? "published" : "draft";

  const rows = content.map((item, i) => {
    const section_key = item.type.includes("__") ? item.type.split("__")[1] : item.type;
    const props = { ...(item.props ?? {}) };
    delete (props as { id?: unknown }).id; // strip Puck's internal id
    delete (props as { editMode?: unknown }).editMode;
    return {
      tenant_id: TENANT_ID,
      page_slug: page,
      section_key,
      position: (i + 1) * 10,
      content: props,
      status,
      updated_by: editorId,
    };
  });

  // Read the outgoing state BEFORE destroying it. The publish path is
  // delete-all-then-insert, so without this the audit row could only say "the
  // page changed", not what it changed from.
  const prev = await supabase
    .from("cms_blocks")
    .select("section_key,position,content,status")
    .eq("tenant_id", TENANT_ID)
    .eq("page_slug", page)
    .order("position");

  const del = await supabase.from("cms_blocks").delete().eq("tenant_id", TENANT_ID).eq("page_slug", page);
  if (del.error) return { ok: false, error: del.error.message };
  if (rows.length) {
    const ins = await supabase.from("cms_blocks").insert(rows);
    if (ins.error) return { ok: false, error: ins.error.message };
  }

  // An unrecorded edit on a licensed FSP's website is the failure mode this
  // table exists to prevent, so a failed audit write fails the save rather than
  // being swallowed. The content write already landed; the caller is told, and
  // the next save re-attempts the record.
  const auditError = await writeAudit({
    editorId,
    entity: "page",
    entityId: page,
    action: publish ? "publish" : "save_draft",
    before: prev.data ?? null,
    after: rows.map(({ section_key, position, content, status }) => ({
      section_key,
      position,
      content,
      status,
    })),
  });
  if (auditError) return { ok: false, error: `saved, but the audit record failed: ${auditError}` };

  // Public pages use ISR (revalidate=60); this purge makes a Publish show on the
  // live route within seconds instead of waiting out the revalidation window.
  revalidatePath(page === "homepage" ? "/" : `/${page}`);
  return { ok: true, count: rows.length, status };
}
