"""Number registry: every number written into RESULTS.md / takeaways.md goes through N(), which
renders it from a key in outputs/stats.json and records (text, key, value) so trace_check.py can
verify each printed number against the saved outputs."""
import csv
import json
import os

from common import OUT

_REG = []
_STATS = None


def stats():
    global _STATS
    if _STATS is None:
        _STATS = json.load(open(os.path.join(OUT, 'stats.json')))
    return _STATS


def get(key):
    cur = stats()
    for part in key.split('/'):
        part = part.replace('~1', '/')  # JSON-pointer style escape for keys that contain '/'
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def render(v, f):
    if f == 'int':
        return f'{int(round(v)):,}'
    if f == 'pct0':
        return f'{100 * v:.0f}'
    if f == 'pct1':
        return f'{100 * v:.1f}'
    if f == 'pct2':
        return f'{100 * v:.2f}'
    if f.startswith('f'):
        return f'{v:.{int(f[1:])}f}'
    if f == 'raw':
        return str(v)
    raise ValueError(f)


def N(key, f='int'):
    v = get(key)
    s = render(v, f)
    _REG.append(dict(text=s, key=key, fmt=f, value=v))
    return s


def P(key, f='pct1'):
    """A Wilson/bootstrap record {p, lo, hi, k, n}: 'p% (95% CI lo–hi)'."""
    return f"{N(key + '/p', f)}% (95% CI {N(key + '/lo', f)}–{N(key + '/hi', f)})"


def KN(key):
    """'k/n' from a record."""
    return f"{N(key + '/k')}/{N(key + '/n')}"


def KNP(key, f='pct1'):
    return f"{KN(key)} ({P(key, f)})"


def save(name):
    fn = os.path.join(OUT, name)
    with open(fn, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['text', 'key', 'fmt', 'value'])
        w.writeheader()
        for r in _REG:
            w.writerow(dict(r, value=json.dumps(r['value'])))
    return fn


def reset():
    _REG.clear()
