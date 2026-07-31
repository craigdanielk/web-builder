"use client";
import Link from "next/link";
import { AppFrame, AppHeader, BellButton } from "@/components/shell";
import { Card, Delta, Spark } from "@/components/primitives";
import { markets, assetById, fmt } from "@/lib/mock";

export default function Markets() {
  return (
    <AppFrame>
      <AppHeader title="Markets" subtitle="Live rates" right={<BellButton />} />
      <div className="scroll px-5 pb-6">
        <Card className="rise flex items-center justify-between p-4">
          <div>
            <p className="text-[12px] uppercase tracking-wide text-ink-mute">XRP / USDT</p>
            <p className="display tnum text-[26px] text-ink">$2.41</p>
          </div>
          <div className="text-right">
            <Delta v={3.82} />
            <div className="mt-1"><Spark data={markets[0].spark} up w={120} h={40} /></div>
          </div>
        </Card>

        <p className="mb-2 mt-5 px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">All pairs</p>
        <Card className="divide-y divide-[var(--color-hairline)] p-1">
          {markets.map((m) => {
            const base = assetById(m.base)!;
            return (
              <Link key={m.pair} href="/transact" className="flex items-center gap-3 rounded-xl px-3 py-3 active:bg-surface-2">
                <span className="grid h-9 w-9 place-items-center rounded-full text-[13px] font-semibold"
                  style={{ background: `color-mix(in srgb,${base.accent} 55%,#0a0c10)`, border: `1px solid color-mix(in srgb,${base.accent} 70%,transparent)` }}>
                  {base.symbol}
                </span>
                <div className="flex-1">
                  <p className="text-[14px] font-semibold text-ink">{m.pair}</p>
                  <p className="text-[12px] text-ink-mute">Vol ${fmt((m.price * 1934), { min: 0, max: 0 })}k</p>
                </div>
                <Spark data={m.spark} up={m.change24h >= 0} w={56} h={22} />
                <div className="w-[86px] text-right">
                  <p className="tnum text-[14px] font-semibold text-ink">{m.price >= 100 ? fmt(m.price, { min: 0, max: 0 }) : fmt(m.price, { min: 2, max: m.price < 2 ? 4 : 2 })}</p>
                  <Delta v={m.change24h} />
                </div>
              </Link>
            );
          })}
        </Card>
      </div>
    </AppFrame>
  );
}
