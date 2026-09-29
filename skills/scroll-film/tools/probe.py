"""Scroll-film QA probe: frame pacing under wheel scroll + screenshots at progress points.
usage: python probe.py --url http://localhost:3000/ [--section 'section[aria-label="Trend Digital"]']
                       [--throttle 1,4] [--shots out_dir] [--points 0,0.15,0.4,0.7,0.86,1]
Reports median/p95 frame ms, fps, frames >50 ms per throttle profile (C7: >=55 fps median at 4x CPU).
Desktop 1440x900 + mobile 390x844 screenshots at each progress point of the pinned section.
"""
import argparse, json
from pathlib import Path
from playwright.sync_api import sync_playwright
ap = argparse.ArgumentParser(); ap.add_argument("--url", required=True); ap.add_argument("--section", default="section")
ap.add_argument("--throttle", default="1,4"); ap.add_argument("--shots"); ap.add_argument("--points", default="0,0.15,0.4,0.7,0.86,1")
a = ap.parse_args()
with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--enable-gpu-rasterization"])
    for rate in [float(x) for x in a.throttle.split(",")]:
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.context.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": rate})
        pg.goto(a.url, wait_until="load"); pg.wait_for_timeout(6000)
        pg.evaluate("window.__d=[];let l=performance.now();(function f(t){window.__d.push(t-l);l=t;requestAnimationFrame(f)})(l)")
        for _ in range(90): pg.mouse.wheel(0, 120); pg.wait_for_timeout(60)
        pg.wait_for_timeout(1500)
        d = sorted(pg.evaluate("window.__d.slice(5)")); n = len(d)
        print(json.dumps({"cpu_throttle": rate, "median_ms": round(d[n // 2], 1), "p95_ms": round(d[int(n * .95)], 1),
                          "fps_median": round(1000 / d[n // 2]), "frames_over_50ms": sum(x > 50 for x in d)}))
        pg.close()
    if a.shots:
        out = Path(a.shots); out.mkdir(parents=True, exist_ok=True)
        for name, vp in [("desktop", {"width": 1440, "height": 900}), ("mobile", {"width": 390, "height": 844})]:
            pg = b.new_page(viewport=vp); pg.goto(a.url, wait_until="load"); pg.wait_for_timeout(5000)
            total = pg.evaluate(f"(()=>{{const e=document.querySelector({json.dumps(a.section)});return e.offsetHeight-innerHeight}})()")
            for p in [float(x) for x in a.points.split(",")]:
                pg.evaluate(f"window.scrollTo(0,{int(total * p)})"); pg.wait_for_timeout(1200)
                pg.screenshot(path=str(out / f"{name}-{p}.png"))
            pg.close()
        print(f"shots -> {out}")
    b.close()
