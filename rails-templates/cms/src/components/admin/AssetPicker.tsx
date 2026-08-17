"use client";

// AssetPicker — choose an image from the library (task X-0112).
//
// Built here, in the library task, and NOT inlined into /admin/media, because
// X-0111 (MediaField for Puck) consumes exactly this component at six field
// sites. That is the whole reason X-0112 runs before X-0111: the picker is the
// expensive half of MediaField, and building it twice is how the two drift.
//
// Consequences of that contract, which are why this file looks the way it does:
//   - it loads its OWN data through a server action. A Puck field renders deep
//     inside a client tree with no server component above it to pass props down,
//     so a picker that required `assets` as a prop could not be used there.
//   - it is uncontrolled with respect to the library: `value` is an asset id,
//     the only thing a cms_blocks row should store.
//   - it renders a trigger, not a layout. The caller owns the surrounding form.

import { useCallback, useEffect, useRef, useState } from "react";
import { listAssetsAction } from "@/app/admin/media/actions";
import { assetLabel, focalPosition, type AssetRef } from "@/lib/media/asset";
import AssetGrid from "./AssetGrid";
import AssetUploadButton from "./AssetUploadButton";

export type AssetPickerProps = {
  /** `cms_assets.id` of the current selection, or null/undefined for none. */
  value?: string | null;

  /** Fires with the new id (null when cleared). This is what the caller persists. */
  onChange: (assetId: string | null) => void;

  /**
   * Fires alongside `onChange` with the whole row. Optional, for callers that
   * need more than the id — e.g. seeding a per-usage alt override from the
   * asset's default, or reading width/height for a layout decision.
   */
  onAssetChange?: (asset: AssetRef | null) => void;

  /** Allow uploading a new image from inside the picker. Default true. */
  allowUpload?: boolean;

  /** Allow clearing the selection back to null. Default true. */
  allowClear?: boolean;

  /** Field label rendered above the trigger. Omit for no label. */
  label?: string;

  /**
   * The already-known row for `value`. Purely an optimisation: it renders the
   * thumbnail on first paint instead of after the list round-trip. Safe to omit.
   */
  initialAsset?: AssetRef | null;

  disabled?: boolean;
};

const ORANGE = "#f47643";
const NAVY = "#0d0e45";

export default function AssetPicker({
  value,
  onChange,
  onAssetChange,
  allowUpload = true,
  allowClear = true,
  label,
  initialAsset,
  disabled,
}: AssetPickerProps) {
  const [open, setOpen] = useState(false);
  const [assets, setAssets] = useState<AssetRef[]>(initialAsset ? [initialAsset] : []);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadedOnce, setLoadedOnce] = useState(false);

  const selected = assets.find((a) => a.id === value) ?? (initialAsset?.id === value ? initialAsset : null);

  const load = useCallback(async (q: string) => {
    setLoading(true);
    setError(null);
    const result = await listAssetsAction(q);
    setLoading(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    setAssets(result.assets);
    setLoadedOnce(true);
  }, []);

  // Resolve `value` to a row even before the modal is opened, so the trigger can
  // show what is currently chosen rather than a bare uuid.
  useEffect(() => {
    if (!loadedOnce && value && !selected) void load("");
  }, [load, loadedOnce, selected, value]);

  useEffect(() => {
    if (open && !loadedOnce) void load("");
  }, [load, loadedOnce, open]);

  // Debounced search. 250ms is below the threshold where typing feels laggy and
  // high enough that a six-character query is one request, not six.
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!open) return;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void load(query), 250);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [load, open, query]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  function commit(asset: AssetRef | null) {
    onChange(asset?.id ?? null);
    onAssetChange?.(asset);
    setOpen(false);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {label ? (
        <span style={{ fontSize: 12, fontWeight: 600, color: "#44403c" }}>{label}</span>
      ) : null}

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button
          type="button"
          disabled={disabled}
          onClick={() => setOpen(true)}
          data-asset-picker-trigger
          data-asset-value={value ?? ""}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: selected ? 6 : "9px 14px",
            borderRadius: 8,
            border: "1px solid #d6d3d1",
            background: "#fff",
            cursor: disabled ? "not-allowed" : "pointer",
            fontSize: 13,
            color: "#44403c",
            minWidth: 0,
          }}
        >
          {selected ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={selected.url}
                alt=""
                style={{
                  width: 44,
                  height: 44,
                  objectFit: "cover",
                  objectPosition: focalPosition(selected.focal_x, selected.focal_y),
                  borderRadius: 5,
                  background: "#f5f5f4",
                  flexShrink: 0,
                }}
              />
              <span style={{ display: "grid", textAlign: "left", minWidth: 0 }}>
                <span
                  style={{
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    maxWidth: 180,
                  }}
                >
                  {assetLabel(selected)}
                </span>
                <span style={{ fontSize: 11, color: selected.alt ? "#78716c" : "#dc2626" }}>
                  {selected.alt ? selected.alt : "No alt text"}
                </span>
              </span>
            </>
          ) : (
            <span>Choose an image…</span>
          )}
        </button>

        {allowClear && value ? (
          <button
            type="button"
            onClick={() => commit(null)}
            style={{
              padding: "7px 11px",
              borderRadius: 8,
              border: "1px solid #e7e5e4",
              background: "#fff",
              color: "#78716c",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            Remove
          </button>
        ) : null}
      </div>

      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Choose an image"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "rgba(13,14,69,.55)",
            display: "grid",
            placeItems: "center",
            padding: 24,
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 820,
              maxHeight: "82vh",
              display: "flex",
              flexDirection: "column",
              background: "#fafaf9",
              borderRadius: 14,
              overflow: "hidden",
              boxShadow: "0 24px 60px -12px rgba(0,0,0,.5)",
              fontFamily: "Inter, system-ui, sans-serif",
            }}
          >
            <div
              style={{
                background: NAVY,
                padding: "14px 18px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <span style={{ color: "#fff", fontSize: 14, fontWeight: 600 }}>Choose an image</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                style={{
                  padding: "6px 12px",
                  borderRadius: 7,
                  border: "1px solid rgba(255,255,255,.25)",
                  background: "rgba(255,255,255,.08)",
                  color: "#fff",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 12,
                padding: "14px 18px",
                borderBottom: "1px solid #ece9e4",
                background: "#fff",
              }}
            >
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by file name or alt text"
                style={{
                  flex: 1,
                  padding: "9px 12px",
                  borderRadius: 8,
                  border: "1px solid #e7e5e4",
                  fontSize: 13,
                  boxSizing: "border-box",
                }}
              />
              {allowUpload ? (
                <AssetUploadButton
                  label="Upload"
                  onUploaded={(asset) => commit(asset)}
                />
              ) : null}
            </div>

            <div style={{ padding: 18, overflowY: "auto" }}>
              {error ? (
                <p role="alert" style={{ fontSize: 13, color: "#dc2626", margin: "0 0 12px" }}>
                  {error}
                </p>
              ) : null}
              {loading && assets.length === 0 ? (
                <p style={{ fontSize: 13, color: "#78716c", margin: 0 }}>Loading…</p>
              ) : (
                <AssetGrid
                  assets={assets}
                  selectedId={value}
                  onSelect={commit}
                  emptyMessage={
                    query
                      ? `Nothing matches “${query}”.`
                      : "The library is empty. Upload an image to get started."
                  }
                  tileSize={128}
                />
              )}
            </div>

            <div
              style={{
                padding: "10px 18px",
                borderTop: "1px solid #ece9e4",
                background: "#fff",
                fontSize: 12,
                color: "#78716c",
              }}
            >
              Click an image to use it. Manage alt text and cropping in{" "}
              <a href="/admin/media" style={{ color: ORANGE }}>
                the image library
              </a>
              .
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
