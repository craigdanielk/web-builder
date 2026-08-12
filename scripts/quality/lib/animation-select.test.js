const { test } = require('node:test');
const assert = require('node:assert');
const injector = require('./animation-injector');

// ============================================================================
// UNIT TESTS: selectLibraryAnimation (new library-based selection)
// ============================================================================

test('selectLibraryAnimation is exported', () => {
  assert.equal(typeof injector.selectLibraryAnimation, 'function');
});

test('deriveComponentIntensity exists and works', () => {
  const deriveIntensity = injector.deriveComponentIntensity;
  assert.equal(typeof deriveIntensity, 'function');

  // Subtle component
  const subtleComp = {
    animation_type: 'entrance',
    duration_range_ms: [100, 200],
    motion_stacking_risk: 'low',
    causes_layout_shift_risk: 'low',
    scroll_coupling_risk: 'low'
  };
  assert.equal(deriveIntensity(subtleComp), 'subtle');

  // Dramatic component (high duration)
  const dramaticComp = {
    animation_type: 'entrance',
    duration_range_ms: [800, 2000],
    motion_stacking_risk: 'low',
    causes_layout_shift_risk: 'low',
    scroll_coupling_risk: 'low'
  };
  assert.equal(deriveIntensity(dramaticComp), 'dramatic');

  // Moderate component (everything else)
  const moderateComp = {
    animation_type: 'entrance',
    duration_range_ms: [300, 600],
    motion_stacking_risk: 'low',
    causes_layout_shift_risk: 'low',
    scroll_coupling_risk: 'low'
  };
  assert.equal(deriveIntensity(moderateComp), 'moderate');
});

test('selectLibraryAnimation returns animation_id format', () => {
  const result = injector.selectLibraryAnimation('HERO', 'moderate', 'framer-motion', []);
  if (result !== null) {
    // Library returns animation_id format like "entrance__blur_fade"
    assert.ok(typeof result === 'string');
    assert.ok(result.includes('__'), 'Should be animation_id format with __');
  }
});

test('common archetypes resolve at moderate intensity', () => {
  const commonArchetypes = ['HERO', 'GALLERY', 'NAV', 'STATS', 'FEATURES', 'TESTIMONIALS',
                             'FAQ', 'HOW-IT-WORKS', 'PRICING', 'CONTACT', 'FOOTER', 'BLOG-PREVIEW',
                             'PRODUCT-SHOWCASE', 'MAP', 'CTA', 'TEAM', 'VIDEO-SHOWCASE', 'NEWSLETTER'];

  let resolvedCount = 0;
  commonArchetypes.forEach(arch => {
    const result = injector.selectLibraryAnimation(arch, 'moderate', 'framer-motion', []);
    if (result !== null) {
      resolvedCount++;
    }
  });

  // At least 50% should resolve at moderate intensity
  assert.ok(resolvedCount >= 9, `Expected at least 9/18 archetypes to resolve at moderate, got ${resolvedCount}`);
});

test('non-existent archetype returns null', () => {
  const result = injector.selectLibraryAnimation('NOT-A-REAL-ARCHETYPE', 'moderate', 'framer-motion', []);
  assert.equal(result, null);
});

// ============================================================================
// CRITICAL FIX 1: Ceiling test that actually validates intensity
// ============================================================================

test('subtle intensity ceiling enforces derived intensity <= subtle', () => {
  // Get the full registry to look up components
  const fullRegistry = injector.loadFullRegistry();
  const componentMap = {};
  fullRegistry.components.forEach(comp => {
    componentMap[comp.animation_id] = comp;
  });

  // For each common archetype, get a subtle result and verify its intensity
  const testArchetypes = ['HERO', 'GALLERY', 'FEATURES', 'STATS', 'FAQ'];

  testArchetypes.forEach(arch => {
    const result = injector.selectLibraryAnimation(arch, 'subtle', 'framer-motion', []);

    if (result !== null) {
      // Look up the component in the full registry
      const comp = componentMap[result];
      assert.ok(comp, `Component ${result} not found in registry`);

      // Derive its intensity
      const derivedIntensity = injector.deriveComponentIntensity(comp);

      // CRITICAL: Assert it is 'subtle' (or would need ceiling filter to fail)
      // This test FAILS if deriveComponentIntensity returns 'moderate' or 'dramatic'
      assert.equal(derivedIntensity, 'subtle',
        `For archetype ${arch}, subtle preset returned component with intensity '${derivedIntensity}' ` +
        `(animation_id: ${result}). This violates the ceiling: subtle preset must never get ` +
        `moderate or dramatic components.`);
    }
  });
});

test('usedPatterns deduplication prevents reuse', () => {
  const first = injector.selectLibraryAnimation('FEATURES', 'moderate', 'framer-motion', []);
  if (first !== null) {
    // Second call should return different pattern or null
    const second = injector.selectLibraryAnimation('FEATURES', 'moderate', 'framer-motion', [first]);
    // They should be different (or both null)
    assert.ok(second !== first || second === null, 'Deduplication should prevent reuse');
  }
});

// ============================================================================
// CRITICAL FIX 2: Regression test that validates resolvability
// ============================================================================

// PATTERN_SNIPPETS keys — the reference-code keyspace the prompt path may name.
const PATTERN_SNIPPET_NAMES = [
  'fade-up-stagger',
  'fade-up-single',
  'character-reveal',
  'word-reveal',
  'count-up',
  'staggered-timeline',
];

// The union of every name the prompt path is allowed to emit: PATTERN_SNIPPETS
// keys plus the 48-component registry keys (the lookupComponent() keyspace).
function buildResolvableNames() {
  const registry = injector.loadRegistry();
  return new Set([
    ...PATTERN_SNIPPET_NAMES,
    ...Object.keys(registry.components || {}),
  ]);
}

/**
 * Assert that every pattern name in an animationContext is resolvable, and that
 * at least one name was found (a vacuous pass is a test failure, not a pass).
 *
 * @param {string} context - animationContext string from buildAnimationContext
 * @param {string} label - which code path produced it
 * @param {string[]} allowExtra - names admissible for this fixture only (e.g. a
 *        preset-supplied section_override, which the pipeline passes through by
 *        design and which is therefore not a leak).
 */
function assertOnlyResolvablePatterns(context, label, allowExtra) {
  const resolvableNames = buildResolvableNames();
  (allowExtra || []).forEach(n => resolvableNames.add(n));

  const patternMatches = context.match(/Pattern: (\w+(?:[_-]\w+)*)/g) || [];
  const extractedPatterns = patternMatches.map(m => m.replace('Pattern: ', ''));

  // VACUITY GUARD: an empty extraction must fail, not pass by iterating nothing.
  assert.ok(extractedPatterns.length > 0,
    `VACUOUS TEST (${label}): no 'Pattern: <name>' line was found in the ` +
    `animationContext, so the resolvability assertion below would iterate an ` +
    `empty array and pass without checking anything. Context was:\n${context.slice(0, 400)}`);

  extractedPatterns.forEach(pattern => {
    assert.ok(resolvableNames.has(pattern),
      `REGRESSION (${label}): output contains unresolvable pattern name '${pattern}'. ` +
      `This means selectLibraryAnimation (which returns animation_id format like ` +
      `'entrance__staggered_grid') leaked into the prompt building path. The prompt ` +
      `path may only name PATTERN_SNIPPETS keys or 48-component registry keys.`);
  });

  // animation_id format (double underscore) must never appear anywhere.
  const animationIds = context.match(/[A-Za-z0-9]+__[A-Za-z0-9_]+/g) || [];
  assert.equal(animationIds.length, 0,
    `REGRESSION (${label}): output contains ${animationIds.length} animation_id-format ` +
    `name(s): ${animationIds.join(', ')}. This is the exact regression this test exists to catch.`);
}

test('buildAnimationContext TIER 1 (component injection) emits only resolvable pattern names', () => {
  // Empty analysis + HERO resolves 'character-reveal' from the 48-component
  // registry and returns via the tier-1 component-injection branch.
  const context = injector.buildAnimationContext(
    {}, '', 'HERO', 0, [], {}, ''
  ).animationContext;

  assertOnlyResolvablePatterns(context, 'tier-1 component injection', []);
});

test('buildAnimationContext TIER 3 (affinity fallback) emits only resolvable pattern names', () => {
  // Entry conditions for the tier-3 branch (animation-injector.js:1329):
  //   1. animationAnalysis is truthy  -> skips the free-design branch (:1147)
  //   2. archetype resolves a non-null pattern list -> not a static section
  //   3. tier 1 misses: the resolved pattern has no component in the
  //      48-component registry. Forced here with a section_overrides entry
  //      naming a pattern that is deliberately absent from the registry.
  //   4. tier 2 misses: perSection has no entry for this sectionIndex, so
  //      there is no extracted animation signature to summarise.
  // Engine/intensity are set to gsap/dramatic because that is the combination
  // for which selectLibraryAnimation has a live candidate — i.e. the inputs
  // under which the historical regression is actually observable.
  const OVERRIDE = 'no-component-pattern';
  const preset = [
    'Motion: scroll-reveal/gsap',
    'animation_intensity: dramatic',
    `section_overrides: GALLERY:${OVERRIDE}`,
  ].join('\n');

  const result = injector.buildAnimationContext(
    { perSection: {} }, preset, 'GALLERY', 0, [], {}, ''
  );

  // Prove we are on tier 3: tier 1 would have returned a component context
  // (which carries an "### Component" block, not a bare Pattern line).
  assert.ok(result.animationContext.includes('## Animation Context'),
    'Expected the tier-3 snippet-fallback context shape');

  // The override is preset-supplied and passed through by design, so it is
  // admissible for this fixture; anything else must be resolvable.
  assertOnlyResolvablePatterns(result.animationContext, 'tier-3 affinity fallback', [OVERRIDE]);
});

test('buildAnimationContext FREE-DESIGN path emits only resolvable pattern names', () => {
  // Free-design branch (animation-injector.js:1147): animationAnalysis is null.
  // NOTE: with the 48-component registry carrying no affinity data,
  // selectAnimation returns null here and the branch lands on its generic
  // fade-up fallback. This case therefore does NOT currently discriminate the
  // selectAnimation -> selectLibraryAnimation swap (both fall through to the
  // same fallback). It is kept as a leak guard, not as a mutation detector.
  const preset = 'Motion: scroll-reveal/gsap\nanimation_intensity: dramatic\n';
  const context = injector.buildAnimationContext(
    null, preset, 'GALLERY', 0, [], {}, ''
  ).animationContext;

  const animationIds = context.match(/[A-Za-z0-9]+__[A-Za-z0-9_]+/g) || [];
  assert.equal(animationIds.length, 0,
    `REGRESSION (free-design path): output contains animation_id-format name(s): ` +
    `${animationIds.join(', ')}.`);
});

// ============================================================================
// REGRESSION TEST: selectAnimation (old path) is byte-identical to 7507e883
// ============================================================================

test('selectAnimation returns PATTERN_SNIPPETS-compatible names', () => {
  const result = injector.selectAnimation('HERO', 'moderate', 'framer-motion', []);
  // Result should be null (because 48-component registry has no affinity data)
  // OR a pattern snippet name (never animation_id format with __)
  if (result !== null) {
    assert.ok(!result.includes('__'),
      `selectAnimation returned animation_id format: ${result}. ` +
      `It should return PATTERN_SNIPPETS keys or null, not animation_ids.`);
  }
});

// ============================================================================
// HIT RATE MEASUREMENT
// ============================================================================

test('library selection hit rate measurement', () => {
  const testArchetypes = ['HERO', 'GALLERY', 'FEATURES', 'STATS', 'FAQ'];
  const intensities = ['subtle', 'moderate', 'dramatic'];
  const results = {};

  intensities.forEach(intensity => {
    results[intensity] = 0;
    testArchetypes.forEach(arch => {
      const result = injector.selectLibraryAnimation(arch, intensity, 'framer-motion', []);
      if (result !== null) {
        results[intensity]++;
      }
    });
  });

  console.log('\n=== LIBRARY SELECTION HIT RATE ===');
  console.log(`Subtle: ${results['subtle']}/${testArchetypes.length}`);
  console.log(`Moderate: ${results['moderate']}/${testArchetypes.length}`);
  console.log(`Dramatic: ${results['dramatic']}/${testArchetypes.length}`);

  // At minimum, moderate should have decent hit rate
  assert.ok(results['moderate'] > 0, 'Moderate intensity should resolve at least some archetypes');
});
