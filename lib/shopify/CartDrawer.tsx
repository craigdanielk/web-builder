"use client";

/**
 * Cart drawer — Layer 8.
 * Slide-out panel: line items, total, checkout button.
 * Use in layout or nav; wire Add to cart on product pages to addToCart(variantId).
 */

import React, { useEffect, useState } from "react";
import {
  getCart,
  getCheckoutUrl,
  removeFromCart,
  updateCartLine,
  type Cart,
  type CartLine,
  formatPrice,
} from "./index";

export interface CartDrawerProps {
  open: boolean;
  onClose: () => void;
  /** Cart ID override (e.g. from server cookie); if not set, uses client cookie */
  cartId?: string | null;
}

export function CartDrawer({ open, onClose, cartId: _cartId }: CartDrawerProps) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    getCart().then((c) => {
      if (!cancelled) {
        setCart(c);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleUpdateQty = async (lineId: string, quantity: number) => {
    if (quantity < 1) {
      const updated = await removeFromCart(lineId);
      setCart(updated);
      return;
    }
    const updated = await updateCartLine(lineId, quantity);
    setCart(updated);
  };

  const handleRemove = async (lineId: string) => {
    const updated = await removeFromCart(lineId);
    setCart(updated);
  };

  const handleCheckout = () => {
    const url = getCheckoutUrl(cart);
    if (url) window.location.href = url;
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-label="Shopping cart"
    >
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white shadow-xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Cart</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded hover:bg-gray-100"
            aria-label="Close cart"
          >
            ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <p className="text-gray-500">Loading...</p>
          ) : !cart || cart.lines?.edges?.length === 0 ? (
            <p className="text-gray-500">Your cart is empty.</p>
          ) : (
            <ul className="space-y-4">
              {cart.lines.edges.map(({ node: line }) => (
                <CartLineItem
                  key={line.id}
                  line={line}
                  onUpdateQty={(q) => handleUpdateQty(line.id, q)}
                  onRemove={() => handleRemove(line.id)}
                />
              ))}
            </ul>
          )}
        </div>
        {cart && cart.lines.edges.length > 0 && (
          <div className="p-4 border-t space-y-2">
            <div className="flex justify-between text-lg font-semibold">
              <span>Total</span>
              <span>{formatPrice(cart.cost.totalAmount)}</span>
            </div>
            <button
              type="button"
              onClick={handleCheckout}
              className="w-full py-3 px-4 bg-black text-white rounded font-medium hover:opacity-90"
            >
              Checkout
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

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
  const product = merch && "product" in merch ? (merch as { product?: { title?: string } }).product : null;
  const title = product?.title ?? (merch as { title?: string }).title ?? "Item";
  const price = line.cost?.totalAmount ?? (merch as { price?: { amount: string; currencyCode: string } }).price ?? { amount: "0", currencyCode: "USD" };

  return (
    <li className="flex gap-3 border-b pb-3">
      {merch.image?.url && (
        <img
          src={merch.image.url}
          alt=""
          className="w-16 h-16 object-cover rounded"
        />
      )}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{title}</p>
        <p className="text-sm text-gray-600">{formatPrice(price)} × {qty}</p>
        <div className="flex items-center gap-2 mt-1">
          <button
            type="button"
            onClick={() => onUpdateQty(qty - 1)}
            className="w-7 h-7 rounded border text-sm"
          >
            −
          </button>
          <span className="w-6 text-center text-sm">{qty}</span>
          <button
            type="button"
            onClick={() => onUpdateQty(qty + 1)}
            className="w-7 h-7 rounded border text-sm"
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
