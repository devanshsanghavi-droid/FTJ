"""Step 2b: turn raw DNS results into the flagged sampling frame, with a seeded random draw order.

Output raw/frame_flagged.csv: rank, domain, bucket, fetch_host, apex_flag, www_flag, apex_ips, www_ips,
apex_canon, www_canon, in_storefront_24, draw_order (random permutation within bucket, seed SEED).
Also writes raw/dns_summary.json with counts per bucket.
"""
import csv, json, os, random
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DNS = os.path.join(BASE, "raw", "dns_results.csv")
OUT = os.path.join(BASE, "raw", "frame_flagged.csv")
SUMMARY = os.path.join(BASE, "raw", "dns_summary.json")
SEED = 20260925
TOP_N = 200000
BUCKETS = [(1, 10000, "1-10k"), (10001, 50000, "10k-50k"), (50001, 100000, "50k-100k"), (100001, 200000, "100k-200k")]
# Shopify's own corporate / platform domains are not merchant storefronts.
PLATFORM = {"shopify.com", "myshopify.com", "shopify.dev", "shopify.ca", "shopify.co.uk", "shopify.in", "shopify.com.au",
            "shopify.de", "shopify.fr", "shopify.jp", "shop.app", "shopifycloud.com", "shopifycdn.com", "shopifysvc.com",
            "shopifyapps.com", "shopifypreview.com", "shopifykloud.com", "shopifycs.com", "shopify.plus", "myshopify.io",
            "shopify.engineering", "shopify.io", "shopifystatus.com", "shopifyinbox.com", "shopify.email"}


def bucket(rank):
    for lo, hi, name in BUCKETS:
        if lo <= rank <= hi:
            return name
    return None


def main():
    rows = defaultdict(dict)
    n_hosts = 0
    resolved = set()
    errs = Counter()
    with open(DNS) as f:
        for r in csv.DictReader(f):
            n_hosts += 1
            d = r["domain"]
            key = "www" if r["host"].startswith("www.") and r["host"] != d else "apex"
            rows[d][key] = r
            rows[d]["rank"] = int(r["rank"])
            if r["ips"]:
                resolved.add(d)
            if r["error"]:
                errs[r["error"]] += 1
    frame = []
    per_bucket_all = Counter()
    per_bucket_resolved = Counter()
    per_bucket_flag = Counter()
    platform_dropped = []
    for d, rr in rows.items():
        rank = rr["rank"]
        if rank > TOP_N:
            continue
        b = bucket(rank)
        per_bucket_all[b] += 1
        if d in resolved:
            per_bucket_resolved[b] += 1
        a, w = rr.get("apex", {}), rr.get("www", {})
        af = int(a.get("in_shopify_block", "0") == "1" or a.get("cname_myshopify", "0") == "1")
        wf = int(w.get("in_shopify_block", "0") == "1" or w.get("cname_myshopify", "0") == "1")
        if not (af or wf):
            continue
        if d in PLATFORM:
            platform_dropped.append(d)
            continue
        per_bucket_flag[b] += 1
        frame.append({"rank": rank, "domain": d, "bucket": b, "fetch_host": d if af else "www." + d,
                      "apex_flag": af, "www_flag": wf, "apex_ips": a.get("ips", ""), "www_ips": w.get("ips", ""),
                      "apex_canon": a.get("canon", ""), "www_canon": w.get("canon", ""),
                      "in_storefront_24": int(a.get("in_storefront_24") == "1" or w.get("in_storefront_24") == "1"),
                      "cname_myshopify": int(a.get("cname_myshopify") == "1" or w.get("cname_myshopify") == "1")})
    rng = random.Random(SEED)
    by_b = defaultdict(list)
    for r in sorted(frame, key=lambda x: x["rank"]):
        by_b[r["bucket"]].append(r)
    out = []
    for b in [x[2] for x in BUCKETS]:
        lst = by_b[b]
        idx = list(range(len(lst)))
        rng.shuffle(idx)
        for order, i in enumerate(idx):
            lst[i]["draw_order"] = order
        out.extend(sorted(lst, key=lambda x: x["draw_order"]))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    summ = {"tranco_list_id": "L5PZ4", "top_n": TOP_N, "dns_hosts_queried": n_hosts,
            "domains_in_top_n": sum(per_bucket_all.values()), "domains_with_any_A": len(resolved),
            "dns_errors": dict(errs), "platform_domains_dropped": platform_dropped,
            "flagged_total": len(frame),
            "flagged_apex_only": sum(1 for r in frame if r["apex_flag"] and not r["www_flag"]),
            "flagged_www_only": sum(1 for r in frame if r["www_flag"] and not r["apex_flag"]),
            "flagged_both": sum(1 for r in frame if r["www_flag"] and r["apex_flag"]),
            "flagged_in_storefront_24": sum(r["in_storefront_24"] for r in frame),
            "flagged_cname_myshopify": sum(r["cname_myshopify"] for r in frame),
            "per_bucket": {b: {"domains": per_bucket_all[b], "resolved": per_bucket_resolved[b], "flagged": per_bucket_flag[b]}
                           for b in [x[2] for x in BUCKETS]}, "seed": SEED}
    json.dump(summ, open(SUMMARY, "w"), indent=2)
    print(json.dumps(summ, indent=2))


if __name__ == "__main__":
    main()
