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
// SAFETY ANALYSIS — the load-bearing "refuse rather than guess" logic.
//
// This still matters under assembly-level wrapping: a component that takes
// no props, or types children as something other than ReactNode, or renders
// an inline root tag, is unsafe to wrap a section in REGARDLESS of where the
// wrap happens — <SlideTabs><Section01HERO /></SlideTabs> would silently
// discard the section's content just as surely as string-rewriting would
// have corrupted it.
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

test('analyzeSafety refuses a render-prop children signature that merely contains the substring "ReactNode"', () => {
  // A naive `/ReactNode/.test(type)` check is a false positive here: this
  // type string DOES contain "ReactNode" (`(state: FooState) => ReactNode`)
  // but children is a FUNCTION the component calls as `children(state)`,
  // not a value it renders directly. Wrapping a section — passing a JSX
  // element as children — would break at the call site. This is exactly
  // the false-positive shape flagged in review: a false negative only costs
  // coverage, a false positive breaks the build.
  const src = `
interface FooProps {
  children: (state: FooState) => React.ReactNode;
}
export function Foo({ children }: FooProps) {
  const state = useFooState();
  return <div>{children(state)}</div>;
}
`;
  const safety = ci.analyzeSafety(src, 'Foo');
  assert.equal(safety.safe, false);
  assert.match(safety.reason, /render-prop function/);
});

// ============================================================================
// IMPORT PLUMBING
// ============================================================================

test('importStatementFor uses a named import for a named export', () => {
  const resolved = ci.resolveComponent('entrance__staggered_timeline');
  const stmt = ci.importStatementFor(resolved);
  assert.equal(stmt, 'import { AnimatedGroup } from "@/components/animations/staggered-timeline";');
});

test('importStatementFor uses a default import for a default export', () => {
  const resolved = ci.resolveComponent('interactive__hover_lift');
  const stmt = ci.importStatementFor(resolved);
  assert.equal(stmt, 'import HoverLift from "@/components/animations/hover-lift";');
});

// ============================================================================
// SELECTION — role-first ordering, dedup, intensity ceiling, refusal-aware
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
// END-TO-END decideComponentForSection
// ============================================================================

test('decideComponentForSection selects a real component and reports it in the reason', () => {
  const out = ci.decideComponentForSection('HOW-IT-WORKS', [], 'moderate');
  assert.equal(out.injected, true);
  assert.ok(out.component);
  assert.match(out.reason, /selected/);
});

test('decideComponentForSection refuses when no safe component exists', () => {
  const registry = ci.loadFullRegistry();
  const allIds = registry.map((c) => c.animation_id);
  const out = ci.decideComponentForSection('HERO', allIds, 'moderate');
  assert.equal(out.injected, false);
  assert.equal(out.component, null);
  assert.equal(out.reason, 'no backed component for role');
});
