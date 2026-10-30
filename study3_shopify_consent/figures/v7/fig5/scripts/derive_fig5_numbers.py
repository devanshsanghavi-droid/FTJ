"""Derived numbers for Figure 5 (v2) that neither analysis/outputs/stats.json nor figures/v7/derived_numbers.json holds.

Only one block is new here: the 100 ms bin counts behind the Fig 5C race histograms (FIGURE_PLAN_v2.md section 6,
"still to derive at build time: the Fig 5C 100 ms bin counts"). They are computed from the committed analysis tables
with exactly the selection of figures/v7/scripts/derive_numbers.py (block fig5c_race_per_sandbox), and every total is
asserted against stats.json (fig5.d) and the shared derived record, so any drift fails loudly.

Writes figures/v7/fig5/derived_numbers.json (value, definition, script, inputs, check). Never reads the raw crawl.
Run from anywhere:  python3 figures/v7/fig5/scripts/derive_fig5_numbers.py
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG5 = os.path.normpath(os.path.join(HERE, '..'))                       # figures/v7/fig5
V2 = os.path.normpath(os.path.join(FIG5, '..'))                         # figures/v2
ROOT = os.path.normpath(os.path.join(V2, '..', '..'))                   # study3_shopify_consent
OUT = os.path.join(ROOT, 'analysis', 'outputs')
DST = os.path.join(FIG5, 'derived_numbers.json')
SCRIPT = 'figures/v7/fig5/scripts/derive_fig5_numbers.py'

S = json.load(open(os.path.join(OUT, 'stats.json')))
DV2 = json.load(open(os.path.join(V2, 'derived_numbers.json')))
RACE = DV2['fig5c_race_per_sandbox']['value']

BIN_MS = 100
LO_MS, HI_MS = RACE['deny']['clip_lo_ms'], RACE['deny']['clip_hi_ms']      # -3000, +1000 (the plan's axis)
EDGES = np.arange(LO_MS, HI_MS + BIN_MS, BIN_MS)                            # 41 edges, 40 bins of 100 ms

# the selection of derive_numbers.py (fig5c_race_per_sandbox): third-party sandboxes that declare 'marketing'
sc = pd.read_csv(os.path.join(OUT, 'sandbox_creations.csv'), low_memory=False, dtype={'pixel_id': str},
                 usecols=['load_id', 't_ms', 'kind', 'pixel_api', 'declares_marketing'])
f5d = pd.read_csv(os.path.join(OUT, 'fig5d.csv'))
sc3 = sc[sc.declares_marketing & (sc.pixel_api.astype(str) != 'shopify-pixel') & (sc.kind != 'open_main_thread_pixel')]

D = {}
val = {}
rows = {}
for ch in ('deny', 'grant'):
    L = f5d[f5d.change == ch][['load_id', 't_update']]
    j = sc3.merge(L, on='load_id')
    lag = (j.t_ms - j.t_update).to_numpy(float)
    # v4 raster (Fig 5c): one row per load, one tick per sandbox; rows sorted by the load's first sandbox start
    j = j.assign(lag=lag)
    per = [(lid, sorted(int(round(v)) for v in g.lag)) for lid, g in j.groupby('load_id', sort=True)]
    per.sort(key=lambda r: (r[1][0], r[0]))
    assert all(float(v) == v for v in lag), ch                     # whole milliseconds: the ints are exact
    assert len(per) == S['fig5']['d'][ch]['loads'] == RACE[ch]['loads'], ch
    assert sum(len(r[1]) for r in per) == S['fig5']['d'][ch]['pixels'], ch
    assert sum(v < 0 for r in per for v in r[1]) == S['fig5']['d'][ch]['pixels_before'], ch
    rows[ch] = dict(loads=[r[0] for r in per], lags_ms=[r[1] for r in per], n_loads=len(per),
                    sandboxes=int(sum(len(r[1]) for r in per)))
    inside = lag[(lag >= LO_MS) & (lag <= HI_MS)]
    # bins are [lo, lo + 100) except the last, which is closed; a lag of exactly 0 ms counts as "after" (as in fig5.d)
    counts, _ = np.histogram(inside, bins=EDGES)
    before = lag < 0
    c_before, _ = np.histogram(inside[inside < 0], bins=EDGES)
    c_after, _ = np.histogram(inside[inside >= 0], bins=EDGES)
    n_below, n_above = int((lag < LO_MS).sum()), int((lag > HI_MS).sum())
    # checks against stats.json fig5.d and the shared derived record
    assert len(lag) == S['fig5']['d'][ch]['pixels'] == RACE[ch]['sandboxes'], ch
    assert int(before.sum()) == S['fig5']['d'][ch]['pixels_before'] == RACE[ch]['before'], ch
    assert n_below == RACE[ch]['n_below_clip'] and n_above == RACE[ch]['n_above_clip'], ch
    assert int(counts.sum()) + n_below + n_above == len(lag), ch
    assert float(np.median(lag)) == RACE[ch]['median_lag_ms'], ch
    assert int(c_before.sum() + c_after.sum()) == int(counts.sum())
    val[ch] = dict(bin_ms=BIN_MS, lo_ms=LO_MS, hi_ms=HI_MS, left_edges_ms=[int(e) for e in EDGES[:-1]],
                   before=[int(v) for v in c_before], after=[int(v) for v in c_after],
                   n_in_axis=int(counts.sum()), n_below_clip=n_below, n_above_clip=n_above,
                   max_bin=int(counts.max()), max_bin_left_edge_ms=int(EDGES[int(np.argmax(counts))]),
                   sandboxes=int(len(lag)))

D['fig5c_race_bins'] = dict(
    value=val,
    definition="Fig 5C histograms: third-party sandboxes declaring 'marketing' in loads where a CMP wrote marketing "
               "'no' (deny) or 'yes' (grant) without a click, counted per 100 ms bin of lag = sandbox start minus the "
               "consent write, on the axis -3 s to +1 s. 'before' = lag < 0 (drawn red for 'no'), 'after' = lag >= 0. "
               "Sandboxes beyond the axis are the edge counts n_below_clip / n_above_clip.",
    script=SCRIPT,
    inputs=['analysis/outputs/sandbox_creations.csv', 'analysis/outputs/fig5d.csv',
            'figures/v7/derived_numbers.json:fig5c_race_per_sandbox'],
    check='per change: bins + edge counts == fig5.d.<change>.pixels; lag < 0 == fig5.d.<change>.pixels_before; '
          'edge counts and median equal fig5c_race_per_sandbox')

D['fig5c_race_loads'] = dict(
    value=rows,
    definition="Fig 5c raster (v4): the same sandboxes as fig5c_race_bins, grouped by load. One row per load where a "
               "CMP wrote marketing 'no' (deny) or 'yes' (grant) without a click; lags_ms = every third-party "
               "'marketing' sandbox's start minus the consent write (ms, ascending). Rows are sorted by the load's "
               "first sandbox start (ties by load id).",
    script=SCRIPT,
    inputs=['analysis/outputs/sandbox_creations.csv', 'analysis/outputs/fig5d.csv'],
    check='per change: rows == fig5.d.<change>.loads; ticks == fig5.d.<change>.pixels; '
          'ticks with lag < 0 == fig5.d.<change>.pixels_before')

with open(DST, 'w') as f:
    json.dump(D, f, indent=1)
for ch in ('deny', 'grant'):
    v = val[ch]
    print(ch, 'in-axis', v['n_in_axis'], 'below', v['n_below_clip'], 'above', v['n_above_clip'], 'max bin', v['max_bin'],
          '@', v['max_bin_left_edge_ms'])
    print('  before', v['before'])
    print('  after ', v['after'])
print('wrote', DST)
