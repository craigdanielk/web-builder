#!/usr/bin/env node
/**
 * build-animation-registry.js
 *
 * Analyzes all animation/UI components (curated + 21st-dev-library) and generates:
 *   1. animation_taxonomy.json   - controlled vocabulary
 *   2. animation_registry.json   - per-component full analysis
 *   3. animation_search_index.json - query-optimised lookup
 *   4. animation_capability_matrix.csv - tabular capabilities
 *   5. analysis_log/<id>.md      - per-component classification rationale
 *
 * Usage:  node scripts/quality/build-animation-registry.js
 */

const fs = require("fs");
const path = require("path");

// Configuration
const LIBRARY_ROOT = path.resolve(__dirname, "../../skills/animation-components");
const OUTPUT_DIR = path.join(LIBRARY_ROOT, "registry");
const LOG_DIR = path.join(OUTPUT_DIR, "analysis_log");
const LIB_21ST = path.join(LIBRARY_ROOT, "21st-dev-library");
const FULL_REGISTRY_PATH = path.join(LIB_21ST, "registry-full.json");
const CURATED_CATEGORIES = ["entrance","scroll","interactive","continuous","text","effect","background"];

const SECTION_ARCHETYPES = [
  "NAV","ANNOUNCEMENT-BAR","FOOTER","HERO","LOGO-BAR","TESTIMONIALS",
  "TRUST-BADGES","FEATURES","HOW-IT-WORKS","COMPARISON","PRICING","STATS",
  "PRODUCT-SHOWCASE","GALLERY","CTA","NEWSLETTER","ABOUT","TEAM",
  "BLOG-PREVIEW","CONTACT","FAQ","PARALLAX-BREAK","MAP","VIDEO-SHOWCASE","AWARDS",
];

// Controlled taxonomy
const TAXONOMY = {
  version: "1.0.0",
  generated: new Date().toISOString(),
  motion_intents: [
    "reveal","entrance","exit","attention","emphasis","transition","morph",
    "parallax","float","pulse","shimmer","flip","scale","slide","rotate",
    "blur","glow","wave","bounce","spring","stagger","collapse","expand",
    "count","typewrite","scramble","gradient","tilt","magnetic","drag",
    "marquee","progress","pin","horizontal_scroll","cursor_follow",
    "spotlight","beam","aurora","perspective","skeleton","loading",
  ],
  interaction_intents: [
    "navigate","engage","inform","confirm","dismiss","expand","collapse",
    "select","deselect","drag","scroll","hover","focus","submit","toggle",
    "sort","filter","search","upload","download","copy","share","none",
  ],
  conversion_support_roles: [
    "attention_capture","urgency_signal","trust_indicator","social_proof",
    "value_highlight","cta_emphasis","scarcity_indicator","progress_feedback",
    "loading_feedback","delight","brand_polish","content_reveal",
    "navigation_aid","data_display","form_interaction","none",
  ],
  layout_contexts: [
    "hero","section","card","button","badge","text","image","nav","footer",
    "modal","sidebar","overlay","list_item","grid_item","full_width",
    "contained","inline","background","toast","dialog","popover","toolbar",
    "form","table","any",
  ],
  trigger_types: [
    "viewport","scroll_linked","hover","click","drag","focus","mount",
    "time_delay","intersection","resize","keyboard","media_query","none",
  ],
  component_types: ["animation","ui","hybrid"],
  animation_types: [
    "entrance","exit","scroll","hover","continuous","text","background",
    "interactive","layout","loading","effect","transition",
  ],
};

// Load the module pieces
const { extractFeatures, classifyComponent, detectMotionIntents } = require("./lib/registry-extractor");
const { buildRegistryEntry, buildSearchIndex, buildCapabilityMatrixCSV, buildAnalysisLog, mapToArchetypes } = require("./lib/registry-builders");
const { validateRegistry, discoverCuratedComponents, discover21stDevComponents } = require("./lib/registry-utils");

const { describe } = require("./lib/capability");

/** What this builder is, in its own words. Compiled into the capability register
 *  by `scripts/capability_register.py`; see that file for why it lives here. */
const CAPABILITY = {
  id: "aurelix.builder.animation-registry",
  name: "Animation component catalogue builder",
  kind: "builder",
  invocation: "node scripts/quality/build-animation-registry.js",
  preconditions: [
    "curated component sources under skills/animation-components/<category>/*.tsx",
    "skills/animation-components/21st-dev-library/ with registry-full.json for the second source — ABSENT from this checkout, measured 2026-08-18",
  ],
  inputs: [
    "skills/animation-components/{entrance,scroll,interactive,continuous,text,effect,background}/*.tsx",
    "skills/animation-components/21st-dev-library/registry-full.json",
  ],
  outputs: [
    "skills/animation-components/registry/animation_taxonomy.json",
    "skills/animation-components/registry/animation_registry.json",
    "skills/animation-components/registry/animation_search_index.json",
    "skills/animation-components/registry/animation_capability_matrix.csv",
    "skills/animation-components/registry/analysis_log/<animation_id>.md",
  ],
  outcome: "a catalogue row per discovered component — classification (animation/ui/hybrid), motion intents, triggers, archetype affinity — plus a per-component rationale log",
  exit_contract: {
    0: "the catalogue was written. This is the ONLY code it returns: quality-gate issues are printed and the run still exits 0, and a per-file read/parse error is counted and skipped",
    1: "an unhandled throw (unreadable input directory, unwritable output directory)",
  },
  measures: [
    "per-component source features: imports, engine, hooks, triggers, export shape",
    "classification into animation | ui | hybrid, and the motion intents behind it",
    "validateRegistry() issues — taxonomy violations and missing fields, printed but never fatal",
  ],
  cannot_see: [
    "that one of its two declared sources has vanished. skills/animation-components/21st-dev-library/ does not exist in this checkout; discover21stDevComponents() returns 0 and that zero is reported as a component count, not as a missing input. Re-running it today would replace the tracked 1034-row animation_registry.json with the 53 curated components alone",
    "whether the rows it wrote stay file-backed. 986 of the 1034 rows in the registry it last produced name paths under that absent tree — measured by os.path.exists over every row, 2026-08-18. The output is a CATALOGUE, not an inventory, and nothing in this builder makes that distinction",
    "drift. It only ever rewrites everything: 53 curated .tsx are on disk today against 48 file-backed registry rows, and it has no way to report those 5 as new — only to regenerate",
    "that selection does not read what it writes. component-inject.js reads animation_library.json (the 48 backed rows), which THIS builder does not emit — registry/annotate_backed_rows.py derives it. Two producers write animation_registry.json and neither knows about the other",
    "whether a classified component actually renders, compiles, or has its npm dependency installed — it reads source text and never executes anything",
  ],
  reachable_from: [],
  cost: "~5-30s, filesystem only; scales with component count. Writes one markdown log per component",
};

function main() {
  if (describe(CAPABILITY)) return;
  console.log("═══════════════════════════════════════════════════════");
  console.log("  Animation Registry Builder v1.0.0");
  console.log("═══════════════════════════════════════════════════════\n");

  // Phase 1: Discover
  console.log("Phase 1: Discovering components...");
  const curatedFiles = discoverCuratedComponents(LIBRARY_ROOT, CURATED_CATEGORIES);
  const devFiles = discover21stDevComponents(LIB_21ST, FULL_REGISTRY_PATH);
  const allFiles = [...curatedFiles, ...devFiles];
  console.log(`  Found ${curatedFiles.length} curated + ${devFiles.length} 21st-dev = ${allFiles.length} total\n`);

  // Phase 2: Extract & classify
  console.log("Phase 2: Extracting features & classifying...");
  const registry = [];
  const featureMap = new Map();
  let animCount = 0, uiCount = 0, hybridCount = 0, errors = 0;

  for (const file of allFiles) {
    try {
      const code = fs.readFileSync(file.path, "utf-8");
      const features = extractFeatures(file.path, code);
      const classification = classifyComponent(features);
      const entry = buildRegistryEntry(file.path, code, features, classification, file.source, file.slug, file.externalDeps, LIBRARY_ROOT, TAXONOMY);
      registry.push(entry);
      featureMap.set(entry.animation_id, features);
      if (classification === "animation") animCount++;
      else if (classification === "ui") uiCount++;
      else hybridCount++;
    } catch (e) {
      errors++;
      console.error(`  ERROR processing ${file.path}: ${e.message}`);
    }
  }
  console.log(`  Classified: ${animCount} animation | ${uiCount} UI | ${hybridCount} hybrid | ${errors} errors\n`);

  // Phase 3: Create output dirs
  console.log("Phase 3: Creating output directories...");
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.mkdirSync(LOG_DIR, { recursive: true });

  // Phase 4: Write taxonomy
  console.log("Phase 4: Writing animation_taxonomy.json...");
  fs.writeFileSync(path.join(OUTPUT_DIR, "animation_taxonomy.json"), JSON.stringify(TAXONOMY, null, 2));

  // Phase 5: Write registry
  console.log("Phase 5: Writing animation_registry.json...");
  const registryOutput = {
    version: "1.0.0",
    generated: new Date().toISOString(),
    total_components: registry.length,
    breakdown: { animation: animCount, ui: uiCount, hybrid: hybridCount },
    components: registry,
  };
  fs.writeFileSync(path.join(OUTPUT_DIR, "animation_registry.json"), JSON.stringify(registryOutput, null, 2));

  // Phase 6: Write search index
  console.log("Phase 6: Writing animation_search_index.json...");
  const searchIndex = buildSearchIndex(registry);
  fs.writeFileSync(path.join(OUTPUT_DIR, "animation_search_index.json"), JSON.stringify(searchIndex, null, 2));

  // Phase 7: Write CSV
  console.log("Phase 7: Writing animation_capability_matrix.csv...");
  const csv = buildCapabilityMatrixCSV(registry);
  fs.writeFileSync(path.join(OUTPUT_DIR, "animation_capability_matrix.csv"), csv);

  // Phase 8: Write analysis logs
  console.log("Phase 8: Writing analysis logs...");
  let logCount = 0;
  for (const entry of registry) {
    const features = featureMap.get(entry.animation_id);
    if (!features) continue;
    const log = buildAnalysisLog(entry, features);
    fs.writeFileSync(path.join(LOG_DIR, `${entry.animation_id}.md`), log);
    logCount++;
  }
  console.log(`  Generated ${logCount} analysis logs\n`);

  // Phase 9: Quality gates
  console.log("Phase 9: Running quality gates...");
  const issues = validateRegistry(registry, TAXONOMY, LIBRARY_ROOT);
  if (issues.length === 0) {
    console.log("  All quality gates passed\n");
  } else {
    console.log(`  ${issues.length} issues found:`);
    issues.slice(0, 20).forEach((i) => console.log(`    - ${i}`));
    if (issues.length > 20) console.log(`    ... and ${issues.length - 20} more`);
    console.log();
  }

  // Summary
  console.log("═══════════════════════════════════════════════════════");
  console.log("  COMPLETE");
  console.log("═══════════════════════════════════════════════════════");
  console.log(`  Total components analyzed: ${registry.length}`);
  console.log(`  Animation: ${animCount} | UI: ${uiCount} | Hybrid: ${hybridCount}`);
  console.log(`  Errors: ${errors}`);
  console.log(`  Quality issues: ${issues.length}`);
  console.log(`\n  Output:`);
  console.log(`    ${path.relative(process.cwd(), OUTPUT_DIR)}/animation_taxonomy.json`);
  console.log(`    ${path.relative(process.cwd(), OUTPUT_DIR)}/animation_registry.json`);
  console.log(`    ${path.relative(process.cwd(), OUTPUT_DIR)}/animation_search_index.json`);
  console.log(`    ${path.relative(process.cwd(), OUTPUT_DIR)}/animation_capability_matrix.csv`);
  console.log(`    ${path.relative(process.cwd(), OUTPUT_DIR)}/analysis_log/ (${logCount} files)`);
  console.log("═══════════════════════════════════════════════════════\n");
}

main();
