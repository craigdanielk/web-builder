import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/**
 * Product rail — the compiled analogue of the BVNK homepage tab videos.
 *
 * Every visible string arrives as a prop carrying its declared `field_key`.
 * Every colour, radius and font arrives from the same compiled token set the
 * page's `globals.css` was written from. There is no literal in this file that
 * a designer would call a design decision the token system did not make, and
 * no string a compliance officer would call a claim.
 *
 * Determinism: the only time source is `useCurrentFrame()`. No Date, no
 * Math.random, no network. Frame N is a pure function of (props, N).
 */

export type RailItem = {
  value: string;
  field_key: string;
  source: string;
};

export type Tokens = Record<string, string>;

export type ProductRailProps = {
  brandName: string;
  eyebrow: string;
  items: RailItem[];
  tokens: Tokens;
  framesPerItem: number;
  introFrames: number;
};

const px = (token: string | undefined, fallback: number): number => {
  if (!token) return fallback;
  const n = parseFloat(token);
  return Number.isFinite(n) ? n : fallback;
};

/** Kinetic type: the brand name assembles a word at a time. */
const Intro: React.FC<{
  brandName: string;
  eyebrow: string;
  tokens: Tokens;
  durationInFrames: number;
}> = ({ brandName, eyebrow, tokens, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = brandName.split(" ");

  const exit = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        opacity: exit,
      }}
    >
      <div
        style={{
          color: tokens.muted,
          fontSize: 22,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          fontWeight: Number(tokens["body-weight"] ?? 400),
          opacity: interpolate(frame, [6, 22], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          marginBottom: px(tokens["block-gap"], 24),
        }}
      >
        {eyebrow}
      </div>
      <div style={{ display: "flex", gap: 20 }}>
        {words.map((word, i) => {
          const s = spring({
            frame: frame - i * 6,
            fps,
            config: { damping: 200, mass: 0.8 },
          });
          return (
            <span
              key={word + String(i)}
              style={{
                color: tokens.foreground,
                fontSize: 96,
                lineHeight: 1.05,
                letterSpacing: "-0.02em",
                fontWeight: Number(tokens["heading-weight"] ?? 500),
                opacity: s,
                transform: `translateY(${(1 - s) * 40}px)`,
                display: "inline-block",
              }}
            >
              {word}
            </span>
          );
        })}
      </div>
      <div
        style={{
          marginTop: px(tokens["block-gap"], 24) * 1.5,
          height: 4,
          width: interpolate(frame, [24, 48], [0, 220], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          background: tokens.accent,
          borderRadius: px(tokens["radius-button"], 100),
        }}
      />
    </AbsoluteFill>
  );
};

/** One declared product, held on screen long enough to read. */
const Card: React.FC<{
  item: RailItem;
  index: number;
  total: number;
  tokens: Tokens;
  durationInFrames: number;
}> = ({ item, index, total, tokens, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({ frame, fps, config: { damping: 200, mass: 0.7 } });
  const exit = interpolate(
    frame,
    [durationInFrames - 14, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const pad = px(tokens["card-pad"], 40);
  const progress = (index + 1) / total;

  return (
    <AbsoluteFill
      style={{ alignItems: "center", justifyContent: "center", opacity: exit }}
    >
      <div
        style={{
          width: 900,
          background: tokens.surface,
          border: `1px solid ${tokens.border}`,
          borderRadius: px(tokens["radius-card"], 32),
          padding: pad,
          transform: `translateY(${(1 - enter) * 48}px)`,
          opacity: enter,
          display: "flex",
          flexDirection: "column",
          gap: px(tokens["block-gap"], 24),
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: px(tokens["block-gap"], 24) / 2,
          }}
        >
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: 999,
              background: tokens.accent,
              display: "inline-block",
            }}
          />
          <span
            style={{
              color: tokens.muted,
              fontSize: 18,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              fontWeight: Number(tokens["body-weight"] ?? 400),
            }}
          >
            {item.field_key.replace(/_/g, " ")}
          </span>
        </div>

        <div
          style={{
            color: tokens.foreground,
            fontSize: 56,
            lineHeight: 1.12,
            letterSpacing: "-0.02em",
            fontWeight: Number(tokens["heading-weight"] ?? 500),
          }}
        >
          {item.value}
        </div>
      </div>

      {/* Rail progress — position in the declared list, not a metric. */}
      <div
        style={{
          marginTop: pad,
          width: 900,
          height: 3,
          background: tokens.border,
          borderRadius: 999,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${progress * 100}%`,
            height: "100%",
            background: tokens.accent,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const ProductRail: React.FC<ProductRailProps> = ({
  brandName,
  eyebrow,
  items,
  tokens,
  framesPerItem,
  introFrames,
}) => {
  return (
    <AbsoluteFill
      style={{
        background: tokens.background,
        fontFamily: `Poppins, ${tokens["font-body"] ?? "sans-serif"}`,
      }}
    >
      <Sequence durationInFrames={introFrames}>
        <Intro
          brandName={brandName}
          eyebrow={eyebrow}
          tokens={tokens}
          durationInFrames={introFrames}
        />
      </Sequence>
      {items.map((item, i) => (
        <Sequence
          key={item.value}
          from={introFrames + i * framesPerItem}
          durationInFrames={framesPerItem}
        >
          <Card
            item={item}
            index={i}
            total={items.length}
            tokens={tokens}
            durationInFrames={framesPerItem}
          />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
