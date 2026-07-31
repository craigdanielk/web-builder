"use client";
import { useState } from "react";
import Link from "next/link";
import { AppFrame } from "@/components/shell";
import { Wordmark, DemoTag } from "@/components/brand";
import { Button } from "@/components/primitives";
import { Fingerprint, Eye, EyeOff, ShieldCheck } from "lucide-react";

export default function Login() {
  const [show, setShow] = useState(false);
  return (
    <AppFrame nav={false}>
      <div className="scroll flex flex-col px-6">
        <div className="rise flex flex-1 flex-col justify-center gap-7 py-6" style={{ animationDelay: "40ms" }}>
          <div className="flex flex-col items-start gap-6">
            <Wordmark />
            <div>
              <h1 className="display text-[30px] leading-[1.1] text-ink">Welcome back.</h1>
              <p className="mt-1 text-[14px] text-ink-mute">Sign in to your institutional account.</p>
            </div>
          </div>

          <form className="flex flex-col gap-3" onSubmit={(e) => e.preventDefault()}>
            <Field label="Email">
              <input type="email" defaultValue="j.volkmann@vfo.example" autoComplete="username"
                className="w-full bg-transparent text-[15px] text-ink outline-none placeholder:text-ink-faint" />
            </Field>
            <Field label="Password" trailing={
              <button type="button" onClick={() => setShow((s) => !s)} aria-label="Toggle password" className="text-ink-mute">
                {show ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            }>
              <input type={show ? "text" : "password"} defaultValue="demo-passphrase" autoComplete="current-password"
                className="w-full bg-transparent text-[15px] text-ink outline-none" />
            </Field>

            <div className="flex items-center justify-between px-1 py-1 text-[13px]">
              <label className="flex items-center gap-2 text-ink-dim">
                <input type="checkbox" defaultChecked className="accent-[var(--color-accent)]" /> Keep me signed in
              </label>
              <Link href="/login" className="font-medium text-accent-2">Forgot?</Link>
            </div>

            <Button href="/kyc" full className="mt-1">Sign in</Button>

            <button type="button" className="flex items-center justify-center gap-2 py-3 text-[14px] font-medium text-ink-dim">
              <Fingerprint size={19} style={{ color: "var(--color-accent)" }} /> Use Face ID
            </button>
          </form>

          <div className="flex items-center gap-2 rounded-xl border border-hairline bg-surface px-3.5 py-3">
            <ShieldCheck size={18} style={{ color: "var(--color-pos)" }} />
            <p className="text-[12px] leading-snug text-ink-mute">
              Protected by 2-factor authentication and hardware-key support. Regulated & segregated custody.
            </p>
          </div>

          <p className="text-center text-[14px] text-ink-mute">
            New to Xago? <Link href="/signup" className="font-semibold text-accent-2">Open an account</Link>
          </p>
        </div>
        <DemoTag />
      </div>
    </AppFrame>
  );
}

function Field({ label, children, trailing }: { label: string; children: React.ReactNode; trailing?: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 rounded-xl border border-hairline bg-surface px-4 py-2.5 focus-within:border-[color-mix(in_srgb,var(--color-accent)_55%,transparent)]">
      <span className="text-[11px] font-medium uppercase tracking-wide text-ink-mute">{label}</span>
      <div className="flex items-center gap-2">{children}{trailing}</div>
    </label>
  );
}
