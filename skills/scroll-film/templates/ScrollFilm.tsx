"use client";
/**
 * ScrollFilm — reusable pinned scroll-film section (Next.js / React 19). From the Trend Digital hero.
 *
 * - Scroll scrubs a pre-extracted frame set (frames.sh output + manifest.json) on a canvas.
 * - Smoothness: Lenis + damped rAF chase, sub-frame cross-dissolve, pre-decoded ImageBitmaps,
 *   zero React state per frame (refs only). Measured 120 fps median on desktop.
 * - Optional start still (pull-back into the film) and EXACT end anchor (the vector-composited still):
 *   generated end frames only approximate a logo, so the film always resolves into the anchor.
 * - Optional settle: the stage glides aside while `children` (your copy) rises in.
 * - Reduced motion: renders the settled end state, no scrub, no Lenis.
 *
 * deps: lenis. Frames under /public: <base>/<set>/f_0001.webp … + manifest.json {count}.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";
import Lenis from "lenis";

export type FrameSet = { dir: string; count?: number }; // count read from manifest.json when omitted
export type ScrollFilmProps = {
  desktop: FrameSet;
  mobile?: FrameSet;
  start?: { desktop: string; mobile?: string };   // optional first still (e.g. inside-the-object)
  endAnchor?: { desktop: string; mobile?: string }; // exact brand still the film must resolve into
  heightVh?: number;                               // scroll length of the pinned section
  bg?: string;
  settle?: { desktopVw: number; mobileVh: number } | null; // null = no glide, copy overlays centre
  timing?: Partial<typeof DEFAULT_TIMING>;
  shade?: { desktop: string; mobile: string };     // readability gradients under the copy
  ariaLabel?: string;
  children?: ReactNode;                            // hero copy / CTAs (rises in at the end)
};

const DEFAULT_TIMING = { startEnd: 0.18, filmStart: 0.04, filmEnd: 0.74, anchorLead: 0.06, settleStart: 0.78, settleEnd: 0.96, copyStart: 0.83 };
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const range = (p: number, a: number, b: number) => clamp((p - a) / (b - a));
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const SOFT_EDGE = "radial-gradient(ellipse 75% 85% at 50% 50%, #000 62%, transparent 100%)";

async function bitmap(url: string) {
  const blob = await (await fetch(url)).blob();
  return "createImageBitmap" in window ? await createImageBitmap(blob)
    : await new Promise<HTMLImageElement>((res) => { const im = new Image(); im.onload = () => res(im); im.src = URL.createObjectURL(blob); });
}

export default function ScrollFilm(props: ScrollFilmProps) {
  const { desktop, mobile: mobileSet, start, endAnchor, heightVh = 480, bg = "#060913", settle = { desktopVw: 20, mobileVh: -24 }, ariaLabel = "Film", children } = props;
  const T = { ...DEFAULT_TIMING, ...props.timing };
  const wrapRef = useRef<HTMLElement>(null), canvasRef = useRef<HTMLCanvasElement>(null), stageRef = useRef<HTMLDivElement>(null);
  const startRef = useRef<HTMLImageElement>(null), shadeRef = useRef<HTMLDivElement>(null), copyRef = useRef<HTMLDivElement>(null), hintRef = useRef<HTMLDivElement>(null);
  const [mobile, setMobile] = useState(false);
  const [reduce, setReduce] = useState(false);

  useEffect(() => {
    const isMobile = !!mobileSet && window.matchMedia("(max-aspect-ratio: 4/5)").matches;
    const isReduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setMobile(isMobile); setReduce(isReduce);
    const set = isMobile ? mobileSet! : desktop;
    let alive = true, dirty = true, count = set.count ?? 0;
    const frames: (ImageBitmap | HTMLImageElement | undefined)[] = [];
    let anchor: ImageBitmap | HTMLImageElement | undefined;
    const url = (i: number) => `${set.dir}/f_${String(i).padStart(4, "0")}.webp`;

    (async () => {
      if (!count) { try { count = (await (await fetch(`${set.dir}/manifest.json`)).json()).count; } catch { return; } }
      const order = isReduce ? [count] : [1, count, ...Array.from({ length: count }, (_, i) => i + 1).filter((i) => i !== 1 && i !== count)];
      let k = 0;
      const worker = async () => { while (alive && k < order.length) { const i = order[k++]; try { frames[i - 1] = await bitmap(url(i)); dirty = true; } catch {} } };
      await Promise.all(Array.from({ length: 6 }, worker));
    })();
    const anchorUrl = endAnchor && (isMobile && endAnchor.mobile ? endAnchor.mobile : endAnchor.desktop);
    if (anchorUrl) bitmap(anchorUrl).then((b) => { anchor = b; dirty = true; }).catch(() => {});

    const c = canvasRef.current!, ctx = c.getContext("2d", { alpha: false })!;
    ctx.imageSmoothingQuality = "high";
    const lenis = isReduce ? null : new Lenis({ lerp: 0.085, smoothWheel: true, wheelMultiplier: 0.9, touchMultiplier: 1.4 });
    const target = () => { const el = wrapRef.current!; const total = el.offsetHeight - window.innerHeight; return isReduce ? 1 : clamp(-el.getBoundingClientRect().top / Math.max(1, total)); };
    let cur = target(), lastP = -1;
    const nearest = (i: number) => { if (frames[i]) return i; for (let d = 1; d < count; d++) { if (frames[i - d]) return i - d; if (frames[i + d]) return i + d; } return -1; };
    const blit = (f: ImageBitmap | HTMLImageElement, alpha: number) => {
      const w0 = "naturalWidth" in f ? f.naturalWidth : f.width, h0 = "naturalHeight" in f ? f.naturalHeight : f.height;
      const s = Math.max(c.width / w0, c.height / h0); ctx.globalAlpha = alpha;
      ctx.drawImage(f, (c.width - w0 * s) / 2, (c.height - h0 * s) / 2, w0 * s, h0 * s);
    };
    const render = (p: number) => {
      if (count) {
        const f = easeInOut(range(p, T.filmStart, T.filmEnd)) * (count - 1), i0 = Math.floor(f), t = f - i0;
        const a = nearest(i0), b = nearest(Math.min(count - 1, i0 + 1));
        if (a >= 0) {
          ctx.globalAlpha = 1; ctx.fillStyle = bg; ctx.fillRect(0, 0, c.width, c.height);
          blit(frames[a]!, 1); if (b >= 0 && b !== a && t > 0.01) blit(frames[b]!, t);
          const ea = easeInOut(range(p, T.filmEnd - T.anchorLead, T.filmEnd + 0.02)); if (anchor && ea > 0) blit(anchor, ea);
          ctx.globalAlpha = 1;
        }
      }
      const st = range(p, 0, T.startEnd);
      if (startRef.current) { startRef.current.style.opacity = String(1 - easeInOut(st)); startRef.current.style.transform = `scale(${1.4 - 0.4 * easeOut(st)})`; }
      const se = settle ? easeInOut(range(p, T.settleStart, T.settleEnd)) : 0;
      if (stageRef.current && settle) stageRef.current.style.transform = isMobile ? `translate3d(0, ${settle.mobileVh * se}vh, 0)` : `translate3d(${settle.desktopVw * se}vw, 0, 0)`;
      const co = easeOut(range(p, T.copyStart, T.settleEnd + 0.02));
      if (shadeRef.current) shadeRef.current.style.opacity = String(settle ? se : co);
      if (copyRef.current) { copyRef.current.style.opacity = String(co); copyRef.current.style.transform = `translate3d(0, ${(1 - co) * 32}px, 0)`; copyRef.current.style.pointerEvents = co > 0.5 ? "auto" : "none"; }
      if (hintRef.current) hintRef.current.style.opacity = String(1 - range(p, 0, 0.04));
    };
    const resize = () => { const dpr = Math.min(window.devicePixelRatio || 1, 2); c.width = Math.round(c.clientWidth * dpr); c.height = Math.round(c.clientHeight * dpr); dirty = true; };
    resize(); window.addEventListener("resize", resize);
    let raf = 0;
    const loop = (time: number) => {
      lenis?.raf(time);
      const tg = target(); cur += (tg - cur) * 0.18; if (Math.abs(tg - cur) < 0.00005) cur = tg;
      if (dirty || Math.abs(cur - lastP) > 0.00002) { render(cur); lastP = cur; dirty = false; }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => { alive = false; cancelAnimationFrame(raf); window.removeEventListener("resize", resize); lenis?.destroy(); frames.forEach((f) => f && "close" in f && f.close()); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shade = props.shade ?? {
    desktop: `linear-gradient(to right, ${bg}f2 0%, ${bg}cc 38%, ${bg}00 62%)`,
    mobile: `linear-gradient(to top, ${bg}f5 0%, ${bg}d9 42%, ${bg}00 70%)`,
  };
  const startSrc = start && (mobile && start.mobile ? start.mobile : start.desktop);
  return (
    <section ref={wrapRef} aria-label={ariaLabel} className="relative" style={{ height: reduce ? "100vh" : `${heightVh}vh`, background: bg }}>
      <div className="sticky top-0 h-screen w-full overflow-hidden" style={{ background: bg }}>
        <div ref={stageRef} className="absolute inset-0 will-change-transform">
          <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden="true" style={{ WebkitMaskImage: SOFT_EDGE, maskImage: SOFT_EDGE }} />
          {!reduce && startSrc && (
            // eslint-disable-next-line @next/next/no-img-element
            <img ref={startRef} src={startSrc} alt="" aria-hidden="true" fetchPriority="high"
              className="absolute inset-0 h-full w-full object-cover will-change-transform" style={{ transform: "scale(1.4)" }} />
          )}
        </div>
        <div ref={shadeRef} className="pointer-events-none absolute inset-0" style={{ opacity: reduce ? 1 : 0, background: mobile ? shade.mobile : shade.desktop }} />
        <div ref={copyRef} className={`absolute z-10 will-change-transform ${mobile ? "inset-x-6 bottom-[8vh]" : "left-[7vw] top-1/2 max-w-[560px] -translate-y-1/2"}`}
          style={{ opacity: reduce ? 1 : 0, pointerEvents: reduce ? "auto" : "none" }}>
          {children}
        </div>
        {!reduce && (
          <div ref={hintRef} className="absolute bottom-8 left-1/2 z-10 -translate-x-1/2 text-center text-xs tracking-[0.25em] text-white/60">
            SCROLL<div className="mx-auto mt-3 h-10 w-px animate-pulse bg-white/40" />
          </div>
        )}
      </div>
    </section>
  );
}
