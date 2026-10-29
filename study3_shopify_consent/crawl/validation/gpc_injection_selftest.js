// Self-test of the emulated-GPC injection on a local page (no network access to third parties).
// The FIRST statement of every worker / frame script reads navigator.globalPrivacyControl and
// reports it, so a value of true proves the injection ran before any of that target's own code.
// Targets covered: main frame, same-site sandboxed iframe (opaque origin, like Shopify LAX pixels),
// cross-site OOPIF, dedicated worker created with {credentials:'omit'} (like Shopify STRICT pixels),
// nested worker, blob-URL worker created inside the sandboxed iframe.
// Also checks the Sec-GPC header on worker fetch() and importScripts requests.
// Usage: node gpc_injection_selftest.js [N] [--brave]
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require(path.join(__dirname, '../../../pilot/pixel_payloads/node_modules/playwright'));
const { RawCDP, wsUrlFromUserDataDir, sleep } = require('../lib/rawcdp');
const { Instrumenter } = require('../lib/instrument');
const { GPC_INJECT, GPC_VERIFY } = require('../lib/inject');

const N = parseInt(process.argv[2] || '20', 10);
const BRAVE = process.argv.includes('--brave');
const NOINJ = process.argv.includes('--noinject');
const hdrLog = [];
const PAGE = (port) => `<!doctype html><html><head><script>
window.__res=[];window.addEventListener('message',function(e){window.__res.push(e.data)});
window.__res.push({where:'main',gpc:navigator.globalPrivacyControl});
var w=new Worker('/w.js',{credentials:'omit'});w.onmessage=function(e){window.__res.push(e.data)};
</script></head><body>
<iframe sandbox="allow-scripts allow-forms" src="/sbx.html"></iframe>
<iframe src="http://localhost:${port}/oopif.html"></iframe>
</body></html>`;
const W = `postMessage({where:'worker',gpc:navigator.globalPrivacyControl});
importScripts('/lib.js');
fetch('/beacon?from=worker',{method:'POST',body:'x'});
var w2=new Worker('/w2.js');w2.onmessage=function(e){postMessage(e.data)};`;
const W2 = `postMessage({where:'nested_worker',gpc:navigator.globalPrivacyControl});fetch('/beacon?from=nested');`;
const LIB = `self.__lib_loaded=1;`;
const SBX = `<!doctype html><script>parent.postMessage({where:'sandbox_iframe',gpc:navigator.globalPrivacyControl},'*');
var b=new Blob(["postMessage({where:'blob_worker_in_sandbox',gpc:navigator.globalPrivacyControl})"],{type:'text/javascript'});
var bw=new Worker(URL.createObjectURL(b));bw.onmessage=function(e){parent.postMessage(e.data,'*')};</script>`;
const OOPIF = `<!doctype html><script>parent.postMessage({where:'oopif',gpc:navigator.globalPrivacyControl},'*');</script>`;

const server = http.createServer((req, res) => {
  const u = req.url;
  if (u.startsWith('/beacon') || u.startsWith('/lib.js') || u.startsWith('/w')) hdrLog.push({ url: u, gpc: req.headers['sec-gpc'] || null });
  const port = server.address().port;
  const send = (ct, body) => { res.writeHead(200, { 'content-type': ct }); res.end(body); };
  if (u === '/' || u.startsWith('/?')) return send('text/html', PAGE(port));
  if (u.startsWith('/w.js')) return send('text/javascript', W);
  if (u.startsWith('/w2.js')) return send('text/javascript', W2);
  if (u.startsWith('/lib.js')) return send('text/javascript', LIB);
  if (u.startsWith('/sbx.html')) return send('text/html', SBX);
  if (u.startsWith('/oopif.html')) return send('text/html', OOPIF);
  if (u.startsWith('/beacon')) return send('text/plain', 'ok');
  res.writeHead(404); res.end();
});

(async () => {
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const summary = {};
  const workerChecks = [];
  for (let i = 0; i < N; i++) {
    const dir = fs.mkdtempSync(path.join(process.env.CS3_TMP || os.tmpdir(), 'cs3selftest-'));
    const opts = { headless: true, args: ['--remote-debugging-port=0'], extraHTTPHeaders: { 'Sec-GPC': '1' } };
    if (BRAVE) { opts.executablePath = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'; delete opts.extraHTTPHeaders; }
    const ctx = await chromium.launchPersistentContext(dir, opts);
    if (!BRAVE && !NOINJ && !process.argv.includes('--nopw')) await ctx.addInitScript({ content: GPC_INJECT });
    const cdp = new RawCDP(await wsUrlFromUserDataDir(dir));
    await cdp.connect();
    const ins = new Instrumenter(cdp, { inject: (BRAVE || NOINJ) ? null : GPC_INJECT });
    await ins.start();
    const page = ctx.pages()[0] || await ctx.newPage();
    await page.goto(`http://127.0.0.1:${port}/?i=${i}`, { waitUntil: 'load' });
    await sleep(1500);
    const res = await page.evaluate(() => window.__res);
    for (const r of res) { const k = r.where; summary[k] = summary[k] || { n: 0, gpc_true: 0 }; summary[k].n++; if (r.gpc === true) summary[k].gpc_true++; }
    const wc = await ins.evalInWorkers(GPC_VERIFY);
    for (const w of wc) workerChecks.push({ i, url: w.url, ...(w.val || {}), err: w.err });
    // request attribution check: which session saw the worker's beacon?
    const rq = ins.requests().filter((r) => /beacon|lib\.js|w2?\.js/.test(r.url)).map((r) => ({ url: r.url.replace(/^https?:\/\/[^/]+/, ''), sess: (ins.targets.get(r.sid) || {}).type || 'root', gpc: r.gpc_hdr, t: r.t }));
    if (i === 0) { console.log('targets:', JSON.stringify([...ins.targets.values()].map((t) => ({ type: t.type, url: t.url.slice(0, 80), waiting: t.waiting, inject: t.inject })))); console.log('requests:', JSON.stringify(rq)); }
    cdp.close();
    await ctx.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
  server.close();
  const hdr = {};
  for (const h of hdrLog) { const k = h.url.split('?')[0] + (h.url.includes('from=') ? '?' + h.url.split('?')[1] : ''); hdr[k] = hdr[k] || { n: 0, gpc1: 0 }; hdr[k].n++; if (h.gpc === '1') hdr[k].gpc1++; }
  const inj_first = workerChecks.filter((w) => w.inj && w.n1 - 1 > w.inj.n0).length;
  console.log(JSON.stringify({ browser: BRAVE ? 'brave' : 'chromium', inject: !(BRAVE || NOINJ), runs: N, first_statement_gpc: summary, sec_gpc_header: hdr, worker_checks: workerChecks.length, worker_gpc_true: workerChecks.filter((w) => w.gpc === true).length, worker_marker_present: workerChecks.filter((w) => w.inj).length, worker_globals_added_after_injection: inj_first }, null, 1));
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
