# Part B2 protocol: the beyond-Shopify pilot

*Do consent banners control ad tags that run outside the page's main script, or outside the banner's reach, on other architectures?*

Status: design plus screening, completed 27 Sep 2026 03:40 PDT. No measurement load has been run. The screening numbers are in §7 and in `screen/raw/screen_summary.json`, and the sites are in `candidates.csv`. The measurement crawl waits for the ethics determination (ethics request §5.3).

Every statement about how a product works is cited to vendor documentation that was read on 26–27 Sep 2026 (§10). Statements marked **(screening)** come from our own static homepage fetches. Statements marked **(hypothesis)** are what the pilot tests.

---

## 1. Question and scope

In Part A, many Shopify stores that showed a cookie banner still sent advertising data before any choice and after "Decline". Most of that data came from pixels in Shopify's sandbox (web workers and iframes), which run outside the page's main script and outside the banner's direct control. The mechanism is general: **a consent tool can only block what it can see**. B2 asks whether the same gap appears in five other setups where tags run somewhere other than the page's main thread, or are controlled by something other than the site's banner.

| Code | Setup | Where the tags run | Who is supposed to enforce consent |
|---|---|---|---|
| PT | **Partytown**: `<script type="text/partytown">` | A web worker, with main-thread DOM calls proxied | The site. Partytown has no consent logic of its own; its docs say consent tools should stay on the main thread. |
| ZZ | **Cloudflare Zaraz** | Mostly on Cloudflare's servers ("server-side"). A small loader and some client-side actions run in the page. | Zaraz Consent Management (purposes), or the site's own CMP if it is wired to `zaraz.consent` |
| GW | **First-party tag gateway / server-side GTM** | The tag loads from the site's own domain or a tagging server, and hits go to a first-party collect endpoint. Onward forwarding happens server-side. | Google Consent Mode signals in each hit, and whatever the server container is configured to do |
| WX | **Wix** sites | Wix marketing integrations and custom code in the page; HTML embeds and app iframes on other origins; site code in a platform worker | Wix consent policy and cookie banner. Apps and iframes must check the policy themselves. |
| BC | **BigCommerce** stores | Script Manager scripts, scripts in theme files, and channel/app integrations | BigCommerce cookie consent (Script Manager categories) or a third-party CMP |

- **Out of scope:** Shopify storefronts (Part A and B1), the vendors' own corporate sites, log-in areas, checkout.
- **This is a pilot.** It measures feasibility and rough effect sizes. The plan was 60–80 sites per setup; screening reached 80 for WX and BC, 26 for GW, 8 for PT and 1 for ZZ (§7). Only the random stratum R (§6.2) supports prevalence statements.

## 2. What each setup does with consent (documentation)

### 2.1 Partytown (PT)

- A script opts in with `type="text/partytown"`. The browser ignores that type, and Partytown finds these scripts and runs them in a web worker. After it runs one, it changes the type to `text/partytown-x` [PT-scripts].
- Main-thread calls that tags expect (`dataLayer.push`, `gtag`, `fbq`) reach the worker only if they are listed in the `forward` config. By default, forwarded calls run **only** in the worker, not also on the main thread (`preserveBehavior: false`) [PT-forward].
- Worker code fetches third-party scripts with `fetch()`, so a vendor without CORS headers must go through a reverse proxy set by `resolveUrl()`. The request URL is then the site's own domain or a proxy host [PT-proxy].
- Partytown lists consent tools and cookie banners as bad candidates for the worker. So in practice the banner runs on the main thread while the tags run in the worker [PT-tradeoffs]. Its "how it works" page does not mention consent at all [PT-how].
- **Why this matters for consent.** Many CMPs block tags on the main thread, for example by rewriting `<script>` types, watching the DOM for new scripts, or patching `document.createElement`. A `text/partytown` script never runs as a main-thread script, and its worker-side `fetch()` is invisible to main-thread hooks. Unless the site (i) renders the Partytown scripts only after consent, or (ii) forwards Consent Mode calls to the worker and the tag honours them, the banner's choice may not reach the tag. **(hypothesis)**

### 2.2 Cloudflare Zaraz (ZZ)

- Zaraz "is loading tools server-side, which means code running in the browser will not be able to see it" [ZZ-faq]. The page loads a small script. By default this is auto-injected [ZZ-settings], at `/cdn-cgi/zaraz/…`, and the path can be customised [ZZ-settings]. Events go to Cloudflare, which forwards them to the configured tools.
- **Consent Management.** Tools are assigned to purposes. "Tools without assigned purposes will skip consent by default", while a tool with a purpose "will not run unless the user gives consent" [ZZ-consent]. Events blocked for lack of consent are queued (`zaraz.consent.sendQueuedEvents()`) [ZZ-api]. The choice is stored in a first-party cookie, `cf_consent` by default [ZZ-api].
- The API is `zaraz.consent.get/set/getAll/setAll`, with the events `zarazConsentAPIReady` and `zarazConsentChoicesUpdated` [ZZ-api]. A site that uses **another** CMP must call this API itself.
- Google Consent Mode v2 is supported through `zaraz.set("google_consent_default", …)` in the page HTML, and server-side requests carry `gcd` [ZZ-gcm].
- The settings include a **Bot Score Threshold** that stops Zaraz loading for suspected bots [ZZ-settings]. Our unmodified, automated browser may therefore see no Zaraz activity at all (§9).

### 2.3 First-party tag gateways and server-side GTM (GW)

- **Google tag gateway for advertisers.** The site "deploy[s] a Google tag using your own first-party infrastructure, hosted on your website's domain" [GW-gateway], through a CDN or load balancer "that can forward requests to external endpoints" [GW-setup]. On Cloudflare, the site picks an unused path, and tags load from `https://<site>/<measurement-path>/…`, with the measurement requests served through that path [GW-cf].
- **Server-side GTM.** The web tag sends hits to a tagging server (`server_container_url` / `transport_url`) on a first-party subdomain. The server container decides where the data goes: "only you have access to the data in the server until you choose to send it elsewhere" [GW-sst].
- **Consent in server-side tagging.** The banner's choice travels as consent parameters on each hit. Google's own server tags "adjust the amount and kind of data they send". The documentation does not say that non-Google tags in the server container respect consent [GW-sst-consent].
- **Consequence for measurement.** A browser sees the hit leave for the site's own endpoint, and sees the consent state that the hit claims (`gcs`, `gcd`). It **cannot** see the server-to-server forwarding (§3).

### 2.4 Wix (WX)

- **Categories.** Wix has five consent categories: Essential, Functional, Analytics, Advertising and Data to third party. Embedded scripts "are automatically rendered or blocked" according to the category chosen at setup [WX-configs] [WX-apps].
- **Custom code** "defaults to essential" and loads without consent unless the owner re-categorises it. Third-party App Market apps are outside Wix's control ("Wix cannot guarantee full compliance") [WX-support].
- **Apps in iframes or worker iframes** must read the consent policy themselves (`getCurrentConsentPolicy`, `onConsentPolicyChanged`). For worker iframe apps, "the consent policy is also passed as a query param in the iframe URL" [WX-apps].
- **Banner audience.** The banner has an audience setting, `all_visitors` or `eu_visitors`, and an optional "Decline all" button (`declineAllConfig`) [WX-banner]. Its default texts include "Accept" and "Decline All".
- **(screening)** Every Wix page carries the site's default policy for the visitor in the viewer model (`"siteConsentPolicy":{essential,functional,analytics,advertising,dataToThirdParty}`). Seen from California, some sites have `analytics`/`advertising` set to `false` by default (banner requiring consent) and others have all `true`. Wix's inline Google Consent Mode bridge applies denial by default only where `gdprEnforcedGeo` is set (`defaultPolicy && gdprEnforcedGeo ? {…advertising:false, analytics:false} : policy`).

### 2.5 BigCommerce (BC)

- **Opt-in consent.** With "cookie consent tracking" enabled, "it is assumed the shopper has not consented to anything until a value is explicitly set". The choice is posted to `POST /api/storefront/consent` with `allow`/`deny` category lists and stored as a cookie [BC-consent].
- **Script categories.** Scripts are categorised Essential, Functional, Analytics or Targeting (the API also has UNKNOWN) [BC-enum]. "Scripts categorized as Essential load on every page regardless", and the others wait for consent. With consent tracking disabled, "all scripts load unconditionally" [BC-catalyst]. Any control-panel user can change a script's category [BC-scripts].
- **(screening)** On Stencil storefronts with consent enabled, `window.consentManagerStoreConfig` is present, and held-back scripts appear as `<script type="text/plain" data-bc-cookie-consent="N">` (for example, a Criteo tag with category 4).
- **Not covered by the documentation:** scripts pasted into theme templates, and integrations installed through channels or apps, such as a native GA4 or Meta channel. Whether these respect the categories is exactly what BC tests. **(hypothesis)**

## 3. Observables: what a browser can and cannot see

The crawler is the Part A instrument: CDP auto-attach to every page, iframe and worker target, a fresh profile for every load, the Default/Decline/GPC arms, the same banner detector and the same Decline-only clicker. Section 5 lists what B2 adds.

| Setup | Directly observable | **Not** observable (and the proxy we use instead) |
|---|---|---|
| PT | Requests from the Partytown worker target (session type `worker`, worker URL matches `partytown-ww-*`, or a blob worker started by the Partytown snippet). DOM counts of `text/partytown` (not yet run) and `text/partytown-x` (run in the worker). `window.partytown` config, including `forward` and whether `resolveUrl` exists. Proxied requests (`…?url=<encoded vendor URL>`), classified by their inner URL. | Nothing essential is hidden: a worker's network traffic is visible to CDP. The only caveat is that a service-worker-mediated build can re-issue requests, so we deduplicate by URL and time. |
| ZZ | Loader and track calls to `/cdn-cgi/zaraz/*` (or a custom path found in the HTML). Client-side vendor requests that Zaraz actions trigger. `zaraz.consent.getAll()` and `purposes` at every checkpoint. The `cf_consent` cookie. `Set-Cookie` names on Zaraz responses. | **Server-side tool execution.** Proxy: a Zaraz track call carrying the event **before any choice** or **after Decline**. We report it as "event data sent to the Zaraz edge", never as "sent to vendor X". Tool cookies appearing (for example `_ga` or `_fbp` set through Zaraz) show that a tool ran. |
| GW | Requests to first-party or tag-gateway hosts that match the rules in `vendor_endpoints_extra.json` (§4): the tag loaded first-party (`gtm.js`/`gtag/js`/custom loader), GA4 hits (`v=2&tid=G-…&en=`), Google Ads/ccm hits, Meta/TikTok wire formats. The `gcs`/`gcd` consent parameters in those hits. `Set-Cookie` names on their responses (`FPID`, `FPLC`, `_ga`, `_fbp`). | **Onward forwarding** from the tagging server or CDN to Google, Meta and others. Proxy: a first-party collect hit before any choice or after Decline (data left the browser), split by the consent state the hit declares. Server-set identifier cookies after Decline are the strongest evidence available. |
| WX | Vendor requests from the top frame, from HTML-embed iframes (`*.filesusr.com`), from app iframes (`*.wixapps.net`) and from the Wix platform worker. `consentPolicyManager.getCurrentConsentPolicy()` at every checkpoint, the `consent-policy` cookie, and `wixTagManager.getConfig().gdprEnforcedGeo`. | Wix-side conversion APIs (for example Meta CAPI run by Wix) are server-side. Proxy: none reliable. We report browser-side only and state the gap. |
| BC | Vendor requests from the top frame and iframes. Held-back scripts (`text/plain` with `data-bc-cookie-consent`) before and after Decline. The `POST /api/storefront/consent` body. `consentManagerStoreConfig()`. First-party cookie names that match `/consent/i`. | Channel integrations that send server-side (for example a conversions API). Proxy: none. We report browser-side only. |

**General limits of any browser measurement.**
- Requests blocked by the browser itself are not counted as data sent. They are logged with `failed=true`, as in Part A.
- Cookies are recorded by **name** only.
- Request bodies are kept up to 4,000 characters.

## 4. Attribution rules for first-party proxies

The machine-readable rules are in `vendor_endpoints_extra.json → first_party_rules`, and the original `crawl/vendor_endpoints.json` is not edited. Each request is classified in this order, and the first match wins:

1. **Third-party host map.** The original 72 entries, then the 39 added host entries. The additions are publisher and B2B ad tech common outside e-commerce (Xandr, PubMatic, Magnite, Index, 6sense, ZoomInfo, …), analytics, hosted server-side-GTM hosts (Stape, TAGGRS, Addingwell, JENTIS) and platform first-party analytics (`frog.wix.com`).
2. **First-party rules, `strong` evidence.** The request goes to the page's own registrable domain, or to a hosted-sGTM host, and its path or wire format is unique to one vendor. Examples: GA4 `v=2&tid=G-…&en=`; Google Ads `/pagead/conversion`, `/ccm/collect`; Meta `/tr?id=…&ev=`; TikTok `/api/v2/pixel`; Zaraz `/cdn-cgi/zaraz/t`; the Partytown proxy `?url=<vendor URL>` (attributed to the inner vendor).
   - Counted in the headline, with the label **"via first-party endpoint"**.
   - The vendor is attributed only when the wire format names it. A GA4 hit to `/g/collect` counts as *Google Analytics via first-party endpoint*. That does **not** mean the server sent it on to Google.
3. **First-party rules, `moderate` evidence** (custom-loader base64 ids, Google tag parameters on an unrecognised path, Stape "Data client" posts, `capig.` subdomains, Zaraz custom paths). Reported in a separate column and not added to headline counts.
4. **Server-side forwarding is never inferred.** A first-party hit is reported as **"data left the browser to a first-party/gateway endpoint"**. The paper must not say "sent to Meta" when the only evidence is a first-party hit.
5. **Consent state claimed by the hit.** Decode `gcs` (official values G100/G110/G101/G111) and `gcd` (an unofficial letter code, so it is validated on calibration pages first) into granted, denied or not set for each signal. After Decline, hits that declare *denied* are a separate category, "denied-flag pings", distinct from hits that declare *granted* or carry no consent parameters.
   - Google documents that denied-state hits are still sent without cookies.
   - This category is the gateway analogue of Part A's opt-out/opt-in split, not automatically a violation.
6. **Identifier cookies set by the server.** `Set-Cookie` names on first-party tag or collect responses (`FPID`, `FPLC`, `_ga`, `_gcl_au`, `_fbp`, `_ttp`, …). Such a cookie set after Decline counts as a strong finding.
7. **Where the request came from.** This extends the Part A `origin` labels:
   - `partytown_worker` (a worker target whose URL or creating script matches Partytown);
   - `zaraz_client` (the stack contains the Zaraz loader);
   - `wix_embed_iframe` (frame host `*.filesusr.com`);
   - `wix_app_frame`;
   - `wix_platform_worker`;
   - `bc_held_back` (a script that was `text/plain` with `data-bc-cookie-consent` in the static HTML and later ran);
   - `main_thread`, `subframe`, `other_worker` (as in Part A).
8. **Double counting.** A tag loaded first-party that then sends to a third-party host counts once per request, not per architecture. A site that matches several setups (for example a BigCommerce store with an sGTM subdomain) is analysed under the setup it was sampled for. Its other setups are listed in `other_architectures`.

## 5. Arms and procedure

The same three conditions as Part A. Every load is a fresh temporary profile in California, with the unmodified headless Chromium UA, no stealth and the automation flag on.

| Arm | Procedure | Windows |
|---|---|---|
| **A0 Default** | Load, no interaction, 6 passive scrolls | 15 s after `load` (12 s after DCL if `load` never fires) |
| **A1 Decline** | Wait up to 10 s for a visible banner. Click **only** a Decline/Reject control (Part A `generic_reject`; never Accept, Settings, "Do not sell" or forms). Observe 15 s. Then reload the same URL once and observe 10 s. | Pre-click, click +1 s, +5 s, end, next page |
| **A2 GPC** | `Sec-GPC: 1` on every request, including worker requests, and `navigator.globalPrivacyControl = true` in every frame **and every worker** before its scripts run. This matters for Partytown workers. | As A0 |

- **Page.** The homepage for PT/ZZ/GW. For WX/BC stores, one public product page when the static homepage links one and `robots.txt` allows it (`candidates.csv → measure_url`), otherwise the homepage. The URL carries the Part A test code (`utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-b2-<id>`) plus the project-page address once it exists.
- **Loads per site.** One screening GET (done) + A0 + A1 (2 loads) + A2 = **5**, under the cap of 8 per site. An optional repeat of A0 on a 20% subsample would make 6.
- **Order and pacing.** Arm order is shuffled per site (seeded). At most 1 navigation per second overall, at most 1 load per site per 10 s, at most 6 browsers at once. `robots.txt` is checked again before each site; disallowed pages are skipped.
- **Readouts at each checkpoint** (added to Part A's probes):
  - PT: `window.partytown`, counts of `text/partytown` and `text/partytown-x` scripts, worker targets.
  - ZZ: `zaraz.consent.APIReady`, `getAll()`, `purposes` (ids and names only), a Zaraz-loaded flag.
  - WX: `consentPolicyManager.getCurrentConsentPolicy()` (policy and defaultPolicy), `wixTagManager.getConfig().gdprEnforcedGeo`.
  - BC: `consentManagerStoreConfig()`, counts of held-back scripts by category, `/consent/i` cookie names.
  - All: TCF/GPP as in Part A, and cookie names.
- **Crawler changes needed** (in a copy of `crawl/`, not in `crawl/` itself):
  1. Replace the `window.Shopify` qualification with "HTTP 2xx/3xx, not blocked, more than 20 requests".
  2. Load `vendor_endpoints_extra.json` and apply §4.
  3. Keep the URL and body for first-party requests that match a rule, and the **names** from `Set-Cookie` on their responses (`Network.responseReceivedExtraInfo`).
  4. Add the new origin labels.
  5. Add the readouts above.
  6. Inject GPC into workers created from blobs. Partytown can use blob workers; verify this on the calibration sites.
- **Calibration before the pilot.** Run all three arms on 2 reserve sites per setup. Check that Partytown worker traffic is attributed, that Zaraz loads for our browser (bot threshold), that `gcd` decoding matches `gcs` where both are present, and the cookie names used by Wix and BigCommerce. Fix the rules, then freeze them before the main pilot.

## 6. Screening method (done 26–27 Sep 2026)

### 6.1 Frame and DNS flags (passive)

- **Frame.** Tranco list L5PZ4, the same as Part A.
- **Ranks 1–200,000.** Part A's DNS results for apex and www were re-used, with no new lookups.
- **Ranks 200,001–1,000,000.** Only `www.<domain>` was resolved, with at most 40 lookups in flight (`screen/dns_platforms.py`). In the top 200k, the www host alone catches 147/153 Wix and 133/141 BigCommerce domains.
- **Flags:**
  - **Wix:** A record in 185.230.60.0/22 (RIPE `wix_com_inc` / `Wixcom-EU`), the Wix edge 34.149.87.45, or a CNAME in `wixdns.net`.
  - **BigCommerce:** an A record in BigCommerce Inc.'s ARIN networks (org INTER-1370: 63.141.128.0/19, 192.200.160.0/19, 104.195.64.0/18), or a CNAME containing `bigcommerce`. RDAP records are saved in `inputs/`.
  - **Cloudflare:** Cloudflare's published IPv4 ranges (`inputs/cloudflare_ips_v4.txt`). Zaraz requires Cloudflare.
  - **Vercel/Netlify:** 76.76.21.0/24 and related ranges, or `vercel`/`netlify` CNAMEs. Partytown is used mostly by JavaScript-framework sites.
  - **Shopify:** the Part A rule, used only to exclude sites.

### 6.2 Strata

| Stratum | Definition | Use |
|---|---|---|
| W | All Wix-flagged domains, ranks 1–1M (census) | WX candidates |
| BC | All BigCommerce-flagged domains, ranks 1–1M (census) | BC candidates |
| R | Seeded random order (seed 20260927) of resolved, non-Shopify, non-Wix/BC top-200k domains; the screened set is a prefix | **Prevalence** of PT/ZZ/GW, and candidates |
| CF | Seeded random Cloudflare-proxied top-200k domains | Zaraz oversample (and PT/GW) |
| J | All Vercel/Netlify-hosted top-200k domains, in seeded order | Partytown oversample (and ZZ/GW) |
| J2 | Vercel/Netlify-hosted domains at ranks 200,001–1,000,000 (www host), in rank order; added 27 Sep 03:15 PDT after the top-200k strata gave too few PT and GW sites | Partytown and gateway top-up |
| CAL | 4 vendor-owned pages (builder.io, partytown.qwik.dev, cloudflare.com, blog.cloudflare.com) | Marker calibration only; never candidates |

**Excluded before any contact:**
- Part A's 1,400 sample stores and every Shopify-flagged domain;
- the platforms' and vendors' own domains;
- names matching the adult or child-directed screens. These are broader than Part A's: they add major adult-site brand tokens and child-site names such as `pbskids`, `coolmath` and `roblox`.

### 6.3 Per-site procedure (`screen/screen_http.py`, driven by `screen_runner.py`)

1. **`robots.txt` first.**
   - `https://<host>/robots.txt`, at most 5 redirects, parsed with RFC 9309 groups (token `python-requests`, else `*`).
   - A 4xx response means allowed. A 5xx, a network error or too many redirects means the site is **skipped**.
   - A homepage redirect to a new host triggers that host's `robots.txt` before the next hop. A robots file reached through a robots redirect is re-used for its host.
2. **One homepage GET.** Redirects are followed by hand. No JavaScript, no cookies kept, library-default UA, no retries. The body is capped at 3 MB.
3. **Static markers** (`screen/markers.py`):
   - Partytown `text/partytown` scripts and library;
   - Zaraz loader or API;
   - gateway: Google tag URLs on first-party or gateway hosts, GTM snippets pointing to non-Google hosts, `server_container_url`/`transport_url`, custom loaders, `capig.` hosts;
   - Wix and BigCommerce platform and consent config;
   - 45 CMP signatures plus `__tcfapi`/GPP;
   - ad/analytics tag hints;
   - title, description and `rating` meta for the adult and child screens.
4. **Storage.**
   - Only pages with an architecture marker are kept, gzipped, in `screen/raw/pages/`. Everything else is reduced to the extracted fields in `screen/raw/screen_results.jsonl`.
   - `Set-Cookie` values are never stored.
   - The job stops if free disk falls below 1.2 GB.
5. **Rate.** At most 1 homepage GET/s and 1 `robots.txt` GET/s overall, and at most 6 sites in flight (robots.txt 2/s and 8 in flight from 00:20–00:30 PDT). `plan.json` is read before every batch, which allows early stopping per stratum.
   - The J2 top-up ran at **0.5** homepage GET/s, 0.5 `robots.txt` GET/s and 4 sites in flight, because the separate Part B1 expansion screener (`round4/expansion/`, Shopify stores only) was running from the same machine at about 1 homepage GET/s. The two jobs never contact the same site, but their **combined** rate was about 1.5 homepage GET/s during the overlap. The earlier B2 strata (00:00–01:37 PDT) also overlapped with that screener, at about 2 GET/s combined. The mentor should confirm that the "1 navigation per second overall" cap applies per crawler job; if it applies per machine, this is a deviation to report in the ethics request.

### 6.4 Eligibility and selection (`screen/build_candidates.py`)

- **Eligible:**
  - HTTP 200 HTML on the same registrable domain;
  - `robots.txt` allows `/`;
  - not adult, child-directed, age-restricted (gambling, AI-roleplay; added 27 Sep 03:30 PDT) or Shopify;
  - an architecture marker;
  - a consent tool visible in the static HTML. For Zaraz, **tier Z** also admits sites without a static CMP, because Zaraz's own modal is injected at run time.
- **Tiers:**
  - **A:** CMP plus an ad or Google tag visible statically;
  - **B:** CMP, no tag visible statically;
  - **Z:** see above.
- **Selection:**
  - Per setup, eligible sites are ordered by tier (A, B, Z), then shuffled with seed 20260927 within each tier.
  - The first 80 are `selected` and the next 20 are `reserve` (cap 100 per setup, 500 in all).
  - Setups are filled rarest first (PT, ZZ, GW, WX, BC), so a site is selected for only one setup.

- **Detector fix (27 Sep 03:30 PDT).** The gateway detector read protocol-relative Google URLs (`//www.googletagmanager.com/gtag/js?id=…`) as same-host paths, so ordinary Google tags counted as gateways. `markers.py` now skips them. All saved pages are re-analysed with the fixed detector (`REANALYSE_ALL=1 python build_candidates.py`), and §7 uses the re-analysed values. The runner's live stop counts (`runner.log`) used the old detector and overstate gateways.

## 7. Screening results

Screening ran from 23:57 PDT 26 Sep to 03:40 PDT 27 Sep 2026. Each site got one `robots.txt` request and at most one homepage GET. No banner was clicked and no page was loaded in a browser. Tables are produced by `screen/report_screening.py` (no network). Counts are per registrable domain, first screening only. Percentages in the marker table are shares of HTTP-200 pages with 95% Wilson intervals.

**Funnel per stratum**

| Stratum | Queued & screened | Name screen (not contacted) | robots.txt disallowed | robots.txt unreachable (skipped) | 401/403/429/503 | Other failure | HTTP 200 HTML |
|---|---:|---:|---:|---:|---:|---:|---:|
| W | 465 | 0 | 1 | 18 | 1 | 33 | 412 |
| BC | 348 | 0 | 1 | 3 | 6 | 0 | 338 |
| R | 1200 | 0 | 32 | 204 | 228 | 50 | 686 |
| CF | 1045 | 0 | 19 | 61 | 322 | 31 | 612 |
| J | 2220 | 0 | 20 | 109 | 272 | 36 | 1783 |
| J2 | 480 | 0 | 3 | 90 | 34 | 2 | 351 |

**Markers among HTTP-200 pages (saved pages re-analysed with the final detector)**

| Stratum | OK pages | Partytown scripts | Partytown library only | Zaraz | Gateway (static) | Static CMP or TCF |
|---|---:|---:|---:|---:|---:|---:|
| W | 412 | 0 (0.0%; 0.0–0.9) | 0 (0.0%; 0.0–0.9) | 0 (0.0%; 0.0–0.9) | 0 (0.0%; 0.0–0.9) | 129 (31.3%; 27.0–35.9) |
| BC | 338 | 1 (0.3%; 0.1–1.7) | 0 (0.0%; 0.0–1.1) | 0 (0.0%; 0.0–1.1) | 5 (1.5%; 0.6–3.4) | 152 (45.0%; 39.8–50.3) |
| R | 686 | 0 (0.0%; 0.0–0.6) | 0 (0.0%; 0.0–0.6) | 0 (0.0%; 0.0–0.6) | 8 (1.2%; 0.6–2.3) | 156 (22.7%; 19.8–26.0) |
| CF | 612 | 1 (0.2%; 0.0–0.9) | 0 (0.0%; 0.0–0.6) | 0 (0.0%; 0.0–0.6) | 5 (0.8%; 0.3–1.9) | 133 (21.7%; 18.6–25.2) |
| J | 1783 | 3 (0.2%; 0.1–0.5) | 15 (0.8%; 0.5–1.4) | 1 (0.1%; 0.0–0.3) | 33 (1.9%; 1.3–2.6) | 532 (29.8%; 27.8–32.0) |
| J2 | 351 | 0 (0.0%; 0.0–1.1) | 1 (0.3%; 0.1–1.6) | 0 (0.0%; 0.0–1.1) | 6 (1.7%; 0.8–3.7) | 87 (24.8%; 20.6–29.6) |

**Candidates per setup** (`candidates.csv`; one row per site and setup)

| Setup | Sites with marker | Eligible (A/B/L/Z) | Tier A / B / L-Z | Selected | Reserve | Backup, no static CMP (U) | Main exclusion reasons |
|---|---:|---:|---|---:|---:|---:|---|
| partytown | 21 | 8 | 3 / 0 / 5 | 8 | 0 | 7 | redirects_to_other_site 5, age_restricted 1 |
| zaraz | 1 | 1 | 0 / 0 / 1 | 1 | 0 | 0 |  |
| gateway | 57 | 26 | 26 / 0 / 0 | 26 | 0 | 22 | shopify_storefront 5, redirects_to_other_site 4, child_directed 1, age_restricted 1 |
| wix | 412 | 120 | 42 / 78 / 0 | 80 | 20 | 0 | no_static_cmp 258, redirects_to_other_site 28, age_restricted 4, child_directed 3 |
| bigcommerce | 347 | 149 | 146 / 3 / 0 | 80 | 20 | 0 | no_static_cmp 180, shopify_storefront 11, child_directed 8, adult 1 |

**What this means**

- **WX and BC reached the target:** 80 selected and 20 reserve each. WX has more tier B sites (a banner but no ad tag visible in the static HTML). Wix injects most tags at run time, so tier B is expected there. On BigCommerce, 146 of 149 eligible stores show a tag statically.
- **GW fell short:** 26 eligible sites, all tier A, plus 22 backups (tier U: gateway present, no consent tool visible statically). About 1% of random top-200k sites (R) serve a Google tag from a first-party host or configure a tagging server in the static HTML. Gateways configured inside a GTM container are invisible here (§9.4).
- **PT fell far short:** 8 eligible sites, plus 7 backups. Of the 8, 3 have `text/partytown` scripts and 5 load the Partytown library with no worker script in the static HTML (tier L). Tier L sites may add worker scripts at run time, possibly only after consent. Partytown scripts appeared on 0 of 686 random sites and on about 0.2% of Vercel/Netlify sites, even in the oversample.
- **ZZ fell far short:** the Zaraz loader appeared on 1 screened page outside the calibration pages, and that site is eligible (tier Z). Zaraz was absent from all 612 reachable Cloudflare-stratum pages. Two explanations fit: Zaraz is rare, or Zaraz is not injected for clients it scores as bots (§2.2). A static fetch cannot tell these apart.
- **The J2 top-up** (Vercel/Netlify, ranks 200,001–1,000,000) added 2 GW sites, 3 GW backups and 1 PT backup in 480 sites. It was stopped there because the yield was too low to justify about 3 more hours of requests.
- **Screening bias.** The library user agent was refused (401/403/429/503) by 7–31% of sites in the R, CF, J and J2 strata (CF highest), and `robots.txt` was unreachable on another 5–19%. Sites with bot protection are therefore under-represented (§9.5).

**Options to close the gap (mentor decision; none has been started, and none needs new screening)**

1. **Use the tier U backups, gated by a banner check.** Run A0 first on each backup. If no consent banner or CMP is detected at run time, stop after that one load and record "no banner seen from California". This could bring GW to at most 48 sites and PT to at most 15.
2. **Treat PT and ZZ as case studies.** Report each site individually (mechanism, what fired and from where). Report no rates and make no comparison with other setups. This is the default if nothing else is approved.
3. **Controlled test sites** for PT and ZZ. The mentor sets up a test site on a free Cloudflare plan with Zaraz plus Zaraz Consent Management and a third-party CMP, and a static page with Partytown and a CMP that blocks main-thread tags. All three arms then run there. This tests the mechanism (H-PT1, H-ZZ1, H-ZZ2) without third-party sites. It needs accounts, which only the authors can create.
4. **Passive discovery for a later study.** HTTP Archive's public crawl data (BigQuery) can list pages that request `/cdn-cgi/zaraz/` or contain `text/partytown`, without contacting any site. Joining that list with Tranco and screening only those sites with the §6.3 procedure would give a proper PT/ZZ frame. This needs a Google Cloud account (mentor).

## 8. Expected outcomes (hypotheses) and how to read them

Part A's reference rates, from banner stores in California:
- an ad request before any choice on 87.3% (358/410);
- a sandboxed ad request before any choice on 50.0% (205/410).

| Setup | Hypothesis | What would support it | What would count against it |
|---|---|---|---|
| PT | **H-PT1.** On sites whose CMP blocks main-thread tags (auto-blocking CMPs, or tags rendered only after consent), tags moved to the Partytown worker still send ad data before any choice and after Decline. | In A0 or A1, ad beacons from `partytown_worker` while main-thread tags of the same vendor are held back (for example by Cookiebot/OneTrust auto-blocking). | Worker tags start only after consent (the site renders `text/partytown` conditionally), or Consent Mode commands are forwarded (`forward` includes `gtag`/`dataLayer.push`) and hits declare denied. |
| PT | **H-PT2.** GPC reaches the worker only through our injection. Tags in the worker do not act on it any more than on the main thread. | Same ad-beacon rate in A2 as in A0. | Lower A2 rates; worker code reading `navigator.globalPrivacyControl`. |
| ZZ | **H-ZZ1.** Tools with no purpose run whatever the choice: Zaraz track calls and tool side effects continue after Decline. | `/t` posts plus tool cookies or client-side vendor requests after Decline; `zaraz.consent.getAll()` showing all purposes false while activity continues. | Activity stops at Decline and queued events are never sent. |
| ZZ | **H-ZZ2.** When the visible banner belongs to another CMP, Decline does not reach Zaraz (no `zaraz.consent.set`). | The third-party CMP records a refusal, yet the Zaraz consent state stays unset or true. | The Zaraz state changes to false within 5 s of the click. |
| ZZ | **H-ZZ3.** Zaraz does not act on GPC (not documented). | A2 is the same as A0. | — |
| GW | **H-GW1.** First-party collect hits leave the browser before any choice at a rate close to Part A's third-party ad rate. | The A0 share of sites with first-party GA4/Ads hits before any choice. | — |
| GW | **H-GW2.** After Decline, first-party hits continue, and most declare *denied* ("denied-flag pings", legally ambiguous). A minority declare *granted* or no consent parameters (clear failures). | Hits sent after Decline, split by their `gcs`/`gcd` state; server-set identifiers after Decline. | No first-party hits after Decline. |
| WX | **H-WX1.** Wix native integrations follow the Wix policy: none before consent on sites whose `siteConsentPolicy` requires it. | No GA/Meta/Google Ads requests from the top frame in A0 or A1 on those sites. | Native-integration requests before any choice. |
| WX | **H-WX2.** Custom code (Essential by default), HTML embeds (`filesusr.com` iframes) and app iframes are outside the banner's control and send ad data before any choice and after Decline. | Ad beacons with origin `wix_embed_iframe` or `wix_app_frame`, or from custom-code tags, in A0/A1 on banner sites. | — |
| WX | **H-WX3.** On sites whose banner audience is EU-only, a California visitor gets the all-granted default policy and no banner. | `siteConsentPolicy` all true; no banner. | — (a description of US defaults, not a failure) |
| BC | **H-BC1.** Script Manager scripts in non-essential categories are held back until consent. | `text/plain` scripts stay unexecuted in A0 and A1. | Held-back scripts execute before any choice. |
| BC | **H-BC2.** Tags that bypass Script Manager (theme files, Essential-categorised pixels, channel apps) fire before any choice and after Decline. | Ad beacons in A0/A1 from vendors whose static tag was not `text/plain`. | — |
| All | **H-GPC.** None of the five setups documents GPC handling. We expect A2 to be close to A0, except where a CMP honours GPC (OneTrust, Usercentrics and others can be configured to). | — | — |

**Reading the results.**
- n is 60–80 per setup, so a 95% Wilson interval is about ±10–12 points at 50%.
- Differences between setups smaller than about 20 points are not interpretable.
- The pilot is meant to show *whether* the gap exists outside Shopify, and to size a later study.
- **Effective n after screening (§7).** Only WX and BC reach 80 sites. GW has about a quarter to a half of the planned size, and PT and ZZ are case studies (single digits). For PT and ZZ we report each site individually and no rates; for GW we report counts with Wilson intervals and no between-setup comparison.

## 9. Limitations

1. **Visible from the United States only.**
   - The EU/UK run was dropped (student's decision, 26 Sep). Every load runs from California, and no crawl runs from outside the United States.
   - Many banners are geo-targeted: Wix `eu_visitors`, Zaraz geo rules, CMP geolocation. So some sites show no banner to us, and many US defaults are opt-out by design. B2 therefore measures **what a US visitor sees**.
   - A1 is possible only where a banner with a first-layer Decline appears in California. Where none appears, only the A0/A2 contrasts are reported.
2. **Server-side forwarding is invisible** (ZZ, GW, and platform conversion APIs). We report proxy observables (§3, §4) and never claim receipt by a vendor.
3. **Bot handling.** An unmodified automated browser can be excluded by Zaraz's bot-score threshold, and treated differently by some CMPs (Part A found this for some Shopify CMPs). We do not evade either. "Zaraz did not load" is recorded as its own outcome. The human normal-browser check (Part C) could add a few B2 sites if the mentor agrees.
4. **Static screening misses things.**
   - CMPs and tags inserted by JavaScript or tag managers are invisible to a static fetch, so the "has CMP" requirement is a lower bound. PT/ZZ/GW sites without a static CMP may still show a banner.
   - Gateways set up **inside** a GTM container (`server_container_url`) are invisible statically. GW candidates are therefore the subset that serves the tag itself from a first-party or gateway host.
   - Custom Zaraz paths are found only through inline markers.
5. **Screening fetch bias.** The library user agent is refused (403/429) or blocked by `robots.txt` on a share of sites (§7). Candidates lean towards sites without aggressive bot protection.
6. **Purposive strata.** CF and J are oversamples chosen by hosting provider. Only R supports prevalence estimates, and its small counts give wide intervals. Rates in the pilot are **per selected site**, not population estimates.
7. **The DNS frame for Wix/BigCommerce** misses sites behind their own CDN or proxy (as in Part A for Shopify). For ranks above 200k, only the www host was resolved.
8. **Unofficial decoders.**
   - The `gcd` letter code is an unofficial decoding; it is validated against `gcs` on calibration loads, and `gcs` is used where the two disagree.
   - The Wix and BigCommerce consent-cookie formats must be confirmed on calibration loads.
9. **The consent tool may not be the banner.** A site can run several consent tools, for example a CMP plus Wix's native policy. The banner the crawler clicks is recorded, and results are split by which tool owns it.
10. **Too few Partytown and Zaraz sites (§7).** Static screening of about 5,000 reachable homepages, including Vercel/Netlify and Cloudflare oversamples, found Partytown worker scripts on 5 sites (plus the library alone on 16) and Zaraz on 1. H-PT and H-ZZ can therefore only be illustrated, not estimated. Zaraz may also be under-detected, because it may not be injected for clients it scores as bots (§2.2); a static fetch cannot tell "no Zaraz" from "Zaraz withheld".
11. **Detector revisions.** Markers changed twice during screening (00:05 PDT: CMP signatures; 03:30 PDT: protocol-relative Google URLs). All saved pages were re-analysed with the final version. Pages without a marker at screening time were not saved, so a later marker addition could not be applied to them. The fixes only removed false positives, so this does not bias the counts downwards.
12. **No legal conclusions.** B2 describes technical behaviour. Whether a given pre-choice or after-Decline request is unlawful depends on jurisdiction, purpose and exemptions, as in Part A.

## 10. Sources (read 26–27 Sep 2026)

- [PT-how] Partytown, "How Does Partytown Work": https://partytown.qwik.dev/how-does-partytown-work
- [PT-scripts] Partytown, "Partytown Scripts": https://partytown.qwik.dev/partytown-scripts
- [PT-forward] Partytown, "Forwarding Events and Triggers": https://partytown.qwik.dev/forwarding-events
- [PT-proxy] Partytown, "Proxying Requests": https://partytown.qwik.dev/proxying-requests
- [PT-tradeoffs] Partytown, "Trade-Offs": https://partytown.qwik.dev/trade-offs
- [ZZ-consent] Cloudflare Zaraz, "Consent management": https://developers.cloudflare.com/zaraz/consent-management/
- [ZZ-api] Cloudflare Zaraz, "Consent API": https://developers.cloudflare.com/zaraz/consent-management/api/
- [ZZ-settings] Cloudflare Zaraz, "Settings": https://developers.cloudflare.com/zaraz/reference/settings/
- [ZZ-faq] Cloudflare Zaraz, "FAQ": https://developers.cloudflare.com/zaraz/faq/
- [ZZ-gcm] Cloudflare Zaraz, "Google Consent Mode": https://developers.cloudflare.com/zaraz/advanced/google-consent-mode/
- [GW-gateway] Google, "Google tag gateway for advertisers": https://developers.google.com/tag-platform/tag-manager/gateway
- [GW-setup] Google, gateway setup guide: https://developers.google.com/tag-platform/tag-manager/gateway/setup-guide
- [GW-cf] Cloudflare, "Google tag gateway": https://developers.cloudflare.com/google-tag-gateway/
- [GW-sst] Google, "Server-side tagging: introduction": https://developers.google.com/tag-platform/tag-manager/server-side/intro
- [GW-sst-consent] Google, "Consent mode with server-side tagging": https://developers.google.com/tag-platform/tag-manager/server-side/consent-mode
- [WX-banner] Wix, "Cookie Banner Settings" (API reference): https://dev.wix.com/docs/api-reference/business-management/cookie-consent-policy/cookie-banner-settings/introduction and the Cookie Banner Settings object
- [WX-configs] Wix, "About the Consent Configs API": https://dev.wix.com/docs/api-reference/business-management/cookie-consent-policy/consent-configs/introduction
- [WX-apps] Wix, "Implement Cookie Consent Requirements": https://dev.wix.com/docs/build-apps/launch-your-app/legal-and-security/gdpr-compliance/implement-cookie-consent-requirements
- [WX-support] Wix Help Center, "Important Information About Editor Elements, Third-Party Apps, Custom Code, and the Cookie Banner": https://support.wix.com/en/article/important-information-about-editor-elements-third-party-apps-custom-code-and-the-cookie-banner
- [BC-consent] BigCommerce, "Set Cookie Consent Preferences": https://docs.bigcommerce.com/developer/api-reference/rest/storefront/consent/post-cookie-consent
- [BC-enum] BigCommerce, "ScriptConsentCategory" (GraphQL Storefront): https://docs.bigcommerce.com/developer/api-reference/graphql/storefront/types/enums/script-consent-category
- [BC-catalyst] BigCommerce, "Catalyst: Cookie Consent": https://docs.bigcommerce.com/developer/docs/storefront/catalyst/features/cookie-consent
- [BC-scripts] BigCommerce, "Scripts API": https://docs.bigcommerce.com/docs/integrations/scripts
- Tranco: Le Pochat et al., NDSS 2019; list L5PZ4. RDAP: ARIN (BigCommerce INTER-1370), RIPE (Wix 185.230.60–63.0/24). Cloudflare IP ranges: https://www.cloudflare.com/ips-v4

## 11. Files

| Path | What |
|---|---|
| `PROTOCOL.md` | This document |
| `candidates.csv` | One row per site × setup it qualifies for, with eligibility, tier, selection (`selected`/`reserve`/…), `measure_url` and static evidence |
| `vendor_endpoints_extra.json` | Additions to `crawl/vendor_endpoints.json`: 39 host entries, 21 first-party/context rules, consent-signal decoders and run-time markers. The original is untouched. |
| `inputs/` | RDAP record for BigCommerce, Cloudflare IPv4 ranges |
| `screen/` | `dns_platforms.py`, `build_queue.py`, `markers.py`, `screen_http.py`, `screen_runner.py`, `build_candidates.py` (run with `REANALYSE_ALL=1`), `report_screening.py` (§7 tables), `build_vendor_endpoints_extra.py`; `queues/` (seeded queues, `plan.json`); `raw/` (DNS flags, `screen_results.jsonl`, gzipped candidate homepages, logs, `screen_summary.json`) |
