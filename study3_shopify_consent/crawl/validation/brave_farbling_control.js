// Positive control for "Shields off via fresh-profile Preferences": Brave Shields (standard
// fingerprinting protection) farbles navigator.hardwareConcurrency and canvas readback; with Shields
// off, the true values are returned. Local page only (127.0.0.1), no third-party traffic.
const http = require('http'); const fs = require('fs'); const path = require('path');
const { chromium } = require(path.join(__dirname, '../../../pilot/pixel_payloads/node_modules/playwright'));
const BRAVE = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser';
const PAGE = `<!doctype html><canvas id=c width=60 height=20></canvas><script>
var c=document.getElementById('c').getContext('2d');c.fillStyle='#f60';c.fillRect(0,0,60,20);c.fillStyle='#069';c.font='14px Arial';c.fillText('cs3 test',2,15);
window.__fp={hc:navigator.hardwareConcurrency,canvas:document.getElementById('c').toDataURL().slice(-40),gpc:navigator.globalPrivacyControl};</script>`;
const VARIANTS = { default: null, default_value_shields_off: { profile: { default_content_setting_values: { braveShields: 2 } } } };
(async () => {
  const srv = http.createServer((q, s) => { s.writeHead(200, { 'content-type': 'text/html' }); s.end(PAGE); });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const out = {};
  for (const exe of ['chromium', 'brave']) for (const [name, prefs] of Object.entries(VARIANTS)) {
    if (exe === 'chromium' && prefs) continue;
    const res = [];
    for (let i = 0; i < 3; i++) {
      const dir = fs.mkdtempSync(path.join(process.env.CS3_TMP, 'farble-'));
      if (prefs) { fs.mkdirSync(path.join(dir, 'Default'), { recursive: true }); fs.writeFileSync(path.join(dir, 'Default', 'Preferences'), JSON.stringify(prefs)); }
      const ctx = await chromium.launchPersistentContext(dir, { executablePath: exe === 'brave' ? BRAVE : undefined, headless: true });
      const p = ctx.pages()[0];
      await p.goto(`http://127.0.0.1:${srv.address().port}/`);
      res.push(await p.evaluate(() => window.__fp));
      await ctx.close(); fs.rmSync(dir, { recursive: true, force: true });
    }
    out[exe + ':' + name] = res;
  }
  srv.close();
  console.log(JSON.stringify(out, null, 1));
  fs.writeFileSync(path.join(__dirname, 'brave_farbling_control.json'), JSON.stringify({ run_at: new Date().toISOString(), true_hw_concurrency: require('os').cpus().length, out }, null, 1));
})();
