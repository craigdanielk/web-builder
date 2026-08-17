"use client";

// AssetGrid — the thumbnail grid, shared by the library page and the picker
// (task X-0112).
//
// Presentational on purpose: it holds no data-loading and no selection state, so
// the same component renders inside /admin/media and inside a Puck MediaField
// modal (X-0111) without either one inheriting the other's behaviour.
//
// Thumbnails are plain <img>, not next/image. next/image would route every
// admin thumbnail through Vercel's transform pipeline — a billed transform per
// tile, per size, for pixels only staff ever see — and it would additionally
// refuse the SVG assets the pipeline deliberately stores byte-for-byte.

import { assetLabel, focalPosition, type AssetRef } from "@/lib/media/asset";

export type AssetGridProps = {
  assets: AssetRef[];
  /** id of the currently selected asset, if any. */
  selectedId?: string | null;
  onSelect: (asset: AssetRef) => void;
  /** Shown in place of the grid when `assets` is empty. */
  emptyMessage?: string;
  /** Minimum tile width in px; the grid auto-fills to the container. */
  tileSize?: number;
};

const ORANGE = "#f47643";

export default function AssetGrid({
  assets,
  selectedId,
  onSelect,
  emptyMessage = "No images yet.",
  tileSize = 140,
}: AssetGridProps) {
  if (assets.length === 0) {
    return (
      <p
        data-asset-grid-empty
        style={{ fontSize: 14, color: "#78716c", padding: "28px 0", margin: 0 }}
      >
        {emptyMessage}
      </p>
    );
  }

  return (
    <div
      data-asset-grid
      data-asset-count={assets.length}
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(auto-fill, minmax(${tileSize}px, 1fr))`,
        gap: 12,
      }}
    >
      {assets.map((asset) => {
        const selected = asset.id === selectedId;
        return (
          <button
            key={asset.id}
            type="button"
            // The oracle (B4) counts these to compare the rendered library
            // against `select count(*) from cms_assets`. Renaming the attribute
            // breaks scripts/verify/tierb-media-library.mjs.
            data-asset-id={asset.id}
            onClick={() => onSelect(asset)}
            title={assetLabel(asset)}
            aria-pressed={selected}
            style={{
              display: "block",
              padding: 0,
              cursor: "pointer",
              background: "#fff",
              border: `2px solid ${selected ? ORANGE : "#ece9e4"}`,
              borderRadius: 10,
              overflow: "hidden",
              textAlign: "left",
              boxShadow: selected ? `0 0 0 3px ${ORANGE}22` : "none",
            }}
          >
            <span
              style={{
                display: "block",
                position: "relative",
                width: "100%",
                aspectRatio: "4 / 3",
                background: "#f5f5f4",
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={asset.url}
                // The asset's own alt is the right text here: this IS the image,
                // not a usage of it. Empty alt on a decorative-by-record asset
                // stays empty — see the contract note on carried provenance.
                alt={asset.alt}
                loading="lazy"
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  objectPosition: focalPosition(asset.focal_x, asset.focal_y),
                  display: "block",
                }}
              />
              {!asset.alt ? (
                <span
                  title="No alt text — screen readers announce nothing for this image"
                  style={{
                    position: "absolute",
                    top: 6,
                    right: 6,
                    padding: "2px 6px",
                    borderRadius: 5,
                    background: "rgba(220,38,38,.92)",
                    color: "#fff",
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: "0.03em",
                  }}
                >
                  NO ALT
                </span>
              ) : null}
            </span>
            <span
              style={{
                display: "block",
                padding: "7px 9px 8px",
                fontSize: 11,
                color: "#57534e",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {assetLabel(asset)}
            </span>
          </button>
        );
      })}
    </div>
  );
}
