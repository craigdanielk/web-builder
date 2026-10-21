"""Rebuild the operator-authored capture bundle from source/index.html.

Run after ANY edit to source/index.html — the build harvests the bundle, not the HTML.
  python3 intake/thuris/make_capture_bundle.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
html = (HERE / "source" / "index.html").read_text(encoding="utf-8")
record = {
    "url": "https://thuris.myshopify.com/",
    "html": html,
    "html_length": len(html),
    "http_status": 200,
    "fetch_error": None,
    "source": "operator-authored",
    "copy_ref": "THURIS-launch-copy.md v1",
}
bundle = HERE / "capture-bundle"
(bundle / "captures").mkdir(parents=True, exist_ok=True)
(bundle / "captures" / "000_home.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
(bundle / "captures_manifest.json").write_text(json.dumps({"captures": [record]}, ensure_ascii=False), encoding="utf-8")
print(f"capture bundle rebuilt: {len(html)} chars of html")
