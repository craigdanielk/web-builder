/**
 * Cart state and helpers — Layer 8.
 * Store cart ID in cookie; create/add/update/remove via Storefront API.
 */

import { shopifyFetch } from "./client";
import {
  CART_CREATE,
  CART_GET,
  CART_LINES_ADD,
  CART_LINES_UPDATE,
  CART_LINES_REMOVE,
} from "./mutations";
import type { CartCreateResult, CartGetResult } from "./mutations";
import type { Cart } from "./types";

const CART_ID_COOKIE = "shopify_cart_id";

export function getCartIdFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${CART_ID_COOKIE}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function setCartIdCookie(cartId: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `${CART_ID_COOKIE}=${encodeURIComponent(cartId)}; path=/; max-age=604800`;
}

export async function createCart(): Promise<Cart | null> {
  const result = await shopifyFetch<CartCreateResult>(CART_CREATE, { input: {} });
  const cart = result?.cartCreate?.cart ?? null;
  if (cart?.id) setCartIdCookie(cart.id);
  return cart;
}

export async function getCart(): Promise<Cart | null> {
  const cartId = getCartIdFromCookie();
  if (!cartId) return null;
  const result = await shopifyFetch<CartGetResult>(CART_GET, { cartId });
  return result?.cart ?? null;
}

export async function getOrCreateCart(): Promise<Cart | null> {
  const existing = await getCart();
  if (existing) return existing;
  return createCart();
}

export async function addToCart(variantId: string, quantity: number = 1): Promise<Cart | null> {
  const cart = await getOrCreateCart();
  if (!cart) return null;
  const result = await shopifyFetch<{ cartLinesAdd: { cart: Cart | null } }>(CART_LINES_ADD, {
    cartId: cart.id,
    lines: [{ merchandiseId: variantId, quantity }],
  });
  const updated = result?.cartLinesAdd?.cart ?? null;
  return updated;
}

export async function updateCartLine(lineId: string, quantity: number): Promise<Cart | null> {
  const cartId = getCartIdFromCookie();
  if (!cartId) return null;
  const result = await shopifyFetch<{ cartLinesUpdate: { cart: Cart | null } }>(CART_LINES_UPDATE, {
    cartId,
    lines: [{ id: lineId, quantity }],
  });
  return result?.cartLinesUpdate?.cart ?? null;
}

export async function removeFromCart(lineId: string): Promise<Cart | null> {
  const cartId = getCartIdFromCookie();
  if (!cartId) return null;
  const result = await shopifyFetch<{ cartLinesRemove: { cart: Cart | null } }>(CART_LINES_REMOVE, {
    cartId,
    lineIds: [lineId],
  });
  return result?.cartLinesRemove?.cart ?? null;
}

export function getCheckoutUrl(cart: Cart | null): string {
  return cart?.checkoutUrl ?? "";
}
