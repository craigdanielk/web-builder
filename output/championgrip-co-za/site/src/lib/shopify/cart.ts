/**
 * Cart state and helpers — Layer 8.
 * Store cart ID in localStorage; create/add/update/remove via Storefront API.
 */

import { shopifyFetch } from "./client";
import {
  CART_CREATE,
  CART_GET,
  CART_LINES_ADD,
  CART_LINES_UPDATE,
  CART_LINES_REMOVE,
} from "./mutations";
import type {
  CartCreateResult,
  CartGetResult,
  CartLinesAddResult,
  CartLinesUpdateResult,
  CartLinesRemoveResult,
} from "./mutations";
import type { Cart } from "./types";

const CART_ID_KEY = "shopify_cart_id";

export function getCartId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(CART_ID_KEY);
  } catch {
    return null;
  }
}

export function setCartId(cartId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(CART_ID_KEY, cartId);
  } catch {
    // localStorage unavailable (e.g. incognito quota exceeded)
  }
}

function clearCartId(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(CART_ID_KEY);
  } catch {
    // noop
  }
}

export async function createCart(): Promise<Cart | null> {
  const result = await shopifyFetch<CartCreateResult>(CART_CREATE, { input: {} });
  const cart = result?.cartCreate?.cart ?? null;
  if (cart?.id) setCartId(cart.id);
  return cart;
}

export async function getCart(): Promise<Cart | null> {
  const cartId = getCartId();
  if (!cartId) return null;
  const result = await shopifyFetch<CartGetResult>(CART_GET, { cartId });
  const cart = result?.cart ?? null;
  // If cart no longer exists on Shopify, clear stale ID
  if (!cart) clearCartId();
  return cart;
}

export async function getOrCreateCart(): Promise<Cart | null> {
  const existing = await getCart();
  if (existing) return existing;
  return createCart();
}

export async function addToCart(variantId: string, quantity: number = 1): Promise<Cart | null> {
  const cart = await getOrCreateCart();
  if (!cart) return null;
  const result = await shopifyFetch<CartLinesAddResult>(CART_LINES_ADD, {
    cartId: cart.id,
    lines: [{ merchandiseId: variantId, quantity }],
  });
  return result?.cartLinesAdd?.cart ?? null;
}

export async function updateCartLine(lineId: string, quantity: number): Promise<Cart | null> {
  const cartId = getCartId();
  if (!cartId) return null;
  const result = await shopifyFetch<CartLinesUpdateResult>(CART_LINES_UPDATE, {
    cartId,
    lines: [{ id: lineId, quantity }],
  });
  return result?.cartLinesUpdate?.cart ?? null;
}

export async function removeFromCart(lineId: string): Promise<Cart | null> {
  const cartId = getCartId();
  if (!cartId) return null;
  const result = await shopifyFetch<CartLinesRemoveResult>(CART_LINES_REMOVE, {
    cartId,
    lineIds: [lineId],
  });
  return result?.cartLinesRemove?.cart ?? null;
}

export function getCheckoutUrl(cart: Cart | null): string {
  return cart?.checkoutUrl ?? "";
}
