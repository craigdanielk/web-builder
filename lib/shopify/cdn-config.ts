/**
 * CDN URL map — Layer 7 static image injection.
 * At build time, load cdn_url_map.json (from Layer 5) and expose section_media lookup.
 * Key: "{page_handle}:{section_type}" -> CDN URL.
 */

export type CdnUrlMap = {
  section_media: Record<string, string>;
  brand_assets: Record<string, string>;
  product_images: string;
  summary?: { uploaded: number; failed: number; skipped_dynamic: number };
};

let cached: CdnUrlMap | null = null;

export function getCdnUrlMap(): CdnUrlMap | null {
  if (cached) return cached;
  try {
    // In Next.js, this can be imported from public or injected at build
    const map = process.env.CDN_URL_MAP_JSON;
    if (map) {
      cached = JSON.parse(map) as CdnUrlMap;
      return cached;
    }
  } catch {
    // ignore
  }
  return null;
}

export function getSectionMediaUrl(pageHandle: string, sectionType: string): string | null {
  const map = getCdnUrlMap();
  if (!map?.section_media) return null;
  const key = `${pageHandle}:${sectionType}`;
  return map.section_media[key] ?? null;
}

export function getBrandAssetPath(assetType: string): string | null {
  const map = getCdnUrlMap();
  if (!map?.brand_assets) return null;
  return map.brand_assets[assetType] ?? null;
}
