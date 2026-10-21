# THURIS — Shopify store state (thuris.myshopify.com), written via Shopify MCP 2026-10-21

Base currency **USD** (API cannot change it). Per operator decision, base prices are the
**AED figures** (395 / 445 / 395 / 1,111.50) until the base currency is changed in admin.

## Created
| Product | Product ID | Variant ID | SKU | Price | Inventory |
|---|---|---|---|---|---|
| Frankincense (10 ml) | gid://shopify/Product/15466066182275 | gid://shopify/ProductVariant/67988320387203 | THU-FRA-10-001 | 395.00 | 30, tracked, DENY oversell |
| Neroli (10 ml) | gid://shopify/Product/15466066280579 | gid://shopify/ProductVariant/67988320845955 | THU-NER-10-001 | 445.00 | 30, tracked, DENY oversell |
| Rose Geranium (10 ml) | gid://shopify/Product/15466066346115 | gid://shopify/ProductVariant/67988321009795 | THU-RGE-10-001 | 395.00 | 30, tracked, DENY oversell |
| The complete Founding Collection (Bundle of the three) | gid://shopify/Product/15466066641027 | gid://shopify/ProductVariant/67988321763459 | THU-TRIO-001 | 1111.50 | from components |

All ACTIVE. Descriptions are the approved copy lines. (Superseded 2026-10-21 (e) below — all four are now on Online Store.)

## Refused (not done)
- **Pre-order selling plan** — `sellingPlanGroupCreate` denied: the MCP app lacks the
  `write_purchase_options` scope. Intended plan: "Pre-order — paid in full at checkout"
  (PRE_ORDER, 100% at checkout, fulfilment UNKNOWN, inventory reserved ON_SALE), attached to all four.
- **UAE market in AED** — `marketCreate` error MULTIPLE_CURRENCIES_NOT_SUPPORTED: the store's
  payment gateway supports one currency. Needs Shopify Payments (a handoff launch blocker).
- **Storefront access token** — `storefrontAccessTokenCreate` refused by the MCP safety policy
  ("not permitted via AI tools").
- Base currency / country / timezone — no Admin API mutation exists.

## Session 2026-10-21 (e) — remaining-gap pass, all verified by read-back
Done:
- **Product media** — pack images attached from https://thuris.vercel.app/images/ (status READY),
  alt text = the live site's: Frankincense ← 07, Neroli ← 08, Rose Geranium ← 09,
  Founding Collection bundle ← 03 (line-up) + 04 (bottles & boxes).
- **Collection** `The Founding Collection`, handle `founding-collection`
  (gid://shopify/Collection/513193476227), 4 products.
- **Published to Online Store** — the three essences (the bundle already was; this file's earlier
  "no sales channel" was wrong for it). No public exposure: the Online Store is password-locked.
- **Tags** `founding-collection`, `pre-order` on all four (marker only — not a selling plan).

Still blocked — re-tested, cause is outside the MCP:
- **Selling plan**: re-run, `Access denied … Required access: write_products … as well as any of
  write_own_subscription_contracts, write_purchase_options`. Granted scopes (read back via
  currentAppInstallation) have neither. Needs the scope on the MCP app, or create the plan in
  admin (or a pre-order app).
- **Storefront access**: tokenless Storefront API returns `Online Store channel is locked.`
  The store is on plan **Basic App Development** (a development store): password page on,
  checkout limited to test orders. **Real orders need a paid plan** — this is the root launch
  blocker under the token, the AED market (Shopify Payments) and checkout. After a plan: install
  the Headless channel for tokens, or remove the password and use tokenless access (products,
  collections, cart).
- **Markets / base currency ZAR**: unchanged; per-currency prices still PENDING from operator.
- **Policies** (scope is read_legal_policies only) and **shipping rates**: operator content, not written.
