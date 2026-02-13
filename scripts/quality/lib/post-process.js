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
 * Very rough strip of string literals and comments to aid bracket counting.
 * Not meant to be a parser — just good enough for a sanity heuristic.
 */
function stripStringsAndComments(code) {
  return code
    .replace(/\/\/.*$/gm, "") // single-line comments
    .replace(/\/\*[\s\S]*?\*\//g, "") // block comments
    .replace(/"(?:[^"\\]|\\.)*"/g, '""') // double-quoted strings
    .replace(/'(?:[^'\\]|\\.)*'/g, "''") // single-quoted strings
    .replace(/`(?:[^`\\]|\\.)*`/g, "``"); // template literals (simplified)
}

// ---------------------------------------------------------------------------
// detectAndRepairTruncation
// ---------------------------------------------------------------------------

/**
 * Detect truncation (e.g. from token limit) and attempt repair.
 *
 * Detection: has export default; JSX open/close tags and self-closing roughly
 * balanced; braces { } equal; last non-empty line ends with export default or }; or }
 *
 * Repair: add missing export default; add missing }; add rough JSX closing tags.
 *
 * @param {string} code – Section component source.
 * @param {string} sectionName – Section identifier for warnings (e.g. "03-about").
 * @returns {{ truncated: boolean, repaired: boolean, code: string, warnings: string[] }}
 */
function detectAndRepairTruncation(code, sectionName) {
  const warnings = [];
  let out = code;
  let repaired = false;
  const originalLength = (code || "").length;

  if (!code || typeof code !== "string") {
    return {
      truncated: true,
      repaired: false,
      code: out,
      warnings: ["Code is empty or not a string."],
    };
  }

  const stripped = stripStringsAndComments(code);

  // 1. export default present
  const hasExport = hasDefaultExport(out);

  // 2. JSX tag balance: opening <Tag vs closing </Tag> and self-closing />
  const openTags = (stripped.match(/<([A-Z][a-zA-Z0-9]*)\b/g) || []).length;
  const closeTags = (stripped.match(/<\/([A-Z][a-zA-Z0-9]*)\s*>/g) || []).length;
  const selfClosing = (stripped.match(/\/>/g) || []).length;
  const jsxBalanced = openTags <= closeTags + selfClosing + 2; // allow small skew

  // 3. Brace balance
  const openBraces = (stripped.match(/\{/g) || []).length;
  const closeBraces = (stripped.match(/\}/g) || []).length;
  const bracesBalanced = openBraces === closeBraces;

  // 4. Last non-empty line
  const nonEmptyLines = code.split(/\n/).filter((l) => l.trim().length > 0);
  const lastLine = nonEmptyLines.length ? nonEmptyLines[nonEmptyLines.length - 1].trim() : "";
  const endsProperly =
    /export\s+default\s+.+;?\s*$/.test(lastLine) ||
    /}\s*;\s*$/.test(lastLine) ||
    /}\s*$/.test(lastLine);

  const truncated = !hasExport || !jsxBalanced || !bracesBalanced || !endsProperly;

  if (!truncated) {
    return {
      truncated: false,
      repaired: false,
      code: out,
      warnings: [],
    };
  }

  // --- Repair ---

  // Component name from const SectionXX or function SectionXX
  const constMatch = out.match(/(?:export\s+)?const\s+([A-Z][a-zA-Z0-9]*)\s*=/);
  const fnMatch = out.match(/(?:export\s+)?function\s+([A-Z][a-zA-Z0-9]*)\s*[(\s]/);
  const componentName = fnMatch ? fnMatch[1] : (constMatch ? constMatch[1] : null);

  if (!hasExport && componentName) {
    out = out.trimEnd();
    if (!out.endsWith(";")) out += "\n";
    out += `\nexport default ${componentName};\n`;
    repaired = true;
  }

  if (!bracesBalanced && openBraces > closeBraces) {
    const missing = openBraces - closeBraces;
    out = out.trimEnd();
    out += "\n" + "}".repeat(missing);
    repaired = true;
  }

  if (!jsxBalanced && openTags > closeTags + selfClosing) {
    const toClose = openTags - (closeTags + selfClosing);
    const tagNames = stripped.match(/<([A-Z][a-zA-Z0-9]*)\b/g) || [];
    const lastOpened = tagNames.slice(-toClose).reverse();
    out = out.trimEnd();
    for (const name of lastOpened) {
      const tagName = name.replace(/^</, "");
      out += `</${tagName}>`;
    }
    repaired = true;
  }

  if (repaired && Math.abs(out.length - originalLength) > 50) {
    warnings.push(
      `Section ${sectionName} was heavily repaired — consider regenerating`
    );
  }

  return {
    truncated: true,
    repaired,
    code: out,
    warnings,
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
};
