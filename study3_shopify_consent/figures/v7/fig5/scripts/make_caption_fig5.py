"""Caption and alt text for Figure 5 (v7; ../../DESIGN_V7.md section 10), written to figures/v7/fig5/caption_fig5.tex
and alt_text_fig5.txt.

The panels print no numbers except axis ticks, so the caption carries every count, percentage, interval and median
(a: the any-vendor shares and the paired differences; b: the gate counts -- not drawn -- the still-sending totals with
their CIs and the class counts; c: the load and store counts per block, the 'k of n sandboxes' lines and the medians).
v7 names every encoding once: a's arm marks (Fig. S8a's coding), light-grey joining line, key and full percentage
scale; b's thin horizontal share bars, the class colours (brick / grey / dark grey, Fig. S8c's), their order from 0 (the
assignment order, = Fig. S8c's key), the class names set at the Decline bar, and each bar's total (short tick) with its
CI on a line just under the bar; c's symmetric-log time axis, the amber write, the brick / grey / slate ticks and their
key, the pale brick key area (the time each 'no' load's sandboxes ran before the write) and the row axis broken, with
cut marks, between the two blocks.
Lowercase panel labels '(a)~'.

Structure (DESIGN_V7 section 10): a bold one-sentence title (the claim), each panel in turn; abbreviations defined at
first use (GPC, CI, pp, CMP); sample sizes, the unit and the interval type and level stated. Every number is rendered
from analysis/outputs/stats.json or the derived-number files through the same registry as the panels
(panels/caption_fig5_numbers.csv), so the trace check covers the caption too. LaTeX conventions follow
paper/sections/*.tex (``quotes'', 95\\%, ~ before units); minus signs are $-$, ranges use --.
Run: python3 figures/v7/fig5/scripts/make_caption_fig5.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_fig5_panels as P  # noqa: E402  (number helpers; importing does not draw anything)

fs = P.fs
N, KN = fs.N, fs.KN


def tex(s):
    """Typographic display characters from the renderers -> LaTeX."""
    return s.replace(fs.MINUS, '$-$').replace(fs.EN_DASH, '--').replace('%', '\\%')


def pct(key):
    return N(key + '/p', 'pct1') + '\\%'


def ci(key, lo='lo', hi='hi'):
    return f"{N(key + '/' + lo, 'pct1')}--{N(key + '/' + hi, 'pct1')}"


def main():
    fs.reset_registry()
    a = 'fig5/a/Any vendor'
    cmp_ = 'fig5/compare'
    dd, dg, ew = cmp_ + '/default_vs_decline', cmp_ + '/default_vs_gpc', cmp_ + '/equal_window'
    ga = 'fig5/c/gate_audit'
    ex = 'fig5b_exclusive_classes'
    rc = 'fig5c_race_per_sandbox'
    d5 = 'fig5/d'
    dec_any = 'fig5/b/Shopify recorded a refusal/decline_any_after'
    gpc_any = 'fig5/c/composition/gpc/any'
    # the sentences below state these facts; fail loudly if the sources ever disagree
    assert fs.stat(dd + '/b_only') == 0 and fs.stat(dg + '/b_only') == 0     # "no store fired ... without"
    for v in ['Any vendor'] + fs.VENDOR_ORDER:                                  # "in every group Default is highest"
        pv = {arm: fs.stat(f"fig5/a/{v.replace('/', '~1')}/{arm}/p") for arm in P.ARMS}
        assert pv['Default'] > max(pv['Decline'], pv['GPC']), v
    assert fs.derived(f'{ex}/decline_refused/new_pixel_declaring_refused_purpose') == 0
    assert fs.stat(ga + '/gpc_sale_pixels/k') == 0 and fs.stat(ga + '/gpc_sale_pixels/loads_with_start/k') == 0
    dm = fs.stat(ga + '/default_denied_mkt_pixels')
    assert dm['n'] - dm['k'] == dm['started']                                   # "the other 28 started"
    assert fs.stat(d5 + '/grant/pixels_after') == fs.stat(d5 + '/grant/pixels')  # "all 342 ... after it"
    assert fs.stat(d5 + '/deny/pixels_before') + fs.stat(d5 + '/deny/pixels_after') == fs.stat(d5 + '/deny/pixels')
    assert fs.stat(d5 + '/deny/pixels_after') == fs.derived(rc + '/deny/after')
    lags = {ch: [v for row in P.ld(f'fig5c_race_loads/{ch}/lags_ms') for v in row] for ch in ('deny', 'grant')}
    assert all(P.C_XLIM[0] < v / 1000 < P.C_XLIM[1] for ch in lags for v in lags[ch])   # "every sandbox is drawn"
    assert sorted(lags['grant'])[int(0.95 * len(lags['grant']))] < 50                   # "most within a few tens of ms"

    title = ('A refusal stops new pixels that declare the refused purpose; pixels that started earlier, declare '
             'other purposes or declare none keep sending.')
    A = (f"(a)~The {N('fig5/a/n_clicked')} stores where the Decline click worked, each loaded three ways: Default, and "
         f"with a refusal (Decline, or the Global Privacy Control (GPC) signal). Share of stores on which a newly "
         f"created sandbox (a Shopify web-pixel worker or iframe) sent an advertising request within "
         f"{N('design/equal_window_s')}~s, for any vendor and for each of the seven vendor groups. Any vendor: Default "
         f"{KN(a + '/Default')} ({pct(a + '/Default')}; 95\\% confidence interval (CI) {ci(a + '/Default')}); the "
         f"fresh page after Decline {KN(a + '/Decline')} ({pct(a + '/Decline')}; {ci(a + '/Decline')}); GPC "
         f"{KN(a + '/GPC')} ({pct(a + '/GPC')}; {ci(a + '/GPC')}). In every group Default is the highest of the "
         f"three, and no store fired after Decline or under GPC without also firing under Default. Paired "
         f"differences: Default $-$ Decline {N(dd + '/paired_diff/diff', 'pct1')} percentage points (pp; 95\\% CI "
         f"{ci(dd + '/paired_diff', 'diff_lo', 'diff_hi')}); Default $-$ GPC {N(dg + '/paired_diff/diff', 'pct1')}~pp "
         f"({ci(dg + '/paired_diff', 'diff_lo', 'diff_hi')}); Decline $-$ GPC {N(ew + '/paired_diff/diff', 'pct1')}~pp "
         f"({ci(ew + '/paired_diff', 'diff_lo', 'diff_hi')}; {N(ew + '/a_only')} stores fired only after Decline and "
         f"{N(ew + '/b_only')} only under GPC, exact McNemar $p = {N(ew + '/p_exact', 'f3')}$). In each group the "
         f"three loads of the same stores sit left to right in the arm coding of Fig.~S8a (filled black circle: "
         f"Default; open dark-grey square: Decline; filled grey triangle: GPC; key at the top right), joined by a thin "
         f"light-grey line, on the full percentage scale; the vendor groups are named on the x axis, with any vendor "
         f"set apart on the left (per-vendor values, on the same scale: Fig.~S8a). Vertical lines: Wilson 95\\% CIs; "
         f"paired differences: Newcombe hybrid-score intervals.")
    B = (f"(b)~Shopify's gate held the new pixels that declare the refused purpose (not drawn): after Decline, "
         f"{N(ex + '/decline_refused/new_pixel_declaring_refused_purpose', source='derived')} of "
         f"{N('fig5/c/decline_n')} stores had a new pixel declaring it; under GPC, "
         f"{KN(ga + '/gpc_sale_pixels')} configured pixel entries that declare ``sale of data'' started "
         f"({KN(ga + '/gpc_sale_pixels/loads_with_start')} at-risk loads; "
         f"{N(ex + '/gpc/pixel_declaring_sale', source='derived')} stores); while the region default denied "
         f"``marketing'', {KN(ga + '/default_denied_mkt_pixels')} entries that declare it were held "
         f"({pct(ga + '/default_denied_mkt_pixels')}; the other {N(ga + '/default_denied_mkt_pixels/started')} "
         f"started). The bars show what still got through: the share of stores that still sent a sandboxed ad "
         f"request despite the refusal, Decline {KN(dec_any)} ({pct(dec_any)}; 95\\% CI {ci(dec_any)}) and GPC "
         f"{KN(gpc_any)} ({pct(gpc_any)}; {ci(gpc_any)}). Each such store is in one class, assigned in the order "
         f"a refused purpose, only purposes left allowed, no purpose; each thin bar stacks the classes from 0 in that "
         f"order, and the classes are named once, at the Decline bar: a refused purpose (brick: a pixel that started "
         f"before the refusal and declares the refused purpose kept sending, on the same page or in an unload beacon; "
         f"Decline only, {N(ex + '/decline_refused/kept_sending_refused_purpose', source='derived')} stores), only "
         f"purposes left allowed (grey; Decline {N(ex + '/decline_refused/only_left_allowed_purposes', source='derived')}"
         f", GPC {N(ex + '/gpc/only_left_allowed_purposes', source='derived')}), no purpose (dark grey; Decline "
         f"{N(ex + '/decline_refused/no_purpose', source='derived')}, GPC {N(ex + '/gpc/no_purpose', source='derived')}"
         f"). The greys of (b) mark these classes, not the arms of (a). Fig.~S8c uses the same class names, colours "
         f"and order, by window and without the one-class-per-store rule. The GPC total includes "
         f"{N(ex + '/gpc/other_unmatched', source='derived')} store that matched no class (not drawn). Decline: the "
         f"{N('fig5/c/decline_n')} stores where Shopify recorded the refusal; GPC: the {N('fig5/c/gpc_n')} stores where "
         f"Shopify set ``sale of data: no''. Just under each bar: its total (a short tick rising toward the bar's end) "
         f"on its Wilson 95\\% CI (horizontal line).")
    C = (f"(c)~The race between a consent-management platform (CMP) and pixel start-up: one row per page load in "
         f"which a CMP wrote ``marketing: no'' to Shopify without a click ({N(d5 + '/deny/loads')} loads, "
         f"{N(d5 + '/deny/stores')} stores; upper block) or ``yes'' ({N(d5 + '/grant/loads')} loads, "
         f"{N(d5 + '/grant/stores')} stores; lower block); the row ticks count the loads within each block, so the "
         f"row axis is broken between the blocks (cut marks). Each tick is one third-party sandbox that declares ``marketing'', "
         f"at its start minus the CMP's consent write (amber line); rows are sorted by the load's first sandbox. The "
         f"time axis is logarithmic on both sides of the write and linear between the two ticks nearest it, so that "
         f"starts seconds before the write and milliseconds after it are both visible; every sandbox is drawn. The "
         f"pale brick ground runs, row by row, from a ``no'' load's first sandbox to the write: the time its "
         f"marketing sandboxes ran before the refusal arrived. Of the "
         f"{N(d5 + '/deny/pixels')} sandboxes in the ``no'' loads, {N(d5 + '/deny/pixels_before')} started before "
         f"the write (brick; median "
         f"{tex(N(rc + '/deny/median_lag_ms', source='derived')).replace('$-$', '')}~ms before) and "
         f"{N(d5 + '/deny/pixels_after')} after it (grey); all {N(d5 + '/grant/pixels')} in the ``yes'' loads "
         f"started after it (slate; median {N(rc + '/grant/median_lag_ms', source='derived')}~ms after); the key at the "
         f"top right names the three tick colours. Throughout, "
         f"brick marks consent lost (b, c), slate consent honoured (c), amber the consent moment (c) and grey "
         f"context.")
    # same form as every other v2 caption file: \caption{...} then \label{...}, so the paper can \input it inside the
    # figure environment. The label is the one the paper's sections already cite for this figure.
    cap = f"\\caption{{\\textbf{{{title}}}\n{tex(A)}\n{tex(B)}\n{tex(C)}}}\n\\label{{fig:choices}}\n"
    # tex() must not double-escape: the parts above already contain LaTeX; re-apply only to renderer characters
    cap = cap.replace('$$-$$', '$-$').replace('\\\\%', '\\%')
    # alt text (K-Dense skill step 3: chart type, variables, main pattern, key numbers), through the same registry
    p0 = lambda key: N(key + '/p', 'pct0') + '%'        # noqa: E731
    alt = (f"Three-panel figure. (a) Dot plot with 95% confidence intervals: of the {N('fig5/a/n_clicked')} stores "
           f"where the Decline click worked, the share on which a newly created sandbox sent an advertising request is "
           f"{p0(a + '/Default')} under Default, {p0(a + '/Decline')} on the fresh page after Decline and "
           f"{p0(a + '/GPC')} under the Global Privacy Control signal; in each of the seven ad vendor groups along the "
           f"x axis Default is highest. Arms are told apart by marker shape and grey level. A refusal lowers the share "
           f"but does not stop it. (b) Two thin horizontal stacked share bars, the classes named at the Decline bar, each "
           f"bar's total and its 95% confidence interval drawn just under it. Shopify's gate held the new pixels that "
           f"declare the refused purpose: none started after Decline "
           f"({N(ex + '/decline_refused/new_pixel_declaring_refused_purpose', source='derived')} of "
           f"{N('fig5/c/decline_n')} stores) or under GPC ({KN(ga + '/gpc_sale_pixels')} 'sale of data' entries), and "
           f"a region default that denies 'marketing' held {KN(ga + '/default_denied_mkt_pixels')} such entries. Yet "
           f"{N(dec_any + '/p', fs.SHARE_PCT)}% of Decline stores and {N(gpc_any + '/p', fs.SHARE_PCT)}% of GPC "
           f"stores still sent a sandboxed ad request, through pixels that started before the refusal "
           f"({N(ex + '/decline_refused/kept_sending_refused_purpose', source='derived')} Decline stores, red), "
           f"declare only purposes left allowed (grey), or declare none (dark grey). (c) Raster on a symmetric "
           f"logarithmic time axis, one row per page load, of when each third-party 'marketing' sandbox started "
           f"relative to a consent-management platform writing consent (amber line): when it wrote 'no', "
           f"{N(d5 + '/deny/pixels_before')} of {N(d5 + '/deny/pixels')} sandboxes had already started, up to seconds "
           f"earlier (red, left of the line, on a pale red area that runs from each load's first sandbox to the "
           f"line); when it wrote 'yes', all {N(d5 + '/grant/pixels')} started after it, most within a few tens of "
           f"milliseconds (blue-grey, right of the line). A key names the three tick colours, and a gap with cut marks on "
           f"the row axis separates the 'no' loads from the 'yes' loads.")
    open(os.path.join(P.FIG5, 'alt_text_fig5.txt'), 'w').write(alt.replace(fs.MINUS, '-') + '\n')
    out = os.path.join(P.FIG5, 'caption_fig5.tex')
    head = ('% caption_fig5.tex -- GENERATED by scripts/make_caption_fig5.py; every number is rendered from\n'
            '% analysis/outputs/stats.json, figures/v7/derived_numbers.json or fig5/derived_numbers.json\n'
            '% (registry: panels/caption_fig5_numbers.csv). Do not edit numbers by hand; edit the script and re-run.\n')
    open(out, 'w').write(head + cap)
    fs.write_registry(os.path.join(P.PANELS, 'caption_fig5_numbers.csv'))
    print(cap)
    words = len(cap.split())
    print(f'wrote {out} ({words} words)')


if __name__ == '__main__':
    main()
