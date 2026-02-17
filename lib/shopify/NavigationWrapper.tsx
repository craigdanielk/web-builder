import { shopifyFetch } from "./client";
import { SHOP_MENU, SHOP_INFO } from "./queries";
import type { ShopMenuResult, ShopInfoResult } from "./queries";
import type { Image, Menu } from "./types";
import Navigation from "@/components/layout/Navigation";

export default async function NavigationWrapper() {
  let menu: Menu | undefined;
  let shopName: string | undefined;
  let logo: Image | undefined;

  try {
    const [menuData, infoData] = await Promise.all([
      shopifyFetch<ShopMenuResult>(SHOP_MENU, { handle: "main-menu" }),
      shopifyFetch<ShopInfoResult>(SHOP_INFO),
    ]);
    menu = menuData?.menu ?? undefined;
    shopName = infoData?.shop?.name || undefined;
    logo = infoData?.shop?.brand?.logo?.image ?? undefined;
  } catch {
    // Fall back to defaults — Navigation renders with no props
  }

  return <Navigation menu={menu} logo={logo} shopName={shopName} />;
}
