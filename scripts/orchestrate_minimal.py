#!/usr/bin/env python3
"""Aurelix Web Builder — orchestrate.py"""
import argparse, json, os, sys, re, shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("anthropic package required: pip install anthropic")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"
ROOT = Path(__file__).parent.parent
BRIEFS_DIR = ROOT / "briefs"
OUTPUT_DIR = ROOT / "output"
PRESETS_DIR = ROOT / "presets"
for d in [BRIEFS_DIR, OUTPUT_DIR, PRESETS_DIR]:
    d.mkdir(exist_ok=True)

PRESET_CONFIGS = {
    "sporting-goods": {
        "style": "bold, energetic, performance-driven",
        "colors": "dark neutrals with high-contrast green accent",
        "typography": "strong sans-serif headers, clean body text",
        "sections": ["HERO", "PRODUCT-SHOWCASE", "FEATURES", "TESTIMONIALS", "CTA", "FAQ"],
        "tone": "authoritative, community-oriented, technically credible",
    },
    "health-wellness": {
        "style": "calm, clean, trustworthy",
        "colors": "soft greens, warm whites, sage",
        "typography": "rounded sans-serif, generous line height",
        "sections": ["HERO", "FEATURES", "PRODUCT-SHOWCASE", "TESTIMONIALS", "FAQ", "CTA"],
        "tone": "expert but approachable, evidence-based",
    },
    "ecommerce": {
        "style": "conversion-focused, clear hierarchy",
        "colors": "neutral base, strong CTA contrast",
        "typography": "legible at all sizes",
        "sections": ["HERO", "PRODUCT-SHOWCASE", "FEATURES", "TESTIMONIALS", "CTA"],
        "tone": "direct, benefit-led",
    },
}
DEFAULT_PRESET = {
    "style": "clean, professional, modern",
    "colors": "neutral palette with brand accent",
    "typography": "clean sans-serif",
    "sections": ["HERO", "FEATURES", "PRODUCT-SHOWCASE", "TESTIMONIALS", "CTA"],
    "tone": "clear and professional",
}

def get_preset(name):
    if name in PRESET_CONFIGS:
        return PRESET_CONFIGS[name]
    f = PRESETS_DIR / f"{name}.json"
    if f.exists():
        return json.loads(f.read_text())
    print(f"[web-builder] WARNING: preset '{name}' not found, using default")
    return DEFAULT_PRESET

def load_brief(project, brief_path):
    if brief_path and Path(brief_path).exists():
        return Path(brief_path).read_text()
    default = BRIEFS_DIR / f"{project}.md"
    if default.exists():
        return default.read_text()
    return f"# Brief: {project}\n## Business\n{project}\n"

SECTION_PROMPT = """You are an expert Next.js/React developer.

Project: {project}
Section to build: {section_type}
Preset: {preset_name}
Style: {style}
Colors: {colors}
Tone: {tone}

Brief:
{brief}

Generate a complete production-quality Next.js TSX component for the {section_type} section.
- Use Tailwind CSS (no external CSS)
- Component name: {component_name}
- Export as default
- Include realistic placeholder content matching the brand
- Mobile-first responsive design
- TypeScript with proper types, no implicit any
- All interfaces defined inline in the file

Return ONLY the TSX code, no explanation, no markdown fences."""

def generate_section(project, section_type, preset_name, preset, brief, client):
    component_name = re.sub(r"[^a-zA-Z0-9]", "", section_type.replace("-", " ").title().replace(" ", "")) + "Section"
    prompt = SECTION_PROMPT.format(
        project=project, section_type=section_type, preset_name=preset_name,
        style=preset.get("style", "modern"), colors=preset.get("colors", "neutral"),
        tone=preset.get("tone", "professional"), brief=brief[:2000],
        component_name=component_name,
    )
    response = client.messages.create(model=MODEL, max_tokens=3000,
        messages=[{"role": "user", "content": prompt}])
    code = response.content[0].text.strip()
    code = re.sub(r"^```(?:tsx|typescript|ts|jsx)?\n?", "", code)
    code = re.sub(r"\n?```$", "", code)
    return code.strip(), component_name

def build(project, preset_name, brief_path=None, deploy=False, output_dir=None):
    if not ANTHROPIC_API_KEY:
        sys.exit("[web-builder] ERROR: ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    preset = get_preset(preset_name)
    brief = load_brief(project, brief_path)
    sections = preset.get("sections", DEFAULT_PRESET["sections"])
    project_out = (output_dir or OUTPUT_DIR) / project
    sections_out = project_out / "sections"
    site_out = project_out / "site"
    components_out = site_out / "src" / "components" / project
    if project_out.exists():
        shutil.rmtree(project_out)
    for d in [sections_out, components_out, site_out / "src" / "app"]:
        d.mkdir(parents=True, exist_ok=True)
    print(f"[web-builder] Building {project} | preset={preset_name}")
    print(f"[web-builder] Sections: {', '.join(sections)}", flush=True)
    generated = []
    for section in sections:
        print(f"[web-builder]   Generating {section}...", flush=True)
        try:
            code, component_name = generate_section(project, section, preset_name, preset, brief, client)
            (components_out / f"{component_name}.tsx").write_text(code)
            (sections_out / f"{section}.tsx").write_text(code)
            generated.append({"section": section, "component": component_name, "status": "generated"})
            print(f"[web-builder]   OK: {component_name}", flush=True)
        except Exception as e:
            print(f"[web-builder]   ERROR: {section}: {e}", flush=True)
            generated.append({"section": section, "status": "error", "error": str(e)})
    component_names = [g["component"] for g in generated if g.get("status") == "generated"]
    imports_str = "\n".join(f'import {n} from "@/components/{project}/{n}";' for n in component_names)
    renders_str = "\n".join(f"      <{n} />" for n in component_names)
    title_match = re.search(r"# Brief: (.+)", brief)
    title = title_match.group(1).strip() if title_match else project.replace("-", " ").title()
    page = f'import type {{ Metadata }} from "next";\n{imports_str}\n\nexport const metadata: Metadata = {{\n  title: "{title}",\n  description: "{title} — built with Aurelix",\n}};\n\nexport default function HomePage() {{\n  return (\n    <main>\n{renders_str}\n    </main>\n  );\n}}\n'
    (site_out / "src" / "app" / "page.tsx").write_text(page)
    manifest = {"project": project, "preset": preset_name,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sections": generated, "output": {"site": str(site_out), "sections": str(sections_out)}}
    (project_out / "site-manifest.json").write_text(json.dumps(manifest, indent=2))
    ok = sum(1 for s in generated if s.get("status") == "generated")
    print(f"[web-builder] Done: {ok}/{len(sections)} sections | output: {project_out}", flush=True)
    if deploy:
        print(f"[web-builder] Deploy: cd {site_out} && vercel --prod --yes", flush=True)
    return manifest

def main():
    parser = argparse.ArgumentParser(description="Aurelix Web Builder")
    parser.add_argument("project")
    parser.add_argument("--preset", default="ecommerce")
    parser.add_argument("--brief", default=None)
    parser.add_argument("--compiled-dir", default=None)
    parser.add_argument("--from-url", default=None)
    parser.add_argument("--deploy", action="store_true")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-to", default=None)
    parser.add_argument("--set-vercel-env", action="store_true")
    parser.add_argument("--no-pause", action="store_true", help="Skip scaffold review checkpoint (no-op in this runner)")
    args = parser.parse_args()
    out_dir = Path(args.output_dir) if args.output_dir else None
    manifest = build(project=args.project, preset_name=args.preset,
                     brief_path=args.brief, deploy=args.deploy, output_dir=out_dir)
    print(json.dumps({"status": "success", "built": args.project}, indent=2), flush=True)

if __name__ == "__main__":
    main()
