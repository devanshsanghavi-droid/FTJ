"""Adaptive, resumable driver for screen_http.screen() (one process => one global rate limit).

Reads queues/plan.json before every batch, so strata can be added (e.g. W/BC after the DNS scan finishes) or
stopped without restarting. Items are interleaved round-robin across active strata (weights in plan.json).
Stop rules (plan.json): per-stratum cap on items screened, and optional `stop_when` targets such as
{"partytown_cmp": 90}: counts of candidate sites with that architecture AND a static CMP signature, over all
strata screened so far. A stratum is dropped once all of its stop_when targets are met or its cap is reached.
The random stratum R is only ever stopped at a batch boundary, so its screened set stays a prefix of the seeded order.
Usage: python screen_runner.py            (writes to raw/screen_results.jsonl; progress in raw/runner.log)
"""
import csv, json, os, shutil, sys, time
from concurrent.futures import ThreadPoolExecutor
import screen_http as S

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, 'queues', 'plan.json')
BATCH = 120


def load_done():
    done, counts = {}, dict(partytown_cmp=0, zaraz_cmp=0, zaraz_any=0, gateway_cmp=0, wix_cmp=0, bc_cmp=0, partytown_any=0, gateway_any=0)
    per = {}
    if os.path.exists(S.OUT):
        for l in open(S.OUT):
            try:
                r = json.loads(l)
            except Exception:
                continue
            done[r['domain']] = r
            per[r['stratum']] = per.get(r['stratum'], 0) + 1
            if r.get('outcome') != 'ok' or r.get('adult_flag') or r.get('child_flag_text'):
                continue
            cmp_ = bool(r.get('cmps'))
            if r['partytown']['any']:
                counts['partytown_any'] += 1; counts['partytown_cmp'] += cmp_
            if r['zaraz']['any']:
                counts['zaraz_any'] += 1; counts['zaraz_cmp'] += cmp_
            if r['gateway']['any']:
                counts['gateway_any'] += 1; counts['gateway_cmp'] += cmp_
            if r['wix']['platform']:
                counts['wix_cmp'] += cmp_
            if r['bigcommerce']['platform']:
                counts['bc_cmp'] += cmp_
    return done, counts, per


def main():
    log = open(os.path.join(HERE, 'raw', 'runner.log'), 'a')
    def say(*a):
        msg = time.strftime('%H:%M:%S ') + ' '.join(str(x) for x in a)
        print(msg, flush=True); log.write(msg + '\n'); log.flush()
    say('start UA', S.UA)
    queues = {}
    while True:
        plan = json.load(open(PLAN))
        if plan.get('pause'):
            say('paused by plan.json'); break
        done, counts, per = load_done()
        active = []
        for st, cfg in plan['strata'].items():
            qf = os.path.join(HERE, 'queues', cfg['queue'])
            if not os.path.exists(qf):
                continue
            mtime = os.path.getmtime(qf)
            if st not in queues or queues[st][0] != mtime:
                queues[st] = (mtime, [r for r in csv.DictReader(open(qf))])
            cap = cfg.get('cap')
            if cap is not None and per.get(st, 0) >= cap:
                continue
            sw = cfg.get('stop_when') or {}
            if sw and all(counts.get(k, 0) >= v for k, v in sw.items()):
                continue
            todo = [r for r in queues[st][1] if r['domain'] not in done]
            if cap is not None:
                todo = todo[:max(0, cap - per.get(st, 0))]
            if todo:
                active.append((st, cfg.get('weight', 1), todo))
        if not active:
            say('nothing left to screen; counts', json.dumps(counts), 'per', json.dumps(per)); break
        batch, seen = [], set()
        idx = {st: 0 for st, _, _ in active}
        while len(batch) < BATCH:
            added = False
            for st, wgt, todo in active:
                for _ in range(wgt):
                    while idx[st] < len(todo) and todo[idx[st]]['domain'] in seen:
                        idx[st] += 1
                    if idx[st] < len(todo) and len(batch) < BATCH:
                        batch.append(todo[idx[st]]); seen.add(todo[idx[st]]['domain']); idx[st] += 1; added = True
            if not added:
                break
        fb = shutil.disk_usage(HERE).free
        if fb < S.MIN_FREE:
            say('STOP: free disk %.2f GB below 1.2 GB' % (fb / 1e9)); break
        t0 = time.time()
        with open(S.OUT, 'a') as fh, ThreadPoolExecutor(S.WORKERS) as ex:
            for rec in ex.map(S.screen, batch):
                fh.write(json.dumps(rec) + '\n'); fh.flush()
        done, counts, per = load_done()
        say('batch %d in %.0fs | active %s | per %s | counts %s | free %.2fGB' % (
            len(batch), time.time() - t0, [a[0] for a in active], json.dumps(per), json.dumps(counts), shutil.disk_usage(HERE).free / 1e9))
    say('runner exit')


if __name__ == '__main__':
    main()
