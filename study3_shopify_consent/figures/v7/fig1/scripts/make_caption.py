"""Caption and alt text for Figure 1 (v6 RESTRAINT; ../../RESTRAINT.md: 'the caption does the explaining'). A bold
one-sentence title, each panel described in turn with lowercase letters '(a)~' and lowercase cross-references
'Fig.~4b', abbreviations defined on first use, n and the unit, the interval type and level, and every encoding named
(colours once: brick = requests that lost consent, amber = the banner becoming visible, grey = context).

v7 (../../DESIGN_V7.md section 10): the figure prints no data numbers except tick labels, so this caption carries all
of them -- the five loss counts, the trace counts and times of b (from navigation start; b's axis is re-based to the
banner), and c's out-of-axis counts and before-the-banner share. Panel a marks the five points with small outlined
numerals 1-5 (never filled discs) on the drawn elements they sit on (region default, script blocker, CMP's choice,
consent gate, the path to the vendors); the caption's (1)-(5) refer to them, in that order (trace_fig1.py checks the
match). The caption also names every v7 encoding: a's nested regions and their grounds, the vendor-group list, b's lane
grounds (a's regions repeated) and c's pale brick 'before the banner' ground. Every number is rendered from analysis/outputs/stats.json or figures/v7/fig1/derived_numbers.json through
figstyle.N / KN or the fig1 readers DN / SEC (never typed) and registered in caption_fig1_numbers.csv for the trace
check (trace_fig1.py).

Outputs: figures/v7/fig1/caption_fig1.tex (label fig:situating), caption_fig1_numbers.csv, alt_text_fig1.txt,
         alt_text_fig1_numbers.csv
Run:  python3 figures/v7/fig1/scripts/make_caption.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_panels as mp  # noqa: E402  (figstyle set-up and the DN / SEC readers for fig1/derived_numbers.json)

fs, DN, SEC = mp.fs, mp.DN, mp.SEC


def tex(s):
    """Typographic minus / en dash from figstyle -> LaTeX."""
    return s.replace(fs.MINUS, '$-$').replace(fs.EN_DASH, '--')


def pct(key):
    return fs.N(key + '/p', 'pct1') + r'\%'


def ci(key):
    return f"{fs.N(key + '/lo', 'pct1')}--{fs.N(key + '/hi', 'pct1')}\\%"


def main():
    fs.reset_registry()
    kn = fs.KN
    bop = 'round4/blocklist/combined/primary/fired'
    t = 'fig1b_trace'
    R = 'fig1c_raster'
    V = mp._dv(t + '/vendor_label')
    cmp_name = {'pandectes': 'Pandectes', 'onetrust': 'OneTrust', 'cookiebot': 'Cookiebot'}[mp._dv(t + '/cmp')]
    assert mp._dv(t + '/neutralized_type') == ['javascript/blocked'] and mp._dv(t + '/n_page_requests') == 0
    assert mp._dv(t + '/clicks') is None and len(mp._dv(t + '/vendors_neutralized_and_sbx')) == 2
    assert mp._dv(t + '/beyond_axis_kinds') == ['beacon'] and mp._dv(t + '/n_beyond_axis') == 1

    title = "Consent is lost at five points between the cookie banner and Shopify's sandboxed pixels."
    A = (
        "(a)~A Shopify store in the browser (outer frame), drawn as nested regions. Top: the page's main thread (light "
        "grey ground), where a consent-management platform's (CMP) cookie banner (amber, the colour of its appearance "
        "in b and c) and its script blocker (black wall) run; the blocker stops vendor tags in the page (grey line; "
        "dotted: the path it cuts). Bottom: Shopify's Web Pixels Manager starts each app or custom pixel in a sandbox "
        "isolated from the page (pixel sandboxes, darker grey ground), a web worker (strict runtime) or a sandboxed "
        "iframe (lax runtime), once Shopify's consent gate (its Customer Privacy API) allows every purpose that the "
        "pixel declares. The gate is set by the store's region default, by the CMP's choice if the CMP writes it to "
        "Shopify, and by Global Privacy Control (GPC). The sandboxes stand under the page's vendor tags (the same "
        "vendors' code, isolated), and the pixels' requests (brick arrows) leave the browser for the ad vendors "
        "underneath the blocker, which covers the page only; the ad-vendor box lists the vendor groups used in every "
        "figure. Consent is lost at five of the drawn elements, marked in a by outlined numerals: "
        f"(1)~the region default, `allowed until choice' on {kn('fig1b/region_allowed')} stores that returned one "
        "(Methods; Fig.~3 measures its effect); "
        f"(2)~the script blocker (blocked on paper): it cannot see into the sandboxes, so on {kn(bop)} stores "
        f"({pct(bop)}; Wilson 95\\% confidence interval (CI) {ci(bop)}) whose CMP listed an ad vendor as blocked and "
        "wrote no `yes' to Shopify, that vendor fired from the sandbox anyway in the Default load (no click; main and "
        "lower-ranked expansion samples combined; Fig.~4); "
        "(3)~the CMP's choice, which arrives late: in loads where a CMP wrote `marketing: no' without a click, "
        f"{fs.N('fig5/d/deny/pixels_before')} of {fs.N('fig5/d/deny/pixels')} third-party sandboxes that declare "
        "marketing had already started (Fig.~5c); "
        "(4)~the consent gate, which reads declared purposes only: under GPC, a pixel that declares no purpose fired "
        f"on {kn('fig5/c/gpc_nopurpose_fired')} stores where Shopify set `sale of data: no' (Fig.~S8c; Fig.~5b counts "
        "each store in one class only); "
        "(5)~the path to the vendors, which a refusal does not cut: after a Decline (a click on the banner's reject "
        "button), a pixel that declares the refused purpose kept sending (same page or unload beacons) on "
        f"{kn('fig5/c/fig5c_rows/f3')} stores with a recorded refusal (Fig.~5b)."
    )
    reqs = mp._dv(t + '/requests')
    within = [q['t_ms'] for q in reqs if q['t_ms'] <= mp._dv(t + '/axis_ms')]
    assert mp._dv(t + '/t_first_sandbox_ms') == min(within) and mp._dv(t + '/tick_groups/3/t_ms_last') == max(within)
    B = (
        f"(b)~Point (2) in one page load (re-check, no click). The store is from the main sample; its CMP ({cmp_name}) "
        f"lists {V} as blocked and wrote no `yes'. It is the first by ID among the "
        f"{fs.N('checks/recheck/blocker/stores_neutralized_and_sbx')} stores where the blocker neutralized a "
        "declared-blocked vendor's page tag while that vendor's sandboxed pixel sent requests, and of its two such "
        f"vendors {V} sent more sandboxed requests. The axis is time from the banner becoming visible (amber line), "
        f"which happened {SEC(t + '/t_banner_ms')}~s after navigation start; the times below are from navigation "
        "start, and no choice was made. The two rows repeat a's grounds (light grey: the page; darker grey: the "
        f"sandbox). Top row: the blocker neutralized {V}'s tag as it was inserted, at "
        f"{SEC(t + '/t_tag_neutralized_ms')}~s (black bar, the wall of a; script type `javascript/blocked'); the tag sent "
        "no request. "
        f"Bottom row: {V}'s pixel in a sandboxed iframe, which had requested its library "
        f"{SEC(t + '/lead_first_sandbox_over_tag_ms', 'f2')}~s earlier, sent {DN(t + '/n_libraries_within_axis')} "
        f"library loads (short brick ticks; key above the axis) and {DN(t + '/n_beacons_within_axis')} data beacons (tall "
        "brick ticks) "
        f"between {SEC(t + '/t_first_sandbox_ms')} and {SEC(t + '/tick_groups/3/t_ms_last')}~s, and "
        f"{DN(t + '/n_beyond_axis')} more beacon at {SEC(t + '/beyond_axis_ms/0')}~s (arrowhead at the right end of the "
        "row); "
        f"requests of one kind less than {DN(t + '/tick_merge_ms')}~ms apart are drawn side by side. This axis has "
        "a larger scale than that of (c); the two zeros are aligned."
    )
    C = (
        "(c)~The same failure at scale: every banner store whose sandboxed pixel sent an ad request before any choice "
        f"({kn('fig1b/banner_fires')} stores that showed a banner), one row each, sorted by its first sandboxed ad "
        "request (brick line) and timed from the banner becoming visible (amber line; the detector polls every "
        f"{fs.N('design/banner_poll_ms')}~ms). Grey ticks: the stores' sandboxed ad requests in the Default load; "
        f"the {DN(R + '/n_requests_left')} requests earlier than the axis and the {DN(R + '/n_requests_right')} later "
        f"are not drawn, and the brick line leaves the axis (arrowheads) for the {DN(R + '/n_first_left')} stores "
        f"whose first request came earlier and the {DN(R + '/n_first_right')} whose first request came later. Rows "
        "above the point where the brick line crosses the amber line (open circle; the pale brick ground between the "
        f"two lines is the time before the banner): the {kn('fig3/b/before_banner')} stores "
        f"({pct('fig3/b/before_banner')}; Wilson 95\\% CI {ci('fig3/b/before_banner')}) whose first request came "
        "before the banner (Fig.~S6b). Per vendor group: Fig.~S6a; per-store request counts: Fig.~S6e."
    )
    tail = (f"All loads from one residential vantage point in California, USA; main sample: {fs.N('design/n_main')} "
            f"popular Shopify stores from the Tranco top {fs.N('design/tranco_top_n')}.")
    body = tex(f"\\textbf{{{title}}}\n{A}\n{B}\n{C}\n{tail}")
    out = os.path.join(mp.FIG1, 'caption_fig1.tex')
    with open(out, 'w') as fh:
        fh.write('% GENERATED by figures/v7/fig1/scripts/make_caption.py: every number is rendered from stats.json /\n'
                 '% fig1/derived_numbers.json (registry: caption_fig1_numbers.csv). Edit the script, not this file.\n')
        fh.write(f'\\caption{{{body}}}\n\\label{{fig:situating}}\n')

    fs.write_registry(os.path.join(mp.FIG1, 'caption_fig1_numbers.csv'))

    # Alt text: chart type, variables, main pattern, key numbers -- rendered through the same readers into its own
    # registry (alt_text_fig1_numbers.csv), which trace_fig1.py checks like the caption's.
    fs.reset_registry()
    p0 = lambda key: fs.N(key + '/p', 'pct0') + '%'        # noqa: E731
    alt = (
        "Three-panel figure. (a) Line drawing of a Shopify store in the browser, as a frame holding two shaded "
        "regions. In the page region, a cookie banner and vendor tags sit beside the consent tool's script blocker, a "
        "black wall that stops the tags. Below the page, three signals (the consent tool's choice, the region default "
        "and Global Privacy Control) enter Shopify's consent gate, which starts pixels in the sandbox region, a web "
        "worker and a sandboxed iframe; their requests, drawn in red, leave the browser for the ad vendors, listed by "
        "name in a box outside the frame, underneath the blocker, which covers the page only. Small circled numerals "
        "one to five mark the points where consent is lost, explained in the caption; for the headline, a vendor that "
        "the consent tool lists as blocked fired "
        f"from the sandbox anyway on {kn(bop)} stores. (b) Two-row event plot of one page load on the two shades of "
        f"(a), timed from the banner becoming visible: the blocker stops {V}'s tag {SEC(t + '/t_tag_neutralized_ms')} seconds after "
        f"navigation start, while {V}'s sandboxed pixel sends {DN(t + '/n_libraries_within_axis')} library loads and "
        f"{DN(t + '/n_beacons_within_axis')} data beacons between {SEC(t + '/t_first_sandbox_ms')} and "
        f"{SEC(t + '/tick_groups/3/t_ms_last')} seconds, after the banner became visible at "
        f"{SEC(t + '/t_banner_ms')} seconds and with no choice made. "
        f"(c) Raster of the {fs.N('fig3/b/n')} banner stores whose sandboxed pixels sent an ad request before any "
        "choice, one row each, sorted by the first request, with each request as a grey tick and the first requests "
        "joined by a red line, against time relative to the banner becoming visible (an amber line at zero); for "
        f"{p0('fig3/b/before_banner')} of them the first request came before the banner was visible, and the area "
        "between the red line and the amber line is shaded pale red."
    )
    open(os.path.join(mp.FIG1, 'alt_text_fig1.txt'), 'w').write(alt.replace(fs.MINUS, '-') + '\n')
    fs.write_registry(os.path.join(mp.FIG1, 'alt_text_fig1_numbers.csv'))
    print('wrote', out, f'({len(body.split())} words), caption_fig1_numbers.csv, alt_text_fig1.txt and its registry')


if __name__ == '__main__':
    main()
