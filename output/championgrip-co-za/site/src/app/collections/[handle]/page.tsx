import { shopifyFetch } from "@/lib/shopify/client";
import { COLLECTION_PRODUCTS } from "@/lib/shopify/queries";
import type { CollectionProductsResult } from "@/lib/shopify/queries";
import Link from "next/link";
import Image from "next/image";

export function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  try {
    const data = await shopifyFetch<CollectionProductsResult>(COLLECTION_PRODUCTS, { handle, first: 1 });
    const c = data?.collection;
    return {
      title: c?.seo?.title || c?.title || "Collection",
      description: c?.seo?.description || c?.description || "",
    };
  } catch {
    return { title: "Collection" };
  }
}

export default async function Page({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const data = await shopifyFetch<CollectionProductsResult>(COLLECTION_PRODUCTS, {
    handle,
    first: 24,
  });
  const collection = data?.collection;
  if (!collection) {
    return (
      <main className="min-h-screen p-8">
        <p>Collection not found.</p>
      </main>
    );
  }
  const products = collection.products?.edges ?? [];
  return (
    <main className="min-h-screen pt-24 px-6 pb-12">
      <h1 className="text-3xl font-semibold text-neutral-900 mb-2">{collection.title}</h1>
      {collection.description && (
        <p className="text-neutral-600 mb-8 max-w-2xl">{collection.description}</p>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map(({ node: p }) => (
          <Link key={p.handle} href={`/products/${p.handle}`} className="group">
            <div className="aspect-square bg-neutral-100 rounded-lg overflow-hidden mb-2">
              {p.featuredImage?.url && (
                <Image src={p.featuredImage.url} alt={p.featuredImage.altText ?? p.title} width={400} height={400} className="w-full h-full object-cover" />
              )}
            </div>
            <h2 className="font-medium text-neutral-900 group-hover:underline">{p.title}</h2>
            <p className="text-sm text-neutral-600">
              {p.priceRange?.minVariantPrice?.amount} {p.priceRange?.minVariantPrice?.currencyCode}
            </p>
          </Link>
        ))}
      </div>
      {products.length === 0 && <p className="text-neutral-500">No products in this collection yet.</p>}
    </main>
  );
}
