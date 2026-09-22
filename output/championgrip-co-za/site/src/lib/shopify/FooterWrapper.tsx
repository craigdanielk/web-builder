import { shopifyFetch } from "./client";
import { SHOP_MENU, SHOP_INFO } from "./queries";
import type { ShopMenuResult, ShopInfoResult } from "./queries";
import type { Menu } from "./types";
import Footer from "@/components/layout/Footer";

/**
 * Rewrite absolute Shopify store URLs to relative paths for the headless frontend.
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

export default async function FooterWrapper() {
  let menu: Menu | undefined;
  let shopName: string | undefined;

  try {
    const [menuData, infoData] = await Promise.all([
      shopifyFetch<ShopMenuResult>(SHOP_MENU, { handle: "footer" }),
      shopifyFetch<ShopInfoResult>(SHOP_INFO),
    ]);
    const rawMenu = menuData?.menu ?? undefined;
    shopName = infoData?.shop?.name || undefined;
    const storeDomain = process.env.SHOPIFY_STORE_DOMAIN || "";
    if (rawMenu && storeDomain) {
      menu = rewriteMenuUrls(rawMenu, storeDomain);
    } else {
      menu = rawMenu;
    }
  } catch {
    // Fall back to defaults — Footer renders with no props
  }

  return <Footer menu={menu} shopName={shopName} />;
}
