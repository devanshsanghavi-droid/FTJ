#!/usr/bin/env python3
"""make_ga_numbers.py -- every number in the graphical abstract and its caption, read from analysis outputs.

Spec: ../../FIGURE_PLAN_v2.md section 5 (graphical abstract, optional, Elsevier).
Reads   analysis/outputs/stats.json and figures/v7/derived_numbers.json (through figstyle.N / KN / CI, which register
        every rendered number) and figures/v7/fig4/derived_numbers.json (tile B's clustered CI, registered here with
        source 'fig4_derived', exactly as fig4/scripts/make_caption_fig4.py does).
Writes  (all next to this script's parent directory, figures/v7/graphical_abstract/)
    ga_numbers.tex                  macros used by panels/ga_tiles.tex (hero numbers, k, n, meter shares)
    ga_numbers.csv                  registry: text, shown, source, key, fmt, value of every rendered number
    derived_numbers.json            the two derived values (meter shares of tiles B and C), with script and inputs
    caption_graphical_abstract.tex  the caption, numbers filled in from the same registry
Nothing is typed by hand: re-run after analysis/run_all.sh and rebuild with ../build.sh.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GA = os.path.dirname(HERE)                                  # figures/v7/graphical_abstract
V2 = os.path.dirname(GA)                                    # figures/v2
sys.path.insert(0, os.path.join(V2, 'style'))
import figstyle as fs  # noqa: E402

REL_SCRIPT = 'figures/v7/graphical_abstract/scripts/make_ga_numbers.py'

# the three stat tiles (FIGURE_PLAN_v2.md section 5), top to bottom
TILE_A = 'fig1b/banner_fires'                # stores with a banner: sandboxed ad pixel before any choice
# Tile B is the Fig 4A hero (QA fix, 2026-09-26): blocklist ENTRIES (one ad vendor listed as blocked on one store) on the
# stores whose CMP wrote no 'yes', counted as in Fig 4A's top row: fired from Shopify's sandbox before any choice.
# (Was stats fig4/a/blocklist/primary/fired = 7 of 14 STORES, which appears only in Fig S7A.)
TILE_B = 'fig4a_routes/primary_no_yes'       # figures/v7/derived_numbers.json (source='derived')
TILE_B_KG = 'fig4a_kg/sandbox'               # figures/v7/fig4/derived_numbers.json: Korn-Graubard CI by store
TILE_C = 'fig5/d/deny'                       # automatic 'no' writes: pixel sandboxes started before the write
# Tile C's unit word is "sandboxes" (panels/ga_tiles.tex), as in Fig 1 badge 3, Fig 5C and the caption below
# (cross-figure QA, 2026-09-26; was "pixels").


FIG4_DERIVED = os.path.join(V2, 'fig4', 'derived_numbers.json')
_D4 = json.load(open(FIG4_DERIVED))


def d4(key):
    """Value at a '/'-separated key of figures/v7/fig4/derived_numbers.json (the record's 'value' level implied)."""
    name, _, rest = key.partition('/')
    return fs._walk(_D4[name]['value'], rest) if rest else _D4[name]['value']


def N4(key, f='int'):
    """Render a fig4/derived_numbers.json number and register it (source 'fig4_derived', as in make_caption_fig4.py)."""
    v = d4(key)
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig4_derived', key=key, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def tex_escape(s):
    return s.replace('%', r'\%')


def derive_blocked_share():
    """Share of the Fig 4A blocklist entries whose vendor fired from Shopify's sandbox before any choice (meter length
    only; derived_numbers.json stores the counts, fig4/derived_numbers.json the same share with its CI)."""
    k = fs.derived(TILE_B + '/sandbox')
    n = fs.derived(TILE_B + '/n')
    return dict(value=k / n, k=k, n=n)


def derive_race_share():
    """Share of marketing pixel sandboxes that had started before the CMP's automatic 'no' (meter length only;
    stats.json stores the counts but no share)."""
    k = fs.stat(TILE_C + '/pixels_before')
    n = fs.stat(TILE_C + '/pixels')
    return dict(value=k / n, k=k, n=n)


def main():
    fs.reset_registry()
    race = derive_race_share()
    blocked = derive_blocked_share()
    # tile B must be the very counts Fig 4A prints (fig4/derived_numbers.json is built from the same entries)
    assert d4('fig4a_entries/counts/sandbox') == blocked['k'] and d4('fig4a_entries/counts/n') == blocked['n']
    assert d4(TILE_B_KG + '/k') == blocked['k'] and d4(TILE_B_KG + '/n') == blocked['n']
    assert d4('fig4a_entries/counts/n_stores') == fs.derived(TILE_B + '/n_stores')

    # ---------------------------------------------------------------- derived_numbers.json
    derived = {
        'ga_blocked_share': {
            'value': blocked['value'],
            'definition': "Tile B meter length: blocklist entries (an ad vendor that the store's CMP listed as blocked "
                          "and that had a configured sandboxed Shopify pixel, on the stores whose CMP wrote no "
                          "'marketing: yes') whose vendor sent an ad request from Shopify's sandbox before any choice, "
                          "as a share of all such entries (k / n; Fig 4A top row). Drawn only; the printed numbers "
                          "are k and n.",
            'script': REL_SCRIPT,
            'inputs': ['figures/v7/derived_numbers.json:fig4a_routes.primary_no_yes.sandbox',
                       'figures/v7/derived_numbers.json:fig4a_routes.primary_no_yes.n'],
            'k': blocked['k'], 'n': blocked['n'],
            'check': 'k, n == fig4/derived_numbers.json fig4a_entries.counts (sandbox, n) and fig4a_kg.sandbox (k, n)',
        },
        'ga_race_share': {
            'value': race['value'],
            'definition': "Tile C meter length: marketing pixel sandboxes that had started before the CMP's "
                          "automatic 'marketing: no' write, as a share of all such sandboxes (k / n). Drawn only; "
                          "the printed numbers are k and n.",
            'script': REL_SCRIPT,
            'inputs': ['analysis/outputs/stats.json:fig5.d.deny.pixels_before',
                       'analysis/outputs/stats.json:fig5.d.deny.pixels'],
            'k': race['k'], 'n': race['n'],
            'check': 'k == stats fig5.d.deny.pixels_before and n == stats fig5.d.deny.pixels',
        },
    }
    assert derived['ga_race_share']['k'] == fs.stat(TILE_C + '/pixels_before')
    assert abs(derived['ga_race_share']['value'] - fs.stat(TILE_C + '/pixels_before') / fs.stat(TILE_C + '/pixels')) < 1e-12
    with open(os.path.join(GA, 'derived_numbers.json'), 'w') as fh:
        json.dump(derived, fh, indent=1)
        fh.write('\n')

    # ---------------------------------------------------------------- tile numbers (registered)
    heroA = fs.N(TILE_A + '/p', 'pct0') + '%'
    kA, nA = fs.N(TILE_A + '/k'), fs.N(TILE_A + '/n')
    kB, nB = fs.N(TILE_B + '/sandbox', source='derived'), fs.N(TILE_B + '/n', source='derived')
    kC, nC = fs.N(TILE_C + '/pixels_before'), fs.N(TILE_C + '/pixels')
    fracA = fs.stat(TILE_A + '/p')
    fracB = derived['ga_blocked_share']['value']
    fracC = derived['ga_race_share']['value']
    # the meter shares must equal k / n of the printed counts
    assert abs(fracA - fs.stat(TILE_A + '/k') / fs.stat(TILE_A + '/n')) < 1e-12
    assert abs(fracB - fs.derived(TILE_B + '/sandbox') / fs.derived(TILE_B + '/n')) < 1e-12

    L = ['% ga_numbers.tex -- GENERATED by scripts/make_ga_numbers.py from analysis/outputs/stats.json and',
         '% derived_numbers.json; do not edit. Registry of every rendered number: ga_numbers.csv.',
         r'\newcommand{\gaHeroA}{%s}' % tex_escape(heroA),
         r'\newcommand{\gaHeroB}{%s of %s}' % (kB, nB),
         r'\newcommand{\gaHeroC}{%s of %s}' % (kC, nC),
         '% meter shares (drawn, not printed): stats.json p for A; derived_numbers.json ga_blocked_share for B and',
         '% ga_race_share for C',
         r'\newcommand{\gaFracA}{%.6f}' % fracA,
         r'\newcommand{\gaFracB}{%.6f}' % fracB,
         r'\newcommand{\gaFracC}{%.6f}' % fracC]
    with open(os.path.join(GA, 'ga_numbers.tex'), 'w') as fh:
        fh.write('\n'.join(L) + '\n')

    # ---------------------------------------------------------------- caption (skill caption guidelines)
    n_main = fs.N('design/n_main')
    tranco = fs.N('design/tranco_top_n')
    ciA = fs.CI(TILE_A)
    pA = fs.N(TILE_A + '/p', 'pct1')
    kA2, nA2 = fs.N(TILE_A + '/k'), fs.N(TILE_A + '/n')
    kB2, nB2 = fs.N(TILE_B + '/sandbox', source='derived'), fs.N(TILE_B + '/n', source='derived')
    storesB = fs.N(TILE_B + '/n_stores', source='derived')
    ciB = N4(TILE_B_KG + '/kg_lo', 'pct1') + '--' + N4(TILE_B_KG + '/kg_hi', 'pct1')
    loadsC = fs.N(TILE_C + '/loads')
    kC2, nC2 = fs.N(TILE_C + '/pixels_before'), fs.N(TILE_C + '/pixels')
    lagC = fs.N(TILE_C + '/median_lag_first_ms', 'int')
    lagC = lagC.lstrip(fs.MINUS)            # "648 ms before": the sign is carried by the word "before"
    assert fs.stat(TILE_C + '/median_lag_first_ms') < 0

    cap = (
        r"\textbf{Cookie-banner blockers cannot see Shopify's sandboxed ad pixels, so the pixels send data before, "
        r"and despite, the visitor's choice.} "
        r"(Left) On Shopify stores, ad pixels run in sandboxes of Shopify's Web Pixels Manager (hatched box: a web "
        r"worker or a sandboxed iframe) and send requests to the ad vendor's servers. The cookie banner of a "
        r"consent-management platform (CMP) and its script blocker act only in the page, so the blocker's reach stops "
        r"short of the sandbox (red bar: the blind spot). The only gate before the sandbox is Shopify's consent state "
        r"(diamond), which is set by Shopify's region default and by what the CMP writes to it. "
        r"(Right) Three results from %s popular Shopify stores in the Tranco top %s, loaded from California. "
        r"Top: on %s of %s stores that showed a banner (%s\%%; Wilson 95\%% confidence interval (CI) %s\%%), a "
        r"sandboxed ad pixel sent a request before any choice. "
        r"Middle: of %s blocklist entries (an ad vendor that the store's CMP listed as blocked and that had a "
        r"configured sandboxed Shopify pixel) on the %s stores whose CMP wrote no `marketing: yes' to Shopify, in %s the "
        r"vendor sent an ad request from Shopify's sandbox before any choice (95\%% CI clustered by store, Korn--Graubard, "
        r"%s\%%). "
        r"Bottom: in %s page loads in which the CMP wrote `marketing: no' to Shopify without a click (the `no'), %s of "
        r"%s third-party pixel sandboxes that declare `marketing' had already started (median %s ms before the write). "
        r"Bars: each count as a share of its total; red, consent failed; outlined light grey, the rest."
    ) % (n_main, tranco, kA2, nA2, pA, ciA.replace(fs.EN_DASH, '--'), nB2, storesB, kB2, ciB, loadsC, kC2, nC2,
         lagC)
    head = ('% caption_graphical_abstract.tex -- GENERATED by scripts/make_ga_numbers.py; numbers from '
            'analysis/outputs/stats.json, figures/v7/derived_numbers.json and fig4/derived_numbers.json (registry: '
            'ga_numbers.csv). Do not edit by hand.\n')
    with open(os.path.join(GA, 'caption_graphical_abstract.tex'), 'w') as fh:
        fh.write(head + cap + '\n')

    fs.write_registry(os.path.join(GA, 'ga_numbers.csv'))
    print('wrote ga_numbers.tex, ga_numbers.csv, derived_numbers.json, caption_graphical_abstract.tex in', GA)


if __name__ == '__main__':
    main()
