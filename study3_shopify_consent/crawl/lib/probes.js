// Page-side probes (run in the page's main world through Playwright).
const fs = require('fs');
const path = require('path');
const SIG = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'cmp_signatures.json'), 'utf8'));

// Compact signature table passed into page functions
const CMP_SIGS = {};
for (const [k, c] of Object.entries(SIG.cmps)) {
  const d = c.detect || {};
  CMP_SIGS[k] = { dom: d.dom_selectors || [], globals: d.globals || [], reject_sel: (c.reject && c.reject.selectors) || [] };
}
const REJECT_RE = SIG._meta.generic_reject.text_regex;
const NEVER_RE = SIG._meta.generic_reject.never_click_regex;

// ---------------------------------------------------------------------------------------------
// Init script (every arm, top frame only): timestamps visitorConsentCollected events and the first
// time a consent banner becomes visible (CMP selectors every 250 ms; generic fixed/sticky
// cookie-notice detector every 1 s). All times are performance.now() (ms since navigation start).
const OBSERVER_SRC = `(() => {
  try { if (window.top !== window) return; } catch (e) { return; }
  if (window.__cs3) return;
  const S = window.__cs3 = { ev: [], banner: null, banner_present: null, ticks: 0 };
  const SIGS = ${JSON.stringify(Object.fromEntries(Object.entries(CMP_SIGS).map(([k, v]) => [k, v.dom])))};
  document.addEventListener('visitorConsentCollected', (e) => { try { S.ev.push({ t: Math.round(performance.now()), d: JSON.stringify(e.detail || null).slice(0, 400) }); } catch (_) {} }, true);
  // visible = on-screen area >= MIN_AREA px^2 AND checkVisibility (opacity/visibility/display of every
  // flat-tree ancestor, so shadow-DOM children of a hidden host do not count). v3 detector (2026-09-26).
  const MIN_AREA = 5000;
  const area = (el) => { const b = el.getBoundingClientRect(); const w = Math.min(b.right, innerWidth) - Math.max(b.left, 0); const h = Math.min(b.bottom, innerHeight) - Math.max(b.top, 0); return (w > 0 && h > 0) ? w * h : 0; };
  const cv = (el) => { try { return el.checkVisibility ? el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true, opacityProperty: true, visibilityProperty: true }) : true; } catch (e) { return true; } };
  const vis = (el, min) => { try { return area(el) >= (min || MIN_AREA) && cv(el) && parseFloat(getComputedStyle(el).opacity || '1') > 0.05; } catch (e) { return false; } };
  const hit = (el) => { try { const b = el.getBoundingClientRect(); const x = Math.min(Math.max((b.left + b.right) / 2, 1), innerWidth - 1); const y = Math.min(Math.max((b.top + b.bottom) / 2, 1), innerHeight - 1); let p = document.elementFromPoint(x, y); const r = el.getRootNode(); if (r && r.host && r.elementFromPoint) { const p2 = r.elementFromPoint(x, y); if (p2) p = p2; } return !!p && (el === p || el.contains(p) || (r && r.host && r.host.contains(p))); } catch (e) { return null; } };
  // A CMP container counts as a VISIBLE BANNER only if, inside it (light + shadow DOM), there is at least one
  // visible clickable control (>= 30 px^2, checkVisibility) and >= 20 characters of rendered text.
  // (v1 accepted any non-zero box and flagged Consentmo's empty full-viewport wrapper as a banner.)
  const CLICK = 'button, a, [role="button"], input[type="button"], input[type="submit"]';
  const deepQ = (root, sel, out, depth) => { out = out || []; depth = depth || 0; if (depth > 5 || out.length > 200) return out; let l = []; try { l = root.querySelectorAll(sel); } catch (e) { return out; } for (const x of l) out.push(x); let n = 0; for (const x of root.querySelectorAll('*')) { if (++n > 3000) break; if (x.shadowRoot) deepQ(x.shadowRoot, sel, out, depth + 1); } return out; };
  const deepText = (el) => { let t = (el.innerText || ''); const walk = (r, d) => { if (d > 5 || t.length > 400) return; for (const x of r.querySelectorAll('*')) { if (x.shadowRoot) { for (const c of x.shadowRoot.children) t += ' ' + (c.innerText || ''); walk(x.shadowRoot, d + 1); } } }; if (el.shadowRoot) { for (const c of el.shadowRoot.children) t += ' ' + (c.innerText || ''); walk(el.shadowRoot, 1); } walk(el, 0); return t.replace(/\\s+/g, ' ').trim(); };
  const visDeep = (el) => {
    const roots = [el]; if (el.shadowRoot) roots.push(el.shadowRoot);
    const ctrls = []; for (const r of roots) deepQ(r, CLICK, ctrls);
    const vc = ctrls.filter((b) => vis(b, 30));
    if (!vc.length) return null;
    const txt = deepText(el);
    if (txt.length < 20) return null;
    return { el: vc[0], n_ctrl: vc.length, txt: txt.slice(0, 200), ctrls: vc.slice(0, 8).map((b) => ((b.innerText || b.value || b.getAttribute('aria-label') || '') + '').trim().slice(0, 40)) };
  };
  const txtRe = /cookie|privacy|consent|personal (information|data)|tracking technolog|your choices|opt[- ]?out/i;
  const btnRe = /accept|agree|allow|got it|^ok$|okay|reject|decline|deny|opt[- ]?out|manage|preferences|settings|necessary|essential/i;
  const generic = () => {
    const all = document.body ? document.body.getElementsByTagName('*') : [];
    let n = 0;
    for (const el of all) {
      if (++n > 6000) break;
      let cs; try { cs = getComputedStyle(el); } catch (e) { continue; }
      if (cs.position !== 'fixed' && cs.position !== 'sticky' && !(el.getAttribute && (el.getAttribute('role') === 'dialog' || el.getAttribute('aria-modal') === 'true'))) continue;
      if (!vis(el)) continue;
      const t = (el.innerText || '').slice(0, 2500);
      if (!txtRe.test(t)) continue;
      const btns = [...el.querySelectorAll('button, a, [role="button"], input[type="button"], input[type="submit"]')].filter((b) => vis(b, 30)).map((b) => (b.innerText || b.value || b.getAttribute('aria-label') || '').trim()).filter((x) => x && x.length < 60);
      if (btns.some((b) => btnRe.test(b))) { try { el.setAttribute('data-cs3-banner', '1'); } catch (e) {} return { tag: el.tagName, id: el.id || null, text: t.replace(/\\s+/g, ' ').slice(0, 240), buttons: btns.slice(0, 10), area: Math.round(area(el)), hit: hit(el), det: 'v3' }; }
    }
    return null;
  };
  const tick = () => {
    S.ticks++;
    if (!document.body || S.banner) return;
    for (const [k, sels] of Object.entries(SIGS)) {
      for (const sel of sels) {
        let els = []; try { els = document.querySelectorAll(sel); } catch (e) { continue; }
        for (const el of els) {
          if (!S.banner_present) S.banner_present = { t: Math.round(performance.now()), cmp: k, sel };
          const ve = visDeep(el);
          if (ve) { S.banner = { t: Math.round(performance.now()), cmp: k, sel, how: 'cmp_selector', n_ctrl: ve.n_ctrl, ctrls: ve.ctrls, text: ve.txt, hit: hit(ve.el), det: 'v3' }; try { el.setAttribute('data-cs3-banner', '1'); } catch (e) {} return; }
        }
      }
    }
    if (S.ticks % 4 === 0) { const g = generic(); if (g) S.banner = Object.assign({ t: Math.round(performance.now()), cmp: null, how: 'generic' }, g); }
  };
  const iv = setInterval(() => { try { tick(); } catch (e) {} if (S.banner || performance.now() > 45000) clearInterval(iv); }, 250);
})();`;

// ---------------------------------------------------------------------------------------------
// Shopify Customer Privacy readout (cmp_signatures.json -> _meta.shopify_consent_readout)
function CONSENT_READ() {
  const o = { t: Math.round(performance.now()) };
  try {
    const cp = window.Shopify && window.Shopify.customerPrivacy;
    o.has_shopify = !!window.Shopify; o.has_cp = !!cp;
    if (cp) {
      for (const f of ['getRegion', 'shouldShowBanner', 'saleOfDataRegion', 'analyticsProcessingAllowed', 'marketingAllowed', 'preferencesProcessingAllowed', 'saleOfDataAllowed', 'currentVisitorConsent', 'getTrackingConsent', 'consentId']) {
        try { if (typeof cp[f] === 'function') { const v = cp[f](); o[f] = (v && typeof v === 'object') ? JSON.parse(JSON.stringify(v)) : v; } } catch (e) { o[f] = 'err'; }
      }
      o.cached = cp.cachedConsent ? JSON.stringify(cp.cachedConsent).slice(0, 300) : undefined;
    }
  } catch (e) { o.err = String(e).slice(0, 100); }
  try { const S = window.__cs3 || {}; o.banner_t = S.banner ? S.banner.t : null; o.nev = (S.ev || []).length; } catch (e) { /* ignore */ }
  try { o.gpc = navigator.globalPrivacyControl === undefined ? 'undefined' : navigator.globalPrivacyControl; } catch (e) { /* ignore */ }
  return o;
}

// ---------------------------------------------------------------------------------------------
// Find the CMP's Decline/Reject control (never Accept). Marks it with data-cs3-reject="1".
// Procedure = cmp_signatures.json _meta.generic_reject.procedure.
function FIND_REJECT(args) {
  const { sigs, rejectRe, neverRe } = args;
  const RR = new RegExp(rejectRe, 'i'); const NR = new RegExp(neverRe, 'i');
  const vis = (el) => { try { const b = el.getBoundingClientRect(); if (!(b.width > 1 && b.height > 1)) return false; if (b.bottom <= 0 || b.right <= 0 || b.top >= innerHeight || b.left >= innerWidth) return false; if (el.checkVisibility && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true, opacityProperty: true, visibilityProperty: true })) return false; const cs = getComputedStyle(el); return cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity || '1') > 0.05; } catch (e) { return false; } };
  const deepAll = (root, sel, out, depth) => {
    out = out || []; depth = depth || 0; if (depth > 6) return out;
    let list = []; try { list = root.querySelectorAll(sel); } catch (e) { /* bad selector */ }
    for (const el of list) out.push(el);
    let all = []; try { all = root.querySelectorAll('*'); } catch (e) { /* ignore */ }
    let n = 0; for (const el of all) { if (++n > 20000) break; if (el.shadowRoot) deepAll(el.shadowRoot, sel, out, depth + 1); }
    return out;
  };
  const textOf = (b) => ((b.innerText || b.value || b.getAttribute('aria-label') || b.getAttribute('title') || '') + '').replace(/\s+/g, ' ').trim();
  const CLICK = 'button, a, [role="button"], input[type="button"], input[type="submit"]';
  const containers = [];
  for (const [k, s] of Object.entries(sigs)) {
    for (const sel of s.dom) for (const el of deepAll(document, sel)) { if (!containers.some((c) => c.el === el)) containers.push({ el, cmp: k, sel }); }
  }
  for (const el of deepAll(document, '[data-cs3-banner="1"]')) if (!containers.some((c) => c.el === el)) containers.push({ el, cmp: null, sel: '[data-cs3-banner]' });
  const seen = []; const cand = [];
  for (const c of containers) {
    const roots = [c.el]; if (c.el.shadowRoot) roots.push(c.el.shadowRoot);
    for (const r of roots) for (const b of deepAll(r, CLICK)) { if (seen.includes(b)) continue; seen.push(b); if (vis(b)) cand.push({ b, cmp: c.cmp, t: textOf(b) }); }
  }
  const texts = cand.map((x) => x.t).filter(Boolean).slice(0, 20);
  let pick = cand.find((x) => x.t && x.t.length < 80 && RR.test(x.t));
  let how = pick ? 'text_regex' : null;
  if (!pick) {
    for (const [k, s] of Object.entries(sigs)) {
      for (const sel of s.reject_sel) {
        for (const b of deepAll(document, sel)) {
          const t = textOf(b);
          if (!vis(b)) continue;
          if (NR.test(t) && !RR.test(t)) continue;
          pick = { b, cmp: k, t }; how = 'cmp_selector:' + sel; break;
        }
        if (pick) break;
      }
      if (pick) break;
    }
  }
  const iframeBanner = [...document.querySelectorAll('iframe')].some((f) => /sp_message_iframe|consent|cookie|privacy|cmp/i.test((f.id || '') + ' ' + (f.src || '') + ' ' + (f.title || '')) && vis(f));
  if (!pick) return { found: false, n_containers: containers.length, containers: containers.slice(0, 5).map((c) => c.cmp + ':' + c.sel), buttons: texts, iframe_banner: iframeBanner };
  for (const el of deepAll(document, '[data-cs3-reject]')) el.removeAttribute('data-cs3-reject');
  pick.b.setAttribute('data-cs3-reject', '1');
  const bb = pick.b.getBoundingClientRect();
  return { found: true, how, cmp: pick.cmp, text: pick.t.slice(0, 80), tag: pick.b.tagName, id: pick.b.id || null, cls: (pick.b.className && pick.b.className.toString ? pick.b.className.toString() : '').slice(0, 100), rect: [Math.round(bb.x), Math.round(bb.y), Math.round(bb.width), Math.round(bb.height)], buttons: texts, n_containers: containers.length, iframe_banner: iframeBanner };
}

// Native JS click fallback on the marked element (used only if Playwright's click fails)
function JS_CLICK_REJECT() {
  const deep = (root) => { const e = root.querySelector('[data-cs3-reject="1"]'); if (e) return e; for (const el of root.querySelectorAll('*')) if (el.shadowRoot) { const x = deep(el.shadowRoot); if (x) return x; } return null; };
  const el = deep(document); if (!el) return false; el.click(); return true;
}

// ---------------------------------------------------------------------------------------------
// CMP detection + declared configuration + page hints
function CMP_PROBE(sigs) {
  const r = { cmp: {} };
  const vis = (el) => { try { const b = el.getBoundingClientRect(); const w = Math.min(b.right, innerWidth) - Math.max(b.left, 0); const h = Math.min(b.bottom, innerHeight) - Math.max(b.top, 0); if (!(w > 0 && h > 0 && w * h >= 5000)) return false; if (el.checkVisibility && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true, opacityProperty: true, visibilityProperty: true })) return false; return parseFloat(getComputedStyle(el).opacity || '1') > 0.05; } catch (e) { return false; } };
  for (const [k, s] of Object.entries(sigs)) {
    const g = s.globals.filter((x) => { try { return typeof window[x] !== 'undefined'; } catch (e) { return false; } });
    let dom = null;
    for (const sel of s.dom) { let els = []; try { els = [...document.querySelectorAll(sel)]; } catch (e) { continue; } if (els.length) { const v = els.some((el) => vis(el) || (el.shadowRoot && [...el.shadowRoot.querySelectorAll('*')].slice(0, 300).some(vis))); if (!dom || v) dom = v ? 'visible' : 'present_hidden'; if (v) break; } }
    if (g.length || dom) r.cmp[k] = { globals: g, dom };
  }
  const dc = {};
  try {
    const P = window.PandectesSettings;
    if (P) {
      const b = P.blocker || {}; const pat = b.patterns || {};
      dc.pandectes = { isActive: b.isActive, defaultBlocked: b.defaultBlocked, gpcIsActive: b.gpcIsActive, blackList: pat.blackList || null, iframesBlackList: pat.iframesBlackList || null, beaconsBlackList: pat.beaconsBlackList || null,
        googleConsentMode: b.googleConsentMode ? { isActive: b.googleConsentMode.isActive, adStorageCategory: b.googleConsentMode.adStorageCategory, analyticsStorageCategory: b.googleConsentMode.analyticsStorageCategory } : null,
        geolocation: P.geolocation ? JSON.parse(JSON.stringify(P.geolocation)) : null, keys: Object.keys(P).slice(0, 40) };
    }
    const R = window.PandectesRulesSettings;
    if (R) { const b = R.blocker || {}; const pat = b.patterns || {}; dc.pandectes_rules = { cookiesBlockedByDefault: R.banner && R.banner.cookiesBlockedByDefault, isActive: b.isActive, defaultBlocked: b.defaultBlocked, gpcIsActive: b.gpcIsActive, blackList: pat.blackList || null, iframesBlackList: pat.iframesBlackList || null, beaconsBlackList: pat.beaconsBlackList || null, geolocation: R.geolocation ? JSON.parse(JSON.stringify(R.geolocation)) : null, keys: Object.keys(R).slice(0, 30) }; }
    const R5 = window.pandectesRulesSettings;
    if (R5) dc.pandectes_v5 = { version: R5.version, banner: R5.banner ? JSON.parse(JSON.stringify(R5.banner)) : null, regions: R5.regions ? JSON.parse(JSON.stringify(R5.regions)) : null, gpc: R5.gpc ? JSON.parse(JSON.stringify(R5.gpc)) : null, blocker: R5.blocker ? JSON.parse(JSON.stringify(R5.blocker)) : null };
  } catch (e) { dc.pandectes_err = String(e).slice(0, 100); }
  try { dc.onetrust = { activeGroups: window.OnetrustActiveGroups || window.OptanonActiveGroups || null, autoblock_script: !![...document.scripts].find((s) => /OtAutoBlock\.js/.test(s.src || '')) }; if (!window.OneTrust && !dc.onetrust.activeGroups && !dc.onetrust.autoblock_script) delete dc.onetrust; } catch (e) { /* ignore */ }
  try {
    if (window.Cookiebot) {
      const c = window.Cookiebot; const sc = [...document.scripts].find((s) => /consent\.cookiebot\.(com|eu)\/uc\.js/.test(s.src || ''));
      dc.cookiebot = { consented: c.consented, declined: c.declined, hasResponse: c.hasResponse, consent: c.consent ? { necessary: c.consent.necessary, preferences: c.consent.preferences, statistics: c.consent.statistics, marketing: c.consent.marketing, method: c.consent.method } : null, blockingmode: sc ? sc.getAttribute('data-blockingmode') : null };
    }
  } catch (e) { /* ignore */ }
  try { if (window.Osano && window.Osano.cm) { const cm = window.Osano.cm; dc.osano = { consent: cm.getConsent ? JSON.parse(JSON.stringify(cm.getConsent())) : null, mode: cm.mode || null }; } } catch (e) { /* ignore */ }
  try { if (window.Didomi && window.Didomi.getUserStatus) dc.didomi = { status: JSON.parse(JSON.stringify(window.Didomi.getUserStatus())).purposes || null }; } catch (e) { /* ignore */ }
  try { if (window.UC_UI && window.UC_UI.getServicesBaseInfo) dc.usercentrics = { services: window.UC_UI.getServicesBaseInfo().slice(0, 80).map((s) => ({ n: s.name, cat: s.categorySlug, st: s.consent && s.consent.status })) }; } catch (e) { /* ignore */ }
  try { if (window.airgap) dc.transcend = { purposes: window.airgap.getConsent ? JSON.parse(JSON.stringify(window.airgap.getConsent())).purposes || null : null }; } catch (e) { /* ignore */ }
  r.declared = dc;
  try {
    const txt = (document.body ? document.body.innerText : '').toLowerCase();
    r.bot_wall_hints = ['access denied', 'just a moment', 'verify you are human', 'are you a robot', 'pardon our interruption', 'press & hold', 'captcha', 'request blocked', 'unusual traffic', 'checking your browser', 'not a robot', 'enable javascript and cookies'].filter((k) => txt.slice(0, 5000).includes(k));
    r.text_len = txt.length;
    r.consent_text_hints = ['accept all', 'reject all', 'decline', 'we use cookies', 'your privacy choices', 'do not sell', 'manage preferences', 'cookie settings'].filter((k) => txt.includes(k));
  } catch (e) { /* ignore */ }
  r.title = (document.title || '').slice(0, 150);
  r.location = location.href.slice(0, 500);
  r.has_shopify = typeof window.Shopify !== 'undefined';
  r.shop = (window.Shopify && window.Shopify.shop) || null;
  r.wpm = typeof window.webPixelsManager !== 'undefined' || !!document.querySelector('script#web-pixels-manager-setup');
  r.nostra = typeof window.Nostra !== 'undefined' || !![...document.scripts].find((s) => /\/_nostra\//.test(s.src || ''));
  try { r.gpc = navigator.globalPrivacyControl === undefined ? 'undefined' : navigator.globalPrivacyControl; } catch (e) { /* ignore */ }
  r.ua = navigator.userAgent;
  r.webdriver = navigator.webdriver;
  try { const S = window.__cs3 || {}; r.cs3 = { banner: S.banner, banner_present: S.banner_present, ev: S.ev, ticks: S.ticks }; } catch (e) { /* ignore */ }
  return r;
}

module.exports = { SIG, CMP_SIGS, REJECT_RE, NEVER_RE, OBSERVER_SRC, CONSENT_READ, FIND_REJECT, JS_CLICK_REJECT, CMP_PROBE };
