export function Wordmark({ size = 30 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2" aria-label="Xago">
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
        <rect width="32" height="32" rx="9" fill="url(#xg)" />
        <path d="M9 9l14 14M23 9L9 23" stroke="#1a0f08" strokeWidth="3.2" strokeLinecap="round" />
        <defs>
          <linearGradient id="xg" x1="0" y1="0" x2="32" y2="32">
            <stop stopColor="#ff9d6b" /><stop offset="1" stopColor="#f47643" />
          </linearGradient>
        </defs>
      </svg>
      <span className="display text-[22px] tracking-tight text-ink">xago</span>
    </span>
  );
}

export function DemoTag() {
  return (
    <div className="flex items-center justify-center gap-1.5 pb-3 pt-1 text-[10px] font-medium uppercase tracking-[0.18em] text-ink-faint">
      <span className="h-1 w-1 rounded-full" style={{ background: "var(--color-accent)" }} />
      Prototype · mock data · not the production app
    </div>
  );
}
