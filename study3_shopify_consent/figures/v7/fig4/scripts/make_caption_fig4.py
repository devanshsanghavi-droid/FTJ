"""Write caption_fig4.tex (LaTeX \\caption + \\label for Figure 4, v7) and alt_text_fig4.txt, with every number
rendered from analysis/outputs/stats.json, figures/v7/derived_numbers.json or fig4/derived_numbers.json through the
figstyle registry (caption_fig4_numbers.csv), so neither carries a typed number.

v7 (../../DESIGN_V7.md section 10; worked example ../../fig1/scripts/make_caption.py): the panels print no values (the
plot shows them by position), so the caption gives each plotted share as a percentage and k of n, and names every v7
encoding once: a's thin unit bars (one cell per store; brick = the declared-blocked vendor fired, light grey = it did
not) with their summaries (open circle + CI), the combined estimate set apart below (filled circle); b's row pairs
(brick circle = blocklist stores, grey square = the comparison; not slate, which means 'denied until consent' in
Fig. 3), the pale brick ground (the key area: the gap between a pair's two shares) and the pooled difference on rows
of its own (near-black diamonds, open = main sample only, filled = combined) with their CIs against a grey zero line
(Fig. 3a-right's grammar: dot + CI, no bars), at one length per percentage point in both plots of b. Panel a is loss point (2) of Fig. 1a measured, and says so (DESIGN_V7 section 10: later figures cite the
schematic's numerals).
Panel contents are v6's: (a) the blocked-on-paper rate by sample; (b) like for like per region default plus the pooled
Mantel-Haenszel difference ('Fig. 4b, right'). (v4's entry matrices are Supplementary Fig. S7d; its re-check trace is
Fig. 1b.)

Caption rules: bold one-sentence claim title; lowercase panel descriptions '(a)~'; abbreviations defined at first
use; n, unit, interval type and level for every panel; every encoding named.
Run:  python3 figures/v7/fig4/scripts/make_caption_fig4.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG4 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG4, '..', 'style')))
import figstyle as fs  # noqa: E402

D4 = json.load(open(os.path.join(FIG4, 'derived_numbers.json')))


def d4(key):
    name, _, rest = key.partition('/')
    return fs._walk(D4[name]['value'], rest) if rest else D4[name]['value']


def N4(key, f='int'):
    """Render a fig4 derived value and register it (source 'fig4_derived')."""
    v = d4(key)
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig4_derived', key=key, fmt=f, value=json.dumps(v)))
    return s


def tex(s):
    """Plain-text number conventions -> LaTeX: typographic minus -> $-$, en dash -> --, % -> \\%."""
    return s.replace(fs.MINUS, '$-$').replace(fs.EN_DASH, '--').replace('%', '\\%')


def N(key, f='int', source='stats'):
    return tex(fs.N(key, f, source))


def KN(key, source='stats'):
    return tex(fs.KN(key, source))


R4 = 'round4/blocklist'
LFL = f'{R4}/combined/like_for_like'
MH, MH_MAIN = f'{LFL}/mh_no_yes', f'{R4}/main/like_for_like/mh_no_yes'
SM = 'fig4_samples'


def signed(key):
    return ('+' if fs.stat(key) > 0 else '') + N(key, 'pct1')


def ci_pp(key):
    lo, hi = N(key + '/rd_lo', 'pct1'), N(key + '/rd_hi', 'pct1')
    return f'{lo} to {hi}' if '$-$' in lo + hi else f'{lo}--{hi}'


def fired(g):
    return KN(f'{R4}/{g}/primary/fired')


def pk(key):
    """'89.8\\% (53 of 59)': a plotted share (the panels print no values; DESIGN_V7 section 1)."""
    return f"{N(key + '/p', 'pct1')}\\% ({KN(key)})"


def main():
    fs.reset_registry()
    assert fs.stat(MH + '/rd_lo') > 0 > fs.stat(MH_MAIN + '/rd_lo')   # "a reduction is ruled out" / main-only CI spans 0
    for g in ('main', 'expansion', 'combined'):                          # "about half" in the title, in every sample
        assert 0.45 <= fs.stat(f'{R4}/{g}/primary/fired/p') <= 0.55
    title = (r"\textbf{Blocked on paper: a vendor that the consent tool's blocklist declares blocked still fired from "
             r"Shopify's sandbox on about half of the stores, and blocklist stores fired more, not less, often than "
             r"comparable stores.}")
    a = (f"(a)~Point~(2) of Fig.~1a at scale: blocklist stores whose consent-management platform (CMP) wrote no "
         f"`marketing: yes' to Shopify in the Default load (no interaction), and whether the ad vendor that the CMP's "
         f"blocklist declared blocked sent a request from its sandboxed Shopify pixel before any choice. Each bar is "
         f"one sample, one cell per store across the full axis: brick cells, the stores on which the declared-blocked "
         f"vendor fired, drawn first so that the brick part ends at the share; light grey cells, the stores on which "
         f"it did not. Under each bar, the sample's share (open circle) with its 95\\% confidence interval (CI): main "
         f"sample (Tranco top {N4(SM + '/main_top_n')}) {pk(R4 + '/main/primary/fired')}, expansion "
         f"{pk(R4 + '/expansion/primary/fired')}. Below a gap, the combined sample, the primary estimate (filled "
         f"circle): {N(R4 + '/combined/primary/fired/p', 'pct1')}\\% ({fired('combined')}; 95\\% CI "
         f"{N(R4 + '/combined/primary/fired/lo', 'pct1')}--{N(R4 + '/combined/primary/fired/hi', 'pct1')}\\%). The "
         f"expansion (Round~4) adds the {N(R4 + '/expansion/n_blocklist')} Shopify stores from Tranco ranks "
         f"{N4(SM + '/expansion_rank_lo')}--{N4(SM + '/expansion_rank_hi')} whose blocklist was in force at run time.")
    b = (f"(b)~Like for like, among stores whose CMP wrote no `yes': share of stores on which any sandboxed ad pixel "
         f"sent a request before any choice, within Shopify's region default at our California vantage point (one "
         f"pair of rows each). Brick circles (upper row): blocklist stores of both samples; grey squares (lower "
         f"row): the comparison, main-sample banner stores without a readable declaration. `Allowed until choice' "
         f"{pk(LFL + '/allowed_no_yes/blocklist')} vs {pk(LFL + '/allowed_no_yes/reference')}; `denied until "
         f"consent' {pk(LFL + '/denied_no_yes/blocklist')} vs {pk(LFL + '/denied_no_yes/reference')}. Pale brick "
         f"ground: the gap between a pair's two shares, that is, how much more often the blocklist stores fired. "
         f"Right, on rows of its own between the two pairs (it belongs to neither default) and at the same scale "
         f"(one percentage point has the same length in both plots): that gap pooled over the two defaults, "
         f"blocklist minus no declaration, by the Mantel--Haenszel method with Sato's variance, as a diamond with its "
         f"95\\% CI against a grey zero line (as in Fig.~3a, right). Combined (filled "
         f"diamond), blocklist stores fired {signed(MH + '/rd')} percentage points (pp; 95\\% CI {ci_pp(MH)}) more "
         f"often, so a reduction is ruled out; main sample only (open diamond), {signed(MH_MAIN + '/rd')}~pp "
         f"({ci_pp(MH_MAIN)}).")
    tail = (f"Horizontal lines: uncapped 95\\% CIs, each in the colour of its mark (Wilson for a share; stores are the "
            f"unit). Open marks: one sample alone; filled marks: the combined sample. Brick marks the blocklist "
            f"stores (consent lost) in both panels and pale brick their excess; grey, the comparison stores and "
            f"context; near-black, the pooled difference. Blocklists are "
            f"readable for Pandectes, OneTrust and Cookiebot only. Main sample {N('design/n_main')} stores; Default "
            f"load unless stated. The blocklist entries by route, from Shopify's sandbox or from a page script: "
            f"Fig.~S7d.")
    body = ' '.join([title, a, b, tail])
    out = ['% caption_fig4.tex -- GENERATED by scripts/make_caption_fig4.py; every number is rendered from',
           '% analysis/outputs/stats.json, figures/v7/derived_numbers.json or fig4/derived_numbers.json',
           '% (registry: caption_fig4_numbers.csv). Do not edit numbers by hand; edit the script and re-run.',
           r'\caption{' + body + '}',
           r'\label{fig:blocked-on-paper}', '']
    open(os.path.join(FIG4, 'caption_fig4.tex'), 'w').write('\n'.join(out))

    # Alt text (K-Dense skill step 3: chart type, variables, main pattern, key numbers), through the same registry.
    p0 = lambda key: fs.N(key + '/p', 'pct0') + '%'        # noqa: E731
    kn = lambda key: fs.KN(key)                            # noqa: E731
    pf = lambda g: f'{R4}/{g}/primary/fired'               # noqa: E731
    alt = (f"Two-panel figure. (a) Thin unit bars, one cell per store, with a dot and 95% confidence interval under each: "
           f"among blocklist stores whose consent tool had not itself consented, the share on which a vendor that the "
           f"blocklist declares blocked still sent a request from Shopify's sandbox before any choice is "
           f"{p0(pf('main'))} in the main sample ({kn(pf('main'))}) and {p0(pf('expansion'))} in the expansion "
           f"({kn(pf('expansion'))}); in both bars the brick cells fill about half. Below, the combined estimate is "
           f"{p0(pf('combined'))} ({kn(pf('combined'))}). (b) Left: dot plot with 95% confidence intervals, one pair "
           f"of rows per Shopify region default; blocklist stores (brick circles) fired at least as often as stores "
           f"without a readable declaration (grey squares): {p0(LFL + '/allowed_no_yes/blocklist')} vs "
           f"{p0(LFL + '/allowed_no_yes/reference')} under 'allowed until choice' and "
           f"{p0(LFL + '/denied_no_yes/blocklist')} vs {p0(LFL + '/denied_no_yes/reference')} under 'denied until "
           f"consent', with the gap between each pair shaded pale brick. Right, on two rows of its own between the "
           f"pairs: pooled over both defaults (diamonds with 95% confidence intervals, against a grey zero line), "
           f"blocklist stores fired {fs.PP(MH + '/rd')} "
           f"(percentage points) more often in the combined sample, an interval entirely above zero, and "
           f"{fs.PP(MH_MAIN + '/rd')} in the main sample alone, an interval that includes zero.")
    open(os.path.join(FIG4, 'alt_text_fig4.txt'), 'w').write(alt.replace(fs.MINUS, '-') + '\n')
    fs.write_registry(os.path.join(FIG4, 'caption_fig4_numbers.csv'))
    words = len(body.split())
    print(f'wrote caption_fig4.tex ({words} words), alt_text_fig4.txt and caption_fig4_numbers.csv '
          f'({len(fs._REG)} numbers)')


if __name__ == '__main__':
    main()
