'use strict';

const https = require('https');
const http = require('http');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const MAX_BUNDLES = 5;
const MAX_BUNDLE_SIZE = 2 * 1024 * 1024; // 2MB
const MAX_CALLS = 200;
const DOWNLOAD_TIMEOUT_MS = 10000;
const MAX_REDIRECTS = 3;

const TAG = '[gsap-extractor]';

// Known GSAP animation properties we care about
const ANIM_PROPS = [
  'y', 'x', 'opacity', 'scale', 'rotation',
  'rotateX', 'rotateY', 'duration', 'ease',
  'stagger', 'delay'
];

const SCROLL_TRIGGER_PROPS = [
  'trigger', 'start', 'end', 'scrub', 'pin', 'once'
];

// ---------------------------------------------------------------------------
// Internal: Download a JS bundle via HTTP(S)
// ---------------------------------------------------------------------------

function downloadBundle(url) {
  return new Promise((resolve) => {
    const fetch = (target, redirectsLeft) => {
      const mod = target.startsWith('https') ? https : http;

      const req = mod.get(target, { timeout: DOWNLOAD_TIMEOUT_MS }, (res) => {
        // Follow redirects
        if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location) {
          if (redirectsLeft <= 0) {
            resolve(null);
            return;
          }
          let loc = res.headers.location;
          if (loc.startsWith('/')) {
            const u = new URL(target);
            loc = `${u.protocol}//${u.host}${loc}`;
          }
          res.resume(); // drain the current response
          fetch(loc, redirectsLeft - 1);
          return;
        }

        if (res.statusCode !== 200) {
          res.resume();
          resolve(null);
          return;
        }

        // Check Content-Length before buffering
        const cl = parseInt(res.headers['content-length'], 10);
        if (cl && cl > MAX_BUNDLE_SIZE) {
          res.resume();
          resolve(null);
          return;
        }

        const chunks = [];
        let totalLen = 0;

        res.on('data', (chunk) => {
          totalLen += chunk.length;
          if (totalLen > MAX_BUNDLE_SIZE) {
            res.destroy();
            resolve(null);
            return;
          }
          chunks.push(chunk);
        });

        res.on('end', () => {
          resolve(Buffer.concat(chunks).toString('utf-8'));
        });

        res.on('error', () => resolve(null));
      });

      req.on('timeout', () => {
        req.destroy();
        resolve(null);
      });

      req.on('error', () => resolve(null));
    };

    fetch(url, MAX_REDIRECTS);
  });
}

// ---------------------------------------------------------------------------
// Internal: Extract balanced braces/parens starting at startIndex
// ---------------------------------------------------------------------------

function extractBalancedBraces(str, startIndex) {
  const open = str[startIndex];
  if (open !== '{' && open !== '(') return null;
  const close = open === '{' ? '}' : ')';

  let depth = 0;
  let inSingleQuote = false;
  let inDoubleQuote = false;
  let inTemplate = false;
  let escaped = false;

  for (let i = startIndex; i < str.length; i++) {
    const ch = str[i];

    if (escaped) {
      escaped = false;
      continue;
    }

    if (ch === '\\') {
      escaped = true;
      continue;
    }

    if (inSingleQuote) {
      if (ch === "'") inSingleQuote = false;
      continue;
    }
    if (inDoubleQuote) {
      if (ch === '"') inDoubleQuote = false;
      continue;
    }
    if (inTemplate) {
      if (ch === '`') inTemplate = false;
      continue;
    }

    if (ch === "'") { inSingleQuote = true; continue; }
    if (ch === '"') { inDoubleQuote = true; continue; }
    if (ch === '`') { inTemplate = true; continue; }

    if (ch === open) {
      depth++;
    } else if (ch === close) {
      depth--;
      if (depth === 0) {
        return str.substring(startIndex, i + 1);
      }
    }
  }

  return null; // unbalanced
}

// ---------------------------------------------------------------------------
// Internal: Parse a GSAP vars object-literal string into structured data
// ---------------------------------------------------------------------------

function parseGsapVars(varsStr) {
  const vars = {};
  let scrollTrigger = null;
  let duration = null;
  let ease = null;

  if (!varsStr) return { vars, scrollTrigger, duration, ease };

  // Strip outer braces if present
  let inner = varsStr.trim();
  if (inner.startsWith('{') && inner.endsWith('}')) {
    inner = inner.slice(1, -1);
  }

  // Extract scrollTrigger sub-object first (before general key-value parsing)
  const stMatch = inner.match(/scrollTrigger\s*:\s*\{/);
  if (stMatch) {
    const stStart = inner.indexOf('{', stMatch.index);
    const stBlock = extractBalancedBraces(inner, stStart);
    if (stBlock) {
      scrollTrigger = {};
      for (const prop of SCROLL_TRIGGER_PROPS) {
        // String values: trigger, start, end
        const strRe = new RegExp(`(?:^|[,{\\s])${prop}\\s*:\\s*["']([^"']+)["']`);
        const strM = stBlock.match(strRe);
        if (strM) {
          scrollTrigger[prop] = strM[1];
          continue;
        }
        // Boolean / numeric values: scrub, pin, once
        const valRe = new RegExp(`(?:^|[,{\\s])${prop}\\s*:\\s*([^,}\\s]+)`);
        const valM = stBlock.match(valRe);
        if (valM) {
          const raw = valM[1].trim();
          if (raw === 'true') scrollTrigger[prop] = true;
          else if (raw === 'false') scrollTrigger[prop] = false;
          else if (!isNaN(Number(raw))) scrollTrigger[prop] = Number(raw);
          else scrollTrigger[prop] = raw;
        }
      }
      // Fill missing scroll trigger props with null
      for (const prop of SCROLL_TRIGGER_PROPS) {
        if (!(prop in scrollTrigger)) scrollTrigger[prop] = null;
      }
    }
  }

  // Extract animation properties from the vars string
  for (const prop of ANIM_PROPS) {
    // String values (ease, delay like "-=0.4")
    const strRe = new RegExp(`(?:^|[,{\\s])${prop}\\s*:\\s*["']([^"']+)["']`);
    const strM = inner.match(strRe);
    if (strM) {
      if (prop === 'duration') duration = strM[1];
      else if (prop === 'ease') ease = strM[1];
      else vars[prop] = strM[1];
      continue;
    }

    // Numeric / unquoted values
    const numRe = new RegExp(`(?:^|[,{\\s])${prop}\\s*:\\s*([^,}"'\\s]+)`);
    const numM = inner.match(numRe);
    if (numM) {
      const raw = numM[1].trim();
      const num = Number(raw);
      if (prop === 'duration') duration = isNaN(num) ? raw : num;
      else if (prop === 'ease') ease = raw;
      else if (prop === 'stagger' || prop === 'delay') {
        vars[prop] = isNaN(num) ? raw : num;
      } else {
        vars[prop] = isNaN(num) ? raw : num;
      }
    }
  }

  return { vars, scrollTrigger, duration, ease };
}

// ---------------------------------------------------------------------------
// Internal: Extract GSAP calls from JS content
// ---------------------------------------------------------------------------

function extractGsapCalls(jsContent) {
  const calls = [];

  const patterns = [
    { re: /gsap\.from\s*\(/g, method: 'from' },
    { re: /gsap\.to\s*\(/g, method: 'to' },
    { re: /gsap\.fromTo\s*\(/g, method: 'fromTo' },
    { re: /gsap\.timeline\s*\(/g, method: 'timeline' },
    { re: /\.from\s*\(/g, method: 'timeline.from' },
    { re: /\.to\s*\(/g, method: 'timeline.to' },
    { re: /ScrollTrigger\.create\s*\(/g, method: 'ScrollTrigger.create' },
  ];

  for (const { re, method } of patterns) {
    let match;
    while ((match = re.exec(jsContent)) !== null) {
      if (calls.length >= MAX_CALLS) break;

      // Find the opening paren for the call arguments
      const parenIdx = jsContent.indexOf('(', match.index + match[0].length - 1);
      if (parenIdx === -1) continue;

      const argBlock = extractBalancedBraces(jsContent, parenIdx);
      if (!argBlock) continue;

      // Strip outer parens
      const argsInner = argBlock.slice(1, -1).trim();

      let targetSelector = null;
      let parsedVars = { vars: {}, scrollTrigger: null, duration: null, ease: null };
      let stagger = null;
      let delay = null;

      if (method === 'timeline') {
        // Timeline constructor: gsap.timeline({ scrollTrigger: {...}, defaults: {...} })
        const braceIdx = argsInner.indexOf('{');
        if (braceIdx !== -1) {
          const block = extractBalancedBraces(argsInner, braceIdx);
          parsedVars = parseGsapVars(block);
        }
      } else if (method === 'ScrollTrigger.create') {
        // Standalone ScrollTrigger: ScrollTrigger.create({ trigger: "...", ... })
        const braceIdx = argsInner.indexOf('{');
        if (braceIdx !== -1) {
          const block = extractBalancedBraces(argsInner, braceIdx);
          parsedVars = parseGsapVars(block);
          // For standalone ScrollTrigger, the whole thing is the scrollTrigger config
          if (!parsedVars.scrollTrigger) {
            const stVars = parseGsapVars(block);
            parsedVars.scrollTrigger = {};
            for (const prop of SCROLL_TRIGGER_PROPS) {
              if (stVars.vars[prop] !== undefined) {
                parsedVars.scrollTrigger[prop] = stVars.vars[prop];
              } else {
                parsedVars.scrollTrigger[prop] = null;
              }
            }
          }
        }
      } else if (method === 'fromTo') {
        // gsap.fromTo(target, fromVars, toVars)
        // Extract target selector
        const selectorMatch = argsInner.match(/^["']([^"']+)["']/);
        if (selectorMatch) targetSelector = selectorMatch[1];

        // Find the two vars objects after the target
        const afterTarget = selectorMatch
          ? argsInner.slice(selectorMatch[0].length).replace(/^\s*,\s*/, '')
          : argsInner;

        const firstBrace = afterTarget.indexOf('{');
        if (firstBrace !== -1) {
          const fromBlock = extractBalancedBraces(afterTarget, firstBrace);
          if (fromBlock) {
            // toVars is after the fromBlock
            const rest = afterTarget.slice(firstBrace + fromBlock.length).replace(/^\s*,\s*/, '');
            const secondBrace = rest.indexOf('{');
            if (secondBrace !== -1) {
              const toBlock = extractBalancedBraces(rest, secondBrace);
              parsedVars = parseGsapVars(toBlock);
            }
          }
        }
      } else {
        // gsap.from/to or timeline .from/.to: (target, vars)
        const selectorMatch = argsInner.match(/^["']([^"']+)["']/);
        if (selectorMatch) targetSelector = selectorMatch[1];

        // Find the vars object
        const braceIdx = argsInner.indexOf('{');
        if (braceIdx !== -1) {
          const block = extractBalancedBraces(argsInner, braceIdx);
          parsedVars = parseGsapVars(block);
        }
      }

      // Pull stagger and delay from vars into top-level
      stagger = parsedVars.vars.stagger !== undefined ? parsedVars.vars.stagger : null;
      delay = parsedVars.vars.delay !== undefined ? parsedVars.vars.delay : null;
      delete parsedVars.vars.stagger;
      delete parsedVars.vars.delay;

      calls.push({
        method,
        targetSelector,
        vars: parsedVars.vars,
        duration: parsedVars.duration,
        ease: parsedVars.ease,
        stagger,
        delay,
        scrollTrigger: parsedVars.scrollTrigger,
        timelineId: null,
        elementY: null,
        source: 'static',
      });
    }

    if (calls.length >= MAX_CALLS) break;
  }

  return calls;
}

// ---------------------------------------------------------------------------
// Internal: Classify GSAP plugin usage from JS bundle content
// ---------------------------------------------------------------------------

function classifyPluginUsage(bundles) {
  const pluginUsage = {};
  const allCode = bundles.map((b) => (typeof b === 'string' ? b : (b.content || ''))).join('\n');

  // SplitText
  const splitTextMatches = [...allCode.matchAll(/new\s+SplitText\s*\(\s*([^,)]+)\s*,\s*\{[^}]*type\s*:\s*["']([^"']+)["']/g)];
  if (splitTextMatches.length > 0) {
    pluginUsage.SplitText = splitTextMatches.map((m) => ({
      target: m[1].trim().replace(/["']/g, ''),
      type: m[2],
    }));
  }

  // Flip
  const flipMatches = [...allCode.matchAll(/Flip\.(getState|from|to|fit|isFlipping)\s*\(/g)];
  if (flipMatches.length > 0) {
    pluginUsage.Flip = flipMatches.map((m) => ({ method: m[1] }));
  }

  // DrawSVG
  const drawSVGMatches = [...allCode.matchAll(/drawSVG\s*:\s*["']?([^"',}]+)/g)];
  if (drawSVGMatches.length > 0) {
    pluginUsage.DrawSVG = drawSVGMatches.map((m) => ({ value: m[1].trim() }));
  }

  // MorphSVG
  const morphMatches = [...allCode.matchAll(/morphSVG\s*:\s*["']?([^"',}]+)/g)];
  if (morphMatches.length > 0) {
    pluginUsage.MorphSVG = morphMatches.map((m) => ({ shape: m[1].trim() }));
  }

  // MotionPath
  const motionPathMatches = [...allCode.matchAll(/motionPath\s*:\s*\{([^}]+)\}/g)];
  if (motionPathMatches.length > 0) {
    pluginUsage.MotionPath = motionPathMatches.map((m) => ({ config: m[1].trim() }));
  }

  // Draggable
  const draggableMatches = [...allCode.matchAll(/Draggable\.create\s*\(\s*([^,)]+)/g)];
  if (draggableMatches.length > 0) {
    pluginUsage.Draggable = draggableMatches.map((m) => ({
      target: m[1].trim().replace(/["']/g, ''),
    }));
  }

  // CustomEase
  const customEaseMatches = [...allCode.matchAll(/CustomEase\.create\s*\(\s*["']([^"']+)["']\s*,\s*["']([^"']+)["']/g)];
  if (customEaseMatches.length > 0) {
    pluginUsage.CustomEase = customEaseMatches.map((m) => ({ name: m[1], curve: m[2] }));
  }

  // ScrollSmoother
  const scrollSmootherMatches = [...allCode.matchAll(/ScrollSmoother\.create\s*\(/g)];
  if (scrollSmootherMatches.length > 0) {
    pluginUsage.ScrollSmoother = [{ detected: true, count: scrollSmootherMatches.length }];
  }

  // Observer
  const observerMatches = [...allCode.matchAll(/Observer\.create\s*\(/g)];
  if (observerMatches.length > 0) {
    pluginUsage.Observer = [{ detected: true, count: observerMatches.length }];
  }

  // ScrambleText (look for scrambleText property)
  const scrambleMatches = [...allCode.matchAll(/scrambleText\s*:\s*\{([^}]+)\}/g)];
  if (scrambleMatches.length > 0) {
    pluginUsage.ScrambleText = scrambleMatches.map((m) => ({ config: m[1].trim() }));
  }

  // matchMedia
  const matchMediaMatches = [...allCode.matchAll(/gsap\.matchMedia\s*\(\s*\)/g)];
  if (matchMediaMatches.length > 0) {
    pluginUsage.matchMedia = [{ detected: true, count: matchMediaMatches.length }];
  }

  return pluginUsage;
}

// ---------------------------------------------------------------------------
// Exported: Extract GSAP animation data from JS bundle URLs
// ---------------------------------------------------------------------------

/**
 * Download JS bundles from captured network URLs and extract GSAP animation
 * call parameters using regex + balanced-brace parsing.
 *
 * @param {string[]} bundleUrls - Array of JS bundle URLs (from network interception)
 * @returns {Promise<{calls: Array, bundlesAnalyzed: number, totalCalls: number}>}
 */
async function extractGsapFromBundles(bundleUrls) {
  // Filter to .js files only and cap at MAX_BUNDLES
  const jsUrls = bundleUrls
    .filter((u) => /\.js(\?|$)/.test(u))
    .slice(0, MAX_BUNDLES);

  console.log(`${TAG} Downloading ${jsUrls.length} bundles...`);

  // Download all bundles in parallel
  const contents = await Promise.all(jsUrls.map((url) => downloadBundle(url)));

  const allCalls = [];
  let bundlesAnalyzed = 0;

  for (let i = 0; i < jsUrls.length; i++) {
    const content = contents[i];
    if (!content) continue;

    bundlesAnalyzed++;
    const fileName = jsUrls[i].split('/').pop().split('?')[0];
    const calls = extractGsapCalls(content);
    console.log(`${TAG} Found ${calls.length} GSAP calls in ${fileName}`);
    allCalls.push(...calls);
  }

  // Deduplicate by target + method
  const seen = new Set();
  const deduped = [];
  for (const call of allCalls) {
    const key = `${call.method}::${call.targetSelector || ''}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(call);
  }

  const bundleContents = contents.filter(Boolean);
  const pluginUsage = classifyPluginUsage(bundleContents);

  return {
    calls: deduped,
    bundlesAnalyzed,
    totalCalls: deduped.length,
    pluginUsage,
  };
}

/**
 * Merge GSAP data from static bundle analysis and runtime interception.
 * Runtime calls take priority because they include elementY positions.
 * Static calls fill in any gaps not covered by runtime detection.
 *
 * @param {Array} staticCalls - Calls extracted from JS bundles (this module)
 * @param {Array} runtimeCalls - Calls captured at runtime (animation-detector.js)
 * @returns {Array} Merged and deduplicated call records
 */
function mergeGsapData(staticCalls, runtimeCalls) {
  // Index runtime calls by target+method for fast lookup
  const runtimeIndex = new Map();
  for (const call of runtimeCalls) {
    const key = `${call.method}::${call.targetSelector || ''}`;
    runtimeIndex.set(key, call);
  }

  // Start with all runtime calls
  const merged = [...runtimeCalls];

  // Add static calls that don't have a runtime counterpart
  for (const call of staticCalls) {
    const key = `${call.method}::${call.targetSelector || ''}`;
    if (!runtimeIndex.has(key)) {
      merged.push(call);
    }
  }

  return merged;
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------
module.exports = { extractGsapFromBundles, mergeGsapData, classifyPluginUsage };
