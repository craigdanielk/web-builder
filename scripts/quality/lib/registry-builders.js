/**
 * registry-builders.js
 *
 * Generates registry entries, search index, capability matrix CSV,
 * and analysis log markdown from extracted features.
 */

const path = require("path");

// Section archetype mapping signals
const ARCHETYPE_SIGNALS = {
  HERO: { filename: /hero|landing|banner|splash/i, content: /hero|headline|tagline|call.?to.?action/i },
  PRICING: { filename: /pricing|price|plan|subscription|tier/i, content: /\$\d+|monthly|yearly|annual|premium|starter|enterprise|free.?tier/i },
  FOOTER: { filename: /footer|bottom.?bar/i, content: /copyright|privacy|terms|all.?rights/i },
  NAV: { filename: /nav|navbar|header|menu|topbar|sidebar/i, content: /menu|navigation|hamburger/i },
  TESTIMONIALS: { filename: /testimonial|review|feedback|quote/i, content: /testimonial|review|rating|stars|customer.?said/i },
  FEATURES: { filename: /feature|benefit|capability|service/i, content: /feature|benefit|capability/i },
  CTA: { filename: /cta|call.?to.?action|signup|get.?started/i, content: /get.?started|sign.?up|subscribe|join|try.?free/i },
  FAQ: { filename: /faq|question|accordion|help/i, content: /frequently|question|answer|faq/i },
  CONTACT: { filename: /contact|form|reach|message/i, content: /contact|email|phone|address|send.?message/i },
  TEAM: { filename: /team|member|people|staff|about.?us/i, content: /team|member|developer|designer|ceo|founder|role/i },
  NEWSLETTER: { filename: /newsletter|subscribe|mail|email.?capture/i, content: /newsletter|subscribe|email|inbox/i },
  "PRODUCT-SHOWCASE": { filename: /product|shop|store|catalog|showcase/i, content: /product|shop|add.?to.?cart|buy.?now/i },
  "LOGO-BAR": { filename: /logo|brand|client|partner|sponsor/i, content: /trusted.?by|partner|client/i },
  GALLERY: { filename: /gallery|photo|portfolio|grid/i, content: /gallery|portfolio|project|showcase/i },
  STATS: { filename: /stat|metric|number|counter|achievement/i, content: /\d+\+|\d+k|\d+%|achievement|metric/i },
  "HOW-IT-WORKS": { filename: /how.?it.?works|step|process|workflow|timeline/i, content: /step\s*\d|how.?it.?works|process|workflow/i },
  "BLOG-PREVIEW": { filename: /blog|article|post|news/i, content: /blog|article|read.?more|publish/i },
  ABOUT: { filename: /about|story|mission|values/i, content: /about|story|mission|vision|values|history/i },
  COMPARISON: { filename: /compar|versus|vs\b/i, content: /compare|versus|vs\b/i },
  MAP: { filename: /map|location|direction/i, content: /map|location|direction|address/i },
  "VIDEO-SHOWCASE": { filename: /video|media|player/i, content: /video|play|watch/i },
};

function mapToArchetypes(filename, code) {
  const matches = [];
  for (const [archetype, signals] of Object.entries(ARCHETYPE_SIGNALS)) {
    let score = 0;
    if (signals.filename.test(filename)) score += 3;
    if (signals.content.test(code)) score += 2;
    if (score >= 3) matches.push({ archetype, score });
  }
  matches.sort((a, b) => b.score - a.score);
  return matches.map((m) => m.archetype);
}

function detectConversionRoles(features, classification, archetypes, taxonomy) {
  const roles = new Set();
  const mi = features.motionIntents;

  if (mi.includes("reveal")) roles.add("content_reveal");
  if (mi.includes("attention")) roles.add("attention_capture");
  if (mi.includes("emphasis")) roles.add("urgency_signal");
  if (mi.includes("pulse")) roles.add("urgency_signal");
  if (mi.includes("glow")) roles.add("cta_emphasis");
  if (mi.includes("shimmer")) roles.add("brand_polish");
  if (mi.includes("count")) roles.add("value_highlight");
  if (mi.includes("loading")) roles.add("loading_feedback");
  if (mi.includes("progress")) roles.add("progress_feedback");
  if (mi.includes("marquee")) roles.add("social_proof");
  if (mi.includes("parallax")) roles.add("brand_polish");
  if (mi.includes("float")) roles.add("delight");
  if (mi.includes("bounce")) roles.add("delight");
  if (mi.includes("magnetic")) roles.add("cta_emphasis");
  if (mi.includes("cursor_follow")) roles.add("delight");

  if (archetypes.includes("CTA")) roles.add("cta_emphasis");
  if (archetypes.includes("TESTIMONIALS")) roles.add("social_proof");
  if (archetypes.includes("TRUST-BADGES")) roles.add("trust_indicator");
  if (archetypes.includes("PRICING")) roles.add("value_highlight");
  if (archetypes.includes("STATS")) roles.add("value_highlight");
  if (archetypes.includes("NEWSLETTER")) roles.add("cta_emphasis");
  if (archetypes.includes("CONTACT")) roles.add("form_interaction");
  if (archetypes.includes("NAV")) roles.add("navigation_aid");
  if (features.formElementCount > 0) roles.add("form_interaction");

  if (roles.size === 0) roles.add("brand_polish");

  return [...roles].filter((r) => taxonomy.conversion_support_roles.includes(r));
}

function detectLayoutContexts(features, archetypes, taxonomy) {
  const contexts = new Set();
  const fn = features.filename.toLowerCase();

  if (archetypes.includes("HERO")) contexts.add("hero");
  if (archetypes.includes("NAV")) contexts.add("nav");
  if (archetypes.includes("FOOTER")) contexts.add("footer");
  if (/card/i.test(fn)) contexts.add("card");
  if (/button/i.test(fn)) contexts.add("button");
  if (/badge/i.test(fn)) contexts.add("badge");
  if (/text|word|char|type/i.test(fn)) contexts.add("text");
  if (/image|img|photo/i.test(fn)) contexts.add("image");
  if (/modal|dialog/i.test(fn)) contexts.add("modal");
  if (/sidebar/i.test(fn)) contexts.add("sidebar");
  if (/overlay/i.test(fn)) contexts.add("overlay");
  if (/toast|notification/i.test(fn)) contexts.add("toast");
  if (/popover|tooltip/i.test(fn)) contexts.add("popover");
  if (/toolbar/i.test(fn)) contexts.add("toolbar");
  if (/form|input/i.test(fn)) contexts.add("form");
  if (/table/i.test(fn)) contexts.add("table");
  if (/background|bg/i.test(fn)) contexts.add("background");
  if (features.isComposable && contexts.size === 0) contexts.add("any");
  if (features.lineCount > 150 && contexts.size === 0) contexts.add("section");
  if (contexts.size === 0) contexts.add("any");

  return [...contexts].filter((c) => taxonomy.layout_contexts.includes(c));
}

function detectInteractionIntents(features, taxonomy) {
  const intents = new Set();
  const fn = features.filename.toLowerCase();

  if (features.triggers.includes("hover")) intents.add("hover");
  if (features.triggers.includes("click")) intents.add("engage");
  if (features.triggers.includes("drag")) intents.add("drag");
  if (features.triggers.includes("focus")) intents.add("focus");
  if (features.triggers.includes("scroll_linked")) intents.add("scroll");
  if (features.formElementCount > 0) intents.add("submit");
  if (/toggle|switch/i.test(fn)) intents.add("toggle");
  if (/accordion|expand|collapse/i.test(fn)) intents.add("expand");
  if (/select|dropdown/i.test(fn)) intents.add("select");
  if (/search/i.test(fn)) intents.add("search");
  if (/sort/i.test(fn)) intents.add("sort");
  if (/filter/i.test(fn)) intents.add("filter");
  if (/upload/i.test(fn)) intents.add("upload");
  if (/copy/i.test(fn)) intents.add("copy");
  if (/share/i.test(fn)) intents.add("share");
  if (/nav|menu|link|breadcrumb/i.test(fn)) intents.add("navigate");
  if (intents.size === 0) intents.add("none");

  return [...intents].filter((i) => taxonomy.interaction_intents.includes(i));
}

function detectAnimationType(features) {
  const mi = features.motionIntents;
  if (mi.includes("loading") || mi.includes("skeleton")) return "loading";
  if (mi.includes("parallax") || mi.includes("progress") || mi.includes("pin") || mi.includes("horizontal_scroll")) return "scroll";
  if (mi.includes("reveal") || mi.includes("entrance") || mi.includes("stagger")) return "entrance";
  if (mi.includes("exit")) return "exit";
  if (mi.includes("shimmer") || mi.includes("typewrite") || mi.includes("scramble") || mi.includes("count")) return "text";
  if (mi.includes("aurora") || mi.includes("perspective") || mi.includes("gradient")) return "background";
  if (mi.includes("float") || mi.includes("pulse") || mi.includes("marquee")) return "continuous";
  if (mi.includes("tilt") || mi.includes("magnetic") || mi.includes("drag") || mi.includes("cursor_follow")) return "interactive";
  if (mi.includes("attention") || mi.includes("scale")) return "hover";
  if (mi.includes("glow") || mi.includes("beam") || mi.includes("spotlight")) return "effect";
  if (features.framerAPIs.layout || features.framerAPIs.layoutGroup) return "layout";
  if (features.triggers.includes("hover")) return "hover";
  if (features.triggers.includes("viewport")) return "entrance";
  if (features.triggers.includes("scroll_linked")) return "scroll";
  return "entrance";
}

function detectSupportedElements(features, code) {
  const elements = new Set();
  const fn = features.filename.toLowerCase();
  if (/text|word|char|type|heading|title/i.test(fn)) elements.add("text");
  if (features.headingCount > 0) elements.add("heading");
  if (/card/i.test(fn) || /card/i.test(code)) elements.add("card");
  if (/button|btn/i.test(fn) || features.buttonCount > 0) elements.add("button");
  if (/image|img|photo/i.test(fn) || features.imageCount > 0) elements.add("image");
  if (/icon|svg/i.test(fn)) elements.add("icon");
  if (/badge/i.test(fn)) elements.add("badge");
  if (/list|item/i.test(fn)) elements.add("list");
  if (/modal|dialog/i.test(fn)) elements.add("modal");
  if (/nav|menu/i.test(fn)) elements.add("nav");
  if (/background|bg/i.test(fn)) elements.add("background");
  if (features.isComposable) elements.add("any");
  if (elements.size === 0) elements.add("any");
  return [...elements];
}

function generateAnimationId(source, slug) {
  const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  return `${norm(source)}__${norm(slug)}`;
}

function analyzePerformanceRisks(features) {
  return {
    layout_shift_risk: (features.modifiesLayout || features.requiresLayoutMeasurement) ? "medium" : "low",
    scroll_coupling_risk: features.triggers.includes("scroll_linked") ? "medium" : "low",
    gpu_accelerated: features.usesTransformOnly || features.usesOpacity,
    mobile_safe: !features.requiresLayoutMeasurement && !features.frameworks.includes("three.js") && features.lineCount < 500,
    motion_stacking_risk: (features.hasStagger && features.hasLooping) ? "medium" : "low",
    accessibility_safe: features.hasReducedMotion || !features.hasLooping,
    reduced_motion_fallback_present: features.hasReducedMotion,
  };
}

function buildRegistryEntry(filePath, code, features, classification, source, slug, externalDeps, libraryRoot, taxonomy) {
  const animationId = generateAnimationId(source, slug);
  const archetypes = mapToArchetypes(features.filename, code);
  const conversionRoles = detectConversionRoles(features, classification, archetypes, taxonomy);
  const layoutContexts = detectLayoutContexts(features, archetypes, taxonomy);
  const interactionIntents = detectInteractionIntents(features, taxonomy);
  const animationType = detectAnimationType(features);
  const supportedElements = detectSupportedElements(features, code);
  const perf = analyzePerformanceRisks(features);
  const relativePath = path.relative(libraryRoot, filePath);

  return {
    animation_id: animationId,
    source_file: relativePath,
    component_type: classification,
    framework: features.frameworks[0] || "none",
    frameworks_all: features.frameworks,
    animation_type: animationType,
    trigger_types: features.triggers,
    supported_elements: supportedElements,
    supported_layout_contexts: layoutContexts,
    section_archetypes: archetypes,
    motion_intents: features.motionIntents,
    interaction_intents: interactionIntents,
    conversion_support_roles: conversionRoles,
    directionality: features.directionality,
    axis: features.axis,
    stagger_support: features.hasStagger,
    interruptible: features.isInterruptible,
    reversible: features.hasReversible,
    composable: features.isComposable,
    looping: features.hasLooping,
    duration_range_ms: features.durationRange,
    easing_profiles: features.easingProfiles,
    requires_layout_measurement: features.requiresLayoutMeasurement,
    causes_layout_shift_risk: perf.layout_shift_risk,
    scroll_coupling_risk: perf.scroll_coupling_risk,
    gpu_accelerated: perf.gpu_accelerated,
    accessibility_safe: perf.accessibility_safe,
    reduced_motion_fallback_present: perf.reduced_motion_fallback_present,
    mobile_safe: perf.mobile_safe,
    motion_stacking_risk: perf.motion_stacking_risk,
    dependencies: externalDeps || features.frameworks.filter((f) => f !== "css" && f !== "none"),
    line_count: features.lineCount,
    has_default_export: features.hasDefaultExport,
    named_exports: features.namedExports,
    keyframe_names: features.keyframeNames,
    example_usage_refs: [],
  };
}

function buildSearchIndex(registry) {
  const index = {
    version: "1.0.0",
    generated: new Date().toISOString(),
    total_entries: registry.length,
    by_intent: {},
    by_section_role: {},
    by_trigger: {},
    by_layout_context: {},
    by_interaction_type: {},
    by_performance_risk: { low: [], medium: [] },
    by_component_type: { animation: [], ui: [], hybrid: [] },
    by_framework: {},
    by_animation_type: {},
  };

  for (const entry of registry) {
    const id = entry.animation_id;
    for (const intent of entry.motion_intents) {
      if (!index.by_intent[intent]) index.by_intent[intent] = [];
      index.by_intent[intent].push(id);
    }
    for (const arch of entry.section_archetypes) {
      if (!index.by_section_role[arch]) index.by_section_role[arch] = [];
      index.by_section_role[arch].push(id);
    }
    for (const trigger of entry.trigger_types) {
      if (!index.by_trigger[trigger]) index.by_trigger[trigger] = [];
      index.by_trigger[trigger].push(id);
    }
    for (const ctx of entry.supported_layout_contexts) {
      if (!index.by_layout_context[ctx]) index.by_layout_context[ctx] = [];
      index.by_layout_context[ctx].push(id);
    }
    for (const intent of entry.interaction_intents) {
      if (!index.by_interaction_type[intent]) index.by_interaction_type[intent] = [];
      index.by_interaction_type[intent].push(id);
    }
    const riskLevel = (entry.causes_layout_shift_risk === "medium" || entry.scroll_coupling_risk === "medium" || entry.motion_stacking_risk === "medium") ? "medium" : "low";
    index.by_performance_risk[riskLevel].push(id);
    index.by_component_type[entry.component_type].push(id);
    for (const fw of entry.frameworks_all) {
      if (!index.by_framework[fw]) index.by_framework[fw] = [];
      index.by_framework[fw].push(id);
    }
    if (!index.by_animation_type[entry.animation_type]) index.by_animation_type[entry.animation_type] = [];
    index.by_animation_type[entry.animation_type].push(id);
  }
  return index;
}

function buildCapabilityMatrixCSV(registry) {
  const headers = [
    "animation_id","component_type","framework","animation_type",
    "viewport_trigger","scroll_linked","hover_trigger","click_trigger",
    "drag_trigger","focus_trigger","mount_trigger","stagger_support",
    "interruptible","reversible","composable","looping","gpu_accelerated",
    "layout_shift_risk","scroll_coupling_risk","motion_stacking_risk",
    "mobile_safe","accessibility_safe","reduced_motion_fallback",
    "requires_layout_measurement","line_count","has_default_export",
    "motion_intents","section_archetypes",
  ];
  const rows = [headers.join(",")];

  for (const entry of registry) {
    const row = [
      entry.animation_id,
      entry.component_type,
      entry.framework,
      entry.animation_type,
      entry.trigger_types.includes("viewport"),
      entry.trigger_types.includes("scroll_linked"),
      entry.trigger_types.includes("hover"),
      entry.trigger_types.includes("click"),
      entry.trigger_types.includes("drag"),
      entry.trigger_types.includes("focus"),
      entry.trigger_types.includes("mount"),
      entry.stagger_support,
      entry.interruptible,
      entry.reversible,
      entry.composable,
      entry.looping,
      entry.gpu_accelerated,
      entry.causes_layout_shift_risk,
      entry.scroll_coupling_risk,
      entry.motion_stacking_risk,
      entry.mobile_safe,
      entry.accessibility_safe,
      entry.reduced_motion_fallback_present,
      entry.requires_layout_measurement,
      entry.line_count,
      entry.has_default_export,
      `"${entry.motion_intents.join(";")}"`,
      `"${entry.section_archetypes.join(";")}"`,
    ];
    rows.push(row.join(","));
  }
  return rows.join("\n");
}

function buildAnalysisLog(entry, features) {
  const lines = [
    `# ${entry.animation_id}`,
    "",
    `**Source:** \`${entry.source_file}\``,
    `**Component Type:** ${entry.component_type}`,
    `**Framework:** ${entry.frameworks_all.join(", ")}`,
    `**Animation Type:** ${entry.animation_type}`,
    `**Line Count:** ${entry.line_count}`,
    "",
    "## Extracted Features",
    "",
    `- **Triggers:** ${entry.trigger_types.join(", ")}`,
    `- **Motion Intents:** ${entry.motion_intents.join(", ")}`,
    `- **Interaction Intents:** ${entry.interaction_intents.join(", ")}`,
    `- **Supported Elements:** ${entry.supported_elements.join(", ")}`,
    `- **Layout Contexts:** ${entry.supported_layout_contexts.join(", ")}`,
    `- **Section Archetypes:** ${entry.section_archetypes.length > 0 ? entry.section_archetypes.join(", ") : "none"}`,
    `- **Directionality:** ${entry.directionality.join(", ")}`,
    `- **Axis:** ${entry.axis.join(", ")}`,
    "",
    "## Capabilities",
    "",
    `- Stagger: ${entry.stagger_support}`,
    `- Interruptible: ${entry.interruptible}`,
    `- Reversible: ${entry.reversible}`,
    `- Composable: ${entry.composable}`,
    `- Looping: ${entry.looping}`,
    `- Duration Range: ${entry.duration_range_ms[0]}ms - ${entry.duration_range_ms[1]}ms`,
    `- Easing: ${entry.easing_profiles.join(", ")}`,
    "",
    "## Performance and Risk",
    "",
    `- GPU Accelerated: ${entry.gpu_accelerated}`,
    `- Layout Shift Risk: ${entry.causes_layout_shift_risk}`,
    `- Scroll Coupling Risk: ${entry.scroll_coupling_risk}`,
    `- Motion Stacking Risk: ${entry.motion_stacking_risk}`,
    `- Mobile Safe: ${entry.mobile_safe}`,
    `- Accessibility Safe: ${entry.accessibility_safe}`,
    `- Reduced Motion Fallback: ${entry.reduced_motion_fallback_present}`,
    `- Requires Layout Measurement: ${entry.requires_layout_measurement}`,
    "",
    "## Classification Rationale",
    "",
  ];

  if (entry.component_type === "animation") {
    lines.push(`Classified as **animation** component. ${features.isComposable ? "Accepts children and wraps them with motion behaviour." : "Provides motion primitives."} ${features.motionElementCount > 0 ? "Uses " + features.motionElementCount + " motion elements." : ""} ${features.hardcodedContentCount < 3 ? "Minimal hardcoded content - reusable across contexts." : ""}`);
  } else if (entry.component_type === "ui") {
    lines.push(`Classified as **UI** component. ${features.hardcodedContentCount > 5 ? "Contains " + features.hardcodedContentCount + " hardcoded content strings." : ""} ${features.shadcnImportCount > 0 ? "Imports " + features.shadcnImportCount + " shadcn/ui components." : ""} ${features.lineCount > 200 ? "Large component (" + features.lineCount + " lines) with structural layout." : ""}`);
  } else {
    lines.push(`Classified as **hybrid** component. Has both significant animation patterns (${features.motionElementCount} motion elements) and UI structure (${features.hardcodedContentCount} content strings, ${features.shadcnImportCount} UI imports).`);
  }

  lines.push("");
  lines.push("## Uncertainty Notes");
  lines.push("");

  const uncertainties = [];
  if (features.frameworks.includes("none")) uncertainties.push("No animation framework detected - classification relies on filename signals only.");
  if (features.shadcnImportCount > 0 && features.motionElementCount > 0) uncertainties.push("Component uses both shadcn/ui imports and motion elements - border case between ui and hybrid.");
  if (!features.hasDefaultExport && features.namedExports.length === 0) uncertainties.push("No clear exports detected - component may not be directly importable.");
  if (features.lineCount > 500) uncertainties.push("Very large file - may contain multiple sub-components. Registry entry covers the primary export only.");

  if (uncertainties.length === 0) {
    lines.push("No significant classification uncertainties.");
  } else {
    uncertainties.forEach((u) => lines.push(`- ${u}`));
  }

  lines.push("");
  lines.push("## Fallback Assumptions");
  lines.push("");
  lines.push(`- Default duration: ${entry.duration_range_ms[0]}ms - ${entry.duration_range_ms[1]}ms (${features.durationRange[0] === 300 && features.durationRange[1] === 800 ? "defaulted - no explicit duration found" : "extracted from code"})`);
  lines.push(`- Default easing: ${entry.easing_profiles.join(", ")} (${features.easingProfiles.length === 1 && features.easingProfiles[0] === "ease-out" ? "defaulted" : "extracted"})`);
  lines.push("");

  return lines.join("\n");
}

module.exports = { buildRegistryEntry, buildSearchIndex, buildCapabilityMatrixCSV, buildAnalysisLog, mapToArchetypes };
