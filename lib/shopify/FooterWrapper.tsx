import { shopifyFetch } from "./client";
import { SHOP_MENU, SHOP_INFO } from "./queries";
import type { ShopMenuResult, ShopInfoResult } from "./queries";
import type { Menu } from "./types";
import Footer from "@/components/layout/Footer";

export default async function FooterWrapper() {
  let menu: Menu | undefined;
  let shopName: string | undefined;

  try {
    const [menuData, infoData] = await Promise.all([
      shopifyFetch<ShopMenuResult>(SHOP_MENU, { handle: "footer" }),
      shopifyFetch<ShopInfoResult>(SHOP_INFO),
    ]);
    menu = menuData?.menu ?? undefined;
    shopName = infoData?.shop?.name || undefined;
  } catch {
    // Fall back to defaults — Footer renders with no props
  }

  return <Footer menu={menu} shopName={shopName} />;
}
