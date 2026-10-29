// Detail of requests Brave blocks (ERR_BLOCKED_BY_CLIENT) on one store page, for a Preferences variant.
const fs = require('fs'); const path = require('path');
const { chromium } = require(path.join(__dirname, '../../../pilot/pixel_payloads/node_modules/playwright'));
const { RawCDP, wsUrlFromUserDataDir, sleep } = require('../lib/rawcdp');
const { Instrumenter } = require('../lib/instrument');
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const exe = process.argv[2] === 'chromium' ? undefined : BRAVE;
const prefs = process.argv[3] ? JSON.parse(process.argv[3]) : null;
(async () => {
  const dir = fs.mkdtempSync(path.join(process.env.CS3_TMP, 'brave-detail-'));
  if (prefs) { fs.mkdirSync(path.join(dir, 'Default'), { recursive: true }); fs.writeFileSync(path.join(dir, 'Default', 'Preferences'), JSON.stringify(prefs)); }
  const ctx = await chromium.launchPersistentContext(dir, { executablePath: exe, headless: true, args: ['--remote-debugging-port=0'] });
  const cdp = new RawCDP(await wsUrlFromUserDataDir(dir)); await cdp.connect();
  const ins = new Instrumenter(cdp, {}); await ins.start();
  const page = ctx.pages()[0];
  await page.goto('https://s0347.store.example/products/<slug>?utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-shieldtest', { waitUntil: 'load', timeout: 45000 }).catch((e) => console.log('goto', String(e).slice(0, 100)));
  await sleep(10000);
  const reqs = ins.requests();
  const bl = reqs.filter((r) => r.fail);
  console.log(JSON.stringify({ exe: exe ? 'brave' : 'chromium', n: reqs.length, failed: bl.map((r) => ({ url: r.url.slice(0, 120), fail: r.fail, blocked: r.blocked, type: r.type })) }, null, 1));
  const ck = reqs.filter((r) => r.ck && r.ck.length && !/[S0347]\.com/.test(new URL(r.url).hostname)).length;
  console.log('third-party requests carrying cookies:', ck);
  cdp.close(); await ctx.close(); fs.rmSync(dir, { recursive: true, force: true });
})();
