/**
 * Shopify helpers — Layer 7.
 */

import type { Money } from "./types";

export function formatPrice(money: Money): string {
  const amount = parseFloat(money.amount);
  const code = money.currencyCode || "USD";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: code,
  }).format(amount);
}

export function getImageUrl(url: string, width?: number, height?: number): string {
  if (!url) return "";
  const u = new URL(url);
  if (width) u.searchParams.set("width", String(width));
  if (height) u.searchParams.set("height", String(height));
  return u.toString();
}
