"use client";
import Link from "next/link";
import { cn } from "@/lib/ui";
import type { Asset } from "@/lib/mock";

/* ── Asset glyph ─────────────────────────────────────────── */
export function Glyph({ a, size = 40 }: { a: Pick<Asset, "symbol" | "accent" | "id">; size?: number }) {
  return (
    <span
      className="grid place-items-center rounded-full font-semibold shrink-0"
      style={{
        width: size,
        height: size,
        background: `color-mix(in srgb, ${a.accent} 55%, #0a0c10)`,
        border: `1px solid color-mix(in srgb, ${a.accent} 70%, transparent)`,
        fontSize: size * 0.42,
        color: "#f6f4f1",
      }}
    >
      {a.symbol}
    </span>
  );
}

/* ── Value delta ─────────────────────────────────────────── */
export function Delta({ v, className }: { v: number; className?: string }) {
  const pos = v >= 0;
  return (
    <span
      className={cn(
        "tnum inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[12px] font-medium",
        className
      )}
      style={{
        color: pos ? "var(--color-pos)" : "var(--color-neg)",
        background: pos ? "var(--color-pos-soft)" : "var(--color-neg-soft)",
      }}
    >
      {pos ? "▲" : "▼"} {Math.abs(v).toFixed(2)}%
    </span>
  );
}

/* ── Status pill ─────────────────────────────────────────── */
export function Pill({ status }: { status: "completed" | "pending" | "failed" | "active" | "paid" | "expired" }) {
  const map: Record<string, [string, string]> = {
    completed: ["var(--color-pos)", "var(--color-pos-soft)"],
    paid: ["var(--color-pos)", "var(--color-pos-soft)"],
    active: ["var(--color-accent-2)", "var(--color-accent-soft)"],
    pending: ["var(--color-warn)", "rgba(246,196,83,0.14)"],
    failed: ["var(--color-neg)", "var(--color-neg-soft)"],
    expired: ["var(--color-ink-mute)", "rgba(137,144,160,0.14)"],
  };
  const [c, bg] = map[status] ?? map.pending;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize"
      style={{ color: c, background: bg }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />
      {status}
    </span>
  );
}

/* ── Buttons ─────────────────────────────────────────────── */
export function Button({
  children, onClick, href, variant = "primary", full, className, type, disabled,
}: {
  children: React.ReactNode; onClick?: () => void; href?: string;
  variant?: "primary" | "ghost" | "soft" | "danger"; full?: boolean;
  className?: string; type?: "button" | "submit"; disabled?: boolean;
}) {
  const base = "inline-flex items-center justify-center gap-2 rounded-xl text-[15px] font-semibold h-12 px-5 transition active:scale-[0.98] disabled:opacity-40";
  const styles: Record<string, string> = {
    primary: "text-[#1a0f08] shadow-[0_8px_24px_-8px_rgba(244,118,67,0.6)]",
    soft: "text-ink border border-hairline-strong",
    ghost: "text-ink-dim",
    danger: "text-[#3a0d0d]",
  };
  const inline: React.CSSProperties =
    variant === "primary" ? { background: "linear-gradient(180deg,var(--color-accent-2),var(--color-accent))" }
    : variant === "danger" ? { background: "var(--color-neg)" }
    : variant === "soft" ? { background: "var(--color-surface-2)" }
    : {};
  const cls = cn(base, styles[variant], full && "w-full", className);
  if (href) return <Link href={href} className={cls} style={inline}>{children}</Link>;
  return <button type={type ?? "button"} onClick={onClick} disabled={disabled} className={cls} style={inline}>{children}</button>;
}

/* ── Card ────────────────────────────────────────────────── */
export function Card({ children, className, style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) {
  return (
    <div className={cn("rounded-2xl border border-hairline bg-surface shadow-[var(--shadow-card)]", className)} style={style}>
      {children}
    </div>
  );
}

/* ── Section heading ─────────────────────────────────────── */
export function SectionLabel({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-1">
      <h2 className="text-[12px] font-semibold uppercase tracking-[0.14em] text-ink-mute">{children}</h2>
      {action}
    </div>
  );
}

/* ── Sparkline ───────────────────────────────────────────── */
export function Spark({ data, up, w = 64, h = 24 }: { data: number[]; up: boolean; w?: number; h?: number }) {
  const min = Math.min(...data), max = Math.max(...data);
  const rng = max - min || 1;
  const pts = data.map((d, i) => `${(i / (data.length - 1)) * w},${h - ((d - min) / rng) * h}`).join(" ");
  const c = up ? "var(--color-pos)" : "var(--color-neg)";
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={c} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
