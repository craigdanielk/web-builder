// @vitest-environment jsdom
// Render smoke test for the five newly ported components. Verifies each mounts,
// produces DOM, and unmounts without throwing — with and without props.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

import ConnectionGlobe from "../background/connection-globe";
import CorridorFlow from "../background/corridor-flow";
import DiagonalRibbon from "../background/diagonal-ribbon";
import MeshGradient from "../background/mesh-gradient";
import GeoChoropleth from "../interactive/geo-choropleth";

declare global {
  // eslint-disable-next-line no-var
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver;
  globalThis.IntersectionObserver = class {
    observe() {} unobserve() {} disconnect() {} takeRecords() { return []; }
    root = null; rootMargin = ""; thresholds = [];
  } as unknown as typeof IntersectionObserver;
  globalThis.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch;
  HTMLCanvasElement.prototype.getContext = vi.fn(() => null) as unknown as HTMLCanvasElement["getContext"];
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.restoreAllMocks();
});

function mount(node: React.ReactNode) {
  act(() => { root.render(node); });
  return container.innerHTML;
}

describe("ported components render", () => {
  it("ConnectionGlobe — default props", () => {
    expect(mount(<ConnectionGlobe className="h-full w-full" />)).toContain("<canvas");
  });

  it("ConnectionGlobe — custom nodes, links and accent colour", () => {
    const html = mount(
      <ConnectionGlobe
        nodes={[{ lat: 0, lng: 0, initial: "A" }, { lat: 40, lng: -74 }, { lat: -33, lng: 151 }]}
        links={[[0, 1], [1, 2]]}
        accentColor="#ff0000"
        dotColor="hsl(210 40% 60%)"
      />,
    );
    expect(html).toContain("<canvas");
  });

  it("CorridorFlow — unique gradient id per instance", () => {
    const html = mount(<><CorridorFlow /><CorridorFlow colors={["#ff0000"]} lineCount={4} /></>);
    const ids = [...html.matchAll(/id="(corridor-grad-[^"]+)"/g)].map((m) => m[1]);
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
  });

  it("DiagonalRibbon — accepts token colours", () => {
    const html = mount(<DiagonalRibbon colors={["var(--x, #123456)", "#654321"]} angle={-30} />);
    expect(html).toContain("blur(");
  });

  it("MeshGradient — four blooms, caller colours", () => {
    const html = mount(<MeshGradient colors={["#111111", "#222222"]} intensity={0.5} />);
    // Attribute occurrences only — the reduced-motion rule inside <style> uses
    // the same name as a selector.
    expect(container.querySelectorAll("[data-aurelix-mesh-bloom]")).toHaveLength(4);
    // jsdom normalises hex to rgb() when serialising an inline style.
    expect(html).toContain("rgb(17, 17, 17)"); // #111111, blooms 1 and 3
    expect(html).toContain("rgb(34, 34, 34)"); // #222222, blooms 2 and 4 — list cycled
    expect(html).toContain("@keyframes aurelix-mesh-drift-1");
  });

  it("GeoChoropleth — renders the skeleton before geo data arrives", () => {
    expect(mount(<GeoChoropleth regions={{ "840": { name: "United States" } }} />)).toContain("animate-pulse");
  });
});
