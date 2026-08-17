"""Nav and footer links, derived from harvested pages only.

`site-spec.json` (produced by the `--from-url` harvest, see
`stage_url_extract` in orchestrate.py) carries the *real* navigation and
footer the source site shipped:

    page["nav"]["links"]  -> [{"label": str, "href": str}, ...]
    page["sections"][i]   -> a FOOTER-archetype section whose
                              content.items[*].ctas carries the real footer
                              link groups: [{"text": str, "href": str}, ...]

Neither of those matches a flat "nav_links"/"footer_links" key on the page
dict — that shape does not exist in the real data (verified against
`~/Developer/GitHub/tenants/cape-crypto/builds/task4-verify/cape-crypto/site-spec.json`).
This module reads the real shape.

Both functions return `[]` when the harvest carries nothing. They must
never fall back to a canned table: shipping "Shop / New Arrivals" on a
licensed FSP's site is the most visible fabrication the system still
produces. An empty nav is a visible gap someone can fix; a plausible fake
nav is a lie that looks finished.

SECURITY: the harvest crawls an arbitrary third-party website. Every
label/href pair below is untrusted input, not merely unreliable content.
This module is the trust boundary: everything downstream (Navigation.tsx,
Footer.tsx template generation in orchestrate.py) assumes the links it
receives from `derive_nav`/`derive_footer` are already safe to serialize
into generated source and render into `<Link href=...>`. Concretely:
  - labels/hrefs containing control characters or newlines are dropped —
    they have no legitimate reason to appear in a nav label and are a
    known vector for smuggling code across naive string interpolation.
  - hrefs are scheme-allowlisted (relative paths, #fragments, http(s),
    mailto) — `javascript:`, `data:`, `vbscript:`, and any other scheme
    are dropped, not rewritten to "#". A crawled `javascript:` href
    rendered into a live `<Link>` is exploitable XSS against real site
    visitors, which is a strictly worse failure than a missing link.
  - callers still MUST serialize with `json.dumps` (never manual quoting)
    when embedding a label/href in generated JS/TSX source — this module
    guarantees the *content* is safe to render, not that any particular
    quoting scheme is correct for it (e.g. a label can legitimately
    contain a `'`, which is exactly why quote-wrapping instead of
    serializing broke on real Cape Crypto copy before this was caught).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

# http/https/mailto plus relative in-app paths ("/...") and same-page
# fragments ("#..."). Everything else — javascript:, data:, vbscript:,
# file:, and any scheme we don't recognise — is rejected outright rather
# than rewritten, per "sourced or absent, never invented/unsafe".
_ALLOWED_SCHEMES = {"http", "https", "mailto"}
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def _is_safe_text(value: str) -> bool:
    """No control characters or newlines/tabs in visible label or href text."""
    return not _CONTROL_CHARS_RE.search(value)


def _is_safe_href(href: str) -> bool:
    if not _is_safe_text(href):
        return False
    if href.startswith("/") or href.startswith("#"):
        return True
    m = _SCHEME_RE.match(href)
    if not m:
        # No scheme and no leading "/" or "#" — e.g. a bare "wealth" or
        # "./wealth". Not dangerous, but also not a shape the harvest is
        # expected to produce; reject rather than guess how to route it.
        return False
    return m.group(1).lower() in _ALLOWED_SCHEMES


def _dedupe(pairs, rejected: list | None = None) -> list[dict]:
    seen: dict[str, dict] = {}
    for label, href in pairs:
        label = (label or "").strip()
        href = (href or "").strip()
        if not label or not href or href == "#":
            continue
        if not _is_safe_text(label):
            if rejected is not None:
                rejected.append({"label": label, "href": href, "reason": "unsafe_label"})
            continue
        if not _is_safe_href(href):
            if rejected is not None:
                rejected.append({"label": label, "href": href, "reason": "unsafe_href_scheme"})
            continue
        if label not in seen:
            seen[label] = {"label": label, "href": href}
    return list(seen.values())


def _nav_pairs(page: dict):
    for link in ((page.get("nav") or {}).get("links")) or []:
        yield link.get("label"), link.get("href")


def _footer_pairs(page: dict):
    for section in page.get("sections") or []:
        if (section.get("archetype") or "").upper() != "FOOTER":
            continue
        for item in (section.get("content") or {}).get("items") or []:
            for cta in item.get("ctas") or []:
                yield cta.get("text"), cta.get("href")


def derive_nav(pages: list, rejected: list | None = None) -> list:
    """Primary navigation, in first-seen order across harvested pages.

    Reads `page["nav"]["links"]`, the shape the real harvest produces.
    Unsafe entries (control characters, disallowed href schemes) are
    dropped, not sanitized-in-place. Pass a list via `rejected` to collect
    what was dropped and why.
    """
    pairs = (pair for page in (pages or []) for pair in _nav_pairs(page))
    return _dedupe(pairs, rejected=rejected)


def localise_hrefs(
    links: list,
    routes: list,
    source_host: str | None = None,
    unmapped: list | None = None,
) -> list:
    """Rewrite harvested absolute hrefs onto built routes. Never invent a route.

    Harvested hrefs point at the SOURCE site, so an untouched nav sends every
    visitor of the new site back to the one it replaces. The mapping is a JOIN,
    not a guess: `routes` is the manifest's list of routes actually built, and a
    harvested path is rewritten only when it equals one of them.

    Rules, in order:
      - relative, `#fragment`, `mailto:`, `tel:`  -> untouched, uncounted
      - absolute on a DIFFERENT host              -> untouched, counted
        (a third-party path that happens to read `/about` is not our `/about`)
      - absolute on the source host, path matches -> rewritten to the route,
        preserving query and fragment
      - absolute on the source host, no match     -> untouched, counted
      - `source_host` unknown                     -> nothing is rewritten; we
        cannot assert any absolute URL is ours

    Matching is exact after stripping one trailing slash. A deeper path is never
    collapsed onto a shorter route: `/wealth/deep` does not become `/wealth`,
    because that would fabricate a destination the manifest never built.

    `unmapped` collects `{label, href, reason}` so the gap is reported rather
    than absorbed. Input links are not mutated.
    """
    known = {_normalise_route(r) for r in (routes or []) if r}
    host = _bare_host(source_host)
    out: list[dict] = []

    for link in links or []:
        href = (link.get("href") or "").strip()
        new = href
        reason = None

        if href and not _SCHEME_RE.match(href) and not href.startswith("#"):
            pass  # relative path — already local
        elif href.startswith("#"):
            pass  # in-page anchor
        elif href.lower().startswith(("mailto:", "tel:")):
            pass  # not a navigation target within the site
        else:
            parsed = urlparse(href)
            if parsed.scheme in ("http", "https"):
                link_host = _bare_host(parsed.netloc)
                if not host or link_host != host:
                    reason = "external_host" if host else "unknown_source_host"
                else:
                    path = _normalise_route(parsed.path or "/")
                    if path in known:
                        new = path
                        if parsed.query:
                            new += f"?{parsed.query}"
                        if parsed.fragment:
                            new += f"#{parsed.fragment}"
                    else:
                        reason = "no_matching_route"

        if reason is not None and unmapped is not None:
            unmapped.append({"label": link.get("label"), "href": href,
                             "reason": reason})
        out.append({**link, "href": new})

    return out


def source_host_from_pages(pages: list) -> str | None:
    """The single host this harvest came from, read off the pages themselves.

    `localise_hrefs` rewrites nothing when it cannot assert which host is ours,
    and that refusal is correct — but the caller has to be able to ANSWER. A
    `--from-url` build answers from `site_spec["source_url"]` or the flag it was
    given. A `--captures` build has neither: `build-site-spec.js` builds from
    capture records with no extraction data, so the spec's top-level
    `source_url` is the empty string. Every page nonetheless carries the real
    URL its capture record came from, so the host is SOURCED here, not guessed.

    Returns the one bare host every page agrees on, or `None`. Disagreement is
    not resolved by majority: a bundle spanning two hosts has no single source
    site, and picking one would rewrite a third party's links onto our routes.
    `www.` and port differences are not disagreement (see `_bare_host`).
    """
    hosts = {h for h in (_bare_host(p.get("source_url")) for p in (pages or [])) if h}
    return hosts.pop() if len(hosts) == 1 else None


def _bare_host(value: str | None) -> str | None:
    """Host without `www.` or port. `www.x.com` and `x.com` are one site."""
    if not value:
        return None
    host = value.strip().lower()
    if "//" in host:
        host = urlparse(host).netloc or host
    host = host.split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _normalise_route(route: str) -> str:
    """`/about/` and `/about` are the same route; `/` stays `/`."""
    route = (route or "").strip()
    if len(route) > 1 and route.endswith("/"):
        route = route[:-1]
    return route or "/"


def derive_footer(pages: list, rejected: list | None = None) -> list:
    """Footer links, read from harvested FOOTER-archetype sections.

    Falls back to the harvested route list (still sourced — page titles and
    routes from the manifest) when no page carries a FOOTER section. Never
    falls back to a hardcoded table. Same unsafe-entry handling as
    `derive_nav`.
    """
    pairs = (pair for page in (pages or []) for pair in _footer_pairs(page))
    links = _dedupe(pairs, rejected=rejected)
    if links:
        return links
    return [
        {"label": p.get("title") or p["route"], "href": p["route"]}
        for p in (pages or [])
        if p.get("route") and p["route"] != "/"
    ]
