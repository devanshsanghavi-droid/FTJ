# ConsentCheck

**Does your Shopify store's cookie banner actually control your ad pixels?**

ConsentCheck is a small, free, open-source tool for **Shopify store owners** to run on their own computer against **their own store**. It opens one page of the store in a real (automated) Chrome browser three times and writes a plain-language report:

- which advertising vendors received data **before the visitor made any choice**;
- whether each vendor's code ran **inside Shopify's pixel sandbox** (a web worker or hidden iframe, which a consent app's script blocking cannot reach) or **in the main page**;
- whether your consent app **passes the visitor's choice to Shopify's Customer Privacy API** (the only thing that controls sandboxed pixels);
- whether **Decline** and the browser's **Global Privacy Control (GPC)** signal stop each vendor;
- which installed pixels **declare no consent purpose** (Shopify starts those whatever the visitor chooses), or declare marketing but not "data sale" (GPC does not stop those);
- concrete fixes, in order, with links to Shopify's documentation.

It is built from the measurement crawler of the study *Consent Enforcement Gaps in Sandboxed Web Pixels: A Large-Scale Measurement of Shopify Storefronts* (1,362 Shopify stores from the Tranco top 200k, measured on 26 September 2026). Code and data: <https://github.com/devanshsanghavi-droid/FTJ>.

A sample report from a real store, with the store anonymised, is in [`test/sample_report.html`](test/sample_report.html) (JSON: [`test/sample_report.json`](test/sample_report.json)).

## Quick start

Requirements: Node.js 22 or newer, and Playwright's Chromium.

```sh
npm install                      # installs playwright
npx playwright install chromium
node consentcheck.js https://your-store.com/products/<slug>
```

Inside the study checkout nothing needs installing: ConsentCheck finds Playwright in `pilot/pixel_payloads/node_modules` and the crawler library in `crawl/lib`. Outside it, run `node tools/vendor_lib.js` once inside the checkout to copy the library into `vendor/crawl/`.

ConsentCheck first asks you to confirm that you own the store or are authorised to test it (use `--yes` in scripts). A run takes about 1–2 minutes and ends with two files next to where you ran it:

- `consentcheck-<host>-<date>.html`: the report (one self-contained file; open it in any browser, or print it);
- `consentcheck-<host>-<date>.json`: the same results as data.

Pick a normal product page. Use a page that `robots.txt` allows (ConsentCheck checks this and stops if it is disallowed).

### Options

| Option | What it does |
|---|---|
| `--out FILE` / `--json FILE` | where to write the report and the JSON |
| `--yes` | confirm non-interactively that you own the store or are authorised to test it |
| `--arms default,decline,gpc` | run only some of the three visits |
| `--utm QUERY` / `--no-tag` | change or drop the test tag added to the page address (default `utm_source=consentcheck&utm_medium=self-test&utm_campaign=consentcheck-<date>`, so you can filter these visits out of your analytics) |
| `--headed` | show the browser window while it runs |
| `--no-screenshots` | leave the two screenshots of the Decline visit out of the report |
| `--save-raw FILE` | also save the raw capture (gzipped JSON) |
| `--from-raw FILE` | re-analyse a saved capture without visiting the store |
| `--render FILE` | re-render the HTML from a JSON result |
| `--min-free-gb N` | refuse to start with less free disk (default 0.5 GB) |

Exit codes: `0` report written (whatever it found), `1` error, `2` ownership not confirmed, `3` robots.txt disallows the page or the site could not be reached, `4` not enough free disk.

## What it does

Each visit uses a **new, empty, temporary browser profile** (deleted afterwards):

1. **Default:** load the page and wait 15 seconds without clicking (the page is scrolled gently, as a visitor would).
2. **Decline:** wait up to 10 seconds for a cookie banner, click **only** its Decline / Reject control, watch 15 seconds, then load the same page once more and watch 10 seconds. This shows whether the choice is written to Shopify and whether pixels start again on the next page.
3. **GPC:** load the page with Global Privacy Control switched on (the `Sec-GPC: 1` header and `navigator.globalPrivacyControl` in every frame and worker, set before the page's own scripts run) and wait 15 seconds.

During each visit ConsentCheck attaches to every part of the page (the page, every iframe, every web worker) through the Chrome DevTools Protocol, so it can tell **which part of the page sent each request**. It reads Shopify's consent state from `window.Shopify.customerPrivacy` about once a second, reads Shopify's list of installed pixels and their declared purposes from the page, and reads the consent header Shopify sends with the page (`Server-Timing: _cmp`).

### How to read the verdicts

| Verdict | Meaning |
|---|---|
| **Sent data / Nothing sent** (before any choice) | any request to the vendor during the Default visit |
| **Shopify's pixel sandbox** | the request came from a Shopify web pixel running in a web worker (STRICT) or hidden iframe (LAX); only Shopify's consent state controls it |
| **Main page** | the request came from a script in the page itself (theme code, a tag manager, an app embed, or a Shopify pixel in OPEN mode); a consent app's blocker can reach it |
| **Stopped** | the vendor sent nothing after the Decline (or with GPC on) |
| **Kept sending briefly, then stopped** | a pixel that started before the click kept sending on the same page, or as the page unloaded, but did not start again on the next page |
| **Not stopped** | the vendor sent data on the fresh page after the Decline (or with GPC on) |
| **Is the Decline passed to Shopify?** | after the click, Shopify's Customer Privacy API reported `marketing: "no"` (and whether data sale was refused too) |

Vendors are recognised from the study's list of about 70 advertising and analytics endpoints (`crawl/vendor_endpoints.json`); only vendors marked as advertising appear in the vendor table.

## What it does not do

- **It is not legal advice.** It reports what the page's code did; whether that is lawful depends on your jurisdiction, notices and contracts.
- **It tests one location:** yours. Shopify and consent apps behave differently by region (for example, the EU and UK versus US states). Run it from the regions you care about, for example through a machine there.
- **It never clicks Accept**, so it cannot confirm that your pixels work after consent.
- **It tests one page, once per condition.** Pages load differently from run to run; re-run before drawing conclusions from a single difference. It does not test checkout, account pages or anything behind a login.
- **The browser is visibly automated** (headless Chrome's own user agent, automation flag on). Some consent apps and pixels behave differently for automated browsers. Confirm important results in an ordinary browser window.
- **It does not change your store.** The fixes are for you to apply in Shopify admin or in your apps.
- **The Decline finder** recognises English button labels ("Reject all", "Decline", "Only necessary", …) and the reject buttons of about 25 consent apps. If your banner has no such button on its first layer, ConsentCheck reports that and clicks nothing.
- **Unknown vendors** (not in the endpoint list) are not counted, and a small share of requests can be attributed to the wrong part of the page.

## Use rules (ethics)

ConsentCheck follows the same binding rules as the study's research crawler:

- **Only stores you own or are authorised to test.** The tool asks before every run.
- **Nothing beyond refusing:** it never logs in, creates accounts, adds to cart, submits forms or buys; on a consent banner it clicks only Decline / Reject, never Accept (a second check refuses any control whose text looks like Accept, Agree or Allow).
- **No disguise:** Playwright's unmodified Chromium with its default user agent and the automation flag on; no stealth plugins, no attempt to get around bot checks or CAPTCHAs. A page that blocks it is reported as not usable.
- **robots.txt respected:** it reads `/robots.txt` first (RFC 9309; a group for `consentcheck`, else `*`). If the page address with the test tag is disallowed it uses the plain address; if that is disallowed too, or `robots.txt` cannot be read because of a server error, it loads nothing.
- **Polite pacing:** one site per run, four page loads in all, at least 10 seconds between page loads.
- **Adult-content labels:** if the page carries an adult-content label (RTA or `rating` meta tag), it stops without interacting.
- **No telemetry:** results stay on your computer; nothing is sent to the authors. The report can contain screenshots of your store; share it with care, or use `tools/anonymize.js`.

Researchers using ConsentCheck on stores they do not own must work under their own ethics approval, exclude adult-content and child-directed sites before any visit, and follow their protocol's limits.

## Validation

- **Live test (26 Sep 2026, 23:15 PDT = 27 Sep 06:15 UTC):** one run (four page loads) on one store that the study's crawl had measured about 21 hours earlier (study code S1154; anonymised as "Store A" in the sample). ConsentCheck's verdicts matched the crawl's on **28 of 28 checks**, including which vendors sent data before any choice and from where, the Decline being written to Shopify, which vendor restarted on the fresh page versus only sending unload beacons, GPC being recorded yet not stopping two vendors, and the four pixels that declare no purpose ([`test/comparison_S1154.md`](test/comparison_S1154.md)).
- **Offline replay:** ConsentCheck's analysis code, run on the study crawl's saved captures of all 1,362 main-sample stores without visiting any site, reproduces the study's store-level results on 99.7–100% of stores per measure ([`test/replay_agreement.txt`](test/replay_agreement.txt); `python3 test/replay_agreement.py`).

## Files

```
consentcheck.js           command-line tool
lib/env.js                finds Playwright and the crawler library
lib/robots.js             robots.txt fetch and RFC 9309 matching
lib/capture.js            the three visits (fresh profiles, pacing, Decline click, GPC) and request attribution
lib/analyze.js            verdicts, findings and fixes (pure function of the capture)
lib/render.js             the single-file HTML report
tools/anonymize.js        make a shareable sample from a result
tools/vendor_lib.js       copy crawl/lib into vendor/ for a standalone release
test/                     sample report, live-test comparison, offline replay against the study crawl
DESIGN.md                 architecture, and how this could become a browser extension or web app
LICENSE                   MIT
```

## Licence and credit

Licence: MIT (`LICENSE`). ConsentCheck reuses the study crawler's instrumentation library (`crawl/lib`: CDP auto-attach, request attribution, GPC injection, consent-banner and Customer Privacy API probes, vendor map).

Author: Devansh Sanghavi (ORCID 0009-0002-7511-542X), <devansh.sanghavi@gmail.com>. Please cite the paper (see `CITATION.cff` at the root of the repository).
