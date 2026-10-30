"""Approximate word counts of the manuscript (LaTeX markup and \\todo items for the authors stripped). Usage: python wordcount.py"""
import glob
import re


def drop_todo(s):
    # remove \todo{...} (open items for the authors) with balanced braces
    out, i = [], 0
    while True:
        j = s.find('\\todo{', i)
        if j < 0:
            out.append(s[i:]); break
        out.append(s[i:j]); k, d = j + 6, 1
        while d:
            d += {'{': 1, '}': -1}.get(s[k], 0); k += 1
        i = k
    return ''.join(out)


def strip(s):
    s = drop_todo(s)
    s = re.sub(r'(?<!\\)%.*', '', s)
    s = re.sub(r'\\(?:cite[tp]?|ref|label|input|tabinput|includegraphics)(?:\[[^\]]*\])?\{[^}]*\}', ' X ', s)
    s = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?', ' ', s)
    s = re.sub(r'[{}$~\\&]', ' ', s)
    return s


def words(s):
    return len([w for w in strip(s).split() if re.search(r'[A-Za-z0-9]', w)])


secs = sorted(glob.glob('sections/*.tex'))
body = ''.join(open(f).read() for f in secs)
# v2 figures (2026-09-27): the captions are \input from captions/figN.tex; inline them so they are counted as captions
body = re.sub(r'\\input\{(captions/fig\d)\}', lambda m: open(m.group(1) + '.tex').read(), body)
floats = ''.join(re.findall(r'\\begin\{(?:widefig|table\*?)\}.*?\\end\{(?:widefig|table\*?)\}', body, flags=re.S))
nofloat = re.sub(r'\\begin\{(?:widefig|table\*?)\}.*?\\end\{(?:widefig|table\*?)\}', ' ', body, flags=re.S)
fm = open('frontmatter.tex').read()
abstract = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', fm, flags=re.S).group(1)
print('abstract words:', words(abstract))
print('main text (sections, without figures/tables):', words(nofloat))
print('captions and tables:', words(floats))
print('main text incl. captions/tables:', words(body))
for f in secs:
    t = re.sub(r'\\begin\{(?:widefig|table\*?)\}.*?\\end\{(?:widefig|table\*?)\}', ' ', open(f).read(), flags=re.S)
    print(f'  {f}: {words(t)}')
