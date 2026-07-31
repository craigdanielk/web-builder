"use client";
import { AppFrame, AppHeader } from "@/components/shell";
import { Card } from "@/components/primitives";
import { MessageCircle, Phone, Search, ChevronDown } from "lucide-react";

const faqs = [
  { q: "How long do cross-border settlements take?", a: "XRP-Ledger routed transfers settle in 3–5 seconds. Fiat rails follow local cut-off times." },
  { q: "What are the transaction limits at Tier 2?", a: "Completing the source-of-funds step lifts you to unlimited institutional volumes." },
  { q: "Which networks are supported for USDC?", a: "ERC-20 and XRPL-issued USDC. Always confirm the network before sending." },
  { q: "How is my custody secured?", a: "Segregated, regulated custody with multi-party approval on outbound value." },
];

export default function Help() {
  return (
    <AppFrame>
      <AppHeader title="Help centre" subtitle="24/7 institutional support" back="/account" />
      <div className="scroll px-5 pb-6">
        <label className="flex items-center gap-2 rounded-xl border border-hairline bg-surface px-4 py-3">
          <Search size={18} className="text-ink-mute" />
          <input placeholder="Search help articles" className="w-full bg-transparent text-[14px] text-ink outline-none placeholder:text-ink-faint" />
        </label>

        <div className="mt-3 grid grid-cols-2 gap-2.5">
          <Card className="flex flex-col items-center gap-2 p-4 text-center">
            <span className="grid h-11 w-11 place-items-center rounded-full" style={{ background: "var(--color-accent-soft)" }}><MessageCircle size={19} style={{ color: "var(--color-accent)" }} /></span>
            <p className="text-[13px] font-semibold text-ink">Live chat</p>
            <p className="text-[11px] text-ink-mute">Avg 2 min</p>
          </Card>
          <Card className="flex flex-col items-center gap-2 p-4 text-center">
            <span className="grid h-11 w-11 place-items-center rounded-full" style={{ background: "var(--color-violet-soft)" }}><Phone size={19} style={{ color: "var(--color-violet)" }} /></span>
            <p className="text-[13px] font-semibold text-ink">Call desk</p>
            <p className="text-[11px] text-ink-mute">Priority line</p>
          </Card>
        </div>

        <p className="mb-2 mt-5 px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">Popular questions</p>
        <Card className="divide-y divide-[var(--color-hairline)] p-1">
          {faqs.map((f) => (
            <details key={f.q} className="group px-3.5 py-3.5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[14px] font-medium text-ink">
                {f.q}
                <ChevronDown size={17} className="shrink-0 text-ink-mute transition group-open:rotate-180" />
              </summary>
              <p className="mt-2 text-[13px] leading-relaxed text-ink-mute">{f.a}</p>
            </details>
          ))}
        </Card>
      </div>
    </AppFrame>
  );
}
