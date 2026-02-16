/**
 * Aurelix lib/shopify — Layer 7 (data) + Layer 8 (cart).
 * Copy this folder into output/{project}/site/src/lib/shopify when deploying with commerce.
 */

export { shopifyFetch } from "./client";
export { getCdnUrlMap, getSectionMediaUrl, getBrandAssetPath } from "./cdn-config";
export type { CdnUrlMap } from "./cdn-config";
export {
  COLLECTION_PRODUCTS,
  PRODUCT_BY_HANDLE,
  SHOP_NAME,
} from "./queries";
export type { CollectionProductsResult, ProductByHandleResult, ShopNameResult } from "./queries";
export {
  CART_CREATE,
  CART_GET,
  CART_LINES_ADD,
  CART_LINES_UPDATE,
  CART_LINES_REMOVE,
} from "./mutations";
export {
  createCart,
  getCart,
  getOrCreateCart,
  addToCart,
  updateCartLine,
  removeFromCart,
  getCheckoutUrl,
  getCartIdFromCookie,
  setCartIdCookie,
} from "./cart";
export { formatPrice, getImageUrl } from "./utils";
export type { Money, Image, Product, ProductVariant, Collection, Cart, CartLine } from "./types";
