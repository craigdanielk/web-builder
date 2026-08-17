import { NextResponse, type NextRequest } from "next/server";
import { ADMIN_COOKIE, readToken } from "@/lib/admin-auth";
import { editorIsActive } from "@/lib/editor-directory";

// Gate the CMS editor: /admin/* requires a valid session cookie belonging to an
// editor who is still active.
//
// TWO checks, not one. The HMAC proves the cookie is ours and unexpired; the
// directory read proves the person behind it has not been revoked since it was
// issued. Skipping the second would make "revoke access" mean "revoke access in
// up to 12 hours", which is not revocation — see contract assertion B3.
//
// Cost: one PostgREST round trip per /admin navigation. That is affordable on a
// surface used by a handful of staff, and it is the price of the guarantee.
// Hosts on which the Xago-branded editor may be served at all.
//
// WHY THIS EXISTS. The production deployment is reachable on its Vercel aliases
// as well as on xago.io, and on every one of them /admin/login rendered a
// 200 with an Xago logo and a password field on a domain Xago does not own.
// That is the phishing signature that got the exchange mockup deleted in
// X-0137 — same page, same shape, different host. Deployment Protection is the
// platform answer and it is not available on this plan (invalid_sso_protection),
// so the gate lives in code, where it also covers the auto-generated aliases
// that cannot be removed from the project.
//
// A 404 rather than a redirect or a 401: the point is that no Xago-branded
// credential surface EXISTS off the real domain. A 401 still says "there is
// something here to log in to".
//
// ADMIN_ALLOWED_HOSTS opts a specific preview host in, comma-separated, for the
// times someone genuinely needs to exercise the editor on a branch deploy
// (X-0175 made preview deploys standard). It is an explicit act, recorded in
// project settings, not a hole that is open by default.
const ADMIN_HOSTS = new Set(
  [
    ...{{ADMIN_HOSTS_JSON}},
    "localhost",
    "127.0.0.1",
    ...(process.env.ADMIN_ALLOWED_HOSTS ?? "").split(","),
  ]
    .map((h) => h.trim().toLowerCase())
    .filter(Boolean),
);

function adminHostAllowed(req: NextRequest): boolean {
  // host header carries the port in dev; the allowlist is host-only.
  const host = (req.headers.get("host") ?? "").toLowerCase().split(":")[0];
  return ADMIN_HOSTS.has(host);
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (!adminHostAllowed(req)) {
    // Not a redirect. Off the canonical host, this surface does not exist.
    return new NextResponse(null, { status: 404 });
  }

  if (pathname === "/admin/login") return NextResponse.next();

  const session = await readToken(
    req.cookies.get(ADMIN_COOKIE)?.value,
    process.env.ADMIN_SESSION_SECRET ?? "",
  );

  if (session && (await editorIsActive(session.editorId))) return NextResponse.next();

  const url = req.nextUrl.clone();
  url.pathname = "/admin/login";
  url.searchParams.set("next", pathname);
  // Signal WHY when a signature was good but the account is gone, so a revoked
  // editor sees "your access was removed" instead of "wrong password".
  if (session) url.searchParams.set("revoked", "1");

  const res = NextResponse.redirect(url);
  // The cookie is now worthless; clearing it stops every subsequent request
  // paying for a directory lookup that will fail the same way.
  if (session) res.cookies.delete(ADMIN_COOKIE);
  return res;
}

export const config = { matcher: ["/admin/:path*"] };
