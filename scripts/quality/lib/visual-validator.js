'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const VIEWPORT = { width: 1440, height: 900 };
const SCROLL_SETTLE_MS = 1200;
const SERVER_STARTUP_TIMEOUT_MS = 30000;
const SERVER_POLL_INTERVAL_MS = 500;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Poll an HTTP endpoint until it responds with a 200-level status.
 * Resolves when the server is ready; rejects on timeout.
 */
function waitForServer(port, timeoutMs = SERVER_STARTUP_TIMEOUT_MS) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(`http://localhost:${port}`, (res) => {
        // Any response means the server is up (Next.js may 200 or 304)
        if (res.statusCode >= 200 && res.statusCode < 400) {
          resolve();
        } else {
          scheduleRetry();
        }
        res.resume(); // drain
      });

      req.on('error', () => {
        scheduleRetry();
      });

      req.setTimeout(2000, () => {
        req.destroy();
        scheduleRetry();
      });
    };

    const scheduleRetry = () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error(`Dev server did not start within ${timeoutMs}ms`));
        return;
      }
      setTimeout(check, SERVER_POLL_INTERVAL_MS);
    };

    check();
  });
}

/**
 * Start the Next.js dev server in the given project directory.
 * Returns the spawned child process once the server responds to HTTP.
 */
async function startDevServer(projectDir, port) {
  const child = spawn('npx', ['next', 'dev', '-p', String(port)], {
    cwd: projectDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: true, // allow process-group kill later
    shell: process.platform === 'win32',
  });

  // Surface early crashes
  let stderr = '';
  child.stderr.on('data', (chunk) => {
    stderr += chunk.toString();
  });

  child.on('error', (err) => {
    throw new Error(`Failed to spawn dev server: ${err.message}`);
  });

  // Wait until server is actually serving HTTP
  try {
    await waitForServer(port);
  } catch (err) {
    killProcess(child);
    throw new Error(
      `Dev server failed to start on port ${port}.\n` +
        `stderr: ${stderr.slice(-500)}\n` +
        `Original: ${err.message}`
    );
  }

  return child;
}

/**
 * Safely kill a child process. Tries killing the process group first
 * (covers any grandchild processes spawned by npx/next), then falls
 * back to killing the process directly.
 */
function killProcess(child) {
  if (!child || child.killed) return;

  try {
    // Kill the entire process group (negative PID)
    process.kill(-child.pid, 'SIGTERM');
  } catch (_ignored) {
    try {
      child.kill('SIGTERM');
    } catch (_alsoIgnored) {
      // already dead — nothing to do
    }
  }
}

/**
 * Use pixelmatch to compare two screenshots and write a diff image.
 *
 * Returns the diff percentage where 0 = identical and 1 = completely different.
 */
async function computeDiff(originalPath, generatedPath, diffOutputPath) {
  const sharp = require('sharp');
  const pixelmatch = require('pixelmatch');
  const { PNG } = require('pngjs');

  // Load images and get metadata
  const origMeta = await sharp(originalPath).metadata();
  const genMeta = await sharp(generatedPath).metadata();

  // Target the smaller of each axis so both images match exactly
  const width = Math.min(origMeta.width, genMeta.width);
  const height = Math.min(origMeta.height, genMeta.height);

  // Resize both to the common dimensions and extract raw RGBA pixels
  const origBuf = await sharp(originalPath)
    .resize(width, height, { fit: 'cover', position: 'left top' })
    .ensureAlpha()
    .raw()
    .toBuffer();

  const genBuf = await sharp(generatedPath)
    .resize(width, height, { fit: 'cover', position: 'left top' })
    .ensureAlpha()
    .raw()
    .toBuffer();

  // Run pixelmatch
  const diffPng = new PNG({ width, height });
  const numDiffPixels = pixelmatch(
    origBuf,
    genBuf,
    diffPng.data,
    width,
    height,
    {
      threshold: 0.1,
      includeAA: false, // ignore anti-aliasing differences
    }
  );

  // Write the diff image (red-highlighted)
  fs.mkdirSync(path.dirname(diffOutputPath), { recursive: true });
  fs.writeFileSync(diffOutputPath, PNG.sync.write(diffPng));

  const totalPixels = width * height;
  return totalPixels > 0 ? numDiffPixels / totalPixels : 0;
}

/**
 * Core comparison loop: scrolls through the page, captures viewport
 * screenshots aligned with each reference section, and diffs them.
 */
async function compareScreenshots(
  projectDir,
  referenceScreenshots,
  port,
  diffDir,
  iteration
) {
  const sharp = require('sharp');
  const { chromium } = require('playwright');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
  });
  const page = await context.newPage();

  await page.goto(`http://localhost:${port}`, {
    waitUntil: 'networkidle',
    timeout: 60000,
  });

  // Let any entrance animations settle
  await page.waitForTimeout(2000);

  // Measure full page height
  const pageHeight = await page.evaluate(() => document.body.scrollHeight);
  const totalSections = referenceScreenshots.length;

  const results = [];

  for (let i = 0; i < totalSections; i++) {
    const sectionName = `section-${i}`;
    const positionRatio = totalSections > 1 ? i / (totalSections - 1) : 0;

    // Scroll to the calculated position
    const scrollY = Math.round(positionRatio * Math.max(0, pageHeight - VIEWPORT.height));
    await page.evaluate((y) => window.scrollTo(0, y), scrollY);
    await page.waitForTimeout(SCROLL_SETTLE_MS);

    // Capture viewport screenshot
    const rawScreenshotPath = path.join(
      diffDir,
      `iter-${iteration}`,
      `${sectionName}-generated-raw.png`
    );
    fs.mkdirSync(path.dirname(rawScreenshotPath), { recursive: true });
    await page.screenshot({ path: rawScreenshotPath });

    // Determine the reference image dimensions so we can crop to match
    const refMeta = await sharp(referenceScreenshots[i]).metadata();
    const cropHeight = Math.min(refMeta.height, VIEWPORT.height);
    const cropWidth = Math.min(refMeta.width, VIEWPORT.width);

    const croppedScreenshotPath = path.join(
      diffDir,
      `iter-${iteration}`,
      `${sectionName}-generated.png`
    );

    await sharp(rawScreenshotPath)
      .extract({ left: 0, top: 0, width: cropWidth, height: cropHeight })
      .toFile(croppedScreenshotPath);

    // Diff against the reference
    const diffPath = path.join(
      diffDir,
      `iter-${iteration}`,
      `${sectionName}-diff.png`
    );
    const diffPercentage = await computeDiff(
      referenceScreenshots[i],
      croppedScreenshotPath,
      diffPath
    );

    results.push({
      name: sectionName,
      originalScreenshot: path.resolve(referenceScreenshots[i]),
      generatedScreenshot: path.resolve(croppedScreenshotPath),
      diffScreenshot: path.resolve(diffPath),
      diffPercentage,
    });

    // Clean up the raw (uncropped) capture
    try {
      fs.unlinkSync(rawScreenshotPath);
    } catch (_e) {
      // non-critical
    }
  }

  await browser.close();
  return results;
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

/**
 * Validate a generated Next.js build against reference section screenshots.
 *
 * @param {string} projectDir         Path to the generated Next.js project
 * @param {string[]} referenceScreenshots  Paths to reference section screenshots (ordered)
 * @param {object} [options]
 * @param {number} [options.maxIterations=2]   Max regeneration / re-comparison iterations
 * @param {number} [options.diffThreshold=0.25] Per-section diff threshold (0–1)
 * @param {number} [options.port=4567]         Port for the dev server
 *
 * @returns {Promise<object>} Validation report
 */
async function validateBuild(projectDir, referenceScreenshots, options = {}) {
  const {
    maxIterations = 2,
    diffThreshold = 0.25,
    port = 4567,
  } = options;

  const resolvedProjectDir = path.resolve(projectDir);
  const diffDir = path.join(resolvedProjectDir, '.quality', 'diffs');
  fs.mkdirSync(diffDir, { recursive: true });

  // ------------------------------------------------------------------
  // Step 1 — Install dependencies
  // ------------------------------------------------------------------
  await new Promise((resolve, reject) => {
    const install = spawn('npm', ['install'], {
      cwd: resolvedProjectDir,
      stdio: 'inherit',
      shell: process.platform === 'win32',
    });

    const timer = setTimeout(() => {
      install.kill('SIGTERM');
      reject(new Error('npm install timed out after 120 seconds'));
    }, 120_000);

    install.on('close', (code) => {
      clearTimeout(timer);
      if (code === 0) resolve();
      else reject(new Error(`npm install exited with code ${code}`));
    });

    install.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });
  });

  // ------------------------------------------------------------------
  // Step 2 — Start the dev server
  // ------------------------------------------------------------------
  const devServer = await startDevServer(resolvedProjectDir, port);

  let report;

  try {
    // ----------------------------------------------------------------
    // Step 3 — Iterative comparison
    // ----------------------------------------------------------------
    let bestResults = null;
    let iterations = 0;

    for (let iter = 0; iter < maxIterations; iter++) {
      iterations = iter;

      const sectionResults = await compareScreenshots(
        resolvedProjectDir,
        referenceScreenshots,
        port,
        diffDir,
        iter
      );

      // Tag each section with whether it needs regeneration
      for (const section of sectionResults) {
        section.needsRegeneration = section.diffPercentage > diffThreshold;
      }

      bestResults = sectionResults;

      // Check if all sections pass
      const failing = sectionResults.filter((s) => s.needsRegeneration);
      if (failing.length === 0) break;

      // If there are more iterations available, the caller could
      // regenerate sections here. For now we just record the results.
    }

    // ----------------------------------------------------------------
    // Step 4 — Compile the report
    // ----------------------------------------------------------------
    const sectionsNeedingFixes = bestResults.filter(
      (s) => s.needsRegeneration
    ).length;

    const avgSimilarity =
      bestResults.length > 0
        ? bestResults.reduce((sum, s) => sum + (1 - s.diffPercentage), 0) /
          bestResults.length
        : 1;

    const overallSimilarity = parseFloat(avgSimilarity.toFixed(4));
    const passed = overallSimilarity >= 1 - diffThreshold;

    report = {
      sections: bestResults,
      overallSimilarity,
      sectionsNeedingFixes,
      passed,
      iterations,
    };
  } finally {
    // ----------------------------------------------------------------
    // Step 5 — Tear down the dev server
    // ----------------------------------------------------------------
    killProcess(devServer);
  }

  return report;
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = { validateBuild };
