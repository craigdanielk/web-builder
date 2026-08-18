'use strict';

/**
 * Decide, per section, which REAL animation-library component (if any) may
 * wrap it — and hand that decision to ASSEMBLY, not to a rewrite of the
 * section's own source.
 *
 * PIVOT (superseding an earlier version of this file): the first draft of
 * this module located an insertion point inside each section's own .tsx by
 * string-scanning for its root `<section>...</section>` — the same
 * approach `animation-apply.js`'s `applyAnimation` used. That approach
 * failed three review rounds there (mismatched sibling-section tag pairing,
 * apostrophes in harvested client copy confusing the scanner, JSX
 * expressions like `{a > b ? 1 : 0}` mistaken for tag boundaries) and was
 * retired from the pipeline entirely. Any hand-rolled parser walking
 * arbitrary generated JSX inherits that same bug class — patching it again
 * was not the fix, avoiding the class of bug was.
 *
 * This module now decides ONLY; it never touches a section file. The page
 * assembler (`_build_page_imports` in orchestrate.py) generates uniform,
 * fully-controlled code — `<ComponentName><SectionNN /></ComponentName>` —
 * so there is no foreign JSX to parse, no root-tag ambiguity, no comment or
 * string-literal confusion, and nothing to corrupt. Section .tsx files are
 * guaranteed byte-identical because nothing here ever opens one for writing.
 *
 * Refusal is still real, just narrower in scope: unresolvable animation_id,
 * missing source file, no verified export in the unified component-registry,
 * a props shape that can't be satisfied without invented values, or an
 * inline/interactive root tag on the WRAPPING component itself (wrapping a
 * block-level section in a `<span>` or `<button>` is invalid nesting
 * regardless of where the wrap happens) — every one of these is a refusal
 * with a `reason`, never a guess.
 */

const fs = require('fs');
const path = require('path');
const { deriveComponentIntensity } = require('./animation-injector');

const COMPONENTS_DIR = path.resolve(__dirname, '../../../skills/animation-components');
const INTENSITY_RANK = { subtle: 1, moderate: 2, expressive: 3, dramatic: 4 };
const FULL_REGISTRY_PATH = path.join(COMPONENTS_DIR, 'registry/animation_registry.json');
const LIBRARY_REGISTRY_PATH = path.join(COMPONENTS_DIR, 'registry/animation_library.json');
const UNIFIED_REGISTRY_PATH = path.join(COMPONENTS_DIR, 'component-registry.json');

let _fullRegistryCache = null;
let _libraryRegistryCache = null;
let _unifiedRegistryCache = null;
let _unifiedBySourceFile = null;
let _poolCache = {};

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

/**
 * The LIBRARY — the rows whose component file exists on disk.
 *
 * `animation_registry.json` is a CATALOGUE, not an inventory: 986 of its 1034
 * rows name files under `21st-dev-library/`, a tree that is absent from this
 * filesystem entirely, so those rows cannot be read, copied or safety-analysed
 * and could never be injected. Selection reads only this file. The 986 are not
 * deleted and not silently dropped — `registry/animation_wishlist.json`
 * records every one of them with the `os.path.exists` sweep that established
 * it, and library + wish-list sum back to the catalogue.
 *
 * Both files are produced by `registry/annotate_backed_rows.py`, whose defining
 * property is that re-running it reproduces them byte for byte.
 *
 * There is no fallback to the catalogue on a read failure. Falling back would
 * put 986 unbacked rows into selection precisely when the split is broken —
 * exactly the state the split exists to make impossible.
 */
function loadBackedLibrary() {
  if (_libraryRegistryCache) return _libraryRegistryCache;
  try {
    const data = JSON.parse(fs.readFileSync(LIBRARY_REGISTRY_PATH, 'utf8'));
    _libraryRegistryCache = Array.isArray(data.components) ? data.components : [];
  } catch (err) {
    _libraryRegistryCache = [];
  }
  return _libraryRegistryCache;
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
  // `continuous` stays first — a logo strip's native motion is a marquee.
  // But the marquee in the library takes `logos: ReactNode[]`, so it is a
  // content-level insert, not a section wrapper, and the wrap model cannot
  // reach it. `entrance` is declared as the honest second preference rather
  // than left to the blanket fallback, where a logo bar served by an
  // entrance component read as a mapping failure instead of a design choice.
  'LOGO-BAR': ['continuous', 'entrance'],
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

/**
 * Engines whose runtime the build can actually install.
 *
 * This filter used to be `engine !== 'framer-motion'`, which was a proxy for
 * "we know we can install this" written when nothing populated per-component
 * `dependencies`. It is now the wrong question: orchestrate.py resolves each
 * injected component's npm packages from the registry row
 * (`animation-injection-deps.json` -> package.json, orchestrate.py:7433-7459),
 * and `registry/annotate_backed_rows.py` derives those packages by parsing the
 * file's real imports. So the honest gate is engine-can-be-installed plus
 * analyzeSafety(), not a single hardcoded framework name.
 *
 * The census measured what that one string cost: 22 of the 48 file-backed
 * components survived it, and 15 gsap + 9 dependency-free ones were discarded
 * without ever being asked whether they were safe. Four of them are wrappers
 * that pass every safety check (DrawSVGReveal, FlipExpandCard, ObserverSwipe,
 * BorderBeam).
 *
 * `three.js` stays out: its one file-backed row (text__text_scramble) is a
 * misdescribed GLSL shader canvas, and a ~600KB WebGL runtime is not something
 * to pull into a page as a section wrapper.
 */
const SUPPORTED_ENGINES = new Set(['framer-motion', 'gsap', 'css', 'none', '']);

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
  // A render-prop signature like `children: (state) => ReactNode` contains
  // the substring "ReactNode" and would pass a bare regex test for it, but
  // it is a FUNCTION type, not a value type — the component calls
  // `children(state)`, so passing a JSX element as children breaks at the
  // call site. Reject any function-shaped children type before checking for
  // ReactNode at all: `=>` never appears in a plain (possibly unioned)
  // ReactNode type, only in a function type.
  if (/=>/.test(childrenField.type)) {
    return {
      safe: false,
      reason: `'${exportName}' types children as a render-prop function ('${childrenField.type}') — cannot pass a JSX element where a function is expected`,
    };
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
// Selection — role-first, file-existence-backed, safety-filtered.
// ---------------------------------------------------------------------------

/** Import path a generated page file uses to reach a copied library component. */
function importPathFor(resolved) {
  return `@/components/animations/${resolved.destName}`;
}

/** The exact import statement (default vs named export) for a resolved component. */
function importStatementFor(resolved) {
  const importPath = importPathFor(resolved);
  return resolved.exportType === 'default'
    ? `import ${resolved.exportName} from "${importPath}";`
    : `import { ${resolved.exportName} } from "${importPath}";`;
}

/**
 * Dedupe by FILE, not by animation_id. Two ids can point at one component:
 * entrance__fade_up_stagger and entrance__staggered_timeline are the same
 * byte-identical AnimatedGroup, and before this the homepage received both
 * — reported as two distinct components in animation-coverage.json while
 * rendering the same animation twice. `duplicate_of` is written by
 * registry/annotate_backed_rows.py from a sha256 of the file.
 */
function canonicalKey(row) {
  return (row && (row.duplicate_of || row.animation_id)) || null;
}

/**
 * The registry filters that do not depend on what a build has already used:
 * role directory, id-describes-file adjudication, installable engine, and the
 * intensity ceiling. Shared by selection and by pool measurement so the two
 * can never drift — the pool a ceiling admits is measured with exactly the
 * predicate selection applies.
 */
function rowAdmissible(c, presetRank, role) {
  if (!c.source_file) return false;
  if (role && c.source_file.split('/')[0] !== role) return false;
  // A row whose animation_id does not describe its file is never a
  // candidate, whatever its role says. `interactive__accordion_expand`
  // is a hardcoded FAQ section carrying placeholder body copy; injecting
  // it would put invented content on a licensed FSP's site. Adjudicated
  // per row in registry/annotate_backed_rows.py with the evidence.
  if (c.id_describes_file === false) return false;
  const engine = c.framework || c.engine || '';
  if (!SUPPORTED_ENGINES.has(engine)) return false;
  // Ceiling, not a target: a component's own intensity may never exceed
  // the tenant preset's explicit `animation_intensity` field. Cape
  // Crypto's is `moderate` per Craig's ruling — deliberately set, not
  // inherited from how animated the source site happened to be.
  const compRank = INTENSITY_RANK[deriveComponentIntensity(c)] || INTENSITY_RANK.moderate;
  if (compRank > presetRank) return false;
  return true;
}

/**
 * Every component a given intensity CEILING admits, ignoring deduplication —
 * i.e. the supply a build configured at this intensity could ever draw on.
 *
 * This exists so an empty result from selectComponentForSection() can be told
 * apart from a library that has nothing. `deriveComponentIntensity` returns
 * `subtle` only for an entrance/exit under 300ms with all three risks low, and
 * no backed component satisfies that, so a preset declaring
 * `animation_intensity: subtle` draws from a pool of ZERO. That is a
 * configuration ceiling, not a supply failure, and reporting it as
 * "no backed component for role" has made a settable field look like a missing
 * library. Measured 2026-08-18: subtle 0 · moderate 7 · expressive 7 ·
 * dramatic 17, out of 48 file-backed rows.
 *
 * Cached per intensity: the safety pass reads every backed file from disk.
 */
function componentPoolForIntensity(presetIntensity) {
  const key = String(presetIntensity == null ? '' : presetIntensity);
  if (Object.prototype.hasOwnProperty.call(_poolCache, key)) return _poolCache[key];
  const registry = loadBackedLibrary();
  const presetRank = INTENSITY_RANK[presetIntensity] || INTENSITY_RANK.moderate;
  const seen = new Set();
  const pool = [];
  for (const c of registry) {
    if (!rowAdmissible(c, presetRank, null)) continue;
    const ck = canonicalKey(c);
    if (ck && seen.has(ck)) continue;
    const resolved = resolveComponent(c.animation_id);
    if (!resolved.ok) continue;
    let source;
    try {
      source = fs.readFileSync(resolved.absPath, 'utf8');
    } catch (err) {
      continue;
    }
    if (!analyzeSafety(source, resolved.exportName).safe) continue;
    if (ck) seen.add(ck);
    pool.push(resolved);
  }
  _poolCache[key] = pool;
  return pool;
}

/** Rows whose `source_file` exists on disk — the real, re-derivable supply. */
function backedRowCount() {
  return loadBackedLibrary().length;
}

/**
 * Pick the first unused, on-disk, framer-motion, safely-wrappable component
 * for a section's archetype, trying its preferred roles before falling back
 * across all roles. Returns a resolved component (see resolveComponent) or
 * null if nothing qualifies.
 */
function selectComponentForSection(archetype, usedAnimationIds, presetIntensity) {
  // The LIBRARY, never the catalogue: an unbacked row can never be a candidate.
  const registry = loadBackedLibrary();
  const roles = roleOrderForArchetype(archetype);
  const used = new Set(usedAnimationIds || []);
  const presetRank = INTENSITY_RANK[presetIntensity] || INTENSITY_RANK.moderate;

  const usedComponents = new Set();
  for (const id of used) {
    const row = registry.find((c) => c.animation_id === id);
    const key = canonicalKey(row);
    if (key) usedComponents.add(key);
  }

  for (const role of roles) {
    const candidates = registry.filter((c) => {
      if (!rowAdmissible(c, presetRank, role)) return false;
      if (used.has(c.animation_id)) return false;
      if (usedComponents.has(canonicalKey(c))) return false;
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
 * Decide whether a section should be wrapped, and with what. This makes NO
 * changes to any file — it returns a decision for the caller (orchestrate.py)
 * to persist and for assembly to act on when it generates the page.
 *
 * `archetype` is the section's SectionArtifact archetype, `usedAnimationIds`
 * the set already consumed elsewhere in this build (deduplication),
 * `presetIntensity` the tenant preset's explicit `animation_intensity`.
 *
 * Three states, never two:
 *   selected      — a real component was chosen
 *   not_measured  — the configured intensity ceiling admits a pool of ZERO, so
 *                   nothing was ever compared; this is a configuration
 *                   outcome and says nothing about the library's supply
 *   no_supply     — the ceiling admits a non-empty pool, and still nothing in
 *                   it fit this role / survived dedupe. That, and only that,
 *                   is a supply statement.
 * `status` is the machine-readable form; `reason` carries the same verdict in
 * prose for the by_reason tally that orchestrate.py writes to
 * animation-coverage.json.
 */
function decideComponentForSection(archetype, usedAnimationIds, presetIntensity) {
  const resolved = selectComponentForSection(archetype, usedAnimationIds, presetIntensity);
  const ceiling = String(presetIntensity == null ? '' : presetIntensity);
  if (!resolved) {
    const pool = componentPoolForIntensity(presetIntensity);
    if (pool.length === 0) {
      return {
        injected: false,
        status: 'not_measured',
        intensity_ceiling: ceiling,
        pool_size: 0,
        reason:
          `NOT_MEASURED: animation_intensity ceiling '${ceiling}' admits 0 of ` +
          `${backedRowCount()} file-backed components — no pool to select from, ` +
          `so supply was never tested`,
        component: null,
      };
    }
    return {
      injected: false,
      status: 'no_supply',
      intensity_ceiling: ceiling,
      pool_size: pool.length,
      reason:
        `no backed component for role (ceiling '${ceiling}' admits a pool of ` +
        `${pool.length}; none fit this role or all were already used)`,
      component: null,
    };
  }
  return {
    injected: true,
    status: 'selected',
    intensity_ceiling: ceiling,
    reason: `selected ${resolved.animationId}`,
    component: resolved,
  };
}

module.exports = {
  loadFullRegistry,
  loadBackedLibrary,
  loadUnifiedRegistry,
  resolveComponent,
  analyzeSafety,
  importPathFor,
  importStatementFor,
  selectComponentForSection,
  decideComponentForSection,
  componentPoolForIntensity,
  backedRowCount,
  roleOrderForArchetype,
  ROLE_BY_ARCHETYPE,
  ALL_ROLES,
};
