// Round 4 (B1 expansion, B2 beyond-Shopify) measurement crawl: a THIN WRAPPER around crawl/crawl.js.
//
// crawl/crawl.js is not edited. This script reads its source, applies a few asserted text substitutions (listed
// below), and runs it as crawl/crawl.js (same __dirname, same lib/ modules, same runLoad/buildRequests/scheduler),
// so the per-load method (fresh profile, arms, banner detector, Decline-only clicker, GPC injection, CDP
// auto-attach, pacing gate) is byte-identical to the Part A crawl.
//
// Substitutions (each must match exactly once or the run aborts):
//   S1 plan      `const plan = buildPlan();` -> the Round 4 plan (plan_r4.json made by --prepare), built with
//                crawl.js's own withCanary / regDom / mulberry32 / shuffle helpers; arms A0, A1, A2 only
//                (no A0r/A2r/V1), order shuffled per site with seed 20260927.
//   S2 STOP      the STOP file is looked up in the output dir (not crawl/).
//   S3 (beyond only) buildRequests keeps the full URL + body for requests that match a first-party rule of
//                round4/beyond/vendor_endpoints_extra.json (or are same-site POSTs), and writes `setck`, the
//                NAMES of cookies set by each response (Network.responseReceivedExtraInfo; values never kept).
// Monkey patches (beyond only; the Part A modules are untouched on disk):
//   P1 Instrumenter._net also records Set-Cookie names (responseReceivedExtraInfo).
//   P2 probes.CONSENT_READ also returns `b2`: Partytown config and script counts, Zaraz consent API state, Wix
//      consent policy / gdprEnforcedGeo, BigCommerce consentManagerStoreConfig and held-back script counts,
//      consent-cookie names, TCF/GPP presence (PROTOCOL.md section 5 'Readouts').
//
// Usage (cwd anywhere):
//   node crawl_r4.js --set expansion|beyond --prepare     robots.txt + (expansion) product-URL resolution -> plan_r4.json
//   node crawl_r4.js --set expansion|beyond --plan-check  print the plan, no network
//   node crawl_r4.js --set expansion|beyond [--conc 6]    run (resumable: skips loads whose raw file exists)
//   touch <outdir>/STOP                                   stop after the loads in flight
// Outputs: round4/<set>/crawl/{plan_r4.json, raw/, screenshots/, logs/}
'use strict';
const fs = require('fs');
const path = require('path');
const Module = require('module');

const args = process.argv.slice(2);
const argVal = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const SET = argVal('--set', '');
if (!['expansion', 'beyond'].includes(SET)) { console.error('--set expansion|beyond'); process.exit(2); }
const STUDY = path.resolve(__dirname, '..', '..', '..');
const CRAWL_DIR = path.join(STUDY, 'crawl');
const R4 = path.join(STUDY, 'round4');
const OUTDIR = process.env.R4_TEST_OUT || path.join(R4, SET, 'crawl'); // R4_TEST_OUT: offline self-test only
const PLAN = path.join(OUTDIR, 'plan_r4.json');
const SEED_R4 = 20260927;
const MIN_FREE = 1.2e9;
fs.mkdirSync(path.join(OUTDIR, 'logs'), { recursive: true });

// ------------------------------------------------------------------ helpers (no network)
function parseCSV(fn) {
  const txt = fs.readFileSync(fn, 'utf8');
  const rows = []; let row = []; let f = ''; let q = false;
  for (let i = 0; i < txt.length; i++) {
    const c = txt[i];
    if (q) { if (c === '"') { if (txt[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
    else if (c === '"') q = true; else if (c === ',') { row.push(f); f = ''; } else if (c === '\n') { row.push(f); rows.push(row); row = []; f = ''; } else if (c !== '\r') f += c;
  }
  if (f.length || row.length) { row.push(f); rows.push(row); }
  const h = rows.shift();
  return rows.filter((r) => r.length === h.length).map((r) => Object.fromEntries(h.map((k, i) => [k, r[i]])));
}
const ARCH_CODE = { partytown: 'PT', zaraz: 'ZZ', gateway: 'GW', wix: 'WX', bigcommerce: 'BC' };
function sites() {
  if (SET === 'expansion') {
    return parseCSV(path.join(R4, 'expansion', 'candidates.csv')).map((r) => ({
      store_id: r.store_id, stratum: 'expansion', domain: r.domain, host: r.final_host || r.domain, product_url: r.product_url || '',
      product_url_source: r.product_url_source, rank: +r.rank, cmp: r.cmp, prechoice_ca: r.prechoice_ca, age_gate_hint: r.age_gate_hint, weight: +r.weight,
    }));
  }
  return parseCSV(path.join(R4, 'beyond', 'candidates.csv')).filter((r) => r.selection === 'selected').map((r) => ({
    store_id: `b2-${ARCH_CODE[r.architecture]}${String(r.selection_order).padStart(3, '0')}`, stratum: 'b2_' + r.architecture, architecture: r.architecture,
    domain: r.domain, host: new URL(r.measure_url).hostname, product_url: r.measure_url, product_url_source: r.measure_url === r.homepage_url ? 'homepage' : 'product_page',
    rank: +r.tranco_rank, tier: r.tier, screen_stratum: r.screen_stratum, cmp: r.cmps,
  }));
}
function freeBytes() { try { const s = fs.statfsSync(OUTDIR); return s.bavail * s.bsize; } catch (e) { return Infinity; } }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const logf = path.join(OUTDIR, 'logs', 'prepare.jsonl');

// ------------------------------------------------------------------ --prepare (network: robots.txt, products.json)
async function fetchT(url, ms = 15000) {
  const ac = new AbortController(); const to = setTimeout(() => ac.abort(), ms);
  try { const r = await fetch(url, { redirect: 'follow', signal: ac.signal }); const text = r.status === 200 ? (await r.text()).slice(0, 2000000) : null; return { status: r.status, final: r.url, text }; }
  catch (e) { return { status: null, error: String((e && e.name) || e) }; } finally { clearTimeout(to); }
}
async function prepare() {
  const RB = require(path.join(R4, 'consentcheck', 'lib', 'robots.js')); // RFC 9309 parse/rulesFor/check (tokens consentcheck, headlesschrome; else '*')
  const withCanary = (u, sid) => { // identical to crawl.js withCanary
    const c = `utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-${sid}`;
    const hashI = u.indexOf('#'); const base = hashI >= 0 ? u.slice(0, hashI) : u; const hash = hashI >= 0 ? u.slice(hashI) : '';
    return base + (base.includes('?') ? (base.endsWith('?') || base.endsWith('&') ? '' : '&') : '?') + c + hash;
  };
  const S = sites();
  const prev = fs.existsSync(PLAN) ? JSON.parse(fs.readFileSync(PLAN, 'utf8')) : { sites: [] };
  const done = new Map(prev.sites.map((s) => [s.store_id, s]));
  const robotsCache = new Map();
  const out = [];
  let lastReq = 0;
  const gate = async () => { const d = 1000 - (Date.now() - lastReq); if (d > 0) await sleep(d); lastReq = Date.now(); }; // <= 1 request / s overall
  for (const s of S) {
    if (done.has(s.store_id)) { out.push(done.get(s.store_id)); continue; }
    if (freeBytes() < MIN_FREE) { console.log('DISK_LOW'); break; }
    if (fs.existsSync(path.join(OUTDIR, 'STOP'))) break;
    const rec = Object.assign({}, s, { prepared_at: new Date().toISOString() });
    let page = s.product_url;
    const origin0 = page ? new URL(page).origin : `https://${s.host}`;
    // robots.txt of the page's origin (once per origin)
    let rb = robotsCache.get(origin0);
    if (!rb) { await gate(); const g = await fetchT(origin0 + '/robots.txt'); rb = { status: g.status, error: g.error || null, rules: null, group: null };
      if (g.status === 200) { const x = RB.rulesFor(RB.parse(g.text)); rb.rules = x.rules; rb.group = x.group; } robotsCache.set(origin0, rb); }
    rec.robots = { url: origin0 + '/robots.txt', status: rb.status, error: rb.error, group: rb.group };
    const allowed = (u) => { if (rb.status === null || rb.status >= 500) return { allowed: false, rule: 'robots_unreachable' }; if (rb.status >= 400 || !rb.rules) return { allowed: true, rule: 'robots_' + rb.status };
      const x = new URL(u); return RB.check(rb.rules, x.pathname + x.search); };
    if (rb.status === null || rb.status >= 500) { rec.decision = 'skip_robots_unreachable'; out.push(rec); fs.appendFileSync(logf, JSON.stringify(rec) + '\n'); continue; }
    // expansion stores without a product URL: one /products.json?limit=1 request (as the main sample), else homepage
    if (!page) {
      const pj = `${origin0}/products.json?limit=1`;
      rec.product_resolution = { tried: 'products.json', allowed: allowed(pj).allowed };
      if (rec.product_resolution.allowed) {
        await gate(); const g = await fetchT(pj); rec.product_resolution.status = g.status;
        try { const h = JSON.parse(g.text).products[0].handle; if (h) { page = `${origin0}/products/${encodeURIComponent(h)}`; rec.product_url_source = 'products_json_r4'; } } catch (e) { /* none */ }
      }
      if (!page) { page = origin0 + '/'; rec.product_url_source = 'homepage_fallback_r4'; }
      rec.product_url = page;
    }
    const tagged = withCanary(page, s.store_id);
    const t = allowed(tagged); const p = allowed(page);
    rec.robots.tagged = t; rec.robots.plain = p;
    if (t.allowed) { rec.decision = 'load_tagged'; rec.load_url = tagged; }
    else if (p.allowed) { rec.decision = 'load_plain'; rec.load_url = page; }
    else if (SET === 'beyond' && s.product_url_source === 'product_page') {
      // PROTOCOL.md 5: the homepage when the product page is not allowed
      const home = `${origin0}/`; const th = allowed(withCanary(home, s.store_id)); const ph = allowed(home);
      if (th.allowed) { rec.decision = 'load_tagged_homepage'; rec.load_url = withCanary(home, s.store_id); rec.product_url = home; rec.product_url_source = 'homepage_robots'; }
      else if (ph.allowed) { rec.decision = 'load_plain_homepage'; rec.load_url = home; rec.product_url = home; rec.product_url_source = 'homepage_robots'; }
      else rec.decision = 'skip_robots_disallow';
    } else rec.decision = 'skip_robots_disallow';
    out.push(rec);
    fs.appendFileSync(logf, JSON.stringify({ id: rec.store_id, decision: rec.decision, robots: rec.robots.status, src: rec.product_url_source, at: rec.prepared_at }) + '\n');
    fs.writeFileSync(PLAN, JSON.stringify({ set: SET, seed: SEED_R4, prepared: new Date().toISOString(), sites: out.concat(S.filter((x) => !out.some((o) => o.store_id === x.store_id) && done.has(x.store_id)).map((x) => done.get(x.store_id))) }, null, 1));
  }
  fs.writeFileSync(PLAN, JSON.stringify({ set: SET, seed: SEED_R4, prepared: new Date().toISOString(), sites: out }, null, 1));
  const c = {}; for (const r of out) c[r.decision] = (c[r.decision] || 0) + 1;
  console.log('prepared', out.length, 'of', S.length, c);
}

// ------------------------------------------------------------------ beyond-only additions
function beyondPatches() {
  const EX = JSON.parse(fs.readFileSync(path.join(R4, 'beyond', 'vendor_endpoints_extra.json'), 'utf8'));
  const py2js = (s) => (s ? s.replace(/\(\?P</g, '(?<') : s);
  const rules = EX.first_party_rules.filter((r) => r.path_regex || r.query_regex || r.host_regex).map((r) => ({ id: r.id, p: r.path_regex ? new RegExp(py2js(r.path_regex)) : null, q: r.query_regex ? new RegExp(py2js(r.query_regex)) : null, h: r.host_regex ? new RegExp(py2js(r.host_regex)) : null }));
  const gw = EX.vendors.filter((v) => v.vendor_class === 'tag_gateway_host').map((v) => new RegExp(py2js(v.host_regex)));
  const regDom = (h) => { h = (h || '').replace(/^www\./, '').toLowerCase(); const parts = h.split('.'); if (parts.length <= 2) return h; return /\.(co|com|net|org|gov|edu|ac)\.[a-z]{2}$/.test(h) ? parts.slice(-3).join('.') : parts.slice(-2).join('.'); };
  global.__R4.keep = (url, host, storeHost, hasBody) => {
    let U; try { U = new URL(url); } catch (e) { return false; }
    const same = regDom(host) === regDom(storeHost); const gwh = gw.some((r) => r.test(host));
    if (!same && !gwh && !/[?&](url|u|target)=https?%3A%2F%2F/i.test(U.search)) return false;
    if (hasBody) return true;
    const q = U.search.replace(/^\?/, '');
    return rules.some((r) => (!r.p || r.p.test(U.pathname)) && (!r.q || r.q.test(q)) && (!r.h || r.h.test(host)) && (r.p || r.q || r.h));
  };
  // P1: Set-Cookie names per response
  const { Instrumenter } = require(path.join(CRAWL_DIR, 'lib', 'instrument.js'));
  const orig = Instrumenter.prototype._net;
  Instrumenter.prototype._net = function (method, p, sid) {
    if (method === 'Network.responseReceivedExtraInfo') {
      const h = p.headers || {}; let sc = null; for (const [k, v] of Object.entries(h)) if (k.toLowerCase() === 'set-cookie') sc = v;
      if (sc) {
        const names = String(sc).split('\n').map((l) => l.split('=')[0].trim()).filter(Boolean).slice(0, 30);
        const k = this._key(sid, p.requestId); const r = this.reqs.get(k);
        if (r) r.setck = names; else { const ex = this.extra.get(k) || {}; ex.setck = names; this.extra.set(k, ex); }
      }
      return undefined;
    }
    return orig.call(this, method, p, sid);
  };
  // P2: architecture readouts at every consent checkpoint
  const P = require(path.join(CRAWL_DIR, 'lib', 'probes.js'));
  const B2 = function () {
    const r = {};
    try {
      const pt = window.partytown; const n1 = document.querySelectorAll('script[type="text/partytown"]').length; const n2 = document.querySelectorAll('script[type="text/partytown-x"]').length;
      if (pt || n1 || n2) r.pt = { cfg: !!pt, fwd: pt && Array.isArray(pt.forward) ? pt.forward.map((f) => (Array.isArray(f) ? f[0] : f)).slice(0, 20) : null, resolveUrl: !!(pt && typeof pt.resolveUrl === 'function'), lib: pt && pt.lib ? String(pt.lib).slice(0, 80) : null, n: n1, nx: n2 };
    } catch (e) { r.pt_err = String(e).slice(0, 60); }
    try {
      const z = window.zaraz;
      if (z || window.zarazData) {
        r.zz = { loaded: !!z };
        const c = z && z.consent;
        if (c) { r.zz.ready = !!c.APIReady; try { r.zz.all = c.getAll ? JSON.parse(JSON.stringify(c.getAll())) : null; } catch (e) { r.zz.all = 'err'; }
          try { r.zz.purposes = c.purposes ? Object.entries(c.purposes).slice(0, 20).map(([k, v]) => [k, v && v.name ? String(v.name).slice(0, 40) : null]) : null; } catch (e) { /* ignore */ } }
      }
    } catch (e) { r.zz_err = String(e).slice(0, 60); }
    try { const w = window.consentPolicyManager; if (w && typeof w.getCurrentConsentPolicy === 'function') { const p = w.getCurrentConsentPolicy(); r.wx = { policy: p ? JSON.parse(JSON.stringify(p.policy || null)) : null, def: p ? p.defaultPolicy : null }; } } catch (e) { r.wx_err = String(e).slice(0, 60); }
    try { const tm = window.wixTagManager; if (tm && typeof tm.getConfig === 'function') { const c = tm.getConfig(); r.wx = r.wx || {}; r.wx.gdprGeo = c ? c.gdprEnforcedGeo : null; } } catch (e) { /* ignore */ }
    try {
      const f = window.consentManagerStoreConfig;
      const held = document.querySelectorAll('script[data-bc-cookie-consent]');
      if (f || held.length) {
        r.bc = { cfg: null, held: {} };
        if (typeof f === 'function') { try { r.bc.cfg = JSON.stringify(f()).slice(0, 600); } catch (e) { r.bc.cfg = 'err'; } }
        for (const s of held) { const k = s.getAttribute('data-bc-cookie-consent') + ':' + (s.type || 'js'); r.bc.held[k] = (r.bc.held[k] || 0) + 1; }
      }
    } catch (e) { r.bc_err = String(e).slice(0, 60); }
    try { r.ck = document.cookie.split(';').map((s) => s.split('=')[0].trim()).filter((n) => /consent|cookie|policy|cf_/i.test(n)).slice(0, 20); } catch (e) { /* ignore */ }
    try { r.tcf = typeof window.__tcfapi === 'function'; r.gpp = typeof window.__gpp === 'function'; } catch (e) { /* ignore */ }
    return r;
  };
  const combined = `function CONSENT_READ_R4() { const o = (${P.CONSENT_READ.toString()})(); try { o.b2 = (${B2.toString()})(); } catch (e) { o.b2_err = String(e).slice(0, 80); } return o; }`;
  P.CONSENT_READ = new Function(`return (${combined});`)(); // eslint-disable-line no-new-func
}

// ------------------------------------------------------------------ run crawl.js with the Round 4 plan
function run() {
  if (!fs.existsSync(PLAN)) { console.error('no plan: run --prepare first'); process.exit(2); }
  const plan = JSON.parse(fs.readFileSync(PLAN, 'utf8'));
  const todo = plan.sites.filter((s) => s.load_url);
  global.__R4 = {
    build: ({ regDom, mulberry32, shuffle }) => {
      const rnd = mulberry32(SEED_R4);
      const rA = mulberry32(SEED_R4 + 3);
      return shuffle(todo, rnd).map((r) => ({ store_id: r.store_id, stratum: r.stratum, domain: r.domain, lock: regDom(r.host || r.domain), base_url: r.product_url, url: r.load_url,
        token: null, arms: shuffle(['A0', 'A1', 'A2'], rA), in_repeat: false, in_v1: false }));
    },
  };
  let src = fs.readFileSync(path.join(CRAWL_DIR, 'crawl.js'), 'utf8');
  const sub = (from, to, tag) => { const n = src.split(from).length - 1; if (n !== 1) { console.error(`substitution ${tag} matched ${n} times`); process.exit(3); } src = src.replace(from, to); };
  sub('const plan = buildPlan();', 'const plan = global.__R4.build({ regDom, mulberry32, shuffle });', 'S1');
  sub("path.join(ROOT, 'STOP')", "path.join(OUT, 'STOP')", 'S2');
  if (SET === 'beyond') {
    beyondPatches();
    sub("|| /\\/api\\/collect|monorail|\\/\\.well-known\\/shopify/.test(pathn));", "|| /\\/api\\/collect|monorail|\\/\\.well-known\\/shopify/.test(pathn) || global.__R4.keep(r.url, host, storeHost, !!body));", 'S3a');
    sub('if (r.ck) o.ck = r.ck;', 'if (r.ck) o.ck = r.ck; if (r.setck) o.setck = r.setck;', 'S3b');
  }
  // crawl.js reads --out relative to crawl/; we pass the absolute-equivalent relative path
  const rel = path.relative(CRAWL_DIR, OUTDIR);
  process.argv = [process.argv[0], path.join(CRAWL_DIR, 'crawl.js'), '--out', rel, '--conc', argVal('--conc', '6')];
  fs.writeFileSync(path.join(OUTDIR, 'logs', 'run_meta.jsonl'), JSON.stringify({ started: new Date().toISOString(), set: SET, n_sites: todo.length, conc: argVal('--conc', '6'), substitutions: SET === 'beyond' ? ['S1', 'S2', 'S3a', 'S3b', 'P1', 'P2'] : ['S1', 'S2'] }) + '\n', { flag: 'a' });
  const m = new Module(path.join(CRAWL_DIR, 'crawl.js'), module);
  m.filename = path.join(CRAWL_DIR, 'crawl.js');
  m.paths = Module._nodeModulePaths(CRAWL_DIR);
  m._compile(src, m.filename);
}

(async () => {
  if (args.includes('--prepare')) return prepare();
  if (args.includes('--plan-check')) {
    const S = sites(); const c = {}; for (const s of S) c[s.stratum] = (c[s.stratum] || 0) + 1;
    console.log(SET, 'sites', S.length, c, 'no product url', S.filter((s) => !s.product_url).length, 'ids unique', new Set(S.map((s) => s.store_id)).size === S.length);
    console.log(S.slice(0, 3));
    return undefined;
  }
  return run();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
