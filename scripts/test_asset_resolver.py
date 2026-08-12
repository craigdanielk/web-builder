#!/usr/bin/env python3
"""Extracted imagery must reach the build; unresolvable slots must be declared.

Runs against a synthetic fixture AND the real extraction-data.json from the
Cape Crypto cold run — the synthetic-only version of this suite is exactly
what let the brief's first draft ship a resolver that reads a key
(`extraction_data["images"]`) the real pipeline never produces.
"""
import json
import os
import socket
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.section_artifact import SectionArtifact
from lib.asset_resolver import resolve_assets, gaps

PASS = 0
FAIL = 0
SKIP = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


def skip(name, reason):
    global SKIP
    SKIP += 1
    print(f"  ○ SKIP {name} ({reason})")


def fake_download(url, dest):
    """No network. Writes deterministic fake bytes keyed by URL so tests can
    tell which URL a download call was for."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = f"fake-bytes-for:{url}".encode()
    dest.write_bytes(payload)
    return len(payload)


TMP = Path(tempfile.mkdtemp(prefix="asset-resolver-test-"))

# ---------------------------------------------------------------------------
# Group 1: synthetic fixture, matching the real assets.images / assets.logos
# shape (src key for images, url key for logos) rather than the brief's
# {"images": [...]} draft, which the real pipeline never emits.
# ---------------------------------------------------------------------------

TSX = '''export default function Logos() {
  return (<section><img src="https://capecrypto.com/media/aluma.png" alt="Aluma" /></section>);
}'''

art = SectionArtifact(tsx=TSX, archetype="LOGO-BAR", variant="strip",
                      section_uid="abc123", intensity="subtle",
                      origin="supabase_template", provenance=[], assets=[], animation=None)

EXTRACTION = {"assets": {"images": [{"src": "https://capecrypto.com/media/aluma.png",
                                     "alt": "Aluma", "sectionIndex": None}]}}

out = resolve_assets(art, EXTRACTION, TMP / "public-1", download_fn=fake_download)
test("remote src is rewritten to a local path",
     "/images/aluma.png" in out.tsx, out.tsx)
test("no remote capecrypto.com src survives",
     "https://capecrypto.com" not in out.tsx)
test("resolution is recorded in assets",
     any(a["origin"] == "extracted" for a in out.assets), str(out.assets))

art2 = SectionArtifact(tsx='<section><img src="/placeholder.svg" alt="" /></section>',
                       archetype="HERO", variant="centered", section_uid="d4",
                       intensity="subtle", origin="supabase_template",
                       provenance=[], assets=[], animation=None)
out2 = resolve_assets(art2, {"assets": {"images": []}}, TMP / "public-1", download_fn=fake_download)
test("unresolvable slot is marked, not silently placeheld",
     any(a["origin"] == "unresolved" for a in out2.assets), str(out2.assets))
test("placeholder src is NOT rewritten when nothing resolves",
     '/placeholder.svg' in out2.tsx, out2.tsx)
test("gaps() describes the unresolved slot for generation",
     len(gaps(out2)) == 1 and "archetype" in gaps(out2)[0], str(gaps(out2)))

# ---------------------------------------------------------------------------
# Group 2: real extraction-data.json from the Cape Crypto cold run.
# This is the file the correction pointed at. If the resolver only reads
# `extraction_data["images"]` (a key that doesn't exist here), every image
# below resolves to zero and this whole group fails.
# ---------------------------------------------------------------------------

REAL_EXTRACTION_PATH = Path(
    "/Users/craigkunte/Developer/GitHub/tenants/cape-crypto/builds/task4-verify/"
    "extractions/cape-crypto-9d4fcf88/extraction-data.json"
)

if not REAL_EXTRACTION_PATH.exists():
    skip("real extraction-data.json group", f"not found at {REAL_EXTRACTION_PATH}")
else:
    real = json.loads(REAL_EXTRACTION_PATH.read_text())
    real_assets = real["assets"]
    test("fixture sanity: real file has assets.images (not top-level images)",
         "assets" in real and "images" not in real and len(real_assets["images"]) == 12,
         f"assets.images={len(real_assets.get('images', []))}")
    test("fixture sanity: real file has assets.logos",
         len(real_assets["logos"]) == 5, f"logos={len(real_assets.get('logos', []))}")

    # 2a. The LOGO-BAR section as actually generated for cape-crypto: the URL
    # lives inside a JS object literal (`image: 'https://...'`), not a bare
    # src="..." attribute, and its query-string cache-buster (?v=6bdf3274e4)
    # differs from the one in extraction-data.json (?v=809f7e496a) — a real
    # crawl/build timing mismatch, not a fixture artifact.
    LOGO_BAR_TSX = """'use client';
import { motion } from 'framer-motion';
import Image from 'next/image';

const logos = [
  { image: 'https://capecrypto.com/assets/images/partners/numeral.svg?v=6bdf3274e4', alt: 'Numeral' },
  { image: 'https://capecrypto.com/assets/images/partners/aluma.svg?v=6bdf3274e4', alt: 'Aluma' },
  { image: 'https://capecrypto.com/assets/images/partners/xago.png?v=6bdf3274e4', alt: 'Xago' },
  { image: 'https://capecrypto.com/assets/images/partners/idatco.png?v=6bdf3274e4', alt: 'Idatco' },
];

export default function LogoBarScrollingMarquee() {
  return (
    <div className="flex">
      {logos.map((logo, i) => (
        <Image key={i} src={logo.image} alt={logo.alt} fill className="object-contain" />
      ))}
    </div>
  );
}"""
    logo_art = SectionArtifact(tsx=LOGO_BAR_TSX, archetype="LOGO-BAR", variant="scrolling-marquee",
                               section_uid="logo1", intensity="subtle", origin="supabase_template",
                               provenance=[], assets=[], animation=None)
    logo_out = resolve_assets(logo_art, real, TMP / "public-real", download_fn=fake_download)
    extracted_logo_count = sum(1 for a in logo_out.assets if a["origin"] == "extracted")
    test("all 4 partner logos resolve despite cache-buster query mismatch",
         extracted_logo_count == 4, str(logo_out.assets))
    test("resolved logo srcs are rewritten off capecrypto.com entirely",
         "capecrypto.com" not in logo_out.tsx, logo_out.tsx)

    # 2b. The real ABOUT section — dave.webp is referenced in the build but
    # is genuinely absent from extraction-data.json's 12 images. It must
    # come back unresolved, not silently pass through or get placeheld.
    ABOUT_TSX = '<Image src="https://capecrypto.com/content/images/2026/06/dave.webp" alt="Dave" fill />'
    about_art = SectionArtifact(tsx=ABOUT_TSX, archetype="ABOUT", variant="editorial-split",
                                section_uid="about1", intensity="subtle", origin="supabase_template",
                                provenance=[], assets=[], animation=None)
    about_out = resolve_assets(about_art, real, TMP / "public-real", download_fn=fake_download)
    test("dave.webp (not present in extraction-data.json) is reported unresolved",
         any(a["origin"] == "unresolved" and "dave.webp" in a["src"] for a in about_out.assets),
         str(about_out.assets))
    test("unresolved dave.webp src is left untouched in tsx (still the remote URL)",
         "https://capecrypto.com/content/images/2026/06/dave.webp" in about_out.tsx, about_out.tsx)

    # 2c. sectionIndex-scoped placeholder fill: a HERO placeholder should
    # only be filled from an extracted image whose sectionIndex matches
    # THIS section (sectionIndex 0 → flag-sa.png / app-screenshot.png /
    # the two badge images), never from an unrelated section's imagery.
    hero_art = SectionArtifact(
        tsx='<section><img src="/placeholder.svg" alt="" /></section>',
        archetype="HERO", variant="centered", section_uid="hero1",
        intensity="subtle", origin="supabase_template",
        provenance=[], assets=[], animation=None,
    )
    hero_out = resolve_assets(hero_art, real, TMP / "public-real",
                               section_index=0, download_fn=fake_download)
    filled = [a for a in hero_out.assets if a["origin"] == "extracted"]
    section0_names = ("flag-sa", "app-screenshot", "google-play-badge", "app-store-badge")
    test("placeholder in a sectionIndex=0 artifact fills from a sectionIndex=0 extracted image",
         len(filled) == 1 and any(n in filled[0]["src"] for n in section0_names),
         str(hero_out.assets))
    test("filled slot is genuinely local (no invented content, real extracted src)",
         bool(filled) and filled[0]["src"].startswith("/images/"), str(hero_out.assets))

    other_section_art = SectionArtifact(
        tsx='<section><img src="/placeholder.svg" alt="" /></section>',
        archetype="TESTIMONIAL", variant="single", section_uid="test1",
        intensity="subtle", origin="supabase_template",
        provenance=[], assets=[], animation=None,
    )
    # sectionIndex=99 has no extracted images at all in the real data —
    # must come back unresolved, proving the fill is scoped, not "any image".
    other_out = resolve_assets(other_section_art, real, TMP / "public-real",
                                section_index=99, download_fn=fake_download)
    test("placeholder with no matching sectionIndex stays unresolved (fill is scoped, not global)",
         any(a["origin"] == "unresolved" for a in other_out.assets), str(other_out.assets))

    # 2d. bytes are non-zero and recorded, and the file actually landed on disk.
    written = list((TMP / "public-real" / "images").glob("*"))
    test("resolved assets are actually written to public_dir/images",
         len(written) >= 4, [p.name for p in written])
    test("recorded byte counts are non-zero for every extracted asset",
         all(a["bytes"] > 0 for a in logo_out.assets if a["origin"] == "extracted"),
         str(logo_out.assets))

# ---------------------------------------------------------------------------
# Group 3: real network fetch of one real extraction asset. Guarded — if
# there's no network path to capecrypto.com, this is reported as a SKIP with
# a reason, never counted as a pass.
# ---------------------------------------------------------------------------

def _network_reachable(host="capecrypto.com", timeout=3) -> bool:
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        urllib.request.urlopen(f"https://{host}/", timeout=timeout)
        return True
    except Exception:
        return False


if REAL_EXTRACTION_PATH.exists():
    if os.environ.get("ASSET_RESOLVER_SKIP_NETWORK"):
        skip("real network download of a real extracted asset", "ASSET_RESOLVER_SKIP_NETWORK set")
    elif not _network_reachable():
        skip("real network download of a real extracted asset", "capecrypto.com unreachable from this host")
    else:
        real = json.loads(REAL_EXTRACTION_PATH.read_text())
        net_art = SectionArtifact(
            tsx='<img src="https://capecrypto.com/assets/images/logo-white.svg?v=809f7e496a" alt="logo" />',
            archetype="LOGO-BAR", variant="strip", section_uid="net1",
            intensity="subtle", origin="supabase_template",
            provenance=[], assets=[], animation=None,
        )
        net_out = resolve_assets(net_art, real, TMP / "public-network")  # real download_fn (default)
        net_extracted = [a for a in net_out.assets if a["origin"] == "extracted"]
        test("real network download resolves the logo and writes real bytes",
             bool(net_extracted) and net_extracted[0]["bytes"] > 0, str(net_out.assets))
else:
    skip("real network download of a real extracted asset", "extraction-data.json not found")

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped\n")
sys.exit(1 if FAIL else 0)
