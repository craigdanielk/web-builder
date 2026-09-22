import { shopifyFetch } from "@/lib/shopify/client";
import { PRODUCT_BY_HANDLE } from "@/lib/shopify/queries";
import type { ProductByHandleResult } from "@/lib/shopify/queries";
import { AddToCartButton } from "@/lib/shopify/AddToCartButton";
import { ProductGallery } from "@/components/champion/ProductGallery";
import { pdpGallery, shop } from "@/lib/site";
import Link from "next/link";

const DISPLAY_TITLE = "Champion Grip Spray.";

export function generateStaticParams() {
  return [];
}

export async function generateMetadata({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  try {
    const data = await shopifyFetch<ProductByHandleResult>(PRODUCT_BY_HANDLE, { handle });
    const p = data?.product;
    return {
      title: p?.seo?.title || `${DISPLAY_TITLE} — ${shop.slogan}`,
      description: p?.seo?.description || p?.description || "",
    };
  } catch {
    return { title: DISPLAY_TITLE };
  }
}

function gallerySlots(
  product: NonNullable<ProductByHandleResult["product"]>
): Array<{ url: string; altText: string | null; width?: number; height?: number }> {
  const fromShopify = (product.images?.edges ?? []).map((e) => e.node).filter((n) => n?.url);
  const merged: Array<{ url: string; altText: string | null; width?: number; height?: number }> = [];
  const seen = new Set<string>();

  for (const item of [...pdpGallery, ...fromShopify]) {
    if (!item?.url || seen.has(item.url)) continue;
    seen.add(item.url);
    merged.push({
      url: item.url,
      altText: ("altText" in item ? item.altText : null) ?? null,
      width: item.width,
      height: item.height,
    });
  }
  return merged.slice(0, 6);
}

export default async function Page({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const data = await shopifyFetch<ProductByHandleResult>(PRODUCT_BY_HANDLE, {
    handle,
  });
  const product = data?.product;
  if (!product) {
    return (
      <main className="min-h-screen p-8">
        <p>Product not found.</p>
      </main>
    );
  }
  const price = product.priceRange?.minVariantPrice;
  const variantId = product.variants?.edges?.[0]?.node?.id ?? "";
  const amount = price?.amount ? Number(price.amount).toFixed(2) : "";
  const summary = product.description?.split(/(?<=\.)\s/).slice(0, 2).join(" ") ?? "";
  const gallery = gallerySlots(product);

  return (
    <main className="cg-pdp">
      <ProductGallery images={gallery} title={DISPLAY_TITLE} />
      <div className="cg-pdp-buy">
        <p className="cg-kicker">120ml spray</p>
        <h1>{DISPLAY_TITLE}</h1>
        <p className="cg-fine">{shop.slogan}</p>
        {price ? <p className="cg-price">{price.currencyCode} {amount}</p> : null}
        {summary ? <p className="cg-lead">{summary}</p> : null}
        <ul className="cg-pdp-points">
          <li>Consistent, accurate deliveries.</li>
          <li>A small amount is enough on each bowl.</li>
          <li>Indoor and outdoor, including carpet.</li>
        </ul>
        {variantId ? (
          <AddToCartButton variantId={variantId} className="cg-buy">
            Add to cart
            <span>{price ? `${price.currencyCode} ${amount}` : "R85"}</span>
          </AddToCartButton>
        ) : null}
        <p className="cg-fine" style={{ marginTop: "1rem" }}>
          <Link href="/">Back to the story</Link>
        </p>
      </div>
      {variantId ? (
        <div className="cg-mobile-buy">
          <strong>{price ? `${price.currencyCode} ${amount}` : "R85"}</strong>
          <AddToCartButton variantId={variantId} className="cg-buy">
            Add to cart
          </AddToCartButton>
        </div>
      ) : null}
    </main>
  );
}
