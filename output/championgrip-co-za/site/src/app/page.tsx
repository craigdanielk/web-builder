import { shopifyFetch } from "@/lib/shopify/client";
import { PRODUCT_BY_HANDLE } from "@/lib/shopify/queries";
import type { ProductByHandleResult } from "@/lib/shopify/queries";
import { HomeExperience } from "@/components/champion/HomeExperience";
import { media, product as catalog, shop } from "@/lib/site";

const HANDLE = "champion-grip-spray-120ml-can-elevate-your-bowling-game-with-confidence";

export const metadata = {
  title: `Champion Grip — ${shop.slogan}`,
  description: "The world's first aerosol bowls grip enhancer. 120ml. R85. The Choice of Champions.",
};

export default async function Page() {
  const data = await shopifyFetch<ProductByHandleResult>(PRODUCT_BY_HANDLE, { handle: HANDLE });
  const product = data?.product;
  if (!product) {
    return (
      <main className="min-h-screen p-8">
        <p>Product not found.</p>
      </main>
    );
  }
  const price = product.priceRange?.minVariantPrice;
  const amount = price?.amount ? Number(price.amount).toFixed(2) : "85.00";
  const currency = price?.currencyCode ?? "ZAR";
  return (
    <HomeExperience
      product={{
        title: product.title,
        handle: product.handle,
        imageUrl: media.packshotHero || media.packshot || product.featuredImage?.url || catalog.image,
        imageAlt: product.featuredImage?.altText ?? product.title,
        priceLabel: `${currency} ${amount}`,
        variantId: product.variants?.edges?.[0]?.node?.id ?? "",
      }}
    />
  );
}
