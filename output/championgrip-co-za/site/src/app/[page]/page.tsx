import { shopifyFetch } from "@/lib/shopify/client";
import { SHOP_PAGE } from "@/lib/shopify/queries";
import type { ShopPageResult } from "@/lib/shopify/queries";
import { notFound } from "next/navigation";

export async function generateMetadata({ params }: { params: Promise<{ page: string }> }) {
  const { page: handle } = await params;
  try {
    const data = await shopifyFetch<ShopPageResult>(SHOP_PAGE, { handle });
    const p = data?.page;
    if (!p) return { title: "Page Not Found" };
    return {
      title: p.seo?.title || p.title,
      description: p.seo?.description || p.bodySummary || "",
    };
  } catch {
    return { title: "Page" };
  }
}

export default async function Page({ params }: { params: Promise<{ page: string }> }) {
  const { page: handle } = await params;
  let pageData: ShopPageResult["page"] = null;
  try {
    const data = await shopifyFetch<ShopPageResult>(SHOP_PAGE, { handle });
    pageData = data?.page ?? null;
  } catch {
    notFound();
  }
  if (!pageData) {
    notFound();
  }
  /* page.body: trusted HTML content from Shopify Storefront API, authored by store owner */
  return (
    <main className="min-h-screen pt-24 px-6 pb-12 max-w-3xl mx-auto">
      <h1 className="text-3xl font-semibold text-neutral-900 mb-6">{pageData.title}</h1>
      <div
        className="prose max-w-none"
        dangerouslySetInnerHTML={{ __html: pageData.body }}
      />
    </main>
  );
}
