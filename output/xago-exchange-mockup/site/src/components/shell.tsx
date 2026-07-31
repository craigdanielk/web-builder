"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/ui";
import {
  Home, Wallet, ArrowLeftRight, Receipt, User, ArrowLeft, Bell,
} from "lucide-react";

/* Device status bar — sells the "real phone" feel for the demo */
export function StatusBar() {
  return (
    <div className="flex items-center justify-between px-6 pt-3 pb-1 text-[13px] font-semibold tracking-tight text-ink">
      <span className="tnum">9:41</span>
      <div className="flex items-center gap-1.5">
        <svg width="17" height="11" viewBox="0 0 17 11" fill="none"><rect x="0" y="6" width="3" height="5" rx="1" fill="currentColor"/><rect x="4.5" y="4" width="3" height="7" rx="1" fill="currentColor"/><rect x="9" y="2" width="3" height="9" rx="1" fill="currentColor"/><rect x="13.5" y="0" width="3" height="11" rx="1" fill="currentColor" opacity="0.4"/></svg>
        <svg width="16" height="11" viewBox="0 0 16 11" fill="none"><path d="M8 2.5C10 2.5 11.7 3.2 13 4.4L14.2 3.1C12.6 1.5 10.4 0.6 8 0.6S3.4 1.5 1.8 3.1L3 4.4C4.3 3.2 6 2.5 8 2.5Z" fill="currentColor"/><path d="M8 5.4C9 5.4 9.9 5.8 10.5 6.4L8 9 5.5 6.4C6.1 5.8 7 5.4 8 5.4Z" fill="currentColor"/></svg>
        <div className="ml-0.5 flex items-center gap-0.5">
          <div className="h-[11px] w-[22px] rounded-[3px] border border-ink/40 p-[1.5px]"><div className="h-full w-[75%] rounded-[1px] bg-ink" /></div>
        </div>
      </div>
    </div>
  );
}

const NAV = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/wallets", label: "Wallets", icon: Wallet },
  { href: "/transact", label: "Transact", icon: ArrowLeftRight, center: true },
  { href: "/activity", label: "Activity", icon: Receipt },
  { href: "/account", label: "Account", icon: User },
];

export function BottomNav() {
  const path = usePathname();
  return (
    <nav className="relative z-20 border-t border-hairline bg-[color-mix(in_srgb,var(--color-canvas)_86%,transparent)] backdrop-blur-xl px-2 pb-[max(10px,env(safe-area-inset-bottom))] pt-2">
      <ul className="flex items-end justify-around">
        {NAV.map(({ href, label, icon: Icon, center }) => {
          const active = path === href || path.startsWith(href + "/");
          if (center)
            return (
              <li key={href} className="-mt-6">
                <Link href={href} aria-label={label} className="flex flex-col items-center gap-1">
                  <span className="grid h-14 w-14 place-items-center rounded-2xl text-[#1a0f08] shadow-[0_10px_28px_-8px_rgba(244,118,67,0.7)]"
                    style={{ background: "linear-gradient(180deg,var(--color-accent-2),var(--color-accent))" }}>
                    <Icon size={24} strokeWidth={2.4} />
                  </span>
                  <span className="text-[10px] font-medium text-ink-mute">{label}</span>
                </Link>
              </li>
            );
          return (
            <li key={href}>
              <Link href={href} aria-label={label}
                className="flex min-w-[56px] flex-col items-center gap-1 py-1.5">
                <Icon size={22} strokeWidth={active ? 2.5 : 1.9} style={{ color: active ? "var(--color-accent)" : "var(--color-ink-mute)" }} />
                <span className="text-[10px] font-medium" style={{ color: active ? "var(--color-ink)" : "var(--color-ink-faint)" }}>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/* Top app header used inside authed screens */
export function AppHeader({ title, back, right, subtitle }: { title: string; back?: string; right?: React.ReactNode; subtitle?: string }) {
  return (
    <header className="flex items-center gap-3 px-5 pb-3 pt-1">
      {back && (
        <Link href={back} aria-label="Back" className="grid h-9 w-9 place-items-center rounded-full border border-hairline bg-surface text-ink-dim active:scale-95">
          <ArrowLeft size={18} />
        </Link>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="display truncate text-[19px] leading-tight text-ink">{title}</h1>
        {subtitle && <p className="truncate text-[12px] text-ink-mute">{subtitle}</p>}
      </div>
      {right}
    </header>
  );
}

export function BellButton() {
  return (
    <Link href="/activity" aria-label="Notifications" className="relative grid h-9 w-9 place-items-center rounded-full border border-hairline bg-surface text-ink-dim active:scale-95">
      <Bell size={17} />
      <span className="absolute right-2 top-2 h-2 w-2 rounded-full" style={{ background: "var(--color-accent)" }} />
    </Link>
  );
}

/* Frame: device viewport + optional bottom nav. Screens compose their own scroll area. */
export function AppFrame({ children, nav = true }: { children: React.ReactNode; nav?: boolean }) {
  return (
    <div className="viewport">
      <div className="device">
        <StatusBar />
        {children}
        {nav && <BottomNav />}
      </div>
    </div>
  );
}
