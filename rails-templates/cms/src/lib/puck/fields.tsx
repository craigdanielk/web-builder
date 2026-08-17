"use client";
import type { Field } from "@measured/puck";
import AssetPicker from "@/components/admin/AssetPicker";
import type { AssetRef } from "@/lib/media/asset";
import { isMediaRef, type MediaRef, type MediaValue } from "@/lib/puck/media";

// Field helpers to cut Puck config boilerplate for our section content shapes.

export const text = (label?: string): Field => ({ type: "text", label });
export const textarea = (label?: string): Field => ({ type: "textarea", label });

export const object = (objectFields: Record<string, Field>, label?: string): Field => ({
  type: "object",
  label,
  objectFields,
});

export const array = (
  arrayFields: Record<string, Field>,
  getItemSummary?: (item: Record<string, unknown>, i?: number) => string,
  label?: string,
): Field => ({
  type: "array",
  label,
  arrayFields,
  getItemSummary: getItemSummary as never,
});

// A CTA link: { label, href }
export const cta = (label = "Button"): Field =>
  object({ label: text("Label"), href: text("Link (href)") }, label);

// A boolean, edited as a Yes/No radio (keeps the content shape as a real
// boolean — e.g. pricing tier `featured`, feature `included`). Declaring it
// keeps Puck from dropping the field on Publish.
export const bool = (label = "Enabled"): Field =>
  ({ type: "radio", label, options: [{ label: "Yes", value: true }, { label: "No", value: false }] }) as Field;

// Edit a string[] as a newline-separated textarea (keeps the content shape as
// a plain array of strings, which Puck's native array field can't express).
export const stringList = (label = "Items"): Field =>
  ({
    type: "custom",
    label,
    render: ({ value, onChange }: { value?: string[]; onChange: (v: string[]) => void }) => (
      <div>
        <textarea
          defaultValue={(value ?? []).join("\n")}
          onBlur={(e) => onChange(e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))}
          rows={Math.max(3, (value ?? []).length + 1)}
          style={{ width: "100%", fontFamily: "inherit", fontSize: 13, padding: 8, borderRadius: 6, border: "1px solid var(--puck-color-grey-09)" }}
          placeholder="One item per line"
        />
        <small style={{ color: "var(--puck-color-grey-05)" }}>One item per line</small>
      </div>
    ),
  }) as Field;

// ---------------------------------------------------------------------------
// media() — a managed image, replacing every free-text image path (X-0111).
//
// Writes `{ assetId, alt }` and nothing else. The id is the only durable handle:
// the bucket path is derived from the file's checksum, so storing a URL would go
// stale the moment the image is replaced, which is the exact thing this field
// exists to let a non-developer do.
//
// Alt text is edited HERE rather than as a sibling `text("Alt")` field. Two
// fields that can disagree is how `logos[].image` + `logos[].alt` ended up able
// to describe different pictures; one value with the description inside it
// cannot. What is typed here is the PER-USAGE override — the asset's own alt in
// the library is the default, and the same headshot legitimately reads
// differently on a leadership grid than in an article.
//
// The decorative tick is worded as INTENT, not as an escape hatch: "Decorative
// image (screen readers skip it)" describes what the reader experiences, so an
// editor picks it because it is true. Labelling it "skip alt text" would make it
// the fast way past a validation error, and every image would end up decorative.
//
// The picker itself is not built here: it is components/admin/AssetPicker, built
// in X-0112 precisely so this field consumes it instead of growing a second one.
// ---------------------------------------------------------------------------
function MediaField({
  value,
  onChange,
  label,
}: {
  value?: MediaValue;
  onChange: (v: MediaRef | null) => void;
  label?: string;
}) {
  const ref = isMediaRef(value) ? value : null;
  // A legacy plain-string path from before X-0113. Shown, not silently dropped:
  // an editor opening the page must see what is on it today, and choosing an
  // image is what converts it.
  const legacy = typeof value === "string" && value ? value : null;

  const alt = ref?.alt ?? "";
  const decorative = ref?.decorative === true;
  const missingAlt = ref !== null && !decorative && alt.trim() === "";

  function pick(assetId: string | null, asset: AssetRef | null) {
    if (!assetId) return onChange(null);
    // Seed the override from the asset's own alt. That is copying the library's
    // description of this exact file, not writing one — nothing is invented.
    onChange(build(assetId, ref?.alt ?? asset?.alt ?? "", decorative));
  }

  /**
   * Assemble the stored value. `decorative` is written only when true, and
   * writing it always clears the alt: the contradictory state (both set) is a
   * save-time rejection, so the editor must not be able to construct it by
   * ticking a box on top of text they already typed.
   */
  function build(assetId: string, nextAlt: string, isDecorative: boolean): MediaRef {
    return isDecorative
      ? { assetId, alt: "", decorative: true }
      : { assetId, alt: nextAlt };
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <AssetPicker
        label={label}
        value={ref?.assetId ?? null}
        onChange={(id) => pick(id, null)}
        onAssetChange={(asset) => pick(asset?.id ?? null, asset)}
      />

      {legacy ? (
        <small style={{ color: "var(--puck-color-grey-05)" }}>
          Currently using the built-in file <code>{legacy}</code>. Choose an image to
          manage it here.
        </small>
      ) : null}

      {ref ? (
        <>
          <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "#44403c" }}>
              Alt text (describes this image here)
            </span>
            <input
              value={alt}
              disabled={decorative}
              onChange={(e) => onChange(build(ref.assetId, e.target.value, false))}
              placeholder={decorative ? "Not needed — screen readers skip this image" : "What does this image show?"}
              style={{
                width: "100%",
                padding: 8,
                fontFamily: "inherit",
                fontSize: 13,
                borderRadius: 6,
                border: `1px solid ${missingAlt ? "#dc2626" : "var(--puck-color-grey-09)"}`,
                background: decorative ? "var(--puck-color-grey-11, #f5f5f4)" : undefined,
                boxSizing: "border-box",
              }}
            />
            {missingAlt ? (
              <small style={{ color: "#dc2626" }}>
                Required — publishing is refused until this image is described.
              </small>
            ) : null}
          </label>

          <label style={{ display: "flex", alignItems: "flex-start", gap: 7, fontSize: 12, color: "#44403c" }}>
            <input
              type="checkbox"
              checked={decorative}
              onChange={(e) => onChange(build(ref.assetId, alt, e.target.checked))}
              style={{ marginTop: 2 }}
            />
            <span>
              Decorative image (screen readers skip it)
              <br />
              <small style={{ color: "var(--puck-color-grey-05)" }}>
                Tick only if the image adds nothing a reader would miss — an icon
                beside a heading that already says the same thing.
              </small>
            </span>
          </label>
        </>
      ) : null}
    </div>
  );
}

export const media = (label = "Image"): Field =>
  ({
    type: "custom",
    label,
    render: ({ value, onChange }: { value?: MediaValue; onChange: (v: MediaRef | null) => void }) => (
      <MediaField value={value} onChange={onChange} label={label} />
    ),
  }) as Field;
