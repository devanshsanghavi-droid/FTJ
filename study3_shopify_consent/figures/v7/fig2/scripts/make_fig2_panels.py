"""Figure 2 (methodology), v7.1: layout, numbers and checks for the three TikZ panels (binding spec ../../DESIGN_V7.md;
the worked example is ../../fig1). The sciplot skill's clean theme and schematic rules (mmd-ahd/scientific-figure-
skill, read and re-implemented, never executed), with FigGenie's nested labelled regions and full boxes and
nature-figure's figure contract and alignment / collision QA.

Figure contract (DESIGN_V7 section 1). One claim, the caption title: we load each store three ways and label every ad
request, including those sent from inside Shopify's sandboxes. Panel roles:
  a  the population: the sampling flow from the Tranco list to the 1,358 analysed stores (quiet supporting panel: line
     art, no colour, no grounds). Three labelled phase regions ('Frame', 'Draw', 'Crawl'; outline only, FigGenie);
     boxes sized to their text with the stage name left and its count right on one row (a ledger); every removal
     branches right with flat ends and its count and reason in 6 pt muted grey, all in one grammar ('not ...'). v7.1
     adds the first step's branch (domains not on Shopify), so EVERY stage equals the one above minus its branches
     (asserted).
  b  (hero) the mechanism: where the crawler attaches. Fig 1a's store in Fig 1a's arrangement and order (the page on
     top, holding the cookie banner and the vendor tags; the pixel sandboxes below at the right, the web worker above
     the sandboxed iframe), inside the outline frame of the store in the browser. What is new is the instrumentation:
     the crawler, outside the browser, drives one bus into the frame that forks (Fig 1a's fork idiom) up into the page
     and right into the worker and the iframe; its note, 'attached before any script runs', sits on the bus. The one
     accent (LEAK, 1.0 pt) is one captured request: it drops out of the sandboxed iframe and the browser and lands on
     its test code in the request's URL, shown below as one shortened line with two square brackets, 'vendor' (the host)
     and 'test code'.
  c  the comparison: the three base arms as timelines under ONE time axis, the time from each page's load event (s),
     ticks 0 to +20 (the axis covers the reload): its fixed protocol times (0, the 10 s compared window, the 15 s
     observation) are exact; the moments that vary by store (navigation start, the banner, the Decline click, the
     reload, the next page's navigation) are drawn at their medians over the analysed stores (fig2/derived_numbers.json
     `fig2c_timeline`, registered as drawn values). One amber tick per arm: its consent moment. Decline's first page
     ends at the reload with a short NEUTRAL end tick named 'reload'; its next page is its own row, so all three
     compared windows ([0, +10]: square brackets) share one zero; the bracket on the next page's row is keyed.

Every number and string the panels print is read from analysis/outputs/stats.json, figures/v7/derived_numbers.json or
fig2/derived_numbers.json and registered (panels/fig2_numbers.csv; checked by scripts/trace_fig2.py); positions that are
drawn but not printed are registered with fmt 'mark'. Every label is checked against MEASURED Arial widths.

Outputs (build/ is generated; never edit by hand):
  build/fig2_layout.tex    cell sizes and every coordinate the panels use, in mm
  build/fig2_numbers.tex   every number and string the panels print, as \\newcommand macros
  panels/fig2_numbers.csv  the registry of those values
Run:  python3 figures/v7/fig2/scripts/make_fig2_panels.py      (build_fig2.sh runs everything)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG2 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG2, '..', 'style')))
sys.path.insert(0, HERE)
import figstyle as fs  # noqa: E402
import redact  # noqa: E402  (fig2/scripts/redact.py: masks for the worked request)

PANELS = os.path.join(FIG2, 'panels')
BUILD = os.path.join(FIG2, 'build')
os.makedirs(PANELS, exist_ok=True)
os.makedirs(BUILD, exist_ok=True)
F2 = json.load(open(os.path.join(FIG2, 'derived_numbers.json')))


# ---------------------------------------------------------------------------------------------------- numbers
def STR(key, source='derived', transform=None, mask=None):
    """A string field (host, parameter, test code) read from derived_numbers.json and registered (no minus-sign
    substitution: 'cmpstudy-S1152' keeps its hyphen). mask: a named redaction from redact.py, registered only in its
    masked form, so no registry file holds the identifying string; trace_fig2.py re-applies the same mask."""
    v = fs.derived(key) if source == 'derived' else fs.stat(key)
    if mask:
        v = redact.apply(mask, v)
    shown = transform(v) if transform else v
    fs._REG.append(dict(text=str(v), shown=shown, source=source, key=key, fmt='str' + (':mask=' + mask if mask else ''),
                        value=json.dumps(v, ensure_ascii=False)))
    return shown


def _f2(key):
    name, _, rest = key.partition('/')
    v = F2[name]['value']
    return fs._walk(v, rest) if rest else v


def DN(key, f='int'):
    """Render a number from fig2/derived_numbers.json ('record/field') and register it."""
    v = _f2(key)
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig2_derived', key=key, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def mark(key):
    """Register a fig2/derived_numbers.json value that is drawn but not printed (c: the median moments)."""
    v = _f2(key)
    fs._REG.append(dict(text='', shown='', source='fig2_derived', key=key, fmt='mark', value=json.dumps(v)))
    return v


def mark_stat(key):
    """Register a stats.json value that is drawn but not printed (c: the protocol's windows)."""
    v = fs.stat(key)
    fs._REG.append(dict(text='', shown='', source='stats', key=key, fmt='mark', value=json.dumps(v)))
    return v


def tex_escape(s):
    return (s.replace('\\', r'\textbackslash{}').replace('&', r'\&').replace('_', r'\_').replace('%', r'\%')
            .replace('#', r'\#').replace('$', r'\$').replace('{', r'\{').replace('}', r'\}'))


def numbers():
    """Every value the panels print, registered (fs._REG); returns {macro name: rendered text}."""
    m = {}
    a = 'fig2a_funnel/'
    for name, key in [('nTranco', 'tranco'), ('nFlagged', 'flagged'), ('nVerified', 'verified'), ('nLive', 'live'),
                      ('nSample', 'sample'), ('nCaptured', 'captured'),
                      ('nExNotLive', 'excluded/not_live'), ('nExContentRules', 'excluded/content_rules'),
                      ('nExNotCaptured', 'excluded/not_captured'), ('nExSensitive', 'excluded/content_sensitivity')]:
        m[name] = fs.N(a + key, source='derived')
    m['nNotShopify'] = DN('fig2a_not_on_shopify/n')
    m['nNotDrawn'] = DN('fig2a_not_drawn/n')
    # every stage equals the one above minus the domains or stores of its side branches, as drawn (v7.1: the first
    # step too)
    v = lambda k: fs.derived(a + k)  # noqa: E731
    assert v('flagged') == v('tranco') - _f2('fig2a_not_on_shopify/n')
    assert v('verified') == v('flagged') - _f2('fig2a_not_drawn/n')
    assert v('live') == v('verified') - v('excluded/not_live')
    assert v('sample') == v('live') - v('excluded/content_rules')
    assert v('captured') == v('sample') - v('excluded/not_captured') - v('excluded/content_sensitivity')
    assert v('captured') == fs.stat('design/n_main') and v('tranco') == fs.stat('design/tranco_top_n')
    # the 38 stores between live and sampled fail the sample's eligibility rules (no product page, duplicate, adult,
    # aimed at children; Supplementary Table S-exclusions): the branch says 'not eligible', the caption gives the rules
    fe = fs.stat('design/funnel_excl')
    assert v('excluded/content_rules') == fe['live_to_sample'] == fe['no_product'] + fe['duplicate'] + fe['adult'] \
        + fe['child'], fe
    assert v('excluded/content_sensitivity') == fe['content_excluded']
    # panel b: the worked request, shortened to one line: the host (names the vendor), the carrier parameter and our
    # test code. The path (with the advertiser's account number) and the landing path (the product slug) are not
    # printed at all; the caption says what was dropped.
    w = 'fig2b_worked_request/'
    m['wrHost'] = tex_escape(STR(w + 'host'))
    m['wrParam'] = tex_escape(STR(w + 'carrier_param'))
    m['wrTestCode'] = tex_escape(STR(w + 'test_code'))
    assert fs.derived(w + 'vgroup') == 'Google' and fs.derived(w + 'vendor') == 'google_ads'
    assert fs.derived(w + 'origin') == 'lax_iframe'     # sent from the sandboxed iframe: the brick path's origin
    assert fs.derived(w + 'before_banner_ms') > 0         # sent before the banner was visible: lost consent (Fig 1c)
    assert fs.derived(w + 'test_code').endswith(fs.derived(w + 'load_id').split('__')[0])
    return m


# ---------------------------------------------------------------------------------------------------- measuring
_TW = {}


def tw_mm(s, size=None):
    """Rendered width (mm) of a one-line Arial string at `size` pt (default 7 pt). matplotlib embeds the same Arial as
    fontspec, so every TikZ box, column and gap is checked against measured widths, not guesses."""
    size = size or fs.FS['label']
    if (s, size) not in _TW:
        with fs.v7_context():
            f = fs.panel(120, 20)
            t = f.text(0, 0.5, s, fontsize=size)
            f.canvas.draw()
            _TW[(s, size)] = t.get_window_extent().width / f.dpi * 25.4
            fs.plt.close(f)
    return _TW[(s, size)]


def unescape(s):
    return s.replace(r'\&', '&').replace(r'\_', '_').replace(r'\#', '#').replace(r'\%', '%')


L7, L6 = fs.FS['label'], fs.FS['note']
CAP7 = L7 * fs.CAP_EM / fs.PT_PER_MM          # cap height of 7 pt Arial (mm): 1.77
CAP6 = L6 * fs.CAP_EM / fs.PT_PER_MM          # 6 pt: 1.52
PAD_X, PAD_Y, BOX_H = 2.4, 1.6, 6.0           # sciplot S.box: 2.4 x 1.6 mm padding, minimum height 6 mm (DESIGN_V7 7.2)
REG_IN = 2.4                                  # region name / content inset from a region edge (7.1)
GAP_SHORT = 0.6                               # connectors stop this short of what they enter (7.3)
TRIM = 2.2                                    # a level-1 frame keeps this much air to the cell's trim (as Fig 1a)

# ---------------------------------------------------------------------------------------------------- grid (mm)
# 190 mm wide, 6 mm gutters, no outer margin. Left column: a, the full height. Right column: b (hero) over c; c's axis
# spans exactly b's outer frame (shared left and right edges).
A_W = 66.0
R_X = A_W + fs.GUTTER_MM
R_W = fs.FIG_W_MM - R_X                       # 118

# ---------------------------------------------------------------------------------------------------- b (hero)
# Rows (mm from the cell top). Fig 1a's tiers: the page on top; below it, at the right, the pixel sandboxes with the web
# worker above the sandboxed iframe (Fig 1a's order, 3 mm apart as there); the crawler's bus enters between them.
B = {}
B['frame_top'] = 0.6
B['frame_name_base'] = B['frame_top'] + 3.7
B['page_top'] = B['frame_name_base'] + 2.4
B['page_name_base'] = B['page_top'] + 3.5
B['rowp_top'] = B['page_name_base'] + 1.8
B['rowp_bot'] = B['rowp_top'] + BOX_H
B['page_bot'] = B['rowp_bot'] + REG_IN
B['sbx_top'] = B['page_bot'] + 3.2            # the gap the page tap rises through
B['sbx_name_base'] = B['sbx_top'] + 3.5
B['roww_top'] = B['sbx_name_base'] + 1.8      # web worker
B['roww_bot'] = B['roww_top'] + BOX_H
B['rowi_top'] = B['roww_bot'] + 3.0           # sandboxed iframe
B['rowi_bot'] = B['rowi_top'] + BOX_H
B['sbx_bot'] = B['rowi_bot'] + REG_IN
B['frame_bot'] = B['sbx_bot'] + REG_IN
B['yw'] = (B['roww_top'] + B['roww_bot']) / 2
B['yi'] = (B['rowi_top'] + B['rowi_bot']) / 2
B['bus'] = (B['yw'] + B['yi']) / 2           # the bus enters the fork between the two sandboxes (Fig 1a's gate row)
B['note_base'] = B['bus'] - 1.5               # the bus note, above the bus with 1.5 mm to its baseline
B['req_base'] = B['frame_bot'] + 6.4          # baseline of the request line
B['brk_top'] = B['req_base'] + 1.15           # square brackets under the request's parts
B['brk_bot'] = B['brk_top'] + 0.7
B['key_base'] = B['brk_bot'] + 0.9 + CAP6     # their 6 pt muted keys
B_H = round(B['key_base'] + 1.3, 2)


def b_geometry(m):
    """Columns of b from measured text; asserts every fit (labels inside boxes, the fork clear of the region names and
    outlines, the bus note clear of the frame, the fork and the page, the brick drop inside the iframe and on the test
    code, the request line inside the cell)."""
    cr_w = max(tw_mm('Crawler'), tw_mm('DevTools Protocol', L6)) + 2 * PAD_X     # 'DevTools Protocol' on one line
    B['cr_x0'], B['cr_x1'] = 0.0, round(cr_w, 3)
    B['fx0'] = round(cr_w + 4.0, 3)                             # the browser frame (level 1)
    B['fx1'] = round(R_W - TRIM, 3)
    B['rx0'], B['rx1'] = B['fx0'] + REG_IN, B['fx1'] - REG_IN   # the page region spans the frame's width
    # one box width for all four boxes: the widest content (name + 3 mm + muted qualifier) plus the padding
    contents = [tw_mm('Cookie banner (CMP)'), tw_mm('Vendor tags'),
                tw_mm('Sandboxed iframe') + 3.0 + tw_mm('lax', L6), tw_mm('Web worker') + 3.0 + tw_mm('strict', L6)]
    W = max(contents) + 2 * PAD_X
    B['bw'] = round(W + 0.5, 1)
    # columns: the cookie banner at the page's left; the vendor tags at its right, directly above the sandbox column
    # (the sandbox region is right-aligned with the page region, as the right column of Fig 1a)
    B['xL'] = round(B['rx0'] + REG_IN + B['bw'] / 2, 3)
    B['xR'] = round(B['rx1'] - REG_IN - B['bw'] / 2, 3)
    B['sx1'] = B['rx1']
    B['sx0'] = round(B['xR'] - B['bw'] / 2 - REG_IN, 3)
    # the fork's spine rises midway between the page's two boxes (it taps the page, not a box) and stays left of the
    # sandbox region (Fig 1a: the fork stands 4.9 mm before the sandboxes)
    B['xs'] = round(((B['xL'] + B['bw'] / 2) + (B['xR'] - B['bw'] / 2)) / 2, 3)
    assert B['sx0'] - B['xs'] >= 3.5, ('b: the fork crowds the sandbox region', B['sx0'] - B['xs'])
    assert B['xs'] - (B['xL'] + B['bw'] / 2) >= 6.0, ('b: the page tap reads as a tap into the banner', B['xs'])
    assert B['xs'] - (B['xL'] + B['bw'] / 2) - ((B['xR'] - B['bw'] / 2) - B['xs']) < 0.01   # midway
    # the sandbox region's name sits in its headroom, clear of the worker branch entering from the left
    assert tw_mm('Pixel sandboxes') + REG_IN <= B['sx1'] - B['sx0'] - 2.0, 'b: sandbox name'
    # the bus note: centred over the bus between the frame's inset and the fork, with real air on all sides
    note_w = tw_mm('attached before any script runs', L6)
    B['xn'] = round((B['fx0'] + REG_IN + B['xs'] - 2.0) / 2, 3)
    assert B['xn'] - note_w / 2 >= B['fx0'] + REG_IN, 'b: bus note vs the frame'
    assert B['xn'] + note_w / 2 <= B['xs'] - 2.0, 'b: bus note vs the fork'
    assert B['note_base'] - CAP6 - B['page_bot'] >= 6.0, 'b: bus note vs the page region'
    assert B['bus'] - B['note_base'] >= 1.4, 'b: bus note vs the bus'
    # the request line: host / '/…&url=…&utm_campaign=' / test code, right-aligned with the browser frame
    head, mid, code = (unescape(x) for x in request_parts(m))
    B['req_w'] = tw_mm(head) + tw_mm(mid) + tw_mm(code)         # three nodes: no kerning across their joins
    B['req_x'] = round(B['fx1'] - B['req_w'], 3)
    # the brick drop: straight down from the sandboxed iframe's bottom onto the centre of the test code
    B['xD'] = round(B['req_x'] + tw_mm(head) + tw_mm(mid) + tw_mm(code) / 2, 3)
    ix0, ix1 = B['xR'] - B['bw'] / 2, B['xR'] + B['bw'] / 2
    assert ix0 + 6.0 <= B['xD'] <= ix1 - 2.0, ('b: the brick drop leaves the iframe off its box', B['xD'], ix0, ix1)
    assert B['req_x'] - 2.0 - tw_mm('Example request') >= 1.0, 'b: the request name runs off the cell'
    assert tw_mm('vendor', L6) + 1.0 <= tw_mm(head) and tw_mm('test code', L6) + 1.0 <= tw_mm(code), 'b: bracket keys'
    assert B['cr_x1'] + 2.0 < B['fx0'], 'b: crawler box vs frame'
    assert B['bus'] - 4.2 > 4.5, 'b: crawler box vs the letter zone'
    assert tw_mm('Shopify store in the browser') + REG_IN <= B['xR'] - B['fx0'], 'b: frame name'
    assert R_W - B['fx1'] >= TRIM - 1e-9, 'b: the frame outline must keep its air to the trim'
    for s in ('Cookie banner (CMP)', 'Vendor tags'):
        assert tw_mm(s) + 2 * PAD_X <= B['bw']
    return B


def request_parts(m):
    """The shortened request line in three parts: the host (bracket 'vendor'); '/…&' for the dropped path and
    parameters, the carrier parameter and 'utm_campaign='; then our test code (bracket 'test code', where the brick
    path lands)."""
    return (m['wrHost'], '/…\\&' + m['wrParam'] + '=…\\&utm\\_campaign=', m['wrTestCode'])


# ---------------------------------------------------------------------------------------------------- c (comparison)
# Lanes (mm from the cell top); time is s from each page's load event; the axis spans b's outer frame exactly. Decline's
# next page sits close under its first page (one arm, two loads); the other pitches leave room for the event names.
C = dict(ydef=7.0, pitch=7.4, pitch_next=5.0, mk=2.3, name=5.0, tick=1.5, end_tick=1.0, brk0=1.15, brk1=1.85,
         ev_lab=2.4, air=2.3)
C['ydec'] = C['ydef'] + C['pitch']
C['ynext'] = C['ydec'] + C['pitch_next']
C['ygpc'] = C['ynext'] + C['pitch']
C['yax'] = C['ygpc'] + 4.3                     # the time axis (bottom spine)
TICK_LEN = fs.TICK_LEN_PT / fs.PT_PER_MM       # 2.5 pt outward
TICK_PAD = 2.0 / fs.PT_PER_MM                  # 2 pt
C['tick_base'] = C['yax'] + TICK_LEN + TICK_PAD + CAP6
C['title_base'] = C['tick_base'] + 0.4 + 2.5 / fs.PT_PER_MM + CAP7
C_H = round(C['title_base'] + 0.9, 2)
C_TICKS = [0, 5, 10, 15, 20]                   # s; the axis ends at +20, past the reload (trace_fig2.py: structural)
C_TICKLABELS = ['0'] + ['+' + str(t) for t in C_TICKS[1:]]
C_AXIS_TITLE = 'Time from the page’s load event (s)'
TICK_WORD = {0: 'zero', 5: 'five', 10: 'ten', 15: 'fifteen', 20: 'twenty'}     # TeX macro names hold no digits


def c_geometry():
    """c's time scale: the medians and the protocol windows mapped onto b's frame width."""
    t = 'fig2c_timeline/'
    s = lambda k: mark(t + k + '/ms') / 1000.0   # noqa: E731
    T = dict(def_nav=-s('default_nav_to_load'), def_banner=-s('default_banner_before_load'),
             gpc_nav=-s('gpc_nav_to_load'), dec_nav=-s('decline_nav_to_load'),
             dec_click=s('decline_click_from_load'), dec_reload=s('decline_reload_from_load'),
             next_nav=-s('next_nav_to_load'))
    T['observe'] = float(mark_stat('design/observe_after_load_s'))         # Default and GPC: until 15 s after load
    T['next_observe'] = float(mark_stat('design/next_page_observe_s'))     # Decline's next page: 10 s after its load
    T['window'] = float(mark_stat('design/equal_window_s'))                # the compared window: 10 s from a load
    # Decline's banner is not drawn (one amber tick per arm: its consent moment); its median still orders the moments
    dec_banner = -_f2(t + 'decline_banner_before_load/ms') / 1000.0
    assert T['window'] <= T['next_observe'] <= T['observe'] < T['dec_reload'] < C_TICKS[-1]
    assert T['dec_nav'] < dec_banner < T['dec_click'] < T['dec_reload'] and T['def_nav'] < T['def_banner']
    assert T['dec_reload'] - T['dec_click'] >= T['observe']            # the first page is observed >= 15 s after the click
    C['left'], C['right'] = B['fx0'], B['fx1']                          # = b's outer frame (shared edges)
    lo = min(T['def_nav'], T['gpc_nav'], T['dec_nav'], T['next_nav'])
    hi = float(C_TICKS[-1])                                             # the axis ends on its last tick
    k = (C['right'] - C['left'] - C['air']) / (hi - lo)                 # mm per s; 2.3 mm of air before the first line
    C['k'] = k
    C['t_left'] = lo - C['air'] / k                                     # time at the left edge
    X = lambda tt: round(C['left'] + (tt - C['t_left']) * k, 3)         # noqa: E731
    C['X'] = {n: X(v) for n, v in T.items()}
    C['X'].update({f'tick_{TICK_WORD[v]}': X(v) for v in C_TICKS})
    C['X']['win'] = X(T['window'])
    C['X']['observe'] = X(T['observe'])
    C['X']['next_observe'] = X(T['next_observe'])
    assert abs(C['X']['tick_twenty'] - C['right']) < 0.01
    C['T'] = T
    # labels: event names centred above their ticks ('GPC signal' flag-style: it marks the line's start) stay clear of
    # each other, of the arm names and of the cell
    names_end = C['name'] + max(tw_mm('Default'), tw_mm('Decline'), tw_mm('GPC'), tw_mm('next page', L6))
    assert names_end + 1.5 <= C['left'], ('c: arm names run into the plot', names_end)
    for lab, x in (('banner visible', C['X']['def_banner']), ('Decline click', C['X']['dec_click'])):
        assert x - tw_mm(lab) / 2 >= names_end + 1.5, ('c: event label hits the arm names', lab)
    assert C['X']['gpc_nav'] - 0.4 >= names_end + 1.5
    # ... and each named tick is the only amber tick under its name
    assert C['X']['dec_click'] - tw_mm('Decline click') / 2 > C['X']['dec_nav'] + 0.5, 'c: click name vs line start'
    assert C['ygpc'] - C['ev_lab'] - CAP7 - (C['ynext'] + C['brk1']) >= 1.2, 'c: GPC label vs next-page bracket'
    assert C['ydec'] - C['ev_lab'] - CAP7 - (C['ydef'] + C['brk1']) >= 1.2, 'c: click label vs Default bracket'
    # the reload: a short NEUTRAL end tick at the end of Decline's first page, named 'reload' (6 pt muted) after it,
    # inside the axis and clear of the cell's right edge
    C['reload_lab_x'] = round(C['X']['dec_reload'] + 1.0, 3)
    assert C['reload_lab_x'] + tw_mm('reload', L6) <= C['right'] - 0.5, 'c: reload label vs the axis end'
    assert C['ynext'] - C['ydec'] >= 2 * C['end_tick'] + 2.0, 'c: reload tick vs the next page line'
    # one bracket is keyed ('compared window', 6 pt muted): the next page's, beside its end, where no line runs above
    # it (the next page stops at +10 s) and well off 'GPC signal''s baseline and x
    C['key_x'] = round(C['X']['win'] + 1.0, 3)
    C['key_base'] = round(C['ynext'] + C['brk1'] + CAP6 / 2, 3)
    assert C['X']['next_observe'] <= C['X']['win'] + 1e-6, 'c: the next page runs past its window'
    assert C['key_x'] + tw_mm('compared window', L6) <= C['right'] - 0.5, 'c: key vs the axis end'
    assert C['ygpc'] - C['ev_lab'] - C['key_base'] >= 2.0, 'c: key and GPC signal on one baseline'
    assert C['key_x'] - (C['X']['gpc_nav'] - 0.4 + tw_mm('GPC signal')) >= 0.25 * (C['right'] - C['left']), \
        'c: key and GPC signal read as one line'
    assert C['ygpc'] - C['tick'] - (C['key_base'] + 0.35) >= 1.0, 'c: key vs the GPC lane'
    assert C['key_base'] - CAP6 - C['ynext'] >= 0.8, 'c: key vs the next page line'
    assert C['left'] - 2.0 > 4.5 and C['ydef'] - C['ev_lab'] - CAP7 >= 1.0, 'c: letter zone and top'
    return C


# ---------------------------------------------------------------------------------------------------- a (population)
# Rows top to bottom inside three phase regions (outline only). y advances by these amounts (mm); the slack that is
# left over in the column is spread over the arrows between stages (STRETCH), so the last region ends at the
# figure's bottom. Every branch is a removal in one grammar: '<count> not <state>'.
A_ROWS = [
    ('region', 'Frame'),
    ('box', 'Tranco top list', 'nTranco'),
    ('branch', 'nNotShopify', 'not on Shopify'),
    ('box', 'DNS on Shopify', 'nFlagged'),
    ('end',),
    ('region', 'Draw'),
    ('branch', 'nNotDrawn', 'not drawn'),
    ('box', 'Checked', 'nVerified'),
    ('branch', 'nExNotLive', 'not live'),
    ('box', 'Live stores', 'nLive'),
    ('branch', 'nExContentRules', 'not eligible'),
    ('box', 'Sampled', 'nSample'),
    ('end',),
    ('region', 'Crawl'),
    ('branch', 'nExNotCaptured', 'not captured'),
    ('branch', 'nExSensitive', 'not eligible (content)'),
    ('box', 'Analysed', 'nCaptured'),
    ('end',),
]
A = dict(rx0=4.9, top=B['frame_top'], name_drop=3.7, gap_min=3.6, branch_dy=3.4, reg_gap=3.0)
A['rx1'] = A_W - 0.3


def a_geometry(m, fig_h):
    """Place a's rows; the stretchable gaps (box-to-box, box-to-branch, region-to-region arrows) share the slack."""
    A['bx0'] = A['rx0'] + REG_IN
    rows = [r for r in A_ROWS if r[0] == 'box']
    # one width for all boxes: the widest row (name, at least 3.2 mm of air, count) plus the padding, so that in every
    # row the name and the count read as two columns of the ledger, not one phrase
    A['bw'] = round(max(tw_mm(r[1]) + 3.2 + tw_mm(m[r[2]]) for r in rows) + 2 * PAD_X, 1)
    A['bx1'] = A['bx0'] + A['bw']
    A['xc'] = A['bx0'] + A['bw'] / 2
    A['xlab'] = A['bx1'] + 1.6
    for r in A_ROWS:
        if r[0] == 'branch':
            s = f"{m[r[1]]} {r[2]}"
            assert A['xlab'] + tw_mm(s, L6) <= A['rx1'] - 1.0, ('a: removal label overflows its region', s,
                                                                A['xlab'] + tw_mm(s, L6) - A['rx1'] + 1.0)
        if r[0] == 'region' and r is not A_ROWS[0]:          # the spine enters every later region through its name's row
            assert tw_mm(r[1]) + REG_IN < A['xc'] - A['rx0'] - 1.0, ('a: region name reaches the spine', r[1])
    # the three phase names differ in their first word (v7.1: 'Sampling frame' and 'Sampling' read as one)
    names = [r[1] for r in A_ROWS if r[0] == 'region']
    assert len({n.split()[0][:4] for n in names}) == len(names), names

    def place(stretch):
        y, items, open_ = A['top'], [], None
        prev = None                                   # kind of the previous placed element
        for r in A_ROWS:
            if r[0] == 'region':
                if prev == 'end':
                    y += A['reg_gap'] + stretch
                open_ = dict(kind='region', name=r[1], top=y, name_base=y + A['name_drop'])
                y += A['name_drop']
                prev = 'region'
            elif r[0] == 'box':
                y += (1.9 if prev == 'region' else (A['gap_min'] + stretch if prev == 'box' else
                                                     A['gap_min'] / 2 + stretch / 2))
                items.append(dict(kind='box', name=r[1], count=m[r[2]], top=y, bot=y + BOX_H))
                y += BOX_H
                prev = 'box'
            elif r[0] == 'branch':
                if prev == 'branch':
                    y += A['branch_dy']
                elif prev == 'region':
                    y += 2.6                          # a clear row below the phase name (its label cap 1.7 mm under)
                else:
                    y += A['gap_min'] / 2 + stretch / 2
                items.append(dict(kind='branch', y=y, text=f"{m[r[1]]} {r[2]}"))
                prev = 'branch'
            else:
                open_['bot'] = y + REG_IN
                items.append(open_)
                y = open_['bot']
                prev = 'end'
        return y, items

    end0, _ = place(0.0)
    n_stretch = 2                                     # region-to-region gaps (2) count once each ...
    n_stretch += sum(1 for a, b in zip(A_ROWS, A_ROWS[1:]) if a[0] == 'box' and b[0] == 'box')
    n_stretch += 0.5 * sum(1 for a, b in zip(A_ROWS, A_ROWS[1:]) if {a[0], b[0]} == {'box', 'branch'})
    stretch = (fig_h - 0.5 - end0) / n_stretch
    assert stretch >= 0, ('a: the flow does not fit the column', end0, fig_h)
    end, items = place(stretch)
    assert abs(end - (fig_h - 0.5)) < 1e-6, (end, fig_h)
    A['items'] = items
    A['stretch'] = stretch
    return A


# ---------------------------------------------------------------------------------------------------- output
DIGIT = {'0': 'Zero', '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five', '6': 'Six', '7': 'Seven',
         '8': 'Eight', '9': 'Nine'}


def mname(prefix, key):
    """TeX macro name for a layout key: 'cr_x0' -> 'BCrXZero' (camel case; TeX names hold no digits)."""
    n = prefix + re.sub(r'(?:^|_)(\w)', lambda g: g.group(1).upper(), key)
    return ''.join(DIGIT.get(ch, ch) for ch in n)


def write_layout(fig_h):
    L = dict(FigH=fig_h, PanelAW=A_W, PanelRX=R_X, PanelRW=R_W, PanelBH=B_H, PanelCY=B_H + fs.GUTTER_MM,
             PanelCH=C_H)
    # b
    for k in ('frame_top', 'frame_name_base', 'page_top', 'page_name_base', 'rowp_top', 'rowp_bot', 'page_bot',
              'sbx_top', 'sbx_name_base', 'roww_top', 'roww_bot', 'rowi_top', 'rowi_bot', 'sbx_bot', 'frame_bot', 'yw',
              'yi', 'bus', 'note_base', 'req_base', 'brk_top', 'brk_bot', 'key_base', 'cr_x0', 'cr_x1', 'fx0', 'fx1',
              'rx0', 'rx1', 'sx0', 'sx1', 'bw', 'xL', 'xR', 'xs', 'xn', 'xD', 'req_x'):
        L[mname('B', k)] = round(B[k], 3)
    # c
    for k in ('ydef', 'ydec', 'ynext', 'ygpc', 'yax', 'mk', 'name', 'tick', 'end_tick', 'brk0', 'brk1', 'ev_lab',
              'tick_base', 'title_base', 'left', 'right', 'key_x', 'key_base', 'reload_lab_x'):
        L[mname('C', k)] = round(C[k], 3)
    for n, x in C['X'].items():
        L[mname('CX', n)] = x
    # a
    L.update(Arx=A['rx0'], ArxR=A['rx1'], Abx=A['bx0'], AbxR=A['bx1'], Axc=A['xc'], Axlab=A['xlab'])
    assert L['PanelAW'] + fs.GUTTER_MM + L['PanelRW'] == fs.FIG_W_MM
    lines = ['% fig2_layout.tex -- GENERATED by scripts/make_fig2_panels.py (cell sizes and coordinates in mm, checked',
             '% against measured Arial widths); do not edit.']
    assert len(L) == len({k for k in L}) and all(re.fullmatch(r'[A-Za-z]+', k) for k in L), 'layout macro names'
    lines += [f'\\def\\{k}{{{v:g}}}' for k, v in L.items()]
    # c: the axis ticks and their labels (structural: trace_fig2.py allows exactly these, in c, at the tick size)
    ticks = [f"\\Tick{{{C['X']['tick_' + TICK_WORD[v]]}}}{{{lab}}}" for v, lab in zip(C_TICKS, C_TICKLABELS)]
    lines += ['\\def\\CTicks{%'] + [t + '%' for t in ticks] + ['}']
    # a: the rows as TikZ commands (\Region, \Stage, \Branch, \Link), in drawing order
    rows, boxes = [], [it for it in A['items'] if it['kind'] == 'box']
    for it in A['items']:
        if it['kind'] == 'region':
            rows.append(f"\\Region{{{it['top']:.3f}}}{{{it['bot']:.3f}}}{{{it['name_base']:.3f}}}{{{it['name']}}}")
    for it in A['items']:
        if it['kind'] == 'box':
            rows.append(f"\\Stage{{{it['top']:.3f}}}{{{it['name']}}}{{{it['count']}}}")
    for b0, b1 in zip(boxes, boxes[1:]):
        rows.append(f"\\Link{{{b0['bot']:.3f}}}{{{b1['top']:.3f}}}")
    for it in A['items']:
        if it['kind'] == 'branch':
            rows.append(f"\\Branch{{{it['y']:.3f}}}{{{it['text']}}}")
    lines += ['\\def\\ARows{%'] + [r + '%' for r in rows] + ['}']
    open(os.path.join(BUILD, 'fig2_layout.tex'), 'w').write('\n'.join(lines) + '\n')
    return L


def write_numbers(m):
    lines = ['% fig2_numbers.tex -- GENERATED by scripts/make_fig2_panels.py from stats.json and derived_numbers.json;',
             '% do not edit. The registry of every value is panels/fig2_numbers.csv.']
    lines += [f'\\newcommand{{\\{k}}}{{{v}}}' for k, v in m.items()]
    head, mid, code = request_parts(m)
    lines += [f'\\newcommand{{\\wrHead}}{{{head}}}', f'\\newcommand{{\\wrMid}}{{{mid}}}',
              f'\\newcommand{{\\wrCode}}{{{code}}}']
    open(os.path.join(BUILD, 'fig2_numbers.tex'), 'w').write('\n'.join(lines) + '\n')


def check_hero(fig_h):
    """DESIGN_V7 section 1: the hero panel (b) gets the most area, about 35-60 % of the figure's cells."""
    area = dict(a=A_W * fig_h, b=R_W * B_H, c=R_W * C_H)
    share = area['b'] / sum(area.values())
    assert area['b'] == max(area.values()) and 0.35 <= share <= 0.60, ('b is not the largest cell', area, share)
    return share


def check_composite(fig_h):
    """fig2.tex's cells and every panel canvas equal the constants here (panels are never rescaled); panels b and c
    print no digit outside the request's test code and c's tick labels (trace_fig2.py checks the PDF as well)."""
    tex = open(os.path.join(FIG2, 'fig2.tex')).read()
    assert '\\Panel {a}' in tex and '\\Panel {b}' in tex and '\\Panel {c}' in tex
    for f in ('fig2a_funnel', 'fig2b_instrumentation', 'fig2c_arms'):
        src = open(os.path.join(FIG2, 'tex', f + '.tex')).read()
        code = '\n'.join(re.sub(r'(?<!\\)%.*', '', ln) for ln in src.splitlines())
        assert re.search(r'\\PanelCanvas\{\\Panel(AW|RW)\}\{\\(FigH|PanelBH|PanelCH)\}', code), f
        texts = [t for t in re.findall(r'\{([^{}]*)\};', code) if not re.fullmatch(r'#\d', t)]
        assert not re.search(r'\d', ''.join(texts)), (f, 'prints a literal number: numbers come from the registry')
    assert fig_h <= fs.FIG_MAX_H_MM and 95.0 <= fig_h <= 150.0, fig_h


if __name__ == '__main__':
    fs.reset_registry()
    nums = numbers()
    b_geometry(nums)
    c_geometry()
    FIG_H = round(B_H + fs.GUTTER_MM + C_H, 2)
    a_geometry(nums, FIG_H)
    lay = write_layout(FIG_H)
    write_numbers(nums)
    check_composite(FIG_H)
    hero = check_hero(FIG_H)
    fs.write_registry(os.path.join(PANELS, 'fig2_numbers.csv'))
    print(f"layout: a {A_W:g} x {FIG_H:g} | b {R_W:g} x {B_H:g} over c {R_W:g} x {C_H:g}; figure 190 x {FIG_H:g} mm")
    print(f"  hero b: {100 * hero:.1f}% of the cell area (a {A_W * FIG_H:.0f}, b {R_W * B_H:.0f}, c {R_W * C_H:.0f} mm2)")
    print(f"  a: box {A['bw']:g} mm, labels from {A['xlab']:.1f} mm, stretch {A['stretch']:.2f} mm | b: box {B['bw']:g} "
          f"mm, columns {B['xL']:g} / {B['xR']:g}, fork {B['xs']:g}, frame {B['fx0']:g}-{B['fx1']:g}, request "
          f"{B['req_x']:.1f}-{B['req_x'] + B['req_w']:.1f} mm, drop {B['xD']:g} | c: {C['k']:.2f} mm/s")
    print('wrote build/fig2_layout.tex, build/fig2_numbers.tex and panels/fig2_numbers.csv')
