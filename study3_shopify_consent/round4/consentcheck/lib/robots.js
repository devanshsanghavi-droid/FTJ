// robots.txt (RFC 9309): fetch once per run, then check every path ConsentCheck will load.
// Group choice: a group naming one of our product tokens, else the '*' group. Longest match wins;
// Allow wins a tie; '*' wildcard and '$' end anchor. 4xx = no restrictions (RFC 9309 2.3.1.3);
// 5xx or unreachable = treat as fully disallowed (RFC 9309 2.3.1.4) -> ConsentCheck does not run.
const TOKENS = ['consentcheck', 'headlesschrome'];
const UA = 'ConsentCheck/0.1 (store-owner self-test of cookie-banner/pixel consent; robots.txt check)';

function parse(text) {
  const groups = []; let cur = null; let lastWasRule = false;
  for (let line of String(text || '').split(/\r?\n/)) {
    line = line.split('#', 1)[0].trim();
    const i = line.indexOf(':'); if (i < 0) continue;
    const k = line.slice(0, i).trim().toLowerCase(); const v = line.slice(i + 1).trim();
    if (k === 'user-agent') {
      if (!cur || lastWasRule) { cur = { agents: [], rules: [] }; groups.push(cur); }
      cur.agents.push(v.toLowerCase()); lastWasRule = false;
    } else if ((k === 'allow' || k === 'disallow') && cur) { cur.rules.push([k, v]); lastWasRule = true; }
  }
  return groups;
}
function rulesFor(groups) {
  const named = groups.filter((g) => g.agents.some((a) => TOKENS.includes(a)));
  if (named.length) return { rules: named.flatMap((g) => g.rules), group: 'named:' + named[0].agents.join(',') };
  const star = groups.filter((g) => g.agents.includes('*'));
  return { rules: star.flatMap((g) => g.rules), group: star.length ? '*' : 'none' };
}
function patRx(p) {
  const end = p.endsWith('$'); if (end) p = p.slice(0, -1);
  return new RegExp('^' + p.split('*').map((x) => x.replace(/[.+?^${}()|[\]\\]/g, '\\$&')).join('.*') + (end ? '$' : ''));
}
function norm(s) { try { return decodeURIComponent(s); } catch (e) { return s; } }
function check(rules, pathQ) {
  let best = null;
  for (const [kind, pat] of rules) {
    if (kind === 'disallow' && pat === '') continue;
    if (patRx(pat).test(pathQ) || patRx(norm(pat)).test(norm(pathQ))) {
      if (!best || pat.length > best.len || (pat.length === best.len && kind === 'allow')) best = { len: pat.length, kind, pat };
    }
  }
  return best ? { allowed: best.kind === 'allow', rule: `${best.kind}: ${best.pat}` } : { allowed: true, rule: null };
}

async function fetchRobots(origin, timeoutMs = 15000) {
  const url = origin + '/robots.txt';
  const ac = new AbortController(); const to = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const r = await fetch(url, { headers: { 'user-agent': UA }, redirect: 'follow', signal: ac.signal });
    const text = r.status === 200 ? (await r.text()).slice(0, 500000) : null;
    return { url, status: r.status, final_url: r.url, text };
  } catch (e) { return { url, status: null, error: String(e && e.name || e) }; } finally { clearTimeout(to); }
}

// Decide which URL (tagged or plain) may be loaded. Returns {ok, url, reason, robots}
async function robotsGate(taggedUrl, plainUrl) {
  const U = new URL(plainUrl);
  const got = await fetchRobots(U.origin);
  const info = { robots_url: got.url, status: got.status, error: got.error || null };
  if (got.status === null || got.status >= 500) return { ok: false, reason: `robots.txt could not be read (${got.error || 'HTTP ' + got.status}); RFC 9309 says to treat the site as disallowed, so nothing was loaded`, robots: info };
  if (got.status >= 400) return { ok: true, url: taggedUrl, reason: `robots.txt returned HTTP ${got.status}: no restrictions`, robots: Object.assign(info, { group: 'none' }) };
  const { rules, group } = rulesFor(parse(got.text));
  info.group = group; info.n_rules = rules.length;
  const pq = (u) => { const x = new URL(u); return x.pathname + x.search; };
  const t = check(rules, pq(taggedUrl));
  info.tagged = Object.assign({ path: pq(taggedUrl) }, t);
  if (t.allowed) return { ok: true, url: taggedUrl, reason: 'allowed by robots.txt', robots: info };
  const p = check(rules, pq(plainUrl));
  info.plain = Object.assign({ path: pq(plainUrl) }, p);
  if (p.allowed && plainUrl !== taggedUrl) return { ok: true, url: plainUrl, reason: `the address with the test tag is disallowed (${t.rule}); using the same page without the tag`, robots: info };
  return { ok: false, reason: `robots.txt disallows ${pq(plainUrl)} (${p.rule || t.rule}); choose a page that robots.txt allows`, robots: info };
}

module.exports = { parse, rulesFor, check, fetchRobots, robotsGate, UA };
