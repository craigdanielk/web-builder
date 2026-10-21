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

All ACTIVE, **published to no sales channel**. Descriptions are the approved copy lines.

## Refused (not done)
- **Pre-order selling plan** — `sellingPlanGroupCreate` denied: the MCP app lacks the
  `write_purchase_options` scope. Intended plan: "Pre-order — paid in full at checkout"
  (PRE_ORDER, 100% at checkout, fulfilment UNKNOWN, inventory reserved ON_SALE), attached to all four.
- **UAE market in AED** — `marketCreate` error MULTIPLE_CURRENCIES_NOT_SUPPORTED: the store's
  payment gateway supports one currency. Needs Shopify Payments (a handoff launch blocker).
- **Storefront access token** — `storefrontAccessTokenCreate` refused by the MCP safety policy
  ("not permitted via AI tools").
- Base currency / country / timezone — no Admin API mutation exists.
