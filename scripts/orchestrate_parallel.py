#!/usr/bin/env python3
"""
Website Builder — Parallel Section Generator

Generates all sections concurrently for faster execution.
Use this after the scaffold is reviewed and approved.

Usage:
  python scripts/orchestrate_parallel.py <project-name> --preset <preset-name>

This script:
  1. Reads an existing scaffold from output/{project}/scaffold.md
  2. Fires all section generations in parallel
  3. Assembles the page
  4. Runs the consistency review

Requirements:
  pip install anthropic --break-system-packages
"""

import asyncio
import json
import os
import subprocess
import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

try:
    from anthropic import AsyncAnthropic
except ImportError:
    print("Error: anthropic package not installed.")
    print("Run: pip install anthropic --break-system-packages")
    sys.exit(1)


ROOT = Path(__file__).parent.parent
SKILLS_DIR = ROOT / "skills"
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "output"
SITE_DIR_NAME = "site"

SECTION_MODEL = "claude-sonnet-4-5-20250514"
REVIEW_MODEL = "claude-sonnet-4-5-20250514"


def read_file(path: Path) -> str:
    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_scaffold(scaffold: str) -> list[dict]:
    sections = []
    for line in scaffold.split("\n"):
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
    match = re.search(
        r"(═══ STYLE CONTEXT ═══.*?═══════════════════════)",
        preset_content,
        re.DOTALL,
    )
    return match.group(1) if match else "[Style header not found]"


async def generate_section(
    client: AsyncAnthropic,
    section: dict,
    index: int,
    total: int,
    style_header: str,
) -> tuple[int, str]:
    """Generate a single section component asynchronously."""
    num = f"{index + 1:02d}"

    prompt = f"""You are a senior frontend developer generating a single website section
as a React + Tailwind CSS + Framer Motion component.

{style_header}

## Section Specification
Number: {index + 1} of {total}
Archetype: {section['archetype']}
Variant: {section['variant']}
Content Direction: {section['content']}

## Instructions

Generate a complete, self-contained React component for this section.

Requirements:
1. Use TypeScript with React.FC typing
2. Use ONLY the colors, fonts, spacing, radius, and animation values from
   the STYLE CONTEXT header above.
3. Self-contained — only React, Framer Motion, and Tailwind CSS
4. Semantic HTML, responsive (mobile-first with sm/md/lg breakpoints)
5. Realistic text content — no lorem ipsum
6. Framer Motion whileInView for scroll-triggered animations
7. Match the animation intensity from the style header

Output ONLY the component code. No markdown fences. Export as default.
Component name: Section{num}{section['archetype'].replace('-', '')}"""

    message = await client.messages.create(
        model=SECTION_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    code = "\n".join(
        block.text for block in message.content if block.type == "text"
    )
    code = re.sub(r"^```\w*\n?", "", code)
    code = re.sub(r"\n?```$", "", code)

    return index, code


def detect_animation_engine(preset_content: str) -> str:
    """Detect animation engine from preset's Motion line."""
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
    return font_name.replace(" ", "_")


def stage_deploy(sections, section_files, preset, project_name):
    """Deploy sections into a runnable Next.js project at output/{project}/site/."""
    print("\n🚀 Deploying to Next.js project...")

    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
    engine = detect_animation_engine(preset_content)
    fonts = parse_fonts(preset_content)
    style_header = extract_style_header(preset_content)

    site_dir = OUTPUT_DIR / project_name / SITE_DIR_NAME
    src_dir = site_dir / "src"
    app_dir = src_dir / "app"
    comp_dir = src_dir / "components" / "sections"

    if not (site_dir / "package.json").exists():
        print("  Creating project structure...")
        deps = {"next": "16.1.6", "react": "19.2.3", "react-dom": "19.2.3"}
        if engine == "gsap":
            deps["gsap"] = "^3.14.2"
        else:
            deps["framer-motion"] = "^12.33.0"

        pkg = {
            "name": project_name, "version": "0.1.0", "private": True,
            "scripts": {"dev": "next dev --webpack", "build": "next build", "start": "next start", "lint": "eslint"},
            "dependencies": deps,
            "devDependencies": {
                "@tailwindcss/postcss": "^4", "@types/node": "^20",
                "@types/react": "^19", "@types/react-dom": "^19",
                "eslint": "^9", "eslint-config-next": "16.1.6",
                "tailwindcss": "^4", "typescript": "^5",
            },
        }
        write_file(site_dir / "package.json", json.dumps(pkg, indent=2) + "\n")
        write_file(site_dir / "tsconfig.json", json.dumps({
            "compilerOptions": {
                "target": "ES2017", "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True, "skipLibCheck": True, "strict": True, "noEmit": True,
                "esModuleInterop": True, "module": "esnext", "moduleResolution": "bundler",
                "resolveJsonModule": True, "isolatedModules": True, "jsx": "preserve",
                "incremental": True, "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        }, indent=2) + "\n")
        write_file(site_dir / "next.config.ts",
                    'import type { NextConfig } from "next";\n\nconst nextConfig: NextConfig = {};\n\nexport default nextConfig;\n')
        write_file(site_dir / "postcss.config.mjs",
                    'const config = {\n  plugins: {\n    "@tailwindcss/postcss": {},\n  },\n};\n\nexport default config;\n')
        write_file(site_dir / ".gitignore", "node_modules/\n.next/\n*.tsbuildinfo\nnext-env.d.ts\n")

    # globals.css
    css = ['@import "tailwindcss";', "", ":root { --background: #fafaf9; --foreground: #1c1917; }",
           "body {", "  background: var(--background);", "  color: var(--foreground);",
           f'  font-family: "{fonts["body"]}", sans-serif;',
           "  -webkit-font-smoothing: antialiased;", "  -moz-osx-font-smoothing: grayscale;", "}"]
    if engine == "gsap":
        css += ["", "html { scroll-behavior: smooth; }", "",
                "::-webkit-scrollbar { width: 4px; }", "::-webkit-scrollbar-track { background: transparent; }",
                "::-webkit-scrollbar-thumb { background: #78716c; border-radius: 2px; }", "",
                "::selection { background: #78716c; color: #ffffff; }", "",
                "@keyframes marquee {", "  0% { transform: translateX(0); }",
                "  100% { transform: translateX(-50%); }", "}"]
    write_file(app_dir / "globals.css", "\n".join(css) + "\n")

    # layout.tsx
    hi = font_import_name(fonts["heading"])
    bi = font_import_name(fonts["body"])
    h_weight = '"400"'
    m = re.search(r"heading:[^,]+,(\d+)", preset_content)
    if m:
        h_weight = f'"{m.group(1)}"'
    layout_lines = [
        'import type { Metadata } from "next";',
        f'import {{ {hi}, {bi} }} from "next/font/google";',
        'import "./globals.css";',
    ]
    layout_code = "\n".join(layout_lines) + f"""

const {hi.lower()} = {hi}({{ subsets: ["latin"], weight: {h_weight} }});
const {bi.lower()} = {bi}({{ subsets: ["latin"], weight: ["400", "500", "700"] }});

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

    # Copy sections
    comp_dir.mkdir(parents=True, exist_ok=True)
    for fp in section_files:
        write_file(comp_dir / fp.name, read_file(fp))

    # page.tsx
    imports, comps = [], []
    for i, (section, fp) in enumerate(zip(sections, section_files)):
        num = f"{i + 1:02d}"
        cn = f"Section{num}{section['archetype'].replace('-', '')}"
        imports.append(f'import {cn} from "@/components/sections/{fp.name.replace(".tsx", "")}";')
        comps.append(f"      <{cn} />")
    write_file(app_dir / "page.tsx",
               "\n".join(imports) + "\n\nexport default function Page() {\n  return (\n    <main className=\"min-h-screen\">\n"
               + "\n".join(comps) + "\n    </main>\n  );\n}\n")

    # npm install
    print("  Installing dependencies...")
    result = subprocess.run(["npm", "install"], capture_output=True, text=True, cwd=str(site_dir), timeout=120)
    if result.returncode != 0:
        print(f"  ⚠ npm install issues:\n{result.stderr[-500:]}")
    else:
        print("  ✓ Dependencies installed")
    print(f"  ✓ Site: output/{project_name}/site/")


async def main_async(project_name: str, preset: str, deploy: bool = False):
    """Run the parallel pipeline."""
    client = AsyncAnthropic()

    # Load scaffold
    scaffold_path = OUTPUT_DIR / project_name / "scaffold.md"
    scaffold = read_file(scaffold_path)
    sections = parse_scaffold(scaffold)

    if not sections:
        print("Error: No sections parsed from scaffold.")
        sys.exit(1)

    # Load preset and extract style header
    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
    style_header = extract_style_header(preset_content)

    print(f"\n⚡ Generating {len(sections)} sections in parallel...")
    start = datetime.now()

    # Fire all section generations concurrently
    tasks = [
        generate_section(client, section, i, len(sections), style_header)
        for i, section in enumerate(sections)
    ]
    results = await asyncio.gather(*tasks)

    # Sort by index and save
    results.sort(key=lambda x: x[0])
    section_files = []

    for index, code in results:
        section = sections[index]
        num = f"{index + 1:02d}"
        name = section["archetype"].lower().replace("-", "_")
        filename = f"{num}-{name}.tsx"
        filepath = OUTPUT_DIR / project_name / "sections" / filename
        write_file(filepath, code)
        section_files.append(filepath)
        print(f"  ✅ {filename}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n  Generated {len(sections)} sections in {elapsed:.1f}s")

    # Assemble page
    print("\n📦 Assembling page...")
    imports = []
    components = []
    for i, (section, filepath) in enumerate(zip(sections, section_files)):
        num = f"{i + 1:02d}"
        comp_name = f"Section{num}{section['archetype'].replace('-', '')}"
        imports.append(f'import {comp_name} from "./sections/{filepath.name.replace(".tsx", "")}";')
        components.append(f"      <{comp_name} />")

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

    # Review
    print("\n🔍 Running consistency review...")
    all_code = ""
    for fp in section_files:
        all_code += f"\n\n--- {fp.name} ---\n\n{read_file(fp)}"

    review_msg = await client.messages.create(
        model=REVIEW_MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"""Review these website sections for consistency against the style context.

{style_header}

{all_code}

Check: color tokens, typography, spacing, border-radius, animation patterns,
button styles. For each dimension report PASS or FAIL with affected sections.
End with a priority fix list.""",
        }],
    )

    review = "\n".join(
        block.text for block in review_msg.content if block.type == "text"
    )
    write_file(OUTPUT_DIR / project_name / "review.md", review)

    if deploy:
        stage_deploy(sections, section_files, preset, project_name)

    print(f"\n{'═' * 60}")
    print(f"  ✅ Parallel pipeline complete")
    print(f"  Output: output/{project_name}/")
    if deploy:
        print(f"  Site:   output/{project_name}/site/")
    print(f"  Total time: {elapsed:.1f}s for section generation")
    print(f"{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="Parallel Website Builder")
    parser.add_argument("project", help="Project name")
    parser.add_argument("--preset", required=True, help="Preset name")
    parser.add_argument("--deploy", action="store_true",
                        help="Deploy to a runnable Next.js project at output/{project}/site/")
    args = parser.parse_args()

    asyncio.run(main_async(args.project, args.preset, args.deploy))


if __name__ == "__main__":
    main()
