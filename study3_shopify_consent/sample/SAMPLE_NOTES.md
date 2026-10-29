# Study 3 store sample: method, funnel, exclusions, limitations

Built 2026-09-25/26 (US Pacific) = 2026-09-26 05:11–05:40 UTC, from a residential connection in California, USA.
Every number below is read from a file written by the scripts in this folder. The source file is given in brackets.

## Files

| File | What it is |
|---|---|
| `sample.csv` | The main sample: 1,400 verified Shopify Online Store storefronts, with columns `store_id, domain, tranco_rank, bucket, weight, homepage_url, product_url, shopify_markers, notes` |
| `creator_stratum.csv` | A purposive stratum of 34 Shopify stores that Study 2 creators link to, each with one real creator-decorated landing URL |
| `funnel_fig2a.csv` | Step counts for Figure 2a |
| `raw/funnel.json` | Funnel and counts per bucket, plus exclusion reasons |
| `raw/dns_summary.json` | DNS-stage counts |
| `raw/request_stats.json` | HTTP request counts and time window |
| `raw/notes_numbers.json` | Other numbers quoted here |
| `raw/frame_flagged.csv` | The sampling frame (2,634 DNS-flagged domains) with the seeded draw order |
| `raw/verification_log.csv` | Stage and reason for every domain we verified |
| `raw/verify_results.jsonl` | Full per-site verification records; the raw homepage bodies are in `raw/homepages/` |
| `raw/content_review.csv` | The 21 keyword-flagged stores and the adult/child decision for each |
| `raw/creator_candidates.csv`, `raw/creator_stratum_exclusions.csv`, `raw/creator_dns.csv` | Working files for the creator stratum |
| `raw/tranco_L5PZ4_top1m.csv`, `raw/tranco_latest_meta.json`, `raw/arin_rdap_SHOPI-1.json` | Inputs as downloaded |

To rebuild, run the scripts in this order: `dns_scan.py` → `build_frame.py` → `verify.py raw/queue_b123.csv` → `build_sample.py queue 660` → `verify.py raw/queue_b4.csv` → `build_sample.py final` → `creator_candidates.py` → `verify.py` (with `VERIFY_OUT=creator_verify.jsonl`, run on `raw/creator_queue.csv`) → `build_creator_stratum.py` → `notes_numbers.py`.

## 1. Ranking list

We used Tranco list **L5PZ4** (https://tranco-list.eu/list/L5PZ4). The API reports it as `created_on` 2026-09-25T22:00:02. Its settings: providers CrUX, Farsight, Majestic, Radar and Umbrella; Dowdall combination; a 30-day window from 2026-08-27 to 2026-09-25; pay-level-domain filtering on [`raw/tranco_latest_meta.json`]. We took ranks 1–200,000. Cite as Le Pochat et al., NDSS 2019, and give the list ID.

Rank buckets are 1–10,000, 10,001–50,000, 50,001–100,000 and 100,001–200,000.

## 2. DNS filter (cheap and passive)

- We resolved each domain `d` and `www.d`, which is **400,000 hostnames**. We used the system resolver (macOS `getaddrinfo`, IPv4, `AI_CANONNAME`) through the home gateway, with at most **50 lookups in flight**. The scan finished at 05:36 UTC after about 23 minutes [`raw/dns_scan.log`].
- **The flag rule.** We flagged a hostname if either of these held:
  - any A record is in **23.227.32.0/19**. This is ARIN net SHOPIFY-NET of Shopify, Inc. (org SHOPI-1), the only IPv4 block in that org's RDAP record [`raw/arin_rdap_SHOPI-1.json`]. Shopify's documented storefront targets (`23.227.38.65`, `shop.myshopify.com`) fall inside it.
  - the end of the CNAME chain is `shop.myshopify.com` or `*.myshopify.com`.

  A domain is flagged if its apex or its www host is flagged.
- We dropped 7 of Shopify's own platform domains: shopify.com, myshopify.com, shop.app, shopifypreview.com, shopify.dev, shopify.io and shopify.engineering.
- **Results** [`raw/dns_summary.json`]:
  - 181,310 of 200,000 domains have an A record for the apex or www.
  - 56,441 hostname lookups returned "no such host".
  - **2,634 domains were flagged**: 2,485 on both apex and www, 75 on the apex only and 74 on www only.
  - 2,632 of the flagged domains have an address in 23.227.38.0/24, and 2,410 have a myshopify CNAME.

| Bucket | Tranco domains | Resolved | DNS-flagged (N_h) |
|---|---:|---:|---:|
| 1–10k | 10,000 | 8,690 | 8 |
| 10k–50k | 40,000 | 35,179 | 206 |
| 50k–100k | 50,000 | 45,999 | 688 |
| 100k–200k | 100,000 | 91,442 | 1,732 |

Shopify storefronts are rare at the very top of the ranking: only 8 of the top 10,000 are flagged. The flag rate rises further down the list.

**DNS recall check.** We took the 219 Shopify landing hosts from Study 2, which were identified from page content rather than DNS. Of these, **190 (86.8%)** resolve to a Shopify IP or myshopify CNAME [`raw/creator_dns.csv`, `raw/notes_numbers.json`]. The rest sit behind the merchant's own CDN or a headless front end: Cloudflare-proxied domains, Netlify or Vercel. The DNS frame therefore misses roughly one in eight Shopify-backed sites, and mostly misses proxied or headless ones.

## 3. Verification (one homepage request per site)

**Design.** The top three buckets are a **census**: all 902 flagged domains were verified.

Bucket 100k–200k is a **simple random sample**:
- Domains were verified in a seeded random order (seed 20260925, stored in `raw/frame_flagged.csv`).
- We drew the shortest prefix of that order that held the remaining quota of eligible stores. The quota was 1,400 minus the 824 eligible stores from the census, which is 576.
- That prefix is **616 of 1,732** domains.
- We verified 44 more domains in the same order (660 in total) but left them out, so that the drawn set stays an exact prefix. They are marked `overdraw_not_in_sample` in `raw/verification_log.csv`.

**Request policy.**
- One `GET https://<host>/`, following redirects. The host is the apex if the apex was flagged, otherwise `www`.
- The User-Agent is the library default, `python-requests/2.32.5`, with no spoofing.
- No cookies carried between sites and no JavaScript.
- No retries.
- At most 8 sites in flight and at most 4 requests per second overall.
- If the homepage had no `/products/` link, we made exactly one `GET /products.json?limit=1`. That happened for 176 sites.

In total we made 1,734 requests to 1,562 sites between 05:25:47 and 05:40:01 UTC [`raw/request_stats.json`]. We never logged in, submitted forms, added to cart or interacted with a consent banner.

**Eligibility rules.** They are applied in this order, and the first failure is recorded:
1. The homepage returns HTTP 200. We record fetch errors, 403 (blocked) and other status codes separately.
2. **It is a Shopify Online Store** (the Liquid storefront). At least one of these must be present:
   - `Shopify.shop = "…"`
   - `/cdn/shop/` assets
   - the inline `web-pixels-manager` bootstrap
   - an `x-shopid` header

   A page with only `cdn.shopify.com` assets or a `powered-by: Shopify` header is classed as **headless** (Hydrogen/Oxygen or a custom front end) and excluded. These stores do not run the Online Store Web Pixels Manager this study measures. A page with no markers at all, or a redirect to a non-Shopify site, is also excluded.
3. It is not password-protected: no `/password` redirect, password template or password form.
4. **It is not adult content and not aimed at children.** A keyword screen checked the domain, `<title>`, meta description and og:site_name, plus the `rating=adult`/RTA meta label. The child screen used only the title and site name, and was switched off when the title also names an adult audience. All 21 flagged sites were then reviewed by the researcher from their title and description [`raw/content_review.csv`]:
   - 11 excluded as aimed at children: toy stores and kidswear, treated conservatively.
   - 4 excluded as adult.
   - 6 kept: general retailers, bookstores, dog toys and novelty gifts.

   Baby-care and parenting products with no "kids", "toys" or "children" positioning were kept.
5. It has a product page URL, either the first same-host `/products/<handle>` link on the homepage or the first handle in `products.json`. In the sample, 136 product URLs come from `products.json`.
6. **De-duplication.** When two Tranco domains serve the same shop (the same `Shopify.shop` value), we keep the better-ranked one. This removed 7 domains, and every twin that was kept is in the sample.

**Funnel for Figure 2a** [`funnel_fig2a.csv`]:

| Step | n |
|---|---:|
| Tranco top 200k (L5PZ4) | 200,000 |
| Resolves (apex or www A record) | 181,310 |
| DNS-flagged Shopify | 2,634 |
| Drawn for verification | 1,518 |
| HTTP 200 homepage | 1,491 |
| Verified live Online Store storefront | 1,438 |
| After adult/child exclusions | 1,424 |
| With product page URL | 1,407 |
| **Sample (after de-duplication)** | **1,400** |
| Successfully captured | *(filled in by the crawl)* |

**Exclusions among the 1,518 drawn domains** [`raw/funnel.json`]:

| Reason | Count |
|---|---:|
| Headless or assets only | 47 |
| No product URL | 17 |
| Blocked with HTTP 403 | 16 |
| Aimed at children | 10 |
| Duplicate | 7 |
| Adult | 4 |
| Fetch errors (2 connection, 2 TLS) | 4 |
| No Shopify markers | 3 |
| Password-protected | 3 |
| HTTP 402 or 404 ("store unavailable") | 4 |
| HTTP 409, 423 or 500 | 3 |

The eleventh child-directed store is in the unused overdraw.

**Weights.** For a store in bucket h the design weight is w_h = N_h / n_h, where N_h is the number of flagged domains in the bucket and n_h the number drawn.

| Bucket | N_h | n_h | Sample | w_h | Estimated eligible storefronts |
|---|---:|---:|---:|---:|---:|
| 1–10k | 8 | 8 | 7 | 1.000 | 7 |
| 10k–50k | 206 | 206 | 181 | 1.000 | 181 |
| 50k–100k | 688 | 688 | 636 | 1.000 | 636 |
| 100k–200k | 1,732 | 616 | 576 | 2.812 | 1,619.5 |

The weights sum to **2,443.5**, which estimates the number of eligible Online Store storefronts among the DNS-flagged top-200k domains. Use these weights for population-level percentages, such as the Figure 6d projection. Unweighted and per-bucket results go in Supplementary Figure S3.

**Sample composition.** These are descriptive only, and taken from the homepage HTML [`raw/request_stats.json`, `raw/notes_numbers.json`]:
- **Web Pixels Manager.** 1,384 of 1,400 stores inline the bootstrap, and `app_pixel_cfg` records how many APP entries its config lists.
- **Served country.** This is the `Shopify.country` value served to our US vantage: US 578, IN 227, GB 94, PK 62, DE 55, JP 44, FR 38, AU 31, IT 26, CA 25.
- **Consent tools.** Static CMP string hints appear on 831 stores: Shopify's own privacy banner 299, Consentmo 235, Pandectes 137, OneTrust 122, Cookiebot 82, CookieHub 71, and others. These are string matches, not a measurement of whether a banner is present. The crawl must detect banners itself.
- **Redirects.** 13 stores redirect to a different host but still serve Shopify markers.

## 4. Creator stratum (`creator_stratum.csv`)

**Source.** We started from the 490 Study 2 landing pages flagged `is_shopify = 1`, which cover 219 store hosts, and their 1,620 link instances in `links.csv`.

**Which URLs qualify.** A link instance is eligible only if all of these hold:
- It is a direct store URL carrying a creator token:
  - `token_level = video` with a `utm_` parameter, or
  - `token_level = creator` with the token readable in the final URL. A creator-owned domain on its own does not count.
- It did not pass through any affiliate network or brand affiliate-link tool: ShopMy, Awin/Tradedoubler, Impact, Rakuten, LTK, Sovrn, Skimlinks, AvantLink, CJ, Pepperjam, Partnerize or MagicLinks.
- It carries no click ID or opaque affiliate ID, and none of the parameters `rfsn*`, `irclickid`, `awc`, `smsclickid`, `sscid`, `ref`, `sca_ref`, `snowball`, `discount*`, …
- It does not use `utm_medium=affiliate`.

We use the **final store URL** as it appeared in Study 2, so no shortener or affiliate redirect is ever exercised. For each store we pick one URL, preferring:
1. video-level over creator-level tokens;
2. `utm_campaign=desc-…`;
3. any `utm_` parameter;
4. `/products/` pages;
5. the most frequently linked URL.

**Funnel.**
- 219 stores.
- 175 have no eligible URL. Of these, 102 have at least one instance through an affiliate network or click ID and none eligible, 39 have no token or only an opaque one, 33 are creator-owned stores with no token in the URL, and 1 is Shopify's own site. See `raw/creator_stratum_exclusions.csv`.
- That leaves 44 candidates.
- A single undecorated homepage check (same policy as above) excluded 10 of them: 7 headless, 1 with no markers (dbrand.com, which is Vercel-hosted), 1 blocked with HTTP 403 (ridge.com) and 1 rate-limited with HTTP 429 (drinkag1.com).
- **34 stores** remain: 6 with a video-level token and 28 with a creator-level token.
- 32 of the 34 are on Shopify IPs.
- 26 are in the Tranco top 1M and 8 are in the top 200k. The rank is that of the registrable domain.
- 3 are also in the main sample: c016.store.example (S0200), c010.store.example (S0871) and c022.store.example (S1224).

**Store C** (C005) is included by design. The motivating Study 2 case uses the per-video landing URL `utm_campaign=desc-VideoToken`. Its products are STEM kits for ages 8 and up, sold to parents, so it is noted as an exception to the child-directed exclusion. Its homepage does not inline the Web Pixels Manager config, which matches the Study 2 note that the pixel config is loaded rather than inlined.

## Limitations

- **Coverage of the DNS frame.** Stores whose domains are proxied through the merchant's own CDN (Cloudflare "orange-to-orange" and similar) or served by headless front ends are not flagged. On the Study 2 set that is 13.2% of known Shopify-backed hosts. The sample describes Shopify Online Store storefronts reachable on Shopify's own edge, not all Shopify merchants.
- **Tranco.** The ranking reflects an aggregate of traffic and DNS popularity, not shopping traffic. The top bucket holds only 8 flagged and 7 sampled stores, so estimates for that bucket are close to anecdotal.
- **Blocking and nonresponse.** 16 sites returned 403 and 4 failed at the TLS or connection level. These requests used an honest library User-Agent and no bot-evasion techniques. We treat these sites as ineligible and did not adjust for nonresponse, so stores with aggressive bot protection are slightly under-represented. The browser crawl may see different blocking.
- **Headless exclusion.** The 47 headless storefronts are out of scope for the Web Pixels Manager sandbox question. They include large brands such as skims.com and fashionnova.com. They deserve a separate study, because consent behaviour on Hydrogen is a different code path.
- **Content screen.** The screen is a keyword filter plus a single-researcher review of titles. It may miss child-directed or adult stores whose titles do not use the keywords. Child exclusions were deliberately conservative: kidswear and toy stores were excluded even when parents are the buyers.
- **Product URL.** The first product link or `products.json` handle may point to a sold-out, gift-card or hidden product. The crawl should record the final product-page status.
- **Single vantage and time.** We used one US-CA residential vantage point and one day. The `Shopify.country` served to us reflects geolocation and market setup, not the merchant's home country.
- **CMP hints.** These are static string matches on the homepage HTML. They can be wrong both ways and are not results.
- **De-duplication** only compared stores inside the drawn set, using the `Shopify.shop` identifier.
- **Repeat requests.** Three stores are in both the main sample and the creator stratum, and barnesandnoble.com was checked by both passes. Each of these sites therefore received at most two homepage requests on the same day.
