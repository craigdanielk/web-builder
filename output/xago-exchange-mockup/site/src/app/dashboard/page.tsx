"use client";
import Link from "next/link";
import { AppFrame, AppHeader, BellButton } from "@/components/shell";
import { Glyph, Delta, Card, SectionLabel, Button } from "@/components/primitives";
import { assets, txs, portfolioUsd, portfolioChange24h, user, usd, fmtAsset, relTime } from "@/lib/mock";
import { ArrowDownLeft, ArrowUpRight, RefreshCw, Plus, ShieldAlert, ChevronRight, Eye } from "lucide-react";

const actions = [
  { label: "Deposit", href: "/wallets", icon: Plus },
  { label: "Send", href: "/transact", icon: ArrowUpRight },
  { label: "Receive", href: "/payment-links", icon: ArrowDownLeft },
  { label: "Convert", href: "/transact", icon: RefreshCw },
];

export default function Dashboard() {
  const top = [...assets].sort((a, b) => b.balance * b.priceUsd - a.balance * a.priceUsd).slice(0, 4);
  return (
    <AppFrame>
      <AppHeader
        title={`Good morning, ${user.firstName}`}
        subtitle={user.company}
        right={<BellButton />}
      />
      <div className="scroll px-5 pb-6">
        {/* Portfolio */}
        <Card className="rise relative overflow-hidden p-5" style={{ animationDelay: "30ms" }}>
          <div className="pointer-events-none absolute -right-10 -top-16 h-40 w-40 rounded-full opacity-40 blur-2xl" style={{ background: "radial-gradient(circle,var(--color-accent),transparent 70%)" }} />
          <div className="flex items-center justify-between">
            <span className="text-[12px] uppercase tracking-[0.14em] text-ink-mute">Total portfolio value</span>
            <Eye size={16} className="text-ink-mute" />
          </div>
          <div className="mt-1.5 flex items-end gap-2.5">
            <span className="display tnum text-[38px] leading-none text-ink">{usd(portfolioUsd)}</span>
          </div>
          <div className="mt-2.5 flex items-center gap-2 text-[13px] text-ink-mute">
            <Delta v={portfolioChange24h} />
            <span className="tnum">+{usd(portfolioUsd * portfolioChange24h / 100).replace("$", "$")}</span>
            <span>· 24h</span>
          </div>
        </Card>

        {/* Quick actions */}
        <div className="mt-4 grid grid-cols-4 gap-2">
          {actions.map(({ label, href, icon: Icon }) => (
            <Link key={label} href={href} className="flex flex-col items-center gap-2 rounded-2xl border border-hairline bg-surface py-3.5 active:scale-95">
              <span className="grid h-10 w-10 place-items-center rounded-full" style={{ background: "var(--color-accent-soft)" }}>
                <Icon size={19} style={{ color: "var(--color-accent)" }} />
              </span>
              <span className="text-[11px] font-medium text-ink-dim">{label}</span>
            </Link>
          ))}
        </div>

        {/* KYC prompt — fixed inline card (audit P2: replaces truncated toast) */}
        {!user.kycComplete && (
          <Link href="/kyc" className="mt-4 flex items-center gap-3 rounded-2xl border p-3.5 active:scale-[0.99]"
            style={{ borderColor: "color-mix(in srgb,var(--color-warn) 40%,transparent)", background: "rgba(246,196,83,0.10)" }}>
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full" style={{ background: "rgba(246,196,83,0.18)" }}>
              <ShieldAlert size={19} style={{ color: "var(--color-warn)" }} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-semibold text-ink">Finish verification to lift limits</p>
              <p className="text-[12px] text-ink-mute">1 step left · Source of funds declaration</p>
            </div>
            <ChevronRight size={18} className="text-ink-mute" />
          </Link>
        )}

        {/* Holdings */}
        <div className="mt-6 flex flex-col gap-2.5">
          <SectionLabel action={<Link href="/wallets" className="text-[12px] font-medium text-accent-2">See all</Link>}>Your assets</SectionLabel>
          <Card className="divide-y divide-[var(--color-hairline)] p-1">
            {top.map((a) => (
              <Link key={a.id} href={`/wallets/${a.id}`} className="flex items-center gap-3 px-3 py-3 active:bg-surface-2 rounded-xl">
                <Glyph a={a} />
                <div className="min-w-0 flex-1">
                  <p className="text-[15px] font-semibold text-ink">{a.name}</p>
                  <p className="tnum text-[12px] text-ink-mute">{fmtAsset(a.balance, a)} {a.id}</p>
                </div>
                <div className="text-right">
                  <p className="tnum text-[15px] font-semibold text-ink">{usd(a.balance * a.priceUsd)}</p>
                  <Delta v={a.change24h} />
                </div>
              </Link>
            ))}
          </Card>
        </div>

        {/* Recent activity */}
        <div className="mt-6 flex flex-col gap-2.5">
          <SectionLabel action={<Link href="/activity" className="text-[12px] font-medium text-accent-2">History</Link>}>Recent activity</SectionLabel>
          <Card className="divide-y divide-[var(--color-hairline)] p-1">
            {txs.slice(0, 3).map((t) => (
              <Link key={t.id} href="/activity" className="flex items-center gap-3 px-3 py-3 active:bg-surface-2 rounded-xl">
                <span className="grid h-10 w-10 place-items-center rounded-full" style={{ background: "var(--color-surface-2)" }}>
                  {t.type === "receive" || t.type === "deposit" ? <ArrowDownLeft size={18} style={{ color: "var(--color-pos)" }} />
                    : t.type === "convert" || t.type === "trade" ? <RefreshCw size={17} style={{ color: "var(--color-violet)" }} />
                    : <ArrowUpRight size={18} style={{ color: "var(--color-accent)" }} />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-medium text-ink">{t.counterparty}</p>
                  <p className="text-[12px] text-ink-mute">{relTime(t.date)} · {t.status}</p>
                </div>
                <p className="tnum text-[14px] font-semibold text-ink">{fmtAsset(t.amount, { kind: t.asset.length === 3 && ["XRP","BTC","USDT","USDC"].includes(t.asset) ? "crypto" : "fiat" })} {t.asset}</p>
              </Link>
            ))}
          </Card>
        </div>

        <Button href="/markets" variant="soft" full className="mt-6">View live markets</Button>
      </div>
    </AppFrame>
  );
}
