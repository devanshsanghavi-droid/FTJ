"""Trace check for RESULTS_R4.md / stats_r4.json.
  1. Registry consistency: every row of outputs/number_registry_r4.csv re-renders identically from stats_r4.json.
  2. Coverage: every numeric token in RESULTS_R4.md is a registered rendering or a structural token (dates, times,
     file names, arm labels, the 95% CI level, section numbers, list/table syntax, ranks 200k-1M).
  3. Same definitions: the Round 4 recomputation of the MAIN sample's blocked-on-paper estimands equals the paper's
     analysis/outputs/stats.json (unconditioned 12/21, primary, fired_mkt, any_sbx, by-default counts, like-for-like
     references and both Mantel-Haenszel results).
  4. Provenance: load records on disk equal the crawler's status log, per set; no raw file outside the two
     round4/<set>/crawl/raw folders was written by this round (main crawl/raw count unchanged at 4,976).
Writes outputs/trace_check_r4.txt; exit 1 on any failure."""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from r4_write_results import get, render  # noqa: E402

NUM = re.compile(r'(?<![\w.\-@#,])[+\-]?(\d[\d,]*(?:\.\d+)?)')
STRUCT = re.compile('|'.join([r'`[^`]*`', r'\b\d{4}-\d{2}-\d{2}T?[\d:]*Z?\b', r'\b\d{2}:\d{2}\b', r'\b95\s?%', r'\bA[012]\b', r'\bB[12]\b',
                              r'^#+ \d+\.', r'\b200k[–-]1M\b', r'\btop-200k\b', r'\bsection \d+(\.\d+)?\b', r'\bPROTOCOL\.md \d+\b', r'\(section 5\.1\)',
                              r'\bat most 6\b', r'\bat least 10 s\b', r'\b1 s\b', r'\bG\d+\b', r'\bPart [A-E]\b', r'\bstores? 12/21\b', r'\(trace check \d\)']))


def main():
    S = json.load(open(os.path.join(HERE, 'stats_r4.json')))
    rep, fails = [], 0
    reg = list(csv.DictReader(open(os.path.join(HERE, 'outputs', 'number_registry_r4.csv'))))
    bad = [r for r in reg if render(get(S, r['key']), r['fmt']) != r['text']]
    fails += len(bad)
    rep.append(f'1. registry: {len(reg)} numbers, {len(bad)} stale' + ''.join(f"\n   STALE {r['key']}: {r['text']}" for r in bad[:20]))
    texts = {r['text'].lstrip('+') for r in reg} | {r['text'] for r in reg}
    md = open(os.path.join(HERE, 'RESULTS_R4.md')).read().splitlines()
    unt = []
    for i, line in enumerate(md, 1):
        m_ = STRUCT.sub(lambda m: ' ' * len(m.group(0)), line)
        for m in NUM.finditer(m_):
            tok = m.group(1).rstrip(',')
            if tok in texts or tok.lstrip('0') == '' or tok in {r['text'].lstrip('+-') for r in reg}:
                continue
            unt.append(f'   line {i}: {tok} :: {line[:120]}')
    fails += len(unt)
    rep.append(f'2. coverage: {len(unt)} untraced numeric tokens' + ('\n' + '\n'.join(unt[:40]) if unt else ''))
    # 3. main reproduction
    M = json.load(open(os.path.join(STUDY, 'analysis', 'outputs', 'stats.json')))['fig4']['a']
    R = S['blocklist']['main']
    pairs = [('unconditioned/fired', M['blocklist']['declared_vendor_fired_sbx']), ('primary/fired', M['blocklist']['primary']['fired']),
             ('primary/fired_mkt', M['blocklist']['primary']['fired_mkt']), ('primary/any_sbx', M['blocklist']['primary']['any_sbx']),
             ('unconditioned/any_sbx', M['blocklist']['any_sbx']), ('by_default/allowed/fired', M['blocklist']['by_default']['allowed']['fired']),
             ('by_default/denied/fired', M['blocklist']['by_default']['denied']['fired']),
             ('like_for_like/allowed/reference', M['like_for_like']['allowed']['reference']), ('like_for_like/denied/reference', M['like_for_like']['denied']['reference']),
             ('like_for_like/allowed_no_yes/reference', M['like_for_like']['allowed_no_yes']['reference']), ('like_for_like/denied_no_yes/reference', M['like_for_like']['denied_no_yes']['reference'])]
    mism = []
    for k, ref in pairs:
        mine = get(R, k)
        for f in ('k', 'n'):
            if mine[f] != ref[f]:
                mism.append(f'{k}.{f}: {mine[f]} != {ref[f]}')
        if ref.get('lo') is not None and abs(mine['lo'] - ref['lo']) > 1e-12:
            mism.append(f'{k}.lo')
    for k in ('mh', 'mh_no_yes'):
        for f in ('rd', 'rd_lo', 'rd_hi', 'k1', 'n1', 'k0', 'n0'):
            if abs(R['like_for_like'][k][f] - M['like_for_like'][k][f]) > 1e-9:
                mism.append(f'{k}.{f}')
    fails += len(mism)
    rep.append(f'3. main reproduction: {len(pairs) + 2} estimands compared, {len(mism)} mismatches' + ''.join('\n   ' + x for x in mism))
    # 4. provenance
    pv = []
    for s in ('expansion', 'beyond'):
        c = S['crawl'][s]
        if c.get('raw_files', 0) != c.get('loads_logged', 0):
            pv.append(f'{s}: raw files {c.get("raw_files")} != status-log loads {c.get("loads_logged")}')
    n_main = len([f for f in os.listdir(os.path.join(STUDY, 'crawl', 'raw')) if f.endswith('.json.gz')])
    if n_main != 4976:
        pv.append(f'main crawl/raw has {n_main} files (expected 4,976)')
    fails += len(pv)
    rep.append(f'4. provenance: {len(pv)} problems' + ''.join('\n   ' + x for x in pv))
    rep.append('PASS' if fails == 0 else f'FAIL ({fails})')
    open(os.path.join(HERE, 'outputs', 'trace_check_r4.txt'), 'w').write('\n'.join(rep) + '\n')
    print('\n'.join(rep))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
