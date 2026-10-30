"""Semantic number checks for the manuscript (consistency pass, 2026-09-26). Called by check_numbers.py.

check_numbers.py shows that every numeric token OCCURS in a saved output. This module checks that numbers that belong
together agree with each other and with stats.json, so that a percentage cannot sit next to the wrong denominator:

  1. PERCENT: every "k of n (p%" / "k/n (p" / table row "k/n & p" : p must equal 100 k / n at the printed precision.
  2. INTERVAL: every "k of n (p%, lo-hi%)" and table row "k/n & p & lo--hi": [lo, hi] must be the Wilson 95% interval of
     k/n at the printed precision, or the interval of a stats.json record that holds the same (k, n) (bootstrap,
     Korn-Graubard); a bracketed "[a--b]" after it must be that record's cluster-bootstrap interval (cb_lo, cb_hi).
  3. TRIPLE: every other "estimate (lo-hi)" or "estimate, 95% CI lo-hi" must match one stats.json record (p / kappa / OR /
     rho / projection count, with lo/hi, cb_lo/cb_hi or lo_fpc/hi_fpc) at the printed precision.
  4. CLAIMS: a registry of the most visible statements (abstract, highlights, figure titles, conclusion, discussion,
     schematic numbers) with the stats.json key and rounding each one must render to.
Every failure is listed in check_numbers_semantic.txt; UNMATCHED triples are failures, not warnings.
"""
import json
import math
import os
import re
from decimal import Decimal, ROUND_HALF_UP

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
S = json.load(open(os.path.join(STUDY, 'analysis', 'outputs', 'stats.json')))


def get(key):
    x = S
    for part in key.split('/'):
        x = x[int(part)] if isinstance(x, list) else x[part]
    return x


def fmt(v, d):
    """Round half up at d decimals (the way the pipeline prints), also accepting Python's banker's rounding."""
    q = Decimal(1).scaleb(-d)
    a = str(Decimal(repr(float(v))).quantize(q, rounding=ROUND_HALF_UP))
    return {a, f'{float(v):.{d}f}'}


def ndec(s):
    return len(s.split('.')[1]) if '.' in s else 0


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


# ---- all records of stats.json that carry an estimate and an interval ----
RECS = []


def collect(x, path=''):
    if isinstance(x, dict):
        est = next((c for c in ('p', 'kappa', 'OR', 'rho', 'estimate', 'est_recall', 'recall') if isinstance(x.get(c), (int, float))), None)
        if est and isinstance(x.get('lo'), (int, float)) and isinstance(x.get('hi'), (int, float)):
            RECS.append((path.lstrip('/'), x, est))
        for k, v in x.items():
            collect(v, f'{path}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            collect(v, f'{path}/{i}')


collect(S)
# derived interval records that live under other key names (checks/*: est_recall + est_recall_lo/hi, est_missed etc.)
EXTRA_TRIPLES = []


def collect_named(x, path=''):
    if isinstance(x, dict):
        for k in list(x):
            if isinstance(x.get(k), (int, float)) and isinstance(x.get(k + '_lo'), (int, float)) and isinstance(x.get(k + '_hi'), (int, float)):
                EXTRA_TRIPLES.append((f'{path}/{k}'.lstrip('/'), x[k], x[k + '_lo'], x[k + '_hi']))
        for k, v in x.items():
            collect_named(v, f'{path}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            collect_named(v, f'{path}/{i}')


collect_named(S)
# referee text pass: Mantel-Haenszel odds ratios are stored as odds_ratio with or_lo / or_hi
def collect_or(x, path=''):
    if isinstance(x, dict):
        if all(isinstance(x.get(c), (int, float)) for c in ('odds_ratio', 'or_lo', 'or_hi')):
            EXTRA_TRIPLES.append((f'{path}/odds_ratio'.lstrip('/'), x['odds_ratio'], x['or_lo'], x['or_hi']))
        for k, v in x.items():
            collect_or(v, f'{path}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            collect_or(v, f'{path}/{i}')


collect_or(S)
# referee text pass: risk differences in percentage points, printed "d pp (95% CI lo to hi)" or "d & lo to hi" (negative values as
# $-x$); they must match a stats.json record (diff, diff_lo, diff_hi) or (rd, rd_lo, rd_hi) at the printed precision
DIFFS = [(path, v, lo, hi) for path, v, lo, hi in EXTRA_TRIPLES if path.endswith('/diff') or path.endswith('/rd') or path in ('diff', 'rd')]
SDEC = r'-?\d+(?:\.\d+)?'
DIFF_RX = re.compile(r'(?<![\w.])(?P<d>' + SDEC + r')(?:\s*(?:pp|percentage points|points))?\s*(?:\(|&|,)\s*(?:95% CI\s*)?(?P<lo>' + SDEC + r')\s+to\s+(?P<hi>' + SDEC + r')')


def triple_matches(p_s, lo_s, hi_s, pct):
    """stats.json records whose (estimate, lo, hi) print as p_s, lo_s, hi_s."""
    d = max(ndec(p_s), ndec(lo_s), ndec(hi_s))
    out = []
    for path, r, est in RECS:
        scale = 100 if (pct and est == 'p') or (est in ('est_recall', 'recall') and pct) else 1
        if est == 'p' and not pct:
            scale = 100 if float(p_s) > 1.0 or float(hi_s) > 1.0 else 1
        pv = r[est] * scale
        if p_s not in fmt(pv, ndec(p_s)):
            continue
        for lk, hk in (('lo', 'hi'), ('cb_lo', 'cb_hi'), ('lo_fpc', 'hi_fpc'), ('kg_lo', 'kg_hi'), ('boot_lo', 'boot_hi'), ('cboot_lo', 'cboot_hi')):
            if isinstance(r.get(lk), (int, float)) and lo_s in fmt(r[lk] * scale, ndec(lo_s)) and hi_s in fmt(r[hk] * scale, ndec(hi_s)):
                out.append(f'{path}[{lk}]')
    for path, v, lo, hi in EXTRA_TRIPLES:
        for scale in ((100, 1) if pct else (1, 100)):
            if p_s in fmt(v * scale, ndec(p_s)) and lo_s in fmt(lo * scale, ndec(lo_s)) and hi_s in fmt(hi * scale, ndec(hi_s)):
                out.append(path)
    # projection counts: "about 382 stores (329-437)"
    for path, r, est in RECS:
        if isinstance(r.get('count'), (int, float)) and isinstance(r.get('count_lo'), (int, float)):
            if p_s in fmt(r['count'], 0) and lo_s in fmt(r['count_lo'], 0) and hi_s in fmt(r['count_hi'], 0):
                out.append(path + '[count]')
    return out


def norm(line):
    line = re.sub(r'(?<!\\)%.*', '', line)                      # LaTeX comments
    line = line.replace('{,}', ',').replace('\\%', '%').replace('--', '\u2013').replace('~', ' ')
    line = line.replace('$', '').replace('\\,', ' ').replace('\\ ', ' ')
    line = line.replace('\u2212', '-').replace('\\textminus', '-')
    # references, citations, labels and code spans carry no measured numbers
    line = re.sub(r'\\(?:ref|label|cite[tp]?|citealt|input|tabinput|includegraphics|url|href|todo|code)\*?(?:\[[^\]]*\])?\{(?:[^{}]|\{[^{}]*\})*\}', ' ', line)
    line = re.sub(r'\b(?:Section|Sections|Table|Tables|Fig|Figs|Figure|Figures|Note)\.?\s*S?\d+(?:\.\d+)*[a-e]?', ' ', line)
    return line


NUMS = r'\d[\d,]*'
DEC = r'\d+(?:\.\d+)?'
# k of n / k/n, then within the same clause "(p%" or "(p," ; allow up to ten words between
PAIR_PCT = re.compile(r'(?<![\w.])(?P<k>' + NUMS + r')(?:\s+of(?:\s+the)?(?:\s+(?!and\b|or\b|of\b)[A-Za-z\'\u2019-]+){0,10}?\s+|/)(?P<n>' + NUMS + r')(?![\d.])'
                      r'(?P<gap>[^()%&\d;]{0,70}?)\((?P<p>' + DEC + r')%?(?P<rest>[^)]{0,60})\)')
TABLE_ROW = re.compile(r'(?P<k>' + NUMS + r')/(?P<n>' + NUMS + r')\s*&\s*(?P<p>' + DEC + r')\s*&\s*(?P<lo>' + DEC + r')\u2013(?P<hi>' + DEC + r')(?:\s*\[(?P<clo>' + DEC + r')\u2013(?P<chi>' + DEC + r')\])?')
CELL = re.compile(r'(?<![\w.])(?P<k>' + NUMS + r')/(?P<n>' + NUMS + r')\s*\((?P<p>' + DEC + r')\)')
TRIPLE = re.compile(r'(?<![\w.\u2013/-])(?P<p>' + DEC + r')(?P<pc>%?)\s*(?:\(|,|&)\s*(?:95% CI\s*|95% CI,?\s*)?(?P<lo>' + DEC + r')%?\s*\u2013\s*(?P<hi>' + DEC + r')(?P<pc2>%?)(?:[;,]?\s*(?:cluster bootstrap by consent tool\s*)?\[?(?P<clo>' + DEC + r')\u2013(?P<chi>' + DEC + r')\]?)?')


def num(s):
    return int(s.replace(',', ''))


def check_file(path):
    fails, notes = [], []
    rel = os.path.relpath(path, HERE)
    seen_triples = set()
    for ln, raw in enumerate(open(path), 1):
        line = norm(raw)
        if not line.strip():
            continue
        # 1 + 2: table rows k/n & p & lo--hi [clo--chi]
        for m in TABLE_ROW.finditer(line):
            k, n, p = num(m['k']), num(m['n']), m['p']
            seen_triples.add((ln, m['p'], m['lo'], m['hi']))
            mods = [f'models/{lst}/{i}' for lst in ('terms_list', 'mixed_list') for i, r in enumerate(S['models'].get(lst, []))
                    if r.get('events_term') == k and r.get('n_term') == n and p in fmt(r['OR'], ndec(p))
                    and m['lo'] in fmt(r['lo'], ndec(m['lo'])) and m['hi'] in fmt(r['hi'], ndec(m['hi']))]
            if mods:
                notes.append(f'{rel}:{ln}: model term events {k}/{n}, OR {p} ({m["lo"]}-{m["hi"]}) = {mods[0]}')
                continue
            if p not in fmt(100 * k / n, ndec(p)):
                fails.append(f'PERCENT {rel}:{ln}: {k}/{n} printed as {p} (is {100 * k / n:.2f})')
            lo, hi = wilson(k, n)
            if not (m['lo'] in fmt(100 * lo, ndec(m['lo'])) and m['hi'] in fmt(100 * hi, ndec(m['hi']))):
                recs = [pp for pp, r, e in RECS if r.get('k') == k and r.get('n') == n and m['lo'] in fmt(100 * r['lo'], ndec(m['lo'])) and m['hi'] in fmt(100 * r['hi'], ndec(m['hi']))]
                if not recs:
                    fails.append(f'INTERVAL {rel}:{ln}: {k}/{n} {m["lo"]}-{m["hi"]} is neither Wilson ({100 * lo:.1f}-{100 * hi:.1f}) nor a stats.json interval of that pair')
            if m['clo']:
                recs = [pp for pp, r, e in RECS if r.get('k') == k and r.get('n') == n and isinstance(r.get('cb_lo'), float)
                        and m['clo'] in fmt(100 * r['cb_lo'], ndec(m['clo'])) and m['chi'] in fmt(100 * r['cb_hi'], ndec(m['chi']))]
                if not recs:
                    fails.append(f'CLUSTER {rel}:{ln}: {k}/{n} [{m["clo"]}-{m["chi"]}] matches no cluster-bootstrap interval of that pair')
                else:
                    notes.append(f'{rel}:{ln}: {k}/{n} cluster [{m["clo"]}-{m["chi"]}] = {recs[0]}')
        # 1 + 2: prose "k of n ... (p%, lo-hi%)"
        for m in PAIR_PCT.finditer(line):
            k, n, p = num(m['k']), num(m['n']), m['p']
            if n < 2 or k > n:
                continue
            if 'Fisher' in m['rest'] or 'p=' in m['rest'] or 'p =' in m['rest']:
                continue
            if re.match(r'\s*(?:of\b|/)', m['rest']) or not (m['rest'].lstrip().startswith('%') or '.' in p or raw.find('%') >= 0 and m['rest'][:1] == '%'):
                continue                                     # "(28 of them", "(9/17", "(19 of 19)": not a percentage of this pair
            if p not in fmt(100 * k / n, ndec(p)):
                fails.append(f'PERCENT {rel}:{ln}: "{m.group(0)[:90]}": {k} of {n} is {100 * k / n:.2f}%, printed {p}')
                continue
            t = re.match(r'\s*%?\s*,\s*(?:95% CI\s*)?(?P<lo>' + DEC + r')%?\u2013(?P<hi>' + DEC + r')', m['rest'])
            if t:
                seen_triples.add((ln, p, t['lo'], t['hi']))
                lo, hi = wilson(k, n)
                if not (t['lo'] in fmt(100 * lo, ndec(t['lo'])) and t['hi'] in fmt(100 * hi, ndec(t['hi']))):
                    recs = [pp for pp, r, e in RECS if r.get('k') == k and r.get('n') == n and any(
                        isinstance(r.get(lk), (int, float)) and t['lo'] in fmt(100 * r[lk], ndec(t['lo'])) and t['hi'] in fmt(100 * r[hk], ndec(t['hi']))
                        for lk, hk in (('lo', 'hi'), ('kg_lo', 'kg_hi'), ('boot_lo', 'boot_hi'), ('cboot_lo', 'cboot_hi')))]
                    if not recs:
                        fails.append(f'INTERVAL {rel}:{ln}: {k} of {n} ({p}%, {t["lo"]}-{t["hi"]}): not the Wilson interval ({100 * lo:.1f}-{100 * hi:.1f}) nor a stats.json interval of that pair')
            notes.append(f'{rel}:{ln}: {k} of {n} -> {p}% ok')
        # 1: table cells "k/n (p)"
        for m in CELL.finditer(line):
            k, n, p = num(m['k']), num(m['n']), m['p']
            if n and p not in fmt(100 * k / n, ndec(p)):
                fails.append(f'PERCENT {rel}:{ln}: cell {k}/{n} ({p}) is {100 * k / n:.2f}')
        # 3b: risk differences with 'to' intervals (may be negative)
        for m in DIFF_RX.finditer(line):
            d_s, lo_s, hi_s = m['d'], m['lo'], m['hi']
            if not (float(lo_s) <= float(d_s) <= float(hi_s)):
                continue
            hits = [pp for pp, v, lo, hi in DIFFS if d_s in fmt(100 * v, ndec(d_s)) and lo_s in fmt(100 * lo, ndec(lo_s)) and hi_s in fmt(100 * hi, ndec(hi_s))]
            if not hits:
                fails.append(f'DIFF {rel}:{ln}: "{d_s} ({lo_s} to {hi_s})" matches no stats.json difference record: {raw.strip()[:120]}')
            else:
                notes.append(f'{rel}:{ln}: difference {d_s} ({lo_s} to {hi_s}) = {hits[0]}')
        # 3: other estimate-interval triples
        for m in TRIPLE.finditer(line):
            key = (ln, m['p'], m['lo'], m['hi'])
            if key in seen_triples:
                continue
            p_s, lo_s, hi_s = m['p'], m['lo'], m['hi']
            if float(lo_s) > float(hi_s) or not (float(lo_s) <= float(p_s) <= float(hi_s)):
                continue                                     # a range, not an estimate with its interval
            pct = bool(m['pc'] or m['pc2']) or float(hi_s) > 1.0
            hits = triple_matches(p_s, lo_s, hi_s, pct)
            if not hits:
                fails.append(f'TRIPLE {rel}:{ln}: "{p_s} ({lo_s}-{hi_s})" matches no stats.json record: {raw.strip()[:120]}')
            else:
                notes.append(f'{rel}:{ln}: {p_s} ({lo_s}-{hi_s}) = {hits[0]}' + (f' (+{len(hits) - 1})' if len(hits) > 1 else ''))
                if m['clo']:
                    cb = [h for h in triple_matches(p_s, m['clo'], m['chi'], pct) if h.endswith('[cb_lo]')]
                    if not cb:
                        fails.append(f'CLUSTER {rel}:{ln}: {p_s} [{m["clo"]}-{m["chi"]}] is not the cluster-bootstrap interval of that estimate')
    return fails, notes


# ---- 4: registry of the most visible claims: (file, regex that must occur, value computed from stats, printed text) ----
def pct(key, d=0):
    return f'{100 * get(key):.{d}f}'


def kn(key):
    return f"{get(key + '/k')} of {get(key + '/n')}"


def c(n):
    return f'{n:,}'


CLAIMS = [
    # abstract and introduction rewritten to the author's writing notes (2026-10-17): verbal ratios checked here
    ('frontmatter.tex', r'A working Decline halved new-sandbox firing',
     2 * get('fig5/compare/default_vs_decline/paired_diff/k_b') == get('fig5/compare/default_vs_decline/paired_diff/k_a')
     and get('fig5/compare/default_vs_decline/b_only') == 0),
    ('frontmatter.tex', r'nearly triple the rate under a denying default',
     2.75 <= get('fig3/d/opt_out/any_sbx/p') / get('fig3/d/opt_in/any_sbx/p') < 3),
    ('sections/s1_intro.tex', r'fired on 70.2% of banner stores whose region default allowed tracking and on 24.0%',
     pct('fig3/d/opt_out/any_sbx/p', 1) == '70.2' and pct('fig3/d/opt_in/any_sbx/p', 1) == '24.0'),
    ('sections/s1_intro.tex', r'on 46 of 89 blocklist stores', kn('round4/blocklist/combined/primary/fired') == '46 of 89'),
    # abstract (referee text pass 2026-09-26)
    ('frontmatter.tex', r'loaded 1,358 popular Shopify storefronts', c(get('design/n_main')) == '1,358'),
    ('frontmatter.tex', r'plus 116 lower-ranked stores chosen for their CMP blocklists', get('round4/blocklist/expansion_funnel/captured_all_three') == 116),
    ('frontmatter.tex', r'On 89 stores whose blocklist named an ad vendor as blocked', get('round4/blocklist/combined/primary/fired/n') == 89),
    ('frontmatter.tex', r'before any choice on 46 \(51.7%\)', kn('round4/blocklist/combined/primary/fired') == '46 of 89' and pct('round4/blocklist/combined/primary/fired/p', 1) == '51.7'),
    ('frontmatter.tex', r'blocklist stores fired more often than comparable stores without one, not less', get('round4/blocklist/combined/like_for_like/mh_no_yes/rd_lo') > 0),
    ('frontmatter.tex', r'still sent ad requests on 23% of stores;', pct('fig5/decline/fresh/p') == '23'),
    ('frontmatter.tex', r'yet 35% of stores with sandboxed requests', pct('fig5/gpc_residual/p') == '35'),
    ('frontmatter.tex', r'came after 525 of 535 third-party marketing sandboxes', (get('fig5/d/deny/pixels_before'), get('fig5/d/deny/pixels')) == (525, 535)),
    ('frontmatter.tex', r'fired on 70% of banner stores where Shopify', pct('fig3/d/opt_out/any_sbx/p') == '70'),
    ('frontmatter.tex', r'after a working Decline on 42% to 88% of sites', min(get('round4/beyond/rates/' + a + '/decline/after_ad/p') for a in ('wix', 'bigcommerce', 'gateway')) == get('round4/beyond/rates/wix/decline/after_ad/p') and pct('round4/beyond/rates/wix/decline/after_ad/p') == '42' and pct('round4/beyond/rates/gateway/decline/after_ad/p') == '88' and max(get('round4/beyond/rates/' + a + '/decline/after_ad/p') for a in ('wix', 'bigcommerce', 'gateway')) == get('round4/beyond/rates/gateway/decline/after_ad/p')),
    # highlights (the .txt copy must say the same)
    ('highlights.tex', r'on 46 of 89 stores \(51.7%\)', kn('round4/blocklist/combined/primary/fired') == '46 of 89' and pct('round4/blocklist/combined/primary/fired/p', 1) == '51.7'),
    ('highlights.tex', r'sandboxed ads more often than stores without one', get('round4/blocklist/combined/like_for_like/mh_no_yes/rd_lo') > 0),
    ('highlights.tex', r'279 of 803 stores kept other sandboxed ads', kn('fig5/gpc_residual') == '279 of 803' and get('fig5/c/gate_audit/gpc_sale_pixels/k') == 0),
    ('highlights.tex', r'still fired on 23% of stores', pct('fig5/decline/fresh/p') == '23'),
    ('highlights.tex', r'after 525 of 535 third-party marketing sandboxes', (get('fig5/d/deny/pixels_before'), get('fig5/d/deny/pixels')) == (525, 535)),
    ('highlights.txt', r'on 46 of 89 stores \(51.7%\)', True),
    ('highlights.txt', r'sandboxed ads more often than stores without one', True),
    ('highlights.txt', r'279 of 803 stores kept other sandboxed ads', True),
    ('highlights.txt', r'still fired on 23% of stores', True),
    ('highlights.txt', r'after 525 of 535 third-party marketing sandboxes', True),
    # figure titles and panel facts quoted in captions (v2 captions since 2026-09-27: captions/*.tex, generated from figures/v2)
    # v6 r2 caption (2026-10-19): the defaults are named with their marks, then the top row gives 'allowed' first, 'denied' second
    # v7 caption (2026-10-20): the marks also say where they sit on a row, and the all-banner-stores row is the bottom row,
    # set apart; the same fact ('allowed' 165 of 235, 70.2%, against 'denied' 40 of 167, 24.0%)
    ('captions/fig3.tex', r"`allowed until choice' \(brick circles, just above each row's centre line\) and `denied until consent' \(slate squares, just below it\)\..*? Bottom row, set apart: all 402 banner stores with a readable default, 165 of 235 \(70\.2%;.*? against 40 of 167 \(24\.0%",
     kn('fig3/d/opt_out/any_sbx') == '165 of 235' and kn('fig3/d/opt_in/any_sbx') == '40 of 167' and pct('fig3/d/opt_out/any_sbx/p', 1) == '70.2'),
    ('captions/fig3.tex', r'The 7 banner stores without a readable default are not shown',
     get('fig1b/banner_fires/n') - get('fig3/d/opt_out/any_sbx/n') - get('fig3/d/opt_in/any_sbx/n') == 7),
    ('captions/fig4.tex', r'blocklist stores fired more, not less, often', get('round4/blocklist/combined/like_for_like/mh_no_yes/rd_lo') > 0),
    # v5 figures (2026-10-17): the primary-set entry matrices moved from Fig 4a to Supplementary Fig. S7d, with this sentence
    ('captions/figS7.tex', r"the route through Shopify's sandbox \(12 of 19 entries",
     (get('derived_v2/fig4/fig4a_entries/value/counts/sandbox'), get('derived_v2/fig4/fig4a_entries/value/counts/n')) == (12, 19)
     and (get('derived_v2/shared/fig4a_routes/value/primary_no_yes/sandbox'), get('derived_v2/shared/fig4a_routes/value/primary_no_yes/n')) == (12, 19)),
    ('captions/figS6.tex', r'The 9 stores whose first request lies beyond the axis are counted at its ends', get('fig3/b/n_gap_beyond_axis') == 9),   # v6 S6b wording
    ('captions/fig6.tex', r'all vendors, 63.4% of 10,676 beacons on 769 stores',
     pct('fig6/a/sandboxed_A0/p', 1) == '63.4' and get('fig6/a/sandboxed_A0/n') == 10676 and get('fig6/a/sandboxed_A0/n_stores') == 769),
    ('sections/s5_results.tex', r'On 32 of these 167 banner stores', kn('fig3/d/opt_in/nomkt_sbx') == '32 of 167'),
    ('sections/s6_application.tex', r'about 2,444 DNS-flagged storefronts', c(round(get('fig5/e/population_estimate'))) == '2,444'),
    ('sections/s6_application.tex', r'agreed on 271 of 273 stores', (get('validation/A0_vs_A0r/agree'), get('validation/A0_vs_A0r/n')) == (271, 273)),
    # discussion and conclusion
    ('sections/s7_discussion.tex', r'with exceptions on 7 of 1,179 stores', kn('fig5/c/gate_audit/pixel_starts/informative_stores') == '7 of 1179'),
    ('sections/s7_discussion.tex', r'fired on 70.2% of banner stores with that default', pct('fig3/d/opt_out/any_sbx/p', 1) == '70.2'),
    ('sections/s7_discussion.tex', r'fired from the sandbox on 46 of 89 stores', kn('round4/blocklist/combined/primary/fired') == '46 of 89'),
    ('sections/s7_discussion.tex', r'after 20 of 231 working Decline clicks', (get('fig5/decline/still_allowed/k'), get('fig5/decline/still_allowed/n')) == (20, 231)),
    ('sections/s7_discussion.tex', r'after 525 of 535 third-party marketing sandboxes', (get('fig5/d/deny/pixels_before'), get('fig5/d/deny/pixels')) == (525, 535)),
    ('sections/s7_discussion.tex', r'kept sending on 32 of 196 stores', kn('fig5/c/fig5c_rows/f3') == '32 of 196'),
    ('sections/s7_discussion.tex', r'after 112 of the 196 refusals', kn('fig5/c/composition/decline_sale_after_refusal/sale_allowed') == '112 of 196'),
    ('sections/s8_ethics_limits_conclusion.tex', r'across 1,358 popular storefronts', get('design/n_main') == 1358),
    ('sections/s8_ethics_limits_conclusion.tex', r'before any choice on 46 of 89 stores', kn('round4/blocklist/combined/primary/fired') == '46 of 89' and get('round4/blocklist/combined/like_for_like/mh_no_yes/rd_lo') > 0),
    ('sections/s8_ethics_limits_conclusion.tex', r'still sent ad requests on 23% of stores', pct('fig5/decline/fresh/p') == '23'),
    ('sections/s8_ethics_limits_conclusion.tex', r'by more than 0.4 percentage points', True),
]


def check_claims():
    fails, notes = [], []
    for rel, rx, ok in CLAIMS:
        txt = open(os.path.join(HERE, rel)).read().replace('{,}', ',').replace('\\%', '%').replace('~', ' ')
        txt = re.sub(r'\s+', ' ', txt)
        if not re.search(rx, txt):
            fails.append(f'CLAIM {rel}: text /{rx}/ not found (claim registry out of date or text changed)')
        elif not ok:
            fails.append(f'CLAIM {rel}: /{rx}/ does not match stats.json')
        else:
            notes.append(f'CLAIM {rel}: /{rx}/ ok')
    return fails, notes


def check_schematic_numbers():
    """Figure 1a/2 schematics read their numbers from figures/schematics/numbers.tex (make_numbers.py)."""
    fails, notes = [], []
    t = open(os.path.join(STUDY, 'figures', 'schematics', 'numbers.tex')).read()
    mac = dict(re.findall(r'\\newcommand\{\\(\w+)\}\{([^}]*)\}', t))
    exp = {'nCaptured': c(get('design/n_main')), 'nSample': c(get('design/sample_n')), 'nTranco': c(get('design/tranco_top_n')),
           'nCreatorCaptured': str(get('design/n_creator')), 'nExclLive': str(get('design/funnel_excl/drawn_to_live')),
           'nExclSample': str(get('design/funnel_excl/live_to_sample')), 'nExclCaptured': str(get('design/funnel_excl/sample_to_captured')),
           'nRepeatPlanned': str(get('design/repeat_planned')), 'nBravePlanned': str(get('design/brave_planned')),
           'pRegionAllowed': pct('fig1b/region_allowed/p')}
    for k, v in exp.items():
        (notes if mac.get(k) == v else fails).append(f'SCHEMATIC \\{k} = {mac.get(k)} (stats.json: {v})')
    return fails, notes


def run(files):
    fails, notes = [], []
    for f in files:
        a, b = check_file(f)
        fails += a
        notes += b
    for fn in (check_claims, check_schematic_numbers):
        a, b = fn()
        fails += a
        notes += b
    return fails, notes
