"use client";

import { useState } from "react";
import { Puck, createUsePuck, type Data } from "@measured/puck";
import "@measured/puck/puck.css";
import { CONFIGS } from "@/lib/puck/config";
import { stripHydratedAssets } from "@/lib/puck/media";
import { savePageAction } from "@/app/admin/actions";

const usePuck = createUsePuck();

// Custom header buttons that read the live Puck data and call the mutation
// directly — not reliant on Puck's built-in Publish button wiring.
function HeaderButtons({ page }: { page: string }) {
  const data = usePuck((s) => s.appState.data) as Data;
  const [status, setStatus] = useState("");

  async function save(publish: boolean) {
    setStatus(publish ? "Publishing…" : "Saving draft…");
    try {
      // Drop the render-only `asset` rows that page.tsx hydrated in, so the
      // editor writes back the id-only shape it was given. savePageAction keeps
      // an item's props wholesale (it strips only Puck's `id` and `editMode`),
      // so anything left here is persisted verbatim — see stripHydratedAssets.
      const content = stripHydratedAssets(data.content) as {
        type: string;
        props?: Record<string, unknown>;
      }[];

      const res = await savePageAction(page, content, publish);
      setStatus(res.ok ? `${publish ? "Published" : "Draft saved"} · ${res.count} sections` : `Error: ${res.error}`);
    } catch (e) {
      setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  const btn = (bg: string): React.CSSProperties => ({
    padding: "8px 16px", borderRadius: 8, border: "none", background: bg, color: "#fff",
    fontSize: 13, fontWeight: 600, cursor: "pointer",
  });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      {status ? <span style={{ fontSize: 13, color: "#57534e" }}>{status}</span> : null}
      <a href="/admin" style={{ fontSize: 13, color: "#57534e", textDecoration: "none" }}>Exit</a>
      <button style={btn("#78716c")} onClick={() => save(false)}>Save draft</button>
      <button style={btn("#f47643")} onClick={() => save(true)}>Publish</button>
    </div>
  );
}

export default function Editor({ page, data }: { page: string; data: Data }) {
  const config = CONFIGS[page];
  return (
    <Puck
      config={config}
      data={data}
      headerTitle={`Editing: ${page}`}
      overrides={{ headerActions: () => <HeaderButtons page={page} /> }}
    />
  );
}
