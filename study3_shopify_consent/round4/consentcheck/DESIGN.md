# ConsentCheck design notes

## Architecture today (command line)

```
consentcheck.js ──> robots.js ──> capture.js (x3 visits) ──> raw capture ──> analyze.js ──> result JSON ──> render.js ──> HTML
                                     │                         (optional .json.gz)   (pure)                       (pure)
                                     └─ crawl/lib: rawcdp, instrument, inject, vendors, probes
```

- **Capture** is the only part that needs a browser. It launches Playwright's Chromium with a fresh temporary profile, opens a second, raw Chrome DevTools Protocol (CDP) connection, and uses the study's `Instrumenter` to auto-attach to every page, out-of-process iframe and web worker (`Target.setAutoAttach` with `waitForDebuggerOnStart` and `flatten`). Every network request is recorded per target session, which is how a request is attributed to Shopify's STRICT worker, a LAX sandbox iframe (or a frame nested in it), an OPEN pixel script, or the main page. GPC is injected before any page script runs, in pages and frames (`Page.addScriptToEvaluateOnNewDocument`) and in workers (a `beforeScriptExecution` instrumentation breakpoint).
- **Page probes** from `crawl/lib/probes.js`: a banner observer (CMP selectors plus a generic fixed-position detector), `Shopify.customerPrivacy` readouts about once a second, the Decline finder (reject-text regex and CMP-specific reject selectors, never Accept) and a CMP/configuration probe (Pandectes, OneTrust, Cookiebot blocklists and others).
- **Analysis** (`lib/analyze.js`) is a pure function from the capture to verdicts, findings and fixes. Keeping it pure means that a saved capture can be re-analysed (`--from-raw`), that the study crawl's own captures can be replayed through it (`test/replay_crawl.js`), and that it can run unchanged in other environments.
- **Rendering** (`lib/render.js`) produces one self-contained HTML file (no external requests), with a light/dark palette, print styles, table captions and header scopes, and status given in words as well as colour.

Definitions follow the study (`analysis/common.py`): advertising vendors from `crawl/vendor_endpoints.json`, CORS preflights excluded, "sandboxed" = STRICT worker, LAX iframe or a frame nested in the LAX iframe, and "after Decline" split into the same page, unload beacons from containers that already existed before the reload, and the fresh page.

## Becoming a browser extension

The main benefit: an owner could test in their own browser, from wherever they are, without installing Node.

1. **Instrumentation.** An extension with the `debugger` permission can attach to a tab and send the same CDP commands (`chrome.debugger.attach`, `chrome.debugger.sendCommand`). The Instrumenter would need a small adapter that maps its `send(method, params, sessionId)` calls onto `chrome.debugger` (recent Chrome versions accept child-target sessions; confirm worker auto-attach on the minimum supported version). Chrome shows a "started debugging this browser" bar while it runs: visible automation, which suits the use rules.
2. **Fresh state per visit.** Use a dedicated profile or window, and clear the store's cookies and storage between visits with `chrome.browsingData.remove` scoped to the store's origin; the extension should refuse to run in the owner's everyday profile while they are logged in to the store admin.
3. **GPC visit.** Add the `Sec-GPC: 1` header with a `declarativeNetRequest` session rule and inject `navigator.globalPrivacyControl` through the same CDP calls used today.
4. **Decline.** Either the extension clicks as now, or it guides the owner ("click Reject now") and only records. Guided mode also works for banners in other languages.
5. **Analysis and report.** `analyze.js` and `render.js` run unchanged in the extension page once `crawl/lib/vendors.js` and `probes.js` load their two JSON files through `import` or `fetch` instead of `fs` (the only Node dependency in the shared code).
6. **Store review.** The `debugger` permission triggers a strong warning and extra review in the Chrome Web Store; plan for a clear privacy policy (no data leave the machine) and the same ownership prompt.

## Becoming a web app

A hosted service is easier to use but raises the misuse question: anyone could point it at any store.

- **Ownership check first.** Either a Shopify app (installed through Shopify's OAuth, so it can only test the store that installed it) or domain verification (a meta tag or file on the store, as search-console tools do). No free-form URL box.
- **A Shopify app can do more:** with read access to the store's pixel and customer-privacy settings through the Admin API it could name the exact custom pixel to fix, check the region settings directly, and re-test after the owner changes them.
- **Server side:** the same capture code in a queue of headless browsers; at most one run per store at a time, the same pacing, results kept only as long as the owner needs them, and no use of results for research without a separate ethics review and the owner's consent.
- **Regions:** a hosted service could run from several countries (for example the EU and the US), which the command-line tool cannot. That changes what is measured and, for research use, needs its own ethics review.

## Possible next steps

- Test a few pages per run (a product, a collection and the home page), and repeat each visit to report how stable a result is.
- An optional **Accept** visit for owners only (clearly separate from the research rules, which forbid Accept) to confirm that pixels do work after consent.
- A `--fail-on high` mode that returns a non-zero exit code, for use in continuous integration after theme or app changes.
- Wider Decline detection (other languages, second-layer "Reject all" in preference centres) and more consent apps' blocklist formats.
- Map app pixel API client ids to app names from the Shopify App Store, so unknown app pixels are named in the report.
