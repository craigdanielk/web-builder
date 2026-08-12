'use strict';

/**
 * Inject a REAL animation-library component into an already-built section.
 *
 * Contrast with animation-apply.js (`applyAnimation`): that rewrites the
 * section's own root `<section>` into a `<motion.section>` using an inline
 * variant string — no file changes, no import, no library code involved.
 * This module is different in kind: it resolves a registry row to an actual
 * `.tsx` file on disk, copies that file into the build, and imports + wraps
 * the section's existing root element with the component's own code. The
 * section's content and its existing inner `<motion.*>` animations are left
 * byte-identical; only an import line and a wrapping pair of tags are added.
 *
 * Refuses rather than guesses at every step: unresolvable animation_id,
 * missing source file, no verified export in the unified component-registry,
 * a props shape that can't be satisfied without invented values, an inline
 * root tag that would produce invalid nesting, an ambiguous or already-
 * wrapped section — every one of these returns `injected:false` with a
 * `reason` string and the input untouched.
 */

const fs = require('fs');
const path = require('path');
const { deriveComponentIntensity } = require('./animation-injector');

const COMPONENTS_DIR = path.resolve(__dirname, '../../../skills/animation-components');
const INTENSITY_RANK = { subtle: 1, moderate: 2, expressive: 3, dramatic: 4 };
const FULL_REGISTRY_PATH = path.join(COMPONENTS_DIR, 'registry/animation_registry.json');
const UNIFIED_REGISTRY_PATH = path.join(COMPONENTS_DIR, 'component-registry.json');

let _fullRegistryCache = null;
let _unifiedRegistryCache = null;
let _unifiedBySourceFile = null;

function loadFullRegistry() {
  if (_fullRegistryCache) return _fullRegistryCache;
  try {
    const raw = fs.readFileSync(FULL_REGISTRY_PATH, 'utf8');
    const data = JSON.parse(raw);
    _fullRegistryCache = Array.isArray(data.components) ? data.components : [];
  } catch (err) {
    _fullRegistryCache = [];
  }
  return _fullRegistryCache;
}

function loadUnifiedRegistry() {
  if (_unifiedRegistryCache) return _unifiedRegistryCache;
  try {
    const raw = fs.readFileSync(UNIFIED_REGISTRY_PATH, 'utf8');
    const data = JSON.parse(raw);
    _unifiedRegistryCache = data.components || {};
  } catch (err) {
    _unifiedRegistryCache = {};
  }
  _unifiedBySourceFile = {};
  for (const key of Object.keys(_unifiedRegistryCache)) {
    const comp = _unifiedRegistryCache[key];
    if (comp && comp.source_file) {
      _unifiedBySourceFile[comp.source_file] = Object.assign({ key }, comp);
    }
  }
  return _unifiedRegistryCache;
}

function unifiedBySourceFile(sourceFile) {
  if (!_unifiedBySourceFile) loadUnifiedRegistry();
  return _unifiedBySourceFile[sourceFile] || null;
}

/**
 * Roles are the top-level directory names under skills/animation-components/
 * (entrance, scroll, interactive, continuous, text, effect, background).
 * The brief is explicit: archetype affinity in the full registry reaches
 * only 2 of 12 real sections (5 rows declare section_archetypes at all).
 * Role reaches all 12 because every backed component has a role by
 * construction (its directory). This is a *candidate order*, not a filter —
 * every role is tried as a fallback so a section is never starved by a
 * mapping gap.
 */
const ROLE_BY_ARCHETYPE = {
  HERO: ['entrance', 'text'],
  FEATURES: ['entrance', 'interactive'],
  'PRODUCT-SHOWCASE': ['entrance', 'interactive'],
  STATS: ['continuous'],
  ABOUT: ['entrance', 'background'],
  'HOW-IT-WORKS': ['scroll', 'entrance'],
  TESTIMONIALS: ['entrance', 'interactive'],
  CTA: ['entrance', 'effect'],
  GALLERY: ['scroll', 'interactive'],
  TEAM: ['entrance', 'interactive'],
  CONTACT: ['entrance'],
  'LOGO-BAR': ['continuous'],
  PRICING: ['entrance', 'interactive'],
  FAQ: ['interactive', 'entrance'],
  NEWSLETTER: ['entrance'],
  'TRUST-BADGES': ['entrance'],
};
const ALL_ROLES = ['entrance', 'interactive', 'scroll', 'continuous', 'text', 'effect', 'background'];

function roleOrderForArchetype(archetype) {
  const preferred = ROLE_BY_ARCHETYPE[String(archetype || '').toUpperCase()] || [];
  const rest = ALL_ROLES.filter((r) => preferred.indexOf(r) === -1);
  return preferred.concat(rest);
}

// ---------------------------------------------------------------------------
// Resolution
// ---------------------------------------------------------------------------

/**
 * Resolve an animation_id to its backing file + verified export metadata.
 * The full registry's `.components` is an ARRAY — this looks up by the
 * `animation_id` field, never by object key.
 */
function resolveComponent(animationId) {
  const registry = loadFullRegistry();
  const row = registry.find((c) => c.animation_id === animationId);
  if (!row) {
    return { ok: false, reason: `no registry row for animation_id '${animationId}'` };
  }
  if (!row.source_file) {
    return { ok: false, reason: `registry row '${animationId}' has no source_file` };
  }
  const absPath = path.join(COMPONENTS_DIR, row.source_file);
  if (!fs.existsSync(absPath)) {
    return { ok: false, reason: `source_file '${row.source_file}' does not exist on disk` };
  }
  const unified = unifiedBySourceFile(row.source_file);
  if (!unified) {
    return {
      ok: false,
      reason: `'${row.source_file}' has no verified export mapping in component-registry.json — refusing to guess an import`,
    };
  }
  const role = row.source_file.split('/')[0];
  return {
    ok: true,
    animationId,
    sourceFile: row.source_file,
    absPath,
    role,
    exportName: unified.export_name,
    exportType: unified.export_type, // 'default' | 'named'
    dependencies: row.dependencies || unified.dependencies || [],
    destName: path.basename(row.source_file, '.tsx'),
  };
}

// ---------------------------------------------------------------------------
// Safety analysis — can this component safely wrap arbitrary section content?
// ---------------------------------------------------------------------------

const INLINE_ROOT_TAGS = new Set(['span', 'a', 'button', 'label', 'input', 'p']);

/** Strip // and /* *‍/ comments so they can't be mistaken for code. */
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '))
    .replace(/\/\/[^\n]*/g, (m) => m.replace(/[^\n]/g, ' '));
}

/**
 * Split a type/interface body on top-level commas, semicolons, AND newlines.
 * TS interfaces are commonly written with no trailing delimiter at all
 * (relying on ASI), one field per line — newline has to count as a
 * separator too, or every field after the first silently vanishes into the
 * "type" of the first field. Splitting only ever happens at brace/paren/
 * bracket depth 0, so a multi-line nested type (`variants?: { container?:
 * Variants; ... }`) is not affected.
 */
function splitTopLevelFields(body) {
  const parts = [];
  let depth = 0;
  let cur = '';
  for (let i = 0; i < body.length; i++) {
    const ch = body[i];
    if ('{(['.indexOf(ch) !== -1) depth++;
    if ('})]'.indexOf(ch) !== -1) depth--;
    if (depth === 0 && (ch === ',' || ch === ';' || ch === '\n')) {
      if (cur.trim()) parts.push(cur.trim());
      cur = '';
    } else {
      cur += ch;
    }
  }
  if (cur.trim()) parts.push(cur.trim());
  return parts;
}

/**
 * Find `type <Name>Props = { ... }` or `interface <Name>Props { ... }` and
 * return its raw body (the intersected trailing object literal when the type
 * is `React.ComponentProps<'div'> & { ... }`). Also handles the inline
 * destructure-typed-parameter form some library files use instead of a named
 * props type: `function X({ a, b }: { a: string; b?: number }) {`.
 */
function findPropsBody(source, exportName) {
  const named = new RegExp(
    '(?:interface|type)\\s+' + exportName + 'Props\\s*(?:=)?\\s*(?:[^{]*&\\s*)?\\{'
  );
  let m = named.exec(source);
  if (m) {
    const start = m.index + m[0].length;
    return extractBalancedBody(source, start);
  }

  // Inline destructured parameter type on the export itself.
  const inline = new RegExp(
    '(?:export\\s+)?(?:default\\s+)?function\\s+' + exportName + '\\s*\\(\\s*\\{[^)]*\\}\\s*:\\s*\\{'
  );
  m = inline.exec(source);
  if (m) {
    const start = m.index + m[0].length;
    return extractBalancedBody(source, start);
  }

  return null;
}

function extractBalancedBody(source, openBraceIndex) {
  let depth = 1;
  let i = openBraceIndex;
  while (i < source.length && depth > 0) {
    if (source[i] === '{') depth++;
    else if (source[i] === '}') depth--;
    i++;
  }
  if (depth !== 0) return null;
  return source.slice(openBraceIndex, i - 1);
}

/** Find the destructured parameter list of the exported function/const, to read default values. */
function findParamDefaults(source, exportName) {
  const patterns = [
    new RegExp('(?:export\\s+)?(?:default\\s+)?function\\s+' + exportName + '\\s*\\(\\s*\\{'),
    new RegExp('(?:export\\s+)?const\\s+' + exportName + '\\s*=\\s*\\(?\\s*\\{'),
  ];
  let m = null;
  for (const re of patterns) {
    m = re.exec(source);
    if (m) break;
  }
  if (!m) return {};
  const openIdx = m.index + m[0].length - 1; // index of the destructure's `{`
  const body = extractBalancedBody(source, openIdx + 1);
  if (body === null) return {};
  const defaults = {};
  for (const field of splitTopLevelFields(body)) {
    const eq = field.indexOf('=');
    if (eq === -1) continue;
    const name = field.slice(0, eq).trim();
    defaults[name] = true;
  }
  return defaults;
}

/** Locate the exported component's return-JSX root tag, e.g. 'div', 'motion.span'. */
function findRootTag(source, exportName) {
  const patterns = [
    new RegExp('(?:export\\s+)?(?:default\\s+)?function\\s+' + exportName + '\\s*\\('),
    new RegExp('(?:export\\s+)?const\\s+' + exportName + '\\s*='),
  ];
  let start = -1;
  for (const re of patterns) {
    const m = re.exec(source);
    if (m) {
      start = m.index;
      break;
    }
  }
  if (start === -1) return null;
  const region = source.slice(start, start + 4000); // component bodies are short
  const m = /return\s*\(?\s*<([A-Za-z][\w.]*)/.exec(region);
  return m ? m[1] : null;
}

/**
 * Decide whether a component can safely wrap arbitrary JSX children.
 * Returns { safe: true } or { safe: false, reason }.
 */
function analyzeSafety(sourceRaw, exportName) {
  const source = stripComments(sourceRaw);

  const propsBody = findPropsBody(source, exportName);
  if (propsBody === null) {
    return { safe: false, reason: `could not locate a props type for '${exportName}' — refusing to guess its shape` };
  }

  const fields = splitTopLevelFields(propsBody);
  const defaults = findParamDefaults(source, exportName);

  let childrenField = null;
  const unsatisfied = [];

  for (const field of fields) {
    const colonIdx = field.indexOf(':');
    if (colonIdx === -1) continue;
    let rawName = field.slice(0, colonIdx).trim();
    const optional = rawName.endsWith('?');
    const name = optional ? rawName.slice(0, -1).trim() : rawName;
    const type = field.slice(colonIdx + 1).trim();

    if (name === 'children') {
      childrenField = { optional, type };
      continue;
    }

    const hasDefault = !!defaults[name];
    if (!optional && !hasDefault) {
      unsatisfied.push(name);
    }
  }

  if (!childrenField) {
    return { safe: false, reason: `'${exportName}' has no children prop — nothing to wrap the section with` };
  }
  if (!/ReactNode|React\.ReactNode/.test(childrenField.type)) {
    return {
      safe: false,
      reason: `'${exportName}' types children as '${childrenField.type}', not ReactNode — cannot wrap JSX`,
    };
  }
  if (unsatisfied.length > 0) {
    return {
      safe: false,
      reason: `'${exportName}' requires prop(s) [${unsatisfied.join(', ')}] with no default — cannot satisfy without inventing values`,
    };
  }

  const rootTag = findRootTag(source, exportName);
  if (!rootTag) {
    return { safe: false, reason: `could not locate '${exportName}'’s returned root element` };
  }
  const bareTag = rootTag.split('.').pop().toLowerCase();
  if (INLINE_ROOT_TAGS.has(bareTag)) {
    return {
      safe: false,
      reason: `'${exportName}' renders an inline/interactive root <${bareTag}> — wrapping a block-level <section> in it would be invalid nesting`,
    };
  }

  return { safe: true };
}

// ---------------------------------------------------------------------------
// Insertion point + wrap
// ---------------------------------------------------------------------------

function maskNonCode(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  while (i < n) {
    const c = src[i];
    const c2 = i + 1 < n ? src[i + 1] : '';
    if (c === '/' && c2 === '/') {
      let j = i;
      while (j < n && src[j] !== '\n') { out += ' '; j++; }
      i = j;
      continue;
    }
    if (c === '/' && c2 === '*') {
      let j = i;
      out += '  ';
      j += 2;
      while (j < n && !(src[j] === '*' && src[j + 1] === '/')) { out += src[j] === '\n' ? '\n' : ' '; j++; }
      if (j < n) { out += '  '; j += 2; }
      i = j;
      continue;
    }
    if (c === "'" || c === '"' || c === '`') {
      const quote = c;
      let j = i + 1;
      out += ' ';
      while (j < n && src[j] !== quote) {
        if (src[j] === '\\' && j + 1 < n) {
          out += src[j] === '\n' ? '\n' : ' ';
          out += src[j + 1] === '\n' ? '\n' : ' ';
          j += 2;
          continue;
        }
        out += src[j] === '\n' ? '\n' : ' ';
        j++;
      }
      if (j < n) { out += ' '; j++; }
      i = j;
      continue;
    }
    out += c;
    i++;
  }
  return out;
}

function findRootSectionSpans(maskedText) {
  const re = /<section\b([^>]*?)(\/)?>|<\/section>/g;
  const spans = [];
  let depth = 0;
  let openStart = null;
  let openAttrs = null;
  let m;
  while ((m = re.exec(maskedText))) {
    const isClose = m[0] === '</section>';
    if (isClose) {
      depth--;
      if (depth < 0) return null;
      if (depth === 0 && openStart !== null) {
        spans.push({ start: openStart, end: re.lastIndex, selfClosing: false, attrs: openAttrs });
        openStart = null;
        openAttrs = null;
      }
      continue;
    }
    const selfClosing = m[2] === '/';
    if (depth === 0) {
      if (selfClosing) {
        spans.push({ start: m.index, end: re.lastIndex, selfClosing: true, attrs: m[1] });
      } else {
        openStart = m.index;
        openAttrs = m[1];
        depth++;
      }
    } else if (!selfClosing) {
      depth++;
    }
  }
  if (depth !== 0) return null;
  return spans;
}

/**
 * Find the single root `<section>...</section>` returned by the file's
 * `export default function`. Mirrors applyAnimation's discipline: any
 * ambiguity (no default export, no root section, multiple roots, unbalanced
 * tags, self-closing root, root not directly returned) is a refusal.
 */
function findInsertionPoint(tsx) {
  const defaultFnMatch = /export\s+default\s+function\s+\w+\s*\([^)]*\)\s*\{/.exec(tsx);
  if (!defaultFnMatch) {
    return { ok: false, reason: 'no export default function found' };
  }
  const regionStart = defaultFnMatch.index;
  // Bound the scan to the default export function's OWN body — brace-match
  // from the `{` that opens it to its matching `}`. Without this, a helper
  // function declared after the default export (a real shape: see
  // 06-faq.tsx's `FAQItem` sibling) would leak into the scan and its own
  // `<section>`, if any, could be mistaken for a second root, or worse, a
  // section-shaped return further down the file could get silently chosen.
  const maskedFull = maskNonCode(tsx);
  const bodyOpen = defaultFnMatch.index + defaultFnMatch[0].length - 1; // index of the `{`
  let depth = 1;
  let i = bodyOpen + 1;
  while (i < maskedFull.length && depth > 0) {
    if (maskedFull[i] === '{') depth++;
    else if (maskedFull[i] === '}') depth--;
    i++;
  }
  if (depth !== 0) {
    return { ok: false, reason: 'default export function body never closes — unbalanced braces' };
  }
  const region = tsx.slice(regionStart, i);
  const masked = maskedFull.slice(regionStart, i);

  const spans = findRootSectionSpans(masked);
  if (spans === null) {
    return { ok: false, reason: 'unbalanced <section> tags — refusing rather than guessing' };
  }
  if (spans.length === 0) {
    return { ok: false, reason: 'no root <section> element found in default export' };
  }
  if (spans.length > 1) {
    return { ok: false, reason: `${spans.length} sibling root <section> elements found — refusing rather than guessing which is the root` };
  }
  const root = spans[0];
  if (root.selfClosing) {
    return { ok: false, reason: 'root is a self-closing <section /> — no body to wrap' };
  }

  const before = region.slice(0, root.start).replace(/\s+$/, '');
  if (!/return\s*\($/.test(before)) {
    return { ok: false, reason: 'root <section> is not directly returned — no safe insertion point' };
  }

  return { ok: true, start: regionStart + root.start, end: regionStart + root.end };
}

/**
 * Wrap the section's root element with the given component. Adds an import
 * line and a pair of wrapping tags; the section body between them (including
 * its own inner <motion.*> animations) is copied through untouched.
 */
function wrapWithComponent(tsx, resolved) {
  const importPath = `@/components/animations/${resolved.destName}`;
  const importLine =
    resolved.exportType === 'default'
      ? `import ${resolved.exportName} from '${importPath}';`
      : `import { ${resolved.exportName} } from '${importPath}';`;

  if (tsx.includes(importPath)) {
    return { ok: false, reason: `section already imports '${importPath}' — refusing to wrap twice` };
  }

  const point = findInsertionPoint(tsx);
  if (!point.ok) return point;

  const inner = tsx.slice(point.start, point.end);
  const wrapped = `<${resolved.exportName}>\n${inner}\n</${resolved.exportName}>`;
  let out = tsx.slice(0, point.start) + wrapped + tsx.slice(point.end);

  if (/^'use client';/m.test(out)) {
    out = out.replace(/^'use client';\s*/m, `'use client';\n\n${importLine}\n`);
  } else {
    out = `${importLine}\n${out}`;
  }

  return { ok: true, tsx: out };
}

// ---------------------------------------------------------------------------
// Selection — role-first, file-existence-backed, safety-filtered.
// ---------------------------------------------------------------------------

/**
 * Pick the first unused, on-disk, framer-motion, safely-wrappable component
 * for a section's archetype, trying its preferred roles before falling back
 * across all roles. Returns a resolved component (see resolveComponent) or
 * null if nothing qualifies.
 */
function selectComponentForSection(archetype, usedAnimationIds, presetIntensity) {
  const registry = loadFullRegistry();
  const roles = roleOrderForArchetype(archetype);
  const used = new Set(usedAnimationIds || []);
  const presetRank = INTENSITY_RANK[presetIntensity] || INTENSITY_RANK.moderate;

  for (const role of roles) {
    const candidates = registry.filter((c) => {
      if (!c.source_file || c.source_file.split('/')[0] !== role) return false;
      const engine = c.framework || c.engine || '';
      if (engine !== 'framer-motion') return false;
      if (used.has(c.animation_id)) return false;
      // Ceiling, not a target: a component's own intensity may never exceed
      // the tenant preset's explicit `animation_intensity` field. Cape
      // Crypto's is `moderate` per Craig's ruling — deliberately set, not
      // inherited from how animated the source site happened to be.
      const compRank = INTENSITY_RANK[deriveComponentIntensity(c)] || INTENSITY_RANK.moderate;
      if (compRank > presetRank) return false;
      return true;
    });

    for (const cand of candidates) {
      const resolved = resolveComponent(cand.animation_id);
      if (!resolved.ok) continue;
      let source;
      try {
        source = fs.readFileSync(resolved.absPath, 'utf8');
      } catch (err) {
        continue;
      }
      const safety = analyzeSafety(source, resolved.exportName);
      if (safety.safe) {
        return resolved;
      }
    }
  }
  return null;
}

/**
 * Attempt injection for one section. `tsx` is the current file content,
 * `archetype` its SectionArtifact archetype, `usedAnimationIds` the set
 * already consumed elsewhere in this build (deduplication).
 */
function injectIntoSection(tsx, archetype, usedAnimationIds, presetIntensity) {
  const resolved = selectComponentForSection(archetype, usedAnimationIds, presetIntensity);
  if (!resolved) {
    return { injected: false, reason: 'no backed component for role', component: null, tsx };
  }

  const result = wrapWithComponent(tsx, resolved);
  if (!result.ok) {
    return { injected: false, reason: result.reason, component: null, tsx };
  }

  return {
    injected: true,
    reason: `wrapped with ${resolved.animationId}`,
    component: resolved,
    tsx: result.tsx,
  };
}

module.exports = {
  loadFullRegistry,
  loadUnifiedRegistry,
  resolveComponent,
  analyzeSafety,
  findInsertionPoint,
  wrapWithComponent,
  selectComponentForSection,
  injectIntoSection,
  roleOrderForArchetype,
  ROLE_BY_ARCHETYPE,
  ALL_ROLES,
};
