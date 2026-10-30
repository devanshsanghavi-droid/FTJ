"""Write caption_fig3.tex (LaTeX \\caption + \\label for Figure 3, v7) and alt_text_fig3.txt, with every number rendered
from analysis/outputs/stats.json, figures/v7/derived_numbers.json or fig3/derived_numbers.json through the figstyle
registry (caption_fig3_numbers.csv), so neither carries a typed number.

v7 (../../DESIGN_V7.md section 10): the panels print no values (numbers live in the caption, the plots show them by
position), so the caption carries every product's counts under the two defaults, the all-store shares, both
differences and b's shares, and names every v7 encoding once: brick circles = 'allowed until choice', slate squares =
'denied until consent' (the summary row of a carries them as direct labels; b, which has none, is reminded of them);
grey = a group of fewer than design.min_stores_row stores (the grey groups are listed from the data; a muted note in
the plot says so too); the pale brick band = the excess under 'allowed until choice' (the key area), drawn between the
two marks of a row where both groups are coloured; a, right, shares the rows and the scale of a, left, and draws each
difference as a dot + CI (section 8.1; no bars) against a grey zero line on an axis from -20: open diamond = all
banner stores (crude, direct label 'Crude'), filled diamond = pooled within product (MH, direct label 'Within
product', level with the middle of the product rows, which a grey bracket groups). v7 moved the summary row 'All
banner stores' below the products (section 8.1); v7 r1 (critics) dropped a, right's bars and its spine-as-zero.

Caption rules: bold one-sentence takeaway title; lowercase panel descriptions '(a)~'; abbreviations defined at first
use; n, unit, interval type and level for every panel; every encoding named.
Run:  python3 figures/v7/fig3/scripts/make_caption_fig3.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG3 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG3, '..', 'style')))
sys.path.insert(0, HERE)
import figstyle as fs  # noqa: E402
import make_fig3_panels as P  # noqa: E402  (N3: the fig3-local derived numbers; the panel encodings)

N, KN, N3 = fs.N, fs.KN, P.N3
S3 = 'fig3a_strata'


def pct(key):
    """'70.2\\%' from a stats {p} record."""
    return N(key + '/p', 'pct1') + r'\%'


def none_or(key):
    """'none' when the (derived) count is 0, else the registered number."""
    return 'none' if fs.derived(key) == 0 else N(key, source='derived')


def tex(s):
    """Typographic minus / en dash from figstyle -> LaTeX."""
    return s.replace(fs.MINUS, '$-$').replace(fs.EN_DASH, '--')


def counts(c):
    """'Pandectes 40/49 and 18/44': stores that fired / stores under 'allowed', then under 'denied'."""
    r = f'{S3}/rows/{c}'
    return (P.CMP_NAME[c].replace('’', "'") + ' ' + N3(r + '/allowed/k') + '/' + N3(r + '/allowed/n') + ' and '
            + N3(r + '/denied/k') + '/' + N3(r + '/denied/n'))


def grey_groups():
    """'Cookiebot's `denied' group and both of Osano's' -- the groups drawn grey in a, left (from the data)."""
    by = {}
    for c, g in P.small_groups():
        by.setdefault(c, []).append(g)
    parts = []
    for c, gs in by.items():
        name = P.CMP_NAME[c].replace('’', "'")
        parts.append(f"both of {name}'s" if len(gs) == 2 else f"{name}'s `{gs[0]}' group")
    return ' and '.join([', '.join(parts[:-1]), parts[-1]] if len(parts) > 1 else parts)


def main():
    fs.reset_registry()
    al, de = 'fig3/d/opt_out', 'fig3/d/opt_in'
    mh = 'fig3/d/mh_by_product'
    cr = mh + '/crude'
    part = 'banner_default_partition/unreadable'
    g = 'fig3/d/opt_in_mkt_fired_after_cmp_grant'
    order = P._D3_value(S3 + '/order')
    min_n = P._D3_value(S3 + '/min_cell_n')
    rows = P._D3_value(S3 + '/rows')
    sparse = [c for c in order if min(rows[c]['allowed']['n'], rows[c]['denied']['n']) < min_n]
    full = [c for c in order if c not in sparse]
    few = fs.stat('design/min_stores_row')
    grey = P.small_groups()
    all_grey = [c for c in full if all((c, x) in grey for x in ('allowed', 'denied'))]
    banded = [c for c in full if not any((c, x) in grey for x in ('allowed', 'denied'))]
    # what the caption and alt text assert about the plot
    assert all(rows[c]['allowed']['p'] > rows[c]['denied']['p'] for c in full)
    assert len(full) == P._D3_value(S3 + '/n_full') and len(sparse) == P._D3_value(S3 + '/n_sparse')
    assert len(full) + len(sparse) == fs.stat(mh + '/n_strata') and full == order[:len(full)]
    assert fs.stat(cr + '/diff_lo') > 0 and fs.stat(mh + '/rd_lo') > 0
    assert all(fs.stat(f'{de}/{m}/p') < fs.stat(f'{al}/{m}/p') for m, _ in P.PURPOSES)
    assert fs.stat(f'{al}/any_sbx/n') + fs.stat(f'{de}/any_sbx/n') == P._D3_value(S3 + '/n_readable')
    assert grey and all_grey and banded and min(fs.stat(f'{x}/any_sbx/n') for x in (al, de)) >= few
    assert all(min(fs.stat(f'{x}/{m}/n') for x in (al, de)) >= few for m, _ in P.PURPOSES)   # b: no grey group

    title = (r"\textbf{Before any choice, whether sandboxed pixels fire tracks Shopify's region default, even within "
             r"the same consent tool.}")
    a = (r"(a)~Left: share of banner stores on which an ad pixel running in a Shopify sandbox sent a request before "
         r"any choice, by Shopify's region default at our California vantage point: `allowed until choice' (brick "
         r"circles, just above each row's centre line) and `denied until consent' (slate squares, just below it). Rows: "
         f"the {N3(S3 + '/n_full')} consent-management platform (CMP) products with at least {N('design/min_cell_n')} "
         f"stores under each default, in order of their Mantel--Haenszel (MH) weight; stores that fired / stores, "
         f"`allowed' then `denied': " + '; '.join(counts(c) for c in full) + r". Bottom row, set apart: all "
         f"{N3(S3 + '/n_readable')} banner stores with a readable default, {KN(al + '/any_sbx')} "
         f"({pct(al + '/any_sbx')}; 95\\% confidence interval (CI) {N(al + '/any_sbx/lo', 'pct1')}--"
         f"{N(al + '/any_sbx/hi', 'pct1')}\\%) against {KN(de + '/any_sbx')} ({pct(de + '/any_sbx')}; "
         f"{N(de + '/any_sbx/lo', 'pct1')}--{N(de + '/any_sbx/hi', 'pct1')}\\%). A "
         f"group of fewer than {N('design/min_stores_row')} stores is drawn grey, as the note in the plot says "
         f"({grey_groups()}; a row with no coloured group has its name in grey). Pale brick band: the excess under "
         r"`allowed until choice', from the `denied' share to the `allowed' share, drawn where both groups are "
         r"coloured. Right, on the same rows and the same scale: the difference, `allowed' minus `denied', in percentage points (pp), with its 95\% CI "
         r"(horizontal line), against a grey zero line: pooled within product by the MH method with Sato's variance "
         r"(filled diamond, `Within product', level with the middle of the product rows, which a grey bracket "
         f"groups) +{N(mh + '/rd', 'pct1')}~pp ({N(mh + '/rd_lo', 'pct1')}--{N(mh + '/rd_hi', 'pct1')}), and over "
         r"all banner stores (open diamond, `Crude', on their row; Newcombe's interval) "
         f"+{N(cr + '/diff', 'pct1')}~pp ({N(cr + '/diff_lo', 'pct1')}--{N(cr + '/diff_hi', 'pct1')}). The pooled "
         r"difference uses all "
         f"{N(mh + '/n_strata')} CMP products with stores under both defaults ({N3(S3 + '/n_strata_stores')} stores; "
         f"the other {N3(S3 + '/n_other')} use a product seen under one default only, or none); the "
         f"{N3(S3 + '/n_full')} drawn on the left carry {N3(S3 + '/w_share_full', 'pct0')}\\% of its weight. The "
         f"other {N3(S3 + '/n_sparse')}, with fewer than {N('design/min_cell_n')} stores under one default, are not "
         f"drawn: " + '; '.join(counts(c) for c in sparse) + f". The {N(part + '/n', source='derived')} banner "
         f"stores without a readable default are not shown; {none_or(part + '/fired')} of them fired.")
    b = (r"(b)~The same measure, counting only the pixels that declare a given purpose, with the markers of (a) "
         r"(brick circles `allowed until choice', slate squares `denied until consent'), its intervals and pale brick "
         r"bands, and the same scale: `marketing' "
         f"{KN(al + '/mkt_sbx')} ({pct(al + '/mkt_sbx')}) against {KN(de + '/mkt_sbx')} ({pct(de + '/mkt_sbx')}); "
         f"not `marketing' {KN(al + '/nomkt_sbx')} ({pct(al + '/nomkt_sbx')}) against {KN(de + '/nomkt_sbx')} "
         f"({pct(de + '/nomkt_sbx')}); no purpose at all (a subset of not `marketing') "
         f"{KN(al + '/nopurpose_sbx')} ({pct(al + '/nopurpose_sbx')}) against {KN(de + '/nopurpose_sbx')} "
         f"({pct(de + '/nopurpose_sbx')}). A store can count under more than one purpose. On "
         f"{KN(g, sep=' of the ')} `denied' stores with a firing `marketing' pixel, the CMP had first told Shopify "
         r"`yes' without a click.")
    tail = (r"Lines through the circles and squares: Wilson 95\% CIs, each in the colour of its mark (stores are the "
            r"unit). All three plots share one scale (the same length per percentage point). Default load (no "
            f"interaction); main sample {N('design/n_main')} stores, {N('fig1b/banner/k')} with a banner. Per-vendor "
            r"rates, the timing of the first sandboxed request, request origins and per-product shares: Fig.~S6.")
    body = ' '.join([title, a, b, tail])
    out = ['% caption_fig3.tex -- GENERATED by scripts/make_caption_fig3.py; every number is rendered from',
           '% analysis/outputs/stats.json, figures/v7/derived_numbers.json or fig3/derived_numbers.json',
           '% (registry: caption_fig3_numbers.csv). Do not edit numbers by hand; edit the script and re-run.',
           r'\caption{' + tex(body) + '}',
           r'\label{fig:region-default}', '']
    open(os.path.join(FIG3, 'caption_fig3.tex'), 'w').write('\n'.join(out))

    # Alt text (chart type, variables, main pattern, key numbers); same registry as the caption.
    p0 = lambda key: N(key + '/p', 'pct0') + '%'        # noqa: E731
    names = ', '.join(P.CMP_NAME[c] for c in full)
    alt = (f"Two-panel figure. (a) Left: dot plot with 95% confidence intervals, one row per consent-management "
           f"product with enough stores under both of Shopify's region defaults ({names}), then a summary row for all "
           f"banner stores. In every row the share of stores whose sandboxed ad pixel sent a request before any choice "
           f"is higher under 'allowed until choice' (brick circles) than under 'denied until consent' (slate "
           f"squares): over all banner stores {p0(al + '/any_sbx')} against {p0(de + '/any_sbx')}. Groups of fewer "
           f"than {N('design/min_stores_row')} stores are grey, as a note in the plot says; a pale brick band spans the "
           f"gap in each row whose groups are both coloured. Right, on the same rows and scale: the difference, "
           f"'allowed' minus 'denied', as a diamond with its interval against a grey zero line, "
           f"+{N(mh + '/rd', 'pct1')} percentage points pooled within the {N(mh + '/n_strata')} products (labelled "
           f"'Within product', level with the middle of the product rows, which a grey bracket groups) and "
           f"+{N(cr + '/diff', 'pct1')} over all banner stores (labelled 'Crude', on their row), both intervals well "
           f"above zero. (b) Paired dot plot of the same measure by the purpose the firing pixel "
           f"declares, same markers and bands: 'marketing' {p0(al + '/mkt_sbx')} against {p0(de + '/mkt_sbx')}; not "
           f"'marketing' {p0(al + '/nomkt_sbx')} against {p0(de + '/nomkt_sbx')}; no purpose at all "
           f"{p0(al + '/nopurpose_sbx')} against {p0(de + '/nopurpose_sbx')}.")
    open(os.path.join(FIG3, 'alt_text_fig3.txt'), 'w').write(alt.replace(fs.MINUS, '-') + '\n')
    fs.write_registry(os.path.join(FIG3, 'caption_fig3_numbers.csv'))
    words = len(body.split())
    print(f'wrote caption_fig3.tex ({words} words), alt_text_fig3.txt and caption_fig3_numbers.csv')


if __name__ == '__main__':
    main()
