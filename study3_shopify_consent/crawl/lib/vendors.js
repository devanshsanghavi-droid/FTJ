// Vendor classification (crawl/vendor_endpoints.json), Shopify web-pixel URL patterns,
// payload decoding (canary / landing URL / event name) and request-origin attribution.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const VE = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'vendor_endpoints.json'), 'utf8'));
const py2js = (s) => (s ? s.replace(/\(\?P</g, '(?<') : s);
const VENDORS = VE.vendors.map((v) => ({
  vendor: v.vendor, display: v.display_name, cls: v.vendor_class, ad: !!v.is_advertising, color: v.figure_color_group || null,
  host: new RegExp(py2js(v.host_regex)), path: v.path_regex ? new RegExp(py2js(v.path_regex)) : null,
  beacon: (v.beacon_path_regex || []).map((x) => new RegExp(py2js(x))), lib: (v.library_path_regex || []).map((x) => new RegExp(py2js(x))),
  apiClientIds: (v.shopify_app_pixel && v.shopify_app_pixel.apiClientIds) || [],
}));
const WPU = {};
for (const [k, v] of Object.entries(VE.shopify_web_pixels_urls)) if (k !== 'notes' && typeof v === 'string') WPU[k] = new RegExp(py2js(v));
// also accept the older 'wpm@' prefix and query strings on sandbox iframes
const APICLIENT2VENDOR = {};
for (const v of VENDORS) for (const id of v.apiClientIds) APICLIENT2VENDOR[String(id)] = v.vendor;

function classifyVendor(u) {
  let U; try { U = new URL(u); } catch (e) { return null; }
  const h = U.hostname.toLowerCase(); const p = U.pathname;
  for (const v of VENDORS) {
    if (!v.host.test(h)) continue;
    if (v.path && !v.path.test(p)) continue;
    let kind = 'other';
    if (v.beacon.some((r) => r.test(p))) kind = 'beacon';
    else if (v.lib.some((r) => r.test(p))) kind = 'library';
    return { vendor: v.vendor, ad: v.ad, cls: v.cls, color: v.color, kind };
  }
  return null;
}

function wpmUrl(u) {
  for (const [k, r] of Object.entries(WPU)) {
    const m = r.exec(u);
    if (m) return { wpm: k, pixel_id: (m.groups && m.groups.pixel_id) || null };
  }
  return null;
}

// ---- payload decoding ----
function safeDecode(s) { try { return decodeURIComponent(s.replace(/\+/g, ' ')); } catch (e) { return s; } }
function bodyText(buf) {
  if (!buf || !buf.length) return '';
  let b = buf;
  try {
    if (b[0] === 0x1f && b[1] === 0x8b) b = zlib.gunzipSync(b);
    else if (b[0] === 0x78 && [0x9c, 0x01, 0xda, 0x5e].includes(b[1])) b = zlib.inflateSync(b);
  } catch (e) { b = buf; }
  return b.toString('utf8');
}
function b64Candidates(s) {
  const out = [];
  const re = /[A-Za-z0-9+/_-]{40,}={0,2}/g; let m; let n = 0;
  while ((m = re.exec(s)) && n < 20) { n++; try { const d = Buffer.from(m[0].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8'); if (/[\x20-\x7e]{12,}/.test(d)) out.push(d); } catch (e) { /* ignore */ } }
  return out;
}
// Returns the text variants to search (raw, URL-decoded x2, base64-decoded chunks)
function textVariants(url, body) {
  const v = [url, safeDecode(url), safeDecode(safeDecode(url))];
  if (body) { v.push(body, safeDecode(body), safeDecode(safeDecode(body))); }
  const extra = [];
  for (const s of v) for (const d of b64Candidates(s)) extra.push(d, safeDecode(d));
  return v.concat(extra);
}
function payloadFlags(url, body, landing) {
  // landing = {canary, pathQ (e.g. '/products/<slug>?'), token (creator token value or null)}
  const vars = textVariants(url, body);
  const has = (needle) => !!needle && vars.some((s) => s.includes(needle));
  const lc = (needle) => !!needle && vars.some((s) => s.toLowerCase().includes(needle.toLowerCase()));
  const f = { canary: has(landing.canary) };
  f.full_url = f.canary && has(landing.pathQ);
  f.path = has(landing.path);
  if (landing.token) f.creator_token = lc(landing.token);
  return f;
}
const EV_KEYS = ['ev', 'en', 'event', 'event_name', 'eventName', 'event_type', 'eventType', 'e', 'action', 'evt', 'type'];
function eventNames(url, body) {
  const out = new Set();
  try {
    const U = new URL(url);
    for (const k of EV_KEYS.slice(0, 9)) { const x = U.searchParams.get(k); if (x && x.length < 60) out.add(x); if (out.size) break; }
  } catch (e) { /* ignore */ }
  if (body && out.size === 0) {
    const t = body.trim();
    if (t.startsWith('{') || t.startsWith('[')) {
      try {
        const j = JSON.parse(t);
        const walk = (o, d) => {
          if (!o || d > 3 || out.size >= 5) return;
          if (Array.isArray(o)) { for (const x of o.slice(0, 20)) walk(x, d + 1); return; }
          if (typeof o === 'object') {
            for (const k of ['event', 'event_name', 'eventName', 'event_type', 'eventType', 'name', 'type', 'ev', 'en']) { if (typeof o[k] === 'string' && o[k].length < 60) { out.add(o[k]); break; } }
            for (const k of ['events', 'data', 'batch', 'payload', 'context']) if (o[k]) walk(o[k], d + 1);
          }
        };
        walk(j, 0);
      } catch (e) { /* not json */ }
    } else if (/^[\w%.-]+=/.test(t)) {
      try { const P = new URLSearchParams(t); for (const k of EV_KEYS) { const x = P.get(k); if (x && x.length < 60) { out.add(x); break; } } } catch (e) { /* ignore */ }
    }
  }
  return [...out].slice(0, 5);
}

module.exports = { VENDORS, WPU, APICLIENT2VENDOR, classifyVendor, wpmUrl, bodyText, payloadFlags, eventNames, safeDecode };
