"""Write analysis/RESULTS.md and figures/takeaways.md. Every number is pulled from outputs/stats.json through
numreg.N(), which records it in outputs/number_registry_*.csv for trace_check.py.
Revised 2026-09-26 after the methods, novelty, claims/ethics, figures and format reviews (review/figure_fixes.md)."""
import os

import numreg
from numreg import N
from common import OUT, STUDY

G = numreg.get


def R(key, f='pct1'):
    """'k of n (p%, 95% CI lo–hi%)' from a Wilson record."""
    return f"{N(key + '/k')} of {N(key + '/n')} ({N(key + '/p', f)}%, 95% CI {N(key + '/lo', f)}–{N(key + '/hi', f)}%)"


def RC(key, f='pct1'):
    """Wilson record (primary) plus the cluster-bootstrap sensitivity interval."""
    return (f"{N(key + '/k')} of {N(key + '/n')} ({N(key + '/p', f)}%, 95% CI {N(key + '/lo', f)}–{N(key + '/hi', f)}%; "
            f"cluster bootstrap by consent tool {N(key + '/cb_lo', f)}–{N(key + '/cb_hi', f)}%)")


def RK(key, f='pct1'):
    """'k of n (p%, 95% CI lo–hi%)' with the Korn-Graubard interval clustered by store (entry-, start- and pair-level shares)."""
    return (f"{N(key + '/k')} of {N(key + '/n')} ({N(key + '/p', f)}%, 95% CI {N(key + '/kg_lo', f)}–{N(key + '/kg_hi', f)}%, "
            f"clustered by store)")


def D(key, f='pct1'):
    """A risk difference record: 'd pp (95% CI lo to hi)'."""
    return f"{N(key + '/diff', f)} pp (95% CI {N(key + '/diff_lo', f)} to {N(key + '/diff_hi', f)})"


def PC(key, f='pct1'):
    return f"{N(key + '/p', f)}%"


def CI(key, f='pct1'):
    return f"{N(key + '/lo', f)}–{N(key + '/hi', f)}%"


def KN(key):
    return f"{N(key + '/k')}/{N(key + '/n')}"


def OR(i, lst='terms_list'):
    b = f'models/{lst}/{i}'
    return f"OR {N(b + '/OR', 'f2')} (95% CI {N(b + '/lo', 'f2')}–{N(b + '/hi', 'f2')})"


def s2(name):
    """Index of a consent tool in the S2 list (the key is computed; numbers still come from stats.json)."""
    return [r['cmp'] for r in G('supp/S2')].index(name)


def det(name):
    """Index of a consent product in stats.json['automation']['detection']['rows'] (the key is computed; numbers come from stats.json)."""
    return [r['cmp'] for r in G('automation/detection/rows')].index(name)


GB = 'Blocker only ~1 unknown ~1 none'
GU = 'unknown ~1 no record'


def results():
    numreg.reset()
    L = []
    w = L.append
    i_sh, i_pa, i_ot = s2('shopify_native'), s2('pandectes'), s2('onetrust')
    w('# Study 3 results: sandboxed Shopify pixels vs consent choices')
    w('')
    w('Analysis of the live crawl of 2026-09-26 (residential vantage point, California, USA), revised the same day after five internal '
      'reviews (`review/figure_fixes.md`). Every number in this file is rendered by `analysis/write_results.py` from '
      '`analysis/outputs/stats.json` and is checked by `analysis/trace_check.py` (result in `analysis/outputs/trace_check.txt`). '
      'Rates are store-level shares of the main sample unless stated. Brackets are 95% confidence intervals. Wilson intervals are primary: '
      'they describe the sampled stores and treat them as a draw from a super-population of such stores, without a finite-population '
      'correction; because the three upper buckets are censuses, corrected intervals for the frame would be narrower (projection of banner '
      f"stores firing before any choice: {N('fig5/e/banner_and_prechoice_sbx/lo_fpc', 'pct1')}–{N('fig5/e/banner_and_prechoice_sbx/hi_fpc', 'pct1')}% "
      f"with the correction, {N('fig5/e/banner_and_prechoice_sbx/lo', 'pct1')}–{N('fig5/e/banner_and_prechoice_sbx/hi', 'pct1')}% without), so "
      'the reported intervals are conservative. Subgroup, per-product and per-vendor intervals are descriptive and not adjusted for multiplicity. '
      f"For headline rates a cluster bootstrap by consent tool (BCa, {N('design/bootstrap_B')} resamples; {N('design/n_clusters')} clusters, "
      f"{N('design/n_singleton_clusters')} of them single stores without a consent tool) is reported as a sensitivity interval, because "
      f"clustering by tool is not part of the sampling design and the three largest tools hold {N('design/top3_cmp_share_of_banner_stores', 'pct0')}% "
      'of banner stores. Shares whose unit is a request, a pixel entry, a pixel start or a store-vendor pair are clustered within stores, so '
      'they carry intervals that resample stores (a percentile bootstrap, or the Korn-Graubard interval where marked); kappa also resamples '
      'stores. Paired risk differences use Newcombe\'s hybrid-score interval for paired data, and independent ones his interval for two '
      'samples.')
    w('')
    w('## 1. Headline findings')
    w('')
    w(f"1. **Before any choice.** A sandboxed ad pixel sent at least one request (a data beacon or a library load) before any choice on "
      f"{RC('fig1b/sandboxed_prechoice')} stores. A consent banner appeared on {RC('fig1b/banner')}. Among banner stores the rate was "
      f"{RC('fig1b/banner_fires')}, against {R('fig1b/nobanner_fires')} of stores without a banner. At our California vantage point Shopify's "
      f"region default was 'allowed until choice' on {R('fig1b/region_allowed')} of stores that returned one; among banner stores the pre-choice "
      f"rate was {R('fig3/d/opt_out/any_sbx')} where the default allowed and {R('fig3/d/opt_in/any_sbx')} where it denied.")
    w(f"2. **Before the banner is even visible.** The banner detector polls every {N('design/banner_poll_ms')} ms. On "
      f"{R('fig3/b/before_banner_by_poll')} of the {N('fig3/b/n')} banner stores with a pre-choice sandboxed request, the first such request came "
      f"more than one polling interval before the banner was detected (primary, conservative); on {R('fig3/b/before_banner')} it came before at "
      f"all. Counting only data beacons, {R('fig3/b/beacon_before_banner')}. The per-store flag repeats only moderately: "
      f"{N('fig3/b/repeat/agree')} of {N('fig3/b/repeat/n')} repeat stores agreed (kappa {N('fig3/b/repeat/kappa', 'f2')}), with median "
      f"absolute timing shifts of {N('fig3/b/repeat/median_abs_shift_first_ms')} ms (first request) and {N('fig3/b/repeat/median_abs_shift_banner_ms')} "
      f"ms (banner) between the two loads.")
    bl_, lf_ = 'fig4/a/blocklist/', 'fig4/a/like_for_like/'
    w(f"3. **Blocked on paper.** {N(bl_ + 'any_sbx/n')} stores ({N(bl_ + 'n_cmps')} consent tools: {N(bl_ + 'by_cmp/pandectes')} Pandectes, "
      f"{N(bl_ + 'by_cmp/onetrust')} OneTrust, {N(bl_ + 'by_cmp/cookiebot')} Cookiebot) have a readable blocklist that names an ad vendor as "
      f"blocked before any choice. A blocklist is in force for a visitor only while the CMP has not consented for that visitor, and on "
      f"{N(bl_ + 'yes_writers_summary/n')} of these stores the CMP itself wrote 'marketing: yes' to Shopify in the Default load without any click "
      f"({N(bl_ + 'bot_rule/n')} of them through Pandectes' rule for automated browsers, see 'What the pages saw of our crawler' below). **Primary (revised after referee review):** "
      f"on the {N(bl_ + 'primary/fired/n')} stores whose CMP wrote no 'yes', the blocklisted vendor's own pixel fired from Shopify's sandbox before "
      f"any choice on {R(bl_ + 'primary/fired')}; any sandboxed ad pixel fired on {KN(bl_ + 'primary/any_sbx')}. Unconditioned, over all "
      f"{N(bl_ + 'declared_vendor_fired_sbx/n')} stores: {R(bl_ + 'declared_vendor_fired_sbx')} (by any route {KN(bl_ + 'declared_vendor_fired_any')}; "
      f"Pandectes {KN(bl_ + 'by_cmp_fired/pandectes')}, OneTrust {KN(bl_ + 'by_cmp_fired/onetrust')}, Cookiebot {KN(bl_ + 'by_cmp_fired/cookiebot')}). "
      f"Conditioning instead on installation, on the {N(bl_ + 'cfg_stores/fired/n')} stores with a configured sandboxed pixel of a declared vendor it "
      f"fired on {R(bl_ + 'cfg_stores/fired')} ({KN(bl_ + 'cfg_stores_primary')} of those whose CMP wrote no 'yes'); on "
      f"{N(bl_ + 'cfg_stores/neither_cfg_nor_fired')} of the {N(bl_ + 'declared_vendor_fired_sbx/n')} stores no declared vendor had a sandboxed pixel at all. "
      f"**The blocklist made no measurable difference to sandboxed firing:** comparing any sandboxed ad pixel like for like within Shopify's region "
      f"default, among stores whose CMP wrote no 'yes', blocklist stores fired on {KN(lf_ + 'allowed_no_yes/blocklist')} vs "
      f"{KN(lf_ + 'allowed_no_yes/reference')} banner stores without a readable declaration where the default allowed marketing, and on "
      f"{KN(lf_ + 'denied_no_yes/blocklist')} vs {KN(lf_ + 'denied_no_yes/reference')} where it denied (Mantel-Haenszel difference "
      f"{N(lf_ + 'mh_no_yes/rd', 'pct1')} pp, 95% CI {N(lf_ + 'mh_no_yes/rd_lo', 'pct1')} to {N(lf_ + 'mh_no_yes/rd_hi', 'pct1')}); over all stores "
      f"{KN(lf_ + 'allowed/blocklist')} vs {KN(lf_ + 'allowed/reference')} and {KN(lf_ + 'denied/blocklist')} vs {KN(lf_ + 'denied/reference')} "
      f"(difference {N(lf_ + 'mh/rd', 'pct1')} pp, {N(lf_ + 'mh/rd_lo', 'pct1')} to {N(lf_ + 'mh/rd_hi', 'pct1')}). This tests the falsification "
      f"criterion of pre-crawl prediction P1: the data are consistent with no reduction and rule out reductions larger than "
      f"{N(lf_ + 'mh_no_yes/reduction_ruled_out_beyond', 'pct0')} percentage points. What decided firing was Shopify's state: the declared "
      f"vendor fired on {KN(bl_ + 'by_default/allowed/fired')} blocklist stores whose default allowed marketing and {KN(bl_ + 'by_default/denied/fired')} "
      f"whose default denied it, and {N(bl_ + 'by_default/denied_auto_grant/declared_vendor_fired')} of those {N(bl_ + 'by_default/denied/fired/k')} "
      f"were stores whose CMP had switched the denying default to 'yes'. **Direct evidence:** in one later re-check load per store, the blocker "
      f"neutralized a declared vendor's main-document tag while that vendor's pixel sent requests from Shopify's sandbox in the same load on "
      f"{N('checks/recheck/blocker/stores_neutralized_and_sbx')} stores ({', '.join(G('checks/recheck/blocker/stores_neutralized_and_sbx_ids'))}; "
      f"none a bot-rule store); and (exploratory) on {N(bl_ + 'pattern_match/stores_match')} stores the CMP's own blocklist pattern matches a URL "
      f"that the sandbox fetched in the Default load ({N(bl_ + 'pattern_match/entries_match')} of {N(bl_ + 'pattern_match/entries_pattern_read')} "
      f"Pandectes entries whose vendor fired from the sandbox; {N(bl_ + 'pattern_match/stores_match_primary')} of these stores wrote no 'yes'). A "
      f"blocker neutralized at least one element in the re-check on {R('checks/recheck/blocker/active')} blocklist stores; of the "
      f"{N('checks/recheck/blocker/fired_main_crawl')} stores where the declared vendor had fired, {N('checks/recheck/blocker/fired_main_crawl_inactive/n')} "
      f"OneTrust stores ({', '.join(G('checks/recheck/blocker/fired_main_crawl_inactive/stores'))}) showed no active blocker, so OneTrust's "
      f"declaration may not be enforced there. Where the banner itself told Shopify 'marketing: no' before any choice, a sandboxed ad pixel had "
      f"already fired on {R('fig4/a/cpapi_deny/any_sbx')}.")
    w(f"4. **The race.** In {N('fig5/d/deny/loads')} loads where the CMP wrote 'marketing: no' to Shopify without a click, "
      f"{N('fig5/d/deny/pixels_before')} of {N('fig5/d/deny/pixels')} third-party pixel sandboxes that declare 'marketing' had already started "
      f"(median {N('fig5/d/deny/median_abs_lag_pixel_ms', 'f0')} ms before the write event); {N('fig5/d/deny/pixels_before_ctapi')} of them "
      f"started before Shopify's consent script (`consent-tracking-api.js`) was even requested, a lower bound for any write through it. "
      f"Conversely, in {N('fig5/d/grant/loads')} loads the CMP wrote 'marketing: yes' with no click at all, and all {N('fig5/d/grant/pixels')} "
      f"gated third-party sandboxes started after it (median {N('fig5/d/grant/median_abs_lag_pixel_ms', 'f0')} ms later). These automatic "
      f"'yes' writes are not all behaviour a visitor would meet: some are the CMP's reaction to an automated browser (see 'What the pages saw of our crawler').")
    w(f"5. **Decline.** {R('fig5/decline/no_reject')} banners had no reject option on the first layer. Of {N('fig5/decline/clicked_all')} "
      f"clicks, {N('fig5/decline/failed_clicks')} forced clicks failed (banner still shown and no refusal recorded; blocked by a modal, an age "
      f"gate or a chat widget) and are excluded. After the {N('fig5/decline/clicked')} clicks that worked, Shopify recorded an explicit "
      f"refusal on {R('fig5/decline/refused')}; on stores whose default allowed marketing, the click turned it off on "
      f"{R('fig5/decline/refused_on_allowed_default')}. On a fresh page (the reload after the click), a newly created sandbox still sent an ad "
      f"request on {RC('fig5/decline/fresh')} of stores, against {PC('fig5/a/Any vendor/Default')} under Default in the same window on the same "
      f"stores (paired reduction {D('fig5/compare/default_vs_decline/paired_diff')}; every fresh-page residual store also fired under Default, "
      f"so about half of the Default-positive stores kept firing: {KN('fig5/compare/fresh_given_default')}); counting any time after the click "
      f"it was {R('fig5/decline/after_decline_any_sbx')}. "
      f"The fresh-page residual was {R('fig5/b/Shopify native banner/decline_residual')} with Shopify's own banner, "
      f"{R('fig5/b/CMP writes to Shopify API/decline_residual')} with third-party tools that write to Shopify, and "
      f"{R('fig5/b/' + GB + '/decline_residual')} with blocker-only or unknown tools.")
    w(f"6. **GPC.** Shopify recorded 'sale of data: no' on {R('context/gpc_cp_sale_denied')} GPC loads that returned a state. Of "
      f"{N('fig5/c/gate_audit/gpc_sale_pixels/n')} configured pixel entries that declare sale of data, {N('fig5/c/gate_audit/gpc_sale_pixels/k')} "
      f"started under GPC, in {N('fig5/c/gate_audit/gpc_sale_pixels/loads_with_start/n')} at-risk loads (upper 95% bound "
      f"{N('fig5/c/gate_audit/gpc_sale_pixels/loads_with_start/hi', 'pct1')}% of loads; the entry-level bound "
      f"{N('fig5/c/gate_audit/gpc_sale_pixels/hi', 'pct2')}% treats entries as independent and is not used). Still, of the stores with sandboxed ad "
      f"requests under Default, {RC('fig5/gpc_residual')} kept sending them under GPC, all from pixels that do not declare sale of data.")
    cq = 'fig5/compare/'
    w(f"7. **Decline vs GPC.** Estimand: persistence after the choice, on a later page (a sandbox created after the choice; equal "
      f"{N('design/equal_window_s')} s windows). On the same {N(cq + 'equal_window/n')} stores: Decline {N(cq + 'equal_window/k_a')} vs GPC "
      f"{N(cq + 'equal_window/k_b')} stores, a paired difference of {D(cq + 'equal_window/paired_diff')} (discordant {N(cq + 'equal_window/a_only')} "
      f"vs {N(cq + 'equal_window/b_only')}, exact McNemar p = {N(cq + 'equal_window/p_exact', 'f3')}); GPC's advantage in post-choice persistence "
      f"was thus between about {N(cq + 'equal_window/paired_diff/diff_lo', 'pct0')} and {N(cq + 'equal_window/paired_diff/diff_hi', 'pct0')} pp. "
      f"Against Default in the same window ({N(cq + 'default_vs_decline/k_a')} stores), Decline reduced the "
      f"share by {D(cq + 'default_vs_decline/paired_diff')} and GPC by {D(cq + 'default_vs_gpc/paired_diff')}. Over the whole visit the controls "
      f"differ much more: a Decline user is exposed before the click, and a sandboxed ad request came before the click on "
      f"{N(cq + 'whole_visit_preclick_vs_gpc/k_a')} of these stores, against {N(cq + 'whole_visit_preclick_vs_gpc/k_b')} for the whole GPC load "
      f"(discordant {N(cq + 'whole_visit_preclick_vs_gpc/a_only')} vs {N(cq + 'whole_visit_preclick_vs_gpc/b_only')}; difference "
      f"{D(cq + 'whole_visit_preclick_vs_gpc/paired_diff')}; the pre-click window is the shorter, so this favours Decline). Sensitivity analysis "
      f"with a different estimand (Decline attempted, including the failed forced clicks): {N(cq + 'all_clicked_fresh_vs_gpc/k_a')} vs "
      f"{N(cq + 'all_clicked_fresh_vs_gpc/k_b')} of {N(cq + 'all_clicked_fresh_vs_gpc/n')}, difference {D(cq + 'all_clicked_fresh_vs_gpc/paired_diff')} "
      f"(p = {N(cq + 'all_clicked_fresh_vs_gpc/p_exact', 'f3')}). The earlier 'any time after the click' comparison "
      f"({N(cq + 'old_any_after_vs_gpc/a_only')} vs {N(cq + 'old_any_after_vs_gpc/b_only')} discordant) mixed unequal windows and sandboxes that "
      f"no choice could stop.")
    ga_ = 'fig5/c/gate_audit/'
    w(f"8. **Shopify's gate held in almost all observed cases.** Measured on configured pixels at risk: {N(ga_ + 'gpc_sale_pixels/k')} "
      f"of {N(ga_ + 'gpc_sale_pixels/n')} sale-declaring pixel entries started under GPC ({N(ga_ + 'gpc_sale_pixels/loads_with_start/k')} of "
      f"{N(ga_ + 'gpc_sale_pixels/loads_with_start/n')} at-risk loads); under a denying region default {RK(ga_ + 'default_denied_mkt_pixels')} "
      f"marketing-declaring pixel entries were held back (loads without a CMP 'yes'; a pixel started in "
      f"{KN(ga_ + 'default_denied_mkt_pixels/loads_with_start')} loads); as a check of the detector, {RK(ga_ + 'allowed_mkt_pixels_started')} such "
      f"entries started when marketing was allowed. Among pixel starts made under a partly denied state by pixels that declare a purpose, "
      f"{N(ga_ + 'pixel_starts/informative/k')} of {N(ga_ + 'pixel_starts/informative/n')} starts had a declared purpose denied; they came from "
      f"{N(ga_ + 'pixel_starts/violation_loads')} loads on {N(ga_ + 'pixel_starts/violation_stores')} stores "
      f"({', '.join(N(ga_ + 'pixel_starts/informative_max_per_store/' + str(i)) for i in range(3))} of them from three single stores), so the "
      f"rate to quote is per store ({R(ga_ + 'pixel_starts/informative_stores')} stores with such a start) or per load "
      f"({R(ga_ + 'pixel_starts/informative_loads')}); the start-level ratio, clustered by store, is {N(ga_ + 'pixel_starts/informative_cluster/p', 'pct1')}% "
      f"(95% CI {N(ga_ + 'pixel_starts/informative_cluster/kg_lo', 'pct1')}–{N(ga_ + 'pixel_starts/informative_cluster/kg_hi', 'pct1')}%), and its "
      f"denominator includes starts whose own declared purposes were all allowed, so it is not a violation rate. The "
      f"{N(ga_ + 'pixel_starts/violation_loads')} loads: "
      f"{N(ga_ + 'pixel_starts/violation_loads_by_class/edge_cached_header')} edge-cached pages carrying another region's "
      f"consent string; {N(ga_ + 'pixel_starts/violation_loads_by_class/unexplained')} loads in which the page's own consent "
      f"string already declined the purpose ({', '.join(G(ga_ + 'pixel_starts/unexplained_loads'))}); and "
      f"{N(ga_ + 'pixel_starts/violation_loads_by_class/created_after_cmp_event')} GPC loads "
      f"({', '.join(s + '__A2' for s in G('fig5/d/deny/first_after_stores'))}) whose first third-party marketing sandbox started "
      f"{N('fig5/d/deny/first_after_lag_ms/0', 'f0')} and {N('fig5/d/deny/first_after_lag_ms/1', 'f0')} ms after a CMP's automatic 'no' was "
      f"dispatched, far beyond the clock differences. Neither group is explained by our data; for the second, the manager may have decided "
      f"before the write, which we did not verify. The first pages of Decline loads are excluded (their consent events were not recorded); they "
      f"hold {N(ga_ + 'pixel_starts/excluded_decline_first_page/flagged')} further flagged starts in "
      f"{N(ga_ + 'pixel_starts/excluded_decline_first_page/loads')} loads.")
    w(f"9. **Google registers refusals in its own layer.** On the next page after a Decline, {N('fig5/flags/google_beacons_gcs/Decline_next/G100')} "
      f"Google beacons on {N('fig5/flags/google_beacons_gcs/Decline_next/G100_stores')} stores carried Consent Mode 'storage denied' "
      f"(gcs=G100), {N('fig5/flags/google_beacons_gcs/Decline_next/G111')} on {N('fig5/flags/google_beacons_gcs/Decline_next/G111_stores')} "
      f"stores 'granted' (G111), and {N('fig5/flags/google_beacons_gcs/Decline_next/none')} on {N('fig5/flags/google_beacons_gcs/Decline_next/none_stores')} "
      f"stores no consent state. Under GPC, Google requests carried the restricted-data-processing flag (rdp) "
      f"{N('fig5/flags/google_flag_kinds/GPC/rdp')} times (Default: {N('fig5/flags/google_flag_kinds/Default/rdp')}) and the non-personalised-ads "
      f"flag (npa) {N('fig5/flags/google_flag_kinds/GPC/npa')} times "
      f"(Default: {N('fig5/flags/google_flag_kinds/Default/npa')}). The sandboxed residuals are not explained by such flags: every "
      f"remaining sandboxed request carried a refusal signal on {N('fig5/flags/resid_decline_fresh/stores_all_flagged')} of "
      f"{N('fig5/flags/resid_decline_fresh/stores')} stores after Decline and {N('fig5/flags/resid_gpc/stores_all_flagged')} of "
      f"{N('fig5/flags/resid_gpc/stores')} under GPC.")
    w(f"10. **URLs reach vendors.** {N('fig6/a/sandboxed_A0/p', 'pct1')}% (95% CI {N('fig6/a/sandboxed_A0/lo', 'pct1')}–"
      f"{N('fig6/a/sandboxed_A0/hi', 'pct1')}%) of {N('fig6/a/sandboxed_A0/n')} sandboxed ad beacons ({N('fig6/a/sandboxed_A0/n_stores')} stores) "
      f"in the Default load carried the full landing URL with our test code (all origins: {N('fig6/a/all_origins_A0/p', 'pct1')}%). On the "
      f"creator's Store C page the per-video code reached TikTok from its sandbox in the Default, repeat and pre-click Decline loads; after "
      f"the Decline and its reload it reached {N('fig6/b/store_c_after_decline/n_vendors')} vendors, "
      f"{N('fig6/b/store_c_after_decline/n_vendors_sandboxed')} from a sandbox and none of them TikTok.")
    w(f"11. **Stable and consistent with native GPC.** Repeat Default loads agreed with kappa {N('validation/A0_vs_A0r/kappa', 'f3')} "
      f"(95% CI {N('validation/A0_vs_A0r/lo', 'f3')}–{N('validation/A0_vs_A0r/hi', 'f3')}); emulated GPC and Brave's native GPC agreed on "
      f"{N('validation/A2_vs_V1/agree')}/{N('validation/A2_vs_V1/n')} stores, of which only {N('validation/A2_vs_V1/pos_both')} were positive; "
      f"the check discriminates because Default and GPC differed on {N('validation/brave_power/stores_default_gpc_differ')} of these stores and "
      f"{N('validation/brave_power/pairs_default_gpc_differ')} store-vendor pairs, and Brave matched GPC on all "
      f"({N('validation/brave_power/stores_brave_matches_gpc')} and {N('validation/brave_power/pairs_brave_matches_gpc')}). Per-store counts of "
      f"sandboxed ad requests also repeated: Spearman rho {N('validation/A0_vs_A0r_count_spearman/rho', 'f3')} "
      f"({N('validation/A0_vs_A0r_count_spearman/lo', 'f3')}–{N('validation/A0_vs_A0r_count_spearman/hi', 'f3')}) for Default vs repeat and "
      f"{N('validation/A2_vs_A2r_count_spearman/rho', 'f3')} ({N('validation/A2_vs_A2r_count_spearman/lo', 'f3')}–"
      f"{N('validation/A2_vs_A2r_count_spearman/hi', 'f3')}) for GPC vs repeat ({N('validation/A0_vs_A0r_count_spearman/n')} stores).")
    w(f"12. **Projection.** Weighted to the DNS-flagged Shopify storefronts in the Tranco top-200k (about {N('fig5/e/population_estimate')}), "
      f"{N('fig5/e/banner_and_prechoice_sbx/p', 'pct1')}% ({N('fig5/e/banner_and_prechoice_sbx/lo', 'pct1')}–{N('fig5/e/banner_and_prechoice_sbx/hi', 'pct1')}%), "
      f"about {N('fig5/e/banner_and_prechoice_sbx/count')} stores ({N('fig5/e/banner_and_prechoice_sbx/count_lo')}–{N('fig5/e/banner_and_prechoice_sbx/count_hi')}, "
      f"including the uncertainty of the frame size), show a banner yet send sandboxed ad requests before any choice; "
      f"{N('fig5/e/gpc_still_sbx/p', 'pct1')}%, about {N('fig5/e/gpc_still_sbx/count')} stores, keep sending them under GPC. These projections "
      f"hold for the DNS frame only (apex or www host on Shopify), whose recall is about {N('checks/frame_recall/recall', 'pct0')}% "
      f"(bucket-wise bounds {N('checks/frame_recall/recall_lo', 'pct0')}–{N('checks/frame_recall/recall_hi', 'pct0')}%).")
    au = 'automation/'
    # the product descriptions below are hand-written; they must match the products the code scan found
    assert G(au + 'static_scan/products_matching_our_crawler') == ['pandectes', 'shopify_native', 'usercentrics']
    assert G(au + 'static_scan/products_with_other_bot_logic') == ['cookiebot', 'cookiehub', 'onetrust']
    i_cm, i_uc, i_di = det('consentmo'), det('usercentrics'), det('didomi')
    w(f"13. **What the pages saw of our crawler (added after referee review).** Every load showed automation: `navigator.webdriver` was true "
      f"and the user agent contained 'HeadlessChrome' in {N(au + 'fingerprint/webdriver')} of {N(au + 'fingerprint/loads')} usable loads with a page "
      f"probe, including all {N(au + 'fingerprint/by_browser/brave/loads')} Brave loads (Brave also ran headless). In the saved code of "
      f"{N(au + 'static_scan/files')} consent-tool scripts, rules that match this fingerprint exist in Pandectes v5 (a bot rule that, when the "
      f"merchant enables it, hides the banner and grants consent with reason 'bot'), in Usercentrics' loader (a user-agent test for "
      f"HeadlessChrome and Playwright; its effect was not traced) and in Shopify's own banner (used for telemetry only in the saved build); "
      f"OneTrust reads a server-side bot header (effect unknown), and Cookiebot and CookieHub test user agents against bot lists that do not "
      f"match ours. The Pandectes signature (banner configured visible for California, banner element present but hidden, a 'marketing: yes' "
      f"write without a click) appeared in both the Default and the GPC load of {N(au + 'pandectes_bot/n_stores')} stores "
      f"({', '.join(G(au + 'pandectes_bot/stores'))}; all {N(au + 'pandectes_bot/v5_loads')} Pandectes v5 loads had both automation signals), "
      f"while {N(au + 'pandectes_bot/n_contrast_stores')} v5 stores configured as opt-in for California showed their banner and wrote nothing. "
      f"Of the {N(au + 'yes_writes/auto_grant_stores')} Default loads in which a CMP switched a denying default to 'yes', "
      f"{N(au + 'yes_writes/without_banner')} came with no detected banner: {N(au + 'yes_writes/n_without_banner_bot_rule')} of these are "
      f"bot-rule stores and {N(au + 'yes_writes/n_without_banner_other')} are unexplained. Of {N(au + 'scroll_yes/loads_with_yes')} 'yes' writes "
      f"without a click in Default and GPC loads, {N(au + 'scroll_yes/before_first_scroll')} came before our first passive scroll and "
      f"{N(au + 'scroll_yes/after_a_scroll')} after it (on {N(au + 'scroll_yes/n_after_scroll_stores')} stores, "
      f"{N(au + 'scroll_yes/lag_min_ms', 'f0')}–{N(au + 'scroll_yes/lag_max_ms', 'f0')} ms after one of our scrolls), where implied consent on "
      f"scroll cannot be excluded. Detected consent tool vs banner shown in the Default load: Consentmo {N(au + f'detection/rows/{i_cm}/detected')} "
      f"stores, {N(au + f'detection/rows/{i_cm}/banner')} banner; Usercentrics {N(au + f'detection/rows/{i_uc}/detected')}, "
      f"{N(au + f'detection/rows/{i_uc}/banner')}; Didomi {N(au + f'detection/rows/{i_di}/detected')}, {N(au + f'detection/rows/{i_di}/banner')} "
      f"(element present but hidden on {N(au + f'detection/rows/{i_di}/dom_hidden')}); full table `analysis/outputs/cmp_detection.csv` and "
      f"`figures/tables/tableS_cmp_detection.tex`. Direction of the biases: a rule that grants consent to automated browsers makes pixels fire "
      f"where a person would first have seen an opt-in banner (so such stores are excluded from the blocked-on-paper primary, and pre-choice rates "
      f"on them are over-stated for human visitors); a rule that hides the banner from bots lowers the banner count; the recall re-check used "
      f"the same browser (webdriver true and a HeadlessChrome user agent in {N('checks/recheck/fingerprint/webdriver')} of "
      f"{N('checks/recheck/fingerprint/with_probe')} re-check loads), so it cannot find banners suppressed for bots.")
    w('')
    w('## 2. Data and definitions')
    w('')
    w(f"- **Sample.** {N('design/n_main')} of {N('design/n_main_planned')} main-sample stores and {N('design/n_creator')} of "
      f"{N('design/n_creator_planned')} creator-stratum stores had a usable load in all three base arms (Default, Decline, GPC). "
      f"{N('design/n_loads_total')} loads were attempted; {N('context/failed_loads')} were not usable ({N('context/failed_stores')} stores), "
      f"including {N('context/failed_by_reason/redirect_off_site')} redirects to google.com and {N('context/failed_by_reason/http_404_product_gone')} "
      f"missing product pages. {N('context/blocked_like_stores')} stores looked like bot blocking; nothing was done to get around it. "
      f"Sampling funnel exclusions: {N('design/funnel_excl/drawn_to_live')} drawn sites were not live storefronts "
      f"({N('design/funnel_excl/headless')} headless or assets-only, {N('design/funnel_excl/http403')} refused access (forbidden), "
      f"{N('design/funnel_excl/other_errors')} other errors); {N('design/funnel_excl/live_to_sample')} storefronts were excluded "
      f"({N('design/funnel_excl/no_product')} without a product page, {N('design/funnel_excl/child')} aimed at children, "
      f"{N('design/funnel_excl/duplicate')} duplicates, {N('design/funnel_excl/adult')} adult content); after the crawl, {N('design/funnel_excl/content_excluded')} "
      f"sampled stores were excluded from every analysis for content sensitivity (two adult-product stores the sampling screen missed, a toy "
      f"retailer and a second possibly child-directed store), and {N('design/funnel_excl/sample_to_captured')} "
      f"of the remaining {N('design/n_main_after_content_exclusion')} sampled stores were not captured in all three arms. Validation loads: repeats on {N('design/repeat_planned')} stores "
      f"({N('context/repeat_main_ok')} usable main-sample stores) and Brave on {N('design/brave_planned')} ({N('context/brave_ok')} usable).")
    w("- **Ad request.** A request to a vendor marked advertising in `crawl/vendor_endpoints.json`, whether a data beacon or a library "
      "(script) load; beacon-only and test-code-beacon versions of the headline rates are in Fig S6. CORS preflights (OPTIONS) are not ad "
      f"requests: DevTools reports a worker fetch's preflight in the page session, where the crawler labelled it main-thread "
      f"({N('attribution/A0/preflights')} Default requests, removed). **Sandboxed** means it was issued inside a Web Pixels Manager STRICT "
      f"worker, a LAX iframe, or any frame nested inside a LAX iframe (the crawler labelled such frames by their own URL; following the saved "
      f"frame tree moved {N('attribution/A0/nested')} Default ad requests on {N('attribution/A0/nested_stores')} stores into the sandbox, and "
      f"{N('attribution/A0/ambiguous_kept_subframe')} whose frame URL was also used outside a sandbox were left out). No store-level sandboxed "
      "flag changed. **Relayed by Shopify** now means a main-thread request whose initiator stack holds "
      "only Shopify or store scripts; requests with a vendor library or another app script in the stack are ordinary main-thread tags.")
    w("- **Before any choice.** Every request of the Default load (no interaction), and requests of the Decline load before the click.")
    w(f"- **Decline click that worked.** The banner was no longer visible {N('design/click_check_s')} s after the click, or Shopify recorded "
      "an explicit refusal. **Recorded refusal**: any Customer Privacy API reading after the click with `currentVisitorConsent.marketing` or "
      "`trackingConsent` equal to 'no'; other clicks are 'marketing still allowed' (state read, not refused) or 'unknown'. The old flag "
      f"(`marketingAllowed()` false at the end of the load) was true on {N('fig5/decline/old_flag_denied_end/k')} of "
      f"{N('fig5/decline/old_flag_denied_end/n')} clicked stores, but on {N('fig5/decline/old_flag_denied_end_default_denied')} of them the "
      "region default already denied marketing before the click; on the "
      f"{N('fig5/decline/old_flag_not_denied_on_denied_default_unreadable')} 'denied' stores where the flag was not set, the state was "
      "unreadable, not 'yes'.")
    w(f"- **After Decline.** Primary: a sandbox created on the next page (the same URL reloaded after the click, observed "
      f"{N('design/next_page_observe_s')} s after its load event) sent an ad request. Secondary: any sandboxed ad request after the click, same "
      "page or next page. Old sandboxes that send on the next page are unload beacons of the reload itself.")
    w(f"- **Equal windows.** For the Decline vs GPC comparison, Default and GPC count sandboxed requests within {N('design/equal_window_s')} s "
      "of the load event, the span the Decline arm's next page is observed for.")
    w(f"- **Region default.** Decoded from the navigation's `Server-Timing: _cmp` string at our California vantage point: 'allowed until "
      f"choice' on {R('context/region_optout_share')} of stores that returned one. Other US states and the EU get other defaults.")
    w("- **Integration group.** From the CMP that showed the banner (else the one detected), mapped with `crawl/cmp_signatures.json`: "
      "Shopify's own banner (mode N); a CMP that writes to Shopify's Customer Privacy API (modes A and C); blocker only, unknown or no CMP "
      "(modes B and X). It is a property of the consent product, not of the store.")
    w("- **Gate audit.** Configured pixels at risk (a declared purpose denied by the page's own consent string) are compared with the pixels "
      "that started. 'Pixel starts' are worker bootstraps, LAX iframes and OPEN main-thread scripts matched to Shopify's state at that moment.")
    w('')
    w('## 3. Results by figure')
    w('')
    w('### Figure 1b-c (situating data)')
    w(f"- 1b: banner shown on {PC('fig1b/banner')} of stores; a sandboxed ad pixel fired before any choice on {PC('fig1b/banner_fires')} of "
      f"banner stores and {PC('fig1b/nobanner_fires')} of stores without a banner; region default 'allowed until choice' on "
      f"{PC('fig1b/region_allowed')}. Any ad request before any choice (any origin): {R('fig1b/any_ad_prechoice')}.")
    w(f"- 1c: store {N('fig1c/store_id', 'raw')} ({N('fig1c/domain', 'raw')}, CMP {N('fig1c/cmp', 'raw')}), chosen by rule (banner store, "
      f"first sandboxed request before the banner, most vendor groups, banner time nearest the median; {N('fig1c/n_candidates')} candidates). "
      f"Banner visible at {N('fig1c/t_banner')} ms; the first sandboxed request, a library load, at {N('fig1c/t_first_sandboxed')} ms and the "
      f"first sandboxed data beacon at {N('fig1c/t_first_sandboxed_beacon')} ms; {N('fig1c/n_sandboxed')} sandboxed and "
      f"{N('fig1c/n_ad_requests')} total ad requests ({N('fig1c/n_library')} library loads) from {N('fig1c/n_vgroups_sandboxed')} vendor groups; "
      f"{N('fig1c/n_with_full_url')} carried the full page URL ({N('fig1c/n_sandboxed_with_full_url')} of them sandboxed); no choice made.")
    w('')
    w('### Figure 3 (before any choice)')
    w(f"- 3a: pre-choice sandboxed firing, banner vs no banner: TikTok {PC('fig3/a/TikTok/banner')} vs {PC('fig3/a/TikTok/no_banner')}, "
      f"Google {PC('fig3/a/Google/banner')} vs {PC('fig3/a/Google/no_banner')}, Pinterest {PC('fig3/a/Pinterest/banner')} vs "
      f"{PC('fig3/a/Pinterest/no_banner')}, Microsoft {PC('fig3/a/Microsoft/banner')} vs {PC('fig3/a/Microsoft/no_banner')}; any vendor "
      f"{RC('fig3/a/any/banner')} vs {RC('fig3/a/any/no_banner')}.")
    w(f"- 3b (paired per store): median gap (banner minus first sandboxed request) {N('fig3/b/median_gap_ms')} ms (IQR "
      f"{N('fig3/b/q25_gap_ms')} to {N('fig3/b/q75_gap_ms')}); earlier by more than {N('design/banner_poll_ms')} ms on "
      f"{R('fig3/b/before_banner_by_poll')}; by more than {N('design/gap_threshold2_ms')} ms on {R('fig3/b/before_banner_500')}; first data beacon "
      f"before the banner {R('fig3/b/beacon_before_banner')} (by more than one polling interval: {R('fig3/b/beacon_before_banner_by_poll')}); "
      f"first beacon with our test code {R('fig3/b/canary_beacon_before_banner')}. Gaps beyond the axis (clipped at the edge): "
      f"{N('fig3/b/n_gap_beyond_axis')}. Repeatability: {N('fig3/b/repeat/agree')}/{N('fig3/b/repeat/n')} agreement, kappa "
      f"{N('fig3/b/repeat/kappa', 'f3')}. Run segment at {N('design/concurrency_limit')} browsers {KN('fig3/b/segment_conc6_before')}, at "
      f"{N('design/concurrency_coordinator')} {KN('fig3/b/segment_conc10_before')}.")
    w(f"- 3c: {N('fig3/c/share_sandbox_boot/p', 'pct1')}% (95% CI {N('fig3/c/share_sandbox_boot/lo', 'pct1')}–{N('fig3/c/share_sandbox_boot/hi', 'pct1')}%) "
      f"of the {N('fig3/c/All/n_requests')} Default ad requests came from inside a sandbox; with requests relayed by Shopify (only Shopify or "
      f"store scripts in the stack) it was {N('fig3/c/share_wpm_boot/p', 'pct1')}% ({N('fig3/c/share_wpm_boot/lo', 'pct1')}–"
      f"{N('fig3/c/share_wpm_boot/hi', 'pct1')}%). The old label (Shopify's manager anywhere in the stack) gave "
      f"{N('fig3/c/share_old_proxy_label_boot/p', 'pct1')}%: of the {N('fig3/c/old_proxy_label/n')} requests it covered, "
      f"{PC('fig3/c/old_proxy_label/vendor_library')} had an ad-vendor library in the stack, {PC('fig3/c/old_proxy_label/other_third_party')} "
      f"another third-party script, and only {PC('fig3/c/old_proxy_label/shopify_or_store_only')} nothing but Shopify or store code. Sandbox "
      f"share by vendor: Pinterest {N('fig3/c/Pinterest/sandbox', 'pct0')}%, TikTok {N('fig3/c/TikTok/sandbox', 'pct0')}%, Microsoft "
      f"{N('fig3/c/Microsoft/sandbox', 'pct0')}%, Google {N('fig3/c/Google/sandbox', 'pct0')}%, Meta {N('fig3/c/Meta/sandbox', 'pct0')}% "
      f"(Meta mostly runs as a Shopify OPEN pixel: {N('fig3/c/Meta/open_pixel', 'pct0')}%). Per store, the median share sandboxed was "
      f"{N('fig3/c/store_share_sandbox/median', 'pct0')}% (IQR {N('fig3/c/store_share_sandbox/q25', 'pct0')}–{N('fig3/c/store_share_sandbox/q75', 'pct0')}%). "
      f"With the crawler's own labels (preflights counted, nested frames not sandboxed) the share was {PC('fig3/c/share_sandbox_crawl_labels')} "
      f"of {N('fig3/c/share_sandbox_crawl_labels/n')}.")
    w(f"- 3d: pixels that declare 'marketing' fired before any choice on {R('fig3/d/opt_out/mkt_sbx')} of 'allowed until choice' banner "
      f"stores and {R('fig3/d/opt_in/mkt_sbx')} of 'denied until consent' banner stores; on {N('fig3/d/opt_in_mkt_fired_after_cmp_grant/k')} "
      f"of those {N('fig3/d/opt_in_mkt_fired_after_cmp_grant/n')} the CMP had told Shopify 'yes' before the pixel fired, without any click. "
      f"Opt-in proxy (the closest this vantage point comes to an EU visitor): on the 'denied until consent' banner stores a sandboxed ad request "
      f"before any choice came from a pixel that does not declare marketing on {R('fig3/d/opt_in/nomkt_sbx')} and from one that declares no "
      f"purpose at all on {R('fig3/d/opt_in/nopurpose_sbx')}. The region-default contrast (pre-crawl prediction P1) persists within consent "
      f"products: Mantel-Haenszel difference {N('fig3/d/mh_by_product/rd', 'pct1')} pp (95% CI {N('fig3/d/mh_by_product/rd_lo', 'pct1')}–"
      f"{N('fig3/d/mh_by_product/rd_hi', 'pct1')}), odds ratio {N('fig3/d/mh_by_product/odds_ratio', 'f1')} ({N('fig3/d/mh_by_product/or_lo', 'f1')}–"
      f"{N('fig3/d/mh_by_product/or_hi', 'f1')}), over {N('fig3/d/mh_by_product/n_strata')} products with stores on both sides "
      f"({N('fig3/d/mh_by_product/stores_in_informative_strata')} stores), against a crude {D('fig3/d/mh_by_product/crude')}; Pandectes "
      f"{KN('fig3/d/mh_by_product/by_product/pandectes/allowed')} vs {KN('fig3/d/mh_by_product/by_product/pandectes/denied')}, OneTrust "
      f"{KN('fig3/d/mh_by_product/by_product/onetrust/allowed')} vs {KN('fig3/d/mh_by_product/by_product/onetrust/denied')}, Cookiebot "
      f"{KN('fig3/d/mh_by_product/by_product/cookiebot/allowed')} vs {KN('fig3/d/mh_by_product/by_product/cookiebot/denied')}.")
    w('')
    w('### Figure 4 (blocked on paper)')
    w(f"- 4a (revised after referee review): markers compare like with like. Circle = any sandboxed ad pixel fired before any choice (every "
      f"row); cross = the blocklisted vendor's own pixel (blocklist rows). CMP wrote no 'yes' ({N(bl_ + 'primary/fired/n')} stores): cross "
      f"{R(bl_ + 'primary/fired')}, circle {KN(bl_ + 'primary/any_sbx')}; all blocklist stores: cross {R(bl_ + 'declared_vendor_fired_sbx')} "
      f"(from a pixel declaring 'marketing': {KN(bl_ + 'declared_vendor_fired_sbx_mkt')}), circle {R(bl_ + 'any_sbx')}. By Shopify's region default, "
      f"among stores whose CMP wrote no 'yes': 'allowed', blocklist {KN(lf_ + 'allowed_no_yes/blocklist')} (cross "
      f"{KN(lf_ + 'allowed_no_yes/blocklist_declared_vendor')}) vs no readable declaration {R(lf_ + 'allowed_no_yes/reference')}, difference "
      f"{D(lf_ + 'allowed_no_yes/diff')}; 'denied', blocklist {KN(lf_ + 'denied_no_yes/blocklist')} (cross "
      f"{KN(lf_ + 'denied_no_yes/blocklist_declared_vendor')}) vs {R(lf_ + 'denied_no_yes/reference')}, difference {D(lf_ + 'denied_no_yes/diff')}. "
      f"Over all stores: 'allowed' {KN(lf_ + 'allowed/blocklist')} vs {R(lf_ + 'allowed/reference')} ({D(lf_ + 'allowed/diff')}); 'denied' "
      f"{KN(lf_ + 'denied/blocklist')} vs {R(lf_ + 'denied/reference')} ({D(lf_ + 'denied/diff')}); the declared vendor fired on "
      f"{KN(bl_ + 'by_default/allowed/fired')} and {KN(bl_ + 'by_default/denied/fired')}. Banner told Shopify 'marketing: no' before any choice: "
      f"{R('fig4/a/cpapi_deny/any_sbx')}; region 'denied until consent' (all banner stores): {R('fig4/a/region_optin/any_sbx')}; the old reference "
      f"row (nothing declared, 'allowed until choice', CMP 'yes' writers included): {R('fig4/a/none_declared_optout/any_sbx')}. The {N(bl_ + 'yes_writers_summary/n')} "
      f"'yes' writers: {N(bl_ + 'yes_writers_summary/bot_rule')} Pandectes v5 bot-rule stores ({', '.join(G(bl_ + 'bot_rule/stores'))}) and "
      f"{N(bl_ + 'yes_writers_summary/pandectes_v4')} Pandectes v4 stores: on {N(bl_ + 'yes_writers_summary/n_v4_no_banner')} "
      f"({', '.join(G(bl_ + 'yes_writers_summary/v4_no_banner'))}) no banner was shown in California and the CMP wrote 'yes' within about a "
      f"second, as an implied-consent (opt-out) mode outside the banner's regions would; on {N(bl_ + 'yes_writers_summary/n_v4_banner_yes_before_scroll')} "
      f"({', '.join(G(bl_ + 'yes_writers_summary/v4_banner_yes_before_scroll'))}) the banner was shown and the 'yes' came with it, before any "
      f"scroll; on {N(bl_ + 'yes_writers_summary/n_v4_banner_yes_after_scroll')} ({', '.join(G(bl_ + 'yes_writers_summary/v4_banner_yes_after_scroll'))}) "
      f"it came just after our first passive scroll. Pandectes v4's code was not saved, so its mode cannot be read from code; Pandectes v5 applies "
      f"an 'optout' policy (consent implied) outside its strict regions. The {N(bl_ + 'pandectes_v4_no_yes/n')} v4 stores without a 'yes' write "
      f"(declared vendor fired on {N(bl_ + 'pandectes_v4_no_yes/fired')}) never recorded consent, so their blocklists were in force. Other "
      f"sensitivity rules: without the {N(bl_ + 'sens_excl_auto_grant/n_excluded')} automatic grants {R(bl_ + 'sens_excl_auto_grant/fired')}; "
      f"without stores whose 'yes' came before the declared vendor's pixel {R(bl_ + 'sens_excl_yes_before_pixel/fired')}. Counting data "
      f"beacons only: {KN(bl_ + 'by_default/beacon_only/declared_vendor_fired_sbx')} (vendor-matched) and "
      f"{KN(bl_ + 'by_default/beacon_only/any_sbx')} (any sandboxed ad pixel).")
    w(f"- 4b: presence now comes from the pixel configuration only ({N('fig4/b/presence_sources/app_vendor')} vendor-app entries, "
      f"{N('fig4/b/presence_sources/app_learned')} other apps mapped by their app ID on other stores, {N('fig4/b/presence_sources/custom_name')} "
      f"custom pixels by name; {N('fig4/b/presence_sources/custom_unnamed')} of {N('fig4/b/presence_sources/custom_total')} sandboxed custom "
      f"pixels have no name). Among banner stores, a configured sandboxed pixel of the vendor group fired before any choice in "
      f"{RK('fig4/b/fired')} store-vendor pairs ({N('fig4/b/n_stores')} stores). The old definition (configuration or a request in any arm) "
      f"gave {R('fig4/b/old_definition')}; the pairs seen only through a request fired in {R('fig4/b/request_only_pairs')}, which is why they "
      f"are reported separately. By tool: Pandectes {PC('fig4/b/by_cmp/pandectes')}, OneTrust {PC('fig4/b/by_cmp/onetrust')}, Cookiebot "
      f"{PC('fig4/b/by_cmp/cookiebot')}, Osano {PC('fig4/b/by_cmp/osano')}, Shopify's own banner {PC('fig4/b/by_cmp/shopify_native')}. The tools "
      f"differ mostly in Shopify's region default: it denied marketing on {KN('fig4/b/by_cmp/shopify_native/region_denied')} Shopify-banner "
      f"stores, {KN('fig4/b/by_cmp/pandectes/region_denied')} Pandectes and {KN('fig4/b/by_cmp/onetrust/region_denied')} OneTrust stores. "
      f"Where the default allowed, Pandectes {PC('fig4/b/by_region/allowed/pandectes')} and OneTrust {PC('fig4/b/by_region/allowed/onetrust')}; "
      f"where it denied, {PC('fig4/b/by_region/denied/pandectes')} and {PC('fig4/b/by_region/denied/onetrust')}. "
      f"{N('fig4/b/cells_n_lt10')} of {N('fig4/b/cells')} vendor x tool cells have n below {N('design/min_cell_n_heatmap')} and are greyed.")
    w(f"- 4c: of {N('fig4/c/n_pairs')} ad-vendor entries declared blocked before any choice on {N('fig4/c/n_stores')} stores, "
      f"{N('fig4/c/cfg/n')} belong to a vendor with a configured sandboxed Shopify pixel on that store ({N('fig4/c/cfg/n_stores')} stores): "
      f"{RK('fig4/c/cfg/sandbox')} fired from the sandbox, {RK('fig4/c/cfg/page')} from an ordinary page script, {RK('fig4/c/cfg/any')} by any "
      f"route, on {KN('fig4/c/cfg/stores_sandbox')} stores (the figure draws these store-clustered intervals). For the other {N('fig4/c/nocfg/n')} entries no configured sandboxed pixel of the "
      f"vendor was identified (classic tags, OPEN pixels, or installation unknown); they fired by any route in {RK('fig4/c/nocfg/any')}: "
      f"{N('fig4/c/nocfg/sandbox/k')} from a Shopify sandbox through a pixel not mapped to the vendor, {N('fig4/c/nocfg/open_pixel/k')} through "
      f"an OPEN pixel and {N('fig4/c/nocfg/page/k')} from ordinary page scripts. Entries that sent nothing cannot be classified as blocked or "
      f"not installed, because Accept was never clicked.")
    w('')
    w('### Figure 5 (do choices work?)')
    w(f"- 5a (same {N('fig5/a/n_clicked')} working clicks, fresh page, {N('design/equal_window_s')} s windows): any vendor Default "
      f"{PC('fig5/a/Any vendor/Default')}, Decline {PC('fig5/a/Any vendor/Decline')}, GPC {PC('fig5/a/Any vendor/GPC')}; TikTok "
      f"{PC('fig5/a/TikTok/Default')} / {PC('fig5/a/TikTok/Decline')} / {PC('fig5/a/TikTok/GPC')}; Microsoft {PC('fig5/a/Microsoft/Default')} / "
      f"{PC('fig5/a/Microsoft/Decline')} / {PC('fig5/a/Microsoft/GPC')}. Before the click on the Decline page: {PC('fig5/a/Any vendor/Decline_preclick')}.")
    w(f"- 5b (fresh-page residual): by recorded state, refusal recorded {R('fig5/b/Shopify recorded a refusal/decline_residual')}, "
      f"'marketing' still allowed {R('fig5/b/marketing still allowed/decline_residual')}, unknown {R('fig5/b/' + GU + '/decline_residual')}. "
      f"Same page after the click: {R('fig5/decline/same_page')}; next page, any sandbox: {R('fig5/decline/next_page_any_phase')}; old-sandbox "
      f"unload beacons on the reload: {R('fig5/decline/unload_old')}. Of stores with a sandboxed request before the click, "
      f"{R('fig5/decline/fresh_given_pre')} had a new one on the fresh page. Failed forced clicks: {N('fig5/decline/failed_clicks')} of "
      f"{N('fig5/decline/forced')} forced clicks ({N('fig5/decline/forced_explicit_no')} forced clicks recorded an explicit 'no' although the "
      f"banner stayed visible); the screenshot audit of all {N('fig5/decline/forced_audit/n')} forced clicks agreed with this rule on "
      f"{N('fig5/decline/forced_audit/agree_with_rule')} (overlays: {N('fig5/decline/forced_audit/overlay_modal')} modals or gates, "
      f"{N('fig5/decline/forced_audit/chat_widget')} chat widget; assistant labels). The failed clicks' fresh-page rate was {R('fig5/decline/failed_residual_fresh')}.")
    cc_ = 'fig5/c/composition/'
    w(f"- 5c (revised after referee review): each residual sandboxed ad request is classed by the purposes its pixel declares and by Shopify's "
      f"state at the time (refused = declares a purpose the choice refused; left allowed = declares only purposes the choice left allowed; "
      f"none = declares no purpose, so no choice can gate it). GPC ({N('fig5/c/gpc_n')} stores where Shopify set 'sale of data: no'; Shopify maps "
      f"GPC to sale of data only): declares sale of data {R(cc_ + 'gpc/sale')}; declares only purposes GPC leaves allowed {R(cc_ + 'gpc/left_allowed')} "
      f"(marketing {KN(cc_ + 'gpc/left_allowed_mkt')}, other purposes only {KN(cc_ + 'gpc/left_allowed_other')}); declares no purpose "
      f"{R(cc_ + 'gpc/none')}; custom pixels only on {N(cc_ + 'gpc/stores_by_type/CUSTOM')} of the {N(cc_ + 'gpc/any/k')} residual stores, app "
      f"pixels only on {N(cc_ + 'gpc/stores_by_type/APP')}, both on {N(cc_ + 'gpc/stores_by_type/APP+CUSTOM')}. Decline, after a recorded refusal "
      f"({N('fig5/c/decline_n')} stores): pixels started before the click that declare a refused purpose kept sending on "
      f"{R('fig5/c/fig5c_rows/f3')} (F3; same page {KN(cc_ + 'decline/same_page/refused')}, unload beacons as the page reloads "
      f"{KN(cc_ + 'decline/unload/refused')}); new sandboxes declaring a refused purpose {KN(cc_ + 'decline/fresh_page/refused')} (the gate held); "
      f"pixels declaring only purposes the Decline left allowed {R('fig5/c/fig5c_rows/f3_incomplete')} (an incomplete refusal: sale of data stayed "
      f"allowed after the refusal on {R(cc_ + 'decline_sale_after_refusal/sale_allowed')} refused stores); pixels declaring no purpose "
      f"{R('fig5/c/fig5c_rows/f4_no_purpose')} (F4). The three classes cover {N(cc_ + 'decline/classes/union')} stores. On the fresh page ({N(cc_ + 'decline/fresh_page/any/k')} "
      f"stores with a new sandbox firing) the classes were: no purpose {KN(cc_ + 'decline/fresh_page/none')} (custom pixels "
      f"{N(cc_ + 'decline/fresh_page/by_type/CUSTOM_none')}, app pixels {N(cc_ + 'decline/fresh_page/by_type/APP_none')}), left allowed "
      f"{KN(cc_ + 'decline/fresh_page/left_allowed')} (custom {N(cc_ + 'decline/fresh_page/by_type/CUSTOM_left_allowed')}, app "
      f"{N(cc_ + 'decline/fresh_page/by_type/APP_left_allowed')}); custom pixels were involved on {N(cc_ + 'decline/fresh_page/custom_any')} of these "
      f"stores and app pixels on {N(cc_ + 'decline/fresh_page/app_any')}. By marketing declaration only (the paper's earlier split): same page, "
      f"marketing-declaring {KN('fig5/c/decline_samepage_mkt_fired')} vs not {KN('fig5/c/decline_samepage_nomkt_fired')} (a tie); unload beacons "
      f"from marketing-declaring pixels {KN('fig5/c/decline_unload_mkt_fired')} (requests: Microsoft UET "
      f"{N(cc_ + 'decline/unload/mkt_vendors_requests/microsoft_uet')}), not declaring {KN('fig5/c/decline_unload_nomkt_fired')}; fresh page "
      f"marketing-declaring {KN('fig5/c/decline_newpage_mkt_fired')} (its marketing purpose was allowed again when it started) vs not "
      f"{KN('fig5/c/decline_newpage_nomkt_fired')}; by this rule F3 (same page or unload) covers {N(cc_ + 'decline/classes_mkt/f3')} stores "
      f"and a pixel not declaring marketing sent in some window on {N(cc_ + 'decline/classes_mkt/not_mkt_any_window')}, "
      f"{N(cc_ + 'decline/classes_mkt/both')} stores in both. Same-page marketing sends: "
      f"{N('fig5/c/samepage_mkt_requests/n')} requests, median {N('fig5/c/samepage_mkt_requests/median_ms', 'f0')} ms and up to "
      f"{N('fig5/c/samepage_mkt_requests/max_ms', 'f0')} ms after the click; stacks: {N('fig5/c/samepage_mkt_requests/stack_pixel_code_only')} "
      f"issued by the pixel's own code under Shopify's sandbox, {N('fig5/c/samepage_mkt_requests/stack_vendor_library')} by the vendor's "
      f"library, {N('fig5/c/samepage_mkt_requests/stack_none')} without a stack, so the stacks cannot separate Shopify-delivered events from "
      f"the vendor's own timers. Over all {N('fig5/decline/fresh/n')} working clicks, the unload beacons were {N('fig5/c/unload_requests/n')} requests on "
      f"{N('fig5/c/unload_requests/stores')} stores ({N('fig5/c/unload_requests/uet')} of them Microsoft UET, {N('fig5/c/unload_requests/min_s', 'f1')}–"
      f"{N('fig5/c/unload_requests/max_s', 'f1')} s after the click, a median {N('fig5/c/unload_requests/median_s_after_reload', 'f2')} s after the reload started); "
      "any real navigation away from the page triggers such beacons. Whether Shopify stops delivering events to a pixel that started before a "
      "late 'no' was not measured; the WPM has no code path that terminates a started pixel. Per-request classes: "
      "`analysis/outputs/residual_composition.csv`.")
    w(f"- Gate audit, pixel starts: {N('fig5/c/gate_audit/pixel_starts/n')} starts in {N('fig5/c/gate_audit/pixel_starts/loads')} loads, of which "
      f"{N('fig5/c/gate_audit/pixel_starts/no_purpose')} by pixels that declare no purpose (cannot be gated), {N('fig5/c/gate_audit/pixel_starts/open_scripts')} "
      f"OPEN scripts, and {N('fig5/c/gate_audit/pixel_starts/all_allowed')} made while every purpose was allowed. The first pages of Decline "
      f"loads are excluded (their consent events were not recorded); they hold {N('fig5/c/gate_audit/pixel_starts/excluded_decline_first_page/flagged')} "
      f"further flagged starts in {N('fig5/c/gate_audit/pixel_starts/excluded_decline_first_page/loads')} loads. Violation stores: "
      f"{', '.join(G('fig5/c/gate_audit/pixel_starts/violation_stores_list'))}. Under a denying default, "
      f"{N('fig5/c/gate_audit/default_denied_mkt_pixels/with_cmp_grant')} marketing pixel entries in loads where the banner said 'yes' first all "
      f"started ({N('fig5/c/gate_audit/default_denied_mkt_pixels/with_cmp_grant_started')}), as the gate intends. The store- and load-level rates "
      f"are in the headline finding on Shopify's gate.")
    w(f"- 5d race (third-party pixels only; Shopify's own pixel entries and OPEN scripts removed): 'no' writes a median "
      f"{N('fig5/d/deny/median_update_ms')} ms after navigation start, the first third-party 'marketing' sandbox a median "
      f"{N('fig5/d/deny/median_first_create_ms')} ms; {N('fig5/d/deny/loads_first_before')} of {N('fig5/d/deny/loads')} loads started it "
      f"before the write (Default {N('fig5/d/deny/by_arm_first_before/A0')} of {N('fig5/d/deny/by_arm/A0')}, GPC "
      f"{N('fig5/d/deny/by_arm_first_before/A2')} of {N('fig5/d/deny/by_arm/A2')}); the {N('fig5/d/deny/loads_first_after')} loads that did "
      f"not are {', '.join(G('fig5/d/deny/first_after_stores'))} (GPC loads; first sandbox {N('fig5/d/deny/first_after_lag_ms/0', 'f0')} and "
      f"{N('fig5/d/deny/first_after_lag_ms/1', 'f0')} ms after the 'no'), which the gate audit flags and which are unexplained. The consent script was requested a median "
      f"{N('fig5/d/deny/median_ctapi_ms')} ms after navigation start. The event time is the dispatch of `visitorConsentCollected`, not the write "
      f"call. 'Yes' writes without a click: {N('fig5/d/grant/loads')} loads on {N('fig5/d/grant/stores')} stores (Pandectes "
      f"{N('fig5/d/grant/by_cmp/pandectes')}), all before our first passive scroll ({N('fig5/d/grant/before_first_scroll')} of "
      f"{N('fig5/d/grant/loads')}). In the Default arm such a CMP 'yes' switched the default on {R('consent_changes_summary/A0_grant_share_of_optin')} "
      f"of 'denied until consent' stores, {N('automation/yes_writes/n_bot_rule')} of them through Pandectes' bot rule (see 'What the pages saw of our crawler').")
    w(f"- Models (`outputs/models_table.csv`). Integration group is a product-level variable whose reference is one product (Shopify's "
      f"banner, {KN('models/native_banner_default_denied')} of its Default-load banner stores with a readable default denying marketing), so these ORs describe products and "
      f"defaults together. Fresh-page Decline residual vs Shopify's banner, Firth with profile-penalised-likelihood CIs: blocker only / "
      f"unknown {OR(0)}, CMP that writes to Shopify {OR(1)}; adjusted for recorded refusal and region default {OR(2)} and {OR(3)}; recorded "
      f"refusal {OR(4)}. With a random intercept per consent product: {OR(0, 'mixed_list')} and {OR(1, 'mixed_list')}. GPC residual: {OR(6)} and {OR(7)}; mixed {OR(2, 'mixed_list')} and {OR(3, 'mixed_list')}. The between-product variance "
      f"was estimated at zero (a boundary estimate) in both mixed models{'' if G('models/mixed_list/2/converged') else ', and the GPC mixed fit did not report convergence'}; "
      f"with a zero variance the mixed models reduce to ordinary logistic fits, so they do not capture clustering by product. Mechanism check (not a "
      f"predictor; it is the outcome seen in another load): under GPC {N('models/gpc_fired_with_default_nosale_ad/k')} of "
      f"{N('models/gpc_fired_with_default_nosale_ad/n')} stores whose Default load had a sandboxed ad request from a pixel not declaring sale of "
      f"data still fired, vs {N('models/gpc_fired_without_default_nosale_ad/k')} of {N('models/gpc_fired_without_default_nosale_ad/n')}; after a "
      f"recorded refusal {N('models/decline_fired_with_default_nomkt_ad_refused/k')} of {N('models/decline_fired_with_default_nomkt_ad_refused/n')} "
      f"vs {N('models/decline_fired_without_default_nomkt_ad_refused/k')} of {N('models/decline_fired_without_default_nomkt_ad_refused/n')}.")
    w(f"- Refusal signals: after a Decline, {N('fig5/flags/post_choice_Decline_after/flagged')} of {N('fig5/flags/post_choice_Decline_after/n')} "
      f"ad requests of any origin carried one ({N('fig5/flags/post_choice_Decline_after/google_flagged')} of "
      f"{N('fig5/flags/post_choice_Decline_after/google')} Google requests); under GPC {N('fig5/flags/post_choice_GPC/flagged')} of "
      f"{N('fig5/flags/post_choice_GPC/n')} ({N('fig5/flags/post_choice_GPC/google_flagged')} of {N('fig5/flags/post_choice_GPC/google')} Google). "
      f"Shares by group and arm: Google {PC('fig6/c/Google/Default')} Default, {PC('fig6/c/Google/Decline')} next page after Decline, "
      f"{PC('fig6/c/Google/GPC')} GPC; Microsoft {PC('fig6/c/Microsoft/Default')}, {PC('fig6/c/Microsoft/Decline')}, {PC('fig6/c/Microsoft/GPC')}; "
      f"other vendors {PC('fig6/c/Other vendors/Default')}, {PC('fig6/c/Other vendors/Decline')}, {PC('fig6/c/Other vendors/GPC')} (URL "
      f"parameters only; body-borne flags such as Meta's data-processing options are not seen).")
    w(f"- Projection (formerly Fig 5e, now a table: `figures/tables/table_projection.tex`; stratified by Tranco bucket; shares of ALL storefronts): banner and pixel before any choice "
      f"{N('fig5/e/banner_and_prechoice_sbx/p', 'pct1')}%; banner without a first-layer reject {N('fig5/e/banner_no_first_layer_reject/p', 'pct1')}% "
      f"(about {N('fig5/e/banner_no_first_layer_reject/count')}); Decline clicked and a fresh-page pixel still fires "
      f"{N('fig5/e/decline_clicked_still_sbx/p', 'pct1')}% (about {N('fig5/e/decline_clicked_still_sbx/count')}, "
      f"{N('fig5/e/decline_clicked_still_sbx/count_lo')}–{N('fig5/e/decline_clicked_still_sbx/count_hi')}); GPC on and pixel still fires "
      f"{N('fig5/e/gpc_still_sbx/p', 'pct1')}%; GPC on and a pixel that declares sale of data fires {N('fig5/e/gpc_declared_sale_pixel_fires/count')} "
      f"(upper bound {N('fig5/e/gpc_declared_sale_pixel_fires/hi', 'pct1')}%, about {N('fig5/e/gpc_declared_sale_pixel_fires/count_hi')} stores). "
      f"Frame size about {N('fig5/e/population_estimate')} ({N('fig5/e/frame_estimate_ci/lo')}–{N('fig5/e/frame_estimate_ci/hi')}).")
    w('')
    w('### Figure 6 (what reaches the vendors)')
    w(f"- 6a (sandboxed beacons with the full URL and test code, Default / Decline load / GPC; the figure draws Korn-Graubard intervals "
      f"clustered by store and omits estimates from fewer than {N('design/min_stores_row')} stores): all vendors {PC('fig6/a/All/Default')} / "
      f"{PC('fig6/a/All/Decline')} / {PC('fig6/a/All/GPC')}; TikTok {PC('fig6/a/TikTok/Default')}; Google {PC('fig6/a/Google/Default')}; "
      f"Pinterest {PC('fig6/a/Pinterest/Default')}; Meta {PC('fig6/a/Meta/Default')} ({N('fig6/a/Meta/Default/n')} beacons on "
      f"{N('fig6/a/Meta/Default/n_stores')} stores). All origins: {PC('fig6/a/All/Default_all_origins')}.")
    w(f"- 6b: see the refusal-signal bullet under Figure 5.")
    w(f"- 6c (Store C, C005): TikTok's sandboxed pixel sent {N('fig6/b/store_c/A0/n_creator_token_tiktok_sbx')} requests carrying the "
      f"video code in the Default load, {N('fig6/b/store_c/A0r/n_creator_token_tiktok_sbx')} in the repeat and "
      f"{N('fig6/b/store_c/A1/n_creator_token_tiktok_sbx')} before the Decline click; {N('fig6/b/store_c/A2/n_creator_token_tiktok')} "
      f"under GPC. The code reached {N('fig6/b/store_c/A0/n_vendors_with_token')} vendors in Default "
      f"({N('fig6/b/store_c/A0/n_vendors_with_token_nongoogle')} not Google) and {N('fig6/b/store_c/A2/n_vendors_with_token')} under GPC. "
      f"In the Decline load it reached {N('fig6/b/store_c_pre_click/n_vendors')} vendors before the click and "
      f"{N('fig6/b/store_c_after_decline/n_vendors')} after the click and reload ({', '.join(G('fig6/b/store_c_after_decline/vendors'))}; "
      f"{N('fig6/b/store_c_after_decline/n_sandboxed')} requests from a sandbox, none to TikTok). Every Store C load received an "
      f"edge-cached consent string for Arizona (`3.AMPS_USAZ`).")
    w(f"- Creator stratum: the creator's code reached at least one ad vendor on {R('fig6/b/creator_token_reached_ad_vendor_A0')} of creator "
      f"stores, a non-Google vendor on {R('fig6/b/creator_token_reached_nongoogle_A0')}, and did so from a sandbox on "
      f"{R('fig6/b/creator_token_reached_sandboxed_A0')}. Per-video codes were present on {N('fig6/b/video_token_stores')} creator landing "
      f"pages and reached an ad vendor on {N('fig6/b/video_token_reached_A0')} ({N('fig6/b/video_token_reached_nongoogle_A0')} a non-Google vendor).")
    w('')
    w('### Supplementary figures')
    w(f"- S2 (per tool; 'banners' and the default column count Default-load banner stores, {N('supp/S2_totals/n_banner')} in all, with "
      f"{N('supp/S2_totals/region_denied_k')} of {N('supp/S2_totals/region_denied_n')} readable defaults denying marketing; "
      f"{N('supp/S2_totals/decline_arm_only_banners')} store showed a banner in the Decline load only): Shopify's own banner had the lowest pre-choice rate ({R(f'supp/S2/{i_sh}/prechoice_sbx')}) and a fresh-page Decline "
      f"residual of {R(f'supp/S2/{i_sh}/after_decline')}, below Pandectes and OneTrust, but also the most denying defaults ({PC(f'supp/S2/{i_sh}/region_denied')}); Pandectes "
      f"{PC(f'supp/S2/{i_pa}/prechoice_sbx')} and {PC(f'supp/S2/{i_pa}/after_decline')}; OneTrust {PC(f'supp/S2/{i_ot}/prechoice_sbx')} and "
      f"{PC(f'supp/S2/{i_ot}/after_decline')}.")
    w(f"- S3 (by Tranco bucket): the pre-choice rate on banner stores ranged {N('supp/S3_prechoice_banner_range/lo', 'pct0')}–"
      f"{N('supp/S3_prechoice_banner_range/hi', 'pct0')}% across the three largest buckets, while banner prevalence ranged from "
      f"{N('supp/S3_banner_range/lo', 'pct0')}% to {N('supp/S3_banner_range/hi', 'pct0')}%.")
    w(f"- S4 (screenshot audit, {N('supp/S4/n')} seeded loads; labels by the analysis assistant, independent human re-labelling still "
      f"pending): banner precision {R('supp/S4/banner_precision')}; reject finder agreement {R('supp/S4/reject_agreement')}; click-dismissal "
      f"flag agreement {R('supp/S4/click_flag_agreement')} ({N('supp/S4/n_clicked')} clicked loads, {N('supp/S4/clicked_without_visible_banner')} "
      f"without a visible banner in its screenshot). S4d: kappa GPC vs repeat {N('validation/A2_vs_A2r/kappa', 'f3')} "
      f"({N('validation/A2_vs_A2r/pos_both')} stores positive in both), store x vendor Default vs repeat {N('validation/A0_vs_A0r_vendor/kappa', 'f3')} "
      f"({N('validation/A0_vs_A0r_vendor/lo', 'f3')}–{N('validation/A0_vs_A0r_vendor/hi', 'f3')}, stores resampled).")
    w(f"- S5 (per vendor): the share of a vendor's Default ad requests sent from the sandbox ranged from "
      f"{N('supp/S5_sandbox_share_min/p', 'pct1')}% (Google Merchant Center) to {N('supp/S5_sandbox_share_max/p', 'pct0')}% (AppLovin); "
      f"TikTok {N('supp/S5_rows/3/sandbox_share_requests', 'pct0')}%, Pinterest {N('supp/S5_rows/5/sandbox_share_requests', 'pct0')}%, "
      f"Google Ads {N('supp/S5_rows/0/sandbox_share_requests', 'pct0')}%, Meta {N('supp/S5_rows/1/sandbox_share_requests', 'pct0')}%. Also as "
      f"a LaTeX table: `figures/tables/tableS5_per_vendor.tex`.")
    w(f"- Table S (consent tool detection; `figures/tables/tableS_cmp_detection.tex`, added after referee review): stores on which each consent "
      f"tool was detected in the Default load, on which its banner was shown, and on which its banner element was present but hidden "
      f"({N('automation/detection/n_products')} tools detected on at least {N('automation/detection/min_detected')} stores).")
    w(f"- S6 (sensitivity): all {N('supp/S6_robustness_variants')} robustness variants overlap the main estimate's interval "
      f"({N('supp/S6_robustness_overlap')} of {N('supp/S6_robustness_variants')}); beacon-only and test-code-beacon rows change the rates "
      f"by a few points; only the definitional variants (any origin; declared-sale pixels only; any time after the click) move them a lot. "
      f"Overlap is not a test of difference: most variants are near-complete subsets of the main sample, and the small crawl segment could "
      f"detect only large differences (see 'Concurrency segments' under the checks for the referee text revision).")
    w('')
    w('## 4. Table of statistics')
    w('')
    w('| Statistic | k / n | Estimate | 95% CI | Source key |')
    w('|---|---|---|---|---|')
    rows = [
        ('Banner shown (Default)', 'fig1b/banner'), ('Sandboxed ad request before any choice', 'fig1b/sandboxed_prechoice'),
        ('Banner stores: sandboxed pre-choice', 'fig1b/banner_fires'), ('No-banner stores: sandboxed pre-choice', 'fig1b/nobanner_fires'),
        ('Region default allowed until choice', 'fig1b/region_allowed'), ('Any ad request before any choice', 'fig1b/any_ad_prechoice'),
        ("Allowed-default banner stores: sandboxed pre-choice", 'fig3/d/opt_out/any_sbx'), ("Denied-default banner stores: sandboxed pre-choice", 'fig3/d/opt_in/any_sbx'),
        ("Denied-default banner stores: pixel not declaring marketing", 'fig3/d/opt_in/nomkt_sbx'),
        ("Denied-default banner stores: pixel declaring no purpose", 'fig3/d/opt_in/nopurpose_sbx'),
        ('First sandboxed request before banner (any gap)', 'fig3/b/before_banner'),
        ('First sandboxed request before banner by more than one poll', 'fig3/b/before_banner_by_poll'),
        ('First sandboxed beacon before banner', 'fig3/b/beacon_before_banner'),
        ("Blocklisted vendor fired from its sandbox, CMP wrote no 'yes' (primary)", 'fig4/a/blocklist/primary/fired'),
        ('Blocklisted vendor fired from its sandbox, all blocklist stores', 'fig4/a/blocklist/declared_vendor_fired_sbx'),
        ('Blocklisted vendor fired, stores with a configured pixel of it', 'fig4/a/blocklist/cfg_stores/fired'),
        ('Blocklisted vendor fired by any route (stores)', 'fig4/a/blocklist/declared_vendor_fired_any'),
        ("Blocklisted vendor fired, without CMP auto-'yes' stores", 'fig4/a/blocklist/sens_excl_auto_grant/fired'),
        ('Re-check: blocker active on blocklist stores', 'checks/recheck/blocker/active'),
        ('Re-check: banner visible, random no-banner stores', 'checks/recheck/recall/random'),
        ('Blocklisted entries with configured pixel: fired from sandbox', 'fig4/c/cfg/sandbox'),
        ("Banner wrote 'no' before choice: sandboxed pre-choice", 'fig4/a/cpapi_deny/any_sbx'),
        ('Configured vendor pixel: fired pre-choice (banner stores, pairs)', 'fig4/b/fired'),
        ('Banner with no first-layer reject', 'fig5/decline/no_reject'), ('Working click: explicit refusal recorded', 'fig5/decline/refused'),
        ('Allowed-default stores: click turned marketing off', 'fig5/decline/refused_on_allowed_default'),
        ('After Decline: fresh-page sandbox fires', 'fig5/decline/fresh'),
        ('After Decline: any sandbox after the click', 'fig5/decline/after_decline_any_sbx'),
        ('After Decline: unload beacons of old sandboxes', 'fig5/decline/unload_old'),
        ("After Decline, Shopify's banner", 'fig5/b/Shopify native banner/decline_residual'),
        ('After Decline, CMP writes to Shopify', 'fig5/b/CMP writes to Shopify API/decline_residual'),
        ('After Decline, blocker only / unknown', 'fig5/b/' + GB + '/decline_residual'),
        ("GPC: Shopify 'sale of data: no' (state read)", 'context/gpc_cp_sale_denied'),
        ('GPC: at-risk loads in which a sale-declaring pixel started', 'fig5/c/gate_audit/gpc_sale_pixels/loads_with_start'),
        ('Denied default: marketing pixel entries held', 'fig5/c/gate_audit/default_denied_mkt_pixels'),
        ('Allowed default: marketing pixel entries started (detector check)', 'fig5/c/gate_audit/allowed_mkt_pixels_started'),
        ('Stores with a pixel start whose declared purpose was denied', 'fig5/c/gate_audit/pixel_starts/informative_stores'),
        ('Loads with a pixel start whose declared purpose was denied', 'fig5/c/gate_audit/pixel_starts/informative_loads'),
        ('Pixel starts with a denied declared purpose (partly denied state)', 'fig5/c/gate_audit/pixel_starts/informative_cluster'),
        ('GPC residual among Default-sandboxed stores', 'fig5/gpc_residual'),
        ('Recorded refusal: same-page marketing pixel kept sending', 'fig5/c/decline_samepage_mkt_fired'),
        ('Recorded refusal: fresh-page marketing pixel fired', 'fig5/c/decline_newpage_mkt_fired'),
        ('Recorded refusal: unload beacon from a marketing-declaring pixel', 'fig5/c/decline_unload_mkt_fired'),
        ('Recorded refusal: pixel declaring a refused purpose kept sending (F3)', 'fig5/c/fig5c_rows/f3'),
        ('Recorded refusal: pixel declaring only purposes left allowed', 'fig5/c/fig5c_rows/f3_incomplete'),
        ('Recorded refusal: pixel declaring no purpose (F4)', 'fig5/c/fig5c_rows/f4_no_purpose'),
        ('Banner wrote marketing yes without click (denied-default stores)', 'consent_changes_summary/A0_grant_share_of_optin'),
        ('Stores with sandboxed full-URL beacon (Default)', 'fig6/a/stores_sandboxed_full_url_A0'),
        ('Creator code reached an ad vendor (Default)', 'fig6/b/creator_token_reached_ad_vendor_A0'),
        ('Screenshot audit: banner precision', 'supp/S4/banner_precision'), ('Screenshot audit: reject agreement', 'supp/S4/reject_agreement'),
    ]
    # entry-, start- and pair-level shares: the interval is clustered by store (Korn-Graubard; referee 2, S1)
    clustered = {'fig4/c/cfg/sandbox', 'fig4/b/fired', 'fig5/c/gate_audit/default_denied_mkt_pixels',
                 'fig5/c/gate_audit/allowed_mkt_pixels_started', 'fig5/c/gate_audit/pixel_starts/informative_cluster'}
    for lab, k in rows:
        if k in clustered:
            w(f"| {lab} (interval clustered by store) | {KN(k)} | {PC(k)} | {N(k + '/kg_lo', 'pct1')}–{N(k + '/kg_hi', 'pct1')}% | "
              f"`{k.replace('~1', '/')}` |")
        else:
            w(f"| {lab} | {KN(k)} | {PC(k)} | {CI(k)} | `{k.replace('~1', '/')}` |")
    # differences (referee revision): paired Newcombe intervals, and Mantel-Haenszel differences across strata
    for lab, k in [('Decline minus GPC, post-choice persistence (paired, same stores)', 'fig5/compare/equal_window/paired_diff'),
                   ('Default minus Decline, same window (paired)', 'fig5/compare/default_vs_decline/paired_diff'),
                   ('Default minus GPC, same window (paired)', 'fig5/compare/default_vs_gpc/paired_diff'),
                   ('Pre-click Decline minus whole GPC load (paired)', 'fig5/compare/whole_visit_preclick_vs_gpc/paired_diff'),
                   ('Decline attempted minus GPC (paired; sensitivity)', 'fig5/compare/all_clicked_fresh_vs_gpc/paired_diff')]:
        w(f"| {lab} | {N(k + '/k_a')} vs {N(k + '/k_b')} of {N(k + '/n')} | {N(k + '/diff', 'pct1')} pp | {N(k + '/diff_lo', 'pct1')} to "
          f"{N(k + '/diff_hi', 'pct1')} pp | `{k}` |")
    for lab, k in [("Blocklist minus no declaration, any sandboxed pixel, by region default (MH; CMP wrote no 'yes')", 'fig4/a/like_for_like/mh_no_yes'),
                   ('Blocklist minus no declaration, by region default (MH; all stores)', 'fig4/a/like_for_like/mh'),
                   ("Default 'allowed' minus 'denied', banner stores, within consent product (MH)", 'fig3/d/mh_by_product')]:
        w(f"| {lab} | {N(k + '/k1')}/{N(k + '/n1')} vs {N(k + '/k0')}/{N(k + '/n0')} | {N(k + '/rd', 'pct1')} pp | {N(k + '/rd_lo', 'pct1')} to "
          f"{N(k + '/rd_hi', 'pct1')} pp | `{k}` |")
    for lab, k in [('Sandboxed share of Default ad requests', 'fig3/c/share_sandbox_boot'), ('Sandboxed or relayed share', 'fig3/c/share_wpm_boot'),
                   ('Sandboxed ad beacons with full URL', 'fig6/a/sandboxed_A0')]:
        w(f"| {lab} | {KN(k)} | {PC(k)} | {CI(k)} | `{k}` |")
    for lab, k in [('Kappa Default vs repeat', 'validation/A0_vs_A0r'), ('Kappa GPC vs repeat', 'validation/A2_vs_A2r'),
                   ('Kappa emulated vs Brave GPC', 'validation/A2_vs_V1')]:
        w(f"| {lab} | {N(k + '/agree')}/{N(k + '/n')} agree | {N(k + '/kappa', 'f3')} | {N(k + '/lo', 'f3')}–{N(k + '/hi', 'f3')} | `{k}` |")
    for lab, k in [('Projection: banner + pre-choice sandboxed', 'fig5/e/banner_and_prechoice_sbx'),
                   ('Projection: banner without first-layer reject', 'fig5/e/banner_no_first_layer_reject'),
                   ('Projection: Decline clicked, fresh-page pixel fires', 'fig5/e/decline_clicked_still_sbx'),
                   ('Projection: GPC on, still fires', 'fig5/e/gpc_still_sbx')]:
        w(f"| {lab} | ~{N(k + '/count')} stores | {N(k + '/p', 'pct1')}% | {N(k + '/lo', 'pct1')}–{N(k + '/hi', 'pct1')}% | `{k}` |")
    for lst in ('terms_list', 'mixed_list'):
        for i in range(len(numreg.get(f'models/{lst}'))):
            b = f'models/{lst}/{i}'
            w(f"| Model: {numreg.get(b + '/model')}, {numreg.get(b + '/term').replace('mgroup=', '')} | events {N(b + '/events')}/{N(b + '/n')} | "
              f"OR {N(b + '/OR', 'f2')} | {N(b + '/lo', 'f2')}–{N(b + '/hi', 'f2')} | `{b}` |")
    w('')
    w('Changes to the planned figure takeaways are listed in `figures/takeaways.md`.')
    w('')
    w('## 5. Checks added after the crawl')
    w('')
    w("Run on 2026-09-26 after all other analyses (final audit); rendered here from `stats.json['checks']` and "
      "`stats.json['ethics_sensitivity']`, which `analysis/checks.py` and `analysis/analyze.py` compute from saved outputs.")
    w('')
    rc = 'checks/recheck/recall/'
    w(f"- **Banner-detector recall (re-check crawl).** {N('checks/recheck/loads')} main-sample stores were loaded once more "
      f"({N('checks/recheck/loads_ok')} usable) with no interaction, and their screenshots were labelled blind to group, consent tool and "
      f"detector result by the analysis assistant (human re-labelling pending). A consent banner was visible on {R(rc + 'flagged_visible')} "
      f"stores on which Shopify's shouldShowBanner() had been true without a detected banner, on {R(rc + 'random')} of a random sample of "
      f"the {N(rc + 'pool_outside_flagged')} other stores without a detected banner, and on {KN(rc + 'consentmo')} flagged Consentmo stores "
      f"(an empty container). On the re-check loads the detector found {R(rc + 'detector_recall_recheck')} visible banners, with no false "
      f"alarm ({KN(rc + 'detector_precision_recheck')}); {N(rc + 'missed_on_recheck_dg_consent_banner')} of the {N(rc + 'missed_on_recheck')} it "
      f"missed were dg-consent-banner elements, a tool outside the signature list. Applying the random rate to the pool gives about "
      f"{N(rc + 'est_missed')} missed banners in the main crawl ({N(rc + 'est_missed_lo')}–{N(rc + 'est_missed_hi')}), a recall of about "
      f"{N(rc + 'est_recall', 'pct0')}% ({N(rc + 'est_recall_lo', 'pct0')}–{N(rc + 'est_recall_hi', 'pct0')}%), assuming a banner seen on the "
      f"re-check was also shown in the original load. Counting the {N(rc + 'n_missed_banner_stores')} banners found as banner stores gives "
      f"{R(rc + 'sens_banner')} against {R(rc + 'sens_no_banner')}.")
    bk = 'checks/recheck/blocker/'
    w(f"- **Blocker activity on the blocklist stores (same re-check crawl, one load per store).** A blocker neutralized at least one script "
      f"or iframe element on {R(bk + 'active')} stores (Pandectes {KN(bk + 'active_by_cmp/pandectes')}, Cookiebot "
      f"{KN(bk + 'active_by_cmp/cookiebot')}, OneTrust {KN(bk + 'active_by_cmp/onetrust')}). Of the {N(bk + 'fired_main_crawl')} stores where "
      f"the declared vendor had fired from the sandbox in the main crawl, the blocker was active on {KN(bk + 'fired_main_crawl_active')} and "
      f"the vendor fired from the sandbox again on {KN(bk + 'fired_main_crawl_fired_again')}. On {N(bk + 'stores_neutralized_and_sbx')} stores "
      f"({N(bk + 'stores_neutralized_and_sbx_excl_auto_grant')} without an automatic 'yes'; {N(bk + 'entries_neutralized_fired_sbx')} entries) "
      f"the blocker neutralized a main-document tag of a declared-blocked vendor in the same load in which that vendor's pixel sent requests "
      f"from Shopify's sandbox. A main-document tag was seen for {R(bk + 'entries_tag_seen')} declared-blocked entries. Blocker activity was "
      f"not logged in the main crawl, so these numbers describe the later load.")
    fr = 'checks/frame_recall/'
    w(f"- **Frame recall.** Homepages of a seeded random sample of {N(fr + 'sampled_per_bucket')} non-flagged domains per bucket were "
      f"requested; of the {N(fr + 'contacted')} contacted, {N(fr + 'inspected')} could be inspected and {N(fr + 'storefronts_missed')} were "
      f"Online Store storefronts the DNS rule had missed. The rule's recall is about {N(fr + 'recall', 'pct0')}% (bucket-wise bounds "
      f"{N(fr + 'recall_lo', 'pct0')}–{N(fr + 'recall_hi', 'pct0')}%, not a joint interval), {N(fr + 'buckets/1-10k/recall', 'pct0')}% "
      f"({N(fr + 'buckets/1-10k/recall_lo', 'pct0')}–{N(fr + 'buckets/1-10k/recall_hi', 'pct0')}%) in the top bucket, where "
      f"{N(fr + 'buckets/1-10k/inframe_live')} flagged storefronts face an estimated {N(fr + 'buckets/1-10k/est_missed')} missed ones. In "
      f"seeded samples of {N(fr + 'sub_sample_per_bucket')} domains per bucket, {N(fr + 'sub_live')} had a live storefront on a shop. or "
      f"store. subdomain, an estimated {N(fr + 'est_sub_total')} across the top-200k; these are outside the frame.")
    ls_ = 'checks/lost_stores/'
    w(f"- **Stores not captured.** {N(ls_ + 'n')} of the {N(ls_ + 'n_sample')} sampled stores lacked a usable load in one of the base arms "
      f"({N(ls_ + 'by_reason/redirect_off_site')} redirected to another site, {N(ls_ + 'by_reason/product_page_gone_404')} product pages gone, "
      f"{N(ls_ + 'by_reason/no_window_Shopify')} without a Shopify page object, {N(ls_ + 'by_reason/dns_not_resolved')} DNS failures, "
      f"{N(ls_ + 'by_reason/http_402')} store unavailable). By bucket: {KN(ls_ + 'by_bucket/1-10k')}, {KN(ls_ + 'by_bucket/10k-50k')}, "
      f"{KN(ls_ + 'by_bucket/50k-100k')} and {KN(ls_ + 'by_bucket/100k-200k')} from the top to the bottom bucket. A CMP was detected on "
      f"{KN(ls_ + 'lost_with_cmp')} lost stores and on {KN(ls_ + 'captured_with_cmp')} captured ones (table: `analysis/outputs/lost_stores.csv`).")
    rb = 'checks/robots/'
    w(f"- **robots.txt (retrospective fetch).** The crawler did not consult robots.txt. Fetched afterwards for {N(rb + 'stores')} stores "
      f"({N(rb + 'main')} main, {N(rb + 'creator')} creator; Store C not fetched), {N(rb + 'robots_200')} served one. It disallowed the exact "
      f"landing URL on {N(rb + 'landing_disallowed')} stores: {N(rb + 'landing_disallowed_by_query_only')} only because of our query "
      f"parameters ({N(rb + 'landing_disallowed_by_utm_rule')} through utm rules) and {N(rb + 'landing_path_disallowed')} by path "
      f"({N(rb + 'disallow_all')} disallow everything). It disallowed the sampling homepage on {N(rb + 'home_disallowed')} stores and the "
      f"public product list on {N(rb + 'pjson_disallowed')} of the {N(rb + 'pjson_checked')} stores where that list was used.")
    es = 'ethics_sensitivity/'
    w(f"- **Stores excluded for content sensitivity.** {N('design/funnel_excl/content_excluded')} main-sample stores are excluded from every "
      "analysis (the author's decision after the crawl): two adult-product stores that the sampling screen missed, a toy retailer noticed on its "
      "re-check screenshot, and a second possibly child-directed store. They were crawled like the other stores, so crawl-level counts "
      "(planned and failed loads, traffic) include them; no store-level result does.")
    w(f"- **Sensitivity to the stores flagged in the ethics review.** Flagged: the {N(rb + 'landing_disallowed')} stores whose robots.txt "
      f"disallowed the landing URL (they include the {N(rb + 'home_disallowed')} with a disallowed homepage): "
      f"{N(es + 'n_flagged')} stores, of which {N(es + 'flagged_main_profile/n')} are analysed main-sample stores, "
      f"{N(es + 'variants/excl_flagged/n_excluded_creator')} creator stores, and {N(es + 'n_flagged_not_analysed')} was never captured. Of the {N(es + 'flagged_main_profile/n')}, "
      f"{N(es + 'flagged_main_profile/banner')} showed a banner, {N(es + 'flagged_main_profile/prechoice_sbx')} sent a pre-choice sandboxed "
      f"request, {N(es + 'flagged_main_profile/gpc_sbx')} sent one under GPC and {N(es + 'flagged_main_profile/blocklist')} were "
      f"blocklist stores. Excluding them moves no headline rate by more than {N(es + 'max_abs_change_pp_flagged', 'f1')} percentage points.")
    w('')
    w(f"| Measure | All analysed stores | Without the robots.txt-flagged stores |")
    w('|---|---|---|')
    labs = [('prechoice', 'Sandboxed ad request before any choice'), ('banner_fires', 'Banner stores: pre-choice'),
            ('nobanner_fires', 'No-banner stores: pre-choice'), ('optout_fires', "Banner, default 'allowed': pre-choice"),
            ('optin_fires', "Banner, default 'denied': pre-choice"), ('blocklist', 'Blocklisted vendor fired from its sandbox'),
            ('decline_fresh', 'After Decline: fresh-page sandbox fires'), ('gpc', 'GPC residual'),
            ('gate_informative', 'Gate audit: starts with a denied declared purpose'), ('gate_gpc_sale', 'Gate audit: sale pixels started under GPC'),
            ('gate_default_denied_held', 'Gate audit: marketing pixels held (denied default)'), ('creator_reached', 'Creator code reached an ad vendor'),
            ('creator_reached_nongoogle', 'Creator code reached a non-Google vendor'), ('creator_reached_sandboxed', 'Creator code sent from a sandbox')]
    for k, lab in labs:
        cells = [f"{KN(es + 'variants/' + v + '/' + k)} ({PC(es + 'variants/' + v + '/' + k)})"
                 for v in ('all', 'excl_flagged')]
        w(f"| {lab} | " + ' | '.join(cells) + ' |')
    w('')
    w(f"- **Landing pages.** The first product link was a gift card, gift voucher or gift certificate on {R('checks/landing/gift_card')} "
      f"captured stores (a further {N('checks/landing/gift_other')} product URLs contain 'gift' but are gift boxes or gifts); a sandboxed ad "
      f"request came before any choice on {R('checks/landing/gift_card_prechoice')} of them and {R('checks/landing/other_prechoice')} of the others.")
    gi = 'checks/gpc_injection/'
    w(f"- **GPC injection.** The injected flag read true in {KN(gi + 'lax_frames')} LAX iframes and {KN(gi + 'other_workers')} other workers "
      f"of the GPC arm; in {KN(gi + 'strict_injection_before_own_code')} STRICT workers the injection preceded the worker's own code (for other "
      f"workers the ordering was confirmed in {KN(gi + 'other_workers_ordering_confirmed')}). Pixel code in STRICT workers read the flag as "
      f"undefined in {KN(gi + 'strict_workers_read_undefined')} workers under emulation and {KN(gi + 'brave_strict_workers_read_undefined')} "
      f"under Brave. Worker requests carried the header in {KN(gi + 'worker_requests_sec_gpc')} cases with header details.")
    w(f"- **Other.** Pandectes v5 stores whose strict regions include California: {KN('checks/v5_strict/california_strict')} "
      f"({KN('checks/v5_strict/in_blocklist')} blocklist stores). Page loads per store including re-runs, the next-page reload and the "
      f"re-check: at most {N('checks/loads/with_recheck_max')}; more than seven on {N('checks/loads/with_recheck_gt7')} stores.")
    # consistency pass 2026-09-26: numbers of earlier stages quoted in the manuscript, read by checks.py provenance()
    pv = 'checks/provenance/'
    w(f"- **Before the re-check** (superseded, retried and next-page loads included): at most {N('checks/loads/before_max')} page loads "
      f"per store, more than seven on {N('checks/loads/before_gt7')} stores and ten or more on {N('checks/loads/before_ge10')} stores; the minimum gap between the starts of two loads of one store in the final crawl was "
      f"{N('checks/loads/min_gap_same_store_s', 'f1')} s.")
    w('')
    # referee text pass 2026-09-26: numbers the manuscript's revised text needs (computed in analyze.py)
    w('### Checks added for the referee text revision')
    w('')
    sg = 'supp/S6_segments/'
    c6, c10 = N('design/concurrency_limit'), N('design/concurrency_coordinator')
    w(f"- **Concurrency segments ({c6} vs {c10} browsers; {c6} minus {c10}, Newcombe interval; 'detectable': the difference detectable with "
      f"{N(sg + 'power', 'pct0')}% power at the two-sided {N(sg + 'alpha', 'pct0')}% level).** Banner stores, pre-choice: {N(sg + 'prechoice_sbx_banner/k1')}/{N(sg + 'prechoice_sbx_banner/n1')} vs {N(sg + 'prechoice_sbx_banner/k2')}/{N(sg + 'prechoice_sbx_banner/n2')}, {D(sg + 'prechoice_sbx_banner')}, detectable "
      f"{N(sg + 'prechoice_sbx_banner/mdd80', 'pct0')} pp. Fresh-page Decline residual: {N(sg + 'decline_residual/k1')}/{N(sg + 'decline_residual/n1')} vs {N(sg + 'decline_residual/k2')}/{N(sg + 'decline_residual/n2')}, "
      f"{D(sg + 'decline_residual')}, detectable {N(sg + 'decline_residual/mdd80', 'pct0')} pp. GPC residual: {N(sg + 'gpc_residual/k1')}/{N(sg + 'gpc_residual/n1')} vs "
      f"{N(sg + 'gpc_residual/k2')}/{N(sg + 'gpc_residual/n2')}, {D(sg + 'gpc_residual')}, detectable {N(sg + 'gpc_residual/mdd80', 'pct0')} pp. First sandboxed request before the "
      f"banner: {KN('fig3/b/segment_conc6_before')} vs {KN('fig3/b/segment_conc10_before')}, {D(sg + 'first_request_before_banner')}, "
      f"detectable {N(sg + 'first_request_before_banner/mdd80', 'pct0')} pp. The race (loads with a CMP's automatic 'no'): the first "
      f"third-party marketing sandbox came first in {N(sg + 'race_deny/conc6/loads_first_before')} of {N(sg + 'race_deny/conc6/loads')} loads "
      f"at {c6} browsers and {N(sg + 'race_deny/conc10/loads_first_before')} of {N(sg + 'race_deny/conc10/loads')} at {c10}; sandboxes started before "
      f"the write: {N(sg + 'race_deny/conc6/pixels_before')} of {N(sg + 'race_deny/conc6/pixels')} and {N(sg + 'race_deny/conc10/pixels_before')} "
      f"of {N(sg + 'race_deny/conc10/pixels')}. The segment check could therefore detect only differences of about "
      f"{N(sg + 'mdd_min', 'pct0')}–{N(sg + 'mdd_max', 'pct0')} pp; it is not evidence that the segments are equal.")
    w(f"- **Repeat-load request counts among positive stores.** Spearman rho over all {N('validation/A0_vs_A0r_count_spearman/n')} stores is dominated by stores with no sandboxed "
      f"request in either load ({N('validation/A0_vs_A0r_count_spearman/zero_both')} of {N('validation/A0_vs_A0r_count_spearman/n')} for Default, "
      f"{N('validation/A2_vs_A2r_count_spearman/zero_both')} for GPC). Among stores positive in both loads: Default rho "
      f"{N('validation/A0_vs_A0r_count_spearman_pos/rho', 'f3')} (95% CI {N('validation/A0_vs_A0r_count_spearman_pos/lo', 'f3')}–"
      f"{N('validation/A0_vs_A0r_count_spearman_pos/hi', 'f3')}; {N('validation/A0_vs_A0r_count_spearman_pos/n')} stores), GPC rho "
      f"{N('validation/A2_vs_A2r_count_spearman_pos/rho', 'f3')} (95% CI {N('validation/A2_vs_A2r_count_spearman_pos/lo', 'f3')}–"
      f"{N('validation/A2_vs_A2r_count_spearman_pos/hi', 'f3')}; {N('validation/A2_vs_A2r_count_spearman_pos/n')} stores).")
    gs = 'context/gpc_sale_by_sod_region/'
    w(f"- **GPC and the consent string's sale-of-data-region field.** In the GPC loads, the navigation's consent string declined sale of data "
      f"on {R(gs + 'field_unset')} loads whose sale-of-data-region field was unset ('f') and on {R(gs + 'field_set')} loads where it was set: "
      f"Shopify declined sale of data under GPC whatever that field said.")
    ck = 'fig3/c/cookies/'
    w(f"- **Cookies on sandboxed requests.** In the Default load, {N(ck + 'strict_worker/with_cookie')} of {N(ck + 'strict_worker/n')} ad "
      f"requests from STRICT workers carried a cookie (LAX iframes {N(ck + 'lax_iframe/with_cookie')} of {N(ck + 'lax_iframe/n')}; main-thread "
      f"page scripts {N(ck + 'main_thread/with_cookie')} of {N(ck + 'main_thread/n')}). On {R(ck + 'stores_sbx_all_cookieless')} stores with a "
      f"sandboxed ad request before any choice, none of these requests carried a cookie, so an audit that looks for tracking through cookies "
      f"would not see them.")
    w('')
    w('### Numbers from earlier stages quoted in the paper')
    w('')
    w("Read by `analysis/checks.py` (`provenance`) from the saved files of the sampling, crawl, pilot and local-validation stages, so that "
      "every number in the manuscript is in stats.json; the file behind each group is named in `stats.json['checks']['provenance']`.")
    w('')
    w(f"- **Sampling.** Keyword screen: {N(pv + 'sample/keyword_screen_flagged')} titles flagged. Census buckets: {N(pv + 'sample/census_drawn')} "
      f"flagged domains verified; bottom bucket: {N(pv + 'sample/random_bucket_drawn')} of {N(pv + 'sample/random_bucket_flagged')} verified "
      f"in seeded random order (design weight {N(pv + 'sample/random_bucket_weight', 'f2')}; weights sum to {N(pv + 'sample/weight_sum', 'f1')}). "
      f"Product-list requests: {N(pv + 'sample/product_list_requests')} (landing page taken from the list for "
      f"{N(pv + 'sample/landing_from_product_list')} stores). Pilot-study Shopify hosts caught by the DNS rule: "
      f"{R(pv + 'sample/pilot_hosts_on_dns')}. Creator stratum: {N(pv + 'sample/creator_no_eligible_url')} of the pilot's store hosts had no "
      f"qualifying link ({N(pv + 'sample/creator_no_url_affiliate_or_click_id')} affiliate network or click identifier, "
      f"{N(pv + 'sample/creator_no_url_no_or_opaque_token')} no or an opaque token, {N(pv + 'sample/creator_no_url_creator_owned')} "
      f"creator-owned without a URL token, {N(pv + 'sample/creator_no_url_platform_site')} Shopify's own site); of "
      f"{N(pv + 'sample/creator_candidates')} candidates, a homepage check excluded {N(pv + 'sample/creator_verify_excluded')} "
      f"({N(pv + 'sample/creator_verify_headless')} headless, {N(pv + 'sample/creator_verify_no_markers')} without Shopify markers, "
      f"{N(pv + 'sample/creator_verify_blocked_403')} blocked, {N(pv + 'sample/creator_verify_rate_limited_429')} rate-limited), leaving "
      f"{N(pv + 'sample/creator_stratum')} stores, {N(pv + 'sample/creator_video_tokens')} with a per-video token and "
      f"{N(pv + 'sample/creator_in_main_sample')} also in the main sample.")
    w(f"- **Crawl.** {N(pv + 'crawl/loads_chromium')} loads in Chromium's headless shell (version {N(pv + 'crawl/chromium_major')}) and "
      f"{N(pv + 'crawl/loads_brave')} in Brave (version {N(pv + 'crawl/brave_major')}), from {G(pv + 'crawl/first_load_utc')} to "
      f"{G(pv + 'crawl/last_load_utc')} UTC; {N(pv + 'crawl/next_page_reloads')} next-page reloads; {N(pv + 'crawl/superseded_v1_loads')} "
      f"loads judged by the superseded banner detector and {N(pv + 'crawl/retry_originals')} retried first attempts; the final detector was "
      f"checked on {N(pv + 'crawl/check_v3_detector_stores')} stores ({N(pv + 'crawl/check_v3_detector_loads')} loads) and the first pilot "
      f"made {N(pv + 'crawl/pilot_v1_detector_loads')} loads; all {N(pv + 'crawl/redirect_host_google')} off-site redirects went to google.com. "
      f"Configuration join of ad requests: {KN(pv + 'crawl/join_strict')} from STRICT workers and {KN(pv + 'crawl/join_lax')} from LAX iframes.")
    w(f"- **Automatic 'yes' writes and scrolling** (all consent events of loads without a click): {N(pv + 'scroll/marketing_grants_without_click')} "
      f"changes of marketing to 'allowed', {N(pv + 'scroll/before_first_scroll')} before the first passive scroll; the other "
      f"{N(pv + 'scroll/after_first_scroll')}, on {N(pv + 'scroll/after_first_scroll_stores')} stores (consent tool: "
      f"{', '.join(G(pv + 'scroll/after_first_scroll_cmps'))}), came "
      f"{N(pv + 'scroll/after_first_scroll_lag_s_min', 'f1')}–{N(pv + 'scroll/after_first_scroll_lag_s_max', 'f1')} s after it.")
    w(f"- **Attribution checks.** LAX frames: in {N(pv + 'attribution/lax_records_sampled')} sampled load records, "
      f"{N(pv + 'attribution/lax_frames_with_attribute')} of {N(pv + 'attribution/lax_frames')} LAX frames carried a recorded sandbox attribute. "
      f"Spot check: {N(pv + 'attribution/spotcheck_strict_google_from_applovin')} of {N(pv + 'attribution/spotcheck_strict')} STRICT requests "
      f"were AppLovin cookie synchronizations to a Google endpoint. Declared blocklists: {N(pv + 'attribution/blocklist_sets/pandectes/stores')} "
      f"Pandectes stores with {N(pv + 'attribution/blocklist_sets/pandectes/distinct_sets')} distinct sets of blocked ad vendors, "
      f"{N(pv + 'attribution/blocklist_sets/onetrust/stores')} OneTrust stores with {N(pv + 'attribution/blocklist_sets/onetrust/distinct_sets')}.")
    w(f"- **Local validation.** GPC injection test page: the flag read true in the first statement of all "
      f"{N(pv + 'validation/selftest_targets_all_true')} of {N(pv + 'validation/selftest_targets')} target types in "
      f"{N(pv + 'validation/selftest_min_true_per_target')} of {N(pv + 'validation/selftest_runs')} runs; without injection, in "
      f"{N(pv + 'validation/control_true_first_statement')} of {N(pv + 'validation/control_runs')} runs. Brave with Shields off returned the "
      f"true hardware concurrency in {N(pv + 'validation/brave_shields_off_true_hw')} of {N(pv + 'validation/brave_shields_off_runs')} runs.")
    w(f"- **Pilot loads of Store C** (earlier creator-link study): under emulated GPC TikTok fired on {KN(pv + 'pilot/gpc_tiktok_fired')} "
      f"landing loads ({KN(pv + 'pilot/gpc_tiktok_fired_video')} per-video landings); in its Default loads TikTok's STRICT sandbox was created on "
      f"{KN(pv + 'pilot/default_tiktok_sandbox')} and Meta's library loaded on {KN(pv + 'pilot/default_meta_fbevents')}. Against "
      f"{KN(pv + 'pilot/crawl_gpc_misses')} TikTok firings in our GPC and repeat-GPC loads: Fisher's exact p = "
      f"{N(pv + 'pilot/fisher_p_video_vs_crawl', 'f2')}; two misses at the pilot's per-video rate have probability "
      f"{N(pv + 'pilot/p_two_misses_at_pilot_rate', 'f1')}. Of the {N(pv + 'pilot/edge_cached_gpc_loads')} edge-cached GPC loads, TikTok fired "
      f"on all {KN(pv + 'pilot/fired_within_threshold')} whose first worker came at most {N(pv + 'pilot/fired_lag_max_ms')} ms after the "
      f"consent script finished and on none of the {N(pv + 'pilot/not_fired_beyond_threshold/n')} later ones (at least "
      f"{N(pv + 'pilot/not_fired_lag_min_ms')} ms); the threshold was chosen after inspecting these loads.")
    w('')
    w('## 6. Limitations and deviations')
    w('')
    w(f"- **Concurrency above the agreed limit.** The first {N('context/loads_conc6')} loads ran at {N('design/concurrency_limit')} "
      f"concurrent browsers; a process from a 'coordinating session' then restarted the crawler at {N('design/concurrency_coordinator')}, and "
      f"{N('context/loads_conc10')} loads ran that way. Its note says this was at the user's request; that could not be verified and it "
      "exceeds the task's politeness limit. Per-site pacing was unchanged. Run segment is a sensitivity row in Fig S6.")
    w("- **One vantage point, one day.** California residential IP, headless Chromium with its default user agent (Meta's library drops "
      "events for headless browsers, so Meta beacons are undercounted), Brave (also headless) only for the native-GPC subsample. Other US "
      "states and the EU get different Shopify region defaults, so the region-default shares hold for our vantage point only.")
    w(f"- **The crawler was visible as automation** (see 'What the pages saw of our crawler'): `navigator.webdriver` was true and the user agent said 'HeadlessChrome' in "
      f"every usable load. Consent tools that react to this bias the results in known directions: Pandectes' bot rule (seen on "
      f"{N('automation/pandectes_bot/n_stores')} stores) hides the banner and grants consent, so pixels fire where a person would first meet an "
      f"opt-in banner (such stores are excluded from the blocked-on-paper primary; their pre-choice firing overstates what a person sees); "
      f"rules that hide a banner from bots (Usercentrics' user-agent test; OneTrust's server-side bot header, effect unknown) lower the banner "
      f"count and so the detector's apparent recall; the recall re-check used the same browser and cannot find banners suppressed for bots. "
      f"Our passive scrolls may also have triggered implied consent on scroll on the {N('automation/scroll_yes/n_after_scroll_stores')} stores "
      f"whose 'yes' came after a scroll. A headful re-run without the automation flag on the affected stores would bound these effects; it "
      f"needs a new crawl.")
    w(f"- **Banner timing** comes from polling every {N('design/banner_poll_ms')} ms, not from an observer; the conservative estimate is primary "
      "and future crawls should timestamp visibility with a MutationObserver or IntersectionObserver.")
    w("- **Decline only on the first layer.** Banners without a first-layer reject were not clicked; one missed reject button in the audit "
      "suggests the finder slightly under-counts non-English reject labels. Banners inside iframes were not clicked. Failed forced clicks are "
      "excluded from the Decline analysis and reported separately.")
    w("- **Screenshot audits are not yet human.** Fig S4 and the forced-click audit were labelled by the analysis assistant from the saved "
      "screenshots; an independent human re-labelling of the same seeded sample is still required before the method can be called validated. "
      f"Banner-detector recall was estimated from a later re-check load (see 'Checks added after the crawl'), at about {N('checks/recheck/recall/est_recall', 'pct0')}% "
      f"({N('checks/recheck/recall/est_recall_lo', 'pct0')}–{N('checks/recheck/recall/est_recall_hi', 'pct0')}%), again with assistant labels "
      "and assuming a banner seen on the re-check was also shown in the original load.")
    w(f"- **Declared blocklists** are readable only for Pandectes, OneTrust and Cookiebot, so the vendor-matched 'blocked on paper' rate rests "
      f"on {N('fig4/c/n_stores')} stores. Custom pixels are matched to vendors by name only (their code is not in the configuration).")
    w("- **Consent events of the Decline arm** were recorded on the last page only, so first-page state changes in Decline loads are "
      "known only from the once-a-second readings; the gate audit therefore excludes the first page of Decline loads (counts above).")
    w("- **Refusal signals** are read from request URLs only, as truncated in the request table (so flagged shares are lower bounds); bodies (e.g. Meta's data-processing options, TikTok's limited data use) are not "
      "in the request table.")
    w("- **Timing** mixes DevTools network timestamps and page clocks, the consent write time is the event dispatch, and data were collected "
      "under two concurrency levels.")
    wp = 'automation/worker_pause/'
    w(f"- **Instrumentation pause.** The crawler attaches to every worker with waitForDebuggerOnStart, so each worker waits until its network "
      f"capture is on: over {N(wp + 'all/n')} workers in {N(wp + 'all/loads')} usable loads the wait was a median {N(wp + 'all/median', 'f0')} ms "
      f"(90th percentile {N(wp + 'all/p90', 'f0')} ms, 99th {N(wp + 'all/p99', 'f0')} ms, maximum {N(wp + 'all/max')} ms); for STRICT "
      f"sandbox workers a median {N(wp + 'strict/median', 'f0')} ms, 90th percentile {N(wp + 'strict/p90', 'f0')} ms, maximum "
      f"{N(wp + 'strict/max')} ms, and {R(wp + 'strict/over_poll')} waited longer than one banner-polling interval. The pause delays "
      "sandboxed requests, so 'pixel before banner' is conservative; the race analysis times container creation, which the pause does not "
      "affect; store-level outcomes change only if a pause pushed a store's only request out of the observation window.")
    w(f"- **Integration mode is a product-level label** ({N('design/n_cmp_clusters')} consent products); the reference group is one product "
      "with an almost always denying default, so no model can separate mode from product or default.")
    w(f"- **Edge caches.** {N('context/nostra_stores')} main-sample stores (and Store C) served cached pages; their consent strings name "
      "other regions. They explain several gate-audit anomalies but not the headline rates (Fig S6).")
    w(f"- **Frame and projection.** The DNS frame (apex or www host on Shopify) has an estimated recall of about "
      f"{N('checks/frame_recall/recall', 'pct0')}% (bucket-wise bounds {N('checks/frame_recall/recall_lo', 'pct0')}–"
      f"{N('checks/frame_recall/recall_hi', 'pct0')}%), and only {N('checks/frame_recall/buckets/1-10k/recall', 'pct0')}% in the top bucket; it "
      f"also excludes storefronts on shop. or store. subdomains (an estimated {N('checks/frame_recall/est_sub_total')} in the top-200k). The "
      "projection covers the DNS-flagged Online Store storefronts only and is conditional on this frame.")
    w('')
    w('## 7. Files')
    w('')
    w("- Code: `analysis/common.py`, `extract_raw.py`, `build_store_table.py`, `gate_audit.py`, `analyze.py`, `models.py`, `audit_sample.py`, "
      "`write_results.py`, `trace_check.py`, `run_all.sh`; figures: `figures/scripts/*.py`, `figures/style.mplstyle`, `figures/colors.py`, "
      "`figures/validate_palettes.sh`, `figures/scripts/check_fonts.py`.")
    w("- Audit data: `analysis/audit_labels.csv`, `analysis/forced_click_audit.csv` (assistant labels).")
    w("- Outputs: `analysis/outputs/` (stats.json, one CSV per panel, store_table.csv, sandbox_creations.csv, raw_stacks.csv, models_table.csv); "
      "panels: `figures/panels/*.pdf|png`; checks: `figures/palette_validation.txt`, `figures/font_check.txt`.")
    w("- Rebuild: `zsh analysis/run_all.sh`.")
    open(os.path.join(STUDY, 'analysis', 'RESULTS.md'), 'w').write('\n'.join(L) + '\n')
    numreg.save('number_registry_results.csv')


def takeaways():
    numreg.reset()
    L = []
    w = L.append
    w('# Figure takeaways (updated to the data)')
    w('')
    w('One sentence per figure. "Planned" is the sentence in FIGURE_PLAN.md; "Now" is what the data support after the review revisions of '
      '2026-09-26. Numbers come from `analysis/outputs/stats.json` (checked by `analysis/trace_check.py`).')
    w('')
    w('## Figure 1: Where consent fails (situating the field)')
    w("- Planned: On Shopify stores, ad pixels run inside a sandbox that the cookie banner's script blocker cannot see; the only gate is "
      "Shopify's consent state, and for US visitors it defaults to 'allowed'.")
    w(f"- Status: supported for our California vantage point: Shopify's region default was 'allowed until choice' on "
      f"{N('fig1b/region_allowed/p', 'pct0')}% of stores.")
    w(f"- Now: On popular Shopify stores ad pixels run in a sandbox that cookie-banner blockers cannot see; at our California vantage point "
      f"Shopify's gate defaulted to 'allowed' on {N('fig1b/region_allowed/p', 'pct0')}% of stores, and a sandboxed ad pixel sent requests "
      f"before any choice on {N('fig1b/banner_fires/p', 'pct0')}% of stores that showed a consent banner ({N('fig1b/nobanner_fires/p', 'pct0')}% "
      f"of stores without one).")
    w('')
    w('## Figure 2: Measurement pipeline (methodology)')
    w("- Planned: We sample popular Shopify stores from a public ranking, load each under four controlled conditions, and attribute every "
      "ad request to its origin and payload.")
    w(f"- Status: supported with corrections: three base arms plus validation loads (repeats, and Brave's native GPC on "
      f"{N('design/brave_subsample')} stores), with GPC emulated in Chromium.")
    w(f"- Now: We sampled {N('design/n_main')} popular Shopify stores from the Tranco top-200k, loaded each under Default, Decline and GPC "
      f"(plus repeats and a native-GPC check), and attributed every ad request to its origin, vendor, timing and payload.")
    w('')
    w('## Figure 3: Pixels fire before any choice')
    w("- Planned: On stores that show a consent banner, sandboxed ad pixels usually fire before the visitor has made any choice.")
    w(f"- Status: partly supported; 'usually' is too strong overall ({N('fig3/a/any/banner/p', 'pct0')}% of banner stores) but holds "
      f"where Shopify's default is 'allowed' ({N('fig3/d/opt_out/any_sbx/p', 'pct0')}%).")
    w(f"- Now: On half of the stores that show a consent banner ({N('fig3/a/any/banner/p', 'pct0')}%), and on "
      f"{N('fig3/d/opt_out/any_sbx/p', 'pct0')}% where Shopify's region default is 'allowed', sandboxed ad pixels send requests before any "
      f"choice, and on {N('fig3/b/before_banner_by_poll/p', 'pct0')}% of the banner stores where they did, the first request left clearly "
      f"before the banner was even visible.")
    w('')
    w('## Figure 4: Blocked on paper')
    w("- Planned: Many consent tools declare a vendor as blocked or 'marketing' while that vendor's sandboxed pixel fires anyway; the gap "
      "depends on how the tool integrates with Shopify.")
    w(f"- Status: supported on a small readable base ({N('fig4/a/blocklist/any_sbx/n')} stores, {N('fig4/a/blocklist/n_cmps')} tools); the "
      f"differences between tools track Shopify's region default more than the integration mode.")
    w(f"- Now (revised after referee review): Where a consent tool's blocklist names an ad vendor as blocked and the tool had not itself "
      f"consented for our browser, that vendor's own sandboxed pixel still fired before any choice on "
      f"{N('fig4/a/blocklist/primary/fired/k')} of {N('fig4/a/blocklist/primary/fired/n')} stores ({N('fig4/a/blocklist/declared_vendor_fired_sbx/k')} "
      f"of {N('fig4/a/blocklist/declared_vendor_fired_sbx/n')} unconditioned), and, like for like, blocklist stores fired no less often than "
      f"stores without a declaration (difference {N('fig4/a/like_for_like/mh_no_yes/rd', 'pct0')} pp, 95% CI "
      f"{N('fig4/a/like_for_like/mh_no_yes/rd_lo', 'pct0')} to {N('fig4/a/like_for_like/mh_no_yes/rd_hi', 'pct0')}): Shopify's state, not the "
      f"blocklist, decided; in one re-check load the blocker neutralized a vendor's page tag while its sandboxed pixel sent requests on "
      f"{N('checks/recheck/blocker/stores_neutralized_and_sbx')} stores.")
    w('')
    w('## Figure 5: Do visitor choices work?')
    w("- Planned: Clicking Decline mostly stops sandboxed pixels only when the banner is wired to Shopify's consent API, and GPC is "
      "honoured unevenly.")
    w(f"- Status: revised. Shopify's gate held for pixels that declare the refused purpose ({N('fig5/c/gate_audit/gpc_sale_pixels/k')} of "
      f"{N('fig5/c/gate_audit/gpc_sale_pixels/n')} sale-declaring pixels started under GPC); after a working Decline and under GPC the "
      f"fresh-page residuals were {N('fig5/a/Any vendor/Decline/p', 'pct0')}% vs {N('fig5/a/Any vendor/GPC/p', 'pct0')}%, against "
      f"{N('fig5/a/Any vendor/Default/p', 'pct0')}% under Default in the same window (paired difference Decline minus GPC "
      f"{N('fig5/compare/equal_window/paired_diff/diff', 'pct1')} pp, 95% CI {N('fig5/compare/equal_window/paired_diff/diff_lo', 'pct1')} to "
      f"{N('fig5/compare/equal_window/paired_diff/diff_hi', 'pct1')}; exact McNemar p = {N('fig5/compare/equal_window/p_exact', 'f3')}): for "
      f"post-choice persistence GPC's advantage was at most about {N('fig5/compare/equal_window/paired_diff/diff_hi', 'pct0')} points, while "
      f"over the whole visit a Decline user is exposed before the click, which GPC avoids.")
    w(f"- Now: Shopify honours a recorded refusal for pixels that declare the refused purpose, so what keeps firing after a working Decline "
      f"({N('fig5/decline/fresh/p', 'pct0')}% of stores on a fresh page) and under GPC ({N('fig5/gpc_residual/p', 'pct0')}% of stores that "
      f"fired under Default) is pixels that declare no purpose (F4), pixels whose declared purpose the choice left allowed (after Decline, "
      f"typically sale of data; under GPC, marketing), pixels started before the choice that kept sending, including unload beacons (F3), "
      f"and CMP writes that lose the race ({N('fig5/d/deny/pixels_before')} of {N('fig5/d/deny/pixels')} third-party 'marketing' sandboxes "
      f"started before a CMP's automatic 'no').")
    w('')
    w('## Figure 6: What reaches the vendors')
    w("- Planned: Whatever sits in the URL (including a creator's per-video campaign code) reaches ad vendors through the sandbox, and the "
      "findings are stable across repeat loads and native vs emulated GPC.")
    w("- Status: supported, now one message; validation moved to Fig S4d and the projection to a table (formerly Fig 5e). Panels in reading order: (a) URL "
      "share, (b) refusal signals, (c) the creator store (Store C), on which the per-video evidence rests.")
    w(f"- Now: {N('fig6/a/sandboxed_A0/p', 'pct0')}% of sandboxed ad beacons carry the full landing URL, a creator's per-video code reached "
      f"TikTok from its sandbox before any choice, and after a refusal Google's requests often carry a refusal signal of Google's own "
      f"(Consent Mode 'denied', npa or rdp; {N('fig6/c/Google/Decline/p', 'pct0')}% on the next page after Decline) while requests of vendors "
      f"other than Google and Microsoft carry none that we can see.")
    w('')
    w('## Supplementary')
    i_sh = s2('shopify_native')
    w(f"- S2: Shopify's own banner has the lowest pre-choice rate of any consent tool ({N(f'supp/S2/{i_sh}/prechoice_sbx/p', 'pct0')}%) and "
      f"also the most denying region defaults ({N(f'supp/S2/{i_sh}/region_denied/p', 'pct0')}%), so tools cannot be ranked on these data.")
    w(f"- S3: Pre-choice firing on banner stores is about the same in each of the three larger Tranco rank buckets "
      f"({N('supp/S3_prechoice_banner_range/lo', 'pct0')}–{N('supp/S3_prechoice_banner_range/hi', 'pct0')}%); banner prevalence and the small-sample Decline residual vary more.")
    w(f"- S4: The crawler's banner, reject and click labels agree with the screenshots in {N('supp/S4/banner_precision/k')}/"
      f"{N('supp/S4/banner_precision/n')}, {N('supp/S4/reject_agreement/k')}/{N('supp/S4/reject_agreement/n')} and "
      f"{N('supp/S4/click_flag_agreement/k')}/{N('supp/S4/click_flag_agreement/n')} audited loads (assistant labels, human re-labelling "
      f"pending), and repeat loads agree with kappa {N('validation/A0_vs_A0r/kappa', 'f3')}.")
    w(f"- S5: How much of a vendor's tracking runs in the sandbox varies from {N('supp/S5_sandbox_share_min/p', 'pct0')}% to "
      f"{N('supp/S5_sandbox_share_max/p', 'pct0')}% of its requests; TikTok ({N('supp/S5_rows/3/sandbox_share_requests', 'pct0')}%) and "
      f"Pinterest ({N('supp/S5_rows/5/sandbox_share_requests', 'pct0')}%) send most requests from it, Google Ads "
      f"({N('supp/S5_rows/0/sandbox_share_requests', 'pct0')}%) and Meta ({N('supp/S5_rows/1/sandbox_share_requests', 'pct0')}%) mostly do not.")
    w(f"- S6: All {N('supp/S6_robustness_variants')} robustness variants give intervals that overlap the main estimates; beacon-only "
      f"definitions lower the rates slightly.")
    open(os.path.join(STUDY, 'figures', 'takeaways.md'), 'w').write('\n'.join(L) + '\n')
    numreg.save('number_registry_takeaways.csv')


if __name__ == '__main__':
    results()
    takeaways()
    print('wrote RESULTS.md and takeaways.md')
