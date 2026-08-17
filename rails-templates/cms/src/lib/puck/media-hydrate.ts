// Render-time hydration of managed image refs (X-0111).
//
// WHY THIS EXISTS AT ALL, since it looks like an avoidable indirection:
//
// All six image-bearing sections are `'use client'` (framer-motion), and a client
// component cannot turn a `cms_assets` id into a URL — `SUPABASE_URL` is
// server-only and there is deliberately no NEXT_PUBLIC mirror, for the reason set
// out at the top of components/media/CmsImage.tsx. Storing the URL in the block
// content instead would denormalise it: the bucket path is derived from the
// asset's checksum, so a re-upload would leave every page pointing at a stale
// object with nothing to detect it. So the id is what is stored, and the id is
// resolved once per page render, on the server, here.
//
// Server-only: this holds the service_role key, same contract as lib/cms.ts.

import "server-only";
import { createClient } from "@supabase/supabase-js";
import { MEDIA_BUCKET } from "@/lib/media/constants";
import { attachAssets, collectAssetIds, type ResolvedAsset } from "./media";

const TENANT_ID = process.env.{{CMS_TENANT_ENV}} ?? "";

type AssetRow = {
  id: string;
  storage_path: string;
  alt: string | null;
  focal_x: number | null;
  focal_y: number | null;
  width: number | null;
  height: number | null;
  mime: string | null;
};

/**
 * Look up the referenced assets in ONE query and attach each row to its ref.
 *
 * Failure is non-fatal by design, and that choice is load-bearing: the whole CMS
 * render path already falls back rather than blanking a page (lib/cms.ts returns
 * null when the store is unreachable). An unresolvable image must cost one image,
 * not the homepage. Sections render a neutral placeholder for a ref with no row.
 *
 * Returns `content` untouched when it holds no managed refs — which is every page
 * until X-0113 migrates them, so the common case costs one tree walk and no I/O.
 */
export async function hydrateBlockMedia<T>(content: T): Promise<T> {
  const ids = [...collectAssetIds(content)];
  if (ids.length === 0) return content;

  const assets = await loadAssets(ids);
  return attachAssets(content, assets) as T;
}

async function loadAssets(ids: string[]): Promise<Map<string, ResolvedAsset>> {
  const out = new Map<string, ResolvedAsset>();

  const url = process.env.SUPABASE_URL ?? "";
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
  if (!url || !key || !TENANT_ID) return out;

  const supabase = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const { data, error } = await supabase
    .from("cms_assets")
    .select("id, storage_path, alt, focal_x, focal_y, width, height, mime")
    .eq("tenant_id", TENANT_ID) // CLAUDE.md rule 2: every read filters by tenant_id
    .in("id", ids);

  if (error || !data) return out;

  for (const row of data as AssetRow[]) {
    out.set(row.id, {
      id: row.id,
      storage_path: row.storage_path,
      url: `${url}/storage/v1/object/public/${MEDIA_BUCKET}/${row.storage_path}`,
      alt: row.alt ?? "",
      focal_x: typeof row.focal_x === "number" ? row.focal_x : 0.5,
      focal_y: typeof row.focal_y === "number" ? row.focal_y : 0.5,
      width: row.width,
      height: row.height,
      mime: row.mime ?? "",
    });
  }

  return out;
}
