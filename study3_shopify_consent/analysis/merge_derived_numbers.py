"""Merge the v2 figures' derived numbers into the analysis provenance.

The v2 figure scripts compute a few numbers that stats.json does not hold (for example the Fig. 4A entry routes or the
Fig. 5C race bins). Each is recorded, with its value, script and inputs, in a derived_numbers.json next to its figure
(figures/v2/derived_numbers.json, figures/v2/<fig>/derived_numbers.json). This script copies them, unchanged, into
  outputs/stats.json                       under 'derived_v2' -> <folder> -> <name> (the value, plus any top-level k / n),
                                           so paper/check_numbers.py (which walks stats.json) and numreg keys can reach them;
  outputs/derived_numbers_provenance.json  one record per number: source file and its sha256, script, inputs, definition,
                                           check, and whether the script file exists.
analysis/trace_check.py (check 4) verifies that both are in sync with the figure folders. Idempotent; run by run_all.sh
after checks.py. It never computes or edits a number.
"""
import glob
import hashlib
import json
import os
import sys

from common import OUT, STUDY, dump

V2 = os.path.join(STUDY, 'figures', 'v2')
PROV = os.path.join(OUT, 'derived_numbers_provenance.json')
KEEP_TOP = ('k', 'n')          # numeric fields some entries carry next to 'value' (e.g. graphical abstract k of n)


def sources():
    files = [os.path.join(V2, 'derived_numbers.json')] + sorted(glob.glob(os.path.join(V2, '*', 'derived_numbers.json')))
    return [f for f in files if os.path.exists(f)]


def tag(fn):
    d = os.path.basename(os.path.dirname(fn))
    return 'shared' if d == 'v2' else d


def collect():
    """(values, provenance) exactly as they should appear in stats.json and the provenance file."""
    values, prov = {}, {}
    for fn in sources():
        raw = open(fn, 'rb').read()
        data = json.loads(raw)
        t = tag(fn)
        values[t] = {}
        for name, e in data.items():
            if not isinstance(e, dict) or 'value' not in e:
                raise SystemExit(f'{fn}: entry {name} has no value record')
            v = {'value': e['value']}
            v.update({k: e[k] for k in KEEP_TOP if k in e})
            values[t][name] = v
            script = e.get('script', '')
            prov[f'{t}/{name}'] = {
                'source': os.path.relpath(fn, STUDY), 'sha256': hashlib.sha256(raw).hexdigest(),
                'script': script, 'script_exists': bool(script) and os.path.exists(os.path.join(STUDY, script)),
                'inputs': e.get('inputs', []), 'definition': e.get('definition', ''), 'check': e.get('check', ''),
                'stats_key': f'derived_v2/{t}/{name}/value'}
    return values, prov


def main():
    values, prov = collect()
    sp = os.path.join(OUT, 'stats.json')
    stats = json.load(open(sp))
    stats['derived_v2'] = values
    dump(stats, "stats.json")
    json.dump(prov, open(PROV, 'w'), indent=1)
    missing = [k for k, p in prov.items() if not p['script_exists']]
    print(f'merge_derived_numbers: {len(prov)} derived numbers from {len(values)} files -> stats.json[derived_v2], '
          f'{os.path.relpath(PROV, STUDY)}; scripts missing: {missing or "none"}')
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
