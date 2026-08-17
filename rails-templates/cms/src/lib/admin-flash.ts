// The one-shot message passed from an /admin/editors action to the page that
// renders next (task X-0100).
//
// It lives here rather than in `editors/actions.ts` because a "use server" file
// may export only async functions — a constant exported alongside the actions
// fails the build outright.
//
// Carried in a short-lived, non-httpOnly cookie rather than a query parameter:
// a one-time password in the URL lands in browser history, the referer header,
// and any screenshot of the address bar. Non-httpOnly so the page's client
// component can delete it the moment it has been displayed.

export const FLASH_COOKIE = "{{COOKIE_PREFIX}}_admin_flash";
export const FLASH_TTL_SECONDS = 120;
export const FLASH_PATH = "/admin/editors";

export type Flash = {
  kind: "password" | "error" | "ok";
  email?: string;
  password?: string;
  message?: string;
};

export function parseFlash(raw: string | undefined): Flash | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Flash;
    return parsed && typeof parsed.kind === "string" ? parsed : null;
  } catch {
    return null;
  }
}
