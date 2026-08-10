"use strict";

const fs = require("fs");
const path = require("path");

// ---------------------------------------------------------------------------
// Patterns
// ---------------------------------------------------------------------------

/** Matches opening markdown code fences: ```tsx, ```typescript, ```jsx, etc. */
const CODE_FENCE_OPEN =
  /^```(?:tsx|typescript|jsx|javascript|ts|js|react)?\s*\n?/;

/** Matches a closing code fence at the end of the string. */
const CODE_FENCE_CLOSE = /\n?```\s*$/;

/**
 * Tokens whose presence means the component requires "use client".
 * We check for both import-style references and direct usage.
 */
const CLIENT_MARKERS = [
  "framer-motion",
  "motion.",
  "useState",
  "useEffect",
  "useRef",
  "useCallback",
  "useMemo",
];

// ---------------------------------------------------------------------------
// cleanComponent
// ---------------------------------------------------------------------------

/**
 * Takes raw Claude output and cleans it into a valid .tsx file.
 *
 * 1. Strips markdown code fences if present.
 * 2. Trims whitespace.
 * 3. Detects if "use client" is needed and prepends it when missing.
 * 4. Ensures a default export exists.
 *
 * @param {string} rawCode  – The raw text produced by the LLM.
 * @param {string} componentName – PascalCase component name (e.g. "HeroSection").
 * @returns {string} Cleaned source code.
 */
function cleanComponent(rawCode, componentName) {
  if (!rawCode || typeof rawCode !== "string") {
    throw new Error("cleanComponent: rawCode must be a non-empty string");
  }
  if (!componentName || typeof componentName !== "string") {
    throw new Error(
      "cleanComponent: componentName must be a non-empty string"
    );
  }

  let code = rawCode;

  // 1. Strip markdown code fences ------------------------------------------------
  code = code.replace(CODE_FENCE_OPEN, "");
  code = code.replace(CODE_FENCE_CLOSE, "");

  // 2. Trim whitespace -----------------------------------------------------------
  code = code.trim();

  // 3. Detect & prepend "use client" if needed -----------------------------------
  const needsClient = CLIENT_MARKERS.some((marker) => code.includes(marker));
  const hasUseClient =
    code.startsWith('"use client"') || code.startsWith("'use client'");

  if (needsClient && !hasUseClient) {
    code = `"use client";\n\n${code}`;
  }

  // 4. Ensure default export exists ----------------------------------------------
  if (!hasDefaultExport(code)) {
    // Try to convert a matching named export:
    //   export function ComponentName  →  export default function ComponentName
    //   export const ComponentName     →  export default ... (tricky, just append)
    const namedFnExport = new RegExp(
      `export\\s+function\\s+${escapeRegExp(componentName)}\\b`
    );
    const namedConstExport = new RegExp(
      `export\\s+const\\s+${escapeRegExp(componentName)}\\b`
    );

    if (namedFnExport.test(code)) {
      code = code.replace(
        namedFnExport,
        `export default function ${componentName}`
      );
    } else if (namedConstExport.test(code)) {
      // Convert `export const Foo` → `const Foo` and append default export
      code = code.replace(namedConstExport, `const ${componentName}`);
      code += `\n\nexport default ${componentName};\n`;
    } else {
      // Last resort — append a bare default export
      code += `\n\nexport default ${componentName};\n`;
    }
  }

  return code;
}

// ---------------------------------------------------------------------------
// validateComponent
// ---------------------------------------------------------------------------

/**
 * Static validation of a component source string (no execution).
 *
 * @param {string} code – The cleaned component source.
 * @param {string} componentName – Expected component name.
 * @returns {{ valid: boolean, warnings: string[], errors: string[] }}
 */
function validateComponent(code, componentName) {
  const warnings = [];
  const errors = [];

  if (!code || typeof code !== "string") {
    errors.push("Component code is empty or not a string.");
    return { valid: false, warnings, errors };
  }

  // 1. Default export check ------------------------------------------------------
  if (!hasDefaultExport(code)) {
    errors.push("Missing default export.");
  }

  // 2. "use client" check --------------------------------------------------------
  const needsClient = CLIENT_MARKERS.some((marker) => code.includes(marker));
  const hasClient =
    code.includes('"use client"') || code.includes("'use client'");

  if (needsClient && !hasClient) {
    errors.push(
      '"use client" directive is required (hooks or framer-motion detected) but missing.'
    );
  }

  // 3a. Rough JSX bracket balance ------------------------------------------------
  //     We only count < and > outside of string literals and comments for a
  //     basic sanity check. This is intentionally imprecise — a full parse
  //     would require a real parser. We strip generic type annotations as best
  //     we can and just flag large imbalances.
  const strippedCode = stripStringsAndComments(code);
  const opens = (strippedCode.match(/</g) || []).length;
  const closes = (strippedCode.match(/>/g) || []).length;

  if (Math.abs(opens - closes) > 2) {
    warnings.push(
      `Potential unmatched JSX brackets: ${opens} opening "<" vs ${closes} closing ">".`
    );
  }

  // 3b. Missing React import -----------------------------------------------------
  const hasJSX = /<[A-Z]/.test(code) || /<[a-z][a-z]/.test(code);
  const hasReactImport =
    /import\s+React/.test(code) || /from\s+['"]react['"]/.test(code);

  if (hasJSX && !hasReactImport && !hasClient) {
    warnings.push(
      'File uses JSX but has no React import and no "use client" directive. ' +
        "This may fail in environments that don't auto-inject React."
    );
  }

  // 3c. Empty component ----------------------------------------------------------
  // Strip imports, comments, and directive to estimate real code length
  const realCode = code
    .replace(/^"use client";\s*/m, "")
    .replace(/^import\s+.*$/gm, "")
    .replace(/\/\/.*$/gm, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .trim();

  if (realCode.length < 50) {
    warnings.push(
      `Component appears nearly empty (${realCode.length} chars of non-import code).`
    );
  }

  // 3d. GSAP engine usage audit ----------------------------------------------------
  // If component imports GSAP, it should actually use gsap. calls, not just import.
  const importsGSAP = /from\s+['"]gsap['"]/.test(code) || /require\s*\(\s*['"]gsap['"]/.test(code);
  const usesGSAP = /gsap\.\w+\(/.test(code);
  const importsFramerMotion = /from\s+['"]framer-motion['"]/.test(code);
  const usesWhileInView = /whileInView/.test(code);

  if (importsGSAP && !usesGSAP) {
    warnings.push(
      "Imports GSAP but never calls gsap.*() — the import is dead code."
    );
  }

  if (importsGSAP && importsFramerMotion && usesWhileInView && !usesGSAP) {
    warnings.push(
      "GSAP engine section uses only Framer Motion whileInView for entrances. " +
        "Should use GSAP ScrollTrigger for entrances when engine is GSAP."
    );
  }

  // 3e. Plugin registration check --------------------------------------------------
  // If the code uses a GSAP plugin (SplitText, Flip, DrawSVG, etc.) it must
  // call gsap.registerPlugin() for it.
  const GSAP_PLUGINS = ["SplitText", "Flip", "DrawSVG", "MorphSVG", "MotionPath",
    "Draggable", "Observer", "ScrambleText", "CustomEase"];
  for (const plugin of GSAP_PLUGINS) {
    const pluginUsed = new RegExp(`\\b${plugin}\\b`).test(code);
    const pluginImported = new RegExp(`from\\s+['"]gsap/${plugin}['"]`).test(code);
    const pluginRegistered = new RegExp(`registerPlugin\\([^)]*${plugin}`).test(code);
    if (pluginUsed && !pluginImported) {
      warnings.push(
        `Uses ${plugin} but does not import it from "gsap/${plugin}".`
      );
    }
    if (pluginImported && !pluginRegistered) {
      warnings.push(
        `Imports ${plugin} but does not register it with gsap.registerPlugin(${plugin}).`
      );
    }
  }

  // 3f. Animation component library import check ------------------------------------
  // If the section uses @/components/animations/, check the import is well-formed
  const animImports = code.match(/@\/components\/animations\/[\w-]+/g) || [];
  if (animImports.length > 0) {
    for (const imp of animImports) {
      const componentName = imp.split('/').pop();
      if (!componentName || componentName.length < 3) {
        warnings.push(`Suspicious animation component import: ${imp}`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    warnings,
    errors,
  };
}

// ---------------------------------------------------------------------------
// processAllSections
// ---------------------------------------------------------------------------

/**
 * Scan a directory for .tsx files, run cleanComponent + validateComponent on
 * each, overwrite if changes were made, and return a summary.
 *
 * @param {string} sectionsDir – Absolute path to the sections directory.
 * @returns {Promise<{ processed: number, modified: number, issues: Array<{file: string, errors: string[], warnings: string[]}> }>}
 */
async function processAllSections(sectionsDir) {
  if (!fs.existsSync(sectionsDir)) {
    throw new Error(`processAllSections: directory not found: ${sectionsDir}`);
  }

  const files = fs
    .readdirSync(sectionsDir)
    .filter((f) => f.endsWith(".tsx"))
    .sort();

  const summary = {
    processed: 0,
    modified: 0,
    issues: [],
  };

  for (const file of files) {
    const filePath = path.join(sectionsDir, file);
    const originalCode = fs.readFileSync(filePath, "utf-8");

    // Derive component name from filename:
    //   "03-about.tsx" → "About"
    //   "07-testimonials.tsx" → "Testimonials"
    const baseName = path.basename(file, ".tsx"); // "03-about"
    const nameWithoutNumber = baseName.replace(/^\d+-/, ""); // "about"
    const componentName = nameWithoutNumber
      .split(/[-_]/)
      .map((seg) => seg.charAt(0).toUpperCase() + seg.slice(1))
      .join("");

    // Clean -----------------------------------------------------------------
    let cleaned;
    try {
      cleaned = cleanComponent(originalCode, componentName);
    } catch (err) {
      summary.issues.push({
        file,
        errors: [`cleanComponent failed: ${err.message}`],
        warnings: [],
      });
      summary.processed++;
      continue;
    }

    // Validate --------------------------------------------------------------
    const result = validateComponent(cleaned, componentName);

    if (result.errors.length > 0 || result.warnings.length > 0) {
      summary.issues.push({
        file,
        errors: result.errors,
        warnings: result.warnings,
      });
    }

    // Write back if modified ------------------------------------------------
    if (cleaned !== originalCode) {
      fs.writeFileSync(filePath, cleaned, "utf-8");
      summary.modified++;
    }

    summary.processed++;
  }

  return summary;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true if the code contains a default export.
 * Checks for:
 *   - export default function
 *   - export default class
 *   - export default ComponentName
 *   - export { ... as default }
 */
function hasDefaultExport(code) {
  return (
    /export\s+default\s+/.test(code) ||
    /export\s*\{[^}]*\bas\s+default\b[^}]*\}/.test(code)
  );
}

/** Escape a string for use in a RegExp constructor. */
function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Strip string literals and comments to aid bracket counting.
 *
 * Single-pass scanner rather than chained regexes. The chained-regex version
 * removed `//` line comments FIRST, which meant any `https://` inside a string
 * literal (extremely common in generated sections: hrefs, image srcs) was read
 * as a comment start and the remainder of the line — including its closing
 * quote and any `}` — was deleted. That inflated the open-brace count and made
 * `detectAndRepairTruncation()` append phantom `}` to perfectly valid files.
 * Scanning left-to-right with an explicit state machine makes string context
 * win over comment detection, which is the correct precedence.
 */
function stripStringsAndComments(code) {
  let out = "";
  let i = 0;
  const n = code.length;

  while (i < n) {
    const ch = code[i];
    const next = code[i + 1];

    // Line comment
    if (ch === "/" && next === "/") {
      while (i < n && code[i] !== "\n") i++;
      continue;
    }

    // Block comment
    if (ch === "/" && next === "*") {
      i += 2;
      while (i < n && !(code[i] === "*" && code[i + 1] === "/")) i++;
      i += 2;
      continue;
    }

    // String / template literal — consume to the matching (unescaped) quote.
    if (ch === '"' || ch === "'" || ch === "`") {
      const quote = ch;
      out += quote + quote; // collapse to an empty literal
      i++;
      while (i < n) {
        if (code[i] === "\\") {
          i += 2;
          continue;
        }
        if (code[i] === quote) {
          i++;
          break;
        }
        i++;
      }
      continue;
    }

    out += ch;
    i++;
  }

  return out;
}

// ---------------------------------------------------------------------------
// JSX scanning (generics-aware)
// ---------------------------------------------------------------------------

/** Characters that can end an identifier immediately before a `<`. */
const IDENT_CHAR = /[A-Za-z0-9_$]/;

/** Characters valid inside a JSX tag name (incl. `Foo.Bar` and `data-x` style). */
const TAG_NAME_CHAR = /[A-Za-z0-9_.$-]/;

/**
 * Characters that cannot legally appear inside a JSX opening tag at brace
 * depth 0. Hitting one means the `<` we started from was an operator, not a
 * tag — e.g. `a < b && c > d`, `count < items.length`.
 */
const NOT_IN_TAG = new Set([";", "<", "&", "|", "?", ",", "(", ")", "[", "]", "+", "*", "%", "!"]);

/**
 * Walk stripped source and match JSX tags with a stack.
 *
 * This replaces the old "count `<Tag` occurrences and subtract closers"
 * arithmetic, which could not tell a JSX element from a TypeScript type
 * argument. `useRef<HTMLDivElement>(null)`, `useState<Item[]>([])`,
 * `Array<{...}>` and `React.FC<Props>` all survive stripStringsAndComments()
 * and each registered as an unmatched opening tag; three of them in one file
 * was enough to make the repairer append literal `</HTMLDivElement>` to an
 * already-valid file.
 *
 * Disambiguation uses two signals together:
 *
 *  1. Adjacency — a `<` glued directly to an identifier character (or `)` /
 *     `]`) is a type-argument list. JSX in *expression* position always opens
 *     after `(`, `{`, `return`, `=>`, `,` or whitespace, so its `<` is never
 *     preceded by part of an identifier. `foo<Bar>` is a generic.
 *  2. Context — adjacency alone is not enough, because JSX *children* are text
 *     and text ends in letters: `Balance</span>` and `Hello<br />` both put an
 *     identifier character immediately before a `<` that is genuinely a tag.
 *     So adjacency is only read as a generic at stack depth 0, i.e. in
 *     expression position. Inside an open element every `<` is a tag.
 *
 * Closing tags (`</`) and fragments (`<>`) are never type arguments and are
 * checked before the adjacency rule at all.
 *
 * @param {string} stripped – Source with strings and comments removed.
 * @returns {{ unclosed: string[], mismatched: number, generics: number, opened: number }}
 */
function scanJsxStack(stripped) {
  const stack = [];
  let mismatched = 0;
  let generics = 0;
  let opened = 0;
  const n = stripped.length;
  let i = 0;

  while (i < n) {
    if (stripped[i] !== "<") {
      i++;
      continue;
    }

    const prev = i > 0 ? stripped[i - 1] : "";
    const next = stripped[i + 1];

    // Fragment: <>  (never a type argument — `Foo<>` is not valid TS)
    if (next === ">" && stripped[i + 2] !== "=") {
      stack.push("");
      opened++;
      i += 2;
      continue;
    }

    // TypeScript type argument list, not a JSX element. Only in expression
    // position (stack empty) — inside an element, `<` after text is a tag.
    if (
      next !== "/" &&
      stack.length === 0 &&
      (IDENT_CHAR.test(prev) || prev === ")" || prev === "]")
    ) {
      generics++;
      i++;
      continue;
    }

    // Closing tag: </Name>
    if (next === "/") {
      let j = i + 2;
      let name = "";
      while (j < n && TAG_NAME_CHAR.test(stripped[j])) name += stripped[j++];
      while (j < n && /\s/.test(stripped[j])) j++;
      if (stripped[j] !== ">") {
        i++;
        continue;
      }
      if (stack.length && stack[stack.length - 1] === name) {
        stack.pop();
      } else {
        const at = stack.lastIndexOf(name);
        if (at > -1) stack.length = at; // close through an unclosed nesting
        mismatched++;
      }
      i = j + 1;
      continue;
    }

    if (!next || !/[A-Za-z]/.test(next)) {
      i++;
      continue;
    }

    // Candidate opening tag ------------------------------------------------
    let j = i + 1;
    let name = "";
    while (j < n && TAG_NAME_CHAR.test(stripped[j])) name += stripped[j++];
    // A real tag name is followed by whitespace, `/` or `>`.
    if (j < n && !/[\s/>]/.test(stripped[j])) {
      i++;
      continue;
    }

    let depth = 0;
    let end = -1;
    let selfClosing = false;
    let k = j;
    while (k < n) {
      const c = stripped[k];
      if (c === "{") { depth++; k++; continue; }
      if (c === "}") { depth--; k++; continue; }
      if (depth > 0) { k++; continue; }
      if (NOT_IN_TAG.has(c)) break;                       // operator, not a tag
      if (c === ">") {
        if (stripped[k - 1] === "=" || stripped[k + 1] === "=") break; // `=>`, `>=`
        selfClosing = stripped[k - 1] === "/";
        end = k;
        break;
      }
      k++;
    }

    if (end === -1) {
      // Unterminated tag (truncated mid-attribute) or a `<` operator. Either
      // way there is nothing reliable to push; skip it.
      i++;
      continue;
    }

    opened++;
    if (!selfClosing) stack.push(name);
    i = end + 1;
  }

  return { unclosed: stack, mismatched, generics, opened };
}

const DELIM_CLOSERS = { "(": ")", "[": "]", "{": "}" };

/**
 * Stack-scan `(`, `[`, `{` over stripped source.
 *
 * The unclosed openers, in the order they were opened, tell the repairer the
 * exact closers a truncated file needs and in which order — which a bare
 * `openBraces - closeBraces` count cannot, since it loses paren/bracket
 * nesting entirely and emits `}` where `)` was needed.
 *
 * @returns {{ expected: string[], overClosed: number }}
 */
function scanDelimiters(stripped) {
  const stack = [];
  let overClosed = 0;
  for (let i = 0; i < stripped.length; i++) {
    const c = stripped[i];
    if (DELIM_CLOSERS[c]) {
      stack.push(DELIM_CLOSERS[c]);
    } else if (c === ")" || c === "]" || c === "}") {
      if (stack.length && stack[stack.length - 1] === c) stack.pop();
      else overClosed++;
    }
  }
  return { expected: stack, overClosed };
}

/**
 * Measure the structural balance of a source file.
 *
 * Every axis is "lower is better". `score` is the aggregate used to decide
 * whether a repair candidate is strictly better than its input.
 */
function measureStructure(code) {
  const stripped = stripStringsAndComments(code);
  const jsx = scanJsxStack(stripped);
  const delims = scanDelimiters(stripped);

  const braceDelta =
    (stripped.match(/\{/g) || []).length - (stripped.match(/\}/g) || []).length;
  const parenDelta =
    (stripped.match(/\(/g) || []).length - (stripped.match(/\)/g) || []).length;

  const hasExport = hasDefaultExport(code);

  const nonEmptyLines = code.split(/\n/).filter((l) => l.trim().length > 0);
  const lastLine = nonEmptyLines.length
    ? nonEmptyLines[nonEmptyLines.length - 1].trim()
    : "";
  const endsProperly =
    /export\s+default\s+.+;?\s*$/.test(lastLine) ||
    /}\s*;\s*$/.test(lastLine) ||
    /}\s*$/.test(lastLine);

  const m = {
    braceImbalance: Math.abs(braceDelta),
    braceDelta,
    parenImbalance: Math.abs(parenDelta),
    parenDelta,
    unclosedTags: jsx.unclosed.slice(),
    unclosedCount: jsx.unclosed.length,
    mismatchedTags: jsx.mismatched,
    genericsIgnored: jsx.generics,
    expectedClosers: delims.expected.slice(),
    overClosedDelims: delims.overClosed,
    // A markdown fence surviving into the source means stripStringsAndComments
    // reads its backticks as a template literal and swallows the rest of the
    // file — every count below becomes meaningless. Tracked so the repairer
    // can refuse to act on numbers it cannot trust.
    codeFences: (code.match(/```/g) || []).length,
    hasExport,
    endsProperly,
  };

  m.score =
    m.braceImbalance +
    m.parenImbalance +
    m.unclosedCount +
    m.mismatchedTags * 2 +
    m.overClosedDelims * 2 +
    (m.hasExport ? 0 : 1) +
    (m.endsProperly ? 0 : 1);

  return m;
}

/** Per-axis comparison — a candidate may not regress ANY axis. */
function regressesAnyAxis(before, after) {
  return (
    after.braceImbalance > before.braceImbalance ||
    after.parenImbalance > before.parenImbalance ||
    after.unclosedCount > before.unclosedCount ||
    after.mismatchedTags > before.mismatchedTags ||
    after.overClosedDelims > before.overClosedDelims ||
    (before.hasExport && !after.hasExport) ||
    (before.endsProperly && !after.endsProperly)
  );
}

/** Public metrics view (no internal-only fields). */
function publicMetrics(m) {
  return {
    score: m.score,
    braceImbalance: m.braceImbalance,
    parenImbalance: m.parenImbalance,
    unclosedTags: m.unclosedCount,
    mismatchedTags: m.mismatchedTags,
    genericsIgnored: m.genericsIgnored,
    unclosedDelimiters: m.expectedClosers.length,
    overClosedDelimiters: m.overClosedDelims,
    codeFences: m.codeFences,
    hasExport: m.hasExport,
    endsProperly: m.endsProperly,
  };
}

// ---------------------------------------------------------------------------
// detectAndRepairTruncation
// ---------------------------------------------------------------------------

/**
 * Detect truncation (e.g. from token limit) and attempt a *proven* repair.
 *
 * Detection triggers on the three signals that a truncated file cannot fake:
 * a missing `export default`, unbalanced braces, or a last line that does not
 * terminate a block. JSX tag imbalance is measured and reported but is NOT a
 * trigger on its own — a file whose braces balance, which ends on `}` and
 * carries a default export cannot have been cut off mid-JSX, so a lone JSX
 * skew there is a measurement artefact, not truncation. That is the class of
 * false positive that was appending `</HTMLDivElement>` to valid files.
 *
 * Repair contract (mirrors scripts/quality/render-fix-contrast.js):
 *   measure input -> build candidate -> re-measure candidate -> keep ONLY if
 *   the candidate scores strictly better AND regresses no individual axis.
 *   Otherwise the input is returned byte-identical with `reverted: true`.
 * A repair that cannot be proven to improve the file is never returned.
 *
 * @param {string} code – Section component source.
 * @param {string} sectionName – Section identifier for warnings (e.g. "03-about").
 * @returns {{ truncated: boolean, repaired: boolean, code: string, warnings: string[],
 *             reverted: boolean, applied: number, before: object|null, after: object|null }}
 */
function detectAndRepairTruncation(code, sectionName) {
  const warnings = [];

  if (!code || typeof code !== "string") {
    return {
      truncated: true,
      repaired: false,
      code,
      warnings: ["Code is empty or not a string."],
      reverted: false,
      applied: 0,
      before: null,
      after: null,
    };
  }

  // --- Measure -----------------------------------------------------------
  const before = measureStructure(code);

  const truncated =
    before.codeFences > 0 ||
    !before.hasExport ||
    before.braceDelta !== 0 ||
    before.expectedClosers.length > 0 ||
    before.overClosedDelims > 0 ||
    !before.endsProperly;

  if (!truncated) {
    if (before.unclosedCount > 0 || before.mismatchedTags > 0) {
      warnings.push(
        `Section ${sectionName}: JSX tag skew observed (${before.unclosedCount} unclosed, ` +
          `${before.mismatchedTags} mismatched) but braces, export and file ending are all ` +
          `intact — treated as a measurement artefact, not truncation. No repair attempted.`
      );
    }
    return {
      truncated: false,
      repaired: false,
      code,
      warnings,
      reverted: false,
      applied: 0,
      before: publicMetrics(before),
      after: publicMetrics(before),
    };
  }

  // A stray markdown fence poisons every measurement (its backticks open a
  // template literal that swallows the rest of the file), so nothing here can
  // be proven. Flag it and refuse to touch the file.
  if (before.codeFences > 0) {
    warnings.push(
      `Section ${sectionName} contains ${before.codeFences} markdown code fence(s) — ` +
        `structural measurement is unreliable and no repair was attempted. ` +
        `Strip the fence or regenerate the section.`
    );
    return {
      truncated: true,
      repaired: false,
      code,
      warnings,
      reverted: false,
      applied: 0,
      before: publicMetrics(before),
      after: publicMetrics(before),
    };
  }

  // --- Build candidate ---------------------------------------------------
  // Append in the order a truncated file actually needs closing: innermost
  // JSX first, then the enclosing braces, then the export statement.
  let candidate = code.trimEnd();
  let applied = 0;

  if (before.unclosedCount > 0) {
    const closers = before.unclosedTags
      .slice()
      .reverse()
      .map((name) => (name === "" ? "</>" : `</${name}>`))
      .join("");
    candidate += closers;
    applied += before.unclosedCount;
  }

  if (before.expectedClosers.length > 0) {
    // Reverse order: innermost delimiter closes first. Using the scanned stack
    // rather than a brace count is what emits `)` where a `return (` is open
    // instead of blindly appending `}`.
    candidate += "\n" + before.expectedClosers.slice().reverse().join("");
    applied += before.expectedClosers.length;
  }

  if (!before.hasExport) {
    const fnMatch = code.match(/(?:export\s+)?function\s+([A-Z][a-zA-Z0-9]*)\s*[(\s]/);
    const constMatch = code.match(/(?:export\s+)?const\s+([A-Z][a-zA-Z0-9]*)\s*[=:]/);
    const componentName = fnMatch ? fnMatch[1] : constMatch ? constMatch[1] : null;
    if (componentName) {
      candidate += `\n\nexport default ${componentName};\n`;
      applied += 1;
    } else {
      warnings.push(
        `Section ${sectionName} has no default export and no component name could be inferred.`
      );
    }
  }

  if (applied === 0 || candidate === code) {
    warnings.push(
      `Section ${sectionName} looks truncated but no repair could be constructed — left unchanged.`
    );
    return {
      truncated: true,
      repaired: false,
      code,
      warnings,
      reverted: false,
      applied: 0,
      before: publicMetrics(before),
      after: publicMetrics(before),
    };
  }

  // --- Re-measure and guard ----------------------------------------------
  const after = measureStructure(candidate);
  const improved = after.score < before.score && !regressesAnyAxis(before, after);

  if (!improved) {
    warnings.push(
      `Section ${sectionName}: repair candidate REVERTED — it did not measurably improve ` +
        `structural balance (score ${before.score} -> ${after.score}). File left byte-identical; ` +
        `regenerate the section instead.`
    );
    return {
      truncated: true,
      repaired: false,
      code, // byte-identical input
      warnings,
      reverted: true,
      applied: 0,
      before: publicMetrics(before),
      after: publicMetrics(after),
    };
  }

  if (after.score > 0) {
    warnings.push(
      `Section ${sectionName} was repaired but is still not fully balanced ` +
        `(residual score ${after.score}) — consider regenerating.`
    );
  }
  if (candidate.length - code.length > 50) {
    warnings.push(
      `Section ${sectionName} was heavily repaired — consider regenerating`
    );
  }

  return {
    truncated: true,
    repaired: true,
    code: candidate,
    warnings,
    reverted: false,
    applied,
    before: publicMetrics(before),
    after: publicMetrics(after),
  };
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  cleanComponent,
  validateComponent,
  processAllSections,
  detectAndRepairTruncation,
  // Exposed for testing / diagnostics — not used by orchestrate.py.
  stripStringsAndComments,
  scanJsxStack,
  measureStructure,
};
