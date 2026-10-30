"""Write figures/v7/fig2/tableS_arms.tex: Supplementary Table S-arms (label tab:s-arms), the measurement arms drawn in
Fig 2c, with each arm's GPC signal, action, observed window and n (loads run, usable loads, stores analysed).
It replaces the v1 Fig 2b arms table (FIGURE_PLAN_v2.md, section 4: 'Fig 2b arms table -> 2C + Table S-arms').
v5: written inside figures/v5 (DESIGN_V5.md section 17: v5 scripts write figures/v5 only); integrating it into the
paper (paper/tables/tableS_arms.tex) is the separate integration step. The validation rows point to Fig 6d, where
v4's Fig 2d (agreement between loads) moved.

The file is a complete table float (caption + label), ready for \\input{tables/tableS_arms.tex} in paper/supplement.tex
(Note 'Sample and crawl details'); it uses the paper preamble's \\mkDefault, \\mkDecline, \\mkGPC, \\mkRepeat and \\code.
Every number is a placeholder filled from analysis/outputs/stats.json ({S:key}) or fig2/derived_numbers.json
({F:key}); the registry of rendered numbers goes to fig2/tableS_arms_numbers.csv (checked by check_fig2_numbers.py).

Run:  python3 figures/v7/fig2/scripts/make_table_arms.py      (build_fig2.sh runs it)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG2 = os.path.normpath(os.path.join(HERE, '..'))
STUDY = os.path.normpath(os.path.join(FIG2, '..', '..', '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG2, '..', 'style')))
import figstyle as fs  # noqa: E402

OUT = os.path.join(FIG2, 'tableS_arms.tex')
REG = os.path.join(FIG2, 'tableS_arms_numbers.csv')
F2 = json.load(open(os.path.join(FIG2, 'derived_numbers.json')))

TEMPLATE = r"""\begin{table}[!htbp]
\centering
\caption{Measurement arms (drawn in Fig.~2c). Every load used a new browser with a new temporary profile: Chromium's headless shell (version {S:checks/provenance/crawl/chromium_major}) in all arms but Brave (version {S:checks/provenance/crawl/brave_major}, also headless). Repeats: a seeded {S:design/repeat_fraction_pct}\% subsample; Brave: a seeded {S:design/brave_subsample}-store subsample. Loads run and usable loads include the {S:design/n_creator} creator-linked stores. Stores analysed: main-sample stores with usable loads in all three base arms (base arms), or in both loads of a comparison (validation rows: Default and GPC against their repeats, GPC against Brave; Fig.~6d). The arms are compared on equal {S:design/equal_window_s}~s windows: from the load event in Default and GPC, and on the next page in Decline (Fig.~5a).}
\label{tab:s-arms}
\small
\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{27mm}>{\raggedright\arraybackslash\hsize=1.2\hsize}X>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash\hsize=0.8\hsize}X@{\hspace{6pt}}r@{\hspace{6pt}}r@{\hspace{6pt}}r@{}}
\toprule
 & & & Window & Loads & Usable & Stores \\
Arm & GPC signal & Action & observed & run & loads & analysed \\
\midrule
Default \mkDefault{} & none & none; passive mouse-wheel scrolls from {F:tableS_arms/first_scroll_after_load_s}~s after the \code{load} event & until {S:design/observe_after_load_s}~s after the \code{load} event & {S:design/loads_by_arm/A0/run} & {S:design/loads_by_arm/A0/ok} & {S:design/n_main} \\[3pt]
Decline \mkDecline{} & none & waited for a visible banner and clicked its first-layer reject control (never Accept or settings); clicked on {S:fig5/decline/clicked_all} stores, worked on {S:fig5/decline/clicked}; no click without such a control & before the click; same page after the click; next page (same URL reloaded, new sandboxes) for {S:design/next_page_observe_s}~s after its \code{load} event & {S:design/loads_by_arm/A1/run} & {S:design/loads_by_arm/A1/ok} & {S:design/n_main} \\[3pt]
GPC \mkGPC{} & \code{Sec-GPC:~1} on every request; \code{navigator.globalPrivacyControl} injected into every frame and worker before its first script & as Default & as Default & {S:design/loads_by_arm/A2/run} & {S:design/loads_by_arm/A2/ok} & {S:design/n_main} \\
\addlinespace
Default repeat \mkRepeat{} & none & as Default & as Default & {S:design/loads_by_arm/A0r/run} & {S:design/loads_by_arm/A0r/ok} & {S:validation/A0_vs_A0r/n} \\
GPC repeat \mkRepeat{} & as GPC & as Default & as Default & {S:design/loads_by_arm/A2r/run} & {S:design/loads_by_arm/A2r/ok} & {S:validation/A2_vs_A2r/n} \\
Brave \mkRepeat{} & Brave's native GPC; Shields (tracker blocking) off & as Default & as Default & {S:design/loads_by_arm/V1/run} & {S:design/loads_by_arm/V1/ok} & {S:validation/A2_vs_V1/n} \\
\bottomrule
\end{tabularx}
\end{table}"""


def fill(m):
    kind, _, key = m.group(1).partition(':')
    if kind == 'S':
        return fs.N(key)
    if kind == 'F':
        name, _, sub = key.partition('/')
        v = fs._walk(F2[name]['value'], sub)
        s = fs.render(v, 'int')
        fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig2_derived', key=key, fmt='int', value=json.dumps(v)))
        return fs.typo(s)
    raise ValueError(kind)


if __name__ == '__main__':
    # consistency checks on the sources (the table would silently disagree with Figs 2c and 6d otherwise)
    lb = fs.stat('design/loads_by_arm')
    assert lb['A0']['run'] == lb['A1']['run'] == lb['A2']['run'] == fs.stat('design/n_planned')
    assert fs.stat('design/n_planned') == fs.stat('design/n_main_planned') + fs.stat('design/n_creator')
    assert lb['A0r']['run'] == lb['A2r']['run'] == fs.stat('design/repeat_planned')
    assert lb['V1']['run'] == fs.stat('design/brave_planned') == fs.stat('design/brave_subsample')
    fs.reset_registry()
    body = re.sub(r'\{((?:S|F):[^{}]+)\}', fill, TEMPLATE)
    assert not re.search(r'\{(?:S|F):', body), 'unfilled placeholder'
    head = ('% tableS_arms.tex -- GENERATED by figures/v7/fig2/scripts/make_table_arms.py from analysis/outputs/stats.json\n'
            '% and figures/v7/fig2/derived_numbers.json (registry: figures/v7/fig2/tableS_arms_numbers.csv); do not edit\n'
            '% by hand. Supplementary Table S-arms (label tab:s-arms): \\input{tables/tableS_arms.tex} in supplement.tex.\n')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w').write(head + body + '\n')
    fs.write_registry(REG)
    print(f'wrote {os.path.relpath(OUT, STUDY)} and {os.path.relpath(REG, STUDY)} ({len(fs._REG)} numbers)')
