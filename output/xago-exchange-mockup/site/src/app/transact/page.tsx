"use client";
import { useMemo, useState } from "react";
import Link from "next/link";
import { AppFrame, AppHeader } from "@/components/shell";
import { Glyph, Card, Button } from "@/components/primitives";
import { assets, assetById, usd, fmtAsset, type AssetId } from "@/lib/mock";
import { ArrowDown, Check, ChevronDown, Zap, X } from "lucide-react";

const STEPS = ["Amount", "Review", "Done"] as const;

export default function Transact() {
  const [step, setStep] = useState(0);
  const [from, setFrom] = useState<AssetId>("USDC");
  const [to, setTo] = useState<AssetId>("XRP");
  const [amount, setAmount] = useState("50000");
  const [picking, setPicking] = useState<null | "from" | "to">(null);

  const fromA = assetById(from)!, toA = assetById(to)!;
  const amt = parseFloat(amount || "0");
  const rate = fromA.priceUsd / toA.priceUsd;
  const feePct = 0.0015;
  const receive = amt * rate * (1 - feePct);
  const fee = amt * feePct;

  return (
    <AppFrame nav={step === 0}>
      <AppHeader title={step === 2 ? "Confirmed" : "Convert"} back={step === 0 ? undefined : "/transact"}
        subtitle={step < 2 ? `Step ${step + 1} of 2` : undefined}
        right={step < 2 ? <Link href="/dashboard" aria-label="Close" className="grid h-9 w-9 place-items-center rounded-full border border-hairline bg-surface text-ink-dim"><X size={17} /></Link> : undefined} />

      <div className="scroll px-5 pb-4">
        {/* progress rail */}
        {step < 2 && (
          <div className="mb-4 flex gap-1.5">
            {STEPS.slice(0, 2).map((s, i) => (
              <div key={s} className="h-1 flex-1 rounded-full transition-all"
                style={{ background: i <= step ? "var(--color-accent)" : "var(--color-surface-3)" }} />
            ))}
          </div>
        )}

        {step === 0 && (
          <div className="rise flex flex-col gap-3">
            <AssetRow label="From" a={fromA} sub={`Balance ${fmtAsset(fromA.available, fromA)} ${fromA.id}`} onPick={() => setPicking("from")} />
            <div className="relative">
              <div className="absolute left-1/2 top-1/2 z-10 grid h-9 w-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-2 border-canvas" style={{ background: "var(--color-accent)" }}>
                <ArrowDown size={16} className="text-[#1a0f08]" />
              </div>
            </div>
            <AssetRow label="To" a={toA} sub={`1 ${fromA.id} ≈ ${fmtAsset(rate, toA)} ${toA.id}`} onPick={() => setPicking("to")} />

            {/* amount */}
            <Card className="mt-2 p-5 text-center">
              <p className="text-[12px] uppercase tracking-wide text-ink-mute">You pay</p>
              <div className="mt-1 flex items-center justify-center gap-1">
                <span className="display text-[22px] text-ink-mute">{fromA.symbol}</span>
                <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^0-9.]/g, ""))}
                  className="display tnum w-full max-w-[220px] bg-transparent text-center text-[40px] text-ink outline-none" />
              </div>
              <p className="tnum mt-1 text-[13px] text-ink-mute">≈ {usd(amt * fromA.priceUsd)}</p>
              <div className="mt-3 flex justify-center gap-2">
                {[25, 50, 100].map((p) => (
                  <button key={p} onClick={() => setAmount(String(Math.round(fromA.available * p / 100)))}
                    className="rounded-full bg-surface-2 px-3 py-1 text-[12px] font-medium text-ink-dim">{p === 100 ? "Max" : `${p}%`}</button>
                ))}
              </div>
            </Card>

            <Card className="flex items-center justify-between p-4">
              <span className="text-[13px] text-ink-mute">You receive</span>
              <span className="tnum text-[16px] font-semibold text-ink">{fmtAsset(receive, toA)} {toA.id}</span>
            </Card>
          </div>
        )}

        {step === 1 && (
          <div className="rise flex flex-col gap-3">
            <Card className="p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3"><Glyph a={fromA} /><div><p className="text-[12px] text-ink-mute">You pay</p><p className="tnum text-[17px] font-semibold text-ink">{fmtAsset(amt, fromA)} {fromA.id}</p></div></div>
              </div>
              <div className="my-3 ml-5 h-6 border-l border-dashed border-hairline-strong" />
              <div className="flex items-center gap-3"><Glyph a={toA} /><div><p className="text-[12px] text-ink-mute">You receive</p><p className="tnum text-[17px] font-semibold text-ink">{fmtAsset(receive, toA)} {toA.id}</p></div></div>
            </Card>
            <Card className="divide-y divide-[var(--color-hairline)] p-1">
              {[["Rate", `1 ${fromA.id} = ${fmtAsset(rate, toA)} ${toA.id}`], ["Network fee", `${usd(fee)} · 0.15%`], ["Settlement", "Instant · XRP Ledger"], ["Reference", "AUTO-77413"]].map(([l, v]) => (
                <div key={l} className="flex items-center justify-between px-3.5 py-3">
                  <span className="text-[13px] text-ink-mute">{l}</span>
                  <span className="tnum text-[13px] font-medium text-ink">{v}</span>
                </div>
              ))}
            </Card>
            <div className="flex items-center gap-2 rounded-xl border border-hairline bg-surface px-3.5 py-3">
              <Zap size={16} style={{ color: "var(--color-accent)" }} />
              <p className="text-[12px] text-ink-mute">Rate locked for 00:14. Executed at confirmation.</p>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="rise flex flex-col items-center gap-4 py-10 text-center">
            <span className="grid h-20 w-20 place-items-center rounded-full" style={{ background: "var(--color-pos-soft)" }}>
              <Check size={40} style={{ color: "var(--color-pos)" }} strokeWidth={3} />
            </span>
            <div>
              <h2 className="display text-[24px] text-ink">Conversion complete</h2>
              <p className="mt-1 text-[14px] text-ink-mute">{fmtAsset(amt, fromA)} {fromA.id} → {fmtAsset(receive, toA)} {toA.id}</p>
            </div>
            <Card className="w-full divide-y divide-[var(--color-hairline)] p-1 text-left">
              {[["Received", `${fmtAsset(receive, toA)} ${toA.id}`], ["Reference", "AUTO-77413"], ["Settled", "Just now · Instant"]].map(([l, v]) => (
                <div key={l} className="flex items-center justify-between px-3.5 py-3"><span className="text-[13px] text-ink-mute">{l}</span><span className="tnum text-[13px] font-medium text-ink">{v}</span></div>
              ))}
            </Card>
          </div>
        )}
      </div>

      {/* sticky CTA */}
      <div className="border-t border-hairline bg-[color-mix(in_srgb,var(--color-canvas)_86%,transparent)] px-5 py-3.5 backdrop-blur-xl">
        {step === 0 && <Button full onClick={() => setStep(1)} disabled={!(amt > 0)}>Review conversion</Button>}
        {step === 1 && <Button full onClick={() => setStep(2)}>Slide to confirm · {usd(amt * fromA.priceUsd)}</Button>}
        {step === 2 && <div className="flex gap-2"><Button variant="soft" full href="/activity">View receipt</Button><Button full href="/dashboard">Done</Button></div>}
      </div>

      {picking && (
        <AssetPicker exclude={picking === "from" ? to : from}
          onClose={() => setPicking(null)}
          onPick={(id) => { picking === "from" ? setFrom(id) : setTo(id); setPicking(null); }} />
      )}
    </AppFrame>
  );
}

function AssetRow({ label, a, sub, onPick }: { label: string; a: ReturnType<typeof assetById>; sub: string; onPick: () => void }) {
  if (!a) return null;
  return (
    <button onClick={onPick} className="flex w-full items-center gap-3 rounded-2xl border border-hairline bg-surface p-4 text-left active:scale-[0.99]">
      <Glyph a={a} />
      <div className="min-w-0 flex-1">
        <p className="text-[12px] text-ink-mute">{label}</p>
        <p className="text-[16px] font-semibold text-ink">{a.name} <span className="text-ink-mute">·</span> {a.id}</p>
        <p className="tnum truncate text-[12px] text-ink-mute">{sub}</p>
      </div>
      <ChevronDown size={18} className="text-ink-mute" />
    </button>
  );
}

function AssetPicker({ exclude, onClose, onPick }: { exclude: AssetId; onClose: () => void; onPick: (id: AssetId) => void }) {
  return (
    <div className="absolute inset-0 z-40 flex flex-col justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50" />
      <div className="rise relative rounded-t-3xl border-t border-hairline bg-surface p-4 pb-6" onClick={(e) => e.stopPropagation()} style={{ animationDuration: "0.28s" }}>
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-surface-3" />
        <p className="mb-2 px-1 text-[13px] font-semibold uppercase tracking-wide text-ink-mute">Select asset</p>
        <div className="max-h-[46vh] overflow-y-auto">
          {assets.filter((a) => a.id !== exclude).map((a) => (
            <button key={a.id} onClick={() => onPick(a.id)} className="flex w-full items-center gap-3 rounded-xl px-2 py-2.5 active:bg-surface-2">
              <Glyph a={a} size={36} />
              <div className="flex-1 text-left"><p className="text-[15px] font-medium text-ink">{a.name}</p><p className="tnum text-[12px] text-ink-mute">{fmtAsset(a.available, a)} {a.id}</p></div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
