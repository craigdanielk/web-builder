// POST /api/contact — where a contact enquiry actually goes (task X-0152).
//
// THE ONE RULE THIS FILE EXISTS TO KEEP: a 200 is returned only after the row
// is committed. The defect being fixed is a form that reported success and
// discarded the message; a route that swallows an insert error and answers 200
// is the identical lie one layer down, and it would pass every check that only
// looks at the status code. So every failure path below returns 500 with
// {ok:false} and no success wording anywhere in the body.
//
// The insert is the source of truth. The X-0156 notification, when it exists,
// is best-effort ON TOP of a committed row and must never veto one: an outbound
// mail provider's uptime is not allowed to become a precondition for our own
// record-keeping. See PLAN-contact-leads.md §6.

import { clientIp, isPlausibleEmail } from "@/lib/editor-directory";
import {
  COMPANY_MAX,
  MESSAGE_MAX,
  NAME_MAX,
  hashIp,
  insertLead,
  leadThrottleState,
} from "@/lib/leads";
import { notifyLead } from "@/lib/notify";

// node:crypto for the HMAC in hashIp(). Declared rather than inferred: on the
// edge runtime this route would fail at request time, not at build time.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Body = Record<string, unknown>;

const str = (v: unknown): string => (typeof v === "string" ? v.trim() : "");

/**
 * Refusals NAME THE FIELD.
 *
 * Not politeness — a 400 that says only "invalid" leaves the visitor guessing
 * which of four inputs to change, and the realistic outcome of guessing is a
 * closed tab. The field name is what lets the form put the message where the
 * person is looking.
 *
 * Field order is fixed and asserted (contract C4): name, then email, then
 * message. An empty submission must report "name", not whichever check happened
 * to run first.
 */
function validate(body: Body):
  | { ok: true; value: { name: string; email: string; company: string | null; message: string; source: string } }
  | { ok: false; field: string; reason: string } {
  const name = str(body.name);
  if (!name) return { ok: false, field: "name", reason: "required" };
  if (name.length > NAME_MAX) return { ok: false, field: "name", reason: `max ${NAME_MAX} characters` };

  const email = str(body.email).toLowerCase();
  if (!email) return { ok: false, field: "email", reason: "required" };
  // The SAME predicate that guards the login path, imported rather than
  // re-expressed: one definition of "an email we accept" on this site, instead
  // of two that drift until they disagree about a real address.
  if (!isPlausibleEmail(email)) return { ok: false, field: "email", reason: "not a valid address" };

  const company = str(body.company);
  if (company.length > COMPANY_MAX) {
    return { ok: false, field: "company", reason: `max ${COMPANY_MAX} characters` };
  }

  const message = str(body.message);
  if (!message) return { ok: false, field: "message", reason: "required" };
  // INCLUSIVE at MESSAGE_MAX. `<` here instead of `<=` would turn away a
  // legitimate long enquiry — the exact loss this endpoint exists to prevent —
  // while every rejection test still passed, which is why C4 asserts the
  // boundary from both sides.
  if (message.length > MESSAGE_MAX) {
    return { ok: false, field: "message", reason: `max ${MESSAGE_MAX} characters` };
  }

  // A provenance label, never a trust boundary: anyone who can POST can set it,
  // exactly as anyone who can POST can set the message. Constrained only in
  // shape, so it cannot smuggle length or punctuation into the row. The
  // verification oracle writes "verify:<run id>" and deletes its own rows.
  const rawSource = str(body.source) || "contact";
  const source = /^[a-z][a-z0-9]*(:[a-z0-9]+)?$/.test(rawSource) && rawSource.length <= 64
    ? rawSource
    : "contact";

  return { ok: true, value: { name, email, company: company || null, message, source } };
}

const json = (body: unknown, status: number, headers?: HeadersInit) =>
  Response.json(body, { status, headers });

export async function POST(req: Request) {
  try {
    let body: Body;
    try {
      body = (await req.json()) as Body;
    } catch {
      return json({ ok: false, field: "body", error: "expected a JSON object" }, 400);
    }
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return json({ ok: false, field: "body", error: "expected a JSON object" }, 400);
    }

    const checked = validate(body);
    if (!checked.ok) {
      return json({ ok: false, field: checked.field, error: checked.reason }, 400);
    }

    const ipHash = hashIp(clientIp(req.headers), process.env.ADMIN_SESSION_SECRET);

    // Counted BEFORE the insert, so a refused submission writes nothing.
    const throttle = await leadThrottleState(ipHash);
    if (throttle.error) {
      // The store could not be read. Not the caller's fault and not their
      // problem to solve, so this is a 500 rather than a 429 — and it is not a
      // 200, because we are about to be unable to keep their message.
      console.error("[contact] throttle read failed:", throttle.error);
      return json({ ok: false, error: "could not accept the message" }, 500);
    }
    if (throttle.limited) {
      return json(
        { ok: false, error: "too many messages from this address" },
        429,
        { "retry-after": String(throttle.retryAfterSec) },
      );
    }

    const { error } = await insertLead({ ...checked.value, ipHash });
    if (error) {
      // The whole point. The message is NOT stored, so the caller is told so —
      // the form shows an address they can reach a human at instead of a
      // thank-you nobody has earned.
      console.error("[contact] insert failed:", error);
      return json({ ok: false, error: "could not save the message" }, 500);
    }

    // X-0156, built here for the first time: the notification the Xago repo
    // specified and never got. It runs AFTER the row is committed and its
    // result is DISCARDED — a mail failure must never turn a saved enquiry
    // into a 500. What it failed to do stays visible in /admin/leads, which
    // counts rows with a null notified_at.
    await notifyLead(checked.value);

    return json({ ok: true }, 200);
  } catch (e) {
    // An unhandled rejection here would surface as an opaque platform error,
    // and an opaque error is indistinguishable from a success to a form that
    // only checks `res.ok === false`. Answer 500 deliberately.
    console.error("[contact] unhandled:", e);
    return json({ ok: false, error: "could not accept the message" }, 500);
  }
}
