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
import time as _time
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

# API resilience
MAX_RETRIES = 3
TIMEOUT_SECONDS = 90


def call_claude_with_retry(client, messages, max_tokens, model=None, system=None, **kwargs):
    """Call Claude API with timeout and exponential backoff retry."""
    model = model or MODELS.get("section", "claude-sonnet-4-5-20250929")
    call_kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        call_kwargs["system"] = system
    call_kwargs.update(kwargs)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                timeout=TIMEOUT_SECONDS,
                **call_kwargs
            )
            return response
        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(term in error_str for term in [
                'timeout', 'rate_limit', 'overloaded', '529', '503', '500',
                'connection', 'network'
            ])
            if not is_retryable or attempt == MAX_RETRIES - 1:
                raise
            wait = (2 ** attempt) * 5  # 5s, 10s, 20s
            print(f"  ⚠ API call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            print(f"  Retrying in {wait}s...")
            _time.sleep(wait)

    raise RuntimeError(f"Claude API failed after {MAX_RETRIES} retries")


def save_checkpoint(output_dir: Path, stage: str, project_name: str, data: dict = None):
    """Save pipeline progress checkpoint after each stage."""
    checkpoint = {
        "project": project_name,
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "data": data or {}
    }
    checkpoint_file = output_dir / "checkpoint.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp = checkpoint_file.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(checkpoint, indent=2, default=str), encoding="utf-8")
    tmp.rename(checkpoint_file)
    print(f"  ✓ Checkpoint saved: stage={stage}")


def load_checkpoint(project_name: str) -> dict | None:
    """Load checkpoint for a project if it exists."""
    checkpoint_file = ROOT / "output" / project_name / "checkpoint.json"
    if checkpoint_file.exists():
        return json.loads(checkpoint_file.read_text(encoding="utf-8"))
    return None


# Stage order for --skip-to vs checkpoint validation
STAGE_ORDER = ["extract", "identify", "scaffold", "sections", "assemble", "review", "deploy"]


def _stage_index(stage: str) -> int:
    """Return index of stage in pipeline order; -1 if unknown."""
    return STAGE_ORDER.index(stage) if stage in STAGE_ORDER else -1


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

def call_claude(prompt: str, stage: str, max_tokens_override: int | None = None) -> str:
    """Call the Anthropic API and return the response text."""
    client = Anthropic()
    budget = max_tokens_override if max_tokens_override else MAX_TOKENS[stage]
    message = call_claude_with_retry(
        client,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=budget,
        model=MODELS[stage],
    )
    text_parts = [
        block.text for block in message.content if block.type == "text"
    ]
    return "\n".join(text_parts)


QUALITY_DIR = ROOT / "scripts" / "quality"
SITE_DIR_NAME = "site"  # Rendered Next.js project lives at output/{project}/site/


# --- URL Extraction Stage ---

def stage_url_extract(url: str, project_name: str) -> tuple[str, str, dict, Path, dict | None]:
    """
    Stage 0: Extract from URL and generate preset + brief.
    Returns (preset_name, brief_content, section_contexts, extraction_dir, site_spec).
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

    # Step 0d: Build site-spec.json (v2.0.0 — deterministic, zero AI calls)
    site_spec = None
    print("\n  [0d] Building site-spec.json from extraction data...")
    site_spec_script = QUALITY_DIR / "build-site-spec.js"
    if site_spec_script.exists() and extraction_data_path.exists() and mapped_sections_path.exists():
        result = subprocess.run(
            [node, str(site_spec_script), str(extraction_dir), project_name],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=60,
        )
        if result.returncode != 0:
            print(f"  ⚠ build-site-spec.js failed: {result.stderr[:300] if result.stderr else '(no stderr)'}")
        else:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"    {line}")
            site_spec_path = OUTPUT_DIR / project_name / "site-spec.json"
            if site_spec_path.exists():
                try:
                    site_spec = json.loads(site_spec_path.read_text(encoding="utf-8"))
                    print(f"  ✓ site-spec.json generated ({len(site_spec.get('sections', []))} sections)")
                except (json.JSONDecodeError, OSError):
                    print("  ⚠ Could not parse site-spec.json")
    else:
        print("  ⚠ build-site-spec.js or extraction data not found, skipping site-spec")

    return preset_name, brief_content, section_contexts, extraction_dir, site_spec


# --- Pattern Identification Stage (v0.9.0) ---

def stage_identify(extraction_dir: Path, project_name: str) -> dict | None:
    """
    Stage 0d: Run pattern identification on extraction data.
    Returns identification result dict or None if not available.
    """
    print("\n🔍 Stage 0d: Identifying patterns...")

    node = "node"
    identifier_script = QUALITY_DIR / "lib" / "pattern-identifier.js"

    if not identifier_script.exists():
        print("  ⚠ pattern-identifier.js not found, skipping identification")
        return None

    result = subprocess.run(
        [node, str(identifier_script), str(extraction_dir), project_name],
        capture_output=True,
        text=True,
        cwd=str(QUALITY_DIR),
        timeout=60,
    )

    if result.returncode != 0:
        print(f"  ⚠ Pattern identification failed: {result.stderr[:500] if result.stderr else '(no stderr)'}")
        return None

    try:
        identification = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print("  ⚠ Could not parse identification output, continuing without it")
        return None

    # Save gap report
    gap_report = identification.get("gapReport", {})
    gaps = gap_report.get("gaps", [])
    gap_path = OUTPUT_DIR / project_name / "gap-report.json"
    gap_path.parent.mkdir(parents=True, exist_ok=True)
    gap_path.write_text(json.dumps(gap_report, indent=2), encoding="utf-8")

    # Save identification for stage_deploy and section prompts
    id_path = OUTPUT_DIR / project_name / "identification.json"
    id_path.parent.mkdir(parents=True, exist_ok=True)
    id_path.write_text(json.dumps(identification, indent=2), encoding="utf-8")

    # Print summary
    color_system = identification.get("colorSystem", {})
    high = sum(1 for g in gaps if g.get("severity") == "high")
    medium = sum(1 for g in gaps if g.get("severity") == "medium")
    low = sum(1 for g in gaps if g.get("severity") == "low")

    print(f"  Color system: {color_system.get('system', 'unknown')} ({len(color_system.get('accents', []))} accents)")
    print(f"  Sections: {identification.get('sectionCount', 0)} total, {identification.get('highConfidence', 0)} high confidence")
    print(f"  Animation patterns: {len(identification.get('animationPatterns', []))} identified")
    if gaps:
        print(f"  ⚠ Gaps: {len(gaps)} ({high} high, {medium} medium, {low} low)")
    else:
        print(f"  ✓ No gaps detected")

    print(f"  → Saved: output/{project_name}/gap-report.json")

    # v1.2.0: Enrich identification with extracted icon/logo data
    extraction_data_path = extraction_dir / "extraction-data.json"
    if extraction_data_path.exists():
        try:
            ext_data = json.loads(extraction_data_path.read_text(encoding="utf-8"))
            assets = ext_data.get("assets", {})
            # Add icon library info
            icon_lib = assets.get("iconLibrary")
            if icon_lib and icon_lib.get("library"):
                identification["iconLibrary"] = icon_lib
                print(f"  Icon library: {icon_lib['library']} ({icon_lib.get('count', 0)} icons)")
            # Add extracted logos
            logos = assets.get("logos", [])
            if logos:
                identification["extractedLogos"] = logos
                print(f"  Extracted logos: {len(logos)} raster images")
            # Add extracted SVGs
            svgs = assets.get("svgs", [])
            if svgs:
                identification["extractedSVGs"] = svgs
                logo_svgs = sum(1 for s in svgs if s.get("category") == "logo")
                icon_svgs = sum(1 for s in svgs if s.get("category") == "icon")
                print(f"  Extracted SVGs: {len(svgs)} ({logo_svgs} logos, {icon_svgs} icons)")
            # Re-save enriched identification
            id_path.write_text(json.dumps(identification, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass

    return identification


def print_gap_summary(project_name: str):
    """Print gap report summary at end of build (v0.9.0)."""
    gap_path = OUTPUT_DIR / project_name / "gap-report.json"
    if not gap_path.exists():
        return

    try:
        report = json.loads(gap_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return

    gaps = report.get("gaps", [])
    if not gaps:
        return

    high = sum(1 for g in gaps if g.get("severity") == "high")
    medium = sum(1 for g in gaps if g.get("severity") == "medium")
    low = sum(1 for g in gaps if g.get("severity") == "low")

    print(f"\n{'═' * 50}")
    print(f"  ⚠ GAP REPORT SUMMARY")
    print(f"  {len(gaps)} gaps identified for {project_name}")
    if high:
        high_descs = [g["description"][:60] for g in gaps if g.get("severity") == "high"]
        print(f"    HIGH: {high} ({', '.join(high_descs)})")
    if medium:
        print(f"    MEDIUM: {medium}")
    if low:
        print(f"    LOW: {low}")
    print(f"  Extension tasks: output/{project_name}/gap-report.json")
    print(f"{'═' * 50}")


# --- Pipeline Stages ---

def stage_scaffold(brief: str, preset: str, project_name: str, no_pause: bool, identification: dict | None = None) -> str:
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

    # ── Inject identification data if available ──
    if identification:
        id_hints = []

        # Section mapping hints (improve low-confidence assignments)
        mapped = identification.get("mappedSections", [])
        low_conf = [s for s in mapped if s.get("confidence", 1) < 0.5]
        if low_conf:
            id_hints.append("\n## Reference Site Section Analysis")
            id_hints.append("The reference site was analyzed. These sections had low-confidence archetype mappings — consider better alternatives:")
            for s in low_conf:
                label = s.get("label", "Unknown")[:80]
                arch = s.get("archetype", "?")
                conf = s.get("confidence", 0)
                cls = s.get("classNames", "")
                # Suggest alternatives based on label keywords
                alt_hint = ""
                label_lower = label.lower()
                if any(w in label_lower for w in ["tested", "approved", "numbers", "stat", "metric", "field"]):
                    alt_hint = " → Consider STATS or TESTIMONIALS"
                elif any(w in label_lower for w in ["product", "format", "access", "pricing", "plan"]):
                    alt_hint = " → Consider PRODUCT-SHOWCASE or PRICING"
                elif any(w in label_lower for w in ["carbon", "sustain", "environ", "planet", "clean"]):
                    alt_hint = " → Consider ABOUT or FEATURES with sustainability variant"
                id_hints.append(f'  - "{label}" (class: {cls}) → mapped as {arch} at {conf:.0%} confidence{alt_hint}')

        # Detected plugins hint
        plugins = identification.get("detectedPlugins", [])
        if plugins:
            id_hints.append(f"\n## Detected Animation Plugins: {', '.join(plugins)}")
            id_hints.append("The reference site uses these GSAP plugins. Include sections that showcase these capabilities:")
            if "SplitText" in plugins:
                id_hints.append("  - SplitText → Use in HERO (character reveal), CTA (word reveal), TESTIMONIALS (line reveal)")
            if "Observer" in plugins:
                id_hints.append("  - Observer → Use in GALLERY (swipe gestures) or HERO (scroll velocity effects)")
            if "Flip" in plugins:
                id_hints.append("  - Flip → Use in PRODUCT-SHOWCASE (filter grid) or PORTFOLIO (expand card)")
            if "DrawSVG" in plugins:
                id_hints.append("  - DrawSVG → Use in HOW-IT-WORKS (step reveal) or FEATURES (icon stroke draw)")

        # Color system hint
        color_sys = identification.get("colorSystem", {})
        if color_sys.get("accents"):
            accents = [a.get("tailwind", "?") for a in color_sys["accents"]]
            id_hints.append(f"\n## Extracted Color System: {color_sys.get('system', 'unknown')} ({', '.join(accents)})")

        if id_hints:
            prompt += "\n" + "\n".join(id_hints)

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
        # Also handles bold markdown wrapping archetype+variant or just archetype:
        #   1. **NAV | sticky-transparent** | content...
        #   1. **NAV** | sticky-transparent | content...
        #   1. NAV | sticky-transparent | content...
        # Strip all bold markdown (**) from the line before parsing
        cleaned = line.strip().replace("**", "")
        match = re.match(
            r"\d+\.\s+([\w][\w-]*)\s*\|\s*([\w][\w-]*)\s*\|\s*(.+)",
            cleaned,
        )
        if match:
            sections.append({
                "archetype": match.group(1).strip(),
                "variant": match.group(2).strip(),
                "content": match.group(3).strip(),
            })
    return sections


def stage_scaffold_v2(site_spec: dict, project_name: str) -> tuple:
    """Stage 1 (v2): Produce section list from site-spec.json. No Claude call needed."""
    print("\n  Stage 1 (v2): Building scaffold from site-spec.json...")

    sections = []
    scaffold_lines = []

    for s in site_spec.get("sections", []):
        archetype = s.get("archetype", "FEATURES")
        variant = s.get("variant", "icon-grid")
        confidence = s.get("confidence", 0.5)
        headings = s.get("content", {}).get("headings", [])
        content_hint = headings[0] if headings else ""

        sections.append({
            "index": s["index"],
            "archetype": archetype,
            "variant": variant,
            "confidence": confidence,
            "content": s.get("content", {}),
            "images": s.get("images", []),
            "icons": s.get("icons", {}),
            "animations": s.get("animations", {}),
            "components": s.get("components", {}),
            "source_rect": s.get("source_rect", {}),
            "confidence_tier": s.get("confidence_tier", ""),
            "confidence_note": s.get("confidence_note", ""),
            "generation_guidance": s.get("generation_guidance", ""),
        })

        scaffold_lines.append(
            f"{s['index'] + 1}. {archetype} | {variant} | "
            f"confidence={confidence:.0%} | {content_hint[:60]}"
        )

    scaffold_text = "\n".join(scaffold_lines)

    # Save scaffold for reference
    output_dir = Path(f"output/{project_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "scaffold.md").write_text(
        f"# Scaffold (v2 - from site-spec.json)\n\n{scaffold_text}\n"
    )

    print(f"  {len(sections)} sections from site-spec")
    for line in scaffold_lines:
        print(f"    {line}")

    return scaffold_text, sections


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


def load_injection_data(extraction_dir: Path | None) -> tuple[dict | None, dict | None]:
    """Load animation analysis and extraction data from the extraction directory."""
    if not extraction_dir or not extraction_dir.exists():
        return None, None

    animation_analysis = None
    extraction_data = None

    anim_path = extraction_dir / "animation-analysis.json"
    if anim_path.exists():
        try:
            animation_analysis = json.loads(anim_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print("  ⚠ Could not load animation-analysis.json")

    extract_path = extraction_dir / "extraction-data.json"
    if extract_path.exists():
        try:
            extraction_data = json.loads(extract_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print("  ⚠ Could not load extraction-data.json")

    return animation_analysis, extraction_data


def call_injector(script: str, args_json: str) -> dict | None:
    """Call a Node.js injection module and return parsed JSON result."""
    node_script = f"""
const mod = require('./lib/{script}');
const args = JSON.parse('{args_json.replace("'", "\\'")}');
const result = mod.fn(args);
console.log(JSON.stringify(result));
"""
    # We'll call each injector's exported function directly via inline script
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True, text=True,
        cwd=str(QUALITY_DIR), timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return None
    return None


def get_animation_contexts(
    animation_analysis: dict | None,
    preset_content: str,
    sections: list[dict],
    identification: dict | None = None,
) -> dict:
    """Call animation-injector.js to get per-section animation context."""
    node_script = f"""
const {{ buildAllAnimationContexts }} = require('./lib/animation-injector');
const animAnalysis = {json.dumps(animation_analysis) if animation_analysis else 'null'};
const presetContent = {json.dumps(preset_content)};
const sections = {json.dumps(sections)};
const identification = {json.dumps(identification) if identification else 'null'};
const result = buildAllAnimationContexts(animAnalysis, presetContent, sections, identification);
console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True, text=True,
        cwd=str(QUALITY_DIR), timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            print("  ⚠ Could not parse animation injection results")
    else:
        if result.stderr:
            print(f"  ⚠ Animation injector error: {result.stderr[-300:]}")
    return {}


def get_asset_contexts(
    extraction_data: dict | None,
    sections: list[dict],
) -> dict:
    """Call asset-injector.js to get per-section asset context."""
    if not extraction_data:
        return {}

    node_script = f"""
const {{ buildAllAssetContexts }} = require('./lib/asset-injector');
const extractionData = {json.dumps(extraction_data)};
const sections = {json.dumps(sections)};
const result = buildAllAssetContexts(extractionData, sections);
console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        capture_output=True, text=True,
        cwd=str(QUALITY_DIR), timeout=30,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            print("  ⚠ Could not parse asset injection results")
    else:
        if result.stderr:
            print(f"  ⚠ Asset injector error: {result.stderr[-300:]}")
    return {}


def get_icon_context(
    archetype: str,
    section_index: int,
    extracted_icons: list | None = None,
) -> str:
    """Call icon-mapper.js to get Lucide React icon context block for a section."""
    node_script = f"""
const {{ buildIconContextBlock }} = require('./lib/icon-mapper');
const result = buildIconContextBlock({json.dumps(archetype)}, {section_index}, {json.dumps(extracted_icons or [])});
console.log(result);
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""


def get_visual_fallback(
    archetype: str,
    section_index: int,
    is_card_grid: bool = False,
    card_count: int = 0,
) -> dict:
    """Call asset-injector.js getVisualFallback() for sections without images."""
    node_script = f"""
const {{ getVisualFallback }} = require('./lib/asset-injector');
const result = getVisualFallback({json.dumps(archetype)}, {section_index}, {json.dumps(is_card_grid)}, {card_count});
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"block": "", "componentFiles": []}


def get_card_embedded_demos(detected_plugins: list) -> dict:
    """Call animation-injector.js buildCardEmbeddedDemos() for plugin demo cards."""
    node_script = f"""
const {{ buildCardEmbeddedDemos }} = require('./lib/animation-injector');
const result = buildCardEmbeddedDemos({json.dumps(detected_plugins)});
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"block": "", "componentFiles": []}


def get_ui_component_matches(
    detected_patterns: list,
    search_index_path: Path | None = None,
) -> dict:
    """Call pattern-identifier.js matchUIComponents() + buildUIComponentBlock()."""
    search_index_load = "null"
    if search_index_path and search_index_path.exists():
        search_index_load = f"require('{search_index_path}')"

    node_script = f"""
const {{ matchUIComponents, buildUIComponentBlock }} = require('./lib/pattern-identifier');
const searchIndex = {search_index_load};
const matches = matchUIComponents({json.dumps(detected_patterns)}, searchIndex);
const result = buildUIComponentBlock(matches);
result.matches = matches;
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"block": "", "componentFiles": [], "matches": []}


def _detect_and_repair_truncation(code: str, section_name: str) -> dict | None:
    """Call post-process.js detectAndRepairTruncation() via Node.js subprocess.

    Returns dict with keys: truncated, repaired, code, warnings.
    Returns None if the Node.js call fails (caller should proceed with original code).
    """
    node_script = f"""
const {{ detectAndRepairTruncation }} = require('./lib/post-process');
const code = {json.dumps(code)};
const result = detectAndRepairTruncation(code, {json.dumps(section_name)});
console.log(JSON.stringify(result));
"""
    try:
        result = subprocess.run(
            ["node", "-e", node_script],
            capture_output=True, text=True,
            cwd=str(QUALITY_DIR), timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def stage_sections(
    sections: list[dict],
    preset: str,
    project_name: str,
    section_contexts: dict | None = None,
    extraction_dir: Path | None = None,
    identification: dict | None = None,
    site_spec: dict | None = None,
) -> list[Path]:
    """Stage 2: Generate each section component individually with engine-aware injection."""
    print(f"\n🔨 Stage 2: Generating {len(sections)} sections...")
    if section_contexts:
        print(f"  (with per-section reference context from URL extraction)")

    preset_content = read_file(SKILLS_DIR / "presets" / f"{preset}.md")
    style_header = extract_style_header(preset_content)
    taxonomy = read_file(SKILLS_DIR / "section-taxonomy.md")
    engine = detect_animation_engine(preset_content)

    # Load engine-specific instruction template
    if engine == "gsap":
        instructions = read_file(TEMPLATES_DIR / "section-instructions-gsap.md")
    else:
        instructions = read_file(TEMPLATES_DIR / "section-instructions-framer.md")

    print(f"  Animation engine: {engine}")

    # Load injection data if available (URL clone mode)
    animation_analysis, extraction_data = load_injection_data(extraction_dir)

    # Build injection contexts
    animation_contexts = {}
    asset_contexts = {}
    if animation_analysis or extraction_data:
        print("  Loading injection data...")
        if animation_analysis:
            raw_anim = get_animation_contexts(
                animation_analysis, preset_content, sections, identification
            )
            # buildAllAnimationContexts returns { contexts: {...}, allComponentFiles: [...], ... }
            # Extract the per-section contexts dict and flatten it for section access
            if raw_anim and "contexts" in raw_anim:
                animation_contexts = raw_anim["contexts"]
                comp_files = raw_anim.get("allComponentFiles", [])
                non_empty = sum(1 for v in animation_contexts.values()
                                if v.get("animationContext", "").strip())
                print(f"  ✓ Animation context for {non_empty}/{len(animation_contexts)} sections"
                      f" ({len(comp_files)} library components matched)")
            elif raw_anim:
                # Fallback: if structure changed, use raw dict
                animation_contexts = raw_anim
                print(f"  ✓ Animation context loaded (legacy format)")
        if extraction_data:
            asset_contexts = get_asset_contexts(extraction_data, sections)
            if asset_contexts:
                non_empty_assets = sum(1 for v in asset_contexts.values()
                                       if v.get("assetContext", "").strip())
                print(f"  ✓ Asset context for {non_empty_assets}/{len(asset_contexts)} sections")

    section_files = []
    all_extra_component_files = []  # v1.2.0: collect extra component files for stage_deploy

    for i, section in enumerate(sections):
        num = f"{i + 1:02d}"
        name = section["archetype"].lower().replace("-", "_")
        filename = f"{num}-{name}.tsx"

        # Get per-section injection blocks
        anim_ctx = animation_contexts.get(str(i), {})
        animation_block = anim_ctx.get("animationContext", "")
        token_budget = anim_ctx.get("tokenBudget", MAX_TOKENS["section"])

        asset_ctx = asset_contexts.get(str(i), {})
        asset_block = asset_ctx.get("assetContext", "")

        budget_label = f" [{token_budget} tokens]" if token_budget != MAX_TOKENS["section"] else ""
        print(f"  [{num}/{len(sections):02d}] {section['archetype']} | {section['variant']}{budget_label}...")

        # Try to find structural reference in taxonomy
        structure_ref = "[No structural reference yet — infer from archetype and variant]"
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

        # Build animation and asset context blocks
        animation_context_block = ""
        if animation_block:
            animation_context_block = f"\n{animation_block}\n"

        asset_context_block = ""
        if asset_block:
            asset_context_block = f"\n{asset_block}\n"

        # Build identification context block (v0.9.0)
        identification_block = ""
        if identification:
            id_parts = []

            # Per-section accent color override
            section_colors = identification.get("sectionColorProfile", {}).get("sectionColors", {})
            sec_color = section_colors.get(str(i), {})
            if sec_color and sec_color.get("accent"):
                id_parts.append(
                    f"## Section Accent Color\n"
                    f"This section's accent color is {sec_color['accent']} (not the default site accent).\n"
                    f"Use {sec_color['accent']} for highlights, buttons, icons, and accent elements in this section."
                )

            # Per-section animation patterns
            section_mapping = identification.get("sectionMapping", {})
            sec_map = section_mapping.get(str(i), {})
            if sec_map:
                anims = sec_map.get("animations", [])
                for anim in anims[:2]:
                    if anim.get("bestMatch"):
                        id_parts.append(
                            f"## Identified Animation Pattern\n"
                            f"Pattern: {anim['pattern']} (from reference site analysis)\n"
                            f"Registry component: {anim['bestMatch']}\n"
                            f"Use this animation pattern for entrance/interaction in this section."
                        )
                ui_comps = sec_map.get("uiComponents", [])
                if ui_comps:
                    id_parts.append(
                        f"## Identified UI Components\n"
                        f"Detected: {', '.join(ui_comps)}\n"
                        f"Incorporate these UI patterns into the section layout."
                    )

            if id_parts:
                identification_block = "\n" + "\n\n".join(id_parts) + "\n"

        # Pinned scroll context block (v1.1.0, reclassified v1.1.2)
        # Triggers on animation assignment (gsap-pinned-horizontal pattern), not archetype
        pinned_scroll_block = ""
        uses_pinned_scroll = (
            (animation_block and "pinned-horizontal" in animation_block.lower())
            or (animation_block and "pin: true" in animation_block.lower() and "scrub" in animation_block.lower())
            or (identification and identification.get("pinnedScrollDetected"))
        )
        if uses_pinned_scroll:
            pinned_scroll_block = """
═══ PINNED HORIZONTAL SCROLL RULES ═══
This section uses GSAP ScrollTrigger with pin: true and scrub: true.
Structure: section (100vh) → overflow-hidden container → flex track with will-change-transform → panels.
Each panel should be min-w-[100vw] or content-sized blocks.

CRITICAL: Use `containerAnimation` for ANY nested animations inside the pinned scroll.
Without containerAnimation, nested ScrollTriggers respond to vertical page scroll, not horizontal position.

MUST include:
- gsap.matchMedia() for mobile fallback (< 768px → vertical stack)
- invalidateOnRefresh: true for responsive recalculation
- Progress indicator (bar, dots, or panel counter)
- prefers-reduced-motion handler

See section-instructions-gsap.md for the full pinned horizontal scroll technique.
═══════════════════════════════════════
"""

        # GSAP plugin context for section prompt (when identification has detectedPlugins)
        plugin_block = ""
        if identification and identification.get("detectedPlugins"):
            plugins = identification["detectedPlugins"]
            plugin_block = f"\n═══ GSAP PLUGIN CONTEXT ═══\nDetected plugins: {', '.join(plugins)}\nUse these plugins where appropriate for this section.\n═══════════════════════════\n"

        # ── v1.2.0: Icon context block ──
        extracted_icons = []
        if identification:
            icon_lib = identification.get("iconLibrary", {})
            if isinstance(icon_lib, dict):
                extracted_icons = icon_lib.get("icons", [])
        icon_block = get_icon_context(section["archetype"], i, extracted_icons)
        if icon_block:
            icon_block = f"\n{icon_block}\n"

        # ── v1.2.0: Visual content fallback (when no images for this section) ──
        visual_fallback_block = ""
        extra_component_files = []
        has_asset_images = bool(asset_block and ("backgroundImage" in asset_block or "image" in asset_block.lower()))
        if not has_asset_images:
            is_card_grid = section["variant"] in (
                "demo-cards", "feature-cards", "benefit-cards", "grid", "card-grid",
                "three-column", "four-column", "bento-grid",
            )
            card_count = 6 if is_card_grid else 0
            vf = get_visual_fallback(section["archetype"], i, is_card_grid, card_count)
            if vf.get("block"):
                visual_fallback_block = f"\n{vf['block']}\n"
                extra_component_files.extend(vf.get("componentFiles", []))

        # ── v1.2.0: Card embedded animation demos (PRODUCT-SHOWCASE demo-cards) ──
        card_embed_block = ""
        if (section["archetype"].upper() == "PRODUCT-SHOWCASE"
                and "demo" in section.get("variant", "").lower()
                and identification and identification.get("detectedPlugins")):
            ced = get_card_embedded_demos(identification["detectedPlugins"])
            if ced.get("block"):
                card_embed_block = f"\n{ced['block']}\n"
                extra_component_files.extend(ced.get("componentFiles", []))

        # ── v1.2.0: UI component injection ──
        ui_component_block = ""
        if identification:
            sec_map = identification.get("sectionMapping", {}).get(str(i), {})
            ui_patterns = sec_map.get("uiComponents", [])
            if ui_patterns:
                search_idx = SKILLS_DIR / "animation-components" / "registry" / "animation_search_index.json"
                ucm = get_ui_component_matches(ui_patterns, search_idx)
                if ucm.get("block"):
                    ui_component_block = f"\n{ucm['block']}\n"
                    extra_component_files.extend(ucm.get("componentFiles", []))

        # ── v2.0.0: Build style + section spec block ──
        # When site_spec is available (--from-url), use JSON style tokens directly.
        # When not (--preset mode), fall back to the compact style header.
        if site_spec:
            style_json = json.dumps(site_spec.get("style", {}), indent=2)
            # Build section-specific JSON from the v2 sections list
            sec_data = section  # Already a rich dict from stage_scaffold_v2
            section_spec_json = json.dumps({
                "archetype": sec_data.get("archetype", "FEATURES"),
                "variant": sec_data.get("variant", "icon-grid"),
                "confidence": sec_data.get("confidence", 1.0),
                "content": sec_data.get("content", {}),
                "images": sec_data.get("images", []),
                "icons": sec_data.get("icons", {}),
                "animations": sec_data.get("animations", {}),
                "components": sec_data.get("components", {}),
                "generation_guidance": sec_data.get("generation_guidance", ""),
            }, indent=2)

            # Resolve content direction for display
            content_dir = sec_data.get("content", {})
            if isinstance(content_dir, dict):
                headings = content_dir.get("headings", [])
                content_display = headings[0] if headings else "(content from site-spec)"
            else:
                content_display = str(content_dir)

            style_and_spec_block = f"""STYLE TOKENS (use these exact values — colors as hex, fonts as names, spacing as rem):
{style_json}

SECTION SPEC (structured data — use exact values, do not interpret or paraphrase):
{section_spec_json}

IMPORTANT: If the section spec contains "components.matched" with import_statement values,
use those EXACT import statements. Do not construct your own import paths.
If images are provided with src URLs, use them as backgroundImage CSS — not <img> tags.
The generation_guidance field indicates confidence level — follow its instructions."""

        else:
            # Legacy --preset mode: use compact style header
            style_and_spec_block = f"""{style_header}

## Section Specification
Number: {i + 1} of {len(sections)}
Archetype: {section['archetype']}
Variant: {section['variant']}
Content Direction: {section['content']}"""
            content_display = section.get("content", "")
            if isinstance(content_display, dict):
                headings = content_display.get("headings", [])
                content_display = headings[0] if headings else ""

        prompt = f"""You are a senior frontend developer generating a single website section
as a React + Tailwind CSS component.

{style_and_spec_block}

## Structural Reference
{structure_ref}
{ref_context_block}{animation_context_block}{asset_context_block}{identification_block}{pinned_scroll_block}{plugin_block}{icon_block}{visual_fallback_block}{card_embed_block}{ui_component_block}
{instructions}
Component name: Section{num}{section['archetype'].replace('-', '')}"""

        # Sections using pinned horizontal scroll are complex — minimum 8192 tokens
        if uses_pinned_scroll:
            token_budget = max(token_budget, 8192)

        code = call_claude(prompt, "section", max_tokens_override=token_budget)

        # Clean up any markdown code fences that might have snuck in
        code = re.sub(r"^```\w*\n?", "", code)
        code = re.sub(r"\n?```$", "", code)

        # ── Truncation detection & repair (v1.1.1) ──
        truncation_result = _detect_and_repair_truncation(code, filename)
        if truncation_result:
            if truncation_result.get("truncated"):
                if truncation_result.get("repaired"):
                    code = truncation_result["code"]
                    print(f"    ⚠ {filename}: truncated — auto-repaired")
                    for w in truncation_result.get("warnings", []):
                        print(f"      {w}")
                else:
                    print(f"    ❌ {filename}: truncated but could not be repaired")

        # Post-process: ensure "use client" directive for components using
        # animation libraries or React hooks
        client_markers = [
            "framer-motion", "motion.", "useState", "useEffect",
            "useRef", "useCallback", "useMemo", "gsap", "ScrollTrigger",
            "DotLottieReact", "lucide-react",
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

        save_checkpoint(OUTPUT_DIR / project_name, "sections", project_name, {"last_section_index": i, "section_count": len(sections)})

        # v1.2.0: Track extra component files for this section
        if extra_component_files:
            all_extra_component_files.extend(extra_component_files)

    # v1.2.0: Save extra component manifest for stage_deploy
    if all_extra_component_files:
        unique_files = list(set(all_extra_component_files))
        manifest_path = OUTPUT_DIR / project_name / "extra-components.json"
        write_file(manifest_path, json.dumps(unique_files, indent=2))
        print(f"  ✓ {len(unique_files)} extra component files queued for stage_deploy")

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
    """Extract heading and body font names from preset's YAML style config."""
    # Match YAML format: heading_font: FontName
    heading = "Inter"
    body = "Inter"
    h_match = re.search(r"heading_font:\s*([A-Za-z][A-Za-z0-9_ ]+)", preset_content)
    if h_match:
        heading = h_match.group(1).strip()
    b_match = re.search(r"body_font:\s*([A-Za-z][A-Za-z0-9_ ]+)", preset_content)
    if b_match:
        body = b_match.group(1).strip()
    # Guard: discard if YAML leaked into the capture
    yaml_markers = ("---", "palette", "bg_primary", "accent")
    if any(m in heading for m in yaml_markers) or any(m in body for m in yaml_markers):
        print("⚠ parse_fonts: detected YAML leak, falling back to Inter")
        heading = "Inter"
        body = "Inter"
    return {"heading": heading, "body": body}


def font_import_name(font_name: str) -> str:
    """Convert a font display name to its next/font/google import name."""
    return font_name.replace(" ", "_")


def stage_deploy(
    sections: list[dict],
    section_files: list[Path],
    preset: str,
    project_name: str,
    extraction_dir: Path | None = None,
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
            "framer-motion": "^12.33.0",  # Always included (hover/tap effects)
            "clsx": "^2.1.1",
            "tailwind-merge": "^2.6.0",
            "lucide-react": "^0.468.0",
        }
        if engine == "gsap":
            deps["gsap"] = "^3.14.2"

        # Detect Lottie assets from extraction data
        has_lottie = False
        if extraction_dir:
            anim_path = extraction_dir / "animation-analysis.json"
            if anim_path.exists():
                try:
                    anim_data = json.loads(anim_path.read_text(encoding="utf-8"))
                    lottie_files = anim_data.get("lottieFiles", [])
                    lottie_assets = (anim_data.get("assets", {}) or {}).get("lottie", [])
                    has_lottie = len(lottie_files) > 0 or len(lottie_assets) > 0
                except (json.JSONDecodeError, OSError):
                    pass
        # Also detect from generated sections importing DotLottieReact
        if not has_lottie:
            for sf in section_files:
                if sf.exists() and "DotLottieReact" in sf.read_text(encoding="utf-8"):
                    has_lottie = True
                    break
        if has_lottie:
            deps["@lottiefiles/dotlottie-react"] = "^0.13.0"
            print(f"  Lottie files detected — adding @lottiefiles/dotlottie-react")

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

        # next.config.ts — ignoreBuildErrors for GSAP/Framer Motion type issues
        write_file(
            site_dir / "next.config.ts",
            'import type { NextConfig } from "next";\n\n'
            "const nextConfig: NextConfig = {\n"
            "  typescript: { ignoreBuildErrors: true },\n"
            "};\n\n"
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
    heading_font = fonts["heading"]
    body_font = fonts["body"]

    # Common Google Fonts that can be imported via next/font/google
    GOOGLE_FONTS = {
        "Inter", "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins",
        "Source Sans Pro", "Source Sans 3", "Raleway", "Nunito", "Playfair Display",
        "Merriweather", "DM Sans", "Space Grotesk", "Plus Jakarta Sans",
        "Outfit", "Sora", "Geist", "Manrope", "Urbanist", "Archivo",
        "Work Sans", "Libre Baskerville", "Cormorant Garamond",
    }

    heading_is_google = heading_font in GOOGLE_FONTS
    body_is_google = body_font in GOOGLE_FONTS

    heading_import = font_import_name(heading_font) if heading_is_google else None
    body_import = font_import_name(body_font) if body_is_google else None

    # Extract weights from preset
    heading_weights = '"400"'
    body_weights = '["400", "500", "700"]'
    h_weight_match = re.search(r"heading_weight:\s*(\d+)", preset_content)
    if h_weight_match:
        heading_weights = f'"{h_weight_match.group(1)}"'

    # Build layout.tsx
    import_lines = ['import type { Metadata } from "next";']
    google_imports = []
    if heading_import:
        google_imports.append(heading_import)
    if body_import and body_import != heading_import:
        google_imports.append(body_import)
    if google_imports:
        import_lines.append(f'import {{ {", ".join(google_imports)} }} from "next/font/google";')
    import_lines.append('import "./globals.css";')

    font_config_lines = []
    if heading_import:
        font_config_lines.append(
            f'const {heading_import.lower()} = {heading_import}({{ subsets: ["latin"], weight: {heading_weights} }});'
        )
    if body_import and body_import != heading_import:
        font_config_lines.append(
            f'const {body_import.lower()} = {body_import}({{ subsets: ["latin"], weight: {body_weights} }});'
        )

    # Build font-family CSS fallback for non-Google fonts
    font_family = f"'{heading_font}', system-ui, sans-serif"

    font_config = chr(10).join(font_config_lines) if font_config_lines else ""
    if font_config:
        font_config = chr(10) + font_config + chr(10)

    layout_code = f"""{chr(10).join(import_lines)}
{font_config}
export const metadata: Metadata = {{
  title: "{project_name.replace('-', ' ').title()}",
  description: "Built with web-builder pipeline",
}};

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="en">
      <body className="antialiased" style={{{{ fontFamily: "{font_family}" }}}}>
        {{children}}
      </body>
    </html>
  );
}}
"""
    write_file(app_dir / "layout.tsx", layout_code)

    # ── Generate cn() utility (clsx + tailwind-merge) ──
    lib_dir = src_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    cn_util = 'import { clsx, type ClassValue } from "clsx";\nimport { twMerge } from "tailwind-merge";\n\nexport function cn(...inputs: ClassValue[]) {\n  return twMerge(clsx(inputs));\n}\n'
    write_file(lib_dir / "utils.ts", cn_util)

    # ── GSAP setup with plugin imports when plugins detected ──
    if engine == "gsap":
        project_dir = OUTPUT_DIR / project_name
        identification_path = project_dir / "identification.json"
        plugins = []
        if identification_path.exists():
            try:
                id_data = json.loads(identification_path.read_text(encoding="utf-8"))
                plugins = id_data.get("detectedPlugins", [])
            except (json.JSONDecodeError, OSError):
                pass
        if plugins:
            plugin_imports = []
            plugin_registers = []
            PLUGIN_IMPORT_MAP = {
                "SplitText": ("SplitText", "gsap/SplitText"),
                "Flip": ("Flip", "gsap/Flip"),
                "DrawSVG": ("DrawSVGPlugin", "gsap/DrawSVGPlugin"),
                "MorphSVG": ("MorphSVGPlugin", "gsap/MorphSVGPlugin"),
                "MotionPath": ("MotionPathPlugin", "gsap/MotionPathPlugin"),
                "CustomEase": ("CustomEase", "gsap/CustomEase"),
                "Observer": ("Observer", "gsap/Observer"),
                "ScrambleText": ("ScrambleTextPlugin", "gsap/ScrambleTextPlugin"),
                "Draggable": ("Draggable", "gsap/Draggable"),
                "ScrollSmoother": ("ScrollSmoother", "gsap/ScrollSmoother"),
            }
            for p in plugins:
                if p in PLUGIN_IMPORT_MAP:
                    name, path = PLUGIN_IMPORT_MAP[p]
                    plugin_imports.append(f'import {{ {name} }} from "{path}";')
                    plugin_registers.append(name)
            if plugin_registers:
                gsap_setup = f'''"use client";
import gsap from "gsap";
import {{ ScrollTrigger }} from "gsap/ScrollTrigger";
{chr(10).join(plugin_imports)}

if (typeof window !== "undefined") {{
  gsap.registerPlugin(ScrollTrigger, {", ".join(plugin_registers)});
}}

export {{ gsap, ScrollTrigger, {", ".join(plugin_registers)} }};
'''
                gsap_setup_path = site_dir / "src" / "lib" / "gsap-setup.ts"
                gsap_setup_path.parent.mkdir(parents=True, exist_ok=True)
                gsap_setup_path.write_text(gsap_setup)
                print(f"  Created gsap-setup.ts with plugins: {', '.join(plugin_registers)}")

    # ── Copy sections ──
    print("  Copying sections...")
    comp_dir.mkdir(parents=True, exist_ok=True)
    for filepath in section_files:
        code = read_file(filepath)
        write_file(comp_dir / filepath.name, code)

    # ── Copy animation components from library ──
    anim_components_dir = SKILLS_DIR / "animation-components"
    registry_path = anim_components_dir / "component-registry.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            components = registry.get("components", {})
            # Collect archetypes used in this build
            used_archetypes = set()
            for sec in sections:
                used_archetypes.add(sec.get("archetype", "").upper().replace("_", "-"))
            # Find components that match used archetypes and are not placeholders
            anim_dest = src_dir / "components" / "animations"
            copied_count = 0
            new_deps = {}
            for pattern_name, comp_def in components.items():
                if comp_def.get("status") == "placeholder":
                    continue
                comp_archetypes = [a.upper() for a in comp_def.get("archetypes", [])]
                # Copy if any archetype matches, or if component has no archetype restriction
                if not comp_archetypes or used_archetypes.intersection(comp_archetypes):
                    # Unified registry uses source_file; legacy uses file
                    rel_path = comp_def.get("source_file") or comp_def.get("file", "")
                    src_file = anim_components_dir / rel_path
                    if src_file.exists():
                        anim_dest.mkdir(parents=True, exist_ok=True)
                        dest_file = anim_dest / f"{pattern_name}.tsx"
                        write_file(dest_file, src_file.read_text(encoding="utf-8"))
                        copied_count += 1
                        for dep in comp_def.get("dependencies", []):
                            new_deps[dep] = "latest"
            if copied_count > 0:
                print(f"  ✓ Copied {copied_count} animation component(s) to components/animations/")
                # Add any new deps to package.json
                # v2.0.0: filter invalid/remapped package names
                INVALID_PKGS = {"@gsap", "motion"}  # @gsap is a scope not a package; motion duplicates framer-motion
                PKG_REMAP = {}  # add remappings here if needed (e.g., {"old-pkg": "new-pkg"})
                if new_deps:
                    pkg_path = site_dir / "package.json"
                    pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))
                    existing_deps = pkg_data.get("dependencies", {})
                    added = []
                    for dep_name, dep_ver in new_deps.items():
                        # Skip known-invalid packages
                        if dep_name in INVALID_PKGS:
                            remap = PKG_REMAP.get(dep_name)
                            if remap:
                                dep_name = remap
                            else:
                                continue
                        if dep_name not in existing_deps:
                            existing_deps[dep_name] = dep_ver
                            added.append(dep_name)
                    if added:
                        pkg_data["dependencies"] = existing_deps
                        write_file(pkg_path, json.dumps(pkg_data, indent=2) + "\n")
                        print(f"  ✓ Added dependencies: {', '.join(added)}")
            else:
                print("  ℹ No animation components ready (all placeholders)")

            # Validate copied animation components (Phase 5D)
            if anim_dest.exists():
                anim_files = list(anim_dest.glob("*.tsx"))
                component_issues = []
                for af in anim_files:
                    content = af.read_text(encoding="utf-8")
                    # Check for valid export
                    if "export default" not in content and "export {" not in content:
                        component_issues.append(f"  ⚠ {af.name}: missing export")
                    # Check for wrong import path
                    if "from 'motion/react'" in content or 'from "motion/react"' in content:
                        component_issues.append(
                            f"  ⚠ {af.name}: uses motion/react instead of framer-motion"
                        )
                        # Auto-fix
                        fixed = content.replace(
                            "from 'motion/react'", "from 'framer-motion'"
                        ).replace('from "motion/react"', 'from "framer-motion"')
                        af.write_text(fixed, encoding="utf-8")
                        component_issues[-1] += " (auto-fixed)"
                    # Check for @/lib/utils dependency
                    if "@/lib/utils" in content:
                        utils_path = site_dir / "src" / "lib" / "utils.ts"
                        if not utils_path.exists():
                            component_issues.append(
                                f"  ⚠ {af.name}: imports @/lib/utils but utils.ts doesn't exist"
                            )
                if component_issues:
                    print(f"  Component validation ({len(component_issues)} issues):")
                    for ci in component_issues:
                        print(ci)
                else:
                    print(f"  ✅ {len(anim_files)} animation components validated")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠ Could not process animation registry: {e}")

    # ── v1.2.0: Copy extra components (visual fallbacks, card demos, UI components) ──
    extra_manifest_path = OUTPUT_DIR / project_name / "extra-components.json"
    if extra_manifest_path.exists():
        try:
            extra_files = json.loads(extra_manifest_path.read_text(encoding="utf-8"))
            anim_dest = src_dir / "components" / "animations"
            anim_dest.mkdir(parents=True, exist_ok=True)
            extra_copied = 0
            for comp_file in extra_files:
                # comp_file is like "background/aurora-background.tsx" or "entrance/blur-fade.tsx"
                src_file = anim_components_dir / comp_file
                if src_file.exists():
                    # Use the filename without the category prefix as the dest name
                    dest_name = Path(comp_file).stem + ".tsx"
                    dest_file = anim_dest / dest_name
                    if not dest_file.exists():
                        write_file(dest_file, src_file.read_text(encoding="utf-8"))
                        extra_copied += 1
                else:
                    print(f"  ⚠ Extra component not found: {comp_file}")
            if extra_copied > 0:
                print(f"  ✓ Copied {extra_copied} extra component(s) (visual fallbacks, demos, UI)")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠ Could not process extra components: {e}")

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

    # ── Download assets if extraction data available ──
    if extraction_dir:
        extract_path = extraction_dir / "extraction-data.json"
        if extract_path.exists():
            print("  Downloading extracted assets...")
            download_script = f"""
const {{ categorizeImages, getDownloadManifest }} = require('./lib/asset-injector');
const {{ verifyAssets, downloadAssets }} = require('./lib/asset-downloader');

(async () => {{
  try {{
    const extractionData = require('{extract_path}');
    const categorized = categorizeImages(extractionData);
    if (categorized.length === 0) {{
      console.log(JSON.stringify({{ downloaded: 0, skipped: "no images" }}));
      return;
    }}
    const manifest = getDownloadManifest(categorized);
    const verified = await verifyAssets(manifest);
    if (verified.length === 0) {{
      console.log(JSON.stringify({{ downloaded: 0, skipped: "none accessible" }}));
      return;
    }}
    const assetManifest = await downloadAssets(verified, '{site_dir}');
    console.log(JSON.stringify({{
      downloaded: Object.keys(assetManifest).length,
      manifest: assetManifest
    }}));
  }} catch (err) {{
    console.error(err.message);
    console.log(JSON.stringify({{ downloaded: 0, error: err.message }}));
  }}
}})();
"""
            dl_result = subprocess.run(
                ["node", "-e", download_script],
                capture_output=True, text=True,
                cwd=str(QUALITY_DIR), timeout=120,
            )
            if dl_result.returncode == 0 and dl_result.stdout.strip():
                try:
                    dl_data = json.loads(dl_result.stdout.strip())
                    count = dl_data.get("downloaded", 0)
                    if count > 0:
                        print(f"  ✓ Downloaded {count} assets to public/")
                    else:
                        skip = dl_data.get("skipped", dl_data.get("error", "unknown"))
                        print(f"  ⚠ No assets downloaded ({skip})")
                except json.JSONDecodeError:
                    print(f"  ⚠ Asset download output not parseable")
            else:
                if dl_result.stderr:
                    print(f"  ⚠ Asset download error: {dl_result.stderr[-300:]}")

    # ── Download Lottie assets if detected ──
    if extraction_dir:
        anim_path = extraction_dir / "animation-analysis.json"
        if anim_path.exists():
            try:
                anim_data = json.loads(anim_path.read_text(encoding="utf-8"))
                lottie_urls = []
                for lf in anim_data.get("lottieFiles", []):
                    url = lf.get("url", "") if isinstance(lf, dict) else str(lf)
                    if url and url.startswith("http"):
                        lottie_urls.append(url)
                # Also check assets.lottie
                for la in (anim_data.get("assets", {}) or {}).get("lottie", []):
                    url = la.get("url", "") if isinstance(la, dict) else str(la)
                    if url and url.startswith("http"):
                        lottie_urls.append(url)
                lottie_urls = list(set(lottie_urls))
                if lottie_urls:
                    print(f"  Downloading {len(lottie_urls)} Lottie assets...")
                    lottie_dir = site_dir / "public" / "lottie"
                    lottie_dir.mkdir(parents=True, exist_ok=True)
                    lottie_dl_script = f"""
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const urls = {json.dumps(lottie_urls)};
const outDir = '{lottie_dir}';
let downloaded = 0;

async function downloadOne(url) {{
  const filename = url.split('/').pop().split('?')[0] || 'animation.json';
  const outPath = path.join(outDir, filename);
  const proto = url.startsWith('https') ? https : http;
  return new Promise((resolve) => {{
    proto.get(url, {{ timeout: 10000 }}, (res) => {{
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {{
        proto.get(res.headers.location, {{ timeout: 10000 }}, (r2) => {{
          const chunks = [];
          r2.on('data', c => chunks.push(c));
          r2.on('end', () => {{ fs.writeFileSync(outPath, Buffer.concat(chunks)); downloaded++; resolve(); }});
        }}).on('error', () => resolve());
        return;
      }}
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {{ if (res.statusCode === 200) {{ fs.writeFileSync(outPath, Buffer.concat(chunks)); downloaded++; }} resolve(); }});
    }}).on('error', () => resolve());
  }});
}}

(async () => {{
  await Promise.all(urls.map(downloadOne));
  console.log(JSON.stringify({{ downloaded }}));
}})();
"""
                    lottie_result = subprocess.run(
                        ["node", "-e", lottie_dl_script],
                        capture_output=True, text=True, timeout=60,
                    )
                    if lottie_result.returncode == 0 and lottie_result.stdout.strip():
                        try:
                            ld = json.loads(lottie_result.stdout.strip())
                            print(f"  ✓ Downloaded {ld.get('downloaded', 0)} Lottie files to public/lottie/")
                        except json.JSONDecodeError:
                            print("  ⚠ Lottie download output not parseable")
                    elif lottie_result.stderr:
                        print(f"  ⚠ Lottie download error: {lottie_result.stderr[-200:]}")
            except (json.JSONDecodeError, OSError):
                pass

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


def stage_review_v2(section_files: list[Path], site_spec: dict | None, project_name: str) -> dict:
    """Stage 4 (v2): Deterministic consistency review. No Claude call."""
    print("\n🔍 Stage 4 (v2): Running deterministic consistency review...")

    issues = []
    section_count = len(section_files)

    # Load site-spec style tokens if available
    style = site_spec.get("style", {}) if site_spec else {}
    palette = style.get("palette", {})

    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended-A
        "]+",
        flags=re.UNICODE
    )

    placeholder_patterns = [
        "/api/placeholder", "via.placeholder.com", "placehold.co",
        "placekitten.com", "picsum.photos", "placeholder.svg",
        "example.com/image", "unsplash.com/random",
    ]

    for section_file in section_files:
        if not section_file.exists():
            issues.append({
                "file": section_file.name,
                "severity": "error",
                "check": "file_exists",
                "message": f"Section file not found: {section_file}"
            })
            continue

        code = section_file.read_text()
        filename = section_file.name

        # ── Check: "use client" directive ──────────────────────────
        if '"use client"' not in code and "'use client'" not in code:
            issues.append({
                "file": filename,
                "severity": "error",
                "check": "use_client",
                "message": "Missing 'use client' directive"
            })

        # ── Check: export default present ──────────────────────────
        if 'export default' not in code:
            issues.append({
                "file": filename,
                "severity": "error",
                "check": "export_default",
                "message": "Missing 'export default' — component won't render"
            })

        # ── Check: balanced braces ─────────────────────────────────
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            issues.append({
                "file": filename,
                "severity": "error",
                "check": "brace_balance",
                "message": f"Unbalanced braces: {open_braces} open, {close_braces} close"
            })

        # ── Check: no emoji characters ─────────────────────────────
        emoji_matches = emoji_pattern.findall(code)
        if emoji_matches:
            issues.append({
                "file": filename,
                "severity": "warning",
                "check": "no_emoji",
                "message": f"Contains emoji characters: {emoji_matches[:3]}"
            })

        # ── Check: no placeholder image URLs ───────────────────────
        for pattern in placeholder_patterns:
            if pattern in code:
                issues.append({
                    "file": filename,
                    "severity": "warning",
                    "check": "no_placeholder_images",
                    "message": f"Contains placeholder image URL: {pattern}"
                })

        # ── Check: imports are valid (basic) ───────────────────────
        import_lines = [l.strip() for l in code.split('\n') if l.strip().startswith('import ')]
        for imp_line in import_lines:
            if "from ''" in imp_line or 'from ""' in imp_line:
                issues.append({
                    "file": filename,
                    "severity": "error",
                    "check": "valid_imports",
                    "message": f"Empty import source: {imp_line[:80]}"
                })
            if "from 'motion/react'" in imp_line or 'from "motion/react"' in imp_line:
                issues.append({
                    "file": filename,
                    "severity": "warning",
                    "check": "valid_imports",
                    "message": f"Import from 'motion/react' should be 'framer-motion': {imp_line[:80]}"
                })

        # ── Check: JSX is not truncated ────────────────────────────
        stripped = code.rstrip()
        if stripped and not stripped.endswith(('}', ';', ')', '`', '"', "'")):
            issues.append({
                "file": filename,
                "severity": "warning",
                "check": "not_truncated",
                "message": f"File may be truncated — ends with: ...{stripped[-20:]}"
            })

    # ── Summary ────────────────────────────────────────────────────
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    passed = len(errors) == 0

    result = {
        "passed": passed,
        "section_count": section_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
    }

    # Save review
    output_dir = OUTPUT_DIR / project_name
    output_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / "review.json"
    review_path.write_text(json.dumps(result, indent=2))

    # Also write human-readable review.md
    review_md = "# Consistency Review (v2 — Deterministic)\n\n"
    review_md += f"**Result:** {'PASS' if passed else 'FAIL'}\n"
    review_md += f"**Sections reviewed:** {section_count}\n"
    review_md += f"**Errors:** {len(errors)}\n"
    review_md += f"**Warnings:** {len(warnings)}\n\n"

    if issues:
        review_md += "## Issues\n\n"
        for issue in issues:
            icon = "❌" if issue["severity"] == "error" else "⚠️"
            review_md += f"- {icon} **{issue['file']}** [{issue['check']}]: {issue['message']}\n"
    else:
        review_md += "No issues found.\n"

    (output_dir / "review.md").write_text(review_md)

    # Print summary
    print(f"  {'✅ PASS' if passed else '❌ FAIL'}: {len(errors)} errors, {len(warnings)} warnings")
    for issue in errors:
        print(f"    ❌ {issue['file']}: {issue['message']}")
    for issue in warnings[:5]:
        print(f"    ⚠  {issue['file']}: {issue['message']}")
    if len(warnings) > 5:
        print(f"    ... and {len(warnings) - 5} more warnings")

    return result


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


def stage_validate(project_name: str) -> dict:
    """Stage 5.5: Pre-flight validation — catch errors before deployment."""
    print("\n═══ STAGE 5.5: PRE-FLIGHT VALIDATION ═══\n")

    project_dir = OUTPUT_DIR / project_name
    sections_dir = project_dir / "sections"
    issues = []

    # 1. Check all section files exist and have content
    section_files = sorted(sections_dir.glob("*.tsx")) if sections_dir.exists() else []
    repaired_count = 0
    if not section_files:
        issues.append("CRITICAL: No section files found in sections/")
    else:
        for sf in section_files:
            content = sf.read_text(encoding="utf-8")
            if len(content.strip()) < 50:
                issues.append(f"CRITICAL: {sf.name} is nearly empty ({len(content)} chars)")
                continue

            # 2. Check "use client" directive
            if '"use client"' not in content and "'use client'" not in content:
                issues.append(f"WARNING: {sf.name} missing 'use client' directive")

            # 3. Check export default
            if 'export default' not in content:
                issues.append(f"CRITICAL: {sf.name} missing export default")

            # 4. Truncation detection & auto-repair (v1.1.1 — replaces basic brace check)
            truncation_result = _detect_and_repair_truncation(content, sf.name)
            if truncation_result and truncation_result.get("truncated"):
                if truncation_result.get("repaired"):
                    sf.write_text(truncation_result["code"], encoding="utf-8")
                    repaired_count += 1
                    issues.append(f"WARNING: {sf.name} was truncated — auto-repaired (brace/JSX/export fix)")
                    for w in truncation_result.get("warnings", []):
                        issues.append(f"WARNING: {sf.name}: {w}")
                else:
                    issues.append(f"CRITICAL: {sf.name} is truncated and could not be auto-repaired")
            elif not truncation_result:
                # Fallback: basic brace balance if Node.js call failed
                open_braces = content.count('{')
                close_braces = content.count('}')
                if abs(open_braces - close_braces) > 2:
                    issues.append(f"WARNING: {sf.name} has unbalanced braces (open={open_braces}, close={close_braces})")

    if repaired_count:
        print(f"  🔧 Auto-repaired {repaired_count} truncated section(s)")

    # 5. Check scaffold exists
    scaffold_path = project_dir / "scaffold.md"
    if not scaffold_path.exists():
        issues.append("WARNING: scaffold.md not found")

    # 6. Check page.tsx exists
    page_path = project_dir / "page.tsx"
    if page_path.exists():
        page_content = page_path.read_text(encoding="utf-8")
        # Check imports match actual section files
        for sf in section_files:
            component_name = sf.stem.split('-', 1)[-1] if '-' in sf.stem else sf.stem
            # Just check the filename is referenced somewhere in page.tsx
            if sf.stem not in page_content and component_name not in page_content:
                issues.append(f"WARNING: {sf.name} not imported in page.tsx")
    else:
        issues.append("WARNING: page.tsx not found (will be created during assembly)")

    # Report
    if issues:
        critical = [i for i in issues if i.startswith("CRITICAL")]
        warnings = [i for i in issues if i.startswith("WARNING")]
        print(f"  Found {len(critical)} critical issues, {len(warnings)} warnings:\n")
        for issue in issues:
            prefix = "  ❌" if issue.startswith("CRITICAL") else "  ⚠"
            print(f"{prefix} {issue}")

        if critical:
            print(f"\n  🛑 {len(critical)} critical issues must be fixed before deployment.")
    else:
        print("  ✅ All pre-flight checks passed.")

    return {'passed': len([i for i in issues if i.startswith("CRITICAL")]) == 0, 'issues': issues}


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
    parser.add_argument("--clean", action="store_true",
                        help="Delete existing output and start completely fresh")
    parser.add_argument("--force", action="store_true",
                        help="Ignore warnings (low confidence, validation issues) and proceed")

    args = parser.parse_args()

    output_dir = OUTPUT_DIR / args.project
    if args.clean and output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print(f"  🗑 Removed existing output: {output_dir}")

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
    extraction_dir = None    # Only populated in URL clone mode
    identification = None    # Only populated in URL clone mode (v0.9.0)
    site_spec = None         # Only populated when build-site-spec.js succeeds (--from-url)

    # ── URL Clone Mode ──────────────────────────────────────────────
    if args.from_url:
        print(f"\n{'═' * 60}")
        print(f"  Website Builder — URL Clone Mode")
        print(f"  Project: {args.project}")
        print(f"  Source:  {args.from_url}")
        print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═' * 60}")

        preset, brief, section_contexts, extraction_dir, site_spec = stage_url_extract(
            args.from_url, args.project
        )
        save_checkpoint(output_dir, "extract", args.project)

        # Stage 0d: Pattern identification (v0.9.0)
        if extraction_dir and extraction_dir.exists():
            identification = stage_identify(extraction_dir, args.project)
            save_checkpoint(output_dir, "identify", args.project)

        print(f"\n{'═' * 60}")
        print(f"  Stage 0 complete — switching to standard pipeline")
        print(f"  Preset:  {preset}")
        print(f"  Brief:   briefs/{args.project}.md")
        print(f"  Context: {len(section_contexts)} section(s)")
        if identification:
            print(f"  Patterns: {identification.get('sectionCount', 0)} sections identified")
        if site_spec:
            print(f"  Site spec: {len(site_spec.get('sections', []))} sections")
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

    # Resolve extraction_dir from previous runs if not set (e.g. --skip-to mode)
    if extraction_dir is None:
        extraction_base = OUTPUT_DIR / "extractions"
        if extraction_base.exists():
            # Try exact project name first, then preset name as fallback
            search_prefixes = [f"{args.project}-"]
            if preset and preset != args.project:
                search_prefixes.append(f"{preset}-")
            for prefix in search_prefixes:
                candidates = sorted(
                    [d for d in extraction_base.iterdir()
                     if d.is_dir() and d.name.startswith(prefix)],
                    key=lambda d: d.stat().st_mtime,
                    reverse=True,
                )
                if candidates:
                    extraction_dir = candidates[0]
                    print(f"  Resolved extraction dir: {extraction_dir.name}")
                    break

    # Load identification data if not already set (e.g. --skip-to without --from-url)
    if identification is None:
        id_path = OUTPUT_DIR / args.project / "identification.json"
        if id_path.exists():
            try:
                identification = json.loads(id_path.read_text(encoding="utf-8"))
                plugins_found = identification.get("detectedPlugins", [])
                if plugins_found:
                    print(f"  Identification loaded: {len(plugins_found)} plugins detected ({', '.join(plugins_found)})")
            except (json.JSONDecodeError, OSError):
                print("  ⚠ Could not load identification.json")

    # Load site_spec from file when not set (e.g. --skip-to after a from_url run)
    if site_spec is None:
        site_spec_path = OUTPUT_DIR / args.project / "site-spec.json"
        if site_spec_path.exists():
            try:
                site_spec = json.loads(site_spec_path.read_text(encoding="utf-8"))
                print(f"  ✓ site-spec.json loaded ({len(site_spec.get('sections', []))} sections)")
            except (json.JSONDecodeError, OSError):
                pass

    if args.skip_to:
        cp = load_checkpoint(args.project)
        if cp:
            skip_idx = _stage_index(args.skip_to)
            # To run from skip_to we need the previous stage completed
            need_idx = skip_idx - 1 if skip_idx > 0 else 0
            cur_idx = _stage_index(cp.get("stage", ""))
            if cur_idx >= 0 and cur_idx < need_idx:
                print(f"Error: Cannot --skip-to {args.skip_to}: checkpoint is '{cp.get('stage')}' (complete stages up to {STAGE_ORDER[need_idx]} first).")
                sys.exit(1)
        else:
            print("  ⚠ No checkpoint found; --skip-to proceeds using filesystem state (backward compatibility).")

        # v2.0.0: prefer rich sections from site-spec.json over scaffold parsing
        if site_spec:
            _scaffold_text, sections = stage_scaffold_v2(site_spec, args.project)
            print(f"  ✓ Using rich sections from site-spec.json ({len(sections)} sections)")
        else:
            scaffold_path = OUTPUT_DIR / args.project / "scaffold.md"
            if not scaffold_path.exists():
                print(f"Error: No existing scaffold at {scaffold_path}")
                sys.exit(1)
            scaffold = read_file(scaffold_path)
            sections = parse_scaffold(scaffold)
    else:
        if site_spec:
            scaffold, sections = stage_scaffold_v2(site_spec, args.project)
            save_checkpoint(output_dir, "scaffold", args.project)
        else:
            scaffold = stage_scaffold(brief, preset, args.project, args.no_pause, identification)
            save_checkpoint(output_dir, "scaffold", args.project)
            sections = parse_scaffold(scaffold)

    if not sections:
        print("Error: Could not parse any sections from scaffold.")
        print("Expected format: N. ARCHETYPE | variant | content direction")
        sys.exit(1)

    print(f"\n  Parsed {len(sections)} sections from scaffold")

    if args.skip_to in (None, "sections"):
        section_files = stage_sections(
            sections, preset, args.project, section_contexts, extraction_dir, identification,
            site_spec=site_spec,
        )
        save_checkpoint(output_dir, "sections", args.project, {"section_count": len(section_files)})
    else:
        section_dir = OUTPUT_DIR / args.project / "sections"
        section_files = sorted(section_dir.glob("*.tsx"))

    if args.skip_to in (None, "sections", "assemble"):
        stage_assemble(sections, section_files, args.project)
        save_checkpoint(output_dir, "assemble", args.project)

    if args.skip_to in (None, "sections", "assemble", "review"):
        site_spec_path = output_dir / "site-spec.json"
        site_spec = None
        if site_spec_path.exists():
            try:
                site_spec = json.loads(site_spec_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        if site_spec:
            stage_review_v2(section_files, site_spec, args.project)
        else:
            stage_review(sections, section_files, preset, args.project)
        save_checkpoint(output_dir, "review", args.project)

    # Stage 5.5: Pre-flight validation (before deploy)
    deploy_ran = False
    if args.deploy or args.skip_to == "deploy":
        validation = stage_validate(args.project)
        if not validation['passed']:
            print("\n  ⚠ Pre-flight validation found critical issues.")
            if not args.force:
                print("  Use --force to deploy anyway, or fix the issues above.")
        if validation['passed'] or args.force:
            stage_deploy(sections, section_files, preset, args.project, extraction_dir)
            save_checkpoint(output_dir, "deploy", args.project)
            deploy_ran = True

    # Print gap report summary if available (v0.9.0)
    if args.from_url:
        print_gap_summary(args.project)

    mode_label = "URL Clone" if args.from_url else "Pipeline"
    print(f"\n{'═' * 60}")
    print(f"  ✅ {mode_label} complete")
    print(f"  Output: output/{args.project}/")
    if deploy_ran:
        print(f"  Site:   output/{args.project}/site/")
    if args.from_url:
        print(f"  Preset: skills/presets/{preset}.md")
        print(f"  Brief:  briefs/{args.project}.md")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
