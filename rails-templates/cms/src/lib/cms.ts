// CMS render layer — reads the tenant-scoped `cms_blocks` content store.
//
// Server-only. Uses the Supabase service_role key (bypasses RLS) and filters
// every query by tenant_id explicitly, per CLAUDE.md rule 2 ("all reads MUST
// filter by tenant_id"). NEVER import this from a client component — the
// service_role key must never reach the browser.
//
// Design contract (0001_cms_blocks.sql, design-spec.md §5):
//   "give me tenant T's published blocks for page P, ordered by position,
//    and hydrate each section_key's component with its content."

import "server-only";
import { createClient } from "@supabase/supabase-js";
import { hydrateBlockMedia } from "@/lib/puck/media-hydrate";

export type CmsBlock = {
  section_key: string;
  archetype: string | null;
  variant: string | null;
  position: number;
  content: Record<string, unknown>;
};

const TENANT_ID = process.env.{{CMS_TENANT_ENV}} ?? "";
const SUPABASE_URL = process.env.SUPABASE_URL ?? "";
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";

function client() {
  if (!SUPABASE_URL || !SERVICE_KEY || !TENANT_ID) return null;
  return createClient(SUPABASE_URL, SERVICE_KEY, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

/**
 * Published blocks for `pageSlug`, ordered by position.
 *
 * Returns `null` when the store is unreachable, unconfigured, or empty — the
 * caller MUST fall back to the in-file section stack so the site never renders
 * blank if the CMS is down. A non-null empty array is never returned; absence
 * of content collapses to null.
 */
export async function getPageBlocks(pageSlug: string): Promise<CmsBlock[] | null> {
  const supabase = client();
  if (!supabase) return null;

  const { data, error } = await supabase
    .from("cms_blocks")
    .select("section_key, archetype, variant, position, content")
    .eq("tenant_id", TENANT_ID) // rule 2: every read filters by tenant_id
    .eq("page_slug", pageSlug)
    .eq("status", "published")
    .order("position", { ascending: true });

  if (error || !data || data.length === 0) return null;

  // Managed image refs (`{ assetId, alt }`, X-0111) carry only an id. Resolve
  // them to bucket URLs here, in the one place BOTH render paths pass through —
  // app/page.tsx for the homepage and lib/cms.page.tsx for the other eight. The
  // sections that draw them are client components and cannot do it themselves:
  // SUPABASE_URL is server-only. One extra query per page render, and none at
  // all for a page whose content holds no managed refs.
  return (await hydrateBlockMedia(data as CmsBlock[])) as CmsBlock[];
}
