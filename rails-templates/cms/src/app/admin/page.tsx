import Link from "next/link";
import { EDITABLE_PAGES } from "@/lib/puck/pages";
import { GROUP_ORDER, metaFor } from "@/lib/puck/page-meta";
import AdminHeader from "@/components/admin/AdminHeader";
import { lastEditByPage, relativeTime } from "@/lib/cms-attribution";

export const metadata = { title: "{{BRAND_NAME}} CMS" };
export const dynamic = "force-dynamic";

const ORANGE = "#f47643";

export default async function AdminHome() {
  // Who touched what, last. Read once for the whole picker rather than per row.
  const lastEdits = await lastEditByPage();

  // Group the editable slugs for display; a slug with no PAGE_META entry still
  // shows (under "Other") rather than silently disappearing from the picker.
  const grouped = new Map<string, string[]>();
  for (const slug of EDITABLE_PAGES) {
    const g = metaFor(slug).group;
    grouped.set(g, [...(grouped.get(g) ?? []), slug]);
  }
  const groups = [
    ...GROUP_ORDER.filter((g) => grouped.has(g)).map((g) => [g, grouped.get(g)!] as const),
    ...[...grouped.entries()].filter(([g]) => !GROUP_ORDER.includes(g as never)),
  ];

  return (
    <main style={{ minHeight: "100vh", background: "#fafaf9", fontFamily: "Inter, system-ui, sans-serif" }}>
      <AdminHeader current="pages" />

      <div style={{ maxWidth: 880, margin: "0 auto", padding: "40px 24px 64px" }}>
        <h1 style={{ fontSize: 26, fontWeight: 600, color: "#1c1917", margin: 0 }}>Edit your website</h1>
        <p style={{ fontSize: 15, color: "#78716c", margin: "6px 0 32px", maxWidth: 560 }}>
          Choose a page to edit its text, images and sections. Changes appear on the live site as soon as you press
          Publish — no developer needed.
        </p>

        {groups.map(([group, slugs]) => (
          <section key={group} style={{ marginBottom: 36 }}>
            <h2 style={{ fontSize: 12, fontWeight: 700, color: "#a8a29e", textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 12px" }}>
              {group}
            </h2>
            <div style={{ display: "grid", gap: 10 }}>
              {slugs.map((slug) => {
                const m = metaFor(slug);
                const last = lastEdits.get(slug);
                return (
                  <div
                    key={slug}
                    style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, padding: "16px 18px", background: "#fff", border: "1px solid #ece9e4", borderRadius: 10 }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <p style={{ fontSize: 15, fontWeight: 600, color: "#1c1917", margin: 0 }}>{m.label}</p>
                      <p style={{ fontSize: 13, color: "#78716c", margin: "3px 0 0" }}>{m.description}</p>
                      {/* Only shown once an edit has actually been recorded. A page
                          nobody has touched says nothing rather than guessing. */}
                      {/* A write by a program says so. The alternative — falling
                          through to "Saved as draft" with no name — would tell an
                          editor a person had touched the page when none had. */}
                      {last ? (
                        <p style={{ fontSize: 12, color: "#a8a29e", margin: "6px 0 0" }}>
                          {last.source ? (
                            <>Written {relativeTime(last.at)} by {last.source}</>
                          ) : (
                            <>
                              {last.action === "publish" ? "Published" : "Saved as draft"} {relativeTime(last.at)}
                              {last.email ? ` by ${last.email}` : ""}
                            </>
                          )}
                        </p>
                      ) : null}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 14, flexShrink: 0 }}>
                      {m.route ? (
                        <a
                          href={m.route}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: 13, color: "#78716c", textDecoration: "none", whiteSpace: "nowrap" }}
                        >
                          View live ↗
                        </a>
                      ) : null}
                      <Link
                        href={`/admin/${slug}`}
                        style={{ padding: "8px 16px", borderRadius: 8, background: ORANGE, color: "#fff", fontSize: 13, fontWeight: 600, textDecoration: "none", whiteSpace: "nowrap" }}
                      >
                        Edit
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}

        <div style={{ padding: "16px 18px", background: "#fff", border: "1px solid #ece9e4", borderRadius: 10 }}>
          <p style={{ fontSize: 12, fontWeight: 700, color: "#a8a29e", textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 10px" }}>
            Good to know
          </p>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "#57534e", lineHeight: 1.65 }}>
            <li><strong>Clearing a field keeps it empty.</strong> An empty field is treated as intentional — it won&apos;t revert to the original text. Delete the section instead if you want it gone.</li>
            <li><strong>Publishing shows on the live site within seconds.</strong> Pages are cached for speed and refreshed the moment you Publish.</li>
            <li><strong>Unpublishing every block reverts the page to its built-in version</strong> — the site never shows a blank page.</li>
            <li><strong>Everyone signs in as themselves.</strong> Each change is recorded against the person who made it, and you can see who edited a page last on the cards above.</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
