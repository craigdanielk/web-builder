/**
 * Shopify Storefront API queries — Layer 7.
 */

import type { Collection, Product } from "./types";

export const COLLECTION_PRODUCTS = `#graphql
  query CollectionProducts($handle: String!, $first: Int!) {
    collection(handle: $handle) {
      title
      description
      image { url altText }
      products(first: $first) {
        edges {
          node {
            handle
            title
            description
            priceRange { minVariantPrice { amount currencyCode } }
            featuredImage { url altText }
            images(first: 4) { edges { node { url altText } } }
            variants(first: 10) {
              edges { node { id title price { amount } availableForSale } }
            }
          }
        }
      }
    }
  }
`;

export const PRODUCT_BY_HANDLE = `#graphql
  query ProductByHandle($handle: String!) {
    product(handle: $handle) {
      handle
      title
      description
      descriptionHtml
      priceRange { minVariantPrice { amount currencyCode } maxVariantPrice { amount currencyCode } }
      featuredImage { url altText width height }
      images(first: 10) { edges { node { url altText width height } } }
      variants(first: 20) {
        edges {
          node {
            id
            title
            price { amount currencyCode }
            availableForSale
            selectedOptions { name value }
            image { url altText }
          }
        }
      }
      tags
    }
  }
`;

export const COLLECTIONS_LIST = `#graphql
  query CollectionsList($first: Int!) {
    collections(first: $first, sortKey: UPDATED_AT, reverse: true) {
      edges {
        node {
          handle
          title
          description
          image { url altText }
        }
      }
    }
  }
`;

export const SHOP_NAME = `#graphql
  query ShopName {
    shop { name }
  }
`;

export interface CollectionsListResult {
  collections: { edges: Array<{ node: { handle: string; title: string; description: string; image?: { url: string; altText: string | null } | null } }> };
}

export interface CollectionProductsResult {
  collection: Collection | null;
}

export interface ProductByHandleResult {
  product: Product | null;
}

export interface ShopNameResult {
  shop: { name: string };
}
