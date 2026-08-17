"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { ADMIN_COOKIE, readToken } from "@/lib/admin-auth";
import { getEditor, writeAudit } from "@/lib/editor-directory";
import { setLeadHandled } from "@/lib/leads";

/**
 * Mark an enquiry dealt with, or put it back on the pile (task X-0154).
 *
 * Any active editor may do this, not only an owner: answering an enquiry is the
 * ordinary work of whoever reads the inbox, and a restriction here would just
 * mean the person who replied cannot record that they did.
 *
 * The audit row is written with the SAME discipline as every other content
 * mutation — a named person, the before and after, and the whole write refused
 * if there is no session to name. "Someone said this was handled" is only worth
 * recording if it says who.
 */
export async function markLeadHandledAction(formData: FormData) {
  const session = await readToken(
    (await cookies()).get(ADMIN_COOKIE)?.value,
    process.env.ADMIN_SESSION_SECRET ?? "",
  );
  if (!session) return;

  const me = await getEditor(session.editorId);
  if (!me || me.revoked_at !== null) return;

  const id = String(formData.get("id") ?? "");
  const handled = String(formData.get("handled") ?? "1") === "1";

  const { lead, error } = await setLeadHandled(id, handled);
  if (error || !lead) {
    // Nothing changed, so nothing is recorded. An audit row for a write that
    // did not happen is worse than no audit row: it is a false record.
    console.error("[admin/leads] could not update lead:", error);
    revalidatePath("/admin/leads");
    return;
  }

  await writeAudit({
    editorId: me.id,
    entity: "lead",
    entityId: lead.id,
    action: handled ? "handled" : "reopened",
    after: { handled_at: lead.handled_at },
  });

  revalidatePath("/admin/leads");
}
