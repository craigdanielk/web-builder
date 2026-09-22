import type { ReactNode } from "react"

export default function PageCopy({
  kicker,
  title,
  children,
}: {
  kicker: string
  title: string
  children: ReactNode
}) {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#0c8558]">{kicker}</p>
      <h1 className="mt-3 text-5xl">{title}</h1>
      <div className="mt-8 space-y-4 text-lg leading-relaxed text-[#29332f]">{children}</div>
    </main>
  )
}
