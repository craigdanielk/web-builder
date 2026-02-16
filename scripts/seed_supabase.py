#!/usr/bin/env python3
"""
Aurelix Supabase Seed Script
Seeds all 4 tables: section_presets, industries, section_archetypes, industry_styles
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

# Load .env
ROOT = Path(__file__).parent.parent
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    sys.exit(1)

import urllib.request
import ssl

SSL_CTX = ssl.create_default_context()

HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def supabase_post(table: str, rows: list[dict], upsert: bool = False) -> int:
    """Insert rows into a Supabase table via REST API. Returns count inserted."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = dict(HEADERS)
    if upsert:
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    # Batch in chunks of 100
    total = 0
    for i in range(0, len(rows), 100):
        batch = rows[i:i + 100]
        data = json.dumps(batch).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        try:
            resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
            total += len(batch)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"  ERROR inserting into {table} (batch {i}-{i+len(batch)}): {e.code}")
            print(f"  {body[:500]}")
            # Try one-by-one for this batch to find the problem row
            for row in batch:
                try:
                    data2 = json.dumps([row]).encode("utf-8")
                    req2 = urllib.request.Request(url, data=data2, method="POST", headers=headers)
                    urllib.request.urlopen(req2, context=SSL_CTX, timeout=15)
                    total += 1
                except urllib.error.HTTPError as e2:
                    print(f"    SKIP row: {json.dumps(row)[:200]} — {e2.read().decode()[:200]}")
    return total


def supabase_get(table: str, params: str = "") -> list:
    """GET rows from a Supabase table."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}" if params else f"{SUPABASE_URL}/rest/v1/{table}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=15)
    return json.loads(resp.read().decode("utf-8"))


def supabase_rpc(fn_name: str, params: dict) -> list:
    """Call a Supabase RPC function."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}"
    data = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers=HEADERS)
    resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=15)
    return json.loads(resp.read().decode("utf-8"))


# ─── STEP 1: Seed section_presets (842 rows from CSV) ─────────────

def seed_section_presets():
    print("\n═══ Step 3.1: Seeding section_presets ═══")
    csv_path = ROOT / "docs" / "Supabase_CSV_&_SQL_Migration_Docs" / "aurelix_section_preset_database.csv"
    if not csv_path.exists():
        print(f"  ERROR: CSV not found at {csv_path}")
        return

    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # Rename saas-software -> saas (LOCKED decision)
            industry = r["industry"]
            if industry == "saas-software":
                industry = "saas"

            rows.append({
                "industry": industry,
                "page_type": r["page_type"],
                "component_type": r["component_type"],
                "position": int(r["position"]),
                "section_archetype": r["section_archetype"],
                "section_variant": r["section_variant"],
                "content_direction": r["content_direction"] or None,
                "priority": r["priority"],
            })

    print(f"  Parsed {len(rows)} rows from CSV")
    count = supabase_post("section_presets", rows)
    print(f"  ✓ Inserted {count} rows into section_presets")
    return rows


# ─── STEP 2: Seed industries (25 rows) ────────────────────────────

INDUSTRY_META = {
    "artisan-food": ("Artisan Food", "Coffee roasters, bakeries, specialty food producers"),
    "automotive": ("Automotive", "Car dealerships, auto parts, vehicle services"),
    "beauty-cosmetics": ("Beauty & Cosmetics", "Skincare, makeup, beauty products and treatments"),
    "construction-trades": ("Construction & Trades", "Builders, contractors, trade services"),
    "creative-studios": ("Creative Studios", "Design agencies, digital studios, creative services"),
    "education": ("Education", "Schools, online courses, e-learning platforms"),
    "electronics-tech": ("Electronics & Tech", "Consumer electronics, gadgets, technology retail"),
    "events-venues": ("Events & Venues", "Event planning, conference venues, wedding venues"),
    "fashion-apparel": ("Fashion & Apparel", "Clothing brands, fashion retail, accessories"),
    "health-wellness": ("Health & Wellness", "Fitness, supplements, wellness products"),
    "home-lifestyle": ("Home & Lifestyle", "Home decor, furniture, lifestyle products"),
    "hotels-hospitality": ("Hotels & Hospitality", "Hotels, resorts, travel accommodation"),
    "jewelry-watches": ("Jewelry & Watches", "Fine jewelry, luxury watches, accessories"),
    "kids-baby": ("Kids & Baby", "Children's products, baby gear, toys"),
    "luxury-premium": ("Luxury & Premium", "High-end brands, premium lifestyle products"),
    "medical-dental": ("Medical & Dental", "Medical practices, dental offices, healthcare"),
    "nonprofits-social": ("Nonprofits & Social", "Charities, NGOs, social causes"),
    "outdoor-adventure": ("Outdoor & Adventure", "Outdoor gear, adventure tourism, camping"),
    "pet-products": ("Pet Products", "Pet supplies, veterinary services, animal care"),
    "professional-services": ("Professional Services", "Law firms, consulting, accounting"),
    "real-estate": ("Real Estate", "Property listings, real estate agencies"),
    "restaurants-cafes": ("Restaurants & Cafes", "Dining, cafes, food service establishments"),
    "saas": ("SaaS & Software", "Software-as-a-service, digital products, apps"),
    "sports-fitness": ("Sports & Fitness", "Athletic gear, gym equipment, sports brands"),
    "sustainable-eco": ("Sustainable & Eco", "Eco-friendly products, sustainable brands"),
}


def seed_industries(preset_rows):
    print("\n═══ Step 3.2: Seeding industries ═══")
    industries = sorted(set(r["industry"] for r in preset_rows))
    print(f"  Found {len(industries)} unique industries")

    rows = []
    for ind in industries:
        display, desc = INDUSTRY_META.get(ind, (ind.replace("-", " ").title(), f"{ind} industry"))
        rows.append({
            "handle": ind,
            "display_name": display,
            "description": desc,
        })

    count = supabase_post("industries", rows)
    print(f"  ✓ Inserted {count} rows into industries")


# ─── STEP 3: Seed section_archetypes (72 combos) ──────────────────

ARCHETYPE_DESCRIPTIONS = {
    "NAV": "Site navigation bar with logo, links, and mobile menu",
    "ANNOUNCEMENT-BAR": "Top-of-page promotional or informational banner",
    "FOOTER": "Page footer with links, social media, and legal info",
    "HERO": "Full-width hero section with headline, subhead, and CTA",
    "LOGO-BAR": "Brand logos, press mentions, or partner showcase",
    "TESTIMONIALS": "Customer reviews and social proof",
    "STATS": "Key metrics and numbers with visual emphasis",
    "TRUST-BADGES": "Certifications, guarantees, and trust signals",
    "FEATURES": "Product or service features in grid/list layout",
    "HOW-IT-WORKS": "Step-by-step process explanation",
    "COMPARISON": "Side-by-side comparison of options",
    "PRICING": "Pricing tiers and subscription plans",
    "CTA": "Call-to-action section driving conversions",
    "NEWSLETTER": "Email signup and newsletter subscription",
    "ABOUT": "Brand story, company background, values",
    "TEAM": "Team members with photos and bios",
    "FAQ": "Frequently asked questions with answers",
    "PRODUCT-SHOWCASE": "Product display grid or featured products",
    "PRODUCT-DETAIL": "Single product detail with images, description, variants",
    "PORTFOLIO": "Work samples, case studies, project gallery",
    "BLOG-PREVIEW": "Recent blog posts preview cards",
    "VIDEO": "Video embed or background video section",
    "GALLERY": "Image gallery with various layouts",
    "CONTACT": "Contact form, map, and business info",
    "APP-DOWNLOAD": "Mobile app download promotion",
    "INTEGRATIONS": "Third-party integrations and partnerships",
    "CART-DRAWER": "Shopping cart slide-out drawer",
    "CONTENT": "Generic content section with rich text",
}


def seed_section_archetypes(preset_rows):
    print("\n═══ Step 3.3: Seeding section_archetypes ═══")
    combos = set()
    for r in preset_rows:
        combos.add((r["section_archetype"], r["section_variant"]))

    print(f"  Found {len(combos)} unique archetype-variant combinations")

    rows = []
    for arch, var in sorted(combos):
        desc = ARCHETYPE_DESCRIPTIONS.get(arch, f"{arch} section")
        rows.append({
            "archetype": arch,
            "variant": var,
            "description": f"{desc} — {var} variant",
            "has_template": False,
            "template_path": None,
        })

    count = supabase_post("section_archetypes", rows)
    print(f"  ✓ Inserted {count} rows into section_archetypes")


# ─── STEP 4: Seed industry_styles (parse .md preset files) ────────

def parse_yaml_style_block(content: str) -> dict | None:
    """Extract YAML style configuration from preset .md file."""
    # Find the ## Style Configuration section
    match = re.search(r"## Style Configuration\s*\n\s*```yaml\s*\n(.*?)```", content, re.DOTALL)
    if not match:
        return None

    yaml_text = match.group(1)

    # Parse YAML manually (simple key:value and nested blocks)
    config = {}
    current_section = None

    for line in yaml_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check if it's a nested key with sub-items
        indent = len(line) - len(line.lstrip())

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            # Remove inline comments
            if "#" in value:
                value = value[:value.index("#")].strip()

            if indent == 0:
                if value:
                    config[key] = value
                else:
                    current_section = key
                    config[key] = {}
            elif current_section and indent > 0:
                if value:
                    config[current_section][key] = value
                else:
                    config[current_section][key] = {}

    return config if config else None


def parse_compact_style_header(content: str) -> str | None:
    """Extract the compact style header block."""
    match = re.search(r"(═══ STYLE CONTEXT ═══.*?═══════════════════════)", content, re.DOTALL)
    return match.group(1) if match else None


def parse_content_direction(content: str) -> dict | None:
    """Extract the Content Direction section."""
    match = re.search(r"## Content Direction\s*\n(.*?)(?=\n## |\n---|\Z)", content, re.DOTALL)
    if not match:
        return None
    text = match.group(1).strip()
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("**") and ":**" in line:
            key = line.split(":**")[0].replace("**", "").strip().lower().replace(" ", "_")
            val = line.split(":**")[1].strip()
            result[key] = val
    return result if result else None


def parse_photography(content: str) -> list | None:
    """Extract photography/visual direction."""
    match = re.search(r"## Photography.*?\n(.*?)(?=\n## |\n---|\Z)", content, re.DOTALL)
    if not match:
        return None
    items = []
    for line in match.group(1).strip().splitlines():
        line = line.strip().lstrip("- ")
        if line:
            items.append(line)
    return items if items else None


def parse_pitfalls(content: str) -> list | None:
    """Extract known pitfalls."""
    match = re.search(r"## Known Pitfalls\s*\n(.*?)(?=\n## |\n---|\Z)", content, re.DOTALL)
    if not match:
        return None
    items = []
    for line in match.group(1).strip().splitlines():
        line = line.strip().lstrip("- ")
        if line:
            items.append(line)
    return items if items else None


def seed_industry_styles():
    print("\n═══ Step 3.4: Seeding industry_styles ═══")
    presets_dir = ROOT / "skills" / "presets"

    # Generic industry presets only (exclude project-specific and template)
    GENERIC_PRESETS = {
        "artisan-food", "beauty-cosmetics", "construction-trades", "creative-studios",
        "education", "events-venues", "fashion-apparel", "health-wellness",
        "home-lifestyle", "hotels-hospitality", "jewelry-watches", "medical-dental",
        "nonprofits-social", "outdoor-adventure", "pet-products", "professional-services",
        "real-estate", "restaurants-cafes", "saas", "sports-fitness",
    }

    ALL_INDUSTRIES = set(INDUSTRY_META.keys())
    rows_with_style = []
    rows_without_style = []

    for ind in sorted(ALL_INDUSTRIES):
        md_name = ind  # saas.md, not saas-software.md
        md_path = presets_dir / f"{md_name}.md"

        if md_name in GENERIC_PRESETS and md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            style_config = parse_yaml_style_block(content)
            compact_header = parse_compact_style_header(content)
            content_dir = parse_content_direction(content)
            photo_dir = parse_photography(content)
            pitfalls = parse_pitfalls(content)

            row = {
                "industry": ind,
                "style_config": style_config,
                "compact_style_header": compact_header,
                "content_direction": content_dir,
                "photography_direction": photo_dir,
                "known_pitfalls": pitfalls,
            }
            rows_with_style.append(row)
            print(f"  ✓ Parsed style config for {ind} ({len(json.dumps(style_config or {}))} bytes)")
        else:
            rows_without_style.append({
                "industry": ind,
                "style_config": None,
                "compact_style_header": None,
                "content_direction": None,
                "photography_direction": None,
                "known_pitfalls": None,
            })
            print(f"  ⚠ No preset .md for {ind} — inserting with NULL style_config")

    all_rows = rows_with_style + rows_without_style
    count = supabase_post("industry_styles", all_rows)
    print(f"  ✓ Inserted {count} rows into industry_styles ({len(rows_with_style)} with style, {len(rows_without_style)} without)")

    if rows_without_style:
        print(f"\n  Missing style configs for: {', '.join(r['industry'] for r in rows_without_style)}")


# ─── STEP 5: Validation ───────────────────────────────────────────

def validate():
    print("\n═══ Step 3.5: Validation ═══")

    # Count section_presets
    presets = supabase_get("section_presets", "select=id&limit=1000")
    # Need to count all rows
    all_presets = supabase_get("section_presets", "select=id")
    print(f"  section_presets: {len(all_presets)} rows (expected 842)")

    # Count industries
    industries = supabase_get("industries", "select=handle")
    print(f"  industries: {len(industries)} rows (expected 25)")

    # Count archetypes
    archetypes = supabase_get("section_archetypes", "select=archetype,variant")
    print(f"  section_archetypes: {len(archetypes)} rows (expected 72)")

    # Count styles
    styles = supabase_get("industry_styles", "select=industry,style_config")
    styles_with_config = [s for s in styles if s.get("style_config")]
    print(f"  industry_styles: {len(styles)} rows ({len(styles_with_config)} with style_config)")

    # Test get_page_sections function
    print("\n  Testing get_page_sections('artisan-food', 'homepage')...")
    try:
        result = supabase_rpc("get_page_sections", {
            "p_industry": "artisan-food",
            "p_page_type": "homepage",
        })
        print(f"  ✓ Returned {len(result)} sections")
        for r in result[:3]:
            print(f"    {r.get('out_position', '?')}. {r.get('out_section_archetype', '?')} | {r.get('out_section_variant', '?')}")
        if len(result) > 3:
            print(f"    ... and {len(result) - 3} more")
    except Exception as e:
        print(f"  ✗ Function call failed: {e}")

    # Check all industries in presets have matching industries row
    distinct_preset_ind = supabase_get("section_presets", "select=industry&limit=1000")
    ind_set = set(r["industry"] for r in distinct_preset_ind)
    ind_table = set(r["handle"] for r in industries)
    missing_in_industries = ind_set - ind_table
    if missing_in_industries:
        print(f"  ⚠ Industries in presets but not in industries table: {missing_in_industries}")
    else:
        print(f"  ✓ All {len(ind_set)} preset industries have matching industries rows")

    # Check industry_styles coverage
    style_industries = set(r["industry"] for r in styles)
    missing_styles = ind_set - style_industries
    if missing_styles:
        print(f"  ⚠ Industries missing from industry_styles: {missing_styles}")
    else:
        print(f"  ✓ All preset industries have industry_styles rows")

    print("\n═══ Seeding complete ═══\n")


# ─── MAIN ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("═══════════════════════════════════════════")
    print("  Aurelix Supabase Seed Script")
    print(f"  Target: {SUPABASE_URL}")
    print("═══════════════════════════════════════════")

    preset_rows = seed_section_presets()
    if preset_rows:
        seed_industries(preset_rows)
        seed_section_archetypes(preset_rows)
    seed_industry_styles()
    validate()
