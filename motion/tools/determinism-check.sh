#!/usr/bin/env bash
# Render the same composition twice and compare the outputs byte for byte.
#
# Determinism is the entire argument for choosing Remotion over a generative
# engine, so it is asserted, not assumed. Two artefacts are compared:
#   1. the PNG frame sequence — the render itself
#   2. the muxed mp4 — the render plus the container
# These can disagree: an encoder may stamp non-deterministic container metadata
# even when every frame is identical. Both results are printed; neither is
# reported as PASS unless it was measured.
#
# Usage: bash tools/determinism-check.sh
set -euo pipefail

cd "$(dirname "$0")/.."
COMP="CapeCryptoProductRail"
WORK="out/determinism"
rm -rf "$WORK"
mkdir -p "$WORK"

hash_dir() {
  # Sorted per-file hashes, then a hash of that listing. Filenames included so
  # a missing or extra frame is a difference, not a silent match.
  find "$1" -type f -name '*.png' | sort | while read -r f; do
    printf '%s  %s\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(basename "$f")"
  done | shasum -a 256 | cut -d' ' -f1
}

echo "== frame sequence, run A =="
npx remotion render src/index.ts "$COMP" "$WORK/seq-a" --sequence --log=error
echo "== frame sequence, run B =="
npx remotion render src/index.ts "$COMP" "$WORK/seq-b" --sequence --log=error

A=$(hash_dir "$WORK/seq-a")
B=$(hash_dir "$WORK/seq-b")
echo "frames A: $A"
echo "frames B: $B"
if [ "$A" = "$B" ]; then
  echo "FRAMES: IDENTICAL ($(find "$WORK/seq-a" -name '*.png' | wc -l | tr -d ' ') frames)"
  FRAMES_OK=1
else
  echo "FRAMES: DIFFER — determinism claim is false for this composition"
  FRAMES_OK=0
fi

echo "== mp4, run A =="
npx remotion render src/index.ts "$COMP" "$WORK/a.mp4" --log=error
echo "== mp4, run B =="
npx remotion render src/index.ts "$COMP" "$WORK/b.mp4" --log=error
MA=$(shasum -a 256 "$WORK/a.mp4" | cut -d' ' -f1)
MB=$(shasum -a 256 "$WORK/b.mp4" | cut -d' ' -f1)
echo "mp4 A: $MA"
echo "mp4 B: $MB"
if [ "$MA" = "$MB" ]; then
  echo "MP4: IDENTICAL"
else
  echo "MP4: DIFFERS (container-level; see FRAMES for the render itself)"
fi

[ "$FRAMES_OK" = "1" ]
