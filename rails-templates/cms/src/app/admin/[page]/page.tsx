import { notFound } from "next/navigation";
import { createClient } from "@supabase/supabase-js";
import type { Data } from "@measured/puck";
import { isEditablePage } from "@/lib/puck/pages";
import { hydrateBlockMedia } from "@/lib/puck/media-hydrate";
import { PAGES } from "@/lib/cms.registry";
import Editor from "./Editor";

export const dynamic = "force-dynamic";

const TENANT_ID = process.env.{{CMS_TENANT_ENV}} ?? "";

// Load the page's blocks (any status), newest position order, as Puck Data.
async function loadData(page: string): Promise<Data> {
  const supabase = createClient(process.env.SUPABASE_URL ?? "", process.env.SUPABASE_SERVICE_ROLE_KEY ?? "", {
    auth: { persistSession: false },
  });
  const { data } = await supabase
    .from("cms_blocks")
    .select("section_key, content, position")
    .eq("tenant_id", TENANT_ID)
    .eq("page_slug", page)
    .order("position", { ascending: true });

  const blocks = data ?? [];
  if (blocks.length === 0) {
    // No rows yet: seed the editor from the page's canonical section order.
    const order = PAGES[page]?.order ?? [];
    return {
      content: order.map((k, i) => ({ type: `${page}__${k}`, props: { id: `${page}__${k}__${i}` } })),
      root: {},
    } as Data;
  }
  // Resolve managed image refs (X-0111) to bucket URLs, exactly as the public
  // render path does in lib/cms.ts. Without this the editor canvas draws a grey
  // placeholder for every image — the sections are client components and cannot
  // resolve an asset id themselves. Gate H-B2 is a human reading the page as an
  // editor sees it, so the preview has to show the real photograph.
  //
  // The resolved `asset` is render-only and MUST NOT round-trip. savePageAction
  // persists an item's props wholesale (it deletes only `id` and `editMode`), so
  // nothing downstream would drop it — Editor.tsx calls stripHydratedAssets()
  // before saving. Hydrate in, strip out; the two are a pair, do not remove one.
  const hydrated = await hydrateBlockMedia(blocks);

  return {
    content: hydrated.map((b, i) => ({
      type: `${page}__${b.section_key}`,
      // Puck requires a unique props.id per item, else items collapse/misrender.
      props: { id: `${page}__${b.section_key}__${i}`, ...((b.content as object) ?? {}) },
    })),
    root: {},
  } as Data;
}

export default async function EditPage({ params }: { params: Promise<{ page: string }> }) {
  const { page } = await params;
  if (!isEditablePage(page)) notFound();
  const data = await loadData(page);
  return <Editor page={page} data={data} />;
}
