#!/usr/bin/env bash
# Extract the methodology from a social reel/video (Instagram/TikTok/YouTube Shorts).
# usage: reel_extract.sh <url> <out-dir>
# -> video, caption, info json, 1 fps frames, contact sheet, local transcript (whisper.cpp; audio never leaves the machine)
# Lessons: Instagram needs a logged-in session -> --cookies-from-browser chrome (run outside the sandbox);
# whisper.cpp's bundled for-tests model is a stub -> use ~/models/ggml-base.en.bin (resume with curl -C -).
set -euo pipefail
URL=$1; OUT=$2; mkdir -p "$OUT/frames"; cd "$OUT"
for b in chrome safari arc brave firefox ""; do
  args=(); [ -n "$b" ] && args=(--cookies-from-browser "$b")
  yt-dlp --no-progress "${args[@]}" -o "reel.%(ext)s" --write-info-json --write-description "$URL" > dl.log 2>&1 && { echo "downloaded${b:+ via $b}"; break; }
done
[ -f reel.mp4 ] || { tail -3 dl.log; exit 2; }
ffmpeg -v error -i reel.mp4 -vf "fps=1,scale=360:-1" frames/f_%02d.jpg
ffmpeg -v error -i frames/f_%02d.jpg -vf "tile=8x6" -frames:v 1 -y contact.jpg
M=${WHISPER_MODEL:-$HOME/models/ggml-base.en.bin}
if [ ! -s "$M" ] || [ "$(stat -f%z "$M" 2>/dev/null || stat -c%s "$M")" -lt 140000000 ]; then
  mkdir -p "$(dirname "$M")"; curl -sL -C - -o "$M" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin; fi
ffmpeg -v error -i reel.mp4 -ar 16000 -ac 1 -y audio.wav
whisper-cli -m "$M" -f audio.wav -otxt -osrt -of transcript > /dev/null 2>&1 && rm -f audio.wav dl.log
echo "caption: $(cat reel.description 2>/dev/null | head -c 200)"; echo "transcript: $OUT/transcript.srt"; echo "contact: $OUT/contact.jpg"
