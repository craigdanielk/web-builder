// Alt-text validation for managed images (X-0111, assertion B6).
//
// A pure function on purpose. The save action (`src/app/admin/actions.ts`) is
// owned by another task and is mid-rewrite, so the RULE lives here where it can
// be tested in isolation, and the action makes one call into it. A validator that
// can only be exercised through a server action is a validator nobody has tested.
//
// THE FOUR RULES, ratified by the lead 2026-07-30, correcting contract §3 B6:
//
//   1. `alt: ""` (or absent, or whitespace) WITHOUT `decorative: true` -> REJECT.
//      An unmarked blank is an omission.
//   2. `alt: ""` WITH `decorative: true` -> ACCEPT. Empty is the WCAG-correct
//      value for an image that carries no information, and the flag is what
//      makes it a recorded decision instead of an omission.
//   3. non-empty `alt` WITH `decorative: true` -> REJECT as contradictory. The
//      content says both "skip this" and "here is what it shows"; picking one
//      silently would discard an editor's actual intent.
//   4. a legacy plain-string path -> ACCEPT. It predates the requirement.
//
// B6 as originally written stopped at rule 1, which made the CORRECT value for a
// decorative icon unsavable and would have forced an editor to write alt text for
// a chevron — on this client, that means inventing copy, which is prohibited
// outright. This is the Tier A lesson repeating: A6 asserted "zero occurrences of
// wp-content" and obeying it literally would have deleted a regulator's citation.
// Assert on what harms a reader, never on the string.
//
// Also not rejected: a ref that is simply absent (null/undefined/""). "No image
// chosen" is a valid state for an optional slot, not an image missing its alt.
//
// Nothing here ever supplies alt text. An empty alt is returned to the editor to
// write; it is never filled in.

import { isMediaRef } from "./media";

export type AltViolation = {
  /** Dotted path to the offending ref, e.g. `team[3].photo`. */
  path: string;
  assetId: string;
  reason: "missing" | "blank" | "contradictory";
};

export type MediaValidationResult = {
  ok: boolean;
  violations: AltViolation[];
  /** One line per violation, ready to show an editor. Empty when `ok`. */
  messages: string[];
};

/**
 * Walk any content value and collect every managed image ref whose alt text and
 * `decorative` flag do not agree with the four rules above.
 *
 * `missing`       = no `alt` key at all, and not marked decorative.
 * `blank`         = `alt` is "" or whitespace, and not marked decorative.
 * `contradictory` = marked decorative AND carrying alt text.
 *
 * `missing` and `blank` are kept apart because they change the message, not the
 * verdict; `contradictory` is a different fault with a different remedy.
 */
export function findAltViolations(content: unknown, path = ""): AltViolation[] {
  const out: AltViolation[] = [];
  walk(content, path);
  return out;

  function walk(node: unknown, at: string) {
    if (node == null) return;

    if (Array.isArray(node)) {
      node.forEach((item, i) => walk(item, `${at}[${i}]`));
      return;
    }
    if (typeof node !== "object") return;

    if (isMediaRef(node)) {
      const alt = (node as { alt?: unknown }).alt;
      const decorative = (node as { decorative?: unknown }).decorative === true;
      const described = typeof alt === "string" && alt.trim() !== "";

      if (decorative && described) {
        // Rule 3. Both signals are present and they disagree; the editor is told,
        // rather than one of the two being quietly discarded.
        out.push({ path: at || "image", assetId: node.assetId, reason: "contradictory" });
      } else if (!decorative && typeof alt !== "string") {
        out.push({ path: at || "image", assetId: node.assetId, reason: "missing" });
      } else if (!decorative && !described) {
        out.push({ path: at || "image", assetId: node.assetId, reason: "blank" });
      }
      // Rule 2 (decorative + blank) falls through as valid. Keep walking either
      // way: a ref is a plain object and could nest another one.
    }

    for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
      // `asset` is the hydrated row injected on the render path, never saved.
      // Its own `alt` column is the library default and is not this decision.
      if (k === "asset") continue;
      walk(v, at ? `${at}.${k}` : k);
    }
  }
}

/**
 * The single call the save action makes.
 *
 * Returns `ok: false` with per-field messages; the action must then write
 * nothing. Passing an array of blocks, one block's content, or a whole Puck
 * `data` object all work — the walk does not care about the wrapper.
 */
export function validateMediaAlt(content: unknown, path = ""): MediaValidationResult {
  const violations = findAltViolations(content, path);
  return {
    ok: violations.length === 0,
    violations,
    messages: violations.map(describeViolation),
  };
}

export function describeViolation(v: AltViolation): string {
  const where = v.path ? ` at ${v.path}` : "";
  switch (v.reason) {
    case "contradictory":
      return (
        `Image${where} is marked decorative but also has alt text. ` +
        `Either clear the alt text or untick "Decorative image".`
      );
    case "missing":
      return (
        `Image${where} has no alt text. Describe what the image shows, ` +
        `or tick "Decorative image" if it adds nothing a reader would miss.`
      );
    default:
      return (
        `Image${where} has empty alt text. Describe what the image shows, ` +
        `or tick "Decorative image" if it adds nothing a reader would miss.`
      );
  }
}
