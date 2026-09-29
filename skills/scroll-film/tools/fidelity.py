"""Anchor fidelity: does the clip land on the exact mark?
usage: python fidelity.py --video clip.mp4 --anchor anchor.png [--end|--start] [--box x,y,w,h]
Compares the clip's last (or first) frame to the anchor inside the mark box (auto = centre 30%).
Reports masked-ink IoU and mean RGB delta. Gate: IoU >= 0.95 before vector overlay; overlay the exact
vector on the final held frame in the player regardless (C4).
Also: silhouette lock test for 3D renders -> compare two PNGs with --a/--b.
"""
import argparse, subprocess, tempfile
import numpy as np
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("--video"); ap.add_argument("--anchor"); ap.add_argument("--a"); ap.add_argument("--b")
ap.add_argument("--start", action="store_true"); ap.add_argument("--box")
a = ap.parse_args()
if a.video:
    t = tempfile.mktemp(suffix=".png")
    seek = ["-ss", "0"] if a.start else ["-sseof", "-0.05"]
    subprocess.run(["ffmpeg", "-v", "error", *seek, "-i", a.video, "-frames:v", "1", "-y", t], check=True)
    A, B = Image.open(t).convert("RGB"), Image.open(a.anchor).convert("RGB")
else:
    A, B = Image.open(a.a).convert("RGB"), Image.open(a.b).convert("RGB")
B = B.resize(A.size, Image.LANCZOS); W, H = A.size
x, y, w, h = map(int, a.box.split(",")) if a.box else (int(W * .35), int(H * .35), int(W * .3), int(H * .3))
pa = np.asarray(A)[y:y + h, x:x + w].astype(int); pb = np.asarray(B)[y:y + h, x:x + w].astype(int)
sat = lambda p: (p.max(-1) - p.min(-1)) > 60          # saturated brand ink vs dark ground
ia, ib = sat(pa), sat(pb); iou = (ia & ib).sum() / max(1, (ia | ib).sum())
delta = np.abs(pa - pb)[ia & ib].mean() if (ia & ib).any() else 999
print({"mark_iou": round(float(iou), 4), "mean_rgb_delta": round(float(delta), 2), "pass": bool(iou >= 0.95)})
