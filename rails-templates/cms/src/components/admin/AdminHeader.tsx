import Link from "next/link";
import { logoutAction } from "@/app/admin/actions";

// The /admin chrome, in one place (task X-0181).
//
// It was copied inline into every admin page, which is how "Your password" and
// "Legal documents" could be added to one screen and be invisible from the
// others — a link nobody can find is the same as a feature that does not exist,
// and that is precisely how the 7 statutory documents went unnoticed.

const NAVY = "#0d0e45";

export type AdminNavKey = "pages" | "legal" | "leads" | "editors" | "account";

const LINKS: { key: AdminNavKey; href: string; label: string }[] = {{ADMIN_NAV_LINKS}};

export default function AdminHeader({ current }: { current: AdminNavKey }) {
  return (
    <header style={{ background: NAVY, padding: "20px 24px" }}>
      <div style={{ maxWidth: 880, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
        <Link href="/admin" style={{ display: "flex", alignItems: "center", gap: 12, textDecoration: "none" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" style={{ height: 26, width: "auto" }} />
          <span style={{ color: "#fff", fontSize: 15, fontWeight: 600, letterSpacing: "0.01em" }}>Content Manager</span>
        </Link>
        <nav style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          {LINKS.map((l) => (
            <Link
              key={l.key}
              href={l.href}
              aria-current={l.key === current ? "page" : undefined}
              style={{
                color: l.key === current ? "#fff" : "rgba(255,255,255,.75)",
                fontSize: 13,
                fontWeight: l.key === current ? 600 : 400,
                textDecoration: "none",
              }}
            >
              {l.label}
            </Link>
          ))}
          <form action={logoutAction}>
            <button style={{ padding: "8px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,.25)", background: "rgba(255,255,255,.08)", color: "#fff", fontSize: 13, fontWeight: 500, cursor: "pointer" }}>
              Sign out
            </button>
          </form>
        </nav>
      </div>
    </header>
  );
}
