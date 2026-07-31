"use client";
import Link from "next/link";
import { AppFrame, AppHeader } from "@/components/shell";
import { Card, Button } from "@/components/primitives";
import { user } from "@/lib/mock";
import {
  BadgeCheck, Users, Link2, ShieldCheck, Bell, FileText, LifeBuoy,
  ChevronRight, LogOut, Fingerprint, Globe, Moon,
} from "lucide-react";

const groups = [
  {
    label: "Money", items: [
      { icon: Users, label: "Beneficiaries", href: "/beneficiaries", sub: "5 recipients" },
      { icon: Link2, label: "Payment links", href: "/payment-links", sub: "2 active" },
      { icon: FileText, label: "Statements & tax", href: "/activity", sub: "Export CSV / PDF" },
    ],
  },
  {
    label: "Security", items: [
      { icon: ShieldCheck, label: "Security centre", href: "/account", sub: "2FA · hardware key" },
      { icon: Fingerprint, label: "Biometric login", href: "/account", sub: "Face ID enabled", toggle: true },
      { icon: Bell, label: "Notifications", href: "/account", sub: "Push · email" },
    ],
  },
  {
    label: "Preferences", items: [
      { icon: Globe, label: "Base currency", href: "/account", sub: "USD" },
      { icon: Moon, label: "Appearance", href: "/account", sub: "Dark" },
      { icon: LifeBuoy, label: "Help centre", href: "/help", sub: "24/7 support" },
    ],
  },
];

export default function Account() {
  return (
    <AppFrame>
      <AppHeader title="Account" />
      <div className="scroll px-5 pb-6">
        <Card className="rise flex items-center gap-4 p-5">
          <span className="grid h-16 w-16 shrink-0 place-items-center rounded-full text-[22px] font-semibold text-ink"
            style={{ background: `color-mix(in srgb,${user.avatarTint} 45%,#0a0c10)`, border: `1px solid color-mix(in srgb,${user.avatarTint} 60%,transparent)` }}>
            {user.initials}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <p className="truncate text-[17px] font-semibold text-ink">{user.name}</p>
              <BadgeCheck size={16} style={{ color: "var(--color-pos)" }} />
            </div>
            <p className="truncate text-[13px] text-ink-mute">{user.company}</p>
            <span className="mt-1.5 inline-block rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ background: "var(--color-violet-soft)", color: "#b6a4ff" }}>
              {user.tier} · Tier {user.kycLevel}
            </span>
          </div>
        </Card>

        {!user.kycComplete && (
          <Link href="/kyc" className="mt-3 flex items-center justify-between rounded-2xl border p-3.5"
            style={{ borderColor: "color-mix(in srgb,var(--color-warn) 40%,transparent)", background: "rgba(246,196,83,0.10)" }}>
            <span className="text-[13px] font-medium text-ink">Complete verification · lift limits</span>
            <ChevronRight size={17} style={{ color: "var(--color-warn)" }} />
          </Link>
        )}

        {groups.map((g) => (
          <div key={g.label} className="mt-5">
            <p className="mb-2 px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">{g.label}</p>
            <Card className="divide-y divide-[var(--color-hairline)] p-1">
              {g.items.map((it) => {
                const Icon = it.icon;
                return (
                  <Link key={it.label} href={it.href} className="flex items-center gap-3 rounded-xl px-3 py-3 active:bg-surface-2">
                    <span className="grid h-9 w-9 place-items-center rounded-full bg-surface-2"><Icon size={17} className="text-ink-dim" /></span>
                    <div className="flex-1"><p className="text-[14px] font-medium text-ink">{it.label}</p><p className="text-[12px] text-ink-mute">{it.sub}</p></div>
                    {"toggle" in it && it.toggle
                      ? <span className="flex h-6 w-10 items-center rounded-full p-0.5" style={{ background: "var(--color-accent)" }}><span className="ml-auto h-5 w-5 rounded-full bg-white" /></span>
                      : <ChevronRight size={17} className="text-ink-mute" />}
                  </Link>
                );
              })}
            </Card>
          </div>
        ))}

        <Button href="/login" variant="soft" full className="mt-6"><LogOut size={16} /> Sign out</Button>
        <p className="mt-4 text-center text-[11px] text-ink-faint">Xago Exchange · mobile redesign prototype · mock data</p>
      </div>
    </AppFrame>
  );
}
