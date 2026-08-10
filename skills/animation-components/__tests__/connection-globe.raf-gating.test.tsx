// @vitest-environment jsdom
//
// A7 (task X-0169, fix F2) — the render loop stops.
//
// TWO DEFECTS, ONE MECHANISM. `draw()` re-scheduled itself unconditionally, so the
// hero globe repainted at 60 fps for the entire session with the hero scrolled far
// off screen; and `prefers-reduced-motion` froze only the rotation variable, so the
// full frame — clear, full-canvas radial gradient, 1,737 arc fills, 14 slerped arcs,
// 14 radial gradients — still ran every frame to produce a picture that never
// changed. The second is an accessibility defect: asking for less motion bought a
// user nothing but the same battery drain.
//
// WHY JSDOM. The assertion is "is another frame scheduled?", which is a question
// about a callback, not about pixels. jsdom answers it deterministically with a
// controllable rAF queue. A browser harness cannot: a hidden tab suspends rAF, so
// "no frame was scheduled" and "the tab is throttling" are indistinguishable there
// — the same reason Navigation.panel-guard.test.tsx lives here.
//
// THE 2D CONTEXT IS STUBBED. jsdom's getContext("2d") returns null, and the
// component returns early on a null context — so without the stub every case below
// would pass while measuring nothing. `expect(drawCalls).toBeGreaterThan(0)` in the
// running case is the positive control that says otherwise.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import ConnectionGlobe from "../background/connection-globe";

declare global {
  // eslint-disable-next-line no-var
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

let container: HTMLDivElement;
let root: Root;

// Frames requested but not yet run, keyed by handle. A Map rather than an array
// because cancelAnimationFrame has to actually REMOVE the pending frame — a fake
// that ignores the cancel runs a frame the browser never would, and reports the
// component as leaking frames it has correctly cancelled.
let queue: Map<number, FrameRequestCallback> = new Map();
let nextHandle = 1;
let cancelled: number[] = [];
/** How many times the component actually painted. */
let drawCalls = 0;
/** The most recent IntersectionObserver callback the component installed. */
let ioCallback: IntersectionObserverCallback | null = null;
let ioDisconnects = 0;

function stubContext() {
  const gradient = { addColorStop: vi.fn() };
  const ctx: Record<string, unknown> = {
    clearRect: vi.fn(() => { drawCalls++; }),
    createRadialGradient: vi.fn(() => gradient),
    fillRect: vi.fn(), beginPath: vi.fn(), arc: vi.fn(), fill: vi.fn(),
    stroke: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), save: vi.fn(),
    restore: vi.fn(), clip: vi.fn(), drawImage: vi.fn(), setTransform: vi.fn(),
    fillText: vi.fn(), measureText: vi.fn(() => ({ width: 0 })),
    fillStyle: "", strokeStyle: "", lineWidth: 1, globalAlpha: 1,
    shadowColor: "", shadowBlur: 0, font: "", textAlign: "", textBaseline: "",
  };
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ctx) as unknown as HTMLCanvasElement["getContext"];
}

/** Run every currently queued frame once (a frame may enqueue the next one). */
function flushFrames(n = 1) {
  for (let i = 0; i < n; i++) {
    const due = [...queue.values()];
    queue = new Map();
    act(() => { due.forEach((cb) => cb(performance.now())); });
  }
}

function setReducedMotion(reduce: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: reduce && query.includes("prefers-reduced-motion"),
    media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

beforeEach(() => {
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  queue = new Map(); cancelled = []; nextHandle = 1; drawCalls = 0;
  ioCallback = null; ioDisconnects = 0;

  stubContext();
  setReducedMotion(false);

  globalThis.requestAnimationFrame = ((cb: FrameRequestCallback) => {
    const handle = nextHandle++;
    queue.set(handle, cb);
    return handle;
  }) as typeof requestAnimationFrame;
  globalThis.cancelAnimationFrame = ((h: number) => { cancelled.push(h); queue.delete(h); }) as typeof cancelAnimationFrame;

  globalThis.ResizeObserver = class {
    observe() {} unobserve() {} disconnect() {}
  } as unknown as typeof ResizeObserver;

  globalThis.IntersectionObserver = class {
    constructor(cb: IntersectionObserverCallback) { ioCallback = cb; }
    observe() {} unobserve() {} disconnect() { ioDisconnects++; }
    takeRecords() { return []; }
    root = null; rootMargin = ""; thresholds = [];
  } as unknown as typeof IntersectionObserver;

  // The dot cloud is irrelevant to scheduling; never resolving keeps the test
  // to one variable (the component draws its uniform fallback meanwhile).
  globalThis.fetch = vi.fn(() => new Promise(() => {})) as unknown as typeof fetch;

  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.restoreAllMocks();
});

function mount() {
  act(() => { root.render(<ConnectionGlobe className="h-full w-full" />); });
}

/** Report intersection to the observer the component installed. */
function intersect(isIntersecting: boolean) {
  expect(ioCallback, "component did not install an IntersectionObserver").not.toBeNull();
  act(() => {
    ioCallback!(
      [{ isIntersecting, intersectionRatio: isIntersecting ? 1 : 0 } as IntersectionObserverEntry],
      {} as IntersectionObserver,
    );
  });
}

describe("ConnectionGlobe render loop (A7)", () => {
  it("schedules nothing until the hero is on screen", () => {
    mount();
    expect(queue.size).toBe(0);
    flushFrames(3);
    expect(drawCalls).toBe(0);
  });

  it("does not re-schedule while IntersectionObserver reports isIntersecting: false", () => {
    mount();
    intersect(false);
    expect(queue.size).toBe(0);
    flushFrames(5);
    expect(drawCalls).toBe(0);
  });

  it("keeps painting while on screen — the positive control", () => {
    mount();
    intersect(true);
    expect(queue.size).toBe(1);
    flushFrames(4);
    expect(drawCalls).toBeGreaterThan(0);
    // A frame ran AND queued its successor: the loop is genuinely running, so the
    // silence in the other cases is a stopped loop and not a broken test.
    expect(queue.size).toBe(1);
  });

  it("stops re-scheduling as soon as the hero scrolls off screen", () => {
    mount();
    intersect(true);
    flushFrames(3);
    const painted = drawCalls;
    expect(painted).toBeGreaterThan(0);

    intersect(false);
    expect(queue.size).toBe(0);
    flushFrames(5);
    expect(drawCalls).toBe(painted); // not one more frame
  });

  it("under prefers-reduced-motion, paints one frame and stops", () => {
    setReducedMotion(true);
    mount();
    intersect(true);
    expect(queue.size).toBe(1);

    flushFrames(1);
    expect(drawCalls).toBe(1);      // it DID render — a frozen globe, not a blank one
    expect(queue.size).toBe(0);   // and asked for nothing more

    flushFrames(5);
    expect(drawCalls).toBe(1);
  });

  it("cancels the pending frame and disconnects the observer on unmount", () => {
    mount();
    intersect(true);
    expect(queue.size).toBe(1);
    act(() => root.unmount());
    expect(cancelled.length).toBeGreaterThan(0);
    expect(ioDisconnects).toBeGreaterThan(0);
    root = createRoot(container); // afterEach unmounts again; give it a live root
  });
});
