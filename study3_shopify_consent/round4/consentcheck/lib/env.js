// Locate the two things ConsentCheck reuses: Playwright, and the study crawler's instrumentation
// library (crawl/lib + crawl/vendor_endpoints.json + crawl/cmp_signatures.json).
//
// Search order (first hit wins):
//   Playwright : $CONSENTCHECK_PLAYWRIGHT, a normal `require('playwright')` (npm install), then the
//                study checkout's pilot/pixel_payloads/node_modules/playwright.
//   Crawl lib  : $CONSENTCHECK_CRAWL_LIB, ./vendor/crawl/lib (created by `node tools/vendor_lib.js` for a
//                standalone copy), then the study checkout's crawl/lib.
const fs = require('fs');
const path = require('path');

const HERE = path.resolve(__dirname, '..');
const STUDY = path.resolve(HERE, '..', '..');          // study3_shopify_consent/
const WORKSPACE = path.resolve(STUDY, '..');            // folder that holds pilot/ and study3_.../

function firstExisting(cands) { for (const c of cands) if (c && fs.existsSync(c)) return c; return null; }

function loadPlaywright() {
  const cands = [process.env.CONSENTCHECK_PLAYWRIGHT, null, path.join(WORKSPACE, 'pilot', 'pixel_payloads', 'node_modules', 'playwright')];
  for (const c of cands) {
    try {
      const pw = c ? require(c) : require('playwright');
      if (pw && pw.chromium) return { chromium: pw.chromium, from: c || 'playwright (node_modules)', version: pwVersion(c) };
    } catch (e) { /* try next */ }
  }
  throw new Error('Playwright not found. Run `npm install playwright && npx playwright install chromium`, or set CONSENTCHECK_PLAYWRIGHT to the playwright package folder.');
}
function pwVersion(dir) {
  try { const p = dir ? path.join(dir, 'package.json') : require.resolve('playwright/package.json'); return JSON.parse(fs.readFileSync(p, 'utf8')).version; } catch (e) { return null; }
}

function crawlLibDir() {
  const d = firstExisting([process.env.CONSENTCHECK_CRAWL_LIB, path.join(HERE, 'vendor', 'crawl', 'lib'), path.join(STUDY, 'crawl', 'lib')]);
  if (!d) throw new Error('Crawl instrumentation library not found. Set CONSENTCHECK_CRAWL_LIB or run `node tools/vendor_lib.js` inside the study checkout.');
  return d;
}

function loadCrawlLib() {
  const d = crawlLibDir();
  return {
    dir: d,
    rawcdp: require(path.join(d, 'rawcdp.js')),        // RawCDP, wsUrlFromUserDataDir, sleep
    instrument: require(path.join(d, 'instrument.js')), // Instrumenter (auto-attach to every page/frame/worker)
    inject: require(path.join(d, 'inject.js')),         // GPC_INJECT, GPC_VERIFY
    vendors: require(path.join(d, 'vendors.js')),       // vendor map, WPM URL patterns, payload flags
    probes: require(path.join(d, 'probes.js')),         // banner observer, CPAPI readout, Decline finder, CMP probe
  };
}

module.exports = { HERE, STUDY, loadPlaywright, loadCrawlLib, crawlLibDir };
