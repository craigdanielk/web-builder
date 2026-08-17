import Link from "next/link";
import { listLeads, type Lead } from "@/lib/leads";
import { relativeTime } from "@/lib/cms-attribution";
import { logoutAction } from "@/app/admin/actions";
import { markLeadHandledAction } from "@/app/admin/leads/actions";

export const metadata = { title: "{{BRAND_NAME}} CMS — Enquiries" };

// Never cached. An inbox that shows a stale list is an inbox that hides the
// enquiry that arrived four minutes ago, which is the one that matters most.
export const dynamic = "force-dynamic";

const NAVY = "#0d0e45";
const ORANGE = "#f47643";

// Gated by src/middleware.ts (matcher: ["/admin/:path*"]) — this route needs no
// auth code of its own, which is exactly why C10 asserts the redirect rather
// than assuming it. A page that is protected by somebody else's matcher is one
// rename away from being public.
export default async function LeadsPage() {
  const leads = await listLeads();
  const unnotified = leads.filter((l) => l.notified_at === null).length;
  const open = leads.filter((l) => l.handled_at === null).length;

  return (
    <main style={{ minHeight: "100vh", background: "#fafaf9", fontFamily: "Inter, system-ui, sans-serif" }}>
      <header style={{ background: NAVY, padding: "20px 24px" }}>
        <div style={{ maxWidth: 880, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" style={{ height: 26, width: "auto" }} />
            <span style={{ color: "#fff", fontSize: 15, fontWeight: 600, letterSpacing: "0.01em" }}>Content Manager</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <Link href="/admin" style={{ color: "rgba(255,255,255,.75)", fontSize: 13, textDecoration: "none" }}>
              ← Pages
            </Link>
            <form action={logoutAction}>
              <button style={{ padding: "8px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,.25)", background: "rgba(255,255,255,.08)", color: "#fff", fontSize: 13, fontWeight: 500, cursor: "pointer" }}>
                Sign out
              </button>
            </form>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 880, margin: "0 auto", padding: "40px 24px 64px" }}>
        <h1 style={{ fontSize: 26, fontWeight: 600, color: "#1c1917", margin: 0 }}>Enquiries</h1>
        <p style={{ fontSize: 15, color: "#78716c", margin: "6px 0 28px", maxWidth: 620 }}>
          Everything sent through the contact form on the website. Newest first. Marking one
          handled records who dealt with it and when — it does not delete anything.
        </p>

        {/*
          The un-notified count, shown from day one though nothing sets
          notified_at until X-0156 lands.

          This is the answer to the strongest argument against storing a lead
          whose notification failed: that an unnotified lead nobody checks is
          functionally lost, and the site has then made the same promise it
          could not keep. A silent best-effort failure is what let the original
          defect live. So the failure is made VISIBLE instead of fatal, and this
          line is that mechanism.
        */}
        {unnotified > 0 ? (
          <div style={{ padding: "14px 18px", background: "#fff", border: `2px solid ${ORANGE}`, borderRadius: 10, marginBottom: 24 }}>
            <p style={{ fontSize: 14, fontWeight: 600, color: "#1c1917", margin: 0 }}>
              {unnotified} {unnotified === 1 ? "enquiry has" : "enquiries have"} not been emailed to anyone
            </p>
            <p style={{ fontSize: 13, color: "#78716c", margin: "5px 0 0", lineHeight: 1.6 }}>
              They are safely stored and listed below. Email notification is not switched on yet,
              so this page is currently the only place they appear — please check it daily.
            </p>
          </div>
        ) : null}

        <p style={{ fontSize: 13, color: "#78716c", margin: "0 0 18px" }}>
          {leads.length === 0
            ? "No enquiries yet."
            : `${leads.length} total · ${open} not yet handled`}
        </p>

        {leads.length === 0 ? (
          <EmptyState />
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {leads.map((lead) => (
              <LeadRow key={lead.id} lead={lead} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

/*
  The empty state, before the first real enquiry arrives.

  It renders the SAME <LeadRow> the real list uses, fed a sample object. That is
  the whole point of doing it this way rather than mocking up a card by hand: a
  hand-drawn preview is a second copy of the layout, and a second copy of state
  is a bug. Change LeadRow and this changes with it, or it cannot go stale.

  It is inert by construction: aria-hidden so a screen reader is not told about
  an enquiry that does not exist, and pointer-events:none so the "Mark handled"
  button inside it cannot be clicked. The caption sits ABOVE it in normal
  contrast, so nothing here can be mistaken for a real message from a real
  person — the field values say what they are rather than impersonating anyone.
*/
const SAMPLE: Lead = {
  id: "sample",
  name: "Their name",
  email: "their.address@example.com",
  company: "Their company (optional — omitted if they leave it blank)",
  message:
    "Their message, exactly as typed, line breaks and all.\n\n" +
    "Reply by clicking the email address above — that opens your mail client " +
    "with the address filled in. Then press Mark handled so the rest of the " +
    "team can see it has been dealt with.",
  source: "contact-form",
  created_at: new Date().toISOString(),
  handled_at: null,
  notified_at: null,
};

function EmptyState() {
  return (
    <div>
      <p style={{ fontSize: 13, color: "#78716c", margin: "0 0 10px", lineHeight: 1.6 }}>
        Nothing has come in yet. When someone fills in the form on the website, it will
        appear here looking like this:
      </p>
      <div aria-hidden="true" style={{ pointerEvents: "none", opacity: 0.55 }}>
        <LeadRow lead={SAMPLE} />
      </div>
    </div>
  );
}

function LeadRow({ lead }: { lead: Lead }) {
  const handled = lead.handled_at !== null;
  return (
    <div
      style={{
        padding: "16px 18px",
        background: "#fff",
        border: "1px solid #ece9e4",
        borderRadius: 10,
        opacity: handled ? 0.65 : 1,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 15, fontWeight: 600, color: "#1c1917", margin: 0, wordBreak: "break-word" }}>
            {lead.name}
            {lead.company ? <span style={{ fontWeight: 500, color: "#78716c" }}> · {lead.company}</span> : null}
          </p>
          <p style={{ fontSize: 13, margin: "3px 0 0" }}>
            {/* The reply path. A mailto is the whole workflow this page needs. */}
            <a href={`mailto:${lead.email}`} style={{ color: NAVY }}>{lead.email}</a>
            <span style={{ color: "#78716c" }}>
              {" · "}{relativeTime(lead.created_at)}
              {handled ? " · handled" : null}
              {lead.notified_at === null ? " · not emailed" : null}
            </span>
          </p>
        </div>
        <form action={markLeadHandledAction} style={{ flexShrink: 0 }}>
          <input type="hidden" name="id" value={lead.id} />
          <input type="hidden" name="handled" value={handled ? "0" : "1"} />
          <button
            style={{ padding: "8px 14px", borderRadius: 8, border: "1px solid #e7e5e4", background: handled ? "#fff" : "#f0fdf4", color: handled ? "#57534e" : "#15803d", fontSize: 13, fontWeight: 500, cursor: "pointer", whiteSpace: "nowrap" }}
          >
            {handled ? "Reopen" : "Mark handled"}
          </button>
        </form>
      </div>
      <p style={{ fontSize: 14, color: "#44403c", margin: "12px 0 0", lineHeight: 1.65, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
        {lead.message}
      </p>
    </div>
  );
}
