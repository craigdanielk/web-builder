#!/usr/bin/env node
/**
 * media-policy — static Device & Media Compatibility policy (canonical; origin: Trend Digital Android incident
 * 2026-10-01, decision record DECISION-native-video.md). Shared verbatim by trend-digital-website and Aurelix AG.
 *
 * RULES (FAIL unless exempted with a decision record):
 *  M1  No hand-rolled WebCodecs video decoding (new VideoDecoder / VideoDecoder.isConfigSupported) in app source.
 *      W3C WebCodecs: un-closed VideoFrames "can cause decoding to stall"; hardware pools are small (Android).
 *  M2  No raw elementary video streams shipped in public/ (.ivf .h264 .h265 .hevc .obu .av1) — use MP4/WebM via <video>.
 *  M3  Every <video> with autoPlay must also be muted + playsInline (Chrome autoplay policy / iOS inline playback).
 * WARN: playbackRate assignments (a native decoder must never be asked to run faster than real time).
 *
 * Usage: node media-policy.mjs --root <project> [--src src] [--public public] [--exempt qa/media-policy-exemptions.json]
 *                              [--override "<reason>"]   (or QA_OVERRIDE env)
 * Exit: 0 PASS · 1 FAIL · 3 NOT_MEASURED (no source dir found). Override turns 1 into 0, logged loudly.
 */
import fs from "node:fs"; import path from "node:path"; import os from "node:os"; import { execFileSync } from "node:child_process";
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const root = path.resolve(arg("--root", "."));
const srcDir = path.join(root, arg("--src", "src")), pubDir = path.join(root, arg("--public", "public"));
const exemptFile = path.join(root, arg("--exempt", "qa/media-policy-exemptions.json"));
const override = arg("--override", process.env.QA_OVERRIDE || "");
const exempt = fs.existsSync(exemptFile) ? JSON.parse(fs.readFileSync(exemptFile, "utf8")) : {}; // {"path": "decision record ref"}
// Judge what SHIPS: inside a git repo only tracked files count (ignored local spike outputs never deploy).
let tracked = null;
try { tracked = new Set(execFileSync("git", ["-C", root, "ls-files", "-z"], { encoding: "utf8", maxBuffer: 1 << 28 }).split("\0").filter(Boolean).map((r) => path.join(root, r))); } catch {}
const walk0 = (d, out = []) => { if (!fs.existsSync(d)) return out; for (const e of fs.readdirSync(d, { withFileTypes: true })) {
  if (e.name === "node_modules" || e.name.startsWith(".")) continue; const p = path.join(d, e.name); e.isDirectory() ? walk0(p, out) : out.push(p); } return out; };
const walk = (d) => walk0(d).filter((p) => !tracked || tracked.has(p));
if (!fs.existsSync(srcDir)) { console.log(`media-policy: NOT_MEASURED — no source dir ${srcDir}`); process.exit(3); }
const rel = (p) => path.relative(root, p); const fails = [], warns = [];
for (const f of walk(srcDir).filter((p) => /\.(tsx?|jsx?|mjs|cjs)$/.test(p))) {
  const s = fs.readFileSync(f, "utf8"), r = rel(f);
  if (/new\s+VideoDecoder\s*\(|VideoDecoder\.isConfigSupported/.test(s) && !exempt[r]) fails.push(`M1 ${r}: hand-rolled WebCodecs video decoding — use native <video> (or add a decision-record exemption)`);
  for (const m of s.matchAll(/<video\b[^>]*>/g)) { const t = m[0];
    if (/\bautoPlay\b|\bautoplay\b/.test(t) && !(/\bmuted\b/.test(t) && /\bplaysInline\b|\bplaysinline\b/.test(t))) fails.push(`M3 ${r}: <video autoPlay> without muted + playsInline`); }
  if (/\.playbackRate\s*=(?!=)/.test(s)) warns.push(`W1 ${r}: playbackRate assignment — never ask a decoder to run faster than 1x; bake timing into the encode`);
}
for (const f of walk(pubDir).filter((p) => /\.(ivf|h264|h265|hevc|obu|av1)$/i.test(p))) { const r = rel(f); if (!exempt[r]) fails.push(`M2 ${r}: raw elementary video stream in public/ — ship MP4/WebM for <video>`); }
warns.forEach((w) => console.log("WARN", w)); fails.forEach((x) => console.log("FAIL", x));
if (!fails.length) { console.log(`media-policy: PASS (${warns.length} warning(s))`); process.exit(0); }
if (override) { console.log(`media-policy: FAIL OVERRIDDEN by ${os.userInfo().username} — reason: ${override}`); process.exit(0); }
console.log(`media-policy: FAIL (${fails.length}). Override only with explicit permission: --override "<reason>" / QA_OVERRIDE`); process.exit(1);
