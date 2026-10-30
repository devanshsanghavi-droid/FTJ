"""Minimal RFC 9309 robots.txt matcher (standard library only).

* Group selection: the groups whose user-agent line matches our product token (case-insensitive;
  the line value equals the token, or the token starts with it); if none, the '*' groups. Several
  matching groups are merged.
* Rules: allow/disallow path patterns with '*' and '$'. The longest matching pattern wins; on a tie
  allow wins. An empty disallow is no rule. '/robots.txt' is always allowed.
* Status handling (done by the caller): 4xx -> allow all; 5xx / unreachable -> skip the site (our rule).
"""
import re
import urllib.parse


def _norm_path(p):
    # percent-encode everything that is not already encoded or reserved, as RFC 9309 compares encoded octets
    return urllib.parse.quote(p, safe="/%*$?=&;:@+,!~'()[]-._")


class Robots:
    def __init__(self, text, token):
        self.token = token.lower()
        self.rules = self._parse(text or "")

    def _parse(self, text):
        groups = []  # list of (agents, rules)
        cur_agents, cur_rules, in_rules = [], [], False
        for raw in text.splitlines()[:20000]:
            line = raw.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip().lower(), v.strip()
            if k in ("user-agent", "useragent", "user agent"):
                if in_rules:
                    groups.append((cur_agents, cur_rules))
                    cur_agents, cur_rules, in_rules = [], [], False
                cur_agents.append(v.lower())
            elif k in ("allow", "disallow"):
                if not cur_agents:
                    continue
                in_rules = True
                if k == "disallow" and v == "":
                    continue
                cur_rules.append((k == "allow", _norm_path(v)))
        if cur_agents:
            groups.append((cur_agents, cur_rules))
        mine = [r for a, r in groups if any(x != "*" and (x == self.token or self.token.startswith(x)) for x in a)]
        if not mine:
            mine = [r for a, r in groups if "*" in a]
        return [x for r in mine for x in r]

    @staticmethod
    def _match(pat, path):
        rx = ""
        for i, ch in enumerate(pat):
            if ch == "*":
                rx += ".*"
            elif ch == "$" and i == len(pat) - 1:
                rx += "$"
            else:
                rx += re.escape(ch)
        return re.match(rx, path) is not None

    def allowed(self, url_or_path):
        u = urllib.parse.urlsplit(url_or_path)
        path = (u.path or "/") + ("?" + u.query if u.query else "")
        path = _norm_path(path)
        if path == "/robots.txt":
            return True
        best, allow = -1, True
        for is_allow, pat in self.rules:
            if self._match(pat, path):
                L = len(pat)
                if L > best or (L == best and is_allow):
                    best, allow = L, is_allow
        return allow


if __name__ == "__main__":
    # self-test
    t = """User-agent: *\nDisallow: /cart\nDisallow: /*?*utm_\nAllow: /products/*$\nDisallow: /private\n\nUser-agent: python-requests\nDisallow: /secret\n"""
    r = Robots(t, "python-requests")
    assert r.allowed("https://x.com/cart")  # our own group replaces '*'
    assert not r.allowed("https://x.com/secret/a")
    r2 = Robots(t.split("User-agent: python")[0], "python-requests")
    assert not r2.allowed("/cart") and r2.allowed("/") and not r2.allowed("/?utm_source=x")
    assert r2.allowed("/products/<slug>?utm_source=x")  # longer Allow /products/*$ wins (RFC 9309 longest match)
    assert r2.allowed("/products/<slug>") and not r2.allowed("/private")
    r3 = Robots("User-agent: *\nDisallow: /\nAllow: /$\n", "python-requests")
    assert r3.allowed("/") and not r3.allowed("/products/<slug>")
    r4 = Robots("User-agent: *\nDisallow:\n", "python-requests")
    assert r4.allowed("/anything")
    r5 = Robots("User-agent: *\nDisallow: /*?\n", "python-requests")
    assert r5.allowed("/products/<slug>") and not r5.allowed("/products/<slug>?utm_source=x")
    print("robots selftest PASS")
