// /admin/media — the branded asset library (task X-0112).
//
// Gated by src/middleware.ts like every other /admin route: unauthenticated
// requests are redirected to /admin/login before this file runs. Assertion B4
// tests that redirect and the listing count together, because a library that
// lists correctly while being world-readable is not a pass.
//
// The first page of assets is read here, on the server, and handed to the client
// shell — so the listing is in the initial HTML rather than appearing after a
// round trip. That is both better for the editor and what makes B4 measurable.

import Link from "next/link";
import { listAssets, assetUrl, MediaUploadError } from "@/lib/media/store";
import type { AssetRef } from "@/lib/media/asset";
import { logoutAction } from "@/app/admin/actions";
import MediaLibrary from "@/components/admin/MediaLibrary";

export const metadata = { title: "{{BRAND_NAME}} CMS — Images" };

// Never cached: an editor who uploads an image and reloads must see it, and B4
// asserts the rendered count equals the live row count.
export const dynamic = "force-dynamic";

const NAVY = "#0d0e45";

export default async function AdminMedia() {
  let assets: AssetRef[] = [];
  let error: string | null = null;

  try {
    assets = (await listAssets()).map((a) => ({ ...a, url: assetUrl(a.storage_path) }));
  } catch (e) {
    // A misconfigured environment must say so. Rendering an empty grid would
    // read as "you have no images", which is a different and false statement.
    error =
      e instanceof MediaUploadError
        ? e.message
        : "The image library could not be loaded. Check the server logs.";
  }

  return (
    <main style={{ minHeight: "100vh", background: "#fafaf9", fontFamily: "Inter, system-ui, sans-serif" }}>
      <header style={{ background: NAVY, padding: "20px 24px" }}>
        <div style={{ maxWidth: 1180, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" style={{ height: 26, width: "auto" }} />
            <span style={{ color: "#fff", fontSize: 15, fontWeight: 600, letterSpacing: "0.01em" }}>
              Content Manager
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Link href="/admin" style={{ color: "rgba(255,255,255,.75)", fontSize: 13, textDecoration: "none" }}>
              ← All pages
            </Link>
            <form action={logoutAction}>
              <button
                style={{ padding: "8px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,.25)", background: "rgba(255,255,255,.08)", color: "#fff", fontSize: 13, fontWeight: 500, cursor: "pointer" }}
              >
                Sign out
              </button>
            </form>
          </div>
        </div>
      </header>

      <div style={{ maxWidth: 1180, margin: "0 auto", padding: "40px 24px 64px" }}>
        <h1 style={{ fontSize: 26, fontWeight: 600, color: "#1c1917", margin: 0 }}>Images</h1>
        <p style={{ fontSize: 15, color: "#78716c", margin: "6px 0 28px", maxWidth: 620 }}>
          Every image used on the website. Upload new ones, write the description screen readers
          announce, and set which part of a picture stays visible when a section crops it.
        </p>

        {error ? (
          <p role="alert" style={{ fontSize: 14, color: "#991b1b", background: "#fee2e2", padding: "12px 16px", borderRadius: 10 }}>
            {error}
          </p>
        ) : (
          <MediaLibrary initialAssets={assets} />
        )}
      </div>
    </main>
  );
}
