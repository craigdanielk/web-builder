// @vitest-environment jsdom
//
// hover-glow — the two defects that made every built page log an error.
//
// DEFECT 1 (the console error). The component reached for a WebGL effect with
// `await import("https://cdn.jsdelivr.net/npm/threejs-components@0.0.19/...")`. No app
// bundler resolves a remote-URL dynamic import: Turbopack lowered it to `t.x(url, ...)`,
// its external-ESM helper, which exists only in the server runtime. In the client chunk
// `t.x` was undefined, so it threw `TypeError: t.x is not a function` on first paint of
// every page — deterministically, before any network request. A try/catch turned that
// into a console.error and a permanently blank <canvas>.
//
// The guard below is a SOURCE test, not a render test, and that is deliberate: the
// failure happens at bundle time, so no amount of rendering under jsdom (which resolves
// the URL happily through Node) can reproduce it. What has to be prevented is the
// specifier ever appearing in the file again.
//
// DEFECT 2 (silent, and worse). The old wrapper put `pointer-events-none` on the CONTENT
// layer rather than the decoration layer, so every link and button inside a wrapped
// section was dead to the mouse, and the wrapper itself ate clicks to randomize colors.
// That one produced no error at all.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import HoverGlow from "../interactive/hover-glow";

declare global {
  // eslint-disable-next-line no-var
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

const SOURCE = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), "../interactive/hover-glow.tsx"),
  "utf-8",
);

// Both guards run against code with comments stripped. The header comment in the
// component has to name the offending URL to be worth reading, and the old neon hexes
// are quoted there too; matching those would fail the file for documenting its own bug.
const CODE_ONLY = SOURCE.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const REMOTE_SPECIFIER = /\b(?:import|require)\s*\(\s*["'`]https?:\/\//;

// #rgb / #rrggbb. The design system is token-driven; a literal here is a color that
// cannot follow --accent when the palette changes, which is exactly how this component
// ended up painting neon on a white ground.
const HEX_LITERAL = /#[0-9a-fA-F]{3,8}\b/;

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  // jsdom has no matchMedia; the component calls it on mount, so without this every
  // render case below would throw before asserting anything.
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("hover-glow", () => {
  it("loads no module over the network", () => {
    expect(REMOTE_SPECIFIER.test(CODE_ONLY)).toBe(false);
  });

  it("names no color literal, only design tokens", () => {
    expect(HEX_LITERAL.test(CODE_ONLY)).toBe(false);
    expect(SOURCE).toContain("var(--accent)");
  });

  it("leaves wrapped content interactive", () => {
    const onClick = vi.fn();
    act(() => {
      root.render(
        <HoverGlow>
          <button type="button" onClick={onClick}>Get started</button>
        </HoverGlow>,
      );
    });

    const button = container.querySelector("button");
    expect(button).not.toBeNull();

    // The decoration must be the pointer-transparent layer, never the content. Asserting
    // on the class is the whole point: jsdom does not do hit-testing, so a click
    // dispatched directly at the button would pass even with the old markup.
    const glow = container.querySelector('[aria-hidden="true"]');
    expect(glow).not.toBeNull();
    expect(glow!.className).toContain("pointer-events-none");
    expect(button!.closest(".pointer-events-none")).toBeNull();

    act(() => {
      button!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does not force a ground color onto the section it wraps", () => {
    act(() => {
      root.render(<HoverGlow><p>copy</p></HoverGlow>);
    });
    // The old version hardcoded `bg-background` and `min-h-[400px]`, which gave every
    // wrapped section an opaque box it never asked for.
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).not.toContain("bg-background");
    expect(wrapper.className).not.toContain("min-h-[");
  });
});
