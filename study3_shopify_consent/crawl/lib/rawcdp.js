// Minimal flat-mode Chrome DevTools Protocol client over the browser's own debugging WebSocket.
// Used next to Playwright (which keeps its own pipe connection) so that we can
//   (1) auto-attach to EVERY target (page, OOPIF iframe, dedicated/shared worker) with
//       waitForDebuggerOnStart + flatten, run an injection before the target's own scripts start,
//       then Runtime.runIfWaitingForDebugger, and
//   (2) record Network events per target session, which tells us whether a request came from a
//       Shopify web-pixel worker, a sandboxed iframe or the main thread.
const fs = require('fs');
const path = require('path');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

class RawCDP {
  constructor(wsUrl) { this.wsUrl = wsUrl; this.id = 0; this.cb = new Map(); this.handlers = []; this.closed = false; }
  connect(timeoutMs = 8000) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(this.wsUrl);
      this.ws = ws;
      const to = setTimeout(() => reject(new Error('cdp connect timeout')), timeoutMs);
      ws.onopen = () => { clearTimeout(to); resolve(); };
      ws.onerror = (e) => { clearTimeout(to); if (!this.opened) reject(new Error('cdp ws error')); };
      ws.onclose = () => { this.closed = true; for (const [, c] of this.cb) c.reject(new Error('cdp closed')); this.cb.clear(); };
      ws.onmessage = (ev) => {
        let m; try { m = JSON.parse(typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString('utf8')); } catch (e) { return; }
        if (m.id !== undefined && this.cb.has(m.id)) {
          const c = this.cb.get(m.id); this.cb.delete(m.id);
          if (m.error) c.reject(new Error(m.error.message || 'cdp error')); else c.resolve(m.result);
        } else if (m.method) {
          for (const h of this.handlers) { try { h(m.method, m.params || {}, m.sessionId || null); } catch (e) { /* ignore */ } }
        }
      };
    });
  }
  on(h) { this.handlers.push(h); }
  send(method, params = {}, sessionId = null) {
    if (this.closed) return Promise.reject(new Error('cdp closed'));
    const id = ++this.id;
    const msg = { id, method, params };
    if (sessionId) msg.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.cb.set(id, { resolve, reject });
      try { this.ws.send(JSON.stringify(msg)); } catch (e) { this.cb.delete(id); reject(e); }
    });
  }
  sendMayFail(method, params = {}, sessionId = null) { return this.send(method, params, sessionId).catch((e) => ({ __err: String(e.message || e) })); }
  close() { try { this.ws.close(); } catch (e) { /* ignore */ } }
}

// Read <userDataDir>/DevToolsActivePort written by Chromium when started with --remote-debugging-port=0.
async function wsUrlFromUserDataDir(dir, timeoutMs = 8000) {
  const f = path.join(dir, 'DevToolsActivePort');
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try {
      const [port, p] = fs.readFileSync(f, 'utf8').split('\n');
      if (port && p) return `ws://127.0.0.1:${port.trim()}${p.trim()}`;
    } catch (e) { /* not yet */ }
    await sleep(50);
  }
  throw new Error('DevToolsActivePort not found');
}

module.exports = { RawCDP, wsUrlFromUserDataDir, sleep };
