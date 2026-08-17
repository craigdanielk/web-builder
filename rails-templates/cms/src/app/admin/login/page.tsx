import { loginAction } from "@/app/admin/actions";

export const metadata = { title: "{{BRAND_NAME}} CMS — Sign in" };

const NAVY = "#0d0e45";
const ORANGE = "#f47643";

const field: React.CSSProperties = {
  width: "100%",
  marginTop: 6,
  marginBottom: 16,
  padding: "11px 12px",
  borderRadius: 8,
  border: "1px solid #e7e5e4",
  fontSize: 14,
  boxSizing: "border-box",
};

const label: React.CSSProperties = { fontSize: 12, fontWeight: 600, color: "#44403c" };

export default async function AdminLogin({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string; revoked?: string; locked?: string }>;
}) {
  const sp = await searchParams;
  // Seconds remaining on a lockout (X-0135), rounded up to whole minutes for
  // display. Parsed rather than trusted: the value rides in the query string, so
  // a caller can put anything there. It only ever chooses wording.
  const lockedMinutes = Number(sp.locked) > 0 ? Math.ceil(Number(sp.locked) / 60) : 0;
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        background: `linear-gradient(180deg, ${NAVY} 0%, #141560 55%, ${NAVY} 100%)`,
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <div style={{ width: "100%", maxWidth: 380 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, justifyContent: "center", marginBottom: 24 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="{{LOGO_SRC}}" alt="{{BRAND_NAME}}" style={{ height: 30, width: "auto" }} />
          <span style={{ color: "#fff", fontSize: 16, fontWeight: 600 }}>Content Manager</span>
        </div>

        <form
          action={loginAction}
          style={{ padding: 32, background: "#fff", border: "1px solid #ece9e4", borderRadius: 14, boxShadow: "0 18px 44px -12px rgba(0,0,0,.45)" }}
        >
          <h1 style={{ fontSize: 20, fontWeight: 600, color: "#1c1917", margin: "0 0 4px" }}>Sign in</h1>
          <p style={{ fontSize: 13, color: "#78716c", margin: "0 0 20px" }}>
            Use your own email and password. Every change you publish is recorded against your name.
          </p>
          <input type="hidden" name="next" value={sp.next ?? "/admin"} />

          <label htmlFor="email" style={label}>Email</label>
          <input
            id="email"
            name="email"
            type="email"
            autoFocus
            required
            autoComplete="username"
            style={field}
          />

          <label htmlFor="password" style={label}>Password</label>
          <input
            id="password"
            name="password"
            type="password"
            required
            autoComplete="current-password"
            style={field}
          />

          {/* A revoked session is a different situation from a bad password, and
              telling someone "wrong password" when their access was removed sends
              them to reset a password that will never work. */}
          {sp.revoked ? (
            <p style={{ color: "#b45309", fontSize: 13, margin: "0 0 12px" }}>
              Your access to the Content Manager has been removed. Speak to whoever manages
              your team&apos;s access.
            </p>
          ) : null}
          {/* A lockout is a different situation again: the credentials may be
              perfectly correct and still be refused, so "wrong password" would
              send someone chasing a problem they do not have. Saying so leaks
              nothing — the counter is keyed on the address as SUBMITTED, so
              anyone can lock any string, including one with no account behind
              it, and the message therefore cannot distinguish the two. */}
          {lockedMinutes > 0 ? (
            <p style={{ color: "#b45309", fontSize: 13, margin: "0 0 12px" }}>
              Too many failed sign-in attempts. Try again in about{" "}
              {lockedMinutes} minute{lockedMinutes === 1 ? "" : "s"}.
            </p>
          ) : sp.error ? (
            <p style={{ color: "#dc2626", fontSize: 13, margin: "0 0 12px" }}>
              That email and password don&apos;t match an account. Check with whoever set up your access.
            </p>
          ) : null}

          <button
            type="submit"
            style={{ width: "100%", padding: "11px 12px", borderRadius: 8, border: "none", background: ORANGE, color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
          >
            Sign in
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: 12, color: "rgba(255,255,255,.55)", margin: "20px 0 0", lineHeight: 1.6 }}>
          Staff access only. Your session lasts 12 hours.
          <br />
          <a href="/" style={{ color: "rgba(255,255,255,.75)" }}>Back to {{CANONICAL_DOMAIN}}</a>
        </p>
      </div>
    </main>
  );
}
