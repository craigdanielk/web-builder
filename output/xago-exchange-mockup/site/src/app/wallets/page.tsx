"use client";
import { useState } from "react";
import Link from "next/link";
import { AppFrame, AppHeader, BellButton } from "@/components/shell";
import { Glyph, Delta, Card, Button } from "@/components/primitives";
import { assets, portfolioUsd, usd, fmtAsset } from "@/lib/mock";
import { Plus, ArrowUpRight, ArrowDownLeft, RefreshCw, Search } from "lucide-react";

type Filter = "all" | "crypto" | "fiat";

export default function Wallets() {
  const [filter, setFilter] = useState<Filter>("all");
  const list = assets.filter((a) => filter === "all" || a.kind === filter);
  return (
    <AppFrame>
      <AppHeader title="Wallets" subtitle={`${assets.length} assets · ${usd(portfolioUsd)}`} right={<BellButton />} />
      <div className="scroll px-5 pb-6">
        {/* filter + search */}
        <div className="flex items-center gap-2">
          <div className="flex gap-1 rounded-full border border-hairline bg-surface p-1">
            {(["all", "crypto", "fiat"] as Filter[]).map((f) => (
              <button key={f} onClick={() => setFilter(f)}
                className="rounded-full px-3.5 py-1.5 text-[13px] font-medium capitalize transition"
                style={filter === f ? { background: "var(--color-surface-3)", color: "var(--color-ink)" } : { color: "var(--color-ink-mute)" }}>
                {f}
              </button>
            ))}
          </div>
          <button aria-label="Search" className="ml-auto grid h-10 w-10 place-items-center rounded-full border border-hairline bg-surface text-ink-dim">
            <Search size={18} />
          </button>
        </div>

        {/* Asset cards — each fully actionable on mobile (audit P1 fix) */}
        <div className="mt-4 flex flex-col gap-3">
          {list.map((a, i) => (
            <Card key={a.id} className="rise p-4" style={{ animationDelay: `${i * 40}ms` }}>
              <Link href={`/wallets/${a.id}`} className="flex items-center gap-3">
                <Glyph a={a} size={44} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-[16px] font-semibold text-ink">{a.name}</p>
                    <Delta v={a.change24h} />
                  </div>
                  <p className="tnum text-[13px] text-ink-mute">{fmtAsset(a.balance, a)} {a.id}</p>
                </div>
                <div className="text-right">
                  <p className="tnum text-[17px] font-semibold text-ink">{usd(a.balance * a.priceUsd)}</p>
                  {a.pending > 0 && <p className="tnum text-[11px]" style={{ color: "var(--color-warn)" }}>{fmtAsset(a.pending, a)} pending</p>}
                </div>
              </Link>
              <div className="mt-3.5 grid grid-cols-4 gap-2">
                <MiniAction href={`/wallets/${a.id}`} icon={Plus} label="Deposit" />
                <MiniAction href="/transact" icon={ArrowUpRight} label="Send" />
                <MiniAction href="/payment-links" icon={ArrowDownLeft} label="Receive" />
                <MiniAction href="/transact" icon={RefreshCw} label="Convert" />
              </div>
            </Card>
          ))}
        </div>

        <Button href="/transact" full className="mt-5">
          <Plus size={18} /> Add funds
        </Button>
      </div>
    </AppFrame>
  );
}

function MiniAction({ href, icon: Icon, label }: { href: string; icon: React.ElementType; label: string }) {
  return (
    <Link href={href} className="flex flex-col items-center gap-1.5 rounded-xl bg-surface-2 py-2.5 active:scale-95">
      <Icon size={17} style={{ color: "var(--color-accent)" }} />
      <span className="text-[11px] font-medium text-ink-dim">{label}</span>
    </Link>
  );
}
