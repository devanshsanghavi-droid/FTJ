// Target instrumentation on top of RawCDP (flat mode).
// - Browser-level Target.setAutoAttach{autoAttach, waitForDebuggerOnStart, flatten} attaches pages;
//   on every attached page/iframe/worker session we enable Network (+Page for frames), optionally run
//   an injection BEFORE the target's own scripts, set auto-attach again (so nested iframes/workers
//   are caught), and only then send Runtime.runIfWaitingForDebugger.
// - Network events are stored per session so every request can be attributed to the target (page,
//   OOPIF, dedicated worker, ...) that issued it.
class Instrumenter {
  constructor(cdp, opts = {}) {
    this.cdp = cdp;
    this.inject = opts.inject || null;       // JS source to run in every target before its scripts
    this.t0 = Date.now();
    this.targets = new Map();                 // sessionId -> {type,url,targetId,parent,t_attach,...}
    this.frames = new Map();                  // frameId -> {url, parentId, sid, name}
    this.reqs = new Map();                    // sid|requestId -> record
    this.order = [];                          // insertion order of keys
    this.extra = new Map();                   // sid|requestId -> extraInfo (may arrive first)
    this.injectResults = [];
    this.pendingInject = new Map();          // worker sid -> target rec awaiting its first script
    this.errors = [];
    this.onRequest = opts.onRequest || null;  // callback(rec) on requestWillBeSent
    this.onFinished = opts.onFinished || null;
    this.bodyRules = opts.bodyRules || [];    // [{name, re}] response bodies to fetch via Network.getResponseBody
    this.bodies = {};                         // name -> [{url, text}]
    this.bodyPromises = [];
    cdp.on((m, p, sid) => this._on(m, p, sid));
  }
  async start() {
    await this.cdp.send('Target.setAutoAttach', { autoAttach: true, waitForDebuggerOnStart: true, flatten: true });
  }
  _on(method, p, sid) {
    if (method === 'Target.attachedToTarget') return this._attach(p, sid);
    if (method === 'Target.detachedFromTarget') { const t = this.targets.get(p.sessionId); if (t) t.t_detach = Date.now() - this.t0; return; }
    if (method === 'Target.targetInfoChanged') { for (const t of this.targets.values()) if (t.targetId === p.targetInfo.targetId) { t.url_last = (p.targetInfo.url || '').slice(0, 600); } return; }
    if (method === 'Page.frameNavigated') { const f = p.frame; this.frames.set(f.id, { url: (f.url || '') + (f.urlFragment || ''), parentId: f.parentId || null, sid, name: f.name || null, sandbox: f.sandboxFlags || null, secOrigin: f.securityOrigin || null }); return; }
    if (method === 'Page.frameAttached') { if (!this.frames.has(p.frameId)) this.frames.set(p.frameId, { url: null, parentId: p.parentFrameId || null, sid }); return; }
    if (method.startsWith('Network.')) return this._net(method, p, sid);
    if (method === 'Debugger.paused') return this._paused(p, sid);
  }
  async _paused(p, sid) {
    const c = this.cdp;
    const rec = this.pendingInject.get(sid);
    if (!rec) { c.sendMayFail('Debugger.resume', {}, sid); return; }
    this.pendingInject.delete(sid);
    const ev = await c.sendMayFail('Runtime.evaluate', { expression: this.inject, returnByValue: true }, sid);
    rec.inject = { state: ev && ev.__err ? 'error' : 'ok', reason: p.reason, err: ev && ev.__err ? ev.__err : (ev && ev.exceptionDetails ? String(ev.exceptionDetails.text).slice(0, 100) : null),
      script: p.data && p.data.url ? String(p.data.url).slice(0, 200) : null, t: Date.now() - this.t0 };
    await c.sendMayFail('Debugger.removeInstrumentationBreakpoint', { instrumentation: 'beforeScriptExecution' }, sid);
    await c.sendMayFail('Debugger.resume', {}, sid);
    c.sendMayFail('Debugger.disable', {}, sid);
  }
  async _attach(p, parentSid) {
    const sid = p.sessionId; const ti = p.targetInfo || {};
    const rec = { sid, type: ti.type, url: (ti.url || '').slice(0, 600), targetId: ti.targetId, parent: parentSid, openerFrame: ti.openerFrameId || null,
      parentFrameId: ti.parentFrameId || null, bctx: ti.browserContextId || null, waiting: !!p.waitingForDebugger, t_attach: Date.now() - this.t0 };
    this.targets.set(sid, rec);
    const c = this.cdp;
    const aa = { autoAttach: true, waitForDebuggerOnStart: true, flatten: true };
    try {
      if (ti.type === 'page' || ti.type === 'iframe') {
        const ps = [c.sendMayFail('Network.enable', { maxPostDataSize: 65536 }, sid), c.sendMayFail('Page.enable', {}, sid)];
        if (this.inject) ps.push(c.sendMayFail('Page.addScriptToEvaluateOnNewDocument', { source: this.inject }, sid));
        ps.push(c.sendMayFail('Target.setAutoAttach', aa, sid));
        const r = await Promise.all(ps);
        rec.setup_errs = r.filter((x) => x && x.__err).map((x) => x.__err).slice(0, 3);
        if (this.inject && ti.type === 'iframe' && process.env.CS3_IFRAME_EVAL_NOW) {
          // document of an OOPIF that already exists (rare): also patch the current realm
          const ev = await c.sendMayFail('Runtime.evaluate', { expression: this.inject }, sid);
          rec.inject_now = ev && ev.__err ? ev.__err : 'ok';
        }
      } else if (ti.type === 'worker' || ti.type === 'shared_worker' || ti.type === 'service_worker') {
        // Runtime.evaluate on a worker that is still paused-on-start crashes the renderer (tested),
        // so we set a Debugger instrumentation breakpoint 'beforeScriptExecution', resume, and inject
        // when the worker pauses right before its FIRST script runs; then remove it and resume.
        const doInject = this.inject && !process.env.CS3_NO_WORKER_INJECT;
        const ps = [c.sendMayFail('Network.enable', { maxPostDataSize: 65536 }, sid), c.sendMayFail('Target.setAutoAttach', aa, sid)];
        if (doInject) {
          rec.inject = { state: 'armed' };
          this.pendingInject.set(sid, rec);
          ps.push(c.sendMayFail('Debugger.enable', {}, sid));
          ps.push(c.sendMayFail('Debugger.setInstrumentationBreakpoint', { instrumentation: 'beforeScriptExecution' }, sid));
          setTimeout(() => { if (this.pendingInject.has(sid)) { this.pendingInject.delete(sid); rec.inject.state = 'timeout'; c.sendMayFail('Debugger.disable', {}, sid); } }, 8000);
        }
        const r = await Promise.all(ps);
        rec.setup_errs = r.filter((x) => x && x.__err).map((x) => x.__err).slice(0, 3);
      }
    } catch (e) { this.errors.push('attach:' + String(e).slice(0, 120)); }
    rec.t_resume = Date.now() - this.t0;
    await c.sendMayFail('Runtime.runIfWaitingForDebugger', {}, sid);
  }
  _key(sid, id) { return (sid || '') + '|' + id; }
  _net(method, p, sid) {
    const k = this._key(sid, p.requestId);
    if (method === 'Network.requestWillBeSent') {
      let r = this.reqs.get(k);
      if (r && p.redirectResponse) {
        // redirect: close the previous hop as its own record
        r.st = p.redirectResponse.status; r.redirected = true;
        const k2 = k + '#' + (r.hop || 0);
        this.reqs.set(k2, r); this.reqs.delete(k); this.order[this.order.indexOf(k)] = k2;
        const nr = this._newReq(p, sid); nr.hop = (r.hop || 0) + 1; nr.redirect_from = r.url.slice(0, 300);
        this.reqs.set(k, nr); this.order.push(k);
        if (this.onRequest) this.onRequest(nr);
        return;
      }
      r = this._newReq(p, sid);
      const ex = this.extra.get(k); if (ex) { Object.assign(r, ex); this.extra.delete(k); }
      this.reqs.set(k, r); this.order.push(k);
      if (this.onRequest) this.onRequest(r);
      return;
    }
    if (method === 'Network.requestWillBeSentExtraInfo') {
      const h = p.headers || {};
      const ex = {};
      const ck = h.cookie || h.Cookie;
      if (ck) ex.ck = ck.split(';').map((s) => s.split('=')[0].trim()).filter(Boolean);
      const g = h['sec-gpc'] || h['Sec-GPC'];
      if (g !== undefined) ex.gpc_hdr = g;
      if (p.associatedCookies) { const bl = p.associatedCookies.filter((c) => c.blockedReasons && c.blockedReasons.length).length; if (bl) ex.ck_blocked = bl; }
      const r = this.reqs.get(k);
      if (r) Object.assign(r, ex); else this.extra.set(k, ex);
      return;
    }
    const r = this.reqs.get(k); if (!r) return;
    if (method === 'Network.responseReceived') {
      const resp = p.response || {};
      r.st = resp.status; r.tr = resp.timing ? undefined : undefined;
      r.mime = (resp.mimeType || '').slice(0, 60);
      if (resp.fromDiskCache) r.cache = 'disk';
      if (resp.fromServiceWorker) r.sw = true;
      r.rtype2 = p.type;
      if (r.is_nav || r.keep_headers) {
        const h = {}; for (const [kk, vv] of Object.entries(resp.headers || {})) h[kk.toLowerCase()] = String(vv).slice(0, 1500);
        r.resp_headers = { 'server-timing': h['server-timing'], 'cf-cache-status': h['cf-cache-status'], age: h.age, 'powered-by': h['powered-by'], 'x-shopid': h['x-shopid'], 'x-cache': h['x-cache'], 'cache-control': h['cache-control'], server: h.server };
      }
      return;
    }
    if (method === 'Network.loadingFailed') { r.fail = p.errorText; if (p.blockedReason) r.blocked = p.blockedReason; if (p.canceled) r.canceled = true; r.t_end = this._rel(p.timestamp); if (this.onFinished) this.onFinished(r); return; }
    if (method === 'Network.loadingFinished') {
      r.t_end = this._rel(p.timestamp); r.bytes = p.encodedDataLength;
      let name = null;
      if (r.is_nav && (!this.mainFrameId || r.frame === this.mainFrameId)) name = 'nav_html';
      else for (const b of this.bodyRules) if (b.re.test(r.url)) { name = b.name; break; }
      if (name) {
        const url = r.url;
        this.bodyPromises.push(this.cdp.sendMayFail('Network.getResponseBody', { requestId: p.requestId }, sid).then((res) => {
          if (!res || res.__err) { (this.bodies[name] = this.bodies[name] || []).push({ url: url.slice(0, 300), err: res ? res.__err : 'none' }); return; }
          const text = res.base64Encoded ? Buffer.from(res.body || '', 'base64').toString('utf8') : (res.body || '');
          (this.bodies[name] = this.bodies[name] || []).push({ url: url.slice(0, 300), text: text.slice(0, 4e6) });
        }));
      }
      if (this.onFinished) this.onFinished(r); return;
    }
  }
  _rel(ts) { if (this.monoBase === undefined) return null; return Math.round((ts - this.monoBase) * 1000 + this.wallBaseRel); }
  _newReq(p, sid) {
    const q = p.request || {};
    // time base: first requestWillBeSent with wallTime establishes monotonic->wall mapping
    if (this.monoBase === undefined && p.wallTime) { this.monoBase = p.timestamp; this.wallBaseRel = Math.round(p.wallTime * 1000 - this.t0); this.wallBase = p.wallTime * 1000; }
    const r = { sid, rid: p.requestId, t: this._rel(p.timestamp), wall: p.wallTime ? Math.round(p.wallTime * 1000) : null, url: q.url || '', m: q.method, type: p.type || null,
      frame: p.frameId || null, loader: p.loaderId || null };
    if (p.type === 'Document' && p.requestId === p.loaderId) r.is_nav = true;
    const ini = p.initiator || {};
    r.ini_type = ini.type || null;
    if (ini.url) r.ini_url = ini.url.slice(0, 400);
    if (ini.requestId) r.ini_req = ini.requestId;
    const st = ini.stack;
    if (st) {
      const urls = [];
      let s = st; let depth = 0;
      while (s && depth < 4) { for (const cf of (s.callFrames || [])) { if (cf.url && !urls.includes(cf.url)) urls.push(cf.url); if (urls.length >= 6) break; } s = s.parent; depth++; }
      r.ini_stack = urls.map((u) => u.slice(0, 300));
    }
    if (q.hasPostData) {
      r.has_post = true;
      if (q.postDataEntries && q.postDataEntries.length) {
        try { r.post_buf = Buffer.concat(q.postDataEntries.map((e) => Buffer.from(e.bytes || '', 'base64'))); } catch (e) { /* ignore */ }
      } else if (q.postData) { r.post_buf = Buffer.from(q.postData, 'utf8'); }
    }
    if (q.headers) { const g = q.headers['Sec-GPC'] || q.headers['sec-gpc']; if (g !== undefined) r.gpc_hdr_req = g; if (q.headers.Referer) r.ref = q.headers.Referer.slice(0, 600); }
    return r;
  }
  async evalInWorkers(expr, timeoutMs = 3000) {
    const out = [];
    for (const [sid, t] of this.targets) {
      if (!(t.type === 'worker' || t.type === 'shared_worker') || t.t_detach !== undefined) continue;
      const r = await Promise.race([this.cdp.sendMayFail('Runtime.evaluate', { expression: expr, returnByValue: true }, sid), new Promise((res) => setTimeout(() => res({ __err: 'timeout' }), timeoutMs))]);
      out.push({ sid, url: t.url, val: r && r.result ? r.result.value : null, err: r && r.__err ? r.__err : null });
    }
    return out;
  }
  requests() { return this.order.map((k) => this.reqs.get(k)).filter(Boolean); }
}
module.exports = { Instrumenter };
