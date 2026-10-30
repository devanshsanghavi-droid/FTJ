"""Write caption_fig2.tex (Figure 2, methodology; v7, ../../DESIGN_V7.md section 10) and alt_text_fig2.txt from templates
whose every number is a placeholder filled from analysis/outputs/stats.json, figures/v7/derived_numbers.json or
figures/v7/fig2/derived_numbers.json. The registry of the rendered numbers goes to caption_fig2_numbers.csv (checked by
scripts/trace_fig2.py). Caption rules: a bold one-sentence title (the claim); each panel in turn as '(a)~' with
lowercase cross-references ('Fig.~1c'); abbreviations defined on first use; n and the unit for every panel.

v7.1 names every encoding once: a's phase frames ('Frame', 'Draw', 'Crawl') and grey flat-ended removal branches (the
first step's 'not on Shopify' branch included, so every count is the one above minus its branches); b's store in Fig
1a's arrangement and its grounds (light grey: the page; darker grey: the sandboxes, the web worker above the sandboxed
iframe; amber: the cookie banner), the crawler's bus and its fork (grey arrows), the note on the bus, the one brick
arrow (a request sent before any choice, brick as in Fig 1c) landing on the test code, and the two square brackets on
the request ('vendor', 'test code'); c's single time axis (time from each page's load event), one amber tick per arm,
the grey end tick at the reload, the square brackets of the compared windows, and the moments drawn at their medians.

Placeholders: {S:key[:fmt]} stats.json   {D:key[:fmt]} figures/v7/derived_numbers.json
              {F:key[:fmt]} fig2/derived_numbers.json   {FS:key} a fig2 time in ms, shown in s (one decimal)
              {KN:key} 'k of n' from stats.json   {T:key} a string (derived)
              {SID:key} the pseudonymous store ID of a load ID (derived; 'S1152__A0' -> 'S1152')
              @SUPP@label -> S:label (a supplement label, read through xr-hyper)
Run:  python3 figures/v7/fig2/scripts/make_caption_fig2.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG2 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG2, '..', 'style')))
import figstyle as fs  # noqa: E402

F2 = json.load(open(os.path.join(FIG2, 'derived_numbers.json')))
TL = 'fig2c_timeline/'

TEMPLATE = r"""\caption{\textbf{We load each store three ways and label every ad request, including those sent from inside Shopify's sandboxes.} (a)~The sampling flow, top to bottom, in three phases, each in a grey outline: Frame (the sampling frame), Draw and Crawl. Each box gives a stage (left) and its count (right); grey branches with flat ends give the domains or stores removed between two stages, with their count and reason, so that each count is the one above minus its branches. Tranco top {S:design/tranco_top_n} domains; {D:fig2a_funnel/flagged} whose domain-name system (DNS) records point to Shopify ({F:fig2a_not_on_shopify/n} not on Shopify by this rule); {D:fig2a_funnel/verified} checked: all {S:checks/provenance/sample/census_drawn} flagged domains of the three upper rank buckets and {S:checks/provenance/sample/random_bucket_drawn} of the {S:checks/provenance/sample/random_bucket_flagged} in the lowest, drawn in a seeded random order until its quota of eligible stores was met (the other {F:fig2a_not_drawn/n} were not drawn); {D:fig2a_funnel/live} live storefronts ({D:fig2a_funnel/excluded/not_live} not live); {D:fig2a_funnel/sample} sampled ({D:fig2a_funnel/excluded/content_rules} not eligible: no product page, a duplicate, adult or aimed at children; Supplementary Table~\ref*{@SUPP@tab:s-exclusions}); {D:fig2a_funnel/captured} captured in all three base arms and analysed ({D:fig2a_funnel/excluded/not_captured} not captured; {D:fig2a_funnel/excluded/content_sensitivity} not eligible on content: adult products or aimed at children, found after the crawl and excluded for content sensitivity). Not shown: the {D:fig2a_funnel/creator} creator-linked stores of Fig.~6, a separate stratum, not counted in the {D:fig2a_funnel/captured}. (b)~Where the crawler attaches, drawn on the store of Fig.~1a in its arrangement: a Shopify store in the browser (outer frame), with the page's main thread (light grey ground), which holds the consent-management platform's (CMP) cookie banner (amber) and the vendor tags, and, below it, the two sandboxes in which Shopify's Web Pixels Manager runs pixels (darker grey ground): a web worker (`strict' runtime) above a sandboxed iframe (`lax'). The crawler, a client of the Chrome DevTools Protocol, stands outside the browser; one bus (grey arrows) forks to every target, the page and each worker and iframe, and attaches the crawler to it before any script runs, including the sandboxes, which a CMP's script blocker in the page cannot reach (Fig.~1a). It records each request in the session of the target that sent it and labels every ad request by origin, timing, vendor and payload. Brick arrow: one captured request, the first sandboxed data beacon with our test code in the Default load of store {SID:fig2b_worked_request/load_id} (one row of Fig.~1c, sent before any choice; brick, as there). A Google Ads pixel sent it from the sandboxed iframe (its origin) {D:fig2b_worked_request/t_ms}~ms after navigation start, {D:fig2b_worked_request/before_banner_ms}~ms before the banner became visible at {D:fig2b_worked_request/t_banner_ms}~ms (its timing). The arrow lands on our test code in the request's URL below. Square brackets mark the host, which names the vendor, and the test code, {T:fig2b_worked_request/test_code}: our pseudonymous code for the store, the value of utm\_campaign in the landing URL that the `{T:fig2b_worked_request/carrier_param}' parameter (the payload) carried. The request path (with the advertiser's account number), the landing page's path and all other parameter values are dropped (\ldots) so that the store cannot be identified. (c)~The three base arms as timelines under one time axis, the time from each page's load event. Each line is one page load and starts at navigation; the marker at the left is the arm's marker used throughout. Amber ticks: each arm's consent moment, named above it. Default (\mkDefault): no interaction; the banner becomes visible (the detector polls every {S:design/banner_poll_ms}~ms), and the load is observed until {S:design/observe_after_load_s}~s after its load event. Decline (\mkDecline): once the banner is visible, the Decline click on a first-layer reject control, made on {S:fig5/decline/clicked_all} stores; it worked on {S:fig5/decline/clicked} (banner gone {S:design/click_check_s}~s after the click, or a refusal recorded by Shopify). The first page is observed after the click and ends at the reload (grey end tick): the same URL is loaded again in the same browser, with new sandboxes, and this next page (the row below) is observed for {S:design/next_page_observe_s}~s after its load event. Global Privacy Control (GPC, \mkGPC): the signal is set from navigation on, in every frame, worker and request. Square brackets: the equal {S:design/equal_window_s}~s windows on which the arms are compared (Fig.~5a), each from a load event (in Decline, the next page's), so that they share one zero. Navigation, the banner, the click, the reload and the next page's navigation vary by store and are drawn at their medians over the analysed stores: in Default, navigation {FS:default_nav_to_load}~s and the banner {FS:default_banner_before_load}~s before the load event ({F:fig2c_timeline/default_nav_to_load/n} and {F:fig2c_timeline/default_banner_before_load/n} loads); in Decline ({F:fig2c_timeline/decline_click_from_load/n} clicked loads), the click {FS:decline_click_from_load}~s and the reload {FS:decline_reload_from_load}~s after the load event, and the next page's load event {FS:next_nav_to_load}~s after its navigation; in GPC, navigation {FS:gpc_nav_to_load}~s before the load event. Each base arm covers {S:design/n_main} stores. Signal, action, window and $n$ of every arm: Supplementary Table~\ref*{@SUPP@tab:s-arms}.}
\label{fig:methods}"""

# Alt text (chart type, variables, main pattern, key numbers); numbers through the same registry, numerals as numbers.
ALT = (r"Three-panel methods figure drawn as line art. (a) Sampling flow as a column of boxes in three outlined phases "
       r"(frame, draw and crawl), each box a stage and its count: Tranco top {S:design/tranco_top_n} domains, "
       r"{D:fig2a_funnel/flagged} whose DNS records point to Shopify, {D:fig2a_funnel/verified} checked, "
       r"{D:fig2a_funnel/live} live, {D:fig2a_funnel/sample} sampled and {D:fig2a_funnel/captured} analysed; grey side "
       r"branches give the domains or stores removed between stages, from {F:fig2a_not_on_shopify/n} domains not on "
       r"Shopify to {D:fig2a_funnel/excluded/content_sensitivity} stores found not eligible after the crawl. "
       r"(b) Schematic, the largest panel, on the store layout of Figure 1a: a crawler box outside a frame for the "
       r"Shopify store in the browser sends one connector bus into it, which forks up into the page (light grey region "
       r"holding the cookie banner and the vendor tags) and right into both of Shopify's pixel sandboxes (darker grey "
       r"region: a web worker above a sandboxed iframe); a note on the bus says it is attached before any script runs. "
       r"One brick-red arrow drops out of the sandboxed iframe and the browser onto the test code of one captured "
       r"request, shown below as a single shortened line of URL text whose host is bracketed as the vendor and whose "
       r"last token is bracketed as the test code. (c) Timelines of the three base arms on one axis, time from each "
       r"page's load event in seconds: Default, Decline (its first page, which ends at a reload, and its next page on "
       r"the row below) and GPC, with one amber tick per arm for the banner, the Decline click and the GPC signal; "
       r"square brackets mark the equal {S:design/equal_window_s} s windows, which line up at zero for all three arms.")


def fill(m):
    kind, _, rest = m.group(1).partition(':')
    key, _, f = rest.partition(':')
    f = f or 'int'
    if kind == 'S':
        return fs.N(key, f)
    if kind == 'D':
        return fs.N(key, f, source='derived')
    if kind == 'F':
        name, _, sub = key.partition('/')
        v = fs._walk(F2[name]['value'], sub) if sub else F2[name]['value']
        s = fs.render(v, f)
        fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig2_derived', key=key, fmt=f, value=json.dumps(v)))
        return fs.typo(s)
    if kind == 'FS':
        k = TL + key + '/ms'
        name, _, sub = k.partition('/')
        v = fs._walk(F2[name]['value'], sub)
        assert v > 0, (k, v)                       # stated as 'before' / 'after': a positive duration
        s = fs.render(v / 1000.0, 'f1')
        fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig2_derived', key=k, fmt='f1/1000', value=json.dumps(v)))
        return fs.typo(s)
    if kind == 'KN':
        return fs.KN(key)
    if kind == 'SID':
        v = fs.derived(key)                        # a load ID 'S<id>__<arm>': the store's pseudonymous ID is shown
        sid = v.split('__')[0]
        assert sid.startswith('S') and sid[1:].isdigit(), sid
        fs._REG.append(dict(text=v, shown=sid, source='derived', key=key, fmt='str', value=json.dumps(v)))
        return sid
    if kind == 'T':
        v = fs.derived(key)
        fs._REG.append(dict(text=v, shown=v, source='derived', key=key, fmt='str', value=json.dumps(v)))
        return v.replace('_', r'\_')
    raise ValueError(kind)


PLACEHOLDER = re.compile(r'\{((?:S|D|F|FS|KN|T|SID):[^{}]+)\}')

if __name__ == '__main__':
    fs.reset_registry()
    body = PLACEHOLDER.sub(fill, TEMPLATE)
    assert not re.search(r'\{(?:S|D|F|FS|KN|T|SID):', body), 'unfilled placeholder'
    assert not re.search(r'\(d\)|Fig\.~2d', body), 'panel d moved to Fig 6d'
    assert re.findall(r'\(([a-z])\)~', body) == ['a', 'b', 'c'], 'panel letters a, b, c, lowercase, in order'
    # labels in the supplement are read through xr-hyper (main.tex: \externaldocument[S:]{supplement}); the prefix is
    # written as @SUPP@ in the template so that '{S:tab:...}' is not taken for a stats placeholder
    body = body.replace('@SUPP@', 'S:')
    head = ('% caption_fig2.tex -- GENERATED by scripts/make_caption_fig2.py; every number is rendered from\n'
            '% analysis/outputs/stats.json, figures/v7/derived_numbers.json or fig2/derived_numbers.json\n'
            '% (registry: caption_fig2_numbers.csv). Do not edit numbers by hand; edit the script and re-run.\n')
    open(os.path.join(FIG2, 'caption_fig2.tex'), 'w').write(head + body + '\n')
    alt = PLACEHOLDER.sub(fill, ALT)
    assert not re.search(r'\{(?:S|D|F|FS|KN|T|SID):', alt), 'unfilled placeholder (alt text)'
    open(os.path.join(FIG2, 'alt_text_fig2.txt'), 'w').write(alt.replace(fs.MINUS, '-') + '\n')
    fs.write_registry(os.path.join(FIG2, 'caption_fig2_numbers.csv'))
    words = len(re.sub(r'\\[a-zA-Z]+|[{}~$]', ' ', body).split())
    print(f'wrote caption_fig2.tex ({words} words), alt_text_fig2.txt and caption_fig2_numbers.csv')
