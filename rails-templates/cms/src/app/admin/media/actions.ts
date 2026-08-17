"use server";

// Admin-gated media actions (tasks X-0109 upload, X-0112 library).
//
// Server actions are directly-invocable POST endpoints — middleware only gates
// page navigations, so each of these re-checks auth itself. Same contract as
// src/app/admin/actions.ts; an ungated upload endpoint on a public marketing
// site is an open abuse vector, and an ungated list endpoint leaks the library.

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { ADMIN_COOKIE, readToken } from "@/lib/admin-auth";
import { editorIsActive } from "@/lib/editor-directory";
import {
  MediaUploadError,
  assetUrl,
  ingestUpload,
  searchAssets,
  updateAsset,
  type StoredAsset,
} from "@/lib/media/store";
import type { AssetPatch, AssetRef } from "@/lib/media/asset";

/**
 * Resolve the signed-in editor, or null.
 *
 * TWO checks, not one. `readToken` proves the cookie is ours and unexpired;
 * `editorIsActive` proves the person behind it has not been revoked since it was
 * issued. A signature-only check would let a removed member of staff keep
 * writing to the client's media bucket until their cookie expired — up to 12
 * hours. Same rule the middleware applies (contract assertion B3).
 */
async function isAdmin(): Promise<boolean> {
  const token = (await cookies()).get(ADMIN_COOKIE)?.value;
  const session = await readToken(token, process.env.ADMIN_SESSION_SECRET ?? "");
  return session !== null && (await editorIsActive(session.editorId));
}

/**
 * Attach the public bucket URL on the server.
 *
 * The browser cannot do this: SUPABASE_URL is server-only. Every asset that
 * crosses to a client component goes through here. Not exported — in a
 * `"use server"` module every exported function becomes a public POST endpoint,
 * and this is a pure mapper, not an action.
 */
function ref(asset: StoredAsset): AssetRef {
  return { ...asset, url: assetUrl(asset.storage_path) };
}

export type UploadResult =
  | { ok: true; asset: AssetRef; deduped: boolean }
  | { ok: false; error: string };

export type AssetResult = { ok: true; asset: AssetRef } | { ok: false; error: string };

export type ListResult = { ok: true; assets: AssetRef[] } | { ok: false; error: string };

/**
 * Ingest one uploaded file and return its asset.
 *
 * Returns a typed result rather than throwing: this is called from the editor,
 * where "that file was 20MB" must render as a message next to the field, not a
 * blank error boundary.
 */
export async function uploadMediaAction(formData: FormData): Promise<UploadResult> {
  if (!(await isAdmin())) return { ok: false, error: "Not signed in." };

  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { ok: false, error: "No file was selected." };
  }

  try {
    const { asset, deduped } = await ingestUpload(
      Buffer.from(await file.arrayBuffer()),
      file.type,
      { alt: String(formData.get("alt") ?? ""), filename: file.name },
    );

    // A "replace" carries the old asset's editorial metadata onto the new row.
    // Skipped on a dedupe hit: those bytes already exist under an asset that has
    // its own alt text, and overwriting it would silently edit an image in use
    // somewhere else.
    const inheritFrom = String(formData.get("inheritFrom") ?? "");
    if (inheritFrom && !deduped) {
      const alt = String(formData.get("inheritAlt") ?? "");
      const fx = Number(formData.get("inheritFocalX"));
      const fy = Number(formData.get("inheritFocalY"));
      const patched = await updateAsset(asset.id, {
        alt,
        focal_x: Number.isFinite(fx) ? fx : 0.5,
        focal_y: Number.isFinite(fy) ? fy : 0.5,
      });
      revalidatePath("/admin/media");
      return { ok: true, asset: ref(patched), deduped };
    }

    revalidatePath("/admin/media");
    return { ok: true, asset: ref(asset), deduped };
  } catch (e) {
    return { ok: false, error: message(e, "Upload failed. Please try again.") };
  }
}

/**
 * List or search the tenant's assets.
 *
 * Backs both the library page's search box and the picker, which has no server
 * component to read from — a Puck field renders inside a client tree.
 */
export async function listAssetsAction(query = ""): Promise<ListResult> {
  if (!(await isAdmin())) return { ok: false, error: "Not signed in." };
  try {
    const assets = await searchAssets(query);
    return { ok: true, assets: assets.map(ref) };
  } catch (e) {
    return { ok: false, error: message(e, "Could not load the image library.") };
  }
}

/** Persist an alt-text or focal-point edit. */
export async function updateAssetAction(id: string, patch: AssetPatch): Promise<AssetResult> {
  if (!(await isAdmin())) return { ok: false, error: "Not signed in." };
  if (!id) return { ok: false, error: "No image selected." };
  try {
    const asset = await updateAsset(id, patch);
    // The library reads live (force-dynamic), but any page rendering this asset
    // is cached — a corrected alt attribute is an accessibility fix and should
    // not wait out a revalidation window.
    revalidatePath("/admin/media");
    revalidatePath("/", "layout");
    return { ok: true, asset: ref(asset) };
  } catch (e) {
    return { ok: false, error: message(e, "Could not save that change.") };
  }
}

/**
 * MediaUploadError carries text written for an editor. Anything else is a bug
 * and gets a generic message plus a server-side log — the raw error may name
 * internals, and the editor cannot act on it either way.
 */
function message(e: unknown, fallback: string): string {
  if (e instanceof MediaUploadError) return e.message;
  console.error("[media] unexpected failure", e);
  return fallback;
}
