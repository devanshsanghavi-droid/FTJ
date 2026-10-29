# Consent Enforcement Gaps in Sandboxed Web Pixels: A Large-Scale Measurement of Shopify Storefronts: data and code

Data and code for the article **"Consent Enforcement Gaps in Sandboxed Web Pixels: A Large-Scale Measurement of Shopify Storefronts"** by Devansh Sanghavi (Los Altos High School; ORCID 0009-0002-7511-542X), submitted to *Computers & Security*.

> **Release status:** first public release (29 October 2026) of the 26 September 2026 measurement package. An updated release with the Round 4 expansion and beyond-Shopify crawls, the final figures, the paper sources and the ConsentCheck tool follows in this repository.

## What the study is

Consent-management platforms (CMPs) on online stores block advertising tags until a visitor agrees. On Shopify, many app advertising pixels run inside Shopify's Web Pixels Manager instead: in web workers (STRICT) or sandboxed iframes (LAX) that a CMP's script blocker cannot see. The study asks whether those sandboxed pixels send requests before any consent choice, after a visitor clicks **Decline**, and under **Global Privacy Control (GPC)**, and whether CMPs that declare an ad vendor "blocked" actually stop it.

Design, in brief (details in `study3_shopify_consent/crawl/CRAWL_NOTES.md` and the paper's Method section):

- **Sample.** Shopify storefronts from the Tranco top-200k (list L5PZ4), stratified by rank bucket (a census of the top three buckets and a random draw from the fourth; `sample/SAMPLE_NOTES.md`), plus a purposive stratum of stores linked from YouTube creators' videos. 1,362 of 1,400 main-sample stores and 34 of 34 creator-stratum stores had a usable load in all three base arms.
- **Crawl.** One live crawl on 2026-09-26 from a residential connection in California, USA, with a fresh headless Chromium profile for every load. 4,976 page loads were attempted. Arms: **Default** (no interaction), **Decline** (click only the banner's first-layer reject control, then reload), **GPC** (`Sec-GPC: 1` plus `navigator.globalPrivacyControl` injected into every frame and worker). Validation arms: repeats on 287 stores (274 usable main-sample stores) and native GPC in Brave on 100 (99 usable).
- **Attribution.** Every request is recorded in the DevTools session of the target that issued it (page, iframe or worker), so requests from Shopify's STRICT workers and LAX iframes can be told apart from ordinary page tags. A researcher canary in the landing URL (`utm_campaign=cmpstudy-<store_id>`) traces what reaches the vendors.
- **Gate audit.** Each configured pixel's declared purposes are joined with Shopify's consent state and with the moment its sandbox started.

All results, with their intervals and definitions, are in `study3_shopify_consent/analysis/RESULTS.md`, the single source for every number in the paper.

## Reproduce every figure and number: one command

```bash
python3 -m pip install -r requirements.txt     # pinned versions; a virtual environment is recommended
./reproduce.sh                                 # or: PY=/path/to/python3 ./reproduce.sh
```

`reproduce.sh` takes under a minute on a laptop and does five things:

1. checks that every file matches `MANIFEST.tsv` (size and SHA-256);
2. regenerates every data figure (`figures/panels/`: Figs. 1b, 1c, 3, 4, 5 and 6, and the supplementary panels `figS2` to `figS6`; the paper prints `figS6_sensitivity` as Supplementary Fig. S5 and gives the per-vendor panel `figS5` as a table) and the supplementary LaTeX tables (`figures/tables/`) from the CSV and JSON files in `analysis/outputs/`;
3. re-renders `analysis/RESULTS.md` and `figures/takeaways.md` from `analysis/outputs/stats.json`, and runs `analysis/trace_check.py`, which fails unless every numeric token in both files is a registered rendering of a `stats.json` value;
4. rebuilds the TikZ schematics (Figs. 1a, 2, S1) and the Figure 1 composite if Tectonic, zsh and macOS are available (the PNG previews use a small CoreGraphics tool); otherwise it keeps the shipped PDFs;
5. compares everything it regenerated with the shipped files (`release_tools/check.py compare`). Text files (RESULTS.md, takeaways.md, tables, number registries, trace check) must be byte-identical. Matplotlib PDFs are compared with their creation date removed. TeX-built PDFs (schematics, Figure 1 composite) always differ in bytes, because TeX writes a timestamp and a random document ID into compressed objects, so they are compared through the PNGs rendered from them. Images are identical only with the same matplotlib and FreeType versions and the Arial font installed; an image difference is reported, not treated as an error.

On the build machine (macOS, versions below), `reproduce.sh` ran on a fresh copy of this tree in about 12 s. The trace check passed, and every regenerated data panel (PNG, and PDF apart from its creation date), table, RESULTS.md, takeaways.md, number registry and trace-check report was identical to the shipped file. With Tectonic 0.17.0 the run took about 18 s: the rebuilt schematic and composite PNGs and `numbers.tex` were also identical, and the 8 TeX-built PDFs differed in bytes only, as step 5 explains.

What this does **not** redo from the public data: the step from raw browser captures to tables and to `stats.json`. That step needs the raw captures and the unreduced tables, which are available on request (next section). The public tables are enough to recompute store-level rates yourself: for example, `analysis/outputs/store_table.csv` has one row per store with the per-arm flags behind the headline rates.

## Full re-run from the raw captures (on request)

The complete pipeline is `study3_shopify_consent/analysis/run_all.sh` (zsh). In order, it: extracts per-load probes and initiator stacks from `crawl/raw/`; builds the store table; runs the gate audit, the statistics (`analyze.py`) and the models (`models.py`); summarizes the re-check crawl; runs the post-crawl checks (`checks.py`); regenerates all figures; and writes RESULTS.md and runs the trace check. It reads the raw captures, the unreduced tables with real store domains, the re-check raw files and several evidence files from the project's review notes. None of these are in this repository, so it runs only in the on-request bundle, which is the original project tree with the original (unpseudonymized) code and file names. In that tree, run `PY=/path/to/python3 zsh study3_shopify_consent/analysis/run_all.sh`. The released copy of `run_all.sh` differs from the original only in letting `PY` and `TECTONIC` be overridden.

The crawl tables themselves are rebuilt from the raw captures with `python3 crawl/build_tables.py && python3 crawl/summarize_crawl.py`. An internal methods review rebuilt all nine tables from the 4,976 raw records and found them byte-identical to the saved ones.

## Re-running the crawler

`crawl/crawl.js` is the crawler that produced the data (usage in its header: `node crawl.js --conc 6 --arms A0,A1,A2 [--only S0001,C005] [--limit-stores N] [--plan-only]`). It reads its store list from `sample/sample.csv` (`store_id`, `domain`, `product_url`, `bucket`, `weight`) and `sample/creator_stratum.csv` (`store_id`, `domain`, `landing_url`, `token_level`, `token`). The released copies of these two files have no domains or URLs, so to re-run the crawler you need either the original store list (on request) or your own list in the same format. The Brave arm expects Brave at its macOS default path (`BRAVE` in `crawl.js`). Keep the politeness rules the crawler enforces: one store at a time per browser, at least 10 s between page loads on a site, at least 1 s between page loads overall, and never Accept, log in, add to cart or submit forms. Note that stores see the canary campaign `cmpstudy-<store_id>` in their analytics.

## Environment and versions

| Component | Version used | Needed for |
|---|---|---|
| Python | 3.13.9 (Anaconda), macOS | analysis, figures, `reproduce.sh` |
| pandas / numpy / scipy / matplotlib | 2.3.3 / 2.3.5 / 1.16.3 / 3.10.6 | analysis, figures (`requirements.txt`) |
| pypdf, Pillow, requests, tldextract | 6.16.2, 12.0.0, 2.32.5, 5.1.2 | font check, contact sheets, sampling scripts |
| Arial (ArialMT, Arial-BoldMT, Arial-ItalicMT) | system font | pixel-identical figure PNGs (`figures/font_check.txt`) |
| Tectonic | 0.17.0 | TikZ schematics, Figure 1 composite |
| Node.js | 18 or newer (build machine: v22.23.2) | crawler |
| Playwright | 1.61.0 (`pilot/pixel_payloads/package.json`, lock file included) | crawler |
| Chromium | `chromium-headless-shell` 149.0.7827.55 (Playwright build), default headless user agent | crawl arms Default, Decline, GPC and repeats |
| Brave | 150.1.92.139 (Chromium 150.0.7871.114), headless, Shields off via a fresh profile's preferences | native-GPC validation arm |

The crawler loads Playwright from `pilot/pixel_payloads/node_modules`. Install it with `cd pilot/pixel_payloads && npm ci && npx playwright install chromium`. `figures/validate_palettes.sh` needs an external palette validator (set `VALIDATOR=`); its last output is `figures/palette_validation.txt`.

## Directory map

```
README.md  LICENSE  LICENSE-DATA  CITATION.cff  requirements.txt
reproduce.sh                  the one command (above)
MANIFEST.tsv                  every file: bytes, SHA-256, PDF hash without creation date, source, transformation
SHA256SUMS                    the same hashes in `shasum -a 256 -c` format
TABLES.tsv                    every CSV table: rows, columns
release_tools/check.py        verify / compare (standard library only)
pilot/pixel_payloads/         package.json + package-lock.json for Playwright (the crawler requires this path)
study3_shopify_consent/
  sample/                     sampling code (frame from Tranco + DNS, verification, stratified draw, creator stratum),
                              SAMPLE_NOTES.md, sample.csv (store_id, rank bucket, design weight, Shopify markers),
                              creator_stratum.csv (store_id, token level), funnel_fig2a.csv, raw/ aggregate summaries
  crawl/
    CRAWL_NOTES.md            protocol, arms, attribution labels, deviations, validation (read this first)
    crawl.js, lib/            crawler: CDP auto-attach per target, GPC injection, vendor map, banner/Decline probes
    cmp_signatures.json       CMP detection signatures, integration modes, reject-control selectors
    vendor_endpoints.json     vendor endpoint map, advertising flags, Web Pixels URL patterns
    build_tables.py, summarize_crawl.py, failure_breakdown.py, breakdown_checks.py, build_*.py
    loads.csv                 one row per store x arm (4,976 loads)
    requests.csv.gz           one row per vendor request (and Shopify WPM sandbox/manager URLs)
    consent_states.csv        Shopify Customer Privacy API readings (about once a second, plus at the click)
    consent_events.csv        visitorConsentCollected events
    cmp.csv, cmp_declared.csv detected CMPs; vendors a readable CMP configuration declares blocked or allowed
    pixels.csv                Web Pixels Manager configuration (type, runtime context, declared purposes) per store
    gpc_checks.csv            GPC injection readout per frame and worker
    canary_other.csv          third-party requests with the canary to hosts outside the vendor map
    crawl_summary.json, failure_breakdown.json, breakdown_checks.txt, logs/ (traffic counts, coordinator note)
    validation/               GPC injection self-test, live GPC summary, Brave Shields and farbling controls
    recheck/                  re-check crawl code and derived results (banner recall, blocker activity, robots.txt)
    endpoint_evidence/, static_mechanism/   code of the endpoint and mechanism surveys (their data: on request)
  analysis/
    run_all.sh                full pipeline (needs the on-request data)
    common.py, extract_*.py, build_store_table.py, gate_audit.py, analyze.py, models.py, checks.py,
    write_results.py, numreg.py, trace_check.py, audit_sample.py
    RESULTS.md                all results, definitions, checks and limitations (generated)
    audit_labels.csv, forced_click_audit.csv   screenshot-audit labels (made by the AI assistant; see Ethics)
    outputs/                  stats.json, one CSV per figure panel, store_table.csv, store_vendor.csv,
                              ad_requests.csv.gz, sandbox_creations.csv, gate_audit.json, models, number registries,
                              trace_check.txt
  figures/
    scripts/                  one script per figure (fig1bc, fig3, fig4, fig5, fig6, figS), shared figutil.py
    colors.py, style.mplstyle the single colour and style definition
    panels/                   final data panels (PDF + 600 dpi PNG)
    schematics/               TikZ sources, numbers.tex (generated from data), PDFs, PNG previews, build.sh
    tables/                   supplementary LaTeX tables written by figS.py
    fig1_composite.*          Figure 1 assembled at final size; takeaways.md (generated)
  review/human_relabel_kit/   blind re-labelling kit, text part: blank label sheets, keys, scoring script
```

Column-level definitions are in `CRAWL_NOTES.md` section 2 (crawl tables) and `RESULTS.md` section 2 (analysis definitions). `TABLES.tsv` lists every table's columns. In the crawl tables, `load_id` is `<store_id>__<arm>`. Arms are `A0` Default, `A1` Decline, `A2` GPC, `A0r`/`A2r` repeats and `V1` Brave. Store ids are `S0001` to `S1400` (main sample) and `C001` to `C034` (creator stratum).

## Pseudonymization

Stores appear only as pseudonymous ids. `build_public.py`, which is kept with the authors, produced this tree from the project files, as follows:

- **Removed columns:** store domains, Tranco ranks (the rank bucket and design weight are kept), page titles, homepage, product and landing URLs, creator channel names, campaign tokens and video ids.
- **URLs cut to their host:** frame URLs, worker URLs, initiator URLs and first-stack URLs keep only the host. Request URLs are removed, because the `host` column already holds the vendor host.
- **Replaced strings:** every store host left in the text is replaced by `<store_id>.store.example`, and store brand words by `[<store_id>]`. Creator names, tokens and video ids become `[<id>-creator]` or `[<id>-video]`. Shopify shop ids, store file paths and product or collection slugs become placeholders. The creator case study (C005) is called **Store C**, as in the paper, including in file names (`fig6b_store_c.csv`) and `stats.json` keys (`store_c`).
- **Scan:** a scanner checked every text file and every PDF's text against all sampled domains, hosts, brand words, creator names, tokens and video ids. It found no match.

**Residual risk.** Pseudonymous is not anonymous. Someone who crawls Shopify stores could still match a store by its combination of consent tool, vendors, pixel ids, consent-string suffixes and timing. Using the data to re-identify stores is contrary to the purpose of the release. The mapping from store ids to domains is available to researchers on request. Merchants can ask for their store's records to be removed: devansh.sanghavi@gmail.com.

## What is not in this repository (available on request)

These items are withheld because they show store identity, contain third-party page content or code, or are raw captures that may hold third-party cookies or payload bodies set during crawling:

- the store-id-to-domain mapping and the full store lists (domains, Tranco ranks, URLs, creator channels and tokens), including the crawl plan;
- the unreduced crawl tables (full request, frame and initiator URLs; page titles);
- the raw browser captures (per-load JSON with request and response metadata, payload bodies up to 4,000 characters, frame trees and consent readings), for the main crawl, retried and superseded loads, the re-check crawl (including its script-element logs) and the pilots, plus the per-load caches derived from them;
- all screenshots and contact sheets of store pages (main crawl and re-check), which the blind re-labelling kit needs, and the kit's title-screen sheets;
- saved third-party code and pages (Shopify's Web Pixels Manager and sandbox runtime, consent-tool scripts, store HTML);
- crawl logs with URLs, raw sampling records (DNS scan, verification log, homepages, frame-recall checks, creator candidates) and the local copy of the Tranco list (get it from tranco-list.eu, list ID L5PZ4);
- the vantage kit, for collaborators who re-run the crawl from another region; it locks the exact crawler code and store list with checksums.

Requests: devansh.sanghavi@gmail.com. Requests are answered for research use, with the data shared under conditions the authors set.

## Ethics

- **What was measured.** Public storefront pages only. There were no human participants and no personal data of real users.
- **How the crawler behaved.** Each load used a fresh temporary browser profile. The crawler never created accounts, logged in, added to cart, submitted forms or bought anything, and it clicked only the most privacy-protective banner option (Decline), never Accept. It used the unmodified headless user agent, so it was identifiable as automated, and it did not get around bot detection or access controls.
- **Load on stores.** At most one page load per store every 10 s. Counting re-runs, the Decline reload and the re-check, each store received at most 11 page loads, and 43 stores received more than seven. The crawler did not consult `robots.txt`. A retrospective fetch found that 20 of the 1,427 stores that served one disallowed the exact landing URL, mostly because of the canary's query parameters. Excluding every store flagged in the ethics review moves no headline rate by more than 0.4 percentage points (`RESULTS.md`, section 5).
- **Deviation.** The planned limit of about six concurrent browsers was exceeded: 578 loads ran at 6 and 4,398 at 10, after another process restarted the crawler. Per-site pacing did not change. The run segment is a sensitivity row in the sensitivity figure (`figS6_sensitivity`).
- **Records created by our visits.** Our visits may appear in merchants' analytics as a campaign named `cmpstudy`. CMPs and Shopify also wrote consent records during our loads (`RESULTS.md`).
- **Stores that should have been excluded.** Stores aimed at children or offering adult content were to be excluded. The sampling screen missed two adult-product stores, and flagged further titles await a human decision. The creator case study (Store C) is a documented, justified exception (paper, Method section).
- **Validation labels.** Every screenshot and content label so far was made by the AI assistant named in the paper (Claude, Anthropic, run in Claude Code). An independent human re-labelling is still required. The same assistant wrote the code, ran the crawls and the analysis, produced the figures and assembled this release.
- **Disclosure.** Disclosure to Shopify, the consent-tool vendors, TikTok and Store C's operator is planned before publication.

## Licences (suggested, to be confirmed by the authors)

- **Code** (`.py`, `.js`, `.sh`, `.swift`, `.tex` sources): MIT. See `LICENSE`.
- **Data and figures:** CC BY 4.0. See `LICENSE-DATA`.
- **Not covered:** third-party material (the Tranco list, Shopify's and the consent tools' code, store pages), none of which is included.

Code: MIT (`LICENSE`). Data: CC BY 4.0 (`LICENSE-DATA`).

## Citation

If you use the data or code, please cite the article and the dataset (`CITATION.cff` has the same information):

```bibtex
@article{blockedonpaper2026,
  author  = {Sanghavi, Devansh},
  title   = {Blocked on paper: How consent is lost between cookie banners and {Shopify}'s sandboxed web pixels},
  journal = {Computers \& Security},
  year    = {},
  volume  = {},
  pages   = {},
  doi     = {},
  note    = {Submitted}
}

@misc{blockedonpaper2026data,
  author       = {Sanghavi, Devansh},
  title        = {Data and code for: Blocked on paper: How consent is lost between cookie banners and {Shopify}'s sandboxed web pixels},
  year         = {},
  publisher    = {},
  version      = {1.0.0},
  doi          = {},
  howpublished = {}
}
```

In the article, cite the dataset as an Elsevier `[dataset]` reference.

## Contact

Devansh Sanghavi, devansh.sanghavi@gmail.com.
