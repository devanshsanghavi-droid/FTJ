"""Step 2: flag Shopify-hosted storefronts among the Tranco top-N via DNS only.

For each registrable domain d in the Tranco top N we resolve both d and www.d with the
system resolver (socket.getaddrinfo, AF_INET, AI_CANONNAME).  A host is flagged when
  * any returned IPv4 address lies in Shopify's ARIN-registered block 23.227.32.0/19
    (SHOPIFY-NET, org SHOPI-1; storefront edge addresses are in 23.227.38.0/24), or
  * its canonical name (end of the CNAME chain) is shop.myshopify.com or *.myshopify.com.
A domain is flagged when either its apex or its www host is flagged.

Politeness / robustness: at most CONCURRENCY lookups in flight (<= 50), results are
appended to dns_results.csv as they arrive, and the script resumes from that file.
"""
import csv, ipaddress, os, socket, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

BASE = os.path.dirname(os.path.abspath(__file__))
TRANCO = os.path.join(BASE, "raw", "tranco_L5PZ4_top1m.csv")
OUT = os.path.join(BASE, "raw", "dns_results.csv")
TOP_N = int(os.environ.get("TOP_N", "200000"))
CONCURRENCY = int(os.environ.get("CONC", "40"))
SHOPIFY_NETS = [ipaddress.ip_network("23.227.32.0/19")]
STOREFRONT_NET = ipaddress.ip_network("23.227.38.0/24")
socket.setdefaulttimeout(10)


def resolve(host):
    t0 = time.time()
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_CANONNAME)
        canon = ""
        ips = []
        for fam, typ, proto, cn, sa in infos:
            if cn and not canon:
                canon = cn
            if sa[0] not in ips:
                ips.append(sa[0])
        return host, canon.rstrip(".").lower(), ips, "", round(time.time() - t0, 3)
    except socket.gaierror as e:
        return host, "", [], "gaierror:%s" % e.errno, round(time.time() - t0, 3)
    except Exception as e:  # noqa
        return host, "", [], "err:%s" % type(e).__name__, round(time.time() - t0, 3)


def classify(canon, ips):
    in_block = any(any(ipaddress.ip_address(i) in n for n in SHOPIFY_NETS) for i in ips)
    in_sf = any(ipaddress.ip_address(i) in STOREFRONT_NET for i in ips)
    cname_sf = canon == "shop.myshopify.com" or canon.endswith(".myshopify.com")
    return int(in_block), int(in_sf), int(cname_sf)


def main():
    domains = []
    with open(TRANCO) as f:
        for row in csv.reader(f):
            r = int(row[0])
            if r > TOP_N:
                break
            domains.append((r, row[1].strip().lower()))
    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for row in csv.DictReader(f):
                done.add(row["host"])
    new = not os.path.exists(OUT)
    fh = open(OUT, "a", newline="")
    w = csv.writer(fh)
    if new:
        w.writerow(["rank", "domain", "host", "canon", "ips", "in_shopify_block", "in_storefront_24",
                    "cname_myshopify", "error", "elapsed_s"])
    todo = []
    for r, d in domains:
        for h in (d, "www." + d):
            if h not in done:
                todo.append((r, d, h))
    print("domains=%d hosts_total=%d already=%d todo=%d" % (len(domains), 2 * len(domains), len(done), len(todo)), flush=True)
    t0 = time.time()
    n = 0
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        it = iter(todo)
        pending = {}
        for _ in range(CONCURRENCY):
            try:
                r, d, h = next(it)
            except StopIteration:
                break
            pending[ex.submit(resolve, h)] = (r, d)
        while pending:
            fin, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for fu in fin:
                r, d = pending.pop(fu)
                host, canon, ips, err, el = fu.result()
                b, s, c = classify(canon, ips)
                w.writerow([r, d, host, canon, " ".join(ips), b, s, c, err, el])
                n += 1
                try:
                    r2, d2, h2 = next(it)
                    pending[ex.submit(resolve, h2)] = (r2, d2)
                except StopIteration:
                    pass
            if n % 2000 < len(fin):
                fh.flush()
                el = time.time() - t0
                print("%d/%d done, %.1f/s, elapsed %.0fs" % (n, len(todo), n / max(el, 1e-6), el), flush=True)
    fh.flush()
    fh.close()
    print("FINISHED n=%d elapsed=%.0fs" % (n, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
