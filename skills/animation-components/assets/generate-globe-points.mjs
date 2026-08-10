// Precompute the hero globe's land dot cloud (task X-0169, fix F1).
//
// WHY THIS EXISTS: the same 1,737 points were computed in the BROWSER on every
// page load, by 6,000 spherical point-in-polygon tests against 177 country
// polygons in one un-yielded loop. Measured, it was 9,842 ms of the homepage's
// 9,845 ms Total Blocking Time — 99.97% of it — and removing it moved Lighthouse
// mobile 53 -> 88. The input never changes, so the answer never changes: it
// belongs at build time, not in 4x-throttled phones.
//
// Deterministic by construction: same topojson in, same points out, byte-identical
// output. That is what makes `--check` meaningful and what lets the emitted file be
// committed and regenerated in `prebuild` without ever drifting.
//
// OUTPUT FORMAT: raw little-endian Float32Array, 3 components (x, y, z) per point.
// No header — the count is the byte length / 12. 20.8 KB for 1,737 points (18.9 KB
// brotli), versus the 105 KB topojson it replaces.
//
// WHY FLOAT32 AND NOT THE Int16 THE PLAN SPECIFIED. Int16 is half the size (10.4 KB)
// and was tried first. Measured, it moves dots by up to **0.017 device px** at the
// desktop radius — sub-pixel, but a shifted antialiased edge changes a pixel's
// coverage by up to that fraction, which at the dots' peak alpha is ~2.6 levels of
// an 8-bit channel. That is a real, if invisible, difference, and "the same 1,737
// dots" was the acceptance bar. Float32 error is 3.0e-8 per component -> 2.4e-5 px,
// which bounds the 8-bit channel delta at 0.008 levels: provably zero after
// rounding, at every angle. 8.5 KB of brotli buys an equivalence proof with no
// hedge in it. `scripts/verify/globe-equivalence.mjs` is that proof.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { geoContains } from "d3-geo";
import { feature } from "topojson-client";

// Paths are CLI-overridable because this script now lives in a shared component
// library rather than inside one site: the topojson input and the emitted binary
// belong to whichever generated site is being built, not to this directory.
//   node generate-globe-points.mjs --in <topojson> --out <bin> [--check]
// Defaults target a Next.js site run from its own root.
const HERE = dirname(fileURLToPath(import.meta.url));
const argOf = (flag, fallback) => {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? resolve(process.argv[i + 1]) : fallback;
};
const TOPOJSON = argOf("--in", resolve(process.cwd(), "public", "countries-110m.json"));
const OUT = argOf("--out", resolve(process.cwd(), "public", "globe-land-points.bin"));
/** The pre-generated cloud shipped alongside this script, for reference/copying. */
export const BUNDLED_OUTPUT = resolve(HERE, "globe-land-points.bin");

// These three constants ARE the visual contract. They are duplicated nowhere else:
// the component no longer samples anything, it just draws what this file emits.
export const SAMPLE_COUNT = 6000;
export const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
export const STRIDE = 12; // bytes per point: 3 x float32

const D2R = Math.PI / 180;

/** The exact fibonacci-sphere + geoContains sampling the component used to run inline. */
export function sampleLandPoints(topo) {
  const land = feature(topo, topo.objects.countries);
  const pts = [];
  for (let i = 0; i < SAMPLE_COUNT; i++) {
    const y = 1 - (i / (SAMPLE_COUNT - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const th = GOLDEN_ANGLE * i;
    const v = { x: Math.cos(th) * r, y, z: Math.sin(th) * r };
    const lat = Math.asin(v.y) / D2R;
    const lng = Math.atan2(v.z, v.x) / D2R;
    if (geoContains(land, [lng, lat])) pts.push(v);
  }
  return pts;
}

export function encode(pts) {
  // Written through a DataView so the file is little-endian on any host that
  // ever runs the build, not merely on the little-endian ones.
  const buf = Buffer.alloc(pts.length * STRIDE);
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  for (let i = 0; i < pts.length; i++) {
    view.setFloat32(i * STRIDE, pts[i].x, true);
    view.setFloat32(i * STRIDE + 4, pts[i].y, true);
    view.setFloat32(i * STRIDE + 8, pts[i].z, true);
  }
  return buf;
}

export function decode(buf) {
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const n = Math.floor(buf.byteLength / STRIDE);
  const pts = [];
  for (let i = 0; i < n; i++) {
    pts.push({
      x: view.getFloat32(i * STRIDE, true),
      y: view.getFloat32(i * STRIDE + 4, true),
      z: view.getFloat32(i * STRIDE + 8, true),
    });
  }
  return pts;
}

function main() {
  const check = process.argv.includes("--check");

  if (!existsSync(TOPOJSON)) {
    console.error(`[globe-points] PRECONDITION: ${TOPOJSON} not found`);
    process.exit(2);
  }

  const topo = JSON.parse(readFileSync(TOPOJSON, "utf8"));
  const nFeatures = topo.objects?.countries?.geometries?.length ?? 0;
  const t0 = Date.now();
  const pts = sampleLandPoints(topo);
  const ms = Date.now() - t0;

  // Fail closed. The component's old runtime guard was `pts.length > 200 ? pts :
  // uniform()` — a build that emitted a near-empty cloud would silently ship a
  // blank globe, so refuse to write it at all.
  if (pts.length <= 200) {
    console.error(`[globe-points] REFUSING: only ${pts.length} land points sampled (expected ~1737)`);
    process.exit(1);
  }

  const buf = encode(pts);

  if (check) {
    if (!existsSync(OUT)) {
      console.error(`[globe-points] FAIL: ${OUT} does not exist — run without --check`);
      process.exit(1);
    }
    const onDisk = readFileSync(OUT);
    if (!onDisk.equals(buf)) {
      console.error(
        `[globe-points] FAIL: committed asset differs from a fresh computation ` +
          `(${onDisk.byteLength / STRIDE} points on disk vs ${pts.length} computed)`,
      );
      process.exit(1);
    }
    console.log(`[globe-points] check OK — ${pts.length} points, ${buf.byteLength} bytes, byte-identical`);
    return;
  }

  writeFileSync(OUT, buf);
  console.log(
    `[globe-points] ${pts.length} land points of ${SAMPLE_COUNT} samples over ` +
      `${nFeatures} country polygons -> ${buf.byteLength} bytes (${ms} ms, build time, not yours)`,
  );
}

if (import.meta.url === `file://${process.argv[1]}`) main();
