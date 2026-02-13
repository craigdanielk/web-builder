#!/usr/bin/env node
'use strict';

/**
 * build-unified-registry.js
 *
 * Builds a unified component registry (component-registry.json) from:
 * 1. Curated .tsx files in skills/animation-components/ (7 categories)
 * 2. Legacy registry.json (metadata: archetypes, intensity, affinity, etc.)
 * 3. animation_registry.json (cross-validate export names)
 *
 * Output schema includes export_name, export_type, import_statement so the
 * pipeline never generates wrong imports (e.g. gradient-shift → GradientBackground named).
 *
 * Usage: node scripts/quality/build-unified-registry.js
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const SKILLS_ANIM = path.join(ROOT, 'skills', 'animation-components');
const LEGACY_REGISTRY_PATH = path.join(SKILLS_ANIM, 'registry.json');
const FULL_REGISTRY_PATH = path.join(SKILLS_ANIM, 'registry', 'animation_registry.json');
const OUTPUT_PATH = path.join(SKILLS_ANIM, 'component-registry.json');

const CURATED_CATEGORIES = ['entrance', 'scroll', 'interactive', 'continuous', 'text', 'effect', 'background'];

/**
 * Extract default export name from source.
 * Matches: export default function Foo, export default Foo, export default class Foo
 */
function extractDefaultExport(source) {
  const defaultFunc = source.match(/export\s+default\s+function\s+(\w+)/);
  if (defaultFunc) return defaultFunc[1];
  const defaultClass = source.match(/export\s+default\s+class\s+(\w+)/);
  if (defaultClass) return defaultClass[1];
  const defaultIdent = source.match(/export\s+default\s+(\w+)\s*;/);
  if (defaultIdent) return defaultIdent[1];
  return null;
}

/**
 * Extract named export names (first/primary for display).
 * Matches: export function Foo, export const Foo, export { Foo, Bar }
 */
function extractNamedExports(source) {
  const names = [];
  const funcRe = /export\s+function\s+(\w+)/g;
  let m;
  while ((m = funcRe.exec(source)) !== null) names.push(m[1]);
  const constRe = /export\s+const\s+(\w+)\s*=/g;
  while ((m = constRe.exec(source)) !== null) names.push(m[1]);
  const braceRe = /export\s+\{\s*([^}]+)\s*\}/g;
  while ((m = braceRe.exec(source)) !== null) {
    m[1].split(',').forEach(function (part) {
      const name = part.replace(/\s+as\s+.+$/, '').trim().split(/\s/).pop();
      if (name && /^\w+$/.test(name)) names.push(name);
    });
  }
  return names;
}

/**
 * Extract package names from import statements.
 */
function extractDependencies(source) {
  const packages = new Set();
  const re = /import\s+(?:[\w{}\s,*]+)\s+from\s+['"]([^'"]+)['"]/g;
  let m;
  while ((m = re.exec(source)) !== null) {
    const spec = m[1];
    if (spec.startsWith('.') || spec.startsWith('@/')) continue;
    const pkg = spec.split('/')[0];
    if (pkg && pkg !== 'react' && pkg !== 'react-dom') packages.add(pkg);
  }
  return Array.from(packages);
}

/**
 * Determine engine from dependencies: gsap -> gsap; framer-motion or motion -> framer-motion.
 */
function detectEngine(dependencies) {
  if (dependencies.some(function (d) { return d === 'gsap' || d.startsWith('@gsap'); })) return 'gsap';
  if (dependencies.some(function (d) { return d === 'framer-motion' || d === 'motion'; })) return 'framer-motion';
  return null;
}

/**
 * Build export_type and export_name for a component.
 * Prefer default if present; otherwise use first named export.
 */
function getExportInfo(source, fullRegistryEntry) {
  const defaultName = extractDefaultExport(source);
  const namedNames = extractNamedExports(source);
  if (defaultName) {
    return { export_type: 'default', export_name: defaultName };
  }
  if (namedNames.length > 0) {
    return { export_type: 'named', export_name: namedNames[0] };
  }
  if (fullRegistryEntry) {
    if (fullRegistryEntry.has_default_export && fullRegistryEntry.named_exports && fullRegistryEntry.named_exports[0]) {
      return { export_type: 'default', export_name: fullRegistryEntry.named_exports[0] };
    }
    if (fullRegistryEntry.named_exports && fullRegistryEntry.named_exports[0]) {
      return { export_type: 'named', export_name: fullRegistryEntry.named_exports[0] };
    }
  }
  return { export_type: 'default', export_name: 'Component' };
}

/**
 * Generate import statement. Stem = filename without .tsx (no category in path).
 */
function buildImportStatement(stem, exportType, exportName) {
  const base = "@/components/animations/" + stem;
  if (exportType === 'named') {
    return "import { " + exportName + " } from '" + base + "'";
  }
  return "import " + exportName + " from '" + base + "'";
}

function main() {
  let legacy = { components: {} };
  if (fs.existsSync(LEGACY_REGISTRY_PATH)) {
    legacy = JSON.parse(fs.readFileSync(LEGACY_REGISTRY_PATH, 'utf8'));
  }

  let fullRegistryByFile = {};
  if (fs.existsSync(FULL_REGISTRY_PATH)) {
    const full = JSON.parse(fs.readFileSync(FULL_REGISTRY_PATH, 'utf8'));
    const list = full.components || [];
    list.forEach(function (entry) {
      const sf = entry.source_file;
      if (sf) fullRegistryByFile[sf] = entry;
    });
  }

  const components = {};
  let legacyKeys = Object.keys(legacy.components || {});

  // When legacy registry is missing (e.g. after migration), discover from filesystem
  if (legacyKeys.length === 0) {
    CURATED_CATEGORIES.forEach(function (cat) {
      const dir = path.join(SKILLS_ANIM, cat);
      if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return;
      const files = fs.readdirSync(dir).filter(function (f) { return f.endsWith('.tsx'); });
      files.forEach(function (f) {
        const stem = f.replace(/\.tsx$/, '');
        legacyKeys.push(stem);
        legacy.components[stem] = { file: cat + '/' + f, category: cat };
      });
    });
    legacyKeys = Object.keys(legacy.components || {});
  }

  legacyKeys.forEach(function (stem) {
    const meta = legacy.components[stem] || {};
    const relativePath = meta.file || (meta.category ? meta.category + '/' + stem + '.tsx' : stem + '.tsx');
    const fullPath = path.join(SKILLS_ANIM, relativePath);
    const source = fs.existsSync(fullPath) ? fs.readFileSync(fullPath, 'utf8') : '';
    const fullEntry = fullRegistryByFile[relativePath];

    const deps = source ? extractDependencies(source) : (meta.dependencies || []);
    const engine = source ? (detectEngine(deps) || meta.engine) : (meta.engine || 'framer-motion');
    const { export_type: exportType, export_name: exportName } = source
      ? getExportInfo(source, fullEntry)
      : (fullEntry
        ? getExportInfo('', fullEntry)
        : { export_type: 'default', export_name: stem.split('-').map(function (w) { return w.charAt(0).toUpperCase() + w.slice(1); }).join('') });

    const importStatement = buildImportStatement(stem, exportType, exportName);
    const lineCount = source ? source.split(/\n/).length : 0;

    components[stem] = {
      source_file: relativePath,
      export_name: exportName,
      export_type: exportType,
      import_statement: importStatement,
      dependencies: deps.length ? deps : (meta.dependencies || []),
      engine: engine,
      category: meta.category || path.dirname(relativePath),
      archetypes: meta.archetypes || [],
      intensity: meta.intensity || 'moderate',
      affinity: meta.affinity || {},
      description: meta.description || '',
      status: meta.status || 'ready',
      line_count: lineCount,
    };
    if (meta.props) components[stem].props = meta.props;
    if (meta.defaultProps) components[stem].defaultProps = meta.defaultProps;
    if (meta.source) components[stem].source = meta.source;
  });

  const out = {
    version: '2.0.0',
    generated_at: new Date().toISOString(),
    component_count: Object.keys(components).length,
    components,
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(out, null, 2), 'utf8');
  console.log('Wrote ' + OUTPUT_PATH + ' with ' + out.component_count + ' components.');
}

main();
