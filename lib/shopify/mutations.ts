/**
 * Shopify Storefront API mutations — Layer 7 & 8 (cart).
 */

import type { Cart } from "./types";

export const CART_CREATE = `#graphql
  mutation CartCreate($input: CartInput!) {
    cartCreate(input: $input) {
      cart {
        id
        checkoutUrl
        lines(first: 50) {
          edges {
            node {
              id
              quantity
              merchandise {
                ... on ProductVariant {
                  id
                  title
                  product { title handle }
                  image { url }
                  price { amount currencyCode }
                }
              }
              cost { totalAmount { amount currencyCode } }
            }
          }
        }
        cost { totalAmount { amount currencyCode } }
      }
    }
  }
`;

export const CART_GET = `#graphql
  query CartGet($cartId: ID!) {
    cart(id: $cartId) {
      id
      checkoutUrl
      totalQuantity
      lines(first: 50) {
        edges {
          node {
            id
            quantity
            merchandise {
              ... on ProductVariant {
                id
                title
                product { title handle }
                image { url }
                price { amount currencyCode }
              }
            }
            cost { totalAmount { amount currencyCode } }
          }
        }
      }
      cost { totalAmount { amount currencyCode } }
    }
  }
`;

export const CART_LINES_ADD = `#graphql
  mutation CartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
    cartLinesAdd(cartId: $cartId, lines: $lines) {
      cart {
        id
        checkoutUrl
        lines(first: 50) { edges { node { id quantity merchandise { ... on ProductVariant { id } } } } }
        cost { totalAmount { amount currencyCode } }
      }
    }
  }
`;

export const CART_LINES_UPDATE = `#graphql
  mutation CartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
    cartLinesUpdate(cartId: $cartId, lines: $lines) {
      cart {
        id
        lines(first: 50) { edges { node { id quantity } } }
        cost { totalAmount { amount currencyCode } }
      }
    }
  }
`;

export const CART_LINES_REMOVE = `#graphql
  mutation CartLinesRemove($cartId: ID!, $lineIds: [ID!]!) {
    cartLinesRemove(cartId: $cartId, lineIds: $lineIds) {
      cart {
        id
        checkoutUrl
        lines(first: 50) { edges { node { id } } }
        cost { totalAmount { amount currencyCode } }
      }
    }
  }
`;

export interface CartCreateResult {
  cartCreate: { cart: Cart | null };
}

export interface CartGetResult {
  cart: Cart | null;
}
