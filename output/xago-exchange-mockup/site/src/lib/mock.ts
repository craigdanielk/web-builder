// Xago Exchange mockup — static mock data (NOT wired to production backend).
// Figures are illustrative for the CEO demo.

export type AssetId = "XRP" | "USDT" | "USDC" | "ZAR" | "USD" | "GBP" | "EUR" | "BTC";

export interface Asset {
  id: AssetId;
  name: string;
  kind: "crypto" | "fiat";
  symbol: string;      // display glyph / ticker
  balance: number;
  available: number;
  pending: number;
  openOrders: number;
  priceUsd: number;    // 1 unit in USD
  change24h: number;   // percent
  accent: string;
}

export const assets: Asset[] = [
  { id: "XRP",  name: "XRP",          kind: "crypto", symbol: "XRP", balance: 128450.22, available: 121000.00, pending: 2450.22, openOrders: 5000, priceUsd: 2.41,   change24h: 3.82,  accent: "#23292f" },
  { id: "USDT", name: "Tether",       kind: "crypto", symbol: "₮",   balance: 540210.00, available: 540210.0,  pending: 0,       openOrders: 0,    priceUsd: 1.0,    change24h: 0.01,  accent: "#26a17b" },
  { id: "USDC", name: "USD Coin",     kind: "crypto", symbol: "$",   balance: 312880.50, available: 300000.0,  pending: 12880.5, openOrders: 0,    priceUsd: 1.0,    change24h: -0.02, accent: "#2775ca" },
  { id: "BTC",  name: "Bitcoin",      kind: "crypto", symbol: "₿",   balance: 4.2081,    available: 4.2081,   pending: 0,       openOrders: 0,    priceUsd: 96420,  change24h: 1.94,  accent: "#f7931a" },
  { id: "ZAR",  name: "S. African Rand", kind: "fiat", symbol: "R",  balance: 8420500.0, available: 8420500,  pending: 0,       openOrders: 0,    priceUsd: 0.055,  change24h: -0.31, accent: "#3a5a40" },
  { id: "USD",  name: "US Dollar",    kind: "fiat",   symbol: "$",   balance: 275000.00, available: 275000,   pending: 0,       openOrders: 0,    priceUsd: 1.0,    change24h: 0,     accent: "#2e5e4e" },
  { id: "GBP",  name: "Pound Sterling", kind: "fiat", symbol: "£",   balance: 96500.00,  available: 96500,    pending: 0,       openOrders: 0,    priceUsd: 1.27,   change24h: 0.12,  accent: "#3d3a63" },
  { id: "EUR",  name: "Euro",         kind: "fiat",   symbol: "€",   balance: 141200.00, available: 141200,   pending: 0,       openOrders: 0,    priceUsd: 1.08,   change24h: -0.08, accent: "#334155" },
];

export const assetById = (id: string) => assets.find((a) => a.id === id);

export const portfolioUsd = assets.reduce((s, a) => s + a.balance * a.priceUsd, 0);
export const portfolioChange24h = 2.14; // blended %

export type TxType = "receive" | "send" | "convert" | "deposit" | "withdraw" | "trade";
export type TxStatus = "completed" | "pending" | "failed";

export interface Tx {
  id: string;
  type: TxType;
  asset: AssetId;
  counterAsset?: AssetId;
  amount: number;
  counterparty: string;
  status: TxStatus;
  date: string;       // ISO
  reference: string;
}

export const txs: Tx[] = [
  { id: "TX-90412", type: "receive", asset: "USDT", amount: 250000, counterparty: "Aurora Holdings Ltd", status: "completed", date: "2026-07-24T07:12:00Z", reference: "Settlement · INV-2291" },
  { id: "TX-90411", type: "convert", asset: "ZAR", counterAsset: "USDT", amount: 4600000, counterparty: "Internal conversion", status: "completed", date: "2026-07-24T06:40:00Z", reference: "R4,600,000 → 248,900 USDT" },
  { id: "TX-90408", type: "send", asset: "XRP", amount: 42000, counterparty: "Meridian Capital", status: "pending", date: "2026-07-24T06:05:00Z", reference: "Payout · batch 7741" },
  { id: "TX-90402", type: "deposit", asset: "GBP", amount: 96500, counterparty: "Barclays · •••4021", status: "completed", date: "2026-07-23T15:22:00Z", reference: "Faster Payment" },
  { id: "TX-90399", type: "trade", asset: "BTC", counterAsset: "USDC", amount: 1.5, counterparty: "Market order", status: "completed", date: "2026-07-23T11:48:00Z", reference: "Buy 1.5 BTC @ 96,180" },
  { id: "TX-90387", type: "send", asset: "USD", amount: 120000, counterparty: "Nakamoto Trust", status: "failed", date: "2026-07-22T18:03:00Z", reference: "Beneficiary unverified" },
  { id: "TX-90380", type: "receive", asset: "EUR", amount: 88000, counterparty: "Zenith Partners GmbH", status: "completed", date: "2026-07-22T09:15:00Z", reference: "SEPA · order 5521" },
  { id: "TX-90361", type: "convert", asset: "USDC", counterAsset: "XRP", amount: 300000, counterparty: "Internal conversion", status: "completed", date: "2026-07-21T14:30:00Z", reference: "300,000 USDC → 124,900 XRP" },
];

export interface Beneficiary {
  id: string;
  name: string;
  handle: string;       // bank ref / wallet tag
  network: string;
  verified: boolean;
  fav: boolean;
  initials: string;
  tint: string;
}

export const beneficiaries: Beneficiary[] = [
  { id: "b1", name: "Meridian Capital", handle: "GB29 •••• 7741", network: "SWIFT · GBP", verified: true, fav: true, initials: "MC", tint: "#7c5cfc" },
  { id: "b2", name: "Aurora Holdings Ltd", handle: "r9cVa•••Xk2p", network: "XRP Ledger", verified: true, fav: true, initials: "AH", tint: "#f47643" },
  { id: "b3", name: "Zenith Partners GmbH", handle: "DE89 •••• 3004", network: "SEPA · EUR", verified: true, fav: false, initials: "ZP", tint: "#35d6a4" },
  { id: "b4", name: "Nakamoto Trust", handle: "0x71C•••9a2E", network: "USDC · ERC-20", verified: false, fav: false, initials: "NT", tint: "#ff6a6a" },
  { id: "b5", name: "Cape Reserve Bank", handle: "ZA •••• 5590", network: "Wire · ZAR", verified: true, fav: false, initials: "CR", tint: "#2775ca" },
];

export interface PaymentLink {
  id: string;
  title: string;
  asset: AssetId;
  amount: number | null;
  status: "active" | "paid" | "expired";
  views: number;
  created: string;
}

export const paymentLinks: PaymentLink[] = [
  { id: "pl1", title: "Invoice · Aurora Q3", asset: "USDT", amount: 250000, status: "paid", views: 3, created: "2026-07-20" },
  { id: "pl2", title: "Retainer · Meridian", asset: "GBP", amount: 45000, status: "active", views: 11, created: "2026-07-22" },
  { id: "pl3", title: "Open donation link", asset: "XRP", amount: null, status: "active", views: 204, created: "2026-07-10" },
  { id: "pl4", title: "Deposit · Zenith", asset: "EUR", amount: 88000, status: "expired", views: 1, created: "2026-06-30" },
];

export interface Market {
  pair: string;
  base: AssetId;
  quote: AssetId;
  price: number;
  change24h: number;
  spark: number[];
}

export const markets: Market[] = [
  { pair: "XRP/USDT",  base: "XRP",  quote: "USDT", price: 2.41,   change24h: 3.82,  spark: [2.28,2.31,2.29,2.35,2.34,2.39,2.41] },
  { pair: "BTC/USDC",  base: "BTC",  quote: "USDC", price: 96420,  change24h: 1.94,  spark: [94100,95200,94800,95600,96010,96180,96420] },
  { pair: "USDT/ZAR",  base: "USDT", quote: "ZAR",  price: 18.19,  change24h: 0.31,  spark: [18.02,18.08,18.11,18.05,18.14,18.16,18.19] },
  { pair: "XRP/ZAR",   base: "XRP",  quote: "ZAR",  price: 43.84,  change24h: 4.10,  spark: [41.9,42.3,42.1,42.9,43.2,43.6,43.84] },
  { pair: "EUR/USD",   base: "EUR",  quote: "USD",  price: 1.08,   change24h: -0.08, spark: [1.083,1.082,1.081,1.080,1.081,1.080,1.080] },
  { pair: "GBP/USD",   base: "GBP",  quote: "USD",  price: 1.27,   change24h: 0.12,  spark: [1.267,1.268,1.269,1.268,1.270,1.269,1.270] },
];

export const user = {
  name: "Jürgen Volkmann",
  firstName: "Jürgen",
  company: "Volkmann Family Office",
  email: "j.volkmann@vfo.example",
  tier: "Institutional",
  kycLevel: 2,
  kycComplete: false, // one step outstanding — drives the KYC prompt (audit P2 fix)
  avatarTint: "#f47643",
  initials: "JV",
};

// Currency formatting — grouped, tabular. Crypto keeps more precision.
export function fmt(n: number, opts?: { max?: number; min?: number }) {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: opts?.min ?? 2,
    maximumFractionDigits: opts?.max ?? 2,
  });
}
export function fmtAsset(n: number, a?: Pick<Asset, "kind">) {
  if (a?.kind === "crypto") return fmt(n, { min: 0, max: n < 10 ? 4 : 2 });
  return fmt(n);
}
export function usd(n: number) {
  return "$" + fmt(n);
}
export function relTime(iso: string) {
  const d = new Date(iso).getTime();
  const now = new Date("2026-07-24T08:00:00Z").getTime();
  const m = Math.round((now - d) / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}
