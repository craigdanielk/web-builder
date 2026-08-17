// The managed-image content shape, and the pure helpers that read it (X-0111).
//
// Client-safe by construction: no React, no `server-only`, no Supabase. Both the
// Puck field (browser) and the render-time hydrator (server) import from here, so
// the two can never disagree about what an image ref looks like.
//
// A managed image is stored as:
//     { "assetId": "<cms_assets uuid>", "alt": "<string>", "decorative"?: true }
//
// A LEGACY plain string path ("/team/mark-fitzjohn.jpg") is still accepted on
// read, and that is not a nicety: X-0113 migrates the 38 existing refs AFTER this
// task lands, so between the two the database holds both shapes at once and every
// section has to render both. Only the new shape is ever written.

/**
 * A `cms_assets` row as a section needs it at render time.
 *
 * Carries `url` already built, because the section components are `'use client'`
 * and `SUPABASE_URL` is server-only — see the header of components/media/CmsImage.tsx.
 */
export type ResolvedAsset = {
  id: string;
  storage_path: string;
  url: string;
  alt: string;
  focal_x: number;
  focal_y: number;
  width: number | null;
  height: number | null;
  mime: string;
};

export type MediaRef = {
  assetId: string;

  /**
   * Per-usage alt override. Distinct from the asset's own default alt: the same
   * headshot is described differently on a leadership grid than in an article.
   * `undefined` means "no override, use the asset's alt"; `""` means the editor
   * deliberately blanked it, and that is NOT the same thing.
   */
  alt?: string;

  /**
   * The image carries no information a reader would miss — a feature icon beside
   * a heading that already says the same thing. `alt=""` is the WCAG-correct
   * value for one, and this flag is what makes that value a RECORDED DECISION
   * rather than an omission, so the save gate can tell the two apart.
   *
   * Ratified by the lead 2026-07-30, correcting contract §3 B6, which as written
   * made the correct value unsavable and would have forced an editor to invent
   * descriptive copy for a decorative chevron on a licensed FSP's site.
   *
   * Only ever `true` or absent. `true` alongside non-empty alt is contradictory
   * and is rejected, not silently resolved in either direction.
   */
  decorative?: boolean;

  /**
   * Injected by `hydrateBlockMedia()` on the render path. NEVER persisted — the
   * admin editor re-reads `cms_blocks` directly, so what is saved is only ever
   * `{ assetId, alt }`.
   */
  asset?: ResolvedAsset | null;
};

/** What a section can be handed for an image field, across both content eras. */
export type MediaValue = MediaRef | string | null | undefined;

/** True for the managed shape. A bare string is legacy, not a ref. */
export function isMediaRef(value: unknown): value is MediaRef {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    typeof (value as MediaRef).assetId === "string" &&
    (value as MediaRef).assetId.length > 0
  );
}

/** The asset id a value points at, or null for legacy/empty values. */
export function mediaAssetId(value: unknown): string | null {
  return isMediaRef(value) ? value.assetId : null;
}

export type ResolvedMedia =
  /** A legacy `/public` path. Rendered by a plain <img>, exactly as before. */
  | { kind: "legacy"; src: string; alt: string }
  /** A managed asset whose row was hydrated on the server. */
  | { kind: "managed"; asset: ResolvedAsset; alt: string }
  /**
   * A managed ref whose row was NOT hydrated — inside the Puck editor canvas,
   * or an asset deleted out from under the content. Sections render a neutral
   * placeholder rather than a broken image.
   */
  | { kind: "unresolved"; assetId: string; alt: string };

/**
 * Turn a stored value into something renderable.
 *
 * ALT RESOLUTION: a ref marked `decorative` renders `alt=""` and nothing
 * overrides that — the flag IS the decision. Otherwise, in order: per-usage
 * override, then the asset's library alt, then `fallbackAlt`, then "".
 *
 * `fallbackAlt` is the description the section already had for this slot — a
 * retired sibling field (`logos[].alt`, `image_alt`) or an adjacent label that
 * names the same thing (a board member's name, a currency's name). Nothing here
 * is generated: a fallback is only ever text the page already displays, and a
 * slot with no such label (a decorative feature icon) passes none and stays
 * `alt=""`, which is the correct value for it.
 *
 * Note what an UNFLAGGED blank does NOT mean: it is not read as "decorative,
 * leave it blank". That is what `decorative` is for, and the difference is not
 * academic — measured 2026-07-30, X-0113 had migrated 19 refs on /company and
 * /supported-currencies with `alt: ""` and no flag, and honouring those blanks
 * verbatim silently dropped the alt text off seven board headshots and twelve
 * currency icons that had carried the person's or currency's name since launch.
 * Rendering falls back; the save gate (media-validation.ts) separately refuses
 * to publish an unflagged blank. Both jobs are needed and neither substitutes.
 */
export function resolveMedia(value: MediaValue, fallbackAlt = ""): ResolvedMedia | null {
  if (typeof value === "string") {
    const src = value.trim();
    return src ? { kind: "legacy", src, alt: fallbackAlt } : null;
  }

  if (!isMediaRef(value)) return null;

  const asset = value.asset ?? null;
  const alt = value.decorative === true
    ? ""
    : firstNonBlank(value.alt, asset?.alt, fallbackAlt);

  if (!asset) return { kind: "unresolved", assetId: value.assetId, alt };
  return { kind: "managed", asset, alt };
}

function firstNonBlank(...candidates: (string | null | undefined)[]): string {
  for (const c of candidates) {
    if (typeof c === "string" && c.trim() !== "") return c;
  }
  return "";
}

/**
 * Every asset id referenced anywhere inside a block's content, deduped.
 *
 * Walks blind rather than knowing the six field paths: the paths are declared in
 * puck/config.tsx and a seventh added there must not silently stop rendering
 * because a hardcoded list here was not updated too.
 */
export function collectAssetIds(content: unknown, into = new Set<string>()): Set<string> {
  if (content == null) return into;
  if (Array.isArray(content)) {
    for (const item of content) collectAssetIds(item, into);
    return into;
  }
  if (typeof content !== "object") return into;

  const id = mediaAssetId(content);
  if (id) into.add(id);

  for (const v of Object.values(content as Record<string, unknown>)) {
    collectAssetIds(v, into);
  }
  return into;
}

/**
 * Deep copy of `content` with every `MediaRef` given its `asset`.
 *
 * Pure — the caller supplies the lookup, so this is testable without a database
 * and the same function serves the public render path and the editor.
 */
export function attachAssets(
  content: unknown,
  assets: Map<string, ResolvedAsset>,
): unknown {
  if (content == null) return content;
  if (Array.isArray(content)) return content.map((item) => attachAssets(item, assets));
  if (typeof content !== "object") return content;

  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(content as Record<string, unknown>)) {
    out[k] = attachAssets(v, assets);
  }

  const id = mediaAssetId(content);
  if (id) out.asset = assets.get(id) ?? null;
  return out;
}

/**
 * The inverse of `attachAssets`: drop every render-only `asset` from a ref.
 *
 * Needed because the admin editor is hydrated too (so its canvas draws the real
 * photograph, gate H-B2) and `savePageAction` persists an item's props WHOLESALE
 * — it deletes only Puck's `id` and `editMode` and keeps everything else. So
 * without this, opening a page in the editor and pressing Publish would write a
 * frozen copy of every `cms_assets` row into `cms_blocks.content`: exactly the
 * denormalisation the id-only shape exists to prevent, since a storage path is
 * derived from the file's checksum and goes stale the moment an image is
 * replaced. Hydrate on the way in, strip on the way out, symmetrically.
 */
export function stripHydratedAssets(content: unknown): unknown {
  if (content == null) return content;
  if (Array.isArray(content)) return content.map(stripHydratedAssets);
  if (typeof content !== "object") return content;

  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(content as Record<string, unknown>)) {
    // Only inside a media ref: `asset` is a plausible field name elsewhere, and
    // deleting it blindly would silently eat unrelated content.
    if (k === "asset" && isMediaRef(content)) continue;
    out[k] = stripHydratedAssets(v);
  }
  return out;
}
