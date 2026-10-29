# Study 3 live capture crawl: notes

The crawl ran on 2026-09-26 from 07:03 to 10:01 UTC (00:03–03:01 PDT), from a residential connection in California, USA. Every number below is read from a file in this folder, and the file is named next to it. Rates are **raw and unweighted**: store-level shares, no Tranco-bucket weights applied, with Wilson 95% intervals. Results are for the main sample unless marked "creator".

## 1. What was done

- **Plan** (`plan.json`, seed 20260926): 1,434 stores, made up of 1,400 main-sample stores and 34 creator-stratum stores.
  - Arm order was shuffled per store.
  - Arms were A0 Default, A1 Decline and A2 emulated GPC on every store.
  - Repeats A0r and A2r ran on a seeded 20% subsample (287 stores).
  - V1, native GPC in Brave, ran on a seeded 100-store subsample of the main sample.
  - Total planned loads: 4,976.
- **Captured.** 4,976 of 4,976 loads have a raw record (`raw/`).
  - Loads that qualify as usable ("ok" = HTTP 2xx/3xx, `window.Shopify` present, not blocked, more than 20 requests), from `crawl_summary.json → loads`:

    | Arm | ok / run |
    |---|---|
    | A0 | 1,397/1,434 |
    | A1 | 1,396/1,434 |
    | A2 | 1,397/1,434 |
    | A0r | 284/287 |
    | A2r | 284/287 |
    | V1 | 99/100 |

  - **Stores captured in all three base arms: 1,362 main and 34 creator** (`crawl_summary.json → stores_captured_all_base_arms`). This meets the target of at least 1,000 main-sample stores.
- **Outputs.**

  | File | Contents | Rows |
  |---|---|---:|
  | `loads.csv` | one row per store × arm | 4,976 |
  | `requests.csv.gz` | one row per vendor request, plus Shopify WPM sandbox/manager URLs | 586,678 |
  | `consent_states.csv` | consent-state readings | 73,027 |
  | `consent_events.csv` | consent events | 1,148 |
  | `cmp.csv` | one row per load × detected CMP | 3,368 |
  | `cmp_declared.csv` | one row per load × CMP × vendor it lists | 1,608 |
  | `pixels.csv` | WPM `webPixelsConfigList` per store | 18,128 |
  | `gpc_checks.csv` | one row per load × frame/worker | 67,596 |
  | `canary_other.csv` | third-party requests carrying the canary whose host is not in `vendor_endpoints.json` | 34,576 |

  - Raw evidence: `raw/*.json.gz` (226 MB) and 682 A1 screenshots in `screenshots/`.
  - Headline rates: `crawl_summary.json` (from `summarize_crawl.py`).
  - Failure and banner counts: `failure_breakdown.json`.
  - Two diagnostic breakdowns: `breakdown_checks.txt`.
- **Code.**
  - `crawl.js` (crawler, resumable per load);
  - `lib/rawcdp.js`, `lib/instrument.js` (CDP auto-attach and per-target network capture);
  - `lib/inject.js` (GPC injection);
  - `lib/vendors.js` (vendor map, WPM URL patterns, payload decoding);
  - `lib/probes.js` (banner detector, Decline finder, consent readout, CMP config probe);
  - `build_tables.py`, `summarize_crawl.py`, `failure_breakdown.py`, `breakdown_checks.py`;
  - `validation/` (§5, §6).
  - Rebuild the tables with `python build_tables.py && python summarize_crawl.py`.

## 2. How a load works (crawl.js)

- **A fresh browser for every load.** Each load launches its own browser with `launchPersistentContext` on a brand-new temporary profile directory, which is deleted after the load. No cookies, storage or cache carry over between arms or stores.
  - Settings: locale `en-US`, time zone `America/Los_Angeles`, viewport 1366×900.
  - User agent: Playwright's default headless UA (it contains `HeadlessChrome`). We did not change it and used no stealth.
  - Chromium: Playwright's `chromium-headless-shell`, version 149.0.7827.55, on 4,876 loads.
  - Brave: version 150.1.92.139 (Chromium 150.0.7871.114), headless, on 100 loads (`loads.csv → browser_version`).
- **URL.**
  - Main sample: `product_url` plus the canary `utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-<store_id>`.
  - Creator stratum: the creator's own `landing_url` plus the same canary (see §7).
- **The arms.**
  - **A0.** No interaction. We observe until 15 s after the `load` event (or 12 s after DOMContentLoaded if `load` never fires), with 6 passive mouse-wheel scrolls of 600 px, one per second, starting 2 s into the window.
  - **A1.** We wait up to 10 s after DOMContentLoaded for a visible banner, then:
    - take a screenshot (`pre`);
    - look for a Decline/Reject control and click it with Playwright, falling back to a forced click;
    - read the consent state at +1 s and +5 s, and take a second screenshot (`post`) at +2 s;
    - observe until 15 s after the click, with scrolling;
    - then load the **same URL again in the same browser** (the "next page") and observe 10 s after its `load` event.
  - The Decline finder follows `cmp_signatures.json → _meta.generic_reject`. It searches only inside the banner (light DOM plus open shadow roots):
    - It first takes the first visible control whose full text matches `text_regex`.
    - Otherwise it takes a CMP-specific reject selector, as long as the control's text does not match `never_click_regex` (unless it matches `text_regex`).
    - It never clicks Accept, Manage/Settings/Preferences or "Do not sell" links, and it never submits a form.
    - If the banner's first layer has no reject control, the load is recorded as `no_decline_option` and nothing is clicked.
    - If no banner appears, A1 is observed like A0.
  - **A2.** A `Sec-GPC: 1` header goes on every request, including worker requests (Playwright `extraHTTPHeaders`). `navigator.globalPrivacyControl=true` is injected into every frame and every worker before any of their scripts run (§5).
  - **V1.** Headless Brave with a fresh profile, Shields turned off in that profile (§6), and no injection. Observed like A0.
- **Recording, per request.** A second DevTools client connects to the browser's own debugging WebSocket (flat CDP, `lib/rawcdp.js`, `lib/instrument.js`). It auto-attaches to every target with `Target.setAutoAttach{autoAttach, waitForDebuggerOnStart, flatten}` and enables `Network` on every page, out-of-process iframe and worker session before resuming it. So every request is logged in the session of the target that issued it. We keep:
  - time since navigation start;
  - session type and worker URL;
  - frame URL;
  - initiator URL and stack;
  - method, resource type, status and failure;
  - the **names** (not values) of cookies sent;
  - the `Sec-GPC` header.

  For vendor, Shopify-pixel and third-party requests we also keep the URL (up to 3,000 characters) and the body (up to 4,000 characters, after gzip/deflate decoding).
- **Where a request came from** (URL patterns in `vendor_endpoints.json → shopify_web_pixels_urls`).

  | Label | Meaning |
  |---|---|
  | `strict_worker` | Issued inside a worker whose URL is a WPM STRICT bootstrap `/web-pixels@<h>/web-pixel-<id>@<v>/sandbox/worker.modern.js` |
  | `lax_iframe` | Issued by a frame whose URL is a WPM LAX sandbox `…/{app\|custom}/web-pixel-<id>@<v>/sandbox/modern/…` |
  | `open_pixel` | Main thread, with an initiator or stack containing `…/web-pixel-<id>@<v>~2/pixel.modern.js` |
  | `open_pixel_chain` | Initiated by a vendor library that an OPEN pixel loaded (e.g. `fbevents.js`) |
  | `wpm_main_proxy` | Main thread, with a stack containing the manager bundle `/cdn/wpm/b<h>m.js` (e.g. a sandboxed pixel's `sendBeacon` proxied to the top frame) |
  | `main_thread` | Anything else in the top document |
  | `subframe` | Any other iframe |
  | `other_worker` | Any other worker |

  - **"Sandboxed" means `strict_worker` or `lax_iframe`.**
  - Each sandboxed or OPEN request is joined to its pixel's configuration (`pixel_type`, `pixel_api`, `pixel_purposes`; `NONE` means the pixel declares no purpose). The join succeeded for 13,250 of 13,334 ad requests from STRICT workers and 18,097 of 18,169 from LAX iframes.
- **Payload flags.**
  - `has_canary`: the URL or body contains `cmpstudy-<store_id>`, checked raw, URL-decoded once or twice, and in base64-decoded chunks.
  - `has_full_url`: the canary **and** the landing path followed by `?`.
  - `has_creator_token`: the creator's token appears.
  - `event`: the first common event key found (`ev`, `en`, `event`, …).
- **Consent state.**
  - All ten `Shopify.customerPrivacy` getters, read about once a second plus at pre-click, click+1 s, click+5 s and the end of the load.
  - A `visitorConsentCollected` listener.
  - The navigation response's `Server-Timing _cmp` string, decoded (`loads.csv: cmp_header_raw, cmp_allow_m, cmp_region …`).
- **Banner detection** (init script in the top frame, every 250 ms for 45 s). A CMP container (from `cmp_signatures.json` `dom_selectors`) counts as a visible banner only if two things hold, with light DOM and shadow DOM both searched:
  - it contains at least one visible clickable control, meaning at least 30 px² on screen and passing `checkVisibility` with opacity and visibility checks through all ancestors;
  - it contains at least 20 characters of rendered text.

  A generic detector also accepts a fixed, sticky or dialog element with cookie/privacy wording and a visible consent button.
- **What CMPs declare** (`cmp.csv`, `cmp_declared.csv`). For each CMP whose config we can read, each vendor it lists gets `declared_prechoice` and `declared_after_decline` (blocked or listed_allowed). Readable configs:
  - Pandectes v4: `PandectesSettings` or `PandectesRulesSettings`, fields `blocker.patterns.blackList[cat]` and `defaultBlocked`.
  - Pandectes v5: `window.pandectesRulesSettings.blocker.{scripts,iframes,pixels}[cat]`. It is opt-in only in the regions listed under `regions.strict`, which does not include US-CA.
  - OneTrust: the `OtAutoBlock.js` map from URL to category, compared with `OnetrustActiveGroups`.
  - Cookiebot: the `configuration.js` tags plus `data-blockingmode`.

  Other CMPs: we record detection and their own consent objects only. A CMP counts as detected if there is script-URL, cookie or CMP-specific global evidence. Generic globals such as `__tcfapi` and generic DOM classes such as `.cc-window` are kept only as `cmps_weak_only`.
- **Pixel configuration** (`pixels.csv`): the WPM `webPixelsConfigList`, parsed from the navigation HTML (CDP `getResponseBody`) with a DOM fallback. Found on 4,827 of 4,857 ok loads (`failure_breakdown.json`).

## 3. Headline raw rates (main sample; `crawl_summary.json`)

**Before any choice (A0)**
- A visible banner appeared on 410/1,362 stores (30.1%, CI 27.7–32.6).
- On those banner stores, an ad-vendor request fired before any choice on 358/410 (87.3%, CI 83.8–90.2).
- A **sandboxed** ad request fired before any choice on 205/410 (50.0%, CI 45.2–54.8).
- By Shopify region mode (`_cmp` header):
  - opt-out (M allowed): 165/236 (69.9%, CI 63.8–75.4);
  - opt-in (M denied): 40/167 (23.9%, CI 18.1–31.0).
  - The opt-in cases are mostly custom LAX pixels declaring no purpose or only SALE_OF_DATA, plus some STRICT app pixels (`breakdown_checks.txt`).
- On 151/205 of those stores (73.7%), the first sandboxed ad request came before the banner was visible. Medians: 1,336 ms to the first sandboxed ad request, 1,715 ms to the banner.

**Decline (A1)**
- A banner was found on 407/1,362 stores. Of those, 165/407 (40.5%) had no reject option on the first layer, and 242 were clicked.
- After the click, Shopify reported `marketingAllowed()=false` on 202/242 (83.5%).
- Sandboxed ad requests:

  | Moment | Stores |
  |---|---|
  | Before the click | 105/242 |
  | After the click, same page | 32/242 (13.2%) |
  | On the next page | 74/242 (30.6%, CI 25.1–36.6) |

  - Of the 105 stores with sandboxed ad requests before the choice, 71 (67.6%, CI 58.2–75.8) still had them on the next page.
  - Any ad request on the next page: 200/242 (82.6%).
- The next-page sandboxed requests are mostly custom LAX pixels with no declared purpose, plus TikTok, Pinterest and Snap STRICT app pixels. 54 of the 74 stores had `marketingAllowed()=false` at the end (`breakdown_checks.txt`).

**GPC (A2, emulated)**
- Shopify reported `saleOfDataAllowed()=false` on 1,169/1,172 loads that returned a consent state (99.7%).
- Among the 803 stores where a sandboxed ad request fired under Default, 279 (34.7%, CI 31.5–38.1) still sent one under GPC.
- Any ad request still fired on 1,216 of the 1,258 stores that had one under Default (96.7%). The median store's ad-request count under GPC was 0.63 of its Default count.
- Per vendor, stores where the vendor fired under Default that still had it under GPC:

  | Vendor | Still fired under GPC |
  |---|---|
  | TikTok | 139/468 (29.7%) |
  | Pinterest | 103/342 (30.1%) |
  | Snap | 132/241 (54.8%) |
  | Meta | 390/982 (39.7%) |
  | Google Ads | 1,088/1,125 (96.7%) |

- The Google & YouTube app declares no purposes, which explains Google Ads' high rate.

**Canary**
- 78,734 of 107,295 ad beacons carried the canary (73.4%).
- 76,401 carried the full landing URL (71.2%).

**Creator stratum** (small n): sandboxed ad requests before the choice on 5/13 banner stores; under GPC 6/19 still sent them.
- Store C (C005; `store_c_C005_quicklook.txt`):
  - It served a cached page whose consent string was generated for an Arizona visitor (`3.AMPS_USAZ`, `cf-cache-status: HIT`) in all 5 loads.
  - TikTok's STRICT pixel sent 4 beacons carrying both the canary and the `desc-VideoToken` token in A0, A0r and A1, before the click.
  - TikTok sent nothing in A2, A2r, or after Decline.

## 4. Failures and blocking (`failure_breakdown.json`)

- 119 of 4,976 loads, across 38 stores, are not "ok":

  | Reason | Loads |
  |---|---:|
  | Redirect to **google.com** instead of the store (bot handling; `final_host`) | 71 |
  | Product page gone (HTTP 404) | 29 |
  | No `window.Shopify` | 7 |
  | DNS failure | 6 |
  | HTTP 403 | 3 |
  | HTTP 402 (store unavailable) | 3 |

  - 23 stores look like blocking: 403, off-site redirect or bot wall.
  - We did not try to get around any of it.
- **Retries.** 19 loads failed with transient timeouts. They were retried once, and all 19 succeeded; the first attempts are kept in `raw_failed_attempt1/`.
- **Challenge-page words.** The words "captcha" and "access denied" appear on 50 normal storefront loads (15 stores), for example in reCAPTCHA notices. They count as blocking only when there is no `window.Shopify`.

## 5. Validation of the GPC injection (A2)

- **Method.**
  - Every page and iframe session gets the injection through `Page.addScriptToEvaluateOnNewDocument` before it is resumed, plus a Playwright init script.
  - For workers, `Runtime.evaluate` on a worker that is still paused at start **crashed the renderer** in this Chromium build (reproduced in testing). So the injection instead sets a Debugger instrumentation breakpoint `beforeScriptExecution`, resumes the worker, injects when it pauses just before its first script, then removes the breakpoint and resumes.
- **Local test** (`validation/gpc_injection_selftest.js`, output in `validation/gpc_injection_selftest_output.txt`).
  - In 20 of 20 runs, the **first statement** of every target read `navigator.globalPrivacyControl === true`. The targets were the main frame, a same-site sandboxed iframe (allow-scripts, opaque origin, like Shopify LAX), a cross-site iframe, a dedicated worker created with `credentials:'omit'` (like STRICT), a nested worker, and a blob worker created inside the sandboxed iframe.
  - `Sec-GPC: 1` was present on the worker script, `importScripts` and `fetch` requests (20/20 each).
  - Control without injection: 0/3 true.
- **Live, in Shopify's sandboxes** (`validation/gpc_live_summary.json`).

  | A2 (emulated GPC) | Result |
  |---|---|
  | STRICT workers: injection OK and marker present | 4,720/4,720 |
  | STRICT workers: worker's own code added globals after the injection (the injection came first) | 4,720/4,720 |
  | Other workers reading `true` | 848/848 |
  | LAX sandbox iframes reading `true` | 2,735/2,735 |
  | `Sec-GPC: 1` on page requests | 710,348/710,348 |
  | `Sec-GPC: 1` on worker requests | 9,348/9,348 |

  In A0 every frame and worker read `undefined`: Chromium has no native GPC.
- **Finding: Shopify's STRICT sandbox erases `navigator`.**
  - At the end of every load, pixel code inside a STRICT worker read `navigator.globalPrivacyControl` as `undefined`. The property exists, but its value has been overwritten. This held in 4,720/4,720 STRICT workers under emulated GPC and in 382/382 under Brave's native GPC.
  - The STRICT sandbox runtime (`validation/shopify_worker_code/wpm_sandbox_strict_sc8540278m.js`, fetched once) has an overwrite table that includes `navigator:[!0,{userAgentData:!1}]` and `WorkerNavigator:!0`. So every navigator property except `userAgentData` is replaced with undefined.
  - Consequence: GPC cannot reach STRICT pixel code through the navigator. It acts only through Shopify's consent state (the WPM gate) and the `Sec-GPC` header on its requests.
  - This supports the mechanism note's correction that failures are not "the emulation missing workers".

## 6. Brave V1 (native GPC): it ran

- **Shields off, via the fresh profile's Preferences only.** Each load writes `profile.default_content_setting_values.braveShields = 2` into a new profile. The user's Brave profile was never touched.
  - A wildcard exception (`"*,*"`) is dropped by Brave (`validation/brave_shields_test.json`). The default value does stay in place (`validation/brave_shields_test.jsonl`).
- **Positive control** (`validation/brave_farbling_control.json`, local page only). With default Shields, Brave randomizes `hardwareConcurrency` (it reported 5 on 2 of 3 runs) and the canvas output. With the preference set, it returned the true 12 and identical canvas output on 3/3 runs, so Shields were off.
- **Trackers load** (`validation/v1_shields_check.json`, 100 stores, V1 compared with A2):
  - 0 `ERR_BLOCKED_BY_CLIENT` responses;
  - known tracker libraries loaded on 96/100 stores in both browsers (1,513 loads in V1, 1,492 in A2).
  - Playwright's default `--disable-component-update` flag also means Brave's ad-block lists never download in these profiles.
- **GPC was on.**
  - `Sec-GPC: 1` on 33,842/33,842 V1 requests that carried header information. Brave does not report header details for worker requests, so the worker header is not observed.
  - `navigator.globalPrivacyControl=true` in 710/710 frames and in 50/50 workers outside STRICT sandboxes.
  - STRICT workers read `undefined` (§5).
- **V1 vs emulated A2 agreement** on whether any sandboxed ad request fires: 99/99 store pairs (21 fired in both). Shopify reported `saleOfDataAllowed()=false` on 88/88 V1 loads that returned a state.
- **Repeat agreement** on the same measure: A0 vs A0r 282/284; A2 vs A2r 284/284.

## 7. Deviations, changes during the run, and limitations

- **Concurrency changed mid-crawl by another session, not by this agent.**
  - The first 578 loads ran at 6 concurrent browsers.
  - At 07:35 UTC a process from a "coordinating session" put `STOP` in place, waited for this crawler to exit, and restarted the same code, plan and seed with `--conc 10`. It wrote `logs/COORDINATOR_NOTE.txt` saying this was "at the user's request".
  - 4,398 loads ran at 10 concurrent browsers. The 19 retries ran at 6 (`failure_breakdown.json → status_log_lines_by_segment`).
  - **This is above the task's limit of about 6 concurrent contexts.** I could not verify the stated user request.
  - Per-site politeness did not change, because the same code applied to every run: one store at a time per worker, at least 10 s between page loads on a site, at least 1 s between page loads globally.
  - Timing measures may differ between the two segments; the run segment should be treated as a covariate.
- **Banner detector replaced after 510 loads.**
  - The first detector counted Consentmo's empty, invisible full-screen wrapper as a banner. This produced false "banner present / no_decline_option" results; screenshots showed no banner.
  - Those 510 loads were moved to `superseded_v1_detector/` and not used.
  - All 4,976 loads in `raw/` use the final detector, checked on 12 known stores in `validation/pilot_runs/check_v3_detector/`.
- **Next-page navigation in A1** (added). We reloaded the same URL once, at least 15 s after the click, to test "Decline acts from the next page" (P3). This added 257 page loads.
- **Creator stratum.** We loaded the creator's `landing_url` (plus the canary), not `product_url`, so the creator or per-video token is present (Fig 6b). Store C was kept by design, as in the sample stage, although it sells children's products. It is a retail store for adult buyers, and we only loaded pages.
- **Headless UA.** The UA says `HeadlessChrome`, and we did not hide it. Meta's `fbevents.js` is known to drop events for headless browsers, so Meta beacons are undercounted, while library loads are not. 71 loads were redirected to google.com.
- **Decline limits.**
  - We clicked only first-layer reject controls. So 167 A1 loads with a banner have `no_decline_option`, many of them US "notice-only" banners (`failure_breakdown.json → A1_no_decline_by_cmp`).
  - 12 clicks needed a forced click, and the banner was still visible 2 s later on 12 loads.
  - Banners inside iframes are not clicked.
  - Selectors marked `unverified` in `cmp_signatures.json` still need the manual screenshot audit (Fig S4). 682 screenshots are available for it.
- **Declared blocklists** are readable only for Pandectes, OneTrust (only when `OtAutoBlock.js` loads successfully; a failed or blocked load leaves the config empty) and Cookiebot. Other CMPs have detection only.
- **Timing base.** Request times come from CDP wall and monotonic clocks relative to the first main-frame document request. Banner times are page `performance.now()` values mapped through `performance.timeOrigin`. The two differ by milliseconds.
- **Scrolling.** In A0, A2 and V1 we scrolled passively. A CMP that treats scrolling as consent would show up as a `visitorConsentCollected` event in `consent_events.csv` without any click; this has not been analysed yet.
- **Disk.** The machine had about 3.3 GB free. The crawler stops by itself below 1.3 GB, which never happened. Bodies and URLs are truncated as described in §2.
- **Politeness.** Loads per store: 3–6, plus one next-page load after a successful Decline (`logs/traffic_counts.json`).
  - Pilots and checks: 24 + 12 loads (`validation/pilot_runs/`) and 5 Brave loads on s0347.store.example (`validation/brave_*`). Two earlier pilot directories were deleted: a first 6-store pilot, and a 12-store check of an intermediate detector.
  - Plain static fetches: 3 (one Pandectes rules file, one Shopify worker bootstrap, one sandbox runtime).
  - No logins, forms, carts or Accept clicks.

## 8. Final-audit re-check (2026-09-26, 15:33–15:41 UTC)

- `recheck/recheck.js` (derived from `crawl.js`; same browser, fresh temporary profiles, pacing, landing URL and canary): one load per store, **no interaction at all** (no clicks, no scrolling), viewport screenshots at about 3, 6 and 10 s after `load`, a log of every `<script>`/`<iframe>` element added to the top document and of every change to its `type`/`src`, and a final snapshot of script elements.
- Stores (`recheck/build_list.py` → `recheck/recheck_list.csv`, 129 stores): the 80 stores with `shouldShowBanner()` true in A0 but no detected banner, a seeded random 30 of the 872 other no-banner stores, and the 21 blocklist stores. The child-directed motivating store (C005) was not loaded.
- 129 loads, 128 usable. Results: `recheck/analyze_recheck.py` → `recheck/recheck_summary.json`, `recall_by_store.csv`, `blocker_by_store.csv`, `blocker_by_entry.csv`, `missed_banner_stores.csv`.
- Screenshot labels (`recheck/sheets/labels_assistant.csv`) were made by the AI assistant, blind (neutral codes, random order; key in `sheets/blind_key.csv`); human re-labelling pending (`../review/human_relabel_kit/`).
- Also run: `recheck/robots_check.py` (one `robots.txt` request per store, C005 excluded) → `recheck/robots/robots_summary.json`; `../sample/frame_recall.py` (frame-recall check) → `../sample/raw/frame_recall/frame_recall_summary.json`.
- Noticed during the re-check: the sampling keyword screen missed two adult-product stores (S0356, S0614) and a toy retailer (S1292, loaded once in the re-check before it was noticed). See `../review/human_relabel_kit/README.txt`.
