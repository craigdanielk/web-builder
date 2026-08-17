"use client";

// Upload control shared by the library page and the picker (task X-0112).
//
// There is exactly ONE upload path in this app: uploadMediaAction ->
// ingestUpload. This component wraps it and adds nothing — no second endpoint,
// no client-side resizing, no direct-to-bucket signed URL. That matters because
// ingestUpload is where the mime allowlist, the 15MB cap, the sharp
// normalisation and the checksum dedupe live; a second path would be a second
// set of rules, and the weaker one would win.

import { useRef, useState, useTransition } from "react";
import { uploadMediaAction } from "@/app/admin/media/actions";
import { ACCEPTED_MIME } from "@/lib/media/constants";
import type { AssetRef } from "@/lib/media/asset";

export type AssetUploadButtonProps = {
  /** Called with the stored asset. `deduped` means these exact bytes were already here. */
  onUploaded: (asset: AssetRef, deduped: boolean) => void;
  label?: string;
  /**
   * Replace mode: copy this asset's alt text and focal point onto the new one.
   * The old asset is NOT modified or deleted — storage paths are content-hashed
   * and cached for a year, so replacement is a new row by construction.
   */
  inheritFrom?: AssetRef | null;
  variant?: "primary" | "secondary";
  disabled?: boolean;
};

const ORANGE = "#f47643";
const ACCEPT = [...ACCEPTED_MIME].join(",");

export default function AssetUploadButton({
  onUploaded,
  label = "Upload an image",
  inheritFrom,
  variant = "primary",
  disabled,
}: AssetUploadButtonProps) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, start] = useTransition();

  function submit(file: File) {
    setError(null);
    const form = new FormData();
    form.set("file", file);
    if (inheritFrom) {
      form.set("inheritFrom", inheritFrom.id);
      form.set("inheritAlt", inheritFrom.alt);
      form.set("inheritFocalX", String(inheritFrom.focal_x));
      form.set("inheritFocalY", String(inheritFrom.focal_y));
    }
    start(async () => {
      const result = await uploadMediaAction(form);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      onUploaded(result.asset, result.deduped);
    });
  }

  const primary = variant === "primary";

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", gap: 6 }}>
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          // Reset first: picking the same file twice in a row fires no change
          // event otherwise, and the second attempt looks like a dead button.
          e.target.value = "";
          if (file) submit(file);
        }}
      />
      <button
        type="button"
        disabled={disabled || pending}
        onClick={() => input.current?.click()}
        style={{
          padding: "9px 16px",
          borderRadius: 8,
          border: primary ? "none" : "1px solid #d6d3d1",
          background: primary ? ORANGE : "#fff",
          color: primary ? "#fff" : "#44403c",
          fontSize: 13,
          fontWeight: 600,
          cursor: pending ? "progress" : "pointer",
          opacity: disabled || pending ? 0.65 : 1,
          whiteSpace: "nowrap",
        }}
      >
        {pending ? "Uploading…" : label}
      </button>
      {error ? (
        <p role="alert" style={{ margin: 0, fontSize: 12, color: "#dc2626", maxWidth: 280 }}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
