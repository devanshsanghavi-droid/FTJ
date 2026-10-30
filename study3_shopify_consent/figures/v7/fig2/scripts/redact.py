"""Redaction rules for the worked request in Fig 2B (and its caption).

The paper reports stores only in aggregate and names none (ethics statement); released data use pseudonymous IDs.
A real request path can still identify a store: the landing page's product slug is searchable, and the advertiser's
account number is an identifier. Both are masked before anything is drawn or registered:

  mask_account('/pagead/viewthroughconversion/<account digits>/') -> '/pagead/viewthroughconversion/•••/'
  mask_product('/products/<slug>')                                -> '/products/<product>'

Only the pseudonymous test code (cmpstudy-S<id>) is shown in full. check_fig2_numbers.py re-applies the same named
mask to the current source value, so the registries (panels/fig2_numbers.csv) never hold the unmasked strings.
"""
import re


def mask_account(path):
    """The advertiser's account number in the request path, shown as bullets."""
    out = re.sub(r'/\d{5,}/', '/•••/', path)
    assert not re.search(r'\d{5,}', out), out
    return out


def mask_product(path):
    """The landing page's product (or collection, page) slug, shown as a placeholder; the page type is kept."""
    m = re.match(r'^/(products|collections|pages)/[^/?#]+', path)
    assert m, f'unexpected landing path shape: {path[:12]}...'
    return f'/{m.group(1)}/<{m.group(1).rstrip("s")}>'


MASKS = {'account': mask_account, 'product': mask_product}


def apply(name, value):
    return MASKS[name](value) if name else value
