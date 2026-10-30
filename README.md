# Consent Enforcement Gaps in Sandboxed Web Pixels: data and code

Code, pseudonymized data, figures and paper sources for the article **"Consent Enforcement Gaps in Sandboxed Web Pixels: A Large-Scale Measurement of Shopify Storefronts"** by Devansh Sanghavi (ORCID [0009-0002-7511-542X](https://orcid.org/0009-0002-7511-542X)), submitted to *Computers & Security*.

Repository: <https://github.com/devanshsanghavi-droid/FTJ> · Contact: devansh.sanghavi@gmail.com

## What the study is

Consent-management platforms (CMPs) on online stores block advertising tags until a visitor agrees. On Shopify, many app advertising pixels run inside Shopify's Web Pixels Manager instead: in web workers (STRICT) or sandboxed iframes (LAX) that a CMP's script blocker cannot see, gated only by Shopify's own consent state. The study asks whether those sandboxed pixels send requests before any consent choice, after a visitor clicks **Decline**, and under **Global Privacy Control (GPC)**, and whether CMPs that declare an ad vendor "blocked" actually stop it.

- **Main crawl (26 September 2026).** Shopify storefronts from the Tranco top 200k (list L5PZ4), stratified by rank bucket, plus a purposive stratum of stores linked from YouTube creators' videos; one residential connection in California, a fresh headless Chromium profile for every load. Arms: **Default** (no interaction), **Decline** (click only the banner's first-layer reject control, then reload), **GPC** (`Sec-GPC: 1` plus `navigator.globalPrivacyControl` in every frame and worker), with repeat and Brave validation arms.
- **Round 4 (27 September 2026).** *B1 expansion:* Shopify stores from Tranco ranks 200,001 to 1,000,000 chosen for a readable CMP blocklist. *B2 beyond Shopify:* a pilot on Wix, BigCommerce, Partytown, Cloudflare Zaraz and first-party tag-gateway sites. Same crawler, same arms (Default, Decline, GPC), `robots.txt` checked before every site.
- **Attribution.** Every request is recorded in the DevTools session of the target that issued it (page, iframe or worker), so requests from Shopify's sandboxes can be told apart from ordinary page tags. A researcher canary in the landing URL (`utm_campaign=cmpstudy-<store_id>`) traces what reaches the vendors.
- **ConsentCheck.** The measurement packaged as a command-line self-test that a merchant runs against their own store.

Every number in the paper traces to `study3_shopify_consent/analysis/outputs/stats.json` (rendered in `analysis/RESULTS.md`) or to `study3_shopify_consent/round4/analysis/stats_r4.json` (rendered in `round4/analysis/RESULTS_R4.md`); the few others (crawl log, pilot notes, literature) are traced by `paper/check_numbers.py`.

## Repository layout

```
README.md  LICENSE (MIT, code)  LICENSE-DATA (CC BY 4.0, data/figures/documents)  CITATION.cff  requirements.txt
reproduce.sh                  one command: regenerate figures, tables and RESULTS.md from the released outputs (below)
MANIFEST.tsv                  every file: bytes, SHA-256, PDF hash without creation date, source path, transformation
SHA256SUMS                    the same hashes in `shasum -a 256 -c` format
TABLES.tsv                    every CSV table: rows and columns
release_tools/check.py        verify (files vs MANIFEST.tsv) / compare (regenerated vs shipped files); standard library
pilot/pixel_payloads/         package.json + package-lock.json for Playwright (the crawler requires this path)
study3_shopify_consent/
  sample/                     sampling code (Tranco + DNS frame, verification, stratified draw, creator stratum),
                              SAMPLE_NOTES.md, sample.csv (store_id, rank bucket, design weight, Shopify markers),
                              creator_stratum.csv (store_id, token level), funnel_fig2a.csv, raw/ aggregate summaries
  crawl/
    CRAWL_NOTES.md            protocol, arms, attribution labels, deviations, validation (read this first)
    crawl.js, lib/            crawler: CDP auto-attach per target, GPC injection, vendor map, banner/Decline probes
    cmp_signatures.json       CMP detection signatures, integration modes, reject-control selectors
    vendor_endpoints.json     vendor endpoint map, advertising flags, Web Pixels URL patterns
    build_tables.py, summarize_crawl.py, failure_breakdown.py, breakdown_checks.py, build_*.py
    loads.csv, requests.csv.gz, consent_states.csv, consent_events.csv, cmp.csv, cmp_declared.csv, pixels.csv,
    gpc_checks.csv, canary_other.csv          the crawl tables (reduced; see "Pseudonymization")
    validation/, recheck/, endpoint_evidence/, static_mechanism/   validation arms, banner re-check, survey code
  analysis/
    run_all.sh                full main-crawl pipeline (needs the on-request raw captures)
    common.py, extract_*.py, build_store_table.py, gate_audit.py, analyze.py, models.py, checks.py,
    write_results.py, numreg.py, trace_check.py, merge_*_numbers.py, audit_sample.py
    RESULTS.md                all main-crawl results, definitions, checks and limitations (generated)
    outputs/                  stats.json, one CSV per figure panel, store_table.csv, store_vendor.csv, ad_requests.csv.gz,
                              sandbox_creations.csv, gate_audit.json, models, number registries, trace_check.txt
  figures/
    v7/                       THE PAPER'S FIGURES (Figs. 1-6, S1-S10, graphical abstract)
      DESIGN_V7.md            the binding figure specification (RESTRAINT.md: rules it keeps in force)
      style/                  figstyle.py, palette and TikZ styles, QA and palette gates, style sheet
      scripts/                derive_numbers.py (shared derived numbers), plan checks
      fig1/ ... fig6/, supp/, graphical_abstract/
                              per figure: build script, TikZ sources (*.tex), scripts/ (derive, panels, caption,
                              trace), panels/*.pdf, the composite PDF, caption_*.tex, alt text, derived_numbers.json,
                              number registries (*_numbers.csv) and the check reports (trace, QA, palette)
      All_figures_v7.pdf      every v7 figure in one file
    scripts/, panels/, schematics/, tables/, fig1_composite.*, colors.py, style.mplstyle, takeaways.md
                              the first (v1) figure set, regenerated by reproduce.sh; tables/ is still read by the
                              paper's supplementary tables
  review/human_relabel_kit/   blind re-labelling kit, text part: blank label sheets, keys, scoring script
  round4/
    expansion/                B1: screening code (dns_scan_ext.py, screen.py, static_detect.py, calibrate.py, robots.py,
                              build_candidates.py), SCREEN_NOTES.md, calibration.json, funnel.json;
                              crawl/: crawl_r4.js (the wrapper that runs crawl/crawl.js unchanged for both Round 4
                              sets), run_r4_crawl.sh, cmp_signatures.json, the crawl tables (reduced)
    beyond/                   B2: PROTOCOL.md, vendor_endpoints_extra.json, screen/ (screening code, plan.json, summaries),
                              crawl/README.md, inputs/cloudflare_ips_v4.txt
    analysis/                 run_r4.sh, r4_tables.py, r4_blocklist.py, r4_beyond.py, r4_write_results.py,
                              r4_trace_check.py, RESULTS_R4.md, stats_r4.json;
                              outputs/: main/, expansion/, beyond/ tables, blocklist_r4.json, number registry, trace
    consentcheck/             ConsentCheck: consentcheck.js, lib/, tools/, README.md, DESIGN.md, LICENSE,
                              test/ (anonymized sample report, live-test comparison, offline replay against the crawl)
  paper/
    main.tex, main_5p.tex, frontmatter.tex, body.tex, backmatter.tex, preamble.tex, supplement.tex, highlights.*
    sections/, captions/ (generated from figures/v7), tables/ (generated tables and their scripts), figs/ (figure PDFs)
    refs.bib, refs_prior.bib, elsarticle.cls, elsarticle-harv.bst
    build.sh, integrate_figures_v2.py, check_numbers.py, check_semantic.py, wordcount.py, make_submission.py,
    tools/pdfpages2png.swift
    main.pdf, supplement.pdf  the built manuscript and supplement
```

Column definitions are in `crawl/CRAWL_NOTES.md` section 2 (crawl tables) and `analysis/RESULTS.md` section 2 (analysis definitions); `TABLES.tsv` lists every table's columns. In the crawl tables `load_id` is `<store_id>__<arm>`. Arms are `A0` Default, `A1` Decline, `A2` GPC, `A0r`/`A2r` repeats and `V1` Brave. Store ids are `S0001` to `S1400` (main sample), `C001` to `C034` (creator stratum), `E0001` to `E0120` (Round 4 expansion) and `b2-PT`, `b2-ZZ`, `b2-WX`, `b2-BC`, `b2-GW` plus a number (Round 4 pilot: Partytown, Zaraz, Wix, BigCommerce, tag gateway).

## Reproduce

Requirements: Python 3.10+ with the packages in `requirements.txt` (`python3 -m pip install -r requirements.txt`, ideally in a virtual environment). For the TikZ figures and the paper also zsh and [Tectonic](https://tectonic-typesetting.github.io/) 0.17 (on `PATH`, or set `TECTONIC=/path/to/tectonic`) and the Arial font. Every script that used a local interpreter or TeX path in the working project reads `PY` and `TECTONIC` from the environment here.

**1. One command for the analysis outputs.**

```bash
./reproduce.sh                                 # or: PY=/path/to/python3 ./reproduce.sh
```

It (1) checks every file against `MANIFEST.tsv`; (2) regenerates the v1 data panels (`figures/panels/`) and the supplementary LaTeX tables (`figures/tables/`) from `analysis/outputs/`; (3) re-renders `analysis/RESULTS.md` and `figures/takeaways.md` from `stats.json` and runs `analysis/trace_check.py`, which fails unless every number in them is a registered rendering of a `stats.json` value; (4) rebuilds the v1 TikZ schematics if Tectonic and zsh are available on macOS with a working `swiftc` (for the PNG previews), and otherwise keeps the shipped ones; (5) compares everything it regenerated with the shipped files (`release_tools/check.py compare`). Text files must be byte-identical; matplotlib PDFs are compared without their creation date; images are identical only with the same matplotlib/FreeType versions and Arial, so an image difference is reported but is not an error.

**2. The paper's figures (`figures/v7/`).** Each figure has a build script that runs its steps in order and stops at the first failing check:

```bash
cd study3_shopify_consent/figures/v7
zsh fig1/build.sh;  zsh fig2/build_fig2.sh;  zsh fig3/build_fig3.sh
zsh fig4/build_fig4.sh;  zsh fig5/build_fig5.sh;  zsh fig6/build_fig6.sh
zsh supp/build_supp.sh;  zsh graphical_abstract/build.sh;  zsh style/build_style_sheet.sh
```

Steps: derive numbers (`scripts/derive_*.py` -> `derived_numbers.json`) -> panels (matplotlib, `scripts/make_*panels.py`) -> TikZ panels and composite (Tectonic) -> caption and alt text (`caption_*.tex`, `alt_text_*.txt`) -> trace check (every printed number traced to `stats.json` / `derived_numbers.json`) -> QA and palette gates. Three derive steps read raw captures, which are on request (`derive_fig1.py` and `derive_fig4.py` one re-check capture, `derive_fig2.py` the raw Decline records); without them the build scripts skip that step and use the shipped `derived_numbers.json`. From this repository, the captions, alt texts, number registries, traces and derived numbers of every figure regenerate byte-identically; the PDFs differ only in TeX's embedded timestamps, and the export manifests and QA reports, which record those, differ accordingly. The graphical abstract's final typography gate (`graphical_abstract/scripts/check_ga.py`) currently fails on the shipped graphical abstract itself (a number below its 18 pt rule); this is not a reproduction error. Preview PNGs need `paper/tools/pdfpages2png` (below).

**3. The paper.**

```bash
cd study3_shopify_consent/paper && zsh build.sh
```

`build.sh` copies the v7 figure PDFs and captions into `figs/` and `captions/` (`integrate_figures_v2.py`), regenerates the generated tables (`tables/*.py`) from the analysis outputs, compiles `supplement.tex`, `main.tex`, `supplement.tex` again (cross-references in both directions), `main_5p.tex` and `highlights.tex`, counts words (`wordcount.py`) and checks that every number in the text traces to a data source (`check_numbers.py`). Page previews need `tools/pdfpages2png` (macOS: `swiftc -O -o tools/pdfpages2png tools/pdfpages2png.swift`); without it they are skipped. `zsh build.sh flat` writes the single-folder submission version (`make_submission.py`).

**What the public data do not redo:** the step from raw browser captures to the crawl tables and `stats.json` / `stats_r4.json`. It needs the raw captures and the unreduced tables (on request, below). The released tables are enough to recompute the store-level results yourself: `analysis/outputs/store_table.csv` and `round4/analysis/outputs/expansion/store_table.csv` have one row per store with the per-arm flags behind the headline rates, and `round4/analysis/outputs/beyond/beyond_sites.csv` one row per pilot site.

### Full re-run from the raw captures (on request)

`study3_shopify_consent/analysis/run_all.sh` (zsh) runs the main-crawl pipeline: extract per-load probes and initiator stacks from `crawl/raw/`, build the store table, run the gate audit, the statistics (`analyze.py`) and the models (`models.py`), summarize the re-check, run the post-crawl checks (`checks.py`), regenerate the figures, write RESULTS.md and run the trace check. `study3_shopify_consent/round4/analysis/run_r4.sh` does the same for Round 4 (tables with the main pipeline's own code, blocklist estimands, beyond-Shopify analysis, RESULTS_R4.md, trace check). Both read the raw captures, the store lists with real domains and evidence files that are not in this repository, so they run in the on-request bundle, which is the original project tree. The crawl tables are rebuilt from raw captures with `python3 crawl/build_tables.py && python3 crawl/summarize_crawl.py`.

## Re-running the crawler

`crawl/crawl.js` is the crawler that produced the main data (usage in its header: `node crawl.js --conc 6 --arms A0,A1,A2 [--only S0001,C005] [--limit-stores N] [--plan-only]`); `round4/expansion/crawl/crawl_r4.js --set expansion|beyond` runs it unchanged for Round 4 (its header lists the asserted substitutions). The crawler reads its store list from `sample/sample.csv` and `sample/creator_stratum.csv` (Round 4: `candidates.csv` and the `plan_r4.json` that `--prepare` writes). The released copies of these files have no domains or URLs, so to re-run it you need the original store lists (on request) or your own list in the same format (`store_id`, `domain`, `product_url`, `bucket`, `weight`; creator stratum also `landing_url`, `token_level`, `token`). Playwright is loaded from `pilot/pixel_payloads/node_modules`: `cd pilot/pixel_payloads && npm ci && npx playwright install chromium`. Keep the politeness rules the crawler enforces: one store at a time per browser, at least 10 s between page loads on a site and 1 s between page loads overall, and never Accept, log in, add to cart or submit forms. Stores see the canary campaign `cmpstudy-<store_id>` in their analytics.

## ConsentCheck

`study3_shopify_consent/round4/consentcheck/` is a merchant self-test built from the crawler: `node consentcheck.js https://your-store.example/products/some-product` makes three visits with fresh profiles (Default, Decline, GPC) and writes a plain-language HTML and JSON report of which vendors received data before a choice, from the page or from Shopify's sandbox, and whether Decline and GPC stopped them, with fixes. It is meant for a store's owner, on their own store. See its `README.md` (requirements: Node.js 22+, Playwright's Chromium) and `test/` (an anonymized sample report, a live-test comparison with the crawl, and an offline replay against the crawl's captures).

## Environment and versions

| Component | Version used | Needed for |
|---|---|---|
| Python | 3.13.9 (Anaconda), macOS | analysis, figures, paper scripts, `reproduce.sh` |
| pandas / numpy / scipy / matplotlib | 2.3.3 / 2.3.5 / 1.16.3 / 3.10.6 | analysis, figures (`requirements.txt`) |
| pypdf, Pillow, requests, tldextract | 6.16.2, 12.0.0, 2.32.5, 5.1.2 | figure QA, contact sheets, sampling scripts |
| Arial (ArialMT, Arial-BoldMT, Arial-ItalicMT) | system font | pixel-identical figures |
| Tectonic | 0.17.0 | TikZ figures, Figure 1 composite, the paper |
| Node.js | 18 or newer for the crawler, 22 or newer for ConsentCheck (build machine: v22.23.2) | crawler, ConsentCheck |
| Playwright | 1.61.0 (`pilot/pixel_payloads/package.json`, lock file included) | crawler, ConsentCheck |
| Chromium | `chromium-headless-shell` 149.0.7827.55 (Playwright build), default headless user agent | crawl arms |
| Brave | 150.1.92.139 (Chromium 150.0.7871.114), headless, Shields off via a fresh profile | native-GPC validation arm |

## Pseudonymization

Stores and pilot sites appear only under the pseudonymous ids above. The release builder (kept with the author) produced this tree from the project files:

- **Removed columns:** store domains, Tranco ranks (the rank bucket and design weight are kept), page titles, homepage, product, landing and request URLs, creator channel names, campaign tokens and video ids, and free-text names that often carry a brand: custom pixel names, custom event names and the names of cookies sent or set.
- **URLs cut to their host:** session, frame, initiator, first-stack, GPC-check and autoblock URLs keep only the host.
- **Rare hosts generalized:** in every host column, a host seen for fewer than three stores (typically a vendor's per-customer subdomain or a store's own second domain) is replaced by its registrable domain if that is seen for three or more stores (`brand.vendor.tv` -> `vendor.tv`), and otherwise by `<rare-host>`.
- **Replaced strings:** every store or site host left in the text, including hosts a store redirected to, becomes `<store_id>.store.example`, and store brand words become `[<store_id>]`. Creator names, tokens and video ids become `[<id>-creator]` / `[<id>-video]`. Shopify shop ids, store file paths, product and collection slugs, analytics, tag-manager and advertiser account ids, and the store name in BigCommerce consent configurations become placeholders; digit runs in the CMP blocklist descriptions (`detail`, `evidence`) become `<n>`. The creator case study (C005) is called **Store C**, as in the paper, including in file names (`fig6b_store_c.csv`) and `stats.json` keys (`store_c`).
- **Scan:** every text file, every PDF's text and every file name was checked against all sampled and screened domains, hosts, brand words, creator names, tokens and video ids, and for personal data and credentials. It found no match.

**Residual risk.** Pseudonymous is not anonymous. Someone who crawls Shopify stores could still match a store by its combination of consent tool, vendors, Web Pixels ids, consent-string suffixes, banner button texts and timing. Using the data to re-identify stores is contrary to the purpose of this release. Merchants can ask for their store's records to be removed: devansh.sanghavi@gmail.com.

## What is not in this repository (available on request)

Withheld because they show store identity, contain third-party page content or code, or are raw captures that may hold third-party cookies or payload bodies set during crawling:

- the store-id-to-domain mapping and the full store and site lists (domains, Tranco ranks, URLs, titles, creator channels and tokens), including the crawl plans and the Round 4 candidate lists and screening queues;
- the unreduced crawl and analysis tables (full request, frame and initiator URLs and hosts, page titles, custom pixel and event names, cookie names);
- the raw browser captures (per-load JSON with request and response metadata, payload bodies up to 4,000 characters, frame trees and consent readings) of the main crawl, retried and superseded loads, the re-check (including its script-element logs), the pilots and Round 4, and the per-load caches derived from them;
- all screenshots and contact sheets of store pages, which the blind re-labelling kit needs, and the kit's title-screen sheets;
- saved third-party code and pages (Shopify's Web Pixels Manager and sandbox runtime, consent-tool scripts, store HTML), crawl logs with URLs, and the raw sampling and screening records (DNS scans, verification logs, homepages, the local copy of the Tranco list: get it from tranco-list.eu, list ID L5PZ4);
- ConsentCheck's live test on a real store (raw capture and the report before anonymization);
- the vantage kit for collaborators who re-run the crawl from another region (exact crawler code and store list, checksum-locked).

Requests from researchers: devansh.sanghavi@gmail.com. Data are shared for research use under conditions the author sets.

## Ethics

- **What was measured.** Public storefront pages and the third-party code on them. No human subjects and no personal data of real users.
- **How the crawler behaved.** A fresh temporary browser profile for every load; no accounts, logins, carts, forms or purchases; banners were only ever declined, never accepted; the unmodified headless user agent, so the browser was visibly automated; no circumvention of bot detection or access controls.
- **`robots.txt`.** The Round 4 screening and crawls and ConsentCheck fetch `robots.txt` before any other request and load a page only if it is allowed. The main crawl did not; a retrospective fetch found 20 of 1,427 stores that disallowed the exact landing URL, mostly because of the canary parameters (paper, Ethics; `RESULTS.md`).
- **Load on stores.** At least 10 s between page loads on a store, and between 3 and 11 page loads per store including re-runs and the re-check.
- **Exclusions.** Stores aimed at children or offering adult content were to be excluded; four stores found after the crawl are excluded from all analyses. The creator case study (Store C) is a documented exception (paper, Method).
- **Validation labels.** The screenshot audits, content screens and recall audit were made with AI assistance (Claude, Anthropic), not by an independent human rater; the blind re-labelling kit in `review/human_relabel_kit/` is released so that they can be checked.
- **Records created by our visits.** Visits may appear in merchants' analytics as a campaign named `cmpstudy`; CMPs and Shopify also wrote consent records during the loads.
- **Disclosure.** The findings were disclosed on 2 October 2026 to Shopify, Pandectes, OneTrust, Usercentrics/Cookiebot and TikTok (paper, Ethics).

## Licences

- **Code** (`.py`, `.js`, `.sh`, `.swift`, and the LaTeX/TikZ sources): MIT, see `LICENSE`. ConsentCheck carries the same licence in `round4/consentcheck/LICENSE`.
- **Data, figures and documents** (tables, JSON, figure PDFs and PNGs, the built paper, Markdown): CC BY 4.0, see `LICENSE-DATA`.
- **Third-party files:** `paper/elsarticle.cls` and `paper/elsarticle-harv.bst` are Elsevier's, under the LaTeX Project Public License. Third-party material the data describe (the Tranco list, Shopify's and the consent tools' code, store pages) is not included.

## Citation

Please cite the article and this repository (`CITATION.cff` has the same information):

```bibtex
@article{sanghavi2026consent,
  author  = {Sanghavi, Devansh},
  title   = {Consent Enforcement Gaps in Sandboxed Web Pixels: A Large-Scale Measurement of {Shopify} Storefronts},
  journal = {Computers \& Security},
  year    = {2026},
  note    = {Submitted}
}

@misc{sanghavi2026consentdata,
  author       = {Sanghavi, Devansh},
  title        = {Data and code for: Consent Enforcement Gaps in Sandboxed Web Pixels: A Large-Scale Measurement of {Shopify} Storefronts},
  year         = {2026},
  version      = {1.0.0},
  howpublished = {\url{https://github.com/devanshsanghavi-droid/FTJ}}
}
```

## Contact

Devansh Sanghavi, Los Altos High School, Los Altos, CA, USA: devansh.sanghavi@gmail.com (questions, data requests, removal requests).
