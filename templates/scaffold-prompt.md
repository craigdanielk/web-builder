# Scaffold Prompt Template

Use this template to generate a page specification from a client brief and
industry preset.

---

## Template

```
You are a senior web designer creating a page specification for a new website.

## Client Brief
{BRIEF_CONTENT}

## Industry Preset
{PRESET_SECTION_SEQUENCE}

## Available Section Archetypes
{TAXONOMY_ARCHETYPE_LIST}

## Instructions

Based on the client brief, generate a page specification. Use the industry
preset's section sequence as your starting point, then adapt it:

1. ADD sections if the brief mentions needs not covered by the default sequence
2. REMOVE sections that aren't relevant to this specific client
3. REORDER if the client's priorities suggest a different flow
4. SELECT the best variant for each section based on the brief's specifics

Output format — a numbered section list:

```
Page: {project name}
Preset: {preset used}
Style: {key style descriptors from preset}
Animation Engine: {framer-motion or gsap}

1. {ARCHETYPE} | {variant} | {animation pattern} | {content direction for this section}
2. {ARCHETYPE} | {variant} | {animation pattern} | {content direction for this section}
...
```

For each section:
- **Animation pattern**: Reference a named pattern from skills/animation-patterns.md.
  Use the Pattern-to-Archetype Map as the default, then override if the brief
  or section content suggests something different. Examples:
  * HERO → character-reveal, word-reveal, or staggered-timeline
  * STATS → count-up
  * FEATURES → fade-up-stagger
  * MAP → marker-pulse
  * Most sections → fade-up-stagger (safe default)
- **Content direction**: Write 1-2 sentences describing:
  * What specific content goes here (not generic, specific to THIS client)
  * Any notable layout considerations

Do NOT generate any code. This is a specification only.
```

---

## Variable Substitutions

- `{BRIEF_CONTENT}` → Contents of `briefs/{project}.md`
- `{PRESET_SECTION_SEQUENCE}` → The "Default Section Sequence" block from the matched preset
- `{TAXONOMY_ARCHETYPE_LIST}` → Just the archetype names and variant names from section-taxonomy.md (not the full structural descriptions — keep it concise)

---

## Expected Output

A clean numbered list that can be parsed by the section generation step.
Each line must follow the format:

```
N. ARCHETYPE | variant | animation pattern | content direction
```

This output gets saved to `output/{project}/scaffold.md` and becomes the
input for the section-by-section generation step.

---

## Quality Checks

Before accepting the scaffold:
- Every section archetype must exist in the taxonomy
- Every variant must exist under its archetype
- No two adjacent sections should serve the same purpose
- The sequence should have a logical narrative flow (problem → solution → proof → conversion)
- Total section count should be 6-14 (under 6 feels incomplete, over 14 feels bloated)
