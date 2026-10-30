#!/usr/bin/env node
// Make a shareable sample from a ConsentCheck JSON result: replaces the store's host, domain, brand word, Shopify
// handle, page path and title, masks store-specific ids (pixel ids, consent ids, long digit runs in URLs), and
// drops the screenshots. Then re-render the HTML with `node consentcheck.js --render OUT.json --out OUT.html`.
//   node tools/anonymize.js in.json out.json [--label "Store A"] [--extra word1,word2]
// Check the output by eye before sharing: a store can also be recognisable from its product names or app mix.
const fs = require('fs');
const args = process.argv.slice(2);
const val = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const [inp, out] = args.filter((a, i) => !a.startsWith('--') && !['--label', '--extra'].includes(args[i - 1]));
if (!inp || !out) { console.error('usage: node tools/anonymize.js in.json out.json [--label "Store A"] [--extra w1,w2]'); process.exit(1); }
const label = val('--label', 'Store A');
const slug = label.toLowerCase().replace(/[^a-z0-9]+/g, '-');
const res = JSON.parse(fs.readFileSync(inp, 'utf8'));

const host = (res.target && res.target.host) || new URL(res.target.url).hostname;
const bare = host.replace(/^www\./, '');
const parts = bare.split('.');
const reg = /\.(co|com|net|org)\.[a-z]{2}$/.test(bare) ? parts.slice(-3).join('.') : parts.slice(-2).join('.');
const brand = reg.split('.')[0];
const shop = (res.target && res.target.shop) || null;
const handle = shop ? shop.replace(/\.myshopify\.com$/, '') : null;
let pagePath = null; try { pagePath = new URL(res.target.loaded_url || res.target.url).pathname; } catch (e) { /* ignore */ }
const extra = (val('--extra', '') || '').split(',').map((x) => x.trim()).filter(Boolean);

const reps = [];
const add = (from, to) => { if (from && from.length >= 3) reps.push([new RegExp(from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), to]); };
if (shop) add(shop, `${slug}.myshopify.com`);
add(host, `www.${slug}.example`);
add(reg, `${slug}.example`);
if (pagePath && pagePath.length > 1) add(pagePath, '/products/<slug>');
if (handle) add(handle, slug);
for (const w of extra) add(w, slug);
add(brand, slug.replace(/-/g, ''));

// store-specific identifiers
const pixMap = new Map(); let pn = 0;
const pixId = (id) => { if (!/^\d{5,}$/.test(id)) return id; if (!pixMap.has(id)) pixMap.set(id, 'px' + String(++pn).padStart(2, '0')); return pixMap.get(id); };
for (const p of res.pixels || []) p.id = pixId(p.id);
for (const v of res.vendors || []) {
  for (const p of v.pixels || []) { p.id = pixId(p.id); p.label = p.label.replace(/\d{5,}/g, (m) => pixId(m)); }
  for (const d of [v.detail.default, v.detail.gpc, ...Object.values(v.detail.decline)]) if (d && d.pixels) d.pixels = d.pixels.map(pixId);
}
function scrub(s) {
  let x = s;
  for (const [re, to] of reps) x = x.replace(re, to);
  x = x.replace(/(_cmp;desc="|\b3[a-zA-Z]*\.[A-Za-z]*_[A-Z]{2,4}_[tf]_[tf])_[^\s"),]+/g, '$1_…');   // consent id after the 4th field
  x = x.replace(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi, '…uuid…');
  x = x.replace(/(?<!\d)(?<!API client )\d{5,}(?!\d)/g, (m) => (pixMap.has(m) ? pixMap.get(m) : m.length >= 7 ? '…' : m));
  return x;
}
function walk(o) {
  if (Array.isArray(o)) return o.map(walk);
  if (o && typeof o === 'object') { const r = {}; for (const [k, v] of Object.entries(o)) r[k] = walk(v); return r; }
  return typeof o === 'string' ? scrub(o) : o;
}
const keepUA = res.run && res.run.user_agent;
let anon = walk(res);
anon.screenshots = null;
anon.target.title = null;
for (const k of ['default_visit', 'decline_visit']) if (anon.store && anon.store.banner && anon.store.banner[k]) anon.store.banner[k].text = null;   // banner wording can identify a store
anon.target.shop = shop ? `${slug}.myshopify.com` : null;
if (anon.run) { anon.run.user_agent = keepUA; }
anon.anonymized = { label, note: 'Store-identifying names, addresses, ids and screenshots replaced or removed by tools/anonymize.js.' };
fs.writeFileSync(out, JSON.stringify(anon, null, 1));
// leak check
const txt = JSON.stringify(anon).toLowerCase();
const leaks = [host, reg, brand, handle, pagePath && pagePath.length > 1 ? pagePath : null, ...extra].filter(Boolean).filter((t) => t.length >= 3 && txt.includes(t.toLowerCase()));
console.log(`anonymized -> ${out}; tokens replaced: ${reps.length}; pixel ids masked: ${pixMap.size}; leak check: ${leaks.length ? 'FOUND ' + leaks.join(', ') : 'clean'}`);
process.exit(leaks.length ? 5 : 0);
