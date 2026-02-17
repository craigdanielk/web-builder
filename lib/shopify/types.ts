/**
 * Shopify Storefront API types — Layer 7.
 * Aligns with commerce-contract.ts and Storefront API 2024-01.
 */

export interface Money {
  amount: string;
  currencyCode: string;
}

export interface Image {
  url: string;
  altText: string | null;
  width?: number;
  height?: number;
}

export interface ProductVariant {
  id: string;
  title: string;
  availableForSale: boolean;
  price: { amount: string; currencyCode: string };
  compareAtPrice?: { amount: string; currencyCode: string };
  selectedOptions: Array<{ name: string; value: string }>;
  image?: Image;
}

export interface Product {
  handle: string;
  title: string;
  description: string;
  descriptionHtml: string;
  priceRange: { minVariantPrice: Money; maxVariantPrice: Money };
  featuredImage?: Image | null;
  images: { edges: Array<{ node: Image }> };
  variants: { edges: Array<{ node: ProductVariant }> };
  tags: string[];
  availableForSale: boolean;
  seo?: { title?: string; description?: string };
}

export interface Collection {
  handle: string;
  title: string;
  description: string;
  image?: Image | null;
  seo?: { title?: string; description?: string };
  products: {
    edges: Array<{ node: Product }>;
    pageInfo?: { hasNextPage: boolean; endCursor: string | null };
  };
}

export interface MenuItem {
  title: string;
  url: string;
  items?: MenuItem[];
}

export interface Menu {
  title: string;
  items: MenuItem[];
}

export interface ShopPage {
  title: string;
  body: string;
  bodySummary: string;
  seo?: { title?: string; description?: string } | null;
}

export interface CartLine {
  id: string;
  quantity: number;
  merchandise: {
    id: string;
    title: string;
    product: Product;
    selectedOptions: Array<{ name: string; value: string }>;
    image?: Image | null;
    price: Money;
  };
  cost: { totalAmount: Money };
}

export interface Cart {
  id: string;
  checkoutUrl: string;
  totalQuantity: number;
  lines: { edges: Array<{ node: CartLine }> };
  cost: { totalAmount: Money };
}
