"use client";

/**
 * Cart context provider — Layer 8.
 * Wraps the app with cart state; exposes useCart() hook.
 * Persists cart ID in localStorage via cart.ts helpers.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { Cart } from "./types";
import {
  getCart as fetchCart,
  addToCart as apiAddToCart,
  updateCartLine as apiUpdateCartLine,
  removeFromCart as apiRemoveFromCart,
  getCheckoutUrl,
} from "./cart";

interface CartContextValue {
  cart: Cart | null;
  isOpen: boolean;
  isLoading: boolean;
  addToCart: (variantId: string, quantity?: number) => Promise<void>;
  updateQuantity: (lineId: string, quantity: number) => Promise<void>;
  removeItem: (lineId: string) => Promise<void>;
  openCart: () => void;
  closeCart: () => void;
}

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Hydrate cart from localStorage on mount
  useEffect(() => {
    let cancelled = false;
    fetchCart().then((c) => {
      if (!cancelled) setCart(c);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const addToCart = useCallback(async (variantId: string, quantity: number = 1) => {
    setIsLoading(true);
    try {
      const updated = await apiAddToCart(variantId, quantity);
      setCart(updated);
      setIsOpen(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateQuantity = useCallback(async (lineId: string, quantity: number) => {
    setIsLoading(true);
    try {
      if (quantity < 1) {
        const updated = await apiRemoveFromCart(lineId);
        setCart(updated);
      } else {
        const updated = await apiUpdateCartLine(lineId, quantity);
        setCart(updated);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const removeItem = useCallback(async (lineId: string) => {
    setIsLoading(true);
    try {
      const updated = await apiRemoveFromCart(lineId);
      setCart(updated);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const openCart = useCallback(() => setIsOpen(true), []);
  const closeCart = useCallback(() => setIsOpen(false), []);

  const value = useMemo<CartContextValue>(
    () => ({
      cart,
      isOpen,
      isLoading,
      addToCart,
      updateQuantity,
      removeItem,
      openCart,
      closeCart,
    }),
    [cart, isOpen, isLoading, addToCart, updateQuantity, removeItem, openCart, closeCart]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) {
    throw new Error("useCart must be used within a <CartProvider>");
  }
  return ctx;
}
