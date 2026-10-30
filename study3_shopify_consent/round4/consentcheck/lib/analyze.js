// Turn the three captured visits into verdicts, findings and fixes. Pure function of the arm records, so a saved
// raw file can be re-analysed (`--from-raw`). Definitions follow the study (analysis/common.py):
//   ad request  request to a vendor marked is_advertising in crawl/vendor_endpoints.json; CORS preflights excluded
//   sandboxed   origin strict_worker (web worker), lax_iframe (sandboxed iframe) or lax_nested (frame inside it)
//   before any choice  every request of the Default visit; Decline visit requests before the click
const SANDBOX = new Set(['strict_worker', 'lax_iframe', 'lax_nested']);
const SHOPIFY_OWN = new Set(['shopify-app-pixel', 'shopify-custom-pixel']);
const PURPOSE_LABEL = { ANALYTICS: 'analytics', MARKETING: 'marketing', PREFERENCES: 'preferences', SALE_OF_DATA: 'data sale' };

function where(origin) {
  if (SANDBOX.has(origin)) return 'sandbox';
  if (origin === 'open_pixel' || origin === 'open_pixel_chain') return 'shopify_open';
  return 'page';
}
const WHERE_LABEL = {
  sandbox: "Shopify's pixel sandbox",
  shopify_open: 'main page (Shopify pixel in OPEN mode)',
  page: 'main page (theme, tag manager or app script)',
};
const ORIGIN_LABEL = {
  strict_worker: 'sandbox: web worker (STRICT)', lax_iframe: 'sandbox: hidden iframe (LAX)', lax_nested: 'sandbox: frame inside the LAX iframe',
  open_pixel: 'main page: Shopify OPEN pixel', open_pixel_chain: 'main page: library loaded by an OPEN pixel', wpm_main_proxy: "main page: called from Shopify's pixel manager",
  main_thread: 'main page script', subframe: 'ordinary iframe in the page', other_worker: 'other web worker',
};

function decodeCmp(v) {
  if (!v || !v.startsWith('3')) return null;
  const parts = v.slice(1).split('_'); const head = parts[0];
  const [choices, purposes] = head.split('.').concat(['']);
  const choice = (ch) => (choices.includes(ch.toLowerCase()) ? 'declined' : (choices.includes(ch.toUpperCase()) ? 'accepted' : 'none'));
  return { raw: v.slice(0, 40), choice_marketing: choice('m'), choice_sale: choice('s'), allow_analytics: purposes.includes('A'), allow_marketing: purposes.includes('M'), allow_preferences: purposes.includes('P'), allow_sale: purposes.includes('S'),
    region: parts[1] || '', banner_required: parts[2] === 't' ? true : (parts[2] === 'f' ? false : null), sale_of_data_region: parts[3] === 't' ? true : (parts[3] === 'f' ? false : null) };
}

function loadOk(rec) {
  if (!rec) return { ok: false, why: 'not run' };
  if (rec.aborted) return { ok: false, why: rec.aborted };
  if (rec.goto_error && !rec.goto_status) return { ok: false, why: rec.goto_error };
  if (!(rec.goto_status >= 200 && rec.goto_status < 400)) return { ok: false, why: 'HTTP ' + rec.goto_status + ([401, 403, 429, 503].includes(rec.goto_status) ? ' (the site may be blocking automated browsers)' : '') };
  const pr = rec.probe || {};
  // as in the study: bot-check words count only when the page is not a working Shopify page ("captcha" also appears in
  // ordinary reCAPTCHA notices)
  if (pr && pr.bot_wall_hints && pr.bot_wall_hints.length && pr.has_shopify !== true) return { ok: false, why: 'the page looked like a bot check: ' + pr.bot_wall_hints.join(', ') };
  if (pr && pr.has_shopify === false) return { ok: false, why: 'window.Shopify not found: this does not look like a Shopify storefront page' };
  if ((rec.n_requests || 0) <= 20) return { ok: false, why: 'too few requests (' + (rec.n_requests || 0) + ')' };
  return { ok: true };
}

const rel = (rec, epoch) => (epoch && rec.nav_wall ? epoch - rec.nav_wall : null);

// Explicit consent values the page's Customer Privacy API reported, in navigation time (ms)
function consentTimeline(rec) {
  const out = [];
  for (const c of rec.consent || []) {
    if (!c || c.__err || !c.has_cp) continue;
    const cv = c.currentVisitorConsent || {};
    out.push({ t: rel(rec, c.epoch), tag: c.tag, marketing: cv.marketing || '', sale_of_data: cv.sale_of_data || '', analytics: cv.analytics || '', tracking: typeof c.getTrackingConsent === 'string' ? c.getTrackingConsent : '',
      marketingAllowed: c.marketingAllowed, saleOfDataAllowed: c.saleOfDataAllowed, analyticsAllowed: c.analyticsProcessingAllowed, region: c.getRegion || null });
  }
  return out;
}
function consentEvents(rec, probe) {
  const ev = (probe && probe.cs3 && probe.cs3.ev) || [];
  return ev.map((e) => { let d = null; try { d = JSON.parse(e.d); } catch (x) { /* ignore */ } return { t: rec.time_origin && rec.nav_wall ? Math.round(rec.time_origin + e.t - rec.nav_wall) : e.t, detail: d }; });
}
function bannerOf(rec) {
  if (rec.arm === 'decline' && rec.banner_wait) {
    const b = rec.banner_wait.banner;
    return b ? { visible: true, t: rec.time_origin && rec.nav_wall ? Math.round(rec.time_origin + b.t - rec.nav_wall) : b.t, cmp: b.cmp || null, controls: b.ctrls || b.buttons || [], text: b.text || null } : { visible: false };
  }
  const b = rec.probe && rec.probe.cs3 && rec.probe.cs3.banner;
  return b ? { visible: true, t: rec.time_origin && rec.nav_wall ? Math.round(rec.time_origin + b.t - rec.nav_wall) : b.t, cmp: b.cmp || null, controls: b.ctrls || b.buttons || [], text: b.text || null } : { visible: false };
}
function cmpsDetected(...probes) {
  const s = new Set();
  for (const p of probes) if (p && p.cmp) for (const [k, v] of Object.entries(p.cmp)) if ((v.globals && v.globals.length) || v.dom) s.add(k);
  return [...s];
}

// ---------------------------------------------------------------- declared blocklists (after crawl/build_tables.py)
function declaredBlocklist(rec, cmp, env) {
  const V = env.lib.vendors;
  const vendorOfHost = (h) => { h = (h || '').toLowerCase().replace(/^\*?\.?/, ''); const v = V.VENDORS.find((x) => x.host.test(h)); return v ? v.vendor : null; };
  const out = {};
  const put = (v, pre, detail) => { if (!v) return; const cur = out[v]; if (!cur || (pre === 'blocked' && cur.pre !== 'blocked')) out[v] = { pre, detail }; };
  const pr = (rec.arm === 'decline' && rec.probe_first) ? rec.probe_first : rec.probe;
  const dc = (pr && pr.declared) || {};
  if (cmp === 'pandectes') {
    for (const key of ['pandectes', 'pandectes_rules']) {
      const p = dc[key]; if (!p || !p.blackList) continue;
      const db = parseInt(p.defaultBlocked != null ? p.defaultBlocked : (p.cookiesBlockedByDefault || 0), 10) || 0;
      for (const ln of ['blackList', 'iframesBlackList', 'beaconsBlackList']) {
        let bl = p[ln] || {}; if (Array.isArray(bl)) bl = { 0: bl };
        for (const [cat, pats] of Object.entries(bl)) {
          const c = parseInt(cat, 10) || 0;
          for (const pat of pats || []) for (const alt of String(pat).split('|')) put(vendorOfHost(alt.trim().split('/')[0].replace(/\\/g, '')), p.isActive && (db & c) ? 'blocked' : 'listed_allowed', `Pandectes ${ln}[${cat}] ${alt.slice(0, 50)}`);
        }
      }
    }
    const p5 = dc.pandectes_v5;
    if (p5 && p5.blocker) {
      const reg = (consentTimeline(rec).find((x) => x.region) || {}).region || '';
      const strict = (p5.regions && p5.regions.strict) || [];
      const optin = !!reg && (strict.includes(reg) || strict.includes(reg.slice(0, 2)));
      for (const ln of ['scripts', 'iframes', 'pixels']) for (const [cat, pats] of Object.entries(p5.blocker[ln] || {})) {
        const c = parseInt(cat, 10) || 0;
        for (const pat of pats || []) for (const alt of String(pat).split('|')) { const a2 = alt.trim().replace(/^https?:\/\//, '').replace(/\\/g, ''); put(vendorOfHost(a2.split('/')[0].split('?')[0]), p5.blocker.enabled && optin && c ? 'blocked' : 'listed_allowed', `Pandectes ${ln}[${cat}] ${alt.slice(0, 50)}`); }
      }
    }
  }
  if (cmp === 'onetrust' && rec.otautoblock && rec.otautoblock.tags) {
    const ag = ((dc.onetrust || {}).activeGroups || '');
    const active = new Set(ag.split(/[,\s]+/).filter(Boolean));
    for (const tg of rec.otautoblock.tags) { const m = /^(?:https?:)?\/\/([^/]+)/.exec(tg.tag || ''); if (!m) continue; put(vendorOfHost(m[1]), (tg.cat || []).some((c) => active.has(c)) ? 'listed_allowed' : 'blocked', `OneTrust auto-block ${m[1]} (${(tg.cat || []).join(',')})`); }
  }
  if (cmp === 'cookiebot' && rec.cookiebot_cfg && rec.cookiebot_cfg.tags) {
    const cb = dc.cookiebot || {}; const cons = cb.consent || {};
    const allowed = new Set([1]); if (cons.preferences) allowed.add(2); if (cons.statistics) allowed.add(3); if (cons.marketing) allowed.add(4);
    const auto = (cb.blockingmode || '') === 'auto';
    for (const tg of rec.cookiebot_cfg.tags) { const m = /^(?:https?:)?\/\/([^/]+)/.exec(tg.url || ''); if (!m) continue; const cats = tg.cat || []; put(vendorOfHost(m[1]), auto && !cats.every((c) => allowed.has(c)) ? 'blocked' : 'listed_allowed', `Cookiebot auto-blocking ${m[1]} (cat ${cats.join(',')})`); }
  }
  return out;
}

// ---------------------------------------------------------------- main
function analyze(raw, env, meta) {
  const V = env.lib.vendors;
  const VINFO = {}; for (const v of V.VENDORS) if (!VINFO[v.vendor]) { VINFO[v.vendor] = v; VNAME[v.vendor] = v.display; }
  const A = raw.arms || {};
  const D = A.default; const R = A.decline; const G = A.gpc;
  const ok = { default: loadOk(D), decline: loadOk(R), gpc: loadOk(G) };

  // ---- pixel configuration (first usable load)
  const cfgSrc = [D, R, G].find((r) => r && r.wpm && r.wpm.found && r.wpm.pixels);
  const pixels = cfgSrc ? cfgSrc.wpm.pixels : [];
  const pixById = Object.fromEntries(pixels.map((p) => [String(p.id), p]));

  // ---- Decline timing
  const clicked = !!(R && R.clicks && R.clicks.t_click_epoch && ['playwright_click', 'playwright_force', 'js_click'].includes(R.clicks.method));
  const tClick = clicked ? rel(R, R.clicks.t_click_epoch) : null;
  const tNext = R && R.next_goto_epoch ? rel(R, R.next_goto_epoch) : null;

  // ---- per-request phase
  const phaseOf = (arm, q) => {
    if (arm !== 'decline' || !clicked) return 'window';
    if (q.t == null || q.t < tClick) return 'before';
    if (tNext == null || q.t < tNext) return 'same_page';
    return (q.c_first != null && q.c_first < tNext) ? 'unload' : 'next_page';
  };
  const adReqs = [];
  for (const [arm, rec] of Object.entries(A)) {
    if (!rec || !ok[arm].ok) continue;
    for (const q of rec.requests || []) {
      if (!q.vendor || !q.ad || q.preflight) continue;
      adReqs.push(Object.assign({ arm, phase: phaseOf(arm, q), where: where(q.origin) }, q));
    }
  }
  // pixel -> vendors it contacted (any arm, any vendor incl. non-ad), for the pixel table
  const pixVendors = {};
  for (const rec of [D, R, G]) for (const q of (rec && rec.requests) || []) if (q.pixel && q.vendor) (pixVendors[q.pixel] = pixVendors[q.pixel] || new Set()).add(q.vendor);

  // ---- Shopify / consent-tool state
  // Shopify's consent header of a navigation's final (non-redirect) response; the first page, or the last one
  const navCmp = (rec, last) => { const ns = ((rec && rec.navigations) || []).filter((n) => n.server_timing_cmp && !n.redirected); const n = last ? ns[ns.length - 1] : ns[0]; return n ? decodeCmp(n.server_timing_cmp) : null; };
  const hdrDefault = navCmp(D); const hdrGpc = navCmp(G);
  const hdrNext = R && R.next_goto_epoch ? navCmp(R, true) : null;
  const tlD = D ? consentTimeline(D) : []; const tlR = R ? consentTimeline(R) : []; const tlG = G ? consentTimeline(G) : [];
  const region = (tlD.find((x) => x.region) || tlR.find((x) => x.region) || {}).region || (hdrDefault && hdrDefault.region) || null;
  const bannerD = D ? bannerOf(D) : { visible: false }; const bannerR = R ? bannerOf(R) : { visible: false };
  const bannerShown = !!(bannerD.visible || bannerR.visible);
  const cmps = cmpsDetected(D && D.probe, R && R.probe_first, R && R.probe, G && G.probe);
  let cmp = bannerR.cmp || bannerD.cmp || null;
  if (!cmp && cmps.length === 1) cmp = cmps[0];
  if (!cmp && cmps.length > 1) { const nn = cmps.filter((c) => c !== 'shopify_native'); cmp = nn.length === 1 ? nn[0] : 'multiple'; }
  const cmpName = cmp ? (CMP_NAMES[cmp] || cmp) : null;

  // automatic writes before any choice (Default visit): explicit yes/no in the API or a consent event
  const evD = D ? consentEvents(D, D.probe) : [];
  const autoYes = tlD.find((x) => x.marketing === 'yes' || x.tracking === 'yes');
  const autoNo = tlD.find((x) => x.marketing === 'no' || x.tracking === 'no');
  const evNo = evD.find((e) => e.detail && e.detail.marketingAllowed === false);
  const evYes = evD.find((e) => e.detail && e.detail.marketingAllowed === true);
  const firstNoT = [autoNo && autoNo.t, evNo && evNo.t].filter((x) => x != null).sort((a, b) => a - b)[0];
  const firstYesT = [autoYes && autoYes.t, evYes && evYes.t].filter((x) => x != null).sort((a, b) => a - b)[0];
  const firstSbxD = adReqs.filter((q) => q.arm === 'default' && q.where === 'sandbox' && q.t != null).map((q) => q.t).sort((a, b) => a - b)[0];
  const firstAdD = adReqs.filter((q) => q.arm === 'default' && q.t != null).map((q) => q.t).sort((a, b) => a - b)[0];

  // Decline written to Shopify?
  let declineRecord = { status: 'not_tested' };
  if (R && ok.decline.ok) {
    if (!(R.banner_wait && R.banner_wait.found)) declineRecord = { status: 'no_banner' };
    else if (R.no_decline_option || (R.clicks && R.clicks.refused)) declineRecord = { status: 'no_decline_button', buttons: (R.clicks && R.clicks.find && R.clicks.find.buttons) || [] };
    else if (!clicked) declineRecord = { status: 'click_failed' };
    else {
      const after = tlR.filter((x) => x.t != null && x.t >= tClick);
      const no = after.find((x) => x.marketing === 'no' || x.tracking === 'no');
      const saleNo = after.find((x) => x.sale_of_data === 'no' || x.saleOfDataAllowed === false);
      const last = after.filter((x) => x.tag !== 'next_page' && x.tag !== 'end').slice(-1)[0] || after.slice(-1)[0] || {};
      const gone = !(R.clicks.banner_after && R.clicks.banner_after.found);
      if (no) declineRecord = { status: saleNo ? 'recorded' : 'recorded_marketing_only', t: no.t, delay_ms: no.t - tClick, banner_gone: gone, next_page_header: hdrNext ? hdrNext.raw : null };
      else if (last.marketingAllowed === true) declineRecord = { status: 'not_recorded_still_allowed', banner_gone: gone };
      else declineRecord = { status: 'not_recorded_default_denied', banner_gone: gone };
      declineRecord.clicked_text = R.clicks.find && R.clicks.find.text;
      declineRecord.after_click = after.filter((x) => x.tag === 'click+1' || x.tag === 'end').map((x) => ({ tag: x.tag, marketing: x.marketing, sale_of_data: x.sale_of_data, marketingAllowed: x.marketingAllowed, saleOfDataAllowed: x.saleOfDataAllowed }));
    }
  }
  // state after the decline (last reading of the first page) -> allowed purposes
  const afterDecl = clicked ? tlR.filter((x) => x.t != null && x.t >= tClick).slice(-1)[0] : null;
  const allowedAfterDecline = afterDecl ? { ANALYTICS: afterDecl.analyticsAllowed !== false, MARKETING: afterDecl.marketingAllowed !== false, SALE_OF_DATA: afterDecl.saleOfDataAllowed !== false } : null;
  const gpcEnd = tlG.slice(-1)[0] || null;
  const gpcRecorded = G && ok.gpc.ok ? ((hdrGpc && hdrGpc.choice_sale === 'declined') || (gpcEnd && gpcEnd.saleOfDataAllowed === false)) : null;
  const gpcVisible = G && ok.gpc.ok ? { frames: (G.frames_gpc || []).filter((f) => f.g === true).length + '/' + (G.frames_gpc || []).length, workers: (G.workers_gpc || []).filter((w) => w.val && w.val.gpc === 'true').length + '/' + (G.workers_gpc || []).length } : null;

  // ---- per-vendor verdicts
  const blk = cmp ? Object.assign({}, D ? declaredBlocklist(D, cmp, env) : {}, R ? declaredBlocklist(R, cmp, env) : {}) : {};
  const vendorKeys = [...new Set(adReqs.map((q) => q.vendor))];
  const summ = (list) => {
    if (!list.length) return { sent: false, n: 0 };
    const pix = [...new Set(list.map((q) => q.pixel).filter(Boolean))];
    return { sent: true, n: list.length, beacons: list.filter((q) => q.vkind !== 'library').length, where: [...new Set(list.map((q) => q.where))], origins: [...new Set(list.map((q) => q.origin))],
      pixels: pix, first_t: list.map((q) => q.t).filter((x) => x != null).sort((a, b) => a - b)[0] ?? null, page_url: list.some((q) => q.page_url), endpoints: [...new Set(list.map((q) => q.host + q.path.replace(/\/[^/]*\d{5,}[^/]*/g, '/…')))].slice(0, 4) };
  };
  const vendors = vendorKeys.map((v) => {
    const q = adReqs.filter((x) => x.vendor === v);
    const d = summ(q.filter((x) => x.arm === 'default'));
    const r = { before: summ(q.filter((x) => x.arm === 'decline' && (x.phase === 'before' || x.phase === 'window'))), same_page: summ(q.filter((x) => x.arm === 'decline' && x.phase === 'same_page')), unload: summ(q.filter((x) => x.arm === 'decline' && x.phase === 'unload')), next_page: summ(q.filter((x) => x.arm === 'decline' && x.phase === 'next_page')) };
    const g = summ(q.filter((x) => x.arm === 'gpc'));
    const pre = ok.default.ok ? (d.sent ? 'sends' : 'silent') : 'not_tested';
    let decl = 'not_tested';
    if (ok.decline.ok && clicked) decl = r.next_page.sent ? 'not_stopped' : ((r.same_page.sent || r.unload.sent) ? 'partly' : ((r.before.sent || d.sent) ? 'stopped' : 'not_seen'));
    let gpc = 'not_tested';
    if (ok.gpc.ok) gpc = g.sent ? 'not_stopped' : (d.sent || r.before.sent ? 'stopped' : 'not_seen');
    const pixIds = [...new Set([].concat(d.pixels || [], r.before.pixels || [], r.next_page.pixels || [], r.same_page.pixels || [], g.pixels || []))];
    const pixInfo = pixIds.map((id) => pixelLabel(pixById[id], id));
    const why = explainVendor({ d, r, g, decl, gpc, pixById, allowedAfterDecline, gpcRecorded, declineRecord });
    const info = VINFO[v] || {};
    return { vendor: v, name: info.display || v, group: info.color || null, before_choice: pre, where_before: d.where || [], decline: decl, gpc, pixels: pixInfo, declared_by_banner: blk[v] || null,
      blocked_on_paper: !!(blk[v] && blk[v].pre === 'blocked' && d.sent && (d.where || []).includes('sandbox')), detail: { default: d, decline: r, gpc: g }, why };
  }).sort((a, b) => (rank(b) - rank(a)) || a.name.localeCompare(b.name));

  // ---- pixel table
  const sentBy = {};
  for (const q of adReqs) if (q.pixel) (sentBy[q.pixel] = sentBy[q.pixel] || new Set()).add(q.arm + ':' + q.phase);
  const pixelRows = pixels.map((p) => {
    const own = SHOPIFY_OWN.has(String(p.id));
    const contacted = [...(pixVendors[p.id] || [])].map((v) => (VINFO[v] || {}).display || v);
    const adSent = !!sentBy[p.id];
    const noPurpose = !own && (!p.pp || p.pp.length === 0);
    const mktNoSale = !own && p.pp && p.pp.includes('MARKETING') && !p.pp.includes('SALE_OF_DATA');
    return { id: String(p.id), type: p.type, runtime: p.rc, runtime_label: p.rc === 'STRICT' ? 'sandbox (web worker)' : p.rc === 'LAX' ? 'sandbox (hidden iframe)' : p.rc === 'OPEN' ? 'main page' : (p.rc || '?'),
      name: p.name || (own ? "Shopify's own pixel" : null), app: p.vendor ? ((VINFO[p.vendor] || {}).display || p.vendor) : (p.type === 'APP' ? `app (API client ${p.api})` : null),
      purposes: (p.pp || []).map((x) => PURPOSE_LABEL[x] || x), shopify_own: own, contacted, sent_ad_data: adSent, sent_when: [...(sentBy[p.id] || [])],
      flags: { no_purpose: noPurpose, marketing_without_data_sale: mktNoSale } };
  });

  // ---- findings and fixes
  const F = []; const fixes = new Set();
  const add = (id, sev, title, text, fx, evidence) => { F.push({ id, severity: sev, title, text, fixes: fx || [], evidence: evidence || null }); (fx || []).forEach((x) => fixes.add(x)); };
  const vn = (list) => list.map((v) => v.name).join(', ');
  const preSenders = vendors.filter((v) => v.before_choice === 'sends');
  const preSbx = preSenders.filter((v) => v.where_before.includes('sandbox'));
  const regionAllows = hdrDefault ? hdrDefault.allow_marketing : null;

  if (!ok.default.ok && !ok.decline.ok && !ok.gpc.ok) add('no_usable_load', 'info', 'No usable page load', `None of the three visits produced a usable Shopify page (${ok.default.why}). Nothing below can be trusted; try another page of the store, or run again later.`, []);
  if (bannerShown && preSenders.length) {
    add('sent_before_choice', 'high', `${preSenders.length} ad ${preSenders.length === 1 ? 'vendor' : 'vendors'} received data before the visitor chose`,
      `Your banner asks visitors to choose, but ${vn(preSenders)} sent requests before any choice was made${preSbx.length ? `; ${vn(preSbx)} did so from Shopify's pixel sandbox, which your consent app's script blocking cannot reach` : ''}.${regionAllows ? ' Shopify\'s own setting for this visitor\'s region was "allowed until the visitor opts out", so Shopify let the pixels start.' : ''}`,
      regionAllows ? ['region_default', 'cpapi_initial'] : ['cpapi_initial'], { first_ad_request_ms: firstAdD ?? null, banner_visible_ms: bannerD.t ?? null });
  } else if (!bannerShown && preSenders.length && ok.default.ok) {
    add('no_banner_sends', 'info', 'No banner was shown to this visitor; ad pixels ran', `No cookie banner appeared for this visit (region ${region || 'unknown'}), and ${vn(preSenders)} sent data. Shopify's setting for this region ${regionAllows ? 'allows tracking until the visitor opts out' : 'requires consent, yet pixels sent data'}. If you intend to ask visitors in this region before tracking, show a banner here and make Shopify require consent.`, regionAllows ? ['region_default'] : ['cpapi_initial']);
  }
  if (firstNoT != null && firstSbxD != null && firstSbxD < firstNoT) add('race', 'medium', 'Pixels started before your consent app said "no"', `Your consent app told Shopify "no" automatically, but only ${fmtS(firstNoT)} after the page started; a sandboxed ad pixel had already sent data at ${fmtS(firstSbxD)}. Shopify never stops a pixel that has already started.`, ['region_default', 'cpapi_initial'], { first_sandboxed_ms: firstSbxD, first_no_ms: firstNoT });
  if (firstYesT != null) add('auto_yes', 'high', 'Your consent app told Shopify "yes" without any click', `In the visit with no interaction, the consent state became "marketing: yes" at ${fmtS(firstYesT)} although nobody clicked anything. Check your consent app for implied consent, consent-on-scroll or special rules for automated browsers. (This test browser is visibly automated; some consent apps treat such browsers differently, so confirm in a normal browser.)`, ['auto_yes']);
  if (declineRecord.status === 'no_decline_button') add('no_decline', 'medium', 'No Decline/Reject button on the first layer of the banner', `ConsentCheck found a banner but no control labelled Decline, Reject or similar (buttons seen: ${(declineRecord.buttons || []).slice(0, 6).join(' | ') || 'none'}), so it did not click anything. Visitors who want to refuse must dig into settings.`, ['decline_button']);
  if (declineRecord.status === 'not_recorded_still_allowed') add('decline_not_written', 'high', 'Your consent app does not pass the Decline to Shopify', `After the click on "${declineRecord.clicked_text || 'Decline'}", Shopify's Customer Privacy API still reported marketing as allowed. Shopify's pixel sandbox takes its orders only from that API, so app and custom pixels ignore this visitor's refusal.`, ['cpapi_integration']);
  if (declineRecord.status === 'recorded_marketing_only') add('decline_partial', 'medium', 'The Decline was passed to Shopify, but "data sale" stayed allowed', 'After the Decline, Shopify recorded marketing: no, but sale or sharing of data remained allowed, so pixels that declare only "data sale" (or that are allowed by it) are not stopped by the click.', ['cpapi_sale']);
  const declNot = vendors.filter((v) => v.decline === 'not_stopped');
  const declPart = vendors.filter((v) => v.decline === 'partly');
  if (declNot.length) add('decline_not_stopped', 'high', `Decline did not stop ${vn(declNot)}`, `On a fresh page after the Decline, ${vn(declNot)} started again and sent data. ${declNot.map((v) => v.why.decline).filter(Boolean).join(' ')}`, fixesFor(declNot, 'decline', declineRecord));
  if (declPart.length) add('decline_leftover', 'medium', `${vn(declPart)} kept sending for a while after the Decline`, `Pixels that had already started before the click kept sending on the same page (or as the page unloaded). They stopped on the next page. Pixels that never start before a choice avoid this.`, ['region_default', 'cpapi_initial']);
  const gpcNot = vendors.filter((v) => v.gpc === 'not_stopped');
  if (ok.gpc.ok && gpcRecorded === false) add('gpc_not_recorded', 'medium', 'Shopify did not record the GPC opt-out', 'With Global Privacy Control switched on, Shopify still reported sale of data as allowed. Shopify honours GPC only in regions set up for opt-out of sale/sharing; check your customer privacy settings.', ['gpc_region']);
  if (gpcNot.length) add('gpc_not_stopped', 'high', `GPC did not stop ${vn(gpcNot)}`, `With the browser's Global Privacy Control signal on, ${vn(gpcNot)} still sent data. ${gpcNot.map((v) => v.why.gpc).filter(Boolean).join(' ')}`, fixesFor(gpcNot, 'gpc'));
  const bop = vendors.filter((v) => v.blocked_on_paper);
  if (bop.length) add('blocked_on_paper', 'high', `Blocked on paper: ${vn(bop)}`, `Your consent app's own configuration lists ${vn(bop)} as blocked until the visitor consents, yet ${bop.length === 1 ? 'its' : 'their'} Shopify pixel sent data from the sandbox before any choice. The app's blocker only reaches scripts in the main page.`, ['no_script_blocking', 'cpapi_initial']);
  const np = pixelRows.filter((p) => p.flags.no_purpose);
  const npSent = np.filter((p) => p.sent_ad_data);
  if (np.length) add('no_purpose', npSent.length ? 'high' : 'low', `${np.length} installed ${np.length === 1 ? 'pixel declares' : 'pixels declare'} no consent purpose`, `${np.map((p) => pixName(p)).join(', ')} ${np.length === 1 ? 'declares' : 'declare'} no privacy purpose to Shopify, so Shopify starts ${np.length === 1 ? 'it' : 'them'} regardless of what the visitor chooses${npSent.length ? `; ${npSent.map((p) => pixName(p)).join(', ')} sent ad data in this test` : ''}.`, np.some((p) => p.type === 'CUSTOM') ? ['custom_purposes'].concat(np.some((p) => p.type === 'APP') ? ['app_purposes'] : []) : ['app_purposes']);
  const mns = pixelRows.filter((p) => p.flags.marketing_without_data_sale && p.sent_ad_data);
  if (mns.length && ok.gpc.ok) add('marketing_not_sale', gpcNot.length ? 'medium' : 'low', `${mns.length} ad ${mns.length === 1 ? 'pixel declares' : 'pixels declare'} marketing but not "data sale"`, `${mns.map((p) => pixName(p)).join(', ')} ${mns.length === 1 ? 'is' : 'are'} not treated as a sale or sharing of data, so GPC and "Do not sell or share" opt-outs do not stop ${mns.length === 1 ? 'it' : 'them'}.`, mns.some((p) => p.type === 'CUSTOM') ? ['custom_data_sale'] : ['app_purposes']);
  const pageVend = vendors.filter((v) => (v.before_choice === 'sends' && v.where_before.includes('page') && bannerShown) || (v.decline === 'not_stopped' && (v.detail.decline.next_page.where || []).includes('page')) || (v.gpc === 'not_stopped' && (v.detail.gpc.where || []).includes('page')));
  if (pageVend.length) add('page_scripts', 'medium', `${vn(pageVend)}: tags in the main page that ignored the choice`, 'These requests came from scripts in the main page (your theme, a tag manager or an app embed), outside Shopify\'s pixel system. Only your consent app can block them there, or you can move them into a Shopify pixel with purposes set.', ['page_tags']);
  if (preSbx.length && !bop.length && cmp && ['pandectes', 'onetrust', 'cookiebot', 'usercentrics', 'cookieyes', 'consentmanager', 'transcend'].includes(cmp)) fixes.add('no_script_blocking');
  const urlLeak = vendors.filter((v) => [v.detail.default, v.detail.gpc, v.detail.decline.next_page].some((x) => x.page_url));
  if (urlLeak.length) add('page_url', 'info', 'Vendors received the full page address', `${vn(urlLeak)} received the page address including its query string (ConsentCheck's test tag was found in their requests). Shopify passes the full URL to pixels; campaign codes and any personal data in URLs travel with it.`, []);
  if (!F.filter((f) => f.severity !== 'info').length && ok.default.ok) add('clean', 'info', 'No problems found in this test', 'No ad vendor sent data in a way that contradicts the visitor\'s choice in this run. Re-test after changing apps or settings, and from the regions you care about.', []);
  F.sort((a, b) => SEV[b.severity] - SEV[a.severity]);

  return {
    tool: { name: 'ConsentCheck', version: meta.version, crawl_lib: meta.crawl_lib_rel, playwright: meta.playwright_version },
    generated_at: new Date().toISOString(),
    target: { url: meta.url, loaded_url: meta.loaded_url, host: meta.host, shop: (D && D.probe && D.probe.shop) || null, title: (D && D.probe && D.probe.title) || null },
    run: { started_at: meta.started_at, ended_at: meta.ended_at, robots: meta.robots, navigations: meta.navigations, browser: (D && D.browser_version) || null, user_agent: (D && D.probe && D.probe.ua) || null, webdriver: D && D.probe ? D.probe.webdriver : null, headed: meta.headed },
    visits: Object.fromEntries(Object.entries(ok).map(([k, v]) => [k, Object.assign({ usable: v.ok, why_not: v.why || null }, A[k] ? { http_status: A[k].goto_status, requests: A[k].n_requests || 0, ad_requests: adReqs.filter((q) => q.arm === k).length, errors: (A[k].errors || []).slice(0, 5) } : {})])),
    store: {
      region, shopify_default: hdrDefault ? { header: hdrDefault.raw, marketing_allowed_before_choice: hdrDefault.allow_marketing, sale_allowed_before_choice: hdrDefault.allow_sale, banner_required_by_shopify: hdrDefault.banner_required } : null,
      banner: { shown: bannerShown, default_visit: bannerD, decline_visit: bannerR }, consent_app: cmp, consent_app_name: cmpName, consent_apps_detected: cmps,
      automatic_before_choice: { first_yes_ms: firstYesT ?? null, first_no_ms: firstNoT ?? null, first_sandboxed_ad_ms: firstSbxD ?? null, first_ad_ms: firstAdD ?? null },
      decline: Object.assign({ clicked, click_ms: tClick, next_page_ms: tNext }, declineRecord), allowed_after_decline: allowedAfterDecline,
      gpc: { shopify_recorded_opt_out: gpcRecorded, header: hdrGpc ? hdrGpc.raw : null, signal_visible: gpcVisible },
      pixel_config_found: !!cfgSrc,
    },
    vendors, pixels: pixelRows, findings: F,
    fixes: [...fixes].filter((k) => FIXES[k]).sort((a, b) => FIX_ORDER.indexOf(a) - FIX_ORDER.indexOf(b)).map((k) => Object.assign({ id: k }, FIXES[k])),
    screenshots: R && R.shots && Object.keys(R.shots).length ? R.shots : null,
    limitations: LIMITATIONS,
  };
}

const SEV = { high: 3, medium: 2, low: 1, info: 0 };
const VNAME = {};
const FIX_ORDER = ['cpapi_integration', 'region_default', 'cpapi_initial', 'custom_purposes', 'custom_data_sale', 'app_purposes', 'page_tags', 'no_script_blocking', 'cpapi_sale', 'gpc_region', 'decline_button', 'auto_yes'];
function rank(v) { return (v.decline === 'not_stopped') * 4 + (v.gpc === 'not_stopped') * 2 + (v.before_choice === 'sends') * 1; }
function fmtS(ms) { return ms == null ? '?' : (ms / 1000).toFixed(1) + ' s'; }
function pixName(p) { return `"${p.name || p.app || 'pixel ' + p.id}" (${p.type === 'CUSTOM' ? 'custom pixel' : 'app pixel'})`; }
function pixelLabel(p, id) {
  if (!p) return { id, label: `pixel ${id}`, purposes: null };
  const app = p.vendor && VNAME[p.vendor] ? VNAME[p.vendor] : null;
  return { id, type: p.type, runtime: p.rc, name: p.name || null, label: p.name ? `${p.name} (${p.type === 'CUSTOM' ? 'custom' : 'app'})` : (app ? `${app} app pixel` : `${p.type === 'CUSTOM' ? 'custom' : 'app'} pixel ${id}`), purposes: (p.pp || []).map((x) => PURPOSE_LABEL[x] || x) };
}
function explainVendor({ d, r, g, decl, gpc, pixById, allowedAfterDecline }) {
  const why = {};
  const reason = (sum, mode) => {
    const parts = [];
    for (const id of sum.pixels || []) {
      const p = pixById[id]; if (!p) continue;
      const nm = `"${p.name || (p.type === 'CUSTOM' ? 'custom pixel ' + id : 'app pixel ' + id)}"`;
      const pp = p.pp || [];
      if (!pp.length) parts.push(`${nm} declares no purpose, so no choice can stop it.`);
      else if (mode === 'gpc' && !pp.includes('SALE_OF_DATA')) parts.push(`${nm} declares ${pp.map((x) => PURPOSE_LABEL[x]).join(' + ')} but not data sale, and Shopify applies GPC only to pixels that declare data sale.`);
      else if (mode === 'decline' && allowedAfterDecline && pp.every((x) => allowedAfterDecline[x] !== false)) parts.push(`${nm} declares ${pp.map((x) => PURPOSE_LABEL[x]).join(' + ')}, which Shopify still allowed after the Decline.`);
      else if (mode === 'decline') parts.push(`${nm} declares ${pp.map((x) => PURPOSE_LABEL[x]).join(' + ')}, which the Decline refused, yet it sent data on the fresh page. It may have started before the refusal reached Shopify on that page; if this repeats in later runs, report it to Shopify.`);
    }
    if ((sum.where || []).includes('page')) parts.push('Some requests came from a script in the main page, which Shopify\'s consent state does not control.');
    return parts.join(' ');
  };
  if (decl === 'not_stopped') why.decline = reason(r.next_page, 'decline');
  if (gpc === 'not_stopped') why.gpc = reason(g, 'gpc');
  return why;
}
function fixesFor(list, mode, declineRecord) {
  const s = new Set();
  const written = declineRecord && /^recorded/.test(declineRecord.status || '');
  for (const v of list) {
    const sum = mode === 'gpc' ? v.detail.gpc : v.detail.decline.next_page;
    for (const p of v.pixels.filter((x) => (sum.pixels || []).includes(x.id))) {
      if (!p.purposes || !p.purposes.length) s.add(p.type === 'CUSTOM' ? 'custom_purposes' : 'app_purposes');
      else if (mode === 'gpc' && !p.purposes.includes('data sale')) s.add(p.type === 'CUSTOM' ? 'custom_data_sale' : 'app_purposes');
      else if (mode === 'decline' && !written) s.add('cpapi_integration');
    }
    if ((sum.where || []).includes('page')) s.add('page_tags');
  }
  return [...s];
}

const CMP_NAMES = { shopify_native: "Shopify's own cookie banner", pandectes: 'Pandectes', consentmo: 'Consentmo', cookiebot: 'Cookiebot (Usercentrics)', onetrust: 'OneTrust', osano: 'Osano', usercentrics: 'Usercentrics', trustarc: 'TrustArc', didomi: 'Didomi', termly: 'Termly', cookieyes: 'CookieYes', enzuzo: 'Enzuzo', iubenda: 'iubenda', axeptio: 'Axeptio', transcend: 'Transcend', ketch: 'Ketch', clarip: 'Clarip', consentmanager: 'consentmanager', cookiefirst: 'CookieFirst', cookiehub: 'CookieHub', cookiescript: 'CookieScript', fides_ethyca: 'Fides (Ethyca)', consentik: 'Consentik', securiti: 'Securiti', multiple: 'several consent tools', generic: 'an unrecognised banner' };

const DOC = {
  cpapi: 'https://shopify.dev/docs/api/customer-privacy',
  privacy: 'https://help.shopify.com/en/manual/privacy-and-security/privacy/customer-privacy-settings/privacy-settings',
  apppixels: 'https://help.shopify.com/en/manual/promoting-marketing/pixels/app-pixels',
  custom: 'https://help.shopify.com/en/manual/promoting-marketing/pixels/custom-pixels/manage',
  customcode: 'https://help.shopify.com/en/manual/promoting-marketing/pixels/custom-pixels/code',
  pixelprivacy: 'https://shopify.dev/docs/api/web-pixels-api/pixel-privacy',
  about: 'https://shopify.dev/docs/apps/build/marketing-analytics/pixels',
  gpc: 'https://globalprivacycontrol.org/',
};
const FIXES = {
  cpapi_integration: { title: "Connect your consent app to Shopify's Customer Privacy API", steps: [
    "Open your consent app's settings and turn on its Shopify integration (often called \"Shopify Customer Privacy API\", \"Shopify consent sync\" or similar).",
    "If you pasted the banner's script into your theme instead of installing the vendor's Shopify app, install the official Shopify app so that it can report choices to Shopify.",
    "Re-run ConsentCheck: under \"Is the Decline passed to Shopify?\" you should see \"yes\"."], links: [DOC.cpapi, DOC.apppixels] },
  cpapi_initial: { title: 'Have your consent app report the initial state before pixels start', steps: [
    'Ask your consent app vendor whether it reports "no" (or "not yet") to Shopify as soon as the page starts, for visitors who have not chosen.',
    "Where it cannot, rely on Shopify's own region setting (next fix) so that pixels wait by default."], links: [DOC.cpapi] },
  region_default: { title: "Make Shopify's default match your banner", steps: [
    "In Shopify admin, go to Settings > Customer privacy and review the cookie banner / consent settings for the regions where your banner asks visitors to choose.",
    'If visitors there should be asked before tracking, set those regions so that tracking requires consent; Shopify then holds marketing pixels until the visitor accepts.',
    "Keep only one banner: if you use a third-party consent app, Shopify recommends disabling its own banner."], links: [DOC.privacy] },
  custom_purposes: { title: 'Set a privacy purpose on every custom pixel', steps: [
    'In Shopify admin, go to Settings > Customer events and open the Custom pixels tab.',
    'Open each pixel listed above as declaring no purpose, find Customer privacy > Permission, choose "Required" and tick the purposes the pixel serves (Marketing for ad pixels; Analytics for measurement).',
    'Under Customer privacy > Data sale, keep "qualifies as data sale" for advertising pixels (this is the default for new custom pixels), then save.'], links: [DOC.custom, DOC.customcode] },
  custom_data_sale: { title: 'Mark ad custom pixels as "data sale"', steps: [
    'In Settings > Customer events > Custom pixels, open each advertising pixel listed above.',
    'Under Customer privacy > Data sale, choose the option saying the data collected qualifies as data sale, then save. Shopify then stops the pixel for visitors who opted out, including by GPC.'], links: [DOC.customcode] },
  app_purposes: { title: 'Ask app developers about purposes (you cannot edit them yourself)', steps: [
    "An app pixel's privacy purposes are set by the app developer. Contact the developer of each app pixel listed above and ask it to declare marketing and data sale for advertising data.",
    "Check whether the app has its own consent settings (for example consent mode or limited data use), and turn them on.",
    'If an advertising app cannot declare its purposes, consider replacing it with a custom pixel whose purposes you control, or removing it.'], links: [DOC.apppixels, DOC.pixelprivacy] },
  no_script_blocking: { title: "Don't rely on script blocking for app and custom pixels", steps: [
    "Your consent app's auto-blocking or blocklist only reaches scripts in the main page. App and custom pixels run in Shopify's sandbox (a web worker or hidden iframe) and are controlled only by Shopify's consent state.",
    'Keep the blocklist for theme scripts, but make sure the Shopify integration and pixel purposes (above) are right, because that is what controls the sandbox.'], links: [DOC.about] },
  page_tags: { title: 'Bring main-page tags under your banner', steps: [
    'Find where the tag is added: theme code (Online Store > Themes > Edit code), a tag manager container, or an app embed (Themes > Customize > App embeds).',
    'Either make your consent app block it until consent (categorise it as marketing), or remove it and add the vendor through a Shopify app or custom pixel with purposes set.'], links: [DOC.about] },
  cpapi_sale: { title: "Make the Decline cover \"sale or sharing\" too", steps: [
    'In your consent app, check how its Decline maps to Shopify\'s purposes; a US-style refusal of advertising should set marketing and sale of data to "no".',
    'Ask the vendor if the mapping cannot be changed in the settings.'], links: [DOC.cpapi] },
  gpc_region: { title: 'Let Shopify honour GPC for these visitors', steps: [
    'In Settings > Customer privacy, check that the regions where you offer "Do not sell or share" are configured for it; Shopify honours GPC in regions set up for opt-out of sale.'], links: [DOC.privacy, DOC.gpc] },
  decline_button: { title: 'Offer a Decline/Reject button on the first layer', steps: [
    'In your consent app\'s banner settings, add a "Reject all" or "Decline" button next to "Accept".'], links: [] },
  auto_yes: { title: 'Check for automatic consent', steps: [
    'Look for implied consent, consent-on-scroll or "consent for bots/crawlers" options in your consent app and switch them off if you do not intend them.',
    'Confirm in an ordinary browser (a new private window) that no "yes" is recorded before a visitor clicks Accept.'], links: [] },
};
const LIMITATIONS = [
  'One visit per condition from one location. Results depend on where the test runs: Shopify and consent apps behave differently by region. Run it from the regions you care about.',
  'The test browser is automated and says so (headless Chrome user agent, automation flag on). Some consent apps and pixels behave differently for automated browsers; confirm important results in a normal browser.',
  'Only one page is loaded; other pages, checkout and logged-in states can differ. Nothing is added to the cart and no form is submitted.',
  'Vendor recognition uses the study\'s list of about 70 advertising and analytics endpoints; unknown vendors are not counted.',
  'Requests are attributed to the sandbox or the main page from browser debugging data; a small share can be misattributed.',
  'This is a technical check, not legal advice. Whether a given behaviour is lawful depends on your jurisdiction, your notices and your contracts.',
];

module.exports = { analyze, decodeCmp, FIXES, WHERE_LABEL, ORIGIN_LABEL, PURPOSE_LABEL, CMP_NAMES };
