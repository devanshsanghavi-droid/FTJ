Human re-labelling kit (final audit, 2026-09-26)

Every validation label in the paper so far was made by the AI assistant. A human author must re-label the
items below BLIND, i.e. without opening the _key_*.csv files, the assistant's label files or the crawler outputs.
Work only from the screenshots / titles named in each BLANK file. Save the filled copy as *_HUMAN.csv next to
the BLANK file (same columns), then run:  /opt/anaconda3/bin/python3 score_agreement.py
It writes human_agreement.json (raw agreement and Cohen's kappa against the assistant's labels and the crawler's
rules). Report those numbers in Section 6.3, Supplementary Fig. S4 and Table S2, and remove the \todo items.

A  A_decline_audit_BLANK.csv    54 seeded Decline loads (pre/post screenshots in crawl/screenshots).
     banner_visible_pre: 1 if a cookie/privacy consent banner is visible in the pre-click shot.
     first_layer_reject_offered: 1 if that banner shows a reject/decline control without opening settings.
     banner_gone_after_click: only if the load was clicked (post shot exists): 1 if the banner is gone.
B  B_forced_clicks_BLANK.csv    12 forced clicks: is an overlay (modal, age gate, chat) covering the banner in
     the pre shot; is the banner still visible in the post shot; did the click fail (banner still there).
C  C_recheck_recall_BLANK.csv   129 re-check loads, as blind contact sheets (crawl/recheck/sheets/sheet_NN.jpg,
     5 codes per sheet; each row shows the viewport about 3, 6 and 10 s after load). Label yes if a cookie or
     privacy consent banner/notice (including a notice-only bar) is visible in ANY of the three shots; newsletter,
     discount, shipping-country and survey pop-ups are not consent banners. Zoom into the full screenshots if a
     bar is small (the assistant found one only on a crop).
D  D_content_screen_BLANK.csv   the 21 titles flagged by the sampling keyword screen: keep / exclude_adult /
     exclude_child (child-directed = products or content aimed mainly at children, not at parents).
E  E_broader_child_screen_BLANK.csv  37 further sampled stores whose title matched a broader child/baby keyword
     list (screen run after the crawl). NOTE: two of them (S0356, S0614) sell adult products and were loaded in
     every arm of the main crawl; S0145 and S1292 (not in this list's regex; noticed on a re-check screenshot)
     look child-directed. Decide keep/exclude for each; if any store is excluded, remove it from
     sample/sample.csv analyses and re-run analysis/run_all.sh (all numbers are regenerated).
