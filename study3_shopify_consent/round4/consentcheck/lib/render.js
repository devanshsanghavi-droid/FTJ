// Single-file HTML report (no external resources): readable, accessible (semantic headings, table captions and
// header scopes, status in words as well as colour, AA contrast, skip link, light/dark), and printable.
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtS = (ms) => (ms == null ? '—' : (ms / 1000).toFixed(1) + ' s');

const STATUS = {
  sends: ['bad', '✗', 'Sent data'],
  silent: ['neutral', '–', 'Nothing sent'],
  stopped: ['good', '✓', 'Stopped'],
  partly: ['warn', '!', 'Kept sending briefly, then stopped'],
  not_stopped: ['bad', '✗', 'Not stopped'],
  not_seen: ['neutral', '–', 'Not seen in this test'],
  not_tested: ['neutral', '?', 'Not tested'],
};
function badge(key, extra) {
  const [cls, sym, txt] = STATUS[key] || ['neutral', '?', key];
  return `<span class="st st-${cls}"><span aria-hidden="true" class="sym">${sym}</span> ${esc(txt)}${extra ? `<span class="sub">${esc(extra)}</span>` : ''}</span>`;
}
function yesNo(val, goodWhen, txtYes, txtNo, txtNA) {
  if (val === null || val === undefined) return `<span class="st st-neutral"><span aria-hidden="true" class="sym">?</span> ${esc(txtNA || 'Not tested')}</span>`;
  const good = val === goodWhen;
  return `<span class="st st-${good ? 'good' : 'bad'}"><span aria-hidden="true" class="sym">${good ? '✓' : '✗'}</span> ${esc(val ? txtYes : txtNo)}</span>`;
}
const SEVLABEL = { high: ['bad', 'Problem'], medium: ['warn', 'Warning'], low: ['neutral', 'Check'], info: ['info', 'Note'] };
const WHERE = { sandbox: "Shopify's pixel sandbox", shopify_open: 'main page (Shopify OPEN pixel)', page: 'main page (theme / tag manager / app script)' };

function declineText(d) {
  switch (d.status) {
    case 'recorded': return ['good', '✓', `Yes: Shopify recorded "no" ${d.delay_ms != null ? fmtS(d.delay_ms) + ' after the click' : ''}`];
    case 'recorded_marketing_only': return ['warn', '!', 'Partly: marketing "no", but data sale stayed allowed'];
    case 'not_recorded_still_allowed': return ['bad', '✗', 'No: Shopify still allowed marketing after the click'];
    case 'not_recorded_default_denied': return ['warn', '!', 'No explicit record (Shopify already denied marketing by default)'];
    case 'no_decline_button': return ['bad', '✗', 'Not tested: no Decline/Reject button found'];
    case 'no_banner': return ['neutral', '–', 'Not tested: no banner appeared'];
    case 'click_failed': return ['neutral', '?', 'Not tested: the click did not work'];
    default: return ['neutral', '?', 'Not tested'];
  }
}

function render(res) {
  const s = res.store; const t = res.target;
  const host = t.host || '';
  const vend = res.vendors || [];
  const pre = vend.filter((v) => v.before_choice === 'sends');
  const preSbx = pre.filter((v) => v.where_before.includes('sandbox'));
  const dNot = vend.filter((v) => v.decline === 'not_stopped');
  const gNot = vend.filter((v) => v.gpc === 'not_stopped');
  const np = (res.pixels || []).filter((p) => p.flags.no_purpose);
  const dt = declineText(s.decline);
  const probs = res.findings.filter((f) => f.severity === 'high').length;
  const warns = res.findings.filter((f) => f.severity === 'medium').length;
  const date = new Date(res.generated_at);
  const names = (l) => l.map((v) => v.name).join(', ');
  const vis = res.visits || {};

  const summaryRows = [
    ['Ad vendors that received data before any choice', pre.length ? `<span class="st st-${s.banner.shown ? 'bad' : 'neutral'}"><span class="sym" aria-hidden="true">${s.banner.shown ? '✗' : '•'}</span> ${pre.length}: ${esc(names(pre))}</span>` : badge('silent')],
    ["…of which from Shopify's pixel sandbox (out of reach of script blocking)", preSbx.length ? `<strong>${preSbx.length}</strong>: ${esc(names(preSbx))}` : '0'],
    ['Is the Decline passed to Shopify?', `<span class="st st-${dt[0]}"><span class="sym" aria-hidden="true">${dt[1]}</span> ${esc(dt[2])}</span>`],
    ['Did Decline stop every ad vendor on the next page?', vis.decline && vis.decline.usable && s.decline.clicked ? yesNo(dNot.length === 0, true, 'Yes', `No: ${names(dNot)}`) : badge('not_tested')],
    ['Did GPC stop every ad vendor?', vis.gpc && vis.gpc.usable ? yesNo(gNot.length === 0, true, 'Yes', `No: ${names(gNot)}`) : badge('not_tested')],
    ['Installed pixels that declare no consent purpose', np.length ? `<span class="st st-warn"><span class="sym" aria-hidden="true">!</span> ${np.length}</span>` : yesNo(true, true, 'None', '')],
  ];

  const findings = res.findings.map((f) => { const [cls, lab] = SEVLABEL[f.severity]; return `<li class="finding f-${cls}"><p class="ftitle"><span class="sev sev-${cls}">${lab}</span> ${esc(f.title)}</p><p>${esc(f.text)}</p>${f.fixes.length ? `<p class="fx">See fix${f.fixes.length > 1 ? 'es' : ''}: ${f.fixes.map((x) => { const i = res.fixes.findIndex((y) => y.id === x); return i >= 0 ? `<a href="#fix-${esc(x)}">${i + 1}</a>` : ''; }).filter(Boolean).join(', ')}</p>` : ''}</li>`; }).join('');

  const fixes = res.fixes.map((f, i) => `<li id="fix-${esc(f.id)}"><h3>${i + 1}. ${esc(f.title)}</h3><ol class="steps">${f.steps.map((x) => `<li>${esc(x)}</li>`).join('')}</ol>${f.links.length ? `<p class="links">Shopify documentation: ${f.links.map((u) => `<a href="${esc(u)}">${esc(u.replace(/^https:\/\//, ''))}</a>`).join(' · ')}</p>` : ''}</li>`).join('');

  const vrows = vend.map((v) => {
    const d = v.detail;
    const whereTxt = (v.where_before || []).map((w) => WHERE[w] || w).join('; ') || '—';
    const preExtra = v.before_choice === 'sends' ? `${d.default.n} request${d.default.n === 1 ? '' : 's'}, first at ${fmtS(d.default.first_t)}` : '';
    const decExtra = v.decline === 'not_stopped' ? `${d.decline.next_page.n} on the fresh page` : v.decline === 'partly' ? `${d.decline.same_page.n + d.decline.unload.n} leftover` : '';
    const gpcExtra = v.gpc === 'not_stopped' ? `${d.gpc.n} request${d.gpc.n === 1 ? '' : 's'}` : '';
    const px = (v.pixels || []).map((p) => `<li>${esc(p.label)}: <span class="pp">${p.purposes && p.purposes.length ? esc(p.purposes.join(', ')) : '<strong>no purpose</strong>'}</span></li>`).join('');
    const why = [v.why.decline ? `After Decline: ${v.why.decline}` : '', v.why.gpc ? `With GPC: ${v.why.gpc}` : ''].filter(Boolean).map((x) => `<p class="why">${esc(x)}</p>`).join('');
    const paper = v.declared_by_banner ? `<p class="why">Consent app configuration: ${esc(v.declared_by_banner.pre === 'blocked' ? 'listed as blocked until consent' : 'listed, allowed')} (${esc(v.declared_by_banner.detail)}).${v.blocked_on_paper ? ' <strong>Blocked on paper:</strong> it sent data from the sandbox anyway.' : ''}</p>` : '';
    return `<tr><th scope="row">${esc(v.name)}</th><td>${badge(v.before_choice, preExtra)}</td><td>${esc(whereTxt)}</td><td>${badge(v.decline, decExtra)}</td><td>${badge(v.gpc, gpcExtra)}</td><td>${px ? `<ul class="plain">${px}</ul>` : '<span class="muted">not a Shopify pixel</span>'}${why}${paper}</td></tr>`;
  }).join('');

  const prows = (res.pixels || []).map((p) => {
    const note = p.shopify_own ? "Shopify's own" : p.flags.no_purpose ? '<strong>No purpose: starts whatever the visitor chooses</strong>' : p.flags.marketing_without_data_sale ? 'Marketing, but not data sale: GPC does not stop it' : '';
    return `<tr${p.flags.no_purpose ? ' class="hl"' : ''}><th scope="row">${esc(p.name || p.app || 'pixel ' + p.id)}<span class="sub">${esc(p.type === 'CUSTOM' ? 'custom pixel' : 'app pixel')} · id ${esc(p.id)}</span></th><td>${esc(p.runtime_label)}</td><td>${p.purposes.length ? esc(p.purposes.join(', ')) : '<strong>none</strong>'}</td><td>${esc(p.contacted.join(', ') || '—')}</td><td>${p.sent_ad_data ? '<span class="st st-bad"><span class="sym" aria-hidden="true">✗</span> yes</span>' : 'no'}</td><td>${note}</td></tr>`;
  }).join('');

  const a = s.automatic_before_choice || {};
  const sd = s.shopify_default;
  const stateRows = [
    ['Visitor region (as Shopify saw it)', esc(s.region || 'unknown')],
    ['Consent app detected', esc(s.consent_app_name || 'none detected') + (s.consent_apps_detected && s.consent_apps_detected.length > 1 ? ` <span class="muted">(also: ${esc(s.consent_apps_detected.join(', '))})</span>` : '')],
    ['Banner shown', s.banner.shown ? `Yes, visible at ${fmtS((s.banner.default_visit && s.banner.default_visit.t) ?? (s.banner.decline_visit && s.banner.decline_visit.t))}${(s.banner.decline_visit.controls || []).length ? ` · buttons: ${esc(s.banner.decline_visit.controls.slice(0, 5).join(' | '))}` : ''}` : 'No'],
    ["Shopify's default before any choice", sd ? (sd.marketing_allowed_before_choice ? 'Marketing <strong>allowed</strong> until the visitor opts out' : 'Marketing <strong>denied</strong> until the visitor consents') + ` <span class="muted">(Server-Timing _cmp ${esc(sd.header)})</span>` : 'unknown'],
    ['Automatic "yes" before any click', a.first_yes_ms != null ? `<span class="st st-bad"><span class="sym" aria-hidden="true">✗</span> at ${fmtS(a.first_yes_ms)}</span>` : 'none seen'],
    ['Automatic "no" before any click', a.first_no_ms != null ? `at ${fmtS(a.first_no_ms)}${a.first_sandboxed_ad_ms != null && a.first_sandboxed_ad_ms < a.first_no_ms ? ` · <strong>after</strong> the first sandboxed ad request (${fmtS(a.first_sandboxed_ad_ms)})` : ''}` : 'none seen'],
    ['Decline click', s.decline.clicked ? `Clicked "${esc(s.decline.clicked_text || '')}" at ${fmtS(s.decline.click_ms)}${s.decline.banner_gone === false ? ' (banner still visible afterwards)' : ''}` : esc(dt[2])],
    ['Is the Decline passed to Shopify?', `<span class="st st-${dt[0]}"><span class="sym" aria-hidden="true">${dt[1]}</span> ${esc(dt[2])}</span>`],
    ['GPC opt-out recorded by Shopify', s.gpc.shopify_recorded_opt_out == null ? 'not tested' : yesNo(!!s.gpc.shopify_recorded_opt_out, true, 'Yes (sale of data: no)', 'No')],
  ];

  const shots = res.screenshots ? Object.entries(res.screenshots).map(([k, b64]) => `<figure><img src="data:image/jpeg;base64,${b64}" alt="Screenshot of the store page ${k === 'before_click' ? 'with the consent banner, before the Decline click' : 'two seconds after the Decline click'}" loading="lazy"><figcaption>${k === 'before_click' ? 'Before the Decline click' : '2 s after the Decline click'}</figcaption></figure>`).join('') : '';

  const visitRows = [['default', 'Default: no click, 15 s'], ['decline', 'Decline: click Decline/Reject, 15 s, then the same page again for 10 s'], ['gpc', 'GPC: Global Privacy Control on, 15 s']].map(([k, lab]) => {
    const v = vis[k] || {};
    return `<tr><th scope="row">${esc(lab)}</th><td>${v.usable ? 'usable' : `<strong>not usable</strong>: ${esc(v.why_not || '')}`}</td><td>${v.http_status ?? '—'}</td><td>${v.requests ?? '—'}</td><td>${v.ad_requests ?? '—'}</td></tr>`;
  }).join('');

  const css = `
:root{--bg:#ffffff;--fg:#1d2433;--muted:#5b6475;--line:#d9dee7;--card:#f7f8fa;--accent:#2848a8;
--good:#067647;--goodbg:#ecfdf3;--bad:#b42318;--badbg:#fef3f2;--warn:#8a3a0c;--warnbg:#fff6e5;--neu:#475467;--neubg:#f0f2f5;--info:#1f4e8c;--infobg:#eef4fc}
@media (prefers-color-scheme: dark){:root{--bg:#12151c;--fg:#e8ebf1;--muted:#a3abba;--line:#2c3340;--card:#1a1f29;--accent:#8fb0ff;
--good:#6ce9a6;--goodbg:#0f2a1d;--bad:#ffa39e;--badbg:#3a1614;--warn:#fec84b;--warnbg:#33240b;--neu:#c2c8d2;--neubg:#252b36;--info:#9ec5ff;--infobg:#172538}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 48px}
.skip{position:absolute;left:-9999px}.skip:focus{left:12px;top:12px;background:var(--bg);padding:8px;z-index:9;outline:3px solid var(--accent)}
header{border-bottom:1px solid var(--line);padding:28px 0 18px;margin-bottom:8px}
.eyebrow{margin:0;color:var(--muted);font-size:.85rem;letter-spacing:.06em;text-transform:uppercase}
h1{margin:.2rem 0 .3rem;font-size:1.9rem;line-height:1.2;word-break:break-word}
h2{font-size:1.35rem;margin:2.2rem 0 .8rem;padding-top:.4rem;border-top:1px solid var(--line)}
h3{font-size:1.05rem;margin:1.2rem 0 .4rem}
.meta{color:var(--muted);margin:0;font-size:.95rem;word-break:break-all}
a{color:var(--accent)}a:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.tally{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 4px;padding:0;list-style:none}
.tally li{border:1px solid var(--line);border-radius:6px;padding:6px 12px;background:var(--card);font-weight:600}
table{border-collapse:collapse;width:100%;margin:.4rem 0 1rem;font-size:.95rem}
caption{text-align:left;color:var(--muted);font-size:.9rem;padding:0 0 6px}
th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}
thead th{font-size:.82rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);border-bottom:2px solid var(--line)}
tbody th{font-weight:600}
.kv th{width:38%;font-weight:600}
.st{display:inline-block;border-radius:5px;padding:2px 8px;font-weight:600;font-size:.9rem}
.st .sym{font-weight:700;margin-right:2px}
.st .sub{display:block;font-weight:400;font-size:.8rem;opacity:.9}
.st-good{color:var(--good);background:var(--goodbg)}.st-bad{color:var(--bad);background:var(--badbg)}
.st-warn{color:var(--warn);background:var(--warnbg)}.st-neutral{color:var(--neu);background:var(--neubg)}
.sub{display:block;color:var(--muted);font-size:.8rem;font-weight:400}
.muted{color:var(--muted)}
ul.findings{list-style:none;padding:0;margin:0}
.finding{border:1px solid var(--line);border-left-width:6px;border-radius:6px;padding:10px 14px;margin:10px 0;background:var(--card)}
.finding p{margin:.3rem 0}.f-bad{border-left-color:var(--bad)}.f-warn{border-left-color:var(--warn)}.f-neutral{border-left-color:var(--neu)}.f-info{border-left-color:var(--info)}
.ftitle{font-weight:650}
.sev{display:inline-block;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;border-radius:4px;padding:1px 7px;margin-right:6px;vertical-align:1px}
.sev-bad{color:var(--bad);background:var(--badbg)}.sev-warn{color:var(--warn);background:var(--warnbg)}.sev-neutral{color:var(--neu);background:var(--neubg)}.sev-info{color:var(--info);background:var(--infobg)}
.fx{font-size:.9rem;color:var(--muted)}
ol.fixes{list-style:none;padding:0}ol.fixes>li{border:1px solid var(--line);border-radius:6px;padding:4px 16px 10px;margin:12px 0}
ol.steps{padding-left:1.3rem}ol.steps li{margin:.25rem 0}
.links{font-size:.88rem;color:var(--muted);word-break:break-word}
ul.plain{list-style:none;padding:0;margin:0}ul.plain li{margin:.1rem 0}
.why{font-size:.88rem;color:var(--muted);margin:.35rem 0 0}
tr.hl th,tr.hl td{background:var(--warnbg)}
figure{margin:0 0 16px}figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:4px}figcaption{color:var(--muted);font-size:.9rem}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.scroll{overflow-x:auto}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:.88rem}
@media (max-width:700px){.wrap{padding:0 16px 40px}h1{font-size:1.5rem}th,td{padding:7px 6px}.kv th{width:45%}}
@media print{:root{--bg:#fff;--fg:#000;--muted:#333;--line:#999;--card:#fff}
body{font-size:10.5pt}.skip{display:none}.wrap{max-width:none;padding:0}
h2{break-after:avoid;page-break-after:avoid}tr,.finding,ol.fixes>li,figure{break-inside:avoid;page-break-inside:avoid}
a{color:#000}.links a::after{content:""}.st,.sev{border:1px solid currentColor}.shots{display:block}figure img{max-height:9cm}}
`;

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>ConsentCheck report: ${esc(host)}</title>
<style>${css}</style>
</head>
<body>
<a class="skip" href="#main">Skip to the results</a>
<div class="wrap">
<header>
<p class="eyebrow">ConsentCheck report</p>
<h1>${esc(host)}</h1>
<p class="meta">Tested ${esc(date.toUTCString())} · visitor region ${esc(s.region || 'unknown')} · page <a href="${esc(t.loaded_url || t.url)}">${esc(t.loaded_url || t.url)}</a></p>
<ul class="tally" aria-label="Totals"><li>${probs} problem${probs === 1 ? '' : 's'}</li><li>${warns} warning${warns === 1 ? '' : 's'}</li><li>${vend.length} ad vendor${vend.length === 1 ? '' : 's'} seen</li><li>${(res.pixels || []).length} Shopify pixels installed</li></ul>
</header>
<main id="main">
<section aria-labelledby="h-sum">
<h2 id="h-sum">Summary</h2>
<table class="kv"><caption>Does your cookie banner control your ad pixels? One visit per condition.</caption><tbody>
${summaryRows.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${v}</td></tr>`).join('\n')}
</tbody></table>
<h3>What we found</h3>
<ul class="findings">${findings}</ul>
</section>
${res.fixes.length ? `<section aria-labelledby="h-fix"><h2 id="h-fix">What to fix, in order</h2><ol class="fixes">${fixes}</ol></section>` : ''}
<section aria-labelledby="h-vend">
<h2 id="h-vend">Ad vendors, visit by visit</h2>
${vend.length ? `<div class="scroll"><table><caption>Every advertising vendor that received a request in any visit. "Sandbox" means Shopify ran the vendor's pixel in a web worker or hidden iframe, where a consent app's script blocking cannot reach it.</caption>
<thead><tr><th scope="col">Vendor</th><th scope="col">Before any choice</th><th scope="col">Ran in</th><th scope="col">After Decline (fresh page)</th><th scope="col">With GPC</th><th scope="col">Shopify pixels involved and their declared purposes</th></tr></thead>
<tbody>${vrows}</tbody></table></div>` : '<p>No advertising vendor received a request in any visit.</p>'}
</section>
<section aria-labelledby="h-state">
<h2 id="h-state">Your consent app and Shopify</h2>
<table class="kv"><caption>Times are seconds after the page request started.</caption><tbody>
${stateRows.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${v}</td></tr>`).join('\n')}
</tbody></table>
</section>
<section aria-labelledby="h-pix">
<h2 id="h-pix">Installed Shopify pixels</h2>
${prows ? `<div class="scroll"><table><caption>From the pixel list Shopify embeds in the page. Shopify starts a pixel only when the visitor's consent allows every purpose it declares; a pixel that declares none starts at once.</caption>
<thead><tr><th scope="col">Pixel</th><th scope="col">Runs in</th><th scope="col">Declared purposes</th><th scope="col">Contacted</th><th scope="col">Sent ad data</th><th scope="col">Note</th></tr></thead>
<tbody>${prows}</tbody></table></div>` : `<p>${s.pixel_config_found ? 'No pixels are installed.' : "Shopify's pixel list was not found in the page."}</p>`}
</section>
${shots ? `<section aria-labelledby="h-shots"><h2 id="h-shots">Screenshots of the Decline visit</h2><div class="shots">${shots}</div></section>` : ''}
<section aria-labelledby="h-how">
<h2 id="h-how">What was tested</h2>
<p>ConsentCheck opened the page three times, each time in a new, empty browser profile, and recorded every network request, which part of the page sent it, and the consent state Shopify reported about once a second.</p>
<div class="scroll"><table><caption>Visits in this run</caption><thead><tr><th scope="col">Visit</th><th scope="col">Result</th><th scope="col">HTTP</th><th scope="col">Requests</th><th scope="col">Ad requests</th></tr></thead><tbody>${visitRows}</tbody></table></div>
<p>It clicked nothing except the banner's Decline/Reject button, never Accept; it did not log in, add to cart or fill in any form. It checked <code>robots.txt</code> first (${esc(res.run.robots && res.run.robots.reason || '')}), waited at least 10 seconds between page loads, and used an unmodified automated Chromium${res.run.user_agent ? ` (<span class="muted">${esc(res.run.user_agent)}</span>)` : ''}.</p>
<h3>Limitations</h3>
<ul>${res.limitations.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>
</section>
</main>
<footer>
<p>ConsentCheck ${esc(res.tool.version)} · open source · built from the measurement crawler of the study <em>Blocked on paper: How consent is lost between cookie banners and Shopify's sandboxed web pixels</em>. Not legal advice. The report stays on your computer; ConsentCheck sends nothing to its authors.</p>
</footer>
</div>
</body>
</html>
`;
}

module.exports = { render };
