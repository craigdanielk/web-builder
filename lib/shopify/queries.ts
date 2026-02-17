/**
 * Shopify Storefront API queries — Layer 7.
 */

import type { Collection, Product, Menu, Image } from "./types";

export const COLLECTION_PRODUCTS = `#graphql
  query CollectionProducts($handle: String!, $first: Int!) {
    collection(handle: $handle) {
      title
      description
      image { url altText }
      seo { title description }
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
      seo { title description }
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

export const SHOP_MENU = `#graphql
  query ShopMenu($handle: String!) {
    menu(handle: $handle) {
      title
      items {
        title
        url
        items {
          title
          url
        }
      }
    }
  }
`;

export const SHOP_INFO = `#graphql
  query ShopInfo {
    shop {
      name
      description
      brand {
        logo {
          image {
            url
            altText
            width
            height
          }
        }
      }
    }
  }
`;

export const COLLECTION_BY_HANDLE = `#graphql
  query CollectionByHandle($handle: String!, $first: Int!) {
    collection(handle: $handle) {
      title
      products(first: $first) {
        edges {
          node {
            id
            title
            handle
            priceRange { minVariantPrice { amount currencyCode } }
            images(first: 1) { edges { node { url altText width height } } }
          }
        }
      }
    }
  }
`;

export const FEATURED_PRODUCTS = `#graphql
  query FeaturedProducts($first: Int!) {
    products(first: $first, sortKey: BEST_SELLING) {
      edges {
        node {
          id
          title
          handle
          priceRange { minVariantPrice { amount currencyCode } }
          images(first: 1) { edges { node { url altText width height } } }
        }
      }
    }
  }
`;

export const SHOP_PAGE = `#graphql
  query ShopPage($handle: String!) {
    page(handle: $handle) {
      title
      body
      bodySummary
      seo { title description }
    }
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

export interface ShopMenuResult {
  menu: Menu | null;
}

export interface ShopInfoResult {
  shop: {
    name: string;
    description: string;
    brand?: {
      logo?: {
        image?: Image | null;
      } | null;
    } | null;
  };
}

export interface CollectionByHandleResult {
  collection: {
    title: string;
    products: {
      edges: Array<{
        node: {
          id: string;
          title: string;
          handle: string;
          priceRange: { minVariantPrice: { amount: string; currencyCode: string } };
          images: { edges: Array<{ node: { url: string; altText: string | null; width?: number; height?: number } }> };
        };
      }>;
    };
  } | null;
}

export interface FeaturedProductsResult {
  products: {
    edges: Array<{
      node: {
        id: string;
        title: string;
        handle: string;
        priceRange: { minVariantPrice: { amount: string; currencyCode: string } };
        images: { edges: Array<{ node: { url: string; altText: string | null; width?: number; height?: number } }> };
      };
    }>;
  };
}

export interface ShopPageResult {
  page: {
    title: string;
    body: string;
    bodySummary: string;
    seo?: { title?: string; description?: string } | null;
  } | null;
}
