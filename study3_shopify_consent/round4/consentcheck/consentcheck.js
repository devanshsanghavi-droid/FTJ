#!/usr/bin/env node
// ConsentCheck: does your Shopify store's cookie banner actually control your ad pixels?
//
//   node consentcheck.js <store-page-url> [--out report.html] [--json report.json] [options]
//
// Loads one page of YOUR store three times, each in a fresh temporary browser profile:
//   Default  (no click), Decline (clicks only the banner's Decline/Reject, then reloads once), GPC (privacy signal on)
// and writes a single-file HTML report plus a JSON file. See README.md.
//
// Options
//   --out FILE          HTML report (default ./consentcheck-<host>-<date>.html)
//   --json FILE         JSON results (default: the HTML name with .json)
//   --yes               confirm non-interactively that you own the store or are authorised to test it
//   --arms LIST         subset of default,decline,gpc (default all three)
//   --utm QUERY         test tag appended to the page address (default utm_source=consentcheck&utm_medium=self-test&utm_campaign=consentcheck-<date>)
//   --no-tag            load the address exactly as given
//   --headed            show the browser window (still visibly automated)
//   --no-screenshots    leave the two Decline screenshots out of the report
//   --save-raw FILE     also save the raw capture (gzipped JSON) for re-analysis
//   --from-raw FILE     re-analyse a saved raw capture instead of visiting the store
//   --render FILE       re-render the HTML from a ConsentCheck JSON file
//   --min-free-gb N     refuse to start with less free disk than this (default 0.5)
// Exit codes: 0 report written; 1 error; 2 not confirmed; 3 robots.txt / unreachable; 4 low disk.
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const readline = require('readline');

const VERSION = '0.1.0';
const argv = process.argv.slice(2);
const flag = (k) => argv.includes(k);
const val = (k, d) => { const i = argv.indexOf(k); return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : d; };
const VALUED = new Set(['--out', '--json', '--arms', '--utm', '--save-raw', '--from-raw', '--render', '--min-free-gb']);
const positional = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && VALUED.has(argv[i - 1])));
const quiet = flag('--quiet');
const log = (m) => { if (!quiet) process.stderr.write(`${new Date().toISOString().slice(11, 19)} ${m}\n`); };

function usage(code) {
  process.stderr.write(fs.readFileSync(__filename, 'utf8').split('\n').slice(1, 22).map((l) => l.replace(/^\/\/ ?/, '')).join('\n') + '\n');
  process.exit(code);
}
function normUrl(u) {
  if (!/^https?:\/\//i.test(u)) u = 'https://' + u;
  const U = new URL(u);
  if (!U.pathname) U.pathname = '/';
  return U.toString();
}
function withTag(u, q) {
  if (!q) return u;
  const U = new URL(u);
  for (const [k, v] of new URLSearchParams(q)) if (!U.searchParams.has(k)) U.searchParams.append(k, v);
  return U.toString();
}
function defaultOut(host) { const d = new Date().toISOString().slice(0, 10); return path.resolve(`consentcheck-${host.replace(/[^a-z0-9.-]/gi, '_')}-${d}.html`); }
function freeGb(dir) { try { const s = fs.statfsSync(dir); return (s.bavail * s.bsize) / 1e9; } catch (e) { return Infinity; } }
async function confirm(host) {
  if (flag('--yes')) return true;
  if (!process.stdin.isTTY) { process.stderr.write('ConsentCheck tests only stores you own or are authorised to test. Re-run with --yes to confirm.\n'); return false; }
  const rl = readline.createInterface({ input: process.stdin, output: process.stderr });
  const a = await new Promise((r) => rl.question(`\nConsentCheck is for testing stores you own or are authorised to test.\nIt will load one page of ${host} about four times over ~2 minutes, click only the banner's\nDecline/Reject button, and never log in, add to cart or submit forms.\nDo you own ${host} or have permission to test it? [y/N] `, r));
  rl.close();
  return /^y(es)?$/i.test(a.trim());
}
function writeOutputs(res, htmlPath, jsonPath) {
  const { render } = require('./lib/render');
  fs.writeFileSync(jsonPath, JSON.stringify(res, null, 1));
  fs.writeFileSync(htmlPath, render(res));
  log(`report: ${htmlPath}`);
  log(`json:   ${jsonPath}`);
}

(async () => {
  if (flag('--help') || flag('-h')) usage(0);
  // ---- re-render only
  if (val('--render')) {
    const res = JSON.parse(fs.readFileSync(val('--render'), 'utf8'));
    const out = path.resolve(val('--out', val('--render').replace(/\.json$/, '') + '.html'));
    fs.writeFileSync(out, require('./lib/render').render(res));
    log(`report: ${out}`);
    process.exit(0);
  }
  const env = {};
  const E = require('./lib/env');
  env.lib = E.loadCrawlLib();
  const { analyze } = require('./lib/analyze');
  // ---- re-analyse a saved capture
  if (val('--from-raw')) {
    const raw = JSON.parse(zlib.gunzipSync(fs.readFileSync(val('--from-raw'))).toString('utf8'));
    const res = analyze(raw, env, raw.meta);
    const html = path.resolve(val('--out', defaultOut(raw.meta.host)));
    writeOutputs(res, html, path.resolve(val('--json', html.replace(/\.html?$/i, '') + '.json')));
    process.exit(0);
  }
  if (!positional.length) usage(1);
  let url;
  try { url = normUrl(positional[0]); } catch (e) { process.stderr.write(`Not a valid address: ${positional[0]}\n`); process.exit(1); }
  const host = new URL(url).hostname;
  const arms = (val('--arms', 'default,decline,gpc')).split(',').map((x) => x.trim()).filter((x) => ['default', 'decline', 'gpc'].includes(x));
  if (!arms.length) usage(1);
  const minFree = parseFloat(val('--min-free-gb', '0.5'));
  if (freeGb(os.tmpdir()) < minFree) { process.stderr.write(`Less than ${minFree} GB free disk; stopping.\n`); process.exit(4); }
  if (!(await confirm(host))) process.exit(2);
  env.pw = E.loadPlaywright();

  // ---- robots.txt, then the test tag
  const tag = flag('--no-tag') ? null : val('--utm', `utm_source=consentcheck&utm_medium=self-test&utm_campaign=consentcheck-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`);
  const { robotsGate } = require('./lib/robots');
  log(`checking ${new URL(url).origin}/robots.txt`);
  const gate = await robotsGate(withTag(url, tag), url);
  if (!gate.ok) { process.stderr.write(`Not loading: ${gate.reason}\n`); process.exit(3); }
  log(gate.reason);

  // ---- visits
  const { captureArm, Pacer } = require('./lib/capture');
  const pacer = new Pacer(10000, 1000);
  const opts = { headed: flag('--headed'), screenshots: !flag('--no-screenshots') };
  const started = new Date().toISOString();
  const armsOut = {};
  for (const arm of arms) {
    if (freeGb(os.tmpdir()) < minFree) { log('free disk fell below the limit; stopping early'); break; }
    log(`visit: ${arm}`);
    try { armsOut[arm] = await captureArm({ env, arm, url: gate.url, pacer, opts, log }); } catch (e) { armsOut[arm] = { arm, url: gate.url, errors: ['fatal:' + String(e).slice(0, 300)] }; }
    const r = armsOut[arm];
    log(`  [${arm}] HTTP ${r.goto_status ?? '—'}, ${r.n_requests ?? 0} requests${r.goto_error ? ', ' + r.goto_error : ''}`);
  }
  const meta = { version: VERSION, url, loaded_url: gate.url, host, started_at: started, ended_at: new Date().toISOString(), robots: { reason: gate.reason, robots_url: gate.robots.robots_url, status: gate.robots.status, group: gate.robots.group || null },
    navigations: pacer.navs, headed: opts.headed, crawl_lib_rel: path.relative(__dirname, env.lib.dir), playwright_version: env.pw.version };
  const raw = { meta, arms: armsOut };
  if (val('--save-raw')) { fs.writeFileSync(path.resolve(val('--save-raw')), zlib.gzipSync(JSON.stringify(raw))); log(`raw capture: ${path.resolve(val('--save-raw'))}`); }
  const res = analyze(raw, env, meta);
  const html = path.resolve(val('--out', defaultOut(host)));
  writeOutputs(res, html, path.resolve(val('--json', html.replace(/\.html?$/i, '') + '.json')));
  const hi = res.findings.filter((f) => f.severity === 'high').length; const med = res.findings.filter((f) => f.severity === 'medium').length;
  log(`done: ${hi} problem(s), ${med} warning(s)`);
  process.exit(0);
})().catch((e) => { process.stderr.write('ConsentCheck error: ' + (e && e.stack || e) + '\n'); process.exit(1); });
