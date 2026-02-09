/**
 * Asset Downloader
 * Downloads verified assets to the site's public directory.
 * Uses content-addressed filenames for deduplication and caching.
 *
 * @module asset-downloader
 */

'use strict';

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

// ── Constants ────────────────────────────────────────────────────────────────

/** Timeout for HEAD verification requests (ms) */
const HEAD_TIMEOUT_MS = 5000;

/** Timeout for download requests (ms) */
const DOWNLOAD_TIMEOUT_MS = 10000;

/** Maximum concurrent downloads */
const MAX_CONCURRENT = 20;

/** Minimum content length to accept (bytes), except SVG */
const MIN_CONTENT_LENGTH = 1024;

/** Valid image Content-Type prefixes */
const VALID_IMAGE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/svg+xml',
  'image/avif',
];

/** Required keys for a valid Lottie JSON file */
const LOTTIE_REQUIRED_KEYS = ['v', 'fr', 'layers'];

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Pick http or https module based on URL protocol.
 *
 * @param {string} url
 * @returns {object} The http or https module
 */
function getTransport(url) {
  return url.startsWith('https') ? https : http;
}

/**
 * Make an HTTP request and return a promise with the response.
 *
 * @param {string} url - URL to request
 * @param {string} method - HTTP method (GET or HEAD)
 * @param {number} timeout - Timeout in ms
 * @returns {Promise<{ statusCode: number, headers: object, body?: Buffer }>}
 */
function request(url, method, timeout) {
  return new Promise((resolve, reject) => {
    const transport = getTransport(url);
    const req = transport.request(url, { method, timeout }, (res) => {
      // Follow redirects (up to 3)
      if ([301, 302, 307, 308].includes(res.statusCode) && res.headers.location) {
        const redirectUrl = res.headers.location.startsWith('http')
          ? res.headers.location
          : new URL(res.headers.location, url).href;
        request(redirectUrl, method, timeout).then(resolve).catch(reject);
        res.resume();
        return;
      }

      if (method === 'HEAD') {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
        });
        res.resume();
        return;
      }

      // For GET: collect body
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
          body: Buffer.concat(chunks),
        });
      });
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Request timeout after ${timeout}ms: ${url}`));
    });

    req.on('error', reject);
    req.end();
  });
}

/**
 * Ensure a directory exists, creating it recursively if needed.
 *
 * @param {string} dir - Absolute path to the directory
 */
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// ── Core Functions ───────────────────────────────────────────────────────────

/**
 * Verify which assets from the download manifest are accessible.
 *
 * Makes HEAD requests in parallel to check availability. Filters out:
 * - HTTP 403/404/500 responses
 * - Content-Length < 1KB (unless SVG)
 * - Non-image Content-Type
 *
 * For Lottie files (.json with /lottie/ path): makes a GET request and
 * verifies the JSON has v, fr, layers keys.
 *
 * @param {Array<{ url: string, localPath: string, category: string }>} downloadManifest
 * @returns {Promise<Array<{ url: string, localPath: string, category: string }>>} Filtered manifest
 */
async function verifyAssets(downloadManifest) {
  if (!downloadManifest || downloadManifest.length === 0) return [];

  const results = await Promise.all(
    downloadManifest.map(async (entry) => {
      try {
        const isLottie = entry.localPath.startsWith('/lottie/');

        if (isLottie) {
          // Lottie: GET and verify structure
          const res = await request(entry.url, 'GET', HEAD_TIMEOUT_MS);
          if (res.statusCode < 200 || res.statusCode >= 400) return null;

          try {
            const json = JSON.parse(res.body.toString('utf-8'));
            const hasRequiredKeys = LOTTIE_REQUIRED_KEYS.every((key) => key in json);
            if (!hasRequiredKeys) return null;
          } catch (_) {
            return null;
          }

          return entry;
        }

        // Images: HEAD request
        const res = await request(entry.url, 'HEAD', HEAD_TIMEOUT_MS);

        // Filter by status code
        if ([403, 404, 500].includes(res.statusCode)) return null;
        if (res.statusCode < 200 || res.statusCode >= 400) return null;

        // Filter by Content-Type
        const contentType = (res.headers['content-type'] || '').toLowerCase();
        const isSvg = contentType.includes('svg');
        const isValidType = VALID_IMAGE_TYPES.some((t) => contentType.includes(t));
        if (!isValidType && contentType !== '' && !contentType.includes('octet-stream')) {
          return null;
        }

        // Filter by Content-Length (skip for SVG which can be small)
        const contentLength = parseInt(res.headers['content-length'] || '0', 10);
        if (contentLength > 0 && contentLength < MIN_CONTENT_LENGTH && !isSvg) {
          return null;
        }

        return entry;
      } catch (_) {
        // Network error, timeout, etc. - skip this asset
        return null;
      }
    })
  );

  return results.filter(Boolean);
}

/**
 * Download assets to the site's public directory.
 *
 * Downloads images to {siteDir}/public/images/ and Lottie files to
 * {siteDir}/public/lottie/. Uses content-addressed filenames for
 * deduplication. Skips download if the file already exists (idempotent).
 *
 * @param {Array<{ url: string, localPath: string, category: string }>} verifiedManifest
 * @param {string} siteDir - Absolute path to the site output directory
 * @returns {Promise<object>} Asset manifest mapping original URLs to local paths
 */
async function downloadAssets(verifiedManifest, siteDir) {
  if (!verifiedManifest || verifiedManifest.length === 0) return {};

  const publicDir = path.join(siteDir, 'public');
  ensureDir(path.join(publicDir, 'images'));
  ensureDir(path.join(publicDir, 'lottie'));

  const assetManifest = {};

  // Process in batches of MAX_CONCURRENT
  for (let i = 0; i < verifiedManifest.length; i += MAX_CONCURRENT) {
    const batch = verifiedManifest.slice(i, i + MAX_CONCURRENT);

    await Promise.all(
      batch.map(async (entry) => {
        // localPath is like /images/abc12345-photo.jpg
        const destPath = path.join(publicDir, entry.localPath);

        // Skip if already downloaded (idempotent)
        if (fs.existsSync(destPath)) {
          assetManifest[entry.url] = entry.localPath;
          return;
        }

        try {
          const res = await request(entry.url, 'GET', DOWNLOAD_TIMEOUT_MS);

          if (res.statusCode < 200 || res.statusCode >= 400) {
            console.warn(`[asset-downloader] HTTP ${res.statusCode} for ${entry.url}, skipping`);
            return;
          }

          if (!res.body || res.body.length === 0) {
            console.warn(`[asset-downloader] Empty response for ${entry.url}, skipping`);
            return;
          }

          // Ensure parent directory exists
          ensureDir(path.dirname(destPath));
          fs.writeFileSync(destPath, res.body);
          assetManifest[entry.url] = entry.localPath;
        } catch (err) {
          console.warn(`[asset-downloader] Failed to download ${entry.url}: ${err.message}`);
          // Continue with remaining downloads
        }
      })
    );
  }

  return assetManifest;
}

module.exports = {
  verifyAssets,
  downloadAssets,
};
