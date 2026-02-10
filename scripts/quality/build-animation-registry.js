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

function main() {
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
