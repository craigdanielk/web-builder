"use client";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AppFrame, AppHeader } from "@/components/shell";
import { Glyph, Delta, Card, Button, Spark } from "@/components/primitives";
import { assetById, txs, usd, fmtAsset, relTime } from "@/lib/mock";
import { Plus, ArrowUpRight, ArrowDownLeft, RefreshCw } from "lucide-react";

export default function WalletDetail() {
  const { asset } = useParams<{ asset: string }>();
  const a = assetById(String(asset).toUpperCase());
  if (!a) return <AppFrame><div className="scroll grid place-items-center text-ink-mute">Asset not found</div></AppFrame>;

  const spark = [0.94, 0.97, 0.95, 0.99, 1.0, 1.03, 1.02, 1.06].map((m) => a.priceUsd * m);
  const rows = txs.filter((t) => t.asset === a.id || t.counterAsset === a.id).slice(0, 5);

  return (
    <AppFrame>
      <AppHeader title={a.name} back="/wallets" subtitle={`${a.id} · ${a.kind}`} right={<Glyph a={a} size={34} />} />
      <div className="scroll px-5 pb-6">
        <Card className="rise p-5">
          <p className="text-[12px] uppercase tracking-wide text-ink-mute">Balance</p>
          <div className="mt-1 flex items-end justify-between">
            <span className="display tnum text-[32px] text-ink">{fmtAsset(a.balance, a)} <span className="text-[18px] text-ink-mute">{a.id}</span></span>
            <Delta v={a.change24h} />
          </div>
          <p className="tnum mt-1 text-[14px] text-ink-mute">≈ {usd(a.balance * a.priceUsd)}</p>
          <div className="mt-3"><Spark data={spark} up={a.change24h >= 0} w={340} h={54} /></div>

          <div className="mt-4 grid grid-cols-3 divide-x divide-[var(--color-hairline)] rounded-xl bg-surface-2">
            {[["Available", a.available], ["Pending", a.pending], ["In orders", a.openOrders]].map(([l, v]) => (
              <div key={l as string} className="px-3 py-3 text-center">
                <p className="text-[11px] text-ink-mute">{l}</p>
                <p className="tnum mt-0.5 text-[14px] font-semibold text-ink">{fmtAsset(v as number, a)}</p>
              </div>
            ))}
          </div>
        </Card>

        <div className="mt-4 grid grid-cols-4 gap-2">
          {[["Deposit", Plus, `/wallets/${a.id}`], ["Send", ArrowUpRight, "/transact"], ["Receive", ArrowDownLeft, "/payment-links"], ["Convert", RefreshCw, "/transact"]].map(([l, Ic, href]) => {
            const Icon = Ic as React.ElementType;
            return (
              <Link key={l as string} href={href as string} className="flex flex-col items-center gap-2 rounded-2xl border border-hairline bg-surface py-3.5 active:scale-95">
                <span className="grid h-10 w-10 place-items-center rounded-full" style={{ background: "var(--color-accent-soft)" }}>
                  <Icon size={18} style={{ color: "var(--color-accent)" }} />
                </span>
                <span className="text-[11px] font-medium text-ink-dim">{l as string}</span>
              </Link>
            );
          })}
        </div>

        <div className="mt-6">
          <p className="px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">Activity</p>
          <Card className="mt-2.5 divide-y divide-[var(--color-hairline)] p-1">
            {rows.map((t) => (
              <Link key={t.id} href="/activity" className="flex items-center gap-3 rounded-xl px-3 py-3 active:bg-surface-2">
                <span className="grid h-9 w-9 place-items-center rounded-full bg-surface-2">
                  {t.type === "receive" || t.type === "deposit" ? <ArrowDownLeft size={16} style={{ color: "var(--color-pos)" }} />
                    : t.type === "convert" || t.type === "trade" ? <RefreshCw size={15} style={{ color: "var(--color-violet)" }} />
                    : <ArrowUpRight size={16} style={{ color: "var(--color-accent)" }} />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-medium text-ink">{t.counterparty}</p>
                  <p className="text-[12px] text-ink-mute">{relTime(t.date)}</p>
                </div>
                <p className="tnum text-[13px] font-semibold text-ink">{fmtAsset(t.amount, a)}</p>
              </Link>
            ))}
          </Card>
        </div>

        <Button href="/transact" full className="mt-5">Trade {a.id}</Button>
      </div>
    </AppFrame>
  );
}
