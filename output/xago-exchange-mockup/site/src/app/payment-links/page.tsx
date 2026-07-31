"use client";
import Link from "next/link";
import { AppFrame, AppHeader } from "@/components/shell";
import { Card, Pill, Button } from "@/components/primitives";
import { paymentLinks, assetById, fmtAsset } from "@/lib/mock";
import { Plus, Link2, Eye, Copy, QrCode } from "lucide-react";

export default function PaymentLinks() {
  return (
    <AppFrame>
      <AppHeader title="Payment links" subtitle="Request & receive funds" back="/account"
        right={<Link href="/payment-links" aria-label="New link" className="grid h-9 w-9 place-items-center rounded-full text-[#1a0f08]" style={{ background: "linear-gradient(180deg,var(--color-accent-2),var(--color-accent))" }}><Plus size={18} /></Link>} />
      <div className="scroll px-5 pb-6">
        {/* Receive hero */}
        <Card className="rise flex items-center gap-4 p-5">
          <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-white p-2">
            <QrCode size={48} className="text-[#0a0c10]" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[14px] font-semibold text-ink">Your receive address</p>
            <p className="tnum truncate text-[12px] text-ink-mute">xago.io/pay/volkmann-fo</p>
            <div className="mt-2 flex gap-2">
              <button className="flex items-center gap-1.5 rounded-full bg-surface-2 px-3 py-1.5 text-[12px] font-medium text-ink-dim"><Copy size={13} /> Copy</button>
              <button className="flex items-center gap-1.5 rounded-full bg-surface-2 px-3 py-1.5 text-[12px] font-medium text-ink-dim"><Link2 size={13} /> Share</button>
            </div>
          </div>
        </Card>

        <p className="mb-2 mt-5 px-1 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">Active & recent</p>
        <div className="flex flex-col gap-2.5">
          {paymentLinks.map((l) => {
            const a = assetById(l.asset)!;
            return (
              <Card key={l.id} className="flex items-center gap-3 p-4">
                <span className="grid h-11 w-11 place-items-center rounded-full" style={{ background: "var(--color-accent-soft)" }}>
                  <Link2 size={18} style={{ color: "var(--color-accent)" }} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-semibold text-ink">{l.title}</p>
                  <p className="tnum text-[12px] text-ink-mute">
                    {l.amount != null ? `${fmtAsset(l.amount, a)} ${l.asset}` : `Open · ${l.asset}`} · <Eye size={11} className="inline" /> {l.views}
                  </p>
                </div>
                <Pill status={l.status} />
              </Card>
            );
          })}
        </div>

        <Button href="/payment-links" full className="mt-5"><Plus size={17} /> Create payment link</Button>
      </div>
    </AppFrame>
  );
}
