// Storage + registry writer for the media pipeline (task X-0109).
//
// Server-only: holds the Supabase service_role key, same contract as cms.ts.
// NEVER import from a client component.
//
// Sequence: checksum the ORIGINAL bytes -> look for an existing asset with that
// checksum -> if absent, normalise, write a content-hashed object, insert a
// tenant-scoped cms_assets row.

import "server-only";
import { createHash } from "node:crypto";
import { createClient } from "@supabase/supabase-js";
import { normalizeImage } from "./normalize";
import { ACCEPTED_MIME, MAX_UPLOAD_BYTES, MEDIA_BUCKET } from "./constants";

const TENANT_ID = process.env.{{CMS_TENANT_ENV}} ?? "";

export type StoredAsset = {
  id: string;
  storage_path: string;
  alt: string;
  focal_x: number;
  focal_y: number;
  width: number | null;
  height: number | null;
  mime: string;
  bytes: number | null;
  checksum: string | null;
};

/** Thrown for input the caller got wrong — surfaced to the editor, not swallowed. */
export class MediaUploadError extends Error {}

function db() {
  const url = process.env.SUPABASE_URL ?? "";
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
  if (!url || !key || !TENANT_ID) {
    throw new MediaUploadError("Media storage is not configured on this environment.");
  }
  return createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
}

const ASSET_COLUMNS =
  "id, storage_path, alt, focal_x, focal_y, width, height, mime, bytes, checksum";

/**
 * Ingest an upload and return its asset row.
 *
 * Idempotent on content: uploading identical bytes twice returns the first
 * asset and writes nothing the second time. The hash is taken over the ORIGINAL
 * upload rather than the normalised output, so a re-upload short-circuits before
 * any sharp work happens.
 */
export async function ingestUpload(
  input: Buffer,
  uploadedMime: string,
  opts: { alt?: string; filename?: string } = {},
): Promise<{ asset: StoredAsset; deduped: boolean }> {
  if (!ACCEPTED_MIME.has(uploadedMime)) {
    throw new MediaUploadError(`Unsupported image type: ${uploadedMime}`);
  }
  if (input.byteLength > MAX_UPLOAD_BYTES) {
    throw new MediaUploadError(
      `Image is ${(input.byteLength / 1048576).toFixed(1)}MB — the limit is ${MAX_UPLOAD_BYTES / 1048576}MB.`,
    );
  }

  const supabase = db();
  const checksum = createHash("sha256").update(input).digest("hex");

  // Dedupe before doing any work. rule 2: every read filters by tenant_id.
  const existing = await supabase
    .from("cms_assets")
    .select(ASSET_COLUMNS)
    .eq("tenant_id", TENANT_ID)
    .eq("checksum", checksum)
    .limit(1);

  if (existing.error) throw new MediaUploadError(existing.error.message);
  if (existing.data && existing.data.length > 0) {
    return { asset: existing.data[0] as StoredAsset, deduped: true };
  }

  const normalized = await normalizeImage(input, uploadedMime);

  // Content-hashed path, never overwritten: Vercel's transform cache does not
  // invalidate on redeploy, so a reused path would serve a stale image. The
  // slug is cosmetic — it only makes the storage browser readable.
  const slug = (opts.filename ?? "image")
    .toLowerCase()
    .replace(/\.[a-z0-9]+$/, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48) || "image";
  const storage_path = `${checksum.slice(0, 16)}-${slug}.${normalized.ext}`;

  const upload = await supabase.storage
    .from(MEDIA_BUCKET)
    .upload(storage_path, normalized.buffer, {
      contentType: normalized.mime,
      // Long max-age is safe precisely because the path is content-addressed.
      cacheControl: "31536000",
      upsert: false,
    });

  // A duplicate path means the same content already landed (checksum prefix
  // collision aside) — tolerate it and fall through to the registry insert.
  if (upload.error && !/exists/i.test(upload.error.message)) {
    throw new MediaUploadError(`Upload failed: ${upload.error.message}`);
  }

  // rule 1: every write carries tenant_id.
  const inserted = await supabase
    .from("cms_assets")
    .insert({
      tenant_id: TENANT_ID,
      storage_path,
      alt: opts.alt ?? "",
      width: normalized.width,
      height: normalized.height,
      mime: normalized.mime,
      bytes: normalized.bytes,
      checksum,
    })
    .select(ASSET_COLUMNS)
    .single();

  if (inserted.error) throw new MediaUploadError(inserted.error.message);
  return { asset: inserted.data as StoredAsset, deduped: false };
}

/** Public CDN URL for an asset. Feed this to next/image, which derives renditions. */
export function assetUrl(storage_path: string): string {
  return `${process.env.SUPABASE_URL}/storage/v1/object/public/${MEDIA_BUCKET}/${storage_path}`;
}

/** Most-recent assets for the tenant — backs the /admin/media library (X-0112). */
export async function listAssets(limit = 100): Promise<StoredAsset[]> {
  const { data, error } = await db()
    .from("cms_assets")
    .select(ASSET_COLUMNS)
    .eq("tenant_id", TENANT_ID)
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) throw new MediaUploadError(error.message);
  return (data ?? []) as StoredAsset[];
}

/** One asset by id, tenant-scoped. Null when it does not exist for this tenant. */
export async function getAsset(id: string): Promise<StoredAsset | null> {
  const { data, error } = await db()
    .from("cms_assets")
    .select(ASSET_COLUMNS)
    .eq("tenant_id", TENANT_ID)
    .eq("id", id)
    .limit(1);
  if (error) throw new MediaUploadError(error.message);
  return (data?.[0] as StoredAsset) ?? null;
}

/**
 * Free-text search across the library (X-0112).
 *
 * Matches the editor-visible fields only — alt text and the filename half of
 * `storage_path`. Searching the checksum prefix would let a query match noise
 * (`ab` hits every path starting `ab…`), which is worse than not matching.
 *
 * An empty query is `listAssets`, not "no results": the search box starts empty
 * and must show the library rather than an empty state that looks like a bug.
 */
export async function searchAssets(query: string, limit = 100): Promise<StoredAsset[]> {
  const q = sanitizeSearch(query);
  if (!q) return listAssets(limit);

  const { data, error } = await db()
    .from("cms_assets")
    .select(ASSET_COLUMNS)
    .eq("tenant_id", TENANT_ID)
    .or(`alt.ilike.%${q}%,storage_path.ilike.%${q}%`)
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) throw new MediaUploadError(error.message);
  return (data ?? []) as StoredAsset[];
}

/**
 * PostgREST parses `or=(...)` as a mini-language: commas separate terms,
 * parentheses group them, and `%`/`*` are wildcards. Anything typed into a
 * search box that reaches that parser unescaped is a syntax error at best and a
 * filter the caller did not write at worst — so the operators are stripped
 * rather than escaped. A user searching for "logo," means "logo".
 */
function sanitizeSearch(query: string): string {
  return String(query ?? "")
    .replace(/[,()*%\\"']/g, " ")
    .trim()
    .slice(0, 80);
}

/**
 * Edit an existing asset's editorial metadata (X-0112).
 *
 * Only alt text and the focal point are mutable. The bytes, the checksum and the
 * storage path are NOT: the path is content-addressed and cached for a year at
 * the CDN, so replacing the image behind an id would serve the old picture from
 * the transform cache indefinitely. Replacement is a new `ingestUpload`, which
 * is why the library's "Replace" copies this metadata onto a new asset instead
 * of writing over this one.
 */
export async function updateAsset(
  id: string,
  patch: { alt?: string; focal_x?: number; focal_y?: number },
): Promise<StoredAsset> {
  const update: Record<string, unknown> = {};

  if (patch.alt !== undefined) update.alt = String(patch.alt).trim().slice(0, 500);
  if (patch.focal_x !== undefined) update.focal_x = focal(patch.focal_x, "focal_x");
  if (patch.focal_y !== undefined) update.focal_y = focal(patch.focal_y, "focal_y");

  if (Object.keys(update).length === 0) {
    throw new MediaUploadError("Nothing to update.");
  }

  // rule 2: the tenant filter is on the UPDATE too. Without it, a guessed uuid
  // from another tenant in this shared database would be writable.
  const { data, error } = await db()
    .from("cms_assets")
    .update(update)
    .eq("tenant_id", TENANT_ID)
    .eq("id", id)
    .select(ASSET_COLUMNS);

  if (error) throw new MediaUploadError(error.message);
  if (!data || data.length === 0) {
    throw new MediaUploadError("That image no longer exists.");
  }
  return data[0] as StoredAsset;
}

/**
 * Validate a focal coordinate before it reaches the DB check constraint.
 *
 * The constraint would reject it anyway; catching it here means the editor sees
 * "must be between 0 and 1" instead of a Postgres constraint name.
 */
function focal(value: number, field: string): number {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || n > 1) {
    throw new MediaUploadError(`${field} must be a number between 0 and 1 (got ${value}).`);
  }
  // Two decimals is finer than a click on a 400px preview can express; storing
  // full float noise makes diffs unreadable for no gain.
  return Math.round(n * 100) / 100;
}
