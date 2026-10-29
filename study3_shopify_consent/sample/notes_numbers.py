"""Collect the supplementary numbers quoted in SAMPLE_NOTES.md into raw/notes_numbers.json."""
import collections, json, os, re
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
R = lambda *p: os.path.join(BASE, *p)
out = {}
ev = pd.read_csv(R("raw", "verification_log.csv"))
rev = pd.read_csv(R("raw", "content_review.csv"))
out["content_review_flagged"] = len(rev)
out["content_review_decisions"] = rev.decision.value_counts().to_dict()
out["overdraw_stage_counts"] = ev[ev.stage == "overdraw_not_in_sample"].shape[0]
d = ev[ev.drawn]
out["drawn_stage_by_bucket"] = {b: g.reason.fillna("").replace("", "eligible").value_counts().to_dict() for b, g in d.groupby("bucket")}
s = pd.read_csv(R("sample.csv"))
n = s.notes.fillna("")
out["sample_served_country_top"] = collections.Counter(re.search(r"served_country=(\w+)", x).group(1) if "served_country=" in x else "NA" for x in n).most_common(10)
cm = collections.Counter()
for x in n:
    m = re.search(r"cmp_hints=([\w|\-]+)", x)
    for k in (m.group(1).split("|") if m else ["none"]):
        cm[k] += 1
out["sample_cmp_hint_counts"] = cm.most_common()
out["sample_by_bucket"] = s.bucket.value_counts().to_dict()
cs = pd.read_csv(R("creator_stratum.csv"))
out["creator_stratum_rows"] = len(cs)
out["creator_token_level"] = cs.token_level.value_counts().to_dict()
out["creator_dns_shopify"] = int(cs.dns_shopify.sum())
out["creator_in_tranco_1m"] = int(cs.tranco_rank.notna().sum())
out["creator_in_tranco_top200k"] = int((cs.tranco_rank <= 200000).sum())
out["creator_also_in_main_sample"] = int(n.shape[0] and cs.notes.fillna("").str.contains("also_in_main_sample").sum())
cx = pd.read_csv(R("raw", "creator_stratum_exclusions.csv"))
out["creator_exclusions_by_stage"] = cx.stage.value_counts().to_dict()
first = cx[cx.stage == "no_eligible_decorated_url"].reason.fillna("")
out["creator_no_url_primary_reason"] = collections.Counter(
    ("affiliate_network_or_click_id" if re.search(r"affiliate|click_id|smsclickid|awc|irclickid", r) else
     "no_token(token_level none/opaque)" if re.search(r"token_level:(none|opaque|nan)", r) else
     "creator_owned_domain_without_url_token" if "creator_token_not_in_final_url" in r else
     "other:" + r[:40]) for r in first).most_common()
dn = pd.read_csv(R("raw", "creator_dns.csv"))
out["study2_shopify_hosts"] = len(dn)
out["study2_shopify_hosts_on_shopify_dns"] = int(dn.shopify_ip_or_cname.sum())
out["study2_dns_recall"] = round(dn.shopify_ip_or_cname.mean(), 4)
json.dump(out, open(R("raw", "notes_numbers.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
