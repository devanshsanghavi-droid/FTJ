"""Step 4b (part 1): candidate creator-decorated landing URLs on Shopify stores, from Study 2 data.

Input : ../../study2_creator_links/data/landing_pages.csv (is_shopify == 1) and links.csv
Output: raw/creator_candidates.csv (one chosen URL per store + reasons) and
        raw/creator_store_exclusions.csv (Shopify landing stores with no eligible URL)

Eligibility of a link instance (all must hold):
  * its final URL is one of the Study-2 Shopify landing pages;
  * token_level == 'video' with a utm_ parameter in the final URL, or
    token_level == 'creator' with the token readable in the final URL (not merely a
    creator-owned domain);
  * the redirect chain used no affiliate network and no brand affiliate-link tool;
  * the final URL carries no click ID / opaque affiliate ID (Study-2 flags) and none of a
    list of known affiliate/click parameters; utm_medium=affiliate is also excluded.
We never visit the original (possibly shortened) link: the chosen URL is the final store URL,
so no affiliate or shortener redirect is exercised.
"""
import os, re, urllib.parse
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
S2 = os.path.abspath(os.path.join(BASE, "..", "..", "study2_creator_links", "data"))
OUT = os.path.join(BASE, "raw", "creator_candidates.csv")
EXC = os.path.join(BASE, "raw", "creator_store_exclusions.csv")

AFF_TOOLS = ["tradedoubler", "awin", "avantlink", "shopmy", "impact", "rakuten", "ltk", "sovrn",
             "skimlinks", "partnerize", "cj", "pepperjam", "magiclinks", "brand_affiliate_link",
             "refersion", "howl", "narrativ", "geniuslink", "amazon"]
AFF_PARAMS = {"rfsn", "irclickid", "irgwc", "awc", "smsclickid", "sscid", "cjevent", "ranmid", "ransiteid",
              "ranEAID".lower(), "gclid", "fbclid", "dclid", "msclkid", "ttclid", "clickid", "click_id",
              "aff", "affid", "aff_id", "affiliate", "affiliate_id", "ref", "sca_ref", "refer", "referral",
              "subid", "sub_id", "afsrc", "wickedid", "_kx", "mc_eid", "srsltid", "dtm_cid", "tw_source",
              "discount", "discount_code", "snowball"}
PLATFORM_HOSTS = {"shopify.com", "myshopify.com", "shop.app"}


def host_key(url):
    h = (urllib.parse.urlsplit(url).hostname or "").lower()
    if h.endswith(".myshopify.com"):
        return h
    parts = h.split(".")
    return h[4:] if h.startswith("www.") else h


def reasons(row):
    r = []
    tool = str(row.link_tool or "")
    if any(t in tool.split("+") or t in tool for t in AFF_TOOLS):
        r.append("affiliate_tool:" + tool)
    if int(row.click_id_final or 0) == 1:
        r.append("click_id_final")
    if int(row.affiliate_opaque_final or 0) == 1:
        r.append("affiliate_opaque_final")
    q = urllib.parse.parse_qsl(urllib.parse.urlsplit(row.final_url).query, keep_blank_values=True)
    keys = {k.lower() for k, v in q}
    bad = sorted((keys & AFF_PARAMS) | {k for k in keys if k.startswith("rfsn")})
    if bad:
        r.append("affiliate_or_click_param:" + ",".join(bad))
    if any(k.lower() == "utm_medium" and "affiliate" in v.lower() for k, v in q):
        r.append("utm_medium=affiliate")
    if "/discount/" in urllib.parse.urlsplit(row.final_url).path:
        r.append("discount_path")
    if host_key(row.final_url) in PLATFORM_HOSTS:
        r.append("platform_site")
    tl = str(row.token_level)
    tok = str(row.token or "")
    if tl == "video":
        if "utm_" not in row.final_url:
            r.append("video_token_not_in_url")
    elif tl == "creator":
        if int(row.creator_readable_final or 0) != 1 or tok.startswith("creator_owned_domain"):
            r.append("creator_token_not_in_final_url")
    else:
        r.append("token_level:" + tl)
    return r


def main():
    lp = pd.read_csv(os.path.join(S2, "landing_pages.csv"))
    L = pd.read_csv(os.path.join(S2, "links.csv"), low_memory=False)
    shop = lp[lp.is_shopify == 1].copy()
    shop["store"] = shop.final_url.map(host_key)
    x = L[L.final_url.isin(set(shop.final_url))].copy()
    x["store"] = x.final_url.map(host_key)
    x["why_not"] = x.apply(lambda r: ";".join(reasons(r)), axis=1)
    x["eligible"] = x.why_not == ""
    x["n_instances"] = x.groupby("final_url").final_url.transform("size")
    el = x[x.eligible].copy()
    el["rank_level"] = el.token_level.map({"video": 0, "creator": 1})
    el["is_utm"] = (~el.final_url.str.contains("utm_", regex=False)).astype(int)
    el["is_desc"] = (~el.final_url.str.contains("utm_campaign=desc-", regex=False)).astype(int)
    el["is_product"] = (~el.final_url.str.contains("/products/", regex=False)).astype(int)
    el = el.sort_values(["store", "rank_level", "is_desc", "is_utm", "is_product", "n_instances", "final_url"],
                        ascending=[True, True, True, True, True, False, True])
    chosen = el.drop_duplicates("store", keep="first")
    agg = x.groupby("store").agg(n_link_instances=("final_url", "size"),
                                 n_channels=("channel", "nunique"),
                                 channels=("channel", lambda s: ";".join(sorted(set(s)))),
                                 n_eligible_instances=("eligible", "sum")).reset_index()
    out = chosen[["store", "channel", "video_id", "url", "final_url", "token_level", "token", "link_tool",
                  "category_link"]].merge(agg, on="store", how="left")
    out.to_csv(OUT, index=False)
    all_stores = sorted(set(shop.store))
    exc = []
    for s in all_stores:
        if s in set(out.store):
            continue
        sub = x[x.store == s]
        why = sub.why_not.str.split(";").explode().value_counts()
        exc.append({"store": s, "n_link_instances": len(sub), "top_reasons": "; ".join("%s(%d)" % (k, v) for k, v in why.head(4).items())})
    pd.DataFrame(exc).to_csv(EXC, index=False)
    print("shopify landing pages:", len(shop), "stores:", len(all_stores))
    print("link instances on those pages:", len(x), "eligible:", int(x.eligible.sum()))
    print("stores with >=1 eligible decorated URL:", len(out))
    print("stores excluded:", len(exc))
    print(out.token_level.value_counts().to_string())


if __name__ == "__main__":
    main()
