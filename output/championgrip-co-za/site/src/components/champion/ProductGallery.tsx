"use client";

import { useState } from "react";
import Image from "next/image";

export type GalleryImage = {
  url: string;
  altText: string | null;
  width?: number;
  height?: number;
};

export function ProductGallery({
  images,
  title,
}: {
  images: GalleryImage[];
  title: string;
}) {
  const [active, setActive] = useState(0);
  const current = images[active] ?? images[0];
  if (!current) return null;

  return (
    <div className="cg-pdp-gallery" aria-label="Product gallery">
      <figure className="cg-pdp-stage">
        <Image
          key={current.url}
          src={current.url}
          alt={current.altText ?? title}
          width={current.width ?? 900}
          height={current.height ?? 1100}
          priority
          className="cg-pdp-stage-img"
        />
      </figure>
      {images.length > 1 ? (
        <ul className="cg-pdp-thumbs" role="list">
          {images.map((img, i) => {
            const selected = i === active;
            return (
              <li key={`${img.url}-${i}`}>
                <button
                  type="button"
                  className={`cg-pdp-thumb${selected ? " is-active" : ""}`}
                  aria-label={`View image ${i + 1}`}
                  aria-current={selected ? "true" : undefined}
                  onClick={() => setActive(i)}
                >
                  <Image
                    src={img.url}
                    alt=""
                    width={96}
                    height={96}
                    aria-hidden
                  />
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
