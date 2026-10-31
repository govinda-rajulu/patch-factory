#!/usr/bin/env python3
"""W17a: advisory prose lint for living docs (knowledge/style/WRITING.md). Never fails.

Prints one ::warning per finding, at most 40, then PROSE_LINT <n>. Fenced code, inline code,
URLs and table separator rows are skipped. Dated records are out of scope on purpose.
Usage: prose_lint.py [FILE ...] (default: the living docs below).
"""
import re
import sys

LIVING = ['README.md', 'RECOVERY.md', 'SECURITY.md', 'AGENTS.md', 'docs/guide.md', 'docs/companions.md',
          'docs/APPS.md', 'docs/council/README.md', 'docs/council/SETUP.md', 'docs/council/PROVIDERS.md',
          'knowledge/README.md', 'knowledge/style/README.md',
          'knowledge/style/UI.md']
STOCK = ['crucial', 'seamless', 'seamlessly', 'delve', 'leverage', 'pivotal', 'showcase', 'tapestry',
         'testament', 'vibrant', 'meticulous', 'meticulously', 'underscores']
RULES = [
    ('dash', re.compile('[\u2013\u2014]'), 'em or en dash in prose (WRITING.md rule 6)'),
    ('stock', re.compile(r'\b(%s)\b' % '|'.join(STOCK), re.I), 'stock word (WRITING.md rule 7)'),
    ('notbut', re.compile(r"\bnot (?:just|only|merely)\b[^.]{0,80}\bbut\b", re.I), '"not just X but Y" (rule 1)'),
    ('opener', re.compile(r"\b(here's the thing|let's dive in|without further ado)\b", re.I), 'staged opener (rule 3)'),
]
FENCE = re.compile(r'```.*?```', re.S)
CODE = re.compile(r'`[^`\n]*`')
URL = re.compile(r'https?://\S+')


def findings(path, text):
    text = FENCE.sub(lambda m: '\n' * m.group(0).count('\n'), text)
    out = []
    for n, line in enumerate(text.split('\n'), 1):
        if re.fullmatch(r'\s*\|?[\s:|-]+\|?\s*', line or 'x'):
            continue
        clean = URL.sub('', CODE.sub('', line))
        for kind, rx, why in RULES:
            m = rx.search(clean)
            if m:
                out.append((path, n, kind, why, m.group(0)))
    return out


def main(argv):
    files = argv or LIVING
    found = []
    for f in files:
        try:
            with open(f, encoding='utf-8') as fh:
                found += findings(f, fh.read())
        except OSError:
            continue
    for path, n, kind, why, hit in found[:40]:
        print('::warning file=%s,line=%d::%s: %s' % (path, n, why, hit[:40]))
    print('PROSE_LINT %d finding(s) in %d file(s) (advisory; never fails)' % (len(found), len(files)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
