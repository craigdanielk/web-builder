#!/usr/bin/env bash
# Video -> scroll-film frame set + manifest.json
# usage: frames.sh <video> <out-dir> [--fps 48] [--long 1920] [--q 88] [--reverse] [--no-denoise] [--no-interp]
# Pipeline: (reverse) -> hqdn3d temporal denoise -> minterpolate optical flow to --fps -> deband -> lanczos scale -> WebP.
# Lessons: q70 WebP bands dark gradients (28-35 dB PSNR); q88 + denoise + deband is the floor for dark footage.
# Interpolation doubles frames (smoothness) but softens; per-frame images cost ~5-10x a video codec -> for
# production prefer the WebCodecs path (templates/ README) and use this for previews/fallback.
set -euo pipefail
V=$1; OUT=$2; shift 2
FPS=48; LONG=1920; Q=88; REV=0; DN=1; INTERP=1
while [ $# -gt 0 ]; do case $1 in --fps) FPS=$2; shift;; --long) LONG=$2; shift;; --q) Q=$2; shift;;
  --reverse) REV=1;; --no-denoise) DN=0;; --no-interp) INTERP=0;; esac; shift; done
IFS=, read W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$V")
if [ "$W" -ge "$H" ]; then SC="scale=${LONG}:-2:flags=lanczos"; else SC="scale=-2:${LONG}:flags=lanczos"; fi
VF=""; [ $REV = 1 ] && VF="reverse,"
[ $DN = 1 ] && VF="${VF}hqdn3d=1.5:1.5:6:6,"
if [ $INTERP = 1 ]; then VF="${VF}minterpolate=fps=${FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"; else VF="${VF}fps=${FPS},"; fi
VF="${VF}deband=1thr=0.015:2thr=0.015:3thr=0.015:range=16:blur=1,${SC}"
rm -rf "$OUT"; mkdir -p "$OUT"
ffmpeg -v error -i "$V" -vf "$VF" -c:v libwebp -quality "$Q" -compression_level 6 -preset photo "$OUT/f_%04d.webp"
N=$(ls "$OUT"/*.webp | wc -l | tr -d ' ')
printf '{"count": %s, "fps": %s, "long_edge": %s, "quality": %s, "reversed": %s, "source": "%s"}\n' "$N" "$FPS" "$LONG" "$Q" "$REV" "$(basename "$V")" > "$OUT/manifest.json"
echo "$OUT: $N frames, $(du -sh "$OUT" | cut -f1)"
