/**
 * Shopify Storefront API cart mutations — Layer 8.
 * Uses Storefront API 2024-10 schema.
 * All mutations return a full cart fragment for context state sync.
 */

import type { Cart } from "./types";

const CART_FRAGMENT = `
  fragment CartFields on Cart {
    id
    checkoutUrl
    totalQuantity
    lines(first: 100) {
      edges {
        node {
          id
          quantity
          merchandise {
            ... on ProductVariant {
              id
              title
              product { title handle }
              selectedOptions { name value }
              image { url altText }
              price { amount currencyCode }
            }
          }
          cost { totalAmount { amount currencyCode } }
        }
      }
    }
    cost { totalAmount { amount currencyCode } }
  }
`;

export const CART_CREATE = `#graphql
  ${CART_FRAGMENT}
  mutation CartCreate($input: CartInput!) {
    cartCreate(input: $input) {
      cart { ...CartFields }
    }
  }
`;

export const CART_GET = `#graphql
  ${CART_FRAGMENT}
  query CartGet($cartId: ID!) {
    cart(id: $cartId) { ...CartFields }
  }
`;

export const CART_LINES_ADD = `#graphql
  ${CART_FRAGMENT}
  mutation CartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
    cartLinesAdd(cartId: $cartId, lines: $lines) {
      cart { ...CartFields }
    }
  }
`;

export const CART_LINES_UPDATE = `#graphql
  ${CART_FRAGMENT}
  mutation CartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
    cartLinesUpdate(cartId: $cartId, lines: $lines) {
      cart { ...CartFields }
    }
  }
`;

export const CART_LINES_REMOVE = `#graphql
  ${CART_FRAGMENT}
  mutation CartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
    cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
      cart { ...CartFields }
    }
  }
`;

export interface CartCreateResult {
  cartCreate: { cart: Cart | null };
}

export interface CartGetResult {
  cart: Cart | null;
}

export interface CartLinesAddResult {
  cartLinesAdd: { cart: Cart | null };
}

export interface CartLinesUpdateResult {
  cartLinesUpdate: { cart: Cart | null };
}

export interface CartLinesRemoveResult {
  cartLinesRemove: { cart: Cart | null };
}
