// Client-safe media types + pure helpers (task X-0112).
//
// `store.ts` is `import "server-only"` and drags @supabase/supabase-js and sharp
// in behind it, so a client component (the picker, the grid) cannot import from
// it — not even for a type, since a stray value import through the same specifier
// would pull the whole module graph into the browser bundle. This file holds the
// shape those components share with the server and nothing else.

/**
 * A `cms_assets` row as the browser sees it.
 *
 * The extra `url` is the point of the type. `SUPABASE_URL` is server-only (there
 * is deliberately no NEXT_PUBLIC_ mirror — see CmsImage.tsx), so a client
 * component cannot build a bucket URL for itself. The server action resolves it
 * once, on the server, and hands it over already built.
 */
export type AssetRef = {
  id: string;
  storage_path: string;
  url: string;
  alt: string;
  focal_x: number;
  focal_y: number;
  width: number | null;
  height: number | null;
  mime: string;
  bytes: number | null;
  checksum: string | null;
};

/** Fields an editor may change on an existing asset. */
export type AssetPatch = {
  alt?: string;
  focal_x?: number;
  focal_y?: number;
};

/**
 * Focal point (0..1) as a CSS `object-position`.
 *
 * Deliberately a second copy of `focalObjectPosition` in components/media/
 * CmsImage.tsx rather than an import of it: CmsImage is a server component that
 * imports next/image, and the admin picker is a client component that must not
 * pull a render-path module in just to place a crosshair. Three lines of
 * arithmetic is the cheaper coupling. Both must agree — if one changes, change
 * both, because the admin preview would otherwise lie about the live crop.
 */
export function focalPosition(focalX?: number | null, focalY?: number | null): string {
  return `${pct(focalX)} ${pct(focalY)}`;
}

function pct(value?: number | null): string {
  const n = typeof value === "number" && Number.isFinite(value) ? value : 0.5;
  return `${Math.round(Math.min(1, Math.max(0, n)) * 1000) / 10}%`;
}

/** Human-readable byte size for the library listing. */
export function formatBytes(bytes: number | null): string {
  if (typeof bytes !== "number" || !Number.isFinite(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * The editor-facing filename. `storage_path` is `<checksum16>-<slug>.<ext>`;
 * the checksum prefix is machinery, not something to show a non-technical user.
 */
export function assetLabel(asset: { storage_path: string }): string {
  return asset.storage_path.replace(/^[0-9a-f]{16}-/, "");
}
