# Figure takeaways (updated to the data)

One sentence per figure. "Planned" is the sentence in FIGURE_PLAN.md; "Now" is what the data support after the review revisions of 2026-09-26. Numbers come from `analysis/outputs/stats.json` (checked by `analysis/trace_check.py`).

## Figure 1: Where consent fails (situating the field)
- Planned: On Shopify stores, ad pixels run inside a sandbox that the cookie banner's script blocker cannot see; the only gate is Shopify's consent state, and for US visitors it defaults to 'allowed'.
- Status: supported for our California vantage point: Shopify's region default was 'allowed until choice' on 82% of stores.
- Now: On popular Shopify stores ad pixels run in a sandbox that cookie-banner blockers cannot see; at our California vantage point Shopify's gate defaulted to 'allowed' on 82% of stores, and a sandboxed ad pixel sent requests before any choice on 50% of stores that showed a consent banner (63% of stores without one).

## Figure 2: Measurement pipeline (methodology)
- Planned: We sample popular Shopify stores from a public ranking, load each under four controlled conditions, and attribute every ad request to its origin and payload.
- Status: supported with corrections: three base arms plus validation loads (repeats, and Brave's native GPC on 100 stores), with GPC emulated in Chromium.
- Now: We sampled 1,362 popular Shopify stores from the Tranco top-200k, loaded each under Default, Decline and GPC (plus repeats and a native-GPC check), and attributed every ad request to its origin, vendor, timing and payload.

## Figure 3: Pixels fire before any choice
- Planned: On stores that show a consent banner, sandboxed ad pixels usually fire before the visitor has made any choice.
- Status: partly supported; 'usually' is too strong overall (50% of banner stores) but holds where Shopify's default is 'allowed' (70%).
- Now: On half of the stores that show a consent banner (50%), and on 70% where Shopify's region default is 'allowed', sandboxed ad pixels send requests before any choice, and on 53% of the banner stores where they did, the first request left clearly before the banner was even visible.

## Figure 4: Blocked on paper
- Planned: Many consent tools declare a vendor as blocked or 'marketing' while that vendor's sandboxed pixel fires anyway; the gap depends on how the tool integrates with Shopify.
- Status: supported on a small readable base (21 stores, 3 tools); the differences between tools track Shopify's region default more than the integration mode.
- Now (revised after referee review): Where a consent tool's blocklist names an ad vendor as blocked and the tool had not itself consented for our browser, that vendor's own sandboxed pixel still fired before any choice on 7 of 14 stores (12 of 21 unconditioned), and, like for like, blocklist stores fired no less often than stores without a declaration (difference 14 pp, 95% CI -8 to 36): Shopify's state, not the blocklist, decided; in one re-check load the blocker neutralized a vendor's page tag while its sandboxed pixel sent requests on 5 stores.

## Figure 5: Do visitor choices work?
- Planned: Clicking Decline mostly stops sandboxed pixels only when the banner is wired to Shopify's consent API, and GPC is honoured unevenly.
- Status: revised. Shopify's gate held for pixels that declare the refused purpose (0 of 7,478 sale-declaring pixels started under GPC); after a working Decline and under GPC the fresh-page residuals were 23% vs 18%, against 45% under Default in the same window (paired difference Decline minus GPC 5.2 pp, 95% CI 0.2 to 10.2; exact McNemar p = 0.058): for post-choice persistence GPC's advantage was at most about 10 points, while over the whole visit a Decline user is exposed before the click, which GPC avoids.
- Now: Shopify honours a recorded refusal for pixels that declare the refused purpose, so what keeps firing after a working Decline (23% of stores on a fresh page) and under GPC (35% of stores that fired under Default) is pixels that declare no purpose (F4), pixels whose declared purpose the choice left allowed (after Decline, typically sale of data; under GPC, marketing), pixels started before the choice that kept sending, including unload beacons (F3), and CMP writes that lose the race (535 of 545 third-party 'marketing' sandboxes started before a CMP's automatic 'no').

## Figure 6: What reaches the vendors
- Planned: Whatever sits in the URL (including a creator's per-video campaign code) reaches ad vendors through the sandbox, and the findings are stable across repeat loads and native vs emulated GPC.
- Status: supported, now one message; validation moved to Fig S4d and the projection to a table (formerly Fig 5e). Panels in reading order: (a) URL share, (b) refusal signals, (c) the creator store (Store C), on which the per-video evidence rests.
- Now: 63% of sandboxed ad beacons carry the full landing URL, a creator's per-video code reached TikTok from its sandbox before any choice, and after a refusal Google's requests often carry a refusal signal of Google's own (Consent Mode 'denied', npa or rdp; 36% on the next page after Decline) while requests of vendors other than Google and Microsoft carry none that we can see.

## Supplementary
- S2: Shopify's own banner has the lowest pre-choice rate of any consent tool (18%) and also the most denying region defaults (98%), so tools cannot be ranked on these data.
- S3: Pre-choice firing on banner stores is about the same in each of the three larger Tranco rank buckets (47–51%); banner prevalence and the small-sample Decline residual vary more.
- S4: The crawler's banner, reject and click labels agree with the screenshots in 53/54, 52/53 and 35/35 audited loads (assistant labels, human re-labelling pending), and repeat loads agree with kappa 0.985.
- S5: How much of a vendor's tracking runs in the sandbox varies from 1% to 87% of its requests; TikTok (55%) and Pinterest (62%) send most requests from it, Google Ads (22%) and Meta (16%) mostly do not.
- S6: All 20 robustness variants give intervals that overlap the main estimates; beacon-only definitions lower the rates slightly.
