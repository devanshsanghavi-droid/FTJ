# ConsentCheck test vs. the study crawl: store S1154

ConsentCheck run: 2026-09-27T06:15:47.618Z (one visit per condition, 4 page loads). Crawl: 2026-09-26, loads A0, A1 (+ next page), A2. The store is named here only by its study code.

**Agreement: 28 of 28 checks.**

| Check | Crawl | ConsentCheck | Agree | Note |
|---|---|---|---|---|
| Shopify default before any choice: marketing allowed | True | True | yes |  |
| Consent tool | onetrust | onetrust | yes |  |
| Banner shown (Default or Decline visit) | True | True | yes |  |
| Decline control clicked | True | True | yes |  |
| Decline written to Shopify as an explicit "no" | recorded | recorded | yes | crawl: refusal_cat |
| GPC: Shopify recorded sale of data "no" | True | True | yes | crawl: cp_sale_end_A2 == False |
| Default visit: marketing allowed at the first reading | False | False | yes | both: an automatic "no" came first |
| Google: sent before any choice (Default) | True | True | yes |  |
| Google: sent from the sandbox before any choice | True | True | yes |  |
| Google: any sandboxed request after Decline (same page or next page) | True | True | yes |  |
| Google: GPC did not stop it (sent in the GPC visit) | True | True | yes |  |
| Google: sandboxed under GPC | True | True | yes |  |
| Meta: sent before any choice (Default) | True | True | yes |  |
| Meta: sent from the sandbox before any choice | False | False | yes |  |
| Meta: any sandboxed request after Decline (same page or next page) | False | False | yes |  |
| Meta: GPC did not stop it (sent in the GPC visit) | False | False | yes |  |
| Meta: sandboxed under GPC | False | False | yes |  |
| Microsoft: sent before any choice (Default) | True | True | yes |  |
| Microsoft: sent from the sandbox before any choice | True | True | yes |  |
| Microsoft: any sandboxed request after Decline (same page or next page) | True | True | yes |  |
| Microsoft: GPC did not stop it (sent in the GPC visit) | True | True | yes |  |
| Microsoft: sandboxed under GPC | True | True | yes |  |
| After Decline, fresh page: sending pixels (type:purposes) | CUSTOM:NONE | CUSTOM:NONE | yes | crawl: residual_composition window fresh_page |
| After Decline, unload beacons as the page reloads (vendors) | microsoft_uet | microsoft_uet | yes | crawl: residual_composition window unload |
| Installed pixels (count) | 16 | 16 | yes |  |
| Same pixel ids as the crawl | True | True | yes |  |
| Same type, container and purposes for every common pixel | True | True | yes |  |
| Pixels declaring no purpose (ids) | 243171669;276300117;293011797;3633021269 | 243171669;276300117;293011797;3633021269 | yes |  |

Timing (Default visit, ms after the navigation started): crawl first sandboxed ad request 821; ConsentCheck first sandboxed ad request 1021, automatic "no" from the consent tool 1334.
