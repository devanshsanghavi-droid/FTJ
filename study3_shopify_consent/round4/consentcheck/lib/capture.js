// One page visit per condition ("arm") in a fresh, temporary browser profile, instrumented with the
// study crawler's library (crawl/lib). Arms:
//   default  no interaction: observe 15 s after the load event (with passive wheel scrolling, as in the study)
//   decline  wait <= 10 s for a consent banner, click ONLY its Decline/Reject control (never Accept),
//            observe 15 s, then load the same page once more (>= 10 s after the first navigation) and observe 10 s
//   gpc      Global Privacy Control on (Sec-GPC: 1 header + navigator.globalPrivacyControl in every frame and
//            worker, injected before the page's own scripts), observe 15 s after load
// The browser is Playwright's unmodified Chromium: default user agent, automation flag on, no stealth.
const fs = require('fs');
const os = require('os');
const path = require('path');

const withTimeout = (p, ms, label) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout:' + (label || ''))), ms))]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Politeness: >= siteGapMs between navigation starts on the site; >= globalGapMs between any two.
class Pacer {
  constructor(siteGapMs = 10000, globalGapMs = 1000) { this.siteGap = siteGapMs; this.globalGap = globalGapMs; this.last = 0; this.navs = []; }
  async beforeNav(label) {
    const wait = Math.max(this.last + Math.max(this.siteGap, this.globalGap) - Date.now(), 0);
    if (this.last && wait > 0) await sleep(wait);
    this.last = Date.now(); this.navs.push({ label, at: new Date(this.last).toISOString() });
  }
}

const ADULT_LABEL = `(() => { const m = [...document.querySelectorAll('meta[name="rating" i]')].map((x) => (x.content || '').toLowerCase());
  const rta = !!document.querySelector('meta[content*="RTA-5042-1996-1400-1577-RTA" i]');
  return { rta, rating: m.filter((x) => /adult|mature|restricted|rta/.test(x)) }; })()`;

const WORKER_VERIFY = `(function(){var g=self;return {gpc:(typeof navigator==='undefined')?'no_navigator':String(navigator.globalPrivacyControl),inj:!!g.__cs3_gpc,href:String(location.href).slice(0,200)};})()`;

async function captureArm({ env, arm, url, pacer, opts, log }) {
  const { chromium } = env.pw; const L = env.lib; const P = L.probes;
  const { RawCDP, wsUrlFromUserDataDir } = L.rawcdp;
  const { Instrumenter } = L.instrument;
  const { GPC_INJECT } = L.inject;
  const isGpc = arm === 'gpc';
  const rec = { arm, url, started_at: new Date().toISOString(), errors: [], consent: [], shots: {} };
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `consentcheck-${arm}-`));
  let ctx = null; let cdp = null; let ins = null;
  try {
    const lo = { headless: !opts.headed, args: ['--remote-debugging-port=0'], viewport: { width: 1366, height: 900 } };
    if (isGpc) lo.extraHTTPHeaders = { 'Sec-GPC': '1' };
    ctx = await withTimeout(chromium.launchPersistentContext(dir, lo), 45000, 'launch');
    rec.browser_version = ctx.browser() ? ctx.browser().version() : null;
    await ctx.addInitScript({ content: P.OBSERVER_SRC });
    if (isGpc) await ctx.addInitScript({ content: GPC_INJECT });
    cdp = new RawCDP(await wsUrlFromUserDataDir(dir));
    await cdp.connect();
    ins = new Instrumenter(cdp, { inject: isGpc ? GPC_INJECT : null, bodyRules: [
      { name: 'otautoblock', re: /cdn\.cookielaw\.org\/consent\/[^/]+\/OtAutoBlock\.js/ },
      { name: 'cookiebot_cfg', re: /consentcdn\.cookiebot\.(com|eu)\/consentconfig\/.+\/configuration\.js/ },
    ] });
    await ins.start();
    const page = ctx.pages()[0] || await ctx.newPage();
    for (let i = 0; i < 40; i++) { const pt = [...ins.targets.values()].find((t) => t.type === 'page'); if (pt && pt.t_resume !== undefined) break; await sleep(50); }
    const pageTarget = [...ins.targets.values()].find((t) => t.type === 'page');
    rec.main_frame_id = pageTarget ? pageTarget.targetId : null;
    ins.mainFrameId = rec.main_frame_id;
    let dclEpoch = null; let loadEpoch = null;
    page.on('domcontentloaded', () => { if (dclEpoch === null) dclEpoch = Date.now(); });
    page.on('load', () => { if (loadEpoch === null) loadEpoch = Date.now(); });
    await pacer.beforeNav(arm);
    rec.t_goto_start = Date.now();
    log(`  [${arm}] loading ${url}`);
    try {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      rec.goto_status = resp ? resp.status() : null;
      rec.goto_url = resp ? resp.url().slice(0, 1000) : null;
    } catch (e) { rec.goto_error = String(e).split('\n')[0].slice(0, 300); }
    const fatal = rec.goto_error && /ERR_NAME_NOT_RESOLVED|ERR_CONNECTION_REFUSED|ERR_ADDRESS_UNREACHABLE|ERR_CERT|ERR_SSL|ERR_TOO_MANY_REDIRECTS|ERR_CONNECTION_RESET|ERR_EMPTY_RESPONSE/.test(rec.goto_error);
    if (!fatal) {
      if (loadEpoch === null) { try { await page.waitForLoadState('load', { timeout: 12000 }); } catch (e) { rec.load_timeout = true; } }
      if (dclEpoch === null) dclEpoch = Date.now();
      const loadRef = loadEpoch || Date.now();
      rec.dcl_epoch = dclEpoch; rec.load_epoch = loadEpoch;
      const ev = (fn, arg, ms = 3000) => withTimeout(page.evaluate(fn, arg), ms, 'eval').catch((e) => ({ __err: String(e.message || e).slice(0, 120) }));
      const to = await ev(() => performance.timeOrigin);
      rec.time_origin = typeof to === 'number' ? to : null;
      const adult = await ev(ADULT_LABEL);
      if (adult && (adult.rta || (adult.rating && adult.rating.length))) {
        rec.aborted = 'adult_content_label'; log(`  [${arm}] page carries an adult-content label: stopping without further interaction`);
      } else {
        const poll = async (tag) => { const c = await ev(P.CONSENT_READ, undefined, 2500); c.tag = tag; c.epoch = Date.now(); rec.consent.push(c); return c; };
        const observe = async (untilEpoch, tag) => {
          const s0 = Date.now(); let k = 0; let lastPoll = 0;
          while (Date.now() < untilEpoch) {
            if (Date.now() - lastPoll >= 1000) { lastPoll = Date.now(); await poll(tag); }
            if (k < 6 && Date.now() - s0 >= 2000 + k * 1000) { try { await withTimeout(page.mouse.wheel(0, 600), 2000, 'wheel'); } catch (e) { /* ignore */ } k++; }
            await sleep(200);
          }
        };
        const shot = async (name) => {
          if (!opts.screenshots) return;
          try { const b = await withTimeout(page.screenshot({ type: 'jpeg', quality: 35, timeout: 8000 }), 9000, 'shot'); rec.shots[name] = b.toString('base64'); } catch (e) { rec.errors.push('shot_' + name + ':' + String(e).slice(0, 80)); }
        };
        if (arm === 'decline') {
          let banner = null;
          while (Date.now() < dclEpoch + 10000) {
            const s = await ev(() => (window.__cs3 ? window.__cs3.banner : null), undefined, 2000);
            if (s && !s.__err && s.t !== undefined) { banner = s; break; }
            await sleep(400);
          }
          rec.banner_wait = { found: !!banner, banner, waited_ms: Date.now() - dclEpoch };
          if (banner) {
            await sleep(1000);
            await poll('pre_click');
            const fr = await ev(P.FIND_REJECT, { sigs: P.CMP_SIGS, rejectRe: P.REJECT_RE, neverRe: P.NEVER_RE }, 6000);
            rec.clicks = { find: fr };
            // Belt and braces: never click anything that reads like Accept/Agree/Allow.
            const safe = fr && fr.found && !/accept|agree|allow|consent|got it|^ok(ay)?$/i.test(fr.text || '');
            await shot('before_click');
            if (fr && fr.found && !safe) { rec.clicks.refused = 'text looked like an accept control'; }
            if (safe) {
              log(`  [${arm}] clicking "${fr.text}" (the banner's Decline/Reject control)`);
              rec.clicks.t_click_epoch = Date.now();
              let method = null;
              try { await page.locator('[data-cs3-reject="1"]').first().click({ timeout: 4000 }); method = 'playwright_click'; } catch (e1) {
                try { await page.locator('[data-cs3-reject="1"]').first().click({ timeout: 2000, force: true }); method = 'playwright_force'; } catch (e2) {
                  const ok = await ev(P.JS_CLICK_REJECT, undefined, 3000); method = ok === true ? 'js_click' : 'click_failed';
                }
              }
              rec.clicks.method = method;
              const tc = rec.clicks.t_click_epoch;
              await sleep(Math.max(0, tc + 1000 - Date.now())); await poll('click+1');
              await sleep(Math.max(0, tc + 2000 - Date.now()));
              await shot('after_click');
              rec.clicks.banner_after = await ev(P.FIND_REJECT, { sigs: P.CMP_SIGS, rejectRe: P.REJECT_RE, neverRe: P.NEVER_RE }, 6000);
              await observe(tc + 15000, 'post_click');
              rec.probe_first = await ev(P.CMP_PROBE, P.CMP_SIGS, 8000);
              await pacer.beforeNav('decline-next-page');
              rec.next_goto_epoch = Date.now();
              log(`  [${arm}] loading the same page again (does the Decline carry over?)`);
              try { const r2 = await page.goto(url, { waitUntil: 'load', timeout: 30000 }); rec.next_status = r2 ? r2.status() : null; } catch (e) { rec.next_error = String(e).split('\n')[0].slice(0, 200); }
              rec.next_load_epoch = Date.now();
              await observe(Date.now() + 10000, 'next_page');
            } else {
              rec.no_decline_option = true;
              await observe(loadRef + 15000, 'observe');
            }
          } else {
            await observe(loadRef + 15000, 'observe');
          }
        } else {
          await observe(loadRef + 15000, 'observe');
        }
        await poll('end');
        rec.probe = await ev(P.CMP_PROBE, P.CMP_SIGS, 8000);
        rec.wpm_dom = await ev(() => { const s = [...document.scripts].map((x) => x.textContent || '').find((t) => t.includes('webPixelsConfigList')); if (!s) return null; const i = s.indexOf('webPixelsConfigList'); const j = s.indexOf('isMerchantRequest', i); return s.slice(i, j > 0 ? j + 20 : i + 200000); }, undefined, 5000);
        if (isGpc) {
          rec.frames_gpc = [];
          for (const f of page.frames().slice(0, 40)) { const r = await withTimeout(f.evaluate(() => ({ h: location.href.slice(0, 160), g: navigator.globalPrivacyControl === undefined ? 'undefined' : navigator.globalPrivacyControl })), 1500, 'fr').catch((e) => ({ err: String(e).slice(0, 60) })); rec.frames_gpc.push(r); }
          rec.workers_gpc = await ins.evalInWorkers(WORKER_VERIFY, 2000);
        }
      }
    }
  } catch (e) {
    rec.errors.push('load:' + String(e).slice(0, 300));
  }
  if (ins) { try { await withTimeout(Promise.allSettled(ins.bodyPromises), 8000, 'bodies'); } catch (e) { rec.errors.push('bodies_timeout'); } }
  const B = ins ? ins.bodies : {};
  try {
    const navs = (B.nav_html || []).filter((x) => x.text);
    rec.wpm = parseWpm(navs.length ? navs[0].text : null, env);
    if ((!rec.wpm || !rec.wpm.found) && typeof rec.wpm_dom === 'string') { const w2 = parseWpm(rec.wpm_dom, env); if (w2 && w2.found) { rec.wpm = w2; rec.wpm.source = 'dom'; } } else if (rec.wpm && rec.wpm.found) rec.wpm.source = 'html';
  } catch (e) { rec.errors.push('wpm:' + String(e).slice(0, 80)); }
  delete rec.wpm_dom;
  try { const ot = (B.otautoblock || []).find((x) => x.text); rec.otautoblock = ot ? { tags: parseOtAutoBlock(ot.text) } : null; } catch (e) { /* ignore */ }
  try { const cb = (B.cookiebot_cfg || []).find((x) => x.text); rec.cookiebot_cfg = cb ? { tags: parseCookiebotConfig(cb.text) } : null; } catch (e) { /* ignore */ }
  if (ins) {
    rec.targets_summary = summarizeTargets(ins);
    rec.requests = buildRequests(ins, rec, env);
  }
  try { if (cdp) cdp.close(); } catch (e) { /* ignore */ }
  try { if (ctx) await withTimeout(ctx.close(), 15000, 'close'); } catch (e) { rec.errors.push('close:' + String(e).slice(0, 80)); }
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) { /* ignore */ }
  rec.ended_at = new Date().toISOString();
  return rec;
}

// ---------------------------------------------------------------- parsing helpers (from crawl.js)
function parseWpm(html, env) {
  if (!html) return null;
  const m = html.match(/webPixelsConfigList:\s*(\[[\s\S]*?\])\s*,\s*isMerchantRequest/);
  if (!m) return { found: false, has_wpm_loader: /wpmLoader|web-pixels-manager-setup/.test(html) };
  try {
    const A2V = env.lib.vendors.APICLIENT2VENDOR;
    const lst = JSON.parse(m[1]);
    return { found: true, pixels: lst.map((x) => ({ id: String(x.id), type: x.type, rc: x.runtimeContext, api: x.apiClientId != null ? String(x.apiClientId) : null, pp: x.privacyPurposes || [], pp_key: Object.prototype.hasOwnProperty.call(x, 'privacyPurposes'), name: x.name || null, vendor: A2V[String(x.apiClientId)] || null })) };
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
function regDom(h) {
  h = (h || '').replace(/^www\./, '').toLowerCase();
  const parts = h.split('.');
  if (parts.length <= 2) return h;
  return /\.(co|com|net|org|gov|edu|ac)\.[a-z]{2}$/.test(h) ? parts.slice(-3).join('.') : parts.slice(-2).join('.');
}
function summarizeTargets(ins) {
  const c = {};
  for (const t of ins.targets.values()) c[t.type] = (c[t.type] || 0) + 1;
  return c;
}

// ---------------------------------------------------------------- request attribution (after crawl.js buildRequests)
// origin: strict_worker | lax_iframe | lax_nested (Shopify sandboxes) | open_pixel | open_pixel_chain (Shopify pixel
// in the main page) | wpm_main_proxy (main-page code called from Shopify's pixel manager) | main_thread | subframe |
// other_worker. Only vendor-map hits and Shopify pixel-manager URLs are kept, plus a count of everything else.
function buildRequests(ins, rec, env) {
  const V = env.lib.vendors;
  const reqs = ins.requests();
  const mainFrame = rec.main_frame_id;
  const nav = reqs.find((r) => r.is_nav && (!mainFrame || r.frame === mainFrame)) || reqs.find((r) => r.is_nav);
  const navWall = nav ? nav.wall : (rec.t_goto_start || ins.t0);
  rec.nav_wall = navWall;
  rec.navigations = reqs.filter((r) => r.is_nav && (!mainFrame || r.frame === mainFrame)).map((r) => ({ t: r.wall - navWall, url: r.url.slice(0, 600), st: r.st, server_timing_cmp: cmpHeader(r.resp_headers), redirected: !!r.redirected }));
  const storeHost = (() => { try { return new URL(rec.goto_url || rec.url).hostname; } catch (e) { return ''; } })();
  let canary = null; let pathQ = null; let pth = null;
  try { const U = new URL(rec.url); canary = U.searchParams.get('utm_campaign'); pathQ = U.pathname + '?'; pth = U.pathname.length > 1 ? U.pathname : null; } catch (e) { /* ignore */ }
  const landing = { canary, pathQ, path: pth, token: null };
  const laxOf = (frameId) => {
    let f = frameId; let depth = 0;
    while (f && depth < 12) {
      const fr = ins.frames.get(f); if (!fr) return null;
      const w = V.wpmUrl(fr.url || '');
      if (w && w.wpm === 'lax_iframe_sandbox') return { frameId: f, pixel: w.pixel_id, self: depth === 0 };
      if (/\/(web-pixels|wpm)@[^/]+\/.*\/sandbox\//.test(fr.url || '')) return { frameId: f, pixel: null, self: depth === 0 };
      f = fr.parentId; depth++;
    }
    return null;
  };
  const libOrigin = new Map();
  const all = [];
  let nOther = 0; let nTotal = 0;
  for (const r of reqs) {
    let host = ''; let pathn = '';
    try { const U = new URL(r.url); host = U.hostname; pathn = U.pathname; } catch (e) { /* data:/blob: */ }
    if (!host) continue;
    nTotal++;
    const t = r.wall != null ? r.wall - navWall : null;
    const tg = ins.targets.get(r.sid) || {};
    const sess = tg.type || 'root';
    let origin = 'main_thread'; let pixel = null; let container = 'd:' + (r.loader || r.frame || 'x');
    if (sess === 'worker' || sess === 'shared_worker' || sess === 'service_worker') {
      const wu = V.wpmUrl(tg.url || '');
      if (wu && wu.wpm === 'strict_worker_bootstrap') { origin = 'strict_worker'; pixel = wu.pixel_id; } else origin = 'other_worker';
      container = 'w:' + r.sid;
    } else if (r.frame && mainFrame && r.frame !== mainFrame) {
      const lx = laxOf(r.frame);
      if (lx) { origin = lx.self ? 'lax_iframe' : 'lax_nested'; pixel = lx.pixel; container = 'f:' + lx.frameId; } else { origin = 'subframe'; container = 'f:' + r.frame; }
    } else {
      const st = [r.ini_url].concat(r.ini_stack || []).filter(Boolean);
      const op = st.map((u) => V.wpmUrl(u)).find((x) => x && x.wpm === 'open_main_thread_pixel');
      if (op) { origin = 'open_pixel'; pixel = op.pixel_id; } else if (st.some((u) => libOrigin.get(u) === 'open_pixel' || libOrigin.get(u) === 'open_pixel_chain')) origin = 'open_pixel_chain';
      else if (st.some((u) => { const x = V.wpmUrl(u); return x && x.wpm === 'manager_bundle'; })) origin = 'wpm_main_proxy';
    }
    const vend = V.classifyVendor(r.url);
    const wpm = V.wpmUrl(r.url);
    if (vend && vend.kind === 'library') libOrigin.set(r.url, origin);
    const o = { t, container };
    if (vend || wpm) {
      let body = null; if (r.post_buf && r.post_buf.length) body = V.bodyText(r.post_buf);
      const flags = canary ? V.payloadFlags(r.url, body, landing) : {};
      Object.assign(o, { host, path: pathn.slice(0, 200), m: r.m, type: r.type, sess, origin });
      if (pixel) o.pixel = pixel;
      if (vend) { o.vendor = vend.vendor; o.vkind = vend.kind; o.ad = vend.ad; }
      if (wpm) { o.wpm = wpm.wpm; if (wpm.pixel_id) o.wpm_pixel = wpm.pixel_id; }
      if (r.m === 'OPTIONS') o.preflight = true;
      if (r.fail) o.fail = r.fail; if (r.blocked) o.blocked = r.blocked;
      if (flags.canary) o.page_url = true;
      const evn = V.eventNames(r.url, body); if (evn.length) o.events = evn;
      const tp = host !== storeHost && regDom(host) !== regDom(storeHost); if (tp) o.tp = true;
      o.keep = true;
    } else nOther++;
    all.push(o);
  }
  // first time each container (worker / sandbox iframe / document) issued any request
  const first = new Map();
  for (const o of all) if (o.t != null && (!first.has(o.container) || o.t < first.get(o.container))) first.set(o.container, o.t);
  const kept = all.filter((o) => o.keep).map((o) => { const x = Object.assign({}, o); delete x.keep; x.c_first = first.get(o.container); return x; });
  rec.n_requests = nTotal; rec.n_requests_not_kept = nOther;
  return kept;
}
function cmpHeader(h) {
  const st = (h && h['server-timing']) || '';
  const m = /_cmp;desc="([^"]+)"/.exec(st);
  return m ? m[1].slice(0, 120) : null;
}

module.exports = { captureArm, Pacer, sleep };
