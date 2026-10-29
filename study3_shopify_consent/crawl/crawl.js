// Study 3 live capture crawl: Shopify web pixels vs cookie-banner blocking.
//
// For each store (sample/sample.csv product_url; sample/creator_stratum.csv landing_url), with a
// researcher canary appended (utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-<store_id>),
// one FRESH browser (fresh temporary profile, deleted afterwards) per load, under these arms:
//   A0  default: no interaction; observe 15 s after the load event with passive wheel scrolling
//   A1  decline: wait <=10 s (after DOMContentLoaded) for a consent banner; click ONLY the CMP's
//       Decline/Reject control (never Accept, never "manage/settings", never "Do not sell" links);
//       screenshots before/after; observe 15 s after the click; then load the same URL once more
//       (next page) and observe 10 s after load (tests "Decline acts from the next page on").
//       No reject control on the first layer -> no_decline_option.
//   A2  emulated GPC in Chromium: Sec-GPC: 1 on every request (Playwright extraHTTPHeaders, also
//       applied to worker sessions) + navigator.globalPrivacyControl=true injected before any script in
//       every frame (CDP Page.addScriptToEvaluateOnNewDocument on every page/OOPIF session, plus a
//       Playwright init script) and every web worker (CDP Target.setAutoAttach{waitForDebuggerOnStart,
//       flatten} -> Debugger 'beforeScriptExecution' instrumentation pause -> Runtime.evaluate ->
//       resume; see validation/gpc_injection_selftest.js).
//   A0r/A2r repeats on a seeded 20% subsample (noise); V1 native GPC in headless Brave (fresh profile,
//       Shields off via Preferences default_content_setting_values.braveShields=2) on 100 stores.
// Every request is recorded from CDP Network events per target session (page / OOPIF / worker).
// Politeness: one store at a time per worker, loads of one site strictly sequential, >= 10 s between
// navigation starts on a site, >= 1 s between navigation starts globally, <= 6 concurrent browsers.
// Honest default headless UA (no spoofing, no stealth). Never logs in, adds to cart, submits forms.
//
// Usage: node crawl.js [--conc 6] [--limit-stores N] [--only S0001,C005] [--arms A0,A1] [--plan-only]
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const { chromium } = require(path.join(__dirname, '../../pilot/pixel_payloads/node_modules/playwright'));
const { RawCDP, wsUrlFromUserDataDir, sleep } = require('./lib/rawcdp');
const { Instrumenter } = require('./lib/instrument');
const { GPC_INJECT } = require('./lib/inject');
const V = require('./lib/vendors');
const P = require('./lib/probes');

const args = process.argv.slice(2);
const argVal = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const CONC = parseInt(argVal('--conc', '6'), 10);
const LIMIT_STORES = parseInt(argVal('--limit-stores', '0'), 10) || 0;
const ONLY = (argVal('--only', '') || '').split(',').filter(Boolean);
const ONLY_ARMS = (argVal('--arms', '') || '').split(',').filter(Boolean);
const OUT_TAG = argVal('--out', '');                 // optional separate output dir (tests)
const ROOT = __dirname;
const OUT = OUT_TAG ? path.join(ROOT, OUT_TAG) : ROOT;
const RAW = path.join(OUT, 'raw');
const SHOTS = path.join(OUT, 'screenshots');
const LOGS = path.join(OUT, 'logs');
for (const d of [RAW, SHOTS, LOGS]) fs.mkdirSync(d, { recursive: true });
const TMP = process.env.CS3_TMP || path.join(os.tmpdir(), 'cs3profiles');
fs.mkdirSync(TMP, { recursive: true });
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const SEED = 20260926;
const STATUS_LOG = path.join(LOGS, 'crawl_status.jsonl');
const MIN_FREE_BYTES = 1.3e9;

// ------------------------------------------------------------------ plan
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function shuffle(arr, rnd) { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
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
function withCanary(u, sid) {
  const c = `utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-${sid}`;
  const hashI = u.indexOf('#'); const base = hashI >= 0 ? u.slice(0, hashI) : u; const hash = hashI >= 0 ? u.slice(hashI) : '';
  return base + (base.includes('?') ? (base.endsWith('?') || base.endsWith('&') ? '' : '&') : '?') + c + hash;
}
function creatorToken(row) {
  let t = row.token || '';
  if (t.startsWith('codebook')) { try { return new URL(row.landing_url).searchParams.get('utm_campaign'); } catch (e) { return null; } }
  t = t.replace(/^q:/, '').split('~')[0];
  if (t.includes('=')) t = t.slice(t.indexOf('=') + 1);
  return t || null;
}
function regDom(h) {
  h = (h || '').replace(/^www\./, '').toLowerCase();
  const parts = h.split('.');
  if (parts.length <= 2) return h;
  return /\.(co|com|net|org|gov|edu|ac)\.[a-z]{2}$/.test(h) ? parts.slice(-3).join('.') : parts.slice(-2).join('.');
}
function buildPlan() {
  const main = parseCSV(path.join(ROOT, '..', 'sample', 'sample.csv'));
  const cre = parseCSV(path.join(ROOT, '..', 'sample', 'creator_stratum.csv'));
  const rnd = mulberry32(SEED);
  const stores = [];
  for (const r of cre) stores.push({ store_id: r.store_id, stratum: 'creator', domain: r.domain, lock: regDom(r.domain), base_url: r.landing_url, url: withCanary(r.landing_url, r.store_id), token: creatorToken(r), token_level: r.token_level });
  for (const r of shuffle(main, rnd)) stores.push({ store_id: r.store_id, stratum: 'main', domain: r.domain, lock: regDom(r.domain), base_url: r.product_url, url: withCanary(r.product_url, r.store_id), token: null, bucket: r.bucket, weight: r.weight });
  const ids = stores.map((s) => s.store_id);
  const rep = new Set(shuffle(ids, mulberry32(SEED + 1)).slice(0, Math.round(0.2 * ids.length)));
  const mainIds = stores.filter((s) => s.stratum === 'main').map((s) => s.store_id);
  const v1 = new Set(shuffle(mainIds, mulberry32(SEED + 2)).slice(0, 100));
  const rA = mulberry32(SEED + 3);
  for (const s of stores) {
    s.arms = shuffle(['A0', 'A1', 'A2'], rA);
    if (rep.has(s.store_id)) s.arms.push('A0r', 'A2r');
    if (v1.has(s.store_id)) s.arms.push('V1');
    s.in_repeat = rep.has(s.store_id); s.in_v1 = v1.has(s.store_id);
  }
  return stores;
}

// ------------------------------------------------------------------ helpers
const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout:' + (label || ''))), ms))]);
const evalT = (page, fn, arg, ms = 3000) => withTimeout(page.evaluate(fn, arg), ms, 'eval').catch((e) => ({ __err: String(e.message || e).slice(0, 120) }));
function decodeCmp(v) {
  if (!v || !v.startsWith('3')) return null;
  const parts = v.slice(1).split('_'); const head = parts[0];
  const [choices, purposes] = (head.split('.').concat(['']));
  const choice = (ch) => (choices.includes(ch.toLowerCase()) ? 'declined' : (choices.includes(ch.toUpperCase()) ? 'accepted' : 'none'));
  return { choice_a: choice('a'), choice_m: choice('m'), choice_p: choice('p'), choice_s: choice('s'), allow_a: purposes.includes('A'), allow_m: purposes.includes('M'), allow_p: purposes.includes('P'), allow_s: purposes.includes('S'),
    region: parts[1] || '', banner: parts[2] === 't' ? true : (parts[2] === 'f' ? false : null), sod_region: parts[3] === 't' ? true : (parts[3] === 'f' ? false : null) };
}
function parseWpm(html) {
  if (!html) return null;
  const m = html.match(/webPixelsConfigList:\s*(\[[\s\S]*?\])\s*,\s*isMerchantRequest/);
  if (!m) return { found: false, has_wpm_loader: /wpmLoader|web-pixels-manager-setup/.test(html) };
  try {
    const lst = JSON.parse(m[1]);
    return { found: true, pixels: lst.map((x) => ({ id: x.id, type: x.type, rc: x.runtimeContext, api: x.apiClientId != null ? String(x.apiClientId) : null, pp: x.privacyPurposes || null, pp_key: Object.prototype.hasOwnProperty.call(x, 'privacyPurposes'), dss: x.dataSharingState || null, name: x.name || null, vendor: V.APICLIENT2VENDOR[String(x.apiClientId)] || null })) };
  } catch (e) { return { found: true, parse_error: String(e).slice(0, 100) }; }
}
function parseOtAutoBlock(txt) {
  const t = txt.replace(/\\"/g, '"').replace(/\\\//g, '/');
  const out = []; const re = /\{[^{}]*?"Tag"\s*:\s*"([^"]*)"[^{}]*?"CategoryId"\s*:\s*\[([^\]]*)\]/g; let m;
  while ((m = re.exec(t)) && out.length < 2000) out.push({ tag: m[1].slice(0, 300), cat: (m[2].match(/"([^"]+)"/g) || []).map((x) => x.replace(/"/g, '')) });
  return out;
}
function parseCookiebotConfig(txt) {
  const out = []; const re = /tags\.push\(\{[^}]*?url:"([^"]*)"[^}]*?cat:\[([^\]]*)\]/g; let m;
  while ((m = re.exec(txt)) && out.length < 3000) if (m[1]) out.push({ url: m[1].slice(0, 300), cat: m[2].split(',').filter(Boolean).map((x) => parseInt(x, 10)) });
  return out;
}
function extractJsonAfter(txt, marker) {
  const i0 = txt.indexOf(marker); if (i0 < 0) return null;
  const i = i0 + marker.length; let d = 0; let j = i; let inStr = false; let esc = false;
  for (; j < txt.length; j++) { const c = txt[j]; if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; continue; } if (c === '"') inStr = true; else if (c === '{') d++; else if (c === '}') { d--; if (d === 0) break; } }
  try { const o = JSON.parse(txt.slice(i, j + 1)); return { version: o.version, banner: o.banner, regions: o.regions, gpc: o.gpc, blocker: o.blocker, store_headless: o.store ? o.store.headless : null }; } catch (e) { return { parse_error: String(e).slice(0, 80) }; }
}
function freeBytes() { try { const s = fs.statfsSync(ROOT); return s.bavail * s.bsize; } catch (e) { return Infinity; } }

// ------------------------------------------------------------------ one load
async function runLoad(store, arm, w) {
  const isGpc = arm === 'A2' || arm === 'A2r';
  const isBrave = arm === 'V1';
  const tStart = Date.now();
  const rec = { store_id: store.store_id, stratum: store.stratum, domain: store.domain, arm, url: store.url, started_at: new Date(tStart).toISOString(), worker: w,
    browser: isBrave ? 'brave' : 'chromium-headless-shell', errors: [], consent: [], clicks: null, shots: [] };
  const dir = fs.mkdtempSync(path.join(TMP, `${store.store_id}-${arm}-`));
  let ctx = null; let cdp = null; let ins = null;
  try {
    if (isBrave) { fs.mkdirSync(path.join(dir, 'Default'), { recursive: true }); fs.writeFileSync(path.join(dir, 'Default', 'Preferences'), JSON.stringify({ profile: { default_content_setting_values: { braveShields: 2 } } })); }
    const opts = { headless: true, args: ['--remote-debugging-port=0'], locale: 'en-US', timezoneId: 'America/Los_Angeles', viewport: { width: 1366, height: 900 } };
    if (isGpc) opts.extraHTTPHeaders = { 'Sec-GPC': '1' };
    if (isBrave) opts.executablePath = BRAVE;
    ctx = await withTimeout(chromium.launchPersistentContext(dir, opts), 30000, 'launch');
    rec.browser_version = ctx.browser() ? ctx.browser().version() : null;
    await ctx.addInitScript({ content: P.OBSERVER_SRC });
    if (isGpc) await ctx.addInitScript({ content: GPC_INJECT });
    cdp = new RawCDP(await wsUrlFromUserDataDir(dir));
    await cdp.connect();
    ins = new Instrumenter(cdp, { inject: isGpc ? GPC_INJECT : null, bodyRules: [
      { name: 'otautoblock', re: /cdn\.cookielaw\.org\/consent\/[^/]+\/OtAutoBlock\.js/ },
      { name: 'cookiebot_cfg', re: /consentcdn\.cookiebot\.(com|eu)\/consentconfig\/.+\/configuration\.js/ },
      { name: 'pandectes_rules', re: /\/pandectes-rules(-latest)?\.js/ },
    ] });
    await ins.start();
    const page = ctx.pages()[0] || await ctx.newPage();
    // wait until our instrumentation of the existing page target is complete
    for (let i = 0; i < 40; i++) { const pt = [...ins.targets.values()].find((t) => t.type === 'page'); if (pt && pt.t_resume !== undefined) break; await sleep(50); }
    const pageTarget = [...ins.targets.values()].find((t) => t.type === 'page');
    rec.main_frame_id = pageTarget ? pageTarget.targetId : null;
    ins.mainFrameId = rec.main_frame_id;
    let dclEpoch = null; let loadEpoch = null;
    page.on('domcontentloaded', () => { if (dclEpoch === null) dclEpoch = Date.now(); });
    page.on('load', () => { if (loadEpoch === null) loadEpoch = Date.now(); });
    rec.t_goto_start = Date.now();
    let resp = null;
    try {
      resp = await page.goto(store.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      rec.goto_status = resp ? resp.status() : null;
      rec.goto_url = resp ? resp.url().slice(0, 1000) : null;
    } catch (e) { rec.goto_error = String(e).split('\n')[0].slice(0, 300); }
    const fatal = rec.goto_error && /ERR_NAME_NOT_RESOLVED|ERR_CONNECTION_REFUSED|ERR_ADDRESS_UNREACHABLE|ERR_CERT|ERR_SSL|ERR_TOO_MANY_REDIRECTS|ERR_CONNECTION_RESET|ERR_EMPTY_RESPONSE/.test(rec.goto_error);
    if (!fatal) {
      if (loadEpoch === null) { try { await page.waitForLoadState('load', { timeout: 12000 }); } catch (e) { rec.load_timeout = true; } }
      if (dclEpoch === null) dclEpoch = Date.now();
      const loadRef = loadEpoch || Date.now();
      rec.dcl_epoch = dclEpoch; rec.load_epoch = loadEpoch;
      const to = await evalT(page, () => performance.timeOrigin);
      rec.time_origin = typeof to === 'number' ? to : null;
      const poll = async (tag) => { const c = await evalT(page, P.CONSENT_READ, undefined, 2500); c.tag = tag; c.epoch = Date.now(); rec.consent.push(c); return c; };
      const observe = async (untilEpoch, scroll, tag) => {
        const s0 = Date.now(); let k = 0; let lastPoll = 0;
        while (Date.now() < untilEpoch) {
          if (Date.now() - lastPoll >= 1000) { lastPoll = Date.now(); await poll(tag); }
          if (scroll && k < 6 && Date.now() - s0 >= 2000 + k * 1000) { try { await withTimeout(page.mouse.wheel(0, 600), 2000, 'wheel'); } catch (e) { /* ignore */ } k++; }
          await sleep(200);
        }
      };
      if (arm === 'A1') {
        // wait up to 10 s after DOMContentLoaded for a visible banner
        let banner = null;
        while (Date.now() < dclEpoch + 10000) {
          const s = await evalT(page, () => (window.__cs3 ? window.__cs3.banner : null), undefined, 2000);
          if (s && !s.__err && s.t !== undefined) { banner = s; break; }
          await sleep(400);
        }
        rec.banner_wait = { found: !!banner, banner, waited_ms: Date.now() - dclEpoch };
        if (banner) {
          await sleep(1000); // let the banner finish animating in
          await poll('pre_click');
          const pre = path.join(SHOTS, `${store.store_id}__A1__pre.jpg`);
          try { await withTimeout(page.screenshot({ path: pre, type: 'jpeg', quality: 30, timeout: 8000 }), 9000, 'shot'); rec.shots.push(path.basename(pre)); } catch (e) { rec.errors.push('shot_pre:' + String(e).slice(0, 80)); }
          const fr = await evalT(page, P.FIND_REJECT, { sigs: P.CMP_SIGS, rejectRe: P.REJECT_RE, neverRe: P.NEVER_RE }, 6000);
          rec.clicks = { find: fr };
          if (fr && fr.found) {
            rec.clicks.t_click_epoch = Date.now();
            let method = null;
            try { await page.locator('[data-cs3-reject="1"]').first().click({ timeout: 4000 }); method = 'playwright_click'; } catch (e1) {
              try { await page.locator('[data-cs3-reject="1"]').first().click({ timeout: 2000, force: true }); method = 'playwright_force'; } catch (e2) {
                const ok = await evalT(page, P.JS_CLICK_REJECT, undefined, 3000); method = ok === true ? 'js_click' : 'click_failed';
              }
            }
            rec.clicks.method = method;
            rec.clicks.t_after_click_epoch = Date.now();
            const tc = rec.clicks.t_click_epoch;
            await sleep(Math.max(0, tc + 1000 - Date.now())); await poll('click+1');
            await sleep(Math.max(0, tc + 2000 - Date.now()));
            const post = path.join(SHOTS, `${store.store_id}__A1__post.jpg`);
            try { await withTimeout(page.screenshot({ path: post, type: 'jpeg', quality: 30, timeout: 8000 }), 9000, 'shot'); rec.shots.push(path.basename(post)); } catch (e) { rec.errors.push('shot_post:' + String(e).slice(0, 80)); }
            rec.clicks.banner_after = await evalT(page, P.FIND_REJECT, { sigs: P.CMP_SIGS, rejectRe: P.REJECT_RE, neverRe: P.NEVER_RE }, 6000);
            await sleep(Math.max(0, tc + 5000 - Date.now())); await poll('click+5');
            await observe(tc + 15000, true, 'post_click');
            rec.probe_first = await evalT(page, P.CMP_PROBE, P.CMP_SIGS, 8000);
            // next page: same URL again in the same context (>= 15 s after the first navigation start)
            await sleep(Math.max(0, rec.t_goto_start + 10000 - Date.now()));
            rec.next_goto_epoch = Date.now();
            try { const r2 = await page.goto(store.url, { waitUntil: 'load', timeout: 30000 }); rec.next_status = r2 ? r2.status() : null; } catch (e) { rec.next_error = String(e).split('\n')[0].slice(0, 200); }
            rec.next_load_epoch = Date.now();
            await observe(Date.now() + 10000, true, 'next_page');
          } else {
            rec.no_decline_option = true;
            await observe(loadRef + 15000, true, 'observe');
          }
        } else {
          await observe(loadRef + 15000, true, 'observe');
        }
      } else {
        await observe(loadRef + 15000, true, 'observe');
      }
      rec.t_obs_end = Date.now();
      await poll('end');
      rec.probe = await evalT(page, P.CMP_PROBE, P.CMP_SIGS, 8000);
      rec.wpm_dom = await evalT(page, () => { const s = [...document.scripts].map((x) => x.textContent || '').find((t) => t.includes('webPixelsConfigList')); if (!s) return null; const i = s.indexOf('webPixelsConfigList'); const j = s.indexOf('isMerchantRequest', i); return s.slice(i, j > 0 ? j + 20 : i + 200000); }, undefined, 5000);
      // GPC visibility inside every frame and every worker (all arms; A0 is the control)
      const frames = page.frames().slice(0, 40);
      rec.frames_gpc = [];
      for (const f of frames) { const r = await withTimeout(f.evaluate(() => ({ h: location.href.slice(0, 160), g: navigator.globalPrivacyControl === undefined ? 'undefined' : navigator.globalPrivacyControl, s: window.origin })), 1500, 'fr').catch((e) => ({ err: String(e).slice(0, 60) })); rec.frames_gpc.push(r); }
      rec.workers_gpc = await ins.evalInWorkers(WORKER_VERIFY, 2000);
      try { const cks = await withTimeout(ctx.cookies(), 5000, 'cookies'); rec.cookies = cks.map((c) => ({ n: c.name, d: c.domain, v: /^(_tracking_consent|OptanonConsent|OptanonAlertBoxClosed|CookieConsent|_pandectes_gdpr|cookieconsent_status|osano_consentmanager|cookiefirst-consent|cookiehub|didomi_token|euconsent-v2|usprivacy|_iub_cs.*|CookieScriptConsent|notice_preferences|cmapi_cookie_privacy|fides_consent|_swb_consent_)$/i.test(c.name) ? decodeURIComponent(c.value || '').slice(0, 500) : undefined })); } catch (e) { rec.errors.push('cookies:' + String(e).slice(0, 80)); }
    }
  } catch (e) {
    rec.errors.push('load:' + String(e).slice(0, 300));
  }
  // collect bodies (CDP Network.getResponseBody)
  if (ins) { try { await withTimeout(Promise.allSettled(ins.bodyPromises), 8000, 'bodies'); } catch (e) { rec.errors.push('bodies_timeout'); } }
  const B = ins ? ins.bodies : {};
  try {
    const navs = (B.nav_html || []).filter((x) => x.text);
    const h = navs.length ? navs[0].text : null;
    rec.html_bodies = (B.nav_html || []).map((x) => ({ url: x.url, len: x.text ? x.text.length : null, err: x.err || null }));
    rec.wpm = parseWpm(h);
    if ((!rec.wpm || !rec.wpm.found) && rec.wpm_dom && typeof rec.wpm_dom === 'string') { const w2 = parseWpm(rec.wpm_dom.replace(/^webPixelsConfigList/, 'webPixelsConfigList')); if (w2 && w2.found) { rec.wpm = w2; rec.wpm.source = 'dom'; } }
    else if (rec.wpm && rec.wpm.found) rec.wpm.source = 'html';
    delete rec.wpm_dom;
    if (h) { rec.html_len = h.length; rec.html_flags = { nostra: /window\.Nostra|\/_nostra\//.test(h), pandectes_inline: /PandectesSettings\s*=|PandectesRulesSettings\s*=/.test(h), hydrogen: /hydrogen|oxygen/i.test(h.slice(0, 5000)), wpm_loader: /wpmLoader|web-pixels-manager-setup/.test(h) }; }
  } catch (e) { rec.errors.push('wpm:' + String(e).slice(0, 80)); }
  try { const ot = (B.otautoblock || []).find((x) => x.text); rec.otautoblock = ot ? { url: ot.url, tags: parseOtAutoBlock(ot.text) } : ((B.otautoblock || []).length ? { url: B.otautoblock[0].url, err: B.otautoblock[0].err } : null); } catch (e) { /* ignore */ }
  try { const cb = (B.cookiebot_cfg || []).find((x) => x.text); rec.cookiebot_cfg = cb ? { url: cb.url, tags: parseCookiebotConfig(cb.text) } : null; } catch (e) { /* ignore */ }
  try { const pr = (B.pandectes_rules || []).find((x) => x.text); if (pr) rec.pandectes_rules_file = { url: pr.url, settings: extractJsonAfter(pr.text, 'window.pandectesRulesSettings=') }; } catch (e) { /* ignore */ }
  if (ins) {
    rec.targets = [...ins.targets.values()].map((t) => ({ sid: t.sid, type: t.type, url: t.url, parent: t.parent, targetId: t.targetId, waiting: t.waiting, t_attach: t.t_attach, t_resume: t.t_resume, inject: t.inject || null, setup_errs: t.setup_errs && t.setup_errs.length ? t.setup_errs : undefined }));
    rec.frames = Object.fromEntries([...ins.frames.entries()].map(([k, f]) => [k, { url: (f.url || '').slice(0, 300), parent: f.parentId, sb: f.sandbox ? f.sandbox.flags || f.sandbox : undefined }]));
    rec.requests = buildRequests(ins, rec, store);
    rec.inst_t0 = ins.t0;
  }
  try { if (cdp) cdp.close(); } catch (e) { /* ignore */ }
  try { if (ctx) await withTimeout(ctx.close(), 15000, 'close'); } catch (e) { rec.errors.push('close:' + String(e).slice(0, 80)); }
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* ignore */ }
  rec.t_end = Date.now(); rec.ms = rec.t_end - tStart;
  return rec;
}

const WORKER_VERIFY = `(function(){var g=self;var r={gpc:(typeof navigator==='undefined')?'no_navigator':String(navigator.globalPrivacyControl),inj:g.__cs3_gpc||null,n1:Object.getOwnPropertyNames(g).length,href:String(location.href).slice(0,300)};
try{r.nav_own=Object.prototype.hasOwnProperty.call(g,'navigator');r.nav_tag=Object.prototype.toString.call(g.navigator);
if(typeof WorkerNavigator!=='undefined'){var d=Object.getOwnPropertyDescriptor(WorkerNavigator.prototype,'globalPrivacyControl');r.proto_has=!!d;
try{r.proto_val=(d&&d.get)?String(d.get.call(g.navigator)):null;}catch(e){r.proto_val='err:'+String(e).slice(0,60)}}
if(r.gpc==='undefined'){try{var pr=Object.getPrototypeOf(g.navigator);r.nav_proto_keys=Object.getOwnPropertyNames(pr).slice(0,50).join(',');r.nav_keys=Object.keys(g.navigator).slice(0,50).join(',');}catch(e){}}}catch(e){r.e=String(e).slice(0,100)}return r;})()`;

// ------------------------------------------------------------------ request records
function buildRequests(ins, rec, store) {
  const reqs = ins.requests();
  const mainFrame = rec.main_frame_id;
  // navigation base: first main-frame document request
  const nav = reqs.find((r) => r.is_nav && (!mainFrame || r.frame === mainFrame)) || reqs.find((r) => r.is_nav);
  const navWall = nav ? nav.wall : (rec.t_goto_start || ins.t0);
  rec.nav_wall = navWall;
  const navs = reqs.filter((r) => r.is_nav && (!mainFrame || r.frame === mainFrame));
  rec.navigations = navs.map((r) => ({ t: r.wall - navWall, url: r.url.slice(0, 600), st: r.st, hop: r.hop || 0, redirected: !!r.redirected, headers: r.resp_headers || null }));
  let landing;
  try { const U = new URL(store.url); landing = { canary: `cmpstudy-${store.store_id}`, pathQ: U.pathname + '?', path: U.pathname.length > 1 ? U.pathname : null, token: store.token }; } catch (e) { landing = { canary: `cmpstudy-${store.store_id}`, pathQ: null, path: null, token: store.token }; }
  const storeHost = (() => { try { return new URL(rec.goto_url || store.url).hostname; } catch (e) { return store.domain; } })();
  const libOrigin = new Map(); // vendor library URL -> origin (for OPEN-pixel chains)
  const out = [];
  let i = 0;
  for (const r of reqs) {
    const t = r.wall != null ? r.wall - navWall : null;
    let host = ''; let pathn = '';
    try { const U = new URL(r.url); host = U.hostname; pathn = U.pathname; } catch (e) { /* data: etc */ }
    if (!host) { i++; continue; } // skip data:/blob: URLs
    const tg = ins.targets.get(r.sid) || {};
    const sess = tg.type || 'root';
    const vend = V.classifyVendor(r.url);
    const wpm = V.wpmUrl(r.url);
    const fr = r.frame ? ins.frames.get(r.frame) : null;
    const frameUrl = fr ? fr.url || '' : '';
    // ---- origin attribution
    let origin = 'main_thread'; let pixel = null; let ev = null;
    if (sess === 'worker' || sess === 'shared_worker' || sess === 'service_worker') {
      const wu = V.wpmUrl(tg.url || '');
      if (wu && wu.wpm === 'strict_worker_bootstrap') { origin = 'strict_worker'; pixel = wu.pixel_id; ev = 'worker_session'; }
      else { origin = 'other_worker'; ev = 'worker_session'; }
    } else if (r.frame && mainFrame && r.frame !== mainFrame) {
      const fw = V.wpmUrl(frameUrl);
      if (fw && fw.wpm === 'lax_iframe_sandbox') { origin = 'lax_iframe'; pixel = fw.pixel_id; ev = 'frame_url'; }
      else if (/\/(web-pixels|wpm)@[^/]+\/.*\/sandbox\//.test(frameUrl)) { origin = 'lax_iframe'; ev = 'frame_url_loose'; }
      else { origin = 'subframe'; ev = 'frame_url'; }
    } else {
      const st = [r.ini_url].concat(r.ini_stack || []).filter(Boolean);
      const op = st.map((u) => V.wpmUrl(u)).find((x) => x && x.wpm === 'open_main_thread_pixel');
      if (op) { origin = 'open_pixel'; pixel = op.pixel_id; ev = 'initiator'; }
      else if (st.some((u) => libOrigin.get(u) === 'open_pixel' || libOrigin.get(u) === 'open_pixel_chain')) { origin = 'open_pixel_chain'; ev = 'initiator_lib'; }
      else if (st.some((u) => { const x = V.wpmUrl(u); return x && x.wpm === 'manager_bundle'; })) { origin = 'wpm_main_proxy'; ev = 'initiator_manager'; }
      else if (wpm && wpm.wpm === 'strict_worker_bootstrap') { origin = 'wpm_bootstrap'; pixel = wpm.pixel_id; ev = 'url'; }
    }
    if (vend && vend.kind === 'library') libOrigin.set(r.url, origin);
    let body = null;
    if (r.post_buf && r.post_buf.length) body = V.bodyText(r.post_buf);
    const thirdParty = host !== storeHost && !host.endsWith('.' + regDom(storeHost)) && regDom(host) !== regDom(storeHost);
    const detail = !!(vend || wpm || r.is_nav || (thirdParty && (body || /[?&]/.test(r.url))) || /\/api\/collect|monorail|\/\.well-known\/shopify/.test(pathn));
    const flags = V.payloadFlags(r.url, body, landing);
    const o = { i, t, host, m: r.m, type: r.type, sess, st: r.st, origin };
    if (r.fail) o.fail = r.fail; if (r.blocked) o.blocked = r.blocked; if (r.canceled) o.canceled = true;
    if (pixel) o.pixel = pixel; if (ev) o.oev = ev;
    if (flags.canary) o.canary = true; if (flags.full_url) o.full_url = true; if (flags.path) o.path_hit = true; if (flags.creator_token) o.creator_token = true;
    if (thirdParty) o.tp = true;
    if (vend) { o.vendor = vend.vendor; o.vkind = vend.kind; o.ad = vend.ad; }
    if (wpm) { o.wpm = wpm.wpm; if (wpm.pixel_id) o.wpm_pixel = wpm.pixel_id; }
    if (r.ck) o.ck = r.ck; if (r.ck_blocked) o.ck_blocked = r.ck_blocked;
    const gh = r.gpc_hdr !== undefined ? r.gpc_hdr : r.gpc_hdr_req; if (gh !== undefined) o.gpc_hdr = gh;
    if (detail) {
      o.url = r.url.slice(0, 3000); if (r.url.length > 3000) o.url_len = r.url.length;
      if (r.ini_type) o.ini_type = r.ini_type; if (r.ini_url) o.ini_url = r.ini_url; if (r.ini_stack) o.ini_stack = r.ini_stack;
      if (sess !== 'page') o.sess_url = (tg.url || '').slice(0, 200);
      if (r.frame && r.frame !== mainFrame) o.frame_url = frameUrl.slice(0, 200);
      if (body) { o.post = body.slice(0, 4000); if (body.length > 4000) o.post_len = body.length; }
      if (vend || wpm || thirdParty) { const e2 = V.eventNames(r.url, body); if (e2.length) o.events = e2; }
      if (r.is_nav) { o.is_nav = true; o.resp_headers = r.resp_headers || null; }
      if (r.redirect_from) o.redirect_from = r.redirect_from;
    } else {
      o.url = r.url.slice(0, 160);
    }
    if (r.t_end != null && r.t != null) o.dur = r.t_end - r.t;
    out.push(o); i++;
  }
  return out;
}

// ------------------------------------------------------------------ scheduler
(async () => {
  const plan = buildPlan();
  if (!OUT_TAG) fs.writeFileSync(path.join(OUT, 'plan.json'), JSON.stringify({ seed: SEED, built: new Date().toISOString(), n_stores: plan.length, stores: plan.map((s) => ({ store_id: s.store_id, stratum: s.stratum, domain: s.domain, url: s.url, token: s.token, arms: s.arms, in_repeat: s.in_repeat, in_v1: s.in_v1 })) }, null, 0));
  if (args.includes('--plan-only')) { console.log('plan written', plan.length); return; }
  let stores = plan;
  if (ONLY.length) stores = stores.filter((s) => ONLY.includes(s.store_id));
  if (LIMIT_STORES) stores = stores.slice(0, LIMIT_STORES);
  const FORCE = (argVal('--force-arms', '') || '').split(',').filter(Boolean);
  if (FORCE.length) stores = stores.map((s) => Object.assign({}, s, { arms: FORCE }));
  const doneFile = (s, a) => path.join(RAW, `${s.store_id}__${a}.json.gz`);
  const queue = stores.filter((s) => s.arms.some((a) => (!ONLY_ARMS.length || ONLY_ARMS.includes(a)) && !fs.existsSync(doneFile(s, a))));
  console.log(new Date().toISOString(), 'stores to do:', queue.length, 'of', stores.length, 'conc', CONC, 'tmp', TMP);
  const busyLocks = new Set(); const lastNav = {}; let lastGlobal = 0; let gate = Promise.resolve();
  let nLoads = 0; let stop = false;
  const navGate = async (lock) => {
    gate = gate.then(async () => {
      const g = 1000 - (Date.now() - lastGlobal); if (g > 0) await sleep(g);
      const d = 10000 - (Date.now() - (lastNav[lock] || 0)); if (d > 0) await sleep(d);
      lastGlobal = Date.now(); lastNav[lock] = Date.now();
    });
    await gate;
  };
  const worker = async (w) => {
    while (!stop) {
      if (fs.existsSync(path.join(ROOT, 'STOP'))) { stop = true; break; }
      if (freeBytes() < MIN_FREE_BYTES) { console.log('DISK_LOW', freeBytes()); stop = true; break; }
      const idx = queue.findIndex((s) => !busyLocks.has(s.lock));
      if (idx < 0) { if (!queue.length) break; await sleep(500); continue; }
      const s = queue.splice(idx, 1)[0];
      busyLocks.add(s.lock);
      for (const arm of s.arms) {
        if (stop) break;
        if (ONLY_ARMS.length && !ONLY_ARMS.includes(arm)) continue;
        if (fs.existsSync(doneFile(s, arm))) continue;
        await navGate(s.lock);
        let rec = null;
        try { rec = await withTimeout(runLoad(s, arm, w), 170000, 'hard'); } catch (e) { rec = { store_id: s.store_id, stratum: s.stratum, domain: s.domain, arm, url: s.url, fatal_error: String(e).slice(0, 300), started_at: new Date().toISOString(), requests: [] }; }
        lastNav[s.lock] = Math.max(lastNav[s.lock] || 0, rec.next_goto_epoch || 0);
        fs.writeFileSync(doneFile(s, arm), zlib.gzipSync(JSON.stringify(rec)));
        nLoads++;
        const nv = (rec.requests || []).filter((r) => r.vendor && r.ad).length;
        const line = { n: nLoads, w, id: s.store_id, arm, st: rec.goto_status || null, err: rec.goto_error || rec.fatal_error || (rec.errors && rec.errors[0]) || null, nreq: (rec.requests || []).length, nad: nv,
          banner: rec.banner_wait ? rec.banner_wait.found : undefined, click: rec.clicks ? rec.clicks.method || (rec.no_decline_option ? 'no_decline_option' : null) : undefined, ms: rec.ms || null, at: new Date().toISOString() };
        fs.appendFileSync(STATUS_LOG, JSON.stringify(line) + '\n');
      }
      busyLocks.delete(s.lock);
      if (s.arms.every((a) => fs.existsSync(doneFile(s, a)))) fs.appendFileSync(path.join(LOGS, 'stores_done.txt'), s.store_id + '\n');
    }
  };
  await Promise.all(Array.from({ length: CONC }, (_, w) => worker(w)));
  console.log(new Date().toISOString(), stop ? 'STOPPED' : 'ALL DONE', 'loads this run:', nLoads);
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
