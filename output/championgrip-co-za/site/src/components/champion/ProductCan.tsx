"use client";

type Props = {
  imageUrl: string;
  alt?: string;
  className?: string;
  /**
   * 3D cylinder wrap is disabled until we have a true label UV / unwrap.
   * Wrapping a full packshot photo onto a cylinder crops and doubles the can.
   */
  enable3d?: boolean;
};

/**
 * Packshot presenter. WebGL cylinder deferred — packshots are already 2D cans.
 */
export function ProductCan({ imageUrl, alt = "", className = "", enable3d: _enable3d = false }: Props) {
  return (
    <div className={`cg-product-can ${className}`} data-mode="img">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={imageUrl} alt={alt} className="cg-can" />
    </div>
  );
}
