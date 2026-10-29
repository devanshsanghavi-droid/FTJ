"""Score the human re-labels (…_HUMAN.csv) against the assistant's labels and the crawler's rules; writes human_agreement.json."""
import json, os
import pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); ST = os.path.join(H, '..', '..')


def kappa(a, b):
    a = pd.Series(a).astype(str).values; b = pd.Series(b).astype(str).values
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((list(a).count(c) / n) * (list(b).count(c) / n) for c in cats)
    return dict(n=n, agree=int(round(po * n)), raw=po, kappa=(po - pe) / (1 - pe) if pe < 1 else 1.0)


out = {}
fp = os.path.join(H, 'A_decline_audit_HUMAN.csv')
if os.path.exists(fp):
    Hh = pd.read_csv(fp).merge(pd.read_csv(os.path.join(H, '_key_A_decline_audit.csv')), on='code')
    A = Hh.merge(pd.read_csv(os.path.join(ST, 'analysis', 'audit_labels.csv')), on='store_id')
    out['A_banner'] = kappa(A.banner_visible_pre_0_1, A.audit_banner_visible)
    out['A_reject'] = kappa(A.first_layer_reject_offered_0_1, A.audit_reject_first_layer)
    c = A[A.banner_gone_after_click_0_1_or_blank.notna()]
    out['A_click'] = kappa(c.banner_gone_after_click_0_1_or_blank, c.audit_banner_gone_after_click)
fp = os.path.join(H, 'B_forced_clicks_HUMAN.csv')
if os.path.exists(fp):
    B = pd.read_csv(fp).merge(pd.read_csv(os.path.join(H, '_key_B_forced_clicks.csv')), on='code').merge(
        pd.read_csv(os.path.join(ST, 'analysis', 'forced_click_audit.csv')), on='store_id')
    out['B_click_failed'] = kappa(B.click_failed_0_1, B.audit_click_failed)
fp = os.path.join(H, 'C_recheck_recall_HUMAN.csv')
if os.path.exists(fp):
    C = pd.read_csv(fp).merge(pd.read_csv(os.path.join(ST, 'crawl', 'recheck', 'sheets', 'labels_assistant.csv')), on='code')
    C = C[C.consent_banner_visible.isin(['yes', 'no'])]
    out['C_banner'] = kappa(C.consent_banner_visible_yes_no.str.lower(), C.consent_banner_visible)
fp = os.path.join(H, 'D_content_screen_HUMAN.csv')
if os.path.exists(fp):
    D = pd.read_csv(fp).merge(pd.read_csv(os.path.join(ST, 'sample', 'raw', 'content_review.csv'))[['domain', 'decision']], on='domain')
    out['D_decision'] = kappa(D.decision_keep_or_exclude_adult_or_exclude_child, D.decision)
json.dump(out, open(os.path.join(H, 'human_agreement.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
