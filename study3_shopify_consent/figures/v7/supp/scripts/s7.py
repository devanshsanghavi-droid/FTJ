"""Supplementary Figure S7 (v7) -- blocked on paper in the main sample: blocklist subsets, every blocklist entry by
route, the re-check, and the primary set's entries store by store.

Binding: figures/v7/DESIGN_V7.md (worked example figures/v7/fig1). fs.v7_context(): open L axes, Arial 7 / 6 pt,
markers 3.5 pt, uncapped 0.75 pt intervals, no panel titles. LEAK brick = sent an ad request before any choice (consent
lost), HONOUR slate = the comparison route (a page script, which the blocker reaches), greys = context. No vendor hues.
Numbers printed: the four cell counts of b and the four stage counts of c (as Fig 2a prints its stages); every other
number is in the caption.

Figure contract (DESIGN_V7 section 1): one claim -- vendors that a blocklist named still fired from Shopify's sandbox,
while the blocker acted only on the page.
  a  the population: the declared-blocked vendor's own sandboxed pixel fired before any choice (Default load), by
     blocklist subset; the primary set (CMP wrote no 'yes') on top, set apart, as a filled brick circle; the sensitivity
     subsets as open brick circles; Wilson 95% CIs.                                     stats fig4/a/blocklist
  b  the comparison of routes: left, the entries whose vendor has a configured sandboxed pixel as a 2 x 2 matrix of
     counts (sent from Shopify's sandbox: rows; from a page script: columns) in Fig S4a-c's matrix grammar (DESIGN_V7
     8.8) -- square cells split by two crossing 0.6 pt SP_AXIS rules, no frame, no fills, 7 pt counts, row title at
     the left, column title below -- except the sandbox-only cell, on the pale brick key-area tint (TINT LEAK: the
     entries whose consent was lost only through the sandbox);
     right, share of entries sent before any choice with Wilson 95% CIs (sandbox brick circle, page script slate
     square; set apart, entries without a configured sandboxed pixel, grey circle).
                                                         supp derived s7b_routes; tables/s7b_entries.csv
  c  the mechanism, re-checked: one load per blocklist store as Fig 2a's ledger -- a vertical spine of one-line boxes
     of one width (the stage left, its count right; 6 mm, 2.4 mm padding), the stores that leave a stage branching
     right as NEUTRAL 0.6 pt lines with flat ends, their count and reason in muted 6 pt (the count only when the
     registry holds it: supp derived s7c_recheck_nesting/excluded, see EXCL below); the last connector is the one
     brick accent (the leak).                    supp derived s7c_recheck_nesting; stats checks/recheck/blocker
  d  (hero; the instances) the primary set store by store: its entries whose vendor has a configured sandboxed pixel,
     as two store x vendor-group glyph matrices with one layout, each on the ground of the region it stands for (Fig 1:
     TINT SAND = Shopify's sandbox, TINT PAGE = the page's scripts), the region named inside at its top-left; brick =
     sent, SP_CONTEXT grey = sent nothing by that route (LIGHT would vanish on the SAND ground), blank = no entry;
     columns = stores grouped by the consent tool whose
     blocklist declared the vendor blocked (a rule under each group, its name below); rows = the vendor groups of every
     other figure (Amazon is in Reddit/other); the key above the right matrix.
                                     figures/v7/derived_numbers.json fig4a_routes/primary_no_yes; tables/s7b_entries.csv
Layout (mm; must equal figS7.tex, asserted): row 1 a | b (92 x H1); row 2 c | d (W_C, W_D x H2); 6 mm gutters; a's
plot, b's matrix and b's plot share their top and their bottom line (asserted). Drawn values are registered (fmt 'raw') in
panels/figS7_numbers.csv; printed counts are registered with their shown text; unit counts are asserted against the
registered derived numbers.
"""
import os

import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle

from s6 import (LW_DATA, MEW7, bb_mm, cat_y, check_alignment, check_composite, ci_h, dot, key_row, mark, mark_d,
                mark_sd, no_digits, no_overlaps, off_spines, plot_box, rows_ylim, share, sstyle, tw_mm, value_axis,
                wilson, within)
from supp_common import SD, SDv, SUPP, fs, finish, table, write_registry

LQ, RQ = '‘', '’'
G = fs.GUTTER_MM
W_A = W_B = 92.0
W_C, W_D = 68.0, 116.0
assert abs(W_A + G + W_B - fs.FIG_W_MM) < 1e-9 and abs(W_C + G + W_D - fs.FIG_W_MM) < 1e-9
H1, H2 = 40.0, 48.0
FIG_H = H1 + G + H2
CELLS = {'a': (0, 0, W_A, H1), 'b': (W_A + G, 0, W_B, H1), 'c': (0, H1 + G, W_C, H2), 'd': (W_C + G, H1 + G, W_D, H2)}
TOP1, PH1 = 5.5, 24.0                 # a, b: plot top and height (x axis at 29.5 mm)
R_PAD = 2.5
SENT, NONE = fs.LEAK, fs.SP_CONTEXT   # d: sent an ad request before any choice / sent nothing by that route (a grey
#                                       that stays visible on the TINT SAND ground: L* 77 against 93)
PRIMARY = sstyle(0)                   # filled brick circle: the primary estimate
VARIANT = sstyle(0, filled=False)     # open brick circle: a sensitivity subset
PRI = 'fig4a_routes/primary_no_yes'   # figures/v7/derived_numbers.json
BP = 25.4 / 72                        # mm per bp


def mm_canvas(fig, top=4.6):
    """An invisible axes over the panel below `top` whose data coordinates are panel mm (x right, y down)."""
    W, H = fs.size_mm(fig)
    ax = fs.axes_mm(fig, 0, top, W, H - top)
    ax.set_xlim(0, W)
    ax.set_ylim(H, top)
    ax.set_axis_off()
    return ax


def stealth(ax, p0, p1, color, lw, length_bp, width_bp, inset_bp, zorder=4):
    """A connector from p0 to p1 (mm canvas) ending in a Stealth head of the TikZ geometry (length x width, inset, bp)
    whose tip is at p1; the line stops inside the head."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    u = (p1 - p0) / np.hypot(*(p1 - p0))
    n = np.array([-u[1], u[0]])
    L, Wd, I = length_bp * BP, width_bp * BP, inset_bp * BP
    head = [p1, p1 - L * u + Wd / 2 * n, p1 - (L - I) * u, p1 - L * u - Wd / 2 * n]
    end = p1 - (L - I) * u
    ax.plot([p0[0], end[0]], [p0[1], end[1]], color=color, lw=lw, solid_capstyle='butt', zorder=zorder,
            clip_on=False)
    ax.add_patch(Polygon(np.array(head), closed=True, facecolor=color, edgecolor='none', zorder=zorder, clip_on=False))


# ------------------------------------------------------------------------------------------------ a
A_ROWS = [('primary/fired', f'Primary: CMP wrote no {LQ}yes{RQ}'),
          ('declared_vendor_fired_sbx', 'All blocklist stores'),
          ('cfg_stores/fired', 'Vendor’s pixel configured'),
          ('sens_excl_auto_grant/fired', f'No {LQ}yes{RQ} written by the CMP itself'),
          ('sens_excl_yes_before_pixel/fired', f'No {LQ}yes{RQ} before the pixel started')]


def panel_a():
    fig = fs.panel(W_A, H1)
    left = np.ceil(fs.INDENT_MM + max(tw_mm(lab, fs.FS['cat']) for _, lab in A_ROWS) + 1.6)
    pw = W_A - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP1, pw, PH1)
    ys = np.array([0.0, 1.5, 2.5, 3.5, 4.5])                      # the primary set on top, set apart
    pts = []
    for i, ((k, _), y) in enumerate(zip(A_ROWS, ys)):
        p, lo, hi = share(f'fig4/a/blocklist/{k}')
        st = PRIMARY if i == 0 else VARIANT
        ci_h(ax, y, lo, hi, st['color'])
        dot(ax, p, y, st)
        pts.append((p, y))
    cat_y(ax, ys, [lab for _, lab in A_ROWS])
    rows_ylim(ax, ys[0], ys[-1], PH1, pad_mm=2.0)
    value_axis(ax, 'x', 0, 100, 25, length_mm=pw)
    ax.set_xlabel('Blocked vendor fired (%)')                     # Fig 4a's measure and title
    off_spines(fig, ax, pts, 'a')
    within(fig, ax, 'a')
    no_overlaps(fig, 'a')
    no_digits(fig, 'a')
    finish(fig, 'figS7a_rows')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ b
B_M_LEFT = 12.0                       # matrix left edge (room for its y title and Yes / No)
B_CELL = PH1 / 2                      # square cells, 12 x 12 mm
B_RULE = dict(color=fs.SP_AXIS, lw=fs.V7_LW['axis'], solid_capstyle='butt', zorder=1)   # Fig S4a-c's crossing rules
B_ROWS = [('cfg/sandbox', 'cfg/n', 'Sandbox', sstyle(0)),
          ('cfg/page', 'cfg/n', 'Page script', sstyle(1)),
          ('nocfg/any', 'nocfg/n', 'Not configured', sstyle(0, color=fs.NEUTRAL))]


def panel_b():
    E = pd.read_csv(os.path.join(SUPP, 'tables', 's7b_entries.csv'))
    cfg = E[E.cfg_sandboxed]
    no = E[~E.cfg_sandboxed]
    R = 's7b_routes'
    assert len(E) == mark_sd(f'{R}/n_entries') and E.store_id.nunique() == mark_sd(f'{R}/n_blocklist_stores')
    assert len(cfg) == mark_sd(f'{R}/cfg/n') and int(cfg.f_sbx.sum()) == mark_sd(f'{R}/cfg/sandbox')
    assert int(cfg.f_page.sum()) == mark_sd(f'{R}/cfg/page') and len(no) == mark_sd(f'{R}/nocfg/n')
    assert int(no.f_any.sum()) == mark_sd(f'{R}/nocfg/any')
    fig = fs.panel(W_B, H1)
    # left: the 2 x 2 matrix of counts (rows: sent from the sandbox; columns: sent from a page script) in the matrix
    # grammar of Fig S4a-c (DESIGN_V7 8.8): square cells split by two crossing 0.6 pt SP_AXIS rules, no frame, no
    # fills but the key cell; 7 pt numerals because the counts are the point
    ax = fs.axes_mm(fig, B_M_LEFT, TOP1, 2 * B_CELL, PH1)
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    for s in ax.spines.values():
        s.set_visible(False)
    cells = {(True, True): 'both', (True, False): 'sandbox_only', (False, True): 'page_only', (False, False): 'neither'}
    for (sbx, page), key in cells.items():
        n = int((cfg.f_sbx.eq(sbx) & cfg.f_page.eq(page)).sum())
        assert n == mark_sd(f'{R}/cfg/{key}'), key
        x, y = (0.5 if page else 1.5), (1.5 if sbx else 0.5)
        # the key area: consent lost only through the sandbox (pale brick, never alpha); the other cells unfilled
        if key == 'sandbox_only':
            ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=fs.TINT['LEAK'], edgecolor='none', zorder=0))
        ax.text(x, y, SD(f'{R}/cfg/{key}'), ha='center', va='center_baseline', fontsize=fs.FS['label'],
                color=fs.SP_FG)
    ax.plot([0, 2], [1, 1], **B_RULE)                     # the two crossing rules (Fig S4a-c)
    ax.plot([1, 1], [0, 2], **B_RULE)
    ax.set_xticks([0.5, 1.5])
    ax.set_xticklabels(['Yes', 'No'], fontsize=fs.FS['cat'])
    ax.set_yticks([1.5, 0.5])
    ax.set_yticklabels(['Yes', 'No'], fontsize=fs.FS['cat'])
    ax.tick_params(length=0, pad=2.5)
    m_box = plot_box(fig, ax)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_color(fs.SP_FG)
    ax.set_xlabel('Page script sent', labelpad=2.0)
    ax.set_ylabel('Sandbox sent', labelpad=2.0)
    # right: share of entries sent before any choice (Wilson 95% CIs, drawn from the registered k and n)
    left = np.ceil(B_M_LEFT + 2 * B_CELL + 4.0 + max(tw_mm(r[2], fs.FS['cat']) for r in B_ROWS) + 1.6)
    pw = W_B - left - R_PAD
    ax2 = fs.axes_mm(fig, left, TOP1, pw, PH1)
    ys = np.array([0.0, 1.0, 2.4])                      # the entries without a configured pixel set apart
    pts = []
    for (kk, nk, _, st), y in zip(B_ROWS, ys):
        k, n = mark_sd(f'{R}/{kk}'), mark_sd(f'{R}/{nk}')
        lo, hi = wilson(k, n)
        ci_h(ax2, y, 100 * lo, 100 * hi, st['color'])
        dot(ax2, 100 * k / n, y, st)
        pts.append((100 * k / n, y))
    cat_y(ax2, ys, [r[2] for r in B_ROWS])
    rows_ylim(ax2, ys[0], ys[-1], PH1, pad_mm=2.6)
    value_axis(ax2, 'x', 0, 100, 25, length_mm=pw)
    ax2.set_xlabel('Sent before any choice (%)')
    off_spines(fig, ax2, pts, 'b right')
    x0 = bb_mm(fig, ax.yaxis.label)[0]
    assert x0 >= fs.INDENT_MM - 0.6, f'b: y title starts {x0:.2f} mm from the edge'
    within(fig, ax2, 'b right')
    b_box = plot_box(fig, ax2)
    assert abs(m_box[2] - b_box[2]) < 1e-9 and abs(m_box[3] - b_box[3]) < 1e-9, 'b: matrix and plot misaligned'
    no_overlaps(fig, 'b')
    no_digits(fig, 'b', allowed=tuple(t.get_text() for t in ax.texts))
    finish(fig, 'figS7b_units')
    return plot_box(fig, ax2)


# ------------------------------------------------------------------------------------------------ c
# Fig 2a's ledger (DESIGN_V7 8.10): one-line stage boxes (name left, count right), one shared width, on one spine;
# the stores that leave a stage branch right between two boxes, flat-ended, '<count> <reason>' in muted 6 pt.
C_STEPS = [('stores', 'Blocklist stores re-checked', None),
           ('active', 'Blocker active in the page', ('not_active', 'not active')),
           ('declared_tag_neutralized', 'Blocked vendor’s tag neutralised', ('not_neutralised', 'not neutralised')),
           ('neutralized_and_sbx', 'Its sandboxed pixel still sent', ('sent_nothing', 'sent nothing'))]
C_X0, C_TOP = fs.INDENT_MM, 5.4                  # box left; first box top (= d's ground top)
C_PADX, C_BOX_H = 2.4, 6.0                       # DESIGN_V7 7.2 / Fig 2a: 2.4 mm padding, 6 mm one-line boxes
C_NUM_GAP = 2.4                                  # min. white between a stage name and its count (Fig 2a)
C_SHORT = 0.6                                    # connectors stop this far short of the box they enter
C_LAB_DX = 1.8                                   # branch label: this far right of the boxes (Fig 2a's xlab)
# The exclusion counts are the differences of the nested stages. They are printed only when the supp registry holds
# them (derive_supp_numbers.py: s7c_recheck_nesting/excluded/{not_active, not_neutralised, sent_nothing}), so every
# printed number stays a registered rendering; until then the branches carry their reason only.
EXCL = SDv('s7c_recheck_nesting').get('excluded')


def panel_c():
    bl = 'checks/recheck/blocker'
    N = 's7c_recheck_nesting'
    assert mark_sd(f'{N}/nested') is True
    vals = [mark_sd(f'{N}/{k}') for k, _, _ in C_STEPS]
    assert vals == sorted(vals, reverse=True) and len(set(vals)) == len(vals), 'c: the stages are nested and shrink'
    assert vals[0] == mark(f'{bl}/stores') and vals[1] == mark(f'{bl}/active/k')
    assert vals[2] == mark(f'{bl}/stores_declared_tag_neutralized') and vals[3] == mark(f'{bl}/stores_neutralized_and_sbx')
    if EXCL is not None:      # each stage equals the one above minus its branch (as Fig 2a asserts)
        for i in range(1, len(C_STEPS)):
            assert vals[i - 1] - vals[i] == mark_sd(f'{N}/excluded/{C_STEPS[i][2][0]}'), C_STEPS[i]
    fig = fs.panel(W_C, H2)
    ax = mm_canvas(fig)
    nums = [SD(f'{N}/{k}') for k, _, _ in C_STEPS]
    w = round(max(tw_mm(lab, fs.FS['cat']) for _, lab, _ in C_STEPS) + C_NUM_GAP
              + max(tw_mm(n, fs.FS['cat']) for n in nums) + 2 * C_PADX + 0.2, 1)      # one shared width (a column)
    xc = C_X0 + w / 2                                                          # the spine
    x_lab = C_X0 + w + C_LAB_DX                                                # branch labels start here
    gap = (H2 - 0.5 - C_TOP - len(C_STEPS) * C_BOX_H) / (len(C_STEPS) - 1)     # the boxes fill the column
    assert gap >= 3.6, 'c: Fig 2a keeps at least 3.6 mm between two boxes'
    for i, (k, lab, br) in enumerate(C_STEPS):
        top = C_TOP + i * (C_BOX_H + gap)
        ax.add_patch(FancyBboxPatch((C_X0, top), w, C_BOX_H, boxstyle='round,pad=0,rounding_size=0.5',
                                    facecolor=fs.SURFACE, edgecolor=fs.SP_AXIS, linewidth=fs.V7_LW['axis'], zorder=2))
        yb = top + C_BOX_H / 2
        ax.text(C_X0 + C_PADX, yb, lab, ha='left', va='center_baseline', fontsize=fs.FS['cat'], color=fs.SP_FG,
                zorder=3)
        ax.text(C_X0 + w - C_PADX, yb, nums[i], ha='right', va='center_baseline', fontsize=fs.FS['cat'],
                color=fs.SP_FG, zorder=3)
        if i:
            y0, y1 = top - gap, top - C_SHORT
            if i == len(C_STEPS) - 1:          # the leak: the one brick accent (1.0 pt, the larger Stealth head)
                stealth(ax, (xc, y0), (xc, y1), fs.LEAK, LW_DATA, 4.25, 3.4, 1.2)
            else:
                stealth(ax, (xc, y0), (xc, y1), fs.SP_AXIS, fs.V7_LW['axis'], 3.4, 2.8, 0.9)
            # the stores that leave this stage branch right from the spine, flat-ended (NEUTRAL 0.6 pt, as Fig 2a)
            ym = top - gap / 2 - 0.4
            ax.plot([xc, x_lab - 1.0], [ym, ym], color=fs.NEUTRAL, lw=fs.V7_LW['axis'], solid_capstyle='butt',
                    zorder=1)
            text = br[1] if EXCL is None else f'{SD(f"{N}/excluded/{br[0]}")} {br[1]}'
            t = ax.text(x_lab, ym, text, ha='left', va='center_baseline', fontsize=fs.FS['note'], color=fs.SP_MUTED)
            assert bb_mm(fig, t)[1] <= W_C - 0.3, ('c: a branch label leaves the panel', text)
    if EXCL is None:
        print('S7c: the exclusion counts are not in the supp registry yet (s7c_recheck_nesting/excluded); '
              'branches drawn with their reason only')
    no_overlaps(fig, 'c')
    no_digits(fig, 'c', allowed=tuple(t.get_text() for t in ax.texts))
    finish(fig, 'figS7c_recheck')


# ------------------------------------------------------------------------------------------------ d
CMP_LABEL = {'pandectes': 'Pandectes', 'onetrust': 'OneTrust', 'cookiebot': 'Cookiebot'}
D_SQ, D_PITCH, D_GROUP_GAP = 3.2, 3.8, 2.0      # cell side, cell pitch (rows and columns), gap between tools (mm)
D_TOP = 5.4                                      # ground top (the key sits above, right)
D_PAD, D_BAND = 1.6, 5.0                         # ground padding around the cells; band for the region name (mm)
D_BETWEEN = 4.5                                  # gap between the two grounds (mm)
REGIONS = (('sandbox', 'f_sbx', 'Shopify’s sandbox', fs.TINT['SAND']),
           ('page', 'f_page', 'Page scripts', fs.TINT['PAGE']))


def panel_d():
    E = pd.read_csv(os.path.join(SUPP, 'tables', 's7b_entries.csv'))
    ent = E[E.cfg_sandboxed & E.primary].copy()
    ref = {k: mark_d(f'{PRI}/{k}') for k in ('n', 'n_stores', 'sandbox', 'page', 'both', 'neither_route')}
    assert (len(ent), ent.store_id.nunique(), int(ent.f_sbx.sum()), int(ent.f_page.sum()),
            int((ent.f_sbx & ent.f_page).sum()), int((~ent.f_sbx & ~ent.f_page).sum())) == \
        (ref['n'], ref['n_stores'], ref['sandbox'], ref['page'], ref['both'], ref['neither_route'])
    assert not ent.duplicated(['store_id', 'vgroup']).any(), 'd: two entries of one vendor group on one store'
    assert set(ent.vgroup) <= set(fs.VENDOR_ORDER)
    pairs = table('fig4c_declared_blocked_pairs.csv')
    assert pairs.groupby('store_id').cmp.nunique().max() == 1
    cmp_of = pairs.drop_duplicates('store_id').set_index('store_id').cmp.to_dict()
    groups_v = [v for v in fs.VENDOR_ORDER if v in set(ent.vgroup)]      # the vendor groups of every other figure
    assert sorted(ent[ent.vgroup == 'Reddit/other'].vendor.unique()) == ['amazon_ads'], 'caption: Amazon in Reddit/other'
    cell = {(r.store_id, r.vgroup): r for r in ent.itertuples()}
    stores = sorted(ent.store_id.unique())
    tools = sorted({cmp_of[s] for s in stores}, key=lambda c: (-sum(cmp_of[s] == c for s in stores), c))

    def score(s):
        es = ent[ent.store_id == s]
        return (-int(es.f_sbx.sum()), -int(es.f_page.sum()), -len(es), s)
    cols, gx = [], D_PAD
    for g in tools:
        for s in sorted([s for s in stores if cmp_of[s] == g], key=score):
            cols.append((s, g, gx))
            gx += D_PITCH
        gx += D_GROUP_GAP
    g_w = gx - D_GROUP_GAP - (D_PITCH - D_SQ) + D_PAD                 # ground width (mm)
    cells_h = (len(groups_v) - 1) * D_PITCH + D_SQ
    g_h = D_BAND + cells_h + D_PAD                                    # ground height (mm)
    fig = fs.panel(W_D, H2)
    ax = mm_canvas(fig)
    lab_w = max(tw_mm(v, fs.FS['cat']) for v in groups_v)
    x_left = np.ceil(fs.INDENT_MM + lab_w + 2.0)
    assert x_left + 2 * g_w + D_BETWEEN <= W_D - 0.5, 'd: the matrices leave the panel'
    y_cells = D_TOP + D_BAND
    for j, (route, flag, name, ground) in enumerate(REGIONS):
        x0 = x_left + j * (g_w + D_BETWEEN)
        # the region's ground (Fig 1's grounds: darker grey = the sandbox, light grey = the page), square, no outline,
        # under every mark; its name inside at the top-left in muted 7 pt
        ax.add_patch(Rectangle((x0, D_TOP), g_w, g_h, facecolor=ground, edgecolor='none', zorder=0.5))
        ax.text(x0 + D_PAD, D_TOP + D_BAND - 1.6, name, ha='left', va='baseline', fontsize=fs.FS['label'],
                color=fs.SP_MUTED)
        k = 0
        for s, g, cx in cols:
            for i, v in enumerate(groups_v):
                e = cell.get((s, v))
                if e is None:
                    continue                                           # no entry: blank
                sent = bool(getattr(e, flag))
                k += sent
                ax.add_patch(Rectangle((x0 + cx, y_cells + i * D_PITCH), D_SQ, D_SQ,
                                       facecolor=SENT if sent else NONE, edgecolor='none', linewidth=0, zorder=2))
        assert k == ref[route]
        # the consent tool under its columns: a 0.6 pt rule under each group, its name below (7 pt)
        for g in tools:
            xg = [cx for s, gg, cx in cols if gg == g]
            a0, a1 = x0 + min(xg), x0 + max(xg) + D_SQ
            yr = D_TOP + g_h + 1.4
            ax.plot([a0, a1], [yr, yr], color=fs.SP_AXIS, lw=fs.V7_LW['axis'], solid_capstyle='butt', zorder=2)
            ax.text((a0 + a1) / 2, yr + 1.0, CMP_LABEL.get(g, g), ha='center', va='top', fontsize=fs.FS['cat'],
                    color=fs.SP_FG)
    for i, v in enumerate(groups_v):                                    # the vendor groups, once, at the left
        ax.text(x_left - 1.6, y_cells + i * D_PITCH + D_SQ / 2, v, ha='right', va='center_baseline',
                fontsize=fs.FS['cat'], color=fs.SP_FG)
    # the key, above the right ground, right-aligned to it
    x_right = x_left + 2 * g_w + D_BETWEEN
    key_row(fig, x_right, D_TOP - 1.7, [('square', SENT, 'Sent'), ('square', NONE, 'Not sent')], gap=2.6)
    assert D_TOP + g_h + 1.4 + 1.0 + 3.0 <= H2 - 0.5, 'd: the tool names leave the panel'
    no_overlaps(fig, 'd')
    no_digits(fig, 'd')
    finish(fig, 'figS7d_matrix')
    return g_w, g_h


if __name__ == '__main__':
    check_composite('figS7.tex', CELLS, FIG_H)
    fs.reset_registry()
    with fs.v7_context():
        boxes = dict(a=panel_a(), b=panel_b())
        panel_c()
        panel_d()
    check_alignment(boxes, ['ab'])
    write_registry('figS7')
    print(f'S7 panels written (figure 190 x {FIG_H:g} mm)')
