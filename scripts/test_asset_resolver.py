#!/usr/bin/env python3
"""Extracted imagery must reach the build; unresolvable slots must be declared.

Runs against a synthetic fixture AND the real extraction-data.json from the
Cape Crypto cold run — the synthetic-only version of this suite is exactly
what let the brief's first draft ship a resolver that reads a key
(`extraction_data["images"]`) the real pipeline never produces.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.section_artifact import SectionArtifact
from lib.asset_resolver import (
    resolve_assets, gaps, _download_verbose, DownloadError, _local_rel_path, _looks_like_image,
)

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
     re.search(r'/images/aluma-[0-9a-f]+\.png', out.tsx) is not None, out.tsx)
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
# Group 1b: filename collision. Two DIFFERENT remote URLs sharing a basename
# ("logo.png" under two different paths — exactly the kind of name that
# repeats across a real site's /assets/ and /content/ directories) must
# resolve to two DIFFERENT local files, each containing its own bytes. A
# resolver that names the local file from the basename alone maps both to
# the same destination; the second URL then finds that destination already
# "exists" and adopts the first URL's bytes without even attempting its own
# fetch — a wrong-but-valid image that passes every other check (non-zero
# size, real magic bytes) while silently showing the wrong picture.
# ---------------------------------------------------------------------------

def make_fake_download(url_to_bytes):
    """download_fn that returns different, known bytes per URL, so a
    collision is detectable by content, not just by non-zero size."""
    def _fn(url, dest):
        payload = url_to_bytes[url]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        return len(payload)
    return _fn


COLLISION_TSX = (
    '<section>'
    '<img src="https://cdn.example.com/assets/partners/logo.png" alt="Partner A" />'
    '<img src="https://cdn.example.com/content/brand/logo.png" alt="Partner B" />'
    '</section>'
)
COLLISION_BYTES = {
    "https://cdn.example.com/assets/partners/logo.png": b"PARTNER-A-BYTES",
    "https://cdn.example.com/content/brand/logo.png": b"PARTNER-B-BYTES",
}
collision_art = SectionArtifact(
    tsx=COLLISION_TSX, archetype="LOGO-BAR", variant="strip", section_uid="coll1",
    intensity="subtle", origin="supabase_template", provenance=[], assets=[], animation=None,
)
collision_extraction = {"assets": {"images": [
    {"src": "https://cdn.example.com/assets/partners/logo.png", "alt": "Partner A", "sectionIndex": None},
    {"src": "https://cdn.example.com/content/brand/logo.png", "alt": "Partner B", "sectionIndex": None},
]}}
collision_out = resolve_assets(
    collision_art, collision_extraction, TMP / "public-collision",
    download_fn=make_fake_download(COLLISION_BYTES),
)
collision_extracted = [a for a in collision_out.assets if a["origin"] == "extracted"]
collision_local_srcs = {a["src"] for a in collision_extracted}
test("both same-basename URLs resolve (not one silently dropped)",
     len(collision_extracted) == 2, str(collision_out.assets))
test("both resolve to DIFFERENT local paths (no basename collision)",
     len(collision_local_srcs) == 2, str(collision_local_srcs))

# Verify each local file holds ITS OWN bytes, not the other URL's — this is
# the actual "wrong image shipped" failure mode, not just a missing entry.
_written_contents = []
_detail_lines = []
for a in collision_extracted:
    p = TMP / "public-collision" / a["src"].lstrip("/")
    content = p.read_bytes() if p.exists() else b""
    _written_contents.append(content)
    _detail_lines.append(f"{a['src']} -> {content!r}")
test("each resolved file contains its own source's bytes (no wrong-image swap)",
     set(_written_contents) == set(COLLISION_BYTES.values()) and len(set(_written_contents)) == 2,
     "; ".join(_detail_lines))

# ---------------------------------------------------------------------------
# Group 1c: the on-disk cache must not adopt a bad leftover. If an earlier
# run crashed mid-download (or an old bug wrote a 403 page to disk), a
# zero-byte or non-image file can sit at the destination path. The
# `dest.exists()` cache-hit branch must not treat that as "already
# downloaded, valid" — it must redownload.
# ---------------------------------------------------------------------------

CACHE_URL = "https://x.example.com/assets/broken.png"
cache_pub = TMP / "public-cache-validate"
cache_rel = _local_rel_path(CACHE_URL)
cache_dest = cache_pub / cache_rel
cache_dest.parent.mkdir(parents=True, exist_ok=True)
cache_dest.write_bytes(b"")  # simulate a zero-byte leftover from a failed prior run

_cache_download_calls = []


def _counting_real_bytes_download(url, dest):
    _cache_download_calls.append(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = b"\x89PNG\r\n\x1a\n" + b"real-png-bytes"
    dest.write_bytes(payload)
    return len(payload)


cache_art = SectionArtifact(
    tsx=f'<img src="{CACHE_URL}" alt="Broken" />', archetype="HERO", variant="centered",
    section_uid="cache1", intensity="subtle", origin="supabase_template",
    provenance=[], assets=[], animation=None,
)
cache_out = resolve_assets(
    cache_art, {"assets": {"images": [{"src": CACHE_URL, "sectionIndex": None}]}},
    cache_pub, download_fn=_counting_real_bytes_download,
)
test("a zero-byte leftover at the cache path triggers a redownload, not a silent adopt",
     _cache_download_calls == [CACHE_URL], f"download calls: {_cache_download_calls}")
test("after redownload, the file on disk holds the real bytes, not the empty leftover",
     cache_dest.read_bytes().startswith(b"\x89PNG"), cache_dest.read_bytes())

# Same check for a non-image (but non-empty) leftover — e.g. an HTML error
# page an older, pre-magic-byte-check version of this module could have
# saved under an image extension.
NONIMAGE_URL = "https://x.example.com/assets/also-broken.png"
nonimage_rel = _local_rel_path(NONIMAGE_URL)
nonimage_dest = cache_pub / nonimage_rel
nonimage_dest.parent.mkdir(parents=True, exist_ok=True)
nonimage_dest.write_bytes(b"<html>403 Forbidden</html>")

_nonimage_calls = []


def _counting_download_2(url, dest):
    _nonimage_calls.append(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = b"\x89PNG\r\n\x1a\n" + b"real-png-bytes-2"
    dest.write_bytes(payload)
    return len(payload)


nonimage_art = SectionArtifact(
    tsx=f'<img src="{NONIMAGE_URL}" alt="AlsoBroken" />', archetype="HERO", variant="centered",
    section_uid="cache2", intensity="subtle", origin="supabase_template",
    provenance=[], assets=[], animation=None,
)
nonimage_out = resolve_assets(
    nonimage_art, {"assets": {"images": [{"src": NONIMAGE_URL, "sectionIndex": None}]}},
    cache_pub, download_fn=_counting_download_2,
)
test("a non-image (HTML error page) leftover at the cache path is not adopted either",
     _nonimage_calls == [NONIMAGE_URL], f"download calls: {_nonimage_calls}")

# ---------------------------------------------------------------------------
# Group 1d: _looks_like_image must not false-negative valid formats. A
# false negative silently downgrades a resolvable asset to unresolved,
# costing coverage quietly rather than loudly. WEBP matters concretely —
# dave.webp (about section, see Group 2) is a real WEBP reference in this
# project, and would need this format to ever resolve if extraction data
# ever does include it.
# ---------------------------------------------------------------------------

_magic_dir = TMP / "magic-bytes"
_magic_dir.mkdir(parents=True, exist_ok=True)


def _write_and_check(name, payload):
    p = _magic_dir / name
    p.write_bytes(payload)
    return _looks_like_image(p)


test("WEBP magic bytes (RIFF....WEBP) are recognized",
     _write_and_check("a.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16))
test("AVIF magic bytes (ftyp box, avif brand) are recognized",
     _write_and_check("a.avif", b"\x00\x00\x00\x18ftypavif\x00\x00\x00\x00" + b"\x00" * 16))
test("GIF89a magic bytes are recognized",
     _write_and_check("a.gif", b"GIF89a" + b"\x00" * 16))
test("SVG preceded by an XML comment is recognized (not just bare <svg)",
     _write_and_check("a.svg", b'<!-- generated by extractor -->\n<svg xmlns="http://www.w3.org/2000/svg">'))
test("SVG preceded by a UTF-8 BOM is recognized",
     _write_and_check("b.svg", b"\xef\xbb\xbf<svg xmlns=\"...\">"))
test("an HTML error page is still correctly rejected (not a false positive)",
     not _write_and_check("bad.html", b"<html><body>403 Forbidden</body></html>"))

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

    # 2b. The real ABOUT section — dave.webp is referenced in the build and is
    # genuinely absent from extraction-data.json's 12 images, because that file
    # is a crawl of the HOMEPAGE ONLY and dave.webp lives on /about. It is
    # nonetheless real, live, same-origin source imagery (verified: 13206 bytes
    # off capecrypto.com), so it must be downloaded and localised.
    #
    # This assertion used to demand the opposite — that dave.webp come back
    # unresolved with the remote URL left in the tsx. That is what shipped: the
    # deployed /about hotlinked capecrypto.com for the one image on the page.
    # "Not in the single page we crawled" is not "not from this site".
    ABOUT_TSX = '<Image src="https://capecrypto.com/content/images/2026/06/dave.webp" alt="Dave" fill />'
    about_art = SectionArtifact(tsx=ABOUT_TSX, archetype="ABOUT", variant="editorial-split",
                                section_uid="about1", intensity="subtle", origin="supabase_template",
                                provenance=[], assets=[], animation=None)
    about_out = resolve_assets(about_art, real, TMP / "public-real", download_fn=fake_download)
    test("dave.webp resolves as same-origin source imagery the homepage crawl never saw",
         any(a["origin"] == "extracted" and "dave" in a["src"] for a in about_out.assets),
         str(about_out.assets))
    test("resolved dave.webp is rewritten off capecrypto.com (no hotlink ships)",
         "capecrypto.com" not in about_out.tsx, about_out.tsx)

    # 2b-ii. The widening is to the SOURCE SITE, not to the open internet. An
    # image URL on a host the crawl never vouched for is still refused.
    FOREIGN_TSX = '<Image src="https://cdn.evil-example.com/tracker.png" alt="x" fill />'
    foreign_art = SectionArtifact(tsx=FOREIGN_TSX, archetype="ABOUT", variant="editorial-split",
                                  section_uid="foreign1", intensity="subtle", origin="supabase_template",
                                  provenance=[], assets=[], animation=None)
    foreign_out = resolve_assets(foreign_art, real, TMP / "public-foreign", download_fn=fake_download)
    test("an image on a host the crawl never served is still reported unresolved",
         all(a["origin"] == "unresolved" for a in foreign_out.assets) and foreign_out.assets,
         str(foreign_out.assets))

    # 2b-iii. A template's own documentation is prose, not markup. ABOUT
    # editorial-split's docblock explains that `<Image src="">` throws in
    # next/image; scanning the raw file read that sentence as an empty image
    # slot and filed a generation job against it. Every ABOUT section in the
    # cape-crypto build carried one of these phantoms.
    COMMENTED_TSX = (
        '/**\n'
        ' * The image is optional. `<Image src="">` THROWS in next/image, so an\n'
        ' * unresolved src must never reach the DOM.\n'
        ' * Docs also cite https://capecrypto.com/assets/images/partners/xago.png\n'
        ' */\n'
        '// see also src="/placeholder.svg"\n'
        'export default function A() { return <p>It doesn\'t render an image.</p>; }\n'
    )
    commented_art = SectionArtifact(tsx=COMMENTED_TSX, archetype="ABOUT", variant="editorial-split",
                                    section_uid="cmt1", intensity="subtle", origin="supabase_template",
                                    provenance=[], assets=[], animation=None)
    commented_out = resolve_assets(commented_art, real, TMP / "public-cmt", download_fn=fake_download)
    test("src=\"\" inside a doc comment is not mistaken for an image slot",
         commented_out.assets == [], str(commented_out.assets))
    test("a section that is all prose files no phantom generation job",
         gaps(commented_out) == [], str(gaps(commented_out)))
    test("comments survive resolution (only the SCAN is masked, not the output)",
         "THROWS in next/image" in commented_out.tsx, commented_out.tsx)

    # An apostrophe in JSX prose must not derail the comment mask — a quote-
    # tracking tokenizer would treat "doesn't" as an unterminated string and
    # blank the rest of the file, silently hiding every real slot after it.
    APOS_TSX = (
        '// it doesn\'t matter\n'
        '<div><p>It doesn\'t render.</p>'
        '<img src="https://capecrypto.com/assets/images/partners/xago.png?v=abc" /></div>'
    )
    apos_art = SectionArtifact(tsx=APOS_TSX, archetype="ABOUT", variant="editorial-split",
                               section_uid="apos1", intensity="subtle", origin="supabase_template",
                               provenance=[], assets=[], animation=None)
    apos_out = resolve_assets(apos_art, real, TMP / "public-apos", download_fn=fake_download)
    test("an apostrophe in JSX prose does not blind the scanner to a later real image",
         any(a["origin"] == "extracted" for a in apos_out.assets), str(apos_out.assets))

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
# Group 3: exactly ONE genuinely networked test — a single live HTTP call
# against capecrypto.com through resolve_assets() end-to-end (no injected
# mock). Everything else in this suite uses `fake_download`; this is the
# sole exception, and it is not run in CI/offline by default.
#
# A prior version of this test diagnosed a real download failure as "host
# unreachable" when the true cause was the origin server 403-ing Python's
# default User-Agent — `urlopen()` without headers raises HTTPError, which a
# bare `except Exception: unreachable` swallows into the wrong story. That
# sent the next person to debug connectivity instead of headers. This
# version wraps `_download_verbose` so the real cause (DNS/connection vs
# HTTP status vs timeout vs non-image response) drives the verdict:
# offline/timeout -> SKIP with that reason, HTTP error or non-image -> FAIL
# with that reason, success -> asserted end-to-end including on-disk bytes.
#
# Off by default (opt in with ASSET_RESOLVER_RUN_NETWORK_TEST=1) so this
# suite doesn't hammer a third-party production site or flake in CI/offline
# runs on every invocation.
# ---------------------------------------------------------------------------

if not os.environ.get("ASSET_RESOLVER_RUN_NETWORK_TEST"):
    skip("real network download of a real extracted asset",
         "opt-in only — set ASSET_RESOLVER_RUN_NETWORK_TEST=1 to run it")
elif not REAL_EXTRACTION_PATH.exists():
    skip("real network download of a real extracted asset", "extraction-data.json not found")
else:
    real = json.loads(REAL_EXTRACTION_PATH.read_text())
    _diagnosis = {}

    def _diagnosing_download(url, dest):
        try:
            return _download_verbose(url, dest)
        except DownloadError as e:
            _diagnosis["error"] = str(e)
            return 0

    net_art = SectionArtifact(
        tsx='<img src="https://capecrypto.com/assets/images/partners/numeral.svg?v=809f7e496a" alt="Numeral" />',
        archetype="LOGO-BAR", variant="strip", section_uid="net1",
        intensity="subtle", origin="supabase_template",
        provenance=[], assets=[], animation=None,
    )
    net_out = resolve_assets(net_art, real, TMP / "public-network", download_fn=_diagnosing_download)
    net_extracted = [a for a in net_out.assets if a["origin"] == "extracted"]

    if not net_extracted and "error" in _diagnosis:
        msg = _diagnosis["error"]
        if msg.startswith("host unreachable") or msg == "timed out":
            skip("real network download of a real extracted asset", f"network offline: {msg}")
        else:
            test(f"real network download of a real extracted asset succeeds (observed: {msg})", False, msg)
    else:
        test("real network download resolves the logo through resolve_assets() end-to-end",
             bool(net_extracted) and net_extracted[0]["bytes"] > 0, str(net_out.assets))
        if net_extracted:
            real_path = TMP / "public-network" / net_extracted[0]["src"].lstrip("/")
            test("downloaded file is real image bytes on disk (SVG magic header)",
                 real_path.exists() and real_path.read_bytes()[:5] in (b"<?xml", b"<svg "),
                 f"first bytes: {real_path.read_bytes()[:20] if real_path.exists() else 'MISSING'}")

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped\n")
sys.exit(1 if FAIL else 0)
