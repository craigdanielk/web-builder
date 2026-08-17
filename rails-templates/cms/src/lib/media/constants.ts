// Media pipeline constants (task X-0109).
//
// Shared by the pure normaliser, the storage writer and the admin action so the
// caps live in exactly one place.

/** Storage bucket created in X-0108: public read, 15MB cap, image mimes only. */
export const MEDIA_BUCKET = "{{MEDIA_BUCKET}}";

/**
 * Longest-edge cap for the stored master, in pixels.
 *
 * Sized against the largest rendition the site can ask for: Next's default
 * deviceSizes top out at 3840, but a 2560 master covers every real layout here
 * (widest full-bleed section at 2x DPR) while roughly halving the bytes of a
 * 4000px phone photo. Vercel scales DOWN from the master, so this is the
 * ceiling on delivered quality — raise it before adding a full-bleed 4K hero.
 */
export const MAX_EDGE_PX = 2560;

/** WebP quality. 82 is the knee of the size/quality curve for photographic content. */
export const WEBP_QUALITY = 82;

/** Hard byte cap, mirrored from the bucket policy so we fail fast with a good message. */
export const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;

/**
 * Accepted upload types.
 *
 * SVG is accepted but NEVER passed through sharp — rasterising untrusted SVG is a
 * known attack surface. It is stored byte-for-byte and must not be routed through
 * next/image (which refuses SVG without dangerouslyAllowSVG). Serving it from the
 * bucket origin rather than the site origin keeps any script it contains away from
 * the admin session cookie.
 */
export const ACCEPTED_MIME = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/avif",
  "image/gif",
  "image/svg+xml",
]);

/** Types that bypass the raster pipeline entirely. */
export const PASSTHROUGH_MIME = new Set(["image/svg+xml"]);
