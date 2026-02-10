/**
 * registry-utils.js
 *
 * File discovery and quality validation utilities for the animation registry.
 */

const fs = require("fs");
const path = require("path");

function discoverCuratedComponents(libraryRoot, categories) {
  const files = [];
  for (const category of categories) {
    const dir = path.join(libraryRoot, category);
    if (!fs.existsSync(dir)) continue;
    for (const file of fs.readdirSync(dir)) {
      if (file.endsWith(".tsx")) {
        files.push({
          path: path.join(dir, file),
          source: category,
          slug: file.replace(".tsx", ""),
          origin: "curated",
        });
      }
    }
  }
  return files;
}

function discover21stDevComponents(lib21st, fullRegistryPath) {
  const files = [];
  if (!fs.existsSync(lib21st)) return files;

  let externalRegistry = {};
  if (fs.existsSync(fullRegistryPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(fullRegistryPath, "utf-8"));
      externalRegistry = data.components || {};
    } catch (e) {
      console.warn("Warning: Could not parse registry-full.json:", e.message);
    }
  }

  const authors = fs.readdirSync(lib21st);
  for (const author of authors) {
    const authorDir = path.join(lib21st, author);
    let stat;
    try {
      stat = fs.statSync(authorDir);
    } catch (_e) {
      continue;
    }
    if (!stat.isDirectory()) continue;

    const componentFiles = fs.readdirSync(authorDir);
    for (const file of componentFiles) {
      if (!file.endsWith(".tsx")) continue;
      const slug = file.replace(".tsx", "");
      const registryKey = `${author}/${slug}`;
      const deps = externalRegistry[registryKey]
        ? externalRegistry[registryKey].dependencies || []
        : [];

      files.push({
        path: path.join(authorDir, file),
        source: author,
        slug,
        origin: "21st-dev",
        externalDeps: deps,
      });
    }
  }
  return files;
}

function validateRegistry(registry, taxonomy, libraryRoot) {
  const issues = [];
  const idSet = new Set();

  for (const entry of registry) {
    // Unique ID check
    if (idSet.has(entry.animation_id)) {
      issues.push("DUPLICATE ID: " + entry.animation_id);
    }
    idSet.add(entry.animation_id);

    // File exists check
    const fullPath = path.join(libraryRoot, entry.source_file);
    if (!fs.existsSync(fullPath)) {
      issues.push("MISSING FILE: " + entry.source_file);
    }

    // Taxonomy compliance
    for (const intent of entry.motion_intents) {
      if (!taxonomy.motion_intents.includes(intent))
        issues.push("INVALID MOTION INTENT: " + intent + " in " + entry.animation_id);
    }
    for (const intent of entry.interaction_intents) {
      if (!taxonomy.interaction_intents.includes(intent))
        issues.push("INVALID INTERACTION INTENT: " + intent + " in " + entry.animation_id);
    }
    for (const role of entry.conversion_support_roles) {
      if (!taxonomy.conversion_support_roles.includes(role))
        issues.push("INVALID CONVERSION ROLE: " + role + " in " + entry.animation_id);
    }
    for (const ctx of entry.supported_layout_contexts) {
      if (!taxonomy.layout_contexts.includes(ctx))
        issues.push("INVALID LAYOUT CONTEXT: " + ctx + " in " + entry.animation_id);
    }
    for (const trigger of entry.trigger_types) {
      if (!taxonomy.trigger_types.includes(trigger))
        issues.push("INVALID TRIGGER: " + trigger + " in " + entry.animation_id);
    }
  }

  return issues;
}

module.exports = { discoverCuratedComponents, discover21stDevComponents, validateRegistry };
