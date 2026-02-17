import { shopifyFetch } from "./client";
import { SHOP_MENU, SHOP_INFO } from "./queries";
import type { ShopMenuResult, ShopInfoResult } from "./queries";
import type { Image, Menu } from "./types";
import Navigation from "@/components/layout/Navigation";

/**
 * Rewrite absolute Shopify store URLs to relative paths for the headless frontend.
 * e.g. "https://store.myshopify.com/collections/all" → "/collections/all"
 */
function rewriteMenuUrls(menu: Menu, storeDomain: string): Menu {
  const domainPatterns = [
    `https://${storeDomain}`,
    `http://${storeDomain}`,
    `https://www.${storeDomain}`,
  ];
  function rewriteUrl(url: string): string {
    for (const prefix of domainPatterns) {
      if (url.startsWith(prefix)) {
        const path = url.slice(prefix.length);
        return path || "/";
      }
    }
    // Also handle *.myshopify.com URLs when storeDomain doesn't match exactly
    const match = url.match(/^https?:\/\/[^/]*\.myshopify\.com(\/.*)?$/);
    if (match) return match[1] || "/";
    return url;
  }
  return {
    ...menu,
    items: menu.items.map((item) => ({
      ...item,
      url: rewriteUrl(item.url),
      items: item.items?.map((sub) => ({ ...sub, url: rewriteUrl(sub.url) })),
    })),
  };
}

export default async function NavigationWrapper() {
  let menu: Menu | undefined;
  let shopName: string | undefined;
  let logo: Image | undefined;

  try {
    const [menuData, infoData] = await Promise.all([
      shopifyFetch<ShopMenuResult>(SHOP_MENU, { handle: "main-menu" }),
      shopifyFetch<ShopInfoResult>(SHOP_INFO),
    ]);
    const rawMenu = menuData?.menu ?? undefined;
    shopName = infoData?.shop?.name || undefined;
    logo = infoData?.shop?.brand?.logo?.image ?? undefined;
    // Rewrite absolute Shopify URLs to relative paths
    const storeDomain = process.env.SHOPIFY_STORE_DOMAIN || "";
    if (rawMenu && storeDomain) {
      menu = rewriteMenuUrls(rawMenu, storeDomain);
    } else {
      menu = rawMenu;
    }
  } catch {
    // Fall back to defaults — Navigation renders with no props
  }

  return <Navigation menu={menu} logo={logo} shopName={shopName} />;
}
