// Lead notification over the Resend REST API. NODE RUNTIME ONLY.
//
// WRITTEN FRESH, not ported. The Xago tenant repo — the reference implementation
// for every other file in this emission — contains ZERO lines of mail-sending
// code: no Resend, SendGrid, SMTP or nodemailer anywhere under site/, and no
// mail dependency in package.json (census docs/census/2026-08-17-xago-rails.md
// §0.1). What that repo has is the DEMAND side, complete: a cms_leads table, a
// POST /api/contact that returns 200 only after the row commits, an inbox that
// counts un-notified leads, and a `notified_at` column created deliberately
// with no writer. This file is the writer.
//
// NO npm PACKAGE. Resend's REST API is one POST and `fetch` reaches it, which is
// how the whole data layer here is written (see leads.ts). A dependency for one
// HTTP call is weight with no evidence behind it.
//
// THREE PROPERTIES, each load-bearing:
//
//   1. It runs AFTER the row is committed and it CANNOT fail the request. Every
//      path below returns an outcome; nothing throws. An outbound mail
//      provider's uptime is not allowed to become a precondition for our own
//      record-keeping — the rule /api/contact's header states.
//   2. Absent configuration is REPORTED, not defaulted. With no RESEND_API_KEY
//      this returns `sent: false` with a reason naming what is missing and sends
//      nothing. It does not pretend, and it does not silently no-op: the
//      un-notified count in /admin/leads is the visible consequence, which is
//      exactly what 0008 created the column for.
//   3. `notified_at` is stamped only on a 2xx from Resend. A stamp on a failed
//      send would erase the only signal that anything went wrong.

import "server-only";
import { setLeadNotified } from "@/lib/leads";

/** Declared at phase 0 (`email_send_domain`), overridable by env at runtime. */
const SEND_DOMAIN = process.env.EMAIL_SEND_DOMAIN || "{{EMAIL_SEND_DOMAIN}}";
/** Declared at phase 0 (`email_notify_to`), overridable by env at runtime. */
const NOTIFY_TO = process.env.EMAIL_NOTIFY_TO || "{{EMAIL_NOTIFY_TO}}";

export type NotifyOutcome = {
  sent: boolean;
  /** Always populated. Names what happened, including when nothing did. */
  reason: string;
};

export type NotifiableLead = {
  name: string;
  email: string;
  company: string | null;
  message: string;
  source: string;
};

/**
 * What is missing, or null when the sender is fully configured.
 *
 * Separated from the send so a health check can ask "is this wired?" without
 * sending anything, and so the reason a notification did not happen is one
 * string rather than a branch buried in a catch.
 */
export function notifyUnconfiguredReason(): string | null {
  const missing: string[] = [];
  if (!process.env.RESEND_API_KEY) missing.push("RESEND_API_KEY");
  if (!SEND_DOMAIN) missing.push("EMAIL_SEND_DOMAIN");
  if (!NOTIFY_TO) missing.push("EMAIL_NOTIFY_TO");
  return missing.length ? `unconfigured: ${missing.join(", ")} absent` : null;
}

function plainBody(lead: NotifiableLead): string {
  // Deliberately plain text and deliberately verbatim. The enquiry is the
  // visitor's own words; reformatting it into HTML would mean escaping, and an
  // escaping bug in a notification is a way to lose part of a message.
  return [
    `Name:    ${lead.name}`,
    `Email:   ${lead.email}`,
    `Company: ${lead.company ?? "(none given)"}`,
    `Source:  ${lead.source}`,
    "",
    lead.message,
  ].join("\n");
}

/**
 * Notify, best-effort, on top of a lead row that is already committed.
 *
 * `leadId` is optional because the insert path does not currently ask
 * PostgREST for a representation, so the caller may not have the id. Without
 * it the mail still goes out and `notified_at` stays null — which understates
 * what happened, and understating is the correct direction: the inbox shows one
 * more un-notified lead than there are, never one fewer.
 */
export async function notifyLead(
  lead: NotifiableLead,
  leadId?: string,
): Promise<NotifyOutcome> {
  const unconfigured = notifyUnconfiguredReason();
  if (unconfigured) {
    // Not an error and not a success. Logged once so the absence is discoverable
    // in the deploy's own logs as well as in the inbox count.
    console.warn(`[notify] ${unconfigured}; lead stored, not notified`);
    return { sent: false, reason: unconfigured };
  }

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      cache: "no-store",
      headers: {
        authorization: `Bearer ${process.env.RESEND_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        from: `Website enquiries <enquiries@${SEND_DOMAIN}>`,
        to: NOTIFY_TO.split(",").map((a) => a.trim()).filter(Boolean),
        // The visitor's address, so a reply reaches them without a copy-paste.
        // NOT `from`: sending as an address on a domain we do not control is
        // what SPF and DKIM exist to refuse.
        reply_to: lead.email,
        subject: `Website enquiry from ${lead.name}`,
        text: plainBody(lead),
      }),
    });

    if (!res.ok) {
      const detail = (await res.text()).slice(0, 500);
      console.error(`[notify] resend ${res.status}: ${detail}`);
      return { sent: false, reason: `resend ${res.status}` };
    }

    if (leadId) {
      const { error } = await setLeadNotified(leadId);
      if (error) {
        // Sent but not stamped. Reported as sent, because it was — the stamp is
        // bookkeeping and lying about the send would be the larger error.
        console.error(`[notify] sent but notified_at not stamped: ${error}`);
        return { sent: true, reason: `sent; stamp failed: ${error}` };
      }
    }
    return { sent: true, reason: leadId ? "sent and stamped" : "sent; no lead id to stamp" };
  } catch (e) {
    // The one thing this function may never do is propagate. A committed lead
    // must not be reported as a failure because a mail provider timed out.
    const reason = e instanceof Error ? e.message : String(e);
    console.error(`[notify] send threw: ${reason}`);
    return { sent: false, reason: `threw: ${reason}` };
  }
}
