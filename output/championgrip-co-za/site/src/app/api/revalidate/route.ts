import { revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

export async function POST(req: NextRequest) {
  const secret = process.env.SHOPIFY_REVALIDATION_SECRET;
  const hmac = req.headers.get("x-shopify-hmac-sha256");
  const topic = req.headers.get("x-shopify-topic") || "";

  if (!secret || !hmac) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.text();
  const digest = crypto
    .createHmac("sha256", secret)
    .update(body, "utf8")
    .digest("base64");

  if (digest !== hmac) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }

  // Revalidate cache tags based on Shopify webhook topic
  if (topic.startsWith("products/")) {
    revalidateTag("products");
  }
  if (topic.startsWith("collections/")) {
    revalidateTag("collections");
  }

  return NextResponse.json({ revalidated: true, topic });
}
