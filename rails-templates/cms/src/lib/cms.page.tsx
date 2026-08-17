import { getPageBlocks } from "@/lib/cms";
import { PAGES } from "@/lib/cms.registry";

// Shared CMS page renderer used by every content-driven route.
// Renders the tenant's published blocks for `slug` (ordered by position),
// falling back to the page's canonical section order when the store is
// unreachable or unseeded — so a route never renders blank.
/**
 * The anchor id for a section, derived from its `section_key`.
 *
 *   "04-how_it_works" -> "how-it-works"
 *   "04b-why_choose"  -> "why-choose"
 *   "09-cta_strip"    -> "cta-strip"
 *
 * Derived rather than stored because an id kept in `content` is a second copy of
 * the section's identity, and the two drift. Before this, NOTHING on any page
 * emitted an id, so every "#anchor" in the CMS pointed at something that could
 * not exist — measured 2026-07-31 on /kyc and /pricing.
 *
 * The numeric prefix is ordering metadata, not identity, so it is stripped: the
 * anchor must survive a section being reordered from 04 to 05.
 */
export function sectionAnchorId(sectionKey: string): string {
  return sectionKey.replace(/^\d+[a-z]?-/, "").replace(/_/g, "-");
}

export async function CmsPage({ slug }: { slug: string }) {
  const page = PAGES[slug];
  if (!page) return null;

  const blocks = await getPageBlocks(slug);
  const items = blocks
    ? blocks.map((b, i) => ({
        key: `${b.section_key}-${i}`,
        anchor: page.anchors[b.section_key] ?? sectionAnchorId(b.section_key),
        Comp: page.registry[b.section_key],
        content: b.content as Record<string, unknown> | undefined,
      }))
    : page.order.map((k) => ({
        key: k,
        anchor: page.anchors[k] ?? sectionAnchorId(k),
        Comp: page.registry[k],
        content: undefined as Record<string, unknown> | undefined,
      }));

  // The wrapper carries the id rather than each section component, so an anchor
  // exists for every section without 40 components each having to remember.
  //
  // A plain block wrapper, NOT `display: contents`: an element with
  // `display: contents` generates no box, and fragment navigation to a boxless
  // element is unreliable across browsers — which would defeat the only reason
  // the id is here. `<main>` is normal flow, so a block-level div around a
  // full-width section is layout-neutral.
  //
  // scroll-mt-24 offsets the sticky header, so following an anchor does not
  // land with the section heading hidden underneath the navigation bar.
  return (
    <main className="min-h-screen">
      {items.map(({ key, anchor, Comp, content }) =>
        Comp ? (
          <div key={key} id={anchor} className="scroll-mt-24">
            <Comp content={content} />
          </div>
        ) : null,
      )}
    </main>
  );
}
