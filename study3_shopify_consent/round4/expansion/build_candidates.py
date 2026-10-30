"""Round 4 / B1 expansion, step 3: frame summary, exact-prefix draw, candidates.csv and funnel.json.

Design: the frame is every DNS-flagged Shopify domain (apex or www; Shopify platform domains dropped) of
Tranco L5PZ4 ranks 200,001-1,000,000. Its seeded random permutation (dns_scan_ext.py, seed 20260926) is the
draw order. The drawn set is the SHORTEST PREFIX of that order that holds TARGET stratum stores; screened
domains after it are marked overdraw_not_in_sample (as in the main sample). Each drawn domain has inclusion
probability n/N, so every candidate gets the design weight N/n.

Stratum ("blocklist stores"): a verified Shopify Online Store storefront (same eligibility rules as the main
sample) whose Pandectes, OneTrust or Cookiebot configuration publishes a readable blocklist that names at
least one advertising vendor (crawl/vendor_endpoints.json) as blocked at least after a refusal, and for which
blocking before any choice for a California visitor is either declared (Pandectes: 'yes') or can only be
determined at run time (OneTrust active groups, Cookiebot consent state: 'unknown'). Stores whose published
configuration declares that the list is NOT applied before a choice in California (Pandectes v4 default not
blocked; v5 California not in the strict opt-in regions) are listed separately and are not to be measured.
"""
import csv, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sample"))
import build_frame  # noqa: E402

TARGET = int(os.environ.get("TARGET", "250"))
DNS = os.path.join(HERE, "raw", "dns_ext.csv")
RES = os.path.join(HERE, "raw", "screen_results.jsonl")
N_DOMAINS_TOTAL = 800000


def load_frame():
    """Compact read of raw/dns_ext.csv: per perm -> [rank, domain, apex(ok,flag,sf,cname) or None, www(...) or None]."""
    dom = {}
    with open(DNS) as f:
        rd = csv.reader(f)
        next(rd)
        for row in rd:
            if len(row) < 11:
                continue
            p, rank, d, host = int(row[0]), int(row[1]), row[2], row[3]
            e = dom.get(p)
            if e is None:
                e = dom[p] = [rank, d, None, None]
            v = (row[4] == "1", row[5] == "1" or row[7] == "1", row[6] == "1", row[7] == "1")
            e[3 if (host.startswith("www.") and host != d) else 2] = v
    k = -1
    while (k + 1) in dom and dom[k + 1][2] is not None and dom[k + 1][3] is not None:
        k += 1
    st = Counter()
    flagged = []
    for p in range(k + 1):
        rank, d, a, w = dom[p]
        st["domains"] += 1
        if a[0] or w[0]:
            st["resolved"] += 1
        af, wf = a[1], w[1]
        if not (af or wf):
            continue
        if d in build_frame.PLATFORM:
            st["platform_dropped"] += 1
            continue
        st["flagged"] += 1
        st["flagged_both" if af and wf else ("flagged_apex_only" if af else "flagged_www_only")] += 1
        st["flagged_in_storefront_24"] += int(a[2] or w[2])
        st["flagged_cname_myshopify"] += int(a[3] or w[3])
        lo = 200 + 100 * ((rank - 200001) // 100000)
        st["flagged_rank_%dk-%dk" % (lo, lo + 100)] += 1
        flagged.append((p, rank, d))
    return st, flagged, k + 1


def main():
    st, flagged, n_prefix_domains = load_frame()
    dns_complete = n_prefix_domains == N_DOMAINS_TOTAL
    N = st["flagged"] if dns_complete else round(st["flagged"] / n_prefix_domains * N_DOMAINS_TOTAL)
    R = {}
    for line in open(RES):
        r = json.loads(line)
        R[r["domain"]] = r
    # within-expansion duplicates: same Shopify.shop, keep the lowest perm
    first_shop = {}
    for r in sorted(R.values(), key=lambda x: x["perm"]):
        if r.get("stage") == "eligible" and r.get("myshopify"):
            s = r["myshopify"].lower()
            if s in first_shop:
                r["stage"] = "dup_expansion"
                r["dup_of_perm"] = first_shop[s]
            else:
                first_shop[s] = r["perm"]

    def cls(r):
        if r.get("stage") != "eligible":
            return r.get("stage")
        if not r.get("blocklist_readable"):
            return "eligible_no_blocklist"
        if not r.get("in_stratum"):
            return "blocklist_not_prechoice_ca"
        pu = r.get("product_url") or ""
        if pu and not (r.get("product_allowed_plain") or r.get("product_allowed_tagged")):
            return "stratum_product_robots_disallowed"
        return "CANDIDATE"

    # exact prefix
    order = []
    n_cand = 0
    end = None
    gaps = 0
    for i, (p, rank, d) in enumerate(flagged):
        r = R.get(d)
        if r is None:
            gaps += 1
            break
        c = cls(r)
        order.append((i, p, rank, d, r, c))
        if c == "CANDIDATE":
            n_cand += 1
            if n_cand >= TARGET:
                end = i + 1
                break
    reached = end is not None
    if end is None:
        end = len(order)
    drawn = order[:end]
    n_drawn = len(drawn)
    weight = N / n_drawn if n_drawn else float("nan")
    drawn_domains = {x[3] for x in drawn}
    overdraw = [r for d, r in R.items() if d not in drawn_domains]

    fun = Counter(c for *_, c in drawn)
    stage = Counter(r.get("stage") for *_, r, _c in drawn)
    lost = sum(1 for *_, r, _c in drawn if r.get("stage") == "lost_not_refetched")
    fetched = sum(1 for *_, r, _c in drawn if r.get("status") is not None) + lost
    http200 = sum(1 for *_, r, _c in drawn if r.get("status") == 200)
    elig = [r for *_, r, _c in drawn if r.get("stage") == "eligible"]
    tgt = Counter(k for r in elig for k in (r.get("target_cmps") or []))
    any_tgt = sum(1 for r in elig if r.get("target_cmps"))
    readable = [r for r in elig if r.get("blocklist_readable")]
    rd_by_cmp = Counter(k for r in readable for k in r.get("blocklist_cmps") or [])
    pre = Counter(r.get("prechoice_ca") for r in readable)
    cands = [(i, p, rank, d, r) for i, p, rank, d, r, c in drawn if c == "CANDIDATE"]

    # ---- candidates.csv
    cols = ["store_id", "domain", "rank", "cmp", "blocklist_readable", "product_url", "weight",
            "draw_order", "perm", "final_host", "prechoice_ca", "ad_vendors_blocklisted", "ad_vendors_blocked_prechoice_ca",
            "cmps_detected", "pandectes_version", "pandectes_blocker_active", "pandectes_geo_only", "onetrust_autoblock", "onetrust_shopify_app",
            "cookiebot_blockingmode", "cookiebot_shopify_app", "product_url_source", "product_allowed_plain", "product_allowed_tagged",
            "age_gate_hint", "served_title", "screened_utc"]
    rows = []
    for j, (i, p, rank, d, r) in enumerate(cands, 1):
        pdx = r.get("pandectes") or {}
        ot = r.get("onetrust") or {}
        cb = r.get("cookiebot") or {}
        rows.append({
            "store_id": "E%04d" % j, "domain": d, "rank": rank, "cmp": "|".join(r.get("blocklist_cmps") or []),
            "blocklist_readable": r.get("blocklist_readable"), "product_url": r.get("product_url") or "", "weight": round(weight, 4),
            "draw_order": i, "perm": p, "final_host": r.get("final_host"), "prechoice_ca": r.get("prechoice_ca"),
            "ad_vendors_blocklisted": "|".join(r.get("ad_vendors_blocklisted") or []),
            "ad_vendors_blocked_prechoice_ca": "|".join(r.get("ad_vendors_blocked_prechoice_ca") or []),
            "cmps_detected": "|".join(sorted((r.get("cmps_static") or {}).keys())),
            "pandectes_version": pdx.get("version", ""), "pandectes_blocker_active": pdx.get("blocker_active", ""),
            "pandectes_geo_only": "|".join(pdx.get("v4_geo_only") or []),
            "onetrust_autoblock": int(bool(ot.get("autoblock_url"))) if ot else "", "onetrust_shopify_app": int(bool(ot.get("shopify_app"))) if ot else "",
            "cookiebot_blockingmode": cb.get("blockingmode", ""), "cookiebot_shopify_app": int(bool(cb.get("shopify_app"))) if cb else "",
            "product_url_source": r.get("product_url_source") or "none",
            "product_allowed_plain": r.get("product_allowed_plain", ""), "product_allowed_tagged": r.get("product_allowed_tagged", ""),
            "age_gate_hint": r.get("age_gate_hint", 0), "served_title": (r.get("title") or "")[:100], "screened_utc": r.get("ts_utc")})
    with open(os.path.join(HERE, "candidates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    # stores whose blocklist is declared NOT to apply before a choice in California (not to be measured)
    nope = [r for *_, r, c in drawn if c == "blocklist_not_prechoice_ca"]
    with open(os.path.join(HERE, "blocklist_not_prechoice_ca.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["domain", "rank", "cmp", "ad_vendors_blocklisted", "pandectes_version", "why"])
        for r in nope:
            pdx = r.get("pandectes") or {}
            why = ("v5: California not in regions.strict (opt-out outside strict regions)" if pdx.get("version") == "v5"
                   else "v4: blocker inactive or ad category not in defaultBlocked")
            w.writerow([r["domain"], r["rank"], "|".join(r.get("blocklist_cmps") or []), "|".join(r.get("ad_vendors_blocklisted") or []),
                        pdx.get("version", ""), why])

    req = Counter()
    for r in R.values():
        if r.get("stage", "").startswith("excl_") and r["stage"].endswith("_domain"):
            continue
        req["robots_txt_fetch_or_cache"] += 1
    ts = sorted(r["ts_utc"] for r in R.values() if r.get("ts_utc"))
    out = {
        "tranco_list_id": "L5PZ4", "ranks": "200001-1000000", "permutation_seed": 20260926,
        "dns": dict(st, domains_in_complete_prefix=n_prefix_domains, dns_scan_complete=dns_complete),
        "frame_N_flagged": N, "frame_N_is_estimate": not dns_complete,
        "target": TARGET, "target_reached": reached, "gaps_in_prefix": gaps,
        "frame_exhausted": bool(dns_complete and not reached and gaps == 0 and len(order) == len(flagged)),
        "drawn_prefix_n": n_drawn, "design_weight": weight,
        "funnel_drawn": {
            "flagged_drawn": n_drawn,
            "excluded_before_any_request_adult_domain": stage.get("excl_adult_domain", 0),
            "excluded_before_any_request_child_domain": stage.get("excl_child_domain", 0),
            "skipped_robots_unreachable": stage.get("skip_robots_unreachable", 0),
            "skipped_robots_disallow_home": stage.get("skip_robots_disallow_home", 0),
            "skipped_robots_redirect": sum(v for k, v in stage.items() if k and k.startswith("skip_robots_redirect")),
            "homepage_fetched": fetched, "fetched_but_record_lost_nonresponse": lost, "http_200": http200,
            "fetch_errors": sum(v for k, v in stage.items() if k and k.startswith("err_")),
            "http_non200": sum(v for k, v in stage.items() if k and k.startswith("http_")),
            "not_shopify": stage.get("not_shopify", 0), "headless": stage.get("headless", 0), "password": stage.get("password", 0),
            "excluded_adult_text": stage.get("excl_adult_text", 0), "excluded_child_text": stage.get("excl_child_text", 0),
            "dup_main_sample": stage.get("dup_main_sample", 0), "dup_expansion": stage.get("dup_expansion", 0),
            "eligible_storefronts": len(elig),
            "with_target_cmp_detected": any_tgt, "target_cmp_detected_by_cmp": dict(tgt),
            "blocklist_readable_ad_vendor": len(readable), "blocklist_readable_by_cmp": dict(rd_by_cmp),
            "prechoice_ca_among_readable": dict(pre),
            "stratum_product_robots_disallowed": fun.get("stratum_product_robots_disallowed", 0),
            "candidates": len(cands),
            "candidates_by_cmp": dict(Counter(x["cmp"] for x in rows)),
            "candidates_by_prechoice_ca": dict(Counter(x["prechoice_ca"] for x in rows)),
            "candidates_without_product_url": sum(1 for x in rows if not x["product_url"]),
            "candidates_age_gate_hint": sum(1 for x in rows if x["age_gate_hint"]),
        },
        "stage_counts_drawn": dict(stage),
        "screened_total_including_overdraw": len(R), "overdraw_not_in_sample": len(overdraw),
        "overdraw_candidates": sum(1 for r in overdraw if r.get("in_stratum")),
        "estimated_stratum_stores_in_frame": round(len(cands) * weight, 1) if n_drawn else None,
        "estimated_readable_blocklist_stores_in_frame": round(len(readable) * weight, 1) if n_drawn else None,
        "screen_window_utc": [ts[0], ts[-1]] if ts else None,
    }
    json.dump(out, open(os.path.join(HERE, "funnel.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
