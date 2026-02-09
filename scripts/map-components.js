#!/usr/bin/env node
'use strict';

/**
 * Map downloaded 21st.dev components to our 27 animation registry patterns.
 * Copies source files into the correct category directories and updates registry.json.
 */

var fs = require('fs');
var path = require('path');

var LIB_DIR = path.resolve(__dirname, '../skills/animation-components/21st-dev-library');
var DEST_DIR = path.resolve(__dirname, '../skills/animation-components');
var reg21st = JSON.parse(fs.readFileSync(path.join(LIB_DIR, 'registry-full.json'), 'utf8'));
var ourReg = JSON.parse(fs.readFileSync(path.join(DEST_DIR, 'registry.json'), 'utf8'));

// Final mapping: pattern → 21st.dev component key
var mapping = {
  'fade-up-stagger':    'ibelick/animated-group',
  'fade-up-single':     'dillionverma/fade-text',
  'character-reveal':   'chetanverma16/text-reveal',
  'word-reveal':        'molecule-lab-rushil/word-rotate',
  'slide-in-left':      'minhxthanh/slide-tabs',
  'slide-in-right':     'minhxthanh/slide-tabs',
  'scale-up':           'badtzx0/blur-reveal',
  'blur-fade':          'badtzx0/blur-reveal',
  'staggered-timeline': 'ibelick/animated-group',
  'parallax-section':   'sshahaider/zoom-parallax',
  'parallax-layers':    'bundui/floating-paths',
  'scroll-progress':    'skyleen77/scroll-progress',
  'pin-and-reveal':     'minhxthanh/sticky-scroll-cards-section',
  'horizontal-scroll':  'uniquesonu/horizontal-scroll-carousel',
  'hover-lift':         'JurreHoutkamp/hover-zoom',
  'hover-glow':         'yashvw25/neon-flow',
  'magnetic-button':    'uilayout.contact/button-magnetic',
  'tilt-card':          'JurreHoutkamp/tilt-card',
  'accordion-expand':   'meschacirung/faq',
  'floating':           'ln-dev7/floating-button',
  'marquee':            'lukacho/marquee',
  'gradient-shift':     'sshahaider/gradient-background',
  'count-up':           'ibelick/sliding-number',
  'typewriter':         'aceternity/typewriter-effect',
  'text-gradient-flow': 'ibelick/text-shimmer-wave',
  'text-scramble':      'dhileepkumargm/digital-glitch',
  'split-text-stagger': 'minhxthanh/bubble-text',
};

// Fallback if gsap version not available
if (!reg21st.components['chetanverma16/text-reveal']) {
  mapping['character-reveal'] = 'jatin-yadav05/scale-letter';
}

var copied = 0;
var failed = 0;
var seen = {};

Object.keys(mapping).forEach(function (pattern) {
  var sourceKey = mapping[pattern];
  var comp = reg21st.components[sourceKey];
  if (!comp) {
    console.log('SKIP ' + pattern + ': source ' + sourceKey + ' not in registry');
    failed++;
    return;
  }

  // Find the source file
  var localFile = comp.files && comp.files[0] ? comp.files[0].localPath : null;
  if (!localFile) {
    console.log('SKIP ' + pattern + ': no files for ' + sourceKey);
    failed++;
    return;
  }

  var srcPath = path.join(LIB_DIR, localFile);
  if (!fs.existsSync(srcPath)) {
    console.log('SKIP ' + pattern + ': file not found ' + srcPath);
    failed++;
    return;
  }

  // Determine destination category
  var category = ourReg.components[pattern] ? ourReg.components[pattern].category : 'entrance';
  var destPath = path.join(DEST_DIR, category, pattern + '.tsx');

  // Copy file
  var source = fs.readFileSync(srcPath, 'utf8');
  fs.mkdirSync(path.dirname(destPath), { recursive: true });
  fs.writeFileSync(destPath, source, 'utf8');

  // Update our registry
  if (ourReg.components[pattern]) {
    ourReg.components[pattern].status = 'ready';
    ourReg.components[pattern].source = '21st.dev/' + sourceKey;
    ourReg.components[pattern].dependencies = comp.dependencies || [];
    // Determine engine from deps
    if ((comp.dependencies || []).indexOf('gsap') >= 0 || (comp.dependencies || []).indexOf('@gsap/react') >= 0) {
      ourReg.components[pattern].engine = 'gsap';
    } else if ((comp.dependencies || []).indexOf('framer-motion') >= 0 || (comp.dependencies || []).indexOf('motion') >= 0) {
      ourReg.components[pattern].engine = 'framer-motion';
    } else {
      ourReg.components[pattern].engine = 'css';
    }
  }

  console.log('OK ' + pattern + ' <- ' + sourceKey + ' [' + (comp.dependencies || []).join(', ') + ']');
  copied++;
});

// Write updated registry
fs.writeFileSync(path.join(DEST_DIR, 'registry.json'), JSON.stringify(ourReg, null, 2) + '\n', 'utf8');

console.log('');
console.log('=== Done ===');
var readyCount = 0, placeholderCount = 0;
Object.keys(ourReg.components).forEach(function (k) {
  if (ourReg.components[k].status === 'ready') readyCount++;
  else placeholderCount++;
});
console.log('Copied: ' + copied + ', Failed: ' + failed);
console.log('Registry: ' + readyCount + ' ready, ' + placeholderCount + ' placeholder');
