"""Write caption_fig6.tex (LaTeX \\caption + \\label for Figure 6, v7) and alt_text_fig6.txt, with every number rendered
from analysis/outputs/stats.json or fig6/derived_numbers.json through the figstyle registry (caption_fig6_numbers.csv),
so neither carries a typed number.

v7 (../../DESIGN_V7.md section 10): the panels print no values (the plot shows them by position), so the caption carries
a's per-load counts (TikTok's sandboxed requests, the vendors that got the code and how), b's three shares, c's seven
vendor shares and the all-vendor share with k of n, d's six agreement shares with k of n -- and names every v7 encoding
once: a's line drawing (the browser outline; the page and sandbox grounds of Fig. 1a; brick arrows = the code leaving
the sandboxes, consent lost; the grey arrow = other routes; the vendors named at the heads of their paths; the code's
placeholder 'utm_campaign=desc-...', the same form as the drawing's), a's two groups of loads and the light line joining
a load's two counts, brick circles = from a sandbox and grey squares = by any route (a and b), dark grey circles in c
and d, c's summary row and the pale brick band of its CI, d's truncated axis and its break mark.
Panel contents are v5's (the paper cites a-d): (a) Store C, the creator-link case; (b) the creator-linked stores;
(c) full landing URL by vendor; (d) validation agreement.

Caption rules: bold one-sentence claim as the title; lowercase panel descriptions '(a)~'; abbreviations defined at first
use; n, unit, interval type and level for every panel; every encoding named once.
Run:  PATH=/opt/anaconda3/bin:$PATH python3 figures/v7/fig6/scripts/make_caption_fig6.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG6 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG6, '..', 'style')))
sys.path.insert(0, HERE)
import figstyle as fs  # noqa: E402
import make_fig6_panels as P  # noqa: E402  (DN: fig6-local derived numbers; the panels' row lists)


def tex(s):
    """Plain-text number conventions -> LaTeX: typographic minus -> $-$, en dash -> --, % -> \\%."""
    return s.replace(fs.MINUS, '$-$').replace(fs.EN_DASH, '--').replace('%', '\\%')


def N(key, f='int'):
    return tex(fs.N(key, f))


def KN(key):
    return tex(fs.KN(key))


def DN(key, f='int'):
    return tex(P.DN(key, f))


def pct(key):
    return N(key + '/p', 'pct1') + r'\%'


def ci(key, lo='lo', hi='hi'):
    return N(f'{key}/{lo}', 'pct1') + '--' + N(f'{key}/{hi}', 'pct1') + r'\%'


def share(key, unit=''):
    """A share as 'p\\% (k of n)'."""
    return f"{pct(key)} ({KN(key)}{unit})"


def main():
    fs.reset_registry()
    # ---- a: Store C, per load (derived grid; the same counts the plot draws, asserted equal to stats.json there)
    g = 'fig6a_store_c_grid'
    grid = P._dv(g)
    m = P._dv('fig6a_store_c_vendors')
    pre, post = ('A0', 'A0r', 'A1pre'), ('A1after', 'A2', 'A2r')
    for f in ('tiktok_sbx_code', 'vendors_code', 'vendors_code_sbx'):        # one sentence per group must hold
        assert len({grid[c][f] for c in pre}) == 1, f
        assert len({grid[c][f] for c in ('A2', 'A2r')}) == 1, f
    assert all(grid[c]['vendors_code_sbx'] == 0 and grid[c]['tiktok_sbx_code'] == 0 for c in post)
    sbx_vendors = {c: [v for v, r in zip(m['vendors'], m['routes'][c]) if r == 2] for c in pre}
    assert all(sorted(s) == ['google_ads', 'tiktok'] for s in sbx_vendors.values()), sbx_vendors
    assert m['vendors'][:3] == ['google_ads', 'google_merchant_center', 'tiktok'] and \
        set(m['groups'][3:]) == {'Reddit/other'}                              # the caption names them in this way
    assert fs.stat('fig6/b/store_c/A0/n_creator_token_tiktok_sbx') == grid['A0']['tiktok_sbx_code']
    b = 'fig6/b'
    ref = P.C_REF
    ag = 'fig6d_agreement'
    s4 = 'supp/S4'

    title = (r"\textbf{Ad vendors receive the landing URL, including a creator's per-video code, and the measurements "
             r"behind this repeat across loads and agree with a screenshot audit.}")
    a = (r"(a)~Store~C, a creator-linked store, loaded from a creator's video link whose uniform resource locator (URL) "
         r"carries a per-video code (`utm\_campaign=desc-\ldots', the video's identifier elided here and in the "
         r"drawing). Left: "
         r"the code's path, on the regions of Fig.~\ref{fig:situating}a (outline: the browser; light grey ground: the "
         r"page's main thread; darker grey ground: the pixel sandboxes). The landing page hands its URL to the pixels "
         r"that Shopify runs in sandboxes isolated from the page, TikTok's pixel in a web worker (strict runtime) and "
         r"Google Ads' pixel in a sandboxed iframe (lax runtime), and they send the code to the ad vendors outside the "
         r"browser (brick arrows); scripts outside the sandboxes can send it as well (grey arrow: other routes). The "
         r"ad vendors that received the code in the Default load are named at the heads of the paths that reached "
         r"them. Right: one row per load of Store~C, in two groups. "
         r"Before any choice: Default, its repeat, and a Decline load before the click on the banner's reject button; "
         r"after a refusal: the same Decline load after the click (the rest of that page and the fresh page after the "
         r"reload), a Global Privacy Control (GPC) load and its repeat (GPC refuses from the start). Brick circles: ad "
         r"vendors that received the code from a sandbox; grey squares: ad vendors that received it by any route; a "
         r"light line joins the two counts of a load. In each of the three loads before any choice the code reached "
         f"{DN(g + '/A0/vendors_code')} ad vendors (Google Ads, Google Merchant Center, TikTok and vendors in the "
         f"Reddit/other group), {DN(g + '/A0/vendors_code_sbx')} of them, TikTok and Google Ads, from a sandbox; "
         f"TikTok's sandboxed pixel sent it in {DN(g + '/A0/tiktok_sbx_code')} requests per load. After the Decline "
         f"click it still reached {DN(g + '/A1after/vendors_code')} vendors and under GPC "
         f"{DN(g + '/A2/vendors_code')}, {DN(g + '/A1after/vendors_code_sbx')} of them from a sandbox, with "
         f"{DN(g + '/A1after/tiktok_sbx_code')} requests from TikTok's sandbox.")
    bb = (f"(b)~All {N(b + '/creator_stores')} creator-linked stores, Default load: share of stores on which the "
          r"creator's code reached any ad vendor, "
          f"{share(b + '/creator_token_reached_ad_vendor_A0')}, a vendor other than Google, "
          f"{share(b + '/creator_token_reached_nongoogle_A0')}, and an ad vendor from a sandbox, "
          f"{share(b + '/creator_token_reached_sandboxed_A0')}; Wilson 95\\% confidence intervals (CIs) "
          f"{ci(b + '/creator_token_reached_ad_vendor_A0')}, {ci(b + '/creator_token_reached_nongoogle_A0')} and "
          f"{ci(b + '/creator_token_reached_sandboxed_A0')} (horizontal lines). Marks as in (a): grey squares, by any "
          r"route; brick circle, from a sandbox.")
    rows = P.c_rows()
    vk = {v: f"fig6/a/{v.replace('/', '~1')}/Default" for v in rows}
    meta = vk['Meta']
    vend = '; '.join(f"{v} {pct(vk[v])} ({KN(vk[v])}{' beacons' if i == 0 else ''})" for i, v in enumerate(rows))
    c = (r"(c)~Sandboxed ad beacons in the Default load that carried the full landing URL with our test code, by "
         r"vendor group in a fixed order (dark grey circles; lines: Korn--Graubard 95\% CIs clustered by store): "
         f"{vend}. Groups with fewer than {N('design/min_stores_row')} stores would be omitted; the "
         f"smallest shown, Meta, has {N(meta + '/n')} beacons on {N(meta + '/n_stores')} stores. Bottom row, set apart: "
         f"all vendors, {pct(ref)} of {N(ref + '/n')} beacons on {N(ref + '/n_stores')} stores (95\\% CI "
         f"{ci(ref)}, resampling stores); this interval is carried up through the vendor rows as a pale brick band "
         r"(as the main estimates in Fig.~S5; these beacons left a sandbox before any choice), so each vendor group "
         r"reads against all vendors.")
    d = (r"(d)~Robustness (dark grey circles; lines: Wilson 95\% CIs), in two named groups. The agreement axis is "
         r"truncated (it does not start at zero; the break mark at its left end shows the cut); every interval ends "
         r"right of the break. "
         r"Between loads: agreement between two loads of the same store on whether a sandboxed ad pixel sent a "
         r"request, for the validation loads, that is, repeats of Default and GPC "
         f"({DN(ag + '/A0_vs_A0r/n')} stores) and Brave's native GPC ({DN(ag + '/A2_vs_V1/n')} stores): Default vs "
         f"repeat {DN(ag + '/A0_vs_A0r/p', 'pct1')}\\% ({DN(ag + '/A0_vs_A0r/k')} of {DN(ag + '/A0_vs_A0r/n')}; "
         f"Cohen's $\\kappa$ {N('validation/A0_vs_A0r/kappa', 'f3')}, 95\\% CI "
         f"{N('validation/A0_vs_A0r/lo', 'f3')}--{N('validation/A0_vs_A0r/hi', 'f3')}), GPC vs repeat "
         f"{DN(ag + '/A2_vs_A2r/p', 'pct1')}\\% ({DN(ag + '/A2_vs_A2r/k')} of {DN(ag + '/A2_vs_A2r/n')}), emulated "
         f"GPC vs Brave {DN(ag + '/A2_vs_V1/p', 'pct1')}\\% ({DN(ag + '/A2_vs_V1/k')} of {DN(ag + '/A2_vs_V1/n')}). "
         r"Screenshot audit: the crawler's labels against saved screenshots: banner detections confirmed "
         f"{share(s4 + '/banner_precision')}, first-layer reject button {share(s4 + '/reject_agreement')}, click "
         f"outcome {share(s4 + '/click_flag_agreement')}. The audit labels have not yet been checked by an "
         r"independent human rater. Details: Fig.~S4.")
    tail = (r"In (a) and (b), brick marks the code leaving from a Shopify sandbox (consent lost) and grey marks any "
            r"route. By arm, with the refusal signals that vendors receive in ad requests: Fig.~S9.")
    body = ' '.join([title, a, bb, c, d, tail])
    out = ['% caption_fig6.tex -- GENERATED by scripts/make_caption_fig6.py; every number is rendered from',
           '% analysis/outputs/stats.json or fig6/derived_numbers.json (registry: caption_fig6_numbers.csv).',
           '% Do not edit numbers by hand; edit the script and re-run.',
           r'\caption{' + body + '}',
           r'\label{fig:reach}', '']
    open(os.path.join(FIG6, 'caption_fig6.tex'), 'w').write('\n'.join(out))

    # ---- alt text (chart type, variables, main pattern, key numbers), through the same registry
    p0 = lambda key: fs.N(key + '/p', 'pct0') + '%'        # noqa: E731
    lo_v = min(rows, key=lambda x: fs.stat(vk[x] + '/p'))
    hi_v = max(rows, key=lambda x: fs.stat(vk[x] + '/p'))
    checks = [(ag + '/' + k, 'fig6') for k in ('A0_vs_A0r', 'A2_vs_A2r', 'A2_vs_V1')] + \
             [(s4 + '/' + k, 'stats') for k in ('banner_precision', 'reject_agreement', 'click_flag_agreement')]
    lowest = min(checks, key=lambda kc: P._dv(kc[0] + '/p') if kc[1] == 'fig6' else fs.stat(kc[0] + '/p'))
    low_txt = (P.DN(lowest[0] + '/p', 'pct0') if lowest[1] == 'fig6' else fs.N(lowest[0] + '/p', 'pct0')) + '%'
    alt = (f"Four-panel figure: a line drawing with a dot plot, then three dot plots. (a) One creator-linked store, "
           f"Store C. Left, a line drawing: a creator's video link, whose URL carries a per-video code, opens the "
           f"store's landing page inside the browser; the page hands its URL to TikTok's and Google Ads' pixels, which "
           f"Shopify runs in sandboxes isolated from the page, and red arrows carry the code from the sandboxes to the "
           f"ad vendors outside the browser, each vendor named at the head of its arrow, while a grey arrow marks the "
           f"page's other routes to them. Right, a dot "
           f"plot with one row per page load, counting the ad vendors that received the code from a Shopify sandbox "
           f"(red circles) and by any route (grey squares): before any choice the code reached "
           f"{P.DN(g + '/A0/vendors_code')} ad vendors, {P.DN(g + '/A0/vendors_code_sbx')} of them (TikTok and Google "
           f"Ads) from a sandbox; after a refusal, by a Decline click or under Global Privacy Control, none received "
           f"it from a sandbox, but {P.DN(g + '/A1after/vendors_code')} and {P.DN(g + '/A2/vendors_code')} vendors "
           f"still received it by other routes. (b) Dot plot with 95% confidence intervals for the "
           f"{fs.N(b + '/creator_stores')} creator-linked stores: the code reached an ad vendor on "
           f"{p0(b + '/creator_token_reached_ad_vendor_A0')} of them and was sent from a sandbox on "
           f"{p0(b + '/creator_token_reached_sandboxed_A0')}. (c) Grey dots by vendor group with 95% confidence "
           f"intervals: {p0(ref)} of sandboxed ad beacons carried the full landing URL (a summary row at the bottom, "
           f"whose confidence interval runs up through the vendor rows as a pale red band), from {p0(vk[lo_v])} "
           f"({lo_v}) to {p0(vk[hi_v])} ({hi_v}). "
           f"(d) Grey dots on an agreement axis that does not start at zero, marked by a break at its left end: "
           f"repeat loads, Brave's native Global "
           f"Privacy Control and a screenshot audit agree with the crawler's measurements on {low_txt} or more of "
           f"stores or loads in every check.")
    open(os.path.join(FIG6, 'alt_text_fig6.txt'), 'w').write(alt.replace(fs.MINUS, '-') + '\n')
    fs.write_registry(os.path.join(FIG6, 'caption_fig6_numbers.csv'))
    print(f'wrote caption_fig6.tex ({len(body.split())} words), alt_text_fig6.txt and caption_fig6_numbers.csv')


if __name__ == '__main__':
    main()
