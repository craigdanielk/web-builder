"use client";

/**
 * Cart drawer — Layer 8.
 * Slide-out panel from the right: line items, quantity controls, subtotal, checkout.
 * Reads state from CartProvider via useCart().
 */

import React from "react";
import { useCart } from "./cart-context";
import { formatPrice } from "./utils";
import { getCheckoutUrl } from "./cart";
import type { CartLine } from "./types";

export function CartDrawer() {
  const { cart, isOpen, isLoading, updateQuantity, removeItem, closeCart } = useCart();

  if (!isOpen) return null;

  const lines = cart?.lines?.edges ?? [];
  const isEmpty = lines.length === 0;

  const handleCheckout = () => {
    const url = getCheckoutUrl(cart);
    if (url) window.location.href = url;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-label="Shopping cart"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={closeCart} />

      {/* Drawer panel */}
      <div className="relative w-full max-w-md bg-white shadow-xl flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">
            Cart{cart?.totalQuantity ? ` (${cart.totalQuantity})` : ""}
          </h2>
          <button
            type="button"
            onClick={closeCart}
            className="p-2 rounded hover:bg-gray-100 transition-colors"
            aria-label="Close cart"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Line items */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading && isEmpty ? (
            <p className="text-gray-500 text-center py-8">Loading...</p>
          ) : isEmpty ? (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-2">Your cart is empty.</p>
              <button
                type="button"
                onClick={closeCart}
                className="text-sm text-black underline hover:no-underline"
              >
                Continue shopping
              </button>
            </div>
          ) : (
            <ul className="space-y-4">
              {lines.map(({ node: line }) => (
                <CartLineItem
                  key={line.id}
                  line={line}
                  onUpdateQty={(q) => updateQuantity(line.id, q)}
                  onRemove={() => removeItem(line.id)}
                />
              ))}
            </ul>
          )}
        </div>

        {/* Footer: subtotal + checkout */}
        {!isEmpty && cart && (
          <div className="p-4 border-t space-y-3">
            <div className="flex justify-between text-lg font-semibold">
              <span>Subtotal</span>
              <span>{formatPrice(cart.cost.totalAmount)}</span>
            </div>
            <p className="text-xs text-gray-500">
              Shipping and taxes calculated at checkout.
            </p>
            <button
              type="button"
              onClick={handleCheckout}
              disabled={isLoading}
              className="w-full py-3 px-4 bg-black text-white rounded font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {isLoading ? "Updating..." : "Checkout"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- Cart line item ---------- */

function CartLineItem({
  line,
  onUpdateQty,
  onRemove,
}: {
  line: CartLine;
  onUpdateQty: (q: number) => void;
  onRemove: () => void;
}) {
  const qty = line.quantity;
  const merch = line.merchandise;
  const title =
    merch && "product" in merch
      ? (merch as { product?: { title?: string } }).product?.title ?? "Item"
      : "Item";
  const variantTitle = merch?.title && merch.title !== "Default Title" ? merch.title : null;
  const price =
    line.cost?.totalAmount ??
    (merch as { price?: { amount: string; currencyCode: string } }).price ??
    { amount: "0", currencyCode: "USD" };

  return (
    <li className="flex gap-3 border-b pb-3 last:border-b-0">
      {merch?.image?.url && (
        <img
          src={merch.image.url}
          alt={merch.image.altText ?? title}
          className="w-16 h-16 object-cover rounded flex-shrink-0"
        />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{title}</p>
        {variantTitle && (
          <p className="text-xs text-gray-500">{variantTitle}</p>
        )}
        <p className="text-sm text-gray-600">{formatPrice(price)}</p>
        <div className="flex items-center gap-2 mt-1">
          <button
            type="button"
            onClick={() => onUpdateQty(qty - 1)}
            className="w-7 h-7 rounded border text-sm hover:bg-gray-50 transition-colors"
            aria-label="Decrease quantity"
          >
            -
          </button>
          <span className="w-6 text-center text-sm">{qty}</span>
          <button
            type="button"
            onClick={() => onUpdateQty(qty + 1)}
            className="w-7 h-7 rounded border text-sm hover:bg-gray-50 transition-colors"
            aria-label="Increase quantity"
          >
            +
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="text-sm text-red-600 hover:underline ml-2"
          >
            Remove
          </button>
        </div>
      </div>
    </li>
  );
}
