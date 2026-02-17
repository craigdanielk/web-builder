#!/usr/bin/env python3
"""
Aurelix Database Integration — Validation Suite
Tests the Supabase integration without consuming API tokens.
"""

import json
import os
import re
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).parent.parent

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


PASS = 0
FAIL = 0
WARN = 0


def test(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")
        if detail:
            print(f"    → {detail}")


def warn(name: str, detail: str = ""):
    global WARN
    WARN += 1
    print(f"  ⚠ {name}")
    if detail:
        print(f"    → {detail}")


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 1: Supabase Client Module ═══\n")

try:
    from lib.supabase_client import (
        BuildCache, check_template_exists, log_build,
        is_supabase_configured, get_section_sequence, get_industry_style,
    )
    test("Import supabase_client", True)
except Exception as e:
    test("Import supabase_client", False, str(e))
    sys.exit(1)

test("Supabase configured", is_supabase_configured())


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 2: Database Queries ═══\n")

# Test get_section_sequence for all 25 industries
industries_with_homepage = [
    "artisan-food", "automotive", "beauty-cosmetics", "construction-trades",
    "creative-studios", "education", "electronics-tech", "events-venues",
    "fashion-apparel", "health-wellness", "home-lifestyle", "hotels-hospitality",
    "jewelry-watches", "kids-baby", "luxury-premium", "medical-dental",
    "nonprofits-social", "outdoor-adventure", "pet-products", "professional-services",
    "real-estate", "restaurants-cafes", "saas", "sports-fitness", "sustainable-eco",
]

for ind in industries_with_homepage:
    try:
        seq = get_section_sequence(ind, "homepage")
        test(f"get_section_sequence('{ind}', 'homepage')", len(seq) > 0,
             f"Got {len(seq)} sections" if seq else "Empty result")
    except Exception as e:
        test(f"get_section_sequence('{ind}', 'homepage')", False, str(e))

# Test get_industry_style
print()
for ind in ["artisan-food", "saas", "automotive", "fashion-apparel"]:
    try:
        style = get_industry_style(ind)
        has_config = style and style.get("style_config") is not None
        if ind == "automotive":
            test(f"get_industry_style('{ind}') — NULL expected", style is not None and style.get("style_config") is None,
                 f"Got: {json.dumps(style.get('style_config'))[:50]}" if style else "None")
        else:
            test(f"get_industry_style('{ind}')", has_config,
                 f"Style config present" if has_config else "No style_config")
    except Exception as e:
        test(f"get_industry_style('{ind}')", False, str(e))


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 3: BuildCache ═══\n")

cache = BuildCache("artisan-food", "homepage")
cache.load()

test("BuildCache loads section_sequence", len(cache.section_sequence) > 0)
test("BuildCache loads industry_style", cache.industry_style is not None)
test("BuildCache has style_config", bool(cache.style_config))
test("BuildCache has compact_style_header", len(cache.compact_style_header) > 10)

# Test preset sequence text matches expected format
seq_text = cache.get_preset_sequence_text()
test("Preset sequence text has numbered lines",
     bool(re.match(r"1\. [A-Z]+", seq_text)),
     f"First line: {seq_text.split(chr(10))[0]}")

# Test synthetic preset content
synthetic = cache.build_synthetic_preset_content()
test("Synthetic preset has Style Configuration", "## Style Configuration" in synthetic)
test("Synthetic preset has section sequence", "## Default Section Sequence" in synthetic)

# Test that existing functions work on synthetic content
def detect_animation_engine(c):
    m = re.search(r"Motion:.*?/(gsap|framer-motion)", c)
    return m.group(1) if m else "framer-motion"

def parse_fonts(c):
    heading = "Inter"
    body = "Inter"
    h = re.search(r"heading_font:\s*([A-Za-z][A-Za-z0-9_ ]+)", c)
    if h: heading = h.group(1).strip()
    b = re.search(r"body_font:\s*([A-Za-z][A-Za-z0-9_ ]+)", c)
    if b: body = b.group(1).strip()
    return {"heading": heading, "body": body}

fonts = parse_fonts(synthetic)
test("parse_fonts works on synthetic content", fonts["heading"] != "Inter" or fonts["body"] != "Inter",
     f"Heading: {fonts['heading']}, Body: {fonts['body']}")


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 4: Template System ═══\n")

# Test check_template_exists (returns Path | str | None; optional cache)
hero_tpl = check_template_exists("HERO", "full-bleed-overlay")
test("HERO/full-bleed-overlay template exists", hero_tpl is not None)
# Path = local file, str = Supabase code_template
if hero_tpl is not None:
    if isinstance(hero_tpl, Path):
        test("Template file is readable", hero_tpl.exists())
        test("Template file has content", hero_tpl.stat().st_size > 100)
    else:
        test("Template content is non-empty string", isinstance(hero_tpl, str) and len(hero_tpl) > 100)

# Non-existent archetype/variant: both local and DB return None
no_tpl = check_template_exists("NONEXISTENT", "fake-variant")
test("NONEXISTENT/fake-variant template does NOT exist (expected)", no_tpl is None)

# Template content (Path or str) has brand token placeholders
if hero_tpl is not None:
    content = hero_tpl.read_text() if isinstance(hero_tpl, Path) else hero_tpl
    test("Template has brand.accent placeholder", "{{brand.accent}}" in content)
    test("Template has brand.heading_font placeholder", "{{brand.heading_font}}" in content)


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 5: Orchestrator Integration ═══\n")

# Verify orchestrate.py imports work
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("orchestrate", ROOT / "scripts" / "orchestrate.py")
    # Don't actually import (it has side effects), just check syntax
    import py_compile
    py_compile.compile(str(ROOT / "scripts" / "orchestrate.py"), doraise=True)
    test("orchestrate.py compiles without errors", True)
except Exception as e:
    test("orchestrate.py compiles without errors", False, str(e))

# Check that --industry and --page args exist in the file
orch_content = (ROOT / "scripts" / "orchestrate.py").read_text()
test("--industry argument defined", '--industry' in orch_content)
test("--page argument defined", '--page' in orch_content)
test("BuildCache import in orchestrate.py", "from lib.supabase_client import BuildCache" in orch_content)
test("build_cache parameter in stage_scaffold", "build_cache" in orch_content.split("def stage_scaffold")[1][:500])
test("build_cache parameter in stage_sections", "build_cache" in orch_content.split("def stage_sections")[1][:500])
test("build_cache parameter in stage_deploy", "build_cache" in orch_content.split("def stage_deploy")[1][:500])
test("build_cache parameter in stage_review", "build_cache" in orch_content.split("def stage_review(")[1][:500])
test("Template-first check in section loop", "check_template_exists" in orch_content)
test("Build logging at end of pipeline", "log_build(" in orch_content)


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 6: Legacy Path Preserved ═══\n")

# Ensure the legacy --preset path is still intact
test("Legacy preset loading preserved in stage_scaffold",
     'read_file(SKILLS_DIR / "presets" / f"{preset}.md")' in orch_content.split("def stage_scaffold")[1][:2000])
test("Legacy preset loading preserved in stage_sections",
     'read_file(SKILLS_DIR / "presets" / f"{preset}.md")' in orch_content.split("def stage_sections")[1][:2000])
test("Legacy preset loading preserved in stage_deploy",
     'read_file(SKILLS_DIR / "presets" / f"{preset}.md")' in orch_content.split("def stage_deploy")[1][:2000])
test("Legacy preset loading preserved in stage_review",
     'read_file(SKILLS_DIR / "presets" / f"{preset}.md")' in orch_content.split("def stage_review(")[1][:2000])

# Ensure .md preset files still exist
preset_dir = ROOT / "skills" / "presets"
preset_files = list(preset_dir.glob("*.md"))
non_template = [f for f in preset_files if f.stem != "_template"]
test(f"Preset .md files still exist ({len(non_template)} found)", len(non_template) >= 20)


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 7: Build Log Write ═══\n")

try:
    result = log_build(
        project_name="__test_validation__",
        industry="artisan-food",
        page_type="homepage",
        sections_from_template=1,
        db_template_count=0,
        sections_from_llm=6,
        total_sections=7,
        build_duration_ms=12345,
        status="completed",
    )
    test("log_build writes successfully", result)
except Exception as e:
    test("log_build writes successfully", False, str(e))


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 8: Directory Structure ═══\n")

template_base = ROOT / "section-templates"
test("section-templates/ directory exists", template_base.is_dir())
test("manifest.json exists", (template_base / "manifest.json").is_file())

manifest = json.loads((template_base / "manifest.json").read_text())
test("manifest has 25 archetypes", len(manifest.get("archetypes", {})) == 25)
test("manifest has 72 total variants", manifest.get("total_variants") == 72)
test("manifest shows templates available (local + db)", manifest.get("templates_available", 0) >= 1)

# Check archetype directories
for arch in manifest.get("archetypes", {}).keys():
    arch_dir = template_base / arch
    if not arch_dir.is_dir():
        test(f"Directory {arch}/ exists", False)
        break
else:
    test("All 25 archetype directories exist", True)


# ═══════════════════════════════════════════════════════════════════
print("\n═══ Test Suite 9: Supabase Schema ═══\n")

# Check migrations exist
migrations_dir = ROOT / "supabase" / "migrations"
migration_files = sorted(migrations_dir.glob("*.sql"))
test("Migration files exist", len(migration_files) >= 2,
     f"Found {len(migration_files)} migration files")
for mf in migration_files:
    test(f"  Migration: {mf.name}", True)


# ═══════════════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {WARN} warnings")
print(f"{'═' * 60}\n")

if FAIL > 0:
    sys.exit(1)
