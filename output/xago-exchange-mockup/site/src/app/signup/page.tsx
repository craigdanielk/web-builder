"use client";
import Link from "next/link";
import { AppFrame, AppHeader } from "@/components/shell";
import { Button, Card } from "@/components/primitives";
import { DemoTag } from "@/components/brand";
import { Building2, User, Mail, ArrowRight, Check } from "lucide-react";

export default function Signup() {
  return (
    <AppFrame nav={false}>
      <AppHeader title="Open an account" back="/login" subtitle="Institutional onboarding · ~3 min" />
      <div className="scroll flex flex-col px-6">
        <div className="rise flex flex-1 flex-col gap-3 py-2">
          {[
            { icon: Building2, label: "Legal entity name", val: "Volkmann Family Office" },
            { icon: User, label: "Authorised representative", val: "Jürgen Volkmann" },
            { icon: Mail, label: "Work email", val: "j.volkmann@vfo.example" },
          ].map((f) => {
            const Icon = f.icon;
            return (
              <label key={f.label} className="flex items-center gap-3 rounded-xl border border-hairline bg-surface px-4 py-3 focus-within:border-[color-mix(in_srgb,var(--color-accent)_55%,transparent)]">
                <Icon size={18} className="text-ink-mute" />
                <div className="flex-1">
                  <span className="block text-[11px] font-medium uppercase tracking-wide text-ink-mute">{f.label}</span>
                  <input defaultValue={f.val} className="w-full bg-transparent text-[15px] text-ink outline-none" />
                </div>
              </label>
            );
          })}

          <Card className="mt-2 p-4">
            <p className="text-[12px] font-semibold uppercase tracking-wide text-ink-mute">What you get</p>
            <ul className="mt-2 flex flex-col gap-2">
              {["Multi-fiat & crypto rails in one account", "Instant XRP-Ledger settlement", "Regulated, segregated custody"].map((b) => (
                <li key={b} className="flex items-center gap-2 text-[13px] text-ink-dim">
                  <Check size={15} style={{ color: "var(--color-pos)" }} /> {b}
                </li>
              ))}
            </ul>
          </Card>

          <label className="mt-1 flex items-start gap-2 px-1 text-[12px] text-ink-mute">
            <input type="checkbox" defaultChecked className="mt-0.5 accent-[var(--color-accent)]" />
            I agree to the Terms of Service and acknowledge the Privacy &amp; AML policy.
          </label>
        </div>

        <div className="pb-2">
          <Button href="/kyc" full>Continue to verification <ArrowRight size={17} /></Button>
          <p className="mt-3 text-center text-[14px] text-ink-mute">
            Already registered? <Link href="/login" className="font-semibold text-accent-2">Sign in</Link>
          </p>
        </div>
        <DemoTag />
      </div>
    </AppFrame>
  );
}
