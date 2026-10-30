"""Round 4 / B1 expansion, step 1: DNS flag of Tranco L5PZ4 ranks 200,001-1,000,000.

Reuses sample/dns_scan.py unchanged (its resolve() and classify(): same resolver, same Shopify
block 23.227.32.0/19, same myshopify CNAME rule, apex OR www flagged).  Differences from the
main-sample scan, both for this stratum only:
  * ranks 200,001..1,000,000 of the SAME list (L5PZ4, already on disk as sample/raw/tranco_L5PZ4_top1m.csv);
  * domains are resolved in a seeded random permutation (SEED) instead of rank order, so that the
    screening step can start on a uniformly random prefix of the frame while the scan is still running.
    The scan still covers every domain; the frame is complete when it finishes.
Output (compact, resumable): raw/dns_ext.csv
  perm, rank, domain, host, ok, in_block, in_sf, cname_sf, canon (only when flagged), ips (only when flagged), error
At most CONC (<= 40) lookups in flight, as in the main scan.
"""
import csv, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.normpath(os.path.join(HERE, "..", "..", "sample"))
sys.path.insert(0, SAMPLE)
import dns_scan  # noqa: E402  (resolve, classify)

TRANCO = os.path.join(SAMPLE, "raw", "tranco_L5PZ4_top1m.csv")
OUT = os.path.join(HERE, "raw", "dns_ext.csv")
LO, HI = 200001, 1000000
SEED = 20260926
CONC = min(int(os.environ.get("CONC", "40")), 40)


def load_domains():
    doms = []
    with open(TRANCO) as f:
        for row in csv.reader(f):
            r = int(row[0])
            if r < LO:
                continue
            if r > HI:
                break
            doms.append((r, row[1].strip().lower()))
    rng = random.Random(SEED)
    idx = list(range(len(doms)))
    rng.shuffle(idx)
    return [(p, doms[i][0], doms[i][1]) for p, i in enumerate(idx)]


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    perm = load_domains()
    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for row in csv.DictReader(f):
                done.add(row["host"])
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="")
    w = csv.writer(fh)
    if new:
        w.writerow(["perm", "rank", "domain", "host", "ok", "in_block", "in_sf", "cname_sf", "canon", "ips", "error"])
    todo = [(p, r, d, h) for p, r, d in perm for h in (d, "www." + d) if h not in done]
    print("list=L5PZ4 ranks=%d-%d domains=%d seed=%d hosts_total=%d already=%d todo=%d conc=%d"
          % (LO, HI, len(perm), SEED, 2 * len(perm), len(done), len(todo), CONC), flush=True)
    t0 = time.time()
    n = 0
    with ThreadPoolExecutor(max_workers=CONC) as ex:
        it = iter(todo)
        pending = {}
        for _ in range(CONC):
            try:
                p, r, d, h = next(it)
            except StopIteration:
                break
            pending[ex.submit(dns_scan.resolve, h)] = (p, r, d)
        while pending:
            fin, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for fu in fin:
                p, r, d = pending.pop(fu)
                host, canon, ips, err, _el = fu.result()
                b, s, c = dns_scan.classify(canon, ips)
                flag = b or c
                w.writerow([p, r, d, host, int(bool(ips)), b, s, c, canon if flag else "", " ".join(ips) if flag else "", err])
                n += 1
                try:
                    p2, r2, d2, h2 = next(it)
                    pending[ex.submit(dns_scan.resolve, h2)] = (p2, r2, d2)
                except StopIteration:
                    pass
            if n % 5000 < len(fin):
                fh.flush()
                el = time.time() - t0
                print("%d/%d done, %.1f/s, elapsed %.0fs" % (n, len(todo), n / max(el, 1e-6), el), flush=True)
    fh.flush()
    fh.close()
    print("FINISHED n=%d elapsed=%.0fs" % (n, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
