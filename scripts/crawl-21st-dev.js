#!/usr/bin/env node
'use strict';

/**
 * 21st.dev Component Crawler
 *
 * Fetches ALL components from 21st.dev's public sitemap and registry API.
 * Downloads source code, dependencies, and metadata for each component.
 *
 * Usage: node scripts/crawl-21st-dev.js [--dry-run] [--filter animation]
 *
 * Output: skills/animation-components/21st-dev-library/
 *   ├── registry-full.json    (complete index of all downloaded components)
 *   ├── {username}/
 *   │   └── {component-name}.tsx
 *   └── ...
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const SITEMAP_URL = 'https://21st.dev/sitemap.xml';
const REGISTRY_BASE = 'https://21st.dev/r';
const OUTPUT_DIR = path.resolve(__dirname, '../skills/animation-components/21st-dev-library');
const CONCURRENCY = 5;           // parallel requests
const DELAY_MS = 200;            // delay between batches to be polite
const REQUEST_TIMEOUT = 15000;   // 15s per request

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

function fetchUrl(url, timeout) {
  timeout = timeout || REQUEST_TIMEOUT;
  return new Promise(function (resolve, reject) {
    var protocol = url.startsWith('https') ? https : http;
    var req = protocol.get(url, { timeout: timeout }, function (res) {
      // Follow redirects
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        fetchUrl(res.headers.location, timeout).then(resolve).catch(reject);
        return;
      }
      if (res.statusCode !== 200) {
        reject(new Error('HTTP ' + res.statusCode + ' for ' + url));
        res.resume();
        return;
      }
      var chunks = [];
      res.on('data', function (chunk) { chunks.push(chunk); });
      res.on('end', function () { resolve(Buffer.concat(chunks).toString('utf8')); });
      res.on('error', reject);
    });
    req.on('error', reject);
    req.on('timeout', function () { req.destroy(); reject(new Error('Timeout for ' + url)); });
  });
}

function sleep(ms) {
  return new Promise(function (resolve) { setTimeout(resolve, ms); });
}

// ---------------------------------------------------------------------------
// Sitemap parsing
// ---------------------------------------------------------------------------

function extractComponentUrls(sitemapXml) {
  var urls = [];
  // Match all <loc> tags containing /community/components/{user}/{name}
  var regex = /<loc>(https:\/\/21st\.dev\/community\/components\/([^/]+)\/([^<]+))<\/loc>/g;
  var match;
  while ((match = regex.exec(sitemapXml)) !== null) {
    urls.push({
      pageUrl: match[1],
      username: match[2],
      componentName: match[3],
      registryUrl: REGISTRY_BASE + '/' + match[2] + '/' + match[3],
    });
  }
  return urls;
}

// ---------------------------------------------------------------------------
// Component fetching
// ---------------------------------------------------------------------------

async function fetchComponent(entry) {
  try {
    var raw = await fetchUrl(entry.registryUrl);
    var data = JSON.parse(raw);
    return {
      pageUrl: entry.pageUrl,
      username: entry.username,
      componentName: entry.componentName,
      registryUrl: entry.registryUrl,
      success: true,
      data: {
        name: data.name || entry.componentName,
        type: data.type || 'registry:ui',
        dependencies: data.dependencies || [],
        registryDependencies: data.registryDependencies || [],
        files: (data.files || []).map(function (f) {
          return {
            path: f.path,
            content: f.content,
            type: f.type || '',
          };
        }),
        tailwind: data.tailwind || {},
      },
    };
  } catch (err) {
    return {
      pageUrl: entry.pageUrl,
      username: entry.username,
      componentName: entry.componentName,
      registryUrl: entry.registryUrl,
      success: false,
      error: err.message,
    };
  }
}

async function fetchBatch(entries, batchNum, totalBatches) {
  var results = await Promise.all(entries.map(fetchComponent));
  var succeeded = results.filter(function (r) { return r.success; }).length;
  var failed = results.filter(function (r) { return !r.success; }).length;
  process.stdout.write('  Batch ' + batchNum + '/' + totalBatches + ': ' + succeeded + ' ok, ' + failed + ' failed\r');
  return results;
}

// ---------------------------------------------------------------------------
// File writing
// ---------------------------------------------------------------------------

function saveComponent(result) {
  if (!result.success || !result.data.files || result.data.files.length === 0) return 0;

  var compDir = path.join(OUTPUT_DIR, result.username);
  fs.mkdirSync(compDir, { recursive: true });

  var filesWritten = 0;
  for (var i = 0; i < result.data.files.length; i++) {
    var file = result.data.files[i];
    if (!file.content) continue;
    // Use the component name as filename
    var ext = path.extname(file.path) || '.tsx';
    var filename = result.componentName + ext;
    var filepath = path.join(compDir, filename);
    fs.writeFileSync(filepath, file.content, 'utf8');
    filesWritten++;
  }
  return filesWritten;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  var args = process.argv.slice(2);
  var dryRun = args.indexOf('--dry-run') >= 0;
  var filterIdx = args.indexOf('--filter');
  var filterKeyword = filterIdx >= 0 ? args[filterIdx + 1] : null;

  console.log('=== 21st.dev Component Crawler ===\n');

  // Step 1: Fetch sitemap
  console.log('1. Fetching sitemap...');
  var sitemapXml;
  try {
    sitemapXml = await fetchUrl(SITEMAP_URL);
  } catch (err) {
    console.error('   Failed to fetch sitemap: ' + err.message);
    process.exit(1);
  }

  // Step 2: Extract component URLs
  var components = extractComponentUrls(sitemapXml);
  console.log('   Found ' + components.length + ' components in sitemap');

  // Optional filter
  if (filterKeyword) {
    var kw = filterKeyword.toLowerCase();
    var animationKeywords = [
      'animate', 'animation', 'fade', 'slide', 'scroll', 'hover', 'parallax',
      'marquee', 'typewriter', 'reveal', 'stagger', 'float', 'glow', 'blur',
      'magnetic', 'tilt', 'counter', 'count', 'motion', 'entrance', 'transition',
      'kinetic', 'wobble', 'bounce', 'pulse', 'shimmer', 'gradient', 'morph',
      'flip', 'rotate', 'scale', 'zoom', 'wave', 'ripple', 'split', 'hero',
      'card', 'text-effect', 'aurora', 'particle', 'trail', 'cursor', 'shader',
      'confetti', 'loader', 'spinner', 'skeleton', 'number', 'flow',
    ];
    if (kw === 'animation') {
      components = components.filter(function (c) {
        return animationKeywords.some(function (k) { return c.componentName.includes(k); });
      });
    } else {
      components = components.filter(function (c) { return c.componentName.includes(kw); });
    }
    console.log('   After filter "' + filterKeyword + '": ' + components.length + ' components');
  }

  if (dryRun) {
    console.log('\n   [DRY RUN] Would fetch these components:\n');
    for (var d = 0; d < Math.min(components.length, 30); d++) {
      console.log('   ' + components[d].username + '/' + components[d].componentName + ' -> ' + components[d].registryUrl);
    }
    if (components.length > 30) {
      console.log('   ... and ' + (components.length - 30) + ' more');
    }
    console.log('\n   Total: ' + components.length + ' components');
    return;
  }

  // Step 3: Create output directory
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  // Step 4: Fetch all components in batches
  console.log('\n2. Fetching ' + components.length + ' components (concurrency: ' + CONCURRENCY + ')...');
  var allResults = [];
  var batches = [];
  for (var i = 0; i < components.length; i += CONCURRENCY) {
    batches.push(components.slice(i, i + CONCURRENCY));
  }

  for (var b = 0; b < batches.length; b++) {
    var batchResults = await fetchBatch(batches[b], b + 1, batches.length);
    allResults = allResults.concat(batchResults);
    if (b < batches.length - 1) await sleep(DELAY_MS);
  }

  console.log(''); // clear the \r line

  // Step 5: Save components
  console.log('\n3. Saving components...');
  var totalFiles = 0;
  var totalSuccess = 0;
  var totalFailed = 0;
  var failedComponents = [];

  for (var s = 0; s < allResults.length; s++) {
    var result = allResults[s];
    if (result.success) {
      var written = saveComponent(result);
      totalFiles += written;
      if (written > 0) totalSuccess++;
    } else {
      totalFailed++;
      failedComponents.push({
        name: result.username + '/' + result.componentName,
        error: result.error,
      });
    }
  }

  // Step 6: Build registry index
  console.log('4. Building registry index...');
  var registryIndex = {
    version: '1.0.0',
    crawledAt: new Date().toISOString(),
    source: '21st.dev',
    totalComponents: allResults.length,
    successfulDownloads: totalSuccess,
    failedDownloads: totalFailed,
    components: {},
  };

  for (var r = 0; r < allResults.length; r++) {
    var res = allResults[r];
    if (!res.success) continue;
    var key = res.username + '/' + res.componentName;
    registryIndex.components[key] = {
      name: res.data.name,
      username: res.username,
      slug: res.componentName,
      dependencies: res.data.dependencies,
      registryDependencies: res.data.registryDependencies,
      files: res.data.files.map(function (f) {
        return {
          path: f.path,
          localPath: res.username + '/' + res.componentName + (path.extname(f.path) || '.tsx'),
        };
      }),
      tailwind: res.data.tailwind,
      pageUrl: res.pageUrl,
      registryUrl: res.registryUrl,
    };
  }

  var registryPath = path.join(OUTPUT_DIR, 'registry-full.json');
  fs.writeFileSync(registryPath, JSON.stringify(registryIndex, null, 2), 'utf8');

  // Step 7: Summary
  console.log('\n=== Summary ===');
  console.log('  Components in sitemap: ' + components.length);
  console.log('  Successfully downloaded: ' + totalSuccess);
  console.log('  Failed: ' + totalFailed);
  console.log('  Files written: ' + totalFiles);
  console.log('  Registry index: ' + registryPath);
  console.log('  Library dir: ' + OUTPUT_DIR);

  if (failedComponents.length > 0 && failedComponents.length <= 20) {
    console.log('\n  Failed components:');
    for (var f = 0; f < failedComponents.length; f++) {
      console.log('    - ' + failedComponents[f].name + ': ' + failedComponents[f].error);
    }
  } else if (failedComponents.length > 20) {
    console.log('\n  ' + failedComponents.length + ' failures (see failures.json for details)');
  }

  // Write failures log
  if (failedComponents.length > 0) {
    var failLog = path.join(OUTPUT_DIR, 'failures.json');
    fs.writeFileSync(failLog, JSON.stringify(failedComponents, null, 2), 'utf8');
  }

  console.log('\nDone!');
}

main().catch(function (err) {
  console.error('Fatal error:', err);
  process.exit(1);
});
