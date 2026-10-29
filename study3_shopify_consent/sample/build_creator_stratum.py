"""Step 4b (part 2): build creator_stratum.csv from the creator candidates and their single homepage check.

Inputs : raw/creator_candidates.csv (creator_candidates.py), raw/creator_verify.jsonl (verify.py run once
         per store on the undecorated homepage), raw/creator_store_exclusions.csv.
Outputs: creator_stratum.csv, raw/creator_stratum_exclusions.csv (all Study-2 Shopify landing stores
         not in the stratum, with the reason), raw/creator_dns.csv (DNS of every Study-2 Shopify store,
         used to estimate how many Shopify stores the DNS filter of the main sample would catch).

The first creator verification pass stored decoded HTML (older verify.py); it is re-analysed offline
here with the current analyse() - no second request is made to any store.
"""
import csv, gzip, json, os, socket, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import verify  # noqa: E402

CAND = os.path.join(BASE, "raw", "creator_candidates.csv")
VER = os.path.join(BASE, "raw", "creator_verify.jsonl")
EXC_IN = os.path.join(BASE, "raw", "creator_store_exclusions.csv")
OUT = os.path.join(BASE, "creator_stratum.csv")
EXC_OUT = os.path.join(BASE, "raw", "creator_stratum_exclusions.csv")
DNS_OUT = os.path.join(BASE, "raw", "creator_dns.csv")
SHOPIFY_NET = ipaddress.ip_network("23.227.32.0/19")
FORCE_INCLUDE = {"c005.store.example": "motivating case from Study 2 (per-video desc-<video> codes); products are "
                                   "STEM kits for ages 8+ sold to parents; included by design despite the child-oriented product line"}


def recover_text(rec):
    p = os.path.join(BASE, rec.get("html_file") or rec.get("body_file"))
    if rec.get("body_file"):
        body = gzip.open(p, "rb").read()
        return verify.decode(body, (rec.get("headers") or {}).get("content-type", ""))
    text = gzip.open(p, "rt", encoding="utf-8").read()
    try:  # old pass decoded charset-less pages as ISO-8859-1; undo that losslessly
        return text.encode("latin-1").decode("utf-8", errors="replace")
    except UnicodeEncodeError:
        return text


def resolve(host):
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_CANONNAME)
        canon = next((i[3] for i in infos if i[3]), "").rstrip(".").lower()
        ips = sorted({i[4][0] for i in infos})
    except Exception:
        return host, "", []
    return host, canon, ips


def storefront_type(markers):
    ms = set(markers)
    if ms & {"Shopify.shop", "/cdn/shop/", "web-pixels-manager", "hdr:x-shopid"}:
        return "online_store"
    if ms:
        return "headless_or_assets_only"
    return "no_markers"


def main():
    cand = pd.read_csv(CAND)
    ver = {}
    for line in open(VER):
        r = json.loads(line)
        ver[r["domain"]] = r
    # DNS for every Study-2 Shopify landing store host (candidates + excluded)
    exc_in = pd.read_csv(EXC_IN)
    s2 = os.path.abspath(os.path.join(BASE, "..", "..", "study2_creator_links", "data", "landing_pages.csv"))
    lp = pd.read_csv(s2)
    hosts = sorted(set(lp[lp.is_shopify == 1].final_url.map(lambda u: urllib.parse.urlsplit(u).hostname)) |
                   set(cand.final_url.map(lambda u: urllib.parse.urlsplit(u).hostname)))
    with ThreadPoolExecutor(20) as ex:
        dns = list(ex.map(resolve, hosts))
    with open(DNS_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["host", "canon", "ips", "shopify_ip_or_cname"])
        for h, c, ips in dns:
            flag = int(any(ipaddress.ip_address(i) in SHOPIFY_NET for i in ips) or c.endswith("myshopify.com"))
            w.writerow([h, c, " ".join(ips), flag])
    dns_map = {h: (c, ips) for h, c, ips in dns}

    rows, exc = [], []
    for i, c in enumerate(cand.itertuples(index=False)):
        rec = ver.get(c.store)
        notes = []
        if rec is None:
            exc.append({"store": c.store, "stage": "verify", "reason": "not_fetched"})
            continue
        if rec.get("status") != 200:
            reason = "homepage_status_%s%s" % (rec.get("status"), ("_" + rec["error"]) if rec.get("error") else "")
            markers, stype, a = [], "unverified", {}
        else:
            text = recover_text(rec)
            hdrs = rec.get("headers") or {}
            if not hdrs:
                if "hdr:powered-by" in rec.get("markers", []):
                    hdrs["powered-by"] = "Shopify"
                if rec.get("x_shopid"):
                    hdrs["x-shopid"] = rec["x_shopid"]
            a = verify.analyse(c.store, rec["final_url"], hdrs, text)
            markers = a["markers"]
            stype = storefront_type(markers)
            reason = ""
            if stype != "online_store":
                reason = stype
            elif a["password"]:
                reason = "password_page"
            elif a["adult_flag"]:
                reason = "adult_content_flag"
            elif (a["child_flag_domain"] or a["child_flag_text"]) and c.store not in FORCE_INCLUDE:
                reason = "child_directed_flag"
        host = urllib.parse.urlsplit(c.final_url).hostname
        canon, ips = dns_map.get(host, ("", []))
        dns_flag = int(any(ipaddress.ip_address(x) in SHOPIFY_NET for x in ips) or canon.endswith("myshopify.com"))
        if reason:
            exc.append({"store": c.store, "stage": "verify", "reason": reason, "status": rec.get("status"),
                        "markers": ";".join(markers), "title": a.get("title", "") if a else ""})
            continue
        if c.store in FORCE_INCLUDE:
            notes.append(FORCE_INCLUDE[c.store])
        if not dns_flag:
            notes.append("not on Shopify IPs by DNS (%s) - outside main-sample frame definition" % (canon or " ".join(ips)))
        if a.get("cmp_hints"):
            notes.append("cmp_hints=" + "|".join(a["cmp_hints"]))
        if not a.get("wpm"):
            notes.append("web_pixels_manager_not_inlined_in_homepage_html")
        rows.append({
            "store_id": "C%03d" % (len(rows) + 1), "domain": c.store, "landing_url": c.final_url,
            "token_level": c.token_level, "token": c.token, "channel": c.channel, "video_id": c.video_id,
            "n_channels": c.n_channels, "n_link_instances": c.n_link_instances,
            "homepage_url": rec["final_url"], "product_url": a.get("product_url") or rec.get("product_url", ""),
            "shopify_markers": ";".join(markers), "storefront_type": stype, "dns_shopify": dns_flag,
            "notes": "; ".join(notes)})
    # Tranco rank (list L5PZ4, full 1M) of the registrable domain, and overlap with the main sample
    import tldextract
    tx = tldextract.TLDExtract(suffix_list_urls=())
    tr = {}
    with open(os.path.join(BASE, "raw", "tranco_L5PZ4_top1m.csv")) as f:
        for rk, dom in csv.reader(f):
            tr[dom] = int(rk)
    main = {}
    if os.path.exists(os.path.join(BASE, "sample.csv")):
        ms = pd.read_csv(os.path.join(BASE, "sample.csv"))
        main = dict(zip(ms.domain, ms.store_id))
    for r in rows:
        e = tx(r["domain"])
        reg = e.domain + "." + e.suffix
        r["tranco_rank"] = tr.get(reg, "")
        if reg in main:
            r["notes"] = "; ".join([x for x in [r["notes"], "also_in_main_sample=%s" % main[reg]] if x])
    cols = ["store_id", "domain", "tranco_rank", "landing_url", "token_level", "token", "channel", "video_id",
            "n_channels", "n_link_instances", "homepage_url", "product_url", "shopify_markers", "storefront_type",
            "dns_shopify", "notes"]
    out_df = pd.DataFrame(rows)[cols]
    out_df["tranco_rank"] = pd.to_numeric(out_df.tranco_rank, errors="coerce").astype("Int64")
    out_df.to_csv(OUT, index=False)
    ex2 = pd.DataFrame(exc)
    ex_prev = exc_in.rename(columns={"top_reasons": "reason"})
    ex_prev["stage"] = "no_eligible_decorated_url"
    allx = pd.concat([ex_prev[["store", "stage", "reason", "n_link_instances"]], ex2], ignore_index=True)
    allx.to_csv(EXC_OUT, index=False)
    d = pd.read_csv(DNS_OUT)
    print("study2 shopify landing stores:", len(cand) + len(exc_in))
    print("with eligible decorated URL:", len(cand))
    print("excluded at verification:", len(ex2), ex2.reason.value_counts().to_dict() if len(ex2) else {})
    print("creator stratum rows:", len(rows), "of which video-level:", sum(r["token_level"] == "video" for r in rows))
    print("DNS: study2 shopify landing hosts:", len(d), "on Shopify IP/CNAME:", int(d.shopify_ip_or_cname.sum()))
    ok = pd.DataFrame(rows)
    print("creator stratum on Shopify IPs:", int(ok.dns_shopify.sum()) if len(ok) else 0)


if __name__ == "__main__":
    main()
