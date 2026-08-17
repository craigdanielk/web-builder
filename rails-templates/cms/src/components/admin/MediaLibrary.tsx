"use client";

// MediaLibrary — the interactive half of /admin/media (task X-0112).
//
// Deliberately a CONSUMER of AssetGrid, the same component the picker renders.
// The library and the picker showing the same tiles is not a coincidence to be
// maintained by hand; it is one component used twice.
//
// The server component above passes the first page of assets, so the library is
// present in the initial HTML (which is also what the B4 oracle counts). Search
// and edits go back through server actions from here.

import { useEffect, useRef, useState, useTransition, type MouseEvent } from "react";
import { listAssetsAction, updateAssetAction } from "@/app/admin/media/actions";
import { assetLabel, focalPosition, formatBytes, type AssetRef } from "@/lib/media/asset";
import AssetGrid from "./AssetGrid";
import AssetUploadButton from "./AssetUploadButton";

const ORANGE = "#f47643";

export default function MediaLibrary({ initialAssets }: { initialAssets: AssetRef[] }) {
  const [assets, setAssets] = useState<AssetRef[]>(initialAssets);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const selected = assets.find((a) => a.id === selectedId) ?? null;

  // Debounced search against the server, not a client-side filter: the grid
  // shows the first 100 rows, so filtering in the browser would search a page
  // of the library and call it the library.
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const t = setTimeout(async () => {
      const result = await listAssetsAction(query);
      if (result.ok) {
        setAssets(result.assets);
        setListError(null);
      } else {
        setListError(result.error);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  function upsert(asset: AssetRef) {
    setAssets((prev) => {
      const i = prev.findIndex((a) => a.id === asset.id);
      if (i === -1) return [asset, ...prev];
      const next = [...prev];
      next[i] = asset;
      return next;
    });
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 340px", gap: 24, alignItems: "start" }}>
      <div style={{ minWidth: 0 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 18 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by file name or alt text"
            aria-label="Search images"
            style={{
              flex: 1,
              padding: "10px 12px",
              borderRadius: 8,
              border: "1px solid #e7e5e4",
              fontSize: 14,
              background: "#fff",
              boxSizing: "border-box",
            }}
          />
          <AssetUploadButton
            onUploaded={(asset, deduped) => {
              upsert(asset);
              setSelectedId(asset.id);
              if (deduped) setListError("That image was already in the library — showing the existing one.");
            }}
          />
        </div>

        {listError ? (
          <p role="status" style={{ fontSize: 13, color: "#92400e", background: "#fef3c7", padding: "8px 12px", borderRadius: 8, margin: "0 0 14px" }}>
            {listError}
          </p>
        ) : null}

        <AssetGrid
          assets={assets}
          selectedId={selectedId}
          onSelect={(a) => setSelectedId(a.id)}
          emptyMessage={
            query ? `Nothing matches “${query}”.` : "No images yet. Upload one to get started."
          }
        />

        <p style={{ fontSize: 12, color: "#a8a29e", margin: "16px 0 0" }}>
          {assets.length} {assets.length === 1 ? "image" : "images"}
          {query ? " matching your search" : " in the library"}
        </p>
      </div>

      <aside
        style={{
          position: "sticky",
          top: 24,
          background: "#fff",
          border: "1px solid #ece9e4",
          borderRadius: 12,
          padding: 18,
        }}
      >
        {selected ? (
          <AssetDetail key={selected.id} asset={selected} onSaved={upsert} />
        ) : (
          <>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: "#1c1917", margin: "0 0 8px" }}>
              Image details
            </h2>
            <p style={{ fontSize: 13, color: "#78716c", margin: 0, lineHeight: 1.6 }}>
              Select an image to edit its description, choose which part stays visible when it is
              cropped, or swap it for a new file.
            </p>
          </>
        )}
      </aside>
    </div>
  );
}

// ---------------------------------------------------------------------------

function AssetDetail({
  asset,
  onSaved,
}: {
  asset: AssetRef;
  onSaved: (asset: AssetRef) => void;
}) {
  const [alt, setAlt] = useState(asset.alt);
  const [focalX, setFocalX] = useState(asset.focal_x);
  const [focalY, setFocalY] = useState(asset.focal_y);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [pending, start] = useTransition();

  const dirty = alt !== asset.alt || focalX !== asset.focal_x || focalY !== asset.focal_y;

  function save() {
    setError(null);
    setSaved(false);
    start(async () => {
      const result = await updateAssetAction(asset.id, {
        alt,
        focal_x: focalX,
        focal_y: focalY,
      });
      if (!result.ok) {
        setError(result.error);
        return;
      }
      onSaved(result.asset);
      setSaved(true);
    });
  }

  /** Click the preview to say which point of the image must never be cropped out. */
  function pickFocal(e: MouseEvent<HTMLDivElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - box.left) / box.width));
    const y = Math.min(1, Math.max(0, (e.clientY - box.top) / box.height));
    setFocalX(Math.round(x * 100) / 100);
    setFocalY(Math.round(y * 100) / 100);
    setSaved(false);
  }

  return (
    <div>
      <h2 style={{ fontSize: 14, fontWeight: 600, color: "#1c1917", margin: "0 0 12px", wordBreak: "break-word" }}>
        {assetLabel(asset)}
      </h2>

      <div
        onClick={pickFocal}
        title="Click the part of the image that must stay visible"
        style={{
          position: "relative",
          width: "100%",
          aspectRatio: "4 / 3",
          borderRadius: 8,
          overflow: "hidden",
          background: "#f5f5f4",
          cursor: "crosshair",
          marginBottom: 8,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={asset.url}
          alt={alt}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: focalPosition(focalX, focalY),
            display: "block",
          }}
        />
        <span
          aria-hidden
          style={{
            position: "absolute",
            left: `${focalX * 100}%`,
            top: `${focalY * 100}%`,
            width: 16,
            height: 16,
            marginLeft: -8,
            marginTop: -8,
            borderRadius: "50%",
            border: "2px solid #fff",
            background: `${ORANGE}cc`,
            boxShadow: "0 0 0 1px rgba(0,0,0,.35)",
            pointerEvents: "none",
          }}
        />
      </div>
      <p
        data-focal-point={`${focalX},${focalY}`}
        style={{ fontSize: 11, color: "#a8a29e", margin: "0 0 16px" }}
      >
        Focal point {Math.round(focalX * 100)}% / {Math.round(focalY * 100)}% — click the image to
        move it. This decides what survives when a section crops the image.
      </p>

      <label htmlFor="asset-alt" style={{ fontSize: 12, fontWeight: 600, color: "#44403c" }}>
        Describe this image
      </label>
      <textarea
        id="asset-alt"
        data-asset-alt
        value={alt}
        onChange={(e) => {
          setAlt(e.target.value);
          setSaved(false);
        }}
        rows={3}
        placeholder="e.g. Mark Fitzjohn, Chief Operating Officer"
        style={{
          width: "100%",
          marginTop: 6,
          padding: "9px 11px",
          borderRadius: 8,
          border: "1px solid #e7e5e4",
          fontSize: 13,
          fontFamily: "inherit",
          resize: "vertical",
          boxSizing: "border-box",
        }}
      />
      <p style={{ fontSize: 11, color: "#78716c", margin: "6px 0 14px", lineHeight: 1.55 }}>
        Read aloud by screen readers and shown if the image fails to load. Describe what it shows,
        not that it is a photo.
      </p>

      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <button
          type="button"
          onClick={save}
          disabled={!dirty || pending}
          style={{
            padding: "9px 16px",
            borderRadius: 8,
            border: "none",
            background: ORANGE,
            color: "#fff",
            fontSize: 13,
            fontWeight: 600,
            cursor: dirty && !pending ? "pointer" : "default",
            opacity: dirty && !pending ? 1 : 0.5,
          }}
        >
          {pending ? "Saving…" : "Save changes"}
        </button>
        {saved && !dirty ? (
          <span role="status" style={{ fontSize: 12, color: "#15803d" }}>
            Saved
          </span>
        ) : null}
      </div>

      {error ? (
        <p role="alert" style={{ fontSize: 12, color: "#dc2626", margin: "0 0 14px" }}>
          {error}
        </p>
      ) : null}

      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "auto 1fr",
          gap: "4px 12px",
          fontSize: 11,
          color: "#78716c",
          margin: "0 0 16px",
          paddingTop: 14,
          borderTop: "1px solid #f5f5f4",
        }}
      >
        <dt>Size</dt>
        <dd style={{ margin: 0 }}>
          {asset.width && asset.height ? `${asset.width} × ${asset.height} · ` : ""}
          {formatBytes(asset.bytes)}
        </dd>
        <dt>Type</dt>
        <dd style={{ margin: 0 }}>{asset.mime}</dd>
        <dt>File</dt>
        <dd style={{ margin: 0, wordBreak: "break-all" }}>{asset.storage_path}</dd>
      </dl>

      <div style={{ paddingTop: 14, borderTop: "1px solid #f5f5f4" }}>
        <AssetUploadButton
          label="Replace with a new file"
          variant="secondary"
          inheritFrom={asset}
          onUploaded={(next) => onSaved(next)}
        />
        <p style={{ fontSize: 11, color: "#78716c", margin: "8px 0 0", lineHeight: 1.55 }}>
          A replacement is added as a new image and carries this description and focal point over.
          Pages already using the old image keep it until you point them at the new one — image
          files are cached for a year, so they are never overwritten in place.
        </p>
      </div>
    </div>
  );
}
