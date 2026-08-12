const { test } = require('node:test');
const assert = require('node:assert');
const ci = require('./component-inject');

// ============================================================================
// RESOLUTION
// ============================================================================

test('resolveComponent finds a real, file-backed, verified-export component', () => {
  const r = ci.resolveComponent('interactive__hover_lift');
  assert.equal(r.ok, true);
  assert.equal(r.exportName, 'HoverLift');
  assert.equal(r.exportType, 'default');
  assert.equal(r.role, 'interactive');
  assert.ok(r.absPath.endsWith('interactive/hover-lift.tsx'));
});

test('resolveComponent refuses an unknown animation_id', () => {
  const r = ci.resolveComponent('not__a_real_component');
  assert.equal(r.ok, false);
  assert.match(r.reason, /no registry row/);
});

test('resolveComponent refuses an unbacked (21st-dev-library) row rather than guessing', () => {
  // Any row whose source_file points outside skills/animation-components/ or
  // doesn't exist must be refused — this is the trap the brief calls out:
  // 986 of 1034 registry rows have no file behind them.
  const registry = ci.loadFullRegistry();
  const unbacked = registry.find((c) => {
    if (!c.source_file) return true;
    const fs = require('fs');
    const path = require('path');
    return !fs.existsSync(path.resolve(__dirname, '../../../skills/animation-components', c.source_file));
  });
  assert.ok(unbacked, 'fixture assumption: at least one unbacked row must exist in the real registry');
  const r = ci.resolveComponent(unbacked.animation_id);
  assert.equal(r.ok, false);
});

// ============================================================================
// SAFETY ANALYSIS — the load-bearing "refuse rather than guess" logic
// ============================================================================

test('analyzeSafety accepts a component with required children + all-optional other props', () => {
  const fs = require('fs');
  const r = ci.resolveComponent('interactive__hover_lift');
  const src = fs.readFileSync(r.absPath, 'utf8');
  const safety = ci.analyzeSafety(src, r.exportName);
  assert.equal(safety.safe, true);
});

test('analyzeSafety refuses a component whose root is an inline tag (span)', () => {
  const fs = require('fs');
  const r = ci.resolveComponent('entrance__blur_fade');
  const src = fs.readFileSync(r.absPath, 'utf8');
  const safety = ci.analyzeSafety(src, r.exportName);
  assert.equal(safety.safe, false);
  assert.match(safety.reason, /inline\/interactive root/);
});

test('analyzeSafety refuses a component with no children prop', () => {
  const fs = require('fs');
  const r = ci.resolveComponent('entrance__fade_up_single');
  const src = fs.readFileSync(r.absPath, 'utf8');
  const safety = ci.analyzeSafety(src, r.exportName);
  assert.equal(safety.safe, false);
  assert.match(safety.reason, /no children prop/);
});

test('analyzeSafety refuses a component with a required non-children prop and no default', () => {
  const fs = require('fs');
  const r = ci.resolveComponent('scroll__parallax_layers');
  const src = fs.readFileSync(r.absPath, 'utf8');
  const safety = ci.analyzeSafety(src, r.exportName);
  assert.equal(safety.safe, false);
  assert.match(safety.reason, /requires prop\(s\)/);
});

test('analyzeSafety accepts interface fields with newline-only separators (no trailing comma/semicolon)', () => {
  // entrance/scale-up.tsx has no delimiters between interface fields at all
  // (relies on ASI) — the field splitter must treat newlines as separators
  // too, or every field after the first is swallowed into the first field's
  // type string.
  const src = `
interface FooProps {
  className?: string
  children: React.ReactNode
  delay?: number
}
export function Foo({ className, children, delay = 0 }: FooProps) {
  return (
    <div>
      {children}
    </div>
  );
}
`;
  const safety = ci.analyzeSafety(src, 'Foo');
  assert.equal(safety.safe, true);
});

test('analyzeSafety refuses children typed as string, not ReactNode', () => {
  const src = `
interface FooProps {
  children: string;
}
export function Foo({ children }: FooProps) {
  return <div>{children}</div>;
}
`;
  const safety = ci.analyzeSafety(src, 'Foo');
  assert.equal(safety.safe, false);
  assert.match(safety.reason, /not ReactNode/);
});

// ============================================================================
// INSERTION POINT
// ============================================================================

const SIMPLE_SECTION = `'use client';

import { motion } from 'framer-motion';

export default function HeroCentered() {
  return (
    <section className="py-24 bg-white">
      <motion.h1 initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Hello</motion.h1>
    </section>
  );
}
`;

test('findInsertionPoint locates the single root <section> of the default export', () => {
  const point = ci.findInsertionPoint(SIMPLE_SECTION);
  assert.equal(point.ok, true);
  const slice = SIMPLE_SECTION.slice(point.start, point.end);
  assert.ok(slice.startsWith('<section'));
  assert.ok(slice.endsWith('</section>'));
});

test('findInsertionPoint refuses a file with no export default function', () => {
  const point = ci.findInsertionPoint('export function NotDefault() { return <section></section>; }');
  assert.equal(point.ok, false);
  assert.match(point.reason, /no export default function/);
});

test('findInsertionPoint refuses two sibling root sections inside the default export (ambiguous)', () => {
  const src = `
export default function Two() {
  return (
    <>
      <section>A</section>
      <section>B</section>
    </>
  );
}
`;
  const point = ci.findInsertionPoint(src);
  assert.equal(point.ok, false);
  assert.match(point.reason, /sibling root/);
});

test('findInsertionPoint ignores a <section> in a helper function declared after the default export', () => {
  // Mirrors the real 06-faq.tsx shape (a helper sub-component with its own
  // return) but with the helper AFTER the default export instead of before,
  // to prove the scan is bounded to the default export's own body and does
  // not leak into sibling declarations.
  const src = `
export default function Two() {
  return (
    <section>A</section>
  );
}
function Helper() {
  return <section>B</section>;
}
`;
  const point = ci.findInsertionPoint(src);
  assert.equal(point.ok, true);
  assert.ok(src.slice(point.start, point.end).includes('A'));
});

test('findInsertionPoint refuses a self-closing root <section />', () => {
  const src = `
export default function Empty() {
  return (
    <section className="x" />
  );
}
`;
  const point = ci.findInsertionPoint(src);
  assert.equal(point.ok, false);
  assert.match(point.reason, /self-closing/);
});

test('findInsertionPoint refuses a root that is not directly returned', () => {
  const src = `
export default function Weird() {
  const el = <section>hi</section>;
  return el;
}
`;
  const point = ci.findInsertionPoint(src);
  assert.equal(point.ok, false);
});

// ============================================================================
// WRAP
// ============================================================================

test('wrapWithComponent wraps the root, preserves inner content, adds one import', () => {
  const resolved = ci.resolveComponent('interactive__hover_lift');
  const result = ci.wrapWithComponent(SIMPLE_SECTION, resolved);
  assert.equal(result.ok, true);
  assert.match(result.tsx, /import HoverLift from '@\/components\/animations\/hover-lift';/);
  assert.match(result.tsx, /<HoverLift>\s*<section/);
  assert.match(result.tsx, /<\/section>\s*<\/HoverLift>/);
  // Inner content (the existing motion.h1) survives untouched.
  assert.match(result.tsx, /<motion\.h1 initial=\{\{ opacity: 0 \}\} animate=\{\{ opacity: 1 \}\}>Hello<\/motion\.h1>/);
});

test('wrapWithComponent refuses to wrap the same component twice (idempotence)', () => {
  const resolved = ci.resolveComponent('interactive__hover_lift');
  const once = ci.wrapWithComponent(SIMPLE_SECTION, resolved);
  assert.equal(once.ok, true);
  const twice = ci.wrapWithComponent(once.tsx, resolved);
  assert.equal(twice.ok, false);
  assert.match(twice.reason, /already imports/);
});

test('wrapWithComponent named export uses named import syntax', () => {
  const resolved = ci.resolveComponent('entrance__staggered_timeline');
  const result = ci.wrapWithComponent(SIMPLE_SECTION, resolved);
  assert.equal(result.ok, true);
  assert.match(result.tsx, /import \{ AnimatedGroup \} from '@\/components\/animations\/staggered-timeline';/);
});

// ============================================================================
// SELECTION — role-first ordering, dedup, refusal-aware
// ============================================================================

test('selectComponentForSection returns a SAFE, unused, real component for HOW-IT-WORKS', () => {
  const resolved = ci.selectComponentForSection('HOW-IT-WORKS', []);
  assert.ok(resolved, 'expected at least one safe candidate for HOW-IT-WORKS (entrance role)');
  assert.ok(resolved.ok);
});

test('selectComponentForSection respects dedup across sections', () => {
  const first = ci.selectComponentForSection('HERO', []);
  assert.ok(first);
  const second = ci.selectComponentForSection('HERO', [first.animationId]);
  if (second) {
    assert.notEqual(second.animationId, first.animationId);
  }
});

test('selectComponentForSection is a ceiling: a dramatic-intensity component is excluded at moderate preset intensity', () => {
  // background__aurora_background derives to 'dramatic' intensity; it must
  // not be selectable when the tenant preset says 'moderate' (Cape Crypto's
  // explicit setting), even though it would otherwise be SAFE and unused.
  const atModerate = ci.selectComponentForSection('ABOUT', [], 'moderate');
  if (atModerate) {
    assert.notEqual(atModerate.animationId, 'background__aurora_background');
  }
  const atDramatic = ci.selectComponentForSection('ABOUT', [], 'dramatic');
  // At dramatic, aurora-background becomes an eligible candidate again (not
  // asserting it's chosen — role order may prefer another entrance/interactive
  // candidate first — only that excluding it was intensity-driven, not absolute).
  assert.ok(atDramatic === null || typeof atDramatic.animationId === 'string');
});

test('selectComponentForSection returns null once every safe candidate is exhausted', () => {
  const registry = ci.loadFullRegistry();
  const allIds = registry.map((c) => c.animation_id);
  const result = ci.selectComponentForSection('HERO', allIds);
  assert.equal(result, null);
});

// ============================================================================
// END-TO-END injectIntoSection
// ============================================================================

test('injectIntoSection injects a real component and reports it in the reason', () => {
  const out = ci.injectIntoSection(SIMPLE_SECTION, 'HOW-IT-WORKS', []);
  assert.equal(out.injected, true);
  assert.ok(out.component);
  assert.match(out.reason, /wrapped with/);
  assert.notEqual(out.tsx, SIMPLE_SECTION);
});

test('injectIntoSection refuses and returns byte-identical tsx when no safe component exists', () => {
  // Exhaust every candidate up front so nothing is left to select.
  const registry = ci.loadFullRegistry();
  const allIds = registry.map((c) => c.animation_id);
  const out = ci.injectIntoSection(SIMPLE_SECTION, 'HERO', allIds);
  assert.equal(out.injected, false);
  assert.equal(out.tsx, SIMPLE_SECTION);
  assert.equal(out.component, null);
});

test('injectIntoSection refuses and returns byte-identical tsx on an unwrappable section shape', () => {
  const noRoot = 'export default function Bare() { return <div>no section here</div>; }';
  const out = ci.injectIntoSection(noRoot, 'HOW-IT-WORKS', []);
  assert.equal(out.injected, false);
  assert.equal(out.tsx, noRoot);
});
