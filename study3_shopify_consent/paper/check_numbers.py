"""Number check for the manuscript: every numeric token in the text must appear in RESULTS.md / stats.json.

Sources (strict since the consistency pass of 2026-09-26; all written by the analysis pipeline, never typed for the paper):
  analysis/outputs/number_registry_*.csv  (numbers rendered from stats.json for RESULTS.md / takeaways.md)
  analysis/outputs/stats.json              (every value, rendered as int, %, 1-3 decimals); since the consistency pass it also
                                           holds, under checks/provenance, the sampling-, crawl-, pilot- and validation-stage
                                           numbers that the paper quotes (read by analysis/checks.py from their saved files)
  analysis/RESULTS.md, figures/takeaways.md (numeric tokens in the text)
  paper/tables/*.json                      (outputs of the paper's own table scripts, which read the pipeline outputs)
  sample/raw/funnel.json                   (sampling funnel behind the generated Table S1 and the Fig. 2 schematic)
  stats.json['derived_v2']                 (v2 figures' derived numbers, each with script and inputs in
                                           analysis/outputs/derived_numbers_provenance.json; merged by merge_derived_numbers.py)
  stats.json['round4']                     (Round 4, 27 Sep 2026: round4/analysis/stats_r4.json copied unchanged by
                                           analysis/merge_round4_numbers.py; its registry number_registry_r4.csv and
                                           RESULTS_R4.md are sources too; analysis/trace_check.py check 5 keeps them in sync)
The crawl, sample, mechanism and review notes are NO LONGER sources. Literature numbers and two sums are listed below with
their source. Structural tokens (section/figure/table numbers, dates, years, versions, legal citations, code) are masked.
Writes paper/check_numbers.txt; exit code 1 if anything is untraced.
This check shows that each number OCCURS in a saved output; check_semantic.py (called at the end) checks that percentages,
intervals and k-of-n pairs agree with each other and with stats.json, and that the abstract, highlights and figure titles
render the right stats.json keys. Every count written as "k of n" or "k/n" is also looked up as a (k, n) pair in stats.json
(paper/check_numbers_pairs.txt lists the matching keys); the rest must be checked by reading.
"""
import csv
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(HERE)
NUM = re.compile(r'(?<![\w.\-@#,])(\d[\d,]*(?:\.\d+)?)')

# numbers that are simple arithmetic on saved values (value -> derivation)
DERIVED = {
    '8': 'stores with edge-cached pages: 7 main-sample stores (stats.json context/cf_hit_stores) + Store C (creator store C005)',
    '976': 'SB 690 chaptered as Chapter 976, Statutes of 2026 (leginfo bill history, approved by the Governor 30 Sep 2026; checked 1 Oct 2026)',
    '24': 'Table 1 row count: 1 + 6 + 3 + 8 + 6 consent products (the table itself; notes/mechanism.md section 4; Pentos removed 2026-09-29 as unverifiable)',
    # v7 Fig. 2a branches (figures/v7/fig2/derived_numbers.json, derive_fig2.py; not merged into stats.json['derived_v2'])
    '197,366': 'Fig. 2a: Tranco domains not on Shopify = design.tranco_top_n 200,000 - DNS-flagged 2,634 (figures/v7/fig2/derived_numbers.json fig2a_not_on_shopify)',
    '1,116': 'Fig. 2a: lowest-bucket domains not drawn = checks/provenance/sample random_bucket_flagged 1,732 - random_bucket_drawn 616 (figures/v7/fig2/derived_numbers.json fig2a_not_drawn)',
}
# numbers quoted from the literature (value -> source); checked against notes/prior_work.md and the cited papers
LITERATURE = {
    '65.4': 'bouhoula2024automated: 65.4% of sites with a reject option likely collect data after rejection (notes/prior_work.md row 4)',
    '1,793': 'tang2025navigating: 1,793 sites in 8 regions (notes/prior_work.md row 1)',
    '7,634': 'libert2026webxray: 7,634 California sites (notes/prior_work.md row 14)',
    '55': 'libert2026webxray: 55% set ad cookies despite GPC (notes/prior_work.md row 14)',
    '31': 'nouwens2025crosscountry: top lists of 31 countries (notes/prior_work.md row 2)',
}

sources = set()


def add_text_numbers(text):
    for m in NUM.finditer(text):
        sources.add(m.group(1).rstrip(',.'))


def render_all(v):
    out = set()
    if isinstance(v, bool) or v is None:
        return out
    if isinstance(v, int):
        out |= {f'{v:,}', str(v)}
    elif isinstance(v, float):
        out |= {f'{v:,.0f}', f'{v:.1f}', f'{v:,.1f}', f'{v:.2f}', f'{v:.3f}'}
        if 0 <= v <= 1:
            out |= {f'{100 * v:.0f}', f'{100 * v:.1f}'}
    return out


def walk(x):
    if isinstance(x, dict):
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
    else:
        sources.update(render_all(x))


for fn in glob.glob(os.path.join(STUDY, 'analysis', 'outputs', 'number_registry_*.csv')) + \
        [os.path.join(STUDY, 'round4', 'analysis', 'outputs', 'number_registry_r4.csv')]:   # Round 4 registry (2026-09-27)
    for r in csv.DictReader(open(fn)):
        sources.add(r['text'])
walk(json.load(open(os.path.join(STUDY, 'analysis', 'outputs', 'stats.json'))))
for fn in glob.glob(os.path.join(HERE, 'tables', '*.json')) + [os.path.join(STUDY, 'sample', 'raw', 'funnel.json')]:
    walk(json.load(open(fn)))
for rel in ['analysis/RESULTS.md', 'figures/takeaways.md', 'round4/analysis/RESULTS_R4.md']:
    add_text_numbers(open(os.path.join(STUDY, rel)).read())

STRUCT = [
    r'\\(?:ref|label|cite[tp]?|citet|citep|input|includegraphics|finalfig|suppfig|todo|url|href)\*?(?:\[[^\]]*\])?\{[^}]*\}',
    r'\\code\{(?:[^{}]|\{[^{}]*\})*\}',                  # code spans, consent strings, URLs
    r'\\(?:begin|end)\{[^}]*\}(?:\{[^}]*\})?',
    r'\\(?:multicolumn|fontsize)\{[^}]*\}\{[^}]*\}',
    r'\\(?:sub)*section\*?\{[^}]*\}',
    r'\b(?:Section|Sections|Table|Tables|Fig|Figs|Figure|Figures)\.?~?\s*S?\d+(?:\.\d+)*[a-d]?(?:\s*(?:--|and|,)\s*S?\d+(?:\.\d+)*[a-d]?)*',
    r'\bS\d(?:--S\d)?\b', r'\bRQ\d\b', r'\\RQ\{\d\}', r'\bF\d(?:\s*(?:--|to)\s*F\d)?\b', r'\bP\d\b',
    r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
    r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
    r'\b(?:19|20)\d{2}\b',                                # years
    r'\b\d{2}:\d{2}\b', r'\bversions?\s+\d+(?:\s+and\s+\d+)?\b', r'\bArticle~?\s*\d+\(\d+\)', r'\b\d{4}/\d+/EC\b', r'\(EU\)\s*\d{4}/\d+',
    r'\bHTTP\s+\d{3}\b', r'\b(?:returned|status)\s+\d{3}\b',
    r'\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b',              # ORCID iD (title page, 2026-09-29)
    r'\b95\\?%', r'\b23\.227\.32\.0/19\b', r'\b1366\$\\times\$900\b', r'\\kappa\s*\\ge\s*0\.81', r'\$\\kappa=0\.81\$',
    r'\bn\s*<\s*5\b', r'\$n\s*<\s*5\$', r'\$n\\ge5\$', r'\$N_h/n_h\$', r'\b1--10k|10k--50k|50k--100k|100k--200k\b',
    r'\btop[- ]200,000\b', r'\b200,001--1,000,000\b', r'\b200k--1M\b', r'\b200,000 to 1,000,000\b',   # Round 4 rank range r'\btop 200\{?,\}?000\b', r'\btop 10,000\b', r'\bL5PZ4\b', r'\bc8540278\b',
    r'\\(?:small|footnotesize|medskip|addlinespace|midrule|toprule|bottomrule)\b', r'\\setlength\{[^}]*\}\{[^}]*\}',
    r'\[(?:\d+(?:\.\d+)?(?:mm|pt|ex))\]', r'\d+(?:\.\d+)?\s*(?:mm|pt)\b', r'\\\\\[[^\]]*\]',
    r'\\[a-zA-Z]+',                                       # any remaining macro name
]
STRUCT_RX = re.compile('|'.join(STRUCT))


def check(path):
    bad, n_tok = [], 0
    for ln, line in enumerate(open(path), 1):
        line = re.sub(r'(?<!\\)%.*', '', line)            # comments
        if not line.strip():
            continue
        body = line.replace('{,}', ',')
        body = STRUCT_RX.sub(lambda m: ' ' * len(m.group(0)), body)
        for m in NUM.finditer(body):
            tok = m.group(1).rstrip(',.')
            if not tok:
                continue
            n_tok += 1
            if tok in sources or tok in DERIVED or (tok in LITERATURE and 's3_related' in path):
                continue
            # single digits used as counts in prose ("three", list numbering) are allowed only if in sources
            bad.append(f'UNTRACED {os.path.relpath(path, HERE)}:{ln}: "{tok}" in: {line.strip()[:150]}')
    return n_tok, bad


# ---- k-of-n pairs: map every count of the form "k of n" or "k/n" to the stats.json records that hold that pair ----
PAIRS = {}


SAME_RECORD = {}


def walk_pairs(x, path=''):
    if isinstance(x, dict):
        if all(isinstance(x.get(c), (int, float)) and x.get(c) == x.get(c) for c in ('k', 'n')):
            PAIRS.setdefault((int(x['k']), int(x['n'])), []).append(path.lstrip('/'))
        # consistency pass: two integer counts held by the same record (e.g. supp/S5_rows gpc_still and stores_default,
        # validation/brave_power stores_default_gpc_differ and n_stores) also form a pair; marked 'same record'
        ints = {c: int(v) for c, v in x.items() if isinstance(v, int) and not isinstance(v, bool)}
        for c1, v1 in ints.items():
            for c2, v2 in ints.items():
                if c1 != c2 and 0 <= v1 <= v2:
                    SAME_RECORD.setdefault((v1, v2), []).append(f"{path.lstrip('/')}[{c1}/{c2}]")
        for k, v in x.items():
            walk_pairs(v, f'{path}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            walk_pairs(v, f'{path}/{i}')


walk_pairs(json.load(open(os.path.join(STUDY, 'analysis', 'outputs', 'stats.json'))))
TEXT_PAIRS = set()
for rel in ['analysis/RESULTS.md']:
    for m in re.finditer(r'(\d[\d,]*)\s*(?:of|/)\s*(?:the\s+)?(\d[\d,]*)', open(os.path.join(STUDY, rel)).read()):
        TEXT_PAIRS.add((int(m.group(1).replace(',', '')), int(m.group(2).replace(',', ''))))
# 'k of [up to three words] n' or 'k/n'; the words may not be 'and' / 'or' ('39 of these stores and 109 pairs' is not a pair)
PAIR_RX = re.compile(r'(?<![\w.])(\d[\d,]*)(?:\s+of(?:\s+the)?(?:\s+(?!and\b|or\b)[a-z-]+){0,3}?\s+|/)(\d[\d,]*)(?![\d.])')


def pairs_in(path):
    out = []
    for ln, line in enumerate(open(path), 1):
        line = re.sub(r'(?<!\\)%.*', '', line).replace('{,}', ',')
        line = STRUCT_RX.sub(lambda m: ' ' * len(m.group(0)), line)
        for m in PAIR_RX.finditer(line):
            k, n = int(m.group(1).replace(',', '')), int(m.group(2).replace(',', ''))
            if n < 2 or k > n:
                continue
            keys = PAIRS.get((k, n), []) or [s_ + ' (same record)' for s_ in SAME_RECORD.get((k, n), [])]
            where = ', '.join(keys[:3]) + (' ...' if len(keys) > 3 else '') if keys else ('text of RESULTS.md' if (k, n) in TEXT_PAIRS else 'UNMAPPED')
            out.append(f'{os.path.relpath(path, HERE)}:{ln}: {k} of {n} -> {where}')
    return out


files = [os.path.join(HERE, f) for f in ['frontmatter.tex', 'backmatter.tex', 'supplement.tex', 'highlights.tex']]
files += sorted(glob.glob(os.path.join(HERE, 'sections', '*.tex')))
# consistency pass 2026-09-26: the generated tables that the manuscript \tabinput's are checked too
files += sorted(glob.glob(os.path.join(HERE, 'tables', '*.tex')))
# v2 figure integration 2026-09-27: the captions are generated files (captions/*.tex, integrate_figures_v2.py) that the
# figure environments \input; their numbers come from stats.json, including stats.json['derived_v2'], the v2 figures'
# derived numbers merged by analysis/merge_derived_numbers.py
files += sorted(glob.glob(os.path.join(HERE, 'captions', '*.tex')))
report, total, fails = [], 0, 0
for f in files:
    n_tok, bad = check(f)
    total += n_tok
    fails += len(bad)
    report += bad
    report.append(f'{os.path.relpath(f, HERE)}: {n_tok} numeric tokens, {n_tok - len(bad)} traced')
report.append(f'DERIVED allowances: {DERIVED}')
report.append(f'LITERATURE (s3_related.tex only): {LITERATURE}')
pair_lines = []
for f in files:
    pair_lines += pairs_in(f)
open(os.path.join(HERE, 'check_numbers_pairs.txt'), 'w').write(
    'Counts of the form "k of n" / "k/n" in the manuscript and the stats.json records that hold the same pair.\n'
    'UNMAPPED pairs are not errors (they may come from notes or be ranges) but must be checked by reading.\n\n' + '\n'.join(pair_lines) + '\n')
n_unm = sum('UNMAPPED' in l for l in pair_lines)
report.append(f'k-of-n pairs: {len(pair_lines)} found, {len(pair_lines) - n_unm} mapped to a stats.json key or a saved output, {n_unm} to check by reading (check_numbers_pairs.txt)')
# ---- semantic checks (check_semantic.py): percentages vs their own k/n, intervals vs Wilson or the stats.json record of the
# same pair, other estimate-interval triples vs stats.json, and a registry of the abstract/highlight/caption claims ----
import check_semantic
sem_fail, sem_notes = check_semantic.run(files)
open(os.path.join(HERE, 'check_numbers_semantic.txt'), 'w').write(
    'Semantic checks (check_semantic.py). FAIL lines must be fixed; the other lines show what each checked number matched.\n\n'
    + '\n'.join(['FAIL ' + x for x in sem_fail] + sem_notes) + '\n')
report += ['SEMANTIC FAIL ' + x for x in sem_fail]
report.append(f'semantic checks: {len(sem_notes)} passed, {len(sem_fail)} failed (check_numbers_semantic.txt)')
fails += len(sem_fail)
report.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails} untraced or inconsistent)') + f' ({total} tokens)')
open(os.path.join(HERE, 'check_numbers.txt'), 'w').write('\n'.join(report) + '\n')
print('\n'.join(r for r in report if not r.endswith('traced') or 'UNTRACED' in r))
sys.exit(0 if fails == 0 else 1)
