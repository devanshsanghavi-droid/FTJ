// Offline self-test: feed the study crawl's saved captures (crawl/raw/<store>__A0/A1/A2.json.gz, read-only) through
// ConsentCheck's analysis and renderer, without visiting any site. Checks that the analysis runs on real data and
// lets its verdicts be compared with the crawl's store table for many stores at once.
//   node test/replay_crawl.js S1154 [S0001 ...] [--html DIR] [--csv FILE]
// Differences from a live ConsentCheck capture: crawl records carry no frame/worker ids, so leftover requests of an
// old sandbox after the reload cannot be told apart from a fresh page (all count as "fresh page"); frames nested
// inside a LAX iframe keep the crawl's 'subframe' label (main page), as in the crawl before the referee revision.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const E = require('../lib/env');
const { analyze } = require('../lib/analyze');
const { render } = require('../lib/render');

const RAW = path.join(E.STUDY, 'crawl', 'raw');
const args = process.argv.slice(2);
const val = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const ids = args.filter((a, i) => !a.startsWith('--') && !['--html', '--csv'].includes(args[i - 1]));
const env = { lib: E.loadCrawlLib() };

function cmpFromHeaders(h) { const m = /_cmp;desc="([^"]+)"/.exec((h && h['server-timing']) || ''); return m ? m[1] : null; }
function adapt(rec, arm) {
  if (!rec) return null;
  const o = Object.assign({}, rec, { arm });
  o.navigations = (rec.navigations || []).map((n) => ({ t: n.t, url: n.url, st: n.st, redirected: !!n.redirected, server_timing_cmp: cmpFromHeaders(n.headers) }));
  if (rec.wpm && rec.wpm.pixels) o.wpm = Object.assign({}, rec.wpm, { pixels: rec.wpm.pixels.map((p) => Object.assign({}, p, { id: String(p.id), pp: p.pp || [] })) });
  o.n_requests = (rec.requests || []).length;
  o.requests = (rec.requests || []).filter((q) => q.vendor || q.wpm).map((q) => {
    let pth = ''; try { pth = new URL(q.url).pathname; } catch (e) { /* ignore */ }
    return { t: q.t, container: null, c_first: undefined, host: q.host, path: pth, m: q.m, type: q.type, sess: q.sess, origin: q.origin, pixel: q.pixel, vendor: q.vendor, vkind: q.vkind, ad: q.ad, wpm: q.wpm, preflight: q.m === 'OPTIONS' || undefined, page_url: q.canary || undefined };
  });
  o.shots = {};
  return o;
}
const rows = [];
for (const id of ids) {
  const rd = (a) => { const f = path.join(RAW, `${id}__${a}.json.gz`); return fs.existsSync(f) ? JSON.parse(zlib.gunzipSync(fs.readFileSync(f)).toString('utf8')) : null; };
  const A0 = rd('A0'); const A1 = rd('A1'); const A2 = rd('A2');
  if (!A0) { console.error(id, 'no crawl record'); continue; }
  const raw = { arms: { default: adapt(A0, 'default'), decline: adapt(A1, 'decline'), gpc: adapt(A2, 'gpc') } };
  const host = (() => { try { return new URL(A0.url).hostname; } catch (e) { return id; } })();
  const meta = { version: 'replay', url: A0.url, loaded_url: A0.url, host, started_at: A0.started_at, ended_at: A2 && A2.started_at, robots: { reason: 'replay of the study crawl (no robots check at crawl time)' }, navigations: [], crawl_lib_rel: 'crawl/lib', playwright_version: null };
  const res = analyze(raw, env, meta);
  const vg = {};
  for (const v of res.vendors) { const g = v.group || 'Reddit/other'; vg[g] = vg[g] || { pre: false, pre_sbx: false, decl: false, gpc: false }; vg[g].pre ||= v.before_choice === 'sends'; vg[g].pre_sbx ||= v.before_choice === 'sends' && v.where_before.includes('sandbox'); vg[g].decl ||= v.decline === 'not_stopped'; vg[g].gpc ||= v.gpc === 'not_stopped'; }
  rows.push({ store_id: id, decline_status: res.store.decline.status, gpc_recorded: res.store.gpc.shopify_recorded_opt_out, region_allows: res.store.shopify_default ? res.store.shopify_default.marketing_allowed_before_choice : null,
    n_nopurpose: res.pixels.filter((p) => p.flags.no_purpose).length, vg: JSON.stringify(vg), findings: res.findings.map((f) => f.id).join('|') });
  if (val('--html')) { fs.mkdirSync(val('--html'), { recursive: true }); fs.writeFileSync(path.join(val('--html'), `${id}.html`), render(res)); }
  console.log(id, res.store.decline.status, 'findings:', res.findings.map((f) => `${f.severity}:${f.id}`).join(', '));
}
if (val('--csv')) {
  const keys = Object.keys(rows[0] || {});
  fs.writeFileSync(val('--csv'), [keys.join(',')].concat(rows.map((r) => keys.map((k) => '"' + String(r[k] ?? '').replace(/"/g, '""') + '"').join(','))).join('\n') + '\n');
}
