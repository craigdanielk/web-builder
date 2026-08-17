// Scheme allowlist for CMS-sourced hrefs.
//
// Content in `cms_blocks` is editable, so any href resolved from a block could
// carry a `javascript:` or `data:` URI — a stored-XSS vector once rendered into
// an <a href>. Every CMS-sourced href MUST pass through this before hitting the
// DOM. Allows same-document relative/hash/query targets and the http(s)/mailto/
// tel schemes; anything else falls back to a safe default.
export function safeHref(href: string | undefined, fallback = "/"): string {
  if (!href) return fallback;
  const v = href.trim();
  // same-document relative targets: "/path", "#anchor", "?query"
  // ("/" not followed by "/" — excludes protocol-relative "//host")
  if (/^(#|\?|\/(?!\/))/.test(v)) return v;
  try {
    const protocol = new URL(v, "https://placeholder.invalid/").protocol;
    if (["http:", "https:", "mailto:", "tel:"].includes(protocol)) return v;
  } catch {
    return fallback;
  }
  return fallback;
}
