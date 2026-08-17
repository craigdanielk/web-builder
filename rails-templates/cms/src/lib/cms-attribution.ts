// "Last edited by / when", for the /admin page picker (task X-0100).
//
// Reads the audit log rather than cms_blocks.updated_at, deliberately: the
// publish path deletes and re-inserts every block on the page, so
// cms_blocks.updated_at is really "when this row was created" and cannot
// distinguish a real edit from a re-seed. cms_audit records the act itself.

import { createClient } from "@supabase/supabase-js";

const TENANT_ID = process.env.{{CMS_TENANT_ENV}} ?? "";

/**
 * `email` names a person; `source` names a program (a seed, an importer). Never
 * both — cms_audit_actor_exclusive refuses a row carrying both, because a write
 * is one or the other. Both NULL is pre-0004 history.
 */
export type LastEdit = { at: string; action: string; email: string | null; source: string | null };

/** page_slug -> the most recent recorded edit. Pages never edited are absent. */
export async function lastEditByPage(): Promise<Map<string, LastEdit>> {
  const out = new Map<string, LastEdit>();

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key || !TENANT_ID) return out;

  const sb = createClient(url, key, { auth: { persistSession: false } });

  const { data: rows, error } = await sb
    .from("cms_audit")
    .select("entity_id,action,at,editor_id,source")
    .eq("tenant_id", TENANT_ID)
    .eq("entity", "page")
    .order("at", { ascending: false })
    .limit(400);

  // The picker must still render if attribution is unavailable — losing the
  // byline line is a degraded page, losing the Edit buttons is an outage.
  if (error || !rows) return out;

  const editorIds = [...new Set(rows.map((r) => r.editor_id).filter(Boolean))] as string[];
  const emails = new Map<string, string>();
  if (editorIds.length) {
    const { data: editors } = await sb
      .from("cms_editors")
      .select("id,email")
      .eq("tenant_id", TENANT_ID)
      .in("id", editorIds);
    for (const e of editors ?? []) emails.set(e.id, e.email);
  }

  // Rows arrive newest-first, so the first sighting of a slug is its latest edit.
  for (const r of rows) {
    if (out.has(r.entity_id)) continue;
    out.set(r.entity_id, {
      at: r.at,
      action: r.action,
      email: r.editor_id ? emails.get(r.editor_id) ?? null : null,
      source: r.source ?? null,
    });
  }
  return out;
}

/** "2 hours ago" / "12 Mar 2026" — short enough to sit on one line in the picker. */
export function relativeTime(iso: string, now = Date.now()): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const mins = Math.round((now - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  if (days < 14) return `${days} day${days === 1 ? "" : "s"} ago`;
  return new Date(then).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
