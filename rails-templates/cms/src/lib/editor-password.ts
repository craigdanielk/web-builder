// Password hashing for CMS editors (task X-0100). NODE RUNTIME ONLY.
//
// scrypt, not PBKDF2-via-Web-Crypto: scrypt is memory-hard, which is the
// property that makes a stolen `pw_hash` expensive to attack offline. The cost
// of that choice is that it cannot run in the edge middleware — Web Crypto has
// no scrypt — so nothing on the middleware path may import this file. That is
// why middleware verifies an HMAC and a revocation flag, never a password.

import { randomBytes, scrypt as scryptCb, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";

const scrypt = promisify(scryptCb);

// N=2^15 with r=8 needs ~32MB per hash. Chosen over the OWASP-2023 minimum of
// 2^14 because logins here are rare (a handful of staff, twice a day) so the
// ~100ms cost is invisible, while every doubling doubles an attacker's bill.
// N is stored IN the hash string so raising it later does not invalidate
// existing rows — verification reads the parameters it was created with.
const N = 32768;
const R = 8;
const P = 1;
const KEYLEN = 32;
const SALT_BYTES = 16;

/** `scrypt$N$r$p$<salt b64>$<derived b64>` */
export async function hashPassword(password: string): Promise<string> {
  const salt = randomBytes(SALT_BYTES);
  const derived = (await scrypt(password.normalize("NFKC"), salt, KEYLEN, {
    N,
    r: R,
    p: P,
    maxmem: 64 * 1024 * 1024,
  })) as Buffer;
  return ["scrypt", N, R, P, salt.toString("base64"), derived.toString("base64")].join("$");
}

/**
 * Constant-time verification. Returns false rather than throwing on a malformed
 * stored hash: a corrupt row must deny access, not 500 the login page.
 */
export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  try {
    const [scheme, n, r, p, saltB64, hashB64] = String(stored).split("$");
    if (scheme !== "scrypt") return false;

    const salt = Buffer.from(saltB64, "base64");
    const expected = Buffer.from(hashB64, "base64");
    if (salt.length === 0 || expected.length === 0) return false;

    const derived = (await scrypt(password.normalize("NFKC"), salt, expected.length, {
      N: Number(n),
      r: Number(r),
      p: Number(p),
      maxmem: 64 * 1024 * 1024,
    })) as Buffer;

    return derived.length === expected.length && timingSafeEqual(derived, expected);
  } catch {
    return false;
  }
}

/**
 * The shortest password a person may choose for themselves (task X-0181).
 *
 * 12, not 8. The generated passwords handed out at invite time are ~100 bits;
 * the moment someone can pick their own, the roster's real strength becomes
 * whatever the weakest self-chosen one is. No composition rules (an upper, a
 * digit, a symbol) — they push people toward `Password1!` and are not what makes
 * a password expensive to guess. Length is.
 */
export const MIN_PASSWORD_LENGTH = 12;

/**
 * Why this password is unacceptable, or null if it is fine.
 *
 * Pure and exported so the policy can be asserted without a database or a
 * browser, and so the SERVER owns the rule. A `minLength` on the input element
 * is a hint to a cooperating browser; this is the check.
 */
export function passwordComplaint(password: string): string | null {
  const pw = password.normalize("NFKC");
  if (pw.length < MIN_PASSWORD_LENGTH) {
    return `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  // A password that is all one character repeated is long and worthless. This is
  // the only content rule, and it exists to catch `aaaaaaaaaaaa`, not to police
  // choices.
  if (new Set(pw).size < 4) {
    return "Use a few more different characters.";
  }
  return null;
}

// Crockford-ish base32: no I/O/1/0, so a password read aloud or copied off a
// screen cannot be mistyped into a different valid-looking string.
const ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789";

/** A one-time password to hand a new editor. ~5 bits/char × 20 = ~100 bits. */
export function generatePassword(length = 20): string {
  const bytes = randomBytes(length);
  let out = "";
  for (let i = 0; i < length; i++) {
    out += ALPHABET[bytes[i] % ALPHABET.length];
    if (i % 5 === 4 && i !== length - 1) out += "-";
  }
  return out;
}
