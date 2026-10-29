"""Step 4: apply eligibility rules to the verification results and write sample.csv + funnel counts.

Design: stratified by Tranco rank bucket.  Buckets listed in CENSUS are verified in full; the
remaining bucket(s) are verified in a seeded random draw order (raw/frame_flagged.csv, draw_order)
and the drawn set is the shortest prefix of that order that contains QUOTA eligible stores.
Design weight of a sampled store in bucket h:  w_h = N_h / n_h, where N_h is the number of
DNS-flagged domains in h (the frame) and n_h is the number drawn (verification attempted) in h.
Sum of w over sampled stores in h estimates the number of eligible storefronts among the flagged
domains of h.

Usage:
  python build_sample.py plan            # print eligible counts so far and the next queue to verify
  python build_sample.py queue <k>       # write raw/queue_b4.csv = first k domains of bucket 100k-200k
  python build_sample.py final           # write sample.csv, raw/verification_log.csv, raw/funnel.json
"""
import collections, csv, gzip, json, os, re, sys, urllib.parse
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import verify  # noqa: E402

FRAME = os.path.join(BASE, "raw", "frame_flagged.csv")
VER = os.path.join(BASE, "raw", "verify_results.jsonl")
DNS_SUMMARY = os.path.join(BASE, "raw", "dns_summary.json")
TARGET_TOTAL = 1400
BUCKETS = ["1-10k", "10k-50k", "50k-100k", "100k-200k"]
CENSUS = ["1-10k", "10k-50k", "50k-100k"]
SAMPLED = "100k-200k"
BLOCK_CODES = {401, 403, 429, 503}
REVIEW = os.path.join(BASE, "raw", "content_review.csv")
_review = {}
if os.path.exists(REVIEW):
    for _r in csv.DictReader(open(REVIEW)):
        _review[_r["domain"]] = _r["decision"]

RE_COUNTRY = re.compile(r"Shopify\.country\s*=\s*[\"']([A-Z]{2})[\"']")
RE_CURRENCY = re.compile(r"Shopify\.currency\s*=\s*\{\s*\"active\"\s*:\s*\"([A-Z]{3})\"")
RE_LOCALE = re.compile(r"Shopify\.locale\s*=\s*[\"']([A-Za-z-]+)[\"']")


def base_host(h):
    h = (h or "").lower()
    return h[4:] if h.startswith("www.") else h


def same_site(domain, host):
    host = (host or "").lower()
    return host == domain or host.endswith("." + domain)


def storefront_type(markers):
    ms = set(markers or [])
    if ms & {"Shopify.shop", "/cdn/shop/", "web-pixels-manager", "hdr:x-shopid"}:
        return "online_store"
    if ms:
        return "headless_or_assets_only"
    return "no_markers"


def load_ver():
    ver = {}
    if os.path.exists(VER):
        for line in open(VER):
            r = json.loads(line)
            ver[r["domain"]] = r
    return ver


def classify(r):
    """Return (stage, reason). stage in {'verified_live', 'eligible'} for survivors."""
    st = r.get("status")
    if st is None:
        return "fetch", "fetch_error:%s" % (r.get("error") or "unknown").split(":")[0]
    if st in BLOCK_CODES:
        return "fetch", "blocked_http_%d" % st
    if st != 200:
        return "fetch", "http_%d" % st
    stype = storefront_type(r.get("markers"))
    if stype == "no_markers":
        if not same_site(r["domain"], r.get("final_host")):
            return "shopify", "redirect_to_non_shopify"
        return "shopify", "no_shopify_markers"
    if stype == "headless_or_assets_only":
        return "shopify", "headless_or_assets_only"
    if r.get("password"):
        return "shopify", "password_protected"
    if r.get("adult_flag") or r.get("child_flag_domain") or r.get("child_flag_text"):
        # keyword screen hit -> researcher review of title/description (raw/content_review.csv)
        dec = _review.get(r["domain"], "")
        if dec == "exclude_adult":
            return "content", "adult_content"
        if dec == "exclude_child":
            return "content", "child_directed"
        if dec != "keep":
            return "content", "content_flag_unreviewed"
    if not r.get("product_url"):
        return "product", "no_product_url"  # no /products/ link on homepage and empty/failed products.json
    return "eligible", ""


def extras(r):
    notes = []
    try:
        body = gzip.open(os.path.join(BASE, r["body_file"]), "rb").read()
        text = verify.decode(body, (r.get("headers") or {}).get("content-type", ""))
        for rx, k in ((RE_COUNTRY, "served_country"), (RE_CURRENCY, "currency"), (RE_LOCALE, "locale")):
            m = rx.search(text)
            if m:
                notes.append("%s=%s" % (k, m.group(1)))
    except Exception:
        pass
    if not same_site(r["domain"], r.get("final_host")):
        notes.append("cross_domain_redirect:%s" % r.get("final_host"))
    if r.get("cmp_hints"):
        notes.append("cmp_hints=" + "|".join(r["cmp_hints"]))
    notes.append("wpm_inline=%d;app_pixel_cfg=%d;custom_pixel_cfg=%d" % (r.get("wpm", 0), r.get("n_app_pixel_cfg", 0),
                                                                         r.get("n_custom_pixel_cfg", 0)))
    if r.get("product_url_source") == "products.json":
        notes.append("product_url_from_products.json")
    if r.get("myshopify"):
        notes.append("myshopify=%s" % r["myshopify"])
    return notes


def evaluate(frame, ver):
    """Walk every bucket in draw order and classify; returns per-domain rows (attempted only)."""
    rows = []
    seen_shop = {}
    # dedupe by Shopify.shop across the whole sample, preferring the better (lower) Tranco rank
    for fr in frame.sort_values("rank").itertuples(index=False):
        r = ver.get(fr.domain)
        if r is None:
            continue
        stage, reason = classify(r)
        if stage == "eligible" and r.get("myshopify"):
            if r["myshopify"] in seen_shop:
                stage, reason = "dedupe", "duplicate_of:%s" % seen_shop[r["myshopify"]]
            else:
                seen_shop[r["myshopify"]] = fr.domain
        rows.append({"domain": fr.domain, "rank": fr.rank, "bucket": fr.bucket, "draw_order": fr.draw_order,
                     "status": r.get("status"), "final_url": r.get("final_url", ""), "stage": stage, "reason": reason,
                     "markers": ";".join(r.get("markers") or []), "title": r.get("title", "")})
    return pd.DataFrame(rows)


def main():
    mode = sys.argv[1]
    frame = pd.read_csv(FRAME)
    ver = load_ver()
    ev = evaluate(frame, ver)
    N = frame.bucket.value_counts().to_dict()
    if mode == "plan":
        for b in BUCKETS:
            e = ev[ev.bucket == b]
            print(b, "N=%d attempted=%d eligible=%d" % (N.get(b, 0), len(e), int((e.stage == "eligible").sum())),
                  e.reason.value_counts().to_dict())
        need = TARGET_TOTAL - int(ev[ev.bucket.isin(CENSUS)].stage.eq("eligible").sum())
        print("bucket %s quota = %d" % (SAMPLED, need))
        return
    if mode == "queue":
        k = int(sys.argv[2])
        q = frame[frame.bucket == SAMPLED].sort_values("draw_order").head(k)
        q.to_csv(os.path.join(BASE, "raw", "queue_b4.csv"), index=False)
        print("queue_b4 =", len(q))
        return
    assert mode == "final"
    census_elig = int(ev[ev.bucket.isin(CENSUS)].stage.eq("eligible").sum())
    quota = TARGET_TOTAL - census_elig
    for b in CENSUS:
        assert (ev.bucket == b).sum() == N[b], "census bucket %s not fully verified" % b
    b4 = ev[ev.bucket == SAMPLED].sort_values("draw_order")
    # contiguous prefix check
    orders = sorted(b4.draw_order)
    assert orders == list(range(len(orders))), "bucket-4 attempted set is not a prefix of the draw order"
    cum = b4.stage.eq("eligible").cumsum().values
    if cum[-1] < quota:
        raise SystemExit("bucket-4 quota not reached: %d < %d; extend queue" % (cum[-1], quota))
    n4 = int((cum < quota).sum()) + 1  # shortest prefix with `quota` eligible
    b4_drawn = set(b4.domain.iloc[:n4])
    b4_overdraw = set(b4.domain.iloc[n4:])
    ev["drawn"] = ev.bucket.isin(CENSUS) | ev.domain.isin(b4_drawn)
    ev.loc[ev.domain.isin(b4_overdraw), "reason"] = ev.loc[ev.domain.isin(b4_overdraw), "reason"].where(
        ev.loc[ev.domain.isin(b4_overdraw), "stage"] != "eligible", "")
    ev.loc[ev.domain.isin(b4_overdraw), "stage"] = "overdraw_not_in_sample"
    n_drawn = ev[ev.drawn].bucket.value_counts().to_dict()
    weight = {b: N[b] / n_drawn[b] for b in BUCKETS}
    ev.to_csv(os.path.join(BASE, "raw", "verification_log.csv"), index=False)

    samp = ev[ev.drawn & ev.stage.eq("eligible")].sort_values("rank")
    out = []
    for i, s in enumerate(samp.itertuples(index=False)):
        r = ver[s.domain]
        u = urllib.parse.urlsplit(r["final_url"])
        out.append({"store_id": "S%04d" % (i + 1), "domain": s.domain, "tranco_rank": s.rank, "bucket": s.bucket,
                    "weight": round(weight[s.bucket], 6), "homepage_url": "%s://%s/" % (u.scheme, u.hostname),
                    "product_url": r["product_url"], "shopify_markers": ";".join(r["markers"]),
                    "notes": "; ".join(extras(r))})
    pd.DataFrame(out).to_csv(os.path.join(BASE, "sample.csv"), index=False)

    d = ev[ev.drawn]
    dns = json.load(open(DNS_SUMMARY))
    funnel = {"tranco_list_id": dns["tranco_list_id"], "top_n": dns["top_n"],
              "domains_with_any_A_record": dns["domains_with_any_A"],
              "dns_flagged_shopify": int(sum(N.values())),
              "drawn_for_verification": int(len(d)),
              "http_200": int((d.status == 200).sum()),
              "verified_live_online_store": int(d.stage.isin(["content", "product", "dedupe", "eligible"]).sum()),
              "after_content_exclusions": int(d.stage.isin(["product", "dedupe", "eligible"]).sum()),
              "with_product_url": int(d.stage.isin(["dedupe", "eligible"]).sum()),
              "sample_after_dedupe": int((d.stage == "eligible").sum()),
              "bucket4_overdraw_verified_but_unused": int(len(b4_overdraw)),
              "per_bucket": {}, "exclusion_reasons": {}}
    for b in BUCKETS:
        e = d[d.bucket == b]
        funnel["per_bucket"][b] = {"tranco_domains": dns["per_bucket"][b]["domains"],
                                   "resolved": dns["per_bucket"][b]["resolved"], "flagged_N": int(N[b]),
                                   "drawn_n": int(len(e)), "sampling_fraction": round(len(e) / N[b], 4),
                                   "http_200": int((e.status == 200).sum()),
                                   "verified_live_online_store": int(e.stage.isin(["content", "product", "dedupe", "eligible"]).sum()),
                                   "sample": int((e.stage == "eligible").sum()), "weight": round(weight[b], 6),
                                   "est_eligible_in_frame": round((e.stage == "eligible").sum() * weight[b], 1)}
    rs = d[d.stage != "eligible"].reason.map(lambda x: x.split(":")[0] if x.startswith(("duplicate_of", "fetch_error")) else x)
    funnel["exclusion_reasons"] = {k: int(v) for k, v in rs.value_counts().items()}
    funnel["fetch_error_detail"] = {k: int(v) for k, v in d[d.reason.str.startswith("fetch_error")].reason.value_counts().items()}
    json.dump(funnel, open(os.path.join(BASE, "raw", "funnel.json"), "w"), indent=2)
    print(json.dumps(funnel, indent=2))


if __name__ == "__main__":
    main()


def write_fig2a_and_stats():
    """Figure 2a funnel table + request statistics (called after `final`)."""
    f = json.load(open(os.path.join(BASE, "raw", "funnel.json")))
    steps = [("Tranco top 200k (list %s)" % f["tranco_list_id"], f["top_n"]),
             ("Resolves (apex or www A record)", f["domains_with_any_A_record"]),
             ("DNS: Shopify IP (23.227.32.0/19) or *.myshopify.com CNAME", f["dns_flagged_shopify"]),
             ("Drawn for verification (census <=100k; random 100k-200k)", f["drawn_for_verification"]),
             ("HTTP 200 homepage", f["http_200"]),
             ("Verified live Online Store storefront", f["verified_live_online_store"]),
             ("After adult/child exclusions", f["after_content_exclusions"]),
             ("With product page URL", f["with_product_url"]),
             ("Sample (after de-duplication)", f["sample_after_dedupe"])]
    with open(os.path.join(BASE, "funnel_fig2a.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["step", "n"])
        w.writerows(steps)
    stats = {}
    for name in ("verify_results.jsonl", "creator_verify.jsonl"):
        p = os.path.join(BASE, "raw", name)
        recs = [json.loads(l) for l in open(p)]
        ts = sorted(r["ts_utc"] for r in recs)
        stats[name] = {"sites": len(recs), "http_requests": int(sum(r.get("n_requests", 0) for r in recs)),
                       "first_utc": ts[0], "last_utc": ts[-1],
                       "products_json_requests": int(sum(1 for r in recs if "products_json_status" in r or "products_json_error" in r))}
    s = pd.read_csv(os.path.join(BASE, "sample.csv"))
    n = s.notes.fillna("")
    stats["sample_product_url_from_products_json"] = int(n.str.contains("product_url_from_products.json").sum())
    stats["sample_wpm_inline"] = int(n.str.contains("wpm_inline=1").sum())
    stats["sample_cross_domain_redirect"] = int(n.str.contains("cross_domain_redirect").sum())
    stats["sample_served_country_US"] = int(n.str.contains("served_country=US").sum())
    stats["sample_with_any_cmp_hint"] = int(n.str.contains("cmp_hints=").sum())
    stats["sample_weight_sum"] = round(float(s.weight.sum()), 1)
    json.dump(stats, open(os.path.join(BASE, "raw", "request_stats.json"), "w"), indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "final":
    write_fig2a_and_stats()
