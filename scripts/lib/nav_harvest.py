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
"""
from __future__ import annotations


def _dedupe(pairs) -> list[dict]:
    seen: dict[str, dict] = {}
    for label, href in pairs:
        label = (label or "").strip()
        href = (href or "").strip()
        if not label or not href or href == "#":
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


def derive_nav(pages: list) -> list:
    """Primary navigation, in first-seen order across harvested pages.

    Reads `page["nav"]["links"]`, the shape the real harvest produces.
    """
    pairs = (pair for page in (pages or []) for pair in _nav_pairs(page))
    return _dedupe(pairs)


def derive_footer(pages: list) -> list:
    """Footer links, read from harvested FOOTER-archetype sections.

    Falls back to the harvested route list (still sourced — page titles and
    routes from the manifest) when no page carries a FOOTER section. Never
    falls back to a hardcoded table.
    """
    pairs = (pair for page in (pages or []) for pair in _footer_pairs(page))
    links = _dedupe(pairs)
    if links:
        return links
    return [
        {"label": p.get("title") or p["route"], "href": p["route"]}
        for p in (pages or [])
        if p.get("route") and p["route"] != "/"
    ]
