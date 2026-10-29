// Can Brave Shields be turned off for all sites through a FRESH profile's Preferences file?
// Loads one sample store (s0347.store.example product page, S0347) in headless Brave under several
// Preferences variants and counts ad/analytics vendor requests and ERR_BLOCKED_BY_CLIENT failures.
// Also records whether Brave sends Sec-GPC and exposes navigator.globalPrivacyControl in each variant.
// At most one page load per 12 s; fresh temporary profile per load; the user's Brave profile is never touched.
const fs = require('fs');
const path = require('path');
const { chromium } = require(path.join(__dirname, '../../../pilot/pixel_payloads/node_modules/playwright'));
const { RawCDP, wsUrlFromUserDataDir, sleep } = require('../lib/rawcdp');
const { Instrumenter } = require('../lib/instrument');
const { GPC_VERIFY } = require('../lib/inject');
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const URL0 = 'https://s0347.store.example/products/<slug>?utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-shieldtest';
const VEND = /(^|\.)(facebook\.(com|net)|tiktok\.com|tiktokw\.us|pinterest\.com|pinimg\.com|snapchat\.com|sc-static\.net|google-analytics\.com|googletagmanager\.com|doubleclick\.net|googleadservices\.com|bing\.com|clarity\.ms|reddit\.com|redditstatic\.com|klaviyo\.com|criteo\.(com|net)|attn\.tv|attentivemobile\.com)$/;
const ALLOW_ALL = { setting: 1 };
const VARIANTS = {
  default: null,
  exc_shields_off: { profile: { content_settings: { exceptions: { braveShields: { '*,*': { setting: 2 } } } } } },
  default_value_shields_off: { profile: { default_content_setting_values: { braveShields: 2 } } },
  exc_features_allow: { profile: { content_settings: { exceptions: { shieldsAds: { '*,*': ALLOW_ALL }, trackers: { '*,*': ALLOW_ALL }, cosmeticFiltering: { '*,*': ALLOW_ALL }, fingerprintingV2: { '*,*': ALLOW_ALL }, httpUpgradableResources: { '*,*': ALLOW_ALL }, referrers: { '*,*': ALLOW_ALL } } } } },
};
const only = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const PREWAIT = parseInt((process.argv.find((a) => a.startsWith('--prewait=')) || '--prewait=0').split('=')[1], 10);
const EXTRA = process.argv.includes('--nocomp') ? ['--disable-component-update'] : [];
(async () => {
  const out = {};
  for (const [name, prefs] of Object.entries(VARIANTS)) {
    if (only.length && !only.includes(name)) continue;
    const dir = fs.mkdtempSync(path.join(process.env.CS3_TMP, 'brave-shields-'));
    if (prefs) { fs.mkdirSync(path.join(dir, 'Default'), { recursive: true }); fs.writeFileSync(path.join(dir, 'Default', 'Preferences'), JSON.stringify(prefs)); }
    const t0 = Date.now();
    const ctx = await chromium.launchPersistentContext(dir, { executablePath: BRAVE, headless: true, args: ['--remote-debugging-port=0', ...EXTRA], locale: 'en-US', timezoneId: 'America/Los_Angeles', viewport: { width: 1366, height: 900 } });
    const cdp = new RawCDP(await wsUrlFromUserDataDir(dir)); await cdp.connect();
    const ins = new Instrumenter(cdp, {}); await ins.start();
    const page = ctx.pages()[0] || await ctx.newPage();
    if (PREWAIT) await sleep(PREWAIT * 1000);
    let err = null;
    try { await page.goto(URL0, { waitUntil: 'load', timeout: 45000 }); } catch (e) { err = String(e).split('\n')[0]; }
    await sleep(12000);
    const gpcMain = await page.evaluate(() => navigator.globalPrivacyControl).catch(() => 'err');
    const wk = await ins.evalInWorkers(GPC_VERIFY);
    const reqs = ins.requests();
    const v = reqs.filter((r) => { try { return VEND.test(new URL(r.url).hostname); } catch (e) { return false; } });
    const blocked = reqs.filter((r) => /BLOCKED_BY_CLIENT/.test(r.fail || '') || r.blocked);
    const hosts = {}; for (const r of v) { const h = new URL(r.url).hostname; hosts[h] = hosts[h] || { n: 0, ok: 0, blocked: 0 }; hosts[h].n++; if (r.st >= 200 && r.st < 400) hosts[h].ok++; if (/BLOCKED_BY_CLIENT/.test(r.fail || '') || r.blocked) hosts[h].blocked++; }
    const gpcHdr = reqs.filter((r) => r.gpc_hdr === '1' || r.gpc_hdr_req === '1').length;
    cdp.close(); await ctx.close();
    let persisted = null;
    try { const P = JSON.parse(fs.readFileSync(path.join(dir, 'Default', 'Preferences'), 'utf8')); persisted = { exc_braveShields: (((P.profile || {}).content_settings || {}).exceptions || {}).braveShields || null, default_braveShields: ((P.profile || {}).default_content_setting_values || {}).braveShields ?? null, trackers: (((P.profile || {}).content_settings || {}).exceptions || {}).trackers || null }; } catch (e) { persisted = 'unreadable'; }
    fs.rmSync(dir, { recursive: true, force: true });
    out[name] = { prewait_s: PREWAIT, extra_args: EXTRA, goto_err: err, n_requests: reqs.length, n_vendor: v.length, n_blocked_by_client: blocked.length, blocked_hosts: [...new Set(blocked.map((r) => { try { return new URL(r.url).hostname; } catch (e) { return '?'; } }))].slice(0, 15), vendor_hosts: hosts, gpc_main: gpcMain, workers: wk.map((w) => ({ url: (w.url || '').slice(-60), gpc: w.val ? String(w.val.gpc) : null, err: w.err, n1: w.val && w.val.n1 })), requests_with_sec_gpc: gpcHdr, persisted, ms: Date.now() - t0 };
    console.log(name, JSON.stringify(out[name]));
    await sleep(12000);
  }
  fs.appendFileSync(path.join(__dirname, 'brave_shields_test.jsonl'), JSON.stringify({ run_at: new Date().toISOString(), url: URL0, results: out }, null, 1));
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
