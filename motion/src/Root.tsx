import React from "react";
import { Composition, staticFile } from "remotion";
import { loadFont } from "@remotion/fonts";
import props from "../props/cape-crypto-product-rail.json";
import { ProductRail, ProductRailProps } from "./ProductRail";

/**
 * The font file is the exact woff2 the compiled site ships (Next's built
 * Poppins latin subset, copied into public/fonts). Loading it locally is what
 * makes the render portable-deterministic — a machine without Poppins
 * installed produces the same frames as one with it.
 */
loadFont({
  family: "Poppins",
  url: staticFile("fonts/poppins-latin-400.woff2"),
  weight: "400",
  format: "woff2",
});

const durationInFrames =
  props.introFrames + props.items.length * props.framesPerItem;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="CapeCryptoProductRail"
      component={ProductRail as React.FC<Record<string, unknown>>}
      durationInFrames={durationInFrames}
      fps={props.fps}
      width={props.width}
      height={props.height}
      defaultProps={
        {
          brandName: props.brandName,
          eyebrow: props.eyebrow,
          items: props.items,
          tokens: props.tokens,
          framesPerItem: props.framesPerItem,
          introFrames: props.introFrames,
        } as unknown as Record<string, unknown>
      }
    />
  );
};

export type { ProductRailProps };
