"use client";
import { useState } from "react";
import { AppFrame, AppHeader, BellButton } from "@/components/shell";
import { Card, Pill } from "@/components/primitives";
import { txs, fmtAsset, relTime, type Tx } from "@/lib/mock";
import { ArrowDownLeft, ArrowUpRight, RefreshCw, Download, Search } from "lucide-react";

const isCrypto = (a: string) => ["XRP", "BTC", "USDT", "USDC"].includes(a);
const icon = (t: Tx) =>
  t.type === "receive" || t.type === "deposit" ? <ArrowDownLeft size={18} style={{ color: "var(--color-pos)" }} />
  : t.type === "convert" || t.type === "trade" ? <RefreshCw size={16} style={{ color: "var(--color-violet)" }} />
  : <ArrowUpRight size={18} style={{ color: "var(--color-accent)" }} />;

export default function Activity() {
  const [tab, setTab] = useState<"all" | "in" | "out">("all");
  const list = txs.filter((t) =>
    tab === "all" ? true : tab === "in" ? ["receive", "deposit"].includes(t.type) : ["send", "withdraw"].includes(t.type));

  const groups: Record<string, Tx[]> = {};
  for (const t of list) {
    const d = new Date(t.date);
    const key = d.toDateString() === new Date("2026-07-24").toDateString() ? "Today"
      : d.toDateString() === new Date("2026-07-23").toDateString() ? "Yesterday"
      : d.toLocaleDateString("en-US", { month: "long", day: "numeric" });
    (groups[key] ??= []).push(t);
  }

  return (
    <AppFrame>
      <AppHeader title="Activity" subtitle="Transaction history" right={<BellButton />} />
      <div className="scroll px-5 pb-6">
        <div className="flex items-center gap-2">
          <div className="flex flex-1 gap-1 rounded-full border border-hairline bg-surface p-1">
            {(["all", "in", "out"] as const).map((f) => (
              <button key={f} onClick={() => setTab(f)}
                className="flex-1 rounded-full py-1.5 text-[13px] font-medium capitalize"
                style={tab === f ? { background: "var(--color-surface-3)", color: "var(--color-ink)" } : { color: "var(--color-ink-mute)" }}>
                {f === "in" ? "Received" : f === "out" ? "Sent" : "All"}
              </button>
            ))}
          </div>
          <button aria-label="Export" className="grid h-10 w-10 place-items-center rounded-full border border-hairline bg-surface text-ink-dim"><Download size={17} /></button>
        </div>

        {Object.entries(groups).map(([day, items]) => (
          <div key={day} className="mt-5">
            <p className="mb-2 px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">{day}</p>
            <Card className="divide-y divide-[var(--color-hairline)] p-1">
              {items.map((t) => (
                <div key={t.id} className="flex items-center gap-3 px-3 py-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-surface-2">{icon(t)}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[14px] font-medium text-ink">{t.counterparty}</p>
                    <p className="truncate text-[12px] text-ink-mute">{t.reference}</p>
                  </div>
                  <div className="text-right">
                    <p className="tnum text-[14px] font-semibold text-ink"
                      style={{ color: ["receive", "deposit"].includes(t.type) ? "var(--color-pos)" : undefined }}>
                      {["receive", "deposit"].includes(t.type) ? "+" : t.type === "send" ? "−" : ""}{fmtAsset(t.amount, { kind: isCrypto(t.asset) ? "crypto" : "fiat" })} {t.asset}
                    </p>
                    <div className="mt-0.5 flex justify-end"><Pill status={t.status} /></div>
                  </div>
                </div>
              ))}
            </Card>
          </div>
        ))}
      </div>
    </AppFrame>
  );
}
