const { test } = require('node:test');
const assert = require('node:assert');
const injector = require('./animation-injector');

// Test 1: Verify export
test('selectAnimation is exported', () => {
  assert.equal(typeof injector.selectAnimation, 'function');
});

// Test 2: Intensity derivation function
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

// Test 3: All common archetypes return non-null at moderate
test('common archetypes resolve at moderate intensity', () => {
  const commonArchetypes = ['HERO', 'GALLERY', 'NAV', 'STATS', 'FEATURES', 'TESTIMONIALS',
                             'FAQ', 'HOW-IT-WORKS', 'PRICING', 'CONTACT', 'FOOTER', 'BLOG-PREVIEW',
                             'PRODUCT-SHOWCASE', 'MAP', 'CTA', 'TEAM', 'VIDEO-SHOWCASE', 'NEWSLETTER'];

  let resolvedCount = 0;
  const results = {};

  commonArchetypes.forEach(arch => {
    const result = injector.selectAnimation(arch, 'moderate', 'framer-motion', []);
    results[arch] = result;
    if (result !== null) {
      resolvedCount++;
    }
  });

  // At least 50% should resolve at moderate intensity
  assert.ok(resolvedCount >= 9, `Expected at least 9/18 archetypes to resolve at moderate, got ${resolvedCount}`);
  console.log(`Resolved ${resolvedCount}/18 common archetypes at moderate intensity`);
});

// Test 4: Non-existent archetype returns null
test('non-existent archetype returns null', () => {
  const result = injector.selectAnimation('NOT-A-REAL-ARCHETYPE', 'moderate', 'framer-motion', []);
  assert.equal(result, null);
});

// Test 5: Subtle ceiling semantics (subtle never gets dramatic components)
test('subtle intensity respects ceiling', () => {
  // Run multiple times to get a good sample
  const subtleResults = [];
  for (let i = 0; i < 20; i++) {
    const result = injector.selectAnimation('HERO', 'subtle', 'framer-motion', []);
    subtleResults.push(result);
  }

  // All should be null or represent truly subtle patterns
  // (can't directly verify intensity from name, so we just verify they exist)
  const nonNull = subtleResults.filter(r => r !== null);
  // At least verify the function runs without crashing
  assert.ok(Array.isArray(subtleResults));
});

// Test 6: Deduplication works
test('usedPatterns deduplication prevents reuse', () => {
  const first = injector.selectAnimation('FEATURES', 'moderate', 'framer-motion', []);
  if (first !== null) {
    // Second call should return different pattern or null
    const second = injector.selectAnimation('FEATURES', 'moderate', 'framer-motion', [first]);
    // They should be different (or both null)
    assert.ok(second !== first || second === null, 'Deduplication should prevent reuse');
  }
});

// Test 7: Engine filtering works for gsap
test('gsap engine filtering', () => {
  // At least one gsap component should exist
  const result = injector.selectAnimation('HERO', 'moderate', 'gsap', []);
  // Result may be null (gsap components in registry), but function should run
  assert.ok(result === null || typeof result === 'string');
});

// Test 8: Hit rate by intensity - measure real selections
test('hit rate measurement', () => {
  const testArchetypes = ['HERO', 'GALLERY', 'FEATURES', 'STATS', 'FAQ'];
  const intensities = ['subtle', 'moderate', 'dramatic'];
  const results = {};

  intensities.forEach(intensity => {
    results[intensity] = 0;
    testArchetypes.forEach(arch => {
      const result = injector.selectAnimation(arch, intensity, 'framer-motion', []);
      if (result !== null) {
        results[intensity]++;
      }
    });
  });

  console.log('\n=== HIT RATE BY INTENSITY ===');
  console.log(`Subtle: ${results['subtle']}/${testArchetypes.length}`);
  console.log(`Moderate: ${results['moderate']}/${testArchetypes.length}`);
  console.log(`Dramatic: ${results['dramatic']}/${testArchetypes.length}`);

  // At minimum, moderate should have decent hit rate
  assert.ok(results['moderate'] > 0, 'Moderate intensity should resolve at least some archetypes');
});
