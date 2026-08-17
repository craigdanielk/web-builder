// Pure image normalisation for the CMS media pipeline (task X-0109).
//
// Buffer in, normalised buffer + intrinsic metadata out. Deliberately free of
// Supabase, filesystem and request context so the transform is unit-testable
// without any I/O — the pure half of the pipeline. Storage lives in store.ts.
//
// Why normalise on upload at all, when the CDN already resizes on request:
// this bounds what we STORE and pay egress on, and fixes phone-photo
// orientation once instead of on every render. Vercel then derives per-
// breakpoint renditions from this master.

import sharp from "sharp";
import {
  MAX_EDGE_PX,
  PASSTHROUGH_MIME,
  WEBP_QUALITY,
} from "./constants";

export type NormalizedImage = {
  /** The bytes to store. WebP for rasters; the untouched original for passthrough types. */
  buffer: Buffer;
  /** Mime of `buffer` — not necessarily the mime that was uploaded. */
  mime: string;
  /** Intrinsic size of the stored master, so callers never re-open the image to size it. */
  width: number | null;
  height: number | null;
  bytes: number;
  /** File extension for the storage path, without the dot. */
  ext: string;
};

/**
 * Normalise an uploaded image into a storable master.
 *
 * Raster path:
 *   1. `.rotate()` with no argument applies the EXIF orientation tag and then
 *      drops the metadata block. This is what both bakes orientation in and
 *      strips EXIF — sharp only preserves metadata when `.withMetadata()` is
 *      called explicitly, which we never do. That also removes GPS coordinates,
 *      which matters for client-supplied photos.
 *   2. Downscale so the longest edge is at most MAX_EDGE_PX. `fit: "inside"`
 *      preserves aspect ratio; `withoutEnlargement` means a small logo is never
 *      upscaled into a blurry larger file.
 *   3. Re-encode to WebP.
 *
 * Passthrough path (SVG): returned untouched. Vector art has no orientation, no
 * EXIF and no meaningful pixel dimensions, and rasterising untrusted SVG through
 * sharp is an attack surface we decline to open.
 */
export async function normalizeImage(
  input: Buffer,
  uploadedMime: string,
): Promise<NormalizedImage> {
  if (PASSTHROUGH_MIME.has(uploadedMime)) {
    return {
      buffer: input,
      mime: uploadedMime,
      width: null,
      height: null,
      bytes: input.byteLength,
      ext: "svg",
    };
  }

  // `failOn: "none"` keeps a slightly-corrupt-but-renderable phone photo from
  // throwing; browsers would display it, so refusing it would be surprising.
  const pipeline = sharp(input, { failOn: "none" })
    .rotate()
    .resize(MAX_EDGE_PX, MAX_EDGE_PX, {
      fit: "inside",
      withoutEnlargement: true,
    })
    .webp({ quality: WEBP_QUALITY });

  const { data, info } = await pipeline.toBuffer({ resolveWithObject: true });

  return {
    buffer: data,
    mime: "image/webp",
    width: info.width,
    height: info.height,
    bytes: data.byteLength,
    ext: "webp",
  };
}
