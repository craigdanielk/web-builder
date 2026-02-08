#!/usr/bin/env python3
"""
Website Builder Orchestration Pipeline

Automates the multi-pass generation workflow:
  1. Read brief + match preset
  2. Generate scaffold (page specification)
  3. Generate each section individually with style header
  4. Assemble into complete page
  5. Run consistency review

Usage:
  python scripts/orchestrate.py <project-name> [--preset <preset-name>] [--no-pause]

Requirements:
  pip install anthropic --break-system-packages
"""

import os
import sys
import json
import argparse
import re
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

# Model selection per pipeline stage
MODELS = {
    "scaffold": "claude-sonnet-4-5-20250514",    # Good judgment for structure
    "section": "claude-sonnet-4-5-20250514",      # Fast, good for individual components
    "review": "claude-sonnet-4-5-20250514",       # Good judgment for quality eval
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
) -> list[Path]:
    """Stage 2: Generate each section component individually."""
    print(f"\n🔨 Stage 2: Generating {len(sections)} sections...")

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
    parser.add_argument("--skip-to", choices=["sections", "assemble", "review"],
                        help="Skip to a specific stage (uses existing scaffold)")

    args = parser.parse_args()

    # Validate
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

    # Run pipeline
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
        section_files = stage_sections(sections, preset, args.project)
    else:
        section_dir = OUTPUT_DIR / args.project / "sections"
        section_files = sorted(section_dir.glob("*.tsx"))

    if args.skip_to in (None, "sections", "assemble"):
        stage_assemble(sections, section_files, args.project)

    if args.skip_to in (None, "sections", "assemble", "review"):
        stage_review(sections, section_files, preset, args.project)

    print(f"\n{'═' * 60}")
    print(f"  ✅ Pipeline complete")
    print(f"  Output: output/{args.project}/")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
