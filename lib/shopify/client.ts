/**
 * Shopify Storefront API client — Layer 7.
 * Initialize with env: SHOPIFY_STORE_DOMAIN, SHOPIFY_STOREFRONT_ACCESS_TOKEN.
 */

function storefrontDomain(): string | undefined {
  return process.env.NEXT_PUBLIC_SHOPIFY_STORE_DOMAIN || process.env.SHOPIFY_STORE_DOMAIN;
}

function storefrontToken(): string | undefined {
  return (
    process.env.NEXT_PUBLIC_SHOPIFY_STOREFRONT_ACCESS_TOKEN ||
    process.env.SHOPIFY_STOREFRONT_ACCESS_TOKEN
  );
}

const endpoint = (): string => {
  const domain = storefrontDomain();
  const token = storefrontToken();
  if (!domain || !token) {
    throw new Error("Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_STOREFRONT_ACCESS_TOKEN");
  }
  return `https://${domain}/api/2024-01/graphql.json`;
};

export async function shopifyFetch<T = unknown>(
  query: string,
  variables?: Record<string, unknown>
): Promise<T> {
  const token = storefrontToken();
  const res = await fetch(endpoint(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Shopify-Storefront-Access-Token": token!,
    },
    body: JSON.stringify({ query, variables }),
    next: { revalidate: 60 },
  });
  if (!res.ok) {
    throw new Error(`Shopify API error: ${res.status} ${res.statusText}`);
  }
  const json = await res.json();
  if (json.errors?.length) {
    throw new Error(json.errors.map((e: { message: string }) => e.message).join("; "));
  }
  return json.data as T;
}
