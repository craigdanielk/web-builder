// TODO: Layer 7 — Connect to Shopify Storefront API

export function generateStaticParams() {
  return [];
}

export default function Page({ params }: { params: { handle: string } }) {
  return (
    <main className="min-h-screen">
      <p>Placeholder — data connection in Layer 7</p>
    </main>
  );
}
