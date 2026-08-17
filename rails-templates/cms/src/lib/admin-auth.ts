// Admin editor sessions — per-user, HMAC-signed, edge-verifiable.
//
// The cookie carries the SIGNED IDENTITY of one editor: `<editorId>.<expiry>`
// plus an HMAC over both. It replaces the pre-X-0100 token, which was an HMAC of
// a constant marker and therefore said only "somebody knew the shared password".
//
// This module deliberately uses Web Crypto ONLY, so it runs unchanged in the
// edge middleware and in Node server actions. Password hashing lives in
// `editor-password.ts` (Node-only) because Web Crypto has no scrypt.
//
// A valid signature is NOT sufficient authorisation on its own: the editor must
// also still be active. That check is a database read and lives in
// `editor-directory.ts`, which middleware calls on every request — see contract
// assertion B3.

export const ADMIN_COOKIE = "{{COOKIE_PREFIX}}_admin";
export const SESSION_TTL_MS = 12 * 60 * 60 * 1000; // 12h

async function hmac(secret: string, msg: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(msg));
  let bin = "";
  for (const b of new Uint8Array(sig)) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export type Session = { editorId: string; expiresAt: number };

/**
 * Mint a session token: `<editorId>.<expiryEpochMs>.<hmac>`.
 *
 * The expiry is inside the signed payload so a token cannot be replayed past
 * its lifetime, and the editor id is inside it so a token cannot be re-pointed
 * at a different account.
 */
export async function makeToken(
  secret: string,
  editorId: string,
  ttlMs = SESSION_TTL_MS,
): Promise<string> {
  const exp = String(Date.now() + ttlMs);
  const payload = `${editorId}.${exp}`;
  return `${payload}.${await hmac(secret, payload)}`;
}

/**
 * Verify signature + expiry and return the identity, or null.
 *
 * Returning the identity rather than a boolean is the point of X-0100: every
 * caller that used to ask "is this an admin?" can now ask "which editor is
 * this?", which is what attribution needs.
 */
export async function readToken(
  token: string | undefined,
  secret: string,
): Promise<Session | null> {
  if (!token || !secret) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [editorId, exp, sig] = parts;
  if (!editorId || !exp || !sig) return null;

  const expMs = Number(exp);
  if (!Number.isFinite(expMs) || Date.now() > expMs) return null;
  if (!timingSafeEqual(sig, await hmac(secret, `${editorId}.${exp}`))) return null;

  return { editorId, expiresAt: expMs };
}

// There is deliberately NO signature-only `verifyToken` helper here any more.
// One existed briefly during X-0100 so admin/media/actions.ts could keep
// compiling, and it was the kind of shortcut that gets reached for again: it
// answers "was this cookie minted by us and is it unexpired", which a revoked
// editor's cookie also satisfies. Every gate now resolves the editor and checks
// revoked_at, via `readToken` + `editorIsActive`.
