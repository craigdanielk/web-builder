#!/usr/bin/env python3
"""
VERIFY GATE M: Device & Media Compatibility (canonical; shared with trend-digital-website scripts/qa/).

Origin: 2026-10-01 — a Trend Digital site stopped loading on Android Chrome (Galaxy S24 Ultra) after a
hand-rolled WebCodecs hero decoder shipped; emulated Android PASSED that build. So this gate has three layers:
  1. media-policy.mjs  (static, git-tracked source of --project-dir): no hand-rolled WebCodecs decoding,
     no raw elementary streams in public/, autoplay video muted+playsInline.
  2. device-matrix.mjs (headless Chrome, --url): routes x desktop-1440@2x / desktop-1280 / android-s24 /
     iphone / reduced-motion — load, errors, failed requests, overflow, stuck video, stuck loader,
     clipped text, tablist mapping.
  3. Real-device checklist (manual until a paid real-device cloud): not executable here — reported as a
     reminder, never as a PASS.
BLOCKING. Override only with operator permission: --override "<reason>" or AURELIX_GATE_M_OVERRIDE (logged).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from lib.capability import describe  # noqa: E402  (capability register, where present)
except ImportError:  # branches without scripts/lib/capability.py: same --describe behaviour, no register validation
    import json as _json

    def describe(spec: dict) -> bool:
        if "--describe" not in sys.argv[1:]:
            return False
        sys.stdout.write(_json.dumps(spec, indent=2, default=str) + "\n")
        return True

NOT_MEASURED = 3
QUALITY = Path(__file__).resolve().parent / "quality"

CAPABILITY = {
    "id": "aurelix.gate.verify-m",
    "name": "Gate M — device & media compatibility (static media policy + headless device matrix)",
    "kind": "gate",
    "invocation": "python3 scripts/verify_gate_m.py [--project-dir <site>] [--url <deployed-url>] "
                  "[--routes /,/about] [--out <dir>] [--override <reason>]",
    "preconditions": [
        "for the policy lane: --project-dir pointing at the generated site (contains src/)",
        "for the matrix lane: a reachable --url (or $GATE_M_URL / $GATE_D_URL), node, and Playwright with "
        "Chrome or Chromium installed in scripts/quality (npm install && npx playwright install chromium)",
    ],
    "inputs": ["--project-dir", "--url (or $GATE_M_URL, $GATE_D_URL)", "--routes", "--override (or $AURELIX_GATE_M_OVERRIDE)"],
    "outputs": ["<out>/device-matrix.json", "<out>/*.png (one screenshot per route x device)"],
    "outcome": "whether the site's media code follows the native-<video> policy, and whether every route loads "
               "and behaves on five emulated device profiles without errors, overflow, stuck media or broken tabs",
    "exit_contract": {
        0: "PASS — at least one lane ran and every lane that ran passed (or a FAIL was explicitly overridden, "
           "which is printed with the reason and the user)",
        1: "FAIL — a policy rule or a device-matrix assertion failed and no override was given",
        3: "NOT_MEASURED — neither lane could run (no --project-dir with src/ and no reachable URL)",
    },
    "measures": [
        "policy: WebCodecs VideoDecoder use in src, raw .ivf/.h264/.h265/.hevc/.obu/.av1 files tracked under "
        "public/, <video autoPlay> lacking muted/playsInline, playbackRate assignments (warning)",
        "matrix: HTTP status, page errors, same-origin console errors and failed requests, horizontal overflow, "
        "on-screen videos asked to play whose clock never advances, visible loading indicators after the settle "
        "budget, clipped text in links/buttons/tabs/headings, tablist selection after each click",
    ],
    "cannot_see": [
        "real hardware decoders: emulation uses desktop Chrome's decoders — the 2026-10-01 Android failure "
        "PASSED emulation; only the static policy and the manual S24 Ultra / iPhone Safari checklist catch it",
        "Safari/WebKit and HEVC playback (Chrome only)",
        "routes not passed in --routes (default: / only)",
        "below-the-fold content beyond what one viewport shows after the settle budget (no scrolling)",
        "visual correctness: it asserts behaviour, not design",
    ],
    "reachable_from": [
        "run_pipeline.py (stage after Gate E, --stop-at full, when a deploy URL is set)",
        "standalone CLI",
    ],
    "cost": "policy: < 1 s. matrix: ~10-15 s per route (five devices run concurrently, 7 s settle each); "
            "requires a live deployment and a local Chrome/Chromium",
}


def main() -> int:
    if describe(CAPABILITY):
        return 0
    ap = argparse.ArgumentParser(description="Gate M: device & media compatibility")
    ap.add_argument("--project-dir", type=Path)
    ap.add_argument("--url", default=os.environ.get("GATE_M_URL") or os.environ.get("GATE_D_URL"))
    ap.add_argument("--routes", default="/")
    ap.add_argument("--out", default="gate-m-report")
    ap.add_argument("--override", default=os.environ.get("AURELIX_GATE_M_OVERRIDE", ""))
    a = ap.parse_args()
    env = dict(os.environ, QA_OVERRIDE=a.override)
    codes: list[int] = []
    if a.project_dir and (a.project_dir / "src").is_dir():
        codes.append(subprocess.run(["node", str(QUALITY / "media-policy.mjs"), "--root", str(a.project_dir.resolve())], env=env).returncode)
    else:
        print("Gate M: policy lane NOT_MEASURED (no --project-dir with src/)")
    if a.url:
        codes.append(subprocess.run(["node", str(QUALITY / "device-matrix.mjs"), "--base", a.url, "--routes", a.routes, "--out", a.out],
                                    env=env, cwd=str(QUALITY)).returncode)
    else:
        print("Gate M: matrix lane NOT_MEASURED (no --url / GATE_M_URL / GATE_D_URL)")
    print("Gate M: REMINDER — real-device checklist (Galaxy S24 Ultra Chrome + iPhone Safari) is required for any "
          "media/animation change; this gate cannot see hardware decoders.")
    ran = [c for c in codes if c != NOT_MEASURED]
    if not ran:
        print("Gate M: NOT_MEASURED — nothing was checked")
        return NOT_MEASURED
    if any(c != 0 for c in ran):
        print("Gate M: FAIL")
        return 1
    print("Gate M: PASS" + (f" (override in effect: {a.override})" if a.override else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
