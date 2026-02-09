#!/usr/bin/env python3
"""
Website Builder Orchestration Pipeline

Automates the multi-pass generation workflow:
  1. Read brief + match preset
  2. Generate scaffold (page specification)
  3. Generate each section individually with style header
  4. Assemble into complete page
  5. Run consistency review

URL Clone Mode (--from-url):
  0. Extract visual data from URL → auto-generate preset + brief
  1-5. Normal pipeline with per-section reference context

Usage:
  python scripts/orchestrate.py <project-name> [--preset <preset-name>] [--no-pause]
  python scripts/orchestrate.py <project-name> --from-url <url> [--no-pause]

Requirements:
  pip install anthropic --break-system-packages
  (URL mode also requires: cd scripts/quality && npm install && npx playwright install chromium)
"""

import os
import sys
import json
import argparse
import re
import subprocess
import uuid
from pathlib import Path
from datetime import datetime

try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not installed.")
    print("Run: pip install anthropic --break-system-packages")
    sys.exit(1)


# --- Configuration ---

ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "skills"
TEMPLATES_DIR = ROOT / "templates"
BRIEFS_DIR = ROOT / "briefs"
OUTPUT_DIR = ROOT / "output"

def load_env_file():
    """Load simple KEY=VALUE pairs from .env into os.environ if not already set."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

load_env_file()

# Model selection per pipeline stage
MODELS = {
    "scaffold": "claude-sonnet-4-5-20250929",    # Good judgment for structure
    "section": "claude-sonnet-4-5-20250929",      # Fast, good for individual components
    "review": "claude-sonnet-4-5-20250929",       # Good judgment for quality eval
}

MAX_TOKENS = {
    "scaffold": 2048,
    "section": 4096,
    "review": 4096,
}


# --- File Helpers ---

def read_file(path: Path) -> str:
    """Read a file and return its contents."""
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str):
    """Write content to a file, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  → Saved: {path.relative_to(ROOT)}")


def list_presets() -> list[str]:
    """List available preset names."""
    preset_dir = SKILLS_DIR / "presets"
    return [
        f.stem for f in preset_dir.glob("*.md")
        if f.stem != "_template"
    ]


# --- Claude API ---

def call_claude(prompt: str, stage: str) -> str:
    """Call the Anthropic API and return the response text."""
    client = Anthropic()

    message = client.messages.create(
        model=MODELS[stage],
        max_tokens=MAX_TOKENS[stage],
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract text from response
    text_parts = [
        block.text for block in message.content if block.type == "text"
    ]
    return "\n".join(text_parts)


QUALITY_DIR = ROOT / "scripts" / "quality"
SITE_DIR_NAME = "site"  # Rendered Next.js project lives at output/{project}/site/


# --- URL Extraction Stage ---

def stage_url_extract(url: str, project_name: str) -> tuple[str, str, dict]:
    """
    Stage 0: Extract from URL and generate preset + brief.
    Returns (preset_name, brief_content, section_contexts).
    """
    print("\n🌐 Stage 0: Extracting from URL...")
    print(f"  URL: {url}")

    node = "node"  # Assumes node is on PATH

    # Generate unique extraction ID to prevent race conditions in parallel builds
    extraction_id = f"{project_name}-{uuid.uuid4().hex[:8]}"
    extraction_dir = OUTPUT_DIR / "extractions" / extraction_id

    # Step 0a: Run url-to-preset.js → generates preset and extraction data
    print("\n  [0a] Generating preset from URL...")
    preset_name = project_name
    preset_script = QUALITY_DIR / "url-to-preset.js"
    result = subprocess.run(
        [node, str(preset_script), url, preset_name,
         "--extraction-dir", str(extraction_dir)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=300,
    )
    if result.returncode != 0:
        print(f"  Error in url-to-preset.js:")
        print(result.stderr[-1000:] if result.stderr else "(no stderr)")
        sys.exit(1)
    print(result.stdout)

    # Verify preset was created
    preset_path = SKILLS_DIR / "presets" / f"{preset_name}.md"
    if not preset_path.exists():
        print(f"  Error: Preset not generated at {preset_path}")
        sys.exit(1)
    print(f"  ✓ Preset saved: {preset_path.relative_to(ROOT)}")

    # Step 0b: Run url-to-brief.js → generates brief (reuses extraction data)
    print("\n  [0b] Generating brief from URL...")
    brief_script = QUALITY_DIR / "url-to-brief.js"
    result = subprocess.run(
        [node, str(brief_script), url, project_name,
         "--extraction-dir", str(extraction_dir)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  Error in url-to-brief.js:")
        print(result.stderr[-1000:] if result.stderr else "(no stderr)")
        sys.exit(1)
    print(result.stdout)

    # Load the generated brief
    brief_path = BRIEFS_DIR / f"{project_name}.md"
    if not brief_path.exists():
        print(f"  Error: Brief not generated at {brief_path}")
        sys.exit(1)
    brief_content = read_file(brief_path)
    print(f"  ✓ Brief saved: {brief_path.relative_to(ROOT)}")

    # Step 0c: Load section contexts for per-section injection
    print("\n  [0c] Loading section context data...")
    section_contexts = {}
    extraction_data_path = extraction_dir / "extraction-data.json"
    mapped_sections_path = extraction_dir / "mapped-sections.json"

    if extraction_data_path.exists() and mapped_sections_path.exists():
        # Generate section contexts using the Node.js module
        context_script = f"""
const {{ buildAllSectionContexts }} = require('./lib/section-context');
const extractionData = require('{extraction_data_path}');
const mappedSections = require('{mapped_sections_path}');
const contexts = buildAllSectionContexts(extractionData, mappedSections);
console.log(JSON.stringify(contexts));
"""
        result = subprocess.run(
            [node, "-e", context_script],
            capture_output=True,
            text=True,
            cwd=str(QUALITY_DIR),
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                section_contexts = json.loads(result.stdout.strip())
                print(f"  ✓ Loaded context for {len(section_contexts)} sections")
            except json.JSONDecodeError:
                print("  ⚠ Could not parse section contexts, continuing without them")
        else:
            print("  ⚠ Could not generate section contexts, continuing without them")
    else:
        print("  ⚠ Extraction data not found, continuing without section contexts")

    return preset_name, brief_content, section_contexts


# --- Pipeline Stages ---

def stage_scaffold(brief: str, preset: str, project_name: str, no_pause: bool) -> str:
    """Stage 1: Generate the page scaffold."""
    print("\n📋 Stage 1: Generating scaffold...")

    # Load resources
    scaffold_template = read_file(TEMPLATES_DIR / "scaffold-prompt.md")
    taxonomy = read_file(SKILLS_DIR / "section-taxonomy.md")
    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")

    # Extract section sequence from preset
    # (Look for the Default Section Sequence block)
    sequence_match = re.search(
        r"## Default Section Sequence\n\n```\n(.*?)```",
        preset_content,
        re.DOTALL,
    )
    preset_sequence = sequence_match.group(1).strip() if sequence_match else "See preset file"

    # Extract just archetype names and variants from taxonomy (keep it concise)
    archetype_lines = []
    current_archetype = None
    for line in taxonomy.split("\n"):
        if line.startswith("### "):
            current_archetype = line.replace("### ", "").strip()
            archetype_lines.append(f"\n{current_archetype}")
        elif line.startswith("- `") and current_archetype:
            variant = line.strip().split("`")[1] if "`" in line else line.strip("- ")
            archetype_lines.append(f"  - {variant}")

    archetype_list = "\n".join(archetype_lines)

    # Build the prompt
    prompt = f"""You are a senior web designer creating a page specification for a new website.

## Client Brief
{brief}

## Industry Preset — Default Section Sequence
{preset_sequence}

## Available Section Archetypes
{archetype_list}

## Instructions

Based on the client brief, generate a page specification. Use the industry
preset's section sequence as your starting point, then adapt it:

1. ADD sections if the brief mentions needs not covered by the default sequence
2. REMOVE sections that aren't relevant to this specific client
3. REORDER if the client's priorities suggest a different flow
4. SELECT the best variant for each section based on the brief's specifics

Output format — a numbered section list:

Page: {project_name}
Preset: {preset}

1. ARCHETYPE | variant | content direction for this section
2. ARCHETYPE | variant | content direction for this section
...

For each section's content direction, write 1-2 sentences describing what
specific content goes here — specific to THIS client, not generic.

Do NOT generate any code. This is a specification only.
Keep total sections between 6 and 14."""

    scaffold = call_claude(prompt, "scaffold")

    # Save
    output_path = OUTPUT_DIR / project_name / "scaffold.md"
    write_file(output_path, scaffold)

    print(f"\n{scaffold}\n")

    # Checkpoint
    if not no_pause:
        print("─" * 60)
        response = input("Review the scaffold above. Continue? [Y/n/edit]: ").strip().lower()
        if response == "n":
            print("Aborted. Edit the scaffold manually and rerun with --no-pause.")
            sys.exit(0)
        elif response == "edit":
            print(f"Edit the scaffold at: {output_path}")
            input("Press Enter when done editing...")
            scaffold = read_file(output_path)

    return scaffold


def parse_scaffold(scaffold: str) -> list[dict]:
    """Parse the scaffold into a list of section specifications."""
    sections = []
    for line in scaffold.split("\n"):
        # Match lines like: 1. HERO | full-bleed-overlay | content direction text
        match = re.match(
            r"\d+\.\s+(\w[\w-]*)\s*\|\s*(\S[\w-]*)\s*\|\s*(.+)",
            line.strip(),
        )
        if match:
            sections.append({
                "archetype": match.group(1).strip(),
                "variant": match.group(2).strip(),
                "content": match.group(3).strip(),
            })
    return sections


def extract_style_header(preset_content: str) -> str:
    """Extract the compact style header from a preset file."""
    match = re.search(
        r"(═══ STYLE CONTEXT ═══.*?═══════════════════════)",
        preset_content,
        re.DOTALL,
    )
    if match:
        return match.group(1)
    return "[Style header not found in preset — check preset format]"


def stage_sections(
    sections: list[dict],
    preset: str,
    project_name: str,
    section_contexts: dict | None = None,
) -> list[Path]:
    """Stage 2: Generate each section component individually."""
    print(f"\n🔨 Stage 2: Generating {len(sections)} sections...")
    if section_contexts:
        print(f"  (with per-section reference context from URL extraction)")

    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
    style_header = extract_style_header(preset_content)
    taxonomy = read_file(SKILLS_DIR / "section-taxonomy.md")

    section_template = read_file(TEMPLATES_DIR / "section-prompt.md")
    section_files = []

    for i, section in enumerate(sections):
        num = f"{i + 1:02d}"
        name = section["archetype"].lower().replace("-", "_")
        filename = f"{num}-{name}.tsx"

        print(f"  [{num}/{len(sections):02d}] {section['archetype']} | {section['variant']}...")

        # Try to find structural reference in taxonomy
        structure_ref = "[No structural reference yet — infer from archetype and variant]"
        # Look for the archetype's Structure field
        arch_pattern = rf"### {re.escape(section['archetype'])}.*?(?=### |\Z)"
        arch_match = re.search(arch_pattern, taxonomy, re.DOTALL)
        if arch_match:
            struct_match = re.search(
                r"\*\*Structure:\*\*\s*(.+?)(?:\n\*\*|\Z)",
                arch_match.group(0),
                re.DOTALL,
            )
            if struct_match and "populate on first use" not in struct_match.group(1).lower():
                structure_ref = struct_match.group(1).strip()

        # Build optional reference context block
        ref_context_block = ""
        if section_contexts and str(i) in section_contexts:
            ref_context_block = f"\n{section_contexts[str(i)]}\n"

        prompt = f"""You are a senior frontend developer generating a single website section
as a React + Tailwind CSS + Framer Motion component.

{style_header}

## Section Specification
Number: {i + 1} of {len(sections)}
Archetype: {section['archetype']}
Variant: {section['variant']}
Content Direction: {section['content']}

## Structural Reference
{structure_ref}
{ref_context_block}
## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above. Do not introduce any values not specified.
3. The component must be self-contained — no external dependencies beyond:
   - React
   - Framer Motion (import {{ motion }} from "framer-motion")
   - Tailwind CSS classes
4. Use semantic HTML elements (section, nav, article, etc.)
5. Include responsive design: mobile-first, with sm/md/lg breakpoints
6. Placeholder images should use a neutral gradient div with descriptive aria-label
7. All text content should be realistic for the client — not lorem ipsum
8. Animation should match the intensity from the style header:
   - Use Framer Motion motion components with whileInView for scroll triggers
   - Apply the entrance, hover, and timing values specified

Output ONLY the component code. No explanation, no markdown code fences.
Export the component as default.
Component name: Section{num}{section['archetype'].replace('-', '')}"""

        code = call_claude(prompt, "section")

        # Clean up any markdown code fences that might have snuck in
        code = re.sub(r"^```\w*\n?", "", code)
        code = re.sub(r"\n?```$", "", code)

        # Post-process: ensure "use client" directive for components using
        # framer-motion or React hooks (adapted from aurelix-mvp generate.js)
        client_markers = [
            "framer-motion", "motion.", "useState", "useEffect",
            "useRef", "useCallback", "useMemo",
        ]
        needs_client = any(marker in code for marker in client_markers)
        has_client = code.startswith('"use client"') or code.startswith("'use client'")
        if needs_client and not has_client:
            code = '"use client";\n\n' + code

        # Ensure default export exists
        if "export default" not in code:
            component_name = f"Section{num}{section['archetype'].replace('-', '')}"
            named_fn_pat = rf"export\s+function\s+{re.escape(component_name)}\b"
            if re.search(named_fn_pat, code):
                code = re.sub(named_fn_pat, f"export default function {component_name}", code)
            else:
                code += f"\n\nexport default {component_name};\n"

        filepath = OUTPUT_DIR / project_name / "sections" / filename
        write_file(filepath, code)
        section_files.append(filepath)

    return section_files


def stage_assemble(sections: list[dict], section_files: list[Path], project_name: str):
    """Stage 3: Assemble all sections into a single page component."""
    print("\n📦 Stage 3: Assembling page...")

    imports = []
    components = []

    for i, (section, filepath) in enumerate(zip(sections, section_files)):
        num = f"{i + 1:02d}"
        component_name = f"Section{num}{section['archetype'].replace('-', '')}"
        relative_path = f"./sections/{filepath.name.replace('.tsx', '')}"
        imports.append(f'import {component_name} from "{relative_path}";')
        components.append(f"      <{component_name} />")

    page_code = f'''import React from "react";
{chr(10).join(imports)}

export default function Page() {{
  return (
    <main className="min-h-screen">
{chr(10).join(components)}
    </main>
  );
}}
'''

    write_file(OUTPUT_DIR / project_name / "page.tsx", page_code)


def detect_animation_engine(preset_content: str) -> str:
    """Detect animation engine from preset's Motion line. Returns 'gsap' or 'framer-motion'."""
    match = re.search(r"Motion:.*?/(gsap|framer-motion)", preset_content)
    return match.group(1) if match else "framer-motion"


def parse_fonts(preset_content: str) -> dict:
    """Extract heading and body font names from preset's Type line."""
    match = re.search(r"heading:([^,]+),", preset_content)
    heading = match.group(1).strip() if match else "Inter"
    match = re.search(r"body:([^,]+),", preset_content)
    body = match.group(1).strip() if match else "Inter"
    return {"heading": heading, "body": body}


def font_import_name(font_name: str) -> str:
    """Convert a font display name to its next/font/google import name."""
    return font_name.replace(" ", "_")


def stage_deploy(
    sections: list[dict],
    section_files: list[Path],
    preset: str,
    project_name: str,
):
    """Stage 5: Deploy sections into a runnable Next.js project at output/{project}/site/."""
    print("\n🚀 Stage 5: Deploying to Next.js project...")

    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
    engine = detect_animation_engine(preset_content)
    fonts = parse_fonts(preset_content)
    style_header = extract_style_header(preset_content)

    site_dir = OUTPUT_DIR / project_name / SITE_DIR_NAME
    src_dir = site_dir / "src"
    app_dir = src_dir / "app"
    comp_dir = src_dir / "components" / "sections"

    # ── Scaffold Next.js project if it doesn't exist ──
    if not (site_dir / "package.json").exists():
        print("  Creating Next.js project structure...")

        # package.json
        deps = {
            "next": "16.1.6",
            "react": "19.2.3",
            "react-dom": "19.2.3",
        }
        if engine == "gsap":
            deps["gsap"] = "^3.14.2"
        else:
            deps["framer-motion"] = "^12.33.0"

        pkg = {
            "name": project_name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev --webpack",
                "build": "next build",
                "start": "next start",
                "lint": "eslint",
            },
            "dependencies": deps,
            "devDependencies": {
                "@tailwindcss/postcss": "^4",
                "@types/node": "^20",
                "@types/react": "^19",
                "@types/react-dom": "^19",
                "eslint": "^9",
                "eslint-config-next": "16.1.6",
                "tailwindcss": "^4",
                "typescript": "^5",
            },
        }
        write_file(site_dir / "package.json", json.dumps(pkg, indent=2) + "\n")

        # tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "ES2017",
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        }
        write_file(site_dir / "tsconfig.json", json.dumps(tsconfig, indent=2) + "\n")

        # next.config.ts
        write_file(
            site_dir / "next.config.ts",
            'import type { NextConfig } from "next";\n\n'
            "const nextConfig: NextConfig = {};\n\n"
            "export default nextConfig;\n",
        )

        # postcss.config.mjs
        write_file(
            site_dir / "postcss.config.mjs",
            "const config = {\n"
            '  plugins: {\n    "@tailwindcss/postcss": {},\n  },\n'
            "};\n\nexport default config;\n",
        )

        # eslint.config.mjs
        write_file(
            site_dir / "eslint.config.mjs",
            'import { dirname } from "path";\n'
            'import { fileURLToPath } from "url";\n'
            'import { FlatCompat } from "@eslint/eslintrc";\n\n'
            "const __filename = fileURLToPath(import.meta.url);\n"
            "const __dirname = dirname(__filename);\n\n"
            "const compat = new FlatCompat({ baseDirectory: __dirname });\n\n"
            'const eslintConfig = [...compat.extends("next/core-web-vitals")];\n\n'
            "export default eslintConfig;\n",
        )

        # .gitignore for the site
        write_file(
            site_dir / ".gitignore",
            "node_modules/\n.next/\n*.tsbuildinfo\nnext-env.d.ts\n",
        )

    # ── Generate globals.css ──
    print("  Generating globals.css...")
    css_lines = [
        '@import "tailwindcss";',
        "",
        ":root { --background: #fafaf9; --foreground: #1c1917; }",
        "body {",
        "  background: var(--background);",
        "  color: var(--foreground);",
        f'  font-family: "{fonts["body"]}", sans-serif;',
        "  -webkit-font-smoothing: antialiased;",
        "  -moz-osx-font-smoothing: grayscale;",
        "}",
    ]
    if engine == "gsap":
        css_lines += [
            "",
            "html { scroll-behavior: smooth; }",
            "",
            "::-webkit-scrollbar { width: 4px; }",
            "::-webkit-scrollbar-track { background: transparent; }",
            "::-webkit-scrollbar-thumb { background: #78716c; border-radius: 2px; }",
            "",
            "::selection { background: #78716c; color: #ffffff; }",
            "",
            "@keyframes marquee {",
            "  0% { transform: translateX(0); }",
            "  100% { transform: translateX(-50%); }",
            "}",
        ]
    write_file(app_dir / "globals.css", "\n".join(css_lines) + "\n")

    # ── Generate layout.tsx ──
    print("  Generating layout.tsx...")
    heading_import = font_import_name(fonts["heading"])
    body_import = font_import_name(fonts["body"])

    layout_imports = [
        'import type { Metadata } from "next";',
        f'import {{ {heading_import}, {body_import} }} from "next/font/google";',
        'import "./globals.css";',
    ]
    # Build font config lines
    heading_weights = '"400"'
    body_weights = '["400", "500", "700"]'
    # Try to extract weight from preset
    h_weight_match = re.search(r"heading:[^,]+,(\d+)", preset_content)
    if h_weight_match:
        heading_weights = f'"{h_weight_match.group(1)}"'

    layout_code = f"""{chr(10).join(layout_imports)}

const {heading_import.lower()} = {heading_import}({{ subsets: ["latin"], weight: {heading_weights} }});
const {body_import.lower()} = {body_import}({{ subsets: ["latin"], weight: {body_weights} }});

export const metadata: Metadata = {{
  title: "{project_name.replace('-', ' ').title()}",
  description: "Built with web-builder pipeline",
}};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en">
      <body className="antialiased">
        {{children}}
      </body>
    </html>
  );
}}
"""
    write_file(app_dir / "layout.tsx", layout_code)

    # ── Copy sections ──
    print("  Copying sections...")
    comp_dir.mkdir(parents=True, exist_ok=True)
    for filepath in section_files:
        code = read_file(filepath)
        write_file(comp_dir / filepath.name, code)

    # ── Generate page.tsx ──
    print("  Generating page.tsx...")
    imports = []
    components = []
    for i, (section, filepath) in enumerate(zip(sections, section_files)):
        num = f"{i + 1:02d}"
        component_name = f"Section{num}{section['archetype'].replace('-', '')}"
        rel = f"@/components/sections/{filepath.name.replace('.tsx', '')}"
        imports.append(f'import {component_name} from "{rel}";')
        components.append(f"      <{component_name} />")

    page_code = f"""{chr(10).join(imports)}

export default function Page() {{
  return (
    <main className="min-h-screen">
{chr(10).join(components)}
    </main>
  );
}}
"""
    write_file(app_dir / "page.tsx", page_code)

    # ── Install dependencies ──
    print("  Installing dependencies (npm install)...")
    result = subprocess.run(
        ["npm", "install"],
        capture_output=True,
        text=True,
        cwd=str(site_dir),
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  ⚠ npm install had issues:\n{result.stderr[-500:]}")
    else:
        print("  ✓ Dependencies installed")

    print(f"  ✓ Site deployed to output/{project_name}/site/")
    print(f"  Run: cd output/{project_name}/site && npm run dev")


def stage_review(sections: list[dict], section_files: list[Path], preset: str, project_name: str):
    """Stage 4: Run consistency review."""
    print("\n🔍 Stage 4: Running consistency review...")

    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
    style_header = extract_style_header(preset_content)

    # Concatenate all section code
    all_sections_code = ""
    for filepath in section_files:
        code = read_file(filepath)
        all_sections_code += f"\n\n--- {filepath.name} ---\n\n{code}"

    prompt = f"""You are a senior frontend QA reviewer checking a multi-section website
for visual and code consistency.

## Style Context
{style_header}

## Sections to Review
{all_sections_code}

## Consistency Checklist

Review every section and check the following. For each item, report
PASS or FAIL with the specific section(s) that violate.

### Color Consistency
- All sections use the same background color tokens
- All sections use the same text color tokens
- Accent color is identical across all buttons and links
- No section introduces colors not in the style header

### Typography Consistency
- All sections use the same heading font family
- All sections use the same body font family
- Heading sizes follow a consistent hierarchy
- Font weights match the style header specification

### Spacing Consistency
- Section padding is uniform across all sections
- Internal gap values are consistent within similar layouts
- Container max-width is the same across all sections

### Border Radius Consistency
- All buttons use the same border-radius value
- All cards use the same border-radius value
- All input fields use the same border-radius value

### Animation Consistency
- All scroll-triggered animations use the same entrance pattern
- Animation duration is consistent across sections
- Easing function is identical across all animations
- Hover states follow the same pattern

### Button Style Consistency
- Primary button style is identical everywhere
- Button text casing is consistent

For each item, output:
✅ PASS — item description
❌ FAIL — item description — Sections affected: list — Fix: specific change needed

End with:
- Total: pass_count/total_count passed
- Priority fix list ordered by visual impact"""

    review = call_claude(prompt, "review")
    write_file(OUTPUT_DIR / project_name / "review.md", review)
    print(f"\n{review}")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Website Builder Pipeline")
    parser.add_argument("project", help="Project name (must match a brief in briefs/)")
    parser.add_argument("--preset", help="Override preset selection", default=None)
    parser.add_argument("--no-pause", action="store_true", help="Skip scaffold review checkpoint")
    parser.add_argument("--skip-to", choices=["sections", "assemble", "review", "deploy"],
                        help="Skip to a specific stage (uses existing scaffold)")
    parser.add_argument("--deploy", action="store_true",
                        help="Also deploy to a runnable Next.js project at output/{project}/site/")
    parser.add_argument("--from-url", help="Clone mode: extract from URL, auto-generate preset + brief",
                        default=None, metavar="URL")

    args = parser.parse_args()

    # ── Project Collision Detection ────────────────────────────────
    # Prevent accidental overwrites when not using --skip-to (which expects existing project)
    if not args.skip_to:
        existing_scaffold = OUTPUT_DIR / args.project / "scaffold.md"
        if existing_scaffold.exists():
            print(f"\n⚠️  Project '{args.project}' already exists at: output/{args.project}/")
            print(f"    To continue an existing project, use: --skip-to <stage>")
            print(f"    To start fresh, delete the directory or use a different project name.")
            sys.exit(1)

    section_contexts = None  # Only populated in URL clone mode

    # ── URL Clone Mode ──────────────────────────────────────────────
    if args.from_url:
        print(f"\n{'═' * 60}")
        print(f"  Website Builder — URL Clone Mode")
        print(f"  Project: {args.project}")
        print(f"  Source:  {args.from_url}")
        print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═' * 60}")

        preset, brief, section_contexts = stage_url_extract(
            args.from_url, args.project
        )

        print(f"\n{'═' * 60}")
        print(f"  Stage 0 complete — switching to standard pipeline")
        print(f"  Preset:  {preset}")
        print(f"  Brief:   briefs/{args.project}.md")
        print(f"  Context: {len(section_contexts)} section(s)")
        print(f"{'═' * 60}")

    # ── Standard Mode ───────────────────────────────────────────────
    else:
        # Validate brief exists
        brief_path = BRIEFS_DIR / f"{args.project}.md"
        if not brief_path.exists():
            print(f"Error: No brief found at {brief_path}")
            print(f"Available briefs: {[f.stem for f in BRIEFS_DIR.glob('*.md') if f.stem != '_template']}")
            sys.exit(1)

        brief = read_file(brief_path)

        # Determine preset
        preset = args.preset
        if not preset:
            available = list_presets()
            if len(available) == 1:
                preset = available[0]
                print(f"Using only available preset: {preset}")
            else:
                print(f"Available presets: {', '.join(available)}")
                preset = input("Select preset: ").strip()

        preset_path = SKILLS_DIR / "presets" / f"{preset}.md"
        if not preset_path.exists():
            print(f"Error: Preset not found: {preset_path}")
            sys.exit(1)

        print(f"\n{'═' * 60}")
        print(f"  Website Builder Pipeline")
        print(f"  Project: {args.project}")
        print(f"  Preset:  {preset}")
        print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═' * 60}")

    # ── Common Pipeline ─────────────────────────────────────────────
    if args.skip_to:
        scaffold_path = OUTPUT_DIR / args.project / "scaffold.md"
        if not scaffold_path.exists():
            print(f"Error: No existing scaffold at {scaffold_path}")
            sys.exit(1)
        scaffold = read_file(scaffold_path)
    else:
        scaffold = stage_scaffold(brief, preset, args.project, args.no_pause)

    sections = parse_scaffold(scaffold)
    if not sections:
        print("Error: Could not parse any sections from scaffold.")
        print("Expected format: N. ARCHETYPE | variant | content direction")
        sys.exit(1)

    print(f"\n  Parsed {len(sections)} sections from scaffold")

    if args.skip_to in (None, "sections"):
        section_files = stage_sections(sections, preset, args.project, section_contexts)
    else:
        section_dir = OUTPUT_DIR / args.project / "sections"
        section_files = sorted(section_dir.glob("*.tsx"))

    if args.skip_to in (None, "sections", "assemble"):
        stage_assemble(sections, section_files, args.project)

    if args.skip_to in (None, "sections", "assemble", "review"):
        stage_review(sections, section_files, preset, args.project)

    if args.deploy or args.skip_to == "deploy":
        stage_deploy(sections, section_files, preset, args.project)

    mode_label = "URL Clone" if args.from_url else "Pipeline"
    print(f"\n{'═' * 60}")
    print(f"  ✅ {mode_label} complete")
    print(f"  Output: output/{args.project}/")
    if args.deploy or args.skip_to == "deploy":
        print(f"  Site:   output/{args.project}/site/")
    if args.from_url:
        print(f"  Preset: skills/presets/{preset}.md")
        print(f"  Brief:  briefs/{args.project}.md")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
