"""Build round4/beyond/candidates.csv from the screening results (no network).

Re-runs markers.analyse() on saved (gzipped) homepages screened before the last marker revision (all pages with
REANALYSE_ALL=1), then
classifies each site, applies exclusions and draws the seeded pilot sample per architecture.

Eligibility (all must hold): HTTP 200 HTML homepage on the same registrable domain; robots.txt allows "/";
not flagged adult / child-directed (name, rating meta, title/description screens) or age-restricted (gambling, AI roleplay); not a Shopify storefront;
at least one architecture marker; a consent tool visible in the static HTML (Zaraz: see tiers).
Architectures: partytown (>=1 script type="text/partytown"), zaraz (Zaraz loader or zaraz API in the HTML),
gateway (Google tag served from a first-party or tag-gateway host, server-container URL, custom loader or
Meta CAPI gateway), wix (Wix platform), bigcommerce (BigCommerce platform).
Tiers (L = Partytown library present but no text/partytown script in the static HTML, e.g. scripts added at run
time, possibly only after consent): A = the consent tool is the platform's/architecture's own or a known CMP AND an ad/analytics tag is
visible in the static HTML; B = consent tool visible but no tag visible statically; Z = Zaraz without a static
CMP (Zaraz's own consent modal is injected at run time and cannot be seen statically; confirmed at crawl time).
Tier U (Partytown / gateway sites with no consent tool in the static HTML; a CMP may still be injected at run time,
e.g. by GTM) is eligible only as `backup_unconfirmed_cmp`: never selected, usable if the mentor wants to top up.
Selection: per architecture, eligible sites in a seeded random order (seed 20260927); the first 80 are
`selected`, the next up to 20 are `reserve` (ethics cap: at most 100 per setup, 500 in all).
Usage: python build_candidates.py        -> ../candidates.csv, raw/screen_summary.json
"""
import csv, gzip, hashlib, json, os, random, re, collections
import markers as M

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
OUT = os.path.join(HERE, '..', 'candidates.csv')
SEED = 20260927
AGE_RESTRICTED = re.compile(r"(casino|slots|poker|sportsbook|betting|bingo|roulette|blackjack)", re.I)
AGE_RESTRICTED_TXT = re.compile(r"\b(casinos?|slots?\s+(?:games?|spiele|online)|online\s+slots?|sports?\s*betting|sportsbook|poker|gambling|"
                                r"gl(?:ue|ü)cksspiel\w*|apuestas|scommesse|ai\s+(?:roleplay|girlfriend|companions?)|roleplay\s+(?:chat|platform)|nsfw)\b", re.I)
N_SEL, N_RES = 80, 20
ARCHS = ['partytown', 'zaraz', 'gateway', 'wix', 'bigcommerce']
AD_VENDORS = {'google_ads', 'meta', 'tiktok', 'pinterest', 'snap', 'microsoft_uet', 'linkedin', 'x_twitter', 'reddit', 'criteo'}


def page_text(domain):
    p = os.path.join(RAW, 'pages', hashlib.sha1(domain.encode()).hexdigest()[:16] + '.html.gz')
    if not os.path.exists(p):
        return None
    b = gzip.open(p).read()
    return b.decode('utf-8', errors='replace')


def gateway_subtype(g, page_host):
    kinds = []
    for u in g['fp_tag_urls']:
        h = u[2:].split('/')[0] if u.startswith('//') else ''
        if not h or h == page_host:
            kinds.append('same_host_path')
        else:
            kinds.append('first_party_subdomain')
    if g['proxy_tag_urls']:
        kinds.append('third_party_tag_host')
    if g['custom_loader']:
        kinds.append('custom_loader')
    if g['sst_endpoints']:
        kinds.append('server_container_url')
    if g['capig']:
        kinds.append('meta_capi_gateway')
    if g.get('known_sst_host'):
        kinds.append('hosted_sgtm')
    return sorted(set(kinds))


def main():
    recs = {}
    for l in open(os.path.join(RAW, 'screen_results.jsonl')):
        r = json.loads(l)
        recs[r['domain']] = r
    rows, funnel = [], collections.Counter()
    for d, r in recs.items():
        st = r['stratum']
        if st == 'CAL':          # calibration pages on vendor-owned sites: never candidates
            continue
        funnel[(st, 'screened')] += 1
        if r.get('outcome') != 'ok':
            funnel[(st, 'out:' + str(r.get('outcome')))] += 1
            continue
        funnel[(st, 'ok')] += 1
        # re-analyse only records screened before the marker revision of 00:05 PDT 27 Sep (they lack the newer fields)
        text = page_text(d) if ('generic_banner_markup' not in r or os.environ.get('REANALYSE_ALL')) else None
        if text is not None:
            a = M.analyse(d, r.get('final_url', 'https://%s/' % r['fetch_host']), {'server': r.get('server', '')}, text)
            r.update(partytown=a['partytown'], zaraz=a['zaraz'], gateway=a['gateway'], cmps=a.get('cmps'), tcf=a.get('tcf'))  # prevalence uses current markers
        else:
            a = r      # no target marker at screening time: keep the stored fields
        arch = [x for x in ARCHS if (a[x]['platform'] if x in ('wix', 'bigcommerce') else a[x]['any'])]
        if not a['partytown']['any'] and a['partytown'].get('lib'):
            arch.insert(0, 'partytown')          # library present, no text/partytown script in the static HTML (tier L)
        if not arch:
            continue
        funnel[(st, 'any_arch')] += 1
        excl = []
        if a.get('adult_flag'):
            excl.append('adult')
        if a.get('child_flag_domain') or a.get('child_flag_text'):
            excl.append('child_directed')
        if a.get('shopify'):
            excl.append('shopify_storefront')
        if a.get('cross_site_redirect'):
            excl.append('redirects_to_other_site')
        if AGE_RESTRICTED.search(d) or AGE_RESTRICTED_TXT.search('%s %s' % (a.get('title') or '', a.get('description') or '')):
            excl.append('age_restricted')     # gambling / AI-roleplay sites: 18+ audiences, excluded like adult sites (27 Sep 03:30 PDT)
        cmps = a.get('cmps') or []
        has_cmp = bool(cmps) or bool(a.get('tcf'))
        tags_visible = sorted(set(a.get('vendors') or []))
        ad_visible = sorted(set(tags_visible) & (AD_VENDORS | {'google_tag'}))
        page_host = a.get('final_host') or r['fetch_host']
        for x in arch:
            if x == 'zaraz' and not has_cmp:
                tier = 'Z'
            elif x == 'partytown' and not a['partytown']['any']:
                tier = 'L' if has_cmp else 'U'
            elif not has_cmp:
                tier = 'U' if x in ('partytown', 'gateway') else None
            else:
                tier = 'A' if ad_visible else 'B'
            detail = ''
            if x == 'partytown':
                p = a['partytown']; detail = 'n_scripts=%d; vendors=%s; forward=%s' % (p['n_scripts'], '|'.join(p['vendors']), p['forward'][:80])
            elif x == 'zaraz':
                z = a['zaraz']; detail = 'paths=%s; custom_path=%s; gcm=%s' % ('|'.join(z['paths']), z['custom_path'], '|'.join(z['gcm']))
            elif x == 'gateway':
                g = a['gateway']; detail = 'subtype=%s; urls=%s; ids=%s' % ('|'.join(gateway_subtype(g, page_host)), '|'.join((g['fp_tag_urls'] + g['proxy_tag_urls'])[:3]), '|'.join(g['tag_ids'][:4]))
            elif x == 'wix':
                w = a['wix']; detail = 'native_banner_requires_consent=%s; site_policy=%s; gcm_bridge=%s' % (w.get('native_banner_requires_consent'), json.dumps(w.get('site_consent_policy'), separators=(',', ':')), w.get('gcm_bridge'))
            elif x == 'bigcommerce':
                b = a['bigcommerce']; detail = 'native_consent=%s; held_back_scripts=%s' % (b.get('consent_enabled'), json.dumps(b.get('consent_categories'), separators=(',', ':')))
            rows.append(dict(architecture=x, domain=d, tranco_rank=r['rank'], screen_stratum=st, in_random_stratum=int(st == 'R'),
                             homepage_url=r.get('final_url', ''), product_url=(a.get('product_url') or '') if x in ('wix', 'bigcommerce') else '',
                             product_robots=r.get('product_robots', ''), measure_url='', tier=tier or '', eligible=int(not excl and tier is not None),
                             exclusion='|'.join(excl) if excl else ('no_static_cmp' if tier is None else ''),
                             cmps='|'.join(cmps), tcf=int(bool(a.get('tcf'))), gcm_default=int(bool(a.get('gcm_default'))),
                             tags_visible='|'.join(tags_visible), other_architectures='|'.join(y for y in arch if y != x),
                             arch_detail=detail, lang=a.get('lang', ''), title=(a.get('title') or '')[:90], screened_utc=r.get('ts_utc', ''),
                             selection='', selection_order=''))
    # measurement URL: product page for stores when found and allowed, else the homepage
    for row in rows:
        if row['product_url'] and row['product_robots'] in ('robots_allowed', 'robots_4xx_allow'):
            row['measure_url'] = row['product_url']
        else:
            row['measure_url'] = row['homepage_url']
    # seeded selection per architecture (a site is selected for at most one architecture: the rarest first)
    taken = set()
    counts = {}
    for x in ARCHS:
        for row in rows:
            if row['architecture'] == x and row['eligible'] and row['tier'] == 'U':
                row['selection'] = 'backup_unconfirmed_cmp'
        el = sorted([row for row in rows if row['architecture'] == x and row['eligible'] and row['tier'] != 'U'], key=lambda z: z['domain'])
        el.sort(key=lambda z: {'A': 0, 'B': 1, 'L': 2, 'Z': 2}[z['tier']])   # tier A first, then B, then L/Z
        rnd = random.Random(SEED + ARCHS.index(x))
        groups = collections.OrderedDict()
        for row in el:
            groups.setdefault(row['tier'], []).append(row)
        order = []
        for t, g in groups.items():
            rnd.shuffle(g); order += g
        k = 0
        for row in order:
            if row['domain'] in taken:
                row['selection'] = 'selected_for_other_architecture'
                continue
            k += 1
            row['selection_order'] = k
            row['selection'] = 'selected' if k <= N_SEL else ('reserve' if k <= N_SEL + N_RES else 'not_needed')
            if k <= N_SEL + N_RES:
                taken.add(row['domain'])
        counts[x] = dict(eligible=len(el), selected=sum(1 for r_ in order if r_['selection'] == 'selected'),
                         reserve=sum(1 for r_ in order if r_['selection'] == 'reserve'),
                         tiers=dict(collections.Counter(r_['tier'] for r_ in el)),
                         backup_unconfirmed_cmp=sum(1 for r_ in rows if r_['architecture'] == x and r_['selection'] == 'backup_unconfirmed_cmp'),
                         candidates_any=sum(1 for r_ in rows if r_['architecture'] == x))
    for row in rows:
        if not row['eligible']:
            row['selection'] = 'excluded'
    rows.sort(key=lambda z: (ARCHS.index(z['architecture']), {'selected': 0, 'reserve': 1, 'not_needed': 2, 'backup_unconfirmed_cmp': 3, 'selected_for_other_architecture': 4, 'excluded': 5}[z['selection']],
                             z['selection_order'] if z['selection_order'] != '' else 9999, int(z['tranco_rank'])))
    fields = list(rows[0].keys()) if rows else []
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fields); w.writeheader(); w.writerows(rows)
    # prevalence in the random stratum R (screened, HTTP 200 inspectable)
    R_ok = [recs[d] for d in recs if recs[d]['stratum'] == 'R' and recs[d].get('outcome') == 'ok']
    def prev(pred):
        k = sum(1 for r in R_ok if pred(r)); n = len(R_ok)
        return dict(k=k, n=n, share=(k / n if n else None))
    summary = dict(funnel={'%s|%s' % k: v for k, v in sorted(funnel.items())}, per_architecture=counts,
                   random_stratum_prevalence=dict(
                       partytown=prev(lambda r: r['partytown']['any']), zaraz=prev(lambda r: r['zaraz']['any']),
                       gateway=prev(lambda r: r['gateway']['any']), static_cmp=prev(lambda r: bool(r.get('cmps')) or r.get('tcf'))),
                   note='prevalence over R-stratum HTTP-200 pages; saved (marker) pages re-analysed with the current markers.py, other pages keep the stored fields (no marker at screening time)')
    json.dump(summary, open(os.path.join(RAW, 'screen_summary.json'), 'w'), indent=1)
    print(json.dumps(summary['per_architecture'], indent=1))
    print(json.dumps(summary['random_stratum_prevalence']))


if __name__ == '__main__':
    main()
