"""Validate the static screen against the main crawl (no network).

For the 1,362 main-sample stores captured by the crawl, apply static_detect to the homepage saved at
sampling time (sample/raw/homepages) and compare with what the crawl read at run time
(crawl/cmp_declared.csv, arm A0). For OneTrust and Cookiebot the vendor blocklist file is taken from the
crawl's own capture of that file (crawl/raw/<store>__A0.json.gz: otautoblock / cookiebot_cfg), which is the
same file the screener fetches from the vendor CDN.
Output: calibration.json and calibration.txt (read-only use of sample/ and crawl/).
"""
import csv, gzip, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import static_detect as sd  # noqa: E402

dom2body = {}
for line in open(os.path.join(ROOT, "sample", "raw", "verify_results.jsonl")):
    r = json.loads(line)
    if r.get("body_file"):
        dom2body[r["domain"]] = os.path.join(ROOT, "sample", r["body_file"])
samp = {r["store_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "sample", "sample.csv")))}
loads = {r["store_id"] for r in csv.DictReader(open(os.path.join(ROOT, "crawl", "loads.csv"))) if r.get("arm") == "A0"}
cmp_rows = [r for r in csv.DictReader(open(os.path.join(ROOT, "crawl", "cmp.csv"))) if r["arm"] == "A0"]
rt_cmp = {}
for r in cmp_rows:
    if r["cmp"] in sd.TARGET and r.get("strong_evidence") == "True":
        rt_cmp.setdefault(r["store_id"], set()).add(r["cmp"])
decl = [r for r in csv.DictReader(open(os.path.join(ROOT, "crawl", "cmp_declared.csv"))) if r["arm"] == "A0" and r["is_advertising"] == "True"]
rt_listed = {}
rt_pre = {}
for r in decl:
    rt_listed.setdefault(r["store_id"], set()).add(r["cmp"])
    if r["declared_prechoice"] == "blocked":
        rt_pre.setdefault(r["store_id"], set()).add(r["cmp"])

rows = []
for sid, s in sorted(samp.items()):
    if sid not in loads:
        continue
    bf = dom2body.get(s["domain"])
    if not bf or not os.path.exists(bf):
        continue
    t = gzip.open(bf).read().decode("utf-8", "replace")
    cm = sd.detect_cmps(t)
    ents = []
    st_cmps = [k for k in sd.TARGET if k in cm]
    pc = sd.pandectes_config(t)
    if pc:
        ents += [dict(e, cmp="pandectes") for e in pc["entries"]]
    ot = sd.onetrust_page(t)
    cb = sd.cookiebot_page(t)
    raw = None
    if ot["autoblock_url"] or cb["tag"]:
        p = os.path.join(ROOT, "crawl", "raw", sid + "__A0.json.gz")
        if os.path.exists(p):
            raw = json.load(gzip.open(p))
    if ot["autoblock_url"] and raw and (raw.get("otautoblock") or {}).get("tags"):
        ents += [dict(e, cmp="onetrust") for e in sd.onetrust_entries(raw["otautoblock"]["tags"])]
    if cb["tag"] and raw and (raw.get("cookiebot_cfg") or {}).get("tags"):
        ents += [dict(e, cmp="cookiebot") for e in sd.cookiebot_entries(raw["cookiebot_cfg"]["tags"], cb["blockingmode"])]
    sm = sd.summarize(ents)
    rows.append(dict(store_id=sid, st_cmps="|".join(st_cmps), rt_cmps="|".join(sorted(rt_cmp.get(sid, []))),
                     st_readable=int(bool(sm["ad_vendors_blocklisted"])), st_pre=sm["prechoice_ca"],
                     rt_listed=int(sid in rt_listed), rt_pre=int(sid in rt_pre),
                     ot_autoblock=int(bool(ot["autoblock_url"])), cb_auto=int(cb["blockingmode"] == "auto"),
                     pd_version=(pc or {}).get("version", "")))

n = len(rows)
c = Counter()
for r in rows:
    c[("readable", r["st_readable"], r["rt_listed"])] += 1
    if r["rt_pre"]:
        c[("rt_pre_by_st", r["st_readable"], r["st_pre"])] += 1
    if r["st_readable"]:
        c[("st_pre", r["st_pre"], r["rt_pre"])] += 1
out = {"n_stores": n, "static_readable": sum(r["st_readable"] for r in rows), "runtime_listed": sum(r["rt_listed"] for r in rows),
       "runtime_prechoice_blocked": sum(r["rt_pre"] for r in rows),
       "agree_table_static_x_runtime_listed": {f"static={a},runtime={b}": v for (k, a, b), v in c.items() if k == "readable"},
       "runtime_prechoice_blocked_by_static": {f"static_readable={a},static_pre={b}": v for (k, a, b), v in c.items() if k == "rt_pre_by_st"},
       "static_pre_x_runtime_pre_among_static_readable": {f"static_pre={a},runtime_pre={b}": v for (k, a, b), v in c.items() if k == "st_pre"},
       "static_target_cmp": Counter(x for r in rows for x in r["st_cmps"].split("|") if x),
       "runtime_target_cmp": Counter(x for r in rows for x in r["rt_cmps"].split("|") if x),
       "disagreements": [r for r in rows if r["st_readable"] != r["rt_listed"]]}
json.dump(out, open(os.path.join(HERE, "calibration.json"), "w"), indent=1, default=dict)
print(json.dumps({k: v for k, v in out.items() if k != "disagreements"}, indent=1, default=dict))
print("disagreements:", len(out["disagreements"]))
for r in out["disagreements"]:
    print(r)
