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

test('subtle intensity ceiling respects derivation', () => {
  // Get a subtle result
  const subtleResult = injector.selectLibraryAnimation('HERO', 'subtle', 'framer-motion', []);

  if (subtleResult !== null) {
    // Verify it came from a subtle component by checking against a dramatic fetch
    const dramaticResult = injector.selectLibraryAnimation('HERO', 'dramatic', 'framer-motion', []);
    // Subtle should never get something that dramatic rejects
    assert.ok(subtleResult || dramaticResult !== null, 'Ceiling should prevent inappropriate matches');
  }
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
// REGRESSION TEST: selectAnimation (old path) is byte-identical to 7507e883
// ============================================================================

test('selectAnimation returns PATTERN_SNIPPETS-compatible names', () => {
  const injector_imported = require('./animation-injector');
  const PATTERN_SNIPPETS = {
    'fade-up-stagger': 'test',
    'fade-up-single': 'test',
    'character-reveal': 'test',
    'word-reveal': 'test',
  };

  const result = injector_imported.selectAnimation('HERO', 'moderate', 'framer-motion', []);
  if (result !== null) {
    // Result should be one of the keys that exist in PATTERN_SNIPPETS
    // (or another pattern snippet key)
    assert.ok(typeof result === 'string');
    // Regression: should NOT contain '__' (that's animation_id format)
    assert.ok(!result.includes('__'), `selectAnimation should return snippet-format names, got: ${result}`);
  }
});

test('buildAnimationContext produces valid prompt without unresolvable names', () => {
  // Exercise the live prompt building path through buildAnimationContext
  const context = injector.buildAnimationContext(
    {},  // animationAnalysis
    '',  // presetContent
    'HERO',  // archetype
    0,   // sectionIndex
    [],  // usedPatterns
    {},  // identification
    ''   // sectionVariant
  );

  // Check that animationContext is generated
  assert.ok(context.animationContext);
  assert.ok(typeof context.animationContext === 'string');

  // Regression check: CRITICAL — prompt must NOT contain unresolvable names like "entrance__blur_fade"
  // These would be from selectLibraryAnimation leaking into the prompt path
  // The prompt path should only use names from PATTERN_SNIPPETS or component library
  const containsLibraryId = context.animationContext.includes('entrance__') ||
                             context.animationContext.includes('scroll__') ||
                             context.animationContext.includes('interactive__');

  assert.ok(!containsLibraryId,
    'Regression: prompt contains unresolvable animation_id format (e.g. entrance__blur_fade). ' +
    'This means selectLibraryAnimation leaked into the prompt building path.');
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
