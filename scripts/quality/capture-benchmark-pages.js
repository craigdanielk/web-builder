// Capture Robinhood pages as benchmark source material.
// PATTERNS ONLY — downstream compile lifts no markup, copy, asset or SVG.
const path = require('path');
const fs = require('fs');
const { extractReference } = require(
  '/Users/craigkunte/Developer/GitHub/services/aurelix-ag/web-builder/scripts/quality/lib/extract-reference.js'
);

const OUT = '/private/tmp/claude-501/-Users-craigkunte-Developer-GitHub-services-aurelix-ag/1883096c-b247-43af-be4f-a5ca49b10cbd/scratchpad/rh';

// Each entry records WHY it is captured, so captured_from is provenanced.
const PAGES = [
  ['home', 'https://robinhood.com/us/en/', 'HERO, NAV, FOOTER, CTA, FEATURES, LOGO-BAR'],
  ['crypto', 'https://robinhood.com/eu/en/crypto/', 'PRODUCT-SHOWCASE, FEATURES, CTA'],
  ['about', 'https://robinhood.com/us/en/about-us/', 'ABOUT, TEAM, LOGO-BAR'],
  ['staking', 'https://robinhood.com/eu/en/crypto/staking/', 'HOW-IT-WORKS numbered steps'],
  ['btc', 'https://robinhood.com/eu/en/crypto/BTC/', 'PORTFOLIO, data-dense card system'],
  ['faq', 'https://robinhood.com/eu/en/support/articles/about-robinhood-crypto/', 'FAQ, TRUST-BADGES'],
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const index = [];
  for (const [slug, url, why] of PAGES) {
    const dir = path.join(OUT, slug);
    fs.mkdirSync(dir, { recursive: true });
    process.stderr.write(`\n=== ${slug} ${url}\n`);
    try {
      const res = await extractReference(url, dir);
      fs.writeFileSync(path.join(dir, 'extraction.json'), JSON.stringify(res, null, 2));
      const domLen = (res && res.dom && res.dom.length) || 0;
      index.push({ slug, url, why, ok: true, dom_elements: domLen });
      process.stderr.write(`    ok  dom=${domLen}\n`);
    } catch (e) {
      index.push({ slug, url, why, ok: false, error: String(e.message || e) });
      process.stderr.write(`    FAIL ${e.message}\n`);
    }
  }
  fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index, null, 2));
  console.log(JSON.stringify(index, null, 2));
})();
