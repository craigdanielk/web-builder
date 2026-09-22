import { shopifyFetch } from "@/lib/shopify/client";
import { COLLECTIONS_LIST } from "@/lib/shopify/queries";
import type { CollectionsListResult } from "@/lib/shopify/queries";
import Link from "next/link";
import Image from "next/image";

export const metadata = {
  title: "Collections",
  description: "Browse all collections",
};

export default async function CollectionsPage() {
  let collections: Array<{ handle: string; title: string; description: string; image?: { url: string; altText: string | null } | null }> = [];
  try {
    const data = await shopifyFetch<CollectionsListResult>(COLLECTIONS_LIST, { first: 50 });
    const edges = data?.collections?.edges;
    collections = Array.isArray(edges) ? edges.map((e) => ({ handle: e.node.handle, title: e.node.title, description: e.node.description ?? "", image: e.node.image })) : [];
  } catch {
    collections = [];
  }
  return (
    <main className="min-h-screen pt-24 px-6 pb-12">
      <h1 className="text-3xl font-semibold text-neutral-900 mb-8">Collections</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {collections.map((c) => (
          <Link key={c.handle} href={`/collections/${c.handle}`} className="group block">
            <div className="aspect-[4/3] bg-neutral-100 rounded-lg overflow-hidden mb-3">
              {c.image?.url && (
                <Image src={c.image.url} alt={c.image.altText ?? c.title} width={600} height={450} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              )}
            </div>
            <h2 className="text-lg font-medium text-neutral-900 group-hover:underline">{c.title}</h2>
            {c.description && <p className="text-sm text-neutral-600 mt-1 line-clamp-2">{c.description}</p>}
          </Link>
        ))}
      </div>
      {collections.length === 0 && <p className="text-neutral-500">No collections found.</p>}
    </main>
  );
}
