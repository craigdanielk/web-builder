# Scroll-film edge-case ledger (each one cost real time or credits)

| # | Trap | Symptom | Fix |
|---|---|---|---|
| E1 | `end_image` guides, doesn't guarantee | Film "lands" on a redrawn, drifted logo (IoU 0.42-0.68) | Always dissolve into the exact vector-composited anchor; gate with `fidelity.py` |
| E2 | Seedance 2.5 max 1080p | "Grainy / below 1080p" on HiDPI | 4k needs Seedance 2.0 (`--mode std --resolution 4k`), or upscale; no model re-renders a take at another resolution |
| E3 | Low source bitrate on dark haze | Noise in flat darks before any encode | Denoise (hqdn3d) + deband; prompt for cleaner grading; consider AI upscale |
| E4 | Per-frame WebP q70 | Banding/blocking (28-35 dB PSNR) | q88 floor for dark footage; better: WebCodecs video decode |
| E5 | Per-frame images ignore temporal redundancy | 11-25 MB per film | WebCodecs (AV1/H.264 keyframe-dense) decode to frames in-browser |
| E6 | Raw scroll -> frame index | Steppy, jumpy | Lenis + damped chase + sub-frame dissolve + 48 fps interpolation |
| E7 | React state per scroll frame | Jank on mid-range | Single rAF loop, refs only |
| E8 | Stage `scale()` during glide | Canvas border edge visible | Translate only; bg colour sampled from the frame edges; radial soft-edge mask |
| E9 | Theme global `h1` colour | Headline renders dark on dark | Set colour inline on hero text |
| E10 | Settle overlaps film end | Anchor never fully resolves; fidelity check misaligned | Resolve anchor BEFORE settle starts (filmEnd 0.74 < settleStart 0.78) |
| E11 | Higgsfield binary drift | Old /opt/homebrew 0.1.x | `~/.npm-global/bin/higgsfield` 1.1.x |
| E12 | Agent sandbox | "Not authenticated" though operator logged in | Run the CLI outside the sandbox; re-login in-runtime if credentials.json missing |
| E13 | `--wait` connection drop | Error but job completed | `generate list` / `generate get <id>` recovery (hf.sh does this) |
| E14 | zsh word-splitting | "Flag --wait ... needs a value" | bash arrays in runner scripts |
| E15 | Shared account consumers | 504 credits drained by unknown Recraft jobs | `hf.sh ledger` before/after every run |
| E16 | Localhost port collisions | OAuth callback hijacked by a stray http.server | Kill preview servers; check `lsof -iTCP:<port>` before login |
| E17 | Instagram gating | yt-dlp "login required" | `--cookies-from-browser chrome` |
| E18 | whisper.cpp test model | Empty transcript | Real ggml model; resume downloads with `curl -C -` |
| E19 | Monotone brand look from stock 3D presets | "Disgusting" R3F renders | Generated film carries the look; code carries exactness + choreography |
| E20 | Isometric logos | Extrusion collapses edge-on | Solve the axonometric (S1 math) — exact canonical lock by construction |
