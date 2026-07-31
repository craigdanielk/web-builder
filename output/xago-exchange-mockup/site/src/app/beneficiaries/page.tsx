"use client";
import Link from "next/link";
import { AppFrame, AppHeader } from "@/components/shell";
import { Card, Button } from "@/components/primitives";
import { beneficiaries } from "@/lib/mock";
import { Plus, Star, BadgeCheck, ShieldAlert, ChevronRight, Send } from "lucide-react";

export default function Beneficiaries() {
  const favs = beneficiaries.filter((b) => b.fav);
  const rest = beneficiaries.filter((b) => !b.fav);
  return (
    <AppFrame>
      <AppHeader title="Beneficiaries" subtitle={`${beneficiaries.length} saved recipients`} back="/account"
        right={<Link href="/beneficiaries" aria-label="Add" className="grid h-9 w-9 place-items-center rounded-full text-[#1a0f08]" style={{ background: "linear-gradient(180deg,var(--color-accent-2),var(--color-accent))" }}><Plus size={18} /></Link>} />
      <div className="scroll px-5 pb-6">
        {favs.length > 0 && (
          <>
            <p className="mb-2 px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">Favourites</p>
            <div className="grid grid-cols-2 gap-2.5">
              {favs.map((b) => (
                <Card key={b.id} className="rise flex flex-col items-center gap-2 p-4 text-center">
                  <Avatar b={b} />
                  <div>
                    <p className="text-[14px] font-semibold text-ink">{b.name}</p>
                    <p className="tnum text-[11px] text-ink-mute">{b.network}</p>
                  </div>
                  <Link href="/transact" className="mt-1 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] font-semibold text-[#1a0f08]" style={{ background: "linear-gradient(180deg,var(--color-accent-2),var(--color-accent))" }}>
                    <Send size={13} /> Send
                  </Link>
                </Card>
              ))}
            </div>
          </>
        )}

        <p className="mb-2 mt-5 px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">All recipients</p>
        <Card className="divide-y divide-[var(--color-hairline)] p-1">
          {rest.map((b) => (
            <Link key={b.id} href="/transact" className="flex items-center gap-3 rounded-xl px-3 py-3 active:bg-surface-2">
              <Avatar b={b} size={40} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <p className="truncate text-[14px] font-semibold text-ink">{b.name}</p>
                  {b.verified ? <BadgeCheck size={15} style={{ color: "var(--color-pos)" }} /> : <ShieldAlert size={15} style={{ color: "var(--color-warn)" }} />}
                </div>
                <p className="tnum text-[12px] text-ink-mute">{b.handle} · {b.network}</p>
              </div>
              <ChevronRight size={18} className="text-ink-mute" />
            </Link>
          ))}
        </Card>

        <Button href="/transact" variant="soft" full className="mt-5"><Plus size={17} /> Add new beneficiary</Button>
      </div>
    </AppFrame>
  );
}

function Avatar({ b, size = 48 }: { b: { initials: string; tint: string; fav?: boolean }; size?: number }) {
  return (
    <span className="relative grid shrink-0 place-items-center rounded-full font-semibold text-ink"
      style={{ width: size, height: size, fontSize: size * 0.36, background: `color-mix(in srgb,${b.tint} 45%,#0a0c10)`, border: `1px solid color-mix(in srgb,${b.tint} 60%,transparent)` }}>
      {b.initials}
      {b.fav && <Star size={12} className="absolute -right-0.5 -top-0.5 fill-current" style={{ color: "var(--color-accent)" }} />}
    </span>
  );
}
