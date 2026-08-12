#!/usr/bin/env python3
"""An <Image> with an empty src does not degrade — next/image THROWS.

`about/03-about.tsx:23` shipped `<Image src="" alt="" fill />` because the
template's {image_url} slot had no harvest to fill it. That is not a cosmetic
gap: next/image raises on an empty src, so the whole route errors at runtime
while every string/brace check passes.

`apply_template_fill` already drops a PAIRED one-line element whose slots all
came out empty (`<a href="{url}">{text}</a>`). Self-closing elements — every
image in the library — were not covered. Same rule, same mechanism.

Sourced or absent. An image whose src cannot be resolved must not render.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import orchestrate  # noqa: E402

apply_template_fill = orchestrate.apply_template_fill

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


# ── the real failing shape, from the real build ──────────────────────────
CODE = '''<div className="relative aspect-[4/5]">
  <Image src="{image_url}" alt="{image_alt}" fill className="object-cover" />
</div>'''

out = apply_template_fill(CODE, {"image_url": "", "image_alt": ""})
test("empty-src <Image /> is dropped entirely",
     "<Image" not in out, repr(out))
test("...and the surrounding markup survives",
     '<div className="relative aspect-[4/5]">' in out and "</div>" in out,
     repr(out))
test("...leaving no empty src to throw on",
     'src=""' not in out, repr(out))

# ── a resolved image must still render ───────────────────────────────────
out = apply_template_fill(
    CODE, {"image_url": "/images/team.jpg", "image_alt": "The team"})
test("a filled <Image /> is kept",
     "<Image" in out and "/images/team.jpg" in out, repr(out))
test("...with its alt text intact", "The team" in out, repr(out))

# ── partially filled: alt present, src empty — still cannot render ───────
out = apply_template_fill(CODE, {"image_url": "", "image_alt": "The team"})
test("alt without src still drops the element (src is what throws)",
     "<Image" not in out, repr(out))

# ── lowercase <img> is the same hazard for layout, same rule ─────────────
out = apply_template_fill(
    '<img src="{hero_src}" alt="{hero_alt}" className="w-full" />',
    {"hero_src": "", "hero_alt": ""})
test("empty <img /> is dropped too", "<img" not in out, repr(out))

# ── elements with NO token are never touched ─────────────────────────────
STATIC = '<Image src="/logo.svg" alt="Logo" width={120} height={40} />'
out = apply_template_fill(STATIC, {"unrelated": "x"})
test("a literal element the fill never claimed is left alone",
     "<Image" in out and "/logo.svg" in out, repr(out))

# ── className-only emptiness must NOT trigger a drop ─────────────────────
out = apply_template_fill(
    '<div className="{wrapper_class}"><span>Real copy</span></div>',
    {"wrapper_class": ""})
test("an empty className alone does not delete a container holding content",
     "Real copy" in out, repr(out))

# ── media is judged on src ALONE ─────────────────────────────────────────
# next/image throws on an empty src whatever else is populated, so a literal
# alt cannot rescue the element. This is stricter than the generic
# all-attributes-empty rule, and deliberately so: for media, src is not one
# attribute among several, it is the thing that decides whether the route
# renders at all.
# NB: `img` is a RESERVED identifier (templates bind it in map callbacks, e.g.
# `images.map((img) => …)`), so it is never substituted. Use a real slot name.
out = apply_template_fill(
    '<Image src="{image_src}" alt="Fallback description" fill />',
    {"image_src": ""})
test("empty src drops the image even when a literal alt is present",
     "<Image" not in out, repr(out))

# ── but a NON-media self-closing element follows the generic rule ────────
out = apply_template_fill(
    '<Divider label="{sep}" tone="muted" />', {"sep": ""})
test("non-media self-closing element with a non-empty attr is kept",
     "<Divider" in out, repr(out))

out = apply_template_fill('<Divider label="{sep}" />', {"sep": ""})
test("non-media self-closing element with all attrs empty is dropped",
     "<Divider" not in out, repr(out))

print(f"\n  RESULTS: {PASS} passed, {FAIL} failed\n")
sys.exit(1 if FAIL else 0)
