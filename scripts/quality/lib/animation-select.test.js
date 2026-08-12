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

test('buildAnimationContext output contains only resolvable pattern names', () => {
  // Build the set of resolvable names from both keyspaces the prompt path uses
  const patternSnippets = {
    'fade-up-stagger': true,
    'fade-up-single': true,
    'character-reveal': true,
    'word-reveal': true,
    'count-up': true,
    'marquee': true,
    'scale-up': true,
    'slide-in-left': true,
  };

  // Also include all keys from the 48-component registry (lookupComponent() path)
  const registry = injector.loadRegistry();
  const registryComponentNames = Object.keys(registry.components || {});
  const resolvableNames = new Set([
    ...Object.keys(patternSnippets),
    ...registryComponentNames
  ]);

  // Exercise buildAnimationContext
  const context = injector.buildAnimationContext(
    {},  // animationAnalysis
    '',  // presetContent
    'HERO',  // archetype
    0,   // sectionIndex
    [],  // usedPatterns
    {},  // identification
    ''   // sectionVariant
  );

  // Extract all pattern names from the prompt output
  const patternMatches = context.animationContext.match(/Pattern: (\w+(?:[_-]\w+)*)/g) || [];
  const extractedPatterns = patternMatches.map(match => match.replace('Pattern: ', ''));

  // Also look for component imports or IDs (animation_id format has __)
  const animationIds = context.animationContext.match(/[\w_]+__[\w_]+/g) || [];

  // CRITICAL ASSERTION: Every pattern name must be resolvable
  extractedPatterns.forEach(pattern => {
    assert.ok(resolvableNames.has(pattern),
      `REGRESSION: buildAnimationContext output contains unresolvable pattern name '${pattern}'. ` +
      `This means selectLibraryAnimation (which returns animation_id format like 'codehagen__hero_badge') ` +
      `leaked into the prompt building path. The prompt path should only use names from PATTERN_SNIPPETS ` +
      `or the 48-component registry. Resolvable names: ${Array.from(resolvableNames).slice(0, 10).join(', ')}...`);
  });

  // CRITICAL: No animation_id format (with __) should appear in output
  assert.equal(animationIds.length, 0,
    `REGRESSION: buildAnimationContext contains ${animationIds.length} animation_id-format names: ` +
    `${animationIds.join(', ')}. This is the exact regression this test exists to catch.`);
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
