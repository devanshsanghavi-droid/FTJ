#!/usr/bin/env python3
"""palette_gate.py -- the colour gate for one figure PDF (v6: binding ../RESTRAINT.md rule 6; v5 machinery kept).

v6 registry (figstyle.py): the semantic tokens LEAK #c65358 (= ACCENT, consent lost), HONOUR #5d769d, THIRD #b788ca,
EVENT #e8a33a; the sandbox fill SAND #3b4656; true-grey neutrals; the fixed vendor hexes; the ordinal ramps.
FAIL any semantic token in the same panel as a vendor hue (each sits within ~10 OKLab dE of one).

v5 grafts from the bake-off judges: (1) a manuscript-wide colour REGISTRY -- figures/colors.py, re-exported by
figstyle.py -- with one role per hue, checked against every colour actually drawn in the PDF; (2) the dataviz skill's
computable colour check (scripts/validate_palette.js) as a hard gate on the hues a figure uses.

What it does
  1. Walks the PDF (including every nested panel) with qa_check's content walker and lists every fill / stroke colour.
  2. Classifies each colour: ink / grey neutral, vendor hue, accent red, ordinal blue step, ordinal grey step.
     FAIL  a chromatic colour that is not in the registry (a new hue needs a registry entry and a validator run first);
     FAIL  an Okabe-Ito hue (figstyle.BANNED_HUES: each one sits on a vendor hue);
     FAIL  red (consent failed) in the same panel as a vendor hue.
  3. Runs validate_palette.js on the white print surface (--surface #ffffff):
     * the vendor hues present, in the fixed VENDOR_ORDER (adjacent pairs), when two or more are present;
     * the ordinal blue steps present, in ramp order, with --ordinal, when two or more are present.
     A validator exit status 1 FAILs unless --accept-validator "<reason>" names the secondary encoding that carries
     identity (e.g. 'vendor sub-rows + direct labels'); the reason is written into the report.
  4. Writes the report (default: palette_validation_<stem>.txt next to the PDF).

Usage
  python3 palette_gate.py FIG.pdf [--out FILE] [--accept-validator "reason"]
  VALIDATOR=/path/to/validate_palette.js overrides the validator search (default: the newest bundled dataviz skill).
Exit status 1 on any FAIL. A missing node / validator is a WARN (the registry checks still run).
"""
import argparse
import collections
import glob
import os
import shutil
import subprocess
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402


def _rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def chromatic(hx, tol=16):
    r, g, b = _rgb(hx)
    return max(r, g, b) - min(r, g, b) > tol


def near(hx, ref, tol=3):
    return max(abs(a - b) for a, b in zip(_rgb(hx), _rgb(ref))) <= tol


def classify(hx):
    for v in fs.VENDOR_ORDER:
        if near(hx, fs.VENDOR[v]):
            return 'vendor', v
    if near(hx, fs.ACCENT):
        return 'accent', 'LEAK brick (consent lost)'
    for k, c in fs.SEMANTIC.items():
        if k != 'LEAK' and near(hx, c):
            return 'semantic', k
    if near(hx, fs.SAND):
        return 'sandbox', 'SAND dark slate (sandbox fill)'
    skin = getattr(fs, 'SKIN', {})                              # sciplot clean skin: theme neutrals + token tints
    for k, c in sorted(skin.items(), key=lambda kv: max(abs(a - b) for a, b in zip(_rgb(hx), _rgb(kv[1])))):
        if near(hx, c):
            return 'skin', k                                    # the nearest skin colour (exact first)
    for i, c in enumerate(fs.ORD_BLUE):
        if near(hx, c):
            return 'ordinal_blue', i
    for c in fs.BANNED_HUES:
        if near(hx, c):
            return 'banned', c
    if not chromatic(hx):
        return 'neutral', hx
    return 'unknown', hx


def find_validator():
    v = os.environ.get('VALIDATOR')
    if v and os.path.exists(v):
        return v
    cands = glob.glob('/private/tmp/claude-*/bundled-skills/*/*/dataviz/scripts/validate_palette.js')
    return max(cands, key=os.path.getmtime) if cands else None


def run_validator(validator, hexes, extra):
    cmd = ['node', validator, ','.join(hexes), '--mode', 'light', '--surface', '#ffffff'] + extra
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode, (res.stdout + res.stderr).strip(), ' '.join(cmd[2:])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pdf')
    ap.add_argument('--out')
    ap.add_argument('--accept-validator', metavar='REASON')
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.pdf)),
                                'palette_validation_' + os.path.splitext(os.path.basename(a.pdf))[0] + '.txt')
    r = PdfReader(a.pdf)
    wk = qa.Walker(r)
    lines, fails, warns = [f'# palette gate (v6) for {os.path.basename(a.pdf)}'], [], []
    used = collections.defaultdict(set)
    for page in r.pages:
        wk.walk(page.get_contents(), page.get('/Resources'), [1, 0, 0, 1, 0, 0])
    for pnl, cnt in sorted(wk.colors.items()):
        kinds = collections.Counter()
        desc = []
        for hx in sorted(cnt):
            k, what = classify(hx)
            kinds[k] += 1
            used[k].add(what)
            desc.append(f'{hx} {k}' + (f' {what}' if k in ('vendor', 'accent', 'semantic', 'sandbox', 'ordinal_blue', 'skin')
                                        else ''))
            if k == 'unknown':
                fails.append(f'panel {pnl}: chromatic colour {hx} is not in the colour registry (figstyle.py)')
            if k == 'banned':
                fails.append(f'panel {pnl}: {hx} is an Okabe-Ito hue (banned in v5: collides with a vendor hue)')
        if (kinds['accent'] or kinds['semantic']) and kinds['vendor']:
            fails.append(f'panel {pnl}: a semantic token (LEAK / HONOUR / THIRD / EVENT) together with vendor hues')
        lines.append(f'colours [{pnl}]: ' + ', '.join(desc))
    validator = find_validator()
    node = shutil.which('node')
    jobs = []
    vend = [v for v in fs.VENDOR_ORDER if v in used['vendor']]
    if len(vend) >= 2:
        jobs.append(('vendor hues present, fixed order, adjacent pairs', [fs.VENDOR[v] for v in vend], []))
    blues = sorted(used['ordinal_blue'])
    if len(blues) >= 2:
        jobs.append(('ordinal blue steps present', [fs.ORD_BLUE[i] for i in blues], ['--ordinal']))
    if not jobs:
        lines.append('validator: not needed (fewer than two registry hues of one role; neutrals carry the encoding)')
    elif not (validator and node):
        warns.append('validator not run: ' + ('node not on PATH' if not node else 'validate_palette.js not found '
                                              '(set VALIDATOR=...)'))
    else:
        lines.append(f'validator: {validator}')
        for what, hexes, extra in jobs:
            rc, txt, cmd = run_validator(validator, hexes, extra)
            lines += ['', f'## {what}: {cmd}', txt, f'exit={rc}']
            if rc != 0:
                if a.accept_validator:
                    warns.append(f'validator FAIL accepted for "{what}": {a.accept_validator}')
                else:
                    fails.append(f'validator FAIL for {what} (fix the colours, or pass --accept-validator naming the '
                                 f'secondary encoding)')
    lines += [''] + [f'WARN {w}' for w in warns] + [f'FAIL {f}' for f in fails]
    lines.append('RESULT: ' + ('PASS' if not fails else f'FAIL ({len(fails)})'))
    open(out, 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(ln for ln in lines if ln.startswith(('colours', 'validator', 'WARN', 'FAIL', 'RESULT', '##'))))
    print('wrote', out)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
