"use client";

/**
 * Add to Cart button — Layer 8.
 * Accepts a variantId and optional quantity, calls addToCart from cart context.
 * Shows loading state during the mutation.
 */

import React, { useState } from "react";
import { useCart } from "./cart-context";

interface AddToCartButtonProps {
  variantId: string;
  quantity?: number;
  disabled?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function AddToCartButton({
  variantId,
  quantity = 1,
  disabled = false,
  className,
  children,
}: AddToCartButtonProps) {
  const { addToCart } = useCart();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (!variantId || loading || disabled) return;
    setLoading(true);
    try {
      await addToCart(variantId, quantity);
    } catch (err) {
      console.error("Failed to add to cart:", err);
    } finally {
      setLoading(false);
    }
  };

  const defaultClassName =
    "w-full py-3 px-6 bg-black text-white rounded font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity";

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || loading || !variantId}
      className={className ?? defaultClassName}
      aria-label="Add to cart"
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Adding...
        </span>
      ) : (
        children ?? "Add to Cart"
      )}
    </button>
  );
}
