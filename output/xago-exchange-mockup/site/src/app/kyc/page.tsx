"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { AppFrame, AppHeader } from "@/components/shell";
import { Button, Card } from "@/components/primitives";
import { Check, IdCard, Home, Banknote, ShieldCheck, ChevronRight, Camera } from "lucide-react";

const STEPS = [
  { key: "identity", label: "Identity", icon: IdCard, done: true, desc: "Passport verified" },
  { key: "address", label: "Address", icon: Home, done: true, desc: "Proof of residence verified" },
  { key: "funds", label: "Source of funds", icon: Banknote, done: false, desc: "Declaration outstanding" },
  { key: "review", label: "Final review", icon: ShieldCheck, done: false, desc: "Compliance sign-off" },
];

export default function KYC() {
  const router = useRouter();
  const [current, setCurrent] = useState(2); // funds step outstanding
  const completed = STEPS.filter((s, i) => s.done || i < current).length;
  const pct = Math.round((completed / STEPS.length) * 100);

  return (
    <AppFrame nav={false}>
      <AppHeader title="Verify your account" subtitle="Tier 2 · one step remaining" />
      <div className="scroll px-5 pb-8">
        {/* Always-visible progress — the fix for the truncated toast */}
        <Card className="rise overflow-hidden p-4">
          <div className="mb-3 flex items-end justify-between">
            <div>
              <p className="text-[12px] uppercase tracking-wide text-ink-mute">Verification progress</p>
              <p className="display text-[26px] text-ink">{pct}<span className="text-[16px] text-ink-mute">%</span></p>
            </div>
            <span className="rounded-full px-2.5 py-1 text-[12px] font-medium" style={{ background: "var(--color-accent-soft)", color: "var(--color-accent-2)" }}>
              {STEPS.length - completed} step left
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-3">
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: `${pct}%`, background: "linear-gradient(90deg,var(--color-accent-2),var(--color-accent))" }} />
          </div>
        </Card>

        <ol className="mt-5 flex flex-col gap-2.5">
          {STEPS.map((s, i) => {
            const done = s.done || i < current;
            const active = i === current;
            const Icon = s.icon;
            return (
              <li key={s.key}>
                <button onClick={() => !done && setCurrent(i)}
                  className="flex w-full items-center gap-3.5 rounded-2xl border p-3.5 text-left transition"
                  style={{
                    borderColor: active ? "color-mix(in srgb,var(--color-accent) 50%,transparent)" : "var(--color-hairline)",
                    background: active ? "var(--color-accent-soft)" : "var(--color-surface)",
                  }}>
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full"
                    style={{ background: done ? "var(--color-pos-soft)" : active ? "var(--color-accent-soft)" : "var(--color-surface-2)" }}>
                    {done ? <Check size={20} style={{ color: "var(--color-pos)" }} />
                          : <Icon size={19} style={{ color: active ? "var(--color-accent)" : "var(--color-ink-mute)" }} />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[15px] font-semibold text-ink">{s.label}</span>
                    <span className="block truncate text-[12px]" style={{ color: done ? "var(--color-pos)" : "var(--color-ink-mute)" }}>
                      {done ? "Completed" : s.desc}
                    </span>
                  </span>
                  {active && <ChevronRight size={18} className="text-ink-mute" />}
                </button>
              </li>
            );
          })}
        </ol>

        {/* Active step body */}
        <Card className="mt-5 p-4">
          <p className="text-[13px] font-semibold uppercase tracking-wide text-ink-mute">Next: {STEPS[current]?.label}</p>
          <p className="mt-1.5 text-[14px] leading-relaxed text-ink-dim">
            Upload a signed declaration of the source of funds for institutional volumes. This unlocks unlimited transaction limits.
          </p>
          <button className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-hairline-strong py-6 text-[13px] text-ink-mute">
            <Camera size={18} /> Tap to upload document
          </button>
        </Card>

        <div className="mt-5 flex flex-col gap-2">
          <Button onClick={() => (current < STEPS.length - 1 ? setCurrent(current + 1) : router.push("/dashboard"))} full>
            {current < STEPS.length - 1 ? "Submit & continue" : "Finish verification"}
          </Button>
          <Button variant="ghost" href="/dashboard" full>Skip for now</Button>
        </div>
      </div>
    </AppFrame>
  );
}
